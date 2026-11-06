import numpy as np, os
from PIL import Image
OUT=os.path.dirname(os.path.abspath(__file__))
frames=np.load(os.path.join(OUT,"frames.npy"),mmap_mode='r'); n,H,W,_=frames.shape
plate=np.load(os.path.join(OUT,"plate.npy"))
# locate sparkle: brightest pixel in plate bottom-right quadrant
q=plate[400:,900:].mean(-1); iy,ix=np.unravel_index(q.argmax(),q.shape); cy,cx=iy+400,ix+900
print("sparkle centre",cy,cx,"plate lum",q.max())
s=[np.asarray(frames[f][cy-3:cy+4,cx-3:cx+4]).mean() for f in range(n)]
print("sparkle 7x7 mean lum per frame (every 6):",np.round(s[::6],1))
# white petal alpha stats: on frame 0 layer, find components whose colour is bright (>230 lum)
from scipy import ndimage as ndi
im=np.asarray(Image.open(os.path.join(OUT,"layer","petals_000.png"))).astype(np.float32)
a=im[...,3]/255; lab,k=ndi.label(a>0.05)
for i in range(1,k+1):
    m=lab==i
    if m.sum()<150: continue
    col=im[...,:3][m].mean(0); print("comp",i,"area",m.sum(),"mean alpha %.2f max alpha %.2f"%(a[m].mean(),a[m].max()),"col",col.round(0))
# full-res crop of frame 0 layer over sky around the left white petals (x 150-500, y 200-450)
SKY=np.array([0xe0,0xdf,0xe2],np.float32)
comp=im[...,:3]*a[...,None]+SKY*(1-a[...,None])
src=np.asarray(frames[0]).astype(np.float32)
crop=np.hstack([src[150:450,100:500],comp[150:450,100:500]])
Image.fromarray(crop.astype(np.uint8)).save(os.path.join(OUT,"white_petal_compare_f0.png"))
