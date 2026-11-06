import { memo, useMemo, type CSSProperties } from "react";
import { SwayImage } from "./SwayImage";
import { seeded } from "./stage";

/* ────────────────────────────────────────────────────────────────
   Garden roses in a glass vase.

   The heads are the photographed bouquet (public/variant-1/bouquet.webp),
   cut above its ribbon and set into the vase so they bend in the breeze
   (SwayImage). Around it, drawn sprigs of wax flower rise high and sway
   on their own clocks, eucalyptus drapes over the rim, and the stems are
   seen through the water, broken at the surface the way refraction
   breaks them.
   ──────────────────────────────────────────────────────────────── */

const VASE = { cx: 516, rim: 452, w: 104, h: 96 };

interface Sprig {
  tip: [number, number];
  bow: number; // sideways bulge of the stem
  dur: number;
  delay: number;
  amp: number;
  blooms: number;
}

const SPRIGS: Sprig[] = [
  { tip: [446, 96], bow: -26, dur: 7.4, delay: -1.2, amp: 2.4, blooms: 7 },
  { tip: [566, 64], bow: 18, dur: 8.6, delay: -4.1, amp: 2, blooms: 8 },
  { tip: [648, 140], bow: 30, dur: 6.8, delay: -2.6, amp: 2.6, blooms: 6 },
  { tip: [404, 196], bow: -22, dur: 6.2, delay: -0.4, amp: 2.8, blooms: 5 },
  { tip: [700, 236], bow: 24, dur: 7.9, delay: -5.3, amp: 2.4, blooms: 5 },
  { tip: [506, 132], bow: -8, dur: 9.4, delay: -3.3, amp: 1.6, blooms: 6 },
];

function stemPath([x0, y0]: [number, number], [x1, y1]: [number, number], bow: number) {
  const mx = (x0 + x1) / 2 + bow;
  const my = (y0 + y1) / 2;
  return `M${x0},${y0} Q${mx},${my} ${x1},${y1}`;
}

/** Point on the quadratic stem at t. */
function along([x0, y0]: [number, number], [x1, y1]: [number, number], bow: number, t: number) {
  const mx = (x0 + x1) / 2 + bow;
  const my = (y0 + y1) / 2;
  const a = (1 - t) * (1 - t);
  const b = 2 * (1 - t) * t;
  const c = t * t;
  return [a * x0 + b * mx + c * x1, a * y0 + b * my + c * y1] as const;
}

