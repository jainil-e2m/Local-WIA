# Week 1 generation-only test: execution and editorial review

Recorded 8 October 2026, 09:22:15 UTC (14:52:15 Asia/Calcutta). Internal development review, not Whitney approval or permission to publish. The user authorised the actual Apodex test and supplied keys locally; no key values appear here.

## Outcome

The embedding leg is disconnected, its code is preserved, and **zero embeddings were generated**. The real whole-week extraction test was run and refined through bounded attempts. A separate, explicitly labelled partial-pool angle diagnostic generated **five angle candidates** from five individually source-valid moments.

**The complete weekly pipeline has not passed.** Its latest extraction returned seven proposed moments, two of which fail the evidence contract. The ordinary pipeline rejected that response before Call 2. The diagnostic did not weaken that gate, repair quotations, mark the failed extraction successful or admit rejected evidence. It exists to evaluate Call 2 without paying for or repeating extraction.

My editorial assessment: the five directions are specific enough to be useful for calibration, but **none is ready to approve unchanged**. Two need material grounding corrections; the other three need more bounded mechanisms and calmer framing. These are assistant review judgments, not founder decisions, numerical recalibration or automatic eligibility scores.

## 1. Exact test scope and disconnect

The active local setting and code default are `CONTENT_ATELIER_EMBEDDINGS_ENABLED=false`. Live credential validation requires only the LLM credentials while this is false. The paid embedding key can stay locally configured without being used.

The normal generation-only path is:

1. Load and preserve the complete weekly source snapshot.
2. Send one physical whole-week extraction request, if an exact compatible validated response is not already cached.
3. Validate the received evidence references, quote, contiguous context and coverage acknowledgement.
4. Send the validated moment pool with its actual surrounding transcript passages to Call 2.
5. Validate and save angle candidates, then return **before embeddings, history loading and ranking**.

An additional guard rejects direct orchestration calls to `_embedding` while disabled. The vector adapter, canonical signature, reuse logic, scoring and PostgreSQL projection code remain available for a later deliberately approved phase. Presence of an embedding profile in a manifest is configuration provenance, not evidence that a vector was generated.

Successful normal generation-only runs use `generation_completed` plus `execution_scope=generation_only`, rather than full pipeline completion. Candidates retain null `embedding`, `max_similarity` and `adjusted_score`; final visible IDs are empty. They are not historical-similarity-verified weekly selections. The separate diagnostic uses `partial`, never `generation_completed` or `completed` for the complete week.

No pgvector database was started/projected, no Slack was included, no briefs/packs were generated, and no content was published. Only Week 1 was processed by the real model.

## 2. Source fidelity and request capacity

Week 1 contains **nine exports and 3,238 source turns**. The lossless compact bridge retains every cue body, full speaker labels, source order, overlapping timestamps, greetings, endings, fillers and existing transcription problems. Compression is export/representation compression, not an editorial summary. Unknown dates, meeting names and timezones stay unknown; the absent Zoom metadata still needs supplying.

The final integrity check compared all nine current original files with their archived original bytes and SHA-256 hashes: **all matched**. Source records, reference maps and complete weekly payloads are stored locally under `testing/.data/weekly_packets/week1/<fingerprint>/`. Scoped request references such as `m4.t0096` map to stable canonical source-span IDs; this mapping does not alter source dialogue.

Apodex's published tokenizer was downloaded explicitly from public assets and pinned/checksummed locally. No private transcript was sent to a cloud token-count endpoint. The public route snapshot advertised a 262,144-token context. Its BF16 hosted framing may differ from the published NVFP4 tokenizer package, so local counts are labelled estimates of message text plus format allowances, not exact provider billing.

| Latest extraction request a4 | Tokens |
|---|---:|
| Locally counted message text, including the trusted schema text | 138,064 |
| Additional response-format proxy | 6 |
| Unmeasured provider margin | 13,807 |
| Reserved completion, including applicable reasoning | 65,536 |
| Headroom against the public reference context | 44,731 |
| Actual returned hosted prompt usage | 138,079 |

The real request was accepted at this size and completed with a `stop` response. Therefore capacity was not the observed blocker for this particular Week 1 test. It does not prove semantic recall of every useful passage or guaranteed capacity on longer future weeks.

The earlier 120,000-character safeguard remains only for the legacy flat request path. Active compact execution uses model-specific local token preflight and refuses overflow without truncating, summarising or automatically splitting the week. Historical GPT-OSS measurements remain separate and have not been relabelled as Apodex counts.

