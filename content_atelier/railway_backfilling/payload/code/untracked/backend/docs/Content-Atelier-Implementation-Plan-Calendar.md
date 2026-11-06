# Content Atelier: Real Packs and Backend Calendar Implementation Plan

Date: 16 October 2026

Status: Proposed engineering plan. This document changes no application behavior, database, deployment, provider permissions or production records.

Outcome: A genuine approved content pack can be scheduled from the Atelier UI; the backend saves the schedule; Home, Weekly Studio and the pack library display the same persisted entries after refresh or another user's sign-in. No runtime calendar or scheduling view includes mock content.

## 1. Scope and decisions

This plan covers the complete missing path from an existing approved backend brief through actual pack production, human pack review, schedule persistence and calendar display. It reuses the implemented angle/brief APIs and SQL worker rather than redesigning intake or editorial discovery.

The user's accepted behavior is:

1. PostgreSQL is the authority for packs, assets and schedules.
2. Only explicitly saved schedules populate the calendar. An approved or generated pack without a saved date creates no calendar entry.
3. An empty database produces an empty calendar. Errors produce an error state, never demo content.
4. Each email, carousel and reel has its own stable asset ID and can have a separate posting time. Whole-pack scheduling saves all five entries atomically.
5. Pack approval is an explicit recorded action. Scheduling does not silently approve content.
6. Saving a schedule records a shared publishing plan. Automatic posting, email sending and confirmation from publishing providers are a separate release.
7. Existing local mock ideas and schedules are never promoted into genuine production records automatically.
8. Preserve the current calendar layout and month/week/day interactions while replacing its data dependencies.

This request supersedes the calendar-out-of-scope ruling in the older brief-generation implementation plan. It does not authorize changes to models, live provider execution, Slack approvals, source intake schedules or the queue architecture. Historical strategy documents are context; current code and this scope govern the work described here.

Implementation defaults:

- Team-only reads through the existing authenticated BFF; explicit backend capabilities for production, approval and scheduling.
- Display timezone Asia/Kolkata, preserving current IST scheduling behavior; backend configuration supplies it. Intake remains independently configured in America/Chicago.
- One active schedule per asset/channel. Multiple reposts of the same asset are outside this release.
- Five pack slots: email, carousel, reel_1, reel_2, reel_3. Captions and production directions belong to their assets; no extra calendar cards for captions.
- Start pack generation explicitly from an approved backend brief. Brief approval alone does not trigger new paid work.
- Reuse the existing SQL worker for pack generation. Calendar CRUD requires no worker.
- Keep provider execution disabled by default. Synthetic tests and cache replay establish wiring without making paid calls.

## 2. Verified starting point

All paths in the file map below are relative to the Content Atelier root:

C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier

| Area | Current behavior | Consequence |
| --- | --- | --- |
| frontend/src/App.tsx | Seeds mock ideas, stores them in localStorage, advances local gates, saves dates on local idea objects. | A browser refresh may retain a date, but no shared backend schedule exists. |
| frontend/src/components/ContentCalendar.tsx | Combines hardcoded October postings, generated demo placements and local idea schedules; starts at a fixed October month. | Removing only one mock array would leave other simulated sources active. |
| frontend/src/components/EditorialHub.tsx and ScheduledContent.tsx | Pass demo postings into Scheduled Content and derive counts from local packs. | Both the cards and counts need conversion. |
| frontend/src/components/PackSchedulePopover.tsx | Calls a synchronous callback and closes immediately on apparent success. | It cannot distinguish a committed backend save from a local update. |
| frontend/src/components/ContentPacksView.tsx | Reads ContentIdea.pack and scheduledAt. | It cannot list SQL packs or represent per-asset partial scheduling reliably. |
| frontend/src/components/SQLWeeklyAngles.tsx and SQLBriefs.tsx | Use real APIs but are not mounted in App. | The real approval-to-production path needs reachable UI. |
| backend/migrations/001_approved_schema.sql | Defines content_packs, content_assets and calendar_entries. Entries pin asset_content_hash and scheduled_for. | Reuse these tables rather than storing dates on angles or briefs. |
| backend/backend_pipeline/briefs/gate_two.py | Records Gate 2 approval and explicitly queues no production jobs. | Real pack production is a missing prerequisite. |
| backend/backend_pipeline/sql_pipeline.py and storage_cli.py | Durable SQL worker handles angle and brief stages. | Extend the same executor with pack stages. |
| backend/backend_pipeline/storage_api.py | Has angle/brief/evidence operations, no pack/calendar API. | New contracts and endpoints are required. |
| frontend/server/app.mjs | Narrow route allowlist and query validation. | New APIs will be unreachable until proxy rules are added. |
| backend/backend_pipeline/database.py | Compares exact recognized schema catalogs. | A migration must update catalog recognition and upgrade tests. |
| backend/backend_pipeline/retrieval.py and briefs/gate_two.py | Read calendar rows into publication history without status filtering. | Scheduling could be mistaken for publication and alter brief-review guards. Fix this before enabling writes. |
| backend/compose.intake.yml | Starts intake/media workers and scheduler, but no editorial SQL worker. | Pack generation needs a separately deployed editorial worker service. |

