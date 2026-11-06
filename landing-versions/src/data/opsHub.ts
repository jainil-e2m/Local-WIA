/* ────────────────────────────────────────────────────────────────
   Ops Hub — the demo corpus.

   ALL SYNTHETIC. Client names, invoice numbers, transcript timestamps and
   quotes below are invented for the walkthrough. They are deliberately NOT
   the real book: the real client in the ClickUp snapshot is Ridgefield
   Weddings and Events, and using real client data in a screen-shared demo
   would put a live account on a projector.

   Two gaps were carried over from the source mock and have now been closed.
   Both are recorded here because the fix is a claim about the client's real
   operation, not a cosmetic one:

   1. THE ROSTER. It read Whitney, Gisselle, Carmen, Jacqueline, Danielle.
      TINA and IVY were missing (Sept 2 @25:50 names both: Ivy is the ads
      creative designer, Tina the LeadLock/GHL designer). Tina also owns
      monthly client reporting — "dedicating the first few business days of
      the month" (Sept 2 @33:01), derived at 18–24 hrs/month, the largest
      single recurring cost anywhere in discovery. Both are on the roster
      below, and Tina's monthly report run appears on Home and in the
      routines table so that cost is visible rather than implied.

   2. SERVICE NAMES. Two accounts read "Amplify", a name that appears nowhere
      in the client's own material. Every account below now carries a real
      offer name: Elevate (the published ads retainer), Foolproof Follow-Up
      Advantage (the LeadLock/GHL offer, Sept 2 @20:59), and the Google
      Search / Meta Ads Accelerators that feed the members portal.
   ──────────────────────────────────────────────────────────────── */

import type { AutoSystem, ScreenId, SourceKey, Tone, WorkStage } from "@/lib/opsHub";
import { STAGE_META, isAcknowledged } from "@/lib/opsHub";
import { OBLIGATION_BY_COMMITMENT } from "@/data/obligations";

export const TEAM: Record<string, string> = {
  Whitney: "W",
  Gisselle: "G",
  Carmen: "C",
  Jacqueline: "J",
  Danielle: "D",
  Tina: "T",
  Ivy: "I",
};

/* ── Clients ──────────────────────────────────────────────────── */

export type Client = {
  id: string;
  name: string;
  contact: string;
  email: string;
  service: string;
  status: "active" | "prospect";
  opStatus: string;
  lastComm: string;
  open: number;
  overdue: number;
  waitingOn: string;
  waitingDays: number;
  next: string;
};

export const CLIENTS: Client[] = [
  {
    id: "bloom",
    name: "Bloom Manor",
    contact: "Sarah Mitchell",
    email: "sarah@bloommanor.com",
    service: "Elevate",
    status: "active",
    opStatus: "Landing-page handoff",
    lastComm: "Today · Gmail",
    open: 7,
    overdue: 1,
    waitingOn: "October gallery assets",
    waitingDays: 5,
    next: "Sep 24 · Strategy call",
  },
  {
    id: "rosewood",
    name: "Rosewood Venue",
    contact: "Dana Whitfield",
    email: "dana@rosewoodvenue.com",
    service: "Elevate + Foolproof Follow-Up",
    status: "active",
    opStatus: "Invoice + recap follow-up",
    lastComm: "2d ago · Gmail",
    open: 4,
    overdue: 1,
    waitingOn: "Requested gallery assets",
    waitingDays: 12,
    next: "Sep 9 · Check-in",
  },
  {
    id: "everly",
    name: "Everly Estate",
    contact: "Nina Cole",
    email: "nina@everlyestate.com",
    service: "Google Search Accelerator",
    status: "active",
    opStatus: "Engagement at risk",
    lastComm: "9d ago · Portal",
    open: 2,
    overdue: 0,
    waitingOn: "",
    waitingDays: 0,
    next: "Sep 10 · Office Hours",
  },
  {
    id: "willow",
    name: "Willow & Pine",
    contact: "Maya Stone",
    email: "maya@willowandpine.com",
    service: "Meta Ads Accelerator",
    status: "active",
    opStatus: "Re-engagement needed",
    lastComm: "24d ago · Portal",
    open: 1,
    overdue: 0,
    waitingOn: "",
    waitingDays: 0,
    next: "Sep 10 · Office Hours",
  },
  {
    id: "magnolia",
    name: "Magnolia House",
    contact: "Tessa Ruiz",
    email: "tessa@magnoliahouse.com",
    service: "Prospect · Elevate",
    status: "prospect",
    opStatus: "Proposal follow-up due",
    lastComm: "Yesterday · Zoom",
    open: 1,
    overdue: 0,
    waitingOn: "",
    waitingDays: 0,
    next: "Sep 5 · Proposal review",
  },
  {
    id: "harbor",
    name: "Harbor House",
    contact: "Elena Park",
    email: "elena@harborhouse.com",
    service: "Foolproof Follow-Up Advantage",
    status: "active",
    opStatus: "Invoice 8 days overdue",
    lastComm: "4d ago · Gmail",
    open: 3,
    overdue: 0,
    waitingOn: "",
    waitingDays: 0,
    next: "Sep 11 · Monthly call",
  },
];

/* ── Inbox ────────────────────────────────────────────────────── */

export type EmailKind =
  | "draft"
  | "sla"
  | "waiting"
  | "sales"
  | "finance"
  | "noaction";

export type Email = {
  id: string;
  queue: string;
  sender: string;
  email: string;
  clientId: string;
  subject: string;
  age: string;
  classification: string;
  priority: "high" | "medium" | "low";
  owner: string;
  rec: string;
  trigger: string;
  kind: EmailKind;
  dest?: string;
  ambiguous?: boolean;
};

export const QUEUES: { id: string; label: string }[] = [
  { id: "needs_whitney", label: "Needs Whitney" },
  { id: "ready_gisselle", label: "Ready for Gisselle" },
  { id: "team_reply_due", label: "Team Reply Due" },
  { id: "waiting_client", label: "Waiting on Client" },
  { id: "sales_followup", label: "Sales Follow-Up" },
  { id: "finance_followup", label: "Finance Follow-Up" },
  { id: "no_action", label: "No Action / File" },
];

/* WHICH AXIS EACH LANE IS ON. The seven lanes above are the client's own
   working vocabulary and they stay — but they mix three different questions:
   two are about WHO owns it, two about WHAT STATE it is in, three about the
   SUBJECT. A reader could not tell why "Needs Whitney" and "Finance
   Follow-Up" were siblings, and an item could plausibly belong in both.

   Rather than invent a new taxonomy for a client who has not agreed to one,
   the lane keeps its name and declares its axis, and the two genuinely
   missing controls — filter by owner, filter by lifecycle state — sit beside
   the rail and cut ACROSS lanes. */
export const QUEUE_AXIS: Record<string, "owner" | "state" | "subject"> = {
  needs_whitney: "owner",
  ready_gisselle: "owner",
  team_reply_due: "state",
  waiting_client: "state",
  sales_followup: "subject",
  finance_followup: "subject",
  no_action: "subject",
};

export const AXIS_META: Record<"owner" | "state" | "subject", { label: string; tone: Tone }> = {
  owner: { label: "by owner", tone: "blue" },
  state: { label: "by state", tone: "amber" },
  subject: { label: "by subject", tone: "slate" },
};

export const EMAILS: Email[] = [
  {
    id: "e1",
    queue: "needs_whitney",
    sender: "Sarah Mitchell",
    email: "sarah@bloommanor.com",
    clientId: "bloom",
    subject: "Any update on the landing page?",
    age: "2h ago",
    classification: "Client reply needed",
    priority: "high",
    owner: "Whitney",
    rec: "AI Draft Ready — confirm delivery timing promised on the Sep 2 call.",
    trigger: "Incoming Gmail",
    kind: "draft",
  },
  {
    id: "e2",
    queue: "needs_whitney",
    sender: "Dana Whitfield",
    email: "dana@rosewoodvenue.com",
    clientId: "rosewood",
    subject: "Can we shift next month’s budget?",
    age: "5h ago",
    classification: "Client decision needed",
    priority: "high",
    owner: "Whitney",
    rec: "AI Draft Ready — Whitney approval required before any budget language goes out.",
    trigger: "Incoming Gmail",
    kind: "draft",
  },
  {
    id: "e3",
    queue: "needs_whitney",
    sender: "Ops Hub",
    email: "ai@weddingindustryads.com",
    clientId: "bloom",
    subject: "Completion update ready — Bloom Manor strategy call",
    age: "1h ago",
    classification: "Completion update",
    priority: "medium",
    owner: "Whitney",
    rec: "All client-facing actions from the Sep 2 call are complete. Review the update draft.",
    trigger: "Meeting action completion",
    kind: "draft",
  },
  {
    id: "e4",
    queue: "ready_gisselle",
    sender: "Elena Park",
    email: "elena@harborhouse.com",
    clientId: "harbor",
    subject: "Question on this month’s reporting cadence",
    age: "1d ago",
    classification: "Client reply needed",
    priority: "medium",
    owner: "Gisselle",
    rec: "AI Draft Ready — operational answer only, cadence confirmed in ClickUp.",
    trigger: "Incoming Gmail",
    kind: "draft",
  },
  {
    id: "e5",
    queue: "ready_gisselle",
    sender: "Nina Cole",
    email: "nina@everlyestate.com",
    clientId: "everly",
    subject: "Re: Office Hours replay link",
    age: "3h ago",
    classification: "Admin reply",
    priority: "low",
    owner: "Gisselle",
    rec: "Draft ready — replay link pulled from Drive session folder.",
    trigger: "Incoming Gmail",
    kind: "draft",
  },
  {
    id: "e6",
    queue: "ready_gisselle",
    sender: "Jacqueline",
    email: "jacqueline@weddingindustryads.com",
    clientId: "bloom",
    subject: "Landing page QA is done",
    age: "4h ago",
    classification: "Internal handoff",
    priority: "medium",
    owner: "Gisselle",
    rec: "Draft ready — hand off to client with revised link.",
    trigger: "Slack + Gmail",
    kind: "draft",
  },
  {
    id: "e7",
    queue: "team_reply_due",
    sender: "Dana Whitfield",
    email: "dana@rosewoodvenue.com",
    clientId: "rosewood",
    subject: "Following up on my question from Thursday",
    age: "29 business hrs",
    classification: "Reply SLA breach",
    priority: "high",
    owner: "Carmen",
    rec: "No reply detected after 29 business hours. Preview internal nudge.",
    trigger: "Reply SLA rule",
    kind: "sla",
  },
  {
    id: "e8",
    queue: "team_reply_due",
    sender: "Elena Park",
    email: "elena@harborhouse.com",
    clientId: "harbor",
    subject: "Creative swap approval?",
    age: "26 business hrs",
    classification: "Reply SLA at risk",
    priority: "medium",
    owner: "Jacqueline",
    rec: "Approaching the 24–48 business-hour expectation. Nudge owner.",
    trigger: "Reply SLA rule",
    kind: "sla",
  },
  {
    id: "e9",
    queue: "waiting_client",
    sender: "Bloom Manor",
    email: "sarah@bloommanor.com",
    clientId: "bloom",
    subject: "October gallery assets — outstanding",
    age: "Waiting 5 days",
    classification: "Waiting on client",
    priority: "medium",
    owner: "Gisselle",
    rec: "Follow up this week — new creative cannot be finalized without the gallery.",
    trigger: "Waiting rule",
    kind: "waiting",
  },
  {
    id: "e10",
    queue: "waiting_client",
    sender: "Rosewood Venue",
    email: "dana@rosewoodvenue.com",
    clientId: "rosewood",
    subject: "Requested gallery assets — outstanding",
    age: "Waiting 12 days",
    classification: "Waiting on client",
    priority: "high",
    owner: "Gisselle",
    rec: "Follow up now — recap is complete, creative work is blocked.",
    trigger: "Waiting rule",
    kind: "waiting",
  },
  {
    id: "e11",
    queue: "sales_followup",
    sender: "Tessa Ruiz",
    email: "tessa@magnoliahouse.com",
    clientId: "magnolia",
    subject: "Great call — send over the details?",
    age: "Yesterday",
    classification: "Sales follow-up",
    priority: "high",
    owner: "Whitney",
    rec: "Call outcome: interested in Elevate. Next step = send Elevate proposal.",
    trigger: "Sales call",
    kind: "sales",
  },
  {
    id: "e12",
    queue: "finance_followup",
    sender: "Rosewood Venue",
    email: "dana@rosewoodvenue.com",
    clientId: "rosewood",
    subject: "INV-204 · $1,850 · 5 days overdue",
    age: "5d overdue",
    classification: "Invoice follow-up",
    priority: "high",
    owner: "Gisselle",
    rec: "Standard HighLevel reminder already sent. Prepare a personal Gmail follow-up.",
    trigger: "Invoice rule",
    kind: "finance",
  },
  {
    id: "e13",
    queue: "no_action",
    sender: "Canva",
    email: "news@canva.com",
    clientId: "",
    subject: "New in Canva: Brand Kit updates",
    age: "6h ago",
    classification: "No action required",
    priority: "low",
    owner: "—",
    rec: "Read by Whitney. No reply, task or client impact detected.",
    trigger: "Incoming Gmail",
    kind: "noaction",
    dest: "Tools / Canva",
  },
  {
    id: "e14",
    queue: "no_action",
    sender: "Bloom Manor",
    email: "sarah@bloommanor.com",
    clientId: "bloom",
    subject: "Thanks! — no reply needed",
    age: "1d ago",
    classification: "Ambiguous",
    priority: "low",
    owner: "—",
    rec: "Likely no action, but the thread is client-facing. Keep in Inbox if unsure.",
    trigger: "Incoming Gmail",
    kind: "noaction",
    dest: "Client / Bloom Manor",
    /* Deliberately unresolved. An automation that never abstains is one that
       silently files a client thread it should have surfaced. */
    ambiguous: true,
  },
];

export const DRAFTS: Record<string, string> = {
  e1: "Hi Sarah,\n\nAbsolutely — the team is finishing the final QA now, and we’re expecting to have the updated page ready for you tomorrow.\n\nWe’ll send the revised link over as soon as those checks are complete.\n\nThank you!",
  e2: "Hi Dana,\n\nHappy to look at shifting next month’s budget. Before we move anything, I want to confirm the split you have in mind so the current tests aren’t interrupted mid-flight.\n\nCan you confirm the amount you’d like moved? I’ll come back with the operational impact today.\n\nThanks!",
  e3: "Hi Sarah,\n\nQuick update — everything we committed to on our last strategy call has now been completed.\n\n✓ Revised landing page\n✓ Keyword review\n✓ Testimonial creative update\n\nHere’s the updated page:\n[link]\n\nThanks!",
  e4: "Hi Elena,\n\nYour reporting cadence is unchanged — the monthly summary goes out on the first business day, and we review it together on our monthly call.\n\nI’ve noted your question and nothing needs to change on your side.\n\nThank you!",
  e5: "Hi Nina,\n\nHere’s the replay from last week’s Google Office Hours — it’s filed in your member portal as well.\n\n[Watch recording]\n\nLet me know if anything didn’t come through.",
  e6: "Hi Sarah,\n\nGood news — final QA on the revised page is complete. Here’s the updated link for your review:\n\n[link]\n\nIf anything looks off, send it back and we’ll adjust today.\n\nThank you!",
  e9: "Hi Sarah,\n\nOne quick follow-up — we’re still waiting on the October gallery assets. Once those land we can finalize the new creative set.\n\nCould you send them over this week?\n\nThank you!",
  e10: "Hi Dana,\n\nFollowing up on the gallery assets we requested — the recap from our last call is complete on our side, and the creative work is waiting on those images.\n\nAny chance you can send them across today or tomorrow?\n\nThank you!",
  e11: "Hi Tessa,\n\nGreat speaking with you — as promised, here’s the Elevate proposal covering the scope we discussed.\n\n[Elevate proposal]\n\nHappy to walk through it live if that’s easier. Just let me know a time that works.\n\nThank you!",
  e12: "Hi Dana,\n\nJust a quick personal note — invoice INV-204 ($1,850) is showing as unpaid and is now 5 days past due.\n\nIf it’s easier, here’s the payment link:\n[Open invoice]\n\nIf it’s already scheduled, ignore me entirely — just wanted to make sure it hadn’t slipped through.\n\nThank you!",
};

/* ── The exact artifact, not a summary of it ─────────────────────
   F04. The reviewer could see a paraphrase of the incoming thread and a body
   with no subject, no recipient and no attachment list — then press a button
   labelled "Approve". Approving something you cannot fully read is not a
   control, and human review is the main control this client was promised.

   `original` is the inbound message verbatim; `subject`, `to`, `cc` and
   `attachments` are what the created Gmail draft would actually carry. */

