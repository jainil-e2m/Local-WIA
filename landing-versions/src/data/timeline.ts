/* ────────────────────────────────────────────────────────────────
   Build timeline shown in the hero's stat row (and in the "View build
   timeline" modal, whenever that is put back on the page).

   THIS IS THE WEDDING INDUSTRY ADS ROADMAP, and it must stay the same
   roadmap the Blueprint presents. Every row below is one Blueprint
   initiative, carrying its Blueprint id — so the hub cannot advertise a
   number the Blueprint does not contain. The previous contents of this
   file were the inherited Wahha Design plan (Technical SEO, OpenClaw,
   AI Presence, Lead Magnet); it was still driving this client's hero
   counters, which read "7 automations · 7 live" for work that was never
   part of this engagement.

   WHAT "DELIVERED" MEANS HERE. Only the three consoles actually built
   and walked through at the blueprint review carry `status:
   "completed"`. Nothing in this engagement is running in production
   against live data yet, so the hero labels them "Demoed at review",
   never "Live". Do not pin a row completed until it is.

   EDIT HERE to keep the client-facing plan current — planned windows
   are planning data, not wired to any backend. Dates are ISO
   `yyyy-mm-dd`, interpreted in the visitor's local timezone.

   The board is time-driven for PROGRESS and milestone-driven for
   DELIVERY. Where the TODAY line stands decides whether a bar is empty,
   filling or past its window; only a pinned `status: "completed"`
   decides whether it counts as delivered. A window that elapses with
   no milestone recorded reads "overdue", not "delivered" — the hero
   tally must never rise merely because time passed.

   THE PLANNED WINDOWS ARE INDICATIVE. Nothing below has been agreed
   with the client as a commitment; they are a proposed sequence for
   the blueprint conversation. Anything running past the current
   engagement is a sketch of order, not a schedule.
   ──────────────────────────────────────────────────────────────── */

export type TimelineStatus = "completed" | "in-progress" | "not-started" | "overdue";

export interface TimelineItem {
  id: string;
  name: string;
  status: TimelineStatus;
  /** Planned working window (start inclusive → end), ISO `yyyy-mm-dd`. */
  start: string;
  end: string;
  /** Set false for plan line-items that are not client-facing automations
      (e.g. the dashboard itself) — they still appear on the timeline but are
      excluded from the hero's automation counts. Defaults to true. */
  countsAsAutomation?: boolean;
}

/** Day 1 of the engagement — the day counter starts here. First discovery
    call, 26 August 2026. */
export const TIMELINE_KICKOFF = "2026-08-26";

/* The assessment window itself, and the consoles built inside it. Neither is
   a client-facing automation, so neither is counted as one — same reasoning
   as the Central Dashboard line-item this replaces. */
const ASSESSMENT: TimelineItem[] = [
  {
    id: "discovery-audit",
    name: "Discovery, task audit & blueprint",
    status: "completed",
    start: "2026-08-26",
    end: "2026-09-10",
    countsAsAutomation: false,
  },
  {
    id: "command-center",
    name: "Command Center (this hub)",
    status: "completed",
    start: "2026-08-26",
    end: "2026-09-10",
    countsAsAutomation: false,
  },
  {
    id: "ops-hub",
    name: "AI Operations Hub walkthrough",
    status: "completed",
    start: "2026-08-26",
    end: "2026-09-10",
    countsAsAutomation: false,
  },
];

/* Phase 1 — Stop the Leaks. Fifteen initiatives, Oct–Dec 2026.
   ON-01, MP-01 and MK-01 are pinned completed: those are the three consoles
   demoed at the 10 September review. */
