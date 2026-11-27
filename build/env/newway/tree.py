import re
def ind(l): return len(l)-len(l.lstrip(' '))
def parse(L, a, b):
    """L lines; returns nodes from L[a:b]"""
    out=[]; i=a
    while i<b:
        l=L[i]
        if not l.strip(): i+=1; continue
        k=ind(l); s=l.strip()
        if s.startswith('<toggle'):
            d=0; j=i
            while True:
                t=L[j].strip()
                if t.startswith('<toggle'): d+=1
                if t.startswith('</toggle>'):
                    d-=1
                    if d==0: break
                j+=1
            m=re.search(r'heading="(h\d)"',s)
            inner=parse(L,i+1,j)
            title=''
            if inner and inner[0]['k']=='p': title=inner[0]['x']; inner=inner[1:]
            out.append({'k':'tog','h':m.group(1) if m else None,'title':title,'kids':inner,'ln':i+1}); i=j+1; continue
        if s.startswith('- '):
            j=i+1
            while j<b and (not L[j].strip() or ind(L[j])>k): j+=1
            # trim trailing blank lines
            out.append({'k':'li','x':s[2:],'kids':parse(L,i+1,j),'ln':i+1}); i=j; continue
        if s.startswith('<image'):
            m=re.search(r'source="([^"]+)"',s); out.append({'k':'img','src':m.group(1),'ln':i+1}); i+=1; continue
        if s in ('<ul>','</ul>','</li>'): i+=1; continue
        if s=='<li>':
            j=i+1; buf=[]
            while L[j].strip()!='</li>': buf.append(L[j].strip()); j+=1
            out.append({'k':'li','x':' '.join(buf),'kids':[],'ln':i+1}); i=j+1; continue
        if s.startswith('<callout'):
            j=i
            while not L[j].strip().startswith('</callout>'): j+=1
            out.append({'k':'callout','kids':parse(L,i+1,j),'ln':i+1}); i=j+1; continue
        if s.startswith('<table'):
            j=i
            while not L[j].strip().startswith('</table>'): j+=1
            out.append({'k':'table','raw':L[i:j+1],'ln':i+1}); i=j+1; continue
        out.append({'k':'p','x':s,'ln':i+1}); i+=1
    return out
