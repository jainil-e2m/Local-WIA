-- Lead Magnet console store — Central Dashboard.
--
-- PURPOSE
-- One row per captured lead, holding the lead's identity plus a CONDENSED
-- summary of the audit it triggered. The console reads only this table, so
-- opening it never queries the per-product audit projects (there will be three;
-- their report payloads are ~2 MB each).
--
-- WHY THE COLUMNS ARE EXACTLY THESE
-- Derived from an audit of every datum the console actually renders: 36 data
-- points, of which 15 need storing. Everything the console computes on the fly
-- is deliberately absent — the letter grade (a mapping over `score`), the
-- coloured status dot, relative timestamps, the `lead_N` display string, all
-- four stats tiles, the whole duplicate-submission panel (a grouping of rows
-- already here), and every search/filter/sort. Storing them would create a
-- second source of truth for a value the dashboard owns.
--
-- The API layer projects these columns back into the `Lead` shape the console
-- already consumes (details.grade is derived on read, etc.), so the frontend is
-- untouched while the table stays minimal.
--
-- ONE TABLE, NOT TWO
-- A funnel submit starts exactly one audit, and a repeat submission is a new
-- lead row (that is what the dedup panel groups). So lead:audit is 1:1 and a
-- join would buy nothing but latency on the one query the console makes.

