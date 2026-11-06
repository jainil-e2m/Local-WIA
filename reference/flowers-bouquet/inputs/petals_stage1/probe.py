import numpy as np, os
from PIL import Image
OUT=os.path.dirname(os.path.abspath(__file__))
frames=np.load(os.path.join(OUT,"frames.npy"),mmap_mode='r')
n,H,W,_=frames.shape
for f in [0,24,48,72,96,120,144,168,192,216,239]:
    fr=np.asarray(frames[f]).astype(np.float32); lum=fr.mean(-1)
    print(f, "TL %.1f TR %.1f BL %.1f BR %.1f  midR %.1f midB %.1f midT %.1f midL %.1f"%(lum[:60,:60].mean(),lum[:60,-60:].mean(),lum[-60:,:60].mean(),lum[-60:,-60:].mean(),lum[300:420,-60:].mean(),lum[-60:,560:720].mean(),lum[:60,560:720].mean(),lum[300:420,:60].mean()))
# save frame 0 and 130 downscaled for viewing
for f in [0,130]:
    Image.fromarray(np.asarray(frames[f])).resize((800,450)).save(os.path.join(OUT,f"frame_{f:03d}_small.png"))
# horizontal profile of frame 0 along row 700 and row 360 (median over 20 rows), sampled every 80 px
fr=np.asarray(frames[0]).astype(np.float32).mean(-1)
print("row 690-710 profile:",np.round(np.median(fr[690:710],0)[::80],1))
print("row 20-40 profile:",np.round(np.median(fr[20:40],0)[::80],1))
print("col 20-40 profile:",np.round(np.median(fr[:,20:40],1)[::60],1))
print("col 1240-1260 profile:",np.round(np.median(fr[:,1240:1260],1)[::60],1))
