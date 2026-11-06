# Content Atelier: Slack notifications when content is scheduled

> **Testing override, 5 November 2026:** The owner requested C0C3FT6DZAS for both email and social notices during testing. The prepared settings file now uses this channel for both routes. The earlier production destinations remain documented for restoration before go-live; no production configuration has been changed.

> **Implementation update, 5 November 2026:** The owner approved building the backend and supplied email channel C0BQ6RW7C84 and social channel C063XKRCJ0M. The owner confirmed **“scheduled for publishing”** as the opening, following the newer publication workflow. The backend consumer, delivery ledger, migration and mapping file are implemented locally; setup is documented in [Slack schedule notifications](Slack-Schedule-Notifications.md). The readiness-dependent message examples below are historical proposal material, not the implemented behavior. Live local delivery is now verified: the real browser save produced two confirmed notices in the testing channel. Production activation remains pending.

> **Direction update, 5 November 2026:** The owner now proposes retiring the whole-pack Ready to publish step in favor of per-piece manual publication marking and next-day Instagram/GHL verification. The readiness-dependent wording and checks in this earlier Slack proposal are provisional and must be revised before implementation. Use “scheduled for publishing” for schedule announcements rather than asserting readiness from a retired approval. See [Publication tracking feasibility](Content-Atelier-Publication-Tracking-Feasibility.md). No implementation changes are authorized by either document.

**Date:** 4 November 2026  
**Status:** Backend implemented and live Slack delivery verified from localhost on 5 November 2026; production deployment and activation pending. Earlier readiness-dependent proposal text is superseded by the implementation update above.  
**Baseline:** The deployed implementation represented by local `main` at `52e7083`. The earlier review refactors were reverted and are not prerequisites.  
**Owner's direction:** Notify the email marketing channel for scheduled email content and the social media channel for scheduled social content. Reuse WIA's existing Slack bot. **Message refinement:** identify each piece, show its planned publishing time and include a direct URL to that piece in its content pack. The generic count-only proposal below has been replaced accordingly.

## 1. Recommendation

Use the existing bot to post ordinary channel messages. Have the **existing scheduler consume committed `schedule_saved` audit events**, with one small database table recording which notifications have been attempted and delivered.

This keeps the scheduling UI and scheduling service unchanged. It needs no new service, worker queue, Slack app, public callback endpoint, frontend configuration or new dependency. The project already uses HTTPX.

The minimum runtime inputs are:

| Proposed environment variable | Value | Where required |
| --- | --- | --- |
| `ATELIER_SLACK_BOT_TOKEN` | Reference to the existing bot's credential | Scheduler only; secret |
| `ATELIER_SLACK_EMAIL_CHANNEL_ID` | ID of the email marketing channel | Scheduler only |
| `ATELIER_SLACK_SOCIAL_CHANNEL_ID` | ID of the social media channel | Scheduler only |
| `ATELIER_PUBLIC_APP_URL` | Public HTTPS Content Atelier origin used for piece links | Scheduler only; not secret |

These are **four configuration values, with only one credential**. The piece links require the fourth value; no existing backend setting for the public Atelier origin was found. Reuse an established equivalent if one is available at implementation time. The documented production origin is `https://content-atelier.up.railway.app`; do not hard-code it into the sender or substitute Command Center's origin or a private backend hostname. If the scheduler already has an appropriate bot credential under an established name, reuse that name instead of requiring another copy. Its presence on Atelier's scheduler has not been verified. Credentials must not be copied into this plan, source control or frontend variables.

Register the two channel destinations in the existing settings registry, with these environment variables as their fallback inputs and empty defaults. Use the existing settings loader and precedence. The token remains environment-only, outside settings rows, API responses and editorial snapshots. No separate enable flag is necessary: a destination can operate when its channel ID and the token are configured; absent configuration leaves notifications off.

The bot must have `chat:write` and access to the two selected conversations. If it already does, no Slack permission change is needed. Confirm membership manually rather than adding channel-discovery scopes. No broad `chat:write.public` permission is required for a bot invited to the target channels. These requirements come from Slack's [message API documentation](https://docs.slack.dev/reference/methods/chat.postMessage/).

## 2. What the repository already provides

