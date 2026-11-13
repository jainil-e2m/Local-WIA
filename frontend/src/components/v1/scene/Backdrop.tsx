import { memo, useMemo } from "react";
import { CoastLive, CoastStatic } from "./Coast";
import { seeded } from "./stage";

/* ────────────────────────────────────────────────────────────────
   The wall behind the table: the arch onto the coast, a blurred band of
   sea and sky for the flowers and the steam to read against, and two
   paper cards for depth. The standing prints at the left (Frames) are a
   separate layer because they sit in front of the laptop.
   ──────────────────────────────────────────────────────────────── */

export function Backdrop() {
  return (
    <div className="v1-backdrop" aria-hidden>
      <div className="v1-sea-panel">
        <span className="v1-sea-panel-shine" />
      </div>
      <div className="v1-paper is-a" />
      <div className="v1-paper is-b" />
      <div className="v1-arch">
        <CoastStatic className="v1-arch-svg" />
        <CoastLive className="v1-arch-svg" />
        <span className="v1-arch-sheen" />
      </div>
    </div>
  );
}

export function Frames() {
  return (
    <div className="v1-frames" aria-hidden>
      <div className="v1-skystrip">
        <SkyStrip />
      </div>
      <div className="v1-print-stand">
        <Reception />
      </div>
    </div>
  );
}

/* ── Sky strip: a tall print of open sky, clouds drifting through ─ */

const SkyStrip = memo(function SkyStrip() {
  return (
    <svg viewBox="0 0 60 212" preserveAspectRatio="none" className="h-full w-full">
      <defs>
        <linearGradient id="v1-sky-strip" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#7fb0de" />
          <stop offset="0.55" stopColor="#b5d2ee" />
          <stop offset="1" stopColor="#e2eef9" />
        </linearGradient>
        <radialGradient id="v1-sky-cloud">
          <stop offset="0" stopColor="#fff" stopOpacity="0.95" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="60" height="212" fill="url(#v1-sky-strip)" />
      <g className="v1-strip-clouds">
        {[
          [10, 40, 26, 9],
          [44, 70, 30, 8],
          [-6, 118, 34, 10],
          [36, 150, 26, 7],
          [12, 192, 38, 11],
          [70, 40, 26, 9],
          [104, 70, 30, 8],
          [54, 118, 34, 10],
          [96, 150, 26, 7],
          [72, 192, 38, 11],
        ].map(([cx, cy, rx, ry], i) => (
          <ellipse key={i} cx={cx} cy={cy} rx={rx} ry={ry} fill="url(#v1-sky-cloud)" opacity={0.85} />
        ))}
      </g>
      {/* two swifts crossing now and then */}
      <g className="v1-swift">
        <path d="M0,0 q3,-2.6 6,0 q3,-2.6 6,0" stroke="#33465f" strokeWidth="0.9" fill="none" />
        <path d="M9,7 q2.2,-2 4.4,0 q2.2,-2 4.4,0" stroke="#33465f" strokeWidth="0.8" fill="none" />
      </g>
    </svg>
  );
});

/* ── Reception: a candlelit long table, flames alive ─────────────── */

