import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";
import { animate, useMotionValue, type AnimationPlaybackControls } from "framer-motion";
import { onLaptopWake } from "../sceneBus";
import { useStage } from "./stage";

/* ────────────────────────────────────────────────────────────────
   Two hardbacks and a laptop on top, built as real CSS 3D boxes so the
   lid can hinge: it closes, rests, and opens again with a little
   overshoot, as a lid does when it is let go. Everything that depends
   on the lid — the screen's spill on the keys, the glowing monogram on
   its back, the light sliding over the aluminium — is derived from the
   one angle, so it can never fall out of step.

   Hovering "Enter Command Center" (sceneBus) or clicking the laptop
   wakes it; the loop picks up again from open.
   ──────────────────────────────────────────────────────────────── */

const OPEN = 106; // degrees from shut
const BASE_H = 8;

/* On the terrace the lid stands as it does in the reference photograph, and
   the sun comes from behind and to the right of the camera, so shadows fall
   forward and to the left: SUN is that direction on the table, per unit of
   height (k = 1 / tan of the sun's elevation, ~60°). */
const TERRACE_OPEN = 112;
const TERRACE_BASE_H = 7;
const TERRACE_YAW = -41.5; // the laptop's turn on the table, as in the reference (and v1.css)
const SUN = { x: -0.6, y: 0.8, k: 0.58 };
const LAP_W = 292;
const LAP_D = 200;
const CAST_PAD = 320; // room round the footprint for the shadow polygons

type Pt = [number, number];

function hull(points: Pt[]): Pt[] {
  const p = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o: Pt, a: Pt, b: Pt) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lower: Pt[] = [];
  const upper: Pt[] = [];
  for (const q of p) {
    while (lower.length > 1 && cross(lower[lower.length - 2], lower[lower.length - 1], q) <= 0) lower.pop();
    lower.push(q);
  }
  for (const q of p.reverse()) {
    while (upper.length > 1 && cross(upper[upper.length - 2], upper[upper.length - 1], q) <= 0) upper.pop();
    upper.push(q);
  }
  return lower.slice(0, -1).concat(upper.slice(0, -1));
}

const polygon = (pts: Pt[]) =>
  `polygon(${hull(pts)
    .map(([x, y]) => `${(x + CAST_PAD).toFixed(1)}px ${(y + CAST_PAD).toFixed(1)}px`)
    .join(", ")})`;

/** The sun shadow on the table, in the laptop's own (turned) frame: the base
    and the lid as separate polygons, so their union keeps its notch. */
function castShadows(yaw: number, lid: number, h: number): [string, string] {
  const r = (-yaw * Math.PI) / 180;
  const dx = (SUN.x * Math.cos(r) - SUN.y * Math.sin(r)) * SUN.k;
  const dy = (SUN.x * Math.sin(r) + SUN.y * Math.cos(r)) * SUN.k;
  const fall = (x: number, y: number, z: number): Pt => [x + z * dx, y + z * dy];
  const foot: Pt[] = [
    [0, 0],
    [LAP_W, 0],
    [LAP_W, LAP_D],
    [0, LAP_D],
  ];
  const base = [...foot, ...foot.map(([x, y]) => fall(x, y, h))];
  const a = (lid * Math.PI) / 180;
  const ty = LAP_D * Math.cos(a);
  const tz = h + LAP_D * Math.sin(a);
  const top = [fall(0, 0, h), fall(LAP_W, 0, h), fall(LAP_W, ty, tz), fall(0, ty, tz)];
  return [polygon(base), polygon(top)];
}

type Faces = Partial<Record<"top" | "front" | "back" | "left" | "right", ReactNode>>;

