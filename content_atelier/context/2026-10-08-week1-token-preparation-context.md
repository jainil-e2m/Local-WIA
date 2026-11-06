# Week 1 pre-LLM preparation — continuity checkpoint

Created: 2026-10-08. This checkpoint preserves the available conversation context, decisions and work state at a context compaction. It records evidence and decisions, not private deliberation. Earlier conversation continuity also exists in the other files in this directory.

## Current request (verbatim)

> I have the week 1 transcripts in the relevant folder that i want you to compact / process and form the payload using the implementation before sending to the llm. i want us to calculate the effective amount of tokens and then verify if the gpt oss would help for the testing or not. thoroughly reason over this task.

The request includes an annotation quoting the explanation that the 120,000-character safeguard is a prototype backend restriction, not GPT-OSS's context limit. The response must address that annotation using `:codex-annotation{index="1"}`.

## Established product and implementation decisions

- Backend implementation belongs in `content_atelier/backend`; preparation ends at content angles for now, not briefs or packs.
- Weekly historical backfill starts with Week 1, then progresses week by week. Historical sources are Zoom transcripts and Zoom metadata; production sources will be Fathom transcripts and metadata, not meeting summaries.
- One physical extraction request must contain the whole week's transcripts. No per-meeting splitting, automatic summary, silent truncation, or silent model substitution.
- Compaction is representation-only: preserve every utterance, greetings, endings, repetition, uncertainty, punctuation, annotations, overlaps, order and source boundaries. Keep the source speaker's full name on every turn, not s1/s2 aliases.
- Meeting dates, days, timezones and names should come from source metadata. Do not infer dates from folder labels, modification times or personal-room filenames. Provisional weekly cutoff remains Saturday 04:00 America/Chicago, subject to client confirmation.
- Call 1 identifies source-grounded key moments, verbatim dialogue and surrounding context. Any condensed summary must be separate from exact evidence. Call 2 generates unlimited distinct grounded angles. Show every distinct angle over the adjusted-score threshold, not an arbitrary four-angle cap.
- Previous turn means the previous completed generation run. Deterministic vector similarity and recency adjustment; no third LLM comparison judge. One embedding vector per angle. Local pgvector; separate logical collections in one database.
- Approved LLM model is exactly `openai/gpt-oss-120b:free`; paid embedding and free LLM credentials are separate and model names are configurable. Do not switch to a paid route without approval.
- Interim JSON/Markdown artifacts and compatible provider responses/embeddings must be retained and reused. Prompt history is in `backend/prompts.md`. All paid operations should preserve reusable request/response artifacts.
- User requires a Markdown context record in this directory whenever compaction or summarization occurs.

## Current evidence and progress

- No live LLM, embedding or pgvector request has been made for this task. No real `.env` has been read or printed.
- Week 1 is at `backend/zoom_backfill_meetings/week1`. There are nine TXT files with WEBVTT content and 3,238 timestamp cues. Counts by file: Carmen variants 192, 260, 397, 586, 709; Check-in with Gisselle 283; LeadLock Sequence Refresh 247; Messaging & Positioning / The Penny 308; Whitney room 256. No Zoom metadata JSON/CSV was found in the backfill folders.
- Existing ingestion strips cue lines, flattens multiline cue bodies and decodes with replacement. It does not yet establish lossless-source fidelity or carry meeting metadata. Existing prompts consume a flat span packet. Current task requires an explicit compact packet contract and a safe local preparation path before claiming readiness.
- Existing `_call_json` counts characters in a serialized request and blocks uncached live calls over 120,000 characters. This is not a token measurement. It must not be interpreted as proof the whole week exceeds model capacity. Legacy guard has not been changed in this task.
- `tiktoken==0.12.0` is installed. The official public vocabulary has been downloaded with approval and cached at `testing/.data/tokenizers`. Set `TIKTOKEN_CACHE_DIR` to that absolute directory. `o200k_harmony` initialized successfully. Local private transcript tokenization needs no network. No actual Week 1 token counts have yet been computed.
- The public vocabulary URL is `https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken`; tiktoken expected SHA256 is `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`.
- Credential-free public GET of `https://openrouter.ai/api/v1/models`, checked at `2026-10-08T06:33:40.8421181Z`, returned 467 models but did not include `openai/gpt-oss-120b:free`. Paid `openai/gpt-oss-120b` was listed with 131,072 context tokens and 117,964 maximum completion tokens. This does not establish permanent discontinuation or authenticated account status. It prevents clearing the approved free route as available on present evidence. No paid fallback is authorized.
- Parsed provider snapshot is retained in the tool orchestration store as `week1_provider_status`; it still needs saving into the preparation artifacts.
- OpenAI Docs skill and its selected model-migration reference have been fully read. Relevant primary sources: `https://developers.openai.com/api/docs/models/gpt-oss-120b` (131,072 context), `https://developers.openai.com/api/docs/guides/token-counting` (local text counts vs API structure), and conversation-state guidance. Official Harmony article search was substantive but direct open failed; installed tokenizer source also confirms `o200k_harmony`.
- Earlier character-only full-name prototype was 419,542 serialized request characters, versus 944,798 for the old flat request. These are not token counts, and those prototypes do not establish byte fidelity. Do not present them as current measured tokens.
- Existing suite previously passed 43 offline tests, before current task source changes. Rerun after changes. Preserve unrelated dirty frontend changes and existing legacy deletions.

