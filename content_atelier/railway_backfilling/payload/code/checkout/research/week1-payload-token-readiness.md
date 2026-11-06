# Week 1 payload, token budget and GPT-OSS testing readiness

Prepared: 8 October 2026. Exact artifact creation: 2026-10-08 06:44:44 UTC / 12:14:44 Asia/Calcutta. No LLM, embedding or cloud token-count request was made. This is a local capacity/fidelity assessment, not a model-quality evaluation or client approval.

## Outcome

All nine supplied Week 1 Zoom transcript exports have been prepared into **one complete weekly extraction request**, preserving all 3,238 timed turns and full speaker names. The source packet and actual rendered system/user messages are saved locally. Original inputs were not edited.

The new compact request has 105,052 locally counted message-text tokens. Counting its response schema as an additional 549-token proxy gives an input estimate of 105,601. It fits the GPT-OSS 120B reference context with a proposed 20,480-token combined completion/reasoning reserve and 2,048-token provider-format margin, leaving 2,943 tokens of headroom. This is a narrow fit, not generous long-context capacity.

**The approved free OpenRouter route is not cleared for a live test:** its exact ID was absent from the public model catalog inspected on 8 October. Zoom calendar metadata is also absent, and the existing live orchestrator has not been rewired to this compact preparation profile. These are separate gates; an input fitting a model's context does not settle route availability, meeting chronology or response quality.

## 1. Sources actually present

Input directory: `backend/zoom_backfill_meetings/week1/`. All nine TXT files contain WEBVTT exports. Their aggregate original size is 415,662 bytes. The original raw bytes are archived, including their line endings and any BOM. After decoding and line-ending normalization, the exports contain 404,167 characters.

| Ref | Filename label, not verified meeting identity/date | Timed turns | Isolated compact packet tokens |
|---|---|---:|---:|
| m1 | Carmen Cruickshank personal room, `(1)` | 192 | 5,955 |
| m2 | Carmen Cruickshank personal room, `(2)` | 260 | 7,003 |
| m3 | Carmen Cruickshank personal room, `(3)` | 397 | 12,053 |
| m4 | Carmen Cruickshank personal room, `(4)` | 586 | 16,872 |
| m5 | Carmen Cruickshank personal room, no suffix | 709 | 18,302 |
| m6 | Check-in with Gisselle | 283 | 8,282 |
| m7 | LeadLock Sequence Refresh | 247 | 11,032 |
| m8 | Messaging & Positioning / The Penny | 308 | 13,331 |
| m9 | Whitney Hodges personal room | 256 | 9,476 |

The whole packet is measured directly at 102,314 tokens, not inferred from a sum of separately tokenized fragments. All 3,238 source cues are included. There are no additional untimed records in this actual batch.

The user described a June 2026 starting week. The files themselves do not establish calendar dates, day, timezone, Zoom meeting IDs or source-confirmed titles. No corresponding metadata export was present. The packet therefore carries null date/day/timezone/name and an explicitly unverified filename label. Sorting filenames gives deterministic packet assembly, **not** meeting-date order. Original turn order and overlaps within each meeting are preserved. The folder is treated as the supplied testing batch, not proof that its dates satisfy the weekly cutoff.

## 2. What compaction changed, and what it did not

Compaction is deterministic representation work, not an LLM summary or editorial filter. It removes export padding and avoids repeating long source/span identifiers and JSON field names beside every turn. A meeting header carries its metadata once. Every cue retains its entire original body, including its full source speaker prefix and dialogue. The model receives greetings, endings, fillers, repetition, uncertainty, punctuation and surrounding conversational material, even when they will not become shortlisted moments.

A normal row is `ref|start+duration|exact cue body`. Synthetic format illustration, not evidence from this week:

```text
MEETING {"source_id":"m1","filename_label":"Example only","name":null,"date":null,"weekday":null,"timezone":null,"status":"zoom_metadata_not_supplied"}
1|16+2|Whitney Hodges: Hi, everyone.
2|17.125+3.375|Another Full Name: Thanks!
END_MEETING m1
```

