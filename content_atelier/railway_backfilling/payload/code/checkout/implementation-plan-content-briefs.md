# Content Atelier: implementation plan for researched content briefs

Prepared 12 October 2026. Status: approved plan; implementation increments 1–5 are now built and verified offline. The separate real pilot remains unexecuted. No real brief/approval or external model request was made. Only the additive full-text index migration was applied locally. See [implementation status](implementation-status-content-briefs.md). The inspection facts below describe the pre-implementation baseline.

The target is a human-approved angle becoming a source-grounded, historically informed production brief, followed by editing and approval at Gate 2. The first release ends at an approved brief. Pack generation and publication remain separate work.

## 1. Starting point and scope reconciliation

### Verified starting point

| Capability/data | Current state | Consequence for this work |
|---|---|---|
| PostgreSQL/pgvector | 13 tables, 30 foreign keys, 18 checks; two `vector(1536)` columns | Retain the approved compact data model |
| Original corpus | 20 transcripts and 8,456 mapped passages | Original text and exact source ranges can ground the brief |
| Transcript vectors | 136 Week 1 chunks and 193 Week 2 chunks, all embedded and provenance-verified | Reuse all 329 existing vectors; do not re-chunk or re-embed them for this release |
| Angle vectors | Six Week 1 and six Week 2 angles, all encoded | Reuse compatible signatures for previous-argument discovery |
| Moments | Seven accepted Week 1 moments and six validated Week 2 moments | Inherited angle evidence is already addressable; Week 1 extraction remains an accepted partial baseline |
| Approvals | All 12 angles remain `pending`; Week 2 is `comparison_review` | No current real angle can be treated as approved for a live brief |
| Briefs | Zero; `content_briefs` already exists | Add writers/services against this existing table |
| Retrieval | No hybrid service or full-text index | Build the retrieval service and its expression index |
| Meeting dates | All 20 `occurred_at` values are null | Assigned June week ranges cannot become meeting dates or factual recency |
| Execution | SQL leases, scoped workers, durable runs/jobs/events, operational artifacts | Extend this working execution path |
| External execution | Persistent switches false | Implement and verify offline first; later live pilots need a bounded authorized request packet |

The engineering plan and architecture describe a larger target: RQ/Redis, topics, moment/topic/brief vectors, new identity/configuration/dossier tables, additional connectors and a legacy-publication catalogue. This brief plan applies their research, writing and review requirements to the compact schema already approved in this chat. It does not claim those wider platform changes are implemented.

For this release:

- Retain 13 tables and two vector columns. No moment, topic, brief or asset vector is added.
- Retain SQL job leases. An eventual RQ transport can execute the same handlers without changing the brief/evidence contracts.
- Use typed research artifacts plus compact SQL references instead of a `research_dossiers` table.
- Keep model settings, feature flags, research budgets and the active brand bundle in configuration and version-controlled files; pin the actual consumed hashes in execution records.
- Use current external authentication. Add server-enforced capabilities for the new brief actions without copying an identity directory into SQL.
- Keep whole-week extraction, the accepted Luna baseline, historical comparison arithmetic, calibration prompts and existing source captures intact.
- Build an optional web-framing adapter behind a disabled flag. DataForSEO, Slack approvals, continuous ingestion, topics and the wider legacy-publication import are separate increments, not prerequisites for an internally grounded first brief.

This is an explicit scope adaptation of the broader documents. If the wider RQ/topics/schema redesign becomes the chosen release scope, its migrations and dependencies need a separate plan.

## 2. The approved-angle handoff

An approved angle is the governing editorial argument. The brief may explain it, qualify it, support it and give each format a useful reader job. It must not quietly substitute another argument, audience or CTA.

The input contract must include:

| Input | Reason it is required |
|---|---|
| Actual selected `angle_id`, current `content_hash` and `approved_hash` | Identify the exact approved revision, including a legitimate original/refinement family selection |
| Argument, audience, tension, take, mechanism, reader decision | Constrain the briefing to the approved contribution |
| Selected CTA | Preserve the human's commercial/engagement decision |
| Linked moment IDs and complete evidence references | Resolve factual grounding without relying on search ranking |
| Source assertions, inference, qualifiers and risks | Keep source facts separate from interpretation and preserve conditions |
| Approval actor/time, assessment/policy reference and approved steer | Explain why this revision was chosen and which direction the editor authorized |
| Source-use restrictions and actual attribution state | Prevent research permission from being mistaken for public-use clearance |

Use one backend approval-contract resolver shared by queuing, drafting and Gate 2. It must check that approval is current, the hash matches, the selected family member is authoritative, the actor was authorized, and the CTA is present. No browser-supplied `approved` flag is sufficient.

### Gate 1 remains a real prerequisite

The comparison workflow deliberately reports three cutoffs without choosing one. This plan must preserve that restriction until a human explicitly selects the approval policy. Building the brief path and completing synthetic end-to-end tests can proceed before that decision.

A separately enabled Gate 1 activation must:

1. Read an explicitly configured authoritative policy, defaulting to unset. Changing the displayed cutoff remains read-only.
2. Reuse the recorded family scenario and current grounding/quality/vector coverage; do not regenerate or choose a cutoff because it happens to yield more angles.
3. Authorize only the selected member of a family. A retained original may be valid even when an automatic refinement row exists; the existing unconditional latest-leaf lock cannot decide this case. Manual edits still invalidate the older candidate until reassessment.
4. Preserve `baseline_quality > 70`, strict historical boundaries and current-batch acknowledgement under the selected policy. This plan does not recalibrate the rubric or thresholds.
5. Bind the actual argument, evidence selection, CTA and steer to the approval contract and record the policy/assessment reference. Preserve legacy approval hash behavior through a versioned resolver rather than silently changing past hashes.
6. Commit the approval and first brief intent together. No synthetic approval or copied legacy angle may bypass comparison provenance.

Until policy activation is explicitly chosen, Week 2 cannot be approved through this new brief path. The development fixtures use legitimately approved synthetic angles in `atelier_test`.

### Atomic and idempotent trigger

On a valid approval, insert a `brief_generation` run and dependent jobs in the approval transaction. The initial intent key is based on the approved angle ID/hash and brief workflow version. Capture the configuration/brand/steer snapshot once on that intent; retries do not create a new first brief because a clock or configuration file changed.

Double approval requests either return the existing intent or a stale-hash conflict; neither creates a second first brief. Explicit regeneration/revision is a separate intent that names the existing brief, instructions and supplied-input hashes.

The HTTP decision returns immediately. No HTTP request waits for a model. A failed research or writing job leaves the angle approved and offers an explicit retry.

## 3. Durable execution stages

Introduce `approved_angle_brief_v1` independently of the existing angle workflows.

| Stage | Processing and supplied data | Durable output |
|---|---|---|
| `brief_prepare` | Validate approval; resolve inherited evidence; freeze brand, sources and allowed archive | Approval/input snapshot and original grounding packet |
| `brief_research` | Plan queries, resolve query vectors, hybrid search, context expansion, evidence grading and bounded gap rounds | Research audit plus compact typed dossier |
| `brief_context` | Join prior use, add optional external framing, compact the writer packet with coverage facts | Frozen writer input, prior-context summaries, unresolved gaps |
| `brief_writing` | One structured writing request against the frozen packet | Exact request, raw response and structurally validated draft artifact |
| `brief_validation` | Deterministic checks and scoped claim-support review; at most one repair and recheck | Validation findings and one saved real brief draft |
| Gate 2 | Edit, answer, revise, approve or reject the exact brief version | Superseding brief rows and hash-bound human decisions |

The research job exposes named substeps: planning, query encoding, semantic/lexical retrieval, restoring context, grading, gaps and coverage. Report actual queries/chunks/items processed. During model calls, show the step, elapsed time and heartbeat rather than an invented percentage.

Research/writing jobs target `angle_id`, since a brief does not exist yet. A saved `brief_id` is returned in `result_refs`. Revision jobs target `brief_id`; never set both scalar target columns, because `pipeline_jobs` allows at most one target. `content_briefs` has no `run_id` column; execution lineage is the generating job's `result_refs` and artifacts.

### Worker changes required by the actual code

- Dispatch brief scopes to a brief-specific input resolver before the weekly `SQLWorker.inputs()` rule. That existing resolver requires each transcript to belong to the run's week; supplemental Week 1 evidence for a Week 2 brief must instead be checked against the explicitly allowed archive.
- A brief's `week_id` remains its approved angle's week. Do not duplicate older transcripts into that week.
- Scope weekly-generation/reassessment mutex checks to their actual weekly run types. Multiple angle briefs may run independently in the same week; an unrelated brief must not block the entire weekly angle pipeline.
- Do not replace `weeks.active_run_id` with a per-angle brief run or overwrite `comparison_review` with a brief-research state.
- Make completion/waiting handlers scope-aware. The generic existing waiting branch writes `weeks.status='awaiting_embeddings'`; brief waits must affect the targeted run/jobs instead.
- After the draft is persisted, the brief run reaches `waiting_for_review`. Gate 2 approval/rejection ends that scope. Revision/regeneration jobs get their own intents, leases and progress.

## 4. Research route A: original grounding is always supplied

Resolve:

`content_angles -> angle_moments -> key_moments.evidence_refs -> transcripts.passage_map/original_text`

For every inherited moment, load all anchor, context and qualification references, including passages outside the initial quote. Validate parent source, passage ID, Unicode character ranges, exact text, source-use restrictions and actual attribution facts.

Include this grounding even when no search result retrieves it. The mandatory material includes conditions, uncertainty and material counterevidence. Deduplication may merge repeated locations but must retain their roles and moment relationships.

An original source quote is evidence of what the export records. It does not automatically verify who spoke, whether a reported result was measured, or permission to publish it. Current labels remain unverified unless an actual verification record is supplied.

For the compact contract, quote verification means a successful original-source binding. A selected supplemental passage can be verified without inventing a `key_moments` row or assuming a nonexistent `quote_verified` SQL column. `moment_id` is optional for such items, while transcript/passage/range references are mandatory.

