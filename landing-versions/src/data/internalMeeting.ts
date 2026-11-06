/* ────────────────────────────────────────────────────────────────
   Internal Meeting + Action Items — the seeded ledger and the pre-computed
   extraction for the demo run.

   WHAT IS MOCKED AND WHAT IS NOT. The item set below is authored, because
   there is no LLM call in this build. Everything ABOUT each item is then
   computed at run time against the pasted text: the quote is verified as a
   literal substring, the MM:SS is derived from the turn that contains it, and
   the ledger match is a fingerprint comparison. So the items are fixed but the
   evidence is live — which is why one item deliberately carries a quote that
   is NOT in the transcript, and genuinely fails.

   THE LEDGER IS THE PRODUCT. There is no ClickUp integration anywhere in this
   feature, so carry-over cannot lean on an external task id. It leans on this
   card's own ledger instead, which is also why the loop that defeated
   Gisselle's two attempts cannot exist here: closure is a human assertion
   recorded locally, never a task status polled from someone else's system
   (26 Aug @6:03 — "when we completed a task, then, um, I don't know, it needed
   to create a new one... it got confusing and I haven't been able to figure
   that out").

   PRIOR-RUN QUOTES ARE NEVER SUBSTRING-CHECKED against the current paste. A
   ledger item's first sighting came out of a DIFFERENT transcript, so checking
   it here would fail every time and, worse, tempt someone to relabel it with a
   timestamp from this run.
   ──────────────────────────────────────────────────────────────── */

/** How an owner was resolved. Rendered on every row — never a bare name. */
export type OwnerBasis =
  | "addressed_directly"
  | "named_in_commitment"
  | "function_map"
  | "unmapped_external"
  | "abstained";

/** Where a date came from. A default must never look like something spoken. */
export type DueBasis = "spoken" | "relative" | "derived" | "default";

export const OWNER_BASIS_LABEL: Record<OwnerBasis, string> = {
  addressed_directly: "addressed directly",
  named_in_commitment: "named in the commitment",
  function_map: "function map",
  unmapped_external: "outside your team",
  abstained: "undecided",
};

export const DUE_BASIS_LABEL: Record<DueBasis, string> = {
  spoken: "a date was said",
  relative: "relative — resolved against the meeting date",
  derived: "derived from what was said",
  default: "default — nobody stated a date",
};

export interface LedgerItem {
  ledgerId: string;
  canonicalText: string;
  owner: string | null;
  ownerBasis: OwnerBasis;
  firstSeenRun: number;
  firstSeenLabel: string;
  /** From a PRIOR transcript. Displayed as-is; never verified against today's. */
  firstSeenDisplay: string;
  firstSeenQuote: string;
  sightings: number;
  /** Days open as of the demo review date, precomputed so no clock is read. */
  ageDays: number;
}

/* ── The seeded prior run ─────────────────────────────────────────
   Run #23 is the 26 August sync, already decided. Six items were recorded.
   Two of them come up again on 2 September and two of those two behave
   differently, which is the whole reason the demo runs a PAIR of meetings
   rather than one: with a single transcript this card does nothing Fathom does
   not already do for free. */
export const SEEDED_LEDGER: LedgerItem[] = [
  {
    ledgerId: "LGR-0004",
    canonicalText: "E2M to send the required items and accesses list",
    owner: "Minu Bhatt",
    ownerBasis: "unmapped_external",
    firstSeenRun: 23,
    firstSeenLabel: "26 Aug",
    firstSeenDisplay: "40:33",
    firstSeenQuote:
      "we'll have what's called a client's requirement document sent across",
    sightings: 1,
    ageDays: 7,
  },
  {
    ledgerId: "LGR-0002",
    canonicalText: "Walk E2M through the ClickUp onboarding process",
    owner: "Whitney Hodges",
    ownerBasis: "named_in_commitment",
    firstSeenRun: 23,
    firstSeenLabel: "26 Aug",
    firstSeenDisplay: "15:50",
    firstSeenQuote: "I'd love to just kind of get your eyes on that",
    sightings: 1,
    ageDays: 7,
  },
  {
    ledgerId: "LGR-0001",
    canonicalText: "Share the recording of the cloud session with Whitney",
    owner: "Asha Kumar",
    ownerBasis: "unmapped_external",
    firstSeenRun: 23,
    firstSeenLabel: "26 Aug",
    firstSeenDisplay: "42:36",
    firstSeenQuote: "I got the recording today. I'll share that with you",
    sightings: 1,
    ageDays: 7,
  },
  {
    ledgerId: "LGR-0003",
    canonicalText: "Create a Slack group and add the stakeholders",
    owner: "Asha Kumar",
    ownerBasis: "unmapped_external",
    firstSeenRun: 23,
    firstSeenLabel: "26 Aug",
    firstSeenDisplay: "43:03",
    firstSeenQuote: "Then I can create a group and, you know, add the stakeholders",
    sightings: 1,
    ageDays: 7,
  },
  {
    ledgerId: "LGR-0005",
    canonicalText: "Fix the mobile CTA that resolves to a 404",
    owner: "Gisselle Jimenez",
    ownerBasis: "function_map",
    firstSeenRun: 23,
    firstSeenLabel: "26 Aug",
    firstSeenDisplay: "41:28",
    firstSeenQuote: "on the mobile section, there is a CTA which points to a 404",
    sightings: 1,
    ageDays: 7,
  },
  {
    ledgerId: "LGR-0006",
    canonicalText: "Check the broken link in the investment guide",
    owner: "Gisselle Jimenez",
    ownerBasis: "function_map",
    firstSeenRun: 23,
    firstSeenLabel: "26 Aug",
    firstSeenDisplay: "41:55",
    firstSeenQuote: "I think we talked about a link in the investment guide",
    sightings: 1,
    ageDays: 7,
  },
];

