import { createApi } from "./axios.config";

/**
 * Client-onboarding provisioning, served by this dashboard's own Express BFF
 * (see server/index.mjs, /api/onboarding/*). Same-origin, so the session
 * cookie rides along and requireSession is the boundary.
 *
 * The flow this drives TERMINATES AT APPROVAL. Nothing here writes to ClickUp,
 * and there is deliberately no provision endpoint to call — see
 * server/onboarding-store.mjs for why APPROVED is a terminal state.
 */
const api = createApi("/api/onboarding");

/** Only two subjects mean a client crossed the signature line. */
export type AlertKind = "signed" | "paid";

export type ClientState =
  | "PRE_EXISTING"
  | "AWAITING_PAIR"
  | "READY"
  | "DRAFTED"
  /* Wave 1 approved — the setup batch. NOT the end of the record: the
     scheduling wave still has to happen once the calls are booked. */
  | "APPROVED"
  /* Wave 2 approved — the dates. */
  | "SCHEDULED"
  | "IGNORED";

/**
 * `dated`   computable from the signature date alone
 * `pending` anchored to a call that has not been scheduled yet
 * `gated`   blocked on a client action, so it gets NO DATE EVER
 */
/* FOUR, not three. "pending" collapsed a task waiting for a call it will get
   with one that has no scheduling rule and never will — and 66 of the 92 ads
   tasks are in the second group. `pending` is retained so a draft stored
   before the split still loads. */
export type DueState = "dated" | "awaiting_anchor" | "unscheduled" | "gated" | "pending";

export interface AlertHalf {
  fingerprint: string;
  firstName: string | null;
  amount: number | null;
  currency: string | null;
  /** "forwarded" is the honest label for every sample that exists today. */
  source: "forwarded" | "direct";
  sender: string | null;
  senderIsDubsado: boolean;
  /** The original alert's date, verbatim from the forwarded header. On a
      forward this is NOT the envelope date. Human-readable, for display. */
  originalDate: string | null;
  /** The same instant as ISO. Due-date arithmetic reads this one. */
  originalDateIso: string | null;
  receivedAt: string | null;
  recordedAt: string | null;
}

/** How much to trust a resolved assignee. Shown per row so a reviewer knows
    which ones actually need looking at. */
export type AssigneeConfidence = "certain" | "likely" | "heuristic" | "ambiguous" | "unknown";

export interface DraftTask {
  id: string;
  title: string;
  /** The destination LIST, not an abstract template — a both-offers client
      gets two lists side by side in one folder. */
  template: string | null;
  assignee: string | null;
  /** THEIR field. Set on 299 of 308 template tasks against only 190 with a real
      assignee, so it is the better source of ownership. */
  role: string | null;
  phase: string | null;
  assigneeConfidence: AssigneeConfidence;
  assigneeInTemplate: string | null;
  isSubtask: boolean;
  /** The relationship, not just the fact of one. */
  parentId: string | null;
  parentTitle: string | null;
  hasDescription: boolean;
  checklistItems: string[];
  templateKey: string | null;
  /** Days after THIS TASK'S anchor. Null = no scheduling rule. */
  offsetDays: number | null;
  /** Which call moves this row when it is rescheduled. */
  anchorKey: string | null;
  scheduleConfirmed: boolean;
  scheduleNote: string | null;
  dueDate: string | null;
  dueState: DueState;
  dueAnchor: string | null;
  /** A deliberate override survives a reschedule; a calculated date does not. */
  dateSource: "calculated" | "manual" | null;
  /** An unresolved item a reviewer consciously deferred, with a named owner. */
  deferredTo: string | null;
  note: string | null;
  /** false = a reviewer dropped it. The row survives so the approved batch
      records what was declined as well as what was approved. */
  include: boolean;
}

export interface DraftList {
  key: string | null;
  name: string;
  listId: string | null;
  taskCount: number | null;
}

export interface Draft {
  tasks: DraftTask[];
  templates: string[];
  /** One entry per ClickUp list that would be created in the client folder. */
  lists: DraftList[];
  destination: {
    model: string | null;
    space: string | null;
    folder: string | null;
    /** Read off the workspace, or inferred. */
    confirmed: boolean;
    /** No approved destination — approval is blocked. */
    manualSetup: boolean;
    evidence: string | null;
    decision: string | null;
  } | null;
  /** Booked call dates, keyed by anchor. Empty at signature. */
  anchors: Record<string, string>;
  /** One line per anchor still waiting, keyed so it can be retired. */
  anchorWarnings: Record<string, string>;
  generatedAt: string | null;
  sourceNote: string | null;
  /** True only while the task list is invented. False now that the real
      ClickUp templates are read. */
  placeholder: boolean;
  warnings: string[];
}

