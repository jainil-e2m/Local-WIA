import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Clock, X } from "lucide-react";
import { Tooltip } from "@/components/ui/tooltip";
import {
  parseISODate,
  effectiveStatus,
  resolveTimelineView,
  timelineItems,
  windowProgress,
  axisPercent,
  startOfDay,
  type TimelineItem,
  type TimelineStatus,
} from "@/data/timeline";

interface TimelineModalProps {
  open: boolean;
  onClose: () => void;
}

type AxisScale = "weekly" | "monthly";

/* Gantt axis — a planning window around the plan in data/timeline.ts. The
   scale toggle only changes tick density/labels (weekly steps vs month
   starts); bar geometry is identical in both.

   DERIVED FROM THE DATA, NOT WRITTEN DOWN. These used to be two literal dates
   ("2026-06-24" → "2026-09-23", 13 weeks) matching the inherited Wahha plan.
   When the roadmap was replaced with this engagement's own — which opens in
   August 2026 and runs into mid-2027 — every bar fell outside that window and
   axisPercent silently clamped all of them onto one edge. Deriving the window
   means the board cannot disagree with the plan it is drawing, whatever the
   plan becomes next. */
const DAY_MS = 86_400_000;

/** Earliest planned start, floored to that week so the first bar is not flush
    against the axis origin. */
const AXIS_START = (() => {
  const starts = timelineItems.map((item) => parseISODate(item.start).getTime());
  return new Date(Math.min(...starts));
})();

/** One weekly tick past the latest planned end — exact 7-day steps from
    AXIS_START, so every weekly label is evenly spaced. */
const AXIS_END = (() => {
  const ends = timelineItems.map((item) => parseISODate(item.end).getTime());
  // Rounded: a DST transition inside the window leaves the raw difference an
  // hour short of a whole number of days.
  const spanDays = Math.round((Math.max(...ends) - AXIS_START.getTime()) / DAY_MS);
  const weeks = Math.ceil(spanDays / 7) + 1;
  return new Date(
    AXIS_START.getFullYear(),
    AXIS_START.getMonth(),
    AXIS_START.getDate() + weeks * 7,
  );
})();

/**
 * Axis end for the FROZEN board: one weekly tick past the last remaining bar.
 *
 * Worth trimming because the frozen board has no TODAY marker — three weeks of
 * empty grid past the final bar reads as "keep scrolling", with nothing out
 * there to find. The extra tick is deliberate padding rather than tidiness:
 * land the axis exactly on the last bar's tick and the final gridline sits on
 * the plot edge, which pushes the monthly view's last label (hardcoded month
 * starts, no edge suppression) off the right side.
 *
 * Clamped to AXIS_END so it can never widen the axis beyond the live one — with
 * nothing suspended it returns AXIS_END exactly, and the live board never calls
 * it at all.
 */
function frozenAxisEndMs(items: readonly TimelineItem[]): number {
  const ends = items.map((item) => parseISODate(item.end).getTime());
  if (!ends.length) return AXIS_END.getTime();
  // Rounded: a DST transition inside the window would leave the raw difference
  // an hour short of a whole number of days.
  const spanDays = Math.round((Math.max(...ends) - AXIS_START.getTime()) / DAY_MS);
  const weeks = Math.ceil(spanDays / 7) + 1;
  const end = new Date(
    AXIS_START.getFullYear(),
    AXIS_START.getMonth(),
    AXIS_START.getDate() + weeks * 7,
  );
  return Math.min(end.getTime(), AXIS_END.getTime());
}

/* The name column stays pinned (sticky) while the plot scrolls horizontally
   under it — its solid background must match the gantt surface below. */
const GANTT_SURFACE = "#12173e";
const LABEL_COLUMN =
  "sticky left-0 z-30 w-[300px] shrink-0 border-r border-white/[0.08] bg-[#12173e] pl-5";
const ROW_PX = 76; // fixed row height keeps label column and plot rows aligned

