# Content Atelier — architecture comparison and reconciled design

Prepared 7 October 2026. Comparison of the supplied 4 October solution architecture with the user-confirmed editorial flow, the corpus review, and the existing application. This is a design recommendation, not implementation or deployment authorisation.

## 1. Decision

Keep the proposal's small, Postgres-centred Python backend. Its main infrastructure choices are suitable starting points for this workload: FastAPI, shared domain models, RQ/Redis, Postgres with relational/full-text/vector retrieval, private raw-file storage, and typed external adapters.

Revise the editorial and durability contracts before implementing it. The key changes are bounded snapshot ingestion, four-angle portfolio selection, a scoped claim ledger, three revision-bound human gates, explicit asset allocation, and independent drafting from the approved brief.

Preserve the existing React frontend and Command Center authentication. The supplied document allows React as an alternative, but its Jinja/HTMX dashboard and new Slack/Google sign-in are not the correct default for the application already built.

The controlling flow is the one the user has now confirmed:

**Batch ingestion → source normalisation → evidence and moments → candidate angles → four-angle portfolio → angle approval → research → brief approval → allocated asset generation → pack approval → production handoff.**

The attached proposal is material for comparison, not authority to override that flow. Its later scope options do not authorise new connectors, delegates, publishing, or infrastructure changes by themselves.

Sources: [supplied architecture][architecture], [corpus/editorial review][taste-review], [current frontend target][ui-spec], [existing authentication][auth-doc].

## 2. What is already strong in the proposal

Several decisions should remain:

- **One authoritative database.** Editorial state, evidence relationships, revisions, approvals, and work intent belong together in Postgres. Redis is delivery/execution infrastructure, not the only copy of a decision.
- **Three knowledge concerns.** Stable editorial policy, growing evidence, and content history need different retrieval and authority rules.
- **Moments rather than call summaries.** The useful unit is a decision, result, question, or teaching insight with provenance.
- **Hybrid retrieval.** Exact names/phrases, metadata, and semantic similarity serve different needs. A vector-only archive would lose important distinctions.
- **A bounded dossier.** Research should have a query/evidence budget, saved provenance, and a visible explanation of gaps.
- **Configurable formats.** Format rules and pack allocation should be explicit configuration rather than embedded in one generic prompt.
- **Human editing and locks.** Version history and protection of accepted fields directly match Whitney's repeated corrections.
- **Optional enrichment.** Provider failures should not fabricate data or block otherwise sound internal-evidence work.
- **Evaluation and cost records.** Record what changed, what was spent, and whether the output actually improved.
- **No autonomous publishing or extra orchestration platform.** The present workflow does not justify microservices per stage, a graph database, or an agent framework.

These strengths should be carried forward, not replaced by a new technology stack.

## 3. Comparison matrix

Section references below refer to the supplied architecture.

