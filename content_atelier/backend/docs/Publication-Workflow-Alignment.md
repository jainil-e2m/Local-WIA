# Publication workflow alignment

Implementation: 6 November 2026.

The current content-pack workflow is approved brief → generated pieces → saved publishing schedules → Slack notices → external publication → manual publication records. Current V2 packs do not need a second whole-pack approval to schedule or to record publication. Governing brief approval, role checks, content/version integrity and editorial findings remain in force.

## Calendar semantics

Calendar reads now run V2 editorial checks independently of legacy pack approval. An absent whole-pack approval no longer creates a warning. Real editorial findings, changed brief approval, superseded packs, unfinished runs and mismatched content remain visible. Legacy V1 validation keeps its existing approval policy.

The existing published-content register remains the source of publication facts. A matching manual mark gives a planned entry `effective_status=published`, a `publication` detail object and `overdue=false`. Its original database status, planned time and revision are retained as scheduling history. Recording publication does not require cancelling the plan and does not publish content to a provider. Genuine content warnings remain available beside the completed status; completion does not erase a content issue or turn it into an overdue schedule.

`GET /storage/calendar` supports:

| status | Results |
| --- | --- |
| active (default) | Planned entries without a publication record |
| published | Completed entries, including manually marked V2 pieces |
| all | Active and completed planned entries; excludes cancelled/draft plans |

Publication filtering occurs in SQL before pagination. This applies to records written before deployment without a backfill. Publication of one piece does not complete its siblings. Unscheduled publication records remain accessible on the pack; this view does not manufacture calendar rows for them.

The frontend calendar requests `status=all`, displays manual Sent/Published badges and preserves the planned calendar position. It uses the backend's publication fact; cached pack details remain available for permissions and compatibility during rollout.

## Pack presentation

The legacy `in_review` and `ready_to_publish` API states and approval history remain stored for compatibility. Both present as Generated in the current pack library. The new `state=generated` list filter combines those states before pagination; old API filters retain their meanings, while old frontend filter links open the combined generated view.

The studio's awaiting-publication count includes generated packs that have unpublished pieces, independently of old approval state. It excludes unfinished and fully published packs. Home combines the old backend count fields into a Generated line. Weekly planning notes, exported documents and edit messages no longer instruct users to approve a pack or return it to review. Content checks and existing source approvals are retained.

## Slack

The sender continues to consume committed schedule_saved events and say scheduled for publishing. It does not certify editorial readiness or platform publication. No channel or credential changes are required for this alignment. The current testing channel mapping remains C0C3FT6DZAS for both routes.

## Deployment and compatibility

This alignment adds no database migration and does not rewrite approval or publication history. The separately implemented Slack feature still requires migration 012 and its schema catalogue.

Deploy the updated backend before the updated frontend: the frontend uses the additive `all` calendar filter and `generated` pack filter, which older backend/relay code does not accept. The frontend image includes the updated relay allowlist. Regenerated backend/openapi.json and frontend/src/api/schema.d.ts must ship with the source.

For the combined release, run the existing migration command using the new backend image, then deploy schema-compatible API/workers/scheduler services and the frontend. Older schema-011 services cannot simply be rolled back against a database migrated to 012. Disabling Slack does not require undoing the schema.

Slack configuration remains separate from code deployment. The backend image does not include backend/deploy/. Configure the scheduler's token, destination IDs and public HTTPS app origin through Railway variables or separately apply database settings. Database settings take precedence over the channel/origin environment fallbacks. Never upload local preview scripts, environment files or synthetic databases.

## Acceptance checks

- A clean generated V2 pack saves schedules without pack approval and returns Scheduled without approval warnings.
- Genuine content findings and revoked governing brief approval remain visible; invalid/unwritten pieces and unauthorized changes are refused.
- Manual publication is recognised by calendar reads and filters, clears overdue status and preserves original planned history and sibling schedules.
- Pagination excludes completed entries from active results before applying offsets and includes them in published/all results.
- The combined generated filter includes both legacy states without changing approval records.
- A real API scheduling save produces two mocked Slack notices, receipt replay produces none, and manual publication completes only the intended piece while pack approval remains pending.
- Existing legacy calendar, content-version, retry, weekly export, frontend route and browser tests are rerun with the new semantics.

Verification logs are kept locally under backend/.test-runs/approval-alignment-* and frontend/.qa/approval-alignment-*. Production settings and data are not modified by these checks.

## Verified results, 6 November 2026

- 90 distinct targeted backend checks passed across the broad regression and final follow-up runs: current/legacy calendar behavior, time/role/version validation, weekly planning and Markdown/Word exports, all 41 Slack tests and all 19 migration tests. The final five-test follow-up also verifies a genuine warning beside a completed publication and repeats the real API → mocked Slack → manual publication flow.
- The broad backend run initially had two test-only assertion errors (ISO response timestamps versus PostgreSQL datetime objects, and assuming batch output was in piece order). Those assertions now check the correct types and identify the email by slot. A local database also needed its first migration before the legacy idempotence assertion; that migration and its repeat were verified. Final follow-up: five passed, no failures.
- Frontend unit checks with bounded concurrency: 535 passed, two existing failures, one skipped. The retained baseline failures are the inline response shape in PackScheduling.tsx and its import of PackSchedulePopover.tsx, which is classified as demo code by the existing architecture assertion.
- Full relay suite: 84 passed, two existing failures in server/packs.test.mjs, which still expects the already-supported scheduling route to be rejected. The changed relay/filter checks passed (19 tests in the focused relay run).
- All three production-build Chromium suites passed: broad application/authentication/document acceptance, manual publication/calendar/mobile behavior (including a real warning beside a completed badge), and session polling. TypeScript, backend Ruff, OpenAPI drift and whitespace checks passed. Generated API types were regenerated from the updated OpenAPI document.

These results verify this feature's regressions; they do not certify the entire repository CI green. The four baseline frontend/relay failures remain explicit and were not bypassed by weakening tests or changing the previously retained scheduling implementation. Test transports prevent live provider/Slack requests.
