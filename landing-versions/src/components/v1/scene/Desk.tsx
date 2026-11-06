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

export function Desk({ showBooks = true }: { showBooks?: boolean }) {
  const { active, still } = useStage();
  const phi = useMotionValue(OPEN);
  const lidRef = useRef<HTMLDivElement>(null);
  const deskRef = useRef<HTMLDivElement>(null);
  const runRef = useRef<(mode: "start" | "wake" | "close") => void>(() => {});

  /* Everything that follows the lid. */
  useEffect(() => {
    const apply = (v: number) => {
      const lid = lidRef.current;
      const desk = deskRef.current;
      if (!lid || !desk) return;
      lid.style.transform = `translateZ(${BASE_H + 0.6}px) rotateX(${v.toFixed(2)}deg)`;
      const open = Math.min(1, Math.max(0, v / OPEN));
      const lit = Math.min(1, Math.max(0, (v - 38) / (OPEN - 38)));
      desk.style.setProperty("--open", open.toFixed(3));
      desk.style.setProperty("--lit", (lit * lit * (3 - 2 * lit)).toFixed(3));
    };
    apply(phi.get());
    return phi.on("change", apply);
  }, [phi]);

  /* The loop: hold open, close, rest, spring open. A wake (or a click) kills
     the running loop and starts a new one from open. */
  useEffect(() => {
    if (still) {
      phi.set(OPEN);
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
        await to(OPEN, true);
      } else if (phi.get() < OPEN - 1) {
        await to(OPEN, true);
      }
      if (!alive()) return;
      await sleep(mode === "start" ? 3600 : 6400);
      while (alive()) {
        await to(0, false);
        if (!alive()) return;
        await sleep(2000);
        if (!alive()) return;
        await to(OPEN, true);
        if (!alive()) return;
        await sleep(6400);
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
  }, [active, still, phi]);

  const toggle = () => runRef.current(phi.get() > OPEN / 2 ? "close" : "wake");

  return (
    <div ref={deskRef} className={`v1-desk${showBooks ? "" : " is-on-scene-books"}`} aria-hidden>
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
            <Box
              w={292}
              d={200}
              h={BASE_H}
              className="v1-base"
              faces={{
                top: (
                  <span className="v1-deck">
                    <span className="v1-keys">
                      {KEYS.map((_, i) => (
                        <span key={i} className="v1-key" />
                      ))}
                    </span>
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
                h={4.5}
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
                <span className="v1-screen-ui">
                  <i />
                  <i />
                  <i />
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
