# Content brief implementation status

<!-- governing-plan-note -->
> **Historical (marked 18 October 2026, plan item S.B9).** This document is kept for traceability. The one governing plan is [the implementation plan](backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md) (revision 6.1 or later); where they differ, the plan wins. Do not plan from this document.

12 October 2026. Implemented through Gate 2 and verified offline. No OpenRouter or external embedding requests were made during this implementation. Real Week 1/Week 2 content, approvals, vectors and execution records were unchanged at the close of implementation verification. Subsequent authorized pilot preparation is recorded below.

The workflow is **hash-bound approved angle → original grounding → hybrid research → frozen dossier and prior coverage → structured brief → validation/one repair → human Gate 2**. Production, packs and publication are separate later stages.

Current local model selection: **`openai/gpt-6.1-sol` for brief writing and its repair pass**. Research planning, evidence grading and support/differentiation review continue to inherit **`openai/gpt-6-luna`**. Angle generation and the embedding model are unchanged. This configuration change made no model calls and leaves all execution switches disabled.

## W1-3 live pilot

The human selected **Give distinct wedding markets distinct landing-page context** and supplied the exact CTA **“Match the landing page per venue for a better client experience.”** Week 1 was reassessed using its existing vectors, and that individual legacy-baseline angle was approved through Gate 1. No other angle was approved. The reviewed guide hierarchy is Founder Voice Guide primary, Knowledge Base supporting, and Savannah strategy; prepared exemplars remain drafts rather than publication history.

Run `brief_run_76d191ebe580663186c56ca8` has completed local preparation: twelve inherited passages, twenty permitted sources, 329 compatible chunks and eleven other admitted arguments. Brief prior coverage uses the frozen run clock, including already-generated Week 2 arguments when briefing a Week 1 angle. Original week ownership and angle-generation novelty policy are unchanged. Two compatibility regressions were added; the focused brief/provider suite passed **43 tests** with its outbound guard active.

The first research dispatch was rejected by automatic approval review pending explicit authorization of the source-data transfer. The human then explicitly approved the bounded OpenRouter brief pipeline. All five stages completed and saved **`brief_f4778b6818b357fde23bb1b4`**, pending Gate 2. Twelve queries used two embedding batches; eight chat calls included one Sol writing call, one Sol repair, and Luna planning/grading/review. Provider-reported cost was **USD 0.32749242**, excluding credit-purchase fees. The PostgreSQL container was restarted after a local service interruption; the original writing result had committed and required no repeated dispatch.

The final dossier retained the twelve inherited passages and eleven prior arguments; no supplemental passages were retained after grading. Candidate/grading budget omissions remain explicit in the research audit/gaps. The repaired brief preserves the approved direction and the venue-level application as untested. Both semantic-review flags passed, with warning findings. Exact source bindings and unrelated source/vector/moment/angle/downstream records passed before/after checks.

Gate 2 is still blocked. Two reported-claim statuses are prose instead of the exact source token, and the prior-difference map includes two exemplar keys outside the historical-angle namespace. The numerical checker also falsely identifies digits in valid claim labels `[C3]`/`[C4]` as quantities; this is a validator defect, not an invented numerical result. Source-use/identity questions, acceptance of the venue-level caveat, and legacy-history review remain unresolved. The single repair was used; no further automatic loop or human approval was performed.

Private generated Markdown/JSON and run-review notes are under `backend/.storage-artifacts/brief-runs/brief_run_76d191ebe580663186c56ca8/exports/`. Full audit, costs, authorization and invariant evidence are in `backend/.storage-artifacts/verification/brief-w1-3-pilot-result.json`.

Persistent external-call switches remain false. The bounded pilot uses process-local capabilities, a 300,000-character request preflight to preserve the complete approved guide bundle, and a longer transport timeout. External web research and Gate 2 approval remain outside this run.

## Buying-research live pilot — 13 October 2026

The human selected **Reviews and buying research answer different questions**, provided the exact ADS CTA, approved its bounded OpenRouter transfers, and chose **0.90 for this pilot only**. The selected candidate is `angle_1d20dd133d5492c950608290`, from today's source-valid five-moment partial diagnostic. Its four saved candidates and five valid moments were revalidated against the admitted Week 2 sources; only this angle and its supporting moment were admitted. The original failed extraction and both rejected quotations remain unchanged. Original IDs, generation time, strategic fields and null reader decision were preserved.

The initial legacy two-call assessment was the wrong path for this same-source rerun and remains in the audit. The implemented comparison reassessment `run_7ed5d1af794f4637b1ce2d9357920414` correctly excluded earlier results over the same eleven Week 2 source revisions from historical novelty. Against the six Week 1 arguments, baseline quality was 80 and maximum cosine was 0.6053777975760815; all three experimental scenarios qualified. The human-selected 0.90 was recorded in the actual Gate 1 approval policy, without changing the permanent/global cutoff. Brief context separately retained the earlier Week 2 arguments and actual brief-use state.

