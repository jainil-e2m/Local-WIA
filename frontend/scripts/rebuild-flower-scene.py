"""Key the yellow-screen bouquet at 2..10 seconds without recoloring its core.

Usage: python scripts/rebuild-flower-scene.py SOURCE.mp4 [--preview]
Local processing dependencies: numpy, scipy, Pillow.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / '.video-deps'))
import numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw

FF = ROOT.parent / 'frontend' / 'node_modules' / 'ffmpeg-static' / 'ffmpeg.exe'
OUT = ROOT / 'public' / 'variant-1'
W, H, FPS = 720, 1280, 24

def smooth(lo, hi, value):
    t = np.clip((value - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)

def matte(rgb):
    f = rgb.astype(np.float32)
    # Per-frame background color: only the clean top/right border, away from
    # flowers and foliage. Brightness-normalized distance also removes shadows.
    samples = np.concatenate((f[:45].reshape(-1, 3), f[:900, -35:].reshape(-1, 3)))
    yellow = (samples[:, 0] - samples[:, 1] > 22) & (samples[:, 1] - samples[:, 2] > 45)
    bg = np.median(samples[yellow], axis=0)
    shade = np.sum(f * bg, axis=2) / np.sum(bg * bg)
    residual = np.linalg.norm(f - shade[..., None] * bg, axis=2)
    # Compare chromaticity at the backdrop's brightness: dark olive leaves
    # must not be mistaken for a darker version of the yellow screen.
    residual /= np.maximum(shade, .15)
    alpha = smooth(7, 19, residual)
    # The screen is bright. Deep bouquet shadows are foreground, even where
    # their olive hue approaches yellow; keep their original colors opaque.
    alpha[f.max(axis=2) < 145] = 1

    # Keep small enclosed flower centers opaque; don't globally remove yellows.
    opaque = alpha > .98
    holes = ndi.binary_fill_holes(opaque) & ~opaque
    labels, count = ndi.label(holes)
    sizes = np.bincount(labels.ravel())
    tiny = (sizes < 1400)
    tiny[0] = False
    _, near_core = ndi.distance_transform_edt(~opaque, return_indices=True)
    neighbors = f[near_core[0], near_core[1]]
    white_neighbor = (neighbors[..., 2] > neighbors[..., 0] * .68) & (neighbors[..., 0] > 160)
    petal_fraction = ndi.mean(white_neighbor, labels, np.arange(len(sizes)))
    tiny &= np.nan_to_num(petal_fraction) > .72
    alpha[tiny[labels]] = 1

    # Isolate the vase from the tabletop, preserving green foliage outside it.
    vase = Image.new('L', (W, H))
    ImageDraw.Draw(vase).polygon([(161,990),(434,990),(438,1155),(425,1195),
                                (395,1212),(204,1212),(169,1190),(160,1150)], fill=255)
    region = np.asarray(vase, dtype=np.float32) / 255
    region[:1070] = 1
    foliage = (f[..., 1] > f[..., 0] + 2) & (f[..., 1] > f[..., 2] + 12)
    region = np.maximum(region, foliage.astype(np.float32))
    region = ndi.gaussian_filter(region, .65)
    alpha *= region

    # Recover edge colors against the yellow plate. Opaque flower/leaf pixels
    # remain byte-for-byte unchanged; correction affects only mixed edge pixels.
    core = alpha > .98
    _, indices = ndi.distance_transform_edt(~core, return_indices=True)
    near = f[indices[0], indices[1]]
    background = shade[..., None] * bg
    direction = near - background
    den = np.sum(direction * direction, axis=2)
    solved = np.clip(np.sum((f - background) * direction, axis=2) / np.maximum(den, 1), 0, 1)
    edge = (alpha > 0) & (alpha < .98) & (region > .99)
    alpha[edge] = solved[edge]
    corrected = np.clip((f - (1-alpha[..., None]) * background) / np.maximum(alpha[..., None], .05), 0, 255)
    colors = np.where(edge[..., None], corrected, f).astype(np.uint8)
    # Pad invisible color pixels with neighboring foreground to avoid codec halos.
    colors[alpha < .01] = near.astype(np.uint8)[alpha < .01]
    return np.dstack((colors, np.round(alpha * 255).astype(np.uint8)))

def preview(rgba, name):
    im = Image.fromarray(rgba)
    im.save(OUT / 'flower-scene-poster-v2.webp', lossless=True)
    yy, xx = np.indices((H, W))
    grid = np.where(((xx//32 + yy//32) % 2)[..., None], 215, 245).astype(np.uint8)
    grid = np.repeat(grid, 3, axis=2)
    panels = []
    for bg in (grid, np.full((H,W,3), 255, np.uint8), np.full((H,W,3), (13,26,51), np.uint8)):
        base = Image.fromarray(bg).convert('RGBA')
        base.alpha_composite(im)
        panels.append(base.convert('RGB').resize((360,640)))
    sheet = Image.new('RGB', (1080,640))
    for i, panel in enumerate(panels): sheet.paste(panel, (i*360,0))
    sheet.save(ROOT / name)

def main():
    source = sys.argv[1]
    only_preview = '--preview' in sys.argv
    dec = subprocess.Popen([str(FF), '-v','error','-ss','2','-i',source,'-t','8',
                            '-an','-vf','fps=24','-f','rawvideo','-pix_fmt','rgb24','pipe:1'], stdout=subprocess.PIPE)
    enc = None
    if not only_preview:
        enc = subprocess.Popen([str(FF),'-v','error','-y','-f','rawvideo','-pix_fmt','rgba',
            '-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-an','-c:v','libvpx-vp9',
            '-pix_fmt','yuva420p','-auto-alt-ref','0','-crf','24','-b:v','0',
            '-deadline','good','-cpu-used','4','-row-mt','1', str(OUT/'flower-scene-alpha-v2.webm')], stdin=subprocess.PIPE)
    count = 0
    while True:
        raw = dec.stdout.read(W*H*3)
        if not raw: break
        if len(raw) != W*H*3: raise RuntimeError('Incomplete frame')
        rgba = matte(np.frombuffer(raw,np.uint8).reshape(H,W,3))
        if count == 0: preview(rgba, 'bouquet-alpha-review.jpg')
        if only_preview:
            dec.terminate()
            break
        enc.stdin.write(rgba.tobytes())
        count += 1
        if count % 24 == 0: print(f'{count}/192 frames', flush=True)
    if enc:
        enc.stdin.close()
        if enc.wait() != 0 or dec.wait() != 0: raise RuntimeError('Encoding failed')
        if count != 192: raise RuntimeError(f'Expected 192 frames, got {count}')
        print('Created 8 seconds of transparent VP9 video.', flush=True)

if __name__ == '__main__': main()
