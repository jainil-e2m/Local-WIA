"""Petal layer keying for flowers_video.mp4.
Stage A: per-frame bouquet mask (largest central CC of non-background, closed, hole-filled, dilated).
Stage B: clean background plate = per-pixel temporal median over frames of pixels that are neither bouquet nor petal.
Stage C: per-frame petal key: metric = max channel |frame-plate| (+ chroma boost), hysteresis (low/high),
         soft alpha, colour recovery (un-premultiply against plate), shadow attenuation, bouquet region zeroed.
Outputs: plate.png/.npy, bouquet_masks.npy (packed), layer/petals_%03d.png (RGBA), alpha.npy (uint8 stack).
"""
import numpy as np, os, sys
from PIL import Image
from scipy import ndimage as ndi
OUT=os.path.dirname(os.path.abspath(__file__))
frames=np.load(os.path.join(OUT,"frames.npy"),mmap_mode='r')
n,H,W,_=frames.shape
BG0=236
# ---------------- parameters ----------------
NONBG_T=28        # stage-A threshold for "not background" (vs 236 / plate)
CLOSE_R=12        # closing radius to glue leaves/babys-breath to the body
BQ_DILATE=18      # px margin added around the source bouquet (see notes)
LOW,HIGH=7.0,26.0 # soft alpha ramp on metric (max channel abs diff)
HYST_HIGH=16.0    # a region survives only if it contains metric > HYST_HIGH
MIN_AREA=40       # px, drop tiny specks
SHADOW_ATTEN=0.35 # alpha multiplier for neutral, mild darkening (petal cast shadows)
ALPHA_FLOOR=0.30  # min alpha inside a strong petal region (fills pale interiors of white petals)
FLOOR_MIN_METRIC=22.0
NEUTRAL_CHROMA=5.0    # component mean chroma below this = grey (bouquet shadow drift, rim leakage)
SMUDGE_AREA=3000; SMUDGE_MAX_METRIC=30.0; SMUDGE_ATTEN=0.08
FEATHER=28.0      # px ramp outside the exclusion mask so petals fade in from under the bouquet
UNPREMUL_FLOOR=0.5
SOFT_R=30; SOFT_GMAX=2.2; SOFT_MAX_METRIC=40.0
SHADOW_ZONE_LUM=228.0
# --------------------------------------------
def disk(r):
    y,x=np.ogrid[-r:r+1,-r:r+1]; return (x*x+y*y)<=r*r

def bouquet_mask(fr, ref):
    d=np.abs(fr.astype(np.int16)-ref).max(-1)
    nb=d>NONBG_T
    nb=ndi.binary_closing(nb,structure=disk(CLOSE_R),border_value=0)
    lab,k=ndi.label(nb)
    if k==0: return np.zeros((H,W),bool)
    sizes=ndi.sum(nb,lab,range(1,k+1))
    # choose the component with largest area that is near centre (weighted)
    cms=ndi.center_of_mass(nb,lab,range(1,k+1))
    best=None;bs=-1
    for i,(s,cm) in enumerate(zip(sizes,cms)):
        dist=np.hypot(cm[0]-H/2,cm[1]-W/2)
        score=s*(1.0 if dist<300 else 0.2)
        if score>bs: bs=score;best=i+1
    m=lab==best
    m=ndi.binary_fill_holes(m)
    return m