const STATUS_META: Record<
  TimelineStatus,
  { label: string; chip: string; bar: string; dot: string }
> = {
  completed: {
    label: "Completed",
    chip: "border-brand-teal/35 bg-brand-teal/15 text-brand-teal",
    bar: "bg-gradient-to-r from-brand-teal to-brand-sky",
    dot: "bg-brand-teal",
  },
  "in-progress": {
    label: "In progress",
    chip: "border-brand-orange/35 bg-brand-orange/15 text-brand-orange",
    // yellow → the turquoise a bar "arrives at" once the automation completes
    bar: "bg-gradient-to-r from-brand-orange to-brand-teal",
    dot: "bg-brand-orange",
  },
  /* A planned window that elapsed with no milestone recorded. It used to
     render as "Completed", which is how a roadmap quietly claims delivery. */
  overdue: {
    label: "Past its window",
    chip: "border-[#c0603f]/40 bg-[#c0603f]/15 text-[#e8a184]",
    bar: "bg-gradient-to-r from-brand-orange to-[#c0603f]",
    dot: "bg-[#c0603f]",
  },
  "not-started": {
    label: "Not started",
    // same muted grey as the modal boundary — no bright white edge
    chip: "border-[#3d4360] bg-white/[0.06] text-white/55",
    bar: "",
    dot: "bg-white/40",
  },
};

const shortDate = (iso: string) =>
  parseISODate(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });

function buildTicks(scale: AxisScale, axisEnd: Date): Array<{ date: Date; label?: string }> {
  const ticks: Array<{ date: Date; label?: string }> = [];
  if (scale === "monthly") {
    /* Walks month starts across the derived window rather than iterating
       months 6..8 of a hardcoded 2026, which silently produced nothing once
       the plan crossed a year boundary. A plan spanning many months gets a
       label every month; the year is appended each January so two Februaries
       are distinguishable. */
    const month = new Date(AXIS_START.getFullYear(), AXIS_START.getMonth() + 1, 1);
    while (month.getTime() <= axisEnd.getTime()) {
      ticks.push({
        date: new Date(month),
        label: month.toLocaleDateString("en-US", {
          month: "long",
          ...(month.getMonth() === 0 ? { year: "numeric" as const } : {}),
        }),
      });
      month.setMonth(month.getMonth() + 1);
    }
    return ticks;
  }
  // Weekly: a uniform 7-day cadence from the first planned start, so every
  // label gets identical breathing room.
  const week = new Date(AXIS_START);
  while (week.getTime() <= axisEnd.getTime()) {
    const pct = axisPercent(week, AXIS_START, axisEnd);
    ticks.push({
      date: new Date(week),
      // the final tick sits on the plot edge — keep its gridline, skip the label
      label:
        pct < 98 ? week.toLocaleDateString("en-US", { month: "short", day: "numeric" }) : undefined,
    });
    week.setDate(week.getDate() + 7);
  }
  return ticks;
}

/**
 * Build-progress overlay — opens from the hero's "View build timeline" pill.
 * A dark-theme Gantt of every automation on the engagement plan: weekly (or
 * monthly, via the scale toggle) axis, one bar per automation, and a vertical
 * TODAY marker that advances by itself each day.
 *
 * On or after the scheduled freeze date the board renders as a fixed snapshot
 * instead: suspended rows drop off, the axis trims to what is left, and the
 * TODAY marker goes away. Which of the two you get is decided entirely by
 * resolveTimelineView() — see data/timeline.ts.
 */
