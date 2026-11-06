import { motion, useReducedMotion, type Variants } from "framer-motion";

/* ────────────────────────────────────────────────────────────────
   The gold orbits beside the library's title, and the tagline among them.

   Drawn in an 864×416 frame that v1.css lays over the right of the
   header. Each line is part of a tilted ellipse fitted to the reference
   drawing (within a pixel): centre, radii and tilt in `e`, and the stretch
   of it that shows as a pair of eccentric angles in `t`. The ends fade
   out along the line, as in the drawing; the upper orbit comes in as a
   run of dots before it turns solid.
   ──────────────────────────────────────────────────────────────── */

type Ellipse = readonly [cx: number, cy: number, rx: number, ry: number, tiltDeg: number];
type Pt = readonly [number, number];

interface Orbit {
  id: string;
  e: Ellipse;
  t: readonly [number, number];
  /** Opacity at [start, fully in, fully out, end] of the line. */
  fade: readonly [number, number, number, number];
  /** Where along the line it is fully in / starts to fade out (0…1). */
  at: readonly [number, number];
  strength?: number;
}

const GOLD = "#d6ad5e";
/* The drawing's lines are fine and pale: every stop is scaled by this. */
const LINE_OPACITY = 0.6;
const UPPER: Ellipse = [481.74, -272.2, 497.47, 458.91, 5.89];

const ORBITS: readonly Orbit[] = [
  { id: "a", e: [318.53, 175.61, 288.99, 221.61, 28.89], t: [-2.9602, -5.4157], fade: [0, 1, 1, 0.15], at: [0.08, 0.86] },
  { id: "b", e: UPPER, t: [1.7901, 0.542], fade: [0, 1, 1, 1], at: [0.26, 1] },
  { id: "c", e: [465.73, -134.69, 496.58, 584.94, 73.35], t: [-0.0357, -0.6228], fade: [0, 1, 1, 1], at: [0.24, 1] },
  { id: "d", e: [561.41, -119.84, 567.08, 458.79, 113.07], t: [0.2444, -0.8288], fade: [0, 1, 1, 0], at: [0.2, 0.8], strength: 0.5 },
];
const DOTTED = { e: UPPER, t: [1.8523, 1.4392] as const };
const BEADS: readonly Pt[] = [
  [722, 133],
  [104, 280],
];

function point([cx, cy, rx, ry, deg]: Ellipse, t: number): Pt {
  const th = (deg * Math.PI) / 180;
  return [
    cx + rx * Math.cos(t) * Math.cos(th) - ry * Math.sin(t) * Math.sin(th),
    cy + rx * Math.cos(t) * Math.sin(th) + ry * Math.sin(t) * Math.cos(th),
  ];
}

function arc(e: Ellipse, [t0, t1]: readonly [number, number], steps = 96) {
  const pts = Array.from({ length: steps + 1 }, (_, i) => point(e, t0 + ((t1 - t0) * i) / steps));
  return { d: `M${pts.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join("L")}`, start: pts[0], end: pts[steps] };
}

const LINES = ORBITS.map((o) => ({ ...o, ...arc(o.e, o.t) }));
const DOTS = arc(DOTTED.e, DOTTED.t, 48);

const EASE = [0.22, 1, 0.36, 1] as const;
const draw: Variants = {
  hidden: { pathLength: 0, opacity: 0 },
  show: (i: number) => ({
    pathLength: 1,
    opacity: 1,
    transition: { pathLength: { duration: 2.2, delay: 0.2 + i * 0.18, ease: EASE }, opacity: { duration: 0.3, delay: 0.2 + i * 0.18 } },
  }),
};
const appear: Variants = {
  hidden: { opacity: 0, scale: 0.4 },
  show: (delay: number) => ({ opacity: 1, scale: 1, transition: { duration: 0.8, delay, ease: EASE } }),
};
const write: Variants = {
  hidden: { clipPath: "inset(-20% 100% -40% 0)" },
  show: (i: number) => ({ clipPath: "inset(-20% 0% -40% 0)", transition: { duration: 1.1, delay: 0.9 + i * 0.55, ease: [0.45, 0, 0.3, 1] } }),
};

/* Each line of the tagline, set along the rotated baseline: x indent and
   baseline in the rotated frame. */
const TAGLINE = [
  ["More time", 0, 0],
  ["for what", 26, 45],
  ["matters.", 56, 88],
] as const;

export function LibraryOrbits() {
  const reduce = useReducedMotion() ?? false;
  return (
    <motion.svg
      className="v1-orbits"
      viewBox="0 0 864 416"
      aria-hidden
      initial={reduce ? false : "hidden"}
      whileInView="show"
      viewport={{ once: true, amount: 0.3 }}
    >
      <defs>
        {LINES.map((l) => (
          <linearGradient
            key={l.id}
            id={`v1-orbit-${l.id}`}
            gradientUnits="userSpaceOnUse"
            x1={l.start[0]}
            y1={l.start[1]}
            x2={l.end[0]}
            y2={l.end[1]}
          >
            {([0, l.at[0], l.at[1], 1] as const).map((offset, k) => (
              <stop key={k} offset={offset} stopColor={GOLD} stopOpacity={l.fade[k] * (l.strength ?? 1) * LINE_OPACITY} />
            ))}
          </linearGradient>
        ))}
        <linearGradient id="v1-orbit-dots" gradientUnits="userSpaceOnUse" x1={DOTS.start[0]} y1={DOTS.start[1]} x2={DOTS.end[0]} y2={DOTS.end[1]}>
          <stop offset="0" stopColor={GOLD} stopOpacity="0" />
          <stop offset="1" stopColor={GOLD} stopOpacity={LINE_OPACITY} />
        </linearGradient>
        <radialGradient id="v1-orbit-bead" cx="0.36" cy="0.3" r="0.75">
          <stop offset="0" stopColor="#fdeec4" />
          <stop offset="0.45" stopColor="#dca32e" />
          <stop offset="1" stopColor="#a8761c" />
        </radialGradient>
      </defs>

      {LINES.map((l, i) => (
        <motion.path
          key={l.id}
          d={l.d}
          className="v1-orbit-line"
          stroke={`url(#v1-orbit-${l.id})`}
          custom={i}
          variants={draw}
        />
      ))}
      <motion.path d={DOTS.d} className="v1-orbit-dots" stroke="url(#v1-orbit-dots)" custom={0.6} variants={appear} />

      {BEADS.map(([x, y], i) => (
        <motion.circle
          key={x}
          cx={x}
          cy={y}
          r="6"
          className="v1-orbit-bead"
          style={{ transformOrigin: `${x}px ${y}px` }}
          custom={1.4 + i * 0.25}
          variants={appear}
        />
      ))}

      <g className="v1-orbit-tagline" transform="rotate(-17 130 160)">
        {TAGLINE.map(([words, dx, dy], i) => (
          <motion.text key={words} x={130 + dx} y={160 + dy} custom={i} variants={write}>
            {words}
          </motion.text>
        ))}
      </g>
    </motion.svg>
  );
}
