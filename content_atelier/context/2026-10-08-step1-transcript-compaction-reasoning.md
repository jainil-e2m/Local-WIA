# Step 1 clarification — complete compact transcripts and grounded moments

Recorded 8 October 2026, Asia/Calcutta. Status: reasoning/proposal only; no runtime implementation or prompt changes. This checkpoint preserves the current request and findings under the user's context-recording instruction. It records evidence and design conclusions, not private internal reasoning.

## User request, verbatim

> for the step 1: ingest and normalise transcripts what i was thinking is that in the normalizing step what we do is remove the unnecessary padding , say between the 1st paragraph and 2nd, and so on other items where we can save from adding unnecessary tokens without disturbing or making any changes to the actual transcript. what i want is that a compacted transcript is sent over to the llm alongside the reference of the speaker, time, meeting date / day & name. I dont want to lose any other context say the greetings, ending, etc, nothing as such of the actual text to be lost. from this compacted transcripts a single payload alonsgside the system & / user prompt the llm identifies the key moments according to our thoroughly reasoned understanding of what stand out as key moment. The llm returns the key moments alongside the timestamp & speaker and the exact dialogue. the key moment could be condensation of the conversation dialogues that took place that resulted in the key moment.
>
> Thoroughly reason this and then i will move to the other 3 steps.

## Inherited context

The implemented package is `../backend/backend_pipeline/`; the template inventory is `../backend/prompts.md`. Current prompt profile is `2026-10-07.gpt-oss-120b.transcript-angle.v2`. The last verified suite had 43 passing offline tests. JSON artifacts remain at `../testing/.data/`; supplied week folders remain under `../backend/zoom_backfill_meetings/`. Both LLM stages retain the approved GPT-OSS 120B Free model. There is no third LLM similarity judge, no four-angle visibility cap and no implemented brief/content-pack generation. Earlier durable context is in `2026-10-08-backend-restructure-context.md`, the previous checkpoints, and linked research/design documents.

## Interpretation and proposed contract

Normalisation is deterministic, zero-LLM, representation-only compaction, not a summary or an editorial filter. Preserve all dialogue, including greetings, closing remarks, fillers, repetition, uncertainty, corrections, interruptions and transcript annotations. Preserve turn boundaries, source order, speaker labels, elapsed timestamps and meeting boundaries. Original bytes remain the evidence authority; a versioned map links compact aliases to original turns and exact source revisions. Safe formatting changes do not justify global whitespace replacement inside speech, grammar correction, deduplication or invented missing text/times.

A compact envelope can put meeting metadata once per meeting and a speaker dictionary once per meeting, then use short local turn references. A declared positional row format is a proposal to measure/evaluate, not automatically better than a readable keyed format. Full IDs and source hashes remain in local provenance rather than being repeated for every dialogue turn. Unknown metadata is explicit null/unknown, not invented by the model. Date/day/name must come from verified source metadata or a user-provided manifest. Week numbers, filesystem timestamps and generic personal-meeting-room filenames are not reliable meeting dates or complete identities. Calendar day can be derived deterministically from a known meeting-local date. Elapsed recording times are not clock times.

Preferred interpretation of “single payload” is the complete selected weekly meeting set, with distinct meeting boundaries, in one extraction request if it fits. Exactly one physical weekly request versus one complete request per meeting is an open clarification, not permission to change the user's call-count preference. Do not silently truncate, summarise, skip greetings, raise limits or add physical requests if the complete payload does not fit the approved budget.

Call 1 receives complete compact source data plus trusted editorial/extraction instructions and a structured output contract. It selects meaningful supported decision/mechanism/tension/objection/result passages using the corpus-derived understanding of Whitney as a strategic thinker serving capable wedding-business owners. Source qualifications, chronology, attribution/cost bases, proposals versus measured results and ownership remain material. The policy is a lens, not current-week evidence. All input dialogue remains available even though the output is a shortlist.

