import { createContext, useContext, useEffect, useRef, useState, type MutableRefObject } from "react";

/* Shared state of the hero's stage. Everything inside is laid out in stage
   pixels (STAGE_W × STAGE_H) and the whole stage is scaled to its column, so
   objects that draw to a canvas need the scale to size their backing store
   (a ResizeObserver does not fire when an ANCESTOR's transform changes). */

export const STAGE_W = 900;
export const STAGE_H = 820;

export interface Parallax {
  /** Smoothed pointer position, -1..1 from the viewport centre. */
  x: number;
  y: number;
}

export interface StageState {
  scale: number;
  /** False while the stage is scrolled out of view — loops should idle. */
  active: boolean;
  /** True when the visitor asked for reduced motion: render one still frame. */
  still: boolean;
  parallax: MutableRefObject<Parallax>;
}

export const StageContext = createContext<StageState>({
  scale: 1,
  active: true,
  still: false,
  parallax: { current: { x: 0, y: 0 } },
});

export function useStage() {
  return useContext(StageContext);
}

/**
 * A requestAnimationFrame loop that idles while the stage is off screen and
 * hands the callback elapsed seconds (clamped, so a stall or a background tab
 * never fast-forwards the scene). `fn` may change identity freely. With `fps`
 * it runs at most that often — the slow decorative motion looks the same at
 * 30 and costs half.
 */
export function useFrameLoop(fn: (t: number, dt: number) => void, enabled = true, fps?: number) {
  const { active, still } = useStage();
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const clock = useRef(0);

  useEffect(() => {
    if (!enabled) return undefined;
    if (still) {
      fnRef.current(clock.current, 0);
      return undefined;
    }
    if (!active) return undefined;
    const step = fps ? 1 / fps : 0;
    let raf = 0;
    let last = -1;
    let acc = 0;
    const tick = (now: number) => {
      raf = requestAnimationFrame(tick);
      const dt = last < 0 ? 0 : Math.min((now - last) / 1000, 0.05);
      last = now;
      acc += dt;
      if (step && acc < step - 0.002 && clock.current > 0) return;
      clock.current += acc;
      fnRef.current(clock.current, acc);
      acc = 0;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, still, enabled, fps]);
}

/**
 * Loads an image and reports it once it can be drawn: `null` while loading,
 * `false` if it failed (a missing file must not leave an empty canvas behind).
 * Waits for `load`, then gives `decode()` a chance to move decoding off the
 * main thread — but never depends on it, since decode() can reject for an
 * image that loaded perfectly well.
 */
export function useImage(src: string): HTMLImageElement | null | false {
  const [img, setImg] = useState<HTMLImageElement | null | false>(null);
  useEffect(() => {
    let alive = true;
    setImg(null);
    const el = new Image();
    el.decoding = "async";
    el.onload = () => {
      let done = false;
      const ready = () => {
        if (done) return;
        done = true;
        if (alive && el.naturalWidth > 0) setImg(el);
      };
      // decode() can stall (a hidden tab defers it), so it only gets a moment.
      if (typeof el.decode === "function") el.decode().then(ready, ready);
      window.setTimeout(ready, 400);
      if (typeof el.decode !== "function") ready();
    };
    el.onerror = () => alive && setImg(false);
    el.src = src;
    return () => {
      alive = false;
      el.onload = null;
      el.onerror = null;
    };
  }, [src]);
  return img;
}

/** Deterministic pseudo-random sequence, so generated scenery is the same on every load. */
export function seeded(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
