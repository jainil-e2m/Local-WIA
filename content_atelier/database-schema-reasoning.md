# Content Atelier — storage decisions and full-flow schema

<!-- governing-plan-note -->
> **Historical (marked 18 October 2026, plan item S.B9).** This document is kept for traceability. The one governing plan is [the implementation plan](backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md) (revision 6.1 or later); where they differ, the plan wins. Do not plan from this document.

**Superseded expanded proposal.** The current schema is the [13-table compact DBML](content-atelier-compact.dbml), explained in [compact storage decisions](database-schema-compact.md). This document retains the earlier broader design for reference.

Design proposal · 9 October 2026

[Complete pasteable DBML](content-atelier.dbml) · [Execution/data flow](data-flow.html) · [Simplified relationship diagrams](data-storage-schema.md)

## 1. Recommendation and scope

Use **one PostgreSQL database with pgvector**, with exactly two permanent vector columns: angle signature embeddings and transcript-chunk embeddings. Keep evidence, relationships, editorial copy, decisions, operational state and UI persistence in SQL.

The schema should answer six concrete questions:

1. What original evidence produced this moment and argument?
2. What inputs, settings and historical ideas were actually used in this run?
3. What did the human approve, at which exact revision, with what CTA and steer?
4. What evidence and prior coverage did the brief writer actually receive?
5. Which approved brief governs each asset, and which exact asset versions form the approved pack?
6. What is merely generated, approved or scheduled, and what was actually published?

These questions determine storage. A field does not earn a permanent place because it appeared in a prototype TypeScript interface or a provider response.

This is a complete **proposed schema**, not a live migration. The current backend remains file-backed, with a separate angle-vector projection helper. Nothing here enables model calls, changes prompts, deploys a database, or changes another chat's testing. Build and populate only the tables consumed by each implemented phase.

### DBML versus Mermaid