CREATE TABLE IF NOT EXISTS leadmagnet_leads (
    -- Server-minted. Never client-supplied: this is the PK every PATCH/DELETE
    -- addresses, so accepting it from a public capture endpoint would let a
    -- caller overwrite an existing lead.
    id                      TEXT        PRIMARY KEY,

    -- Human-facing display number ("lead_9"). Stable across re-sorts and never
    -- reused after a delete, which is why it is stored rather than derived from
    -- row order.
    seq                     INTEGER     NOT NULL,

    -- Correlation key minted by the FUNNEL and sent to both the lead capture and
    -- the audit intake. Needed because the lead is captured at form submit,
    -- before an audit_id exists, and the audit backend never learns the email —
    -- so there is nothing else the two records share. UNIQUE so a replayed
    -- capture cannot fan one audit summary out across several leads.
    capture_id              TEXT        UNIQUE,

    -- ── Lead identity (from the funnel form) ─────────────────────────────
    name                    TEXT        NOT NULL,
    email                   TEXT        NOT NULL,
    phone                   TEXT,
    -- Stored absolute (https://…) and matched by normalized host.
    domain_url              TEXT,
    -- technical_seo | onpage_seo | ai_seo. Text rather than an enum so a fourth
    -- funnel does not need a migration; the application validates it.
    product                 TEXT        NOT NULL,
    captured_at             TIMESTAMPTZ NOT NULL,

    -- ── Operator annotation ──────────────────────────────────────────────
    -- Dashboard-owned. The audit backend must never write this column, and the
    -- public capture endpoint must ignore the key outright.
    notes                   TEXT,

    -- ── Condensed audit summary (pushed by the audit backend) ────────────
    -- All nullable: the lead exists from form submit, and the summary lands
    -- 50-220s later. NULL here means "audit still running or never reported",
    -- which the console renders differently from a zero.
    audit_id                TEXT,
    audit_status            TEXT,
    audit_error             TEXT,
    audit_completed_at      TIMESTAMPTZ,

    score                   SMALLINT,
    pages_audited           SMALLINT,
    checks_total            SMALLINT,
    checks_applicable       SMALLINT,
    -- Real engine buckets. There is deliberately no `warnings` column: the audit
    -- engine has no such status (pass | fail | information | not_applicable |
    -- partial_rate_limit). The console's "warnings" pill is rendered from
    -- `indeterminate`, and `grade` is derived from `score` — neither is stored.
    checks_passed           SMALLINT,
    checks_failed           SMALLINT,
    severity_critical       SMALLINT,
    severity_high           SMALLINT,
    severity_advisory       SMALLINT,
    checks_indeterminate    SMALLINT,

    -- Replaces the `scheduler_cron == "FULL_AUDIT_COMPLETED"` sentinel: a
    -- 40-char text column used as a boolean.
    full_audit_completed    BOOLEAN     NOT NULL DEFAULT FALSE,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The console's only list query: newest first.
CREATE INDEX IF NOT EXISTS idx_leadmagnet_leads_captured_at
    ON leadmagnet_leads (captured_at DESC);

-- The audit-summary push looks a lead up by correlation key, then by audit id
-- on retry (once the first push has stamped it).
CREATE INDEX IF NOT EXISTS idx_leadmagnet_leads_audit_id
    ON leadmagnet_leads (audit_id)
    WHERE audit_id IS NOT NULL;

-- The dedup panel groups by (email, product, domain). Supports that grouping and
-- the console's source filter.
CREATE INDEX IF NOT EXISTS idx_leadmagnet_leads_dedup
    ON leadmagnet_leads (email, product, domain_url);

-- `seq` is allocated as max(seq)+1 rather than from a sequence, so a deleted
-- lead's number is never reused and the counter survives a restart (the JSON
-- store kept it in memory, which lost it on every deploy).

-- ── Booked call (pushed by zcal's webhook) ───────────────────────────
-- Added as ALTER … IF NOT EXISTS rather than folded into the CREATE above,
-- because ensureSchema() replays this whole file on every boot: existing
-- deployments already have the table, so new columns have to arrive this way or
-- they would only ever exist on a fresh database.
--
-- Why the booking is stored on the lead rather than in its own table: a lead
-- books at most one call from the funnel, and the console renders it on the lead
-- row it already fetched. A reschedule overwrites in place (same meeting_event_id),
-- so there is no history to keep here — zcal owns that.
--
-- meeting_booked_email / meeting_booked_name are stored even when they equal the
-- lead's own, because the console compares them to decide whether to show that
-- the call was booked under different details. Storing only the difference would
-- mean re-deriving it on every read.
ALTER TABLE leadmagnet_leads ADD COLUMN IF NOT EXISTS meeting_event_id         TEXT;
ALTER TABLE leadmagnet_leads ADD COLUMN IF NOT EXISTS meeting_starts_at        TIMESTAMPTZ;
ALTER TABLE leadmagnet_leads ADD COLUMN IF NOT EXISTS meeting_duration_minutes SMALLINT;
-- The invitee's IANA zone, as zcal reports it. Kept so the console can say which
-- zone the prospect booked in; the time itself is absolute in meeting_starts_at.
ALTER TABLE leadmagnet_leads ADD COLUMN IF NOT EXISTS meeting_timezone         TEXT;
-- booked | cancelled. A cancelled booking keeps its time rather than being
-- nulled: "they booked and cancelled" is different from "never booked".
ALTER TABLE leadmagnet_leads ADD COLUMN IF NOT EXISTS meeting_status           TEXT;
ALTER TABLE leadmagnet_leads ADD COLUMN IF NOT EXISTS meeting_url              TEXT;
ALTER TABLE leadmagnet_leads ADD COLUMN IF NOT EXISTS meeting_booked_email     TEXT;
ALTER TABLE leadmagnet_leads ADD COLUMN IF NOT EXISTS meeting_booked_name      TEXT;

-- A reschedule or cancellation arrives for an event already stored, and is
-- matched on this rather than on the attendee again.
CREATE INDEX IF NOT EXISTS idx_leadmagnet_leads_meeting_event
    ON leadmagnet_leads (meeting_event_id)
    WHERE meeting_event_id IS NOT NULL;

-- The webhook matches a booking to a lead by attendee email, then by name.
-- Both are compared case-insensitively, so the indexes have to be too.
CREATE INDEX IF NOT EXISTS idx_leadmagnet_leads_email_lower
    ON leadmagnet_leads (lower(email));
CREATE INDEX IF NOT EXISTS idx_leadmagnet_leads_name_lower
    ON leadmagnet_leads (lower(name));

-- What the prospect typed into the booking form's own questions.
--
-- JSONB, not a text column, because the invite may carry more than one question
-- and each answer is a (question, answer) pair — zcal identifies answers by the
-- question's text, not by an id. A checkbox answer arrives as an array and is
-- flattened to one string before it gets here.
--
-- Stored on the lead rather than folded into `notes`: notes are operator-owned
-- (see above) and must never be overwritten by an inbound push. The console
-- renders this alongside the operator's own notes instead.
ALTER TABLE leadmagnet_leads ADD COLUMN IF NOT EXISTS meeting_question_answers JSONB;

-- ── Soft delete ──────────────────────────────────────────────────────
-- "Delete" in the console hides a lead; it does not destroy it. Prospect
-- records are the output of paid acquisition and a misclick used to be
-- unrecoverable — the row carried the identity, the score, the operator's
-- notes and the booked call, and DELETE took all four with no undo and no
-- audit trail beyond a gap in `seq`.
--
-- DELIBERATELY ONE-WAY FROM THE APPLICATION. Nothing in the API can set this
-- back to TRUE: removeLead only ever writes FALSE, and no other statement
-- touches the column. Restoring is a manual decision made against the
-- database:
--
--     UPDATE leadmagnet_leads SET lead_active = TRUE WHERE id = 'lead_...';
--     -- or, to see what is hidden first:
--     SELECT id, seq, name, email, domain_url, captured_at
--       FROM leadmagnet_leads WHERE NOT lead_active ORDER BY captured_at DESC;
--
-- NOT NULL DEFAULT TRUE so every existing row stays visible when this column
-- is added, and so a row can never be accidentally hidden by a NULL.
ALTER TABLE leadmagnet_leads ADD COLUMN IF NOT EXISTS lead_active BOOLEAN NOT NULL DEFAULT TRUE;

-- The finished full audit's client PDF.
--
-- Stored rather than fetched on demand so the console can render a Download
-- button only when there is something to download, with no upstream round trip
-- per row. It is an ABSOLUTE Google Drive link in every product that supplies
-- one (Technical SEO resolves it from Drive at rehydrate; AI SEO writes it from
-- drive_download_link), so it needs no proxying and stays valid after the run's
-- worker is gone.
--
-- Nullable and written only on a SUCCESSFUL terminal tick: a lead whose audit
-- failed, or which completed before this column existed, simply has no button.
ALTER TABLE leadmagnet_leads ADD COLUMN IF NOT EXISTS audit_report_url TEXT;

-- When a FULL audit was started from the console, and only then.
--
-- The column exists to tell two producers of `audit_id` apart. A lead's audit
-- id is written by two things that mean different runs:
--
--   1. the funnel's own quick audit, pushed in by an audit backend through
--      POST /api/leadmagnet/audit-summary, and
--   2. a deep-dive run started here by POST /leads/:id/full-audit.
--
-- Nothing distinguished them, so a lead that merely came through a funnel read
-- as "a full audit is already in flight" and the start route attached to the
-- quick run instead of submitting a real one. Every AI SEO lead was in that
-- state: their ids 404 on the audit service the console polls, because they were
-- created on a different deployment entirely.
--
-- Only setAuditRun's start path writes this; the summary webhook never does. So
-- a funnel-only lead has NULL here and can never be mistaken for a running full
-- audit, which retires the whole failure mode without touching a single row.
ALTER TABLE leadmagnet_leads ADD COLUMN IF NOT EXISTS full_audit_started_at TIMESTAMPTZ;
