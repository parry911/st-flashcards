"""Parse Perry's S&T Notion page (page.md, fresh fetch) into the flashcard DECK.
Word-for-word: text is only re-cut at his own breaks, never retyped."""
import re, json, sys
from html import escape

SRC = sys.argv[1] if len(sys.argv) > 1 else 'page.md'
L = open(SRC).read().split('\n')
MAXROWS = 8

# ---------- toggle tree ----------
nodes, stack = [], []
for i, l in enumerate(L):
    s = l.strip()
    if s.startswith('<toggle'):
        j = i + 1
        while not L[j].strip():
            j += 1
        n = dict(i=i, ti=j, title=L[j].strip(), depth=len(stack), kids=[], parent=stack[-1] if stack else None)
        if stack:
            nodes[stack[-1]]['kids'].append(len(nodes))
        nodes.append(n); stack.append(len(nodes) - 1)
    elif s == '</toggle>':
        nodes[stack.pop()]['end'] = i
assert not stack

# ---------- text helpers ----------
def unescape_md(s):
    s = s.replace('\\<', '&lt;').replace('\\>', '&gt;')
    return re.sub(r'\\([$~_.\-\[\]*#|+])', r'\1', s)

def clean_inline(s):
    s = s.replace('\xa0', ' ')
    s = re.sub(r'<span[^>]*>', '', s).replace('</span>', '')
    s = s.replace('<br />', '<br>')
    s = unescape_md(s)
    s = re.sub(r'<(b|i|u)>(\s*)</\1>', r'\2', s)
    return s.strip()

def plain(s):
    s = re.sub(r'<br>', ' ', s)
    s = re.sub(r'<[^>]+>', '', s)
    return s.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')

def words(s):
    return re.findall(r"[A-Za-z0-9\u00C0-\u024F\u0370-\u03FF\u0400-\u04FF]+", plain(s).lower())

TAGRE = re.compile(r'<(/?)(b|i|u)>')
def split_html(s, k):
    """split html string at plain-text index k (exclusive); balance b/i/u tags on both sides"""
    p = 0; pos = None; idx = 0
    while idx <= len(s):
        if p == k:
            pos = idx; break
        if idx == len(s): break
        if s[idx] == '<':
            e = s.index('>', idx)
            if s[idx:e+1] == '<br>': p += 1
            idx = e + 1; continue
        if s[idx] == '&':
            e = s.find(';', idx)
            if 0 < e - idx < 6:
                idx = e + 1; p += 1; continue
        idx += 1; p += 1
    if pos is None:
        pos = len(s)
    a, b = s[:pos], s[pos:]
    # move closing tags that sit right at the start of b onto a
    m = re.match(r'^((?:</(?:b|i|u)>)+)', b)
    if m:
        a += m.group(1); b = b[m.end():]
    open_ = []
    for m in TAGRE.finditer(a):
        if m.group(1):
            if open_ and open_[-1] == m.group(2): open_.pop()
        else: open_.append(m.group(2))
    a += ''.join(f'</{t}>' for t in reversed(open_))
    b = ''.join(f'<{t}>' for t in open_) + b
    a = re.sub(r'<(b|i|u)>(\s*)</\1>', r'\2', a); b = re.sub(r'<(b|i|u)>(\s*)</\1>', r'\2', b)
    return a.strip(), b.strip()

