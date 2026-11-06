-- Migration 008 (plan label 007; 2.B1, sections 4.8 and 10). Additive; needs 005 and 007.
-- The plan numbers migrations in planned order and the runner assigns the next free number at merge: Phase L's context
-- store took 006 and the evidence model 007, so the moments ledger is file 008.
-- Turns `key_moments` from a week's by-product into the ledger: a scene belongs to a document, not to a week or a run;
-- it states who said it and in what role, whether its quote binds the source, what may be said in public about it, and
-- carries its own search copy and vector. `topics` and `moment_topics` follow (2.B7). Existing moments are promoted from
-- `moment_body` and `evidence_refs`, never regenerated, and the unverified moments the weekly path kept only in a job's
-- `result_refs` (E.B12a) become rows with `quote_verified = false`.

ALTER TABLE key_moments
  ALTER COLUMN week_id DROP NOT NULL,
  ALTER COLUMN run_id DROP NOT NULL,
  -- The document the moment's first anchor passage belongs to.
  ADD COLUMN document_id text REFERENCES transcripts (transcript_id),
  ADD COLUMN moment_type text,
  -- Who said the anchor line: the label as the transcript writes it, and the person and role it resolves to (1.B5).
  ADD COLUMN speaker_label text,
  ADD COLUMN speaker_id text REFERENCES people (person_id),
  ADD COLUMN speaker_role text NOT NULL DEFAULT 'unknown'
    CHECK (speaker_role IN ('staff', 'client', 'prospect', 'vendor', 'outside', 'ai_agent', 'unknown')),
  -- direct_quote: said by the person it is credited to; team_report: a staff member relaying a result or praise;
  -- screenshot_text: text read from an image or pasted in (2.B13, deferred).
  ADD COLUMN evidence_kind text NOT NULL DEFAULT 'direct_quote'
    CHECK (evidence_kind IN ('direct_quote', 'team_report', 'screenshot_text')),
  ADD COLUMN client_id text REFERENCES clients (client_id),
  -- cleared: the client allows named use; anonymise: the default; internal_only; do_not_use. Derived by the backend from
  -- the client's consent level and the sensitivity (moments/checks.py); the browser never decides it.
  ADD COLUMN consent_status text NOT NULL DEFAULT 'anonymise'
    CHECK (consent_status IN ('cleared', 'anonymise', 'internal_only', 'do_not_use')),
  -- true: the quote is in the source (exact, or repaired to the source's own text with the repair recorded).
  -- false: kept as a record, never proof, never embedded, never sent to a strategist.
  ADD COLUMN quote_verified boolean NOT NULL DEFAULT true,
  ADD COLUMN quote_repair jsonb,
  ADD COLUMN unverified_reason text,
  ADD COLUMN sensitivity text CHECK (sensitivity IN ('public_candidate', 'internal_only', 'unknown')),
  ADD COLUMN destination text CHECK (destination IN ('public_opportunity', 'internal_intelligence', 'research_needed')),
  ADD COLUMN occurred_at timestamptz,
  ADD COLUMN extractor_version text,
  -- The deterministic checks' results (2.B4): role plausibility, numbers, consent; see moments/checks.py.
  ADD COLUMN checks jsonb NOT NULL DEFAULT '{}'::jsonb,
  -- A document extracted again under a newer extractor leaves its older moments readable but not current; cards and
  -- briefs that cite them keep working.
  ADD COLUMN is_current boolean NOT NULL DEFAULT true,
  ADD COLUMN embedding vector(1536),
  ADD COLUMN embedding_model text,
  ADD COLUMN embedding_input_hash text,
  ADD COLUMN tsv tsvector GENERATED ALWAYS AS (to_tsvector('english',
    coalesce(moment_body->>'quote', '') || ' ' || coalesce(moment_body->>'context_summary', '') || ' ' ||
    coalesce(moment_body->>'proposition', ''))) STORED,
  ADD CONSTRAINT key_moments_vector_has_input_hash CHECK ((embedding IS NULL) = (embedding_input_hash IS NULL)),
  ADD CONSTRAINT key_moments_vector_has_model CHECK (embedding IS NULL OR embedding_model IS NOT NULL),
  ADD CONSTRAINT key_moments_unverified_has_no_vector CHECK (quote_verified OR embedding IS NULL),
  ADD CONSTRAINT key_moments_unverified_has_reason CHECK (quote_verified OR unverified_reason IS NOT NULL);

CREATE INDEX key_moments_document ON key_moments (document_id) WHERE document_id IS NOT NULL;
CREATE INDEX key_moments_client ON key_moments (client_id) WHERE client_id IS NOT NULL;
CREATE INDEX key_moments_occurred_at ON key_moments (occurred_at);
CREATE INDEX key_moments_type ON key_moments (moment_type);
CREATE INDEX key_moments_searchable ON key_moments (consent_status, speaker_role) WHERE quote_verified AND is_current;
CREATE INDEX key_moments_tsv ON key_moments USING gin (tsv);

-- 1. Promote what the existing moments already say. The first anchor passage gives the document and the speaker.
WITH anchors AS (
  SELECT DISTINCT ON (m.moment_id) m.moment_id, e.r->>'transcript_id' AS transcript_id, e.r->>'passage_id' AS passage_id
  FROM key_moments m, LATERAL jsonb_array_elements(m.evidence_refs) WITH ORDINALITY AS e(r, n)
  WHERE e.r->'roles' ? 'anchor'
  ORDER BY m.moment_id, e.n
), promoted AS (
  SELECT a.moment_id, t.transcript_id AS document_id, t.occurred_at, t.client_id, p.p->>'speaker' AS speaker_label,
         t.speaker_map -> (p.p->>'speaker') AS mapped
  FROM anchors a
  JOIN transcripts t ON t.transcript_id = a.transcript_id
  LEFT JOIN LATERAL (SELECT x AS p FROM jsonb_array_elements(t.passage_map) x WHERE x->>'passage_id' = a.passage_id LIMIT 1) p ON true
)
UPDATE key_moments m SET
  document_id = promoted.document_id,
  occurred_at = promoted.occurred_at,
  client_id = promoted.client_id,
  speaker_label = promoted.speaker_label,
  speaker_id = (SELECT person_id FROM people WHERE person_id = promoted.mapped->>'person_id'),
  speaker_role = CASE WHEN promoted.mapped->>'role' IN ('staff', 'client', 'prospect', 'vendor', 'outside', 'ai_agent')
                      THEN promoted.mapped->>'role' ELSE 'unknown' END
FROM promoted WHERE promoted.moment_id = m.moment_id;

UPDATE key_moments SET
  moment_type = moment_body->>'moment_type',
  sensitivity = CASE WHEN moment_body->>'sensitivity' IN ('public_candidate', 'internal_only', 'unknown')
                     THEN moment_body->>'sensitivity' END,
  destination = CASE WHEN moment_body->'discovery'->>'destination' IN ('public_opportunity', 'internal_intelligence', 'research_needed')
                     THEN moment_body->'discovery'->>'destination' END;

-- The same rules moments/checks.py applies to a new moment; a test keeps the two in agreement. A result or testimonial
-- spoken by anyone other than a client or prospect is a staff member relaying it (or a speaker the roster cannot place,
-- which is treated the same way until the document is normalised).
UPDATE key_moments SET evidence_kind = 'team_report'
WHERE moment_type IN ('result', 'testimonial') AND speaker_role NOT IN ('client', 'prospect');

UPDATE key_moments m SET consent_status = CASE
  WHEN c.consent = 'no_use' THEN 'do_not_use'
  WHEN m.sensitivity = 'internal_only' THEN 'internal_only'
  WHEN c.consent = 'may_name' AND m.sensitivity = 'public_candidate' AND m.evidence_kind = 'direct_quote' THEN 'cleared'
  ELSE 'anonymise' END
FROM clients c WHERE c.client_id = m.client_id;
UPDATE key_moments SET consent_status = 'internal_only' WHERE client_id IS NULL AND sensitivity = 'internal_only';

-- The extractor each existing moment came from: the profile its extraction job recorded, else the weekly default.
UPDATE key_moments m SET extractor_version = COALESCE(
  (SELECT j.result_refs->>'extraction_profile' FROM pipeline_jobs j
    WHERE j.run_id = m.run_id AND j.stage = 'moment_extraction' AND j.status = 'completed' LIMIT 1),
  '2026-10-13.weekly.v3')
WHERE m.run_id IS NOT NULL;

-- 2. The unverified moments the weekly path kept only in a job's result_refs (E.B12a) become rows. Their identity is
-- the run and the extractor's local key, so loading again adds nothing. The draft is kept whole in moment_body.
INSERT INTO key_moments (moment_id, week_id, run_id, moment_body, evidence_refs, document_id, moment_type, sensitivity,
                         occurred_at, extractor_version, quote_verified, unverified_reason, consent_status, checks)
SELECT 'unverified_' || substr(md5(j.run_id || ':' || (u.value->>'local_key')), 1, 24), j.week_id, j.run_id,
       u.value->'draft', '[]'::jsonb, d.transcript_id, u.value->'draft'->>'moment_type',
       CASE WHEN u.value->'draft'->>'sensitivity' IN ('public_candidate', 'internal_only', 'unknown')
            THEN u.value->'draft'->>'sensitivity' END,
       d.occurred_at, COALESCE(j.result_refs->>'extraction_profile', '2026-10-13.weekly.v3'), false,
       COALESCE(u.value->>'reason', 'The quote does not bind to its source'),
       CASE WHEN u.value->'draft'->>'sensitivity' = 'internal_only' THEN 'internal_only' ELSE 'anonymise' END,
       jsonb_build_object('loaded_from_job', j.job_id)
FROM pipeline_jobs j
CROSS JOIN LATERAL jsonb_array_elements(COALESCE(j.result_refs->'unverified_moments', '[]'::jsonb)) AS u(value)
JOIN pipeline_runs r ON r.run_id = j.run_id
-- A document only when the run read exactly one; a draft that cannot name its document keeps document_id null.
LEFT JOIN LATERAL (
  SELECT t.transcript_id, t.occurred_at FROM transcripts t
  WHERE jsonb_array_length(COALESCE(r.input_refs->'transcripts', '[]'::jsonb)) = 1
    AND t.transcript_id = r.input_refs->'transcripts'->0->>'id') d ON true
WHERE j.stage = 'moment_extraction' AND j.status = 'completed' AND jsonb_typeof(u.value->'draft') = 'object'
  AND j.run_id IS NOT NULL
ON CONFLICT (moment_id) DO NOTHING;

-- 3. Topics: short canonical subjects that give recurrence, retrieval expansion and memory a stable key (2.B7).
CREATE TABLE topics (
  topic_id text PRIMARY KEY,
  name text NOT NULL CHECK (length(btrim(name)) > 0),
  description text,
  -- Content pillars from the strategy document this topic serves (ATTRACT, WARM, CONVERT), if any.
  pillars jsonb NOT NULL DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked', 'merged')),
  -- Where a merged topic's moments went; a merged topic receives no new links.
  merged_into text REFERENCES topics (topic_id),
  embedding vector(1536),
  embedding_model text,
  embedding_input_hash text,
  origin text NOT NULL DEFAULT 'model' CHECK (origin IN ('model', 'person')),
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((embedding IS NULL) = (embedding_input_hash IS NULL)),
  CHECK (status <> 'merged' OR merged_into IS NOT NULL),
  CHECK (merged_into IS NULL OR merged_into <> topic_id)
);
CREATE UNIQUE INDEX topics_name_unique ON topics (lower(name)) WHERE status <> 'merged';
CREATE INDEX topics_status ON topics (status);

CREATE TABLE moment_topics (
  moment_id text NOT NULL REFERENCES key_moments (moment_id) ON DELETE CASCADE,
  topic_id text NOT NULL REFERENCES topics (topic_id),
  assigned_by text NOT NULL DEFAULT 'model' CHECK (assigned_by IN ('model', 'person', 'merge')),
  -- The nearest-topic similarity that led to the assignment, or null when a person made it.
  similarity real,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (moment_id, topic_id)
);
CREATE INDEX moment_topics_topic ON moment_topics (topic_id);

-- A topic's rename, merge, block and a person's link or unlink are audited like every other decision (2.B7).
ALTER TABLE decisions DROP CONSTRAINT decisions_item_kind_check;
ALTER TABLE decisions ADD CONSTRAINT decisions_item_kind_check CHECK (item_kind IN ('angle', 'considered_idea', 'brief',
  'brand_kit_item', 'brand_kit_version', 'brand_kit_source', 'published_content', 'run_plan', 'seed', 'topic'));

COMMENT ON TABLE key_moments IS 'The moments ledger: one scene per row, belonging to a document (week_id and run_id are the cycle that first read it, null for a document extracted on its own). Validated quote, record, type, speaker and role, consent and sensitivity; quote_verified=false rows are records, never proof.';
COMMENT ON COLUMN key_moments.consent_status IS 'cleared | anonymise | internal_only | do_not_use, derived by the backend from the client''s consent level and the sensitivity (moments/checks.py).';
COMMENT ON COLUMN key_moments.quote_verified IS 'The quote is in the source text (exact or repaired to the source''s own words, with quote_repair recording it). false rows are never proof, never embedded.';
COMMENT ON TABLE topics IS 'Canonical subjects (2.B7). A blocked topic receives no new links; a merged one points at the topic that absorbed it.';
