# Content Atelier — pgvector data and pipeline review

Reviewed: 8 October 2026 (Asia/Calcutta).

**Historical architecture audit.** The user approved the compact 13-table design on 9 October 2026. The current [schema/pipeline map](../data-storage-schema.md), [storage and retrieval contract](../content_atelier_vectordb.md), and [complete DBML](../content-atelier-compact.dbml) supersede expanded storage recommendations and section references below. This audit is retained as a record of the earlier document review; its broader inventory is not the approved table list.

Purpose: establish what data and pipeline stages depend on vector storage before reviewing its implementation. This is a repository/document audit. It does not change generation prompts, connect embeddings, start a database or replace the separate generation-testing work.

Subsequent user clarification, 8 October 2026: the active vector scope is **generated angles and transcript chunks only**. The broader inventory in this audit explains earlier architecture, not a requirement to embed the other categories. All other data is ordinary PostgreSQL data. See [current two-target reasoning](pgvector-two-target-storage-design.md).

## 1. What the system is intended to store

The intended deployment uses **one PostgreSQL database with pgvector**. Reviewing “the vector database” first means reviewing semantic representations, retrieval and their links to authoritative records; relational storage is part of the same eventual database.

The architecture separates three knowledge concerns:

1. **Evidence:** what was said, by whom, when, in which source, with what qualifications.
2. **Content memory:** what was proposed, reviewed, produced and actually published.
3. **Editorial policy:** applicable voice, strategy, offer, CTA and format rules.

Evidence and content memory have semantic search uses. Active policy is loaded deterministically; essential rules must not depend on whether similarity search retrieves them. Generated angles are content memory, not independent factual evidence.

During current experimentation, validated JSON artifacts are authoritative and pgvector is intended as a rebuildable projection. The eventual production architecture makes PostgreSQL authoritative and keeps original files in private object storage. These are different implementation phases, not two competing production databases.

## 2. Documents that establish the design

| Source | What it establishes | How to interpret it |
|---|---|---|
| [Original solution architecture](<C:/Users/Jainil Trivedi/Downloads/Content-Atelier-Solution-Architecture.md>) §§2–4, 7, 10 | Infrastructure, three knowledge tiers, segments/moments/topics/memory, shared hybrid retrieval, later research and publication | Broad original proposal; later requirements override conflicting defaults |
| [Storage design](../content_atelier_vectordb.md) §§1–13 | Expanded data inventory, revisions, authority, claims, representations and retrieval boundaries | Design specification, not proof of an implemented schema |
| [Transcript-to-angle specification](../transcript_to_content-angle.md) §§3, 7–10 | Current first-slice ordering, every valid angle retained, one vector per angle, numerical overlap and recency | Governs current slice where older architecture differs |
| [Week-by-week testing design](../content_atelier_week_by_week_testing.md) §§8–12 | Durable service artifacts, exact reuse, JSON-to-pgvector projection and historical experiments | Some controls remain proposed rather than implemented |
| [Reconciled architecture review](architecture-comparison-and-reconciled-design.md) §§5–9 | Source revisions, scoped claims, evidence permissions and downstream contracts | Proposed broader refinements |
| [Backend README](../backend/README.md), [runtime package](../backend/backend_pipeline/pipeline.py) | Actual executable behavior and current generation-only boundaries | Code determines what currently runs; testing evolves in another chat |

There are stale passages within otherwise useful documents. Storage-design §14 still says “four-angle selection” and requires memory before drafting; its §1 amendments and §7.3, plus the active slice specification, supersede those statements. The original architecture's extra similarity LLM judge and fixed 3–5 selection target also do not govern this slice. The current baseline has no third similarity judge, no fixed four-angle cap, and optional future pre-generation memory retrieval.

## 3. Data inventory connected to pgvector

“Planned” below means a documented responsibility when that stage is built, not a requirement to embed everything before the first angle test.

| Data | Semantic representation | Who uses it | Current implementation |
|---|---|---|---|
| Raw meetings/source documents | Source identity and whole file are metadata/provenance; searchable chunks are embedded separately | Ingestion, citation reconstruction, evidence verification | Local transcript revisions and lossless weekly packets; no whole-document vector |
| Transcript segments | Context header plus normalized conversational chunk; original wording remains available | Archive search, historical corroboration, objections, founder explanations, research dossiers | Timestamped speaker spans exist; planned grouped search chunks/full-text/vector index are absent |
| Slack threads and image-derived text | Parent/reply context or eligible OCR/description linked to the attachment | Same evidence-search functions | Broader design only; current ingestion is transcripts |
| Key moments | Moment type, scoped summary/title and supporting quote | Reusable insight discovery, recurrence and historical research | Structured moments and source-span links saved in JSON; no moment embeddings |
| Canonical topics | Name, description and reviewed aliases | Find related discussions over months; nominate topic assignments; expand research | Registry/topic vectors not implemented |
| Every valid generated angle, including suppressed candidates | One canonical argument signature | Historical novelty/recency and current-set overlap review | Signature builder, optional embedding provider/cache, JSON vector persistence and historical scoring exist; embeddings default to disconnected |
| Prior published emails, captions, carousels, scripts or transcripts | Published key message with useful context; sections where needed | Audience-facing repetition checks and prior-coverage research | Corpus files exist, but no implemented published-memory import/index |
| Briefs and generated assets | Brief message spine or asset's substantive message | Recall existing work; avoid producing the same argument across packs | Later-stage design only |
| Reviewed positive exemplars | Suitable excerpt with format, audience and editorial purpose | Help later writers choose an appropriate execution | Optional semantic target; not a current indexed collection |
| Reviewed corrections/negative examples | Labeled before/after case and scope | Review and correction recall | Optional later target, separate from positive exemplars |
| Scoped claims | Proposition including subject, period, units, attribution and qualifiers | Retrieve permitted factual claims | Separate claim ledger proposed; current moments/angles carry some qualifications. Claim vectors optional |
| External findings | Dated, cited public finding | Later research/reuse | Optional separate target; not current ingestion |
| Active brand/offer/CTA/format policy | Exact active version selected by stage/format | Extraction, generation and validation | Prompt policy files exist; vector retrieval is not needed to enforce them |

