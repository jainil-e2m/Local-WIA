/**
 * GLSL for the live marble (MarbleVeins.tsx, driven by renderer.ts).
 *
 * GLSL ES 1.00 throughout, so the same sources compile under WebGL1 and WebGL2.
 *
 * UNITS. Everything is computed in "design pixels" (dp): the pixel grid of the
 * offline marble the delivered design was matched against
 * (scripts/build-hero-marble.mjs), where 1 CSS px = 1.915 dp and the stone is
 * anchored to the region's top-right corner. Working in dp keeps every tuned
 * constant from that script meaningful here, and keeps the veins the same size
 * on every screen.
 *
 * TWO STAGES.
 *   Bake — four passes, run once per size. They evaluate the expensive part
 *   (hundreds of noise lookups per pixel: the stone, and each vein's distance
 *   field) into textures. renderer.ts runs them in strips over several frames.
 *   Composite — every frame. Reads those textures and does only the cheap,
 *   time-dependent part: where each vein is in its life.
 *
 * THE LIFE OF A VEIN. Each vein set has a clock. A point's phase is
 *   phi = fract(cycles - along / L + spread * h)
 * `along` is the distance along the vein's run direction, so phi is a wave
 * travelling along every vein: the ink front. Behind the front a vein has just
 * been drawn (sharp, dark, a wet glow at the tip); further back it is sinking
 * into the stone (wider, paler, gone). Ahead of the front there is nothing yet
 * but a faint seep of pigment. `h` is a field that varies ACROSS veins but
 * barely along them, so neighbouring veins are drawn at different moments.
 *
 * Which stretches of vein take part changes every cycle (pick()). A vein
 * therefore draws, lives, fades, and next time round different veins form.
 */

export const VERTEX = /* glsl */ `
attribute vec2 aPos;
void main() {
  gl_Position = vec4(aPos, 0.0, 1.0);
}
`;

