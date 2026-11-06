import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { HERO_WIDE, useMatchMedia } from "@/hooks/useMatchMedia";
import { createMarbleRenderer } from "./renderer";

/**
 * The landing hero's marble, alive: cobalt veins draw themselves across the
 * stone, settle, sink back and fade, and each cycle different veins form.
 * Rendered with WebGL (see shaders.ts for how the veins live and die).
 *
 * It fills its parent, which MarbleHero pins to the right-hand region of the
 * hero; the stone dissolves in from that region's left edge and never crosses
 * it. Below 1100px the copy spans the whole width, so there is no region to
 * fill and nothing is mounted — not even a WebGL context.
 *
 *   - Starts mid-cycle, so the page opens with veins already in flight.
 *   - Runs at 30fps: the motion is slow, and half the frames is half the GPU.
 *   - Pauses while scrolled out of view or in a background tab, and resumes
 *     from where it stopped rather than jumping ahead.
 *   - Reduced motion gets one still frame.
 *   - No WebGL (or a lost context) falls back to the still render the offline
 *     script produced.
 */

const START_T = 9;
const FRAME_S = 1 / 30;

export function MarbleVeins() {
  const wide = useMatchMedia(HERO_WIDE);
  const reduce = useReducedMotion() ?? false;
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [failed, setFailed] = useState(false);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!wide || failed || !canvas) return undefined;
    const renderer = createMarbleRenderer(canvas);
    if (!renderer) {
      setFailed(true);
      return undefined;
    }

    let raf = 0;
    let last = -1;
    let since = Infinity; // seconds since the last composite
    let t = START_T;
    let drawn = false;
    let onScreen = true;
    let stopped = false;

    const measure = () => {
      const { width, height } = canvas.getBoundingClientRect();
      renderer.resize(width, height, window.devicePixelRatio || 1);
    };

    const tick = (now: number) => {
      raf = 0;
      if (stopped) return;
      // Clamped, so a stall or a background tab never fast-forwards the veins.
      const dt = last < 0 ? 0 : Math.min((now - last) / 1000, 0.1);
      last = now;
      if (!reduce) t += dt;
      since += dt;

      const baking = renderer.baking();
      if (baking || !drawn || since >= FRAME_S - 0.004) {
        if (renderer.frame(t)) {
          since = 0;
          if (!drawn) {
            drawn = true;
            setShown(true);
          }
        }
      }

      const settled = drawn && !renderer.baking();
      if (reduce && settled) return; // the one still frame is up
      if (onScreen) raf = requestAnimationFrame(tick);
    };

    const kick = () => {
      if (!raf && !stopped) {
        last = -1;
        raf = requestAnimationFrame(tick);
      }
    };

    measure();
    kick();

    let resizeTimer = 0;
    const ro = new ResizeObserver(() => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => {
        measure();
        kick();
      }, 150);
    });
    ro.observe(canvas);

    const io = new IntersectionObserver(([entry]) => {
      onScreen = entry.isIntersecting;
      if (onScreen) kick();
    });
    io.observe(canvas);

    const onLost = (e: Event) => {
      e.preventDefault();
      setFailed(true);
    };
    canvas.addEventListener("webglcontextlost", onLost);

    return () => {
      stopped = true;
      cancelAnimationFrame(raf);
      window.clearTimeout(resizeTimer);
      ro.disconnect();
      io.disconnect();
      canvas.removeEventListener("webglcontextlost", onLost);
      renderer.dispose();
    };
  }, [wide, reduce, failed]);

  if (!wide) return null;

  if (failed) {
    return (
      <img src="/landing/marble-a.webp" alt="" decoding="async" className="landing-marble-still" />
    );
  }

  return (
    <canvas ref={canvasRef} className="landing-marble-canvas" style={{ opacity: shown ? 1 : 0 }} />
  );
}
