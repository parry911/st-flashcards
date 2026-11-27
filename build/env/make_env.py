"""Build the site page with both decks: S&T data from the live page, Environment & DM from newway/ (big cards) + deck.json (EIA).
Writes env/site_deck.json (the env deck as embedded) and ../../index.html."""
import json, re, os, sys
from html import escape
sys.argv = [sys.argv[0]]
exec(open('core.py').read())
import subprocess
subprocess.run([sys.executable, 'newway/build.py'], check=True)   # big cards from the New way + EIA cards from deck.json
D = json.load(open('newway/env_big.json'))
# question fronts (Claude's wording, fronts only; card backs stay word for word): fronts/*.txt, "card id | question"
import glob as _g
Q = {}
for f in sorted(_g.glob('fronts/*.txt')):
    for ln in open(f):
        if ' | ' in ln and not ln.startswith('#'):
            cid, q = ln.rstrip('\n').split(' | ', 1); Q[cid.strip()] = q.strip()
ids = {c['id'] for t in D['topics'] for c in t['cards']}
Q = {k: v for k, v in Q.items() if k in ids}   # only the EIA cards still use question fronts
for t in D['topics']:
    for c in t['cards']:
        if c['id'] in Q: c['q'] = escape(Q[c['id']])
print('question fronts', len(Q), 'of', len(ids))
# long prose cards: the front says to give them a quick read in Notion (Perry, 24 Nov)
READ = [l.strip() for l in open('read_in_notion.txt') if l.strip() and not l.startswith('#')]
READ = [r for r in READ if r in ids]
for t in D['topics']:
    for c in t['cards']:
        if c['id'] in READ: c['read'] = 1
D['notion'] = 'https://app.notion.com/p/4221111b206d80b0a97fe118421fe6d8'
print('quick-read cards', len(READ))
D['title'] = 'Environment &amp; DM'
D['subtitle'] = 'GS3 · 6 sections · ' + str(len(D['topics'])) + ' topics · one big card per topic (EIA: ' + str(sum(len(t['cards']) for t in D['topics'] if t['subj'] == 's06')) + ' cards)'
D['img'] = {str(k): f'img/env/{k:02d}.jpg' for k in range(len(json.load(open('img_refs.json')))) if os.path.exists(f'../../img/env/{k:02d}.jpg')}
json.dump(D, open('site_deck.json', 'w'), ensure_ascii=False, separators=(',', ':'))
# S&T deck: exactly what is live
live = open('../../index.html').read()
if 'const DECKS={st:' in live:
    a = live.index('const DECKS={st:') + len('const DECKS={st:'); b = live.index(',env:', a)
else:
    a = live.index('const DECK=') + len('const DECK='); b = live.index(';\n</script>', a)
ST = json.loads(live[a:b].replace('<\\/', '</'))
BUILD = re.search(r'const BUILD="([^"]*)"', live).group(1)
enc = lambda x: json.dumps(x, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
html = open('../template.html').read().replace('/*CSS_GS3*/', open('../gs3_css.css').read())
html = html.replace('/*DATA*/', enc(ST)).replace('/*ENVDATA*/', enc(D)).replace('/*BUILD*/', os.environ.get('BUILD_DATE') and 'updated ' + os.environ['BUILD_DATE'] or BUILD)
open('../../index.html', 'w').write(html)
print('S&T topics', len(ST['topics']), '| env topics', len(D['topics']), 'images', len(D['img']), '| page', len(html.encode()) // 1024, 'KB')
