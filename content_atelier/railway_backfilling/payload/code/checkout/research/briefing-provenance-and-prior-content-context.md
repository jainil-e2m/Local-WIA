# Briefing — provenance, hybrid retrieval and prior-content context

Updated 9 October 2026 · Approved 13-table design · [DBML](../content-atelier-compact.dbml) · [Storage rationale](../content_atelier_vectordb.md)

This reconciles the earlier provenance/context-table proposal with the compact schema. The required information remains, but it uses existing content rows, SQL relationships and validated JSON fields. There is no separate evidence-packet, retrieval-session, source-span, topic-vector or revision table.

## 1. The brief's input contract

A brief starts from an approved `content_angles` record with its actual CTA, linked moments and current hash. The job pins that input. The saved brief uses `angle_id` and `angle_input_hash`.

The writer needs three types of context:

1. **Original grounding:** what supports the chosen angle, its conditions, speaker attribution and uncertainty.
2. **Supplemental research:** relevant additional evidence, counterexamples, unanswered questions and authoritative external framing when allowed.
3. **Prior coverage:** what related arguments were previously generated/used/published and how the proposed brief will differ.

These are different roles. A prior generated argument is useful editorial context, not independent factual evidence. A supplemental search hit is a candidate, not an approved claim.

## 2. Original grounding is a deterministic join

```text
content_angles.angle_id
  -> angle_moments.angle_id / moment_id          [SQL foreign keys]
  -> key_moments.evidence_refs                  [validated JSON]
  -> transcripts.transcript_id / passage_map    [original locations]
  -> transcripts.original_text                 [evidence authority]
```

Supply the chosen angle's evidence even if it would not rank in supplemental top-k. Resolve all required anchor/context/qualification references, including multiple transcripts used by a moment. Restore neighboring statements when a short excerpt changes the apparent claim.

Validate referenced transcript existence, passage/range ownership, speaker uncertainty and permitted use. A foreign key from angle to moment does not validate JSON passage references automatically.

Do not infer that a meeting's title/client metadata verifies every speaker or result. Preserve what is known and mark uncertainty. Brief claims must stay within the supported scope.

## 3. Supplemental search uses meaning and terms

The original [solution architecture](<C:/Users/Jainil Trivedi/Downloads/Content-Atelier-Solution-Architecture.md>) §§3.4–3.6 describes semantic passage retrieval, lexical search and RRF. Map its broader vector inventory to the two approved columns:

| Operation | Approved storage/access path | Purpose |
|---|---|---|
| Semantic passage search | `transcript_chunks.embedding` | Relevant phrasing and conceptual support beyond exact words |
| Keyword search | Full-text expression index over `transcript_chunks.chunk_text` | Names, terms, mechanisms and numeric concepts |
| Name/spelling lookup | Optional `pg_trgm` index/function on actual needed text | Candidate spelling/label resolution |
| Original context expansion | `passage_refs` → `transcripts.passage_map/original_text` | Exact attribution, quotations and qualifications |
| Related moment lookup | Passage overlap against `key_moments.evidence_refs` | Original claim/context lineage |
| Prior argument lookup | `content_angles.embedding` | Similar past editorial coverage |
| Prior use/publication | SQL joins through briefs/assets/calendar | Actual saved copy and known distribution state |

Generate query intents for the approved argument, mechanism, reader decision, missing support and counterevidence. Apply the same allowed source/date/use filters to all candidate lists before fusion; recheck access when resolving originals.

Starting research budgets from the architecture are 6–10 targeted queries, top 50 semantic and top 50 lexical candidates per query, optional reranking of roughly 50 fused candidates, and at most two gap-filling rounds. About 12 total queries and 40 graded evidence items are starting bounded budgets. They are tuning proposals, not schema limits or a novelty-scoring cap.

