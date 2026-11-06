# Reproducing WIA's editorial judgment through OpenRouter

This investigation concerns the six Week 3–4 directions in the 16 October copywriting analysis. They are reference examples endorsed in the present request, not measured winners or an exhaustive answer key. Findings below distinguish observed artifacts, editorial interpretation and controlled tests. Nothing has been published, scheduled or pushed to GitHub.

## A. Executive diagnosis

**The verified gap is between developing source-grounded candidates and making a comparative Reel recommendation.** The earlier API run produced a broad set of proposals. The IDE review compared those proposals, reread relevant source passages, used six approved scripts as taste evidence, excluded weak or previously covered material, and recommended a small slate. These are different tasks with different context. Candidate count is not publishing cadence.

Evidence ranked by strength:

1. **Verified: different editorial context and task.** The API requests did not include `instagram_reel.md`; the successful IDE analysis did. Its explicit user instruction asked for copywriter judgment, actual comparisons, exclusions, revised directions and depth restraint. Historical signatures in the pilot were empty. Existing instructions already asked for broader meaning and plain language; this was not simply an absent 'zoom out' instruction.
2. **Verified: source was often available before framing weakened.** Baseline Sol's offer-economics candidate already recognizes the owner's commercial question. Carmen's creative decision and the Week 4 owners' desire for guidance are present in the supplied context. The generator often foregrounds an operating principle or tool distinction rather than the more consequential thought in its own rationale. This is a formulation and selection problem for those cases.
3. **Verified: no downstream similarity removal explains the pilot.** Embeddings, history matching, ranking and refinement were disabled. The 9/10/9 Week 3 counts came directly from the three generation responses. Valid JSON and high self-scores did not establish creative quality. Production SQL comparison has additional stages, but they did not execute in this pilot.
4. **Observed limitation: discovery is not complete recall.** The shared extraction omitted some potentially usable process material, including a local-targeting clarification without measured results. The IDE recommendation nevertheless depends substantially on that same shared shortlist; it does not prove independent superior raw-transcript discovery.
5. **Unestablished: model capability as the primary cause.** The IDE serving model and internal compute allocation are not recorded in the analysis artifact. Context, instructions, candidate visibility and number of editorial steps changed together. Different model names alone cannot explain the result.

**Experimental conclusion:** sixteen new paid calls cost **USD 4.95712137** in returned provider receipts. Instruction-only changes improved some wording without producing a selective slate. Adding approved examples improved known-case exclusion, but still returned broad candidate sets. A source-analysis intervention recovered some material and lost other strong material. An extra selection/refinement call did not consistently make the desired editorial choices and failed strict boundary-retention checks. **None of these interventions consistently reproduced the six reference directions' standard.** The tested calibration is implemented; the unproven additional stage and revised extraction are not installed. A better-looking sample does not establish reliable approval or generalization.

## B. Context and pipeline reconstruction

### What the IDE actually used

The visible prior task and its local artifacts establish a multi-step editorial review, not a single full-transcript generation. It read all six scripts in [the approved corpus](../corpus/instagram/instagram_reels/instagram_reel.md), the existing Week 3 model reviews and canonical outputs, relevant Week 3–4 evidence packets and original surrounding passages, the project agenda, the angle specification and the active prompt construction. Earlier conversation supplied Whitney's feedback on broader significance, collaboration, brand positioning, dry wording, repetition and internal intelligence.

It grouped 28 Week 3 proposals into eleven treatment families, compared them with approved content, and produced [the six revised directions](2026-10-16-instagram-reel-copywriting-analysis.md). The [exact inventory](2026-10-16-reel-copywriting-angle-inventory.md) preserves what the API actually proposed. The IDE did **not** independently reread all eleven complete raw transcript exports. It reread selected full context intervals from the extracted evidence. Its revised Week 4 directions were new editorial proposals from 17 reviewed source moments: no returned Week 4 angle output was available at that time.

This supports a reconstruction of visible editorial operations. It cannot reveal private reasoning, establish an exact hidden prompt, quantify attention, or prove that the agent consciously followed the methodology inferred below. The complete user copywriter brief is visible in this chat; there is no separate saved single-request payload that reproduces the whole IDE context.

### Actual source and request path