Logical targets may share a retrieval service, but must preserve evidence, generated-memory, published-memory and exemplar identities. A match in one must not silently substitute for another.

## 4. Pipeline stages: vector reads and writes

| Stage | Vector relationship | Data that must travel with the vector |
|---|---|---|
| Source ingestion and preparation | Produces the material for evidence representations; does not require similarity search to admit a source | Source/event identity, exact revision/hash, dates, speakers, raw-file reference, inclusion/access |
| Segment indexing | Writes segment vectors and full-text representations | Chunk boundaries, source offsets/timestamps, context header, parser/segmenter versions |
| Moment extraction | Reviews all admitted weekly source context; saves moments. Later moment indexing writes moment vectors | Anchors, contiguous context, exact quote, qualifications and verification dimensions |
| Topic linking | Searches compatible topic vectors and maintains topic links | Stable topic identity, assignment confidence and reviewed merge/status history |
| Weekly candidate generation | Current baseline generates from the week's moments and actual context. Historical evidence retrieval and bounded prior-coverage summaries are broader/optional additions | Exact moment/source dependencies and active policy |
| Angle embedding | Writes/reuses one vector for each valid angle signature, after saving candidates | Angle identity, original generation event, exact signature/hash, profile and artifact reference |
| Historical overlap/recency | Reads eligible prior angle vectors; compares exact numerical similarity and applies generation-age adjustment | Historical IDs, original generation timestamps, compatible profile, snapshot and rule configuration |
| Current-set overlap | Compares siblings as a set, separate from historical age penalties | Pair IDs, raw similarities and explicit close-pair disposition; policy remains unresolved |
| Gate 1 decisions | Decisions change memory eligibility/reservations; approval itself is an exact state transition | Exact angle revision, actor/action/reason/date |
| Research dossier after approval | Searches segments/moments/topics and prior content; expands neighboring context | Citations, source revisions, filters, ordered hits/scores, qualifying/counterevidence and gaps |
| Brief and asset creation | Reads dossier, applicable policy and reviewed examples; optionally writes message-memory vectors | Exact brief/asset revisions, claims, locks and dependencies |
| Publication recording | Writes/updates published-message memory | Actual channel/date/wording and publication evidence; approval is a separate event |
| Rebuild/profile migration | Reprojects saved compatible vectors, or creates a new representation for changed text/profile | Readiness, active profile, coverage and old-run provenance |

Historical research has several distinct questions: “find another client describing this problem,” “find the original qualifying passage,” “how does Whitney explain it?”, and “have we already used this argument?” They need different targets and filters even when all use the same database.

## 5. Actual current code path

The full vector-enabled path in [pipeline.py](../backend/backend_pipeline/pipeline.py) is:

```text
Discover week's transcript files
  → save source revisions and weekly snapshot
  → Call 1: extract and validate moments
  → save moments.json
  → Call 2: generate and validate angles using moments + source context
  → save candidates.json before embedding/filtering
  → build/reuse canonical signature embeddings
  → save embedding artifacts and per-angle vector references
  → load prior angles.json from completed compatible runs
  → Python cosine comparison + generation-recency adjustment
  → save angles.json and review.json
```

With embeddings disabled, execution stops after saving candidates and a generation-only review. Similarity, recency adjustment and visibility are explicitly not run. Failed extraction and explicitly partial diagnostics do not become completed vector history.

Specific implementation facts:

