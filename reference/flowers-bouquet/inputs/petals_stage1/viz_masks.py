import numpy as np, os
from PIL import Image
OUT=os.path.dirname(os.path.abspath(__file__))
frames=np.load(os.path.join(OUT,"frames.npy"),mmap_mode='r'); n,H,W,_=frames.shape
raw=np.unpackbits(np.load(os.path.join(OUT,"bouquet_masks_raw.npy")),axis=-1)[...,:W].astype(bool)
excl=np.unpackbits(np.load(os.path.join(OUT,"bouquet_masks.npy")),axis=-1)[...,:W].astype(bool)
tiles=[]
for f in [0,60,110,130,150,200]:
    fr=np.asarray(frames[f]).astype(np.float32)
    ring=excl[f]&~raw[f]
    v=fr.copy(); v[raw[f]]=v[raw[f]]*0.5+np.array([255,0,0])*0.5; v[ring]=v[ring]*0.5+np.array([0,255,0])*0.5
    tiles.append(np.asarray(Image.fromarray(v.astype(np.uint8)).resize((520,293))))
grid=np.vstack([np.hstack(tiles[:3]),np.hstack(tiles[3:])])
Image.fromarray(grid).save(os.path.join(OUT,"masks_viz.png"))
valid=np.load(os.path.join(OUT,"plate_valid.npy"))
Image.fromarray((valid*255).astype(np.uint8)).resize((640,360)).save(os.path.join(OUT,"plate_valid_small.png"))
