/* Client-onboarding provisioning store — the conjunction correlator.
 *
 * onboarding-alert-parser.mjs turns one Dubsado email into a typed HALF-signal.
 * This module holds the other half of the problem: pairing two halves into one
 * client, refusing to fire on a half, and refusing to fire twice.
 *
 * Same durability contract as leads-store.mjs: state lives in memory, mirrored
 * to disk with atomic writes (temp file + rename) serialized through one
 * promise chain. Point ONBOARDING_FILE at a mounted volume to survive
 * redeploys — and note that for THIS store the file is not a convenience, it
 * is the dedupe key (see WHY OUR OWN STORE IS THE SOURCE OF TRUTH).
 *
 * ── THREE CORRECTIONS TO THE OBVIOUS DESIGN ───────────────────────────────
 *
 * 1. "ALREADY ONBOARDED OR NOT" CANNOT BE BINARY.
 *    Two alerts arrive per client, in no guaranteed order, minutes or days
 *    apart. So a single alert from an unknown client is not a green light.
 *    There are three outcomes, not two:
 *      already provisioned  -> ignore
 *      half-pair pending    -> attach, re-check whether the pair is now whole
 *      never seen           -> open a pending record and wait
 *
 * 2. THE RECURRING-PAYMENT TRAP IS WHY THE PROVISIONED CHECK EXISTS.
 *    Elevate is a monthly retainer. Month 2's payment fires a subject
 *    IDENTICAL in shape to month 1's — same client, same project, same
 *    grammar. Nothing in the alert distinguishes a new signing from the
 *    thirteenth invoice of an existing one. Without the provisioned check this
 *    store would re-onboard a paying client every month, forever.
 *
 * 3. SEED BEFORE THE FIRST POLL, OR ONBOARD THE ENTIRE CLIENT BOOK.
 *    A first poll against an empty store scans 90 days of Dubsado mail and
 *    reads every historical alert as a new signing. `ingest` therefore REFUSES
 *    to run until `seed()` has been called, and says so. This is a guard
 *    against a very loud first-run failure, not a nicety.
 *
 * ── WHY OUR OWN STORE IS THE SOURCE OF TRUTH, NOT CLICKUP ─────────────────
 * The tempting dedupe is "does a ClickUp list named after this project already
 * exist?" — but that makes fuzzy name matching load-bearing on the one
 * decision that must never be wrong. This store's projectKey is deterministic
 * and ours. A ClickUp lookup belongs on the review card as a SOFT WARNING
 * ("a list matching 'The Elia' already exists — provision anyway?"), which is
 * advisory to a human rather than authoritative over a machine.
 *
 * ── IDENTITY IS THE PROJECT, NEVER THE PERSON ─────────────────────────────
 * Records key on `projectKey`. The payer and the signer can differ, so pairing
 * on a first name would strand both halves forever. See the parser's header.
 */

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { normalizeProjectKey } from "./onboarding-alert-parser.mjs";

/* ── OFFER VOCABULARY ──────────────────────────────────────────────────────
   Transcript-derived, not ClickUp-derived. Whitney, Sept 2 @19:59: "if they're
   just doing the foolproof follow-up advantage, which is our, like, lead lock
   GHL offer, then that's its own thing, versus if they're signing on for ads
   management as well, then it's like, we're going off both of those onboarding
   templates."

   So this is a SET, not a 1-of-N switch: {leadlock}, {ads}, or both.

   CORRECTED BY THE CLICKUP READ. "Both" does NOT mean one merged list. A live
   ELEVATE client, Ridgefield Weddings and Events, is laid out as ELEVATE
   Clients (space) -> Ridgefield Weddings and Events (folder) -> three separate
   lists: LeadLock Onboarding, Google + Meta Onboarding, and Client Management.
   So the both-case is two onboarding lists side by side in one client folder,
   and the eight name collisions between the templates need no dedup because
   they land in different lists.

   `templateConfirmed` now means a real ClickUp template was READ for that
   offer, not merely that Whitney named one. */
export const OFFERS = Object.freeze({
  leadlock: {
    key: "leadlock",
    label: "Foolproof Follow-Up Advantage",
    note: "The LeadLock / GHL offer",
    templateConfirmed: true,
  },
  ads: {
    key: "ads",
    label: "Ads management",
    note: "Google + Meta",
    templateConfirmed: true,
  },
  elevate: {
    key: "elevate",
    label: "Elevate (retainer)",
    /* Confirmed by reading Ridgefield: an ELEVATE client receives BOTH
       onboarding lists plus Client Management. Also the reason the provisioned
       check is load-bearing — a monthly retainer re-fires the paid alert every
       month with an identical subject shape. */
    note: "Monthly retainer — gets both onboarding lists. Repeat payments re-fire the paid alert.",
    templateConfirmed: true,
  },
  google_accelerator: {
    key: "google_accelerator",
    label: "Google Search Accelerator",
    note: "Published at $1,997 — the one real paid sample matches this exactly",
    templateConfirmed: false,
  },
  meta_accelerator: {
    key: "meta_accelerator",
    label: "Meta Ads Accelerator",
    note: "Published at $1,697 — ambiguous with LeadLock setup at the same price",
    templateConfirmed: false,
  },
  full_service: {
    key: "full_service",
    label: "Full service",
    note: "Named on the Aug 26 call. Mapped to both onboarding lists; ARCHIVES - Full Service space exists.",
    templateConfirmed: true,
  },
});

export const OFFER_KEYS = Object.freeze(Object.keys(OFFERS));

/* ── STATES ────────────────────────────────────────────────────────────────
   PRE_EXISTING  seeded as already-onboarded before the first poll; never a card
   AWAITING_PAIR one half seen, waiting for the other — the conjunction gate
   READY         both halves present; awaiting a human to activate and pick offers
   DRAFTED       offers chosen, execution draft generated and editable
   APPROVED      wave 1 approved — the setup batch. NOT the end of the record.
   SCHEDULED     wave 2 approved — the dates, once the calls were booked
   IGNORED       withdrawn, with a reason on the record

   APPROVED IS NO LONGER TERMINAL, and that was a real defect rather than a
   simplification. The whole point of the two-wave design is that setup is
   approved at signature and the dates are approved later, once the client has
   booked. A terminal APPROVED meant the second wave could never happen: the
   date-application call accepted only a DRAFTED record, so approving the
   pre-booking batch permanently locked the schedule out.

   No ClickUp mutation is issued in either wave, so there is still no
   PROVISIONING or FAILED state — inventing those before a write path exists
   would be modelling code that does not run. */
