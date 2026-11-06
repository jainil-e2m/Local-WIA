# Content Atelier v2 — Ledger-to-Digest Upgrade

## Summary

Upgrade the existing Content Atelier rather than rewrite it. Preserve its strongest foundations—source ingestion, deterministic pre-filtering, verbatim verification, versioned prompts, model-call auditing, evidence claims, job idempotency, consent defaults, and the current BFF trust boundary—while replacing per-call gist delivery with this production workflow:

```text
Continuous capture
→ deterministic cleaning/classification
→ verifiable moment extraction
→ persistent moments ledger
→ cross-call clustering
→ eligibility
→ weighted ranking
→ manual 3–5 idea digest
→ Gate 1
→ research
→ brief
→ Gate 2
→ independent asset generation
→ automated checks
→ Gate 3
→ immutable in-app approved state
```

Decisions already locked:

- Content Atelier is the system of record; Slack only posts notifications and secure deep links.
- Whitney alone approves all three gates.
- Digest generation is manual during calibration.
- External research runs only after Gate 1.
- Gate 3 ends in an in-app `approved_ready` state; it creates nothing in GHL, Drive, Canva, or publishing systems.
- The first production pack contains one email, one 7–10-slide carousel, one to three reels, and long/short captions for social assets.
- Pass reasons and edit history are captured now, but no automated learning or prompt changes are included.
- The current backend is treated as pre-production, while migrations remain non-destructive.

## 1. Architecture and invariants

### Service boundaries

- Keep `content_atelier` as a standalone FastAPI/Postgres service with its own workers, model credentials, source credentials, and spend controls.
- Add a team-only `/api/content-atelier/*` BFF proxy to the Command Center. The browser sends its existing session cookie; the BFF injects the Atelier bearer token and authenticated `X-Atelier-Actor`.
- The Atelier service independently authorizes Whitney-only gate decisions using a required `ATELIER_WHITNEY_EMAIL`. Other team accounts may inspect sources, generate digest previews, edit unapproved briefs/assets, and run checks, but cannot approve gates.
- Register a private Slack review channel through `SLACK_REVIEW_CHANNEL_ID`. Slack receives “needs review” messages and app links only; it contains no approval buttons and never receives the content pack as a hand-off.
- Introduce numbered database migrations now. Baseline the current schema, enable `pgvector`, and stop relying on replaying one growing `schema.sql` for production evolution.

### Non-negotiable evidence rules

- Preserve every raw source before parsing or cleaning.
- Cleaning creates a separate searchable/model-facing representation; it never changes the verbatim source.
- Extracted quotes point to stable source segments and retain raw quote, timecode, speaker, attribution confidence, and source URL.
- Figures require scope as well as a source.
- Glossary correction annotates cleaned text but never silently rewrites quoted evidence.
- External research may inform hooks, framing, and audience language; it can never substantiate a WIA or client claim.
- Named-client use defaults to denied. An idea remains eligible only if it can be safely anonymized or the consent register explicitly allows naming.
- The model may suggest an offer, never a CTA. Whitney must choose the CTA at Gate 1.
- Prompts and scoring configurations remain versioned and reproducible. Feedback does not silently alter them.

## 2. Backend and data-flow changes

### Capture, cleaning, and source health

Implement these source paths:

- **Fathom:** webhook-first ingestion, plus nightly reconciliation for every configured per-user credential. Preserve test-event filtering, raw-body storage, recording-ID deduplication, and immediate webhook acknowledgement.
- **Zoom:** retain the existing one-time historical loader. Do not add a live Zoom webhook.
- **Slack:** poll the approved signal channels every 15 minutes, including threads and files. Store channel/message IDs, raw payload, permalink, author, timestamps, thread relationships, and file metadata. Do not use the Events API in this release.
- **Manual source:** retain transcript upload for podcasts, webinars, interviews, and other human-flagged material.
- Add a source-health API and UI showing last success, cursor, delay, last error, and credentials/hosts with missing coverage.

Cleaning/classification must:

- Materialize transcript segments with stable IDs, sequence, raw text, cleaned text, speaker, start/end time, and attribution quality.
- Apply WIA glossary replacements only to `cleaned_text`.
- Classify calls using Fathom calendar facts first, then frozen team roster/title rules, then an LLM only for unresolved cases.
- Exclude internal meetings and fragments before model work.
- Deduplicate Zoom/Fathom cutover overlap by recording/meeting identifiers when available, otherwise content hash plus time proximity.
- Treat Slack plain text as directly searchable. Treat OCR/vision output from files as `unverified_visual` until a person confirms it; unconfirmed OCR may corroborate an idea but cannot satisfy the hard proof gate.

### Pass A and the persistent moments ledger

Retain the existing unconditioned extraction principle: Pass A receives no voice guide, content strategy, novelty corpus, or scoring rubric.

Expand moment types to:

- praise
- result
- milestone
- soundbite
- teaching
- question
- objection
- story

Keep the model’s prompt-version-specific extraction output for audit, then promote only validated results into a canonical `atelier_moment` ledger.

Each canonical moment stores:

- Source pointer and stable source-span hash
- Raw quote and cleaned display text
- Source segment/timecode and source deep link
- Speaker and attribution confidence
- Moment type and extraction reason
- Proof state: `verified_text`, `verified_visual`, `unverified_visual`, or `paraphrase`
- Client, call type, date, and source metadata
- Consent/public-use status
- Extraction prompt/model-call provenance
- Search vector, embedding model/version, and lifecycle status
- Human labels, suppression reason, and whether it has supported an approved idea

Re-running a changed extraction prompt must not duplicate the same source span. New or materially different moments are added; prior extraction runs remain auditable.

### Search and clustering

Add a source archive index over transcript chunks, Slack text, moments, and published precedent:

- PostgreSQL full-text search for names, offers, exact terminology, and phrases
- `pgvector` embeddings for semantic similarity
- Reciprocal Rank Fusion over keyword and semantic results, with filters for date, source, client, call type, proof state, and consent state
- Default embedding model/dimension fixed in configuration and recorded on every row so future re-embedding is explicit

Manual digest generation uses:

- New eligible moments since the last notified digest
- Unresolved moments from the trailing 90 days
- Published precedent from the trailing 12 months for novelty
- No external demand data

Clustering procedure:

1. Retrieve semantic neighbors using cosine similarity, initially `>= 0.82`.
2. Build provisional groups from shared topics, offers, clients, and neighboring vectors.
3. Ask an editorial model to split or merge provisional groups and state one general principle per resulting idea.
4. Allow a strong singleton idea; recurrence is beneficial but never mandatory.
5. Prevent one moment from occupying two ideas in the same digest.
6. Persist the input moment IDs, prompt/config versions, grouping rationale, and primary/supporting evidence.

### Eligibility and editorial ranking

Move the current worthiness logic from call level to clustered-idea level.

An idea is ineligible when any of these fail:

- A one-sentence general principle exists.
- At least one primary proof item is exact, source-linked, and appropriately attributed.
- Every load-bearing figure has scope.
- The idea can be safely anonymized or consent permits the required identity.
- Positioning, capability, and ICP guards contain no `fatal` result.
- The cluster can support an email, a 7–10-slide carousel, and at least one complete reel without invention.
- The idea is not a repeat of recently published content.

