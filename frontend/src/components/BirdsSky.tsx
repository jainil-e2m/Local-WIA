import { useReducedMotion } from "framer-motion";

/**
 * Full-bleed sky loop behind the hero — the DEFAULT landing background.
 *
 * A bare `/` renders this. `?variant=gradient` opts back into the original
 * gradient/grid/orb hero, which is kept in Hero.tsx as the fallback.
 *
 * WHAT THE ASSET IS. Not the source clip as delivered. That clip opened on a
 * screenshot of a video player (play button, REC dot) morphing from white
 * doves, peaked at 10–12 birds, carried an AI watermark in the corner, and its
 * first and last frames had nothing in common. This loop is re-composited:
 * the clouds are a median plate of the whole clip (so they are cleaner than
 * any single source frame), the watermark is patched out, and 3–4 real bird
 * flights harvested from the clip are re-timed so the loop wraps mid-flight.
 * The seam is therefore a normal frame step, not a crossfade.
 *
 * WHY object-cover. The loop is 16:9 at 1280×720; the hero is 100svh. Cover
 * crops the cloud edges on tall viewports and keeps the birds (centre) intact.
 *
 * REDUCED MOTION shows the poster only — a still sky with birds in it — rather
 * than nothing, because the hero would otherwise fall back to the gradient and
 * the variant would silently disappear for those users.
 */
export function BirdsSky() {
  const reduce = useReducedMotion();

  return (
    <div className="absolute inset-0" aria-hidden>
      {reduce ? (
        <img
          src="/birds-hero-poster.jpg"
          alt=""
          className="h-full w-full object-cover"
          decoding="async"
        />
      ) : (
        <video
          autoPlay
          loop
          muted
          playsInline
          preload="auto"
          disablePictureInPicture
          poster="/birds-hero-poster.jpg"
          className="h-full w-full object-cover"
        >
          <source src="/birds-hero.webm" type="video/webm" />
          <source src="/birds-hero.mp4" type="video/mp4" />
        </video>
      )}
      {/* Faint lift under the copy column so ink stays comfortably readable
          where the top-left cloud runs behind the headline. Kept very light:
          the clouds are the point of the variant. */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(900px 520px at 22% 42%, rgba(255,255,255,0.42), transparent 70%)",
        }}
      />
    </div>
  );
}
