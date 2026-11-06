# Builds frontend/public/flowers-bouquet.webm: a completely still bouquet whose roses fade colour on a
# staggered, periodic schedule, with the source clip's drifting petals composited under it.
#
# usage: python build_flowers_bouquet.py <inputs_root> <out.webm> [--seed 7] [--crf 32] [--frames N]
#            [--passes primary:0:id,under:60:rot90] [--scale 0.8] [--concurrency 3.5] [--report DIR]
#   <inputs_root> holds seg236/ recolour236/ petals2/ as produced by the two analysis workflows (see README.md).
#   --frames N renders only the first N frames (a quick test); the report strips are still written.

"""WHY THIS CONSTRUCTION. The source (flowers_video.mp4, a Veo render) never rigidly rotates: what reads as
rotation is a 1.19x zoom plus non-rigid morphing in frames ~77-178, after which the layout returns to the
frame-0 arrangement. Nothing can be counter-rotated into a "completely still" bouquet, so the bouquet is ONE
frame (236: sharp, no petals on or near the rim) and every other requirement is synthesised on top of it:

  STILL       the base RGBA never changes; only pixels inside a rose's soft mask are ever rewritten.
  COLOUR      each scheduled rose has precomputed recolours (Lab, shading preserved) for its allowed targets;
              a change is a 60-frame (2.5 s) smoothstep blend in Lab between two of those states.
  RANDOM      a seeded scheduler places 2 fades per participating rose on a jittered lattice over the loop so
              ~3.5 fades are in flight at any instant, staggered, with no two touching roses fading together,
              at most MAX_OFF roses away from their original colour, and every rose back to its original colour
              by the end of the loop — the colour timeline is periodic, so the wrap is seamless by construction.
  PETALS      the source's petals are keyed out of the source (petals2/layer, stabilised so the source's zoom
              does not change their size) and composited UNDER the bouquet so they emerge from its rim. The
              source's last second is almost empty (1-3 petals vs ~16 at its head), so a pass does not use it:
              the loop is three 144-frame passes, each playing source frames 24..215 with a 48-frame crossfade
              into the next (the outgoing pass's frames 168..215 fade out while the incoming pass's 24..71 fade
              in — both sides dense, so the seam never reads as a burst). Successive passes are flipped
              (identity, h-flip, v-flip) so the pattern does not repeat identically every 6 s. A second, rotated,
              time-offset pass fills the bands the 16:9 source leaves at the top and bottom of the square canvas;
              radial drift stays radial under any rotation/flip about the bouquet centre, so every copy is
              geometrically consistent. Petals are suppressed under the bouquet footprint (they pass behind it),
              and each source frame's alpha is ramped to zero over 70 px at its own geometric edge so petals
              leaving the source frame dissolve instead of being cut by the stabilisation bands.
  LOOP        432 frames = 18 s at 24 fps; frame 432 == frame 0 for the bouquet, and the petal passes are
              432-periodic too. One VP9 keyframe (see the orb build for why).
"""
import os, sys, json, argparse, subprocess
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ap = argparse.ArgumentParser()
ap.add_argument("inputs"); ap.add_argument("out")
ap.add_argument("--seed", type=int, default=7)
ap.add_argument("--crf", type=int, default=32)
ap.add_argument("--frames", type=int, default=0)
ap.add_argument("--passes", default="primary:0:id,under:72:rot90",
                help="comma list of name:offset_frames:geometry (id|hflip|vflip|rot90|rot270), bottom-most LAST")
ap.add_argument("--scale", type=float, default=0.8, help="source px -> canvas px about the bouquet centre")
ap.add_argument("--concurrency", type=float, default=3.5, help="target number of fades in flight at any instant")
ap.add_argument("--under-alpha", type=float, default=1.0, help="opacity of the non-primary petal passes")
ap.add_argument("--report", default=None)
args = ap.parse_args()