Brief run `brief_run_c9d93e21502a743f2ac7912b` completed all five stages and saved **`brief_2ff7b35b7ad9cc0e3493bc82`**, pending Gate 2. The dossier retained 61 original passages and twelve prior angles; twelve research queries used two batches. No supplemental evidence was retained, and grading-budget omissions remain explicit. Eight chat calls included Sol writing/one repair and Luna planning/grading/two reviews. Reported brief-run cost was **USD 0.412373935**; the one angle-signature embedding cost **USD 0.0000038**, giving **USD 0.412377735** combined, excluding credit-purchase fees.

An operational review-reference bug was fixed narrowly: a review finding may cite a prior-angle ID actually supplied in the dossier. Unknown references still fail, and those prior arguments cannot ground factual claims. All **22 brief regression tests passed**, including both invariants, with outbound requests blocked; twelve initial compatibility tests also passed. Explicit retry reused the unchanged cached first review, preserving its substantive overlap/permission findings and avoiding another charged first-review call. Requests, model responses and schemas were not rewritten.

The repaired brief preserves the exact CTA and describes surveys/shared spreadsheets as proposed rather than implemented or currently offered, with no adoption or marketing results. It explicitly acknowledges that its argument is not substantively different from the earlier pending Week 2 buying-research angle. Consolidation/refresh, source-use clearance and CTA scope/DM-destination verification remain human review work. Exact qualifier/status-token requirements and extra exemplar keys still fail the strict contract; citation-label digits also trigger the known numerical-check false positive. Gate 2 remains blocked; no second repair, approval, packs or publication were performed.

Private Markdown/JSON and review notes are under `backend/.storage-artifacts/brief-runs/brief_run_c9d93e21502a743f2ac7912b/exports/`; the full run/cost/authorization/invariant record is `backend/.storage-artifacts/verification/buying-research-brief-result.json`. Existing unrelated source/chunk/angle/brief/downstream rows passed before/after checks. Permanent execution switches remain false.

## What is ready

| Component | Result and reason |
|---|---|
| Approval handoff | Gate 1 approval and the initial brief intent commit together when briefing is enabled. Idempotency binds the approved angle/hash and workflow. A missing reviewed brand bundle rolls the transaction back instead of leaving an unexplained approval. |
| Comparison authority | A configured authoritative cutoff is required to approve comparison candidates; it remains unset. Approval follows the recorded family scenario and revalidates its frozen vectors, quality and grounding. An original fallback remains approvable even when it has an automatic refinement child. Prior CTA approvals cannot invalidate unrelated selected families. |
| Original evidence | Exact moment links resolve preserved transcript passages, ranges, qualifiers, claim status and source-use/attribution metadata. Search ranking cannot remove inherited grounding. |
| Supplemental research | Six to ten initial queries; up to twelve distinct queries across three rounds. Query vectors resolve in one batch per round and remain transient/cache artifacts. Exact cosine and English full-text search use the same permitted chunk IDs, with RRF rank constant 60 and up to fifty results per branch. The first five fused chunks per query are expanded for inspection. |
| Evidence selection | About forty graded passage items is a soft inspection budget. Complete linked moment/qualification groups may exceed it. Required context is preserved, and oversized requests fail preflight. Grades cover every delivered evidence ID exactly once. Original evidence and the related qualification passages remain retained. Audit artifacts keep rankings, grading decisions and budget omissions. |
| Prior coverage | Eligible argument families are searched independently of passage discovery. Actual passage overlap links back through moments and angles. Exact original angles with recorded briefs are included even when the family's representative uses different evidence. Actual brief and calendar records distinguish generated, approved and published use; no publication is inferred. |
| Frozen inputs | The preparation stage pins original evidence, permitted source/chunk/moment hashes, argument/use records and the execution contract. Retries recover these inputs and reject changed dependencies. Writer/reviewer packets omit the bulky retrieval audit while preserving its hash. |
| Writing and validation | Strict production contract: reader promise, core insight, message spine, narrative, claims, differentiation, voice, CTA, email, eight-slide carousel, three distinct reels, creative/accessibility/distribution/evaluation directions, questions and sources. Deterministic source/range/quote/status/number checks supplement a scoped support/differentiation review. At most one automatic repair. |
| Gate 2 | Protected list/detail, versions, edits, answers, permission references, scoped human review, approval/rejection, refinement and JSON/Markdown exports. Edits create superseding rows and invalidate semantic review. Required answers and incomplete-history acknowledgement block approval. Human answers are context, never source proof. |
| Operational recovery | Existing SQL leases, heartbeats, explicit retries and job/event progress are retained. Received requests/raw responses are preserved before validation/SQL writes. Compatible replay never dispatches a provider. Usage/billing artifacts distinguish new dispatches, cache reuse, fixture execution and unknown costs. |
| UI | A separate **Content Brief Review** uses real SQL APIs, shows source passages and previous-use context, versions, questions, approvals and refinement controls. Approved angle cards show research progress. Other prepared studio views remain the existing mock library. |
| Optional web research | A bounded `WebResearchProvider` interface is built and tested with fixtures. It uses an explicitly reviewed public topic/question packet, checks source URL/domain/recency rules and records receipts. No production web adapter is configured; unavailable framing is labelled. It cannot prove an internal result. |