If source evidence contradicts the approved argument, record the conflict and require an editorial decision. Do not manufacture evidence to protect a high angle score. Thin evidence may produce a narrow observation/teaching brief; a contradicted central claim returns to Gate 1 or remains blocked at Gate 2.

## 5. Research route B: supplemental hybrid retrieval

### Query planning

The planner receives the approved argument/mechanism/reader decision, inherited evidence, known gaps and allowed-source scope. It emits typed query intents across support, audience pain, objections, explanation, numbers, counterexamples and relevant previous coverage.

Start with eight targeted queries, within the documents' proposed 6–10 range. Allow at most two gap rounds and 12 unique queries overall. Each additional query must name an unresolved evidence need. Exhaustion becomes a recorded gap, not another loop.

### Query vectors and model compatibility

Encode the exact query strings with the configured compatible Small model only when that separate operation is authorized. Query vectors stay transient or in operational caches; they are not another SQL vector column or a new table.

Reuse a compatible existing angle vector for an initial argument-level seed search when appropriate. The focused query intents still need their own vectors; having 329 chunk vectors does not mean every new research query is already encoded.

Separate angle/chunk/query cache fingerprints by purpose. Check common semantic-space identity—requested model/approved alias, endpoint, dimension and synthetic/real mode—rather than requiring the angle, chunk and query profile digests to be equal. Their input contracts intentionally differ. Dimensions alone are insufficient.

Missing compatible vectors, changed inputs or unavailable query caches produce an explicit wait/failure. Replay never falls back to a provider, and semantic coverage cannot silently become lexical-only research. An explicitly requested limited-research mode would need its own visible contract; it is not the default first release.

### Candidate discovery

For each query, use the same eligible source IDs and confirmed filters in both branches:

1. Exact pgvector cosine retrieval, top 50 chunks.
2. PostgreSQL full-text retrieval over the same `chunk_text`, top 50 chunks.
3. Reciprocal Rank Fusion with initial equal method weights and `sum(1/(60+rank))`; one-based ranks and deterministic tie-breaking.
4. Restore original passage context, deduplicate overlapping locations and grade relevance/support/limits.

Rank fusion orders candidates for inspection. Neither cosine nor RRF is factual confidence. The angle novelty cutoffs 0.78/0.85/0.90 do not govern passage relevance. Do not directly add raw lexical and cosine scores.

Exact scans are appropriate for this initial 329-chunk corpus and preserve a useful reference for later retrieval evaluation. No HNSW index is needed in the first increment.

### Lexical and fuzzy support

Add an expression GIN index on `to_tsvector('english', chunk_text)` without a stored `tsvector` column. The query uses the matching explicit language configuration. Curated phrase/alias variants may come from the approved glossary; unknown spellings are not identities.

Optional `pg_trgm` support is confined to approximate term/name lookup when evaluation demonstrates a miss. It is not a fuzzy truth score or a replacement for semantic discovery. Keep exact source quotation validation unchanged; stable stored offsets normally make fuzzy quote recovery unnecessary.

### Restore context and grade items

For each hit, resolve `passage_refs` into originals. Add relevant neighboring turns and any linked moment's full qualification range. Apply a bounded context window, then extend for explicit qualifications when necessary; preserve the reason for each expansion.

Grade items as anchor/support, qualification, counterevidence, explanation/context or external framing. Record relevant claim scope, source status, attribution and permitted use. A team report cannot become an independently verified client testimonial. Overlapping captures of one call do not count as independent corroboration.

Aim for about 40 graded items in the writer packet. Mandatory original grounding and material contradictions are retained even if they exceed that target and still fit the request. Reduce weaker supplemental material first. If essential material cannot fit, fail preflight visibly rather than silently dropping it.

Existing filename headers and whole-turn boundaries remain unchanged. Retrieval-time context can add known date/role facts for reading; this does not pretend those facts were included in the embedding. The current absence of overlap is evaluated through retrieval tests before any later re-chunking proposal.

## 6. Research route C: prior content and intended difference

Use both routes, because each finds information the other can miss:

- **Reverse evidence lineage:** retrieved passage/range -> actually overlapping moment evidence -> `angle_moments` -> angle -> briefs -> assets/calendar. Sharing a meeting ID alone is insufficient.
- **Independent prior-argument retrieval:** exact cosine against compatible prior angle family signatures, followed by SQL enrichment into their actual saved brief/asset use. This finds related arguments from other transcripts.

Scan the entire eligible known angle archive at this scale. Five displayed comparisons are not a coverage limit. Retain relevant reverse-lineage matches even when they were outside the initial semantic display list. Collapse replay/refinement families without hiding substantive original/fallback records actually used.

Inspect the selected angle family's own prior use through exact SQL. Novelty self-exclusion must not hide that it previously produced content. Other current-week selected angles/briefs supply separately labelled sibling context, helping each brief keep its reader decision distinct.

Compact each relevant item into actual IDs, prior argument/audience/mechanism, evidence use, known generation/approval/publication state, known time and the proposed difference. Existing generated angles are editorial context, not factual proof or evidence of public publication.