The current production data population and deployed service health have not been verified. Local Docker access was unavailable during the architecture audit. This plan must not assume that tables are empty or that an editorial worker is already running.

## 3. Target flow and responsibility

1. A verified team member opens actual stored angles and briefs through the reachable Weekly Studio.
2. The existing backend performs Gate 1 and Gate 2 decisions using its current hashes, evidence checks and actor capabilities.
3. On an approved, consumable brief, an authorized user selects Generate pack.
4. The API creates a durable production run and planned pack/assets; it returns a run ID without waiting for inference.
5. The editorial SQL worker produces the assets, validates them and assembles the pack manifest.
6. The pack appears in the backend-backed library as awaiting human review, with actual processing errors and blockers.
7. An authorized reviewer approves the exact manifest. No calendar entries are created yet.
8. A scheduler chooses dates for selected assets, or a common date/time for the full pack.
9. The API validates the current approval and expected versions and commits the entire requested schedule in one transaction.
10. The browser receives the saved entries and refreshes the shared calendar/list queries.
11. Another signed-in team member sees the same entries. Selecting a card opens the exact saved asset and pack.

The API owns permissions, state transitions, idempotency, concurrency and schedule persistence. The worker owns expensive content production. The UI owns selection and display. PostgreSQL owns durable business state; artifact files own immutable provider receipts and intermediate results.

## 4. Workstream A: contracts and additive database migration

Deliverable: migration 004_packs_calendar.sql, recognized schema catalogs and typed backend/frontend contracts.

Before migration, inspect counts, actual status values, orphan relationships and duplicate active schedules in all three existing tables. Do not delete or relabel existing records to make constraints pass. Unexpected rows require an explicit reviewed repair or exclusion plan.

### 4.1 Pack and asset contracts

- Keep the existing pack/asset tables and their owning relationships.
- Add explicit production provenance on packs: source_brief_id, source_brief_hash, production_run_id and contract_version. Populate them from the validated approved brief and run, never from browser assertions.
- For pre-existing records, use an additive nullable upgrade first; validate provenance before allowing approval or scheduling. Make fields mandatory for all new writes. Never fabricate historical hashes.
- Pack content remains in content_assets.content_body with a discriminator/schema version. Use Pydantic contracts for an email, carousel and reel.
- Email: title, subject options/selected subject, preview text, body, approved CTA label and URL.
- Carousel: title, ordered slides, caption and production directions. Follow the approved brief's slide specification rather than introducing a fixed eight-slide rule.
- Reel: title, spoken script, caption, approved CTA and visual/recording directions, with its stable slot key.
- Each asset retains supporting evidence/claim references and qualifications from the approved brief in its versioned envelope. Do not convert a briefing hypothesis into an established fact.
- The canonical manifest covers slot order, asset IDs/types/content hashes, approved brief IDs/hashes and the successful validation artifact. Approval binds to that exact manifest.
- Confirm all five required slots once, with consistent brief lineage. Existing unique pack/slot and pack/ordinal indexes help enforce this.

### 4.2 Schedule state

Extend calendar_entries with:

- revision: integer used for optimistic concurrency.
- pack_manifest_hash: the exact approved pack manifest at scheduling.
- display_timezone: the validated IANA timezone used for the user's selection.
- created_by and updated_by: trusted actor IDs.

Keep asset_id, asset_content_hash, channel and scheduled_for as the authoritative scheduled target and instant. Use the parent asset to obtain pack identity; do not duplicate the content body into calendar rows.

Recognized states are draft, scheduled, needs_review, cancelled and published. Drafts do not appear on the active calendar. Published remains confirmation-backed and cannot be set through this release's browser mutation API. Passing the due time never changes a schedule to published.

- Add a partial unique index on asset_id/channel for active states scheduled and needs_review.
- Require a timestamp for scheduled/needs_review entries and a publication timestamp for published entries.
- Add a positive revision check and appropriately bounded channel validation. Logical destinations initially map email to email and carousel/reels to instagram; format and destination remain distinct fields in the response.
- Preserve cancelled entries as history. A deliberate new scheduling request after cancellation creates a new entry.
- Reject repeat scheduling of already published assets in this release; explicit repost/version handling can follow later.

### 4.3 Mutation receipts and audit

Add a small durable request-receipt table for production/approval/scheduling mutations:

- request_id, trusted actor, operation/target, canonical request hash, committed response and creation time.
- A request ID is bound to its actor and normalized payload. Reuse with different content returns 409.
- A repeated request after a lost response returns the original committed response, even if its chosen publishing time has since passed. Perform receipt lookup before current-time eligibility checks.
- Insert the receipt and business changes in one transaction. A rollback leaves neither a successful receipt nor partial entries.

Use existing pipeline_runs/pipeline_events for pack and schedule audit events. Schedule-only operations use a completed scheduling run with no worker jobs. Record actor, operation, previous/new time, target IDs, revision and request ID.

Add the table to schema checks and synthetic-test isolation/reset tooling. Preserve compatibility with baseline, brief-index and intake upgrades; test the supported upgrade paths and a second no-op application. APIs/workers must not run DDL on startup.

Exit condition: an isolated real PostgreSQL database upgrades successfully, constraints enforce the intended state, and existing recognized storage/intake catalogs still work.

## 5. Workstream B: genuine pack production and approval

Deliverable: backend_pipeline/packs package, prompt contracts, SQL worker dispatch and pack APIs.

### 5.1 Queueing

- Require an approved brief that passes the existing backend can_consume/blocker checks.
- Freeze the approved brief, evidence/clearances, CTA, founder brand bundle and exact execution contract.
- Include exact configured model IDs, prompt/schema hashes, provider route and execution mode in the intent. Introduce explicit pack writer/reviewer settings with no silent model fallback.
- Create deterministic run/pack/asset identities for the same intent. Repeated submission returns the same run.
- Production regeneration from a changed brief or instructions creates a replacement pack and new assets; supersedes_id retains lineage.
- No mutation of consumed asset content. An asset already included in a reviewed or scheduled manifest requires a replacement version.

### 5.2 Proposed jobs, all on the existing SQL worker

| Job | Input and output |
| --- | --- |
| pack_prepare | Revalidate the frozen brief; create five planned asset slots and a production input artifact. |
| pack_email | Write the email/copy envelope from the approved email direction and evidence. |
| pack_carousel | Write ordered slides, caption and directions from the approved carousel direction. |
| pack_reel_1 | Write the first reel and its caption/directions. |
| pack_reel_2 | Write the second reel and its caption/directions. |
| pack_reel_3 | Write the third reel and its caption/directions. |
| pack_validation | Validate all five artifacts, evidence/CTA handling, completeness and distinct reader contributions; save actual findings. |
| pack_assembly | Recheck dependencies, save final validated assets/manifest and mark the run waiting_for_review. |

Each writing job depends on prepare; validation depends on all five writing jobs; assembly depends on validation. This is eight jobs, not eight worker services. One SQL worker may execute them serially; later replicas can claim independent jobs using existing leases.

Reuse existing request fingerprinting, raw-response persistence, cache/replay and cost accounting patterns. A successful sibling asset is reused after a failed asset is retried. Lease expiry or an unknown paid-call outcome requires explicit review/retry. No automatic provider repair/retry should purchase duplicate output after uncertainty.