const COMMON = /* glsl */ `
precision highp float;

uniform vec2 uRes;      // size of the target being drawn, in its own pixels
uniform vec2 uPxToDp;   // design pixels per target pixel, x and y
uniform float uOriginX; // design-px x of the region's left edge

const float DP_H = 1560.0; // the offline stone's height; uv = dp / DP_H

float sq(float x) { return x * x; }

vec2 dpPos() {
  return vec2(uOriginX + gl_FragCoord.x * uPxToDp.x, (uRes.y - gl_FragCoord.y) * uPxToDp.y);
}

/* Hash without sine (D. Hoskins): stable across GPUs, no precision cliff. */
vec2 hash22(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.xx + p3.yz) * p3.zy);
}

float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}

/* Perlin-style gradient noise with unit gradients, ~[-1, 1] like the script's. */
float gnoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = p - i;
  vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  vec2 g00 = normalize(hash22(i) * 2.0 - 0.99999);
  vec2 g10 = normalize(hash22(i + vec2(1.0, 0.0)) * 2.0 - 0.99999);
  vec2 g01 = normalize(hash22(i + vec2(0.0, 1.0)) * 2.0 - 0.99999);
  vec2 g11 = normalize(hash22(i + vec2(1.0, 1.0)) * 2.0 - 0.99999);
  float n00 = dot(g00, f);
  float n10 = dot(g10, f - vec2(1.0, 0.0));
  float n01 = dot(g01, f - vec2(0.0, 1.0));
  float n11 = dot(g11, f - vec2(1.0, 1.0));
  return mix(mix(n00, n10, u.x), mix(n01, n11, u.x), u.y) * 1.41;
}

float fbm(vec2 p, int octaves, float gain) {
  float sum = 0.0;
  float amp = 1.0;
  float norm = 0.0;
  for (int i = 0; i < 6; i++) {
    if (i >= octaves) break;
    sum += amp * gnoise(p);
    norm += amp;
    amp *= gain;
    p = p * 2.03 + vec2(1.7, 9.2);
  }
  return sum / norm;
}

/* One offset per independent noise "instance" (the script's seeds). */
vec2 seed(float k) { return vec2(k * 2.17, k * 1.31); }

/**
 * The smooth layout of a vein set: anisotropic, domain-warped fbm whose zero
 * iso-line is the vein. (ca, sa) is the run direction, measured from +x
 * towards the TOP. Few octaves on purpose: fine octaves in the LEVEL field
 * pinch off into small closed loops, which real veins don't make. (jag is
 * unused here; it is accepted so both fields take the same parameter list.)
 */
float layoutField(vec2 P, vec2 o, float ca, float sa, float across, float along, float warp, float jag) {
  vec2 uv = P / DP_H;
  float a = uv.x * ca - uv.y * sa;
  float b = uv.x * sa + uv.y * ca;
  float qa = a * along + warp * fbm(uv * 1.6 + o + vec2(11.0, 0.0), 4, 0.5);
  float qb = b * across + warp * fbm(uv * 1.6 + o + vec2(5.2, 24.3), 4, 0.5);
  return fbm(vec2(qa, qb) + o, 3, 0.5);
}

/** The vein field proper: the layout, displaced at three scales so the lines kink like cracks. */
float veinField(vec2 P, vec2 o, float ca, float sa, float across, float along, float warp, float jag) {
  vec2 j = jag * vec2(fbm(P / 46.0 + o, 3, 0.55), fbm(P / 46.0 + o + vec2(9.1, 3.7), 3, 0.55))
    + 0.45 * jag * vec2(fbm(P / 15.0 + o + vec2(7.7, 0.0), 3, 0.55), fbm(P / 15.0 + o + vec2(0.0, 2.2), 3, 0.55))
    + 0.9 * vec2(fbm(P / 7.0 + o + vec2(3.3, 0.0), 3, 0.55), fbm(P / 7.0 + o + vec2(0.0, 5.1), 3, 0.55));
  return layoutField(P + j, o, ca, sa, across, along, warp, jag);
}

/**
 * How decisively the layout field crosses zero here, 0..1. Gentle crossings
 * are where an iso-line closes into a small loop, so veins are faded out
 * there. Thresholds come from the slope distribution at zero crossings for
 * these sets: median 2.6-3.6 per uv, lowest decile 0.7-1.6.
 */
float steepness(vec2 P, vec2 o, float ca, float sa, float across, float along, float warp, float jag) {
  float n0 = layoutField(P, o, ca, sa, across, along, warp, jag);
  float nx = layoutField(P + vec2(4.0, 0.0), o, ca, sa, across, along, warp, jag);
  float ny = layoutField(P + vec2(0.0, 4.0), o, ca, sa, across, along, warp, jag);
  return smoothstep(0.9, 1.9, length(vec2(nx - n0, ny - n0)) * (DP_H / 4.0));
}

/**
 * Distance in design px to the field's zero iso-line, |n| / |grad n|. Using a
 * true distance (not |n| itself) keeps a vein's width honest where the field
 * flattens out, instead of ballooning into blobs.
 */
float isoDist(vec2 P, vec2 o, float ca, float sa, float across, float along, float warp, float jag) {
  float n0 = veinField(P, o, ca, sa, across, along, warp, jag);
  float nx = veinField(P + vec2(0.6, 0.0), o, ca, sa, across, along, warp, jag);
  float ny = veinField(P + vec2(0.0, 0.6), o, ca, sa, across, along, warp, jag);
  vec2 g = vec2(nx - n0, ny - n0) / 0.6;
  return abs(n0) / max(length(g), 1e-6);
}

/* Distances live in 8-bit channels, square-root encoded so the first few
   pixels either side of a vein — where its width is decided — get most of the
   precision, while halos and speckles can still reach 48 dp out. */
float encDist(float d) { return sqrt(clamp(d / 48.0, 0.0, 1.0)); }
float decDist(float e) { return 48.0 * e * e; }

/* Where the blue may be strong: a cluster top-right (as in the design), a band
   through the lower middle, and a quieter field everywhere else. */
float emphasis(vec2 uv) {
  float tr = exp(-(sq((uv.x - 1.08) / 0.5) + sq((uv.y - 0.02) / 0.34)));
  float low = exp(-(sq((uv.x - 0.62) / 0.42) + sq((uv.y - 0.86) / 0.22)));
  float mid = exp(-(sq((uv.x - 0.55) / 0.3) + sq((uv.y - 0.18) / 0.25)));
  return clamp(0.4 + 0.95 * tr + 0.5 * low + 0.3 * mid + 0.8 * fbm(uv * 2.2 + seed(51.0), 3, 0.5), 0.0, 1.0);
}

/* Resting depth along the veins, 0 = at the surface, 1 = sunk. Stretched along
   the run direction, so a vein surfaces and sinks over its LENGTH. */
float restDepth(vec2 uv, vec2 off) {
  float a = uv.x * 0.788011 - uv.y * 0.615661;
  float b = uv.x * 0.615661 + uv.y * 0.788011;
  return clamp(0.06 - fbm(vec2(a * 2.4, b * 1.1) + off, 4, 0.55) * 1.4, 0.0, 1.0);
}

/* Phase spread: varies across a set's veins (b), barely along them (a), so
   neighbouring veins draw at different moments while each front travels
   steadily. (ca, sa) is the set's run direction. */
float spread(vec2 uv, float ca, float sa, vec2 off) {
  float a = uv.x * ca - uv.y * sa;
  float b = uv.x * sa + uv.y * ca;
  return clamp(0.5 + 0.8 * fbm(vec2(b * 1.5, a * 0.25) + off, 3, 0.5), 0.0, 1.0);
}
`;

