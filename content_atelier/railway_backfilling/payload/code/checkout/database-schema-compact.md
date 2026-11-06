# Content Atelier — compact database schema

Approved design · 9 October 2026 · [Complete DBML](content-atelier-compact.dbml) · [Pipeline map](data-storage-schema.md) · [HTML flow](data-flow.html)

The approved schema extends the accepted 11-table structure with **`pipeline_runs` and `pipeline_events`**, producing **13 tables**. Stage tracking stays on `pipeline_jobs`, with processing-step messages and measured progress. Approval applies to the design; no database migration or runtime change has been executed. Transcript-to-angle testing remains unchanged.

The [storage and retrieval explanation](content_atelier_vectordb.md) details argument similarity, freshness, uncapped historical scoring, hybrid brief retrieval, fuzzy alignment and prior-content lineage. These behaviors must be implemented against the compact contracts below.

The complete DBML passes the official parser and PostgreSQL SQL export with **30 relationships, 18 checks and exactly two vector columns**. Run foreign keys, table documentation, local links and the complete-file end marker were verified without contacting a database.

## Stored records

| Table | Consumer and purpose |
|---|---|
| `weeks` | Actual seven-day source grouping, selected execution for the UI, overall state and coverage gaps |
| `transcripts` | Original input, source links and stable original passage locations for extraction and evidence inspection |
| `transcript_chunks` | Search passages and embeddings for supplemental briefing evidence |
| `key_moments` | Actual validated Call 1 output and exact supporting/context/qualification locations |
| `content_angles` | Actual validated Call 2 output, quality/matching, UI visibility, argument vectors, edits, CTA and Gate 1 decision |
| `angle_moments` | Foreign-key relationship between each angle and one or more supporting moments |
| `content_briefs` | Approved angle dependency, compact research/prior coverage, generated/edited contract and Gate 2 decision |
| `content_packs` | Production grouping, ordered content manifest, pack checks and Gate 3 decision |
| `content_assets` | Real assigned deliverables, governing briefs, generated/edited copy and asset checks |
| `calendar_entries` | Exact asset content scheduled per channel and actually confirmed publication |
| `pipeline_runs` | Actual execution identity, requested scope, frozen input references, trigger, overall state and partial-failure summary |
| `pipeline_jobs` | Actual stage executions and their outputs, failures, retry/ownership state and UI running status |
| `pipeline_events` | Meaningful timestamped milestones, warnings, retries and failures for the process timeline |

The only vector columns are `content_angles.embedding` and `transcript_chunks.embedding`, each `vector(1536)`. Embedding model/settings live in configuration. All other columns are ordinary SQL or JSONB. Source provider identity is actual ingestion provenance, not a model-provider registry. Authentication and display timezone remain external.

## Compact JSON contracts

The application must validate these structures before storing them. JSONB reduces tables; it does not automatically enforce references inside a document.