| Existing implementation | Consequence for this feature |
| --- | --- |
| `frontend/src/components/PackScheduling.tsx` stages dates locally, then posts selected items on **Save all schedules** | Notify on the committed save, not on a checkbox, date selection or the per-piece staging button. No frontend edits are needed. |
| `backend_pipeline/calendar/service.py::schedule` validates and saves a batch in one database transaction | A rejected or rolled-back save must produce no notification. |
| `production_common.receipt` returns the saved result for the same request ID | A client retry does not create a second scheduling action. |
| `packs/service.py::audit` writes a `schedule_saved` event and completed scheduling run in that same transaction | The event is already a durable trigger. Its details include the request ID, pack ID, changed asset IDs, entry IDs, previous/saved times and revisions. |
| `calendar/service.py::reschedule` delegates to `schedule` | Saved reschedules already use the same trigger; a separate hook is unnecessary. |
| `jobs/scheduler.py::tick` runs independently handled parts, normally once per 30-second loop | Add a bounded notification part; reuse the running scheduler rather than creating another process. |
| Intake uses `ATELIER_SLACK_INTAKE_TOKEN` to authenticate requests into Atelier | This is not an outbound Slack bot token. Do not reuse or alter it for posting. |
| Schema migration registration and catalogue checking are strict | A delivery table requires a properly registered migration and coordinated schema-compatible backend deployment. |

No current outbound Slack sender was found in the active application code reviewed. The owner's confirmation establishes that a reusable bot exists, but its app name, token location, permissions and the exact two destination IDs remain setup inputs. Existing intake channel IDs must not be assumed to be these destinations.

## 3. Proposed notification behavior

### Trigger and routing

“When content is scheduled” means **after a successful scheduling save**, not a reminder at the publishing time and not a Slack-scheduled message.

| Content asset type | Logical destination |
| --- | --- |
| `email` | Email marketing |
| `carousel` | Social media |
| `reel` (`reel_1`, `reel_2`, `reel_3`) | Social media |

Use stored asset types and explicit mappings. Do not route unknown future asset types to social by default.

Group each save by destination. Saving the normal five-piece pack generates **one email notification and one social notification**, rather than five separate posts. A partial save notifies only the affected destination(s). Independent save actions remain independent notifications.

### Specific, concise messages for version 1

Each message should open with a clear Content Atelier announcement appropriate to the scenario, then answer **what was scheduled, when it is planned to publish, and where to open it**. Keep one post per save/destination, but give every affected piece its own linked title and publishing time. Illustrative examples for pieces whose publishing readiness has been confirmed (not real content or schedule records):

> Content Atelier has a new email ready to publish at the time below.  
> **Why good enquiries go quiet ↗**  
> Tue 10 Nov 2026 · 09:00 IST

> Content Atelier has 4 new social pieces ready to publish on the schedules below.  
> **Carousel · Why good enquiries go quiet ↗**  
> Tue 10 Nov 2026 · 11:00 IST  
> **Reel 1 · What we check before following up ↗**  
> Wed 11 Nov 2026 · 11:00 IST  
> **Reel 2 · Faster replies are only part of it ↗**  
> Thu 12 Nov 2026 · 11:00 IST  
> **Reel 3 · Give the enquiry a clear next step ↗**  
> Fri 13 Nov 2026 · 11:00 IST

The title and arrow in each example represent a clickable link to that exact piece, not just the pack's first tab. Counts reflect only the relevant, materially changed pieces in that save. Include a pack name once only when it adds useful context; do not repeat the same title in a heading and a piece row.

Use these scenario-dependent openings, with singular/plural and counts adjusted to the actual batch:

| Scenario | Opening sentence |
| --- | --- |
| New email, confirmed ready | Content Atelier has a new email ready to publish at the time below. |
| New social pieces, confirmed ready | Content Atelier has 4 new social pieces ready to publish on the schedules below. |
| New schedule, review pending | Content Atelier has 4 new social pieces scheduled for the times below. Pack review is still pending. |
| Genuine reschedule, confirmed ready | The publishing schedule for 2 social pieces in Content Atelier has changed. They are ready to publish at the updated times below. |
| Genuine reschedule, review pending | The schedule for 2 social pieces in Content Atelier has changed. Pack review is still pending. |
| Mixed new and changed schedules, confirmed ready | Content Atelier has publishing schedule updates for the pieces below. They are ready to publish at the listed times. |
| Readiness cannot be confirmed, or other review warnings remain | Content Atelier has publishing schedules for the pieces below. Check their status in the content pack before publishing. |

