"""apply hand decisions: python3 apply.py spec/0N.txt 'u7=/+1.2.!3.4.5' ...  (sets the split spec of a unit, keeps any k:/h: prefix)"""
import re,sys
f=sys.argv[1]; s=open(f).read()
for a in sys.argv[2:]:
    u,new=a.split('=',1)
    pat=re.compile(r'(?<!l:)(?<![\w])('+u+r')(/\+[\da.!*+]*|/s)?(?=[\s&+>]|$)', re.M)
    n=len(pat.findall(s)); assert n==1, (u,n)
    s=pat.sub(lambda m: m.group(1)+new, s)
open(f,'w').write(s); print('applied',len(sys.argv)-2)
