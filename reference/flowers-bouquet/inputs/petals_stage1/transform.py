import numpy as np, os, json
from scipy import ndimage as ndi
OUT=os.path.dirname(os.path.abspath(__file__))
W=1280
raw=np.unpackbits(np.load(os.path.join(OUT,"bouquet_masks_raw.npy")),axis=-1)[...,:W].astype(bool)
n=raw.shape[0]
cy=np.zeros(n);cx=np.zeros(n);r=np.zeros(n)
for f in range(n):
    m=raw[f]; ys,xs=np.nonzero(m); cy[f]=ys.mean(); cx[f]=xs.mean(); r[f]=np.sqrt(m.sum()/np.pi)
sm=lambda v: ndi.gaussian_filter1d(v,3,mode='nearest')
cys,cxs,rs=sm(cy),sm(cx),sm(r)
r0=np.median(rs[:48]); cy0=np.median(cys[:48]); cx0=np.median(cxs[:48])
scale=rs/r0
print("static ref: centre (y,x)=(%.1f,%.1f) radius %.1f"%(cy0,cx0,r0))
print("frame  cy   cx   r   scale")
for f in range(0,n,12): print("%3d %6.1f %6.1f %6.1f %.3f"%(f,cys[f],cxs[f],rs[f],scale[f]))
print("scale range",scale.min().round(3),scale.max().round(3),"centre drift max px",np.hypot(cys-cy0,cxs-cx0).max().round(1))
json.dump({"ref_center_xy":[float(cx0),float(cy0)],"ref_radius":float(r0),
           "per_frame":[{"f":f,"cx":float(cxs[f]),"cy":float(cys[f]),"r":float(rs[f]),"scale":float(scale[f])} for f in range(n)]},
          open(os.path.join(OUT,"bouquet_transform.json"),"w"),indent=0)
