import numpy as np, os
from PIL import Image
from scipy import ndimage as ndi
OUT=os.path.dirname(os.path.abspath(__file__))
frames=np.load(os.path.join(OUT,"frames.npy"),mmap_mode='r'); n,H,W,_=frames.shape
plate=np.load(os.path.join(OUT,"plate.npy"))
alphas=np.load(os.path.join(OUT,"alpha.npy"),mmap_mode='r')
for f in [0,120,160]:
    fr=np.asarray(frames[f]).astype(np.float32); d=fr-plate; ad=np.abs(d)
    metric=ad.max(-1); chroma=np.abs(d[...,2]-d[...,0])+np.abs(d[...,1]-d[...,0]); metric=ndi.uniform_filter(metric+0.5*chroma,3)
    gy,gx=np.gradient(ndi.gaussian_filter(metric,1.5)); g=np.hypot(gy,gx)
    a=alphas[f].astype(np.float32)/255; m=a>0.02; lab,k=ndi.label(m); idx=np.arange(1,k+1)
    area=ndi.sum(m,lab,idx); w=ad.max(-1); cw=ndi.sum(chroma*w,lab,idx)/np.maximum(ndi.sum(w,lab,idx),1e-6)
    gmax=ndi.maximum(g,lab,idx); g95=[np.percentile(g[lab==i],95) for i in idx]
    mx=ndi.maximum(metric,lab,idx); mean_a=ndi.mean(a,lab,idx); cms=ndi.center_of_mass(m,lab,idx)
    print("frame",f)
    for i in np.argsort(-area)[:14]:
        print("  area %6d  cm(y,x)=(%4d,%4d) chroma %.1f maxmetric %.0f gmax %.2f g95 %.2f meanA %.2f"%(area[i],cms[i][0],cms[i][1],cw[i],mx[i],gmax[i],g95[i],mean_a[i]))
