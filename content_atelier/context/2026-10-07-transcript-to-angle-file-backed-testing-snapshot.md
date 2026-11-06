# Content Atelier — weekly transcripts to selected content angles

Prepared: 7 October 2026. Updated after the user's implementation clarifications on the same date.

Status: implementation design for review, not implemented. The user has additional clarifications before implementation begins. This slice ends with ranked, grounded, distinct angle cards ready for Whitney's review; it does not generate briefs or content packs. Very-close pair selection remains unresolved; see §16 and the [next-call ledger][call-ledger]. No backend implementation, new account access or deployment is performed.

## 1. Outcome and the latest requirements

Testing amendment, 7 October 2026: the user now specifies local pgvector, one embedding vector per angle, one week's backfilled Zoom transcripts followed by gradual chronological backfill, and JSON/Markdown persistence before the full PostgreSQL schema. The [week-by-week testing design][testing-design] defines the initial file store, scratch projection, simulated-versus-real clocks, branch isolation, model recommendations and full paid-output reuse contract. No paid test/harness is run. “Final content angles generation” remains to clarify as deterministic selection versus an additional refinement pass; it is not permission for a third similarity judge.

The proposed slice is sound: read the week's eligible transcripts, identify editorially meaningful passages with their surrounding context, generate specific angles from those passages, store/embed the candidates, compare them with historical and current-generation angle memory, apply a recency-sensitive overlap penalty, and surface a non-redundant high-quality set.

The desired output is not a set of call summaries or generic marketing tips. It is a set of **specific reader-facing arguments supported by this week's evidence**, each with inspectable source context and a reason to be considered now.

Confirmed by the latest request:

- Cover all in-scope transcripts in the weekly batch, not a convenient sample.
- LLM Call 1 shortlists relevant moments and preserves surrounding context.
- LLM Call 2 generates grounded, distinct candidate angles and quality scores.
- There is no fixed editorial cap on the number of generated candidate angles.
- Store and embed generated candidates in the angle-memory collection within the same Postgres database.
- Fetch similar historical angles using a similarity threshold and consider angles from the previous generation turn as well.
- Reduce a candidate's score when substantially similar angles were generated recently; greater similarity and greater recency should increase that reduction.
- Display every eligible distinct candidate strictly above the adjusted-score threshold; there is no four-angle display cap.
- “Last turn” is the previous completed generation run, not earlier batches in the current run.
- No additional LLM similarity judge is allowed; comparison and score adjustments use deterministic numerical rules.
- The first implementation is transcripts only; Slack is deferred.
- Saturday 04:00 Texas time is provisional and must be confirmed with WIA, including the actual timezone, weekly window and late-arrival policy.

Important distinctions:

1. **Unlimited candidate count is not unlimited computation.** There is no instruction to generate exactly four/five/ten candidates, but provider context/output limits, safe budgets and completion tracking still exist.
2. **Directly related means source-related.** The candidates should be closely grounded in the weekly material, not all closely similar to each other.
3. **Generated recency is the requested clock.** Prior generation can reduce scores even when that old candidate was never published. Publication remains a separate fact.
4. **Visible is not approved.** The selected cards await the existing human angle gate; no CTA is silently chosen and no brief/asset work starts.

The latest user clarification supersedes the earlier four-angle display target: surface **all qualifying distinct angles above the adjusted-score threshold**. Operational budgets and UI pagination must not silently reinstate a four-item selection cap. A later brief/pack allocation can still select a production subset through its own explicit decision. [Storage design][vector-design] [Next-call ledger, U-01][call-ledger]

## 2. Scope, inputs, and explicit non-goals

### 2.1 Initial inputs

The base contract accepts already accumulated transcript records, with stable recording/document IDs, source system, meeting purpose, occurrence date, participants/speaker attribution, transcript text/turns, timestamps and source locators where available.

Use the initial input adapter needed for the actual available material: an authorised file/export import or configured transcript connector. Choosing production connector credentials and host coverage is a separate implementation decision. This specification does not provision them.

The user confirmed **transcripts only** for the first implementation. Keep source processing reusable for a later approved Slack rollout, but do not ingest/process weekly Slack threads in this slice. Historical angle memory, active curated policy and existing authorised source metadata are companion inputs. Historical transcripts may help a later research stage, but must not replace this week's source anchor during candidate generation.

### 2.2 Out of scope

- External web/SEO research as a prerequisite to angle generation.
- Full historical brief research, brief approval and asset allocation.
- Emails, carousel copy, reel scripts, captions and pack approval.
- Publishing, scheduling, automated learning, fine-tuning and a new dashboard/authentication system.
- A separate vector database or a graph database.

Use existing approved voice/strategy/offer definitions to keep directions appropriate. Offer fit is optional directional context here, not a selected CTA or an invented current service promise.

### 2.3 Two logical LLM stages, not necessarily two physical requests

“LLM Call 1” and “LLM Call 2” name the two main reasoning responsibilities. A week of long calls may require several provider requests within each responsibility. Claiming exactly two physical calls irrespective of weekly size would create truncation and coverage risks.

Recommend naming them `moment_extraction` and `angle_generation`. Store each physical attempt and its exact input/version. If exactly two physical requests is a hard product constraint, we first need a measured maximum weekly input/output budget and an explicit overflow behaviour.

The user explicitly ruled out an additional LLM similarity-comparison step. Only the two logical LLM responsibilities above are present. Embedding generation is still needed for angle similarity, but it is not an extra semantic judge. Exact vector comparison and versioned numerical rules handle matching; unresolved very-close display policy remains a product clarification, not a third LLM call.

## 3. Weekly batch and source preparation

### 3.1 Freeze a complete, auditable batch

Create an editorial cycle with business timezone, occurred-time start/end, cutoff, approved source scope, source revision manifest and coverage status. Preserve observed/fetched time separately from meeting occurrence time.

Every in-scope transcript should reach one of: ready, processed, excluded with reason, pending/unreadable, failed with error, or missing according to a verified coverage expectation. Zero extracted moments is a valid processed outcome; it is not a failure or a reason to invent a story.

Do not claim that “all transcripts were processed” because one connector returned successfully. Missing host access, pending transcripts, pagination or unavailable attachments need visible coverage records. If partial coverage is allowed, it is explicitly accepted and labelled before the results are treated as the week's complete selection.

### 3.1.1 Provisional execution time versus weekly source window

The user proposed Saturday morning **04:00 Texas time**, for now. Record this as provisional. For discussion, `America/Chicago` is the timezone assumption **only if WIA means Central Time**, with 04:00 kept as local wall-clock time across daylight-saving changes. Do not hardcode year-round UTC−6, infer the timezone from the operator's location, or install an automation from this design task.

