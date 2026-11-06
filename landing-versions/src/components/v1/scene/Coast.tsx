import { memo, useMemo } from "react";
import { seeded } from "./stage";
import { smooth, xAt } from "./svg";

/* ────────────────────────────────────────────────────────────────
   The Amalfi coast in the arch — painted, not photographed, so it can
   move: the sea glitters, boats cross the bay trailing their wakes,
   clouds drift and the surf breathes at the foot of the cliff.

   Two SVGs on purpose. The town alone is a few hundred shapes, and any
   animated element inside an SVG repaints the whole SVG; so the still
   scenery lives in one and the handful of moving parts in another, and
   only the small one repaints per frame.

   Scene space is 290 × 560 (the arch). A print on the table reuses it
   through a different viewBox, at low detail and without the motion.
   ──────────────────────────────────────────────────────────────── */

export const COAST_W = 290;
export const COAST_H = 560;

/* The cliff's seaward edge, top to bottom — monotonic in y, so the town can
   ask "how far out does the rock reach at this height?" with xAt(). */
const EDGE: [number, number][] = [
  [0, 112],
  [38, 117],
  [66, 141],
  [94, 182],
  [120, 222],
  [146, 262],
  [162, 300],
  [172, 342],
  [178, 384],
  [181, 418],
  [171, 446],
  [148, 466],
  [108, 482],
  [58, 494],
  [0, 503],
];

const HOUSE = [
  "#f8f3ea",
  "#f5eadb",
  "#f2e2cf",
  "#f9f5ee",
  "#f0ddc6",
  "#f6ece0",
  "#efd9c0",
  "#fbf8f2",
  "#eed6bb",
  "#f4e6d2",
  "#f7efe4",
  "#ece2d4",
];

interface House {
  x: number;
  y: number;
  w: number;
  h: number;
  fill: string;
  roof: string | null;
  win: number;
}

/* Positano stacks its houses in terraces that follow the slope, so the town
   is laid out row by row from the water up rather than scattered: each row
   runs inward from the cliff edge with small gaps, the facades sit in a
   narrow band of pale tones, and only the shading separates them. Low
   contrast is what makes it read as a town at this size instead of noise. */
function buildTown(detail: "high" | "low"): { houses: House[]; trees: [number, number, number][] } {
  const rand = seeded(7);
  const houses: House[] = [];
  const trees: [number, number, number][] = [];
  const rowStep = detail === "high" ? 5.4 : 8;
  for (let y = 190; y < 468; y += rowStep + rand() * 1.6) {
    const edge = xAt(EDGE, y) - 6;
    // the town widens towards the water and thins out up the slope
    const depth = y < 240 ? 44 : y < 300 ? 92 : y < 400 ? 138 : 150;
    let x = edge - 4 - rand() * 6;
    const stop = Math.max(4, edge - depth - rand() * 14);
    while (x > stop) {
      const w = 4.6 + rand() * 5.4;
      const h = 4 + rand() * 3.2;
      x -= w + 0.6 + rand() * 1.8;
      if (x < stop) break;
      if (rand() < 0.12) {
        // a garden or a terrace wall instead of a house
        if (rand() < 0.6) trees.push([x + w / 2, y - 1, 2.2 + rand() * 3]);
        continue;
      }
      houses.push({
        x,
        y: y + (rand() - 0.5) * 2.4,
        w,
        h,
        fill: HOUSE[Math.floor(rand() * HOUSE.length)],
        roof: rand() < 0.16 ? (rand() < 0.65 ? "#d29576" : "#c4b59b") : null,
        win: detail === "high" && rand() < 0.3 ? (w > 9 ? 2 : 1) : 0,
      });
    }
  }
  houses.sort((a, b) => a.y - b.y);
  return { houses, trees };
}

