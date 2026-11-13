/* ────────────────────────────────────────────────────────────────
   Postgres-backed Lead Magnet store.

   Drop-in for createLeadsStore() in leads-store.mjs: same method names, same
   LeadsError codes, same returned `Lead` shape. index.mjs picks between them on
   whether LEADS_DATABASE_URL is set, so local development without Postgres keeps
   working and a deploy that forgets the variable degrades to the JSON file rather
   than crashing.

   TWO DELIBERATE DIFFERENCES FROM THE JSON STORE

   1. `read()` and `status()` are ASYNC here. They were synchronous because the
      JSON store held everything in memory. Their three call sites in index.mjs
      are awaited accordingly.

   2. `seq` is allocated as max(seq)+1 IN SQL, not from an in-memory counter.
      The JSON store's counter lived in the process, so every deploy reset it and
      numbers could be reused after a restart — the opposite of the "stable, never
      reused" contract the console's Lead ID column promises.

   WHAT IS STORED vs WHAT IS RETURNED
   The table holds only what the console cannot compute (see
   leadmagnet-schema.sql). `details.grade` is derived from `score` on read, and
   the console's "warnings" pill is fed from `checks_indeterminate` — the engine
   has no `warning` status, so nothing of the sort is stored. This keeps the
   table minimal without the frontend needing to change.
   ──────────────────────────────────────────────────────────────── */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import crypto from "node:crypto";
import pg from "pg";
import { chooseLeadForBooking } from "./meeting-match.mjs";

import { LEAD_TYPES, LIMITS, LeadsError, sanitizeDetails } from "./leads-store.mjs";
import { normalizeUrl } from "./bookmarks-store.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCHEMA_PATH = path.join(__dirname, "leadmagnet-schema.sql");

const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const cleanString = (raw, maxLength) =>
  typeof raw === "string" ? raw.trim().slice(0, maxLength) : "";

/** Score -> letter. Derived on READ so the grade can never drift from the score
 *  it describes, and so the column does not exist to be written wrongly. */
function gradeFor(score) {
  if (typeof score !== "number") return undefined;
  if (score >= 90) return "A";
  if (score >= 80) return "B";
  if (score >= 70) return "C";
  if (score >= 60) return "D";
  return "F";
}

/**
 * Project a row into the `Lead` shape the console already consumes, so the
 * frontend and its API client need no changes.
 *
 * Optional fields are OMITTED rather than set to null: the JSON store built
 * objects with `undefined` values that JSON.stringify dropped, and the console
 * checks `lead.phone ? …`. Emitting explicit nulls would render "null".
 */
function rowToLead(row) {
  const lead = {
    id: row.id,
    seq: row.seq,
    name: row.name,
    email: row.email,
    type: row.product,
    timestamp: row.captured_at.toISOString(),
  };
  if (row.phone) lead.phone = row.phone;
  if (row.domain_url) lead.domainUrl = row.domain_url;
  if (row.notes) lead.notes = row.notes;
  if (row.capture_id) lead.captureId = row.capture_id;
  if (row.audit_id) lead.auditId = row.audit_id;
  if (row.audit_status) lead.auditStatus = row.audit_status;
  if (row.audit_error) lead.auditError = row.audit_error;
  if (row.audit_report_url) lead.auditReportUrl = row.audit_report_url;

  const details = {};
  if (row.score !== null && row.score !== undefined) {
    details.score = row.score;
    details.grade = gradeFor(row.score);
  }
  if (row.checks_passed !== null && row.checks_passed !== undefined) {
    details.passed = row.checks_passed;
    // The console's amber pill. Fed from indeterminate checks because the engine
    // has no "warning" status to store.
    details.warnings = row.checks_indeterminate ?? 0;
    details.critical = row.severity_critical ?? 0;
  }
  /* Exposed flat rather than folded into `details`: it is not a detail of the
     captured lead, it is provenance for the audit id above — the console and the
     server both branch on it before deciding whether a run is in flight. */
  if (row.full_audit_started_at) lead.fullAuditStartedAt = row.full_audit_started_at.toISOString();
  if (row.full_audit_completed) details.scheduler_cron = "FULL_AUDIT_COMPLETED";
  if (row.audit_completed_at) details.last_audit_time = row.audit_completed_at.toISOString();
  if (Object.keys(details).length > 0) lead.details = details;

  /* The booked call. Exposed as one nested object rather than eight flat keys so
     the console can test for its presence in one place, and so a lead that never
     booked carries nothing at all. */
  if (row.meeting_starts_at) {
    lead.meeting = {
      eventId: row.meeting_event_id ?? null,
      startsAt: row.meeting_starts_at.toISOString(),
      durationMinutes: row.meeting_duration_minutes ?? null,
      timezone: row.meeting_timezone ?? null,
      status: row.meeting_status ?? "booked",
      url: row.meeting_url ?? null,
      bookedEmail: row.meeting_booked_email ?? null,
      bookedName: row.meeting_booked_name ?? null,
      /* JSONB comes back already parsed. Normalised to null rather than [] so
         the console can test truthiness without also testing length. */
      questionAnswers: Array.isArray(row.meeting_question_answers) && row.meeting_question_answers.length
        ? row.meeting_question_answers
        : null,
    };
  }
  // Flat mirror of the id, so the matcher can read candidates straight from
  // rowToLead output without knowing the nesting.
  if (row.meeting_event_id) lead.meetingEventId = row.meeting_event_id;

  return lead;
}

