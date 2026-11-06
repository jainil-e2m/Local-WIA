# Phase N2: the minimal paid delivery run (23 and 24 October 2026)

This is plan section 5.0c, part 2: steps 2 to 7 of section 5.0a's "Next step" table, run on the working copy `atelier_work`. The readings were done by the implementing agent as WIA's delegated reviewer (R55, D12) and form the minimal gate (D40), one sample each.

**Keys.** The run up to brief 2's writing went on the Client OpenRouter key, which has a USD 2 limit, because the internal key was at USD 0 until its weekly reset on 26 October. On 23 October (19:00 UTC) the owner added a new internal key and gave the rest of N2 a ceiling of USD 1.50, then USD 0.75 more (USD 2.25 in all). Brief 2's validation and brief 3 went on that key and spent USD 1.7155.

## Setup

**The stack.** This is N1's stack, the repository's own: `backend/compose.yml` with `research/shakedown-2026-10/compose.shakedown.yml`. It runs:
- the production image in backend mode, with the API, scheduler, editorial worker, bulk worker and intake worker;
- the Atelier Frontend;
- Command Center.

It was pointed at the working copy with `STACK_DATABASE_URL` and `SHAKEDOWN_ARTIFACTS_DIR` (`atelier-work/artifacts`), and the Client key was passed as `SHAKEDOWN_OPENROUTER_KEY`. The N1 scratch database and its volumes were kept.

**Backup.** `atelier-wt/backups/atelier_work-2026-10-23-before-n2.dump` was taken before anything ran.

**What was applied before step 2:**
- the reclassification of `transcript_8223a163373716323e0b44f7` as internal;
- Gisselle's roster email;
- `context-seed`, `context-review-apply`, `context-published-points` and `context-entries-apply`;
- knowledge base 9 compiled and approved (`approved_pending_benchmark`);
- `production-settings.json`;
- the candidate profiles: strategist v7, card verification v4, scenes v3 under both extraction keys, contract v4 and writer v5.

**Knowledge base 9 for the runs.** It was held to its benchmark at first, so it was put in force with the `knowledge_base.version` pin (0.B8) rather than activated. Its reading below decided activation, and the pin was cleared afterwards.

## The steps

**Step 2: routes cached (USD 0).** `token_budget --model <m> --store` was run for `openai/gpt-6-luna`, `openai/gpt-6.1-sol` and `anthropic/claude-sonnet-5.5`. The snapshots are in `atelier-work/artifacts/provider_catalog/`.

**Step 3: October calls embedded (6.B18; USD 0.0033).**
- Estimate: 241 chunks from 11 included calls, USD 0.003.
- `documents reembed --mode live` ran on the stack's bulk worker: "All 241 transcript chunks encoded and verified".
- Three more included October calls (Judy 9 October, Rose 8 October, The Penny 13 October) were checked. Every current chunk already had a vector; only superseded chunks from the old segmentation have none.

**Step 4: delivery window extracted (E.B31; USD 0.0908 against an estimate of 0.046).**
- `moments extract --from 2026-10-12T00:00:00-05:00 --to 2026-10-20T00:00:00-05:00` ran with scenes v3 on Luna and knowledge base 9, on the bulk queue.
- 7 documents, each succeeding on its first attempt.
- 147 verified scenes, 6 quotes repaired.
- **K13 holds:** the longest call, The Brightside (35 scenes), took 106 seconds. The slowest call took 133 seconds, against a limit of 3,600.

**Step 5: the October cycle (USD 0.7976; preview estimate 0.63).**
- Started from the app: 12 to 20 October, 7 calls, with the preview and its estimate shown first.
- Run `run_2140fa0b66b64a7e9325705557cc29bd`. It reused the 147 scenes, so there was no new extraction.
- Strategist v7 on Sol: one call, 188,604 input and 13,993 output tokens, USD 0.6114, 426 seconds.
- Card verification v4 on Sonnet: one call for all cards, USD 0.1862.
- Five ranked cards.

