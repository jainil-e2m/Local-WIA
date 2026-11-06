# Content Atelier — two vector targets and SQL content lineage

Updated 9 October 2026 · [Approved 13-table DBML](../content-atelier-compact.dbml) · [Full storage/retrieval reasoning](../content_atelier_vectordb.md)

The accepted design stores only **angle signatures and transcript chunks as vectors**. This document replaces the earlier recommendation for separate vector/profile/revision tables. All records are in one PostgreSQL database; the vectors are columns on their corresponding content rows.

## 1. The two targets

| Target | Stored representation | Main consumers | Original authority |
|---|---|---|---|
| `content_angles.embedding` | Audience, tension, argument, take, mechanism and reader decision | Historical novelty evaluation; related prior coverage during brief research | Saved argument, `angle_moments` and original supporting moment evidence |
| `transcript_chunks.embedding` | Contextualized coherent source passage | Supplemental briefing support/counterevidence | `transcripts.original_text` through stable passage references |

Both approved columns use `vector(1536)`. The baseline embedding contract is `text-embedding-3-small`, configured outside the database. No topic, moment, brief, memory or asset vector is part of the approved scope.

Angle and chunk vectors solve different questions. Angle matching asks whether an argument repeats earlier coverage. Chunk retrieval asks which original passages are useful for researching this approved argument. An angle similarity hit cannot verify a source claim.

## 2. Stage-by-stage reasoning

| Phase | Vector involvement | SQL/JSON data supplied or saved |
|---|---|---|
| Source admission | Prepare chunk encoding for later research | Originals, source links, stable passage maps, use restrictions and frozen run inputs |
| Call 1: moments | None; read complete admitted originals | Validated moments with exact anchors, context and qualifications |
| Call 2: angles | Prepare canonical signature after generation | Every valid candidate and supporting moment relationships |
| Historical overlap | Exact cosine comparison across eligible historical representatives | Actual comparison facts, original age, freshness-weighted risk and score/visibility |
| Current-batch overlap | Separate pairwise angle comparison | Flags and unresolved editorial disposition |
| Gate 1 | Explain/re-evaluate affected matching after edits | Actual argument, chosen CTA and hash-bound human decision |
| Brief research | Hybrid chunk search and independent prior-angle search | Exact original grounding, graded supplemental proof, relevant prior use and known gaps |
| Brief draft / Gate 2 | Consume selected research; no brief vector | Brief contract, evidence/context fields, questions/answers and hash-bound approval |
| Assets / Gate 3 | Routine production uses approved brief; no fresh open-ended search | Actual assigned copy, brief/hash references, checks and exact pack manifest |
| Scheduling / publication | No immediate vector operation | Exact asset/hash and actual distribution facts for future coverage context |

All valid generated arguments are retained, even when suppressed from the UI, because future matching is against generated coverage rather than only published coverage. Originals and qualifications are retained because similarity alone cannot reconstruct them.

## 3. Minimal relationships carry the rest

```text
week -> original transcripts -> chunks with passage_refs
run -> key moments with evidence_refs
angle -> angle_moments -> key moments -> original passages
approved angle/hash -> brief + selected evidence + prior context
approved brief/hash -> assigned assets -> owning pack and manifest
exact approved asset/hash -> calendar and confirmed publication
```

The angle-to-moment relationship is a SQL join table. Evidence and prior-context details use validated JSON rather than separate provenance tables. Validate every reference and preserve cited originals; JSON is not automatic foreign-key enforcement.

Reverse a retrieved original passage into moments whose actual evidence ranges overlap it, then follow `angle_moments` into past angles, briefs, assets and calendar facts. Do not attach all moments in the same meeting. Search old angle signatures independently as well: past related arguments may use other transcripts.

Store the selected compact result in `content_briefs.selected_evidence/prior_content_context/research_gaps`. No permanent retrieval-session/context table is required. Prepared research can be transient or a compact job checkpoint until a valid brief draft is saved.

## 4. Matching policies remain separate

Angle-history scoring combines normalized cosine overlap with recency measured from original generation time. Its initial exact scan has no fixed scoring top-k; a proposed five-item reviewer summary is a display budget. Current-batch pairs are independent of historical age penalties.

Brief research combines semantic passages with full-text results using rank fusion, then resolves and grades original evidence. Trigram spelling lookup and quote-string alignment help locate text. They do not replace semantic retrieval or authorise unsupported claims.

The original solution architecture's extra LLM angle judge is superseded by the numerical two-call angle setup. Optional passage reranking is a separate later briefing operation.

Detailed rules and starting values: [angle matching](pgvector-creation-and-angle-matching-spec.md), [briefing provenance and fuzzy matching](briefing-provenance-and-prior-content-context.md).

## 5. Configuration and tracking need no extra registries

Model/provider settings, prompt versions, editorial policies and display timezone stay in configuration. Source provenance and actual decision parameters remain with the content/run that consumed them because they explain actual inputs and results.

The compact tracking layer is `pipeline_runs` for actual execution scope/frozen inputs, `pipeline_jobs` for stage/target/live processing/retry state, and `pipeline_events` for meaningful history. Existing authentication supplies actor identity.

This is the approved design, not proof of an implemented database. Missing/incompatible vectors, incomplete history, unresolved prior coverage and unmeasurable progress remain visible rather than converted into low-risk/completed results.