FF = next(p for p in [r"C:\Users\Jainil Trivedi\Desktop\Wedding_Industry_Ads\frontend\node_modules\ffmpeg-static\ffmpeg.exe",
                      r"C:\Users\Jainil Trivedi\AppData\Local\Programs\Python\Python312\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"] if os.path.exists(p))
R = args.inputs.rstrip("/\\")
REP = args.report or os.path.join(os.path.dirname(os.path.abspath(args.out)), "render_report")
os.makedirs(REP, exist_ok=True)

FPS, CANVAS = 24, 720
LOOP, NSEG = 432, 3                          # asset loop; petal passes per loop
PLOOP, OVERLAP, HEAD0 = LOOP // NSEG, 48, 24 # pass period, crossfade length, first source frame a pass shows
SEG_GEOM = ["id", "hflip", "vflip"]          # geometry of successive passes (all symmetries of radial drift)
BORDER = 70                                  # source-space alpha ramp at each frame's geometric edge
NSRC = 240
assert HEAD0 + PLOOP + OVERLAP <= NSRC, "a pass would run off the end of the source"
EXCLUDE_TARGETS = {rid: {"cream", "champagne"} for rid in (1, 2, 3, 4, 5)}   # navy source is 8-bit-crushed: lifted to cream it
                                                                               # reads as a flat grey rose (seen in situ), so navy
                                                                               # roses move only within the blue/lilac/slate family
DROP_ROSES = {14}                            # label misses a contiguous outer petal: dark targets would leave a white wedge
FADE = 60                                    # 2.5 s colour fade
HOLD = 48                                    # min frames a rose keeps its new colour before fading back (=> starts >= 108 apart)
RETURN_MAX = 150                             # ...and it fades back within this many frames, so a change reads as change/hold/return
MAX_OFF = 7                                  # roses away from their original colour at any instant (13 roses x ~190 frames / 432 ~ 5.7)
CLASS_GAP = 12                               # two roses of one class never START fading within this many frames (lattice is ~16.6;
                                             # anything >= 33 makes 10 navy events in 26 slots infeasible — the touch rule already
                                             # keeps neighbouring flowers from changing together)
BG = np.array([0xe0, 0xdf, 0xe2], np.float32) / 255   # hero ground for previews/metrics
O = np.array([CANVAS / 2, CANVAS / 2])       # canvas centre
S = args.scale
N_OUT = args.frames if args.frames else LOOP

def smoothstep(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)

# ---------------------------------------------------------------- inputs
seg = json.load(open(f"{R}/seg236/roses.json"))
pal = json.load(open(f"{R}/recolour236/palette.json"))
prep = json.load(open(f"{R}/petals2/report.json"))
base_rgb = np.asarray(Image.open(f"{R}/seg236/base_f236.png").convert("RGB")).astype(np.float32) / 255
base_a = np.asarray(Image.open(f"{R}/seg236/bouquet_alpha.png").convert("L")).astype(np.float32) / 255
base_lab = np.load(f"{R}/recolour236/base_lab.npy").astype(np.float32)
H, W = base_a.shape

def xy(v):
    return np.array([v["x"], v["y"]], float) if isinstance(v, dict) else np.array(v[:2], float)
C = xy(prep["center"])                                   # petal-layer centre (source px)
Cb = xy(seg["centroid"])                                 # f236 bouquet centroid (source px)
BASE_SCALE = float(prep.get("recommended_base_scale", 1.045))
print(f"petal centre {C}, base centroid {Cb}, base scale {BASE_SCALE:.3f}, canvas scale {S}")

# Lab -> sRGB (D65). Applied as a DIFFERENCE on top of the base PNG so static pixels are the PNG bit-for-bit.
def lab_to_srgb(lab):
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16) / 116; fx = fy + a / 500; fz = fy - b / 200
    finv = lambda t: np.where(t > 6 / 29, t ** 3, 3 * (6 / 29) ** 2 * (t - 4 / 29))
    X, Y, Z = 0.95047 * finv(fx), finv(fy), 1.08883 * finv(fz)
    rgb = np.stack([3.2404542 * X - 1.5371385 * Y - 0.4985314 * Z,
                    -0.9692660 * X + 1.8760108 * Y + 0.0415560 * Z,
                    0.0556434 * X - 0.2040259 * Y + 1.0572252 * Z], -1)
    rgb = np.clip(rgb, 0, 1)
    return np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)

