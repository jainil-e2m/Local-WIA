# Weekly angle storage: setup, execution and verification

Implementation, the first live Week 2 comparison and Week 1/2 transcript chunk encoding were verified on 12 October 2026. The weekly path is **historical comparison plus one optional refinement pass**, through provisional review. Legacy two-call runs retain their existing Gate 1 behavior. Persistent external switches remain disabled; authorized live operations used process-local permissions. Hybrid retrieval, researched briefing and Gate 2 are now built and verified offline. The authoritative cutoff remains unset and the real brief pilot remains later work. See [brief implementation status](../implementation-status-content-briefs.md). See [the implementation reasoning](../implementation-plan-historical-comparison.md).

## Current local state

The dedicated Compose project is `content-atelier-storage`. PostgreSQL listens only on `127.0.0.1:15432`, using its own named volume. It does not use the other project databases on this computer. The pinned image contains PostgreSQL 17.10 and pgvector 0.8.2.

The approved baseline has **13 tables, 30 foreign keys, 18 checks and exactly two `vector(1536)` columns**. Its SHA-256 is `1f89fa2894074cd6c54b51083e6c775a76ac1e1f59341d3b3f2fbefbb25fc6bb`. No configuration/version/profile tables were added. The four future content tables exist and are empty.

| Stored content | Current count / state |
|---|---|
| Weeks | June 1–7 and June 8–14, 2026 |
| Original transcripts | 20: nine in Week 1 and eleven in Week 2 |
| Original mapped passages | 8,456: 3,238 and 5,218 |
| Prepared transcript chunks | 329: 136 Week 1 and 193 Week 2; all have verified 1,536-dimensional Small vectors |
| Validated key moments | 13: seven accepted Week 1 moments and six source-validated Week 2 moments |
| Content angles | 12: six Week 1 and six Week 2 candidates, all with verified 1,536-dimensional Small embeddings |
| Angle/moment links | 12 explicit links; the original accepted Week 1 pool is preserved |
| Briefs, packs, assets, calendar entries | Zero |

Week 1 is `awaiting_matching`; Week 2 is `comparison_review`. The earlier Week 1 preparation made six explicitly authorized Small embedding requests, preserving the accepted partial baseline. The later Week 2 angle run made one Luna extraction request, one Luna angle-generation request and six Small embedding requests. All eight comparison stages completed. No refinement targets were found, so Call 3 completed as a recorded skip. No chunk encoding, approval or briefing took place in that angle run. A subsequent separately authorized operation encoded all 329 existing chunks in 12 Small requests, preserving both weekly review states and all earlier content/execution records.

The six angles preserve `2026-10-08T11:28:56.043339Z` as their actual first generation time. June dates group the corpus; they do not backdate generation or prove when a meeting occurred. Unknown meeting dates remain null. Angle bodies, quality, evidence links, source records and accepted partial-baseline status were checked unchanged. All six are eligible compatible history for the new Week 2 comparison workflow; this does not approve them or calibrate the experimental thresholds.

Current embedding readiness is recorded in `.storage-artifacts/verification/week1-embedding-readiness.json`. The earlier comparison implementation's real-data fingerprint reports describe its offline verification point, before this explicitly authorized embedding operation.

Week 1 is explicitly an **accepted partial baseline**, following the user's selection of the six Luna candidates. Seven proposed moments passed exact source validation, two failed, and the original extraction remains failed. A successful second call does not turn that extraction into complete coverage, approval or final selection.

The aggregate admission report is saved locally under `.storage-artifacts/verification/admission-report.json`; final source/API checks are in `verification/final-storage-report.json`. Raw original bytes are archived by hash under `.storage-artifacts/source-originals/`. These private local artifacts and `.env.storage.local` are ignored by Git.

## First live Week 2 result

Run `run_f92042c802f84d8a9a1401a460cb0f55` used the 11 admitted June 8-14 transcripts (5,218 passages). It produced six exact-source-validated moments and six angles. All six satisfy baseline quality above 70 and historical cosine below each of **0.78, 0.85 and 0.90**. Maximum historical cosines range from approximately **0.560 to 0.636**; no selected current-batch candidate reaches the 0.90 flag. Quality scores are model self-assessments (five 100s and one 90), not independent editorial ratings. Transcript delivery acknowledgment does not establish complete editorial comprehension.

