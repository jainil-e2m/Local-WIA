# Implementation context — transcript-to-angle backend

Latest user request, verbatim:

> I approve of using the GTP-OSS 120B Free. Can we build the entire backend pipeline till the content angle generation using the specific tech stack. For now we build upon the decided storage system. I want us to use that for the purpose of refining the prompts for the llm calls in order to adapt it according to the responses received. Thoroughly reason on this.

This changes the task from reasoning-only to implementation. GPT-OSS 120B Free is now approved; the earlier spelling is interpreted as the discussed exact OpenRouter ID openai/gpt-oss-120b:free. It does not approve uploading private transcripts to an unreviewed provider, payments, public exposure, model-weight training, or downstream briefs/packs/publication.

## Carried-forward contracts

Transcripts first; two logical LLM stages (moments/context, then grounded arguments); no extra LLM similarity judge; all valid candidates retained; one active canonical vector per angle; all eligible distinct candidates strictly above the adjusted-score threshold visible, no four-item cap. Last turn means previous completed generation run. JSON authoritative while learning the production schema, Markdown review/labels, local pgvector rebuildable projection. Save full safe requests, returned responses, validated artifacts, usage, errors, lineage, vectors and reuse events for paid and free calls. Never save keys/authorization headers or inaccessible reasoning.

Use frozen prior-history snapshots, isolated experiment branches, actual execution clocks and explicitly simulated editorial clocks. Replays/rescores do not refresh generation age. Very-close keep-both behavior is still unresolved; the implementation must expose an explicit review/policy state instead of silently inventing that decision. Model self-scores and illustrative thresholds are not validated production quality.

The user will supply about three months of numbered weekly meetings starting June 2026. Existing user input root backend/zoom_backfill_meetings contains week1/week2. Exact date windows and source processing authority remain unconfirmed. Schedule is provisionally Saturday04:00 Texas; no scheduler is to be installed by this slice.

## Inspected implementation facts

- Supplied architecture: Python3.12+, FastAPI, Pydanticv2, RQ/Redis, SQLAlchemy2/psycopg3/pgvector, OpenAI-compatible OpenRouter model calls. Full production relational schema/Alembic can remain deferred by the subsequent JSON-testing decisions.
- The original tracked backend files remain user-deleted, unrelated frontend changes remain dirty. A fresh backend_pipeline directory is planned to preserve them; do not restore old files or move user transcripts.
- Python3.12.10 and pydantic, FastAPI, httpx, pytest, RQ, Redis, psycopg, tiktoken, uvicorn, ruff, OpenAI SDK, SQLAlchemy and pgvector libraries are available. Current RQ is1.16.2; production requirement will target a documented newer pinned version and Windows testing can use direct execution rather than Unix-fork worker assumptions.
- Docker CLI exists but its daemon is not running. pg_isready reports no PostgreSQL on127.0.0.1:5432. No services started/installed or keys inspected.
- Small local excerpts of two supplied .txt files were read to identify format. Both begin WEBVTT and contain timestamped speaker cues. Treat text as untrusted source evidence, never executable instructions. No material was sent to an external inference endpoint.
- Current .gitignore excludes corpus/, transcripts/, VTTs and .data/, but the user backfill .txt area is untracked. As a normal scoped implementation safeguard, add a specific ignore rule for backend/zoom_backfill_meetings without moving/deleting files.
- OpenAI Docs skill read; official GPT-OSS/embedding docs and OpenRouter structured-output parameters fetched. No API-key helper available. LLM must stay the exact approved :free ID, disable model fallback, validate structured responses locally, and save refusals/truncation/invalid data without promoting it.

## Implementation plan and bounds

Build a Python package with typed manifests/results, strict WEBVTT ingestion, meaning-preserving source spans and full-coverage batches, versioned prompt files, a durable single-writer JSON store, cacheable LLM/embedding adapters, two-stage orchestration, deterministic cosine/recency ranking and review states. Add FastAPI local-only job/review endpoints, CLI for inspect/prepare/plan/replay/live/rescore/feedback/comparison, RQ queued jobs with JSON-backed reconciliation, and a minimal pgvector projection plus Docker Compose setup.

Offline fake-provider fixtures are explicitly synthetic, not fake completed runs over real meetings. Live mode requires approved source/provider policy and explicit enablement; paid embeddings additionally require a configured budget/paid-call gate. The proposed default embedding is Small/1536, not an implicit authorization to charge. No new source connectors, Slack, research, angle rewrite judge, frontend integration or pack generation.