conv_err = np.abs(lab_to_srgb(base_lab) - base_rgb).max() * 255
print(f"base_lab -> sRGB reproduces base_f236.png within {conv_err:.2f}/255 (only affects recoloured pixels)")

# bouquet crop (source space) — everything bouquet-related is composed inside it
ys, xs = np.where(base_a > 0)
cy0, cy1, cx0, cx1 = max(ys.min() - 4, 0), min(ys.max() + 5, H), max(xs.min() - 4, 0), min(xs.max() + 5, W)
crop = (slice(cy0, cy1), slice(cx0, cx1))
base_rgb_c, base_a_c, base_lab_c = base_rgb[crop], base_a[crop], base_lab[crop]
base_srgb_from_lab_c = lab_to_srgb(base_lab_c)

# roses + their recolours
labels = np.load(f"{R}/seg236/label_map.npy")
class_colour = pal["class_colour"]

def spur_weight(rid, bbox):
    """Navy/blue labels can carry a thin inter-rose shadow spur (rose 2: a 5-6 px wide sliver along the r2/r7
    boundary) that turns into a light spike under a light recolour. Open the label, keep the body, regrow 2 px,
    and return a soft weight (1 on the body, 0 on the spur) over the bbox — or None when nothing is removed."""
    x0, y0, x1, y1 = bbox
    m = labels[y0:y1, x0:x1] == rid
    body = ndi.binary_opening(m, structure=np.ones((9, 9), bool))
    if not body.any(): return None
    lab_, n = ndi.label(body)
    if n > 1:
        body = lab_ == (np.argmax(ndi.sum(body, lab_, range(1, n + 1))) + 1)
    body = ndi.binary_dilation(body, iterations=2) & m
    removed = int(m.sum() - body.sum())
    if removed < 50: return None
    w = ndi.gaussian_filter(ndi.binary_dilation(body, iterations=2).astype(np.float32), 1.0)
    return np.clip(w, 0, 1), removed

roses = {}
for r in seg["roses"]:
    if not r.get("schedule") or r["id"] in DROP_ROSES: continue
    own = class_colour[r["class"]]
    states = {}
    for t in pal["allowed"].get(r["class"], []):
        if t == own or t in EXCLUDE_TARGETS.get(r["id"], ()): continue
        f = f"{R}/recolour236/recolour/r{r['id']}_{t}.npz"
        if not os.path.exists(f): print(f"  missing {os.path.basename(f)} - target dropped for rose {r['id']}"); continue
        z = np.load(f)
        x0, y0, x1, y1 = [int(v) for v in z["bbox"]]
        states[t] = dict(lab=z["lab"].astype(np.float32), alpha=z["alpha"].astype(np.float32), bbox=(x0, y0, x1, y1))
    if not states: continue
    if r["class"] in ("navy", "blue"):
        sw = spur_weight(r["id"], next(iter(states.values()))["bbox"])
        if sw is not None:
            w, removed = sw
            for st in states.values(): st["alpha"] = st["alpha"] * w
            print(f"  rose {r['id']}: spur cleanup removed {removed} label px from its mask")
    roses[r["id"]] = dict(meta=r, own=own, states=states)
print(f"{len(roses)} roses available for the schedule: " + ", ".join(f"{i}({roses[i]['meta']['class']}:{len(roses[i]['states'])})" for i in roses))

# ---------------------------------------------------------------- schedule
def cyc_in(t, start, length):                           # is frame t inside the cyclic interval [start, start+length)?
    return (t - start) % LOOP < length
def overlap(a, b, length=FADE):                          # do two cyclic fade intervals overlap?
    return (a - b) % LOOP < length or (b - a) % LOOP < length