| Stage | Implementation and actual behavior | Material implication |
|---|---|---|
| Discovery / ingestion | `prepare.py:read_source`, `weekly.py:load_compact_week`; frozen Zoom `.txt` exports, five W3 / six W4 files, 1,837 / 1,803 turns | Lossless turn delivery; source week labels are not confirmed publication dates. No Fathom material silently substituted. |
| Moment extraction | `prompts.py:weekly_moment_prompt`, extraction system + WIA strategy + editorial policy + `moment_extraction.weekly_v3.md`; complete weekly cue packet and trusted inventory | A genuine source-discovery stage already exists. Luna interprets as well as quotes. Its interpretations remain provisional. |
| Reference expansion | `weekly.py:resolve_moment_references`; `pipeline.py:_parse_moments` | Resolves cue IDs, expands every turn between context bounds, checks containment, chronology and literal anchor quote. It does not prove semantic completeness or correct interpretation. |
| Context assembly | `pipeline.py:_moment_packet` | Supplies moment records **and original surrounding dialogue**, revision hashes and source metadata. The angle model is not limited to one-line summaries. Upstream omissions remain unavailable. |
| Angle generation | `prompts.py:angle_prompt`, `angle_generation.system.md`, `angle_generation.user.md`, strategy/policy, moment packet, empty prior-signature list | Each model performs source reinterpretation, public/internal routing, formulation, comparison, exclusion and self-scoring in one candidate call. No separate editorial critic ran. |
| Provider | `provider.py:chat_body`, `LiveProvider.json_call` | Two messages, JSON object mode with full schema appended at system authority; high reasoning; exact model ID; no tools; no automatic fallback/retry. |
| Validation / records | `pipeline.py:_call_json`, `_parse_angles`, `models.py:StageArtifact`, `store.py` | Original request/raw response, parsed output, costs, hashes and run lineage retained. IDs/coverage/assertion prefixes checked. The parser does not certify the truth of every assertion or creative appeal. |
| Pilot presentation | `model_experiment.py` and `reviewed_experiment.py`; independent cell data roots | Generated candidates remain independently inspectable. No embeddings, history, SQL merge or refinement can contaminate a later model's pilot input. |
| Application SQL flow | `sql_pipeline.py:SQLWorker`, `comparison.py:history_context/evaluate`, `repository.py:save_moments/save_angles` | SQL mode can freeze archive context, generate, embed, assess, refine and reassess. It preserves source associations and parent replacements. This is a separate execution path from the pilot. |
| API / UI | `api.py`, SQL repository projections and `frontend/server/app.mjs` proxy | Browser-facing data derives from stored objects; the frontend did not silently rewrite the raw pilot candidates. Human approval and later brief work are separate from generation. |

The configured local PostgreSQL connection was attempted read-only during this investigation and was unavailable (`OperationalError`). SQL behavior here is code-based reconstruction, not a claim that new SQL jobs or migrations ran. The JSON artifacts provide the authoritative records for this comparison.

### Exact baseline configuration

The canonical suite is `testing/.data/experiments/week3-week4-shared-luna-angle-quality-20261015/`. Prepared request files under `cells/week{3,4}/{luna-pro,sol,sonnet}/prepared-angle.request.json` establish these exact routes:

| Role / alias | Exact requested model | Reasoning | Sampling / budget |
|---|---|---|---|
| Shared weekly extractor / Luna Pro | `openai/gpt-6-luna-pro` | high | No temperature; no explicit completion cap |
| Luna Pro angles | `openai/gpt-6-luna-pro` | high | Same |
| Sol angles | `openai/gpt-6.1-sol` | high | Same |
| Sonnet angles | `anthropic/claude-sonnet-5.5` | high | Same |

The client removes temperature for these exact routes. Therefore 'temperature 0.2' would describe the generic builder default, **not** these actual requests. Provider `require_parameters` is true and `allow_fallbacks` false. `usage.include` is true. No output cap does not mean unlimited generation: provider limits apply. No tools or external search were enabled. Full input was sent without truncation or automatic splitting. A conservative UTF-8 byte allowance, explicitly not native token counting, checks the saved route catalog. Timeout in the prepared setup is 900 seconds.

The environment's generic default is `openai/gpt-6-luna`; the comparison explicitly overrides it. Do not infer Pro from a display label or assume the experiment changed `.env`. All three angle calls receive identical messages for a week and a single shared Luna pool. They do not inherit another angle model's response.

Week 3 yielded 18 accepted moments, then 9 Luna / 10 Sol / 9 Sonnet candidates and eight internal insights each. Week 4's original 17-moment response failed literal quote validation; a separately approved derivative changes two quote fields only. Its 17 reviewed moments are not a successful original extraction. The old Week 4 Luna angle dispatch has no returned raw response or result; its charge remains unknown. This investigation neither retries it nor clears its marker. Original Sol/Sonnet Week 4 cells had not dispatched; the new baseline cell is explicitly separate.

## C. Forensic analysis of the six reference directions

Source IDs below resolve to original passages in the [Week 3 source review](week3-week4-comparison-2026-10-15/week3-shared-moments.md) and [Week 4 reviewed source review](week3-week4-comparison-2026-10-15/week4-shared-moments.md). Timestamps refer to those recordings. Openings and interpretations are proposed editorial language, not quotations or observed audience reactions.

