import { describe, it, expect } from "vitest";
import {
  timelineItems,
  automationItems,
  automationCounts,
  automationStatusCounts,
  isTimelineFrozen,
  resolveTimelineView,
  parseISODate,
  startOfDay,
  kickoffDayNumber,
  effectiveStatus,
  windowProgress,
  axisPercent,
  SUSPENDED_ITEM_IDS,
  TIMELINE_FREEZE_FROM,
  type TimelineItem,
} from "./timeline";

describe("timeline data", () => {
  it("lists every roadmap row exactly once", () => {
    expect(timelineItems).toHaveLength(32);
    expect(new Set(timelineItems.map((t) => t.id)).size).toBe(32);
  });

  it("every planned window ends after it starts", () => {
    for (const item of timelineItems) {
      expect(parseISODate(item.end).getTime()).toBeGreaterThan(parseISODate(item.start).getTime());
    }
  });

  /* The hub must not be able to advertise an automation the Blueprint does
     not contain, so the counted rows are exactly the 29 Blueprint initiative
     ids — and nothing else. */
  it("counts exactly the 29 Blueprint initiatives as automations", () => {
    expect(automationItems).toHaveLength(29);
    for (const item of automationItems) {
      expect(item.id).toMatch(/^(CC|ON|MK|OP|MP|MC|PM|FF)-\d{2}$/);
    }
  });

  it("excludes the assessment line-items from the automation set", () => {
    const excluded = timelineItems
      .filter((i) => i.countsAsAutomation === false)
      .map((i) => i.id);
    expect(excluded).toEqual(["discovery-audit", "command-center", "ops-hub"]);
    expect(automationItems.map((i) => i.id)).not.toContain("ops-hub");
  });
});

describe("automationCounts (drives the hero's stat row)", () => {
  /* Only the three consoles walked through at the 10 September review are
     pinned completed. The hero labels that tally "Demoed at review", so a
     fourth pin appearing here means someone claimed a delivery. */
  it("reports three demoed consoles at the review, and reconciles to the total", () => {
    const counts = automationCounts(new Date(2026, 8, 10, 12));
    expect(counts).toEqual({ total: 29, delivered: 3, inDevelopment: 26 });
    expect(counts.delivered + counts.inDevelopment).toBe(counts.total);
  });

  /* THE CORRECTION. This used to assert that the tally CLIMBS as the TODAY
     line clears each planned window — so the hero's "Demoed at review" count
     grew by itself while nobody demonstrated anything, and by 2028 claimed
     all 29 were delivered against a repository where three consoles exist.
     A delivery is now a recorded milestone; a date passing is not one. */
  it("does NOT advance merely because time passes", () => {
    expect(automationCounts(new Date(2026, 9, 23, 12))).toMatchObject({
      total: 29,
      delivered: 3,
    });
    expect(automationCounts(new Date(2027, 0, 1, 12))).toMatchObject({
      total: 29,
      delivered: 3,
    });
    expect(automationCounts(new Date(2028, 0, 1))).toMatchObject({
      total: 29,
      delivered: 3,
      inDevelopment: 26,
    });
  });

  it("honours early-delivery pins before the plan starts", () => {
    expect(automationCounts(new Date(2026, 0, 1))).toMatchObject({
      total: 29,
      delivered: 3,
    });
  });

  it("counts an elapsed window as overdue, not as delivered", () => {
    const counts = automationStatusCounts(new Date(2028, 0, 1));
    expect(counts.completed).toBe(3);
    expect(counts.overdue).toBeGreaterThan(0);
  });
});

