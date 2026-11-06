"""Build the seamless 3-4 bird hero loop from harvested sprites.

Pipeline: clean plate (watermark patched) -> harvest sprite sequences for the
clean flights -> extend each flight off-frame by cycling its flap cycle along
its own velocity -> mirror for opposite-direction twins -> schedule so 3-4 are
visible at all times with no overlaps, wrapping modulo the loop length ->
composite frame-by-frame -> encode WebM/MP4/poster.
"""
import os, random, pickle, subprocess
import numpy as np
import imageio_ffmpeg
from PIL import Image, ImageFilter, ImageDraw

random.seed(7); np.random.seed(7)
W, H = 1280, 720
NOUT, FPS = 240, 24
CYC = 8                      # flap cycle length (frames) used for extension
PUB = r"C:\Users\Jainil Trivedi\Desktop\Wedding_Industry_Ads\frontend\public"

mm = np.load("full.npy", mmap_mode="r")
plate = np.asarray(Image.open("plate_full.png")).astype(np.float32)
cands = pickle.load(open("cands.pkl", "rb"))["cands"]

# ---------- 1. plate: patch the watermark (bilinear fill from the box border) ----------
x0, y0, x1, y1 = 1128, 568, 1192, 632
h, w = y1 - y0, x1 - x0
top, bot = plate[y0 - 1, x0:x1], plate[y1, x0:x1]
lef, rig = plate[y0:y1, x0 - 1], plate[y0:y1, x1]
fy = np.linspace(0, 1, h)[:, None, None]; fx = np.linspace(0, 1, w)[None, :, None]
vert = top[None] * (1 - fy) + bot[None] * fy
horz = lef[:, None] * (1 - fx) + rig[:, None] * fx
plate[y0:y1, x0:x1] = (vert + horz) / 2
pimg = Image.fromarray(plate.astype(np.uint8))
region = pimg.crop((x0 - 6, y0 - 6, x1 + 6, y1 + 6)).filter(ImageFilter.GaussianBlur(1.4))
pimg.paste(region, (x0 - 6, y0 - 6))
plate = np.asarray(pimg).astype(np.float32)
pimg.save("plate_clean.png")

# ---------- 2. harvest sprites ----------
USE = [c for c in cands if c["L"] >= 34]

def sprite(f, b, pad=8):
    xa, ya = max(0, b["x0"] - pad), max(0, b["y0"] - pad)
    xb, yb = min(W, b["x1"] + pad + 1), min(H, b["y1"] + pad + 1)
    rgb = np.asarray(mm[f][ya:yb, xa:xb], dtype=np.float32)
    diff = np.abs(rgb - plate[ya:yb, xa:xb]).sum(axis=2)
    a = np.clip((diff - 45) / 75, 0, 1)
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9)),
                   dtype=np.float32) / 255
    a[diff < 28] = 0
    return dict(rgb=rgb, a=a, ox=b["cx"] - xa, oy=b["cy"] - ya)

def offscreen(p, s):
    x = p[0] - s["ox"]; y = p[1] - s["oy"]; hh, ww = s["a"].shape
    return x > W + 2 or x + ww < -2 or y > H + 2 or y + hh < -2

flights = []
for c in USE:
    fr = sorted(c["obs"])
    pts = np.array([(c["obs"][f]["cx"], c["obs"][f]["cy"]) for f in fr])
    sp = [sprite(f, c["obs"][f]) for f in fr]
    v0 = (pts[CYC - 1] - pts[0]) / (CYC - 1)
    v1 = (pts[-1] - pts[-CYC]) / (CYC - 1)
    back = []
    for k in range(1, 120):
        s = sp[(-k) % CYC]; p = pts[0] - v0 * k
        if offscreen(p, s): break
        back.append((tuple(p), s))
    back.reverse()
    fwd = []
    if c["eout"] == "-":
        for k in range(1, 120):
            s = sp[len(sp) - CYC + ((k - 1) % CYC)]; p = pts[-1] + v1 * k
            if offscreen(p, s): break
            fwd.append((tuple(p), s))
    seq = back + [(tuple(p), s) for p, s in zip(pts, sp)] + fwd
    flights.append(dict(name=f"#{c['id']}", seq=seq, nat=len(sp), ext=len(back) + len(fwd)))
    mseq = [((W - 1 - p[0], p[1]),
             dict(rgb=s["rgb"][:, ::-1], a=s["a"][:, ::-1], ox=s["rgb"].shape[1] - 1 - s["ox"], oy=s["oy"]))
            for p, s in seq]
    flights.append(dict(name=f"#{c['id']}m", seq=mseq, nat=len(sp), ext=len(back) + len(fwd)))

for fl in flights:
    print(f"flight {fl['name']:>5}: {len(fl['seq']):3d} frames ({fl['nat']} real + {fl['ext']} extended)")

# ---------- 3. schedule ----------
def bbox_at(p, s, infl=18):
    x = p[0] - s["ox"]; y = p[1] - s["oy"]; hh, ww = s["a"].shape
    return (x - infl, y - infl, x + ww + infl, y + hh + infl)

def visible(p, s):
    x = p[0] - s["ox"]; y = p[1] - s["oy"]; hh, ww = s["a"].shape
    return x < W - 4 and x + ww > 4 and y < H - 4 and y + hh > 4

