p="petal_key.py"; s=open(p,encoding="utf-8").read()
i0=s.index('    if stage in("C","all"):'); s=s[:i0]
s+='''    if stage in("C","all"):
        plate=np.load(os.path.join(OUT,"plate.npy"))
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
'''
s=s.replace('SHADOW_ATTEN=0.35 # alpha multiplier for neutral, mild darkening (petal cast shadows)',
'''SHADOW_ATTEN=0.35 # alpha multiplier for neutral, mild darkening (petal cast shadows)
ALPHA_FLOOR=0.30  # min alpha inside a strong petal region (fills pale interiors of white petals)
FLOOR_MIN_METRIC=22.0
NEUTRAL_CHROMA=5.0    # component mean chroma below this = grey (bouquet shadow drift, rim leakage)
SMUDGE_AREA=3000; SMUDGE_MAX_METRIC=30.0; SMUDGE_ATTEN=0.08
FEATHER=28.0      # px ramp outside the exclusion mask so petals fade in from under the bouquet
UNPREMUL_FLOOR=0.5''')
open(p,"w",encoding="utf-8").write(s); print("patched")
