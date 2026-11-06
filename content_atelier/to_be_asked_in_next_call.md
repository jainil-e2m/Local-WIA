# Content Atelier — next client call and meeting ledger

<!-- governing-plan-note -->
> **Historical (marked 18 October 2026, plan item S.B9).** This document is kept for traceability. The one governing plan is [the implementation plan](backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md) (revision 6.1 or later); where they differ, the plan wins. Do not plan from this document.

Created: 7 October 2026. Status: preparation and decision tracking; no client meeting is recorded as held.

## 1. Purpose and authority

This is the central ledger for questions requiring Whitney/WIA's response, preparation documents, and dated meeting records. It also separates internal product/engineering choices from client questions so a technical decision is not accidentally presented as client approval.

The eventual slice ends at **weekly content-angle visibility**. The current authorised test stops earlier at **unembedded angle candidates** while prompts are refined: ingestion, contextual key moments and candidate generation only. Angle-memory comparison, recency-adjusted ranking and visibility remain disconnected until explicit user approval. Briefs, content packs, public publishing and scheduling are later stages.

The user's latest decisions are confirmed requirements. They are not evidence that Whitney has approved an operating schedule, source access, public reuse, scoring settings or later production quantities. The user subsequently authorised the local transcript-to-angle implementation and the corpus-grounded prompt review. That slice and its offline tests are present; live inference, provider/source authority and production readiness remain separate gates. Earlier design-only statements are historical, not the current implementation status.

Use stable question IDs. Preserve earlier answers and their authority when a decision changes; mark them superseded instead of erasing them.

## 2. Confirmed user decisions

| ID | Requirement | Authority / date | Effect on the design |
|---|---|---|---|
| U-01 | Show every distinct angle above the adjusted-score threshold | User, 7 October 2026 | No four-angle display cap; no padding weak weeks. Pagination does not cap eligibility. |
| U-02 | “Last turn” means the previous completed generation run | User, 7 October 2026 | Previous-run angles are included once within eligible history; earlier physical batches in the current run remain current candidates. |
| U-03 | No additional LLM similarity-comparison stage | User, 7 October 2026 | Use compatible embeddings, exact cosine comparison, versioned numerical rules and inspectable match records. No hidden third LLM judge. |
| U-04 | First implementation processes transcripts only | User, 7 October 2026 | Slack stays in the wider storage design but is not ingested or processed in this first slice. |
| U-05 | Saturday morning, 4:00 a.m. Texas time, for now | User, 7 October 2026; provisional for client confirmation | Document as a proposed weekly execution time, not a confirmed timezone/window/cutoff or an installed automation. |
| U-06 | Keep all valid generated angles in separate logical angle memory within the same PostgreSQL/pgvector database | Earlier user decision | Persist candidates before filtering; historical evidence and generated-angle memory have different retrieval/authority roles. |
| U-07 | Run pgvector locally for current testing | User, 7 October 2026 | Rebuildable projection code/local-service definition present; no running database or live integration verification yet |
| U-08 | One embedding vector per content angle | User, 7 October 2026 | One canonical active representation; not hook/topic/quote/format vectors |
| U-09 | Test one week of backfilled Zoom meeting transcripts, then advance/backfill week by week | User, 7 October 2026 | Exact first dates/export coverage remain to choose; history must be scoped chronologically |
| U-10 | Use JSON/Markdown ledgers/datastore records before final production PostgreSQL schema | User, 7 October 2026 | JSON authoritative for initial experiments; Markdown reviews; pgvector rebuildable projection |
| U-11 | Save full paid-service inputs, returned outputs and intermediates for reuse wherever compatible | User, 7 October 2026 | Dedicated paid-call artifacts/cost/reuse ledger; no secrets or invalid/incompatible silent replay |
| U-12 | User will supply roughly three months of meetings in numbered week1, week2, etc. folders, starting in June 2026 | User, 7 October 2026 | Process chronologically one week at a time; exact first/last intervals and actual window count are not inferred from folder labels |
| U-13 | Representation-only compaction preserves every utterance and the full speaker name on each turn | User, 8 October 2026 clarification | No speaker aliases, editorial pruning, preparatory summary, greeting/ending removal or silent truncation |
| U-14 | Call 1 is one physical extraction request containing the complete week | User, 8 October 2026 clarification | Supersedes earlier automatic batching proposals for extraction; measure actual token capacity and fail transparently if it does not fit |
| U-15 | Backfill uses Zoom transcripts/metadata; production will use Fathom transcripts/metadata | User, 8 October 2026 clarification | Shared evidence contract with separate adapters; do not use Fathom summaries as transcripts or infer absent Zoom dates from filenames |
| U-16 | Use `apodex/apodex-1.1-mini:free` for both LLM stages and prepare local environment configuration | User, 8 October 2026 model-configuration request | Supersedes GPT-OSS as the active default; blank shared free-account key and separate paid embedding key. Configuration does not establish private-source processing permission or whole-week live readiness |
| U-17 | Generate no embeddings until the user approves; preserve/disconnect the vector leg, test Week 1 with supplied keys, and review the real flow/angle quality | User, 8 October 2026 live-test request | `CONTENT_ATELIER_EMBEDDINGS_ENABLED=false`; stop after candidates. Specific Week 1 Apodex inference authorised, not publication, Slack, database projection or automatic later-week runs. Five diagnostic angles generated, full extraction still failed; D-15 records outcomes |
| U-18 | Test the same Week 1 pipeline with exact `openai/gpt-6-luna`, a funded OpenRouter key, saved output and costs for both LLM stages | User, 8 October 2026 paid-model comparison request | Supersedes Apodex as current configured model, not the source/prompt contract. Embeddings stay disconnected. Both stages cost-instrumented; actual extraction failed before Call 2. D-16 preserves paid usage, rejection and next decisions |
| U-19 | Retry Luna using the locally updated working key with no application input/output token limit | User, 8 October 2026 uncapped-retry request | Blank completion setting omits output-cap fields; explicit input flag disables local size rejection for both stages, not source/schema checks. A3 returned nine proposals, seven individually valid, full extraction failed two quote checks; Call 2 not attempted. D-17 records result/cost |
| U-20 | Explain the blocked angle step and execute it either in a new run or using this run's saved moments | User, 8 October 2026 continuation request | Chosen option: reuse seven individually valid A3 moments and original context in existing explicit partial diagnostic. Six Luna angle candidates generated, two rejected records preserved; no new extraction, embeddings or automatic future fail-fast-policy change. D-18 records result/cost/replay |

