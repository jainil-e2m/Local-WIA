# Content Atelier backend pipeline

<!-- governing-plan-note -->
> **Historical (marked 19 October 2026, plan revision 7).** This file records the backend as it stood around 13 to 16 October. The governing plan is [the implementation plan](docs/Content-Atelier-Implementation-Plan-Brief-Generation.md); the current commands and variables are in [DEPLOYMENT.md](../DEPLOYMENT.md); where they differ, those win.

**Real packs and calendar (16 October 2026):** the SQL worker now handles an explicit
approved-brief-to-pack production workflow. The calendar stores and reads per-asset
schedules through authenticated APIs. See [deployment and behavior](docs/Calendar-Deployment.md).
Live pack generation remains independently disabled by default. The file-backed
calibration runner described below retains its separate scope.

**Current strategic discovery release (13 October 2026):** both LLM stages now use Whitney's feedback, explicit ATTRACT/WARM/CONVERT strategy and new typed opportunity contracts. Reader decisions are optional; internal intelligence and research-required public hypotheses are retained separately. See [the implementation and verification notes](docs/2026-10-13-Strategic-Discovery-Revision.md) and [the exact prompt snapshot](prompts-strategic-v1.md). Models and external-call permissions are unchanged. The earlier profiles and Week 1 results described below are historical diagnostics, not output from the revised mechanism. Current templates cannot recreate an old exact-profile replay request.

**First live test of that release:** the user-authorized Week 2 run on exact `openai/gpt-6-luna-pro` executed both stages. Seven moments were proposed; five passed individual source checks and two failed literal quotes. An explicit partial-pool continuation produced four WARM candidates and one internal insight for $0.15221204 combined reported cost. The parent remains failed; this is not a whole-week pass. See [the full test review](../research/week2-luna-pro-strategic-test-review-2026-10-13.md). Models were overridden per test, not changed in `.env`; actual replay incurred zero new cost.

**SQL workflow:** [STORAGE.md](STORAGE.md) documents the implemented thirteen-table PostgreSQL/pgvector baseline, source admission, six-candidate Luna bootstrap, durable generation/encoding/matching stages, Gate 1 APIs and verification. The isolated real database has both June 2026 corpora prepared. External SQL generation and encoding are disabled independently. Use `python -m backend_pipeline.storage_cli` for this workflow.

The sections below describe the separate file-backed calibration runner. Its prompts, model configuration and artifacts remain available to the testing chat; the legacy `angle_vectors` projection is not used by the new SQL workflow. The legacy experiment HTTP routes (`POST /runs`, `GET /runs/{id}/review`) are retired (plan 6.B8); the local experiment CLI remains available.

This package implements the transcript-to-content-angle testing slice. It uses Python, Pydantic, JSON artifacts and the user-selected OpenRouter `openai/gpt-6-luna` model for both LLM stages. OpenAI `text-embedding-3-small` at 1,536 dimensions and a rebuildable pgvector projection remain configured but disconnected. The test-phase source of truth is `testing/.data/`; no production schema is assumed. Earlier GPT-OSS and Apodex measurements remain historical diagnostics, not Luna token counts.

**Current approved test scope: generation only.** `CONTENT_ATELIER_EMBEDDINGS_ENABLED=false` is the default and local setting. Every week stops after saving key moments and angle candidates. Embedding requests, vector-history similarity, recency penalties and final visible selection are disconnected until the user explicitly approves reconnection. Existing embedding/ranking code remains intact.

The legacy projection schema is in `backend_pipeline/db.py`. `project_json_vectors` remains a calibration-only rebuild adapter. The new SQL workflow uses inline vectors on `content_angles` and `transcript_chunks`, with real PostgreSQL/pgvector integration checks described in [STORAGE.md](STORAGE.md).

## Backend layout and working directory

All implementation/setup files now live under `content_atelier/backend/`:

```text
backend/
  backend_pipeline/
    api.py, cli.py, pipeline.py, worker.py          Application entry points and orchestration
    config.py, models.py, contracts.py             Configuration and typed contracts
    ingest.py, prompts.py                           Sources and prompts
    llm/                                           Every model call: requests, routing, run plans, cache, cost, repair, llm_runs
    store.py, scoring.py, db.py                    JSON authority, ranking and pgvector projection
    prompt_templates/                             Two-stage prompts and curated editorial policy
    evaluation_cases.json                         Synthetic editorial diagnostics
    tests/                                        Offline contract/reuse/path tests
  .env.example
  pyproject.toml
  requirements.txt
  compose.yml                                     The whole local stack: Postgres, Redis, API, scheduler, workers
  prompts.md                                      Exact stage-template snapshot and timestamp ledger
  README.md
  zoom_backfill_meetings/                          Existing private inputs, unchanged
```

Run commands below from `content_atelier/backend/`, not the application root. Import paths remain `backend_pipeline.*`. The project-root datastore at `content_atelier/testing/.data/` remains in place; source identifiers and compatible request keys are not renamed by this restructure. Research, client-call ledgers and context snapshots also remain at the project root. The new backend setup files replace the directory's previously removed legacy setup, not the deleted `atelier` implementation. Use absolute paths for `CONTENT_ATELIER_DATA_ROOT` and `CONTENT_ATELIER_TRANSCRIPT_ROOT`, as in the template; custom relative paths are interpreted from the command's working directory.

## Safe modes

`plan` parses and stores source manifests without calling a provider.

`fake` exercises the configured execution boundary with a deterministic empty fake provider. Generation-only is the default. This is useful for wiring/failure tests, not a content-quality result.

`replay` uses only compatible previously validated **live** artifacts. It requires neither live enablement nor credentials and stops on any missing artifact without contacting a provider. It never substitutes fake outputs for real ones. Matching models, endpoints, dimensions, prompts and original transcript files must still be configured/available; this command reconstructs a report from those inputs, not from an arbitrary run ID.

`live` requires `CONTENT_ATELIER_LIVE=true` and the LLM credentials. Set `OPENROUTER_API_KEY` once for both stages or use explicit `OPENROUTER_MOMENTS_KEY`/`OPENROUTER_ANGLES_KEY` overrides. The user supplied the actual keys locally and authorized the Week 1 test; they are not reproduced here. With embeddings disabled, no embedding credential is required or used. The separate embedding configuration is retained only for later approved reconnection. There is no silent paid-model fallback and test authorization does not clear public reuse.

### Current Luna generation-only configuration

