import numpy as np, os, csv
from scipy import ndimage as ndi
from PIL import Image
D="C:/Users/JAINIL~1/AppData/Local/Temp/claude/C--Users-Jainil-Trivedi-Desktop-Wedding-Industry-Ads-frontend/baa3834a-d7ce-41fe-b657-81dfbb3245b8/scratchpad/flowers/motion"
frames=np.load(os.path.join(D,"frames_full.npy"),mmap_mode='r')
masks=np.load(os.path.join(D,"masks.npy"))
rows=list(csv.reader(open(os.path.join(D,"per_frame_center_radius.csv"))))[1:]
C=np.array([[float(r[1]),float(r[2]),float(r[3])] for r in rows])
N=len(C)
# ---- polar unwrap, normalized radius
NA=360; NR=60
ang=np.linspace(0,2*np.pi,NA,endpoint=False)
rad=np.linspace(0.15,0.85,NR)
def polar(i):
    cx,cy,r=C[i]
    g=frames[i].astype(np.float32).mean(2)
    xx=cx+np.outer(rad*r,np.cos(ang)); yy=cy+np.outer(rad*r,np.sin(ang))
    return ndi.map_coordinates(g,[yy,xx],order=1)
P=np.stack([polar(i) for i in range(N)])
P=P-P.mean(2,keepdims=True)
def shift(a,b):
    # circular cross-corr along angle axis, summed over radii
    fa=np.fft.rfft(a,axis=1); fb=np.fft.rfft(b,axis=1)
    cc=np.fft.irfft(fa*np.conj(fb),n=NA,axis=1).sum(0)
    k=int(np.argmax(cc))
    # subpixel parabolic
    y0,y1,y2=cc[(k-1)%NA],cc[k],cc[(k+1)%NA]
    d=0.5*(y0-y2)/(y0-2*y1+y2) if (y0-2*y1+y2)!=0 else 0
    s=k+d
    if s>NA/2: s-=NA
    return s, cc[k]/np.sqrt((a**2).sum()*(b**2).sum())
inc=[0.0]; corr=[1.0]
for i in range(1,N):
    s,c=shift(P[i],P[i-1]); inc.append(s); corr.append(c)
inc=np.array(inc); cum=np.cumsum(inc)
# also vs frame 0 directly (drift check) for each frame
vs0=np.array([shift(P[i],P[0])[0] for i in range(N)])
vs0c=np.array([shift(P[i],P[0])[1] for i in range(N)])
# ---- sharpness: Laplacian variance inside mask crop
sharp=[]
for i in range(N):
    cx,cy,r=C[i]; g=frames[i].astype(np.float32).mean(2)
    lap=ndi.laplace(g)
    m=ndi.binary_erosion(masks[i],iterations=15)
    sharp.append(float(lap[m].var()))
sharp=np.array(sharp)
# ---- petals near rim / overlapping
f=frames
near=[]; over=[]
yy,xx=np.mgrid[0:720,0:1280]
for i in range(N):
    cx,cy,r=C[i]
    im=f[i].astype(np.float32); mx=im.max(2); mn=im.min(2)
    fg=((mx-mn)>28)|(mn<175)
    fg=ndi.binary_opening(fg,iterations=1)
    other=fg&~ndi.binary_dilation(masks[i],iterations=3)
    lab,n=ndi.label(other)
    cnt=0
    if n:
        sizes=ndi.sum(other,lab,range(1,n+1))
        cys=ndi.center_of_mass(other,lab,range(1,n+1))
        for s,(py,px) in zip(sizes,cys):
            if s<150: continue
            d=np.hypot(px-cx,py-cy)
            if d<r+90: cnt+=1
    near.append(cnt)
    # overlapping petals: smooth low-texture blue/navy/white blobs inside mask
    g=im.mean(2)
    gm=np.hypot(ndi.sobel(g,0),ndi.sobel(g,1))
    smooth=ndi.uniform_filter(gm,9)<12
    R,G,B=im[...,0],im[...,1],im[...,2]
    navy=(B>R+25)&(mx<120)
    lblue=(B>R+35)&(B>150)
    white=(mn>200)&((mx-mn)<25)
    cand=smooth&(navy|lblue|white)&ndi.binary_erosion(masks[i],iterations=6)
    cand=ndi.binary_opening(cand,structure=np.ones((5,5)))
    lab,n=ndi.label(cand)
    c=0
    if n:
        sizes=ndi.sum(cand,lab,range(1,n+1))
        c=int((sizes>700).sum())
    over.append(c)
near=np.array(near); over=np.array(over)
np.savez(os.path.join(D,"motion_metrics.npz"),inc=inc,cum=cum,vs0=vs0,vs0c=vs0c,corr=np.array(corr),sharp=sharp,near=near,over=over,C=C)
with open(os.path.join(D,"per_frame_metrics.csv"),"w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["frame","cx","cy","radius_px","scale_vs_base","center_offset_px","rot_inc_deg","rot_cum_deg","rot_vs_f0_deg","corr_prev","sharp_lapvar","petals_near_rim","petal_blobs_over_bouquet"])
    base_r=np.median(C[:60,2]); bcx=np.median(C[:60,0]); bcy=np.median(C[:60,1])
    for i in range(N):
        w.writerow([i,round(C[i,0],1),round(C[i,1],1),round(C[i,2],1),round(C[i,2]/base_r,3),round(np.hypot(C[i,0]-bcx,C[i,1]-bcy),1),round(inc[i],2),round(cum[i],1),round(vs0[i],1),round(corr[i],3),round(sharp[i],1),near[i],over[i]])
print("base r,cx,cy",base_r,bcx,bcy)
for i in range(0,N,8):
    print(i,"inc%.2f cum%.1f vs0 %.1f c%.3f sharp%.0f near%d over%d scale%.3f off%.1f"%(inc[i],cum[i],vs0[i],corr[i],sharp[i],near[i],over[i],C[i,2]/base_r,np.hypot(C[i,0]-bcx,C[i,1]-bcy)))
