# Builds frontend/public/liquid-sphere.webm as a seamless PALINDROME (ping-pong) loop.
# usage: python build_liquid_sphere_pingpong.py <scratch_dir> <out.webm> [head=1] [tail=236] [ease=8] [crf=36]
#        DRY=1 python build_liquid_sphere_pingpong.py ...   -> print the frame schedule only, encode nothing
# Supersedes find_loop_point.py + build_liquid_sphere.py (kept for reference).

"""WHY A PALINDROME. The source clip is a liquid morph whose topology changes
throughout: it is not periodic, so no cut point exists where the thin tendrils
truly align, and any crossfade between "similar silhouette, different detail"
frames shows ~0.5s of doubled edges (that was the previous build: a 16-frame
blend centred on a 30->232 cut). Playing forward then backward makes the first
and last frames true neighbours by construction, so there is nothing to blend.
The only trade-off is that the motion reverses, which for a liquid reads as
breathing rather than as a wrap.

TURNAROUNDS. A hard reversal is a velocity flip, visible as a bounce when the
motion is fast. The source's own head is already a standstill (the generator
eased in from a still pose: adjacent-frame steps 0.00, 0.01, 0.02 ... 0.25 over
its first 12 frames against a clip mean of 1.73), so that end needs nothing and
is where the file wraps: any browser `loop` hitch lands on a motionless orb.
The tail is still moving (~30% of mean speed), so its last EASE source frames
are time-stretched over ~pi/2*EASE output frames with a cosine velocity ramp to
zero (a pendulum at the end of its swing: constant acceleration through the
turnaround, so no dwell and no bounce), using ffmpeg's motion-compensated
interpolation (minterpolate) for the sub-frame positions. Integer positions
always use the original frames.

ONE KEYFRAME. An I-frame's quantisation pattern differs from the P-frames
around it. Under motion that is invisible (measured: the step into a keyframe
is no larger than its neighbours), but where the orb is still it is the whole
frame step, and both turnarounds are still. So the GOP is the entire loop: the
only I/P boundary left is the wrap itself, and crf 36 keeps that residual
(same-content frames differ by ~3.5 rms) well below any motion step.

MINTERPOLATE LOOKAHEAD. It emits nothing past the second-to-last input frame
(12 inputs at 24fps -> 101 frames at 240fps, i.e. up to input 10.0), so TAIL
must sit at least two frames before the clip's last frame (239) and the trimmed
feed runs to the clip end. TAIL=236 leaves a frame of slack.
"""
import os, sys, subprocess, numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CANDS = [r"C:\Users\Jainil Trivedi\AppData\Local\Programs\Python\Python312\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe",
         os.path.join(HERE, "..", "..", "frontend", "node_modules", "ffmpeg-static", "ffmpeg.exe")]
FF  = next(p for p in CANDS if os.path.exists(p))
SRC = r"C:\Users\Jainil Trivedi\Downloads\give_the_slurs_outside_the_cen.mp4"
SP, OUT = sys.argv[1], sys.argv[2]
HEAD = int(sys.argv[3]) if len(sys.argv) > 3 else 1      # first source frame used; frames 0 and 1 are identical
TAIL = int(sys.argv[4]) if len(sys.argv) > 4 else 236    # last source frame used; see MINTERPOLATE LOOKAHEAD
EASE = int(sys.argv[5]) if len(sys.argv) > 5 else 8      # source frames stretched into the tail turnaround
CRF  = int(sys.argv[6]) if len(sys.argv) > 6 else 36
X0, Y0, X1, Y1 = 272, 0, 992, 720                        # crop: square around the orb, watermark off
W, H, FPS, NSRC = 1280, 720, 24, 240
Q = 10                                                   # sub-frame grid: minterpolate runs at FPS*Q
MARGIN = 4                                               # lead-in frames so minterpolate's window is full at the ease start
assert TAIL <= NSRC - 3, "minterpolate cannot produce the last interval; leave >= 2 frames after TAIL"
LO, HI = 10.0, 30.0
SPARK = (slice(540, 660), slice(1100, 1220))
BG = np.array([0xe0, 0xdf, 0xe2], np.float32)            # hero ground, for strips + step metric

# ---------------------------------------------------------------- schedule
M = round(EASE * np.pi / 2)                                 # cosine ramp averages 2/pi, so this many steps cover EASE frames
vel = np.cos(np.pi / 2 * (np.arange(M) + 0.5) / M)
vel *= EASE / vel.sum()                                     # exact landing on TAIL; leaves the ramp's first step within ~3% of 1
fwd = [float(n) for n in range(HEAD, TAIL - EASE + 1)]
p = float(TAIL - EASE)
for v in vel:
    p += v
    fwd.append(round(p * Q) / Q)
fwd[-1] = float(TAIL)                                       # guard float drift
back = fwd[1:-1][::-1]                                      # mirror without repeating either turnaround frame
seq = fwd + back
pid = lambda pos: int(round(pos * Q))                       # dict key on the sub-frame grid
need = sorted(set(pid(x) for x in seq))
frac = [k for k in need if k % Q]
print(f"schedule: forward {len(fwd)} frames (source {HEAD}..{TAIL}, last {EASE} stretched over {M}), "
      f"back {len(back)}, total {len(seq)} = {len(seq)/FPS:.2f}s; {len(frac)} interpolated positions")