Structural checks can prove shape, IDs, exact copied quotations and supported references. They cannot prove every semantic claim; retain findings and require human pack review. Do not invent a passed voice/overlap score when the relevant check did not run.

### 5.3 Human approval and replacement

- Pack detail returns can_approve, can_schedule and blockers from backend policy.
- Approval requires the expected manifest hash, actual successful validation and current governing brief/evidence clearance.
- Rejection requires a reason and persists it.
- Approval creates no calendar row.
- Replacements leave existing schedules visible with a needs_review warning; do not automatically cancel, transfer dates or publish replacement content. Reapproval and deliberate rescheduling select the new assets.
- Defence in depth: list/detail reads derive effective eligibility if an upstream restriction or replacement makes a stored schedule invalid. Keep the saved dated entry visible with its warning instead of silently dropping it.

Existing Gate 2 approval behavior remains unchanged; the new explicit Generate pack action is the handoff.

Exit condition: a saved approved brief can produce one durable five-asset pack, resume from a failed stage, receive manifest-bound approval and expose exact saved copy through detail APIs.

## 6. Workstream C: calendar service and transaction semantics

Deliverable: backend_pipeline/calendar service/contracts, schedule operations and range queries.

### 6.1 Schedule request

The request carries:

- request_id and expected_pack_manifest_hash.
- An explicit list of one to five asset IDs, expected asset content hashes and expected schedule revisions.
- For each asset, scheduled_for as an offset-aware timestamp and display_timezone as an IANA identifier.
- Initial creation uses no existing entry/revision. Updates identify the active entry and its expected revision.

Whole-pack scheduling resolves all five stable assets from the approved manifest. The server verifies that a whole-pack request contains every required slot once. Individual scheduling resolves the selected asset, never an array position from the UI.

Reject naive timestamps, unknown zones, impossible local times, duplicate asset IDs, unsupported destinations, missing content and invalid lineage. For zones with daylight-saving changes, require an explicit offset and verify that it matches the chosen local wall time. Persist UTC; round-trip the selected civil date/time correctly.

### 6.2 Single transaction

1. Authenticate and authorize the actor; resolve any committed idempotency receipt.
2. Lock the governing brief/pack and affected assets/entries in a documented consistent order shared with approval/replacement operations.
3. Verify current brief consumability, approval/manifest/hash binding and expected revisions inside the transaction.
4. Check future instants against server time and validate the complete batch.
5. Insert or deliberately update all requested calendar entries, incrementing revisions. No unrelated piece loses its date.
6. Write events and the durable successful response receipt.
7. Commit, then return exactly the saved entries.

Concurrent schedulers produce one committed result and a 409 refresh conflict for the stale request. Database uniqueness is the final duplicate guard. Do not silently overwrite another person's selection.

PATCH reschedules and POST cancellation use the same receipt/revision rules. Cancellation must remain possible even if upstream content is no longer eligible. Published/cancelled entries are terminal for ordinary rescheduling; return a clear conflict rather than resurrecting them.

Different packs may share a time. Do not invent a single-slot scheduling restriction that the user did not request.

### 6.3 Read model

Calendar reads use a half-open UTC interval [from,to), derived from the complete visible civil-date range in the configured display timezone.

- Bound a request to at most 93 days.
- Default to saved active schedules and needs_review entries. An explicit history filter may return only genuinely confirmed published entries; no automatic published inference.
- Return calendar_entry_id, revision, asset_id, asset_content_hash, pack_id, pack_manifest_hash, title, format, destination channel, scheduled_for, timezone, stored/effective status and warning/blocker summaries.
- Derive format from asset_type and title from the versioned asset contract. Include source brief/angle IDs and generation week when known.
- Return server_time, display_timezone and filters/range metadata.
- Sort by scheduled_for then stable entry ID. Use bounded pagination with a next cursor; the client must load every page before presenting totals as complete.
- Join exact related records. Broken lineage is an explicit integrity warning/error, never a fallback to the first available idea.
- Schedule summary and readiness come from the same service used by pack detail and Scheduled Content.

The first release refreshes on successful mutation, window focus and a modest polling interval (for example 30 seconds). No websocket or calendar worker is necessary.

