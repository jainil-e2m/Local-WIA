# flowers-bouquet — hero asset pipeline

Builds `frontend/public/flowers-bouquet.webm` (720×720, VP9 with alpha, 24 fps, 18 s seamless loop) from
`frontend/public/flowers_video.mp4` (a 10 s Veo render of a top-down bridal bouquet with petals drifting off it).

## The brief and what it forced

The bouquet must not move at all; only the flowers change colour, "randomly", each change a clearly visible 2–3 s
fade, 3–4 flowers changing at any time, staggered; the petals-leaving effect is kept; nothing else changes.

Analysis of the source showed it never rigidly rotates (±3° at most): what reads as rotation is a 1.19× zoom plus
non-rigid Veo morphing in frames ~77–178, after which the layout returns to the frame-0 arrangement. Nothing can be
counter-rotated into a still bouquet, so the asset is a **composite**:

| layer | where it comes from |
|---|---|
| static bouquet | source frame 236 (sharp, no petals on or near the rim), soft alpha, cast shadow removed |
| colour fades | per-rose recolours precomputed in Lab with the rose's own shading preserved; a change is a 60-frame smoothstep blend between two states; a seeded scheduler places 2 fades per participating rose (13 roses, 26 fades) so ~3.5 are in flight at any instant, touching roses avoid fading together, and every rose is back to its original colour by the end of the loop |
| petals | keyed out of the source against a temporal-median background plate, inverse-zoom stabilised so their size does not change, composited *under* the bouquet so they emerge from its rim; three 6 s passes of the dense source range (frames 24–215) with 2 s crossfades, flipped per pass, plus a rotated time-offset pass to fill the bands the 16:9 source leaves on a square canvas |

The colour timeline is periodic on 432 frames and the petal passes are too, so the loop wraps with no seam. One VP9
keyframe (see `../liquid-sphere/build_liquid_sphere_pingpong.py` for why I-frame boundaries matter on still content).

## Rebuild

```
python build_flowers_bouquet.py inputs out.webm            # full 432-frame render + report strips next to out.webm
python build_flowers_bouquet.py inputs out.webm --frames 48 # quick smoke test
```

Knobs: `--seed` (schedule), `--crf` (32), `--scale` (0.8 source px → canvas px), `--concurrency` (3.5 fades in
flight), `--passes` (petal passes as `name:offset:geometry`). Constants at the top of the script: fade length,
hold/return window, per-rose target exclusions (navy roses never lift to cream/champagne — the 8-bit-crushed navy
source turns flat grey when lifted), dropped roses (14: its label misses an outer petal).

The report folder gets `schedule.json`, `steps.csv` (frame-to-frame RMS incl. the wrap step), `rose_traces.csv`
(mean colour of every scheduled rose per frame), `petal_counts.csv`, `seam_strip.png`, `sheet.png`, and a fade strip.

## inputs/ (produced by two agent workflows, archived here so the build is reproducible)

- `seg236/` — `base_f236.png` (frame 236), `bouquet_alpha.png` (soft alpha; no shadow, no Veo leaf halo, rim
  baby's breath kept), `label_map.npy` (int32, one id per rose), `roses.json` (class, centroid, bbox, touching
  neighbours, `schedule` flag), `overlay.png`; scripts `decode236.py`, `alpha236.py`, `segment236.py`.
- `recolour236/` — `palette.json` (7 colours measured/curated: midnight navy, cornflower, ivory cream, periwinkle
  `#8da1fd`, dusty lilac, champagne, slate blue; allowed transitions per class), `base_lab.npy`,
  `recolour/r{ID}_{target}.npz` (`lab`, shared soft `alpha`, exclusive-end `bbox`), `fidelity.json`,
  `full_frame_demo.png`; script `recolour236.py` (Lab pipeline, V-based shading with rank matching onto the
  target class's shading distribution, anchored dark/base/light ramps, HF re-injection, outward-only feather).
- `petals2/` — `layer/petals_%03d.png` (240 stabilised RGBA frames, straight alpha, tight bouquet exclusion +
  rim colour gate, no cast shadows), `report.json` (centre, footprint radii, recommended base scale, per-frame
  geometric bands, petal counts, seam analysis); script `key2.py` (+ `metrics.py`, `strips.py`). It consumes
  `petals_stage1/` (plate, per-frame bouquet transform/masks, and the first-pass keying/stabilisation scripts;
  the 663 MB `frames.npy` decode cache is not archived — `decode.py` regenerates it).
- `analysis_pass1/` — the first analysis pass (motion/still-frame search, f6 segmentation and recolour
  prototypes) kept for reference.

Python 3.12 with numpy, scipy, Pillow; ffmpeg from `frontend/node_modules/ffmpeg-static` (no OpenCV needed).
