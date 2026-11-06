import numpy as np, os
from PIL import Image
OUT=os.path.dirname(os.path.abspath(__file__))
frames=np.load(os.path.join(OUT,"frames.npy"),mmap_mode='r'); plate=np.load(os.path.join(OUT,"plate.npy"))
im=np.asarray(Image.open(os.path.join(OUT,"layer","petals_120.png"))).astype(np.float32); a=im[...,3]/255
# residual smudge region in f120 crop: alpha in (0.1,0.6) & lum of colour > 200, within y 420-720 x 900-1280
reg=(a>0.1)&(a<0.7)&(im[...,:3].mean(-1)>200); reg[:420]=False; reg[:,:900]=False
ys,xs=np.nonzero(reg); print("residual px",reg.sum(),"bbox y",ys.min(),ys.max(),"x",xs.min(),xs.max())
d=np.asarray(frames[120]).astype(np.float32)-plate
print("plate lum there: mean %.1f min %.1f max %.1f"%(plate.mean(-1)[reg].mean(),plate.mean(-1)[reg].min(),plate.mean(-1)[reg].max()))
print("d mean",d[reg].mean(0).round(1),"d.min(-1) pct 10/50/90",np.percentile(d[reg].min(-1),[10,50,90]).round(1))
ch=np.abs(d[...,2]-d[...,0])+np.abs(d[...,1]-d[...,0]); print("chroma pct 10/50/90",np.percentile(ch[reg],[10,50,90]).round(1))
print("alpha pct",np.percentile(a[reg],[10,50,90]).round(2))
