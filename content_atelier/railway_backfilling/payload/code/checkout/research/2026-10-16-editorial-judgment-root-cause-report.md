# Editorial judgment failure: root-cause diagnosis and reliability plan

**Diagnostic phase only. No OpenRouter requests, no model generations, no application or prompt changes.** This report re-examines saved evidence rather than treating the earlier investigation's conclusions as ground truth. Proposed experiments below have not run and are not authorized by this report.

## A. Executive diagnosis

**The strongest supported explanation is a mismatch between the editorial decision required and the decision actually represented and evaluated.** The application develops expansive, source-grounded opportunity records. The successful IDE work compared interpretations and selected an owner-facing thought for a limited Reel slate. The earlier experiments mostly continued testing the first task and then judged it against the second. They did not directly establish whether a model can frame a supplied thought well or discriminate between strong and weak treatments of the same scene.

For the creative-refresh case, the crucial principle survives extraction and generation: new creative does not automatically justify changing a working ad. What changes is its emphasis. The model's own public justification treats adding a client-review process as making the idea more substantive. The final reviewer then calls the resulting combined management treatment familiar and skips it. **That is observable loss of focus and an unsuccessful editorial choice. It is not evidence that the model failed to understand Carmen's statement.** It also does not establish the model's hidden reason for making that choice.

Five findings materially sharpen the previous diagnosis:

1. **A generator-to-editor contract mismatch is verified.** The current user template requests a 21-field opportunity record, forbids rankings and finished hooks, and leaves format/allocation to later work. The six references were selected, expressed directions for Reels. Working titles, final creative expression and a ranked slate were not compared under equivalent instructions or candidate budgets. Eight proposals instead of three is not, by itself, a quality failure.
2. **The failed-review count overstated what could be concluded about reliability.** All sixteen calls returned parseable JSON and stopped normally. Three failed additional research guards. In both final reviews, an exact-string retention check rejected qualifications that were often preserved in paraphrase. This is a concrete validator/contract problem, separate from whether the reviewer's choices were good.
3. **Source loss must be distinguished from lost emphasis.** The revised Week 4 pool retained 51 of the guided-owner exchange's 55 turns inside a 124-turn attribution moment, while omitting the opening desire for things to become easier and calmer. It lost the dedicated interpretation and an important opening, not the entire supporting conversation. More source was delivered overall, yet that direction was not proposed.
4. **The earlier calibration result is narrower than transferable taste learning.** The combined arm explicitly instructed models not to repeat the already-covered DJ case. Its omission in three Week 3 model samples shows compliance with that concrete exclusion. The experiment did not isolate the full scripts' contribution, establish a general archive-aware judgment capability, or measure a framing-quality gain independently.
5. **The missing measurement is consequential.** The 92 new candidate records have no independent client-level pass/fail labels. There was no blinded evaluation, preregistered creative success criterion, source-level recall benchmark or held-out week. Of those 92, 66 exceeded the existing numerical component's cutoff; that is not an editorial acceptance rate.

Confidence is **high** about the observed transformation, task mismatch, guard defects and experimental limitations; **moderate** that explanation-oriented salience and poorly calibrated comparative criteria account for the recurring pattern; **unresolved** about their respective causal contributions versus model capability, long-context effects and response-schema burden.

**Minimum next step:** define and label the decision we want, then test framing ability and comparative judgment on small, fixed source cases. Keep source safeguards. Do not add another broad generation batch, swap models, or install a critic before that function has demonstrated discrimination. No new creative fix has been validated by this offline diagnosis.

## B. Audit of the previous solution

### Evidence and scope

Primary evidence consists of the saved suite at `testing/.data/experiments/reel-editorial-forensics-20261016/`, the older frozen Week 3–4 suite, current code, the 30-file before snapshot, exact request bodies, received outputs, validation errors and cost receipts. This investigation uses standard-library local-file inspection only; it does not import or invoke the inference runner.

Supporting deliverables:

- [Per-call audit](root-cause-2026-10-16/experiment-call-audit.md): all sixteen cells, exact model, role, counts, reported tokens, status and cost.
- [Machine-readable offline audit](root-cause-2026-10-16/offline-audit.json): message/control comparisons, self-score diagnostics, moment pools and source inventory.
- [Complete previous-change inventory](root-cause-2026-10-16/previous-change-inventory.json): 456 path records, including the preserved snapshot and isolated run artifacts; attribution limitations are explicit.
- [Six complete source-to-angle traces](root-cause-2026-10-16/source-to-angle-traces.json): original surrounding turns, upstream interpretations and actual treatments.
- [Previous implementation diff](2026-10-16-editorial-implementation.diff) and [reported verification](2026-10-16-editorial-verification.json).

The old suite's unreturned Week 4 Luna request still has no returned result or known charge. It is not counted as a new experiment or silently retried. Nothing here resolves its remote status.

### What changed

| File or artifact group | Previous change | Evidence / limit |
|---|---|---|
| `backend/backend_pipeline/prompts.py` | Added angle-only editorial/calibration components; appended literal approved scripts to default user data and separate SQL packet fields; added angle-specific version | Before/after bytes available |
| `backend/backend_pipeline/pipeline.py` | Added optional per-call prompt-version metadata and supplied it for angle generation; import formatting | Before/after bytes available; no new selection algorithm |
| `backend/backend_pipeline/sql_pipeline.py` | Supplied the same version for existing generation/refinement calls; import formatting | Before/after bytes available; no new SQL stage |
| `backend/backend_pipeline/model_experiment.py` | Included three new template files in future runtime sealing | Before/after bytes available; original suite not resealed |
| `prompt_templates/reel_editorial.md`, `reel_calibration.md`, `reel_approved_examples.md` | New instruction, calibration and literal six-script bundle | Existing files and creation history; bundle equals supplied corpus |
| `tests/test_reel_calibration.py`, `tests/test_editorial_forensics.py` | New builder/cache/provenance and experimental selection-validation checks | These test integrity, not human creative preference |
| `tests/test_model_experiment.py`, `tests/test_reviewed_experiment.py` | Empty-history checks changed from an end-of-message assumption to parsing the history field separately from examples | Documented in prior report and current code; complete before-byte snapshots for these tests were not preserved |
| `backend/scripts/editorial_forensics.py` | New isolated experiment harness, including temporary Selection and Review contracts and validators | Research-only; these are not production angle contracts |
| `backend/scripts/render_editorial_forensics.py` | New local renderer for reports, prompts, outputs, costs and hashes | Does not generate content |
| `context/2026-10-16-editorial-forensics.md` | Investigation state and later cost-approval correction | Context record, not an application control |
| Seven `research/2026-10-16-editorial-*` deliverables, 38 snapshot/component/schema files and 370 isolated run files | Reports, complete prompts, outputs, exact requests/responses, costs, seals and comparison data | Enumerated individually in the full inventory |
| `research/2026-10-16-generated-angle-title-inventory.md` | Later clarification: all 92 successful generation records | Subsequent to the sixteen-call investigation |

Of the 30 preserved paths, four current code files differ and 26 remain identical; none is missing. No deletion is recorded. A complete historical checkout snapshot was not made, so “every unrelated working-tree edit came from this investigation” would be false. The inventory separates verified byte differences from documented additions and test edits.

The original angle system/user template files, extraction templates, production response schemas, provider routing code, model defaults, scoring thresholds, matching algorithms and approval workflow were unchanged relative to that snapshot. The *assembled angle prompts* changed through the new components and examples. Model overrides and high reasoning were applied inside the experiment, not installed as new global model defaults.

