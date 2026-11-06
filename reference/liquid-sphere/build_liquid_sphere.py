# Builds frontend/public/liquid-sphere.webm. Run find_loop_point.py first; it reported 30->232.
# usage: python build_liquid_sphere.py <scratch_dir> <out.webm> 30 232 16
# ffmpeg is not on PATH on this machine; the imageio-ffmpeg binary below is used.

"""Encode the liquid-sphere loop from a detected loop point.

The clip is near-periodic: frame END lands back on frame START to within ~2
frames of motion (see loopfind.py). The loop is START..END-1, and a short
crossfade is centred on the wrap so that each side blends with the frames the
OTHER side continues into. Because those pairs are already aligned, the blend
adds no visible ghost; it only smooths the ~2-frame residual.
"""
import sys, subprocess, numpy as np
from PIL import Image
FF  = r"C:\Users\Jainil Trivedi\AppData\Local\Programs\Python\Python312\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
SRC = r"C:\Users\Jainil Trivedi\Downloads\give_the_slurs_outside_the_cen.mp4"
SP, OUT = sys.argv[1], sys.argv[2]
START, END, K = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])   # K = total crossfade frames, split across the wrap
X0, Y0, X1, Y1 = 272, 0, 992, 720
W, H, FPS = 1280, 720, 24
LO, HI = 10.0, 30.0
SPARK = (slice(540, 660), slice(1100, 1220))
L, HALF = END - START, K // 2
assert START - HALF >= 0 and END + HALF <= 240, "crossfade runs off the clip"

def decode():
    p = subprocess.Popen([FF, "-v", "error", "-i", SRC, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                         stdout=subprocess.PIPE, bufsize=10**8)
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
    # edge spill suppressor: on semi-transparent pixels pull any yellow cast back to neutral
    semi = (a > 0.02) & (a < 0.98)
    y = np.minimum(fg[..., 0], fg[..., 1]) - fg[..., 2]
    y = np.where(semi & (y > 0), y, 0)
    fg[..., 0] -= 0.6 * y; fg[..., 1] -= 0.6 * y
    return np.clip(fg, 0, 255)[Y0:Y1, X0:X1], a[Y0:Y1, X0:X1]

src = {}
for n, fr in enumerate(decode()):
    if START - HALF <= n < END + HALF:
        fg, a = key(fr)
        src[n] = (fg.astype(np.uint8), (a * 255).astype(np.uint8))
h, w = src[START][1].shape
print(f"loop {START}->{END}: {L} frames ({L/FPS:.2f}s), crossfade {K} frames centred on the wrap, {w}x{h}")

def premul(n):
    fg, a = src[n]; a = a.astype(np.float32) / 255.0
    return fg.astype(np.float32) * a[..., None], a

def frame(t):
    """Output frame t in [0, L). Wrap sits between t=L-1 and t=0."""
    n = START + t
    if t >= L - HALF:            # tail: blend with the frames the head continues FROM
        k = t - (L - HALF)                        # 0..HALF-1
        wgt = (k + 1) / (K + 1)                   # rises toward the pre-head sequence
        p1, a1 = premul(n); p2, a2 = premul(n - L)
    elif t < HALF:               # head: blend with the frames the tail continues INTO
        k = t                                     # 0..HALF-1
        wgt = (HALF - k) / (K + 1)                # falls away from the post-tail sequence
        p1, a1 = premul(n); p2, a2 = premul(n + L)
    else:
        p, a = premul(n)
        return p, a
    return (1 - wgt) * p1 + wgt * p2, (1 - wgt) * a1 + wgt * a2

enc = subprocess.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "pipe:0",
                        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "31", "-row-mt", "1",
                        "-deadline", "good", "-cpu-used", "1", "-auto-alt-ref", "0", "-g", "48", OUT], stdin=subprocess.PIPE)
keep = {}
for t in range(L):
    p, a = frame(t)
    rgb = np.where(a[..., None] > 1e-3, p / np.maximum(a[..., None], 1e-3), 0)
    rgba = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)
    if t in (0, 1, 2, L-3, L-2, L-1, HALF + 4): keep[t] = rgba
    enc.stdin.write(rgba.tobytes())
enc.stdin.close(); enc.wait()
Image.fromarray(keep[HALF + 4], "RGBA").save(f"{SP}/poster2.png")

# wrap strip: last three output frames then first three, composited on the hero ground
bg = np.array([0xe0, 0xdf, 0xe2], np.float32)
def comp(x):
    a = x[..., 3:4] / 255.0
    return Image.fromarray((x[..., :3] * a + bg * (1 - a)).astype(np.uint8)).resize((240, 240), Image.Resampling.BOX)
strip = np.hstack([np.asarray(comp(keep[t])) for t in (L-3, L-2, L-1, 0, 1, 2)])
Image.fromarray(strip).save(f"{SP}/wrap_strip.png")
# numeric seam: rms difference between last and first output frame vs a typical adjacent pair
def rms(x, y): return float(np.sqrt(np.mean((x.astype(np.float32) - y.astype(np.float32)) ** 2)))
print(f"rms wrap  L-1 -> 0 : {rms(keep[L-1], keep[0]):.3f}")
print(f"rms inner L-2 -> L-1: {rms(keep[L-2], keep[L-1]):.3f}   0 -> 1: {rms(keep[0], keep[1]):.3f}")
print("done", enc.returncode)
