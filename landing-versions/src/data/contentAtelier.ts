/* ────────────────────────────────────────────────────────────────
   Content Atelier — the corpus, the queue and the published precedent.

   WHY THIS MOVED OUT OF opsHub.ts. The screen used to run on one moment,
   four candidate quotes and five drafts, because one session transcript was
   all the workspace held. The 21 September access handover changed that
   input: roughly forty artifacts across seven platforms, including five
   chains where a source recording, the ChatGPT reasoning that shaped it and
   the published email / Instagram post all survive. That is no longer a
   constant nested in a screen file — it is the dataset the feature exists to
   work on.

   THE ONE RULE EVERYTHING HERE OBEYS. Nothing is drafted from a source we
   do not hold in readable form. A .mp4 sitting in Drive is a RECORDING, not
   a transcript; the engine cannot quote it, and this model says so with
   `holds.transcript` rather than quietly generating something plausible.
   That distinction is the whole reason the queue below has three different
   blocked states instead of one list of ideas.

   THE HANDOVER'S OWN GAP, STATED ONCE. Client meetings are deleted from
   Zoom to save storage and archived to Drive as video. So the Zoom
   integration — which is the connected one — reaches the workshops and
   reaches almost none of the client calls, and the client calls are where
   the results live. Every "blocked" row in the queue traces back to that
   one fact. See TRANSCRIPTION_GAP.
   ──────────────────────────────────────────────────────────────── */

import { SOURCE_META, type SourceKey, type Tone } from "@/lib/opsHub";

/* ── Platforms ────────────────────────────────────────────────────
   SourceKey covers the seven systems the rest of the hub reads. Growth
   Signals touches four more that no other screen does, so they are added
   here rather than widening SourceKey for one feature. `stt` is not a
   vendor — it is the speech-to-text capability nobody has provisioned, kept
   as a platform so the queue can point at the thing that is missing. */

export type PlatformKey =
  | SourceKey
  | "chatgpt"
  | "instagram"
  | "openrouter"
  | "stt";

export const PLATFORM_META: Record<PlatformKey, { label: string; color: string }> = {
  ...SOURCE_META,
  chatgpt: { label: "ChatGPT", color: "#10A37F" },
  instagram: { label: "Instagram", color: "#C13584" },
  openrouter: { label: "OpenRouter", color: "#6467F2" },
  stt: { label: "Transcription", color: "#8B8681" },
};

/* ── What we hold, per artifact ──────────────────────────────────
   The difference between `transcript` and `video` is the difference between
   an artifact the engine can work on and one a person still has to sit
   through. Everything in the queue is gated on it. */

export type Holding =
  | "transcript"
  | "video"
  | "doc"
  | "chat"
  | "published"
  | "link"
  /* The connection itself — a mailbox, a role, a key. It belongs in the
     corpus because it is part of what was handed over, and it must NOT
     count as something the engine can read, or the readable total counts
     credentials as content. */
  | "access";

export const HOLDING_META: Record<Holding, { label: string; tone: Tone }> = {
  transcript: { label: "Text held", tone: "green" },
  video: { label: "Video only", tone: "amber" },
  doc: { label: "Document", tone: "blue" },
  chat: { label: "Reasoning chat", tone: "violet" },
  published: { label: "Published", tone: "navy" },
  link: { label: "Share link only", tone: "slate" },
  access: { label: "Connection", tone: "outline" },
};

export type CorpusItem = {
  id: string;
  platform: PlatformKey;
  title: string;
  held: Holding;
  when?: string;
  note?: string;
};

/* ── THE CORPUS ───────────────────────────────────────────────────
   Everything the 21 September handover put within reach, grouped by the
   platform it actually lives on rather than by what it is about. Grouping
   by platform is the useful axis here: it is how access is granted, how it
   breaks, and how the gaps read. */

