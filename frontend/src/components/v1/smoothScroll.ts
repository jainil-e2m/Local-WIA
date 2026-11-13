import { useEffect } from "react";
import Lenis from "lenis";

/* ────────────────────────────────────────────────────────────────
   Inertial scrolling for the landing, and only the landing: it is made
   when V1Landing mounts and destroyed when it leaves, so the consoles
   keep plain native scroll.

   Not for touch (phones already have momentum) or reduced motion. Wheel
   events inside a dialog, or anything marked data-lenis-prevent, scroll
   natively; while an overlay is open the page itself holds still.
   ──────────────────────────────────────────────────────────────── */

let current: Lenis | null = null;

export function useSmoothScroll(paused: boolean) {
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    if (window.matchMedia("(prefers-reduced-motion: reduce), (pointer: coarse)").matches) return undefined;
    const lenis = new Lenis({
      autoRaf: true,
      lerp: 0.085,
      wheelMultiplier: 0.9,
      prevent: (node) => !!node.closest?.('[role="dialog"], [data-lenis-prevent]'),
    });
    current = lenis;
    return () => {
      lenis.destroy();
      if (current === lenis) current = null;
    };
  }, []);

  useEffect(() => {
    if (!current) return;
    if (paused) current.stop();
    else current.start();
  }, [paused]);
}

/** Glide to a page offset or an element: through Lenis when it is running,
    natively otherwise. */
export function smoothScrollTo(target: number | HTMLElement, { offset = 0 }: { offset?: number } = {}) {
  if (current) {
    current.scrollTo(target, { offset, duration: 1.5, easing: (t) => 1 - Math.pow(1 - t, 4) });
    return;
  }
  const top = typeof target === "number" ? target : target.getBoundingClientRect().top + window.scrollY;
  window.scrollTo({ top: top + offset, behavior: "smooth" });
}