PostgreSQL's `websearch_to_tsquery` supports search-like queries; language configuration must fit the corpus. An expression GIN over `to_tsvector('english', chunk_text)` supports the initial English design without another stored column. [PostgreSQL query controls](https://www.postgresql.org/docs/current/textsearch-controls.html), [index documentation](https://www.postgresql.org/docs/current/textsearch-indexes.html)

Use rank fusion because raw cosine and lexical scores have different scales:

```text
RRF_score(d) = sum(1 / (60 + rank(d, list)))
# Ranks start at 1; a missing item contributes zero.
```

The original starting constant is 60. See the primary [RRF paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf). Fusion prioritizes inspection; it is not a factual confidence score.

Optionally rerank passages when a representative evaluation shows improvement. Restore original context and grade support/limits afterward. Optional brief passage reranking must not be confused with the superseded third LLM judge for angle similarity.

## 4. What “fuzzy matching” means here

There is no general fuzzy-logic inference engine in the accepted design. Three mechanisms complement each other:

- Embedding cosine finds meaning-based relevance.
- Full-text and trigram matching locate words, concepts and approximate name spellings.
- Quote-string alignment helps locate an original span near an expected position.

`pg_trgm` uses trigrams for string similarity and search. A similar person/company label only nominates a potential identity; confirm with actual source facts. [PostgreSQL pg_trgm](https://www.postgresql.org/docs/current/pgtrgm.html)

The original architecture §4.3 proposes normalized fuzzy quotation alignment in a ±90-second window at 0.90 similarity. Its algorithm/normalization are not fully specified. Later strict quotation checks in the current generation testing take precedence and are unchanged by this document.

A fuzzy alignment is useful for locating a span despite formatting changes. It cannot authorise an altered number, negation, qualification or speaker. A quotation must still satisfy the current original-wording policy. A paraphrase needs evidence/claim validation rather than quotation-style permission.

Before implementation, define the exact scorer and normalization rules. String similarity 0.90 is not cosine similarity 0.90. Different scorers can behave differently, particularly with extra/missing words. [RapidFuzz scorer definitions](https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html)

## 5. Preserve prior coverage through two discovery routes

### A. Reverse passage lineage

```text
retrieved transcript_chunks.passage_refs
  -> original transcript/passage/ranges
  -> key_moments.evidence_refs with actual overlap
  -> angle_moments
  -> previous content_angles
  -> content_briefs
  -> content_assets
  -> calendar_entries
```

The relevant relationship is actual evidence overlap, not “same transcript.” A meeting may contain many unrelated moments. A chunk may span several passages; a moment may use qualification outside that chunk. Resolve the moment's full referenced context before summarizing prior use.

Narrow by retrieved transcripts/passages, then validate JSON overlap. A reverse B-tree on `angle_moments(moment_id)` and workload-driven JSON/FK indexes can make this efficient without adding a topic/moment vector.

### B. Independent prior-angle semantic search

Search prior angle signatures using the approved argument/mechanism. Enrich returned IDs through SQL into actual previous briefs/assets and known publication records. This catches related arguments built from other transcripts.

Use relevant authorised history. Collapse duplicate angle families and overlapping evidence before compaction. Unlike the novelty penalty, this research route should also inspect the chosen angle's own earlier use via exact SQL, so a family self-exclusion cannot hide repeated publication.

A brief context budget may show only selected relevant prior items, but material omitted/unknown coverage must be recorded. The angle-history scoring scan remains uncapped and separate.

## 6. The compact packet saved with the brief

| Field | Required meaning |
|---|---|
| `content_body` | Generated/edited brief contract: audience, insight, narrative, scoped claims, CTA, exclusions, questions/answers and asset instructions |
| `selected_evidence` | Exact transcript/passage/ranges, optional discovery chunk IDs, evidence role, compact excerpt/summary, conditions and attribution; external framing labelled with URL/type |
| `prior_content_context` | Relevant previous argument/use, actual angle/brief/asset IDs when internal, known publication state/time, and intended difference |
| `research_gaps` | Unanswered questions, conflicts, inaccessible history, missing embeddings and material budget omissions |
| `angle_input_hash` | The approved angle/CTA/evidence-selection contract actually supplied |

Illustrative shapes below describe JSON semantics, not extra DBML columns. Keys are proposed application contracts and require validation; sample IDs are placeholders:

```json
{
  "selected_evidence": [
    {
      "evidence_id": "ev_1",
      "transcript_id": "tr_example",
      "passage_refs": [{"passage_id": "p_12", "char_start": 1200, "char_end": 1450}],
      "discovery_chunk_id": "chunk_example",
      "role": "support",
      "summary": "Observed outcome under the stated operating conditions.",
      "qualifications": ["Limited to the described team and observation period."]
    }
  ],
  "prior_content_context": [
    {
      "angle_id": "angle_previous",
      "brief_id": "brief_previous",
      "asset_id": "asset_previous",
      "publication": {"state": "scheduled"},
      "prior_argument": "Earlier coverage framed the operational bottleneck.",
      "intended_difference": "This brief explains the decision mechanism and its limits."
    }
  ],
  "research_gaps": {
    "coverage_complete": false,
    "items": ["A relevant legacy publication could not be inspected."]
  }
}
```

Define character ranges consistently against each original text; the example uses transcript-global half-open offsets. Never present summaries as exact quotation. Conditions/uncertainty remain with evidence, not only in a removable general footnote.

Calendar state derives from actual records; “published” requires confirmation time. Generated, approved and scheduled content are distinct prior-use states. If externally edited publication wording has not been verified, label that limitation.

## 7. Context compaction must preserve relevant differences

Reserve context budget in this order:

1. Chosen-angle original grounding and essential conditions.
2. Material counterevidence or conflicting attribution.
3. Strongly related prior arguments and actual uses.
4. Selected supplemental support/external framing.
5. Explicit residual gaps and material omissions.

This is a starting priority policy, not a claim that every brief has the same token budget. Deduplicate overlapping passages and repeated family summaries before trimming. Keep evidence references so reviewers can reopen originals.

Prior-context compaction should state what was covered, who it addressed, how it framed the argument, what is known about use/publication, and the proposed new contribution. “Similar content exists” is too vague to help the writer choose a distinct treatment.

Old generated copy cannot verify a source result. Preserve references back to original proof, and separate prior editorial inference from direct source assertions.

## 8. Prepare, draft, review and reuse

A research job starts with a valid approved angle/hash. It resolves the packet before invoking the brief writer. Because `content_briefs.content_body` is required, do not create an empty fake brief for research tracking.

Prepare transiently, or checkpoint compact selected references/summaries in `pipeline_jobs.result_refs` when restartability requires it. `input_hash` pins the actual supplied inputs. Save a valid draft together with selected evidence/prior context/gaps. A checkpoint is not a second full transcript/retrieval dump.

Gate 2 reviews the exact draft/evidence/CTA contract and binds its hash to actor/time. Material edits to claims or evidence return to research and review. After approval or downstream consumption, preserve the saved record and create a `supersedes_id` replacement.

Assets consume the current approved brief/hash and its evidence contract. Routine email/carousel/reel generation does not need another open-ended vector search. A requested new factual claim returns to the brief workflow rather than silently extending the approved contract.

## 9. Limits of the thirteen-table scope

Internally produced assets have real brief lineage. A global catalogue of legacy external publications is not defined here. Authorised legacy examples can be supplied as labelled URL/excerpt prior context, with incomplete archive coverage recorded. Do not create fictitious moments/angles/briefs to populate internal foreign keys.

Source use restrictions, JSON reference validation, stable original passage maps, completeness flags and hash-bound dependencies require implementation. Nullable vectors and empty arrays cannot stand in for completed research.

This document updates the approved design only. It does not certify retrieval quality, execute a migration or change strict quotation validation in the separate testing chat.