## 3. What actually happened

All requests selected `apodex/apodex-1.1-mini:free`. The returned successful HTTP responses identify Novita. No automatic paid fallback or model substitution was used. JSON-object mode, temperature 0.2, low reasoning and a 65,536-token completion reserve are fingerprinted in the saved requests.

| Attempt | Purpose / observed result | Downstream outcome |
|---|---|---|
| a1 | Actual route rejects `json_schema` with HTTP 400, despite catalog-advertised support | Raw rejection preserved; no extraction or angles |
| a2 | Explicit supported `json_object` format, with the full strict contract at system authority: seven proposals, all seven quotes incorrectly bound; invented turn 3239 | Rejected; no angles |
| a3 | Meeting-scoped references, exact nine-meeting acknowledgements, evidence-first prompt: ten proposals, six exact quotes; context lists were sparse rather than contiguous | Rejected; no angles |
| a4 | Same complete source; brief literal quotes and explicit first/last context boundaries: seven proposals, six exact quotes; five records individually pass source structure | Whole batch rejected for cross-meeting evidence and a non-exact quote |
| a5 | Separate Call 2 diagnostic reuses the five individually valid a4 records, retains both rejects and all actual context | Five candidates saved; status `partial`; no new extraction, embeddings or ranking |
| r1 | Cache-only replay of a5's exact angle request and original source snapshot | Identical candidate IDs/content/timestamps; zero new service attempts |

The scoped-reference and boundary changes improved observed quotation binding and removed the need for the model to enumerate thousands of IDs. This is a small uncontrolled calibration sequence, not proof that any individual change caused a general quality improvement. All rejected outputs remain available for examination.

The live compact coverage response now acknowledges each meeting's supplied first ID, last ID and turn count. The backend still checks exact source references for every admitted moment. It records delivered turns separately from the model acknowledgement and does **not** claim the acknowledgement proves comprehension or a complete semantic audit.

### Actual returned usage

| Attempt | Prompt | Completion | Reasoning included in completion | Total | Reported cost |
|---|---:|---:|---:|---:|---:|
| a2 | 127,179 | 56,199 | 26,460 | 183,378 | 0 |
| a3 | 137,962 | 11,606 | 7,546 | 149,568 | 0 |
| a4 | 138,079 | 9,056 | 6,373 | 147,135 | 0 |
| a5 | 44,196 | 8,592 | 5,498 | 52,788 | 0 |
| Sum of reported usage | 447,416 | 85,453 | 45,877 | 532,869 | 0 |

Each returned usage object also reports zero upstream inference cost. The rejected a1 response has no usage/billing record; no charge is inferred from an absent field. There were **four extraction attempts and one angle attempt**, not five logical pipeline stages. Reasoning counts are not additional to the completion column. Replay makes no new request and its reused original usage is not counted again.

## 4. Extraction quality: structural validity is necessary, not sufficient

The latest full extraction is still correctly blocked:

- `google_ads_timeline` spans m1 and m3 in one moment, violating the single-conversation contract. It also phrases a practitioner's stated runway as a general rule that early silence is normal. Separate moments could later support a qualified relationship in Call 2; this is not permission to combine their source contexts.
- `tour_cancellation_rate` supplies a quote that is not an exact substring of its declared anchors. The backend does not silently add an anchor, stitch adjacent cues or fix a transcription to accept it.

The five other records pass **reference, literal-fragment and context-structure checks**, not automatic semantic verification. For example, the pricing moment includes numeric detail in its summary that lies before its returned context boundary. The source editor saw it somewhere in the whole week, but Call 2 was not supplied those cues. A valid short quote does not prove every summary assertion.

The model's coverage notes also reference a “platform-fit moment” that is not present in the final seven-record list. Meeting acknowledgements are exact, but explanatory coverage prose is not automatically true. Three acknowledged meetings produce no accepted moments; that may be appropriate, but no human gold-standard inventory exists to quantify missed opportunities. Do not claim measured recall or full thematic coverage from seven proposals.

## 5. All five generated candidates: source-grounded editorial assessment

The full original candidates remain unchanged in the private JSON artifact linked below. I reviewed all five and their complete selected context intervals. Suggested directions here are manual review proposals, not additional LLM generations or final replacement records.

