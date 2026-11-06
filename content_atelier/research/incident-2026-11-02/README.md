# November 1 weekly-cycle incident: production inspection

Inspection date: November 2, 2026. Production database snapshots were read at 12:20-12:22 PM IST (06:50-06:52 UTC). These checks inspect existing state and provider metadata. They do not import documents, activate connectors, retry the schedule, deploy changes, or purchase model calls. PostgreSQL confirmed `transaction_read_only=on` for both database inspections.

## Verified production evidence

- Railway project: Content Atelier (`3409333b-1844-456c-93f9-f572ba92eb92`), production environment.
- Frontend, API, scheduler, editorial worker, bulk worker and intake worker run commit `efedd191a100fa7e156aa8e0145e6e185e78c733`.
- Scheduler deployment: `2c503a8b-ea14-4de1-9a07-d992852cf111`.
- Production logs contain exactly three weekly-task failures in the inspected November 1 execution window. Application timestamps are 04:00:23, 04:00:53 and 04:01:24 America/Chicago, corresponding to 15:30:23, 15:30:53 and 15:31:24 IST.
- Each stack trace ends with `ValueError: Write the Fathom folders outside the repository (R48), not under /`.
- The deployed stack is `periodic.run_due` -> `schedule.run` -> `collect_window` -> `fathom_backfill.run` -> `outside_repository`. It stops before the call to list Fathom meetings.
- A read-only listing using the scheduler's configured Fathom key completed successfully and returned 18 recording IDs in the missed window: 2026-10-25 10:00 UTC inclusive to 2026-11-01 10:00 UTC exclusive. Some recordings may represent the same meeting; 18 recordings is not a distinct-call count or a verified missing-document count.
- The same listing found no recordings after the missed cutoff through the inspection time (2026-11-02 06:36 UTC). This states what this configured Fathom key returned, not that no meetings took place.

## Root cause

`config.py` derives `BACKEND_ROOT` from the installed package location. The folder guard takes `BACKEND_ROOT.parent` as the repository root. Locally this is the checkout; inside the image the package is `/app/backend_pipeline`, `BACKEND_ROOT` is `/app`, and its parent is `/`. The guard therefore rejects ordinary temporary paths underneath `/tmp` as if they were repository paths.

The weekly workflow calls collection before collector activation and before previewing or starting a cycle. These failed attempts therefore cannot create the weekly cards or a review document, and do not reach paid model or embedding work. Existing work and independently initiated work need separate inspection.

## Evidence files

- `deployment-evidence.json`: selected deployment metadata; no secrets.
- `fathom-metadata-evidence.json`: recording IDs, titles and timestamps only; no transcript bodies or credentials.
- `production-readonly-evidence.json`: deployed folder-check reproduction, the schedule claim, alert, collector state, documents, cycle history, output counts and recorded model activity.
- `recording-reconciliation.json`: the authoritative reconciliation of Fathom's 18 listed recording IDs against all 14 documents in the missed window, including documents marked as duplicates. The initial canonical-only lookup in the production evidence's `already_imported` field omits two stored duplicate documents; this reconciliation corrects that interpretation without discarding the initial evidence.
- `collector-readonly-evidence.json`: pending source, collection requests and job retry state.
- `temporary-access-cleanup.json`: receipt confirming the dedicated temporary Railway SSH registration was removed and its private/public key files deleted. A final CLI check confirmed no Railway SSH keys remained registered. The earlier temporary registration of the existing personal key was also removed; its local key files were untouched.
- `inspect_production.py`: read-only diagnostic. SQL sessions set `default_transaction_read_only=on` and a statement timeout. Credentials are obtained in memory and never printed or saved. `--fathom-list` lists provider metadata only; `--inside-container` uses the deployed private database connection and also exercises the path guard without creating transcript files.
- `temporary_ssh_diagnostics.py`: creates a dedicated diagnostic key following explicit user approval, uses it only for read-only inspection, revokes its registration in a `finally` block and deletes the exact newly created key files. No private key is stored in this evidence directory.

## Actual production impact

### The missed weekly run is confirmed, and has not recovered

The database's `schedule.weekly_cycle.2026-11-01` claim is `failed`, with `attempts: 3` and the same folder error. Its last update was November 1 at 15:31:24 IST. It is the only weekly schedule claim. The alert remained unresolved and had 2,472 observations at the snapshot. That count represents alert scans, not 2,472 failed generation runs.

The scheduler heartbeat was current within seconds of the inspection. The process being online therefore does not establish that the weekly task completed.

