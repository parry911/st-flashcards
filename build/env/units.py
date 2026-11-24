"""Inventory: every piece of Perry's text gets an id (u1, u2, ...) in page order. Topics carry circle, PYQs, group."""
import json, re, sys
sys.argv = [sys.argv[0]]
exec(open('core.py').read())
PYQ = json.load(open('pyq.json')); EIA = json.load(open('eia.json'))
CIRC = {'🟢': 'g', '🟡': 'y', '⚪': 'w'}
units = []; topics = []
subjects = [k for k, n in enumerate(nodes) if n['depth'] == 0]
for si, sk in enumerate(subjects):
    for tk in nodes[sk]['kids']:
        T = nodes[tk]; raw = T['title']
        circ = CIRC.get(raw[:1]); name = clean_inline(raw[1:] if circ else raw)
        tinfo = {'subj': f's{si+1:02d}', 'node': tk, 'name': name, 'circle': circ, 'toggles': [], 'units': [],
                 'pyq': [clean_inline(q) for q in PYQ.get(raw, [])]}
        if raw in EIA['eia_topics']: tinfo['group'] = EIA['eia_group']
        def walk(nk, path):
            items, src = own_items(nk)
            tinfo['toggles'].append({'node': nk, 'path': [clean_inline(nodes[p]['title']) for p in path]})
            for it in items:
                u = {'id': f'u{len(units)+1}', 'node': nk}
                for k, v in it.items():
                    if not k.startswith('_'): u[k] = v
                u['g'] = it.get('_g'); u['ind'] = it.get('_ind', 0); u['bul'] = it.get('_bul', False)
                units.append(u); tinfo['units'].append(u['id'])
            for c in nodes[nk]['kids']: walk(c, path + [c])
        walk(tk, [])
        topics.append(tinfo)
used_pyq = {t['name'] for t in topics if t['pyq']}
assert sum(len(t['pyq']) for t in topics) == sum(len(v) for v in PYQ.values()), 'a PYQ owner did not match a topic'
json.dump({'units': units, 'topics': topics}, open('units.json', 'w'), ensure_ascii=False)
from collections import Counter
print(len(units), 'units', len(topics), 'topics | circles', Counter(t['circle'] for t in topics), '| topics with PYQs', len(used_pyq))
for si in range(len(subjects)):
    ts = [t for t in topics if t['subj'] == f's{si+1:02d}']
    print(f's{si+1:02d}', clean_inline(nodes[subjects[si]]['title']), len(ts), 'topics', sum(len(t['units']) for t in ts), 'units')
