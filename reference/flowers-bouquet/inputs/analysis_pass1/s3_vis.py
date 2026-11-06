import numpy as np, os
from PIL import Image, ImageDraw
D="C:/Users/JAINIL~1/AppData/Local/Temp/claude/C--Users-Jainil-Trivedi-Desktop-Wedding-Industry-Ads-frontend/baa3834a-d7ce-41fe-b657-81dfbb3245b8/scratchpad/flowers/motion"
frames=np.load(os.path.join(D,"frames_full.npy"),mmap_mode='r')
M=np.load(os.path.join(D,"motion_metrics.npz")); C=M["C"]
def crop(i,side=None,out=260):
    cx,cy,r=C[i]; side=int(r*2*1.25) if side is None else side
    im=Image.fromarray(np.asarray(frames[i]))
    box=(int(cx-side/2),int(cy-side/2),int(cx+side/2),int(cy+side/2))
    c=im.crop(box).resize((out,out),Image.LANCZOS)
    d=ImageDraw.Draw(c); d.text((5,5),"f%d"%i,fill=(255,0,0))
    return c
sel=[0,48,96,120,144,168,192,239]
sheet=Image.new("RGB",(260*len(sel),260))
for k,i in enumerate(sel): sheet.paste(crop(i),(260*k,0))
sheet.save(os.path.join(D,"aligned_seq.png"))
# diff frame 0 vs 232 (scale-normalised)
a=np.array(crop(0,out=520)).astype(float); b=np.array(crop(232,out=520)).astype(float)
diff=np.abs(a-b).mean(2); diff=np.clip(diff*3,0,255).astype(np.uint8)
Image.fromarray(np.concatenate([a.astype(np.uint8),b.astype(np.uint8),np.stack([diff]*3,2)],1)).save(os.path.join(D,"diff_0_232.png"))