Model status: exact Luna for both stages. U-19 authorises uncapped requests; U-20 authorises saved-moment continuation. A3 Call 1 remains failed with nine proposals/seven individually valid and $0.016626175 historical cost. A4 Call 2 successfully generated six candidates from that seven-record pool, new cost $0.009089175; continuation status partial, actual cache-only replay $0. D-18 records the latest result; D-17/D-16 preserve earlier extraction/rejection accounting. Small/1,536 remains dormant. D-09/D-14 remain historical GPT-OSS research and D-15 preserves Apodex history. This is not complete weekly extraction, founder approval, general production-processing authority or permission to publish.

“Above” is documented as a strict comparison: `adjusted_score > visible_threshold`, using the stored unrounded score. A score equal to the threshold does not pass. Numerical threshold values remain uncalibrated.

The user also said: **“incase its a very close similarity then only include both relevant ones.”** The no-extra-LLM decision is clear; the intended meaning of “include both” is not yet clear enough to implement. Track that separately as I-01.

## 3. Status vocabulary

| Status | Meaning |
|---|---|
| User confirmed | The project owner has answered; not necessarily a client response. |
| Provisional — client confirmation needed | A working assumption exists; Whitney/WIA has not confirmed it. |
| Open — client response needed | No client answer is recorded. |
| Open — internal decision | Product/engineering clarification for the user, not automatically a client agenda item. |
| Engineering calibration | Evaluate settings against authorised examples; do not ask the client to invent cosine values. |
| Client answered | Record the actual answer, speaker, meeting/source reference and date before using this status. |
| Superseded / deferred | Preserve prior history and name its replacement or later stage. |

A completed preparation document does not close a question. Silence, a model suggestion, and a supplied proposal are not client approval.

## 4. Questions for the next client call

### 4.1 Current transcript-to-angle slice

All entries below remain unanswered by the client as of this document's creation. Priority reflects the current slice, not a scheduled meeting.

