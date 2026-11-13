/* ────────────────────────────────────────────────────────────────
   The obligation ledger — ONE work item, seen from four screens.

   WHY THIS FILE EXISTS. Inbox, Meetings, Ops Watch and Client Hub used to
   hold four separate state models for the same piece of work. Approving a
   draft closed the inbox row; posting a nudge cleared the Ops Watch risk;
   the Client Hub commitment ledger was static and moved for neither. So the
   demo could show Whitney a falling risk count while nobody had replied,
   sent or delivered anything.

   An OBLIGATION is the single identifiable work item. It carries the links
   the client's own operation already has — the Gmail thread, the meeting it
   was promised on, the Slack channel it was dispatched to, the ClickUp task
   that tracks it, and the account it belongs to — and exactly one lifecycle
   stage (see WORK_STAGES in lib/opsHub.ts). Every screen is a view of that
   stage; none of them owns a private copy.

   WHAT IS DELIBERATELY *NOT* HERE. This is not a second task manager. There
   is no create, no edit, no assignment UI. ClickUp stays the system of record
   for task execution (Sept 2 @42:16 — the team "check off the tasks" there and
   nothing else). This ledger only tracks the handful of states an operations
   layer has to know to chase and confirm work: prepared, approved, drafted,
   sent, waiting on an acknowledgement, in progress, done, client told.
   ──────────────────────────────────────────────────────────────── */

import type { SourceKey, WorkStage } from "@/lib/opsHub";

export type ObligationLinks = {
  /** Gmail rows in the Inbox corpus that are views of this obligation. */
  emails?: string[];
  /** Commitment ledger rows on the Client Hub. */
  commitments?: string[];
  /** Ops Watch chase rows. */
  teamActions?: string[];
  /** `${meetingId}:${taskId}` for the meeting that created it. */
  meetingTasks?: string[];
  /** Invoice ids in the money ledger. */
  invoices?: string[];
  /** The Slack channel the dispatch lands in. */
  slack?: string;
  /** The ClickUp task that tracks execution — theirs, not ours. */
  clickup?: string;
};

export type Obligation = {
  id: string;
  title: string;
  clientId: string;
  /** Who owes the work. A client name here means we are waiting on them. */
  owner: string;
  /** Where it was promised, in one line a reviewer can check. */
  origin: string;
  /** True when finishing it requires telling the client. Only these can
      reach `client_informed`; for the rest, `completed` is the end. */
  clientFacing: boolean;
  /** Stage before anyone touches the demo. */
  seed: WorkStage;
  /** Parent obligation this one is a step of.

      WHY THERE IS A HIERARCHY. "Deliver the revised landing page" is the
      obligation; the reply telling the client when, and the email carrying the
      finished link, are two separate communications that serve it. Flattening
      them would make approving one draft appear to advance the other. Nesting
      them means the parent CANNOT read further ahead than its least advanced
      step — see `deriveStage` — so a delivery cannot look done while its
      client handoff is still sitting in drafts. */
  partOf?: string;
  links: ObligationLinks;
};

