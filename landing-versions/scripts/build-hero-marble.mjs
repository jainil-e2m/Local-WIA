/**
 * Offline builder for the landing hero's STILL marble — writes
 * public/landing/marble-a.webp.
 *
 *   node scripts/build-hero-marble.mjs
 *
 * The hero's marble is normally live: src/components/marble/ renders it with
 * WebGL, veins drawing themselves and fading. That renderer is a GPU port of
 * this script — same noise model, same tuned constants, in the same "design
 * pixel" grid — so this file is where the look was first matched against the
 * delivered design. Its output is now only the fallback for a browser without
 * WebGL (or one that loses its GL context). If you retune the live shaders,
 * the still drifting a little from them is acceptable; it is rarely seen.
 *
 * WHY NOT A LIVE SVG FILTER. The prototype drew the stone with stacked
 * feTurbulence filters. Those rasterise on the CPU, re-run on every resize,
 * render differently in Safari, and can only produce veins of one even width
 * and strength — which is exactly what reads as fake.
 *
 * WHAT MAKES IT READ AS STONE
 *   - Veins are iso-lines of a domain-warped, anisotropic noise field, so they
 *     run diagonally (bottom-left → top-right) and wander rather than repeat.
 *     Line width comes from distance-to-iso-line (|n| / |∇n|), so a vein keeps
 *     a true pixel width instead of ballooning wherever the field flattens.
 *   - A small high-frequency warp kinks them like cracks.
 *   - Every vein has a DEPTH that varies along its length: at the surface it is
 *     thin, sharp and deep cobalt; as it sinks it widens, softens, pales and
 *     finally disappears into the stone. That is the "fades in and out" look.
 *   - Pigment speckles and a soft bloom gather only around surfaced veins.
 *   - The left edge dissolves irregularly into the page ground (#f5f7fb).
 */
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { PNG } = require("pngjs");
const ffmpeg = require("ffmpeg-static");

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT_DIR = path.join(ROOT, "public", "landing");

const W = 1800;
const H = 1560;

/* ── noise ─────────────────────────────────────────────────────────────── */

function makeRng(seed) {
  let s = seed >>> 0 || 1;
  return () => (s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296;
}

function makeNoise(seed) {
  const rnd = makeRng(seed);
  const p = Array.from({ length: 256 }, (_, i) => i);
  for (let i = 255; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [p[i], p[j]] = [p[j], p[i]];
  }
  const perm = new Uint8Array(512);
  for (let i = 0; i < 512; i++) perm[i] = p[i & 255];
  const gx = new Float32Array(256);
  const gy = new Float32Array(256);
  for (let i = 0; i < 256; i++) {
    const a = rnd() * Math.PI * 2;
    gx[i] = Math.cos(a);
    gy[i] = Math.sin(a);
  }
  return (x, y) => {
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    const xf = x - xi;
    const yf = y - yi;
    const X = xi & 255;
    const Y = yi & 255;
    const u = xf * xf * xf * (xf * (xf * 6 - 15) + 10);
    const v = yf * yf * yf * (yf * (yf * 6 - 15) + 10);
    const aa = perm[perm[X] + Y];
    const ab = perm[perm[X] + Y + 1];
    const ba = perm[perm[X + 1] + Y];
    const bb = perm[perm[X + 1] + Y + 1];
    const n00 = gx[aa] * xf + gy[aa] * yf;
    const n10 = gx[ba] * (xf - 1) + gy[ba] * yf;
    const n01 = gx[ab] * xf + gy[ab] * (yf - 1);
    const n11 = gx[bb] * (xf - 1) + gy[bb] * (yf - 1);
    const x1 = n00 + (n10 - n00) * u;
    const x2 = n01 + (n11 - n01) * u;
    return (x1 + (x2 - x1) * v) * 1.41;
  };
}

function makeFbm(seed, octaves, gain = 0.5, lacunarity = 2.03) {
  const layers = Array.from({ length: octaves }, (_, i) => makeNoise(seed * 7919 + i * 104729));
  let norm = 0;
  for (let i = 0, a = 1; i < octaves; i++, a *= gain) norm += a;
  return (x, y) => {
    let sum = 0;
    let amp = 1;
    let f = 1;
    for (let i = 0; i < octaves; i++) {
      sum += amp * layers[i](x * f, y * f);
      amp *= gain;
      f *= lacunarity;
    }
    return sum / norm;
  };
}

const clamp01 = (t) => (t < 0 ? 0 : t > 1 ? 1 : t);
const smooth = (a, b, t) => {
  const x = clamp01((t - a) / (b - a));
  return x * x * (3 - 2 * x);
};
const mix = (a, b, t) => a + (b - a) * t;
const hexRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);

