"""
Production rose recolours for frame 236 (static bouquet base).

Driven by seg236/label_map.npy + roses.json on base_f236.png.  Lab pipeline from recolour_proto.py
(V-based shading, rank matching onto the reference class' shading CDF, anchored dark/base/light ramp,
HF re-injection, outward feather weighted by the squared class gate) with the critic fixes:
  (a) navy targets: light anchor is clamped (bisection on its offset from the base) until the recoloured
      rose's p90 V lies inside the real navy roses' p90-V range measured on f236.
  (b) ramp anchors sit at the ROSE'S OWN t quantiles (q10 / q50 / q90) so the recoloured median is the
      palette base by construction; specular chroma roll-off reduced to 20% over the top 5%.
  (c) soft mask: gaussian(sigma 1) of the label -> >0.5 -> outward feather (sigma 1 beyond a 1 px
      dilation) x squared source-class gate x bouquet alpha, zero on other roses' labels; one mask per rose.
  (d) navy->cream/champagne: local-contrast boost + HF gain kept; judged on the contact sheets.
Outputs (interface): base_lab.npy, recolour/r{ID}_{target}.npz (lab, alpha, bbox), palette.json,
fidelity.json, contact sheets, full_frame_demo.png.
"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
SEG = os.path.join(os.path.dirname(HERE), "seg236")
OUT = os.path.join(HERE, "recolour")
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------------------- colour (identical to recolour_proto.py)
def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def linear_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)

M_RGB2XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                      [0.2126729, 0.7151522, 0.0721750],
                      [0.0193339, 0.1191920, 0.9503041]], np.float32)
M_XYZ2RGB = np.linalg.inv(M_RGB2XYZ).astype(np.float32)
WP = np.array([0.95047, 1.0, 1.08883], np.float32)

def _f(t):
    d = 6 / 29
    return np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4 / 29)

def _finv(t):
    d = 6 / 29
    return np.where(t > d, t ** 3, 3 * d * d * (t - 4 / 29))

def rgb_to_lab(rgb):
    lin = srgb_to_linear(rgb)
    xyz = lin @ M_RGB2XYZ.T / WP
    f = _f(xyz)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], -1).astype(np.float32)

def lab_to_rgb(lab):
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200
    xyz = np.stack([_finv(fx), _finv(fy), _finv(fz)], -1) * WP
    lin = xyz @ M_XYZ2RGB.T
    return linear_to_srgb(lin)

def hex_to_rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255

def rgb_to_hex(rgb):
    r = np.clip(np.round(np.asarray(rgb) * 255), 0, 255).astype(int)
    return '#%02x%02x%02x' % tuple(r)

def hex_to_lab(h):
    return rgb_to_lab(hex_to_rgb(h)[None, None])[0, 0].astype(np.float64)

def lab_to_hex(lab):
    return rgb_to_hex(lab_to_rgb(np.asarray(lab, np.float32)[None, None])[0, 0])

def dE(l1, l2):
    return float(np.sqrt(np.sum((np.asarray(l1, np.float64) - np.asarray(l2, np.float64)) ** 2)))

# ----------------------------------------------------------------------------- load
img = np.asarray(Image.open(os.path.join(SEG, "base_f236.png")).convert("RGB")).astype(np.float32) / 255
H, W, _ = img.shape
LAB = rgb_to_lab(img)
np.save(os.path.join(HERE, "base_lab.npy"), LAB.astype(np.float32))
L, A, B = LAB[..., 0], LAB[..., 1], LAB[..., 2]
CHROMA = np.hypot(A, B)
V = img.max(-1)
LABEL = np.load(os.path.join(SEG, "label_map.npy"))
BALPHA = np.asarray(Image.open(os.path.join(SEG, "bouquet_alpha.png"))).astype(np.float32) / 255
ROSES = json.load(open(os.path.join(SEG, "roses.json")))["roses"]
RID = {r["id"]: r for r in ROSES}
CLASS_IDS = {c: [r["id"] for r in ROSES if r["class"] == c] for c in ("navy", "blue", "cream")}
SCHED = [r["id"] for r in ROSES if r["schedule"]]

# ----------------------------------------------------------------------------- class gates (soft membership, used squared in the feather band)
def gate_soft(cls, L=L, A=A, B=B, C=CHROMA):
    if cls == "navy":
        return np.maximum(np.clip((52 - L) / 12, 0, 1) * np.clip((-2 - B) / 10, 0, 1), np.clip((16 - L) / 6, 0, 1))
    if cls == "blue":
        return np.clip((L - 34) / 8, 0, 1) * np.clip((88 - L) / 6, 0, 1) * np.clip((-12 - B) / 10, 0, 1)
    return np.clip((L - 50) / 10, 0, 1) * np.clip((30 - C) / 8, 0, 1) * np.clip((B + 1) / 5, 0, 1) * np.clip((A + 8) / 4, 0, 1)

# ----------------------------------------------------------------------------- class pools (measured on f236 from the label map)
def pool_mask(cls):
    m = np.isin(LABEL, CLASS_IDS[cls])
    return ndi.binary_erosion(m, iterations=1)

def pool_stats(m):
    Lp, ap, bp = L[m], A[m], B[m]
    med = np.array([np.median(Lp), np.median(ap), np.median(bp)])
    dk = Lp <= np.percentile(Lp, 15); lt = Lp >= np.percentile(Lp, 85)
    dark = np.array([np.median(Lp[dk]), np.median(ap[dk]), np.median(bp[dk])])
    light = np.array([np.median(Lp[lt]), np.median(ap[lt]), np.median(bp[lt])])
    return dict(median=med, dark=dark, light=light, n=int(m.sum()))

def shading_cdf(m, nb=256):
    Vp = V[m]
    lo, hi = np.percentile(Vp, [1, 99])
    t = np.clip((Vp - lo) / max(hi - lo, 1e-3), 0, 1)
    h, _ = np.histogram(t, bins=nb, range=(0, 1))
    cdf = np.cumsum(h).astype(np.float64); cdf /= cdf[-1]
    return cdf

REF = {}
for cls in ("navy", "blue", "cream"):
    m = pool_mask(cls)
    REF[cls] = dict(stats=pool_stats(m), cdf=shading_cdf(m))

# real navy roses: p90 of V (0..255) per rose -> the admissible range for navy-target recolours
NAVY_P90 = {i: float(np.percentile(V[LABEL == i] * 255, 90)) for i in CLASS_IDS["navy"]}
NAVY_P90_RANGE = (min(NAVY_P90.values()), max(NAVY_P90.values()))

# ----------------------------------------------------------------------------- palette
BRIEF = {
    "navy":       dict(hex="#0f1437", dark="#05081e", light="#2a418f", ref_class="navy",  name="Midnight Navy"),
    "cornflower": dict(hex="#6683d0", dark="#4561b5", light="#8eacea", ref_class="blue",  name="Cornflower Blue"),
    "cream":      dict(hex="#d7d1c5", dark="#a49576", light="#ebe7dd", ref_class="cream", name="Ivory Cream"),
    "periwinkle": dict(hex="#8da1fd", dark="#3d5fb7", light="#c3c9fe", ref_class="blue",  name="Periwinkle"),
    "lilac":      dict(hex="#b1a4d6", dark="#6d6095", light="#d8d0ed", ref_class="blue",  name="Dusty Lilac"),
    "champagne":  dict(hex="#d2b494", dark="#8e6f4c", light="#eedac6", ref_class="cream", name="Champagne"),
    "slate":      dict(hex="#6c7fa8", dark="#264169", light="#a4aec8", ref_class="blue",  name="Slate Blue"),
}
CLASS_COLOUR = {"navy": "navy", "blue": "cornflower", "cream": "cream"}
PALETTE = {}
for k, e in BRIEF.items():
    e = dict(e); e["brief_hex"] = e["hex"]
    if k in ("navy", "cornflower", "cream"):
        st = REF[e["ref_class"]]["stats"]
        e["hex"], e["dark"], e["light"] = lab_to_hex(st["median"]), lab_to_hex(st["dark"]), lab_to_hex(st["light"])
        e["measured_on_f236"] = True
    e["lab"] = [round(float(x), 2) for x in hex_to_lab(e["hex"])]
    PALETTE[k] = e
TARGETS = list(BRIEF.keys())

# ----------------------------------------------------------------------------- soft masks (c)
FEATHER_MARGIN = 6
CREAM_OPEN_R = 5      # opening radius: removes label protrusions narrower than 2R+1 px (blossom spurs)
CREAM_REGROW = 3      # geodesic regrow inside the label: recovers shaved petal scallops, not the spurs

def rose_bbox(i):
    x0, y0, x1, y1 = RID[i]["bbox"]
    return (max(x0 - FEATHER_MARGIN, 0), max(y0 - FEATHER_MARGIN, 0), min(x1 + FEATHER_MARGIN, W), min(y1 + FEATHER_MARGIN, H))

def disc(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]; return (x * x + y * y) <= r * r

LUM = img.mean(-1)
LRANGE = ndi.maximum_filter(LUM, 5) - ndi.minimum_filter(LUM, 5)   # speckle texture (blossom clusters / baby's breath)

def largest(m):
    cc, n = ndi.label(m)
    if n <= 1: return m
    sz = ndi.sum(m, cc, range(1, n + 1)); return cc == (1 + int(np.argmax(sz)))

def rose_mask(i, refine=True):
    """Returns (bbox, hard, alpha) on the bbox crop.
    hard = gaussian(1.0) of the label > 0.5, then class-dependent refinement:
      cream : the label has spurs / lobes into adjacent white blossom clusters -> drop 'lobe' regions (dark-gap density
              rule, see code) near the boundary, opening disc(CREAM_OPEN_R), largest component, geodesic regrow
              CREAM_REGROW px inside the kept label, fill holes, smooth 0.8.
      navy/blue : the label stops ~1 px inside the dark/blue rim (a fringe of the old colour survives a light
              recolour) -> grow up to 2 px into pixels that still pass the source-class gate (>0.6) and belong
              to no other rose.
    alpha = 1 on hard; outward gaussian(1.0) tail beyond a 1 px dilation x squared source-class gate x bouquet
    alpha; zero on other roses' labels."""
    x0, y0, x1, y1 = rose_bbox(i)
    lab_c = LABEL[y0:y1, x0:x1]
    cls = RID[i]["class"]
    ind = (lab_c == i).astype(np.float32)
    hard0 = ndi.gaussian_filter(ind, 1.0) > 0.5
    other = (lab_c != 0) & (lab_c != i)
    g = gate_soft(cls, L[y0:y1, x0:x1], A[y0:y1, x0:x1], B[y0:y1, x0:x1], CHROMA[y0:y1, x0:x1])
    hard = hard0
    if refine and cls == "cream":
        # blossom lobes: label regions near the boundary whose 11x11 neighbourhood holds >= 22% dark gap pixels
        # (V < 0.45 inside the label).  Cream petals never do (their darkest crevices sit at V ~0.55-0.65);
        # the <= 2 px dark leaf band the segmentation's dilation added along the boundary stays below 0.18.
        dist_in = ndi.distance_transform_edt(hard0)
        dark_in = (V[y0:y1, x0:x1] < 0.45) & hard0
        dens = ndi.uniform_filter(dark_in.astype(np.float32), 11)
        lobe = ndi.binary_closing(dens >= 0.22, disc(3)) & hard0 & (dist_in <= 18)
        cc, n = ndi.label(lobe)
        if n:
            sz = ndi.sum(lobe, cc, range(1, n + 1)); lobe &= np.isin(cc, [k + 1 for k, a in enumerate(sz) if a >= 60])
        keep = hard0 & ~lobe
        core = largest(ndi.binary_opening(keep, disc(CREAM_OPEN_R)))
        hard = core
        for _ in range(CREAM_REGROW):
            hard = ndi.binary_dilation(hard, disc(1)) & keep
        hard = ndi.binary_fill_holes(hard)
        hard = ndi.gaussian_filter(hard.astype(np.float32), 0.8) > 0.5
    elif refine:
        grow = hard0
        for _ in range(2):
            grow = ndi.binary_dilation(grow, disc(1)) & (g > 0.6) & ~other | grow
        hard = grow
    hard &= ~other
    sp = ndi.gaussian_filter(ndi.binary_dilation(hard, iterations=1).astype(np.float32), 1.0)
    alpha = sp * g ** 2 * BALPHA[y0:y1, x0:x1]
    alpha[other] = 0
    alpha = np.where(hard, 1.0, alpha).astype(np.float32)
    return (x0, y0, x1, y1), hard, alpha