/** A W×D×H box standing on its footprint; faces are stylable by class. */
function Box({
  w,
  d,
  h,
  className,
  style,
  faces = {},
}: {
  w: number;
  d: number;
  h: number;
  className?: string;
  style?: CSSProperties;
  faces?: Faces;
}) {
  const box = { width: w, height: d, ...style } as CSSProperties;
  return (
    <div className={`v1-box ${className ?? ""}`} style={box}>
      <div className="v1-face is-top" style={{ width: w, height: d, transform: `translateZ(${h}px)` }}>
        {faces.top}
      </div>
      <div
        className="v1-face is-front"
        style={{ top: d, width: w, height: h, transformOrigin: "50% 0", transform: `translateZ(${h}px) rotateX(-90deg)` }}
      >
        {faces.front}
      </div>
      <div
        className="v1-face is-back"
        style={{ top: -h, width: w, height: h, transformOrigin: "50% 100%", transform: `translateZ(${h}px) rotateX(90deg)` }}
      >
        {faces.back}
      </div>
      <div
        className="v1-face is-left"
        style={{ left: -h, width: h, height: d, transformOrigin: "100% 50%", transform: `translateZ(${h}px) rotateY(-90deg)` }}
      >
        {faces.left}
      </div>
      <div
        className="v1-face is-right"
        style={{ left: w, width: h, height: d, transformOrigin: "0 50%", transform: `translateZ(${h}px) rotateY(90deg)` }}
      >
        {faces.right}
      </div>
    </div>
  );
}