Exit condition: CRUD/range reads use real SQL and remain correct under retries, concurrent updates, month boundaries, stale approvals and partial failures.

## 7. Workstream D: API and authenticated proxy

The Python paths are under /storage; the browser paths below are under /api/atelier. Reuse the existing trusted session/actor BFF instead of exposing the backend secret.

| Method and browser path | Contract |
| --- | --- |
| GET /calendar/config | Display timezone, server time, feature readiness and the current actor's capabilities. |
| GET /packs | Bounded filters for week/approval status and pagination; include per-asset scheduling summary. |
| GET /packs/{pack_id} | Saved assets, lineage, blockers, approval hash, production status and active schedule revisions. |
| POST /briefs/{brief_id}/pack | Queue a frozen production intent; return 202 and run/pack IDs. |
| GET /packs/{pack_id}/production | Jobs, progress, errors and recorded cost states. |
| POST /packs/{pack_id}/decision | Approve/reject the expected manifest with a mutation request ID. |
| POST /packs/{pack_id}/schedule | Save one or all asset schedules atomically. |
| GET /calendar | Bounded from/to, status and cursor filters. |
| PATCH /calendar/{entry_id} | Reschedule with expected revision and request ID. |
| POST /calendar/{entry_id}/cancel | Cancel with expected revision, request ID and optional reason. |

Add generation-stage retries through the existing job retry operation with pack capability checks. Verify that its authorization is adequate for the new target rather than assuming a team role permits every retry.

Use typed payloads that forbid extra fields. Standardize 401 unauthenticated, 403 unauthorized, 404 missing resource, 409 stale state/eligibility conflict, 422 malformed inputs and 503 unavailable dependencies. Include stable error codes and actionable blocker messages.

Extend BFF exact method/path/query allowlists, ID validation and bounded body handling. Preserve same-origin mutation checks, verified team access and server-derived actor identity. No arbitrary passthrough, caller-supplied bearer token or actor forwarding.

Long generation calls stay outside the request path, so existing short BFF timeouts can remain. Pack detail responses contain actual full copy; list/calendar responses contain summaries. Do not increase request limits globally to accommodate unnecessary serialized UI objects.

Proposed settings:

- ATELIER_PACKS_ENABLED, ATELIER_ALLOW_PACK_GENERATION.
- Exact pack writer/reviewer model configuration and existing provider credentials on API/worker only.
- ATELIER_PACK_EDITORS, ATELIER_PACK_APPROVERS, ATELIER_CALENDAR_SCHEDULERS.
- ATELIER_CALENDAR_ENABLED and ATELIER_CALENDAR_TIMEZONE.

Team users can read; a dedicated scheduler capability permits mutations. Feature readiness, role failures and an empty result are distinct UI states.

Exit condition: the authenticated browser can access exactly these operations, and invalid methods, query strings, forged identities and unauthorized writes are rejected.

## 8. Workstream E: frontend integration and removal of mock scheduling

### 8.1 Genuine types and shared data access

- Add StoredPack, StoredAsset, CalendarEntryDTO, PackProduction and scheduling request/response contracts.
- Keep backend IDs/hashes/revisions intact. Do not coerce StoredPack into ContentIdea with invented scores, research or quotes.
- Separate presentational date-cell helpers from data loading. Reuse the current visual components against real DTOs.
- Add small shared query hooks/services using the existing fetch helper and a mutation invalidation signal; no new state-management library is required.
- Use cancellation/request identity to prevent a late response for one month from replacing a newer month's data.
- Fetch all pages and report incomplete/loading/error states accurately. Zero visible entries after filtering must be distinguishable from no schedules in the range.

### 8.2 Calendar

