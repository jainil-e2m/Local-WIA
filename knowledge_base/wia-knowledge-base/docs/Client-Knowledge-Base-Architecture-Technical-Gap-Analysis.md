# Client Knowledge Base: technical architecture gap analysis

**Date:** 20 October 2026 · **Status:** Technical audit, required additions and revision coverage map  
**Architecture:** [Client Knowledge Base Solution Architecture](Client-Knowledge-Base-Solution-Architecture.md).

## 1. Finding

This finding describes the first KB draft audited at the start of this round. Section 8 tracks the technical additions subsequently made; the main architecture has now been expanded.

The first draft established the product boundary, important invariants and logical components, but left too many implementation mechanisms undefined. Development guidance requires explicit inputs, outputs, algorithms, transactions, numerical starting parameters and failure effects.

The revision adds database execution rules, extraction contracts, retrieval algorithms, workflow transitions, job schedules, physical schema and operational configuration. Proposed engineering settings remain distinguishable from approved product policy and tested results.

## 2. Technical depth requirements

| Topic | Original KB specification gap | Required addition |
|---|---|---|
| Stack | Database access/session mechanics deferred | Chosen libraries, transaction/session ownership, migration paths, sync/async policy and dependency pinning process |
| Retrieval | Authorised retrieval principle without a bounded algorithm | Eligible corpus, search request/hit schemas, filter placement, ranking, indexes and examples |
| Extraction | Fields described mainly in prose | Typed output contracts, extraction taxonomy, batching, source-span validation and acceptance rules |
| Workflow | Event/treatment table without complete transition rules | Orthogonal states including reopening, superseded verification and correction approval |
| Jobs | Job families and failure principles | Work schema, atomic claims/publication, dispatch/recovery loops, schedules and bounded parameters |
| Data | Record groups and relationships | Columns/types/nullability, foreign keys, check/unique constraints, indexes and representative DDL |
| Interfaces | Mostly placeholder service methods | Typed adapter contracts and concrete HTTP routes/request/response/error examples |
| Configuration | Many values left to later configuration/testing | Proposed starting settings, units/validation, setting ownership and explicit unset blockers |

These requirements govern the KB's own engineering design. Numerical starting values require calibration; provider capabilities, source access, capacity and recovery targets require verification.

## 3. Clarifications obtained during this audit

The three questions asked in this round are answered; they are not open dependencies.

| Question | User answer | Consequence for the deeper specification |
|---|---|---|
| Technical Q21 | **SQLAlchemy ORM with psycopg and Alembic** | Define ORM mappings/session management and Alembic ownership under the SOP's SQL migration location. Do not keep raw SQL versus ORM undecided |
| Technical Q22 | **Authorised resolvers apply corrections; other editors propose** | Separate proposal creation from application. Resolution rights allow audited direct application; editing rights alone do not |
| Technical Q23 | **Automatically reopen and supersede prior verification** | A validated reopening of the mapped ClickUp task reopens the KB action. Prior verification remains historical and is superseded; it is not silently deleted or automatically restored later |

The user selected SQLAlchemy ORM with psycopg and Alembic for the KB. Define its session, mapping and migration ownership explicitly. [SQLAlchemy PostgreSQL/psycopg documentation](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg), [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html).

Q23 is a specific exception to preserving reviewed state: the reopened task changes the action's current progress and supersedes its verification. It does not authorise overwriting reviewed owners/deadlines, contractual facts or every other corrected field. Repeated deliveries and older task snapshots must not create false reopening transitions.

## 4. Missing specifications and required deliverables

**P0:** needed to implement the shared foundation/first-release correctness. **P1:** needed before the related capability goes live; engineering can build independent foundations meanwhile. **P2:** conditional extension after measurement, not a reason to delay the core.

### TG-01 — Chosen stack and database execution model · P0

**Current gap:** a stack table does not tell developers where sessions live or which execution model to use.

Add the selected PostgreSQL/SQLAlchemy/psycopg/Alembic baseline, Python/runtime compatibility policy and Pydantic validation approach. Specify session-per-request/job, transaction ownership in services, connection-pool limits, statement/lock timeouts, sync versus async engine use and clean shutdown. Never share an ORM session between worker jobs/threads.

