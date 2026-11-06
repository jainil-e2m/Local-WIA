-- Migration 007 (plan label 006; 1.B1, sections 4.8 and 9). Additive; needs 005 and 006.
-- The plan numbers migrations in planned order and the runner assigns the next free number at merge: Phase L's
-- context store took 006, so the evidence model is file 007 and the plan's 007 to 009 (Phases 2 to 5) shift by one.
-- Gives every document an identity of its own (not a week's), a call type and an inclusion decision with a reason,
-- an occurrence date with a recorded source, participants with roles, and a link to its canonical copy; gives chunks a
-- header, a date, speaker roles, the embedding model that produced the vector and a full-text column; and creates the
-- reference tables: clients, people, the glossary and the Slack channels each connection reads.

CREATE TABLE clients (
  client_id text PRIMARY KEY,
  name text NOT NULL CHECK (length(btrim(name)) > 0),
  aliases jsonb NOT NULL DEFAULT '[]'::jsonb,
  -- What may be said in public about this client: anonymise_only until a person records more (R48).
  consent text NOT NULL DEFAULT 'anonymise_only' CHECK (consent IN ('anonymise_only', 'may_name', 'no_use')),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'former')),
  notes text,
  source text NOT NULL DEFAULT 'reviewed_list',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX clients_name_unique ON clients (lower(name));

CREATE TABLE people (
  person_id text PRIMARY KEY,
  name text NOT NULL CHECK (length(btrim(name)) > 0),
  role text NOT NULL CHECK (role IN ('staff', 'client', 'prospect', 'vendor', 'outside', 'ai_agent')),
  status text NOT NULL DEFAULT 'current' CHECK (status IN ('current', 'former')),
  title text,
  -- Every way a transcript may write the name (first name, mis-transcriptions). The roster item is the editing surface.
  aliases jsonb NOT NULL DEFAULT '[]'::jsonb,
  email text,
  slack_user_id text,
  client_id text REFERENCES clients,
  -- The key of the confirmed roster item this row mirrors (brand_kit_items.key); null for people the roster does not hold.
  roster_key text,
  source text NOT NULL CHECK (source IN ('roster', 'corpus', 'call', 'manual')),
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (client_id IS NULL OR role IN ('client', 'prospect'))
);
CREATE UNIQUE INDEX people_email_unique ON people (lower(email)) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX people_roster_key_unique ON people (roster_key) WHERE roster_key IS NOT NULL;
CREATE INDEX people_role ON people (role, status);

CREATE TABLE glossary_terms (
  term_id text PRIMARY KEY,
  term text NOT NULL CHECK (length(btrim(term)) > 0),
  kind text NOT NULL CHECK (kind IN ('product', 'staff', 'client', 'other')),
  -- Common mis-transcriptions and spelling variants of the term.
  variants jsonb NOT NULL DEFAULT '[]'::jsonb,
  notes text,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'retired')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX glossary_terms_term_unique ON glossary_terms (lower(term));

CREATE TABLE slack_channels (
  channel_id text PRIMARY KEY,
  -- The live Slack connection that reads the channel; null for a channel known only from a workspace export (1.B7).
  connection_id text REFERENCES intake_connections,
  name text,
  workspace text,
  included boolean NOT NULL DEFAULT true,
  exclusion_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (included OR exclusion_reason IS NOT NULL)
);
CREATE INDEX slack_channels_connection ON slack_channels (connection_id) WHERE connection_id IS NOT NULL;