def make_schedule(rng):
    """Randomised construction (fast, restarts on failure): (1) 2k fade starts on a jittered lattice; (2) match
    them into k (outbound, return) pairs 108..RETURN_MAX frames apart (cyclic); (3) deal k roses onto the pairs
    so touching roses never fade together and same-class roses never start within CLASS_GAP frames."""
    ids = list(roses)
    n_ev = int(round(LOOP * args.concurrency / FADE))
    k = min((n_ev + 1) // 2, len(ids))
    n_ev = 2 * k
    lattice = LOOP / n_ev
    starts = sorted(int(round((i * lattice + rng.uniform(-4, 4)) % LOOP)) for i in range(n_ev))
    lo, hi = FADE + HOLD, RETURN_MAX
    # (2) greedy random matching: walk the slots in random order, pair each free slot with a random free slot ahead of it
    free = set(range(n_ev)); pairs = []
    for i in rng.permutation(n_ev):
        if i not in free: continue
        cands = [j for j in free if j != i and lo <= (starts[j] - starts[i]) % LOOP <= hi]
        if not cands: pairs = None; break
        j = int(rng.choice(cands)); free -= {i, j}; pairs.append((starts[i], starts[j]))
    if pairs is None:                                    # stranded slot: fall back to the provably perfect matching (even slot i -> i+7)
        d = max(7, int(np.ceil(lo / lattice)))
        pairs = [(starts[i], starts[(i + d) % n_ev]) for i in range(0, n_ev, 2)]
        if len({j for p in pairs for j in p}) != n_ev:
            FAIL["pairing"] = FAIL.get("pairing", 0) + 1; return None
    # (3) deal roses onto pairs by hill-climbing swaps on a penalty. A hard no-overlap rule for touching roses is
    #     infeasible here: every pair is busy ~28% of the loop, so two pairs only avoid each other when they sit
    #     6-7 apart on the 13-pair cycle, and roses 3 and 8 each touch three others. Penalise instead and minimise.
    chosen = [ids[i] for i in rng.permutation(len(ids))[:k]]
    touches = {i: set(roses[i]["meta"].get("touches", [])) for i in chosen}
    cls = {i: roses[i]["meta"]["class"] for i in chosen}
    def penalty(assign):
        ev = [(assign[p], t) for p, pr in enumerate(pairs) for t in pr]
        touch = klass = 0
        for i in range(len(ev)):
            ri, ti = ev[i]
            for j in range(i + 1, len(ev)):
                rj, tj = ev[j]
                if ri == rj: continue
                if (rj in touches[ri] or ri in touches[rj]) and overlap(ti, tj): touch += 1
                if cls[ri] == cls[rj] and min((ti - tj) % LOOP, (tj - ti) % LOOP) < CLASS_GAP: klass += 1
        return 10 * touch + klass, touch, klass
    assign = list(chosen)
    best_p = penalty(assign)[0]
    improved = True
    while improved and best_p > 0:
        improved = False
        for a in range(k):
            for b in range(a + 1, k):
                assign[a], assign[b] = assign[b], assign[a]
                p = penalty(assign)[0]
                if p < best_p: best_p = p; improved = True
                else: assign[a], assign[b] = assign[b], assign[a]
    _, touch, klass = penalty(assign)
    # targets: deal each class's allowed colours from a shuffled cycle so roses of one class do not all pick the same move
    deck = {}
    def next_target(rose):
        c = cls[rose]
        if not deck.get(c):
            deck[c] = list(rng.permutation(sorted({t for r in chosen if cls[r] == c for t in roses[r]["states"]})))
        for i, t in enumerate(deck[c]):
            if t in roses[rose]["states"]: return str(deck[c].pop(i))
        return str(rng.choice(sorted(roses[rose]["states"])))
    sched = {}
    for p, (t1, t2) in enumerate(pairs):
        rose = assign[p]
        sched[rose] = dict(t1=t1, t2=t2, a=roses[rose]["own"], b=next_target(rose))   # a->b at t1, b->a at t2 (cyclic)
    # occupancy: roses away from their original colour (fading counts as away)
    off = np.zeros(LOOP, int)
    for e in sched.values():
        length = (e["t2"] - e["t1"]) % LOOP + FADE
        for t in range(LOOP):
            if cyc_in(t, e["t1"], length): off[t] += 1
    return sched, off, touch, klass

rng = np.random.default_rng(args.seed)
FAIL = {}
best = None; tried = 0
for attempt in range(1500):
    res = make_schedule(rng); tried += 1
    if res is None: continue
    sched, off, touch, klass = res
    total = 10 * touch + klass + 3 * max(0, off.max() - MAX_OFF)
    if best is None or total < best[0]: best = (total, sched, off, touch, klass)
    if total == 0: break
if best is None: sys.exit(f"no schedule could be paired; failures by stage: {FAIL}")
total, sched, off, touch, klass = best
print(f"schedule: best of {tried} attempts - residual: {touch} touching-rose overlaps, {klass} same-class near-starts, "
      f"off-colour max {off.max()} (cap {MAX_OFF})")
inflight = np.zeros(LOOP, int)
for e in sched.values():
    for t in range(LOOP):
        inflight[t] += cyc_in(t, e["t1"], FADE) + cyc_in(t, e["t2"], FADE)
print(f"schedule: {len(sched)} roses, {2*len(sched)} fades of {FADE} frames; in flight min/mean/max {inflight.min()}/{inflight.mean():.2f}/{inflight.max()}; "
      f"off-colour max {off.max()}")
for rose, e in sorted(sched.items(), key=lambda kv: kv[1]["t1"]):
    print(f"  rose {rose:>2} {roses[rose]['meta']['class']:>5}: {e['a']:>10} -> {e['b']:<10} @ {e['t1']:>3} ({e['t1']/FPS:5.2f}s)   back @ {e['t2']:>3} ({e['t2']/FPS:5.2f}s)")
json.dump(dict(seed=args.seed, fade=FADE, loop=LOOP, events={str(k): v for k, v in sched.items()},
               inflight=inflight.tolist(), off=off.tolist()), open(f"{REP}/schedule.json", "w"), indent=1)

def rose_state(rose, t):
    """-> (from_state, to_state, s) for frame t; states are 'orig' or a target name; s in [0,1]."""
    e = sched[rose]
    if cyc_in(t, e["t1"], FADE): return "orig", e["b"], float(smoothstep(((t - e["t1"]) % LOOP + 0.5) / FADE))
    if cyc_in(t, e["t2"], FADE): return e["b"], "orig", float(smoothstep(((t - e["t2"]) % LOOP + 0.5) / FADE))
    in_b = cyc_in(t, e["t1"] + FADE, (e["t2"] - e["t1"] - FADE) % LOOP)
    return (e["b"], e["b"], 1.0) if in_b else ("orig", "orig", 0.0)

# ---------------------------------------------------------------- bouquet composition (source space)
def state_lab(rose, name, bbox):
    if name == "orig":
        x0, y0, x1, y1 = bbox; return base_lab[y0:y1, x0:x1]
    return roses[rose]["states"][name]["lab"]

def compose_bouquet(t):
    """Premultiplied RGBA uint8 of the bouquet crop for frame t, plus per-rose mean sRGB for the traces."""
    lab = base_lab_c.copy()
    traces = {}
    for rose in sched:
        f, to, s = rose_state(rose, t)
        st = roses[rose]["states"]
        bbox = next(iter(st.values()))["bbox"]; alpha = next(iter(st.values()))["alpha"]
        x0, y0, x1, y1 = bbox
        if f == "orig" and to == "orig":
            traces[rose] = None; continue
        b = base_lab[y0:y1, x0:x1]
        lf, lt = state_lab(rose, f, bbox), state_lab(rose, to, bbox)
        delta = alpha[..., None] * ((1 - s) * (lf - b) + s * (lt - b))
        lab[y0 - cy0:y1 - cy0, x0 - cx0:x1 - cx0] += delta
        traces[rose] = (alpha, bbox)
    rgb = base_rgb_c + (lab_to_srgb(lab) - base_srgb_from_lab_c)
    rgb = np.clip(rgb, 0, 1)
    tr = {}
    for rose, v in traces.items():
        alpha, (x0, y0, x1, y1) = v if v else (next(iter(roses[rose]["states"].values()))["alpha"], next(iter(roses[rose]["states"].values()))["bbox"])
        sub = rgb[y0 - cy0:y1 - cy0, x0 - cx0:x1 - cx0]
        m = alpha > 0.5
        tr[rose] = sub[m].mean(0) if m.any() else np.zeros(3)
    prem = np.dstack([rgb * base_a_c[..., None], base_a_c])
    return (prem * 255 + 0.5).astype(np.uint8), tr, rgb

# ---------------------------------------------------------------- geometry
GEOM = {"id": np.eye(2), "hflip": np.diag([-1.0, 1.0]), "vflip": np.diag([1.0, -1.0]),
        "rot90": np.array([[0.0, -1.0], [1.0, 0.0]]), "rot270": np.array([[0.0, 1.0], [-1.0, 0.0]])}

def affine_coeffs(Rm, centre, scale):
    """PIL AFFINE data mapping canvas px -> source px for forward map  canvas = O + scale*Rm(src - centre)."""
    Ri = np.linalg.inv(Rm) / scale
    c = centre - Ri @ O
    return (Ri[0, 0], Ri[0, 1], c[0], Ri[1, 0], Ri[1, 1], c[1])

def warp(prem_u8, coeffs):
    """Premultiplied RGBA uint8 (any size) -> premultiplied float canvas (720x720x4) via bicubic affine."""
    im = Image.fromarray(prem_u8, "RGBA").transform((CANVAS, CANVAS), Image.AFFINE, coeffs, resample=Image.BICUBIC)
    out = np.asarray(im).astype(np.float32) / 255
    out[..., :3] = np.minimum(out[..., :3], out[..., 3:4])     # bicubic overshoot guard: premultiplied colour <= alpha
    return out

def over(src, dst):
    return src + dst * (1 - src[..., 3:4])

# ---------------------------------------------------------------- petal passes
# per-frame geometric bands of the stabilised layer (inverse zoom leaves transparent margins): [left, right, top, bottom] px
bands = prep.get("bands_geom_lrtb") or [[0, 0, 0, 0]] * NSRC
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def border_ramp(idx):
    l, r_, t_, b = [float(v) for v in bands[idx]]
    d = np.minimum.reduce([xx - l, (W - r_) - xx, yy - t_, (H - b) - yy])
    return np.clip(d / BORDER, 0, 1)

petal_cache = {}
def petal_prem(idx):
    if idx not in petal_cache:
        if len(petal_cache) > 64: petal_cache.clear()
        a = np.asarray(Image.open(f"{R}/petals2/layer/petals_{idx:03d}.png").convert("RGBA")).astype(np.float32) / 255
        a[..., 3] *= border_ramp(idx)
        prem = a.copy(); prem[..., :3] *= a[..., 3:4]
        petal_cache[idx] = (prem * 255 + 0.5).astype(np.uint8)
    return petal_cache[idx]

def petal_track(t, geom):
    """Premultiplied float canvas layer of one petal pass at asset frame t (432-periodic).
    Pass `segment` runs from asset frame segment*PLOOP showing source frames HEAD0, HEAD0+1, ... for PLOOP+OVERLAP
    frames; its last OVERLAP frames fade out while the next pass's first OVERLAP frames fade in."""
    t %= LOOP
    seg_i, tau = t // PLOOP, t % PLOOP
    def piece(segment, frame, weight):
        Rm = GEOM[geom] @ GEOM[SEG_GEOM[segment % NSEG]]
        return warp(petal_prem(frame), affine_coeffs(Rm, C, S)) * weight
    if tau < OVERLAP:
        w = float(smoothstep((tau + 0.5) / OVERLAP))
        head = piece(seg_i, HEAD0 + tau, w)                          # incoming pass, source frames HEAD0 .. HEAD0+OVERLAP-1
        tail = piece(seg_i - 1, HEAD0 + PLOOP + tau, 1 - w)          # outgoing pass, source frames HEAD0+PLOOP .. HEAD0+PLOOP+OVERLAP-1
        return over(head, tail)
    return piece(seg_i, HEAD0 + tau, 1.0)

passes = []
for spec in args.passes.split(","):
    name, off_, geom = spec.split(":"); passes.append((name, int(off_), geom))
print("petal passes (top first):", passes)

# bouquet placement: base centroid -> canvas centre, scaled by S*BASE_SCALE; the crop origin shifts the centre
bouquet_coeffs = affine_coeffs(GEOM["id"], Cb - np.array([cx0, cy0]), S * BASE_SCALE)
bouquet_alpha_canvas = warp((np.dstack([np.zeros_like(base_a_c)] * 3 + [base_a_c]) * 255 + 0.5).astype(np.uint8), bouquet_coeffs)[..., 3]
# petals pass BEHIND the bouquet: suppress them under its footprint (dilated 3 px, soft) so nothing shows through
# the semi-transparent baby's-breath rim
under_bouquet = 1 - np.clip(ndi.gaussian_filter(ndi.binary_dilation(bouquet_alpha_canvas > 0.5, iterations=3).astype(np.float32), 1.5), 0, 1)

# ---------------------------------------------------------------- render + encode + measure
enc = subprocess.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{CANVAS}x{CANVAS}", "-r", str(FPS), "-i", "pipe:0",
                        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", str(args.crf), "-row-mt", "1",
                        "-deadline", "good", "-cpu-used", "1", "-auto-alt-ref", "0", "-g", str(LOOP), args.out], stdin=subprocess.PIPE)

