"""Segment individual roses on a base frame of flowers_video.mp4 and build the bouquet alpha mask.
Outputs (in this folder): label_map.npy, bouquet_mask.png, overlay.png, roses.json, debug_classmasks.png
"""
import json, subprocess, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = "C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/frontend/public/flowers_video.mp4"
FF = "C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/frontend/node_modules/ffmpeg-static/ffmpeg.exe"
W, H = 1280, 720
FRAME = 6
# manual overrides (source-pixel x,y on frame 6), justified in main():
STATIC_PETALS = [(975, 399), (613, 607)]          # not roses: excluded from the label map
TABLE_PETALS = [(975, 399, 'dark'), (545, 688, 'light')]  # lying on the table: carved out of the alpha too
EXTRA_CREAM_SEEDS = [(634, 595)]


def load_frame(idx):
    p = subprocess.Popen([FF, "-v", "error", "-i", SRC, "-frames:v", str(idx + 1), "-an", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "pipe:1"], stdout=subprocess.PIPE)
    d = p.stdout.read(); p.wait()
    return np.frombuffer(d, np.uint8).reshape(-1, H, W, 3)[idx].copy()


def rgb2hsv(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a.max(2); mn = a.min(2); d = mx - mn; dd = np.where(d == 0, 1, d)
    h = np.where(mx == r, ((g - b) / dd) % 6, np.where(mx == g, (b - r) / dd + 2, (r - g) / dd + 4)) * 60
    h = np.where(d > 1e-6, h, 0)
    s = np.where(mx > 0, d / np.where(mx == 0, 1, mx), 0)
    return h, s, mx


def disc(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y) <= r * r


def opening_reconstruct(mask, r):
    """Open with a disc, then geodesic-reconstruct inside the original mask so petal edges come back
    but thin/small structures (baby's breath, stems) that were fully removed by the opening stay gone."""
    seed = ndi.binary_opening(mask, disc(r))
    prev = None; cur = seed
    while prev is None or (cur != prev).any():
        prev = cur
        cur = ndi.binary_dilation(cur, disc(1)) & mask
    return cur


def watershed(mask, dist, markers):
    """Marker-based watershed on -dist inside mask: level-set flooding by geodesic dilation of labels."""
    lab = markers.copy()
    levels = np.unique(np.round(dist[mask]).astype(int))[::-1]
    st = ndi.generate_binary_structure(2, 1)
    for lv in levels:
        active = mask & (dist >= lv - 0.5)
        while True:
            grown = ndi.grey_dilation(lab, footprint=st)
            new = (lab == 0) & active & (grown > 0)
            if not new.any():
                break
            lab = np.where(new, grown, lab)
    return lab


def split_class(mask, min_area, peak_r, min_peak_dist, merge_r, extra_markers=()):
    """Return int label map of individual roses within a binary class mask."""
    mask = mask.copy()
    cc, n = ndi.label(mask)
    sizes = ndi.sum(mask, cc, range(1, n + 1))
    keep = np.isin(cc, [i + 1 for i, s in enumerate(sizes) if s >= min_area])
    mask &= keep
    dist = ndi.distance_transform_edt(mask)
    mx = ndi.maximum_filter(dist, footprint=disc(peak_r))
    peaks = (dist == mx) & (dist >= min_peak_dist)
    for (x, y) in extra_markers:   # manual seeds (x,y) for roses the peak finder misses
        if mask[y, x]:
            peaks[y, x] = True
    # merge peaks that are close (plateaus / twin maxima)
    pk, _ = ndi.label(ndi.binary_dilation(peaks, disc(merge_r)) & mask)
    markers = np.where(peaks, pk, 0)
    # every component must have at least one marker; if not, mark its max
    cc, n = ndi.label(mask)
    for i in range(1, n + 1):
        comp = cc == i
        if not (markers[comp] > 0).any():
            idx = np.argmax(np.where(comp, dist, -1)); markers.flat[idx] = markers.max() + 1
    lab = watershed(mask, dist, markers)
    ids = np.unique(lab); ids = ids[ids > 0]
    out = np.zeros_like(lab)
    for k, i in enumerate(ids, 1):
        out[lab == i] = k
    return out


def main():
    img = load_frame(FRAME)
    f = img.astype(np.float32) / 255.
    h, s, v = rgb2hsv(f)

    # ---------- bouquet mask ----------
    border = np.concatenate([f[:8].reshape(-1, 3), f[-8:].reshape(-1, 3), f[:, :8].reshape(-1, 3), f[:, -8:].reshape(-1, 3)])
    bg = np.median(border, 0)
    diff = np.abs(f - bg).max(2)
    chroma = f.max(2) - f.min(2)
    warm = f[..., 0] - f[..., 2]
    # The table has a soft neutral-grey shadow on the right (chroma <= 0.02, v ~0.77-0.88) that a plain
    # difference threshold floods into. Every real bouquet element is either chromatic (leaves, roses,
    # cream petals have chroma >= 0.035) or dark (navy, deep leaf shadows). Neutral white baby's breath
    # at the very rim is lost by this rule (it is hole-filled where surrounded).
    # The Veo render has a soft light-grey halo (~6-10 px) around every leaf; a loose threshold pulls that
    # halo in as opaque and even connects fallen petals on the table. So: tight core, then a trimap.
    def largest_filled(m, close_r):
        m = ndi.binary_fill_holes(ndi.binary_closing(m, disc(close_r)))
        cc, n = ndi.label(m)
        sizes = ndi.sum(m, cc, range(1, n + 1))
        return cc == (int(np.argmax(sizes)) + 1)
    loose = largest_filled((chroma > 0.035) | (v < 0.62), 4)
    loose = ndi.binary_fill_holes(ndi.binary_closing(loose, disc(6)))
    tight = largest_filled((chroma > 0.06) | (v < 0.58), 3)          # excludes the halo; petals on the table disconnect
    # carve fallen petals lying on the TABLE that touch the rim (verified visually): a navy petal at right
    # (touches a leaf) and a white petal at the bottom (inside the 10 px band). Local colour blob around the point.
    yy, xx = np.ogrid[:H, :W]
    carve = np.zeros((H, W), bool)
    for (sx, sy, kind) in TABLE_PETALS:
        near = ((xx - sx) ** 2 + (yy - sy) ** 2) <= 45 ** 2
        blob = ((v < 0.50) if kind == 'dark' else ((v > 0.60) & (v < 0.91) & (chroma < 0.07))) & near
        cc, n = ndi.label(blob)
        k = cc[sy, sx]
        if k:
            carve |= ndi.binary_dilation(cc == k, disc(4))
    tight &= ~carve
    bou = loose & ndi.binary_dilation(tight, disc(10)) & ~carve       # loose mask, trimmed to the tight mass
    bou = ndi.binary_fill_holes(bou)
    # trimap: opaque core = bou eroded 7 px (the halo band is never in the core); in the band the alpha is a
    # soft matte = difference from the flat table colour. Leaf shadows/halo run ~10 px at diff 5..30/255, so the
    # ramp starts at 18/255 (0.07) and saturates at ~57/255 (0.22).
    core = ndi.binary_erosion(bou, disc(7))
    soft = np.clip((diff - 0.07) / 0.15, 0, 1)
    alpha = np.where(core, 1.0, np.where(bou, soft, 0.0)).astype(np.float32)
    alpha = ndi.gaussian_filter(alpha, 0.7)  # ~1 px feather
    Image.fromarray((alpha * 255).astype(np.uint8)).save(os.path.join(HERE, "bouquet_mask.png"))
    rgba = np.dstack([img, (alpha * 255).astype(np.uint8)])
    Image.fromarray(rgba).save(os.path.join(HERE, "base_rgba_preview.png"))
    # alpha check: composite over dark slate + 3x zooms of hard spots (cream rim top, thin leaves left/bottom)
    dark = np.array([40, 44, 52], np.float32)
    comp = (f * alpha[..., None] + dark / 255. * (1 - alpha[..., None]))
    comp8 = (comp * 255).astype(np.uint8)
    ys_, xs_ = np.where(alpha > 0.01)
    cy0, cy1, cx0, cx1 = ys_.min(), ys_.max(), xs_.min(), xs_.max()
    whole = Image.fromarray(comp8[cy0:cy1, cx0:cx1])
    whole = whole.resize((900, int(whole.height * 900 / whole.width)))
    zooms = [comp8[40:200, 560:760], comp8[380:540, 280:480], comp8[560:720, 500:700]]
    sheet = Image.new("RGB", (900 + 600, max(whole.height, 3 * 480)), (0, 0, 0))
    sheet.paste(whole, (0, 0))
    for i, z in enumerate(zooms):  # 3x zoom of a 200x160 patch
        sheet.paste(Image.fromarray(z).resize((600, 480), Image.LANCZOS), (900, i * 480))
    sheet.save(os.path.join(HERE, "alpha_check.png"))

    # ---------- class masks ----------
    inb = bou
    green = (h >= 55) & (h < 170) & (s > 0.12)
    navy = (h >= 200) & (h <= 265) & (s > 0.45) & (v < 0.5) & inb
    blue = (h >= 195) & (h <= 245) & (s > 0.30) & (v >= 0.45) & inb
    # cream roses: warm (r-b >= 0.04), low-moderate saturation, hue in the tan band. Baby's breath is
    # neutral (warm ~0.01) -> excluded by warmth; spray roses share the colour and are excluded by SIZE
    # below (they are ~20 px radius vs ~45 px for a cream rose). Yellow-green buds (h > 48) go to green.
    creamA = (v > 0.45) & (s < 0.40) & ~green & (warm > 0.04) & ((h >= 10) & (h <= 48))       # tan cores / folds
    creamB = (v > 0.70) & (s < 0.14) & ~green & (warm > 0.02)                                  # near-white petal tips
    cream = (creamA | creamB) & inb & ~navy & ~blue
    cream = ndi.binary_closing(cream, disc(4))  # bridge petal-edge lines inside a rose
    navy_m = opening_reconstruct(navy, 6)
    blue_m = opening_reconstruct(blue, 6)
    # size gate: open with a large disc (kills spray roses / baby's breath), then grow back a limited
    # number of steps inside the class mask so petal edges return but neighbouring spray roses do not
    CREAM_OPEN_R = 18
    seed = ndi.binary_opening(cream, disc(CREAM_OPEN_R))
    cream_m = seed
    for _ in range(12):
        cream_m = ndi.binary_dilation(cream_m, disc(1)) & cream
    # manual rescue: cream rose half-hidden at the bottom rim (source ~634,595) is real but too fragmented
    # for the size gate. Take the raw cream mask within 48 px of the seed, opened gently.
    for (sx, sy) in EXTRA_CREAM_SEEDS:
        yy, xx = np.ogrid[:H, :W]
        near = ((xx - sx) ** 2 + (yy - sy) ** 2) <= 48 ** 2
        loc = ndi.binary_opening(cream & near, disc(7))
        cc, n = ndi.label(loc)
        if n:
            sizes = ndi.sum(loc, cc, range(1, n + 1)); big = int(np.argmax(sizes)) + 1
            cream_m |= (cc == big)
    navy_m = ndi.binary_fill_holes(ndi.binary_closing(navy_m, disc(3)))
    blue_m = ndi.binary_fill_holes(ndi.binary_closing(blue_m, disc(3)))
    cream_m = ndi.binary_fill_holes(ndi.binary_closing(cream_m, disc(4)))
    cream_m &= ~(navy | blue)  # hole-filling must not swallow an adjacent blue petal into a cream rose
    # manual exclusion of STATIC FALLEN PETALS that sit inside the bouquet mask (verified visually):
    # a navy petal lying on the table at the right rim and a light-blue petal lying on greenery at the bottom.
    for (sx, sy) in STATIC_PETALS:
        for m in (navy_m, blue_m, cream_m):
            cc, n = ndi.label(m)
            k = cc[sy, sx]
            if k:
                m &= ~(cc == k)
    blue_m &= ~navy_m
    cream_m &= ~navy_m & ~blue_m

    labs = {}
    labs['navy'] = split_class(navy_m, min_area=900, peak_r=22, min_peak_dist=14, merge_r=14)
    labs['blue'] = split_class(blue_m, min_area=900, peak_r=22, min_peak_dist=14, merge_r=14)
    labs['cream'] = split_class(cream_m, min_area=3000, peak_r=26, min_peak_dist=18, merge_r=18)

    label = np.zeros((H, W), np.int32); cls_of = {}
    nid = 0
    for c in ['navy', 'blue', 'cream']:
        L = labs[c]
        for i in range(1, L.max() + 1):
            nid += 1; label[L == i] = nid; cls_of[nid] = c
    np.save(os.path.join(HERE, "label_map.npy"), label)

    # ---------- per-rose stats ----------
    roses = []
    ids = list(range(1, nid + 1))
    for i in ids:
        m = label == i
        area = int(m.sum()); cy, cx = ndi.center_of_mass(m)
        ring = ndi.binary_dilation(m, disc(3)) & ~m
        touch = sorted(int(t) for t in np.unique(label[ring]) if t != 0 and t != i)
        partial = bool((ring & ~bou).any())
        conf = 'high'
        if partial:
            conf = 'medium (touches bouquet rim, likely partial)'
        if area < 2000:
            conf = 'low (small)'
        roses.append(dict(id=i, colour_class=cls_of[i], cx=round(float(cx), 1), cy=round(float(cy), 1),
                          area_px=area, touches=touch, confidence=conf))
    counts = {c: sum(1 for r in roses if r['colour_class'] == c) for c in ['navy', 'blue', 'cream']}
    json.dump(dict(frame=FRAME, roses=roses, counts=counts), open(os.path.join(HERE, "roses.json"), "w"), indent=1)

    # ---------- overlay ----------
    ys, xs = np.where(bou)
    y0, y1 = max(ys.min() - 30, 0), min(ys.max() + 30, H); x0, x1 = max(xs.min() - 30, 0), min(xs.max() + 30, W)
    crop = img[y0:y1, x0:x1]; L = label[y0:y1, x0:x1]
    S = 2
    ov = Image.fromarray(crop).resize(((x1 - x0) * S, (y1 - y0) * S), Image.BICUBIC)
    Lb = np.kron(L, np.ones((S, S), np.int32))
    er = ndi.grey_erosion(Lb, footprint=disc(1)); dl = ndi.grey_dilation(Lb, footprint=disc(1))
    contour = (Lb != er) | (Lb != dl)
    ova = np.array(ov)
    colmap = {'navy': (255, 60, 60), 'blue': (255, 200, 0), 'cream': (0, 200, 255)}
    for i in ids:
        cm = contour & ((Lb == i) | (dl == i))
        ova[cm] = colmap[cls_of[i]]
    ov = Image.fromarray(ova); d = ImageDraw.Draw(ov)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
    for r in roses:
        x = (r['cx'] - x0) * S; y = (r['cy'] - y0) * S; t = str(r['id'])
        bb = d.textbbox((x, y), t, font=font, anchor='mm')
        d.rectangle([bb[0] - 3, bb[1] - 2, bb[2] + 3, bb[3] + 2], fill=(0, 0, 0))
        d.text((x, y), t, fill=colmap[r['colour_class']], font=font, anchor='mm')
    if ov.width > 1600:
        ov = ov.resize((1600, int(ov.height * 1600 / ov.width)), Image.LANCZOS)
    ov.save(os.path.join(HERE, "overlay.png"))
    dbg = np.zeros((H, W, 3), np.uint8)
    dbg[navy_m] = (0, 0, 140); dbg[blue_m] = (90, 150, 255); dbg[cream_m] = (255, 240, 200)
    dbg[green & inb & ~navy_m & ~blue_m & ~cream_m] = (0, 120, 0)
    Image.fromarray(dbg[y0:y1, x0:x1]).save(os.path.join(HERE, "debug_classmasks.png"))
    print(json.dumps(counts)); print("bg", bg * 255, "bouquet bbox", x0, y0, x1, y1, "n roses", nid)
    for r in roses:
        print(r)


if __name__ == "__main__":
    main()
