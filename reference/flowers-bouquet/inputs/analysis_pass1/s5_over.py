import numpy as np, os, csv
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
D="C:/Users/JAINIL~1/AppData/Local/Temp/claude/C--Users-Jainil-Trivedi-Desktop-Wedding-Industry-Ads-frontend/baa3834a-d7ce-41fe-b657-81dfbb3245b8/scratchpad/flowers/motion"
frames=np.load(os.path.join(D,"frames_full.npy"),mmap_mode='r')
masks=np.load(os.path.join(D,"masks.npy"))
M=np.load(os.path.join(D,"motion_metrics.npz")); C=M["C"]; sharp=M["sharp"]; near=M["near"]
N=len(C); base_r=296.31
# temporal petal-over-bouquet detector: moving blobs inside eroded mask vs frames +-5
over2=np.zeros(N,int); overpx=np.zeros(N,int)
for i in range(N):
    g=frames[i].astype(np.float32)
    m=ndi.binary_erosion(masks[i],iterations=8)
    ds=[]
    for j in (i-5,i+5):
        if 0<=j<N:
            d=np.abs(g-frames[j].astype(np.float32)).max(2); ds.append(d)
    d=np.min(ds,0) if len(ds)==2 else ds[0]
    mv=(d>45)&m
    mv=ndi.binary_opening(mv,structure=np.ones((7,7)))
    lab,n=ndi.label(mv)
    if n:
        sizes=ndi.sum(mv,lab,range(1,n+1)); over2[i]=int((sizes>400).sum()); overpx[i]=int(sizes[sizes>400].sum())
np.save(os.path.join(D,"over2.npy"),over2)
with open(os.path.join(D,"per_frame_metrics.csv")) as fh: rows=list(csv.reader(fh))
rows[0]+=["moving_blobs_over_bouquet","moving_blob_px"]
for i in range(N): rows[i+1]+=[over2[i],overpx[i]]
with open(os.path.join(D,"per_frame_metrics.csv"),"w",newline="") as fh: csv.writer(fh).writerows(rows)
print("stable-range frames with over2==0:")
for lo,hi in ((0,77),(179,240)):
    print(lo,hi,[i for i in range(lo,hi) if over2[i]==0])
print("f20,21,48,52,236,228,232,226,220,224:",[(i,over2[i],overpx[i]) for i in (20,21,48,52,236,228,232,226,220,224)])
sel=[236,228,232,226,239,230,224,220]
side=int(base_r*2*1.4); out=200
sheet=Image.new("RGB",(out*8,out),(30,30,30))
for k,i in enumerate(sel):
    cx,cy=C[i,0],C[i,1]
    im=Image.fromarray(np.asarray(frames[i])).crop((int(cx-side/2),int(cy-side/2),int(cx+side/2),int(cy+side/2))).resize((out,out),Image.LANCZOS)
    ImageDraw.Draw(im).text((4,4),"f%d sh%d near%d ov%d"%(i,sharp[i],near[i],over2[i]),fill=(255,0,0))
    sheet.paste(im,(k*out,0))
sheet.save(os.path.join(D,"candidates_sheet.png"))
# hi-res look at f236 crop
i=236; cx,cy=C[i,0],C[i,1]; side=int(base_r*2*1.2)
Image.fromarray(np.asarray(frames[i])).crop((int(cx-side/2),int(cy-side/2),int(cx+side/2),int(cy+side/2))).save(os.path.join(D,"f236_crop.png"))
Image.fromarray(np.asarray(frames[236])).save(os.path.join(D,"f236_full.png"))
