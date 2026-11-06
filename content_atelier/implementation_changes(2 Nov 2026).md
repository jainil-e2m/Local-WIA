# Implementation changes — 2 November 2026

This record covers the Content Atelier production incident investigated on 2 November 2026, the deployed backend fix, and the approved recovery of the missed weekly run. It distinguishes the permanent application change from the temporary production recovery steps. Times below are in IST unless otherwise stated.

## Outcome

The missed 1 November weekly cycle was recovered successfully. Collection and scene extraction completed, and a subsequent input-size blocker was worked around for this run only. The existing pipeline generated five content-angle cards and their review documents. The cards reached Gate 1 for human review; recovery did not approve or publish them.

The permanent fix was committed as `9b50c9d047a2d1005b19fbd80fea5f9e2476a32b` and deployed to the relevant backend services. The input-size recovery required no additional application implementation, deployment, model change, or global configuration change.

## Issue and fix summary

| Issue | Actual cause | Fix applied | Scope |
| --- | --- | --- | --- |
| Weekly collection rejected its temporary output folder | In Docker, the folder validator inferred `/` as the repository root instead of `/app`, so it incorrectly blocked `/tmp`. | If the inferred boundary is the filesystem root, protect `BACKEND_ROOT` instead. Temporary output is accepted while application-code directories remain protected. | Permanent backend code fix; deployed. |
| Redeployment did not automatically recover the missed weekly task | The database retained the 1 November schedule claim with all three attempts exhausted. Restarting the service did not reset that claim. | After checking for an existing recovery cycle, reset only that claim's attempt counter from three to zero under the existing scheduler lock. The normal scheduler collected the missed window and created the cycle. | One-time production recovery; claim is now done and must not be reset again. |
| Card generation refused to send the recovered week's request | The local conservative byte-based allowance plus margin was 945,520, exceeding the cached 922,000 prompt limit. This was not a measured-token overflow or a provider rejection. | For one generation attempt, omit seven already-internal-only scenes, keeping all public-eligible scenes. The 284-scene request passed preflight at 897,723. Retry only the failed generation job, then restore the original 291-scene extraction result and retain accurate sent-ID coverage. | Temporary run-specific workaround; completed. The input-sizing safeguard itself was not changed. |

These actions recovered the existing workflow. They did not introduce a replacement scheduler, change future weekly cutoffs, raise global input limits, or delete source material.

## 1. Weekly collection failed because the Docker folder boundary was misidentified

### Observed issue and impact

The Home and Sources alerts reported that a scheduled run did not happen. Production logs and the stored weekly claim confirmed this error:

```text
ValueError: Write the Fathom folders outside the repository (R48), not under /
```

The scheduler attempted the 1 November weekly task three times and exhausted its retry allowance. The error occurred before Fathom meeting discovery, collection, or creation of the weekly cycle. Those failed attempts did not reach paid model or embedding work. Existing documents and previous extractions remained stored.

An online scheduler service did not mean the weekly task had succeeded. The alert's repeated observation count also did not represent thousands of separate failed runs: the stored claim recorded three failed attempts.

### Root cause

The backfill validator inferred the repository boundary from `BACKEND_ROOT.parent`. In the production image, the backend is installed under `/app/backend_pipeline`, so `BACKEND_ROOT` is `/app` and its parent is `/`.

The guard consequently treated the entire filesystem as the repository. It rejected the scheduler's legitimate temporary output under `/tmp` because every absolute directory falls beneath `/`.

### Permanent fix

Updated the Fathom backfill folder validator, `outside_repository()`:

```python
project = BACKEND_ROOT.parent.resolve()
if project.parent == project:
    project = BACKEND_ROOT.resolve()
```

When the inferred boundary is the filesystem root, the guard now protects the actual backend directory instead. This allows external temporary folders while continuing to reject writes into application code. Normal checkout behavior and the existing research exception remain intact.

The backend commit contained the validator correction and regression coverage for folder validation, collection duplicate prevention, and future weekly schedules.

The commit did not change the scheduler architecture, Dockerfile, database schema, model settings, weekly cutoff, or retry policy.

