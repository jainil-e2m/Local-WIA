"""
Shading-preserving rose recolour prototype (frame 6 of flowers_video.mp4).

FINAL METHOD
------------
Colour space: CIE Lab (D65, sRGB primaries), numpy implementation.  Output is composited
in Lab and converted back to sRGB once (float pipeline -> no banding).

Segmentation (prototype only, seeds hand-picked):
  class predicate on Lab (navy: L<46 & (b*<-10 | L<12); blue: 40<=L<85 & b*<-20 & C>24;
  cream: L>58 & C<24 & b*>3 & a*>-6, i.e. WARM low-chroma -> rejects the neutral grey
  background and cool leaves) & radius around the seed -> opening (per rose, 1..3 iterations
  to cut necks into touching roses) -> connected component containing the seed -> limited
  geodesic regrow -> closing + fill holes.
  alpha = 1 on the hard mask; OUTWARD gaussian tail (sigma 1.0) beyond a 1px dilation,
  multiplied by the SQUARED soft colour gate so mixed rose/leaf rim pixels are pushed toward
  "not rose" (kills both the dark seam and the pale halo).

Recolour (per rose, per target):
  1. shading signal S = V = max(R,G,B) in sRGB (on navy this keeps ~150 quantisation levels
     where L keeps ~10); t = (S - p1)/(p99 - p1) over the rose.
  2. t low-passed (sigma 0.8); when the rose is lifted >15 L (dark->light) a local-contrast
     boost k*(t - G4(t)), k<=0.6, re-strengthens petal-boundary shading that the generator
     crushed into the blacks.
  3. rank (CDF) matching of t onto the shading distribution of the reference class the target
     belongs to (navy / blue / cream pools measured on this frame), midpoint-CDF convention,
     blended 70/30 with identity, clamped to [0.03, 0.97].  This is what makes navy->cream a
     mostly-bright rose with dark crevices and cream->navy a mostly-dark rose with light rims.
  4. Lab ramp anchored at t=0.15 dark shade, t=0.5 base, t=0.85 light shade, piecewise-linear
     and extrapolated, so hue and chroma drift with lightness like real petals.
  5. high-frequency L residual of the source re-injected, scaled by target/source L range
     (clamped 0.5..2.6); chroma rolled off 35% at the brightest 10% (specular rims).
  Fade: out = lab + s*alpha*(new_lab - lab), s in [0,1] (Lab lerp = perceptually even fade).
"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
FRAME = os.path.join(HERE, "frame006.png")

# ----------------------------------------------------------------------------- colour
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
    return np.stack([L, a, b], -1)

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
    return rgb_to_lab(hex_to_rgb(h)[None, None])[0, 0]

def lab_to_hex(lab):
    return rgb_to_hex(lab_to_rgb(np.asarray(lab, np.float32)[None, None])[0, 0])

# ----------------------------------------------------------------------------- load
img = np.asarray(Image.open(FRAME).convert("RGB")).astype(np.float32) / 255
H, W, _ = img.shape
LAB = rgb_to_lab(img)
L, A, B = LAB[..., 0], LAB[..., 1], LAB[..., 2]
CHROMA = np.hypot(A, B)
yy, xx = np.mgrid[0:H, 0:W]

# ----------------------------------------------------------------------------- class pools (for measuring + reference shading CDFs)
bouquet_c = (640, 372); bouquet_r = 290
in_bouquet = (xx - bouquet_c[0]) ** 2 + (yy - bouquet_c[1]) ** 2 < bouquet_r ** 2
V = img.max(-1)  # HSV value = max sRGB channel: keeps far more quantisation levels than L on navy
def gate_navy(soft=False):
    # navy: dark and blue-ish.  soft version ramps membership over a band around each threshold.
    # near-black rim pixels (L<12) lose their hue in 8-bit: count them as navy regardless of b*
    if not soft: return (L < 46) & ((B < -10) | (L < 12))
    return np.maximum(np.clip((52 - L) / 12, 0, 1) * np.clip((-2 - B) / 10, 0, 1), np.clip((16 - L) / 6, 0, 1))
def gate_blue(soft=False):
    if not soft: return (L >= 40) & (L < 85) & (B < -20) & (CHROMA > 24)
    return np.clip((L - 34) / 8, 0, 1) * np.clip((88 - L) / 6, 0, 1) * np.clip((-12 - B) / 10, 0, 1)
def gate_cream(soft=False):
    # cream: light, low chroma, WARM (b*>3) -> excludes the neutral grey background and cool leaves
    if not soft: return (L > 58) & (CHROMA < 24) & (B > 3) & (A > -6)
    return np.clip((L - 50) / 10, 0, 1) * np.clip((30 - CHROMA) / 8, 0, 1) * np.clip((B + 1) / 5, 0, 1) * np.clip((A + 8) / 4, 0, 1)
GATES = {"navy": gate_navy, "blue": gate_blue, "cream": gate_cream}
cls_navy = in_bouquet & (L < 38) & (B < -10)
cls_blue = in_bouquet & gate_blue()
cls_cream = in_bouquet & gate_cream()
# remove thin speckle so baby's breath / tiny florets do not dominate the pools
cls_cream = ndi.binary_opening(cls_cream, iterations=3)
cls_navy = ndi.binary_opening(cls_navy, iterations=2)
cls_blue = ndi.binary_opening(cls_blue, iterations=1)

def pool_stats(m):
    Lp = L[m]; ap = A[m]; bp = B[m]
    med = np.array([np.median(Lp), np.median(ap), np.median(bp)])
    lo, hi = np.percentile(Lp, [3, 97])
    # dark shade = median a,b of the darkest 15%, light shade = of the lightest 15%
    dk = Lp <= np.percentile(Lp, 15); lt = Lp >= np.percentile(Lp, 85)
    dark = np.array([np.median(Lp[dk]), np.median(ap[dk]), np.median(bp[dk])])
    light = np.array([np.median(Lp[lt]), np.median(ap[lt]), np.median(bp[lt])])
    return dict(median=med, dark=dark, light=light, lo=lo, hi=hi, n=int(m.sum()))

def shading_cdf(m, nb=256):
    Vp = V[m]
    lo, hi = np.percentile(Vp, [1, 99])
    t = np.clip((Vp - lo) / max(hi - lo, 1e-3), 0, 1)
    h, _ = np.histogram(t, bins=nb, range=(0, 1))
    cdf = np.cumsum(h).astype(np.float64); cdf /= cdf[-1]
    return cdf

REF = {}
for name, m in [("navy", cls_navy), ("blue", cls_blue), ("cream", cls_cream)]:
    st = pool_stats(m)
    REF[name] = dict(stats=st, cdf=shading_cdf(m))
    print(f"class {name:5s} n={st['n']:6d} median={lab_to_hex(st['median'])} "
          f"dark={lab_to_hex(st['dark'])} light={lab_to_hex(st['light'])} "
          f"L range {st['lo']:.1f}..{st['hi']:.1f}  Lab med={np.round(st['median'],1)}")

# ----------------------------------------------------------------------------- palette
# Ramps: (dark, base, light) as hex.  Existing three are MEASURED from the frame pools.
def measured_entry(name, key):
    st = REF[key]['stats']
    return dict(name=name, hex=lab_to_hex(st['median']), dark=lab_to_hex(st['dark']),
                light=lab_to_hex(st['light']))

def synth_entry(name, base_hex, dL_dark=-24, dL_light=+16, c_dark=1.0, c_light=0.62, hue_shift_light=0.0):
    """Build dark/light shades from a base colour in Lab: darker + same/more chroma,
    lighter + less chroma (petal rims wash toward white), optional hue drift."""
    Lb, ab, bb = hex_to_lab(base_hex)
    dark = np.array([Lb + dL_dark, ab * c_dark, bb * c_dark])
    light = np.array([Lb + dL_light, ab * c_light, bb * c_light])
    if hue_shift_light:
        th = np.deg2rad(hue_shift_light); c, s = np.cos(th), np.sin(th)
        light[1], light[2] = light[1] * c - light[2] * s, light[1] * s + light[2] * c
    return dict(name=name, hex=base_hex, dark=lab_to_hex(dark), light=lab_to_hex(light))

def rose_entry(name, hard):
    """Measured from a hand-segmented rose: base = median Lab, dark/light = median Lab of the darkest/lightest 15%."""
    m = hard
    Lp, ap, bp = L[m], A[m], B[m]
    dk = Lp <= np.percentile(Lp, 15); lt = Lp >= np.percentile(Lp, 85)
    return dict(name=name,
                hex=lab_to_hex([np.median(Lp), np.median(ap), np.median(bp)]),
                dark=lab_to_hex([np.median(Lp[dk]), np.median(ap[dk]), np.median(bp[dk])]),
                light=lab_to_hex([np.median(Lp[lt]), np.median(ap[lt]), np.median(bp[lt])]))

PALETTE = [
    measured_entry("Midnight Navy (existing)", "navy"),
    measured_entry("Cornflower Blue (existing)", "blue"),
    measured_entry("Ivory Cream (existing)", "cream"),
    synth_entry("Periwinkle", "#8da1fd", dL_dark=-26, dL_light=+14, c_dark=1.05, c_light=0.55),
    synth_entry("Dusty Lilac", "#b1a4d6", dL_dark=-26, dL_light=+15, c_dark=1.15, c_light=0.55),
    synth_entry("Champagne", "#d2b494", dL_dark=-26, dL_light=+13, c_dark=1.2, c_light=0.6),
    synth_entry("Slate Blue", "#6c7fa8", dL_dark=-26, dL_light=+18, c_dark=1.1, c_light=0.6),
]
for p in PALETTE:
    Lb = hex_to_lab(p['hex'])[0]
    p['ref'] = 'navy' if Lb < 40 else ('blue' if Lb < 72 else 'cream')
    print(f"palette {p['name']:28s} base={p['hex']} dark={p['dark']} light={p['light']} L={Lb:.0f} ref={p['ref']}")

# ----------------------------------------------------------------------------- segmentation (prototype)
def segment_rose(seed, cls, radius, feather=1.0, open_iter=4):
    """Connected component of the class predicate containing the seed, radius-limited.
    alpha = feathered spatial mask x soft colour gate (so leaves in the feather band get ~0)."""
    x0, y0 = seed
    g = GATES[cls]
    within = g() & ((xx - x0) ** 2 + (yy - y0) ** 2 < radius ** 2)
    within = ndi.binary_opening(within, iterations=open_iter)
    lab_, n = ndi.label(within)
    lid = lab_[y0, x0]
    if lid == 0:
        sizes = ndi.sum(within, lab_, range(1, n + 1)); lid = 1 + int(np.argmax(sizes))
    hard = lab_ == lid
    if open_iter > 1:  # regrow: dilate the kept component and intersect with the ungated predicate (geodesic reconstruction, limited)
        grow = ndi.binary_dilation(hard, iterations=open_iter - 1)
        hard = grow & g() & ((xx - x0) ** 2 + (yy - y0) ** 2 < radius ** 2)
        hard = ndi.binary_opening(hard, iterations=1)
        lab2, _ = ndi.label(hard); hard = lab2 == lab2[y0, x0] if lab2[y0, x0] else hard
    hard = ndi.binary_closing(hard, iterations=3)
    hard = ndi.binary_fill_holes(hard)
    hard = ndi.binary_opening(hard, iterations=2)
    # feather OUTWARD: alpha=1 on the hard mask, a short gaussian tail beyond it (never eats into the rose)
    sp = ndi.gaussian_filter(ndi.binary_dilation(hard, iterations=1).astype(np.float32), feather)
    sp = np.where(hard, 1.0, sp).astype(np.float32)
    # in the tail, weight by the SQUARED soft colour gate: mixed rose/leaf pixels are pushed toward "not rose"
    soft = np.where(hard, 1.0, g(soft=True) ** 2)
    alpha = sp * soft
    core = ndi.binary_erosion(hard, iterations=3)
    alpha = np.where(core, sp, alpha)
    seedcol = np.median(LAB[y0 - 5:y0 + 6, x0 - 5:x0 + 6].reshape(-1, 3), axis=0)
    return hard, alpha.astype(np.float32), seedcol

# ----------------------------------------------------------------------------- recolour
def recolour(lab, hard, alpha, entry, detail_gain=1.15, match_strength=0.7, lp_sigma=0.8):
    """Shading-preserving recolour.
    shading signal S = V (max sRGB channel) -> relative t in the rose's own 1..99 pct range
    -> low-pass -> rank-matched onto the target class' shading CDF -> target Lab ramp
    (anchored: t=.15 dark shade, t=.5 base, t=.85 light shade, extrapolated beyond)
    + high-frequency L residual re-injected, scaled by the mapping's local slope."""
    Lsrc = lab[..., 0]
    S = V
    lo, hi = np.percentile(S[hard], [1, 99])
    t = np.clip((S - lo) / max(hi - lo, 1e-3), 0, 1)
    t_lp = ndi.gaussian_filter(t, lp_sigma)
    # local-contrast boost for crushed dark sources (navy interiors are 8-bit crushed by the generator):
    # strengthens petal-boundary shading before it is lifted into a light target. k scales with how
    # compressed the source range is relative to the target ramp.
    lift = hex_to_lab(entry['hex'])[0] - float(np.median(Lsrc[hard]))   # how far the rose is being lifted
    k_lc = float(np.clip((lift - 15.0) / 40.0, 0.0, 0.6))                 # 0 for same/darker, 0.6 for navy->cream
    if k_lc > 0:
        t_lp = np.clip(t_lp + k_lc * (t_lp - ndi.gaussian_filter(t_lp, 4.0)), 0, 1)
    nb = 256
    h, _ = np.histogram(t_lp[hard], bins=nb, range=(0, 1))
    src_cdf = np.cumsum(h).astype(np.float64); src_cdf /= src_cdf[-1]
    ref_cdf = REF[entry['ref']]['cdf']
    idx = np.clip((t_lp * (nb - 1)).astype(int), 0, nb - 1)
    cdf_prev = np.concatenate([[0.0], src_cdf[:-1]])
    u = 0.5 * (cdf_prev[idx] + src_cdf[idx])          # midpoint convention: a flat plateau maps to its rank centre
    grid = (np.arange(nb) + 0.5) / nb
    t_m = np.interp(u, ref_cdf, grid)
    t2 = np.clip(match_strength * t_m + (1 - match_strength) * t_lp, 0.03, 0.97)
    dk, bs, lt = hex_to_lab(entry['dark']), hex_to_lab(entry['hex']), hex_to_lab(entry['light'])
    tt = t2[..., None]
    lo_seg = dk + (bs - dk) * ((tt - 0.15) / 0.35)      # linear through (0.15,dark),(0.5,base)
    hi_seg = bs + (lt - bs) * ((tt - 0.5) / 0.35)       # linear through (0.5,base),(0.85,light)
    ramp = np.where(tt < 0.5, lo_seg, hi_seg)
    # high-frequency detail from source L, scaled by target/source dynamic range
    Lhf = Lsrc - ndi.gaussian_filter(Lsrc, lp_sigma)
    Lrange_src = max(np.percentile(Lsrc[hard], 99) - np.percentile(Lsrc[hard], 1), 1e-3)
    Lrange_tgt = (lt[0] - dk[0]) / 0.7
    gain = float(np.clip(Lrange_tgt / Lrange_src, 0.5, 2.6)) * detail_gain
    ramp[..., 0] += Lhf * gain
    ramp[..., 0] = np.clip(ramp[..., 0], 0, 100)
    # chroma roll-off toward the very brightest highlights (petal rim catching light)
    over = np.clip((t2 - 0.9) / 0.1, 0, 1)
    ramp[..., 1:] *= (1 - 0.35 * over)[..., None]
    return ramp