| Area | Supplied proposal | Reconciled recommendation | Why |
|---|---|---|---|
| Initial operation (§4.1–4.5) | Continuous polling/extraction, weekly cycle | One bounded batch/snapshot first; reuse connectors for later polling | Matches the newly confirmed initial flow and makes the exact evidence set auditable |
| Weekly result (§4.5) | 3–5 angles | Four-angle target; explicit shortage if evidence is insufficient | Four is the user requirement, not a reason to pad |
| Research placement (§4.5, §5) | Web enrichment before angle selection and after approval | Substantive research after Gate 1; pre-gate internal proof/history checks remain | Keeps Whitney selecting grounded directions before the larger research investment |
| Final review (§1.4, §6) | Two gates plus lightweight final review | Three enforceable gates; Gate 3 approves the exact pack | This is the confirmed workflow and the existing UI contract |
| Approver (§6.4) | Whitney or Giselle/delegate | Whitney by default; delegation only if explicitly approved later | Editor/handoff roles are not automatically approval authority |
| CTA (§6.3) | Suggested CTA preset in Slack | Suggested offer fit, blank deliberate CTA selection | Prevents a default being mistaken for Whitney's choice |
| Manual ideas (§6.4) | Approver-origin idea can go straight to brief | Same Gate 1 validation and explicit approval action | Manual origin is not permission, proof, or a CTA |
| Source inclusion (§4.2) | Exclude internal calls | Include configured WIA operational/editorial discussions; exclude engineering/vendor noise separately | The current four angles are partly supported by internal WIA discussions |
| Moment verification (§4.3) | Fuzzy quote match, role plausibility, numbers present | Separate text match, speaker confirmation, meaning, claim scope, and permission | A number or quote can be present and still be misleading |
| Pack writing (§4.7) | Anchor first, remaining assets conditioned on it | Each asset from the approved brief/claim set; set-level review afterwards | Avoids one draft's errors or cadence propagating through the pack |
| Reel variety (§4.7) | Distinct by hook | Distinct supported claim/decision/contribution | Different openings can still be the same reel three times |
| Pack quantity (§1.2, §10) | One whole pack per brief | Explicit weekly allocation across approved brief revisions | Avoids silently turning four angles into twenty core assets |
| Memory (§7.3) | Approved pack treated like published; same-topic work blocked | Separate in-progress reservations, approval, scheduling, actual publication, and argument overlap | Unpublished work is not audience exposure; one topic can support different useful angles |
| Freshness (§7.4) | External spike can lift cooldown | External change can trigger review, not refresh an unchanged claim automatically | Timeliness is not automatically a new argument or new WIA evidence |
| Jobs (§9.2) | Status, after-commit enqueue, Redis lookup, reconciliation | Transactional work intent, DB lease/fencing, revision-aware idempotency, reconciliation | Prevents duplicate execution and stale results, not merely lost enqueue |
| Frontend/auth (§2.4) | Jinja/HTMX and Slack/Google SSO | Existing React/Node boundary and Command Center identity | Preserve the work and integration already present |
| Retention (§4.2, §12) | Raw immutable; deleted Slack moments removed | Versioned active sources, tombstones, dependency invalidation, explicit purge/retention policy | Immutability is not a reason to retain revoked private material forever |

## 4. The system boundary to use

### 4.1 Infrastructure

Use the existing frontend service as the public UI/authentication boundary. Add a Python backend with:

1. **FastAPI API service:** domain commands, read models, approval service, and later Slack callbacks.
2. **RQ worker service:** ingestion, extraction, selection, research, generation, and checks.
3. **Scheduler/dispatcher:** initiates due work and reconciles persisted work intent.
4. **Postgres:** source/version metadata, claims, workflow, revisions, decisions, and work items.
5. **Redis:** queue transport and RQ execution metadata.
6. **Private object storage:** raw exports, transcripts, images, and other source bytes.

This is a modular application, not a microservice per stage. The API, worker, and scheduler share Python domain logic and schemas. The frontend remains TypeScript; “shared Pydantic models” does not mean React can consume Python classes directly. Use a versioned API contract and generated or checked TypeScript types.

Do not introduce a replacement dashboard merely to make the stack appear single-language.

### 4.2 Authentication and authorisation

The local authentication document records an existing Command Center session, Node login forwarding, and a one-use SSO handoff. It explicitly warns against starting an independent auth server. [Existing authentication][auth-doc]

Recommended boundary:

- Keep the existing UI/session flow.
- Expose Atelier API operations through a constrained same-origin path.
- Have the Python API obtain a verified principal through the established server-side session authority or an explicitly designed authenticated gateway contract.
- Do not trust browser-supplied email/role headers or private networking alone.
- Authorise every read/write against the backend's Atelier permissions.
- Map the existing broad account role to finer Atelier capabilities; “team” does not mean “may approve Whitney's pack.”
- Protect cookie-authenticated mutations against cross-site requests and replay.

The exact server-to-server verification mechanism needs an integration contract. It does not require a new user-facing sign-in provider.

### 4.3 Slack

Keep Slack as an attention and optional command surface, not a second state machine. For the initial ingestion/angles milestone, dashboard review is sufficient; one-tap Slack approvals can be a later slice.

If enabled, Slack actions must identify the exact revision and call the same domain service as dashboard actions. Replayed/stale clicks must not approve a newer brief.

Acknowledge Slack quickly, then report the committed result separately. The document's sequence puts database work and queue enqueue before acknowledgement; do not make external work part of that deadline. Slack explicitly recommends early acknowledgement within its three-second window. [Slack acknowledgement documentation](https://docs.slack.dev/tools/bolt-python/concepts/acknowledge/)

An acknowledgement means receipt, not completed approval. If the decision cannot be persisted, communicate failure; do not display “approved” because the callback was acknowledged.