export type DraftEnvelope = {
  from: string;
  to: string;
  cc?: string;
  subject: string;
  attachments?: string[];
  /** The inbound message this replies to, verbatim rather than summarised. */
  original?: { from: string; when: string; subject: string; body: string };
};

export const ENVELOPES: Record<string, DraftEnvelope> = {
  e1: {
    from: "hello@weddingindustryads.com",
    to: "Sarah Mitchell <sarah@bloommanor.com>",
    subject: "Re: Any update on the landing page?",
    original: {
      from: "Sarah Mitchell <sarah@bloommanor.com>",
      when: "Today, 07:42",
      subject: "Any update on the landing page?",
      body:
        "Hi Whitney,\n\nJust checking in — on our call you mentioned the revised page would be with us this week. Is that still looking likely? I have a venue open house on Saturday and I would love to be sending traffic to the new one by then.\n\nNo rush if not, just want to plan around it.\n\nSarah",
    },
  },
  e2: {
    from: "hello@weddingindustryads.com",
    to: "Dana Whitfield <dana@rosewoodvenue.com>",
    subject: "Re: Can we shift next month’s budget?",
    original: {
      from: "Dana Whitfield <dana@rosewoodvenue.com>",
      when: "Today, 04:10",
      subject: "Can we shift next month’s budget?",
      body:
        "Morning — we had a slower month on enquiries than I expected and I am wondering whether we should move some of the Meta spend over to Google for October. What would you recommend? Happy to go with your call.\n\nDana",
    },
  },
  e3: {
    from: "hello@weddingindustryads.com",
    to: "Sarah Mitchell <sarah@bloommanor.com>",
    subject: "Everything from our Sep 2 call is done",
    attachments: ["Sep 2 Strategy — summary.pdf"],
  },
  e4: {
    from: "hello@weddingindustryads.com",
    to: "Elena Park <elena@harborhouse.com>",
    subject: "Re: Question on this month’s reporting cadence",
    original: {
      from: "Elena Park <elena@harborhouse.com>",
      when: "Yesterday, 16:20",
      subject: "Question on this month’s reporting cadence",
      body:
        "Hi — quick one. Are the monthly reports still coming at the start of the month, or has that moved? I want to line up our own board pack around it.\n\nElena",
    },
  },
  e5: {
    from: "hello@weddingindustryads.com",
    to: "Nina Cole <nina@everlyestate.com>",
    subject: "Re: Office Hours replay link",
    attachments: ["Replay link (member portal)"],
    original: {
      from: "Nina Cole <nina@everlyestate.com>",
      when: "Today, 06:15",
      subject: "Re: Office Hours replay link",
      body:
        "Hi Gisselle — I missed Thursday's Google session. Is there a recording anywhere? I could not find it in the portal.\n\nNina",
    },
  },
  e6: {
    from: "hello@weddingindustryads.com",
    to: "Sarah Mitchell <sarah@bloommanor.com>",
    subject: "Your revised landing page is ready",
    attachments: ["Revised page — preview link"],
    original: {
      from: "Jacqueline (Slack, #client-bloom-manor)",
      when: "Today, 05:50",
      subject: "Landing page QA is done",
      body:
        "Final QA is done on the Bloom revised page. Copy fixes are in, the form posts to the right list and the thank-you page redirect works. Safe to send to Sarah.",
    },
  },
  e9: {
    from: "hello@weddingindustryads.com",
    to: "Sarah Mitchell <sarah@bloommanor.com>",
    subject: "Following up — October gallery assets",
  },
  e10: {
    from: "hello@weddingindustryads.com",
    to: "Dana Whitfield <dana@rosewoodvenue.com>",
    subject: "Following up — gallery assets",
  },
  e11: {
    from: "hello@weddingindustryads.com",
    to: "Tessa Ruiz <tessa@magnoliahouse.com>",
    subject: "Your Elevate proposal",
    attachments: ["Elevate proposal (Dubsado link)"],
    original: {
      from: "Tessa Ruiz <tessa@magnoliahouse.com>",
      when: "Yesterday, 15:02",
      subject: "Great call — send over the details?",
      body:
        "Thanks for today, that was really helpful. Could you send over the details for the fuller package you mentioned? I would like to take it to my business partner this week.\n\nTessa",
    },
  },
  e12: {
    from: "hello@weddingindustryads.com",
    to: "Dana Whitfield <dana@rosewoodvenue.com>",
    subject: "Quick note — INV-204",
    attachments: ["Invoice payment link (HighLevel · WIA account)"],
  },
};

export const NUDGES: Record<string, string> = {
  e7: "Hey Carmen — Rosewood asked a question on Thursday and I don’t see a reply on the thread yet.\n\nIt’s at 29 business hours. Can you take it today, or should I hand it to Whitney?",
  e8: "Hey Jacqueline — Harbor House is waiting on creative-swap approval (26 business hours).\n\nCan you confirm on the thread today?",
};

/* The primary action per email kind: [label, resulting status, toast]. */
export const EMAIL_ACTIONS: Record<
  EmailKind,
  [string, "approved" | "filed" | "nudged", string]
> = {
  draft: ["Approve draft", "approved", "Draft created in Gmail — simulated"],
  waiting: [
    "Draft follow-up",
    "approved",
    "Follow-up draft created in Gmail — simulated",
  ],
  sla: [
    "Approve internal nudge",
    "nudged",
    "Internal nudge posted to Slack — simulated",
  ],
  sales: [
    "Approve proposal draft",
    "approved",
    "Elevate proposal draft created in Gmail — simulated",
  ],
  finance: [
    "Create personal draft",
    "approved",
    "Personal invoice reminder drafted in Gmail — simulated",
  ],
  noaction: ["Archive & file", "filed", "Archived and filed — simulated"],
};

export const DONE_LABEL: Record<string, string> = {
  approved: "Draft created in Gmail",
  filed: "Archived & filed",
  kept: "Kept in Inbox",
  nudged: "Nudge posted to Slack",
  snoozed: "Snoozed 4 hours",
};

/* ── Meetings ─────────────────────────────────────────────────── */

export type MeetingTask = {
  id: string;
  title: string;
  owner: string;
  due: string;
  ts: string;
};

export type Meeting = {
  id: string;
  title: string;
  type: "client" | "internal" | "sales" | "office_hours";
  source: SourceKey;
  clientId: string;
  date: string;
  duration: string;
  host: string;
  channel: string;
  decisions: string[];
  clientCommitments: string[];
  wiaCommitments: string[];
  risks: string[];
  tasks: MeetingTask[];
  moments: { ts: string; tag: string; text: string }[];
  files: [string, string][];
  fileDest: string;
  processed?: boolean;
  exceptions?: boolean;
};

export const MEETING_FILTERS: { id: string; label: string }[] = [
  { id: "needs_review", label: "Needs Review" },
  { id: "client", label: "Client" },
  { id: "internal", label: "Internal" },
  { id: "sales", label: "Sales" },
  { id: "office_hours", label: "Office Hours" },
  { id: "exceptions", label: "Exceptions" },
  { id: "processed", label: "Processed" },
];

export const MEETINGS: Meeting[] = [
  {
    id: "bloom-strategy",
    title: "Bloom Manor — Monthly Strategy",
    type: "client",
    source: "zoom",
    clientId: "bloom",
    date: "Sep 2",
    duration: "58 min",
    host: "Whitney",
    channel: "#client-bloom-manor",
    decisions: [
      "Testimonial creative test approved",
      "Revised page needs client handoff",
      "Keyword exclusions to be reviewed before next flight",
      "Recap to be sent same day",
    ],
    clientCommitments: ["Send October gallery Friday"],
    wiaCommitments: [
      "Deliver revised page",
      "Review keyword exclusions",
      "Update creative",
      "Send recap",
    ],
    risks: ["Client gallery still outstanding"],
    tasks: [
      {
        id: "t1",
        title: "Complete landing-page handoff",
        owner: "Jacqueline",
        due: "Tomorrow",
        ts: "24:18",
      },
      {
        id: "t2",
        title: "Review keyword exclusions",
        owner: "Carmen",
        due: "Friday",
        ts: "31:05",
      },
      {
        id: "t3",
        title: "Send client recap",
        owner: "Gisselle",
        due: "Today",
        ts: "42:18",
      },
    ],
    moments: [
      {
        ts: "24:18",
        tag: "Commitment",
        text: "“We’ll have the revised page over to you this week.”",
      },
      {
        ts: "31:05",
        tag: "Decision",
        text: "“Let’s pull the broad keywords before the next flight.”",
      },
      {
        ts: "31:42",
        tag: "Client win",
        text: "“We’ve had more venue tours this month than any month this year.”",
      },
      { ts: "42:18", tag: "Action", text: "“Gisselle will send the recap today.”" },
    ],
    files: [
      ["Recording.mp4", "recording"],
      ["Transcript.txt", "transcript"],
      ["Summary.md", "summary"],
      ["Action Items.md", "action items"],
    ],
    fileDest: "Drive / Clients / Bloom Manor / Meetings / 2026-09-02 Strategy",
  },
  {
    id: "monday-team",
    title: "Monday Team Meeting",
    type: "internal",
    source: "fathom",
    clientId: "",
    date: "Aug 31",
    duration: "42 min",
    host: "Gisselle",
    channel: "#team-ops",
    decisions: [
      "Weekly overdue review moves to Monday",
      "Harbor House creative swap approved internally",
    ],
    clientCommitments: [],
    wiaCommitments: [
      "Clear overdue client-facing tasks",
      "Confirm Office Hours host coverage",
      "Ship Rosewood recap",
    ],
    risks: ["Three overdue tasks are client-facing"],
    tasks: [
      {
        id: "i1",
        title: "Clear 3 overdue Bloom Manor tasks",
        owner: "Jacqueline",
        due: "Wednesday",
        ts: "06:12",
      },
      {
        id: "i2",
        title: "Rebuild Google keyword exclusion list",
        owner: "Carmen",
        due: "Thursday",
        ts: "11:40",
      },
      {
        id: "i3",
        title: "Post Rosewood recap + invoice note",
        owner: "Gisselle",
        due: "Today",
        ts: "18:22",
      },
      {
        id: "i4",
        title: "Confirm Office Hours host coverage",
        owner: "Gisselle",
        due: "Tomorrow",
        ts: "21:05",
      },
      {
        id: "i5",
        title: "Approve Harbor House creative swap",
        owner: "Whitney",
        due: "Today",
        ts: "26:31",
      },
      {
        id: "i6",
        title: "Update Meta audience exclusions",
        owner: "Carmen",
        due: "Friday",
        ts: "29:48",
      },
      {
        id: "i7",
        title: "Refresh testimonial creative brief in ClickUp",
        owner: "Jacqueline",
        due: "Friday",
        ts: "33:02",
      },
    ],
    moments: [
      {
        ts: "06:12",
        tag: "Risk",
        text: "“Three of the overdue ones are client-facing.”",
      },
      { ts: "18:22", tag: "Action", text: "“I’ll get the Rosewood recap out today.”" },
      {
        ts: "26:31",
        tag: "Decision",
        text: "“Approve the swap, but Whitney signs off.”",
      },
    ],
    files: [
      ["Recording.mp4", "recording"],
      ["Transcript.txt", "transcript"],
      ["Summary.md", "summary"],
      ["Action Items.md", "action items"],
    ],
    fileDest: "Drive / Internal / Team Meetings / 2026-08-31 Monday",
  },
  {
    id: "magnolia-sales",
    title: "Magnolia House — Discovery Call",
    type: "sales",
    source: "zoom",
    clientId: "magnolia",
    date: "Sep 3",
    duration: "34 min",
    host: "Whitney",
    channel: "#sales",
    decisions: ["Strong fit for Elevate", "Proposal to be sent before Friday"],
    clientCommitments: ["Confirm internal budget window"],
    wiaCommitments: ["Send Elevate proposal", "Share venue-tour benchmark example"],
    risks: ["Prospect comparing two agencies"],
    tasks: [
      {
        id: "s1",
        title: "Send Elevate proposal",
        owner: "Whitney",
        due: "Today",
        ts: "19:44",
      },
      {
        id: "s2",
        title: "Log prospect in HighLevel pipeline",
        owner: "Gisselle",
        due: "Today",
        ts: "30:10",
      },
    ],
    moments: [
      {
        ts: "19:44",
        tag: "Buying signal",
        text: "“Elevate sounds like the right level for us.”",
      },
      {
        ts: "30:10",
        tag: "Next step",
        text: "“Send the proposal and we’ll review Thursday.”",
      },
    ],
    files: [
      ["Recording.mp4", "recording"],
      ["Transcript.txt", "transcript"],
      ["Summary.md", "summary"],
    ],
    fileDest: "Drive / Sales / Magnolia House / 2026-09-03 Discovery",
  },
  {
    id: "rosewood-checkin",
    title: "Rosewood Venue — Monthly Check-in",
    type: "client",
    source: "fathom",
    clientId: "rosewood",
    date: "Aug 25",
    duration: "46 min",
    host: "Gisselle",
    channel: "#client-rosewood",
    decisions: ["Recap sent and acknowledged", "Gallery assets requested again"],
    clientCommitments: ["Send requested gallery assets"],
    wiaCommitments: ["Send recap", "Hold creative until assets arrive"],
    risks: ["Assets outstanding 12 days"],
    tasks: [
      {
        id: "r1",
        title: "Send check-in recap",
        owner: "Gisselle",
        due: "Aug 25",
        ts: "38:02",
      },
      {
        id: "r2",
        title: "Request gallery assets again",
        owner: "Gisselle",
        due: "Aug 26",
        ts: "40:15",
      },
    ],
    moments: [
      { ts: "38:02", tag: "Commitment", text: "“Recap goes out right after this call.”" },
    ],
    files: [
      ["Recording.mp4", "recording"],
      ["Transcript.txt", "transcript"],
      ["Summary.md", "summary"],
      ["Action Items.md", "action items"],
    ],
    fileDest: "Drive / Clients / Rosewood Venue / Meetings / 2026-08-25 Check-in",
    processed: true,
  },
  {
    id: "meta-office-hours",
    title: "Meta Ads Office Hours — Sep 3",
    type: "office_hours",
    source: "zoom",
    clientId: "",
    date: "Sep 3",
    duration: "61 min",
    host: "Whitney",
    channel: "#accelerator-internal",
    decisions: ["Session recap approved for the portal"],
    clientCommitments: [],
    wiaCommitments: [
      "Publish community recap",
      "File session assets",
      "Process attendance",
    ],
    risks: ["2 Zoom participants unmatched"],
    tasks: [
      {
        id: "o1",
        title: "Publish community recap post",
        owner: "Gisselle",
        due: "Today",
        ts: "58:30",
      },
      {
        id: "o2",
        title: "Match 2 unidentified participants",
        owner: "Gisselle",
        due: "Today",
        ts: "01:12",
      },
    ],
    moments: [
      {
        ts: "12:04",
        tag: "Teaching",
        text: "“Creative fatigue shows up in frequency before cost.”",
      },
      {
        ts: "44:20",
        tag: "Topic",
        text: "“Lead-form quality beats lead volume every time.”",
      },
    ],
    files: [
      ["Recording.mp4", "recording"],
      ["Summary.md", "summary"],
      ["Attendance.csv", "action items"],
    ],
    fileDest: "Drive / Accelerators / Meta Office Hours / 2026-09-03",
    processed: true,
  },
  {
    /* The deliberately broken pack. Four typed exceptions, each with real
       recovery copy — this is the most valuable screen in the whole hub,
       because a demo where everything succeeds teaches nobody what happens
       when a connector is not authorized. */
    id: "harbor-review",
    title: "Harbor House — Creative Review",
    type: "client",
    source: "fathom",
    clientId: "harbor",
    date: "Sep 3",
    duration: "38 min",
    host: "Jacqueline",
    channel: "#client-harbor-house",
    exceptions: true,
    decisions: ["Creative swap agreed in principle"],
    clientCommitments: [],
    wiaCommitments: ["Confirm swap once transcript is available"],
    risks: [
      "Transcript not returned by the recorder’s Fathom account",
      "Slack channel not authorized for Ops Hub",
    ],
    tasks: [
      {
        id: "h1",
        title: "Confirm creative swap scope",
        owner: "Jacqueline",
        due: "Tomorrow",
        ts: "—",
      },
      {
        id: "h2",
        title: "Update creative brief in ClickUp",
        owner: "Carmen",
        due: "Friday",
        ts: "—",
      },
      {
        id: "h3",
        title: "Send client confirmation",
        owner: "Danielle",
        due: "Friday",
        ts: "—",
      },
    ],
    moments: [],
    files: [
      ["Recording.mp4", "recording"],
      ["Summary.md", "summary"],
    ],
    fileDest: "No mapped folder for Harbor House meetings",
  },
];