def composite(lab, new_lab, alpha, s=1.0):
    a = (alpha * s)[..., None]
    out = lab * (1 - a) + new_lab * a
    return out

# ----------------------------------------------------------------------------- helpers for output
def to_img(rgb):
    return Image.fromarray(np.clip(np.round(rgb * 255), 0, 255).astype(np.uint8))

def crop(rgb, cx, cy, half=95, scale=4):
    x0, y0 = max(cx - half, 0), max(cy - half, 0)
    c = rgb[y0:y0 + 2 * half, x0:x0 + 2 * half]
    im = to_img(c).resize((c.shape[1] * scale, c.shape[0] * scale), Image.LANCZOS)
    return im

def label(im, text):
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        f = ImageFont.load_default()
    d.rectangle([0, 0, im.width, 40], fill=(20, 20, 20))
    d.text((10, 6), text, fill=(255, 255, 255), font=f)
    return im

def sheet(panels, path):
    w = sum(p.width for p in panels); h = max(p.height for p in panels)
    s = Image.new("RGB", (w, h), (0, 0, 0)); x = 0
    for p in panels:
        s.paste(p, (x, 0)); x += p.width
    if s.width > 1600:
        s = s.resize((1600, int(s.height * 1600 / s.width)), Image.LANCZOS)
    s.save(path); return path