## 5. Ingestion: the first milestone should close a snapshot

### 5.1 Separate four clocks

Store these independently:

- **Occurred time:** when the call/message/publication happened.
- **Observed time:** when the Atelier fetched it.
- **Source revision time:** when upstream content changed, if available.
- **Editorial cutoff:** the boundary for a specific weekly snapshot.

The document's “moments created since the last cycle” is ambiguous. After a backfill, hundreds of historical moments are created today. They must not all become this week's new events.

Late arrivals need an explicit policy: include them as late-arriving evidence in the next run, or deliberately reopen a snapshot. Never silently change an approved brief's source set.

WIA's editorial timezone remains configuration to confirm. The operator's Asia/Calcutta timezone is not evidence of WIA's weekly boundary.

### 5.2 Required entities

An ingestion run should record:

- Requested sources/hosts/channels and time window.
- Connector runs, page/checkpoint progress, and failures.
- Readable/missing/pending transcript or attachment states.
- Immutable source revision IDs and content hashes.
- Scope, configuration, normaliser, and extractor versions.
- The frozen source manifest.
- Completion policy and human acknowledgement of any reduced coverage.

A source snapshot is not just a cycle ID and settings JSON. It is a list of the exact source revisions used.

Allow complete, incomplete, and deliberately accepted partial coverage. Do not claim “all data ingested” because every configured connector returned HTTP success.

### 5.3 Idempotency and source revisions

Use stable source identity plus immutable revision history:

- One logical source document can have several revisions.
- Each processing/extraction result references its source revision.
- Reprocessing does not overwrite the evidence behind an approval.
- Duplicate Zoom/Fathom captures link to one conversation identity, but both original representations remain traceable.
- Repeated source export, overlapping transcript segment, and independently recurring client concern are three different relationships.

The document's key “document + pipeline version” is insufficient when that document changes but the code does not. Include the source revision/hash and relevant configuration versions.

### 5.4 Connector-specific edge cases

**Fathom:** the documented list filter uses created_at, not the meeting's occurrence time, and transcripts are available after processing. A watermark alone is insufficient: keep pending recording IDs and retry them, and use an overlapping reconciliation window. Verify host/share coverage rather than assuming one administrator key sees private calls. [List-meetings filters](https://developers.fathom.ai/api-reference/meetings/list-meetings) · [Fathom access and processing](https://developers.fathom.ai/faq)

