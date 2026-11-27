"""Environment & DM big cards: one card per syllabus topic, built from the New way of the Notion page.
page.md = Notion fetch of the page (with discussions); comments.json = comment texts by discussion id.
EIA cards and all PYQs come from ../deck.json unchanged. Writes env_big.json."""
import json, re, hashlib, html as H, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inline import chars, snap, plain, render
HERE = os.path.dirname(os.path.abspath(__file__))
from tree import parse
_L = open(os.path.join(HERE, 'page.md')).read().split('\n')
_a = _L.index('<content>') + 1; _b = [i for i, l in enumerate(_L) if l.strip() == '</content>'][0]
T = parse(_L, _a, _b)
CM = json.load(open(os.path.join(HERE, 'comments.json')))
ENV = os.path.join(HERE, '..') + '/'
OLD = json.load(open(ENV + 'deck.json'))
REFS = json.load(open(ENV + 'img_refs.json'))
IMGID = {}
for k, (f, src) in enumerate(REFS):
    if os.path.exists(os.path.join(HERE, '../../../img/env', f'{k:02d}.jpg')):
        IMGID[re.search(r'notion-file-block://([0-9a-f-]+)', src).group(1)] = f'img/env/{k:02d}.jpg'
CIRC = {'🟢': 'g', '🟡': 'y', '⚪': 'w'}
SECNAME = {'1': '1. Conservation', '2': '2. Climate Change', '3': '3. Pollution', '4': '4. Renewable Energy', '5': '5. Disaster Management'}
missing = []
def cmtext(d):
    v = CM.get(d)
    if not v: missing.append(d); return None
    return ' '.join(v if isinstance(v, list) else [v])
class Card:
    def __init__(s): s.cm = {}; s.cmk = {}; s.hs = []
    def html(s, txt, hsmark=None):
        C = snap(chars(txt))
        for x in C:
            d = x['cm']
            if d and d not in s.cmk:
                t = cmtext(d)
                if t is None: x['cm'] = None; continue
                k = str(len(s.cm)); s.cm[k] = H.escape(t, quote=False); s.cmk[d] = k
        return C
    def out(s, C): return render(C, s.cmk)
def hs_body(card, kids):
    parts = []; lis = []
    def flush():
        if lis: parts.append('<ul>' + ''.join(f'<li>{x}</li>' for x in lis) + '</ul>'); lis.clear()
    for y in kids:
        if y['k'] == 'li': lis.append(card.out(card.html(y['x'])))
        elif y['k'] == 'img':
            bid = re.search(r'notion-file-block://([0-9a-f-]+)', y['src']).group(1)
            if bid in IMGID: flush(); parts.append(f'<div class="pic"><img src="{IMGID[bid]}" alt="" loading="lazy"></div>')
            else: print('image without file', y['src'][:80])
        elif y['k'] == 'tog':
            flush(); parts.append(f'<details><summary>{card.out(card.html(y["title"]))}</summary>{hs_body(card, y["kids"])}</details>')
        elif y['k'] == 'p': flush(); parts.append(f'<p>{card.out(card.html(y["x"]))}</p>')
        else: raise Exception(y['k'])
    flush(); return ''.join(parts)
def cue(txt):
    fm = re.match(r'^Frame\s*:\s*', txt)
    if fm: return None, txt[fm.end():]   # the FRAME heading above is the cue
    p = plain(chars(txt)).strip()
    segs = [x.strip() for x in p.split(' · ')]
    labs = [x.split(':', 1)[0].strip() for x in segs if ':' in x and len(x.split(':', 1)[0]) <= 30]
    if len(segs) > 1 and len(labs) >= 2: return H.escape(' · '.join(labs), quote=False), txt
    m = re.match(r'^([^:<]{1,30}):\s*', txt)
    if m and ':' in p[:31]:
        lab = m.group(1).strip()
        if lab.lower() == 'frame': return None, txt[m.end():]
        return H.escape(lab, quote=False), txt
    return None, txt
def point(card, x, rows):
    t = x['x']; h = None; lt = False
    m = re.match(r'^<b>([A-Z]{1,2})</b>\s*:?\s*', t)
    if m: h = m.group(1); t = t[m.end():]; lt = True
    else: h, t = cue(t)
    C = card.html(t)
    row = {'C': C, 'h': h, 'lt': lt, 'hs': []}
    rows.append(row)
    for y in x.get('kids', []):
        if y['k'] == 'tog': add_hs(card, y, row)
        else: raise Exception('li kid ' + y['k'])