## Remaining work

1. Add a deterministic local preparation path using real backend machinery, without loading credentials or invoking providers. Preserve original bytes and hash, full cue content, names on each turn, timing, ordering, source mapping and explicit missing metadata.
2. Build and save one whole-week extraction request with a compact packet interpretation matched to the actual schema/prompt. Avoid claiming live pipeline integration if it is a separate preparation profile.
3. Tokenize actual rendered system/user text locally using cached `o200k_harmony`; report schema/formatting uncertainty separately from exact plain-text counts. Reserve completion/reasoning capacity and a labeled engineering margin. Do not count every HTTP envelope key as model-visible text.
4. Save immutable reusable raw/normalized/payload/request/token-report/provider-snapshot artifacts beneath `testing/.data/preparations/week1` with content-addressed IDs. No live model call.
5. Add offline tests, run the suite and execute actual Week 1 preparation. Verify all nine sources and 3,238 cues are included and source text fidelity passes.
6. Present measured counts, context fit, missing metadata and free-route availability separately. Explain whether testing is technically suitable vs currently runnable. Ask for model-route direction only for a subsequent live test, without auto-switching.
7. Update this checkpoint with final results and exact artifact paths. Address the response annotation in the final answer and cite primary model/token-count/provider sources.

## Related continuity files

- `2026-10-08-step1-transcript-compaction-reasoning.md`: prior step-1 reasoning and confirmed full-name / one-request / Zoom-to-Fathom decisions.
- `2026-10-08-backend-restructure-context.md`: backend layout and earlier prompt-ledger handoff.
- `2026-10-07-original-v1-prompt-texts.md`: archived prompt text.

## Completed work and final handoff state — 8 October 2026

The requested local preparation/token assessment is now complete. No provider, embedding, cloud token-count API, real `.env` or database service was invoked. No transcript was sent externally or truncated. Original input byte hashes remain unchanged.

### Implemented files and deliberate scope

- Added `backend/backend_pipeline/prepare.py`: standalone local weekly preparation and counting CLI. It reuses real backend prompts, schema, chat request builder and datastore, but intentionally does not call `Settings.from_env` or providers. Cached public tokenizer vocabulary is required; no automatic network download during private processing.
- Added `moment_extraction.compact.md`, a separately versioned packet interpretation supplement, and `compact_moment_prompt` in `prompts.py`. Existing v2 live prompt text and editorial policy are unchanged. Compact profile is `2026-10-08.weekly-compact-preparation.v1`; preparation version is `2026-10-08.lossless-weekly-preparation.v1`.
- Added immutable atomic byte/text writes to `JsonStore` and preparation tests. Strict UTF-8 decoding, full cue-body preservation after line-ending normalization, nonblank line accounting, untimed unknown content, reversible millisecond timing and full source names are covered.
- Updated `backend/prompts.md` with exact supplement/version/hash/timestamp provenance, `backend/README.md` with safe command/scope, and `to_be_asked_in_next_call.md` with U-13–U-15, D-14, I-10/I-11 and superseded batching proposals.
- Added thorough measured review at `research/week1-payload-token-readiness.md` and requested it be shown in Codex; tool returned queued, not proof that it is visibly open.
- Legacy live runner is NOT rewired to the compact profile. It still constructs the over-capacity flat packet and retains its 120,000-character guard. The user's task was local pre-LLM preparation; do not imply live testing is enabled.

### Actual Week 1 artifacts and counts