# ----------------------------------------------------------------------------- run
ROSES = {
    "navy":  dict(seed=(760, 300), cls="navy", radius=56, open_iter=3),   # 4: cuts the neck into the blue rose's shadow
    "cream": dict(seed=(640, 355), cls="cream", radius=58, open_iter=1),  # petals are split by thin crevices: keep light
    "blue":  dict(seed=(560, 270), cls="blue", radius=58, open_iter=1),
}
PAL = {p['name'].split(' (')[0]: p for p in PALETTE}

def refresh_measured(masks):
    for i, (nm, key) in enumerate([("Midnight Navy (existing)", "navy"), ("Cornflower Blue (existing)", "blue"), ("Ivory Cream (existing)", "cream")]):
        e = rose_entry(nm, masks[key][0]) if key == "cream" else measured_entry(nm, key)
        e['ref'] = key
        PALETTE[i] = e; PAL[nm.split(' (')[0]] = e
        print(f"measured {nm:28s} base={e['hex']} dark={e['dark']} light={e['light']}")
CASES = [
    ("navy",  "Ivory Cream",     "navy_to_cream"),
    ("cream", "Midnight Navy",   "cream_to_navy"),
    ("blue",  "Periwinkle",      "blue_to_periwinkle"),
    ("blue",  "Dusty Lilac",     "blue_to_lilac"),
    ("navy",  "Champagne",       "navy_to_champagne"),
    ("cream", "Slate Blue",      "cream_to_slate"),
]

