import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { HERO_WIDE, useMatchMedia } from "@/hooks/useMatchMedia";
import { createStackedAlphaPlayer } from "./stackedAlpha";

/**
 * The landing hero's bouquet: a turning bouquet with petals falling around
 * it, keyed off its turquoise backdrop and looped (scripts/build-hero-bouquet.py).
 *
 * It fills its parent, which MarbleHero positions over the marble.
 *
 *   - The still (the loop's first frame) paints at once and stays until the
 *     video has drawn its first frame, so there is no blank moment and no
 *     jump when playback takes over.
 *   - Every edge of the asset fades to nothing before the frame border, so
 *     petals dissolve into the page rather than meeting a box.
 *   - Pauses while scrolled away or in a background tab.
 *   - Reduced motion gets the still and never downloads the video.
 *   - No WebGL, a lost context, or a refused autoplay keep the still.
 *   - Below 1100px the florals are dropped, so nothing is mounted at all.
 */

const STILL = "/landing/bouquet-still.webp";
const LOOP = "/landing/bouquet-loop.mp4";

export function BouquetVideo() {
  const wide = useMatchMedia(HERO_WIDE);
  const reduce = useReducedMotion() ?? false;
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [failed, setFailed] = useState(false);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!wide || reduce || failed || !canvas) return undefined;
    const player = createStackedAlphaPlayer(canvas);
    if (!player) {
      setFailed(true);
      return undefined;
    }

    // Kept out of the DOM: it is only a frame source for the canvas.
    const video = document.createElement("video");
    video.muted = true;
    video.defaultMuted = true;
    video.loop = true;
    video.playsInline = true;
    video.setAttribute("muted", "");
    video.setAttribute("playsinline", "");
    video.preload = "auto";
    video.src = LOOP;

    let stopped = false;
    let drawn = false;
    let onScreen = true;
    let raf = 0;
    let frameCb = 0;

    const paint = () => {
      if (stopped || video.readyState < 2) return;
      player.draw(video);
      if (!drawn) {
        drawn = true;
        setPlaying(true);
      }
    };
    // Draw once per decoded frame where the browser can say when that is;
    // otherwise once per display frame.
    const perFrame = typeof video.requestVideoFrameCallback === "function";
    const onVideoFrame = () => {
      paint();
      if (!stopped) frameCb = video.requestVideoFrameCallback(onVideoFrame);
    };
    const onAnimationFrame = () => {
      paint();
      if (!stopped) raf = requestAnimationFrame(onAnimationFrame);
    };
    if (perFrame) frameCb = video.requestVideoFrameCallback(onVideoFrame);
    else raf = requestAnimationFrame(onAnimationFrame);

    const sync = () => {
      if (onScreen && !document.hidden) {
        video.play().catch(() => {
          /* autoplay refused: the still stays up */
        });
      } else {
        video.pause();
      }
    };
    const measure = () => {
      // Layout size, not getBoundingClientRect: the wrapper's entrance
      // animation scales it, and a transform never fires the observer again.
      player.resize(canvas.clientWidth, canvas.clientHeight, window.devicePixelRatio || 1);
      paint();
    };

    const io = new IntersectionObserver(([entry]) => {
      onScreen = entry.isIntersecting;
      sync();
    });
    io.observe(canvas);
    const ro = new ResizeObserver(measure);
    ro.observe(canvas);
    document.addEventListener("visibilitychange", sync);
    const fail = () => setFailed(true);
    video.addEventListener("error", fail);
    canvas.addEventListener("webglcontextlost", fail);

    measure();
    sync();

    return () => {
      stopped = true;
      cancelAnimationFrame(raf);
      if (perFrame && frameCb) video.cancelVideoFrameCallback(frameCb);
      io.disconnect();
      ro.disconnect();
      document.removeEventListener("visibilitychange", sync);
      video.removeEventListener("error", fail);
      canvas.removeEventListener("webglcontextlost", fail);
      video.pause();
      video.removeAttribute("src");
      video.load(); // releases the decoder
      player.dispose();
    };
  }, [wide, reduce, failed]);

  if (!wide) return null;
  const live = !reduce && !failed;

  return (
    <>
      <img
        src={STILL}
        alt=""
        decoding="async"
        className="landing-bouquet-layer"
        style={{ opacity: live && playing ? 0 : 1 }}
      />
      {live && (
        <canvas
          ref={canvasRef}
          className="landing-bouquet-layer"
          style={{ opacity: playing ? 1 : 0 }}
        />
      )}
    </>
  );
}