/* ── The reviewer matrix, and the pack as separate outputs ────────
   F04. Two defects sat behind one "Approve pack" button.

   1. WHO MAY APPROVE WHAT was inconsistent across the Blueprint: CC-02 and
      the global governance line reserved AI-generated client email for
      Whitney, while ON-02, MK-03 and CC-04 said "Whitney or Gisselle". A
      whole-pack approval hid the difference entirely — the same click
      authorised three internal ClickUp tasks and one client-facing email.

   2. A PACK IS SEVERAL DISPATCHES and they do not succeed together. One
      approval that reports one outcome cannot show a failed Slack post, its
      retry, or the manual owner who picks it up.

   THE MATRIX BELOW IS THE ONE READING OF DISCOVERY, applied everywhere:
     · anything AI-generated that a CLIENT or MEMBER will read → Whitney
       approves (26 Aug @32:05 "I usually like to review stuff just in case";
       2 Sept @8:01 "we'll review any drafts before they go out")
     · internal artifacts — ClickUp tasks, Slack dispatch, Drive filing →
       Gisselle approves; they are her existing job
     · Gisselle's OWN short acknowledgements, written by her on threads she
       owns, are unchanged and need nobody (26 Aug @31:35–32:43). That
       exemption does not extend to generated drafts.

   Anything the client has not signed off on is marked `pending` rather than
   asserted — see AUTHORITY_META.confirmed. */

export type ReviewerAuthority =
  | "whitney"
  | "gisselle"
  | "gisselle_own_words"
  | "either";

export const AUTHORITY_META: Record<
  ReviewerAuthority,
  { label: string; who: string; tone: Tone; basis: string; confirmed: boolean }
> = {
  whitney: {
    label: "Whitney approves",
    who: "Whitney Hodges",
    tone: "red",
    basis: "AI-generated, client- or member-facing",
    confirmed: true,
  },
  gisselle: {
    label: "Gisselle approves",
    who: "Gisselle Jimenez",
    tone: "blue",
    basis: "Internal only — ClickUp, Slack, Drive",
    confirmed: true,
  },
  gisselle_own_words: {
    label: "Gisselle sends — no gate",
    who: "Gisselle Jimenez",
    tone: "slate",
    basis:
      "Her own short replies on threads she owns. Not generated drafts",
    confirmed: true,
  },
  either: {
    label: "Whitney or Gisselle — to confirm",
    who: "Either",
    tone: "amber",
    basis:
      "Proposed, not agreed",
    confirmed: false,
  },
};

/** The matrix as a table, rendered on Source Coverage and in the Blueprint. */
export const REVIEWER_MATRIX: {
  artifact: string;
  authority: ReviewerAuthority;
  sends: string;
  initiative: string;
}[] = [
  {
    artifact: "AI-drafted client reply",
    authority: "whitney",
    sends: "Whitney, from Gmail",
    initiative: "CC-02",
  },
  {
    artifact: "AI-drafted client recap after a meeting",
    authority: "whitney",
    sends: "Whitney, or Gisselle once the template is approved",
    initiative: "MK-03 / CC-04",
  },
  {
    artifact: "Onboarding welcome email",
    authority: "whitney",
    sends: "Gisselle, after the first is approved per offer",
    initiative: "ON-02",
  },
  {
    artifact: "Personal invoice follow-up",
    authority: "whitney",
    sends: "Gisselle from hello@, after Whitney sees it",
    initiative: "OP-03",
  },
  {
    artifact: "Member-portal recap or reminder post",
    authority: "whitney",
    sends: "Gisselle, once theme and copy are approved",
    initiative: "MP-02 / MP-03",
  },
  {
    artifact: "Internal Slack dispatch to the team",
    authority: "gisselle",
    sends: "Gisselle",
    initiative: "MK-01 / OP-01",
  },
  {
    artifact: "ClickUp task creation and assignment",
    authority: "gisselle",
    sends: "Gisselle",
    initiative: "MK-01 / ON-02",
  },
  {
    artifact: "Drive filing of recordings and assets",
    authority: "gisselle",
    sends: "Nobody — no message is produced",
    initiative: "MK-02 / ON-03",
  },
  {
    artifact: "Gisselle's own short acknowledgement",
    authority: "gisselle_own_words",
    sends: "Gisselle, as today",
    initiative: "—",
  },
  {
    artifact: "Content published to WIA's own channels",
    authority: "either",
    sends:
      "Not agreed. Client clearance is Whitney's per call",
    initiative: "MC-03 / MC-04",
  },
];

export type PackOutput = {
  id: string;
  kind: "clickup" | "slack" | "gmail" | "drive";
  source: SourceKey;
  label: string;
  destination: string;
  /** The exact artifact a reviewer approves, where a message exists. */
  body?: string;
  clientFacing: boolean;
  authority: ReviewerAuthority;
  /** The obligation this output serves, so releasing it moves the ledger. */
  obligationId?: string;
  /** Simulated first-attempt failure. Exactly one per pack, deliberately. */
  failsFirstAttempt?: boolean;
  failureReason?: string;
  /** Who picks it up if the automated path stays broken. */
  manualOwner?: string;
};

/* Written per meeting rather than generated, because the artifacts genuinely
   differ: a sales pack produces a proposal draft, an office-hours pack a
   community recap, an internal pack neither. */
const PACK_OUTPUTS: Record<string, PackOutput[]> = {
  "bloom-strategy": [
    {
      id: "o-tasks",
      kind: "clickup",
      source: "clickup",
      label: "3 ClickUp tasks",
      destination: "ELEVATE Clients / Bloom Manor / Client Management",
      body:
        "1. Complete landing-page handoff — Jacqueline — due tomorrow (24:18)\n2. Review keyword exclusions — Carmen — due Friday (31:05)\n3. Send client recap — Gisselle — due today (42:18)",
      clientFacing: false,
      authority: "gisselle",
    },
    {
      id: "o-drive",
      kind: "drive",
      source: "drive",
      label: "4 files to Drive",
      destination: "Drive / Clients / Bloom Manor / Meetings / 2026-09-02 Strategy",
      clientFacing: false,
      authority: "gisselle",
    },
    {
      /* THE ONE THAT FAILS. A renamed Slack channel is the most ordinary
         integration failure there is, and it is the one that leaves a task
         assigned and nobody told. */
      id: "o-slack",
      kind: "slack",
      source: "slack",
      label: "Slack recap to #client-bloom-manor",
      destination: "#client-bloom-manor",
      body:
        "*Bloom Manor — Monthly Strategy · Sep 2*\n\nDecisions: testimonial creative test approved · revised page needs client handoff · keyword exclusions before the next flight.\n\n• Jacqueline — landing-page handoff, due tomorrow\n• Carmen — keyword exclusions, due Friday\n• Gisselle — client recap, due today\n\nClient owes us: October gallery, Friday.",
      clientFacing: false,
      authority: "gisselle",
      failsFirstAttempt: true,
      failureReason:
        "channel_not_found — #client-bloom-manor was renamed. The tasks above were still created, so a retry must not create them twice.",
      manualOwner: "Gisselle",
    },
    {
      id: "o-recap",
      kind: "gmail",
      source: "gmail",
      label: "Client recap draft",
      destination: "Gmail drafts · sarah@bloommanor.com",
      body:
        "Hi Sarah,\n\nThank you for the time today. Here is where we landed:\n\n• The revised landing page comes to you this week — we will send the link the moment QA is signed off.\n• We are pulling the broad keywords before the next flight.\n• The testimonial creative test is approved and going into build.\n\nOne thing from your side: the October gallery, whenever it is ready — the new creative set is waiting on it.\n\nRecording and summary are in your folder.\n\nThank you!",
      clientFacing: true,
      authority: "whitney",
      obligationId: "ob-bloom-recap",
    },
  ],
  "monday-team": [
    {
      id: "o-tasks",
      kind: "clickup",
      source: "clickup",
      label: "ClickUp tasks",
      destination: "Internal / Team Ops",
      clientFacing: false,
      authority: "gisselle",
    },
    {
      id: "o-slack",
      kind: "slack",
      source: "slack",
      label: "Slack recap to #team-ops",
      destination: "#team-ops",
      clientFacing: false,
      authority: "gisselle",
    },
  ],
  "magnolia-sales": [
    {
      id: "o-tasks",
      kind: "clickup",
      source: "clickup",
      label: "ClickUp tasks",
      destination: "Sales pipeline",
      clientFacing: false,
      authority: "gisselle",
    },
    {
      id: "o-proposal",
      kind: "gmail",
      source: "gmail",
      label: "Elevate proposal draft",
      destination: "Gmail drafts · tessa@magnoliahouse.com",
      clientFacing: true,
      authority: "whitney",
      obligationId: "ob-magnolia-proposal",
    },
  ],
};

/** Outputs for a pack. Falls back to a task-and-filing pair so a meeting
    added later renders something honest rather than nothing. */
export function packOutputs(m: Meeting): PackOutput[] {
  return (
    PACK_OUTPUTS[m.id] ?? [
      {
        id: "o-tasks",
        kind: "clickup",
        source: "clickup",
        label: `${m.tasks.length} ClickUp tasks`,
        destination: m.channel,
        clientFacing: false,
        authority: "gisselle",
      },
    ]
  );
}

export type ExceptionDef = {
  key: string;
  system: SourceKey;
  code: string;
  message: string;
  recovery: string;
  buttons: [string, "primary" | "ghost"][];
};

export const PACK_EXCEPTIONS: ExceptionDef[] = [
  {
    key: "transcript",
    system: "fathom",
    code: "SOURCE_UNAVAILABLE",
    message: "Transcript unavailable",
    recovery:
      "The recorder’s Fathom account has not shared this meeting with the team. Fathom API keys are user-scoped, so an admin key does not unlock it.",
    buttons: [
      ["Retry demo", "primary"],
      ["Upload transcript", "ghost"],
    ],
  },
  {
    key: "slack",
    system: "slack",
    code: "CHANNEL_UNAUTHORIZED",
    message: "Private channel unavailable",
    recovery:
      "The hub is not authorized for #client-harbor-house. Choose an authorized channel or copy the dispatch and post it manually.",
    buttons: [
      ["Choose authorized channel", "primary"],
      ["Copy message", "ghost"],
    ],
  },
  {
    key: "drive",
    system: "drive",
    code: "FOLDER_UNMAPPED",
    message: "Client meeting folder not mapped",
    recovery:
      "The hub files into existing mapped client folders only — it never creates onboarding folders.",
    buttons: [
      ["Choose existing folder", "primary"],
      ["Open source coverage", "ghost"],
    ],
  },
  {
    key: "clickup",
    system: "clickup",
    code: "WRITE_PARTIAL",
    message: "2 tasks created · 1 task failed",
    recovery:
      "Assignee mapping missing for Danielle. Fix the mapping and retry the single failed write.",
    buttons: [
      ["Fix mapping", "primary"],
      ["Retry", "ghost"],
    ],
  },
];

/* ── Client Hub (client 360) ─────────────────────────────────────
   FIVE TABS, AND A RULE ABOUT WHERE INFERENCE HAPPENS.

   Every tab here is a read. Now, Timeline, Meetings, Money and Attendance
   are joins over structured source data; Commitments is a lookup of
   extraction that already ran once, when the meeting landed. Nothing on this
   screen calls a model at read time, and that is the point rather than an
   accident: read-time inference bills per glance, so its cost grows with
   adoption — the hub gets more expensive precisely as it gets more useful.
   Write-time inference bills per meeting and per inbound email, which is a
   number you can forecast from last month's calendar.

   The seven asks are the same rule applied to the panel that looks most like
   AI. Each one resolves to a count computed from this data plus a jump to
   the tab that holds the evidence — see ASK_ROUTES. They used to return
   authored prose, which was both a token cost and a staleness bug: an answer
   generated at 9am is wrong by 11am, and a cache cannot tell you which.

   ACCOUNT SHAPE DRIVES THE TAB SET. A prospect has no invoices and an
   Accelerator member has no 1:1 strategy calls, so a fixed five-tab bar
   would hand a third of the book empty screens. `clientTabs` returns the set
   that account can actually fill. */

export type ClientShape = "retainer" | "accelerator" | "prospect";

export function clientShape(c: Client): ClientShape {
  if (c.status === "prospect") return "prospect";
  return c.service.includes("Accelerator") ? "accelerator" : "retainer";
}

/* Money is dropped for prospects — nothing is billed yet. Attendance
   replaces Meetings for Accelerator members, because their sessions are the
   group Office Hours and the replay link lives on the attendance row. */
export function clientTabs(c: Client): [string, string][] {
  const shape = clientShape(c);
  /* Spine, Now and Brief are the three READINGS of the same record — the
     whole engagement, this week, and the handover. They are shape-invariant
     because every account has a history, a present and a successor. What
     varies by shape is only the LEDGERS underneath them. */
  const readings: [string, string][] = [
    ["spine", "Spine"],
    ["now", "Now"],
    ["brief", "Brief"],
  ];
  const ledgers: [string, string][] = [
    ["commitments", "Commitments"],
    ["timeline", "Timeline"],
  ];
  if (shape === "prospect")
    return [...readings, ...ledgers, ["meetings", "Meetings"]];
  if (shape === "accelerator")
    return [...readings, ...ledgers, ["attendance", "Attendance"], ["money", "Money"]];
  return [...readings, ...ledgers, ["meetings", "Meetings"], ["money", "Money"]];
}

/* ── Commitments ──────────────────────────────────────────────────
   The promise ledger, and the reason this screen survives turnover. Split by
   side because "we owe them" and "they owe us" drive opposite actions: one
   is a nudge at your own team, the other is a follow-up at the client.

   `ts` is the transcript timestamp where it was said, so a commitment can be
   heard rather than taken on trust. Harbor House rows carry "—" on purpose:
   the recorder's Fathom account never returned that transcript, so those
   commitments came from the summary alone and cannot be cited to a second.
   An extraction that hid that distinction would be the more dangerous one.

   `ack` uses the same four paths Ops Watch states out loud (ACK_PATHS), so
   "acknowledged" means one auditable thing across the hub. */

export type CommitmentSide = "wia" | "client";
export type CommitmentState = "done" | "in_progress" | "open" | "overdue" | "blocked";
export type AckPath = "reacted" | "replied" | "status_moved" | "manual" | "none" | "na";

export type Commitment = {
  id: string;
  clientId: string;
  side: CommitmentSide;
  text: string;
  owner: string;
  due: string;
  state: CommitmentState;
  madeOn: string;
  meetingId: string;
  /* Transcript timestamp, or "—" when no transcript was returned. */
  ts: string;
  clickup: string;
  ack: AckPath;
  ackDetail: string;
};

export const COMMITMENT_STATE_META: Record<
  CommitmentState,
  { label: string; tone: Tone }
> = {
  done: { label: "Delivered", tone: "green" },
  in_progress: { label: "In progress", tone: "blue" },
  open: { label: "Open", tone: "neutral" },
  overdue: { label: "Overdue", tone: "red" },
  blocked: { label: "Blocked", tone: "amber" },
};

export const ACK_META: Record<AckPath, { label: string; tone: Tone }> = {
  reacted: { label: "Acknowledged · reaction", tone: "green" },
  replied: { label: "Acknowledged · reply", tone: "green" },
  status_moved: { label: "Acknowledged · status moved", tone: "green" },
  manual: { label: "Acknowledged · by hand", tone: "slate" },
  none: { label: "Not acknowledged", tone: "amber" },
  na: { label: "Client-side", tone: "outline" },
};