Search/join actual previous brief message spines and saved asset text when available, including lexical checks for framing that parent-angle semantic retrieval could miss. No new brief/asset embedding is added. These paths initially have no real records and must report that fact.

The documents' four-month published-content review cannot currently be claimed complete: this schema has no imported legacy-publication catalogue and no confirmed publication records. Include known relevant older arguments rather than hiding them behind an unverified date filter. Report admitted-archive coverage separately from global publication coverage.

Authorized legacy examples can be supplied as labelled URL/excerpt context with known dates and provenance. Do not fabricate angle/moment/brief relationships for imported emails or carousels. A future dedicated import catalogue is a separate scope decision.

During validation, require the brief to state its actual new contribution: a supported mechanism, qualification, audience decision, counterpoint or application. Rewording a familiar hook is insufficient. A scoped claim-support/differentiation review and Gate 2 inspect this treatment; no uncalibrated brief cosine cutoff is invented.

History growth is different from source corruption. Pin the research snapshot/as-of facts and check included inputs for mutation. Do not invalidate every concurrent brief merely because an unrelated new row appears. Before Gate 2, refresh materially related prior-use/publication facts and show or block unresolved distinctness changes. Never silently alter an approved brief's saved context.

## 7. Dossier, coverage and context compaction

Define strict `EvidenceItem`, `PriorContentItem`, `Coverage`, `ResearchGap` and `ResearchDossier` contracts before prompts.

Every internal evidence item has a stable dossier-local ID, original source hashes/locations, optional moment/discovery chunk IDs, exact excerpt, evidence role, supported proposition, claim status, qualifications, attribution state and permitted-use state. Any summary is labelled as a summary rather than verbatim wording.

The dossier records all planned/executed queries, query-vector provenance, ranked hits and scores, grading decisions, rejected-item reasons, context expansions and gaps. Save the full audit in durable private operational artifacts. `pipeline_jobs.result_refs` holds its path/hash and compact actual references; it does not duplicate the archive.

Coverage must distinguish at least:

- Inherited evidence resolution and allowed source scope.
- Eligible/compatible chunk vector counts and completed semantic/lexical searches.
- Known angle-family coverage and sibling context.
- Confirmed internal publication coverage versus missing legacy archive.
- External research completed, disabled, unavailable or not needed.
- Material omissions caused by access restrictions or context budget.

An empty match list means completed research found no relevant items only when its coverage says so. It cannot disguise skipped research or unavailable vectors.

Reserve prompt space in order: approved argument/CTA and original grounding; qualifications/counterevidence; strongly related prior coverage; strong supplemental evidence; explicit gaps. Deduplicate overlapping passages/family summaries before trimming. Preserve material gaps and citations in the final packet.

Preflight the actual complete writer request against a brief-specific configured input/output budget. Do not change legacy angle settings or truncate essential context. Freeze the clock and all supplied hashes once; retries reuse the same packet.

## 8. Brand guidance, exemplars and external framing

### Brand bundle

Import the selected voice, strategy, CTA rules, banned phrases and two or three structural exemplars into a reviewed text bundle under a configured filesystem path. Pin source document hashes and the active bundle hash in each run. Load the selected guides whole as a stable writer prefix.

Resolve the two overlapping voice guides before a real pilot; do not let the model choose which conflicting instruction wins. The existing `editorial_policy.md` and prepared briefs can bootstrap offline contract tests, but they do not certify the final founder voice.

Exemplars demonstrate structure and treatment. Their quotations, numbers and client outcomes are not source evidence for the new angle. If a requested audience/pillar/funnel field is not supported by the approved angle or selected brand bundle, record a confirmation question instead of inventing it.

### External framing

Provide an optional bounded `WebResearchProvider` interface. It accepts sanitized topic/questions, not original transcripts or personal/client identifiers. Validate URLs, date/domain rules and returned citations. Save request/response/usage artifacts and cache by request/recency policy.

Default the feature to off during implementation. If enabled later, allow one brief-depth request and at most one explicit bounded retry, then continue with an unavailable label if it fails. It cannot repair missing internal evidence for a client/WIA claim. External fact claims need their own cited sources; they do not substantiate internal results.

DataForSEO/reranking remain optional future adapters. The first core brief must work with them off. Retrieval reranking is considered after an evaluation identifies useful misses.

## 9. The structured brief contract

Define `BriefDocumentV1` as the strict model-output contract. Expose its schema through OpenAPI and derive a frontend type. The server, not the writer, adds hashes, execution provenance, verification/approval state and validation findings.

