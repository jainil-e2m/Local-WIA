-- Approved thirteen-table baseline. Run only through storage_cli init.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE "weeks" (
  "week_id" text PRIMARY KEY,
  "week_start" date NOT NULL,
  "week_end" date NOT NULL,
  "status" text NOT NULL DEFAULT 'pending',
  "active_run_id" text,
  "coverage_notes" jsonb,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "week_has_seven_inclusive_dates" CHECK (week_end = week_start + 6)
);

CREATE TABLE "pipeline_runs" (
  "run_id" text PRIMARY KEY,
  "week_id" text NOT NULL,
  "run_scope" text NOT NULL,
  "status" text NOT NULL DEFAULT 'queued',
  "current_message" text,
  "error_summary" text,
  "has_partial_failures" boolean NOT NULL DEFAULT false,
  "trigger_type" text NOT NULL,
  "triggered_by" text,
  "input_refs" jsonb NOT NULL,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "started_at" timestamptz,
  "finished_at" timestamptz,
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "run_status_is_valid" CHECK (status IN ('queued', 'running', 'waiting_for_review', 'completed', 'partially_completed', 'failed', 'cancelled'))
);

CREATE TABLE "transcripts" (
  "transcript_id" text PRIMARY KEY,
  "week_id" text NOT NULL,
  "source_type" text NOT NULL,
  "upstream_id" text,
  "title" text NOT NULL,
  "source_url" text,
  "occurred_at" timestamptz,
  "original_text" text NOT NULL,
  "passage_map" jsonb NOT NULL,
  "content_hash" text NOT NULL,
  "source_metadata" jsonb,
  "use_restrictions" jsonb,
  "processing_status" text NOT NULL DEFAULT 'pending',
  "ingested_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "transcript_chunks" (
  "chunk_id" text PRIMARY KEY,
  "transcript_id" text NOT NULL,
  "chunk_text" text NOT NULL,
  "passage_refs" jsonb NOT NULL,
  "content_hash" text NOT NULL,
  "embedding" vector(1536)
);

CREATE TABLE "key_moments" (
  "moment_id" text PRIMARY KEY,
  "week_id" text NOT NULL,
  "run_id" text NOT NULL,
  "moment_body" jsonb NOT NULL,
  "evidence_refs" jsonb NOT NULL,
  "created_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "content_angles" (
  "angle_id" text PRIMARY KEY,
  "week_id" text NOT NULL,
  "run_id" text NOT NULL,
  "supersedes_id" text,
  "content_body" jsonb NOT NULL,
  "quality_scores" jsonb,
  "base_score" numeric,
  "adjusted_score" numeric,
  "selection_status" text NOT NULL DEFAULT 'candidate',
  "matching_result" jsonb,
  "selected_cta" jsonb,
  "content_hash" text NOT NULL,
  "embedding_input_hash" text,
  "embedding" vector(1536),
  "first_generated_at" timestamptz NOT NULL,
  "approval_status" text NOT NULL DEFAULT 'pending',
  "approved_hash" text,
  "approved_by" text,
  "approved_at" timestamptz,
  "review_note" text,
  "updated_by" text,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "angle_scores_in_range" CHECK ((base_score IS NULL OR base_score BETWEEN 0 AND 100) AND (adjusted_score IS NULL OR adjusted_score BETWEEN 0 AND 100)),
  CONSTRAINT "angle_vector_has_input_hash" CHECK ((embedding IS NULL) = (embedding_input_hash IS NULL)),
  CONSTRAINT "angle_approval_is_bound" CHECK (approval_status <> 'approved' OR (approved_hash IS NOT NULL AND approved_hash = content_hash AND approved_by IS NOT NULL AND approved_at IS NOT NULL AND selected_cta IS NOT NULL))
);

CREATE TABLE "angle_moments" (
  "angle_id" text NOT NULL,
  "moment_id" text NOT NULL,
  "evidence_role" text NOT NULL,
  PRIMARY KEY ("angle_id", "moment_id")
);

CREATE TABLE "content_briefs" (
  "brief_id" text PRIMARY KEY,
  "week_id" text NOT NULL,
  "angle_id" text NOT NULL,
  "angle_input_hash" text NOT NULL,
  "supersedes_id" text,
  "content_body" jsonb NOT NULL,
  "selected_evidence" jsonb NOT NULL,
  "prior_content_context" jsonb NOT NULL,
  "research_gaps" jsonb,
  "content_hash" text NOT NULL,
  "approval_status" text NOT NULL DEFAULT 'pending',
  "approved_hash" text,
  "approved_by" text,
  "approved_at" timestamptz,
  "review_note" text,
  "updated_by" text,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "brief_approval_is_bound" CHECK (approval_status <> 'approved' OR (approved_hash IS NOT NULL AND approved_hash = content_hash AND approved_by IS NOT NULL AND approved_at IS NOT NULL))
);

