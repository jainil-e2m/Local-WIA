"""petals2: re-key the petal layer with a tight, colour-gated bouquet exclusion, then stabilise (inverse zoom).
Usage: key2.py masks | key f0 f1 ... | key all
Outputs (this folder): masks_raw.npy (packed per-frame source bouquet masks), mask_f236.npy, excl_stab.npy (packed,
stabilised exclusion zones), alpha_stab.npy (uint8 stack), layer/petals_%03d.png (RGBA straight alpha, stabilised).
"""
import numpy as np, os, sys, json, time
from PIL import Image
from scipy import ndimage as ndi
HERE=os.path.dirname(os.path.abspath(__file__)); PET=os.path.join(os.path.dirname(HERE),"petals")
frames=np.load(os.path.join(PET,"frames.npy"),mmap_mode='r'); n,H,W,_=frames.shape
plate=np.load(os.path.join(PET,"plate.npy")).astype(np.float32); plate_lum=plate.mean(-1)
T=json.load(open(os.path.join(PET,"bouquet_transform.json"))); CX0,CY0=T["ref_center_xy"]
# ---------------- parameters ----------------
NONBG_T=28; CLOSE_R=6             # stage-A bouquet mask: closing radius 6 glues only <12 px gaps (was 12 -> <24 px)
EXCL_DIL=5; FEATHER=8.0           # tight exclusion: dilation + alpha ramp outside it
RECON_T=9.0; RECON_PX=14          # pale bouquet fringe (metric>RECON_T) geodesically connected to the exclusion, up to 14 px, is excluded too
BORDER_FEATHER=24.0               # px alpha ramp at the source frame borders (petals fade instead of being cut by the frame edge)
RIM_W=40.0                        # rim colour gate band outside the exclusion edge
RIM_COMP_MIN_FRAC=0.40            # component-level kill if < this fraction of its rim pixels are petal-coloured
LOW,HIGH=7.0,26.0; HYST_HIGH=16.0; MIN_AREA=40
SHADOW_ATTEN=0.0                  # bouquet floats over a sky: no petal cast shadows
ALPHA_FLOOR=0.30; FLOOR_MIN_METRIC=22.0; ALPHA_FLOOR_INTERIOR=0.60   # interior (>3 px from the region edge) of strong regions: fills mottled pale petal cores, keeps edges soft
NEUTRAL_CHROMA=5.0; SMUDGE_AREA=3000; SMUDGE_MAX_METRIC=30.0; SMUDGE_ATTEN=0.08
UNPREMUL_FLOOR=0.5
SOFT_R=30; SOFT_GMAX=2.2; SOFT_MAX_METRIC=40.0; SHADOW_ZONE_LUM=228.0
SPARKLE_XY=(1161,581); SPARKLE_R=24
# --------------------------------------------
def disk(r):
    y,x=np.ogrid[-r:r+1,-r:r+1]; return (x*x+y*y)<=r*r
def bouquet_mask(fr):
    d=np.abs(fr.astype(np.int16)-plate.astype(np.int16)).max(-1); nb=d>NONBG_T
    nb=ndi.binary_closing(nb,structure=disk(CLOSE_R),border_value=0)
    lab,k=ndi.label(nb)
    if k==0: return np.zeros((H,W),bool)
    idx=range(1,k+1); sizes=ndi.sum(nb,lab,idx); cms=ndi.center_of_mass(nb,lab,idx)
    best=max(range(k),key=lambda i: sizes[i]*(1.0 if np.hypot(cms[i][0]-H/2,cms[i][1]-W/2)<300 else 0.2))
    return ndi.binary_fill_holes(lab==best+1)