export const OBLIGATIONS: Obligation[] = [
  /* ── Bloom Manor — the fully-sourced account. The Sep 2 strategy call
        produced four WIA commitments and one client one; each is an
        obligation here, and the walkthrough in the review notes follows
        ob-bloom-lp from a client email all the way to "client informed". */
  {
    id: "ob-bloom-lp",
    title: "Deliver the revised landing page to Bloom Manor",
    clientId: "bloom",
    owner: "Jacqueline",
    origin: "Sep 2 strategy call · 24:18 — “We’ll have the revised page over to you this week.”",
    clientFacing: true,
    seed: "in_progress",
    links: {
      commitments: ["cm-bloom-1"],
      meetingTasks: ["bloom-strategy:t1"],
      slack: "#client-bloom-manor",
      clickup: "Landing Page QA · In Progress",
    },
  },
  {
    /* Step 1 — answer the client's "when?" while the work is still running. */
    id: "ob-bloom-lp-timing",
    title: "Tell Sarah when the revised page lands",
    clientId: "bloom",
    owner: "Whitney",
    origin: "Incoming Gmail · client asking for an update",
    clientFacing: true,
    seed: "review_pending",
    partOf: "ob-bloom-lp",
    links: { emails: ["e1"], slack: "#client-bloom-manor" },
  },
  {
    /* Step 2 — the actual handoff. Until this is SENT, ob-bloom-lp cannot
       read completed, however green the ClickUp task looks. */
    id: "ob-bloom-lp-handoff",
    title: "Send Bloom Manor the revised page link",
    clientId: "bloom",
    owner: "Gisselle",
    origin: "Slack #client-bloom-manor — Jacqueline: “Final QA is done”",
    clientFacing: true,
    seed: "review_pending",
    partOf: "ob-bloom-lp",
    links: { emails: ["e6"], slack: "#client-bloom-manor" },
  },
  {
    id: "ob-bloom-keywords",
    title: "Review Bloom Manor keyword exclusions before the next flight",
    clientId: "bloom",
    owner: "Carmen",
    origin: "Sep 2 strategy call · 31:05",
    clientFacing: false,
    seed: "in_progress",
    links: {
      commitments: ["cm-bloom-2"],
      meetingTasks: ["bloom-strategy:t2"],
      slack: "#client-bloom-manor",
      clickup: "Keyword exclusions · Open",
    },
  },
  {
    /* The unacknowledged one. Seeded at `waiting_ack`, which is what makes
       Ops Watch's risk count real: nudging it adds an event and changes
       nothing else. Only an acknowledgement moves it. */
    id: "ob-bloom-testimonial",
    title: "Update the Bloom Manor testimonial creative",
    clientId: "bloom",
    owner: "Jacqueline",
    origin: "Sep 2 strategy call · 31:05 — dispatched to Slack, no reaction since",
    clientFacing: false,
    seed: "waiting_ack",
    links: {
      commitments: ["cm-bloom-3"],
      teamActions: ["ack-jacqueline"],
      slack: "#client-bloom-manor",
      clickup: "Testimonial creative · Open · due yesterday",
    },
  },
  {
    id: "ob-bloom-recap",
    title: "Send the Bloom Manor call recap",
    clientId: "bloom",
    owner: "Gisselle",
    origin: "Sep 2 strategy call · 42:18",
    clientFacing: true,
    seed: "completed",
    links: {
      commitments: ["cm-bloom-4"],
      meetingTasks: ["bloom-strategy:t3"],
      slack: "#client-bloom-manor",
    },
  },
  {
    /* The completion update. It exists ONLY to close the loop on ob-bloom-lp
       and its siblings, which is why the Inbox row for it is gated: it cannot
       be approved while any client-facing Bloom obligation is still open. */
    id: "ob-bloom-completion",
    title: "Tell Bloom Manor everything from the Sep 2 call is done",
    clientId: "bloom",
    owner: "Whitney",
    origin: "Derived — fires when the call’s client-facing commitments close",
    clientFacing: true,
    seed: "review_pending",
    links: { emails: ["e3"], slack: "#client-bloom-manor" },
    /* Gated in the Inbox: it claims every client-facing commitment from the
       Sep 2 call is complete, so it cannot be approved while one is open.
       See `completionBlockers` in hooks/useOpsHub.ts. */
  },
  {
    id: "ob-bloom-gallery",
    title: "Bloom Manor to send the October gallery assets",
    clientId: "bloom",
    owner: "Sarah Mitchell (client)",
    origin: "Sep 2 strategy call — client agreed to send after the call",
    clientFacing: false,
    seed: "waiting_reply",
    links: { emails: ["e9"], commitments: ["cm-bloom-5"] },
  },
  {
    id: "ob-bloom-thanks",
    title: "Bloom Manor “thanks” thread — filing decision",
    clientId: "bloom",
    owner: "Gisselle",
    origin: "Incoming Gmail, no action detected — classifier abstained",
    clientFacing: false,
    seed: "unread",
    links: { emails: ["e14"] },
  },

  /* ── Rosewood Venue — the account that shows the same obligation in three
        places. e7 is the email, ack-carmen is the Ops Watch chase and
        cm-rose-2 is the commitment. One stage drives all three. */
  {
    id: "ob-rosewood-reply",
    title: "Reply to Dana’s question from Thursday",
    clientId: "rosewood",
    owner: "Carmen",
    origin: "Client Gmail thread · 29 business hours with no reply",
    clientFacing: true,
    seed: "unread",
    links: {
      emails: ["e7"],
      commitments: ["cm-rose-2"],
      teamActions: ["ack-carmen"],
      slack: "#client-rosewood",
      clickup: "No task created",
    },
  },
  {
    id: "ob-rosewood-budget",
    title: "Answer Rosewood’s budget-shift question",
    clientId: "rosewood",
    owner: "Whitney",
    origin: "Incoming Gmail · client decision needed",
    clientFacing: true,
    seed: "review_pending",
    links: { emails: ["e2"], slack: "#client-rosewood" },
  },
  {
    id: "ob-rosewood-gallery",
    title: "Rosewood to send the requested gallery assets",
    clientId: "rosewood",
    owner: "Dana Whitfield (client)",
    origin: "Requested by Gisselle · 12 days with no reply",
    clientFacing: false,
    seed: "waiting_reply",
    links: { emails: ["e10"], commitments: ["cm-rose-4"] },
  },
  {
    id: "ob-rosewood-invoice",
    title: "Recover INV-204 · $1,850 · 5 days overdue",
    clientId: "rosewood",
    owner: "Gisselle",
    origin: "HighLevel (WIA account) invoice status · standard reminder already sent",
    clientFacing: true,
    seed: "review_pending",
    links: { emails: ["e12"], invoices: ["INV-204"] },
  },

  /* ── Everly, Willow, Harbor, Magnolia ── */
  {
    id: "ob-everly-replay",
    title: "Send Nina the Office Hours replay link",
    clientId: "everly",
    owner: "Gisselle",
    origin: "Incoming Gmail · admin reply",
    clientFacing: true,
    seed: "review_pending",
    links: { emails: ["e5"], commitments: ["cm-everly-2"] },
  },
  {
    id: "ob-harbor-cadence",
    title: "Answer Harbor House on the reporting cadence",
    clientId: "harbor",
    owner: "Gisselle",
    origin: "Incoming Gmail · operational answer only",
    clientFacing: true,
    seed: "review_pending",
    links: { emails: ["e4"] },
  },
  {
    id: "ob-harbor-creative",
    title: "Approve the Harbor House creative swap",
    clientId: "harbor",
    owner: "Jacqueline",
    origin: "Client Gmail thread · 26 business hours, approaching the expectation",
    clientFacing: true,
    seed: "unread",
    links: { emails: ["e8"], slack: "#client-harbor-house" },
  },
  {
    id: "ob-magnolia-proposal",
    title: "Send the Elevate proposal to Magnolia House",
    clientId: "magnolia",
    owner: "Whitney",
    origin: "Sep 3 sales call · prospect asked for Elevate scope and timeline",
    clientFacing: true,
    seed: "review_pending",
    links: { emails: ["e11"], commitments: ["cm-mag-1"] },
  },

  /* ── Not client work ── */
  {
    id: "ob-canva-news",
    title: "Canva product newsletter — file it",
    clientId: "",
    owner: "Gisselle",
    origin: "Tools label · read by Whitney, no action detected",
    clientFacing: false,
    seed: "unread",
    links: { emails: ["e13"] },
  },
];