export const CORPUS: CorpusItem[] = [
  /* Drive — by volume, the real archive. Client calls were moved here out
     of Zoom, which is why the video rows outnumber everything else. */
  { id: "dr-folder", platform: "drive", title: "WIA | Marketing › Results Social Proof › Call with Clients", held: "access", note: "The archive root. Client recordings are filed per client under it." },
  { id: "dr-voice", platform: "drive", title: "Founder voice guide", held: "doc", note: "The primary voice reference." },
  { id: "dr-voice-kb", platform: "drive", title: "Whitney Founder Voice Knowledge Base", held: "doc", note: "Second voice document — overlap with the guide not yet reconciled." },
  { id: "dr-wlf", platform: "drive", title: "Strategy from WLF", held: "doc", note: "The consultant strategy document named on the 16 September call." },
  { id: "dr-funk-rec", platform: "drive", title: "Funktastic Strategy Call — Meta Ads", held: "video", when: "source set" },
  { id: "dr-funk-tx", platform: "drive", title: "Funktastic Strategy Call — transcript", held: "transcript", note: "One of only two client-call transcripts in the handover." },
  { id: "dr-pr-jul", platform: "drive", title: "Press Record Strategy Call — Google Ads ROI", held: "video", note: "Best sales month ever. No transcript supplied." },
  { id: "dr-pr-aug", platform: "drive", title: "Press Record Co — back-to-back record months", held: "video", note: "August beat July. No transcript supplied." },
  { id: "dr-lyss", platform: "drive", title: "Miss Lyss Planning Check-in Call", held: "video", note: "Produced a published email, two Instagram posts and a case study." },
  { id: "dr-carroll", platform: "drive", title: "Carroll Hall Social Proof — Whitney's monthly Q&A", held: "video" },
  { id: "dr-carroll-tx", platform: "drive", title: "Carroll Hall — transcript", held: "transcript", note: "The second client-call transcript." },
  { id: "dr-lyss-cs", platform: "drive", title: "Miss Lyss case study", held: "doc", note: "The only finished case study in the set — the shape the engine should match." },
  { id: "dr-oh-0709", platform: "drive", title: "Google Ads Weekly Office Hours", held: "video", when: "9 Jul 2026" },
  { id: "dr-oh-0813", platform: "drive", title: "Google Ads Office Hours", held: "video", when: "13 Aug 2026" },
  { id: "dr-oh-0820", platform: "drive", title: "Google Ads Office Hours", held: "video", when: "20 Aug 2026" },
  { id: "dr-oh-0827", platform: "drive", title: "Google Ads Office Hours", held: "video", when: "27 Aug 2026" },
  { id: "dr-imp-0611", platform: "drive", title: "Impromptu Zoom Meeting", held: "video", when: "11 Jun 2026" },
  { id: "dr-imp-0820", platform: "drive", title: "Impromptu Zoom Meeting", held: "video", when: "20 Aug 2026" },
  { id: "dr-ws-uvp", platform: "drive", title: "Workshop · Defining your UVP", held: "video" },
  { id: "dr-ws-funnel", platform: "drive", title: "Workshop · How to audit your inquiry funnel", held: "video" },
  { id: "dr-ws-lp", platform: "drive", title: "Workshop · More examples of ads traffic landing pages", held: "video" },
  { id: "dr-ws-msg", platform: "drive", title: "Workshop · Messaging & Positioning Questionnaire", held: "video" },
  { id: "dr-ws-brand", platform: "drive", title: "Workshop · Building a brand that supports lead generation", held: "video", note: "With Emily Foster." },
  { id: "dr-ws-research", platform: "drive", title: "Workshop · Using market research to attract the right clients", held: "video" },

  /* Zoom — connected, and pointed at the smaller half of the archive. */
  { id: "zm-user", platform: "zoom", title: "ai@ user with a recordings + transcripts role", held: "access", note: "The connection itself. Created 21 September." },
  { id: "zm-workshops", platform: "zoom", title: "Workshop transcripts and summaries", held: "transcript", note: "Reachable by searching “workshop”. Per-workshop coverage not yet verified." },
  { id: "zm-client", platform: "zoom", title: "Client meetings", held: "link", note: "DELETED from Zoom to save storage. The archive copy in Drive is video." },

  /* Fathom — one public share link, no key. */
  { id: "fa-meta-0827", platform: "fathom", title: "Meta Ads Office Hours", held: "link", when: "27 Aug 2026", note: "A public share URL, not an API result. Meta office hours exist nowhere else." },
  { id: "fa-rest", platform: "fathom", title: "Internal meetings and remaining office hours", held: "link", note: "No API key supplied and no plan tier confirmed." },

  /* ChatGPT — the reasoning trail, which is the part no other source has. */
  { id: "gp-podcast", platform: "chatgpt", title: "Podcast reel scripts generation", held: "chat" },
  { id: "gp-uvp-reel", platform: "chatgpt", title: "UVP workshop → reel script generation", held: "chat" },
  { id: "gp-uvp-plan", platform: "chatgpt", title: "UVP workshop planning", held: "chat" },
  { id: "gp-uvp-email", platform: "chatgpt", title: "UVP workshop → marketing email", held: "chat" },
  { id: "gp-week914", platform: "chatgpt", title: "WIA marketing, week of 14 Sep 2026", held: "chat" },
  { id: "gp-lyss", platform: "chatgpt", title: "Miss Lyss → marketing email generation", held: "chat", note: "The same URL is also listed under Carroll Hall. One of the two labels is wrong." },
  { id: "gp-carroll-cs", platform: "chatgpt", title: "Carroll Hall → case study creation", held: "chat" },
  { id: "gp-funk", platform: "chatgpt", title: "Funktastic → content generation", held: "chat" },
  { id: "gp-research", platform: "chatgpt", title: "Market research workshop → content", held: "chat" },
  { id: "gp-research-mkt", platform: "chatgpt", title: "Market research workshop → marketing", held: "chat" },
  { id: "gp-account", platform: "chatgpt", title: "Account credentials", held: "access", note: "Shared via LastPass. The full data export, saved memories and project list are still outstanding." },

  /* HighLevel — six published emails, and the location id they expose. */
  { id: "hl-loc", platform: "highlevel", title: "Location id, read off the preview URLs", held: "access", note: "Xi40zxmRvW8Pbyk5DYHp. Closes the “location ids not yet recorded” gap in Source Coverage." },
  { id: "hl-lyss", platform: "highlevel", title: "Miss Lyss marketing email", held: "published" },
  { id: "hl-carroll-1", platform: "highlevel", title: "Carroll Hall marketing email #1", held: "published" },
  { id: "hl-carroll-2", platform: "highlevel", title: "Carroll Hall marketing email #2", held: "published" },
  { id: "hl-funk-1", platform: "highlevel", title: "Funktastic marketing email #1", held: "published" },
  { id: "hl-funk-2", platform: "highlevel", title: "Funktastic marketing email #2", held: "published" },
  { id: "hl-research", platform: "highlevel", title: "Market research workshop marketing email", held: "published" },

  /* Instagram — the approved voice at its most compressed. */
  { id: "ig-lyss-1", platform: "instagram", title: "Miss Lyss feed post", held: "published" },
  { id: "ig-lyss-2", platform: "instagram", title: "Miss Lyss reel", held: "published" },
  { id: "ig-funk-1", platform: "instagram", title: "Funktastic reel #1", held: "published" },
  { id: "ig-funk-2", platform: "instagram", title: "Funktastic reel #2", held: "published" },
  { id: "ig-research", platform: "instagram", title: "Market research workshop feed post", held: "published" },

  /* Slack and Gmail — the connection, not a corpus. */
  { id: "sl-channels", platform: "slack", title: "Client channels + #social-proof-and-results", held: "access", note: "Membership, not an app install. Reading it programmatically still needs a bot token." },
  { id: "gm-ai", platform: "gmail", title: "ai@weddingindustryads.com", held: "access", note: "Created and shared. The white-label identity everything else signs up through." },
  { id: "or-key", platform: "openrouter", title: "OpenRouter account and key", held: "access", note: "Created on the ai@ account. No spend cap recorded." },
];

export const CORPUS_ORDER: PlatformKey[] = [
  "drive",
  "zoom",
  "fathom",
  "chatgpt",
  "highlevel",
  "instagram",
  "slack",
  "gmail",
  "openrouter",
];

/** Sources the engine can actually read. Credentials and folder handles are
    excluded deliberately — counting a mailbox as a source inflates the one
    number the whole queue is limited by. */
export const READABLE = CORPUS.filter(
  (c) => c.held === "transcript" || c.held === "doc" || c.held === "chat",
).length;

export const UNREADABLE = CORPUS.filter((c) => c.held === "video").length;

export const CHAT_COUNT = CORPUS.filter((c) => c.held === "chat").length;

/* The single technical dependency the handover created and did not fill.
   Stated once, referenced by every blocked row rather than repeated — and
   DERIVED, because a hand-written "fourteen" drifted from the data the
   moment a recording was added to it. */
export const TRANSCRIPTION_GAP =
  `${UNREADABLE} of the recordings in Drive are video with no transcript beside them, and Zoom no longer holds the client calls they came from. Reading them needs a speech-to-text provider, which is not on the access list and not something OpenRouter covers for every model.`;

/* ── Publication clearance ────────────────────────────────────────
   Named-client permission was raised on 16 September and never answered.
   It is not academic here: four of the five published chains name the
   client outright, so the working default is already "named", and the
   engine needs to know whether that was a decision or a habit. */
