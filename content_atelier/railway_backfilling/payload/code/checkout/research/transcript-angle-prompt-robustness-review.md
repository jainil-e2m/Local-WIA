# Corpus-grounded review of the two Content Atelier prompts

Prepared 7 October 2026. Prompt release: `2026-10-07.gpt-oss-120b.transcript-angle.v2`.

Layout amendment, 8 October 2026: the user requested backend-local organisation while this review was being finished. The package, prompts, evaluation cases and tests now live in `content_atelier/backend/backend_pipeline/`; setup/configuration template and execution README live in `content_atelier/backend/`. Project-level research, context and `testing/.data/` are retained. The package name and prompt release are unchanged by the move.

Verification, 8 October 2026: 43 offline tests passed after relocation; Ruff lint/format checks, Python compilation and CLI help also passed. No real inference, embedding payment, new credential read or live database integration test was performed. See [execution and configuration instructions](../backend/README.md).

## 1. Outcome and honest readiness

The initial prompts were directionally correct but insufficiently specific to Whitney's taste and insufficiently coupled to the output validator. Both stages have now been revised, with a curated editorial policy, complete nested response contracts, explicit coverage/source checks, actual context in Call 2, grounded scoring anchors and reproducible signature construction.

This is a substantially stronger **first calibration release**, not proof that GPT-OSS has learned Whitney's judgment. Offline tests verify software contracts, persistence and known structural failure cases. No real provider response was generated or assessed in this review. Client approval of the inferred policy and empirical output quality remain separate.

There is also a concrete execution constraint: Week 1 is too large to treat as an unbounded request without a tested input/output budget. A conservative preflight now stops an oversized live request before calling a provider. Bounded weekly batching is still needed; longer prompts cannot repair this orchestration issue.

## 2. Authority and scope

The current user requirements govern the release: transcripts only; two logical LLM responsibilities; every useful grounded candidate, no count cap; one canonical embedding per angle; deterministic history/similarity/recency handling, no additional LLM judge; JSON artifacts retained for compatible reuse; angles stop at internal human review. The original four-angle target in the earlier taste review is superseded. No briefs, finished assets, offer selection, CTA, scheduling or public reuse is authorised here.

For taste, explicit founder corrections have stronger authority than assistant drafts or consultant ideas. The voice guide describes the stable attitude and thinking style. Published examples demonstrate execution, but are not automatically accurate proof, current commercial promises or approved rules. A recent correction may have a narrow format scope: September caption rhythm restrictions should not be misrepresented as a ban on every concise working title or old slide headline.

This review revisited the existing broad corpus analysis and checked primary founder guidance, corrective conversation turns and representative published examples. It did not newly inspect every raw export, all original slide images or playable reel audio. Long draft-filled conversations were reviewed through relevant corrections/excerpts. Existing visual/audio coverage limitations remain; no performance conclusion was drawn from likes or delivery counts.

## 3. What the corpus changes in the prompts

| Evidence | Editorial requirement | Consequence for these two stages |
|---|---|---|
| Founder Voice Guide v2: strategic thinking, calm confidence, principles before tactics | The intellectual product is a better decision, not an ads tip decorated with brand vocabulary | Call 1 favours consequential choices; Call 2 requires a tension, take, mechanism and reader decision |
| June market-research corrections: too many liberties, planned service mistaken for current delivery | Persuasive clarity must preserve the source's truth conditions and task ownership | Claim-status enums, qualification retention, correction-bearing context; no invented current offer |
| July attribution case and August clarity revisions; published July email | Unknown prior results are not zero; attributable bookings are not all revenue; unequal cost bases are not a clean comparison | Explicit subject/period/cost/attribution boundaries, source assertions and exact surrounding passages |
| June autopilot revisions | A coordinated acquisition system and strategic investment matter; LeadLock is not the entire explanation | Preserve multiple interventions and human consultations; do not imply WIA handles all marketing |
| August founder correction and ten-week carousel/email | The owner was already a good marketer; capacity is the tension, not neglect | Preserve competence, existing foundations and relief without rejecting organic marketing |
| September UVP email and workshop-reel revisions | Show depth and genuine commercial transformation, without requiring prospects to finish the work before joining | Explain the buyer decision and potential business consequence; distinguish guidance, initial setup and ongoing client tasks |
| July clip/caption corrections and September caption directive | Generic corrective contrasts, repetitive phrases and staccato copy obscure the genuine insight | Natural internal prose; concrete titles; no phrase-bank imitation; exact quotes exempt from paraphrase restrictions |
| Knowledge-base and carousel warnings | An estimate, cross-client combination or attractive published claim can still be wrong | Do not calculate new proof, combine outcomes or import old metrics as current evidence |
| Savannah strategy, interpreted through Whitney's corrections | Frameworks support the argument but must not override evidence or capable audience framing | Strategic lenses, not quotas, aggressive rhetoric or mandatory Attract/Warm/Convert buckets |