/* ── Reverse indexes. Built once; every screen looks up through these so a
      link can never be maintained in two directions and disagree. */

const index = <K extends keyof ObligationLinks>(key: K) => {
  const map: Record<string, string> = {};
  for (const o of OBLIGATIONS) {
    const values = o.links[key];
    if (Array.isArray(values)) for (const v of values) map[v] = o.id;
  }
  return map;
};

export const OBLIGATION_BY_EMAIL = index("emails");
export const OBLIGATION_BY_COMMITMENT = index("commitments");
export const OBLIGATION_BY_TEAM_ACTION = index("teamActions");
export const OBLIGATION_BY_MEETING_TASK = index("meetingTasks");
export const OBLIGATION_BY_INVOICE = index("invoices");

export const OBLIGATION_META = Object.fromEntries(
  OBLIGATIONS.map((o) => [o.id, o]),
) as Record<string, Obligation>;

export const CHILDREN_OF: Record<string, string[]> = OBLIGATIONS.reduce(
  (acc, o) => {
    if (o.partOf) (acc[o.partOf] ??= []).push(o.id);
    return acc;
  },
  {} as Record<string, string[]>,
);

/** The obligation whose completion the Bloom completion update claims. */
export const COMPLETION_UPDATE_SCOPE: Record<string, string[]> = {
  "ob-bloom-completion": ["ob-bloom-lp", "ob-bloom-recap"],
};

/** Where each link type lives, for the "one item, five systems" strip. */
export const LINK_SOURCE: Record<string, SourceKey> = {
  emails: "gmail",
  slack: "slack",
  clickup: "clickup",
  meetingTasks: "zoom",
  invoices: "highlevel",
};
