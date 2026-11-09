#!/usr/bin/env python3
"""Generate GitHub profile SVGs using authenticated GitHub GraphQL API.
Uses only the standard library and GITHUB_TOKEN provided by GitHub Actions.
"""
import datetime as dt
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'public'
USER = os.environ.get('GITHUB_USERNAME', 'sarahaliriel')
TOKEN = os.environ.get('GITHUB_TOKEN')
BG, DARK, MUTED, ACCENT, LIGHT = '#F8F2EB', '#38271F', '#70594A', '#B99A82', '#E8D8C9'
FONT = 'Montserrat,Inter,Arial,Helvetica,sans-serif'

def text(x,y,s,size=16,color=DARK,weight=400,anchor=None):
    attr=f' text-anchor="{anchor}"' if anchor else ''
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color}"{attr}>{escape(str(s))}</text>'

def frame(w,h,title,subtitle=''):
    result=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">',f'<rect width="{w}" height="{h}" rx="16" fill="{BG}"/>',text(28,35,title,17,DARK,700)]
    if subtitle: result.append(text(28,56,subtitle,11,MUTED))
    return result

def write(name,parts):
    ASSETS.mkdir(parents=True,exist_ok=True)
    (ASSETS/name).write_text('\n'.join(parts+['</svg>'])+'\n',encoding='utf-8')
    print('Created',name)

def graphql():
    if not TOKEN:
        raise RuntimeError('GITHUB_TOKEN is missing; run this through GitHub Actions')
    today=dt.datetime.now(dt.timezone.utc)
    # One-year window, explicit UTC boundaries.
    start=(today-dt.timedelta(days=364)).replace(hour=0,minute=0,second=0,microsecond=0)
    query='''query($login:String!, $from:DateTime!, $to:DateTime!) {
      user(login:$login) {
        name
        contributionsCollection(from:$from,to:$to) {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
        repositories(first:100,ownerAffiliations:OWNER,privacy:PUBLIC,isFork:false) {
          totalCount
          nodes { stargazerCount }
        }
      }
    }'''
    body=json.dumps({'query':query,'variables':{'login':USER,'from':start.isoformat().replace('+00:00','Z'),'to':today.isoformat().replace('+00:00','Z')}}).encode()
    request=Request('https://api.github.com/graphql',data=body,headers={'Authorization':f'Bearer {TOKEN}','User-Agent':'sarahaliriel-readme-stats','Content-Type':'application/json','Accept':'application/vnd.github+json'},method='POST')
    with urlopen(request,timeout=25) as resp: data=json.load(resp)
    if data.get('errors'):raise RuntimeError(str(data['errors']))
    if not data.get('data',{}).get('user'):raise RuntimeError('GitHub user not found')
    return data['data']['user']

def make_cards(user):
    collection=user['contributionsCollection']['contributionCalendar']
    days=sorted((d for w in collection['weeks'] for d in w['contributionDays']),key=lambda d:d['date'])
    counts={dt.date.fromisoformat(d['date']):d['contributionCount'] for d in days}
    today=dt.datetime.now(dt.timezone.utc).date()
    # Avoid counting future dates; streak may legitimately end yesterday.
    dates=[x for x in sorted(counts) if x<=today]
    active=sum(1 for day in dates if counts[day]>0)
    total=collection['totalContributions']
    repos=user['repositories']['totalCount']
    stars=sum(node['stargazerCount'] for node in user['repositories']['nodes'])
    parts=frame(360,190,'GitHub overview','LAST 12 MONTHS · PUBLIC PROFILE DATA')
    parts.extend([text(28,109,f'{total:,}',38,DARK,700),text(28,132,'contributions',13,MUTED),'<path d="M 188 79 V 158" stroke="#D7C4B5"/>',text(212,98,str(active),23,DARK,700),text(212,117,'active days',12,MUTED),text(212,146,str(repos),23,DARK,700),text(255,146,'public repos',11,MUTED),text(28,171,f'{stars:,} stars across first 100 public repositories',10,MUTED)])
    write('github-overview.svg',parts)

    def is_on(day):return counts.get(day,0)>0
    # Start at today unless no contributions today, when yesterday is valid as current streak.
    anchor=today if is_on(today) else today-dt.timedelta(days=1)
    current=0
    while is_on(anchor-dt.timedelta(days=current)):
        current+=1
    longest=0
    run=0
    for day in dates:
        if is_on(day):run+=1;longest=max(longest,run)
        else:run=0
    parts=frame(360,190,'Contribution streak','LAST 12 MONTHS · UTC')
    parts.extend(['<circle cx="180" cy="100" r="50" stroke="#E6D8CC" stroke-width="9" fill="none"/>','<circle cx="180" cy="100" r="50" stroke="#B99A82" stroke-width="9" stroke-dasharray="220 314" stroke-linecap="round" fill="none" transform="rotate(-90 180 100)"/>',text(180,110,current,37,DARK,700,'middle'),text(59,103,longest,26,DARK,700,'middle'),text(59,125,'longest',11,MUTED,400,'middle'),text(304,103,active,26,DARK,700,'middle'),text(304,125,'active days',11,MUTED,400,'middle'),text(180,174,'current streak · days',12,MUTED,500,'middle')])
    write('github-streak.svg',parts)

    # Weekly bar-chart: real contribution counts, zero-based with last 26 weeks shown.
    last_weeks=[]
    # Group by ISO week start (Monday); avoid misleading fictional values.
    groups={}
    for day in dates:
        monday=day-dt.timedelta(days=day.weekday())
        groups[monday]=groups.get(monday,0)+counts[day]
    last_weeks=sorted(groups.items())[-26:]
    maximum=max([n for _,n in last_weeks]+[1])
    parts=frame(740,250,'Contribution activity','WEEKLY CONTRIBUTIONS · LAST 26 WEEKS')
    parts.extend(['<path d="M 33 202 H 708" stroke="#D7C4B5" stroke-width="1"/>'])
    for index,(_,count) in enumerate(last_weeks):
        x=39+index*25.4
        h=round(count/maximum*117,1)
        y=201-h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="16" height="{max(h,1):.1f}" rx="3" fill="{ACCENT if count else LIGHT}"/>')
    if last_weeks:
        parts.extend([text(39,226,last_weeks[0][0].strftime('%b %d'),11,MUTED),text(701,226,last_weeks[-1][0].strftime('%b %d'),11,MUTED,anchor='end')])
    parts.append(text(700,35,f'{sum(x[1] for x in last_weeks):,} in 26 weeks',12,MUTED,anchor='end'))
    write('github-activity.svg',parts)

if __name__=='__main__':
    make_cards(graphql())
