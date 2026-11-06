-- Explicit additive migration. Existing schedules and assets are never fabricated.
ALTER TABLE content_packs ADD COLUMN source_brief_id text;
ALTER TABLE content_packs ADD COLUMN source_brief_hash text;
ALTER TABLE content_packs ADD COLUMN production_run_id text;
ALTER TABLE content_packs ADD COLUMN contract_version text;
ALTER TABLE calendar_entries ADD COLUMN revision integer NOT NULL DEFAULT 1 CHECK (revision > 0);
ALTER TABLE calendar_entries ADD COLUMN pack_manifest_hash text;
ALTER TABLE calendar_entries ADD COLUMN display_timezone text NOT NULL DEFAULT 'Asia/Kolkata';
ALTER TABLE calendar_entries ADD COLUMN created_by text;
ALTER TABLE calendar_entries ADD COLUMN updated_by text;
ALTER TABLE calendar_entries ADD CONSTRAINT calendar_status CHECK (status IN ('draft','scheduled','needs_review','cancelled','published'));
ALTER TABLE calendar_entries ADD CONSTRAINT active_calendar_has_time CHECK (status NOT IN ('scheduled','needs_review') OR scheduled_for IS NOT NULL);
CREATE UNIQUE INDEX calendar_active_asset_channel ON calendar_entries(asset_id,channel) WHERE status IN ('scheduled','needs_review');
CREATE TABLE mutation_receipts (
  request_id text PRIMARY KEY,
  actor text NOT NULL,
  operation text NOT NULL,
  request_hash text NOT NULL,
  response jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
