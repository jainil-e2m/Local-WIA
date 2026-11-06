-- Outbound Slack notices consume committed schedule_saved events; calendar writes are unchanged.
CREATE TABLE slack_schedule_notifications (
  notification_id text PRIMARY KEY,
  source_event_id text NOT NULL,
  destination text NOT NULL CHECK (destination IN ('email','social')),
  channel_id text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL CHECK (status IN ('pending','sending','sent','failed','skipped')),
  attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  next_attempt_at timestamptz NOT NULL DEFAULT now(),
  claim_token text,
  lease_expires_at timestamptz,
  slack_ts text,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  sent_at timestamptz,
  UNIQUE (source_event_id,destination),
  CHECK ((claim_token IS NULL) = (lease_expires_at IS NULL)),
  CHECK ((status='sending') = (claim_token IS NOT NULL AND lease_expires_at IS NOT NULL))
);
CREATE INDEX slack_schedule_notifications_due ON slack_schedule_notifications (next_attempt_at,created_at)
  WHERE status='pending';
CREATE INDEX schedule_saved_events ON pipeline_events (created_at,event_id) WHERE event_type='schedule_saved';