- Call 2 currently receives an empty history argument: `angle_prompt(self._moment_packet(...), [])`. It does not retrieve history from pgvector before drafting.
- [contracts.py](../backend/backend_pipeline/contracts.py) builds the embedding input from **audience, tension, argument, take, mechanism and reader decision**. Title, quality scores and recency are excluded. The code does not currently add a separately structured proof/case field to the signature.
- Embedding reuse identifies the exact request, including signature text, endpoint, model and dimensions, in separate fake/live namespaces. A new angle ID with identical compatible signature text can reuse vector values.
- [_load_history](../backend/backend_pipeline/pipeline.py) reads files under `experiments/**/angles.json`, deduplicates angle IDs and excludes non-completed runs, later week indices, incompatible model/dimension profile labels and fake/live mismatches.
- [scoring.py](../backend/backend_pipeline/scoring.py) performs cosine calculations in Python. There is no pgvector SELECT/search in the running pipeline.
- [db.py](../backend/backend_pipeline/db.py) contains an independently callable projection helper. No production caller, connection lifecycle or CLI projection command currently wires it into pipeline execution.
- The projection table is `angle_vectors(angle_id, run_id, embedding_profile, signature_hash, generated_at, eligible, embedding vector(1536))`. Its only additional index is on `run_id`.
- Compose declares a pgvector/Postgres service and persistent volume. A service definition and a projection helper do not establish a deployed or integrated retrieval system.

At the metadata inspection in this review, saved run embedding directories contained no vector files and the inspected `service_calls` store contained no embedding artifact records. This is a point-in-time observation of the default testing datastore; other generation work can continue changing it. No database service status was checked and no credentials were read.

## 6. Storage and replay dependencies

Current vector recovery depends on these files in `content_atelier/testing/.data/`:

| Artifact | Responsibility |
|---|---|
| `sources/...`, `weekly_packets/...`, `cycles/.../snapshots/...` | Source bytes/representations, source revisions, reference mapping and weekly provenance |
| `service_calls/<fingerprint>/attempts/<artifact-id>/...` | Exact request, raw response, parsed/validated output, error/usage and original creation time |
| `cache/artifacts/<fingerprint>.json` | Pointer to a validated checksummed reusable artifact |
| `experiments/default/runs/<run-id>/candidates.json` | Valid angles retained before vector or scoring failure |
| `.../embeddings/<angle-id>.json` | Vector values, model/dimensions, fingerprint and original service artifact reference |
| `.../angles.json` | Vector-bearing angle records and scoring output for completed history |
| `.../manifest.json`, `review.json`, `reuse/...` | Run lifecycle, readiness/reporting and preserved original lineage |

Rebuilding pgvector from existing compatible vectors should require local projection, not another embedding request. A changed signature or embedding space can require new inference; changing a score threshold should only require rescoring. Replaying an angle must preserve its original generation date rather than making old suggestions appear newly generated.

For general evidence search, a new textual query normally needs a compatible query embedding or exact reuse of a cached one. Angle-to-angle checks already have a candidate vector and need no separate query-embedding call. This distinction affects caching and cost design.

## 7. Gaps to address in the vector-storage review

These are findings from code inspection, not changes made in this chat:

1. **pgvector integration is absent.** Projection, connection management, vector reads, eligibility filters and reconciliation/rebuild need an explicit path before pgvector becomes the working search mechanism.
2. **Projection provenance is incomplete.** `Angle` records do not supply `embedding_profile` or `signature_hash`; the helper defaults them to Small/1536 and an empty string. Another 1,536-dimensional model could therefore be mislabeled. It skips missing/wrong-sized vectors silently, and does not propagate `eligible` on insert/update or remove stale rows.
3. **Search-history identity is weaker than cache identity.** Manifests use model + dimensions; embedding cache keys also include endpoint and exact input. History needs an explicit compatible profile/projection contract. Equal dimensions alone do not establish compatibility.
4. **History is not frozen or branch-isolated.** `_load_history` scans all experiment subdirectories; there is no recorded fixed prior-history ID set or branch restriction. Week-index filtering is not a simulated editorial cutoff. Ranking uses the actual current clock.
5. **Match evidence is insufficiently recorded.** Scoring retains an aggregate but not matched historical IDs/raw cosine/age/contribution rows. The field named `max_similarity` currently contains maximum overlap-times-recency risk, not raw cosine similarity. These must be distinct values for review.
6. **Current-set semantic comparison is absent.** Exact duplicate signatures are rejected during parsing, but siblings are not numerically compared. The configured close threshold is not consumed by ranking. Its selection policy still needs resolution.
7. **Broader search targets remain designs.** Source/moment/topic embeddings, full-text/hybrid search, published memory, dossier retrieval and optional examples are not implemented by the angle projection.

The existing projection test uses a recording connection to inspect emitted SQL and vector parameters. It does not test a real PostgreSQL connection, vector adaptation, transaction recovery or cosine query. No live integration or model test was run for this audit.

## 8. Boundary for the later SQL review

We can review vector storage first while identifying the exact relational dependencies it needs: source and angle revisions, profile identity, run/history snapshots, timestamps, eligibility, status, decision and publication records, and dependency links.

The vector layer finds relevant meaning. The accompanying records explain what the hit is, whether it is usable, when it originated, and whether it was merely proposed or actually published. A useful storage contract preserves both.

The next concrete design step is to settle each active vector target's authoritative entity/revision, canonical text, compatible profile, eligibility/readiness, read/write stage and rebuild procedure. That provides a reviewable pgvector contract before extending the full relational schema.