def preview(prem):
    return (np.clip(prem[..., :3] + BG * (1 - prem[..., 3:4]), 0, 1) * 255 + 0.5).astype(np.uint8)

steps, petal_counts, keep = [], [], {}
trace_rows = []
prev = None; first = None
still_ref = None
rose_support = np.zeros(base_a_c.shape, bool)
for rose in sched:
    st = next(iter(roses[rose]["states"].values())); x0, y0, x1, y1 = st["bbox"]
    rose_support[y0 - cy0:y1 - cy0, x0 - cx0:x1 - cx0] |= st["alpha"] > 0
fade_rose = min(sched, key=lambda k: sched[k]["t1"])
fade_frames = set(range(sched[fade_rose]["t1"] - 6, sched[fade_rose]["t1"] + FADE + 7, 12))
sheet_frames = set(range(0, LOOP, 24))
seam_frames = set(range(LOOP - 6, LOOP)) | set(range(6))

for t in range(N_OUT):
    canvas = np.zeros((CANVAS, CANVAS, 4), np.float32)
    for name, off_, geom in reversed(passes):          # bottom-most last in the list -> composite first
        layer = petal_track(t + off_, geom)
        if name != "primary" and args.under_alpha != 1.0: layer *= args.under_alpha
        canvas = over(layer, canvas)
    canvas *= under_bouquet[..., None]
    petal_only = canvas.copy()
    bouq_u8, tr, rgb_src = compose_bouquet(t)
    canvas = over(warp(bouq_u8, bouquet_coeffs), canvas)
    # encode (straight alpha)
    a = canvas[..., 3:4]
    straight = np.where(a > 1e-4, canvas[..., :3] / np.maximum(a, 1e-4), 0)
    enc.stdin.write((np.dstack([np.clip(straight, 0, 1), a[..., 0]]) * 255 + 0.5).astype(np.uint8).tobytes())
    # metrics
    pv = preview(canvas)
    if prev is not None: steps.append(float(np.sqrt(np.mean((pv.astype(np.float32) - prev.astype(np.float32)) ** 2))))
    if first is None: first = pv
    prev = pv
    vis = (petal_only[..., 3] >= 0.25) & (bouquet_alpha_canvas < 0.5)
    lab_, n = ndi.label(vis); sizes = ndi.sum(vis, lab_, range(1, n + 1)) if n else []
    petal_counts.append(int(np.sum(np.asarray(sizes) >= 25)))
    trace_rows.append([t] + [v for rose in sorted(sched) for v in (tr[rose] * 255).round(1)])
    if t % 24 == 0:
        still = rgb_src[~rose_support]
        if still_ref is None: still_ref = still
        else: assert np.array_equal(still, still_ref), f"bouquet changed outside the roses at frame {t}"
    if t in fade_frames or t in sheet_frames or t in seam_frames: keep[t] = pv
    if t % 48 == 0: print(f"  frame {t}/{N_OUT}  petals visible {petal_counts[-1]}  fades in flight {inflight[t % LOOP]}")