Map Alembic revisions under `backend/sql/migrations/`, establish one schema owner, and give migration commands/configuration and upgrade/rollback compatibility rules. Choose a tested dependency set rather than copy an old version pin or say “latest”. SQLAlchemy and Alembic selection is settled; exact tested pins are engineering work.

**Completion artifact:** dependency table, connection/session code skeleton, migration layout and commands, plus one ORM model/migration pair illustrating constraints.

### TG-02 — Deployment topology and process ownership · P0

**Current gap:** the KB lists deployment units but leaves execution responsibilities and resource competition vague.

Specify the public UI/API origin, any proxy/BFF role, internal service URLs, process commands, health/readiness endpoints, scheduler leadership and migration job. Show exactly which process can access connector secrets, database, Redis and model credentials. Identify whether authenticated chat uses SSE, polling or both and how proxy timeouts affect it.

Provide an initial API/worker/scheduler layout for ten simultaneous users and explain which capacity remains isolated for current intake while long agent/backfill jobs run. A list of priority queues alone does not guarantee fifteen-minute updates during a burst of interactive work.

**Completion artifact:** deployment/service table, container entry points, local compose example, network diagram and capacity test assumptions.

### TG-03 — Physical data schema and invariants · P0

**Current gap:** groups such as `facts`, `actions` and `reviews` are logical nouns, not enough to produce migrations consistently.

Specify core columns/types/nullability, foreign keys, uniqueness, delete/update behaviour and indexes. Include business/engagement identity, source/version keys, evidence scope links, observation/effective times, current-value pointers, actions, review proposals, lifecycle/verification events, per-user read revisions and grants/overrides. Define money precision/currency and the distinction between date-only deadlines and timestamp deadlines.

Define how current-state rows relate to immutable history and how concurrency versions advance. Distinguish a source version, an extraction version, a reviewed entity revision and an answer dependency revision; one generic `version` field cannot explain all four.

**Completion artifact:** core ORM models/DDL sketches, relationship diagram with actual keys, index catalogue and migration sequence. Later-feature tables can be specified after their definitions without postponing the foundation schema.

### TG-04 — Canonical connector and processing envelopes · P0

**Current gap:** adapters have placeholder method names without typed return values or partial/error semantics.

Define `SourceRef`, `SourceObservation`, `ChangeBatch`, `CoverageResult`, `OriginalFetchResult`, `SourceAvailability` and `ProcessingResult`. Include connector account/scope, provider record ID, provider version when available, content hash, event/update/observation times, pagination/checkpoint, deletions, capability limitations and retry classification.

Specify when a batch cursor is safe to commit, how partial pages are retried, and how a transient full body flows through parsing without entering permanent work payloads/logs. Document providers that do not expose a total count, historical versions or a reliable deletion signal.

**Completion artifact:** typed contracts, representative payloads and invariants all connector implementations must satisfy.

### TG-05 — Eight source-specific intake playbooks · P0

**Current gap:** the source matrix records what each integration is for but not its full synchronisation procedure.

For each source provide endpoint/method, read scopes/account identity, event subscriptions, verification method, minimal receipt, pagination, cursor semantics, incremental reconciliation, renewal rules, API-limit handling and a concrete failure/recovery sequence. Verify current provider details before treating them as configured behaviour.

| Source | KB-specific details still required |
|---|---|
| Gmail | Watch/Pub/Sub topology and authentication, mailbox/label/query boundaries, history checkpoint/replay, expired-history recovery, attachment parsing and Dubsado event identification |
| Drive | Approved-folder traversal/membership changes, native export formats, change tokens/watches, shared-drive handling, revision fetch limits and removal versus access loss |
| Calendar | Calendar registry, occurrence IDs/recurring instances, cancellations/copies, incremental tokens, full-resync behaviour and event-to-meeting matching |
| Slack | Exact channel/thread scope, history/replies pagination, edit/delete/reaction events, acknowledgement actor mapping and late event reconciliation |
| ClickUp | Workspace/list/task mapping, status/assignee/date/comment/checklist fields, event authentication, refresh reconciliation and the new reopening rule |
| Fathom | WIA recorder/account visibility, meeting/transcript/summary pagination, webhook validation/retries, deduplication and API fallback for missed notifications |
| Historical Zoom | Obtainable transcript/archive discovery, direct versus Drive representations, existing recording-instance identifiers and completeness checks without new transcription |
| LeadLock | Proven location authorisation, account mapping, endpoint-specific read capabilities and explicit handling of current feature-access denials |