export const STATES = Object.freeze([
  "PRE_EXISTING",
  "AWAITING_PAIR",
  "READY",
  "DRAFTED",
  "APPROVED",
  "SCHEDULED",
  "IGNORED",
]);

export const IGNORE_REASONS = Object.freeze({
  already_provisioned: "This client has already been onboarded.",
  recurring_payment: "Repeat payment on an already-onboarded client.",
  half_pair_timeout: "Only one half of the signature pair ever arrived.",
  dismissed: "Dismissed by a reviewer.",
  pre_seed_backlog: "Historical alert predating the first poll.",
});

export const LIMITS = Object.freeze({
  clients: 500,
  repeatAlerts: 20,
  draftTasks: 400,
  projectName: 300,
  firstName: 200,
  text: 500,
  note: 2000,
  offers: OFFER_KEYS.length,
  /* Steps 2-4. `messageBody` is sized for their real Slack templates — the
     project-timeline post is 1538 characters before substitution, and the
     six computed week ranges push it past 1600. */
  stageItems: 60,
  messageBody: 4000,
});

/** Half-pairs older than this are withdrawn rather than waiting forever. */
export const DEFAULT_HALF_PAIR_TTL_DAYS = 14;

const emptyState = () => ({
  version: 1,
  seededAt: null,
  seedNote: null,
  lastPollAt: null,
  clients: [],
});

export class OnboardingError extends Error {
  constructor(code, message, status = 400) {
    super(message);
    this.name = "OnboardingError";
    this.code = code;
    this.status = status;
  }
}

const cleanString = (raw, maxLength) =>
  typeof raw === "string" && raw.trim() ? raw.trim().slice(0, maxLength) : null;

const cleanIso = (raw) => {
  if (typeof raw !== "string" || !raw.trim()) return null;
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
};

/**
 * A stable identity for one alert, so a 15-minute poll re-reading the same
 * mailbox does not open a second record.
 *
 * Prefers the mailbox's own message id. The fallback hash deliberately
 * includes the alert's ORIGINAL date and amount: without them, month 2 of a
 * retainer would fingerprint identically to month 1 and be silently swallowed
 * as a duplicate, hiding the recurring payment from the audit trail instead of
 * recording it as ignored.
 */
export const fingerprintAlert = (alert, messageId) => {
  const explicit = cleanString(messageId, LIMITS.text);
  if (explicit) return explicit;
  return crypto
    .createHash("sha256")
    .update(
      [
        alert?.kind ?? "",
        alert?.projectKey ?? "",
        alert?.originalDate ?? alert?.receivedAt ?? "",
        alert?.amount ?? "",
      ].join("|"),
    )
    .digest("hex")
    .slice(0, 32);
};

/** The parsed half, reduced to what a record and a review card need. */
const halfFromAlert = (alert, fingerprint, at) => ({
  fingerprint,
  firstName: cleanString(alert.firstName, LIMITS.firstName),
  amount: Number.isFinite(alert.amount) ? alert.amount : null,
  currency: cleanString(alert.currency, 8),
  /* Kept verbatim on the record because the review card shows it: a reviewer
     approving a write should see the raw subject that triggered it. */
  source: alert.source === "forwarded" ? "forwarded" : "direct",
  sender: cleanString(alert.sender, LIMITS.text),
  senderIsDubsado: alert.senderIsDubsado === true,
  originalDate: cleanString(alert.originalDate, LIMITS.text),
  /* Machine-readable twin of originalDate. Due-date arithmetic reads this;
     the review card reads the human string. */
  originalDateIso: cleanIso(alert.originalDateIso),
  receivedAt: cleanString(alert.receivedAt, LIMITS.text),
  recordedAt: at,
});

const sanitizeHalf = (raw) =>
  raw && typeof raw === "object"
    ? {
        fingerprint: cleanString(raw.fingerprint, LIMITS.text),
        firstName: cleanString(raw.firstName, LIMITS.firstName),
        amount: Number.isFinite(raw.amount) ? raw.amount : null,
        currency: cleanString(raw.currency, 8),
        source: raw.source === "forwarded" ? "forwarded" : "direct",
        sender: cleanString(raw.sender, LIMITS.text),
        senderIsDubsado: raw.senderIsDubsado === true,
        originalDate: cleanString(raw.originalDate, LIMITS.text),
        originalDateIso: cleanIso(raw.originalDateIso),
        receivedAt: cleanString(raw.receivedAt, LIMITS.text),
        recordedAt: cleanIso(raw.recordedAt),
      }
    : null;

/**
 * One editable row of the execution draft.
 *
 * The store treats a draft task as validated-but-opaque: it bounds and cleans
 * the fields so an edit cannot corrupt the document, but it does not know what
 * a ClickUp task is. Shape and meaning belong to onboarding-plan.mjs; edits
 * come from a human in the review UI.
 *
 * `dueState` is the three-way distinction that keeps this tool credible:
 *   dated    a date computable from the signature date
 *   pending  anchored to a call that has not been scheduled yet
 *   gated    blocked on a client action, so it gets no date EVER
 * A due date on a client-gated task goes overdue through no fault of the
 * assignee — and on a team that only ever used ClickUp to tick boxes, false
 * overdue is exactly how a tool stops being trusted.
 */
/* FOUR, not three. "pending" collapsed two different situations: a task
   waiting for a call date it will get, and a task with no scheduling rule
   that will never date itself from anything. 66 of the 92 ads tasks are in
   the second group, and calling them "waiting for kickoff" said the opposite
   of the truth. `pending` is still accepted so an older stored draft loads. */
export const DUE_STATES = Object.freeze([
  "dated",
  "awaiting_anchor",
  "unscheduled",
  "gated",
  "pending",
]);