Artifact directory:
`testing/.data/preparations/week1/fbdd50910e4c2d8192a80a8c17419a17ff4b0a74c8bd0bccfcdb02dfdff5c1f5/`

Contains original source byte archives, complete normalized source records, source_packet TXT/JSON, messages/system.txt and user.txt, request.json, reference_map.json, integrity.json, provider_catalog_snapshot.json, token_report.json, report.md and independent_verification.json. Original creation was `2026-10-08T06:44:44.755088+00:00`. Identical reruns reused this directory rather than creating a new preparation or spending inference credits.

- Nine sources, 3,238 cues; all have source speaker names and all are included. No untimed records in this actual batch.
- Original raw bytes: 415,662. Normalized raw export characters: 404,167.
- Original WEBVTT export text, independently tokenized by file: 133,626 tokens. Removing only blank separator lines: also 133,626 tokens. Padding-only removal did not reduce local token total for this batch.
- Old flat v2 message text: 316,004 local tokens. New message text: 105,052, a 66.76% reduction achieved by representation changes, not dialogue deletion.
- Source packet: 102,314 tokens; full user message: 103,178; full system: 1,874. Schema proxy: 549. Input-with-schema proxy: 105,601.
- Reference context: 131,072. Proposed combined reasoning/final JSON reserve: 20,480. Provider-format uncertainty margin: 2,048. Budgeted total: 128,129; headroom: 2,943. This is a narrow conditional fit, not an exact hosted usage figure or guaranteed extraction success.
- Coverage-only empty-moment JSON with all 3,238 IDs: 8,729 tokens; selected reserve leaves 11,751 for reasoning and substantive records. No coverage-schema change has been made.
- With the same margin, reserves 16,384 / 20,480 fit with headroom 7,039 / 2,943. Reserves 24,576 / 32,768 do not fit (deficits 1,153 / 9,345).
- Exact serialized request: 363,290 characters. This exceeds the old character guard despite the narrow token fit. Do not just increase the guard on the old flat runner.
- Hosted provider exact tokens remain null. Local plain-text counts are exact for cached o200k_harmony strings; schema/framing behavior is a labeled uncertainty.

### Verification outcome

- Final suite: 62 offline tests passed (latest 7.09 seconds). First test attempt failed due to sandbox fixture temp-directory permissions; reruns used newly created workspace scratch directories and passed. Those test scratch outputs are synthetic, not real provider results; do not index them as historical angles.
- Changed-module Ruff lint and format checks passed; compilation succeeded.
- Independent actual-source audit verified unchanged original byte hashes, each cue body against original normalized source lines, every one of 3,238 compact rows' start/end via Decimal arithmetic, complete packet inclusion in request, and exact prompt-ledger supplement match. A first audit assumed no final template newline and failed; corrected audit accounts for the unchanged user template's one final newline and passed. This was a test-assumption correction, not transcript loss.
- Request artifacts are git-ignored. No files deleted or unrelated frontend/legacy changes altered.

### Remaining gates for a later live experiment

1. Resolve the approved free route's availability. Public catalog at `2026-10-08T06:33:40.8421181Z` did not advertise `openai/gpt-oss-120b:free`. Paid `openai/gpt-oss-120b` was listed; never auto-substitute it. No inference failure/permanent retirement/account state has been established.
2. Supply Zoom dates/day/timezones/source-confirmed names and verify batch membership. Folder label, filename order and elapsed cue timing are not calendar metadata. Fathom remains future production adapter work.
3. Explicitly wire compact references/text/raw-byte revisions into response validation, hydration, cache identity and a verified route-aware token preflight before live runner use.
4. Consider a deliberate coverage-contract revision because ID echo consumes output space; current schema is retained. No auto-split, summary, truncation or new LLM judge.
5. Actual GPT-OSS extraction recall/grounding/qualifications and Whitney-style usefulness still require an authorized evaluated model response. Preserve failures/usage before parsing; do not claim empty/partial results as a complete extraction.

Final response should lead with local preparation complete, give measured budget and narrow fit, explain lack of free-route/live readiness, link the exact request and detailed review, mention source fidelity/tests/no sends, and address the safeguard annotation with `:codex-annotation{index="1"}`. Skill influence: OpenAI Docs guided tokenizer/context accounting and provider-exact-count caveats. Primary references: OpenAI GPT-OSS model page, OpenAI token-count guidance, OpenRouter reasoning accounting and timestamped public model catalog.
