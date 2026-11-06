# Content Atelier documentation versus implementation review

Reviewed on 12 October 2026 against documentation commit `e3ab4cdbc9488469caa3397bdc147099a93aab53`, the current working tree, the sibling Command Center implementation in `../frontend`, and the local real database using a read-only transaction.

Code evidence paths in this report are relative to the Content Atelier repository root; `../frontend` identifies the sibling Command Center checkout. Links in the added-file table are relative to this document.

**Subsequent workspace progress:** The initial observations below preceded the real Week 2 run and transcript-chunk encoding. The follow-up at the end of this report records the newer state; use that section for current angle/chunk counts and execution status.

**Verdict:** The additions are useful requirements, architecture and planning material. They do not describe a completed implementation. The major upstream and brief-generation gaps are real. Several current-state statements describe the 10 October snapshot and are now stale; the revised execution plan also overrides parts of the architecture and roadmap. Treating every added file as the current specification would produce conflicting instructions.

Existing source files and the seven added documents were not edited during this review. This file records the review separately. No external model or embedding request was made.

## What the commit added

`git show --stat HEAD` confirms seven new files and 5,465 inserted lines, with no application code changed in that commit.

| Added file | Lines | Purpose and scope |
| --- | ---: | --- |
| [Content-Atelier-Feasibility-Study.md](Content-Atelier-Feasibility-Study.md) | 413 | Draft of 29 September: source feasibility, moments ledger, weekly selection, brand voice, SerpAPI research, three gates, a full copy pack, risks, phasing and rough costs. |
| [Content-Atelier-Solution-Architecture.md](Content-Atelier-Solution-Architecture.md) | 1,598 | Proposed revision 2 of 4 October: Railway, FastAPI, RQ/Redis, Postgres/pgvector, continuous document intake, hybrid retrieval, topics, research, approvals, briefs, configurable packs, memory and operations. Replaces SerpAPI with OpenRouter web research and optional DataForSEO. |
| [Content-Atelier-Status-Audit.md](Content-Atelier-Status-Audit.md) | 419 | Audit of downloaded snapshots dated 10 October: capability coverage, 16 deviations, tests, missing foundations and recommendations. Its findings need to retain their original snapshot/date qualification. |
| [Content-Atelier-Implementation-Roadmap-Brief-Generation.md](Content-Atelier-Implementation-Roadmap-Brief-Generation.md) | 782 | Target workflow and workstreams through an approved researched brief. Excludes packs, scheduling and publishing; records RQ and uncapped-angle decisions. |
| [Content-Atelier-Implementation-Plan-Brief-Generation.md](Content-Atelier-Implementation-Plan-Brief-Generation.md) | 1,370 | Detailed execution plan, revision 3 of 11 October: source rulings, phases 0–6, work-item IDs, contracts, API/job catalogues, risks and acceptance checks. Records Command Center as identity provider and launch link only. |
| [Content-Atelier-Pitch.html](Content-Atelier-Pitch.html) | 570 | Interactive presentation of the larger product vision: sources → moments → weekly shortlist → approvals → email, carousel and three reel scripts. It is presentation code, not a pipeline integration. |
| [transcript.md](transcript.md) | 313 | Source material from the 16 September WIA/E2M requirements call. It supports the voice/strategy inputs, transcript-inspired content and copy deliverables; it is not an implementation status report. |

## Verified present state

The workspace contains substantial pre-existing uncommitted implementation changes, including `angle_workflow.py`, `comparison.py`, `refinement.py`, `backend/STORAGE.md` and updates to the SQL worker, review UI and proxy. These were not introduced by the documentation commit. Findings below distinguish the current local implementation from the older committed snapshot.

The real database returned the following counts during the review:

| Item | Observed |
| --- | ---: |
| Weeks / transcripts / transcript chunks | 2 / 20 / 329 |
| Key moments / content angles | 13 / 6 |
| Angles with embeddings | 6 |
| Transcript chunks with embeddings | 0 |
| Transcripts with known occurrence dates | 0 |
| Briefs / packs / assets / calendar entries | 0 / 0 / 0 / 0 |
| Approved angles | 0; all six angles were pending |

Week 1 was `awaiting_matching`; Week 2 was `queued` at the read-only check. This is a point-in-time observation, not a claim that a queued job has completed. The saved Week 1 readiness artifact records six real 1,536-dimensional `openai/text-embedding-3-small` embeddings via OpenRouter and preserves the accepted partial baseline. Embeddings do not establish completed matching, approval or editorial calibration.

