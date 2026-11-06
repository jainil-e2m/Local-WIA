/* ────────────────────────────────────────────────────────────────
   Engagement record — the Client Hub's longitudinal corpus.

   WHAT THIS IS. One append-only event log per client, running from the day
   the engagement began to the day you are looking at it. Every other view in
   the Client Hub — Spine, Now, Brief, and the five ledgers — is a projection
   over this log. That is the whole point: the record is connected because it
   is ONE list, not because five lists are drawn next to each other.

   ALL SYNTHETIC, same rule as data/opsHub. Client names, invoice numbers,
   transcript seconds and quotes are invented. The real book lives in ClickUp
   and HighLevel and is deliberately not loaded into a demo environment.

   DATES ARE REAL ISO, AND THAT IS THE POINT. The Ops Hub corpus carries
   display strings — "Today", "2d ago", "Sep 2" — which is why staleness
   cannot be computed there and why a timeline cannot be drawn from it. Every
   event below carries `occurredAt` as a real timestamp. Anything the UI shows
   as "47 days ago" is arithmetic against DEMO_NOW, never a written string.

   DEMO_NOW IS FROZEN, NOT THE WALL CLOCK. It matches DEMO_DATE in
   data/opsHub — Friday 4 September 2026. A demo that reads the real clock
   drifts: "overdue by 3 days" becomes "overdue by 240 days" the next quarter
   and every screenshot in the deck goes stale. Freeze it, and the record
   reads the same in March as it did in September.

   THE RECORD BOUNDARY IS DRAWN, NOT HIDDEN. Each record declares where its
   history actually starts and which sources could not be reached that far
   back. Three real walls show up in the corpus rather than being papered
   over, because each one will be hit in production:

     1. Fathom keys are user-level. Harbor House lost its meeting record the
        month a team member without an authorised key became the recorder.
     2. Zoom cloud recordings age out. Both long-running retainers have
        meetings on record from before retention that carry no transcript,
        so their commitments cite nothing.
     3. A prospect has no engagement to backfill. Magnolia's record begins at
        first contact and its spine is mostly empty — which is the correct
        picture, not a broken one.
   ──────────────────────────────────────────────────────────────── */

import type { SourceKey } from "@/lib/opsHub";

/* ── Frozen clock ─────────────────────────────────────────────── */

/** Friday 4 September 2026, 17:00. Matches DEMO_DATE in data/opsHub. */
export const DEMO_NOW = "2026-09-04T17:00:00";
export const DEMO_NOW_MS = new Date(DEMO_NOW).getTime();

/* ── Lanes ────────────────────────────────────────────────────── */

export type EventLane =
  | "onboarding"
  | "comms"
  | "meetings"
  | "commitments"
  | "work"
  | "money"
  | "engagement";

export type LaneMeta = {
  key: EventLane;
  label: string;
  /** Short form for the spine rail, which is 132px wide. */
  short: string;
  color: string;
  /** Days of silence before this lane reads as stale. Null = never stale
      (onboarding is a period, not a cadence — it does not "go quiet"). */
  expectDays: number | null;
  /** What the lane answers, shown on the spine legend. */
  question: string;
};

/* Lane colours are the WIA ramp already in tailwind.config.js, deepened
   where a 5px mark on white needed the contrast. They are NOT the source
   brand marks — SOURCE_META owns those, and a mark on the spine carries both
   (lane colour for the bar, source dot for the origin). */
export const LANES: LaneMeta[] = [
  {
    key: "onboarding",
    label: "Onboarding & setup",
    short: "Onboarding",
    color: "#3644b8",
    expectDays: null,
    question: "How did this engagement start?",
  },
  {
    key: "comms",
    label: "Client communication",
    short: "Comms",
    color: "#5070ff",
    expectDays: 7,
    question: "When did we last actually speak to them?",
  },
  {
    key: "meetings",
    label: "Calls & recordings",
    short: "Meetings",
    color: "#3a3f96",
    expectDays: 35,
    question: "What was said, and can we still hear it?",
  },
  {
    key: "commitments",
    label: "Promises made",
    short: "Commitments",
    color: "#7d4a0f",
    expectDays: 30,
    question: "What did we say we would do?",
  },
  {
    key: "work",
    label: "Work delivered",
    short: "Work",
    color: "#16724c",
    expectDays: 45,
    question: "What have we actually produced for them?",
  },
  {
    key: "money",
    label: "Invoices & terms",
    short: "Money",
    color: "#87725f",
    expectDays: 35,
    question: "Are they paying, and on what terms?",
  },
  {
    key: "engagement",
    label: "Engagement health",
    short: "Health",
    color: "#a83323",
    expectDays: 21,
    question: "Are they still showing up?",
  },
];

export const LANE_META: Record<EventLane, LaneMeta> = Object.fromEntries(
  LANES.map((l) => [l.key, l]),
) as Record<EventLane, LaneMeta>;

/* ── Event kinds ──────────────────────────────────────────────── */

export type EventKind =
  /* onboarding */
  | "contract_signed"
  | "invoice_paid_first"
  | "pair_matched"
  | "provisioning_approved"
  | "clickup_created"
  | "drive_created"
  | "welcome_sent"
  | "slack_created"
  | "kickoff_booked"
  | "kickoff_held"
  /* comms */
  | "email_in"
  | "email_out"
  | "slack_thread"
  | "recap_sent"
  | "escalation"
  /* meetings */
  | "call_held"
  | "transcript_filed"
  | "transcript_missing"
  | "recording_expired"
  | "no_show"
  /* commitments */
  | "commitment_made"
  | "commitment_delivered"
  | "commitment_overdue"
  | "commitment_blocked"
  | "ack_missing"
  /* work */
  | "campaign_launched"
  | "asset_approved"
  | "revision_requested"
  | "report_delivered"
  /* money */
  | "invoice_issued"
  | "invoice_paid"
  | "invoice_overdue"
  | "reminder_sent"
  | "tier_changed"
  | "renewal"
  /* engagement */
  | "session_attended"
  | "session_missed"
  | "attendance_unmatched"
  | "risk_raised"
  | "risk_cleared"
  | "contact_changed";

/** Rendering weight on the spine. `major` gets a labelled mark, `normal` a
    dot, `minor` a tick. Nothing is hidden at any weight — minor rows still
    appear in the list below the spine and in every ledger. */
export type EventWeight = "major" | "normal" | "minor";

export type EventSide = "wia" | "client" | "system";

export type EngagementEvent = {
  id: string;
  clientId: string;
  /** When it happened. */
  occurredAt: string;
  lane: EventLane;
  kind: EventKind;
  source: SourceKey;
  side: EventSide;
  actor: string;
  title: string;
  detail: string | null;
  /** Transcript second, message id, invoice id — whatever makes this
      checkable. NULL IS MEANINGFUL: it says the fact is real but uncitable,
      and the UI renders it as an explicit dash rather than hiding the row.
      Never populate this with something derived; a fabricated citation is
      worse than an admitted gap. */
  citation: string | null;
  /** Deep-link label back into the source system. */
  sourceRef: string | null;
  weight: EventWeight;
};

/* ── Phases ───────────────────────────────────────────────────── */

export type PhaseKey =
  | "prospect"
  | "onboarding"
  | "launch"
  | "steady"
  | "at_risk"
  | "renewal";

export const PHASE_META: Record<PhaseKey, { label: string; color: string }> = {
  prospect: { label: "Prospect", color: "#9da2b1" },
  onboarding: { label: "Onboarding", color: "#3644b8" },
  launch: { label: "Launch", color: "#5070ff" },
  steady: { label: "Steady state", color: "#16724c" },
  at_risk: { label: "At risk", color: "#a83323" },
  renewal: { label: "Renewal window", color: "#7d4a0f" },
};

export type Phase = {
  key: PhaseKey;
  startsAt: string;
  /** Null = still current. Derived as the next phase's start when rendering. */
  note: string;
};

/* ── Approved assets ──────────────────────────────────────────── */

export type AssetKind =
  | "landing-page"
  | "ad-copy"
  | "creative"
  | "strategy"
  | "report";

export const ASSET_KIND_LABEL: Record<AssetKind, string> = {
  "landing-page": "Landing page",
  "ad-copy": "Ad copy",
  creative: "Creative",
  strategy: "Strategy",
  report: "Report",
};

export type ApprovedAsset = {
  id: string;
  clientId: string;
  kind: AssetKind;
  title: string;
  approvedAt: string;
  approvedBy: string;
  source: SourceKey;
  sourceRef: string;
  /** Asset id this replaced. The chain is what makes "what is live today"
      answerable without reading the whole folder. */
  supersedes: string | null;
  note: string | null;
};

/* ── People, with validity ────────────────────────────────────── */

/* A contact who left in March must not retro-sign every 2025 event. Fields
   that move over an engagement carry validity rather than overwriting, which
   is the difference between a record and a snapshot. */
export type PersonRecord = {
  name: string;
  role: string;
  email: string;
  side: EventSide;
  validFrom: string;
  validTo: string | null;
};

/* ── Backfill declaration ─────────────────────────────────────── */

export type BackfillMode = "backfilled" | "from-connection" | "no-engagement";

export type Backfill = {
  mode: BackfillMode;
  /** Earliest event this record actually holds. The spine's left edge. */
  beginsAt: string;
  summary: string;
  /** Sources that returned history this far back. */
  reachable: SourceKey[];
  /** Sources that did not, and the production reason why. Shown on screen —
      an unreachable source is a hole in the record, not a footnote. */
  unreachable: { source: SourceKey; from: string | null; why: string }[];
};

