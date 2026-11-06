/* The three onboarding steps that follow the ClickUp provisioning draft.
 *
 * ── WHY THESE THREE, IN THIS ORDER ────────────────────────────────────────
 * Whitney listed the signature-wave side effects in one breath (Sept 2):
 * "emailing the client with a copy of their signed contract and their link to
 * book their ads kickoff call, creating a folder for the client in our Google
 * Drive and uploading all of the necessary assets there — sales call records,
 * their contract, any questions that they have filled out — then she is
 * creating a Slack channel particularly for that client account. She is
 * sending a message to the team in Slack letting them know, hey, this new
 * client has signed on."
 *
 * Ordering them by dependency rather than by the order she said them:
 *
 *   STEP 2  Drive folder      nothing depends on it, everything else does.
 *                             The email attaches a file from it; the Slack
 *                             bookmarks link to it.
 *   STEP 3  Welcome email     needs the countersigned contract from step 2,
 *                             and it is the thing that CAUSES the booking
 *                             that step 4 waits on.
 *   STEP 4  Slack channel     GATED, on TWO anchors. Their own team-brief
 *                             template opens "She has scheduled her Ads
 *                             Kickoff Call for (DATE) and their LeadLock
 *                             Kickoff call for (DATE)" — so the announcement
 *                             cannot be a signature-wave action at all, and
 *                             it needs both dates. Each timeline variant
 *                             counts its weeks from its own track's kickoff.
 *                             See buildSlackStage for why the second date is
 *                             entered and never derived.
 *
 * That last point is a correction to the call, not a design choice: Whitney
 * narrated Slack as a day-0 step and her own templates disagree.
 *
 * The order also runs from least to most consequential — a Drive folder is
 * nearly harmless, an @channel post is socially irreversible, an email to the
 * client is the most irreversible of the three. So the approve gate gets more
 * meaningful as you advance, which is the right shape for a human-in-the-loop
 * flow.
 *
 * ── WHERE THE CONTENT COMES FROM ──────────────────────────────────────────
 * Every folder name, sharing setting, bookmark and message body below is
 * VERBATIM from the descriptions on their own ClickUp template tasks, read
 * over the API and kept in `.clickup-snapshot/clickup-descriptions.json`.
 * The earlier snapshot captured description *lengths* only, which is why
 * these steps could not be built before. Each constant carries the task it
 * was read off.
 *
 * Nothing here is invented. Where their template says something we cannot
 * resolve — the body copy of an email that lives in a Google Doc we have no
 * access to — the row says so instead of filling in plausible prose.
 *
 * ── THE BOUNDARY IS THE SAME AS STEP 1 ────────────────────────────────────
 * No Drive call, no Gmail call, no Slack call. These are drafts a human
 * approves, and approval records the authorisation and stops. There is no
 * client library for any of the three systems in this codebase.
 */

/** Step 1 is the ClickUp draft, which predates this module and lives in
    onboarding-plan.mjs. These are steps 2-4. */
export const STAGE_KEYS = Object.freeze(["drive", "email", "slack"]);

/** Where each row's value came from. Rendered as a badge, because a reviewer
    approving a batch should be able to see which values were read out of
    something real and which are waiting on a human or on the client. */
export const ITEM_SOURCES = Object.freeze([
  "from-alert", // recovered from the Dubsado signed/paid alert
  "from-sales-call", // an artifact of the sales call that predates signature
  "template-copy", // a copy of one of their own template documents
  "computed", // derived here (a date, a slug, a week range)
  "from-step", // produced by an earlier step in this flow
  "human", // deliberately left for a person to write
  "awaiting-client", // cannot exist until the client acts
]);

/** Same three-state vocabulary the ClickUp task table uses, so the four steps
    read as one product: ready now / waiting on a call / client-gated. */
export const ITEM_STATES = Object.freeze(["ready", "pending", "gated"]);

/* ── Drive, verbatim ──────────────────────────────────────────────
   From `Create Google Drive Client Folder` (LeadLock, 409 chars) and
   `Google Drive Client Folder` (Google + Meta v1/v2, 408 chars — the same text
   bar one word):

     "Create a folder titled the client's company name in the appropriate
      service in the shared drive - WIA | Clients. This folder will not be
      shared with the client. Create a subfolder titled ' WIA + Client's
      company name'. Modify the access to 'Anyone with the link' is viewer as
      this will be shared with the client. Inside the client folder create the
      following folders: Brand Assets / Call Recordings & Summaries"

   TWO folders per client, not one. The outer one is internal; the inner
   `WIA + <Company>` is the only thing that gets link-shared. That detail is
   the whole reason this step is worth drafting rather than describing. */
const DRIVE_SHARED_DRIVE = "WIA | Clients";
const DRIVE_SHARED_DRIVE_URL =
  "https://drive.google.com/drive/folders/1hNgm5xfG-TxdHK37Rb-0DcyQ_2tnlRwI";

/* The LeadLock track keeps its recordings under a DIFFERENT parent. From
   `Upload Call Recording to Google Drive` (151 chars): "Look for the client's
   folder in the Foolproof Follow-Up Advantage Folder and upload it to the
   client's folder inside the Recordings & Summaries folder." */
const DRIVE_SERVICE_BY_OFFER = Object.freeze({
  elevate: "ELEVATE",
  ads: "Google Search Accelerator",
  leadlock: "Foolproof Follow-Up Advantage",
  google_accelerator: "Google Search Accelerator",
  meta_accelerator: "Meta Ads Accelerator",
  full_service: "ARCHIVES - Full Service",
});