describe("day-granularity (TODAY marker aligns with bar geometry)", () => {
  const AXIS_START = parseISODate("2026-06-24");
  const AXIS_END = parseISODate("2026-09-23");
  const ppc: TimelineItem = {
    id: "openclaw-ppc",
    name: "PPC",
    status: "not-started",
    start: "2026-07-13",
    end: "2026-07-28",
  };

  it("startOfDay strips the time of day", () => {
    const d = startOfDay(new Date(2026, 6, 28, 23, 59, 59));
    expect([d.getFullYear(), d.getMonth(), d.getDate(), d.getHours()]).toEqual([2026, 6, 28, 0]);
  });

  it("puts the TODAY marker exactly on a bar edge that ends today, at any hour", () => {
    const barEndPct = axisPercent(parseISODate(ppc.end), AXIS_START, AXIS_END);
    for (const hour of [0, 9, 12, 23]) {
      const todayPct = axisPercent(
        startOfDay(new Date(2026, 6, 28, hour, 37)),
        AXIS_START,
        AXIS_END,
      );
      expect(todayPct).toBeCloseTo(barEndPct, 10);
    }
  });

  it("puts a filling bar's leading edge exactly on the TODAY marker", () => {
    const item: TimelineItem = {
      id: "ai-seo",
      name: "AI SEO",
      status: "not-started",
      start: "2026-07-07",
      end: "2026-08-04",
    };
    const now = new Date(2026, 6, 28, 12, 36); // mid-afternoon, mid-window
    const left = axisPercent(parseISODate(item.start), AXIS_START, AXIS_END);
    const right = axisPercent(parseISODate(item.end), AXIS_START, AXIS_END);
    const fillEdgePct = left + windowProgress(item, now) * (right - left);
    const todayPct = axisPercent(startOfDay(now), AXIS_START, AXIS_END);
    expect(fillEdgePct).toBeCloseTo(todayPct, 10);
  });

  it("windowProgress no longer drifts within a single day", () => {
    const morning = windowProgress(ppc, new Date(2026, 6, 20, 0, 1));
    const night = windowProgress(ppc, new Date(2026, 6, 20, 23, 59));
    expect(morning).toBe(night);
  });
});

describe("parseISODate", () => {
  it("parses as local midnight (no UTC off-by-one)", () => {
    const d = parseISODate("2026-08-26");
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 7, 26]);
    expect(d.getHours()).toBe(0);
  });
});

describe("kickoffDayNumber", () => {
  /* Kickoff is the first discovery call, 26 August 2026. */
  it("is Day 1 on kickoff day itself (any time of day)", () => {
    expect(kickoffDayNumber(new Date(2026, 7, 26, 0, 1))).toBe(1);
    expect(kickoffDayNumber(new Date(2026, 7, 26, 23, 59))).toBe(1);
  });

  it("increments once per calendar day", () => {
    expect(kickoffDayNumber(new Date(2026, 8, 1, 9))).toBe(7);
    expect(kickoffDayNumber(new Date(2026, 8, 10, 9))).toBe(16);
  });

  it("goes non-positive before kickoff (used for the countdown)", () => {
    expect(kickoffDayNumber(new Date(2026, 7, 24, 12))).toBe(-1); // 2 days out
    expect(kickoffDayNumber(new Date(2026, 7, 25, 12))).toBe(0); // 1 day out
  });
});

describe("effectiveStatus (the TODAY line decides the state)", () => {
  const base: TimelineItem = {
    id: "x",
    name: "X",
    status: "in-progress",
    start: "2026-08-01",
    end: "2026-08-11",
  };

  it("is not-started while the line is before the window", () => {
    expect(effectiveStatus(base, new Date(2026, 6, 20))).toBe("not-started");
  });

  it("turns in-progress the moment the line reaches the exact start date", () => {
    expect(effectiveStatus(base, new Date(2026, 7, 1, 0, 0))).toBe("in-progress");
    expect(effectiveStatus(base, new Date(2026, 7, 6))).toBe("in-progress");
  });

  it("reads overdue — not Delivered — once the line has crossed the window", () => {
    /* A planned end date arriving is not evidence that anything shipped. */
    expect(effectiveStatus(base, new Date(2026, 7, 11))).toBe("overdue");
    expect(effectiveStatus(base, new Date(2027, 0, 1))).toBe("overdue");
    expect(effectiveStatus({ ...base, status: "not-started" }, new Date(2027, 0, 1))).toBe(
      "overdue",
    );
  });

  it('a "completed" pin stays Delivered even before its window', () => {
    expect(effectiveStatus({ ...base, status: "completed" }, new Date(2026, 0, 1))).toBe(
      "completed",
    );
  });
});