const PHASE_1: TimelineItem[] = [
  { id: "ON-01", name: "ON-01 · Signed-and-paid onboarding trigger", status: "completed", start: "2026-09-01", end: "2026-09-10" },
  { id: "MP-01", name: "MP-01 · Roll call & absence flagging", status: "completed", start: "2026-09-01", end: "2026-09-10" },
  { id: "MK-01", name: "MK-01 · Meeting recap → action items → ClickUp", status: "completed", start: "2026-09-01", end: "2026-09-10" },
  { id: "CC-01", name: "CC-01 · Inbox triage & auto-filing", status: "not-started", start: "2026-10-05", end: "2026-10-23" },
  { id: "CC-02", name: "CC-02 · Draft emails in Whitney's voice", status: "not-started", start: "2026-10-12", end: "2026-11-13" },
  { id: "CC-03", name: "CC-03 · Waiting-tag follow-up detector", status: "not-started", start: "2026-11-02", end: "2026-11-20" },
  { id: "MP-02", name: "MP-02 · Session reminder posts", status: "not-started", start: "2026-10-05", end: "2026-10-16" },
  { id: "OP-01", name: "OP-01 · Overdue task digest → Slack", status: "not-started", start: "2026-10-19", end: "2026-10-30" },
  { id: "OP-03", name: "OP-03 · Billing & data-hygiene flags", status: "not-started", start: "2026-10-19", end: "2026-10-30" },
  { id: "MK-02", name: "MK-02 · Zoom asset auto-archival", status: "not-started", start: "2026-10-26", end: "2026-11-13" },
  { id: "ON-02", name: "ON-02 · Welcome email + checklist assignment", status: "not-started", start: "2026-11-09", end: "2026-11-27" },
  { id: "ON-04", name: "ON-04 · Onboarding workspace provisioning", status: "not-started", start: "2026-11-16", end: "2026-12-11" },
  { id: "ON-03", name: "ON-03 · Client asset intake → Drive filing", status: "not-started", start: "2026-11-23", end: "2026-12-04" },
  { id: "PM-01", name: "PM-01 · Weekly Google Ads performance watch", status: "not-started", start: "2026-11-30", end: "2026-12-18" },
  { id: "PM-02", name: "PM-02 · Weekly Meta Ads performance watch", status: "not-started", start: "2026-11-30", end: "2026-12-18" },
];

/* Phase 2 — Free the Founder. Eleven initiatives, Jan–Mar 2027. */
const PHASE_2: TimelineItem[] = [
  { id: "MC-01", name: "MC-01 · Transcript → content idea queue", status: "not-started", start: "2027-01-11", end: "2027-01-29" },
  { id: "MC-02", name: "MC-02 · Reel scripts with voice-note steering", status: "not-started", start: "2027-01-18", end: "2027-02-12" },
  { id: "CC-04", name: "CC-04 · Post-meeting template recap emails", status: "not-started", start: "2027-01-11", end: "2027-01-29" },
  { id: "CC-05", name: "CC-05 · Post-sales-call proactive drafts", status: "not-started", start: "2027-01-25", end: "2027-02-19" },
  { id: "MK-03", name: "MK-03 · Client-facing recap drafting", status: "not-started", start: "2027-02-01", end: "2027-02-26" },
  { id: "MP-03", name: "MP-03 · Session recap post + Canva banner", status: "not-started", start: "2027-02-08", end: "2027-02-26" },
  { id: "OP-02", name: "OP-02 · Action-item chase & acknowledgement tracking", status: "not-started", start: "2027-02-15", end: "2027-03-19" },
  { id: "PM-03", name: "PM-03 · Monthly client report pack", status: "not-started", start: "2027-02-15", end: "2027-03-26" },
  { id: "ON-05", name: "ON-05 · Cross-track launch gate", status: "not-started", start: "2027-03-01", end: "2027-03-12" },
  { id: "MC-03", name: "MC-03 · Multi-format repurposing", status: "not-started", start: "2027-03-08", end: "2027-03-26" },
  { id: "MC-04", name: "MC-04 · Case-study extraction", status: "not-started", start: "2027-03-15", end: "2027-04-02" },
];

/* Phase 3 — Own the Fulfillment. The track both discovery calls named as the
   larger prize and deliberately sequenced last. Scoped after Phase 1–2 land. */
const PHASE_3: TimelineItem[] = [
  { id: "FF-01", name: "FF-01 · Maintained client knowledge base", status: "not-started", start: "2027-04-12", end: "2027-05-14" },
  { id: "FF-02", name: "FF-02 · Creative brief & first-draft copy", status: "not-started", start: "2027-05-03", end: "2027-06-04" },
  { id: "FF-03", name: "FF-03 · Landing-page QA & conversion check", status: "not-started", start: "2027-05-24", end: "2027-06-18" },
];

export const timelineItems: TimelineItem[] = [
  ...ASSESSMENT,
  ...PHASE_1,
  ...PHASE_2,
  ...PHASE_3,
];

/** The roadmap's three phases in order, for surfaces that present the plan
    phase by phase. Same rows as `timelineItems`, grouped — not a second list. */
export const ROADMAP_PHASES: readonly { id: string; title: string; items: readonly TimelineItem[] }[] = [
  { id: "phase-1", title: "Stop the Leaks", items: PHASE_1 },
  { id: "phase-2", title: "Free the Founder", items: PHASE_2 },
  { id: "phase-3", title: "Own the Fulfillment", items: PHASE_3 },
];