| Candidate | Strong supported decision | Current issue / review result |
|---|---|---|
| “No posing can misrepresent a photographer's actual service” | Describe candid photography without implying the photographer will not provide helpful portrait direction | **Revise.** Good, specific Whitney fit. Rejected clients, wasted consultations and damaged reviews are unobserved outcomes added in its mechanism. |
| “When ads promise clarity, the landing page must deliver it or traffic leaks at the form” | Inspect which service context the ad already conveys and which questions the destination must answer | **Hold/rewrite grounding.** Useful diagnostic hypothesis becomes a usual cause; the Google/Meta distinction is overgeneralised. |
| “Text follow-ups can outperform email for venue tour conversations” | Test a channel that may make tour responses and cancellation feedback easier | **Revise.** Source-specific observation is useful; improved show rates and greater honesty are not established. |
| “Your strongest differentiator is useless if couples can't find it” | Make an existing comparison aid easier to discover at the relevant buyer decision | **Revise.** Strong idea, but “useless,” “never see” and choosing a cheaper competitor overstate evidence and disrespect existing effort. |
| “A system that works for venues may not fit a small photographer's economics” | Separate liking a tool from whether recurring expense fits the owner's actual capacity | **Hold/rewrite grounding.** Promising respectful theme, but unsupported/ambiguous pricing, an invented 50-wedding example and mischaracterised setup objection contaminate the argument. |

### 5.1 Ad-copy precision: preserve service truth

Selected context: `m1.t0020–m1.t0076`, about 01:12–05:38 of the export. The photographer explicitly distinguishes candid capture from refusing to help people pose. Couples want real moments and guidance during portraits; this is a substantive buyer-expectation decision, not a generic “improve your copy” tip.

The candidate's working title, tension and reader decision are useful. Its mechanism goes beyond the discussion by asserting wrong clients, wasted time and potential bad reviews. The source supports a concern about what the wording communicates, not an observed chain of harm. A statement that the wording was not performance-tested does not neutralise confident claims elsewhere.

Better bounded direction: **“Describe candid photography without promising couples no guidance.”** Explain the distinction that the actual owner protects. Keep the alternative wording as an agreed review choice, not a proven improvement or current live campaign result.

### 5.2 Landing-page context: diagnosis, not a settled cause

Selected context: `m4.t0048–m4.t0196`, about 05:09–16:10. The team considers a destination planner's poorly explained service, reported page-to-form movement, possible audience fit, actual Meta copy, reported leads and possible tracking uncertainty. The same interval includes their observation that richer Meta ads explain the service before a visitor reaches the shared page.

The candidate correctly preserves the 20% figure as an unaudited observation in its notes. But “usually still looking for information,” “often means” and a page that “must” explain more because Google visitors have “no context” are stronger than the evidence. Google visitors do not literally arrive with no prior context. Also, Meta is not paid search; calling “Meta and Google” paid search is an avoidable category error.

Do not turn the reported 20% page-to-form movement into a verified abandonment rate, claim nobody inquired, or erase the actual Meta leads later discussed. The cause remains a hypothesis; ad copy, audience and measurement questions are still in the source.

Better bounded direction: **“Before changing the inquiry form, inspect the service context visitors receive.”** This preserves the owner's diagnostic decision without asserting that missing clarity is usually the cause. The large context interval may be justified by the platform comparison, but a single narrower proposition would reduce unrelated detail in Call 2 without removing anything from Call 1.

### 5.3 Text conversation: distinguish the observation from the proposal

Selected context: `m7.t0173–m7.t0191`, about 25:12–27:45. The team observes tour-related text replies and cancellation/competitor feedback in one venue account. They explicitly say emails are still needed. Whitney then suggests a host photo, introduction and arrival instructions before a tour; that proposed fuller sequence is not currently happening.

The candidate preserves the internal-only handling and absence of a split test, and its test-oriented reader decision is useful. But it predicts improved show rates and “more honest” feedback, neither of which is demonstrated. It also combines feedback-channel choice and a pre-arrival relationship-building proposal. They could support separate angles only if each has enough distinct substance; the model must not default to one or two simply to meet a count.

Better bounded direction: **“Use tour texts to make replying and giving feedback easier, while retaining email's role.”** If the host introduction is selected, present it explicitly as a proposed experiment in arrival confidence, not an implemented system or attendance result. Practical text consent/operating requirements belong to later verification, not invented approval here.

### 5.4 Comparison chart: visibility, not absence of value

Selected context: `m8.t0248–m8.t0266`, about 32:34–34:14. The owner already has a comparison chart and uses it in follow-up. Whitney missed it in site navigation and recommends including it on the landing page. The chart contains estimates of externally sourced costs, not verified universal savings.