**Slack:** preserve parent/reply identity and refresh known relevant threads. A reply to an old parent is not safely covered by polling only new top-level messages or rescanning the last fourteen days. Test the actual token/scopes/channel types and pagination; do not assume counts from a generic API table are guaranteed per response. [Thread retrieval](https://docs.slack.dev/reference/methods/conversations.replies/)

A missing message can reflect pagination, retention, permissions, or deletion. Do not automatically infer deletion from an incomplete poll. Explicit deletion handling and occasional authoritative reconciliation are separate concerns.

**Zoom:** treat cloud recordings and alternative transcript exports as adapter capabilities, not one universal source. Audit the actual already-exported material and access before provisioning a new backfill. An audio file without text remains a pending/unreadable source until an authorised transcription path succeeds.

**Manual/corpus inputs:** classify voice/strategy documents, published examples, operational evidence, draft chats, and analyst summaries separately. Do not index rejected assistant copy as a verified client event.

### 5.5 Source scope

The proposal's external/internal filter is too coarse for this corpus.

Useful WIA team discussions can contain campaign decisions, client requests, copy hypotheses, and operational trade-offs. This week's fair-comparison, testimonial, follow-up, and footage angles demonstrate that.

Use purpose plus configured series/channel scope:

- Client calls.
- Office hours and workshops.
- WIA client-performance or editorial/operations discussions.
- Product-engineering/vendor discussions, normally excluded.
- Prospect discussions only if explicitly in scope, with stricter handling.

Internal staff reports are valid evidence of what the team discussed. They are not direct client testimonials or verified performance outcomes.

## 6. The missing layer: a scoped claim ledger

The proposed moments ledger is necessary but not enough.

Three statements can contain the same number and have different truth conditions:

1. “The client reported $70,000 in bookings attributable to ads.”
2. “The business made $70,000.”
3. “Our ads generated $70,000 in profit.”

Only the first corresponds to the relevant corpus story's scope. Quote matching and checking whether 70,000 occurs in the dossier will not reject the other two.

### 6.1 Separate moment, claim, and editorial inference

- **Moment:** a meaningful source event or passage.
- **Claim:** a proposition that could appear in public copy, with its evidence and limits.
- **Editorial inference:** the principle or reader decision the moment helps explain.

A moment can support several claims. A claim can require several source spans. An editorial mechanism can be plausible without being an experimentally proven explanation of the client's results.

Use ordinary relational links for this; it does not require a graph database.

### 6.2 Claim fields

At minimum:

- Subject/client/account and period.
- Measure, unit, value, baseline, denominator.
- Attribution boundary and costs included.
- Reported/measured/estimated/derived/hypothetical status.
- Derivation, assumptions, qualifiers, and counterevidence.
- Exact supporting span IDs.
- Verification dimensions and current eligibility.
- Approved wording or permitted paraphrase boundaries.
- Explicit exclusions.

Check quantitative factual claims, not every numeral indiscriminately. Slide numbers, “three questions,” script-duration targets, and labelled hypothetical examples are not all client-result claims.

### 6.3 Verification must have multiple dimensions

The proposed 0.9 fuzzy match within ninety seconds can be a useful locator check after calibration. It is not a general “verified” flag.

Store independently:

1. Text found in source.
2. Timestamp/span accuracy.
3. Speaker identity confirmation.
4. Interpretation/context confirmation.
5. Measurement/derivation confirmation.
6. Public-use eligibility.

A fuzzy match can tolerate a changed negation or number. A quote that fails matching is **not automatically safe as a paraphrase**; it may be unsupported. Return to the actual span or withhold it.

OCR/vision output similarly needs original-image provenance and uncertainty. A model's extraction described as “word for word” does not make it exact.

### 6.4 Permission is not one ordered enum

The document's client consent values mix naming, quotation, and anonymisation. These are separate permissions.

Track at least naming, verbatim quote, result metric, screenshot, visual identity, paid-training excerpt, and scope/expiry/revocation. Track handling separately: omit name, blur account details, paraphrase, aggregate, or use an illustrative example.

Anonymising a name can leave a story identifiable. A public client post does not itself prove permission to reuse its screenshot. Permission for a quote does not automatically cover revenue figures.

Drafting and public handoff can have different permissions. A restricted internal preview may contain material that must be removed before Gate 3/handoff.

## 7. Knowledge and retrieval

### 7.1 Keep the three tiers, make their authority explicit

**Editorial policy bundle:** load the complete active, curated rules needed for that stage. This includes scoped founder corrections, current voice principles, CTA/offer ownership rules, and glossary. “Brand kit loaded whole” should not mean every historic email, rejected chat draft, and long example document.

**Evidence:** searchable source spans, moments, claims, related topics, and permission status.

**Content history:** proposals, decisions, brief/asset revisions, and actual publication records.

Choose a bounded exemplar set per format and job. The latest caption restrictions must not be defeated by a higher volume of older fragment-heavy examples.

### 7.2 Retrieval recipe

Keep hybrid search and topic expansion, then:

- Apply source/access eligibility before ranking.
- Search proof, audience language, Whitney's explanation, counterexamples, and prior coverage separately.
- Bring neighbouring turns for meaning.
- Deduplicate by conversation/event, not merely chunk ID.
- Include conflicting or limiting evidence deliberately.
- Record coverage and omission when the dossier budget truncates results.

A topic registry improves recall; it does not guarantee that every relevant moment was assigned correctly. “Read the whole archive” should mean search across the permitted archive with inspectable coverage, not promise all evidence fits into a forty-item dossier.

### 7.3 Embedding changes

Recording model ID is necessary but not sufficient. Queries and rows must use the same embedding-space version. Do not mix vectors from different models just because their dimensions match.

Re-embed into a separate version, evaluate retrieval, then switch the active version. Keep full-text and exact metadata independent of that migration.

Choose exact/vector-index strategies from measured corpus size and latency. The document's 100,000-row threshold is a starting heuristic, not an SLA guarantee.

### 7.4 External research

Move substantive web/SEO enrichment after Gate 1 in the initial implementation. Internal evidence and publication-memory checks remain before it.

Keep provider interfaces, sanitisation, cache, budgets, and honest unavailable states. Search demand should be optional directional context, not proof of resonance or a veto against an evergreen insight.

Separate pro-audience queries from couple-audience queries. Couple venue-search volume is not direct evidence that wedding business owners want a particular Instagram lesson.

Critically, use an isolated public-topic research context. Do not enable web search on a prompt containing the private brief, transcript, client quote, or full brand examples and assume a query sanitiser elsewhere protects it.

OpenRouter's ZDR controls apply to inference routing, not web plugins/tools and their separate retention policies. Enforce approved routing for private model calls and audit tool policies independently. [OpenRouter ZDR documentation](https://openrouter.ai/docs/guides/features/zdr)

Keep DataForSEO off initially unless explicitly chosen. An adapter seam is useful; building every enrichment endpoint is not necessary to prove ingestion and angle judgment.

## 8. Four-angle selection and content memory

### 8.1 Selection

Retain the document's hard proof/usability gates and evidence-backed scoring. Treat arithmetic as explainable aggregation, not objective truth: the underlying model scores still require calibration.

Replace hard “no two on the same topic” with central-argument comparison. Topic labels are broad and multi-purpose; two distinct buyer decisions can share one topic.

An angle signature should include:

- Audience/state.
- Tension.
- Belief shift.
- Mechanism.
- Primary proof/case.
- Reader decision.
- Editorial job.

Compare the set for shared mechanisms, promises, proof, hooks, and endings. Funnel/pillar/offer balance is a soft consideration. Add LeadLock or other offer fits only from current approved offer definitions.

For a small shortlist, evaluate several four-item combinations instead of relying only on a greedy top-score rule. Keep the selection explanation short and auditable.

If fewer than four pass, return an explicit shortage and credible approved backlog options. Human approval remains the selection authority.

### 8.2 Separate reservation from publication cooldown

Use distinct memory events:

- Proposed.
- Selected/angle-approved.
- Brief-approved.
- Pack-approved.
- Produced.
- Scheduled.
- Published.
- Withdrawn/discarded.

An active reservation can discourage duplicating work. A publication cooldown describes audience exposure. They are not the same clock.

“Passed: done before” should link to the prior work or store the founder's coverage assertion with its uncertainty. It should not invent a publication dated today.

Rejection reasons have scope: a poor treatment can be off-brand while the broader topic remains valuable.

### 8.3 Novelty

Embedding thresholds nominate pairs for review; they do not prove sameness. Shared vocabulary and fundamentals are normal in Whitney's work.

New evidence can warrant a revisit. So can a genuinely different reader decision or audience treatment. An external spike alone should not lift an unchanged angle's cooldown automatically.

Show known prior pieces and explain what is new. Disclose archive coverage. Mock/generated/scheduled records do not certify publication.

Import the supplied published examples before the first selection run. Manual publication recording is acceptable initially; automated import can wait.

## 9. The three gates and the generation contract

### Gate 1: the angle

Approve exact angle revision, evidence boundaries, steering, offer relevance, and deliberately chosen CTA/action.

Do not preselect a CTA in Slack or the dashboard. An approved reply prompt, resource link, or intentional no-explicit-ask mode should be representable without a fake sales URL.

Manual ideas go through the same checks. Whitney can explicitly approve a manually created idea through the same command; creation alone does not approve it.

### Gate 2: the brief

Approve exact brief revision with:

- Central insight, audience, objective, and message spine.
- Allowed claim IDs and excluded interpretations.
- Speaker/point of view.
- Offer ownership and chosen invitation.
- Essential questions resolved.
- Assigned asset contributions and feasible reel count.
- Source/asset handling and novelty limitations.
- Locked wording and production constraints.

Use the framework's functional main point. Do not force an identical “how we help” beat into every short clip.

### Asset allocation

The current documents conflict on one weekly pack versus one pack per angle. Keep the schema capable of explicit allocation:

- A weekly pack plan.
- Assets assigned to exact approved brief revisions.
- Optional angle bundles only if the production contract explicitly selects them.

Propose allocation during angle review, refine alongside briefs, freeze before generation. Do not let four selected angles automatically create four complete five-asset bundles.

### Generation

Write every assigned asset from the approved brief, permitted claim set, current policy bundle, selected exemplars, and CTA.

An approved lead asset may be additional context if Whitney chooses, but not a mandatory derivation chain. The later September record already superseded that mechanism.

Distinct reels require distinct supported points or decisions. Hook similarity is only one symptom. Allow fewer than three when evidence is thin.

Format specs are versioned configuration with trusted supported schemas and validators. Adding a completely new output type can still require renderer/export/validation work; “formats are data” is extensibility, not a promise that arbitrary new formats need no engineering.

### Gate 3: the final pack

Keep final approval a full domain gate, even if the UI feels lightweight.

Hard failures include unsupported/incorrect claims, prohibited disclosure, missing required speaker confirmation, wrong offer promise, unchosen CTA, stale brief/plan, and unresolved essential checks.

Warnings can cover non-blocking creative choices or incomplete optional enrichment. The document's “one repair, then show flags” must not allow hard factual/privacy failures to be accepted as ordinary warnings.

An authorised reviewer approves the exact asset versions and pack manifest. Production handoff uses that manifest.

Final rendered graphics/edited video still need production QA; copy approval is not publication.

## 10. Durability: tighten RQ without replacing it

### 10.1 Why the reconciliation idea is right but incomplete

After-commit enqueue plus a sweep can recover missed work. It does not by itself prevent:

- Two sweeps/workers generating the same output concurrently.
- A stale worker saving a result after the brief changes.
- A regenerated asset being skipped because the old idempotency key is finished.
- A failed job being retried forever.
- A dead scheduler never running the sweep.
- A provider completing a paid request before a worker loses its response.

Idempotency prevents duplicate logical effects. It does not detect missed schedules or guarantee exactly-once external billing.

### 10.2 Proposed minimum work model

Within the transaction that changes an editorial state, persist a work item:

- Operation and input fingerprint.
- Exact source/angle/brief/plan revision dependencies.
- Status, next attempt, attempt limit.
- Lease owner/expiry and fencing token.
- Output pointer, cancellation, and error category.

Dispatch ready work to RQ. The worker claims it in Postgres before expensive work. It renews the lease, persists checkpoints, and commits outputs only while its lease and expected input revisions remain valid.

Reconciliation reads Postgres due/leased states first. Redis job presence is an optimisation, not authority over whether the work was completed.

One work-item/outbox table plus a polling dispatcher is enough; no event broker or workflow platform is required.

### 10.3 Key design

Use logical idempotency fingerprints that include:

- Source processing: source revision + processing/config version.
- Extraction: source revision + extractor/policy version.
- Cycle selection: editorial cycle + snapshot + run revision.
- Brief: approved angle revision + research/policy input versions.
- Pack: approved brief assignments + plan/template/policy versions.
- Regeneration: explicit generation request + target asset/base revision.
- Notification: decision/event + target channel.

The ISO week alone prevents valid reruns from being distinguishable. Brief version plus format/index alone prevents an intentional regeneration of that same asset from being distinguishable.

Keep RQ IDs syntactically safe and separate from readable domain keys.

### 10.4 Scheduler and retries

RQ cron schedules recurring jobs, while delayed retries need the worker-side scheduler. The proposal configures Retry intervals but its worker command omits --with-scheduler. Include that capability explicitly; running rq cron is not a substitute. [RQ retry documentation](https://python-rq.org/docs/exceptions/)

RQ currently marks its cron scheduler beta. Pin and test the chosen version, timezone/DST behaviour, restart catch-up, and scheduler heartbeat. Do not assume another scheduling package is a drop-in configuration replacement. [RQ cron documentation](https://python-rq.org/docs/cron/)

Persist due periods and run a startup catch-up as well as scheduled reconciliation. Alert when scheduling stops; an unavailable scheduler cannot repair itself through a job it never enqueues.

### 10.5 Stale work, retries, and partial runs

- Source/claim/permission changes flag dependent artifacts.
- A changed brief invalidates affected pack approvals.
- A stale worker result can be retained as a historical attempt but cannot become the current approved artifact.
- Transient network errors can retry; invalid permissions/configuration and exhausted schema repairs need visible attention.
- External rate limits should delay/reschedule work rather than consume a worker indefinitely.
- Persist completed theme/asset results before assembling the set.
- Show a coverage-labelled partial result when allowed; do not silently drop failed themes or imply full completion.
- Cache successful external responses and reserve budgets before calls. A crash can still cause an ambiguous external-charge outcome; never promise no provider will charge twice.

### 10.6 Job isolation

Keep interactive, ordinary, and bulk work separate. Priority ordering alone does not guarantee that a long backfill will leave worker capacity for a brief. Reserve capacity for founder-facing work when load requires it.

Use bounded concurrency inside a macro-stage and save each result. The design does not need a job per sentence or retrieval hit, but it should not hide an entire weekly pipeline inside one unobservable thirty-minute task.

## 11. Security, deletion, and recovery

Store only the credentials required for configured sources; verify privileges using representative calls. Do not expand channel/call visibility merely because the proposal describes it.

Logs should record request fingerprints, input IDs, usage, errors, and policy decisions without private transcript bodies or token-bearing URLs by default. Tracing adds another disclosure surface and should remain optional.

Keeping stored state in Railway does not mean all processing stays there: model and research providers receive selected inputs. ZDR is a retention/routing control, not a data-residency guarantee. If no approved privacy/schema-compatible route is available, fail the private model stage visibly rather than relaxing those requirements through a fallback.

Raw revisions are immutable during ordinary processing, but deletion/permission revocation can require removing access or purging them. Propagate a dependency event to claims, dossiers, briefs, assets, cached model/research payloads, search indexes, and pending handoffs.

Use tombstones to prevent the next connector sync from reimporting withdrawn material. Reapply deletion/withdrawal records after restores. Record minimal audit facts without preserving the sensitive content being removed.

Do not infer confirmed deletion from an incomplete Slack poll. When a source's availability is uncertain, mark it appropriately and stop relying on it as current verified evidence.

Backups need a restore test with the chosen Postgres/pgvector image and storage configuration. Railway's documentation supports separate volume backups, PITR, and portable logical exports, but this must be enabled and tested for the actual deployment. [Railway backup guidance](https://docs.railway.com/guides/postgres-backups-restores) · [Railway PITR](https://docs.railway.com/volumes/point-in-time-recovery)

A pg_dump saved to the same Railway account/bucket is portable but not independent of that account. If recovery from account/project loss is required, arrange an approved separately controlled copy. Do not describe same-account storage as an offsite failure boundary.

## 12. Domain model additions

The document's table list is a good starting point. Add or refine these first-class entities:

| Entity | Responsibility |
|---|---|
| ingestion_run / connector_run | Scope, checkpoint, coverage, fetch progress, errors |
| source_revision | Immutable exact payload/version behind derived evidence |
| editorial_snapshot / snapshot_source | Frozen manifest of source revisions |
| claim / claim_evidence | Scoped public propositions, supporting spans, derivations, exclusions |
| permission_policy / permission_event | Independent usage dimensions, handling, revocation |
| angle_revision | Immutable argument and selection/steer dependencies |
| research_dossier_revision | Exact evidence/context gathered for an approved angle |
| brief_revision | Approved message spine, claim set, required questions, format assignment |
| pack_plan / plan_assignment | Weekly allocation across exact approved briefs |
| pack_revision / asset_revision | Exact generated/edited content and manifest |
| check_run | Hard/soft review result bound to artifact/input/policy revision |
| gate_decision | Actor, authority, exact revision, action, reason, channel |
| work_item / work_attempt | Durable intent, lease, retries, input fingerprint, output |
| publication_event | Actual channel/date/URL and evidence of use |
| withdrawal_event | Dependency invalidation and protection against reimport |

These can be combined where sensible; the requirement is the responsibility, not fifteen additional tables by decree.

Store critical identifiers, dates, statuses, and relationships relationally. Structured JSON is appropriate for editorial bodies and provider payloads, but should not hide revision/approval/permission rules inside arbitrary blobs.

Version configuration as well as copy: prompts, voice policy, offer definitions, format specs, templates, ranking rules, and model routing. Approval and generation records should identify the effective versions.

## 13. Evaluation changes

Keep the proposed golden examples and retrieval tests, but remove two assumptions:

1. The ten-week source must first be located and verified; “probably in the backfill” is not an acceptance fixture.
2. Its historical ranking must be tested against an as-of snapshot. If the published suite is already in current memory, rejecting it as recently covered may be the correct result.

Do not condition a test on the exact published answer and then treat similarity to that answer as proof of generalisation. Separate exemplar cases from held-out cases.

Evaluate:

- Ingestion coverage, late transcripts, edits, duplicate captures, old-thread replies.
- Scoped facts and wrong-speaker cases.
- Estimates, fee/media-spend comparisons, planned features, and anonymous identification.
- Relevant retrieval plus counterevidence and independent recurrence.
- Four-angle set distinctness and shortage handling.
- Latest caption rules and local-edit preservation.
- Three genuinely distinct reels, or honest reduction.
- CTA/offer ownership and all three revision-bound gates.
- Redis loss, duplicate delivery, worker death, stale outputs, and exhausted retries.
- Publication-memory separation and withdrawal propagation.

Model-family diversity in the critic is useful to evaluate, not a guarantee of independence or truth. Pin evaluated fallback routes too; an untested fallback can silently change both voice and factual behaviour.

Recorded input/output runs make the system auditable. They do not guarantee a future model call will reproduce identical prose.

## 14. Revised build sequence

| Milestone | Deliverable | Acceptance |
|---|---|---|
| M0 — Contract and existing-access audit | Source scope, business timezone, current corpus/import inventory, auth/API boundary, permissions, pack-allocation decision log | No guessed source coverage, delegated approval, or production volume |
| M1 — Batch snapshot | Source adapters/imports, raw revisions, normalisation, canonical conversation deduplication, pending/missing states, frozen manifest | Rerun without duplicate logical sources; late/failed sources visible |
| M2 — Evidence and retrieval | Segments, moments, scoped claims, permission handling, topics, hybrid search | Cases preserve subject/period/attribution and find related plus limiting evidence |
| M3 — Four-angle portfolio / Gate 1 | Candidate selection, memory, argument-overlap review, deliberate CTA selection, revision-bound approval | Grounded distinct set or honest shortage; no premature asset drafting |
| M4 — Research / brief / Gate 2 | Bounded dossier, current policy/offer retrieval, structured brief, locks and required questions | Approved exact brief supports the argument and assigned assets |
| M5 — Plan / pack / Gate 3 | Explicit allocation, independent generation, closed claim references, hard/soft checks, exact final approval | No fabricated result or stale approval; usable varied content |
| M6 — Handoff and operations | Approved manifest, production notes, publication recording, recovery drill, budgets and alerts | Handoff only after Gate 3; no autonomous publishing |

Durability and permission controls begin with M1, not as a last-minute hardening exercise. The initial user-facing outcome remains ingestion through four useful angles; later milestones should not delay proving that core.

Defer pre-angle web/SEO enrichment, Slack one-tap approvals, automated publication import, tracing, extra formats, and learning proposals until the core is calibrated. Capture edits and decisions immediately, but policy updates remain deliberate reviewed releases.

## 15. Decisions still needing confirmation

These do not block writing the ingestion contracts, but some block later generation:

1. Four complete angle-packs versus one weekly pack allocated across four angles.
2. WIA editorial timezone, source window, and cutoff.
3. Exact included hosts/channels/meeting purposes and current access.
4. Public-use/anonymous-use permission rules and withdrawal policy.
5. Current offer scope/ownership and approved CTA modes/destinations.
6. Carousel limits and the meaning of “up to three” reels for the chosen pack plan.
7. Whether Slack actions and any delegated approvals are actually wanted.
8. Whether DataForSEO is needed at the first research milestone.

Defaults recommended here: preserve existing auth, Whitney alone approves, initial batch operation, four-angle target, no CTA preselection, no padding, optional post-approval enrichment, and no autonomous publication.

## 16. Technical verification boundaries

This review checked decisive runtime/provider points against primary documentation: RQ cron and delayed retries; Fathom filters/access/processing; Slack thread retrieval and acknowledgement; OpenRouter ZDR; Railway backup/PITR guidance.

It did not revalidate every price, legal claim, vendor comparison, endpoint, or performance number in the supplied appendix. Treat those as dated proposal assumptions until tested or verified for the selected integration. The existing deployment guide is local product evidence, not a fresh verification of every Railway capability it mentions.

The main conclusion is architectural, not vendor-specific: **keep the infrastructure simple, but make evidence, revisions, approvals, and work recovery explicit enough to protect Whitney's judgment.**

[architecture]: <Content-Atelier-Solution-Architecture.md (outside the repository)>
[taste-review]: <../research/whitney-taste-and-editorial-pipeline.md>
[ui-spec]: <../frontend/Frontend-contentatelier.md>
[auth-doc]: <../frontend/AUTH.md>


