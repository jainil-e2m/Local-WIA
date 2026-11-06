# Content Atelier context checkpoint — 8 October 2026

## Active user requests

Earlier unfinished request: “i want you to revisit the prompts for each of the llm calls for robustness, and matching the requirement of the content atelier i.e. according to the identified samples, past data from the corpus and the analysis derived from that. I want thorough reasoning on this and ensure that the prompts are adept.”

Newest additive request: “I also want to organize the backend implementation to be within the /backend directory. organize the existing implementation files for structuring into the backend directory of /content atelier.”

The user requires context checkpoints in this directory whenever the conversation is compacted or summarized. This is a record of requests, evidence, decisions and work state, not private internal reasoning. Earlier context and the detailed prompt review remain available in `2026-10-07-prompt-robustness-review-context.md` and `../research/transcript-angle-prompt-robustness-review.md`.

## Current layout and relocation

The executable package, four prompts and shared editorial policy, tests and synthetic evaluation scenarios are now under `content_atelier/backend/backend_pipeline/`. The README, `.env.example`, `pyproject.toml`, `requirements.txt` and `docker-compose.pipeline.yml` are under `content_atelier/backend/`.

The supplied transcripts remain under `content_atelier/backend/zoom_backfill_meetings/`; local authoritative artifacts remain under `content_atelier/testing/.data/`. No real credentials were read or moved. Moves used exact resolved paths validated within the workspace, and refused to overwrite existing destinations. Unrelated frontend changes and legacy implementation deletions were preserved.

Configuration derives the package, backend and project roots explicitly. Environment precedence is process variables, then `backend/.env`, then legacy `content_atelier/.env`. Default transcript/datastore paths are unchanged. Compose declares the existing project name `content_atelier`. Execute commands from the backend directory, including `python -m backend_pipeline --help` and `python -m pytest -q --basetemp=../testing/.pytest-tmp`.

## Prompt review implementation

The two logical LLM stages remain evidence extraction and angle generation, with GPT-OSS 120B Free unchanged. Prompts now apply a corpus-grounded shared editorial policy, preserve source qualifications and chronology, respect capable business owners, distinguish plans/estimates/reports from measured outcomes, and define distinctness through argument, mechanism and reader decision rather than headline variants. Actual source context accompanies moment summaries in Call 2. Nested closed schemas, complete input-ID acknowledgements and deterministic grounding checks were added. Canonical embedding text is built by code rather than the model. Existing embedding compatibility remains version 2; revised LLM requests intentionally receive new cache fingerprints.

Scope remains transcripts only, no fixed four-angle cap, no third LLM similarity judge, no briefs/packs/publication. All eligible angles above the adjusted threshold are intended to be visible. Similarity/recency is deterministic. Prompts do not resolve the still-open within-run near-similarity retention policy. JSON artifacts are authoritative interim storage; Markdown is a human ledger; pgvector is rebuildable. Prior responses, raw provider receipts, moments, angles and embeddings remain retained for compatible replay.

## Evidence and limitations

Primary voice/strategy guides, selected original ChatGPT user corrections, published emails, a carousel transcription and the earlier editorial analysis were reviewed. Export roles and assistant drafts are not automatically founder-approved. No new full visual/audio reel inspection or founder acceptance evaluation was performed. The OpenAI Docs skill informed schema hardening and calibration guidance; the existing OpenRouter model was not changed.

Week 1 contains 9 transcripts and 3,238 spans. Source text is 245,115 characters; rendered prompt messages are 870,794 characters, with another 2,359 characters of schema. These are character counts, not verified model token counts. A conservative live-request preflight now fails before a provider call above the configured character limit. Bounded context-preserving batching is still needed before running the entire week live. No real LLM/embedding requests, paid calls, private source uploads, database services or live PostgreSQL integration tests were performed.

## Verification state at checkpoint

Before relocation, 40 offline tests passed. A request-size diagnostic and two backend path/environment tests were subsequently added. Expected current count is 43, not yet verified at this checkpoint. The running pytest process is command session `54086`; poll for completion. Ruff reported two import-order errors in `backend_pipeline/tests/test_prompt_contracts.py` and `test_reuse.py` after changing the project root. Fix these with Ruff, then rerun lint, formatting, tests, compile checks and CLI help. Do not claim a final result until observed.

## Remaining handoff work

Verify the relocation and tests; check active documentation for obsolete paths; update the meeting ledger and review report with actual outcomes; preserve the four original v1 prompt texts alongside this checkpoint; provide a self-contained handoff for both prompt hardening and directory organization. Explicitly distinguish implemented offline invariants from unproven model/editorial quality, and warn that full-week live execution still needs bounded batching.

## Completed verification and handoff state

Both pytest runs after relocation completed successfully: 43 tests passed, most recently in 9.12 seconds. Ruff fixed the two import-order issues; final lint and format checks passed. `compileall` and `python -m backend_pipeline --help` passed from the backend directory. The former root `backend_pipeline/` directory no longer exists. Git ignore checks confirmed credentials, transcripts, datastore and test temp files remain ignored, while the backend `.env.example` remains trackable.

The project README, backend README, testing README, client-question ledger and prompt review now document current paths, verification and limitations. Original v1 texts are saved in `2026-10-07-original-v1-prompt-texts.md`. Existing frontend changes and deleted legacy backend implementation were not restored or modified. No real `.env` content was read; configuration precedence was verified with synthetic files. No real provider or database call occurred.

Implementation work for the two active requests is complete. The final handoff should link the backend instructions and thorough prompt review, state that commands now run from `content_atelier/backend/`, distinguish unchanged local storage from changed prompt fingerprints, report 43 passing offline tests, and identify bounded batching as the next necessary task before a full Week 1 live run. Do not claim model acceptance, completed near-duplicate policy or production readiness.

## Subsequent user request — consolidated prompt ledger

User: “store the prompts used for each step of the llm usage in an md called prompts.md in this directory. where all the prompts per stage are specified along with the timestamp of when they were created / edited.”

Created `backend/prompts.md` at the ledger snapshot timestamp 2026-10-08 10:56:47 +05:30 (Asia/Calcutta). It contains the exact five current runtime components: both stages' system/user templates and the shared editorial policy. It documents assembly order, dynamic placeholders, model/schema configuration, canonical embedding input (not a chat prompt), the absence of a third LLM selection prompt, and the edit/version/history protocol. Historical creation/v2 edit dates are 7 October 2026; exact historical times were not recorded and were not fabricated. The ledger includes SHA-256 hashes over UTF-8/LF source contents. All five copied blocks and hashes were checked against runtime files. No runtime prompt, profile, cache or credential was changed, and no model was called. Backend README links the ledger; the preparation-document index adds D-13.