export const CLEARANCE_QUESTION =
  "Four of the five published chains name the client. Whether that is a standing permission or a per-post judgement is still open — until it is answered the engine drafts named and flags it.";

/* ── CTA library ──────────────────────────────────────────────────
   MC-02's most specific requirement, and the one the old screen buried
   inside the draft text: "it doesn't have to come up with what the CTA is
   going to be — it can ask me." So the CTA is a field a person sets, the
   engine never picks one, and staging is blocked while it is empty.

   `destination` is empty where the handover did not supply the URL. That is
   not a placeholder to fill in later — it is the outstanding ask. */

export type CtaOption = {
  id: string;
  label: string;
  track: string;
  destination: string;
};

export const CTA_OPTIONS: CtaOption[] = [
  {
    id: "vault",
    label: "Watch the full teardown in The Vault",
    track: "Accelerator members",
    destination: "",
  },
  {
    id: "accelerator",
    label: "Apply for the Google Search / Meta Ads Accelerator",
    track: "Accelerators",
    destination: "",
  },
  {
    id: "elevate",
    label: "Join the Elevate waitlist",
    track: "Elevate — done-for-you",
    destination: "",
  },
  {
    id: "reply",
    label: "Reply and tell me your biggest challenge",
    track: "Engagement — no destination needed",
    destination: "the inbox",
  },
];

/* ── Published precedent ──────────────────────────────────────────
   The most valuable thing in the handover, and the thing the old screen had
   no place for. Each chain is a complete worked example: a source, the
   ChatGPT conversation that shaped it, and what actually went out.

   ONE OF THEM IS A BENCHMARK, NOT AN EXAMPLE. Funktastic is the only chain
   where the source TRANSCRIPT and the published output both survive, which
   makes it the only case where the engine can be run against a source whose
   correct answer is already known. Every other chain teaches voice; this one
   measures accuracy. */

export type PrecedentChain = {
  id: string;
  title: string;
  client: string;
  source: { platform: PlatformKey; label: string; held: Holding }[];
  reasoning: { label: string }[];
  published: { platform: PlatformKey; label: string }[];
  /** What this chain is good for, in one line. */
  teaches: string;
  /** True on the one chain that can be scored rather than imitated. */
  benchmark?: boolean;
  /** Anything about the chain that does not hold up. */
  caveat?: string;
};

export const PRECEDENT: PrecedentChain[] = [
  {
    id: "pc-funktastic",
    title: "“It felt like fate” — the client who kept seeing them on Instagram",
    client: "Funktastic",
    source: [
      { platform: "drive", label: "Strategy call recording", held: "video" },
      { platform: "drive", label: "Strategy call transcript", held: "transcript" },
    ],
    reasoning: [{ label: "Content generation chat" }],
    published: [
      { platform: "instagram", label: "Reel #1" },
      { platform: "instagram", label: "Reel #2" },
      { platform: "highlevel", label: "Marketing email #1" },
      { platform: "highlevel", label: "Marketing email #2" },
    ],
    teaches:
      "Source text in, four published assets out — the only chain where both ends are readable, so the engine can be scored against it instead of imitating it.",
    benchmark: true,
  },
  {
    id: "pc-lyss",
    title: "Planning check-in → the full five-asset spread",
    client: "Miss Lyss",
    source: [{ platform: "drive", label: "Planning check-in recording", held: "video" }],
    reasoning: [{ label: "Marketing email generation chat" }],
    published: [
      { platform: "highlevel", label: "Marketing email" },
      { platform: "instagram", label: "Feed post" },
      { platform: "instagram", label: "Reel" },
      { platform: "drive", label: "Case study" },
    ],
    teaches:
      "The widest spread from one source, and the only finished case study — the shape MC-04 has to hit.",
    caveat: "Source is video with no transcript, so the chain cannot be replayed from its own input.",
  },
  {
    id: "pc-carroll",
    title: "Monthly Q&A → two marketing emails and a case study",
    client: "Carroll Hall",
    source: [
      { platform: "drive", label: "Social proof recording", held: "video" },
      { platform: "drive", label: "Transcript", held: "transcript" },
    ],
    reasoning: [
      { label: "Marketing generation chat" },
      { label: "Case study creation chat" },
    ],
    published: [
      { platform: "highlevel", label: "Marketing email #1" },
      { platform: "highlevel", label: "Marketing email #2" },
    ],
    teaches:
      "Two emails from one session without the second reading as a repeat — the redundancy problem, already solved by hand.",
    caveat:
      "Its marketing chat link is identical to the Miss Lyss one. One of the two labels is wrong and the real chat may be missing.",
  },
  {
    id: "pc-research",
    title: "Market research workshop → email and feed post",
    client: "The Vault",
    source: [{ platform: "drive", label: "Workshop recording", held: "video" }],
    reasoning: [
      { label: "Workshop content chat" },
      { label: "Marketing generation chat" },
    ],
    published: [
      { platform: "highlevel", label: "Marketing email" },
      { platform: "instagram", label: "Feed post" },
    ],
    teaches:
      "A workshop, not a client call — the teaching register, and a CTA pointed at the Accelerators rather than Elevate.",
  },
  {
    id: "pc-uvp",
    title: "Defining your UVP — planning, script and email",
    client: "The Vault",
    source: [{ platform: "drive", label: "Workshop recording", held: "video" }],
    reasoning: [
      { label: "Workshop planning chat" },
      { label: "Reel script generation chat" },
      { label: "Marketing email generation chat" },
    ],
    published: [],
    teaches:
      "The only chain that shows the planning step before the content — how a topic is chosen, not just how it is written up.",
    caveat: "No published artifact supplied, so the end of this chain is unverified.",
  },
];

/* ── Access coverage ──────────────────────────────────────────────
   What the handover granted, what that reaches, and what it does not. This
   is the same audit the Source Coverage screen runs for the whole hub,
   narrowed to the things the Atelier depends on — because a content
   engine blocked on transcription is not a content problem. */

export type AccessState = "connected" | "partial" | "missing";

export const ACCESS_META: Record<AccessState, { label: string; tone: Tone }> = {
  connected: { label: "Connected", tone: "green" },
  partial: { label: "Partial", tone: "amber" },
  missing: { label: "Not granted", tone: "red" },
};

export type CoverageRow = {
  platform: PlatformKey;
  state: AccessState;
  granted: string;
  reaches: string;
  gap?: string;
};