`risk` guards remain eligible but travel into the digest, brief, checks, and final review as warnings.

Rank eligible ideas deterministically. The model returns a 0–5 score, one-line reason, and supporting evidence for each criterion; application code calculates:

```text
total score =
    audience pain × 30%
  + recurrence   × 25%
  + novelty      × 25%
  + offer fit    × 20%
```

Normalize to 0–100. Initial digest threshold is 65.

- Return no more than five ideas.
- Do not pad to three: zero, one, or two strong ideas is valid.
- Tie-break by proof confidence, then recency, then stable idea ID.
- Store all criterion scores, reasons, weights, prompt hashes, and the final computed score.
- Do not include SerpAPI demand in ranking during this release.

### Digest and Gate 1

Digest lifecycle:

```text
preview → notified → in_review → resolved
```

- Any authenticated team editor may create a manual preview.
- Preview generation is idempotent for the same moment snapshot, clustering configuration, and prompt versions.
- A team editor explicitly clicks “Send for review”; only then is one concise Slack notification posted to the private review channel.
- The notification contains digest date, idea count, short titles, and a secure deep link. It exposes no sensitive client evidence.
- Whitney reviews each item in Atelier.

Gate 1 supports:

- **Approve:** required CTA selection, optional steer, and optional title edit.
- **Pass:** required reason code—`off_brand`, `done_before`, `weak_proof`, `wrong_audience`, `not_now`, `consent`, or `other`—plus optional detail.
- **Request another look:** search instruction that may validly return no new evidence.

The UI may display the model-selected offer, but no CTA is preselected. Whitney chooses from the managed CTA catalog or enters a custom CTA with label and destination. Approval snapshots the idea revision, evidence, warnings, steer, offer, and CTA and enqueues research.

### Research and the one-page brief

For each Gate 1 approval, build an auditable research packet.

Internal research retrieves:

- Corroborating results from other calls
- Repeated audience questions and objections
- Whitney’s explanations of the topic
- Relevant Slack proof
- Prior coverage and published precedent
- Consent and attribution warnings

External research runs behind a `ResearchProvider` adapter using SerpAPI:

- Fixed recipes for Autocomplete, People Also Ask, related searches, Trends, and forum results
- Maximum 15 billable searches per approved idea
- Raw query, provider response metadata, timestamp, URL, and summarized finding stored
- SerpAPI failure or missing credentials produces `external_research_unavailable`; it never blocks the brief
- External findings are labeled as framing, never WIA/client proof

Generate a versioned `ContentBrief` containing:

- Core principle and insight
- Primary and corroborating proof with source links
- Audience pain in audience language
- Three-to-four-line message spine
- Unique role for the email, carousel, and each proposed reel
- Target reel count from one to three
- Whitney’s selected CTA
- Voice and point-of-view instruction
- Claims requiring permission or recording verification
- Handling warnings
- Required and optional open questions
- Internal and external research summaries

Gate 2 is blocked while required questions are unanswered. Whitney may edit, approve, or request changes. An approval freezes the exact brief revision and enqueues pack generation.

### Independent asset generation and checks

Generate every asset in a separate job from the same approved brief revision and brand kit. No asset receives another generated asset as context.

The pack contract is:

- **Email:** primary subject, subject alternatives, preview text, body, CTA label/link, and P.S.
- **Carousel:** 7–10 ordered slides with per-slide copy and design notes, plus long and short captions.
- **Reels:** one to three distinct scripts with hook, alternate hooks, timed sections, b-roll/on-screen guidance, production/handling notes, plus long and short captions for each.
- Exclude Stories, case studies, reel-cover titles, hashtags, and alt text in this release.

After generation, run:

1. **Factual checks — blocking**
   - Every quote and figure maps to approved evidence.
   - Figure text preserves scope.
   - No named client violates consent.
   - No external research is presented as client/WIA evidence.
2. **Structural checks — blocking**
   - Required assets and fields exist.
   - Carousel has 7–10 slides.
   - Reel count matches the brief and angles are distinct.
   - CTA exactly matches Whitney’s selected CTA.
   - Point of view and required captions are present.
3. **Voice checks**
   - Deterministically block banned vocabulary and known negative-contrast constructions.
   - Run an LLM critic against the founder guide and approved exemplars.
   - Automatically attempt at most two targeted repairs; unresolved subjective issues become warnings.
4. **Overlap checks**
   - Exclude the shared message spine and CTA, then compare asset similarity and repeated passages.
   - Exact paragraph reuse is blocking.
   - High semantic overlap is a warning requiring Whitney’s acknowledgement rather than an automatic rejection.

Store every check result with checker version, evidence, severity, and the asset revision it evaluated.

### Gate 3 and revision rules

Gate 3 is enabled only when:

- Every required asset exists.
- All blocking checks pass for the current revisions.
- Research and brief revisions are still current.
- Whitney has acknowledged any remaining warnings.

Whitney may edit assets in place before approval. An edit creates a new append-only asset revision and reruns affected checks.

Approval freezes the pack snapshot and sets:

```text
approved_ready
```

No Slack hand-off, Drive document, GHL draft, Canva action, publishing action, or downstream job is created. The approved pack remains readable and copyable inside Atelier.

Revision invalidation rules:

- Editing an approved Gate 1 idea, steer, or CTA makes its brief and pack stale and requires Gate 1 approval again.
- Editing an approved brief makes existing packs stale and requires Gate 2 approval again.
- Editing a pack invalidates only its current checks and Gate 3 approval.
- A Gate 3-approved pack is immutable. Further changes create a new pack revision requiring checks and Gate 3 approval.
- All gate decisions are append-only and retain actor, timestamp, revision, decision, reason, and complete approved snapshot.

## 3. Public interfaces and UI

### Database additions

Introduce versioned entities for:

- Transcript segments and glossary annotations
- Canonical moments and human labels
- Search chunks and embeddings
- Idea clusters, moment membership, eligibility evaluations, and score snapshots
- Digests and digest items
- Research runs/findings
- Briefs and brief revisions
- Packs, assets, and asset revisions
- Automated check results
- Gate decisions and feedback events
- Slack notification outbox

Extend jobs and model-call audit rows with `subject_type` and `subject_id` so work can belong to moments, ideas, briefs, packs, or assets rather than only calls.

Keep existing candidates, verdicts, and claims read-only for calibration and regression during the transition. Do not destructively drop them in this upgrade.

### API surface

Keep existing health, source, and call endpoints. Add:

```text
GET  /source-health
GET  /moments
GET  /moments/{id}
POST /moments/{id}/labels
POST /moments/{id}/confirm-visual-proof

POST /digests/preview
GET  /digests
GET  /digests/{id}
POST /digests/{id}/notify

GET  /ideas/{id}
POST /ideas/{id}/gate-1

GET  /ideas/{id}/research
GET  /briefs/{id}
PUT  /briefs/{id}
POST /briefs/{id}/gate-2

GET  /packs/{id}
PATCH /assets/{id}
POST /packs/{id}/checks
POST /packs/{id}/gate-3
```