export const COMMITMENTS: Commitment[] = [
  /* Bloom Manor — Sep 2 strategy call. The one fully-sourced account in the
     demo corpus: Zoom returned the transcript, so every row cites a second. */
  {
    id: "cm-bloom-1",
    clientId: "bloom",
    side: "wia",
    text: "Deliver the revised landing page",
    owner: "Jacqueline",
    due: "Tomorrow · Sep 5",
    state: "in_progress",
    madeOn: "Sep 2",
    meetingId: "bloom-strategy",
    ts: "24:18",
    clickup: "Landing Page QA · In Progress",
    ack: "status_moved",
    ackDetail: "Moved out of Open yesterday; final QA confirmed in Slack today",
  },
  {
    id: "cm-bloom-2",
    clientId: "bloom",
    side: "wia",
    text: "Review keyword exclusions before the next flight",
    owner: "Carmen",
    due: "Today · Sep 4",
    state: "open",
    madeOn: "Sep 2",
    meetingId: "bloom-strategy",
    ts: "31:05",
    clickup: "Keyword exclusion review · Open",
    ack: "replied",
    ackDetail: "Replied in the action thread on Sep 2",
  },
  {
    id: "cm-bloom-3",
    clientId: "bloom",
    side: "wia",
    text: "Update the testimonial creative",
    owner: "Jacqueline",
    due: "Sep 3",
    state: "overdue",
    madeOn: "Sep 2",
    meetingId: "bloom-strategy",
    ts: "31:05",
    clickup: "Testimonial creative · Open · due yesterday",
    ack: "none",
    ackDetail: "Message delivered to #client-bloom-manor, no reaction after 23 hours",
  },
  {
    id: "cm-bloom-4",
    clientId: "bloom",
    side: "wia",
    text: "Send the call recap the same day",
    owner: "Gisselle",
    due: "Sep 2",
    state: "done",
    madeOn: "Sep 2",
    meetingId: "bloom-strategy",
    ts: "42:18",
    clickup: "Send client recap · Complete",
    ack: "replied",
    ackDetail: "Sent Sep 2 after Whitney approved the draft",
  },
  {
    id: "cm-bloom-5",
    clientId: "bloom",
    side: "client",
    text: "Send the October gallery assets",
    owner: "Sarah Mitchell",
    due: "Friday · Sep 5",
    state: "open",
    madeOn: "Sep 2",
    meetingId: "bloom-strategy",
    ts: "47:02",
    clickup: "Blocks: testimonial creative set",
    ack: "na",
    ackDetail: "Requested 5 days ago · follow-up drafted, not sent",
  },

  /* Rosewood Venue — Aug 25 check-in, recorded on Fathom. The SLA row is the
     one that matters: a promise nobody made out loud, created by the 24–48
     business-hour reply rule rather than by the meeting. */
  {
    id: "cm-rose-1",
    clientId: "rosewood",
    side: "wia",
    text: "Send the check-in recap",
    owner: "Gisselle",
    due: "Aug 25",
    state: "done",
    madeOn: "Aug 25",
    meetingId: "rosewood-checkin",
    ts: "38:02",
    clickup: "Send check-in recap · Complete",
    ack: "replied",
    ackDetail: "Sent same day; client acknowledged Aug 26",
  },
  {
    id: "cm-rose-2",
    clientId: "rosewood",
    side: "wia",
    text: "Reply to Dana’s budget question",
    owner: "Carmen",
    due: "Sep 3",
    state: "overdue",
    madeOn: "Sep 3",
    meetingId: "",
    ts: "—",
    clickup: "No task created",
    ack: "none",
    ackDetail: "No reply after 29 business hours · expectation is 24–48",
  },
  {
    id: "cm-rose-3",
    clientId: "rosewood",
    side: "wia",
    text: "Hold the creative build until the gallery assets arrive",
    owner: "Carmen",
    due: "On assets",
    state: "blocked",
    madeOn: "Aug 25",
    meetingId: "rosewood-checkin",
    ts: "40:15",
    clickup: "Creative build · Blocked",
    ack: "status_moved",
    ackDetail: "Moved to Blocked Aug 26 with the reason recorded",
  },
  {
    id: "cm-rose-4",
    clientId: "rosewood",
    side: "client",
    text: "Send the requested gallery assets",
    owner: "Dana Whitfield",
    due: "Aug 26",
    state: "overdue",
    madeOn: "Aug 25",
    meetingId: "rosewood-checkin",
    ts: "40:15",
    clickup: "Blocks: creative build",
    ack: "na",
    ackDetail: "Requested twice · outstanding 12 days",
  },

  /* Everly Estate — Google Accelerator. No 1:1 calls, so the ledger is
     programme obligations on both sides, which is what an Accelerator
     relationship actually consists of. */
  {
    id: "cm-everly-1",
    clientId: "everly",
    side: "wia",
    text: "Publish the Aug 20 session replay to the member portal",
    owner: "Gisselle",
    due: "Aug 21",
    state: "done",
    madeOn: "Aug 20",
    meetingId: "",
    ts: "—",
    clickup: "Publish replay · Complete",
    ack: "status_moved",
    ackDetail: "Filed to Drive and linked in HighLevel Aug 21",
  },
  {
    id: "cm-everly-2",
    clientId: "everly",
    side: "wia",
    text: "Send Nina the Office Hours replay link she asked for",
    owner: "Gisselle",
    due: "Today · Sep 4",
    state: "in_progress",
    madeOn: "Sep 4",
    meetingId: "",
    ts: "—",
    clickup: "No task — handled in Inbox",
    ack: "none",
    ackDetail: "Draft ready in the Gisselle queue, awaiting send",
  },
  {
    id: "cm-everly-3",
    clientId: "everly",
    side: "client",
    text: "Submit the Google Ads account for the next audit round",
    owner: "Nina Cole",
    due: "Aug 28",
    state: "overdue",
    madeOn: "Aug 20",
    meetingId: "",
    ts: "—",
    clickup: "Blocks: September audit round",
    ack: "na",
    ackDetail: "Two portal reminders delivered · no submission",
  },

  /* Willow & Pine — Meta Accelerator, four sessions missed. The programme
     obligation is intact on WIA's side and unmet on theirs, which is the
     only honest way to frame a re-engagement case. */
  {
    id: "cm-willow-1",
    clientId: "willow",
    side: "wia",
    text: "Send a personal re-engagement email rather than another reminder",
    owner: "Whitney",
    due: "Today · Sep 4",
    state: "open",
    madeOn: "Sep 4",
    meetingId: "",
    ts: "—",
    clickup: "Re-engage Willow & Pine · Open",
    ack: "none",
    ackDetail: "Raised by the missed-attendance rule at the 4th consecutive session",
  },
  {
    id: "cm-willow-2",
    clientId: "willow",
    side: "client",
    text: "Attend a Meta Office Hours session",
    owner: "Maya Stone",
    due: "Sep 10 session",
    state: "overdue",
    madeOn: "Aug 6",
    meetingId: "",
    ts: "—",
    clickup: "Attendance tracked in HighLevel",
    ack: "na",
    ackDetail: "Last confirmed attendance Aug 6 · Sep 3 match unresolved",
  },

  /* Magnolia House — prospect. A discovery call generates commitments like
     any other call, and this is where deals leak: the proposal promised on
     Sep 3 is due today and nobody has acknowledged it. */
  {
    id: "cm-mag-1",
    clientId: "magnolia",
    side: "wia",
    text: "Send the Elevate proposal",
    owner: "Whitney",
    due: "Today · Sep 4",
    state: "open",
    madeOn: "Sep 3",
    meetingId: "magnolia-sales",
    ts: "19:44",
    clickup: "Send Elevate proposal · Open · due today",
    ack: "none",
    ackDetail: "Draft prepared in the Whitney queue, not yet approved",
  },
  {
    id: "cm-mag-2",
    clientId: "magnolia",
    side: "wia",
    text: "Share the venue-tour benchmark example",
    owner: "Whitney",
    due: "With the proposal",
    state: "open",
    madeOn: "Sep 3",
    meetingId: "magnolia-sales",
    ts: "22:30",
    clickup: "No task created",
    ack: "none",
    ackDetail: "Mentioned once on the call; no owner confirmed it",
  },
  {
    id: "cm-mag-3",
    clientId: "magnolia",
    side: "wia",
    text: "Log the prospect in the HighLevel pipeline",
    owner: "Gisselle",
    due: "Sep 3",
    state: "done",
    madeOn: "Sep 3",
    meetingId: "magnolia-sales",
    ts: "30:10",
    clickup: "Log prospect · Complete",
    ack: "status_moved",
    ackDetail: "Contact created from the referral record Aug 24, stage updated Sep 3",
  },
  {
    id: "cm-mag-4",
    clientId: "magnolia",
    side: "client",
    text: "Confirm the internal budget window",
    owner: "Tessa Ruiz",
    due: "Thursday · Sep 10",
    state: "open",
    madeOn: "Sep 3",
    meetingId: "magnolia-sales",
    ts: "30:10",
    clickup: "Gates: proposal review",
    ack: "na",
    ackDetail: "Agreed on the call to review Thursday",
  },

  /* Harbor House — the account with no transcript. Every ts is "—" because
     Fathom never returned the recording to the team, so these came out of the
     summary alone. Danielle's row is blocked by the same missing ClickUp
     assignee mapping that broke the execution pack. */
  {
    id: "cm-harbor-1",
    clientId: "harbor",
    side: "wia",
    text: "Confirm the creative swap scope",
    owner: "Jacqueline",
    due: "Tomorrow · Sep 5",
    state: "open",
    madeOn: "Sep 3",
    meetingId: "harbor-review",
    ts: "—",
    clickup: "Confirm swap scope · Open",
    ack: "none",
    ackDetail: "Approval thread at 26 business hours · channel unauthorized",
  },
  {
    id: "cm-harbor-2",
    clientId: "harbor",
    side: "wia",
    text: "Update the creative brief in ClickUp",
    owner: "Carmen",
    due: "Friday · Sep 5",
    state: "open",
    madeOn: "Sep 3",
    meetingId: "harbor-review",
    ts: "—",
    clickup: "Update creative brief · Open",
    ack: "manual",
    ackDetail: "Marked acknowledged by Gisselle after a verbal confirmation",
  },
  {
    id: "cm-harbor-3",
    clientId: "harbor",
    side: "wia",
    text: "Send the client confirmation",
    owner: "Danielle",
    due: "Friday · Sep 5",
    state: "blocked",
    madeOn: "Sep 3",
    meetingId: "harbor-review",
    ts: "—",
    clickup: "Write failed · no assignee mapping for Danielle",
    ack: "none",
    ackDetail: "The task was never created, so no acknowledgement is possible",
  },
  {
    id: "cm-harbor-4",
    clientId: "harbor",
    side: "wia",
    text: "Answer the reporting cadence question",
    owner: "Gisselle",
    due: "Today · Sep 4",
    state: "in_progress",
    madeOn: "Sep 3",
    meetingId: "",
    ts: "—",
    clickup: "No task — handled in Inbox",
    ack: "replied",
    ackDetail: "Draft ready; cadence confirmed against ClickUp before drafting",
  },
  {
    id: "cm-harbor-5",
    clientId: "harbor",
    side: "client",
    text: "Approve the creative swap",
    owner: "Elena Park",
    due: "Friday · Sep 5",
    state: "open",
    madeOn: "Sep 3",
    meetingId: "harbor-review",
    ts: "—",
    clickup: "Gates: creative build",
    ack: "na",
    ackDetail: "Agreed in principle on the call, not confirmed in writing",
  },
];

/* ── Money ────────────────────────────────────────────────────────
   HighLevel invoice events, which are structured and therefore free to read
   however often anyone looks. The reminder trail matters as much as the
   balance: "overdue" reads very differently once you know two automatic
   reminders have already gone out under WIA's name.

   `INVOICES` — the Ops Watch finance queue — is DERIVED from this ledger
   further down rather than listed a second time. Two hand-kept lists of the
   same overdue invoices is a drift bug waiting for the first edit. */

export type InvoiceState = "paid" | "open" | "overdue";

export type InvoiceReminder = {
  when: string;
  kind: "auto" | "personal";
  detail: string;
};

export type InvoiceRow = {
  id: string;
  clientId: string;
  amount: number;
  issued: string;
  due: string;
  state: InvoiceState;
  paidOn: string;
  /* Days past due — overdue rows only. */
  overdueDays: number;
  /* Days from issue to payment — paid rows only. This is the number that
     says whether an account is actually a slow payer, which a balance
     cannot. */
  daysToPay: number;
  reminders: InvoiceReminder[];
  payUrl: string;
};

export const CLIENT_INVOICES: Record<string, InvoiceRow[]> = {
  bloom: [
    {
      id: "INV-207",
      clientId: "bloom",
      amount: 2400,
      issued: "Sep 1",
      due: "Sep 15",
      state: "open",
      paidOn: "",
      overdueDays: 0,
      daysToPay: 0,
      reminders: [],
      payUrl: "app.gohighlevel.com/invoice/INV-207",
    },
    {
      id: "INV-201",
      clientId: "bloom",
      amount: 2400,
      issued: "Aug 12",
      due: "Aug 26",
      state: "paid",
      paidOn: "Aug 26",
      overdueDays: 0,
      daysToPay: 14,
      reminders: [
        { when: "Aug 24", kind: "auto", detail: "Due-soon reminder delivered" },
      ],
      payUrl: "app.gohighlevel.com/invoice/INV-201",
    },
    {
      id: "INV-195",
      clientId: "bloom",
      amount: 2400,
      issued: "Jul 12",
      due: "Jul 26",
      state: "paid",
      paidOn: "Jul 24",
      overdueDays: 0,
      daysToPay: 12,
      reminders: [],
      payUrl: "app.gohighlevel.com/invoice/INV-195",
    },
  ],
  rosewood: [
    {
      id: "INV-204",
      clientId: "rosewood",
      amount: 1850,
      issued: "Aug 16",
      due: "Aug 30",
      state: "overdue",
      paidOn: "",
      overdueDays: 5,
      daysToPay: 0,
      reminders: [
        { when: "Aug 28", kind: "auto", detail: "Due-soon reminder delivered" },
        { when: "Aug 31", kind: "auto", detail: "Overdue reminder 1 delivered" },
        { when: "Sep 3", kind: "auto", detail: "Overdue reminder 2 delivered" },
        {
          when: "Today",
          kind: "personal",
          detail: "Personal Gmail follow-up drafted for Gisselle — not sent",
        },
      ],
      payUrl: "app.gohighlevel.com/invoice/INV-204",
    },
    {
      id: "INV-199",
      clientId: "rosewood",
      amount: 1850,
      issued: "Jul 16",
      due: "Jul 30",
      state: "paid",
      paidOn: "Aug 2",
      overdueDays: 0,
      daysToPay: 17,
      reminders: [
        { when: "Jul 31", kind: "auto", detail: "Overdue reminder 1 delivered" },
      ],
      payUrl: "app.gohighlevel.com/invoice/INV-199",
    },
    {
      id: "INV-190",
      clientId: "rosewood",
      amount: 1850,
      issued: "Jun 16",
      due: "Jun 30",
      state: "paid",
      paidOn: "Jul 4",
      overdueDays: 0,
      daysToPay: 18,
      reminders: [
        { when: "Jul 1", kind: "auto", detail: "Overdue reminder 1 delivered" },
      ],
      payUrl: "app.gohighlevel.com/invoice/INV-190",
    },
  ],
  everly: [
    {
      id: "INV-206",
      clientId: "everly",
      amount: 497,
      issued: "Sep 1",
      due: "Sep 8",
      state: "open",
      paidOn: "",
      overdueDays: 0,
      daysToPay: 0,
      reminders: [],
      payUrl: "app.gohighlevel.com/invoice/INV-206",
    },
    {
      id: "INV-200",
      clientId: "everly",
      amount: 497,
      issued: "Aug 1",
      due: "Aug 8",
      state: "paid",
      paidOn: "Aug 4",
      overdueDays: 0,
      daysToPay: 3,
      reminders: [],
      payUrl: "app.gohighlevel.com/invoice/INV-200",
    },
  ],
  willow: [
    {
      id: "INV-205",
      clientId: "willow",
      amount: 497,
      issued: "Sep 1",
      due: "Sep 8",
      state: "open",
      paidOn: "",
      overdueDays: 0,
      daysToPay: 0,
      reminders: [],
      payUrl: "app.gohighlevel.com/invoice/INV-205",
    },
    {
      id: "INV-197",
      clientId: "willow",
      amount: 497,
      issued: "Aug 1",
      due: "Aug 8",
      state: "paid",
      paidOn: "Aug 3",
      overdueDays: 0,
      daysToPay: 2,
      reminders: [],
      payUrl: "app.gohighlevel.com/invoice/INV-197",
    },
  ],
  harbor: [
    {
      id: "INV-198",
      clientId: "harbor",
      amount: 1750,
      issued: "Aug 13",
      due: "Aug 27",
      state: "overdue",
      paidOn: "",
      overdueDays: 8,
      daysToPay: 0,
      reminders: [
        { when: "Aug 25", kind: "auto", detail: "Due-soon reminder delivered" },
        { when: "Aug 28", kind: "auto", detail: "Overdue reminder 1 delivered" },
        { when: "Sep 1", kind: "auto", detail: "Overdue reminder 2 delivered" },
        { when: "Today", kind: "auto", detail: "Overdue reminder 3 delivered" },
      ],
      payUrl: "app.gohighlevel.com/invoice/INV-198",
    },
    {
      id: "INV-191",
      clientId: "harbor",
      amount: 1750,
      issued: "Jul 15",
      due: "Jul 29",
      state: "paid",
      paidOn: "Jul 29",
      overdueDays: 0,
      daysToPay: 14,
      reminders: [],
      payUrl: "app.gohighlevel.com/invoice/INV-191",
    },
  ],
  /* Magnolia House is a prospect. No ledger, and `clientTabs` hides Money
     rather than showing a zeroed one. */
  magnolia: [],
};

