"""page_raw.md (fresh Notion fetch) -> page.md for the Environment & DM deck, plus pyq.json and pin.json.

Only structure changes here, never words:
  - grey PYQ toggles are lifted out (they feed the PYQ star panel, keyed by topic title)
  - the label legend line and the keyword callout sit above the first section: the callout goes to the pinned box
  - the PARFREII line under DISASTER MANAGEMENT goes to the pinned box
  - other loose lines directly under a section become a small topic of their own (no circle)
  - "ANUDEEP NOTES" (EIA) is called "EIA notes"; each of its bold sub-heads becomes an EIA topic
"""
import re, json

L = open('page_raw.md').read().split('\n')
a = L.index('<content>') + 1; b = L.index('</content>')
L = L[a:b]

def title_after(i):
    j = i + 1
    while not L[j].strip(): j += 1
    return j

# ---------- pinned box: keyword callout (above section 1) ----------
pin = {}
first_h1 = next(i for i, l in enumerate(L) if l.strip() == '<toggle heading="h1">')
for i in range(first_h1):
    if L[i].strip().startswith('<callout'):
        j = i + 1; body = []
        while L[j].strip() != '</callout>': body.append(L[j]); j += 1
        pin['keywords'] = '\n'.join(x for x in body if x.strip())

# ---------- walk toggles; lift grey PYQ toggles ----------
out = []; stack = []; pyq = {}; i = 0
def owner():
    for kind, t in reversed(stack):
        if kind in ('h4',): return t
    for kind, t in reversed(stack):
        if kind == 'h1': return t
    return None
while i < len(L):
    s = L[i].strip()
    if s.startswith('<toggle'):
        kind = 'gray' if 'color="gray"' in s else 'h1' if 'heading="h1"' in s else 'h4' if 'heading="h4"' in s else 'plain'
        tj = title_after(i)
        if kind == 'gray':
            depth = 1; j = i + 1; items = []
            while depth:
                t = L[j].strip()
                if t.startswith('<toggle'): depth += 1
                elif t == '</toggle>': depth -= 1
                elif j > tj and t.startswith('- '): items.append(t[2:])
                j += 1
            pyq.setdefault(owner(), []).extend(items)
            i = j
            while i < len(L) and not L[i].strip() and out and not out[-1].strip(): i += 1
            continue
        stack.append((kind, L[tj].strip()))
    elif s == '</toggle>':
        stack.pop()
    out.append(L[i]); i += 1
L = out

# ---------- section-level loose lines ----------
out = []; i = 0; depth = 0; sec = None
while i < len(L):
    s = L[i].strip()
    if s.startswith('<toggle'):
        if 'heading="h1"' in s:
            sec = L[title_after(i)].strip(); out.append(L[i]); out.append(L[title_after(i)])
            i = title_after(i) + 1; depth += 1; continue
        depth += 1
    elif s == '</toggle>':
        depth -= 1
    elif depth == 1 and s:
        # a run of loose lines directly under a section
        j = i; block = []
        while j < len(L) and not L[j].strip().startswith('<toggle') and L[j].strip() != '</toggle>':
            block.append(L[j]); j += 1
        text = [x for x in block if x.strip()]
        if 'PARFREII' in ' '.join(text):
            pin['parfreii'] = '\n'.join(text)
        else:
            body = [x for x in text if not re.match(r'^</?callout', x.strip())]
            lab = re.sub(r'<[^>]+>', '', re.sub(r'^- ', '', body[0])).split(':')[0].strip()
            out += ['<toggle heading="h4">', lab, ''] + body + ['</toggle>', '']
        i = j; continue
    out.append(L[i]); i += 1
L = out

# ---------- EIA: ANUDEEP NOTES -> one topic per bold sub-head ----------
k = next(i for i, l in enumerate(L) if l.strip() == 'ANUDEEP NOTES')
assert L[k - 1].strip() == '<toggle>'
depth = 1; e = k + 1
while depth:
    t = L[e].strip()
    if t.startswith('<toggle'): depth += 1
    elif t == '</toggle>': depth -= 1
    e += 1
body = L[k + 1:e - 1]
new = []; cur = None
for l in body:
    m = re.fullmatch(r'<b>(.+)</b>', l.strip())
    if m:
        if cur is not None: new += ['</toggle>', '']
        new += ['<toggle heading="h4">', m.group(1), '']; cur = m.group(1)
    else:
        new.append(l)
new += ['</toggle>']
L = L[:k - 1] + new + L[e:]
eia_topics = [l.strip() for i, l in enumerate(new) if i and new[i - 1] == '<toggle heading="h4">']

# EIA PYQs sit under the section: give each to the sub-head that names its year, the rest to the first
sec6 = [s for s in pyq if s and s.startswith('6')]
for s in sec6:
    for q in pyq.pop(s):
        yr = re.match(r'<b>(\d{4})', q).group(1)
        tgt = next((t for t in eia_topics if f'PYQ {yr}' in t), eia_topics[0])
        pyq.setdefault(tgt, []).append(q)

open('page.md', 'w').write('\n'.join(L))
json.dump(pyq, open('pyq.json', 'w'), ensure_ascii=False, indent=0)
json.dump(pin, open('pin.json', 'w'), ensure_ascii=False, indent=0)
json.dump({'eia_topics': eia_topics, 'eia_group': 'EIA notes'}, open('eia.json', 'w'), ensure_ascii=False)
print('lines', len(L), '| PYQ owners', len(pyq), 'questions', sum(len(v) for v in pyq.values()), '| pin', list(pin), '| EIA topics', eia_topics)