The first Call 2 validation failed because assertions used original passage citations without the required moment prefix. All 18 citations resolved unambiguously to their declared current-week moments. The SQL-only `citation_adapter.py` adds those known prefixes while preserving the exact assertion text, qualifiers, scores and original raw response. Unknown, historical, undeclared, ambiguous and uncited references still fail. The response was validated and recovered through the cache; the existing generation job completed on attempt 2 with **zero additional generation calls**. Forty-seven citation, comparison and SQL regression cases passed with outbound requests guarded. Legacy calibration parsing is unchanged.

The run's JSON/CSV, human-readable angle review, dispatch record, citation recovery and verification are under `.storage-artifacts/experiments/sql/runs/run_f92042c802f84d8a9a1401a460cb0f55/`. `verification.json` confirms compatible vector/signature/provenance for each candidate and backend approval denial. Week 1 records, original sources/chunks and downstream tables remained unchanged. No authoritative cutoff was selected, and no briefs were generated. This run exercises real generation, encoding and final comparison; live refinement remains unexercised because the target set was empty.

## Responsibilities and relationships

| Implementation | Responsibility |
|---|---|
| `migrations/*.sql`, `migrations/schema-catalog-<version>.json` | Numbered migrations applied by `storage_cli migrate`, and one exact catalogue per recorded version (`python -m backend_pipeline.schema_catalog --check` fails on drift) |
| `database.py`, `repository.py` | Transactions, SQL authority, process state, claims and evidence reads |
| `storage_sources.py` | Original-text range maps, coherent whole-turn chunks and lossless SQL packet reconstruction |
| `chunk_encoding.py`, `scripts/embed_week1_week2_chunks.py` | Independent tracked chunk encoding, bounded batches, exact-input/provenance checks, response/cache recovery and the authorized corpus operator |
| `import_history.py` | Source/response revalidation and explicit partial Luna history admission |
| `sql_pipeline.py` | Versioned two-call/comparison orchestration, independent encoding and one-pass refinement |
| `angle_workflow.py`, `comparison.py`, `refinement.py` | Pure eligibility/family selection, frozen comparisons and strict third-call validation |
| `matching.py` | Frozen history, exact cosine, freshness risk and separate current-batch flags |
| `gate_one.py`, `storage_api.py` | Hash-checked edits, assessment, CTA decisions and protected read/queue APIs |
| Frontend `SQLWeeklyAngles.tsx` and server proxy | SQL-derived review, original evidence, process updates and trusted identity forwarding |

SQL is the authority for admitted content and execution state. Files hold exact provider requests/responses, validated reusable cache, billing artifacts and raw-byte archives. The separate calibration runner still uses `testing/.data/`; its old `angle_vectors` adapter is not used by this workflow. No calibration prompts, response contracts or model caps were changed for storage setup.

The relationship is `angle_moments → key_moments.evidence_refs → transcripts.passage_map → transcripts.original_text`. Each evidence reference pins a captured transcript ID, passage ID, exact character range and role. Offsets count Unicode code points, use a zero-based start and exclusive end, and resolve into the preserved LF-normalized original. Original bytes remain separately archived. Speaker labels are unverified labels.

Changed source bytes create a new immutable capture. Already cited originals remain. Re-admitting identical input is idempotent; a changed parser view of an existing capture fails visibly instead of changing old evidence. Ordinary processing reconstructs its packet from its frozen SQL inputs, without reopening current source files. Both real corpora were checked byte for byte against the calibrated reader: packet sizes remain 358,002 and 516,999 UTF-8 bytes. Explicit header ordering preserves request fingerprints across PostgreSQL JSONB serialization.

Chunks contain consecutive whole turns, with source context and ordered original-passage references. They split at a size boundary or a conversational gap, never by cutting a quotation. An unusually long turn can exceed the usual target size. The existing whole-turn boundaries and filename headers were preserved during encoding; no overlap, invented meeting date or speaker role was added. Chunk encoding is implemented and complete for the admitted Week 1/2 corpus. Hybrid semantic/full-text briefing retrieval is implemented offline. Optional fuzzy term lookup and richer contextual-header changes remain later evaluation work.

## Transcript chunk encoding

`transcript_chunk_embedding` is an independent `transcript_encoding` run, one per week. It uses the existing runs/jobs/events tables, does not replace `weeks.active_run_id`, and does not rerun extraction, angle generation, matching or approval. The CLI can queue a cached-only intent with `python -m backend_pipeline.storage_cli encode-chunks --week-id week_2026-06-01`; live mode additionally requires explicit process-local encoding permission.

