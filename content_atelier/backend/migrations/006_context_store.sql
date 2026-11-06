-- Migration 006 (plan label 010; L.B1, sections 4.8 and 4.12). Additive; needs 005 only.
-- The plan numbers migrations in planned order and the runner assigns the next free number at merge: Phase L's
-- context store merged first, so it is file 006, and the plan's 006 to 009 (Phases 1 to 5) shift by one.
-- Creates the context store (brand-kit items with provenance and validity) and the published-content memory,
-- and lets brand_kit_docs record what a compiled version was built from.

CREATE TABLE brand_kit_items (
  item_id text PRIMARY KEY,
  kind text NOT NULL CHECK (kind IN ('rule', 'exemplar', 'offer', 'price', 'roster_member', 'result', 'cta',
    'process_step', 'belief', 'audience_phrase', 'format_rule', 'campaign', 'content_plan_entry', 'performance_note')),
  -- A stable natural key such as offer:elevate. Confirmed items with the same key supersede one another.
  key text NOT NULL CHECK (key ~ '^[a-z_]+:[a-z0-9][a-z0-9_.:-]*$'),
  body jsonb NOT NULL,
  text text NOT NULL CHECK (length(btrim(text)) > 0),
  valid_from date,
  valid_to date,
  status text NOT NULL CHECK (status IN ('candidate', 'confirmed', 'rejected', 'retired')),
  visibility text NOT NULL CHECK (visibility IN ('public', 'internal')),
  sensitivity text NOT NULL DEFAULT 'none' CHECK (sensitivity IN ('none', 'client_private', 'personal', 'confidential')),
  -- Results only: published (WIA published it), client_permission (recorded per result) or none.
  permission text CHECK (permission IN ('published', 'client_permission', 'none')),
  source_kind text NOT NULL CHECK (source_kind IN ('export_seed', 'knowledge_base', 'gate_decision', 'approved_card',
    'approved_brief', 'brief_edit', 'published_piece', 'performance_entry', 'approver_entry', 'seed', 'learning_loop')),
  -- Export conversation file and date; or the decision, card, brief, edit or published-piece ID.
  source_ref text NOT NULL,
  -- Every citation behind the item: conversation files, chunk reports, attachments, decisions, diffs.
  source_detail jsonb NOT NULL DEFAULT '{}'::jsonb,
  statement_date date,
  -- Whitney, a named team member, or 'model'.
  author text NOT NULL,
  model_written boolean NOT NULL DEFAULT false,
  confidence text CHECK (confidence IN ('low', 'medium', 'high')),
  supersedes_id text REFERENCES brand_kit_items,
  reviewed_by text,
  reviewed_at timestamptz,
  review_note text,
  embedding vector(1536),
  hash text NOT NULL,
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_kind, source_ref),
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from),
  -- Nothing is confirmed (or retired after confirmation) without a recorded reviewer (R51).
  CHECK (status NOT IN ('confirmed', 'retired') OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)),
  CHECK (kind <> 'result' OR permission IS NOT NULL),
  CHECK (permission IS NULL OR kind = 'result')
);
CREATE INDEX brand_kit_items_kind_status ON brand_kit_items (kind, status, key);
CREATE INDEX brand_kit_items_validity ON brand_kit_items (kind, valid_from, valid_to) WHERE status = 'confirmed';
CREATE INDEX brand_kit_items_supersedes ON brand_kit_items (supersedes_id) WHERE supersedes_id IS NOT NULL;

-- Content memory: what WIA published, linked to the card and brief behind it, with its performance (L.B1, L.B7, 3.B10).
CREATE TABLE published_content (
  content_id text PRIMARY KEY,
  published_on date,
  channel text NOT NULL CHECK (length(btrim(channel)) > 0),
  title text NOT NULL CHECK (length(btrim(title)) > 0),
  text text,
  key_message text,
  pillar text,
  content_type text,
  sibling_group text,
  status text NOT NULL CHECK (status IN ('unconfirmed', 'confirmed')),
  source_kind text NOT NULL CHECK (source_kind IN ('export_seed', 'published_import', 'approver_entry', 'approved_brief')),
  source_ref text NOT NULL,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  embedding vector(1536),
  -- No foreign key until 3.B1 creates topics.
  topic_id text,
  angle_id text REFERENCES content_angles,
  brief_id text REFERENCES content_briefs,
  -- One entry per measurement: {date, metric, value, source, entered_by}.
  performance jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(performance) = 'array'),
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_kind, source_ref)
);
CREATE INDEX published_content_date ON published_content (published_on DESC);
CREATE INDEX published_content_brief ON published_content (brief_id) WHERE brief_id IS NOT NULL;

-- Compiled knowledge-base versions (L.B4): the confirmed items behind each document, and whether an identity
-- change still waits for its benchmark smoke result (R44).
ALTER TABLE brand_kit_docs ADD COLUMN compiled_from jsonb;
ALTER TABLE brand_kit_docs ADD COLUMN benchmark_state text NOT NULL DEFAULT 'not_required'
  CHECK (benchmark_state IN ('not_required', 'pending', 'passed', 'failed'));

-- Decisions on knowledge-base versions and published pieces are audited like every other decision.
ALTER TABLE decisions DROP CONSTRAINT decisions_item_kind_check;
ALTER TABLE decisions ADD CONSTRAINT decisions_item_kind_check CHECK (item_kind IN ('angle', 'considered_idea', 'brief',
  'brand_kit_item', 'brand_kit_version', 'brand_kit_source', 'published_content', 'run_plan', 'seed'));