Every state-changing request carries `expected_revision`. Return `409 revision_conflict` when another edit or approval won the race. Approvals and notifications also use idempotency keys so retries cannot duplicate decisions or Slack messages.

Generate TypeScript API types from FastAPI’s OpenAPI document in CI; the generated contract is committed and frontend compilation fails on drift.

### Content Atelier UI

Replace the fixture-driven candidate/steer/lead-asset workflow with four app views:

1. **Review**
   - Current digest and unresolved Gate 1 items
   - Briefs awaiting Gate 2
   - Packs awaiting Gate 3
2. **Moments**
   - Searchable ledger with source, quote, proof, consent, attribution, labels, and cluster history
3. **Ideas**
   - Digest history, ineligible/set-aside ideas, scores, reasons, and approved idea lineage
4. **Library & Sources**
   - Brand kit, precedent, CTA catalog, consent register, source coverage, ingestion health, and job failures

Add URL-addressable deep links for digest, idea, brief, pack, asset, and source moment. Slack links must survive refresh and open the correct gate.

Remove production dependence on fixture state including `leadAsset`, `scriptState`, local CTA state, local clearance state, and “derived from lead” behavior. Keep fixtures only in Storybook/test factories if still useful.

## 4. Delivery sequence and rollout

### Phase 1 — Foundation and moments ledger

- Introduce migrations, segment materialization, glossary annotations, source health, Fathom reconciliation, Slack polling, OCR verification state, embeddings, and hybrid search.
- Re-import the 150 Zoom transcripts and reproduce `78 client · 4 workshop · 61 internal · 7 fragment`.
- Backfill approved Slack channels and rerun expanded Pass A across all extractable sources.
- Ship the Moments and Library & Sources views before changing the reviewer flow.

### Phase 2 — Shadow clustering, eligibility, and digest

- Implement clustering, current worthiness guards at idea level, deterministic ranking, digest preview, pass reasons, and Gate 1.
- Replay historical windows and map the five known positive chains.
- Have Whitney label approximately 30 representative moments/ideas.
- Tune prompt/config versions against those labels without notifying Slack.
- Enable private-channel notifications only after the regression set meets acceptance criteria.

### Phase 3 — Research, brief, and Gate 2

- Add internal retrieval, the isolated SerpAPI adapter, research packets, brief generation/editing, open questions, revision invalidation, and Whitney-only Gate 2 approval.
- Verify the entire brief path still works with SerpAPI disabled or failing.

### Phase 4 — Pack, checks, and Gate 3

- Add independent asset generation, asset revisions, factual/structural/voice/overlap checks, bounded repair attempts, pack review, warning acknowledgement, and immutable Gate 3 approval.
- Keep the old fixture UI behind a temporary feature flag until one historical pack completes the new path.

### Phase 5 — Controlled production launch

- Run two manual shadow digests using live incoming material.
- Compare the top ideas and set-asides with Whitney before sending notifications.
- Enable live digest notification, still manually triggered.
- Do not introduce a weekly schedule until digest acceptance data shows the ranking is trusted.
- Retain legacy verdict tables and endpoints for one release, then plan their removal separately.

Operational metrics:

- Source lag and missing-host coverage
- Extraction and OCR verification failures
- Moments per source and duplicate rate
- Eligible/ineligible rates and fatal-guard reasons
- Digest size and Gate 1 approval/pass reasons
- Time spent at each gate
- Brief and asset revision counts
- Percentage of generated copy surviving human edits
- Check failure/warning rates
- Model and SerpAPI cost by idea/pack
- Job queue age, retry count, and terminal failures

Alert on source silence beyond expected cadence, terminal jobs, failed Slack notification, spend-ceiling pauses, and missing required Fathom credentials.

## 5. Test plan and acceptance criteria

### Deterministic and schema tests

- Raw source survives every cleaning/glossary operation unchanged.
- Zoom/Fathom cutover duplicates collapse to one source.
- Slack thread replies and files ingest once.
- Internal/fragment calls never enter Pass A.
- Candidate quotes must match source segments exactly.
- Re-running a prompt version is idempotent; a new prompt version remains auditable without duplicating canonical moments.
- Score calculation, threshold, tie-breaking, maximum-five behavior, and “do not pad” behavior are deterministic.
- Fatal guards exclude; risk guards propagate.
- Model-written CTA values are discarded.
- Consent defaults to unnamed and denied.
- Revision conflicts return 409 and do not overwrite newer work.
- Upstream edits correctly stale downstream revisions.

### Integration tests

- Fathom webhook and reconciliation deliver the same meeting once.
- Slack polling respects configured channels, pagination, rate limits, threads, file authentication, and retry behavior.
- BFF rejects unauthenticated/client-role access, overwrites spoofed actor headers, and forwards Whitney’s verified email.
- Manual digest preview is reproducible and notification retry posts only once.
- Gate 1 approval requires Whitney and a CTA; pass requires a reason.
- SerpAPI failure still produces an internal-only brief.
- Gate 2 cannot approve unresolved required questions.
- Assets are generated from the brief only and cannot read sibling drafts.
- Blocking checks prevent Gate 3; warnings require acknowledgement.
- Gate 3 produces only `approved_ready` and no external hand-off call.

### Golden and end-to-end tests

- Existing 27 backend tests continue passing.
- Historical import reproduces the four known classification totals.
- All five known positive source chains become eligible ideas in historical replay.
- Internal meetings yield no ideas.
- Hard-negative client calls mostly remain outside the digest with specific reasons.
- The “10 weeks” chain survives extraction, clustering, eligibility, ranking, research, brief, independent generation, checks, and all three gates with source lineage intact.
- A strong singleton idea can exceed the digest threshold without recurrence.
- A recurring but generic question fails if it has no distinct principle.
- A named client without consent is either safely anonymized or excluded.
- A scoped figure remains scoped in every generated asset.
- Frontend build, generated API types, component tests, gate-flow E2E tests, and accessibility checks pass.

Launch acceptance:

- Every digest item has verifiable proof and an inspectable eligibility/score explanation.
- No digest contains more than five ideas or padded weak ideas.
- No CTA is selected by AI.
- No asset contains an unsupported quote, figure, or client identity.
- Every final asset traces to the approved brief and evidence.
- No external system receives a pack after Gate 3.
- Whitney can complete every gate from a deep-linked app screen without using developer tooling.

## Assumptions

- The current backend has no production data that blocks additive migration or historical replay.
- Whitney’s login email will be supplied as deployment configuration.
- WIA will provide one private Slack review-channel ID and approve `chat:write`; interactive Slack scopes are unnecessary.
- The already collected voice documents, strategy material, emails, carousels, chats, Zoom transcripts, Slack corpus, offers, and precedent chains remain available for seeding and calibration.
- Manual digest generation remains the only cadence in this release; a business timezone is not needed until scheduled digests are approved later.
- Feedback events are retained for future analysis, but weights, prompts, and voice notes change only through an explicit later implementation and regression run.

## 6. File-by-file implementation map

This section is the implementation manifest. It distinguishes existing files that must change from new files that should be introduced. The division is intentional: existing modules retain their current responsibilities where they remain sound, while new workflow stages receive dedicated modules so `api.py`, `worker.py`, and `store.py` do not become monoliths.

### 6.1 Existing backend files to modify

