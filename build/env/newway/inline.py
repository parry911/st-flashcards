import re, html as H
TAG=re.compile(r'<(/?)(b|i|u|s|span)((?:\s+[a-z-]+="[^"]*")*)\s*>')
W=re.compile(r"[0-9A-Za-zÀ-ɏ₀-₉'’%]")
def chars(s):
    out=[]; st={'b':0,'i':0,'u':0,'s':0}; spans=[]
    i=0
    while i<len(s):
        m=TAG.match(s,i)
        if m:
            cl,tg,at=m.groups()
            if tg=='span':
                if cl: spans.pop()
                else:
                    col=re.search(r'color="([^"]*)"',at); dis=re.search(r'discussion-urls="([^"]*)"',at)
                    spans.append({'mark':bool(col and col.group(1).endswith('_bg')),'cm':dis.group(1).split(',')[0].rsplit('/',1)[1] if dis else None})
            else: st[tg]+=(-1 if cl else 1)
            i=m.end(); continue
        c=s[i]
        if c=='\\' and i+1<len(s): c=s[i+1]; i+=1
        out.append({'c':c,'b':st['b']>0,'i':st['i']>0,'mark':any(x['mark'] for x in spans),'cm':next((x['cm'] for x in reversed(spans) if x['cm']),None),'hs':None})
        i+=1
    return out
TRIM=set(" ·+→,;:–—-&")
TRIM_END=TRIM|{"("}
TRIM_START=TRIM|{")"}
def snap(C):
    n=len(C); i=0
    while i<n:
        if not C[i]['cm']: i+=1; continue
        k=C[i]['cm']; j=i
        while j<n and C[j]['cm']==k: j+=1
        s,e=i,j
        while s>0 and C[s-1]['cm'] is None and W.match(C[s-1]['c']) and W.match(C[s]['c']): s-=1
        while e<n and C[e]['cm'] is None and W.match(C[e]['c']) and W.match(C[e-1]['c']): e+=1
        while s<e and (C[s]["c"] in TRIM_START): s+=1
        while e>s and (C[e-1]["c"] in TRIM_END): e-=1
        txt=''.join(x['c'] for x in C[s:e])
        if txt.startswith('(') and txt.count('(')>txt.count(')'): s+=1
        txt=''.join(x['c'] for x in C[s:e])
        if txt.endswith(')') and txt.count(')')>txt.count('('): e-=1
        while e>s and C[e-1]['c'] in TRIM: e-=1
        for x in C[i:j]: x['cm']=None
        for x in C[s:e]: x['cm']=k
        i=max(j,e)
    return C
def plain(C): return ''.join(x['c'] for x in C)
def render(C, cmids):
    """cmids: dict discussion-id -> short key; returns html"""
    out=[]; i=0; n=len(C)
    while i<n:
        key=(C[i]['cm'],C[i]['hs']); j=i
        while j<n and (C[j]['cm'],C[j]['hs'])==key: j+=1
        inner=fmt(C[i:j]); cm,hs=key
        if cm is not None and cm in cmids: inner=f'<span class="cm" data-c="{cmids[cm]}">{inner}</span>'
        if hs is not None: inner=f'<button class="hs" data-h="{hs}">{inner}</button>'
        out.append(inner); i=j
    return ''.join(out)
def fmt(C):
    out=[]; i=0
    while i<len(C):
        key=(C[i]['b'],C[i]['i'],C[i]['mark']); j=i
        while j<len(C) and (C[j]['b'],C[j]['i'],C[j]['mark'])==key: j+=1
        t=H.escape(''.join(x['c'] for x in C[i:j]),quote=False)
        if key[0]: t='<b>'+t+'</b>'
        if key[1]: t='<i>'+t+'</i>'
        if key[2]: t='<mark>'+t+'</mark>'
        out.append(t); i=j
    return ''.join(out)