/* ────────────────────────────────────────────────────────────────
   Scheduled hand-off — OFF for this engagement.

   The mechanism below froze the board on a fixed date once the previous
   engagement's subscription lapsed. Wedding Industry Ads' roadmap runs
   live, so the freeze date is null and nothing is suspended. Both are
   kept rather than deleted: setting a date here is the documented way
   to snapshot the board at the end of an engagement, and
   resolveTimelineView() is the only thing that knows it exists.
   ──────────────────────────────────────────────────────────────── */

/**
 * First day the board is shown FROZEN, ISO `yyyy-mm-dd`, read in the visitor's
 * local timezone like every other date in this file. `null` runs live
 * indefinitely, which is the current setting.
 */
export const TIMELINE_FREEZE_FROM: string | null = null;

/**
 * Line items dropped from the frozen board — planned automations an engagement
 * no longer covers. Empty while the board runs live.
 */
export const SUSPENDED_ITEM_IDS: readonly string[] = [];

const DAY_MS = 86_400_000;

/** Parse ISO yyyy-mm-dd as LOCAL midnight (new Date("yyyy-mm-dd") would be UTC). */
export function parseISODate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

/**
 * Collapse an instant to local midnight.
 *
 * The whole board is day-granular — axis ticks, bar endpoints and status
 * boundaries are all local midnights. Anything comparing "now" against them
 * must be normalized the same way, otherwise the time of day leaks into the
 * geometry: an un-normalized TODAY marker drifts up to a full day-width past
 * a bar that ends on the same date (0px at midnight, ~12px by 23:59).
 */
export function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

/**
 * 1-based day counter since kickoff: Day 1 on TIMELINE_KICKOFF itself,
 * incrementing every local midnight. Zero or negative = kickoff is still
 * `1 - n` days away.
 */
export function kickoffDayNumber(now: Date = new Date()): number {
  const start = parseISODate(TIMELINE_KICKOFF);
  return Math.floor((startOfDay(now).getTime() - start.getTime()) / DAY_MS) + 1;
}

/**
 * Where the TODAY line stands relative to an item's planned window decides the
 * state the board shows:
 *   line before start  → not-started (empty track)
 *   line at/after start → in-progress (bar starts filling)
 *   line fully past end → completed ("Delivered")
 * A `status: "completed"` in the data acts as a pin — an item delivered early
 * stays delivered regardless of its window.
 */
export function effectiveStatus(item: TimelineItem, now: Date = new Date()): TimelineStatus {
  if (item.status === "completed") return "completed";
  const t = startOfDay(now).getTime();
  /* A PASSED DATE IS NOT A DELIVERY. This used to return "completed" once
     the TODAY line cleared an item's planned end, which meant the hero's
     "Demoed at review" tally grew on its own as time passed — a count of
     demonstrations that rises because nobody demonstrated anything. Only a
     pinned `status: "completed"` counts as delivered now; a window that has
     elapsed with no milestone recorded reads as overdue, which is the true
     statement and the more useful one. */
  if (t >= parseISODate(item.end).getTime()) return "overdue";
  if (t >= parseISODate(item.start).getTime()) return "in-progress";
  return "not-started";
}

/**
 * Fraction of an item's planned window the TODAY line has crossed (0..1) —
 * this is what makes in-progress bars grow a little further every day, and
 * what fills a bar completely once the line has fully passed it.
 *
 * Day-granular (see startOfDay), so a filling bar's leading edge lands exactly
 * on the TODAY line instead of a few pixels past it.
 */
export function windowProgress(item: TimelineItem, now: Date = new Date()): number {
  const status = effectiveStatus(item, now);
  if (status === "completed") return 1;
  if (status === "not-started") return 0;
  const start = parseISODate(item.start).getTime();
  const end = parseISODate(item.end).getTime();
  if (end <= start) return 0;
  return Math.min(1, Math.max(0, (startOfDay(now).getTime() - start) / (end - start)));
}

/** Whether a plan line-item counts as a client-facing automation (see the flag). */
const isAutomation = (item: TimelineItem) => item.countsAsAutomation !== false;

/** Plan line-items that count as client-facing automations (see the flag). */
export const automationItems = timelineItems.filter(isAutomation);

/**
 * Three-way tally of the automations by their time-driven state. The single
 * source of truth for every count in the UI (hero stat row + the timeline
 * modal's summary chips), so the `countsAsAutomation` exclusion is applied
 * once and can never diverge between the two surfaces.
 *
 * `source` exists so a tally can be taken over a narrowed board (the frozen
 * view drops the suspended items) without any caller having to re-implement the
 * exclusion — it is applied here regardless of what is passed. Omitting it
 * counts the whole plan, which is what every existing caller does.
 */
