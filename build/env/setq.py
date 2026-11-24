"""python3 setq.py 'card-id=new question' ... : replace question fronts in fronts/*.txt"""
import glob,sys
fix=dict(a.split('=',1) for a in sys.argv[1:]); done=set()
for f in sorted(glob.glob('fronts/*.txt')):
    L=open(f).read().split('\n')
    for i,l in enumerate(L):
        k=l.split(' | ',1)[0]
        if k in fix: L[i]=k+' | '+fix[k]; done.add(k)
    open(f,'w').write('\n'.join(L))
miss=set(fix)-done; assert not miss, miss; print('questions changed',len(done))