CREATE TABLE "content_packs" (
  "pack_id" text PRIMARY KEY,
  "week_id" text NOT NULL,
  "supersedes_id" text,
  "title" text NOT NULL,
  "manifest_hash" text,
  "validation_result" jsonb,
  "approval_status" text NOT NULL DEFAULT 'pending',
  "approved_hash" text,
  "approved_by" text,
  "approved_at" timestamptz,
  "review_note" text,
  "updated_by" text,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "pack_approval_is_bound" CHECK (approval_status <> 'approved' OR (manifest_hash IS NOT NULL AND approved_hash IS NOT NULL AND approved_hash = manifest_hash AND approved_by IS NOT NULL AND approved_at IS NOT NULL))
);

CREATE TABLE "content_assets" (
  "asset_id" text PRIMARY KEY,
  "pack_id" text NOT NULL,
  "brief_id" text NOT NULL,
  "brief_input_hash" text NOT NULL,
  "supersedes_id" text,
  "slot_key" text NOT NULL,
  "ordinal" integer NOT NULL,
  "asset_type" text NOT NULL,
  "reader_contribution" text NOT NULL,
  "status" text NOT NULL DEFAULT 'planned',
  "content_body" jsonb,
  "content_hash" text,
  "validation_result" jsonb,
  "updated_by" text,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "asset_order_is_positive" CHECK (ordinal > 0),
  CONSTRAINT "asset_content_has_hash" CHECK ((content_body IS NULL) = (content_hash IS NULL)),
  CONSTRAINT "generated_asset_has_content" CHECK (status = 'planned' OR content_body IS NOT NULL)
);

CREATE TABLE "calendar_entries" (
  "calendar_entry_id" text PRIMARY KEY,
  "asset_id" text NOT NULL,
  "asset_content_hash" text NOT NULL,
  "channel" text NOT NULL,
  "scheduled_for" timestamptz,
  "status" text NOT NULL DEFAULT 'draft',
  "external_schedule_id" text,
  "published_at" timestamptz,
  "published_url" text,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "scheduled_entry_has_time" CHECK (status <> 'scheduled' OR scheduled_for IS NOT NULL),
  CONSTRAINT "published_entry_has_confirmation_time" CHECK (status <> 'published' OR published_at IS NOT NULL)
);

CREATE TABLE "pipeline_jobs" (
  "job_id" text PRIMARY KEY,
  "run_id" text NOT NULL,
  "week_id" text NOT NULL,
  "stage" text NOT NULL,
  "transcript_id" text,
  "angle_id" text,
  "brief_id" text,
  "pack_id" text,
  "asset_id" text,
  "calendar_entry_id" text,
  "status" text NOT NULL DEFAULT 'queued',
  "current_step" text,
  "current_message" text,
  "completed_units" integer,
  "total_units" integer,
  "progress_details" jsonb,
  "idempotency_key" text UNIQUE NOT NULL,
  "input_hash" text,
  "attempt_count" integer NOT NULL DEFAULT 0,
  "result_refs" jsonb,
  "error_summary" text,
  "lease_token" text,
  "lease_expires_at" timestamptz,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  "started_at" timestamptz,
  "finished_at" timestamptz,
  "heartbeat_at" timestamptz,
  CONSTRAINT "job_has_at_most_one_target" CHECK (num_nonnulls(transcript_id, angle_id, brief_id, pack_id, asset_id, calendar_entry_id) <= 1),
  CONSTRAINT "job_attempt_count_nonnegative" CHECK (attempt_count >= 0),
  CONSTRAINT "job_progress_units_nonnegative" CHECK ((completed_units IS NULL OR completed_units >= 0) AND (total_units IS NULL OR total_units >= 0)),
  CONSTRAINT "job_progress_units_in_range" CHECK (completed_units IS NULL OR total_units IS NULL OR completed_units <= total_units),
  CONSTRAINT "job_lease_is_complete" CHECK (num_nonnulls(lease_token, lease_expires_at) IN (0, 2))
);