const Sprigs = memo(function Sprigs() {
  const base: [number, number] = [VASE.cx, VASE.rim + 6];
  const parts = useMemo(
    () =>
      SPRIGS.map((s, i) => {
        const rand = seeded(60 + i);
        const leaves = Array.from({ length: 6 }, (_, k) => {
          const t = 0.25 + k * 0.1 + rand() * 0.04;
          const [x, y] = along(base, s.tip, s.bow, t);
          const side = k % 2 ? 1 : -1;
          return { x, y, r: side * (38 + rand() * 25), s: 0.8 + rand() * 0.5 };
        });
        const blooms = Array.from({ length: s.blooms }, (_, k) => {
          const t = 0.62 + (k / s.blooms) * 0.38;
          const [x, y] = along(base, s.tip, s.bow, t);
          const off = (rand() - 0.5) * 18;
          return { x: x + off, y: y + (rand() - 0.5) * 8, r: 2.2 + rand() * 2.4, bud: rand() < 0.35 };
        });
        return { leaves, blooms };
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  return (
    <svg className="v1-sprigs" viewBox="0 0 900 820" aria-hidden>
      {SPRIGS.map((s, i) => (
        <g
          key={i}
          className="v1-sprig"
          style={
            {
              transformOrigin: `${base[0]}px ${base[1]}px`,
              animationDuration: `${s.dur}s`,
              animationDelay: `${s.delay}s`,
              ["--amp"]: `${s.amp}deg`,
            } as CSSProperties
          }
        >
          <path d={stemPath(base, s.tip, s.bow)} stroke="#6f8d5b" strokeWidth="1.5" fill="none" strokeLinecap="round" />
          {parts[i].leaves.map((l, k) => (
            <ellipse
              key={k}
              cx={l.x}
              cy={l.y}
              rx={7 * l.s}
              ry={2.4 * l.s}
              fill={k % 2 ? "#7fa06a" : "#6a8a57"}
              transform={`rotate(${l.r} ${l.x} ${l.y}) translate(${l.r > 0 ? 6 : -6} 0)`}
              opacity="0.92"
            />
          ))}
          {parts[i].blooms.map((b, k) => (
            <g key={k}>
              <path
                d={stemPath(along(base, s.tip, s.bow, 0.6) as [number, number], [b.x, b.y], (b.x - s.tip[0]) * 0.2)}
                stroke="#7d9a66"
                strokeWidth="0.8"
                fill="none"
              />
              {b.bud ? (
                <circle cx={b.x} cy={b.y} r={b.r * 0.7} fill="#f6f3ea" stroke="#dcd6c6" strokeWidth="0.4" />
              ) : (
                <g transform={`translate(${b.x} ${b.y})`}>
                  {[0, 72, 144, 216, 288].map((a) => (
                    <ellipse
                      key={a}
                      cx="0"
                      cy={-b.r * 0.6}
                      rx={b.r * 0.5}
                      ry={b.r * 0.62}
                      fill="#fffdf8"
                      stroke="#e4ddcc"
                      strokeWidth="0.3"
                      transform={`rotate(${a})`}
                    />
                  ))}
                  <circle r={b.r * 0.3} fill="#e8d59a" />
                </g>
              )}
            </g>
          ))}
        </g>
      ))}
    </svg>
  );
});

/* Eucalyptus over the rim, in front of the glass. */
const Drape = memo(function Drape() {
  const stems: { d: string; leaves: [number, number, number, number][]; cls: string }[] = useMemo(() => {
    const mk = (pts: [number, number][], cls: string) => {
      const d = `M${pts[0][0]},${pts[0][1]} Q${pts[1][0]},${pts[1][1]} ${pts[2][0]},${pts[2][1]}`;
      const leaves: [number, number, number, number][] = [];
      for (let k = 1; k <= 6; k++) {
        const t = k / 6.4;
        const x = (1 - t) * (1 - t) * pts[0][0] + 2 * (1 - t) * t * pts[1][0] + t * t * pts[2][0];
        const y = (1 - t) * (1 - t) * pts[0][1] + 2 * (1 - t) * t * pts[1][1] + t * t * pts[2][1];
        leaves.push([x + (k % 2 ? 5 : -5), y + (k % 2 ? -3 : 3), 4.2 + (1 - t) * 2.4, k * 33]);
      }
      return { d, leaves, cls };
    };
    return [
      mk(
        [
          [VASE.cx - 22, VASE.rim + 2],
          [VASE.cx - 66, VASE.rim - 8],
          [VASE.cx - 96, VASE.rim + 34],
        ],
        "is-left",
      ),
      mk(
        [
          [VASE.cx + 24, VASE.rim + 2],
          [VASE.cx + 70, VASE.rim - 14],
          [VASE.cx + 104, VASE.rim + 22],
        ],
        "is-right",
      ),
    ];
  }, []);

  return (
    <svg className="v1-drape" viewBox="0 0 900 820" aria-hidden>
      {stems.map((s, i) => (
        <g key={i} className={`v1-drape-stem ${s.cls}`}>
          <path d={s.d} stroke="#71906a" strokeWidth="1.4" fill="none" />
          {s.leaves.map(([x, y, r, a], k) => (
            <ellipse
              key={k}
              cx={x}
              cy={y}
              rx={r}
              ry={r * 0.82}
              transform={`rotate(${a} ${x} ${y})`}
              fill={k % 2 ? "#9db5a0" : "#87a28c"}
              stroke="#6f8c76"
              strokeWidth="0.4"
            />
          ))}
        </g>
      ))}
    </svg>
  );
});

const Vase = memo(function Vase() {
  const stems = useMemo(() => {
    const rand = seeded(23);
    return Array.from({ length: 11 }, (_, i) => {
      const top = 12 + (i / 10) * 80 + (rand() - 0.5) * 6;
      const bottom = 38 + (i / 10) * 44 + (rand() - 0.5) * 8;
      return { top, bottom, w: 1.6 + rand() * 1.4, c: ["#7c9b61", "#6b8a53", "#8dab70"][i % 3] };
    });
  }, []);
  const W = 104;
  const H = 96;
  const water = 30; // y of the water line

  return (
    <svg className="v1-vase" viewBox={`0 0 ${W} ${H + 8}`} aria-hidden>
      <defs>
        <linearGradient id="v1-water" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#e3efe9" stopOpacity="0.5" />
          <stop offset="1" stopColor="#c7ddd2" stopOpacity="0.62" />
        </linearGradient>
        <linearGradient id="v1-glass" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.75" />
          <stop offset="0.12" stopColor="#ffffff" stopOpacity="0.1" />
          <stop offset="0.5" stopColor="#ffffff" stopOpacity="0" />
          <stop offset="0.82" stopColor="#ffffff" stopOpacity="0.14" />
          <stop offset="0.93" stopColor="#ffffff" stopOpacity="0.6" />
          <stop offset="1" stopColor="#c9d6dc" stopOpacity="0.5" />
        </linearGradient>
        <clipPath id="v1-vase-clip">
          <path d={`M4,4 L${W - 4},4 L${W - 4},${H - 6} Q${W - 4},${H + 2} ${W - 14},${H + 2} L14,${H + 2} Q4,${H + 2} 4,${H - 6} Z`} />
        </clipPath>
      </defs>
      {/* back of the glass */}
      <ellipse cx={W / 2} cy="4" rx={W / 2 - 4} ry="4.2" fill="none" stroke="#dfe8ec" strokeWidth="1" />
      <g clipPath="url(#v1-vase-clip)">
        <rect x="0" y="0" width={W} height={H + 8} fill="#eef5f7" opacity="0.28" />
        {/* stems above the water */}
        {stems.map((s, i) => (
          <path
            key={`a${i}`}
            d={`M${s.top},0 L${s.top + (s.bottom - s.top) * (water / (H - 4))},${water}`}
            stroke={s.c}
            strokeWidth={s.w}
            opacity="0.9"
          />
        ))}
        {/* water, and the stems inside it — shifted, as refraction shifts them */}
        <rect x="0" y={water} width={W} height={H} fill="url(#v1-water)" />
        {stems.map((s, i) => {
          const x0 = s.top + (s.bottom - s.top) * (water / (H - 4));
          return (
            <path
              key={`b${i}`}
              d={`M${x0 + (x0 - W / 2) * 0.08},${water} L${s.bottom + (s.bottom - W / 2) * 0.1},${H - 4}`}
              stroke={s.c}
              strokeWidth={s.w * 1.15}
              opacity="0.78"
            />
          );
        })}
        <ellipse className="v1-meniscus" cx={W / 2} cy={water} rx={W / 2 - 4} ry="3.6" fill="#f4faf7" opacity="0.7" />
        {/* front glass: highlights and a thick base */}
        <rect x="0" y="0" width={W} height={H + 8} fill="url(#v1-glass)" />
        <rect x="9" y="8" width="5" height={H - 22} rx="2.5" fill="#fff" opacity="0.55" />
        <rect x={W - 17} y="12" width="2" height={H - 30} rx="1" fill="#fff" opacity="0.5" />
        <rect x="4" y={H - 12} width={W - 8} height="14" fill="#e6f0f1" opacity="0.55" />
      </g>
      <path
        d={`M4,4 L4,${H - 6} Q4,${H + 2} 14,${H + 2} L${W - 14},${H + 2} Q${W - 4},${H + 2} ${W - 4},${H - 6} L${W - 4},4`}
        fill="none"
        stroke="#b9c8cf"
        strokeOpacity="0.7"
        strokeWidth="1"
      />
      <ellipse cx={W / 2} cy="4" rx={W / 2 - 4} ry="4.2" fill="none" stroke="#fff" strokeWidth="1.3" opacity="0.9" />
      <path d={`M10,${H - 10} Q${W / 2},${H - 4} ${W - 10},${H - 10}`} stroke="#fff" strokeWidth="1.2" fill="none" opacity="0.7" />
    </svg>
  );
});

export function Bouquet() {
  const headW = 430;
  const headH = Math.round(headW * (698 * 0.685) / 837);
  const pad = 46;
  const left = VASE.cx - 0.46 * headW;
  const top = VASE.rim + 20 - headH;

  return (
    <div className="v1-bouquet" aria-hidden>
      <Sprigs />
      <SwayImage
        src="/variant-1/bouquet.webp"
        crop={[0, 0, 1, 0.685]}
        width={headW}
        height={headH}
        pad={pad}
        pivot={[0.46, 1.1]}
        bend={0.05}
        flutter={1.7}
        speed={0.9}
        fade={[0.84, 1]}
        fadeCenter={-0.16}
        seed={1.3}
        className="v1-bouquet-head"
        style={{ left: left - pad, top: top - pad }}
      />
      <div className="v1-vase-wrap" style={{ left: VASE.cx - VASE.w / 2, top: VASE.rim - 4, width: VASE.w, height: VASE.h + 8 }}>
        <Vase />
      </div>
      <Drape />
    </div>
  );
}
