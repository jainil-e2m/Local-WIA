import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/* ────────────────────────────────────────────────────────────────
   Themed tooltip — replaces the native `title` attribute, which the
   OS renders (unstyleable, ~1s delay, invisible on touch).

   Surface matches the platform's overlay language: the navy/blur of
   ReportToast with the muted grey border used by the timeline modal,
   its chips/toggle and the automation cards.

   Rendered in a portal so it is never clipped by a scroll container
   (the gantt uses overflow:auto + contain:paint, which would cut off
   an inline tooltip).
   ──────────────────────────────────────────────────────────────── */

const SHOW_DELAY_MS = 120;
const GAP_PX = 10; // space between trigger edge and bubble (room for the caret)
const EDGE_PX = 8; // min distance from the viewport edge

type Placement = "top" | "bottom";

interface TooltipProps {
  /** Tooltip body. When empty/undefined the trigger renders with no tooltip. */
  content?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  /** Accessible text when `content` is rich markup. Defaults to the content. */
  label?: string;
  /**
   * Set false when the child is already focusable (a link or button). Focus
   * events bubble, so the tooltip still opens on keyboard focus — this just
   * avoids making the wrapper a second, redundant tab stop.
   */
  focusable?: boolean;
}

export function Tooltip({
  content,
  children,
  className,
  style,
  label,
  focusable = true,
}: TooltipProps) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ left: 0, top: 0, placement: "top" as Placement });
  const triggerRef = useRef<HTMLDivElement>(null);
  const bubbleRef = useRef<HTMLDivElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const id = useId();

  const clearTimer = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  };

  /** Anchor the bubble to the trigger, flipping below when there's no room above. */
  const place = useCallback(() => {
    const trigger = triggerRef.current;
    if (!trigger) return;
    const r = trigger.getBoundingClientRect();
    const bubble = bubbleRef.current?.getBoundingClientRect();
    const width = bubble?.width ?? 0;
    const height = bubble?.height ?? 0;

    const placement: Placement = r.top - height - GAP_PX < EDGE_PX ? "bottom" : "top";
    const half = width / 2;
    const left = Math.min(
      Math.max(r.left + r.width / 2, EDGE_PX + half),
      window.innerWidth - EDGE_PX - half,
    );
    setPos({
      left,
      top: placement === "top" ? r.top - GAP_PX : r.bottom + GAP_PX,
      placement,
    });
  }, []);

  const show = () => {
    if (!content) return;
    clearTimer();
    timer.current = setTimeout(() => setOpen(true), SHOW_DELAY_MS);
  };

  const hide = useCallback(() => {
    clearTimer();
    setOpen(false);
  }, []);

  // Measure once mounted, then track scroll/resize so the bubble stays glued
  // to its trigger (the gantt scrolls in both axes underneath it).
  useLayoutEffect(() => {
    if (!open) return;
    place();
  }, [open, place]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") hide();
    };
    window.addEventListener("scroll", place, true);
    window.addEventListener("resize", place);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("scroll", place, true);
      window.removeEventListener("resize", place);
      window.removeEventListener("keydown", onKey);
    };
  }, [open, place, hide]);

  useEffect(() => clearTimer, []);

  return (
    <>
      <div
        ref={triggerRef}
        className={className}
        style={style}
        // pointerdown → a drag is starting (gantt pan); get out of the way
        onPointerEnter={show}
        onPointerLeave={hide}
        onPointerDown={hide}
        onFocus={show}
        onBlur={hide}
        tabIndex={content && focusable ? 0 : undefined}
        aria-describedby={open ? id : undefined}
      >
        {children}
      </div>

      {open &&
        content &&
        createPortal(
          <div
            ref={bubbleRef}
            id={id}
            role="tooltip"
            aria-label={label}
            className={[
              // NB: explicit rgba — Tailwind's opacity scale has no /97 step,
              // so `bg-[#141a45]/97` would silently drop the background.
              "pointer-events-none fixed z-[100] flex items-center gap-2 whitespace-nowrap",
              "rounded-[10px] border border-[#3d4360] bg-[rgba(20,26,69,0.97)] px-[11px] py-[7px]",
              "text-[12px] font-medium leading-tight text-white backdrop-blur-xl",
              // Fade only. tailwindcss-animate's `animate-in` would also drive
              // `transform`, overriding the translate() below that positions the
              // bubble — so it would drift in from the raw anchor coords.
              "shadow-[0_18px_44px_-14px_rgba(0,0,0,0.7)] motion-safe:animate-fade-in",
            ].join(" ")}
            style={{
              left: pos.left,
              top: pos.top,
              transform: `translate(-50%, ${pos.placement === "top" ? "-100%" : "0"})`,
            }}
          >
            {content}
            {/* caret — a rotated square borrowing two of the bubble's borders */}
            <span
              aria-hidden
              className="absolute left-1/2 h-[9px] w-[9px] -translate-x-1/2 rotate-45 border-[#3d4360] bg-[#141a45]"
              style={
                pos.placement === "top"
                  ? { bottom: -5, borderRightWidth: 1, borderBottomWidth: 1 }
                  : { top: -5, borderLeftWidth: 1, borderTopWidth: 1 }
              }
            />
          </div>,
          document.body,
        )}
    </>
  );
}
