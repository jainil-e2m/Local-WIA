-- Migration 010 (Phase N8: 1.B12's and 1.B13's extensions, 3.B17, L.B13, 1.B11). Additive; needs 009.
-- Identities: a person or a client account carries its pronouns, a staff member's dates, and the two flags a privacy rule
-- reads (never name; never link to a named piece of published work), with who reviewed it and on what basis (D21).
-- Internal calls become evidence of how WIA works: a scene says which class of evidence it is (team_practice for an
-- internal meeting, D24). Founder notes are seeds linked to the call they are about (D29). A document dated only to the
-- week its source folder names keeps that window as evidence beside its date (1.B11).

ALTER TABLE people
  ADD COLUMN pronouns text CHECK (pronouns IS NULL OR pronouns IN ('she/her', 'he/him', 'they/them')),
  ADD COLUMN joined_on date,
  ADD COLUMN left_on date,
  -- Never named in public copy, whatever the consent of their account says.
  ADD COLUMN do_not_name boolean NOT NULL DEFAULT false,
  -- Published work this person must never be linked to: [{what, markers[], reason}]. A marker is a phrase or figure that
  -- identifies the work ("$70K"); copy that refers to the person, or is built on their calls, and carries a marker is blocked.
  ADD COLUMN do_not_link jsonb NOT NULL DEFAULT '[]'::jsonb,
  -- Who confirmed the identity, when, and on what evidence: {by, at, basis[]}.
  ADD COLUMN reviewed jsonb,
  ADD CONSTRAINT people_left_after_joined CHECK (left_on IS NULL OR joined_on IS NULL OR left_on >= joined_on);

ALTER TABLE clients
  ADD COLUMN business text,
  ADD COLUMN do_not_name boolean NOT NULL DEFAULT false,
  ADD COLUMN do_not_link jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN reviewed jsonb;
-- A business WIA has only pitched is an account too (its people are prospects), so account memory and the privacy rules
-- can follow it if it becomes a client.
ALTER TABLE clients DROP CONSTRAINT clients_status_check;
ALTER TABLE clients ADD CONSTRAINT clients_status_check CHECK (status IN ('active', 'former', 'prospect'));

-- call: a scene from a call with someone outside WIA (or a Slack thread); team_practice: a scene from an internal meeting,
-- eligible to show WIA's process, standards and decisions, never a client quote, name or figure (D24). Derived from the
-- document's call type by moments/checks.py, like consent_status.
ALTER TABLE key_moments ADD COLUMN evidence_class text NOT NULL DEFAULT 'call'
  CHECK (evidence_class IN ('call', 'team_practice'));
UPDATE key_moments m SET evidence_class = 'team_practice'
  FROM transcripts t WHERE t.transcript_id = m.document_id AND t.call_type = 'internal';
CREATE INDEX key_moments_evidence_class ON key_moments (evidence_class) WHERE is_current;

-- Founder notes (L.B13): Whitney's one "what stood out" line about one call, a seed linked to that call.
ALTER TABLE seeds DROP CONSTRAINT seeds_kind_check;
ALTER TABLE seeds ADD CONSTRAINT seeds_kind_check CHECK (kind IN ('thought', 'draft', 'asset', 'founder_note'));
ALTER TABLE seeds ADD COLUMN transcript_id text REFERENCES transcripts (transcript_id);
ALTER TABLE seeds ADD CONSTRAINT seeds_founder_note_has_call CHECK (kind <> 'founder_note' OR transcript_id IS NOT NULL);
CREATE INDEX seeds_transcript ON seeds (transcript_id) WHERE transcript_id IS NOT NULL;

-- Occurrence dating (1.B11): what supports the date, kept beside it. {detail, conflicts[], window: {start, end, basis}}.
-- A window is the week a source folder names (the Zoom backfill's week folders, filed by recording time); it bounds the
-- day a spoken cue or a recording list names, and dates a document to its week when nothing names the day.
ALTER TABLE transcripts ADD COLUMN date_evidence jsonb;

ALTER TABLE decisions DROP CONSTRAINT decisions_item_kind_check;
ALTER TABLE decisions ADD CONSTRAINT decisions_item_kind_check CHECK (item_kind IN ('angle', 'considered_idea', 'brief',
  'brand_kit_item', 'brand_kit_version', 'brand_kit_source', 'published_content', 'run_plan', 'seed', 'topic', 'pack',
  'person', 'client', 'document'));

COMMENT ON COLUMN people.do_not_link IS 'Published work this person must never be linked to: [{what, markers, reason}] (1.B12).';
COMMENT ON COLUMN clients.do_not_link IS 'Published work this account must never be linked to: [{what, markers, reason}] (1.B12).';
COMMENT ON COLUMN key_moments.evidence_class IS 'call | team_practice (an internal meeting: process and standards, never a client quote, name or figure; D24).';
COMMENT ON COLUMN seeds.transcript_id IS 'The call a founder note is about (L.B13); null for other seeds.';
COMMENT ON COLUMN transcripts.date_evidence IS 'What supports occurred_at: {detail, conflicts, window {start, end, basis}} (1.B11).';
