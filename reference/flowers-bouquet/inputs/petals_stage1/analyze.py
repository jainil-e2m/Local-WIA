import numpy as np, os
from PIL import Image
from scipy import ndimage as ndi
OUT=os.path.dirname(os.path.abspath(__file__))
frames=np.load(os.path.join(OUT,"frames.npy"),mmap_mode='r'); n,H,W,_=frames.shape
alphas=np.load(os.path.join(OUT,"alpha.npy"),mmap_mode='r')
# petal counts per frame: components with alpha>0.15 and area>=250 px (a petal at 1280 scale is >=~20x15)
counts=[]; whites=[]; wal=[]
for f in range(n):
    a=alphas[f].astype(np.float32)/255
    m=a>0.15; lab,k=ndi.label(m)
    if k==0: counts.append(0); continue
    idx=np.arange(1,k+1); area=ndi.sum(m,lab,idx)
    good=idx[area>=250]; counts.append(len(good))
    if f%12==0:
        im=np.asarray(Image.open(os.path.join(OUT,"layer",f"petals_{f:03d}.png"))).astype(np.float32)
        for i in good:
            mm=lab==i; col=im[...,:3][mm].mean(0)
            if col.mean()>200 and (col[0]-col[2])>0:   # cream/white petal
                wal.append((a[mm].mean(),a[mm].max(),col.round(0).tolist(),int(mm.sum())))
counts=np.array(counts)
per_sec=[int(round(counts[s*24:(s+1)*24].mean())) for s in range(10)]
print("petals per frame (every 6):",counts[::6])
print("mean petals per second:",per_sec)
print("white petal components sampled (mean alpha, max alpha, colour, area):")
for w in wal[:25]: print("  %.2f %.2f %s %d"%w)
wa=np.array([w[0] for w in wal]); print("white petals: n=%d mean-of-mean-alpha %.2f median %.2f min %.2f"%(len(wa),wa.mean(),np.median(wa),wa.min()))
# alpha coverage per second (fraction of frame with alpha>0.15) as intensity proxy
cov=np.array([(alphas[f]>38).mean() for f in range(n)])
print("coverage per sec (%):",[round(cov[s*24:(s+1)*24].mean()*100,2) for s in range(10)])
# seam: first 24 vs last 24 frames
A0=alphas[:24].astype(np.float32).mean(0)/255; A1=alphas[-24:].astype(np.float32).mean(0)/255
print("mean alpha mass first1s %.1f last1s %.1f (in 1000px units)"%(A0.sum()/1000,A1.sum()/1000))
# overlap between frame 239 and frame 0 petals
a0=alphas[0]>38; a1=alphas[239]>38
print("frame0 petal px",a0.sum(),"frame239 petal px",a1.sum(),"overlap",(a0&a1).sum())
# petal positions frame 0 & 239 (centroids of comps>=250)
for f in [0,239]:
    m=alphas[f]>38; lab,k=ndi.label(m); idx=np.arange(1,k+1); area=ndi.sum(m,lab,idx); g=idx[area>=250]
    cms=ndi.center_of_mass(m,lab,g); print("frame",f,"centroids (y,x):",[(int(c[0]),int(c[1])) for c in cms])
# motion: how far do petals move per frame? compare centroid drift frames 0->6 rough via cross-correlation of alpha maps (global)
# simple: mean abs displacement estimate via best shift in +-30px for the frame 230 vs 239 alpha maps
def best_shift(a,b,r=30):
    best=(1e18,0,0)
    A=a[::4,::4].astype(np.float32); B=b[::4,::4].astype(np.float32)
    for dy in range(-r//4,r//4+1):
        for dx in range(-r//4,r//4+1):
            s=((np.roll(np.roll(A,dy,0),dx,1)-B)**2).sum()
            if s<best[0]: best=(s,dy*4,dx*4)
    return best[1:]
print("global best shift 230->239 (9 frames):",best_shift(alphas[230]>38,alphas[239]>38))
print("global best shift 0->9:",best_shift(alphas[0]>38,alphas[9]>38))
# how many petals in last 1s are exiting vs. how many appear in first second?
print("counts last 24 frames:",counts[-24:]); print("counts first 24 frames:",counts[:24])
# zoom segment: excluded area per frame (fraction) every 12
excl=np.load(os.path.join(OUT,"bouquet_masks.npy"))
ex=np.unpackbits(excl,axis=-1)[...,:W].sum((1,2))/(H*W)
print("excluded fraction per frame (every 12):",np.round(ex[::12]*100,1))
# petal size stats per second (median comp area)
med=[]
for s in range(10):
    ar=[]
    for f in range(s*24,(s+1)*24,4):
        m=alphas[f]>38; lab,k=ndi.label(m); idx=np.arange(1,k+1); area=ndi.sum(m,lab,idx); ar+=list(area[area>=250])
    med.append(int(np.median(ar)) if ar else 0)
print("median petal area px per second:",med)