/* ── Steps 2-4 ────────────────────────────────────────────────────
   The ClickUp draft above is step 1. These three follow it: the Google Drive
   client folder, the welcome email, and the Slack channel with its two posts.

   Same boundary as step 1 — a plan a human edits and approves, and nothing is
   written. There is no Drive, Gmail or Slack client in this codebase. */
export type StageKey = "drive" | "email" | "slack";

/** `ready` now · `pending` waiting on a call · `gated` waiting on the client.
    Deliberately the same three-state vocabulary the task table uses. */
export type StageItemState = "ready" | "pending" | "gated";

/** Where a row's value came from, badged per row so a reviewer can see which
    values were read out of something real. */
export type ItemSource =
  | "from-alert"
  | "from-sales-call"
  | "template-copy"
  | "computed"
  | "from-step"
  | "human"
  | "awaiting-client";

export interface StageItem {
  id: string;
  title: string;
  detail: string | null;
  group: string | null;
  source: ItemSource | string;
  state: StageItemState;
  confidence: AssigneeConfidence;
  note: string | null;
  include: boolean;
}

/** A Slack post. `edited` stops a reviewer's rewrite being clobbered when the
    kickoff date arrives and the templates re-render. */
export interface StageMessage {
  id: string;
  label: string;
  sourceTask: string | null;
  body: string;
  edited: boolean;
  include: boolean;
}

export interface StageStructureRow {
  depth: number;
  text: string;
  note: string | null;
  chip: string | null;
  href: string | null;
  /** Envelope rows use label/value instead of text. */
  label: string | null;
  value: string | null;
  muted: boolean;
}

export interface StagePlan {
  key: StageKey;
  order: number | null;
  title: string;
  subtitle: string | null;
  system: string | null;
  structure: { kind: "tree" | "envelope" | string; rows: StageStructureRow[] };
  items: StageItem[];
  messages: StageMessage[];
  /** Non-null while the step cannot be approved. Step 4 carries one until both
      kickoff dates are known, because its posts name both. */
  gate: { blockedBy: string | null; label: string | null; hint: string | null } | null;
  /** Which kickoff dates step 4 holds. Two, not one — on the one live client
      the two calls were 34 days apart, so neither is derived from the other. */
  anchors: { leadlock: string | null; ads: string | null } | null;
  warnings: string[];
  sourceNote: string | null;
}

export interface Stage {
  key: StageKey;
  state: "OPEN" | "APPROVED";
  plan: StagePlan;
  approvedPlan: StagePlan | null;
  approvedAt: string | null;
}

export interface StageSummary {
  total: number;
  ready: number;
  pending: number;
  gated: number;
  excluded: number;
  messages: number;
  needsConfirm: number;
  blocked: boolean;
}

export interface OnboardingClient {
  projectKey: string;
  projectName: string;
  state: ClientState;
  halves: { signed: AlertHalf | null; paid: AlertHalf | null };
  offers: string[];
  draft: Draft | null;
  approvedBatch: Draft | null;
  /** Steps 2-4, opened when step 1 is approved. Empty before that. */
  stages: Stage[];
  provisioned: boolean;
  repeatAlerts: { kind: AlertKind; fingerprint: string; amount: number | null; at: string | null }[];
  firstSeenAt: string | null;
  pairedAt: string | null;
  activatedAt: string | null;
  approvedAt: string | null;
  ignoredAt: string | null;
  ignoreReason: string | null;
  ignoreNote: string | null;
}

export interface Offer {
  key: string;
  label: string;
  note: string;
  /** Only two offers were ever named as having a template. */
  templateConfirmed: boolean;
}

export interface Board {
  seeded: boolean;
  seededAt: string | null;
  seedNote: string | null;
  lastPollAt: string | null;
  clients: OnboardingClient[];
  status: {
    seeded: boolean;
    total: number;
    counts: Record<ClientState, number>;
    durable: boolean;
    loadError: string | null;
  };
  offers: Record<string, Offer>;
  callAnchors: Record<string, { label: string; booked: string }>;
}