The current UI explicitly submits `historical_comparison_v1`. The eight stages are extraction, history context, angle generation, initial embedding, initial assessment, refinement, refined embedding and final assessment. The legacy four-stage workflow still exists. Comparison results evaluate three provisional cutoffs, 0.78, 0.85 and 0.90, and cannot be approved while authoritative threshold selection is pending.

Evidence: `backend/backend_pipeline/angle_workflow.py:4`, `repository.py:104`, `sql_pipeline.py:127`, `gate_one.py:80`, `frontend/src/components/SQLWeeklyAngles.tsx:45`, and `backend/.storage-artifacts/verification/week1-embedding-readiness.json`.

## Material implementation differences

These are real differences from the target design. A planned feature being absent is a delivery gap, not evidence that the document falsely claims it is built.

| Area | Added documents' target | Current implementation | Assessment and evidence |
| --- | --- | --- | --- |
| Extraction unit and failures | Extract one source document independently, validate each moment and repair once. The weekly cycle reads an accumulated ledger. | Reconstruct all admitted transcripts for a week and make one extraction request. Invalid output fails the stage; no automatic extraction repair. | Structural change required. `sql_pipeline.py:154`, `pipeline.py:567`; execution plan rulings R2/R3 at lines 91–92. The optional angle-refinement call does not implement extraction repair. |
| Job execution | RQ on Redis, cron schedules and reconciliation sweep; Postgres remains the durable authority. | SQL jobs are claimed with locks, leases and heartbeats. Expired jobs fail and need explicit retry. Redis is present in development Compose but is not the SQL workflow's executor. | Deliberate current design versus planned migration. `repository.py:152`, `storage_cli.py:53`; execution plan decision 1 at line 77. |
| Data model and intake | Independent source documents; clients, people, consent, topics, decisions, source connections and versioned research/brief data. | Fixed 13-table baseline; transcripts, moments and angles require a week; local file admission labels sources `zoom`; no operational Fathom/Slack connectors. | Substantial schema and ingestion work remains. `001_approved_schema.sql:32`, `storage_sources.py:12`, `repository.py:49`, `database.py:46`. |
| Archive retrieval | Semantic and full-text search over segments/moments, with topic expansion for brief research. | Six angle vectors support prior-angle comparison. No encoded transcript chunks, moment-vector column, full-text index or hybrid archive-search service. | The archive-retrieval gap remains despite real angle embeddings. Schema at lines 49/58; `matching.py:125`. |
| Angle scoring and duplicate policy | Seven-criterion configurable rubric; every proof/quality-qualified angle after duplicate removal, with no weekly cap. | Five quality criteria with fixed weights. Legacy visibility uses adjusted score >70. Comparison qualification uses baseline score >70 and historical cosine below each cutoff; freshness affects ranking. Current-batch overlaps are flagged, not collapsed to a winner. | Both scoring and duplicate semantics still differ. `models.py:53`, `angle_workflow.py:12`, `matching.py:175`; execution plan R6 and item 3.B6 at lines 95/823. |
| Memory and freshness | Topic, angle and published-content memory; status-based cooldowns and eligibility from new evidence. The new plan gives explicit behavior for undated sources. | Validated prior-angle representatives and frozen comparisons; 28-day decay from actual first-generation time, up to 50% ranking penalty. No published-content/topic policy. Source dates remain unknown. | Narrow memory is implemented; the wider policy is not. `matching.py:30`, `matching.py:52`, `comparison.py:84`. In the new comparison workflow, decay cannot rescue an angle that fails the historical cutoff. |
| Gate 1 and briefs | Approve an angle with CTA/steer and atomically enqueue research and brief jobs; review/edit/version/approve the brief at Gate 2. | Legacy Gate 1 saves approval/rejection but creates no brief job. Comparison-owned angles cannot be approved. Brief table is empty; no research dossier, writer or real Gate 2. | Largest downstream delivery gap. `gate_one.py:80` and `gate_one.py:107`; plan lines 888–909. |
| Slack and authorisation | Slack actions call the same approval service; Atelier approver/editor/viewer/admin roles and consent enforcement. | No Slack approval endpoints or role lookup. The BFF requires a team session for SQL routes; the backend verifies a private secret and actor. Static app assets admit both team and client sessions. | Genuine missing capability/access restriction. `storage_api.py:48`, `frontend/server/app.mjs:109`, `frontend/server/app.mjs:142`. |
| Product UI | Real routed source, moments, cycle, research and brief screens; mock pack/calendar flows hidden in this brief-only scope. | Weekly Angle Review is API-backed. Other reachable studio/calendar/pack screens use fixtures and browser state; mock brief creation uses a 1.3-second timer. | Prototype behavior must not be counted as backend completion. `App.tsx:43`, `App.tsx:86`, `IdeaDetailModal.tsx:96`, `editorialWeeks.ts:3`. |
| Research/model configuration | OpenRouter web research and optional DataForSEO, staged models, enforced output schemas, routing/privacy controls and budgets. | No external research adapter. Provider supports both `json_schema` and `json_object`; example config selects the latter. Both generation stages default to the same model, though they can be configured separately. Embedding code default points at OpenAI, while the recorded Week 1 operation used OpenRouter. | Missing research and configuration alignment; privacy account settings were not verified. `provider.py:17`, `config.py:21`, `.env.example:50`. |
| Deployment and scheduling | Backend container, Railway worker/scheduler/storage, migrations, monitoring and one real cycle schedule in WIA's chosen timezone. | No backend Dockerfile/Railway deployment config or scheduled cycle. Mock week labels use India time; countdown uses Saturday 04:00 Chicago. | Backend readiness gap plus UI schedule mismatch. `frontend/src/utils/editorialWeeks.ts:8`, `nextRun.ts:1`; `DEPLOYMENT.md:164` still describes unavailable backend deployment features. |
| Command Center | Revised execution plan: existing sign-in and a launch link; remove Atelier proxy, fixture screen and data. | The launch/sign-in integration exists, but the sibling frontend still mounts its older Atelier proxy and retains fixture UI/data. The Atelier's own BFF correctly uses `/storage/*`. | Cleanup is pending. Do not describe the working Atelier BFF as the obsolete Command Center proxy. `../frontend/server/content-atelier-proxy.mjs:14`, `../frontend/server/index.mjs:1701`, `frontend/server/app.mjs:94`. |