**Completion artifact:** one sequence diagram and implementation sheet per source, based on existing scope files and current primary documentation. No new source or paid-media scope is introduced.

### TG-06 — Deterministic identity and duplicate resolution · P0

**Current gap:** “map identities and deduplicate” lacks a precedence order and concrete matching keys.

Define a matching ladder: explicit provider mapping, verified contact/account link, deterministic secondary keys, then reviewed ambiguity. Specify aliases, contact roles, WIA/E2M versus client speakers, source-specific account boundaries and multiple service engagements. Distinguish identity confidence from extraction confidence.

Define canonical meeting/task/commercial-event linking across sources and what is retained as separate corroborating evidence. A repeated meeting number, contact name or similar text alone cannot merge recurring calls or separate commitments. State how changed mappings reprocess observations and invalidate affected views without losing reviewed decisions.

**Completion artifact:** matching/deduplication decision tables, canonical key examples, ambiguity reasons and shared-business fixtures.

### TG-07 — Extraction schemas, batching and evidence validators · P0

**Current gap:** the KB describes extracted fields but does not specify an exact output schema or enough acceptance checks.

Define typed `FactObservation`, `ActionCandidate`, `DecisionCandidate`, `IssueCandidate`, `CommercialEventCandidate` and source-span references where applicable. Separate explicit commitments, client requests and AI proposals. Make owner/date/evidence fields nullable with explicit unknown reasons. Specify admissible task categories and statement/actor attribution.

Define source batching/token limits and how long transcripts are processed with boundary context and cross-batch reconciliation. Processing all history is not achieved by truncating every call to a fixed prompt budget. Verify quoted text/locators against the transient original before cleanup; check numbers, speaker identity, date derivation, business links and required evidence.

Specify validation failures: reject unsupported claims, retain valid partial results with coverage, send ambiguous interpretations to review and bound repair attempts. Confidence values must not become self-authorising acceptance thresholds.

**Completion artifact:** Pydantic/JSON schemas, extraction prompt/skill contracts, validator rules and representative success/partial/rejected outputs.

### TG-08 — Current-value reducer and field-authority matrix · P0

**Current gap:** the architecture gives two authority examples but leaves most fields and conflict cases to implementation.

Define a pure reconciliation/reducer contract: existing reviewed value + new source observation + field policy + revision state → maintained value, history event, review item and invalidation set. Distinguish source event time, observation time, effective time and human correction time so historical queries do not mistake discovery date for business date.

Build a field matrix for profile details, task owner, deadline, progress, acknowledgement, verification, signed terms and paid events. Identify automatic mapping, preserved human correction, review and prohibited inference. Include the newly approved task-reopening exception explicitly. Do not extend “meeting wins over ClickUp due date” to every field or every conversation.

**Completion artifact:** authority matrix, reducer pseudocode, before/after examples and expected conflict outcomes.

### TG-09 — Complete action/correction state machines · P0

**Current gap:** an event/treatment table does not define legal transitions, preconditions or supersession.

Define independent progress, origin, review/conflict, acknowledgement and verification states. Show which transitions come from sources, editors, resolvers and verifiers, and how the combined state is projected to the frontend's labels. Define whether historical items are active, archived, withdrawn or review-only without conflating those concepts.

Incorporate Q22: editors propose; authorised resolvers can apply. Incorporate Q23: a genuine mapped ClickUp reopening changes progress automatically and supersedes the previous verification, preserving its history. A subsequent completion requires a new valid follow-up check; it must not resurrect the old verification.

Define owner reassignment and its effect on identified-owner acknowledgement; preserve previous acceptance history rather than attributing it to the new owner. Specify handling of changed commitments, cancelled tasks, duplicate events, late source snapshots, concurrent verification and reaction removal. Any remaining business choice must be explicit rather than buried in code defaults.

**Completion artifact:** state diagrams plus transition table with trigger, actor permission, guards, transaction effects, emitted change and failure result.

### TG-10 — HTTP API and field-by-field frontend contracts · P0

