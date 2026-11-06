> The governing plan is `Content-Atelier-Implementation-Plan-Brief-Generation.md` (Phase 0, section 8). This note says what Phase 0 left and how to operate it.

# Phase 0: platform baseline, hand-over

Branch `item/0-platform-baseline`. Status of every item is in the plan (section 8 and "Implementation status"); the log row is in Appendix G.

## What exists now

| Part | Where | How to use it |
| --- | --- | --- |
| Migrations | `database.py`, `migrations/`, `schema_catalog.py` | `python -m backend_pipeline.storage_cli migrate` is the only way to change a schema. One catalogue per recorded version; CI runs `python -m backend_pipeline.schema_catalog --check`. After adding a migration: `--write`, review the diff, commit. |
| The `llm` module | `backend_pipeline/llm/` | Every model and embedding call goes through it: routing (`data_collection: deny`, ZDR), the run plan, an `llm_runs` row for each call (planned, replayed, refused), one repair for schema failures. New call sites use `llm.workflow.chat` or `StageCaller`. |
| One executor | `backend_pipeline/jobs/` | Every job is a row in `pipeline_jobs` first; `policy.py` names its queue and timeout; the dispatcher puts it on the RQ queue after the commit; `executor.run_job` is the only function a worker runs. |
| The scheduler | `python -m backend_pipeline.jobs scheduler` | Every 30 seconds: settle lost workers, release waiting intake jobs, re-queue committed rows with no live queue entry, run the intake cycle, the context jobs and the keyed periodic tasks. Add a scheduled task by appending a `periodic.Task` to `scheduler.periodic_tasks`; its period key makes it run once per period, including after downtime. |
| Job health | `python -m backend_pipeline.jobs health` | JSON from the job rows: per queue what is queued, running, lost or failed, the oldest wait, and whether the scheduler finished a pass in the last five minutes. |
| Settings | `settings_store.py`, `storage_cli settings ...`, `GET/PUT /storage/settings` | See `DEPLOYMENT.md`, "Settings". |
| Users and roles | `gates/roles.py`, `storage_cli users ...`, `GET /storage/me`, Node `GET /me` | See `DEPLOYMENT.md`, "Users and roles". |
| Artifact store | `artifacts.py`, `store.py` | `store_for(settings)` is the one way to open it. `ATELIER_ARTIFACT_STORE=s3` moves it to a bucket. `python -m backend_pipeline.artifacts copy --from <folder>` restores a folder. |
| Local stack | `backend/compose.yml` | `docker compose up -d --build` from `backend/`. |

## The rule for paid work after a lost worker

`jobs/recover.py` decides, from the rows alone. A job that sent no model call is queued again, up to three attempts. A job with a call that was sent and never settled (`llm_runs` still `sent`) is queued again only when the saved response can be replayed from the artifact store; otherwise it fails, the orphaned row is closed, and a person decides with `retry`. A chunk-embedding job always waits for review.

## Drills (all in `tests/test_jobs_db.py`, and run once against the real stack)

- Flush Redis in the middle of a cycle: after one scheduler pass the remaining stages are queued and complete, once each, with no new job rows and no repeated provider call.
- Kill a worker in the middle of a job: queued again once when nothing was sent; failed, not repeated, when a call was sent and its answer is not saved; replayed when it is.
- The same on `backend/compose.yml` (Postgres, Redis, API, scheduler, three worker kinds): jobs queued from a host process were dispatched by the scheduler and run by the editorial worker; with Redis flushed and the worker stopped, the next pass re-queued the job and the restarted worker ran it.

## What is not done, and why

- **0.B4 replay of the real Week 1 artifacts** needs S.B10 (the developer's machine).
- **0.B7 in production:** the services are specified in `DEPLOYMENT.md`, "Production services on Railway". Creating them needs the owner's approval of deployments in that Railway environment; restoring the backup needs S.B10; the card and brief tabs "done when" needs the sign-in (S.C1).
- **Settings with no code yet** (`scoring.criteria`, `memory.cooldowns`, `approvals`, `research`, `providers.routing`, `budgets`, `slack.*`) arrive with the items that read them.
- **Old local volumes:** the removed compose files used `intake_artifacts`, `intake_models` and `intake_redis`. Copy anything worth keeping out of them before deleting; the stack now keeps artifacts in `backend/.storage-artifacts`.
