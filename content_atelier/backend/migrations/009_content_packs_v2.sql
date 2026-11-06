-- Migration 009 (Phase NP, NP.B1; the content-packs plan, section 5.3). Additive; needs 008.
-- Content pack contract v2: the pack-level fields of a pack version (before-publishing notes, client quotes, the
-- finisher's notes, the change record and provenance) live on the pack row, beside its five piece rows in content_assets.
-- Decisions on a pack (a clearance, an attestation, ready to publish, an edit) are audited like Gate 1's and Gate 2's (R45).

ALTER TABLE content_packs ADD COLUMN content_body jsonb;
ALTER TABLE content_packs ADD COLUMN content_hash text;
ALTER TABLE content_packs ADD CONSTRAINT pack_content_has_hash CHECK ((content_body IS NULL) = (content_hash IS NULL));
-- The current pack of a brief is the one nothing supersedes; the versions list walks supersedes_id.
CREATE INDEX content_packs_source_brief ON content_packs (source_brief_id);
CREATE INDEX content_packs_supersedes ON content_packs (supersedes_id);

ALTER TABLE decisions DROP CONSTRAINT decisions_item_kind_check;
ALTER TABLE decisions ADD CONSTRAINT decisions_item_kind_check CHECK (item_kind IN ('angle', 'considered_idea', 'brief',
  'brand_kit_item', 'brand_kit_version', 'brand_kit_source', 'published_content', 'run_plan', 'seed', 'topic', 'pack'));

COMMENT ON COLUMN content_packs.content_body IS 'content_pack_v2: the pack-level fields (packs/contracts_v2.PackBody); null for v1 packs and for a pack still finishing.';
