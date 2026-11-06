import numpy as np, os
from PIL import Image
from scipy import ndimage as ndi
OUT=os.path.dirname(os.path.abspath(__file__))
frames=np.load(os.path.join(OUT,"frames.npy"),mmap_mode='r')
n,H,W,_=frames.shape
BG=236.0
# background-like per pixel per frame: max channel abs diff < 20
plate=np.zeros((H,W,3),np.float32); cnt=np.zeros((H,W),np.int32)
# process in row chunks to keep memory sane
acc=[]
for y0 in range(0,H,24):
    blk=np.asarray(frames[:,y0:y0+24]).astype(np.int16)   # n,90,W,3
    d=np.abs(blk-236).max(-1)  # n,90,W
    bgm=d<20
    cnt[y0:y0+24]=bgm.sum(0)
    # masked median: set non-bg to nan and nanmedian
    b=blk.astype(np.float32); b[~bgm]=np.nan
    with np.errstate(all='ignore'):
        plate[y0:y0+24]=np.nanmedian(b,axis=0)
    pass
np.save(os.path.join(OUT,"plate_raw.npy"),plate); np.save(os.path.join(OUT,"plate_cnt.npy"),cnt)
valid=cnt>=12
print("pixels with >=12 bg samples:",valid.mean())
# fill holes (bouquet core) with smooth surface: fit 2D quadratic per channel on valid pixels, then blend
yy,xx=np.mgrid[0:H,0:W]; X=(xx/W-0.5); Y=(yy/H-0.5)
A=np.stack([np.ones_like(X),X,Y,X*X,Y*Y,X*Y],-1)
sub=valid & (np.random.default_rng(0).random((H,W))<0.05)
fit=np.zeros_like(plate)
for c in range(3):
    coef,*_=np.linalg.lstsq(A[sub],plate[...,c][sub],rcond=None)
    fit[...,c]=A@coef
    print("chan",c,"quad coef",np.round(coef,2))
full=plate.copy(); full[~valid]=fit[~valid]
# smooth the seam: feather filled area
full=np.where(valid[...,None],plate,ndi.gaussian_filter(full,(6,6,0)))
np.save(os.path.join(OUT,"plate.npy"),full)
Image.fromarray(np.clip(full,0,255).astype(np.uint8)).save(os.path.join(OUT,"plate.png"))
# uniformity metrics on valid area
v=plate[valid]
print("plate valid: mean",v.mean(0),"std",v.std(0),"min",v.min(0),"max",v.max(0))
print("quad fit range (vignette/gradient) per chan:",[(fit[...,c][valid].min(),fit[...,c][valid].max()) for c in range(3)])
# corners vs centre-ish ring
lum=plate.mean(-1)
print("corner mean",lum[:60,:60].mean(),lum[:60,-60:].mean(),lum[-60:,:60].mean(),lum[-60:,-60:].mean(),"edge mid",lum[300:420,:60].mean(),lum[300:420,-60:].mean())
# temporal noise: bg pixels residual to plate over frames (sample rows)
res=[]
for f in range(0,n,10):
    fr=np.asarray(frames[f]).astype(np.float32)
    d=fr-full
    m=valid & (np.abs(d).max(-1)<20)
    res.append(d[m])
res=np.concatenate(res)
print("temporal residual std per chan",res.std(0),"p99 of max-abs",np.percentile(np.abs(res).max(-1),99),"p99.9",np.percentile(np.abs(res).max(-1),99.9))
# save count map viz
Image.fromarray((np.clip(cnt/n,0,1)*255).astype(np.uint8)).resize((640,360)).save(os.path.join(OUT,"plate_cnt.png"))
Image.fromarray(np.clip(full,0,255).astype(np.uint8)).resize((640,360)).save(os.path.join(OUT,"plate_small.png"))
