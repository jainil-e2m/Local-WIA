# pgvector creation and angle matching — approved compact contract

Updated 9 October 2026 · [Approved DBML](../content-atelier-compact.dbml) · [Storage rationale](../content_atelier_vectordb.md)

This replaces the earlier embedding-profile/vector-side-table proposal. The approved database contains thirteen tables and exactly two inline vector columns. It remains a design, not an executed migration or a production verification.

## 1. Storage and embedding contract

| Record | Persisted semantic input | Vector column | Exact relationship |
|---|---|---|---|
| Angle | Canonical audience/tension/argument/take/mechanism/reader-decision signature derived from `content_body` | `content_angles.embedding vector(1536)` | `angle_id` → `angle_moments` → moments → original evidence |
| Chunk | Exact contextualized `chunk_text` | `transcript_chunks.embedding vector(1536)` | `transcript_id` FK and validated `passage_refs` into original text |

Baseline model: **`text-embedding-3-small` at 1,536 dimensions**. The dimension is OpenAI's documented default and matches the accepted DBML. Keep one active model/input-format contract in configuration. Equal dimension does not make different models compatible. [OpenAI embeddings guide](https://developers.openai.com/api/docs/guides/embeddings)

Angle `embedding_input_hash` binds the exact canonical semantic input. `content_hash` instead binds approval-relevant content and references; the two are not interchangeable. The existing signature builder excludes titles, scores, generation dates and review state. Dates influence freshness separately.

Chunk `content_hash` must identify contextual text and its original locations, avoiding false deduplication of identical words spoken in different places. Preserve already cited chunk rows and stable passage maps when changing chunking.

No embedding profile, representation registry, angle-vector side table or chunk-vector side table is introduced.

## 2. Write sequence and failures

1. Admit complete authorised originals, store their stable passage maps and freeze `pipeline_runs.input_refs`.
2. Call 1 produces validated moments with original evidence references. Vector preparation does not filter its input.
3. Call 2 produces validated angles and their `angle_moments` links. Retain all valid candidates, including ones later suppressed from UI.
4. Construct canonical signatures and prepare vectors. Only store a vector with its matching input hash.
5. Freeze historical eligibility/evaluation time, compute numerical overlap and current-batch comparisons, then persist the actual evaluated result.
6. Select visible candidates using the current unrounded scoring rule; Gate 1 still requires human review and CTA choice.

Provider failure leaves semantic evaluation unavailable. The DBML allows a null angle vector/input-hash pair and null scores. Do not manufacture a zero vector or zero-risk decision. Failed/pending chunk encoding must appear in later research coverage.

A database transaction should bind the saved angle, its supporting moment links and the evaluation state that actually exists. Encoding can occur asynchronously; the UI must distinguish “candidate saved” from “matching complete.” Persist real completion/error facts on the stage job.

## 3. Comparison population

For each evaluation:

- Freeze an evaluation timestamp and historical representative IDs/content hashes.
- Include eligible authorised prior completed generation results, including prior intentional generation runs within the same week.
- Exclude the current generation cohort and the candidate's own `supersedes_id` family/replayed copies.
- Resolve a single representative per logical angle family under a deterministic documented rule.
- Preserve original `first_generated_at` for edited copies/revival. Do not use import, updated or embedding time as generation age.
- Compare current-batch pairs separately, so insertion order cannot turn siblings into age-zero history.

If eligibility excludes a still incomplete run, state that coverage boundary explicitly. An embedding-missing eligible representative is a coverage failure, not an automatic exclusion that yields complete novelty.

Re-evaluating a reused angle for another run does not change its original generation lineage. Keep completed per-run reassessment in the corresponding job's `result_refs` instead of overwriting original `run_id`/generation time or pretending another generation occurred.

## 4. Exact cosine query

pgvector's cosine distance operator is `<=>`. Cosine similarity is `1 - distance`. Exact retrieval is the initial strategy for angle-history evaluation. [pgvector documentation](https://github.com/pgvector/pgvector)

The application supplies the frozen, authorised, family-resolved IDs. The following illustrates the vector operation, not a complete admission/security implementation:

```sql
SELECT angle_id,
       content_hash,
       first_generated_at,
       1 - (embedding <=> $1::vector) AS cosine_similarity
FROM content_angles
WHERE angle_id = ANY($2::text[])
  AND embedding IS NOT NULL;
-- No LIMIT: score every eligible representative.
```

Before treating this as complete, compare returned IDs with the frozen eligible set and verify compatible nonzero vectors. A null vector is filtered from the SQL operation but must still cause an explicit incomplete-coverage result. Future/missing generation times also require a data-quality disposition.

Freeze logical arguments and hashes against concurrent edits, or use preserved immutable representatives. The supplied input must still match `embedding_input_hash` at evaluation time.

## 5. Numerical rule and quality baseline