This is a particularly good Whitney-fit situation: a capable owner has already done useful work; the next question is where the buyer encounters it. “Useless” undermines that existing effort. “They never see it” is contradicted by use in follow-up, and “default to a venue-only option” is an invented buyer outcome. “Almost too simple” describes the owner's concern about the chart's detail, not proof that its navigation causes losses.

Better bounded direction: **“Make your existing comparison guide easier to find when couples assess value.”** Preserve estimated-cost labels and the proposed placement test. Do not assert that all-inclusive always wins or that placement has demonstrated a conversion lift.

### 5.5 Tool economics: do not convert a budget objection into bad judgment

Selected context: `m9.t0219–m9.t0241`, about 28:32–29:59. The photographer states a maximum of about twenty weddings a year, a low existing monthly expense and concern about the new ongoing cost. She praises the system, would recommend it and explicitly says the setup fee is not the main objection. Whitney acknowledges that comparison is not apples to apples.

The moment summary and resulting source assertion contain $147 monthly and $12.97 setup. Those amounts occur earlier at `m9.t0214` and `m9.t0216`, **outside the context supplied to Call 2**. The original transcript literally contains “$12.97”; it may be a transcription problem, but we must not silently reinterpret it as $1,297 or a current published offer. Either include the required source interval and mark ambiguity, or omit exact price from this direction. The statement that she rejects both fees misstates her expressly recurring-cost objection.

The mechanism also invents a fifty-wedding payback example and implies a venue/planner system has proven viable; no measured return is supplied. The twenty-wedding cap can be used as a reported prospect circumstance, not a break-even calculation or general incapacity rule.

Better bounded direction: **“A tool can be valuable and still not fit your current recurring-cost budget.”** Respect the owner and compare capabilities, existing expenses, capacity and workflow needs without pretending the existing and proposed tools are equivalent. Accurate product/offer scope and verified economics would need research later.

## 6. Whitney fit, distinctness and scores

The underlying decisions are meaningfully different: truthful service positioning, page orientation, reply-channel choice, comparison-evidence placement and recurring-cost fit. Shared messaging foundations do not make the first, second and fourth identical. Nevertheless, two are website-review directions, so later editorial selection should compare their exact contribution instead of relying on different titles.

No embeddings were used to make this manual assessment. No historical similarity, last-run overlap, novelty, recency adjustment or threshold-eligible visible set has been calculated. The five candidates also do not prove a complete week's editorial range because the input pool was partial.

Model base scores are 80, 73, 73, 80 and 80. Their grounding dimensions are 4, 3, 3, 4 and 4 out of five. These are self-assessments converted mechanically by the existing formula, not independently calibrated quality measurements. The pricing example is a concrete counterexample to trusting those scores: it receives 4/5 grounding despite its source-context mismatch. Passing a JSON/reference validator does not override this.

Whitney fit should be judged against the [corpus-based taste research](whitney-taste-and-editorial-pipeline.md): respect competent owners, explain the thinking beneath a tactic, preserve uncertainty and actual service ownership, and make the commercial relevance meaningful without manufacturing results. These candidates are most promising when they retain the real decision, and weakest when their mechanisms add a familiar universal marketing story.

## 7. Next prompt refinement targets, not silent policy learning

The executed Call 1 v1/v2/v3 refinements are archived in [prompts.md](../backend/prompts.md), including full supplement texts, exact assembly and timestamps. Call 2 ran the existing corpus-grounded v2 templates unchanged. No semantic prompt is automatically rewritten from a model response.

The next deliberate release should address observed failures, not just add more generic “be accurate” language:

| Stage | Concrete instruction to strengthen | Evaluation evidence |
|---|---|---|
| Call 1 | Keep every moment within one meeting even if a recurring topic spans several; return separate evidence records instead | a4 cross-meeting runway proposal must be rejected, not combined |
| Call 1 | Every material number/condition in the summary must lie in the selected context; otherwise widen context deliberately or omit it | Pricing amounts before the returned boundary |
| Call 1 | Prefer faithful bounded propositions over slogan-like angle titles; keep observed vs hypothesised vs proposed status in the proposition itself | “Useless,” “repel” and mandatory 90-day rules |
| Call 1 | Include a neighbouring correction that changes the interpretation, even if the quote is earlier | Setup expense not the main objection; email still needed |
| Call 1 | Coverage prose may name only records actually returned and accurately distinguish excluded material | Reference to an absent platform-fit moment |
| Call 2 | Unsupported detail in the moment summary is not usable evidence; factual assertions require the supplied source_evidence, not just a moment ID prefix | Pricing copy-through despite missing cues |
| Call 2 | Put material uncertainty in argument, take and mechanism, not only qualifiers/inference fields | Landing-page cause and text attendance implication |
| Call 2 | Explain only the supported mechanism; do not add buyer losses, reviews, attendance, honesty, payback examples or numerical thresholds from generic knowledge | All five reviewed mechanisms |
| Call 2 | Respect work already done; avoid absolutes such as useless/never and guaranteed competitive superiority | Existing comparison chart and follow-up use |
| Call 2 | Distinguish an observed conversation from a proposed sequence; do not treat suggestions as delivered services | Pre-tour host introduction |