# ----------------------------------------------------------------------------- recolour
NB = 256

def piecewise(t, knots_t, knots_v, ext=0.6):
    """Piecewise-linear through (knots_t[k], knots_v[k]) with damped (ext x slope) extrapolation beyond the ends."""
    t = np.asarray(t, np.float64)
    out = np.empty(t.shape + (3,), np.float64)
    for ch in range(3):
        v = [k[ch] for k in knots_v]
        y = np.interp(t, knots_t, v)
        s0 = (v[1] - v[0]) / max(knots_t[1] - knots_t[0], 1e-3)
        s1 = (v[-1] - v[-2]) / max(knots_t[-1] - knots_t[-2], 1e-3)
        y = np.where(t < knots_t[0], v[0] + ext * s0 * (t - knots_t[0]), y)
        y = np.where(t > knots_t[-1], v[-1] + ext * s1 * (t - knots_t[-1]), y)
        out[..., ch] = y
    return out

def recolour_crop(i, target, bbox, hard, alpha, light_scale=1.0, k_lc_max=0.6, detail_gain=1.15,
                  match_strength=0.7, lp_sigma=0.8, roll=0.2, roll_from=0.95, ext=0.6,
                  gain_max=2.6, lc_sigma=4.0, denoise=0, hf_denoise=0):
    x0, y0, x1, y1 = bbox
    lab = LAB[y0:y1, x0:x1].astype(np.float64)
    Lsrc = lab[..., 0]
    S = V[y0:y1, x0:x1].astype(np.float64)
    if denoise: S = ndi.median_filter(S, denoise)
    entry = PALETTE[target]
    lo, hi = np.percentile(S[hard], [1, 99])
    t = np.clip((S - lo) / max(hi - lo, 1e-3), 0, 1)
    t_lp = ndi.gaussian_filter(t, lp_sigma)
    lift = hex_to_lab(entry["hex"])[0] - float(np.median(Lsrc[hard]))
    k_lc = float(np.clip((lift - 15.0) / 40.0, 0.0, k_lc_max))
    if k_lc > 0:
        t_lp = np.clip(t_lp + k_lc * (t_lp - ndi.gaussian_filter(t_lp, lc_sigma)), 0, 1)
    h, _ = np.histogram(t_lp[hard], bins=NB, range=(0, 1))
    src_cdf = np.cumsum(h).astype(np.float64); src_cdf /= src_cdf[-1]
    ref_cdf = REF[entry["ref_class"]]["cdf"]
    idx = np.clip((t_lp * (NB - 1)).astype(int), 0, NB - 1)
    cdf_prev = np.concatenate([[0.0], src_cdf[:-1]])
    u = 0.5 * (cdf_prev[idx] + src_cdf[idx])
    grid = (np.arange(NB) + 0.5) / NB
    t_m = np.interp(u, ref_cdf, grid)
    t2 = np.clip(match_strength * t_m + (1 - match_strength) * t_lp, 0.03, 0.97)
    q10, q50, q90 = np.percentile(t2[hard], [10, 50, 90])
    q10 = min(q10, q50 - 0.02); q90 = max(q90, q50 + 0.02)
    dk, bs, lt = hex_to_lab(entry["dark"]), hex_to_lab(entry["hex"]), hex_to_lab(entry["light"])
    lt = bs + light_scale * (lt - bs)
    ramp = piecewise(t2, [q10, q50, q90], [dk, bs, lt], ext=ext)
    Lhf_src = ndi.median_filter(Lsrc, hf_denoise) if hf_denoise else Lsrc
    Lhf = Lhf_src - ndi.gaussian_filter(Lhf_src, lp_sigma)
    Lrange_src = max(np.percentile(Lsrc[hard], 99) - np.percentile(Lsrc[hard], 1), 1e-3)
    Lrange_tgt = (lt[0] - dk[0]) / max(q90 - q10, 0.05)
    gain = float(np.clip(Lrange_tgt / Lrange_src, 0.5, gain_max)) * detail_gain
    ramp[..., 0] = np.clip(ramp[..., 0] + Lhf * gain, 0, 100)
    over = np.clip((t2 - roll_from) / (1 - roll_from), 0, 1)
    ramp[..., 1:] *= (1 - roll * over)[..., None]
    # outside the alpha support the file must equal base_lab so the compositor blend is exact
    out = np.where((alpha > 0)[..., None], ramp, lab).astype(np.float32)
    return out, dict(gain=gain, k_lc=k_lc, q=(float(q10), float(q50), float(q90)), light_scale=light_scale)