/* Vein-set geometry. Run directions as (cos, sin) of 36°, 18°, 48°, 42°, 58°. */
const BLUE_1 = "seed(3.0), 0.809017, 0.587785, 2.6, 0.52, 0.4, 8.0";
const BLUE_2 = "seed(17.0), 0.951057, 0.309017, 3.1, 0.46, 0.4, 6.0";
const BLUE_3 = "seed(43.0), 0.669131, 0.743145, 2.9, 0.62, 0.42, 7.0";
const GREY_1 = "seed(29.0), 0.743145, 0.669131, 3.6, 0.55, 0.35, 5.0";
const GREY_2 = "seed(37.0), 0.529919, 0.848048, 5.2, 0.55, 0.35, 4.0";

/** Full res: the stone (with its grey hairline veins) in rgb, cobalt set 1's distance in a. */
export const BAKE_STONE = /* glsl */ `${COMMON}
const vec3 STONE_LIGHT = vec3(0.969, 0.973, 0.992); // #f7f8fd
const vec3 STONE_MID = vec3(0.886, 0.902, 0.953);   // #e2e6f3
const vec3 STONE_SHADE = vec3(0.776, 0.808, 0.898); // #c6cee5
const vec3 GREY_VEIN = vec3(0.612, 0.643, 0.753);   // #9ca4c0

void main() {
  vec2 P = dpPos();
  vec2 uv = P / DP_H;

  // soft cloudy body, a faint diagonal haze, and mid-scale mottling
  float c1 = fbm(uv * 1.5 + seed(71.0), 6, 0.55);
  float c2 = fbm(uv * 0.7 + vec2(3.3, 1.1) + seed(73.0), 4, 0.5);
  float s = fbm(vec2(uv.x * 0.711 - uv.y * 0.549, (uv.x * 0.61 + uv.y * 0.79) * 3.4) + seed(79.0), 5, 0.5);
  float t = 0.5 + 1.2 * c1 + 0.6 * c2;
  float mottle = smoothstep(0.05, 0.45, fbm(uv * 4.2 + vec2(8.8, 2.1) + seed(71.0), 6, 0.55));
  vec3 col = mix(STONE_LIGHT, STONE_MID, smoothstep(0.25, 0.85, t));
  float shade = smoothstep(0.15, 0.6, s) * 0.55 + smoothstep(0.55, 1.0, t) * 0.5;
  col = mix(col, STONE_SHADE, clamp(shade * 0.7 + mottle * 0.35, 0.0, 1.0));

  // grey ghost veins: two crossing sets make the fine hairline network
  float w = 0.8 + 0.6 * (0.5 + fbm(uv * 3.0 + vec2(4.0, 0.0) + seed(89.0), 3, 0.5));
  float fragG = smoothstep(-0.3, 0.15, fbm(uv * 2.0 + seed(67.0), 3, 0.5));
  float fragG2 = smoothstep(-0.1, 0.2, fbm(uv * 2.4 + seed(69.0), 3, 0.5));
  float k = 0.0;
  if (fragG > 0.002) {
    float g1 = isoDist(P, ${GREY_1});
    k += fragG * (0.85 * exp(-sq(g1 / w)) + 0.1 * exp(-sq(g1 / (w * 6.0))));
  }
  if (fragG2 > 0.002) {
    float g2 = isoDist(P, ${GREY_2});
    k += 0.5 * fragG2 * exp(-sq(g2 / (w * 0.8)));
  }
  col = mix(col, GREY_VEIN, clamp(k, 0.0, 1.0));

  float d1 = 48.0;
  if (emphasis(uv) > 0.005) d1 = isoDist(P, ${BLUE_1});
  gl_FragColor = vec4(col, encDist(d1));
}
`;