**Correction to 'the reviewer was removed':** an additional reviewer was tried experimentally and not enabled in production. Its research helpers still exist. The application's existing targeted SQL refinement pass was not removed. Research D/E-review calls reused the transport stage label `angle_refinement`, but supplied different schemas and tasks; they are not a test of the existing targeted refinement workflow as a whole.

### Experiment audit table

| Experiment | Variable changed | Conditions held constant | Observed outcome | Valid conclusion | Remaining uncertainty |
|---|---|---|---|---|---|
| A, saved W3 / new W4 Sol | No intended intervention; historical W3 reused, missing W4 baseline executed | Frozen admitted transcripts, original prompts/schemas; W4 request equals its saved prepared body | W3 Luna/Sol/Sonnet: 9/10/9 candidates; W4 Sol: 11 | Exact baseline records are available | W3 was not freshly repeated; no returned W4 Luna/Sonnet baseline; no independent quality labels |
| B, W3 and W4 Sol | Added editorial instructions to system text | Actual user messages and non-message settings equal A; original pools, schema, model, high reasoning; no downstream selection | 10 / 9 candidates; some clearer central language | Instruction addition is a reasonably isolated input intervention | One sample/week/condition; no measured causal quality gain; changed count is not quality |
| C-source, both weeks | Added source-understanding instructions to the existing Luna extractor | Original full weekly user packet and non-message settings are byte/structure equal; same extractor model/high reasoning/schema | 17 / 15 accepted moments versus original 18 / reviewed 17 | A particular extraction treatment changes boundaries, labels and discovery inventory | No framing-only interpretation control; extraction nondeterminism; no full source recall labels |
| C generation, both weeks | Replaced the moment pool with C-source output | Actual system message and non-message settings equal baseline Sol; same angle schema; no filtering | 9 / 10 candidates | Source treatment alone did not obviously eliminate the pattern in these samples | Pool IDs, counts, boundaries and interpretations all changed together; no component attribution |
| D, selection-only | New task, system, schema and candidate input; source passages retained | Sol/high reasoning, frozen A candidates and original source per week; no rewriting | W3 returned 2 priorities + 1 reserve but failed `source_issue` rule; W4 returned valid 2 + 1 | This selector can produce a slate and real comparative reasons | No approved corpus; D/W4 added a null-semantics instruction absent from D/W3; no shuffled order, repetition or other reviewer model |
| E, combined Sol | Added calibration notes **and** six scripts, including explicit DJ non-reuse guidance, on top of B | Original pools and same Sol/non-message settings; same schema; no filtering | W3 8; W4 9 | This bundle excluded a directly identified known case and changed proposals | Notes versus examples versus direct exclusion not isolated; no independent creative-quality measure |
| E, W3 model comparison | Model slug | Messages identical across Luna Pro, Sol and Sonnet; same schema/high-effort label/provider policy | 7 / 8 / 9 candidates; all omit known DJ retelling | Models vary under the same supplied content; absolute inability to articulate a clear creative position is not supported | One week/sample/model; high-effort labels are not matched compute; no model winner or capability ceiling established |
| E, W4 exact repeat | A fresh draw / serving conditions | **Entire request equal**, same model/source/examples/schema/settings | 9 then 10 candidates | Exact request equality does not imply deterministic content | Only two samples, no quality labels; cache state and completion usage changed |
| E-review, both weeks | Added comparative selection **and** rewriting task with new system/schema, supplied E candidates and examples | Sol/high reasoning; original source pools and literal approved scripts | Both returned 2 + 1; both failed exact parent-boundary retention; some questionable exclusions | These particular runs show task substitution and a brittle guard | Not a clean selection-only ablation: candidate dependency, prompt, schema and task changed; no pairwise gold choices or reviewer-model comparison |

All sixteen requests used exact saved route slugs, JSON-object mode, high reasoning, no temperature, no explicit completion cap, no tools and no automatic retry/fallback. All returned `finish_reason=stop`. Models' reported token counts differ; this is not evidence of equal compute or equivalent native tokenization. No local output cap or client truncation explains the observed drafts. The files cannot prove attention to every delivered turn or all internal provider behavior.

The Week 4 repeat reported 100,152 prompt tokens in both runs but 11,211 versus 15,745 completion tokens, and substantially different caching. Its lower second cost does not demonstrate a quality or efficiency improvement.

### Experimental adequacy

| Requirement | What actually existed |
|---|---|
| Defined baseline | Yes: exact stored requests and outputs, with the W4 limitations above |
| Consistent source | Frozen raw sources; common pools for A/B/E; C deliberately changed the pool |
| Controlled configuration | Good request-level controls; no seed and no matched cross-model compute |
| Comparable output budget | Same absence of explicit caps; variable counts and output lengths, not equal candidate budgets |
| Quality rubric | Qualitative anchors and research score fields; no independently applied per-candidate labeled dataset |
| Independent/blinded evaluation | No. The evaluating agent also authored the reference recommendations |
| Repeated trials | One exact E/W4 repeat; not repeated pairs across all arms or evaluator orders |
| Success criterion | No prospectively fixed human acceptance rate, pairwise win criterion or tolerated strategic rewriting |
| Held-out validation | None |
| Integrity tests | Reported 70 focused passes and 104 additional passes, five overlapping; 22 SQL cases skipped. Useful code evidence, not creative-quality validation |

Therefore the old investigation supports local observations and several controlled input comparisons. It does not establish statistical reliability, an absolute quality improvement, a model-capability diagnosis, or a generally ineffective reviewer concept.

## C. Failure trace and practical taxonomy

### Distinctions the evaluation must preserve

**Source relevance** asks whether an actual exchange supports an opportunity. **Topic relevance** asks whether the subject matters to the audience. **Creative framing** chooses the thought through which the audience encounters that subject. **Editorial judgment** compares plausible framings, including reasons to skip. **Execution** makes the chosen thought natural to hear. **Final selection** decides whether it earns a scarce slot alongside other content and actual history.

These are separable. A topic can be worthy and its draft weak. A clear working description can be an appropriate intermediate record without being the best opening. A specific educational distinction can be a good Reel. The references are not better merely because they are shorter, broader or more opinionated.

The six anchors also differ: a genuine commercial question; a supported professional position; a hypothetical owner experience illustrated by a team account; a capability-and-support story; a couple's readiness situation; and an actual client correction. Do not collapse them into a universal hook formula.

### Trace 1: working creative, examined in detail

Source: W3, `Carmen Cruickshank's Personal Meeting Room's transcript (1).txt`, `moment_baa14f0096a2495fb5aa0669`, 00:19:09–00:21:07. Canonical cues `zoom:85bb927d029f3bb7:span:273` onward.

Selected turns are separate in the original unless adjacent:

> **[00:19:09] Marisa:** asks whether ads are refreshed monthly and how the content process works.
>
> **[00:19:28] Carmen:** “if something's working, I normally don't try to change it a lot” while explaining monthly creative availability.
>
> **[00:19:49] Carmen:** describes refreshing some conversion creative more because performance was declining.
>
> **[00:20:06–00:20:40] Marisa:** says she misses some updates and asks for formal review time.
>
> **[00:20:48] Whitney:** offers a recurring strategy meeting; its implementation is not shown.

The first and later descriptive entries above are paraphrases; Carmen's quoted substring is literal. The complete original turns are retained in the trace data.

