import json,re,sys
D=json.load(open('site_deck.json'))
st=lambda s: re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',re.sub(r'<br>|</span><span class="li[^"]*">',' ¦ ',s or ''))).strip()
from html import unescape
for t in D['topics']:
    if t['subj']!=sys.argv[1]: continue
    for c in t['cards']:
        print(f"Q {c['id'].split(':')[0][:18]}:{c['id'].split(':')[1][:14]} | {unescape(c['q'])}")
        for r in c['rows']:
            if 't' in r: print('   ', (st(r['h'])[:28]+' ' if r.get('h') else '')+st(r['t'])[:int(sys.argv[2])])
