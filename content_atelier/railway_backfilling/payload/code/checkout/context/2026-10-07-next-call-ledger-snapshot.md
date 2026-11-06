# Content Atelier — next client call and meeting ledger

Created: 7 October 2026. Status: preparation and decision tracking; no client meeting is recorded as held.

## 1. Purpose and authority

This is the central ledger for questions requiring Whitney/WIA's response, preparation documents, and dated meeting records. It also separates internal product/engineering choices from client questions so a technical decision is not accidentally presented as client approval.

The current build scope ends at **weekly content-angle visibility**: transcript ingestion and processing, contextual key moments, grounded candidate generation, angle-memory comparison, recency-adjusted ranking, and a distinct visible set. Briefs, content packs, public publishing and scheduling are later stages.

The user's latest decisions are confirmed requirements. They are not evidence that Whitney has approved an operating schedule, source access, public reuse, scoring settings or later production quantities. The user has more clarifications before implementation; **coding is not started or authorised by this ledger**.

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
| C-04 | High; open — client response needed | Which transcript system, hosts/accounts and meeting series should we include? Which internal/client calls are useful, and which should be excluded? Who can grant the required access? | Transcripts only is settled; exact source coverage is not. Include useful WIA discussions based on purpose, not an automatic rule excluding every internal call. |
| C-05 | High; open — client response needed | May these transcripts be processed by the chosen AI services and stored for internal content development? What retention, deletion and restricted-client requirements apply? | Internal processing authority is required before live ingestion. Existing documents are not a blanket permission grant. Select provider/privacy routing internally once constraints are known. |
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
| I-03 | Open — internal decision | Start with authorised transcript exports/files or a live configured connector? What original historical-angle records are available for the initial import? | File-based fixtures can validate the pipeline without live account access. Live import depends on source authority and actual credentials. |
| I-04 | Proposed engineering contract | Call 1 and Call 2 are two logical stages; physical requests may be batched/retried to preserve full weekly coverage. No separate similarity LLM stage. | A hard requirement for exactly two physical provider requests would need measured input limits and overflow behaviour; it is not assumed here. |
| I-05 | Open — internal discussion | The user has additional clarifications before implementation. | Remain in documentation/reasoning mode until those are addressed and implementation is requested. |

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
| D-01 | [Transcript-to-content-angle specification][angle-spec] | Current implementation design through visible angle cards; incorporates U-01 to U-05 and tracks I-01 | Current design; not code |
| D-02 | [Vector database storage design][vector-spec] | Broader evidence/policy/memory storage; transcript-only and threshold-visibility amendments take precedence over earlier four-angle assumptions | Current storage reference; broader than first slice |
| D-03 | [Whitney taste and editorial review][taste-review] | Corpus-grounded editorial preferences, source authority and factual limits | Research/reference; validate current preferences with client |
| D-04 | [Architecture comparison and reconciled design][architecture-review] | Analysis of original proposal and editorial pipeline | Reference; newer decisions in D-01/this ledger override conflicting earlier defaults |
| D-05 | [Supplied solution architecture][supplied-architecture] | Client/project-supplied architecture proposal used for comparison | Unmodified background proposal; not the sole current requirements source |
| D-06 | [Next-call and meeting ledger][this-ledger] | Questions, authority/status, preparation-document index and dated meeting index | Current ledger |

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

**Ready for the remaining design discussion; not yet cleared to begin implementation.** The main pipeline and four newly resolved product choices are concrete. The user's additional clarifications and I-01 remain before finalising close-pair behaviour.

| Area | Current readiness | What remains |
|---|---|---|
| Overall pipeline / datastore | Defined | One PostgreSQL/pgvector store; typed evidence and angle memory; no new separate vector service |
| Source scope and visible count | User confirmed | Transcripts only; every qualified distinct angle above the adjusted threshold |
| Previous-run comparison | User confirmed | Previous completed generation run; current batches kept separate |
| Similarity execution | Defined numerical baseline | Exact cosine, compatible signature/profile, versioned thresholds; no additional LLM judge |
| Very-close pair selection | Not final | I-01 needs the user's precise intended behaviour |
| Weekly execution timing | Provisional | C-01–C-03; these can remain configurable for an offline fixture build but need agreement for a live weekly service |
| Live transcript ingestion | Not verified | Source coverage, access, AI processing authority and retention; C-04–C-06 |
| Ranking settings / empirical quality | Not calibrated | I-02 and representative labelled examples; do not claim validated production thresholds |
| Implementation start | On hold at user's request for further clarification | I-05; no backend, connector, migration or scheduler change is made |
| Briefs / packs | Deliberately outside this slice | C-10/C-11 later; do not block transcript-to-angle design on asset quantities |

Once the remaining internal clarifications are settled, an authorised file-based fixture implementation can exercise the contracts while client-facing live-operating questions are pending. A production weekly service should not claim complete coverage, confirmed freshness or authorised live processing until its actual inputs, permissions and calibration are verified.

## 10. Change history

- 7 October 2026: created this ledger; recorded U-01–U-06, provisional Saturday 04:00 Texas timing, client questions, internal questions, document index and future meeting-record workflow. No client response or held meeting is invented.
- 7 October 2026: revised the transcript-to-angle design and amended the storage reference to remove the old four-angle display assumption and optional additional LLM similarity judge. Very-close pair behaviour remains explicitly unresolved.

[angle-spec]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/transcript_to_content-angle.md>
[vector-spec]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/content_atelier_vectordb.md>
[taste-review]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/research/whitney-taste-and-editorial-pipeline.md>
[architecture-review]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/research/architecture-comparison-and-reconciled-design.md>
[supplied-architecture]: <C:/Users/Jainil Trivedi/Downloads/Content-Atelier-Solution-Architecture.md>
[this-ledger]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/to_be_asked_in_next_call.md>