/** How much to trust `assignee`. Surfaced per row so a reviewer knows which
    ones actually need looking at rather than re-reading all 194. */
export const ASSIGNEE_CONFIDENCE = Object.freeze([
  "certain", // Role maps 1:1 to one person in their own data
  "likely", // maps, but on thin evidence (1-3 observed tasks)
  "heuristic", // split by keyword, e.g. Ads Manager -> Google vs Meta
  "ambiguous", // Role known, person genuinely undecidable
  "unknown", // no Role on the task at all
]);

const sanitizeDraftTask = (raw) => {
  if (!raw || typeof raw !== "object") return null;
  const title = cleanString(raw.title, LIMITS.text);
  if (!title) return null;
  return {
    id: cleanString(raw.id, LIMITS.text) ?? crypto.randomUUID(),
    title,
    /* The destination LIST this task lands in — their real ClickUp list name,
       since a both-offers client gets two lists side by side rather than one
       merged one. */
    template: cleanString(raw.template, LIMITS.text),
    assignee: cleanString(raw.assignee, LIMITS.firstName),
    /* Their own field. Set on 299 of 308 template tasks against only 190 with
       a real assignee, so it is the better source of ownership. */
    role: cleanString(raw.role, LIMITS.firstName),
    phase: cleanString(raw.phase, LIMITS.firstName),
    assigneeConfidence: ASSIGNEE_CONFIDENCE.includes(raw.assigneeConfidence)
      ? raw.assigneeConfidence
      : "unknown",
    assigneeInTemplate: cleanString(raw.assigneeInTemplate, LIMITS.firstName),
    isSubtask: raw.isSubtask === true,
    /* The relationship, not just the fact of one. The draft kept `isSubtask`
       and dropped the parent, so 135 rows read as free-floating tasks with
       names like "Send email update". */
    parentId: cleanString(raw.parentId, LIMITS.text),
    parentTitle: cleanString(raw.parentTitle, LIMITS.text),
    hasDescription: raw.hasDescription === true,
    checklistItems: Array.isArray(raw.checklistItems)
      ? raw.checklistItems.slice(0, 30).map((c) => cleanString(c, LIMITS.text)).filter(Boolean)
      : [],
    templateKey: cleanString(raw.templateKey, LIMITS.text),
    /* Which call moves this row, and whether the rule is theirs or ours. */
    anchorKey: cleanString(raw.anchorKey, LIMITS.firstName),
    scheduleConfirmed: raw.scheduleConfirmed === true,
    scheduleNote: cleanString(raw.scheduleNote, LIMITS.note),
    /* A reviewer's deliberate override survives a reschedule; a calculated
       date is recomputed. Conflating them is why a moved call moved nothing. */
    dateSource: raw.dateSource === "manual" || raw.dateSource === "calculated"
      ? raw.dateSource
      : null,
    /* An unresolved item a reviewer consciously deferred, with a named owner.
       Deferral is allowed; ignoring is not. */
    deferredTo: cleanString(raw.deferredTo, LIMITS.firstName),
    /* Kept on the row so wave 2 can recompute the date from a newly-known
       kickoff anchor WITHOUT rebuilding the draft and discarding a reviewer's
       edits. */
    offsetDays: Number.isInteger(raw.offsetDays) ? raw.offsetDays : null,
    dueDate: cleanString(raw.dueDate, 40),
    dueState: DUE_STATES.includes(raw.dueState) ? raw.dueState : "unscheduled",
    dueAnchor: cleanString(raw.dueAnchor, LIMITS.text),
    note: cleanString(raw.note, LIMITS.note),
    /* A reviewer removing a task sets include:false rather than deleting the
       row, so the approved batch records what was declined as well as what was
       approved. "Will not write" is half of what makes the gate reviewable. */
    include: raw.include !== false,
  };
};

const sanitizeDraft = (raw) => {
  if (!raw || typeof raw !== "object") return null;
  const tasks = Array.isArray(raw.tasks)
    ? raw.tasks.slice(0, LIMITS.draftTasks).map(sanitizeDraftTask).filter(Boolean)
    : [];
  return {
    tasks,
    templates: Array.isArray(raw.templates)
      ? raw.templates.slice(0, LIMITS.offers).map((t) => cleanString(t, LIMITS.text)).filter(Boolean)
      : [],
    generatedAt: cleanIso(raw.generatedAt),
    /* Where the lists would be created: space -> per-client folder -> one list
       per template. Measured from a live client, not assumed. */
    destination: raw.destination && typeof raw.destination === "object"
      ? {
          model: cleanString(raw.destination.model, LIMITS.text),
          space: cleanString(raw.destination.space, LIMITS.text),
          folder: cleanString(raw.destination.folder, LIMITS.text),
          /* Whether the space was READ off the workspace or inferred, and
             whether this package has to go to manual setup. Approval is
             blocked on the second. */
          confirmed: raw.destination.confirmed === true,
          manualSetup: raw.destination.manualSetup === true,
          evidence: cleanString(raw.destination.evidence, LIMITS.note),
          decision: cleanString(raw.destination.decision, LIMITS.note),
        }
      : null,
    lists: Array.isArray(raw.lists)
      ? raw.lists.slice(0, 10).map((l) => ({
          key: cleanString(l?.key, LIMITS.text),
          name: cleanString(l?.name, LIMITS.text),
          listId: cleanString(l?.listId, LIMITS.text),
          taskCount: Number.isInteger(l?.taskCount) ? l.taskCount : null,
        })).filter((l) => l.name)
      : [],
    /* One warning per anchor still waiting, keyed so applying a date can
       retire exactly the line it answers. */
    anchorWarnings:
      raw.anchorWarnings && typeof raw.anchorWarnings === "object"
        ? Object.fromEntries(
            Object.entries(raw.anchorWarnings)
              .slice(0, 12)
              .map(([k, v]) => [cleanString(k, 40), cleanString(v, LIMITS.note)])
              .filter(([k, v]) => k && v),
          )
        : {},
    /* EVERY anchor, not one kickoff. Keyed by anchor id; a key is present
       only once that call has actually been booked. */
    anchors:
      raw.anchors && typeof raw.anchors === "object"
        ? Object.fromEntries(
            Object.entries(raw.anchors)
              .slice(0, 12)
              .map(([k, v]) => [cleanString(k, 40), cleanString(v, 40)])
              .filter(([k, v]) => k && v),
          )
        : {},
    sourceNote: cleanString(raw.sourceNote, LIMITS.note),
    /* True only while the task list is invented. It is false now that the real
       ClickUp templates are read; the UI badge keys off this. */
    placeholder: raw.placeholder === true,
    warnings: Array.isArray(raw.warnings)
      ? raw.warnings.slice(0, 20).map((w) => cleanString(w, LIMITS.note)).filter(Boolean)
      : [],
  };
};

