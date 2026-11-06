import { useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { StageContext, STAGE_H, STAGE_W, type Parallax, type StageState } from "./stage";
import { OrbitCards, OrbitRings, ORBIT_BOUNDS, type OrbitClock } from "./Orbit";
import { FlowerVideo } from "./FlowerVideo";
import { Desk } from "./Desk";
import { SceneBackground } from "./SceneBackground";

/* ────────────────────────────────────────────────────────────────
   The still life on the right of the hero.

   Laid out in a fixed 900×820 stage (stage px) and scaled to fit its
   column, so the composition holds its proportions at every width. Layers
   are painted back to front — backdrop, gold rings, the table and what is
   on it, then the cards. Their positions stay fixed as the pointer moves.
   ──────────────────────────────────────────────────────────────── */

const NARROW = "(max-width: 1099px)";
const MAX_SCALE = 1.12;
const SCENE_SCALE = 0.92;
const SCENE_W = Math.max(STAGE_W, ORBIT_BOUNDS.width);
const SCENE_H = Math.max(STAGE_H, ORBIT_BOUNDS.height);

function layer(depth: number, z: number): CSSProperties {
  return { ["--d" as string]: depth, zIndex: z } as CSSProperties;
}

export function HeroScene() {
  const reduce = useReducedMotion() ?? false;
  const colRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.8);
  const [narrow, setNarrow] = useState(false);
  const [active, setActive] = useState(true);
  const parallax = useRef<Parallax>({ x: 0, y: 0 });
  const clock = useRef<OrbitClock>({ turn: 0, speed: 1, holds: 0 });

  /* Fit the stage to its column. Wide: the whole column, both axes. Narrow
     (stacked under the copy): width only, and the column takes the height. */
  useLayoutEffect(() => {
    const col = colRef.current;
    if (!col) return undefined;
    const mql = window.matchMedia(NARROW);
    const fit = () => {
      const isNarrow = mql.matches;
      setNarrow(isNarrow);
      const { width, height } = col.getBoundingClientRect();
      const s = isNarrow
        ? Math.min(width / SCENE_W, 1)
        : Math.min(width / SCENE_W, (height - 24) / SCENE_H, MAX_SCALE);
      setScale(Math.max(0.3, Math.round(s * SCENE_SCALE * 1000) / 1000));
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(col);
    mql.addEventListener("change", fit);
    return () => {
      ro.disconnect();
      mql.removeEventListener("change", fit);
    };
  }, []);

  /* Idle every loop in the scene while it is scrolled away. */
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return undefined;
    const io = new IntersectionObserver(([e]) => setActive(e.isIntersecting), { threshold: 0.02 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const ctx = useMemo<StageState>(
    () => ({ scale, active, still: reduce, parallax }),
    [scale, active, reduce],
  );

  return (
    <div
      ref={colRef}
      className="v1-scene-col"
      style={narrow ? { height: SCENE_H * scale } : undefined}
      aria-hidden
    >
      <StageContext.Provider value={ctx}>
        <div
          ref={stageRef}
          className="v1-stage"
          style={{
            transform: narrow
              ? `translateX(-50%) scale(${scale})`
              : `translate(-50%, -50%) scale(${scale})`,
          }}
        >
          <motion.div
            className="v1-layer"
            style={layer(6, 1)}
            initial={{ opacity: 0, scale: 0.985 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1.6, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          >
            <SceneBackground />
          </motion.div>

          <div className="v1-layer" style={layer(9, 2)}>
            <OrbitRings clock={clock} />
          </div>

          <div className="v1-layer" style={layer(14, 4)}>
            <FlowerVideo />
          </div>

          <div className="v1-layer" style={layer(6, 6)}>
            <Desk showBooks={false} />
          </div>

          <div className="v1-layer" style={{ zIndex: 10 }}>
            <OrbitCards clock={clock} />
          </div>
        </div>
      </StageContext.Provider>
    </div>
  );
}