### 1. Was the quieter offer's advertising worthwhile? — W3 priority

**Source.** `moment_685c9db487511394f76b1711`, `Carmen Cruickshank's Personal Meeting Room's transcript (1).txt`, 00:11:56–00:17:11. Mike asks whether the higher-priced band offer's advertising is worthwhile despite fewer conversions; at 00:13:51–00:14:39 he contrasts several DJ bookings with one band booking. Carmen had supplied figures; Whitney proposes reporting sales as well as calls. One $14,000 booking is reported. Planner-origin bookings have uncertain discovery sources.

**Editorial choice.** Foreground the owner's consequential question, not the definition of conversion value. Different-priced offers make a simple inquiry-count comparison inadequate. A wedding owner can recognize the decision without learning attribution terminology first. The specific two-offer situation supplies credibility; the broader question concerns judging business value.

**Why choose it.** It gives the conversation a commercial problem to resolve intellectually without claiming the account was proven profitable. Baseline Sol S2 already approaches this thought: this is partly selection and compression, not wholly new discovery. The adjacent LeadLock growth scene is already treated by approved Reel 6, while the attribution scene would add technical explanation and speculative journeys.

**Restraint / boundaries.** Leave out a reconstructed ROI calculation, algorithm details, all business-growth numbers and untracked-planner speculation. Booking value is not profit, collected revenue or verified incremental return. The proposed reporting change is not a delivered historical report. A legitimate alternative is the owner's need for a report that answers a business question; select it only if the same value argument is not duplicated elsewhere.

### 2. An ad does not need changing because the calendar did. — W3 priority

**Source.** `moment_baa14f0096a2495fb5aa0669`, same recording, 00:19:09–00:21:07. Marisa asks about refresh frequency. At 00:19:28 Carmen distinguishes new creative supply from changing working ads; at 00:19:49 she describes refreshing declining conversion creative. The discussion also reveals missed updates and a proposed recurring review.

**Editorial choice.** Make a supported professional position the central thought: activity is not automatically the right reason for a change. This gives a viewer something to consider rather than a lesson about refresh cadence. The concrete contrast is Carmen's choice between leaving working creative and changing declining creative, not an invented universal rule.

**Why choose it.** It demonstrates judgment that might otherwise be invisible to a client. A tutorial on creative fatigue requires more technical setup and offers less distinct personality. It adds an opinion to a slate otherwise dominated by explanation. An alternative on client review routines is weaker for a public Reel because it shifts attention to administration and an unresolved delivery concern.

**Restraint / boundaries.** Omit two-month recipes, algorithm guarantees and claims of perfect proactive communication. Credit Carmen/the team. Do not imply Whitney personally made the decision, or that proposed meetings were already established. The source contains declining ads too: the point cannot become 'never change creative.'

### 3. A quiet inbox can make you want to change everything. — W3 reserve

**Source.** `moment_a3deaf92e77cc94f7c6548e5`, `Carmen Cruickshank's Personal Meeting Room's transcript (3).txt`, 00:21:17–00:26:14. This is a team discussion of an owner's concern, not a direct recorded owner testimonial. At 00:22:29–00:22:45 Fallon recounts Jill saying inquiries slowed and asks whether organic inquiries also slowed. Other location, page and lead-system checks follow; the concern recurs after a temporary improvement.

**Editorial choice.** Begin with a recognizable possibility for an owner and use one diagnostic question to reveal restraint before changing everything. The opening is a reasonable creative interpretation, not evidence that Jill wanted to change every part of the campaign. Distinguish that imagined viewer situation from the case facts.

**Why reserve.** The diagnostic question offers a human entrance to technical work, but the source is internal and unresolved; a public treatment can readily become an account audit lesson or defensive agency story. The fact that the material can be reframed does not make it mandatory. A fuller diagnostic breakdown may serve another format better.

**Restraint / boundaries.** Keep the organic-versus-paid question and its significance; leave out the full troubleshooting sequence and unverified causes. No claim that the question solved the slowdown, that seasonality caused it, or that WIA restored performance. Review client/team handling before public reuse.

### 4. They had the ads running; they wanted to stop guessing. — W4 priority

**Source.** `moment_1c4dc73fb89e4a4e32377888`, `Whitney Hodges's Personal Meeting Room's transcript.txt`, 00:05:17–00:12:18. Victoria says they feel close and want business to become easier/calmer. They built a funnel, have Meta running, started Google, and want to understand it. Whitney asks where guidance is needed and explains an Accelerator option. At 00:12:18 Victoria describes having tried three approaches.

**Editorial choice.** Recognize competent owners seeking confidence and support. The commercially meaningful distinction is the kind of help they want, not a generic managed-versus-DIY service comparison. 'Stop guessing' condenses the exchange; it is proposed copy, not their verbatim wording.