/* ── STEPS 2-4 ─────────────────────────────────────────────────────────────
   The ClickUp draft above is step 1. Steps 2-4 — the Drive folder, the welcome
   email, the Slack channel and its two posts — are the rest of what Gisselle
   does by hand at signature, and they are modelled as a SEPARATE progression
   that only opens once step 1 has been approved.

   Why separate rather than four states on the record: step 1's approval is
   what sets `provisioned`, and `provisioned` is the single flag that makes
   month 2 of a retainer inert (see fingerprintAlert). Folding three more
   approvals into the same state machine would put that flag behind three more
   gates and re-open the recurring-payment trap. So `approve()` keeps its exact
   meaning — "a human authorised this onboarding" — and the stages hang off the
   record afterwards.

   Consequence: the record reaches APPROVED with steps 2-4 still open. That is
   accurate. Approving the ClickUp batch really is the commitment; the Drive
   folder and the Slack posts really do follow it.

   Nothing here writes to Drive, Gmail or Slack. There is no client for any of
   those systems in this codebase — see onboarding-stages.mjs. */
export const STAGE_KEYS = Object.freeze(["drive", "email", "slack"]);
export const STAGE_STATES = Object.freeze(["OPEN", "APPROVED"]);
export const ITEM_STATES = Object.freeze(["ready", "pending", "gated"]);

const sanitizeStageItem = (raw) => {
  if (!raw || typeof raw !== "object") return null;
  const title = cleanString(raw.title, LIMITS.text);
  if (!title) return null;
  return {
    id: cleanString(raw.id, LIMITS.text) ?? crypto.randomUUID(),
    title,
    detail: cleanString(raw.detail, LIMITS.text),
    group: cleanString(raw.group, LIMITS.text),
    source: cleanString(raw.source, LIMITS.firstName) ?? "computed",
    state: ITEM_STATES.includes(raw.state) ? raw.state : "ready",
    confidence: ASSIGNEE_CONFIDENCE.includes(raw.confidence) ? raw.confidence : "certain",
    note: cleanString(raw.note, LIMITS.note),
    include: raw.include !== false,
  };
};

/* A Slack post. `edited` is what stops a reviewer's rewritten body being
   clobbered when the kickoff date arrives and the templates re-render — the
   same rule the task table uses for a hand-set due date. */
const sanitizeStageMessage = (raw) => {
  if (!raw || typeof raw !== "object") return null;
  const body = cleanString(raw.body, LIMITS.messageBody);
  if (!body) return null;
  return {
    id: cleanString(raw.id, LIMITS.text) ?? crypto.randomUUID(),
    label: cleanString(raw.label, LIMITS.text) ?? "Message",
    sourceTask: cleanString(raw.sourceTask, LIMITS.note),
    body,
    edited: raw.edited === true,
    include: raw.include !== false,
  };
};

const sanitizeStagePlan = (raw) => {
  if (!raw || typeof raw !== "object") return null;
  const key = STAGE_KEYS.includes(raw.key) ? raw.key : null;
  if (!key) return null;
  return {
    key,
    order: Number.isInteger(raw.order) ? raw.order : null,
    title: cleanString(raw.title, LIMITS.text) ?? key,
    subtitle: cleanString(raw.subtitle, LIMITS.note),
    system: cleanString(raw.system, LIMITS.text),
    structure:
      raw.structure && typeof raw.structure === "object"
        ? {
            kind: cleanString(raw.structure.kind, LIMITS.firstName) ?? "tree",
            rows: Array.isArray(raw.structure.rows)
              ? raw.structure.rows.slice(0, 40).map((row) => ({
                  depth: Number.isInteger(row?.depth) ? row.depth : 0,
                  text: cleanString(row?.text, LIMITS.text) ?? "",
                  note: cleanString(row?.note, LIMITS.text),
                  chip: cleanString(row?.chip, LIMITS.text),
                  href: cleanString(row?.href, LIMITS.note),
                  label: cleanString(row?.label, LIMITS.text),
                  value: cleanString(row?.value, LIMITS.text),
                  muted: row?.muted === true,
                }))
              : [],
          }
        : { kind: "tree", rows: [] },
    items: Array.isArray(raw.items)
      ? raw.items.slice(0, LIMITS.stageItems).map(sanitizeStageItem).filter(Boolean)
      : [],
    messages: Array.isArray(raw.messages)
      ? raw.messages.slice(0, 6).map(sanitizeStageMessage).filter(Boolean)
      : [],
    /* Which kickoff dates step 4 already holds. Two, not one: their brief
       names both, and on the one live client the two calls were 34 days apart
       in the opposite order to their own timeline — so neither is derivable
       from the other. */
    anchors:
      raw.anchors && typeof raw.anchors === "object"
        ? {
            leadlock: cleanString(raw.anchors.leadlock, 40),
            ads: cleanString(raw.anchors.ads, 40),
          }
        : null,
    /* Null once the blockers clear. Step 4 carries one until both anchors are
       known, because its posts name both kickoff dates. */
    gate:
      raw.gate && typeof raw.gate === "object"
        ? {
            blockedBy: cleanString(raw.gate.blockedBy, LIMITS.firstName),
            label: cleanString(raw.gate.label, LIMITS.text),
            hint: cleanString(raw.gate.hint, LIMITS.note),
          }
        : null,
    warnings: Array.isArray(raw.warnings)
      ? raw.warnings.slice(0, 10).map((w) => cleanString(w, LIMITS.note)).filter(Boolean)
      : [],
    sourceNote: cleanString(raw.sourceNote, LIMITS.note),
  };
};

