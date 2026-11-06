# Apodex configuration continuity — 2026-10-08

## Current authorization

Latest user request: "proceed with the configuration into the env for the model of apodex. I want it to be ready for testing. just the api key left to be inserted"

The user requires a Markdown continuity record in `content_atelier/context` whenever this chat is compacted or summarized. This file records the active task state after compaction; earlier research and requirements remain preserved in the other context files and backend/research documents. It contains task state and evidence, not private reasoning or credentials.

## Inherited requirements

- First implementation: transcripts only, Zoom backfill by week; production will use Fathom transcripts and source metadata.
- Call 1 must contain the entire week in one physical extraction request. No automatic meeting-by-meeting batching, summaries before extraction, silent truncation, or paid fallback.
- Compaction changes representation only. Preserve all spoken text, speaker names in each turn, timestamps, source order, greetings/endings, uncertainty, repetitions and overlapping turns.
- Call 1 extracts grounded key moments and faithful quotes with surrounding context. Call 2 generates an uncapped set of distinct, grounded content angles.
- Similarity/recency filtering is deterministic, using one embedding per angle. No additional LLM similarity judge. Compare against historical angles and the previous completed generation run; show all distinct angles above the adjusted-score threshold.
- JSON/Markdown artifacts are the authoritative prototype store, with local pgvector as a projection. Preserve paid/free requests, raw responses, validated intermediates and embeddings for compatible replay/reuse.
- Free-account LLM key and paid embedding key remain separate. Models are environment-configurable. Embedding choice remains OpenAI `text-embedding-3-small`, 1,536 dimensions.
- The user now chooses `apodex/apodex-1.1-mini:free` for both LLM stages. No inference or transcript upload is authorized merely to prepare configuration; current preparation is offline.
- Preserve existing secrets and unrelated dirty files. Edit local files with apply_patch. Do not print complete .env files or secret values.

## Previous measured state

- Week 1 has nine WEBVTT-format TXT files, 3,238 cues, 415,662 raw bytes. All speaker names are preserved in the compact preparation.
- Existing preparation artifact: `testing/.data/preparations/week1/fbdd50910e4c2d8192a80a8c17419a17ff4b0a74c8bd0bccfcdb02dfdff5c1f5`.
- GPT-OSS-specific count: 105,052 message tokens plus 549 schema proxy tokens, 20,480 reserved completion tokens and 2,048 margin against 131,072 context tokens. These counts are not Apodex token counts.
- Existing live runner still used a flat span payload and a 120,000-character safeguard; the lossless weekly compact preparation existed separately. Changing model IDs alone would not establish whole-week live readiness.
- Last completed offline suite: 62 tests passed. No live inference, embedding request or paid database operation has been performed.
- Zoom dates/name/timezone metadata are absent in the provided fixtures. Filename labels are unverified; metadata must not be fabricated.

## Public model facts from prior research

OpenRouter advertised Apodex through Novita/bf16 with 262,144 context tokens, zero input/output prices, JSON-schema/structured-output support and reasoning controls. The developer homepage advertised a free promotion through October 15. These are time-sensitive facts and require fresh public metadata checks before live use. Actual model quality on Whitney's corpus has not been measured.

Primary sources: https://openrouter.ai/api/v1/models/apodex/apodex-1.1-mini:free/endpoints ; https://www.apodex.com/ ; https://huggingface.co/apodex/Apodex-1.1-mini-NVFP4 ; https://openrouter.ai/docs/guides/features/structured-outputs . Novita's public privacy policy alone does not establish retention terms for customer transcript content.

## Work state at compaction

- A commentary update promised configuration of both LLM stages, preservation of credentials and offline-only verification.
- The OpenAI Docs skill was read completely for migration/token-budget safeguards. Its required official documentation search found https://developers.openai.com/api/docs/guides/token-counting ; that page still needs fetching before the migration reference/local implementation inspection.
- The Apodex homepage was fetched; its endpoint metadata URL failed in the web renderer. Public metadata can be inspected with an authorized public GET, without sending private content.
- No current-task .env contents have been read and no configuration or implementation changes have been made yet.

## Next checks

1. Fetch official token-counting guidance, read the skill's model-migration reference, and announce skill usage.
2. Inspect configuration/templates, pipeline, preparation code and tests; inspect actual environment settings with secret values redacted.
3. Configure both Apodex stage IDs, retaining separate embedding configuration and credentials.
4. Resolve the actual compact-request wiring and model-specific token-budget gates necessary for truthful testing readiness. Do not reuse GPT-OSS tokenizer counts as Apodex counts or simply disable size protection.
5. Run offline verification, save relevant artifacts, and document an explicit user-initiated live test command. Report any remaining gate honestly; do not claim that the API key is the sole remaining requirement unless verified.

## Related records

- `context/2026-10-08-free-model-selection-context.md`
- `research/week1-payload-token-readiness.md`
- `backend/README.md`, `backend/prompts.md`, `backend/backend_pipeline/prepare.py`
- `to_be_asked_in_next_call.md`

## Configuration outcome after verification

- Completed the official token-counting page fetch and read the migration skill reference. Its scoped-migration guidance informed retaining existing prompts/output contracts and reporting orchestration compatibility work explicitly instead of concealing it with a configuration override.
- Read-only, redacted inspection found neither `backend/.env` nor project-root `.env` existed. Created `backend/.env` with blank credentials; Git check-ignore confirms it is ignored.
- Both `.env` model IDs, `.env.example` and Settings defaults are now `apodex/apodex-1.1-mini:free`. The OpenRouter model page was freshly fetched and advertises the exact route and JSON-schema support. No inference validated this advertisement.
- `OPENROUTER_API_KEY` can be filled once for both LLM stages; Settings resolves it to each missing stage key. Explicit moment/angle keys override the shared key. Paid embeddings remain isolated under `EMBEDDING_API_KEY`, with OpenRouter `openai/text-embedding-3-small`, 1,536 dimensions in the local environment.
- All credentials are blank and `CONTENT_ATELIER_LIVE=false`. The 120,000-character safeguard remains intact. No prompt/template edit, historical artifact rewrite, source modification, private upload, model call, embedding request or database operation occurred.
- Added `test_apodex_config.py`: six offline tests for Apodex defaults/safeguards, shared keys, stage overrides, embedding isolation, blank-key rejection and model configurability. Full suite: 68 passed. Ruff lint, changed-file format checks and compileall passed.
- Actual local settings were verified using an allowlisted output containing only models, endpoint/dimensions, guard/live settings and key-presence booleans. No secret values were printed.
- Backend README and client-call ledger now distinguish configuration-ready from whole-week live-ready; U-16 records user selection and I-10's route-choice answer. Previous GPT-OSS numbers remain historical and explicitly non-transferable.

### Remaining honest handoff

The requested environment configuration is complete, but API insertion is not the only remaining whole-week live gate. The old runner uses flat spans and cannot consume the compact preparation. The smallest implementation follow-up is to wire lossless weekly source packet/reference maps into Call 1, evidence validators and cache identity, and provide Apodex-compatible local token preflight plus explicit output reserve. This is implementation work beyond model/env configuration; it has not been silently introduced in this turn. Full runs also need the separate paid embedding key. Actual source privacy permission, missing Zoom metadata and editorial calibration remain separate limits.
