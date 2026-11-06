# Week 3/4 model comparison — generation results

Run date: 15 October 2026. **Week 3 completed across all three angle models. Week 4 extraction failed exact-quote validation; its three angle calls have not run.** A two-quote recovery preview passes local validation but has not been admitted. Approval for that recovery is pending.

Five paid requests were dispatched, with four completed stages and one failed stage. Total provider-reported inference cost is **$1.081364205**. The failed extraction's cost is included. No requests were retried, and no model responses were used as inputs to another angle model.

## Generated Week 3 samples

All three models used the same frozen **18-moment** shortlist from one Luna Pro extraction of five supplied transcript exports / 1,837 turns. Each angle call used identical system and user messages, high reasoning, and empty historical signatures. The candidate counts below are the models' generation outputs, before any embeddings, matching, ranking, thresholds, refinement, or approval. They are not counts remaining after a similarity call.

| Angle model | Public candidates | Internal insights | Model-assigned purposes | Reported angle-call cost | Full output and source dialogue |
|---|---:|---:|---|---:|---|
| `openai/gpt-6-luna-pro` | 9 | 8 | 9 WARM | $0.08213607 | [Luna Pro review](week3-week4-comparison-2026-10-15/week3-luna-pro.md) |
| `openai/gpt-6.1-sol` | 10 | 8 | 7 WARM, 1 ATTRACT, 2 CONVERT | $0.40345850 | [Sol review](week3-week4-comparison-2026-10-15/week3-sol.md) |
| `anthropic/claude-sonnet-5.5` | 9 | 8 | 9 WARM | $0.45327600 | [Sonnet review](week3-week4-comparison-2026-10-15/week3-sonnet.md) |

The shared Week 3 extraction cost **$0.051530965**, counted once rather than once per angle model. Week 3's four-call total was **$0.990401535**. The [shared shortlist review](week3-week4-comparison-2026-10-15/week3-shared-moments.md) preserves the extraction's interpretations, qualifications, coverage notes and original surrounding turns.

Every completed model has a separate original response, validated artifacts, usage receipt, cost record and readable review. The reviews include timestamped original supporting dialogue for candidates and internal insights. The Luna review has a clearly marked independent review note about two source-reference errors; its generated text remains unchanged.

## What the Week 3 comparison shows

These are qualitative reviewer findings, separate from the models' own scores. There was one response per model and only one completed week, so this is not a stable model ranking or evidence of client acceptance.

**Sol shows the strongest strategic interpretation in this sample.** Its advantage is the substance of several treatments, rather than its larger count or more varied pillar labels. In the automation discussion, it connects the self-service inquiry journey to the owner's capacity to deliver events, while keeping the human sales call in the story. In the reporting discussion, it separates two substantive opportunities: understanding the economics of two differently priced offers, and understanding the limits of attribution. That is closer to the client's request to show how WIA thinks about the business behind the advertising.

Sol also connects the client's difficulty articulating one offer's value with the proposed research into why couples chose it. This gives buyer research a concrete positioning question to answer, rather than presenting another generic reminder to send surveys. Its process examples preserve client contributions, including proposed review meetings, client-supplied locations, existing welcome workflows, and appointment-quality corrections. Its internal records correctly distinguish course feedback from participant-progress operations, and identify a suspiciously transcribed vendor price as something to verify rather than silently correcting it.

Sol still has work to do. Several titles and central perspectives remain closer to internal principles than compelling brand directions. Phrases about information recipients, change boundaries and conversion definitions can remain academic even when their underlying reasoning is strong. The CONVERT and ATTRACT labels are provisional editorial choices, not proof that those treatments will achieve those purposes. The automation social-proof treatment depends on a client's report and needs its existing boundaries retained; the reported 90-event figure is a forecast, not a completed result.

**Sonnet is generally more direct, but stays heavily in familiar education.** It recognizes useful scenes around keeping buyer research separate from planning information, coordinating landing pages with a rebrand, creative refresh decisions and diagnosing a slowdown. It preserves the distinction between client input and practitioner work. However, all nine candidates are WARM, and the reviews-versus-research treatment returns to a theme already raised in the client's earlier repetition feedback. The separate planning-form treatment does add a different process decision, but this experiment does not exercise archive-based overlap assessment. Some confident wording needs scrutiny: “combining them weakens both” is stronger than the supplied exchange demonstrates, and an automation treatment's suggestion of producing callers ready to decide should stay tied to the participant report rather than become a general performance claim.

**Luna Pro finds useful process material at the lowest reported angle-call cost, but needs the most caution on this sample's reliability.** It identifies rebrand coordination, performance-dependent creative refreshes, cross-channel diagnosis and the role of client input. Its nine treatments are all WARM. Several central perspectives still emphasize technically careful lessons rather than the larger story of WIA's work. The important factual problem is that two internal insights have exchanged source references, despite passing the automated contract checks.

WARM-only output is not inherently a failure: neither the supplied evidence nor the prompts require a pillar quota. The substantive question is whether the selected treatment demonstrates a valuable perspective, process or service contribution. A different label alone does not make another angle distinct.

## Confirmed reliability findings

### Two Luna internal insights cite the wrong moments

