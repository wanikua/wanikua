"""Render wanikua's 2026 public contribution calendar using GitHub GraphQL."""
import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

START = date(2026, 1, 1)
END = date(2026, 12, 31)
LEVELS = ['NONE', 'FIRST_QUARTILE', 'SECOND_QUARTILE', 'THIRD_QUARTILE', 'FOURTH_QUARTILE']
COLORS = ['#e2e2da', '#b1c0a2', '#809974', '#536f4e', '#2c452f']
OUT = Path(__file__).resolve().parents[1] / 'assets/contributions-2026.svg'
QUERY = """query($from: DateTime!, $to: DateTime!) {
  user(login: "wanikua") {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionLevel } } }
    }
  }
}"""


def read_calendar(now):
    stop = min(now, datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
    payload = {'query': QUERY, 'variables': {'from': '2026-01-01T00:00:00Z', 'to': stop.isoformat()}}
    request = urllib.request.Request('https://api.github.com/graphql', json.dumps(payload).encode(),
        {'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'], 'Content-Type': 'application/json',
         'User-Agent': 'wanikua-profile-calendar'})
    with urllib.request.urlopen(request, timeout=30) as response:
        reply = json.load(response)
    if reply.get('errors'):
        raise RuntimeError(reply['errors'])
    weeks = reply['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
    levels = {}
    for week in weeks:
        for item in week['contributionDays']:
            day = date.fromisoformat(item['date'])
            if START <= day <= stop.date():
                levels[day] = LEVELS.index(item['contributionLevel'])
    if len(levels) != (stop.date() - START).days + 1:
        raise ValueError('GitHub returned an incomplete 2026 calendar')
    return levels


def render(levels):
    origin = START - timedelta(days=(START.weekday() + 1) % 7)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="171" viewBox="0 0 960 171">',
           '<title>2026 GitHub contributions</title><rect width="960" height="171" fill="#f8f8f4"/>']
    for n in range((END - START).days + 1):
        day = START + timedelta(days=n)
        week, weekday = divmod((day - origin).days, 7)
        x, y = 21 + week * 17.5, 38 + weekday * 17.5
        if day.day == 1:
            svg.append(f'<text x="{x}" y="24" font-family="monospace" font-size="13" fill="#535750">{day:%b}</text>')
        if day in levels:
            svg.append(f'<rect x="{x}" y="{y}" width="13" height="13" rx="1" fill="{COLORS[levels[day]]}"/>')
        else:
            svg.append(f'<circle cx="{x+6.5}" cy="{y+6.5}" r="1" fill="#d7d8cd"/>')
    return ''.join(svg) + '</svg>\n'


if __name__ == '__main__':
    OUT.write_text(render(read_calendar(datetime.now(timezone.utc))), encoding='utf-8')