/* ── palette (sampled from the delivered design) ──────────────────────── */

const GROUND = hexRgb("#f5f7fb"); // page background the stone dissolves into
const STONE_LIGHT = hexRgb("#f7f8fd");
const STONE_MID = hexRgb("#e2e6f3");
const STONE_SHADE = hexRgb("#c6cee5");
const GREY_VEIN = hexRgb("#9ca4c0");
const COBALT_CORE = hexRgb("#1641cc");
const COBALT_BLOOM = hexRgb("#3459ec");
const COBALT_SUNK = hexRgb("#8a9eec");

/* ── fields ────────────────────────────────────────────────────────────── */

/**
 * A vein field: anisotropic, domain-warped fbm evaluated over the image.
 * Its zero iso-line is the vein. `angleDeg` is the run direction measured
 * from +x towards the TOP of the image.
 */
function veinField({ seed, angleDeg, across, along, warp, jag }) {
  const base = makeFbm(seed, 5, 0.52);
  const wx = makeFbm(seed + 11, 4, 0.5);
  const wy = makeFbm(seed + 23, 4, 0.5);
  const jx = makeFbm(seed + 37, 3, 0.55);
  const jy = makeFbm(seed + 41, 3, 0.55);
  const th = (angleDeg * Math.PI) / 180;
  const ca = Math.cos(th);
  const sa = Math.sin(th);
  const out = new Float32Array(W * H);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      // crack-like kinks: a few pixels of high-frequency displacement
      const px =
        x +
        jag * jx(x / 46, y / 46) +
        0.45 * jag * jx(x / 15 + 7.7, y / 15) +
        0.9 * jx(x / 7 + 3.3, y / 7);
      const py =
        y +
        jag * jy(x / 46 + 9.1, y / 46 + 3.7) +
        0.45 * jag * jy(x / 15, y / 15 + 2.2) +
        0.9 * jy(x / 7, y / 7 + 5.1);
      const u = px / H;
      const v = py / H;
      // rotate into the vein frame (image y points down)
      const a = u * ca - v * sa;
      const b = u * sa + v * ca;
      const qa = a * along + warp * wx(u * 1.6, v * 1.6);
      const qb = b * across + warp * wy(u * 1.6 + 5.2, v * 1.6 + 1.3);
      out[y * W + x] = base(qa, qb);
    }
  }
  return out;
}

/** Distance in pixels to the field's zero iso-line, from |n| / |∇n|. */
function isoDistance(field) {
  const out = new Float32Array(W * H);
  for (let y = 0; y < H; y++) {
    const y0 = y > 0 ? y - 1 : y;
    const y1 = y < H - 1 ? y + 1 : y;
    for (let x = 0; x < W; x++) {
      const x0 = x > 0 ? x - 1 : x;
      const x1 = x < W - 1 ? x + 1 : x;
      const gx = (field[y * W + x1] - field[y * W + x0]) / (x1 - x0);
      const gy = (field[y1 * W + x] - field[y0 * W + x]) / (y1 - y0);
      const g = Math.max(Math.hypot(gx, gy), 1e-6);
      out[y * W + x] = Math.abs(field[y * W + x]) / g;
    }
  }
  return out;
}

/** A scalar map over the image, f(u, v) with u, v in image-height units. */
function scalarMap(fn) {
  const out = new Float32Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) out[y * W + x] = fn(x / H, y / H, x, y);
  return out;
}

console.time("fields");

// Primary cobalt veins, ~38° — the dominant diagonal of the design.
const blue1 = isoDistance(
  veinField({ seed: 3, angleDeg: 36, across: 2.6, along: 0.42, warp: 0.3, jag: 8 }),
);
// Secondary, sparser set at a shallower angle — branches and cross-cracks.
const blue2 = isoDistance(
  veinField({ seed: 17, angleDeg: 18, across: 3.1, along: 0.34, warp: 0.3, jag: 6 }),
);
// Faint grey ghost veins — two crossing sets make the fine hairline network.
const grey = isoDistance(
  veinField({ seed: 29, angleDeg: 42, across: 3.6, along: 0.55, warp: 0.35, jag: 5 }),
);
const grey2 = isoDistance(
  veinField({ seed: 31, angleDeg: 58, across: 5.2, along: 0.9, warp: 0.4, jag: 4 }),
);

