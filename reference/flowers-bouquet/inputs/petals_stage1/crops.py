import numpy as np, os
from PIL import Image
OUT=os.path.dirname(os.path.abspath(__file__))
frames=np.load(os.path.join(OUT,"frames.npy"),mmap_mode='r')
SKY=np.array([0xe0,0xdf,0xe2],np.float32)
def comp(f,y0,y1,x0,x1):
    im=np.asarray(Image.open(os.path.join(OUT,"layer",f"petals_{f:03d}.png"))).astype(np.float32)[y0:y1,x0:x1]; a=im[...,3:4]/255
    return (im[...,:3]*a+SKY*(1-a)).astype(np.uint8), (a[...,0]*255).astype(np.uint8)
# smudge zones: f120 bottom-right, f160 right-middle ; show source | composite | alpha
rows=[]
for f,(y0,y1,x0,x1) in [(120,(420,720,900,1280)),(160,(420,720,900,1280)),(0,(420,720,900,1280))]:
    c,a=comp(f,y0,y1,x0,x1); src=np.asarray(frames[f])[y0:y1,x0:x1]
    rows.append(np.hstack([src,c,np.repeat(a[...,None],3,-1)]))
Image.fromarray(np.vstack(rows)).save(os.path.join(OUT,"crop_smudge_zones.png"))
# white petal edge/halo check at full res: f0 (0-200, 300-800) and f80 region with white petals
rows=[]
for f,(y0,y1,x0,x1) in [(0,(0,220,300,800)),(80,(380,600,180,680))]:
    c,a=comp(f,y0,y1,x0,x1); src=np.asarray(frames[f])[y0:y1,x0:x1]
    rows.append(np.hstack([src,c]))
Image.fromarray(np.vstack(rows)).save(os.path.join(OUT,"crop_white_halo.png"))
print([np.asarray(Image.open(os.path.join(OUT,"layer",f"petals_{f:03d}.png")))[...,3][420:720,900:1280].mean()/255 for f in (0,120,160)])
