import numpy as np, os, sys
from PIL import Image
OUT=os.path.dirname(os.path.abspath(__file__))
SKY=np.array([0xe0,0xdf,0xe2],np.float32)
FR=[0,40,80,120,160,200,239]
tiles=[]
for f in FR:
    im=np.asarray(Image.open(os.path.join(OUT,"layer",f"petals_{f:03d}.png"))).astype(np.float32)
    a=im[...,3:4]/255.0
    comp=im[...,:3]*a+SKY*(1-a)
    t=Image.fromarray(comp.astype(np.uint8)).resize((640,360),Image.LANCZOS)
    tiles.append(np.asarray(t))
rows=[np.hstack(tiles[i:i+2]) if i+1<len(tiles) else np.hstack([tiles[i],np.full_like(tiles[i],0xe0)]) for i in range(0,len(tiles),2)]
grid=np.vstack(rows)
name=sys.argv[1] if len(sys.argv)>1 else "test_strip.png"
Image.fromarray(grid).save(os.path.join(OUT,name))
print("saved",name,grid.shape)