Each moment separates a model-written condensation/interpretation from verbatim source dialogue. A conversation-level insight can involve multiple turns and speakers; it must not become a fabricated composite quote attributed to one person. Return source/turn references, selected evidence and sufficient setup/correction/context, a bounded summary and proposition, relevance/reasons/strength, claim status and qualifications/handling concerns. The backend resolves original dialogue and metadata and validates any model-returned text/time/speaker against those records. The authoritative displayed evidence must be reconstructed from source, not accepted as freshly generated speech. Context selection is meaning-based, not a fixed seconds window. Source-locator validity and structured JSON do not prove semantic interpretation or permission.

## Current-code findings

- `ingest.py` trims cue lines and joins them with spaces; its plain-text fallback flattens the whole file into one span with zero timestamps. This is not a fully verified fidelity contract for arbitrary transcripts. Decoder replacement, mixed-format handling and preservation of structural text need tests before claiming nothing is lost.
- `models.py` has speaker and elapsed-time span fields but no explicit meeting name/date/day metadata.
- `pipeline.load_week()` sends a flat list with repeated long IDs/source metadata for every turn, not a meeting-grouped compact packet.
- Moment records currently hold one literal anchor quote plus source/context references and interpretation. Call 2 rehydrates context, but an explicit fully hydrated multi-speaker moment evidence view is still a proposed amendment.
- No runtime source, output schema, prompt, version or stored cache was changed by this reasoning turn. These findings do not revoke the previously passing tests; those tests do not establish the newly requested complete-fidelity behavior.

## Read-only Week 1 measurements

PowerShell counted approximately 413,899 raw-export characters across 9 files and 400,911 after removing blank lines: about 3.1% smaller. That was a size-only diagnostic, not an approved normalisation transformation. PowerShell counts its string characters; these are not model tokens.

A Python diagnostic reused the existing parser and compared JSON representations without writing files or calling providers. It included all 3,238 currently parsed turns and 245,115 dialogue characters. Dates/day/timezone were null; names came from filenames and were labelled accordingly. Counts below use Python string characters, not a verified model tokenizer:

| Representation | Current | Compact prototype |
|---|---:|---:|
| Source packet | 858,430 | 343,063 |
| System + user messages | 870,794 | 355,427 |
| Serialized request including schema/settings | 944,798 | 377,899 |

The prototype's approximately 60% request-character reduction comes largely from reducing repeated metadata and verbose references. It preserves text from current parsed spans, not proof that the current parser captured every original byte/dialogue. Its existing prompt was not adapted to the new packet shape, so this is not a runnable release or actual provider compatibility result. The default live safeguard is 120,000 serialized-request characters; the prototype still exceeds it. Actual selected-route token capacity, output/reasoning reserve, coverage output and moment evidence volume need measurement before promising one complete weekly request.

## Documentation influence and boundaries

The OpenAI Docs skill was used for input/output design. Official prompt-engineering guidance supports clear boundaries between task instructions and source data and planning for finite context. Structured-output guidance explicitly notes that valid structured responses can still contain mistakes or be incomplete. These principles support local source validation; they do not establish actual OpenRouter free-route limits or prove model fidelity. The approved model was not replaced. No credentials were read, private transcripts uploaded, inference/embedding requests made, services started or backend code edited.

Sources consulted: https://developers.openai.com/api/docs/guides/prompt-engineering and https://developers.openai.com/api/docs/guides/structured-outputs. Local evidence includes the existing parser/contracts/orchestrator, the Founder Voice Guide, selected transcript headers and the previous corpus-grounded prompt review.

## Clarifications to carry forward

1. Does “single payload” require one physical extraction request for the whole week, or mean one complete payload per meeting? The design currently prefers the complete weekly set when safely feasible; no automatic batching decision is assumed.
2. How will authoritative meeting date/name/timezone metadata be supplied: Zoom metadata or a per-week manifest? Current inspected exports expose elapsed cue times and speaker labels, but do not provide sufficient date metadata to assert the required meeting calendar dates.

The next response should explain the proposal and trade-offs thoroughly, separate exact dialogue from condensation, identify the implementation gaps and ask these limited clarifications. The user intends to discuss the remaining stages afterwards; do not implement them or revise current prompts prematurely.

## Subsequent confirmed decisions — 8 October 2026

