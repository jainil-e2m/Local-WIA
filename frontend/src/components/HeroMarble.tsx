import { useMemo } from "react";
import { motion, useReducedMotion } from "framer-motion";

type Vein = {
  delay: number;
  duration: number;
  opacity: number;
  rotation: number;
  scale: number;
  x: string;
  y: string;
};

export function HeroMarble() {
  const reduce = useReducedMotion();
  const veins = useMemo<Vein[]>(
    () =>
      Array.from({ length: 6 }, (_, index) => ({
        delay: -index * 4.3,
        duration: 22 + index * 3.7,
        opacity: 0.52 - index * 0.035,
        rotation: -18 + index * 17,
        scale: 0.72 + (index % 3) * 0.16,
        x: `${-18 + ((index * 29) % 104)}%`,
        y: `${-10 + ((index * 31) % 104)}%`,
      })),
    [],
  );

  return (
    <div className="hero-marble pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      {veins.map((vein, index) => (
        <motion.span
          key={index}
          className="hero-marble__vein"
          style={{
            left: vein.x,
            top: vein.y,
            opacity: vein.opacity,
            rotate: vein.rotation,
            scale: vein.scale,
          }}
          animate={
            reduce
              ? undefined
              : {
                  x: ["-7%", "7%", "-3%", "-7%"],
                  y: ["-4%", "5%", "-2%", "-4%"],
                  rotate: [vein.rotation, vein.rotation + 3, vein.rotation - 2, vein.rotation],
                  scale: [vein.scale * 0.98, vein.scale * 1.04, vein.scale, vein.scale * 0.98],
                  opacity: [0, vein.opacity, vein.opacity * 0.72, 0],
                }
          }
          transition={{ duration: vein.duration, delay: vein.delay, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
      <motion.div
        className="hero-marble__sheen"
        animate={reduce ? undefined : { opacity: [0.12, 0.3, 0.12], x: ["-4%", "5%", "-4%"] }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}
