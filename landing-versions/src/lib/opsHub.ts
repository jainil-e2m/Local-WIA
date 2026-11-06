/* ────────────────────────────────────────────────────────────────
   Ops Hub — types, design tokens and derived counts.

   Re-skin note. The source mock ran a navy/DM-Serif palette of its own.
   Nothing of that palette survives here: every colour below resolves to the
   WIA extraction already in tailwind.config.js (brand.* and console.*), so
   the hub reads as the same product as the landing page rather than a second
   one. The ONE deliberate exception is SOURCE_META — those are third-party
   brand marks (Gmail red, Slack purple, ClickUp green…) used as 5px dots for
   recognition. Recolouring them to the brand ramp would make seven sources
   indistinguishable, which is the opposite of the point.

   THE COUNTS ARE DERIVED, NEVER LITERAL. Every badge in the shell and every
   KPI on Home is computed from queue state by `deriveCounts`. Acting on an
   item decrements its nav badge in the same tick. Hardcoding those numbers
   would let the demo drift the moment anyone clicked anything — which is
   exactly the failure that makes a mock feel fake.
   ──────────────────────────────────────────────────────────────── */

export type Tone =
  | "neutral"
  | "blue"
  | "green"
  | "amber"
  | "red"
  | "navy"
  | "slate"
  | "outline"
  | "violet";

/* Pill classes. `console.good/bad/warn` are the darkened semantic ends the
   theme already defines for exactly this reason — brand.orange/teal/sky all
   fall under 1.7:1 on near-white and cannot carry status text. */
export const TONE_CLASS: Record<Tone, string> = {
  neutral: "border-transparent bg-brand-mist/70 text-brand-gray",
  blue: "border-transparent bg-brand-primary/10 text-brand-primary",
  green: "border-transparent bg-console-good/10 text-console-good",
  amber: "border-transparent bg-console-warn/10 text-console-warn",
  red: "border-transparent bg-console-bad/10 text-console-bad",
  navy: "border-transparent bg-brand-ink text-white",
  slate: "border-brand-stone/60 bg-brand-mist/50 text-brand-secondary",
  outline: "border-brand-mist bg-white text-brand-gray",
  violet: "border-transparent bg-brand-teal/15 text-[#6b5847]",
};

/* Glyph chips on the operating queue — a filled square of tone. */
export const GLYPH_CLASS: Record<Tone, string> = {
  neutral: "bg-brand-mist/70 text-brand-gray",
  blue: "bg-brand-primary/10 text-brand-primary",
  green: "bg-console-good/10 text-console-good",
  amber: "bg-console-warn/10 text-console-warn",
  red: "bg-console-bad/10 text-console-bad",
  navy: "bg-brand-ink text-white",
  slate: "bg-brand-mist/50 text-brand-secondary",
  outline: "bg-white text-brand-gray",
  violet: "bg-brand-teal/15 text-[#6b5847]",
};

export type SourceKey =
  | "gmail"
  | "slack"
  | "clickup"
  | "zoom"
  | "fathom"
  | "drive"
  | "highlevel"
  | "aihq";

/* `logo` is the connected-sources mark in the sidebar. These are normalised
   derivatives under /logos/sources/, not the raw files in /logos/: the
   originals arrive as a mix of white-background PNGs, opaque JPEGs and, for
   HighLevel, a 4168x934 wordmark. All seven were flood-filled to transparency
   from their corners, cropped to the glyph and squared to 128px so they sit on
   the dark sidebar without a white card around them. Regenerating them is a
   one-off image job, not a build step — the originals stay in /logos/. */
export const SOURCE_META: Record<
  SourceKey,
  { label: string; color: string; logo?: string }
> = {
  gmail: { label: "Gmail", color: "#D94C4C", logo: "/logos/sources/gmail.png" },
  slack: { label: "Slack", color: "#7C3AED", logo: "/logos/sources/slack.png" },
  clickup: {
    label: "ClickUp",
    color: "#2E9E6B",
    logo: "/logos/sources/clickup.png",
  },
  zoom: { label: "Zoom", color: "#2D8CFF", logo: "/logos/sources/zoom.png" },
  fathom: {
    label: "Fathom",
    color: "#E07A3F",
    logo: "/logos/sources/fathom.png",
  },
  drive: { label: "Drive", color: "#1F8A5B", logo: "/logos/sources/drive.png" },
  highlevel: {
    label: "HighLevel",
    color: "#3F55D6",
    logo: "/logos/sources/highlevel.png",
  },
  /* Ops Hub is us, so it takes the WIA brand primary rather than the mock's —
     and it carries no third-party mark, which is why `logo` is optional. */
  aihq: { label: "Ops Hub", color: "#5070ff" },
};