Configured 8 October 2026: both stage models default to exact `openai/gpt-6-luna`; `.env` and `.env.example` agree. The user supplied a funded OpenRouter key for this specific comparison. Exact-model compatibility was checked against [OpenAI's Luna documentation](https://developers.openai.com/api/docs/models/gpt-6-luna) and [OpenRouter's route](https://openrouter.ai/openai/gpt-6-luna). The shared key resolves to both stage credentials, but never supplies the embedding credential. Stage-specific keys take precedence. Process variables still override local files. Apodex remains configurable; it is no longer the active default.

The shared key is set locally at `OPENROUTER_API_KEY=`; optional stage-key lines can stay blank. `.env` is Git-ignored; do not put credentials into documentation, command history or saved request artifacts. Paid embedding keys are not needed during this phase. Default live mode remains false, so paid calls still require explicit enablement.

`CONTENT_ATELIER_LLM_PAYLOAD_FORMAT=compact_weekly` connects the lossless weekly reader to canonical source IDs, exact-quote/context validation and request cache identity. It sends the whole week once, preserving all dialogue and source speaker names. Raw bytes and reference maps are archived under `weekly_packets/weekN/<hash>/`; compact canonical source views use `sources/compact_weekly/...`, separate from legacy views. Unknown Zoom metadata stays null. The legacy flat mode/character guard remain available for compatibility tests, but local input-size rejection is disabled for the newly user-authorised uncapped test.

For constrained tests, cache Luna's public route metadata with `python -m backend_pipeline.token_budget --model openai/gpt-6-luna`. This explicit command fetches public limits only; it never loads private source packets or API keys. Installed tiktoken has no established native Luna mapping, so the available local preflight is explicitly a conservative UTF-8 text-byte allowance, not an exact native-token measurement. When input checks are enabled it verifies model ID/checksum and supported parameters, checks limits and an explicit output reserve, and refuses overflow without batching/truncation. **The current uncapped test bypasses this rejection entirely**, retaining only input-size diagnostics. Native counts come from returned provider usage. Apodex's separate pinned published-tokenizer preflight remains available; its historical counts are not relabelled as Luna counts.

Historical Novita/Apodex requests rejected JSON-schema format with HTTP 400. This Luna comparison deliberately retains `CONTENT_ATELIER_LLM_RESPONSE_FORMAT=json_object`, appends the complete strict response contract at system authority and validates locally. JSON mode does not offer provider-enforced schema decoding. Reasoning effort stays low and response timeout 900 seconds. Earlier Luna attempts used 65,536 then 16,384 output reserves; **the user has now explicitly removed application input/output caps**. Actual/template settings have blank `CONTENT_ATELIER_LLM_COMPLETION_TOKENS=` and `CONTENT_ATELIER_LLM_INPUT_LIMITS_ENABLED=false`. Blank resolves to None and omits both max_tokens and max_completion_tokens; it does not send a hidden substitute, zero or an “infinite” value. The explicit false flag bypasses compact-week conservative capacity rejection and legacy character rejection while saving diagnostics. The retained 120,000-character default is inactive in this test. Model/provider defaults, finite capacity, account credits/quotas and response timeout still apply. OpenRouter documents both output-cap fields as [optional parameters](https://openrouter.ai/docs/api_reference/parameters).

Luna alone omits temperature because its exact route does not advertise it; other model bodies retain 0.2 and their historical compatibility. Luna requests `usage:{include:true}` for cost/usage accounting. Exact settings/messages are fingerprinted. Missing/malformed/partial results are preserved and rejected, never auto-repaired or silently accepted. Prompt-template text/editorial policy is unchanged. To restore constrained tests, explicitly enable the input checks and configure an appropriate positive output reserve; the class default leaves checks enabled. This override removes size limits, **not** schema/source validation or the embeddings gate.

Generation-only saves `moments.json`, `candidates.json` and `review.json`, marks the manifest `generation_completed`/`generation_only`, and leaves candidate vectors/similarity/adjusted scores null. It does not write `angles.json` or an embeddings directory. High model self-scores do not make candidates the final similarity-verified visible set. After explicit reconnection, identical validated LLM artifacts can be reused for the vector leg.

### Latest Week 1 Luna result — authorised saved-moment Call 2 continuation

The user subsequently authorised reuse of A3 key moments to execute angle generation. Existing explicit partial-pool calibration ran Call 2 on the **seven individually validated moments and original surrounding transcript passages**, without modifying either rejected record or rerunning extraction. `week1-gpt6-luna-partial-angle-diagnostic-20261008-a4` produced **six validated angle candidates**, status partial; original A3 remains failed. Call 2 reported **$0.009089175**, 56,446 input / 4,067 completion tokens. New extraction cost $0; A3+A4 pair cost $0.02571535. Embeddings, history/ranking and final visibility remain disconnected; no candidate is founder-approved. All requests remain uncapped locally. Actual cache-only replay R1 reproduced identical candidates/lineage with zero new requests and $0 new cost. See the [six-angle execution and source review](../research/week1-gpt6-luna-content-angle-review.md) and saved candidates/costs.

To replay this specific partial diagnostic with current Luna settings and original source bytes, without new inference:

```powershell
python -m backend_pipeline.calibration --from-run week1-gpt6-luna-generation-only-20261008-a3 --run-id week1-luna-diagnostic-replay-new-id --mode replay
```

Use a fresh report ID. The command fails on a cache miss rather than charging. Ordinary whole-week execution still stops at a failed extraction; this explicit diagnostic is not an automatic partial fallback or complete-week acceptance.

### Uncapped extraction A3 — preserved upstream failure

The user supplied a new working key and requested removal of local input/output caps. `week1-gpt6-luna-generation-only-20261008-a3` returned nine proposed moments, seven individually valid in offline review, but the full response failed two exact quote-binding checks. One quotation changed initial capitalization; another omitted the actual quoted cue from its anchors. Native usage: 116,370 input / 4,160 completion; **$0.016626175** reported Call 1 cost. Normal `stop`, not an output-length failure. Call 2 not attempted, $0; no Luna angles/embeddings. Full input and prompts are unchanged; actual stored request has no output-cap fields and local input rejection is disabled. See the [uncapped retry review](../research/week1-gpt6-luna-uncapped-retry-review.md) for raw output, costs and diagnostics. No automatic repair or additional paid retry was made.

### Earlier Week 1 Luna attempts

`week1-gpt6-luna-generation-only-20261008-a1` received HTTP 402 without output or usage. The single bounded retry, `week1-gpt6-luna-generation-only-20261008-a2`, returned 14 proposed moments with 116,370 input and 6,631 completion tokens. OpenRouter reported **$0.017861675** for Call 1, including its cache-write/input and completion accounting. It finished normally, but failed strict validation on an invalid `buyer tension` enum. Offline per-record review found 11 individually valid proposals and two additional quote-binding failures; a coverage note also cites nonexistent IDs. No failed record was repaired or promoted to the validated cache. Call 2 was **not attempted**, cost $0; no Luna angles or embeddings exist. The original 402 attempt has unknown billing rather than an assumed zero charge.

See the [Luna execution, cost and evidence review](../research/week1-gpt6-luna-test-review.md). Both stages are configured and cost-tested offline, but a successful two-stage Luna run has not yet occurred. Further paid retries or a deliberately partial-pool Call 2 diagnostic require a new decision; neither is an automatic fallback.

### Historical Apodex result and explicit partial-pool diagnostic

The real test included all nine exports/3,238 turns. Active extraction profile v3 uses meeting-scoped `mN.tNNNN` references and exact first/last context boundaries. The backend retrieves the entire contiguous same-meeting interval and applies the original strict quote/source checks. Exact nine-meeting boundary/count acknowledgements are delivery acknowledgements, not proof of comprehension.

Historical whole-week extraction `week1-apodex-generation-only-20261008-a4` remains **failed**: seven proposed moments include two invalid records. A separate, explicitly labelled diagnostic reused the five individually valid records for Call 2 and saved **five angle candidates** under `week1-apodex-partial-angle-diagnostic-20261008-a5`. That diagnostic stays `partial`, does not promote failed extraction into the cache, and never enters the embedding/history/ranking leg. No candidate is human-approved or ready unchanged. See the [full execution and editorial review](../research/week1-generation-only-test-review.md) for each candidate, evidence limitations and next prompt targets.

To replay the **diagnostic only**, with no new extraction, angle or embedding request:

```powershell
# Use a separate shell with the original Apodex request settings, not Luna defaults.
$env:OPENROUTER_MOMENTS_MODEL = "apodex/apodex-1.1-mini:free"
$env:OPENROUTER_ANGLES_MODEL = "apodex/apodex-1.1-mini:free"
$env:CONTENT_ATELIER_LLM_COMPLETION_TOKENS = "65536"
python -m backend_pipeline.calibration --from-run week1-apodex-generation-only-20261008-a4 --run-id week1-review-replay-new-id --mode replay
```

Use a new report ID. The command defaults to replay, requires the exact original source bytes/reference map and current extraction profile, and fails on a Call 2 cache miss. It is not an automatic fallback in ordinary weekly execution. The actual `week1-apodex-partial-angle-replay-20261008-r1` replay reproduced identical candidates with original lineage and zero new service attempts. Ordinary full weekly replay cannot pass the failed extraction cache.

## Commands

From `content_atelier/backend/`:

```powershell
python -m backend_pipeline plan --week 1
python -m backend_pipeline run --week 1 --mode fake
```

For a fresh environment, install `requirements.txt` from this backend directory. Local API entry point: `python -m uvicorn backend_pipeline.api:app --host 127.0.0.1 --port 8000`. No service is started by moving the files. The local stack is `compose.yml` (plan 0.B12; `docker compose up -d --build` from this directory).

Live calls are intentionally explicit. The user authorized the Week 1 generation-only test, not embeddings or publication:

```powershell
$env:CONTENT_ATELIER_LIVE = "true"
python -m backend_pipeline run --week 1 --mode live
```

After the first successful live run, repeat without permitting new inference:

```powershell
python -m backend_pipeline run --week 1 --mode replay
```

Ordinary live reruns also consult the cache first, but a miss may make a new call. Use replay when a strict no-new-request guarantee is needed.

Environment mapping:

| Pipeline stage | Credential | Model | Base URL |
|---|---|---|---|
| Key moments/context | `OPENROUTER_MOMENTS_KEY` | `OPENROUTER_MOMENTS_MODEL` | `OPENROUTER_BASE_URL` |
| Content angles | `OPENROUTER_ANGLES_KEY` | `OPENROUTER_ANGLES_MODEL` | `OPENROUTER_BASE_URL` |
| Angle embeddings | `EMBEDDING_API_KEY` | `OPENAI_EMBEDDING_MODEL` | `EMBEDDING_BASE_URL` |

If the two LLM stages share one key, set `OPENROUTER_API_KEY` once; blank stage-specific key variables inherit it. Alternatively set both stage keys explicitly. Do not put keys in command history or commit `.env`. The settings loader supports `backend/.env`; `content_atelier/.env` remains a backward-compatible fallback. Precedence is process environment, backend-local file, then project-root file. No existing secret was relocated by the configuration change.

The existing input root is `content_atelier/backend/zoom_backfill_meetings/`, containing week1, week2 and later folders; override it with `CONTENT_ATELIER_TRANSCRIPT_ROOT`. The input parser accepts `.txt`, `.vtt`, and `.webvtt` files containing WEBVTT cues. Each week is processed as a source snapshot and later weeks do not enter earlier runs.

## Prompt refinement

The [consolidated prompt ledger](prompts.md) contains both stages' full system/user templates, the shared policy, timestamp provenance, release history, component hashes and embedding-input assembly. It is a documentation snapshot; runtime still loads the files under `backend_pipeline/prompt_templates/`.

Prompt templates are versioned in `backend_pipeline/prompt_templates/`. Every stage stores its complete rendered request, prompt version, raw provider body, validated artifact and dependencies. A compatible artifact is reused on a later run. Prompt changes produce a new fingerprint, preserve the old response, and can reuse Stage 1 when only Stage 2 changed. Human labels should be added as separate review records before changing prompts; the pipeline never automatically learns policy from model output.

Prompt profile v2 includes a shared curated Whitney editorial policy, actual surrounding source turns in the Stage 2 packet, complete nested Pydantic response schemas, unique/full coverage acknowledgement checks, literal quote checks and chronological same-source context. Model score anchors distinguish grounded proposals from unsupported result claims. Upstream qualifications and handling concerns are preserved in angle records; source assertions identify their supporting moments. These are source/provenance contracts, not automatic semantic fact-checking or publication approval.

The backend now builds one canonical embedding signature from audience, tension, argument, take, mechanism and reader decision. Call 2 no longer returns a free-form signature. Working titles, scores and generation times do not affect that representation. Generated candidates contain the signature but no vector while embeddings are disconnected. One active vector per approved/refined signature/profile is reserved for later reconnection.

The [corpus-grounded prompt review](<../research/transcript-angle-prompt-robustness-review.md>) explains source authority, evidence-to-policy choices, examples, limits and the proposed human calibration procedure. `evaluation_cases.json` contains 14 synthetic diagnostics, explicitly not real evaluated model responses or reusable client proof.

### Whole-week preparation and token measurement

The user confirmed one physical extraction request for the complete week, with the full source speaker name on every turn. Batching, per-meeting calls, summarization and silent truncation are not authorized alternatives. The historical flat v2 packet has 316,004 locally measured system/user text tokens for Week 1, so it cannot fit GPT-OSS's 131,072-token reference context.

The separate local preparation entry point now archives exact source bytes, preserves every cue body after line-ending normalization, retains overlapping/source order, records every nonblank line, and compacts only export syntax and repetitive representation. Cue times are `start+duration` in seconds, exactly reversible to milliseconds; full names remain in source dialogue. Unknown notes/plain text remain as untimed records. Invalid encoding/timing fails instead of silently losing text. Zoom metadata is currently missing and stays null; filenames are explicitly unverified labels, not dates or confirmed meeting names.

From this backend directory:

```powershell
python -m backend_pipeline.prepare --week 1 --provider-snapshot "../testing/.data/provider_catalog/2026-10-08-gpt-oss-status.json"
```

This command never loads `.env`, sends inference/embedding requests or accesses a cloud token-count API. It requires the verified public tokenizer vocabulary already cached under `testing/.data/tokenizers`; a missing cache fails locally rather than downloading during private processing. Optional CLI flags select input/datastore paths, model label, reference context, completion reserve and safety margin without loading secrets. A model label override does not change the tokenizer/profile: this diagnostic is for GPT-OSS, not generic model counting.

Artifacts are immutable and content-addressed under `testing/.data/preparations/weekN/<fingerprint>/`: original bytes, complete normalized source records, source packet TXT/JSON, exact request, rendered messages, reference map, integrity checks, provider snapshot, token report and Markdown report. Identical inputs/profile/settings reuse the directory. These are preparation artifacts, not validated model responses or entries in the inference-result cache.

Measured Week 1: nine sources, 3,238 cues; 105,052 message-text tokens plus a 549-token schema proxy. A proposed 20,480-token combined reasoning/final-output reserve and 2,048-token provider-format margin leave 2,943 tokens of context headroom. The coverage-only response costs 8,729 tokens before substantive moments. These are local tokenizer counts and labeled engineering allowances, not an exact hosted-provider usage bill or proof of editorial completeness. A 24,576-token response reserve already exceeds the reference context once the same margin is included.

Historical state at the GPT-OSS preparation checkpoint: the live runner was not connected to that packet and the legacy 120,000-character guard blocked its 363,290-character body. The subsequent authorized Apodex test uses the deliberately connected lossless packet and a separate published-tokenizer preflight described above. The standalone preparation command and its GPT-OSS counts remain unchanged; relabelling them does not count Apodex tokens. The legacy guard is not raised. No paid fallback was selected when GPT-OSS's free route was absent.

Full measured reasoning: [Week 1 payload and GPT-OSS readiness review](../research/week1-payload-token-readiness.md). The prompt ledger records the compact interpretation supplement separately from the unchanged v2 live prompts.

## Local persistence and compatible reuse

The default root is `testing/.data/`, overridden by `CONTENT_ATELIER_DATA_ROOT`. JSON is the machine-readable datastore, not Markdown and not a database cache that disappears when pgvector is rebuilt. Keep a protected backup of this directory and original inputs. Git ignore rules do not provide encryption or a backup.

```text
testing/.data/
  sources/weekN/<source-id>/<revision-hash>.json     Normalised source spans and revision provenance
  cycles/weekN/snapshots/<snapshot-hash>.json        Immutable weekly source snapshots
  cycles/weekN/sources.json                         Latest weekly source snapshot pointer
  service_calls/<request-hash>/attempts/<artifact-id>/
    request.json                                   Exact safe request, saved before a call
    response.raw.json                              Received provider body, saved before content parsing
    output.received.json                           Parsed output, when parsing succeeds
    artifact.json                                  Validated output/usage/lineage, or failure record
    cost.json                                      Per-attempt returned billing and validation status
    preflight.json                                 Local model-specific capacity check when live
  cache/artifacts/<request-hash>.json               Pointer to a validated, checksummed artifact
  experiments/default/runs/<report-run-id>/
    manifest.json                                  Report lifecycle and configuration profiles
    moment_extraction.json                         Original or reused Stage 1 service artifact
    moments.json                                   Validated key moments and surrounding-context references
    angle_generation.json                          Original or reused Stage 2 service artifact
    candidates.json                                All generated candidates, saved before embeddings
    embeddings/<angle-id>.json                      Vector, model/dimensions and artifact reference
    angles.json                                    Candidates with saved vectors and adjusted scores
    review.json                                    Visible IDs and mechanically acknowledged coverage counts
    reuse/<artifact-id>.json                        Original generation reference; zero new inference cost
    costs/<artifact-id>.json                        Stage billing record, including rejected responses/reuse
    cost_summary.json, cost_summary.md              Both stages, known subtotal and unknown total states
```

Raw failed/truncated/refused responses stay in their attempt directories. They are not silently accepted into the validated cache. A retry reuses successful earlier stages and may retry the failed stage. If the HTTP response never arrived, there is no returned body to save; an unknown outcome must not be interpreted as proof of no provider charge.

Cost recording begins before dispatch and is updated immediately upon raw receipt, before content validation. Returned `usage.cost` is authoritative, with native input/output/reasoning/cache details and upstream breakdown retained. A billed response remains billed even if its content fails validation. Missing cost is unknown, not zero; a stage never sent has zero new cost. Cached work retains its original cost/lineage but contributes zero new cost to the replay report. Reasoning tokens are already within completion usage and are not billed a second time. Summaries exclude credit-purchase fees and do not constitute enforced budgets or exactly-once billing. A run total is unknown if any dispatched call has unknown billing; known subtotals remain visible.

Reuse keys include cache/validation version, fake/live namespace, stage, endpoint, model, exact prompts/schema/request parameters and input dependency hashes. Embeddings are keyed by exact canonical signature text plus model, endpoint, dimensions and output format. Credentials are excluded from stored requests and fingerprints: changing a key alone does not invalidate identical work. Source revisions remain separate immutable snapshots.

| Change or operation | Expected inference behavior |
|---|---|
| Identical compatible rerun or backfill of already processed material | Reuse moments, angles and vectors; no new requests |
| Stage 2 prompt/model change | Reuse Stage 1; regenerate angles; reuse any exact unchanged signature/profile vector |
| Stage 1 prompt/model/source change | Rerun extraction; reuse Stage 2 only if its full resulting input is unchanged |
| Embedding model/endpoint/dimensions or signature change | Re-embed affected signatures only; reuse LLM outputs where compatible |
| Similarity/visibility/decay setting change | Rescore saved outputs; no model calls |
| PostgreSQL rebuild or later schema migration | Project saved vectors; no re-embedding required |
| Previously unseen week's meetings | New extraction/generation work is expected; only exact compatible artifacts can be reused |

Moment IDs are stable for identical evidence/output. Cached angle IDs, original run IDs and generation timestamps are preserved; a replay creates a new report, not a new content-generation event. An angle has one active vector in a given profile. Old profile artifacts can be retained for experiment provenance without comparing incompatible spaces.

Older artifacts from the initial incomplete cache implementation are retained, but not automatically reused: they lack the model/route/isolation guarantees of cache version 2. No automatic legacy promotion or automatic deletion is implemented.

The v2 prompt/schema release changes LLM request compatibility (LLM validation version 3). Earlier responses remain retained, but are not reused as if they had followed the revised instructions. Embedding validation compatibility stays at version 2: unchanged exact requests can reuse their vectors. Changed canonical signature text legitimately needs a new vector only during an authorised inference run; this review made none.

## Verification and boundaries

Run the offline tests from the backend directory, keeping the temp directory in the existing project-level testing area:

```powershell
python -m pytest -q --basetemp=../testing/.pytest-tmp
python -m ruff check backend_pipeline
```

Verified 8 October 2026 after relocation: **43 offline tests passed**, Ruff lint/format checks passed, Python compilation passed, and module CLI help ran successfully. Backend-root/default-path and synthetic environment-precedence tests are included.

Historical 8 October Apodex configuration checkpoint: **68 offline tests passed**; credentials were blank and no inference had run at that point. The new tests covered shared-key resolution, stage overrides, missing/blank-key rejection, embedding-key isolation and configurable model overrides. The user subsequently supplied keys and authorised the generation-only test above; the populated `.env` remains ignored, default live mode false and embeddings false.

After the authorised Week 1 test: **89 offline tests passed**; Ruff passed. Real attempts comprised four extraction requests (one format rejection) and one partial-pool angle request. All four responses with usage reported zero inference/upstream cost; the format rejection supplied no usage. Zero embeddings or database calls occurred. Nine source archives match current original bytes/hashes, a fifty-artifact JSON scan found no supplied credentials, and actual cache-only replay made zero new service attempts. The full weekly extraction still fails two evidence records; source-grounded review identifies semantic revisions in all five diagnostic candidates. These are honest failure/calibration findings, not a production acceptance.

Luna/cost-tracking checkpoint, 8 October 2026: **107 offline tests passed**, Ruff and changed-module format checks passed, compilation passed. Eighteen new synthetic tests cover model-specific compatibility/preflight, reported/missing/invalid billing, failed-response preservation, no-dispatch and timeout accounting, two-stage totals and zero-new-cost replay. The first final-suite invocation encountered a sandbox temp-directory setup error; rerunning with a fresh explicit workspace temp directory passed all 107. The actual paid Luna extraction failed content validation as documented above; offline two-stage accounting/replay tests are not a claim that real Luna Call 2 or live replay succeeded.

Uncapped retry checkpoint: **112 offline tests passed in 25.45 seconds**, Ruff/changed-file formatting passed. Five additional synthetic cases verify omitted output fields, explicit input-gate bypass for both payload modes, retained rejection/cost for bad quotations and blank environment configuration. Both stages resolve Luna, embeddings stay false and complete Week 1 remains 3,238 turns. The fresh run ID is `week1-gpt6-luna-generation-only-20261008-a3`; do not confuse earlier a1/a2 results with its outcome.

Nonempty counting-provider tests verify zero-request identical reruns; original generation lineage; prompt/model/profile invalidation; fake/live isolation; replay without credentials; preservation after a downstream failure; receipt of malformed responses before parsing; source revisions; corrupt-vector rejection; and JSON-to-projection reconstruction using a recording connection. Prompt-contract tests cover nested fields/schemas, source/context/reference boundaries, coverage, qualifier/handling preservation, rendering, canonical duplication and preflight. Tests use synthetic fixtures and mocked HTTP, not private transcripts or paid inference. Actual Novita JSON-object compatibility and partial-pool output were separately tested live; complete weekly success and a running pgvector database remain unverified.

This is a single-writer test-phase store. It does not yet implement concurrent request leases, exactly-once provider billing, automatic raw-response repair, cost budgets, frozen experiment history branches or simulated historical clocks. Do not run overlapping writers against the same datastore. Ranking uses the current clock while retaining original generation dates. The complete week must remain one extraction request, not automatic batching; this Week 1 fits, but future sizes and complete semantic coverage need validation. Editorial selection remains uncalibrated. The numerical within-run near-duplicate/very-close-pair selection policy is also not complete; neither prompt-only distinctness nor exact canonical duplicate rejection replaces that work. Do not treat a real weekly run as production-ready yet.

The current test configuration stops at unembedded review candidates; the preserved full execution branch can later stop at ranked visible records only after approved reconnection. Neither branch creates briefs, packs, external research, Slack ingestion, approvals, scheduled execution or public content.

## Future source intake (SQL/RQ)

The separate SQL intake service now supports future Fathom transcripts and authenticated Slack bot deliveries, attachment extraction, indexing and weekly source buckets. It does not scan or import the historical corpus or trigger editorial generation. See [Future source intake setup and bot contract](docs/Future-Source-Intake.md) and `intake.env.example`. Connectors remain inactive until explicitly configured and activated.