if __name__ == "__main__":
    masks = {}
    ov = img.copy()
    for k, cfg in ROSES.items():
        hard, alpha, sc = segment_rose(cfg['seed'], cfg['cls'], cfg['radius'], open_iter=cfg['open_iter'])
        masks[k] = (hard, alpha)
        print(f"rose {k}: hard px={hard.sum()} alpha sum={alpha.sum():.0f} seed Lab={np.round(sc,1)} hex={lab_to_hex(sc)}")
        col = {"navy": (1, 0, 0), "cream": (0, 1, 0), "blue": (1, 0, 1)}[k]
        ov = ov * (1 - 0.5 * alpha[..., None]) + np.array(col) * 0.5 * alpha[..., None]
    to_img(ov[150:500, 450:900]).resize((900, 700)).save(os.path.join(HERE, "masks_overlay.png"))

    refresh_measured(masks)
    outs = []
    full = LAB.copy()
    for src, tgt, tag in CASES:
        hard, alpha = masks[src]
        entry = PAL[tgt]
        new = recolour(LAB, hard, alpha, entry)
        after = lab_to_rgb(composite(LAB, new, alpha, 1.0))
        mid = lab_to_rgb(composite(LAB, new, alpha, 0.5))
        cx, cy = ROSES[src]['seed']
        panels = [label(crop(img, cx, cy), f"before ({src})"),
                  label(crop(mid, cx, cy), "50% fade"),
                  label(crop(after, cx, cy), f"after -> {tgt}")]
        p = sheet(panels, os.path.join(HERE, f"ba_{tag}.png")); outs.append(p); print("wrote", p)
        if tag in ("navy_to_cream", "cream_to_navy", "blue_to_periwinkle"):
            full = composite(full, new, alpha, 1.0)
    fr = lab_to_rgb(full)
    to_img(fr[100:620, 360:920]).resize((1120, 1040), Image.LANCZOS).save(os.path.join(HERE, "context_all_three.png"))
    to_img(fr).save(os.path.join(HERE, "frame006_recoloured_full.png"))

    # palette sheet
    sw = Image.new("RGB", (7 * 220, 260), (236, 238, 242)); d = ImageDraw.Draw(sw)
    try: f = ImageFont.truetype("arial.ttf", 16)
    except Exception: f = ImageFont.load_default()
    for i, p in enumerate(PALETTE):
        x = i * 220 + 10
        for j, key in enumerate(['dark', 'hex', 'light']):
            c = tuple(int(v * 255) for v in hex_to_rgb(p[key]))
            d.rectangle([x, 10 + j * 60, x + 200, 60 + j * 60], fill=c)
            d.text((x + 6, 14 + j * 60), p[key], fill=(255, 255, 255) if hex_to_lab(p[key])[0] < 60 else (40, 40, 40), font=f)
        d.text((x, 200), p['name'][:26], fill=(30, 30, 30), font=f)
        d.text((x, 222), f"ref={p['ref']}", fill=(90, 90, 90), font=f)
    sw.save(os.path.join(HERE, "palette_sheet.png"))
    json.dump([{k: v for k, v in p.items()} for p in PALETTE], open(os.path.join(HERE, "palette.json"), "w"), indent=2)
