p="petal_key.py"; s=open(p,encoding="utf-8").read()
a='''            a=np.where(soft,a*SMUDGE_ATTEN,a)
'''
b='''            a=np.where(soft,a*SMUDGE_ATTEN,a)
            # uncovered static-shadow zone: during the zoom the bouquet's cast shadow moves, exposing plate pixels that
            # are in shadow in the median -> brighter, neutral, low-contrast patches. Only where the plate is itself dark.
            unc=(plate_lum<SHADOW_ZONE_LUM)&(d.min(-1)>-4)&(chroma<8)&(metric<30)
            a=np.where(unc,a*0.1,a)
'''
assert a in s; s=s.replace(a,b)
s=s.replace('        plate=np.load(os.path.join(OUT,"plate.npy"))\n        excl=np.unpackbits(np.load(os.path.join(OUT,"bouquet_masks.npy")),axis=-1)[...,:W].astype(bool)\n        os.makedirs(os.path.join(OUT,"layer"),exist_ok=True)',
            '        plate=np.load(os.path.join(OUT,"plate.npy")); plate_lum=plate.mean(-1)\n        excl=np.unpackbits(np.load(os.path.join(OUT,"bouquet_masks.npy")),axis=-1)[...,:W].astype(bool)\n        os.makedirs(os.path.join(OUT,"layer"),exist_ok=True)')
assert "plate_lum=plate.mean(-1)" in s
s=s.replace("SOFT_R=30; SOFT_GMAX=2.2; SOFT_MAX_METRIC=40.0","SOFT_R=30; SOFT_GMAX=2.2; SOFT_MAX_METRIC=40.0\nSHADOW_ZONE_LUM=228.0")
open(p,"w",encoding="utf-8").write(s); print("patched")