if __name__=="__main__":
    stage=sys.argv[1] if len(sys.argv)>1 else "all"
    # reference background for stages A/B: previous plate if one exists (iterative refinement), else flat 236
    pp=os.path.join(OUT,"plate.npy")
    REF=np.load(pp).astype(np.int16) if os.path.exists(pp) else np.int16(BG0)
    print("reference:", "plate.npy" if os.path.exists(pp) else "flat 236")
    if stage in("A","all"):
        masks=np.zeros((n,H,W),bool)
        for f in range(n):
            masks[f]=bouquet_mask(np.asarray(frames[f]),REF)
        np.save(os.path.join(OUT,"bouquet_masks_raw.npy"),np.packbits(masks,axis=-1))
        areas=masks.sum((1,2)); print("bouquet area px per frame (every 12):",areas[::12])
        # equivalent radius
        print("equiv radius:",np.round(np.sqrt(areas/np.pi))[::12])
    if stage in("B","all"):
        masks=np.unpackbits(np.load(os.path.join(OUT,"bouquet_masks_raw.npy")),axis=-1)[...,:W].astype(bool)
        dil=disk(BQ_DILATE)
        excl=np.stack([ndi.binary_dilation(masks[f],structure=dil) for f in range(n)])
        np.save(os.path.join(OUT,"bouquet_masks.npy"),np.packbits(excl,axis=-1))
        plate=np.zeros((H,W),np.float32)[...,None].repeat(3,-1); cnt=np.zeros((H,W),np.int32)
        for y0 in range(0,H,24):
            blk=np.asarray(frames[:,y0:y0+24]).astype(np.int16)
            ref=REF[y0:y0+24] if REF.ndim==3 else REF
            d=np.abs(blk-ref).max(-1)
            ok=(d<22)&(~excl[:,y0:y0+24])
            cnt[y0:y0+24]=ok.sum(0)
            b=blk.astype(np.float32); b[~ok]=np.nan
            with np.errstate(all='ignore'):
                plate[y0:y0+24]=np.nanmedian(b,axis=0)
        valid=cnt>=10
        print("plate valid fraction",valid.mean())
        # normalized-convolution fill of the never-visible core (only cosmetic; that area is zeroed anyway)
        pv=np.nan_to_num(plate)*valid[...,None]
        fill=np.full_like(plate, float(np.nan_to_num(plate)[valid].mean()))
        vf=valid.astype(np.float32)
        for sg in (240,120,60,30):   # coarse to fine; finer scales overwrite where they have support
            num=ndi.gaussian_filter(pv,(sg,sg,0)); den=ndi.gaussian_filter(vf,sg)
            okd=den>0.15
            fill=np.where(okd[...,None],num/np.maximum(den,1e-3)[...,None],fill)
        full=np.where(valid[...,None],np.nan_to_num(plate),fill)
        np.save(os.path.join(OUT,"plate.npy"),full); np.save(os.path.join(OUT,"plate_valid.npy"),valid)
        Image.fromarray(np.clip(full,0,255).astype(np.uint8)).save(os.path.join(OUT,"plate.png"))
        Image.fromarray(np.clip(full,0,255).astype(np.uint8)).resize((800,450)).save(os.path.join(OUT,"plate_small.png"))
        v=full[valid]; lum=full.mean(-1)
        print("plate(valid) mean",v.mean(0).round(2),"std",v.std(0).round(2),"min",v.min(0),"max",v.max(0))
        print("lum corners TL/TR/BL/BR",lum[:60,:60].mean().round(1),lum[:60,-60:].mean().round(1),lum[-60:,:60].mean().round(1),lum[-60:,-60:].mean().round(1))
        # noise: residual to plate over bg pixels far from anything (metric<6 on smoothed)
        res=[]
        for f in range(0,n,8):
            d=np.asarray(frames[f]).astype(np.float32)-full
            m=valid&(~excl[f])&(ndi.maximum_filter(np.abs(d).max(-1),15)<12)
            res.append(d[m][::7])
        res=np.concatenate(res); am=np.abs(res).max(-1)
        print("bg temporal residual std/chan",res.std(0).round(2),"p99 maxabs",np.percentile(am,99),"p99.9",np.percentile(am,99.9),"max",am.max())
    if stage in("C","all"):
        plate=np.load(os.path.join(OUT,"plate.npy")); plate_lum=plate.mean(-1)
        excl=np.unpackbits(np.load(os.path.join(OUT,"bouquet_masks.npy")),axis=-1)[...,:W].astype(bool)
        os.makedirs(os.path.join(OUT,"layer"),exist_ok=True)
        alphas=np.zeros((n,H,W),np.uint8)
        stats=[]
        for f in range(n):
            fr=np.asarray(frames[f]).astype(np.float32)
            d=fr-plate
            ad=np.abs(d)
            metric=ad.max(-1)
            chroma=np.abs(d[...,2]-d[...,0])+np.abs(d[...,1]-d[...,0])
            metric=metric+0.5*chroma
            metric=ndi.uniform_filter(metric,3)
            low=metric>LOW
            lab,k=ndi.label(low)
            a=np.zeros((H,W),np.float32)
            if k:
                idx=np.arange(1,k+1)
                mx=ndi.maximum(metric,lab,idx)
                area=ndi.sum(low,lab,idx)
                # component-level neutrality: mean chroma weighted by |d| (grey smudges ~0, cream petals >6, blue >>)
                w=ad.max(-1)
                cw=ndi.sum(chroma*w,lab,idx)/np.maximum(ndi.sum(w,lab,idx),1e-6)
                keep=np.zeros(k+1,bool); keep[1:]=(mx>HYST_HIGH)&(area>=MIN_AREA)
                strong=np.zeros(k+1,bool); strong[1:]=mx>FLOOR_MIN_METRIC
                smudge=np.zeros(k+1,bool); smudge[1:]=(cw<NEUTRAL_CHROMA)&((area>SMUDGE_AREA)|(mx<SMUDGE_MAX_METRIC))
                region=keep[lab]; region=ndi.binary_fill_holes(region)
                a=np.clip((metric-LOW)/(HIGH-LOW),0,1)
                a=np.where(region&strong[lab],np.maximum(a,ALPHA_FLOOR),a)*region
                a=np.where(smudge[lab],a*SMUDGE_ATTEN,a)
            # per-pixel softness: very soft, low-contrast structure (bouquet shadow drifting during the zoom, rim
            # leakage) has no sharp edge within SOFT_R px; every real petal (even defocused zoom ones) does.
            gy,gx=np.gradient(ndi.gaussian_filter(metric,1.5)); g=np.hypot(gy,gx)
            soft=(ndi.maximum_filter(g,size=2*SOFT_R+1)<SOFT_GMAX)&(metric<SOFT_MAX_METRIC)
            a=np.where(soft,a*SMUDGE_ATTEN,a)
            # uncovered static-shadow zone: during the zoom the bouquet's cast shadow moves, exposing plate pixels that
            # are in shadow in the median -> brighter, neutral, low-contrast patches. Only where the plate is itself dark.
            unc=(plate_lum<SHADOW_ZONE_LUM)&(d.min(-1)>-4)&(chroma<8)&(metric<30)
            a=np.where(unc,a*0.1,a)
            # per-pixel: neutral mild darkening (petal cast shadows on the backdrop) attenuated
            neutral=(d.max(-1)<0)&(d.min(-1)>-50)&(np.abs(d[...,2]-d[...,0])<7)&(np.abs(d[...,1]-d[...,0])<7)
            a=np.where(neutral,a*SHADOW_ATTEN,a)
            a=ndi.gaussian_filter(a,0.8)
            # feathered bouquet exclusion: 0 inside the (dilated) source bouquet, ramps to 1 over FEATHER px outside
            dist=ndi.distance_transform_edt(~excl[f])
            a=a*np.clip(dist/FEATHER,0,1)
            with np.errstate(all='ignore'):
                col=plate+d/np.maximum(a,UNPREMUL_FLOOR)[...,None]
            col=np.clip(col,0,255)
            rgba=np.dstack([col,a*255]).astype(np.uint8)
            Image.fromarray(rgba,"RGBA").save(os.path.join(OUT,"layer",f"petals_{f:03d}.png"))
            alphas[f]=(a*255).astype(np.uint8)
            if f%40==0: print("keyed",f,flush=True)
        np.save(os.path.join(OUT,"alpha.npy"),alphas)
