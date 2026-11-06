"""Bouquet alpha for frame 236. Writes bouquet_alpha.png, alpha_check*.png, alpha_debug.png, bou.npy.
Rules (all thresholds on 0..1 floats):
  strong  = chroma>0.06 | v<0.58 | |f-plate|max>0.16          roses, leaves, deep shadow
  weak    = chroma>0.028 | v<0.66 | bud                        greenish stems / grey-green bud shading; NOT the neutral, bright Veo halo
  bud     = neutral (chroma<0.04), lum>0.925, not darker than plate by >3/255, speckled (5x5 lum range>0.09),
            and >3 px away from any leaf/rose body -> white baby's-breath buds that are table-coloured
  body    = closed+filled strong core, plus components of closed strong within 30 px (detached leaf tips),
            plus weak within 14 px of the core; closing disc(4) bridges buds; fill holes; 2 px opening-reconstruct
  content = (strong | warm-bright cream tips (r-b>0.025,v>0.6) | bud closed 1 px) inside body
  alpha   = 1 on content and on the deep interior (>20 px from the body boundary); elsewhere inside the body
            the soft content score (so table-grey gaps between rim leaves stay transparent); gaussian 0.7 feather
  score   = max( ramp(|f-plate|max, 0.10..0.28), ramp(chroma, 0.03..0.08), ramp(0.66-v, 0..0.12) )
  interstitial table grey (chroma<6/255, min>=228) in the deep interior: alpha *= GREY_MULT (0.85)
"""
import numpy as np, os, sys
from PIL import Image
from scipy import ndimage as ndi
HERE=os.path.dirname(os.path.abspath(__file__))
PET="C:/Users/JAINIL~1/AppData/Local/Temp/claude/C--Users-Jainil-Trivedi-Desktop-Wedding-Industry-Ads-frontend/baa3834a-d7ce-41fe-b657-81dfbb3245b8/scratchpad/flowers/petals"
H,W=720,1280
img=np.asarray(Image.open(os.path.join(HERE,"base_f236.png")).convert("RGB"))
f=img.astype(np.float32)/255.
plate=np.load(os.path.join(PET,"plate.npy")).astype(np.float32)/255.
d=f-plate; dmax=np.abs(d).max(-1)
v=f.max(-1); chroma=f.max(-1)-f.min(-1); lum=f.mean(-1)
GREY_MULT=float(sys.argv[1]) if len(sys.argv)>1 else 0.85
DEEP=int(sys.argv[2]) if len(sys.argv)>2 else 20
def disc(r):
    y,x=np.ogrid[-r:r+1,-r:r+1]; return (x*x+y*y)<=r*r
def largest(m):
    cc,n=ndi.label(m); s=ndi.sum(m,cc,range(1,n+1)); return cc==(int(np.argmax(s))+1)
