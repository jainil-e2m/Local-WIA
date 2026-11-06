"""rim_strip.png: 2x rim close-ups where petals emerge (source | gated layer over sky with scaled f236 base as grey | ungated).
full_strip.png: frames 0,40,80,120,160,200,239 over #e0dfe2."""
import numpy as np, os, json, sys
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import key2
HERE=key2.HERE
SKY=np.array([0xe0,0xdf,0xe2],np.float32); H,W=720,1280
rep=json.load(open(os.path.join(HERE,"report.json")))
S=np.load(os.path.join(HERE,"base_scaled_fp.npy")); dS=ndi.distance_transform_edt(~S)
edgeS=S&~ndi.binary_erosion(S,iterations=2)
masks=key2.unpack(np.load(os.path.join(HERE,"masks_raw.npy")))
def layer(f):
    im=np.asarray(Image.open(os.path.join(HERE,"layer",f"petals_{f:03d}.png"))).astype(np.float32); return im[...,:3],im[...,3]/255
def over_sky(rgb,a): return rgb*a[...,None]+SKY*(1-a[...,None])
def with_base(comp): v=comp.copy(); v[S]=128; return v
def up2(c): return np.asarray(Image.fromarray(np.clip(c,0,255).astype(np.uint8)).resize((c.shape[1]*2,c.shape[0]*2),Image.NEAREST))
near=rep["nearest_petal_px"]
# pick frames: nearest<=4, spread over the clip (one per ~24-frame bucket), prefer big visible petals
cands=[f for f in range(240) if near[f] is not None and near[f]<=4]
picked=[];
for b in range(0,240,20):
    fs=[f for f in cands if b<=f<b+20]
    if fs: picked.append(fs[len(fs)//2])
if len(sys.argv)>1: picked=[int(x) for x in sys.argv[1:]]
print("rim strip frames",picked)
rows=[]
CS=150
for f in picked:
    rgb,a=layer(f); vis=(a>=0.25)&~S
    lab,k=ndi.label(vis); idx=np.arange(1,k+1); area=ndi.sum(vis,lab,idx); mn=ndi.minimum(dS,lab,idx)
    ok=idx[(area>=300)&(mn<=6)]
    if len(ok)==0: ok=idx[np.argsort(mn)[:1]]
    i=ok[np.argmax(area[ok-1])]
    m=lab==i; pts=np.argwhere(m&(dS<=dS[m].min()+1)); py,px=pts[len(pts)//2]
    y0=int(np.clip(py-CS//2,0,H-CS)); x0=int(np.clip(px-CS//2,0,W-CS)); sl=(slice(y0,y0+CS),slice(x0,x0+CS))
    # stabilised source frame for reference
    src=key2.stab_affine(np.asarray(key2.frames[f]).astype(np.float32),f)
    gated=with_base(over_sky(rgb,a))
    a_u,col_u,E,distE,_=key2.key_frame(f,masks,gate=False); rgb_u,ao_u=key2.stabilise(a_u,col_u,f)
    ungated=with_base(over_sky(rgb_u,ao_u))
    # mark the exclusion edge (red) on the ungated panel so the exclusion vs base gap is visible
    Es=key2.stab_affine(E.astype(np.float32),f)>0.5; edgeE=Es&~ndi.binary_erosion(Es,iterations=1)
    ungated[edgeE]=(255,0,0)
    tiles=[up2(src[sl]),up2(gated[sl]),up2(ungated[sl])]
    row=np.hstack(tiles); im=Image.fromarray(row); d=ImageDraw.Draw(im)
    d.text((4,4),f"f{f:03d} nearest={near[f]:.1f}px  src | gated+base | ungated+excl edge",fill=(200,0,0))
    rows.append(np.asarray(im))
Image.fromarray(np.vstack(rows)).save(os.path.join(HERE,"rim_strip.png"))
# full strip
tiles=[]
for f in (0,40,80,120,160,200,239):
    rgb,a=layer(f); comp=over_sky(rgb,a)
    im=Image.fromarray(comp.astype(np.uint8)).resize((640,360),Image.LANCZOS); ImageDraw.Draw(im).text((6,6),f"f{f:03d}",fill=(120,0,0))
    tiles.append(np.asarray(im))
grid=[np.hstack(tiles[i:i+2]) if i+1<len(tiles) else np.hstack([tiles[i],np.full_like(tiles[i],0xe0)]) for i in range(0,len(tiles),2)]
Image.fromarray(np.vstack(grid)).save(os.path.join(HERE,"full_strip.png"))
# same frames with base region grey (for my own judgement of pops)
tiles=[]
for f in (0,40,80,120,160,200,239):
    rgb,a=layer(f); comp=with_base(over_sky(rgb,a)); comp[edgeS]=(90,90,90)
    tiles.append(np.asarray(Image.fromarray(comp.astype(np.uint8)).resize((640,360),Image.LANCZOS)))
grid=[np.hstack(tiles[i:i+2]) if i+1<len(tiles) else np.hstack([tiles[i],np.full_like(tiles[i],0xe0)]) for i in range(0,len(tiles),2)]
Image.fromarray(np.vstack(grid)).save(os.path.join(HERE,"full_strip_base.png"))
print("strips written")