These changes encode what the examples repeatedly protect, not merely their surface phrasing. The intended outcome is an angle Whitney can recognise as worth developing without first repairing the audience, chronology, commercial ownership or central claim.

## 4. Call 1: preserve evidence before persuading

### Its job

Call 1 selects passages containing a transferable decision, mechanism, objection, tension, observation or properly bounded result. It does not summarise the meeting, generate hooks or optimise for a dramatic number. A routine technical exchange can reveal a good decision; a spectacular metric can be unusable without sufficient interpretation.

Selection asks, in effect: what does this passage let a wedding-business owner understand that would matter to a real decision? The permitted lenses include buyer confidence, messaging, positioning, landing-page experience, follow-up, measurement, foundations and sustainable capacity. They are not a compulsory list of topics. Unsupported emotional diagnoses, invented pain and generic advice remain excluded.

### What travels downstream

Each moment has a literal anchor quote, source IDs, contiguous context, a factual summary, bounded proposition, audience relevance, claim status, handling label, qualifications, strength and concise reasons. Numerical qualifications must preserve the subject, period, measure, comparison, attribution and costs where available; they must identify meaningful missing information rather than manufacture a value.

The full week is not the right context unit for every moment, nor is a fixed number of seconds. The useful interval includes enough setup and resolution to preserve meaning, including later corrections that change the claim. The prompt asks for the smallest sufficient interval. The validator enforces that supplied context includes the anchors, is chronological and contiguous, and stays within one source. It cannot prove the model selected every semantically necessary turn; that is an evaluation obligation.

The quote must be a nonempty literal substring of an anchor. Multiple anchors can support a proposition, but the quoted string cannot stitch unrelated turns. Grammar, restricted words and em dashes in genuine evidence are preserved. Voice preferences apply to generated paraphrases, not to editing the historical record.

### Status and handling

The distinctions reported, measured, estimated, planned, hypothetical and inferred are explicit. A speaker saying a number was measured, without the measurement record, still supplies reported evidence. A planned process can be useful as a process decision, but not as proof of delivered service or results. Mixed passages preserve additional distinctions in qualifications.

Speaker labels are unverified, not reliable proof of founder identity. A named client is not public consent. The three sensitivity labels describe internal handling concerns and candidacy, never publication approval. Public candidacy requires evidence in the packet rather than a model deciding that anonymisation is sufficient.

### Coverage and valid emptiness

Every supplied span must be acknowledged exactly once, whether shortlisted or excluded. A zero-moment result is valid and needs an explanation; it must not trigger quota filling. Coverage IDs are a mechanical acknowledgement, not proof of semantic understanding. The review now uses `coverage: acknowledged` and counts rather than a self-certifying complete label.

## 5. Call 2: turn evidence into a distinct contribution

### Actual context, not an interpretation-only handoff

Previously Call 2 received the quote and Call 1 summary, but not the actual surrounding turns. That made a mistaken summary easier to amplify. The new moment packet includes exact source_evidence, timestamps/ordinals/speaker labels, source revision hashes and explicit unverified identity status. The strategist can inspect the passage rather than treating the previous model's interpretation as authority.

Current source evidence supplies facts. The editorial policy supplies a lens. Prior signatures, if supplied, provide overlap context only. They do not prove a client's result, service availability or publication history. The current orchestrator sends no prior signatures into Call 2 and compares history later in code; an empty list is not evidence of no prior content.

