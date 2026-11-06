import numpy as np, os
from PIL import Image
OUT=os.path.dirname(os.path.abspath(__file__))
frames=np.load(os.path.join(OUT,"frames.npy"),mmap_mode='r')
fr=np.asarray(frames[0]).astype(int)
# white petal near top-centre in frame 0: approx (x=400,y=15) at 800 scale -> (640,24) full; also (240,95)->(384,152); (150,180)->(240,288)
for (x,y,name) in [(640,24,'top white'),(384,152,'left white'),(240,288,'far-left white'),(860,90,'blue top'),(1000,290,'navy right'),(1090,470,'white right'),(700,660,'bg lower mid'),(100,100,'bg TL')]:
    p=fr[y-6:y+7,x-6:x+7].reshape(-1,3)
    print(name,(x,y),"mean",p.mean(0).round(1),"min",p.min(0),"max",p.max(0))
# crop at full res around top white petal & left white petal for viewing
Image.fromarray(np.asarray(frames[0])[0:200,300:800]).save(os.path.join(OUT,"crop_white_f0.png"))