export const COVERAGE: CoverageRow[] = [
  {
    platform: "gmail",
    state: "connected",
    granted: "ai@weddingindustryads.com created, credentials in LastPass",
    reaches: "The white-label identity every other signup and verification code runs through.",
  },
  {
    platform: "openrouter",
    state: "connected",
    granted: "Account on the ai@ address, key shared",
    reaches: "Every text model the drafting steps need, behind one key.",
    gap: "No spend cap recorded, and no transcription model selected — see the Drive row.",
  },
  {
    platform: "drive",
    state: "connected",
    granted: "Shared drive plus the Results Social Proof folders",
    reaches: "Both voice documents, the WLF strategy, six workshops, four office hours and every archived client call.",
    gap: `${UNREADABLE} of those are video. Without a speech-to-text step the engine reads the folder names and nothing else.`,
  },
  {
    platform: "zoom",
    state: "partial",
    granted: "ai@ user with a recordings and transcripts role",
    reaches: "Workshop transcripts and summaries, searchable by “workshop”.",
    gap: "Client meetings are deleted from Zoom by policy, so the calls carrying the results are not here. Per-workshop transcript coverage is also unverified.",
  },
  {
    platform: "fathom",
    state: "partial",
    granted: "One public share link — Meta Ads Office Hours, 27 August",
    reaches: "That single session, by URL.",
    gap: "No API key and no plan tier. Jacqueline's Meta office hours run on Fathom and exist nowhere else.",
  },
  {
    platform: "chatgpt",
    state: "partial",
    granted: "Account credentials in LastPass, plus eleven shared chat links",
    reaches: "The reasoning behind five published chains — how a source became an angle.",
    gap: "The account data export, saved memories and the Projects / Custom GPT list are still outstanding. Shared links carry no memory.",
  },
  {
    platform: "slack",
    state: "partial",
    granted: "Added to the client channels and #social-proof-and-results",
    reaches: "A person can read them.",
    gap: "Membership is not an integration. Reading history, pulling the screenshots or watching for a flag emoji needs an app install with a bot token.",
  },
  {
    platform: "highlevel",
    state: "missing",
    granted: "Six email preview URLs, which expose the location id",
    reaches: "Six finished emails as voice reference, and one confirmed location id.",
    gap: "No private integration token, so nothing can be read at volume or drafted back into the account.",
  },
  {
    platform: "instagram",
    state: "missing",
    granted: "Five public post URLs",
    reaches: "Five captions, by hand.",
    gap: "No Business Suite access and no export, so the approved-caption corpus stops at five.",
  },
  {
    platform: "stt",
    state: "missing",
    granted: "Nothing — this was not on the access list",
    reaches: "—",
    gap: TRANSCRIPTION_GAP,
  },
];

/* ── The queue ────────────────────────────────────────────────────
   Moments awaiting Whitney. Not a list of ideas: each row states what we
   hold, and the state follows from that rather than from how interesting
   the moment is.

     drafted   a transcript is held and a pack exists
     ready     a transcript is held, nothing drafted yet
     blocked   a recording exists and cannot be read

   `claimSourced` is the same honesty flag the old `voiceNote.sourced`
   carried. A claim paraphrased in the handover note is not a quote, and the
   card says which it is. */

export type QueueState = "drafted" | "ready" | "blocked";

export const QUEUE_META: Record<QueueState, { label: string; tone: Tone }> = {
  drafted: { label: "Pack drafted", tone: "blue" },
  ready: { label: "Ready to draft", tone: "green" },
  blocked: { label: "Blocked", tone: "amber" },
};

export type Moment = {
  id: string;
  client: string;
  meeting: string;
  kind: "Workshop" | "Client call" | "Office hours" | "Social proof";
  when: string;
  state: QueueState;
  /** Where the source sits, in the order it would be reached. */
  origin: { platform: PlatformKey; label: string; held: Holding }[];
  /** The line this moment turns on. */
  claim: string;
  /** Timestamp, where a transcript backs the claim. */
  ts?: string;
  /** False when the claim is paraphrase rather than quotation. */
  claimSourced: boolean;
  signals: string[];
  /** Which offer this moment naturally points at, before Whitney decides. */
  suggests: string;
  /** Present on every blocked row: the reason, not a status word. */
  blockedBy?: string;
};

export const MOMENTS: Moment[] = [
  {
    id: "vault-landing-pages",
    client: "The Vault",
    meeting: "Real-World Ads Traffic Landing Page Examples",
    kind: "Workshop",
    when: "Session held · transcript in workspace",
    state: "drafted",
    origin: [
      { platform: "zoom", label: "Workshop transcript", held: "transcript" },
      { platform: "drive", label: "Session recording", held: "video" },
    ],
    claim:
      "“There’s not like a hard and fast rule as to what your conversion rate should be.”",
    ts: "10:21",
    claimSourced: true,
    signals: ["Teaching moment", "Benchmark data", "Marketing insight"],
    suggests: "The Vault · Accelerator members",
  },
  {
    id: "carroll-hall-qa",
    client: "Carroll Hall",
    meeting: "Social proof — Whitney's monthly Q&A",
    kind: "Social proof",
    when: "Recording and transcript in Drive",
    state: "ready",
    origin: [
      { platform: "drive", label: "Transcript", held: "transcript" },
      { platform: "drive", label: "Recording", held: "video" },
    ],
    claim:
      "Two marketing emails already went out from this session. The transcript is held, so a reel and carousel can be drafted from the same source.",
    claimSourced: true,
    signals: ["Client voice", "Already proven", "Unworked formats"],
    suggests: "Elevate · done-for-you",
  },
  {
    id: "press-record-july",
    client: "Press Record",
    meeting: "Strategy call — Google Ads ROI",
    kind: "Client call",
    when: "Recording in Drive",
    state: "blocked",
    origin: [{ platform: "drive", label: "Recording", held: "video" }],
    claim:
      "Steve shared that July was their best sales month ever, crediting Google Ads performance for the result.",
    claimSourced: false,
    signals: ["Record month", "Google Ads", "Named result"],
    suggests: "Elevate · done-for-you",
    blockedBy:
      "Video only. The claim above is the handover's own paraphrase — there is no transcript to quote Steve from, and a result post that misquotes the client is worse than no post.",
  },
  {
    id: "press-record-august",
    client: "Press Record Co",
    meeting: "Strategy call — back-to-back record months",
    kind: "Client call",
    when: "Recording in Drive",
    state: "blocked",
    origin: [{ platform: "drive", label: "Recording", held: "video" }],
    claim: "August beat July. Two consecutive record-breaking months driven by Google Ads.",
    claimSourced: false,
    signals: ["Record month", "Sequel to July", "Google Ads"],
    suggests: "Elevate · done-for-you",
    blockedBy:
      "Video only. Pairs with the July call as a two-part story, which is the strongest sequence in the corpus and the one we can read the least of.",
  },
  {
    id: "google-oh-0827",
    client: "Accelerator members",
    meeting: "Google Ads Office Hours",
    kind: "Office hours",
    when: "27 Aug 2026",
    state: "blocked",
    origin: [{ platform: "drive", label: "Recording", held: "video" }],
    claim:
      "The most recent of four Google Ads office hours in the archive. Member questions are the closest thing in the corpus to an audience research set.",
    claimSourced: false,
    signals: ["Teaching moment", "Audience questions", "Recurring format"],
    suggests: "Accelerators",
    blockedBy:
      "Video only, like the other three Google office hours. Carmen hosts these on Zoom, so a transcript should exist upstream of the Drive copy.",
  },
  {
    id: "meta-oh-0827",
    client: "Accelerator members",
    meeting: "Meta Ads Office Hours",
    kind: "Office hours",
    when: "27 Aug 2026",
    state: "blocked",
    origin: [{ platform: "fathom", label: "Public share link", held: "link" }],
    claim:
      "Jacqueline's Meta office hours. The only session in the handover that lives on Fathom rather than Drive or Zoom.",
    claimSourced: false,
    signals: ["Teaching moment", "Meta Ads", "Single source"],
    suggests: "Accelerators",
    blockedBy:
      "A share URL is not an integration. Without a Fathom key this session is reachable by hand and the rest of the Meta office hours are not reachable at all.",
  },
];