export const SOURCE_ORDER: SourceKey[] = [
  "gmail",
  "slack",
  "clickup",
  "zoom",
  "fathom",
  "drive",
  "highlevel",
];

/* ── Native vs Ops Hub attribution ──────────────────────────────────
   The single most important honesty device carried over from the mock. It
   labels WHO is automating each thing, so the hub cannot take credit for
   behaviour the platform already ships. That distinction is the spine of the
   scope argument (native HighLevel scheduling, native ClickUp recurrence,
   native Gmail filters) and it belongs on screen, not in a footnote. */
export type AutoSystem =
  | "ai_hq"
  | "clickup"
  | "highlevel"
  | "gmail"
  | "human"
  | "zoom"
  | "ai_assisted"
  | "validation"
  | "gmail_filter"
  | "native_highlevel_ai";

export const AUTO_BADGE: Record<AutoSystem, { label: string; tone: Tone }> = {
  ai_hq: { label: "Ops Hub Automation", tone: "blue" },
  clickup: { label: "Native Automation · ClickUp", tone: "slate" },
  highlevel: { label: "Native Automation · HighLevel", tone: "slate" },
  gmail: { label: "Native Automation · Gmail", tone: "slate" },
  human: { label: "Human decision", tone: "outline" },
  zoom: { label: "Native Automation · Zoom", tone: "slate" },
  ai_assisted: { label: "AI Assisted", tone: "violet" },
  validation: { label: "Production Validation", tone: "amber" },
  gmail_filter: { label: "Native Gmail Filter", tone: "slate" },
  native_highlevel_ai: { label: "Native event + Ops Hub", tone: "slate" },
};

/* ── Screens ──────────────────────────────────────────────────── */

export type ScreenId =
  | "home"
  | "inbox"
  | "meetings"
  | "ops"
  | "clients"
  | "content"
  | "settings";

/* `clients` is labelled "Client Hub" in the nav. It is still not a CRM — no
   pipeline, no deal stages — it is the operational context that Inbox,
   Meetings and Ops Watch read from, gathered per account. */
export const PAGE_META: Record<ScreenId, { title: string; subtitle: string }> = {
  home: {
    /* NOT "Operations Command Center". The app this hub sits inside is called
       the Command Center, so that title read as a second product with almost
       the same name. Every other entry here is the screen's own name, and
       this one now follows the same rule. The product name lives once, in the
       sidebar brand block. */
    title: "Operations Overview",
    subtitle: "Attention · context · approval across WIA",
  },
  inbox: {
    title: "AI Inbox",
    subtitle: "Context-aware triage and drafts — nothing auto-sends",
  },
  meetings: {
    title: "Meeting-to-Execution",
    subtitle: "One reviewable execution pack per meeting",
  },
  clients: {
    title: "Client Hub",
    subtitle: "Operational context for Inbox, Meetings and Ops Watch",
  },
  ops: { title: "Ops Watch", subtitle: "Exceptions and recurring routines" },
  content: {
    title: "Content Atelier",
    subtitle: "WIA’s own marketing — Phase 2 (MC-01 → MC-04)",
  },
  settings: {
    title: "Source Coverage & Automation Access",
    subtitle: "What the hub can reach, and what it deliberately cannot",
  },
};

/* ── Mutable demo state ───────────────────────────────────────── */

export type EmailStatus =
  | "open"
  | "approved"
  | "filed"
  | "kept"
  | "nudged"
  | "snoozed";

/* ── ONE WORK LIFECYCLE ────────────────────────────────────────────
   A SECOND axis, deliberately separate from EmailStatus above.

   EmailStatus records what the automation DID to one artifact — a draft was
   created, a nudge was posted, the thread was filed. WorkStage records where
   the underlying OBLIGATION has got to, which is a different question and the
   one every screen actually needs.

   THE CORRECTION THIS MODEL EXISTS FOR. The previous version collapsed
   "approved" into "completed", so approving a draft closed the row, posting a
   nudge closed the row, and the Home count fell without anybody having
   replied, sent or delivered anything. Creating a draft is not sending it;
   sending a nudge is not receiving an acknowledgement; an acknowledgement is
   not completion. Each of those is now its own stage, and only the two closed
   stages take an item out of the open counts.

   Every screen derives from this. An obligation (see WORK_ITEMS in
   data/opsHub.ts) is the single identifiable work item — it carries links to
   its email, meeting, Slack thread, ClickUp task and account, and Inbox,
   Meetings, Ops Watch and Client Hub are four views of the same stage. */

