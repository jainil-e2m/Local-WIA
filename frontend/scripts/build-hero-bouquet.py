"""
Offline builder for the landing hero's turning bouquet.

    python3 scripts/build-hero-bouquet.py <source.mp4>

Writes public/landing/bouquet-loop.mp4 (stacked alpha: colour on top, matte
below — played by src/components/bouquet/) and public/landing/bouquet-still.webp
(the loop's first frame, with real alpha). Needs numpy and scipy; ffmpeg comes
from the repo's ffmpeg-static.

THE SOURCE. A generated 1280x720, 24fps clip of a tied bouquet turning on a
lit turquoise backdrop, petals falling. The owner asked for seconds 2-7. What
that window contains, measured (these numbers drive the constants below):

  - The backdrop is a lit gradient (#7dc2c2 top-left .. #94d0d1 mid-left ..
    #549d9b bottom-right), and the bouquet casts a darker shadow on it
    (#417874). A single key colour would leave halos and eat the blue-green
    eucalyptus, so each frame is keyed against its own clean plate.
  - Frames 44-53 carry a morph: a rose dissolves into a translucent ghost and
    a flower re-forms into a daisy. Nothing before frame 55 is used.
  - The camera drifts (~50 px across, ~27 px down) and zooms (head radius
    341 -> 293 -> 311 px). Both are removed: the head is locked to one centre
    and one size, so nothing breathes or slides.
  - The bouquet turns only ~105 degrees in the window (surface travel ~534 px
    at radius ~290 px; a full turn would need ~17 s of footage). No two frames
    a usable distance apart show the same view (best silhouette IoU 0.79 vs
    0.96 for neighbours), so the loop cannot close on a matching frame. It
    closes with a short dissolve at the least different pair instead.
  - The head touches the top edge in almost every frame and the stems run
    off the bottom, so the top and bottom fade out like the sides.

PIPELINE
  1. key every frame: clean-plate residual (shadow-aware), then an alpha solve
     and colour unmix against the nearest confidently opaque colour (kills the
     turquoise fringe), sparkle/glint removal, dark interior pockets filled.
  2. stabilise: smoothed head centroid and radius -> fixed centre and size.
  3. seam: on quarter-res stabilised heads, the (start, length) whose seam
     pairs differ least; a SEAM-frame dissolve closes the loop.
  4. fade every edge to zero before the frame border (no box), pad colours
     under transparency (no compression bleed), encode.
"""
import os
import subprocess
import sys

import numpy as np
from scipy import ndimage as ndi

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FF = os.path.join(ROOT, "node_modules", "ffmpeg-static", "ffmpeg")
OUT = os.path.join(ROOT, "public", "landing")
W, H, FPS = 1280, 720, 24

FIRST_OK = 55   # frames 44-53 morph (see above)
LAST = 168      # 7.0 s
SEAM = 8        # dissolve length at the loop point (1/3 s)
N_MIN = 90      # shortest acceptable loop (3.75 s)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def smoother(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * t * (t * (t * 6 - 15) + 10)


