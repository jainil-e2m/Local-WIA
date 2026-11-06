/* ────────────────────────────────────────────────────────────────
   Lead Magnet lead store — a single JSON document on disk.

   INTERIM by design: this stands in for the three per-service Lead
   Magnet backends (each with its own DB) until they exist. The funnel
   pages POST captured leads here and /leadmagnetdashboard reads them
   back, so the end-to-end flow is testable with no external service.
   When the real backends land, the funnel's POST target and the
   dashboard's API client re-point and this module retires — see
   Lead_Magnet/leadmagnet_central_dashboard_integration.md.

   Same durability contract as bookmarks-store.mjs: state lives in
   memory, mirrored to disk with atomic writes (temp file + rename)
   serialized through one promise chain. Point LEADS_FILE at a mounted
   volume to survive redeploys.
   ──────────────────────────────────────────────────────────────── */

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { normalizeUrl } from "./bookmarks-store.mjs";
import { chooseLeadForBooking } from "./meeting-match.mjs";

/** The only sources the Lead Magnet funnels produce. `seo_audit` and
    `contact_form` are retired site-wide and are rejected on write. */
export const LEAD_TYPES = new Set(["technical_seo", "onpage_seo", "ai_seo"]);

export const LIMITS = {
  leads: 2000, // bounds the file at ~1 MB of pure lead JSON
  nameLength: 200,
  emailLength: 254,
  phoneLength: 50,
  gradeLength: 8,
  cronLength: 40,
  notesLength: 2000,
  auditIdLength: 80,
};

// Deliberately simple: "has one @ with something around it". Real validation
// is the funnel's job; this only keeps junk rows out of the store.
const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const emptyState = () => ({ version: 1, nextSeq: 1, leads: [] });

const cleanString = (raw, maxLength) =>
  typeof raw === "string" ? raw.trim().slice(0, maxLength) : "";

/** Millisecond-precision ISO 8601 UTC, or null. */
function cleanIsoDate(raw) {
  if (typeof raw !== "string") return null;
  const time = Date.parse(raw);
  if (Number.isNaN(time)) return null;
  return new Date(time).toISOString();
}

/**
 * Whitelist + coerce a details payload. Unknown keys are dropped (the funnel
 * may evolve ahead of this store), invalid values are dropped field-by-field
 * rather than failing the lead. Returns undefined when nothing survives.
 */
export function sanitizeDetails(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return undefined;
  const details = {};

  const score = Number(raw.score);
  if (Number.isFinite(score) && score >= 0 && score <= 100) details.score = Math.round(score);

  const grade = cleanString(raw.grade, LIMITS.gradeLength);
  if (grade) details.grade = grade;

  /* `opportunities` and `info` arrived with the real Technical SEO audit, which
     reports five severities where this store originally carried three. Without
     them the console would show 15 of a typical 34 findings and silently drop
     the rest. Older leads simply lack the keys, which sanitizeDetails already
     handles field-by-field. */
  for (const key of ["passed", "warnings", "critical", "opportunities", "info"]) {
    const count = Number(raw[key]);
    if (Number.isInteger(count) && count >= 0 && count <= 10_000) details[key] = count;
  }

  /* Identifier of the Technical SEO audit behind this lead.
     The audit service keeps the report durably in its own database, so storing
     the id is enough to reach both formats later — copying the report itself
     into this JSON document would blow the ~1 MB budget LIMITS.leads assumes.
     Shape-checked rather than length-checked alone: it is rendered into a URL. */
  const auditId = cleanString(raw.audit_id, LIMITS.auditIdLength);
  /* Products mint different shapes: Technical SEO and AI SEO use `audit_<hex>`;
     the On-Page snapshot service mints bare 32-char hex, with no prefix and no
     hyphens (e.g. e990bb5318f84bffa13d7d999c4387b2 -- not a UUID). The check was
     `^audit_...` and so dropped every On-Page id SILENTLY: the field simply
     vanished, and those leads could not be correlated back to their audit at all.
     What it is really defending is the URL this gets rendered into, so it now
     constrains the character set instead of the prefix: no slash, dot, colon or
     percent can get through. */
  if (/^[A-Za-z0-9_-]+$/.test(auditId)) details.audit_id = auditId;

  const cron = cleanString(raw.scheduler_cron, LIMITS.cronLength);
  if (cron) details.scheduler_cron = cron;

  const auditTime = cleanIsoDate(raw.last_audit_time);
  if (auditTime) details.last_audit_time = auditTime;

  return Object.keys(details).length > 0 ? details : undefined;
}