- Remove runtime OCTOBER_POSTS, octoberMockPosts, octoberDemoPosts and calendarDemo dependencies from the calendar and Scheduled Content.
- Remove derivation from ContentIdea.scheduledAt/contentSchedules and the idea fallback in openPost.
- Initialize the current month and focused day from the configured timezone. Clamp/reset focus when changing months, especially between 31-day and shorter months.
- Month, week, day and daily modal use the same real entries and stable IDs; query the complete visible range, including adjacent dates if they are actually rendered.
- Date navigation/focus and format/search filters remain available. Render active entries in chronological order and group individual assets by their actual date.
- Selecting a card opens the pack/asset ID from its DTO through a real content detail component. Missing content shows a retryable error.
- Show loading, empty, backend-unavailable and needs-review states explicitly. A background refresh failure may retain last successfully fetched real entries only with a visible stale-data warning; it must not use mock or localStorage entries.
- A schedule in the past stays scheduled/overdue until cancelled or genuinely confirmed published. Time passing alone is not publication evidence.

### 8.3 Scheduling controls and pack library

- Refactor PackSchedulePopover to receive a stored pack and optional asset ID and await a Promise-returning mutation.
- Separate Approve pack from Confirm schedule; remove auto-approval from scheduleContentPiece/schedulePack/handleLibrarySchedule paths.
- Show server eligibility and blockers, disable duplicate submission, and retain the input/picker until save success.
- Reuse the same request ID for an uncertain retry. Changed inputs receive a new request ID.
- Show the existing exact dates for all assets. Provide explicit whole-pack versus selected-piece behavior; changing one piece leaves other dates unchanged.
- On 409, refresh real state and preserve the user's proposed time for review. Never overwrite blindly.
- After commit, invalidate calendar, pack detail/list and Scheduled Content together.
- Global Content Packs and Weekly Studio's Content Packs read the same backend list/detail service.
- Show accurate unscheduled, partially scheduled (for example 2/5) and fully scheduled states.

### 8.4 Reachable approved-brief path

- Mount the existing SQL angle/brief review logic in the real Weekly Studio tabs; adapt its presentation without rebuilding editorial discovery.
- Add Generate pack only to an actual approved/consumable brief, with actual mode/readiness and job progress.
- Replace Weekly Studio's Packs/Scheduled branches with the new backend-backed components and counts.
- Replace local inspector scheduling controls with actual pack/asset detail. Existing legacy mock inspectors must not offer scheduling actions or feed the real library/calendar.
- The Home ideas view and other unrelated prototype screens may retain their separate local data during this scoped release, but cannot contribute calendar entries or production counts.
- Do not automatically migrate, upload or trust existing localStorage schedules. Leave unrelated stored ideas intact; retire their scheduling consumers.
- Old demo fixture files can stay test-only if another test needs them. Production runtime imports for the scheduling surfaces must be removed.

Exit condition: the user's entire brief-to-pack-to-schedule interaction is reachable, and Home/Weekly Studio/library share real state without any mock scheduling route.

## 9. Workstream F: publication-history correctness

This is a release blocker, not a cosmetic follow-up.

Current retrieval.previous, retrieval.check_prior and briefs.gate_two.prior_state query all calendar rows as publications. Adding genuine schedules would otherwise change frozen publication context and could make unrelated brief approvals stale merely because a date was added or changed.

- Centralize a confirmed-publication projection used by all three call sites.
- Include only status=published with a real published_at and exact asset-version lineage.
- Hash stable publication facts, not irrelevant schedule updated_at values.
- Keep planned/scheduled coverage separate if supplied as editorial context; label it explicitly and do not claim it reached an audience.
- Version any changed frozen research contract. Preserve historical artifacts rather than rewriting their approved evidence. Review any actually populated legacy calendar history before switching behavior.
- Saving, rescheduling or cancelling an unpublished item must not change confirmed-publication history or invalidate a brief on that basis.
- A later genuine publication may appropriately change coverage and trigger the existing review requirements.

Exit condition: dedicated integration tests prove planned entries are never treated as publication evidence.

## 10. Delivery sequence and reviewable milestones

