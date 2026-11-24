"""Build the deck from a hand arrangement (spec/*.txt) of Perry's text units.

Spec lines:
  C <roles> | <title> | <items>
  roles : def how use issue fix gov news fact tbl pic, joined with + (e.g. use+issue)
  title : -        the card's own toggle name (or topic name)
          uN       a heading/short line of Perry's, used as the card title (consumed)
          l:uN     the label of unit uN (unit itself still placed as a point)
          @N12     the name of toggle node 12
  items : uN         one unit (heading/picture/video/table/point by its own kind)
          uA-uB      each unit in the range, separately
          uA+uB+uC   one point, shown as a bulleted list
          uA&uB      one point, the lines run on (a sentence broken over lines)
          h:uN       show a line as a heading
          k:uN       keep a long paragraph whole (no splitting at sentence breaks)
Every unit must be used exactly once. Nothing is retyped: every word comes from units.json.
"""
import json, re, sys, glob, hashlib
PARTIAL = '--partial' in sys.argv
sys.argv = [sys.argv[0]]
exec(open('core.py').read())
D = json.load(open('units.json'))
U = {u['id']: u for u in D['units']}
ORDER = {u['id']: i for i, u in enumerate(D['units'])}
TOPIC_OF = {}
for ti, t in enumerate(D['topics']):
    for uid in t['units']: TOPIC_OF[uid] = ti
NODEPATH = {}
for t in D['topics']:
    for tg in t['toggles']: NODEPATH[tg['node']] = tg['path']
ROLES = {'def', 'how', 'use', 'issue', 'fix', 'gov', 'news', 'fact', 'tbl', 'pic', 'eg', 'cause', 'effect'}
SPLIT_OVER = 75   # paragraphs longer than this open in pieces, cut only at Perry's own sentence ends

errors = []
def err(m): errors.append(m)

def uid_ok(x):
    if x not in U: err(f'unknown unit {x}'); return False
    return True

def expand(tok):
    m = re.fullmatch(r'u(\d+)-u(\d+)', tok)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return [f'u{i}' for i in range(a, b + 1)]
    return [tok]

def utext(u, with_label=True):
    t = u.get('t', '')
    if with_label and u.get('h'): return u['h'] + ' ' + t
    return t

SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z“"(\[0-9])')
def split_long(html):
    """cut a long paragraph at sentence ends into pieces of roughly 25-50 words"""
    p = plain(html)
    if len(p.split()) <= SPLIT_OVER: return [html]
    cuts = [m.start() for m in SENT.finditer(p)]
    pieces, start, last = [], 0, 0
    words_at = lambda i: len(p[:i].split())
    chosen = []
    for c in cuts:
        if words_at(c) - words_at(last) >= 30 and len(p[c:].split()) >= 15:
            chosen.append(c); last = c
    if not chosen: return [html]
    out = []; rest = html; offset = 0
    for c in chosen:
        a, b = split_html(rest, c - offset + 1)  # include the space
        out.append(a); rest = b; offset = c + 1
    out.append(rest)
    return [x for x in out if plain(x).strip()]

def plus_cuts(html):
    """plain-text positions and bracket depth of Perry's ' + ' joins"""
    p = plain(html); d = 0; cuts = []
    for i, ch in enumerate(p):
        if ch in '([': d += 1
        elif ch in ')]': d = max(0, d - 1)
        elif p[i:i+3] == ' + ': cuts.append((i, d))
    return cuts

def plus_split(html, spec):
    """'+' joins become line breaks (one point shown as a list) or, marked '!', start a new point.
    spec: '' or '*' = every top-level '+' is a line break; numbers (1-based over all '+') pick joins; '!N' = new point.
    Returns a list of points, each a list of pieces. The '+' itself is the only thing removed."""
    cuts = plus_cuts(html); kinds = {}
    toks = [x for x in spec.split('.') if x] or ['*']
    for x in toks:
        if x in ('*', '+'):
            for k, (pos, d) in enumerate(cuts, 1):
                if d == 0: kinds.setdefault(k, 'br' if x == '*' else 'pt')
        elif x.startswith('!'): kinds[int(x[1:])] = 'pt'
        else: kinds[int(x)] = 'br'
    for k in kinds:
        if not 1 <= k <= len(cuts): err(f'plus join {k} not in line ({len(cuts)} joins)')
    sel = [(cuts[k-1][0], kinds[k]) for k in sorted(kinds) if 1 <= k <= len(cuts)]
    if not sel: err('no top-level + join to cut in: ' + plain(html)[:70])
    points = [[]]; rest = html; offset = 0
    for c, kind in sel:
        a_, b_ = split_html(rest, c - offset)
        points[-1].append(a_); b_ = re.sub(r'^((?:<[^>]+>)*)\+\s*', r'\1', b_)
        if kind == 'pt': points.append([])
        offset = c + 3; rest = b_
    points[-1].append(rest)
    return [[x for x in pt if plain(x).strip()] for pt in points]

