"""Metrics for the petals2 stabilised layer: f236 footprint, base scale, nearest-petal distances, petal counts,
transparent bands, seam statistics. Writes report.json."""
import numpy as np, os, json, sys
from scipy import ndimage as ndi
HERE=os.path.dirname(os.path.abspath(__file__)); PET=os.path.join(os.path.dirname(HERE),"petals")
T=json.load(open(os.path.join(PET,"bouquet_transform.json"))); CX0,CY0=T["ref_center_xy"]
H,W=720,1280; n=240
alphas=np.load(os.path.join(HERE,"alpha_stab.npy"),mmap_mode='r')
excl=np.unpackbits(np.load(os.path.join(HERE,"excl_stab.npy")),axis=-1)[...,:W].astype(bool)
masks=np.unpackbits(np.load(os.path.join(HERE,"masks_raw.npy")),axis=-1)[...,:W].astype(bool)
F=np.load(os.path.join(HERE,"mask_f236.npy"))
ys,xs=np.nonzero(F); c236=(float(ys.mean()),float(xs.mean())); r236=float(np.sqrt(F.sum()/np.pi))
# source footprint radius in stabilised space (per-frame masks mapped by the inverse zoom)
def stab(img,f):
    e=T["per_frame"][f]; s=e["scale"]; cx,cy=e["cx"],e["cy"]
    return ndi.affine_transform(img,np.array([[s,0],[0,s]]),offset=np.array([cy-s*CY0,cx-s*CX0]),order=1,mode='constant',cval=0.0)
rs=[float(np.sqrt((stab(masks[f].astype(np.float32),f)>0.5).sum()/np.pi)) for f in range(0,n,6)]
src_r=float(np.median(rs))
def scaled_fp(k):
    off=np.array([c236[0]-c236[0]/k, c236[1]-c236[1]/k])
    return ndi.affine_transform(F.astype(np.float32),np.array([[1/k,0],[0,1/k]]),offset=off,order=1)>0.5
stable=list(range(0,61))+list(range(190,240))
U=np.zeros((H,W),np.int32)
for f in stable: U+=excl[f]
scan=[]
chosen=None
R50=U>=0.5*len(stable)      # robust exclusion zone: excluded in >=50% of the stable frames (drops transiently glued petals)
for k in np.round(np.arange(1.00,1.151,0.005),3):
    S=scaled_fp(k); dS=ndi.distance_transform_edt(~S)
    unc=(~S)&(U>0)
    cov=1-(U[unc].sum()/U.sum())            # pixel-weighted over stable frames, per-frame zones
    gaps=np.repeat(dS[unc],U[unc]) if unc.any() else np.zeros(1)
    mx=float(gaps.max()) if unc.any() else 0.0
    allg=np.repeat(dS[U>0],U[U>0]); p99all=float(np.percentile(allg,99))
    covR=float(1-((~S)&R50).sum()/R50.sum()); p99R=float(np.percentile(dS[R50],99)); mxR=float(dS[R50].max())
    scan.append(dict(k=float(k),coverage_perframe=round(float(cov),4),p99_gap_perframe=round(p99all,1),max_gap_perframe=round(mx,1),
                     coverage_robust=round(covR,4),p99_gap_robust=round(p99R,1),max_gap_robust=round(mxR,1),
                     overshoot_px=int((S&(U==0)).sum())))
    if chosen is None and covR>=0.99 and p99R<=5.0: chosen=float(k)
if chosen is None: chosen=1.15
auto_k=chosen
if len(sys.argv)>1: chosen=float(sys.argv[1])
K=chosen; S=scaled_fp(K); dS=ndi.distance_transform_edt(~S)
uncov_per_frame=[int((excl[f]&~S).sum()) for f in range(n)]
uncov_far=[int((excl[f]&(dS>5)).sum()) for f in range(n)]
for e in scan: print(e)
print("chosen K",K)
print("uncovered excl px per frame (every 6):",[int((excl[f]&~S).sum()) for f in range(0,n,6)])
# ---- per-frame metrics ----
A_T=64  # alpha >= 0.25
nearest=[]; counts_full=[]; counts_win=[]; bbox=[]; bands_geom=[]
X0,X1=CX0-450,CX0+450
for f in range(n):
    a=alphas[f]>=A_T
    vis=a&~S
    nearest.append(float(dS[vis].min()) if vis.any() else None)
    lab,k=ndi.label(vis)
    if k:
        idx=np.arange(1,k+1); area=ndi.sum(vis,lab,idx); good=idx[area>=150]
        cms=ndi.center_of_mass(vis,lab,good) if len(good) else []
        counts_full.append(len(good)); counts_win.append(int(sum(1 for c in cms if X0<=c[1]<=X1)))
    else: counts_full.append(0); counts_win.append(0)
    nz=alphas[f]>0
    if nz.any():
        yy,xx=np.nonzero(nz); bbox.append([int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())])
    else: bbox.append(None)
    e=T["per_frame"][f]; s=e["scale"]; cx,cy=e["cx"],e["cy"]
    # source rectangle mapped into stabilised space: x_stab = CX0 + (x_src - cx)/s
    L=CX0+(0-cx)/s; R=CX0+(W-cx)/s; Tt=CY0+(0-cy)/s; B=CY0+(H-cy)/s
    bands_geom.append([round(max(0.0,L),1),round(max(0.0,W-R),1),round(max(0.0,Tt),1),round(max(0.0,H-B),1)])  # left,right,top,bottom