| Milestone | Work | Required evidence before proceeding |
| --- | --- | --- |
| M1: storage/contracts | A plus confirmed-publication projection from F. | Catalog upgrade/idempotency tests; no schedule-to-publication leakage. |
| M2: real schedule service | C and authenticated routes from D, using isolated genuine-shaped fixtures. | SQL save/read/reschedule/cancel, conflicts, lost-response retries and atomicity pass. |
| M3: clean calendar UI | Calendar/data-access work from E; remove all mock schedule feeds. | Empty/error/current-month behavior and real API cards verified. No production claims without API data. |
| M4: pack production | B, remaining D and deployment command for editorial SQL worker. | Synthetic/cache replay produces complete versioned pack and human approval; failed-stage reuse verified. |
| M5: complete UI path | Library, popover, real SQL brief tab and Scheduled Content integration. | Approved brief to real pack to saved calendar works through authenticated UI. |
| M6: staging/release | Integration/browser acceptance and rollout below. | Cross-browser persistence, all five slots, timezone and rollback checks pass. |

M2/M3 can be completed before a live pack has been generated. That makes the no-mock calendar correct early; its honest empty state is expected. M4/M5 are mandatory before claiming the full end-to-end workflow is complete.

Suggested implementation units are separate small changes: migration/history semantics; calendar repository/API; BFF contracts; calendar read UI/mock removal; pack workflow; pack review/schedule UI; integrated deployment/acceptance.

## 11. File map

| Existing file/group | Planned change |
| --- | --- |
| backend/migrations/004_packs_calendar.sql and schema-catalog variants | Additive fields, request receipts, constraints/indexes and recognized schemas. |
| backend/backend_pipeline/database.py, storage_cli.py, database test/reset helpers | Explicit migration command, catalog checking and isolated test setup. |
| backend/backend_pipeline/packs/{contracts,workflow,runtime,validation,service}.py | New actual content production, artifact reuse, detail and approval service. |
| backend/backend_pipeline/prompt_templates/pack_* | Versioned production and review prompts consuming only frozen approved inputs. |
| backend/backend_pipeline/calendar/{contracts,service}.py | Scheduling invariants, transactions, receipts, queries and actor policy. |
| backend/backend_pipeline/sql_pipeline.py, repository.py | Pack-stage dispatch, lifecycle states and target-aware retry capability checks. |
| backend/backend_pipeline/storage_api.py, storage_config.py | Pack/calendar endpoints and settings. |
| backend/backend_pipeline/retrieval.py, briefs/gate_two.py | Confirmed-publication projection and guards. |
| frontend/server/app.mjs and storage.test.mjs | Narrow authenticated proxy rules, query validation and tests. |
| frontend/src/types, utils, new data hooks | Real pack/calendar DTOs, requests, date conversions and shared invalidation. |
| frontend/src/components/ContentCalendar.tsx, CalendarDayModal.tsx | Real API entries, backend IDs and current-date navigation. |
| frontend/src/components/ContentPacksView.tsx, PackSchedulePopover.tsx, ScheduledContent.tsx | Real library, async schedule flow, per-asset readiness and partial scheduling. |
| frontend/src/components/EditorialHub.tsx, SQLWeeklyAngles.tsx, SQLBriefs.tsx, App.tsx | Reachable backend approval/production flow; retire mock scheduling wiring and counts. |
| backend/compose editorial overlay, STORAGE.md, storage.env.example, DEPLOYMENT.md | Editorial worker startup, flags, migrations, staging and rollback instructions. |

Final filenames can follow repository conventions; the responsibilities and boundaries above should remain intact.

## 12. Verification matrix

Use the existing outbound-HTTP prohibition and a dedicated PostgreSQL database ending in _test. Tests must not truncate a real database or send external model/embedding requests.