/* ── Candidate moments inside the one transcript we can read ───────
   MC-01. Unchanged from the previous model except for where they live:
   every quote is cited by the timestamp it already carries in the case
   study, and nothing was invented to lengthen the list. */

export type Candidate = {
  id: string;
  ts: string;
  quote: string;
  why: string;
  /** Set on exactly one: the moment the pack was drafted from. */
  isDrafted?: boolean;
};

export const CANDIDATES: Record<string, Candidate[]> = {
  "vault-landing-pages": [
    {
      id: "cand-1021",
      ts: "10:21",
      quote:
        "“There’s not like a hard and fast rule as to what your conversion rate should be.”",
      why: "A benchmark question WIA is asked constantly, answered against real accounts.",
      isDrafted: true,
    },
    {
      id: "cand-0211",
      ts: "02:11",
      quote: "“A high volume of lower quality leads.”",
      why: "The quality-over-quantity position, in one line. Overlaps heavily with 10:21.",
    },
    {
      id: "cand-1924",
      ts: "19:24",
      quote: "“Live music sound without the live band price tag.”",
      why: "A positioning line from a client's own page — strong copy, but it is THEIR line, not WIA's insight.",
    },
    {
      id: "cand-2316",
      ts: "23:16",
      quote:
        "A conversion-built website outperformed expectations, so it was not replaced with a landing page.",
      why: "Argues against WIA's own default. Interesting, and needs Whitney's judgement before it is public.",
    },
  ],
};

/* ── The steer ────────────────────────────────────────────────────
   MC-02. Still illustrative: no voice recording or transcription of one
   exists anywhere in the workspace, including in the 21 September handover,
   so `sourced` stays false and the screen says so. */

export type Steer = {
  captured: string;
  transcript: string;
  applied: string[];
  sourced: boolean;
};

export const STEERS: Record<string, Steer> = {
  "vault-landing-pages": {
    captured: "Slack audio clip · #marketing (proposed surface)",
    sourced: false,
    transcript:
      "Use the landing page session for this one. The angle I want is that the conversion rate on its own is a useless number — I keep getting asked what a good rate is and the honest answer is that it depends where the click came from. Lead on the two venues where the lower-converting page got the cheaper lead, because that is the part nobody says out loud. Keep it teaching, not selling. And do not put any client name or any recognisable page on screen — blur the analytics before the numbers are readable.",
    applied: [
      "Angle set to “the rate is not the scoreboard” rather than a benchmark round-up",
      "Texas vs California comparison leads the body in every format",
      "Teaching register, no offer pitch — CTA points at The Vault only",
      "Client names, page branding and legible analytics excluded in the production notes",
    ],
  },
};

/* ── The production drafts ────────────────────────────────────────
   Preserved verbatim from the previous model. Every figure is lifted from
   the session recording and the case study keeps its timestamps, so any
   number can be checked against what was actually said. The recording is a
   paid members' workshop that walks client analytics on screen, which is
   why the case study and the reels carry handling notes rather than reading
   as publishable copy. */

