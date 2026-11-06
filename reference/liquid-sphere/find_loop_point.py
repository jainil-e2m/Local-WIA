"""Find the best loop point in the liquid-sphere clip.

Cost of cutting so that output frame j lands back on frame i is not just how
alike frames i and j look: two frames can match pose and still mismatch in
MOTION, which reads as a hitch at the wrap. So the cost sums the match at the
seam and at its immediate neighbours (Schodl's video-textures trick), which
forces the velocity to agree too.
"""
import sys, subprocess, numpy as np
from PIL import Image

FF  = r"C:\Users\Jainil Trivedi\AppData\Local\Programs\Python\Python312\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
SRC = r"C:\Users\Jainil Trivedi\Downloads\give_the_slurs_outside_the_cen.mp4"
SP  = sys.argv[1]
W, H = 1280, 720
LO, HI = 10.0, 30.0
SPARK = (slice(540, 660), slice(1100, 1220))
M = 128          # match resolution
A_W = 1.6        # silhouette weighs more than colour: it is what the eye tracks

def decode():
    p = subprocess.Popen([FF, "-v", "error", "-i", SRC, "-an", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "pipe:1"], stdout=subprocess.PIPE, bufsize=10**8)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    p.wait()

def chroma(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return (-0.168736*r - 0.331264*g + 0.5*b), (0.5*r - 0.418688*g - 0.081312*b)

def key(frame):
    f = frame.astype(np.float32)
    c = np.concatenate([f[8:48, 8:48].reshape(-1,3), f[8:48,-48:-8].reshape(-1,3),
                        f[-48:-8, 8:48].reshape(-1,3), f[-48:-8,-48:-8].reshape(-1,3)])
    bg = c.mean(0)
    cb, cr = chroma(f); bcb, bcr = chroma(bg)
    d = np.sqrt((cb-bcb)**2 + (cr-bcr)**2)
    a = np.clip((d - LO) / (HI - LO), 0, 1)
    a[SPARK] = 0
    a3 = a[..., None]
    fg = np.where(a3 > 0.02, (f - bg*(1-a3)) / np.maximum(a3, 0.05), f)
    return np.clip(fg, 0, 255), a

feat = []
for fr in decode():
    fg, a = key(fr)
    rgba = np.dstack([fg * a[..., None] / 255.0, a * A_W]).astype(np.float32)  # premultiplied
    small = np.asarray(Image.fromarray((np.clip(rgba,0,A_W)/A_W*255).astype(np.uint8), "RGBA")
                       .resize((M, M), Image.Resampling.BOX), np.float32) / 255.0
    feat.append(small.reshape(-1))
X = np.asarray(feat, np.float32)
N = len(X)
sq = (X*X).sum(1)
D = sq[:,None] + sq[None,:] - 2.0 * (X @ X.T)
D = np.sqrt(np.maximum(D, 0)) / np.sqrt(X.shape[1])   # rms per feature
np.save(f"{SP}/D.npy", D)

print(f"frames {N}  mean adjacent-frame distance {np.mean([D[i,i+1] for i in range(N-1)]):.4f}")
adj = float(np.mean([D[i,i+1] for i in range(N-1)]))

# seam cost: match at the wrap plus its neighbours, so velocity agrees too
def cost(i, j):
    return (D[i,j] + D[i+1,j+1] + D[i-1,j-1]) / 3.0

cands = []
for i in range(2, N-2):
    for j in range(i+72, N-2):          # >= 3s of loop
        cands.append((cost(i,j), i, j, j-i))
cands.sort()
print(f"\n{'cost':>8} {'ratio':>6} {'start':>5} {'end':>5} {'len':>4} {'secs':>5}   (ratio = cost / adjacent-frame distance)")
for c, i, j, L in cands[:14]:
    print(f"{c:8.4f} {c/adj:6.2f} {i:5d} {j:5d} {L:4d} {L/24:5.2f}")

# best per loop length band, so a longer loop can be chosen if its seam is close
print("\nbest by minimum length:")
for minL in (72, 96, 120, 144, 168, 192):
    sub = [x for x in cands if x[3] >= minL]
    if sub:
        c,i,j,L = sub[0]
        print(f"  >= {minL/24:4.1f}s : cost {c:.4f} (ratio {c/adj:5.2f})  frames {i}->{j}  len {L} ({L/24:.2f}s)")