## Statements to correct or qualify

| Finding | Documentation location | Verified correction |
| --- | --- | --- |
| **No embeddings have ever been generated** is stale. | Status audit line 16; roadmap line 166; execution plan risk K6 at line 1170 and structural issue S4 at line 285. | Six real angle embeddings exist in SQL and have a saved readiness/provenance record. Retain the distinct warnings that segment/moment retrieval, final matching and threshold calibration are incomplete. |
| **Only four job stages exist** omits the current local workflow. | Status audit line 60; roadmap line 15. | Four stages describe legacy runs. The new local comparison path has eight, frozen history, one refinement pass, original fallback and three scenario reports. This is uncommitted implementation progress after the audited snapshot. |
| **Gate 1 is generally available for generated angles** needs a workflow qualification. | Audit/backend summaries and roadmap line 123. | Legacy approval remains implemented, subject to complete current matching. The new UI's comparison workflow explicitly denies approval pending threshold selection, including after edits/reassessment. |
| **The BFF relays only JSON** is stale. | Execution plan lines 23 and 253. | It now also relays the narrowly allowlisted comparison CSV response, preserving the team-session boundary. The 64 KB body cap, 10-second timeout and query-string rejection still exist. Arbitrary Markdown/brief export is still unimplemented. `frontend/server/app.mjs:116`. |
| **11 unverified SQL tests / missing pgvector** describes the old audit environment. | Status audit lines 38/63; execution plan line 226. | Fresh review: 112 offline backend cases and 41 SQL/comparison cases passed; pgvector/Postgres tests ran on the guarded `atelier_test` database. Preserve historical test results but add the newer verification separately. |
| **No evaluation set exists** is too broad. | Status audit line 212. | `evaluation_cases.json` already contains corpus-derived synthetic diagnostic scenarios; the same audit mentions 14 diagnostic cases elsewhere. A founder-labelled calibration set, golden acceptance fixture and real retrieval evaluation are still absent. |
| **The prompt deliberately includes internal meetings** was not corroborated. | Status audit D4 and evidence pointer at line 397. | Current prompts do not contain the cited instruction. The execution plan already corrects this at line 111: the confirmed gap is the absence of classification/exclusion, not that prompt rule. Keep the correction consistent across files. |
| **source_type allows only three values** misstates SQL enforcement. | Status audit line 173. | The column is unrestricted `text NOT NULL`; the three types are in a comment, not an enum/CHECK. Admission currently hard-codes Zoom, and Slack ingestion is missing, but adding a Slack value alone does not require changing that column's SQL type. |
| **Exporter uses another developer's absolute path** is resolved locally. | Status audit D16. | The local exporter now resolves paths relative to its file and uses `DBML_CORE_PATH` or `@dbml/core`. The old absolute path is still in HEAD, so this is a working-tree fix, not part of the documentation commit. Other portability findings need their own review. |
| **Referenced architecture/storage files are missing** requires a Git/workspace distinction. | Status audit line 46. | The approved DBML, schema notes, `backend/STORAGE.md` and research material are present locally but untracked in this checkout. The downloaded/committed snapshot limitation was valid; local presence does not make those files available to someone checking out HEAD. |

