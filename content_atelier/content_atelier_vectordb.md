# Content Atelier — storage, similarity and evidence retrieval

<!-- governing-plan-note -->
> **Historical (marked 18 October 2026, plan item S.B9).** This document is kept for traceability. The one governing plan is [the implementation plan](backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md) (revision 6.1 or later); where they differ, the plan wins. Do not plan from this document.

Approved 13-table design · 9 October 2026 · [DBML](content-atelier-compact.dbml) · [Schema and pipeline map](data-storage-schema.md) · [HTML flow](data-flow.html)

This is the storage/retrieval contract for the approved compact schema. The baseline, real corpus admission and versioned SQL workflows exist locally; see [implementation and verification](backend/STORAGE.md). The current weekly path is [historical comparison plus one refinement pass](implementation-plan-historical-comparison.md), reporting three cutoffs without authorizing Gate 1 approval. Legacy two-call runs preserve their existing scoring/approval contract. Persistent external generation/encoding/refinement switches remain disabled; separately authorized process-local operations have encoded all 12 angles and 329 Week 1/2 transcript chunks. Hybrid brief retrieval, dossier preparation and Gate 2 now run offline behind disabled switches; see [brief implementation status](implementation-status-content-briefs.md). Full-text search complements semantic discovery. No trigram extension/fuzzy evidence score was added; exact source bindings remain authoritative. The calibration runner remains separate.

## 1. Why one PostgreSQL database is sufficient