User selected the earlier proposal “speaker names once rather than repeating them beside every turn” and corrected it: “keep the speaker name in their turns as well since rather than s1, s2 even the names would contain almost similar amount of tokens.” Full source speaker names must remain on every turn; the proposed s1/s2 aliases are superseded. Token costs vary with names/tokenizer; comparable token costs were not assumed or verified. Short meeting/turn references and removal of repeated non-dialogue metadata remain possible without replacing speaker names.

User asked “WHAT IS THIS?” about the 120,000-character safeguard. Read-only code inspection confirmed it is an engineering safeguard introduced by the assistant, not a model context limit, provider policy or user requirement. `Settings.max_llm_request_characters` defaults to 120000; the environment mapping is `CONTENT_ATELIER_MAX_LLM_REQUEST_CHARACTERS`. `_call_json` counts `len(json.dumps(request, ensure_ascii=False))`, including serialized messages/schema/settings, after checking compatible cached artifacts. An oversized uncached live request is recorded as failed and stops before a provider call. It does not truncate the transcript. Its current error message proposes batching; that recommendation is not compatible with the newly confirmed one-request requirement and must be revised when implementation is authorised. The guard is still present; no code or configuration was changed in this reasoning turn.

User confirmed: “a Single payload means one physical extraction request containing the whole week.” This is now a firm design requirement for Call 1, not one request per meeting and not automatic extraction batches. There is no LLM preprocessing/summary call. The complete weekly dialogue and metadata, with trusted instructions/schema, go into one extraction request on a fresh successful run. A compatible cached result may require zero new inference. Over-budget or incomplete-output conditions must be reported rather than silently deleting text, splitting the request or changing the model. One physical request cannot be promised for unbounded input independent of provider/model capacity; token-aware feasibility must be validated for the actual complete week and adequate output reserve.

User confirmed: “It will be through zoom metadata for the backfilling and once in production, it will be actually fathom transcripts and no more zoom transcripts.” Historical input is Zoom transcript plus corresponding Zoom metadata. Production input is full Fathom transcript plus corresponding source metadata, not a meeting summary. Distinct provider importers should produce a common meeting/turn evidence contract while preserving raw originals, provider IDs, source revisions, meeting title/date/timezone and full source speaker labels. Calendar day is derived from an established meeting-local date; elapsed transcript times are not wall-clock times. Missing names/times/metadata stay explicit rather than being invented. These decisions settle the two previous clarification questions; actual metadata matching/access and adapter implementation still need validation.

### Updated size diagnostic with speaker names retained

A read-only Python comparison reused all 3,238 existing parsed turns from nine Week 1 files. Every proposed row's speaker, dialogue and elapsed start/end matched its parsed source span. Dates/day/timezones remain null because Zoom metadata has not yet been loaded. Names were marked as filename-derived, not validated metadata. No provider was contacted and no file was written by the diagnostic.

- Existing serialized request: 944,798 characters.
- Proposed compact packet with full speaker names: 384,820 characters.
- Proposed serialized request with full speaker names: 419,542 characters.
- Request-character reduction: 55.59%.
- Actual GPT-OSS token count: not measured.

This supersedes the alias-based prototype size as the candidate representation consistent with the user's preference. It is still only a size/fidelity-to-current-parsed-spans diagnostic: it does not prove complete original parsing or update the runtime prompt to understand the new packet.

### Official documentation verification

OpenAI Docs was used to distinguish the local character gate from the model's token budget. The fetched official GPT-OSS 120B model page lists a 131,072-token context window: https://developers.openai.com/api/docs/models/gpt-oss-120b . Official context guidance describes budgeting input, output and applicable reasoning tokens: https://developers.openai.com/api/docs/guides/conversation-state . Those model-level facts do not establish the configured OpenRouter free provider's actual maximum output, accounting or availability. No universal characters-per-token conversion, model switch, paid route or exact count was inferred.

The proposed replacement is a model/route-aware local token preflight over actual messages and applicable schema/template overhead, plus an explicit completion/reasoning reserve and route output checks. Exact accounting must avoid double-counting reasoning if it is already included in a provider's total completion budget. The 120,000-character constant is not the final product contract. Further implementation remains gated on the user's next instruction; current prompts/version/cache and runtime guard are unchanged.
