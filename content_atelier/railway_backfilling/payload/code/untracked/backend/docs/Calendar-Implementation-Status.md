# Calendar implementation and verification

Date: 16 October 2026

Status: Implemented and verified locally. Production activation has not been performed.

## Delivered

- Additive migration 004, exact recognized catalogs for all supported baseline/brief/intake combinations, and an explicit calendar-migrate CLI command.
- Genuine five-slot pack production from an approved backend brief, using eight jobs on the existing SQL worker. Models and execution contracts are explicit; live generation remains disabled by default.
- Frozen approved brief/brand/evidence inputs, per-slot response reuse, production validation, manifest-bound human approval and replacement lineage.
- Whole-pack and per-asset schedule persistence, optimistic revision checks, transaction receipts, concurrency protection, rescheduling, cancellation and before/after audit events.
- Authenticated pack/calendar API routes and narrow BFF method/query allowlists.
- Home month/week/day calendar, daily modal, pack library, exact asset detail and Weekly Studio production/scheduled tabs connected to actual backend records.
- Source passages, claims/qualifications and validation findings available during pack review.
- Mock calendar feeds and localStorage scheduling removed from active scheduling surfaces. Legacy fixture code used by old tests is isolated under frontend/src/testing.
- Confirmed publication history separated from planned schedules; due time never becomes publication.
- Worker liveness reporting, an editorial Compose overlay, deployment/settings documentation and narrow-screen calendar improvements.

## Verified results

| Check | Result |
| --- | --- |
| Full offline Python suite | 265 passed, 100 environment-dependent tests skipped. |
| Native PostgreSQL 17 / pgvector scheduling, brief and storage suites | 47 passed, including concurrent schedulers and failed-slot recovery. |
| Migration variants on a second native database | All four baseline/brief/intake combinations passed, including repeat application and subsequent additive upgrades. |
| Frontend tests | 119 passed, one pre-existing environment-dependent source audit skipped. |
| Node BFF/auth/proxy tests | 15 passed. |
| New backend modules/tests lint | Ruff passed. |
| Frontend typecheck and production build | Passed. |
| Built-app browser acceptance | Passed against the actual Node BFF, Python API and native database. |

The browser run used synthetic records in an explicitly isolated database. It exercised approved-brief replay → saved pack → exact-manifest human approval → failed-save recovery → five saved schedules → exact asset drilldown → individual rescheduling → reload → a second authenticated browser → cancellation. It also verified the empty calendar and narrow-screen day view with no horizontal page overflow.

All content production during verification used synthetic providers or compatible saved responses. No paid LLM, embedding or publishing request was made. No application/production database was migrated or seeded.

The offline command intentionally omitted SQL/optional connector environments; the 47 relevant native SQL tests were run separately. Unrelated optional connector/backfill integration environments were not enabled.

## Files and reproduction

- Implementation specification: Content-Atelier-Implementation-Plan-Calendar.md.
- Activation and rollback: Calendar-Deployment.md.
- Native acceptance: backend_pipeline/tests/test_calendar.py.
- Offline contract checks: backend_pipeline/tests/test_calendar_contracts.py.
- Migration-order verifier: scripts/verify_calendar_migrations.py; refuses any database except atelier_calendar_migration_test.
- Browser runner: frontend/tests/calendar.acceptance.mjs; npm run test:e2e, using a loopback-only fixture deployment.

Raw verification logs and desktop/mobile screenshots are retained under the ignored .qa directory. Generated synthetic test artifacts are ignored under testing/.calendar-*.

## Activation boundary

Apply migration 004 to the intended backed-up database, configure read/actor/timezone settings, point the BFF to the API and start the shared-volume editorial worker as described in Calendar-Deployment.md. Calendar scheduling itself needs no worker; production generation does.

Exact production writer/reviewer models and permission to make live calls must be configured deliberately. External publishing, email sending, media uploads and publication confirmation remain a separate release.