export interface DraftSummary {
  total: number;
  dated: number;
  awaitingAnchor: number;
  unscheduled: number;
  gated: number;
  excluded: number;
  deferred: number;
  unresolvedAssignee: number;
  needsConfirm: number;
  /** Non-empty means approval is refused. Recomputed locally as a reviewer
      edits, so the gate moves with the edits rather than with a round trip. */
  blockers: { kind: string; count: number; label: string }[];
}

export type IngestOutcome =
  | "not_seeded"
  | "rejected"
  | "half_pending"
  | "half_replaced"
  | "pair_completed"
  | "duplicate_half"
  | "already_provisioned"
  | "recurring_payment";

export const getBoard = async (): Promise<Board> => (await api.get("")).data;

/* Empties the store and drops the seed flag — the state a first boot finds.
   Called on every mount of the console so the demo never resumes mid-flow.
   Leaves the board UNSEEDED by design; `ingestAlert` refuses until
   `seedBoard` runs, and that gate is deliberate. */
export const resetBoard = async (): Promise<Board> => (await api.post("/reset")).data;

export const seedBoard = async (projectNames: string[], note?: string) =>
  (await api.post("/seed", { projectNames, note })).data;

/**
 * Ingest one alert.
 *
 * Today this is a paste: Gmail scope on hello@weddingindustryads.com was never
 * requested, so there is no mailbox to poll. The shape matches a poller's
 * inner loop so swapping a real Gmail read in later changes the caller only.
 */
export const ingestAlert = async (input: {
  subject: string;
  body?: string;
  from?: string;
  receivedAt?: string;
}): Promise<{ outcome: IngestOutcome; client: OnboardingClient | null }> =>
  (await api.post("/ingest", input)).data;

export const activateClient = async (
  projectKey: string,
  offers: string[],
  signatureDate?: string | null,
): Promise<{ client: OnboardingClient; summary: DraftSummary }> =>
  (await api.post(`/${encodeURIComponent(projectKey)}/activate`, { offers, signatureDate })).data;

export const saveDraft = async (
  projectKey: string,
  draft: Draft,
): Promise<{ client: OnboardingClient; summary: DraftSummary }> =>
  (await api.put(`/${encodeURIComponent(projectKey)}/draft`, { draft })).data;

/** The gate. Records what a human authorised, then stops. */
export const approveBatch = async (
  projectKey: string,
  draft: Draft,
  /* "setup" is the pre-booking batch; "schedule" approves the dates once the
     calls are booked. Two waves, because a client signs before they book. */
  wave: "setup" | "schedule" = "setup",
): Promise<{ client: OnboardingClient; summary: DraftSummary }> =>
  (await api.post(`/${encodeURIComponent(projectKey)}/approve`, { draft, wave })).data;

/**
 * WAVE 2+ — a call gets booked.
 *
 * One anchor at a time. The tasks hanging off THAT anchor date themselves and
 * nothing else moves, so a LeadLock kickoff cannot invent ads deadlines. A
 * reviewer's deliberate override is preserved; a previously calculated date
 * is recomputed, which is what lets a postponed call actually move things.
 */
export const applyAnchorDate = async (
  projectKey: string,
  anchor: string,
  date: string,
): Promise<{
  client: OnboardingClient;
  computed: number;
  preserved: number;
  summary: DraftSummary;
}> => (await api.post(`/${encodeURIComponent(projectKey)}/anchor`, { anchor, date })).data;

/** The anchors, and who books each one. Mirrors ANCHORS in onboarding-plan.mjs. */
export const ANCHOR_LABELS: Record<string, { label: string; booked: string; clientGated?: boolean }> = {
  signed_and_paid: {
    label: "Signed and first payment received",
    booked: "Automatic — the alert pair is what opens this record",
  },
  ads_kickoff: {
    label: "Ads kickoff call",
    booked: "The CLIENT books it, via the welcome-email link",
  },
  messaging_positioning: {
    label: "Messaging & positioning interview",
    booked: "A second Whitney call, booked separately",
  },
  ad_strategy: {
    label: "Ad strategy presentation",
    booked: "Whitney and Carmen — “shortly after” the positioning interview",
  },
  leadlock_kickoff: {
    label: "LeadLock kickoff call",
    booked: "Danielle. Runs in PARALLEL with the ads track",
  },
  internal_tests: {
    label: "Internal and client testing complete",
    booked: "A team milestone, not a booked call",
  },
  launch_approval: {
    label: "Client approves launch",
    booked: "The CLIENT decides — a waiting state, not a date",
    clientGated: true,
  },
};