const sanitizeStage = (raw) => {
  const plan = sanitizeStagePlan(raw?.plan);
  if (!plan) return null;
  return {
    key: plan.key,
    state: STAGE_STATES.includes(raw.state) ? raw.state : "OPEN",
    plan,
    approvedPlan: sanitizeStagePlan(raw?.approvedPlan),
    approvedAt: cleanIso(raw?.approvedAt),
  };
};

const sanitizeStages = (raw) => {
  if (!Array.isArray(raw)) return [];
  const byKey = new Map();
  for (const entry of raw.slice(0, STAGE_KEYS.length)) {
    const stage = sanitizeStage(entry);
    if (stage && !byKey.has(stage.key)) byKey.set(stage.key, stage);
  }
  /* Always in flow order, never in whatever order they were persisted. */
  return STAGE_KEYS.map((key) => byKey.get(key)).filter(Boolean);
};

const sanitizeOffers = (raw) => {
  if (!Array.isArray(raw)) return [];
  const seen = new Set();
  for (const value of raw.slice(0, LIMITS.offers)) {
    if (typeof value === "string" && OFFER_KEYS.includes(value)) seen.add(value);
  }
  return [...seen];
};

const sanitizeClient = (raw) => {
  if (!raw || typeof raw !== "object") return null;
  const projectKey = normalizeProjectKey(raw.projectKey ?? raw.projectName);
  if (!projectKey) return null;
  const state = STATES.includes(raw.state) ? raw.state : "AWAITING_PAIR";
  return {
    projectKey,
    projectName: cleanString(raw.projectName, LIMITS.projectName) ?? projectKey,
    state,
    halves: {
      signed: sanitizeHalf(raw.halves?.signed),
      paid: sanitizeHalf(raw.halves?.paid),
    },
    offers: sanitizeOffers(raw.offers),
    draft: sanitizeDraft(raw.draft),
    approvedBatch: sanitizeDraft(raw.approvedBatch),
    /* Steps 2-4, opened by initStages once step 1 is approved. Empty on every
       record that has not got that far. */
    stages: sanitizeStages(raw.stages),
    provisioned: raw.provisioned === true || state === "APPROVED" || state === "PRE_EXISTING",
    repeatAlerts: Array.isArray(raw.repeatAlerts)
      ? raw.repeatAlerts
          .slice(-LIMITS.repeatAlerts)
          .map((entry) => ({
            kind: entry?.kind === "signed" ? "signed" : "paid",
            fingerprint: cleanString(entry?.fingerprint, LIMITS.text),
            amount: Number.isFinite(entry?.amount) ? entry.amount : null,
            at: cleanIso(entry?.at),
          }))
          .filter((entry) => entry.fingerprint)
      : [],
    firstSeenAt: cleanIso(raw.firstSeenAt),
    pairedAt: cleanIso(raw.pairedAt),
    activatedAt: cleanIso(raw.activatedAt),
    approvedAt: cleanIso(raw.approvedAt),
    ignoredAt: cleanIso(raw.ignoredAt),
    ignoreReason: cleanString(raw.ignoreReason, LIMITS.text),
    ignoreNote: cleanString(raw.ignoreNote, LIMITS.note),
  };
};

const sanitizeState = (parsed) => {
  const next = emptyState();
  if (!parsed || typeof parsed !== "object") return next;
  next.seededAt = cleanIso(parsed.seededAt);
  next.seedNote = cleanString(parsed.seedNote, LIMITS.note);
  next.lastPollAt = cleanIso(parsed.lastPollAt);
  if (Array.isArray(parsed.clients)) {
    const byKey = new Map();
    for (const raw of parsed.clients.slice(0, LIMITS.clients)) {
      const client = sanitizeClient(raw);
      if (client && !byKey.has(client.projectKey)) byKey.set(client.projectKey, client);
    }
    next.clients = [...byKey.values()];
  }
  return next;
};

/**
 * Open (or create) the provisioning store at `filePath`.
 *
 * Reads are synchronous over in-memory state; every mutation persists the
 * whole document. Inject `now` in tests — the half-pair TTL depends on it.
 */