| Section | Required production purpose |
|---|---|
| Assignment | Working title, approved angle statement, audience, objective, reader promise and supported/confirmed positioning |
| Why now | Known internal recency and dated external framing; explicitly unknown meeting dates stay unknown |
| Core insight and message spine | One central supported idea and 3–4 lines shared across formats |
| Audience pain | Source-grounded problem and language, with attribution limits |
| Narrative | Hook, problem, main point, transformation/reader decision and CTA direction |
| Evidence boundaries | Established observations, interpretations/hypotheses, excluded claims and scope conditions |
| Proof points/claims | Statements with evidence IDs, claim kind, source status, qualifications and structured numeric facts when relevant |
| Differentiation | Related previous/common framing and the supported new contribution |
| Voice | Confirmed perspective/tone/rules/avoidances from the pinned brand bundle |
| Format plan | Default one email, one eight-slide carousel and three distinct reels; each has a reader job, outline/beats and evidence links |
| CTA | Exactly the selected action/track/destination facts; elaborated wording cannot change the approved offer or invitation |
| Creative/accessibility | Treatment, required/illustrative assets, captions/alt text, privacy constraints |
| Distribution | Proposed role/sequence/adaptations without invented scheduling or publication facts |
| Evaluation | Meaningful audience-response signals; no invented numeric performance targets |
| Similarity review | Scope/as-of/completeness, related actual records and intended differences |
| Consent/open questions | Item-specific permission needs and required/optional questions |
| Sources/handoff checklist | Resolvable evidence references, source kinds and remaining production requirements |

These fields reconcile the architecture/roadmap with the richer prepared `ProductionBrief` examples, including creative direction, distribution, success signals and checklist. Format counts belong to the pinned brief template, not new configuration tables or pre-created asset rows.

Directions can include proposed hooks, email subject directions, slide plans and reel beats. This scope saves no finished pack, asset or calendar row. Every format develops the same approved contribution in a different useful way.

## 10. Writer, support checks and one repair

Use separately versioned prompts for research planning, evidence grading, writing, claim/differentiation review and repair. Do not overwrite calibration/angle prompts or reuse their responses for a brief.

The writer gets only the pinned brand/exemplar bundle, approved contract, selected original evidence, prior context and explicit gaps. Each call starts from that complete immutable packet, not a continuing chat whose hidden history might affect the result.

### Validation layers

1. **Structure:** required sections/types, unique evidence/claim IDs, allowed fields, nonempty meaningful directions, correct template counts.
2. **References:** every citation exists in the dossier, maps to an allowed original/URL, matches its source hash/range and retains its qualifications.
3. **Quote/attribution/use:** exact wording is original-bound; unknown identity/clearance is not marked verified/cleared. Public quotations, names and private screenshots require the actual permitted-use record.
4. **Numbers and status:** bind value/unit/timeframe/subject/population to the cited supporting fact. Mere number presence is insufficient. Reported/planned/estimated observations cannot become measured or causal results.
5. **Claim scope:** source assertions, inference, hypothesis, proposed action and external context are labelled. Inference cannot masquerade as observed proof.
6. **Editorial direction:** approved argument/audience/reader decision/CTA preserved; material contradictions addressed; no unintended move to another angle.
7. **Historical treatment:** meaningful differences are stated and tied to the available prior coverage; unknown publication coverage is not advertised as global novelty.
8. **Human readiness:** required questions and blocking findings remain visible; unverified facts cannot be cleared by the writer itself.

Deterministic reference/numeric rules cannot prove natural-language entailment. Add one bounded structured claim-support/differentiation review per draft, citing exact evidence IDs and scope changes. Human review remains necessary; a reviewer-model `pass` is not independent factual verification.

One automatic repair receives the exact failures plus the same approved/evidence packet. It may remove unsupported claims or narrow them, but cannot fabricate evidence, change the approved argument or start unbounded research. Re-run deterministic checks and, when relevant, the support review once.

A structurally valid draft with blocking content findings can be saved for correction with approval disabled. An unparseable response is an operational failure with raw artifacts, not a fabricated brief row. Thin evidence yields constrained claims/questions; changed fundamental direction returns to Gate 1.

### Explicit call accounting

The brief is a new workflow; the angle pipeline's three-chat-call test authorization does not cover it.

| Work | Initial path | Bounded maximum without external framing |
|---|---:|---:|
| Query planning | 1 structured call | 3 including two gap plans |
| Evidence grading | 1 structured call | 3 including two gap rounds |
| Writing | 1 structured call | 1 |
| Claim/differentiation review | 1 structured call | 2 if a repaired draft requires recheck |
| Repair | 0 or 1 | 1 |
| Total chat calls | 4 before any repair | 10 |
| Query embeddings | Initial batch, up to 10 strings | At most 12 unique queries over up to 3 rounds/batches |

These are proposed upper bounds, not a requirement to use every call. Stop gap work when needs are met. External framing, if authorized, has its own one-request/one-retry budget and billing record. Tests cover budget exhaustion and no provider fallback.

Use separately configurable research/writer/review models with the existing credential as an optional fallback, not a new required account. The configured Luna route is a development candidate, not a quality conclusion. Pin models/routing/output budgets for the later real pilot after the active brand bundle and exemplars are selected.

Record actual dispatches, cache reuse, tokens, provider-reported costs, stage/model and failure state in existing job/artifact records. Do not claim exactly-once billing if a paid response was lost; an uncertain attempt stops for explicit review/retry.

## 11. SQL storage, hashing and audit artifacts