ALTER TABLE transcripts
  -- Where occurred_at came from: the provider, a filename, Zoom's recording list, a calendar export, or a person.
  -- 'unknown' (with occurred_at null) is an explicit statement that no evidence dates the document. A week is never a source.
  ADD COLUMN occurred_at_source text CHECK (occurred_at_source IN ('provider', 'filename', 'content', 'zoom_listing', 'calendar', 'manual', 'unknown')),
  ADD COLUMN call_type text CHECK (call_type IN ('client_1to1', 'office_hours', 'workshop', 'prospect', 'internal', 'vendor', 'fragment', 'slack_thread', 'other')),
  ADD COLUMN included boolean NOT NULL DEFAULT true,
  ADD COLUMN exclusion_reason text,
  ADD COLUMN client_id text REFERENCES clients,
  -- The distinct people in the call with a role each: [{name, role, person_id, basis, inferred}].
  ADD COLUMN participants jsonb NOT NULL DEFAULT '[]'::jsonb,
  -- Speaker label -> {person_id, role, basis, inferred}, stored beside the immutable passage map, never inside it.
  ADD COLUMN speaker_map jsonb,
  ADD COLUMN canonical_document_id text REFERENCES transcripts (transcript_id),
  ADD COLUMN raw_object_key text,
  -- How call_type was decided: {method: rule|model|person, reason, rule_version, decided_by, decided_at}.
  ADD COLUMN classification jsonb,
  ADD COLUMN normaliser_version text,
  ADD COLUMN normalised_at timestamptz,
  -- Whether scenes were extracted from this document (Phase 2 fills them in): pending, queued, running, completed, failed.
  ADD COLUMN extraction_status text NOT NULL DEFAULT 'pending' CHECK (extraction_status IN ('pending', 'queued', 'running', 'completed', 'failed', 'not_applicable')),
  ADD CONSTRAINT transcripts_exclusion_has_reason CHECK (included OR exclusion_reason IS NOT NULL),
  ADD CONSTRAINT transcripts_not_its_own_canonical CHECK (canonical_document_id IS NULL OR canonical_document_id <> transcript_id);

CREATE INDEX transcripts_occurred_at ON transcripts (occurred_at) WHERE included;
CREATE INDEX transcripts_call_type ON transcripts (call_type, included);
CREATE INDEX transcripts_client ON transcripts (client_id) WHERE client_id IS NOT NULL;
CREATE INDEX transcripts_canonical ON transcripts (canonical_document_id) WHERE canonical_document_id IS NOT NULL;

ALTER TABLE transcript_chunks
  ADD COLUMN header text,
  ADD COLUMN occurred_at timestamptz,
  ADD COLUMN speaker_roles jsonb,
  -- The model that produced the stored vector (the embedding contract's model), null while unembedded.
  ADD COLUMN embedding_model text,
  ADD COLUMN segmentation_version text NOT NULL DEFAULT 'v1',
  -- A re-segmentation adds rows and retires the old ones; retired rows stay readable for what already cites them.
  ADD COLUMN is_current boolean NOT NULL DEFAULT true,
  -- The glossary-normalised copy full-text search reads. The original text is never changed.
  ADD COLUMN search_text text,
  ADD COLUMN tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(search_text, chunk_text))) STORED;

CREATE INDEX transcript_chunks_tsv ON transcript_chunks USING gin (tsv);
CREATE INDEX transcript_chunks_current ON transcript_chunks (transcript_id) WHERE is_current;

-- Existing rows keep their data; the new columns state what is already known about them.
UPDATE transcripts SET occurred_at_source = 'provider' WHERE occurred_at IS NOT NULL;
UPDATE transcripts t SET raw_object_key = 'source-originals/' || t.content_hash || '.original'
  WHERE t.source_type IN ('zoom', 'fathom', 'manual') AND t.week_id IS NOT NULL;
UPDATE transcripts t SET raw_object_key = r.raw_artifact
  FROM intake_revisions r WHERE r.transcript_id = t.transcript_id;
UPDATE transcripts t SET extraction_status = 'completed'
  WHERE EXISTS (SELECT 1 FROM pipeline_jobs j JOIN pipeline_runs r USING (run_id)
    WHERE j.stage = 'moment_extraction' AND j.status = 'completed'
      AND r.input_refs->'transcripts' @> jsonb_build_array(jsonb_build_object('id', t.transcript_id)));
UPDATE transcript_chunks SET embedding_model = 'openai/text-embedding-3-small' WHERE embedding IS NOT NULL;
UPDATE transcript_chunks c SET occurred_at = t.occurred_at FROM transcripts t WHERE t.transcript_id = c.transcript_id;

COMMENT ON TABLE people IS 'One source for people: WIA staff (mirroring the confirmed roster), clients, prospects, vendors and outside names. Speakers in a passage map resolve to these rows.';
COMMENT ON TABLE clients IS 'Clients from a reviewed list kept outside the repository. consent defaults to anonymise_only.';
COMMENT ON COLUMN transcripts.occurred_at_source IS 'Evidence behind occurred_at; unknown means explicitly undated. Never derived from an admission week.';
COMMENT ON COLUMN transcripts.speaker_map IS 'Speaker label to person and role, beside the immutable passage_map. Zoom roles are inferred from names and marked so.';
COMMENT ON COLUMN transcript_chunks.search_text IS 'Glossary-normalised copy for search only; chunk_text and the original text are never altered.';