def isect(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

# precompute per-flight per-frame (visible, bbox)
pre = []
for fl in flights:
    pre.append([(visible(p, s), bbox_at(p, s)) for p, s in fl["seq"]])

def evaluate(sched):
    count = np.zeros(NOUT, int); boxes = [[] for _ in range(NOUT)]; overlaps = 0
    for fi, st in sched:
        for k, (vis, bb) in enumerate(pre[fi]):
            if not vis: continue
            t = (st + k) % NOUT
            count[t] += 1
            for ob in boxes[t]:
                if isect(bb, ob): overlaps += 1
            boxes[t].append(bb)
    pen = int(np.sum(np.clip(3 - count, 0, None) * 3) + np.sum(np.clip(count - 4, 0, None) * 3) + overlaps * 12)
    return pen, count, overlaps

nF = len(flights)
best = None
for _ in range(2500):
    k = random.randint(8, min(12, nF))
    picks = random.sample(range(nF), k)
    sched = [(fi, random.randrange(NOUT)) for fi in picks]
    pen, cnt, ov = evaluate(sched)
    if best is None or pen < best[0]:
        best = (pen, sched, cnt, ov)
pen, sched, cnt, ov = best
for _ in range(6000):
    trial = list(sched)
    r = random.random()
    if r < 0.7:                                   # nudge an offset
        i = random.randrange(len(trial)); fi, st = trial[i]
        trial[i] = (fi, (st + random.randint(-36, 36)) % NOUT)
    elif r < 0.85 and len(trial) < min(12, nF):   # add a flight not yet used
        unused = [i for i in range(nF) if i not in [f for f, _ in trial]]
        if unused: trial.append((random.choice(unused), random.randrange(NOUT)))
    elif len(trial) > 8:                          # drop one
        trial.pop(random.randrange(len(trial)))
    p2, c2, o2 = evaluate(trial)
    if p2 <= pen:
        pen, sched, cnt, ov = p2, trial, c2, o2

print(f"\nschedule penalty={pen} overlaps={ov} flights={len(sched)}")
print("visible-count histogram:", {int(v): int((cnt == v).sum()) for v in np.unique(cnt)})
print("schedule:", [(flights[fi]["name"], st) for fi, st in sched])

# ---------- 4. composite, one frame at a time ----------
os.makedirs("out", exist_ok=True)
place = [[] for _ in range(NOUT)]
for fi, st in sched:
    for k, (p, s) in enumerate(flights[fi]["seq"]):
        place[(st + k) % NOUT].append((p, s))
for t in range(NOUT):
    F = plate.copy()
    for p, s in place[t]:
        x = int(round(p[0] - s["ox"])); y = int(round(p[1] - s["oy"])); hh, ww = s["a"].shape
        xa, ya, xb, yb = max(0, x), max(0, y), min(W, x + ww), min(H, y + hh)
        if xb <= xa or yb <= ya: continue
        sa = s["a"][ya - y:yb - y, xa - x:xb - x][..., None]
        F[ya:yb, xa:xb] = s["rgb"][ya - y:yb - y, xa - x:xb - x] * sa + F[ya:yb, xa:xb] * (1 - sa)
    Image.fromarray(np.clip(F, 0, 255).astype(np.uint8)).save(f"out/{t:04d}.png")

# ---------- 5. diagnostics ----------
cell = (320, 180)
sheet = Image.new("RGB", (5 * cell[0], 4 * cell[1]))
for i, t in enumerate(range(0, NOUT, 12)):
    im = Image.open(f"out/{t:04d}.png").resize(cell, Image.LANCZOS)
    ImageDraw.Draw(im).text((6, 6), f"f{t} ({t/24:.1f}s) birds={cnt[t]}", fill=(200, 30, 30))
    sheet.paste(im, ((i % 5) * cell[0], (i // 5) * cell[1]))
sheet.save("out_sheet.png")
seam = Image.new("RGB", (8 * 320, 180))
for i, t in enumerate([236, 237, 238, 239, 0, 1, 2, 3]):
    im = Image.open(f"out/{t:04d}.png").resize((320, 180), Image.LANCZOS)
    ImageDraw.Draw(im).text((6, 6), f"f{t}", fill=(200, 30, 30)); seam.paste(im, (i * 320, 0))
seam.save("seam_strip.png")
a = np.asarray(Image.open("out/0239.png"), dtype=int)
b = np.asarray(Image.open("out/0000.png"), dtype=int)
c2 = np.asarray(Image.open("out/0001.png"), dtype=int)
print(f"\nseam mean|f239-f0| = {np.abs(a-b).mean():.3f}   normal step mean|f0-f1| = {np.abs(b-c2).mean():.3f}")
print(f"background pixels identical across seam: {(np.abs(a-b).sum(axis=2)==0).mean()*100:.1f}%")

# ---------- 6. encode ----------
ff = imageio_ffmpeg.get_ffmpeg_exe()
common = ["-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", "out/%04d.png",
          "-an", "-pix_fmt", "yuv420p", "-r", str(FPS)]
vp9 = ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "24", "-row-mt", "1", "-deadline", "good", "-cpu-used", "1"]
subprocess.run([ff, *common, *vp9, "-pass", "1", "-f", "null", "NUL"], check=True)
subprocess.run([ff, *common, *vp9, "-pass", "2", os.path.join(PUB, "birds-hero.webm")], check=True)
subprocess.run([ff, *common, "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high",
                "-movflags", "+faststart", os.path.join(PUB, "birds-hero.mp4")], check=True)
Image.open("out/0000.png").convert("RGB").save(os.path.join(PUB, "birds-hero-poster.jpg"),
                                                 quality=88, optimize=True, progressive=True)
for fn in ("birds-hero.webm", "birds-hero.mp4", "birds-hero-poster.jpg"):
    print(f"  {fn:22s} {os.path.getsize(os.path.join(PUB, fn))/1024:8.0f} KB")