The input is the exact stored `chunk_text`, including its filename header. `exact-chunk-text-v1` binds endpoint, model, dimensions, synthetic/real mode and input text into a distinct cache contract. It cannot reuse an angle-signature cache. Chunk content and original references are frozen and rechecked before every SQL commit. Existing vectors with incompatible/missing provenance fail visibly instead of being overwritten.

The endpoint, model string and dimensions are defined once, in `backend_pipeline/config.py` (`embedding_contract`): `https://openrouter.ai/api/v1`, `openai/text-embedding-3-small`, 1,536, the values the archive was encoded with. Every environment example carries the same values. At start-up the API, the SQL worker and the intake worker compare the process's contract with the digests recorded by completed chunk and angle-signature encoding jobs, and refuse to start when none matches; the message names both contracts. Set `ATELIER_ALLOW_EMBEDDING_CONTRACT_CHANGE=true` only while deliberately re-encoding the archive under a new contract. With `ATELIER_BRIEFS_ENABLED=true`, the API and SQL worker also refuse to start unless `ATELIER_BRAND_BUNDLE_PATH` names a reviewed bundle.

Requests contain at most 32 texts. A conservative 8,191-byte limit rejects oversized inputs without truncation or a tokenizer download; the real corpus maximum was 2,543 UTF-8 bytes. The API supports multiple string inputs in one embedding request. [OpenRouter batch embedding documentation](https://openrouter.ai/docs/api_reference/embeddings)

Exact requests and raw responses are archived before validation and writes. Response indices must cover every requested input exactly once, model identity must match, and every vector must have 1,536 finite dimensions and a nonzero float32 norm. Atomic caches live under `chunk-encoding/`; job `result_refs.vectors` binds each chunk ID, parent transcript, content/input/view hash and stored vector digest to its cache and received response. Retry can recover both a validated cache and a received-but-not-yet-cached batch without a second paid dispatch. Failures require explicit retry.

The bounded real-corpus operator is `scripts/embed_week1_week2_chunks.py`: without `--execute` it is read-only. The authorized operation made 12 OpenRouter Small requests for 329 inputs, using 208,733 reported input tokens and $0.00417466 reported cost. No generation/refinement/brief requests were made. All sources, chunk text/ranges, moments, angles, approval states, weekly review states and earlier execution records were preserved; only chunk vectors and new operational/provenance records were written.

Independent read-only verification compared all 329 stored float32 vectors against their actual indexed provider responses and exact request texts. Sample exact cosine queries returned their own chunks with cosine approximately one. This certifies storage/provenance and search mechanics, not retrieval relevance. The approved 13-table/two-vector catalog is unchanged; no full-text, trigram or ANN index was added.

Private evidence: `.storage-artifacts/verification/week1-week2-chunk-embedding-readiness.md`, `week1-week2-chunk-embedding-readiness.json`, `week1-week2-chunk-embedding-verification.json`, and `chunk-embedding-operations/`. The earlier transcript readiness audit remains the dated pre-encoding snapshot. Sixty-two chunk, citation, comparison and SQL tests passed with outbound HTTP guarded; cases include batch ordering/completeness, incompatible inputs/models/vectors, cache reuse, and recovery after a post-response SQL failure.

## Setup and read-only checks

Run these commands from `content_atelier/backend/`, with the backend dependencies installed:

```powershell
docker compose up -d postgres
python -m backend_pipeline.storage_cli migrate
python -m backend_pipeline.storage_cli check
```

`init` is an explicit administrator operation. It serializes the baseline with an advisory lock and applies DDL in one transaction. An exact existing baseline is a no-op. A nonempty, partial or mismatched schema fails without automatic repair. Normal APIs and workers never execute DDL. Catalog comparison includes columns, checks, keys, indexes and vector types.

The SQL file is exported from the approved DBML; its extra reverse index supports finding angles for a moment. `migrations/export-schema.cjs` uses the optional design-time `@dbml/core` package, or the `DBML_CORE_PATH` environment variable, and works independently of the caller's working directory. It is not a runtime dependency. A future incremental schema change needs its own reviewed migration and applied-state procedure; this baseline does not invent a migration-history product table.

An ignored `.env.storage.local` has already been created for the local setup, with both execution permissions false and a random backend secret. The one environment reader (`settings_store.load_env_files`, shared by `Settings`, `StorageSettings` and `IntakeSettings`) loads only `ATELIER_*` values from that file; process environment takes precedence. `storage.env.example` documents the variables; the behavioural ones are also settings stored in the database (DEPLOYMENT.md, "Settings"). Existing `.env` model/provider credentials were preserved. Production must supply its own private database credentials and shared backend secret.

Admission and the explicit historical import are repeatable:

```powershell
python -m backend_pipeline.storage_cli admit --directory zoom_backfill_meetings/week1 --start 2026-06-01 --week-index 1
python -m backend_pipeline.storage_cli admit --directory zoom_backfill_meetings/week2 --start 2026-06-08 --week-index 2
python -m backend_pipeline.storage_cli import-luna --week-id week_2026-06-01
python -m backend_pipeline.storage_cli review --week-id week_2026-06-08
```

The import verifies the original source revisions, individually revalidates the received moment proposals, verifies the validated angle artifact/cache hash, and compares the six saved candidates with freshly parsed candidates. It preserves original IDs, actual origin runs, generation time, relationships and partial status. It makes no provider calls.

## Run stages and recovery

The weekly UI explicitly submits `historical_comparison_v1`. It queues:

1. `moment_extraction`: unchanged Call 1 and original source validation.
2. `history_context`: freeze the complete eligible archive, compact semantic records and current moment/evidence hashes before Call 2.
3. `angle_generation`: separately versioned Call 2 with current evidence and historical overlap context; freeze its evaluation clock immediately after validation.
4. `angle_initial_embedding`: resolve compatible SQL vectors/cache for every valid original.
5. `angle_initial_assessment`: calculate quality/history metrics; target baseline quality at most 70 or maximum historical cosine at least 0.78. No final suppression.
6. `angle_refinement`: one Call 3 with targets/reasons, prior arguments, all current moments including unused ones, and other proposals. Record completion without dispatch when there are no targets.
7. `angle_refined_embedding`: resolve only replacement signatures, reusing compatible vectors/cache.
8. `angle_final_assessment`: evaluate all three cutoffs, selecting one member per family and recalculating scenario-specific current-batch flags.

```powershell
python -m backend_pipeline.storage_cli submit --week-id week_2026-06-08 --mode replay --workflow historical_comparison_v1
python -m backend_pipeline.storage_cli worker --max-jobs 8
python -m backend_pipeline.storage_cli comparison --run-id <saved-run-id>
```

These generic commands are examples; the authorized real Week 2 test used `scripts/run_week2_comparison.py --execute` with permissions local to that process. Missing compatible responses fail visibly in replay mode. No real-generation fallback is permitted. `ATELIER_ALLOW_REFINEMENT` defaults to false; real Call 3 requires it plus generation permission, using the same angle model/credential. Semantic failure never starts another refinement pass.

The default CLI/API `two_call_v1` remains compatible with persisted legacy runs. It freezes source IDs/hashes and queues four stages:

1. `moment_extraction`: resolve compatible validated cache, or the explicitly enabled whole-week first call; validate original quotations and context before committing moments.
2. `angle_generation`: consume the saved moment pool and original evidence; validate the existing second-call contract before committing angles and links.
3. `angle_embedding`: resolve compatible signature-vector cache; external encoding requires its own explicit permission and operation.
4. `angle_matching`: freeze historical representatives and the comparison clock, perform exact historical/current-batch comparisons and save review results.

Source admission and chunk preparation also have actual completed runs/jobs/events. Generation-only artifacts can be retained while encoding/matching wait. Missing embeddings do not silently become zero risk or visible selections.

```powershell
python -m backend_pipeline.storage_cli submit --week-id week_2026-06-08 --mode replay
python -m backend_pipeline.storage_cli worker --max-jobs 4
# Long-running workers and the scheduler, when ready to process queued jobs (needs Redis; `docker compose up -d` starts all of it):
python -m backend_pipeline.jobs scheduler
python -m backend_pipeline.jobs worker --queues interactive,default,bulk
```

These are legacy operational examples. `replay` cannot call a provider. Week 2 now has stored extraction and comparison-generation responses; the legacy angle prompt has a different fingerprint. Use the explicit comparison workflow for the new path. No replay cache miss falls back to OpenRouter or synthetic content.

Jobs are claimed with row locks and `SKIP LOCKED`. An unexpired lease token is required for heartbeat and output commit. Provider work occurs outside the SQL transaction; short transactions save each completed stage. Validated output is archived before content writes, so a post-response database failure can reuse it without another inference call. Cache reuse preserves original angle IDs and generation time, rather than producing duplicate history entries.

Every job is a row in `pipeline_jobs` first, then put on an RQ queue (`interactive`, `default`, `bulk`, `intake`, `media`) after the commit, with the row's idempotency key and attempt as the RQ job id. `storage_cli worker --max-jobs N` runs ready rows inline with the same claim and handlers, for the command line and the tests; the polling `--watch` worker and the heartbeat files are gone. Redis is not a second workflow authority: the scheduler (`jobs scheduler`) re-queues any committed row that is not on a queue, so a flushed Redis loses nothing. Heartbeats update job rows. Events record meaningful starts, completions, failures, retries and admissions. Unit counts are used for measurable source/chunk/vector work, not guessed model-call percentages.

A failed or waiting stage can be retried inside the same run:

```powershell
python -m backend_pipeline.storage_cli retry --job-id <saved-job-id>
python -m backend_pipeline.storage_cli worker --max-jobs 4
```

When a worker disappears its lease runs out and the scheduler settles the job from the rows: a job that sent no model call is queued again (up to three attempts); a job whose call was sent and never settled is queued again only if the saved response can be replayed, otherwise it fails and waits for an explicit retry, because a second request could pay again for an answer the provider already has. A chunk-embedding job always waits for review. The worker does not automatically send another potentially billable request after an unknown outcome. Retry attempts increment on the same job and retain validated upstream output. This provides resumable execution, not an exactly-once billing guarantee.

Real generation would require `ATELIER_ALLOW_GENERATION=true`, the existing legacy live-generation switch and valid provider credentials, then an explicitly submitted `live` run. None was enabled here.

The authorized Week 1 embedding used process-local encoding permission only; persistent generation, encoding and refinement switches remain false. `scripts/embed_accepted_week1.py --execute` is the bounded operator workflow: six admitted signatures, the configured Small encoder, an embedding-only outbound guard, a run-scoped worker, and verification of unchanged content/evidence/Week 2 state. A compatible completed encoding is reused without dispatch. It must not be used to run Week 2 generation; later live execution needs its own user instruction.

Independent angle encoding has two modes:

```powershell
python -m backend_pipeline.storage_cli encode --run-id <saved-run-id> --mode cached
python -m backend_pipeline.storage_cli worker --max-jobs 2
```

`cached` does not call an external encoder. Later, an explicitly requested `live` encoding operation would require `ATELIER_ALLOW_ENCODING=true` and the configured embedding credential. Enabling generation alone never enables encoding. The existing model configuration is consumed without a new profile table; the baseline is the configured Small embedding model at 1,536 dimensions. Exact endpoint/model/dimension/input contract digests and actual vector fingerprints are execution provenance in jobs/artifacts.

## Similarity and selection

The comparison workflow evaluates **0.78, 0.85 and 0.90** simultaneously. A candidate qualifies under cutoff `t` only when grounding/references are valid, matching coverage is complete, **baseline quality > 70**, and **maximum historical cosine < t**. Equality fails; comparisons use unrounded values. No cutoff is authoritative. A qualifying replacement is preferred; otherwise a qualifying original survives; otherwise that family has no qualifying member. Freshness adjustment remains ranking/explanation only.

History freezes before Call 2; the clock freezes just after Call 2. Initial/final assessment reuse that archive and clock. Content, quality, source views, moments, generation age, vector bytes and the encoding contract are bound to the intent. Changed frozen inputs require a new assessment intent. Missing/incompatible coverage pauses processing and produces no qualified counts. Completed new workflows admit one latest source-valid representative per family; unfinished new workflows and replays of the current source cohort cannot enter history.

Original bodies/evidence remain unchanged. Valid replacements have their own rows/links and retain the parent's first generation time. Actual third-call time stays in artifacts/jobs. Candidate metrics live in `matching_result`; targets, dispositions, family choices, counts and assessment snapshots live in existing job `result_refs`. There are no new tables or vector columns.

The formula below is retained for ranking and **legacy selection**:

The embedding input is the existing six-field signature: audience, tension, argument, take, mechanism and reader decision. Titles, scores, CTA and freshness do not decorate the vector. Vectors must have 1,536 finite values, nonzero norm, the exact signature hash and compatible encoding provenance. Actual float32 vector bytes are checked against their execution fingerprint.

History includes validated arguments, including valid suppressed candidates, plus the explicitly admitted partial baseline. Synthetic data is isolated in a database whose name ends in `_test`, and cannot join real history. Replays retain original IDs; replacement families use one eligible representative. The current cohort and its own replacement families are excluded from history. Prior calendar weeks and earlier eligible same-week runs can contribute.

The history snapshot is read under repeatable-read isolation and saves IDs, hashes, original generation dates, candidate quality inputs, partial-coverage facts, a fixed UTC clock and the scoring numbers it uses (`scoring`: the matching settings, 0.B8). Retry uses the same snapshot; changed frozen content or quality requires a new reassessment. A missing candidate or missing/incompatible historical vector blocks complete matching.

For every eligible historical angle:

```text
cosine = 1 - pgvector cosine distance
overlap = clamp((cosine - 0.78) / 0.22, 0, 1)
freshness = 2 ** (-age_days / 28)
pair_risk = overlap * freshness
historical_risk = maximum pair_risk across the entire eligible history
adjusted_score = base_score * (1 - 0.50 * historical_risk)
legacy_visible = complete matching AND adjusted_score > 70
```

The base score retains the established weights: 35% grounding, 25% source relevance, 15% audience fit, 15% specificity and 10% editorial usefulness, with five-point assessments scaled to 100. Generation supplies model self-assessments; edits require a new explicit editor assessment before matching can finalize.

Historical matching uses an **exact scan**, with no ANN index or top-k cap deciding eligibility or penalty. The UI initially shows five comparisons sorted by risk, with all comparisons expandable. Current-batch cosine at or above 0.90 creates a separate flag within each scenario's selected cohort; it does not merge arguments or choose winners. Legacy Gate 1 requires overlap acknowledgement when flagged. Call 3 refines supported arguments; it is not a similarity judge or fuzzy-title matcher.

Brief retrieval now combines exact semantic chunk retrieval, indexed full-text matching, mandatory inherited evidence and SQL joins to prior use. It has independent briefing gates; angle matching does not dispatch research. RRF ranks discovery candidates, while exact original bindings and scoped review validate support. Optional fuzzy term lookup remains separate future evaluation work.

## API, UI and Gate 1

Start the backend on a local/private interface:

```powershell
python -m uvicorn backend_pipeline.api:app --host 127.0.0.1 --port 18081
```

From `content_atelier/frontend/`, start the BFF with its existing Command Center configuration and the same private backend secret:

```powershell
$env:PORT='18080'
node --env-file-if-exists=.env --env-file-if-exists=.env.local --env-file=../backend/.env.storage.local server/index.mjs
```

The BFF uses `ATELIER_BACKEND_ORIGIN` and `ATELIER_API_SECRET`. For Vite development, set `ATELIER_BFF_ORIGIN=http://127.0.0.1:18080` in the Vite process and use the existing auth configuration. Auth must issue a valid Command Center session; no mock sign-in bypass was added. Backend flags are startup configuration, so restart the API/worker after intentionally changing them.

The browser uses `/api/atelier/*`. The BFF validates the actual session, requires team access for this internal multi-client corpus, rejects cross-origin mutations and forwards a trusted actor plus backend authorization. It strips browser-supplied identity/authorization and does not forward the browser cookie to Python. Direct `/storage/*` routes require the private secret and trusted actor. Secrets never go into `VITE_*` settings or browser storage. The legacy experiment HTTP routes are retired (plan 6.B8); local experiment CLI commands remain available.

The Weekly Angle Review reads real SQL rows and shows uncapped candidates, processing states, original transcripts/evidence and qualifications. Comparison runs show three quality/history-qualified summaries, recovery reasons, original fallback IDs and current-batch conflict counts. Changing the displayed cutoff performs no inference/encoding. Original transcripts are available before generation. No Week 2 angles, briefs or packs were fabricated. Existing other studio views remain the older mock library.

Protected exports are `GET /storage/runs/{id}/comparison` (JSON) and `/comparison.csv`. The same team-session/trusted-actor proxy exposes them under `/api/atelier`. Incomplete comparisons export no qualified counts. JSON preserves the assessment contract and candidates; CSV includes per-family results, metrics, flags, counts and snapshot. Historical reports retain the assessed quality even after later rescoring.

Edits use an expected hash and a replacement linked with `supersedes_id`, preserving evidence and original generation age. Saved generation records retain their original identity for cache reuse and frozen-history references. Edits clear quality/matching/approval; changed semantic input also clears the vector/hash. The editor then saves a reasoned quality assessment and requests saved-angle reassessment. That operation queues encoding/matching without repeating Call 1 or Call 2. Reassessment invalidates approvals when coverage is incomplete, selection falls below the threshold, or current-batch flags change. It preserves human rejections and later CTA decisions during compatible generation replay.

Comparison-only approval is denied in the backend and UI through immutable run/family ownership, including after edits, rescoring or reassessment. Comparison reassessment creates a new frozen intent and queues history, cached encoding and final comparison without model calls. Explicit family membership keeps originals reviewable when a scenario falls back from their replacement. Legacy approval still requires current matching, a visible score, current hash, selected CTA and verified actor/time. With briefing disabled, legacy Gate 1 creates no brief work. When explicitly enabled, current hash-bound approval and the first brief intent commit together; comparison approval additionally requires an explicitly configured authoritative policy and permitted actor. The policy remains unset locally.

## Verification and limits

The full backend run passed **151 tests**. After the final legacy partial-quality preservation change, **all 40 affected SQL/comparison tests passed**, including the additional edge-case regression: **152 distinct backend cases verified overall**. The original 129 cases remain covered. Comparison tests verify eight proposals/six targets, three-cutoff outcomes, quality recovery and fallback, strict boundaries, unused-moment lineage, zero results, hidden-vector waits, frozen-input changes, invalid responses, post-response SQL recovery, replay isolation and approval denial after editing/reassessment. They use actual pgvector and an outbound HTTP transport guard. These results do not establish real semantic accuracy.

Readiness evidence is in `.storage-artifacts/verification/comparison-readiness.json`, with full/focused JUnit files and the real before/after fingerprints. The complete synthetic report is `verification/comparison/synthetic-comparison.json` with a CSV companion. Its eight families/six targets produce final qualified counts **4 / 5 / 7**, all from the same generation, vectors, archive and clock. Those artifacts are explicitly synthetic and are not Week 2 editorial outcomes.

All four storage/comparison UI/request tests and all 12 authentication/server-proxy tests pass. TypeScript checks and the production frontend build pass. The previously run broader frontend suite has an unrelated existing failure in `ScheduledContent.test.tsx`: it expects two scheduling controls, while the calendar component renders ten. That calendar component/test was not changed here. A private source-fixture test is also skipped by the existing suite.

Use the dedicated test database only:

```powershell
$env:ATELIER_TEST_DATABASE_URL='postgresql://atelier:atelier_local_only@127.0.0.1:15432/atelier_test'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
New-Item -ItemType Directory -Force .test-tmp | Out-Null
python -m pytest backend_pipeline/tests -q --basetemp .test-tmp/verification-run
```

Integration fixtures refuse any database name other than `atelier_test`; cleanup affects only that database. No synthetic rows were inserted into real `atelier`. Read-only before/after fingerprints cover all real rows and the exact catalog via `scripts/verify_comparison_readiness.py`. Reports remain private under `.storage-artifacts/verification/comparison-real-before.json` and `comparison-real-after.json`.

Week 1 angle embeddings, real Week 2 generation/encoding/comparison and both weeks' 329 transcript chunk embeddings are complete following explicit destination approvals. Real Call 3 remains unexercised because Week 2 had no refinement targets; its recovery behavior is covered by offline fixtures. Semantic threshold calibration, real retrieval/support/voice evaluation, actual Command Center deployment connectivity and the real brief pilot remain later work. Brief orchestration and Gate 2 are now implemented and verified offline. The saved persistent switches are still false.

## Approved-angle briefing and Gate 2

`approved_angle_brief_v1` uses existing tables and five leased per-angle jobs: preparation, research, context, writing and validation. The first approval intent is idempotent; retries preserve its frozen input/artifact contract. Brief scopes leave `weeks.active_run_id` and weekly status intact. The draft run stops at `waiting_for_review`; Gate 2 approval/rejection ends that scope without enqueuing production.

Core research uses mandatory original grounding plus exact pgvector/full-text discovery and RRF. Source/angle/moment/vector/use hashes are checked before requests and commits. Dossiers and raw/audit/billing artifacts stay private. Query embeddings are purpose/model-bound transient caches. Numerical claims bind value, units, timeframe and subject to exact original supporting text; public quotations and names require actual source-use/attribution permission. Reviewer-model output supplements these checks and does not establish independent factual truth.

Default switches are `ATELIER_BRIEFS_ENABLED=false`, `ATELIER_ALLOW_BRIEF_GENERATION=false`, `ATELIER_ALLOW_BRIEF_WEB=false`, with empty actor capability lists and unset `ATELIER_ANGLE_APPROVAL_CUTOFF`. Configure an actually reviewed brand bundle from `brief-brand-bundle.example.json`; its pending template cannot authorize a real approval. Gate 1 approval queues the first brief in the same transaction; if the brief cannot be queued (for example, the bundle is missing), the approval still commits and a failed `brief_generation` run records the reason in `error_summary`. Queue the brief again with `storage_cli brief` once the configuration is fixed. Complete selected guide texts, source-document hashes and exemplars belong in that reviewed packet, not new SQL tables. Writer/reviewer overrides remain application settings. The ordinary SQL worker handles briefing; Redis/RQ is unnecessary.

The brief retrieval index (`transcript_chunks_text_search_idx`, migration 002) is applied by `python -m backend_pipeline.storage_cli migrate` with every other migration; the separate `brief-indexes` command is gone (0.B3).

Protected brief routes include `/briefs` (bounded `week_id`, `status`, `limit`, `offset` filters), `/briefs/{id}`, `/versions`, `/export.json`, `/export.md`; mutation endpoints cover edits, answers, scoped review, clearance, decisions and revisions. `/angles/{id}/research` shows actual jobs/dossier/costs; `/angles/{id}/brief` requests the approved-angle intent. `/briefs/contract` exposes the strict document schema. `/search/transcripts` inspects compatible cached query vectors only and reports `awaiting_query_encoding` instead of calling a provider. The BFF retains team sessions, trusted actors, CSRF checks and its 64-KB mutation limit.

The separate **Content Brief Review** reads real SQL results. Human edits/answers/reviews create linked replacement versions; unsupported edits cannot retain the earlier semantic-review hash. Required questions, deterministic blockers, changed dependencies and incomplete-history acknowledgement prevent approval. Source permission references cannot override an explicit upstream restriction. Revision instructions must explicitly request changing a locked field; merely mentioning/preserving it does not unlock it. Added context uses inspected evidence IDs, never arbitrary browser-supplied proof.

`python -m backend_pipeline.storage_cli brief --angle-id <id> --actor <trusted-id> --mode replay` queues cache-only work. A replay intent cannot silently become live after a switch change. A run freezes its knowledge-base version, prompts, schemas and models at its first stage; when they change mid-run it fails with "Frozen brief execution contract changed", and an editor or approver starts a fresh run for the same approved card with `storage_cli brief --angle-id <id> --actor <trusted-id> --regenerate` (or `POST /angles/{id}/brief` with `"regenerate": true`): the new run key adds a regeneration counter (4.B1), recorded on the run with the run it replaces, which is kept, marked `superseded_by` and can no longer be retried. Gate 2 re-checks a v2 or v3 brief with the rejection rules and lint patterns of the knowledge-base version the brief pins (the store, else `knowledge_base/archive/<version>/`); a version found in neither blocks approval. Contract v2 is superseded by v3 for new briefs (`deploy/production-settings.json`); a v2 brief warns at Gate 2 that no reviewer from a different model family read it. Following separately authorized pilot setup, `activate-brief --run-id <id> --expected-input-hash <hash> --actor <trusted-id>` records explicit live mode without dispatching; retry/start the worker separately. It refuses synthetic/already-dispatched scopes and disabled live capabilities. No live activation was performed here.

Optional web framing uses a bounded `WebResearchProvider` interface and an approved public topic/question packet. No production adapter is configured. Source URL/domain/90-day rules and artifacts are checked; unavailable context is labelled. External framing is never internal-result proof.

Billing records use received provider usage, retain unknown costs, and distinguish cache recovery from new requests. Query batches and web receipts are included in brief-specific cost projections without changing legacy cost-report contracts. Verification runs use fixtures and an outbound HTTP guard. See [implementation status](../implementation-status-content-briefs.md), the synthetic brief report, final JUnit records and real before/after fingerprints under `.storage-artifacts/verification`.

Latest brief verification: **190 full-backend tests plus 41 final focused checks passed; 19 affected frontend/auth/proxy tests passed**. TypeScript and production build pass. The real retrieval smoke covered twenty sources/329 compatible chunks and verified 112 expanded original passages using an existing vector, without query encoding or content writes. All real row fingerprints remain unchanged and all persistent switches remain false. Readiness: `.storage-artifacts/verification/brief-readiness.json`.