pgvector stores vectors on ordinary PostgreSQL rows and supports cosine distance. SQL remains the authority for content, relationships, approvals, evidence locations and execution state. A vector is a derived representation for discovery or comparison, not a second copy of the source record. [pgvector documentation](https://github.com/pgvector/pgvector)

Only two kinds of data have persistent embeddings:

- **Content angles:** semantic signatures of generated arguments, for historical overlap evaluation and discovery of relevant previous coverage during briefing.
- **Transcript chunks:** contextual passages, for finding supplemental evidence during brief research.

Key moments, briefs, assets, packs and calendar entries are reached through SQL or validated JSON references. Their actual text is stored when a pipeline phase or UI needs it; another embedding is not necessary to preserve their relationships.

The approved tables are:

| Responsibility | Tables | Why retained |
|---|---|---|
| Source and evidence | `weeks`, `transcripts`, `transcript_chunks`, `key_moments` | Weekly inputs, original proof, search passages and extracted moments |
| Argument and review | `content_angles`, `angle_moments`, `content_briefs` | Generated arguments, exact grounding, editable decisions and briefing contracts |
| Production and distribution | `content_packs`, `content_assets`, `calendar_entries` | Assigned copy, pack approval, scheduling and actual publication |
| Execution and visibility | `pipeline_runs`, `pipeline_jobs`, `pipeline_events` | Actual execution intent, live processing state and meaningful history |

Model/provider settings, embedding profiles, prompt versions, timezone and editorial schedules are configuration rather than new database registries. `weeks` is retained because the weekly workspace consumes it. `transcripts.source_type/upstream_id` records actual source provenance, not model configuration.

## 2. Compact storage preserves exact relationships

### Originals and moments

`transcripts.original_text` is preserved captured text. Its `passage_map` contains stable local passage IDs, original character ranges, speaker labels/uncertainty and timestamps when known. A changed captured input receives a new transcript row/hash. Existing citations continue to resolve against their original row.

`key_moments.moment_body` stores the validated extraction: quotation, proposition, contextual qualifications, strength/reasons, audience relevance and claim/sensitivity information actually needed downstream. `evidence_refs` stores transcript IDs, passage IDs/ranges and roles such as anchor, context or qualification. A moment may require evidence from multiple transcripts.

`angle_moments` supplies real SQL foreign keys between an angle and its moments. Do not also maintain an independently editable JSON moment-ID list on the angle.

### Chunks and briefs

`transcript_chunks.passage_refs` refers into its own transcript's stable passage map. The chunk's text is the exact contextualized embedding input; resolve quotations against `original_text`, because context headers or search formatting are not original speech.

`content_briefs.angle_id/angle_input_hash` records the exact approved angle consumed. The brief stores selected original evidence, compact prior-content context, unresolved gaps and its generated/edited contract. Claims use locally validated evidence IDs. A retrieved old angle is prior editorial coverage; it is not new factual proof.

### Assets and publication

Each `content_assets` record identifies its governing brief and consumed `brief_input_hash`. Each asset belongs to one pack. `content_packs.manifest_hash` binds ordered slots, exact asset IDs/content hashes and governing brief IDs/hashes. A calendar entry pins an exact asset/hash, channel and publication state.

This is the compact design's trade-off: many-to-many angle grounding uses a small join table; passage/evidence/context detail uses JSON. JSON reduces table count but does not enforce references. The application must validate existence, passage ownership, range bounds, permissions and week/run consistency. Do not delete or silently rewrite referenced originals.

## 3. What the two embeddings represent

### Angle signature

Embed a canonical structured argument, using the current signature-builder fields:

```text
Audience: ...
Tension: ...
Argument: ...
Take: ...
Mechanism: ...
Reader decision: ...
```

Normalize formatting consistently. Exclude titles, scores, IDs, generation dates, freshness labels and approval/publication state. A catchy title should not decide whether two arguments repeat; dates belong in the subsequent freshness calculation. The signature must retain enough argument/mechanism detail to separate “same audience/topic” from “same editorial claim.”

`content_hash` covers approval-relevant content. `embedding_input_hash` covers only the canonical semantic input. A CTA-only or display-title edit can require reapproval without requiring another embedding, provided those changes do not change the argument signature. An argument/evidence edit must invalidate affected quality, matching and visibility decisions.

### Transcript chunk

Chunk along coherent passage boundaries, preserving nearby qualifications and source/speaker facts that are actually known. A starting experiment around 200–400 tokens with modest contextual overlap is a tuning proposal, not a schema limit. A fixed window that separates “the result occurred only under these conditions” from the result is poor evidence retrieval.

Keep the exact input in `chunk_text`, original locations in `passage_refs` and an input identity in `content_hash`. Unknown dates or identities stay unknown. Deduplication must include locations as well as text; repeated identical statements at different original positions can matter for attribution.

### Embedding contract

The baseline is **OpenAI `text-embedding-3-small`, 1,536 dimensions**, matching the approved vector columns and current configuration default. OpenAI documents 1,536 as this model's default dimension. This establishes compatibility, not that the model is optimal for this corpus. [OpenAI embeddings guide](https://developers.openai.com/api/docs/guides/embeddings)

Use the same configured embedding contract for indexed text and query text. Do not mix equal-sized vectors from different models as though dimension equality established compatibility. Configuration must identify the embedding contract; a contract change requires pausing retrieval or invalidating/rebuilding all affected vectors before serving comparisons. A separate embedding-profile table is unnecessary while one active contract is enforced.

Nullable vectors represent preparation failure or pending work. An unavailable vector is not a zero vector and not evidence of low similarity. Candidate/history embedding failures must be surfaced in matching coverage; chunk failures must be surfaced in research coverage.

## 4. Which stages use vector retrieval

| Stage | Supplied data and vector use | Reason |
|---|---|---|
| Weekly admission | Originals and stable references; prepare chunk embeddings separately | Preserve complete input and make later evidence searchable |
| Call 1: key moments | Read complete admitted transcripts; no semantic top-k filter | Important moments and qualifications must not disappear because a search did not nominate them |
| History / Call 2 | Freeze the complete eligible archive; supply compact substantive historical arguments and all validated current evidence | Generate with prior coverage in view; history is context, never current factual evidence |
| Initial matching | Exact comparison of original signatures against all frozen historical signatures; separate quality diagnosis | Target baseline quality at most 70 or maximum cosine at least 0.78 for recovery without suppressing originals |
| Call 3 / final matching | One optional reconstruction pass using all current moments, including unused ones; validate and encode replacements | Compare original/replacement families at 0.78, 0.85 and 0.90 using identical archive/clock |
| Gate 1 | Provisional comparison counts, evidence, recovery reasons and scenario-specific current-batch flags | Approval remains disabled until an authoritative policy is selected later |
| Brief research | Exact grounding plus hybrid chunk search and prior-angle search | Find supporting/contradictory context and past coverage without losing provenance |
| Brief generation / Gate 2 | Consume the selected evidence/context packet and known gaps | Retrieval must be resolved into reliable scoped input before drafting |
| Asset generation | Consume current approved brief/hash and evidence contract | Routine copy production should not silently introduce claims from new retrieval |
| Gate 3 / calendar | SQL completeness/checks, exact asset hashes and actual publication | Scheduling is about approved saved copy and confirmed distribution |

Call 1 extracts moments, Call 2 generates historically aware proposals, and optional Call 3 reconstructs targeted arguments from current evidence. Similarity evaluation remains numerical; Call 3 is not a similarity judge. Brief research/drafting is later work. The legacy calibration prompts and two-call workflow remain unchanged.

All source-valid generated arguments persist. New comparison originals/replacements remain provisional, with no authoritative visible/suppressed assignment from an arbitrary cutoff. Valid suppressed legacy arguments remain eligible history. Invalid raw responses are operational artifacts, not valid angle records. Unfinished new comparison workflows are excluded from historical admission; completed workflows contribute one latest source-valid representative per family, independently of experimental scenario selections.

## 5. Angle similarity, freshness and top-k

### Freeze the comparison universe

Freeze historical IDs/content/signatures/qualifications before Call 2; freeze the evaluation clock immediately after validated Call 2. Initial and final assessment use the same archive and clock. Pin quality inputs, source views/moments, generation dates, actual float32 vectors and the encoding contract. Changed frozen inputs require a new assessment intent; retries retain the snapshot. Earlier eligible same-week work can contribute, but an identical captured source cohort is a replay/current cohort and is excluded, alongside the candidate's replacement family.

Use one representative per logical angle family under a documented rule. An edited copy preserves the original `first_generated_at`. Regeneration/import/re-embedding time must not make an old argument appear fresh. A genuinely new but similar argument is a new historical record, not automatically a superseding version.

Evaluate current candidates against each other in a separate pairwise pass. Do not let insertion order make the first candidate “history” for the second and impose an artificial age-zero historical penalty.

### Comparison eligibility and retained ranking contract

For each `t` in **0.78, 0.85 and 0.90**, require valid grounding/references, complete matching, **baseline_quality > 70**, and **maximum_historical_cosine < t**. Equality fails. Freshness-adjusted score is for ranking/explanation and does not independently disqualify a candidate. A qualifying replacement wins within its family; otherwise retain a qualifying original; otherwise report no qualifying member. Count the family once. Recalculate current-batch flags at 0.90 within each scenario's selected cohort.

Initial quality weakness and historical repetition are diagnoses for one recovery pass, not final suppression. Call 3 receives originals/reasons, substantive historical matches and raw cosines, all current moments with exact evidence, and the other current proposals. A different relevant argument may use previously unused moments, but no historical evidence IDs. Its own quality must pass the unchanged rubric; lowering cosine alone cannot rescue weak quality. There is no fixed weekly count or additional semantic loop. No-supported-alternative is a valid outcome; an invalid response is an operational failure.

The retained freshness/ranking values and legacy selection rule are:

| Setting | Starting value | Interpretation |
|---|---:|---|
| Historical cosine floor | 0.78 | Begin historical overlap calculation |
| Current-batch close-overlap flag | 0.90 | Flag close current arguments; final disposition needs editorial policy |
| Freshness half-life | 28 days | Recency contribution halves every 28 days |
| Maximum penalty | 0.50 | At most half the base quality score |
| Legacy visible adjusted score | Strictly greater than 70 | Only the preserved two-call workflow uses adjusted score for eligibility |
| Reviewer match summary | 5 | Proposed initial display count, ordered by pair risk |
| Historical scoring top-k | **No fixed cap** | Every eligible qualifying historical comparison contributes |

These are starting configuration values, not empirically calibrated accuracy claims. The visible match count is a display budget, not permission to calculate novelty from only five neighbors.

For candidate `c` and historical representative `h`:

```text
similarity = 1 - cosine_distance(c.embedding, h.embedding)
overlap = clamp((similarity - 0.78) / (1 - 0.78), 0, 1)
age_days = (evaluation_time - h.first_generated_at) / one_day
recency = 2 ^ (-age_days / 28)
pair_risk = overlap * recency
historical_risk = max(pair_risk across eligible history)
adjusted_score = base_score * (1 - 0.50 * historical_risk)
```

The cutoff includes 0.78, but overlap is zero exactly at the floor. Treat future/invalid generation dates as data-quality issues requiring a defined correction; silently changing dates makes evaluation misleading. With a complete eligible corpus and no qualifying comparisons, historical risk is zero. Missing vectors or incomplete history are not that situation.

The current five-dimension quality baseline is:

```text
base_score = 20 * (
  0.35 * grounding +
  0.25 * source_relevance +
  0.15 * audience_fit +
  0.15 * specificity +
  0.10 * editorial_usefulness
)
# Each dimension is scored from 0 to 5.
```

Model-assessed quality remains an editorial estimate, not an independently verified truth score.

For a base score of 90 and cosine similarity of 0.95, the adjusted score is about **60.76 at 7 days**, **72.61 at 28 days**, and **85.65 at 84 days**. At similarity 0.82 and age 7 days it is about **83.12**. Freshness changes the penalty applied to repetition; it is not part of the embedding.

### Why five nearest angles are insufficient

A recent moderately similar angle may have more pair risk than an older highly similar angle. An initial cosine-nearest-five query can omit the maximum freshness-weighted risk. Use an exact scan of all eligible angle representatives initially, calculate risks, then derive the reviewer summary from the result. If archive size later requires a faster method, it must preserve the decision rule or explicitly measure and accept retrieval loss.

The max-risk rule avoids counting the same repetition penalty multiple times. The separate baseline quality gate prevents weak but dissimilar content from qualifying. There is no fixed selection count. Qualified scenario counts do not establish semantic accuracy without later real embedding tests and editorial review. Backend approval is blocked through run/family provenance and remains blocked after edits, rescoring and comparison reassessment.

Store actual evaluated parameters/time, history IDs/hashes, raw cosine, age, overlap, recency and pair risk in `matching_result`. These are facts behind a particular decision, not a configuration-version registry. Current-batch results belong there separately. A close-current flag is not automatically an approved suppression/merge policy; the UI must disclose unresolved overlap.

Current code still needs reconciliation with parts of this contract: the scoring implementation can skip missing vectors and labels aggregate risk `max_similarity`. The desired storage semantics must not disguise incomplete coverage as a finished low-risk result. These documentation changes do not alter that testing code. See the [focused angle specification](research/pgvector-creation-and-angle-matching-spec.md).

## 6. Brief research follows three complementary routes

### Route A: original grounding, always supplied

Start with the exact approved angle/hash and `angle_moments`. Resolve each referenced moment's `evidence_refs` into original transcript passages, then recover relevant neighboring context and qualifications.

This route is deterministic. A source supporting the chosen angle must not be dropped because another chunk ranks higher or uses closer vocabulary. Include relevant counterevidence and claim limits, not just a shortened favourable quote.

### Route B: supplemental hybrid passage discovery

Generate focused research queries for the approved argument, mechanism, reader decision, missing support and potential counterexamples. Apply permitted-source/date/role/use restrictions consistently to semantic and lexical searches.

For each query:

1. Search chunk embeddings for semantic relevance.
2. Search the same eligible chunks with PostgreSQL full-text retrieval for exact terms, numbers and named concepts.
3. Fuse ranked candidates, deduplicate overlapping evidence, optionally rerank when evaluation demonstrates a benefit.
4. Resolve hits to original passages, restore qualifications/neighboring context, and grade whether they actually support a scoped claim.

PostgreSQL provides `websearch_to_tsquery` for search-like text; configuration/language must suit the source corpus. An English configuration is the original architecture's baseline, not a universal multilingual solution. [PostgreSQL text-search controls](https://www.postgresql.org/docs/current/textsearch-controls.html)

A high semantic score nominates a passage; it does not verify a quotation, attribution, client result or causal claim.

### Route C: relevant prior content coverage

Use both of these discovery routes:

- **Reverse evidence lineage:** retrieved original passage/range → overlapping moment evidence → `angle_moments` → prior angles → briefs → assets → calendar.
- **Independent argument search:** query prior angle signatures directly, then join their SQL lineage. Related prior coverage can come from different transcripts and would be missed by reverse evidence lookup alone.

A transcript ID match is too broad. Match actual passage/range overlap and restore that moment's own context/qualification references. A chunk can span multiple passages, a moment can cite multiple transcripts, and an angle can combine several moments.

Also inspect prior publications of the chosen angle's own family through SQL. Excluding self-family from a novelty penalty must not hide that family's previous use during briefing.

For each relevant prior item, preserve compact facts: prior argument, audience/claim/mechanism, prior asset use, known publication state/time, the current angle's proposed difference, and exact angle/brief/asset IDs. Distinguish generated, approved, scheduled and actually published content. A schedule or URL alone does not prove the external wording matches the saved approved asset.

The purpose is to preserve relevant context for a distinct brief. Retrieval cannot guarantee distinctness by itself: the brief must explicitly state its intended difference and the reviewer must assess that choice.

## 7. Semantic, lexical, fuzzy and exact matching have different jobs

| Method | Appropriate use | Limitation |
|---|---|---|
| Cosine over embeddings | Argument overlap and meaning-based passage discovery | Similar meaning is not verified fact, quotation or identity |
| PostgreSQL full-text search | Exact concepts, product names, numbers and query terms | Stemming/lexical matching may miss paraphrases |
| `pg_trgm` string similarity | Spelling variants and approximate name/label lookup | A similar name is only a candidate identity |
| Normalized quote-string matching | Locating a quoted span around a known location | Must preserve numbers, negation, attribution and exact approved quotation rules |
| Exact IDs / original ranges / hashes | Provenance, original wording, consumed inputs and approval validity | Requires preserved originals and validated references |

The original solution architecture describes semantic and keyword retrieval with Reciprocal Rank Fusion (RRF), trigram name matching, and fuzzy quotation alignment. It does **not** specify a general fuzzy-logic inference engine. `pg_trgm` compares strings using trigrams; it complements semantic search rather than replacing it. [PostgreSQL pg_trgm documentation](https://www.postgresql.org/docs/current/pgtrgm.html)

The original quote-alignment proposal searched a ±90-second window with a normalized similarity threshold of 0.90. It did not fully specify a string scorer or normalization rules. Later strict quotation validation for the current testing slice takes precedence; this document does not relax it. A fuzzy match may locate an original span but cannot approve changed quantities, removed qualifications or altered speaker identity. String similarity 0.90 and embedding cosine 0.90 are different measurements.

If implementing a string scorer later, specify its algorithm, normalization and protected tokens. RapidFuzz exposes several scorers with different semantics, so “use fuzzy matching at 90” is not a complete contract. [RapidFuzz scorer documentation](https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html)

RRF combines ranks, not incomparable raw cosine and lexical scores:

```text
fused_score(document) = sum(1 / (60 + rank_in_each_retrieval_list))
# Lists use ranks starting at 1; absent documents contribute zero.
```

The `60` is the original architecture's starting constant, consistent with the method studied in the [RRF research paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf). Fusion ranks evidence for inspection; it does not decide factual admissibility.

The architecture's older extra LLM angle-similarity judge is superseded by the accepted numerical two-call angle setup. Optional passage reranking during briefing is a different later research operation, not that third angle judge.

## 8. Brief retrieval budgets and compact context

The original architecture suggests 6–10 targeted research queries, 50 semantic and 50 lexical candidates per query, optional reranking of roughly 50 fused candidates, and up to two gap-filling rounds. About 12 total queries and 40 graded evidence items can serve as initial bounded budgets.

These are research starting budgets, not approved universal counts or schema constraints. They do not set the angle-history scoring top-k. Tune them with representative briefs and record material coverage limitations.

Reserve space first for chosen-angle grounding, essential qualifications/conflicts and strongly related previous coverage. Remove duplicate overlapping passages and repeated argument-family summaries before truncating. Do not replace original proof with an old generated brief summary.

`content_briefs.selected_evidence` retains selected locations, roles, compact excerpts/summaries and use conditions. External framing uses explicit URL/reference/type; it cannot impersonate internal client-result proof. `prior_content_context` retains the prior-coverage summary and references. `research_gaps` retains relevant unresolved questions, inaccessible sources, conflicts and material budget omissions.

An empty context array can mean “completed search found no relevant items.” It must not silently mean “search was skipped or archive was unavailable.” Completion/coverage state and gaps explain the distinction.

Prepare research before creating the real draft. `content_briefs.content_body` is required, so do not create a fake blank brief merely to checkpoint research. If retries need durable prepared context, keep compact actual selected references/summaries in `pipeline_jobs.result_refs`, pin the supplied input with `input_hash`, and save the valid draft with its selected evidence/prior context together.

## 9. Physical indexes without extra data tables

| Access path | Initial index/strategy | Reason |
|---|---|---|
| Week/source lookup | Approved source/weekly B-tree indexes | Admission, UI grouping and direct evidence lookup |
| Angle-to-moment lookup | `angle_moments` composite primary key | Direct grounding |
| Moment-to-angle lookup | Baseline B-tree on `angle_moments(moment_id)` | Reverse prior-coverage traversal |
| Exact historical angle evaluation | Exact cosine scan of frozen eligible representatives | Preserve uncapped freshness-weighted decision |
| Chunk semantic search | Exact retrieval initially; HNSW with `vector_cosine_ops` when measured workload warrants it | Supplemental passage search can accept measured ANN trade-offs |
| Chunk keyword search | Expression GIN on `to_tsvector('english', chunk_text)`, or appropriate configured language | Full-text lookup without adding a third stored column/table |
| Relevant JSON evidence lookup | Targeted JSONB indexing or a validated narrowed scan after passage retrieval | Preserve the compact schema without indexing every JSON field |
| Prior brief/asset/pack joins | Index actual frequent FK/join predicates in the later migration | Fast history enrichment |
| Job/event UI | Approved status/lease, run/time and job/time indexes | Active work and paginated history |

GIN is the usual preferred full-text index type in PostgreSQL. An expression index can use the approved `chunk_text` column; an extra stored `tsvector` field is not part of the approved DBML. [PostgreSQL text-search indexes](https://www.postgresql.org/docs/current/textsearch-indexes.html)

pgvector defaults to exact nearest-neighbor search; approximate indexes such as HNSW trade some recall for speed. Filtering can affect approximate candidate recall, so test allowed-source filtered retrieval against exact results before selecting HNSW settings. Index settings are deployment configuration, not an embedding-profile record. [pgvector indexing documentation](https://github.com/pgvector/pgvector)

Illustrative later migration statements:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
-- Existing approved table: no vector side table.
CREATE INDEX transcript_chunks_text_search_idx
  ON transcript_chunks USING gin (to_tsvector('english', chunk_text));
-- Add only after workload/recall evaluation:
CREATE INDEX transcript_chunks_embedding_hnsw_idx
  ON transcript_chunks USING hnsw (embedding vector_cosine_ops)
  WHERE embedding IS NOT NULL;
CREATE INDEX angle_moments_moment_idx ON angle_moments (moment_id);
```

The HNSW/full-text statements are examples for the later briefing-retrieval phase. The implemented baseline already enables pgvector and the reverse moment/angle index; it uses exact angle matching. JSON validation, transaction guards, durable processing and protected Gate 1 state transitions are described in [the implementation runbook](backend/STORAGE.md).

## 10. Editing must invalidate stale authority

In draft, update body/edit columns and recompute relevant hashes. After approval or downstream consumption, preserve the original and create an edited replacement linked by `supersedes_id`. Protect against supersedes cycles and accidental family merging.

For angles, distinguish semantic input changes from other approval-relevant changes. Clear stale scores/matching/visibility when evaluation inputs change. Rebuild the vector only when its canonical input changes; until then null vector/input hash represents unavailable semantic evaluation, not novelty.

Approval requires current content hash, actor/time and required CTA/contract checks. Downstream consumers verify the approved hash and actual dependency:

```text
approved angle/hash -> brief.angle_input_hash
approved brief/hash -> asset.brief_input_hash
exact ordered assets/brief hashes -> pack.manifest_hash and approval
exact approved asset/hash -> calendar.asset_content_hash
```

Revalidate at work/approval time, not only when a button was initially displayed. Gate 3 requires complete assigned assets, current successful checks and required warning acknowledgement. A missing check is not a pass.

Ordinary asset edits stay inside the approved brief's claim scope. Added facts or changed claims return to brief research/review. Actual publication must be confirmed; if external wording can change, publication context should be labelled accordingly rather than presumed to match the saved asset.

## 11. Runs, processing steps and retry visibility

`pipeline_runs` stores one actual requested execution and frozen admitted IDs/hashes. The week can have several runs. A retry of the same job stays inside its run; a new generation request can create another run. Completion is relative to requested `run_scope`.

`pipeline_jobs` stores one stage for the whole week or one target. Brief and asset jobs can run independently. Its live step/message, heartbeat, meaningful unit counts, attempt number and lease support progress and recovery. The idempotency key identifies a single intent; it must include the scope/input identity needed to distinguish new work from retry.

`pipeline_events` provides append-only meaningful milestones, warnings, retries and failures. Record compact IDs/failure facts, not transcript dumps or every heartbeat. Update related job/run state and milestone events transactionally. Events expose review milestones; approval authority stays on the content record.

Show measured percentage only when the current step has a meaningful known total. A running LLM request usually shows step/elapsed time/heartbeat. Do not manufacture progress from elapsed time. Unknown totals are null.

Workers must claim, refresh and complete jobs only while holding a current lease token. Persist actual output references for safe reuse; stale workers must not overwrite newer completion. Idempotency and leases do not guarantee exactly-once provider billing or external publication.

The inspected AI Readiness backend's run/stage/event/context responsibilities are compacted into these three tracking tables plus frozen input references. Its audit-specific report/artifact/fetch tables are not part of Content Atelier's content pipeline.

## 12. What the compact schema deliberately cannot claim

The schema does not provide a global legacy-publication import catalogue. Internally produced assets require real brief lineage. Authorised external examples can enter a brief as labelled URL/excerpt context; do not fabricate angle/moment/brief records to fit historical imports. Record archive coverage gaps.

No extra tables are needed merely to remember configuration versions, provider metadata, editorial cycles or intermediate retrieval lists. Preserve actual consumed evidence/context and decision facts because they explain the saved content. Raw diagnostics remain in the existing operational/testing boundary.

Before production, validate the JSON references, stable passage preservation, rights filters, embedding compatibility, historical completeness, current-batch overlap disposition, scorer calibration, evidence retrieval quality, hash-bound gate guards and retry semantics. This is an implementation checklist grounded in the approved design, not a claim that those mechanisms already run.

Further detail: [angle creation/matching contract](research/pgvector-creation-and-angle-matching-spec.md), [brief provenance and prior coverage](research/briefing-provenance-and-prior-content-context.md), and [compact column contracts](database-schema-compact.md).


## Implemented brief retrieval — 12 October 2026

Queries are transient embeddings in the chunk vector space, cached by exact text, endpoint, model, dimensions, purpose and synthetic/real identity. They introduce no SQL vector column. Research starts with 6–10 queries and permits two bounded gap rounds, twelve distinct queries overall, with one query-encoding batch per round. The frozen permitted chunk IDs are identical for exact cosine and English full-text searches. Each branch ranks up to fifty hits; reciprocal rank fusion uses constant 60. The first five fused chunks per query are inspected, with original neighboring context and complete linked moment qualifications restored. The evidence budget of about forty passages is soft: complete qualification groups survive, while oversized required packets fail preflight.

Evidence IDs bind exact original transcript/passage/ranges, source hashes/use metadata, claim status and qualifications. The same brief keeps inherited angle evidence even if it ranks poorly in retrieval. Similarity cannot verify a quote, establish entailment or upgrade a reported observation to a measured result. Fuzzy term lookup remains optional future work; it cannot replace exact quote/range checks.

Prior argument vectors are checked against completed compatible provenance. SQL joins restore moment, brief and calendar use, including exact original angles with prior briefs when a refinement represents their family. Archived arguments and actual uses are frozen before research; later source, moment, vector, approval or publication changes cannot silently reuse an old writer packet. Generated/approved/published states remain distinct, and missing legacy publication coverage is an explicit Gate 2 acknowledgement. The brief itself has no embedding.