| File | Required upgrade | Reliability implications |
|---|---|---|
| `content_atelier/backend/pyproject.toml` | Add Alembic, pgvector, embedding/search dependencies, Slack/SerpAPI HTTP client support, and CLI entry points for migrations, source polling, embedding backfill, historical replay, and digest generation. Add explicit dependency version ranges. | Locking dependency families prevents deployment drift; new CLI entry points make every backfill and replay repeatable. |
| `content_atelier/backend/.env.example` | Document Whitney identity, Slack token/channel/allowlist, SerpAPI key, embedding model/dimension, editorial/brief/generation/critic models, search thresholds, digest score threshold, source polling intervals, app deep-link base URL, and per-provider spend caps. | Startup validation must distinguish required production variables from optional degraded-mode integrations. No secret is exposed to the frontend. |
| `content_atelier/backend/Dockerfile` | Add migration/runtime assets and ensure the container runs as the existing unprivileged user. Do not run destructive migrations in the image build. | The image must be reproducible and contain every prompt/migration referenced by its hashes. |
| `content_atelier/backend/railway.json` | Add a release/migration command and keep the web process separate from worker execution if Railway services are split. | A failed migration must stop deployment before new application code serves traffic. |
| `content_atelier/backend/schema.sql` | Freeze as the documented pre-v2 baseline or reduce it to test-bootstrap compatibility. New production schema changes move to numbered migrations. | Prevents additive replay from silently masking failed renames, backfills, constraint changes, or vector-dimension changes. |
| `content_atelier/backend/atelier/config.py` | Add typed settings for all new identities, providers, model roles, thresholds, limits, poll intervals, deep-link origins, and feature flags. Add `require_*` methods and cross-field validation. | Invalid Whitney email, embedding dimension, Slack configuration, or production auth must fail at startup rather than during a gate decision. |
| `content_atelier/backend/atelier/db.py` | Add transaction helpers, migration-version checks, advisory-lock helpers for source polls/digest generation, vector adapters, pagination primitives, and test transaction support. | State transitions, approvals, notifications, and revision invalidation must commit atomically. |
| `content_atelier/backend/atelier/models.py` | Expand source, segment, moment, proof, idea, score, digest, CTA, research, brief, pack, asset, check, approval, and revision Pydantic models. Preserve strict structured-output schemas and validators. | The same models must define model JSON Schema, API validation, and persistence validation to prevent contract drift. |
| `content_atelier/backend/atelier/normalise.py` | Preserve raw input while producing stable segment IDs, millisecond time ranges, cleaned text, source URLs, and source-specific metadata. Add Zoom/Fathom cross-source identity hints. | Verbatim evidence continues to bind to raw text even when cleaned text is corrected for search/model comprehension. |
| `content_atelier/backend/atelier/prefilter.py` | Formalize rule precedence: source facts, frozen roster/title rules, then optional LLM fallback. Return explainable classification reasons and confidence. | Every excluded source must be auditable; no LLM fallback runs when deterministic evidence already resolves the class. |
| `content_atelier/backend/atelier/extract.py` | Extend Pass A moment types, require segment references, retain candidate audit rows, verify raw quotes, and promote validated outputs into the canonical moments ledger through a stable span hash. | Changed prompts can discover new moments without duplicating previously verified source spans. |
| `content_atelier/backend/atelier/context.py` | Split context assembly by task: eligibility, internal research, brief, generation, and critic. Add token budgets and explicit exclusions for each task. | Prevent cross-client contamination, external research becoming proof, and sibling assets entering generation context. |
| `content_atelier/backend/atelier/llm.py` | Support task-specific models, embeddings, structured retries, cost recording by subject, provider error classification, and zero-data-retention routing. | Retries remain bounded; every request/response/model/prompt/cost/latency remains auditable. |
| `content_atelier/backend/atelier/prompts.py` | Register and hash all new prompt files. Include scoring configuration hashes in digest reproducibility keys. | A prompt or scoring change creates a new auditable run rather than mutating old results. |
| `content_atelier/backend/atelier/jobs.py` | Generalize jobs from call-only work to `subject_type`/`subject_id`, add source-level and workflow jobs, strengthen idempotency keys, expose queue age/failure metrics, and retain stale-job recovery. | Every expensive or external action is retryable without duplicate model charges, approvals, or notifications. |
| `content_atelier/backend/atelier/worker.py` | Dispatch reconciliation, Slack polling, cleaning, moment promotion, embedding, clustering, eligibility, research, brief, asset, check, repair, and notification jobs. Separate continuous schedules from manual digest creation. | No scheduler callback performs expensive work inline; spend ceilings and concurrency limits apply by job class. |
| `content_atelier/backend/atelier/store.py` | Retain call persistence but delegate new domains to focused repositories. Add source-segment and canonical-moment primitives used across ingest/extraction. | Avoid one untestable data-access module while keeping shared transaction/deduplication behavior consistent. |
| `content_atelier/backend/atelier/triage.py` | Keep the current call-level verdict implementation as a legacy calibration path. Extract reusable principle, proof, novelty, sufficiency, and guard logic for idea-level eligibility. | Historical verdict regression remains available while production selection moves to clustered ideas. |
| `content_atelier/backend/atelier/api.py` | Compose routers for source health, moments, digests, ideas, research, briefs, packs, assets, checks, approvals, and library settings. Enforce Whitney-only approvals, expected revisions, idempotency, pagination, and consistent error envelopes. | Route handlers remain thin; authorization and state transitions are tested centrally rather than duplicated. |
| `content_atelier/backend/cli/backfill.py` | Materialize segments, calculate cross-source identity hints, enqueue expanded Pass A/embedding work, and keep the existing dry-run classification proof. | Re-running a backfill is safe and reproduces the known corpus counts. |
| `content_atelier/backend/cli/seed_corpus.py` | Seed the full brand kit, published precedent, offers, CTA catalog, glossary, consent defaults, and calibration-chain metadata with version/checksum reporting. | Seed operations become idempotent and report exactly what changed. |
| `content_atelier/backend/cli/run_triage.py` | Preserve legacy prompt calibration and add a clear deprecation note; historical v2 replay belongs in a separate CLI. | Prevents operators from mistaking legacy per-call verdicts for the production digest path. |
| `content_atelier/backend/prompts/extract-candidates.md` | Extend the unconditioned extraction taxonomy and require source-segment references without introducing strategy or voice criteria. | Recall expands without contaminating Pass A with editorial confirmation bias. |
| `content_atelier/backend/prompts/worthiness-and-gist.md` | Preserve as the legacy calibration prompt and source for reusable guard language; do not use it directly as the clustered-idea prompt. | Existing positive/negative fixtures continue to prove the old bar while the new prompt is independently versioned. |
| `content_atelier/backend/README.md` | Replace the gist-only operating guide with the v2 service topology, migrations, worker roles, CLI commands, degraded modes, and gate invariants. | An operator can run, repair, and verify the service without relying on undocumented knowledge. |
| `content_atelier/backend/PLAN.md` | Mark the original gist slice as completed/legacy and link to this implementation plan as the v2 source of record. | Prevents contradictory build instructions from remaining equally authoritative. |

### 6.2 New backend files to add