export const INVOICE_STATE_META: Record<InvoiceState, { label: string; tone: Tone }> = {
  paid: { label: "Paid", tone: "green" },
  open: { label: "Open", tone: "blue" },
  overdue: { label: "Overdue", tone: "red" },
};

export const money = (n: number) => `$${n.toLocaleString("en-US")}`;

/* ── Attendance (Accelerator members) ─────────────────────────────
   Office Hours attendance, matched from the Zoom participant report against
   the HighLevel member record.

   THE UNMATCHED ROW IS THE IMPORTANT ONE. A participant called "Maya" joined
   the Sep 3 Meta session at 91% similarity to Maya Stone. The matcher will
   not assert it, so Willow & Pine's fourth consecutive miss is provisional
   and the screen says so — a re-engagement email sent to someone who did
   attend costs more than a day's delay. */

export type AttendanceState = "attended" | "missed" | "unmatched";

export type AttendanceRow = {
  clientId: string;
  session: string;
  date: string;
  state: AttendanceState;
  detail: string;
  replay: string;
};

export const ATTENDANCE_STATE_META: Record<
  AttendanceState,
  { label: string; tone: Tone }
> = {
  attended: { label: "Attended", tone: "green" },
  missed: { label: "Missed", tone: "amber" },
  unmatched: { label: "Needs match", tone: "red" },
};

export const CLIENT_ATTENDANCE: Record<string, AttendanceRow[]> = {
  everly: [
    {
      clientId: "everly",
      session: "Google Ads Office Hours",
      date: "Sep 2",
      state: "missed",
      detail: "2nd consecutive miss · reminder delivered 1 hour before",
      replay: "Accelerators / Google Office Hours / 2026-09-02",
    },
    {
      clientId: "everly",
      session: "Google Ads Office Hours",
      date: "Aug 27",
      state: "missed",
      detail: "1st miss · reminder delivered",
      replay: "Accelerators / Google Office Hours / 2026-08-27",
    },
    {
      clientId: "everly",
      session: "Google Ads Office Hours",
      date: "Aug 20",
      state: "attended",
      detail: "Matched automatically from the Zoom participant report",
      replay: "Accelerators / Google Office Hours / 2026-08-20",
    },
    {
      clientId: "everly",
      session: "Google Ads Office Hours",
      date: "Aug 13",
      state: "attended",
      detail: "Matched automatically · 52 min of 61",
      replay: "Accelerators / Google Office Hours / 2026-08-13",
    },
    {
      clientId: "everly",
      session: "Google Ads Office Hours",
      date: "Aug 6",
      state: "attended",
      detail: "Matched automatically · full session",
      replay: "Accelerators / Google Office Hours / 2026-08-06",
    },
  ],
  willow: [
    {
      clientId: "willow",
      session: "Meta Ads Office Hours",
      date: "Sep 3",
      state: "unmatched",
      detail:
        "Participant “Maya” joined for 47 min · 91% similarity to Maya Stone · not asserted",
      replay: "Accelerators / Meta Office Hours / 2026-09-03",
    },
    {
      clientId: "willow",
      session: "Meta Ads Office Hours",
      date: "Aug 27",
      state: "missed",
      detail: "3rd consecutive miss · reminder delivered",
      replay: "Accelerators / Meta Office Hours / 2026-08-27",
    },
    {
      clientId: "willow",
      session: "Meta Ads Office Hours",
      date: "Aug 20",
      state: "missed",
      detail: "2nd consecutive miss · reminder delivered",
      replay: "Accelerators / Meta Office Hours / 2026-08-20",
    },
    {
      clientId: "willow",
      session: "Meta Ads Office Hours",
      date: "Aug 13",
      state: "missed",
      detail: "1st miss · reminder delivered",
      replay: "Accelerators / Meta Office Hours / 2026-08-13",
    },
    {
      clientId: "willow",
      session: "Meta Ads Office Hours",
      date: "Aug 6",
      state: "attended",
      detail: "Last confirmed attendance · matched automatically",
      replay: "Accelerators / Meta Office Hours / 2026-08-06",
    },
  ],
};

/* ── Timeline ─────────────────────────────────────────────────────
   One merged feed per account, filtered by source rather than split across
   three tabs that rendered identical rows. Every row opens the evidence
   drawer, because a timeline you cannot drill into is a rumour. */

export type TimelineRow = {
  when: string;
  s: SourceKey;
  text: string;
  meta: string;
  status: string;
  tone: Tone;
};

/* Rows that count as "since the last call" for the change ask. Kept as data
   so the ask and any future recency filter cannot disagree. */
export const RECENT_WHEN = ["Today", "Yesterday", "1d ago", "2d ago"];

export const CLIENT_TIMELINES: Record<string, TimelineRow[]> = {
  bloom: [
    {
      when: "Today",
      s: "gmail",
      text: "Client requested landing-page update",
      meta: "Sarah Mitchell · thread open",
      status: "Reply due",
      tone: "amber",
    },
    {
      when: "Today",
      s: "slack",
      text: "Jacqueline confirmed final QA",
      meta: "#client-bloom-manor",
      status: "Context",
      tone: "outline",
    },
    {
      when: "Today",
      s: "clickup",
      text: "Testimonial creative passed its due date",
      meta: "Owner Jacqueline · no acknowledgement in 23h",
      status: "Overdue",
      tone: "red",
    },
    {
      when: "Yesterday",
      s: "clickup",
      text: "Landing Page QA moved to In Progress",
      meta: "Owner Jacqueline · due tomorrow",
      status: "In progress",
      tone: "blue",
    },
    {
      when: "Sep 2",
      s: "gmail",
      text: "Strategy call recap sent",
      meta: "Approved by Whitney before sending",
      status: "Sent",
      tone: "green",
    },
    {
      when: "Sep 2",
      s: "clickup",
      text: "3 tasks created from the strategy call",
      meta: "Jacqueline · Carmen · Gisselle",
      status: "Created",
      tone: "blue",
    },
    {
      when: "Sep 2",
      s: "slack",
      text: "Action dispatch posted to the client channel",
      meta: "#client-bloom-manor · 2 of 3 acknowledged",
      status: "Dispatched",
      tone: "green",
    },
    {
      when: "Sep 2",
      s: "zoom",
      text: "Monthly Strategy Call",
      meta: "58 min · 4 decisions · 3 actions",
      status: "Processed",
      tone: "green",
    },
    {
      when: "Sep 2",
      s: "drive",
      text: "Meeting transcript filed",
      meta: "Clients / Bloom Manor / Meetings / 2026-09-02",
      status: "Filed",
      tone: "green",
    },
    {
      when: "Sep 1",
      s: "highlevel",
      text: "Invoice INV-207 issued",
      meta: "$2,400 · due Sep 15",
      status: "Open",
      tone: "blue",
    },
    {
      when: "Aug 26",
      s: "highlevel",
      text: "Invoice INV-201 paid",
      meta: "$2,400 · on time",
      status: "Paid",
      tone: "green",
    },
  ],
  rosewood: [
    {
      when: "Today",
      s: "highlevel",
      text: "INV-204 flagged overdue",
      meta: "$1,850 · 5 days past due · standard reminder sent",
      status: "Needs review",
      tone: "amber",
    },
    {
      when: "Today",
      s: "gmail",
      text: "Budget-shift question awaiting Whitney",
      meta: "Draft prepared · approval required before any budget language",
      status: "Draft ready",
      tone: "blue",
    },
    {
      when: "2d ago",
      s: "gmail",
      text: "Client asked a question — no reply detected",
      meta: "Owner Carmen · 29 business hours",
      status: "SLA breach",
      tone: "red",
    },
    {
      when: "2d ago",
      s: "slack",
      text: "Nudge prepared for Carmen",
      meta: "#client-rosewood · not yet posted",
      status: "Ready",
      tone: "blue",
    },
    {
      when: "Aug 26",
      s: "clickup",
      text: "Creative build moved to Blocked",
      meta: "Reason recorded: waiting on the client gallery",
      status: "Blocked",
      tone: "amber",
    },
    {
      when: "Aug 25",
      s: "fathom",
      text: "Monthly Check-in",
      meta: "46 min · recap sent same day",
      status: "Processed",
      tone: "green",
    },
    {
      when: "Aug 25",
      s: "drive",
      text: "Check-in recording + transcript filed",
      meta: "Clients / Rosewood Venue / Meetings",
      status: "Filed",
      tone: "green",
    },
    {
      when: "Aug 23",
      s: "gmail",
      text: "Gallery assets requested again",
      meta: "Waiting 12 days",
      status: "Waiting",
      tone: "amber",
    },
    {
      when: "Aug 2",
      s: "highlevel",
      text: "Invoice INV-199 paid",
      meta: "$1,850 · 3 days late",
      status: "Paid",
      tone: "green",
    },
  ],
  everly: [
    {
      when: "Today",
      s: "gmail",
      text: "Nina asked for the Office Hours replay link",
      meta: "Draft ready · link pulled from the Drive session folder",
      status: "Draft ready",
      tone: "blue",
    },
    {
      when: "2d ago",
      s: "highlevel",
      text: "Missed Google Office Hours (2nd consecutive)",
      meta: "Attendance from the Zoom participant report",
      status: "At risk",
      tone: "amber",
    },
    {
      when: "2d ago",
      s: "zoom",
      text: "Participant report processed — Nina Cole absent",
      meta: "18 of 24 members matched automatically",
      status: "Processed",
      tone: "green",
    },
    {
      when: "Aug 28",
      s: "clickup",
      text: "Ads-account submission passed its due date",
      meta: "Client-side · blocks the September audit round",
      status: "Overdue",
      tone: "red",
    },
    {
      when: "Aug 27",
      s: "highlevel",
      text: "Missed Google Office Hours (1st)",
      meta: "Reminder delivered 1 hour before",
      status: "Context",
      tone: "outline",
    },
    {
      when: "Aug 21",
      s: "drive",
      text: "Aug 20 session replay filed and linked",
      meta: "Accelerators / Google Office Hours / 2026-08-20",
      status: "Filed",
      tone: "green",
    },
    {
      when: "Aug 20",
      s: "zoom",
      text: "Attended Google Office Hours",
      meta: "Matched automatically",
      status: "Attended",
      tone: "green",
    },
    {
      when: "Aug 19",
      s: "highlevel",
      text: "Community reminder delivered",
      meta: "Recurring post · 1 hour before",
      status: "Sent",
      tone: "green",
    },
    {
      when: "Aug 4",
      s: "highlevel",
      text: "Membership invoice INV-200 paid",
      meta: "$497 · 3 days to pay",
      status: "Paid",
      tone: "green",
    },
  ],
  willow: [
    {
      when: "Today",
      s: "highlevel",
      text: "Missed Meta Office Hours (4th consecutive)",
      meta: "Personal email recommended over another reminder",
      status: "Re-engage",
      tone: "red",
    },
    {
      when: "Today",
      s: "clickup",
      text: "Re-engagement task created for Whitney",
      meta: "Raised by the missed-attendance rule",
      status: "Open",
      tone: "blue",
    },
    {
      when: "Sep 3",
      s: "zoom",
      text: "Participant “Maya” could not be matched automatically",
      meta: "91% suggested match · needs confirmation",
      status: "Needs match",
      tone: "amber",
    },
    {
      when: "Aug 27",
      s: "highlevel",
      text: "Missed Meta Office Hours (3rd consecutive)",
      meta: "Reminder delivered",
      status: "Context",
      tone: "outline",
    },
    {
      when: "Aug 20",
      s: "highlevel",
      text: "Missed Meta Office Hours (2nd consecutive)",
      meta: "Reminder delivered",
      status: "Context",
      tone: "outline",
    },
    {
      when: "Aug 6",
      s: "zoom",
      text: "Attended Meta Office Hours",
      meta: "Last confirmed attendance",
      status: "Attended",
      tone: "green",
    },
    {
      when: "Aug 3",
      s: "highlevel",
      text: "Membership invoice INV-197 paid",
      meta: "$497 · 2 days to pay",
      status: "Paid",
      tone: "green",
    },
  ],
  magnolia: [
    {
      when: "Today",
      s: "clickup",
      text: "Elevate proposal due today",
      meta: "Owner Whitney · promised on the Sep 3 call",
      status: "Open",
      tone: "blue",
    },
    {
      when: "Yesterday",
      s: "zoom",
      text: "Discovery call — strong fit for Elevate",
      meta: "34 min · next step: send proposal",
      status: "Processed",
      tone: "green",
    },
    {
      when: "Yesterday",
      s: "gmail",
      text: "Proposal follow-up draft prepared",
      meta: "Awaiting Whitney approval",
      status: "Draft ready",
      tone: "blue",
    },
    {
      when: "Yesterday",
      s: "drive",
      text: "Discovery recording + summary filed",
      meta: "Sales / Magnolia House / 2026-09-03 Discovery",
      status: "Filed",
      tone: "green",
    },
    {
      when: "Yesterday",
      s: "highlevel",
      text: "Pipeline stage moved to Proposal",
      meta: "Logged by Gisselle from the call outcome",
      status: "Updated",
      tone: "green",
    },
    {
      when: "Aug 24",
      s: "highlevel",
      text: "Lead created from referral",
      meta: "Contact: Tessa Ruiz",
      status: "Context",
      tone: "outline",
    },
  ],
  harbor: [
    {
      when: "Today",
      s: "highlevel",
      text: "INV-198 overdue 8 days",
      meta: "$1,750 · 3 automatic reminders sent · needs review",
      status: "Needs review",
      tone: "amber",
    },
    {
      when: "1d ago",
      s: "gmail",
      text: "Reporting cadence question",
      meta: "Draft prepared for Whitney",
      status: "Draft ready",
      tone: "blue",
    },
    {
      when: "2d ago",
      s: "gmail",
      text: "Creative swap approval waiting on Jacqueline",
      meta: "26 business hours",
      status: "At risk",
      tone: "amber",
    },
    {
      when: "Sep 3",
      s: "fathom",
      text: "Creative Review — transcript not returned",
      meta: "The recorder’s Fathom account never shared the meeting",
      status: "Blocked",
      tone: "red",
    },
    {
      when: "Sep 3",
      s: "clickup",
      text: "2 tasks created · 1 write failed",
      meta: "No assignee mapping for Danielle",
      status: "Partial",
      tone: "amber",
    },
    {
      when: "Sep 3",
      s: "slack",
      text: "Dispatch could not post",
      meta: "#client-harbor-house is not authorized for Ops Hub",
      status: "Blocked",
      tone: "red",
    },
    {
      when: "Sep 3",
      s: "drive",
      text: "Filing skipped — no mapped folder",
      meta: "Harbor House has no meetings folder mapped",
      status: "Unmapped",
      tone: "amber",
    },
    {
      when: "Jul 29",
      s: "highlevel",
      text: "Invoice INV-191 paid",
      meta: "$1,750 · on time",
      status: "Paid",
      tone: "green",
    },
  ],
};

/* ── The asks, as routes rather than generations ──────────────────
   Same seven questions, same source attribution. What changed is what a
   click does: it computes a line off the data above and jumps to the tab
   holding the evidence, instead of spending tokens to describe it.

   `answer` is a pure function of loaded state, so it cannot go stale and
   cannot invent — the two failure modes of the version it replaces. */

export type AskContext = {
  client: Client;
  commitments: Commitment[];
  timeline: TimelineRow[];
  invoices: InvoiceRow[];
  meetings: Meeting[];
};

export type AskRoute = {
  q: string;
  tab: string;
  patch?: Record<string, unknown>;
  sources: string[];
  answer: (ctx: AskContext) => string;
};

const plural = (n: number, one: string, many = `${one}s`) =>
  `${n} ${n === 1 ? one : many}`;