**Why choose it.** Approved Reels 4 and 5 respect capable owners and the value of support. This scene can make an offer understandable through a person's situation without cataloguing modules or implying DIY incompetence. It supports a different reason for seeking WIA than being unable to run an ad. A narrower alternative on campaign objective confusion would turn the scene into an introductory platform lesson.

**Restraint / boundaries.** No sale, later transformation, increased confidence or improved results is established. Do not turn historical call descriptions into current program scope, price or universal suitability. An offer connection is earned here, but does not require a full product pitch.

### 5. Interest needs somewhere useful to go. — W4 priority

**Source.** `moment_729c08576259422181b39698`, `Workshop_ Building a Brand That Supports Premium Lead Generation's transcript.txt`, 01:06:42–01:18:35; Whitney's central response 01:17:51–01:18:29. An ice-sculpture provider describes weak Meta follow-through and wanting adjacent demand. Emily supplies SEO/adjacent-content ideas. Whitney distinguishes someone just discovering the service from someone ready for a detailed inquiry form. Related nurture discussion follows in `moment_331f75617d426e5c1df24f86`, 01:18:45–01:22:05.

**Editorial choice.** Enter through the prospective couple's experience: noticing something appealing is different from being ready to provide event details. That makes an otherwise technical funnel distinction intelligible. The unusual service helps visualize discovery, without restricting the whole thought to ice-sculpture vendors.

**Why choose it.** The thought offers an alternative to dismissing all quiet prospects as bad leads. It connects interest to a useful next interaction without needing an entire lead-nurture course. Do not split adjacent follow-up material into another Reel saying substantially the same thing.

**Restraint / boundaries.** Omit the SEO tutorial, platform comparison, legal speculation and exact sequence timing. Credit Emily for her recommendations. Do not claim a shorter form, email sequence or new campaign was implemented or increased bookings. 'Interest' alone is not proof a person is qualified or will buy. Another defensible framing is making follow-up useful to the couple, if the source scene and selected slate warrant it.

### 6. The owner knows things the ad account cannot tell us. — W4 reserve

**Source.** `moment_7bd068bbf7d499107487a129`, Whitney's meeting-room recording, 00:14:21–00:17:44. Blair wants better lead-source knowledge. Whitney initially asks about mixed paid/organic page use. At 00:15:49 Victoria clarifies the page is ads-only; at 00:17:04 she confirms a distinct form. Whitney then moves to which campaign/ad and proposes UTMs/hidden fields.

**Editorial choice.** Show collaboration through an actual correction that changes the next question. This is more concrete than saying 'we listen to clients,' and more human than a tracking tutorial. The owner's knowledge influences the diagnosis; expert status does not require pretending the initial assumption was correct.

**Why reserve.** It demonstrates partnership, but the tracking explanation can easily take over. The stronger guided-DIY idea already uses this call; scheduling both together may overuse the same scene and service theme. A detailed attribution treatment may be useful elsewhere without earning a Reel priority.

**Restraint / boundaries.** Leave UTM instructions and hidden-field setup out of the central perspective. Neither the owner's setup nor the proposed fix was independently verified. No complete attribution solution was delivered in the excerpt. Do not exaggerate the correction into a confrontation or generic owner-versus-expert conflict.

## D. Observed workflow differences

| Question | IDE review | Existing pilot | Evidence / implication |
|---|---|---|---|
| More source? | Selected context rereads; no independent full-transcript sweep | Complete weeks at extraction, selected contiguous intervals at generation | Do not attribute success to the IDE reading every raw transcript. Test discovery separately. |
| Better taste context? | Full six scripts and explicit copywriter task | Strategy/handbook-derived instructions, no full scripts, empty archive | A calibration intervention is justified to test; examples remain taste data, not current facts. |
| Valuable moments? | Reinterprets a preselected pool and existing candidates | Luna already selects public/process/internal possibilities | Extraction exists; omissions can matter, but many strong scenes survived. |
| Comparison? | Cross-model inventory, archive overlap, explicit omissions and small recommendation | Each model returns candidates and self-scores independently | Candidate development and final prioritization are not equivalent. Test selection without rewriting. |
| Framing? | Owner's situation, meaningful question or supported opinion leads | Frequently an operating rule leads; richer significance remains in rationale | Test whether instructions carry the meaningful thought into central fields. |
| Restraint? | Leaves incidental technical facts in support, excludes weak topics | More task-level candidates retained | Fewer is not inherently better; judge selected thought, not count. |
| Postprocessing? | Human-readable synthesis by this agent | Strict parsing, no pilot ranking/matching | No evidence that embeddings destroyed promising angles in this run. |
| Model advantage? | Serving configuration unavailable | Exact routes/settings recorded | Not a controlled model comparison; do not claim architecture/model superiority. |