/* Their VIP Day template asks for a third set (`Call Recordings`, `Brand
   Assets`, `Resources`) and no client-facing subfolder. Encoded so the shape
   is right if those offers are ever mapped, rather than silently reusing the
   Elevate convention. */
const DRIVE_SUBFOLDERS = Object.freeze({
  standard: ["Brand Assets", "Call Recordings & Summaries"],
  vipday: ["Call Recordings", "Brand Assets", "Resources"],
});

/* ── Slack, verbatim ──────────────────────────────────────────────
   `Share details with team in Slack` — 1313 chars, and byte-identical in the
   stale v1 and the live v2 template. The parenthesised placeholders are
   THEIRS; the {{...}} tokens are this module's substitutions for them.

   The "Things to note" block is left EMPTY on purpose. In their template it
   is a worked example about a client mid-transition from another agency —
   i.e. a human observation that no automation can produce. A blank box with a
   cursor in it is the honest rendering, and it is also where the
   human-in-the-loop argument stops being an abstraction. */
const SLACK_TEAM_BRIEF = `@channel Hi team! {{firstName}} from {{company}} has signed on for {{offer}}! We will be setting up {{scope}}.

{{They}} {{have}} scheduled {{their}} Ads Kickoff Call for {{adsKickoff}} and their LeadLock Kickoff call for {{leadlockKickoff}}. From there, we will schedule {{their}} Messaging & Positioning Interview and {{their}} Ads Strategy Call.

Sharing {{their}} onboarding resources below. These can also be found in the Bookmarks folder at the top of this channel. I will be sharing {{their}} onboarding questionnaire and creating the LeadLock subaccount once that's completed.

Client Folder
LeadLock Kickoff Call Worksheet
Onboarding Questionnaire

Checklists:
{{checklists}}

Sale Call:
Recording
Summary

Things to note:
{{thingsToNote}}

@Whitney Hodges Let us know of any other details that need to be shared for this client!`;

/* `Share project timeline` — 1538 chars in the ads template, 648 in LeadLock.
   Its first word is "MODIFY DATES:", which is the manual burden stated by
   their own template. Six weeks for a both-offers client, four for LeadLock
   alone, and the closing "Ongoing:" block is their own written definition of
   what happens after onboarding ends. */
const SLACK_TIMELINE_ADS = `MODIFY DATES:

We're looking at the timeline below for this project (Subject to the client's response and feedback). Due dates will be set in ClickUp checklists.

Week 1 ({{w1}})
Onboarding calls to make initial tech connections and set up the necessary accounts. (Ads Kickoff Call and Messaging & Positioning Call)
Get access to branding assets, photos, and template emails.

Week 2 ({{w2}})
Continued onboarding calls and account setup. (Ads Strategy Call and LeadLock Kickoff Call)

Week 3 ({{w3}})
Google Ads launched
Ivy briefed on Meta Client Attraction Ads
Content creation begins and ads are presented to the client for feedback.
LeadLock BTS tech setup begins (phone setup, DNS, A2P, snapshot) and design/copy work.

Week 4 ({{w4}})
Meta Client Attraction Ads launched.
Ivy briefed on Conversion Ads.
Conversion Ads presented to the client for feedback.

Week 5 ({{w5}})
Conversion Ads launched.
Retargeting Ads content creation begins.
Retargeting Ads presented to the client for feedback.
LeadLock implementation completed and design work reviewed.
LeadLock assets shared with client for feedback.

Week 6 ({{w6}})
Retargeting Ads launched.
LeadLock onboarding call takes place, and system goes live.

Ongoing:
LeadLock tech support.
Ad campaign maintenance and optimization
Detailed analytics and reporting, and ad spend management
A monthly 30-minute 1:1 call with your account manager available upon request.

Let me know if anything needs to be modified!`;

const SLACK_TIMELINE_LEADLOCK = `MODIFY DATES:

We are looking at the timeline below for this project (Subject to client's response and feedback). Due dates will be set in ClickUp checklists.)

Week 1 ({{w1}}) Kickoff call to make initial tech connections and set up the necessary accounts, as well as getting access to branding assets, photos, and template emails.

Week 2 ({{w2}}) Start BTS tech setup (phone setup, DNS, A2P, snapshot) and design/copy work.

Week 3 ({{w3}}) Complete implementation and review design work.

Week 4 ({{w4}}) Launch implementation. Share assets with the client for feedback and schedule an onboarding call.`;

/* Recovered from the @-mention links inside the LeadLock team brief, which
   resolve to real Slack member IDs. Those three are therefore CERTAIN; the
   rest of the roster is inferred from the ads template's `@channel` plus the
   Role→person map, so they are marked `likely`. */
const SLACK_ROSTER = Object.freeze([
  { name: "Whitney Hodges", role: "CEO", confidence: "certain", note: "@-mentioned in their own template (U04LHK2MJVC)" },
  { name: "Danielle McGinnis", role: "GHL Specialist", confidence: "certain", note: "@-mentioned in their own template (U0AFN0NUZ9C)" },
  { name: "Tina Henares", role: "LeadLock Designer", confidence: "certain", note: "@-mentioned in their own template (U07J56D53RD)" },
  { name: "Gisselle Jimenez", role: "Assistant", confidence: "likely", note: "Posts the brief; her ClickUp account is 'WIA Support'" },
  { name: "Carmen Cruickshank", role: "Ads Manager · Google", confidence: "likely", note: "Ads track only" },
  { name: "Jacqueline Hood", role: "Ads Manager · Meta", confidence: "likely", note: "Ads track only" },
  { name: "Ivy Ayala", role: "Marketing Assistant", confidence: "likely", note: "Ads creative only" },
]);