Execution time does not by itself define the meeting-occurrence window or the transcript-availability cutoff. A proposed window is previous Saturday 04:00 inclusive to current Saturday 04:00 exclusive in the confirmed timezone; the client must confirm that, any grace period and late/corrected transcript handling. Resolve local boundaries to UTC separately and preserve both with the run. See C-01–C-03 and the timezone sources in the [next-call ledger][call-ledger].

### 3.2 Preserve exact evidence before normalisation

Keep original source bytes in private storage where available and authorised. Create immutable ordinary-processing source revisions with hashes. Segment/normalisation/extraction outputs reference the exact revision.

Resolve speakers and roles; retain uncertainty. Use high-confidence glossary normalisation for search while preserving raw text for quotes. Classify meeting purpose so useful WIA editorial/operations discussions are not removed by a blanket internal-call rule, while engineering/vendor noise does not become content evidence without a decision to include it.

Merge duplicate exports into one canonical conversation identity without erasing provenance. Zoom and Fathom copies of one meeting do not prove recurrence across two calls. Adjacent overlapping chunks are not independent moments.

### 3.3 Store chunks, but do not discover moments only by top-k chunk search

Store context-preserving transcript segments with source turn IDs, sequence, speaker/role, timestamps, raw/normalised text and compatible search representations. They support evidence access and future historical retrieval.

For moment discovery, process the entire eligible transcript through LLM Call 1. If a call fits the approved input budget, retain full conversational context. If it does not, split on conversational boundaries with overlap and carry the relevant introduction/qualifiers. Track every interval's processing coverage and merge duplicate extracted moments afterwards.

Do not retrieve just five “interesting” chunks first and pretend the rest of that meeting was reviewed. Weekly moment recall is a coverage problem before it is a similarity-search problem. [Source/moment contracts][vector-design]

## 4. LLM Call 1 — shortlist moments with their surrounding context

### 4.1 What it should recognise

Identify moments that could support an insightful argument for wedding-industry business owners:

- A concrete result, with attribution and limitations.
- A revealing question, objection, trade-off or decision.
- An audience tension or before/after experience.
- A teaching explanation or strategic mechanism.
- A staff/client story showing what changes when a process improves.
- A credible new observation or recurring concern supported by the actual record.

Do not reward raw excitement, a number without meaning, or a generic motivational statement. Useful moments can be qualitative and can come from one strong source. Multiple independent sources strengthen recurrence, but they are not mandatory for every useful angle.

Use a reviewed current editorial policy bundle, not every older promotional email or rejected assistant draft. Transcript text is evidence, not instructions that can change the pipeline's rules or authorise tools.

### 4.2 The source/context packet

Each retained moment needs:

| Field | Purpose |
|---|---|
| Moment ID and source revision | Stable provenance; system assigns identity |
| Anchor turn/span IDs | Pinpoint the passage that triggered the insight |
| Exact anchor quote or factual passage | Inspect the underlying language |
| Context turn/span IDs | Preserve setup, qualifiers, response and implications |
| Context summary | Short orientation, explicitly a model interpretation |
| Speaker/role/client confidence | Prevent staff reports becoming direct testimonials |
| Moment type and source-supported proposition | Explain what is interesting and what can be said |
| Audience relevance | Explain why the wedding professional would care |
| Qualification/exclusion list | Record what the passage does not establish |
| Measurement/claim status | Reported, measured, estimated, derived, hypothetical or planned |
| Sensitivity/permission requirements | Keep internal research and public use separate |
| Relevance/strength assessment and concise reasons | Help shortlist without hiding the supporting evidence |

Require source-span IDs from the provided transcript, not invented recording links or timestamps. The model can nominate context IDs; the application resolves those IDs back to original text.

### 4.3 Surrounding context should be meaning-complete

Do not define context as a fixed number of seconds on each side regardless of meaning. Include enough material to answer:

- Who is speaking and about which client/account?
- What time period and comparison are being discussed?
- Is the statement an actual result, an estimate, a plan or an illustration?
- What qualification changes the apparent meaning?
- Does a later response contradict or correct the anchor?

A bounded initial turn/timestamp window is useful, but allow explicit extension to source-linked turns when necessary. If safe context exceeds the processing budget, flag the gap instead of silently omitting the qualifier.

### 4.4 Validate before admitting a moment to generation

Application checks must resolve all references, verify that quoted text occurs in the source, retain correct values/units, and detect incompatible speaker/client references. Mark text matching, speaker confirmation, interpretation and permission independently; a fuzzy match is not comprehensive verification.

Persist extracted candidates and reasons for exclusion. Shortlisting is based on relevance and evidence usability, not a fixed “top three moments per call.” Weak/noisy material can be withheld from LLM Call 2 while remaining traceable.

A moment with unresolved central factual meaning must not support a confidently factual angle. A restricted story may remain available for authorised internal review, but it cannot silently become publicly usable evidence.

## 5. Build the week-wide moment/context pool

Combine admitted moments across all processed transcripts while preserving their individual provenance. Link related concerns by canonical topic and source-supported proposition; keep different speakers/accounts/periods separate.

The aggregate is a structured evidence pool, not one short “this week everyone discussed ads” summary. Summarising the entire week into a generic paragraph would erase the specific tension, mechanism and proof that make angles useful.

Deduplicate extraction overlap and alternate exports by underlying source event. Do not collapse different client experiences merely because their wording is similar. Recurrence counts use independent conversations/clients, not chunk count.

Maintain a coverage map showing admitted moments, excluded moments, generation batches and unresolved context. If the week-wide pool cannot fit one LLM Call 2 request, assemble coherent bounded evidence packs with a compact global topic map and traceable cross-pack references. Rehydrate complete source/context packets before an angle uses evidence outside its current pack.

Every admitted moment must be considered by the generation stage, or its omission must be explicit. A compact global map is orientation, not a replacement for factual source context. Track cross-pack combination opportunities so batching does not silently prevent useful connections across calls.

## 6. LLM Call 2 — generate specific, grounded candidate angles

### 6.1 An angle is an argument, not a topic or hook variant

A topic could be “lead follow-up.” An angle should state a particular source-supported decision or belief shift for an audience, with an explanation of why it matters. Two openings for the same claim are two hooks, not two distinct angles.

An admitted angle needs:

- Defined audience/state and concrete tension.
- One clear take or central claim.
- Source-supported mechanism or explanation, with inference labelled where necessary.
- Reader decision, implication or belief shift.
- At least one relevant moment from this week's batch.
- Supporting moment/context/claim IDs and the contribution of each.
- Explicit excluded interpretations and unresolved questions.
- Concise differentiation from other current candidates.
- Quality components, each with a short evidence-based reason.

The model should propose multiple angles from one moment only when they deliver genuinely different supported reader contributions. It can combine moments across transcripts, but cannot transfer one client's result to another, erase a DIY/agency chapter, or turn temporal association into proven causality.

The corpus cases are useful calibration tests: the ten-week posting pause protects a competent owner's ability to step away, not a universal “never post again” lesson; ad-attributable bookings are not profit or all business revenue. [Editorial case readings][taste-review]

### 6.2 “No limit” means no target quota or arbitrary candidate cap

The prompt should request all substantive angles supported by the supplied evidence, allowing zero where appropriate. It should not request exactly N angles, reward filler to meet a minimum, or split one idea repeatedly to increase count.

Physical requests still have output-token and cost/time bounds. Use resumable batches/continuations with an explicit coverage ledger, supplied previously generated signatures and unexplored evidence combinations. Continue only while genuinely unexamined evidence/contributions remain. Prevent a loop that generates cosmetic paraphrases forever.

If an operational budget is reached before coverage is complete, save the valid candidates and show `generation_incomplete` with the unprocessed evidence. Do not silently treat a truncated JSON response or an arbitrary first page as the complete weekly pool. This budget is an operational safeguard, not a quality-independent editorial candidate limit.

### 6.3 Suggested structured response contract

Each model response contains an array of candidate records, evidence coverage and any remaining work. Candidate fields include:

| Field | Interpretation |
|---|---|
| Local candidate key | Response-local reference; persisted ID assigned by application |
| Title and one-sentence argument | Human-readable direction, not finished copy |
| Audience, tension, take, mechanism, reader decision | Structured meaning used to assess distinctness |
| Source moment/context IDs | References restricted to the provided evidence |
| Source-supported assertions | Each material assertion mapped to supporting claim/span IDs |
| Editorial inference | Useful interpretation kept separate from reported source facts |
| Required qualifiers / forbidden claims | Preserve meaning when the angle is later expanded |
| New contribution relative to supplied candidate signatures | Explain substantive difference, not just a changed hook |
| Quality components with reasons | Independent of historical recency, which code adds later |
| Questions/risks | What cannot yet be assumed |
| Processed evidence IDs and continuation state | Auditable coverage rather than an invented “complete” boolean |

The application validates schema, references, authorised evidence, metric scope and readiness. It persists valid candidates, including those later below the floor or suppressed for overlap. Malformed attempts are recorded as errors; invalid raw responses are not promoted into verified angles.

### 6.4 Base quality score from Call 2

Call 2 should assess quality without pretending to know historical novelty before memory comparison. Do not include a second hidden recency penalty in its base score.

Recommended starting rubric, explicitly uncalibrated:

| Component | Meaning | Proposed weight |
|---|---|---:|
| Grounding | The central/material assertions are supported with correct scope | 0.35 |
| Direct source relevance | The direction actually follows from this week's passages, without a vague leap | 0.25 |
| Audience fit | A capable wedding professional would recognise a meaningful problem/decision | 0.15 |
| Specificity | Clear argument, concrete mechanism or situation; not interchangeable marketing advice | 0.15 |
| Editorial usefulness | A useful implication or perspective worth developing | 0.10 |

Each component is a 0–5 anchored assessment. Require short reasons and relevant evidence IDs, not a request for hidden internal reasoning. Suggested anchors: 0 = absent/unsupported, 3 = acceptable but needs refinement, 5 = unusually strong and precise; define intermediate examples during calibration.

The application computes:

```text
base_quality = 20 * (
    0.35 * grounding
  + 0.25 * source_relevance
  + 0.15 * audience_fit
  + 0.15 * specificity
  + 0.10 * editorial_usefulness
)
```

This produces 0–100, not a probability of success. Grounding and direct source relevance jointly dominate because the user explicitly prefers closely related, defensible directions over vaguely associated ideas.

Use independent admission checks before ranking: missing/nonexistent source references, central unsupported claims, prohibited disclosure and unresolved material context cannot be compensated by high audience/creativity scores. Proposed calibration floors could include grounding and source relevance each at least 4/5, plus base quality at least 70/100; these are examples, not approved production thresholds.

LLM self-assessment is a noisy judgment. Schema/range validation and deterministic arithmetic make scoring inspectable, not automatically correct. Evaluate agreement with Whitney's labels and review source-faithfulness errors, not just how high the model rates itself.

## 7. Store and embed before filtering away candidates

### 7.1 Candidate identity and semantic representation

Persist stable angle identity, exact revision, generation run/cohort, source dependencies, policy/prompt/model versions, structured argument, base-score components/reasons and processing status. Retain all valid generated candidates even if they will not appear in the week's visible set.

Embed a canonical semantic signature built from audience, tension, take, mechanism, core claim, reader decision and relevant proof/case context. Keep projection text/hash/version and compatible embedding profile. Do not embed only the catchy title, and do not embed a fabricated source quote merely because Call 2 returned it.

Embedding is a derived representation; the authoritative angle remains structured content plus provenance. Query vectors and stored signatures must use a compatible embedding space/profile. Same dimensions alone do not establish compatibility.

Confirmed for this test: **one active embedding vector per angle**, using one canonical argument signature; no separate hook/topic/quote/format vectors. Save the returned vector artifact so local pgvector can be rebuilt without repaying. Semantic signature/profile changes invalidate the active projection; do not compare incompatible spaces or concurrently search multiple versions for one angle. OpenAI large/1,536 is a recommendation to evaluate, not an already selected model. [Testing design, §§10–12][testing-design]

### 7.2 Persisted does not mean historical for this candidate's own run

Freeze a memory cohort/as-of boundary when the selection run starts. Store new candidates immediately but mark them as belonging to the current generation cohort.

Use three comparison sets:

- **Historical set:** eligible candidates from prior completed generation cohorts, as of the frozen memory boundary.
- **Current set:** all newly generated candidates in this cohort, including candidates generated by earlier physical Call 2 batches.
- **Previous-turn set:** the previous completed generation run, explicitly confirmed by the user; include its eligible IDs and deduplicate them against historical matches. It is a highlighted historical subset, not a second penalty.

A new angle must not match itself at similarity 1.0 and age zero. Nor should the first batch saved today unfairly penalise the second batch as if it were an old historical proposal. Current-cohort overlap is handled through symmetric pairwise set selection.

