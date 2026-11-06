-- Migration 011 (Phase N6: 6.B4; Phase N10: 6.B13). Additive; needs 010.
-- Failure alerts: one row per open condition (a failed job, a stuck queue, a stopped intake connection, a budget refusal, a
-- scheduled run that did not happen, a missed backup or restore check, a low accepted share two weeks running). The
-- scheduler's scan opens it once, counts each pass that still sees it, and resolves it as `cleared` when the condition is
-- gone; a person may dismiss it. The app is the channel: `notified` records each channel's state ({"email": "off"} while the
-- owner keeps alert emails off, 25 October 2026).

CREATE TABLE alerts (
  alert_id text PRIMARY KEY,
  kind text NOT NULL CHECK (kind IN ('job_failed', 'job_stuck', 'intake_stopped', 'budget_refused', 'schedule_missed',
                                     'backup_missing', 'restore_check_failed', 'accepted_share_low', 'scheduler_silent')),
  -- What the alert is about: a job id, a queue, a connection, a budget purpose, a schedule key, a week.
  subject text NOT NULL,
  severity text NOT NULL CHECK (severity IN ('warning', 'error')),
  message text NOT NULL,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurrences integer NOT NULL DEFAULT 1 CHECK (occurrences >= 1),
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz,
  resolved_by text,
  resolution text CHECK (resolution IS NULL OR resolution IN ('cleared', 'dismissed')),
  notified jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT alerts_resolution_pair CHECK ((resolved_at IS NULL) = (resolution IS NULL))
);
-- One open alert per condition.
CREATE UNIQUE INDEX alerts_one_open ON alerts (kind, subject) WHERE resolved_at IS NULL;
CREATE INDEX alerts_recent ON alerts (last_seen_at DESC);