/* ── Email, and the gap that closed ───────────────────────────────
   Fourteen of their "Send X email" tasks carry no body — the description is
   the single word "Template:" plus a link to a Google Doc in a numbered
   library (Client Email Templates > <offer> > "1 [CONTRACT]", "2
   [ONBOARDING]", "3 Welcome Email", "4 Onboarding Questionnaire Reminder",
   "5 Walkthrough Video Email", "6 Ongoing Support"). Drive access was never
   granted, so this step used to draft the envelope and say the body was
   unreachable.

   THE BODIES ARE NOW IN HAND, supplied per offer, and they settle three
   things the transcripts could not:

   1. THE ELEVATE EMAIL CARRIES TWO BOOKING LINKS, not one. Whitney described
      only the ads kickoff on the call, and an earlier pass concluded from that
      the LeadLock kickoff must be booked some other way. The template
      disproves it — both links sit in the same email.

   2. THE INTENDED ORDER IS ADS FIRST: "Ideally, this call should be scheduled
      for a later date than the Ads Kickoff Call." Ridgefield inverted it by 34
      days. So the two anchors are genuinely independent, AND the written
      intent is knowable — which is exactly what to put to Gisselle.

   3. FFA BUNDLES THE QUESTIONNAIRE INTO THE BOOKING FLOW — "When booking,
      you'll be prompted to complete our LeadLock onboarding questionnaire" —
      while ELEVATE sends it as a separate link due "at least 24 hours prior to
      the first call". Two mechanisms for the same artifact, and only the
      Elevate one can go unanswered indefinitely.

   The VIP and accelerator variants carry NO booking link at all: they propose
   a date in prose ("our first available opening for your VIP Day is Tuesday,
   July 2... let me know what time") and name the expert who will run it. For
   those offers there is no client-booked anchor to wait on, and the reply is a
   negotiation rather than a calendar event. */

const BOOKING_LINKS = Object.freeze({
  adsKickoff: "https://weddingindustryads.com/ads-kickoff-call",
  leadlockKickoff: "https://support.leadlockpro.com/kick-off-call",
  /* From the post-kickoff follow-up, not the welcome email. */
  strategyCall: "https://weddingindustryads.com/strategy-call-with-wia",
});

/* Verbatim, with their own placeholder tokens normalised to {{...}} so they
   can be resolved. Anything we cannot resolve keeps THEIR marker, so it reads
   as unfinished rather than as fact. */
const WELCOME_ELEVATE = [
  "Subject: Countersigned Contract & Next Steps for Onboarding",
  "",
  "Hi {{firstName}},",
  "",
  "Thank you for signing the agreement and submitting payment! Please find your countersigned contract attached for your records.",
  "",
  "To kick things off, I'd like to get your first two onboarding calls scheduled:",
  "",
  "Ads Kickoff Call: " + BOOKING_LINKS.adsKickoff,
  "The goal of this call is initial introductions, expectations, and tech connections for your Google and Meta Ads campaigns.",
  "",
  "LeadLock Kickoff Call: " + BOOKING_LINKS.leadlockKickoff,
  "The goal of this call is to get your LeadLock account set up to begin building your inquiry funnel. Ideally, this call should be scheduled for a later date than the Ads Kickoff Call.",
  "",
  "We'll coordinate scheduling your Messaging & Positioning Call and Google+Meta Strategy Call when we meet for the Ads Kickoff Call.",
  "",
  "Please follow the link below to complete our onboarding questionnaire at least 24 hours prior to the first call. It's thorough, so please feel free to get started as soon as you'd like. You can save drafts and come back to it as needed. By following the link you'll also find the list of accounts/login information you'll need to have handy on the call.",
  "",
  "(INSERT ONBOARDING QUESTIONNAIRE)",
  "",
  "If you have any questions, please let me know!",
  "",
  "Thank you,",
  "Whitney",
].join("\n");

const WELCOME_FFA = [
  "Subject: Countersigned Contract & Next Steps for Onboarding",
  "",
  "Hi {{firstName}},",
  "",
  "Thank you for signing the contract and submitting payment! Please find your countersigned contract attached for your records.",
  "",
  "To kick things off, we'll schedule your LeadLock Kickoff Call. This call is where we'll cover introductions, expectations, and strategy so you feel confident moving forward.",
  "",
  "Please use the link below to choose a time that works best for you. When booking, you'll be prompted to complete our LeadLock onboarding questionnaire. This ensures we have everything we need in place ahead of the call.",
  "",
  BOOKING_LINKS.leadlockKickoff,
  "",
  "If you have any questions in the meantime, please don't hesitate to reach out. We're so excited to get started!",
  "",
  "Thank you,",
  "Whitney",
].join("\n");

const WELCOME_ACCELERATOR = [
  "Subject: Countersigned Contract & Next Steps",
  "",
  "Hi {{firstName}},",
  "",
  "Thank you for signing the contract and submitting payment! Please find your countersigned contract attached for your records.",
  "",
  "Please follow the link below to complete our onboarding questionnaire and submit this to us at your earliest convenience.",
  "",
  "(INSERT ONBOARDING QUESTIONNAIRE)",
  "",
  "We'd love to get your first {{channel}} Ads 1:1 call scheduled for {{proposedDate}}. Does this date/time happen to work for you? If so, we'll send over the Zoom link and more details. If not, we can explore other options the week of {{proposedDate}}.",
  "",
  "If you have any questions, please let me know!",
  "",
  "Thank you,",
  "Whitney",
].join("\n");

