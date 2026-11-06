import subprocess, numpy as np, os, csv
from scipy import ndimage as ndi
from PIL import Image
D="C:/Users/JAINIL~1/AppData/Local/Temp/claude/C--Users-Jainil-Trivedi-Desktop-Wedding-Industry-Ads-frontend/baa3834a-d7ce-41fe-b657-81dfbb3245b8/scratchpad/flowers/motion"
FF="C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/frontend/node_modules/ffmpeg-static/ffmpeg.exe"
SRC="C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/frontend/public/flowers_video.mp4"
W,H=1280,720
p=subprocess.run([FF,"-v","error","-i",SRC,"-an","-f","rawvideo","-pix_fmt","rgb24","pipe:1"],capture_output=True)
buf=np.frombuffer(p.stdout,np.uint8)
N=buf.size//(W*H*3); print("frames",N)
frames=buf.reshape(N,H,W,3)
np.save(os.path.join(D,"frames_full.npy"),frames)
# background estimate: per-pixel median of a few frames far apart -> but bouquet always in center; use light-grey detection instead
f=frames.astype(np.float32)
mx=f.max(3); mn=f.min(3)
sat=(mx-mn)  # chroma
dark=255-mx
# foreground: colored or darker than bg
fg=(sat>28)|(mn<175)
rows=[]
masks=np.zeros((N,H,W),bool)
for i in range(N):
    m=fg[i]
    m=ndi.binary_opening(m,iterations=1)
    m=ndi.binary_closing(m,structure=np.ones((9,9)))
    lab,n=ndi.label(m)
    if n==0: rows.append((i,0,0,0)); continue
    sizes=ndi.sum(m,lab,range(1,n+1))
    # pick largest component
    k=int(np.argmax(sizes))+1
    mm=lab==k
    mm=ndi.binary_fill_holes(mm)
    # fill gaps: closing with big structure then fill holes
    mm=ndi.binary_closing(mm,structure=np.ones((25,25)))
    mm=ndi.binary_fill_holes(mm)
    ys,xs=np.nonzero(mm)
    cx,cy=xs.mean(),ys.mean(); area=mm.sum(); r=np.sqrt(area/np.pi)
    masks[i]=mm
    rows.append((i,cx,cy,r))
    if i%24==0: print(i,round(cx,1),round(cy,1),round(r,1))
np.save(os.path.join(D,"masks.npy"),masks)
with open(os.path.join(D,"per_frame_center_radius.csv"),"w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["frame","cx","cy","radius_px"]); w.writerows(rows)
# quick sheet of masks overlay at some frames
sel=[0,60,100,120,140,160,180,239]
tiles=[]
for i in sel:
    im=frames[i].copy(); im[masks[i]]=(0.5*im[masks[i]]+[0,127,0]).astype(np.uint8)
    tiles.append(np.array(Image.fromarray(im).resize((400,225))))
sheet=np.concatenate([np.concatenate(tiles[:4],1),np.concatenate(tiles[4:],1)],0)
Image.fromarray(sheet).save(os.path.join(D,"mask_check.png"))