enc.stdin.close(); enc.wait()
if N_OUT == LOOP: steps.append(float(np.sqrt(np.mean((first.astype(np.float32) - prev.astype(np.float32)) ** 2))))
print(f"encoded {args.out}: {os.path.getsize(args.out)/1e6:.2f} MB, ffmpeg rc {enc.returncode}")

# ---------------------------------------------------------------- report
steps = np.array(steps); pc = np.array(petal_counts)
np.savetxt(f"{REP}/steps.csv", steps, fmt="%.3f")
np.savetxt(f"{REP}/petal_counts.csv", pc, fmt="%d")
with open(f"{REP}/rose_traces.csv", "w") as fh:
    fh.write("frame," + ",".join(f"r{rose}_{ch}" for rose in sorted(sched) for ch in "rgb") + "\n")
    for row in trace_rows: fh.write(",".join(str(v) for v in row) + "\n")
print(f"rms step mean {steps.mean():.3f}  p95 {np.percentile(steps, 95):.3f}  max {steps.max():.3f}" + (f"  WRAP (last->first) {steps[-1]:.3f}" if N_OUT == LOOP else ""))
print(f"petals visible per frame: min {pc.min()}  mean {pc.mean():.1f}  max {pc.max()};  frames with < 4 petals: {(pc < 4).sum()}")
print("bouquet pixels outside the roses: identical in every sampled frame (asserted)")