/** Which welcome template each offer sends, and what it needs resolved. */
const WELCOME_BY_OFFER = Object.freeze({
  elevate: { body: WELCOME_ELEVATE, label: "ELEVATE welcome email", links: ["ads", "leadlock"] },
  full_service: {
    body: WELCOME_ELEVATE,
    label: "ELEVATE welcome email",
    links: ["ads", "leadlock"],
  },
  /* No ads-only variant was supplied. Borrowing Elevate's is flagged on the
     step rather than done silently — it offers a LeadLock kickoff to a client
     who did not buy LeadLock. */
  ads: {
    body: WELCOME_ELEVATE,
    label: "ELEVATE welcome email (borrowed)",
    links: ["ads", "leadlock"],
    borrowed: true,
  },
  leadlock: {
    body: WELCOME_FFA,
    label: "Foolproof Follow-Up Advantage welcome email",
    links: ["leadlock"],
  },
  google_accelerator: {
    body: WELCOME_ACCELERATOR,
    label: "Accelerator onboarding email",
    links: [],
    tokens: { channel: "Google" },
    proposesDate: true,
  },
  meta_accelerator: {
    body: WELCOME_ACCELERATOR,
    label: "Accelerator onboarding email",
    links: [],
    tokens: { channel: "Meta" },
    proposesDate: true,
  },
});
const EMAIL_TEMPLATE_DOCS = Object.freeze({
  welcome: {
    task: "Send Onboarding Email with call links",
    docId: "1k44-nata4Y6Unp5HHVkBSKmFqQosrbrDCAzzCBzMMw0",
  },
  callConfirmation: {
    task: "Send call confirmation email",
    docId: "190XCi3vWdYnFF1PChXjZS9vzxHbRsEpt0tvZZnwpzBk",
  },
  questionnaireReminder: {
    task: "Send Reminder / Complete Onboarding Questionnaire",
    docId: "1BIO-SHaK9mr7VlMwgH2HYX3JQb82tZWKfOgoa8Xa37A",
    name: "3 Onboarding Questionnaire Reminder",
  },
  marketResearch: {
    task: "SEND MARKET RESEARCH SURVEY",
    docId: "15H7rycIKczYwQKJuuWKJy7lPpYE5yjgu4w9AxktLPqI",
  },
});

const MAILBOX = "hello@weddingindustryads.com";

/* ── date helpers ─────────────────────────────────────────────── */

const addDays = (iso, days) => {
  const base = new Date(iso);
  if (Number.isNaN(base.getTime())) return null;
  base.setUTCDate(base.getUTCDate() + days);
  return base.toISOString().slice(0, 10);
};

const humanDate = (iso) => {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
};

const longDate = (iso) => {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
};

/** "May 26 – Jun 2", the format their own timeline post uses. */
const weekRange = (anchor, week) => {
  const from = addDays(anchor, (week - 1) * 7);
  const to = addDays(anchor, week * 7);
  return from && to ? `${humanDate(from)} – ${humanDate(to)}` : `Week ${week}`;
};

/** Their channel names were never shown to us, so this is a guess and is
    labelled one wherever it renders. */
const channelSlug = (projectName) =>
  `client-${String(projectName ?? "")
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60)}`;

const fill = (template, values) =>
  template.replace(/\{\{(\w+)\}\}/g, (_, key) =>
    values[key] === undefined || values[key] === null ? `({{${key}}})` : String(values[key]),
  );

const item = (id, title, rest = {}) => ({
  id,
  title,
  detail: rest.detail ?? null,
  group: rest.group ?? null,
  source: ITEM_SOURCES.includes(rest.source) ? rest.source : "computed",
  state: ITEM_STATES.includes(rest.state) ? rest.state : "ready",
  confidence: rest.confidence ?? "certain",
  note: rest.note ?? null,
  include: rest.include !== false,
});

/* ── STEP 2 · Google Drive ────────────────────────────────────── */