export type WorkStage =
  | "unread"
  | "in_progress"
  | "review_pending"
  | "approved"
  | "draft_created"
  | "sent"
  | "waiting_ack"
  | "waiting_reply"
  | "noted"
  | "completed"
  | "client_informed";

export const WORK_STAGES: {
  id: WorkStage;
  label: string;
  /** List-column form. The queue list is 340px wide with a sender name in it,
      so "Waiting for acknowledgement" cannot ride in a pill next to one. */
  short: string;
  tone: Tone;
  hint: string;
  /** Closed means nobody owes this obligation anything else. ONLY these two
      leave the open counts — that is the whole point of the model. */
  closed?: boolean;
  /** Which phase of the lifecycle, for grouping in the status menu. */
  group: "to do" | "in flight" | "closed";
}[] = [
  {
    id: "unread",
    label: "Unread",
    short: "Unread",
    tone: "outline",
    hint: "Nobody has opened it yet",
    group: "to do",
  },
  {
    id: "review_pending",
    label: "Review pending",
    short: "Review",
    tone: "blue",
    hint: "The hub has prepared something; a reviewer has not decided yet",
    group: "to do",
  },
  {
    id: "in_progress",
    label: "In progress",
    short: "Active",
    tone: "blue",
    hint: "Someone is working it right now",
    group: "in flight",
  },
  {
    id: "approved",
    label: "Approved",
    short: "Approved",
    tone: "violet",
    hint: "A reviewer approved it — nothing has left the building yet",
    group: "in flight",
  },
  {
    id: "draft_created",
    label: "Draft created — not sent",
    short: "Drafted",
    tone: "violet",
    hint: "A Gmail draft exists. A person still has to press send",
    group: "in flight",
  },
  {
    id: "sent",
    label: "Sent / posted",
    short: "Sent",
    tone: "blue",
    hint: "A human sent or posted it. The work it asks for is still outstanding",
    group: "in flight",
  },
  {
    id: "waiting_ack",
    label: "Waiting for acknowledgement",
    short: "No ack",
    tone: "amber",
    hint: "Nudged, and the owner has not reacted, replied or moved the task",
    group: "in flight",
  },
  {
    id: "waiting_reply",
    label: "Waiting on reply",
    short: "Waiting",
    tone: "amber",
    hint: "Handled on our side; waiting on someone else",
    group: "in flight",
  },
  {
    id: "noted",
    label: "Noted",
    short: "Noted",
    tone: "slate",
    hint: "Read and acknowledged — no action yet",
    group: "to do",
  },
  {
    id: "completed",
    label: "Completed",
    short: "Done",
    tone: "green",
    hint: "The work itself is finished",
    closed: true,
    group: "closed",
  },
  {
    id: "client_informed",
    label: "Client informed",
    short: "Closed",
    tone: "green",
    hint: "Finished AND the client has been told — the loop is shut",
    closed: true,
    group: "closed",
  },
];

export const STAGE_META = Object.fromEntries(
  WORK_STAGES.map((w) => [w.id, w]),
) as Record<WorkStage, (typeof WORK_STAGES)[number]>;

/* The stage implied by a disposition, where the disposition is unambiguous.

   NOTE WHAT IS NOT HERE. `approved` does NOT map to completed. Approving a
   reply produces a Gmail draft and nothing more, so it maps to
   `draft_created` and the row stays open until somebody records the send.
   `nudged` maps to `waiting_ack`, not completed, for the same reason: the
   nudge is an EVENT on an open obligation, not its resolution. */
export const DISPOSITION_STAGE: Record<EmailStatus, WorkStage> = {
  open: "unread",
  approved: "draft_created",
  filed: "completed",
  nudged: "waiting_ack",
  kept: "noted",
  snoozed: "waiting_reply",
};

/* The one predicate every open count is derived from. Anything that counts
   work MUST route through this, or the queue badges and the Home KPIs drift
   apart the first time a row is moved. */
export function isOpenWork(stage: WorkStage): boolean {
  return !STAGE_META[stage].closed;
}