### The semantic spine

An angle must state who it serves and in what state, the recognisable tension, its central argument, the belief shift, why it follows, and the owner's next decision. The working title names the concrete issue rather than pretending to be final cover copy. It should survive without the story's most eye-catching metric.

The mechanism is especially important. “Build better systems” does not reveal Whitney's thinking. Explaining how a useful comparison answer reduces a couple's uncertainty, or how attributable bookings inform the next campaign decision, does. The supported business consequence should be visible without a promise of guaranteed growth. The prompt avoids two opposite failures: generic clarity with no meaningful consequence, and overstated performance certainty.

The source_assertions list distinguishes what the passage supports from a separately labelled inference. Each assertion identifies a supporting current moment. This is a provenance check, not automatic semantic entailment: a syntactically valid reference could still accompany a false sentence. Human/source evaluation remains essential.

Upstream qualifications and sensitivity labels are also carried into stored angles by code, even if Call 2 omits them. A flattering rewrite cannot silently remove these internal constraints. The current free-text qualification format is useful for calibration but is not yet a full typed numerical claim ledger.

### Distinctness, not variation

The prompt compares audience state, belief shift, mechanism and reader decision. Different headlines, formats, emotional adjectives, offers or client names do not necessarily create different angles. One case can support two contributions if the evidence genuinely explains two different decisions. A shared theme such as buyer confidence is not automatically duplication.

For example, an attribution discussion can support a measurement decision and a support-versus-isolation decision if both are present in its context. “Know what works”, “Confident advertising” and “Marketing clarity” are one contribution when all three merely recommend the same measurement change.

There is no minimum or maximum candidate count. No implicit four-item cap or one-angle-per-moment rule is introduced. The model must omit unsupported or shallow variants, acknowledge every supplied moment and explain relevant exclusions. It does not calculate numerical similarity, apply generation recency, invent novelty/demand scores or select the final visible set.

Exact identical canonical arguments fail local validation, even under different titles. Paraphrased near-duplicates still need the intended deterministic numerical stage and editorial calibration. The existing ranker is not a completed within-run semantic deduplication/very-close-pair policy; prompt wording is not a substitute for that unfinished requirement. No extra LLM judge was added.

### Scores that mean something inspectable

The five existing dimensions remain grounding, source relevance, audience fit, specificity and editorial usefulness, on 0–5 anchored scales. Reasons must point to the actual source and important limits. These are candidate-quality estimates, not verified founder approval, demand, engagement or predicted conversions.

A grounded proposal can score well as a proposal. It cannot score well as evidence that a planned service has already produced results. Recency is deliberately excluded from self-scores because code applies it later. A spectacular result cannot compensate for missing evidence or an unsupported central claim. Thresholds still require calibration against accepted/rejected directions.

## 6. Robustness belongs in contracts as well as instructions

The new contracts define every nested field with required types, closed objects, nonblank strings, finite bounded scores and explicit nullable inference. Missing factual fields no longer receive silent empty/default values. Local parsing rejects unknown source/moment references, duplicate IDs/local keys, invalid quotes, cross-source or discontinuous context, incomplete coverage, unsupported assertion locators and exact duplicate signatures.

