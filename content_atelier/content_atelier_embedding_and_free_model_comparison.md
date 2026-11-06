# Content Atelier — Small embeddings and free-model testing

<!-- governing-plan-note -->
> **Historical (marked 18 October 2026, plan item S.B9).** This document is kept for traceability. The one governing plan is [the implementation plan](backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md) (revision 6.1 or later); where they differ, the plan wins. Do not plan from this document.

Prepared: 7 October 2026. Status: researched recommendations and input contract, not an implementation or a completed model evaluation.

## 1. Recommendation and decision status

Start the first chronological experiment with **OpenAI `text-embedding-3-small`, 1,536 dimensions, one canonical argument vector per angle**. This replaces the earlier proposed Large-at-1,536 starting profile; the user's inclination towards Small is recorded, but final model approval is still open.

For the two LLM stages, first evaluate **`openai/gpt-oss-120b:free` for both key-moment/context extraction and grounded angle generation**. Then compare a smaller extraction challenger while holding the angle-generation model fixed. These are task-fit hypotheses, not evidence that a model already matches Whitney's taste. Real transcripts require an approved provider/data route before any call.

The final visible set remains deterministic: exact cosine comparisons, historical recency penalties, current-candidate overlap rules and the adjusted-score threshold. A free model does not create permission to add a third LLM similarity judge or final rewriting stage.

The user will supply roughly three months of past meeting transcripts in `week1`, `week2`, etc., beginning in June 2026. We will work through them in chronological weekly increments. Exact first/last dates and the actual number of windows remain to be established; this does not silently mean exactly twelve weeks or June–August.

## 2. Small versus Large: size, cost and local efficiency

Prices below are standard OpenAI embedding input-token prices checked on the preparation date, in USD. They exclude LLM generation, retries, taxes and infrastructure. [Small model documentation][small] [Large model documentation][large]

| Profile | Dimensions | USD / million input tokens | pgvector bytes / vector | Practical role |
|---|---:|---:|---:|---|
| Small, default | 1,536 | 0.02 | 6,152 ≈ 6.01 KiB | Recommended first baseline |
| Large, default | 3,072 | 0.13 | 12,296 ≈ 12.01 KiB | Later quality comparison if justified |
| Large, shortened | 1,536 | 0.13 | 6,152 ≈ 6.01 KiB | Compare model quality at the same storage dimension |

Both models support the `dimensions` parameter. Shortening Large changes its output length, not its advertised input-token price. Equal output lengths do not make Small and Large compatible embedding spaces. [OpenAI embedding guide][embedding-guide]

For pgvector's ordinary single-precision `vector` type, storage is `4 * dimensions + 8` bytes. At 10,000 angles, the vectors alone occupy approximately 58.67 MiB at 1,536 dimensions versus 117.26 MiB at 3,072. This excludes row overhead, metadata, indexes and JSON copies; serialized JSON vectors may occupy substantially more than binary pgvector values. [Official pgvector storage documentation][pgvector]

The efficiency conclusions are deliberately narrow:

- Small costs **6.5 times less** than Large for identical input-token volume, an approximately 84.6% lower embedding inference bill.
- Default Small has half the floating-point components of default Large. Exact cosine work scales approximately with `eligible_angle_count * dimensions`, so component work and vector payload are roughly halved. This is not a measured promise of twice the end-to-end speed.
- Small/1,536 and Large/1,536 have the same vector size and dimension-related comparison work. Large is not inherently more expensive to store when shortened to the same size.
- Hosted embedding latency also depends on batching, network and provider load; no latency benchmark has been run here.
- At this initial three-month scale, source processing, grounding quality and human review are likely more consequential than vector storage. Measure actual candidate counts before introducing approximate indexes or aggressively shortening Small.

Ordinary `vector` HNSW/IVFFlat indexes support up to 2,000 dimensions. That is an index limit, not a ban on storing or exactly querying a 3,072-dimensional vector. Start with exact scans for full threshold coverage; no approximate-index workaround is needed for the recommended Small profile. [pgvector index limits][pgvector]

### 2.1 A concrete cost example

If 1,000 generated angle signatures average 300 input tokens each, the embedding input is 300,000 tokens:

- Small: `300,000 / 1,000,000 * 0.02 = USD 0.006`.
- Large: `300,000 / 1,000,000 * 0.13 = USD 0.039`.
- Difference: USD 0.033 for that invented example, not a quote for the supplied meetings.

An exact compatible artifact replay has zero new embedding inference cost. Rebuilding pgvector from saved vectors also has no new embedding inference charge. A changed embedding model, dimensions or canonical signature can require new embeddings; repeated threshold experiments should not.

We are embedding **angle signatures**, not every raw transcript as a prerequisite. Stage 1 must read all admitted transcript intervals to identify moments; top-k transcript-vector search is not a substitute for that coverage. Historical source-chunk embeddings can be added later for the separate evidence-retrieval purpose.

### 2.2 What quality can and cannot be inferred

OpenAI reports broader embedding benchmark results in which Large performs better than Small. That does not establish the result for Whitney's argument-level repetition test, especially when Large is shortened. The decision must be based on our labelled angle pairs, not the word “Large.” [OpenAI benchmark comparison][embedding-guide]

Keep Small at its default 1,536 dimensions initially. Test whether it correctly separates:

1. The same argument in different wording.
2. The same wedding-business topic with a genuinely different reader contribution.
3. Closely related arguments with different mechanisms, objections or recommendations.
4. Unrelated arguments sharing common industry vocabulary.

Do not copy an earlier illustrative cosine cutoff into this profile and call it calibrated. A cosine of 0.9 is not a 90% probability of duplication. Fix the canonical signature and label pairs before choosing match/close thresholds; inspect false suppression and missed repetition as distinct errors.

If a later Large comparison is authorised, use an isolated profile/projection and the same pair labels. Do not place Small and Large vectors together merely because both have length 1,536, and do not keep multiple simultaneously searchable vectors for one angle. Preserve previous responses as versioned audit artifacts while choosing one active representation.

## 3. Free OpenRouter shortlist for the two stages

These exact `:free` IDs were listed with zero prompt/completion token prices when checked. Catalogue listing is not a verified successful request from this account, a service guarantee, or a privacy approval. Context limits below refer to the inspected free endpoint, not a paid sibling or advertised underlying training capability.

| Listed free endpoint | Listed context | Proposed experiment role | Main test |
|---|---:|---|---|
| [openai/gpt-oss-120b:free][oss120] | 131,072 | First reference for both stages; prioritise it for Stage 2 | Source-faithful synthesis, distinct useful arguments and JSON validity |
| [openai/gpt-oss-20b:free][oss20] | 131,072 | Smaller Stage 1 challenger | Moment recall, speaker attribution and preserved qualifications |
| [nvidia/nemotron-3.5-lightning:free][lightning] | About 1M | Throughput-oriented Stage 1 challenger on suitable non-confidential data only | Complete transcript coverage without thin/generalized summaries |
| [nvidia/nemotron-3-super-120b-a12b:free][super] | 262,144 | Stage 2 challenger on suitable non-confidential data only | Cross-moment argument synthesis without invented proof |
| [qwen/qwen3.8-27b:free][qwen27] | 262,144 | Alternative family for either stage | Grounding, specificity, structure and human editing effort |

“Smaller” or a throughput-oriented architecture does not guarantee a faster free hosted response. Measure successful stage latency, retries and quality on the actual route. A million-token advertised window is not a reason to put three months into one prompt; coverage and output limits still matter.

### 3.1 Why these stage choices

Stage 1 is an **evidence selection** task, not a general meeting summary. It must preserve exact source IDs, quoted spans, speaker attribution, objections, qualifiers and the surrounding explanation. A missed strong moment cannot be recovered by eloquent angle copy in Stage 2. Test smaller models on extraction, but reject them if their apparent efficiency comes from leaving relevant intervals out.

Stage 2 is an **argument construction** task. It must explain a specific reader problem, a grounded position/mechanism, an actionable implication and why that contribution differs from other candidates. It should return as many substantive grounded angles as the evidence supports, without padding, hook variations masquerading as distinct angles, or a four-item cap. The GPT-OSS 120B choice is a reasonable first hypothesis for this more synthesis-heavy responsibility, not a measured ranking over Nemotron or Qwen.

