import subprocess, numpy as np, os
SRC="C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/frontend/public/flowers_video.mp4"
FF="C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/frontend/node_modules/ffmpeg-static/ffmpeg.exe"
OUT="C:/Users/JAINIL~1/AppData/Local/Temp/claude/C--Users-Jainil-Trivedi-Desktop-Wedding-Industry-Ads-frontend/baa3834a-d7ce-41fe-b657-81dfbb3245b8/scratchpad/flowers/petals"
W,H=1280,720
p=subprocess.run([FF,"-v","error","-i",SRC,"-an","-f","rawvideo","-pix_fmt","rgb24","pipe:1"],capture_output=True)
buf=np.frombuffer(p.stdout,np.uint8)
n=buf.size//(W*H*3)
frames=buf[:n*W*H*3].reshape(n,H,W,3)
print("frames",n,frames.shape)
np.save(os.path.join(OUT,"frames.npy"),frames)
# background stats from border band (outer 40 px) per frame
border=np.concatenate([frames[:,:40].reshape(n,-1,3),frames[:,-40:].reshape(n,-1,3),frames[:,:,:40].reshape(n,-1,3),frames[:,:,-40:].reshape(n,-1,3)],axis=1)
med=np.median(border.reshape(-1,3),axis=0)
print("border median rgb",med)
# per frame border median (petals will perturb little)
pf=np.median(border,axis=1)
print("per-frame border median min/max per channel",pf.min(0),pf.max(0))