**Step 6: the brief (USD 1.0019, of which USD 0.1436 was a lost answer).**
- Card 1 was developed after Gate 1 corrections (below). Its brief started by itself: run `brief_run_3dc7bce67c2a295fc22913c7`, brief `brief_579f970d9210bc9be2cfbfde`.
- The research step failed twice before succeeding: two defects, below.
- Validation then waited on the briefs budget. Its worst case of USD 0.22 exceeded the USD 0.22 left, and the job waited with that reason in the app. USD 0.25 was moved from refreshes to briefs, keeping the USD 3.50 total, and validation completed: "Brief ready for Gate 2".

**Brief calls:**

| Call | Model | Cost (USD) |
| --- | --- | --- |
| Research plan | Sonnet | 0.0190 |
| Grade, answer lost | Sonnet | 0.1436 |
| Grade | Sonnet | 0.1485 |
| Plan, round 2 | Sonnet | 0.0223 |
| Grade, round 2 | Sonnet | 0.1304 |
| Write | Sol | 0.1700 |
| Verify | Sonnet | 0.1976 |
| Repair | Sol | 0.1530 |
| Verify again (changed claims only) | Sonnet | 0.0175 |

**Brief 1 cost USD 0.86 without the lost call, against the plan's USD 0.43.**

**Briefs 2 and 3 were not started on 23 October's first pass.** The Client key had USD 0.60 left, below one brief, and the stop rule says a run whose estimate passes the remainder is not started. They were run later the same day ("Briefs 2 and 3" below).

**Step 7: the configuration of record (USD 0).**
- `backend/deploy/production-settings.json` names every part that passed: scenes v3, strategist v7, card verification v4, contract v4 with writer v5. Knowledge base 9 is recorded as the active version on the working copy (`kb-benchmark --passed`), and N3 restores it with the dump.
- The standing caps were set so this week's remainder fits the key:

| Purpose | Cap (USD) | Left (USD) |
| --- | --- | --- |
| Cycle | 0.80 | 0.0024 |
| Briefs | 1.01 | 0.0081 |
| Refreshes | 0.25 | 0.25 |
| Extraction | 0.20 | 0.1092 |
| Embedding | 0.05 | 0.047 |
| Context mining | 0.05 | 0.05 |
| **Total** | | **about 0.47**, against the key's 0.60 |

**At the 26 October renewal the caps go back to D36's** with `budgets set`: cycle 1.20, briefs 1.20 (see the cost finding), refreshes 0.50, extraction 0.40, embedding 0.10, context mining 0.10.

**Briefs 2 and 3 (23 October, finished on the new internal key).** The owner asked for N2 to be finished, so brief 2 was started on what the Client key had left; it and brief 3 were finished on the internal key the owner added, within the ceiling the owner set.

*Brief 2 on the Client key (what it had left):*
- **Budgets.** The briefs budget was given the key's USD 0.55 remainder (cap 1.55, then 1.60) and the other budgets were closed (cycle 0.7976 and extraction 0.0908, each at its spend; refreshes, embedding and context mining at the USD 0.01 minimum). A call that does not fit therefore waits with its reason instead of meeting the key's limit.
- **Card 2** was developed from the app with a delegated note: run `brief_run_abbe14b8d1e173dbdaec21c9`.
- **Done so far:** research (two rounds: plans USD 0.0268 and 0.0285, grades 0.1340 and 0.0969) and writing (Sol, 0.1769). Total USD 0.4630.
- **Validation waits:** "next call could cost up to USD 0.23", against USD 0.14 left on the key.
- **To finish:** after the internal key's reset, switch the stack's key and raise the briefs cap (D42). The waiting job then runs, and its saved answers replay at no cost.
- **What is left:** brief 2's validation (about USD 0.2 to 0.4) and brief 3 on card 5 (about USD 0.86), about USD 1.25 in all.
- **The stack** was stopped again after the wait.