const SELECT_COLS = `
  id, seq, capture_id, name, email, phone, domain_url, product, captured_at, notes,
  audit_id, audit_status, audit_error, audit_completed_at, audit_report_url, score, pages_audited,
  checks_total, checks_applicable, checks_passed, checks_failed,
  severity_critical, severity_high, severity_advisory, checks_indeterminate,
  full_audit_completed, full_audit_started_at,
  meeting_event_id, meeting_starts_at, meeting_duration_minutes, meeting_timezone,
  meeting_status, meeting_url, meeting_booked_email, meeting_booked_name,
  meeting_question_answers
`;

export function createLeadsDbStore(connectionString, { now = () => Date.now() } = {}) {
  const pool = new pg.Pool({
    connectionString,
    max: 5,
    // Railway Postgres terminates idle connections; keep the pool small and
    // let it reopen rather than holding sockets across a quiet night.
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 10_000,
    // Railway's internal network is trusted and its certs are not in the CA
    // bundle, so verification is off for the managed plugin only. An external
    // Postgres should set sslmode in the URL instead.
    ssl: /railway|proxy\.rlwy|amazonaws|render|supabase/i.test(connectionString)
      ? { rejectUnauthorized: false }
      : undefined,
  });

  let ready = null;
  let loadError = null;

  /** Applied once per process, idempotently (CREATE TABLE/INDEX IF NOT EXISTS).
   *  Safe if the API and any other consumer race: Postgres serialises DDL and
   *  every statement is conditional. */
  async function ensureSchema() {
    if (!ready) {
      ready = (async () => {
        const sql = fs.readFileSync(SCHEMA_PATH, "utf8");
        await pool.query(sql);
      })().catch((error) => {
        // Remember the failure but let each call retry: a Postgres that is still
        // booting should not poison the process for good.
        loadError = error.message;
        ready = null;
        throw error;
      });
    }
    return ready;
  }

  /* Every caller of this treats null as "no such lead", so a soft-deleted row
     is simply invisible to getLead / updateLead / setAuditRun — no caller needs
     to know the column exists. The one path that deliberately does NOT filter is
     applyAuditSummary: see the note there. */
  async function fetchById(client, id) {
    const { rows } = await client.query(
      `SELECT ${SELECT_COLS} FROM leadmagnet_leads WHERE id = $1 AND lead_active`,
      [id],
    );
    return rows[0] ?? null;
  }

  return {
    backend: "postgres",

    async read() {
      await ensureSchema();
      const { rows } = await pool.query(
        `SELECT ${SELECT_COLS} FROM leadmagnet_leads
          WHERE lead_active
          ORDER BY captured_at DESC, seq DESC`,
      );
      return { leads: rows.map(rowToLead) };
    },

    /** One lead by id, or null. Used by the full-audit routes, which act on a
        single row and must not pull the whole table to do it. */
    async getLead(id) {
      await ensureSchema();
      const client = await pool.connect();
      try {
        const row = await fetchById(client, id);
        return row ? rowToLead(row) : null;
      } finally {
        client.release();
      }
    },

    async status() {
      try {
        await ensureSchema();
        const { rows } = await pool.query(
          "SELECT count(*)::int AS n FROM leadmagnet_leads WHERE lead_active",
        );
        return { backend: "postgres", durable: true, loadError: null, counts: { leads: rows[0].n } };
      } catch (error) {
        return {
          backend: "postgres",
          durable: false,
          loadError: loadError ?? error.message,
          counts: { leads: 0 },
        };
      }
    },

    /**
     * Validate + store one captured lead. Same contract as the JSON store:
     * name/email/type are the identity and are required; a malformed domainUrl is
     * DROPPED rather than rejected, because losing a contact over a typo'd
     * website field would defeat the capture funnel.
     *
     * `notes` is deliberately not accepted — this path is reachable from the
     * public capture endpoint, so honouring it would let anyone write into the
     * CRM. Notes are PATCH-only.
     */
    async createLead({ name, email, phone, domainUrl, type, details, captureId } = {}) {
      await ensureSchema();

      const cleanName = cleanString(name, LIMITS.nameLength);
      if (!cleanName) throw new LeadsError("invalid_name", "A contact name is required.");
      const cleanEmail = cleanString(email, LIMITS.emailLength).toLowerCase();
      if (!EMAIL_SHAPE.test(cleanEmail)) {
        throw new LeadsError("invalid_email", "A valid email address is required.");
      }
      if (!LEAD_TYPES.has(type)) {
        throw new LeadsError("invalid_type", `type must be one of: ${[...LEAD_TYPES].join(", ")}.`);
      }

      const safeDetails = sanitizeDetails(details) ?? {};
      const id = `lead_${crypto.randomUUID()}`;
      const capturedAt = new Date(now()).toISOString();

      const { rows } = await pool.query(
        `INSERT INTO leadmagnet_leads (
           id, seq, capture_id, name, email, phone, domain_url, product, captured_at,
           score, checks_passed, checks_indeterminate, severity_critical,
           full_audit_completed, audit_completed_at, audit_id
         ) VALUES (
           $1,
           COALESCE((SELECT max(seq) FROM leadmagnet_leads), 0) + 1,
           $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
         )
         /* The funnel saves the SAME lead twice: once at form submit, once when
            the audit resolves, both carrying the capture id. capture_id is UNIQUE,
            so the second arrival raised a unique violation that captureRemotely
            swallows — which is why On-Page leads have been landing with no score.

            Identity is deliberately NOT updated: the second save is an enrichment,
            not a correction, and both arrivals carry the same name and email. Every
            metric is COALESCEd so a later save that omits a field cannot blank a
            value already stored. The notes column is dashboard-owned and is never
            written here. (No backticks in this comment: it lives inside a JS
            template literal, and a stray pair terminates the SQL string.)

            A NULL capture_id does not conflict in Postgres, so a capture without
            one still inserts a fresh row exactly as before. */
         ON CONFLICT (capture_id) DO UPDATE SET
           phone                = COALESCE(EXCLUDED.phone, leadmagnet_leads.phone),
           domain_url           = COALESCE(EXCLUDED.domain_url, leadmagnet_leads.domain_url),
           score                = COALESCE(EXCLUDED.score, leadmagnet_leads.score),
           checks_passed        = COALESCE(EXCLUDED.checks_passed, leadmagnet_leads.checks_passed),
           checks_indeterminate = COALESCE(EXCLUDED.checks_indeterminate, leadmagnet_leads.checks_indeterminate),
           severity_critical    = COALESCE(EXCLUDED.severity_critical, leadmagnet_leads.severity_critical),
           audit_completed_at   = COALESCE(EXCLUDED.audit_completed_at, leadmagnet_leads.audit_completed_at),
           audit_id             = COALESCE(EXCLUDED.audit_id, leadmagnet_leads.audit_id),
           full_audit_completed = leadmagnet_leads.full_audit_completed OR EXCLUDED.full_audit_completed,
           updated_at           = now()
         RETURNING ${SELECT_COLS}`,
        [
          id,
          cleanString(captureId, 64) || null,
          cleanName,
          cleanEmail,
          cleanString(phone, LIMITS.phoneLength) || null,
          normalizeUrl(domainUrl) || null,
          type,
          capturedAt,
          // Only present when a caller supplies pre-computed metrics (the console's
          // manual-entry path). A funnel capture arrives before its audit finishes,
          // so these are normally null until the backend pushes a summary.
          safeDetails.score ?? null,
          safeDetails.passed ?? null,
          safeDetails.warnings ?? null,
          safeDetails.critical ?? null,
          safeDetails.scheduler_cron === "FULL_AUDIT_COMPLETED",
          safeDetails.last_audit_time ?? null,
          /* The column has always existed and rowToLead already projects it to
             the console, but this INSERT never wrote it -- so an On-Page lead
             landed with its score and still no way to reach the report behind
             it. sanitizeDetails has already shape-checked the value against the
             URL it gets rendered into. */
          safeDetails.audit_id ?? null,
        ],
      );
      return rowToLead(rows[0]);
    },

    /** Dashboard-side edit. `notes` is writable ONLY here. */
    async updateLead(id, patch = {}) {
      await ensureSchema();
      const client = await pool.connect();
      try {
        await client.query("BEGIN");
        const existing = await fetchById(client, id);
        if (!existing) throw new LeadsError("not_found", "Lead not found.", 404);

        const sets = [];
        const values = [];
        const push = (col, value) => {
          values.push(value);
          sets.push(`${col} = $${values.length}`);
        };

        if (patch.name !== undefined) {
          const cleanName = cleanString(patch.name, LIMITS.nameLength);
          if (!cleanName) throw new LeadsError("invalid_name", "A contact name is required.");
          push("name", cleanName);
        }
        if (patch.email !== undefined) {
          const cleanEmail = cleanString(patch.email, LIMITS.emailLength).toLowerCase();
          if (!EMAIL_SHAPE.test(cleanEmail)) {
            throw new LeadsError("invalid_email", "A valid email address is required.");
          }
          push("email", cleanEmail);
        }
        if (patch.phone !== undefined) push("phone", cleanString(patch.phone, LIMITS.phoneLength) || null);
        if (patch.domainUrl !== undefined) push("domain_url", normalizeUrl(patch.domainUrl) || null);

        // Omitting `notes` leaves it untouched; an empty/whitespace value clears it.
        if (patch.notes !== undefined) {
          push("notes", cleanString(patch.notes, LIMITS.notesLength) || null);
        }

        // details merges PER FIELD, so a partial score update is safe.
        if (patch.details !== undefined) {
          const d = sanitizeDetails(patch.details) ?? {};
          if (d.score !== undefined) push("score", d.score);
          if (d.passed !== undefined) push("checks_passed", d.passed);
          if (d.warnings !== undefined) push("checks_indeterminate", d.warnings);
          if (d.critical !== undefined) push("severity_critical", d.critical);
          if (d.last_audit_time !== undefined) push("audit_completed_at", d.last_audit_time);
          if (d.scheduler_cron !== undefined) {
            push("full_audit_completed", d.scheduler_cron === "FULL_AUDIT_COMPLETED");
          }
        }

        if (sets.length === 0) {
          await client.query("COMMIT");
          return rowToLead(existing);
        }

        values.push(id);
        const { rows } = await client.query(
          `UPDATE leadmagnet_leads SET ${sets.join(", ")}, updated_at = now()
             WHERE id = $${values.length}
           RETURNING ${SELECT_COLS}`,
          values,
        );
        await client.query("COMMIT");
        return rowToLead(rows[0]);
      } catch (error) {
        await client.query("ROLLBACK").catch(() => {});
        throw error;
      } finally {
        client.release();
      }
    },

    /**
     * Record the lifecycle of a full audit against a lead.
     *
     * SEPARATE FROM updateLead ON PURPOSE. updateLead serves the operator's own
     * PATCH, which is reachable from the browser; if it could write these columns
     * then any team session could forge a completed audit by hand. Audit
     * lifecycle is written only by the server following a real upstream run, so
     * it gets its own door and `details` is not a way through it.
     *
     * Writes real columns rather than the `details` projection. Note in
     * particular that `full_audit_completed` is the actual BOOLEAN — the
     * `scheduler_cron === "FULL_AUDIT_COMPLETED"` sentinel that updateLead still
     * accepts is a read-side compatibility shim synthesised by rowToLead, and
     * this path deliberately does not extend its use.
     */
    async setAuditRun(id, patch = {}) {
      await ensureSchema();
      const client = await pool.connect();
      try {
        await client.query("BEGIN");
        const existing = await fetchById(client, id);
        if (!existing) throw new LeadsError("not_found", "Lead not found.", 404);

        const sets = [];
        const values = [];
        const push = (col, value) => {
          values.push(value);
          sets.push(`${col} = $${values.length}`);
        };

        // Each is optional so one call can start a run (id + status) and a later
        // one can finish it (status + completedAt) without clearing the rest.
        if (patch.auditId !== undefined) {
          push("audit_id", cleanString(patch.auditId, LIMITS.auditIdLength) || null);
        }
        if (patch.auditStatus !== undefined) {
          push("audit_status", cleanString(patch.auditStatus, 40) || null);
        }
        if (patch.auditError !== undefined) {
          push("audit_error", cleanString(patch.auditError, 500) || null);
        }
        if (patch.completedAt !== undefined) push("audit_completed_at", patch.completedAt);
        if (patch.reportUrl !== undefined) {
          push("audit_report_url", cleanString(patch.reportUrl, 2000) || null);
        }
        if (patch.fullAuditCompleted !== undefined) {
          push("full_audit_completed", Boolean(patch.fullAuditCompleted));
        }
        /* Written by the start route and nothing else. applyAuditSummary
           deliberately leaves it alone, which is what keeps a funnel-pushed
           audit id from ever reading as a running full audit. */
        if (patch.fullAuditStartedAt !== undefined) {
          push("full_audit_started_at", patch.fullAuditStartedAt || null);
        }

        if (sets.length === 0) {
          await client.query("COMMIT");
          return rowToLead(existing);
        }

        values.push(id);
        const { rows } = await client.query(
          `UPDATE leadmagnet_leads SET ${sets.join(", ")}, updated_at = now()
             WHERE id = $${values.length}
           RETURNING ${SELECT_COLS}`,
          values,
        );
        await client.query("COMMIT");
        return rowToLead(rows[0]);
      } catch (error) {
        await client.query("ROLLBACK").catch(() => {});
        throw error;
      } finally {
        client.release();
      }
    },

    /**
     * Hide a lead. NOT a DELETE.
     *
     * The row, its audit summary, the operator's notes and any booked call all
     * survive; the console simply stops selecting it. This is the only statement
     * in the codebase that writes `lead_active`, and it only ever writes FALSE —
     * so restoring a lead is necessarily a manual decision made against the
     * database (see leadmagnet-schema.sql for the UPDATE).
     *
     * `AND lead_active` in the WHERE keeps the 404 honest: hiding an
     * already-hidden lead is not-found rather than a silent success.
     */
    async removeLead(id) {
      await ensureSchema();
      const { rowCount } = await pool.query(
        "UPDATE leadmagnet_leads SET lead_active = FALSE, updated_at = now() WHERE id = $1 AND lead_active",
        [id],
      );
      if (rowCount === 0) throw new LeadsError("not_found", "Lead not found.", 404);
    },

    /**
     * Apply a condensed summary pushed by an audit backend.
     *
     * Matched on `capture_id` first (the funnel mints it and sends it to both the
     * capture and the audit intake), then on `audit_id` so a retry after a
     * successful first push is idempotent rather than creating a second match.
     *
     * Never writes `notes` — that column is dashboard-owned and an audit backend
     * has no business in it.
     *
     * Returns the updated lead, or null when no lead matches. Null is NOT an
     * error: an audit can legitimately be started outside the funnel (a direct
     * API call, or the console's own re-run), in which case there is no lead to
     * attach it to and the caller should not retry forever.
     */
    async applyAuditSummary(summary = {}) {
      await ensureSchema();
      const captureId = cleanString(summary.capture_id, 64) || null;
      const auditId = cleanString(summary.audit_id, 64) || null;
      if (!captureId && !auditId) {
        throw new LeadsError("invalid_summary", "capture_id or audit_id is required.");
      }

      const counts = summary.counts ?? {};
      const clamp = (value) =>
        Number.isInteger(value) && value >= 0 && value <= 32_767 ? value : null;
      // Type check BEFORE range check. `Number(null)` is 0, which satisfies both
      // bounds, so a failed run (the backend sends score: null) would store a
      // real-looking 0 and the console would render grade F for an audit that
      // never produced one. `clamp` above is already type-first for the counts.
      const score =
        typeof summary.score === "number" &&
        Number.isFinite(summary.score) &&
        summary.score >= 0 &&
        summary.score <= 100
          ? Math.round(summary.score)
          : null;

      const { rows } = await pool.query(
        `UPDATE leadmagnet_leads SET
           audit_id             = COALESCE($1, audit_id),
           audit_status         = $2,
           audit_error          = $3,
           audit_completed_at   = $4,
           score                = $5,
           pages_audited        = $6,
           checks_total         = $7,
           checks_applicable    = $8,
           checks_passed        = $9,
           checks_failed        = $10,
           severity_critical    = $11,
           severity_high        = $12,
           severity_advisory    = $13,
           checks_indeterminate = $14,
           updated_at           = now()
         -- Deliberately NOT filtered on lead_active. This is the audit
         -- backend's service-to-service push, not something an operator sees:
         -- a summary that lands after a lead was hidden should still be stored
         -- (the row is intact and may be restored), and refusing it here would
         -- report "no match" and invite the sender to retry forever.
         WHERE ($15::text IS NOT NULL AND capture_id = $15)
            OR ($1::text  IS NOT NULL AND audit_id   = $1)
         RETURNING ${SELECT_COLS}`,
        [
          auditId,
          cleanString(summary.status, 32) || null,
          cleanString(summary.error_message, 500) || null,
          summary.completed_at ?? null,
          score,
          clamp(counts.pages_audited ?? summary.pages_audited),
          clamp(counts.checks_total),
          clamp(counts.checks_applicable),
          clamp(counts.passed),
          clamp(counts.failed),
          clamp(counts.critical),
          clamp(counts.high),
          clamp(counts.advisory),
          clamp(counts.indeterminate),
          captureId,
        ],
      );
      return rows[0] ? rowToLead(rows[0]) : null;
    },

    /**
     * Attach a booked call to the lead that made it.
     *
     * Two steps on purpose. SQL narrows to plausible candidates — cheap, and
     * index-backed on lower(email), lower(name) and meeting_event_id — then
     * chooseLeadForBooking() decides, so the ranking rules live in exactly one
     * place and are the same ones the JSON store applies.
     *
     * Returns null when nothing matches. That is an ordinary outcome, not a
     * failure: someone can book from a link shared by hand, or under details
     * that resemble no lead we hold.
     */
    async applyMeeting(event = {}) {
      await ensureSchema();
      const eventId = cleanString(event.eventId, 128) || null;
      if (!eventId) {
        throw new LeadsError("invalid_meeting", "eventId is required.");
      }

      const email = cleanString(event.bookedEmail, 320)?.toLowerCase() || null;
      const name = cleanString(event.bookedName, 200) || null;
      const phoneDigits = (cleanString(event.bookedPhone, 40) || "").replace(/\D/g, "");
      // Last ten digits, matching meeting-match.mjs — see the note there on why.
      const phoneTail = phoneDigits.length >= 10 ? phoneDigits.slice(-10) : null;

      const { rows } = await pool.query(
        `SELECT ${SELECT_COLS} FROM leadmagnet_leads
          WHERE lead_active AND (
                meeting_event_id = $1
             OR ($2::text IS NOT NULL AND lower(email) = $2)
             OR ($3::text IS NOT NULL AND lower(name)  = lower($3))
             OR ($4::text IS NOT NULL
                 AND length(regexp_replace(coalesce(phone, ''), '\\D', '', 'g')) >= 10
                 AND right(regexp_replace(coalesce(phone, ''), '\\D', '', 'g'), 10) = $4))`,
        [eventId, email, name, phoneTail],
      );

      const chosen = chooseLeadForBooking(rows.map(rowToLead), event, { now: now() });
      if (!chosen) return null;

      const { rows: updated } = await pool.query(
        `UPDATE leadmagnet_leads SET
           meeting_event_id         = $1,
           meeting_starts_at        = $2,
           meeting_duration_minutes = $3,
           meeting_timezone         = $4,
           meeting_status           = $5,
           meeting_url              = $6,
           meeting_booked_email     = $7,
           meeting_booked_name      = $8,
           meeting_question_answers = $9,
           updated_at               = now()
         WHERE id = $10
         RETURNING ${SELECT_COLS}`,
        [
          eventId,
          event.startsAt ?? null,
          Number.isInteger(event.durationMinutes) ? event.durationMinutes : null,
          cleanString(event.timezone, 64) || null,
          cleanString(event.status, 32) || "booked",
          cleanString(event.meetingUrl, 500) || null,
          email,
          name,
          /* Re-serialised here rather than passed as an object: node-postgres
             sends a JS object to a JSONB column as its stringified form anyway,
             and being explicit keeps a malformed value from reaching the column. */
          Array.isArray(event.questionAnswers) && event.questionAnswers.length
            ? JSON.stringify(event.questionAnswers.slice(0, 5))
            : null,
          chosen.id,
        ],
      );
      return updated[0] ? rowToLead(updated[0]) : null;
    },

    async close() {
      await pool.end();
    },
  };
}