Reserve “new” for newly scheduled entries, rather than reschedules. Every scenario retains the per-piece linked titles and times; reschedules show the old time → new time. Scheduling is a publishing plan, not evidence of an external publish action.

Use the same working title as the app: the first email subject option, or the carousel/Reel's `content.title`, falling back to its piece label. This follows `frontend/src/components/packFields.ts::pieceTitle`; no frontend refactor is needed. Show the publishing instant recorded by the scheduling event, formatted in the calendar's existing `display.timezone`, with an explicit time-zone label. Do not use the scheduler host's timezone or add another timezone setting. The examples use IST only for illustration.

Build each absolute link as `{ATELIER_PUBLIC_APP_URL}/studio/packs/{pack_id}?piece={piece_key}`, encoding identifiers and using the event's pack version and the asset's stored slot key (`email`, `carousel`, `reel_1`, `reel_2`, `reel_3`). `PackDetail.tsx` already reads `?piece=` and selects that tab. Existing sign-in and access checks continue to apply. Validate the configured public origin; without a valid origin, mark delivery blocked/failed with a clear configuration error rather than silently sending a notice without the requested links.

Use simple Slack formatting or basic Block Kit sections, with the same linked title/time information in accessible fallback text. Disable link/media unfurls so the message stays compact. Escape content-derived labels rather than interpreting them as Slack mentions or markup. Include no full copy, transcript, file attachment, approval action or blanket channel mention.

For genuine time changes, use the corresponding reschedule opening above and show the old publishing time → the new publishing time for each changed piece. A mixed new/updated batch uses the neutral schedule-update opening, with changed rows clearly labelled. These times come from the audit's recorded values, not from a later overwrite of the calendar entry.

A saved date can belong to an in-review pack under the deployed behavior. **“Ready to publish” is a conditional statement, never the default for a successful schedule save.** At delivery, reuse the calendar's existing readiness checks (including `packs.blockers(..., approved=True)` and entry-level version/publication checks), once per pack with shared results across its notifications. Approval must match the manifest, and the pieces must have no applicable readiness warnings. If approval is pending, use the pending-review opening; for other warnings or an unavailable check, use the neutral opening. Do not invent a new gate, infer readiness from the presence of a date, or make a model call.

This requirement adds an existing-readiness assessment in the asynchronous sender; the earlier proposal to avoid that assessment no longer applies when the message explicitly claims readiness. Keep it out of the scheduling request and avoid repeating it for each piece. Refresh the opening's readiness classification before each delivery attempt, while retaining the referenced version's titles and recorded times.

Before posting an event's schedule, check that its entry is still active and matches the recorded publishing instant and content/manifest version. Omit rows whose schedule was replaced, cancelled, superseded or marked published before delivery; skip the notification if none remain. Do not announce readiness for a historical time that has already passed. Existing calendar data and checks remain the source of truth; this sender does not change them.

### Duplicate and change rules

- Replaying the same request ID produces no new source event and no new post.
- A new request that saves the same instant again produces no post, even though the existing service increments its revision. Compare the audit's old and new times as instants, not as differently formatted strings.
- A display-timezone-only change does not count as a publishing-time change for this general notice. The current event does not record the previous display zone; do not expand the scheduling audit contract just for this feature.
- A genuine reschedule produces a piece-specific update notice with the old and new publishing times through the same consumer.
- Cancellation notices and editing/deleting previous Slack messages are outside version 1. Do not change the current cancellation API or its relay restrictions.

## 4. Delivery design and why it is small

Flow:

1. The existing save commits its schedules, audit event and request receipt.
2. The scheduler discovers committed `schedule_saved` events not yet represented in its delivery ledger.
3. It derives the email/social groups from the recorded changes and stored assets, and records the intended piece titles, old/new publishing instants, links and destinations.
4. It claims a small number of pending deliveries and commits those claims.
5. It calls Slack outside the database transaction.
6. It records success or schedules a retry in a new, short transaction.

The source event is already durable, so discovery can happen on a later pass without changing `schedule()`. A Slack outage does not add HTTP work to the schedule request or roll back a saved calendar action.

### One additive delivery table

Proposed name: `slack_schedule_notifications`. Necessary information:

- Source event ID; request ID and pack ID for correlation.
- Logical destination (`email` or `social`) and the actual destination channel ID, captured when the delivery is created.
- Message text and per-piece metadata (title, slot key, old/new publishing instants, linked pack version), affected entry/asset references, and message version. Do not store the full piece copy.
- Status: `pending`, `sending`, `sent`, `failed` or `skipped`.
- Attempt count, next attempt time, claim token and lease expiry.
- Created/sent timestamps, returned Slack message timestamp and a sanitized last error code.