#### Migrations and persistence

| New file or directory | Responsibility |
|---|---|
| `content_atelier/backend/alembic.ini` | Alembic configuration using `DATABASE_URL` without storing credentials. |
| `content_atelier/backend/migrations/env.py` | Async migration environment, schema version checks, and safe offline SQL generation. |
| `content_atelier/backend/migrations/versions/0001_baseline.py` | Declare the existing schema as the migration baseline without recreating live objects. |
| `content_atelier/backend/migrations/versions/0002_ledger_digest_workflow.py` | Enable pgvector; add segments, glossary, moments, search chunks, ideas, evaluations, digests, research, briefs, packs, checks, approvals, feedback, and notification outbox; extend jobs/model calls. |
| `content_atelier/backend/migrations/versions/0003_backfill_v2_metadata.py` | Transactional metadata backfill and indexes. It must not call models or external APIs. |
| `content_atelier/backend/atelier/repositories/` | Focused repositories for moments, ideas, digests, research, briefs, packs, approvals, notifications, and library data. Each accepts an existing transaction when a multi-entity transition is required. |

#### Capture, cleaning, and search

| New file | Responsibility |
|---|---|
| `content_atelier/backend/atelier/glossary.py` | Apply versioned WIA term corrections to cleaned text while preserving raw spans and correction annotations. |
| `content_atelier/backend/atelier/fathom.py` | List meetings per credential, reconcile cursors/windows, normalize API/webhook parity, and enqueue missing calls. |
| `content_atelier/backend/atelier/slack.py` | Poll allowlisted channels, page history/replies, deduplicate replies, download authenticated files, record cursors, and enqueue text/vision processing. |
| `content_atelier/backend/atelier/vision.py` | Extract structured text from Slack images, persist bounding/source metadata, and require human confirmation before proof becomes verified. |
| `content_atelier/backend/atelier/moments.py` | Promote verified candidates, compute stable span hashes, manage labels/proof transitions, and enforce moment lifecycle rules. |
| `content_atelier/backend/atelier/embeddings.py` | Batch embeddings, model/dimension validation, re-embedding status, cost capture, and deterministic chunk/moment updates. |
| `content_atelier/backend/atelier/search.py` | Full-text/vector retrieval, Reciprocal Rank Fusion, metadata filtering, and evidence-safe result shapes. |

#### Editorial selection

| New file | Responsibility |
|---|---|
| `content_atelier/backend/atelier/clustering.py` | Build provisional similarity groups, call the editorial cluster prompt, support singletons, and persist cluster membership/rationale. |
| `content_atelier/backend/atelier/eligibility.py` | Apply principle, proof, scope, consent, positioning, capability, ICP, sufficiency, and novelty gates to idea revisions. |
| `content_atelier/backend/atelier/ranking.py` | Validate 0–5 criterion scores, calculate the fixed weighted total, threshold results, and apply deterministic tie-breaks. |
| `content_atelier/backend/atelier/digests.py` | Build idempotent manual previews, select at most five ideas, manage digest lifecycle, and resolve completion. |
| `content_atelier/backend/atelier/approvals.py` | Centralize Whitney authorization, state-transition validation, revision checks, immutable snapshots, warning acknowledgement, and downstream staleness. |
| `content_atelier/backend/atelier/notifications.py` | Render minimal Slack review messages, write through an outbox, deduplicate retries, and construct secure app deep links. |

#### Research, briefing, and generation

| New file or directory | Responsibility |
|---|---|
| `content_atelier/backend/atelier/research/base.py` | Define provider-neutral queries, findings, provenance, cost, and degraded-mode contracts. |
| `content_atelier/backend/atelier/research/internal.py` | Retrieve corroboration, pain language, Whitney explanations, Slack proof, consent, and precedent through the hybrid search layer. |
| `content_atelier/backend/atelier/research/serpapi.py` | Execute fixed SerpAPI recipes with a 15-search cap, normalize results, and fail open to internal-only research. |
| `content_atelier/backend/atelier/briefs.py` | Assemble/generate versioned briefs, validate required questions and format roles, and manage Gate 2 edits. |
| `content_atelier/backend/atelier/generation.py` | Create independent email/carousel/reel jobs from one approved brief without exposing sibling outputs. |
| `content_atelier/backend/atelier/checks/factual.py` | Bind claims to evidence, preserve figure scope, enforce consent, and reject external research used as proof. |
| `content_atelier/backend/atelier/checks/structural.py` | Enforce pack schemas, slide/reel counts, CTA identity, POV, captions, and required fields deterministically. |
| `content_atelier/backend/atelier/checks/voice.py` | Enforce deterministic voice prohibitions, run the voice critic, and produce targeted bounded repair instructions. |
| `content_atelier/backend/atelier/checks/overlap.py` | Detect exact paragraph reuse and semantic redundancy after excluding approved shared language. |
| `content_atelier/backend/atelier/checks/service.py` | Orchestrate check versions, severities, current-revision validation, repairs, and Gate 3 readiness. |
| `content_atelier/backend/atelier/metrics.py` | Produce source, queue, workflow, quality, and spend metrics without logging sensitive content. |

#### API routers and CLIs

| New file or directory | Responsibility |
|---|---|
| `content_atelier/backend/atelier/routers/` | Separate source-health, moments, digests, ideas, briefs, packs, approvals, and library routes while reusing the existing auth dependency. |
| `content_atelier/backend/cli/poll_sources.py` | Safely run one Fathom/Slack reconciliation pass for operations and debugging. |
| `content_atelier/backend/cli/backfill_embeddings.py` | Estimate and execute chunk/moment embeddings with resumable progress and spend confirmation. |
| `content_atelier/backend/cli/replay_editorial.py` | Replay historical windows through clustering/eligibility/ranking, diff configurations, and emit machine-readable calibration reports. |
| `content_atelier/backend/cli/generate_digest.py` | Create a digest preview from the command line without sending Slack notifications. |

#### New prompt files

All prompts remain static, byte-for-byte hashed files. Task data is always a separate user message.

| New prompt | Purpose |
|---|---|
| `content_atelier/backend/prompts/cluster-moments.md` | Merge/split provisional groups and state the shared principle without ranking them. |
| `content_atelier/backend/prompts/evaluate-idea.md` | Return eligibility tests, guards, 0–5 score components, explanations, evidence IDs, and offer suggestion—but never a CTA. |
| `content_atelier/backend/prompts/research-plan.md` | Select bounded internal and external research questions after Gate 1. |
| `content_atelier/backend/prompts/content-brief.md` | Produce the one-page brief contract from approved idea, research, brand kit, steer, and human CTA. |
| `content_atelier/backend/prompts/generate-email.md` | Produce the structured email asset only. |
| `content_atelier/backend/prompts/generate-carousel.md` | Produce the structured 7–10-slide carousel and two captions only. |
| `content_atelier/backend/prompts/generate-reel.md` | Produce one reel angle/script and its two captions; one invocation per approved angle. |
| `content_atelier/backend/prompts/voice-critic.md` | Identify brand/AI-tell violations with exact spans and repair instructions. |
| `content_atelier/backend/prompts/overlap-critic.md` | Judge whether pieces repeat rather than reinforce the approved message spine. |