def as_list(pieces):
    if len(pieces) == 1: return pieces[0]
    return '<span class="lst">' + '<br>'.join(f'<span class="li">{x}</span>' for x in pieces) + '</span>'

def sent_split(html):
    """cut at every sentence end of Perry's (for lines that mix two ideas, e.g. challenges then way forward)"""
    p = plain(html); cuts = [m.start() for m in SENT.finditer(p)]
    out = []; rest = html; offset = 0
    for c in cuts:
        a, b = split_html(rest, c - offset + 1); out.append(a); rest = b; offset = c + 1
    out.append(rest)
    return [x for x in out if plain(x).strip()]

used = {}
cards_by_topic = {i: [] for i in range(len(D['topics']))}
for f in sorted(glob.glob('spec/*.txt')):
    for ln, line in enumerate(open(f), 1):
        line = line.split('#', 1)[0].rstrip() if not line.lstrip().startswith('C ') else line.rstrip()
        if not line.strip() or not line.lstrip().startswith('C '): continue
        where = f'{f}:{ln}'
        try:
            _, roles, title, items = [x.strip() for x in re.split(r'\s*\|\s*', 'X|' + line.strip()[2:], maxsplit=3)]
        except ValueError:
            err(f'{where}: bad line'); continue
        roles = roles.split('+')
        for r in roles:
            if r not in ROLES: err(f'{where}: unknown role {r}')
        toks = []
        for tok in items.split():
            toks += expand(tok)
        rows = []; topics_here = set(); first_node = None; row_nodes = []
        last_node = [None]
        def use(x):
            if not uid_ok(x): return None
            if x in used: err(f'{where}: {x} already used at {used[x]}')
            used[x] = where; topics_here.add(TOPIC_OF[x])
            last_node[0] = U[x]['node']
            return U[x]
        # title
        card_title = None
        if title.startswith('l:'):
            if uid_ok(title[2:]): card_title = U[title[2:]].get('h') or err(f'{where}: {title} has no label')
        elif re.fullmatch(r'u\d+', title):
            u = use(title)
            if u: card_title = u.get('sec') or utext(u); first_node = u['node']
        elif title.startswith('@N'):
            nk = int(title[2:]); card_title = (NODEPATH.get(nk) or [None])[-1] or clean_inline(nodes[nk]['title'])
        elif title != '-':
            err(f'{where}: bad title {title}')
        for tok in toks:
            while len(row_nodes) < len(rows): row_nodes.append(last_node[0])
            if tok.startswith('h:'):
                u = use(tok[2:])
                if u: rows.append({'sec': u.get('sec') or utext(u)}); first_node = first_node or u['node']
                continue
            keep = tok.startswith('k:')
            if keep: tok = tok[2:]
            persent = tok.endswith('/s')
            if persent: tok = tok[:-2]
            plus = None
            mp = re.search(r'/\+([\d.!*+]*)$', tok)
            if mp: plus = mp.group(1); tok = tok[:mp.start()]
            if '>' in tok:   # A>B: Perry's short line A becomes the label shown before point B
                a, b = tok.split('>')
                persent_b = b.endswith('/s'); b = b[:-2] if persent_b else b
                plus_b = None
                mp = re.search(r'/\+([\d.!*+]*)$', b)
                if mp: plus_b = mp.group(1); b = b[:mp.start()]
                ua, ub = use(a), use(b)
                if ua and ub:
                    first_node = first_node or ua['node']
                    lab = ua.get('sec') or utext(ua)
                    body = utext(ub)
                    pieces = [as_list(pt) for pt in plus_split(body, plus_b)] if plus_b is not None else sent_split(body) if persent_b else split_long(body)
                    for k, pc in enumerate(pieces):
                        rows.append({'h': lab, 't': pc} if k == 0 else {'t': pc, 'cont': 1})
                continue
            if '&' in tok or '+' in tok:
                parts = re.split(r'([&+])', tok); us = []
                for x in parts[::2]:
                    u = use(x)
                    if u: us.append(u)
                if not us: continue
                first_node = first_node or us[0]['node']
                if '+' in tok:
                    lead = us[0]
                    lines = [utext(x, x is not lead) for x in us]
                    body = '<span class="lst">' + '<br>'.join(f'<span class="li">{x}</span>' for x in lines) + '</span>'
                    rows.append({'h': lead['h'], 't': body} if lead.get('h') else {'t': body})
                else:
                    body = us[0].get('t', '') + ''.join(' ' + utext(x) for x in us[1:])
                    rows.append({'h': us[0]['h'], 't': body} if us[0].get('h') else {'t': body})
                continue
            u = use(tok)
            if not u: continue
            first_node = first_node or u['node']
            if 'sec' in u: rows.append({'sec': u['sec']})
            elif 'img' in u: rows.append({'img': u['img']})
            elif 'video' in u: rows.append({'video': u['video']})
            elif 'table' in u:
                hdr = u['hdr']; head = u['table'][0] if hdr else None
                body = u['table'][1:] if hdr else u['table']
                rows.append({'_table': True, 'head': [plain(h).strip() for h in head] if head else None,
                             'rows': table_rows({'head': head, 'rows': body})})
            else:
                pieces = [as_list(pt) for pt in plus_split(u['t'], plus)] if plus is not None else [u['t']] if keep else sent_split(u['t']) if persent else split_long(u['t'])
                for k, pc in enumerate(pieces):
                    r = {'t': pc}
                    if k == 0 and u.get('h'): r['h'] = u['h']
                    if k > 0: r['cont'] = 1
                    rows.append(r)
        while len(row_nodes) < len(rows): row_nodes.append(last_node[0])
        if len(topics_here) > 1: err(f'{where}: units from more than one topic')
        if not topics_here: err(f'{where}: empty card'); continue
        ti = topics_here.pop()
        cards_by_topic[ti].append({'roles': roles, 'title': card_title, 'node': first_node, 'rows': rows, 'where': where, 'nodes': row_nodes})