| Existing field/store | Implementation contract |
|---|---|
| `content_briefs.angle_id`, `angle_input_hash` | Governing approved angle revision and actual consumed approval hash |
| `content_body` | Backend-owned envelope containing `schema_version`, `document`, review/answer/lock state and consumed provenance/validation references |
| `selected_evidence` | The selected original locations, hashes, evidence roles, excerpts/qualifications and labelled external references |
| `prior_content_context` | Compact actual prior arguments/use/publication states and intended differences, with real IDs when internal |
| `research_gaps` | Typed coverage/limitations/conflicts/omissions and unresolved research needs |
| `supersedes_id` | Actual replacement brief of the same logical assignment |
| Approval columns | Actor/time/hash-bound decision on that saved brief |
| `pipeline_runs.input_refs` | Approved input, workflow/configuration/model/brand references and source/archive scope |
| `pipeline_jobs` | Leases, steps/counts, idempotency, input hash and actual artifact/draft references |
| `pipeline_events` | Meaningful queue/research/writing/validation/review/retry milestones |
| Operational artifacts | Exact requests/responses, full retrieval audit, validated cache, dossier/packet and billing metadata |

No empty brief is created to represent researching. Its API state is derived from jobs until a structurally valid draft exists. Save the draft, selected evidence, prior context, gaps and generating-job reference atomically.

Canonical brief hashing covers the approved dependency and the actual document/claim/evidence/CTA/prior-context contract, including material answers and locks that affect revision. Server-owned review metadata is validated; the model cannot supply approval or a trusted verification flag. Freeze immutable consumed brand/evidence/policy snapshots separately from currently active configuration.

Full research artifacts must remain durable and access-controlled alongside SQL. Hashes and paths alone are insufficient if a deploy loses their files. Reuse the operational artifact interface with an explicitly retained volume/object-storage deployment path; moving this store later must preserve verified bytes and references.

### Minimal migration and exact catalog checks

Add only the required full-text expression index initially:

```sql
CREATE INDEX transcript_chunks_text_search_idx
  ON transcript_chunks USING gin (to_tsvector('english', chunk_text));
```

Keep the baseline SQL immutable. Introduce an explicit additive migration command with advisory locking and exact recognized before/after catalogs. The current `database.check()` compares the entire catalog, including indexes, so the migration, expected catalog, administrator setup and test checks must change together. A known baseline may be upgraded explicitly; an unknown/partial database fails visibly. Workers and APIs never run DDL.

This changes physical indexes, not the 13 tables or their two vector columns. Do not recreate the existing reverse `angle_moments(moment_id)` index. Add further brief/asset lookup or trigram indexes only for actual query predicates after measurement.

## 12. Gate 2, revisions and staleness

Build Gate 2 after the read-only draft contract works.

- **Edit:** `expected_hash` plus allowed field changes; row lock, source/claim checks, superseding brief, actor/event. Preserve exact evidence links and mark intentionally edited fields locked.
- **Answer:** save a typed answer and a new version. An editor's uncited factual answer is labelled context, not verified source proof. New factual support must enter the dossier and pass the same checks.
- **Refine:** queue a brief-targeted job with instructions and locked fields; retain locks unless the instruction explicitly names an authorized change. Same validations and one repair limit.
- **Add context:** accept selected authorized original evidence or labelled user context; validate references and refresh the dossier before revision. Never treat free text as verified internal proof.
- **Clearance:** accept an authorized, item-specific source-use decision with an actual permission reference, allowed scope and actor/time; save it on a new pending version. A free-text answer or a model's `public_candidate` label cannot grant permission. Existing upstream `use_restrictions` take precedence; changing a prohibition requires a separately authorized source-policy update and dependency recheck.
- **Approve:** current non-stale hash, authorized actor, no required unanswered question or blocking claim/use finding, and current evidence/dependency checks. Approval queues no pack work.
- **Reject:** recorded reason on the current version, with the action/event preserved. It does not rewrite the angle generation result.
- **Regenerate:** explicit new research/draft intent; keep the old brief readable and link replacements by the actual logical assignment.

Use `supersedes_id` and existing actor/time columns for version history. A displayed version number can be derived from the validated chain. No separate version table is required. Lock/check the parent and refuse a second child caused by concurrent edits; a stale edit returns 409 and the UI preserves unsaved changes.

Effective staleness includes changed/withdrawn angle approval or CTA/steer, a superseding governing angle, changed selected source/use facts, or invalid consumed evidence/provenance. New brand policy or materially relevant previous publication may require re-review. Do not rewrite the old approved row to make it appear to have consumed the new inputs. API `can_approve`/`can_consume` describes effective readiness; substantive corrections create a new pending version.

Warnings such as incomplete legacy-publication coverage may be acknowledged with an explicit scoped review decision and without claiming global novelty. Missing proof for a claimed result or disallowed public source use cannot be acknowledged away. Required questions are defined by these material conditions, not by every optional editorial preference.

## 13. API, proxy and real UI

All new routes retain private backend authorization, trusted actor forwarding and team-scoped source access. Derive canonical actor/capabilities from the trusted session/configured approver mapping; never accept a role/actor from the browser. The new approval capability defaults closed until configured. Do not add a duplicate user table or silently change legacy team behavior.