export const ASK_ROUTES: AskRoute[] = [
  {
    q: "What did we promise them on the last call?",
    tab: "commitments",
    patch: { commitSide: "wia", commitState: "all" },
    sources: ["Zoom / Fathom · transcript", "ClickUp · linked tasks", "Gmail · recap"],
    answer: ({ commitments, meetings }) => {
      const wia = commitments.filter((c) => c.side === "wia");
      if (!wia.length) return "No commitments on record for this account.";
      const last = meetings[0];
      const fromCall = last ? wia.filter((c) => c.meetingId === last.id) : [];
      const rows = fromCall.length ? fromCall : wia;
      const done = rows.filter((c) => c.state === "done").length;
      return `${plural(rows.length, "commitment")}${
        fromCall.length && last ? ` from the ${last.date} call` : ""
      } · ${done} delivered, ${rows.length - done} outstanding.`;
    },
  },
  {
    q: "What are we waiting on?",
    tab: "commitments",
    patch: { commitSide: "client", commitState: "all" },
    sources: ["ClickUp · blocking tasks", "Gmail · thread direction", "Slack · channel"],
    answer: ({ commitments, client }) => {
      const open = commitments.filter((c) => c.side === "client" && c.state !== "done");
      if (!open.length) return "Nothing outstanding from this client.";
      const late = open.filter((c) => c.state === "overdue").length;
      return `${plural(open.length, "item")} outstanding from ${client.contact}${
        late ? ` · ${late} past the agreed date` : ""
      }.`;
    },
  },
  {
    q: "What is overdue?",
    tab: "commitments",
    patch: { commitSide: "all", commitState: "overdue" },
    sources: ["ClickUp · overdue view", "HighLevel · invoice state"],
    answer: ({ commitments, invoices }) => {
      const late = commitments.filter((c) => c.state === "overdue");
      const bills = invoices.filter((i) => i.state === "overdue");
      if (!late.length && !bills.length) return "Nothing overdue on this account.";
      const parts: string[] = [];
      if (late.length) parts.push(plural(late.length, "commitment"));
      if (bills.length)
        parts.push(
          `${plural(bills.length, "invoice")} (${money(
            bills.reduce((t, i) => t + i.amount, 0),
          )})`,
        );
      return `${parts.join(" and ")} overdue.`;
    },
  },
  {
    q: "Has the team acknowledged the latest actions?",
    tab: "commitments",
    patch: { commitSide: "wia", commitState: "unacked" },
    sources: ["Slack · reactions and replies", "ClickUp · status events"],
    answer: ({ commitments }) => {
      const ours = commitments.filter((c) => c.side === "wia" && c.state !== "done");
      if (!ours.length) return "No open actions on this account.";
      const silent = ours.filter((c) => c.ack === "none").length;
      return `${ours.length - silent} of ${plural(
        ours.length,
        "open action",
      )} acknowledged${silent ? ` · ${silent} still silent` : ""}.`;
    },
  },
  {
    q: "When did we last email them?",
    tab: "timeline",
    patch: { timelineSource: "gmail" },
    sources: ["Gmail · thread history"],
    answer: ({ timeline }) => {
      const last = timeline.find((r) => r.s === "gmail");
      if (!last) return "No email on record for this account.";
      return `${last.when} — ${last.text} (${last.status.toLowerCase()}).`;
    },
  },
  {
    q: "Where is the last meeting recording?",
    tab: "meetings",
    sources: ["Drive · mapped meeting folder", "Zoom / Fathom · recording"],
    answer: ({ meetings }) => {
      const last = meetings[0];
      if (!last) return "No meetings recorded against this account.";
      if (last.fileDest.startsWith("No mapped"))
        return `${last.date} — recorded, but filing was skipped: no mapped folder.`;
      return `${last.date} — ${plural(last.files.length, "file")} filed to ${last.fileDest}.`;
    },
  },
  {
    q: "What has changed since the last call?",
    tab: "timeline",
    patch: { timelineSource: "all" },
    sources: ["ClickUp · status events", "Slack · channel", "Gmail · today"],
    answer: ({ timeline, meetings }) => {
      const recent = timeline.filter((r) => RECENT_WHEN.includes(r.when));
      if (!recent.length) return "Nothing has moved since the last call.";
      const last = meetings[0];
      const sources = new Set(recent.map((r) => r.s));
      return `${plural(recent.length, "event")} across ${plural(
        sources.size,
        "source",
      )} since ${last ? `the ${last.date} call` : "the last call"}.`;
    },
  },
];

/* ── Account attention, derived once ─────────────────────────────
   ONE definition of "this account needs attention", used by the nav badge,
   the account cards and the Now tab. It was previously CLIENTS.length, which
   put a 6 on the sidebar and told the operator that every account was on
   fire — a badge that never changes is a badge nobody reads.

   Blocked counts as attention; open-and-not-yet-due does not. That is why
   Magnolia House stays quiet: its proposal is due today and nothing has
   slipped yet, so surfacing it would dilute the four accounts that have. */

/* F12: a flag used to be a coloured pill and nothing else, so "2 commitments
   overdue" left the reader to work out where those two live. Each flag now
   carries the destination that resolves it. */
export type AccountFlag = {
  text: string;
  tone: Tone;
  screen?: ScreenId;
  extra?: Record<string, unknown>;
};

export function accountFlags(
  clientId: string,
  /* LIVE stage reader. Without it these flags were computed from static
     COMMITMENTS alone, so acknowledging a chase or completing a delivery
     anywhere else in the hub left the account overview saying the opposite.
     Optional so the pure-data tests can still call it. */
  stageOf?: (obligationId: string) => WorkStage,
): AccountFlag[] {
  const flags: AccountFlag[] = [];
  const commits = COMMITMENTS.filter((c) => c.clientId === clientId).map((c) =>
    liveCommitment(c, stageOf),
  );

  const lateOurs = commits.filter((c) => c.side === "wia" && c.state === "overdue");
  if (lateOurs.length)
    flags.push({
      text: `${lateOurs.length} commitment${lateOurs.length === 1 ? "" : "s"} overdue`,
      tone: "red",
      screen: "clients",
      extra: { clientId, clientTab: "commitments", commitSide: "wia", commitState: "overdue" },
    });

  const blocked = commits.filter((c) => c.state === "blocked");
  if (blocked.length)
    flags.push({
      text: `${blocked.length} blocked`,
      tone: "amber",
      screen: "clients",
      extra: { clientId, clientTab: "commitments", commitSide: "all", commitState: "blocked" },
    });

  const lateBills = (CLIENT_INVOICES[clientId] ?? []).filter(
    (i) => i.state === "overdue",
  );
  if (lateBills.length)
    flags.push({
      text: `${lateBills.map((i) => i.id).join(", ")} overdue`,
      tone: "red",
      screen: "ops",
      extra: { opsTab: "finance", invoiceId: lateBills[0].id },
    });

  const silent = commits.filter(
    (c) => c.side === "wia" && c.state !== "done" && c.ack === "none",
  );
  if (silent.length)
    flags.push({
      text: `${silent.length} unacknowledged`,
      tone: "amber",
      screen: "ops",
      extra: { opsTab: "team" },
    });

  const lateTheirs = commits.filter((c) => c.side === "client" && c.state === "overdue");
  if (lateTheirs.length)
    flags.push({
      text: `${lateTheirs.length} waiting on client`,
      tone: "amber",
      screen: "inbox",
      extra: { inboxQueue: "waiting_client" },
    });

  const unmatched = (CLIENT_ATTENDANCE[clientId] ?? []).filter(
    (a) => a.state === "unmatched",
  );
  if (unmatched.length)
    flags.push({
      text: "Attendance unmatched",
      tone: "red",
      screen: "clients",
      extra: { clientId, clientTab: "attendance" },
    });

  return flags;
}

/* An account is "on the board" if anything has actually slipped: an overdue
   commitment on EITHER side, an overdue invoice, a blocked commitment, or an
   unresolved attendance match. An unacknowledged-but-not-yet-late action is a
   nudge, not an alarm, and is the one signal deliberately excluded.

   Stated against the ledgers rather than by reading the tones out of
   accountFlags. A rule that infers severity from pill colour breaks silently
   the first time a label is reworded — which it did: a client-side overdue
   row renders amber, so Everly Estate dropped off the board despite an
   Ads-account submission a week past due and blocking its audit round. */
export function accountNeedsAttention(
  clientId: string,
  stageOf?: (obligationId: string) => WorkStage,
): boolean {
  const commits = COMMITMENTS.filter((c) => c.clientId === clientId).map((c) =>
    liveCommitment(c, stageOf),
  );
  return (
    commits.some((c) => c.state === "overdue" || c.state === "blocked") ||
    (CLIENT_INVOICES[clientId] ?? []).some((i) => i.state === "overdue") ||
    (CLIENT_ATTENDANCE[clientId] ?? []).some((a) => a.state === "unmatched")
  );
}

/* ── The commitment ledger, read through the live lifecycle ───────
   A commitment carries two independent facts: whether it is LATE (its own
   `state`, which is about the calendar) and how far the work has got (the
   obligation's stage, which is about people). They were previously one
   static field, so nothing anyone did in the hub could move a commitment.

   The rule: a closed stage makes the row Delivered whatever the calendar
   said; an open stage cannot un-deliver a row that was seeded done; and the
   acknowledgement column is answered by the lifecycle rather than by a
   hardcoded `ack`. */
export function liveCommitment(
  c: Commitment,
  stageOf?: (obligationId: string) => WorkStage,
): Commitment {
  const obligationId = OBLIGATION_BY_COMMITMENT[c.id];
  if (!stageOf || !obligationId) return c;
  const stage = stageOf(obligationId);
  const closed = STAGE_META[stage].closed;
  return {
    ...c,
    state: closed ? "done" : c.state === "done" ? "in_progress" : c.state,
    ack:
      c.ack === "na"
        ? "na"
        : isAcknowledged(stage)
          ? stage === "in_progress"
            ? "manual"
            : "status_moved"
          : "none",
  };
}

/** The obligation behind a commitment row, for the cross-screen link. */
export const commitmentObligation = (id: string): string | undefined =>
  OBLIGATION_BY_COMMITMENT[id];

/* ── Ops Watch ────────────────────────────────────────────────── */

export const OPS_TABS: [string, string][] = [
  ["team", "Team"],
  ["waiting", "Waiting"],
  ["finance", "Finance"],
  ["data", "Data Quality"],
  ["routines", "Routines"],
];

export type TeamAction = {
  id: string;
  client: string;
  task: string;
  owner: string;
  since: string;
  facts: [string, string][];
};

export const TEAM_ACTIONS: TeamAction[] = [
  {
    id: "ack-jacqueline",
    client: "Bloom Manor",
    task: "Testimonial creative",
    owner: "Jacqueline",
    since: "No acknowledgement after 23 hours",
    facts: [
      ["Source", "Sep 2 strategy call · 31:05"],
      ["ClickUp", "Open · due yesterday"],
      ["Slack", "Message delivered, no reaction"],
    ],
  },
  {
    id: "ack-carmen",
    client: "Rosewood Venue",
    task: "Reply to client question",
    owner: "Carmen",
    since: "No reply after 29 business hours",
    facts: [
      ["Source", "Client Gmail thread"],
      ["ClickUp", "No task created"],
      ["Expectation", "24–48 business hours"],
    ],
  },
];

/* ── The overdue rows behind Home's "2 overdue" ──────────────────
   These used to be the literal `2` in `teamRisk = 2 + …`. A hardcoded
   component of a derived number is the same defect as a hardcoded badge: the
   Ops Watch list and the Home KPI could disagree and nothing would catch it.
   They are the two client-facing rows out of the Monday digest. */
export type OverdueTask = {
  id: string;
  client: string;
  task: string;
  owner: string;
  overdueBy: string;
  clickup: string;
};

export const OVERDUE_TASKS: OverdueTask[] = [
  {
    id: "od-bloom-testimonial",
    client: "Bloom Manor",
    task: "Testimonial creative",
    owner: "Jacqueline",
    overdueBy: "1 day",
    clickup: "Testimonial creative · Open · due yesterday",
  },
  {
    id: "od-rosewood-recap",
    client: "Rosewood Venue",
    task: "Rosewood recap",
    owner: "Gisselle",
    overdueBy: "Due today, not started",
    clickup: "Rosewood recap · Open · due today",
  },
];

/* The four ways an action can be considered acknowledged. Stated on screen
   because "acknowledged" is otherwise the vaguest word in the product. */
export const ACK_PATHS = [
  "Owner reacts with the configured acknowledgement emoji on the action message",
  "Owner replies in the action thread",
  "Linked ClickUp task moves out of Open",
  "Reviewer marks it acknowledged by hand",
];

export type Invoice = {
  id: string;
  client: string;
  amount: string;
  age: string;
  due: string;
  contact: string;
};

/* DERIVED from CLIENT_INVOICES — the finance queue is "every overdue row in
   the ledger", not a second hand-kept list that can disagree with it. */
export const INVOICES: Invoice[] = CLIENTS.flatMap((c) =>
  (CLIENT_INVOICES[c.id] ?? [])
    .filter((i) => i.state === "overdue")
    .map((i) => ({
      id: i.id,
      client: c.name,
      amount: money(i.amount),
      age: `${i.overdueDays}d`,
      due: i.due,
      contact: `${c.contact} · ${c.email}`,
    })),
);

export type InvalidEmail = {
  id: string;
  /** WHICH ACCOUNT. Without it, half this work is invisible: invalid-email
      checks run in both HighLevel accounts (2 Sept @9:30). */
  tenant: "Wedding Industry Ads" | "LeadLock Pro";
  name: string;
  role: string;
  entered: string;
  validity: string;
  suggestion: string;
  confidence: string;
  when: string;
  lowConfidence?: boolean;
};

export const INVALID_EMAILS: InvalidEmail[] = [
  {
    id: "iq1",
    tenant: "Wedding Industry Ads",
    name: "Jessica Morgan",
    role: "New lead · requested the venue-tour guide",
    entered: "jessica@gmail.con",
    validity: "Undeliverable",
    suggestion: "jessica@gmail.com",
    confidence: "High",
    when: "Flagged 08:10",
  },
  {
    /* The abstain case. `@rmail` has no safe correction, so the row refuses
       to guess. An automation that always answers is the one you stop
       trusting the first time it silently rewrites a real address. */
    id: "iq2",
    /* The second account. Its rows look identical without the tenant column,
       which is exactly how half the work goes missing. */
    tenant: "LeadLock Pro",
    name: "Priya Raman",
    role: "New lead · requested pricing sheet",
    entered: "priya@rmail",
    validity: "Risky · unverifiable",
    suggestion: "No safe correction suggested",
    confidence: "Low",
    when: "Flagged 08:10",
    lowConfidence: true,
  },
];

export type Routine = {
  title: string;
  system: AutoSystem;
  cadence: string;
  status: string;
  checklist: string[];
  note: string;
  /* ── THE OPERATIONAL HOME — F12 ────────────────────────────────
     Several efficiency outputs in the Blueprint had no answer to "and then
     what?": a returned questionnaire that cannot be filed, a recap waiting
     for portal approval, a missing workshop theme, a monthly report awaiting
     review. Listing an automation without naming where its exceptions land
     means Gisselle still coordinates them by hand — the hub just becomes
     another place to look.

     Six fields, one row each, and no new screen per automation. */
  trigger: string;
  /** Which existing queue an exception lands in. Never a new screen. */
  queue: string;
  reviewer: string;
  /** The NATIVE system the output ends up in. */
  destination: string;
  /** Who picks it up when the automated path fails or an input is missing. */
  failureOwner: string;
  /** How anyone knows it is finished. */
  completion: string;
  /** What is missing today that would stop it, if anything. */
  missingInput?: string;
  initiative: string;
};

/* The native-vs-AI inventory. Most of these are platform behaviour we are
   NOT rebuilding, and saying so is the point of the table. The count is
   derived on screen rather than written here — it read "six of nine" against
   ten rows for as long as it was a sentence. */