### 6.3 Existing Command Center files to modify

| File | Required upgrade | Reliability implications |
|---|---|---|
| `frontend/server/index.mjs` | Register the team-only Content Atelier proxy, configuration validation, request-size limits, actor injection, allowed methods, timeout/abort behavior, and structured proxy logs. Prefer delegating the implementation to a new proxy module rather than enlarging `index.mjs` further. | The browser never receives upstream URL/token and cannot spoof the approving actor. |
| `frontend/server/package.json` and `frontend/server/package-lock.json` | Add only dependencies required by the extracted proxy tests, if any; prefer existing platform APIs. | Server dependency changes remain locked and independently testable. |
| `frontend/.env.example` | Add server-only `CONTENT_ATELIER_URL`, `CONTENT_ATELIER_API_TOKEN`, and optional timeout configuration; document the frontend feature flag separately. | Prevent accidental `VITE_` exposure of secrets. |
| `frontend/package.json` and `frontend/package-lock.json` | Add OpenAPI type generation, Content Atelier contract verification, and browser E2E scripts. Add Playwright only if selected for the gate-flow E2E suite. | CI gains explicit contract/build/test entry points instead of relying on developer convention. |
| `frontend/src/pages/OpsHubPage.tsx` | Resolve Content Atelier deep-link query parameters and render the new server-backed screen without affecting other Ops Hub screens. | Slack links survive refresh and browser navigation. |
| `frontend/src/components/opshub/screens/ContentAtelierScreen.tsx` | Replace fixture/local-state workflow with loading/error/empty states and the four v2 views. Decompose detailed views into dedicated Atelier components. | Avoid one oversized component and ensure every mutation reflects server-confirmed state. |
| `frontend/src/data/contentAtelier.ts` | Remove production fixture ownership. Move reusable examples to test factories; retain only presentation metadata that is genuinely static, if any. | Production can no longer silently fall back to persuasive but fake content. |
| `frontend/src/hooks/useOpsHub.ts` | Remove `setCandidate`, `setSteer`, `setScript`, `setCta`, `setLeadAsset`, `setClearance`, and `stageContent` from production flow. Delegate server work to a new Atelier hook/API service. | Eliminates split-brain local state that diverges after refresh or concurrent edits. |
| `frontend/src/lib/opsHub.ts` | Remove obsolete Atelier state fields and add typed URL/deep-link parsing where it belongs. | Gate state is no longer duplicated in the global demo state. |
| `frontend/src/components/opshub/screens/HomeScreen.tsx` | Replace fixture-derived Content Atelier counts with API-backed review/source-health summaries and safe unavailable states. | Home-screen counts cannot disagree with the Atelier queue. |
| `frontend/src/components/opshub/OpsHubShell.tsx` | Preserve navigation while adding current review counts and deep-linked tab selection without exposing restricted actions to client-role accounts. | Navigation and authorization remain consistent across direct and in-app entry. |
| `frontend/Content_Atelier.md` | Reconcile the source-of-record specification with ledger/digest/three-gate decisions and mark superseded lead-asset language clearly. | Future product work reads one coherent specification. |
| `frontend/wia_resource_mapping.md` | Update collected-source status, runtime ownership, seed paths, live integrations, and calibration fixtures. | Prevents corpus/tooling state from drifting away from implementation reality. |
| `frontend/DEPLOY.md` | Document two-service deployment, BFF variables, Whitney identity, Slack review channel, migrations, worker process, health checks, and rollback. | Operators can deploy and roll back without exposing secrets or skipping migrations. |

### 6.4 New Command Center files to add

| New file | Responsibility |
|---|---|
| `frontend/server/content-atelier-proxy.mjs` | A dedicated authenticated proxy that allowlists paths/methods, injects bearer/actor headers, forwards JSON safely, supports request IDs, and never forwards browser-supplied authorization headers. |
| `frontend/src/services/api/contentAtelier.ts` | Typed browser API for source health, moments, digests, ideas, briefs, assets, checks, and gates using the same-origin BFF. |
| `frontend/src/services/api/contentAtelier.generated.ts` | Generated OpenAPI types; never hand-edited. |
| `frontend/src/hooks/useContentAtelier.ts` | Server-backed query/mutation state, abort handling, refresh after mutations, revision-conflict recovery, and stable user-facing errors. |
| `frontend/src/components/opshub/atelier/ReviewView.tsx` | Unified Gate 1/Gate 2/Gate 3 queue and manual digest-preview controls. |
| `frontend/src/components/opshub/atelier/MomentsView.tsx` | Search/filter ledger, proof confirmation, source inspection, labels, and cluster usage. |
| `frontend/src/components/opshub/atelier/IdeasView.tsx` | Digest history, scores, eligibility explanations, set-asides, and lineage. |
| `frontend/src/components/opshub/atelier/LibrarySourcesView.tsx` | Brand kit, precedent, CTA catalog, consent register, source health, and failed jobs. |
| `frontend/src/components/opshub/atelier/IdeaGate.tsx` | Gate 1 proof/score review, CTA selection, steer, pass reasons, and re-search instruction. |
| `frontend/src/components/opshub/atelier/BriefEditor.tsx` | Version-aware one-page brief editing, research/evidence panels, questions, and Gate 2. |
| `frontend/src/components/opshub/atelier/PackReview.tsx` | Asset navigation, revisions, checks, warning acknowledgement, copy actions, and Gate 3. |
| `frontend/src/components/opshub/atelier/EvidenceLink.tsx` | Consistent source, timecode, attribution, proof, consent, and scope rendering. |
| `frontend/src/components/opshub/atelier/RevisionConflict.tsx` | Explain stale edits and reload/compare options after a 409 without overwriting another user. |
| `frontend/src/test/factories/contentAtelier.ts` | Typed UI/test fixtures replacing production fixture data. |

## 7. Test files to modify and create

Testing must prove deterministic invariants separately from model quality. A model-facing test may validate schema, grounding, fixture outcomes, or bounded behavior; it must not depend on exact creative wording unless the wording is an explicit prohibition.

### 7.1 Existing backend test files to modify

| Test file | Additions |
|---|---|
| `content_atelier/backend/tests/test_prefilter.py` | Stable segment/classification reasons, Fathom fact precedence, roster fallback, unresolved LLM fallback contract, and guarantee that internal/fragments never enqueue Pass A. Keep real-corpus count assertions. |
| `content_atelier/backend/tests/test_schema.py` | New Pydantic strict schemas, CTA stripping, proof-state validation, score bounds, brief/asset contracts, revision fields, and OpenAPI schema compatibility. |
| `content_atelier/backend/tests/test_verdict.py` | Preserve legacy `derive_worthy` regression and add parity tests showing clustered eligibility reuses principle/evidence/novelty/sufficiency/guard semantics correctly. |

### 7.2 New backend unit and integration tests

