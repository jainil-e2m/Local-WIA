# Content Atelier: the operations runbook (plan 6.B9)

What the system does by itself every week, what the app shows when something goes wrong, and the few commands a person
runs when it does. Written for whoever looks after the system; the build and deployment detail is in `DEPLOYMENT.md`.
Since Phase N7 (25 October 2026) no weekly step needs a developer.

## The week, by itself

| When (America/Chicago) | What happens | Where it shows |
| --- | --- | --- |
| Every hour, from Sunday 1 November 2026 | The Fathom collector lists new recordings, imports each call, normalises it (speakers, call type, date, the account it belongs to), embeds its chunks and links a second recording of the same meeting to the first | Sources, Intake |
| Every hour | Every included call no extraction has read yet gets its scenes extracted (`upkeep.py`), so account memory and the founder-note picker see it the same day | Sources, Documents |
| A new client's first call | The account its title names is added, anonymised, with its outside speakers as people, marked "added by the system" for a person to check (`identities.provisional_account`) | Documents (the account) |
| Sunday 04:00 | The week's calls are brought in again (anything the collector missed), then the cycle starts over the seven days before, under the shared WIA account's standing approval (`cycle/schedule.py`) | Weekly Studio, Home |
| When the cycle finishes | The week's review document (Markdown and Word) is made and kept with the run | Weekly Studio (the cycle panel), Home |
| Monday 00:00 UTC | The weekly budgets renew; anything waiting for a budget starts by itself | Home (spend), the cycle panel |
| Every night 08:15 UTC | The database dump (`db-backup`); once a month it also restores the dump into a scratch database and compares every table's count | Sources (alerts) when it does not |
| Every night and every Monday | The knowledge base's staleness check, and the learning loop's candidates from the week's edits (they wait for an approver; nothing confirms itself) | Knowledge |

People do what is theirs: WIA's decisions at Gate 1 and Gate 2, marking packs ready, founder notes, tone requests, and
approving the knowledge-base changes those make (an approved change is in force at once: `context.release.benchmark_required`
is off in production).

## Alerts: what each means and what to do

The scheduler scans every 30 seconds. Each condition is one alert on the Sources screen and in the bell, until it clears
by itself or a person dismisses it. Nothing is emailed (the owner, 25 October 2026).

| Alert | What it means | What to do |
| --- | --- | --- |
| A job failed | One step failed after its retries; the alert names it and its reason | Read the reason on the job (Sources, Intake or the cycle panel) and press Retry. A failure that repeats is a defect: `python -m backend_pipeline.jobs health` from the `api` service shows every queue |
| A queue is stuck | Work has waited past its threshold and nothing on that queue moves, or a worker died mid-job | Check the worker service in Railway (it restarts by itself on failure); the reconcile pass re-queues a dead worker's job |
| The Fathom connection stopped | Its last collection failed, or no collection ran for three hours | Read the error on Sources, Intake. "Fathom HTTP 401" is a key problem: rotate the key (below). A transient error clears by itself |
| Jobs wait for a budget | A paid step would pass this week's cap; it starts by itself on Monday | Raise the cap if the week needs it: `storage_cli budgets set --purpose <purpose> --weekly-usd <n> --actor <approver>` |
| A scheduled run did not happen | The Sunday cycle, the hourly upkeep or the budget renewal failed three times | The alert names the reason. Start the week's cycle from the app (Weekly Studio, preview then start) |
| No database backup | No dump for a day and a half | Check the `db-backup` service's last run in Railway |
| The restore check failed | The monthly restore did not match the dump's counts | Run `python -m backend_pipeline.backup verify` from the image and read the differences |
| The scheduler is silent | No scheduler pass for ten minutes: nothing scheduled, no retry and no alert scan is running | Restart the `scheduler` service in Railway |
| Fewer than half the cards developed two weeks running | Editorial monitoring (6.B13) | Read the skip reasons at Gate 1; a pattern is a tone request or a knowledge-base change |

## Re-running something