The participant-progress / pipeline insight cites `moment_ab2b2ecd0400f6f72b564f98`, whose actual source is Jillian's course and troubleshooting feedback. The course-feedback insight cites `moment_2c5f077bd2fa4da6c1d7d62b`, whose actual source is Whitney and Gisselle's participant-progress discussion. The passages exist, but the attached references do not substantiate those two records.

This is a semantic binding failure, not a missing-ID or malformed-JSON problem. It demonstrates why automated validation is not factual approval. The original records have not been fixed or relabeled. Their review includes the finding and a link to the correct original passages.

### Extraction still shows an overly strict outcome requirement

Week 3's extraction coverage notes exclude the YouTube demand-generation exchange at `m4.t0185–m4.t0211` because it had not been tested and had no reported outcome. Reading that passage shows another possible reason to retain it: the client asks whether YouTube reaches local people, and Carmen explains the geographic targeting. The client then explains that she had assumed a broad audience would not help her business.

That is potentially a misconception or process scene without requiring a performance case study. The proposed channel and performance language still need careful boundaries. The finding is not that this must become a public angle; it is that lack of a result is too narrow a reason to dismiss it. This passage was not added to the frozen evidence or fed into any comparison call.

### Historical overlap was deliberately untested

Historical signatures were empty for every model. No embeddings, archive retrieval or similarity filtering ran. The familiar market-research theme is therefore a useful review concern, but none of these outputs establishes that its ideas are historically new. Broader strategic interpretation has improved; novelty, source entailment and final selection still require evaluation.

## Why Week 4 stopped

The Week 4 extraction used all six supplied exports / **1,803 turns** and returned **17 proposed moments**. It passed the strategic response contract and compact-reference resolution, but the normal parser rejected the whole response with:

> Moment quote must match an existing anchor span

Read-only diagnosis found two literal-quote failures. Fifteen proposals pass the normal parser individually. That is a diagnostic result only: **zero Week 4 moments were admitted, no partial pool was created, and none of the three Week 4 angle models was called.**

| Proposal | Cited source | Exact failure |
|---|---|---|
| `m4_google_conversion_correction` | `m4.t0256` | The model begins its quote “Um, or I guess…”; the actual turn contains “…Like, um, or I guess…”. The quoted substring is not literal. |
| `m6_adjacent_search_intent` | `m6.t0429` | The model begins “Um, so we wouldn't…”; the original says “Um, but, like, we wouldn't…”. Fillers and wording were changed. |

These are quote-reproduction errors. The evidence exists in the cited turns, but the original response still fails the exact rule and has not been accepted. Keeping that distinction matters when evaluating extraction reliability.

The failed call cost **$0.09096267**, retained in the total. Its original raw response, failed artifact, usage and source packet remain intact. The [rejected extraction review](week3-week4-comparison-2026-10-15/week4-rejected-extraction-review.md) includes all 17 proposed interpretations and their original context, clearly marked as rejected. A [diagnostic JSON](week3-week4-comparison-2026-10-15/week4-validation-diagnostic.json) records the individual checks. The [rejected model content](week3-week4-comparison-2026-10-15/week4-rejected-proposals.json) excludes private provider reasoning and is separate from accepted pipeline artifacts.

## Reviewed recovery proposal — not applied

A local preview replaces only the two quote values with shorter, verbatim excerpts already present in the same cited anchor turns. All other response fields remain identical. The normal whole-response reference resolver and parser then pass all **17 moments**. No canonical artifacts, failed receipts, prompts, runtime code, source files or dispatch markers were changed, and no new calls were made.

The exact edits and source revisions are in the [recovery proposal](week3-week4-comparison-2026-10-15/week4-quote-recovery-proposal.json); the [preview response](week3-week4-comparison-2026-10-15/week4-quote-recovery-preview.json) is explicitly unadmitted research material.

Continuing this way requires an explicitly approved recovery path because the sealed test prohibits automatic repairs. That path must preserve the failed provider response and the two-edit provenance, revalidate the complete derived response, identify it as reviewed evidence rather than unaltered model output, and freeze the same derived pool for all three remaining models. It must not overwrite the original failure or delete dispatch markers. The present harness has not been modified to admit this preview.

If approved, this could complete Week 4 without buying another extraction: the remaining three angle requests would bring the total to the original maximum of eight paid calls. Until then, there are no Week 4 angle samples to compare.

## Execution and isolation checks

- Final suite, runtime, schema and frozen-source integrity checks passed. The original transcript files still match their frozen hashes.
- Five started markers and five dispatch markers exist. Five raw responses are preserved. Four stages completed and one failed. The active-stage lock is absent; no model request remains running.
- All three Week 3 angle message arrays are identical, with explicit high reasoning and the same evidence-pool hash. No sibling results, scores, critiques or Week 3 outputs entered another generation request or the Week 4 extraction.
- No embedding, similarity, ranking, recency, refinement, SQL job, approval or publishing stage ran. No global configuration, editorial prompt or production implementation was changed during execution.
- No paid retries, partial acceptance, model substitutions, Git commits, GitHub pushes or deployment occurred. Research projections and offline diagnostic helpers were added locally.

The [machine-readable results](2026-10-15-week3-week4-model-comparison-results.json) contain exact stage costs, timings, returned model identities, usage and artifact locations. These are provider-reported inference costs; credit-purchase fees are excluded. The earlier setup tests remain the setup evidence; they were not rerun merely to generate these reports. Actual live response checks and local source diagnostics supply the evidence for this execution report.