**Current gap:** endpoint groups and the current TypeScript interfaces do not define the production API.

Specify methods/paths, request/response schemas, authentication/permissions, pagination/filter/sort rules, optimistic concurrency, idempotency and error codes. Cover business/engagement records, actions, corrections/reviews, change reads, citations/search, health/coverage, refresh, administration and later chat runs.

Map each existing displayed field to the API projection, source/evidence requirements, null/unavailable rendering and release gate. Explicitly address `Action.owner`, required due strings, single `sourceId`, `Client.coverage`, `Invoice.status/amount` and generated health/narrative fields. Avoid inventing a percentage, balance or invoice merely to preserve the mock shape. Preserve the deliberate deferral of narrative-summary maintenance.

Define stale-write responses and UI recovery rather than letting a browser `PATCH` overwrite another person's review. Keep last-successful sync, source event time and last attempt distinct in the API.

**Completion artifact:** endpoint catalogue, JSON examples, shared frontend types and per-screen field mapping/error behaviour.

### TG-11 — Central authentication/provisioning integration contract · P0

**Current gap:** existing auth is referenced without specifying the KB's exact integration and required central changes.

Specify central application/client registration, trusted identity/session validation, callback flow, state/challenge checks where used, cookie attributes, expiry/logout and disabled-account propagation. Establish the stable user identifier and how central identity maps to KB membership.

The inspected central registry is configuration-managed; a provisioning API cannot simply be assumed to exist. Define create/link identity, initial credential/invitation handling, existing-account conflicts, retries, partial provisioning and membership activation. List required Command Center changes separately from KB-owned implementation. KB-only removal must not disable other products.

**Completion artifact:** sign-in and Add user sequence diagrams, central API schemas, failure table and cross-application rollout dependency.

### TG-12 — Permission model and enforcement queries · P0

**Current gap:** the policy is clear, but the schema and enforcement mechanism are not.

Define role assignment cardinality, baseline grant aggregation, per-user overrides, client/module grants, feature availability and operation permissions. Encode Inherit/Allow/Deny precedence and self-verification checks in one policy service, with explicit effective-scope projections and revision invalidation.

Choose whether database row-level controls supplement application scoping and explain the boundary for workers/service identities. Give representative scoped SQL/ORM queries for shared evidence, list counts, search and current-user private chat. Never use an unrestricted query and rely on frontend filtering.

Specify how revocation reaches active requests, queued jobs, streaming delivery and citation/download access; sanitised admin metadata must not contain chat content. Include policy checks inside the final mutation transaction so permission changes cannot race a stale precheck.

**Completion artifact:** permissions schema, evaluation function/pseudocode, scoped query examples, operation-to-endpoint matrix and adversarial cases.

### TG-13 — Concrete retrieval/index implementation · P1

**Current gap:** authorised retrieval has no executable search plan or bounded tuning parameters.

Specify retained index units, deterministic context headers, keyword/name matching, exact relation queries, optional embeddings, candidate generation, fusion/reranking and citation hydration. If recommending hybrid search, include SQL and explain how permission filters constrain candidates before ranking. Give proposed starting candidate/result/context limits and mark their calibration status.

KB storage and search retain selected facts/excerpts rather than a full-transcript index. Specify how to recognise insufficient retained context, fetch approved originals where the selected execution mode allows it, validate supporting spans and disclose edited/unavailable original versions. Define embedding-model/version migration and permitted reprocessing without pretending unretained originals are locally replayable.

**Completion artifact:** `SearchRequest`/`SearchHit`, index definitions, search SQL/pseudocode, bounded original-hydration path and relevance fixtures.

### TG-14 — Chat planner/router and client interaction protocol · P1

**Current gap:** high-level routing does not determine which code path answers a question or how the UI handles it.

Specify a typed query plan: resolved client/engagement/time/entity, intent, required freshness, permissible tools, evidence need and resource ceiling. Define ordered paths for approved definitions, parameterised direct queries, dependency-valid cache, evidence synthesis and eligible Viktor skills. Distinguish deterministic intent recognition from model planning and define unresolved-entity clarification.

Specify typed tools, argument validation, maximum plan/tool steps, cancellation, progress events, terminal answer states and evidence/freshness response. Define synchronous direct answers versus asynchronous agent jobs and reconnect behaviour. Store safe run metadata without exposing private conversation bodies in admin diagnostics.