| ID | Priority / status | Ask Whitney/WIA | Why it matters / provisional position |
|---|---|---|---|
| C-01 | High; provisional — client confirmation needed | Should the weekly run begin Saturday at 4:00 a.m. in your local Texas timezone? Which city/timezone should govern it, and should it follow daylight saving time? | User's provisional timing is recorded. Assume `America/Chicago` only for discussion until confirmed; do not use a fixed UTC offset. |
| C-02 | High; open — client response needed | What exact period should each weekly batch cover? Is Saturday 4:00 a.m. the processing start, transcript availability cutoff, or both? | Proposed window: previous Saturday 4:00 a.m. inclusive to current Saturday 4:00 a.m. exclusive, in the confirmed business timezone, based on meeting occurrence. This is a proposal, not a decision. |
| C-03 | High; open — client response needed | What should happen when a meeting occurred in that week but its transcript arrives late, is corrected, or is missing at cutoff? | Decide grace period, partial-week visibility and deliberate rerun/backfill policy. Never silently rewrite an already reviewed result. |
| C-04 | High; open — client response needed | For the initial Zoom backfill, which accounts/hosts and meeting series should we include, and what exports/access cover the chosen week? Which internal/client calls are useful or excluded, and who authorises access? | User selected backfilled Zoom transcripts; exact coverage/adapter and client authority remain open. Include useful WIA discussions by purpose, not a blanket exclusion of all internal calls. |
| C-05 | High; open — client response needed | May these transcripts and derived moment/angle packets be processed by the chosen AI services and stored for internal content development? What retention, deletion and restricted-client requirements apply? | Internal processing authority is required before real-source inference. D-09 identifies NVIDIA free endpoints that prohibit confidential/personal data; raw client meetings must not be sent there by default. Check every actual provider route; free pricing is not privacy permission. |
| C-06 | High; open — client response needed | Which names, quotations, client stories and performance figures can appear in internal angle cards, and what needs approval or anonymisation before public use? | Separate internal discovery from publication permission. Material confidentiality blocks processing/disclosure as applicable; later public clearance is not inferred from angle visibility. |
| C-07 | Medium; open — client response needed | Which past angles or published messages should count as prior coverage, and where is the reliable archive? Can we review examples of “too repetitive” versus “same topic, useful new contribution”? | Seed history honestly and calibrate repetition against editorial labels. Available corpus coverage is incomplete; an empty match list does not prove an argument was never used. |
| C-08 | Medium; open — client response needed | Can you identify a small set of angles you would accept, reject as vague, or reject as unsupported, with the source passages and short reasons? Are the documented voice/audience preferences still current? | Calibrate source grounding, relevance, usefulness and distinctness. Translate these examples into engineering thresholds; do not treat unreviewed ChatGPT drafts as approved taste. |
| C-09 | Medium; open — client response needed | If a week has no qualified angles or incomplete source coverage, should we show an empty/incomplete result or wait for missing transcripts? Who is responsible for resolving it? | User has already rejected quota filling by choosing threshold-based visibility. Confirm the client's operating/review preference for empty or incomplete weeks. |

### 4.2 Later-stage questions — tracked, not prerequisites for this slice

| ID | Status / stage | Question | Boundary |
|---|---|---|---|
| C-10 | Deferred — briefs/packs | What are the current offers, approved factual claims and CTA destinations? How should a CTA be chosen for a direction? | Historical promotional copy cannot supply current promises. No CTA or asset is chosen automatically in this slice. |
| C-11 | Deferred — pack allocation | How should approved angles map to weekly emails, reels, carousels and other assets? Which quantities and approval roles apply? | “All qualifying angles visible” does not mean “a complete pack for every angle.” Later production capacity/selection remains separate. |
| C-12 | Deferred — Slack rollout | Which Slack channels/threads, access rules, reply/backfill policies and retention settings should be included when Slack is added? | Do not enable Slack in the transcript-only implementation. |

## 5. Internal clarifications and calibration — not automatically client questions