/* ── The record ───────────────────────────────────────────────── */

export type EngagementTerms = {
  tier: string;
  offers: string[];
  monthly: number | null;
  contractRef: string | null;
  renewalAt: string | null;
};

/* Origin comes straight from the /onboarding console's own fields, which are
   the only real ISO timestamps anywhere in this build. Joining projectKey to
   clientId is what gives the spine a left edge without inventing one. */
export type EngagementOrigin = {
  projectKey: string | null;
  signedAt: string | null;
  paidAt: string | null;
  pairedAt: string | null;
  activatedAt: string | null;
  /** Two anchors, not one — on the live client the calls were 34 days apart. */
  kickoffLeadlockAt: string | null;
  kickoffAdsAt: string | null;
};

export type EngagementRecord = {
  clientId: string;
  origin: EngagementOrigin;
  terms: EngagementTerms;
  backfill: Backfill;
  phases: Phase[];
  people: PersonRecord[];
  assets: ApprovedAsset[];
  events: EngagementEvent[];
};

/* ────────────────────────────────────────────────────────────────
   Compact authoring form.

   A row is [date, lane, kind, source, side, actor, title, detail, citation,
   weight]. Written as tuples because 150 events in object literal form is
   unreadable and unreviewable; `expand` gives them ids and a clientId.
   ──────────────────────────────────────────────────────────────── */

type Row = [
  string, // occurredAt
  EventLane,
  EventKind,
  SourceKey,
  EventSide,
  string, // actor
  string, // title
  string | null, // detail
  string | null, // citation
  EventWeight?,
];

function expand(clientId: string, rows: Row[]): EngagementEvent[] {
  return rows
    .map(([occurredAt, lane, kind, source, side, actor, title, detail, citation, weight], i) => ({
      id: `${clientId}-e${String(i + 1).padStart(3, "0")}`,
      clientId,
      occurredAt,
      lane,
      kind,
      source,
      side,
      actor,
      title,
      detail,
      citation,
      sourceRef: refFor(source, kind),
      weight: weight ?? "normal",
    }))
    .sort((a, b) => a.occurredAt.localeCompare(b.occurredAt));
}

/* The link label a row carries back to its origin system. Deliberately a
   LABEL, not a URL: this build has no connector, and a fake href that 404s
   in front of a client is worse than an honest "where to look". */
function refFor(source: SourceKey, kind: EventKind): string | null {
  if (kind === "recording_expired" || kind === "transcript_missing") return null;
  switch (source) {
    case "gmail":
      return "Open thread in Gmail";
    case "slack":
      return "Open in Slack";
    case "clickup":
      return "Open task in ClickUp";
    case "zoom":
      return "Open recording in Zoom";
    case "fathom":
      return "Open in Fathom";
    case "drive":
      return "Open file in Drive";
    case "highlevel":
      return "Open in HighLevel";
    default:
      return null;
  }
}

/* ── Recurring cadence ────────────────────────────────────────────
   An 18-month retainer does not send four emails and two invoices. The
   authored rows above are the events that MEAN something — a tier change, a
   contact handover, a commitment, a renewal. The rhythm between them is
   regular by definition, so it is generated rather than typed: a monthly
   retainer payment and a monthly recap, which is what those lanes actually
   look like on a healthy account.

   This matters visually, not just numerically. Without the rhythm, Bloom's
   comms lane is a single hatched gap running the width of the spine, and the
   reference account reads as abandoned — the exact opposite of what it is
   there to show. Silence has to be rare for it to mean anything.

   THE GENERATED ROWS CARRY NO INVOICE NUMBER. Inventing a sequence alongside
   the authored INV-207 would produce a ledger whose numbers run backwards
   through time, and someone would rightly notice. They cite the HighLevel
   period reference instead, which is what a real monthly charge is keyed on. */

const pad = (n: number) => String(n).padStart(2, "0");

const at = (d: Date, time = "09:00:00") =>
  `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${time}`;

const period = (d: Date) => `HL-${d.getFullYear()}-${pad(d.getMonth() + 1)}`;

const thread = (d: Date, suffix = "") =>
  `thread-${d.getFullYear()}-${pad(d.getMonth() + 1)}${suffix}`;

/** Walks month by month from `from` to `to` inclusive, emitting whatever
    `build` returns for each. */
function monthly(from: string, to: string, build: (d: Date, i: number) => Row[]): Row[] {
  const out: Row[] = [];
  const end = new Date(to);
  const d = new Date(from);
  let i = 0;
  while (d.getTime() <= end.getTime()) {
    out.push(...build(new Date(d), i));
    d.setMonth(d.getMonth() + 1);
    i += 1;
  }
  return out;
}

/** The monthly retainer charge, on the money lane. */
const retainer = (d: Date, payer: string, amount: string): Row => [
  at(d, "09:00:00"),
  "money",
  "invoice_paid",
  "highlevel",
  "client",
  payer,
  `Monthly retainer paid — ${amount}`,
  null,
  period(d),
  "minor",
];

/** The recap that follows each monthly call, on the comms lane. */
const recap = (d: Date, sender: string): Row => [
  at(d, "16:30:00"),
  "comms",
  "recap_sent",
  "gmail",
  "wia",
  sender,
  "Monthly recap sent",
  null,
  thread(d),
  "minor",
];

/** An inbound client thread — the traffic between the scheduled beats. */
const inbound = (d: Date, sender: string, subject: string): Row => [
  at(d, "11:15:00"),
  "comms",
  "email_in",
  "gmail",
  "client",
  sender,
  subject,
  null,
  thread(d, "-b"),
  "minor",
];

const shift = (d: Date, days: number) => {
  const out = new Date(d);
  out.setDate(out.getDate() + days);
  return out;
};

/** A promise made on a monthly call and closed before the next one. Only
    generated for months whose transcript survived — which is why Bloom's and
    Rosewood's commitment lanes start where Zoom's retention window does, and
    Harbor's stops where its Fathom key does. The empty stretch either side is
    the coverage story told on a second lane. */
const promise = (d: Date, i: number, owner: string, text: string): Row[] => {
  const cite = `${pad(12 + (i % 26))}:${pad((i * 7) % 60)}`;
  const done = shift(d, 9 + (i % 5));
  return [
    [at(d, "09:30:00"), "commitments", "commitment_made", "zoom", "wia", owner, text, "Agreed on the monthly call.", cite, "minor"],
    [at(done, "15:00:00"), "commitments", "commitment_delivered", "clickup", "wia", owner, `${text} — delivered`, null, cite, "minor"],
  ];
};

/** The monthly report pack. It is the largest recurring cost in the whole
    scope (18-24 hrs/month), so a record of the engagement that did not show
    it going out every month would be missing the work itself. */
const report = (d: Date): Row => [
  at(d, "11:00:00"),
  "work",
  "report_delivered",
  "drive",
  "wia",
  "Tina",
  "Monthly report pack delivered",
  null,
  `report-${d.getFullYear()}-${pad(d.getMonth() + 1)}`,
  "minor",
];

/* ════════════════════════════════════════════════════════════════
   BLOOM MANOR — the reference record.

   18 months, healthy, fully backfilled, and the one account where the
   recent meeting transcript came back. Everything else in the corpus is a
   degraded version of this one, so a reviewer can see what "complete" looks
   like before seeing what a hole looks like.
   ════════════════════════════════════════════════════════════════ */