def find_label(s):
    """Perry's own label at the start of a line: 'Label: rest', 'Label - rest', 'Question? rest'."""
    p = plain(s)
    cands = []
    m = re.search(r'\s?:(?!//)', p)
    while m and m.start() > 0 and p[m.start()-1:m.start()].isdigit() and p[m.end():m.end()+1].isdigit():
        m = re.compile(r'\s?:(?!//)').search(p, m.end())
    if m: cands.append(m.end())
    m = re.search(r'\s[-–]\s', p)
    if m: cands.append(('dash', m.start(), m.end()))
    m = re.search(r'\?', p)
    if m: cands.append(('q', m.end()))
    best = None
    for c in cands:
        if isinstance(c, int):
            end = c; lab = p[:end].rstrip(':').strip(); kind = 'colon'
        elif c[0] == 'dash':
            end = c[2]; lab = p[:c[1]].strip(); kind = 'dash'
        else:
            end = c[1]; lab = p[:end].strip(); kind = 'q'
        rest = p[end:].strip()
        w = len(lab.split())
        if not rest or len(re.findall(r'\w+', rest)) < 1: continue
        if w < 1: continue
        if kind == 'colon' and w > 7: continue
        if kind == 'dash' and (w > 5 or not lab[:1].isupper()): continue
        if kind == 'q' and w > 9: continue
        if re.search(r'https?$', lab): continue
        if lab.count('(') != lab.count(')'): continue
        if kind != 'q' and '?' in lab: continue
        lab2 = re.sub(r'\b(vs|e\.g|i\.e|etc|Dr|St|No|Mr|Prof)\.', 'X', lab)
        if re.search(r'\.\s', lab2) or lab2.endswith('.'): continue
        if best is None or end < best[0]:
            best = (end, kind)
    if not best: return None
    a, b = split_html(s, best[0])
    if not plain(b).strip(): return None
    return a, b

# ---------- line classification ----------
SKIP = re.compile(r'^(<p />|<p>|</p>|</toggle>|<ul>|</ul>|<ol>|</ol>|<li[^>]*>|</li>|<callout[^>]*>|</callout>|---|<colgroup>|</colgroup>|<col[^>]*/>)$')
MARK = re.compile(r'^(- |\d+\. |\d+\\\. |\\> ?|> )')

def is_sec(raw, s):
    """Perry's own headings inside a toggle: markdown headings, all-bold/underlined lines, short 'Label:' lines."""
    if re.match(r'^#{1,4} ', raw): return True
    body = re.sub(r'^(<b>|<u>|<i>)+', '', s); body = re.sub(r'(</b>|</u>|</i>)+$', '', body)
    if s != body and '<' not in body and len(body.split()) <= 14 and '<br>' not in s and (not re.match(r'^- ', raw.strip()) or plain(s).strip().endswith(':')):
        return True
    p = plain(s).strip()
    w = len(p.split())
    if p.endswith(':') and w <= 8: return True
    if not MARK.match(raw) and w <= 5 and ':' not in p and '<br>' not in s and HEADWORDS.search(p):
        return True
    return False

HEADWORDS = re.compile(r'\b(applications?|challenges?|definitions?|characteristics|initiatives?|process|concerns?|scope|features?|status|uses|advantages?|way forward|significance|types?|components?|hurdles?|limitations?|policy|impacts?|overview|strategy|strategic|innovations?|comparison|framework|landscape|metrics|mission|properties|mechanism|support|recommendations|development|implementation|working|examples?|engineering|advances|current|future)\b', re.I)

def rows_from_line(raw):
    s = raw.strip()
    s = MARK.sub('', s, count=1)
    s = clean_inline(s)
    out = []
    chunks = [c.strip() for c in re.split(r'(?:<br>\s*){2,}', s) if plain(c).strip()]
    for k, c in enumerate(chunks):
        c = re.sub(r'^(<br>\s*)+|(\s*<br>)+$', '', c)
        lab = find_label(c) if k == 0 or True else None
        if lab:
            out.append({'h': lab[0], 't': lab[1]})
        else:
            out.append({'t': c})
    return out