const buildDriveStage = ({ projectName, offers, templates }) => {
  const service =
    offers.map((key) => DRIVE_SERVICE_BY_OFFER[key]).find(Boolean) ?? "ELEVATE";
  const subfolders = DRIVE_SUBFOLDERS.standard;
  const hasAds = templates.includes("ads");
  const hasLeadLock = templates.includes("leadlock");

  const rows = [
    { depth: 0, text: DRIVE_SHARED_DRIVE, note: "shared drive", href: DRIVE_SHARED_DRIVE_URL },
    { depth: 1, text: service, note: "service folder, chosen by offer" },
    { depth: 2, text: projectName, note: "internal · NOT shared with the client" },
    {
      depth: 3,
      text: `WIA + ${projectName}`,
      note: "Anyone with the link · Viewer",
      chip: "the only client-facing folder",
    },
    ...subfolders.map((name) => ({ depth: 3, text: name, note: "" })),
  ];

  const items = [];

  /* Both templates carry `Upload Countersigned Contract` and a sales-call
     upload. Step 1 must NOT dedupe those — two lists, two tasks, measured on
     Ridgefield. Drive MUST, because it is one file. This is the one place the
     two-list model collapses, and getting the inversion right is the point. */
  items.push(
    item("drive-contract", "Countersigned contract", {
      group: "Seeded at signature",
      detail: "PDF from the Dubsado signature alert",
      source: "from-alert",
      note:
        hasAds && hasLeadLock
          ? "Satisfies `Upload Countersigned Contract` in BOTH lists — two ClickUp tasks, one file."
          : null,
    }),
    item("drive-sales-recording", "Sales call recording + transcript", {
      group: "Seeded at signature",
      detail: "Into Call Recordings & Summaries",
      source: "from-sales-call",
      note:
        hasAds && hasLeadLock
          ? "Satisfies the upload task in both lists (the LeadLock one also asks for the transcript)."
          : null,
    }),
  );

  if (hasAds) {
    items.push(
      item("drive-consult-form", "Ads consultation form", {
        group: "Seeded at signature",
        detail: "Their pre-sales intake, from Dubsado",
        source: "from-alert",
      }),
      item("drive-funnel-map", `Funnel Map — ${projectName}`, {
        group: "Template copies",
        detail: "Copy of their Funnel Map template sheet, renamed",
        source: "template-copy",
      }),
      item("drive-ads-strategy", `Ads Strategy — ${projectName}`, {
        group: "Template copies",
        detail: "Copy of the Ads Strategy template",
        source: "template-copy",
      }),
      item("drive-ads-creative", `Ads Creative — ${projectName}`, {
        group: "Template copies",
        detail: "Copy of the Ads Creative template",
        source: "template-copy",
      }),
    );
  }

  if (hasLeadLock) {
    items.push(
      item("drive-ll-worksheet", `LeadLock Kickoff Call Worksheet — ${projectName}`, {
        group: "Template copies",
        detail: 'Their task: "Make a copy… Update the title with the client\'s name."',
        source: "template-copy",
      }),
    );
  }

  /* Not in any subtask list — recovered from the Ads Kickoff Call description:
     "drop the recording link and the AI generated notes inside of the client
     meetings doc found in the client folder." So the folder is expected to
     already contain a meetings doc that nothing creates. */
  items.push(
    item("drive-meetings-doc", "Client meetings doc", {
      group: "Template copies",
      detail: "Where every recording link + Fathom summary gets indexed",
      source: "template-copy",
      confidence: "likely",
      note: "No task creates this. Recovered from the Ads Kickoff description, which assumes it exists.",
    }),
  );

  items.push(
    item("drive-brand-assets", "Brand assets", {
      group: "Waiting on the client",
      detail: "Folder created empty",
      source: "awaiting-client",
      state: "gated",
      note: 'Their task: "Review the answers in the questionnaire and check the uploaded assets." Nothing to file until the questionnaire returns.',
    }),
    item("drive-questionnaire", "Onboarding questionnaire (downloaded)", {
      group: "Waiting on the client",
      detail: "Exported from Dubsado once completed",
      source: "awaiting-client",
      state: "gated",
    }),
    item("drive-call-recordings", "Onboarding call recordings", {
      group: "Waiting on the client",
      detail: "One per call, as they happen",
      source: "awaiting-client",
      state: "pending",
    }),
  );

  return {
    key: "drive",
    order: 2,
    title: "Google Drive client folder",
    subtitle: "Two folders, one of them link-shared, plus the artifacts that exist today",
    system: "Google Drive",
    structure: { kind: "tree", rows },
    items,
    gate: null,
    messages: [],
    warnings: [
      "`Share Google Drive Folder (add client email address)` exists only in the superseded v1 template — v2 deleted the step that hands the client their folder.",
      hasAds && hasLeadLock
        ? "The contract and the sales recording are one file each here, but two tasks each in ClickUp. Step 1 keeps both; this step merges them."
        : null,
    ].filter(Boolean),
    sourceNote:
      "Folder names, the client-facing subfolder and its sharing setting are verbatim from their `Create Google Drive Client Folder` task description.",
  };
};

/* ── STEP 3 · The welcome email ───────────────────────────────── */