| ID | Status | Decision / question | Readiness effect |
|---|---|---|---|
| I-01 | Open — internal decision | For a very-close match, does “include both relevant ones” mean show the new/historical pair side by side for comparison, keep both as weekly selectable angles, or a different rule? Should the same rule apply to two newly generated candidates? | Resolve before final automatic close-pair selection. Do not silently suppress one, admit both, or resurrect an old suggestion as new weekly evidence. |
| I-02 | Engineering calibration | Choose and version historical match threshold, current-pair close threshold, adjusted-score threshold, recency half-life, maximum penalty fraction and admission floors. | Existing numerical examples are illustrative. This needs labelled fixtures and measured behaviour, not a new LLM judge or guessed client approval. |
| I-03 | Partially resolved — internal details open | User will supply roughly three months in numbered weekly folders starting June 2026. What are week1's exact start/end dates, the actual final date, export coverage and initial angle-history seed? | Week 1's nine exports/3,238 cues were prepared locally on 8 October; missing Zoom metadata prevents date validation. Protect this untracked input root. Do not assume June 1, a particular Saturday, exactly twelve weeks or a June–August span. |
| I-04 | Earlier batching proposal superseded for Call 1 by U-14 | Two logical LLM stages remain; Call 1 must be one physical extraction request containing the full week. No separate similarity LLM stage. | Local token preparation now exists. If a real budget fails, stop and report it; do not silently split/summarize/truncate. Retry and Call 2 physical-request policy still need deliberate treatment. |
| I-05 | Staged clarifications continue; local build authorized | The user requested and authorized the backend/testing implementation and current Week 1 local preparation. | Do not treat the earlier documentation-only pause as active; do not infer permission to change later-stage contracts or perform unrequested inference. |
| I-06 | Model comparison selected; extraction and semantic calibration open | Luna selected under U-18; Apodex history preserved; Small/1,536 dormant. | D-16: actual native input 116,370 tokens and 14 proposals, but schema/source errors stop Call 2. Eleven individually valid records are offline diagnostics, not accepted whole-week output. |
| I-07 | Open — internal clarification asked asynchronously | Does “final content angles generation” mean the final deterministic selected set, or an additional LLM refinement pass? | Preserve two logical LLM stages until answered; no additional similarity judge |
| I-08 | Open — test timeline/branch decision | Confirm named historical-simulation versus actual-operation clock and isolated A/B history branches. | Prevent backfill execution timestamps or unrelated trial variants from distorting recency |
| I-09 | Specific paid Week 1 comparison authorised; broader operating policy open | Set per-stage/week/experiment cost ceilings, quota/retry policy and production provider/privacy routes. | U-18 authorises Luna, not purchases or an unlimited retry loop. A1 HTTP 402 led to one announced 16,384-reserve retry; A2 Call 1 cost $0.017861675, Call 2 not sent. Stage/run accounting is implemented, missing billing stays unknown; enforced budgets and future automatic runs remain unconfirmed. |
| I-10 | Actual compatibility tested; whole-week acceptance open | Novita rejects advertised json_schema; explicitly use supported json_object plus trusted full schema and strict local validation. | Requests authenticated and fit, but source binding/semantic errors remain. No silent schema weakening, random free router or paid fallback. |
| I-11 | Explicit live test refinement implemented | Replace thousands of echoed turn IDs with exact per-meeting first/last/count acknowledgements and retain granular quote/context checks. | Full 3,238-turn input preserved; review separates delivery count from acknowledgement. Neither proves comprehension; D-13/D-15 document the live-only contract. |
| I-12 | Engineering prompt calibration — next iteration | Keep factual uncertainty in the proposition/mechanism, require summaries' quantities inside selected context, and prevent unsupported outcomes being copied into angles. | D-15 records five real candidate reviews. Partial pool is diagnostic only; no embedding approval, founder label or extra LLM judge is inferred. |
| I-13 | Luna extraction findings — next deliberate refinement, not yet implemented | Exact enum compliance, quote-to-anchor copying, single-cue quotations and validation of source IDs inside free-text coverage notes. | D-16: two quote-binding failures and one enum failure; m6 coverage note invents two IDs despite correct meeting acknowledgement. Strict schema may address enums, not semantic/source accuracy. Choose a full extraction rerun versus explicitly partial Call 2; no further paid request made automatically. |
| I-14 | Uncapped test completed; source-copy/binding remains open | Application caps removed under U-19; no additional reserve reduction or schema repair authorised. | D-17: normal stop, nine proposals, seven individually valid, two exact quote defects. Provider capacity/credit limits still apply. Refinement or a partial-pool angle diagnostic needs a separate decision; no embeddings approval inferred. |
| I-15 | Explicit partial-pool angle continuation executed; future acceptance policy open | U-20 authorises this reuse diagnostic, not blanket acceptance of invalid extraction or an automatic fallback. | D-18: seven valid records produced six candidates, original failures preserved and no new extraction. Decide separately whether future normal runs should continue from a nonempty valid subset while remaining visibly partial, or retain whole-response fail-fast; semantic/review/privacy gates remain. |

Recommended discussion starting point for I-01, **not an accepted rule**: show both matched records in a comparison panel, keep historical records labelled as history, and choose weekly suggestions only from candidates grounded in the current week's admitted evidence. If the intent is to retain both in the weekly selectable set, define which close pairs qualify and how that relates to the distinctness requirement.

Exact cosine comparison is concrete and reproducible given the vectors. It does not prove that two arguments are semantically identical. The baseline uses transparent numerical overlap/recency penalties; it must not invent a semantic-relation label or a zero-penalty exemption requiring an unapproved third LLM. Unresolved close cases remain inspectable.

## 6. Provisional weekly timing contract

| Field | Current record | Authority |
|---|---|---|
| Proposed execution day/time | Saturday, 04:00 local Texas time | User-provisional |
| Proposed timezone identifier | `America/Chicago`, conditional on WIA confirming Central Time | Engineering assumption; C-01 open |
| Daylight-saving behaviour | Keep 04:00 local wall-clock time across seasonal changes | Recommendation to confirm; not fixed CST year-round |
| Proposed source window | Previous Saturday 04:00 inclusive → current Saturday 04:00 exclusive | Engineering proposal; C-02 open |
| Window's inclusion clock | Meeting occurrence time, not export/download time | Design recommendation |
| Availability cutoff / grace | Not decided | C-02/C-03 open |
| Late/corrected transcript handling | Explicit later run or deliberately reopened source snapshot; policy not final | C-03 open |
| Scheduler configured | No | Documentation only |