describe("windowProgress", () => {
  const base: TimelineItem = {
    id: "x",
    name: "X",
    status: "in-progress",
    start: "2026-08-01",
    end: "2026-08-11",
  };

  it("follows the TODAY line: empty before, full once crossed", () => {
    expect(windowProgress(base, new Date(2026, 6, 1))).toBe(0);
    expect(windowProgress(base, new Date(2026, 9, 1))).toBe(1);
    // a status pin can only pull a bar forward to Delivered, never hold it back
    expect(windowProgress({ ...base, status: "completed" }, new Date(2026, 0, 1))).toBe(1);
    expect(windowProgress({ ...base, status: "not-started" }, new Date(2027, 0, 1))).toBe(1);
  });

  it("advances in whole days inside the window", () => {
    // Aug 1 → Aug 11 is a 10-day span; on Aug 6 exactly 5 days have elapsed.
    // Deliberately NOT 0.55 — progress is day-granular so a filling bar's edge
    // lands on the TODAY marker rather than a few px past it.
    expect(windowProgress(base, new Date(2026, 7, 6, 12))).toBeCloseTo(0.5, 10);
  });
});

describe("axisPercent", () => {
  const start = parseISODate("2026-07-06");
  const end = parseISODate("2026-10-19");

  it("maps the endpoints to 0 and 100 and clamps beyond them", () => {
    expect(axisPercent(start, start, end)).toBe(0);
    expect(axisPercent(end, start, end)).toBe(100);
    expect(axisPercent(new Date(2026, 0, 1), start, end)).toBe(0);
    expect(axisPercent(new Date(2027, 0, 1), start, end)).toBe(100);
  });

  it("puts the midpoint at 50%", () => {
    const mid = new Date((start.getTime() + end.getTime()) / 2);
    expect(axisPercent(mid, start, end)).toBeCloseTo(50, 5);
  });
});

/* ── Scheduled freeze ─────────────────────────────────────────────
   OFF for this engagement: TIMELINE_FREEZE_FROM is null and nothing is
   suspended, so the board runs live. These assertions guard that state —
   if a freeze date is ever set again, they fail loudly and the frozen-board
   expectations have to come back with it. */

describe("isTimelineFrozen", () => {
  it("is switched off, so the board never freezes", () => {
    expect(TIMELINE_FREEZE_FROM).toBeNull();
    expect(SUSPENDED_ITEM_IDS).toHaveLength(0);
    expect(isTimelineFrozen(new Date(2026, 8, 10))).toBe(false);
    expect(isTimelineFrozen(new Date(2030, 0, 1))).toBe(false);
  });
});

describe("resolveTimelineView — live, at every date", () => {
  it("keeps the TODAY marker and the whole plan, far past the last window", () => {
    const view = resolveTimelineView(new Date(2030, 0, 1));
    expect(view.frozen).toBe(false);
    expect(view.showToday).toBe(true);
    expect(view.items).toBe(timelineItems);
    expect(view.tally.total).toBe(29);
  });
});

describe("count helpers accept a narrowed board", () => {
  const now = new Date(2027, 0, 1); // everything delivered by then

  it("defaults to the whole plan, exactly as before the source param existed", () => {
    expect(automationStatusCounts(now)).toEqual(automationStatusCounts(now, timelineItems));
    expect(automationCounts(now)).toEqual(automationCounts(now, timelineItems));
    expect(automationCounts(now).total).toBe(automationItems.length);
  });

  it("applies the countsAsAutomation exclusion to whatever it is handed", () => {
    // Central Dashboard is passed in but must not be counted — callers never
    // have to pre-filter, which is what stops the rule diverging.
    const withAssessment = timelineItems.filter(
      (item) => item.countsAsAutomation === false || item.id === "ON-01",
    );
    expect(withAssessment.length).toBe(4);
    expect(automationCounts(now, withAssessment).total).toBe(1);
  });
});
