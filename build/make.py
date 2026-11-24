import json, re, os, sys
sys.argv=[sys.argv[0]]
exec(open('build_deck.py').read().split('# ---------- build ----------')[0])
D = json.load(open('deck.json'))
# pinned box: the page title line and the Vigyan Dhara line, word for word
t = L[8].lstrip('#').strip()
m = re.match(r'SCIENCE AND TECH \((any new tech would have these problems :)\s*(.*?)\s*\)\s*,\s*(if tech is really niche then .*?)\s*\)\s*$', t)
assert m, t
lead, heads_s, niche = m.groups()
heads=[]; depth=0; cur=''
for ch in heads_s:
    if ch=='(': depth+=1
    if ch==')': depth-=1
    if ch==',' and depth==0: heads.append(cur.strip()); cur=''
    else: cur+=ch
if cur.strip(): heads.append(cur.strip())
vd = L[10].strip()
assert vd.startswith('(The Vigyan Dhara') and vd.endswith(')')
vd = vd[1:-1]
vd = vd.replace('The Vigyan Dhara Scheme', '<b>The Vigyan Dhara Scheme</b>', 1)
# check every word of the two lines is kept
src_words = words(clean_inline(L[8].lstrip('#'))) + words(clean_inline(L[10]))
got_words = words('SCIENCE AND TECH ' + lead + ' ' + ' '.join(heads) + ' ' + niche) + words(vd)
assert src_words == got_words, (src_words, got_words)
D['pin'] = {'lead': lead, 'heads': heads, 'niche': niche, 'vd': vd}
D['title'] = 'S&amp;T Flashcards'
D['subtitle'] = 'Science and Tech · 13 subjects · ' + str(len(D['topics'])) + ' topics'
imgs = {}
for f in sorted(os.listdir('img')):
    mm = re.match(r'(\d\d)\.(png|jpg|jpeg|gif|webp)$', f)
    if mm and os.path.getsize('img/'+f) > 1000: imgs[int(mm.group(1))] = 'img/' + f
skip = set(json.load(open('img_skip.json'))) if os.path.exists('img_skip.json') else set()
D['img'] = {str(k): v for k, v in imgs.items() if k not in skip}
html = open('template.html').read()
html = html.replace('/*CSS_GS3*/', open('gs3_css.css').read())
html = html.replace('/*DATA*/', json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
# the Environment & DM deck rides along (built by env/make_env.py)
ENVF = 'env/site_deck.json'
html = html.replace('/*ENVDATA*/', open(ENVF).read().replace('</', '<\\/') if os.path.exists(ENVF) else 'null')
html = html.replace('/*BUILD*/', 'updated ' + (os.environ.get('BUILD_DATE') or '24 Nov'))
os.makedirs('site', exist_ok=True)
open('site/index.html', 'w').write(html)
print('heads', heads); print('images wired', len(D['img']), 'size', len(html))
