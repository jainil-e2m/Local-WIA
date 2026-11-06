# Strategic prompt upgrade handoff

Jainil approved installing the supplied Key Moments and Angle candidates with exactly three narrowly scoped reconciliations: bounded offer context, retention of precise source/handling safeguards, and schema-conditional internal intelligence output. Refinement must use relevant intelligence only as context, without emitting `internal_insights` or implying creation of extra records. Original candidate packages remain unchanged and have byte-identical source snapshots in `research/sources/prompt-upgrade-2026-10-15/`.

Baseline commit: `aafa8c24246daaa6e89e7f3bb7d717dd0f1b8b23`. The four runtime targets were tracked and clean before edits. Existing substantial intake/backfill/frontend changes remain unrelated. No automatic commit, stage, push, provider call, database operation or deployment occurred.

Installed targets: `moment_extraction.weekly_v3.md`, the exact weekly user prefix in `prompts.py`, `angle_generation.system.md`, and byte-identical candidate `angle_generation.user.md`. Shared strategy/policy, base/legacy prompts, comparison/refinement supplements, schemas, validators, scoring, thresholds, provider configuration and approval behavior remain unchanged by hash. No new profile loader or schema migration was introduced.

Checks: expanded relevant suite **142 passed, 22 skipped** (isolated SQL test database unavailable); new verification module **31 passed** after fixture import cleanup; scoped Ruff and diff checks passed. Two pre-existing wording assertions were adapted to equivalent candidate sentences. A repository-wide whitespace check found unrelated existing `repository.py` issues; do not fix or absorb them as part of this task.

Sixteen synthetic baseline/installed request snapshots verify four builders in both JSON modes. The full existing archived Week 2 extraction request was rendered locally with all 11 sources and 5,218 turns, unchanged source content and no dispatch. Request characters increased from 545,931 to 557,333 under unchanged configuration. Native token counts/provider capacity were not newly verified; existing local capacity validation remains disabled. New angle-stage size depends on future extraction output.

Full report, rollback and limitations: `research/2026-10-15-strategic-prompt-upgrade.md`. Hashes/configuration/package provenance: its companion `-verification.json`. Exact candidate-only changes: `research/2026-10-15-strategic-prompt-reconciliations.diff`. Local synthetic request bodies and focused JUnit report: `backend/.storage-artifacts/verification/prompt-upgrade-20261015/`.

Status: implemented and locally schema/parser compatible; no model/editorial evaluation or production readiness claim. Any next integrated Week 2 run starts with all admitted transcripts, not the earlier two-moment diagnostic pool. Keep paid execution distinct from this completed file-only upgrade.