export const BODIES: Record<string, Record<string, string>> = {
  "vault-landing-pages": {
    reel: "REEL SCRIPT — 75 sec — talking head + screen recording\nSource: The Vault · Real-World Ads Traffic Landing Page Examples · 10:21\n\nHOOK (0:00–0:06) — to camera\n“A page converting at 5% and a page converting at 1% can both be working. Let me show you why.”\n\nALT HOOKS — pick on the day\n• “Everyone asks me what a good landing page conversion rate is. Here is the real range, from real accounts.”\n• “We opened the back end on six wedding businesses. The best page was not the highest-converting one.”\n\nSETUP (0:06–0:18) — to camera\nSix real wedding businesses. Google and Meta traffic pointed at long-form landing pages. I went into the back end on every one of them, and I want to give you the honest spread — because the percentage on its own tells you almost nothing.\n\nBODY 1 — THE RANGE (0:18–0:34)\nON SCREEN: 1%–6%\nThese pages land between 1% and 6%. Where you fall inside that depends on where the click came from.\nON SCREEN: META · curiosity · 1–3%\nON SCREEN: GOOGLE · high intent · 3–6%\nMeta clicks are curiosity-driven — someone was scrolling. Google clicks are high intent — someone was searching. Same page, two different numbers, and neither one is wrong.\n\nBODY 2 — THE COMPARISON (0:34–0:54)\nB-ROLL: the two venue pages scrolling side by side\nTwo venues. Similar spend across both platforms. Similar inquiry volume for the month.\nThe Texas venue converted just under 5% — 40 opt-ins.\nThe California venue pulled more traffic, converted lower, and produced a slightly lower cost per lead.\nON SCREEN: lower rate. cheaper leads.\nSo which page is better? The one that lost on percentage.\n\nBODY 3 — WHAT THE PAGE IS ASKING FOR (0:54–1:08)\nB-ROLL: the “schedule a tour” button\nOne of these venues does not ask people to inquire. It asks them to schedule a tour. Its opt-in rate is lower — and it should be. It is asking for more. Fewer hands go up, and the ones that do already know they want to walk the property.\nA higher barrier buys you a better-qualified lead. That is a trade, not a failure.\n\nCLOSE (1:08–1:15) — to camera\nA low-barrier form will always give you more leads. It will not give you better ones. So stop grading the percentage. Grade what the page costs you per lead worth having.\n\nCTA\nFull teardown of all six pages — including the two that need work — is in The Vault.\n\nPRODUCTION NOTES\n• Blur every analytics screen before the figures are legible. The benchmark is quotable; the accounts are not.\n• Hold the 1–6% card long enough to screenshot. That frame is the save.\n• No client name and no recognisable page branding on screen at any point.\n• Captions burned in — this plays on mute.",
    carousel: "CAROUSEL — 10 slides — 4:5\nSource: The Vault · Real-World Ads Traffic Landing Page Examples · 10:21\n\nSLIDE 1 — cover\nYour landing page converts at 2%.\nGood or bad?\n[small] Six real wedding businesses. Real back-end numbers.\n\nSLIDE 2\nNeither — until you know where the traffic came from.\nThe honest range on ads traffic landing pages: 1% to 6%.\n\nSLIDE 3\nMeta clicks are curiosity. → 1–3%\nGoogle clicks are intent. → 3–6%\nSame page. Different number. Neither is broken.\n\nSLIDE 4 — the comparison\nTexas venue: just under 5%. 40 opt-ins in a month.\nCalifornia venue: lower rate — and a cheaper lead.\nSimilar spend. Similar inquiries.\n\nSLIDE 5\nSo the “worse” page won.\nRate is a ratio. Cost per qualified lead is a business number. Only one of those pays you.\n\nSLIDE 6 — the barrier\nOne venue asks for a tour, not an inquiry.\nIts rate is lower by design. It asks for more, so fewer hands go up — and the ones that do already want to walk the property.\n\nSLIDE 7\nA higher barrier is a trade, not a failure.\nLow-barrier forms give you volume. Volume is not the goal.\n\nSLIDE 8 — what all six pages do\nTestimonial in the hero · location legible immediately · “what sets us apart” early · photography throughout · pricing and inclusions deliberately far down · owner story · self-qualifying section · FAQs\n\nSLIDE 9\nWhy pricing sits low on the page:\nEmotional buy-in first, numbers second. By the time someone reaches the rates, they already want it to work.\n\nSLIDE 10 — CTA\nThe only question worth asking:\nwhat is this page costing me per lead worth having?\n[small] Full six-page teardown in The Vault.\n\nDESIGN NOTES\n• Slides 4 and 5 are the carry — set them in the largest type in the deck.\n• Slide 8 is dense on purpose; it is the screenshot people save.\n• Percentages as numerals, never spelled out. No screenshots of client pages.\n\nPOST CAPTION — see the Caption tab.",
    email: "SUBJECT — primary\nIs 2% a good landing page conversion rate?\n\nSUBJECT — alternates for the A/B\n• The “worse” landing page won\n• What six wedding businesses actually convert at\n• Your conversion rate is not the number that matters\n\nPREVIEW TEXT\nSix real accounts, the honest range, and the page that lost on percentage.\n\nBODY\n\nIt depends on where the traffic came from — and on what the page is asking for.\n\nWe went into the back end on six wedding businesses running ads traffic to long-form landing pages. The honest range is 1% to 6%.\n\nMeta traffic clicks out of curiosity, so it lands around 1–3%. Google traffic is high intent, so it lands around 3–6%. Same page, two different numbers.\n\nHere is the part worth sitting with.\n\nTwo venues. Similar spend across Google and Meta. Similar inquiry volume for the month. The Texas venue converted just under 5% — 40 opt-ins. The California venue pulled more traffic, converted lower, and its leads came in slightly cheaper.\n\nThe lower-converting page was the better buy.\n\nA third venue asks people to schedule a tour rather than inquire. Its opt-in rate is lower, and that is exactly what should happen: it asks for more, so fewer hands go up — and the ones that do already know they want to see the place. A higher barrier buys a better-qualified inquiry. That is a trade you might want to make on purpose.\n\nThis is why we do not chase the ratio. A simple page with a short form will generate plenty of leads, and most of them will not be yours. We would rather have a long page that lets people self-qualify and sends you fewer, better inquiries.\n\nThree things every one of the six pages does, if you want to audit your own this week:\n\n1. The testimonial sits in the hero, above anything about the business.\n2. The location is legible in the first screen — market first, story second.\n3. Pricing and inclusions sit deliberately far down the page, so the emotional buy-in lands before the numbers do.\n\nThere is no hard and fast rule for what your rate should be. It moves with your market, your platform mix, and what you are asking people to do. Look at the leads.\n\nCTA BUTTON\nWatch the full teardown →\n\nP.S.\nTwo of the six pages have real problems, and we say so on the recording — including one where the differentiators are a list of line items where a story should be. That section is worth your time even if you skip the numbers.\n\n— Whitney",
    caption: "CAPTION — feed post / carousel\nSource: The Vault · Real-World Ads Traffic Landing Page Examples · 10:21\n\nHOOK LINE\nIs 2% a good conversion rate?\n\nBODY\nNobody can answer that without knowing where the click came from.\n\nMeta traffic is curiosity — 1–3%. Google traffic is intent — 3–6%. Across six real wedding businesses, the whole honest range is 1% to 6%.\n\nBut here is the part that gets left out of every “benchmark” post.\n\nTwo venues. Similar ad spend. Similar inquiries for the month. One converted just under 5%. The other converted lower — and got cheaper leads.\n\nThe lower percentage was the better page.\n\nAnd a page that asks people to book a tour instead of just inquiring will always convert lower. It is asking for more. Fewer hands go up, and the ones that do are already halfway to a booking.\n\nA low-barrier form will give you more leads. It will not give you better ones. Quality over quantity — that is the whole reason we build long pages that let people self-qualify.\n\nSo the question was never “what is my conversion rate.” It is what this page costs you per lead worth having.\n\nCTA\nFull six-page teardown is in The Vault → link in bio\n\nSHORT VARIANT — Stories / Threads\nTwo venues, similar spend, similar inquiries. One converted just under 5%. The other converted lower and got cheaper leads. The “worse” page won. Stop grading the percentage.\n\nHASHTAGS\n#weddingvenue #venuemarketing #weddingpros #weddingindustry #weddingvenueowner #googleads #metaads #leadgeneration #weddingbusiness #venueowner\n\nALT TEXT\nText graphic reading “Your landing page converts at 2% — good or bad?” followed by conversion benchmarks: Meta traffic 1–3%, Google traffic 3–6%, overall range 1% to 6%.",
    case_study: "SOURCE\nThe Vault — Real-World Ads Traffic Landing Page Examples (24:44 session). Six live pages walked against their own back-end numbers, plus one website used as a control.\n\nMETHOD\nEvery page reviewed here is receiving paid traffic only — Google Ads and Meta, no organic, no email. Rates are the page’s own opt-in rate over roughly the trailing month, read from the account back end during the session. Two pages are under a month old and are flagged as such.\n\nBENCHMARK\nAds traffic landing pages: 1–6%.\nMeta only, curiosity-driven click: 1–3%.\nGoogle, high intent: 3–6%.\nFluctuates by market and by business — “there’s not like a hard and fast rule as to what your conversion rate should be” (10:21).\n\nTHE SIX PAGES\n\n1 · Texas Hill Country venue — just under 5%, 40 opt-ins in the month (07:19)\nFamily operated, outside San Antonio. Glowing testimonial in the hero with the inquiry link beside it. Differentiators carried by specifics their couples actually repeat back — outdoor ceremony sites, indoor space, “dancing under the stars.” No on-site accommodation, so the nearby-lodging question is turned into another CTA: inquire and we will send you the options. Rental-fee range published, full pricing withheld.\n\n2 · California Redwoods estate — more traffic, lower rate, slightly LOWER cost per lead (09:40)\nPrivate estate on 80 forested acres, on-site lodging. Same formula as the Texas page, one deliberate difference: inclusions are grouped into two digestible sections — property access, then design, rentals, planning and vendor coordination — rather than a long line-item list, because this is an all-inclusive experience rather than a venue-only rental. On similar spend it produced similar monthly inquiries at a slightly lower cost per lead. The rate lost; the economics won.\n\n3 · Davis and Gray, North Texas — lower opt-in, and two named problems (11:03)\nRecently launched. The CTA asks people to schedule a tour rather than inquire — a higher barrier, and the lower opt-in rate is the expected cost of it. Pricing fully broken out, venue-only against all-inclusive, ahead of the tour. Flagged on the recording as areas of opportunity: the North Texas location needs to be more prominent, and “why couples choose Davis and Gray” is a stack of line items where storytelling belongs — what the day will feel like, from the first tour through to the wedding itself.\n\n4 · Texas ranch — over 4% (15:40)\nLeads on exceptional service and on wedding packages that include the on-site lodging. Accommodation described in detail because it carries the package. Full team introduced. Runs the formula straight, with consistent CTAs throughout.\n\n5 · Chicago band — just over 1% (18:33)\nTwo weeks live and mid-rebrand, so read it as early signal, not a verdict. Two things worth copying: a scrolling awards banner, and video on the page — for a band it is the product, and the same logic applies to a venue with a virtual tour, provided page speed survives it. Packages are described by who they are for before what is in them.\n\n6 · DJ-hybrid sister brand — just over 3% (18:41)\nAlso new, same rebrand. Emotional hero statement about what the couple’s wedding deserves rather than a description of the service. The positioning line does the work: “live music sound without the live band price tag” (19:24).\n\nTHE FORMULA ALL SIX RUN\nTestimonial in the hero, with the location legible in the first screen · differentiators next, drawn from real positioning work rather than adjectives · “what sets us apart” early · photography throughout · inclusions and pricing deliberately far down the page, so emotional buy-in lands first · owner story, usually the husband-and-wife team · self-qualifying section · FAQs, with the ones that do not deserve page space answered here.\n\nWHAT THE NUMBERS ACTUALLY SAY\nRate is not the scoreboard. California lost on rate and won on cost per lead. Davis and Gray converts lower because it asks for a tour — a higher barrier buying a better-qualified inquiry. Low-barrier forms produce “a high volume of lower quality leads” (02:11), which is why the house position is quality over quantity and why these pages are long enough for people to disqualify themselves.\n\nTHE CONTROL — A WEBSITE INSTEAD OF A LANDING PAGE\nOne business pointed Google Ads at a conversion-built website the day it launched, and it performed from the start. Designed by Emily Foster, not by us. It behaves like the landing pages where it counts: logo and wide photograph in the hero, what it is and where it is, CTA early. Pricing is public. “Book a tour” routes through the same inquiry form first — inquire, then schedule. Best guess on the recording is that a dedicated long-form page would convert higher, but the site is bringing in qualified leads that turn into sales, so it is not being replaced (23:16).\n\nWHEN A WEBSITE IS ENOUGH — the qualifying questions\nIs it genuinely built for conversion, or just built? Does it push the next step? How recently was it updated? Did you DIY it, or work with a professional? This client had just invested in a site and wanted more eyes on it — that is the case where pointing ads at the website is the right call.\n\nNOTE\nFigures are client back-end data captured during a paid members’ session. Internal review only — not cleared for publication, and the per-client rates should not be paired with the location details in anything outward-facing.",
  },
};