| New test file | Reliability, robustness, and accuracy coverage |
|---|---|
| `content_atelier/backend/tests/test_migrations.py` | Fresh upgrade, baseline adoption, repeat migration, pgvector availability, constraint/index presence, and downgrade/rollback policy validation. |
| `content_atelier/backend/tests/test_config.py` | Required production values, malformed identities/URLs/dimensions, optional SerpAPI degradation, and secret-safe error messages. |
| `content_atelier/backend/tests/test_normalise_v2.py` | Stable segment IDs, raw/clean separation, time conversion, source links, Unicode/whitespace edge cases, and duplicate identity hints. |
| `content_atelier/backend/tests/test_glossary.py` | Longest-match behavior, case handling, correction annotations, no mutation of raw quote, overlapping terms, and glossary versioning. |
| `content_atelier/backend/tests/test_fathom_reconciliation.py` | Webhook/poll parity, test-event omission semantics, pagination, per-user cursor isolation, private-call coverage, retry, and recording-ID idempotency. |
| `content_atelier/backend/tests/test_slack_ingest.py` | Allowlist enforcement, history pagination, threads, duplicate reply trap, file HTML-login trap, rate limiting, cursor recovery, and idempotent re-polls. |
| `content_atelier/backend/tests/test_vision.py` | OCR output storage, file/source provenance, unverified default, human confirmation transition, and prohibition on unverified proof satisfying eligibility. |
| `content_atelier/backend/tests/test_moments.py` | Source-span hashing, verbatim enforcement, promotion/deduplication across prompt versions, labels, proof transitions, suppression, and consumed/reusable lifecycle. |
| `content_atelier/backend/tests/test_embeddings.py` | Batch/idempotent embedding, model/dimension mismatch, partial retry, re-embedding version behavior, and spend cap. |
| `content_atelier/backend/tests/test_search.py` | Full-text exact matches, semantic matches, Reciprocal Rank Fusion, filters, stable ordering, consent/proof filtering, and cross-client isolation. |
| `content_atelier/backend/tests/test_clustering.py` | Threshold boundaries, transitive grouping, split/merge schema, singleton preservation, no duplicate moment per digest, and reproducible membership from the same snapshot. |
| `content_atelier/backend/tests/test_eligibility.py` | Every hard gate independently, fatal versus risk guards, anonymization, scoped figures, minimum pack sufficiency, repeat detection, and precise rejection reasons. |
| `content_atelier/backend/tests/test_ranking.py` | Weight arithmetic, normalization, threshold 65, tie-break order, zero recurrence singleton, maximum five, no padding, and invalid model scores. |
| `content_atelier/backend/tests/test_digests.py` | 90-day backlog window, since-last-notification window, idempotent previews, lifecycle transitions, concurrent generation lock, and unresolved idea handling. |
| `content_atelier/backend/tests/test_notifications.py` | Minimal safe Slack payload, deep-link encoding, outbox retry, duplicate suppression, channel allowlist, and absence of sensitive evidence. |
| `content_atelier/backend/tests/test_approvals.py` | Whitney-only gates, editor permissions, expected revisions, immutable snapshots, CTA requirement, pass reasons, warning acknowledgement, and all downstream invalidation rules. |
| `content_atelier/backend/tests/test_internal_research.py` | Corroboration and prior coverage retrieval, evidence lineage, client filters, source limits, and exclusion of unrelated client context. |
| `content_atelier/backend/tests/test_serpapi.py` | Fixed query recipes, 15-search cap, response normalization, caching, timeout/429/5xx handling, missing-key degradation, and framing-only classification. |
| `content_atelier/backend/tests/test_briefs.py` | Required fields, message spine size, unique format roles, open-question blocking, CTA immutability, version edits, and stale downstream packs. |
| `content_atelier/backend/tests/test_generation.py` | Independent context per asset, correct asset count/schema, reel angle isolation, no sibling output leakage, idempotent job retries, and bounded failures. |
| `content_atelier/backend/tests/test_factual_checks.py` | Quote/figure evidence binding, scope loss, fabricated claim, prohibited naming, anonymization, and external-research-as-proof rejection. |
| `content_atelier/backend/tests/test_structural_checks.py` | Slide/reel counts, CTA equality, POV, captions, required fields, and deterministic error paths. |
| `content_atelier/backend/tests/test_voice_checks.py` | Banned terms, negative-contrast patterns, staccato/stacked patterns where deterministic, critic schema, two-repair limit, and warning persistence. |
| `content_atelier/backend/tests/test_overlap_checks.py` | Exact duplicate paragraphs, exclusions for CTA/message spine, semantic threshold behavior, and warning acknowledgement. |
| `content_atelier/backend/tests/test_api_v2.py` | Authentication, authorization, pagination, filtering, error envelopes, revision conflicts, idempotency, and complete gate endpoint transitions. |
| `content_atelier/backend/tests/test_worker_v2.py` | Dispatch for every job type, stale recovery, priority, retry exhaustion, spend pausing, source advisory locks, and unknown-job quarantine. |
| `content_atelier/backend/tests/test_metrics.py` | Correct counts/latencies/costs without transcript or client content leaking into labels/logs. |

### 7.3 Historical and golden tests

| New test file or fixture | Coverage |
|---|---|
| `content_atelier/backend/tests/golden/test_corpus_classification.py` | Reproduce `78 client · 4 workshop · 61 internal · 7 fragment` when the private corpus is available; skip clearly when absent. |
| `content_atelier/backend/tests/golden/test_editorial_replay.py` | Prove the five known positive chains become eligible and hard-negative calls remain mostly below digest selection. |
| `content_atelier/backend/tests/golden/test_ten_weeks_chain.py` | Trace the canonical “10 weeks” example from raw source through moment, idea, brief, assets, checks, and approval snapshots. |
| `content_atelier/backend/tests/golden/fixtures/expected_chains.json` | Non-sensitive IDs/expected decisions and failure classes; no raw client transcript text is committed. |
| `content_atelier/backend/tests/golden/fixtures/whitney_labels.json` | The approximately 30 human labels used as a versioned regression set once supplied. |

Golden tests must report confusion counts, selected-rank changes, and rejection-reason changes per prompt/scoring version. They may not silently update expected outputs.

### 7.4 Command Center server tests

| New or modified test file | Coverage |
|---|---|
| `frontend/server/content-atelier-proxy.test.mjs` | Session requirement, team-role requirement, upstream configuration failure, method/path allowlist, actor override, bearer secrecy, request body forwarding, timeout/abort, upstream JSON/non-JSON errors, and request IDs. |
| `frontend/server/auth-core.test.mjs` | Add Whitney/team identity cases only if authorization helpers are generalized; preserve authoritative role resolution. |
| `frontend/server/upstream-url.test.mjs` | Add Content Atelier URL cases if the common upstream policy is reused. |

### 7.5 Frontend unit and component tests

