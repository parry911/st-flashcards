import json, re, sys
exec(open('core.py').read().replace("SRC = sys.argv[1] if len(sys.argv) > 1 else 'page.md'", "SRC='page.md'"))
D = json.load(open('units.json'))
U = {u['id']: u for u in D['units']}
subj = sys.argv[1]; lo = int(sys.argv[2]); hi = int(sys.argv[3])
ts = [t for t in D['topics'] if t['subj'] == subj][lo:hi]
NP = {}
for t in ts:
    for tg in t['toggles']: NP[tg['node']] = tg['path']
def pc(h):
    p = plain(h); d = 0; n = 0
    for i, ch in enumerate(p):
        if ch in '([': d += 1
        elif ch in ')]': d = max(0, d-1)
        elif d == 0 and p[i:i+3] == ' + ': n += 1
    return n
for t in ts:
    print(f"\n### [{t['circle']}] {t['name']}  (pyq {len(t['pyq'])})")
    last = None
    for uid in t['units']:
        u = U[uid]
        if u['node'] != last and NP.get(u['node']): print('   >> toggle:', ' › '.join(NP[u['node']]))
        last = u['node']
        if 'sec' in u: s = 'SEC ' + plain(u['sec'])
        elif 'img' in u: s = 'IMG ' + str(u['img'])
        elif 'table' in u: s = 'TABLE ' + ' || '.join(' | '.join(plain(c) for c in r) for r in u['table'])
        else:
            s = (('[' + plain(u['h']) + '] ') if u.get('h') else '') + plain(u.get('t', ''))
            k = [0]
            def num(m):
                k[0] += 1; return f' +{k[0]} '
            s = re.sub(r' \+ ', num, s)
        if ' +' not in s and len(s) > 200: s = s[:200] + ' …'
        if ' +' in s and len(s) > 420: s = s[:420] + ' …'
        ind = '  ' * (u.get('ind', 0) // 2)
        print(f"{uid}{'' if u.get('bul') else '¶'} {ind}{s}")
