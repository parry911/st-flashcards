import json,re,sys
exec(open('core.py').read().replace("SRC = sys.argv[1] if len(sys.argv) > 1 else 'page.md'","SRC='page.md'"))
D=json.load(open('units.json')); U={u['id']:u for u in D['units']}
spec=open(f'spec/0{sys.argv[1][-1]}.txt').read()
tok={}
for m in re.finditer(r'(u\d+)(/\+[\da.!*+]*)?',spec): tok.setdefault(m.group(1),m.group(2) or '')
for t in D['topics']:
    if t['subj']!=sys.argv[1]: continue
    head=False
    for uid in t['units']:
        u=U[uid]; txt=u.get('t','')
        if not txt: continue
        p=plain(txt); d=0; out=''; k=0; a=0; i=0
        while i<len(p):
            ch=p[i]
            if ch in '([': d+=1
            elif ch in ')]': d=max(0,d-1)
            if p[i:i+5]==' + + ': k+=1; out+=f' [{k}] '; i+=5; continue
            if p[i:i+3]==' + ': k+=1; out+=f' [{k}{"" if d==0 else "'"}] '; i+=3; continue
            if p[i:i+3]==' → ': a+=1; out+=f' →a{a} '; i+=3; continue
            out+=ch; i+=1
        if k==0 and a==0: continue
        if not head: print('##',t['name'][:50]); head=True
        print(f"{uid}{tok.get(uid,'')} {('['+plain(u['h']).strip()+'] ') if u.get('h') else ''}{out}")