*The rest on the new internal key (ceiling USD 2.25):*
- **Budgets.** The stack was rebuilt from `main` and started on the internal key. The briefs cap was set to this week's spend plus the ceiling (USD 2.93, then 3.68 when the owner added USD 0.75); every other purpose stayed closed at its spend or USD 0.01. The app's briefs record and the key agree to USD 0.0002.
- **Brief 2's validation** was released by the raised cap: verify (Sonnet, USD 0.1912), repair (Sol, 0.1679), verify again (0.0517). **Brief 2 cost USD 0.8738** in all: `brief_b2ad696069930da13b4e2c4d`.
- **Brief 3: card 5** (`angle_42805fa134964598862f84e41aac1666`, corrected at Gate 1) was developed from the app with the delegated note, after its "verify before publishing" item was ticked under D12: run `brief_run_4627ca9337fde751045f1141`. Research (two rounds: plans 0.0787 and 0.0802, grades 0.1867 and 0.1857) and writing (Sol, 0.1811) went through.
- **Its validation was cut off.** The claim check of 126 statements used 8,601 reasoning tokens and stopped at statement 100, at its 16,000-token output limit (USD 0.2459 spent, nothing usable). The step failed with "the model's answer was cut off". Two defects lay behind it (defects 4 and 5 below): a structured answer cut off part way was never retried with a raised limit, and retrying the step replayed the cut-off answer and failed again without a call. The output limit was frozen into the run, so raising it would have voided brief 3's research and writing.
- **After the fix,** with `models.completion_tokens` at 32,000 on the working copy, "Try this step again" ran: verify (0.2515, 16,567 output tokens, which the old limit would have cut), repair (0.0752), verify again (0.0199). **Brief 3 cost USD 1.3049,** of which USD 0.2459 was the cut-off call: `brief_57502d2280064c9564925d56`.
- **The stack** was stopped at the end, and the briefs cap closed at its spend (USD 3.1807).

## Gate 1 (delegated, R55)

The cards were read in the app. Unsupported facts the verifier flagged were corrected with "Edit this card"; each edit is a new card version, with its embedding and matching at no model cost.

- **Card 1** ("How we decide whether to replace a client's existing page"): the audience and point named a "website designer" and a "venue" the call never mentions. Both were corrected, the verify item was acknowledged, and the card was **developed** with a note.
- **Card 2** ("How we handle a new ad a client doesn't love"): the invented motive "because their approval matters" was removed, and the client's name, which is only a device label, was dropped. Left for Whitney's decision.
- **Card 5** ("What goes into our decisions about competing venues"): the point was narrowed to what the scene shows. Erin's unstated role ("marketer") became "the client's team", with the verify item reworded and a note. Left for Whitney's decision.
- **Cards 3 and 4:** left pending for Whitney. Card 3 fails test 3 on this reading; card 4 carries the verifier's one blocking flag.

## Card reading (step 5): passes

| Card | Point is about | Verdict | Flags |
| --- | --- | --- | --- |
| 1 | a WIA standard | Meets 4.2; the five tests pass | Two checks, one of them the only deterministic flag ("How we decide" generalises one scene) |
| 2 | a client's experience | Meets 4.2 | Three checks: invented motive, frequency, speaker label |
| 3 | a WIA belief | **Fails test 3.** The reader's takeaway is a messaging tactic for their own ads ("I hadn't thought of my team's ability to move quickly as a reason couples could choose us") | One check |
| 4 | a WIA standard | Held: `research_required` | The verifier's one **blocking** flag (an invented reason: the scenes never say why Whitney asked for "what actually happens"), plus two checks |
| 5 | a WIA standard | Meets 4.2 narrowly: a view of WIA's judgment, not a keyword tutorial | Three checks: overclaim, Erin's role, offer |