dbdiagram.io uses DBML for table/column/key diagrams. Paste the entire contents of `content-atelier.dbml` into its editor. Mermaid is suitable for execution diagrams but is a different language. The DBML includes table groups, actual columns, nullable references, composite keys and selected check constraints. Its custom `vector(1536)` column types are deliberate. [DBML syntax](https://dbml.dbdiagram.io/docs/)

## 2. What this review changed

The earlier Markdown was a logical relationship sketch. The DBML adds the responsibilities that actual pipeline and UI behavior require:

- Live weekly bucket membership is separate from a run's frozen source-revision manifest.
- A moment can cite **multiple source revisions**. Current `Moment.source_ids` and the weekly extractor support this; a mandatory single transcript FK would lose valid provenance.
- Logical angles, briefs, assets and packs have stable identities, while generated/edited content and approvals bind immutable revisions.
- Every pack has a normalized assignment plan and an exact asset-revision manifest. A JSON allocation alone cannot enforce governing-brief relationships.
- Individual schedules are persistent planning records. A scheduled date does not establish publication.
- Scoped factual claims and permission facts are explicit. A verified quotation is not automatically a verified result, causal claim or public-use permission.
- Source synchronization uses the same durable work/attempt mechanism as generation; no parallel ingestion-job store is introduced.

The current frontend prototype also has a four-concept capacity, per-idea packs, legacy score dimensions, mock metrics and local-storage simulation. Those are **not automatically adopted as database rules**. Earlier user decisions favor threshold-based angle selection without a fixed four-angle cap. `pack_slots` can represent either deliberate per-angle packs or a weekly allocation across approved briefs; the schema does not silently choose or generate both. Production allocation/capacity remains an explicit product policy.

## 3. The storage test

| Category | Keep? | Reason |
|---|---|---|
| Irreplaceable source facts | Yes | Original input, known metadata, actual permission and publication facts |
| Generated or human-edited editorial work | Yes | Pipeline handoff, review, history, version comparison and reuse |
| Relationship and membership records | Yes | Exact source lineage, weekly snapshots, approved input sets and manifests |
| Decisions and their effective inputs | Yes | Resume the UI, explain selection, preserve exact approval and detect stale dependencies |
| Search projections | Yes, narrowly | Two vector targets plus generated text-search indexes; rebuildable from SQL records |
| Deterministic display values | Derive | Counts, days ago, dates/day labels, pending gates, usage counts and current phase |
| Provider/cache payloads | Conditional | Only compatible reuse, coverage, repair or actionable failure consumers justify retention |
| Hypothetical future integrations/metrics | Defer | No permanent records until the feature has a real writer and reader |

**A small database is not necessarily a database with very few tables.** Hiding source IDs, approval targets and pack membership inside one giant JSON document saves table names while losing integrity. This full-flow proposal has 51 tables in eight groups. Fifteen are link or membership tables. Others include narrow identity/version/operational records, not 51 independent copies of content. Each is tied to a consumer below.

## 4. Every table and why it exists

### A. Sources and transcript retrieval

| Table | Data retained | Pipeline/UI consumer and why it cannot simply be omitted |
|---|---|---|
| `clients` | Existing external client reference, display name, business type | Client filters and consent scope. Only a lightweight identity reference; the Atelier does not become a CRM. Unknown identity remains unknown. |
| `source_connections` | Enabled provider, known allowed scope and last committed checkpoint | Configured source ingestion, resume, Sources/health view. Secrets stay in the existing server secret configuration. Latest success/error is derived from attempts. |
| `sources` | Stable upstream identity, type/purpose, client, known title/date/link, confirmed duplicate/thread relationships, availability/withdrawal state | Bucket, source detail, filters, deduplication and eligibility. Keep occurred time separate from when the app observed the source. |
| `source_revisions` | Exact original payload bytes, used known metadata, input hash and revision/observation times | Quote verification, replay, correction history and evidence inspection. A hash alone cannot recover the evidence. Store one raw input version; parser changes reuse it. |
| `source_spans` | Ordered original passage text, exact input/parser version, available timestamps, speaker labels/roles and attribution state | Extraction, neighboring context, citations and reverse lineage. A new parser produces a new span view without copying raw input again. |
| `transcript_chunks` | Source/parser/chunking versions, sequence, one exact contextualized embedding text and input hash; generated `tsvector` projection | Brief discovery and hybrid text search. Do not save separate original, normalized and rendered copies of every chunk. |
| `chunk_spans` | Chunk → original span membership | Resolve a search hit into exact evidence, and find relevant moments despite rechunking. |

Original recording/video bytes are not copied merely because a recording link exists. Transcript content is in SQL; recording/media locators point to their actual source. Image/OCR storage would be added only with an implemented evidence feature and an explicit original-media retention need.

### B. Configuration and weekly execution

| Table | Data retained | Consumer |
|---|---|---|
| `policy_versions` | One typed registry for actual editorial/voice/offer/CTA/format/exemplar/parsing/chunking/signature/prompt/scoring/retrieval/checker/model-route versions, body/hash and activation | Generation, checks, Library and historical reproducibility. Avoid separate version tables for every configuration kind. A CTA pins its offer version when applicable. Custom CTAs are inactive version records, rather than duplicated untracked approval blobs. |
| `embedding_profiles` | Model/provider route, fixed physical dimensions, metric, actual parameters and profile hash | Vector compatibility, re-embedding and matching. Model name alone does not describe the entire embedding contract. |
| `editorial_cycles` | Business period/timezone, cutoff, administrative state and concurrency version | Week selector and weekly lifecycle. Do not infer the business week from the operator's timezone. Detailed pipeline phase is derived. |
| `cycle_sources` | Included/excluded/pending live bucket membership and reasons | Weekly bucket and missing-input display before a source has a readable revision. |
| `pipeline_runs` | Cycle, parent run, mode/purpose/scope, memory eligibility branch, fixed scoring time, history readiness and completion state | Evaluation isolation, reruns, completeness and execution history. Generation-only remains distinguishable from a completed similarity evaluation. |
| `run_sources` | Exact admitted source revisions and their role | Frozen extraction/generation inputs. Late arrivals cannot silently alter an old approved input set. |
| `run_policies` | Exact effective policy versions per stage | Explain/replay old work without substituting today's active rules. |

Only versions actually supplied to a stage are linked. The database does not store every possible combination of models, prompts and configuration in advance.

### C. Evidence and permissions

| Table | Data retained | Consumer |
|---|---|---|
| `moments` | Selected literal quote, proposition, context, type, audience relevance, qualifications, epistemic category, sensitivity, strength/reasons, verification dimensions and applicable human ledger labels | Angle generation, Moments Ledger and evidence review. The model's `measured` category is not a human measurement confirmation. Corrections create superseding immutable records. |
| `moment_spans` | Anchor/context/qualification links to actual source spans | Exact lineage. Supports multiple transcripts without embedding or copying their full text into the moment. |
| `claims` | Specific factual proposition considered for copy, applicable quantitative/subject/period/attribution scope, allowed wording, limits, exclusions and verification | Brief contract and factual checking. Create only when a factual proposition is considered for downstream use. A hook, slide number or general editorial principle does not automatically need a claim row. |
| `claim_spans` | Supporting, qualifying and contradicting original passages | Proof panel, claim validation and dependency tracking. |
| `permission_events` | Recorded permission dimensions, scope/handling, effective/expiry times, evidence reference, actor and one exact client/source/moment/claim target | Consent register and source/claim-use checks. Naming, quoting and using result figures are independent dimensions. Applicable restrictions remain in force across scopes. |

Why store a claim when a moment already exists? “The client reported bookings attributed to ads” and “we generated profit” may reuse the same number and quotation while making different assertions. The claim record captures the permitted proposition and its limits. It becomes necessary at briefing/copy validation; it is not a third extraction model stage or another vector target.

There is no global people directory. A supplied speaker label and its verified/unknown role belong to the source context. Keep uncertain facts null or explicitly unverified; do not manufacture meeting dates, names, proof scores or consent from incomplete exports.

### D. Angles and argument memory

| Table | Data retained | Consumer |
|---|---|---|
| `angles` | Stable logical identity, real origin/original generation time, originating run and optional derivation link | Memory, age calculation and history. Revival, title edits and re-embedding do not refresh generation age. |
| `angle_revisions` | Title, argument, audience, tension, take, mechanism, reader decision, source assertions, inference, qualifiers/risks and authorship | Angle UI, argument signature, research and exact Gate 1 approval. This is generated/editorial content, not hidden chain of thought. |
| `angle_moments` | Actually cited moments and their role | Evidence display and angle → moment → source resolution. The run already records the larger input set. |
| `angle_evaluations` | Actual five-dimensional quality assessment/method/reasons, base score, evaluated risk/adjusted score, selection state and exact candidate embedding | Ranking and reviewer explanation at a fixed run. Save observed decision inputs; do not silently recompute the historical card with changed weights. |
| `angle_embeddings` | Exact logical angle/revision/profile/signature encoder/input hash, vector, attempt and activation | Subsequent-week argument comparison and prior-angle briefing discovery. No copy of the full angle or source text in this vector table. |
| `chunk_embeddings` | Exact chunk/profile/input hash, vector, attempt and activation | Semantic transcript research. Original content/citations remain in SQL. |
| `run_history_angles` | One exact historical vector representative per logical angle in this run | Reproducible eligibility and replay. Filters alone can drift as an archive changes. |
| `angle_matches` | Every qualifying historical pair and its raw cosine | Explain the overlap result. Age/overlap/freshness are derived from the frozen run, angle date and scoring policy. |
| `current_angle_pairs` | Qualifying close current pairs, raw cosine and explicit/unresolved disposition | Distinctness review. Current pairs are separate from historical freshness penalties; no winner is silently imposed. |
| `cycle_angles` | This week's chosen revision/evaluation, generated/manual/revived participation, known previous cycle and concurrency version | Weekly Studio, previous concepts and revival. Do not copy an old angle to make it look newly generated. |

Every valid generated angle is retained even when scoring suppresses it; future matching and Ideas/History consume it. Invalid or failed model output is not a valid angle merely because an HTTP response arrived. Fake/evaluation runs do not enter production memory unless an explicit policy admits them.

An argument making a materially different reader promise becomes a new logical angle, with a derivation link when appropriate. Cosmetic edits and ordinary revisions keep the logical identity and original age. This is an editorial identity decision; the schema does not silently redefine an old idea as fresh or add another similarity-judging model stage.

The existing UI's old proof/audience-pain/offer-fit/recurrence/novelty/demand bars are not independent measured data. The current backend has grounding, source relevance, audience fit, specificity and editorial usefulness. Store the real assessment and method; the UI should display that contract or label a separately performed editorial review honestly.

### E. Brief research and editorial contract

| Table | Data retained | Consumer |
|---|---|---|
| `brief_contexts` | Exact Gate 1 decision/workstream/run, one frozen compact packet/hash and coverage/gap metadata | Brief writing, replay and review of what the writer actually received. Snapshotting the packet is a deliberate exception to deriving every rendered view. |
| `context_findings` | Selected/graded finding, kind, summary/assessment, discovery chunk, relevant external URL/time/query trace and meaningful inclusion/omission decisions | Research detail and context assembly. Do not permanently persist every ungraded top-50 candidate hit. |
| `finding_spans` | Exact original evidence/neighboring qualifications behind a finding | Citations and proof review. Discovery chunk identity is not a replacement for supporting span identity. |
| `context_prior_content` | Exact prior angle/brief/asset/publication references actually supplied, compact coverage/state and discovery path | Distinct briefing with history from matched transcripts or independently matched prior arguments. Historical proposals are not mislabeled as publication or factual proof. |
| `briefs` | Stable workstream identity | Refresh-safe brief link and revision history. |
| `brief_revisions` | One structured body, exact context, attempt/editor/date and hash | Brief editing, required questions, locks, Gate 2 and asset generation. Body includes the actual production directions/claim exclusions, not finished assets. |
| `brief_evidence` | Findings actually carried into this brief | Proof/citation display and context-to-brief membership validation. A brief may use a subset of the dossier. |
| `brief_claims` | Exact allowed factual claim versions | Closed claim set for asset generation and checking. |

The frozen packet and its structured membership serve different consumers: the packet preserves the exact compacted text supplied; the membership tables allow SQL joins, inspection and invalidation. Both are needed here. Avoid also saving full source bundles inside briefs, assets, request logs and prior-content snapshots.

The structured brief body preserves actual UI fields: audience/reader promise, insight, message spine, voice, proof and hypotheses, excluded claims, CTA wording, assigned-asset directions, creative notes, distribution intent, questions/answers, success criteria and locks when used. Store intent and criteria; do not turn them into invented observed performance.

### F. Production and review

| Table | Data retained | Consumer |
|---|---|---|
| `packs` | Stable cycle/group identity and title | Pack list, history and deep links. |
| `pack_plan_revisions` | Exact immutable allocation version and actor/time | Plan changes and generation inputs. |
| `pack_slots` | Ordered slot, one exact governing brief, format version, required flag and distinct reader contribution | Assignment UI and independent asset generation. Format/asset counts are policy, not a hard SQL limit. |
| `assets` | Stable generated/imported identity and pack slot key or real import source | Asset history and genuine past-content imports. Do not fabricate missing prior angle/brief lineage. |
| `asset_revisions` | Exact structured copy, immutable assignment, attempt/editor/date, hash and supersession | Editor, version comparison, checks, pack assembly and actual publication representation. |
| `asset_claims` | Claims actually expressed and structured body location | Factual validation and evidence display. Generated claims must belong to the governing brief's allowed set. |
| `pack_revisions` | Exact plan, manifest version/hash and creation time | Gate 3 approves this manifest, not a mutable pack identifier. |
| `pack_revision_assets` | One exact revision per logical asset in a pack snapshot | Freeze the review set, preserve prior packs and verify required-slot completion. No duplicated pack-wide copy of every asset body. |
| `check_results` | Exact asset/pack revision, checker version, kind, pass/warn/fail/unavailable result, blocking flag and actionable findings | Check UI, repair and approval readiness. Unknown/unavailable is not pass. |
| `review_events` | One exact target, applicable gate/workstream, action/reason/steer, explicit CTA version, authenticated actor/authority, timestamp and idempotency | Three gates, saved/pass/revisit actions, labels/feedback, plan confirmation and exact warning acknowledgement. These events are append-only; worker models cannot approve. |

Save asset structure as a validated JSON body rather than a table per slide, paragraph, shot or caption. Those components currently share an asset's editing, checking, approval and scheduling lifecycle. Email stores subjects/preview/body/CTA; carousel stores ordered slides/design notes/caption variants; each reel stores its own spoken script/hook/talking points/shot direction/captions. Split a component into an independent table only if it gains an independent lifecycle or relational query requirement.

This also avoids storing a brief's suggested outline as the supposedly generated final email or reel. Approval timestamps come from decisions, not a second mutable set of `angleApprovedAt`, `briefApprovedAt` and `publishingApprovedAt` fields on the same frontend idea blob.

Save meaningful committed revisions. Coalesce temporary keystrokes and unsaved editor state in the client; do not generate a permanent audit version for every keypress. Once a saved revision is used by a context, assignment, check or approval, preserve its exact content and dependencies.

### G. Planning and publication

| Table | Data retained | Consumer |
|---|---|---|
| `asset_schedules` | Exact asset revision, exact Gate 3 approval, channel, UTC instant/entered timezone, reschedule lineage and planning state | Current individual-piece scheduling and Calendar. Editing copy does not silently make the approved old schedule refer to new copy. |
| `publication_events` | Actual published asset representation, optional schedule, channel/date when known, link/confirmation and recorder | Posted/history state and prior-content briefing. No automatic publication is implied. |

A calendar date in the past is a passed schedule, not proof of posting. An approved pack is ready, not published. A date of unknown provenance stays null. If people modify the copy before posting, save that representation as an asset revision before recording its publication.

Imported published copy with unknown original angle/brief lineage is still useful SQL history. Retrieve it through actual text lookup or deliberate exemplar selection and mark coverage limitations; do not pretend it participates in angle-vector matching until a real angle representation is supplied. No third vector target is introduced for these imports.

### H. Operations

| Table | Data retained | Consumer |
|---|---|---|
| `work_items` | Durable stage intent, run/connector, idempotency, frozen expected-input manifest, state/due time, real progress and lease/fencing | Background execution, safe refresh/retry, source sync and operator health. Reuse one mechanism; Redis is delivery, not the canonical completion record. |
| `work_attempts` | Actual attempt/model/route/settings/fingerprint, output hash, returned usage, conditional validated replay cache, state/times and safe error | Paid-call reuse, replay, coverage, debugging and cost/operator reporting. Model settings and usage stay server-side. |

No job is created per sentence or search candidate. A persisted checkpoint/attempt should correspond to independently resumable, meaningful work. Domain relationships remain real foreign keys; `input_manifest` is a bounded operational request describing expected dependencies, not the sole relationship store.

## 5. What each phase reads and writes

| Phase | Reads | Durable writes | Vector role |
|---|---|---|---|
| Ingest and normalize | Configured scope/checkpoint and admitted source | Source/input revision, parser-scoped spans, bucket membership and sync attempt | None required to preserve input |
| Chunk/index transcripts | Source spans and chunking/profile version | Chunks, membership, input hashes and compatible attachments | Chunk vectors support later research |
| Extract/verify moments | Complete frozen weekly source view and exact extraction policy | Valid moments, actual anchors/context, qualifications and coverage | No moment embedding |
| Generate angles | Validated moments, original context and active curated rules | Every valid argument revision, actual moment links and quality assessment | Angle signatures are encoded after valid generation |
| Compare/score | Compatible exact candidate vectors, frozen eligible history, scoring policy/as-of | Qualifying matches/current pairs, observed score/selection explanation | Semantic argument overlap; no extra similarity judge |
| Gate 1 | Exact argument, evidence, score/repetition explanation, chosen CTA and steer | Human event for the exact revision/workstream | None |
| Brief research | Original argument → moments → spans, permitted hybrid transcript results, independently retrieved prior angles, their related SQL content/publications | Graded findings, citations, compact prior coverage, coverage/gaps and frozen packet | Chunk search discovers evidence; angle search discovers prior arguments |
| Brief/Gate 2 | Frozen packet, Gate 1 decision and editorial/format policy | Structured brief revisions, actual evidence/allowed claims, answers/locks and exact human approval | No brief embedding |
| Plan and generate pack | Approved brief revisions, assigned contributions, allowed claims and exact format policy | Immutable assignments and independently generated asset revisions | Routine generation reads approved SQL inputs |
| Check/Gate 3 | Exact manifest/assets, governing briefs/claims, live permissions and checker rules | Revision-bound checks/acknowledgements and human approval of the manifest | No persistent pack/asset vector target |
| Schedule/record use | Exact approved asset/manifest and actual publication confirmation | Individual schedules and separate publication events | Future briefing follows SQL history; future angle scoring retains original angle age |

## 6. Vector relationships and matching semantics

```text
angle_embeddings
  → exact angle_revision
    → cited moments
      → original source spans → source revision

chunk_embeddings
  → exact transcript_chunk
    → chunk_spans → original source spans
      → intersecting moment_spans → relevant moments
        → angle_moments → other angle revisions
          → approved context/brief → assigned asset revisions → actual publications
```

This reverse traversal nominates related records. It does not automatically admit every moment from a meeting just because one chunk matched. Original anchor/context role and evidence assessment determine relevance. An independent angle-vector query catches prior arguments built from other transcripts.

At briefing, preserve the original chosen-angle evidence through direct SQL lookup first. Supplement it with hybrid multi-query research and prior-content expansion. Freeze only the evidence/compact history actually supplied, preserving important limiting facts and visible gaps. SQL guarantees retrieval of the known linked records; semantic search cannot guarantee discovery of every relevant unknown passage.

The baseline remains `text-embedding-3-small`, 1,536 dimensions, cosine. Queries are ephemeral vectors, not another permanent dataset. Same dimensions do not make different model/profile outputs comparable. A dimension change requires a migration, not merely changing `embedding_profiles.dimensions`.

For angle history, retain the earlier scoring contract:

```text
quality_base = 20 × (0.35 grounding + 0.25 source_relevance
                    + 0.15 audience_fit + 0.15 specificity
                    + 0.10 editorial_usefulness)
overlap      = clamp((cosine - 0.78) / (1 - 0.78), 0, 1)
freshness    = 2 ^ (-original_generation_age_days / 28)
pair_risk    = overlap × freshness
overall_risk = maximum pair_risk across all qualifying historical matches
adjusted     = quality_base × (1 - 0.50 × overall_risk)
visible      = adjusted > 70
```

These values are current, uncalibrated defaults stored in a scoring policy version, not permanent SQL constants. Exact angle scans evaluate all eligible history; store all qualifying matches and derive the five-row reviewer summary by pair risk. Do not cap scoring at top five or let approximate retrieval silently omit a risky qualifying pair. Current close-pair disposition remains unresolved and separately represented. Unknown historical generation dates cannot be assigned an invented freshness weight: report the gap and apply a deliberately chosen eligibility policy.

For transcript research, semantic cosine retrieval, full-text search and rank fusion serve discovery. The original architecture proposes top 50 semantic plus top 50 lexical candidates per query, reciprocal-rank fusion and evidence grading. Those are retrieval-policy budgets, not 100 facts to store and not the angle-scoring top-k. Fuzzy spelling can help name/term lookup; it does not establish identity, meaning, exact quotation or permission. Strict existing quote validation is not relaxed by this schema.

## 7. Data deliberately not stored

- Additional embeddings for moments, topics, claims, policies, briefs, assets, publications or query history.
- A second copy of transcript text in each moment, angle, brief and asset. Selected quotes, contextualized chunks and the frozen briefing packet have their own actual consumer; wholesale source-bundle duplication does not.
- Every below-threshold angle pair, every ungraded research hit or a saved query-vector array.
- A separate `primaryQuote`, speaker/client/date/URL bundle on every angle when lineage resolves those facts.
- `daysAgo`, weekday strings, formatted timestamps, usage counts, pending counts, calendar layout, an invented progress percentage or duplicate workflow phase badges.
- A duplicated pack-wide JSON body containing copies of all asset revisions; the pack manifest references them.
- A standalone table per carousel slide, paragraph or reel shot while those components share the asset lifecycle.
- Prototype flags/palettes/mock layout versions/deployment IDs/simulation state, synthetic demand/overlap scores or hardcoded Client Intelligence metrics.
- Authentication users/passwords/session cookies/OAuth/API keys. Existing authentication owns identity; events retain verified actor references and required authority facts.
- Model chain of thought, complete HTTP response envelopes, full private-text debug logs or a permanent vector-array cache alongside pgvector.
- Analytics, social publishing credentials, autonomous handoffs, learning proposals, notifications, graph databases, separate vector services and extra media stores without an implemented consumer.

Temporary provider evidence is not automatically forever data. Keep the compatible structured cache only while replay/repair consumes it. Pin material needed for a retained replay contract; otherwise expire it under a defined retention policy after durable domain outputs are verified. An output hash alone is insufficient if replay still requires the exact structured output. Malformed responses may have a restricted temporary diagnostic record; they are not valid editorial entities.

## 8. Referential and operational requirements for a real migration

DBML parsing/export is not the same as enforcing the complete business contract. The implementation migration must add these responsibilities:

1. **Extension/search indexes:** enable pgvector; generate `search_tsv` and its GIN index. Add `pg_trgm` only when spelling search has an actual consumer. Keep angle matching exact initially. Add an HNSW cosine index for chunk candidate discovery only if measured scale/latency warrants it; approximate indexes can change recall. [pgvector documentation](https://github.com/pgvector/pgvector)
2. **Partial uniqueness:** one active angle vector per logical angle, one active chunk vector per chunk, one active policy version per `(kind, policy_key)`, and at most one live schedule per intended asset/channel. Preserve old vectors pinned by historical runs; do not count them as additional current ideas.
3. **Identity consistency:** composite FK checks already cover angle owner/revision and manifest asset owner/revision. Also enforce same source/parser for chunk membership; run-history vector ownership/profile; candidate vector ownership; cycle/evaluation ownership; context/finding/brief agreement; pack/plan/slot/asset ownership; prior-context lineage agreement; schedule membership in its approved manifest; and generated claims belonging to the governing brief.
4. **Typed configuration/content:** validate each policy/brief/asset/assessment JSON schema. Referenced policy kinds must agree with their role. Unknown metadata stays nullable; explicit unknown verification/permission states are not silently coerced to success.
5. **Revision-bound decisions:** apply expected-revision/concurrency checks, verified human authority, CTA choice, answered required questions, current dependencies, blocker checks and exact warning acknowledgements transactionally. An existing auth `team` role is not itself permission to approve. Superseded substantive evidence/argument/brief/plan changes make dependent work stale rather than swapping its FKs silently.
6. **Durable work:** atomically commit domain changes and next work intent; leases/fencing and input-version checks reject late/stale worker promotion. Request/decision idempotency prevents duplicate logical actions. Provider charges may still be ambiguous after a crash; cache/fingerprints do not promise exactly-once billing.
7. **Use-time eligibility:** source/claim permission and withdrawal apply before retrieval and again before approval/use. Historical approvals do not bypass later restrictions. Controlled purge, when required, must include vectors and retained packets/caches containing withdrawn material, while minimal source tombstones prevent reimport. Ordinary immutable revisions do not mean unconditional permanent retention.

Use opaque `text` IDs to preserve saved identifiers during migration. Use `timestamptz` for instants; display formatting belongs in the UI. Use ordinary relational columns for dates, ownership, references, statuses and decision targets; JSON is for validated editorial structure and scoped assessment payloads. Add further indexes from actual filter/join latency, not an index on every JSON field.

## 9. Build sequence without speculative data collection

| Increment | Implement/populate when needed |
|---|---|
| Source and execution foundation | Sources/revisions/spans, used policy versions, cycle/run manifests and durable work. Connection/client rows only for known enabled integrations/identities. |
| Transcript/angle proof | Moments/links, valid angles/revisions/quality. Add the two vector targets, profiles, frozen history and match/evaluation rows only when embedding/scoring is intentionally reconnected. Generation-only continues with null overlap results. |
| Gate 1 and weekly UI | Cycle participation, exact review events, CTA versions and concurrency. No mock approval state in local storage as authority. |
| Briefing | Graded context/prior coverage, factual claims, permission register, brief revisions/evidence/claim sets and Gate 2. External-framing rows only for executed research. |
| Production | Actual plan slots, asset revisions/claims, exact manifest, checks and Gate 3. No saved pack until generated/assembled. |
| Scheduling/publication | Individual schedules when users schedule; publication rows only when actual use is recorded or a real published example is imported. |

This is a full-flow schema so dependencies are designed before migration. It is not a requirement to deploy all downstream tables or populate all nullable metadata before testing the first two generation stages.

## 10. Verification and source basis

The complete DBML was checked with the official `@dbml/core` 10.3.1 parser using `dbmlv2` and PostgreSQL SQL export: 51 tables, 118 relationships and exactly two vector columns. All 51 tables have a consumer explanation in this document, and local links were checked. Parser validation checks syntax and reference binding; no PostgreSQL database was contacted and migration constraints/triggers have not been exercised. [Official DBML parser documentation](https://dbml.dbdiagram.io/js-module/core/)

Local implementation/design inputs:

- [Backend moment/angle models](backend/backend_pipeline/models.py) and [response/signature contracts](backend/backend_pipeline/contracts.py).
- [Current scoring](backend/backend_pipeline/scoring.py), [JSON storage](backend/backend_pipeline/store.py), [limited vector projection](backend/backend_pipeline/db.py) and [backend scope](backend/README.md).
- [Actual frontend data types](frontend/src/types/atelier.ts), [approval/revival behavior](frontend/src/utils/editorialWorkflow.ts), [individual scheduling](frontend/src/utils/publishingSchedule.ts) and [existing authentication](frontend/AUTH.md).
- [Target frontend workflow](frontend/Frontend-contentatelier.md), [reconciled architecture](research/architecture-comparison-and-reconciled-design.md), [vector matching spec](research/pgvector-creation-and-angle-matching-spec.md) and [briefing provenance](research/briefing-provenance-and-prior-content-context.md).

Older four-angle ranking, broader vector targets and automatic publication assumptions do not override the user's later two-target, threshold-based and human-review decisions.