- `transcripts.passage_map`: ordered stable passage IDs, original-text character ranges, available start/end seconds, speaker labels/roles and attribution uncertainty. Resolve quotes against `original_text`; do not overwrite captured text or cited passage maps.
- `transcript_chunks.passage_refs`: ordered passage IDs/ranges belonging to the chunk's own transcript. `chunk_text` is the exact contextualized embedding input, not the authoritative original quote.
- `key_moments.moment_body`: quote, proposition, type, context summary, audience relevance, qualifications, strength, reasons, claim status and sensitivity from validated extraction.
- `key_moments.evidence_refs`: actual transcript IDs, passage IDs/ranges and anchor/context/qualification roles. Multiple transcripts are allowed; each must be admitted to that extraction. No separate copied transcript-ID list is needed.
- `content_angles.content_body`: title, argument, audience, tension, take, mechanism, reader decision, source assertions, editorial inference, qualifiers and risks. Quality scores/reasons are separate from editable argument content. Supporting moments use `angle_moments`, rather than a second JSON moment-ID list.
- `content_angles.matching_result`: actual historical/current comparison results, referenced angle IDs, similarities, evaluated recency/pair risk, overlap outcome and explanation. Retain qualifying historical comparisons used by scoring; reviewer top-k remains a display query. An unavailable/unfinished comparison is null, not zero risk.
- `content_angles.selected_cta`: actual chosen invitation/destination and any required owner information. This is a Gate 1 input; suggested offer fit in the generated angle is not approval.
- `content_briefs.content_body`: insight, audience, narrative, allowed scoped claims, CTA wording, exclusions, questions/answers and asset directions. Claims reference selected evidence with local validated IDs.
- `content_briefs.selected_evidence`: actual selected original transcript/passage references, optional discovery chunk IDs, roles, compact summaries, qualifications and use conditions. External framing has an actual URL and cannot establish a client result.
- `content_briefs.prior_content_context`: relevant original angle/brief/asset IDs, compact previous coverage and intended difference. Any published status references actual confirmed calendar publication. Previously generated/approved content remains distinct from published content.
- `content_assets.content_body`: format-specific final copy. Ordered slides and captions belong to the carousel body; scripts and shot directions belong to the reel body. No fixed five-piece pack or four-angle cap is implied.
- `validation_result`: checks against the exact asset content hash or pack manifest hash, actionable findings and actual warning acknowledgement identity/time. Unavailable checks do not count as passes. Store current checks needed by review; raw provider diagnostics stay outside the content tables.
- `pipeline_jobs.result_refs`: actual produced record IDs, coverage/output summaries and completed per-run reassessment when an existing angle is reused. It is not another full source/output payload copy.
- `pipeline_runs.input_refs`: admitted transcript/content IDs and their exact hashes, plus scope-specific approved input references. Freeze the admitted references before execution; later stage inputs remain attached to their actual job/content records. Do not copy source text or provider settings into this snapshot.
- `pipeline_jobs.progress_details`: current substep facts needed by the UI, such as which deliverable is active or which retrieval phase is running. Unknown unit totals remain null. Actual returned-output summaries belong in `result_refs`.
- `pipeline_events.details`: compact milestone-specific references or failure facts, including actual content IDs for review events. No raw model response, prompt, source dump, credential or heartbeat stream.

Research/prior-content arrays may legitimately be empty after completed research. Unknown coverage must instead be made explicit in `research_gaps` or the relevant completion state. Do not present missing research as a confirmed absence of prior content.

## Pipeline relationships

The week supplies transcripts. Extraction produces moments whose JSON references resolve into original passage maps. Angle generation supplies arguments linked through `angle_moments`. All valid angles persist, including score-suppressed candidates, while the UI selects the eligible visible set.

After Gate 1, the brief's `angle_id` and `angle_input_hash` identify the exact approved argument/CTA/evidence selection it consumed. Brief research starts with the angle's own supporting moments, expands through transcript retrieval, and follows relevant SQL content history into compact prior context. The vector search is discovery; original passages remain the evidence authority.

After Gate 2, each selected deliverable is assigned as a `content_assets` row with a brief reference and `brief_input_hash`. Its body/hash remain null while planned. Generation fills the actual body and current checks. Only selected slots are created.

The pack manifest hash covers the ordered selected slots, exact asset IDs, their content hashes, governing brief IDs and consumed brief hashes. Gate 3 requires every assigned asset to be complete, current checks to succeed and required warnings to be acknowledged. Calendar entries then pin an actual asset and its `asset_content_hash`; a schedule is not proof of publication.

## Editing and approval

Draft edits update the relevant content row and `updated_by`/`updated_at`. Hashes must include all approval-relevant fields and referenced evidence/assignments; they are not hashes of text alone. Actor identity is resolved by trusted server authentication.

Argument changes clear stale angle embeddings, matching results, quality/adjusted scores and visibility until re-evaluated. Re-embedding is required only if the canonical semantic embedding input changes. `embedding_input_hash` records that input, rather than pretending the embedding covers every SQL field.