Leave Mode A/Mode B and specialist eligibility test-dependent, but define both against the same interfaces and explicit enablement criteria. These unsettled choices do not prevent specifying the execution contract now.

**Completion artifact:** routing decision table, query/answer/tool schemas, async/SSE-or-polling protocol and example traces for common questions.

### TG-15 — Provider call and skill execution specifications · P1

**Current gap:** two candidate names do not specify who retrieves what or how provider output is reconciled.

For hybrid and Viktor-led, draw responsibility boundaries across retrieval, extraction, interpretation and validation. Define skill input/output formation, permitted connections/tools, source-completeness reporting, asynchronous continuation, billing metadata and cancellation. Specify what makes a route ineligible for a restricted user.

For API interpretation, define actual request settings, schema handling, context budget, fallback eligibility, bounded retry/repair, privacy configuration and cost capture. Keep prompt/skill/routing versions in reviewed releases. Candidate settings may be proposed while keeping model choices subject to KB evaluation.

**Completion artifact:** per-stage/skill provider contracts, typed result/error envelopes, proposed configuration and an evaluation capability matrix.

### TG-16 — Cache lookup, publication and invalidation algorithm · P1

**Current gap:** dependency-aware caching is described thoroughly as a principle but not as an implementable protocol.

Specify canonical query normalisation, scope/private-context partition, cache key, manifest, revision source, collection/time dependencies, TTL as a safety limit, and admission checks. Give exact read/publish order for concurrent source, permission and time-boundary changes. Specify negative-result caching and why new collection members invalidate “none found”.

Define in-flight coalescing, lease/fencing, owner loss, wait timeout and late result rejection. Coordinate database revision changes/outbox publication with Redis, rather than assume `SET NX` alone guarantees correctness. Distinguish private answer caches from shareable KB artifacts.

Semantic answer reuse requires a calibrated intent/entity/time equivalence check; it is not a fixed cosine threshold copied from content similarity. It can remain disabled until its tests pass while exact/direct reuse is implemented.

**Completion artifact:** manifest schema, sample opaque keys, cache state/sequence diagrams, lookup/publication pseudocode and race test cases.

### TG-17 — Outbox, work claims, retries and actual schedules · P0

**Current gap:** durable work is named, but there are no complete transactional algorithms or operational starting settings.

Define work/outbox columns, unique idempotency keys, claim/lease/token semantics, dispatch acknowledgement, heartbeat, retry eligibility and stale-worker commit protection. Explain each crash boundary: before commit, after commit/before enqueue, after provider response/before persistence, and after accepted persistence/before worker acknowledgement. Account for possible repeated paid calls when a response is lost; database idempotency alone does not make provider billing exactly once.

Supply a named job catalogue with queue, trigger, deduplication key, timeout, maximum attempts, backoff, success checkpoint and replay rules. Define actual sweep/reconciliation/watch-renewal/retention schedules, scheduler leadership, provider-specific throttling and capacity reserved for freshness. RQ's documented scheduler capabilities should be checked against pinned versions rather than copied from the older reference. [RQ cron documentation](https://python-rq.org/docs/cron/).

**Completion artifact:** claim/commit SQL or ORM pseudocode, crash matrix, job table, scheduler file and proposed validated settings.

### TG-18 — Backfill completeness and source-coverage accounting · P0

**Current gap:** all available history and WIA gap sign-off are clear requirements, but “complete” has no precise computational definition.

Define the inventory unit/window, expected/discovered/obtained/parsed/extracted/reconciled counts, unavailable originals, unsupported formats and cursor exhaustion. Handle providers without total counts, duplicate copies and shared-business material without inflating coverage.

Specify restartable manifests, checkpoint advancement and reconciliation after mappings change. Define the exact launch gap-report schema and what WIA acceptance records. A limited test dataset must never produce a production-complete flag. Counts need denominators/definitions before displaying a coverage percentage.

**Completion artifact:** coverage tables, reconciliation algorithm, backfill run manifest and signed-off gap-report example.

### TG-19 — Retention/deletion execution and original retrieval safety · P0

**Current gap:** policy categories exist but the expiry calculation and cleanup effects are unspecified.

