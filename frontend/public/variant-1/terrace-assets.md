# Terrace scene assets

The landing uses the supplied `Modify_scene_and_animate_breeze_20261009114818.mp4`
as `terrace-breeze.mp4`, without changing its footage. The bowl of berries and
coffee are part of this video. The laptop is rendered in code with a hinged lid.
The diary and pen are transparent photographic assets derived from the supplied
product references using the built-in image generation tool.

`terrace-poster.webp` is its first frame. `terrace-extended.webp` was created with
the built-in image generation tool using that first frame as the edit target.
It supplies the missing sky and marble caps, plus a still fallback under the
video. The center remains the supplied moving footage.

Generation prompt: extend the 1920 x 1080 frame above and below to a 1920 x 1500
composition, keeping its horizontal scale, camera, terrace, berries, coffee,
light and marble pattern. Reconstruct the cropped circular boundary with
matching sky/white column above and matching marble below. Add no laptop,
notebook, pen or extra objects. Use a white exterior. The tool returned a
1419 x 1108 raster, converted to WebP for the page.

Scene coordinates use a 748 px circular viewport. The 1920 px video is scaled
by 748 / 1500 and offset so its circle center (984, 540) lands at (374, 374).
The still extension uses the same horizontal field of view, with a short
vertical feather at each video edge.

The laptop is drawn through a real perspective camera solved from the
reference composite (same terrace frame, laptop corners measured and fitted
at ~3px RMS in the 748px circle): perspective 1452px about the frame centre
(362, 374), table plane tilted 77.86 degrees, base centre anchored at
(253.87, 557.58), lid open 112 degrees. The laptop is turned -41.5 degrees
about its base centre (the reference pose) and scaled 0.9575, which is 90% of
its previous on-screen size. Shadows follow the sun (behind and right of the camera, ~60 degrees
high): a contact line, soft occlusion, and base and lid sun shadows
re-projected in code as the lid moves, plus a faint
marble reflection of the near sides.

## Diary and gold pen

- `terrace-stationery-v2.webp`: current diary and adjacent gold pen composition.
- `terrace-diary.webp` and `terrace-gold-pen.webp`: earlier individual assets,
  retained but no longer rendered.

The current 1902 x 827 asset has real alpha transparency and was converted to
WebP at quality 96. It is displayed at its intrinsic aspect ratio with automatic
height, 306px wide (85% of the earlier 360px), scaled about the diary's centre
at (417.6, 661.5) so it keeps its place on the table. The camera perspective, parallel pen alignment and contact shadows are
part of the photograph; no CSS squash, skew or independent pen rotation is
applied. It contains no table or checkerboard background.

Current composition prompt (built-in tool): Preserve the supplied cream diary's
leather grain, gold border, stitch perforations, ivory page block and navy WIA
emblem, and the supplied gold pen's brushed barrel, clip and WIA engraving.
Arrange both at the low tabletop camera angle of the reference scene. Place
the pen beside and parallel to the diary's near-left edge with a narrow,
consistent gap. Use genuine alpha transparency and natural contact shadows;
include no other objects. Preserve real physical proportions and crisp texture.

Refinement prompt (built-in tool): Keep materials and branding, lower the camera
so the near-left edge descends right at 24-27 degrees, and keep the pen parallel
with an 8mm gap. Reduce the pen barrel diameter by 25% without changing its
length. Use physical camera foreshortening, not image compression. Preserve
all corners and the whole pen on a transparent, wide composition.

Diary prompt (built-in tool): Create a single isolated photographic cutout of
the cream WIA leather diary from the supplied product image, positioned in the
table perspective of the supplied terrace reference. Preserve cream leather
grain, gold stitching and ornamental corners, navy WIA within a gold circle.
Low three-quarter overhead view, visible cream pages and gold-edged bottom
cover. All corners visible, genuine transparent background, no pen or table.
Warm natural sunlight from upper left and subtle contact shadow.

Pen prompt (built-in tool): Isolate the supplied gold WIA ballpoint on a real
transparent background. Preserve the brushed champagne gold barrel, navy WIA
engraving, polished clip, cap rings and metal tip. Horizontal with nib at left
and cap at right. Crisp photographic detail, no other objects or background,
minimal contact shadow, for compositing on a sunlit marble desk.

The laptop holds open for 10 seconds initially, closes, rests for 2 seconds,
then springs open and holds for 14 seconds. Clicking it closes and reopens it;
the hero CTA wakes it. Offscreen motion pauses and reduced-motion mode holds
the laptop open and uses a still video frame.
