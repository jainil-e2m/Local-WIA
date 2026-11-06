import numpy as np, os, csv
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
D="C:/Users/JAINIL~1/AppData/Local/Temp/claude/C--Users-Jainil-Trivedi-Desktop-Wedding-Industry-Ads-frontend/baa3834a-d7ce-41fe-b657-81dfbb3245b8/scratchpad/flowers/motion"
frames=np.load(os.path.join(D,"frames_full.npy"),mmap_mode='r')
masks=np.load(os.path.join(D,"masks.npy"))
M=np.load(os.path.join(D,"motion_metrics.npz")); C=M["C"]; sharp=M["sharp"]; near=M["near"]; over=M["over"]; vs0=M["vs0"]; vs0c=M["vs0c"]
N=len(C); base_r=296.31; bcx,bcy=642.72,372.87
scale=C[:,2]/base_r; off=np.hypot(C[:,0]-bcx,C[:,1]-bcy)
# --- navy-only polar rotation vs frame 0
NA=360; NR=50; ang=np.linspace(0,2*np.pi,NA,endpoint=False); rad=np.linspace(0.15,0.85,NR)
def navy_polar(i):
    cx,cy,r=C[i]; im=frames[i].astype(np.float32)
    nav=((im[...,2]>im[...,0]+25)&(im.max(2)<120)).astype(np.float32)
    nav=ndi.uniform_filter(nav,5)
    xx=cx+np.outer(rad*r,np.cos(ang)); yy=cy+np.outer(rad*r,np.sin(ang))
    p=ndi.map_coordinates(nav,[yy,xx],order=1); return p-p.mean(1,keepdims=True)
P0=navy_polar(0)
def sh(a,b):
    cc=np.fft.irfft(np.fft.rfft(a,axis=1)*np.conj(np.fft.rfft(b,axis=1)),n=NA,axis=1).sum(0)
    k=int(np.argmax(cc)); s=k if k<=NA/2 else k-NA
    return s, cc[k]/np.sqrt((a**2).sum()*(b**2).sum()+1e-9)
navrot=[]; navc=[]
for i in range(N):
    s,c=sh(navy_polar(i),P0); navrot.append(s); navc.append(c)
navrot=np.array(navrot); navc=np.array(navc)
# --- residual morph: align frame i to frame 0 (translate+scale+rotate by vs0) then mean abs diff inside base mask
def aligned(i,rot):
    cx,cy,r=C[i]; s=r/base_r
    th=np.deg2rad(rot)
    yy,xx=np.mgrid[0:720,0:1280].astype(np.float32)
    dx=xx-bcx; dy=yy-bcy
    sx=cx+s*(np.cos(th)*dx-np.sin(th)*dy); sy=cy+s*(np.sin(th)*dx+np.cos(th)*dy)
    out=np.stack([ndi.map_coordinates(frames[i][...,c].astype(np.float32),[sy,sx],order=1) for c in range(3)],2)
    return out
f0=frames[0].astype(np.float32); m0=ndi.binary_erosion(masks[0],iterations=20)
resid=np.zeros(N)
for i in range(0,N,4):
    rot=vs0[i] if abs(vs0[i])<30 else 0
    a=aligned(i,rot); resid[i]=np.abs(a-f0)[m0].mean()
for i in range(N):
    if i%4: resid[i]=resid[i-(i%4)]
with open(os.path.join(D,"per_frame_metrics.csv")) as fh: rows=list(csv.reader(fh))
rows[0]+= ["navy_rot_vs_f0_deg","navy_corr","resid_vs_f0_aligned"]
for i in range(N): rows[i+1]+= [int(navrot[i]),round(navc[i],3),round(resid[i],1)]
with open(os.path.join(D,"per_frame_metrics.csv"),"w",newline="") as fh: csv.writer(fh).writerows(rows)
print("frame navyrot navyc resid | scale off sharp near over")
for i in range(0,N,8): print(i,navrot[i],round(navc[i],2),round(resid[i],1),"|",round(scale[i],3),round(off[i],1),int(sharp[i]),near[i],over[i])
# segments
bad=(scale>1.04)|(off>8)
lab,n=ndi.label(bad)
for k in range(1,n+1):
    idx=np.nonzero(lab==k)[0]; print("SEG",idx[0],idx[-1],"maxscale",round(scale[idx].max(),3),"maxoff",round(off[idx].max(),1))
# candidates
ok=(scale<1.035)&(scale>0.96)&(off<6)&(over==0)
cand=[i for i in range(N) if ok[i]]
score=sharp/ sharp[ok].max() - 0.08*near - 0.05*np.abs(vs0)
order=sorted(cand,key=lambda i:-score[i])
print("TOP:",[(i,int(sharp[i]),near[i],round(vs0[i],1),round(scale[i],3),round(off[i],1)) for i in order[:24]])
np.save(os.path.join(D,"cand_order.npy"),np.array(order))
sel=order[:18]
side=int(base_r*2*1.2); out=260
sheet=Image.new("RGB",(out*6,out*3),(30,30,30))
for k,i in enumerate(sel):
    cx,cy=C[i,0],C[i,1]
    im=Image.fromarray(np.asarray(frames[i])).crop((int(cx-side/2),int(cy-side/2),int(cx+side/2),int(cy+side/2))).resize((out,out),Image.LANCZOS)
    ImageDraw.Draw(im).text((4,4),"f%d s%d n%d"%(i,sharp[i],near[i]),fill=(255,0,0))
    sheet.paste(im,((k%6)*out,(k//6)*out))
sheet.save(os.path.join(D,"cand_pool.png"))
