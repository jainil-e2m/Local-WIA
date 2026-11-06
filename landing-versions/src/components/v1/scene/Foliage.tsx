import { useMemo, useRef } from "react";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { StageContext, type StageState } from "./stage";
import { SwayImage } from "./SwayImage";

/**
 * Out-of-focus fern and a garden rose in the bottom-left corner, as if on a
 * table nearer the camera — the depth cue the design's corner carries. Both
 * sway on the breeze. Rendered at a fraction of their on-screen resolution,
 * which is the blur and also most of the saving; they fade as the page
 * scrolls so they never drift up over the navigation.
 */
export function Foliage() {
  const reduce = useReducedMotion() ?? false;
  const parallax = useRef({ x: 0, y: 0 });
  const ctx = useMemo<StageState>(() => ({ scale: 1, active: true, still: reduce, parallax }), [reduce]);
  const { scrollY } = useScroll();
  const opacity = useTransform(scrollY, [0, 260], [1, 0]);

  return (
    <motion.div
      className="v1-foliage"
      aria-hidden
      style={{ opacity }}
      initial={{ y: 40 }}
      animate={{ y: 0 }}
      transition={{ duration: 1.6, delay: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      <StageContext.Provider value={ctx}>
        <SwayImage
          src="/variant-1/fern.webp"
          width={470}
          height={286}
          pad={40}
          pivot={[0.94, 1.08]}
          bend={0.075}
          flutter={3.2}
          speed={0.8}
          seed={4.2}
          resolution={0.34}
          className="v1-foliage-fern"
        />
      </StageContext.Provider>
    </motion.div>
  );
}