### Local validation

- The new external-folder regression cases reproduced the original failure and passed with the fix.
- The focused suite passed **41 tests**, with no failures or skips, using isolated local PostgreSQL fixtures.
- The real collection/backfill integration path was exercised with mocked Fathom HTTP. A second collection did not duplicate documents, jobs, or runs, and did not fetch the stored transcript again.
- A Linux check using the production `/app/backend_pipeline` layout accepted temporary output and rejected application-code output, including traversal back into it.
- Schedule tests covered 8, 15 and 22 November 2026, plus 14 March 2027 after the daylight-saving transition. The intended Sunday 04:00 `America/Chicago` cutoff was preserved.
- Backend Ruff checks and the OpenAPI drift check passed.

### Production recovery after deployment

Deployment alone could not retry the missed task: the exhausted claim persisted in the database across restarts.

After verifying the deployed fix and checking that no recovery cycle already existed, the single claim `schedule.weekly_cycle.2026-11-01` was re-armed under the scheduler's existing advisory lock. Its attempt counter was reset from three to zero at **13:47:29**. The existing scheduler then performed the recovery and marked the claim done at **13:48:02**.

No second scheduler or separate collection mechanism was started. The completed 1 November claim must not be reset again for this incident.

Collection reconciled the five missing Fathom recordings: all five were fetched, four became new documents, and one duplicate was skipped. The recovered cycle included 16 documents. Scene extraction reused 12 previous document extractions and made four new extraction calls, costing **USD 0.043645**. It produced **291 verified scenes**; six additional unverified scenes were excluded from proof.

## 2. The recovered cycle then hit the card-generation input-size safeguard

### Observed issue and root cause

Collection and extraction succeeded, but card generation stopped with:

```text
Whole-week token budget exceeded; no request sent. No batching or truncation permitted.
```

The generation stage assembled the week's verified scenes together with instructions and the response schema into one request. Its local preflight used a conservative UTF-8 byte-based input allowance plus a margin, rather than a measured native token count.

| Saved preflight measure | Original request |
| --- | ---: |
| Conservative input allowance | 859,563 |
| Additional margin | 85,957 |
| Allowance including margin | 945,520 |
| Cached prompt limit | 922,000 |
| Excess over prompt limit | 23,520 |
| Output reserve | 32,000 |
| Cached total context capacity | 1,050,000 |

The prompt-only check failed even though the total-context check retained headroom. This was an application safeguard refusing to send the request, not a provider rejection or a spending-limit failure. The cached capacities were the route values used by this run; they were not changed or presented as an independently verified current provider maximum.

Completed collection and extraction results remained available, so recovery did not require repeating them.

### Approved temporary workaround

The selected input was reduced from **291 to 284 verified scenes** for this generation attempt only. The seven omitted scenes were already classified as `internal_only` in both consent and effective handling. They were not removed merely for having lower confidence.

The selection retained:

- **All 169 scenes allowed by existing handling for public consideration.** Publication still requires normal review.
- **115 of the 122 internal-only scenes.**
- Representation from **all 16 documents**.
- The original dialogue and evidence ranges for every retained scene.

Original scene references omitted: `S85`, `S129`, `S138`, `S139`, `S158`, `S162`, and `S182`.

The approved seven-scene reduction preserved all public-eligible evidence. Omitting internal context can still influence model selection or ranking; identical output was not guaranteed.

The reduced preflight allowance was **816,111**, plus **81,612** margin, totaling **897,723** against the unchanged **922,000** prompt limit. It passed with **24,277** headroom. The model, instructions, schema, output reserve, and global limits were unchanged.

### Local validation and production execution

Seven focused checks against a throwaway local PostgreSQL database verified the unchanged worker's original/reduced read behavior, preservation of source records, stale-update rejection, generation-only retry, restoration, and honest coverage reporting. Six additional checks verified atomic rollback, duplicate-retry prevention, refusal to restore during active generation, and idempotent restoration. These were focused database rehearsals, not a complete production-equivalent model pipeline test.

After explicit approval, Railway CLI access was used to:

1. Recheck production state and preserve the original extraction result and approved selection.
2. Temporarily replace only this run's extraction result ID list with the approved 284 IDs, using expected-state guards.
3. Atomically request **one retry of the existing failed generation job** through the normal repository mechanism.
4. Verify that the worker's saved outgoing request matched the approved request.
5. Restore the original 291-ID extraction result after generation terminated and reconcile the saved coverage with the actual 284 IDs sent.

The temporary change was applied at **17:46:35**. Final recovery integrity was verified at **17:57:19**.

No original moment or transcript record was deleted, shortened, or reclassified. No successful extraction was restarted. A temporary restoration watchdog was removed after completion, and temporary diagnostic SSH registrations and key files were removed.

## 3. Verified recovery result

| Item | Recorded result |
| --- | --- |
| Production project | Content Atelier, production |
| Recovered week | `week_2026-10-25` |
| Original collection window | 25 October 10:00 UTC through 1 November 10:00 UTC |
| Recovery cycle | `run_113a8c5a0b384cfba61e6fc7b59367ee` |
| Retried generation job | `job_6f34d2bb0a994017bb711a1e752194ca` |
| Cycle status at recovery completion | `waiting_for_review` — Angles ready for Gate 1 |
| Generated cards | 5 |
| Generation, verification, embedding and matching | Completed |
| Verification readiness | All five `needs_check`, zero blocking flags |
| Review exports | Markdown and Word documents created by the existing scheduler |
| Original extraction result | Restored to 291 verified scene IDs |
| Actual generation coverage | 291 verified, 284 sent, 7 intentionally not sent |

Coverage remained explicitly incomplete because seven verified scenes were deliberately omitted. This was an honest coverage record, not a failed pipeline stage or a consent-based exclusion.

Generated cards at recovery completion:

1. What we build follow-up around
2. How we reconsider advice during an ads audit
3. How we build the next round of ad creative
4. What our ad specialists share before strategy calls
5. How we decide whether to build an ads landing page

| Stage | Recorded model | Input tokens | Output tokens | Cost, USD |
| --- | --- | ---: | ---: | ---: |
| Card generation | `openai/gpt-6.1-sol` | 216,072 | 13,117 | 0.671349 |
| Card verification | `anthropic/claude-sonnet-5.5` | 45,071 | 9,174 | 0.193760 |

Generation and verification cost **USD 0.865109** combined. This excludes the earlier extraction cost and does not include an asserted embedding-cost total. The measured generation input count also illustrates why the original conservative byte allowance should not be described as an actual native token count.

## 4. Separate collector backlog discovered; not fixed in this work

The investigation also found **87 waiting collection jobs**, with some reaching **91 attempts**, and repeated Fathom HTTP 404/429 responses involving recording `197260974`. That recording already had a stored revision. These counts describe collection requests and retry attempts, not 87 or 91 missing calls.

The collector had been active since 27 October, and the waiting requests predated the weekly folder failure. Pending-source rechecks could keep otherwise unrelated collection requests incomplete. The provider's reason for the 404 response, and whether retry amplification fully explained the rate limiting, were not established.

This backlog was deliberately left unchanged while the weekly cycle was recovered. It still requires separate investigation. The one-run input reduction also does not provide a permanent solution for future weeks that exceed the existing input safeguard.

## 5. Developer handoff: what remains

- **Folder validation:** fixed and deployed. Preserve the filesystem-root fallback and the checks that reject writes into application code.
- **Missed weekly run:** recovered. Its schedule claim is done, the original extraction result is restored, and the recovered cards are available for human review. Do not repeat the schedule reset or the generation retry for this incident.
- **Input-size handling:** the existing safeguard remains unchanged. Larger future weekly packets can still fail the same preflight. Investigate a permanent input-sizing or input-selection approach separately; do not assume the temporary 284-scene selection applies to future runs.
- **Collector backlog:** still unresolved. Investigate why a previously imported recording remains pending and why unrelated collection requests repeatedly revisit it. Preserve its stored revision, check per-source retry isolation and coordinated 429 backoff, and verify that the waiting requests can settle. No collector fix was implemented during this recovery.