The June 2026 dates do not require these models to have pretrained knowledge of the meetings. The provided transcript is the evidence. Do not use model memory to invent current ad-platform rules, results, offers or facts missing from that evidence.

Two logical stages may need bounded physical batches. Preserve coverage and shared source IDs, account for overlapping windows, and avoid silently treating a truncated output as a complete week's extraction/generation. Free does not mean unlimited context/output or unlimited retries.

## 4. The privacy gate comes before the free-price decision

**The inspected NVIDIA free endpoints explicitly prohibit confidential information or personal data and disclose logging for security/product improvement. Raw WIA/client meeting transcripts must not be routed there by default.** Both the Lightning and Super pages carry that notice. [Lightning endpoint notice][lightning] [Super endpoint notice][super]

Suitable tests for those endpoints are synthetic fixtures or source material verified to be non-confidential and permitted. Removing names alone does not remove client strategy, identifying stories, financial figures or restricted business information. Angle/context packets can also disclose confidential substance even if the raw transcript is not sent.

For GPT-OSS and Qwen, absence of the same banner is **not** proof of privacy suitability. Check the actual serving provider's retention/training policies, endpoint terms and client processing authority. Local pgvector and local artifact storage do not make a hosted LLM or OpenAI embedding request local.

OpenRouter's current Free plan lists 50 requests/day, no contractual SLA and no data-policy-based routing. Therefore this design must not promise that a required provider/privacy constraint can be enforced on a purely free account. Verify the available account/endpoint capabilities; if they cannot meet the requirement, stop rather than relax privacy or silently upgrade. [OpenRouter current plans][plans]

Open-weight models can be self-hosted instead, but that requires appropriate hardware and has operational costs. Nothing here authorises a local-model installation, cloud GPU spend, account upgrade or private source transmission.

## 5. Free calls still need durable preservation

Retain the same request/response/validation/provenance artifacts for free calls as for paid calls. Saving them avoids quota consumption, disappearing endpoints and uncontrolled resampling as well as paid inference. Local artifact reuse is separate from provider prompt caching and works without a new request.

The planned common attempt area is now `testing/.data/service_calls/`, replacing the earlier proposed `paid_calls/` label before any runtime data exists. Each attempt records `service_tier`, requested/returned model/provider, price snapshot, usage when reported, validation, source dependencies, request/response hashes and actual execution time. Cost reports can still distinguish paid attempts from free attempts. `testing/.data/ledgers/service-attempts.jsonl` is the proposed shared ledger; no actual records are fabricated here.

Use exact model IDs, no paid model fallback, and no automatic model substitution when a free endpoint is unavailable. A retry or local replay is not a new generation event. A genuinely new model sample is a new attempt/run with recorded lineage; it must not overwrite the first response.

Before testing, check current account quota and endpoint schema support; OpenRouter documents `free_model_daily_requests` in its key-information response. Do not read or expose credentials in documentation. Back off on rate limits, preserve incomplete states, and resume from checkpoints. A failed request must not be treated as complete coverage. [OpenRouter limits and account counters][limits]

LLM stages on free endpoints can have zero listed token charges while Small embeddings still incur their small API charge. Preserve both types under one pipeline lineage. No inference requests of either kind were made during this research.

## 6. The supplied week folders and chronology

Read-only folder inventory during this review found `backend/zoom_backfill_meetings/week1/` and `week2/`. Their contents, source coverage and dates were not inspected or ingested. Prefer reusing the user's existing source location through a configurable input root; no move or backend-code restoration is needed. Git status shows the backfill area as untracked, so it is not fully excluded by current ignore rules. Before committing, explicitly protect that chosen input root; no ignore-rule edit or source move was made in this reasoning turn.

Alternatively, the following already-ignored input convention can be used if the user chooses it. It is a recommendation, not a request to relocate existing files:

```text
content_atelier/
  transcripts/                 # private inputs; ignored by current Git rules
    week1/                     # first supplied interval starts in June 2026
      [actual Zoom exports]
      manifest.json            # create from verified dates/source metadata
    week2/
      [actual Zoom exports]
      manifest.json
    week3/
      ...
  testing/
    .data/                     # private derived artifacts and complete attempts
```