Central Time has different standard/daylight UTC offsets; a fixed UTC−6 would shift the intended local execution time during daylight time. [NIST local time guidance](https://www.nist.gov/pml/time-and-frequency-division/local-time-faqs). Texas is not a sufficiently precise timezone label: the National Park Service documents Mountain Time in El Paso and the Central/Mountain boundary in western Texas. [NPS timezone explanation](https://www.nps.gov/gumo/learn/management/superintendents_compendium.htm).

Compute adjacent weekly boundaries in the confirmed timezone before storing UTC instants. A local seven-day window spanning a daylight-saving change need not contain exactly 168 elapsed hours. Preserve the timezone, local boundaries, resolved UTC boundaries and schedule-policy version with each editorial cycle. This records an implementation contract; it does not install a recurring task.

## 7. Preparation-document ledger

These files already exist or are created by this documentation update. “Current” means current within its stated scope; it does not imply implemented functionality.

| ID | Document | Role / scope | Status |
|---|---|---|---|
| D-01 | [Transcript-to-content-angle specification][angle-spec] | Current implementation design through visible angle cards; latest file-backed test amendment links D-07 | Current design; not code |
| D-02 | [Vector database storage design][vector-spec] | Broader evidence/policy/memory storage; transcript-only and threshold-visibility amendments take precedence over earlier four-angle assumptions | Current storage reference; broader than first slice |
| D-03 | [Whitney taste and editorial review][taste-review] | Corpus-grounded editorial preferences, source authority and factual limits | Research/reference; validate current preferences with client |
| D-04 | [Architecture comparison and reconciled design][architecture-review] | Analysis of original proposal and editorial pipeline | Reference; newer decisions in D-01/this ledger override conflicting earlier defaults |
| D-05 | [Supplied solution architecture][supplied-architecture] | Client/project-supplied architecture proposal used for comparison | Unmodified background proposal; not the sole current requirements source |
| D-06 | [Next-call and meeting ledger][this-ledger] | Questions, authority/status, preparation-document index and dated meeting index | Current ledger |
| D-07 | [Local week-by-week testing and paid-output reuse design][testing-design] | JSON-ledger/local-pgvector roles, one-vector contract, chronological/A-B history, clocks, paid artifact reuse/costs, embedding and OpenRouter shortlist | Design reference; initial harness/reuse implemented in D-10, not every proposed feature; no paid calls |
| D-08 | [Dedicated testing datastore README][testing-readme] | Runtime area/record responsibilities and preservation/recovery checklist | Real Week 1 requests/responses/failures and partial candidates now preserved privately; no embeddings |
| D-09 | [Small embeddings and free-model comparison][model-comparison] | Sizes/prices/efficiency, exact free endpoint shortlist, confidentiality limits, June week-folder manifests and controlled stage evaluations | Researched recommendations; no inference or input import |
| D-10 | [Backend pipeline implementation README][pipeline-readme] | Generation-only boundary, lossless compact live runner, token preflight, strict validation, explicit partial diagnostic/replay | 89 offline tests pass; actual inference tested with remaining failures; database not started |
| D-11 | [.env.example][env-example] | Configurable stage models/keys, dormant paid embedding profile, compact/token/response settings | Actual keys supplied locally, not documented; embeddings false and default live false |
| D-12 | [Corpus-grounded prompt robustness review][prompt-review] | Evidence-to-policy mapping, revised two-stage prompts/contracts, 14 diagnostic cases, scoring/signature reasoning and historical flat-packet size limitation | Prompt v2 offline-tested; actual GPT-OSS output quality untested. U-14 supersedes batching proposals; D-14 supplies actual compact token measurements |
| D-13 | [Stage prompts and timestamp ledger][prompt-ledger] | Complete prompts/policy and dated extraction refinements through live v3 | Actual v1/v2/v3 extraction supplements preserved; Call 2 v2 unchanged in a5. No automatic learning |
| D-14 | [Week 1 payload and token-readiness review][week1-readiness] | Actual complete weekly preparation, fidelity, local token counts, response-budget scenarios, free-route status, missing Zoom metadata and live integration gates | Local artifacts saved; 62 offline tests pass; narrow conditional context fit; no live LLM/embedding requests |
| D-15 | [Week 1 generation-only execution and editorial review][week1-live-review] | Actual requests/usage, extraction failures/refinements, all five diagnostic angles, Whitney fit, evidence limits, zero embeddings and replay | Five partial candidates, not complete weekly success; 89 offline tests, original-byte verification, no-new-request replay |
| D-16 | [Week 1 GPT-6 Luna execution, cost and evidence review][week1-luna-review] | Exact-model compatibility, native usage and both-stage accounting; HTTP 402, bounded retry, all 14 proposals, source/semantic limits and stored output | Call 1 billed $0.017861675 but full extraction failed; 11 individually valid in offline audit, no Luna angles/embeddings; 107 offline tests |
| D-17 | [Week 1 uncapped Luna retry review][week1-luna-uncapped-review] | User-requested cap removal, new-key retry, omitted output fields, full-input integrity, all nine proposals, two precise quotation defects and costs | Call 1 $0.016626175; seven individually valid but full response rejected, Call 2 not attempted; no embeddings, 112 offline tests |
| D-18 | [Week 1 Luna saved-moment content-angle review][week1-luna-angle-review] | Explanation of fail-fast gate, authorised seven-record continuation, all six angles/source reviews, separate original/new costs and actual replay | Six validated unembedded candidates, partial status; one new Call 2 $0.009089175, no new extraction, pair total $0.02571535; replay zero new requests/cost |

Meeting files are indexed below when created. Context checkpoints/snapshots in `context/` preserve continuity and earlier document versions; they are not substitute client meeting evidence.

## 8. Dated meeting ledger

Naming convention: `meeting_YYYY-MM-DD.md`, using the **actual intended/held meeting date**, in the Content Atelier directory. If two separate meetings occur on one date, use a descriptive suffix and record it here. Do not create a fictional meeting record simply to populate this table.

No dated meeting file has been created and no client meeting date has been provided as part of this request.

| Meeting date | File | Lifecycle | Question IDs / preparation documents | Outcome |
|---|---|---|---|---|
| — | None yet | Not scheduled/recorded | Initial agenda candidates: C-01–C-09; references D-01–D-04 | No client answers recorded |

Lifecycle: `planned` → `held — notes pending` → `recorded`; or `cancelled/rescheduled`. “Recorded” means notes/outcomes are captured, not that an audio recording exists or was authorised.

### 8.1 Template for a future meeting file

Copy this structure into the actual dated file when preparing a meeting. Placeholders are not answers.

```markdown
# Content Atelier — meeting YYYY-MM-DD

Status: planned
Scheduled date/time/timezone: [actual details, or not yet confirmed]
Actual meeting date/time: [fill only after meeting]
Participants: [planned; distinguish actual attendees afterwards]
Source of outcomes: [notes / authorised transcript locator / other verified record]
Linked ledger question IDs: [C-xx / relevant I-xx]
Preparation documents and versions: [D-xx, filenames and revision dates]

## Before the meeting
### Objective and agenda
- [Topic, question ID, expected decision, priority]
### Evidence/examples to discuss
- [Document section or authorised example]
### Proposed options and open assumptions
- [Clearly mark proposals as unconfirmed]

## After the meeting
### Questions and actual responses
| ID | Question | Response | Speaker / evidence locator | Answer date | Status |
|---|---|---|---|---|---|
| [ID] | [Question] | [Actual answer or unanswered] | [Reference] | [Date] | [Status] |

### Decisions and boundaries
- [Confirmed decision, authority, affected scope; distinguish our interpretation]
### Remaining questions / disagreements
- [ID, missing detail, owner, next action]
### Follow-up actions
| Action | Owner | Due date if agreed | Status |
|---|---|---|---|

## Documentation reconciliation
| Document | Section/change | Decision ID | Updated / pending |
|---|---|---|---|

## Revision history
- [Date: preparation / post-meeting notes / clarification; author and source]
```

### 8.2 Before and after each meeting

1. Before: create the actual dated file, add it to §8, link the specific questions and supporting documents, and distinguish proposals from confirmed facts.
2. After: fill actual attendance, responses, source locators, unresolved questions and agreed actions. Do not infer an answer from a topic merely being discussed.
3. Update this ledger's status and answer provenance; link the meeting record and affected design sections.
4. Reconcile D-01/D-02 when decisions change. Append a change entry and preserve superseded answers. No automatic implementation follows from taking meeting notes.
5. Keep private quotes/transcripts access-controlled; never invent a recording link or treat internal notes as permission for public reuse.

## 9. Readiness through the content-angle stage

**Ready for controlled generation-only prompt calibration, not complete weekly acceptance, production or embeddings.** A3 full extraction still fails two quote checks, but U-20 authorised use of its seven individually valid saved records. Call 2 now executed and produced six Luna candidates; D-18 records the partial diagnostic, all six source reviews, $0.009089175 new cost and actual zero-request replay. Original A3 $0.016626175 is not rebilled. All nine exports/3,238 turns remain preserved; 112 offline tests are verified. D-17/D-16 preserve earlier extraction/accounting and D-15 preserves Apodex history. Missing Zoom metadata, complete semantic coverage, production permissions, calibrated scoring, future partial-acceptance/spending policy and close-pair behavior remain open. Local token caps stay removed for this test, but source/schema checks and finite external provider/account constraints remain. No candidate is founder-approved or final similarity-ranked visible content.

| Area | Current readiness | What remains |
|---|---|---|
| Overall pipeline / datastore | Defined; testing mode user confirmed | Initial JSON datastore/Markdown ledgers plus local pgvector projection; full typed production schema later, no new separate vector service |
| Source scope and visible count | User confirmed | Transcripts only; every qualified distinct angle above the adjusted threshold |
| Previous-run comparison | User confirmed | Previous completed generation run; current batches kept separate |
| Similarity execution | Defined numerical baseline | Exact cosine, compatible signature/profile, versioned thresholds; no additional LLM judge |
| Very-close pair selection | Not final | I-01 needs the user's precise intended behaviour |
| Weekly execution timing | Provisional | C-01–C-03; these can remain configurable for an offline fixture build but need agreement for a live weekly service |
| Live transcript ingestion | Not verified | Source coverage, access, AI processing authority and retention; C-04–C-06 |
| Ranking settings / empirical quality | Not calibrated | I-02 and representative labelled examples; do not claim validated production thresholds |
| One-vector / week-by-week test contract | User confirmed; harness proposed | U-07–U-12; June start/numbered folders now known, exact intervals, profile/models, clocks/branches and cost/quota/privacy settings still need decisions |
| Final-generation interpretation | Not final | I-07: final selected set versus additional paid refinement pass |
| Implementation start | Generation-only pipeline and both-stage cost tracking implemented; specific Luna Week 1 test executed | Full extraction still fails; next paid retry/partial diagnostic needs direction. No embeddings until approval, no PostgreSQL projection or production connectors; no briefs/packs |
| Briefs / packs | Deliberately outside this slice | C-10/C-11 later; do not block transcript-to-angle design on asset quantities |

Once the remaining internal clarifications are settled, an authorised file-based fixture implementation can exercise the contracts while client-facing live-operating questions are pending. A production weekly service should not claim complete coverage, confirmed freshness or authorised live processing until its actual inputs, permissions and calibration are verified.

## 10. Change history

- 8 October 2026, saved-moment continuation update: U-20/D-18/I-15. Explained that Call 2 was never rejected; whole-response extraction validation stopped it. Existing explicit diagnostic reused seven valid A3 records plus original surrounding dialogue, preserving two failures; no application/prompt/source edit. One new Luna angle call generated six validated candidates, reported $0.009089175; parent extraction not repeated, embeddings/ranking off. Actual R1 replay identical IDs/times and zero requests/cost. Future automatic partial-pool policy not silently implemented; no founder/public approval inferred.
- 8 October 2026, uncapped retry update: recorded U-19/D-17/I-14. User-supplied keys preserved; both stages remain exact Luna. Blank output reserve omits caps; explicit false input-limit setting bypasses local compact/legacy size rejection with diagnostics only. Full source/prompts and strict quote/context/schema checks unchanged. A3 returned nine proposals, seven individually valid, but failed two quote checks; Call 1 $0.016626175, Call 2 not attempted, zero embeddings. 112 offline tests, Ruff/format/compilation/whitespace checks pass. No automatic repair, further retry, purchase, meeting or founder approval inferred.
- 8 October 2026, Luna comparison update: recorded U-18, D-16 and I-13. Both defaults/actual/template models now exact Luna, keys preserved. Added Luna-only compatible body assembly, public-route-cache/conservative local preflight and paid/unknown/replay-zero stage/run JSON/Markdown accounting. Saved initial HTTP 402 and one announced 16,384-reserve retry: 14 proposed moments, 11 individually valid offline, full extraction failed and Call 2 not attempted. Actual extraction cost $0.017861675, no Luna angles/embeddings/database calls. All prompt-template text remains unchanged; 107 offline tests, lint/changed-file formatting/compilation pass. No client answer, meeting or further paid fallback is invented.
- 8 October 2026, live-test update: recorded U-17 and D-15, disconnected embeddings by default and preserved their code. Connected lossless whole-week live ingestion and pinned local Apodex token preflight. Archived one format rejection, three extraction responses with strict failures, five partial-pool Call 2 candidates and a zero-new-call replay. All reported successful-response inference costs zero; no embedding/database/publishing calls. Extraction v1/v2/v3 refinements are timestamped, Call 2 baseline unchanged, all five candidates manually source-reviewed, 89 offline tests pass. No client answer or held meeting is invented.

- 7 October 2026: created this ledger; recorded U-01–U-06, provisional Saturday 04:00 Texas timing, client questions, internal questions, document index and future meeting-record workflow. No client response or held meeting is invented.
- 7 October 2026: revised the transcript-to-angle design and amended the storage reference to remove the old four-angle display assumption and optional additional LLM similarity judge. Very-close pair behaviour remains explicitly unresolved.
- 7 October 2026: recorded local pgvector, one-vector, first-week Zoom backfill, JSON/Markdown persistence and full paid-output reuse requirements (U-07–U-11). Added D-07/D-08 and I-06–I-09. Model selections, final-refinement meaning and timeline recommendations remain unconfirmed; no paid calls or database changes.
- 7 October 2026: recorded the user's roughly three-month, numbered-week meeting supply beginning June 2026 (U-12), Small preference and request for free model options. Added D-09; changed the proposed first profile to Small/1,536 and GPT-OSS 120B free for both stages. Expanded preservation to free requests under the proposed service_calls area; flagged NVIDIA free endpoint confidentiality restrictions. Exact week1 dates, privacy authority and final choices remain open. No source import, inference, installation or implementation.
- 7 October 2026: user approved GPT-OSS 120B Free and requested implementation through angle generation. Added the fresh `backend_pipeline/` slice using the agreed Python/FastAPI/Pydantic/RQ-compatible stack, JSON authority, versioned prompts, explicit live mode, deterministic ranking and minimal pgvector projection. Week1 was tested offline against discovered source files; no external call or database service was run. Existing deleted backend files and frontend changes were preserved.
- 7 October 2026: added separate `.env` configuration for moment extraction, angle generation and embedding credentials/models/base URLs. Embeddings may use an OpenRouter-paid key by setting `EMBEDDING_BASE_URL` to OpenRouter; direct OpenAI remains supported. Live startup now validates required credentials. Offline tests and lint pass; no secrets were added.
- 7 October 2026: audited and corrected compatible local reuse of raw responses, moments, angles and embeddings, with replay-only mode and preserved original generation lineage. The reuse suite passed 19 offline tests; no live inference or database integration test occurred.
- 7 October 2026: added D-12 and released corpus-grounded v2 prompts, curated editorial policy, complete nested response contracts, exact source-context handoff, coverage/source checks and code-generated signatures. Added 14 synthetic evaluation diagnostics, not model-evaluated results. Measured Week 1 at nine exports/3,238 spans and 870,794 rendered input characters; added a conservative uncached-live size preflight. Bounded weekly batching and real output calibration remain necessary. No client approval or private-source inference was invented.
- 8 October 2026: user requested backend-local organisation. Moved the package, prompts, tests, dependency/configuration template and local Compose definition into `backend/`; retained transcripts at `backend/zoom_backfill_meetings/` and datastore at `testing/.data/`. Added process → backend `.env` → legacy project `.env` precedence and path tests without reading/moving real credentials. Verified 43 offline tests, Ruff lint/format checks, compilation and CLI help. Current prompt/restructure context and original v1 prompt texts are preserved under `context/`. No deployment, live provider call or database service was started.
- 8 October 2026: recorded U-13–U-15, superseding automatic Call 1 batching and speaker-alias proposals. Built a local-only complete Week 1 preparation command, raw-byte archives, source maps, compact prompt supplement and D-14 token/route review. All nine exports/3,238 cues are included; 62 offline tests and changed-module Ruff checks pass. Prepared request remains unsent; paid services, real `.env`, PostgreSQL and the legacy live runner were not invoked. Added I-10/I-11 without treating engineering decisions as client questions or answers.
- 8 October 2026: recorded U-16 and switched both active LLM defaults/template values to Apodex 1.1 Mini Free. Created Git-ignored `backend/.env` with blank shared free-account and separate paid embedding credentials; no existing .env files/secrets were overwritten. Added six isolated configuration tests; 68 offline tests, lint, changed-file formatting and compilation pass. Shared key never supplies embeddings; explicit stage overrides remain supported. Prompts, historical GPT-OSS artifacts, source fixtures and the live guard remain unchanged. Documented that compact-week runner integration and Apodex-specific token preflight are still required; no model request, embedding call, database startup or private-source upload occurred.

[angle-spec]: <transcript_to_content-angle.md>
[vector-spec]: <content_atelier_vectordb.md>
[taste-review]: <research/whitney-taste-and-editorial-pipeline.md>
[architecture-review]: <research/architecture-comparison-and-reconciled-design.md>
[supplied-architecture]: <Content-Atelier-Solution-Architecture.md (outside the repository)>
[this-ledger]: <to_be_asked_in_next_call.md>
[testing-design]: <content_atelier_week_by_week_testing.md>
[testing-readme]: <testing/README.md>
[model-comparison]: <content_atelier_embedding_and_free_model_comparison.md>
[pipeline-readme]: <backend/README.md>
[prompt-review]: <research/transcript-angle-prompt-robustness-review.md>
[prompt-ledger]: <backend/prompts.md>
[env-example]: <backend/.env.example>
[week1-readiness]: <research/week1-payload-token-readiness.md>
[week1-live-review]: <research/week1-generation-only-test-review.md>
[week1-luna-review]: <research/week1-gpt6-luna-test-review.md>
[week1-luna-uncapped-review]: <research/week1-gpt6-luna-uncapped-retry-review.md>
[week1-luna-angle-review]: <research/week1-gpt6-luna-content-angle-review.md>