def add_hs(card, y, row):
    i = len(card.hs)
    title = plain(chars(y['title'])).strip()
    card.hs.append({'t': H.escape(title, quote=False), 'b': hs_body(card, y['kids'])})
    # highlight in place if the title text is in the point, else add a chip after it
    if row is None: return
    P = plain(row['C']).lower(); k = P.find(title.lower())
    if k >= 0 and title and all(c['hs'] is None for c in row['C'][k:k + len(title)]):
        for c in row['C'][k:k + len(title)]: c['hs'] = i
    else: row['hs'].append(i)
def build_topic(sec, grp, t):
    name = t['title'].strip(); circ = CIRC.get(name[0]); nm = name[1:].strip() if circ else name
    card = Card(); rows = []; secrows = []
    cur = 'Frame'; blocks = [[cur, []]]
    for x in t['kids']:
        if x['k'] == 'p':
            m = re.match(r'^<b>([^<]+)</b>\s*(:\s*(.*))?$', x['x'])
            assert m, x['x']
            blocks.append([m.group(1).strip(), []])
            if m.group(3): point(card, {'x': m.group(3)}, blocks[-1][1]); blocks[-1][1][-1]['h'] = None
        elif x['k'] == 'li': point(card, x, blocks[-1][1])
        elif x['k'] == 'tog':
            last = blocks[-1][1][-1] if blocks[-1][1] else None
            add_hs(card, x, last)
            if last is None: blocks[-1][1].append({'C': [], 'h': None, 'lt': False, 'hs': [len(card.hs) - 1]})
        else: raise Exception(x['k'])
    out = []
    for nmb, rs in blocks:
        if not rs: continue
        out.append({'sec': H.escape(nmb, quote=False)})
        for r in rs:
            body = card.out(r['C'])
            if r['hs']: body += ' ' + ''.join(f'<button class="hs chipx" data-h="{i}">{card.hs[i]["t"]}</button>' for i in r['hs'])
            o = {'t': body.strip()}
            if r['h']: o['h'] = r['h']
            if r['lt']: o['lt'] = 1
            out.append(o)
    sid = 'b-' + re.sub(r'[^a-z0-9]+', '-', nm.lower()).strip('-')
    payload = {'id': sid + ':big', 'big': 1, 'path': [], 'roles': [], 'rows': out, 'hs': card.hs, 'cm': card.cm}
    payload['v'] = hashlib.md5(json.dumps([r.get('t', r.get('sec')) for r in out], ensure_ascii=False).encode()).hexdigest()[:6]
    top = {'id': sid, 'subj': 's0' + sec[0], 'name': H.escape(nm, quote=False), 'cards': [payload]}
    if circ: top['circle'] = circ
    if grp: top['group'] = H.escape(grp.title() if grp.isupper() else grp, quote=False).replace('Dm Core', 'DM core')
    return top
tops = []; keys = {}
def walk(n, grp=None, sec=None):
    for x in n:
        if x['k'] == 'tog' and x['h'] == 'h1': walk(x['kids'], None, x['title'].replace('\\', ''))
        elif x['k'] == 'tog' and x['h'] == 'h3': walk(x['kids'], x['title'], sec)
        elif x['k'] == 'tog' and x['h'] == 'h4' and x['title'].startswith('🔑'): keys[x['title'][1:].strip()] = x
        elif x['k'] == 'tog' and x['h'] == 'h4' and sec and not sec.startswith('6'): tops.append(build_topic(sec, grp, x))
        elif x['k'] == 'callout': walk(x['kids'], grp, sec)
walk(T)
# keys box: keyword callout + PINCH-FC + PARFREII
kc = next(x for x in T if x['k'] == 'callout' and x['kids'] and 'keywords' in x['kids'][0].get('x', ''))
kw = H.escape(plain(chars(kc['kids'][0]['x'])), quote=False).replace('ENVIRONMENT', '<b>ENVIRONMENT</b>', 1)
def keylist(t):
    li = []
    for y in t['kids']:
        if y['k'] != 'li': continue
        C = chars(y['x']); s = render(C, {})
        s = re.sub(r'^<b>([A-Za-z]+)</b>', r'<span class="lt">\1</span>', s)
        li.append(f'<li>{s}</li>')
    return '<ul class="keys">' + ''.join(li) + '</ul>'