| Parameter | Starting value |
|---|---:|
| Historical cosine floor | 0.78 |
| Current-batch close-overlap flag | 0.90 |
| Recency half-life | 28 days |
| Maximum historical penalty fraction | 0.50 |
| Visibility gate | Unrounded adjusted score > 70 |
| Reviewer summary count | Proposed 5, expandable |
| Scoring top-k | All eligible qualifying history |

```text
overlap = clamp((cosine_similarity - 0.78) / 0.22, 0, 1)
recency = 2 ^ (-age_days / 28)
pair_risk = overlap * recency
historical_risk = max(pair_risk)
adjusted_score = base_score * (1 - 0.50 * historical_risk)

base_score = 20 * (
  0.35 * grounding + 0.25 * source_relevance +
  0.15 * audience_fit + 0.15 * specificity +
  0.10 * editorial_usefulness
)
# Quality dimensions are 0–5.
```

The exact floor has zero overlap; negative/below-floor similarities have zero overlap. Empty **complete** history yields zero risk. Incomplete history does not. Quality estimates and thresholds remain subject to corpus calibration.

| Base | Cosine | Age | Adjusted score |
|---:|---:|---:|---:|
| 90 | 0.95 | 7 days | 60.76 |
| 90 | 0.95 | 28 days | 72.61 |
| 90 | 0.95 | 84 days | 85.65 |
| 90 | 0.82 | 7 days | 83.12 |

This balances freshness and similarity at the pair-risk stage. A recent moderate overlap can outrank an old strong overlap. Do not rank by freshness alone, change vector contents based on age or reset an old argument's generation date.

Max risk avoids double-counting copies. It is deliberately different from summing risks across a populous archive. There is no fixed four-angle selection cap.

Current-batch close-overlap flags need an explicit editorial disposition (keep with stated difference, revise, merge or suppress). Until that decision is settled, a flag does not imply an automatic penalty or guarantee that every visible angle is distinct.

## 6. Reviewer top-k is separate from scoring

Calculate all eligible comparisons before choosing the initial five reviewer matches. Order that summary by `pair_risk`, then stable tie-breakers such as raw cosine and ID. Allow inspection of all qualifying comparisons.

Cosine-nearest-five can miss the maximum risk because it ignores age while selecting candidates. Increasing ANN top-k is not an exact guarantee for the current rule. An archive-scale optimisation must either preserve the result mathematically or undergo an explicit measured-recall/decision-impact acceptance.

The five-item display is a recommendation for the review UI, not a proven operating value or an extra schema field.

## 7. Actual result retained in JSON

`content_angles.matching_result` should capture:

- completion/coverage state, evaluation time and actual parameters;
- eligible representative IDs/hashes and any missing/invalid members;
- qualifying historical angle IDs, raw cosine, original generation age, normalized overlap, recency and pair risk;
- aggregate historical risk and scoring explanation;
- current-batch pair results and unresolved close-overlap flags.

Store qualifying scoring evidence rather than only five UI hits. If a compact frozen-set digest is used, it must resolve to the actual admitted references retained for that execution; a digest alone cannot explain which history was considered.

An unavailable comparison remains null/explicitly incomplete. Scores and selection must not masquerade as an approved final novelty decision. Publication/approval enrichment is SQL metadata for explanation, not an input silently inserted into this formula.

## 8. Editing and approval

Draft edits update the actual row. Changes to argument/evidence invalidate affected quality, matching and selection. Re-embedding is necessary when the canonical signature changes; otherwise preserve a verified matching vector/input hash and still recompute the relevant evaluation/approval hashes.

After approval or downstream consumption, preserve the saved argument and create a replacement via `supersedes_id`. Keep original generation age for the same family. `supersedes_id` means an edited version of the same item, not merely a semantically similar new argument.

Gate 1 binds the current approval-relevant hash, selected CTA, authenticated actor and time. Brief jobs verify that authority and pin `angle_input_hash`. Selecting a visible angle is not itself an approval.

## 9. Index and rollout boundary

Enable pgvector in a later migration. Start angle evaluation with an exact scan over eligible representatives. Transcript search can start exact and gain a cosine HNSW index after workload/filtered-recall measurement. Full-text expression GIN and reverse relationship indexes do not require new tables.

Changing the active embedding contract must pause retrieval or invalidate/rebuild the affected corpus before serving. A rolling mixture of models is incompatible with this compact single-contract design.

The current testing implementation already supplies several baseline defaults and the signature builder. Its missing-vector/future-date behavior and aggregate `max_similarity` naming do not fully express this approved completeness contract. This document does not change that code or certify the defaults' accuracy.

Brief retrieval has its own hybrid candidate budgets and fuzzy alignment rules; those must not be confused with angle-history scoring. See [brief provenance and matching](briefing-provenance-and-prior-content-context.md).