export function TimelineModal({ open, onClose }: TimelineModalProps) {
  const [scale, setScale] = useState<AxisScale>("weekly");

  /* Drag-to-pan: holding the left mouse button anywhere on the gantt pans it
     horizontally (same effect as the scrollbar). Only scrollLeft is driven —
     vertical scrolling is deliberately left alone. Touch devices already pan
     natively, so this is mouse-only. */
  const ganttRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ startX: number; startLeft: number } | null>(null);
  const [panning, setPanning] = useState(false);

  function onGanttPointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if ((e.pointerType && e.pointerType !== "mouse") || e.button !== 0) return;
    const el = ganttRef.current;
    if (!el || el.scrollWidth <= el.clientWidth) return; // nothing to pan
    dragRef.current = { startX: e.clientX, startLeft: el.scrollLeft };
    setPanning(true);
    el.setPointerCapture?.(e.pointerId);
    e.preventDefault(); // no text selection while grabbing
  }

  function onGanttPointerMove(e: React.PointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    const el = ganttRef.current;
    if (!drag || !el) return;
    el.scrollLeft = drag.startLeft - (e.clientX - drag.startX);
  }

  function onGanttPointerEnd() {
    if (!dragRef.current) return;
    dragRef.current = null;
    setPanning(false);
  }

  // Esc to close + lock page scroll while open (same contract as AutomationsModal)
  useEffect(() => {
    if (!open) return;
    setScale("weekly"); // default view on every open
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  /* Resolved on every render → the board self-advances day by day, until the
     scheduled freeze date turns it into a fixed snapshot. Everything below
     reads `asOf` instead of the clock, so both behaviours are one code path:
     freezing is a different instant, not a different renderer. */
  const view = resolveTimelineView();
  const { items, asOf } = view;

  /* Frozen, the axis is trimmed to the rows that remain. Live, it is the full
     planning window — the constant, untouched. */
  const axisEndMs = view.frozen ? frozenAxisEndMs(items) : AXIS_END.getTime();
  // Memoized on the timestamp, not the Date: a fresh Date every render would
  // invalidate the ticks memo below on every render.
  const axisEnd = useMemo(() => new Date(axisEndMs), [axisEndMs]);
  const ticks = useMemo(() => buildTicks(scale, axisEnd), [scale, axisEnd]);

  /* `today` is collapsed to local midnight so the marker sits on the same
     day-grid as the axis ticks and bar endpoints; otherwise the time of day
     pushes it past a bar that ends on today's date. */
  const today = startOfDay(asOf);
  const todayInAxis = today >= AXIS_START && today <= axisEnd;
  // A frozen board has no today to mark: the snapshot is a past date, and a
  // marker on it would claim the plan is still moving.
  const showTodayMarker = view.showToday && todayInAxis;
  const todayPct = axisPercent(today, AXIS_START, axisEnd);
  // Per-row states drive each bar; the summary chips use the shared tally so
  // they exclude non-automation line items (the dashboard itself) exactly like
  // the hero's stat row does — that row still renders, it just isn't counted.
  const statuses = items.map((item) => effectiveStatus(item, asOf));
  const counts = view.counts;

  /* The vertical TODAY tag prefers the middle row, but never sits on a bar:
     if the middle row's bar crosses today's x-position, shift to the nearest
     clear row (upward first). */
  const bars = items.map((item) => {
    const left = axisPercent(parseISODate(item.start), AXIS_START, axisEnd);
    const right = axisPercent(parseISODate(item.end), AXIS_START, axisEnd);
    return { left, width: right - left };
  });
  const PAD = 1.4; // percent of clearance around the tag
  const blocked = bars.map((b) => todayPct >= b.left - PAD && todayPct <= b.left + b.width + PAD);
  let tagRow = Math.floor(items.length / 2);
  if (blocked[tagRow]) {
    for (let step = 1; step < items.length; step++) {
      if (tagRow - step >= 0 && !blocked[tagRow - step]) {
        tagRow -= step;
        break;
      }
      if (tagRow + step < items.length && !blocked[tagRow + step]) {
        tagRow += step;
        break;
      }
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="fixed inset-0 z-[80] flex items-center justify-center overflow-hidden bg-[#0b0f22]/60 px-4 py-6 backdrop-blur-xl"
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-label="Automation build timeline"
        >
          <div className="relative w-full max-w-[1180px]" onClick={(e) => e.stopPropagation()}>
            <motion.div
              initial={{ opacity: 0, y: 42, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 32, scale: 0.98, transition: { duration: 0.22 } }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              // Opaque panel, no backdrop-filter: the hero keeps animating behind
              // the overlay, and a translucent blurred panel would force that to
              // be re-sampled on every scroll frame (visible jank on the gantt).
              // Muted grey border — deliberately not white so the edge stays quiet.
              className="relative flex max-h-[82svh] w-full flex-col overflow-hidden rounded-[28px] border border-[#3d4360] bg-[#10153a] shadow-[0_40px_110px_-30px_rgba(0,0,0,0.7)]"
            >
              {/* close — inside the panel's top-right corner; the header area
                  never scrolls in this layout, so nothing can slide under it */}
              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="absolute right-5 top-5 z-10 grid h-10 w-10 place-items-center rounded-full border border-white/15 bg-white/[0.06] text-white/60 transition-colors hover:bg-white/[0.14] hover:text-white"
              >
                <X className="h-[18px] w-[18px]" />
              </button>

              <div className="flex min-h-0 flex-col px-7 pb-7 pt-8 sm:px-9">
                {/* ── Header ─────────────────────────────────── */}
                <div>
                  <p className="text-[11.5px] font-bold uppercase tracking-[0.3em] text-brand-orange">
                    Automation Hub
                  </p>
                  <h2 className="mt-2 text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
                    Build timeline
                  </h2>
                  {/* Present tense only holds while the plan is still moving. */}
                  <p className="mt-2 max-w-md text-[14px] leading-relaxed text-white/60">
                    {view.frozen
                      ? "Everything we've built for you."
                      : "Every automation we're building for you."}
                  </p>
                </div>

                {/* ── Summary chips + scale toggle ───────────── */}
                <div className="mt-6 flex flex-wrap items-center gap-2.5">
                  {(Object.keys(counts) as TimelineStatus[])
                    /* Frozen, nothing is building or pending — "0 In progress"
                       is noise next to a board that shows why. Live, every chip
                       stays even at zero, so the running board is unchanged. */
                    .filter((status) => !view.frozen || counts[status] > 0)
                    .map((status) => (
                      <span
                        key={status}
                        className={[
                          "inline-flex items-center rounded-full border px-3.5 py-1.5",
                          "text-[11px] font-bold uppercase tracking-[0.14em] tabular-nums",
                          STATUS_META[status].chip,
                        ].join(" ")}
                      >
                        {`${counts[status]} ${STATUS_META[status].label}`}
                      </span>
                    ))}

                  {/* subtle weekly ⇄ monthly switch */}
                  {/* same muted grey border as the modal boundary */}
                  <div className="ml-auto inline-flex rounded-full border border-[#3d4360] bg-white/[0.05] p-1">
                    {(["weekly", "monthly"] as const).map((option) => (
                      <button
                        key={option}
                        type="button"
                        aria-pressed={scale === option}
                        onClick={() => setScale(option)}
                        className={[
                          "rounded-full px-3.5 py-1 text-[11px] font-bold uppercase tracking-[0.14em] transition-colors",
                          scale === option
                            ? "bg-white/[0.14] text-white"
                            : "text-white/45 hover:text-white/75",
                        ].join(" ")}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>

                {/* ── Gantt ──────────────────────────────────── */}
                {/* Weekly gets a wide canvas — labels never cram; the container
                  scrolls horizontally (themed bar) and the name column stays
                  pinned. Monthly is compact enough to fit without scrolling. */}
                <div
                  // The gantt is the scroll surface for BOTH axes: the date row
                  // sticks to the top during vertical scroll exactly like the
                  // name column sticks during horizontal scroll (frozen panes).
                  // [contain:paint] keeps scroll repaints inside this box;
                  // transform-gpu on the content promotes it to its own layer so
                  // scrolling is compositor-driven (smooth), not a main-thread
                  // repaint.
                  ref={ganttRef}
                  data-testid="timeline-gantt"
                  onPointerDown={onGanttPointerDown}
                  onPointerMove={onGanttPointerMove}
                  onPointerUp={onGanttPointerEnd}
                  onPointerCancel={onGanttPointerEnd}
                  className={[
                    "scrollbar-themed mt-7 min-h-0 flex-1 overflow-auto overscroll-contain rounded-2xl",
                    "border border-white/[0.08] [contain:paint]",
                    panning ? "cursor-grabbing select-none" : "cursor-grab",
                  ].join(" ")}
                  style={{ background: GANTT_SURFACE }}
                >
                  <div
                    className={[
                      "transform-gpu pb-4 pr-5",
                      scale === "weekly" ? "min-w-[1400px]" : "min-w-[640px]",
                    ].join(" ")}
                  >
                    {/* axis labels — vertically sticky over the scrolling rows */}
                    <div
                      className="sticky top-0 z-40 flex pt-3"
                      style={{ background: GANTT_SURFACE }}
                    >
                      <div className={LABEL_COLUMN} />
                      <div className="relative h-8 flex-1">
                        {ticks.map(({ date, label }) => {
                          if (!label) return null;
                          const pct = axisPercent(date, AXIS_START, axisEnd);
                          return (
                            <span
                              key={date.toISOString()}
                              className={[
                                "absolute top-1.5 whitespace-nowrap text-[10px] font-semibold",
                                "uppercase tracking-[0.06em] text-white/40",
                                // the first tick hugs the sticky name column — left-align
                                // it so it isn't centered halfway underneath
                                pct < 1 ? "translate-x-1" : "-translate-x-1/2",
                              ].join(" ")}
                              style={{ left: `${pct}%` }}
                            >
                              {label}
                            </span>
                          );
                        })}
                      </div>
                    </div>

                    {/* rows */}
                    <div className="flex">
                      {/* label column */}
                      <div className={LABEL_COLUMN}>
                        {items.map((item, i) => (
                          <div
                            key={item.id}
                            className="flex items-center gap-3 border-t border-white/[0.06] pr-5"
                            style={{ height: ROW_PX }}
                          >
                            <span className="w-6 shrink-0 text-[12px] font-extrabold tabular-nums text-white/25">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <div className="min-w-0">
                              <p className="text-[13px] font-bold leading-snug text-white/90">
                                {item.name}
                              </p>
                              <p className="mt-0.5 text-[10.5px] font-medium tabular-nums text-white/35">
                                {shortDate(item.start)} → {shortDate(item.end)}
                                {statuses[i] === "in-progress" && " · Building"}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* plot column */}
                      <div className="relative flex-1">
                        {/* gridlines follow the active scale */}
                        {ticks.map(({ date }) => (
                          <span
                            key={date.toISOString()}
                            className="absolute inset-y-0 w-px bg-white/[0.05]"
                            style={{ left: `${axisPercent(date, AXIS_START, axisEnd)}%` }}
                            aria-hidden
                          />
                        ))}

                        {/* today line + vertical tag — both move every day */}
                        {showTodayMarker && (
                          <>
                            <span
                              className="absolute inset-y-0 z-10 w-[2px] bg-brand-orange/80"
                              style={{ left: `${todayPct}%` }}
                              aria-hidden
                            />
                            <span
                              aria-label="Today"
                              className="absolute z-20 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center rounded-full bg-brand-orange px-[5px] py-2 text-[8px] font-extrabold leading-[1.3] text-[#141a45]"
                              style={{ left: `${todayPct}%`, top: tagRow * ROW_PX + ROW_PX / 2 }}
                            >
                              {"TODAY".split("").map((letter, i) => (
                                <span key={i} aria-hidden>
                                  {letter}
                                </span>
                              ))}
                            </span>
                          </>
                        )}

                        {items.map((item, i) => {
                          // Bar state is decided by the TODAY line: empty until
                          // the line reaches the start date, filling while it
                          // crosses the window, Delivered once fully past.
                          const status = statuses[i];
                          const fill = windowProgress(item, asOf);
                          const meta = STATUS_META[status];

                          return (
                            <div
                              key={item.id}
                              className="relative border-t border-white/[0.06]"
                              style={{ height: ROW_PX }}
                            >
                              <Tooltip
                                className="absolute top-1/2 h-[20px] -translate-y-1/2 overflow-hidden rounded-full border border-white/10 bg-white/[0.05] outline-none focus-visible:ring-2 focus-visible:ring-white/40"
                                style={{ left: `${bars[i].left}%`, width: `${bars[i].width}%` }}
                                label={`${item.name} — ${meta.label}`}
                                content={
                                  <>
                                    <span
                                      className={`h-[7px] w-[7px] shrink-0 rounded-full ${meta.dot}`}
                                      aria-hidden
                                    />
                                    <span>{item.name}</span>
                                    <span className="text-white/40" aria-hidden>
                                      ·
                                    </span>
                                    {/* mirrors the label shown on the bar itself */}
                                    <span className="text-white/60">
                                      {status === "in-progress"
                                        ? "Building"
                                        : status === "completed"
                                          ? "Delivered"
                                          : meta.label}
                                    </span>
                                  </>
                                }
                              >
                                {fill > 0 && (
                                  <span
                                    className={`absolute inset-y-0 left-0 rounded-full ${meta.bar}`}
                                    style={{ width: `${fill * 100}%` }}
                                    aria-hidden
                                  />
                                )}
                                {/* Dark text on a teal→sky gradient — the sky
                                    end is light enough to wash the ink out, so
                                    a soft light halo (inverse of Building's
                                    dark shadow) keeps the edges crisp there. */}
                                {status === "completed" && (
                                  <span className="absolute inset-0 grid place-items-center whitespace-nowrap text-[9px] font-extrabold uppercase tracking-[0.12em] text-[#141a45] [text-shadow:0_1px_2px_rgba(255,255,255,0.45)]">
                                    Delivered
                                  </span>
                                )}
                                {/* Label spans both the colored fill and the
                                    dark unfilled track, so no single flat
                                    color reads well on both — a solid white
                                    washes out against the lighter part of the
                                    orange→teal gradient. A dark drop-shadow
                                    keeps it crisp there while staying just as
                                    visible over the near-black track. */}
                                {status === "in-progress" && (
                                  <span className="absolute inset-0 grid place-items-center whitespace-nowrap text-[9px] font-extrabold uppercase tracking-[0.12em] text-white [text-shadow:0_1px_3px_rgba(0,0,0,0.75)]">
                                    Building
                                  </span>
                                )}
                                {/* A window that elapsed with nothing
                                    recorded. It used to be painted
                                    "Delivered", which is how a roadmap
                                    claims a delivery it never made. */}
                                {status === "overdue" && (
                                  <span className="absolute inset-0 grid place-items-center whitespace-nowrap text-[9px] font-extrabold uppercase tracking-[0.12em] text-white [text-shadow:0_1px_3px_rgba(0,0,0,0.75)]">
                                    Past its window
                                  </span>
                                )}
                              </Tooltip>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>

                {/* ── Legend / status key ────────────────────── */}
                <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2.5 text-[11.5px] font-semibold text-white/55">
                  <span className="inline-flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-brand-teal" aria-hidden />
                    Completed
                  </span>
                  <span className="inline-flex items-center gap-2">
                    <span
                      className="h-2 w-6 rounded-full bg-gradient-to-r from-brand-orange to-brand-teal"
                      aria-hidden
                    />
                    In progress
                  </span>
                  <span className="inline-flex items-center gap-2">
                    <Clock className="h-3.5 w-3.5 text-white/40" aria-hidden />
                    Not started
                  </span>
                  {/* No key for a marker the frozen board does not draw. */}
                  {view.showToday && (
                    <span className="inline-flex items-center gap-2">
                      <span className="h-3.5 w-[2px] bg-brand-orange/80" aria-hidden />
                      Today
                    </span>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