/** Acknowledged = the owner has done something observable. Waiting on an
    acknowledgement, unread and review-pending are all "not acknowledged";
    everything from in-progress onward is. Ops Watch's risk count uses this,
    which is why posting a nudge no longer clears a risk. */
export function isAcknowledged(stage: WorkStage): boolean {
  return (
    stage === "in_progress" ||
    stage === "approved" ||
    stage === "draft_created" ||
    stage === "sent" ||
    stage === "completed" ||
    stage === "client_informed"
  );
}

/** How far along each stage is. Used to roll a parent obligation up from its
    steps: the parent reads the LEAST advanced of its children, so a delivery
    cannot show as completed while its client handoff is still in drafts.
    `noted` and `review_pending` share a rank because neither is progress on
    the work itself — one is "seen", the other is "prepared". */
export const STAGE_RANK: Record<WorkStage, number> = {
  unread: 0,
  noted: 1,
  review_pending: 1,
  in_progress: 2,
  approved: 3,
  draft_created: 3,
  sent: 4,
  waiting_ack: 4,
  waiting_reply: 4,
  completed: 5,
  client_informed: 6,
};

/** What a reviewer is offered next, given where the obligation stands. Kept
    in one place so Inbox, Ops Watch and Client Hub cannot offer different
    next steps for the same item. */
export const NEXT_STAGE: Partial<Record<WorkStage, WorkStage[]>> = {
  unread: ["in_progress", "noted"],
  review_pending: ["approved", "in_progress"],
  approved: ["sent", "in_progress"],
  draft_created: ["sent", "in_progress"],
  sent: ["waiting_ack", "waiting_reply", "completed"],
  waiting_ack: ["in_progress", "completed"],
  waiting_reply: ["in_progress", "completed"],
  in_progress: ["completed", "waiting_reply"],
  noted: ["in_progress", "completed"],
  completed: ["client_informed"],
};

/* ── Obligation events ─────────────────────────────────────────────
   A nudge, a send and an acknowledgement are events ON an obligation, not
   states OF it. Keeping them as a list is what lets Ops Watch say "nudged
   twice, still no reply" instead of silently overwriting the first nudge. */

export type ObligationEvent = {
  at: string;
  actor: string;
  text: string;
  /** The system the event landed in, so the trail is checkable. */
  where: SourceKey;
};

export type OpsHubState = {
  screen: ScreenId;
  user: "Whitney" | "Gisselle";

  /** The client's own lane, or "all" to look across every lane. */
  inboxQueue: string;
  /** Owner filter — cuts across lanes. "all" or a person's name. */
  inboxOwner: string;
  /** Lifecycle filter — cuts across lanes. all | open | waiting | closed. */
  inboxStateFilter: string;
  emailId: string;
  emailState: Record<string, EmailStatus>;
  /* Re-triage: a queue picked by hand wins over the queue in the seed data. */
  emailQueue: Record<string, string>;
  /* Explicit stage per OBLIGATION (not per email) — absent means derive it
     from the disposition of the obligation's email, or from its seed stage. */
  stages: Record<string, WorkStage>;
  /* Append-only trail per obligation. A nudge is an entry here. */
  events: Record<string, ObligationEvent[]>;
  /* Reviewer edits to a prepared draft, keyed by email id. */
  draftEdits: Record<string, string>;

  meetingFilter: string;
  meetingId: string | null;
  /* `revision` is a real state, not a toast: a pack sent back stays on the
     list saying so until somebody re-opens it. */
  packState: Record<string, "needs_review" | "approved" | "revision">;
  packExceptions: Record<string, boolean>;
  taskState: Record<string, "complete">;
  /* Per-output execution result, keyed `${meetingId}:${outputId}`. A pack is
     several dispatches and they do not all succeed together. */
  outputState: Record<string, "pending" | "released" | "failed" | "held" | "manual">;
  /* Outputs the reviewer chose NOT to release in this approval. */
  outputHeld: Record<string, boolean>;
  outputRetried: Record<string, boolean>;
  outputOwner: Record<string, string>;

  clientId: string | null;
  clientTab: string;
  /* Source filter for the merged Timeline tab; "all" or a SourceKey. */
  timelineSource: string;
  /* Spine — the engagement record's time axis. Zoom is a SpineZoom and
     spineLane an EventLane, both typed as string here for the same reason
     clientTab is: lib/opsHub sits underneath data/opsHub, and importing
     lib/engagement (which imports data/opsHub) would close a cycle. The
     Client Hub narrows them at the point of use. */
  spineZoom: string;
  spineLane: string;
  spineEventId: string | null;
  /* Commitments filters. `commitState` carries one value the data does not:
     "unacked" is an acknowledgement filter, not a lifecycle state, and it is
     what the acknowledgement ask routes to. */
  commitSide: "all" | "wia" | "client";
  commitState: string;
  askAnswer: string | null;

  opsTab: string;
  digestState: "ready" | "posted";
  invoiceId: string | null;
  invoiceState: Record<string, "overdue" | "draft_ready" | "handled">;
  invalidState: Record<string, boolean>;

  /** Which of the three Content Atelier views is open. */
  atelierView: string;
  contentId: string;
  contentTab: string;
  contentStage: Record<string, string>;
  /* MC-01 → MC-02 → MC-03, as gates rather than one library of finished
     drafts: a candidate is accepted or rejected, a steer is written, a lead
     asset is approved, and only then do the derived formats unlock. */
  candidateState: Record<string, "accepted" | "rejected">;
  steerDraft: Record<string, string>;
  scriptState: Record<string, "draft" | "approved">;
  clearance: Record<string, boolean>;
  /* The CTA is Whitney's to set and the engine's never to guess — her one
     explicit instruction on 16 September. Empty means unset, and unset
     blocks staging rather than defaulting to something plausible. */
  contentCta: Record<string, string>;
  /* Which asset the rest of the pack is written from. Either the reel or
     the email can lead, because either is where she actually starts. */
  leadAsset: Record<string, string>;

  paletteOpen: boolean;
  paletteQ: string;
  drawer: DrawerPayload | null;
  msgModal: MsgModalPayload | null;
  toast: string | null;
};