const Reception = memo(function Reception() {
  const VX = 40; // vanishing point
  const VY = 70;
  const candles = useMemo(() => {
    const out: { x: number; y: number; h: number; w: number; delay: number; dur: number }[] = [];
    const rand = seeded(5);
    for (let i = 0; i < 7; i++) {
      const t = 0.12 + i * 0.13; // depth along the table, 0 = far
      const y = VY + 8 + Math.pow(t, 1.35) * 86;
      const spread = 3 + t * 18;
      for (const side of [-1, 1]) {
        out.push({
          x: VX + side * spread * 0.42,
          y,
          h: 6 + t * 26,
          w: 0.8 + t * 1.6,
          delay: -rand() * 2,
          dur: 0.9 + rand() * 0.8,
        });
      }
    }
    return out;
  }, []);

  return (
    <svg viewBox="0 0 80 166" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
      <defs>
        <linearGradient id="v1-rc-wall" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#efe5da" />
          <stop offset="0.5" stopColor="#e6d7c6" />
          <stop offset="1" stopColor="#d6c1aa" />
        </linearGradient>
        <radialGradient id="v1-rc-glow">
          <stop offset="0" stopColor="#fff3d6" stopOpacity="0.95" />
          <stop offset="1" stopColor="#fff3d6" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="v1-rc-flame">
          <stop offset="0" stopColor="#fffbea" />
          <stop offset="0.45" stopColor="#ffe08a" />
          <stop offset="1" stopColor="#ffb648" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="v1-rc-cloth" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f6f1ea" />
          <stop offset="1" stopColor="#fffdf9" />
        </linearGradient>
      </defs>
      <rect width="80" height="166" fill="url(#v1-rc-wall)" />
      {/* tall window at the end of the room */}
      <rect x="31" y="22" width="18" height="44" rx="9" fill="#f9f3ea" opacity="0.9" />
      <rect x="39.4" y="22" width="1.2" height="44" fill="#e3d4c1" />
      {/* chandeliers */}
      <circle cx="22" cy="16" r="18" fill="url(#v1-rc-glow)" opacity="0.8" />
      <circle cx="60" cy="24" r="16" fill="url(#v1-rc-glow)" opacity="0.7" />
      {[
        [18, 14],
        [22, 18],
        [26, 13],
        [57, 22],
        [61, 26],
        [64, 21],
      ].map(([x, y], i) => (
        <circle key={i} className="v1-sparkle" cx={x} cy={y} r="0.8" fill="#fff" style={{ animationDelay: `${-i * 0.7}s` }} />
      ))}
      {/* chairs along both sides */}
      {Array.from({ length: 6 }, (_, i) => {
        const t = 0.15 + i * 0.16;
        const y = VY + 6 + Math.pow(t, 1.35) * 86;
        const s = 0.35 + t;
        return [-1, 1].map((side) => (
          <rect
            key={`${i}${side}`}
            x={VX + side * (8 + t * 34) - 3 * s}
            y={y - 9 * s}
            width={6 * s}
            height={10 * s}
            rx={2.4 * s}
            fill="#fbf8f3"
            stroke="#d9cab6"
            strokeWidth={0.4}
          />
        ));
      })}
      {/* the table */}
      <path d={`M${VX - 5},${VY + 6} L${VX + 5},${VY + 6} L82,170 L-2,170 Z`} fill="url(#v1-rc-cloth)" />
      <path d={`M${VX - 5},${VY + 6} L-2,170`} stroke="#e2d6c6" strokeWidth="0.6" />
      <path d={`M${VX + 5},${VY + 6} L82,170`} stroke="#e2d6c6" strokeWidth="0.6" />
      {/* florals down the centre */}
      {Array.from({ length: 6 }, (_, i) => {
        const t = 0.18 + i * 0.15;
        const y = VY + 9 + Math.pow(t, 1.35) * 86;
        const r = 1.6 + t * 6;
        return (
          <g key={i}>
            <circle cx={VX - r * 0.6} cy={y} r={r} fill="#f3d3d4" />
            <circle cx={VX + r * 0.5} cy={y - r * 0.2} r={r * 0.9} fill="#fff6f4" />
            <circle cx={VX} cy={y - r * 0.6} r={r * 0.7} fill="#ebbcc1" />
            <circle cx={VX + r * 1.1} cy={y + r * 0.2} r={r * 0.5} fill="#a4b896" />
          </g>
        );
      })}
      {/* candles, with flames that flicker */}
      {candles.map((c, i) => (
        <g key={i}>
          <rect x={c.x - c.w / 2} y={c.y - c.h} width={c.w} height={c.h} fill="#fffdf8" />
          <g
            className="v1-flame"
            style={{
              transformOrigin: `${c.x}px ${c.y - c.h}px`,
              animationDelay: `${c.delay}s`,
              animationDuration: `${c.dur}s`,
            }}
          >
            <circle cx={c.x} cy={c.y - c.h - c.w * 1.4} r={c.w * 4.2} fill="url(#v1-rc-glow)" opacity="0.7" />
            <ellipse cx={c.x} cy={c.y - c.h - c.w * 1.2} rx={c.w * 0.8} ry={c.w * 1.6} fill="url(#v1-rc-flame)" />
          </g>
        </g>
      ))}
      {/* warm bokeh */}
      {[
        [10, 40, 5],
        [70, 52, 6],
        [64, 10, 4],
      ].map(([x, y, r], i) => (
        <circle key={i} className="v1-bokeh" cx={x} cy={y} r={r} fill="#fff1d2" style={{ animationDelay: `${-i * 1.3}s` }} />
      ))}
    </svg>
  );
});
