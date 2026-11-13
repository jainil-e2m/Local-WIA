import {
  effectiveStatus,
  parseISODate,
  resolveTimelineView,
  startOfDay,
  type TimelineItem,
} from "@/data/timeline";

/* The bell reads the build timeline — the same source as the hero's stat row —
   so every notification is a statement the roadmap actually supports: what
   started, what is about to, what was demoed, and anything whose window has
   passed with no milestone recorded. Nothing here is invented for the UI. */

export type NoticeTone = "started" | "soon" | "done" | "overdue";

export interface Notice {
  id: string;
  tone: NoticeTone;
  title: string;
  detail: string;
}

const SOON_DAYS = 14;
const DAY_MS = 86_400_000;

const short = (iso: string) =>
  parseISODate(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });

/** "CC-01 · Inbox triage & auto-filing" → its two halves. */
function split(item: TimelineItem) {
  const [code, ...rest] = item.name.split(" · ");
  return rest.length ? { code, label: rest.join(" · ") } : { code: "", label: item.name };
}

export function timelineNotices(now: Date = new Date()): Notice[] {
  const view = resolveTimelineView(now);
  const today = startOfDay(view.asOf).getTime();
  const automations = view.items.filter((i) => i.countsAsAutomation !== false);
  const out: Notice[] = [];

  for (const item of automations) {
    const status = effectiveStatus(item, view.asOf);
    const { code, label } = split(item);
    const start = parseISODate(item.start).getTime();
    if (status === "overdue") {
      out.push({
        id: `overdue:${item.id}`,
        tone: "overdue",
        title: label,
        detail: `${code} · window closed ${short(item.end)}, no milestone recorded`,
      });
    } else if (status === "in-progress") {
      out.push({
        id: `started:${item.id}`,
        tone: "started",
        title: label,
        detail: `${code} · ${start === today ? "started today" : `in build since ${short(item.start)}`}`,
      });
    } else if (status === "not-started" && start - today <= SOON_DAYS * DAY_MS) {
      out.push({
        id: `soon:${item.id}`,
        tone: "soon",
        title: label,
        detail: `${code} · starts ${short(item.start)}`,
      });
    }
  }

  const demoed = automations.filter((i) => effectiveStatus(i, view.asOf) === "completed");
  if (demoed.length) {
    out.push({
      id: `done:${demoed.map((i) => i.id).join(",")}`,
      tone: "done",
      title: `${demoed.length} consoles demoed at review`,
      detail: demoed.map((i) => split(i).code).join(" · "),
    });
  }

  const order: Record<NoticeTone, number> = { overdue: 0, started: 1, soon: 2, done: 3 };
  return out.sort((a, b) => order[a.tone] - order[b.tone]).slice(0, 6);
}