Retries that reuse the same logical generation request are not new generation events. An intentional regeneration is a new request/cohort with visible lineage. It must not overwrite the old score or reset its source timestamps. Meaningful new generation recency belongs to a genuine generation event, not an embedding refresh or storage update.

### 7.3 Previous-turn interpretation

Confirmed: “last turn” means the **previous completed generation run**, including an intentional same-week regeneration. Earlier physical batches within the current run belong to the current set and receive symmetric current-pair comparison, not historical age-zero penalties. Incomplete/failed runs do not become the previous completed run; completion/readiness is an explicit durable state.

For same-week regeneration, preserve any accepted/pinned angle choices explicitly and rank replacements around them; do not casually erase a reviewed direction. Exactly which prior suggestions are retained or superseded is a product command, not a vector-search side effect.

## 8. Retrieve similarity matches and assess meaning

### 8.1 Define the comparison metric and threshold

Use raw cosine similarity on compatible angle signatures for the threshold test. pgvector's cosine operator yields distance, with similarity equal to `1 - distance`. [pgvector querying][pgvector]

The retrieval condition is similarity **at or above** a calibrated threshold, not “whatever five nearest rows exist.” A nearest result can still be unrelated; conversely, there may be many legitimate matches above the threshold.

The old proposal's approximately 0.78 related / 0.90 duplicate values are only starting hypotheses for its representation/model. Recalibrate for the actual signature/profile against labelled pairs of same argument, related but distinct contribution, and unrelated directions. These values are not approved by this document.

### 8.2 Threshold coverage, not silent top-k truncation

For the initial modest history, recommend exact comparison against eligible historical representatives and persist every threshold-qualified match, with pagination if needed. A presentation shortlist can be smaller, but ranking must not overlook a more recent important match simply because it was outside a nearest-neighbour top-k list.

pgvector supports exact search; approximate indexes trade recall for speed. [pgvector indexing][pgvector] If approximate retrieval is introduced later, validate filtered recall against exact comparisons and explicitly distinguish approximate coverage from complete threshold coverage.

A future production optimisation may retrieve a bounded candidate neighbourhood and rerank exact distances, but it must retain enough coverage for recency-aware ranking or report uncertainty. “No duplicate found” is not credible if memory was incomplete or queries truncated silently.

### 8.3 What each match records

Retain candidate/historical revision IDs, compatible profile, raw similarity, deterministic match band/rule version, historical generation time, age at score cutoff, prior status/reason, structured signatures/source references, freshness factor and penalty contribution. Do not invent a semantic relation or confidence label that no permitted stage established.

Do not fetch only a title/score: the prior audience, mechanism, core claim, reader decision and evidence are needed to tell whether the angle really repeats. A historical generated angle supplies editorial history, not new proof for today's claims.

### 8.4 Concrete numerical matching; no additional LLM judge

The automatic baseline is deterministic given the stored compatible vectors, signature text, timestamps and configuration:

- A raw cosine below the historical retrieval threshold is not a historical match.
- A raw cosine at/above that threshold is a qualified numerical match and contributes to the continuous overlap/recency formula in §9.
- A separate calibrated current-pair close threshold identifies pairs needing the selected close-pair policy in §10. It is not automatically the same threshold as historical relatedness.
- Identical canonical structured-signature hashes identify exact representation repeats; hash equality is not a general paraphrase detector or proof that all evidence revisions are identical.
- Every compared pair retains both records and its exact numerical inputs. Do not hard-delete a candidate because a high cosine was found.

The user has prohibited a separate similarity LLM judge. Call 2 already supplies structured reader contributions and source links; comparison does not invoke a hidden third model to assign semantic labels. Source permission/validity checks remain mandatory regardless of similarity.

Exact cosine means the numerical calculation/retrieval is exact, not that semantic interpretation is infallible. “A fast first reply” and “what a later nurture message must clarify” might share a topic while serving different reader decisions. A high numerical match can penalise such a useful direction; a low match can miss a paraphrase. Calibrate the signature and thresholds on labelled examples and expose the matched arguments to human review. Do not promise perfectly automatic semantic distinctness.

The user's very-close wording—“then only include both relevant ones”—is preserved as an unresolved **selection/display instruction**, not interpreted as permission for a judge or an automatic duplicate ban. Ask whether both means the historical/new comparison pair, two current qualifying angles, or both retained in the weekly selectable set; see I-01 in the [ledger][call-ledger].

## 9. Recency-aware historical score reduction

### 9.1 What the user's recency requirement means

For this slice, the penalty depends on when a similar **angle was generated**, whether or not that historical angle was selected. Store publication and approval separately; neither should secretly replace the generation clock.

Unselected valid proposals therefore contribute to historical overlap, as requested. Their status/rejection reasons remain visible for editorial interpretation. Do not mix unrelated off-brand/privacy rules into an unexplained recency number.

Within one current generation cohort, use pairwise set selection instead of historical age penalties. Otherwise all sibling candidates have nearly zero age and whichever was saved first receives an unfair advantage.

### 9.2 Recommended deterministic formula

This formula is a proposal to calibrate, not a claim that its parameters have been approved or empirically validated.

For candidate `a` and eligible historical match `h`:

```text
s(a,h) = cosine similarity in the compatible angle-signature space
tau = calibrated historical relatedness retrieval threshold, with tau < 1

overlap(a,h) = clamp((s(a,h) - tau) / (1 - tau), 0, 1)

age_days(h) = days between h's genuine generation event and score_as_of
freshness(h) = 2 ^ (-age_days(h) / half_life_days)

pair_risk(a,h) = overlap(a,h) * freshness(h)
historical_risk(a) = max(pair_risk(a,h) for eligible h), or 0 if none

penalty_points(a) = base_quality(a) * max_penalty_fraction * historical_risk(a)
adjusted_score(a) = base_quality(a) - penalty_points(a)
```

Require positive half-life, a bounded penalty fraction in `[0,1]`, compatible profiles and valid historical generation times not later than `score_as_of`. Missing/future timestamps are data problems to review, not silently normalised into trustworthy recency.

Why this structure:

- Holding base quality and age fixed, a larger similarity increases the reduction.
- Holding base quality and similarity fixed, a more recent generation increases the reduction.
- Older matches decay gradually rather than expiring at an unexplained cliff.
- The penalty is bounded; it cannot create a negative score.
- The base score remains inspectable and is never overwritten.
- The formula uses only available numerical inputs; it contains no hidden semantic-relation multiplier or third LLM assessment.