**Why the reading passes:**
- No deterministic flag blocks.
- Three public cards (1, 2 and 5) meet section 4.2: plain titles, Whitney's six fields, and the point passing the five tests.
- No idea is of a kind WIA rejected: no platform lesson, no office-hours walkthrough.
- No card takes a public stance.
- Every binding is `bound` to a verified scene, either by its exact span (cards 4, 5, and one point of card 2) or by the verifier's scene match.

Contingency A was not run.

## Brief reading (step 6): passes

**Checks.** No content-level blocking finding. The two blocking findings are Gate 2's own procedural items: the writer's CTA awaits a person, and the required before-publishing items are unanswered. There are 12 warnings, most of them "a recommendation that cites neither a turn of the call nor a knowledge-base document" on outline and format lines. One is substantive: Reel 2's screen "before replacing them" implies a replacement the call doesn't show.

**W3 to W8:** none recurs.
- W3: the subjects ("A new landing page still has something to prove"; "Does your current ad page need replacing?") state WIA's point or the reader's question, never a narration of a third party.
- W4: slide 1 carries the carousel title's promise.
- W5/W7: the covers name the landing page.
- W6: no insider term in first-touch text ("LeadLock" appears only inside a call quote).
- W8: the b-roll screens tell the turn of the story, and the actors are exact ("our team", "Whitney").

**4.3, on this reading:**
- The email has its send header, an opening scene, short paragraphs, one bold line, ELEVATE with its descriptor, a reply CTA, "Talk soon, Whitney", no bullets and no "DM".
- Reel 1 runs 86 seconds, with personal lines flagged and no "Okay, so".
- There are two Reels, with the stance Reel omitted and its reason given (D30).
- The carousel has 7 slides, with "we" and "us" and both readers named on slide 7.
- Weaknesses: dense carousel paragraphs, kicker-like caption endings, the repeated "rather than" contrast, and no client words in Reel 1's script.

**Blind reading against the three writer v4 briefs of 20 October** (`blind-reading/reading.md`): ranked A (writer v5), then C, D and B (all writer v4). The reading prefers v5. Contingency B was not run.

## Brief 2 reading (card 2, "How we handle a new ad a client doesn't love"): passes, with a Gate 2 rewrite to ask for

The full brief is `brief-2.json`; the reading was done by the implementing agent (D39) on the whole brief with its evidence and checks.

**Checks.** No content-level blocking finding. The stored checks show 11 blocking findings; eight of them, "The (not WIA staff) is named in the public narrative", are false (defect 6 below, fixed). Recomputed with the fix, three remain, all Gate 2 procedure: the CTA proposal, a public quotation's clearance (Whitney's own "no hard feelings" line) and the required before-publishing items. The 11 warnings are the usual "a recommendation that cites neither a turn nor a document" on outline lines, and the carousel CTA warning (slide 7 does name both readers; the check is too strict there).

**Story fidelity: faithful but thin.** Nothing is invented: the client's reaction stays tentative ("not a completed rejection"), Whitney's offer of edits or non-use is credited and quoted, and P5 keeps "the ads were poor" and the ambiguous quick-review line out. But the copy never tells what the client said, so the email and Reel 1 argue the principle without the moment that proves it.

**W3 to W8:** none. The subject "Can I say no to an ad my agency made?" is the reader's own question, the covers name the ad, slide 1 is the carousel title, no insider term. Reel 2's b-roll leaves out the client's hesitation, the turn of the story.

**4.3:** the email has its send header, a bold line and "Talk soon, Whitney", but no offer and no reply CTA, by the card's own guardrail (a WARM piece with no ask). Two Reels with the reason given; Reel 1 about 78 seconds; carousel of 7 slides with both readers on slide 7.

**Weaknesses for Gate 2:** abstract and repetitive voice ("room", "space", "judgment" in every asset; kicker endings); Reel 1 tells no story; P1 holds the client's situation out of public copy until permission, while every asset is built on it, so permission decides whether the brief runs at all.

## Brief 3 reading (card 5, "What goes into our decisions about competing venues"): passes, with one fidelity fix for Gate 2