| Step | Observed transformation |
|---|---|
| Source moment | A practical question elicits a choice between retaining working creative and changing declining creative; a separate review problem follows |
| Underlying thought | One supported perspective is that a calendar change is not sufficient reason to replace a working ad. A second legitimate perspective concerns client visibility into management |
| Original interpretation | The moment's proposition combines “performance-dependent” refresh with a client-proposed review cadence; `attention_reason` explicitly values pairing them |
| Baseline Sol framing | “Creative production and live campaign changes can follow different schedules.” Core also carries client review cadence |
| B framing | “Fresh creative can be ready without replacing ads that still work.” Its core stays more focused and the communication concern is separated internally |
| E framing | Similar clear title, but core describes two decisions; `selection_reason` says the client review process makes the scene more substantive than a generic instruction |
| Preserved / lost | The professional position survives. Its priority and simple audience-facing expression are diluted by the second operational topic |
| Final review | `creative_replacement` is skipped as “useful but familiar” and more suitable to an FAQ; it never directly compares the reference framing against this draft |
| Observable mechanism | A stated preference for a richer process explanation promotes a second issue; subsequent judgment evaluates that combined treatment. This is salience/formulation plus selection, not demonstrated literal comprehension failure |

The source-analysis C variant narrows this interval from 18 turns to nine (00:19:09–00:20:04), excluding the later review meeting discussion. Its baseline Sol output **still** describes creative readiness and replacement as management decisions. Removing the secondary issue did not, by itself, produce the preferred expression in this one sample. Thus neither “the meeting context caused everything” nor “we only need more context” is established.

E/Sol's quality justification also says the principle is familiar and no measured effect was supplied. Its distinctiveness score is 3.5, making the scalar bottleneck exactly 70. Absence of a measured effect does not invalidate a supported professional position; it would matter if the angle claimed a performance effect. The written reason makes that distinction worth testing, but does not reveal how the model internally weighted each consideration. Under the existing strict numeric component this draft would not qualify. That component was disabled in the pilot, and SQL can attempt a targeted refinement, so this is a prospective filtering risk rather than the cause of the recorded reviewer skip.

There is also counterevidence to a total framing inability: E/Sonnet writes, “Make new creative regularly, but let performance decide what gets replaced.” Its title is a natural position about working ads. The field-rich schema does not make a clear stance impossible. The reference's advantage is emphasis and restraint, rather than a wholly absent insight.

Approved Reel 1 leads with a definite recommendation before explaining foundations; Reel 3 turns the apparently surprising training session into evidence for a belief. They show how explanation can serve a central position. They do not prove that every professional position deserves publication or that the creative-refresh reference is the only defensible angle.

Do not remove the source's communication limitation to make WIA look flawless. Keep it available as a boundary; do not automatically make it the central idea. Likewise, Carmen's algorithm rationale is attributed, not independently verified platform law.

### Traces 2–6

| Case / source | Initial interpretation | Generated framing | Lost or preserved signal | Final review / defensible diagnosis |
|---|---|---|---|---|
| **Commercial value**, W3 `moment_685c9db487511394f76b1711`, 00:11:56–00:17:11 | The original moment foregrounds attribution limits and wider performance, though its 60-turn context includes Mike asking whether the expensive band's ads are worthwhile | Baseline Sol already creates offer-economics content. E/Sol: “A quieter inquiry stream needs sales context when booking values differ” | The owner's business question is understood, but expression leads with a reporting principle. E/Luna has no separate economics treatment | E-review makes sales context a reserve. This is partly relative selection, not proof of missing source or misunderstanding. The $14K report does not prove profit or causal ROI |
| **Quiet inbox**, W3 `moment_a3deaf92e77cc94f7c6548e5`, 00:21:17–00:26:14 | Team discussion of a client's reported slowdown; Fallon asks whether organic inquiries slowed too | E/Sol leads with “checking organic changes the advertising investigation” | Diagnostic thought survives; the reference's owner-facing entrance is less visible | Reviewer selects it but keeps investigative wording. Reference emotion is a plausible audience situation, not a verified statement that Jill wanted to change everything. Execution and framing should be judged separately |
| **Guided owner**, W4 `moment_1c4dc73fb89e4a4e32377888`, 00:05:17–00:12:18 | Original moment recognizes self-directed owners wanting guidance. They say they want things easier/calmer, have built a funnel and want to understand ads | E/Sol: expert help is compatible with wanting to remain the person who understands/runs campaigns | A credible human/commercial thought is present. C loses its separate label and the first four turns, but retains 51/55 turns inside attribution context | Reviewer skips for overlap with Reel 5 and current-offer checks. The overlap is a real consideration, but not proof a new scene adds nothing. No purchase or outcome may be invented; historical program specifications are unnecessary to the support-fit thought |
| **Interest/readiness**, W4 `moment_729c08576259422181b39698` plus `moment_331f75617d426e5c1df24f86` | First pointer emphasizes adjacent-service truthfulness. In the 80-turn original interval, Whitney's 01:18:07–01:18:35 contribution distinguishes cold discovery from readiness for a detailed form | E splits adjacent demand and useful follow-up; a9 says early interest can develop through useful contact | Buyer readiness survives, but becomes a follow-up treatment with room for a much larger guide | Reviewer holds a9 for cadence, reply handling and stopping criteria. Those are central to a guide, not necessary to the bounded readiness thought. This is observable substitution of a more demanding task |
| **Collaboration**, W4 `moment_7bd068bbf7d499107487a129`, 00:14:21–00:17:44 | Original proposition already says a client clarification changes the attribution diagnosis | E's rationale notices the correction; core still describes channel/campaign attribution questions | The collaborative interaction survives as supporting evidence while tracking becomes the foreground | Reviewer acknowledges the diagnostic scene but prefers a different measurement idea and suggests a longer guide. Portfolio choice may be legitimate; this never tests whether it would prefer the human-collaboration framing if shown it directly |

**Correction to the old C conclusion:** the W4 attribution moment starts at 00:05:59 and runs to 00:18:32, with 124 turns. It contains nearly all of the guided-owner exchange. It omits 00:05:17's “easier, and calmer” desire and Whitney asking where guidance is needed. This is a boundary-and-label issue plus downstream salience, not wholesale loss of competence evidence. Source retention by turn count alone would miss that distinction.

### Failure taxonomy tied to actual outputs