All weekly cycle rows were inspected (there are four, fewer than the query's limit of twelve). The latest was manually started on October 25 and covers October 18-25. There is no November 1 cycle and no later manual recovery cycle. Since the November 1 scheduled cutoff, the database contains zero newly created angle rows, brief rows and content-pack rows. The missed task did not reach cycle creation, generation or review-document creation. The number of cards that would have been produced cannot be determined without executing generation; zero actual new rows is not an estimate of the missing card count.

### Correction to the initial collector-activation concern

The hourly Fathom collector was already activated on **October 27, 2026, at 16:42:59 IST** (11:12:59 UTC). It ran before the failed November 1 weekly task. The possibility raised in the initial code-only assessment that this failure prevented the collector's first activation does not apply to the observed production state.

There are **14 imported transcript records** for the missed weekly window. Two are marked as duplicates, leaving **12 included, nonduplicate documents**; all twelve have completed scene extraction. The weekly generation was therefore blocked even though substantial source material had already arrived and been processed.

Of Fathom's **18 currently listed recordings**, **13 already have corresponding database documents**, including those two duplicates. One additional document in the database has a recording ID not returned by the current listing. It is not counted as missing or deleted; current provider visibility alone does not establish why it is not listed.

### The missing recordings

Five listed recording IDs have no corresponding transcript anywhere in the database, and there is no stored document within ten minutes of their occurrence. All five were recorded on October 26, before collector activation. The collector intentionally starts at activation; weekly catch-up was supposed to fill the earlier gap and failed before doing so.

| Recording ID | Fathom title | Occurred, IST |
| --- | --- | --- |
| 196273263 | Check-in with Gisselle | October 26, 20:07:26 |
| 196306102 | Google Ads Weekly Team Meeting | October 26, 20:52:50 |
| 196305821 | Google Ads Weekly Meeting | October 26, 20:53:54 |
| 196331219 | Meta Ads Weekly Team Meeting | October 26, 21:31:09 |
| 196389453 | WIA Weekly Meeting | October 26, 22:37:38 |

The two Google Ads recordings may be captures of one meeting. No transcript bodies were downloaded to compare them, so five is a verified missing-recording count, not a verified distinct-meeting count. Their eventual eligibility for generation also requires normal classification; titles alone do not establish it.

### Costs

The three failed weekly attempts stopped before provider collection, imports, embedding, extraction or generation. They therefore caused no model or embedding charges through that task. A separate `context_mining` call succeeded after the scheduled cutoff at a recorded cost of USD 0.075260; this is unrelated background work. No total application spend of zero is claimed.

## Separate collector problem discovered during inspection

The collector is active but its connection health is `pending` with `Fathom HTTP 429`. At the snapshot:

- 53 collection jobs had completed.
- 87 collection jobs were waiting, with five to 91 attempts each. Their requests were marked `pending_transcript`, beginning with windows on October 29, before the November 1 weekly failure.
- One source, recording `197260974`, was marked `pending_transcript` even though it already had an imported revision. Its last successful transcript check was October 28. Recent worker logs show repeated HTTP 404 and HTTP 429 responses for this recording's transcript endpoint.
- The discovery checkpoint had still advanced to November 2, 11:33 AM IST. Advancing discovery is not equivalent to completing all transcript retrieval or completing the weekly bucket.
- The previous intake bucket was still `collecting`; the new week's bucket was `open`.

The code explains how these states can coexist: `intake/fathom.py` rechecks global pending/stale sources during each collection request, advances the discovery checkpoint before transcript retrieval, and raises `PendingTranscript` if any selected source is unavailable. The client maps a 404 to `PendingTranscript`. A previously stored recording that later becomes unavailable can therefore keep unrelated collection requests incomplete. Each request has its own retry/backoff, so many requests can repeatedly hit the same source. The observed repeated requests and 429 responses are consistent with this amplification. The provider's underlying reason for returning 404, and whether this retry behavior is the sole cause of rate limiting, have not been established.

This is a separate issue that predates the weekly folder failure. It does not show that all collection stopped or that 87 calls are missing: 87 is a count of collection requests/jobs. Existing source revisions remain stored. Pending health with a recent checkpoint also does not meet the current alert detector's error-or-stale-checkpoint condition, explaining why the screenshot need not show a second collector alert.

## Recovery work indicated by the evidence

1. Correct the folder guard so it identifies the actual source/repository boundary in both checkout and Docker layouts; verify the deployed-layout case before redeployment.
2. Reconcile/backfill the five missing recording IDs with duplicate checks and normal classification, preserving existing documents and completed extraction.
3. After the fix, explicitly retry the November 1 scheduled period in a controlled manner. Its three-attempt claim persists through process restarts. Check the preview and existing runs first to prevent duplicate work. Verify cycle creation, generated cards and the eventual review document.
4. Investigate the unavailable recording and isolate per-source retry state from unrelated collection requests. Preserve its existing revision, avoid treating every 404 indefinitely as first-time publication delay, coordinate rate-limit backoff, and verify the waiting requests and collecting bucket can settle.

No recovery mutations or application-code changes were made as part of this inspection. Temporary account access was removed after use.
