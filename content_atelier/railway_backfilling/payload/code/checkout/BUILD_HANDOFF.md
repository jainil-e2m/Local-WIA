# Current build handoff

Prepared 9 October 2026 (Asia/Calcutta) from the working tree. This is a current continuation guide, not an archive of chat history. Code inspection informed this handoff; no tests, database operations, provider calls, commits or pushes were performed while preparing it. Recheck status and run verification on the destination machine.

## Objective and scope

Continue Content Atelier's weekly transcript-to-content-angle build: PostgreSQL/pgvector storage, durable processing, historical matching, and a real weekly-angle review UI through Gate 1. Brief generation, content packs, publishing and new source connectors are outside this phase.

User wants necessary current context available at home, without committing legacy documents or historical snapshots. Keep this guide alongside current code, runtime prompts and clean setup documentation. Exclude `context/`, historical research/planning notes, client review documents and generated document QA outputs from the transfer commit. Do not discard local copies.

Repository: https://github.com/jainil-e2m/WIA-Content-Atelier

At preparation time the checkout was `main`, with last commit `592ea46`. The new implementation was staged or untracked, not committed. The existing upstream cannot be assumed to contain this build. Record the actual transfer commit after committing and pushing the selected files.

## Architecture to preserve

- `backend/backend_pipeline/` is the current Python package. The old `backend/atelier/`, CLI, Alembic setup and old backend tests are staged for deletion.
- `pipeline.py` plus `store.py` retain the file-backed prompt/calibration runner. JSON artifacts preserve exact provider requests/responses, validated cache, evidence, billing and historical diagnostics.
- `repository.py`, `database.py`, `sql_pipeline.py`, `storage_sources.py`, `import_history.py`, `matching.py`, `gate_one.py`, `storage_api.py` and `storage_cli.py` implement the SQL path. Inspect these implementations before relying on older README claims about missing SQL functionality.
- SQL is business authority for the SQL workflow. JSON remains operational artifact/cache storage; do not let both runners write the same business records independently.
- `backend/migrations/001_approved_schema.sql` is the thirteen-table baseline. `schema-catalog.json` is required at runtime for strict schema verification. Initialization refuses a different/nonempty schema instead of repairing it automatically.
- Tables: weeks, pipeline_runs, transcripts, transcript_chunks, key_moments, content_angles, angle_moments, content_briefs, content_packs, content_assets, calendar_entries, pipeline_jobs, pipeline_events. Future downstream table presence does not authorize downstream workflows.
- Preserve original source bytes, stable IDs, exact source/quote validation, request fingerprints, generation timestamps and lineage. Failed or partial extraction must remain identified as failed/partial. Do not silently repair, truncate, batch or substitute results.
- Embedding vectors require 1,536 finite values and nonzero magnitude. Matching retains cosine, overlap, age and recency as distinct values. Current risk uses overlap clamped from `(cosine - .78) / .22` and a 28-day recency half-life. Missing/incompatible historical vectors must block complete matching rather than imply zero duplication risk.
- The SQL frontend is `SQLWeeklyAngles.tsx` with `weeklyStorage.ts` DTOs/client utilities. `App.tsx` imports the component. Other studio views still use mock/localStorage behavior; do not present all views as SQL-backed.
- Browser calls `/api/atelier/...` through the frontend server proxy to backend `/storage/...`. Preserve verified team-session checks, CSRF controls, identity stripping and the server-only shared secret. Never place that secret in a `VITE_*` variable.

## Current model work and execution boundaries

Current configured LLM model for both stages is exact `openai/gpt-6-luna` through OpenRouter. Treat this as the repository's configured value; check current provider availability before a new live run. Runtime templates live in `backend_pipeline/prompt_templates/`, with contracts/validators in code. Markdown in that directory is runtime input and belongs in the code commit.

The latest documented Week 1 baseline is partial:

- Extraction `week1-gpt6-luna-generation-only-20261008-a3`: nine proposed moments; seven individually validated, two failed quote-binding checks. Whole extraction remained failed.
- Explicit partial-pool Call 2 `week1-gpt6-luna-partial-angle-diagnostic-20261008-a4`: six validated candidates from seven accepted moments. Original extraction remains failed; candidates are not founder-approved or final similarity-verified selections.
- Documented cache-only replay reproduced those candidates without new requests. Replay is reuse, not another batch of six new angles.
- Week 1 has no real embeddings/final historical matching established by these generation diagnostics. Preserve saved outputs; do not rerun generation merely to move them to SQL.
- Week 2 originals were supplied locally; actual calendar week assignments need confirmation. Unknown meeting dates remain null. Do not reuse synthetic test dates for customer data.

Model settings in `.env.example` retain compact whole-week input, JSON-object responses with strict local validation, low reasoning effort, blank output-token cap and disabled local input-size rejection. Finite provider limits still apply. Do not change this profile silently when expecting fingerprint-compatible replay.

Leave paid execution disabled during continuation and offline verification:

```text
CONTENT_ATELIER_LIVE=false
CONTENT_ATELIER_EMBEDDINGS_ENABLED=false
ATELIER_ALLOW_GENERATION=false
ATELIER_ALLOW_ENCODING=false
ATELIER_SYNTHETIC_DATABASE=false
```