This revision removes the earlier proposed `relation` coefficient. Without an allowed semantic judge, granting a zero penalty to a supposedly “different contribution” would rely on an unestablished classification. The baseline instead treats qualified numerical matches consistently. A shared-topic false positive remains possible and inspectable; calibrate signatures/thresholds and track any explicit later human override as a separate decision, not silently inside base quality.

At exactly `s = tau`, the pair is retrieved but its continuous overlap is zero; similarity above the threshold increases the contribution. Keep raw values for arithmetic and round only for presentation.

### 9.3 Why strongest-match aggregation rather than summing every match

The simplest safe initial aggregation is maximum pair risk, after deduplicating revisions/representations. A candidate can be extremely similar to a very old angle and moderately similar to a very recent one; evaluate both products before choosing the maximum. The highest raw cosine match is not necessarily the dominant penalty.

Summing all retrieved records would punish a candidate merely because one old idea has many paraphrases/revisions in the database. It would also change rankings as retrieval page size changes. Maximum risk avoids that multiplication while respecting the most significant similarity/recency combination.

For a logical argument family with several genuine past generations, retain the event history and compute the strongest eligible contribution. Re-embedding, metadata edits and retried requests do not refresh generation recency. An intentional repeated generation in a prior cohort does create a new event; exclude the current cohort consistently.

Repetition frequency across independent old proposals could become another explicitly calibrated feature later, but is not hidden inside this initial maximum formula.

### 9.4 Worked example

Illustrative parameters only: relatedness threshold `0.78`, half-life `28 days`, maximum penalty fraction `0.50`.

| Candidate | Base quality | Similarity / age of dominant numerical match | Numerical treatment | Penalty points | Adjusted score |
|---|---:|---|---|---:|---:|
| A | 92 | 0.96 / 7 days | Qualified recent match | 31.65 | 60.35 |
| B | 88 | 0.90 / 56 days | Qualified older match | 6.00 | 82.00 |
| C | 84 | No qualified match | No matched-history contribution | 0.00 | 84.00 |
| D | 91 | 0.94 / 2 days | Qualified very recent match | 31.49 | 59.51 |

The numbers are calculated examples, not corpus/model evaluation results. Before current-pair selection, the adjusted order is C, B, A, D. High base quality does not conceal a very recent high-similarity match. D no longer receives an unproved semantic exemption: if a reviewer sees a useful distinct contribution, that flags calibration/explicit review, not a hidden LLM classification.

An illustrative visible threshold of 70 would admit B and C on score and exclude A and D from automatic score-qualified visibility; current-set checks still apply. The test is strictly `adjusted_score > 70` using unrounded values. All four remain saved and inspectable; there is no requirement to fill four slots.

### 9.5 Temporal and evidence qualifications

- Use generated-event dates, not `updated_at`, embedding time, import time or meeting time.
- A previously generated argument about an older transcript can still be recent editorial work.
- Imported historical content with unknown generation time must not be dated “generated today” merely because it was imported today. Retain known publication time separately and treat recency uncertainty explicitly.
- A strongly overlapping historical match with missing timing may require review before claiming the new angle passed freshness. Do not quietly treat unknown age as ancient.
- New evidence can improve base quality and justify consideration, but it does not automatically erase a numerical match/recency penalty. A changed reader contribution is documented in the structured angle; it is not an automatic semantic exemption from this deterministic formula.
- Fix `score_as_of` for a selection run. Opening the page tomorrow should not silently mutate the saved ranking; a deliberate rescore produces a new ranking revision.

## 10. Select a high-quality distinct current set

### 10.1 Three separate decisions

1. **Admission:** is the candidate sufficiently grounded, source-related and eligible to consider?
2. **Historical ranking:** how much should recent similar generation reduce its base quality?
3. **Current-set selection:** which candidates can be shown together without repeating the same contribution?

Historical reduction alone does not solve intra-week duplication. Sorting scores and showing every candidate above the threshold could still display several high-quality rewrites of one argument.

### 10.2 Current pairwise comparisons

Compare all admitted candidates in the current cohort, including earlier physical generation batches. Reuse signatures and exact cosine calculations, but keep these comparisons separate from historical age penalties. Store exact-representation matches and threshold-qualified close pairs with the numerical rule/version that identified them.

A raw close-pair flag is not a confirmed same-argument label. The desired editorial distinction remains independently supported reader contributions, not different hooks/audience labels. **The automatic disposition of very-close pairs is not final until I-01 is answered.** Do not implement a greedy one-winner suppression rule or a keep-both exception as if either had been approved.

Near-neighbour retrieval can shortlist current pairs when volume grows, with tested coverage. For a modest pool, exact/blockwise pairwise comparison is simpler to audit. Unlimited candidate generation does not remove the need to handle quadratic comparison cost with explicit operational budgets/completeness state.

### 10.3 Do not treat similarity as transitive

If A overlaps B and B overlaps C, that does not prove A overlaps C. Do not automatically merge an entire connected component of an embedding-neighbour graph into one “duplicate cluster.” A and C may both belong in the visible set.

Use actual pair records, not connected-component membership. Exact repeated representations can be deduplicated as representations while retaining their angle/event records; raw similarity chains cannot establish semantic-equivalence families.

### 10.4 Selection contract and remaining close-pair decision

The resolved part of selection is reproducible:

1. Exclude candidates failing admission or required memory/context readiness, retaining their status/reasons.
2. Compute historical adjusted scores at the frozen cutoff.
3. Keep candidates strictly above the configured visible threshold, using unrounded scores.
4. Order by adjusted score, then grounding/source relevance, then a stable ID for ties.
5. Compute and persist current-pair matches across the full admitted cohort; expose comparison records and any existing pinned choices.
6. Apply the explicitly agreed close-pair policy once I-01 is resolved; record selected/suppressed/review-required dispositions and the responsible pair/rule.
7. Surface every eligible distinct passing candidate; pagination can split the list, not remove eligible candidates.

Before I-01 is resolved, this is a specification with an open selection branch, not a fully executable algorithm. Preserve affected candidates and pair evidence; do not represent a draft unresolved set as a final automatically distinct selection.

If the eventual rule suppresses conflicting current candidates, a stable score-ordered greedy selection is an auditable starting heuristic, not a global optimum. If the intended rule keeps both relevant close angles, define the relevance/distinctness condition and whether it covers historical/current pairs or current/current pairs before implementing it. Close history remains a ranking input; it is not automatically promoted into this week's new candidate pool.

Keep historical-adjusted score separate from current-pair disposition and any explicit human override. A candidate's source quality does not become “weak evidence” merely because it has a close match.