The audit's broader conclusion that there is no complete, calibrated real-data workflow through a brief remains supported. Creating six embeddings does not invalidate that conclusion. Likewise, failed output validation is observed, but the audit's wording that whole-week batching directly *caused* enum/quote mistakes is a causal inference: batching magnifies the blast radius; it is not proof of why the model made those mistakes.

## Disagreements inside the documentation set

1. **Command Center boundary: actionable unresolved inconsistency.** Roadmap section 8.2 (line 553 onward) permits a `GET /v1/summary` status tile, replacing the fixture screen with a launch card, and changing Command Center `/launch` for deep links. Execution plan revision 3 explicitly prohibits summary/proxy integration and keeps Command Center's link/SSO unchanged (lines 69–80, 1091–1093); deep-link work moves to the Atelier server. Update the roadmap to revision 3's ruling or prominently mark these earlier alternatives as superseded.
2. **Angle count: explicit amendment, not a hidden code defect.** Architecture lines 32/630 and pitch line 242 target 3–5. Both newer planning documents record the 10 October decision for no upper cap; the mock still has four. Give the architecture/pitch a visible supersession note so implementers do not reintroduce a cap from the older design.
3. **Research provider: explicit design revision.** The feasibility study uses SerpAPI; the architecture and later plans choose OpenRouter web research plus optional DataForSEO. The architecture already explains this change. The mock research view does not establish a working SerpAPI integration.
4. **Deliverable scope: distinguish the product from this milestone.** Feasibility/pitch/architecture describe the full pack and final review. The two implementation documents intentionally stop at an approved brief and enqueue nothing after Gate 2. This is a narrower delivery scope, not abandonment of the larger product. State that distinction on the pitch and plan cover pages.
5. **Learning loop: deferred implementation.** The feasibility/pitch describe choices and edits improving later shortlists. The architecture puts automated proposed updates later; the current backend has neither that loop nor its decision/feedback data model. Treat it as future behavior.
6. **Older live product spec remains incompatible.** The sibling `../frontend/Content_Atelier.md` still records the 23 September nightly/per-call-gist workflow and independently written assets. The new plan instead uses a weekly ledger cycle and a researched brief. New plan ruling R1 says the older spec is historical, but the older file itself has not been marked superseded.
7. **Earlier local reconciliation is not covered by the new plan's precedence rules.** `research/architecture-comparison-and-reconciled-design.md`, dated 7 October, recommends bounded snapshot intake, four angles, three enforceable gates and independent drafting; it also explains why some team calls can contain useful evidence. The new documents instead propose continuous per-document intake, uncapped angles and exclusion of internal/vendor calls. The later decisions can supersede earlier recommendations, but this local document still describes its flow as controlling. Mark its superseded recommendations explicitly and resolve the internal-call policy; absence of classification alone does not establish that every internal call is unsuitable evidence.

The execution plan records four decisions; this review confirms they are written there, not that the code implements them or that independent approval records were inspected. Of the four, uncapped SQL candidate counts and the standalone Atelier UI align in part; RQ execution, Slack actions and Command Center cleanup remain future work.

## Verification and limits

Fresh checks completed during this review:

- Backend offline tests: **112 passed**, excluding the SQL/storage and comparison files.
- SQL/storage plus comparison tests: **41 passed**, using only `atelier_test`. Fixtures check that exact database name before truncating test tables and an autouse guard forbids external HTTP/model calls. Together the two backend commands verified **153 cases**.
- Auth, SSO and storage proxy tests: **12 passed**. Initial sandbox-localhost failures were environmental and disappeared when rerun with localhost access.
- Weekly storage/UI tests: **4 passed**.
- TypeScript: `tsc --noEmit` **passed**.
- Real database observation: explicitly read-only; no production rows or schema were changed by this review.

