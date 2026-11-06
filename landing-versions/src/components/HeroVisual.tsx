import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

/**
 * Bouquet loop — a top-down bridal bouquet (navy, cornflower and cream roses)
 * whose flowers fade to new colours while petals drift off it, alpha-keyed
 * WebM, so it floats directly on the hero. Hidden when the browser can't play
 * VP9 alpha or the user prefers reduced motion.
 *
 * WHY THE BOUQUET IS PERFECTLY STILL. The source render (flowers_video.mp4)
 * zooms and morphs — nothing in it can be stabilised into a still bouquet — so
 * the asset is a composite: one clean source frame is the static bouquet,
 * individual roses are recoloured on a staggered periodic schedule (2.5s
 * smoothstep fades in Lab, 3–4 flowers in transition at any moment, every
 * rose back to its original colour by the end of the 18s loop), and the
 * source's petals are keyed out and composited under the bouquet so they still
 * leave from its rim. The colour timeline and the petal passes are both
 * periodic on the loop length, so the wrap is seamless by construction. Built
 * offline by reference/flowers-bouquet/build_flowers_bouquet.py (README there).
 */
export function HeroVisual() {
  const reduce = useReducedMotion();
  const [unsupported, setUnsupported] = useState(false);

  if (reduce || unsupported) return null;

  const src = "/flowers-bouquet.webm";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.92, y: 24 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 1.1, delay: 0.9, ease: [0.22, 1, 0.36, 1] }}
      className="relative flex items-center justify-center"
      aria-hidden
    >
      {/* soft glow behind the shape */}
      <div
        className="absolute h-[70%] w-[70%] rounded-full blur-[80px] opacity-45"
        style={{
          background:
            "radial-gradient(circle, rgba(141,161,253,0.42), rgba(195,152,120,0.24) 55%, transparent 75%)",
        }}
      />

      <motion.video
        autoPlay
        loop
        muted
        playsInline
        disablePictureInPicture
        animate={{ y: [0, -14, 0] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        className="relative w-full max-w-[540px]"
        style={{ filter: "drop-shadow(0 24px 48px rgba(34,30,23,0.22))" }}
      >
        <source src={src} type='video/webm; codecs="vp9"' onError={() => setUnsupported(true)} />
      </motion.video>
    </motion.div>
  );
}