export function automationStatusCounts(
  now: Date = new Date(),
  source: readonly TimelineItem[] = timelineItems,
): Record<TimelineStatus, number> {
  const statuses = source.filter(isAutomation).map((item) => effectiveStatus(item, now));
  return {
    completed: statuses.filter((s) => s === "completed").length,
    "in-progress": statuses.filter((s) => s === "in-progress").length,
    "not-started": statuses.filter((s) => s === "not-started").length,
    overdue: statuses.filter((s) => s === "overdue").length,
  };
}

/**
 * The hero's automation tally, derived from the same time-driven states the
 * timeline board shows — so the counters advance on their own as the TODAY
 * line crosses each window, with no data edits.
 *
 * `delivered` is what the hero labels "Demoed at review", and it counts ONLY
 * rows pinned `status: "completed"` — a recorded milestone, not an elapsed
 * date. Before this the tally rose on its own as the TODAY line cleared each
 * planned window, so the number of things demonstrated grew while nobody
 * demonstrated anything. `inDevelopment` is everything else, so the two
 * always sum to `total`.
 */
export function automationCounts(
  now: Date = new Date(),
  source: readonly TimelineItem[] = timelineItems,
): {
  total: number;
  delivered: number;
  inDevelopment: number;
} {
  const total = source.filter(isAutomation).length;
  const delivered = automationStatusCounts(now, source).completed;
  return { total, delivered, inDevelopment: total - delivered };
}

/** Position of a date along an axis window, clamped to 0..100 (percent). */
export function axisPercent(date: Date, axisStart: Date, axisEnd: Date): number {
  const pct =
    ((date.getTime() - axisStart.getTime()) / (axisEnd.getTime() - axisStart.getTime())) * 100;
  return Math.min(100, Math.max(0, pct));
}

/* ── The frozen board ──────────────────────────────────────────── */

/** The freeze boundary as a local Date, or null while the board runs live. */
function freezeBoundary(): Date | null {
  return TIMELINE_FREEZE_FROM ? parseISODate(TIMELINE_FREEZE_FROM) : null;
}

/**
 * Whether the board has reached its freeze date.
 *
 * Day-granular against local midnight, the same convention bars and the TODAY
 * marker already use — so the board freezes at the visitor's midnight, not at
 * some shared instant. A tab left open crosses over on its next render.
 */
export function isTimelineFrozen(now: Date = new Date()): boolean {
  const boundary = freezeBoundary();
  return boundary !== null && startOfDay(now).getTime() >= boundary.getTime();
}

export interface TimelineView {
  /** True once the freeze date has arrived: the board is a fixed snapshot. */
  frozen: boolean;
  /**
   * The instant every status, bar fill and count on this view must be computed
   * against — pass it wherever `now` would have gone.
   *
   * Live it is `now`. Frozen it is the day BEFORE the freeze: the last day the
   * engagement covered. Reading the freeze date itself would put the board one
   * day into the period no longer covered, which is precisely where a suspended
   * item's window starts filling.
   *
   * Pinning this one value is what freezes the board. None of the date maths
   * above needs to know the concept exists.
   */
  asOf: Date;
  /** Rows to render, in plan order. */
  items: TimelineItem[];
  /** Whether to draw the TODAY marker and its legend entry. */
  showToday: boolean;
  /** Three-way tally over `items` at `asOf` — the modal's summary chips. */
  counts: Record<TimelineStatus, number>;
  /** The hero's stat row, over the same items and the same instant. */
  tally: { total: number; delivered: number; inDevelopment: number };
}

/**
 * What the timeline should show right now — the one place the freeze policy
 * lives, and the only thing both surfaces (the board and the hero's stat row)
 * should read. They have to agree: a hero counting 2 in development beside a
 * board with nothing in development is the visible bug this prevents.
 *
 * `now` is injectable for the same reason every function above takes it: so the
 * behaviour can be tested at a chosen date rather than on the wall clock.
 */
export function resolveTimelineView(now: Date = new Date()): TimelineView {
  const frozen = isTimelineFrozen(now);
  const boundary = freezeBoundary();

  const items = frozen
    ? timelineItems.filter((item) => !SUSPENDED_ITEM_IDS.includes(item.id))
    : timelineItems;

  /* Calendar arithmetic, not `- DAY_MS`: subtracting a fixed 24h from a local
     midnight lands at 23:00 the previous day across a DST boundary, and every
     comparison downstream is against local midnights. */
  const asOf =
    frozen && boundary !== null
      ? new Date(boundary.getFullYear(), boundary.getMonth(), boundary.getDate() - 1)
      : now;

  return {
    frozen,
    asOf,
    items,
    showToday: !frozen,
    counts: automationStatusCounts(asOf, items),
    tally: automationCounts(asOf, items),
  };
}
