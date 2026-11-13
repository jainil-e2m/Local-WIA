/* ────────────────────────────────────────────────────────────────
   Engagement record — derivations.

   Everything the Client Hub shows about time is computed here, never stored
   in the corpus. Same rule the hub already follows for counts, extended to
   dates: a record that carries "47 days ago" as a string is wrong the next
   morning, and a demo that recomputes it from a frozen clock is right
   forever.

   ONE CLOCK. Every function below measures against DEMO_NOW, not
   Date.now(). Pass a different `now` only in tests.
   ──────────────────────────────────────────────────────────────── */

import {
  DEMO_NOW_MS,
  LANE_META,
  LANES,
  PHASE_META,
  type ApprovedAsset,
  type EngagementEvent,
  type EngagementRecord,
  type EventLane,
  type Phase,
  type PhaseKey,
} from "@/data/engagement";
import {
  CLIENT_ATTENDANCE,
  CLIENT_INVOICES,
  COMMITMENTS,
  money,
  type Client,
} from "@/data/opsHub";
import type { SourceKey, Tone } from "@/lib/opsHub";

const DAY = 86_400_000;

/* ── Dates ────────────────────────────────────────────────────── */

export const ms = (iso: string) => new Date(iso).getTime();

export const daysBetween = (a: number, b: number) => Math.round((b - a) / DAY);

export const daysAgo = (iso: string, now = DEMO_NOW_MS) =>
  Math.floor((now - ms(iso)) / DAY);

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** "2 Sep 2026" — unambiguous, and short enough for a dense row. */
export function fmtDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