| Layer | Required checks |
| --- | --- |
| Migration | Existing supported schemas upgrade, rerun is a no-op, conflicting legacy data fails with a diagnosis, exact catalogs include new objects, intake still works. |
| SQL scheduling | Five-entry atomic save, individual save, full rollback on one bad asset, duplicate/retry protection, expected revision conflict, transaction race and cancellation. Use separate connections to exercise real concurrency. |
| Version/approval | No scheduling an unapproved/incomplete/superseded pack or stale asset; replacement does not silently transfer dates; cancellation still works with stale upstream content. |
| Idempotency | Lost committed response and retry return identical IDs; retry after the selected time passes still returns the receipt; same key/different payload or actor is rejected. |
| Time/range | IST midnight, UTC date crossing, month/year/leap boundaries, exclusive range end, DST gap/fold for a configurable zone, server-side future validation and full pagination. |
| Production | Exact five slots, frozen brief/brand/CTA, evidence qualifications, failed sibling retry without regenerating good assets, cache replay, locked/superseded input rejection and manifest-bound approval. |
| API/BFF | Unauthenticated/client/unauthorized actors denied; trusted identity forwarded; invalid routes/queries rejected; no caller identity override; declared response status/content type. |
| UI interaction | Initial loading/empty/error, no October fixtures, current month, stale response cancellation, async picker waits, failed save retains input, duplicate button click, per-piece reschedule and correct card drilldown. |
| Cross-surface | Mutation refreshes Home, pack library and Scheduled Content, including 2/5 versus 5/5 counts. Another authenticated browser reads the same DB state. |
| Editorial history | Schedule/reschedule/cancel never count as published or alter the confirmed-publication review hash; genuine publication changes it intentionally. |
| Deployment | API and worker share DB/artifacts/config, worker can drain a synthetic production run, API restart retains schedules and startup does not migrate automatically. |

Existing frontend tests mostly use node/tsx and static rendering. Add the smallest suitable browser interaction harness for asynchronous scheduling and cross-page behavior; static markup tests alone cannot establish these guarantees. Reuse an existing harness if one is present at implementation time.

Run the appropriate Python tests/lint, frontend typecheck/tests/build and BFF tests after changes. Complete real SQL and browser acceptance before describing the work as end-to-end verified; mocked transports alone are insufficient.

## 13. Deployment and rollout

1. Back up the target database and inspect current pack/calendar rows. Confirm the intended database and artifact volume.
2. Deploy/run the explicit additive migration with feature writes disabled; verify the catalog.
3. Deploy the compatible API and BFF, timezone and capability settings. Keep live generation disabled.
4. Deploy one long-running editorial SQL worker using storage_cli worker --watch, sharing the API's database, artifacts and frozen provider/model configuration. It must survive service restarts. Intake workers are unchanged.
5. Deploy the frontend reading the real API with no mock scheduling fallback. Readiness failures show a feature-unavailable state.
6. Exercise isolated staging fixtures through the actual authentication/BFF/API/SQL/UI path.
7. Verify real approved inputs, reviewed model settings and live-generation authorization separately before any real production call. Run no paid calls merely because the code was deployed.
8. Enable calendar mutations for the configured scheduler actors and complete an authorized real-pack scheduling check.

Operational signals: SQL-worker heartbeat and queued job age; API/database availability; failed production jobs with recorded cost states; schedule mutation errors/conflicts; calendar query failures; integrity warnings. An API health response alone does not prove a worker is running.

Rollback disables new generation/schedule mutations first. Keep persisted schedules readable, retain receipts/audit history and roll back to the last API-backed calendar build. Do not re-enable a demo-backed calendar as a fallback. Prefer retaining an additive schema over destructive down-migration.

## 14. Definition of done

- A real consumable approved brief can create a real five-asset pack through a reachable UI action.
- The pack has actual persisted copy, lineage, validation findings and manifest-bound human approval.
- Scheduling succeeds only after the backend commits its requested entries.
- Home month/week/day views, daily modal, Weekly Studio Scheduled Content and the pack library agree on those saved entries and counts.
- Reloading, API restart and a second authenticated browser retain the same schedules.
- Rescheduling/cancellation work with concurrency and retry protection.
- No calendar/scheduled card or count comes from fixtures, mock generation or localStorage.
- With no saved entries, all schedule surfaces show honest empty states.
- A selected entry opens its exact asset and pack, with no fabricated ContentIdea adapter or unrelated fallback.
- Scheduled copy is never treated as published evidence, and due time never creates a published status.
- Backend unavailable, no permission, missing worker, missing content and no schedules are distinguishable states.
- Database migration, real SQL, BFF, frontend interaction and integrated acceptance evidence are recorded.

## 15. Deliberately separate follow-up work

Automatic email/social publishing and delivery confirmation; provider account connections; media rendering/upload; recurring/repost schedules; drag-and-drop scheduling; reminders/Slack messages; full replacement of unrelated mock screens; migration of the editorial executor to RQ; redesign of source intake or discovery prompts.

These do not block a durable, shared, backend-backed content calendar.
