# Artifact persistence and reuse — working context (7 October 2026)

## Current user request

> will the received embeddings be stored locally so that we can use them at a later stage when the embeddings will be needed to backfill, rather than re running it through the embedding model again? and the same goes for the llm model responses? as well as the identification of the key moments and the content angles generated in each of the 2 calls.

This checkpoint is being saved at a context boundary, as explicitly requested by the user. It preserves task context, decisions, evidence and work state, not private reasoning. The broader implementation context is in `2026-10-07-backend-pipeline-implementation-context.md`.

## Agreed requirements

- Scope is transcripts → grounded key moments/context → distinct content angles → one embedding per angle → deterministic similarity/recency scoring. No briefs, packs or publishing yet.
- Two main LLM stages, no additional LLM similarity judge; show every eligible distinct angle above the adjusted-score threshold, without a four-angle cap.
- `openai/gpt-oss-120b:free` is approved. Stage models and embedding model are environment-configurable; embedding credentials are separate from LLM credentials.
- Local JSON is the authoritative interim datastore; Markdown provides human-readable ledgers; local pgvector is a rebuildable projection. Cache all usable requests, responses, usage and lineage without credentials.
- Week-by-week historical testing starts with June 2026, supplied in numbered week folders. Actual weekly windows remain unconfirmed. Proposed cutoff is Saturday 04:00 America/Chicago.
- Preserve original generation times during replay; “last turn” means previous completed generation run.
- Preserve unrelated user changes, including deleted old backend files and modified frontend files. No live model/payment calls, database start or production mutation has occurred in this task.

## Findings that prompted this correction

The initial implementation persisted outputs but did not reliably reuse all of them:

1. Embeddings were written per run, without checking an embedding cache before calling the provider.
2. Random moment IDs changed Stage 2 prompts on rerun, defeating reuse.
3. Random angle IDs and refreshed dates changed generation lineage on replay.
4. Cache keys omitted model, endpoint, actual request parameters/schema and fake/live isolation.
5. Raw LLM responses could be lost when content parsing failed; full rendered requests were not saved.
6. Validation status was written before domain validation.
7. Immutable writes prevented the run manifest from changing from planned to completed.
8. History was not filtered by completed status, mode, embedding profile or current week/run.

The user has been informed that these paths are being corrected to meet the existing reuse requirement.

## Changes applied, not yet verified at this checkpoint

- `models.py`: versioned service artifacts, full request, output checksum and metadata.
- `store.py`: safe resolved paths, explicit overwrite for mutable pointers/manifests, immutable versioned artifact cache with checksum validation; unsafe legacy caches ignored.
- `provider.py`: shared exact request builders; response receipt callback before HTTP/content parsing; fake vector dimensions follow configuration.
- `pipeline.py`: exact dependency-aware fake/live cache keys, saved request attempts, raw receipts and received outputs; validated artifact reuse; embedding cache lookup; replay mode fails without external calls on a miss; stable moment/angle IDs; original generation lineage; revisioned source snapshots; persisted moments and candidates before subsequent stages; completed manifest updates; filtered, deduplicated history.
- CLI/API: replay added to accepted modes.

## Immediate remaining work

1. Inspect syntax/formatting and run lint/tests using workspace-local test temp directories.
2. Add nonempty counting-provider tests proving identical reruns use zero new requests, stable lineage, model/profile invalidation, fake/live isolation, replay-only behavior, raw failure receipts and source revision preservation.
3. Correct any implementation issues found. Update README with storage paths, compatible reuse rules, replay semantics and legacy-cache migration limits.
4. Report tested behavior honestly; do not claim broader end-to-end production readiness or a real provider/pgvector test.

## Environment and verification constraints

Project: `C:\Users\Jainil Trivedi\Desktop\Wedding_Industry_Ads\content_atelier`.
Backend package: `backend_pipeline`. Interim data root defaults to `testing/.data` and is ignored by Git.
Use `python -m pytest -q --basetemp=testing/.pytest-tmp` to stay in the permitted workspace. Python 3.12, pytest, ruff, httpx and backend dependencies are available. Docker daemon is off and local Postgres is not running. Never read or display `.env` credentials.
All source/document edits use apply_patch; formatting commands are permitted. Run pipeline mutations sequentially to avoid the previous Windows replace race.

## Completed correction and verification

The previously listed work-in-progress changes are now implemented and verified. Added failed/completed manifest transitions and explicit rejection of reused report run IDs; preserved original generation lineage; fixed invalid cache-shape handling; excluded workspace-local pytest temporary output from Git. Updated `backend_pipeline/README.md` and the testing datastore README with actual paths, compatibility rules, replay-only operation and unimplemented design boundaries.

Verification on 7 October 2026:

- `python -m pytest -q --basetemp=testing/.pytest-tmp`: **19 passed** (the three original tests plus nonempty reuse/failure/profile tests).
- `python -m ruff check backend_pipeline`: all checks passed after formatting/import correction.
- `python -m compileall -q backend_pipeline`: completed successfully.
- Git ignore checks confirmed private `.data/` service receipts, `.pytest-tmp/` outputs and the supplied backfill root are excluded.
- A nonempty synthetic first run required one extraction, one angle-generation and one embedding request; its identical rerun required zero new requests and preserved angle IDs, original generation date and original run ID.
- Embedding profile changes reused both LLM stages; Stage 2 prompt/model changes reused extraction and exact unchanged signature vectors; threshold-only changes reused all model outputs.
- A failed embedding stage preserved moments/candidates for a new report run. Malformed LLM content had its received raw body saved before parsing failed. Invalid dimensions/checksums were not promoted to the validated cache.
- Fake artifacts could not satisfy a live-namespace replay; a replay with matching live artifacts needed no credentials, and a miss stopped without calling the mock provider.
- A recording-connection test reconstructed the 1,536-dimensional vector projection from saved JSON without an additional embedding request. This is not a running PostgreSQL integration test.

No real model or paid service call was made; HTTP tests used MockTransport. No database/Redis service was started. Pytest emitted an environment-level requests dependency warning unrelated to the reuse tests, which all passed.

### Remaining boundaries (not blockers for this cache correction)

Single-writer JSON only: no concurrent leases/exactly-once billing, budget enforcement, automatic repair of invalid saved responses, frozen experiment branches or simulated historical clock yet. Model structured-output compatibility, full coverage/context-window handling and editorial calibration need separate real-route validation. Raw artifacts lacking version-2 identity guarantees are retained but deliberately not reused automatically. A new week's sources or a genuinely changed request can require new inference; a pgvector schema rebuild alone does not.