Specify category policy schema, expiry basis/effective dates, treatment of existing records, preview/apply/cleanup workflow, cleanup retries and audit. Keep transient full originals bounded without reintroducing a permanent archive. Define secure original fetch, temporary-file lifecycle, size/format limits and interrupted-job cleanup.

Distinguish confirmed upstream deletion (retain excerpt with warning), explicit KB erasure, category expiry, permission revocation and temporary access failure. Define what each does to excerpts, fact support, vectors/search, artifacts, answer caches, history and backups. Avoid deleting then automatically reimporting expired records through an unchanged backfill job. Record what can be retained as a non-content tombstone under policy.

**Completion artifact:** retention data model, effect matrix, cleanup/original-fetch sequences and restore-after-expiry tests. Actual durations remain admin configuration, not guessed business policy.

### TG-20 — Deployment, observability and recovery runbooks · P0

**Current gap:** one-hour/four-hour targets are recorded, but there is no complete way to operate or prove them.

Specify backup/archiving configuration and health signals, protected-copy failure domain, secret/config recovery, restore commands, validation queries, application cutover and reopening checks. Flush/change cache namespace and reconcile newer access revocations before serving restored state. Define exactly when the recovery clock starts and when usable restoration is achieved.

Supply deployment/migration/rollback steps, health versus readiness checks, alertable metrics and failure dashboards with sanitised fields. A same-provider bucket is not automatically an independent disaster-recovery copy. Do not copy claims of off-provider protection from a reference without checking the actual failure domain.

**Completion artifact:** operator runbooks, recovery scenario/coverage table and prelaunch restore-drill evidence format.

### TG-21 — Measurable QA and release gates · P0

**Current gap:** important test categories exist, but there are few defined samples, metrics or proposed pass conditions.

Define a versioned fixture/golden-answer set, expected evidence/actions and evaluation runners. Include source completeness, citation support, false commitments, unknown handling, business matching, permission leakage, correction approval, automatic reopening/supersession, cache races, expiry and restore. Compare candidate routes on matched inputs and show missing inputs separately from reasoning errors.

Propose initial sample sizes, thresholds and latency/freshness measures with rationale; distinguish engineering starting targets from WIA acceptance decisions and measured results. Specify ten-user workloads, including cold/warm cache and ongoing ingestion, and define what a failed release gate does. Zero observed defects in a fixture set is not a proof of universal accuracy.

**Completion artifact:** metric definitions, proposed gate table, representative workload and reproducible report. No benchmark needs to be fabricated to make the architecture specific.

### TG-22 — Concrete configuration, costs and build dependencies · P0/P1

**Current gap:** configuration tables and cost categories contain many placeholders rather than a deployable engineering starting point.

Provide YAML/env/settings examples with units, validation, ownership and defaults. Separate runtime secrets, admin business policies, version-controlled AI behaviour and experiment parameters. Propose bounded technical settings such as queue retries, page sizes, timeouts and cache safeguards; label them provisional and explain their measurement plan. Keep actual role grants, retention periods and commercial definitions as required business configuration.

Specify an initial service/process footprint and cost calculation tied to observed records, token volume, user workload, backfill and ongoing change rates. Include conditional agent calls, cache recognition costs, transient original retrieval, backup/restore capacity and the continuing Viktor plan. Unknown monthly cap does not require leaving the cost model qualitative.

Turn the build plan into dependency packages with concrete deliverables: central provisioning changes, schema, adapters, reducer/lifecycle, API/frontend replacement, candidate evaluation, full backfill and release evidence. Preserve the agreed November targets as targets, not validated estimates.

**Completion artifact:** starting configuration, capacity/cost scenarios and engineering work packages with exit criteria. Fresh prices and empirical workloads must be verified when calculating the revised estimate.

## 5. Depth standard for the revised architecture

Each substantial section should answer:

1. What is the input, and which typed schema validates it?
2. What exact algorithm/rule/transition operates on it?
3. Which process/service executes it, and under which authority?
4. What is stored, what stays transient and what identifies a version/duplicate?
5. What is atomic, what is asynchronous and what happens at each failure boundary?
6. What are the bounded starting parameters and who can change them?
7. What output/API/event reaches the frontend or next stage?
8. What proves the result, access and recovery behaviour are correct?