/* ── The pack ─────────────────────────────────────────────────────
   THE SPEC IS WHITNEY'S, NOT OURS. Stated on 16 September: "one marketing
   email, three real scripts, and one carousel … and of course captions to
   go along with all of that." The previous model shipped one draft per
   format behind five tabs, which is a different deliverable — it gave her a
   single reel to accept or reject where she asked for three to choose
   between on the day.

   THE LEAD ASSET IS A CHOICE, NOT A CONSTANT. The old screen hard-wired the
   reel as the thing that unlocks everything else. Her actual process: "I
   usually have it take the source content and either have it give me a
   script for reels first, or we work on a marketing email first." So either
   can lead, and whichever she approves is what the rest derive from.

   The three reel angles are not three rewrites of one script. Each takes a
   different claim from the same session — the alternate hooks the original
   draft already listed as "pick on the day" are now written out, because a
   hook without a script behind it is not a choice between three things. */

export type AssetKind = "reel" | "carousel" | "email" | "caption" | "case_study";

export const ASSET_META: Record<AssetKind, { label: string; tone: Tone }> = {
  reel: { label: "Reel script", tone: "blue" },
  carousel: { label: "Carousel", tone: "violet" },
  email: { label: "Marketing email", tone: "green" },
  caption: { label: "Caption", tone: "slate" },
  case_study: { label: "Case study", tone: "amber" },
};

export type PackAsset = {
  id: string;
  kind: AssetKind;
  label: string;
  /** Reels only — the claim this one is built on. */
  angle?: string;
  body: string;
  /** True on the two formats Whitney actually starts from. */
  canLead: boolean;
  /** Why this one cannot leave without a check, where it applies. */
  handling?: string;
};

export const PACK_SPEC =
  "1 marketing email · 3 reel scripts · 1 carousel · captions for all of it";

