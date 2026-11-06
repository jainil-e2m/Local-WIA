import { useCallback, useEffect, useRef, useState } from "react";

/* ────────────────────────────────────────────────────────────────
   Right-edge reveal for the bookmarks island, with the two open
   modes a peeking dock needs:

     "peek"   — revealed by parking the cursor at the right edge;
                auto-dismisses once the cursor moves away
     "pinned" — opened deliberately (header button, or any click
                inside the island); stays until it is closed

   Distances use documentElement.clientWidth, which EXCLUDES the
   scrollbar, so the trigger sits inside the layout viewport instead
   of under the scrollbar gutter. Dwell + grace delays and separate
   open/close thresholds (hysteresis) stop the panel flickering when
   the cursor brushes the edge on its way to the scrollbar.
   ──────────────────────────────────────────────────────────────── */

export type RevealMode = "closed" | "peek" | "pinned";

/** Cursor must be within this many px of the right edge to arm the reveal. */
const OPEN_WITHIN_PX = 4;
/** While peeking, staying within this band keeps it open (island is ~108px). */
const KEEP_WITHIN_PX = 150;
/** Linger time before a peek opens — a quick pass shouldn't trigger it. */
const DWELL_MS = 120;
/** Grace period before a peek closes, so crossing small gaps is forgiving. */
const GRACE_MS = 220;

export function useEdgeReveal(): {
  mode: RevealMode;
  isOpen: boolean;
  pin: () => void;
  close: () => void;
  toggle: () => void;
} {
  const [mode, setMode] = useState<RevealMode>("closed");

  // Mirrored in a ref so the pointer listener binds once and never restarts
  // its in-flight timers on a state change.
  const modeRef = useRef(mode);
  modeRef.current = mode;

  const openTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearOpen = () => {
    if (openTimer.current) clearTimeout(openTimer.current);
    openTimer.current = null;
  };
  const clearClose = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = null;
  };

  const pin = useCallback(() => {
    clearOpen();
    clearClose();
    setMode("pinned");
  }, []);

  const close = useCallback(() => {
    clearOpen();
    clearClose();
    setMode("closed");
  }, []);

  const toggle = useCallback(() => {
    clearOpen();
    clearClose();
    // Peeking counts as open, so the button closes it rather than re-opening.
    setMode((current) => (current === "closed" ? "pinned" : "closed"));
  }, []);

  useEffect(() => {
    const onMove = (event: PointerEvent) => {
      // Hover is a mouse affordance; on touch this would make the right edge a
      // dead zone that swallows taps.
      if (event.pointerType && event.pointerType !== "mouse") return;
      if (modeRef.current === "pinned") return;

      const distance = document.documentElement.clientWidth - event.clientX;

      if (distance <= OPEN_WITHIN_PX) {
        clearClose();
        if (modeRef.current === "closed" && !openTimer.current) {
          openTimer.current = setTimeout(() => {
            openTimer.current = null;
            setMode("peek");
          }, DWELL_MS);
        }
        return;
      }

      clearOpen();
      if (modeRef.current !== "peek") return;
      if (distance <= KEEP_WITHIN_PX) {
        clearClose(); // still hovering the island itself
        return;
      }
      if (!closeTimer.current) {
        closeTimer.current = setTimeout(() => {
          closeTimer.current = null;
          setMode("closed");
        }, GRACE_MS);
      }
    };

    // Leaving the document entirely (to browser chrome) also dismisses a peek —
    // pointermove stops firing there, so it would otherwise stay open.
    const onLeave = () => {
      if (modeRef.current !== "peek") return;
      clearOpen();
      if (!closeTimer.current) {
        closeTimer.current = setTimeout(() => {
          closeTimer.current = null;
          setMode("closed");
        }, GRACE_MS);
      }
    };

    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerleave", onLeave);
    return () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
      clearOpen();
      clearClose();
    };
  }, []);

  return { mode, isOpen: mode !== "closed", pin, close, toggle };
}