/** Full res: set 2's distance, the speckle field, the left-edge dissolve, set 3's distance. */
export const BAKE_DETAIL = /* glsl */ `${COMMON}
const float FADE_DP = 360.0; // the stone fades in over ~190 CSS px from the region's left edge

void main() {
  vec2 P = dpPos();
  vec2 uv = P / DP_H;

  float d2 = 48.0;
  float present = smoothstep(0.12, 0.38, fbm(uv * 2.6 + seed(61.0), 3, 0.5));
  if (present > 0.002) d2 = isoDist(P, ${BLUE_2});

  float speck = gnoise(P / 2.6 + seed(97.0)) * 0.75 + gnoise(P / 9.0 + seed(101.0)) * 0.65;

  // Irregular dissolve into the page ground. The second factor pins it to
  // exactly zero at the region's edge, so nothing ever crosses it.
  float x = gl_FragCoord.x * uPxToDp.x / FADE_DP;
  float edge = x + 0.35 * fbm(uv * 2.4 + seed(83.0), 4, 0.55) + 0.1 * fbm(uv * 9.0 + seed(83.0), 4, 0.55);
  float dissolve = smoothstep(0.0, 1.0, edge) * smoothstep(0.0, 0.2, x);

  float d3 = 48.0;
  if (emphasis(uv) > 0.005) d3 = isoDist(P, ${BLUE_3});
  gl_FragColor = vec4(encDist(d2), clamp((speck + 1.4) / 2.8, 0.0, 1.0), dissolve, encDist(d3));
}
`;

/** Quarter res: emphasis, set 2's presence, and each set's phase spread. */
export const BAKE_FIELDS = /* glsl */ `${COMMON}
void main() {
  vec2 uv = dpPos() / DP_H;
  float present = smoothstep(0.12, 0.38, fbm(uv * 2.6 + seed(61.0), 3, 0.5)) * 0.85;
  float h1 = spread(uv, 0.809017, 0.587785, seed(113.0));
  float h2 = spread(uv, 0.951057, 0.309017, seed(127.0));
  gl_FragColor = vec4(emphasis(uv), present, h1, h2);
}
`;

/** Quarter res: resting depths for sets 1 and 2 — two versions each, which
 *  the composite drifts between, so the stretches that run crisp change too. */
