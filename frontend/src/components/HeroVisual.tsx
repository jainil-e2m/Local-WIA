import { motion, useReducedMotion } from "framer-motion";

/**
 * The supplied bouquet clip is cropped to 0.0–6.8s, foreground-matted and
 * encoded as a VP9-alpha WebM. Its final four frames ease into its opening
 * phase, so the browser loop restart reads as continuous movement.
 */
export function HeroVisual() {
  const reduce = useReducedMotion();

  if (reduce) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.92, y: 24 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 1.1, delay: 0.9, ease: [0.22, 1, 0.36, 1] }}
      className="relative -mr-[19vw] flex h-[min(72svh,720px)] min-h-[560px] items-center justify-end"
      aria-hidden
    >
      <motion.video
        autoPlay
        loop
        muted
        playsInline
        disablePictureInPicture
        preload="auto"
        animate={{ y: [0, -10, 0] }}
        transition={{ duration: 6.8, repeat: Infinity, ease: "easeInOut" }}
        className="relative w-[min(74vw,1040px)] max-w-none"
        style={{ filter: "drop-shadow(0 30px 34px rgba(39,51,85,0.2))" }}
      >
        <source src="/wedding-bouquet-alpha.webm" type='video/webm; codecs="vp9"' />
      </motion.video>
    </motion.div>
  );
}
