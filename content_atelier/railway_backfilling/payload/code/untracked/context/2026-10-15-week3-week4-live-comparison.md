# Week 3/4 live comparison state — 15 October 2026

The user approved the prepared eight-call shared-extraction comparison, then explicitly approved sending all 11 Week 3/4 transcripts and derived evidence to OpenRouter. Calls now made: five. Four stages completed; Week 4 extraction failed. No request remains running and no retries occurred.

Active suite: `testing/.data/experiments/week3-week4-shared-luna-angle-quality-20261015/`.

- Week 3 extraction: `openai/gpt-6-luna-pro`, high reasoning, 18 validated moments from five exports / 1,837 turns.
- Week 3 Luna angle generation: 9 candidates, 8 internal insights, all WARM.
- Week 3 Sol angle generation: 10 candidates, 8 internal insights, 7 WARM / 1 ATTRACT / 2 CONVERT.
- Week 3 Sonnet angle generation: 9 candidates, 8 internal insights, all WARM.
- All Week 3 angle requests have identical messages and the same pool hash. No history, embeddings, similarity, ranking, refinement, approvals or SQL jobs ran.
- Week 4 extraction: Luna Pro high, six exports / 1,803 turns, returned 17 proposals but failed whole-response exact-quote validation. No accepted pool and no Week 4 angle calls.
- Five requests and five raw receipts. Reported total cost USD **1.081364205**, including the failed extraction. Source and runtime seals still verify; original transcripts unchanged.

## Readable results

Main report: `research/2026-10-15-week3-week4-model-comparison-results.md`.
Machine-readable results: same basename `.json`.
Reviews and diagnostics: `research/week3-week4-comparison-2026-10-15/`.

Reviews preserve original timestamped context. Sol offers the strongest strategic interpretation in this single completed week, a provisional reviewer opinion rather than a stable model ranking. Luna's two internal insights swap course-feedback and participant-progress source IDs; those records remain unchanged and flagged. Week 3 extraction also excludes a local YouTube misconception/process scene for lack of an outcome, suggesting continued over-caution.

## Week 4 exact failures and pending approval

Local diagnosis uses the normal parser on validation copies only. Fifteen proposals pass individually, two fail. The original batch remains rejected with zero admitted moments.

1. `m4_google_conversion_correction`, anchor `m4.t0256`: model quote begins `Um, or I guess`; source contains `Like, um, or I guess`.
2. `m6_adjacent_search_intent`, anchor `m6.t0429`: model quote begins `Um, so we wouldn't`; source contains `Um, but, like, we wouldn't`.

A concrete local recovery preview changes only these two `quote` values to shorter literal excerpts from the same anchor turns. The complete derived response then passes the normal reference resolver and parser for all 17 moments. This preview has NOT been admitted, cached, frozen as a pool or used for inference. Original provider receipts and failed status are unchanged.

Proposal and exact source revisions: `research/week3-week4-comparison-2026-10-15/week4-quote-recovery-proposal.json`.
Preview response: `.../week4-quote-recovery-preview.json`.
Rejected source review: `.../week4-rejected-extraction-review.md`.

An asynchronous user question is pending: approve reviewed quote recovery preserving the failure and an edit log, revalidate all 17, then run the remaining three independent Week 4 angle calls without another extraction; or keep the failed run unchanged. **No approval to repair has yet been received.** The existing experiment expressly forbids automatic repair; do not promote the preview or delete started/dispatch markers on elapsed time alone.

If the user approves recovery, the harness needs an explicit reviewed-derived-evidence path and provenance. Its current `verify_pool` expects the accepted original extraction artifact and its exact output. Do not overwrite or relabel the failed provider artifact to satisfy that check. Preserve the original failure in the experiment's quality findings. Freeze the same reviewed pool for all three Week 4 models, with no sibling or Week 3 outputs, and send each remaining angle request at most once. That would total eight paid requests, retaining one paid extraction per week.

Offline report helpers added under `backend/.storage-artifacts/verification/week3-week4-models-20261015/`: `collect_live_results.py` and `diagnose_week4.py`. They generate research projections only, have no network calls, and do not change active pipeline artifacts. No production code, prompts, schemas, global configuration, Git commits or pushes changed during this execution.