| Failure mode | Actual evidence | Earliest observable stage | Mechanism established / unresolved |
|---|---|---|---|
| Topic or task leads instead of the thought | E/W3 rebrand handoff is presented as moving approved assets before website launch | Generation | A valid coordination topic is foregrounded; whether it deserves a Reel is an editorial decision, not guaranteed failure |
| Lesson replaces owner-facing question | E/W3 `sales_context` starts with sales context rather than Mike's genuine commercial question | Formulation | Meaning is present; what leads is different |
| Second operational issue broadens the core | Creative-refresh drafts repeatedly add review cadence | Moment interpretation and generation | Public justification explicitly values pairing issues; causal effect of the upstream label is untested |
| Opinion becomes a neutral distinction | E/Sol creative core defines two decisions | Formulation | A supported position is expressed as classification; E/Sonnet provides a stronger counterexample |
| Meaning remains in rationale | E/W4 a4 describes client correction vividly but centers attribution in core | Formulation | Same response contains a possible stronger foreground; no need to assume missing comprehension |
| Human setup loses salience | C/W4 omits the calmer/easier opening and nests guidance inside attribution | Context boundaries and provisional interpretation | Verified omission; influence of label versus missing opening needs isolation |
| Familiarity substitutes for contextual distinctiveness | E-review skips working-creative judgment as familiar; skips guided ownership partly for Reel 5 overlap | Comparative selection | Recorded reasons, not a measured brand preference. Familiar beliefs can be worthwhile with a new scene; not every new scene earns a slot |
| Script completeness is required for an angle | a9 held for cadence/stopping rules | Evaluation | The reviewer explicitly introduces a practical-guide objective beyond the central thought |
| Incomplete archive permits real repeats | Buyer-research directions recur without the sent 10 June email being supplied | Context / novelty evaluation | Exact prior email is absent; model cannot be expected to identify that particular unseen overlap |
| Adjacent variants compete for separate slots | Buying-decision research versus separate-form administration; readiness versus follow-up can become repetitive | Generation / slate comparison | Some genuinely differ; duplicate classification needs central-thought comparison, not a ban on shared moments |
| Factual scope becomes too absolute | E/Sonnet buyer-research core says only deciding-factor evidence tells what ads should say | Formulation / claim review | A scope-overstatement risk despite more nuanced qualifications. Not evidence of a fabricated client outcome; requires semantic review |
| Guard failure is confused with editorial failure | E-review paraphrases retained boundaries but fails string inclusion | Research validation / reporting | Concrete implementation defect; independent from taste |
| High scores stand in for suitability | 66/92 numeric scores exceed 70; creative Sol draft's bottleneck is 3.5, giving exactly 70 | Scoring / potential later filtering | Scores are uncalibrated. No actual filtering happened in the pilot; a score-only cutoff effect is a counterfactual, not the observed source of removal |
| Too many candidates mistaken for bad content | A/B/E return 7–11 proposals, while references are a small slate | Evaluation design | Different tasks/count budgets. Large candidate sets are not inherently bad; final selection quality must be measured separately |

No verified fabricated performance outcome is asserted for the selected new traces. That risk belongs in future hard-negative tests; it should not be invented to complete a taxonomy.

## D. Ranked root causes and competing hypotheses

“High” below means a mechanism or mismatch is directly observable, not that a replacement has been proven to solve it. The distinction between a proximate failure and its underlying cause matters.

| Proposed cause | Supporting evidence | Counterevidence / boundary | Confidence | Decisive next test |
|---|---|---|---|---|
| **1. Required editorial task is not the generator/evaluation contract** | Current template requests opportunities, prohibits rankings/hooks; references result from a comparative Reel assignment; no matched final-output budget | Candidate development is a legitimate stage; no need to force a small quota upstream | High mismatch; medium causal contribution | Same known source/thought and model, evaluate a central-thought framing task separately from full opportunity-record expansion |
| **2. Substantive meaning survives but salience and comparative criteria favor process completeness** | Creative rationale explicitly values a second management issue; review rejects familiar position; readiness held as an incomplete guide | Prompts explicitly say no outcome required for process and avoid lessons; some generated cores are strong | High occurrence in documented cases; moderate general explanation | Frame-only task plus label-masking contrast, then pairwise selection on human-labeled alternatives |
| **3. Evaluation did not operationalize creative success** | No independent labels, held-out material, pairwise gold test, preregistered success condition or repeated reviewer orders | Qualitative rubric and detailed analysis existed; integrity tests were useful | High methodological defect; not a direct cause of every draft | Label fixed cases and current baseline, then test evaluator agreement/order stability before trusting it |
| **4. Reviewer/guard specification defects** | D3 null semantics unclear; E-review requires identical boundary strings not explicitly requested verbatim | These checks intentionally protected provenance and prevented silent promotion | High for failed status; low as explanation of weak framing itself | Offline metadata-inheritance design and existing-response boundary adjudication; separate contract tests from quality tests |
| **5. Upstream labels and context boundaries steer attention** | Guided-owner story embedded in attribution; calmer opening omitted; original commercial pointer emphasizes attribution despite value question | Original passages remain available and models sometimes recover different interpretations; C creative narrowing still yields a lesson | Moderate; labels versus context not isolated | Hold every source turn fixed and mask only proposition/discovery pointers; separately restore only missing setup turns |
| **6. Novelty objective uses incomplete coverage / may overvalue unfamiliarity** | DJ exclusion is directly instructed; missing email allows repetition; reviewer dismisses familiar creative principle | Some novelty-based exclusions are defensible; full archive could reveal more legitimate overlap | High archive gap; moderate weighting issue | Complete fixed eligible archive and human-labeled same-belief/new-scene comparisons, without changing source/model |
| **7. Twenty-one fields, long context or instruction ordering crowd creative work** | Full records require strategy, process, risk and quality explanations; E/Sol about 25K system characters and 289–297K user characters | No minimum angle count; no evidence-context duplication in these pools; clear stances can still be written under the same schema | Plausible, unproven | Known-thought framing with lean versus existing output burden; source-only versus provisional-label context controls, one variable at a time |
| **8. Model cannot reliably discriminate or frame** | Three models still yield uneven work; four Sol editorial calls show concerning choices | Natural opinion wording appears, no direct framing-only or strong-versus-weak discrimination test; reviewers only used Sol | Unresolved; absolute incapacity contradicted | Test the failed narrow task first; only then compare exact available model routes on that task |

### Explanations not supported as the current cause

- **Embeddings removed the good ideas:** no matching, ranking or embeddings executed in these generation experiments.
- **Only summaries were sent:** original source passages were supplied. Original W3/W4 pools delivered 687/583 unique source turns; C delivered 702/819. There were no repeated evidence span IDs within those respective packets.
- **A fixed quota forced the generators to fill slots:** the response schema does not impose a positive minimum angle count and prompts permit empty results. The review experiments had maxima, not mandatory exact counts. Always receiving three review recommendations does not prove quota filling without an all-weak test.
- **There were no strategic instructions:** substantial strategy/process/angle-selection guidance already existed before B/E. Adding more instructions was not a clean test of whether instructions were missing.
- **Source fidelity must be weakened to sound natural:** supported opinion wording appears with full evidence safeguards; accuracy constraints do not logically require academic phrasing.
- **An extra reviewer is inherently ineffective:** only specific Sol prompts, input pools and flawed guards were tried, without a validated discrimination benchmark.
- **Temperature, length cutoff or fallback explains the weakness:** temperature was omitted, no explicit completion cap was configured, all sixteen stopped normally, and exact routing/fallback policy was checked. No supporting evidence for that explanation was found.

## E. Reviewer diagnosis and the correct evidence standard

### Two different failures were bundled together

**Contract reliability.** D/W3's prompt/schema permitted a nullable text field named `source_issue` without explaining that a valid qualification must use null. Its response used that field to record valid limits, then the validator rejected selected records whenever it was non-null. D/W4 added the missing instruction. These are different protocols, so the improved validation result is not a repeated quality result.

For E-review, `validate_review` tests exact set inclusion of every parent qualifier/risk sentence. The request says preserve valid boundaries, not reproduce all strings verbatim. For example:

- Parent: “The passage begins mid-explanation, so the full introduction to the proposal is unavailable.”
- Review: “The passage begins mid-explanation; the full introduction to the proposal is unavailable.”

The guard treats these as different. Similarly, “Verify speaker identities and permission for recognizable client details” becomes a warning to review identities and permission before using recognizable details. The examples are materially equivalent on inspection. Other returned boundaries still require individual checking; this is not a blanket semantic approval of every rewrite.