| Route (under `/storage`) | Purpose |
|---|---|
| `GET /angles/{id}/research` | Current intent, progress, dossier/coverage and findings |
| `POST /angles/{id}/brief` | Idempotent start/recovery for an already valid approved contract; never approves the angle |
| `POST /search` | Authorized archive discovery with explicit mode/coverage; no hidden provider call |
| `GET /briefs` | Paginated saved briefs with allowed week/status filters |
| `GET /briefs/{id}` | Document, evidence, prior context, findings, dependencies and server-derived readiness |
| `GET /briefs/{id}/export` | JSON with Markdown; browser downloads/copies it |
| `GET /briefs/{id}/versions` | Actual superseding chain and change provenance |
| `PATCH /briefs/{id}` | Hash-checked field edit |
| `POST /briefs/{id}/answers` | Typed answer/new version |
| `POST /briefs/{id}/refine` | Explicit revision job |
| `POST /briefs/{id}/context` | Validated selected evidence/user context |
| `POST /briefs/{id}/clearance` | Explicit hash-bound item-specific source-use decision and permission reference |
| `POST /briefs/{id}/decision` | Gate 2 approval/rejection |
| `POST /briefs/{id}/regenerate` | Explicit research regeneration |
| Existing job retry route | Resume the same failed/waiting intent with cache recovery |

The current Node proxy rejects all query strings and caps bodies at 64 KB. Add a closed route and filter allowlist for brief/search pagination, validate duplicate/unknown parameters, and forward them intentionally. Edits send changed fields; evidence selection sends IDs/locators. Raise a route-specific body limit only for a measured legitimate revision payload. Keep model work outside its HTTP timeout.

Implement a SQL-backed brief reader/editor and research panel, linked from the real angle view. Reuse presentation helpers through a typed `BriefDTO` adapter; do not attach a fixture `ContentIdea` to a real SQL angle. Render private source excerpts/citations, findings, prior coverage, questions, locks and versions. Unknown recording URLs are shown as unavailable, not invented links.

Replace timer-based brief creation for this real path with returned run/job progress. Gate 2 says `Approve brief`; it must not invoke the mock browser pack generator. Command Center remains the existing sign-in/launch boundary; this implementation adds no second Atelier screen there.

## 14. Concrete implementation increments and exit gates

| Increment | Backend/storage | UI/verification | Exit gate |
|---|---|---|---|
| 1. Contracts and input authority | Strict brief/evidence/dossier/coverage contracts; versioned approval resolver; cross-week source permissions; configuration/brand snapshot; scope-aware jobs | Typed API fixtures; approval/input-state explanations | A genuine approved synthetic angle resolves complete inherited evidence; pending/changed/unauthorized angles fail |
| 2. Retrieval | Explicit index migration/catalog handling; exact semantic plus full-text search; query cache/provenance; context expansion; reverse lineage | Search/research results with exact references and coverage; offline rank/filter tests | Known positive passages, qualifiers and counterexamples are reachable across weeks; no restricted evidence leaks |
| 3. Dossier and prior coverage | Bounded planner/grader/gaps; whole eligible prior-angle discovery and SQL enrichment; compaction; optional external adapter off | Dossier reader, real named steps; recorded omissions | A replay/synthetic run saves a reproducible dossier with original grounding and meaningful prior differences |
| 4. Draft and validation | Stage dispatch/cost/cache integration; structured writer; claim/differentiation review; one repair; atomic draft save | SQL brief reader, findings and Markdown export | Full offline workflow saves one grounded draft with traceable inputs; SQL-write recovery repeats no successful paid work |
| 5. Gate 2 and revisions | Hash-checked edits/answers/refine/context; locks; staleness; server capabilities and decisions | Brief editor/questions/versions/blocked states | Current valid versions can be approved; stale/unsupported/disallowed versions cannot; no packs are queued |
| 6. Rollout and live pilot | Explicit Gate 1 policy/approver setup and separately authorized bounded provider execution | Human retrieval/brief quality evaluation on representative real angles | One real approved angle yields a reviewed brief with actual usage, gaps and lineage recorded |

Implementation can complete increments 1–5 offline with current real data read-only and synthetic writes confined to `atelier_test`. Increment 6 requires the real approval/pilot choices; no live fallback is needed to certify the mechanics of increments 1–5.

Suggested modules: `briefs/contracts.py`, `briefs/inputs.py`, `briefs/workflow.py`, `briefs/research.py`, `briefs/context.py`, `briefs/writer.py`, `briefs/validation.py`, `briefs/gate_two.py`, `retrieval.py`, and the explicit index migration/CLI. Extend existing provider/stage-artifact/cache/cost infrastructure rather than adding a second execution framework. Add separately versioned brief prompts and protected API/proxy/UI types.

## 15. Verification and acceptance

Use the isolated `atelier_test` database with nonempty synthetic responses/vectors and an outbound-request guard. Real corpus reads remain read-only until a separately authorized pilot; never import fake output into `atelier`.

Required cases:

1. Initial approval and jobs are atomic; duplicate requests/retries create one initial intent. Pending comparison candidates cannot be laundered into approval.
2. Scenario-selected original fallbacks retain their complete original body/evidence/score, despite an automatic refinement child. Manual edits still invalidate old authority.
3. Original grounding survives low supplemental rank, context compaction and multiple transcript/moment links.
4. Cross-week evidence is allowed only within the authorized snapshot; source/role/date facts are not invented.
5. Semantic and lexical filters match; rank fusion handles one-sided hits, ties, empty searches and repeated passages. Missing/incompatible vectors produce an explicit incomplete state.
6. Query vectors have compatible semantic-space identity but distinct cache purposes; changing a displayed report/filter performs no hidden encoding.
7. Exact passage overlap finds prior uses, while independent angle search finds coverage from unrelated transcripts; own-family prior use and current siblings are not hidden.
8. Generated/approved/scheduled/published states are distinguished. Missing legacy archive is not `no previous content`.
9. Quotes retain wording/qualifiers and attribution limits. A correct number cited from an unrelated claim still fails support checks. Planned/reported results cannot become measured causal proof.
10. External/user-added material cannot impersonate internal verified proof. Named/public use requires actual scope clearance.
11. Template sections and each format's distinct reader job are present; CTA/approved direction remains exact.
12. One repair maximum; no repeated inference on semantic failure, provider timeout or cached replay. Raw-response/cache-to-SQL failures recover without overwriting originals.
13. Multiple briefs operate independently without replacing weekly state; lease loss, explicit retries, budget stops and stale upstream inputs remain visible.
14. Edits/answers create actual superseding versions; locks survive refinement; concurrent edits conflict without lost input. Backend and UI both deny invalid Gate 2 approval.
15. No fabricated empty research brief or downstream pack/asset/calendar row is created. Exports and deep links preserve source/brief lineage and access checks.
16. The recognized index migration is additive, guarded and reflected in the exact catalog. Old angle workflows, corpus/vector fingerprints, authentication/proxy behavior and calibration contracts regress cleanly.

Build a representative retrieval evaluation set of roughly 10–15 intents, including paraphrased queries, exact quantities, counterevidence, distant qualifications, duplicate captures and unknown speaker/date cases. Hand-label original passage ranges, not only the existing extracted moments. Report recall/rank and inspect missed qualifications before tuning top-k/weights or adding a reranker.

Offline tests establish mechanics. Real retrieval quality requires compatible real query vectors and editorial labels. After authorization, begin with one approved real angle; inspect the dossier before writing. Then compare three representative briefs against the prepared examples, recording factual scope, usefulness, voice, format distinction and prior-content treatment. Do not infer semantic accuracy from synthetic vectors, angle self-scores or the earlier chunk self-cosine checks.

Acceptance for this release: the product can take a legitimate approved angle into a reproducible dossier, validated saved brief and hash-bound Gate 2 decision; every material claim/evidence/prior-use relationship is inspectable; failures/retries are explicit; and no production pack is generated.

## 16. Inputs to settle before the real pilot

| Choice | Proposed treatment during implementation | Why it matters before live use |
|---|---|---|
| Authoritative angle policy | Unset; keep comparison approval blocked | A real approved Week 2 input does not yet exist |
| Active founder voice/strategy bundle | Configured reviewed files; fixture bundle offline | Avoid contradictory voice rules and invented positioning |
| Approver/editor capability mapping | Trusted external identity plus server configuration; new approvals default closed | Define who can clear questions and approve exact versions |
| Selected CTA/steer/template | Frozen explicit values, default prepared five-piece template | Writer needs an actual approved invitation and deliverable plan |
| Writer/research/review models and per-run budget | Configurable, no live calls; existing Luna route is a candidate | Pin actual routing/capability and validate quality before broader runs |
| External framing | Adapter built/tested but disabled | Core internal proof remains usable without web/DataForSEO |
| Legacy-publication review | Record incomplete coverage; accept labelled authorized examples | No four-month/global novelty claim without that archive |

These choices do not prevent implementing the contracts, retrieval, orchestration, UI and offline tests. They govern the later real approval and provider dispatch.

## References

- [Engineering plan, research/writing and Gate 2](backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md)
- [Roadmap and target brief contract](backend/docs/Content-Atelier-Implementation-Roadmap-Brief-Generation.md)
- [Solution architecture, sections 3.4–3.6 and 4.6](backend/docs/Content-Atelier-Solution-Architecture.md)
- [Approved compact evidence/prior-context design](research/briefing-provenance-and-prior-content-context.md)
- [Current storage implementation and real verification](backend/STORAGE.md)
- [Fresh chunk encoding/provenance report](backend/.storage-artifacts/verification/week1-week2-chunk-embedding-readiness.md)
- [PostgreSQL 17 full-text indexes](https://www.postgresql.org/docs/17/textsearch-indexes.html), [PostgreSQL 17 trigram matching](https://www.postgresql.org/docs/17/pgtrgm.html), [pgvector exact/approximate search](https://github.com/pgvector/pgvector).
