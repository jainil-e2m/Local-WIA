# Content Atelier — minimal pipeline schema

<!-- governing-plan-note -->
> **Historical (marked 18 October 2026, plan item S.B9).** This document is kept for traceability. The one governing plan is [the implementation plan](backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md) (revision 6.1 or later); where they differ, the plan wins. Do not plan from this document.

**Superseded 21-table proposal.** The current proposal is the [13-table compact DBML](content-atelier-compact.dbml), explained in [compact storage decisions](database-schema-compact.md).

Previous proposal · 9 October 2026 · [Complete DBML](content-atelier-minimal.dbml)

This replaces the earlier expanded 51-table proposal. It contains **21 tables** for data actually passed between content-processing stages and their human decisions. No migration has been executed.

There are no policy/model/profile/timezone registries, separate source/copy revision tables, connector configuration tables or job-attempt logs. Backend configuration and the existing execution system own those responsibilities.

## What is stored

| Stage | Tables | Stored data |
|---|---|---|
| Execution grouping | `pipeline_runs`, `run_sources` | Actual batch/week, state/times/coverage and admitted source inputs |
| Source evidence | `sources`, `source_spans` | Captured original text, known source facts, ordered passages, available speaker/timestamp information and actual use restrictions |
| Transcript discovery | `transcript_chunks`, `chunk_spans` | Contextualized search passages, hashes, embeddings and original-passage membership |
| Moment extraction | `moments`, `moment_spans` | Quotes, propositions, context, qualifications, verification/strength/reasons and actual anchors/context across one or more sources |
| Angle generation | `angles`, `angle_moments` | All valid arguments, actual cited moments, original generation date, quality assessment and argument embedding |
| Evaluation/weekly reuse | `run_angles`, `angle_matches` | Current batch participation and actual scores/qualifying comparison results, including historical versus current matching |
| Brief research | `brief_contexts`, `context_evidence`, `context_prior_content` | Selected compact input, original citations/external framing, important qualifications, known prior coverage and gaps |
| Editorial brief | `briefs` | The actual structured contract including allowed scoped claims, evidence IDs, exclusions, questions/answers and selected asset directions |
| Production | `packs`, `pack_items`, `assets` | Explicit deliverable assignments, one governing brief per item, exact saved assets and pack membership |
| Validation/review | `check_results`, `approvals` | Actual checks/acknowledgements and human angle/brief/pack decisions, including the explicit CTA and steer |

## The two vector columns

- `angles.embedding`: semantic representation of the argument fields. Original angle data remains on the same row; actual moments are linked through `angle_moments`.
- `transcript_chunks.embedding`: representation of `chunk_text`. A result resolves through `chunk_spans` into original `source_spans`, then into relevant moments/angles and SQL content history.

Null vectors mean not yet encoded. All nonnull vectors use one configured embedding/encoding contract; changing that contract requires deliberate coordinated re-embedding. Because this schema does not label rows with model profiles, retrieval must be paused or all old vectors invalidated before replacing that contract; equal dimensions alone do not establish compatibility. No model/provider/profile data is stored here. Query vectors remain transient. The fixed vector dimension is part of the physical column definition.

## Core relationships

```text
source → original spans → moment → angle
                    ↑                ↓
           searchable chunks    run participation + matches
                                     ↓
                              Gate 1 decision + CTA/steer
                                     ↓
                    selected evidence + compact prior coverage
                                     ↓
                               brief → Gate 2
                                     ↓
                   pack item → exact governed asset → checks
                                     ↓
                           pack manifest → Gate 3
```

`run_angles` prevents copying an unchanged angle just to revive it in another week. It supplies the current evaluation/workstream while `angles.first_generated_at` preserves the real original age. For an edited record that still represents the same logical angle, `original_angle_id` points directly to its original record and the original generation date is retained. Historical matching selects one representative per logical angle and excludes the current logical angle itself.