### 10.5 Confirmed final visible count

The user chose **threshold mode: every qualified distinct angle strictly above the adjusted-score threshold**. No fixed four-angle portfolio is the default or an unresolved choice in this slice. A good week may show more than four; a weak week may show fewer or none.

Do not impose a hidden display cap through nearest-neighbour top-k, API page size, prompt quotas or a later pack-capacity assumption. Visibility still awaits founder review at Gate 1; it does not authorise writing or public use.

## 11. Minimum persisted domain contracts

Use these evidence/memory responsibilities from the vector-storage design; they do not require a separate table for every row. For the user-selected first testing phase, versioned JSON records are authoritative, Markdown is the review/decision layer, and local pgvector is a minimal rebuildable search projection. The eventual full typed PostgreSQL schema is not determined by that scratch projection. Stable IDs, provenance, validation, permissions and dependency contracts are still required now. [File-backed testing design][testing-design]

| Record | Required responsibility for this slice |
|---|---|
| Editorial cycle / run | Weekly window, frozen source/memory scope, versions, readiness and final selection revision |
| Source / source revision | Logical conversation identity, exact content version, original locator, permissions and completeness |
| Segment / source turn | Exact raw/normalised text with IDs, speaker/role, sequence and timestamps |
| Extraction attempt / moment | Input coverage, retained context, structured insight, qualifiers, claim references and readiness |
| Claim / evidence link | Source-supported proposition, attribution/units/period, exclusions and verification dimensions |
| Topic / moment-topic link | Coherent aggregation and inspectable recurrence without erasing differences |
| Angle / angle revision | Every valid candidate, structured signature, generation lineage, base score and exact dependencies |
| Embedding representation | One active vector per angle; compatible profile/projection/version/hash, retained paid artifact and readiness |
| Similarity match / pair record | Historical/current/previous-turn set, exact cosine, numerical band/rule version, age, structured signatures and risk contribution |
| Ranking revision | Base components, penalty inputs, adjusted score, cutoff/configuration and dominant match |
| Selection / selection item | All-qualified display contract, close-pair policy version, selected/suppressed/review-required state, rank, reasons and coverage |
| Work attempt / intent | Idempotent processing, checkpoints, retry/lease state and errors |

Production historical eligibility includes genuine persisted prior candidate generation, regardless of selection/publication; exclude mocks, malformed outputs, revoked/inaccessible representations and duplicate retries. In backfill testing, admit real generated candidates only from the explicit experiment branch/history snapshot. Other A/B branches and future weeks are excluded without deleting their artifacts. A stored proposal is never independent factual evidence.

Retain every candidate's disposition: visible, quality-below-floor, current-overlap-suppressed, history-penalised, pending-context, pending-permission, pending-memory, or superseded by intentional regeneration. Use exact states/reasons rather than deleting everything except winners.

The structured operational records are authoritative: validated JSON in the initial testing mode, then typed relational records after migration. Scores, timestamps, permissions and approved/pinned choices are not enforced by retrieving embeddings. Restore vectors from retained artifacts; provenance/decisions are not disposable cache data.

## 12. Prompt and validation requirements

### 12.1 Call 1 prompt contract

Provide meeting purpose, exact turn/source IDs, role uncertainty, relevant active policy and the entire permitted transcript/context portion. Ask for content-worthy source passages, meaning-complete context, relevance, factual scope, exclusions and permission questions. Permit zero moments.

Prohibit fabricated quotes/timestamps, treating staff praise as a direct testimonial, deleting qualifications, and following instructions embedded in the transcript. Require only concise externally inspectable rationale and the source references needed to validate the result.

### 12.2 Call 2 prompt contract

Provide admitted moment/context packets, source-supported claims, audience/voice policy, current factual offer boundaries if relevant and current-cohort signatures from earlier physical batches. Request all substantive supported directions, not a fixed number; permit no additional angles when evidence is exhausted.

Ask for reader contribution, source mapping, limits, differences from other supplied candidates, and anchored quality assessments. Do not reward general marketing knowledge that is not supported by this week's material. No finished assets or automatically chosen CTA are required here.

The user's required baseline generates from weekly evidence before historical memory scoring. Earlier documents recommended historical retrieval before generation; keep that as a separately selectable enhancement, not an unannounced requirement in this two-stage baseline. Historical and publication-memory context must still be labelled as history, never source proof, if later added.

### 12.3 Structured output and bounded repairs

Validate schema and score ranges, permitted IDs, source context, quote/value/attribution fields and declared coverage. Treat missing/invalid output as a visible stage failure or bounded repair, not a successful empty week.

If a response is truncated, retain only safely validated completed units through the designed response protocol; do not parse arbitrary fragments into invented records. Repair/retry attempts preserve request identity and coverage state. A model's self-declared `complete` must agree with the application's input-coverage ledger.

A claimed quotation and a useful paraphrase both need source support. Direct string matching is insufficient to approve interpretation; unresolved central meaning remains withheld or explicitly review-required.

### 12.4 Provider/model choices remain configurable

Pin evaluated model/prompt/schema/profile identities per logical stage. Use structured output, budgets, approved privacy/routing, and versioned policies. No exact model ID, price, context limit or throughput is selected in this document.

Evaluate candidate-generation and moment recall on representative weekly material before choosing production models. Do not infer that a stronger model eliminates the need for provenance, or that two models automatically provide independent verification.

## 13. Execution, re-runs, and incomplete states

Use the existing proposed modular Python backend boundary and shared domain models. RQ/Redis can carry work while Postgres keeps durable input/output/decision state; this does not require a new workflow platform. No deleted backend is restored by this design task. [Earlier infrastructure/durability review][architecture-review]

That is the broader infrastructure proposal, not a prerequisite for the first local experiment. The initial harness can use single-writer file-backed attempts/checkpoints and a scratch pgvector projection while the production schema is refined. Preserve exact paid request/returned response/usage artifacts before parsing/DB writes; use fingerprints, exclusive leases, compatible replay and explicit billing-unknown states. A cache hit/threshold rescore is not a fresh generation event. See the dedicated preservation/reuse contract in [testing design §8][testing-design].

An orchestration outline, not implementation code:

```text
freeze weekly source scope and prior memory cohort
normalise/version all eligible transcripts; record missing coverage
extract and validate moments/context for every eligible source interval
assemble and track the admitted week-wide evidence pool
generate candidates across resumable evidence packs
persist every valid candidate and compatible signature embedding
retrieve threshold-qualified historical/previous-turn matches
compare current candidates numerically; record close pairs under the agreed policy
compute generation-recency penalties at a fixed cutoff
select and persist qualified non-conflicting candidates
expose weekly angle cards with evidence, matches and score explanations
```

