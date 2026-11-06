p="petal_key.py"; s=open(p,encoding="utf-8").read()
a='''    if stage in("A","all"):
        masks=np.zeros((n,H,W),bool)
        for f in range(n):
            masks[f]=bouquet_mask(np.asarray(frames[f]),BG0)'''
b='''    # reference background for stages A/B: previous plate if one exists (iterative refinement), else flat 236
    pp=os.path.join(OUT,"plate.npy")
    REF=np.load(pp).astype(np.int16) if os.path.exists(pp) else np.int16(BG0)
    print("reference:", "plate.npy" if os.path.exists(pp) else "flat 236")
    if stage in("A","all"):
        masks=np.zeros((n,H,W),bool)
        for f in range(n):
            masks[f]=bouquet_mask(np.asarray(frames[f]),REF)'''
assert a in s; s=s.replace(a,b)
a2='''            d=np.abs(blk-BG0).max(-1)
            ok=(d<22)&(~excl[:,y0:y0+24])'''
b2='''            ref=REF[y0:y0+24] if REF.ndim==3 else REF
            d=np.abs(blk-ref).max(-1)
            ok=(d<22)&(~excl[:,y0:y0+24])'''
assert a2 in s; s=s.replace(a2,b2)
open(p,"w",encoding="utf-8").write(s); print("patched")