If a developer still has to invent a material business rule or the core transaction protocol after reading the section, it needs further detail. The architecture need not contain every production function, CSS breakpoint or final index tuning value to meet that standard.

### Worked example: the detail missing from correction handling

The current instruction “preserve reviewed corrections with an audit trail” should become an implementable sequence. The following is a proposed protocol illustrating the expected depth, not a new business approval rule:

```text
Input: target/field, proposed value, expected entity revision,
       reason and retained evidence references; actor comes from trusted session.

1. Resolve active identity/membership and permitted client/module scope.
2. Validate the field's value schema and evidence scope.
3. Begin a short database transaction; lock/check the current entity revision.
4. Recheck effective operation rights and field authority for this mutation.
5. If only proposal rights: persist a pending correction; do not replace current value.
6. If resolver rights: append correction history and apply the maintained value.
7. Persist the change revision, required review updates and invalidation/outbox rows.
8. Commit; workers perform subsequent derived work outside the transaction.
9. Return the applied/proposed result and current revision; a stale revision conflicts.
10. UI shows the appropriate read/unread change, independently of conflict resolution.
```

The complete specification must attach concrete models, endpoint/error codes, version checks, transaction isolation and tests to that sequence. Authorisation must not be decided by a browser-supplied `apply=true` flag.

### Worked example: automatic reopening

```text
Verified action + valid mapped ClickUp active-state transition:
  append the new source observation;
  reopen current progress according to the configured task-status mapping;
  mark the current verification superseded, preserving who/when/evidence;
  create a new change revision and update dependent collections/artifacts/caches.

Duplicate/stale source snapshot:
  no additional reopening or verification event.

Later task completion:
  supports Done under normal rules; old superseded verification does not reactivate.
```

Define source ordering, authoritative refetch and locking before implementing this rule. An automatic reopening is a genuine change event, not merely a review badge attached to an otherwise Verified action.

## 6. What to specify now versus what must remain conditional

| Decision class | Treatment |
|---|---|
| Settled product policy | Encode exactly; do not repeatedly ask about first-release priorities, testing access, source scope or private chats |
| Q21–Q23 choices | Record as decisions and update the main architecture's conflicting placeholders/policies |
| Engineering mechanism | Propose a concrete baseline, alternatives and rationale; do not defer every detail as configuration |
| Numerical engineering starting value | Label proposed/calibratable, define units/bounds and the test that will tune it |
| Actual business configuration | Keep required inputs such as role grants, emoji mapping, retention periods and stage definitions explicit |
| Provider capability/account access | Verify the current API/account; do not assume an adapter or Viktor eliminates a denial |
| Empirical candidate selection | Keep hybrid versus Viktor-led and chat Mode A/Mode B unresolved until evaluated, but specify both interfaces now |

No need to reopen full-original retention: the user selected facts/excerpts. Define retrieval/extraction around that constraint. No need to reintroduce the deferred question about maintaining summary/background/focus narratives. Health scoring, Shopify, fresh paid-media intake and later feature order likewise remain outside new automatic assumptions.

## 7. Revision order and completion criteria

1. Close foundation choices and encode Q21–Q23; specify physical schema, identity/access and correction/action state machines.
2. Specify canonical intake contracts, per-source playbooks, matching, extraction validation and coverage.
3. Specify HTTP/frontend contracts and exact transaction/event boundaries.
4. Specify durable jobs, real schedules, provider adapters and protected workload capacity.
5. Specify retrieval, chatbot execution, cache algorithms and conditional route evaluations.
6. Complete retention/restore runbooks, numerical starting configuration, QA gates and capacity/cost calculations.

Preserve sections 0–16 and Appendices A/B, deepening their existing subsections. Add focused tables, schemas, SQL/pseudocode, configuration and sequence/state diagrams inside those sections rather than lengthening the policy preamble.

The rewritten document is development-guiding when a developer can trace a source event through normalisation, extraction, reconciliation, review/application, cache invalidation and the exact frontend response; can trace an authenticated correction and a reopened Verified action through the same boundaries; and can explain each crash/retry/access-loss outcome without inventing the missing rules.