Enforce uniqueness on `(source_event_id, destination)`. Record no-op and non-applicable groups as skipped, so the consumer does not repeatedly inspect them. Keep delivery state separate from immutable audit events and editorial run status. Store no Slack credential in this table.

Discover events using an anti-join against the ledger, not a single “last timestamp” cursor. Concurrent transactions can commit out of timestamp order, and timestamps can tie; neither should cause a missed event. Add a narrowly scoped event index if the actual query plan requires it. Discovery and claim batches must be bounded.

### Activation without posting historical schedules

For each destination, the **first fully configured scheduler pass** must initialize a durable activation marker and mark all currently visible scheduling events skipped for that destination, in the same transaction under an initialization lock. It sends nothing for that historical set. A scheduling transaction not yet committed is not in that set; its later committed event is discoverable normally.

This defines a clear start boundary without relying on event timestamps. Write a structured “destination initialized” log before conducting the new-save acceptance check.

After initialization, ordinary restarts or temporary outages catch up from the ledger and unseen committed events. Use a fixed 24-hour event-age limit for version 1, marking older unsent notices skipped and recording that outcome, so a prolonged outage does not flood channels with obsolete notices. This limit is a proposed operational default, not an extra deployment setting.

Missing configuration pauses that destination without HTTP calls or consuming attempts. Changing a channel must not silently redirect already queued deliveries: retain the recorded target and require explicit reconciliation if it no longer matches the configured destination. Do not replay historical events into a newly selected channel.

### Claiming and retries