The full brief is `brief-3.json`.

**Checks.** No content-level blocking finding: the two blocking findings are Gate 2's CTA and before-publishing items. There are 22 warnings. Two name covers that do not say what they are about ("A competing venue's search needed context"; "Competing venues need local context").

**Story fidelity: one real paraphrase problem, caught by the verifier.** On the call, Erin said of a bigger venue: "we have gotten some people that are, like, we can't afford them, but we could afford you". The brief says couples "had considered a nearby venue before considering theirs", in the email, both Reels and slide 3. Neither "nearby" nor "before" is in the call. The card's guardrail keeps price comparisons out, so the writer replaced the real reason with an invented one, and the repair kept it. Six verifier warnings flag exactly this. **For Gate 2:** say that couples who looked at a bigger venue had come to them instead, which keeps the price out without inventing a reason. Everything else is exact: Carmen as WIA's Google Ads lead, Erin only as "a member of the client's team" (P2), the Hamptons venue as a different market, and Carmen's agreement as a recommendation, not a completed change (P3).

**W3 to W8:** none blocking. The subject "We don't rule out a venue search by its name alone" states WIA's point; slide 1 is the title; no insider term (the Google Search Accelerator carries its descriptor). Reel 2's first screen names "Carmen" without her role.

**4.3:** met in full. The email has its send header, an opening scene, one bold line, the Accelerator with its descriptor, a reply CTA and "Talk soon, Whitney". Two Reels with the reason given (Reel 1 about 85 seconds). A 9-slide carousel with both readers on slide 9 and the only Instagram offer CTA.

**Weaknesses for Gate 2:** the fidelity fix above; the covers; the same two-part line ("we bring the advertising expertise, the client's team brings ...") repeated across assets.

## Blind reading 2: the three writer v5 briefs against the three writer v4 briefs (`blind-reading-2/`)

Six briefs, rendered by the same `blind.py` and shuffled under neutral letters: N2's briefs 1 to 3 (writer v5, contract v4) and the three writer v4 briefs of 20 October (contract v3). The reader was a subagent of the implementing session (D39, D40): it read only the six files and the plan's sections 3.2 and 4.3, with the key kept outside its reach until it had scored and ranked them. No paid model ran.

| Rank | Brief | Configuration (from the key) | First-touch | Story fidelity | Voice | Structure (4.3) | Publishable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | E | writer v5: brief 3 | 4 | 5 | 4 | 5 | 4 |
| 2 | B | writer v5: brief 1 | 4 | 5 | 3 | 5 | 4 |
| 3 | C | writer v5: brief 2 | 4 | 3 | 3 | 3 | 3 |
| 4 | D | writer v4: `brief-d0e9fbc9` | 3 | 4 | 2 | 2 | 3 |
| 5 | F | writer v4: `brief-d4f2db12` | 3 | 3 | 3 | 2 | 2 |
| 6 | A | writer v4: `brief-1f79f6d4` | 2 | 3 | 2 | 1 | 1 |

**All three writer v5 briefs rank above all three writer v4 briefs.** The reader's summary: only E and B deliver the whole 4.3 skeleton; C has the best subject line but "never tells what the client said"; the v4 briefs lose the send header, the second Reel and the carousel title, and A repeats "office hours" in every asset. Its full findings are in `blind-reading-2/reader.md`.

**What the blind reader could not see:** the call. Its fidelity score of 5 for brief 3 is a reading of the brief alone; against the evidence, the "nearby" paraphrase above stands, and is a Gate 2 fix. Layout differs between contracts v3 and v4, so the reading is blind to the configuration names but not fully to the layout, as in the first blind reading.

## The hand-off views: checked