Historical matching stores all qualifying results, including the evaluated recency weight and pair risk. The reviewer summary is a query over those results; it does not cap the scoring scan. Current pairs are separately labeled and receive no historical recency penalty. Recalculation before approval replaces that workstream's result set atomically; evaluated inputs/results already used in an approval remain inspectable, and a later reassessment uses a new execution record.

## Compact storage choices

- One source row contains the actual captured input; there is no separate source-version header. Changed original input becomes a new source row so old citations retain the old material.
- Canonical spans stay stable once cited. Chunking may create new chunk rows/memberships without changing their original spans. This schema assumes one canonical passage map for each captured input, rather than a parser-version registry.
- Evidence rows represent the selected passages and their role. Important surrounding qualifications get their own cited rows. Only actual selected external framing is retained; transient search-hit lists are omitted.
- The context body stores compact editorial context, not another full transcript bundle. Evidence and prior-content tables preserve the exact known references supplied to briefing.
- Brief/asset JSON is validated structured content, including allowed claims and their scope/source evidence. Dedicated claim-history tables are omitted; local claim/evidence IDs inside JSON must be validated by the backend.
- Carousel slides/captions and reel script/shot directions share their asset lifecycle and remain inside that asset's JSON body.
- `pack_items` serves both allocation and exact manifest membership. Every saved slot must be filled and valid before final approval; unused optional slots are not created.
- Approval rows store actual chosen CTA data, not a CTA-configuration foreign key. No unrelated policy payloads are copied into decisions.

## Data preservation and approval checks

Fewer tables do not mean approved material is overwritten. Captured source text, cited spans, completed context packets and saved content already relied on by an approval/downstream artifact must remain stable. An edit requiring changed approved copy creates a new actual content row and requires the affected approval again. Temporary keystrokes are not permanent versions; unused drafts need not be retained indefinitely.

Hashes tie embeddings/checks/manifests to actual content. They are integrity data consumed by the pipeline, rather than a separate version-management subsystem. A changed angle argument invalidates its embedding attachment. A changed asset body or pack membership invalidates old checks; final approval checks the current hashes transactionally and freezes its manifest/dependencies.

The application/migration must also enforce:

- Chunk membership refers to the chunk's own source, and moment anchors/context belong to admitted inputs.
- Candidate/history comparisons have compatible nonnull vectors; missing history/embeddings are not recorded as zero-risk completed matches.
- Gate 1 context refers to an approved decision for the intended run-angle. Supplied prior angle/brief/asset references agree with their actual lineage.
- Evidence used as internal proof preserves original wording, attribution uncertainty and limiting facts. External framing cannot substantiate a client result.
- Each asset selected by a pack item has that item's governing brief and requested format; that exact brief has Gate 2 approval.
- Gate 2 requires answered required questions/current upstream approval. Gate 3 requires complete selected slots, current checks, resolved blockers and exact warning acknowledgements.
- Human authority comes from existing server authentication. Models cannot create approvals; browser-supplied actor identity is not trusted.
- Use restrictions are checked during retrieval and again at use/approval. Copy approval does not establish public-use consent.

DBML contains basic foreign keys/checks, not all of those cross-record or authority rules. Enable pgvector in the implementation migration. Add reverse-join and text-search indexes from actual access patterns; exact angle matching remains the initial method. The complete file passes the official DBML parser with 21 tables, 38 relationships and exactly two vector columns. No database was contacted during document validation.

## What is outside this schema

Configuration files own prompts, editorial/format rules, model/provider selection, timezone, scoring thresholds and embedding settings. Existing operational storage owns queues, retries, adapter cursors, diagnostic payloads and cache/replay policies. These responsibilities continue to exist without being content tables.

Schedules and publication events are outside the core ending at the approved pack. Previously published examples can be admitted as actual `sources` and referenced by `context_prior_content.source_id`; missing original angle/brief lineage stays null. Generated/approved assets are not labeled as published without actual confirmation. If persistent Calendar or publication tracking is later included, add its substantive data then.

This simplification does not promise exact historical provider/request replay or keep old vector attachments across embedding-contract changes. It does preserve actual source/content relationships and saved decisions/results required by the core pipeline.