Commands run in the `api` service (`railway ssh`) or from a checkout through a temporary TCP proxy with production's
variables (`DEPLOYMENT.md`, "Documents and evidence"). Each one says what it would do with `--dry-run` or `--estimate`.

| To | Run |
| --- | --- |
| Normalise a document again (after correcting an account or a person) | `python -m backend_pipeline.storage_cli documents normalise --ids <transcript_id>` |
| Extract a document's scenes again | `python -m backend_pipeline.storage_cli moments extract --ids <transcript_id> --mode live --retry-failed` |
| Bring in a week's calls by hand (if the collector is off) | `python -m backend_pipeline.storage_cli documents fathom-backfill --from <YYYY-MM-DD> --to <YYYY-MM-DD> --timezone America/Chicago --out <folder outside the repository> --embed live` |
| Run a cycle over a window | The app: Weekly Studio, the cycle panel, preview then start |
| Develop a card again, or retry a brief | The app: the card's brief panel (Retry), or a Gate 2 refresh with feedback |
| Finish a pack again | The app: the pack's "Finish again" |
| The week's review document | The app (cycle panel), or `storage_cli review-document --week-id <week> [--format docx --out <file>]` |
| Remove one client's material on request | `python -m backend_pipeline.storage_cli clients remove --client-id <id> --actor <approver> --dry-run`, then with `--confirm <id>` |

## Keys and accounts

| Key | Where it lives | To rotate |
| --- | --- | --- |
| OpenRouter (the Client key since 25 October) | `OPENROUTER_API_KEY` and `EMBEDDING_API_KEY` on `api`, `scheduler` and every worker | Set the new key on those services (a variable change redeploys them without approval), then revoke the old key. The standing caps must fit the key: they total USD 4.20 a week since 26 October, enough for the Sunday cycle and the hourly upkeep; when the team starts developing briefs and packs on a funded key, raise briefs, refreshes and packs with `storage_cli budgets set` (for example 4, 1.5 and 4) |
| Fathom | `ATELIER_FATHOM_API_KEY` on `api`, `scheduler` and every worker | Generate a new key in Fathom, set it, redeploy; the collector's checkpoint is kept, so nothing is fetched twice |
| The backend secret | `ATELIER_API_SECRET`, equal on `api` and the Frontend | Set the same new value on both and redeploy both |
| Command Center's session secret and password | `SESSION_SECRET`, `AUTH_PASSWORD_HASH` on Command Center | The owner's (the agent never sets or enters passwords) |
| The artifact bucket | `ATELIER_S3_*` on every backend service and `db-backup` | Rotate in the bucket's credentials, set on every service |

Who may do what is the role lists on every backend service: `ATELIER_BRIEF_APPROVERS` (Gate 1 and Gate 2 decisions, the
schedule's standing approval), `ATELIER_BRIEF_EDITORS`, `ATELIER_INTAKE_ADMINS` (the collector), `ATELIER_IDENTITY_APPROVERS`.
The scheduled cycle starts under `cycle.schedule.actor`, which must be on the approver and intake-administrator lists.

## Restoring

The nightly dumps are in the `artifacts` bucket under `backups/db/` (the newest 14, one a week for 8 weeks, one a month for a
year). To restore: rehearse first (`python -m backend_pipeline.backup verify --key <dump>`), then `pg_restore --no-owner
--no-acl -d <database>` with the image's PostgreSQL 17 client, through a temporary TCP proxy, and delete the proxy straight
after (`DEPLOYMENT.md`, "Production services on Railway", steps 1 and 2).

## Switching something off

| To stop | Set |
| --- | --- |
| The Sunday cycle | `cycle.schedule.enabled` false (`storage_cli settings set`); the cycle is then started from the app |
| Paid work entirely | `budgets.standing` false (every paid call then needs a named run plan), or the `ATELIER_ALLOW_*` switches false |
| A new prompt, model or knowledge base | Its settings key back to the previous value (each release names its switch-back in `deploy/production-settings.json`) |