print("tail ease positions:", " ".join(f"{x:.1f}" for x in fwd[-M-1:]))
print("wrap: ...", " ".join(f"{x:.0f}" for x in seq[-3:]), "|", " ".join(f"{x:.0f}" for x in seq[:3]), "...")
if os.environ.get("DRY"): sys.exit(0)

# ---------------------------------------------------------------- decode + key
def raw_frames(vf=None):
    args = [FF, "-v", "error", "-i", SRC, "-an"] + (["-vf", vf] if vf else []) + ["-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    p = subprocess.Popen(args, stdout=subprocess.PIPE, bufsize=10**8)
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
    """Chroma-key the yellow plate (sampled from the corners), unmix the edge colour, kill spill, crop."""
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
    semi = (a > 0.02) & (a < 0.98)
    y = np.minimum(fg[..., 0], fg[..., 1]) - fg[..., 2]
    y = np.where(semi & (y > 0), y, 0)
    fg[..., 0] -= 0.6 * y; fg[..., 1] -= 0.6 * y
    fg = np.clip(fg, 0, 255)[Y0:Y1, X0:X1]; a = a[Y0:Y1, X0:X1]
    return np.dstack([fg.astype(np.uint8), (a * 255).astype(np.uint8)])   # straight-alpha RGBA

frames = {}
for n, fr in enumerate(raw_frames()):
    if HEAD <= n <= TAIL:
        frames[n * Q] = key(fr)
print(f"keyed {len(frames)} original frames")

A = TAIL - EASE - MARGIN
vf = (f"trim=start_frame={A}:end_frame={NSRC},setpts=PTS-STARTPTS,"
      f"minterpolate=fps={FPS*Q}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none")
want = set(frac); got = 0
for i, fr in enumerate(raw_frames(vf)):
    k = A * Q + i
    if k in want and k not in frames:
        frames[k] = key(fr); got += 1
missing = [k for k in frac if k not in frames]
print(f"interpolated {got} sub-frame positions; missing {len(missing)}")
for k in missing:   # should not happen (see MINTERPOLATE LOOKAHEAD); fall back to the nearest so the build completes, loudly
    near = min(frames, key=lambda j: abs(j - k))
    print(f"  WARNING position {k/Q:.1f} missing, using {near/Q:.1f}")
    frames[k] = frames[near]

# ---------------------------------------------------------------- encode
h, w = frames[HEAD * Q].shape[:2]
enc = subprocess.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "pipe:0",
                        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", str(CRF), "-row-mt", "1",
                        "-deadline", "good", "-cpu-used", "1", "-auto-alt-ref", "0", "-g", str(len(seq)), OUT], stdin=subprocess.PIPE)
for pos in seq:
    enc.stdin.write(frames[pid(pos)].tobytes())
enc.stdin.close(); enc.wait()
print(f"encoded {OUT}: {os.path.getsize(OUT)/1e6:.2f} MB, ffmpeg rc {enc.returncode}")

# ---------------------------------------------------------------- verify
def comp(rgba):
    a = rgba[..., 3:4].astype(np.float32) / 255.0
    return rgba[..., :3].astype(np.float32) * a + BG * (1 - a)
def rms(x, y): return float(np.sqrt(np.mean((x - y) ** 2)))
def thumb(rgba): return np.asarray(Image.fromarray(comp(rgba).astype(np.uint8)).resize((200, 200), Image.Resampling.BOX))

steps = []
prev = comp(frames[pid(seq[0])])
for pos in seq[1:] + seq[:1]:                              # last entry = the wrap step (last frame -> first frame)
    cur = comp(frames[pid(pos)]); steps.append(rms(prev, cur)); prev = cur
steps = np.array(steps)
T = len(fwd) - 1                                           # index of the tail turnaround frame in seq
with open(f"{SP}/pp_steps.txt", "w") as fh:
    fh.write("\n".join(f"{i}\t{s:.3f}" for i, s in enumerate(steps)))
print(f"\nrms step  mean {steps.mean():.3f}  max {steps.max():.3f} at {steps.argmax()}")
print(f"wrap step (last->first): {steps[-1]:.3f}   first steps: " + " ".join(f"{s:.2f}" for s in steps[:6]))
print(f"tail turnaround, steps {T-M}..{T+M}: " + " ".join(f"{s:.2f}" for s in steps[T-M:T+M]))

strip = np.hstack([thumb(frames[pid(seq[i])]) for i in range(T-8, T+9)])
Image.fromarray(strip).save(f"{SP}/pp_tail_strip.png")   # 8 before the peak, peak, 8 after
strip = np.hstack([thumb(frames[pid(seq[i])]) for i in list(range(-6, 0)) + list(range(0, 6))])
Image.fromarray(strip).save(f"{SP}/pp_wrap_strip.png")   # last 6 frames | first 6 frames
print("strips written")