The full frontend suite and build were not rerun for this documentation review. Existing readiness records describe a prior unrelated scheduling-test failure; this review does not make a new claim about it. Railway services, external vendor/API capabilities, account retention settings, founder approval and real semantic calibration were not independently verified. No paid operation was triggered.

## Recommended documentation action

Keep the dated audit as historical evidence and add a current-state/supersession note. Use the revised brief-generation plan as the declared target *if those recorded decisions are the intended scope*, and the local comparison plan/`backend/STORAGE.md` for what the current slice actually does. Reconcile the roadmap's Command Center alternatives and the newer comparison policy before treating the plans as one executable specification. Track the existing local implementation/reference files in Git when ready so a checkout can reproduce the state this review inspected.

## Follow-up: stages through angle generation and review

A subsequent source inspection and read-only database check on 12 October confirmed the real Week 2 comparison run has completed, with 12 stored angle vectors across Week 1/2 and all 329 transcript chunks encoded. Week 2 is `comparison_review`; all eight comparison stages are completed and all 12 angles remain pending approval. The Week 2 run produced six validated moments and six angles; refinement was recorded as a skip because it had no targets. Live refinement therefore remains unexercised. No model or encoding operation was triggered by this follow-up review.

The comparison baseline for this scoped review is phases 1–3 of the new brief-generation implementation plan. Researching/writing the content brief is outside this follow-up scope.

| Stage | Status against the new plan | Remaining difference |
| --- | --- | --- |
| Source intake | Partial | Manual files for two weeks work. Continuous Fathom/Slack intake, independent documents and the wider backfill are missing. |
| Normalisation | Missing | Call classification, resolved speaker roles, client consent, glossary handling and occurrence-date recovery. All 20 admitted source dates remain null. The policy for useful internal-call evidence also needs reconciliation. |
| Segmentation/indexing | Partial, advanced | All 329 chunks now have vectors. Rich context headers, overlap, moment vectors and the hybrid/full-text archive retrieval service remain absent. |
| Moment extraction | Implemented differently | Whole-week extraction rather than per-document jobs; failures remain stage-wide rather than individual moment rejection/repair. The taxonomy still has seven types rather than the architecture's ten. |
| Topics and candidate themes | Missing | No topic registry, recurrence grouping, candidate pre-score, moment date window or unused-backlog theme selection. |
| Angle generation | Working, different unit | One generation request uses the current week's moments and historical arguments; the plan calls for one request per theme. Explicit pillar, hooks, why-now, differentiation, suggested CTA and what-is-new fields remain absent. |
| Light pre-angle enrichment | Missing | No web research adapter enriching candidate themes. This is separate from full post-approval brief research. |
| Rubric scoring | Implemented differently | The generator self-scores five criteria with fixed weights. The plan specifies a separate seven-criterion analysis call, reasons/evidence per criterion and configurable weights. |
| Memory/freshness | Partial | Frozen prior-angle history and exact comparisons work. Published-content/topic memory, status cooldowns, source/publication age and the ambiguous-band semantic judge remain missing. |
| Selection/review | Provisional | Three experimental historical cutoffs are reported; none is authoritative. Current-batch overlap is flagged rather than collapsing duplicates to the higher-ranked member. Comparison approval remains blocked. |

Gate 1 completion additionally requires the approver role, CTA choice/steer contract, structured pass reasons, snooze/revive/manual ideas and Slack actions. Queue execution remains Postgres leases rather than the proposed RQ/Redis transport; scheduling and reconciliation are still absent. These are separate platform/review gaps around the angle algorithm.

For the parallel brief implementation, existing angle bodies and verified moment/evidence links provide a usable development input. The production handoff must use a human-approved angle revision with its selected CTA and approved hash. The new comparison path currently supplies provisional candidates, so it does not yet satisfy that handoff. The plan's expanded angle fields also need an agreed API contract if the brief depends on them.

Sources: `backend/STORAGE.md:3`, `backend/backend_pipeline/chunk_encoding.py:12`, `sql_pipeline.py:128`, `contracts.py:79`, `angle_workflow.py:12`, `gate_one.py:80`, and implementation plan items 3.B2–3.B13 (lines 819–830). This follow-up did not rerun the test suite; earlier verification remains a dated record.