CREATE TABLE "pipeline_events" (
  "event_id" text PRIMARY KEY,
  "run_id" text NOT NULL,
  "job_id" text,
  "event_type" text NOT NULL,
  "severity" text NOT NULL DEFAULT 'info',
  "message" text NOT NULL,
  "attempt_number" integer,
  "details" jsonb,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "event_attempt_number_positive" CHECK (attempt_number IS NULL OR attempt_number >= 1)
);

CREATE UNIQUE INDEX ON "weeks" ("week_start");

CREATE INDEX ON "pipeline_runs" ("week_id", "created_at");

CREATE INDEX ON "pipeline_runs" ("status", "updated_at");

CREATE UNIQUE INDEX ON "transcripts" ("source_type", "upstream_id", "content_hash");

CREATE INDEX ON "transcripts" ("week_id");

CREATE UNIQUE INDEX ON "transcript_chunks" ("transcript_id", "content_hash");

CREATE INDEX ON "key_moments" ("week_id", "run_id");

CREATE INDEX ON "content_angles" ("week_id", "run_id", "selection_status");

CREATE UNIQUE INDEX ON "content_assets" ("pack_id", "slot_key");

CREATE UNIQUE INDEX ON "content_assets" ("pack_id", "ordinal");

CREATE INDEX ON "calendar_entries" ("scheduled_for", "status");

CREATE INDEX ON "calendar_entries" ("asset_id");

CREATE INDEX ON "pipeline_jobs" ("week_id", "run_id", "stage");

CREATE INDEX ON "pipeline_jobs" ("status", "lease_expires_at");

CREATE INDEX ON "pipeline_events" ("run_id", "created_at", "event_id");

CREATE INDEX ON "pipeline_events" ("job_id", "created_at");

COMMENT ON COLUMN "weeks"."active_run_id" IS 'Run currently shown in the weekly UI; it must belong to this week.';

COMMENT ON TABLE "pipeline_runs" IS 'One actual execution, separate from its calendar week. input_refs freezes admitted content IDs/hashes and requested scope before work starts; no transcript copies or model configuration. Job retries stay inside the same run. Completion is relative to the requested scope.';

COMMENT ON COLUMN "pipeline_runs"."run_scope" IS 'Actual requested work, such as weekly_angles, brief_generation, pack_generation or scheduling.';

COMMENT ON COLUMN "pipeline_runs"."trigger_type" IS 'scheduled, manual or source_update.';

COMMENT ON COLUMN "pipeline_runs"."triggered_by" IS 'Existing authenticated subject for a human-triggered run.';

COMMENT ON TABLE "transcripts" IS 'Preserved source text plus stable passage IDs, original-text offsets, speakers and available timestamps in passage_map. Metadata contains known facts only. Changed captured input gets a new row; cited originals stay stable.';

COMMENT ON COLUMN "transcripts"."source_type" IS 'fathom, zoom or manual; identifies actual source provenance.';

COMMENT ON COLUMN "transcripts"."upstream_id" IS 'Namespace by provider/account/source identity; null for manual inputs.';

COMMENT ON TABLE "transcript_chunks" IS 'Contextualized embedding input and ordered references into its transcript passage_map. Null embedding means unavailable for vector retrieval. Preserve chunks already cited in briefs.';

COMMENT ON TABLE "key_moments" IS 'Validated Call 1 content: quote, proposition, type, context, qualifications, audience relevance, strength, reasons, claim status and sensitivity. evidence_refs supplies transcript/passage IDs and anchor/context/qualification roles; a moment may use multiple transcripts.';

COMMENT ON TABLE "content_angles" IS 'Validated Call 2 arguments, including valid suppressed candidates. content_body holds title, argument, audience, tension, take, mechanism, reader decision, assertions, inference, qualifiers and risks. UI selects visible records. Preserve original generation age on reuse or edited copies of the same logical angle.';

COMMENT ON TABLE "content_briefs" IS 'Editable brief contract, required questions/answers and CTA. angle_input_hash pins the approved angle consumed. Selected evidence retains exact internal locations or external URLs and qualifications. Prior context retains actual old angle/brief/asset IDs, compact coverage and known approval/publication state.';

COMMENT ON TABLE "content_packs" IS 'Production grouping; assets below contain the copy. manifest_hash covers ordered slots, exact asset IDs/content hashes and governing brief input hashes. Final approval requires complete assigned assets and current successful checks.';

COMMENT ON TABLE "content_assets" IS 'One actual assigned deliverable and governing approved brief. Body/hash are null before generation. Email fields, ordered carousel slides/caption or reel script/shot directions stay in JSON. Each asset has one owning pack; edits to a consumed pack use a replacement pack and asset records.';

