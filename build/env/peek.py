import json, re, sys
D = json.load(open('deck.json'))
strip = lambda s: re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', re.sub(r'<br>|</span><span class="li[^"]*">', ' ¦ ', s))).strip()
RL = {'def':'What it is','how':'How it works','use':'Significance','issue':'Challenges','fix':'Way forward','gov':'Initiatives','news':'In the news','fact':'Key facts','tbl':'Table','pic':'Notes','eg':'Examples','cause':'Causes','effect':'Effects'}
want = sys.argv[1:]
for t in D['topics']:
    if want and not any(w.lower() in t['name'].lower() for w in want): continue
    for c in t['cards']:
        path = c.get('path', []); big = c.get('title') or (path[-1] if path else t['name'])
        crumbs = [t['name']] + path if c.get('title') or path else []
        secs = [strip(r['sec']) for r in c['rows'] if 'sec' in r] or [strip(r['h']) for r in c['rows'] if r.get('h') and not r.get('cont')]
        n = sum(1 for r in c['rows'] if 't' in r)
        print(f"\n== {' › '.join(crumbs)} | {strip(big)} | [{' · '.join(RL[r] for r in c['roles'])}] {n} pts | cue: {' · '.join(secs[:4])}")
        for r in c['rows']:
            if 'sec' in r: print('   ##', strip(r['sec']))
            elif 't' in r: print('   -', ('['+strip(r['h'])+'] ' if r.get('h') else '') + strip(r['t'])[:230])
            else: print('   ', list(r))