// Where the blue is allowed to be strong: a top-right cluster (as in the
// design), a band through the lower middle, everything else quieter.
const emphNoise = makeFbm(51, 3, 0.5);
const emphasis = scalarMap((u, v) => {
  const tr = Math.exp(-(((u - 1.08) / 0.5) ** 2 + ((v - 0.02) / 0.34) ** 2));
  const low = Math.exp(-(((u - 0.62) / 0.42) ** 2 + ((v - 0.86) / 0.22) ** 2));
  const mid = Math.exp(-(((u - 0.55) / 0.3) ** 2 + ((v - 0.18) / 0.25) ** 2));
  return clamp01(0.3 + 0.95 * tr + 0.5 * low + 0.3 * mid + 0.8 * emphNoise(u * 2.2, v * 2.2));
});

// Fragment masks: which stretches of each set exist at all.
const frag2Noise = makeFbm(61, 3, 0.5);
const frag2 = scalarMap((u, v) => smooth(0.12, 0.38, frag2Noise(u * 2.6, v * 2.6)));
const fragGNoise = makeFbm(67, 3, 0.5);
const fragG = scalarMap((u, v) => smooth(-0.15, 0.25, fragGNoise(u * 2, v * 2)));
const fragG2Noise = makeFbm(69, 3, 0.5);
const fragG2 = scalarMap((u, v) => smooth(0, 0.3, fragG2Noise(u * 2.4, v * 2.4)));

// Stone body.
const cloudA = makeFbm(71, 6, 0.55);
const cloudB = makeFbm(73, 4, 0.5);
const streak = makeFbm(79, 5, 0.5);
const edgeNoise = makeFbm(83, 4, 0.55);
const width = makeFbm(89, 3, 0.5);

// Speckle source: fine value-ish noise thresholded per pixel.
const speckN = makeNoise(97);
const speckN2 = makeNoise(101);

console.timeEnd("fields");

/**
 * Depth along the veins, 0 = at the surface (sharp, dark), 1 = sunk out of
 * sight. Sampled stretched along the vein direction so a vein surfaces and
 * sinks over its LENGTH rather than flickering across its width. `phase`
 * slides the field (the live renderer drifts between two such phases).
 */
function depthMap(seed, phase) {
  const f = makeFbm(seed, 4, 0.55);
  const th = (38 * Math.PI) / 180;
  const ca = Math.cos(th);
  const sa = Math.sin(th);
  return scalarMap((u, v) => {
    const a = u * ca - v * sa;
    const b = u * sa + v * ca;
    const n = f(a * 2.4 + phase, b * 1.1 + phase * 0.37);
    return clamp01(0.22 - n * 1.4);
  });
}