export const ROUTINES: Routine[] = [
  {
    title: "Google Office Hours host checklist",
    system: "clickup",
    cadence: "Weekly · Thursday · owner Carmen",
    status: "Recurring",
    checklist: ["Host Zoom session", "Complete attendance record", "Post internal recap"],
    note: "ClickUp recurring task — no custom AI required.",
    trigger: "ClickUp recurring task fires each Thursday morning",
    queue:
      "Ops Watch · Routines. Non-completion shows in the Monday overdue digest.",
    reviewer: "Carmen — she is the host",
    destination: "ClickUp (task) + the roll-call record",
    failureOwner: "Gisselle, if the checklist is still open on Friday",
    completion: "Checklist ticked and an attendance record exists for the session",
    initiative: "MP-01",
  },
  {
    title: "Meta Office Hours host checklist",
    system: "clickup",
    /* Jacqueline, not Carmen. Sept 2 @14:00: "Carmen is for Google Ads
       office hours … then Jacqueline for meta ads". The copied row was the
       one place in the hub that contradicted the rest of the mapping. */
    cadence: "Weekly · Thursday · owner Jacqueline",
    status: "Recurring",
    checklist: ["Host Zoom session", "Complete attendance record", "Post internal recap"],
    note: "ClickUp recurring task — roll-call completion lives in the checklist.",
    trigger: "ClickUp recurring task fires each Thursday afternoon",
    queue:
      "Ops Watch · Routines. Non-completion shows in the Monday overdue digest.",
    reviewer: "Jacqueline — she is the host",
    destination: "ClickUp (task) + the roll-call record",
    failureOwner: "Gisselle, if the checklist is still open on Friday",
    completion: "Checklist ticked and an attendance record exists for the session",
    initiative: "MP-01",
  },
  {
    title: "Google Office Hours reminder",
    system: "highlevel",
    cadence: "Weekly · 1 hour before",
    status: "Scheduled",
    checklist: [],
    note: "Scheduled in HighLevel Social Planner to the Community channel.",
    trigger: "Scheduled 1 hour before the session",
    queue:
      "No queue while it succeeds; a failed post lands in Ops Watch · Routines",
    reviewer: "None — copy is pre-approved and recurring",
    destination: "HighLevel Social Planner → Google Search Accelerator channel",
    failureOwner: "Gisselle posts by hand if the scheduled instance does not publish",
    completion: "Publication receipt from the Social Planner",
    missingInput:
      "Publication receipts are a tenant assumption — see the capability register",
    initiative: "MP-02",
  },
  {
    title: "Meta Office Hours reminder",
    system: "highlevel",
    cadence: "Weekly · 1 hour before",
    status: "Scheduled",
    checklist: [],
    note: "Approved recurring copy variants — no weekly approval needed.",
    trigger: "Scheduled 1 hour before the session",
    queue:
      "No queue while it succeeds; a failed post lands in Ops Watch · Routines",
    reviewer: "None — approved recurring copy variants",
    destination: "HighLevel Social Planner → Meta Ads Accelerator channel",
    failureOwner: "Gisselle posts by hand if the scheduled instance does not publish",
    completion: "Publication receipt from the Social Planner",
    missingInput:
      "Publication receipts are a tenant assumption — see the capability register",
    initiative: "MP-02",
  },
  {
    title: "Q&A reminder",
    system: "validation",
    cadence: "Every other week · 1 hour before",
    status: "Scheduled",
    checklist: [],
    note: "Recurring Community series behaviour needs production validation in the WIA tenant; otherwise pre-schedule each instance.",
    trigger: "Every other week, 1 hour before the announced Q&A",
    queue: "Ops Watch · Routines",
    reviewer: "None once the recurring series is validated in the tenant",
    destination: "HighLevel Communities → Announcements",
    failureOwner: "Gisselle",
    completion: "Publication receipt from the Social Planner",
    missingInput:
      "Whether a recurring Community series can be scheduled at all in this tenant is untested",
    initiative: "MP-02",
  },
  {
    title: "Workshop reminder",
    system: "ai_assisted",
    cadence: "Every other week · theme changes",
    status: "Needs review",
    checklist: [],
    note: "Theme-specific copy is drafted for review, then scheduled in HighLevel.",
    trigger: "Every other week — but only once Whitney has set the theme",
    queue: "AI Inbox · Needs Whitney, as a draft awaiting the theme",
    reviewer: "Whitney — the theme and title are hers",
    destination: "HighLevel Communities → Announcements",
    failureOwner: "Gisselle chases Whitney for the theme; unposted is worse than late",
    completion: "Post published with the correct theme",
    missingInput:
      "THE THEME. Without it the reminder cannot be drafted at all — this is the missing-input case the queue has to show rather than silently skip.",
    initiative: "MP-02",
  },
  {
    title: "Monday overdue digest",
    system: "ai_hq",
    cadence: "Monday · 08:30 · ClickUp → Slack",
    status: "Scheduled",
    checklist: [],
    note: "Deterministic overdue query; AI only groups and shortens the digest.",
    trigger: "Monday 08:30, deterministic ClickUp overdue query",
    queue: "Ops Watch · Team",
    reviewer: "Gisselle reviews before it posts",
    destination: "Slack #team-ops",
    failureOwner: "Gisselle posts the list by hand",
    completion: "Posted, and each named row acknowledged by its owner",
    initiative: "OP-01",
  },
  {
    title: "Invalid-email verification",
    system: "highlevel",
    cadence: "On workflow entry",
    status: "Active",
    checklist: [],
    note: "Native HighLevel Email Verification branches risky/invalid contacts to human review.",
    trigger: "Contact enters a workflow in either HighLevel account",
    queue: "Ops Watch · Data Quality",
    reviewer:
      "Gisselle — the correction is hers, and the automation abstains when it cannot suggest one",
    destination: "HighLevel contact record, then re-entry into the workflow",
    failureOwner:
      "Gisselle; an address with no safe correction stays flagged rather than guessed",
    completion:
      "Corrected address saved AND the contact re-entered the workflow so the material actually goes",
    initiative: "OP-03",
  },
  {
    title: "Invoice exception",
    system: "native_highlevel_ai",
    cadence: "On invoice status change",
    status: "Active",
    checklist: [],
    note: "Native HighLevel event → Ops Hub personal Gmail follow-up. Scheduled API query is the fallback.",
    trigger: "Invoice status changes to overdue in the WIA HighLevel account",
    queue: "Ops Watch · Finance",
    reviewer: "Whitney sees the amount and wording; Gisselle sends from hello@",
    destination: "Gmail draft under hello@, carrying the HighLevel payment link",
    failureOwner: "Gisselle, if the payment link cannot be read from the invoice",
    completion: "Invoice marked paid in HighLevel — not when the email is sent",
    missingInput:
      "LeadLock Pro takes no payments, so this routine runs against the WIA account only",
    initiative: "OP-03",
  },
  /* THE LARGEST RECURRING COST IN DISCOVERY, AND IT IS NOT THIS HUB'S JOB.
     Tina spends "the first few business days of the month" assembling client
     reports by hand (Sept 2 @33:01) — 18–24 hrs/month, more than every audited
     assistant task put together. It is client-facing delivery, not internal
     ops, so it is built separately as PM-03 in the Blueprint. It is listed
     here anyway: a routines table that silently omitted the biggest routine
     would be the more misleading choice. */
  {
    title: "Monthly client report pack",
    system: "human",
    cadence: "Monthly · first 3 business days · owner Tina",
    status: "Not automated",
    checklist: [
      "Pull Google Ads and Meta screenshots per account",
      "Write the why behind the numbers",
      "Record the video walkthrough",
    ],
    note: "18–24 hrs/month, entirely manual today. Out of this hub's scope — delivered as PM-03 (Monthly Client Report Pack) in the Blueprint roadmap.",
    trigger: "First business day of the month",
    queue: "Not in this hub — PM-03 has its own review step",
    reviewer: "Whitney approves every client-facing report",
    destination: "Client email + the client's Drive folder",
    failureOwner: "Tina, as today",
    completion: "Report delivered and the monthly strategy call booked",
    missingInput:
      "One current report exactly as a client receives it, and a decision on the video walkthrough",
    initiative: "PM-03",
  },
];

export const DIGEST_PREVIEW =
  "*Monday overdue digest — 6 tasks across 3 people*\n\n• Jacqueline — Bloom Manor testimonial creative (overdue 1 day)\n• Jacqueline — Clear 3 overdue Bloom Manor tasks (due Wednesday)\n• Carmen — Google keyword exclusions (due Thursday)\n• Carmen — Meta audience exclusions (due Friday)\n• Gisselle — Rosewood recap (due today)\n• Gisselle — Office Hours host coverage (due tomorrow)\n\n3 of 6 are client-facing.";

/* ── Content Atelier ─────────────────────────────────────────────
   Moved to data/contentAtelier.ts on 21 September. It was a constant nested
   in this file when the workspace held one transcript; the access handover
   turned it into a corpus of forty-odd artifacts across seven platforms
   with its own coverage model, which is a module. */

/* ── Settings ─────────────────────────────────────────────────── */

export type SourceSetting = {
  key: SourceKey;
  role: string;
  status: string;
  tone: Tone;
  caps: string[];
  note: string;
};

/* Every `note` here is a real production constraint, not flavour. They are
   the reason this is a demo environment and not a deployment. */
export const SOURCE_SETTINGS: SourceSetting[] = [
  {
    key: "gmail",
    role: "Primary client communication · hello@…",
    status: "Covered",
    tone: "green",
    caps: [
      "mailbox push notifications",
      "threads",
      "labels",
      "create drafts",
      "last event 2m ago",
    ],
    note: "Production notes: mailbox watches must be renewed at least every 7 days (daily recommended) and notifications can be delayed, so a history-sync fallback is required. Draft-only is an APPLICATION boundary, not an OAuth one — the scopes that create drafts also permit sending, so the guarantee is that this service exposes no send operation.",
  },
  {
    key: "slack",
    role: "Primary internal communication",
    status: "Partial coverage",
    tone: "amber",
    caps: [
      "8 authorized channels",
      "2 private client channels missing",
      "reaction + reply events",
      "post to authorized channels",
    ],
    note: "Production note: history and events are scope- and membership-dependent. The hub never claims all-workspace visibility.",
  },
  {
    key: "clickup",
    role: "Task ledger · 4 client lists + Ops list",
    status: "Covered",
    tone: "green",
    caps: [
      "create tasks with owner + due date",
      "status / assignee webhooks",
      "native recurring host tasks",
      "webhook health: good",
    ],
    note: "Office Hours host checklists stay native ClickUp recurring tasks — no custom recurrence is built.",
  },
  {
    key: "zoom",
    role: "Whitney-hosted meetings + Office Hours",
    status: "Partial coverage",
    tone: "amber",
    caps: [
      "ai@ user with a recordings + transcripts role",
      "workshop transcripts — searchable by “workshop”",
      "CLIENT MEETINGS DELETED BY POLICY",
      "past-meeting participant report",
    ],
    /* DOWNGRADED 21 Sep. This read "Covered", which was true of the API and
       false of the archive. WIA deletes client meetings from Zoom to save
       storage and files the recording to Drive, so the integration reaches
       the workshops and reaches almost none of the calls carrying client
       results — and the Drive copy is video with no transcript beside it. */
    note: "Production note: client meetings are deleted from Zoom by policy and archived to Drive as video, so the transcript-completed event never fires for them. Cloud transcription also requires a paid plan with audio transcription enabled, and the participant API requires Pro or higher.",
  },
  {
    key: "fathom",
    role: "Team meeting source · per-user keys",
    status: "Partial coverage",
    tone: "amber",
    caps: [
      "1 public share URL — Meta Ads Office Hours, 27 Aug",
      "no API key supplied",
      "plan tier unconfirmed",
      "Whitney — not used (Zoom source)",
    ],
    /* CORRECTED 21 Sep. Three users were listed as "covered" on the strength
       of a plan, not a key. The access handover supplied one public share
       link and no key at all, so nothing here is reachable programmatically —
       including Jacqueline's Meta office hours, which exist nowhere else. */
    note: "Production note: Fathom API keys are user-level and none has been issued. A key reaches meetings that user recorded or that were shared to their Team; an admin key does not unlock other users’ unshared meetings.",
  },
  {
    key: "drive",
    role: "Meeting archive",
    status: "Covered",
    tone: "green",
    caps: [
      "file into mapped client folders",
      "11 client folders mapped",
      "1 mapping unresolved — Harbor House",
    ],
    note: "The hub files into existing folders only. It does not create onboarding folder structures.",
  },
  {
    /* TWO ACCOUNTS, NOT ONE. The hub previously described "a shared GHL
       sub-account" and the API dependency claimed both domains run in one.
       They do not, and the difference is load-bearing: the invoice check
       belongs to WIA only, while invalid-email checks run in both. */
    key: "highlevel",
    role: "TWO accounts · WIA (agency) and LeadLock Pro (white label)",
    status: "Partial coverage",
    tone: "amber",
    caps: [
      "WIA — invoices, Community, members portal, contacts",
      "LeadLock Pro — contacts and invalid emails ONLY",
      "LeadLock Pro takes no payments",
      "Community post scheduling (Social Planner)",
      "email verification action",
    ],
    note: "Production validation required in EACH account separately: confirm the recurring Community series behaves as expected in the WIA tenant, that the invoice payload exposes the client-facing payment URL, and that a corrected contact can re-enter its workflow. The WIA location id is now recorded — Xi40zxmRvW8Pbyk5DYHp, read off the email preview URLs in the 21 September handover. The LeadLock Pro id is still unknown, and no private integration token has been issued for either.",
  },
];

/* ── THE CAPABILITY REGISTER — F10 ───────────────────────────────
   Blanket readiness language ("API access required") flattened four very
   different situations into one. Each dependency now declares which of these
   it is, because they cost different amounts and support different promises:

     confirmed   a documented native path we have read and can point at
     configure   available, needs setting up in the client's tenant
     untested    an API path that exists but has not been proven on their data
     fallback    no automated path; a person does it, deliberately

   Nothing here is marked confirmed on the strength of a vendor's marketing
   page. Every row states what would have to be TESTED to move it up. */

export type CapabilityState = "confirmed" | "configure" | "untested" | "fallback";

export const CAPABILITY_META: Record<
  CapabilityState,
  { label: string; tone: Tone }
> = {
  confirmed: { label: "Confirmed native path", tone: "green" },
  configure: { label: "Configuration needed", tone: "blue" },
  untested: { label: "Untested in their tenant", tone: "amber" },
  fallback: { label: "Manual fallback", tone: "slate" },
};

export type Capability = {
  area: string;
  initiative: string;
  state: CapabilityState;
  /** What we actually know, stated without overreach. */
  position: string;
  /** The test that would move this row, or the reason it cannot. */
  validation: string;
  /** Public documentation, checked 10 September 2026. */
  reference?: string;
};

export const CAPABILITY_REGISTER: Capability[] = [
  {
    area: "Gmail — drafts only",
    initiative: "CC-02",
    state: "confirmed",
    position:
      "Draft-only is enforced by the application, not the OAuth grant — the scopes that create drafts also permit sending.",
    validation:
      "Confirm the service exposes no send call, and test the Gmail handoff on hello@.",
    reference: "https://developers.google.com/workspace/gmail/api/auth/scopes",
  },
  {
    area: "Dubsado — signed and paid triggers",
    initiative: "ON-01",
    state: "untested",
    position:
      "Dubsado has native Zapier triggers for Contract Signed and New Payment Received — better than email parsing, if the plan includes them.",
    validation:
      "Check plan availability and whether the payload identifies the first installment. Keep email parsing as fallback.",
    reference:
      "https://help.dubsado.com/en/articles/15920601-dubsado-triggers-and-actions-in-zapier",
  },
  {
    area: "Fathom — meeting coverage",
    initiative: "MK-01",
    state: "untested",
    position:
      "Keys are per-user, so a Team plan is not access to every recording. Zoom already covers Whitney's own calls.",
    validation:
      "Test one recording per recorder and one private meeting before buying an upgrade.",
    reference: "https://developers.fathom.ai/quickstart",
  },
  {
    area: "Drive — archival and provisioning",
    initiative: "MK-02 / ON-03 / ON-04",
    state: "configure",
    position:
      "A shared folder in My Drive is not a shared drive. Service accounts own no files and carry no quota.",
    validation:
      "Identify each destination type, then test upload, sharing and duplicates on one real folder.",
    reference:
      "https://developers.google.com/workspace/drive/api/guides/handle-errors#storageQuotaExceeded",
  },
  {
    area: "Canva — dated session banners",
    initiative: "MP-03",
    state: "fallback",
    position:
      "Autofill requires Canva Enterprise. Exporting a design is not the same entitlement.",
    validation:
      "Confirm the plan. If not available, keep the manual date edit and export.",
    reference: "https://www.canva.dev/docs/connect/autofill-guide/",
  },
  {
    area: "HighLevel Communities — publishing",
    initiative: "MP-02 / MP-03",
    state: "untested",
    position:
      "Social Planner is the right tool. Tags, recurrence, event targeting and failure receipts are still assumptions.",
    validation:
      "Post one of each event type in the right channel, plus a changed theme and a failed post.",
    reference:
      "https://help.gohighlevel.com/support/solutions/articles/155000004093/",
  },
  {
    area: "Zoom — recording, transcript, participants",
    initiative: "MK-01 / MK-02 / MP-01",
    state: "configure",
    position:
      "The participant report is the right attendance source — it sees silent attendees. Needs Pro or higher.",
    validation:
      "Confirm the plan tier and pull one participant report for a real session.",
  },
  {
    area: "Ads accounts — metric access",
    initiative: "PM-01 / PM-02 / PM-03",
    state: "untested",
    position:
      "No inventory yet of which ad accounts are readable per client, or which metrics are available.",
    validation:
      "List every managed account and its access level. Reconcile against one current client report.",
  },
  {
    area: "HighLevel invoices — payment link",
    initiative: "OP-03",
    state: "untested",
    position:
      "The follow-up needs a payment URL from the invoice. It exists in the UI; the API payload is untested.",
    validation:
      "Read one overdue invoice over the API and confirm the payment URL.",
  },
  {
    area: "Corrected contacts — workflow re-entry",
    initiative: "OP-03",
    state: "untested",
    position:
      "Correcting the address is half the job — the contact also has to re-enter the workflow.",
    validation:
      "Test re-entry in each account and confirm the material is actually delivered.",
  },
  {
    area: "Model processing and retention",
    initiative: "All AI initiatives",
    state: "configure",
    position:
      "Client email, transcripts and account context pass through a model provider via OpenRouter.",
    validation:
      "Agree the routing and retention path before any client content is processed.",
  },
];

