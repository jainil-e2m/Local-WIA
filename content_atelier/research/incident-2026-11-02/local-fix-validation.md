# Local validation: weekly Fathom folder guard

Date: November 2, 2026. Implemented locally; not committed, pushed, deployed, or used to retry production.

## Change

The only application change is two lines in `backend/backend_pipeline/documents/fathom_backfill.py`. When the inferred repository is a filesystem root, the validator protects `BACKEND_ROOT` instead. In the Docker image this protects `/app`, allowing the scheduler's temporary output under `/tmp`. The normal checkout boundary and its existing research exception remain intact.

No frontend, configuration, Dockerfile, schema, scheduler implementation, schedule settings, retry limits, collector state or production data changed.

## Verification

- The three new external-folder regression cases failed against the original validator and passed after the fix.
- The final focused suite passed **41 tests, with no skips or failures**, against an isolated temporary local PostgreSQL 17 + pgvector container and synthetic fixtures. Coverage includes the complete Fathom backfill suite, weekly schedule suite, scene-ledger reuse suite, backend path suite, and five existing periodic-task claim/retry tests.
- A new integration test calls the real `schedule.collect_window` and real backfill with only Fathom HTTP replaced by `httpx.MockTransport`. The first call imports and normalises a synthetic recording; a second call imports nothing, creates no additional runs/jobs/documents, and does not fetch the stored transcript again.
- The folder tests cover `/tmp`-equivalent, artifact and sibling directories; application code and path traversal back into it remain blocked.
- Added explicit future schedule expectations for November 8, 15 and 22, 2026, and March 14, 2027 after the daylight-saving transition. The cutoff stays Sunday 04:00 America/Chicago.
- A separate Linux container check used the actual `/app/backend_pipeline` installation layout with the patched source mounted read-only. It accepted a real temporary directory and rejected `/app`, application-code output, and traversal into application code. The container had no network access.
- Repository backend Ruff checks passed. OpenAPI drift check reported `backend/openapi.json is current`. `git diff --check` passed.

The PostgreSQL tests used a loopback-only random port, a new throwaway server with temporary storage, and fixture-controlled test database names. Outbound HTTP and model calls were forbidden by the existing test fixtures. The temporary database container was stopped and removed after verification.

## Next production step

After review and the separately requested GitHub push/deployment, verify the scheduler runs the corrected commit. Only then re-check for a recovery cycle and re-arm the single exhausted `schedule.weekly_cycle.2026-11-01` claim. That production operation has not been performed. The independent collector retry/429 issue remains outside this patch.