def parse_table_html(i0):
    rows, cur, cell, hdr = [], None, None, False
    i = i0
    if 'header-row="true"' in L[i0]: hdr = True
    while True:
        s = L[i].strip()
        if s.startswith('<tr'): cur = []
        elif s == '</tr>': rows.append(cur); cur = None
        elif s.startswith('<td'): cell = []
        elif s == '</td>': cur.append('<br>'.join(cell)); cell = None
        elif s == '</table>': break
        elif cell is not None and s: cell.append(clean_inline(s))
        i += 1
    if not hdr and rows and all(re.fullmatch(r'(<b>.*</b>|)', c.strip()) for c in rows[0]):
        hdr = True
    if not hdr and len(rows) > 1 and all(len(plain(c).split()) <= 4 and not plain(c).strip().endswith('.') for c in rows[0]) \
       and any(len(plain(c).split()) > 6 for r in rows[1:] for c in r):
        hdr = True  # a plain first row of short column names
    return rows, hdr, i

def parse_table_pipe(i0):
    rows = []; i = i0
    while i < len(L) and L[i].strip().startswith('|'):
        cells = [clean_inline(c.strip()) for c in L[i].strip().strip('|').split('|')]
        if not all(re.fullmatch(r'-+', c) for c in cells): rows.append(cells)
        i += 1
    return rows, True, i - 1

IMGREFS = [r for _, r in json.load(open('img_refs.json'))]

def own_items(nk):
    """items in toggle nk that are not inside child toggles"""
    n = nodes[nk]
    kid_ranges = [(nodes[c]['i'], nodes[c]['end']) for c in n['kids']]
    items = []; src = []
    i = n['ti'] + 1
    while i < n['end']:
        inside = next((r for r in kid_ranges if r[0] <= i <= r[1]), None)
        if inside:
            i = inside[1] + 1; continue
        raw = L[i]; s = raw.strip()
        if not s or SKIP.match(s):
            i += 1; continue
        if s.startswith('<image'):
            m = re.search(r'source="([^"]+)"', s)
            items.append({'img': IMGREFS.index(m.group(1))}); src.append((i, 'img'))
        elif s.startswith('!['):
            src.append((i, 'stock'))  # licensed stock image: kept off the public site
        elif s.startswith('<video'):
            m = re.search(r'source="([^"]+)"', s)
            items.append({'video': m.group(1).replace('&amp;', '&')}); src.append((i, 'video'))
        elif s.startswith('<table'):
            rows, hdr, e = parse_table_html(i)
            prev = items[-1] if items else None
            if prev and 'table' in prev and src and src[-1][1] == 'table' and all(not L[k].strip() for k in range(src[-1][2] + 1, i)) \
               and len(prev['table'][0]) == len(rows[0]):
                prev['table'] += rows  # the same table, broken in two on the page: keep one header
                src[-1] = (src[-1][0], 'table', e)
            else:
                items.append({'table': rows, 'hdr': hdr}); src.append((i, 'table', e))
            i = e
        elif s.startswith('|'):
            rows, hdr, e = parse_table_pipe(i)
            items.append({'table': rows, 'hdr': hdr}); src.append((i, 'table', e)); i = e
        else:
            c = clean_inline(MARK.sub('', s, count=1))
            if is_sec(s, c):
                t = re.sub(r'^#{1,4} ', '', s) if s.startswith('#') else MARK.sub('', s, count=1)
                items.append({'sec': clean_inline(t)}); src.append((i, 'sec'))
            else:
                rr = rows_from_line(s)
                for k_, r in enumerate(rr):
                    r['_g'] = i; r['_ind'] = len(raw) - len(raw.lstrip()); r['_bul'] = bool(MARK.match(s)); r['_n'] = len(rr)
                    items.append(r)
                src.append((i, 'row'))
        i += 1
    return items, src

def slug(s):
    s = plain(clean_inline(s)).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:40].strip('-') or 'x'

# ---------- making the cards read well: headings, broken lines, short lists ----------
TERM = re.compile(r'[.;,]$')
PREPS = {'by', 'of', 'to', 'and', 'or', 'the', 'a', 'an', 'with', 'for', 'in', 'on', 'from', 'as', 'at'}
HEADSTART = re.compile(r'^(why|what|how|about|key|types? of|examples?)\b', re.I)
def pl(r): return plain(r.get('t', '')).strip()
def nwords(r): return len(pl(r).split())
def is_plain_row(r): return 't' in r and not r.get('h') and r.get('_n', 1) == 1
def allcaps(s):
    letters = [ch for ch in s if ch.isalpha()]
    return len(letters) >= 3 and sum(ch.isupper() for ch in letters) / len(letters) > 0.85