/* ── ACCOUNT AND MAILBOX TOPOLOGY — F09 ──────────────────────────
   The hub described "a shared GHL sub-account" and alternated between
   Whitney's mailbox, Whitney's and Gisselle's, and shared access. Discovery
   is specific and different, and the difference decides whether half the
   invalid-email work gets done at all.

   TWO HIGHLEVEL ACCOUNTS (2 Sept @8:45–9:47). Overdue payments exist in the
   WIA account only — "in this LeadLock Pro account, we don't take payments
   here". Invalid-email checks run in BOTH.

   ONE SHARED MAILBOX (26 Aug @26:00, 2 Sept @12:24). hello@ is where client
   communication arrives and leaves. Whitney stars; Gisselle drafts. `ai@` is
   an INTEGRATION IDENTITY agreed on 2 Sept — it is what tool access is
   granted to, and it does not by itself define which mailbox, sub-account,
   client folder or meeting is reachable. */

export type Tenant = {
  id: string;
  name: string;
  system: string;
  purpose: string;
  /** What this tenant is the source of. */
  sourceOf: string[];
  /** What it explicitly is NOT. */
  notSourceOf: string[];
  evidence: string;
};

export const TENANTS: Tenant[] = [
  {
    id: "ghl-wia",
    name: "Wedding Industry Ads",
    system: "HighLevel · agency SaaS plan",
    purpose: "The agency's own account",
    sourceOf: [
      "Overdue invoices + payment links",
      "Invalid-email contacts",
      "Members portal + Communities",
      "Accelerator rosters",
    ],
    notSourceOf: ["Client LeadLock builds"],
    evidence: "2 Sept @8:45–9:30, @13:21",
  },
  {
    id: "ghl-leadlock",
    name: "LeadLock Pro",
    system: "HighLevel · white-label side",
    purpose: "The GHL white-label used for client builds",
    sourceOf: ["Invalid-email contacts"],
    notSourceOf: [
      "Payments — none are taken here",
      "Members portal content",
    ],
    evidence: "2 Sept @9:30",
  },
  {
    id: "gmail-hello",
    name: "hello@weddingindustryads.com",
    system: "Gmail · shared mailbox",
    purpose: "All client and lead communication, in and out",
    sourceOf: [
      "Client threads, stars, waiting tag",
      "Dubsado signed / paid alerts",
      "Drafts — both Whitney and Gisselle",
    ],
    notSourceOf: ["Personal mailboxes"],
    evidence: "26 Aug @26:00; 2 Sept @12:24",
  },
  {
    id: "identity-ai",
    name: "ai@weddingindustryads.com",
    system: "Integration identity",
    purpose: "Credentials only — not a mailbox",
    sourceOf: ["Nothing — it is not a data source"],
    notSourceOf: [
      "Client mail — that is hello@",
      "Implicit access — each grant is separate",
    ],
    evidence: "2 Sept @0:05 and @18:27",
  },
];

/* ── EMAIL POLICY — F14 ──────────────────────────────────────────
   "Learns from your edits" and "never auto-archives tools mail" were both
   broader than what was actually said, and neither was written down as a
   rule anyone could check. This is the compact policy table the client has
   to agree, with the discovery line each row rests on and an explicit note
   where the row is a PROPOSAL rather than something they told us. */

export type PolicyRow = {
  situation: string;
  rule: string;
  basis: string;
  agreed: boolean;
};

export const EMAIL_POLICY: PolicyRow[] = [
  {
    situation: "Whitney read it and took no action",
    rule: "File to the client or category folder. Her reading it is the trigger.",
    basis: "26 Aug @25:03",
    agreed: true,
  },
  {
    situation: "Vendor and tool mail (Canva, Dubsado…)",
    rule: "Surface once, then file on her no-action. Never archived before she sees it.",
    basis: "26 Aug @30:15",
    agreed: true,
  },
  {
    situation: "A client thread with no reply from us",
    rule: "Escalate at 24 business hours, breach at 48. Owner nudged in Slack.",
    basis: "26 Aug @24:00",
    agreed: true,
  },
  {
    situation: "We are waiting on a client",
    rule: "Waiting tag, reviewed Mondays with Whitney. Her call, not a timer.",
    basis: "26 Aug @28:00",
    agreed: true,
  },
  {
    situation: "Business hours for every threshold above",
    rule: "Mon–Fri, Central, excluding US holidays. Gisselle is in Honduras.",
    basis: "No definition was given. 26 Aug @1:44",
    agreed: false,
  },
  {
    situation: "The starring system",
    rule: "Stars stay Whitney's signal; machine state moves to labels.",
    basis: "Six star meanings today. 26 Aug @39:36",
    agreed: false,
  },
  {
    situation: "A snoozed or kept email",
    rule: "Returns to its queue with its original actions. Deferral is not disposal.",
    basis: "Design requirement",
    agreed: true,
  },
  {
    situation: "An edit Whitney makes to a draft",
    rule: "Style edits become reviewed guidance. Factual edits correct that client only.",
    basis: "She asked for voice, not fact absorption. 26 Aug @40:03",
    agreed: false,
  },
  {
    situation: "Where draft facts come from",
    rule: "Phase 1: the thread, that client's Drive folder and ClickUp tasks. No cross-client retrieval.",
    basis: "The richer knowledge base is FF-01, Phase 3",
    agreed: false,
  },
];

/* ── DATA INVENTORY — F17 ────────────────────────────────────────
   "Synthetic demo data" is on the sidebar of every screen, and it is not an
   accurate description of everything in this repository. Three different
   kinds of material are present and they carry different sharing rules. */

export type DataOrigin = "synthetic" | "derived" | "real";

export const DATA_ORIGIN_META: Record<DataOrigin, { label: string; tone: Tone }> = {
  synthetic: { label: "Invented", tone: "green" },
  derived: { label: "Derived from real material", tone: "amber" },
  real: { label: "Real client data", tone: "red" },
};

export const DATA_INVENTORY: {
  what: string;
  where: string;
  origin: DataOrigin;
  shareable: string;
}[] = [
  {
    what: "Accounts, contacts, invoices and emails in this hub",
    where: "src/data/opsHub.ts",
    origin: "synthetic",
    shareable: "Yes — invented for the walkthrough",
  },
  {
    what: "Roll-call roster and session history",
    where: "src/data/rollCall.ts",
    origin: "synthetic",
    shareable: "Yes — a mock of the Communities roster",
  },
  {
    what: "Office-hours transcript used by the roll-call demo (Google track)",
    where: "src/data/rollCallTranscript.ts",
    origin: "derived",
    shareable:
      "Internal only — real member names",
  },
  {
    what: "Meta-track office-hours transcript",
    where: "src/data/rollCallMetaTranscript.ts",
    origin: "synthetic",
    shareable:
      "Yes — invented, to carry the brief and silent attendee cases",
  },
  {
    what: "ClickUp onboarding templates and assignees",
    where: "server/onboarding-templates.json",
    origin: "real",
    shareable:
      "Internal only — real staff names and procedures",
  },
  {
    what: "Onboarding sample client and its alert pair",
    where: "src/pages/OnboardingPage.tsx",
    origin: "real",
    shareable:
      "Internal only — a real signed client",
  },
  {
    what: "The Vault session content and its figures",
    where: "src/data/opsHub.ts · PACKAGES",
    origin: "derived",
    shareable:
      "Internal only — real client analytics on screen",
  },
  {
    what: "Internal-meeting transcript and ledger",
    where: "src/data/internalMeetingTranscript.ts",
    origin: "derived",
    shareable: "Internal only — a real team meeting",
  },
];

/* What this hub deliberately does NOT do. Onboarding orchestration is the
   first line because it is the one workstream already built elsewhere — the
   signature-branch console at /onboarding — and duplicating it here would
   create two disagreeing sources of truth. */
/* Each line names where that work actually lives, so "out of scope" reads as
   a boundary in a roadmap rather than as something nobody thought about. */
export const OUT_OF_SCOPE: [string, string][] = [
  ["No onboarding orchestration", "Client Onboarding console · ON-01 → ON-05"],
  ["No client performance reporting", "Monthly Client Report Pack · PM-03"],
  ["No ad strategy generation", "Fulfillment track · Phase 3"],
  ["No creative briefs", "Fulfillment track · FF-02"],
  ["No client ad copy", "Fulfillment track · FF-02"],
  ["No landing-page work", "Fulfillment track · FF-03"],
];

export const IDENTITY_ACCESS = ["ClickUp", "Slack", "HighLevel", "Drive"];

/* ── Command palette ──────────────────────────────────────────── */

export type PaletteDef = {
  tag: string;
  label: string;
  dest: string;
  /* ScreenId, not string: a palette row that points at a removed screen is a
     dead end the compiler should refuse, not something a grep has to find. */
  screen: ScreenId;
  extra?: Record<string, unknown>;
};

/* Fourteen operator questions, each routing to an exact screen + tab +
   filter. This is the answer to "how is it all connected?" — you ask the
   question you already ask out loud, and it lands on the answer. */
export const PALETTE_DEFS: PaletteDef[] = [
  { tag: "Review", label: "What needs my review today?", dest: "Home", screen: "home" },
  {
    tag: "Waiting",
    label: "What are we waiting on from clients?",
    dest: "AI Inbox",
    screen: "inbox",
    extra: { inboxQueue: "waiting_client" },
  },
  {
    tag: "Team",
    label: "Which team actions have not been acknowledged?",
    dest: "Ops Watch",
    screen: "ops",
    extra: { opsTab: "team" },
  },
  {
    tag: "Meetings",
    label: "What did we promise Bloom Manor on the last call?",
    dest: "Client Hub",
    screen: "clients",
    extra: {
      clientId: "bloom",
      clientTab: "commitments",
      askAnswer: "What did we promise them on the last call?",
    },
  },
  {
    tag: "Meetings",
    label: "Which meetings still need an execution pack approved?",
    dest: "Meetings",
    screen: "meetings",
    extra: { meetingId: null, meetingFilter: "needs_review" },
  },
  {
    tag: "Replies",
    label: "Which client emails are past the reply expectation?",
    dest: "AI Inbox",
    screen: "inbox",
    extra: { inboxQueue: "team_reply_due" },
  },
  {
    tag: "Finance",
    label: "Which invoices are overdue?",
    dest: "Ops Watch",
    screen: "ops",
    extra: { opsTab: "finance" },
  },
  {
    tag: "Data",
    label: "Which lead emails are invalid?",
    dest: "Ops Watch",
    screen: "ops",
    extra: { opsTab: "data" },
  },
  {
    tag: "Routines",
    label: "Which routines are native automations, not AI?",
    dest: "Ops Watch",
    screen: "ops",
    extra: { opsTab: "routines" },
  },
  {
    tag: "Content",
    label: "Which client-call moments could become WIA content?",
    dest: "Content Atelier",
    screen: "content",
  },
  {
    tag: "Sources",
    label: "What can the hub read and write?",
    dest: "Settings",
    screen: "settings",
  },
];

/* ── Home ─────────────────────────────────────────────────────── */

export type QueueRow = {
  time: string;
  label: string;
  status: string;
  tone: Tone;
  icon: string;
  /* Optional — a row with no screen renders as plain schedule text. Same
     reasoning as PaletteDef: the id itself is checked. */
  screen?: ScreenId;
  extra?: Record<string, unknown>;
};

export const OPERATING_QUEUE: QueueRow[] = [
  { time: "08:05", label: "Gmail changes synced", status: "Completed", tone: "green", icon: "✓" },
  {
    time: "08:07",
    label: "HighLevel invalid-email workflow checked",
    status: "Native",
    tone: "green",
    icon: "✓",
    screen: "ops",
    extra: { opsTab: "routines" },
  },
  {
    time: "08:10",
    label: "1 invalid email needs review",
    status: "Needs review",
    tone: "amber",
    icon: "⚠",
    screen: "ops",
    extra: { opsTab: "data" },
  },
  {
    time: "08:12",
    label: "Rosewood invoice became overdue",
    status: "Exception",
    tone: "amber",
    icon: "⚠",
    screen: "ops",
    extra: { opsTab: "finance", invoiceId: "INV-204" },
  },
  {
    time: "08:20",
    label: "Fathom coverage — 1 user source unverified",
    status: "Blocked",
    tone: "red",
    icon: "!",
    screen: "settings",
  },
  {
    time: "09:30",
    label: "Bloom Manor call processed",
    status: "Completed",
    tone: "green",
    icon: "✓",
    screen: "meetings",
    extra: { meetingId: "bloom-strategy" },
  },
  {
    time: "09:34",
    label: "Execution Pack needs review",
    status: "Needs review",
    tone: "blue",
    icon: "●",
    screen: "meetings",
    extra: { meetingId: "bloom-strategy" },
  },
  {
    /* 11:00 CST, matching lib/rollCall.ts and the more specific of the two
       readings in discovery (26 Aug @8:16 — "like 11am or 10am CST", and the
       member-portal reminder Gisselle reads out at 14:35 says 11am). */
    time: "11:00",
    label: "Google Office Hours",
    status: "Scheduled",
    tone: "neutral",
    icon: "○",
  },
  {
    time: "14:30",
    label: "Meta reminder scheduled in HighLevel",
    status: "Scheduled",
    tone: "neutral",
    icon: "○",
  },
  {
    time: "15:30",
    label: "Meta Office Hours",
    status: "Scheduled",
    tone: "neutral",
    icon: "○",
  },
  {
    time: "17:00",
    label: "Waiting-client aging check",
    status: "Scheduled",
    tone: "neutral",
    icon: "○",
    screen: "ops",
    extra: { opsTab: "waiting" },
  },
];

export const COVERAGE_STRIP: [SourceKey, string, Tone][] = [
  ["gmail", "Covered", "green"],
  ["slack", "8 channels", "amber"],
  ["clickup", "Covered", "green"],
  ["zoom", "Covered", "green"],
  ["fathom", "Partial · 3 users", "amber"],
  ["drive", "Covered", "green"],
  ["highlevel", "Covered", "green"],
];

export const TEAM_PULSE = [
  {
    initial: "J",
    title: "Bloom Manor testimonial creative",
    who: "Jacqueline",
    meta: "No Slack acknowledgement",
    status: "Overdue 1 day",
    tone: "red" as Tone,
  },
  {
    initial: "C",
    title: "Google keyword review",
    who: "Carmen",
    meta: "Due today",
    status: "Acknowledged",
    tone: "green" as Tone,
  },
  {
    initial: "G",
    title: "Rosewood recap",
    who: "Gisselle",
    meta: "Draft ready in Gmail",
    status: "Draft ready",
    tone: "blue" as Tone,
  },
  /* Tina's monthly report run. Nothing in this hub touches it — it is here so
     the person carrying the largest recurring load is visible on the screen
     that claims to show where the team's week is going. */
  {
    initial: "T",
    title: "Monthly reports · 4 accounts",
    who: "Tina",
    meta: "Manual · not automated (PM-03)",
    status: "Day 3 of 3",
    tone: "amber" as Tone,
  },
];

/* THE DEMO DAY HAS TO BE A THURSDAY. Home's operating queue schedules both
   Office Hours sessions — Google at 11:00, Meta at 15:30 — and those run every
   Thursday (26 Aug @8:16). Dated to a Friday, the one screen a host would read
   first showed their own sessions on a day they do not happen. September 3
   2026 is a Thursday, keeps Fathom's "last event: Sep 3" as today, and leaves
   the Sep 2 Bloom Manor call being processed the following morning. */
export const DEMO_DATE = "Thursday, September 3, 2026";