def measure(lab_c, hard, target):
    rgb = lab_to_rgb(lab_c)
    med = np.median(lab_c[hard].reshape(-1, 3), axis=0)
    med_rgb = lab_to_rgb(med.astype(np.float32)[None, None])[0, 0] * 255
    p90 = float(np.percentile(rgb[hard].max(-1) * 255, 90))
    return dict(median_lab=[round(float(x), 2) for x in med], median_rgb=[int(round(float(x))) for x in med_rgb],
                median_hex=lab_to_hex(med), dE=round(dE(med, hex_to_lab(PALETTE[target]["hex"])), 2), p90_V=round(p90, 1))

def build(i, target, bbox, hard, alpha, **kw):
    ls = 1.0; info = None
    lab_c, info = recolour_crop(i, target, bbox, hard, alpha, light_scale=ls, **kw)
    m = measure(lab_c, hard, target)
    if hex_to_lab(PALETTE[target]["hex"])[0] < 20:
        lo_lim, hi_lim = NAVY_P90_RANGE
        if m["p90_V"] > hi_lim:
            a, b = 0.0, 1.0
            for _ in range(14):
                ls = 0.5 * (a + b)
                lab_c, info = recolour_crop(i, target, bbox, hard, alpha, light_scale=ls, **kw)
                m = measure(lab_c, hard, target)
                if m["p90_V"] > hi_lim: b = ls
                elif m["p90_V"] < lo_lim: a = ls
                else: break
    return lab_c, m, info