done_subj = {D['topics'][TOPIC_OF[x]]['subj'] for x in used}
missing = [u['id'] for u in D['units'] if u['id'] not in used and (not PARTIAL or D['topics'][TOPIC_OF[u['id']]]['subj'] in done_subj)]
if missing: err(f'{len(missing)} units not placed: ' + ' '.join(missing[:60]))
if errors:
    print('\n'.join(errors[:80])); print(len(errors), 'problems'); sys.exit(1)

# ---------- assemble the deck ----------
DECK = {'subjects': [], 'topics': []}
seen_s = []
for t in D['topics']:
    if t['subj'] not in seen_s: seen_s.append(t['subj'])
subjects = [k for k, n in enumerate(nodes) if n['depth'] == 0]
for si, sk in enumerate(subjects):
    DECK['subjects'].append({'id': f's{si+1:02d}', 'name': clean_inline(nodes[sk]['title'])})
used_t = set()
for ti, t in enumerate(D['topics']):
    tid = slug(nodes[t['node']]['title']); b = tid; n_ = 2
    while tid in used_t: tid = f'{b}-{n_}'; n_ += 1
    used_t.add(tid)
    topic = {'id': tid, 'subj': t['subj'], 'name': t['name'], 'cards': []}
    if t.get('circle'): topic['circle'] = t['circle']
    if t.get('pyq'): topic['pyq'] = t['pyq']
    if t.get('group'): topic['group'] = t['group']
    ids = set()
    for c in cards_by_topic[ti]:
        path = NODEPATH.get(c['node'], [])
        out_rows = []
        shown = {c['node']}
        for r, nd in zip(c['rows'], c['nodes']):
            if nd is not None and nd not in shown:
                shown.add(nd)
                p_ = NODEPATH.get(nd, [])
                if p_ and p_[-1] != c['title'] and not (len(p_) <= len(path) and p_ == path[:len(p_)]):
                    # Perry's toggle name for these lines (keeps every toggle title on a card)
                    out_rows.append({'sec': p_[-1], 'tg': 1})
            if r.get('_table'):
                c['table'] = 1; c['head'] = r['head']; out_rows += r['rows']
            else:
                out_rows.append(r)
        for r in out_rows:   # tidy line breaks at the very start or end of a point (no words touched)
            for k in ('t', 'h'):
                if k in r: r[k] = re.sub(r'^(\s*<br>\s*)+|(\s*<br>\s*)+$', '', r[k]).strip()
        card = {'path': path, 'roles': c['roles'], 'rows': out_rows}
        if c['title']: card['title'] = c['title']
        if c.get('table'):
            card['table'] = 1
            if c.get('head'): card['head'] = c['head']
        base = f"{tid}:{c['roles'][0]}-{slug(c['title'] or (path[-1] if path else 'main'))}"
        cid = base; n_ = 2
        while cid in ids: cid = f'{base}-{n_}'; n_ += 1
        ids.add(cid); card['id'] = cid
        card['v'] = hashlib.md5(json.dumps(out_rows, ensure_ascii=False).encode()).hexdigest()[:6]
        topic['cards'].append(card)
    if topic['cards']: DECK['topics'].append(topic)
json.dump(DECK, open('deck.json', 'w'), ensure_ascii=False)
n = sum(len(t['cards']) for t in DECK['topics'])
from collections import Counter
pts = Counter(min(sum(1 for r in c['rows'] if 't' in r), 14) for t in DECK['topics'] for c in t['cards'])
print('cards', n, 'units placed', len(used), 'of', len(U), '| points per card', sorted(pts.items()))
