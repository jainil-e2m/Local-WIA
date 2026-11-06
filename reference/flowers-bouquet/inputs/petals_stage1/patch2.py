p="petal_key.py"; s=open(p,encoding="utf-8").read()
a='''        pv=np.nan_to_num(plate)*valid[...,None]
        num=ndi.gaussian_filter(pv,(40,40,0)); den=ndi.gaussian_filter(valid.astype(np.float32),40)
        fill=num/np.maximum(den,1e-3)[...,None]
        full=np.where(valid[...,None],np.nan_to_num(plate),fill)'''
b='''        pv=np.nan_to_num(plate)*valid[...,None]
        fill=np.full_like(plate, float(np.nan_to_num(plate)[valid].mean()))
        vf=valid.astype(np.float32)
        for sg in (240,120,60,30):   # coarse to fine; finer scales overwrite where they have support
            num=ndi.gaussian_filter(pv,(sg,sg,0)); den=ndi.gaussian_filter(vf,sg)
            okd=den>0.15
            fill=np.where(okd[...,None],num/np.maximum(den,1e-3)[...,None],fill)
        full=np.where(valid[...,None],np.nan_to_num(plate),fill)'''
assert a in s; s=s.replace(a,b); open(p,"w",encoding="utf-8").write(s); print("patched")