/** Drop anything malformed rather than trusting a hand-edited file. */
/**
 * Validate a stored booking.
 *
 * Mirrors sanitizeDetails: the JSON file is a plain-text store an operator can
 * open, so nothing from it is trusted on the way back in. A booking with no
 * usable start time is dropped whole rather than rendered as "Meeting on:
 * Invalid Date".
 */
export function sanitizeMeeting(raw) {
  if (!raw || typeof raw !== "object") return null;
  const startsAt = cleanIsoDate(raw.startsAt);
  if (!startsAt) return null;

  const meeting = { startsAt };
  const eventId = cleanString(raw.eventId, 128);
  if (eventId) meeting.eventId = eventId;
  if (Number.isInteger(raw.durationMinutes) && raw.durationMinutes > 0) {
    meeting.durationMinutes = raw.durationMinutes;
  }
  const timezone = cleanString(raw.timezone, 64);
  if (timezone) meeting.timezone = timezone;
  meeting.status = cleanString(raw.status, 32) === "cancelled" ? "cancelled" : "booked";
  // Same XSS boundary as domainUrl: this becomes an href in the console.
  const url = normalizeUrl(raw.url);
  if (url) meeting.url = url;
  const bookedEmail = cleanString(raw.bookedEmail, LIMITS.emailLength).toLowerCase();
  if (bookedEmail) meeting.bookedEmail = bookedEmail;
  const bookedName = cleanString(raw.bookedName, LIMITS.nameLength);
  if (bookedName) meeting.bookedName = bookedName;
  /* Answers to the invite's own questions. Re-validated pair by pair: this file
     is editable by hand, and the console renders these straight into the page. */
  if (Array.isArray(raw.questionAnswers)) {
    const answers = [];
    for (const entry of raw.questionAnswers.slice(0, 5)) {
      if (!entry || typeof entry !== "object") continue;
      const answer = cleanString(entry.answer, 2000);
      if (!answer) continue;
      const question = cleanString(entry.question, 300);
      answers.push(question ? { question, answer } : { answer });
    }
    if (answers.length) meeting.questionAnswers = answers;
  }
  return meeting;
}