This is a proposed alternative structure, not a set of newly created/imported folders/files. The manifest and downstream artifact contracts apply identically to the observed backfill root. Preserve original VTT/timestamped exports where possible; other actual export formats need inspection before choosing a parser. Do not rename away the only source provenance.

Each future weekly manifest should record:

- Numeric `week_index` and a stable cycle ID; the folder is a label, not its date definition.
- Verified local start/end and timezone, corresponding UTC instants and window-policy version.
- Meeting occurrence timestamps, source/export identities, revision/content hashes and original relative file references.
- Expected versus supplied meeting inventory, missing/corrected/late files, permissions and coverage readiness.
- The frozen prior-history snapshot and actual-versus-simulated clock mode used by the experiment run.

Sort by verified date interval/numeric week index, not lexical folder order (`week10` otherwise precedes `week2`). Detect accidental duplicate exports using source identity/revision/hash; do not treat a corrected transcript as the same evidence snapshot. Distinguish an empty week from a missing-data week.

Future weeks can exist on disk but cannot enter an earlier run's source pool or eligible angle history. Complete week1, review it and choose the branch to advance; then admit week2. All valid prior generated candidates on that branch remain history, including non-visible candidates. Controlled model comparisons share the same frozen prior history, not the result of the preceding challenger trial.

The exact date interval for `week1` is still needed. “Starts in June” does not resolve June 1 versus a Saturday-boundary window, and no date is invented. The provisional Saturday 04:00 Texas schedule remains separately awaiting timezone/window confirmation.

## 7. First-week evaluation before advancing

Use authorised material and human labels; no new LLM judge is needed:

1. Identify a small set of clearly useful source moments, weak/non-content discussion, and tricky qualifiers before inspecting model output.
2. Evaluate GPT-OSS 120B extraction, save full artifacts and label omissions/unsupported inclusions.
3. Generate angles from that admitted pool; label evidence support, reader usefulness, argument distinctness and fit with the corpus-derived editorial policy.
4. Embed canonical signatures with Small and test labelled repeated-versus-related pairs. Version thresholds rather than tuning them solely to yield a desired angle count.
5. Compare one Stage 1 challenger against the same input/evidence labels while holding generation/settings fixed. For Stage 2 comparisons, reuse the same frozen admitted moment pool.
6. Record JSON validity, coverage, latency/retries, unsupported claim count, useful distinct yield and human editing effort. Do not declare victory from the model's own base score.
7. Retain a held-out later week to test generalisation after first-week prompt/rubric refinement. Do not repeatedly use all three months as a tuning set and call the result independently validated.

User-requested refinement concerns prompts, source contracts, rubrics, similarity settings and stage models. It is not authorisation to fine-tune model weights on client transcripts.

## 8. Open choices and related records

Before real source processing, settle the exact week1 interval and supplied coverage, approve the model/profile, verify privacy routes and budgets/quota, and resolve the already-recorded very-close pair policy. These are not evidence of a held client meeting.

The [testing specification][testing-design] contains the full datastore/replay/clock contracts. The [next-call ledger][ledger] now records the supplied-folder plan and this comparison as a preparation document. The [transcript-to-angle specification][angle-spec] remains the two-stage functional baseline.

[small]: https://developers.openai.com/api/docs/models/text-embedding-3-small
[large]: https://developers.openai.com/api/docs/models/text-embedding-3-large
[embedding-guide]: https://developers.openai.com/api/docs/guides/embeddings
[pgvector]: https://github.com/pgvector/pgvector
[oss120]: https://openrouter.ai/openai/gpt-oss-120b:free
[oss20]: https://openrouter.ai/openai/gpt-oss-20b:free
[lightning]: https://openrouter.ai/nvidia/nemotron-3.5-lightning:free
[super]: https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b:free
[qwen27]: https://openrouter.ai/qwen/qwen3.8-27b:free
[plans]: https://openrouter.ai/pricing/
[limits]: https://openrouter.ai/docs/api_reference/limits
[testing-design]: <content_atelier_week_by_week_testing.md>
[ledger]: <to_be_asked_in_next_call.md>
[angle-spec]: <transcript_to_content-angle.md>