## Storage

The schema still has **13 tables, 30 foreign keys, 18 checks and two `vector(1536)` columns**. Migration `002_brief_retrieval_index.sql` adds only a GIN expression index for transcript full-text search. It was tested for exact catalogue agreement/idempotency and applied to the local real database. Workers execute no automatic DDL.

Generated drafts use existing `content_briefs` columns: the structured document/review/provenance envelope in `content_body`, exact `angle_input_hash`, `selected_evidence`, `prior_content_context`, `research_gaps`, supersession and hash-bound approval. Dossiers, provider receipts, query vectors and cost projections are private artifact files referenced by jobs. No empty placeholder briefs or new configuration/scoring/version tables were introduced.

## Verification evidence

- **190 full-backend tests passed, followed by 41 passing final focused checks** (including replay-only web, invalid external recency and incomplete-response recovery cases). **19 affected UI/auth/proxy tests passed**. TypeScript and production build passed. Full backend acceptance and final focused JUnit files: `backend/.storage-artifacts/verification/brief-backend-final.xml` and `brief-focused-final.xml`.
- Real SQL retrieval smoke: twenty sources, 329 compatible chunks, original-reference checks passed using an existing stored vector, with no query encoding or content writes. Evidence: `brief-real-retrieval-smoke.json`. This is a mechanics check, not relevance calibration.
- A complete synthetic researched/approved brief and its lineage: `backend/.storage-artifacts/verification/brief-synthetic-report.json`.
- Real before/after row/catalog fingerprints: `brief-implementation-real-before.json` and `brief-implementation-real-after.json` in the same verification folder.
- The affected SQL UI and all auth/proxy tests pass. TypeScript and the production frontend build pass.
- The broader frontend suite still has its existing `ScheduledContent.test.tsx` mismatch: ten scheduling controls versus two expected. That component and test were not changed. One existing private-fixture test is skipped.

The fixtures exercise cross-week retrieval, bounded gap rounds, one repair, invalid/missing evidence, exact quotations and qualifications, numerical prose, permission/actor restrictions, edited/locked versions, stale dependencies, raw-response and SQL-write recovery, family fallbacks, closed comparison approval, exports and cache-only inspection. These verify mechanics and invariants; they do not establish real retrieval relevance, semantic entailment or founder voice quality.

Implementation verification confirmed all thirteen tables' row hashes/counts matched the pre-implementation snapshot: **20 transcripts, 329 embedded chunks, 13 moments, 12 embedded pending angles, zero briefs/packs/assets/calendar records**. No real approval or run was created during that verification. The only catalogue difference was the approved full-text index. The later W1-3 approval/preparation above is a separately authorized change.

## Before a real pilot

For comparison-workflow candidates, select the authoritative angle cutoff explicitly. Legacy Week 1 baseline candidates use their completed existing selection contract. Configure trusted approver/editor actor IDs and review the active founder brand bundle. Select/pin writer/reviewer settings if overrides are needed. Persistent generation, encoding, refinement, briefing and web switches remain false. Setting a switch does not convert a replay run into live execution.

Real approval queues cache-only briefing by default. A later explicitly authorized pilot can select live mode through the CLI, using the exact run-input hash and configured capabilities, then retry the paused stage/start its worker. `activate-brief` performs no inference itself. No production/pack job follows Gate 2 approval.

The first live pilot is complete through generation and validation, with the contract/validator issues above and human Gate 2 review still outstanding. Further relevance/support/voice evaluation, optional external-provider configuration and content-pack implementation remain separate work. Implementation increments 1–5 are complete; the real pilot has now produced a reviewable SQL draft, not approval-ready acceptance.

References: [approved implementation plan](implementation-plan-content-briefs.md), [storage runbook](backend/STORAGE.md), [pipeline/data-store map](data-storage-schema.md), [data flow](data-flow.html).