const BLOOM: EngagementRecord = {
  clientId: "bloom",
  origin: {
    projectKey: "bloom-manor",
    signedAt: "2025-03-14T16:22:00",
    paidAt: "2025-03-14T18:05:00",
    pairedAt: "2025-03-14T18:07:00",
    activatedAt: "2025-03-17T09:15:00",
    kickoffLeadlockAt: "2025-03-25T15:00:00",
    kickoffAdsAt: "2025-04-07T15:00:00",
  },
  terms: {
    tier: "Elevate",
    offers: ["Elevate retainer"],
    monthly: 2400,
    contractRef: "Dubsado · Elevate 12mo",
    renewalAt: "2027-03-14",
  },
  backfill: {
    mode: "backfilled",
    beginsAt: "2025-02-10T11:04:00",
    summary:
      "Backfilled to the first inbound enquiry, 32 days before signature. Gmail, ClickUp, Drive and HighLevel all returned full history.",
    reachable: ["gmail", "clickup", "drive", "highlevel", "zoom", "slack"],
    unreachable: [
      {
        source: "zoom",
        from: "2025-09-04",
        why: "Cloud recordings age out of the retention window. Calls before September 2025 are on record from the calendar and the recap, but the recording and transcript are gone — so their commitments cite nothing.",
      },
    ],
  },
  phases: [
    { key: "prospect", startsAt: "2025-02-10T11:04:00", note: "Inbound enquiry from the venue directory" },
    { key: "onboarding", startsAt: "2025-03-14T16:22:00", note: "Contract signed and first invoice paid the same evening" },
    { key: "launch", startsAt: "2025-04-07T15:00:00", note: "Ads kickoff call — first campaigns live 9 days later" },
    { key: "steady", startsAt: "2025-05-19T09:00:00", note: "Monthly strategy cadence from here" },
  ],
  people: [
    { name: "Sarah Mitchell", role: "Owner", email: "sarah@bloommanor.com", side: "client", validFrom: "2025-02-10", validTo: null },
    { name: "Dominic Reyes", role: "Events manager", email: "dominic@bloommanor.com", side: "client", validFrom: "2025-06-01", validTo: "2026-04-30" },
    { name: "Whitney", role: "Owner · approver", email: "whitney@wia", side: "wia", validFrom: "2025-03-14", validTo: null },
    { name: "Jacqueline", role: "Creative", email: "jacqueline@wia", side: "wia", validFrom: "2025-04-07", validTo: null },
    { name: "Carmen", role: "Paid media", email: "carmen@wia", side: "wia", validFrom: "2025-04-07", validTo: null },
  ],
  assets: [
    { id: "bloom-a1", clientId: "bloom", kind: "strategy", title: "Messaging & positioning — Bloom Manor", approvedAt: "2025-04-02T14:30:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Bloom Manor / Strategy", supersedes: null, note: "The positioning every later asset is written against." },
    { id: "bloom-a2", clientId: "bloom", kind: "landing-page", title: "Enquiry landing page v1", approvedAt: "2025-04-16T11:00:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Bloom Manor / Landing pages", supersedes: null, note: null },
    { id: "bloom-a3", clientId: "bloom", kind: "ad-copy", title: "Google Search — core ad group copy", approvedAt: "2025-04-16T11:20:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Bloom Manor / Ad copy", supersedes: null, note: null },
    { id: "bloom-a4", clientId: "bloom", kind: "creative", title: "Autumn testimonial set (6 statics)", approvedAt: "2025-09-22T10:10:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Bloom Manor / Creative", supersedes: null, note: null },
    { id: "bloom-a5", clientId: "bloom", kind: "landing-page", title: "Enquiry landing page v2 — tour-first CTA", approvedAt: "2026-02-11T15:45:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Bloom Manor / Landing pages", supersedes: "bloom-a2", note: "Raised the barrier deliberately — fewer enquiries, better qualified." },
    { id: "bloom-a6", clientId: "bloom", kind: "creative", title: "2026 spring gallery set (9 statics)", approvedAt: "2026-05-06T09:30:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Bloom Manor / Creative", supersedes: "bloom-a4", note: null },
    { id: "bloom-a7", clientId: "bloom", kind: "strategy", title: "Messaging refresh — 2026 season", approvedAt: "2026-06-18T13:00:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Bloom Manor / Strategy", supersedes: "bloom-a1", note: "Supersedes the 2025 positioning. Anything drafted against the old doc is out of date." },
  ],
  events: expand("bloom", [
    /* The retainer cadence stops in June because July, August and September
       are named invoices in CLIENT_INVOICES — the record must show the rows
       the Money tab shows, not a generic charge beside them. */
    ...monthly("2025-05-14", "2026-06-14", (d) => [retainer(d, "Sarah Mitchell", "$2,400")]),
    ...monthly("2025-05-16", "2026-07-16", (d) => [
      recap(d, "Gisselle"),
      inbound(shift(d, 9), "Sarah Mitchell", "Question on this month's creative"),
    ]),
    ["2026-07-05T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-195 issued — $2,400", "July retainer.", "INV-195", "minor"],
    ["2026-07-09T11:40:00", "money", "invoice_paid", "highlevel", "client", "Sarah Mitchell", "INV-195 paid", "4 days from issue.", "INV-195", "minor"],
    ...monthly("2025-06-05", "2026-08-05", (d) => [report(d)]),
    /* Starts October 2025, not April: the calls before that are on record but
       their recordings aged out, so nothing was extracted from them. */
    ...monthly("2025-10-20", "2026-08-17", (d, i) =>
      promise(d, i, i % 2 ? "Carmen" : "Jacqueline", "Action from the monthly review"),
    ),
    ["2025-02-10T11:04:00", "comms", "email_in", "gmail", "client", "Sarah Mitchell", "Inbound enquiry from the venue directory", "Asked for pricing and what a 90-day test would look like.", "msg-8841", "major"],
    ["2025-02-19T15:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Discovery call", "45 min. Venue does 40 weddings a year, wants to fill midweek.", null, "normal"],
    ["2025-02-19T16:40:00", "meetings", "recording_expired", "zoom", "system", "Zoom", "Recording no longer available", "Past the cloud-recording retention window. The call is on record; the audio is not.", null, "minor"],
    ["2025-02-24T10:00:00", "comms", "email_out", "gmail", "wia", "Whitney", "Elevate proposal sent", "12-month Elevate retainer at $2,400/mo.", "msg-8903", "normal"],
    ["2025-03-14T16:22:00", "onboarding", "contract_signed", "gmail", "client", "Sarah Mitchell", "Contract signed", "Dubsado signature alert forwarded to the shared inbox.", "alert-sig-2211", "major"],
    ["2025-03-14T18:05:00", "onboarding", "invoice_paid_first", "highlevel", "client", "Sarah Mitchell", "First invoice paid — $2,400", "Paid 1h 43m after signature.", "INV-101", "major"],
    ["2025-03-14T18:07:00", "onboarding", "pair_matched", "aihq", "system", "AI HQ", "Signature and payment paired to one client", "Both halves matched on fingerprint; the provisioning draft opened.", null, "minor"],
    ["2025-03-17T09:15:00", "onboarding", "provisioning_approved", "aihq", "wia", "Gisselle", "Provisioning batch approved", "42 tasks across 2 ClickUp lists, 1 excluded by the reviewer.", null, "normal"],
    ["2025-03-17T09:22:00", "onboarding", "clickup_created", "clickup", "system", "AI HQ", "ClickUp lists created", "Bloom Manor / Lead Lock + Bloom Manor / Ads.", null, "minor"],
    ["2025-03-17T09:24:00", "onboarding", "drive_created", "drive", "system", "AI HQ", "Drive client folder mapped", "Filed under Clients / Bloom Manor.", null, "minor"],
    ["2025-03-17T09:31:00", "onboarding", "welcome_sent", "gmail", "wia", "Gisselle", "Welcome email sent", "Approved by Whitney before it went.", "msg-9014", "normal"],
    ["2025-03-17T09:40:00", "onboarding", "slack_created", "slack", "system", "AI HQ", "Slack channel created", "#client-bloom-manor, 4 members.", null, "minor"],
    ["2025-03-19T11:00:00", "onboarding", "kickoff_booked", "highlevel", "client", "Sarah Mitchell", "Lead Lock kickoff booked", "Booked for 25 March.", null, "minor"],
    ["2025-03-25T15:00:00", "onboarding", "kickoff_held", "zoom", "wia", "Whitney", "Lead Lock kickoff call held", "Access handover and account audit.", null, "major"],
    ["2025-04-02T14:30:00", "work", "asset_approved", "drive", "wia", "Whitney", "Messaging & positioning approved", "The document every later draft is written against.", "drive-str-01", "major"],
    ["2025-04-07T15:00:00", "onboarding", "kickoff_held", "zoom", "wia", "Whitney", "Ads kickoff call held", "13 days after the Lead Lock call — two anchors, not one.", null, "major"],
    ["2025-04-14T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-108 issued — $2,400", "April retainer.", "INV-108", "minor"],
    ["2025-04-16T11:00:00", "work", "asset_approved", "drive", "wia", "Whitney", "Landing page v1 approved", null, "drive-lp-01", "normal"],
    ["2025-04-16T11:20:00", "work", "asset_approved", "drive", "wia", "Whitney", "Google Search ad copy approved", null, "drive-copy-01", "normal"],
    ["2025-04-16T16:30:00", "work", "campaign_launched", "clickup", "wia", "Carmen", "Google Search campaigns live", "Three ad groups, midweek-weighted.", "CU-3312", "major"],
    ["2025-04-18T10:12:00", "money", "invoice_paid", "highlevel", "client", "Sarah Mitchell", "INV-108 paid", "4 days from issue.", "INV-108", "minor"],
    ["2025-05-19T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "First monthly strategy call", "Moved to a monthly cadence from here.", null, "normal"],
    ["2025-06-01T09:00:00", "engagement", "contact_changed", "highlevel", "client", "Sarah Mitchell", "Dominic Reyes added as events manager", "Second contact on the account.", null, "minor"],
    ["2025-06-16T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, null, "normal"],
    ["2025-07-21T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, null, "normal"],
    ["2025-08-18T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, null, "normal"],
    ["2025-09-15T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", "First call inside the Zoom retention window — recording and transcript both held.", "14:20", "normal"],
    ["2025-09-22T10:10:00", "work", "asset_approved", "drive", "wia", "Whitney", "Autumn testimonial creative approved", "Six statics.", "drive-cr-01", "normal"],
    ["2025-10-20T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "09:41", "normal"],
    ["2025-11-17T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", "Peak-season review.", "22:08", "normal"],
    ["2025-12-15T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "18:55", "normal"],
    ["2026-01-19T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", "2026 planning.", "31:12", "normal"],
    ["2026-02-11T15:45:00", "work", "asset_approved", "drive", "wia", "Whitney", "Landing page v2 approved — tour-first CTA", "Supersedes v1. Lower opt-in rate on purpose.", "drive-lp-02", "major"],
    ["2026-02-16T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "12:37", "normal"],
    ["2026-03-14T09:00:00", "money", "renewal", "highlevel", "client", "Sarah Mitchell", "Renewed for a second 12 months", "No change to tier or rate.", "INV-188", "major"],
    ["2026-03-16T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "08:04", "normal"],
    ["2026-04-20T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "25:30", "normal"],
    ["2026-04-30T17:00:00", "engagement", "contact_changed", "highlevel", "client", "Sarah Mitchell", "Dominic Reyes left the venue", "Back to a single contact. Threads addressed to him stop here.", null, "minor"],
    ["2026-05-06T09:30:00", "work", "asset_approved", "drive", "wia", "Whitney", "Spring gallery creative approved", "Nine statics, supersedes the autumn set.", "drive-cr-02", "normal"],
    ["2026-05-18T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "16:44", "normal"],
    ["2026-06-15T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "11:02", "normal"],
    ["2026-06-18T13:00:00", "work", "asset_approved", "drive", "wia", "Whitney", "Messaging refresh approved — 2026 season", "Supersedes the 2025 positioning document.", "drive-str-02", "major"],
    ["2026-07-20T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "19:23", "normal"],
    ["2026-08-05T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-201 issued — $2,400", "August retainer.", "INV-201", "minor"],
    ["2026-08-09T14:02:00", "money", "invoice_paid", "highlevel", "client", "Sarah Mitchell", "INV-201 paid", "4 days from issue — consistent with the account average.", "INV-201", "minor"],
    ["2026-08-17T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "07:58", "normal"],
    ["2026-09-01T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-207 issued — $2,400", "September retainer, due 15 Sep.", "INV-207", "minor"],
    ["2026-09-02T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", "48 min. Transcript returned in full — every commitment below cites a second.", "00:00", "major"],
    ["2026-09-02T09:24:00", "commitments", "commitment_made", "zoom", "wia", "Whitney", "Deliver the revised landing page", "Owner Jacqueline, due 5 Sep.", "24:18", "normal"],
    ["2026-09-02T09:31:00", "commitments", "commitment_made", "zoom", "wia", "Whitney", "Update the testimonial creative", "Owner Jacqueline, due 3 Sep.", "31:05", "normal"],
    ["2026-09-02T09:31:00", "commitments", "commitment_made", "zoom", "wia", "Whitney", "Review keyword exclusions before the next flight", "Owner Carmen, due 4 Sep.", "31:05", "normal"],
    ["2026-09-02T09:42:00", "commitments", "commitment_made", "zoom", "wia", "Whitney", "Send the call recap the same day", "Owner Gisselle, due 2 Sep.", "42:18", "normal"],
    ["2026-09-02T09:47:00", "commitments", "commitment_made", "zoom", "client", "Sarah Mitchell", "Send the October gallery assets", "Client-side, due 5 Sep. Blocks the testimonial creative set.", "47:02", "normal"],
    ["2026-09-02T14:10:00", "meetings", "transcript_filed", "drive", "system", "AI HQ", "Recording, transcript and summary filed", "Clients / Bloom Manor / Meetings / 2026-09-02.", "drive-mtg-0902", "minor"],
    ["2026-09-02T14:30:00", "comms", "recap_sent", "gmail", "wia", "Gisselle", "Call recap sent", "Sent after Whitney approved the draft.", "msg-11902", "normal"],
    ["2026-09-03T11:00:00", "commitments", "commitment_overdue", "clickup", "wia", "Jacqueline", "Testimonial creative now overdue", "Due 3 Sep, still Open.", "CU-4410", "major"],
    ["2026-09-03T11:05:00", "commitments", "ack_missing", "slack", "wia", "Jacqueline", "No acknowledgement after 23 hours", "Message delivered to #client-bloom-manor, no reaction and no reply.", null, "major"],
    ["2026-09-04T08:40:00", "comms", "email_in", "gmail", "client", "Sarah Mitchell", "Any update on the landing page?", "Reply due — 2h old at time of view.", "msg-11988", "major"],
    ["2026-09-04T09:15:00", "comms", "slack_thread", "slack", "wia", "Jacqueline", "Final QA confirmed in channel", "Landing page moved out of Open yesterday.", null, "normal"],
  ]),
};

/* ════════════════════════════════════════════════════════════════
   ROSEWOOD VENUE — the long one, and the one that changed shape.

   22 months, a mid-engagement tier change, a contact handover, and money
   that has started slipping. It is the account where the record earns its
   keep: none of that history is legible from any single system.
   ════════════════════════════════════════════════════════════════ */

const ROSEWOOD: EngagementRecord = {
  clientId: "rosewood",
  origin: {
    projectKey: "rosewood-venue",
    signedAt: "2024-11-08T14:10:00",
    paidAt: "2024-11-11T10:02:00",
    pairedAt: "2024-11-11T10:05:00",
    activatedAt: "2024-11-12T09:00:00",
    kickoffLeadlockAt: "2024-11-19T14:00:00",
    kickoffAdsAt: "2024-12-03T14:00:00",
  },
  terms: {
    tier: "Amplify",
    offers: ["Elevate retainer", "Amplify upgrade"],
    monthly: 1850,
    contractRef: "Dubsado · Elevate 12mo → Amplify",
    renewalAt: "2026-11-08",
  },
  backfill: {
    mode: "backfilled",
    beginsAt: "2024-10-15T09:30:00",
    summary:
      "Backfilled to first contact, 24 days before signature. The oldest record in the book — and the one with the largest recording gap.",
    reachable: ["gmail", "clickup", "drive", "highlevel", "slack"],
    unreachable: [
      {
        source: "zoom",
        from: "2025-09-04",
        why: "Cloud recordings age out. Eleven monthly calls from the first year are on record from the calendar and recaps, with no recording and no transcript behind them.",
      },
      {
        source: "slack",
        from: "2024-11-08",
        why: "#client-rosewood is a private channel and AI HQ is not a member. Client-side Slack on this account is invisible to the record.",
      },
    ],
  },
  phases: [
    { key: "prospect", startsAt: "2024-10-15T09:30:00", note: "Referral from an existing venue client" },
    { key: "onboarding", startsAt: "2024-11-08T14:10:00", note: "Signature and payment three days apart" },
    { key: "launch", startsAt: "2024-12-03T14:00:00", note: "Ads kickoff, campaigns live before the new year" },
    { key: "steady", startsAt: "2025-01-20T09:00:00", note: "Monthly cadence, Elevate tier" },
    { key: "renewal", startsAt: "2026-08-08T09:00:00", note: "Renewal window opened 90 days out — decision due 8 Nov" },
  ],
  people: [
    { name: "Priya Raman", role: "Marketing lead", email: "priya@rosewoodvenue.com", side: "client", validFrom: "2024-10-15", validTo: "2025-07-31" },
    { name: "Dana Whitfield", role: "Owner", email: "dana@rosewoodvenue.com", side: "client", validFrom: "2025-08-01", validTo: null },
    { name: "Whitney", role: "Owner · approver", email: "whitney@wia", side: "wia", validFrom: "2024-11-08", validTo: null },
    { name: "Carmen", role: "Paid media", email: "carmen@wia", side: "wia", validFrom: "2024-12-03", validTo: null },
  ],
  assets: [
    { id: "rose-a1", clientId: "rosewood", kind: "strategy", title: "Messaging & positioning — Rosewood", approvedAt: "2024-11-27T10:00:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Rosewood Venue / Strategy", supersedes: null, note: "Written for Priya. Never refreshed after the contact changed." },
    { id: "rose-a2", clientId: "rosewood", kind: "landing-page", title: "Enquiry landing page v1", approvedAt: "2024-12-10T11:30:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Rosewood Venue / Landing pages", supersedes: null, note: null },
    { id: "rose-a3", clientId: "rosewood", kind: "ad-copy", title: "Meta prospecting — copy set A", approvedAt: "2025-01-14T09:45:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Rosewood Venue / Ad copy", supersedes: null, note: null },
    { id: "rose-a4", clientId: "rosewood", kind: "creative", title: "Winter open-day creative", approvedAt: "2025-10-08T14:00:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Rosewood Venue / Creative", supersedes: null, note: null },
    { id: "rose-a5", clientId: "rosewood", kind: "landing-page", title: "Enquiry landing page v2 — Amplify build", approvedAt: "2025-09-24T16:00:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Rosewood Venue / Landing pages", supersedes: "rose-a2", note: "Rebuilt for the Amplify upgrade." },
    { id: "rose-a6", clientId: "rosewood", kind: "ad-copy", title: "Meta prospecting — copy set B", approvedAt: "2026-03-03T10:15:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Rosewood Venue / Ad copy", supersedes: "rose-a3", note: null },
  ],
  events: expand("rosewood", [
    ...monthly("2024-12-11", "2026-06-11", (d) => {
      const payer = d.getTime() < new Date("2025-08-01").getTime() ? "Priya Raman" : "Dana Whitfield";
      /* The retainer steps up with the Amplify upgrade on 1 Sep 2025 — the
         money lane has to show the change, not just the invoice that named it. */
      const amount = d.getTime() < new Date("2025-09-01").getTime() ? "$1,450" : "$1,850";
      return [
        ...(d.getTime() <= new Date("2026-05-11").getTime() ? [retainer(d, payer, amount)] : []),
        recap(shift(d, 3), "Gisselle"),
        ...(d.getMonth() % 2 === 0
          ? [inbound(shift(d, 14), payer, "Question on the current flight")]
          : []),
      ];
    }),
    ["2026-06-24T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-190 issued — $1,850", "June retainer.", "INV-190", "minor"],
    ["2026-06-30T14:05:00", "money", "invoice_paid", "highlevel", "client", "Dana Whitfield", "INV-190 paid", "6 days from issue.", "INV-190", "minor"],
    ...monthly("2025-02-06", "2026-07-06", (d) => [report(d)]),
    ...monthly("2025-10-20", "2026-06-20", (d, i) =>
      promise(d, i, "Carmen", "Action from the monthly review"),
    ),
    ["2024-10-15T09:30:00", "comms", "email_in", "gmail", "client", "Priya Raman", "Referral introduction", "Referred by an existing venue client.", "msg-6620", "major"],
    ["2024-10-29T14:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Discovery call", null, null, "normal"],
    ["2024-10-29T15:30:00", "meetings", "recording_expired", "zoom", "system", "Zoom", "Recording no longer available", "Past retention.", null, "minor"],
    ["2024-11-08T14:10:00", "onboarding", "contract_signed", "gmail", "client", "Priya Raman", "Contract signed", "Elevate, 12 months.", "alert-sig-1904", "major"],
    ["2024-11-11T10:02:00", "onboarding", "invoice_paid_first", "highlevel", "client", "Priya Raman", "First invoice paid — $1,450", "Three days after signature.", "INV-044", "major"],
    ["2024-11-12T09:00:00", "onboarding", "provisioning_approved", "aihq", "wia", "Gisselle", "Provisioning batch approved", "38 tasks, 1 ClickUp list.", null, "normal"],
    ["2024-11-12T09:12:00", "onboarding", "clickup_created", "clickup", "system", "AI HQ", "ClickUp list created", "Rosewood Venue / Lead Lock.", null, "minor"],
    ["2024-11-12T09:15:00", "onboarding", "drive_created", "drive", "system", "AI HQ", "Drive client folder mapped", null, null, "minor"],
    ["2024-11-12T09:20:00", "onboarding", "welcome_sent", "gmail", "wia", "Gisselle", "Welcome email sent", null, "msg-6701", "normal"],
    ["2024-11-19T14:00:00", "onboarding", "kickoff_held", "zoom", "wia", "Whitney", "Lead Lock kickoff call held", null, null, "major"],
    ["2024-11-27T10:00:00", "work", "asset_approved", "drive", "wia", "Whitney", "Messaging & positioning approved", "Written against Priya's brief.", "drive-str-r1", "major"],
    ["2024-12-03T14:00:00", "onboarding", "kickoff_held", "zoom", "wia", "Whitney", "Ads kickoff call held", null, null, "major"],
    ["2024-12-10T11:30:00", "work", "asset_approved", "drive", "wia", "Whitney", "Landing page v1 approved", null, "drive-lp-r1", "normal"],
    ["2024-12-18T10:00:00", "work", "campaign_launched", "clickup", "wia", "Carmen", "Meta prospecting live", null, "CU-2201", "major"],
    ["2025-01-14T09:45:00", "work", "asset_approved", "drive", "wia", "Whitney", "Meta copy set A approved", null, "drive-copy-r1", "normal"],
    ["2025-01-20T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "First monthly strategy call", null, null, "normal"],
    ["2025-02-17T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, null, "normal"],
    ["2025-03-17T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, null, "normal"],
    ["2025-04-21T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, null, "normal"],
    ["2025-05-19T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, null, "normal"],
    ["2025-06-16T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, null, "normal"],
    ["2025-07-21T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", "Priya's last call.", null, "normal"],
    ["2025-07-31T17:00:00", "engagement", "contact_changed", "highlevel", "client", "Dana Whitfield", "Priya Raman left — Dana Whitfield took over", "The positioning document was written for Priya and has never been refreshed.", null, "major"],
    ["2025-08-18T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", "First call with Dana.", null, "normal"],
    ["2025-09-01T11:00:00", "money", "tier_changed", "highlevel", "client", "Dana Whitfield", "Upgraded from Elevate to Amplify", "Monthly moved from $1,450 to $1,850.", "INV-131", "major"],
    ["2025-09-15T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", "First call inside the Zoom retention window.", "13:48", "normal"],
    ["2025-09-24T16:00:00", "work", "asset_approved", "drive", "wia", "Whitney", "Landing page v2 approved — Amplify build", "Supersedes v1.", "drive-lp-r2", "major"],
    ["2025-10-08T14:00:00", "work", "asset_approved", "drive", "wia", "Whitney", "Winter open-day creative approved", null, "drive-cr-r1", "normal"],
    ["2025-10-20T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "21:10", "normal"],
    ["2025-11-17T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "17:33", "normal"],
    ["2025-12-15T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "09:12", "normal"],
    ["2026-01-19T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "28:40", "normal"],
    ["2026-02-16T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "15:05", "normal"],
    ["2026-03-03T10:15:00", "work", "asset_approved", "drive", "wia", "Whitney", "Meta copy set B approved", "Supersedes set A.", "drive-copy-r2", "normal"],
    ["2026-03-16T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "06:22", "normal"],
    ["2026-04-20T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "19:50", "normal"],
    ["2026-05-18T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "11:41", "normal"],
    ["2026-06-15T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "24:03", "normal"],
    ["2026-07-20T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", "Last call on this account — 46 days before the date of view.", "08:17", "major"],
    ["2026-07-24T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-199 issued — $1,850", "July retainer.", "INV-199", "minor"],
    ["2026-08-02T10:30:00", "money", "invoice_paid", "highlevel", "client", "Dana Whitfield", "INV-199 paid", "9 days from issue — slower than this account's average.", "INV-199", "minor"],
    ["2026-08-08T09:00:00", "money", "renewal", "highlevel", "system", "AI HQ", "Renewal window opened", "90 days out. Decision due 8 Nov.", null, "major"],
    ["2026-08-12T10:00:00", "commitments", "commitment_made", "gmail", "wia", "Whitney", "Send the Q3 performance summary", "Owner Whitney. No transcript — this came out of an email thread.", null, "normal"],
    ["2026-08-15T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-204 issued — $1,850", "Due 30 Aug.", "INV-204", "minor"],
    ["2026-08-24T09:00:00", "comms", "email_out", "gmail", "wia", "Gisselle", "Recap follow-up sent", "No reply since.", "msg-11440", "normal"],
    ["2026-08-30T23:59:00", "money", "invoice_overdue", "highlevel", "system", "HighLevel", "INV-204 past due", "$1,850, 5 days overdue at the date of view.", "INV-204", "major"],
    ["2026-08-31T08:00:00", "money", "reminder_sent", "highlevel", "system", "HighLevel", "Automatic reminder sent", "HighLevel's own reminder. Historically these land in promotions.", "INV-204", "minor"],
    ["2026-09-01T09:00:00", "commitments", "commitment_overdue", "clickup", "wia", "Whitney", "Q3 performance summary now overdue", null, "CU-4388", "normal"],
    ["2026-09-02T10:00:00", "commitments", "commitment_blocked", "clickup", "wia", "Carmen", "Audience rebuild blocked", "Waiting on the client's updated guest-list export.", "CU-4391", "normal"],
    ["2026-09-03T14:00:00", "money", "reminder_sent", "gmail", "wia", "Gisselle", "Personal Gmail follow-up drafted", "Carries the HighLevel payment link. Held for a human to send.", "INV-204", "normal"],
    ["2026-09-03T15:20:00", "engagement", "risk_raised", "aihq", "system", "AI HQ", "Account flagged — invoice and recap both outstanding", "Two ledgers slipped in the same week.", null, "major"],
  ]),
};

/* ════════════════════════════════════════════════════════════════
   EVERLY ESTATE — Accelerator member, and the engagement-health case.

   Short record, group sessions instead of one-to-one calls, and a slide from
   attending to missing that is only visible on a time axis. On the ledgers
   alone this account looks fine.
   ════════════════════════════════════════════════════════════════ */

const EVERLY: EngagementRecord = {
  clientId: "everly",
  origin: {
    projectKey: "everly-estate",
    signedAt: "2026-02-20T11:30:00",
    paidAt: "2026-02-20T11:48:00",
    pairedAt: "2026-02-20T11:50:00",
    activatedAt: "2026-02-21T09:00:00",
    kickoffLeadlockAt: null,
    kickoffAdsAt: "2026-03-05T16:00:00",
  },
  terms: {
    tier: "Google Search Accelerator",
    offers: ["Google Search Accelerator"],
    monthly: 497,
    contractRef: "HighLevel · Accelerator monthly",
    renewalAt: null,
  },
  backfill: {
    mode: "backfilled",
    beginsAt: "2026-01-28T16:20:00",
    summary:
      "Backfilled to the webinar registration that started it. Complete — the whole engagement post-dates the connected sources.",
    reachable: ["gmail", "clickup", "drive", "highlevel", "zoom", "slack"],
    unreachable: [],
  },
  phases: [
    { key: "prospect", startsAt: "2026-01-28T16:20:00", note: "Registered for the Google Ads webinar" },
    { key: "onboarding", startsAt: "2026-02-20T11:30:00", note: "Self-serve signup, paid immediately" },
    { key: "launch", startsAt: "2026-03-05T16:00:00", note: "Ads kickoff, first office hours the week after" },
    { key: "steady", startsAt: "2026-04-02T18:00:00", note: "Weekly office-hours cadence" },
    { key: "at_risk", startsAt: "2026-08-06T18:00:00", note: "Three consecutive sessions missed, plus a blocking item unreturned" },
  ],
  people: [
    { name: "Nina Cole", role: "Owner", email: "nina@everlyestate.com", side: "client", validFrom: "2026-01-28", validTo: null },
    { name: "Carmen", role: "Accelerator host", email: "carmen@wia", side: "wia", validFrom: "2026-03-05", validTo: null },
  ],
  assets: [
    { id: "everly-a1", clientId: "everly", kind: "strategy", title: "Accelerator onboarding worksheet", approvedAt: "2026-03-05T17:10:00", approvedBy: "Carmen", source: "drive", sourceRef: "Drive · Everly Estate / Accelerator", supersedes: null, note: null },
    { id: "everly-a2", clientId: "everly", kind: "ad-copy", title: "Search ad copy — reviewed in session", approvedAt: "2026-04-16T18:40:00", approvedBy: "Carmen", source: "drive", sourceRef: "Drive · Everly Estate / Accelerator", supersedes: null, note: "Reviewed live on office hours rather than approved in a gate." },
  ],
  events: expand("everly", [
    ...monthly("2026-03-20", "2026-07-20", (d) => [retainer(d, "Nina Cole", "$497")]),
    ["2026-08-01T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-200 issued — $497", "August Accelerator.", "INV-200", "minor"],
    ["2026-08-05T08:40:00", "money", "invoice_paid", "highlevel", "client", "Nina Cole", "INV-200 paid", "4 days from issue.", "INV-200", "minor"],
    ...monthly("2026-03-24", "2026-06-24", (d) => [
      inbound(d, "Nina Cole", "Question from office hours"),
    ]),
    ["2026-01-28T16:20:00", "comms", "email_in", "gmail", "client", "Nina Cole", "Registered for the Google Ads webinar", null, "msg-10220", "major"],
    ["2026-02-20T11:30:00", "onboarding", "contract_signed", "highlevel", "client", "Nina Cole", "Accelerator signup", "Self-serve, no contract alert.", null, "major"],
    ["2026-02-20T11:48:00", "onboarding", "invoice_paid_first", "highlevel", "client", "Nina Cole", "First payment — $497", null, "INV-166", "major"],
    ["2026-02-21T09:00:00", "onboarding", "provisioning_approved", "aihq", "wia", "Gisselle", "Accelerator provisioning approved", "Community access and the member checklist.", null, "normal"],
    ["2026-02-21T09:06:00", "onboarding", "welcome_sent", "gmail", "wia", "Gisselle", "Welcome email sent", null, "msg-10288", "normal"],
    ["2026-03-05T16:00:00", "onboarding", "kickoff_held", "zoom", "wia", "Carmen", "Accelerator kickoff call held", null, null, "major"],
    ["2026-03-05T17:10:00", "work", "asset_approved", "drive", "wia", "Carmen", "Onboarding worksheet completed", null, "drive-acc-e1", "normal"],
    ["2026-03-12T18:00:00", "engagement", "session_attended", "zoom", "client", "Nina Cole", "Google Office Hours — attended", null, null, "minor"],
    ["2026-03-19T18:00:00", "engagement", "session_attended", "zoom", "client", "Nina Cole", "Google Office Hours — attended", null, null, "minor"],
    ["2026-03-26T18:00:00", "engagement", "session_attended", "zoom", "client", "Nina Cole", "Google Office Hours — attended", null, null, "minor"],
    ["2026-04-02T18:00:00", "engagement", "session_attended", "zoom", "client", "Nina Cole", "Google Office Hours — attended", null, null, "minor"],
    ["2026-04-09T18:00:00", "engagement", "session_attended", "zoom", "client", "Nina Cole", "Google Office Hours — attended", null, null, "minor"],
    ["2026-04-16T18:40:00", "work", "asset_approved", "drive", "wia", "Carmen", "Search ad copy reviewed in session", null, "drive-acc-e2", "normal"],
    ["2026-04-16T18:00:00", "engagement", "session_attended", "zoom", "client", "Nina Cole", "Google Office Hours — attended", null, null, "minor"],
    ["2026-04-23T18:00:00", "engagement", "session_attended", "zoom", "client", "Nina Cole", "Google Office Hours — attended", null, null, "minor"],
    ["2026-05-07T18:00:00", "engagement", "session_missed", "zoom", "client", "Nina Cole", "Google Office Hours — missed", null, null, "minor"],
    ["2026-05-14T18:00:00", "engagement", "session_attended", "zoom", "client", "Nina Cole", "Google Office Hours — attended", null, null, "minor"],
    ["2026-05-21T18:00:00", "engagement", "session_attended", "zoom", "client", "Nina Cole", "Google Office Hours — attended", null, null, "minor"],
    ["2026-06-04T18:00:00", "engagement", "session_attended", "zoom", "client", "Nina Cole", "Google Office Hours — attended", null, null, "minor"],
    ["2026-06-11T18:00:00", "engagement", "session_missed", "zoom", "client", "Nina Cole", "Google Office Hours — missed", null, null, "minor"],
    ["2026-06-18T18:00:00", "engagement", "session_attended", "zoom", "client", "Nina Cole", "Google Office Hours — attended", "Last session attended.", null, "normal"],
    ["2026-07-02T10:00:00", "comms", "email_out", "gmail", "wia", "Carmen", "Ads account access requested", "Needed to run the quarterly audit.", "msg-11002", "normal"],
    ["2026-07-02T10:05:00", "commitments", "commitment_made", "gmail", "client", "Nina Cole", "Send Ads account access", "Client-side. Agreed by email, no transcript.", null, "normal"],
    ["2026-07-09T18:00:00", "engagement", "session_missed", "zoom", "client", "Nina Cole", "Google Office Hours — missed", null, null, "minor"],
    ["2026-07-16T18:00:00", "engagement", "session_missed", "zoom", "client", "Nina Cole", "Google Office Hours — missed", "Second consecutive.", null, "normal"],
    ["2026-07-23T18:00:00", "engagement", "session_missed", "zoom", "client", "Nina Cole", "Google Office Hours — missed", "Third consecutive — the two-week flag was already up.", null, "major"],
    ["2026-07-28T09:00:00", "commitments", "commitment_overdue", "clickup", "client", "Nina Cole", "Ads account access now overdue", "Blocking the quarterly audit round.", "CU-4201", "major"],
    ["2026-08-06T18:00:00", "engagement", "risk_raised", "aihq", "system", "AI HQ", "Four-week attendance flag raised", "No session attended since 18 June.", null, "major"],
    ["2026-08-13T18:00:00", "engagement", "session_missed", "zoom", "client", "Nina Cole", "Google Office Hours — missed", null, null, "minor"],
    ["2026-08-20T18:00:00", "engagement", "session_missed", "zoom", "client", "Nina Cole", "Google Office Hours — missed", null, null, "minor"],
    ["2026-08-27T18:00:00", "engagement", "session_missed", "zoom", "client", "Nina Cole", "Google Office Hours — missed", null, null, "minor"],
    ["2026-09-01T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-206 issued — $497", "September Accelerator.", "INV-206", "minor"],
    ["2026-09-03T18:00:00", "engagement", "session_missed", "zoom", "client", "Nina Cole", "Google Office Hours — missed", "Eleven weeks since the last attendance.", null, "normal"],
  ]),
};

/* ════════════════════════════════════════════════════════════════
   WILLOW & PINE — Accelerator member with an identity problem.

   Short, and carries the unmatched-participant case: a Zoom display name
   that did not resolve to a member record, so the miss count underneath it
   is provisional and the record says so.
   ════════════════════════════════════════════════════════════════ */

const WILLOW: EngagementRecord = {
  clientId: "willow",
  origin: {
    projectKey: "willow-pine",
    signedAt: "2026-04-15T10:05:00",
    paidAt: "2026-04-15T10:12:00",
    pairedAt: "2026-04-15T10:14:00",
    activatedAt: "2026-04-15T14:00:00",
    kickoffLeadlockAt: null,
    kickoffAdsAt: "2026-04-23T16:00:00",
  },
  terms: {
    tier: "Meta Ads Accelerator",
    offers: ["Meta Ads Accelerator"],
    monthly: 497,
    contractRef: "HighLevel · Accelerator monthly",
    renewalAt: null,
  },
  backfill: {
    mode: "backfilled",
    beginsAt: "2026-03-30T13:15:00",
    summary: "Complete. The engagement is five months old and entirely inside the connected window.",
    reachable: ["gmail", "clickup", "drive", "highlevel", "zoom"],
    unreachable: [],
  },
  phases: [
    { key: "prospect", startsAt: "2026-03-30T13:15:00", note: "Downloaded the Meta ads lead magnet" },
    { key: "onboarding", startsAt: "2026-04-15T10:05:00", note: "Self-serve signup" },
    { key: "launch", startsAt: "2026-04-23T16:00:00", note: "Accelerator kickoff" },
    { key: "steady", startsAt: "2026-05-07T18:00:00", note: "Weekly office-hours cadence" },
    { key: "at_risk", startsAt: "2026-08-13T18:00:00", note: "Attendance unresolved and comms gone quiet" },
  ],
  people: [
    { name: "Maya Stone", role: "Owner", email: "maya@willowandpine.com", side: "client", validFrom: "2026-03-30", validTo: null },
    { name: "Carmen", role: "Accelerator host", email: "carmen@wia", side: "wia", validFrom: "2026-04-23", validTo: null },
  ],
  assets: [
    { id: "willow-a1", clientId: "willow", kind: "strategy", title: "Accelerator onboarding worksheet", approvedAt: "2026-04-23T17:00:00", approvedBy: "Carmen", source: "drive", sourceRef: "Drive · Willow & Pine / Accelerator", supersedes: null, note: null },
  ],
  events: expand("willow", [
    ...monthly("2026-05-15", "2026-07-15", (d) => [retainer(d, "Maya Stone", "$497")]),
    ["2026-08-01T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-197 issued — $497", "August Accelerator.", "INV-197", "minor"],
    ["2026-08-06T09:25:00", "money", "invoice_paid", "highlevel", "client", "Maya Stone", "INV-197 paid", "5 days from issue.", "INV-197", "minor"],
    ...monthly("2026-05-19", "2026-06-19", (d) => [
      inbound(d, "Maya Stone", "Question from office hours"),
    ]),
    ["2026-03-30T13:15:00", "comms", "email_in", "gmail", "client", "Maya Stone", "Downloaded the Meta ads lead magnet", null, "msg-10740", "major"],
    ["2026-04-15T10:05:00", "onboarding", "contract_signed", "highlevel", "client", "Maya Stone", "Accelerator signup", null, null, "major"],
    ["2026-04-15T10:12:00", "onboarding", "invoice_paid_first", "highlevel", "client", "Maya Stone", "First payment — $497", null, "INV-172", "major"],
    ["2026-04-15T14:00:00", "onboarding", "provisioning_approved", "aihq", "wia", "Gisselle", "Accelerator provisioning approved", null, null, "normal"],
    ["2026-04-15T14:05:00", "onboarding", "welcome_sent", "gmail", "wia", "Gisselle", "Welcome email sent", null, "msg-10802", "normal"],
    ["2026-04-23T16:00:00", "onboarding", "kickoff_held", "zoom", "wia", "Carmen", "Accelerator kickoff call held", null, null, "major"],
    ["2026-04-23T17:00:00", "work", "asset_approved", "drive", "wia", "Carmen", "Onboarding worksheet completed", null, "drive-acc-w1", "normal"],
    ["2026-05-07T18:00:00", "engagement", "session_attended", "zoom", "client", "Maya Stone", "Meta Office Hours — attended", null, null, "minor"],
    ["2026-05-14T18:00:00", "engagement", "session_attended", "zoom", "client", "Maya Stone", "Meta Office Hours — attended", null, null, "minor"],
    ["2026-05-21T18:00:00", "engagement", "session_attended", "zoom", "client", "Maya Stone", "Meta Office Hours — attended", null, null, "minor"],
    ["2026-06-04T18:00:00", "engagement", "session_attended", "zoom", "client", "Maya Stone", "Meta Office Hours — attended", null, null, "minor"],
    ["2026-06-11T18:00:00", "engagement", "session_missed", "zoom", "client", "Maya Stone", "Meta Office Hours — missed", null, null, "minor"],
    ["2026-06-18T18:00:00", "engagement", "session_attended", "zoom", "client", "Maya Stone", "Meta Office Hours — attended", null, null, "minor"],
    ["2026-07-02T18:00:00", "engagement", "session_attended", "zoom", "client", "Maya Stone", "Meta Office Hours — attended", null, null, "minor"],
    ["2026-07-09T18:00:00", "engagement", "session_missed", "zoom", "client", "Maya Stone", "Meta Office Hours — missed", null, null, "minor"],
    ["2026-07-16T18:00:00", "engagement", "session_attended", "zoom", "client", "Maya Stone", "Meta Office Hours — attended", "Last confirmed attendance.", null, "normal"],
    ["2026-07-23T18:00:00", "engagement", "session_missed", "zoom", "client", "Maya Stone", "Meta Office Hours — missed", null, null, "minor"],
    ["2026-08-06T18:00:00", "engagement", "attendance_unmatched", "zoom", "system", "AI HQ", "Participant did not resolve to a member", "Zoom display name 'M. Stone (iPhone)' — 91% similarity to Maya Stone. Not asserted; the miss count below it is provisional.", null, "major"],
    ["2026-08-13T18:00:00", "engagement", "session_missed", "zoom", "client", "Maya Stone", "Meta Office Hours — missed", null, null, "minor"],
    ["2026-08-14T09:00:00", "comms", "email_out", "gmail", "wia", "Carmen", "Re-engagement email sent", "No reply.", "msg-11380", "normal"],
    ["2026-08-20T18:00:00", "engagement", "session_missed", "zoom", "client", "Maya Stone", "Meta Office Hours — missed", null, null, "minor"],
    ["2026-08-27T18:00:00", "engagement", "session_missed", "zoom", "client", "Maya Stone", "Meta Office Hours — missed", null, null, "minor"],
    ["2026-09-01T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-205 issued — $497", null, "INV-205", "minor"],
    ["2026-09-03T18:00:00", "engagement", "session_missed", "zoom", "client", "Maya Stone", "Meta Office Hours — missed", null, null, "minor"],
  ]),
};

/* ════════════════════════════════════════════════════════════════
   MAGNOLIA HOUSE — the prospect.

   There is no engagement yet, so most of the spine is empty. That is the
   correct picture rather than a broken one, and it is the reason the record
   declares a mode of "no-engagement" instead of pretending to a start date.
   ════════════════════════════════════════════════════════════════ */

const MAGNOLIA: EngagementRecord = {
  clientId: "magnolia",
  origin: {
    projectKey: null,
    signedAt: null,
    paidAt: null,
    pairedAt: null,
    activatedAt: null,
    kickoffLeadlockAt: null,
    kickoffAdsAt: null,
  },
  terms: {
    tier: "Prospect · Elevate proposed",
    offers: ["Elevate retainer (proposed)"],
    monthly: null,
    contractRef: null,
    renewalAt: null,
  },
  backfill: {
    mode: "no-engagement",
    beginsAt: "2026-07-22T09:40:00",
    summary:
      "No engagement to backfill. The record begins at first contact and holds six weeks of a sales conversation — nothing more, because nothing more has happened.",
    reachable: ["gmail", "zoom", "clickup"],
    unreachable: [
      { source: "highlevel", from: null, why: "No contract, no invoice, no member record. There is nothing on the money or engagement lanes and there should not be." },
    ],
  },
  phases: [{ key: "prospect", startsAt: "2026-07-22T09:40:00", note: "Enquiry through the site — proposal out, decision pending" }],
  people: [
    { name: "Tessa Ruiz", role: "Owner", email: "tessa@magnoliahouse.com", side: "client", validFrom: "2026-07-22", validTo: null },
    { name: "Whitney", role: "Owner · approver", email: "whitney@wia", side: "wia", validFrom: "2026-07-22", validTo: null },
  ],
  assets: [],
  events: expand("magnolia", [
    ["2026-07-22T09:40:00", "comms", "email_in", "gmail", "client", "Tessa Ruiz", "Enquiry through the site", "Asked what a first 90 days looks like.", "msg-11120", "major"],
    ["2026-07-24T10:00:00", "comms", "email_out", "gmail", "wia", "Gisselle", "Discovery call offered", null, "msg-11133", "normal"],
    ["2026-08-04T15:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Discovery call", "38 min. Transcript held.", "00:00", "major"],
    ["2026-08-04T15:22:00", "commitments", "commitment_made", "zoom", "wia", "Whitney", "Send the Elevate proposal", "Owner Whitney, agreed on the call.", "22:14", "normal"],
    ["2026-08-04T17:30:00", "meetings", "transcript_filed", "drive", "system", "AI HQ", "Recording and transcript filed", null, "drive-mtg-0804", "minor"],
    ["2026-08-11T11:00:00", "comms", "email_out", "gmail", "wia", "Whitney", "Elevate proposal sent", "$2,400/mo, 12 months.", "msg-11205", "major"],
    ["2026-08-11T11:02:00", "commitments", "commitment_delivered", "gmail", "wia", "Whitney", "Elevate proposal delivered", "Closed the commitment from the discovery call.", "msg-11205", "normal"],
    ["2026-08-19T16:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Proposal walkthrough", "26 min.", "00:00", "normal"],
    ["2026-08-19T16:18:00", "commitments", "commitment_made", "zoom", "client", "Tessa Ruiz", "Come back with a decision", "Client-side, agreed for 4 Sep.", "18:37", "normal"],
    ["2026-08-28T09:15:00", "comms", "email_in", "gmail", "client", "Tessa Ruiz", "Asked for a second reference", null, "msg-11402", "normal"],
    ["2026-08-28T14:00:00", "comms", "email_out", "gmail", "wia", "Gisselle", "Reference introduction sent", null, "msg-11418", "normal"],
    ["2026-09-04T09:00:00", "commitments", "commitment_made", "clickup", "wia", "Whitney", "Proposal follow-up due today", "Nothing is late yet — this is the day it was agreed for.", "CU-4402", "major"],
  ]),
};

/* ════════════════════════════════════════════════════════════════
   HARBOR HOUSE — the hole in the record.

   A twelve-month retainer whose meeting history stops dead in April, because
   the team member who became the recorder does not have an authorised Fathom
   key. Every commitment after that date is real and uncitable, and the spine
   draws the gap rather than closing over it.

   This is the most important account in the corpus. An engagement record that
   only ever shows complete history teaches the reviewer to trust it
   unconditionally, which is exactly the wrong lesson.
   ════════════════════════════════════════════════════════════════ */

const HARBOR: EngagementRecord = {
  clientId: "harbor",
  origin: {
    projectKey: "harbor-house",
    signedAt: "2025-09-02T13:00:00",
    paidAt: "2025-09-05T09:30:00",
    pairedAt: "2025-09-05T09:33:00",
    activatedAt: "2025-09-08T09:00:00",
    kickoffLeadlockAt: "2025-09-16T14:00:00",
    kickoffAdsAt: "2025-09-30T14:00:00",
  },
  terms: {
    tier: "Amplify",
    offers: ["Amplify retainer"],
    /* $1,750, matching CLIENT_INVOICES. Rosewood is the $1,850 account; the
       two were briefly given the same rate and the same invoice number, which
       is exactly the kind of drift a single record is supposed to prevent. */
    monthly: 1750,
    contractRef: "Dubsado · Amplify 12mo",
    renewalAt: "2026-09-02",
  },
  backfill: {
    mode: "backfilled",
    beginsAt: "2025-08-11T10:00:00",
    summary:
      "Backfilled to first contact. Email, tasks, files and money are complete — the meeting record is not, and stops in April.",
    reachable: ["gmail", "clickup", "drive", "highlevel"],
    unreachable: [
      {
        source: "fathom",
        from: "2026-04-14",
        why: "Danielle became the recorder on this account in April and her Fathom key is not authorised. Fathom keys are user-level, so an admin key does not unlock meetings she recorded and did not share. Five calls since then have a summary and no transcript.",
      },
      {
        source: "drive",
        from: "2026-04-14",
        why: "Folder mapping for Harbor House is unresolved, so nothing has been filed since the recorder changed.",
      },
    ],
  },
  phases: [
    { key: "prospect", startsAt: "2025-08-11T10:00:00", note: "Referral" },
    { key: "onboarding", startsAt: "2025-09-02T13:00:00", note: "Signature, payment three days later" },
    { key: "launch", startsAt: "2025-09-30T14:00:00", note: "Ads kickoff" },
    { key: "steady", startsAt: "2025-11-10T09:00:00", note: "Monthly cadence" },
    { key: "renewal", startsAt: "2026-06-04T09:00:00", note: "Renewal was due 2 Sep — two days before the date of view, and undecided" },
  ],
  people: [
    { name: "Elena Park", role: "Owner", email: "elena@harborhouse.com", side: "client", validFrom: "2025-08-11", validTo: null },
    { name: "Whitney", role: "Owner · approver", email: "whitney@wia", side: "wia", validFrom: "2025-09-02", validTo: "2026-04-13" },
    { name: "Danielle", role: "Account lead", email: "danielle@wia", side: "wia", validFrom: "2026-04-14", validTo: null },
  ],
  assets: [
    { id: "harbor-a1", clientId: "harbor", kind: "strategy", title: "Messaging & positioning — Harbor House", approvedAt: "2025-09-24T11:00:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Harbor House / Strategy", supersedes: null, note: null },
    { id: "harbor-a2", clientId: "harbor", kind: "landing-page", title: "Enquiry landing page v1", approvedAt: "2025-10-14T10:30:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Harbor House / Landing pages", supersedes: null, note: null },
    { id: "harbor-a3", clientId: "harbor", kind: "ad-copy", title: "Search + Meta copy set", approvedAt: "2025-11-04T09:00:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Harbor House / Ad copy", supersedes: null, note: null },
    { id: "harbor-a4", clientId: "harbor", kind: "creative", title: "Spring 2026 creative set", approvedAt: "2026-03-10T15:00:00", approvedBy: "Whitney", source: "drive", sourceRef: "Drive · Harbor House / Creative", supersedes: null, note: "Last asset filed before the folder mapping broke." },
  ],
  events: expand("harbor", [
    ...monthly("2025-10-05", "2026-05-05", (d) => [retainer(d, "Elena Park", "$1,750")]),
    ...monthly("2025-10-09", "2026-06-09", (d) => [recap(d, "Gisselle")]),
    ["2026-06-24T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-191 issued — $1,750", "June retainer.", "INV-191", "minor"],
    ["2026-07-02T09:50:00", "money", "invoice_paid", "highlevel", "client", "Elena Park", "INV-191 paid", "8 days from issue.", "INV-191", "minor"],
    /* Both stop in March. The reports stop because the Drive mapping broke;
       the commitments stop because the Fathom key did. Two different failures
       landing in the same month is exactly why the record has to name the
       source rather than just show the silence. */
    ...monthly("2025-11-12", "2026-03-12", (d) => [report(d)]),
    ...monthly("2025-12-08", "2026-03-09", (d, i) =>
      promise(d, i, "Whitney", "Action from the monthly review"),
    ),
    ["2025-08-11T10:00:00", "comms", "email_in", "gmail", "client", "Elena Park", "Referral introduction", null, "msg-9440", "major"],
    ["2025-08-21T14:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Discovery call", null, null, "normal"],
    ["2025-09-02T13:00:00", "onboarding", "contract_signed", "gmail", "client", "Elena Park", "Contract signed", "Amplify, 12 months.", "alert-sig-2680", "major"],
    ["2025-09-05T09:30:00", "onboarding", "invoice_paid_first", "highlevel", "client", "Elena Park", "First invoice paid — $1,750", null, "INV-136", "major"],
    ["2025-09-08T09:00:00", "onboarding", "provisioning_approved", "aihq", "wia", "Gisselle", "Provisioning batch approved", null, null, "normal"],
    ["2025-09-08T09:10:00", "onboarding", "clickup_created", "clickup", "system", "AI HQ", "ClickUp lists created", null, null, "minor"],
    ["2025-09-08T09:14:00", "onboarding", "welcome_sent", "gmail", "wia", "Gisselle", "Welcome email sent", null, "msg-9512", "normal"],
    ["2025-09-16T14:00:00", "onboarding", "kickoff_held", "zoom", "wia", "Whitney", "Lead Lock kickoff call held", null, null, "major"],
    ["2025-09-24T11:00:00", "work", "asset_approved", "drive", "wia", "Whitney", "Messaging & positioning approved", null, "drive-str-h1", "major"],
    ["2025-09-30T14:00:00", "onboarding", "kickoff_held", "zoom", "wia", "Whitney", "Ads kickoff call held", null, null, "major"],
    ["2025-10-14T10:30:00", "work", "asset_approved", "drive", "wia", "Whitney", "Landing page v1 approved", null, "drive-lp-h1", "normal"],
    ["2025-10-21T10:00:00", "work", "campaign_launched", "clickup", "wia", "Carmen", "Search and Meta campaigns live", null, "CU-3801", "major"],
    ["2025-11-04T09:00:00", "work", "asset_approved", "drive", "wia", "Whitney", "Ad copy set approved", null, "drive-copy-h1", "normal"],
    ["2025-11-10T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "First monthly strategy call", null, "10:20", "normal"],
    ["2025-12-08T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "14:55", "normal"],
    ["2026-01-12T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "22:31", "normal"],
    ["2026-02-09T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "18:07", "normal"],
    ["2026-03-09T09:00:00", "meetings", "call_held", "zoom", "wia", "Whitney", "Monthly strategy call", null, "09:44", "normal"],
    ["2026-03-10T15:00:00", "work", "asset_approved", "drive", "wia", "Whitney", "Spring creative set approved", "Last asset filed before the folder mapping broke.", "drive-cr-h1", "normal"],
    ["2026-04-13T17:00:00", "engagement", "contact_changed", "clickup", "wia", "Danielle", "Account lead changed — Whitney to Danielle", "The recorder changed with it, and the meeting record stops here.", null, "major"],
    ["2026-04-14T09:00:00", "meetings", "transcript_missing", "fathom", "system", "AI HQ", "Transcript unavailable — April call", "Recorded on Danielle's Fathom account, not shared to the team. Summary only.", null, "major"],
    ["2026-05-11T09:00:00", "meetings", "transcript_missing", "fathom", "system", "AI HQ", "Transcript unavailable — May call", "Summary only.", null, "normal"],
    ["2026-06-04T09:00:00", "money", "renewal", "highlevel", "system", "AI HQ", "Renewal window opened", "Decision was due 2 Sep.", null, "major"],
    ["2026-06-08T09:00:00", "meetings", "transcript_missing", "fathom", "system", "AI HQ", "Transcript unavailable — June call", "Summary only.", null, "normal"],
    ["2026-07-13T09:00:00", "meetings", "transcript_missing", "fathom", "system", "AI HQ", "Transcript unavailable — July call", "Summary only.", null, "normal"],
    ["2026-07-24T09:00:00", "money", "invoice_issued", "highlevel", "system", "HighLevel", "INV-198 issued — $1,750", "Due 27 Aug.", "INV-198", "minor"],
    ["2026-08-10T09:00:00", "meetings", "transcript_missing", "fathom", "system", "AI HQ", "Transcript unavailable — August call", "Summary only. Fifth in a row.", null, "normal"],
    ["2026-08-10T09:30:00", "commitments", "commitment_made", "fathom", "wia", "Danielle", "Rebuild the enquiry form", "From the August summary. No transcript, so no second to cite.", null, "normal"],
    ["2026-08-10T09:35:00", "commitments", "commitment_made", "fathom", "client", "Elena Park", "Confirm the 2027 pricing page copy", "From the August summary. Uncitable.", null, "normal"],
    ["2026-08-27T23:59:00", "money", "invoice_overdue", "highlevel", "system", "HighLevel", "INV-198 past due", "$1,750, 8 days overdue at the date of view.", "INV-198", "major"],
    ["2026-08-28T08:00:00", "money", "reminder_sent", "highlevel", "system", "HighLevel", "Automatic reminder sent", null, "INV-198", "minor"],
    ["2026-09-01T09:00:00", "commitments", "commitment_blocked", "clickup", "wia", "Danielle", "Enquiry form rebuild blocked", "Waiting on the pricing page copy from the client.", "CU-4380", "normal"],
    ["2026-09-02T09:00:00", "money", "renewal", "highlevel", "system", "AI HQ", "Renewal date passed undecided", "The 12-month term ended two days before the date of view.", null, "major"],
    ["2026-09-03T10:00:00", "commitments", "ack_missing", "slack", "wia", "Danielle", "No acknowledgement on the form rebuild", null, null, "normal"],
    ["2026-09-03T16:00:00", "engagement", "risk_raised", "aihq", "system", "AI HQ", "Account flagged — renewal passed, invoice overdue, no transcript in five months", "Three separate problems, none of which is visible from one system.", null, "major"],
  ]),
};

/* ── The book ─────────────────────────────────────────────────── */

export const ENGAGEMENTS: Record<string, EngagementRecord> = {
  bloom: BLOOM,
  rosewood: ROSEWOOD,
  everly: EVERLY,
  willow: WILLOW,
  magnolia: MAGNOLIA,
  harbor: HARBOR,
};

export const engagementFor = (clientId: string): EngagementRecord | null =>
  ENGAGEMENTS[clientId] ?? null;