def load_frames(src):
    raw = subprocess.run([FF, "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (W * H * 3)
    return np.frombuffer(raw, np.uint8)[: n * W * H * 3].reshape(n, H, W, 3)


# ---------------------------------------------------------------- keying

def clean_plate(f):
    """The backdrop as it would look with nothing in front of it: a smooth fill
    from confidently-backdrop pixels (gradient AND floor shadow included)."""
    R, G, B = f[..., 0], f[..., 1], f[..., 2]
    mx = np.maximum(np.maximum(R, G), B) + 1.0
    conf = ((np.minimum(G, B) - R) / mx > 0.27) & (np.abs(G - B) / mx < 0.06)
    conf = ndi.binary_erosion(conf, iterations=3)
    k = 8
    hs, ws = H // k, W // k
    c = conf[: hs * k, : ws * k].reshape(hs, k, ws, k).mean(axis=(1, 3))
    plate = np.stack([(f[: hs * k, : ws * k, ch] * conf[: hs * k, : ws * k]).reshape(hs, k, ws, k).sum(axis=(1, 3)) / (k * k)
                      for ch in range(3)], -1)
    out = np.zeros_like(plate)
    filled = np.zeros((hs, ws), bool)
    for sigma in (1.5, 3, 6, 12, 24, 48):
        num = np.stack([ndi.gaussian_filter(plate[..., ch], sigma) for ch in range(3)], -1)
        den = ndi.gaussian_filter(c, sigma)[..., None]
        est = num / np.maximum(den, 1e-6)
        take = (~filled) & (den[..., 0] > 0.25)
        out[take] = est[take]
        filled |= take
    out[~filled] = est[~filled]
    return np.stack([ndi.zoom(out[..., ch], (H / hs, W / ws), order=1) for ch in range(3)], -1)[:H, :W]


def key_frame(f):
    """f: float32 HxWx3 in 0..255 -> (alpha 0..1, unmixed colour 0..255, bouquet mask)."""
    bg = clean_plate(f)
    s = np.clip(np.sum(f * bg, -1) / (np.sum(bg * bg, -1) + 1e-6), 0.3, 1.25)
    resid = np.linalg.norm(f - s[..., None] * bg, axis=-1)      # 0 for backdrop, shadow or vignette
    a0 = smoothstep(10.0, 26.0, resid)

    core = ndi.binary_erosion(a0 > 0.97, iterations=1)
    if core.any():
        _, (iy, ix) = ndi.distance_transform_edt(~core, return_indices=True)
        fnear = f[iy, ix]
    else:
        fnear = f.copy()
    band = ndi.binary_dilation((a0 > 0.01) & (a0 < 0.97), iterations=1)
    d = fnear - bg
    dd = np.sum(d * d, -1)
    a_solve = np.clip(np.sum((f - bg) * d, -1) / np.maximum(dd, 1e-6), 0, 1)
    alpha = np.where(band & (dd > 30.0 ** 2), a_solve, a0)
    alpha = np.where(core, 1.0, alpha)

    m = alpha > 0.35
    lab, n = ndi.label(m)
    keep = np.zeros(n + 1, bool)
    if n:
        areas = ndi.sum(m, lab, range(1, n + 1))
        for k, (sl, area) in enumerate(zip(ndi.find_objects(lab), areas), start=1):
            fill = area / float((sl[0].stop - sl[0].start) * (sl[1].stop - sl[1].start))
            px = f[sl][lab[sl] == k]
            cyan = float(np.mean((np.minimum(px[:, 1], px[:, 2]) - px[:, 0]) / (px.max(axis=1) + 1.0)))
            star = area < 500 and fill < 0.42      # four-armed sparkle glints
            glint = area < 1500 and cyan > 0.10    # bokeh: a brightened turquoise, not a petal
            keep[k] = not (star or glint or area < 70)
    keepmask = keep[lab]
    alpha = np.where(ndi.binary_dilation(keepmask, iterations=3), alpha, 0.0)
    bouquet = np.zeros_like(m)
    if n and keep.any():
        sizes = ndi.sum(keepmask, lab, range(1, n + 1)) * keep[1:]
        bouquet = lab == (1 + int(np.argmax(sizes)))
    # enclosed gaps: dark ones are shadow pockets (fill), bright ones are backdrop (keep clear)
    enclosed = ndi.binary_fill_holes(bouquet) & ~bouquet
    dark = smoothstep(0.78, 0.55, s)
    holes = enclosed & (dark > 0.5)
    alpha = np.where(enclosed, np.maximum(alpha, dark), alpha)

    a3 = np.clip(alpha, 1e-3, 1)[..., None]
    F = (f - (1 - a3) * bg) / a3
    w = smoothstep(0.08, 0.5, alpha)[..., None]
    F = w * F + (1 - w) * fnear
    F = np.where(holes[..., None], f, F)
    R, G, B = F[..., 0], F[..., 1], F[..., 2]
    spill = np.maximum(0, np.minimum(G, B) - R - 6)
    neutralish = 1 - smoothstep(10, 30, np.abs(G - B))
    edge = smoothstep(6, 0, ndi.distance_transform_edt(alpha > 0.5))
    F[..., 1:3] -= (spill * neutralish * (0.35 + 0.65 * edge))[..., None]
    return np.clip(alpha, 0, 1).astype(np.float32), np.clip(F, 0, 255).astype(np.float32), bouquet


def key_all(frames):
    # Held in memory (~0.45 GB for the window) rather than in temp files.
    n = LAST - FIRST_OK + 1
    col = np.empty((n, H, W, 3), np.uint8)
    alp = np.empty((n, H, W), np.uint8)
    disk = np.hypot(*np.mgrid[-10:11, -10:11]) <= 10
    stats = []
    for i in range(n):
        a, c, bouquet = key_frame(frames[FIRST_OK + i].astype(np.float32))
        col[i] = np.round(c).astype(np.uint8)
        alp[i] = np.round(a * 255).astype(np.uint8)
        head = ndi.binary_opening(ndi.binary_fill_holes(bouquet), structure=disk)
        lab, k = ndi.label(head)
        if k:
            head = lab == (1 + int(np.argmax(ndi.sum(head, lab, range(1, k + 1)))))
        ys, xs = np.nonzero(head)
        R, G, B = c[..., 0], c[..., 1], c[..., 2]
        turq = int(((a > 0.1) & (np.minimum(G, B) - R > 40) & (np.abs(G - B) < 18)).sum())
        stats.append(dict(frame=FIRST_OK + i, cx=float(xs.mean()), cy=float(ys.mean()), area=int(head.sum()), turquoise=turq))
        if i % 10 == 0:
            print(f"keyed frame {FIRST_OK + i}", flush=True)
    return col, alp, stats


# ---------------------------------------------------------------- loop

def build(col, alp, stats):
    n = len(stats)
    cxs = ndi.gaussian_filter1d(np.array([s["cx"] for s in stats]), 5, mode="nearest")
    cys = ndi.gaussian_filter1d(np.array([s["cy"] for s in stats]), 5, mode="nearest")
    Rs = ndi.gaussian_filter1d(np.sqrt(np.array([s["area"] for s in stats]) / np.pi), 8, mode="nearest")
    R_T = float(np.percentile(Rs, 40))       # near the typical size: little upscaling anywhere
    CW, CH = 1400, 820
    C = np.array([CW / 2, CH / 2 + 10])

    def stabilised(i, scale=1.0, cw=CW, ch=CH):
        k = R_T / Rs[i] * scale
        oy, ox = np.mgrid[0:ch, 0:cw].astype(np.float32)
        sy, sx = (oy - C[1] * scale) / k + cys[i], (ox - C[0] * scale) / k + cxs[i]
        a = alp[i].astype(np.float32) / 255
        out = np.empty((ch, cw, 4), np.float32)
        out[..., 3] = ndi.map_coordinates(a, [sy, sx], order=1, cval=0.0)
        for c in range(3):
            out[..., c] = ndi.map_coordinates(col[i][..., c].astype(np.float32) / 255 * a, [sy, sx], order=1, cval=0.0)
        return out

    # seam search: quarter-res stabilised heads
    q = 0.25
    cwq, chq = int(CW * q), int(CH * q)
    yy, xx = np.mgrid[0:chq, 0:cwq]
    head = np.hypot(xx - C[0] * q, yy - C[1] * q) < 0.85 * R_T * q
    T = np.stack([stabilised(i, q, cwq, chq)[head] for i in range(n)])
    D = np.stack([np.abs(T - T[a]).mean(axis=(1, 2)) for a in range(n)])
    best = None
    for j in range(n):
        for N in range(N_MIN, n):
            if j + N + SEAM - 1 >= n:
                break
            cost = float(np.mean([D[j + t, j + N + t] for t in range(SEAM)]))
            if best is None or cost - 0.00002 * N < best[0]:
                best = (cost - 0.00002 * N, cost, j, N)
    _, cost, j, N = best
    print(f"loop: source frames {FIRST_OK + j}..{FIRST_OK + j + N - 1} ({N} frames, {N / FPS:.2f}s); "
          f"seam difference {cost:.3f} vs {np.mean([D[t, t + 1] for t in range(n - 1)]):.3f} between neighbours")

    # crop: where every used frame has real pixels
    used = range(j, j + N + SEAM)
    boxes = np.array([(C[0] - cxs[i] * R_T / Rs[i], C[1] - cys[i] * R_T / Rs[i],
                       C[0] + (W - cxs[i]) * R_T / Rs[i], C[1] + (H - cys[i]) * R_T / Rs[i]) for i in used])
    left, top = np.ceil(boxes[:, :2].max(axis=0))
    right, bottom = np.floor(boxes[:, 2:].min(axis=0))
    OW, OH = int((right - left) // 16 * 16), int((bottom - top) // 16 * 16)
    ox0, oy0 = int(left + ((right - left) - OW) // 2), int(top)
    print(f"output {OW}x{OH}; head centre ({C[0] - ox0:.0f}, {C[1] - oy0:.0f}), radius {R_T:.0f}")

    gy, gx = np.mgrid[0:OH, 0:OW].astype(np.float32)
    fade = (smoother(0, 130, gx) * smoother(0, 130, OW - 1 - gx) * smoother(0, 64, gy) * smoother(0, 150, OH - 1 - gy))

    def frame(t):
        crop = lambda i: stabilised(i)[oy0:oy0 + OH, ox0:ox0 + OW]  # noqa: E731
        if t < SEAM:
            w = smoother(0, 1, (t + 0.5) / SEAM)
            f = (1 - w) * crop(j + N + t) + w * crop(j + t)
        else:
            f = crop(j + t)
        return f * fade[..., None]

    return frame, N, OW, OH, (float(C[0] - ox0), float(C[1] - oy0), R_T)


def pad_colour(rgb, a):
    """Smoothly extend edge colours under full transparency, so neither the codec
    nor texture filtering can bleed a wrong colour into an edge."""
    out, known = rgb.copy(), a > 0.02
    filled = known.copy()
    for sigma in (2, 6, 18, 54):
        wgt = ndi.gaussian_filter(known.astype(np.float32), sigma)
        est = np.stack([ndi.gaussian_filter(rgb[..., c] * known, sigma) for c in range(3)], -1) / np.maximum(wgt, 1e-6)[..., None]
        take = (~filled) & (wgt > 0.02)
        out[take] = est[take]
        filled |= take
    out[~filled] = rgb[known].mean(axis=0) if known.any() else 0.5
    return out


def export(frame, N, OW, OH):
    os.makedirs(OUT, exist_ok=True)
    enc = subprocess.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH * 2}",
                            "-r", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv",
                            "-c:v", "libx264", "-preset", "veryslow", "-crf", "22", "-pix_fmt", "yuv420p",
                            "-profile:v", "high", "-tune", "film", "-colorspace", "bt709", "-color_primaries", "bt709",
                            "-color_trc", "bt709", "-color_range", "tv", "-movflags", "+faststart", "-an",
                            os.path.join(OUT, "bouquet-loop.mp4")], stdin=subprocess.PIPE)
    worst_turq, worst_border = 0, 0.0
    for t in range(N):
        f = frame(t)
        a = f[..., 3]
        rgb = np.clip(np.where(a[..., None] > 1e-4, f[..., :3] / np.maximum(a[..., None], 1e-4), 0), 0, 1)
        rgb = pad_colour(rgb, a)
        enc.stdin.write((np.concatenate([rgb, np.repeat(a[..., None], 3, -1)], 0) * 255 + 0.5).clip(0, 255).astype(np.uint8).tobytes())
        R_, G_, B_ = rgb[..., 0] * 255, rgb[..., 1] * 255, rgb[..., 2] * 255
        worst_turq = max(worst_turq, int(((a > 0.1) & (np.minimum(G_, B_) - R_ > 40) & (np.abs(G_ - B_) < 18)).sum()))
        worst_border = max(worst_border, float(max(a[0].max(), a[-1].max(), a[:, 0].max(), a[:, -1].max())))
        if t == 0:
            rgba = (np.concatenate([rgb, a[..., None]], -1) * 255 + 0.5).clip(0, 255).astype(np.uint8)
            subprocess.run([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{OW}x{OH}", "-i", "-",
                            "-c:v", "libwebp", "-quality", "88", "-pix_fmt", "yuva420p",
                            os.path.join(OUT, "bouquet-still.webp")], input=rgba.tobytes(), check=True)
    enc.stdin.close()
    enc.wait()
    print(f"checks: turquoise pixels in the worst frame {worst_turq}; highest alpha on the frame border {worst_border:.4f}")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    frames = load_frames(sys.argv[1])
    col, alp, stats = key_all(frames)
    del frames
    frame, N, OW, OH, geo = build(col, alp, stats)
    export(frame, N, OW, OH)
    print("wrote public/landing/bouquet-loop.mp4 and bouquet-still.webp; frame geometry (cx, cy, r):", geo)


if __name__ == "__main__":
    main()