export function createOnboardingStore(filePath, { now = () => Date.now() } = {}) {
  let state = emptyState();
  let durable = true;
  let loadError = null;

  try {
    if (fs.existsSync(filePath)) {
      state = sanitizeState(JSON.parse(fs.readFileSync(filePath, "utf8")));
    }
  } catch (error) {
    /* A corrupt file must not take the server down — start empty and surface
       it, leaving the bad file untouched for inspection. But note the stakes
       are higher here than for leads: an empty store is an UNSEEDED store, so
       ingest refuses rather than re-onboarding the whole client book. */
    loadError = error instanceof Error ? error.message : String(error);
  }

  let writes = Promise.resolve();
  const persist = () => {
    const snapshot = JSON.stringify(state, null, 2);
    writes = writes.then(async () => {
      const tmp = `${filePath}.${crypto.randomUUID()}.tmp`;
      try {
        await fsp.mkdir(path.dirname(filePath), { recursive: true });
        await fsp.writeFile(tmp, snapshot, "utf8");
        await fsp.rename(tmp, filePath); // atomic swap
        durable = true;
      } catch (error) {
        durable = false;
        await fsp.rm(tmp, { force: true }).catch(() => {});
        console.error(
          JSON.stringify({
            event: "onboarding_persist_failed",
            path: filePath,
            error: error instanceof Error ? error.message : String(error),
          }),
        );
      }
    });
    return writes;
  };

  const iso = () => new Date(now()).toISOString();
  const find = (projectKey) => state.clients.find((c) => c.projectKey === projectKey);

  const mustFind = (projectKey) => {
    const key = normalizeProjectKey(projectKey);
    const client = key ? find(key) : null;
    if (!client) throw new OnboardingError("not_found", "No onboarding record for that project.", 404);
    return client;
  };

  return {
    /** The whole board. Newest first — a reviewer works the recent end. */
    read() {
      return {
        seeded: Boolean(state.seededAt),
        seededAt: state.seededAt,
        seedNote: state.seedNote,
        lastPollAt: state.lastPollAt,
        clients: [...state.clients].sort((a, b) =>
          String(b.firstSeenAt ?? "").localeCompare(String(a.firstSeenAt ?? "")),
        ),
      };
    },

    status() {
      const counts = Object.fromEntries(STATES.map((s) => [s, 0]));
      for (const client of state.clients) counts[client.state] += 1;
      return {
        seeded: Boolean(state.seededAt),
        seededAt: state.seededAt,
        lastPollAt: state.lastPollAt,
        total: state.clients.length,
        counts,
        durable,
        loadError,
      };
    },

    /**
     * Mark the existing client book as already onboarded, before the first poll.
     *
     * Idempotent and additive: calling it again adds newly-named projects and
     * refreshes `seededAt` without disturbing records already in flight.
     */
    async seed({ projectNames = [], note } = {}) {
      if (!Array.isArray(projectNames)) {
        throw new OnboardingError("invalid_seed", "projectNames must be an array.");
      }
      const at = iso();
      let added = 0;
      for (const raw of projectNames.slice(0, LIMITS.clients)) {
        const projectKey = normalizeProjectKey(raw);
        if (!projectKey) continue;
        if (find(projectKey)) continue;
        if (state.clients.length >= LIMITS.clients) {
          throw new OnboardingError("limit_reached", `At most ${LIMITS.clients} clients.`, 409);
        }
        state.clients.push(
          sanitizeClient({
            projectKey,
            projectName: cleanString(raw, LIMITS.projectName) ?? projectKey,
            state: "PRE_EXISTING",
            provisioned: true,
            firstSeenAt: at,
          }),
        );
        added += 1;
      }
      state.seededAt = at;
      state.seedNote = cleanString(note, LIMITS.note) ?? state.seedNote;
      await persist();
      return { added, seededAt: at, total: state.clients.length };
    },

    /**
     * Correlate one parsed alert into the board.
     *
     * Returns `{ outcome, client }`. Every outcome is a deliberate branch —
     * see the three corrections in this file's header.
     */
    async ingest(alert, { messageId } = {}) {
      if (!alert || typeof alert !== "object" || !alert.projectKey || !alert.kind) {
        return { outcome: "rejected", client: null };
      }
      if (!state.seededAt) {
        /* Refusing is the whole point. An unseeded first poll would read 90
           days of history as a queue of new signings. */
        return { outcome: "not_seeded", client: null };
      }

      const kind = alert.kind === "signed" ? "signed" : "paid";
      const projectKey = normalizeProjectKey(alert.projectKey);
      if (!projectKey) return { outcome: "rejected", client: null };

      const at = iso();
      const fingerprint = fingerprintAlert(alert, messageId);
      state.lastPollAt = at;

      let client = find(projectKey);

      if (!client) {
        if (state.clients.length >= LIMITS.clients) {
          throw new OnboardingError("limit_reached", `At most ${LIMITS.clients} clients.`, 409);
        }
        client = sanitizeClient({
          projectKey,
          projectName: alert.projectName,
          state: "AWAITING_PAIR",
          firstSeenAt: at,
        });
        client.halves[kind] = halfFromAlert(alert, fingerprint, at);
        state.clients.push(client);
        await persist();
        return { outcome: "half_pending", client };
      }

      /* Already onboarded — the recurring-payment guard. Month 2 of a retainer
         lands here with a subject indistinguishable from month 1's. Recorded
         on the audit trail rather than dropped, so a reviewer can see that the
         guard fired and why. */
      if (client.provisioned) {
        const known = client.halves[kind]?.fingerprint === fingerprint;
        if (!known) {
          client.repeatAlerts.push({ kind, fingerprint, amount: alert.amount ?? null, at });
          if (client.repeatAlerts.length > LIMITS.repeatAlerts) client.repeatAlerts.shift();
          await persist();
          return { outcome: "recurring_payment", client };
        }
        return { outcome: "already_provisioned", client };
      }

      /* Idempotency for a 15-minute poll re-reading the same mailbox. */
      if (client.halves[kind]?.fingerprint === fingerprint) {
        return { outcome: "duplicate_half", client };
      }

      const alreadyHadThisKind = Boolean(client.halves[kind]);
      client.halves[kind] = halfFromAlert(alert, fingerprint, at);
      if (!client.projectName) client.projectName = alert.projectName;

      const whole = Boolean(client.halves.signed && client.halves.paid);
      if (whole && client.state === "AWAITING_PAIR") {
        client.state = "READY";
        client.pairedAt = at;
        await persist();
        return { outcome: "pair_completed", client };
      }

      await persist();
      return {
        outcome: alreadyHadThisKind ? "half_replaced" : "half_pending",
        client,
      };
    },

    /**
     * A human opens a READY record, picks the offer set and receives a draft.
     *
     * Offer selection is REQUIRED and cannot be derived: the offer name appears
     * on neither alert subject. `draft` is built by the caller from
     * onboarding-plan.mjs and stored here for editing.
     */
    async activate(projectKey, { offers, draft } = {}) {
      const client = mustFind(projectKey);
      if (client.state !== "READY" && client.state !== "DRAFTED") {
        throw new OnboardingError(
          "invalid_state",
          `Cannot activate a record in state ${client.state}.`,
          409,
        );
      }
      const chosen = sanitizeOffers(offers);
      if (!chosen.length) {
        throw new OnboardingError("invalid_offers", "At least one offer must be selected.");
      }
      client.offers = chosen;
      client.draft = sanitizeDraft(draft) ?? { tasks: [], templates: [], generatedAt: iso(), placeholder: true, warnings: [] };
      client.state = "DRAFTED";
      client.activatedAt = iso();
      await persist();
      return client;
    },

    /**
     * Persist a reviewer's edits to the draft, without approving it.
     *
     * Takes an options object rather than a bare draft so all three mutators
     * — activate, updateDraft, approve — have the same call shape. They did
     * not, and the inconsistency immediately cost a silently-wrong call.
     */
    async updateDraft(projectKey, { draft } = {}) {
      const client = mustFind(projectKey);
      if (client.state !== "DRAFTED") {
        throw new OnboardingError(
          "invalid_state",
          `Only a DRAFTED record can be edited (this one is ${client.state}).`,
          409,
        );
      }
      const next = sanitizeDraft(draft);
      if (!next) throw new OnboardingError("invalid_draft", "A draft is required.");
      client.draft = next;
      await persist();
      return client;
    },

    /**
     * WAVE 2+ — a call gets booked, and the tasks hanging off THAT anchor
     * compute themselves.
     *
     * Three corrections to the previous `applyKickoffDate`:
     *
     *  1. ONE ANCHOR AT A TIME. It applied a single "kickoff" to every
     *     phase-driven task on both tracks, which invented LeadLock deadlines
     *     from an ads call. Only tasks whose `anchorKey` matches move.
     *
     *  2. IT ACCEPTS AN APPROVED RECORD. It required DRAFTED, so approving
     *     the setup batch made the scheduling wave impossible — which is the
     *     wave the whole design exists for.
     *
     *  3. IT PRESERVES ONLY DELIBERATE OVERRIDES. It skipped every task that
     *     already had a date, including dates it had calculated itself, so a
     *     postponed call could not move anything. Now `dateSource: "manual"`
     *     is preserved and `"calculated"` is recomputed.
     */
    async applyAnchorDate(projectKey, { anchor, date } = {}) {
      const client = mustFind(projectKey);
      if (client.state !== "DRAFTED" && client.state !== "APPROVED" && client.state !== "SCHEDULED") {
        throw new OnboardingError(
          "invalid_state",
          `Only a drafted, approved or scheduled record can be scheduled (this one is ${client.state}).`,
          409,
        );
      }
      const iso = cleanIso(date);
      if (!iso) throw new OnboardingError("invalid_date", "A valid date is required.");
      if (!anchor || typeof anchor !== "string") {
        throw new OnboardingError("invalid_anchor", "An anchor is required.");
      }
      if (!client.draft) throw new OnboardingError("invalid_draft", "No draft to schedule.");

      const base = new Date(iso);
      let computed = 0;
      let preserved = 0;
      client.draft.tasks = client.draft.tasks.map((task) => {
        if (task.anchorKey !== anchor) return task;
        if (task.dueState === "gated") return task;
        if (task.offsetDays === null || task.offsetDays === undefined) return task;
        if (task.dateSource === "manual") {
          preserved += 1;
          return task;
        }
        const due = new Date(base);
        due.setUTCDate(due.getUTCDate() + task.offsetDays);
        computed += 1;
        return {
          ...task,
          dueState: "dated",
          dueDate: due.toISOString().slice(0, 10),
          dateSource: "calculated",
        };
      });
      client.draft.anchors = { ...(client.draft.anchors ?? {}), [anchor]: iso.slice(0, 10) };
      /* Drop the "waiting on this anchor" warning now that it has a date,
         so the banner does not contradict the row above it. */
      const remaining = { ...(client.draft.anchorWarnings ?? {}) };
      delete remaining[anchor];
      client.draft.anchorWarnings = remaining;
      /* Re-entering the scheduling wave on an already-scheduled record puts
         it back to APPROVED so the new dates are approved deliberately. */
      if (client.state === "SCHEDULED") client.state = "APPROVED";
      await persist();
      return { client, computed, preserved };
    },

    /**
     * Record a human's batch approval. TWO WAVES, not one.
     *
     * `wave: "setup"` (default) approves the pre-booking batch — the lists,
     * the owners, the tasks. `wave: "schedule"` approves the dates once the
     * calls have been booked. Separating them is what lets a client sign
     * before booking anything, which is the ordinary case.
     *
     * No ClickUp request is issued in either wave, by design: this build
     * stops at approval and raises a persistent notification. `approvedBatch`
     * is a frozen copy of exactly what was approved — including the rows a
     * reviewer excluded — so the record answers "what did a human actually
     * authorise?" rather than "what did the planner propose?".
     */
    async approve(projectKey, { draft, wave = "setup" } = {}) {
      const client = mustFind(projectKey);
      const allowed = wave === "schedule" ? ["APPROVED", "DRAFTED"] : ["DRAFTED"];
      if (!allowed.includes(client.state)) {
        throw new OnboardingError(
          "invalid_state",
          `Cannot approve the ${wave} wave from state ${client.state}.`,
          409,
        );
      }
      const batch = sanitizeDraft(draft) ?? client.draft;
      if (!batch || !batch.tasks.length) {
        throw new OnboardingError("invalid_draft", "Nothing to approve.");
      }
      client.approvedBatch = batch;
      client.draft = batch;
      client.state = wave === "schedule" ? "SCHEDULED" : "APPROVED";
      client.approvedAt = client.approvedAt ?? iso();
      if (wave === "schedule") client.scheduleApprovedAt = iso();
      /* Set on the FIRST approval and only there. It is what makes month 2
         of a retainer inert. */
      client.provisioned = true;
      await persist();
      return client;
    },

    /* ── STEPS 2-4 ───────────────────────────────────────────────────────
       Open the Drive / email / Slack steps on a record whose ClickUp batch has
       just been approved. Idempotent: calling it twice does not discard a
       reviewer's edits, because the second call finds stages already there and
       leaves them. That matters — the route calls it on every approval, and an
       approval can be retried. */
    async initStages(projectKey, { stages } = {}) {
      const client = mustFind(projectKey);
      if (client.state !== "APPROVED") {
        throw new OnboardingError(
          "invalid_state",
          `Steps 2-4 open once the ClickUp batch is approved (this record is ${client.state}).`,
          409,
        );
      }
      if (client.stages?.length) return client;
      const next = sanitizeStages(
        (stages ?? []).map((plan) => ({ key: plan?.key, state: "OPEN", plan })),
      );
      if (!next.length) throw new OnboardingError("invalid_stage", "No step plans supplied.");
      client.stages = next;
      await persist();
      return client;
    },

    /** A reviewer's edits to one step, saved without approving it. */
    async updateStage(projectKey, { stage, plan } = {}) {
      const client = mustFind(projectKey);
      const entry = (client.stages ?? []).find((s) => s.key === stage);
      if (!entry) throw new OnboardingError("unknown_stage", `No step "${stage}" on this record.`, 404);
      if (entry.state === "APPROVED") {
        throw new OnboardingError("invalid_state", `Step "${stage}" is already approved.`, 409);
      }
      const next = sanitizeStagePlan(plan);
      if (!next || next.key !== stage) {
        throw new OnboardingError("invalid_stage", "A plan for this step is required.");
      }
      entry.plan = next;
      await persist();
      return client;
    },

    /**
     * Approve one of steps 2-4. STILL TERMINAL — nothing is written.
     *
     * Keeps `approvedPlan` as a frozen copy including the rows a reviewer
     * excluded, for the same reason step 1 keeps `approvedBatch`: the record
     * has to answer what a human authorised, not what the planner proposed.
     *
     * A step carrying a gate cannot be approved. Step 4's posts name the
     * kickoff dates, so approving it while the gate stands would authorise
     * sending two messages full of "(DATE)".
     */
    async approveStage(projectKey, { stage, plan } = {}) {
      const client = mustFind(projectKey);
      const entry = (client.stages ?? []).find((s) => s.key === stage);
      if (!entry) throw new OnboardingError("unknown_stage", `No step "${stage}" on this record.`, 404);
      if (entry.state === "APPROVED") {
        throw new OnboardingError("invalid_state", `Step "${stage}" is already approved.`, 409);
      }
      const next = sanitizeStagePlan(plan) ?? entry.plan;
      if (next.gate) {
        throw new OnboardingError(
          "stage_gated",
          next.gate.label ?? `Step "${stage}" is still blocked.`,
          409,
        );
      }
      entry.plan = next;
      entry.approvedPlan = next;
      entry.state = "APPROVED";
      entry.approvedAt = iso();
      await persist();
      return client;
    },

    /**
     * The kickoff booking, arriving AFTER step 1 was approved.
     *
     * `applyKickoffDate` above only runs on a DRAFTED record, which is right
     * for wave 2 of step 1. But a reviewer who approved step 1 without a date
     * and then reached step 4's gate needs a way through it, so this does the
     * same arithmetic on an APPROVED record — over the live draft and the
     * frozen approved batch both, since after approval they are the same
     * authorisation seen twice.
     *
     * Re-rendering step 4's posts from the new anchor is the CALLER's job (see
     * rehydrateSlackStage), so this module keeps knowing nothing about the
     * templates.
     */
    async recordKickoff(projectKey, { kickoffDate } = {}) {
      const client = mustFind(projectKey);
      if (client.state !== "APPROVED") {
        throw new OnboardingError(
          "invalid_state",
          `Only an approved record schedules from here (this one is ${client.state}).`,
          409,
        );
      }
      const anchor = cleanIso(kickoffDate);
      if (!anchor) throw new OnboardingError("invalid_date", "A valid kickoff date is required.");
      const day = anchor.slice(0, 10);
      const base = new Date(anchor);
      let computed = 0;

      /* `approve()` assigns the SAME object to both `draft` and
         `approvedBatch`, so after approval these are usually one batch seen
         twice. Deduping by identity is what stops the count being doubled —
         and stops it being halved on the records where they genuinely are two
         objects, which is what an unconditional /2 got wrong. */
      const batches = new Set([client.draft, client.approvedBatch].filter(Boolean));
      for (const batch of batches) {
        batch.tasks = batch.tasks.map((task) => {
          if (task.dueState === "gated") return task;
          if (task.offsetDays === null || task.dueDate) return task;
          const due = new Date(base);
          due.setUTCDate(due.getUTCDate() + task.offsetDays);
          computed += 1;
          return { ...task, dueState: "dated", dueDate: due.toISOString().slice(0, 10) };
        });
        batch.kickoffDate = day;
        batch.warnings = (batch.warnings ?? []).filter((w) => !/kickoff call not booked/i.test(w));
      }

      await persist();
      return { client, computed };
    },

    async ignore(projectKey, { reason = "dismissed", note } = {}) {
      const client = mustFind(projectKey);
      if (client.state === "APPROVED" || client.state === "SCHEDULED") {
        throw new OnboardingError("invalid_state", "An approved record cannot be ignored.", 409);
      }
      client.state = "IGNORED";
      client.ignoredAt = iso();
      client.ignoreReason = IGNORE_REASONS[reason] ? reason : "dismissed";
      client.ignoreNote = cleanString(note, LIMITS.note);
      await persist();
      return client;
    },

    /**
     * Withdraw half-pairs that never completed.
     *
     * A half-pair is a real state, not an error — a client who signed but has
     * not paid is genuinely mid-signature, and that is exactly the question
     * ("which signed clients haven't paid yet?") that currently lives only in
     * Whitney's head. But it cannot wait forever, or the board fills with
     * abandoned deals.
     */
    async expireStalePairs({ ttlDays = DEFAULT_HALF_PAIR_TTL_DAYS } = {}) {
      const cutoff = now() - ttlDays * 24 * 60 * 60 * 1000;
      const expired = [];
      for (const client of state.clients) {
        if (client.state !== "AWAITING_PAIR") continue;
        const seen = Date.parse(client.firstSeenAt ?? "");
        if (Number.isNaN(seen) || seen > cutoff) continue;
        client.state = "IGNORED";
        client.ignoredAt = iso();
        client.ignoreReason = "half_pair_timeout";
        expired.push(client.projectKey);
      }
      if (expired.length) await persist();
      return { expired };
    },

    /**
     * Await every queued write.
     *
     * Needed by callers that must know the document is on disk — and by tests,
     * where an in-flight rename otherwise races the temp directory's teardown
     * and logs a spurious ENOENT.
     */
    flush() {
      return writes;
    },

    /** Test seam. */
    async reset() {
      state = emptyState();
      await persist();
    },
  };
}