- Use short transactions and row locking with `SKIP LOCKED`, plus a committed claim token and expiry, to prevent two scheduler instances from sending the same pending row normally. Recover expired claims after a crash.
- Post through the existing HTTPX dependency to Slack's fixed `chat.postMessage` endpoint. Use a short request timeout and bound each pass to at most two HTTP attempts, at most one per actual channel. Do not hold a database transaction across the HTTP request.
- Treat a response as success only when HTTP handling succeeds and its JSON reports `ok: true`; store the returned message timestamp. Slack explicitly requires checking `ok`, even when HTTP succeeds. See the [API response documentation](https://docs.slack.dev/reference/methods/chat.postMessage/).
- For HTTP 429, honor `Retry-After`; persist a channel cooldown so the next queued notice does not immediately repeat the same failure. This bot may also post through another service, so do not assume Atelier controls its entire rate budget. Slack documents [per-channel posting limits and retry handling](https://docs.slack.dev/apis/web-api/rate-limits/).
- Retry transient transport/5xx failures with persisted backoff. Start with five attempts, with delays of 30 seconds, 2 minutes, 10 minutes and 30 minutes; a longer server retry delay wins. Use injected time in tests. No long sleeps inside the scheduler.
- Invalid credentials, missing permission, an unavailable destination or malformed payload should become visible failed deliveries requiring correction, rather than an endless retry loop.
- Keep a bounded number of attempts per pass and put this part after the scheduler's existing principal work. A slow or broken Slack call must not prevent the remaining error handling and heartbeat from completing.

The normal target is delivery on a subsequent scheduler pass, generally around its existing 30-second cadence when healthy. This is not a strict 30-second SLA: existing scheduler work, retries and outages can delay delivery. Freeze the per-piece message metadata when preparing the delivery so retries do not silently acquire different titles or dates; titles must come from the referenced pack version, and publishing times from the source event.

**Reliability boundary:** local deduplication prevents ordinary repeated saves or worker races from generating repeated deliveries. There is still a rare ambiguous case where Slack accepts a post but its response or the local success commit is lost. Retrying can duplicate the message. Do not promise exactly-once delivery across the network or assume an undocumented Slack idempotency guarantee. An informational notification is the proposed version-1 tradeoff.

### Why not the superficially shorter alternatives?

| Alternative | Tradeoff |
| --- | --- |
| Call Slack inside `schedule()` | Couples schedule response time and database work to Slack availability. Unnecessary because the durable event already exists. |
| Browser or in-memory background send after save | Fewer persistence changes, but a closed tab or process restart can lose notifications. |
| Generic pipeline job added to a scheduling run | Current scheduling audit runs are completed; the existing dispatcher selects active runs. Retrofitting that lifecycle adds unrelated executor/run changes. |
| Event polling with only a timestamp cursor | No adequate per-destination retry ledger and a risk of missing late commits. |
| Incoming webhooks | Suitable if no bot existed, but the owner prefers the existing bot. Avoid enabling and managing an additional channel-bound credential path. |

The table is the main additional implementation cost. It provides durable delivery without new infrastructure or changes to scheduling behavior. This is a small code feature, not something the current app can enable through configuration alone.

## 5. Implementation steps, once requested

### Step A — Confirm the existing bot and destinations

Confirm the app identity, secure token reference, both channel IDs and public Atelier origin. Check `chat:write` and membership. Reuse the existing credential and app; do not rotate tokens or broaden scopes automatically. Do not assume a valid inbound intake token can post to Slack.

Exit: four configuration inputs identified, with no credential recorded in documentation. No Slack messages are necessary during planning.

### Step B — Add durable tracking and configuration definitions

Add the delivery table as migration `012` if that is still the next free version at implementation time. Register it in `database.py`; generate its schema catalogue through the existing isolated-database tooling. Preserve migrations 001–011 and their catalogues unchanged. Adjust migration tests that explicitly enumerate the latest version.

Add the two destination settings with empty defaults and environment fallbacks. Use scheduler-side reads of the effective settings. Read the bot token only in the sender's runtime configuration; it must not become a model/run snapshot field or browser API field.

Exit: fresh migration, upgrade from 011, repeat migration and exact catalogue checks pass. Unconfigured behavior performs no HTTP calls.

### Step C — Build the bounded audit-event consumer

Add a small module dedicated to Slack schedule notices: activation/baselining, event grouping, ledger discovery, claiming, posting, retry classification and recovery. Integrate it as one independently handled part of `jobs/scheduler.py::tick`.

Leave `calendar/service.py`, `PackScheduling.tsx`, the Node relay allowlist and all approval/publishing behavior unchanged. Do not revive the earlier review's optional refactors or implement unrelated Slack digests/actions.

Exit: a committed synthetic save leads to the correct pending delivery groups with piece titles, saved publishing times and direct piece links; a mocked successful response records sent state; scheduling itself calls no Slack transport.

### Step D — Add focused verification and operating instructions

Add offline transport/formatting tests and isolated PostgreSQL integration tests. Document the four runtime inputs, start boundary, failure lookup, bounded retry behavior and disable procedure in `DEPLOYMENT.md` and the environment example.

Use existing structured logs plus the ledger for initial operations. Include read-only queries for pending/failed counts, oldest pending age and per-delivery error codes. Do not expand the alert-kind schema or add a notification dashboard in version 1. Document a targeted operator recovery procedure for a corrected failed delivery; do not automatically resend all failed rows.

Exit: tests below pass and a reviewer can explain exactly when, where and how many messages a save creates.

## 6. Expected file footprint

| File area | Planned change |
| --- | --- |
| `backend/backend_pipeline/notifications/` or one equivalently scoped new module | Dedicated consumer and sender, not a general notification framework |
| `backend/backend_pipeline/jobs/scheduler.py` | One bounded, independently handled scheduler part |
| `backend/backend_pipeline/settings_store.py` | Two optional destination definitions with environment fallbacks |
| `backend/migrations/012_slack_schedule_notifications.sql` | Delivery table, uniqueness/claim indexes and only any necessary event-discovery index |
| `backend/migrations/schema-catalog-012.json` and `backend_pipeline/database.py` | Register the additive schema version |
| Backend notification, scheduler, settings and migration tests | Focused coverage and latest-version expectations |
| `backend/.env.example`, `DEPLOYMENT.md` | Placeholders and operating instructions |

No frontend source, API response schema, generated frontend type, bot application service or model prompt change is anticipated. If the baseline moves, reassess the footprint before implementing.

## 7. Verification matrix

Use synthetic data and HTTPX mocks; no model calls or real Slack posts in automated tests.

| Case | Required result |
| --- | --- |
| First activation with an existing calendar history | Old events marked skipped; zero posts |
| A save that commits while activation is in progress | Seen as historical if included in the activation snapshot, otherwise discovered afterward; not lost by a timestamp cursor |
| Single email / single carousel / single Reel | Correct destination, working title, publishing time and exact piece URL |
| Five-piece batch | Exactly two normal delivery groups: email count 1, social count 4 |
| Partial batch / multiple genuine reschedules | Only affected, changed pieces counted; correct update wording |
| Piece-link navigation | Every link selects the correct Email/Carousel/Reel tab; sign-in preserves the destination |
| Message formatting / timezone / retries | Email subject and social titles match the referenced version; explicit calendar timezone, correct date boundaries, escaped labels, compact formatting and stable metadata on retry |
| Missing/invalid public origin | Visible configuration failure; no fabricated link or silent fallback to a count-only message |
| Request receipt replay | No second source action or delivery |
| New request with unchanged publishing instant | No notification; equivalent offset representations do not count as a change |
| Validation failure / stale revision / batch rollback | No committed event for the failed mutation and no notification |
| In-review pack | Existing scheduling behavior preserved; no claim of approval/publication |
| Scenario-dependent announcement | New ready pieces use the Content Atelier readiness opening; pending/unknown readiness uses an accurate alternative; reschedules do not claim new content |
| Readiness or schedule changes before delivery/retry | Opening reflects current checks, validation runs once per pack, and stale/cancelled/published schedule rows are omitted rather than announced as ready |
| No configuration / one destination missing / token absent | No calls for disabled destinations; ordinary scheduling unaffected |
| Two consumers racing / restart during a claim | Unique ledger rows; ordinary race deduplicated; expired claims recovered |
| HTTP 200 with `ok: false` | Not recorded as delivered |
| HTTP 429 / timeouts / 5xx / permanent permission error | Correct persistent cooldown/backoff or terminal failure; no busy retry loop |
| One route fails | Other destination and existing scheduler parts still run |
| Old unsent notice / changed channel config | Age policy and frozen-target policy applied explicitly |
| Capture of logs, settings and responses | No token or content body leakage |
| Database migration and catalogue checks | Fresh and upgraded schema match exactly; old migrations unchanged |

Run backend lint, OpenAPI drift, focused notification/scheduler/calendar/settings tests, migration/catalogue checks and broader applicable backend tests. Existing unrelated baseline failures must be reported separately rather than masked or silently fixed as part of this feature. No frontend redesign or broad test cleanup is a prerequisite.

After implementation is authorized, live acceptance should use an explicitly agreed test save and verify one concise post in each destination, every piece link and its publishing time, a same-request replay with no repeat, and a genuine time update. This planning session sends no messages and performs no live acceptance.

## 8. Deployment and rollback

1. Confirm the existing bot's membership, token reference, two intended channel IDs and public Atelier origin.
2. Deliver schema migration and backend code through the existing deployment process, initially with notification destinations unset. Coordinate API/editorial-worker releases that validate schema with the new schema version. The frontend and existing bot service need no configuration or application change.
3. Configure the four values on the existing scheduler, reusing equivalent established values where available. The two channel IDs can alternatively be stored through the existing settings mechanism; do not configure conflicting table and environment values.
4. Wait for the first configured pass to log both initialized destinations and skip pre-existing events.
5. Perform the agreed new-save acceptance check; inspect delivery rows and verify existing calendar behavior.

To stop notifications, remove the scheduler token or clear its effective destination settings, then restart it if changing environment values. Check for database overrides when clearing an environment fallback. Existing schedules and approvals are not changed; pending notices remain inspectable, and the age policy bounds later catch-up. Use a targeted reconciliation if the intent is to discard a paused backlog rather than resume it.

**Schema compatibility matters:** the current `database.check()` rejects unknown recorded versions. After migration 012, simply rolling backend images back to `52e7083` is not a safe rollback strategy. Normal rollback is to disable this feature while retaining the schema-compatible backend release. Any full image/schema rollback needs its own tested procedure; do not casually drop the table or alter migration records on production.

## 9. Remaining inputs and acceptance boundary

Required before setup: the existing bot's identity/credential reference, exact email marketing and social media channel IDs, public Atelier origin, and confirmation that it can post there. A bot's general ability to post somewhere does not establish access to both destinations.

Proposed defaults in this plan: immediate-after-save rather than due-time reminders; grouping per save/destination; concise piece-specific titles, publishing times and links; update notices for genuine reschedules; no cancellation notices; no history before first activation; 24-hour maximum age for unsent notices. These are implementation-plan assumptions for review, not changes already applied.

Done means a successful new save is noticed in the correct Slack channel through the existing bot, ordinary retries do not create duplicate delivery work, Slack failures do not interfere with scheduling, and the deployed scheduling workflow retains its current behavior.
