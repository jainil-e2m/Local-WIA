import { useSyncExternalStore } from "react";

/* ────────────────────────────────────────────────────────────────
   Frame-budget guard for the decorative loops.

   The scene's sway and steam are the expensive part on a machine without
   GPU compositing (software WebGL can take 100ms a frame). If frames stay
   slow for a couple of seconds, those loops stand down and hold their last
   frame, so the page's own animations and the orbit keep the main thread.
   One-way for the visit: flapping between modes would read as stutter.
   ──────────────────────────────────────────────────────────────── */

let low = false;
const listeners = new Set<() => void>();

export function markLowPower() {
  if (low) return;
  low = true;
  listeners.forEach((fn) => fn());
}

export function useLowPower(): boolean {
  return useSyncExternalStore(
    (fn) => {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    () => low,
    () => false,
  );
}

/** Feed frame deltas (ms); trips the guard after sustained slow frames. */
export function createFrameWatch(limitMs = 50, forMs = 2500) {
  let ema = 16;
  let slowFor = 0;
  return (dtMs: number) => {
    const dt = Math.min(dtMs, 120); // a resumed tab's first gap is not a slow frame
    ema = ema * 0.9 + dt * 0.1;
    slowFor = ema > limitMs ? slowFor + dt : 0;
    if (slowFor > forMs) markLowPower();
  };
}