All six returned review recommendations fail at least one literal-parent inclusion condition. Neither failed status proves creative incompetence, nor does a readable paraphrase establish a publishable recommendation. The raw failures should remain recorded; the diagnosis should distinguish an over-strict guard from a genuinely dropped factual limit.

**Editorial discrimination.** The final reviewer sees original passages and the approved scripts, but not the user-endorsed reference alternatives. It evaluates already developed E candidates with scores and justifications visible. It is not blinded, order is fixed, no weak same-source contrasts are provided for calibration, and only Sol reviews. It selects and rewrites together. Those conditions cannot establish whether it recognizes a stronger framing when directly shown one.

Its stated reasons show at least one concrete task error: evaluating the readiness thought as a complete follow-up guide. Other decisions—choosing the tour-page distinction over another tracking-related idea, or concern about guided-DIY overlap—are contestable portfolio judgments, not automatically proven errors. A human preference benchmark is needed to decide them.

The review system replaces the generation system with a shorter reviewer policy plus calibration; it does not retain the complete WIA strategy/editorial instruction text. Therefore this was a bundled task/context/schema change, not simply “add an independent critic to the otherwise identical workflow.”

### Central evidence versus optional elaboration

| Intended central thought | Evidence necessary now | Not necessary unless the angle claims it |
|---|---|---|
| A working ad need not change merely because a month passed | Carmen's actual decision/rationale; distinguish working from declining ads; correct speaker and scope | Proved algorithm penalty, universal refresh interval, measured lift or a fully implemented review SOP |
| Capable owners can want guidance without handing over control | Owners' existing work/desire to understand; Whitney's recommendation in context | A purchase, improved confidence after buying, current price or every current program feature |
| Discovery can precede readiness for a detailed inquiry | Whitney's buyer-readiness explanation and the attendee's situation | A completed nurture sequence, exact cadence, stopping rule or conversion result |
| The owner's knowledge changes a recommendation | Actual clarification and resulting change in question | Tested HoneyBook configuration or proof every attribution problem was solved |
| A particular strategy produced measured growth | Matched periods, definitions, attribution and outcome evidence sufficient for that causal claim | A vivid quote alone is insufficient; this is a different evidentiary burden |

The evaluator should first identify the central claim, then test only what that claim requires. If the candidate expands into a tutorial, request the additional facts or narrow it back. Do not invent implementation details or treat a case-specific position as an industry frequency claim.

A better evaluation function remains plausible. It must demonstrate recognition of human-labeled distinctions, factual disqualifiers, genuine new-scene value, harmless incompleteness, and the option to select nothing. It may eventually operate inside one generation call, through existing human Gate 1, or as a separate paid task. No separate call is justified merely by giving it the title “editor.”

## F. Root-cause test plan

**Status of every prospective model test in this section: NOT RUN.** The user's restriction prohibits all OpenRouter requests in this diagnostic phase, including catalog checks. There is no approved spending budget. The following is a decision plan for a later separately approved step, not authorization to execute it.

### What the current pipeline actually rewards

| Stage | Observable objective / enforcement | What it does not establish |
|---|---|---|
| Ingestion and compact preparation | Deliver admitted turns losslessly with real cue references and revision identity | That every relevant recording was admitted, transcription is correct, or every useful thought will be noticed |
| Moment discovery | Select meaningful exchanges; provide propositions, audience relevance, discovery use, literal quotes and coverage acknowledgments | Coverage acknowledgment is not recall; a valuable thought can be buried inside another moment |
| Angle generation | Complete a 21-field strategic record plus internal findings, all moment acknowledgments, evidence statements and self-scores | No explicit ranked final slate is requested. Field completeness cannot measure creative appeal |
| Parsing | Types, real IDs, context containment, exact anchor quote at extraction, assertion prefixes, coverage and canonical duplicates | Prefix presence is not assertion entailment; canonical equality is not semantic duplicate detection |
| Numeric quality | For strategic drafts, `20 × min(grounding, strategic_fit, distinctiveness, audience_resonance, source_strength)` | No independent creative-quality calibration; low novelty or lack of results may influence the wrong task |
| JSON pilot completion | Persist candidates, mark generation complete; no vectors/history/ranking | It does not select, approve or publish content |
| SQL/full comparison, when run | Evidence/readiness, complete comparisons, numeric quality, history similarity and optional targeted replacement/family choice | No established test of audience interest or Whitney's taste; history is admitted `content_angles`, not an automatic scan of the email directory |
| Gate 1 | Explicit editorial approval action, current evidence/matching conditions and recorded actor; separate from generation | A high score does not itself approve content. Approval logic is not proof of creative merit or universal reuse clearance |

The code and prompts do **not** explicitly maximize angle count, require one idea per moment, require every angle to teach an action, or seek agreement among models. Assertions that these are the programmed objective are unsupported. Nevertheless, outputs' stated reasons repeatedly reward process explanation, extra useful distinctions and completeness. That is an observed behavior to diagnose, not a proven hidden reward function.

The effect of the JSON burden, long context, order and upstream pointers remains unresolved. Current packets contain no duplicate evidence span IDs; a generic claim that repeated snippets caused the problem is contradicted here. The angle context is large, but supplying more C/W4 source turns did not solve framing. Neither observation isolates a context-length effect.

### Exact benchmark material

Development anchors are the six frozen trace records in [source-to-angle-traces.json](root-cause-2026-10-16/source-to-angle-traces.json). They include original cue IDs, surrounding turns, original interpretations and actual candidate versions. Preserve complete relevant intervals, speaker status and all claim boundaries.

Start narrow-task testing with three different creative jobs:

1. **Professional position:** the 18-turn working-creative interval, W3 `moment_baa14f0096a2495fb5aa0669`. Known underlying thought supplied in a framing-only condition: Carmen distinguishes making creative available from a justified decision to change a working ad. Do not supply the reference sentence as an answer.
2. **Owner situation:** the 55-turn guided-owner interval, W4 `moment_1c4dc73fb89e4a4e32377888`, including 00:05:17's stated desire. Supplied thought: experienced owners have done substantial work, want help with decisions and want to remain involved. No invented sale or later transformation.
3. **Buyer situation:** the original 80-turn workshop interval for `moment_729c08576259422181b39698` and adjoining 24-turn `moment_331f75617d426e5c1df24f86`. Supplied thought: newly interested people may not be ready for a detailed inquiry; useful next contact can help them consider it. Preserve Emily/Whitney ownership. Do not supply sequence details as if implemented.

For discrimination, add the other three trace cases and the tour-page-versus-tour-booking distinction as a positive control for focused education. Include a clearly identified **constructed test foil**, such as converting the unresolved slowdown into a verified campaign recovery, solely to check factual rejection. It must never be recorded as an actual model output. Include an all-weak slate only after human judges agree it lacks a publishable central thought.

### Targeted experiments and falsifiers

