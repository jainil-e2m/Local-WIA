-- Explicit, additive upgrade. No historical sources are scanned or registered.
ALTER TABLE transcripts ALTER COLUMN week_id DROP NOT NULL;
ALTER TABLE pipeline_runs ALTER COLUMN week_id DROP NOT NULL;
ALTER TABLE pipeline_jobs ALTER COLUMN week_id DROP NOT NULL;
ALTER TABLE pipeline_jobs ADD COLUMN executor text NOT NULL DEFAULT 'postgres'
  CHECK (executor IN ('postgres','rq'));

CREATE TABLE intake_connections (
  connection_id text PRIMARY KEY,
  provider text NOT NULL CHECK (provider IN ('fathom','slack')),
  activated_at timestamptz NOT NULL,
  checkpoint timestamptz NOT NULL,
  config jsonb NOT NULL,
  health text NOT NULL DEFAULT 'ready',
  error_summary text,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE intake_buckets (
  bucket_id text PRIMARY KEY,
  starts_at timestamptz NOT NULL UNIQUE,
  cutoff timestamptz,
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','collecting','completed')),
  completed_at timestamptz,
  CHECK (cutoff IS NULL OR cutoff > starts_at)
);
CREATE UNIQUE INDEX intake_one_open_bucket ON intake_buckets ((true)) WHERE status = 'open';
CREATE UNIQUE INDEX intake_one_collecting_bucket ON intake_buckets ((true)) WHERE status = 'collecting';
CREATE TABLE intake_requests (
  request_id text PRIMARY KEY,
  connection_id text NOT NULL REFERENCES intake_connections,
  bucket_id text NOT NULL REFERENCES intake_buckets,
  window_start timestamptz NOT NULL,
  window_end timestamptz NOT NULL,
  coverage jsonb NOT NULL DEFAULT '{}',
  status text NOT NULL DEFAULT 'pending',
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (window_end >= window_start)
);
CREATE TABLE intake_batches (
  batch_id text PRIMARY KEY,
  request_id text NOT NULL REFERENCES intake_requests,
  content_hash text NOT NULL,
  raw_artifact text NOT NULL,
  status text NOT NULL DEFAULT 'received',
  received_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE intake_sources (
  source_id text PRIMARY KEY,
  connection_id text NOT NULL REFERENCES intake_connections,
  upstream_id text NOT NULL,
  kind text NOT NULL,
  title text NOT NULL,
  source_url text,
  occurred_at timestamptz,
  latest_revision_id text,
  provider_updated_at timestamptz,
  status text NOT NULL DEFAULT 'received',
  metadata jsonb NOT NULL DEFAULT '{}',
  received_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (connection_id, upstream_id)
);
CREATE TABLE intake_revisions (
  revision_id text PRIMARY KEY,
  source_id text NOT NULL REFERENCES intake_sources,
  transcript_id text UNIQUE REFERENCES transcripts,
  content_hash text NOT NULL,
  raw_artifact text NOT NULL,
  collection_status text NOT NULL DEFAULT 'received',
  extraction_status text NOT NULL DEFAULT 'pending',
  indexing_status text NOT NULL DEFAULT 'pending',
  deleted boolean NOT NULL DEFAULT false,
  error_summary text,
  received_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_id, content_hash)
);
ALTER TABLE intake_sources ADD FOREIGN KEY (latest_revision_id) REFERENCES intake_revisions;
CREATE TABLE intake_membership (
  bucket_id text NOT NULL REFERENCES intake_buckets,
  revision_id text NOT NULL REFERENCES intake_revisions,
  PRIMARY KEY (bucket_id, revision_id)
);
CREATE TABLE intake_assets (
  asset_id text PRIMARY KEY,
  revision_id text NOT NULL REFERENCES intake_revisions,
  provider_file_id text NOT NULL,
  filename text NOT NULL,
  mime_type text NOT NULL,
  expected_hash text,
  size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
  content_hash text,
  raw_artifact text,
  source_id text REFERENCES intake_sources,
  status text NOT NULL DEFAULT 'awaiting_upload',
  metadata jsonb NOT NULL DEFAULT '{}',
  UNIQUE (revision_id, provider_file_id)
);
CREATE INDEX intake_revision_source ON intake_revisions(source_id,received_at);
CREATE INDEX intake_request_pending ON intake_requests(status,connection_id);
CREATE INDEX intake_member_revision ON intake_membership(revision_id);
CREATE TABLE intake_schema_migrations (
  version text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO intake_schema_migrations(version) VALUES ('003_future_intake');