pin = {'kw': kw, 'keys': [['PINCH-FC · causes and fixes', keylist(keys['PINCH-FC'])], ['PARFREII · DM solutions', keylist(keys['PARFREII'])]]}
# PYQs: old topics' PYQs moved to the new big cards
MAP = {'overview': 'b-biodiversity-loss', 'criteria-for-biodiversity-hotspots': 'b-biodiversity-loss', 'the-biological-diversity-act-2002': 'b-biodiversity-loss',
 'aravallis': 'b-mining', 'unregulated-sand-mining': 'b-mining', 'coastal-sand-mining': 'b-mining', 'wetland-conservation': 'b-fragile-ecosystems',
 'anthropogenic-factors': 'b-climate-change-the-problem', 'melting-glaciers-ice-sheets': 'b-climate-change-the-problem', 'climate-change-sea-level-rise': 'b-climate-change-the-problem',
 'legal-policy-developments': 'b-climate-negotiations', 'panchamrit-india-s-cop26-climate-goals': 'b-climate-negotiations', 'india-specific-legislations': 'b-climate-negotiations',
 'cop-3-kyoto-protocol': 'b-climate-negotiations', 'cop-21-paris': 'b-climate-negotiations', 'cop-26-glasgow': 'b-climate-negotiations',
 'air': 'b-air', 'water': 'b-water', 'oil-spills': 'b-oil-spills', 'solid-waste': 'b-solid-waste', 'e-waste': 'b-e-waste', 'mercury-emissions': 'b-hazardous-biomedical-waste',
 'benefits-of-renewable-energy-re': 'b-energy-transition', 'challenges-of-re': 'b-energy-transition', 'solar-energy': 'b-solar', 'nuclear-energy-mission-budget-2025-26': 'b-nuclear', 'biofuels': 'b-bioenergy',
 'india-s-disaster-approach': 'b-india-s-dm-framework', 'disaster-management-amendment-act-2025': 'b-india-s-dm-framework', 'national-disaster-management-plan-ndmp-2': 'b-india-s-dm-framework', 'new-technology-for-disaster-management': 'b-india-s-dm-framework',
 'disaster-risk-formula': 'b-dm-spine', 'disaster-resilience': 'b-dm-spine', 'world-conferences-on-disaster-risk-reduc': 'b-dm-spine',
 'earthquakes': 'b-earthquakes', 'tsunamis': 'b-tsunamis', 'floods': 'b-floods', 'landslides': 'b-landslides', 'cloudburst': 'b-cloudburst', 'drought': 'b-drought', 'dams': 'b-dams'}
EXTRA = {'b-water': ['coastal-sand-mining']}   # seawater intrusion also sits under Water
byid = {t['id']: t for t in tops}
for o in OLD['topics']:
    if o['subj'] == 's06' or not o.get('pyq') or o['id'] not in MAP: continue   # people's movements PYQs are EIA questions: their EIA cards carry them
    tgt = [MAP[o['id']]] + [k for k, v in EXTRA.items() if o['id'] in v]
    for k in tgt:
        L = byid[k].setdefault('pyq', [])
        for q in o['pyq']:
            if q not in L: L.append(q)
# one PYQ in ../pyq.json that the old deck never placed: run-of-river (2013) goes to Hydro
for q in json.load(open(ENV + 'pyq.json')).get('🟢 Run-of-river Hydro', []):
    if q not in byid['b-hydro'].setdefault('pyq', []): byid['b-hydro']['pyq'].append(q)
def yr(q):
    m = re.search(r'(\d{4})', q); return -int(m.group(1)) if m else 0
for t in tops:
    if 'pyq' in t: t['pyq'].sort(key=yr)
eia = [t for t in OLD['topics'] if t['subj'] == 's06']
subjects = [{'id': 's0' + k, 'name': v} for k, v in SECNAME.items()] + [{'id': 's06', 'name': '6. EIA'}]
D = {'subjects': subjects, 'topics': tops + eia, 'pin': pin}
json.dump(D, open(os.path.join(HERE, 'env_big.json'), 'w'), ensure_ascii=False)
print('topics', len(tops), '+ EIA', len(eia), '| hot-spots', sum(len(t['cards'][0]['hs']) for t in tops), '| comments', sum(len(t['cards'][0]['cm']) for t in tops), '| rows', sum(sum(1 for r in t['cards'][0]['rows'] if 't' in r) for t in tops))
print('missing comment texts', len(missing), missing[:5])
print('no PYQ:', [t['id'] for t in tops if not t.get('pyq')])