export const BAKE_DEPTH = /* glsl */ `${COMMON}
void main() {
  vec2 P = dpPos();
  vec2 uv = P / DP_H;
  // A gentle crossing rests fully sunk, i.e. never shows (see steepness()).
  float s1 = steepness(P, ${BLUE_1});
  float s2 = steepness(P, ${BLUE_2});
  gl_FragColor = vec4(
    mix(1.0, restDepth(uv, seed(201.0)), s1),
    mix(1.0, restDepth(uv, seed(211.0)), s2),
    mix(1.0, restDepth(uv, vec2(1.7, 0.63) + seed(201.0)), s1),
    mix(1.0, restDepth(uv, vec2(2.3, 0.85) + seed(211.0)), s2)
  );
}
`;

/** Quarter res: line width, and set 3's phase spread and resting depths. */
export const BAKE_EXTRA = /* glsl */ `${COMMON}
void main() {
  vec2 P = dpPos();
  vec2 uv = P / DP_H;
  float s3 = steepness(P, ${BLUE_3});
  gl_FragColor = vec4(
    clamp(0.5 + fbm(uv * 2.2 + seed(89.0), 3, 0.5), 0.0, 1.0),
    spread(uv, 0.669131, 0.743145, seed(131.0)),
    mix(1.0, restDepth(uv, seed(223.0)), s3),
    mix(1.0, restDepth(uv, vec2(1.9, 0.71) + seed(223.0)), s3)
  );
}
`;

