"""
build_lotus_sway.py - seamless "breeze through the lotus" loop from the static lotus RGBA asset.

usage: python build_lotus_sway.py <lotus.webp|png> <out_dir> [--seconds 6] [--fps 30] [--amp 0.022] [--start 0.68]

What it does
  * splits the asset into petals (each petal is its own connected component of the alpha mask)
  * per petal, finds its base (the pixel nearest the flower's root) and its tip (the pixel farthest from it)
    and parametrises the petal along that axis, u = 0 at base ... 1 at tip
  * builds a per-pixel displacement field: zero for u < START (the body never moves), then a smoothstep ramp to
    the tip, where the petal is displaced perpendicular to its axis by a sum of upward-travelling sine waves
    (a flame-like lick, not a left-right slide), plus a much smaller along-axis "reach"
  * every wave frequency is an integer multiple of 1/LOOP, so frame N == frame 0 with continuous velocity
  * remaps the premultiplied RGBA with cubic sampling, so the gradient, the edges and the transparency survive
  * exports VP9 WebM with alpha, ProRes 4444 with alpha, and an H.264 MP4 on pure white; writes a contact sheet,
    a seam strip (last 3 frames | first 3 frames), steps.csv (frame-to-frame RMS incl. the wrap step) and
    a stillness check for the body.
"""
import argparse, csv, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out_dir")
ap.add_argument("--seconds", type=float, default=6.0)
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--amp", type=float, default=0.031, help="tip displacement as a fraction of petal length")
ap.add_argument("--start", type=float, default=0.68, help="u (0 base..1 tip) where motion begins")
ap.add_argument("--seed", type=int, default=3)
ap.add_argument("--crf", type=int, default=12)
ap.add_argument("--ss", type=int, default=2, help="supersampling factor for the warp (sharper moving edges)")
args = ap.parse_args()

FF = r"C:\Users\Jainil Trivedi\AppData\Local\Programs\Python\Python312\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
os.makedirs(args.out_dir, exist_ok=True)
frames_dir = os.path.join(args.out_dir, "frames"); os.makedirs(frames_dir, exist_ok=True)

# ---------------------------------------------------------------- source
img = np.array(Image.open(args.src).convert("RGBA")).astype(np.float32) / 255.0
H0, W0 = img.shape[:2]
# even dimensions for 4:2:0 encoders: pad with fully transparent pixels (never visible)
H, W = H0 + (H0 % 2), W0 + (W0 % 2)
src = np.zeros((H, W, 4), np.float32); src[:H0, :W0] = img
alpha = src[..., 3]
prem = src.copy(); prem[..., :3] *= alpha[..., None]          # premultiplied for resampling
SS = args.ss
prem_hi = cv2.resize(prem, (W * SS, H * SS), interpolation=cv2.INTER_LANCZOS4) if SS > 1 else prem
ys_hi, xs_hi = (np.mgrid[0:H * SS, 0:W * SS].astype(np.float32) + 0.5) / SS - 0.5   # hi-res pixel centres in lo-res coords

# ---------------------------------------------------------------- petals
mask = (alpha > 0.02).astype(np.uint8)
n, lab, stats, cent = cv2.connectedComponentsWithStats(mask, 8)
petals = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 500]
ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
root = np.array([W0 / 2.0, float(np.max(np.nonzero(mask)[0]))])   # flower root: bottom centre of the asset
print(f"{len(petals)} petals, root at {root}")

rng = np.random.default_rng(args.seed)
fields = []   # per petal: (u map, axis, perp, length, phases)
for i in petals:
    m = lab == i
    py, px = np.nonzero(m)
    d = (px - root[0]) ** 2 + (py - root[1]) ** 2
    base = np.array([px[d.argmin()], py[d.argmin()]], np.float32)
    # tip = pixel farthest from the base (not the root), so a curved outer petal still gets its true tip
    d2 = (px - base[0]) ** 2 + (py - base[1]) ** 2
    tip = np.array([px[d2.argmax()], py[d2.argmax()]], np.float32)
    axis = tip - base; L = float(np.hypot(*axis)); axis /= L
    perp = np.array([-axis[1], axis[0]], np.float32)
    u = ((xs - base[0]) * axis[0] + (ys - base[1]) * axis[1]) / L
    phases = rng.uniform(0, 2 * np.pi, 4)
    fields.append((np.clip(u, 0, 1), axis, perp, L, phases))
    print(f"  petal {i}: base {base.round()} tip {tip.round()} len {L:.0f}px  phases {np.round(phases, 2)}")