const CLIFF = smooth([[-4, 108], ...EDGE.slice(1, -1), [-4, 507]], false, 0.6) + " L-4,560 L-10,560 Z";
const UPPER_GREEN = smooth(
  [
    [-4, 112],
    [34, 116],
    [62, 138],
    [86, 172],
    [96, 196],
    [72, 214],
    [44, 236],
    [18, 262],
    [-4, 280],
  ],
  false,
  0.6,
);
const HEADLAND = smooth(
  [
    [104, 238],
    [128, 229],
    [150, 218],
    [176, 211],
    [204, 206],
    [226, 197],
    [252, 192],
    [276, 194],
    [296, 190],
  ],
  false,
  0.5,
);
const FAR_RANGE = smooth(
  [
    [-4, 208],
    [40, 200],
    [78, 203],
    [118, 194],
    [160, 199],
    [204, 188],
    [248, 194],
    [296, 186],
  ],
  false,
  0.5,
);

/* ── Still scenery ─────────────────────────────────────────────── */

const f = (n: number) => Math.round(n * 10) / 10;

/* The town alone is well over a thousand shapes. As live DOM that is half a
   megabyte of markup the page has to style and hit-test forever; as an image
   it is rasterised once. So the still scenery is written out as one SVG
   document, cached per detail level, and drawn through a single <image>. */
const cache = new Map<string, string>();