function sanitizeState(parsed) {
  if (!parsed || typeof parsed !== "object") return emptyState();
  const rows = Array.isArray(parsed.leads) ? parsed.leads : [];

  const leads = rows
    .map((row) => {
      if (!row || typeof row !== "object" || typeof row.id !== "string") return null;
      const name = cleanString(row.name, LIMITS.nameLength);
      const email = cleanString(row.email, LIMITS.emailLength).toLowerCase();
      if (!name || !EMAIL_SHAPE.test(email) || !LEAD_TYPES.has(row.type)) return null;
      const timestamp = cleanIsoDate(row.timestamp);
      if (!timestamp) return null;

      const lead = { id: row.id, name, email, type: row.type, timestamp };
      // Display number. Kept separate from `id`: the id is the primary key used
      // for every PATCH/DELETE, so it must never be renumbered.
      if (Number.isInteger(row.seq) && row.seq > 0) lead.seq = row.seq;
      const phone = cleanString(row.phone, LIMITS.phoneLength);
      if (phone) lead.phone = phone;
      // normalizeUrl is the same XSS boundary bookmarks use: these URLs are
      // rendered straight into an href on the dashboard.
      const domainUrl = normalizeUrl(row.domainUrl);
      if (domainUrl) lead.domainUrl = domainUrl;
      const details = sanitizeDetails(row.details);
      if (details) lead.details = details;
      const notes = cleanString(row.notes, LIMITS.notesLength);
      if (notes) lead.notes = notes;
      // Preserved on reload: dropping these would orphan every in-flight audit
      // from the lead that triggered it.
      const captureId = cleanString(row.captureId, 64);
      if (captureId) lead.captureId = captureId;
      const auditId = cleanString(row.auditId, 64);
      if (auditId) lead.auditId = auditId;
      const auditStatus = cleanString(row.auditStatus, 32);
      if (auditStatus) lead.auditStatus = auditStatus;
      /* Provenance for auditId, and it has to survive a reload for the same
         reason auditId does: without it a restart would turn every genuinely
         running full audit back into a funnel-only lead. */
      const fullAuditStartedAt = cleanIsoDate(row.fullAuditStartedAt);
      if (fullAuditStartedAt) lead.fullAuditStartedAt = fullAuditStartedAt;
      // Why a failed run's reason survives a reload too: without it the console
      // would show a run that stopped with no way to say why, which reads
      // identically to the dashboard itself having lost the result.
      const auditError = cleanString(row.auditError, 500);
      if (auditError) lead.auditError = auditError;
      /* Only ever persisted as false — an absent field means active, matching
         the Postgres column's DEFAULT TRUE. Dropping this on reload would
         un-delete every hidden lead on the next restart. */
      if (row.leadActive === false) lead.leadActive = false;
      /* Re-validated on read like every other stored URL: this file is editable
         by hand and the value becomes an href in the console. */
      const reportUrl = normalizeUrl(row.auditReportUrl);
      if (reportUrl) lead.auditReportUrl = reportUrl;
      /* The booked call, re-validated field by field like everything else here:
         this file is on disk and a hand-edit must not be able to put an unparsed
         date or a hostile URL in front of the console. */
      const meeting = sanitizeMeeting(row.meeting);
      if (meeting) {
        lead.meeting = meeting;
        if (meeting.eventId) lead.meetingEventId = meeting.eventId;
      }
      return lead;
    })
    .filter(Boolean)
    .slice(0, LIMITS.leads);

  /* Display numbers. Leads written before `seq` existed get one here, assigned
     oldest-first so the earliest capture reads as lead_1. `nextSeq` is stored
     rather than derived from max(seq): deleting the newest lead must not hand
     its number to the next one, or two different leads would share an id in
     someone's notes. */
  const highest = leads.reduce((max, lead) => Math.max(max, lead.seq ?? 0), 0);
  let nextSeq =
    Number.isInteger(parsed.nextSeq) && parsed.nextSeq > highest ? parsed.nextSeq : highest + 1;
  for (const lead of [...leads].sort((a, b) => a.timestamp.localeCompare(b.timestamp))) {
    if (lead.seq === undefined) lead.seq = nextSeq++;
  }

  return { version: 1, nextSeq, leads };
}