# per-source-class recolour parameters.  Navy sources are 8-bit crushed: the shading signal is median-denoised,
# the HF gain is capped at 1.0 (no noise amplification) and petal-boundary shading is re-strengthened with a
# stronger local-contrast boost; rank matching is pushed to 0.9 so the lifted rose takes the target class'
# bright/flat shading distribution.
CLASS_PARAMS = {
    "navy":  dict(gain_max=1.0, k_lc_max=1.6, lc_sigma=2.5, denoise=3, hf_denoise=3, match_strength=0.9),
    "blue":  dict(),
    "cream": dict(),
}
# transitions dropped on visual grounds after the contact-sheet review (source class -> targets)
VISUAL_DROP = {"navy": set(), "blue": set(), "cream": set()}
DROP_REASON = {}
# visual quality notes from the contact-sheet review (allowed, but the weakest transitions)
QUALITY = {
    "navy->cream": "soft: petal structure is present at 2x/3x but mid-tones are greyer and softer than a real cream rose "
                   "(the 8-bit-crushed navy source carries little shading); smallest/occluded roses 1 and 4 are the weakest",
    "navy->champagne": "soft: same source limitation as navy->cream; reads as a satin champagne rose, best on roses 2, 3, 5",
    "cream->navy": "flat: dark rose with faint swirl, p90 V clamped into the real navy range; reads correctly at display size",
}