near=np.array([x if x is not None else np.inf for x in nearest])
has=near<=150
p50=float(np.percentile(near[has],50)); p80=float(np.percentile(near[has],80))
within12=float((near<=12).mean()*100)
pps_full=[int(round(np.mean(counts_full[s*24:(s+1)*24]))) for s in range(10)]
pps_win=[int(round(np.mean(counts_win[s*24:(s+1)*24]))) for s in range(10)]
bg=np.array(bands_geom)
# ---- seam: frames 0-23 vs 216-239 ----
seam=[]
for i in range(24):
    a0=alphas[i]>=A_T; a1=alphas[216+i]>=A_T
    v0=a0&~S; v1=a1&~S
    inter=(v0&v1).sum(); union=(v0|v1).sum()
    seam.append(dict(head=i,tail=216+i,petals_head=counts_full[i],petals_tail=counts_full[216+i],win_head=counts_win[i],win_tail=counts_win[216+i],
                     iou=round(float(inter/max(union,1)),3),near_head=nearest[i],near_tail=nearest[216+i]))
# petal centroids near the rim (within 60 px) in head/tail frames, for the seam notes
def rim_petals(f):
    a=(alphas[f]>=A_T)&~S; lab,k=ndi.label(a); out=[]
    if k:
        idx=np.arange(1,k+1); area=ndi.sum(a,lab,idx); mn=ndi.minimum(dS,lab,idx); cms=ndi.center_of_mass(a,lab,idx)
        for i,(ar,d,c) in enumerate(zip(area,mn,cms)):
            if ar>=150 and d<=60: out.append(dict(x=int(c[1]),y=int(c[0]),area=int(ar),dist=round(float(d),1)))
    return out
gate=json.load(open(os.path.join(HERE,"gate_stats.json")))
rep=dict(center=dict(x=CX0,y=CY0),f236_centroid_xy=[c236[1],c236[0]],f236_footprint_radius=r236,source_footprint_radius=src_r,
         source_footprint_radius_per_frame_stab=[round(x,1) for x in rs],
         recommended_base_scale=K,base_scale_auto_99pct_robust=auto_k,base_scale_scan=scan,exclusion_px_outside_base_per_frame=uncov_per_frame,exclusion_px_more_than_5px_outside_base_per_frame=uncov_far,exclusion_dilation_px=5,exclusion_feather_px=8,
         rim_gate="within 40 px outside the exclusion edge: keep blue (B>R+15) | white (chroma<14 & V>205) | cream (chroma<24 & V>185 & R>=G-2 & G>=B-2); reject green-dominant (G>R+8 & G>B+8) and grey (chroma<6 & V<205); per-pixel gate smoothed sigma 1, plus component kill when <40% of a component's rim pixels are petal-coloured",
         nearest_petal_px=[None if x is None else round(x,1) for x in nearest],nearest_petal_px_p50=p50,nearest_petal_px_p80=p80,
         frames_with_petal_within_150=int(has.sum()),frames_with_petal_within_12px_pct=within12,
         petals_per_frame_full=counts_full,petals_per_frame_window900=counts_win,petals_per_second_full=pps_full,petals_per_second_window900=pps_win,
         bands_geom_lrtb=bands_geom,bands_geom_max_lrtb=[float(x) for x in bg.max(0)],bands_geom_argmax_frame=[int(x) for x in bg.argmax(0)],
         frames_with_band_gt0=[int(f) for f in np.nonzero(bg.max(1)>0.5)[0][[0,-1]]] if (bg.max(1)>0.5).any() else [],
         content_bbox_xyxy=bbox,seam=seam,rim_petals_head=[rim_petals(f) for f in range(0,24,4)],rim_petals_tail=[rim_petals(f) for f in range(216,240,4)],
         gate_rim_alpha_removed_frac=round(float(sum(g['rim_alpha_removed'] for g in gate)/max(sum(g['rim_alpha_pre'] for g in gate),1e-6)),4))
json.dump(rep,open(os.path.join(HERE,"report.json"),"w"),indent=1)
np.save(os.path.join(HERE,"base_scaled_fp.npy"),S)
print("f236 centroid (x,y)",c236[1],c236[0],"r236",r236,"src_r",src_r)
print("nearest p50/p80",p50,p80,"within12%",within12,"frames<=150",has.sum())
print("pps full",pps_full,"win",pps_win)
print("bands max lrtb",bg.max(0),"frames",bg.argmax(0))
print("nearest per frame:",[None if x is None else round(x) for x in nearest])
print("gate removed frac",rep["gate_rim_alpha_removed_frac"])