## E. Reproducible editorial method

1. **Understand and bind source.** Existing extraction identifies speakers, situation, question/decision, contributions, response and uncertainty; binds literal evidence and enough contiguous context. Discovery interpretations remain provisional.
2. **Consider competing uses.** For each substantive scene, compare a literal lesson, an audience-facing situation or question, a supported opinion/process demonstration and internal-only use. These are thinking options, not output quotas. Reject rather than cosmetically rescue weak public topics.
3. **Formulate one worthwhile thought.** State what the owner would recognize or have reason to consider. Make that thought survive reading the title and core perspective alone. A rationale cannot compensate for a generic central claim.
4. **Use detail deliberately.** Keep the real choice or interaction that substantiates the thought. Leave ancillary setup steps in the source record. Never simplify by changing chronology, ownership, outcome status or claim basis.
5. **Calibrate and compare.** Use existing approved scripts for creative choices and overlap, never as a source of new facts. Compare candidate thoughts and scenes, not just titles or pillar labels. Prioritize distinct owner stakes within the actual planning range; preserve alternatives and exclusions for review.
6. **Validate and recommend.** Run existing structural/evidence checks; expose concise source-grounded reasons, missing facts and handling concerns. Self-scores are provisional. Human approval and source clearance remain separate.

These responsibilities need not become six paid calls. The experiments below determine which can stay inside the existing generation prompt and whether a separate stage adds sufficient value.

## F. Complete prompts and call contracts

The baseline snapshot retains all original templates. [The complete installed prompt appendix](2026-10-16-installed-editorial-prompts.md) reproduces the actual system/user templates for weekly extraction, default generation, SQL comparison and targeted refinement, including their dynamic-input boundaries, examples and full schema links. It explains each responsibility, input, output, consumer and failure boundary. It is generated from the installed builders, rather than an idealized replacement prompt. All sixteen exact request bodies, schemas and responses remain inspectable per experiment cell.

The two new trusted components are `backend/backend_pipeline/prompt_templates/reel_editorial.md` and `reel_calibration.md`. The complete literal six-script corpus is bundled as `reel_approved_examples.md`, byte-identical to the supplied corpus. Bundling keeps workers independent of this desktop's filesystem and fits the current Docker build's backend-only copy. The scripts remain user-message contextual data. They never replace current transcript evidence or enter system authority as instructions.

Initial generation retains `angles`, `internal_insights`, `processed_moment_ids`, `coverage_notes`. Targeted refinement still returns only `outcomes`, `processed_moment_ids`, `coverage_notes`; its internal-intelligence instruction remains conditional. No response schema or database schema was changed. Weekly extraction remains byte-for-byte unchanged. The installed default generation messages match tested arm E exactly before schema serialization; this is verified in a local test.

## G. Controlled comparison

The independent suite is `testing/.data/experiments/reel-editorial-forensics-20261016/`. The initial 14-dispatch bound was explicitly extended to **16** after B/E remained broad inventories, to test the missing comparison-plus-formulation step once per week. The amendment and its reason are saved. There were exactly sixteen dispatches, with no automatic retries. Original artifacts were never mutated, a started cell cannot dispatch twice, and no automatic quote repair, fallback, history matching or embeddings ran. All six reference directions were excluded from generation inputs. Approved existing scripts were allowed as taste/overlap context in the combined arm. No full prior analysis report was supplied as a hidden answer key.

| Arm | Controlled intervention | Important limit |
|---|---|---|
| A | Reconstruct all three returned W3 baselines; obtain missing W4 Sol baseline with exact saved body | Saved W3 calls are earlier samples; no fake missing Luna result. |
| B | Same Sol, same moments, schema and settings; add editorial instructions only | Any improvement is a single-sample prompt effect, not proof of reliability. |
| C | Same Luna extractor and raw weekly input, extra source-understanding instructions; then baseline Sol angle prompt on its new pool | Tests extraction treatment; pool content/count/IDs may change. Existing pipeline already had extraction. |
| D | Same A candidates and source; explicit Sol comparative selection, no rewriting or new calibration corpus | Can improve a slate, not repair the candidate's wording. Research recommendation up to two priorities and one reserve is not a production cap. |
| E | Combine supported instructions/calibration, with pool choice recorded | Additional context is a bundled intervention. Do not claim its individual contribution is isolated. |

### Editorial assessment rules

Factual eligibility is separate from creative value. Check source identity, speaker, chronology, attribution, case/result status, exact quote support, cost bases and scope. Hard factual failures cannot be offset by appealing language. Unknown handling blocks publication clearance, not necessarily a private angle proposal.