| Test | Hypothesis / independent variable | Controls and exact material | Evaluation and confirming observation | Observation that weakens it | Existing result / limit |
|---|---|---|---|---|---|
| **A. Baseline reconstruction** | The observed outputs are genuine consequences of the recorded requests rather than post-processing | Actual saved bodies, raw outputs, artifacts and original pools; no regeneration | Compare message/settings identity, output lineage and parser path; locate loss before any disabled filter | A mismatch in request/source lineage or evidence a later stage rewrote the core | Completed offline: A/B users/settings equal; E/W3 model messages equal; E/W4 repeat entire body equal; no pilot filtering. This is not a fresh stochastic reproduction |
| **B. Interpretation / salience** | Provisional topic labels steer attention even when dialogue contains the better thought | Same Sol route/settings and all source turns; change only presence of `proposition`, `discovery` and interpretive summary pointers. Separately test restoring only the four omitted guided-owner setup turns | Human source-level labels for meaningful questions and contributor reasoning, before any final angles. Better recognition with pointer masking supports anchoring; improvement only with setup restored supports boundary loss | Same interpretation with/without pointers/setup, or source-only output already recognizes the desired significance | Not run. Historical C changed labels and boundaries together, so it cannot isolate these mechanisms |
| **C. Framing only** | A model can express a known thought naturally once discovery is removed | Three fixed source cases above; human-specified underlying thought without reference wording; same model/high setting, archive, output fields and budget across repetitions | Blind human pass/borderline/fail on central thought, source fidelity and natural delivery. Strong repeated alternatives support conditional framing ability | Continued operational definitions despite correctly supplied thought, or invented emotion/results needed to make it sound appealing | Not run. Existing Sonnet stance is positive evidence of some ability, not a controlled framing-only result |
| **C2. Response burden, only if needed** | Full strategic-record expansion dilutes a good thought | Same source **and supplied thought**; lean central expression versus existing 21-field response. Ask humans to assess only identical title/core fields | Better central expression under the lean condition suggests output-task burden; metadata can remain application-side | Same quality in both; lean output merely shorter or drops evidence without improving the thought | Not run. Do not change schema/model/context together or count metadata length as a quality gain |
| **D. Editorial discrimination** | The evaluator can choose among actual framings for the right reason | Fixed human-labeled same-source pairs, same source/evidence/archive; remove model IDs, self-scores and creator justifications; counterbalance A/B and case order | Record preferred option, both usable/neither, missing **central** fact if any, and one decisive creative difference. Check factual foil and education control | Prefers routine completeness, rejects readiness for irrelevant cadence, penalizes all education, chooses unsupported drama, or flips with order | Not run. Earlier D/E-review never showed the strong reference alternatives directly, never counterbalanced order, and only used Sol |
| **E. Selection / filtering** | Weak outcomes come from ranking choices rather than generation capacity | Exact same candidate pool and actual eligible archive; compare existing numeric/family policy with a validated comparative procedure. Keep wording fixed for selection-only testing | Blind human slate decisions; count strong candidates lost, weak ones promoted and redundant selections. Return fewer/none for genuinely weak pools | New selector adds no human-preferred value or rescues weak wording merely through higher scores | Offline numeric diagnostic completed: 66/92 above 70, but full history/vectors absent. The E/Sol creative draft is exactly 70 and would fail the numeric component, while SQL may attempt refinement. Not an observed pilot removal |
| **F. Model/configuration** | The narrow failed function depends materially on model or supported reasoning setting | Only after B/C/D locates the failed function; same small packet, fields, budget, order balancing and human labels; change one exact route or one setting | Repeated, human-labeled improvement on that function with comparable source integrity and cost | Variation is no greater than within-model repeats, or gains come only from different task/context | Not run. Historical E/W3 tests three models on generation, not editorial discrimination. Saved high-effort labels do not prove matched compute |

### Smallest decision sequence

**First, zero API calls:** have Whitney or an authorized content editor label the six anchor comparisons plus focused-education and factual controls; adjudicate what is truly weak versus a valid alternative. Score the current baseline using the same representation and source, without model names. Do not ask a new model to create its own supposed ground truth.

**Then, if separately approved, an initial screen of at most four small calls:** two exact-repeat framing-only trials on the three fixed cases, and two counterbalanced discrimination trials on the fixed comparison set. This is a capability screen, not an end-to-end fix or a reliable order-effect estimate. Two draws cannot separate every order effect from stochastic variation; if that matters, it needs another explicitly approved design.

Decision rules:

- Framing succeeds, discrimination fails: do not install a model reviewer. Retain human selection and investigate the discrimination definition/context.
- Discrimination succeeds, framing fails: test a targeted expression task before changing extraction or rerunning entire weeks.
- Both succeed, full pipeline fails: prioritize pointer salience, response burden and source/setup boundaries, one controlled intervention at a time.
- Both fail: inspect instructions and benchmark agreement, then compare models only on the failed narrow function. Do not buy another broad multi-model batch.
- Results are ambiguous: report that result and stop at the approved call boundary. No opportunistic expansion.

A pure interpretation probe, schema ablation, selector experiment, model comparison and held-out end-to-end validation are **conditional later tests**, not additional calls silently included in those four. Costs must be estimated from the actual proposed bodies and supported limits before seeking approval. No current price, guaranteed charge or approved dollar budget is asserted here. Previously uncapped high reasoning should not be carried into a supposedly bounded-cost test without considering its worst-case completion cost.

### Available holdout material

[The proposed holdout inventory](root-cause-2026-10-16/proposed-holdout-inventory.json) identifies **Week 5 and Week 6**, six local exports each. Neither week appears in the sixteen-call generation suite. Their file revisions have no byte-identical match to development Weeks 1–4, and no byte duplicates between these two holdout weeks. Source-family/story overlap still needs checking; different hashes do not prove a new idea.

This establishes candidate holdouts relative to the investigated experiments, not proof that no other job, person or model has ever encountered those recordings. There are no independently approved scripts for these validation weeks identified in the evidence used here.

I hashed and timestamp-counted these files without editorially analyzing their dialogue. One 97-byte Week 5 file contains only a greeting. It is a useful no-op source-admission/abstention case, not a promise of another content opportunity. The others are candidate validation sources, not already certified useful material.

Keep Weeks 1–4 as development: they have already influenced instructions, feedback or examples. Freeze Week 5 for the first validation and Week 6 as a second unchanged validation week. Do not tune to Week 5 and continue calling it held out. Any archive used must be frozen consistently across methods, with date/status uncertainty preserved and no other model's same-week outputs silently added as history.

For later end-to-end validation, use one shared extraction per source week where no accepted cache exists, freeze it, and compare methods on identical evidence. Repeated generation and independent judgments need separately approved scope. A manually assembled evidence pool can test framing cheaply, but cannot validate full transcript-discovery recall. No held-out model outputs or real-world approvals are claimed now.

## G. Reliability design

### What can be retained, what must be proved

Retain the useful existing architecture: lossless source preparation, one reusable weekly discovery pass, original surrounding passages, source identity, separate candidate/internal uses, existing artifacts and human Gate 1. The previous work established practical compatibility and isolation; it did not validate an autonomous editorial selector.

The proposed logical workflow is:

1. **Discover and preserve the setup.** Existing extraction binds evidence. Evaluate whether it retains the question/desire, professional response and resulting state, not just cue counts. A provisional label is a pointer. It must not silently become the only interpretation later stages are allowed to consider.
2. **Choose the thought before expanding the record.** An audience-facing question, observation, position or interaction should stand on its own. Compare materially different interpretations where supported. This can be work within the current call; a separate model stage is not assumed. A source may legitimately support internal research or no Reel.
3. **Separate evidence eligibility from creative judgment.** Identify central factual assertions, inferential framing and optional development material. Preserve source boundaries in immutable provenance and determine which are material to the chosen thought. Do not ask the model to reproduce every inherited warning verbatim to preserve the underlying record.
4. **Compare clean representations.** A prospective evaluator first compares thought, audience stake, necessary scene and focal implication. Hide model IDs, creator scores and promotional selection justifications. Supply evidence for factual checking and the actual eligible archive for overlap. A fluent long record should not win merely because more fields were completed.
5. **Select a slate after testing discrimination.** Evaluate novelty of the thought/scene, relevance to actual slots and differences across the slate. Same pillar does not mean duplication; different pillars do not create difference. A familiar WIA belief can earn a new demonstration. A repeated case cannot earn a new slot merely by changing its title.
6. **Revise only a diagnosed deficiency.** If the source is good but expression is weak, preserve the source family and revise the central framing. If the central claim is unsupported, obtain the needed evidence or hold. If the idea adds little, skip rather than polish indefinitely. No automatic paid revision is enabled or authorized.
7. **Finalize honestly.** Structurally valid candidates remain candidates. Human approval remains explicit. A run with no worthwhile angle can finish its research work and report “no recommendation / editorial review required,” rather than pretending a platform failure occurred or filling slots with weak topics. Proposed quality dispositions must be represented separately from transport/schema failure.

