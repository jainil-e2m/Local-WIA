# Real content packs and calendar

The Atelier calendar and scheduling views read PostgreSQL. No mock calendar entries or browser-local schedules are imported. Empty storage produces an empty calendar.

> **Status (22 October 2026).** Written for the 004 release. The production deployment (Railway services, the queue workers, the variables) is in `DEPLOYMENT.md`; this page covers only what is specific to packs and the calendar. Where an earlier version of this page named a command or file the code does not have, it now says so: `storage_cli` has no `calendar-migrate` command (`migrate` applies migration 004 with the rest), and there is no `compose.storage.yml` or `compose.editorial.yml` (the local stack is `backend/compose.yml`).

## Upgrade and run

1. Back up the target database and inspect existing content_packs, content_assets and calendar_entries. Migration 004 is additive and does not invent historical provenance. Conflicting legacy status values or active duplicates must be resolved deliberately; do not delete them to force an upgrade.
2. Configure the same ATELIER_DATABASE_URL, ATELIER_ARTIFACT_ROOT and ATELIER_API_SECRET on the Python API and editorial worker.
3. From the backend directory run:

~~~powershell
python -m backend_pipeline.storage_cli migrate
python -m backend_pipeline.storage_cli check
~~~

`migrate` applies every migration up to the latest, including 004 (packs and calendar), in one transaction. It is explicit, transactional and repeatable. Startup never runs DDL. (There is no separate `calendar-migrate` command.)

4. Set the production/calendar settings in storage.env.example. Start the API, the scheduler and an editorial worker (ATELIER_REDIS_URL must be set on all three):

~~~powershell
python -m uvicorn backend_pipeline.api:app --host 127.0.0.1 --port 18081
python -m backend_pipeline.jobs scheduler
python -m backend_pipeline.jobs worker --queues interactive,default
~~~

The worker is a separate long-running service, not a one-time job. Pack stages run on the `interactive` queue (`backend_pipeline/jobs/policy.py`); angle and brief stages share the same worker. Source intake and media extraction keep their own queue workers (`--queues intake`, `--queues media`). No calendar worker is needed.

The local Docker stack is `backend/compose.yml` (Postgres, Redis, the migration, the API, the scheduler and every worker; `docker compose up -d --build` from `backend/`). It reads `backend/.env`, and still reads `.env.storage.local` when it exists. Set provider credentials as backend environment variables; never put them in frontend VITE variables.

5. Point the frontend BFF's ATELIER_BACKEND_ORIGIN to the new API origin, and set its matching ATELIER_API_SECRET. Existing Command Center auth configuration remains necessary.
6. Deploy the frontend. Weekly Studio now uses the actual angle/brief review APIs; its pack and schedule tabs and Home's calendar use the new production/calendar APIs.

## Capabilities and readiness

- ATELIER_PACKS_ENABLED=true enables actual pack reads/production queueing.
- ATELIER_CALENDAR_ENABLED=true enables calendar reads and writes.
- ATELIER_CALENDAR_TIMEZONE=Asia/Kolkata preserves the current IST publishing plan. This is separate from intake's America/Chicago cutoff.
- ATELIER_PACK_EDITORS and ATELIER_PACK_APPROVERS are comma-separated trusted actor IDs.
- ATELIER_CALENDAR_SCHEDULERS is a separate comma-separated trusted actor list.
- Identity is derived by the BFF from the verified Command Center user ID, falling back to email when that account has no ID. Use the same representation in capability lists.
- Pack generation requires explicit exact ATELIER_PACK_WRITER_MODEL and ATELIER_PACK_REVIEW_MODEL values. There is no silent model fallback.
- Real inference additionally requires both ATELIER_ALLOW_GENERATION=true and ATELIER_ALLOW_PACK_GENERATION=true. Both stay false by default. Enabling UI reads or scheduling does not enable inference.

Use the existing real Gate 1/Gate 2 capability and configuration requirements to approve the source brief. Its backend blockers remain enforced. Generate a pack explicitly from a consumable approved brief; approval alone starts no new production requests.

Replay uses only compatible saved responses and fails honestly on a cache miss. Deployment is not authorization for paid inference. Tests use a dedicated database ending in _test with synthetic providers, and make no external model calls.

The API reports worker liveness using shared-volume heartbeat files. API and worker must share the artifact volume; API health alone does not prove a worker is available. A queued pack may wait until the worker starts.

## User workflow

Weekly Studio: approve actual stored angle/brief → Generate saved content pack → inspect five saved assets and production findings → approve the exact pack → choose a whole-pack or individual publishing time → Confirm schedule.

Confirm waits for the database transaction before showing success. Home and Scheduled Content read the same entries. Pack summaries show partial scheduling, such as 2/5. Each card opens its exact backend asset.

Rescheduling requires the current revision. A conflicting change requires a refresh/review before confirmation. Cancelled entries remain in audit history. An overdue date stays scheduled; it does not become published.

## Boundaries and rollback

Saving a date is a shared publishing plan. It does not send an email, upload media or publish on Instagram. Those provider integrations are a separate release.

Legacy prototype ideas in other screens cannot feed the real calendar. Their local storage is left intact and is never uploaded as real schedules.

Before rollback, disable live generation and clear the production/approval/scheduler capability lists while keeping ATELIER_PACKS_ENABLED and ATELIER_CALENDAR_ENABLED true for reads. Restart the API and worker to apply configuration. Retain saved schedules, receipts and audit events. Roll back only to an API-backed calendar build; never restore mock calendar fallback. Prefer keeping the additive schema.

## Verification

Python integration tests use ATELIER_TEST_DATABASE_URL and refuse a database whose name is not atelier_test. Initialize a disposable PostgreSQL/pgvector database with storage_cli init first. Never point the test URL at the application database.

~~~powershell
python -m pytest -q backend_pipeline/tests/test_calendar.py backend_pipeline/tests/test_briefs.py backend_pipeline/tests/test_sql_storage.py
npm --prefix ../frontend run lint
npm --prefix ../frontend test
npm --prefix ../frontend run build
~~~

The calendar tests cover full-pack atomicity, single-piece scheduling, duplicate request receipts, conflicts, native concurrent schedulers, cancellation, permissions, source-version warnings, publication-history separation and failed production-stage reuse. Browser acceptance should additionally verify confirmation wait/error handling, refresh and a second authenticated browser.

### Browser acceptance runner

The calendar's standalone browser runner (`frontend/tests/calendar.acceptance.mjs`, against an external fixture BFF) drove
the version 1 pack scheduling, which is gone (D43e: no screen schedules a pack). It was replaced by the frontend's browser
end-to-end test (6.X1): `npm run test:e2e` from `frontend/` builds the real app and drives Chromium through the real Node
server against a stubbed backend and Command Center session endpoint, needing no database and no outside service
(`frontend/tests/e2e/`, `frontend/README.md`, "Browser end-to-end test").
