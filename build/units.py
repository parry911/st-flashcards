"""Inventory: every piece of Perry's text gets an id (u1, u2, ...) in page order."""
import json, re, sys
sys.argv = [sys.argv[0]]
exec(open('build_deck.py').read().split('# ---------- build ----------')[0])
units = []; topics = []
subjects = [k for k, n in enumerate(nodes) if n['depth'] == 0]
for si, sk in enumerate(subjects):
    for tk in nodes[sk]['kids']:
        T = nodes[tk]; tinfo = {'subj': f's{si+1:02d}', 'node': tk, 'name': clean_inline(T['title']), 'toggles': [], 'units': []}
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
json.dump({'units': units, 'topics': topics}, open('units.json', 'w'), ensure_ascii=False)
print(len(units), 'units', len(topics), 'topics')