SMALL = {'a', 'an', 'the', 'and', 'or', 'of', 'in', 'on', 'for', 'to', 'by', 'with', 'as', 'at', 'vs', 'from', '&'}
def titlecase(p):
    ws = re.findall(r"[A-Za-z0-9][\w'’\-./]*", p)
    if not ws or not (ws[0][0].isupper() or ws[0][0].isdigit()) or re.search(r'[.!]$', p.strip()): return False
    big = [x for x in ws[1:] if x.lower() not in SMALL]
    if not big: return len(ws) <= 3
    return sum(1 for x in big if x[0].isupper() or x[0].isdigit()) / len(big) >= 0.75

def refine(items):
    # 1. one sentence broken over two lines on the page: keep it together in one point
    out = []
    for it in items:
        prev = out[-1] if out else None
        if prev is not None and is_plain_row(prev) and is_plain_row(it) and it.get('_g', 0) > prev.get('_g', 0):
            a = pl(prev); b = pl(it)
            last = a.split()[-1].lower() if a.split() else ''
            cont = re.search(r'[,—–-]$', a) or last in PREPS or (not re.search(r'[.?!:;)"”\]]$', a) and b[:1].islower())
            if cont and not re.search(r'[.?!]$', a):
                prev['t'] = prev['t'] + '<br>' + it['t']; prev['_n'] = 1; prev['_joined'] = True
                continue
        out.append(it)
    items = out
    # 2. a short line that introduces what follows is a heading, not a point to recall
    #    (decided from the bottom up, so a heading followed by a sub-heading is caught too)
    for k in range(len(items) - 1, -1, -1):
        it = items[k]
        if not is_plain_row(it) or it.get('_joined'): continue
        p = pl(it); w = len(p.split())
        if w == 0 or w > 12 or TERM.search(p): continue
        nxt = items[k + 1] if k + 1 < len(items) else None
        prv = items[k - 1] if k > 0 else None
        if nxt is None: continue
        tc = titlecase(p)
        strong = allcaps(p) or p.endswith(':') or (p.endswith('?') and w <= 10) or bool(HEADSTART.search(p))
        if 'sec' in nxt:
            if strong and not p.endswith('?'): it['_head'] = True
            continue
        if 't' not in nxt: continue
        if nxt.get('_head'):
            if (strong or tc or not it.get('_bul')) and not p.endswith('?'): it['_head'] = True
            continue
        if p.endswith('?') and is_plain_row(nxt) and pl(nxt).endswith('?'): continue   # a list of questions
        if w > 9 and not p.endswith(':'): continue
        in_list = prv is not None and is_plain_row(prv) and nwords(prv) <= 12 and prv.get('_ind') == it.get('_ind') and prv.get('_bul') == it.get('_bul') \
                  and not re.search(r'[:?]$', pl(prv))
        leads = bool(nxt.get('h')) or nwords(nxt) >= 13 or p.endswith(':') or \
                (nxt.get('_ind', 0) > it.get('_ind', 0) and (strong or tc))
        title_leads = tc and is_plain_row(nxt) and not titlecase(pl(nxt))
        if strong and (leads or title_leads or not it.get('_bul')): it['_head'] = True
        elif tc and (leads or title_leads) and not in_list: it['_head'] = True
        elif not it.get('_bul') and w <= 6 and (leads or title_leads) and not in_list and not re.search(r'[.?!]$', p): it['_head'] = True
    items = [{'sec': it['t'], '_fromrow': 1} if it.get('_head') else it for it in items]
    # 3. a run of short plain points (a list) opens as one point
    out = []; run = []
    def flush():
        if len(run) >= 2:
            base = run[0].get('_ind', 0)
            g = dict(run[0]); g['t'] = '<span class="lst">' + '<br>'.join(f'<span class="li{" li2" if x.get("_ind", 0) > base else ""}">{x["t"]}</span>' for x in run) + '</span>'; g['_list'] = len(run)
            out.append(g)
        else:
            out.extend(run)
        run.clear()
    for it in items:
        ok = is_plain_row(it) and nwords(it) <= 14 and not pl(it).endswith(':')
        if ok and run and it.get('_ind', 0) >= run[0].get('_ind', 0):
            run.append(it); continue
        flush()
        if ok: run.append(it)
        else: out.append(it)
    flush()
    return out

