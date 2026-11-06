import numpy as np, os
from PIL import Image
from scipy import ndimage as ndi
OUT=os.path.dirname(os.path.abspath(__file__))
frames=np.load(os.path.join(OUT,"frames.npy"),mmap_mode='r'); n,H,W,_=frames.shape
plate=np.load(os.path.join(OUT,"plate.npy"))
# sparkle: search near (600,1176) for brightest plate pixel
q=plate[560:640,1130:1220].mean(-1); iy,ix=np.unravel_index(q.argmax(),q.shape); cy,cx=iy+560,ix+1130
print("sparkle centre",cy,cx,"plate lum",q.max(),"surround",plate[cy-30:cy+30,cx-30:cx+30].mean())
s=np.array([np.asarray(frames[f][cy-2:cy+3,cx-2:cx+3]).mean() for f in range(n)])
print("sparkle 5x5 lum per frame (every 4):",np.round(s[::4],0))
# where is the big grey component 16 in frame 0 layer?
im=np.asarray(Image.open(os.path.join(OUT,"layer","petals_000.png"))).astype(np.float32); a=im[...,3]/255
lab,k=ndi.label(a>0.05); sizes=ndi.sum(a>0.05,lab,range(1,k+1)); big=np.argmax(sizes)+1
ys,xs=np.where(lab==big); print("big grey comp bbox y",ys.min(),ys.max(),"x",xs.min(),xs.max())
excl=np.unpackbits(np.load(os.path.join(OUT,"bouquet_masks.npy")),axis=-1)[...,:W].astype(bool)
d=np.asarray(frames[0]).astype(np.float32)-plate
print("diff stats in big comp: mean",d[lab==big].mean(0).round(1),"min",d[lab==big].min(0))
# how does the plate look there vs frame 0 there
Image.fromarray(np.hstack([np.asarray(frames[0])[ys.min():ys.max(),xs.min():xs.max()],np.clip(plate,0,255).astype(np.uint8)[ys.min():ys.max(),xs.min():xs.max()]])).save(os.path.join(OUT,"bigcomp_f0.png"))