function render(depth1, depth2, file) {
  console.time(file);
  const png = new PNG({ width: W, height: H });
  const d = png.data;
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      const u = x / H;
      const v = y / H;
      const xf = x / W;

      /* stone — soft cloudy body with faint diagonal haze */
      const c1 = cloudA(u * 1.5, v * 1.5);
      const c2 = cloudB(u * 0.7 + 3.3, v * 0.7 + 1.1);
      const s = streak(u * 0.9 * 0.79 - v * 0.9 * 0.61, (u * 0.61 + v * 0.79) * 3.4);
      let t = 0.5 + 1.2 * c1 + 0.6 * c2;
      const mottle = smooth(0.05, 0.45, cloudA(u * 4.2 + 8.8, v * 4.2 + 2.1));
      let r = mix(STONE_LIGHT[0], STONE_MID[0], smooth(0.25, 0.85, t));
      let g = mix(STONE_LIGHT[1], STONE_MID[1], smooth(0.25, 0.85, t));
      let b = mix(STONE_LIGHT[2], STONE_MID[2], smooth(0.25, 0.85, t));
      const shade = smooth(0.15, 0.6, s) * 0.55 + smooth(0.55, 1.0, t) * 0.5;
      const shadeK = clamp01(shade * 0.95 + mottle * 0.7);
      r = mix(r, STONE_SHADE[0], shadeK);
      g = mix(g, STONE_SHADE[1], shadeK);
      b = mix(b, STONE_SHADE[2], shadeK);

      /* grey ghost veins */
      {
        const w = 0.8 + 0.6 * (0.5 + width(u * 3 + 4, v * 3));
        const a = 0.7 * fragG[i] * Math.exp(-((grey[i] / w) ** 2));
        const halo = 0.1 * fragG[i] * Math.exp(-((grey[i] / (w * 6)) ** 2));
        const a2 = 0.5 * fragG2[i] * Math.exp(-((grey2[i] / (w * 0.8)) ** 2));
        const k = clamp01(a + halo + a2);
        r = mix(r, GREY_VEIN[0], k);
        g = mix(g, GREY_VEIN[1], k);
        b = mix(b, GREY_VEIN[2], k);
      }

      /* cobalt veins: one pass per set */
      const E = emphasis[i];
      const sets = [
        [blue1[i], depth1[i], 1],
        [blue2[i], depth2[i], frag2[i] * 0.85],
      ];
      for (const [dist, D, presence] of sets) {
        if (presence <= 0.001) continue;
        // core width at the surface, 0.6–2.0 px, varying along the vein
        const w0 = 1.1 + 2.0 * clamp01(0.5 + width(u * 2.2, v * 2.2));
        // sinking widens and softens the line, and fades it out entirely
        const wSunk = w0 * (1 + 3.5 * D * D);
        const visible = (1 - smooth(0.4, 0.85, D)) * presence * E;
        if (visible <= 0.002) continue;
        const sharp = 1 - smooth(0.0, 0.5, D);
        const core = Math.exp(-((dist / wSunk) ** 2)) / (1 + 1.6 * D);
        const bloom = Math.exp(-((dist / (4 + 6 * D)) ** 2)) * (0.16 + 0.14 * E) * sharp;
        const pool = Math.exp(-((dist / 3.2) ** 2)) * smooth(0.6, 1, E) * sharp * 0.5;

        // pigment speckles cluster around surfaced veins in strong regions
        const sp =
          speckN(x / 2.6, y / 2.6) * 0.75 + speckN2(x / 9, y / 9) * 0.65 - (0.82 - 0.45 * E);
        const speck =
          smooth(0, 0.16, sp) * Math.exp(-((dist / 18) ** 2)) * sharp * smooth(0.4, 0.85, E);

        const coreCol = [0, 1, 2].map((k) =>
          mix(COBALT_CORE[k], COBALT_SUNK[k], smooth(0, 0.8, D)),
        );
        let k = clamp01(bloom * visible);
        r = mix(r, COBALT_BLOOM[0], k);
        g = mix(g, COBALT_BLOOM[1], k);
        b = mix(b, COBALT_BLOOM[2], k);
        k = clamp01((pool + core) * visible);
        r = mix(r, coreCol[0], k);
        g = mix(g, coreCol[1], k);
        b = mix(b, coreCol[2], k);
        k = clamp01(speck * 0.9 * presence);
        r = mix(r, COBALT_CORE[0], k);
        g = mix(g, COBALT_CORE[1], k);
        b = mix(b, COBALT_CORE[2], k);
      }

      /* irregular dissolve into the page ground on the left */
      const edge = xf + 0.07 * edgeNoise(u * 2.4, v * 2.4) + 0.02 * edgeNoise(u * 9, v * 9);
      const F = smooth(0.02, 0.32, edge);
      r = mix(GROUND[0], r, F);
      g = mix(GROUND[1], g, F);
      b = mix(GROUND[2], b, F);

      const o = i * 4;
      d[o] = Math.round(clamp01(r) * 255);
      d[o + 1] = Math.round(clamp01(g) * 255);
      d[o + 2] = Math.round(clamp01(b) * 255);
      d[o + 3] = 255;
    }
  }
  const tmp = path.join(OUT_DIR, `.${file}.png`);
  fs.writeFileSync(tmp, PNG.sync.write(png));
  execFileSync(ffmpeg, [
    "-v",
    "error",
    "-y",
    "-i",
    tmp,
    "-c:v",
    "libwebp",
    "-quality",
    "84",
    "-compression_level",
    "6",
    path.join(OUT_DIR, file),
  ]);
  if (!process.argv.includes("--keep-png")) fs.unlinkSync(tmp);
  console.timeEnd(file);
}

fs.mkdirSync(OUT_DIR, { recursive: true });
render(depthMap(201, 0), depthMap(211, 0), "marble-a.webp");