A bounded pre-return self-check can be part of each of the existing two prompts; it need not expose reasoning or create a third call. Deterministic validators should continue enforcing factual structure, while a manually reviewed source-claim fixture set tests semantic behavior. Avoid ad hoc string bans or repairing arbitrary prices: these would not solve the meaning problem.

Keep the original baseline and label any proposed replacement separately. After a deliberate Call 2 revision, this same validated partial pool can test angle interpretation without new extraction; it remains partial. A later full-week extraction test must independently pass. Do not change models, auto-run unlimited retries, promote partial evidence to complete coverage or enable embeddings merely to obtain a successful status.

## 8. Preservation, reuse and verification

All exact requests, returned bodies, parsed received JSON, failure records, refined prompts, source maps, validated moment subsets, candidates and usage are stored in the private local datastore. API keys are excluded from requests and cache identity. A literal scan of fifty private JSON artifacts found no supplied credential values. Git-ignore is not encryption or a retention policy; protect and back up this datastore.

The diagnostic requires a saved failed live response from the exact current extraction profile and unchanged original raw source revisions/reference map. It validates globally unique labels, rejects invalid records without editing them, and never caches failed Call 1 as successful. Call 2 still uses the ordinary strict contract. Default diagnostic mode is cache-only replay.

Actual replay r1 saved the identical five candidates with original generation lineage and zero new service attempts. Future embeddings can be generated from approved/refined signatures once the user explicitly reconnects the vector leg. Changing a prompt creates a new request fingerprint; preserving an old response does not mean falsely reusing it under different instructions.

Verification: **89 offline tests passed**, including nine new partial-pool tests; Ruff passed. Tests cover generation-only stopping, direct embedding guard, missing paid key being irrelevant, literal source boundaries, delivery acknowledgement, token overflow refusal, synthetic future opt-in/reuse, partial failure preservation, original-byte snapshot comparison, replay-only behavior and strict downstream rejection. Vector reconnection tests use synthetic providers, not paid calls. No running pgvector integration was performed.

## 9. Artifacts and decision for the next iteration

Private local records:

- [Latest failed whole-week extraction manifest](../testing/.data/experiments/default/runs/week1-apodex-generation-only-20261008-a4/manifest.json).
- [Partial-pool evidence diagnostic](../testing/.data/experiments/default/runs/week1-apodex-partial-angle-diagnostic-20261008-a5/moment_diagnostic.json).
- [Individually validated moments](../testing/.data/experiments/default/runs/week1-apodex-partial-angle-diagnostic-20261008-a5/moments.json).
- [Unaltered five generated candidates](../testing/.data/experiments/default/runs/week1-apodex-partial-angle-diagnostic-20261008-a5/candidates.json).
- [Original angle request, response and usage](../testing/.data/experiments/default/runs/week1-apodex-partial-angle-diagnostic-20261008-a5/angle_generation.json).
- [Explicit partial review status](../testing/.data/experiments/default/runs/week1-apodex-partial-angle-diagnostic-20261008-a5/review.json).
- [Source-grounded assistant review ledger](../testing/.data/experiments/default/runs/week1-apodex-partial-angle-diagnostic-20261008-a5/quality_review.json).
- [Cache-only replay review](../testing/.data/experiments/default/runs/week1-apodex-partial-angle-replay-20261008-r1/review.json).

**Ready for further controlled prompt calibration; not ready for automatic weekly acceptance or embeddings.** Apodex demonstrably handles this request size and generates useful directions at reported zero cost, but the observed reference and semantic errors remain important. Stay at the moment/angle stage, strengthen the specific evidence behaviors above, rerun a bounded comparison deliberately and require the complete extraction contract plus source-grounded review before treating Week 1 as a successful weekly generation.