const buildEmailStage = ({ projectName, firstName, offers, templates }) => {
  const hasAds = templates.includes("ads");
  const hasLeadLock = templates.includes("leadlock");
  const to = firstName ? `${firstName} — ${projectName}` : projectName;

  const offerKey = offers.find((key) => WELCOME_BY_OFFER[key]) ?? "elevate";
  const variant = WELCOME_BY_OFFER[offerKey];

  const body = fill(variant.body, {
    firstName: firstName ?? "(CLIENT NAME)",
    ...(variant.tokens ?? {}),
  });
  /* Their own unresolved markers, counted rather than quietly filled. The
     questionnaire link is a Dubsado URL nobody has given us; the proposed VIP
     or accelerator date is a human decision by construction. */
  const unresolved = [
    body.includes("(INSERT ONBOARDING QUESTIONNAIRE)") ? "the onboarding questionnaire link" : null,
    /\{\{proposedDate\}\}/.test(body) ? "the proposed call date" : null,
  ].filter(Boolean);

  const rows = [
    { label: "From", value: MAILBOX },
    { label: "To", value: to },
    { label: "Subject", value: body.split("\n")[0].replace(/^Subject:\s*/, "") },
  ];

  const items = [
    item("email-contract", "Countersigned contract", {
      group: "Attachment",
      detail: "The same PDF filed in step 2",
      source: "from-step",
      note: "Every variant of this email opens by attaching it: “Please find your countersigned contract attached for your records.”",
    }),
  ];

  if (variant.links.includes("ads")) {
    items.push(
      item("email-ads-kickoff-link", "Ads Kickoff Call booking link", {
        group: "Links",
        detail: BOOKING_LINKS.adsKickoff,
        source: "template-copy",
        note: "Client-booked. This is the anchor the ads track counts weeks from.",
      }),
    );
  }
  if (variant.links.includes("leadlock")) {
    items.push(
      item("email-ll-kickoff-link", "LeadLock Kickoff Call booking link", {
        group: "Links",
        detail: BOOKING_LINKS.leadlockKickoff,
        source: "template-copy",
        note: hasAds
          ? "Their template asks the client to book this AFTER the ads kickoff — “Ideally, this call should be scheduled for a later date than the Ads Kickoff Call.” Ridgefield booked it 34 days EARLIER."
          : "Client-booked. Booking it also triggers their questionnaire.",
      }),
    );
  }

  if (offerKey === "leadlock") {
    items.push(
      item("email-questionnaire-bundled", "Onboarding questionnaire", {
        group: "Links",
        detail: "Bundled into the booking flow, not sent as its own link",
        source: "template-copy",
        note: "“When booking, you'll be prompted to complete our LeadLock onboarding questionnaire.” This is the one variant where the questionnaire cannot be left unanswered while the call goes ahead.",
      }),
    );
  } else {
    items.push(
      item("email-questionnaire-link", "Onboarding questionnaire link", {
        group: "Links",
        detail: "Still living in Dubsado — URL not supplied",
        source: "human",
        state: "pending",
        confidence: "unknown",
        note: "Their template leaves “(INSERT ONBOARDING QUESTIONNAIRE)” as a manual paste. Due “at least 24 hours prior to the first call”, and it also carries the account/login list the client needs on the call — so a late questionnaire delays the kickoff, not just the paperwork.",
      }),
    );
  }

  if (variant.proposesDate) {
    items.push(
      item("email-proposed-date", "Proposed 1:1 date", {
        group: "Body",
        detail: "This variant has no booking link — the date is proposed in prose",
        source: "human",
        state: "pending",
        confidence: "unknown",
        note: "“We'd love to get your first call scheduled for {{proposedDate}}. Does this date/time happen to work for you?” The reply is a negotiation, so there is no client-booked anchor to wait on for this offer.",
      }),
    );
  }

  /* Everything after this email, queued and excluded by default: none of it
     can be drafted at signature. */
  items.push(
    item("email-post-kickoff", "Post-kickoff follow-up", {
      group: "Queued behind the client",
      detail: "Onboarding Guide Presentation + call recording + strategy-call booking link",
      source: "awaiting-client",
      state: "pending",
      include: false,
      note: `Real sends also carry the client's Drive folder, the Messaging & Positioning Questionnaire, and — for multi-brand clients — a LeadLock user-adding ask with a Loom tutorial. Strategy-call link: ${BOOKING_LINKS.strategyCall}`,
    }),
    item("email-mp-questionnaire", "Messaging & Positioning Questionnaire", {
      group: "Queued behind the client",
      detail: "A SECOND questionnaire, sent after the kickoff call",
      source: "awaiting-client",
      state: "pending",
      include: false,
      note: "A Google Doc, reviewed together on the M&P call. Distinct from the onboarding questionnaire and absent from every ClickUp template — it appears only in real sent mail.",
    }),
    item("email-questionnaire-reminder", "Questionnaire chaser", {
      group: "Queued behind the client",
      detail: `Their library numbers it — “${EMAIL_TEMPLATE_DOCS.questionnaireReminder.name}”`,
      source: "awaiting-client",
      state: "gated",
      include: false,
    }),
    item("email-market-research", "Market research survey", {
      group: "Queued behind the client",
      detail: "Its own template; carries no Phase, so it can never be dated",
      source: "awaiting-client",
      state: "pending",
      include: false,
      note: "Present in both ads templates, absent from Ridgefield's live list. Its only live trace is “Draft the market research survey questions” in the MAINTENANCE list, 106 days later — drafting from scratch rather than sending a template.",
    }),
  );

  return {
    key: "email",
    order: 3,
    title: "Welcome email to the client",
    subtitle: "Their own template, per offer — the one outbound artifact in the signature wave",
    system: "Gmail · hello@weddingindustryads.com",
    structure: { kind: "envelope", rows },
    items,
    gate: null,
    messages: [
      {
        id: "email-welcome",
        label: variant.label,
        sourceTask:
          "their `Client Email Templates` library, reached from the `Send Onboarding Email with call links` task",
        body,
        include: true,
      },
    ],
    warnings: [
      unresolved.length
        ? `This email still needs ${unresolved.join(" and ")} pasted in by hand — their template leaves ${unresolved.length === 1 ? "it" : "both"} as a literal marker.`
        : null,
      variant.borrowed
        ? "No ads-only welcome template was supplied, so this borrows the ELEVATE one — which offers a LeadLock Kickoff Call to a client who did not buy LeadLock. Ask for the ads-only variant."
        : null,
      hasAds && hasLeadLock
        ? "This email is where both anchors are set, and their template states the intended order: the LeadLock call should be booked LATER than the ads kickoff. Ridgefield did the reverse by 34 days, which is why step 4 asks for both dates instead of deriving one."
        : null,
      variant.proposesDate
        ? "The accelerators have a full email template library but NO ClickUp onboarding template, so step 1 contributes zero tasks for them. Email is the only part of accelerator onboarding this flow can draft."
        : null,
    ].filter(Boolean),
    sourceNote:
      "Body verbatim from their per-offer welcome template, with only the client's first name substituted. Their own unresolved markers are left in place rather than filled.",
  };
};

/* ── STEP 4 · Slack ───────────────────────────────────────────── */