Required safeguards:

- Source/extraction keys include exact source revision and processing/policy version.
- Generation keys include cycle, evidence snapshot, run request, evidence-pack/coverage identity and generation versions.
- A retry shares the logical request; an intentional regeneration gets a new request with lineage.
- Embedding keys include angle revision, signature/projection version and compatible profile.
- Ranking keys include candidate-set revision, frozen history/cohort, numerical match-policy version, score cutoff and score-policy version.
- Selection keys include ranking revision, close-pair policy/pinned choices, quality floors and the all-qualified display contract.

Commit durable intent/checkpoints; claim work before expensive operations; do not accept stale results over newer source/run revisions. Cache completed valid work. Reconciliation should not regenerate completed output or pretend Redis presence proves completion.

Expose pending/failed extraction, generation, embedding, history retrieval and unresolved comparison-policy/review states separately. No LLM semantic-review job exists. If memory is unavailable, preserve base scores and candidates but mark freshness unchecked; do not substitute a fabricated zero penalty and display a supposedly vetted selection.

For partial transcript coverage, distinguish visible provisional candidates from a completed weekly selection. For an empty evidence week, return an honest no-qualified-angles result. For insufficient distinctness, return fewer with explanations rather than padding. All these are valid product outcomes when correctly labelled.

Permission/source changes after snapshot creation still restrict processing and invalidate affected dependencies. Frozen history provides reproducibility, not permission to access material after revocation.

## 14. The weekly angle-card/read-model contract

The visible card should make the decision understandable without exposing raw private data to an unauthorised viewer:

- Title, argument, audience, tension and reader contribution.
- Primary source passage plus surrounding context; supporting/counterpoint sources.
- Source and speaker confidence, claim limitations and public-use requirements.
- Base quality and its component/reason breakdown.
- Historical penalty points and adjusted score.
- Dominant recent numerical matches, generation dates, raw similarity and both structured arguments/source references; distinguish observed differences from confirmed semantic labels.
- Current-set conflict/suppression explanation where applicable.
- Rank, selected/review-required state, weekly coverage and memory completeness.

Keep the full threshold-match audit available behind a detail view; the card can show the dominant/relevant few without truncating the underlying scoring computation. Do not label numeric similarity as proof of sameness or a composite score as predicted engagement.

The current frontend's `ContentIdea` has a composite `score`, a different breakdown, a single primary quote and existing source context. It does not yet encode all this new base/penalty/cohort contract. Design an API/read-model adapter rather than stuffing new meanings into existing mock values or silently assigning demand/novelty scores. Existing frontend mocks and sourced demos remain excluded from generated-history scoring unless deliberately used in tests. [Current frontend type contract][frontend-types]

Displaying the selected set leaves it at Gate 1. Founder acceptance, chosen CTA and later research/brief/pack stages remain separate commands beyond this slice.

## 15. Acceptance tests before building beyond angle selection

### 15.1 Evidence and moment recall

- Every in-scope transcript/interval has a processed or explicitly incomplete/excluded outcome.
- One interesting passage near the end of a long meeting is not lost to context/output truncation.
- Context includes a later correction, attribution qualifier or estimate marker when it changes the anchor's meaning.
- Multiple exports/chunks of one conversation do not inflate independent recurrence.
- Staff report, client quote and hypothetical example stay distinct.
- Unknown attribution is not silently promoted to verified speaker identity.
- The ten-week posting and ad-attributable booking cases preserve the corpus's actual argument/limits.

### 15.2 Generation relevance and coverage

- A relevant moment can produce zero, one or several substantive angles without a forced count.
- Cosmetic hooks for one contribution are not admitted as separate distinct arguments.
- All admitted moments receive explicit generation consideration/omission records, including multi-pack runs.
- Cross-transcript combinations preserve client/period/source boundaries.
- Strong generic advice without an actual weekly source link fails admission despite an inflated self-score.
- Source IDs/quotes invented by a model are rejected; invalid attempts do not become successful empty outputs.
- A larger candidate pool is not silently clipped to four; a weak week is not padded to four.

### 15.3 Memory and recency

- All valid candidates persist and have explicit embedding/search readiness before filtering.
- Self/current-cohort/retry records do not create historical age-zero penalties.
- The previous completed run's eligible IDs are included once; earlier physical current-run batches are not historical.
- Threshold retrieval excludes below-threshold nearest rows and does not lose an important recent match behind top-k truncation.
- Same dimensions from an incompatible profile cannot be compared.
- Numerical matching never invokes an additional LLM judge or invents a zero-penalty semantic classification; high-cosine shared-topic false positives are inspectable calibration cases.
- Holding other inputs fixed, penalty increases with similarity and with recency.
- Duplicating historical revisions does not multiply the maximum penalty.
- A more recent moderate-similarity match can dominate an older higher-similarity match.
- Import/re-embedding/update time does not replace actual generation time.
- Missing timing/memory is marked uncertain, not assumed safely fresh.

### 15.4 Selection, reproducibility, and review

- Raw-neighbour chains do not automatically force transitive duplicate groups.
- Several current rewrites cannot fill the visible set just because all have high scores.
- Rerunning identical ranking inputs/cutoff yields identical arithmetic/order; this is not a promise that a fresh model call reproduces identical prose.
- Accepted/pinned choices survive a scoped regeneration, where that behaviour is selected.
- Base score, penalty, final score and suppression reasons remain inspectable.
- Every eligible distinct candidate strictly above the unrounded adjusted threshold is visible, including sets larger than four; threshold equality fails and pagination does not truncate selection.
- Very-close pair handling matches the explicitly agreed I-01 rule; no unresolved rule silently suppresses or admits both records.
- Embedding/history failures or unresolved close-pair dispositions cannot silently produce a “fully vetted” set.
- Revoked evidence invalidates affected candidates/readiness even under a frozen snapshot.

Use held-out weekly fixtures and labelled angle pairs. Historical simulations must use the evidence and angle history available at that simulated time; future generated/published records and desired answer packs must not leak into the setup. Compare source-grounding precision, missed meaningful moments, numerical-match false positives/negatives against human labels, selected-set redundancy and Whitney's editing/acceptance effort. Do not optimise for the model's own high scores or scraped engagement counts.

## 16. Confirmed decisions, client ledger, and readiness

The user's answers resolve the earlier cardinality, previous-turn, additional-judge and source-scope questions:

| Decision | Confirmed position |
|---|---|
| Final visible set | Every eligible distinct angle strictly above the adjusted-score threshold; no four-angle cap |
| “Last turn” | Previous completed generation run, including intentional same-week regeneration |
| Additional similarity LLM judge | Not allowed; exact compatible-vector comparison and deterministic score rules |
| Initial weekly inputs | Transcripts only; Slack deferred |
| Weekly timing | Saturday morning 04:00 Texas time, provisional for client confirmation |

One user phrase is still ambiguous: **“incase its a very close similarity then only include both relevant ones.”** Ask whether “both” means displaying the old/new match pair for comparison or retaining both as selectable weekly angles, and whether the rule also covers two current candidates. I-01 in the [next-call ledger][call-ledger] preserves this without inventing a decision.

The ledger separates client-confirmed operating facts from user requirements and engineering calibration. It indexes preparation documents and future `meeting_YYYY-MM-DD.md` records with agenda, actual answers, authority and document updates. No meeting date or client answer is manufactured.

**Readiness:** the architecture and main stage contracts are ready for the remaining clarification discussion, but implementation should not start yet: the user explicitly has further clarifications, and close-pair selection is not final. Source hosts/access/permissions are needed for live ingestion; weekly timezone/window/late-arrival rules are provisional; numerical floors, decay and thresholds need representative fixture calibration. These are not all reasons to block a later authorised offline prototype, but they must not be claimed as settled production behaviour.

The generated-recency requirement is understood: genuine prior generated angles count, not only published pieces. Two logical LLM stages may use bounded physical batches for coverage; no third similarity reasoning stage is added. Numerical examples remain proposals, not client-approved settings.

The new testing requirements are confirmed; exact first Zoom week/export coverage, model/profile choices, budgets/privacy routes and named historical-simulation/branch policy still need configuration or confirmation. Historical testing stores actual execution and explicit simulated generation dates separately; it must not present backfilled model output as truly generated in the past. “Final generation” meaning is open in ledger I-07. [Testing design][testing-design]

## 17. Build sequence for this slice only

1. **Contract/fixtures:** finish the user's remaining clarifications and close-pair policy; preserve confirmed transcript-only/all-qualified scope; configure provisional weekly boundaries explicitly and prepare authorised transcript examples and held-out moment/angle-pair labels.
2. **Batch foundation:** source identity/revisions, coverage manifests, turn/context references, normalisation and source search representations.
3. **Call 1:** structured extraction, context rehydration, claim/speaker/permission checks, persistence and full input-coverage ledger.
4. **Call 2:** source-grounded candidate schema, unrestricted substantive generation across bounded batches, quality components and validated base arithmetic.
5. **Angle memory:** persist/embed all valid candidates, compatible profiles, historical/current/previous-turn cohorts and exact threshold-match records.
6. **Ranking/selection:** exact numerical matches, generated-recency decay, maximum-risk aggregation, strict quality threshold and the explicitly agreed close-pair policy; no additional LLM judge.
7. **Weekly review read model:** expose evidence, score/match explanations, coverage and uncertainty through the existing frontend/API boundary.
8. **Acceptance/recovery:** verify replay/idempotency, missing-input/provider failures, withdrawals, profile compatibility and source-faithful selection before proceeding to briefs.

The initial user-facing milestone is successful only when it can explain why each visible angle is grounded, useful, sufficiently fresh and distinct from the other visible angles—and honestly report when it cannot establish those conditions.

## 18. Relationship to earlier documents and limits of this review

This latest specification narrows the broader architecture to transcript intake through weekly angle visibility. It preserves one Postgres database, exact evidence/provenance, founder authority and no autonomous downstream generation.

Where requirements differ from earlier recommendations:

- Candidate generation is explicitly uncapped by count; operational safety budgets are still real.
- Final visible count is now confirmed as every qualified distinct candidate above the adjusted-score threshold, superseding the earlier four-angle target.
- “Last turn” is confirmed as the previous completed generation run; first inputs are transcripts only.
- The additional semantic LLM judge is prohibited; the default penalty uses numerical overlap and recency without an unestablished semantic multiplier.
- Saturday 04:00 Texas timing is provisional and tracked for client confirmation in the next-call ledger.
- Generation recency is the requested penalty clock; publication history stays separate.
- The required baseline checks historical memory after generation; pre-generation memory retrieval is optional enhancement.
- Historical freshness is a score reduction, not an automatic permanent duplicate ban. Current-set redundancy is handled separately.

The formulas, weights, floors and example table are proposed design choices. Example arithmetic was independently checked; no real model evaluation, transcript processing, migration, connector or database implementation was performed. Existing backend deletions and frontend changes were preserved. The supplied architecture remains unchanged; the vector-storage reference is amended to reflect the latest scope/count decisions. Earlier versions are retained in context snapshots.

Design verification for this revision: 142 arithmetic/design checks passed for the numerical-only formula, including bounded scores, similarity/recency monotonicity, no-match risk zero, the retrieval-threshold boundary, maximum-risk rather than duplicate-summing, and the strict visible-threshold comparison. The example table was independently calculated, and the five quality weights sum to 1.0. These are arithmetic/design checks, not production pipeline tests, calibrated semantic accuracy or an implemented close-pair policy.

## Sources

- [Supplied solution architecture][architecture]: original source/moment, weekly generation, memory and data-model proposals.
- [Vector-storage design][vector-design]: typed evidence/memory boundaries, claims, revisions, embeddings and permissions.
- [Next-call and meeting ledger][call-ledger]: user decisions, provisional weekly timing, client questions, unresolved close-pair wording and future meeting-record index.
- [Corpus/editorial review][taste-review]: source authority, factual hazards and Whitney's editorial preferences.
- [Reconciled architecture review][architecture-review]: scoped claims, generation contracts, freshness clocks and durable work.
- [Current frontend types][frontend-types]: existing read-model shape, not an implemented backend guarantee.
- [Official pgvector documentation][pgvector]: cosine distance/similarity and exact versus approximate retrieval, checked 7 October 2026. Installed capability/configuration remains to be verified when building.

[architecture]: <Content-Atelier-Solution-Architecture.md (outside the repository)>
[vector-design]: <../content_atelier_vectordb.md>
[taste-review]: <../research/whitney-taste-and-editorial-pipeline.md>
[architecture-review]: <../research/architecture-comparison-and-reconciled-design.md>
[frontend-types]: <../frontend/src/types/atelier.ts>
[pgvector]: https://github.com/pgvector/pgvector
[call-ledger]: <../to_be_asked_in_next_call.md>
[testing-design]: <../content_atelier_week_by_week_testing.md>