# which petal governs each pixel (so the warp field is defined just outside the petal edge too).
# Built from PETAL pixels only: the source has tiny semi-transparent specks along some petal crests, and if they
# took part in the nearest-petal assignment they would punch zero-displacement holes into the field right at the
# moving edge (seen as notches on the mid-tier petals). Specks now simply ride along with their nearest petal.
petal_mask = np.isin(lab, petals).astype(np.uint8)
print(f"non-petal specks ignored for ownership: {n - 1 - len(petals)} components, {int(mask.sum() - petal_mask.sum())} px")
dist, lbl = cv2.distanceTransformWithLabels((petal_mask == 0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
# DIST_LABEL_PIXEL numbers the zero pixels (petal_mask==1) 1..k in raster order; map that index back to a petal id
zero_idx = np.flatnonzero(petal_mask.ravel())                    # raster order == label numbering
pixel_label = lab.ravel()[zero_idx]                               # petal id of the k-th zero pixel
owner = np.zeros((H, W), np.int32)
inside = lbl > 0
owner[inside] = pixel_label[lbl[inside] - 1]
petal_pos = {i: k for k, i in enumerate(petals)}

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)

N = int(round(args.seconds * args.fps))
T = args.seconds
# wave set: (cycles per loop, relative amplitude, spatial lag in radians along the petal)
WAVES = [(2, 0.60, 1.4), (3, 0.30, 2.4), (5, 0.12, 3.2)]
norm = sum(a for _, a, _ in WAVES)

def displacement(t):
    dx = np.zeros((H, W), np.float32); dy = np.zeros((H, W), np.float32)
    for i in petals:
        u, axis, perp, L, ph = fields[petal_pos[i]]
        sel = owner == i
        if not sel.any():
            continue
        uu = u[sel]
        w = smoothstep(args.start, 1.0, uu) ** 1.4                 # body rigid, tip free
        s = sum(a * np.sin(2 * np.pi * c * t / T + ph[k] - lag * uu) for k, (c, a, lag) in enumerate(WAVES)) / norm
        reach = 0.22 * np.sin(2 * np.pi * 2 * t / T + ph[3] - 1.0 * uu)   # slight along-axis flicker
        amp = args.amp * L * w
        dx[sel] = amp * (s * perp[0] + reach * axis[0])
        dy[sel] = amp * (s * perp[1] + reach * axis[1])
    return dx, dy

# body stillness check region: u < start for every petal (pixels that must never change)
still = np.zeros((H, W), bool)
for i in petals:
    u = fields[petal_pos[i]][0]
    still |= (lab == i) & (u < args.start - 0.02)

# pixels that can ever move (warp weight > 0 for their owning petal); everything else is copied from the source
moving = np.zeros((H, W), bool)
for i in petals:
    moving |= (owner == i) & (fields[petal_pos[i]][0] > args.start - 0.01)
moving = cv2.dilate(moving.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)

prev = None; steps = []; first = None; body_err = 0.0
for f in range(N):
    t = f / args.fps
    dx, dy = displacement(t)
    if SS > 1:   # warp at SSx resolution with Lanczos, then area-average down: crisp, alias-free moving edges
        dxh = cv2.resize(dx, (W * SS, H * SS), interpolation=cv2.INTER_LINEAR)
        dyh = cv2.resize(dy, (W * SS, H * SS), interpolation=cv2.INTER_LINEAR)
        mx = (xs_hi - dxh + 0.5) * SS - 0.5; my = (ys_hi - dyh + 0.5) * SS - 0.5
        out = cv2.remap(prem_hi, mx, my, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        out = cv2.resize(np.clip(out, 0, 1), (W, H), interpolation=cv2.INTER_AREA)
    else:
        mx = xs - dx; my = ys - dy                                     # backward map
        out = cv2.remap(prem, mx, my, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    out = np.clip(out, 0, 1)
    out[~moving] = prem[~moving]                                    # rigid body: source pixels, untouched
    a = out[..., 3]
    rgb = np.where(a[..., None] > 1e-4, out[..., :3] / np.maximum(a, 1e-4)[..., None], 0)
    rgb = np.clip(rgb, 0, 1)
    out8 = (np.dstack([rgb, a]) * 255 + 0.5).astype(np.uint8)
    cv2.imwrite(os.path.join(frames_dir, f"f_{f:04d}.png"), cv2.cvtColor(out8, cv2.COLOR_RGBA2BGRA))
    body_err = max(body_err, float(np.abs(out[still] - prem[still]).max()))
    if prev is not None:
        steps.append(float(np.sqrt(np.mean((out - prev) ** 2))))
    if first is None:
        first = out
    prev = out
    if f % 30 == 0:
        print(f"frame {f}/{N}")
wrap = float(np.sqrt(np.mean((first - prev) ** 2)))
with open(os.path.join(args.out_dir, "steps.csv"), "w", newline="") as fh:
    wr = csv.writer(fh); wr.writerow(["step", "rms"])
    for k, s in enumerate(steps): wr.writerow([f"{k}->{k+1}", f"{s:.6f}"])
    wr.writerow([f"{N-1}->0 (wrap)", f"{wrap:.6f}"])
print(f"steps: mean {np.mean(steps):.5f} min {np.min(steps):.5f} max {np.max(steps):.5f}  wrap {wrap:.5f}")
print(f"max body (rigid region) deviation: {body_err*255:.3f}/255")

# ---------------------------------------------------------------- reports
def load(k):
    return cv2.imread(os.path.join(frames_dir, f"f_{k:04d}.png"), cv2.IMREAD_UNCHANGED)
def on_white(bgra):
    a = bgra[..., 3:4].astype(np.float32) / 255
    return (bgra[..., :3] * a + 255 * (1 - a)).astype(np.uint8)
strip = np.hstack([cv2.resize(on_white(load(k)), (W // 4, H // 4)) for k in [N - 3, N - 2, N - 1, 0, 1, 2]])
cv2.imwrite(os.path.join(args.out_dir, "seam_strip.png"), strip)
ks = np.linspace(0, N - 1, 12).astype(int)
tiles = [cv2.resize(on_white(load(k)), (W // 4, H // 4)) for k in ks]
sheet = np.vstack([np.hstack(tiles[r * 4:(r + 1) * 4]) for r in range(3)])
cv2.imwrite(os.path.join(args.out_dir, "sheet.png"), sheet)
# tip-motion overlay: max |displacement| across the loop over the source, to show exactly what moves
mag = np.zeros((H, W), np.float32)
for f in range(0, N, 6):
    dx, dy = displacement(f / args.fps); mag = np.maximum(mag, np.hypot(dx, dy))
heat = cv2.applyColorMap((np.clip(mag / max(mag.max(), 1e-6), 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
base_bgr = on_white(cv2.cvtColor((src * 255).astype(np.uint8), cv2.COLOR_RGBA2BGRA))
ov = (0.55 * base_bgr + 0.45 * heat).astype(np.uint8); ov[mask == 0] = base_bgr[mask == 0]
cv2.imwrite(os.path.join(args.out_dir, "motion_map.png"), ov)

# ---------------------------------------------------------------- encode
seq = os.path.join(frames_dir, "f_%04d.png")
common = [FF, "-y", "-loglevel", "error", "-framerate", str(args.fps), "-i", seq]
jobs = {
    "lotus_sway_alpha.webm": common + ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", str(args.crf),
                                       "-deadline", "best", "-cpu-used", "0", "-row-mt", "1", "-g", str(N), "-auto-alt-ref", "0"],
    "lotus_sway_alpha_prores4444.mov": common + ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"],
    "lotus_sway_white.mp4": common + ["-filter_complex", f"color=c=white:s={W}x{H}:r={args.fps}[bg];[bg][0:v]overlay=format=auto:shortest=1,format=yuv420p",
                                      "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-g", str(N), "-movflags", "+faststart"],
}
for name, cmd in jobs.items():
    outp = os.path.join(args.out_dir, name)
    rc = subprocess.run(cmd + [outp]).returncode
    print(f"{name}: {os.path.getsize(outp)/1e6:.2f} MB (rc {rc})")