Then assess 0–5: **idea** (a worthwhile thought versus a topic), **owner recognition** (a credible business situation/stake), **framing** (clear specific perspective versus a neutral rule), **voice** (natural confident speech versus report language), **Reel focus** (one connected thought versus a course outline), **depth/specificity** (necessary scene versus incidental detail), **commercial meaning** (owner value/WIA relevance without forced promotion), and **slate contribution** (meaningful difference from the other ideas and known examples). 3 means useful but needing work; 4 strong; 5 exceptional, not a default. Record reasons and decisions, not a spurious approval probability.

Manual evaluation here is an informed editorial assessment by the same agent that authored the reference recommendations, not an independent client verdict or blinded human trial. Strong alternative directions are eligible; matching the reference titles is not the objective. Two already studied weeks are development cases; unseen material and Whitney's actual choices are required for generalization.

### Actual results

[Every returned direction, its central thought, selection reason, literal supporting source anchors and limitations](2026-10-16-editorial-experiment-outputs.md) is preserved in the output appendix. [The machine-readable results and cost receipts](2026-10-16-editorial-experiment-results.json) distinguish completed and failed cells. Counts are diagnostics, not editorial scores.

| Arm | Week 3 | Week 4 | Editorial finding |
|---|---|---|---|
| A | Saved Luna 9 / Sol 10 / Sonnet 9 | New exact-body Sol baseline: 11 | All three W3 models and W4 Sol could identify meaningful process material; candidate generation was not a final slate. W4 Luna/Sonnet baseline output remains unavailable, not invented. |
| B | Sol 10 candidates | Sol 9 candidates | Clearer wording in places, but operational rules and adjacent educational treatments remain. Prompt instructions alone did not establish a strong selection effect. |
| C discovery | Luna 17 moments, all five meetings acknowledged | Luna 15 moments, all six meetings acknowledged | Both passed literal/schema validation. W3 recovered the local YouTube question; W4 omitted a dedicated moment for the capable owners seeking guidance. Coverage acknowledgment is not recall. |
| C generation | Sol 9 candidates | Sol 10 candidates | Generally the same instructional tendency. Added material did not consistently improve the slate; original pools retained for E. |
| D selection only | Received 2 priorities + 1 reserve, failed validation | Valid 2 priorities + 1 reserve | W3 selected automation and buyer research without archive awareness. W4 chose conversion meaning and useful follow-up, with guided support as reserve. Selection can reduce a list, but does not itself repair framing. |
| E instructions + examples | Sol 8; independent Luna 7; Sonnet 9 | Sol 9; exact repeat 10 | Known DJ-case reuse was excluded. Commercial framing improved selectively; too many rule-like directions remain. No universal model winner. |
| E final comparative formulation | Received 2 priorities + 1 reserve, failed boundary-retention check | Same | Did not reliably prefer the stronger professional opinion, guided-owner story or inquiry-readiness thought. Not installed. |

The three failed cells were not reclassified as successful because their text could be read. D/W3 used non-null `source_issue` for correctly retained qualifications, violating its selection rule. D/W4 clarified that field's semantics before dispatch; its success is not a clean repetition of the identical D/W3 protocol. Both final-review outputs omitted or reworded some parent qualifier/risk strings, failing the experiment's exact retention check. That strict check is not proof every paraphrase was factually wrong, but it prevents claiming the requested retention contract passed. Raw responses and charges remain visible. There was no silent repair or extra retry.

### Observable quality anchors

| Dimension | Technically relevant but weak | Stronger observable standard |
|---|---|---|
| Underlying thought | Names a subject or distinguishes two tools | Makes a worthwhile observation, decision or supported position clear |
| Audience connection | Identifies 'wedding pros' | Gives an owner a recognizable situation or consequential question |
| Creative framing | Turns the task into a rule | Chooses a perspective that makes the scene worth discussing |
| Source grounding | Uses an existing ID | Preserves who contributed what, chronology, status and claim basis |
| Voice | Grammatically plain yet report-like | A person could naturally say the thought with a point of view |
| Reel suitability | Requires a glossary or several setup lessons | Has a natural entrance and one connected thought |
| Specificity / depth | Copies incidental detail or becomes generic | Uses the particular detail that substantiates the wider meaning |
| Commercial relevance | Appends a product or CTA | Makes an owner stake or WIA contribution intelligible without forced promotion |
| Novelty / variety | Changes title or pillar | Adds a materially different scene, consequence or perspective to actual known content |
| Clarity / restraint | The significance exists only in rationale | Title and core carry the worthwhile thought; support does not overwhelm it |

These anchors guide the manual comparisons below. No fabricated numeric average, predicted engagement score or client-approval percentage is reported. Models' own quality numbers are not an independent evaluation.

### Representative comparisons and decisions