export type DrawerPayload = {
  title: string;
  source: SourceKey;
  label: string;
  excerpt: string;
  time: string;
  client: string;
};

export type MsgModalPayload = {
  kind: string;
  member: string;
  id: string;
  title: string;
  body: string;
  note: string;
};

export const INITIAL_STATE: OpsHubState = {
  screen: "home",
  user: "Whitney",

  inboxQueue: "needs_whitney",
  inboxOwner: "all",
  inboxStateFilter: "all",
  emailId: "e1",
  emailState: {},
  emailQueue: {},
  stages: {},
  events: {},
  draftEdits: {},

  meetingFilter: "needs_review",
  meetingId: null,
  packState: {},
  packExceptions: {},
  taskState: {},
  outputState: {},
  outputHeld: {},
  outputRetried: {},
  outputOwner: {},

  clientId: null,
  /* Spine, not Now: the record opens on the whole engagement and you drill
     into today, rather than opening on today and having to go looking for
     the history. That order is the entire argument for the screen. */
  clientTab: "spine",
  timelineSource: "all",
  spineZoom: "all",
  spineLane: "all",
  spineEventId: null,
  commitSide: "all",
  commitState: "all",
  askAnswer: null,

  opsTab: "team",
  digestState: "ready",
  invoiceId: null,
  invoiceState: {},
  invalidState: {},

  atelierView: "queue",
  contentId: "vault-landing-pages",
  contentTab: "reel-a",
  contentStage: {},
  candidateState: {},
  steerDraft: {},
  scriptState: {},
  clearance: {},
  contentCta: {},
  leadAsset: {},

  paletteOpen: false,
  paletteQ: "",
  drawer: null,
  msgModal: null,
  toast: null,
};

/* Everything the reset button clears. Kept as one exported object so the
   Settings screen cannot drift out of step with INITIAL_STATE. */
export const RESETTABLE: Partial<OpsHubState> = {
  inboxOwner: "all",
  inboxStateFilter: "all",
  emailState: {},
  emailQueue: {},
  stages: {},
  events: {},
  draftEdits: {},
  packState: {},
  packExceptions: {},
  taskState: {},
  outputState: {},
  outputHeld: {},
  outputRetried: {},
  outputOwner: {},
  digestState: "ready",
  invoiceState: {},
  invalidState: {},
  contentStage: {},
  candidateState: {},
  steerDraft: {},
  scriptState: {},
  clearance: {},
  contentCta: {},
  leadAsset: {},
  askAnswer: null,
  timelineSource: "all",
  spineZoom: "all",
  spineLane: "all",
  spineEventId: null,
  commitSide: "all",
  commitState: "all",
  invoiceId: null,
  drawer: null,
  msgModal: null,
};
