import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TimelineModal } from "./TimelineModal";
import {
  timelineItems,
  effectiveStatus,
  automationStatusCounts,
  parseISODate,
  SUSPENDED_ITEM_IDS,
  TIMELINE_FREEZE_FROM,
} from "@/data/timeline";

/* Axis labels and month names are derived from the plan the modal is drawing,
   the same way the component derives them — so replacing the roadmap moves the
   assertions with it instead of breaking them. */
const axisStart = new Date(
  Math.min(...timelineItems.map((i) => parseISODate(i.start).getTime())),
);
const weekLabel = (weeksIn: number) =>
  new Date(
    axisStart.getFullYear(),
    axisStart.getMonth(),
    axisStart.getDate() + weeksIn * 7,
  ).toLocaleDateString("en-US", { month: "short", day: "numeric" });

describe("<TimelineModal />", () => {
  beforeEach(() => {
    /* Mid-plan: November 6 2026 sits inside Phase 1, so the board has bars in
       all three states at once — which is what most assertions below need. */
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 10, 6, 12));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders nothing while closed", () => {
    render(<TimelineModal open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("lists every automation on the plan", () => {
    render(<TimelineModal open onClose={vi.fn()} />);
    for (const item of timelineItems) {
      expect(screen.getByText(item.name)).toBeInTheDocument();
    }
  });

  it("summarizes statuses with the time-driven counts", () => {
    render(<TimelineModal open onClose={vi.fn()} />);
    // derived from the shared tally, not hardcoded — moves with the plan dates
    const counts = automationStatusCounts(new Date());
    expect(screen.getByText(`${counts.completed} Completed`)).toBeInTheDocument();
    expect(screen.getByText(`${counts["in-progress"]} In progress`)).toBeInTheDocument();
    expect(screen.getByText(`${counts["not-started"]} Not started`)).toBeInTheDocument();
  });

  it("excludes non-automation rows from the chips but still renders them", () => {
    render(<TimelineModal open onClose={vi.fn()} />);
    // The assessment rows are displayed as Delivered rows on the board...
    expect(screen.getByText("Command Center (this hub)")).toBeInTheDocument();
    expect(screen.getByText("AI Operations Hub walkthrough")).toBeInTheDocument();
    // ...but none of them is counted: the chips tally Blueprint initiatives only.
    const excluded = timelineItems.filter((i) => i.countsAsAutomation === false).length;
    const counts = automationStatusCounts(new Date());
    const chipTotal =
      counts.completed + counts["in-progress"] + counts["not-started"] + counts.overdue;
    expect(chipTotal).toBe(timelineItems.length - excluded);
  });

  it("closes via the close button", () => {
    const onClose = vi.fn();
    render(<TimelineModal open onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("opens the weekly axis on the first planned start and steps in 7s", () => {
    render(<TimelineModal open onClose={vi.fn()} />);
    expect(screen.getByText(weekLabel(0))).toBeInTheDocument();
    expect(screen.getByText(weekLabel(1))).toBeInTheDocument();
    expect(screen.getByText(weekLabel(2))).toBeInTheDocument();
  });

  it("switches to month labels via the scale toggle and back", () => {
    render(<TimelineModal open onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /monthly/i }));
    expect(screen.getByText("October")).toBeInTheDocument();
    expect(screen.getByText("November")).toBeInTheDocument();
    // The year rides on January so two of the same month are distinguishable.
    expect(screen.getByText("January 2027")).toBeInTheDocument();
    expect(screen.queryByText(weekLabel(1))).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /weekly/i }));
    expect(screen.getByText(weekLabel(1))).toBeInTheDocument();
    expect(screen.queryByText("November")).not.toBeInTheDocument();
  });

  it("keeps every planned bar inside the derived axis window", () => {
    /* The failure this guards against is silent: a bar outside
       AXIS_START..AXIS_END gets clamped by axisPercent onto one edge and still
       renders, which is exactly what the hardcoded 2026 axis did to this plan. */
    const ends = timelineItems.map((i) => parseISODate(i.end).getTime());
    const axisEnd = Math.max(...ends);
    for (const item of timelineItems) {
      expect(parseISODate(item.start).getTime()).toBeGreaterThanOrEqual(axisStart.getTime());
      expect(parseISODate(item.end).getTime()).toBeLessThanOrEqual(axisEnd);
    }
  });

  it("renders the vertical TODAY tag when today is inside the axis", () => {
    render(<TimelineModal open onClose={vi.fn()} />);
    expect(screen.getByLabelText("Today")).toBeInTheDocument();
  });

  it("labels in-progress bars Building, never a percentage", () => {
    vi.setSystemTime(new Date(2026, 10, 6, 12)); // mid-window for the Phase 1 items
    render(<TimelineModal open onClose={vi.fn()} />);
    const building = timelineItems.filter(
      (t) => effectiveStatus(t, new Date()) === "in-progress",
    ).length;
    expect(building).toBeGreaterThan(0);
    // one exact-match node per in-progress bar (the label column's copy sits in
    // a mixed text node — "Jul 24 → Aug 14 · Building" — so it isn't matched here)
    expect(screen.getAllByText("Building")).toHaveLength(building);
    expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument();
  });

  it("labels each bar the TODAY line has fully crossed as Delivered", () => {
    render(<TimelineModal open onClose={vi.fn()} />);
    const delivered = timelineItems.filter(
      (t) => effectiveStatus(t, new Date()) === "completed",
    ).length;
    expect(delivered).toBeGreaterThan(0); // sanity: the fixed date crosses some bars
    expect(screen.getAllByText("Delivered")).toHaveLength(delivered);
  });

  it("pans horizontally with left-button drag (and only horizontally)", () => {
    render(<TimelineModal open onClose={vi.fn()} />);
    const gantt = screen.getByTestId("timeline-gantt");
    // jsdom has no layout — fake an overflowing scroll area
    Object.defineProperty(gantt, "scrollWidth", { value: 1600, configurable: true });
    Object.defineProperty(gantt, "clientWidth", { value: 800, configurable: true });
    gantt.scrollLeft = 100;

    fireEvent.pointerDown(gantt, { button: 0, clientX: 500 });
    fireEvent.pointerMove(gantt, { clientX: 440 }); // drag 60px left → content pans right
    expect(gantt.scrollLeft).toBe(160);

    fireEvent.pointerUp(gantt);
    fireEvent.pointerMove(gantt, { clientX: 300 }); // after release, moves do nothing
    expect(gantt.scrollLeft).toBe(160);
  });

  it("ignores non-primary buttons for panning", () => {
    render(<TimelineModal open onClose={vi.fn()} />);
    const gantt = screen.getByTestId("timeline-gantt");
    Object.defineProperty(gantt, "scrollWidth", { value: 1600, configurable: true });
    Object.defineProperty(gantt, "clientWidth", { value: 800, configurable: true });
    gantt.scrollLeft = 100;

    fireEvent.pointerDown(gantt, { button: 2, clientX: 500 }); // right-click
    fireEvent.pointerMove(gantt, { clientX: 400 });
    expect(gantt.scrollLeft).toBe(100);
  });

  /* ── The freeze is off for this engagement ──────────────────────
     The snapshot mechanism stays in the code (data/timeline.ts documents it as
     the end-of-engagement rollback), but this client's board runs live. These
     assert that, so switching it back on fails here rather than silently
     changing what the client sees. */
  describe("with no freeze date configured", () => {
    it("runs live and keeps the TODAY marker", () => {
      expect(TIMELINE_FREEZE_FROM).toBeNull();
      expect(SUSPENDED_ITEM_IDS).toHaveLength(0);
      render(<TimelineModal open onClose={vi.fn()} />);
      expect(screen.getByLabelText("Today")).toBeInTheDocument();
      expect(
        screen.getByText("Every automation we're building for you."),
      ).toBeInTheDocument();
    });

    it("renders every row on the plan, with nothing dropped", () => {
      render(<TimelineModal open onClose={vi.fn()} />);
      for (const item of timelineItems) {
        expect(screen.getByText(item.name)).toBeInTheDocument();
      }
    });

    it("reads past-its-window, not Delivered, once every date has passed", () => {
      /* THE CORRECTION. This used to assert that every row on the board
         reads "Delivered" in 2028 — a roadmap that claims 32 deliveries
         because the calendar moved. Only recorded milestones are delivered. */
      vi.setSystemTime(new Date(2028, 0, 1));
      render(<TimelineModal open onClose={vi.fn()} />);
      const pinned = timelineItems.filter((i) => i.status === "completed").length;
      expect(screen.getAllByText("Delivered")).toHaveLength(pinned);
      expect(screen.getAllByText("Past its window").length).toBeGreaterThan(0);
      expect(screen.queryByText("Building")).not.toBeInTheDocument();
    });
  });
});