/** Every frame. */
export const COMPOSITE = /* glsl */ `${COMMON}
uniform sampler2D uStone;  // stone rgb, set 1 distance
uniform sampler2D uDetail; // set 2 distance, speckle, dissolve, set 3 distance
uniform sampler2D uFields; // emphasis, set 2 presence, phase spread 1, 2
uniform sampler2D uDepth;  // resting depths, sets 1 and 2
uniform sampler2D uExtra;  // line width, set 3 phase spread and resting depths
uniform float uCycles1;    // set 1's clock, in cycles (wrapped at 97)
uniform float uCycles2;
uniform float uCycles3;
uniform float uDepthMix;

const vec3 COBALT_CORE = vec3(0.086, 0.255, 0.8);    // #1641cc
const vec3 COBALT_BLOOM = vec3(0.204, 0.349, 0.925); // #3459ec
const vec3 COBALT_SUNK = vec3(0.541, 0.62, 0.925);   // #8a9eec

const float L1 = 1.4;     // set 1: length of one cycle along the vein, in uv
const float L2 = 1.1;
const float L3 = 1.25;
const float SPREAD = 0.6; // how far apart (in cycles) neighbouring veins run

float vnoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = p - i;
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash12(i), hash12(i + vec2(1.0, 0.0)), u.x),
    mix(hash12(i + vec2(0.0, 1.0)), hash12(i + vec2(1.0, 1.0)), u.x),
    u.y
  );
}

/* Which stretches of vein take part in cycle c. The pattern for each cycle is
   read from a circle in noise space, so cycle 97 is cycle 0 again and the
   clock can wrap without anything jumping. */
float pick(vec2 uv, float c) {
  float ang = c * 0.0647767; // 2pi / 97
  return smoothstep(0.24, 0.46, vnoise(uv * 1.7 + 31.0 * vec2(cos(ang), sin(ang))));
}

vec3 inkVein(vec3 col, float dist, float rest, float presence, float E, float w0, float speckN,
             float phi, float chosen, float chosenNext) {
  float rise = smoothstep(0.0, 0.012, phi);       // the stroke's leading taper
  float tip = 1.0 - smoothstep(0.0, 0.05, phi);   // wet ink just behind the front
  float sink = smoothstep(0.42, 0.84, phi);       // slowly settles back into the stone
  float ahead = smoothstep(0.955, 1.0, phi);      // pigment seeping ahead of the front

  float D = clamp(rest + sink * 1.15, 0.0, 1.0);  // 0 at the surface, 1 sunk out of sight
  float vis = (1.0 - smoothstep(0.4, 0.85, D)) * presence * E * rise * chosen;
  float sharp = 1.0 - smoothstep(0.0, 0.5, D);

  float w = w0 * (1.0 + 3.5 * D * D) * (1.0 + 0.3 * tip);
  float core = exp(-sq(dist / w)) / (1.0 + 1.6 * D);
  float bloom = exp(-sq(dist / (4.0 + 6.0 * D))) * (0.16 + 0.14 * E) * sharp
    + 0.3 * tip * exp(-sq(dist / 8.0));
  float pool = exp(-sq(dist / 3.2)) * smoothstep(0.6, 1.0, E) * sharp * 0.5;
  float speck = smoothstep(0.0, 0.16, speckN - (0.82 - 0.45 * E))
    * exp(-sq(dist / 18.0)) * sharp * smoothstep(0.4, 0.85, E);
  vec3 coreCol = mix(COBALT_CORE, COBALT_SUNK, smoothstep(0.0, 0.8, D));

  col = mix(col, COBALT_BLOOM, clamp(bloom * vis, 0.0, 1.0));
  col = mix(col, coreCol, clamp((pool + core) * vis, 0.0, 1.0));
  col = mix(col, COBALT_CORE, clamp(speck * 0.9 * presence * rise * chosen, 0.0, 1.0));

  float seep = ahead * 0.14 * exp(-sq(dist / 5.0)) * presence * E * chosenNext
    * (1.0 - smoothstep(0.4, 0.85, rest));
  return mix(col, COBALT_BLOOM, clamp(seep, 0.0, 1.0));
}

void main() {
  vec2 st = gl_FragCoord.xy / uRes;
  vec4 stone = texture2D(uStone, st);
  vec4 detail = texture2D(uDetail, st);
  float dissolve = detail.b;
  if (dissolve < 0.002) {
    gl_FragColor = vec4(0.0);
    return;
  }
  vec4 fields = texture2D(uFields, st);
  vec4 rest = texture2D(uDepth, st);
  vec4 extra = texture2D(uExtra, st);

  vec3 col = stone.rgb;
  float d1 = decDist(stone.a);
  float d2 = decDist(detail.r);
  float d3 = decDist(detail.a);
  float speckN = detail.g * 2.8 - 1.4;
  float w0 = 1.1 + 2.0 * extra.r;
  float E = fields.r;
  vec2 uv = dpPos() / DP_H;

  // Set 1 draws from bottom-left to top-right.
  if (d1 < 40.0) {
    float x = uCycles1 - (uv.x * 0.809017 - uv.y * 0.587785) / L1 + fields.b * SPREAD;
    float c = floor(x);
    col = inkVein(col, d1, mix(rest.r, rest.b, uDepthMix), 1.0, E, w0, speckN,
                  x - c, pick(uv, c), pick(uv, c + 1.0));
  }
  // Set 2, the cross-cracks, draws the other way.
  if (d2 < 40.0 && fields.g > 0.002) {
    float x = uCycles2 + (uv.x * 0.951057 - uv.y * 0.309017) / L2 + fields.a * SPREAD;
    float c = floor(x);
    vec2 o = vec2(7.3, 3.1);
    col = inkVein(col, d2, mix(rest.g, rest.a, uDepthMix), fields.g, E, w0, speckN,
                  x - c, pick(uv + o, c), pick(uv + o, c + 1.0));
  }
  // Set 3, steeper, draws bottom-left to top-right on its own clock.
  if (d3 < 40.0) {
    float x = uCycles3 - (uv.x * 0.669131 - uv.y * 0.743145) / L3 + extra.g * SPREAD;
    float c = floor(x);
    vec2 o = vec2(-4.9, 11.7);
    col = inkVein(col, d3, mix(extra.b, extra.a, uDepthMix), 1.0, E, w0, speckN,
                  x - c, pick(uv + o, c), pick(uv + o, c + 1.0));
  }

  gl_FragColor = vec4(col * dissolve, dissolve); // premultiplied over the page ground
}
`;
