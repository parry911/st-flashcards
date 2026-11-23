"""Every non-empty line of the page must appear, word for word and in order, on a card."""
import json, re, sys
sys.argv = [sys.argv[0]]
exec(open('build_deck.py').read().split('# ---------- build ----------')[0])
D = json.load(open('deck.json'))

def stream(c, t, subj):
    parts = [subj, t['name']] + c['path'] + ([c['title']] if c.get('title') else []) + c.get('head', [])
    for r in c['rows']:
        for k in ('sec', 'h', 't'):
            if k in r: parts.append(r[k])
    return ' '.join(' '.join(words(x)) for x in parts)

subjname = {s['id']: s['name'] for s in D['subjects']}
streams = []
for t in D['topics']:
    for c in t['cards']:
        streams.append((c['id'], t['subj'], ' ' + stream(c, t, subjname[t['subj']]) + ' '))
imgs_on_cards = sorted(r['img'] for t in D['topics'] for c in t['cards'] for r in c['rows'] if 'img' in r)
vids = sum(1 for t in D['topics'] for c in t['cards'] for r in c['rows'] if 'video' in r)

first = min(n['i'] for n in nodes if n['depth'] == 0)
last = max(n['end'] for n in nodes if n['depth'] == 0)
STRUCT = re.compile(r'^(<p />|<p>|</p>|</?toggle[^>]*>|</?ul>|</?ol>|<li[^>]*>|</li>|<callout[^>]*>|</callout>|---|</?colgroup>|<col[^>]*/>|<table[^>]*>|</table>|<tr[^>]*>|</tr>|<td[^>]*>|</td>|<image[^>]*/>|<video[^>]*/>)$')
missing = []; checked = 0; per_subj = {}
subj_of_line = {}
for k, n in enumerate(nodes):
    if n['depth'] == 0:
        for i in range(n['i'], n['end'] + 1): subj_of_line[i] = n['title']
for i in range(first, last + 1):
    s = L[i].strip()
    if not s or STRUCT.match(s) or s.startswith('!['): continue
    if s.startswith('|'):
        cells = [c for c in s.strip('|').split('|') if not re.fullmatch(r'\s*-+\s*', c)]
        toks = [words(clean_inline(c)) for c in cells]
    else:
        toks = [words(clean_inline(MARK.sub('', s, count=1)))]
    for tk in toks:
        if not tk: continue
        checked += 1
        needle = ' ' + ' '.join(tk) + ' '
        ok = any(needle in st for _, _, st in streams)
        sj = subj_of_line.get(i, '?')
        per_subj.setdefault(sj, [0, 0]); per_subj[sj][0] += 1
        if not ok:
            per_subj[sj][1] += 1
            missing.append((i, s[:160]))
print('lines checked', checked, 'missing', len(missing))
for k, v in per_subj.items(): print(f'  {k[:40]:40} {v[0]:5} lines  {v[1]} missing')
for m in missing[:40]: print('MISSING', m)
refs = json.load(open('img_refs.json'))
print('images on cards', len(imgs_on_cards), 'of', len(refs), 'distinct', len(set(imgs_on_cards)), '| videos', vids)