The output schema is generated from the same Pydantic definitions used for local validation. This avoids a prompt requesting one object while the provider constrains another. These schema choices follow the shape described in [official structured-output guidance](https://developers.openai.com/api/docs/guides/structured-outputs); that guidance does not establish which constraints the actual OpenRouter free route supports. The route still needs an explicit compatibility test and must fail rather than silently switching models or dropping protections.

Task instructions and the curated policy stay in the trusted message, while source packets remain untrusted JSON data. Prompt rendering now replaces placeholders only once in the template. A source string containing `{{PRIOR_SIGNATURES}}` is not rewritten into unrelated historical text. This protects input fidelity; it is not proof that a model resists every adversarial instruction.

The existing OpenAI-compatible adapter and exact approved model ID are retained. No Harmony special tokens are manually embedded in prompts: [OpenAI's GPT-OSS format documentation](https://developers.openai.com/cookbook/articles/openai-harmony) describes formatting as the provider/inference implementation's responsibility when using an API. Explanations are brief selection/score rationales, not requested private reasoning transcripts. Direct task goals and structured boundaries are consistent with [official reasoning-prompt guidance](https://developers.openai.com/api/docs/guides/reasoning-best-practices), without assuming every hosted route behaves identically.

## 7. One embedding input and release/reuse implications

Call 2 no longer invents a separate embedding signature. The backend constructs one string from audience, tension, argument, take, mechanism and reader decision, normalising whitespace. Titles, channel labels, self-scores and generation timestamps do not decorate the vector input. A number present in the central semantic fields can still be included; the function does not claim to remove every incidental numerical detail or normalise paraphrases perfectly.

This reduces signature drift and preserves the agreed one-vector-per-angle representation. It does not make similarity thresholds universally reliable or prove that two paraphrases will receive the same vector.

The v2 policy/templates/full schemas change the LLM request fingerprint. Old raw responses, moments and angles remain retained, but a matching old v1 inference result is not misrepresented as a v2 result. The LLM validation compatibility version changes to 3; embedding compatibility remains at version 2. If the exact resulting signature/model/dimensions/endpoint still match a saved vector request, it remains reusable. The new canonical layout will often differ from the original free-form signature, so a future authorised test may legitimately need one new vector per changed input. No re-embedding was performed during this review.

Changing only Call 2's instructions can still reuse Call 1. Changing the shared editorial policy affects both stages, intentionally. Threshold-only changes remain inference-free. Identical compatible reruns preserve stable moment/angle IDs, original generation times and origin-run lineage. Saved v1 requests are evidence of earlier experiments, not founder-positive training labels. The previous four prompt texts are preserved in the [v1 prompt archive](../context/2026-10-07-original-v1-prompt-texts.md) for review/rollback. Restoring text alone would not roll back the new contracts; an intentional rollback would also need compatible schemas and validation.

## 8. Measured Week 1 execution risk

The current configured source directory was inspected locally without provider inference:

| Diagnostic | Count |
|---|---:|
| Transcript exports | 9 |
| Normalised spans | 3,238 |
| Source text characters | 245,115 |
| Rendered system and user prompt characters | 870,794 |
| Generated JSON-schema characters | 2,359 |
| JSON listing only the coverage IDs | 109,102 |

These are character counts, not GPT-OSS tokens. A tokenizer estimate was attempted but its local vocabulary cache was unavailable and its vocabulary-fetch request failed; no source text was transmitted by that fetch. No model-specific count or actual route usage was established. Exact limits and overhead must be verified against the selected route, not guessed from a characters-per-token rule.

The default live-request preflight is now 120,000 serialized-request characters, configurable as `CONTENT_ATELIER_MAX_LLM_REQUEST_CHARACTERS`. This is a conservative operational safeguard, not a documented model context limit or guaranteed output reserve. The full Week 1 packet exceeds it. On a miss requiring a live call, the failed attempt/request is recorded and the call stops before contacting the provider. Compatible cache hits and replay remain usable without a new request.

Do not raise the limit simply to make this packet pass. Next, implement bounded, source-aware batches with enough overlapping/correction context, coverage aggregation, duplicate-moment consolidation, stable provenance and independent attempt caches. Large moment pools likewise need bounded generation with documented completion and a global current-candidate distinctness pass. These are physical requests within the same two logical responsibilities, not permission for a third judge. Do not truncate weekly sources or coverage lists and report success.

## 9. Evaluation and refinement procedure

`backend/backend_pipeline/evaluation_cases.json` contains 14 explicitly synthetic diagnostics inspired by corpus corrections, not real generated results or fresh client evidence. They cover unknown attribution, system versus tool, capable-owner capacity, workshop depth/ownership, planned service, conditional estimates, cross-client merging, hook duplication, shared-theme distinct contributions, injection, missing attachments, empty material, historical fact leakage and specific natural expression.

The new offline tests exercise response/schema checks, literal context propagation, source isolation, qualifier/handling retention, one-pass rendering, canonical representation and the size gate. Existing nonempty counting-provider tests also check artifact reuse. These tests cannot tell us how the actual GPT-OSS route will phrase or interpret a new weekly conversation. Diagnostic manifests and invariant tests are distinct from a model evaluation.

When authority, route compatibility and bounded batching are ready:

1. Run the diagnostic inputs through the same two stages, preserving exact requests/raw responses and validated outputs under an isolated experiment branch. A real pass needs returned output, not expected-output text posing as output.
2. Have a human compare each claim with its source, label the evidence interpretation and assess the argument. Do not add an LLM similarity judge.
3. Treat fabricated claims, misleading chronology, merged subjects, lost material limits and incorrect offer promises as hard failures, not a slight score penalty. Return unresolved material for evidence/review rather than inventing a repair.
4. Assess each direction on source fidelity, real audience/state, belief shift, explained mechanism, concrete decision, substantive distinctness, commercial accuracy and natural expression. Also record missed useful moments and why some apparently strong model outputs are unusable.
5. Request Whitney's acceptance/rejection examples and reasons through existing ledger question C-08. Her judgment remains the calibration target; model self-scores do not certify fit.
6. Change one prompt responsibility at a time where possible, keep the source/history conditions fixed, compare labels and failure rates, retain both attempts and deliberately release the next policy. Do not silently rewrite prompts from model feedback or user edits.

## 10. Remaining limits and next decisions

- Bounded input/output orchestration is not implemented by this prompt review. Week 1 should not proceed as one live request.
- Mechanical coverage acknowledgement is not semantic full-coverage proof; context selection may still omit a meaningful qualification.
- The full nested schema and current adapter parameters need actual free-route verification; no current account availability or privacy authority is inferred.
- Assertion IDs establish provenance links, not entailment. Numerical and causal fidelity still require source-based evaluation; a fully typed claim ledger is future work.
- The historical/within-run numerical similarity policy, very-close keep-both behaviour, frozen comparison branches and simulated backfill clocks remain separate unfinished requirements.
- Model self-scores and the current numerical visibility thresholds remain uncalibrated. A syntactically valid angle is not automatically an adept editorial result.
- Current offers, permission/retention requirements, identities and exact weekly windows still need their existing client answers. This release invents none.

The prompts are now suitable as an explicit, source-grounded test contract. They should be judged and refined on truthful, useful directions Whitney recognises, not on the number of angles produced or whether the JSON looks polished.

## Primary local evidence

- [Founder Voice Guide](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/docs/founder-voice-guide.md>) and [Knowledge Base](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/docs/founder-voice-knowledge-base.md>).
- [Savannah's strategy](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/docs/strategy-wlf-savannah.md>), interpreted through founder corrections rather than adopted as factual claims or mandatory quotas.
- [Market-research corrections](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/chatgpt/wia-marketing-assumptions-vs-data.md>), [autopilot corrections](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/chatgpt/wia-sales-on-autopilot.md>) and [ten-week story](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/chatgpt/wia-marketing-week-of-81726.md>).
- [Attribution and chronology](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/chatgpt/from-uncertainty-to-clarity.md>), [case-study revisions](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/chatgpt/case-study-creation.md>) and [July clip/caption corrections](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/chatgpt/wia-social-media-week-of-july-27.md>).
- [UVP email development](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/chatgpt/write-marketing-email.md>), [workshop reel revisions](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/chatgpt/workshop-reel-script.md>) and [September caption directive](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/chatgpt/caption-strategy-summary.md>).
- [Published attribution email](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/emails/2026-07-31-i-honestly-have-no-idea-if-this-is-working.md>), [published capacity email](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/emails/2026-08-20-she-didn-t-post-on-instagram-for-10-weeks.md>), [published workshop email](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/emails/2026-09-16-what-i-taught-our-clients-this-week.md>) and [carousel text archive](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/instagram/wia_carousels.md>).
- [Earlier broad editorial analysis](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/research/whitney-taste-and-editorial-pipeline.md>), with its older four-angle target superseded by the current user requirement.