| New or modified test file | Coverage |
|---|---|
| `frontend/src/services/api/contentAtelier.test.ts` | URL encoding, query parameters, expected revisions, error normalization, abort behavior, and typed response use. |
| `frontend/src/hooks/useContentAtelier.test.ts` | Loading/refetch/mutation states, cancellation, 409 handling, stale response suppression, and server-confirmed updates. |
| `frontend/src/components/opshub/screens/ContentAtelierScreen.test.tsx` | Four-view navigation, URL restoration, loading/error/empty states, role-safe controls, and no fixture fallback. |
| `frontend/src/components/opshub/atelier/IdeaGate.test.tsx` | Proof/score visibility, no preselected CTA, required CTA on approval, required pass reason, re-search instruction, and forbidden approval for non-Whitney users. |
| `frontend/src/components/opshub/atelier/MomentsView.test.tsx` | Search/filter combinations, source links, proof confirmation, attribution/consent warnings, and pagination. |
| `frontend/src/components/opshub/atelier/BriefEditor.test.tsx` | Edit/revision flow, research provenance, unanswered required questions, save conflicts, and Gate 2 controls. |
| `frontend/src/components/opshub/atelier/PackReview.test.tsx` | Asset revisions, blocking/warning display, acknowledgement, stale checks, copy behavior, and Gate 3 immutability. |
| `frontend/src/components/opshub/atelier/RevisionConflict.test.tsx` | Reload/compare behavior and guarantee that stale local content is not automatically resubmitted. |
| `frontend/src/hooks/useOpsHub.inbox.test.ts` and related Ops Hub tests | Update expectations after removal of local Atelier workflow fields; verify unrelated Ops Hub behavior does not regress. |

### 7.6 Browser end-to-end and accessibility tests

Add `frontend/e2e/content-atelier.spec.ts` with a controlled fake Atelier upstream and cover:

1. Team editor generates a manual digest preview.
2. Digest notification is requested exactly once.
3. Whitney opens the Slack-style deep link and lands on the correct Gate 1 item.
4. Approval is blocked until Whitney selects a CTA.
5. Gate 1 approval produces research/brief state.
6. Required brief questions block Gate 2.
7. Gate 2 approval produces independently generated assets.
8. A factual failure blocks Gate 3.
9. An acknowledged non-blocking voice/overlap warning allows Gate 3.
10. Gate 3 freezes the pack as `approved_ready` and presents no hand-off/publish action.
11. A stale second browser receives a revision conflict rather than overwriting work.
12. Client-role and non-Whitney accounts cannot approve gates.

Run automated accessibility assertions on every gate view: keyboard-only completion, focus movement after mutations/errors, accessible names for evidence links and status indicators, error association, contrast, and no information conveyed only by color.

## 8. Requirement-to-verification traceability

| Requirement | Primary implementation | Required proof |
|---|---|---|
| Continuous capture without duplicates | Fathom/Slack ingest, source registry, jobs | Webhook/poll parity and Slack re-poll integration tests |
| Raw evidence cannot be rewritten | Normalizer, segments, glossary, moments | Raw/clean separation and verbatim tests |
| Only relevant calls reach AI | Pre-filter and source facts | Corpus classification totals and no-internal-enqueue tests |
| Every useful moment persists | Pass A promotion and moment ledger | Prompt rerun/deduplication tests and ledger API tests |
| Ideas can combine calls | Search and clustering | Multi-call cluster, singleton, and duplicate-membership tests |
| Worthiness remains strict | Eligibility guards and principle/sufficiency | One-test-per-gate unit coverage plus hard-negative replay |
| Ranking is explainable | Ranking service and score snapshot | Arithmetic, threshold, tie-break, and API explanation tests |
| Digest never pads weak ideas | Digest service | Zero-to-five selection tests |
| Whitney alone approves | BFF identity plus Atelier approvals | Role/actor spoof and all-gates authorization tests |
| CTA is human-selected | Gate 1 model/API/UI validators | CTA stripping and approval-blocked-without-CTA tests |
| Research cannot become proof | Research types and factual checker | SerpAPI framing-only and external-proof rejection tests |
| Brief controls generation | Brief revision and asset jobs | Context-capture tests proving every asset uses the same brief revision |
| Assets are independent | Per-asset generator jobs | Sibling-output leakage tests |
| Claims remain traceable | Asset evidence links and factual checker | Unsupported quote/figure/identity tests |
| AI voice risks are controlled | Deterministic rules, critic, repair cap | Banned-pattern and two-repair-limit tests |
| Gate 3 cannot publish | Approval state machine | E2E and API tests asserting no external hand-off job/action |
| Concurrent work is safe | Expected revisions and immutable snapshots | 409 conflict and stale-downstream tests |
| External failures degrade safely | Provider adapters and job retries | SerpAPI-down, Slack-down, model-429, and retry-exhaustion tests |
| Costs remain bounded | Job spend guards and per-provider caps | Spend ceiling and 15-search cap tests |

## 9. CI quality gates and definition of done

### Required CI jobs

1. **Backend static:** formatting check, lint/type check, migration validation, and strict-schema generation.
2. **Backend unit:** deterministic tests without network or private corpus.
3. **Backend integration:** ephemeral PostgreSQL with pgvector, full migrations, API/jobs/repositories, and mocked providers.
4. **Historical regression:** runs only where the encrypted/private corpus is available; emits a report artifact and never uploads raw transcripts.
5. **Frontend static:** TypeScript, lint, formatting, OpenAPI generated-file drift, and production build.
6. **Frontend unit/component:** Vitest with accessibility assertions.
7. **BFF:** Node test suite including the Atelier proxy.
8. **E2E:** browser gate lifecycle against controlled backend fixtures.
9. **Security/dependency:** secret scan and dependency vulnerability report; failures follow the repository’s agreed severity threshold.

No CI job may call a live model, Slack, Fathom, SerpAPI, or production database. Live-provider smoke tests are explicit operator commands in staging.

### Reliability definition of done

- Migrations succeed on an empty database and an existing v1 database and are repeatable in staging.
- Every external call has timeout, bounded retry, idempotency, and auditable failure state.
- Source reconciliation can recover events missed during a deployment.
- A worker crash cannot strand work permanently or duplicate an approval/notification.
- Every state-changing API supports optimistic concurrency.
- Logs and metrics contain IDs and states, not transcript bodies, quotes, client revenue, or secrets.
- A provider outage has a defined degraded state visible in the UI.

### Accuracy definition of done

- Every stored quote used as proof is verbatim-verified or human-confirmed visual evidence.
- Every load-bearing figure includes scope and source.
- All known positive chains are recovered in historical replay.
- Internal meetings produce zero eligible ideas.
- The digest never exceeds five or pads below-threshold ideas.
- External research never satisfies a factual claim check.
- Every generated asset can be traced to one approved brief revision and its evidence.

### Product definition of done

- Whitney can complete all three gates in the app from deep links.
- No gate can be approved by a different actor.
- Every gate presents the evidence, warnings, and exact revision being approved.
- A refresh or second browser shows server state, not lost local demo state.
- Gate 3 produces only an immutable in-app `approved_ready` pack.
- There is no GHL, Drive, Canva, scheduling, sending, posting, or publishing path in v1.

### Documentation and operational hand-off

Before production enablement, documentation must include:

- Environment-variable and secret ownership matrix
- Fathom key onboarding and source-coverage verification
- Slack app scope/reinstall/channel-invite procedure
- Migration and rollback runbook
- Worker/job recovery runbook
- Prompt/scoring change and historical-replay procedure
- Consent and CTA catalog maintenance procedure
- Manual digest preview/notify operating procedure
- Incident procedure for a questionable quote, figure, identity, or approved pack

This plan is complete only when the implementation, tests, migration history, generated API contract, operational runbooks, and the reconciled product specification all describe the same three-gate ledger-to-digest system.