export type RowKind =
  | "new"
  | "sighting"
  | "closure_candidate"
  | "abstain"
  | "unverified"
  | "not_proposed";

export interface ExtractedRow {
  id: string;
  kind: RowKind;
  title: string;
  owner: string | null;
  ownerBasis: OwnerBasis;
  /** Set on an abstain where two owners are equally plausible. */
  ownerCandidates?: string[];
  /** ISO, or null when nobody stated one. */
  due: string | null;
  dueBasis: DueBasis;
  dueNote?: string;
  /** Already past as of the review date — flagged rather than quietly shown. */
  duePast?: boolean;
  /** Verified live against the paste. Order matters: first is the primary. */
  quotes: string[];
  /** Set for a row that matched the ledger. */
  ledgerId?: string;
  /** Why this row was not proposed as an action. */
  reason?: string;
  /** The decision this row is asking a human for. */
  question?: string;
  /** Ledger owner before this run, when the sighting changed it. */
  ownerWas?: string;
  /** The ClickUp list this WOULD be filed under. Never written. */
  proposedList?: string;
}

/* ── The demo run ─────────────────────────────────────────────────
   Ten decidable rows plus four not-proposed. Deliberately not more: the point
   is a review that finishes in a couple of minutes, because a card that takes
   longer to check than the job takes to do by hand does not get used twice. */
