#!/usr/bin/env python3
"""Generate GitHub profile SVGs using authenticated GitHub GraphQL API.
Uses only the standard library and GITHUB_TOKEN provided by GitHub Actions.
"""
import datetime as dt
import json
import math
import os
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'public'
USER = os.environ.get('GITHUB_USERNAME', 'sarahaliriel')
TOKEN = os.environ.get('GITHUB_TOKEN')

BG = '#F8F2EB'
DARK = '#38271F'
MUTED = '#70594A'
ACCENT = '#B99A82'
LIGHT = '#E8D8C9'
DIVIDER = '#D7C4B5'
RING_BG = '#E6D8CC'

FONT = 'Montserrat,Inter,Arial,Helvetica,sans-serif'


def text(x, y, s, size=16, color=DARK, weight=400, anchor=None):
    attr = f' text-anchor="{anchor}"' if anchor else ''
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}"{attr}>'
        f'{escape(str(s))}</text>'
    )


def frame(w, h, title, subtitle=''):
    result = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">',
        f'<rect width="{w}" height="{h}" rx="16" fill="{BG}"/>',
        text(28, 35, title, 17, DARK, 700),
    ]
    if subtitle:
        result.append(text(28, 56, subtitle, 11, MUTED))
    return result


def write(name, parts):
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / name).write_text('\n'.join(parts + ['</svg>']) + '\n', encoding='utf-8')
    print('Created', name)


def graphql():
    if not TOKEN:
        raise RuntimeError('GITHUB_TOKEN is missing; run this through GitHub Actions')

    today = dt.datetime.now(dt.timezone.utc)
    start = (today - dt.timedelta(days=364)).replace(hour=0, minute=0, second=0, microsecond=0)

    query = '''query($login:String!, $from:DateTime!, $to:DateTime!) {
      user(login:$login) {
        name
        contributionsCollection(from:$from,to:$to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
        repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false) {
          totalCount
          nodes {
            stargazerCount
          }
        }
      }
    }'''

    body = json.dumps({
        'query': query,
        'variables': {
            'login': USER,
            'from': start.isoformat().replace('+00:00', 'Z'),
            'to': today.isoformat().replace('+00:00', 'Z'),
        }
    }).encode()

    request = Request(
        'https://api.github.com/graphql',
        data=body,
        headers={
            'Authorization': f'Bearer {TOKEN}',
            'User-Agent': 'sarahaliriel-readme-stats',
            'Content-Type': 'application/json',
            'Accept': 'application/vnd.github+json',
        },
        method='POST'
    )

    with urlopen(request, timeout=25) as resp:
        data = json.load(resp)

    if data.get('errors'):
        raise RuntimeError(str(data['errors']))
    if not data.get('data', {}).get('user'):
        raise RuntimeError('GitHub user not found')

    return data['data']['user']


def make_cards(user):
    collection = user['contributionsCollection']['contributionCalendar']
    days = sorted(
        (d for w in collection['weeks'] for d in w['contributionDays']),
        key=lambda d: d['date']
    )
    counts = {dt.date.fromisoformat(d['date']): d['contributionCount'] for d in days}

    today = dt.datetime.now(dt.timezone.utc).date()
    dates = [x for x in sorted(counts) if x <= today]

    active = sum(1 for day in dates if counts[day] > 0)
    total = collection['totalContributions']
    repos = user['repositories']['totalCount']
    stars = sum(node['stargazerCount'] for node in user['repositories']['nodes'])

    # =========================
    # Card 1: GitHub overview
    # =========================
    parts = frame(360, 190, 'GitHub overview', 'LAST 12 MONTHS · PUBLIC PROFILE DATA')
    parts.extend([
        text(28, 109, f'{total:,}', 38, DARK, 700),
        text(28, 132, 'contributions', 13, MUTED),

        f'<path d="M 188 79 V 158" stroke="{DIVIDER}"/>',

        text(214, 98, str(active), 23, DARK, 700),
        text(214, 117, 'active days', 12, MUTED),

        text(214, 146, str(repos), 23, DARK, 700),
        text(214, 165, 'public repos', 12, MUTED),
    ])
    write('github-overview.svg', parts)

    # =========================
    # Streak calculations
    # =========================
    def is_on(day):
        return counts.get(day, 0) > 0

    anchor = today if is_on(today) else today - dt.timedelta(days=1)

    current = 0
    while is_on(anchor - dt.timedelta(days=current)):
        current += 1

    longest = 0
    run = 0
    for day in dates:
        if is_on(day):
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    # =========================
    # Card 2: Contribution streak
    # =========================
    parts = frame(360, 190, 'Contribution streak', 'LAST 12 MONTHS · UTC')

    cx = 180
    cy = 112
    r = 31
    circumference = 2 * math.pi * r

    base = max(longest, 1)
    progress = current / base if base else 0
    progress = max(0.08, min(progress, 0.999))  # evita círculo 100% fechado visualmente
    dash = round(circumference * progress, 1)
    gap = round(circumference, 1)

    parts.extend([
        f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="{RING_BG}" stroke-width="8" fill="none"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="{ACCENT}" stroke-width="8" '
        f'stroke-dasharray="{dash} {gap}" stroke-linecap="round" fill="none" '
        f'transform="rotate(-90 {cx} {cy})"/>',

        text(cx, cy + 11, current, 35, DARK, 700, 'middle'),

        text(48, 110, longest, 24, DARK, 700, 'middle'),
        text(48, 138, 'longest', 11, MUTED, 400, 'middle'),

        text(312, 110, active, 24, DARK, 700, 'middle'),
        text(312, 138, 'active days', 11, MUTED, 400, 'middle'),

        text(cx, 174, 'current streak · days', 12, MUTED, 500, 'middle'),
    ])
    write('github-streak.svg', parts)

    # =========================
    # Card 3: Contribution activity
    # =========================
    groups = {}
    for day in dates:
        monday = day - dt.timedelta(days=day.weekday())
        groups[monday] = groups.get(monday, 0) + counts[day]

    last_weeks = sorted(groups.items())[-26:]
    maximum = max([n for _, n in last_weeks] + [1])

    parts = frame(740, 250, 'Contribution activity', 'WEEKLY CONTRIBUTIONS · LAST 26 WEEKS')
    parts.extend([
        f'<path d="M 33 202 H 708" stroke="{DIVIDER}" stroke-width="1"/>'
    ])

    for index, (_, count) in enumerate(last_weeks):
        x = 39 + index * 25.4
        h = round(count / maximum * 117, 1)
        y = 201 - h
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="16" height="{max(h,1):.1f}" rx="3" fill="{ACCENT if count else LIGHT}"/>'
        )

    if last_weeks:
        parts.extend([
            text(39, 226, last_weeks[0][0].strftime('%b %d'), 11, MUTED),
            text(701, 226, last_weeks[-1][0].strftime('%b %d'), 11, MUTED, anchor='end'),
        ])

    parts.append(
        text(700, 35, f'{sum(x[1] for x in last_weeks):,} in 26 weeks', 12, MUTED, anchor='end')
    )
    write('github-activity.svg', parts)


if __name__ == '__main__':
    make_cards(graphql())