`GET /storage/briefs/{id}/handoff` was read through the app for all three briefs. Each returns `brief_handoff_v1` with four pieces (`reel_1`, `reel_2`, `carousel`, `email`), the anchor by rule (`reel_1`: "the first Reel; else the carousel; else the email; else the caption; else the stories"), the message spine, the claims, the before-publishing items and the evidence. Each has `can_consume: false`, as it should: Gate 2 has not approved them, and the blockers it lists are the CTA, the before-publishing items and the history acknowledgement (brief 2 adds the quotation clearance). Brief 2's view showed the false "The (not WIA staff)" blocker on the image built before defect 6's fix, and not after it.

## The brief-done checkpoint: holds (24 October)

1. **N2's exit is met in full:** three briefs on the configuration of record (contract v4, writer v5, knowledge base 9), each with no content-level blocking finding and its reading recorded above; the blind reading prefers all three to writer v4.
2. **Each brief's hand-off view** carries every asset's copy with its piece key, the anchor and the message spine, checked above; a pack stage consumes a brief only when `can_consume` is true.
3. **The configuration of record** is in `production-settings.json`, now with `models.completion_tokens` at 32,000.

Brief work stops here (plan revision 8.4): a brief changes only for a defect that a live week or the pack stage finds. The Gate 2 points above (brief 2's story, brief 3's paraphrase, the covers) are Whitney's edits at Gate 2, not more brief engineering.

## Knowledge base 9 reading: passes, narrowly

The record is `kb9-reading.wia-kb-2026-10-22.c-a1a75795.json`.
- **This run:** one blocking accuracy flag in five cards, and no card without WIA's contribution.
- **Version 8's recorded runs** (`research/benchmark-v1/results/2026-10-20-strategist_v6.wia-kb-2026-10-20.c-6bf62f94.json`): 0 to 1 a run, with means of 0 (Week 1) and 0.33 (Week 2).

The run equals version 8's worst run and is above its mean, on a different window and with a stricter verifier (v4). The brief raised no content-level blocking finding.

It is recorded as the version's benchmark (`kb-benchmark --passed`, decision `decision_d66dda946aeb424993dbff1119d29515`) and is the active version on the working copy. Version 8 is the switch-back.

Version 9 is also the committed default file knowledge base, promoted the way commit 910e91d promoted version 8: version 8 moved to `backend/knowledge_base/archive/wia-kb-2026-10-20.c-6bf62f94/`, the pins followed, and DEPLOYMENT.md step 5 compiles it as `unchanged`.

The figures check (`test_strategist_v5.py`) finds two figures in it that wording cannot clear:
- "90 events" is the published ELEVATE result, 17 to 90 events, in Whitney's own Reel in document 19.
- "17 weddings" appears only in document 19's note naming her slip, which RR-10 blocks in copy.

The check pins exactly those two, so any other figure still fails it.

## S.B8: the replay in a fresh container (USD 0): passes

1. `atelier_work` was copied into a fresh `atelier_sb8c`, and brief 1 and its run were removed there.
2. The same production image (`content-atelier-backend:local`) ran with `replay.env`: DEPLOYMENT.md's editorial variables, with no key, no plan and no generation switch.
3. It ran `storage_cli brief --angle-id angle_835445840224445487b8ed1352f85dcd --mode replay` and then `storage_cli worker`.
4. All five stages completed.
5. All 8 model calls were `replayed` at USD 0, with no dispatch and no refusal.
6. The replayed brief's document is byte-identical to brief 1's (md5 `5fea40d8c7070bfd05e675b076621dfa`).

The writer step that 20 October's S.B8 left open is now done: the stack's editorial worker, which is the production image from the documented variables, wrote brief 1 live.

## Defects found by the paid run, fixed at their cause with a test (stop rules applied)

1. **A lost answer was never charged** (`llm/transport.py`, `llm/failures.py`). Sonnet's first grade call was cut off mid-body after 341 seconds (`RemoteProtocolError`). The key was charged USD 0.1436, but the briefs plan recorded nothing, so the standing caps under-counted real spend.
   - Fix: a request that was sent but whose answer was lost (closed mid-body, read error or read timeout) now settles at its worst case. The app says "the answer was cut off on its way back … the budget counts it at its most" instead of "could not be reached".
   - Test: `test_run_plans.py::test_a_call_whose_answer_was_lost_after_sending_counts_at_its_worst_case`.
   - The working copy's record of the lost call was corrected to the key's actual charge.
   - The step's one retry (the stop rule) then ran on the rebuilt image.