These are decimal-string source refs, not speaker aliases. Seconds preserve supplied millisecond precision; end is exactly start plus duration. They are elapsed recording times, not calendar times. Original timecode strings, end times, full text, full speaker labels, source line numbers, source IDs and raw-byte revision hashes stay in the JSON source/reference map. Short refs are scoped to the immutable prepared request and must never be treated as globally permanent evidence IDs.

Cue bodies are not stripped, rewritten, deduplicated, stitched or paraphrased. Internal line breaks and meaningful whitespace remain after CRLF/CR-to-LF normalization. Blank separator lines and the standalone WEBVTT header are recorded as export structure rather than conversation. Numeric cue identifiers are retained in the local source map. Unknown non-cue blocks are retained in the model packet as untimed content. Invalid UTF-8 or invalid/unparseable cue times fail rather than substituting characters or fabricated zero timestamps. Fathom production ingestion will need its own source adapter to the same evidence contract; this preparation command does not pretend to implement it already.

The compact interpretation supplement explains the new packet format, unknown metadata, exact-quote rules, per-meeting context and short-ID coverage. The existing corpus-grounded evidence-editor system prompt, Whitney policy, moment user instructions and nested response schema are otherwise unchanged. The prompt ledger stores the supplement and its separate version. This avoids measuring a packet against instructions that still assume flat JSON span objects.

## 3. Why deleting blank lines is not enough

Actual local comparisons for this batch:

| Representation | Local text tokens | Interpretation |
|---|---:|---|
| Original normalized WEBVTT exports, tokenized separately | 133,626 | Already exceeds the reference context before adding prompts/schema/output |
| Same exports with only blank separator lines removed, separately tokenized | 133,626 | Fewer characters, no token reduction in this particular measurement |
| Existing flat v2 system + user messages | 316,004 | Repeated field labels, long IDs and metadata impose substantial overhead |
| New compact system + user messages | 105,052 | Same source dialogue; structural/reference representation changed |

The 66.76% reduction compares actual message text before/after, not characters or billable usage. It is not achieved by removing 66.76% of the conversation. In the new packet, tokenizing each full cue body in isolation totals 78,544 tokens; these bodies include the names. The remaining packet cost is primarily refs, timing and meeting structure. Segment token totals are diagnostics, not exact additive billing quantities.

This illustrates the distinction that prompted this task: character count is a poor basis for deciding whether the request fits. In this corpus, removing visually large amounts of paragraph padding saves no local tokens because the tokenizer represents the relevant newline runs efficiently. Repeated long identifiers, punctuation and field structure matter much more. There is no fixed characters-per-token ratio being assumed.

## 4. Token-count methodology and uncertainty

The measurement runs entirely locally with installed `tiktoken==0.12.0`, encoding `o200k_harmony`. Its public vocabulary is cached beneath `testing/.data/tokenizers` and SHA256-verified as `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`. Source strings resembling model special tokens are encoded as ordinary text, not injected as message boundaries. No transcript was uploaded for counting.

The actual rendered system and user message contents are counted separately. The minified nested response-schema text is counted as an additional proxy. Model ID, temperature, HTTP envelope keys, local file paths not in the prompts, API headers and credentials are not blindly counted as model input. The serialized HTTP request's 363,290 characters are a separate diagnostic, not the token count.