COMMENT ON COLUMN "content_assets"."asset_type" IS 'email, carousel or reel; no fixed asset-count cap.';

COMMENT ON TABLE "calendar_entries" IS 'Schedules the exact asset content, not an entire pack or a JSON array position. Publishing instants use timestamptz; display timezone stays in application configuration. Published state requires actual confirmation.';

COMMENT ON TABLE "pipeline_jobs" IS 'One stage execution for the whole week or one target. Same-stage brief/asset jobs can run independently. current_step/message/details supply UI updates; unit counts are null when unmeasurable. result_refs contains output IDs and completed per-run reassessment. A retry updates this job and appends events; leases support recovery.';

COMMENT ON TABLE "pipeline_events" IS 'Append-only meaningful process milestones, warnings, retries and failures. A referenced job must belong to the event run. Approval events reference the actual content decision; they do not grant approval. Small payloads only; periodic heartbeats remain on jobs.';

ALTER TABLE "weeks" ADD FOREIGN KEY ("active_run_id") REFERENCES "pipeline_runs" ("run_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "pipeline_runs" ADD FOREIGN KEY ("week_id") REFERENCES "weeks" ("week_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "transcripts" ADD FOREIGN KEY ("week_id") REFERENCES "weeks" ("week_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "transcript_chunks" ADD FOREIGN KEY ("transcript_id") REFERENCES "transcripts" ("transcript_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "key_moments" ADD FOREIGN KEY ("week_id") REFERENCES "weeks" ("week_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "key_moments" ADD FOREIGN KEY ("run_id") REFERENCES "pipeline_runs" ("run_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_angles" ADD FOREIGN KEY ("week_id") REFERENCES "weeks" ("week_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_angles" ADD FOREIGN KEY ("run_id") REFERENCES "pipeline_runs" ("run_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_angles" ADD FOREIGN KEY ("supersedes_id") REFERENCES "content_angles" ("angle_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "angle_moments" ADD FOREIGN KEY ("angle_id") REFERENCES "content_angles" ("angle_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "angle_moments" ADD FOREIGN KEY ("moment_id") REFERENCES "key_moments" ("moment_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_briefs" ADD FOREIGN KEY ("week_id") REFERENCES "weeks" ("week_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_briefs" ADD FOREIGN KEY ("angle_id") REFERENCES "content_angles" ("angle_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_briefs" ADD FOREIGN KEY ("supersedes_id") REFERENCES "content_briefs" ("brief_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_packs" ADD FOREIGN KEY ("week_id") REFERENCES "weeks" ("week_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_packs" ADD FOREIGN KEY ("supersedes_id") REFERENCES "content_packs" ("pack_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_assets" ADD FOREIGN KEY ("pack_id") REFERENCES "content_packs" ("pack_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_assets" ADD FOREIGN KEY ("brief_id") REFERENCES "content_briefs" ("brief_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_assets" ADD FOREIGN KEY ("supersedes_id") REFERENCES "content_assets" ("asset_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "calendar_entries" ADD FOREIGN KEY ("asset_id") REFERENCES "content_assets" ("asset_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "pipeline_jobs" ADD FOREIGN KEY ("run_id") REFERENCES "pipeline_runs" ("run_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "pipeline_jobs" ADD FOREIGN KEY ("week_id") REFERENCES "weeks" ("week_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "pipeline_jobs" ADD FOREIGN KEY ("transcript_id") REFERENCES "transcripts" ("transcript_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "pipeline_jobs" ADD FOREIGN KEY ("angle_id") REFERENCES "content_angles" ("angle_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "pipeline_jobs" ADD FOREIGN KEY ("brief_id") REFERENCES "content_briefs" ("brief_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "pipeline_jobs" ADD FOREIGN KEY ("pack_id") REFERENCES "content_packs" ("pack_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "pipeline_jobs" ADD FOREIGN KEY ("asset_id") REFERENCES "content_assets" ("asset_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "pipeline_jobs" ADD FOREIGN KEY ("calendar_entry_id") REFERENCES "calendar_entries" ("calendar_entry_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "pipeline_events" ADD FOREIGN KEY ("run_id") REFERENCES "pipeline_runs" ("run_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "pipeline_events" ADD FOREIGN KEY ("job_id") REFERENCES "pipeline_jobs" ("job_id") DEFERRABLE INITIALLY IMMEDIATE;

CREATE INDEX angle_moments_reverse ON angle_moments(moment_id);