const REEL_B = "REEL SCRIPT — 60 sec — talking head + screen recording\nANGLE B · the benchmark round-up\nSource: The Vault · Real-World Ads Traffic Landing Page Examples · 10:21\n\nHOOK (0:00–0:05) — to camera\n“Everyone asks me what a good landing page conversion rate is. Here is the real range, from real accounts.”\n\nSETUP (0:05–0:16) — to camera\nNot a survey. Not an industry report. Six wedding businesses, all running paid traffic to long-form landing pages, and I went into the back end on every one of them.\n\nBODY 1 — THE SPREAD (0:16–0:36)\nON SCREEN: 1% — 6%\nThat is the whole honest range. And before you decide where you sit in it, you need to know which half of your traffic you are looking at.\nON SCREEN: META · 1–3%\nMeta clicks are curiosity. Nobody woke up looking for a venue — they were scrolling.\nON SCREEN: GOOGLE · 3–6%\nGoogle clicks are intent. Somebody typed the thing they wanted.\nSame page, two different numbers, and neither of them is broken.\n\nBODY 2 — THE PAGES AT EACH END (0:36–0:52)\nB-ROLL: pages scrolling, analytics blurred\nAt the top of the range, a Texas venue just under 5% — forty opt-ins in a month.\nIn the middle, a Texas ranch over 4%, running the formula straight.\nAt the bottom, a band two weeks into a rebrand at just over 1% — which is early signal, not a verdict, and I would not grade it yet.\n\nBODY 3 — WHAT THE RANGE DOES NOT TELL YOU (0:52–1:04) — to camera\nHere is the catch. One of the six converted LOWER than the venue above it and produced a cheaper lead. So if you take one number out of this, take this one: the range tells you whether your page is broken. It does not tell you whether it is working.\n\nCLOSE (1:04–1:12) — to camera\nThere is no hard and fast rule for what your rate should be. It moves with your market, your platform mix, and what you are asking people to do.\n\nCTA\nAll six pages, walked end to end, are in The Vault.\n\nPRODUCTION NOTES\n• The 1–6% card is the save — hold it long enough to screenshot.\n• Blur every analytics screen before the figures are legible.\n• No client name and no recognisable page branding at any point.\n• Captions burned in.";

const REEL_C = "REEL SCRIPT — 55 sec — talking head\nANGLE C · the page that asks for more\nSource: The Vault · Real-World Ads Traffic Landing Page Examples · 11:03\n\nHOOK (0:00–0:06) — to camera\n“One of these venues has a worse conversion rate on purpose. It is the smartest thing on the page.”\n\nSETUP (0:06–0:18) — to camera\nMost landing pages ask you to inquire. Low barrier, one form, plenty of hands go up. This one asks you to schedule a tour. Higher barrier. Fewer hands. And a lower opt-in rate, every single month.\n\nBODY 1 — THE TRADE (0:18–0:36) — to camera\nThat is not a page problem. That is a page asking for more, and getting fewer, better people.\nON SCREEN: low barrier → more leads\nON SCREEN: high barrier → better leads\nSomebody who books a tour has already decided they want to walk your property. Somebody who fills in a form has decided they want an email. Those are not the same person, and they do not close at the same rate.\n\nBODY 2 — WHEN NOT TO DO IT (0:36–0:48) — to camera\nThis only works if the rest of the page has earned it. The one I am describing publishes its pricing in full — venue-only against all-inclusive — before it ever asks for the tour. It answers the expensive question first. If your page asks for a tour before it has told anyone what you cost, you will not get fewer better leads. You will get nothing.\n\nCLOSE (0:48–0:55) — to camera\nSo stop optimising the percentage. Decide what you want the page to ask for, then let the number land where it lands.\n\nCTA\nThe full teardown — including two pages that need work — is in The Vault.\n\nPRODUCTION NOTES\n• No analytics on screen in this one at all. The claim is structural, not numerical.\n• Do not name the venue: the recording flags real areas of opportunity on this page.\n• Captions burned in.";

export const PACK: Record<string, PackAsset[]> = {
  "vault-landing-pages": [
    {
      id: "reel-a",
      kind: "reel",
      label: "Reel script A",
      angle: "The rate is not the scoreboard",
      body: BODIES["vault-landing-pages"].reel,
      canLead: true,
      handling: "Analytics on screen — blur before the figures are legible.",
    },
    {
      id: "reel-b",
      kind: "reel",
      label: "Reel script B",
      angle: "The benchmark round-up",
      body: REEL_B,
      canLead: true,
      handling: "Analytics on screen — blur before the figures are legible.",
    },
    {
      id: "reel-c",
      kind: "reel",
      label: "Reel script C",
      angle: "The page that asks for more",
      body: REEL_C,
      canLead: true,
      handling: "Names a page the recording criticises. Client must not be identifiable.",
    },
    {
      id: "email",
      kind: "email",
      label: "Marketing email",
      body: BODIES["vault-landing-pages"].email,
      canLead: true,
    },
    {
      id: "carousel",
      kind: "carousel",
      label: "Carousel",
      body: BODIES["vault-landing-pages"].carousel,
      canLead: false,
    },
    {
      id: "caption",
      kind: "caption",
      label: "Captions",
      body: BODIES["vault-landing-pages"].caption,
      canLead: false,
    },
    {
      id: "case-study",
      kind: "case_study",
      label: "Case study",
      body: BODIES["vault-landing-pages"].case_study,
      canLead: false,
      handling:
        "Per-client rates paired with location details. Internal review only — not cleared for publication as written.",
    },
  ],
};

/* ── Readers ──────────────────────────────────────────────────────
   Kept here so no screen has to know how the corpus is shaped. */

export const momentById = (id: string): Moment =>
  MOMENTS.find((m) => m.id === id) ?? MOMENTS[0];

export const packOf = (momentId: string): PackAsset[] => PACK[momentId] ?? [];

export const assetById = (momentId: string, assetId: string): PackAsset | undefined =>
  packOf(momentId).find((a) => a.id === assetId);

export const leadCandidates = (momentId: string): PackAsset[] =>
  packOf(momentId).filter((a) => a.canLead);

/** Same format as the lead — a choice between equals, not a derivative.
    Picking reel A leaves B and C as the two she did not take. */
export const alternatesOf = (momentId: string, leadId: string): PackAsset[] => {
  const lead = assetById(momentId, leadId);
  if (!lead) return [];
  return packOf(momentId).filter((a) => a.id !== leadId && a.kind === lead.kind);
};

/** Everything written FROM the approved lead. */
export const derivedOf = (momentId: string, leadId: string): PackAsset[] => {
  const lead = assetById(momentId, leadId);
  if (!lead) return packOf(momentId);
  return packOf(momentId).filter((a) => a.kind !== lead.kind);
};

export const corpusFor = (platform: PlatformKey): CorpusItem[] =>
  CORPUS.filter((c) => c.platform === platform);

/** What is actually waiting on a person, for the nav badge. */
export const OPEN_SIGNALS = MOMENTS.filter((m) => m.state !== "blocked").length;