This audit identifies the initial gaps and captures the new choices. Section 8 maps the technical elaboration now added to the main architecture; updating a few baseline/state paragraphs alone would not have addressed these gaps. Runtime implementation, provider evaluations and measured acceptance remain outstanding and are not represented as completed by this documentation revision.

## 8. Coverage added to the main architecture in this revision

The audit led to direct expansion of the existing architecture, not just a separate list of future work. These are specification additions; they are not executed code or measured provider/runtime results.

| Audit areas | Main architecture additions |
|---|---|
| TG-01–02 | [2.5 Runtime/session/transaction baseline](Client-Knowledge-Base-Solution-Architecture.md#25-proposed-runtime-and-transaction-baseline): process ownership, connection budget, sync handlers, Alembic ownership and commands |
| TG-03 | [10.1 Physical schema](Client-Knowledge-Base-Solution-Architecture.md#101-physical-schema-starting-point) and [10.2 ORM mapping](Client-Knowledge-Base-Solution-Architecture.md#102-representative-orm-mapping-and-schema-ownership): typed columns/constraints, partial/unique indexes, example SQLAlchemy model and bootstrap |
| TG-04–08 | [4.8–4.10](Client-Knowledge-Base-Solution-Architecture.md#48-canonical-inputoutput-contracts): source/extraction contracts, batching/validation, eight source procedures, identity ladder, field reducer and coverage accounting |
| TG-09 | [6.6 Mutation/state protocol](Client-Knowledge-Base-Solution-Architecture.md#66-mutation-protocol-and-legal-transitions): proposal/application, automatic reopening, verification supersession, idempotency/revision/lock behaviour |
| TG-10 | [4.11 HTTP/frontend contracts](Client-Knowledge-Base-Solution-Architecture.md#411-core-http-and-frontend-contracts): concrete routes, error/concurrency/pagination semantics and mock-field replacements |
| TG-11–12 | [12.5 Auth/policy contract](Client-Knowledge-Base-Solution-Architecture.md#125-exact-policy-boundary-and-proposed-central-service-contract): central endpoints explicitly marked proposed, provisioning failure handling, membership policy and private-content boundary |
| TG-13 | [3.8 Retrieval algorithm](Client-Knowledge-Base-Solution-Architecture.md#38-search-contract-and-proposed-ranking-algorithm): scoped SQL, keyword/optional semantic path, candidate/context bounds and original hydration |
| TG-14–15 | [8.5 Query/provider execution](Client-Knowledge-Base-Solution-Architecture.md#85-query-execution-and-provider-output-contracts): typed plans/tools, routing order, progress/final states, bounded calls, actual documented Viktor transport and versioned skills |
| TG-16 | [7.6 Cache protocol](Client-Knowledge-Base-Solution-Architecture.md#76-cache-manifest-and-race-safe-publication): manifest/key, hit validation, safe publication/coalescing and deletion/expiry effects |
| TG-17–18 | [9.6 Work protocol](Client-Knowledge-Base-Solution-Architecture.md#96-durable-work-protocol-job-keys-and-proposed-schedules) plus 4.10 coverage: claims/fencing, job identities/timeouts/retries, real scheduling baseline, crash table and freshness allocations |
| TG-19–20 | Sections 7.5–7.6 and [9.7 Runbook](Client-Knowledge-Base-Solution-Architecture.md#97-operator-deployment-and-recovery-procedure): policy/expiry effects, protected restore/cutover, cache/access reconciliation and operational triggers |
| TG-21 | [11.5 Proposed gates](Client-Knowledge-Base-Solution-Architecture.md#115-proposed-initial-evaluation-and-performance-gates): initial fixture size, measurable retrieval/latency targets, mandatory invariants and ten-user workload |
| TG-22 | [A.4 Configuration](Client-Knowledge-Base-Solution-Architecture.md#a4-proposed-executable-configuration-shape) and [15.4 Workload calculator](Client-Knowledge-Base-Solution-Architecture.md#154-workload-based-calculation-to-implement): units/limits/owners, explicit required inputs and cost equations |

**Still genuinely conditional:** tested dependency pins, provisioned source/auth endpoints, provider-account capability and isolation tests, actual role/retention/business definitions, measured QA/capacity/costs, and hybrid/Viktor-led or chat-mode selection. Proposed defaults and interfaces make implementation concrete without misrepresenting those items as approved values or completed results.
