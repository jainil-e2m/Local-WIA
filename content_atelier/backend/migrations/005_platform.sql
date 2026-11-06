-- Migration 005 (plan 0.B3, section 4.8). Additive. Applied by `storage_cli migrate` after 001 to 004.
-- Creates the tables Phase E needs: run plans, decisions and labels, the knowledge-base table,
-- founder seeds, settings, users, the model-call record, and the job columns for one executor.

CREATE TABLE schema_migrations (
  version text PRIMARY KEY,
  name text NOT NULL,
  checksum text NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now(),
  applied_by text NOT NULL DEFAULT 'storage_cli migrate',
  -- 'detected' for 001 to 004, found by their marker objects; 'applied' when the runner ran the file.
  source text NOT NULL CHECK (source IN ('detected', 'applied'))
);

CREATE TABLE settings (
  key text PRIMARY KEY,
  value jsonb NOT NULL,
  updated_by text NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
  email text PRIMARY KEY CHECK (email = lower(email) AND position('@' IN email) > 1),
  name text,
  role text NOT NULL CHECK (role IN ('viewer', 'editor', 'approver', 'admin')),
  slack_user_id text UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- One row per human decision on any item: the audit log (architecture section 10), with llm_runs.
CREATE TABLE decisions (
  decision_id text PRIMARY KEY,
  item_kind text NOT NULL CHECK (item_kind IN ('angle', 'considered_idea', 'brief', 'brand_kit_item', 'run_plan', 'seed')),
  item_id text NOT NULL,
  week_id text REFERENCES weeks,
  action text NOT NULL,
  disposition text CHECK (disposition IN ('develop', 'reframe', 'hold', 'internal', 'skip', 'revive', 'approve', 'reject')),
  reason_code text,
  note text,
  reframe jsonb,
  central_point_kept boolean,
  hold_until date,
  -- Who decided (the verified actor) and whose judgement it records: Whitney, or a named
  -- team member relaying her (R45, X3).
  actor text NOT NULL,
  author text NOT NULL,
  expected_hash text,
  resulting_item_id text,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (disposition <> 'reframe' OR (reframe IS NOT NULL AND central_point_kept IS NOT NULL)),
  CHECK (disposition <> 'hold' OR hold_until IS NOT NULL)
);
CREATE INDEX decisions_item ON decisions (item_kind, item_id, created_at);

-- The benchmark's labels (R45, E.B2). One disposition is one decision plus a label pointing to it;
-- imported proxy labels (for example the ChatGPT export's preference pairs) have no decision.
CREATE TABLE calibration_labels (
  label_id text PRIMARY KEY,
  item_kind text NOT NULL,
  item_id text NOT NULL,
  decision_id text REFERENCES decisions,
  week_id text,
  disposition text NOT NULL,
  reason_code text,
  reframe jsonb,
  central_point_kept boolean,
  rubric_ratings jsonb,
  rater text NOT NULL,
  author text NOT NULL,
  source text NOT NULL,
  proxy boolean NOT NULL DEFAULT false,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (decision_id IS NOT NULL OR proxy OR source <> 'gate')
);
CREATE INDEX calibration_labels_item ON calibration_labels (item_kind, item_id);
CREATE UNIQUE INDEX calibration_labels_one_per_decision ON calibration_labels (decision_id) WHERE decision_id IS NOT NULL;

-- Run plans for paid calls (E.B1, R39): a real-data call outside an active plan is refused.
CREATE TABLE run_plans (
  plan_id text PRIMARY KEY,
  purpose text NOT NULL,
  stages text[] NOT NULL CHECK (cardinality(stages) > 0),
  models text[] NOT NULL CHECK (cardinality(models) > 0),
  input_set_hash text NOT NULL,
  max_calls integer NOT NULL CHECK (max_calls > 0),
  max_cost_usd numeric(10, 4) NOT NULL CHECK (max_cost_usd > 0),
  approver text NOT NULL,
  approved_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'exhausted', 'closed', 'expired')),
  calls_used integer NOT NULL DEFAULT 0 CHECK (calls_used >= 0),
  cost_used_usd numeric(10, 4) NOT NULL DEFAULT 0 CHECK (cost_used_usd >= 0),
  closed_at timestamptz,
  closed_reason text,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  CHECK (calls_used <= max_calls),
  CHECK (expires_at > approved_at)
);

-- One row per model or embedding call (0.B4 writes it for every call; E.B1 for planned ones).
CREATE TABLE llm_runs (
  llm_run_id text PRIMARY KEY,
  plan_id text REFERENCES run_plans,
  stage text NOT NULL,
  model text NOT NULL,
  provider text,
  routing_policy text NOT NULL,
  request_fingerprint text NOT NULL,
  prompt_version text,
  knowledge_base_version text,
  input_tokens integer,
  output_tokens integer,
  cost_usd numeric(12, 6),
  status text NOT NULL CHECK (status IN ('sent', 'succeeded', 'failed', 'refused', 'replayed')),
  error text,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX llm_runs_plan ON llm_runs (plan_id, created_at);

-- Non-model outbound calls (web research, connectors), for cost and audit.
CREATE TABLE external_calls (
  call_id text PRIMARY KEY,
  plan_id text REFERENCES run_plans,
  service text NOT NULL,
  operation text NOT NULL,
  status text NOT NULL,
  cost_usd numeric(12, 6),
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Versioned knowledge-base documents (E.B11 e, R41). Files in backend/knowledge_base/ seed it;
-- Phase L's compiler writes later versions (migration 010 adds compiled_from, benchmark_state).
CREATE TABLE brand_kit_docs (
  key text NOT NULL,
  version text NOT NULL,
  heading text NOT NULL,
  owner text NOT NULL,
  status text NOT NULL CHECK (status IN ('supplied', 'confirmed', 'draft', 'unconfirmed')),
  effective_date date NOT NULL,
  review_interval_days integer NOT NULL CHECK (review_interval_days > 0),
  approver text,
  approved_at timestamptz,
  sha256 text NOT NULL,
  body text NOT NULL,
  object_key text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (key, version)
);

-- Founder seeds (E.B19): a thought, a draft or a published asset, offered to a cycle.
CREATE TABLE seeds (
  seed_id text PRIMARY KEY,
  kind text NOT NULL CHECK (kind IN ('thought', 'draft', 'asset')),
  text text NOT NULL CHECK (length(btrim(text)) > 0),
  target_offer text,
  source_url text,
  always_true boolean NOT NULL DEFAULT false,
  author text NOT NULL,
  created_by text NOT NULL,
  week_id text REFERENCES weeks,
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'used', 'withdrawn')),
  used_in_run_id text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- One executor (0.B5): queue and RQ identity on every job row.
ALTER TABLE pipeline_jobs ADD COLUMN queue text NOT NULL DEFAULT 'default'
  CHECK (queue IN ('interactive', 'default', 'bulk', 'intake', 'media'));
ALTER TABLE pipeline_jobs ADD COLUMN rq_job_id text;
ALTER TABLE pipeline_jobs ADD COLUMN priority integer NOT NULL DEFAULT 0;