/** A reviewer's edits to one of steps 2-4, saved without approving. */
export const saveStage = async (
  projectKey: string,
  stage: StageKey,
  plan: StagePlan,
): Promise<{ client: OnboardingClient; summary: StageSummary }> =>
  (await api.put(`/${encodeURIComponent(projectKey)}/stage/${stage}`, { plan })).data;

/** The gate for one of steps 2-4. Records the authorisation and stops. */
export const approveStage = async (
  projectKey: string,
  stage: StageKey,
  plan: StagePlan,
): Promise<{ client: OnboardingClient; summary: StageSummary }> =>
  (await api.post(`/${encodeURIComponent(projectKey)}/stage/${stage}/approve`, { plan })).data;

/**
 * The kickoff bookings arriving after step 1 was approved.
 *
 * The only way through step 4's gate. `kickoffDate` is the LeadLock/phase
 * anchor and also recomputes the ClickUp due dates; `adsKickoffDate` feeds
 * step 4's posts only. Either may be sent alone. Any message body a reviewer
 * edited is left alone.
 */
export const applyStageKickoff = async (
  projectKey: string,
  anchors: { kickoffDate?: string; adsKickoffDate?: string },
): Promise<{ client: OnboardingClient; computed: number }> =>
  (await api.post(`/${encodeURIComponent(projectKey)}/stage-kickoff`, anchors)).data;

export const ignoreClient = async (projectKey: string, reason: string, note?: string) =>
  (await api.post(`/${encodeURIComponent(projectKey)}/ignore`, { reason, note })).data;

/** Recompute the header counts locally as a reviewer edits. */
export const summarize = (draft: Draft | null): DraftSummary => {
  const all = draft?.tasks ?? [];
  const kept = all.filter((task) => task.include);
  /* A deferral is a decision with a name on it, so it clears the blocker.
     Leaving the row unresolved does not. */
  const missingOwner = kept.filter((t) => !t.assignee && t.role !== "Client" && !t.deferredTo);
  const guessedOwner = kept.filter(
    (t) => ["ambiguous", "heuristic"].includes(t.assigneeConfidence) && !t.deferredTo,
  );
  return {
    blockers: [
      ...(draft?.destination?.manualSetup
        ? [
            {
              kind: "destination",
              count: 1,
              label: "No approved ClickUp destination for this package",
            },
          ]
        : []),
      ...(missingOwner.length
        ? [{ kind: "owner", count: missingOwner.length, label: "tasks with no owner" }]
        : []),
      ...(guessedOwner.length
        ? [
            {
              kind: "ambiguous",
              count: guessedOwner.length,
              label: "tasks whose owner was guessed, not given",
            },
          ]
        : []),
    ],
    total: kept.length,
    dated: kept.filter((t) => t.dueState === "dated").length,
    /* Two different things, deliberately not summed: one waits for a call
       and will date itself, the other never will. */
    awaitingAnchor: kept.filter((t) => t.dueState === "awaiting_anchor").length,
    unscheduled: kept.filter((t) => t.dueState === "unscheduled").length,
    gated: kept.filter((t) => t.dueState === "gated").length,
    deferred: kept.filter((t) => t.deferredTo).length,
    excluded: all.length - kept.length,
    unresolvedAssignee: kept.filter((t) => !t.assignee && t.role !== "Client").length,
    needsConfirm: kept.filter((t) =>
      ["ambiguous", "heuristic"].includes(t.assigneeConfidence),
    ).length,
  };
};

/** Recompute a step's header counts locally as a reviewer edits, mirroring
    summarizeStage in server/onboarding-stages.mjs. */
export const summarizeStagePlan = (plan: StagePlan | null): StageSummary => {
  const all = plan?.items ?? [];
  const kept = all.filter((i) => i.include);
  const messages = (plan?.messages ?? []).filter((m) => m.include);
  return {
    total: kept.length + messages.length,
    ready: kept.filter((i) => i.state === "ready").length,
    pending: kept.filter((i) => i.state === "pending").length,
    gated: kept.filter((i) => i.state === "gated").length,
    excluded: all.length - kept.length,
    messages: messages.length,
    needsConfirm: kept.filter((i) => ["heuristic", "ambiguous", "unknown"].includes(i.confidence))
      .length,
    blocked: Boolean(plan?.gate),
  };
};
