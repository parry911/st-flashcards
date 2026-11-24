import json,re,sys
D=json.load(open('deck.json'))
st=lambda s: re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',re.sub(r'<br>|</span><span class="li[^"]*">',' ¦ ',s or ''))).strip()
W=int(sys.argv[2]) if len(sys.argv)>2 else 110
for t in D['topics']:
    if t['subj']!=sys.argv[1]: continue
    print(f"## {t['name']}")
    for c in t['cards']:
        p=c.get('path',[])
        print(c['id'], '['+'+'.join(c['roles'])+']', ('» '+' › '.join(p)) if p else '', ('T: '+st(c['title'])[:50]) if c.get('title') else '')
        for r in c['rows']:
            if 'sec' in r: print('   #', st(r['sec'])[:60])
            elif 't' in r: print('   -', (st(r.get('h',''))+' ' if r.get('h') else '')+st(r['t'])[:W])
