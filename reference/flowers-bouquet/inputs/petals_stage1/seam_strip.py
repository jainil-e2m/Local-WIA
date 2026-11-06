import numpy as np, os
from PIL import Image
OUT=os.path.dirname(os.path.abspath(__file__))
SKY=np.array([0xe0,0xdf,0xe2],np.float32)
def comp(f):
    im=np.asarray(Image.open(os.path.join(OUT,"layer",f"petals_{f:03d}.png"))).astype(np.float32); a=im[...,3:4]/255
    return np.asarray(Image.fromarray((im[...,:3]*a+SKY*(1-a)).astype(np.uint8)).resize((512,288),Image.LANCZOS))
top=np.hstack([comp(f) for f in [216,228,239]]); bot=np.hstack([comp(f) for f in [0,12,24]])
Image.fromarray(np.vstack([top,bot])).save(os.path.join(OUT,"seam_strip.png")); print("seam strip saved")
