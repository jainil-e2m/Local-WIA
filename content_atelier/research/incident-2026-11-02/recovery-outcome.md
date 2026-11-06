# November 1 weekly-cycle recovery outcome

Verified on November 2, 2026, through production database records, worker logs and the saved preflight artifact. The only production data mutation performed by the recovery helper was the authorized one-time retry-counter reset for `schedule.weekly_cycle.2026-11-01`.

## Successful recovery of the original failure

- Confirmed the scheduler runs commit `9b50c9d047a2d1005b19fbd80fea5f9e2476a32b`; the corrected folder check accepts its temporary directory and still rejects application-code paths.
- Confirmed no recovery cycle existed before the reset and the original claim was failed with three attempts and the exact original folder error.
- Under the scheduler's existing advisory lock, reset that claim's attempts to zero at **13:47:29 IST**. The before/after claim is saved in the timestamped `weekly-recovery-rearm-*.json` receipt.
- The existing scheduler collected the missed window and marked its orchestration claim done at **13:48:02 IST**. No task was invoked directly and no second scheduler was started.
- Fathom listed 18 recordings. Thirteen were already stored. All five missing transcripts were successfully fetched: four became new documents and one matched another recording of the same call and was not imported twice.
- The scheduler created exactly one recovery cycle, `run_113a8c5a0b384cfba61e6fc7b59367ee`, for `week_2026-10-25`, with the original October 25 10:00 UTC through November 1 10:00 UTC window and 16 included documents.
- The original missed-schedule alert cleared.

## Extraction completed

The extraction job completed at **13:58:03 IST**. It delivered **291 verified scenes from 16 documents**, reusing 12 documents already in the ledger. Six additional scenes were unverified and excluded from proof. Four new model extraction calls succeeded. Their recorded costs sum to **USD 0.043645**. Those completed results remain stored.

## New blocker: local card-generation size check

At **13:58:06 IST**, `angle_generation` failed with:

> Whole-week token budget exceeded; no request sent. No batching or truncation permitted.

This is a different failure from the corrected folder check. It is an application preflight refusal, before sending the card-generation request to the model; it is not a provider rejection or a spending-budget failure.

The saved report is `service_calls/b711709c8a5be0b742458b57ed5d535c00efc09db772d2b77c14e23328d8a941/attempts/artifact_9bec0c8147004f48/preflight.json` in the shared artifact store. Its relevant values are:

| Field | Value |
| --- | ---: |
| Model | openai/gpt-6.1-sol |
| Message text UTF-8 bytes | 853,145 |
| Response-format UTF-8 bytes | 6,418 |
| Conservative input allowance | 859,563 |
| Additional input margin | 85,957 |
| Allowance plus input margin | 945,520 |
| Cached prompt limit | 922,000 |
| Excess over cached prompt limit | 23,520 |
| Output reserve | 32,000 |
| Cached total context capacity | 1,050,000 |
| Total-context headroom after reserve | 72,480 |

The failed condition is the prompt-only comparison, `945520 > 922000`; the total-context comparison still has positive headroom. The code deliberately budgets UTF-8 bytes conservatively. These are not measured native tokens, and this result does not prove the actual model request would exceed provider capacity. The cached route snapshot is dated October 23, 2026; current provider capacity was not asserted or changed during this inspection.

The run is now failed at `angle_generation`, with zero new angle cards and no review document. Matching and angle embedding remain queued behind the failed stage. RQ worker log lines saying `Job OK` reflect the handler returning after recording the application failure; PostgreSQL's job/run status establishes the actual pipeline outcome.

## Scope and next step

- Do not reset the weekly schedule again: its collection/start orchestration is done and a recovery cycle exists.
- A separate investigation of the conservative input-sizing calculation and its saved route is needed before retrying the failed card-generation job in this same cycle.
- Do not repeat collection or successful scene extraction, disable input safeguards, truncate inputs or change models without an explicit decision.
- The older collector pending/429 backlog was not modified.
- The monitoring SSH connection was interrupted once; its remaining public-key registration was explicitly revoked. Subsequent diagnostic registrations were also revoked and their dedicated key files deleted. The original personal SSH key files were unchanged.

No application code, configuration, model settings, prompt-size limits or additional retry counters were changed after this new blocker was found.