strong=(chroma>0.06)|(v<0.58)|(dmax>0.16)
lrange=ndi.maximum_filter(lum,5)-ndi.minimum_filter(lum,5)
textured=lrange>0.05
speckled=lrange>0.09                                              # sprig buds sit next to much darker stems/gaps; the halo gradient never reaches this
leafbody=ndi.binary_opening((chroma>0.06)|(v<0.58),disc(2))       # leaves/roses without thin stems
bud=(d.max(-1)>-0.012)&(chroma<0.04)&(lum>0.925)&speckled&~ndi.binary_dilation(leafbody,disc(3))
weak=(chroma>0.028)|(v<0.66)|bud
strong_c=ndi.binary_fill_holes(ndi.binary_closing(strong,disc(4)))
core0=largest(strong_c)
near30=ndi.binary_dilation(core0,disc(30))
core0=core0|ndi.binary_propagation(strong_c&near30&~core0, mask=strong_c)   # detached leaf tips within 30 px
near=ndi.binary_dilation(core0,disc(14))
bou=core0|(weak&near)
bou=ndi.binary_closing(bou,disc(4))
bou=ndi.binary_fill_holes(bou)
# keep main body + anything of it within 30 px (the detached tips)
main=largest(bou); bou=main|(bou&ndi.binary_dilation(main,disc(30)))
bou=ndi.binary_propagation(ndi.binary_opening(bou,disc(2)),mask=bou)
np.save(os.path.join(HERE,"bou.npy"),bou)
warm=(f[...,0]-f[...,2]>0.025)&(v>0.6)                       # cream petal tips are warm; table/halo are neutral
bud_c=ndi.binary_closing(bud,disc(1))&~ndi.binary_dilation(leafbody,disc(2))   # fill 1-2 px gaps between buds only
cc,n=ndi.label(bud_c); sz=ndi.sum(bud_c,cc,range(1,n+1))
bud_c&=np.isin(cc,[i+1 for i,a in enumerate(sz) if a>=8])                       # drop isolated 2-3 px specks
content=(strong|warm|bud_c)&bou                                # leaf/rose anti-aliased edge pixels are NOT content: they take the soft score
dist_out=ndi.distance_transform_edt(bou)
deep=bou&(dist_out>DEEP)
core=content|deep
score=np.maximum.reduce([np.clip((dmax-0.10)/0.18,0,1), np.clip((chroma-0.03)/0.05,0,1), np.clip((0.66-v)/0.12,0,1)])
alpha=np.where(core,1.0,np.where(bou,score,0.0)).astype(np.float32)
alpha=ndi.gaussian_filter(alpha,0.7)
inter=deep&(chroma*255<6)&(img.min(-1)>=228)&~content
inter_s=ndi.gaussian_filter(inter.astype(np.float32),1.0)
alpha=np.clip(alpha*(1-(1-GREY_MULT)*inter_s),0,1)
Image.fromarray(np.round(alpha*255).astype(np.uint8)).save(os.path.join(HERE,"bouquet_alpha.png"))
np.save(os.path.join(HERE,"alpha_f.npy"),alpha)
a5=alpha>0.5; area=int(a5.sum()); cy,cx=ndi.center_of_mass(a5)
print("alpha>0.5 area",area,"centroid",round(cx,1),round(cy,1),"equiv r",round(float(np.sqrt(area/np.pi)),1))
print("interstitial deep table px",int(inter.sum()),"bud px",int((bud&bou).sum()),"soft px",int((bou&~core).sum()))
ys,xs=np.where(bou); y0,y1=max(ys.min()-20,0),min(ys.max()+20,H); x0,x1=max(xs.min()-20,0),min(xs.max()+20,W)
dbg=np.zeros((H,W,3),np.uint8)
dbg[bou]=(90,90,90); dbg[content]=(0,90,0); dbg[deep&~content]=(0,50,0); dbg[bud&bou]=(255,255,0); dbg[inter]=(255,0,255)
Image.fromarray(dbg[y0:y1,x0:x1]).save(os.path.join(HERE,"alpha_debug.png"))
def comp(bg):
    bgc=np.array(bg,np.float32)/255
    return (np.clip(f*alpha[...,None]+bgc*(1-alpha[...,None]),0,1)*255).astype(np.uint8)
cA=comp((40,44,52)); cB=comp((0xe0,0xdf,0xe2)); cM=comp((128,128,128))
whole=Image.new("RGB",((x1-x0)*2,(y1-y0)))
whole.paste(Image.fromarray(cA[y0:y1,x0:x1]),(0,0)); whole.paste(Image.fromarray(cB[y0:y1,x0:x1]),(x1-x0,0))
whole=whole.resize((1600,int(whole.height*1600/whole.width)),Image.LANCZOS); whole.save(os.path.join(HERE,"alpha_check.png"))
zooms=[(340,470,540,620),(760,80,960,230),(300,300,500,450),(560,560,760,710),(860,380,1060,530),(400,120,600,270)]
for k in range(0,len(zooms),3):
    sh=Image.new("RGB",(1200,1350))
    for i,(zx0,zy0,zx1,zy1) in enumerate(zooms[k:k+3]):
        for j,c in enumerate((cA,cM)):
            sh.paste(Image.fromarray(c[zy0:zy1,zx0:zx1]).resize((600,450),Image.LANCZOS),(j*600,i*450))
    sh.save(os.path.join(HERE,f"alpha_check_zoom{k//3+1}.png"))
# light bg zooms too
sh=Image.new("RGB",(1200,900))
for i,(zx0,zy0,zx1,zy1) in enumerate(zooms[:4]):
    sh.paste(Image.fromarray(cB[zy0:zy1,zx0:zx1]).resize((600,450),Image.LANCZOS),((i%2)*600,(i//2)*450))
sh.save(os.path.join(HERE,"alpha_check_zoom_light.png"))