**Commercial question, partial progress.** B/W3 says, “A higher-priced offer needs a sales-value view alongside lead volume.” E/Sol says, “A quieter inquiry stream needs sales context when booking values differ,” and explicitly recognizes that Mike already understands the offers. That is more respectful and owner-relevant. Yet the phrasing still foregrounds a reporting principle. The reference foregrounds the owner's question of whether advertising was worthwhile. Retain the source/idea; keep working on formulation. Luna/E omitted a separate offer-economics treatment, showing that shared examples and the same evidence do not ensure the same opportunity is selected.

**Creative judgment, still overexplained.** E/Sol retains “Fresh creative can be ready without replacing an ad that is still working,” but its core describes two management decisions and its rationale adds client review responsibilities. The supported professional position is present; the final review dismissed it as familiar and better suited to an FAQ. The reference makes the position the reason to hear the Reel. This is an editorial disagreement about what deserves a slot, not missing source, a failed embedding match or a wording-only problem. No current experiment resolves that taste judgment reliably.

**Quiet inbox, mixed framing.** B/W3 foregrounds checking paid/organic; E's core keeps a careful diagnostic principle. The final review selects it, but still titles it as a direction to widen an investigation. The reference enters through an owner's recognizable uncertainty and lets the diagnostic question demonstrate judgment. That entrance remains an interpretation, not evidence the source client wanted to change everything. Retain as a reserve or another format if the human entrance cannot be carried into the central thought.

**Guided owners, stronger candidate but weak final selection.** E/W4 states, “Wanting expert advertising help can be compatible with wanting to remain the person who understands and runs the campaigns.” This is closer to the reference's competent-owner story than the baseline's support-model rule. The exact repeat retains the same thought. However, the final review rejects it for similarity to approved Reel 5, even though the different scene and motivation may justify a new treatment. Mere topical overlap should not veto a distinct owner story. The relevant facts were already in the original pool; C discovery's omission would make this harder.

**Interest and readiness, not a missing how-to.** E/W4 produces a useful follow-up thought and a separate adjacent-demand treatment. The final review holds follow-up because cadence and stopping rules are unresolved. Those facts matter for a practical implementation guide, but the reference's thought about discovering a service versus being ready to inquire does not require them. This demonstrates the model's recurring tendency to judge an idea as if it must become a complete lesson. Do not install a critic merely because it produces detailed explanations.

**Collaboration, larger meaning still in rationale.** E/W4 explicitly notes the client's correction, but its central perspective remains about attribution questions. The reference makes the client's contribution the story and tracking the example. The final review sends it toward a longer tracking walkthrough. The source and rationale are adequate; the chosen foreground remains misaligned.

**A genuinely credible alternative.** W4's immediate correction from a 'booked tour' to a tour-page visit is a compact, owner-relevant measurement idea. It can support focused education without being automatically rejected as technical. Both selectors recognize it. It does not need to match a reference angle to be a reasonable reserve. Its central idea must preserve page visit versus booking, and must not become an accusation of dishonest reporting.

**Archive awareness improves, but its coverage remains limited.** All three E/W3 models omit a fresh treatment of the DJ automation-growth case already used in Reel 6. That is a concrete gain. They still return buyer-research treatments. The project also contains [the sent market-research email](../corpus/emails/2026-06-10-the-question-we-ask-every-new-client.md), which directly contrasts reviews with asking why couples booked. I verified its body and sent-date metadata. It was absent from the pilot and E's six-script calibration. This explains why the reviewers can call that idea relatively fresh against the supplied examples while missing a real archive overlap. It does not prove the email was imported into SQL; that database was unavailable. Six calibration examples are not a complete novelty archive. I did not silently add this newly checked email to the already tested production prompt or claim a complete-history check.

### What the experiments can and cannot establish

B is the cleanest instruction contrast: same Sol, original pool, schema, settings and downstream behavior. C changes the source-discovery treatment with the original Luna model and then the pool supplied to baseline Sol; it is not a Sol-only source-analysis ablation. D tests selection on existing candidates, with the protocol clarification disclosed. E adds calibration as a bundle, not an isolated test of every sentence or example. Its Week 3 three-model messages are identical; their outputs are isolated and do not influence one another. The Week 4 repeat uses the exact same request and still varies. Remote serving conditions, caching and model nondeterminism were not controlled.

The final two calls test a separate selection-and-formulation responsibility, but their failed contracts and unconvincing editorial choices give no basis to make it mandatory. Experiments remain development evidence from two known weeks, reviewed by an agent already familiar with the reference choices. No blinded human evaluation, Whitney approval, audience test, unseen-week generalization or paid latency benchmark is claimed. The missing original W4 Luna result and its unknown charge remain outside the reported new total.

## H. Implementation and verification

### Implemented, with a deliberately narrow scope