def split_parts(items):
    """cut a toggle's items into cards of about MAXROWS rows, only at Perry's headings or line breaks.
    Tables become their own cards."""
    segs = []; cur = []
    for it in items:
        if 'table' in it:
            lead = []
            while cur and 'sec' in cur[-1]:
                lead.insert(0, cur.pop())
            if cur: segs.append(('rows', cur)); cur = []
            it = dict(it); it['lead'] = lead
            segs.append(('table', it))
        else:
            cur.append(it)
    if cur: segs.append(('rows', cur))
    parts = []
    for kind, seg in segs:
        if kind == 'table':
            rows = seg['table']; hdr = seg['hdr']
            head = rows[0] if hdr else None; body = rows[1:] if hdr else rows
            n = max(1, -(-len(body) // MAXROWS)); size = -(-len(body) // n)
            for k in range(n):
                parts.append({'table': True, 'head': head, 'rows': body[k*size:(k+1)*size], 'lead': seg['lead'] if k == 0 else []})
            continue
        # sections: [sec?, items...]
        secs = []; c = []
        for it in seg:
            if 'sec' in it and c:
                secs.append(c); c = []
            c.append(it)
        if c: secs.append(c)
        merged = []; carry = []
        for sc in secs:
            if not any('t' in x for x in sc):
                carry += sc; continue
            merged.append(carry + sc); carry = []
        if carry:
            if merged: merged[-1] += carry
            else: merged.append(carry)
        secs = merged
        cur, nrow = [], 0
        def nr(lst): return sum(1 for x in lst if 't' in x)
        for si_, sc in enumerate(secs):
            k = nr(sc)
            rest = sum(nr(x) for x in secs[si_:])
            small_tail = rest <= 2 and nrow + rest <= MAXROWS + 2   # don't leave a one- or two-point card at the end
            if cur and nrow + k > MAXROWS and nrow > 0 and not small_tail:
                parts.append({'items': cur}); cur, nrow = [], 0
            if k > MAXROWS:
                # long section with no headings inside: cut evenly at Perry's own lines
                n = -(-k // MAXROWS); size = -(-k // n)
                chunk, cnt, lastg = [], 0, None
                for it in sc:
                    if 't' in it and cnt >= size and it.get('_g') != lastg:
                        parts.append({'items': cur + chunk}); cur, chunk, cnt = [], [], 0
                    chunk.append(it)
                    if 't' in it: cnt += 1; lastg = it.get('_g')
                cur, nrow = chunk, cnt
            else:
                cur += sc; nrow += k
        if cur: parts.append({'items': cur})
    # parts made only of headings/images/videos with no rows: fold into neighbour
    out = []
    for p in parts:
        if not p.get('table') and not any('t' in x for x in p['items']) and out and not out[-1].get('table'):
            out[-1]['items'] += p['items']
        elif not p.get('table') and not any('t' in x for x in p['items']) and not out:
            out.append(p)
        else:
            if out and not out[-1].get('table') and not any('t' in x for x in out[-1]['items']):
                p['items'] = out[-1]['items'] + p['items']; out[-1] = p
            else:
                out.append(p)
    return out

def table_rows(part):
    head = part['head']; rows = []
    for r in part['rows']:
        if head:
            lab = r[0]
            bits = []
            for k in range(1, len(r)):
                hl = plain(head[k]).strip() if k < len(head) else ''
                if plain(r[k]).strip():
                    bits.append((f'<span class="th">{escape(hl)}</span> ' if hl else '') + r[k])
            rows.append({'h': lab, 't': '<br>'.join(bits)} if plain(lab).strip() else {'t': '<br>'.join(bits)})
        else:
            rows.append({'h': r[0], 't': ' · '.join(c for c in r[1:] if plain(c).strip())})
    return rows

# ---------- build ----------
subjects = [k for k, n in enumerate(nodes) if n['depth'] == 0]
DECK = {'subjects': [], 'topics': []}
coverage_src = []   # (line_no, kind, card_id)
used_slugs = set()
for si, sk in enumerate(subjects):
    S = nodes[sk]
    sid = f's{si+1:02d}'
    DECK['subjects'].append({'id': sid, 'name': clean_inline(S['title'])})
    # subject-level own lines (should be none)
    it, src = own_items(sk)
    assert not [x for x in src if x[1] not in ('stock',)], ('loose lines under subject', S['title'], src)
    for tk in S['kids']:
        T = nodes[tk]
        tid = slug(T['title'])
        base = tid; n_ = 2
        while tid in used_slugs:
            tid = f'{base}-{n_}'; n_ += 1
        used_slugs.add(tid)
        topic = {'id': tid, 'subj': sid, 'name': clean_inline(T['title']), 'cards': []}
        # walk this topic toggle and all sub-toggles, depth first in page order
        carry = []
        def walk(nk, path):
            nonlocal_carry = carry
            items, src = own_items(nk)
            if nonlocal_carry:
                items = nonlocal_carry + items; nonlocal_carry.clear()
            if items and not any('t' in x for x in items) and nodes[nk]['kids']:
                # only a picture or video above the sub-toggles: show it on the first sub-toggle's card
                nonlocal_carry.extend(items); items = []
            items = refine(items)
            parts = split_parts(items) if items else []
            cslug = '/'.join(slug(nodes[p]['title']) for p in path) or 'main'
            nparts = len(parts)
            for pi, p in enumerate(parts):
                cid = f'{tid}:{cslug}' + (f'#{pi+1}' if nparts > 1 else '')
                card = {'id': cid, 'path': [clean_inline(nodes[p_]['title']) for p_ in path]}
                if nparts > 1: card['part'] = [pi + 1, nparts]
                if p.get('table'):
                    card['table'] = 1
                    if p['head']: card['head'] = [plain(h).strip() for h in p['head']]
                    card['rows'] = p['lead'] + table_rows(p)
                else:
                    card['rows'] = p['items']
                topic['cards'].append(card)
            for i_, s_ in enumerate(src):
                coverage_src.append((s_, tid, [c['id'] for c in topic['cards'][len(topic['cards'])-nparts:]] if nparts else []))
            for c in nodes[nk]['kids']:
                walk(c, path + [c])
        walk(tk, [])
        DECK['topics'].append(topic)

for t in DECK['topics']:
    for c in t['cards']:
        for r in c['rows']:
            for k in [k for k in r if k.startswith('_')]: r.pop(k)
import hashlib
for t in DECK['topics']:
    for c in t['cards']:   # content fingerprint: if a card's points change in a later build, old red/green marks are not re-applied to the wrong points
        c['v'] = hashlib.md5(json.dumps(c['rows'], ensure_ascii=False).encode()).hexdigest()[:6]
ids = [c['id'] for t in DECK['topics'] for c in t['cards']]
assert len(ids) == len(set(ids)), [x for x in ids if ids.count(x) > 1]
json.dump(DECK, open('deck.json', 'w'), ensure_ascii=False)
json.dump(coverage_src, open('coverage_src.json', 'w'))
print('subjects', len(DECK['subjects']), 'topics', len(DECK['topics']), 'cards', len(ids))