def pack(m): return np.packbits(m,axis=-1)
def unpack(p): return np.unpackbits(p,axis=-1)[...,:W].astype(bool)
def stab_affine(img, f, order=1):
    """map source-space image to stabilised space: out(p) = in(c_f + s*(p - c_ref))"""
    e=T["per_frame"][f]; s=e["scale"]; cx,cy=e["cx"],e["cy"]
    mat=np.array([[s,0],[0,s]]); off=np.array([cy-s*CY0, cx-s*CX0])
    if img.ndim==2: return ndi.affine_transform(img,mat,offset=off,order=order,mode='constant',cval=0.0)
    return np.stack([ndi.affine_transform(img[...,c],mat,offset=off,order=order,mode='constant',cval=0.0) for c in range(img.shape[-1])],-1)

def petal_colour_gate(col):
    R,G,B=col[...,0],col[...,1],col[...,2]; V=col.max(-1); ch=V-col.min(-1)
    green=(G>R+8)&(G>B+8)
    grey=(ch<6)&(V<205)
    blue=B>R+15
    white=(ch<14)&(V>205)
    cream=(ch<24)&(V>185)&(R>=G-2)&(G>=B-2)     # shaded warm cream (petal underside)
    return (blue|white|cream)&~green&~grey

def key_frame(f, masks, gate=True):
    fr=np.asarray(frames[f]).astype(np.float32); d=fr-plate; ad=np.abs(d)
    metric=ad.max(-1); chroma=np.abs(d[...,2]-d[...,0])+np.abs(d[...,1]-d[...,0]); metric=metric+0.5*chroma
    metric=ndi.uniform_filter(metric,3)
    low=metric>LOW; lab,k=ndi.label(low); a=np.zeros((H,W),np.float32)
    if k:
        idx=np.arange(1,k+1); mx=ndi.maximum(metric,lab,idx); area=ndi.sum(low,lab,idx)
        w=ad.max(-1); cw=ndi.sum(chroma*w,lab,idx)/np.maximum(ndi.sum(w,lab,idx),1e-6)
        keep=np.zeros(k+1,bool); keep[1:]=(mx>HYST_HIGH)&(area>=MIN_AREA)
        strong=np.zeros(k+1,bool); strong[1:]=mx>FLOOR_MIN_METRIC
        smudge=np.zeros(k+1,bool); smudge[1:]=(cw<NEUTRAL_CHROMA)&((area>SMUDGE_AREA)|(mx<SMUDGE_MAX_METRIC))
        region=ndi.binary_fill_holes(keep[lab])
        a=np.clip((metric-LOW)/(HIGH-LOW),0,1)
        a=np.where(region&strong[lab],np.maximum(a,ALPHA_FLOOR),a)*region
        interior=ndi.binary_erosion(region,structure=disk(3))
        a=np.where(interior&strong[lab],np.maximum(a,ALPHA_FLOOR_INTERIOR),a)
        a=np.where(smudge[lab],a*SMUDGE_ATTEN,a)
    gy,gx=np.gradient(ndi.gaussian_filter(metric,1.5)); g=np.hypot(gy,gx)
    soft=(ndi.maximum_filter(g,size=2*SOFT_R+1)<SOFT_GMAX)&(metric<SOFT_MAX_METRIC)
    a=np.where(soft,a*SMUDGE_ATTEN,a)
    unc=(plate_lum<SHADOW_ZONE_LUM)&(d.min(-1)>-4)&(chroma<8)&(metric<30)
    a=np.where(unc,a*0.1,a)
    neutral=(d.max(-1)<0)&(d.min(-1)>-50)&(np.abs(d[...,2]-d[...,0])<7)&(np.abs(d[...,1]-d[...,0])<7)
    a=np.where(neutral,a*SHADOW_ATTEN,a)
    a=ndi.gaussian_filter(a,0.8)
    # ---- tight feathered exclusion ----
    E0=ndi.binary_dilation(masks[f],structure=disk(EXCL_DIL))
    grow=E0|(metric>RECON_T); E=E0.copy()
    for _ in range(RECON_PX): E=ndi.binary_dilation(E)&grow
    distE=ndi.distance_transform_edt(~E)
    a=a*np.clip(distE/FEATHER,0,1)
    by,bx=np.ogrid[:H,:W]; border=np.minimum(np.minimum(bx,W-1-bx),np.minimum(by,H-1-by)).astype(np.float32)
    a=a*np.clip(border/BORDER_FEATHER,0,1)
    # colour recovery (un-premultiply against plate)
    with np.errstate(all='ignore'):
        col=np.clip(plate+d/np.maximum(a,UNPREMUL_FLOOR)[...,None],0,255)
    # ---- rim colour gate ----
    rim=(distE>0)&(distE<=RIM_W)
    petal=petal_colour_gate(col)
    gs=ndi.gaussian_filter(petal.astype(np.float32),1.0)
    a_pre=a.copy()
    if gate: a=np.where(rim,a*gs,a)
    m=a_pre>0.25; lab2,k2=ndi.label(m)
    if k2 and gate:
        idx=np.arange(1,k2+1)
        rim_px=ndi.sum(m&rim,lab2,idx); pet_px=ndi.sum(m&rim&petal,lab2,idx)
        frac=np.where(rim_px>0,pet_px/np.maximum(rim_px,1),1.0)
        kill=np.zeros(k2+1,bool); kill[1:]=(rim_px>0)&(frac<RIM_COMP_MIN_FRAC)
        a=np.where(kill[lab2],0.0,a)
    # ---- static sparkle overlay ----
    sy,sx=np.ogrid[:H,:W]; a[(sx-SPARKLE_XY[0])**2+(sy-SPARKLE_XY[1])**2<=SPARKLE_R**2]=0
    info={'rim_alpha_removed':float((a_pre-a)[rim].sum()),'rim_alpha_pre':float(a_pre[rim].sum())}
    return a, col, E, distE, info

