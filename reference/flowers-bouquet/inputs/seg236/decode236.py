import numpy as np, subprocess, os
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__))
SRC="C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/frontend/public/flowers_video.mp4"
FF="C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/frontend/node_modules/ffmpeg-static/ffmpeg.exe"
PET="C:/Users/JAINIL~1/AppData/Local/Temp/claude/C--Users-Jainil-Trivedi-Desktop-Wedding-Industry-Ads-frontend/baa3834a-d7ce-41fe-b657-81dfbb3245b8/scratchpad/flowers/petals"
frames=np.load(os.path.join(PET,"frames.npy"),mmap_mode='r')
cached=np.asarray(frames[236]).copy()
out=os.path.join(HERE,"ff236.png")
subprocess.run([FF,"-v","error","-y","-i",SRC,"-an","-vf","select='eq(n\,236)'","-vsync","0","-frames:v","1",out],check=True)
ff=np.asarray(Image.open(out).convert("RGB"))
d=np.abs(ff.astype(int)-cached.astype(int))
print("ffmpeg vs cached: max",d.max(),"mean",d.mean(), "frac>2", (d.max(-1)>2).mean())
Image.fromarray(cached).save(os.path.join(HERE,"base_f236.png"))
# crops for inspection at full res: bouquet region ~ x 330..960, y 40..700
img=cached
Image.fromarray(img[30:390, 320:960]).save(os.path.join(HERE,"insp_top.png"))
Image.fromarray(img[350:710, 320:960]).save(os.path.join(HERE,"insp_bot.png"))
Image.fromarray(img).resize((1280//1,720)).save(os.path.join(HERE,"insp_full.png"))
plate=np.load(os.path.join(PET,"plate.npy"))
dd=np.abs(img.astype(np.float32)-plate).max(-1)
print("diff from plate stats: p50",np.percentile(dd,50),"p90",np.percentile(dd,90))
# heat map of diff>6 outside a circle of r=330 around centroid to spot fallen petals
yy,xx=np.mgrid[0:720,0:1280]
far=((xx-643)**2+(yy-370)**2)>330**2
m=(dd>8)&far
from scipy import ndimage as ndi
lab,n=ndi.label(m)
sizes=ndi.sum(m,lab,range(1,n+1)); cms=ndi.center_of_mass(m,lab,range(1,n+1))
for s,c in zip(sizes,cms):
    if s>30: print("far blob area",int(s),"at x,y",round(c[1]),round(c[0]))