Local text counts are exact for the chosen tokenizer and strings; **the effective hosted-provider input count is not known exactly**. Its chat framing, schema rendering, constrained-generation implementation or tokenizer/template revision can change the final input. The report therefore leaves `hosted_provider_exact_input_tokens` null, rather than claiming an exact OpenRouter usage figure. The additional 2,048 tokens are an explicit engineering margin, not measured provider overhead or a mathematical upper bound. OpenAI likewise distinguishes plain-text local tokenization from schema/API-level accounting. [OpenAI token-count guidance](https://developers.openai.com/api/docs/guides/token-counting)

OpenAI lists a 131,072-token context for GPT-OSS 120B. This is the reference model capacity, not confirmation that every hosted variant accepts that full input or this exact schema. [GPT-OSS 120B model reference](https://developers.openai.com/api/docs/models/gpt-oss-120b)

## 5. Full input/output budget

| Component | Tokens | Measurement status |
|---|---:|---|
| Source packet within user message | 102,314 | Local tokenizer count; included below, not added twice |
| Full user message | 103,178 | Local tokenizer count |
| Full system message + shared policy + format supplement | 1,874 | Local tokenizer count |
| System + user text | 105,052 | Exact sum of those local message counts |
| Response schema | 549 | Local schema-text count used as a hosted-format proxy |
| Input proxy | 105,601 | Messages + schema proxy |
| Provider-format/schema uncertainty margin | 2,048 | Proposed engineering allowance |
| Combined reasoning + final JSON reserve | 20,480 | Proposed experiment setting, recorded as `max_tokens` |
| Total budgeted | 128,129 | Below the reference capacity |
| Remaining headroom | 2,943 | Narrow, conditional fit |

The arithmetic is `105601 + 2048 + 20480 = 128129`, leaving `131072 - 128129 = 2943`. Reserving final-output capacity is essential. OpenRouter documents that reasoning and visible output share the completion limit on most providers, and that hiding reasoning does not remove its budget cost. The actual selected route's accounting still needs verification. [OpenRouter reasoning accounting](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)

| Combined completion reserve | Headroom after same input/margin | Fits reference context? |
|---:|---:|---|
| 16,384 | 7,039 | Yes, but less room for useful output |
| 20,480 | 2,943 | Yes, narrowly |
| 24,576 | -1,153 | No |
| 32,768 | -9,345 | No |

This is not an assertion that 20,480 completion tokens will be sufficient. The current schema asks the model to return every reviewed turn ID in `processed_span_ids`. Even the minified JSON object with **zero moments**, all 3,238 refs and no notes uses 8,729 tokens. The proposed reserve leaves at most 11,751 additional local-token equivalents for reasoning, moment records, quotes, context references, qualifications and coverage notes. Actual JSON whitespace or provider accounting can change that figure. Rich extraction may run out of output budget even though the input is accepted.

That coverage contract is retained, not silently weakened. It is expensive, and the future design should explicitly consider a compact per-meeting coverage acknowledgement while the backend deterministically verifies packet completeness. Such a change would require a deliberate prompt/schema/validator revision. A model echoing every ID does not prove it understood every turn. No such contract change or extra extraction call has been made here.

## 6. Model availability is a different question

A credential-free GET of the [OpenRouter public model catalog](https://openrouter.ai/api/v1/models) at `2026-10-08T06:33:40.8421181Z` returned 467 models. The exact approved ID `openai/gpt-oss-120b:free` was absent. The paid ID `openai/gpt-oss-120b` was present with 131,072 context tokens and a top-provider maximum completion of 117,964; that output maximum does not override the combined context budget for this long input. Only the relevant catalog entries and inspection timestamp are retained, without account keys.

Catalog absence is not proof of permanent retirement, authenticated account status or a failed inference request. It is enough that the approved free route cannot currently be represented as verified available. The paid route's metadata does not establish a free route's capabilities. No alternate free router, other model or paid route was substituted. If the exact free route becomes available, inspect its providers and schema/reasoning/context support before using the payload; if it does not, choosing another route needs the user's direction.

## 7. Artifacts and reuse

Preparation directory, relative to the project:

```text
testing/.data/preparations/week1/fbdd50910e4c2d8192a80a8c17419a17ff4b0a74c8bd0bccfcdb02dfdff5c1f5/
  manifest.json                         Immutable identity, status and source revisions
  raw/m1.original ... m9.original        Exact source bytes
  sources/m1.json ... m9.json            Full normalized records and source line accounting
  source_packet.txt                     Complete compact whole-week evidence packet
  source_packet.json                    Same packet in a JSON wrapper
  messages/system.txt, user.txt          Exact rendered model-message text
  request.json                          Single extraction request; not sent
  reference_map.json                    Short refs → source/time/name/text/revision records
  integrity.json                        Source fidelity and zero-request checks
  provider_catalog_snapshot.json        Timestamped, non-authenticated route evidence
  token_report.json, report.md           Measured counts, assumptions and readiness flags
```

The fingerprint covers original source records/bytes, actual rendered request/settings, preparation version, tokenizer vocabulary, context/margin settings and the supplied provider snapshot. Identical preparations reuse the same immutable directory. Changes retain a new directory without replacing historical sources or paid results. Re-preparing does not incur inference/embedding cost. These files are a preparation ledger, not fake model output, approved angles or validated inference-cache entries. Runtime `.data` remains git-ignored; local storage still needs appropriate access controls and backups.

## 8. Implemented scope and verification

Added `backend_pipeline.prepare`, compact Call 1 rendering/supplement and atomic immutable byte/text archive support. It reuses the real backend's trusted prompts, schema, request builder and datastore. It does not read `.env`, contact a provider, start PostgreSQL, extract key moments or generate angles. The old live pipeline still constructs its original flat packet, so passing `run --mode live` would **not** automatically use this saved request or source map.

The 120,000-character guard remains untouched. This prepared request is 363,290 serialized characters, so the legacy character guard would reject it if passed through that path. That is evidence of the guard's mismatch with the token budget, not a reason to disable it blindly. Its removal/replacement must accompany wiring the correct compact input, evidence/quote hydration, prompt/cache identity and verified model/route limits. Existing flat input remains over capacity independently of the guard.

Verification completed: all 62 offline tests passed after moving pytest's temporary fixtures to a newly created workspace-owned scratch directory; the first attempt encountered sandbox temporary-directory permissions, not a source-code failure. Ruff checks passed for the changed modules. Tests cover full names, greetings/endings, multiline spacing, overlaps, untimed notes, strict encoding/timing failure, untrusted placeholder text, one complete weekly request, immutable reuse and no inference/embedding call. Actual Week 1 artifacts independently verify raw archive SHA256 and full nonblank-line accounting. Software tests establish the implementation contract, not GPT-OSS's extraction quality.

## 9. Decision and next test gates

GPT-OSS 120B is **technically plausible for a carefully bounded Week 1 experiment with this compact representation**, but not presently cleared as an available, reliable free test route. Input fit is demonstrated locally with limited completion space; semantic recall, qualifier retention, groundedness and actual provider behavior are untested.

Before a live experiment:

1. Supply Zoom meeting metadata to resolve actual dates/day/timezones/names and verify this supplied batch's weekly membership. Do not fabricate it from filenames.
2. Resolve an available authorized route, including transcript privacy, strict schema support, reasoning controls and effective context. Do not default to the paid GPT-OSS listing.
3. Deliberately integrate compact source refs/text and raw-byte revisions into response validators, evidence hydration, cache identity and token preflight. Do not just raise the character cap on the old runner.
4. Agree whether to keep the costly 3,238-ID acknowledgement or explicitly revise its contract. Do not split the user's single weekly extraction request to avoid the budget issue.
5. Save any authorized provider response immediately, including truncation/refusal/error and usage. Reject incomplete JSON as incomplete, never silently call it a complete week's extraction. Reuse compatible successful outputs; do not automatically make another paid request.
6. Evaluate Call 1 against manually reviewed substantive passages, including corrections and qualifications across the beginning/middle/end and all meetings. Only then pass validated moments and hydrated context to Call 2 and evaluate distinct, grounded angles. Fit alone is not evidence of Whitney-style usefulness or comprehensive recall.

No choice is needed to inspect the completed local payload. A route decision and metadata are needed before calling the live test ready.
