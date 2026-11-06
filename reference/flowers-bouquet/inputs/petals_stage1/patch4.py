p="petal_key.py"; s=open(p,encoding="utf-8").read()
a='''            # per-pixel: neutral mild darkening (petal cast shadows on the backdrop) attenuated'''
b='''            # per-pixel softness: very soft, low-contrast structure (bouquet shadow drifting during the zoom, rim
            # leakage) has no sharp edge within SOFT_R px; every real petal (even defocused zoom ones) does.
            gy,gx=np.gradient(ndi.gaussian_filter(metric,1.5)); g=np.hypot(gy,gx)
            soft=(ndi.maximum_filter(g,size=2*SOFT_R+1)<SOFT_GMAX)&(metric<SOFT_MAX_METRIC)
            a=np.where(soft,a*SMUDGE_ATTEN,a)
            # per-pixel: neutral mild darkening (petal cast shadows on the backdrop) attenuated'''
assert a in s; s=s.replace(a,b)
s=s.replace("UNPREMUL_FLOOR=0.5","UNPREMUL_FLOOR=0.5\nSOFT_R=30; SOFT_GMAX=2.2; SOFT_MAX_METRIC=40.0")
open(p,"w",encoding="utf-8").write(s); print("patched")