/** "2 Sep" — inside a run where the year is already established. */
export function fmtShort(iso: string): string {
  const d = new Date(iso);
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

export function fmtMonth(dt: Date): string {
  return `${MONTHS[dt.getMonth()]} ${String(dt.getFullYear()).slice(2)}`;
}

export function fmtTime(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/** Relative, and deliberately coarse past a fortnight. "43 days ago" is
    actionable; "1,043 days ago" is noise, so long gaps read in months. */
export function fmtRel(iso: string, now = DEMO_NOW_MS): string {
  const d = Math.floor((now - ms(iso)) / DAY);
  if (d < 0) return `in ${Math.abs(d)}d`;
  if (d === 0) return "today";
  if (d === 1) return "yesterday";
  if (d < 14) return `${d} days ago`;
  if (d < 60) return `${Math.floor(d / 7)} weeks ago`;
  if (d < 365) return `${Math.floor(d / 30)} months ago`;
  const years = Math.floor(d / 365);
  const rem = Math.floor((d % 365) / 30);
  return rem ? `${years}y ${rem}m ago` : `${years}y ago`;
}

/** "18 months" / "1y 10m" — the headline number on an account card. */
export function fmtDuration(days: number): string {
  if (days < 31) return `${days} days`;
  const months = Math.round(days / 30.44);
  if (months < 24) return `${months} months`;
  return `${Math.floor(months / 12)}y ${months % 12}m`;
}

/* ── Engagement age ───────────────────────────────────────────── */

/** Day zero: the day both halves paired, falling back to signature, then to
    the record boundary. A prospect has no day zero and returns null — the UI
    must say "not started" rather than counting from first contact, which
    would quietly turn a sales conversation into an engagement. */
export function engagementStart(rec: EngagementRecord): string | null {
  return rec.origin.pairedAt ?? rec.origin.signedAt ?? null;
}

export function engagementAgeDays(
  rec: EngagementRecord,
  now = DEMO_NOW_MS,
): number | null {
  const start = engagementStart(rec);
  return start === null ? null : Math.floor((now - ms(start)) / DAY);
}

/* ── Phases ───────────────────────────────────────────────────── */

export type ResolvedPhase = Phase & {
  endsAt: string | null;
  label: string;
  color: string;
  current: boolean;
};

/** Phases are authored with a start only; the end is the next one's start.
    Storing both would let them drift apart the first time one is edited. */
export function resolvedPhases(
  rec: EngagementRecord,
  now = DEMO_NOW_MS,
): ResolvedPhase[] {
  return rec.phases.map((p, i) => {
    const next = rec.phases[i + 1];
    return {
      ...p,
      endsAt: next ? next.startsAt : null,
      label: PHASE_META[p.key].label,
      color: PHASE_META[p.key].color,
      current: !next && ms(p.startsAt) <= now,
    };
  });
}

export function currentPhase(
  rec: EngagementRecord,
  now = DEMO_NOW_MS,
): ResolvedPhase | null {
  const all = resolvedPhases(rec, now);
  return all.length ? all[all.length - 1] : null;
}

export const phaseKeyOf = (rec: EngagementRecord): PhaseKey | null =>
  rec.phases.length ? rec.phases[rec.phases.length - 1].key : null;

/* ── Spine span & ticks ───────────────────────────────────────── */

export type SpineZoom = "all" | "year" | "quarter" | "month";

export const ZOOMS: { id: SpineZoom; label: string; days: number | null }[] = [
  { id: "all", label: "Whole engagement", days: null },
  { id: "year", label: "12 months", days: 365 },
  { id: "quarter", label: "90 days", days: 90 },
  { id: "month", label: "30 days", days: 30 },
];

export type Span = { startMs: number; endMs: number; days: number };

/** The window the spine draws. "all" runs from the record boundary — not the
    engagement start — so the pre-signature sales conversation stays visible
    and the boundary marker has somewhere to sit. */
export function spanFor(
  rec: EngagementRecord,
  zoom: SpineZoom,
  now = DEMO_NOW_MS,
): Span {
  const endMs = now + 3 * DAY; // a little air to the right of the today line
  const z = ZOOMS.find((x) => x.id === zoom);
  const startMs =
    z && z.days !== null ? now - z.days * DAY : ms(rec.backfill.beginsAt) - 5 * DAY;
  return { startMs, endMs, days: Math.max(1, Math.round((endMs - startMs) / DAY)) };
}

export type Tick = { ms: number; label: string; major: boolean };

/** Gridline dates for the span. Quarters on a multi-year view, months in the
    middle, weeks up close — chosen by span length so the rail never crowds. */
export function ticksFor(span: Span): Tick[] {
  const out: Tick[] = [];
  const start = new Date(span.startMs);

  if (span.days > 400) {
    const d = new Date(start.getFullYear(), Math.floor(start.getMonth() / 3) * 3, 1);
    while (d.getTime() <= span.endMs) {
      if (d.getTime() >= span.startMs) {
        const q = Math.floor(d.getMonth() / 3) + 1;
        out.push({
          ms: d.getTime(),
          label: `Q${q} ${String(d.getFullYear()).slice(2)}`,
          major: d.getMonth() === 0,
        });
      }
      d.setMonth(d.getMonth() + 3);
    }
    return out;
  }

  if (span.days > 75) {
    const d = new Date(start.getFullYear(), start.getMonth(), 1);
    while (d.getTime() <= span.endMs) {
      if (d.getTime() >= span.startMs) {
        out.push({ ms: d.getTime(), label: fmtMonth(d), major: d.getMonth() === 0 });
      }
      d.setMonth(d.getMonth() + 1);
    }
    return out;
  }

  const d = new Date(span.startMs);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + ((8 - d.getDay()) % 7)); // next Monday
  while (d.getTime() <= span.endMs) {
    out.push({ ms: d.getTime(), label: fmtShort(d.toISOString()), major: false });
    d.setDate(d.getDate() + 7);
  }
  return out;
}

/** Position of an instant inside the span, 0–100. */
export const pctOf = (at: number, span: Span) =>
  ((at - span.startMs) / (span.endMs - span.startMs)) * 100;

export const inSpan = (e: EngagementEvent, span: Span) => {
  const t = ms(e.occurredAt);
  return t >= span.startMs && t <= span.endMs;
};

/* ── Lane health & staleness ──────────────────────────────────── */

export type HealthState = "fresh" | "aging" | "stale" | "silent" | "n/a";

export type LaneHealth = {
  lane: EventLane;
  label: string;
  short: string;
  color: string;
  count: number;
  lastAt: string | null;
  days: number | null;
  expectDays: number | null;
  state: HealthState;
  /** Why it is in that state, in words a reviewer can act on. */
  note: string;
  /** Sources that stopped returning data on this lane, from the backfill
      declaration. A silent lane with an unreachable source is a coverage
      problem, not a client problem — and those need different responses. */
  blindSources: SourceKey[];
};

const LANE_SOURCES: Record<EventLane, SourceKey[]> = {
  onboarding: ["gmail", "highlevel", "clickup", "drive", "slack", "aihq"],
  comms: ["gmail", "slack"],
  meetings: ["zoom", "fathom", "drive"],
  commitments: ["zoom", "fathom", "clickup", "slack", "gmail"],
  work: ["clickup", "drive"],
  money: ["highlevel", "gmail"],
  engagement: ["zoom", "highlevel", "aihq"],
};

/** Events a lane needs before its silence is worth measuring. Below this it
    has no rhythm, so a gap is not evidence of anything. */
export const CADENCE_MIN = 3;

export function laneHealth(
  rec: EngagementRecord,
  now = DEMO_NOW_MS,
): LaneHealth[] {
  return LANES.map((meta) => {
    const rows = rec.events.filter((e) => e.lane === meta.key);
    const last = rows.length ? rows[rows.length - 1] : null;
    const days = last ? Math.floor((now - ms(last.occurredAt)) / DAY) : null;

    const blind = rec.backfill.unreachable
      .filter((u) => LANE_SOURCES[meta.key].includes(u.source))
      .map((u) => u.source);

    let state: HealthState = "n/a";
    let note = "No cadence expected on this lane.";

    if (meta.expectDays === null) {
      state = "n/a";
      note = rows.length
        ? "A period, not a cadence — nothing here goes stale."
        : "Nothing recorded.";
    } else if (rows.length > 0 && rows.length < CADENCE_MIN) {
      /* You cannot be late against a rhythm you never had. A retainer has no
         office hours, so its engagement lane holds two contact changes and
         nothing else — calling that "stale" put an 18-month alarm on the
         healthiest account in the book. Absence only means something once a
         cadence exists to be absent from. */
      state = "n/a";
      note = `Only ${rows.length} event${rows.length === 1 ? "" : "s"} ever — no cadence on this lane for this account.`;
    } else if (last === null || days === null) {
      state = "silent";
      note = "Nothing has ever landed on this lane.";
    } else if (days <= meta.expectDays) {
      state = "fresh";
      note = `Within the ${meta.expectDays}-day expectation.`;
    } else if (days <= meta.expectDays * 2) {
      state = "aging";
      note = `${days} days since the last event — past the ${meta.expectDays}-day expectation.`;
    } else {
      state = "stale";
      note = `${days} days of silence against a ${meta.expectDays}-day expectation.`;
    }

    if (blind.length && state !== "fresh") {
      note += ` ${blind.length === 1 ? "One source is" : `${blind.length} sources are`} unreachable on this lane, so some of the silence may be coverage rather than inactivity.`;
    }

    return {
      lane: meta.key,
      label: meta.label,
      short: meta.short,
      color: meta.color,
      count: rows.length,
      lastAt: last?.occurredAt ?? null,
      days,
      expectDays: meta.expectDays,
      state,
      note,
      blindSources: blind,
    };
  });
}

export const HEALTH_META: Record<HealthState, { label: string; tone: Tone }> = {
  fresh: { label: "Current", tone: "green" },
  aging: { label: "Aging", tone: "amber" },
  stale: { label: "Stale", tone: "red" },
  silent: { label: "Never", tone: "red" },
  "n/a": { label: "—", tone: "outline" },
};

/* ── Gaps ─────────────────────────────────────────────────────── */

export type Gap = {
  lane: EventLane;
  fromMs: number;
  toMs: number;
  days: number;
  /** A gap that a declared unreachable source explains. Drawn differently:
      one is "they went quiet", the other is "we stopped being able to see". */
  explainedBy: SourceKey | null;
  why: string | null;
};

/** Silences longer than twice the lane's expectation, inside the span. The
    point is to DRAW them: a lane that simply stops has to look like it
    stopped, or an incomplete record reads as a complete one. */
export function gapsFor(
  rec: EngagementRecord,
  lane: EventLane,
  span: Span,
  now = DEMO_NOW_MS,
): Gap[] {
  const meta = LANE_META[lane];
  if (meta.expectDays === null) return [];
  const threshold = meta.expectDays * 2 * DAY;

  const rows = rec.events
    .filter((e) => e.lane === lane)
    .map((e) => ms(e.occurredAt))
    .sort((a, b) => a - b);
  /* Same rule as laneHealth: no cadence, no gap. Two events eighteen months
     apart are not a silence between them, they are just two events. */
  if (rows.length < CADENCE_MIN) return [];

  const unreachable = rec.backfill.unreachable.filter((u) =>
    LANE_SOURCES[lane].includes(u.source),
  );

  const marks = [...rows, now];
  const out: Gap[] = [];
  for (let i = 0; i < marks.length - 1; i++) {
    const from = marks[i];
    const to = marks[i + 1];
    if (to - from < threshold) continue;
    if (to < span.startMs || from > span.endMs) continue;
    const cause = unreachable.find((u) => u.from !== null && ms(u.from) <= to);
    out.push({
      lane,
      fromMs: from,
      toMs: to,
      days: Math.round((to - from) / DAY),
      explainedBy: cause?.source ?? null,
      why: cause?.why ?? null,
    });
  }
  return out;
}

/* ── Citation coverage ────────────────────────────────────────── */

export type Coverage = { citable: number; total: number; pct: number };

/** How much of the record can be checked. Counted only over the lanes where
    a citation is meaningful — an invoice row does not need a transcript
    second, and scoring it as uncited would make the number meaningless. */
export function citationCoverage(rec: EngagementRecord): Coverage {
  const scored = rec.events.filter(
    (e) => e.lane === "meetings" || e.lane === "commitments",
  );
  const citable = scored.filter((e) => e.citation !== null).length;
  return {
    citable,
    total: scored.length,
    pct: scored.length ? Math.round((citable / scored.length) * 100) : 0,
  };
}

/* ── Assets ───────────────────────────────────────────────────── */

/** What is actually live: assets nothing else supersedes. The chain is why
    "which landing page is current" is answerable without opening Drive. */
export function liveAssets(rec: EngagementRecord): ApprovedAsset[] {
  const superseded = new Set(
    rec.assets.map((a) => a.supersedes).filter((x): x is string => x !== null),
  );
  return rec.assets
    .filter((a) => !superseded.has(a.id))
    .sort((a, b) => b.approvedAt.localeCompare(a.approvedAt));
}

export function supersededAssets(rec: EngagementRecord): ApprovedAsset[] {
  const superseded = new Set(
    rec.assets.map((a) => a.supersedes).filter((x): x is string => x !== null),
  );
  return rec.assets
    .filter((a) => superseded.has(a.id))
    .sort((a, b) => b.approvedAt.localeCompare(a.approvedAt));
}

/* ── Activity density, for the account cards ──────────────────── */

/** Twelve monthly buckets of event counts — the sparkline on a card. Cheap
    enough to run for every account in the grid. */
export function activityBuckets(
  rec: EngagementRecord,
  months = 12,
  now = DEMO_NOW_MS,
): number[] {
  const out = new Array(months).fill(0) as number[];
  const end = new Date(now);
  for (const e of rec.events) {
    const t = new Date(e.occurredAt);
    const diff =
      (end.getFullYear() - t.getFullYear()) * 12 + (end.getMonth() - t.getMonth());
    if (diff >= 0 && diff < months) out[months - 1 - diff] += 1;
  }
  return out;
}

/* ── The brief ────────────────────────────────────────────────── */

export type BriefFact = {
  label: string;
  value: string;
  cite: string | null;
  tone?: Tone;
};

export type BriefSection = {
  key: string;
  title: string;
  blurb: string;
  facts: BriefFact[];
};

/* Assembled from the record and the ledgers, never written by hand. It is
   the handover artefact: what someone taking this account over on Monday has
   to know, in the order they need it. The last section is the one that makes
   it trustworthy — what the record CANNOT tell them. */
export function buildBrief(
  rec: EngagementRecord,
  client: Client,
  now = DEMO_NOW_MS,
): BriefSection[] {
  const commits = COMMITMENTS.filter((c) => c.clientId === client.id);
  const invoices = CLIENT_INVOICES[client.id] ?? [];
  const attendance = CLIENT_ATTENDANCE[client.id] ?? [];
  const health = laneHealth(rec, now);
  const phase = currentPhase(rec, now);
  const age = engagementAgeDays(rec, now);
  const live = liveAssets(rec);

  const openCommits = commits.filter((c) => c.state !== "done");
  const overdue = commits.filter((c) => c.state === "overdue");
  const blocked = commits.filter((c) => c.state === "blocked");
  const unacked = commits.filter(
    (c) => c.side === "wia" && c.state !== "done" && c.ack === "none",
  );
  const theirs = commits.filter((c) => c.side === "client" && c.state !== "done");

  const paid = invoices.filter((i) => i.state === "paid");
  const lateBills = invoices.filter((i) => i.state === "overdue");
  const collected = paid.reduce((t, i) => t + i.amount, 0);
  const outstanding = invoices
    .filter((i) => i.state !== "paid")
    .reduce((t, i) => t + i.amount, 0);
  const avgPay = paid.length
    ? Math.round(paid.reduce((t, i) => t + i.daysToPay, 0) / paid.length)
    : null;

  const contacts = rec.people.filter((p) => p.side === "client" && p.validTo === null);
  const formerContacts = rec.people.filter(
    (p) => p.side === "client" && p.validTo !== null,
  );

  const meetingsHealth = health.find((h) => h.lane === "meetings")!;
  const commsHealth = health.find((h) => h.lane === "comms")!;
  const cov = citationCoverage(rec);

  const sections: BriefSection[] = [];

  sections.push({
    key: "who",
    title: "Who they are",
    blurb: "Identity and commercial terms as they stand today.",
    facts: [
      { label: "Account", value: `${client.name} · ${client.service}`, cite: null },
      {
        label: "Primary contact",
        value: contacts.length
          ? contacts.map((p) => `${p.name} (${p.role}) · ${p.email}`).join(" · ")
          : "None on record",
        cite: null,
      },
      ...(formerContacts.length
        ? [
            {
              label: "Previous contacts",
              value: formerContacts
                .map((p) => `${p.name} — left ${fmtShort(p.validTo!)}`)
                .join(" · "),
              cite: null,
              tone: "amber" as Tone,
            },
          ]
        : []),
      {
        label: "Monthly",
        value: rec.terms.monthly === null ? "Not contracted" : `${money(rec.terms.monthly)} / month`,
        cite: rec.terms.contractRef,
      },
      {
        label: "Offers",
        value: rec.terms.offers.join(" · "),
        cite: null,
      },
      {
        label: "Engagement age",
        value:
          age === null
            ? "Not started — prospect"
            : `${fmtDuration(age)} · since ${fmtDate(engagementStart(rec)!)}`,
        cite: rec.origin.projectKey ? `Onboarding · ${rec.origin.projectKey}` : null,
      },
      {
        label: "Phase",
        value: phase ? `${phase.label} — ${phase.note}` : "Unknown",
        cite: null,
        tone: phase?.key === "at_risk" ? "red" : phase?.key === "renewal" ? "amber" : "green",
      },
    ],
  });

  sections.push({
    key: "start",
    title: "How it started",
    blurb: "Straight from the onboarding record — the only dates in this build that were never typed by hand.",
    facts:
      rec.origin.signedAt === null
        ? [
            {
              label: "Status",
              value: "No contract signed. This is a sales conversation, not an engagement.",
              cite: null,
              tone: "outline",
            },
            {
              label: "First contact",
              value: fmtDate(rec.backfill.beginsAt),
              cite: null,
            },
          ]
        : [
            { label: "Contract signed", value: fmtDate(rec.origin.signedAt), cite: rec.origin.projectKey },
            {
              label: "First payment",
              value: rec.origin.paidAt
                ? `${fmtDate(rec.origin.paidAt)} · ${daysBetween(ms(rec.origin.signedAt), ms(rec.origin.paidAt))} days after signature`
                : "Not recorded",
              cite: null,
            },
            {
              label: "Provisioning approved",
              value: rec.origin.activatedAt ? fmtDate(rec.origin.activatedAt) : "Not recorded",
              cite: null,
            },
            {
              label: "Kickoff calls",
              value:
                [rec.origin.kickoffLeadlockAt, rec.origin.kickoffAdsAt].filter(Boolean).length === 2
                  ? `Lead Lock ${fmtShort(rec.origin.kickoffLeadlockAt!)} · Ads ${fmtShort(rec.origin.kickoffAdsAt!)} — ${daysBetween(ms(rec.origin.kickoffLeadlockAt!), ms(rec.origin.kickoffAdsAt!))} days apart`
                  : rec.origin.kickoffAdsAt
                    ? fmtDate(rec.origin.kickoffAdsAt)
                    : "Not booked",
              cite: null,
            },
          ],
  });

  sections.push({
    key: "stands",
    title: "Where it stands",
    blurb: "Derived from the commitment ledger. Nothing here is written by hand.",
    facts: [
      {
        label: "Open commitments",
        value: openCommits.length ? `${openCommits.length} open` : "Nothing outstanding",
        cite: null,
        tone: openCommits.length ? "blue" : "green",
      },
      {
        label: "Overdue",
        value: overdue.length
          ? overdue.map((c) => `${c.text} (${c.owner})`).join(" · ")
          : "None",
        cite: overdue.length ? overdue[0].clickup : null,
        tone: overdue.length ? "red" : "green",
      },
      {
        label: "Blocked",
        value: blocked.length ? blocked.map((c) => c.text).join(" · ") : "None",
        cite: null,
        tone: blocked.length ? "amber" : "green",
      },
      {
        label: "Unacknowledged",
        value: unacked.length
          ? `${unacked.length} — ${unacked.map((c) => c.owner).join(", ")}`
          : "All acknowledged",
        cite: null,
        tone: unacked.length ? "amber" : "green",
      },
      {
        label: "Waiting on them",
        value: theirs.length ? theirs.map((c) => c.text).join(" · ") : "Nothing",
        cite: null,
        tone: theirs.length ? "amber" : "green",
      },
      {
        label: "Last call",
        value: meetingsHealth.lastAt
          ? `${fmtDate(meetingsHealth.lastAt)} · ${fmtRel(meetingsHealth.lastAt, now)}`
          : "No call on record",
        cite: null,
        tone: meetingsHealth.state === "stale" ? "red" : meetingsHealth.state === "aging" ? "amber" : "green",
      },
      {
        label: "Last contact",
        value: commsHealth.lastAt
          ? `${fmtDate(commsHealth.lastAt)} · ${fmtRel(commsHealth.lastAt, now)}`
          : "No contact on record",
        cite: null,
        tone: commsHealth.state === "stale" ? "red" : commsHealth.state === "aging" ? "amber" : "green",
      },
      { label: "Next scheduled", value: client.next, cite: null },
    ],
  });

  sections.push({
    key: "work",
    title: "What we have produced",
    blurb: "Approved assets, newest first. Superseded versions stay on the record but are not live.",
    facts: live.length
      ? live.map((a) => ({
          label: a.title,
          value: `Approved ${fmtDate(a.approvedAt)} by ${a.approvedBy}${a.note ? ` — ${a.note}` : ""}`,
          cite: a.sourceRef,
        }))
      : [{ label: "Nothing approved", value: "No assets on record for this account.", cite: null, tone: "outline" as Tone }],
  });

  sections.push({
    key: "money",
    title: "Money",
    blurb: "The ledger, plus the one number a balance cannot give you: how fast they actually pay.",
    facts: [
      { label: "Collected", value: money(collected), cite: null },
      {
        label: "Outstanding",
        value: outstanding ? money(outstanding) : "Nothing outstanding",
        cite: null,
        tone: outstanding ? "amber" : "green",
      },
      {
        label: "Average days to pay",
        value: avgPay === null ? "No paid invoice yet" : `${avgPay} days from issue`,
        cite: null,
        tone: avgPay !== null && avgPay > 21 ? "amber" : "green",
      },
      {
        label: "Overdue now",
        value: lateBills.length
          ? lateBills.map((i) => `${i.id} · ${money(i.amount)} · ${i.overdueDays}d late`).join(" · ")
          : "None",
        cite: lateBills.length ? lateBills[0].id : null,
        tone: lateBills.length ? "red" : "green",
      },
      {
        label: "Renewal",
        value: rec.terms.renewalAt
          ? ms(rec.terms.renewalAt) < now
            ? `${fmtDate(rec.terms.renewalAt)} — PASSED, undecided`
            : `${fmtDate(rec.terms.renewalAt)} · ${fmtRel(rec.terms.renewalAt, now).replace(" ago", "")} away`
          : "No renewal date — rolling monthly",
        cite: null,
        tone: rec.terms.renewalAt && ms(rec.terms.renewalAt) < now ? "red" : "neutral",
      },
    ],
  });

  const attended = attendance.filter((a) => a.state === "attended").length;
  const missed = attendance.filter((a) => a.state === "missed").length;
  const unmatched = attendance.filter((a) => a.state === "unmatched").length;
  const healthLane = health.find((h) => h.lane === "engagement")!;

  sections.push({
    key: "health",
    title: "Engagement health",
    blurb: "Are they still showing up — and do we trust the record that says so?",
    facts: [
      {
        label: "Attendance",
        value: attendance.length
          ? `${attended} attended · ${missed} missed${unmatched ? ` · ${unmatched} unresolved` : ""}`
          : "Not an Accelerator member — no group sessions",
        cite: null,
        tone: unmatched ? "red" : missed > attended ? "amber" : "green",
      },
      {
        label: "Last activity on this lane",
        value: healthLane.lastAt ? `${fmtRel(healthLane.lastAt, now)} — ${healthLane.note}` : healthLane.note,
        cite: null,
        tone: HEALTH_META[healthLane.state].tone,
      },
      {
        label: "Record confidence",
        value:
          cov.total === 0
            ? "No meeting or commitment rows on this account, so there is nothing to cite either way."
            : `${cov.pct}% of meeting and commitment rows carry a citation (${cov.citable} of ${cov.total}).`,
        cite: null,
        tone:
          cov.total === 0
            ? "outline"
            : cov.pct >= 80
              ? "green"
              : cov.pct >= 50
                ? "amber"
                : "red",
      },
    ],
  });

  sections.push({
    key: "cannot",
    title: "What this record cannot tell you",
    blurb:
      "The honest section. A handover that hides its own holes is worse than no handover — this is where someone taking the account over needs to ask a human.",
    facts: [
      {
        label: "Record begins",
        value: `${fmtDate(rec.backfill.beginsAt)} — ${rec.backfill.summary}`,
        cite: null,
        tone: rec.backfill.mode === "backfilled" ? "green" : "amber",
      },
      ...(rec.backfill.unreachable.length
        ? rec.backfill.unreachable.map((u) => ({
            label: `${u.source} unreachable${u.from ? ` from ${fmtShort(u.from)}` : ""}`,
            value: u.why,
            cite: null,
            tone: "red" as Tone,
          }))
        : [
            {
              label: "No gaps",
              value: "Every connected source returned history for the whole engagement.",
              cite: null,
              tone: "green" as Tone,
            },
          ]),
      ...health
        .filter((h) => h.state === "stale")
        .map((h) => ({
          label: `${h.label} is stale`,
          value: h.note,
          cite: null,
          tone: "amber" as Tone,
        })),
    ],
  });

  return sections;
}

/* ── What to watch ────────────────────────────────────────────── */

export type WatchItem = { text: string; tone: Tone; tab: string };

/** The brief's closing list, and the only part of it that is a judgement.
    Each line names the tab that answers it, so it is a route rather than an
    instruction. */
export function watchList(
  rec: EngagementRecord,
  client: Client,
  now = DEMO_NOW_MS,
): WatchItem[] {
  const out: WatchItem[] = [];
  const commits = COMMITMENTS.filter((c) => c.clientId === client.id);
  const invoices = CLIENT_INVOICES[client.id] ?? [];
  const health = laneHealth(rec, now);

  const overdue = commits.filter((c) => c.state === "overdue");
  if (overdue.length)
    out.push({
      text: `${overdue.length} commitment${overdue.length === 1 ? "" : "s"} past the agreed date — ${overdue.map((c) => c.owner).join(", ")}.`,
      tone: "red",
      tab: "commitments",
    });

  const unacked = commits.filter(
    (c) => c.side === "wia" && c.state !== "done" && c.ack === "none",
  );
  if (unacked.length)
    out.push({
      text: `${unacked.length} action${unacked.length === 1 ? "" : "s"} never acknowledged by the owner.`,
      tone: "amber",
      tab: "commitments",
    });

  const late = invoices.filter((i) => i.state === "overdue");
  if (late.length)
    out.push({
      text: `${late.map((i) => i.id).join(", ")} overdue — the personal follow-up carrying the payment link is drafted, not sent.`,
      tone: "red",
      tab: "money",
    });

  if (rec.terms.renewalAt && ms(rec.terms.renewalAt) < now)
    out.push({
      text: `Renewal date passed on ${fmtDate(rec.terms.renewalAt)} with no decision recorded.`,
      tone: "red",
      tab: "brief",
    });
  else if (rec.terms.renewalAt && ms(rec.terms.renewalAt) - now < 90 * DAY)
    out.push({
      text: `Renewal due ${fmtDate(rec.terms.renewalAt)} — inside the 90-day window.`,
      tone: "amber",
      tab: "brief",
    });

  for (const h of health.filter((x) => x.state === "stale")) {
    out.push({
      text: `${h.label}: ${h.note}`,
      tone: h.blindSources.length ? "amber" : "red",
      tab: h.lane === "meetings" ? "meetings" : h.lane === "comms" ? "timeline" : "spine",
    });
  }

  const superseded = rec.assets.filter((a) => a.supersedes !== null);
  if (superseded.length)
    out.push({
      text: `${superseded.length} asset${superseded.length === 1 ? " has" : "s have"} been superseded — anything drafted against the older version is out of date.`,
      tone: "neutral",
      tab: "spine",
    });

  if (!out.length)
    out.push({
      text: "Nothing has slipped on this account. Next scheduled: " + client.next.toLowerCase() + ".",
      tone: "green",
      tab: "now",
    });

  return out;
}