function coastSvg(detail: "high" | "low"): string {
  const hit = cache.get(detail);
  if (hit) return hit;
  const { houses, trees } = buildTown(detail);
  const out: string[] = [];
  const add = (x: string) => out.push(x);

  add(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${COAST_W} ${COAST_H}" width="${COAST_W}" height="${COAST_H}">`);
  add(`<defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a9c7e6"/><stop offset="0.55" stop-color="#cfe0f0"/><stop offset="1" stop-color="#edf2f6"/></linearGradient>
    <linearGradient id="sea" x1="0" y1="0" x2="0.15" y2="1"><stop offset="0" stop-color="#9cc4df"/><stop offset="0.08" stop-color="#6ea7d2"/><stop offset="0.38" stop-color="#3b88c2"/><stop offset="0.75" stop-color="#2470ad"/><stop offset="1" stop-color="#1b5d97"/></linearGradient>
    <radialGradient id="cove" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#4fb7c6" stop-opacity="0.85"/><stop offset="1" stop-color="#4fb7c6" stop-opacity="0"/></radialGradient>
    <linearGradient id="rock" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#bdb29c"/><stop offset="0.5" stop-color="#a39780"/><stop offset="1" stop-color="#857a68"/></linearGradient>
    <linearGradient id="green" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#98b27e"/><stop offset="1" stop-color="#6d8a5a"/></linearGradient>
    <linearGradient id="head" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8fa58f"/><stop offset="1" stop-color="#6f8a77"/></linearGradient>
    <linearGradient id="haze" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.5" stop-color="#f4f7fa" stop-opacity="0.55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
    <radialGradient id="sun" cx="0.85" cy="0.12" r="0.7"><stop offset="0" stop-color="#fffaf0" stop-opacity="0.55"/><stop offset="1" stop-color="#fffaf0" stop-opacity="0"/></radialGradient>
    <linearGradient id="airy" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4f7fb" stop-opacity="0.5"/><stop offset="0.45" stop-color="#f4f7fb" stop-opacity="0.16"/><stop offset="1" stop-color="#f4f7fb" stop-opacity="0"/></linearGradient>
    <linearGradient id="shade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#1c2a3a" stop-opacity="0.16"/><stop offset="0.6" stop-color="#1c2a3a" stop-opacity="0"/></linearGradient>
  </defs>`);

  // sky and sea
  add(`<rect width="${COAST_W}" height="230" fill="url(#sky)"/>`);
  add(`<rect y="200" width="${COAST_W}" height="${COAST_H - 200}" fill="url(#sea)"/>`);
  add(`<ellipse cx="150" cy="452" rx="60" ry="26" fill="url(#cove)"/>`);
  add(`<ellipse cx="190" cy="430" rx="40" ry="18" fill="url(#cove)" opacity="0.7"/>`);
  add(`<ellipse cx="70" cy="520" rx="90" ry="34" fill="url(#cove)" opacity="0.75"/>`);

  // far range and the headland across the bay, with its village
  add(`<path d="${FAR_RANGE} L296,214 L-4,214 Z" fill="#b7c7d6" opacity="0.85"/>`);
  add(`<path d="${HEADLAND} L296,246 L104,246 Z" fill="url(#head)"/>`);
  add(`<path d="M104,245 L296,245" stroke="#dce8ef" stroke-width="1.4" opacity="0.7"/>`);
  const village: string[] = [];
  for (let i = 0; i < (detail === "high" ? 46 : 18); i++) {
    const r = seeded(100 + i)();
    const x = 132 + ((i * 37) % 150) + r * 4;
    const y = 233 + ((i * 13) % 9) - (x - 132) * 0.04;
    village.push(`M${f(x)},${f(y)}h${f(1.6 + r * 1.6)}v${f(1.2 + r)}h${f(-(1.6 + r * 1.6))}z`);
  }
  add(`<path d="${village.join("")}" fill="#f4efe6" opacity="0.75"/>`);
  add(`<rect y="176" width="${COAST_W}" height="80" fill="url(#haze)"/>`);

  // the cliff, its upper gardens, crags and terraces
  add(`<path d="${CLIFF}" fill="url(#rock)"/>`);
  add(`<path d="${UPPER_GREEN} L-4,112 Z" fill="url(#green)" opacity="0.95"/>`);
  const crag = seeded(19);
  for (let i = 0; i < (detail === "high" ? 30 : 12); i++) {
    const y = 190 + crag() * 280;
    const x = xAt(EDGE, y) - 4 - crag() * 18;
    const r = 2 + crag() * 6;
    add(`<ellipse cx="${f(x)}" cy="${f(y)}" rx="${f(r)}" ry="${f(r * 0.6)}" fill="#5d584e" opacity="${f(0.1 + crag() * 0.14)}"/>`);
  }
  for (let i = 0; i < (detail === "high" ? 30 : 12); i++) {
    const rand = seeded(300 + i);
    const y = 196 + rand() * 260;
    const x = Math.max(4, xAt(EDGE, y) - 60 - rand() * 80);
    const fill = rand() < 0.5 ? "#7f9a66" : "#6a8656";
    add(`<ellipse cx="${f(x)}" cy="${f(y)}" rx="${f(8 + rand() * 18)}" ry="${f(3 + rand() * 4)}" fill="${fill}" opacity="0.72"/>`);
  }

  // the town: facades, then their shade, roofs and windows, back to front
  for (const h of houses) {
    add(`<rect x="${f(h.x)}" y="${f(h.y)}" width="${f(h.w)}" height="${f(h.h)}" fill="${h.fill}"/>`);
    add(`<path d="M${f(h.x + h.w * 0.74)},${f(h.y)}h${f(h.w * 0.26)}v${f(h.h)}h${f(-h.w)}v-0.9h${f(h.w * 0.74)}z" fill="#7a6650" opacity="0.11"/>`);
    if (h.roof) add(`<rect x="${f(h.x - 0.3)}" y="${f(h.y - 1.1)}" width="${f(h.w + 0.6)}" height="1.5" fill="${h.roof}"/>`);
    if (h.win > 0)
      add(`<path d="M${f(h.x + 1.6)},${f(h.y + h.h * 0.4)}h1v1.5h-1z${h.win > 1 ? `M${f(h.x + 4.4)},${f(h.y + h.h * 0.4)}h1v1.5h-1z` : ""}" fill="#6d6a68" opacity="0.32"/>`);
  }
  for (const [x, y, sz] of trees) {
    add(`<ellipse cx="${f(x)}" cy="${f(y)}" rx="${f(sz * 0.45)}" ry="${f(sz)}" fill="#4c6a45" opacity="0.85"/>`);
  }

  // the church: majolica dome and campanile
  add(`<g transform="translate(118 356)">
    <rect x="-1" y="0" width="16" height="11" fill="#f6efe2"/>
    <rect x="11" y="0" width="4" height="11" fill="#5a4a3a" opacity="0.15"/>
    <path d="M1,0 A6.5,6.5 0 0 1 14,0 Z" fill="#d7b64e"/>
    <path d="M3.4,-3.4 Q7.5,-6.6 11.6,-3.4" stroke="#4f8a63" stroke-width="0.9" fill="none"/>
    <path d="M7.5,-6.5 L7.5,0" stroke="#3f7a55" stroke-width="0.7"/>
    <rect x="-7" y="-12" width="5" height="23" fill="#f3e9d8"/>
    <rect x="-7" y="-15" width="5" height="3" fill="#c9795a"/>
    <rect x="-5.6" y="-9" width="1.6" height="2.4" fill="#4b4a4d" opacity="0.6"/>
  </g>`);

  // the beach under the town, with its umbrellas
  add(`<path d="M84,486 Q118,474 152,466 L160,472 Q122,482 86,493 Z" fill="#e9dcc4"/>`);
  if (detail === "high") {
    for (const [x, y, c] of [
      [98, 482, "#e46a4f"],
      [106, 480, "#f2b84b"],
      [114, 478, "#3e7fc1"],
      [122, 476, "#e46a4f"],
      [131, 474, "#f2b84b"],
      [139, 472, "#3e7fc1"],
    ] as const)
      add(`<circle cx="${x}" cy="${y}" r="1.9" fill="${c}"/>`);
  }

  // sea stacks
  add(`<path d="M168,500 C170,482 176,468 184,462 C190,458 194,466 196,476 C199,488 200,496 203,504 Z" fill="url(#rock)"/>`);
  add(`<path d="M196,504 C198,494 203,488 209,489 C214,490 215,498 217,505 Z" fill="#7c776b"/>`);
  add(`<path d="M176,474 C178,468 182,464 185,463" stroke="#c9c2b0" stroke-width="1.2" fill="none" opacity="0.7"/>`);

  // air over the far slope, sun from the upper right, shade on the left
  add(`<path d="${CLIFF}" fill="url(#airy)"/>`);
  add(`<rect width="${COAST_W}" height="${COAST_H}" fill="url(#sun)"/>`);
  add(`<rect width="${COAST_W}" height="${COAST_H}" fill="url(#shade)"/>`);
  add(`</svg>`);

  const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(out.join(""))}`;
  cache.set(detail, url);
  return url;
}

export const CoastStatic = memo(function CoastStatic({
  viewBox = `0 0 ${COAST_W} ${COAST_H}`,
  detail = "high",
  className,
}: {
  viewBox?: string;
  detail?: "high" | "low";
  className?: string;
}) {
  const href = useMemo(() => coastSvg(detail), [detail]);
  return (
    <svg viewBox={viewBox} preserveAspectRatio="xMidYMid slice" className={className} aria-hidden>
      <image href={href} x="0" y="0" width={COAST_W} height={COAST_H} preserveAspectRatio="none" />
    </svg>
  );
});

/* ── Moving parts ──────────────────────────────────────────────── */

export const CoastLive = memo(function CoastLive({ className }: { className?: string }) {
  const glints = useMemo(() => {
    const rand = seeded(41);
    return Array.from({ length: 46 }, () => {
      const y = 214 + Math.pow(rand(), 1.3) * 330;
      const nearSun = rand() < 0.45;
      const x = nearSun ? 170 + rand() * 120 : 150 + rand() * 140 - (y - 214) * 0.12;
      return {
        x,
        y,
        w: 3 + rand() * (y > 380 ? 16 : 10),
        o: 0.25 + rand() * 0.55,
        d: 2.6 + rand() * 4,
        delay: -rand() * 6,
      };
    });
  }, []);

  return (
    <svg viewBox={`0 0 ${COAST_W} ${COAST_H}`} preserveAspectRatio="xMidYMid slice" className={className} aria-hidden>
      <defs>
        <radialGradient id="v1-cloud">
          <stop offset="0" stopColor="#fff" stopOpacity="0.95" />
          <stop offset="0.6" stopColor="#fff" stopOpacity="0.5" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
        {/* wakes fade away from the stern: L is opaque on its left end, R on its right */}
        <linearGradient id="v1-wake-l" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#fff" stopOpacity="0.9" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="v1-wake-r" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#fff" stopOpacity="0" />
          <stop offset="1" stopColor="#fff" stopOpacity="0.9" />
        </linearGradient>
      </defs>

      {/* clouds */}
      <g className="v1-cloud-drift">
        <ellipse cx="70" cy="70" rx="46" ry="12" fill="url(#v1-cloud)" />
        <ellipse cx="96" cy="62" rx="26" ry="10" fill="url(#v1-cloud)" />
        <ellipse cx="214" cy="118" rx="52" ry="10" fill="url(#v1-cloud)" opacity="0.8" />
        <ellipse cx="160" cy="156" rx="34" ry="6" fill="url(#v1-cloud)" opacity="0.7" />
      </g>
      <g className="v1-cloud-drift is-slow">
        <ellipse cx="-40" cy="96" rx="40" ry="9" fill="url(#v1-cloud)" opacity="0.75" />
        <ellipse cx="250" cy="40" rx="34" ry="9" fill="url(#v1-cloud)" opacity="0.6" />
      </g>

      {/* glitter on the water */}
      {glints.map((g, i) => (
        <rect
          key={i}
          className="v1-glint"
          x={g.x}
          y={g.y}
          width={g.w}
          height={g.y > 360 ? 1.3 : 0.9}
          rx="0.5"
          fill="#f3fbff"
          style={{
            ["--o" as string]: g.o,
            animationDuration: `${g.d}s`,
            animationDelay: `${g.delay}s`,
          }}
        />
      ))}

      {/* boats: hull, cabin and a wake that trails behind the direction of travel */}
      <g className="v1-boat is-west">
        {/* heading west, bow on the left, wake trailing east */}
        <g transform="translate(0 304)">
          <path d="M11,-0.7 L50,-3.4 L50,3.4 L11,0.7 Z" fill="url(#v1-wake-l)" />
          <path d="M0,0 L3,-1.9 L11.5,-1.9 L11.5,1.6 L3,1.6 Z" fill="#fff" />
          <rect x="5" y="-3.7" width="4.2" height="1.9" rx="0.5" fill="#eef1f4" />
        </g>
      </g>
      <g className="v1-boat is-east">
        {/* heading east, bow on the right, wake trailing west */}
        <g transform="translate(0 394)">
          <path d="M0,-0.8 L-58,-4 L-58,4 L0,0.8 Z" fill="url(#v1-wake-r)" />
          <path d="M0,-2.1 L10,-2.1 L13.5,0 L10,1.8 L0,1.8 Z" fill="#fff" />
          <rect x="2.4" y="-4.4" width="5" height="2.3" rx="0.6" fill="#eef1f4" />
        </g>
      </g>
      <g className="v1-sail">
        <g transform="translate(232 262)">
          <path d="M0,0 L0,-11 L6.4,0 Z" fill="#fbfbfb" />
          <path d="M-0.6,0.4 L-0.6,-9 L-4,0.4 Z" fill="#eef1f4" />
          <path d="M-5,1 L8,1 L6.5,2.6 L-3.6,2.6 Z" fill="#f4f4f4" />
        </g>
      </g>

      {/* surf breathing at the foot of the cliff and round the stacks */}
      <path
        className="v1-surf"
        d="M58,498 Q100,488 148,470 Q166,462 180,450"
        stroke="#f5fbff"
        strokeWidth="2.2"
        strokeLinecap="round"
        fill="none"
      />
      <path
        className="v1-surf is-late"
        d="M164,503 Q186,508 210,505"
        stroke="#f5fbff"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
});
