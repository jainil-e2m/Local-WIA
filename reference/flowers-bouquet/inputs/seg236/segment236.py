"""Segment individual roses on frame 236 of flowers_video.mp4 (port of segmentation/segment_roses.py from frame 6).
Inputs: base_f236.png, bouquet_alpha.png (from alpha236.py).  Outputs: label_map.npy, roses.json, overlay.png, debug_classmasks.png
Differences from the f6 script: no STATIC_PETALS / TABLE_PETALS carve-outs and no manual cream seed (f236 has no fallen
petals on the bouquet - verified at full resolution); bouquet region comes from bouquet_alpha.png; cream labels are dilated
2 px inside the alpha; roses.json uses the new schema with schedule flags.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1280, 720
FRAME = 236
CREAM_DIL = 2
# manual overrides filled in after visual review of overlay.png: id -> (schedule, note)
REVIEW = {
    11: (False, 'blue sliver at the left rim, mostly hidden behind cream 14 and leaves'),
    12: (False, 'whole rose but sits on the top silhouette; its outer petals are in the feathered alpha rim'),
    15: (False, 'right-rim rose, right half covered by eucalyptus leaves'),
    18: (False, 'bottom-right rose, leaves cross its lower half and it touches the rim'),
    19: (False, 'bottom-rim rose, partly under navy 5 and sprigs'),
}
# manual extra watershed seeds (x, y) per class for roses the peak finder merges
EXTRA_SEEDS = {'navy': [], 'blue': [], 'cream': []}


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
    seed = ndi.binary_opening(mask, disc(r))
    return ndi.binary_propagation(seed, mask=mask)


def watershed(mask, dist, markers):
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
    mask = mask.copy()
    cc, n = ndi.label(mask)
    sizes = ndi.sum(mask, cc, range(1, n + 1))
    mask &= np.isin(cc, [i + 1 for i, s in enumerate(sizes) if s >= min_area])
    dist = ndi.distance_transform_edt(mask)
    mx = ndi.maximum_filter(dist, footprint=disc(peak_r))
    peaks = (dist == mx) & (dist >= min_peak_dist)
    for (x, y) in extra_markers:
        if mask[y, x]:
            peaks[y, x] = True
    pk, _ = ndi.label(ndi.binary_dilation(peaks, disc(merge_r)) & mask)
    markers = np.where(peaks, pk, 0)
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
    img = np.asarray(Image.open(os.path.join(HERE, "base_f236.png")).convert("RGB"))
    f = img.astype(np.float32) / 255.
    alpha = np.asarray(Image.open(os.path.join(HERE, "bouquet_alpha.png"))).astype(np.float32) / 255.
    inb = alpha > 0.5
    h, s, v = rgb2hsv(f)
    warm = f[..., 0] - f[..., 2]
    green = (h >= 55) & (h < 170) & (s > 0.12)
    navy = (h >= 200) & (h <= 265) & (s > 0.45) & (v < 0.5) & inb
    blue = (h >= 195) & (h <= 245) & (s > 0.30) & (v >= 0.45) & inb
    creamA = (v > 0.45) & (s < 0.40) & ~green & (warm > 0.04) & ((h >= 10) & (h <= 48))
    creamB = (v > 0.70) & (s < 0.14) & ~green & (warm > 0.02)
    cream = (creamA | creamB) & inb & ~navy & ~blue
    cream = ndi.binary_closing(cream, disc(4))
    navy_m = opening_reconstruct(navy, 6)
    blue_m = opening_reconstruct(blue, 6)
    CREAM_OPEN_R = 18
    seed = ndi.binary_opening(cream, disc(CREAM_OPEN_R))
    cream_m = seed
    for _ in range(12):
        cream_m = ndi.binary_dilation(cream_m, disc(1)) & cream
    navy_m = ndi.binary_fill_holes(ndi.binary_closing(navy_m, disc(3)))
    blue_m = ndi.binary_fill_holes(ndi.binary_closing(blue_m, disc(3)))
    cream_m = ndi.binary_fill_holes(ndi.binary_closing(cream_m, disc(4)))
    cream_m &= ~(navy | blue)
    blue_m &= ~navy_m
    cream_m &= ~navy_m & ~blue_m
    labs = {}
    labs['navy'] = split_class(navy_m, 900, 22, 14, 14, EXTRA_SEEDS['navy'])
    labs['blue'] = split_class(blue_m, 900, 22, 14, 14, EXTRA_SEEDS['blue'])
    labs['cream'] = split_class(cream_m, 3000, 26, 18, 18, EXTRA_SEEDS['cream'])
    label = np.zeros((H, W), np.int32); cls_of = {}; nid = 0
    for c in ['navy', 'blue', 'cream']:
        L = labs[c]
        for i in range(1, L.max() + 1):
            nid += 1; label[L == i] = nid; cls_of[nid] = c
    # cream labels: dilate CREAM_DIL px inside the alpha, not into other labels / leaves / blue / navy pixels
    grow_ok = inb & (label == 0) & ~green & ~navy & ~blue
    for i in [k for k, c in cls_of.items() if c == 'cream']:
        m = label == i
        for _ in range(CREAM_DIL):
            m = (ndi.binary_dilation(m, disc(1)) & grow_ok) | m
        label[m & (label == 0)] = i
    label[~inb] = 0   # hole-filled class masks may spill a few px past the alpha at rim roses
    np.save(os.path.join(HERE, "label_map.npy"), label)
    # ---- stats
    a5 = alpha > 0.5; area_b = int(a5.sum()); cyb, cxb = ndi.center_of_mass(a5); req = float(np.sqrt(area_b / np.pi))
    rim = ndi.binary_dilation(~inb, disc(6))
    roses = []
    for i in range(1, nid + 1):
        m = label == i; area = int(m.sum()); cy, cx = ndi.center_of_mass(m)
        ys, xs = np.where(m); bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        ring = ndi.binary_dilation(m, disc(3)) & ~m
        touch = sorted(int(t) for t in np.unique(label[ring]) if t != 0 and t != i)
        on_rim = bool((m & rim).any())
        dist = ndi.distance_transform_edt(m); rmax = float(dist.max()); r_eq = float(np.sqrt(area / np.pi))
        fill = area / ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
        conf = 'high'; notes = []
        if on_rim:
            conf = 'partial'; notes.append('touches bouquet rim')
        if area < 2500:
            conf = 'partial'; notes.append('small area')
        if rmax < 0.55 * r_eq:
            conf = 'partial'; notes.append('thin/irregular (inscribed r %.0f vs eq r %.0f)' % (rmax, r_eq))
        if fill < 0.5:
            conf = 'partial'; notes.append('low bbox fill %.2f' % fill)
        sched = conf == 'high'
        if i in REVIEW:
            sched, n2 = REVIEW[i]; notes.append(n2); conf = 'high' if sched else 'partial'
        roses.append({'id': i, 'class': cls_of[i], 'cx': round(float(cx), 1), 'cy': round(float(cy), 1), 'area': area,
                      'bbox': bbox, 'touches': touch, 'confidence': conf, 'schedule': bool(sched), 'notes': '; '.join(notes)})
    counts = {c: sum(1 for r in roses if r['class'] == c) for c in ['navy', 'blue', 'cream']}
    out = {'frame': FRAME, 'centroid': [round(float(cxb), 1), round(float(cyb), 1)], 'equiv_radius': round(req, 1), 'roses': roses}
    json.dump(out, open(os.path.join(HERE, "roses.json"), "w"), indent=1)
    # ---- overlay (2x crop, contours in class colour, white = alpha 0.5 contour, '*' = schedule false)
    ys, xs = np.where(inb); y0, y1 = max(ys.min() - 20, 0), min(ys.max() + 20, H); x0, x1 = max(xs.min() - 20, 0), min(xs.max() + 20, W)
    S = 2; crop = img[y0:y1, x0:x1]; L = label[y0:y1, x0:x1]
    ov = Image.fromarray(crop).resize(((x1 - x0) * S, (y1 - y0) * S), Image.BICUBIC)
    Lb = np.kron(L, np.ones((S, S), np.int32))
    er = ndi.grey_erosion(Lb, footprint=disc(1)); dl = ndi.grey_dilation(Lb, footprint=disc(1))
    contour = (Lb != er) | (Lb != dl); ova = np.array(ov)
    colmap = {'navy': (255, 60, 60), 'blue': (255, 200, 0), 'cream': (0, 200, 255)}
    for i in range(1, nid + 1):
        ova[contour & ((Lb == i) | (dl == i))] = colmap[cls_of[i]]
    Ab = np.kron(inb[y0:y1, x0:x1], np.ones((S, S), bool)); ac = Ab & ~ndi.binary_erosion(Ab, disc(1)); ova[ac] = (255, 255, 255)
    ov = Image.fromarray(ova); d = ImageDraw.Draw(ov)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 24)
    except Exception:
        font = ImageFont.load_default()
    for r in roses:
        x = (r['cx'] - x0) * S; y = (r['cy'] - y0) * S; t = str(r['id']) + ('' if r['schedule'] else '*')
        bb = d.textbbox((x, y), t, font=font, anchor='mm')
        d.rectangle([bb[0] - 3, bb[1] - 2, bb[2] + 3, bb[3] + 2], fill=(0, 0, 0))
        d.text((x, y), t, fill=colmap[r['class']], font=font, anchor='mm')
    if ov.width > 1600:
        ov = ov.resize((1600, int(ov.height * 1600 / ov.width)), Image.LANCZOS)
    ov.save(os.path.join(HERE, "overlay.png"))
    dbg = np.zeros((H, W, 3), np.uint8); dbg[inb] = (40, 40, 40)
    dbg[navy_m] = (0, 0, 140); dbg[blue_m] = (90, 150, 255); dbg[cream_m] = (255, 240, 200)
    dbg[green & inb & ~navy_m & ~blue_m & ~cream_m] = (0, 120, 0)
    dbg[cream & inb & ~cream_m] = (140, 110, 60)   # raw cream dropped by the size gate (spray roses etc.)
    Image.fromarray(dbg[y0:y1, x0:x1]).save(os.path.join(HERE, "debug_classmasks.png"))
    print(json.dumps(counts), "centroid", out['centroid'], "req", out['equiv_radius'], "n", nid)
    for r in roses:
        print(r['id'], r['class'], r['cx'], r['cy'], r['area'], r['touches'], r['confidence'], r['notes'])


if __name__ == "__main__":
    main()