const KEYS = Array.from({ length: 6 * 14 });
const KEY_ROWS = [
  ["esc", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12", ""],
  ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "delete"],
  ["tab", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]", "\\"],
  ["caps", "A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'", "return"],
  ["shift", "Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "shift"],
  ["fn", "ctrl", "opt", "cmd", " ", "cmd", "opt", "<", "^", ">"],
];

export function Desk({ showBooks = true, terrace = false }: { showBooks?: boolean; terrace?: boolean }) {
  const { active, still } = useStage();
  const OPEN_AT = terrace ? TERRACE_OPEN : OPEN;
  const phi = useMotionValue(OPEN_AT);
  const baseHeight = terrace ? TERRACE_BASE_H : BASE_H;
  const lidRef = useRef<HTMLDivElement>(null);
  const deskRef = useRef<HTMLDivElement>(null);
  const baseCastRef = useRef<HTMLElement>(null);
  const lidCastRef = useRef<HTMLElement>(null);
  const runRef = useRef<(mode: "start" | "wake" | "close") => void>(() => {});

  /* Everything that follows the lid; on the terrace that includes the
     shadows, re-projected as the lid moves. */
  useEffect(() => {
    const apply = () => {
      const v = phi.get();
      const lid = lidRef.current;
      const desk = deskRef.current;
      if (!lid || !desk) return;
      lid.style.transform = `translateZ(${baseHeight + 0.6}px) rotateX(${v.toFixed(2)}deg)`;
      const open = Math.min(1, Math.max(0, v / OPEN_AT));
      const lit = Math.min(1, Math.max(0, (v - 38) / (OPEN_AT - 38)));
      desk.style.setProperty("--open", open.toFixed(3));
      desk.style.setProperty("--lit", (lit * lit * (3 - 2 * lit)).toFixed(3));
      if (terrace) {
        const [base, top] = castShadows(TERRACE_YAW, Math.max(0, v), baseHeight);
        if (baseCastRef.current) baseCastRef.current.style.clipPath = base;
        if (lidCastRef.current) lidCastRef.current.style.clipPath = top;
      }
    };
    apply();
    return phi.on("change", apply);
  }, [phi, baseHeight, terrace, OPEN_AT]);

  /* The loop: hold open, close, rest, spring open. A wake (or a click) kills
     the running loop and starts a new one from open. */
  useEffect(() => {
    if (still) {
      phi.set(OPEN_AT);
      return undefined;
    }
    if (!active) return undefined;

    let token = 0;
    let current: AnimationPlaybackControls | null = null;
    const timers = new Set<number>();
    const sleep = (ms: number) =>
      new Promise<void>((resolve) => {
        const id = window.setTimeout(() => {
          timers.delete(id);
          resolve();
        }, ms);
        timers.add(id);
      });
    const to = (v: number, open: boolean) => {
      current?.stop();
      current = open
        ? animate(phi, v, { type: "spring", stiffness: 34, damping: 7.6, mass: 1.15, restDelta: 0.05 })
        : animate(phi, v, { duration: 1.8, ease: [0.62, 0.02, 0.3, 1] });
      return new Promise<void>((resolve) => {
        current!.then(resolve, resolve);
      });
    };

    /* One loop at a time: each run takes a token, and starting another
       retires the previous one at its next await. */
    const run = async (mode: "start" | "wake" | "close") => {
      const mine = ++token;
      const alive = () => mine === token;
      if (mode === "close") {
        await to(0, false);
        if (!alive()) return;
        await sleep(2600);
        if (!alive()) return;
        await to(OPEN_AT, true);
      } else if (phi.get() < OPEN_AT - 1) {
        await to(OPEN_AT, true);
      }
      if (!alive()) return;
      await sleep(terrace ? 10000 : mode === "start" ? 3600 : 6400);
      while (alive()) {
        await to(0, false);
        if (!alive()) return;
        await sleep(2000);
        if (!alive()) return;
        await to(OPEN_AT, true);
        if (!alive()) return;
        await sleep(terrace ? 14000 : 6400);
      }
    };

    runRef.current = (mode) => void run(mode);
    void run("start");
    const off = onLaptopWake(() => void run("wake"));

    return () => {
      token++;
      runRef.current = () => {};
      current?.stop();
      timers.forEach((id) => window.clearTimeout(id));
      off();
    };
  }, [active, still, phi, terrace, OPEN_AT]);

  const toggle = () => runRef.current(phi.get() > OPEN_AT / 2 ? "close" : "wake");

  return (
    <div ref={deskRef} className={`v1-desk${terrace ? " is-on-terrace" : showBooks ? "" : " is-on-scene-books"}`} aria-hidden>
      <div className="v1-desk-shadow" />
      <div className="v1-desk-cam">
        <div className="v1-desk-world">
          {showBooks ? (
            <>
              <div className="v1-book-shadow" />
              <Box
                w={336}
                d={246}
                h={26}
                className="v1-book is-lower"
                faces={{
                  top: <span className="v1-cover" />,
                  front: (
                    <span className="v1-spine">
                      <span className="v1-spine-rule" />
                      The Wedding Industry
                      <span className="v1-spine-rule" />
                    </span>
                  ),
                  right: <span className="v1-pages" />,
                  left: <span className="v1-pages" />,
                  back: <span className="v1-pages" />,
                }}
              />
              <Box
                w={316}
                d={232}
                h={19}
                className="v1-book is-upper"
                faces={{
                  top: (
                    <span className="v1-cover is-upper">
                      <span className="v1-cover-foil">WIA · Playbook</span>
                    </span>
                  ),
                  front: <span className="v1-spine is-quiet">Command Center · Vol. II</span>,
                  right: <span className="v1-pages" />,
                  left: <span className="v1-pages" />,
                  back: <span className="v1-pages" />,
                }}
              />
            </>
          ) : null}

          <div className="v1-laptop" onClick={toggle} title="Open or close the laptop">
            {terrace && (
              <>
                {/* Sun shadow, the soft occlusion round the footprint, the
                    dark line where the aluminium meets the stone, and the
                    marble's reflection of the near sides. */}
                <span className="v1-lap-cast">
                  <i ref={baseCastRef} />
                  <i ref={lidCastRef} />
                </span>
                <span className="v1-lap-occlusion" />
                <span className="v1-lap-contact" />
                <Box
                  w={LAP_W}
                  d={LAP_D}
                  h={baseHeight}
                  className="v1-lap-mirror"
                  style={{ transform: `translateZ(${-baseHeight}px)` }}
                  faces={{ front: <span />, left: <span /> }}
                />
              </>
            )}
            <Box
              w={292}
              d={200}
              h={baseHeight}
              className="v1-base"
              faces={{
                top: (
                  <span className="v1-deck">
                    <span className="v1-keys">
                      {terrace ? KEY_ROWS.map((row, rowIndex) => (
                        <span className={`v1-key-row is-row-${rowIndex}`} key={rowIndex}>
                          {row.map((label, index) => <span key={index} className={`v1-key${label === " " ? " is-space" : ""}`}><span>{label}</span></span>)}
                        </span>
                      )) : KEYS.map((_, i) => (
                        <span key={i} className="v1-key" />
                      ))}
                    </span>
                    {terrace && <span className="v1-hinge-bar" />}
                    <span className="v1-trackpad" />
                    <span className="v1-spill" />
                  </span>
                ),
                front: <span className="v1-edge is-front" />,
                back: <span className="v1-edge" />,
                left: (
                  <span className="v1-edge is-ports">
                    <i />
                    <i />
                    <i />
                  </span>
                ),
                right: <span className="v1-edge" />,
              }}
            />
            <div ref={lidRef} className="v1-lid">
              <Box
                w={292}
                d={200}
                h={terrace ? 3.6 : 4.5}
                className="v1-lid-box"
                faces={{
                  top: (
                    <span className="v1-lid-outer">
                      <span className="v1-lid-logo">
                        <svg viewBox="0 0 64 64">
                          <circle cx="32" cy="32" r="29" fill="none" stroke="currentColor" strokeWidth="1.6" />
                          <text x="32" y="33" textAnchor="middle" dominantBaseline="central" fill="currentColor">
                            WIA
                          </text>
                        </svg>
                      </span>
                      <span className="v1-lid-sheen" />
                    </span>
                  ),
                  front: <span className="v1-edge is-lid" />,
                  back: <span className="v1-edge is-lid" />,
                  left: <span className="v1-edge is-lid" />,
                  right: <span className="v1-edge is-lid" />,
                }}
              />
              <div className="v1-screen">
                {terrace && <><span className="v1-webcam" /><span className="v1-screen-wordmark">WIA</span></>}
                {terrace ? <LaptopDashboard /> : <span className="v1-screen-ui">
                  <i />
                  <i />
                  <i />
                </span>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function LaptopDashboard() {
  return (
    <div className="v1-laptop-dashboard">
      <div className="v1-dashboard-rail"><b>WIA</b><span /><span /><span /><span /><span /></div>
      <div className="v1-dashboard-content">
        <header><span>COMMAND CENTER</span><span className="v1-dashboard-avatar">W</span></header>
        <p>Business overview</p>
        <div className="v1-dashboard-tabs"><span>Overview</span><span>Campaigns</span><span>Clients</span></div>
        <div className="v1-dashboard-chart">
          <span>Performance</span><strong>Growing together</strong>
          <svg viewBox="0 0 230 100" fill="none" aria-hidden>
            <defs><linearGradient id="terrace-chart-fill" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#396dff" stopOpacity=".2" /><stop offset="1" stopColor="#396dff" stopOpacity="0" /></linearGradient></defs>
            <path d="M5 90H225M5 65H225M5 40H225M5 15H225" stroke="#e9edf4" strokeWidth="1" />
            <path d="M5 88 25 82 45 85 65 63 85 68 105 48 125 53 145 35 165 43 185 24 205 28 225 7V98H5Z" fill="url(#terrace-chart-fill)" />
            <path d="m5 88 20-6 20 3 20-22 20 5 20-20 20 5 20-18 20 8 20-19 20 4 20-21" stroke="#396dff" strokeWidth="2" strokeLinejoin="round" />
          </svg>
        </div>
        <div className="v1-dashboard-metrics"><span>Campaigns<b>04</b></span><span>Automations<b>29</b></span><span>Connected<b>All systems</b></span></div>
      </div>
    </div>
  );
}