export class LeadsError extends Error {
  constructor(code, message, status = 400) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

/**
 * Open (or create) the store at `filePath`.
 *
 * Reads are synchronous over in-memory state; every mutation persists the
 * whole document. Leads are returned newest-first — the dashboard's
 * "most recent audit for this domain" lookup depends on that ordering.
 */
export function createLeadsStore(filePath, { now = () => Date.now() } = {}) {
  let state = emptyState();
  let durable = true;
  let loadError = null;
  let migrated = false;

  try {
    if (fs.existsSync(filePath)) {
      const raw = JSON.parse(fs.readFileSync(filePath, "utf8"));
      state = sanitizeState(raw);
      // Did this document predate `seq`/`nextSeq`? If so the numbers were just
      // invented in memory; write them out once so they become authoritative
      // rather than being re-derived (and potentially re-shuffled) every boot.
      migrated =
        !Number.isInteger(raw?.nextSeq) ||
        (Array.isArray(raw?.leads) && raw.leads.some((row) => !Number.isInteger(row?.seq)));
    }
  } catch (error) {
    // A corrupt file must not take the whole server down — start empty and
    // surface it, leaving the bad file untouched for inspection.
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
            event: "leads_persist_failed",
            path: filePath,
            error: error instanceof Error ? error.message : String(error),
          }),
        );
      }
    });
    return writes;
  };

  // Flush the one-time seq backfill. Safe to fire before any request: writes
  // are serialized through the same queue every mutation uses.
  if (migrated) persist();

  /* Mirrors the Postgres store's fetchById: a hidden lead reads as absent.
     `leadActive !== false` rather than `=== true` so rows written before the
     field existed stay visible. */
  const isActive = (lead) => lead.leadActive !== false;
  const findLead = (id) => state.leads.find((lead) => lead.id === id && isActive(lead));

  return {
    /** All leads, newest first. */
    read() {
      return {
        leads: state.leads
          .filter(isActive)
          .sort((a, b) => b.timestamp.localeCompare(a.timestamp)),
      };
    },

    /** Diagnostics for the boot log / health surface. */
    status() {
      return {
        path: filePath,
        durable,
        loadError,
        counts: { leads: state.leads.filter(isActive).length },
      };
    },

    /**
     * Validate + store one captured lead. Name, email and type are the
     * identity of a lead and are required; a malformed domainUrl is dropped
     * rather than rejected — losing the contact because of a typo'd website
     * field would defeat the whole capture funnel.
     *
     * `notes` is deliberately NOT accepted here. It is dashboard-authored
     * annotation, and this path is reachable from the public capture endpoint —
     * honouring it would let anyone write arbitrary text into the CRM. Notes
     * are settable only through updateLead, behind a session.
     */
    async createLead({ name, email, phone, domainUrl, type, details, captureId }) {
      if (state.leads.length >= LIMITS.leads) {
        throw new LeadsError("limit_reached", `At most ${LIMITS.leads} leads.`, 409);
      }
      const cleanName = cleanString(name, LIMITS.nameLength);
      if (!cleanName) throw new LeadsError("invalid_name", "A contact name is required.");
      const cleanEmail = cleanString(email, LIMITS.emailLength).toLowerCase();
      if (!EMAIL_SHAPE.test(cleanEmail)) {
        throw new LeadsError("invalid_email", "A valid email address is required.");
      }
      if (!LEAD_TYPES.has(type)) {
        throw new LeadsError("invalid_type", `type must be one of: ${[...LEAD_TYPES].join(", ")}.`);
      }

      const cleanPhone = cleanString(phone, LIMITS.phoneLength);
      const cleanDomain = normalizeUrl(domainUrl);
      const cleanDetails = sanitizeDetails(details);
      // Correlation key minted by the funnel and sent to the audit intake too.
      // Without it a pushed summary has nothing to match on.
      const cleanCapture = cleanString(captureId, 64);

      /* A capture id that is already here is the SAME submission arriving twice,
         not a second prospect. The On-Page funnel saves once at form submit and
         again when the audit resolves, reusing its capture id — so without this
         branch every On-Page submission produced TWO lead rows here, and a unique
         violation on the Postgres store (leads-db.mjs), which captureRemotely
         swallows. Either way the audit summary never landed.

         Merge rather than replace: the second save carries the metrics and the
         first carries the identity, and a later save that happens to omit a field
         must not blank what is already stored. */
      if (cleanCapture) {
        const existing = state.leads.find((row) => row.captureId === cleanCapture);
        if (existing) {
          if (cleanPhone) existing.phone = cleanPhone;
          if (cleanDomain) existing.domainUrl = cleanDomain;
          if (cleanDetails) existing.details = { ...(existing.details ?? {}), ...cleanDetails };
          await persist();
          return existing;
        }
      }

      const lead = {
        id: `lead_${crypto.randomUUID()}`,
        seq: state.nextSeq++,
        name: cleanName,
        email: cleanEmail,
        type,
        timestamp: new Date(now()).toISOString(),
      };
      if (cleanPhone) lead.phone = cleanPhone;
      if (cleanDomain) lead.domainUrl = cleanDomain;
      if (cleanDetails) lead.details = cleanDetails;
      if (cleanCapture) lead.captureId = cleanCapture;

      state.leads.unshift(lead);
      await persist();
      return lead;
    },

    /**
     * Patch one lead. Contact fields replace; `details` merges per-field so
     * the dashboard's deep-dive audit can update scores without resending
     * the whole object. `id`, `type` and `timestamp` are immutable.
     *
     * `notes` is the one field owned by the dashboard operator rather than the
     * audit — this is the only way it can be written.
     */
    /** One lead by id, or null. Mirrors the Postgres store's method so the
        full-audit routes never branch on which backend is mounted. */
    async getLead(id) {
      return findLead(id) ?? null;
    },

    async updateLead(id, patch = {}) {
      const lead = findLead(id);
      if (!lead) throw new LeadsError("not_found", "Lead not found.", 404);

      if (patch.name !== undefined) {
        const cleanName = cleanString(patch.name, LIMITS.nameLength);
        if (!cleanName) throw new LeadsError("invalid_name", "A contact name is required.");
        lead.name = cleanName;
      }
      if (patch.email !== undefined) {
        const cleanEmail = cleanString(patch.email, LIMITS.emailLength).toLowerCase();
        if (!EMAIL_SHAPE.test(cleanEmail)) {
          throw new LeadsError("invalid_email", "A valid email address is required.");
        }
        lead.email = cleanEmail;
      }
      if (patch.phone !== undefined) {
        const cleanPhone = cleanString(patch.phone, LIMITS.phoneLength);
        if (cleanPhone) lead.phone = cleanPhone;
        else delete lead.phone;
      }
      if (patch.domainUrl !== undefined) {
        const cleanDomain = normalizeUrl(patch.domainUrl);
        if (cleanDomain) lead.domainUrl = cleanDomain;
        else delete lead.domainUrl;
      }
      if (patch.details !== undefined) {
        const merged = sanitizeDetails({ ...lead.details, ...patch.details });
        if (merged) lead.details = merged;
        else delete lead.details;
      }
      if (patch.notes !== undefined) {
        // Clearing the box removes the field rather than storing an empty string.
        const notes = cleanString(patch.notes, LIMITS.notesLength);
        if (notes) lead.notes = notes;
        else delete lead.notes;
      }

      await persist();
      return lead;
    },

    /**
     * Record the lifecycle of a full audit against a lead.
     *
     * Mirrors the Postgres store's method so the route above it never branches on
     * which backend is mounted. See leads-db.mjs for why this is separate from
     * updateLead rather than an extension of it.
     *
     * This store has no columns, so the run lands on the lead object directly
     * (auditId / auditStatus, exactly as rowToLead projects them under Postgres)
     * and the FULL_AUDIT_COMPLETED sentinel goes into `details`, which is where
     * this store has always kept it.
     */
    async setAuditRun(id, patch = {}) {
      const lead = findLead(id);
      if (!lead) throw new LeadsError("not_found", "Lead not found.", 404);

      if (patch.auditId !== undefined) {
        const auditId = cleanString(patch.auditId, 64);
        if (auditId) lead.auditId = auditId;
        else delete lead.auditId;
      }
      if (patch.auditStatus !== undefined) {
        const status = cleanString(patch.auditStatus, 32);
        if (status) lead.auditStatus = status;
        else delete lead.auditStatus;
      }
      if (patch.auditError !== undefined) {
        const error = cleanString(patch.auditError, 500);
        if (error) lead.auditError = error;
        else delete lead.auditError;
      }
      if (patch.reportUrl !== undefined) {
        const url = cleanString(patch.reportUrl, 2000);
        if (url) lead.auditReportUrl = url;
        else delete lead.auditReportUrl;
      }
      /* Only the start route sets this; applyAuditSummary never does. That is
         the whole mechanism separating a funnel-pushed audit id from a full run
         started here — see leadmagnet-schema.sql for the failure it retires. */
      if (patch.fullAuditStartedAt !== undefined) {
        const startedAt = cleanIsoDate(patch.fullAuditStartedAt);
        if (startedAt) lead.fullAuditStartedAt = startedAt;
        else delete lead.fullAuditStartedAt;
      }
      if (patch.completedAt !== undefined || patch.fullAuditCompleted !== undefined) {
        const details = { ...lead.details };
        if (patch.completedAt !== undefined) {
          const iso = cleanIsoDate(patch.completedAt);
          if (iso) details.last_audit_time = iso;
        }
        if (patch.fullAuditCompleted !== undefined) {
          if (patch.fullAuditCompleted) details.scheduler_cron = "FULL_AUDIT_COMPLETED";
          else delete details.scheduler_cron;
        }
        if (Object.keys(details).length > 0) lead.details = details;
        else delete lead.details;
      }

      await persist();
      return lead;
    },

    /** Hide a lead. NOT a removal — see leads-db.mjs for the full rationale. */
    async removeLead(id) {
      const lead = findLead(id);
      if (!lead) throw new LeadsError("not_found", "Lead not found.", 404);
      lead.leadActive = false;
      await persist();
      return lead;
    },

    /**
     * Apply a condensed summary pushed by an audit backend.
     *
     * Present so this fallback satisfies the same interface as the Postgres
     * store: POST /api/leadmagnet/audit-summary calls it, and without it the
     * endpoint would TypeError whenever LEADS_DATABASE_URL is unset.
     *
     * Matched on captureId first, then auditId, so a retry after a successful
     * push updates the same row instead of missing. Never touches `notes`.
     */
    async applyAuditSummary(summary = {}) {
      const captureId = cleanString(summary.capture_id, 64);
      const auditId = cleanString(summary.audit_id, 64);
      if (!captureId && !auditId) {
        throw new LeadsError("invalid_summary", "capture_id or audit_id is required.");
      }
      const lead = state.leads.find(
        (item) =>
          (captureId && item.captureId === captureId) || (auditId && item.auditId === auditId),
      );
      if (!lead) return null;

      const counts = summary.counts ?? {};
      if (auditId) lead.auditId = auditId;
      const status = cleanString(summary.status, 32);
      if (status) lead.auditStatus = status;

      const merged = { ...(lead.details ?? {}) };
      // Type-first: `Number(null)` is 0, so a failed run would otherwise record a
      // score of 0 and the console would grade it F. See leads-db.mjs.
      if (typeof summary.score === "number" && Number.isFinite(summary.score)) {
        merged.score = Math.round(summary.score);
      }
      if (Number.isInteger(counts.passed)) merged.passed = counts.passed;
      if (Number.isInteger(counts.indeterminate)) merged.warnings = counts.indeterminate;
      if (Number.isInteger(counts.critical)) merged.critical = counts.critical;
      if (summary.completed_at) merged.last_audit_time = summary.completed_at;
      const safe = sanitizeDetails(merged);
      if (safe) lead.details = safe;

      await persist();
      return lead;
    },

    /**
     * Attach a booked call to the lead that made it.
     *
     * Same ranked matching the Postgres store uses — chooseLeadForBooking is the
     * single source of that policy. Returns null when no lead qualifies, which
     * the route reports as an accepted-but-unmatched booking.
     */
    async applyMeeting(event = {}) {
      const eventId = cleanString(event.eventId, 128);
      if (!eventId) {
        throw new LeadsError("invalid_meeting", "eventId is required.");
      }

      const chosen = chooseLeadForBooking(state.leads.filter(isActive), event, { now: now() });
      if (!chosen) return null;

      const meeting = sanitizeMeeting({
        eventId,
        startsAt: event.startsAt,
        durationMinutes: event.durationMinutes,
        timezone: event.timezone,
        status: event.status,
        url: event.meetingUrl,
        bookedEmail: event.bookedEmail,
        bookedName: event.bookedName,
        questionAnswers: event.questionAnswers,
      });
      if (!meeting) {
        throw new LeadsError("invalid_meeting", "startsAt is required.");
      }

      chosen.meeting = meeting;
      chosen.meetingEventId = eventId;
      await persist();
      return chosen;
    },

    /** Test hook — resolves once queued writes have hit disk. */
    flush() {
      return writes;
    },
  };
}