Prompt refinement uses immutable attempts and prompt-content hashes, records human labels/corrections, reuses unaffected extraction for Stage2 prompt changes, invalidates dependents when extraction/source/policy changes, and compares runs against frozen sources/history. Do not automatically edit prompts or convert model output into policy without human review.

Save further checkpoints and final artifact/outcome details here before any context boundary. Earlier complete context and document snapshots remain in this directory.

## Implementation outcome

Created `backend_pipeline/` with typed models, config, WEBVTT/text ingestion, atomic JSON store, versioned moment/angle prompts, OpenRouter GPT-OSS adapter, OpenAI Small embedding adapter, deterministic cosine/recency ranking, FastAPI endpoints, CLI, RQ-compatible job entry point, minimal pgvector schema/projector, Docker Compose service definition, README, and tests.

Safety: `plan` performs source discovery/manifest persistence; `fake` completes the offline contract with deterministic empty synthetic output; `live` requires CONTENT_ATELIER_LIVE=true plus provider credentials. No live call was made. No PostgreSQL table was created because Docker daemon and local PostgreSQL are unavailable. Existing deleted backend files and frontend modifications were not restored or changed. The user-supplied backfill root was not added to Git after the repository-specific ignore rule was added.

Verification on 7 October 2026: Week1 discovered 9 transcript exports. `python -m backend_pipeline plan --week 1` passed. `python -m backend_pipeline run --week 1 --mode fake` passed with 0 moments/angles because the fake provider intentionally returns no editorial content. `python -m pytest -q --basetemp=testing/.pytest-tmp` passed 3 tests. `ruff check backend_pipeline` passed. `python -m compileall -q backend_pipeline` passed. One initial plan attempt failed due to Windows replacement of an existing ignored artifact; JsonStore was amended to preserve completed artifacts as immutable and replay succeeded.

Current implementation limitation to address before live testing: GPT-OSS provider structured-output support must be verified at the chosen OpenRouter endpoint at request time; the adapter requires parameters and disables fallbacks, then local Pydantic/reference validation remains authoritative. The current moment/angle schema sent to the provider is intentionally minimal and needs first-week response review before prompt revisions. PostgreSQL projection is code-only until a local pgvector service is started. Exact week date manifests and source/privacy approval remain open.

The prompt-refinement loop is implemented as versioned immutable attempts and compatibility fingerprints, not autonomous prompt mutation: source/Stage1 changes invalidate dependent Stage2 artifacts; Stage2-only changes reuse valid Stage1 output; human labels/review records should drive the next prompt version. Keep this boundary when extending the pipeline.

## Credential/model configuration amendment

The user requested separate credentials and configurable models for moments, angles and embeddings. Added `.env.example` and updated config/provider/README/API. Variables are `OPENROUTER_MOMENTS_KEY`, `OPENROUTER_ANGLES_KEY`, `OPENROUTER_MOMENTS_MODEL`, `OPENROUTER_ANGLES_MODEL`, `OPENROUTER_BASE_URL`, `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, `OPENAI_EMBEDDING_MODEL`, plus dimensions and scoring thresholds. Embeddings can use a separate OpenRouter-paid key/base URL or direct OpenAI key/base URL. A shared `OPENROUTER_API_KEY` and `OPENAI_API_KEY` remain backward-compatible fallbacks.

Live mode validates credentials before pipeline execution; fake/plan modes do not require them. Environment-loading test successfully resolved three independently configured model IDs; Ruff and all 3 tests passed after the change. No real credentials were read or stored. OpenRouter embedding endpoint/model availability and the account's permissions/terms still require verification before the first live call.

## Persistence/reuse audit amendment

The follow-up storage audit found that initial persistence did not yet provide reliable embedding reuse and that random moment IDs/model-agnostic cache keys could invalidate or incorrectly reuse downstream work. These paths have now been corrected and tested. The completed evidence, 19-test result and remaining implementation limits are recorded in `2026-10-07-artifact-reuse-correction-context.md`; consult that checkpoint and the updated backend README for current behavior rather than treating the earlier three-test wiring result as full reuse verification. Added credential-free replay-only mode, exact versioned request keys, raw response receipt before parsing, stable IDs/original dates and failed/completed run lifecycle updates. No live inference or database integration test has occurred.