### Calibration that would address the actual distinction

The existing six scripts are useful positive taste data, but they do not cover Whitney's full preferences or teach every same-source comparison. A more diagnostic calibration set would pair:

- One source scene and supported central facts.
- A true but less compelling operational treatment.
- A stronger observation, question, opinion or human/business treatment.
- A short human-approved explanation of the decisive difference.
- A legitimate focused-education example and an attractive but unsupported foil.

That is a **proposed contrastive test resource**, not evidence that adding it will work. Do not copy the six reference titles into production as mandatory forms. Keep varied creative jobs and new validation sources. Use the full history to decide prior use; taste exemplars alone cannot certify novelty. Do not load all historical material indiscriminately or call directory presence successful retrieval.

### Measurement and monitoring

Record request/model/effort/limits, source revisions and exact evidence, prompt version, candidate versions, human dispositions, comparisons, missing central facts, archive coverage, failures and costs. Existing request and artifact storage already supplies much of this. Additions should serve a specific unresolved diagnostic need, not another sprawling scorecard.

Track separately: discovery misses; factual/attribution errors; central-thought weakness; execution-only edits; inappropriate rejection for irrelevant detail; repeated concepts/cases; useful diversity; abstention correctness; structural failures; human strategic rewriting; and new paid cost. Model agreement is not an independent quality measure. Quality and source-readiness statuses must not be overwritten by a high average score.

### Guarantees and their limits

| Category | Feasible requirement | Current position / needed logic |
|---|---|---|
| **Hard process guarantees** | Admit only schema-valid parsed outputs; real source IDs; exact extracted anchor text; source-bound context; complete ID acknowledgments; preserve versions/raw receipts when received; canonical duplicate checks | Much is already implemented. Acknowledgment is not comprehension; exact references are not factual entailment. No blanket semantic-duplicate guarantee |
| **Hard approval integrity** | Generation must not assign human approval; require explicit acceptance action against current evidence/content identity; retain pending/held status for unresolved eligibility | Existing Gate 1 provides an explicit action and guards. Creative acceptability itself remains a human decision, not guaranteed by the action's software preconditions |
| **Hard spending-process controls** | No request outside a user-approved exact batch/model/source scope and remaining call count; no inferred approval from commentary; no retry/extension without approval | Current research `--live` flag and mutable dispatch bound are not proof of human approval. A future pre-dispatch approval record should bind the reviewed plan/hash. Do not change it during this diagnosis |
| **Cost visibility** | Record dispatch, returned usage and known/unknown cost honestly | Existing storage helps; a lost remote response can leave charge unknown. A local estimate alone cannot guarantee a provider's final bill |
| **Statistical targets** | Human-acceptable output proportion, paired preference, evaluator agreement, repeat consistency, source recall, appropriate abstention | No validated current creative reliability rate. Measure on independently labeled cases and held-out weeks with denominators and uncertainty |
| **Human editorial decisions** | Whether a thought is worth a slot, whether a familiar belief has a valuable new scene, desired mix, permissible degree of provocation, brand voice and strategic priorities | Do not claim a model score conclusively settles these. Capture judgments and disagreements rather than turning one author's preference into universal law |

A finite output cap and conservative cost estimate can improve budget predictability if the route supports them. A hard monetary guarantee requires provider-side enforcement or verified bounded pricing assumptions, not just a local comment saying “budget.” Every OpenRouter request—including metadata queries—remains prohibited in this phase.

## H. Acceptance criteria

### Observable rubric, without an invented score threshold

These are proposed decision anchors for human calibration. They are not yet a validated classifier or numeric brand standard.

| Dimension | Pass behavior | Borderline behavior | Fail behavior |
|---|---|---|---|
| Central thought / distinctiveness | A worthwhile interpretation, question or supported position is identifiable | Useful principle whose particular contribution is still unclear | Merely names an advertising task or repeats a generic belief |
| Natural audience relevance | A credible owner/couple situation or consequential decision is apparent | Relevant audience named, but stake needs explanation | Only a broad audience label or invented emotional assumption |
| Creative framing | The selected perspective makes the real scene worth discussing | Perspective exists mainly in rationale or is spread across two ideas | Neutral synopsis or completeness presented as the creative value |
| Point of view / meaningful tension | Clear observation, real choice, desire or question; no manufactured conflict | Correct distinction but limited reason to care | False controversy, compulsory opinion or no worthwhile thought |
| Reel suitability / execution | Can enter naturally and develop one connected thought | Needs focus or simpler spoken expression | Requires a glossary, several lessons or setup steps before the point |
| Corpus consistency | Uses demonstrated clarity, owner respect, scene and business meaning without copying | Plausible but insufficiently evidenced taste fit | Repeats an existing case or inherits unsupported example facts |
| Specificity / depth | Necessary detail supports a transferable or legitimately narrow thought | Too many particulars, or broadened nearly to a slogan | Topic becomes either generic “strategy matters” or a narrow administrative tutorial without audience appeal |
| Central evidence | Source supports the stated facts with correct owner, chronology, scope and outcome status | A precisely identified central uncertainty requires a hold/narrowing | Fabrication, source mismatch, forecast-as-result or unsupported causal claim |
| Editorial distinctiveness | Adds a different thought/scene/consequence to current slate and actual eligible history | Overlap is meaningful but a new contribution is arguable | Cosmetic rewrite, pillar relabeling or duplicated case presented as fresh |
| Restraint | Core stands alone; necessary boundaries stay available; optional guide detail omitted | One extra issue weakens focus | Unrelated completeness requirements dominate, or crucial caveats are hidden to make the claim exciting |

A **passing angle** could be the professional judgment reference developed honestly from Carmen's choice. A **borderline draft** is E/Sol's two-decision formulation: the thought is real and supported, but needs focus before a Reel recommendation. A **failing fit for this intended treatment** is requiring a full nurture stopping rule before allowing any readiness observation. The source-grounded tour-page distinction is a positive education control. These examples must be adjudicated by Whitney/an authorized editor; they do not establish that every technical angle fails or every short opinion passes.

### Measurable release requirements