const buildSlackStage = ({
  projectName,
  firstName,
  offers,
  templates,
  kickoffDate,
  adsKickoffDate,
  offerLabel,
}) => {
  const hasAds = templates.includes("ads");
  const hasLeadLock = templates.includes("leadlock");
  const slug = channelSlug(projectName);

  /* ── TWO ANCHORS, NOT ONE ──────────────────────────────────────
     Their team brief names TWO kickoff dates and the two timeline variants
     count weeks from different ones: the ads post's week 1 is "Ads Kickoff
     Call and Messaging & Positioning Call", the LeadLock post's week 1 is its
     own kickoff. Deriving the second from the first looks reasonable — their
     ads timeline does put "LeadLock Kickoff Call" in week 2 — but the one
     live client inverts it by 34 days IN THE OPPOSITE DIRECTION:

         LeadLock kickoff  2026-03-25   (live `Complete Onboarding Call`)
         Ads kickoff       2026-04-28   (live `Complete Ads Kickoff Call`)

     And step 1's single `kickoffDate` is the LEADLOCK one — its phase cadence
     (+0/+7/+14/+21/+28) was recovered from Ridgefield's LeadLock list. So a
     both-offers client needs a second date entered by hand, and nothing here
     may guess it. An unresolved anchor leaves THEIR OWN "(DATE)" placeholder
     in place, which is honest and visibly unfinished. */
  const anchors = {
    leadlock: hasLeadLock ? (kickoffDate ?? null) : null,
    ads: hasAds ? (adsKickoffDate ?? null) : null,
  };
  const missing = [
    hasLeadLock && !anchors.leadlock ? "the LeadLock kickoff" : null,
    hasAds && !anchors.ads ? "the ads kickoff" : null,
  ].filter(Boolean);

  const gate = missing.length
    ? {
        blockedBy: "kickoff",
        label: `Waiting on ${missing.join(" and ")}`,
        hint: "Their team brief opens “She has scheduled her Ads Kickoff Call for (DATE) and their LeadLock Kickoff call for (DATE)”, and each timeline variant counts weeks from its own kickoff — so these posts cannot be written at signature. On Ridgefield the two calls were 34 days apart, so the second one is entered, never derived.",
      }
    : null;

  const roster = SLACK_ROSTER.filter((person) => {
    if (!hasAds && ["Carmen Cruickshank", "Jacqueline Hood", "Ivy Ayala"].includes(person.name))
      return false;
    if (!hasLeadLock && ["Tina Henares", "Danielle McGinnis"].includes(person.name)) return false;
    return true;
  });

  /* Their `Create Bookmarks folder` task says "the client's Google Drive, and
     the ClickUp checklist" — singular. Their team brief lists THREE
     checklists. For a both-offers client the brief is right and the bookmark
     task is stale, so this follows the brief and flags the discrepancy. */
  const checklistNames = [
    hasAds ? "Google + Meta Onboarding Checklist" : null,
    hasLeadLock ? "LeadLock Checklist" : null,
    hasAds ? "Ads Traffic Landing Page Checklist" : null,
  ].filter(Boolean);

  const bookmarks = [`${projectName} — Google Drive folder`, ...checklistNames];

  const rows = [
    { depth: 0, text: `#${slug}`, note: "new channel", chip: "naming convention unconfirmed" },
    { depth: 1, text: `${roster.length} members invited`, note: "" },
    { depth: 1, text: `Bookmarks folder · ${bookmarks.length}`, note: "" },
    ...bookmarks.map((name) => ({ depth: 2, text: name, note: "" })),
  ];

  /* Each from its own anchor. Unresolved stays as their placeholder. */
  const adsKickoff = longDate(anchors.ads);
  const leadlockKickoff = longDate(anchors.leadlock);

  const scope = [
    hasAds ? "Google ads, Meta Ads" : null,
    hasLeadLock ? "LeadLock" : null,
    hasAds ? "and creating an ads traffic landing page" : null,
  ]
    .filter(Boolean)
    .join(", ")
    .replace(", and creating", " and creating");

  const brief = fill(SLACK_TEAM_BRIEF, {
    /* Their template hardcodes "She has scheduled her…". We know the
       signatory's first name from the Dubsado alert and nothing else, so
       guessing from a name would misgender a real client on a message going
       to the whole team. Neutral by default, and the warning below tells them
       the template needs a pronoun field. */
    They: "They",
    have: "have",
    their: "their",
    firstName: firstName ?? "(CLIENT NAME)",
    company: projectName,
    offer: offerLabel ?? "ELEVATE",
    scope: scope || "their onboarding",
    adsKickoff: adsKickoff ?? "(DATE)",
    leadlockKickoff: leadlockKickoff ?? "(DATE)",
    checklists: checklistNames.join("\n"),
    thingsToNote: "",
  });

  const timelineTemplate = hasAds ? SLACK_TIMELINE_ADS : SLACK_TIMELINE_LEADLOCK;
  const weeks = hasAds ? 6 : 4;
  /* The ads variant's week 1 is the ads kickoff; the LeadLock variant's is
     the LeadLock kickoff. Same template shape, different anchor. */
  const timelineAnchor = hasAds ? anchors.ads : anchors.leadlock;
  const timeline = fill(
    timelineTemplate,
    Object.fromEntries(
      Array.from({ length: weeks }, (_, i) => [
        `w${i + 1}`,
        timelineAnchor ? weekRange(timelineAnchor, i + 1) : `DATE`,
      ]),
    ),
  );

  const items = [
    item("slack-channel", `Create #${slug}`, {
      group: "Channel",
      source: "computed",
      confidence: "heuristic",
      note: "Their real naming convention was never shown to us. Rename before approving.",
    }),
    ...roster.map((person, i) =>
      item(`slack-member-${i}`, `Invite ${person.name}`, {
        group: "Members",
        detail: person.role,
        source: "computed",
        confidence: person.confidence,
        note: person.note,
      }),
    ),
    ...bookmarks.map((name, i) =>
      item(`slack-bookmark-${i}`, name, {
        group: "Bookmarks",
        detail: i === 0 ? "From step 2" : "From step 1",
        source: "from-step",
      }),
    ),
    item("slack-viktor", "Add Viktor.ai to the channel", {
      group: "Channel",
      detail: "Their own final subtask under Create Slack Channel",
      source: "template-copy",
    }),
    item("slack-things-to-note", "“Things to note” — the human paragraph", {
      group: "Post 1 · team brief",
      detail: "Left blank on purpose",
      source: "human",
      state: "pending",
      confidence: "unknown",
      note: "In their template this is a worked example about a client mid-transition from another agency. No automation can produce it; a person types it.",
    }),
  ];

  return {
    key: "slack",
    order: 4,
    title: "Slack channel and the two posts",
    subtitle: "Their own message templates, filled in from steps 1 and 2",
    system: "Slack",
    structure: { kind: "tree", rows },
    items,
    gate,
    /* Persisted, so a second visit knows which anchor it already has. */
    anchors,
    messages: [
      {
        id: "slack-post-brief",
        label: "Post 1 · team brief",
        sourceTask: "`Share details with team in Slack` — 1313 chars, identical in v1 and v2",
        body: brief,
        include: true,
      },
      {
        id: "slack-post-timeline",
        label: `Post 2 · project timeline (${weeks} weeks)`,
        sourceTask: hasAds
          ? "`Share project timeline` — 1538 chars, the ads variant"
          : "`Share project timeline` — 648 chars, the LeadLock variant",
        body: timeline,
        include: true,
      },
    ],
    warnings: [
      "Their brief names TWO kickoff dates. On Ridgefield they were 34 days apart and in the opposite order to their own timeline (LeadLock 25 Mar, ads 28 Apr), so neither is derived from the other — and step 1's single anchor is the LeadLock one.",
      "The eight resources the brief lists (Client Folder, worksheet, questionnaire, three checklists, recording, summary) are BARE TEXT in their template, not links — the only real hyperlink in it is @Whitney Hodges. Whoever posts this attaches the URLs by hand.",
      "Both announcements label their “Things to note” block “(EXAMPLE)”, so the paragraph in their template is a worked sample rather than live copy. It is left blank here.",
      "Their team brief hardcodes “She has scheduled her…”. The alert gives us a first name and nothing else, so these render neutrally — the template wants a pronoun field.",
      "Their `Create Bookmarks folder` task says “the client's Google Drive, and the ClickUp checklist” — singular. Their own team brief lists three checklists. This follows the brief.",
      hasAds
        ? "The timeline promises six weeks. Ridgefield's ads track ran from 28 Apr to 6 Jul and retargeting never launched — their own template is the benchmark delivery misses."
        : null,
    ].filter(Boolean),
    sourceNote:
      "Both message bodies are verbatim from their ClickUp task descriptions, with only the parenthesised placeholders substituted.",
  };
};