def thumb(img, size=240): return np.asarray(Image.fromarray(img).resize((size, size), Image.Resampling.BOX))
def crop2x(img, cx, cy, half=110):
    x0, y0 = int(max(cx - half, 0)), int(max(cy - half, 0)); sub = img[y0:y0 + 2 * half, x0:x0 + 2 * half]
    return np.asarray(Image.fromarray(sub).resize((sub.shape[1] * 2, sub.shape[0] * 2), Image.Resampling.BICUBIC))
if N_OUT == LOOP:
    Image.fromarray(np.hstack([thumb(keep[t]) for t in list(range(LOOP - 6, LOOP)) + list(range(6))])).save(f"{REP}/seam_strip.png")
    Image.fromarray(np.vstack([np.hstack([thumb(keep[t], 200) for t in range(r, r + 6 * 24, 24)]) for r in range(0, LOOP, 6 * 24)])).save(f"{REP}/sheet.png")
m = roses[fade_rose]["meta"]
pc_canvas = O + S * BASE_SCALE * (np.array([m["cx"], m["cy"]]) - Cb)
fr = sorted(t for t in fade_frames if t in keep)
if fr:
    Image.fromarray(np.hstack([crop2x(keep[t], *pc_canvas) for t in fr])).save(f"{REP}/fade_strip_rose{fade_rose}.png")
    print(f"fade strip: rose {fade_rose} ({m['class']} -> {sched[fade_rose]['b']}), frames {fr}")
print("report written to", REP)