# ----------------------------------------------------------------------------- output helpers
def to_img(rgb):
    return Image.fromarray(np.clip(np.round(rgb * 255), 0, 255).astype(np.uint8))

def font(sz=20):
    try: return ImageFont.truetype("arial.ttf", sz)
    except Exception: return ImageFont.load_default()

def crop2x(rgb, cx, cy, half):
    x0, y0 = int(np.clip(cx - half, 0, W - 2 * half)), int(np.clip(cy - half, 0, H - 2 * half))
    c = rgb[y0:y0 + 2 * half, x0:x0 + 2 * half]
    return to_img(c).resize((c.shape[1] * 2, c.shape[0] * 2), Image.LANCZOS)

def label_img(im, text):
    d = ImageDraw.Draw(im); d.rectangle([0, 0, im.width, 24], fill=(20, 20, 20)); d.text((6, 3), text, fill=(255, 255, 255), font=font(17)); return im

def composite_full(items):
    """items: list of (bbox, lab_c, alpha) -> full-frame sRGB with those roses recoloured (s=1)."""
    lab = LAB.astype(np.float64).copy()
    for (x0, y0, x1, y1), lab_c, alpha in items:
        base = LAB[y0:y1, x0:x1].astype(np.float64)
        lab[y0:y1, x0:x1] = base + alpha[..., None] * (lab_c - base)
    return lab_to_rgb(lab.astype(np.float32))