SQL capabilities have separate switches from the file-backed runner. New paid generation and real encoding need an explicit user decision. Prior Week 1 diagnostic authorization does not authorize new Week 2 calls. Cache misses should fail/wait rather than silently call a provider.

## What must actually reach home

Commit current backend/frontend code, tests, dependencies, migration/catalog, Compose configuration, blank environment templates and this guide. Keep the intended old-backend deletions together with its replacement.

The following required additions were UNTRACKED when this guide was prepared; include them explicitly:

```text
backend/backend_pipeline/tests/test_sql_storage.py
backend/storage.env.example
frontend/server/storage.test.mjs
frontend/src/components/SQLWeeklyAngles.tsx
frontend/src/types/weeklyStorage.ts
frontend/src/utils/weeklyStorage.ts
frontend/src/utils/weeklyStorage.test.tsx
BUILD_HANDOFF.md
```

Private state needs a separate private file transfer, not GitHub:

- `backend/zoom_backfill_meetings/`: original Week 1/Week 2 source files, preserving their bytes and structure.
- `testing/.data/`: existing JSON datastore, including original packets, requests/responses, validated cache, A3/A4 manifests and diagnostic metadata. Transfer the complete datastore rather than guessing a minimal subset: import/replay checks provenance and cache integrity.
- `backend/.storage-artifacts/` if SQL operations have already created artifacts that need continuation.
- Any populated SQL database that must be preserved needs a deliberate backup/restore. Compose alone does not transfer its Docker volume. Verify whether relevant database state exists before deciding to rebuild.
- Recreate local secrets privately on the destination. Do not commit real `.env` files or secrets inside handoff prose.

With code alone, the home chat can continue implementation and synthetic tests. It cannot truthfully replay/import real Week 1 or process the supplied Week 2 corpus without the private inputs/artifacts.

## Destination setup and verification

Use the committed dependency files. From `backend/`, create a virtual environment and install `requirements.txt`. Copy `.env.example` to `.env` and `storage.env.example` to `.env.storage.local`; set destination paths for transcript/data roots and a new private API secret. Preserve disabled execution switches.

The local storage Compose file binds PostgreSQL to loopback port 15432 using pgvector/PostgreSQL 17. Inspect it, then initialize only a dedicated local database:

```powershell
# From backend/, after installing dependencies and configuring local environment:
docker compose -f compose.storage.yml up -d
python -m backend_pipeline.storage_cli init
python -m backend_pipeline.storage_cli check
python -m pytest backend_pipeline/tests
```

SQL integration tests are skipped unless `ATELIER_TEST_DATABASE_URL` is set. They require a dedicated initialized database named `atelier_test` and truncate its content tables. A passing run with skipped SQL tests is not proof of PostgreSQL integration. Never point that suite at production or the working customer database.

From `frontend/`:

```powershell
npm ci
npm run lint
npm test
npm run build
```

Inspect `frontend/server/index.mjs` and existing frontend authentication configuration to set the BFF/auth origin and backend origin/secret. Verify the weekly view with real authenticated proxy wiring; a Vite-only screen is insufficient evidence of end-to-end behavior.

CLI operations available for later controlled work: `admit`, `import-luna`, `review`, `submit`, `worker`, `retry`, `encode`, `reassess`. Read their arguments in `storage_cli.py`. Admission needs explicit `--start` and `--week-index`; do not invent the real dates. Import validates original evidence and A4 artifact integrity.

## Next work and known cleanup

1. Complete a portable transfer commit, including every source dependency above. Review the staged diff for documents and secrets. Avoid blanket `git add .`.
2. Run offline backend/frontend checks and isolated real PostgreSQL integration; record actual passes, skips and failures. This handoff establishes no fresh pass claim or production readiness.
3. Verify SQL bootstrap/import against the privately transferred saved Week 1 state, preserving partial coverage, IDs and original age. Verify Week 2 admission once real calendar assignments are supplied.
4. Exercise worker recovery, cached/replay behavior, matching completeness, Gate 1 edits/approval and proxy authentication. Keep live inference disabled while resolving implementation defects.
5. Rewrite current READMEs around the implemented SQL path and this guide. Root README currently links to local design/research documents; backend README mixes earlier file-backed status with later results. Remove broken links and obsolete deployment claims from the transfer version.
6. Fix or exclude `backend/migrations/export-schema.cjs`: it currently requires a dependency from an absolute Codex directory and a local root DBML file. The committed SQL/catalog are runtime requirements; that script is not portable as written. If schema editing needs a maintained canonical design source, retain only the current approved source or build a portable export workflow; do not reintroduce the archive.
7. Replace personal absolute paths in environment examples with portable setup guidance. Historical `backend/prompts.md` is an edit ledger/snapshot, not runtime input, and can remain local.

## Starter prompt for the home chat

Read BUILD_HANDOFF.md and inspect the current checkout before continuing the Content Atelier build. Continue the PostgreSQL/pgvector weekly-angle workflow through Gate 1, preserving saved Week 1 partial results and strict provenance. Verify the implementation with offline tests and an isolated atelier_test database. Tell me which private inputs or artifacts are missing before attempting real-data import/replay. Keep paid generation and embedding disabled. Do not commit legacy context snapshots, client documents, secrets or generated test outputs. Use current code as the source for implementation status and update this handoff with verified progress.