- `backend/backend_pipeline/prompts.py`: adds the two tested editorial components only to angle tasks; supplies the complete bundled approved scripts as distinct user/context data in default, SQL generation and SQL refinement builders. Source evidence, archive context and taste examples remain separate. Missing/empty examples fail before dispatch.
- `backend/backend_pipeline/prompt_templates/reel_editorial.md`, `reel_calibration.md`, `reel_approved_examples.md`: tested guidance and literal six-script snapshot. The latter equals the original corpus byte-for-byte and ships inside the existing backend package/container path.
- `backend/backend_pipeline/pipeline.py`: optional per-call prompt-version metadata; default generation records `2026-10-16.reel-editorial.v1` without changing the extraction profile or its request. Existing request-content hashes isolate cache identity. A test confirms changing only editorial calibration reuses moments and regenerates angles.
- `backend/backend_pipeline/sql_pipeline.py`: existing generation/refinement calls record that same angle-specific version. No new workflow stage, table or job type.
- `backend/backend_pipeline/model_experiment.py`: new prompt/example files are included in runtime sealing for future preparations. A historical seal should reject changed active code; the old suite was not resealed or weakened to accept it. Exact old requests and the baseline code snapshot remain available for reconstruction.
- New offline calibration/isolation tests and the isolated `scripts/editorial_forensics.py` research harness; `scripts/render_editorial_forensics.py` renders auditable outputs, prompts, costs and provenance. Two existing tests now parse the empty prior-signature field separately from the intentionally added example corpus.

The original system/user files, extraction instructions, schemas, provider model routing, `.env`, prices, scheduling and downstream quality/similarity thresholds were not changed by this implementation. The earlier unrelated working-tree edits were preserved. No GitHub push, new publication, destructive migration, automatic quote recovery or extra default model call was introduced.

### Verification

- **70 focused tests passed**: real prompt builders, exact test-to-installed messages, initial/refinement contracts, literal source/reference validation, complete example delivery, missing calibration, unchanged extraction files and stage-specific cache/version behavior.
- **104 additional checks passed, 22 skipped**: generation-only flow, replay/reuse/cost behavior, independent shared-evidence experiments, reviewed recovery, comparison/citation behavior and the research selector's invalid-ID/failure cases. Five calibration tests overlap the focused run. SQL integration cases require an isolated `atelier_test` database and were skipped; no live SQL success is claimed.
- Ruff passed for changed/new modules and tests. `sql_pipeline.py` was checked with its pre-existing broad-exception lint warning excluded; that unrelated handler was not refactored.
- All **30 baseline snapshot files** still match their preserved hashes; all **11 frozen transcript exports** match the original suite. The bundled approved scripts match their source bytes. [The provenance check](2026-10-16-editorial-provenance-check.json) records this; [the baseline-to-current diff](2026-10-16-editorial-implementation.diff) separates this work from earlier Git changes.
- Tests initially hit the sandbox's system temporary-directory restriction; rerunning under fresh workspace-local temporary directories resolved it. The example-placement assertions were updated after they exposed their previous end-of-message assumption. Final checks above passed after those corrections. Automated tests forbid outbound HTTP.

### Remaining limits

This release improves calibration and known-case exclusion. It does **not** turn every proposed angle into something Whitney is likely to approve, perform complete archive comparison, or automatically reproduce the six reference directions. The existing candidate output remains proposals for editorial review. A separate selector is specifically **not enabled**, because the experiments did not establish that it adds dependable judgment. Revised extraction remains experimental because its recall trade-offs were mixed. No production deployment or live SQL verification occurred.

The practical path supported here is to retain exact source discovery and independent candidates, add verified creative calibration, and measure the remaining selection/formulation gap against real human decisions and fuller eligible history. The evidence does not justify an expanding chain of mandatory paid critics or a claim that the quality problem is solved.

## I. Regression and quality validation

Keep a versioned corpus of source-grounded test scenes with original context, acceptable distinct interpretations, attribution/outcome boundaries and documented existing-content overlap. Do not require the six reference answers verbatim. Include weak-topic negatives, valuable internal-only intelligence, guest expertise, corrected expert assumptions, forecasts, unmatched spend periods, missing permissions and unresolved outcomes.

Use paired requests on identical frozen pools for future prompt comparisons. Repeat more than once, randomize labels for human review, record model/route/settings/time and assess with the same rubric. Include at least one unseen week before enabling broad rollout. Separate recall at moment discovery, factual precision, interesting-idea quality, slate redundancy, human strategic rewriting, latency and paid cost. A high JSON pass rate must not substitute for creative acceptance.

The decisive operational measure is Whitney's actual disposition: approve the idea, reframe, another format, research hold, internal only or skip, with the reason and extent of strategic rewriting. Track these without assuming every unpublished idea was rejected. Preserve previous versions and exact request hashes for rollback. Reassess calibration when the archive or strategy changes; do not keep a six-example taste inference frozen as universal brand law.