def stabilise(a, col, f):
    pm=np.dstack([col*a[...,None], a])
    out=stab_affine(pm,f)
    ao=np.clip(out[...,3],0,1)
    rgb=np.where(ao[...,None]>1e-3, out[...,:3]/np.maximum(ao,1e-3)[...,None], 0)
    return np.clip(rgb,0,255), ao

if __name__=="__main__":
    stage=sys.argv[1]
    if stage=="masks":
        t0=time.time(); masks=np.zeros((n,H,W),bool)
        for f in range(n): masks[f]=bouquet_mask(np.asarray(frames[f]))
        np.save(os.path.join(HERE,"masks_raw.npy"),pack(masks)); np.save(os.path.join(HERE,"mask_f236.npy"),masks[236])
        r=np.sqrt(masks.sum((1,2))/np.pi); print("equiv radius every 12:",r[::12].round(1),"time",round(time.time()-t0))
    elif stage=="key":
        masks=unpack(np.load(os.path.join(HERE,"masks_raw.npy")))
        full=(sys.argv[2]=="all")
        fl=list(range(n)) if full else [int(x) for x in sys.argv[2:]]
        os.makedirs(os.path.join(HERE,"layer"),exist_ok=True)
        if full:
            alphas=np.zeros((n,H,W),np.uint8); excl_stab=np.zeros((n,H,W),bool)
        t0=time.time(); infos=[]
        for f in fl:
            a,col,E,distE,info=key_frame(f,masks); infos.append(dict(f=f,**info))
            rgb,ao=stabilise(a,col,f)
            Image.fromarray(np.dstack([rgb,ao*255]).astype(np.uint8),"RGBA").save(os.path.join(HERE,"layer",f"petals_{f:03d}.png"))
            Es=stab_affine(E.astype(np.float32),f)>0.5
            if full:
                alphas[f]=(ao*255).astype(np.uint8); excl_stab[f]=Es
            else:
                np.save(os.path.join(HERE,f"excl_stab_{f:03d}.npy"),Es)
            if f%20==0 or not full: print("keyed",f,round(time.time()-t0),"s",flush=True)
        if full:
            np.save(os.path.join(HERE,"alpha_stab.npy"),alphas); np.save(os.path.join(HERE,"excl_stab.npy"),pack(excl_stab))
        json.dump(infos,open(os.path.join(HERE,"gate_stats.json"),"w"))