# ----------------------------------------------------------------------------- run
if __name__ == "__main__":
    only = sys.argv[1:]   # optional: list of targets to (re)build
    print("pools:")
    for cls in ("navy", "blue", "cream"):
        st = REF[cls]["stats"]
        print(f"  {cls:5s} n={st['n']:6d} median={lab_to_hex(st['median'])} dark={lab_to_hex(st['dark'])} light={lab_to_hex(st['light'])} Lab={np.round(st['median'],1)}")
    print("navy p90 V per rose:", {k: round(v, 1) for k, v in NAVY_P90.items()}, "range", NAVY_P90_RANGE)
    for k, e in PALETTE.items():
        print(f"  palette {k:10s} hex={e['hex']} dark={e['dark']} light={e['light']} L={e['lab'][0]:.1f} ref={e['ref_class']}")

    masks = {i: rose_mask(i) for i in SCHED}
    fidelity = {}
    results = {}   # (i,target) -> (bbox, lab_c, alpha)
    for i in SCHED:
        bbox, hard, alpha = masks[i]
        cls = RID[i]["class"]
        for target in TARGETS:
            if target == CLASS_COLOUR[cls]: continue
            if only and target not in only: continue
            lab_c, m, info = build(i, target, bbox, hard, alpha, **CLASS_PARAMS[cls])
            fn = f"r{i}_{target}.npz"
            np.savez(os.path.join(OUT, fn), lab=lab_c.astype(np.float32), alpha=alpha.astype(np.float32),
                     bbox=np.array(bbox, np.int32))
            navy_t = hex_to_lab(PALETTE[target]["hex"])[0] < 20
            reasons = []
            if m["dE"] > 10: reasons.append(f"dE {m['dE']} > 10")
            elif m["dE"] > 8: reasons.append(f"dE {m['dE']} > 8 (warn)")
            if navy_t and not (NAVY_P90_RANGE[0] - 0.5 <= m["p90_V"] <= NAVY_P90_RANGE[1] + 0.5):
                reasons.append(f"p90 V {m['p90_V']} outside navy range {np.round(NAVY_P90_RANGE,1).tolist()}")
            m.update(file=fn, rose=i, src_class=cls, target=target, n_alpha_px=int((alpha > 0).sum()), n_hard_px=int(hard.sum()),
                     alpha_sum=round(float(alpha.sum()), 1), hf_gain=round(info["gain"], 3), k_lc=round(info["k_lc"], 3),
                     light_scale=round(info["light_scale"], 4), t_quantiles=[round(q, 3) for q in info["q"]],
                     numeric_pass=(m["dE"] <= 10) and not (navy_t and reasons and "p90" in " ".join(reasons)),
                     reason="; ".join(reasons) if reasons else "ok")
            fidelity[fn] = m
            results[(i, target)] = (bbox, lab_c, alpha)
            print(f"{fn:22s} med={m['median_hex']} dE={m['dE']:5.2f} p90V={m['p90_V']:5.1f} gain={info['gain']:.2f} klc={info['k_lc']:.2f} ls={info['light_scale']:.3f} {m['reason']}")
    # allowed = targets (not the class colour) where every scheduled rose of the class passes numerically
    allowed = {}
    for cls in ("navy", "blue", "cream"):
        ids = [i for i in SCHED if RID[i]["class"] == cls]
        al = []
        for t in TARGETS:
            if t == CLASS_COLOUR[cls]: continue
            ok = all(fidelity[f"r{i}_{t}.npz"]["numeric_pass"] for i in ids if f"r{i}_{t}.npz" in fidelity)
            if ok and t not in VISUAL_DROP[cls]: al.append(t)
            elif not ok: DROP_REASON[f"{cls}->{t}"] = "numeric: " + "; ".join(fidelity[f"r{i}_{t}.npz"]["reason"] for i in ids if not fidelity[f"r{i}_{t}.npz"]["numeric_pass"])
        allowed[cls] = al
    for cls, ts in VISUAL_DROP.items():
        for t in ts: DROP_REASON.setdefault(f"{cls}->{t}", "visual")
    # remove files of dropped transitions so the recolour/ folder holds only allowed pairs
    removed = []
    for fn in list(fidelity):
        m = fidelity[fn]
        if m["target"] not in allowed[m["src_class"]]:
            m["numeric_pass"] = False if not m["numeric_pass"] else m["numeric_pass"]
            m["dropped"] = True; m["drop_reason"] = DROP_REASON.get(f"{m['src_class']}->{m['target']}", "")
            pth = os.path.join(OUT, fn)
            if os.path.exists(pth): os.remove(pth); removed.append(fn)
    for fn, m in fidelity.items():
        m["pass"] = bool(m["numeric_pass"] and not m.get("dropped"))
    json.dump(dict(navy_p90_range=list(NAVY_P90_RANGE), navy_p90_per_rose=NAVY_P90, class_params=CLASS_PARAMS,
                   n_files_kept=len(fidelity) - len(removed), removed_files=removed, files=fidelity),
              open(os.path.join(HERE, "fidelity.json"), "w"), indent=1)
    pal = dict(colours={k: dict(hex=e["hex"], dark=e["dark"], light=e["light"], ref_class=e["ref_class"], lab=e["lab"],
                                name=e["name"], brief_hex=e["brief_hex"], measured_on_f236=e.get("measured_on_f236", False))
                        for k, e in PALETTE.items()},
               allowed=allowed, class_colour=CLASS_COLOUR, dropped=DROP_REASON, quality=QUALITY,
               notes="navy/cornflower/cream remeasured on f236 from the label-map pools (median Lab; dark/light = median of the "
                     "darkest/lightest 15% by L; brief_hex keeps the brief's values). Other colours: brief hex with the brief's "
                     "dark/light shades. Lab = CIE Lab D65 from sRGB, the same conversion as base_lab.npy and the npz files. "
                     "Recolour anchors sit at the rose's own t quantiles q10/q50/q90 so the median lands on hex; navy targets have "
                     f"the light anchor clamped so p90 V is within the real navy roses' range {np.round(NAVY_P90_RANGE,1).tolist()}. "
                     "Navy-source recolours use denoised shading, HF gain <= 1.0 and a stronger local-contrast boost (see fidelity.json class_params).")
    json.dump(pal, open(os.path.join(HERE, "palette.json"), "w"), indent=1)
    print("allowed", allowed, "dropped", DROP_REASON, "removed", len(removed))

    # ---------------- contact sheets: per class, 2 targets per sheet, rows = before / after T1 / after T2, columns = roses
    HALF = {"navy": 75, "blue": 65, "cream": 80}
    sheets = []
    for cls in ("navy", "blue", "cream"):
        ids = [i for i in SCHED if RID[i]["class"] == cls]
        tg = [t for t in TARGETS if t != CLASS_COLOUR[cls]]
        if only: tg = [t for t in tg if t in only]
        half = HALF[cls]; pw = 4 * half
        for k in range(0, len(tg), 2):
            pair = tg[k:k + 2]
            rows = 1 + len(pair)
            S = Image.new("RGB", (pw * len(ids), (pw + 26) * rows), (0, 0, 0))
            for c, i in enumerate(ids):
                cx, cy = int(RID[i]["cx"]), int(RID[i]["cy"])
                S.paste(label_img(crop2x(img, cx, cy, half), f"r{i} {cls} (before)"), (c * pw, 0))
                for r, t in enumerate(pair):
                    bbox, lab_c, alpha = results[(i, t)]
                    full = composite_full([(bbox, lab_c, alpha)])
                    m = fidelity[f"r{i}_{t}.npz"]
                    S.paste(label_img(crop2x(full, cx, cy, half), f"r{i} -> {t}  dE {m['dE']:.1f}"), (c * pw, (r + 1) * (pw + 26)))
            if S.width > 1600: S = S.resize((1600, int(S.height * 1600 / S.width)), Image.LANCZOS)
            p = os.path.join(HERE, f"sheet_{cls}_{'_'.join(pair)}.png"); S.save(p); sheets.append(p); print("sheet", p)

    # ---------------- 3x rim checks: light->dark and dark->light edges
    def crop3(rgb, cx, cy, half=48):
        c = rgb[cy - half:cy + half, cx - half:cx + half]; return to_img(c).resize((half * 6, half * 6), Image.LANCZOS)
    rim = [(13, "navy"), (16, "slate"), (1, "cream"), (5, "champagne"), (8, "cream"), (9, "champagne")]
    rim = [d for d in rim if d in results]
    panels = []
    for i, t in rim:
        bbox, lab_c, alpha = results[(i, t)]
        cx, cy = int(RID[i]["cx"]), int(RID[i]["cy"])
        full = composite_full([(bbox, lab_c, alpha)])
        panels.append((label_img(crop3(img, cx, cy), f"r{i} before"), label_img(crop3(full, cx, cy), f"r{i} -> {t} (3x)")))
    if panels:
        pw = panels[0][0].width
        S = Image.new("RGB", (pw * len(panels), 2 * (pw + 26)), (0, 0, 0))
        for c, (a, b) in enumerate(panels):
            S.paste(a, (c * pw, 0)); S.paste(b, (c * pw, pw + 26))
        if S.width > 1600: S = S.resize((1600, int(S.height * 1600 / S.width)), Image.LANCZOS)
        S.save(os.path.join(HERE, "sheet_rim_check_3x.png")); print("rim sheet")

    # ---------------- full frame demo: four roses, four targets, mixed classes
    demo = [(2, "champagne"), (8, "lilac"), (16, "navy"), (10, "periwinkle")]
    demo = [d for d in demo if d in results]
    full = composite_full([results[d] for d in demo])
    x0, y0, x1, y1 = 330, 40, 960, 700
    im = to_img(full[y0:y1, x0:x1]); im = im.resize((540, int(im.height * 540 / im.width)), Image.LANCZOS)
    im.save(os.path.join(HERE, "full_frame_demo.png"))
    to_img(full[y0:y1, x0:x1]).save(os.path.join(HERE, "full_frame_demo_1x.png"))
    print("demo", demo)