Edits to content or selected CTA invalidate its current approval. Brief generation must verify current Gate 1 authority/hash; asset generation must verify current Gate 2 authority/hash. Final approval must verify current upstream inputs, complete deliverables and current checks in one transaction.

Once a record is approved, or relied on by downstream work, preserve it and create an edited replacement in the same table linked by `supersedes_id`. This is actual saved content, not a separate revision registry. Approved packs and their owning asset records remain stable; replacement consumed packs get replacement pack/asset records. This compact model gives each asset one owning pack rather than adding another membership table.

`supersedes_id` denotes changed copy of the same logical item, not merely a similar new argument. Resolve angle families when selecting historical representatives and excluding self-matches. Preserve the real `first_generated_at` on edited copies of the same logical angle. Replays or week revival do not reset the original generation age.

Approval columns retain the decision on that saved record. `pipeline_events` can record an actual review milestone for the process timeline; authorization and the authoritative content decision stay on the content record. Temporary keystrokes are not process events, and there is no separate review-history registry.

## Execution and implementation boundaries

`pipeline_runs` gives an execution an identity separate from its week. `weeks.active_run_id`, `pipeline_jobs.run_id`, `key_moments.run_id` and `content_angles.run_id` now have actual run foreign keys. The application also verifies week consistency; an event's optional job must belong to its run. Record creation `run_id` values retain actual original generation lineage.

A new generation request can create a new run; a retry remains another attempt of the same job. Run completion is relative to `run_scope`: an angle-generation run may complete when cards are ready, while a broader requested workflow may wait at a human gate. Partial failures remain explicit. In parallel stages, the UI derives active work from jobs instead of assuming a single current stage describes every active task.

Each job either operates on the whole week or one named target. Per-object brief/asset jobs can progress independently. A retry increments the attempt count on the same intent; successful upstream work is referenced rather than regenerated. A worker must claim/update/complete only while its lease token is current, and an idempotency key prevents duplicate intent creation. This does not promise exactly-once external model billing or publication.

The process UI reads overall state from `pipeline_runs`, live stage/step state from `pipeline_jobs`, and paginated history from `pipeline_events`. Update related run/job state and append corresponding milestone events transactionally. Heartbeats update the job instead of appending repeated events. Events for retry/failure capture the applicable `attempt_number`.

`completed_units` and `total_units` describe measured work within the current step/attempt and reset when that step/attempt changes. Compute a percentage only when a positive meaningful total exists. An in-flight LLM call normally shows its active step, elapsed time and heartbeat rather than an invented completion percentage. Unit counts do not estimate wall-clock completion time.

No additional stage-run, context, attempt-history or checkpoint table is introduced. The separate `audit_runs`, `audit_stage_runs`, `audit_events` and `audit_run_contexts` patterns were inspected in the AI Readiness backend; their relevant responsibilities map to these three execution tables and the compact input-reference field. Its domain-specific report/artifact/fetch tables are not copied.

The implementation must also validate JSON references, stage/target compatibility, hash calculations, self-link cycles, allowed state transitions, source use restrictions and original-wording/qualification checks. Dates use seven inclusive calendar days; ingestion cutoffs and display timezone remain configured separately.

Enable pgvector in the later SQL migration. Add workload-driven reverse-join/text-search indexes and the transcript retrieval index there; the initial angle-history comparison remains an exact vector scan over eligible representatives. Fixed vector dimensions do not establish model compatibility: changing the configured embedding contract requires retrieval to pause or all old vectors to be invalidated before replacement.

The DBML is the diagram specification. Its exported baseline SQL, catalog guard, repositories, evidence validators, workers and protected Gate 1 APIs now exist; see [the runbook](backend/STORAGE.md). The local database has all thirteen tables, with nine populated through angle preparation. Semantic ownership/evidence invariants are checked by the repository and validators; the approved SQL supplies the declared foreign keys and checks. Brief/production/calendar behavior remains a future contract. Existing calibration prompts, provider settings and historical response artifacts remain intact.