2. **One miscopied evidence ID failed the whole research stage** (`briefs/workflow.py`). In the retry's second round, Sonnet graded all 47 items but wrote `ev_bf85af6b4cc4878d4aa1c966` for `ev_bf85af6b3cc4878d4aa1c966`. The coverage check discarded USD 0.30 of correct grading.
   - Fix: `repair_graded_ids` repairs a graded ID that is one character off exactly one ungraded delivered ID, and records the repair in the dossier's audit. This follows the quote rule: a near-miss is repaired and recorded. Wider differences, ambiguous IDs and duplicates still fail.
   - Tests: `test_brief_paths.py::test_a_miscopied_evidence_id_in_the_grading_is_repaired_only_when_it_is_unambiguous` and, end to end, `test_briefs.py::test_a_grade_with_one_miscopied_evidence_id_is_repaired_and_recorded`.
   - The re-run replayed the four saved research responses at USD 0. Only stages on their first attempt spent.
3. **The cycle preview under-estimated the strategist by half** (`cycle/window.py`). It sized each scene by its record (1,313 characters on average). The strategist reads each scene with the call turns it spans, about 4,300 characters, so it sent 188,604 tokens against about 78,000 estimated (USD 0.61 against 0.32).
   - Fix: the estimate counts the spanned turns (`evidence_refs`). On the October window it now gives about 189,000 tokens.
   - Test: `test_cycle_window_db.py::test_the_strategist_estimate_counts_the_call_turns_each_scene_carries`.
   - Card verification's estimate (8 calls) stays conservative; v4 verifies all cards in one call.

The free models could not show any of the three: they are a paid model's long-answer transport failure, a paid model's ID-copy error, and the size of a paid packet.

**Found finishing briefs 2 and 3:**

4. **A structured answer cut off at its output limit was never retried** (`llm/transport.py`, `llm/providers.py`). E.B1's one retry with a raised limit covered only an answer with *no* content at the limit. Brief 3's claim check wrote 100 of its 126 verdicts and stopped at 16,000 tokens, 8,601 of them reasoning, and part of a JSON answer is no answer.
   - Fix: a JSON call's answer cut off at its limit is asked once more with the raised limit (twice the cap, at least 24,000, at most 64,000), as its own planned call that the budget checks first. A text answer is not retried; a refusal or a complete answer never is.
   - Tests: `test_llm_module.py::test_a_json_answer_cut_off_part_way_is_asked_again_once_with_a_raised_limit`, `test_a_cut_off_answer_from_a_caller_that_reads_text_is_not_retried`, and the updated repair test.
5. **Retrying the step could never get past a cut-off answer** (`llm/workflow.py`, `briefs/runtime.py`). A step retry reuses its job, and recovery found the cut-off answer saved by the failed attempt and failed on it without a call. And the output limit was part of the run's frozen contract, so raising it would have failed the run with "contract changed" and cost the research and writing again (about USD 1).
   - Fix: recovery skips an answer cut off at its limit, so the retry makes the call again at the limit the settings now give. The output limit is an operating limit, like a confirmed price: it is no longer part of what must stay frozen, and each call's request still records the limit it was sent with.
   - Tests: `test_briefs.py::test_raw_received_before_exception_is_recovered[length]` (now asked again, not failed) and `test_context_closeout.py::test_a_raised_output_limit_does_not_stop_a_run_in_flight`.
   - **Why the cap exists at all** (the owner's question): it does nothing for quality; a call is billed for what it writes. It sets the output reserve that a budget checks before sending (the call's worst case), gives the provider a known figure, and stops a runaway answer at a known cost. So it should never bind in normal work: `production-settings.json` now sets 32,000, and the retry covers the rare case that still runs out.