| Requirement | Measurement / proposed gate | Current result |
|---|---|---|
| Structural/source integrity | Every accepted record passes types, IDs, source identity/context and required literal extraction checks; zero known critical source violations may be promoted | Existing checks are substantial; selected semantic claims still need review. Not a certified truth rate for all 92 |
| Correct central-claim evidence standard | Enumerated development cases must not be rejected solely for irrelevant implementation details; factual foils must be held/rejected | Earlier a9 fails the intended standard; revised evaluator not tested |
| Human quality baseline | Label each assessed draft as ready as an angle, needs central reframing, execution-only edit, hold, internal or skip; count all evaluated candidates, including empty/failing outputs | **No independent client adjudications are recorded for these 92 records in the available evidence. The labeled denominator is 0; acceptance rate is unmeasured, not 0%** |
| Editorial-quality target | Establish an absolute target from Whitney's baseline decisions and required output/capacity; compare blind paired methods on unchanged sources with a predeclared analysis and uncertainty | No defensible numerical target can be calibrated from the existing unlabelled results. Do not invent “80% quality” or equate 13/16 contract passes with it |
| Comparative improvement | Report human-preferred wins, losses, ties, both-good/both-bad, factual failures and substantial strategic rewrites; require evidence of improvement and adequate absolute utility, not just a higher model score | Not measured; six endorsed anchors are development examples, not a blinded test set |
| Diversity | Selected records differ materially in thought/stake; actual history overlap is checked or explicitly unknown; number of worthwhile distinct directions meets actual slots where source supports them | No validated slate-diversity rate. Same purpose/type is not automatically a duplicate |
| Repeat reliability | Repeat unchanged requests and record idea/selection stability and human acceptability, not just record count | One W4 pair returned 9/10; no repeat quality labels or reliable variance estimate |
| Evaluator validity | Agreement with human-adjudicated distinctions, appropriate factual rejection and no irrelevant-detail vetoes; report order flips and disagreements | Earlier reviewers were never tested this way |
| Abstention | Known all-weak/no-op cases can return no recommendation and a useful reason; no forced per-source or weekly yield | Empty arrays are allowed; no all-weak editorial behavior test was performed |
| Held-out generalization | Freeze new source weeks, prompt/criteria/archive and evaluation protocol before generation; include every result/failure in the denominator | W5/W6 identified and reserved as candidates; zero validation generations performed |
| Cost/process integrity | Explicit approval of calls/models/payload/budget before dispatch; fixed call limit, no auto-expansion; report actual receipts and unknowns | Required user policy now explicit. No new calls here. An enforceable application approval gate remains proposed |

A numerical preference or acceptance target should be agreed after baseline labeling and before the next experiment's outputs are seen. If inferential statistics are used, choose the confidence criterion in advance and report whether the sample can support it. Neither two familiar weeks nor a handful of attractive examples supports a general reliability claim.

The six development anchors can form an enumerated regression gate: preserve their valid central claim and do not discard them solely for absent irrelevant facts. Passing those known cases is necessary diagnostic evidence, **not proof of performance on new material**. Allow other genuinely strong alternatives rather than requiring exact reference wording or identical priorities.

The current evidence does not meet a release gate for an autonomous final selector. That is a finding about evidence and capability claims, not an instruction to roll back or modify the current application during this phase.

## I. Implementation plan, ordered by evidence and cost

**Nothing in this section has been implemented during the diagnostic phase.** Preserve the current implementation and before snapshot. A later implementation requires its own explicit instruction, and any OpenRouter use requires separate approval of its concrete scope and cost.

| Priority | Proposed work | Expected impact / evidence | Cost and latency | Complexity / new risk |
|---|---|---|---|---|
| **P0** | Bind paid dispatch to an explicitly approved, immutable batch plan: exact requests/models/source scope, call limit and conservative cost allowance | High process value; directly addresses unapproved spend/extension. It is not a creative-quality fix | Local design/testing first; zero inference calls | Low–moderate; stale approval or changed requests must invalidate rather than silently broaden permission |
| **P1** | Build a small human-adjudicated benchmark from the actual six traces, education control, factual foil and no-op/weak slate; label current baseline blind where possible | Highest information value: resolves what success means and whether alternative framings are really weaker | Zero API cost; real editorial time | Low tooling; same author/known titles can compromise blinding, so record that limitation |
| **P2** | Correct research guard design before judging a replacement evaluator: unambiguous issue status; preserve inherited provenance application-side; separate relevant claim limits from model wording | High confidence technical repair of demonstrated false failures | Offline schema/validator tests and saved-response replay; no model call needed to demonstrate the literal-string issue | Low–moderate; never weaken actual factual constraints or silently overwrite raw failures |
| **P3** | Execute only the separately approved framing/discrimination screen in F; preserve every failure and stop at approved boundary | Distinguishes expression capability from comparative judgment instead of buying another full-week batch | At most four small calls in the proposed initial screen; **not approved or run**. Body-based estimate required before approval | Low experimental code; tiny sample diagnoses gross faults, not reliability |
| **P4** | If narrow abilities work, test pointer masking, missing setup restoration or response burden **one at a time**, guided by which failure remains | Targets salience/boundary/representation causes with actual evidence | Conditional bounded comparisons; no default extra call per week | Moderate; hiding useful context or overcompressing facts can introduce new errors |
| **P5** | Adopt the minimum task/representation correction supported by those results within existing builders/contracts; preserve original evidence and internal intelligence | Potentially restores central expression without another mandatory stage | Ideally same discovery + generation call count | Moderate; do not install another generic instruction appendix and call it a validated fix. Full schema changes only if the ablation justifies them |
| **P6** | Audit and expose eligible archive coverage, including actual published email concepts where admitted; retain same-week/model isolation | Strong evidence of a real coverage gap, especially buyer research | Local archive/provenance work first; no automatic inference needed for known records | Moderate; overaggressive novelty can suppress useful brand beliefs; indiscriminate history can contaminate comparisons |
| **P7** | Add comparative model selection or one targeted revision only if discrimination and slate benefit are demonstrated; otherwise retain human Gate 1 | Feasible function, unproven implementation. Do not infer benefit from a detailed rationale | Potential extra paid call(s); any such increase requires approval and measured value | Higher complexity; shared biases, order effects, invented repairs and misplaced completeness can worsen output |
| **P8** | Compare exact available models/settings on the identified failed narrow task; subsequently validate on frozen W5/W6 | Resolves model contribution only after task/context confounds are controlled | Conditional cost; current availability/pricing must be checked only with permission | Moderate; route/compute differences and small samples can create a false winner |

### Minimum effective change versus a larger architecture

The minimum justified next work is **measurement plus the demonstrated guard correction**, followed by the narrow capability screen if approved. The evidence does not yet identify a validated prompt replacement, model swap or multi-call architecture as the creative fix.

If a model can frame a supplied thought and recognize the human-preferred alternatives, the likely economical intervention is a better-defined central-thought task and calibrated comparison within the current flow, with evidence inherited rather than repeatedly rewritten. If it cannot discriminate reliably, keep final selection with the human editor while testing generation improvements. A separate reviewer becomes useful only after it earns that role empirically.

For code work later, start with the experimental validators and existing prompt builders, `Quality`/comparison policy and Gate 1 metadata. Reuse request hashes and artifacts. Do not change model routing, embedding policy, database schema or production scheduling merely because the previous result was disappointing. A paid critic, a schema reduction and a more expansive discovery pass are alternative hypotheses to test, not mandatory components of a “robust” system.

### Diagnostic stop condition

This report locates concrete losses, corrects overbroad conclusions, identifies two implementation-level reviewer-test defects, and specifies the smallest tests that could distinguish the remaining explanations. It does **not** claim that the creative problem has been solved or that model capability has been causally isolated.

The diagnostic phase ends here: **zero OpenRouter requests and zero application/prompt changes**. Only new research/audit artifacts were written. The existing implementation, original calls and baseline remain preserved. [The diagnostic verification record](root-cause-2026-10-16/diagnostic-verification.json) checks the application files and prior artifacts against their before hashes. Future implementation and any paid work are separate decisions.