/**
 * Build steps 2-4 for a client whose ClickUp draft has just been approved.
 *
 * @param {object} input
 * @param {string} input.projectName
 * @param {string} [input.firstName]   Signatory, from the Dubsado alert.
 * @param {string[]} input.offers      Selected offer keys.
 * @param {string[]} input.templates   Template keys the offer set resolved to.
 * @param {string} [input.kickoffDate] Wave 2's anchor. Absent = step 4 gated.
 * @param {string} [input.offerLabel]  Human offer name for the Slack brief.
 */
export const buildStagePlans = ({
  projectName,
  firstName = null,
  offers = [],
  templates = [],
  kickoffDate = null,
  adsKickoffDate = null,
  offerLabel = null,
} = {}) => {
  const shared = {
    projectName,
    firstName,
    offers,
    templates,
    kickoffDate,
    adsKickoffDate,
    offerLabel,
  };
  return [buildDriveStage(shared), buildEmailStage(shared), buildSlackStage(shared)];
};

/**
 * Re-render step 4's two posts once a kickoff anchor arrives.
 *
 * Mirrors `applyKickoffDate` in the store: recompute the derived values and
 * leave everything a human touched alone. A reviewer who has already typed
 * the "Things to note" paragraph or edited a body keeps it.
 */
export const rehydrateSlackStage = (plan, input) => {
  if (!plan || plan.key !== "slack") return plan;
  const fresh = buildSlackStage(input);
  return {
    ...plan,
    gate: fresh.gate,
    anchors: fresh.anchors,
    structure: fresh.structure,
    messages: plan.messages.map((message) => {
      const next = fresh.messages.find((m) => m.id === message.id);
      /* `edited` is set by the store when a reviewer changes a body. */
      if (!next || message.edited) return message;
      return { ...message, body: next.body };
    }),
  };
};

/** Counts for a step header, recomputed live as a reviewer edits. */
export const summarizeStage = (plan) => {
  const all = plan?.items ?? [];
  const kept = all.filter((i) => i.include !== false);
  const messages = (plan?.messages ?? []).filter((m) => m.include !== false);
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