6. **A meeting label was searched for by its first word** (`briefs/validation_v2.py`). The speaker "The Organic Moment Photo + Video" was looked for in public copy as "The", which every brief contains: eight false blocking findings on brief 2. The same rule looked for "Steve’s iPhone" as "Steve’s", so copy naming "Steve" would have passed.
   - Fix: `outside_name` takes the label's first word that is a name (no article, device or room word, no possessive), and each name is reported once.
   - Test: `test_brief_v2.py::test_a_meeting_label_is_matched_by_the_name_in_it_once`.

## Findings for the owner

- **A brief costs about USD 0.86, not 0.43, on this configuration.** The costs: two research rounds on Sonnet (0.32), the Sol writer (0.17), Sonnet's verification at high reasoning effort (0.20), a repair (0.15) and a short re-verification. **D36's weekly briefs cap of USD 1.20 covers one brief a week, not three.** Three briefs a week need about USD 2.6 for briefs alone. Either the briefs cap or the weekly budget rises, or the verifier's effort or model changes (a settings change, judged on a live week).
- **The cycle costs about USD 0.80** with strategist v7 on a full week (188,604 input tokens), against the plan's 0.3 to 0.5.
- **Briefs 2 and 3 confirm the cost:** brief 2 USD 0.87, brief 3 USD 1.06 without its cut-off call (1.31 with it). A brief costs USD 0.86 to 1.06; three a week need about USD 2.6 to 3.2 for briefs alone (D42).
- **N2's exit is met in full** (24 October): three briefs, their readings, the blind reading, the hand-off views and the brief-done checkpoint above.

## Spend

| Key | Before N2 (USD) | N2 (USD) | Left (USD) |
| --- | --- | --- | --- |
| Client (limit 2) | 0.0034 (N1) | 2.3566 (1.8936, then brief 2's research and writing 0.4630) | 0.1400 |
| Internal (new key, USD 15 a week) | 0 | 1.7155 (brief 2's validation 0.4108; brief 3 1.3049), against the owner's ceiling of 2.25 | 13.2845 |

The N2 total, USD 4.0721, breaks down as embedding 0.0033, extraction 0.0908, cycle 0.7976 and briefs 3.1807 (brief 1 1.0019, brief 2 0.8738, brief 3 1.3049, the rest replays at 0). The standing plans' records match the keys within USD 0.0003.

## State left

- The delivery stack (`atelier-shakedown`) was stopped at the end, with its volumes kept, so no worker holds a live key unattended.
- The standing caps on `atelier_work` are closed at this week's spend (briefs USD 3.1807; cycle 0.7976; extraction 0.0908; refreshes, embedding and context mining 0.01). **At the 26 October renewal they go back to D36's** with `budgets set` (briefs per D42).
- `models.completion_tokens` is 32,000 on `atelier_work`, as in `production-settings.json`.
- The working copy `atelier_work` holds everything above.
- The scratch database `atelier_sb8c` holds the replayed brief.
- Restart the stack with the same compose, `STACK_DATABASE_URL` and `SHAKEDOWN_ARTIFACTS_DIR`.

## Files

| File | What it is |
| --- | --- |
| `review-document-week_2026-10-12.md` | The week's review document (export of record) |
| `cycle-cards.json` | The five cards as generated, before the Gate 1 edits |
| `brief-1.json`, `brief-2.json`, `brief-3.json` | The three briefs' rows |
| `kb9-reading.wia-kb-2026-10-22.c-a1a75795.json` | The knowledge base 9 reading |
| `blind-reading/` | The first blind reading (brief 1 against writer v4): inputs, the key, `blind.py` and the result |
| `blind-reading-2/` | The second blind reading (briefs 1 to 3 against writer v4): inputs, the key and the reader's full findings (`reader.md`) |
| `replay.env` | S.B8's container variables |
