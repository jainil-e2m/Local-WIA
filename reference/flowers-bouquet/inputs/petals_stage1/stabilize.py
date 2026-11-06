"""Undo the source camera zoom on the petal layer: scale each RGBA frame by 1/scale about the bouquet centre and
shift the bouquet centroid back to the static reference, so petal sizes and the empty bouquet disc match the static base."""
import numpy as np, os, json
from PIL import Image
from scipy import ndimage as ndi
OUT=os.path.dirname(os.path.abspath(__file__))
T=json.load(open(os.path.join(OUT,"bouquet_transform.json")))
cx0,cy0=T["ref_center_xy"]
os.makedirs(os.path.join(OUT,"layer_stab"),exist_ok=True)
SKY=np.array([0xe0,0xdf,0xe2],np.float32)
tiles=[]
for e in T["per_frame"]:
    f=e["f"]; s=e["scale"]; cx,cy=e["cx"],e["cy"]
    im=np.asarray(Image.open(os.path.join(OUT,"layer",f"petals_{f:03d}.png"))).astype(np.float32)
    # output pixel (y,x) samples input at  c_in + s*(out - c_ref)   (scale factor s maps ref-space to source-space)
    mat=np.array([[s,0],[0,s]]); off=np.array([cy-s*cy0, cx-s*cx0])
    # premultiply for correct interpolation
    a=im[...,3:4]/255; pm=np.dstack([im[...,:3]*a, a])
    out=np.stack([ndi.affine_transform(pm[...,c],mat,offset=off,order=1,mode='constant',cval=0.0) for c in range(4)],-1)
    ao=np.clip(out[...,3],0,1); rgb=np.where(ao[...,None]>1e-3, out[...,:3]/np.maximum(ao,1e-3)[...,None], 0)
    rgba=np.dstack([np.clip(rgb,0,255),ao*255]).astype(np.uint8)
    Image.fromarray(rgba,"RGBA").save(os.path.join(OUT,"layer_stab",f"petals_{f:03d}.png"))
    if f in (0,40,80,120,160,200,239):
        comp=rgb*ao[...,None]+SKY*(1-ao[...,None])
        tiles.append(np.asarray(Image.fromarray(comp.astype(np.uint8)).resize((640,360),Image.LANCZOS)))
rows=[np.hstack(tiles[i:i+2]) if i+1<len(tiles) else np.hstack([tiles[i],np.full_like(tiles[i],0xe0)]) for i in range(0,len(tiles),2)]
Image.fromarray(np.vstack(rows)).save(os.path.join(OUT,"test_strip_stabilized.png")); print("stabilized strip saved")