export const DEMO_ROWS: ExtractedRow[] = [
  /* Two sightings inside ONE run, 46 minutes apart, collapsed to one item.
     Free proof of the dedupe mechanic that needs no prior run at all. */
  {
    id: "n1",
    kind: "new",
    title: "Create ai@weddingindustryads.com and share the credentials with Minu via LastPass",
    owner: "Whitney Hodges",
    ownerBasis: "named_in_commitment",
    due: null,
    dueBasis: "default",
    quotes: [
      "Yeah, we can definitely do that.",
      "Yeah, we can share that through LastPass.",
    ],
    proposedList: "Team Actions",
  },
  {
    id: "n2",
    kind: "new",
    title: "Grant ai@ access to ClickUp, GHL and the Members Portal",
    owner: "Gisselle Jimenez",
    ownerBasis: "function_map",
    due: null,
    dueBasis: "default",
    quotes: ["So we need to add you to ClickUp, our GHL, and then"],
    proposedList: "Team Actions",
  },
  {
    id: "n3",
    kind: "new",
    title: "Send E2M a couple of the office-hours transcripts",
    owner: "Gisselle Jimenez",
    ownerBasis: "addressed_directly",
    due: null,
    dueBasis: "default",
    quotes: [
      "Then if you can send across a transcript, a couple of them for the Office of Meetings, that would be perfect.",
    ],
    proposedList: "Team Actions",
  },
  {
    id: "n4",
    kind: "new",
    title: "Review the ClickUp onboarding checklist for quick wins once access lands",
    owner: "Minu Bhatt",
    ownerBasis: "unmapped_external",
    due: null,
    dueBasis: "default",
    dueNote: "Conditional on ClickUp access landing first.",
    quotes: [
      "I think once we have access to ClickUp, we can ourselves go through this entire checklist and identify things that are an easy, quick wins for us.",
    ],
  },

  /* The carry-over. Owner changed between runs, which is exactly why the
     fingerprint excludes owner — with it in the hash this match cannot fire. */
  {
    id: "s1",
    kind: "sighting",
    ledgerId: "LGR-0004",
    title: "E2M to send the required items and accesses list",
    owner: "Asha Kumar",
    ownerWas: "Minu Bhatt",
    ownerBasis: "unmapped_external",
    due: "2026-09-03",
    dueBasis: "relative",
    dueNote: '"tomorrow", resolved against the meeting date of 2 Sep',
    duePast: true,
    quotes: ["And tomorrow, when Asha sends out a recap, you'll also see a list of."],
  },

  /* The card NOTICES a possible completion and ASKS. It never asserts closure,
     because it cannot observe one — only a human can. */
  {
    id: "c1",
    kind: "closure_candidate",
    ledgerId: "LGR-0002",
    title: "Walk E2M through the ClickUp onboarding process",
    owner: "Whitney Hodges",
    ownerBasis: "named_in_commitment",
    due: null,
    dueBasis: "default",
    question:
      "This run contains what looks like the walkthrough itself. Mark it closed?",
    quotes: [
      "Yeah, I think, Gisselle, maybe if you want to share your screen and share, like, the ClickUp onboarding template, like, we can walk you through all of it.",
    ],
  },

  {
    id: "a1",
    kind: "abstain",
    title: "Add ai@ to Slack and all the client channels",
    owner: null,
    ownerBasis: "abstained",
    due: null,
    dueBasis: "default",
    question:
      "Phrased as a question, and no acceptance appears anywhere in this transcript. Is this an item?",
    quotes: [
      "Would it be helpful for us to actually get you guys with that AI at weddingindustryads.com into our Slack, and all the client channels",
    ],
  },
  {
    id: "a2",
    kind: "abstain",
    title: "Switch the team to a Fathom team account",
    owner: null,
    ownerBasis: "abstained",
    due: null,
    dueBasis: "default",
    question: "Conditional, no owner named and no date. Is this an item, and whose?",
    quotes: [
      "if we need to switch to a team account or anything like that, I mean, we, we totally can.",
    ],
  },
  {
    id: "a3",
    kind: "abstain",
    title: "The 15-minute sync after the blueprint call",
    owner: null,
    ownerBasis: "abstained",
    ownerCandidates: ["Asha Kumar", "Whitney Hodges"],
    due: null,
    dueBasis: "default",
    question: "Asha to schedule it, or Whitney to attend it?",
    quotes: ["you and me can have a history of 15-minute sync up just after the fall"],
  },

  /* DELIBERATELY BROKEN. "by Friday" appears nowhere in the transcript, so the
     substring check fails for real and this row lands in review with its
     quotation marks stripped. It is the only thing on screen proving the check
     runs rather than being claimed. */
  {
    id: "f1",
    kind: "unverified",
    title: "Send E2M the office-hours transcripts by Friday",
    owner: "Gisselle Jimenez",
    ownerBasis: "addressed_directly",
    due: "2026-09-05",
    dueBasis: "spoken",
    quotes: [
      "send across a transcript, a couple of them for the Office of Meetings by Friday",
    ],
  },

  {
    id: "x1",
    kind: "not_proposed",
    title: "Move off Dubsado and rebuild it into GHL",
    owner: null,
    ownerBasis: "abstained",
    due: null,
    dueBasis: "default",
    reason:
      "An owner is named, but there is no date and it is described as an ongoing plan that predates this meeting — nothing was committed here.",
    quotes: [
      "it is on Gisselle's plate and part of our plan for us to eventually stop using Dubsado",
    ],
  },
  {
    id: "x2",
    kind: "not_proposed",
    title: "Stop relying on the per-client ChatGPT projects",
    owner: null,
    ownerBasis: "abstained",
    due: null,
    dueBasis: "default",
    reason: "An opinion, not an action.",
    quotes: ["we don't see it as a long-term solution"],
  },
  {
    id: "x3",
    kind: "not_proposed",
    title: "Replace the monthly report with an executive summary",
    owner: null,
    ownerBasis: "abstained",
    due: null,
    dueBasis: "default",
    reason: "An aspiration — no owner, no date.",
    quotes: [
      "I would love something like that that can create more of just like an executive summary on a monthly basis.",
    ],
  },
  {
    id: "x4",
    kind: "not_proposed",
    title: "Swap the campaign URLs once LeadLock goes live",
    owner: null,
    ownerBasis: "abstained",
    due: null,
    dueBasis: "default",
    reason:
      "Standing process narration in the habitual tense — describing how it always works, not committing to it here.",
    quotes: ["we need to switch the URL for the campaigns to now go"],
  },
];

/** Ledger ids this run touched — everything else is the aging view. */
export const TOUCHED_LEDGER_IDS = DEMO_ROWS.map((r) => r.ledgerId).filter(
  (id): id is string => Boolean(id),
);

/* ── The processing stages ────────────────────────────────────────
   Three of the four genuinely run. The fourth is the pre-computed one and says
   so, because ten seconds of a spinner with invented stage labels is the one
   part of a mock that costs more than it returns — "what is it doing right
   now?" has to have a true answer. */
export interface StageSpec {
  id: string;
  label: string;
  /** false = pre-computed for this build, and labelled as such on screen. */
  real: boolean;
  /** Milliseconds this stage is held on screen. */
  holdMs: number;
}

export const STAGES: StageSpec[] = [
  { id: "read", label: "Reading the transcript", real: true, holdMs: 1200 },
  { id: "verify", label: "Checking every quote against the transcript, word for word", real: true, holdMs: 1600 },
  { id: "ledger", label: "Matching against your ledger", real: true, holdMs: 1400 },
  { id: "extract", label: "Pulling out commitments, owners and dates", real: false, holdMs: 5600 },
];

/** The review date the demo is staged on, so no wall clock is read. */
export const REVIEW_DATE = "2026-09-08";
export const RUN_NUMBER = 24;
export const PRIOR_RUN_NUMBER = 23;
