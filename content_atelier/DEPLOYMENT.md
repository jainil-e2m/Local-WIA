# Deploying Content Atelier

This describes what exists and how to run it. The production target (all services on WIA's Railway project, the real data transferred, live verification) is Phase 7 of the plan: `backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md`, section 14A.

## What is deployed today

**6 November 2026: hardened for the unattended run of Sunday 8 November (PR #65, `a54c620`).** Every backend service runs
`a54c620`. What changed and why is in `research/incident-2026-11/PERMANENT_FIXES.md`, "6 November". On Railway:
- **`editorial-worker` runs 2 replicas** (it was 1): a brief no longer waits behind another brief or the weekly cycle (on
  2 and 3 November brief steps waited 10 to 24 minutes in the queue). Jobs are claimed under a lease, so two replicas never
  run one job twice.
- **The OpenRouter key is production's own again** on `api`, `scheduler` and the three workers (checked by hash). A test
  key was on them from 07:09 to 08:13 UTC for the production test below.
- **The scheduler** re-executes itself in place past 1 GB (`ATELIER_SCHEDULER_MEMORY_LIMIT_MB`); it held about 115 MB
  after the deploy, against 2.7 GB before it.
- **A full production test was run and then removed.** The week's scheduled run was started by hand through
  `cycle.schedule.run` (not through its claim, so Sunday's claim stays unset), two cards were taken through refresh, edit,
  Gate 1, brief, brief edit and revision, Gate 2, pack, pack edit, kept line, refinish, ready to publish, calendar schedule,
  reschedule and cancel, and a skip, a hold and a revive were recorded. Everything it wrote was then deleted in one
  transaction (diffed row by row against the backup `backups/db/atelier-20261106T070158Z.dump` taken before it), with its
  objects in the `artifacts` bucket, its cost records, and this week's standing plan counters put back. Kept, as repairs to
  data that was already there: the Fathom backlog settling (237 requests completed) and the scenes of
  `transcript_9a425517e60eea247c0dea4e`, whose extraction failed on 4 November, now re-pointed to that call's own
  extraction run `docext_ffbdd7fdd49f28e345d30f01`.
- **CI does not run**: GitHub refuses every job ("recent account payments have failed or your spending limit needs to be
  increased"), on `main` since 3 November. PR #65 was checked locally instead (2,112 passed; the 11 failures also fail on
  `main`).

**27 October 2026, evening: no spend caps, and production has its own OpenRouter key.** This supersedes the Client-key and
standing-caps statements further down.
- **Caps (PR #42, `ff49862`):** `budgets.uncapped` is `true` on production (`deploy/production-settings.json`, applied
  through a temporary TCP proxy, deleted after). `budgets renew` lifted every weekly plan to the uncapped ceiling and reopened
  the spent packs and refreshes plans. No job waits for budget, and spend is still recorded.
- **Screens (PRs #43, `ef6187e`, and #44, `6f2f2f4`):** with no weekly limits, Settings shows only the schedule and the
  Weekly cycle page shows no spending list. The cycle preview no longer warns that an estimate passes a budget (it summed only
  capped purposes, so it always warned). Finish again and the costs view no longer mention budgets. Costs stay under Alerts
  and costs. Checked on production in the browser pane.
- **Key:** the owner created a dedicated production OpenRouter key and set it in Railway as `OPENROUTER_API_KEY` and
  `EMBEDDING_API_KEY` on `api`, `scheduler`, `editorial-worker`, `bulk-worker` and `intake-worker`. It is the same on all
  five, compared by hash, and never printed. It is kept in Railway only, never in a local environment file. The five services
  were redeployed. A production search was billed to the new key (usage 0 to USD 0.00000008), while the Client key stayed at
  USD 22.94. The key has no credit limit; the only ceiling is the OpenRouter account's credit (USD 50, USD 38.96 used, on
  27 October), which the owner tops up. Never set the Client or internal key on these services again.
- **Costs page (PRs #46, `c1ecad3`, and #47, `b6e829f`):** asked for in the 27 October sync. It opens with three totals: spent
  since `costs.count_from` (set to 2026-10-27 on production), this week, and the last 8 weeks. Below them is the cost of each
  content pack run, from the run's own call records: the cost OpenRouter reported for every call, with its generation id. The
  breakdown by week, purpose, stage and model is folded. Checked against the database on production: USD 5.64 over 32 calls
  since 27 October, and USD 7.13 over 32 pack calls in all, every one with a reported cost. The three earliest packs show
  "no new charge" because their answers were first written in an earlier test run. A repair attempt refused by the old
  weekly cap before sending is not counted as a call.
- **Costs count from the hand-over (PR #49):** at the owner's request the costs page leaves out the team's own tests and
  remakes. `costs.count_from` is the moment production was handed over (`2026-10-27T18:01:00Z`), and the totals, the weeks and the content
  pack table all start there. The page shows two totals, spent since the hand-over and this week, and says "No content pack
  has been made yet" until the first one.

**27 October 2026, afternoon: Round 2's second pass is on production, and the week of 18 October was remade for the demo.**
PR #40 (`515e364`) deployed; `settings apply` switched `prompts.profile.pack_finish` to `2026-10-27.pack-finish.v4` and
`pack_refinish` to `2026-10-27.pack-refinish.v3` (the plan reads the card's whole call). For the demo, the internal key was
put on the five model-calling services, the week's two briefs were refreshed with writer v5.3, taken through Gate 2 by the
team under delegation, packed by finisher v4, their remaining blocking lines edited with reasons, and both marked Ready to
publish (USD 3.49 on the internal key: refreshes 1.16, packs 2.33). The Client key was then set back on all five (checked
by hash) and the five redeployed; the caps are back at briefs 1.00, refreshes 0.40, packs 0.70; the TCP proxy is deleted.
Record: `research/round2-2026-10/VERIFICATION.md`.

**27 October 2026: Round 2 (WIA's feedback of 26 October) is on production.** PR #38 (`7623814`) deployed to every
service; `settings apply --file deploy/production-settings.json` (through a temporary TCP proxy, deleted after) switched
`prompts.profile.brief_writer` to v5.3 and the pack profiles to finish v3, check v4, repair v2 and refinish v2. The two packs
marked Ready to publish (week of 18 October) were finished again under finisher v3 (USD 2.14 on the Client key, the packs
cap raised to USD 3.30 for it and set back to USD 0.70), their remaining blocking lines edited by the team with reasons, and
both left in review for WIA. The Client key has about USD 2.06 left for Sunday's cycle. Record and verification:
`research/round2-2026-10/` (`VERIFICATION.md`). Switch-backs: v5.2, pack-finish.v2, pack-check.v3, pack-repair.v1,
pack-refinish.v1.

**26 October 2026: the OpenRouter key was off production for part of the day and is back.** At the owner's request the
`OPENROUTER_API_KEY` and `EMBEDDING_API_KEY` variables were deleted from `api`, `scheduler`, `editorial-worker`, `bulk-worker`
and `intake-worker` (so nothing could spend while the screens were reworked), then, at the owner's request the same day, set
again to **the Client key** on all five (checked by hash against the Client key in the local backend environment file, never printed) and the
five services redeployed on `b88f500`. The Client key had USD 4.20 left of its USD 25 limit (no reset), which the standing
caps below are sized to. The screens were decluttered on the same day (`research/n6-n11-2026-10/ui-declutter.md`).

Verified on 25 October 2026 (Phases N6, N10, N7 and N11, `research/n6-n11-2026-10/README.md`, "Production"): every
backend service on `bc38a32` (PRs #28 to #31: migration 011, failure alerts, the hourly upkeep, the Sunday schedule, Home's
summary, strategist v9), the Frontend on `fafec9e` (the screens' realignment with the mockup follows in its own PR);
`deploy/production-settings.json` applied (strategist v9, `cycle.schedule.*`, `context.release.benchmark_required` false).
**The OpenRouter key is the Client key** on `api`, `scheduler` and the three workers (`OPENROUTER_API_KEY` and
`EMBEDDING_API_KEY`, 25 October; the internal key is no longer used), and `ATELIER_ALLOW_INTAKE_ENCODING=true` is set on
`scheduler` and `intake-worker`. **The first scheduled run is Sunday 1 November 2026, 04:00 America/Chicago**: it collects
the calls of 25 to 31 October, activates the Fathom collector once, starts the cycle under `ai@weddingindustryads.com` and
writes the week's review document (Markdown and Word) to the run; hourly collection and the Sunday cycle follow by
themselves. Content: last week (`week_2026-10-18`, the calls of 18 to 24 October) regenerated and taken through both gates
under delegation, two packs ready to publish; `week_2026-10-12` kept; `week_2026-06-01`, `week_2026-06-08` and
`week_2026-10-20` archived. **Standing caps** (from 26 October, sized to the Client key's remaining credit so the Sunday run
and the hourly upkeep always fit): cycle 1.5, scene extraction 0.4, embedding 0.1, context mining 0.1, briefs 1.0,
refreshes 0.4, packs 0.7 (USD 4.20 a week). When the WIA team starts developing briefs and packs on a funded key, raise them
with `python -m backend_pipeline.storage_cli budgets set --purpose <purpose> --weekly-usd <amount> --actor <approver>` (for
example briefs 4, refreshes 1.5, packs 4).

| Railway project | Service | Source | State |
| --- | --- | --- | --- |
| Content Atelier (production) | `api`, `scheduler`, `editorial-worker`, `bulk-worker`, `intake-worker` | `kenil-e2m/WIA-Content-Atelier` `main`, root `/backend`, `backend/Dockerfile`, watch path `/backend/**` | Running since 24 October on the database restored from N2; on `bc38a32` since 25 October (migration 011) |
| Content Atelier (production) | `db-backup` (cron, 08:15 UTC) | the same image, `python -m backend_pipeline.backup dump` | The nightly dump to the `artifacts` bucket (6.B6), in place of Railway volume backups, which need a Pro workspace |
| Content Atelier (production) | `Frontend` | the same repository, root `/frontend`, Dockerfile, watch path `/frontend/**` | The real app (backend mode) at `https://content-atelier.up.railway.app`, pointed at `api` over private networking; sign-in through Command Center |
| Content Atelier (production) | `postgres`, `Redis`, buckets `artifacts` and `transfer-inbox` | images and Railway buckets | `postgres` holds the restored database; `artifacts` holds the 8,224 artifact files (574 MB) and the dumps under `backups/db/` |
| Command-Center (production) | `WIA-Command-Center` | `kenil-e2m/WIA-Command-Center` `main` | Real accounts since 24 October (S.C1): `AUTH_DISABLED` removed, `SESSION_SECRET` and `AUTH_PASSWORD_HASH` set, one standard account `ai@weddingindustryads.com` |

**Deployments from `main` wait for approval** in Railway for every service (the commits' author is not a member of the
Railway workspace). Approve only the newest deployment of each service, and only when it builds the commit you merged:
in the dashboard, or with the API (`railway api 'mutation { deploymentApprove(id: "<deployment id>") }'`). An older
deployment left waiting is never approved.

## Production services on Railway (plan 0.B7, 7.B1, D13)

One environment: the existing `Content Atelier` project's `production`. Everything below exists since 24 October 2026 (Phase N3); the steps stay here as the runbook for a rebuild. All application services use the repository `jainil-e2m/WIA-Content-Atelier`, root directory `/backend`, builder Dockerfile, one image. The API and the databases have **no public domain**: the Frontend reaches the API over private networking, which on Railway is IPv6 (the API binds `::`).

| Service | Start command | Notes |
| --- | --- | --- |
| `postgres` | image `pgvector/pgvector:0.8.2-pg17` (the CI digest), a volume at `/var/lib/postgresql/data` | **Exists** (19 October 2026, empty database `atelier`). Railway's stock template has no pgvector, so it is a custom image: it publishes `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` and `RAILWAY_PRIVATE_DOMAIN`, but **no `DATABASE_URL`**. Turn on volume backups before any data arrives. |
| `redis` | Railway Redis | **Exists.** The queue transport only (a flush loses nothing). |
| bucket `artifacts` | Railway bucket (S3-compatible) | **Exists, empty.** The artifact store. Read its real name, endpoint, region and URL style from the bucket's own variables; its display name is not its name. |
| `api` | the image default (`python -m backend_pipeline.serve`: uvicorn on `${PORT:-8000}`, one socket for IPv6 and IPv4, `${WEB_CONCURRENCY:-3}` processes) | Set `PORT=8000`. Health check path `/health`; pre-deploy command `python -m backend_pipeline.storage_cli migrate`. |
| `scheduler` | `python -m backend_pipeline.jobs scheduler` | Exactly one replica. |
| `editorial-worker` | `python -m backend_pipeline.jobs worker --queues interactive,default` | At least one replica. Give it the same pre-deploy migrate (lock-guarded), or it may refuse to start while `api`'s migration of a new release runs. |
| `bulk-worker` | `python -m backend_pipeline.jobs worker --queues bulk` | The `bulk` queue (`backend/backend_pipeline/jobs/policy.py`): document normalisation, moment and chunk embeddings, topic assignment and the scheduled knowledge-base benchmark. Without it those jobs wait on the queue and imports never finish normalising or embedding; with it an hour-long backfill or re-embedding cannot block briefs. Deploy it with the other workers (step 4). |
| `intake-worker` | `python -m backend_pipeline.jobs worker --queues intake` | Connectors stay off until WIA supplies the keys. |
| `db-backup` | `python -m backend_pipeline.backup dump`, cron `15 8 * * *` (UTC), restart policy Never | The nightly dump (6.B6): a custom-format `pg_dump` and a manifest (exact row counts per table taken in the dump's own snapshot, the newest migration, size, SHA-256) written to the artifact store under `backups/db/`, read back, then pruned to the newest 14, one a week for 8 weeks and one a month for 12 months. Variables: `ATELIER_DATABASE_URL`, `ATELIER_ARTIFACT_STORE` and the `ATELIER_S3_*` set only. The monthly restore check runs by itself (Phase N6): when the last check is older than 28 days or failed, `dump` restores the dump it has just written into a scratch database, compares every table's count with its manifest and drops the scratch database; both results are recorded in `settings` (`backup.last_dump`, `backup.last_restore_check`) and a missed night or a failed check is an alert in the app. `python -m backend_pipeline.backup verify` still runs the check by hand, from any machine with the image and the two variable sets. To restore: download the dump from the bucket and `pg_restore --no-owner --no-acl -d <database>` with the image's PostgreSQL 17 client. |
| `media-worker` | `python -m backend_pipeline.jobs worker --queues media` | About 2 vCPU and 4 GB; the speech and OCR models. Create it only once live intake carries attachments; until then it is not part of the order. |

**The scheduled knowledge-base benchmark runs from a checkout, not here (L.B11).** Its job is on the `bulk` queue, but its inputs (the development weeks' call excerpts and Whitney's alternatives) live under `research/` and the `evaluation` package, which the image does not carry (R48). On `bulk-worker` it therefore records a `skipped` result with the reason on the waiting version (the Versions screen and the cycle's notice show it) and finishes; it does not fail. It also follows the configuration of record: the strategist profile and model come from the settings (`prompts.profile.strategist`, `models.angle_generation`), and a profile the harness has no configuration for is skipped the same way. A tone change or any identity change is benchmarked from a checkout with the inputs and a key, under a run plan (`storage_cli plan create --standing kb_benchmark ...`), by a developer or the weekly tone loop (plan X.2).

**Variables on `api`, `scheduler` and every worker** (references to the services above, never copied values):

- `ATELIER_DATABASE_URL=postgresql://${{postgres.POSTGRES_USER}}:${{postgres.POSTGRES_PASSWORD}}@${{postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{postgres.POSTGRES_DB}}`;
- `ATELIER_REDIS_URL` (the Redis service's private URL);
- `ATELIER_ARTIFACT_STORE=s3`, and `ATELIER_S3_BUCKET`, `ATELIER_S3_ENDPOINT`, `ATELIER_S3_REGION`, `ATELIER_S3_ACCESS_KEY_ID`, `ATELIER_S3_SECRET_ACCESS_KEY` from the `artifacts` bucket's variables; `ATELIER_S3_PATH_STYLE=false` when the bucket reports virtual-host addressing;
- `ATELIER_API_SECRET` (a generated secret, equal on the API and the Frontend);
- the allow-lists and the settings from "Variables by container"; every `ATELIER_ALLOW_*` catch `false` until a run plan is approved; no `OPENROUTER_API_KEY` until the first planned paid run;
- after the first migration, the candidate editorial configuration (it includes `context.schedule.mining_live: true`: the weekly learning loop's paid categorisation, which needs a run plan covering stage `context_mining`; without one the loop categorises by rules and says why): `python -m backend_pipeline.storage_cli settings apply --file deploy/production-settings.json --actor <approver> --dry-run`, then without `--dry-run` (plan E.X4, provisional: the code defaults are the configuration WIA rated 1 of 5).

**Order, each step checked before the next** (restore before the first migration; a full `pg_restore` cannot land on a schema the API has already created):

1. **Backups.** Railway's volume backups and backup schedules need a Pro workspace (the API refuses them otherwise), and the plan is the owner's to change, so production keeps its own: the `db-backup` cron service (below). Rehearse the restore on a scratch database first (D13): `python -m backend_pipeline.backup verify --file <dump> --expect <counts.json> --scratch atelier_rehearsal_<x>`, with the counts from `backup counts` on the source database; it restores, compares every table's count and drops the scratch database. Then restore for real.
2. **Restore the developer's data** (S.B10) into the empty `atelier` database: open a temporary TCP proxy on `postgres` (`railway tcp-proxy create --port 5432 --service postgres`), run `docker run --rm -v <dump folder>:/d pgvector/pgvector:0.8.2-pg17 pg_restore --no-owner --no-acl --exit-on-error -h <proxy host> -p <proxy port> -U atelier -d atelier /d/<name>.dump` (the backend image also carries the PostgreSQL 17 client since 24 October; Debian's own is too old for a PG 17 dump), compare `backup counts` on both sides, and remove the proxy straight after (`railway tcp-proxy delete <id>`). Then copy the artifacts from the owner's machine with the `artifacts` bucket's credentials: `python -m backend_pipeline.artifacts copy --from <folder> --dry-run`, then without `--dry-run` (it never replaces or deletes). With no handover yet, skip this step: the API's migration creates the schema on the empty database, and S.B14's import fills it.
3. Deploy `api`. Its pre-deploy migration brings the restored (or empty) database to the latest version; the embedding-contract check must pass with no re-embedding; `GET /health` answers.
4. Deploy `scheduler`, `editorial-worker` and `bulk-worker` (and `intake-worker` once connectors are on; `media-worker` only once intake carries attachments). `python -m backend_pipeline.jobs health`, run in the `api` service (`railway ssh`), shows the scheduler alive and no job lost.
   Then cache each live model's public route in the bucket (`python -m backend_pipeline.token_budget --model <model> --store`, once per extraction, strategist and card-verification model: `openai/gpt-6-luna`, `openai/gpt-6.1-sol` and `anthropic/claude-sonnet-5.5` in the production configuration): a live weekly call is sized against it before it is sent, and refused without it, with the command to run.
5. **Bootstrap the context store** (L.B1, L.B2) from a checkout of the same commit, through the proxy, because `research/` is not in the image: `storage_cli context-seed --approver <owner email>`, then `storage_cli context-review-apply --actor <owner email>` (the reviewed decisions of `research/chatgpt-export-2026-10-18/seed-review-2026-10-18.json`), then `storage_cli context-published-points --actor <owner email>` (the central point and date of each piece in WIA's published log, `backend/knowledge_base/published-central-points.json`, E.B25 (f): the strategist and the verifier's same-point check read the last twelve months), then `storage_cli context-entries-apply --actor <owner email>` (the reviewed entries of `backend/knowledge_base/reviewed-entries.json`, with document 05's entries derived from `offer-descriptors.json` and `insider-terms.json`, E.B25 (i), (j)), then check the store against the committed knowledge base: `storage_cli kb-compile --on 2026-10-22 --actor <owner email>` must report `unchanged` and name the committed version (`backend/knowledge_base/manifest.json`, version 9, `wia-kb-2026-10-22.c-a1a75795`: version 8 (version 6's rules, the superseded lines of the supplied documents 01 to 03 from `backend/knowledge_base/supersessions.json` and the editing guide, `17-editing-guide.md`) with the documents the committed additions list adds from 22 October (`backend/knowledge_base/additions.json`: Whitney's spoken voice, `18-spoken-voice.md`, and her raw-to-final chains, `19-transformations.md`, E.B25 (j), L.B12), document 05's approved descriptors and insider-term glossary, document 09's first-touch rules and the published register at piece level, the default since its reading in phase N2 on 23 October (D40, `research/n2-delivery-2026-10/kb9-reading.wia-kb-2026-10-22.c-a1a75795.json`); versions 5 to 8 are archived). A line the supersessions list names that is no longer in its document, or an added document whose text is not the reviewed one, stops the compile, naming it. Every stage's prefix is kept within `context.budget.prefix_tokens` (30,000 by default; E.B25 (d)) by dropping whole documents from the bottom of the recorded priority list (`prefix-priority.v3` for a version holding document 18 or 19, as version 9 does; `prefix-priority.v2` before), and each run records what was dropped; the setting is the only knob. Then `storage_cli kb-compile --actor <owner email>` on the day compiles the operating update (recent published pieces and the content plan's dates): it shows no identity change, and `storage_cli kb-approve --version <it> --actor <owner email> --note "go-live"` activates it with no benchmark (R44). If a compile shows any other identity change, stop: the store does not match the committed inputs.
6. Only after S.C1 (Command Center refuses `AUTH_DISABLED` and has real accounts) set on the Frontend `ATELIER_BACKEND_ORIGIN=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:8000` and `ATELIER_API_SECRET`, and approve its deployment. `COMMAND_CENTER_AUTH_ORIGIN` stays public: private networking does not cross projects.

The Frontend's deployments wait for approval in Railway; the new services may do the same, so the owner approves them in the dashboard.

## The pieces

| Piece | Code | Process |
| --- | --- | --- |
| Atelier app and Node server | `frontend/` | `node server/index.mjs` (the Dockerfile builds the SPA, then runs this). The Dockerfile's `ARG VITE_ATELIER_MODE` defaults to `backend`: an image built with no arguments is the real, API-backed app. The saved mock flow (the Looms demo) is built only with `--build-arg VITE_ATELIER_MODE=mock`; any other value fails the build. Checks the Command Center session, serves the SPA to `team` sessions only, and proxies an allowlist of routes to the editorial API. |
| Editorial API | `backend/` | `python -m backend_pipeline.serve` (the image default: uvicorn on one socket bound to `::` with IPv6-only off, so it answers IPv6, as Railway's IPv6-only private network needs, and IPv4, as health checks and the local stack need; `uvicorn --host ::` alone answers IPv6 only; the platform's `$PORT` is honoured, health check path `/health`). Weekly storage, Gate 1, briefs, flags. Refuses to start on an embedding-contract mismatch, on a database not at the code's migration (run `storage_cli migrate` first), when the database stays unreachable past `ATELIER_STARTUP_DATABASE_WAIT_SECONDS`, or when briefs are on without a reviewed brand bundle. |
| Editorial worker | `backend/` | `python -m backend_pipeline.jobs worker --queues interactive,default,bulk`. An RQ worker for every editorial stage: extraction, angles, matching, brief and pack stages, chunk encoding. The local stack (`backend/compose.yml`) runs one such worker on all three queues; Railway splits it into `editorial-worker` (`interactive,default`) and `bulk-worker` (`bulk`). |
| Intake worker, media worker | `backend/` | `python -m backend_pipeline.jobs worker --queues intake` and `--queues media` (the media worker carries the speech and OCR models). Fathom and Slack intake, off until WIA supplies the keys and the bot. |
| Scheduler | `backend/` | `python -m backend_pipeline.jobs scheduler`. One process: every 30 seconds it settles jobs whose worker is gone, puts any committed job that is not on a queue back on it, and runs the scheduled work (intake cycle, context jobs, keyed periodic tasks). Exactly one is needed; a second is harmless. |
| Redis | — | `redis:7.4`, the queue transport only: Postgres holds every job row and decides every outcome, so flushing Redis loses nothing (the next scheduler pass re-queues). `ATELIER_REDIS_URL` on the API, the scheduler and every worker. |
| Postgres with pgvector | — | `pgvector/pgvector:0.8.2-pg17`, the CI image. |

## Variables by container

Secrets are set in the platform, never in git or in any `VITE_*` variable. Every variable below is read by the code; `backend_pipeline/tests/test_documented_variables.py` checks that. In the backend tables, the models, profiles, thresholds, budgets, schedules and feature flags are **settings** whose legacy variable still works as described under "Settings" above (a database row wins over the variable); the secrets, endpoints, paths, allow-lists and `ATELIER_ALLOW_*` safety catches are environment-only, and a test fails when an example file names a behavioural variable that is neither.

### Atelier Node server (`frontend/`)

| Variable | Required | Meaning |
| --- | --- | --- |
| `COMMAND_CENTER_AUTH_ORIGIN` | Yes | Command Center's server origin, used for session checks. Scheme, host and port only; no path. |
| `COMMAND_CENTER_PUBLIC_ORIGIN` | Yes, always | The public HTTPS Command Center origin for browser redirects in the sign-in hand-off. Set it in every deployment: `/api/auth/sso/start` answers 503 ("Set COMMAND_CENTER_PUBLIC_ORIGIN ...", `frontend/server/sso.mjs`) when no valid public origin is available, which is the case whenever it is unset and the auth origin is private (Railway's `*.railway.internal` is HTTP). Leaving it unset works only by falling back to a public HTTPS `COMMAND_CENTER_AUTH_ORIGIN`; do not rely on that. |
| `ATELIER_BACKEND_ORIGIN` | For real data | The editorial API's origin (private networking on Railway). Unset: weekly routes return 503. |
| `ATELIER_API_SECRET` | For real data | Shared secret; must equal the API's |
| `PORT` | Set by Railway | Listening port (8080 locally) |
| `NODE_ENV` | Set by the Dockerfile | `production` issues Secure cookies |
| `VITE_ATELIER_MODE` | Build argument, default `backend` | Which app the image contains (`frontend/Dockerfile`, `frontend/src/App.tsx`): `backend` is the real app, `mock` the saved demo flow. It is fixed at build time, not read at run time, and no secret goes in it. |

### Editorial API and worker (`backend/`)

**Storage, gates and switches** (`backend/storage.env.example`; locally in `backend/.env.storage.local`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `ATELIER_DATABASE_URL` | local compose database | Postgres connection string |
| `ATELIER_ARTIFACT_ROOT` | `backend/.storage-artifacts` (`/artifacts` in the image) | The folder of the local artifact store: saved requests and responses, dossiers, cost files, brief runs and intake originals |
| `ATELIER_ARTIFACT_STORE` | `local` | `local` (the folder above) or `s3` (an S3-compatible bucket, for a platform where the API and every worker are separate containers with no shared disk). Every caller opens the store through one interface (plan 0.B7). |
| `ATELIER_S3_BUCKET`, `ATELIER_S3_PREFIX` | blank | With `ATELIER_ARTIFACT_STORE=s3`: the bucket (required) and an optional key prefix, e.g. `production` |
| `ATELIER_S3_ENDPOINT`, `ATELIER_S3_REGION`, `ATELIER_S3_PATH_STYLE` | blank, `auto`, `true` | The S3-compatible service's endpoint (leave blank for AWS), region and addressing style |
| `ATELIER_S3_ACCESS_KEY_ID`, `ATELIER_S3_SECRET_ACCESS_KEY` | blank | The bucket credentials (secrets: set in the platform, never in git) |
| `ATELIER_API_SECRET` | blank | Must equal the Node server's |
| `ATELIER_BRIEF_APPROVERS` / `ATELIER_BRIEF_EDITORS` | blank | Command Center emails. Approvers decide Gate 1 and Gate 2; editors edit (S.B3, R37, R50). These are the legacy lists: the `users` table takes precedence for anyone with a row (see Users and roles). |
| `ATELIER_ALLOW_GENERATION`, `ATELIER_ALLOW_ENCODING`, `ATELIER_ALLOW_REFINEMENT` | `false` | Safety switches for paid extraction and angles, embeddings and refinement |
| `ATELIER_BRIEFS_ENABLED`, `ATELIER_ALLOW_BRIEF_GENERATION`, `ATELIER_ALLOW_BRIEF_WEB` | `false` | Briefs, live brief generation, web research at brief depth |
| `ATELIER_BRAND_BUNDLE_PATH` | blank | Reviewed brand bundle: a file path, or `artifact:<key>` for a file in the artifact store (so a platform with no shared disk keeps it in the bucket). Required when briefs are on with the v1 contract; the processes refuse to start without it. v2 briefs read the knowledge base and need no bundle (E.B11 f). |
| `ATELIER_BRIEF_MODEL`, `ATELIER_BRIEF_REVIEW_MODEL` | `openai/gpt-6.1-sol`, `anthropic/claude-sonnet-5.5` | Brief writer, and plan, grade and review models (settings `models.brief`, `models.brief_review`). A live brief refuses to run unless both are set explicitly, by row or variable, not left at the default (S.B8, section 4.10). |
| `ATELIER_BRIEF_MAX_CHARACTERS` | `120000` | Request preflight; the system prefix (prompt and knowledge base) does not count (E.B15 e) |
| `ATELIER_BRIEF_SCHEMA` | `v1` | Brief contract for new runs: `v1`, or `v2` (WIA perspective first, format plan per channel, CTA confirmed at Gate 2; E.B15). Revisions keep their brief's version. |
| `ATELIER_BRIEF_WRITER` | `v2` | The brief writer's prompt, which must suit the contract: `v2` (released 18 October) or `v3` (E.B22, plan section 1.9.8: copy kept apart from direction, every caveat in Before publishing and Claims) for contract v2; `v4` or `v4.1` (E.B23, 5.B6) for contract v3; `v5` (E.B33) or `v5.1` (NP.B10: v5 writing exactly three Reels, story, stance and b-roll text, with its own answer schema) for contract v4. Frozen with each run; the production configuration sets `v5` (`backend/deploy/production-settings.json`). |
| `ATELIER_BRIEF_CHANNELS` | `reel,carousel,email,caption` | The confirmed channel set a v2 format plan may use (`stories` and `threads` are optional additions) |
| `ATELIER_DUPLICATE_COSINE` | `0.90` | Cards closer than this to a better-ranked card collapse into it (0.5 to 1.0; E.B16 l, E.B6) |
| `ATELIER_ANGLE_APPROVAL_CUTOFF` | blank | Legacy comparison approval cutoff (0.78, 0.85 or 0.90) |
| `ATELIER_SYNTHETIC_DATABASE` | `false` | Test databases only |
| `ATELIER_RUN_PLAN_ID` | blank | The active run plan this process may spend under (E.B1). Without it, every live model or embedding call is refused. Create one with `storage_cli plan create`. Every call, a refused one and a repair included, is a row in `llm_runs` (model, prompt version, knowledge-base version, tokens, cost); a response that breaks its schema gets exactly one repair call, which counts against the plan (0.B4). |
| `ATELIER_RUN_PLAN_FILE` | blank | A file plan instead, for a harness or one-off script run; its call ledger is written beside it |
| `ATELIER_REDIS_URL` | blank | The queue transport (`redis://host:port/db`) for the API, the scheduler and every worker. Blank: the API queues nothing itself and workers refuse to start; the older `ATELIER_INTAKE_REDIS_URL` is still read. Postgres is the source of truth, so Redis may be flushed or replaced at any time (plan 0.B5). |
| `PORT` | `8000` | The API's listening port; Railway sets it. |
| `ATELIER_ALLOW_PACK_GENERATION` | `false` | The live switch for content packs (Phase NP): set it to exactly `true` on `api` and `editorial-worker` (any other value is off). With it and `ATELIER_ALLOW_GENERATION=true`, approving a v4 brief at Gate 2 starts its pack live under the `packs` standing budget; otherwise a pack runs in replay (saved responses only). |
| `ATELIER_PACKS_ENABLED` | `false` | The `features.packs` setting's variable; production sets the setting from `production-settings.json` instead |
| `ATELIER_CALENDAR_ENABLED` and the other calendar variables, `ATELIER_PACK_EDITORS`, `ATELIER_PACK_APPROVERS` | `false`, blank | The calendar is out of scope (`backend/docs/Calendar-Deployment.md`); the pack role lists apply only to a person with no `users` row |
| `ATELIER_CONTEXT_ENABLED` | `false` | Shows the Knowledge screens (review queue, what the system knows, versions; L.F1 to L.F3). The context routes work either way; stages use the store whenever migration 006 is applied. |
| `ATELIER_IDENTITY_APPROVERS` | blank (the brief approvers) | Who may confirm identity items (rules, exemplars, beliefs, audience language, format) and approve versions that change them: Whitney (rulings 2.5) |
| `ATELIER_WIA_REVIEWERS` | blank (no decision counts as WIA's) | WIA's own reviewers, as emails or names (Whitney and those she names, R50). A Gate 1 or Gate 2 decision whose actor or named author is on this list writes WIA's label (source `gate`); any other, such as one recorded under D12's delegation, is kept with a proxy label (source `gate_delegated`) that never calibrates as WIA's (plan 2.3) |
| `ATELIER_CONTEXT_PREFIX_TOKENS`, `ATELIER_CONTEXT_SITUATIONAL_TOKENS`, `ATELIER_CONTEXT_EXEMPLAR_TOKENS` | `30000`, `6000`, `4000` | Context budgets (section 4.12): the prefix is measured and recorded on each run; the situational block and exemplars are cut to fit |
| `ATELIER_CONTEXT_EXEMPLARS_K` | `3` | Confirmed exemplars a brief writer receives, chosen by channel and pillar (L.B5) |
| `ATELIER_CONTEXT_NIGHTLY_HOUR`, `ATELIER_CONTEXT_MINING_WEEKDAY` | `3` (UTC), `0` (Monday) | When the scheduler runs the staleness job (daily) and the learning loop (weekly) |
| `ATELIER_CONTEXT_MINING_LIVE` | `false` | The setting `context.schedule.mining_live`. `true` lets the weekly learning loop categorise Gate 2 edits with `OPENROUTER_CONTEXT_MINING_MODEL`, a paid call under `ATELIER_RUN_PLAN_ID`. The production configuration (`backend/deploy/production-settings.json`) sets it `true`, to be applied at M4 step 5 under a standing budget; with it off the loop categorises by rules only. |
| `ATELIER_CONTEXT_REVIEW_DAYS_ROSTER_MEMBER` (and one per item kind) | 30 for operating facts, 90 for rules, 180 for exemplars and beliefs | Review intervals the staleness job warns on (L.B8) |

**Models, prompts and embeddings** (`backend/.env.example`; locally in `backend/.env`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | blank | Key for chat stages. Every request carries the privacy routing (`backend/docs/Privacy-Routing-Addendum.md`). |
| `OPENROUTER_MOMENTS_MODEL`, `OPENROUTER_ANGLES_MODEL`, `OPENROUTER_ANGLE_GENERATION_MODEL` | Luna; blank | Extraction model; angle model; strategist override (card profiles only). With `OPENROUTER_VERIFICATION_MODEL`, frozen at submit (E.B16 n): the API and the editorial worker must carry the same values, or the worker refuses the run |
| `OPENROUTER_VERIFICATION_MODEL` | blank | E.B10's model pass over each week's cards; must be another family than the strategist's. Blank runs the deterministic pass only. |
| `OPENROUTER_CONTEXT_MINING_MODEL` | blank | The learning loop's edit categoriser (L.B6); must be another family than the brief writer's. Blank categorises by rules. |
| `CONTENT_ATELIER_ANGLE_PROMPT_PROFILE` | `2026-10-19.reel-editorial.v2` | The setting `prompts.profile.strategist`; strategist profiles are listed in `backend/docs/Angle-Prompt-Profiles.md` |
| `CONTENT_ATELIER_KNOWLEDGE_BASE_DIR` | blank (the committed `knowledge_base/`) | Development override, environment only (a settings row cannot replace it): the file knowledge base to load when no compiled version is active or pinned. Pin a compiled version with the setting `knowledge_base.version` instead. |
| `CONTENT_ATELIER_EXTRACTION_PROFILE` | `2026-10-19.scenes.v2` | The weekly cycle's moments: `2026-10-19.scenes.v2` reads the moments ledger (each document's own scene extraction, 2.B2; a document the ledger lacks is extracted once and kept), `2026-10-13.weekly.v3` the whole-week prompt, `2026-10-18.scenes.v1` the v1 scene loop (replay) (E.B12). Frozen at submit. |
| `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`, `OPENAI_EMBEDDING_MODEL`, `CONTENT_ATELIER_EMBEDDING_DIMENSIONS` | OpenRouter, `openai/text-embedding-3-small`, 1536 | The one embedding contract. A process with a different one refuses to start. |
| `ATELIER_SETTINGS_CACHE_SECONDS` | `5` | How long a process keeps the settings table it read before reading it again (0.B8); a write in the same process is seen at once |
| `WEB_CONCURRENCY` | `3` | The API's processes. The reads are Python work, so one process uses one core however many the host has. Each runs at most 16 requests at a time, each with a database connection, so keep the total well under PostgreSQL's 100 connections |
| `ATELIER_STARTUP_DATABASE_WAIT_SECONDS` | `60` | How long the API and workers wait for the database at start-up before refusing to start, since the contract check needs it (S.B5). |
| `CONTENT_ATELIER_LIVE`, `CONTENT_ATELIER_EMBEDDINGS_ENABLED` | `false` | Legacy file-pipeline switches |
| `CONTENT_ATELIER_LLM_*`, `CONTENT_ATELIER_REQUEST_TIMEOUT_SECONDS` | see the example | Request shape and limits |

### Intake (`backend/intake.env.example`; locally in `backend/.env.intake.local`)

`ATELIER_API_SECRET`, `ATELIER_INTAKE_ADMINS`, `ATELIER_SLACK_INTAKE_TOKEN`, `ATELIER_FATHOM_API_KEY` (when it is unset, the code falls back to `FATHOM_API_KEY`, the name a developer's `backend/.env` uses), `ATELIER_SLACK_WORKSPACE`, `ATELIER_SLACK_CHANNELS`, `ATELIER_ALLOW_INTAKE_ENCODING`, `ATELIER_INTAKE_AUDIO_MODEL` and `ATELIER_INTAKE_REDIS_URL`, plus the embedding contract. A process started without Docker Compose reads `.env.intake.local` through the same single loader as `backend/.env`; the workspace, channels and audio model are settings (`intake.slack.workspace`, `intake.slack.channels`, `intake.audio_model`).

## Settings (plan 0.B8, section 4.10, Appendix D)

Behaviour that is not a secret is a **setting**: a typed value with a code default, stored in the database (`settings` table: key, value, who changed it, when) and changed without a deploy. Secrets, endpoints, paths, the allow-lists and the safety catches stay in environment variables (below); no setting can hold one, and `settings set` refuses a key that looks like a secret.

**Precedence, highest first, for one key:**

1. **A settings row** (`storage_cli settings set`, or `PUT /storage/settings/{key}`).
2. **The legacy environment variable** the setting absorbs (the third column below), from the process environment or, below it, `backend/.env`, the project-root `.env`, `backend/.env.storage.local` and `backend/.env.intake.local`. These four files are read by one loader (`settings_store.load_env_files`), the process environment winning over every file.
3. **The code default**, which equals the value in `backend/.env.example`, `storage.env.example` and `intake.env.example` (a test fails when they differ, so a fresh deployment behaves like the examples).

A key marked "environment wins" in the last column reverses 1 and 2 (development or emergency use; today only `knowledge_base.directory`, which is also not settable in the table; it selects the file knowledge base used when no compiled version is active or pinned). Keys marked "environment only" (the embedding contract and that directory) cannot be set in the table.

**Migrating a deployment that keeps these values in environment variables.** Nothing changes on upgrade: with no row, the variable is the value. Run `python -m backend_pipeline.storage_cli settings import-env --actor <your email>` in a container that has the variables; it writes each one as a row (recording who) and keeps a row that already exists. `settings list` shows each key's value, its source (`default`, `env` or `table`), and `env_ignored` where a row now overrides a variable still set. The variables can then be removed.

**Changing a setting.**

```bash
python -m backend_pipeline.storage_cli settings list
python -m backend_pipeline.storage_cli settings get models.brief
python -m backend_pipeline.storage_cli settings set models.angle_generation openai/gpt-6.1-sol --actor <your email>
python -m backend_pipeline.storage_cli settings set prompts.profile.strategist 2026-10-18.wia-strategist.v5 --actor <your email>
python -m backend_pipeline.storage_cli settings unset models.angle_generation --actor <your email>   # back to the variable, then the default
```

A value is validated by type, choice and range, and an unknown key is refused. The API, the editorial worker (at the start of each job) and the repository read the table again within `ATELIER_SETTINGS_CACHE_SECONDS` (default 5), so the next request or job uses a new value with no restart. A weekly run that is already queued keeps the profile and models it froze at submit, and a worker with different ones refuses it (create a new run). `GET /storage/settings` (editors and approvers) and `PUT /storage/settings/{key}` (approvers) do the same over HTTP for operators and scripts; permissions are decided in `settings_api.require_settings_admin`, which the users-and-roles work (0.B9) replaces. **The Node server does not relay these routes** (its allowlist is unchanged) because no screen reads or edits settings yet; a screen that does adds them with a server test. A database that cannot be reached, or one below migration 005, falls back to the environment and defaults (the API and worker refuse to start without the database anyway), and an invalid stored row is ignored and refuses a start until fixed.

**Runs record what they used.** A weekly run, a comparison reassessment, a chunk-encoding run, a brief run and a pack run store `settings_snapshot` in their `input_refs`: each behavioural key the run uses with its value and its source, plus `knowledge_base_version`, the version the strategist profile loaded at submit, or the version a v2 brief writer froze when its first stage began. It is the evidence for "the run used the profile and models in the table at that time", and it is shown read-only in the week's answer (`GET /storage/weeks/{id}`, under `runs[].input_refs`). The matching numbers (`matching.related`, `matching.close`, `matching.half_life_days`, `matching.max_recency_penalty`, `scoring.visible_threshold`) are frozen again into each assessment snapshot (`scoring`), from the run's `settings_snapshot` where it recorded them, so a resumed, re-checked or approved assessment scores as it was frozen. The comparison runner's three experimental cutoffs (0.78, 0.85, 0.90) and its quality bar of 70 are its own policy, not these settings.

**Live mode names its models.** A live weekly run (at submit and again at job start), a live brief and the legacy `cli run --mode live` refuse to start when a paid stage's model is still the code default: set `models.moment_extraction` and `models.default` (or `models.angle_generation` under a strategist profile), and `models.brief` and `models.brief_review` for briefs, by row or variable, even to the value the default already has.

**Keys** (the Appendix D table of the plan; `Absorbs` is the variable that is the value until a row exists):

| Key | Default | Type | Meaning | Absorbs | Set in |
| --- | --- | --- | --- | --- | --- |
| `models.default` | `openai/gpt-6-luna` | text | Model for every stage without its own (angle refinement, comparison, brief fallback) | `OPENROUTER_ANGLES_MODEL`, `OPENROUTER_MODEL` | table |
| `models.moment_extraction` | `openai/gpt-6-luna` | text | Moment and scene extraction | `OPENROUTER_MOMENTS_MODEL` | table |
| `models.angle_generation` | blank | text (optional) | Strategist angle generation; applies to the card profiles only, blank keeps models.default (use openai/gpt-6.1-sol with the strategist profile) | `OPENROUTER_ANGLE_GENERATION_MODEL` | table |
| `models.card_verification` | blank | text (optional) | E.B10's model pass over each week's cards (another model family than the strategist's); blank skips it | `OPENROUTER_VERIFICATION_MODEL` | table |
| `models.context_mining` | blank | text (optional) | The learning loop's edit categoriser (another family than the brief writer); blank categorises by rules only | `OPENROUTER_CONTEXT_MINING_MODEL` | table |
| `models.brief` | `openai/gpt-6.1-sol` | text (optional) | Brief writer and repair | `ATELIER_BRIEF_MODEL` | table |
| `models.brief_review` | `anthropic/claude-sonnet-5.5` | text (optional) | Brief plan, grade and review | `ATELIER_BRIEF_REVIEW_MODEL` | table |
| `models.pack_writer` | blank | text (optional) | Pack writer: the finisher and the repair (production: `anthropic/claude-opus-5.5`); a live pack refuses to run without it | `ATELIER_PACK_WRITER_MODEL` | table |
| `models.pack_review` | blank | text (optional) | Pack reviewer: the fidelity check and re-check (production: `anthropic/claude-sonnet-5.5`); a live pack refuses to run without it | `ATELIER_PACK_REVIEW_MODEL` | table |
| `models.reasoning_effort.default` | `high` | one of `low`, `medium`, `high` | Reasoning effort for every stage without its own | `CONTENT_ATELIER_LLM_REASONING_EFFORT` | table |
| `models.reasoning_effort.moment_extraction` | blank | one of `low`, `medium`, `high` | Reasoning effort for moment_extraction; blank uses the default | none | table |
| `models.reasoning_effort.angle_generation` | blank | one of `low`, `medium`, `high` | Reasoning effort for angle_generation; blank uses the default | none | table |
| `models.reasoning_effort.card_verification` | blank | one of `low`, `medium`, `high` | Reasoning effort for card_verification; blank uses the default | none | table |
| `models.reasoning_effort.context_mining` | blank | one of `low`, `medium`, `high` | Reasoning effort for context_mining; blank uses the default | none | table |
| `models.reasoning_effort.brief` | blank | one of `low`, `medium`, `high` | Reasoning effort for the brief writer and repair; blank uses the default | none | table |
| `models.reasoning_effort.brief_review` | blank | one of `low`, `medium`, `high` | Reasoning effort for brief plan, grade and review; blank uses the default | none | table |
| `models.reasoning_effort.pack_writer` | `medium` | one of `low`, `medium`, `high` | Reasoning effort for the pack writer (the planning probe's; high would double the cost); blank uses the default | none | table |
| `models.reasoning_effort.pack_review` | `medium` | one of `low`, `medium`, `high` | Reasoning effort for the pack reviewer; blank uses the default | none | table |
| `models.response_format` | `json_schema` | one of `json_schema`, `json_object` | Structured-output request format (R16: json_schema everywhere) | `CONTENT_ATELIER_LLM_RESPONSE_FORMAT` | table |
| `models.payload_format` | `compact_weekly` | one of `legacy_flat`, `compact_weekly` | How the week is sent to the model (the whole week in one call) | `CONTENT_ATELIER_LLM_PAYLOAD_FORMAT` | table |
| `models.completion_tokens` | blank | whole number (optional) | Output token cap; blank sends none (provider default capacity). A live weekly call on the compact payload is refused without one, so production sets it (`deploy/production-settings.json`: 16000) | `CONTENT_ATELIER_LLM_COMPLETION_TOKENS` | table |
| `models.completion_tokens.moment_extraction` | blank | whole number (optional) | Output token cap for scene extraction; blank uses `models.completion_tokens`. Production sets 32000 (`deploy/production-settings.json`): Luna's scene extractions used up to 20,607 output tokens, reasoning included (N1 shakedown, 23 October) | none | table |
| `models.input_limits_enabled` | `true` | true or false | Reject over-size requests locally; false only for an uncapped calibration run | `CONTENT_ATELIER_LLM_INPUT_LIMITS_ENABLED` | table |
| `models.request_timeout_seconds` | `900` | number | Per-request timeout for model calls | `CONTENT_ATELIER_REQUEST_TIMEOUT_SECONDS` | table |
| `models.max_request_characters` | `120000` | whole number | Largest week of source material sent in one request (the trusted prefix is not counted) | `CONTENT_ATELIER_MAX_LLM_REQUEST_CHARACTERS` | table |
| `prompts.profile.strategist` | `2026-10-19.reel-editorial.v2` | profile name | Angle prompt profile (the strategist card profiles are opt-in; v3 and the legacy v1 are kept for replay) | `CONTENT_ATELIER_ANGLE_PROMPT_PROFILE` | table |
| `prompts.profile.extraction` | `2026-10-19.scenes.v2` | one of `2026-10-19.scenes.v2`, `2026-10-13.weekly.v3`, `2026-10-18.scenes.v1`, `2026-10-23.scenes.v3` | Moment extraction: the moments ledger's per-document scenes (v2, or v3 with human lines and counter-expected decisions, E.B31), the whole-week prompt or the v1 scene loop | `CONTENT_ATELIER_EXTRACTION_PROFILE` | table |
| `prompts.profile.card_verification` | `card-verification.v3` | one of `card-verification.v3`, `card-verification.v4` | The card verifier's model-pass prompt: v3 (E.B26), or v4 (E.B30: strategist v7's point tests, with the reason a card is rejected for public use) | — | table |
| `prompts.profile.brief` | `brief_document_v1` | one of `brief_document_v1`, `brief_document_v2` | Brief contract for new briefs (v2 after its writer benchmark); the variable accepts `v1` or `v2` | `ATELIER_BRIEF_SCHEMA` | table |
| `prompts.profile.brief_writer` | `v2` | one of `v2`, `v3`, `v4`, `v4.1`, `v5`, `v5.1` | The brief writer's prompt: v2 or v3 (E.B22: finished copy kept apart from direction, caveats only in Before publishing and Claims) for contract v2; v4 or v4.1 (v4 with a refresh's instructions and locked lines, 5.B6) for contract v3; v5 (E.B33) or v5.1 (NP.B10: v5 writing exactly three Reels, story, stance and b-roll text, when the reel channel is confirmed) for contract v4; frozen with each run | `ATELIER_BRIEF_WRITER` | table |
| `knowledge_base.version` | blank | text (optional) | Pin a compiled knowledge-base version for every stage; blank uses the active approved version | none | table |
| `knowledge_base.directory` | blank | text (optional) | Development override: a file knowledge base to load instead of backend/knowledge_base | `CONTENT_ATELIER_KNOWLEDGE_BASE_DIR` | environment wins; environment only |
| `briefs.channels` | `["reel", "carousel", "email", "caption"]` | list | The confirmed channel set for v2 format plans | `ATELIER_BRIEF_CHANNELS` | table |
| `briefs.max_characters` | `120000` | whole number | Largest brief request, in characters | `ATELIER_BRIEF_MAX_CHARACTERS` | table |
| `embedding.endpoint` | `https://openrouter.ai/api/v1` | text | Embedding endpoint of the archive's contract; changing it means re-encoding (`ATELIER_ALLOW_EMBEDDING_CONTRACT_CHANGE`) | `EMBEDDING_BASE_URL` | environment only |
| `embedding.model` | `openai/text-embedding-3-small` | text | Embedding model string of the archive's contract | `OPENAI_EMBEDDING_MODEL` | environment only |
| `embedding.dimensions` | `1536` | whole number | Embedding dimensions of the archive's contract | `CONTENT_ATELIER_EMBEDDING_DIMENSIONS` | environment only |
| `matching.related` | `0.78` | number | Cosine at which a past angle counts as related | `CONTENT_ATELIER_SIMILARITY_THRESHOLD` | table |
| `matching.close` | `0.9` | number | Cosine at which two angles of one week are flagged as close (cards collapse at matching.duplicate) | `CONTENT_ATELIER_CLOSE_THRESHOLD` | table |
| `matching.duplicate` | `0.9` | number | Cosine at which a card collapses into a better-ranked one, 0.5 to 1.0 (E.B16 l, E.B6) | `ATELIER_DUPLICATE_COSINE` | table |
| `matching.half_life_days` | `28` | number | Recency half-life of a past angle's risk | none | table |
| `matching.max_recency_penalty` | `0.5` | number | Largest score reduction for a repeated angle | none | table |
| `matching.approval_cutoff` | blank | number (optional) | The comparison cutoff Gate 1 approval uses; blank until an authoritative policy is selected | `ATELIER_ANGLE_APPROVAL_CUTOFF` | table |
| `scoring.visible_threshold` | `70` | number | Adjusted score above which a legacy angle is visible | `CONTENT_ATELIER_VISIBLE_THRESHOLD` | table |
| `features.briefs` | `false` | true or false | Briefs (Gate 2, research, writer); needs a reviewed brand bundle | `ATELIER_BRIEFS_ENABLED` | table |
| `gates.one_click` | `false` | true or false | The two approvals are one click and the screens ask only for feedback (production: `true`). Material a client asked to remove, a stale version and a card rejected for public use still stop an approval | none | table |
| `features.packs` | `false` | true or false | Content packs (production: `true`): a v4 brief approved at Gate 2 gets its pack | `ATELIER_PACKS_ENABLED` | table |
| `packs.finish_mode` | `finish` | one of `finish`, `missing_only`, `assemble` | How a pack is finished after Gate 2: the finisher and its fidelity loop; the brief's copy verbatim with only a missing Reel kind written; or no model call (a missing kind shows as not written) | none | table |
| `prompts.profile.pack_finish`, `prompts.profile.pack_check`, `prompts.profile.pack_repair` | `2026-10-25.pack-finish.v2`, `2026-10-25.pack-check.v2`, `2026-10-25.pack-repair.v1` | a released profile (v1 of the finisher and the check stays selectable, so a pack made under it replays) | The finisher's, the fidelity check's and the repair's prompts. v2 (NP.X3's stop rule) keeps the supporting example's own order and outcome and flags an added one. `2026-10-26.pack-check.v3` (NP-7, the code default; production names it only after its reading) adds the approved brief's WIA perspective to the check's sources, so a stance line the team approved is not flagged, and marks one moment widened into a practice unsupported | none | table |
| `prompts.profile.pack_caption`, `prompts.profile.pack_refinish` | `2026-10-26.pack-caption.v1`, `2026-10-26.pack-refinish.v1` | a released profile | NP-7's two person-started passes: the post-recording pass (a face-to-camera Reel's caption and three covers written from what Whitney said on the recorded take, `POST /storage/packs/{id}/pieces/{key}/recorded`) and finishing again with a permission (the finisher with granted items and stated facts as attested evidence, `POST /storage/packs/{id}/refinish`). Both spend the `packs` budget | none | table |
| `features.calendar` | `false` | true or false | The production calendar | `ATELIER_CALENDAR_ENABLED` | table |
| `features.context` | `false` | true or false | The Knowledge screens and review queue (Phase L) | `ATELIER_CONTEXT_ENABLED` | table |
| `display.timezone` | `Asia/Kolkata` | time zone | Calendar display time zone only | `ATELIER_CALENDAR_TIMEZONE` | table |
| `cycle.timezone` | `America/Chicago` | time zone | The weekly cycle's time zone (R36) | none | table |
| `cycle.weekday` | `6` | whole number | The weekday the weekly collection closes and the scheduled cycle starts, 0 Monday to 6 Sunday (R36 said Saturday; the owner moved it to Sunday, 25 October 2026) | none | table |
| `cycle.hour` | `4` | whole number | The hour, in the cycle time zone, the weekly collection closes and the scheduled cycle starts (R36) | none | table |
| `cycle.schedule.enabled`, `cycle.schedule.first_day`, `cycle.schedule.actor` | `false`, none, none | true or false; YYYY-MM-DD; an address | The weekly cycle starts by itself at the scheduled time (3.B11, N7), from the first day, under the actor's standing approval (an approver and intake administrator). Production: on, 2026-11-01, the shared WIA account | none | table |
| `offers.status` | empty | list | Offer status changes made in the app, over the offer calendar file: each line `Offer: status` or `Offer: status until YYYY-MM-DD` (open, waitlist, delivering, closed). Read by every cycle's strategy brief; a closed offer holds no card | none | table |
| `context.release.benchmark_required` | `true` | true or false | Whether an approved identity change waits for a benchmark result before it is used (R44). Production: off, so the approver's approval releases it (no paid benchmark and no developer in the weekly loop) | none | table |
| `context.budget.prefix_tokens` | `30000` | whole number | Knowledge-base prefix budget (about four characters a token) | `ATELIER_CONTEXT_PREFIX_TOKENS` | table |
| `context.budget.situational_tokens` | `6000` | whole number | Dated situational block budget | `ATELIER_CONTEXT_SITUATIONAL_TOKENS` | table |
| `context.budget.exemplar_tokens` | `4000` | whole number | Exemplar budget | `ATELIER_CONTEXT_EXEMPLAR_TOKENS` | table |
| `context.exemplars.k` | `3` | whole number | Exemplars chosen per brief | `ATELIER_CONTEXT_EXEMPLARS_K` | table |
| `context.schedule.nightly_hour` | `3` | whole number | Hour (UTC) the nightly staleness job may run | `ATELIER_CONTEXT_NIGHTLY_HOUR` | table |
| `context.schedule.mining_weekday` | `0` | whole number | Weekday (0 Monday) of the learning loop | `ATELIER_CONTEXT_MINING_WEEKDAY` | table |
| `context.schedule.mining_live` | `false` | true or false | Whether the learning loop's categoriser may make a paid call | `ATELIER_CONTEXT_MINING_LIVE` | table |
| `context.plan_max_age_days` | `30` | whole number | A cycle whose newest content plan entry is older than this many days warns in its week summary (L.B10) | none | table |
| `context.mining.support_weeks` | `4` | whole number | Weeks of Gate reasons and edits a learned rule candidate's two-decision support may span; 1 is the mined week alone (L.B11) | none | table |
| `context.same_point.window_days` | `60` | whole number | A card repeating a central point WIA published this many days ago or less ranks below the cards that do not (3.B5, D23) | none | table |
| `context.same_point.fresh_angle_days` | `30` | whole number | The window for a fresh angle on a published point: the card's point repeats it but its title does not (3.B5, D23) | none | table |
| `context.review_interval.offer` | `30` | whole number | Review interval in days for offer items | `ATELIER_CONTEXT_REVIEW_DAYS_OFFER` | table |
| `context.review_interval.price` | `30` | whole number | Review interval in days for price items | `ATELIER_CONTEXT_REVIEW_DAYS_PRICE` | table |
| `context.review_interval.roster_member` | `30` | whole number | Review interval in days for roster_member items | `ATELIER_CONTEXT_REVIEW_DAYS_ROSTER_MEMBER` | table |
| `context.review_interval.cta` | `60` | whole number | Review interval in days for cta items | `ATELIER_CONTEXT_REVIEW_DAYS_CTA` | table |
| `context.review_interval.campaign` | `14` | whole number | Review interval in days for campaign items | `ATELIER_CONTEXT_REVIEW_DAYS_CAMPAIGN` | table |
| `context.review_interval.content_plan_entry` | `14` | whole number | Review interval in days for content_plan_entry items | `ATELIER_CONTEXT_REVIEW_DAYS_CONTENT_PLAN_ENTRY` | table |
| `context.review_interval.result` | `90` | whole number | Review interval in days for result items | `ATELIER_CONTEXT_REVIEW_DAYS_RESULT` | table |
| `context.review_interval.process_step` | `90` | whole number | Review interval in days for process_step items | `ATELIER_CONTEXT_REVIEW_DAYS_PROCESS_STEP` | table |
| `context.review_interval.performance_note` | `90` | whole number | Review interval in days for performance_note items | `ATELIER_CONTEXT_REVIEW_DAYS_PERFORMANCE_NOTE` | table |
| `context.review_interval.rule` | `90` | whole number | Review interval in days for rule items | `ATELIER_CONTEXT_REVIEW_DAYS_RULE` | table |
| `context.review_interval.format_rule` | `90` | whole number | Review interval in days for format_rule items | `ATELIER_CONTEXT_REVIEW_DAYS_FORMAT_RULE` | table |
| `context.review_interval.exemplar` | `180` | whole number | Review interval in days for exemplar items | `ATELIER_CONTEXT_REVIEW_DAYS_EXEMPLAR` | table |
| `context.review_interval.belief` | `180` | whole number | Review interval in days for belief items | `ATELIER_CONTEXT_REVIEW_DAYS_BELIEF` | table |
| `context.review_interval.audience_phrase` | `180` | whole number | Review interval in days for audience_phrase items | `ATELIER_CONTEXT_REVIEW_DAYS_AUDIENCE_PHRASE` | table |
| `intake.slack.workspace` | `T03P5A3L1DK` | text | Slack workspace of the intake connector | `ATELIER_SLACK_WORKSPACE` | table |
| `intake.slack.channels` | `["C082DURRJ2U", "C09LQ656BPU", "C091CPQD8L9"]` | list | Slack channels the intake connector reads | `ATELIER_SLACK_CHANNELS` | table |
| `intake.audio_model` | `small.en` | text | Speech-to-text model for audio uploads | `ATELIER_INTAKE_AUDIO_MODEL` | table |
| `models.document_classification` | blank | text (optional) | Fast model that places a document the rules cannot (call type); blank classifies by rules only and marks such documents for a person | none | table |
| `models.reasoning_effort.document_classification` | blank | one of `low`, `medium`, `high` | Reasoning effort for document_classification; blank uses the default | none | table |
| `documents.included_call_types` | `client_1to1`, `office_hours`, `workshop`, `prospect`, `slack_thread` | list | Call types whose documents are included in extraction and cycles; internal, vendor and fragment are excluded by default, `other` waits for a person (1.B4) | none | table |
| `documents.staff_email_domains` | `weddingindustryads.com` | list | Email domains that mark a call participant as WIA staff (a Fathom invitee address); names are resolved against the roster | none | table |
| `documents.fragment_words` | `50` | whole number, 1 or more | A transcript with fewer words than this is a fragment | none | table |
| `documents.slack_export.excluded_channels` | `wia-ai-team-testing` | list | Slack channels (by name) the export import leaves out | none | table |
| `documents.segmentation.max_characters` | `2400` | whole number, 200 to 6000 | Largest chunk body, in characters; a turn longer than this stays whole | none | table |
| `documents.segmentation.gap_seconds` | `90` | whole number, 10 or more | A pause longer than this starts a new chunk | none | table |
| `search.rrf_k` | `60` | whole number, 1 to 1000 | Reciprocal rank fusion constant: a hit ranked r by a method adds 1/(k + r); a larger k flattens the difference between ranks | none | table |
| `search.candidates` | `100` | whole number, 10 to 500 | Candidates each method (phrase, meaning) hands to the fusion for each kind of hit; the answer is the best k of them | none | table |
| `search.semantic_min_cosine` | `0.0` | number, 0 to 1 | Meaning matches below this cosine are dropped before fusion; 0 keeps the nearest candidates whatever their cosine. Raise it only after measuring on real moments | none | table |
| `moments.embedding.batch_size` | `32` | whole number, 1 to 256 | Moments sent to the embedding model in one request | none | table |
| `topics.candidates` | `5` | whole number, 1 to 20 | Nearest topics offered for a moment, by embedding | none | table |
| `topics.attach_similarity` | `0.8` | number, 0.5 to 1 | A moment whose nearest active topic is at least this similar (cosine) is attached to it without a model call | none | table |
| `documents.slack_triage.min_words` | `3` | whole number, 0 or more | A Slack thread with fewer words than this (emoji and links not counted) is excluded before extraction (2.B9) | none | table |
| `documents.slack_triage.bot_names` | `slackbot`, `zapier`, `workflow builder`, `github`, `google calendar`, `zoom` | list | Speaker names (any name ending in "bot" too) whose Slack posts are automation; a thread of only these is excluded before extraction (2.B9) | none | table |
| `moments.extraction_profile` | `2026-10-19.scenes.v2` | one of `2026-10-19.scenes.v2`, `2026-10-18.scenes.v1` | Scene profile for a document's own extraction (2.B2); v1 stays for replay and comparison | none | table |
| `moments.estimate.output_tokens_per_document` | `6000` | whole number, 1 or more | Output tokens (reasoning included) `moments extract --estimate` assumes per document; replace with the pilot's measured figure | none | table |
| `moments.estimate.input_usd_per_million` | blank | number (optional) | USD per million input tokens for an extraction model that is not in the price table (`costs.py`) | none | table |
| `moments.estimate.output_usd_per_million` | blank | number (optional) | USD per million output tokens for an extraction model that is not in the price table (`costs.py`) | none | table |

Settings that Appendix D lists but no code reads yet (`scoring.criteria`, `memory.cooldowns.*`, `approvals.*`, `research.*`, `providers.routing`, `slack.*`, `features.web_research`, `cycle.context_budget`) are added with the item that first reads them. Appendix D's `budgets.*` settings are read now: they are the standing weekly budgets in the next section. `roles.*` stays in the allow-list variables until `users` (0.B9) replaces them.

## Standing budgets (plan 6.B3)

Paid calls in a live week need no run-plan variable and no redeploy. Each purpose has one database run plan per budget week
(Monday 00:00 UTC to the next Monday, when the internal OpenRouter key's allowance also resets), named
`plan_standing_<purpose>_<YYYYMMDD>`, created from the settings below the first time a call needs it and renewed by the
scheduler's weekly `standing_budgets` task (0.B6), which also closes last week's plans as expired. Workers and the API find
it by the call's purpose: a job's run scope names it (a weekly cycle is `cycle`, its extraction stage `extraction`, a first
brief `briefs`, a brief revision `refreshes`), otherwise the call's stage does. The call that would pass the cap (with its
worst case: the whole request as input plus its output cap) is refused before it is sent; the job waits instead of failing,
with the reason in words on the job and its run, which the app shows on the cycle screen, the card's brief panel and the
brief; the scheduler's reconcile pass queues it again once the purpose has room (a raised cap or the next week).
`ATELIER_RUN_PLAN_ID` (or `ATELIER_RUN_PLAN_FILE`) still overrides all of this for a one-off run, such as a backlog import
or a benchmark.

The default caps total USD 3.50 a week before packs, inside plan D36's estimate for live operation (about USD 2 to 4 a week,
scaled from the 18 October development week's USD 1.19 for three cards and three briefs), and USD 7.00 with the packs
purpose's USD 3.50 (D43f). Measure the first live week and reset them.

| Settings (USD / calls per week) | Default | What it pays for |
| --- | --- | --- |
| `budgets.weekly_usd.cycle` / `budgets.weekly_calls.cycle` | `1.20` / `80` | the weekly cycle: the strategist call on the window's scenes, its repair, card verification and the cycle's card embeddings |
| `budgets.weekly_usd.briefs` / `budgets.weekly_calls.briefs` | `1.20` / `200` | first briefs (research planning, grading, writing, review, repair, verification, their query embeddings) |
| `budgets.weekly_usd.refreshes` / `budgets.weekly_calls.refreshes` | `0.50` / `120` | brief revisions (refresh with feedback); a card refresh spends it when its job names the purpose |
| `budgets.weekly_usd.embedding` / `budgets.weekly_calls.embedding` | `0.10` / `600` | document, chunk and moment embeddings and search queries outside a brief |
| `budgets.weekly_usd.extraction` / `budgets.weekly_calls.extraction` | `0.40` / `200` | scene extraction of new calls, document classification and topic assignment |
| `budgets.weekly_usd.context_mining` / `budgets.weekly_calls.context_mining` | `0.10` / `60` | the learning loop's categoriser (`context.schedule.mining_live`) |
| `budgets.weekly_usd.packs` / `budgets.weekly_calls.packs` | `3.50` / `60` | content packs (D43f): the finisher, the fidelity check, the repair and the re-check of each pack started by a Gate 2 approval or "Finish again", and NP-7's post-recording pass and permission re-finish. About USD 0.45 to 0.85 a pack. Production is set to `6.00` (D43f) |
| `budgets.standing` | `true` | `false` switches standing budgets off: every paid call then needs a named run plan |
| `budgets.uncapped` | `false` (production: `true`) | `true` lifts every weekly cap: no paid call is refused or waits for a cap; spend is still recorded and shown. The OpenRouter key's own limit still applies |
| `costs.count_from` | blank (production: `2026-10-27T18:01:00Z`) | The moment the costs page counts from (ISO 8601; a day alone counts from 00:00 UTC). Its totals, weeks and content packs leave out everything earlier, such as the team's own tests and remakes; blank counts the last 8 weeks in full. Each content pack's cost comes from its run's own call records (`pack-runs/<run>/cost_summary.json`): the cost the model provider reported for each call |

A blank `budgets.weekly_usd.<purpose>` removes that purpose's standing budget. The settings rows record who set each cap.

```bash
python -m backend_pipeline.storage_cli budgets show                       # this week's caps, spend, what is left and what waits
python -m backend_pipeline.storage_cli budgets set --purpose briefs --weekly-usd 2 --actor whitney@example.com   # an approver
python -m backend_pipeline.storage_cli budgets set --purpose context_mining --clear --actor whitney@example.com
python -m backend_pipeline.storage_cli budgets renew                      # what the scheduler runs each week
```

`GET /storage/budgets` answers the same for the app.

**What was spent** (plan 6.B7): `GET /storage/costs?from=&to=` (any team member, like the budgets) and
`storage_cli costs [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--json]` give the recorded cost of every model and embedding call
(`llm_runs.cost_usd`) and of other paid services (`external_calls`), in all and per budget week, by stage, by model and
provider and by budget purpose (the plan that paid, so a brief's query embedding counts as briefs). The default window is
the last eight budget weeks. A call sent with no recorded cost is counted as unknown, never as zero; replayed calls cost
nothing.

### Caps for a week of use (plan N5)

A live week is one cycle, three briefs (each USD 0.86 to 1.26 measured), a Gate 2 refresh or two (USD 0.74 measured), three
packs (USD 0.60 to 0.68 measured), a post-recording pass or two and the new calls' scenes: about USD 5.5 to 8.5. Production's
caps for the first live week, all on the internal key, whose limit is USD 15 a week:

| Purpose | USD | Why |
| --- | --- | --- |
| cycle | 1.20 | one cycle (about 0.80) |
| briefs | 4.00 | three briefs with room for a repair each (2.70, D42's figure, held the third brief waiting in N4) |
| refreshes | 1.50 | two Gate 2 refreshes (one measured 0.74) and card refreshes |
| embedding | 0.10 | |
| extraction | 0.40 | the week's new calls |
| context_mining | 0.10 | |
| packs | 6.00 | the go-live week (D43f): three packs, two post-recording passes, a Finish again or a permission re-finish |
| **In all** | **13.30** | under the key's USD 15, so a cap, not the key, stops a run |

**The caps stay as set; no weekly reset is needed** (Phase N10: nothing in the week needs a person). They hold a week of
use with room for a repair each, under the key's USD 15. When a week needs more (a busy week, a repair loop), the work
waits with its reason, the app shows it as an alert, and it starts by itself on Monday; an approver may raise a cap with
`budgets set ... --actor <approver>` instead of waiting.

### The weekly tone loop (plan M5, X.2; NP.X4)

Each week, once WIA has used the week:
1. **Requests.** A tone request WIA enters in the app (Context, an approver's entry of kind `rule` or `exemplar`) is confirmed
   on entry; one sent another way is entered the same way, `author` naming who asked.
2. **Corrections given twice.** The learning loop (`POST /storage/context/mining`, or the scheduler's weekly context pass) turns a correction given twice, at
   either gate or in a pack, into one rule candidate citing both (L.B14, NP.B13). An approver accepts it in the review queue
   with its category, edits it, or rejects it.
3. **One version.** `POST /storage/context/versions` (or `kb-publish`) compiles the week's confirmed items into one version.
   An identity change (rules, exemplars) is approved pending its result.
4. **The release.** In production the approver's approval releases the version (`context.release.benchmark_required` is
   false since 25 October 2026: no paid benchmark and no developer in the weekly loop; the version's record says it was
   released without a benchmark, and the version before it stays one setting away). Where the setting is on, a version waits
   for a result: `POST /storage/context/versions/{version}/benchmark` with a reading or a run as `result_ref` makes it active
   (`test_x2_tone_loop_db.py`).
5. **The finisher (NP.X4).** When WIA's pack edits show a change the finisher itself should make (not one rule), a new prompt
   file `pack_finish.vN.md` is released only after the agent's reading of it on the last live week's packs, replayed from
   their saved inputs, and `prompts.profile.pack_finish` names it through `settings apply`. The reading goes beside the
   tone releases.
6. **Labelled cases (NP.X5).** `packs.check_cases.candidates(conn, week_id)` lists the week's person-made pack edits; each
   factual correction is added to `research/packs-2026-10/check-cases.json` and the check is scored against the cases when its
   profile changes.

## Failure alerts (plan 6.B4, Phase N6)

The scheduler scans every pass (`alerts.py`): a failed job (counted from the first scan, so history raises nothing), a
stuck queue (a ready job waiting past its threshold while nothing on its queue moves, or a worker that died mid-job), an
intake connection that stopped (an error, or no collection for three hours), jobs waiting for a weekly budget, a scheduled
run that failed three times, a missed nightly dump or a failed or overdue restore check, and fewer than half of the cards
developed two judged weeks running (6.B13). Each condition is one row in `alerts` (migration 011), opened once, counted
while it lasts and cleared when it goes; a person may dismiss one, and a dismissed condition stays quiet until it has
cleared once. A silent scheduler cannot scan for itself, so `GET /storage/alerts` adds it live from the heartbeat. The app
is the only channel: `notified` records `{"email": "off"}` (the owner, 25 October 2026: no alert emails or Slack).

    GET  /storage/alerts                      open alerts (?resolved=true adds the last 14 days' resolved ones)
    POST /storage/alerts/{alert_id}/dismiss   acknowledge one

What each alert means and what to do is in `backend/docs/Operations-Runbook.md`.

## Home's summary, the schedule and archived weeks (6.F2, 3.B11, Phase N10)

`GET /storage/summary` is what Home shows in one read: what waits for whom (cards at Gate 1, held cards whose date has come,
briefs at Gate 2 for an approver; packs in review for an editor or an approver; packs still with the system, with their
reasons), the latest cycle and whether the schedule started it, the next scheduled run, source health (the collector, the
extraction counts), open alerts and the week's spend against its caps. `GET /storage/schedule` is the next run in words
("Sunday 04:00 America/Chicago"). `GET /storage/weeks/{week_id}/measures` adds editorial monitoring (6.B13) to the week's
measures: the accepted share against the bar, the skip reasons, the cards with an evidence flag, the knowledge base and
strategist the cycle ran on, and its cost.

A week whose content was superseded (its calls run again) or was an early diagnostic below the standard is archived, never
deleted: `storage_cli weeks archive --week-id <id> --reason "<why>" --actor <approver>` (and `weeks restore`). `GET /weeks`
leaves archived weeks out unless asked (`?include_archived=true`), and Home's counts and editorial monitoring skip them.

## Week measures (7.X2)

The main plan's section 4.5 bar and the content-packs plan's section 4.6 measures for one week, read from the database
only (one read-only transaction, no model call):

```bash
python -m backend_pipeline.storage_cli week-measures --week week_2026-10-12          # the report in words
python -m backend_pipeline.storage_cli week-measures --week week_2026-10-12 --json   # the same, as JSON
```

It prints the cards (the slate, developed or reframed keeping the point, the top five, a skip in the top three), rubric
2.3a's means on cards and briefs, the briefs approved and approved without rewriting the central point, Gate 2 edits in
the learning loop's categories, and the packs (in the week, marked ready, ready with light edits or none, pieces
published, cost per pack from `llm_runs`). "Light edits or none" means at most 3 distinct lines (a piece and a path)
edited or put back by a person across the pack's versions. Every count is split into WIA's own rows and delegated ones,
and each threshold is judged on WIA's rows only; a "Done" threshold also reads the week before (two consecutive live
weeks). A decision counts as WIA's when it was recorded as WIA's (`decisions.details.wia_review`, label source `gate`),
whatever `ATELIER_WIA_REVIEWERS` says today; brief edits and published pieces carry no such record and are read against
today's `ATELIER_WIA_REVIEWERS`. Factual problems, repeats and edits by check kind are not in the database and are
reported as not judged.

## Content packs (Phase NP; the content-packs plan, `backend/docs/Content-Atelier-Implementation-Plan-Content-Packs.md`)

**What happens.** Approving a v4 brief at Gate 2 starts its content pack by itself (D43c): one pack run (`run_scope`
`pack_generation`, queue `interactive`) under this week's `packs` standing budget. Its six stages run on the editorial
worker: assemble (hand-off view v2 to five pieces, no model), finish (`models.pack_writer`, Opus 5.5 at medium effort),
check (`models.pack_review`, Sonnet 5.5), repair (Opus, only when something is flagged), re-check (only when something was
repaired) and finalize (put-back, findings, the deterministic checks, the version, no model). A pack takes about 2 to 6
minutes and USD 0.45 to 0.85 (the paid proof: USD 0.47 to 0.69, 2 min 22 s to 6 min 4 s; `research/packs-2026-10/np5-proof.md`). Every pack is 1 email, 1 carousel and 3 Reels (story, stance, b-roll text); a brief without
a stance Reel gets one written by the finisher.

**Switches.** `features.packs` on (production settings) and `ATELIER_ALLOW_PACK_GENERATION=true` on `api` and
`editorial-worker` (with `ATELIER_ALLOW_GENERATION=true`). With the variable off, a pack runs in replay: it answers only
from saved responses, so a new pack fails at its finish step with "No compatible pack response is cached".
`packs.finish_mode` switches the finisher: `finish` (default), `missing_only` (the brief's copy verbatim, only a missing
Reel written and checked) or `assemble` (no model call; a missing Reel shows as not written and blocks Ready). The
switch-back for the finisher's model is `models.pack_writer = anthropic/claude-sonnet-5.5`.

**States, derived on read.** finishing; waiting (a spent budget or a failed step, with the reason; the pack's "Try again"
or `POST /storage/briefs/{id}/pack` retries it); in review; ready to publish (a person marked this exact manifest ready;
no open blocking finding; client permissions and client quotes are before-publishing notes, never a gate); superseded (a
newer version: every edit, revert, text-changing attestation and Finish again makes one). Marking a piece published is
recorded through capture (`published_content`, `source_ref = pack:<brief_id>:<piece>`) outside the manifest.

**Routes** (all under `/storage`, 503 `packs_disabled` while the flag is off): `POST /briefs/{id}/pack`, `GET /packs`
(`week_id`, `brief_id`, `state`), `GET /packs/{id}`, `GET /packs/{id}/production`, `PATCH /packs/{id}/pieces/{key}`,
`POST /packs/{id}/pieces/{key}/revert`, `POST /packs/{id}/clearances`, `POST /packs/{id}/findings/{fid}/attest`,
`POST /packs/{id}/finish`, `POST /packs/{id}/decision`, `POST /packs/{id}/pieces/{key}/published`,
`GET /weeks/{id}/pack-plan`, `GET /weeks/{id}/packs.md`, `GET /weeks/{id}/packs.docx`. The Node relay allowlists each of them.

**The week's pack document** (NP.B12): the same document as Markdown (`packs.md`) or as a Word file (`packs.docx`,
rendered from that Markdown by `python-docx` with its built-in styles and no client template); the pack screen's week view
links both. From the command line: `storage_cli pack-document --week <week_id> [--out packs.md]` (Markdown, printed without
`--out`) or `storage_cli pack-document --week <week_id> --format docx --out packs.docx`.

**The week's review document** (5.B14): the week's cards and briefs with every asset's copy, as Markdown
(`GET /storage/weeks/{id}/review.md`) or as a Word file (`GET /storage/weeks/{id}/review.docx`, rendered from that Markdown
by the pack document's converter on the template in the image, `backend_pipeline/briefs/templates/review-template.docx`,
which carries the 13 October header; the Dockerfile makes it with `python -m backend_pipeline.briefs.review_template`, and
it is never committed, as no office file is kept outside `research/` (R48); without the file the same template is built in
memory). From the command line:
`storage_cli review-document --week-id <week_id> [--out review.md]` or
`storage_cli review-document --week-id <week_id> --format docx --out review.docx`. The Cycles panel links the Markdown; the
Node relay does not allowlist `review.docx` yet, so the app's button for it is a frontend change still to make.

**Replay to another database.** A pack's model answers are saved in the artifact store under `pack-cache/` (keyed by the
exact request, which carries no identifiers that differ between copies of the data) with their artifacts under
`pack-attempts/`. Copying both folders from one store to another (`python -m backend_pipeline.artifacts copy`, never
replace, every upload read back) lets the same approved brief give the same pack at USD 0 there, as NP-6 did from the
paid proof's scratch copy to production.
- **The key covers the exact request, including each stage's wire schema.** A docstring on a `packs/contracts_v2.py`
  output model is part of that schema, so editing one voids every saved answer. A test pins the four schema hashes; change
  them only together with a new profile.
- **Running the CLI against production through a TCP proxy.** The settings loader connects with a 3-second timeout and
  otherwise falls back to defaults. Run research scripts through `research/packs-2026-10/np5/remote.py`, which waits 30
  seconds and stops on that fallback. Each Gate 2 step re-reads the evidence's transcripts and takes minutes over a proxy.

**The free-model shakedown only:** `storage_cli pack-canned --run-id <run> --answer <file>` puts a canned finisher
answer in a pack run's response cache; it refuses unless the run's frozen writer model is a free model.

## Running it locally

From `backend/`, with Docker:

```bash
docker compose up -d --build
docker compose logs -f editorial-worker scheduler
```

`backend/compose.yml` is the whole platform on one machine, the same processes as production (plan 0.B12): Postgres with pgvector (127.0.0.1:15432), Redis (127.0.0.1:16379), a one-shot `migrate` service, the one API (127.0.0.1:18081, the address the Node server's `ATELIER_BACKEND_ORIGIN` points at), the `scheduler`, the `editorial-worker` (queues `interactive`, `default`, `bulk`), the `intake-worker` and the `media-worker`.

- **One environment file**, `backend/.env` (copy `.env.example`). `.env.storage.local` and `.env.intake.local` are still read after it when they exist, so an older setup keeps working. The stack sets its own database, Redis and artifact paths inside the containers.
- **The artifact store is shared with host tools.** The containers mount `backend/.storage-artifacts` (override with `ATELIER_ARTIFACTS_DIR`), so `python -m backend_pipeline.storage_cli ...` run from a terminal against `127.0.0.1:15432` sees the same database and the same saved responses.
- The project name is unchanged (`content-atelier-storage`), so the existing `atelier_data` volume and its data are kept. The older split files (`compose.storage.yml`, `compose.editorial.yml`, `compose.intake.yml`) and their `intake_*` volumes are gone; their data lives on only if you copy it. Never run `down --volumes` on the shared volume.
- The migration runs by itself before the other services start. To run it by hand (a fresh database gets every migration; an existing one is upgraded in place, in one transaction):

  ```bash
  docker compose run --rm migrate
  ```

- **Watch a job run.** Queue work (the app, or `storage_cli submit` from the host), then follow `docker compose logs -f editorial-worker`; `python -m backend_pipeline.jobs health` prints what is queued, running, lost or failed on each queue and whether the scheduler is alive, from the job rows alone.
- Stop with `docker compose down` (keeps the data).

- Paid calls run under a run plan, approved by name, with a call limit, a cost cap and an expiry:

  ```bash
  python -m backend_pipeline.storage_cli plan create --purpose "Week 5 held-out run" --stage angle_generation --model openai/gpt-6.1-sol --input-set-hash <hash> --max-calls 20 --max-cost-usd 4 --approver whitney@example.com
  ```

  Then start the worker with `ATELIER_RUN_PLAN_ID` set to the printed `plan_id`. Use `storage_cli plan show` or `plan close` to inspect or end it.
  A plan covers one input set: `storage_cli plan input-hash --run-id <run>` prints a weekly run's hash (its frozen transcripts), and the worker refuses to spend a plan approved for another week. `--input-set-hash '*'` covers any input set, for a harness or a plan meant for several runs. Only the weekly cycle names its input set, so a plan bound to one week pays for that week's extraction, strategist and verification calls only; brief generation, the learning loop's categoriser, encoding and the evaluation harness name none and run under a `'*'` plan (E.B1).
- Submitting a weekly run, retrying a job and queueing an encoding take the verified email (`X-Atelier-Email`), not the actor ID: a live submit needs an approver (`ATELIER_BRIEF_APPROVERS`), a replay submit, a retry or an encode an editor or approver (`ATELIER_BRIEF_EDITORS`). Every Gate 2 route binds to the email the same way.

**The context system (Phase L).** Once per environment, after `migrate` (migration 006):

```bash
python -m backend_pipeline.storage_cli context-seed --approver <the E.X2 approver's email> --actor <your email>
```

It loads KB 04 to 06 as confirmed items (WIA confirmed them in E.X2) and every entry of the export analysis as a candidate for review. It needs only the committed `research/` and `knowledge_base/` folders, never the raw export; the backend image carries neither `research/` nor the drafts, so run it once from a repository checkout with `ATELIER_DATABASE_URL` pointing at the environment's database. A second run changes nothing, and after it nothing from ChatGPT is accepted (R52). Then:

- the reviewer clears the queue in the app (Knowledge, Review queue), or `GET /storage/context/queue`. The seed's delegated review (decision D12) is committed: `storage_cli context-review-apply --actor <approver email>` applies it in any environment through the same review service, one decision each, and leaves in the queue any entry whose draft changed since;
- `storage_cli kb-compile --actor <email>` writes a draft version from the confirmed items; `kb-approve --version <v> --note "..."` approves it. A version that changes rules, exemplars or voice waits for `python -m evaluation run --knowledge-base-version <v>` (a paid run under a plan) and `kb-benchmark --version <v> --result <file> --passed`. Approval refuses a draft compiled from an older active version ("compile again"), so approving it never rolls back a later approval. `kb-export --version <v> --dir <folder>` writes a version as a file knowledge base and checks that the files reproduce its hashes; that is how `backend/knowledge_base/` follows the reviewed store. The verifier's and Gate 2's lint patterns are compiled from the confirmed rules into each version (a rule carries them in its body's `patterns`; the manifest's `rule_patterns` binds `rejection-rules.patterns.json` by hash, and the loader refuses a hand edit), and every confirmed rule names its category. A version approved but still waiting for its smoke result is kept under `backend/knowledge_base/pending/<version>/` until it passes, then replaces the committed one, which moves to `archive/`;
- published finals (L.B9): on an approved brief the brief screen offers "What was published from this brief". `POST /storage/briefs/{id}/published` (editor or approver; channel, title, the final text, the publish date, an optional link and figures) stores a confirmed `published_content` row linked to the brief and its card (`source_kind` `approved_brief`, `source_ref` `capture:<brief>:<channel>:<piece>`, so sending it again answers the same row with 200), keeps its difference from the brief's copy as an edit for the learning loop and its figures as performance; `GET /storage/briefs/{id}/published` lists the brief's pieces. A brief that is not approved, or whose content no longer matches its approved hash, is refused (409). The final is embedded only when the API process has `ATELIER_ALLOW_ENCODING=true`, an embedding key and a `'*'` plan for the `embedding` stage (as for search); otherwise its vector stays empty. No migration;
- the scheduler (`python -m backend_pipeline.jobs scheduler`) runs the context jobs when `ATELIER_CONTEXT_ENABLED` is on: it retires expired items nightly and runs the learning loop weekly, each once per period even after downtime. `storage_cli context-scheduler` remains as a standalone loop with the same claims. `context-staleness` and `context-mining` run either job once. A missed mining weekday is caught up on the next pass after the nightly hour, over the week before that weekday; when earlier weekdays were missed too, from where the last pass that ran stopped reading, at most `context.mining.support_weeks` weeks back (L.B11). A rule candidate's two independent decisions or edits may come from different weeks within `context.mining.support_weeks` (default 4), so a correction made once in each of two weeks becomes a candidate; a decision or edit already cited by a rule item never supports another; feedback given at a gate (decision notes, card refresh feedback, brief refresh instructions) is sorted into kinds of correction by fixed patterns, and a kind given twice, on two cards or briefs or two days, becomes one rule candidate citing both (L.B14, `knowledge/repeats.py`, no model call);
- the scheduled benchmark (L.B11): every scheduler pass looks for a version approved with an identity change and waiting for its benchmark (compiled from the version in force), and queues one `evaluation_run` job on the `bulk` queue that runs benchmark v1 (strategist v5, development Weeks 1 and 2, three samples) on the version and on its base, then records the comparison on the version (`scheduled_benchmark`: the report's path under `research/benchmark-v1/scheduled/`, the accuracy measures that got worse and a suggested verdict) for an identity approver, who records the verdict under Versions (or `kb-benchmark`); the job never activates a version. It spends only under a standing run plan a person created for it, and refuses without one (the cycle's knowledge notice says why):

  ```bash
  python -m backend_pipeline.storage_cli plan create --standing kb_benchmark --purpose "Standing: benchmark approved identity changes (L.B11)" --stage evaluation --model openai/gpt-6.1-sol --input-set-hash '*' --max-calls 24 --max-cost-usd 3 --hours 2160 --approver <owner email>
  ```

  A plan with fewer calls left than the samples still needed (12 for a first run; a base already benchmarked is reused) is not used. The job runs only where the `evaluation` package and benchmark v1's inputs (`research/`, R48) are present: the backend image carries neither, so on the platform the benchmark worker is a `bulk` worker run from a repository checkout with `ATELIER_DATABASE_URL`, `ATELIER_REDIS_URL` and `OPENROUTER_API_KEY` (the owner decides where it runs); elsewhere the job is not queued and the notice says so. The cycle also says when confirmed identity items wait to be compiled, and when a compiled identity change waits for an identity approver. No migration;

Then, from `frontend/`:

```bash
docker compose up --build
```

Set `COMMAND_CENTER_AUTH_ORIGIN` to a running Command Center (for example `http://host.docker.internal:8787`). Set `ATELIER_BACKEND_ORIGIN=http://host.docker.internal:18081` and the same `ATELIER_API_SECRET`. Sign in at http://localhost:8080/login with a Command Center `team` account.

Checks:

- `GET /health` on both services;
- `GET /api/atelier/flags` after sign-in;
- a `client` session receives no page or bundle (S.F3).

## Documents and evidence (plan Phase 1)

Every transcript, backfilled or live, is a **document**: it belongs to no week, has a call type, an inclusion decision with a
visible reason, an occurrence date with a recorded source (or an explicit "unknown"), participants with roles, and, once
embedded, chunks that carry a header. Nothing below changes a stored original: the text and the passage map are immutable, and
everything learned later is written beside them.

**Bringing documents in** (each command is idempotent; importing the same folder twice adds nothing):

```bash
python -m backend_pipeline.storage_cli documents import <folder>                 # .txt, .vtt, .webvtt and native Fathom folders
python -m backend_pipeline.storage_cli documents slack-export <export folder or .zip> --workspace T03P5A3L1DK
```

One file never stops an import: a file that does not parse is listed under `failed` with its reason (fix it and import
again), and a Fathom capture its `metadata.json` does not select for admission (a capture of a call Zoom already has) is
listed under `skipped`. Read both lists after the backfill import.

**Fathom calls from before the collector's activation** (plan 6.B18): the collector never fetches a call created before it was
activated, so earlier calls come through a one-off command. It lists the meetings recorded in the window (whole days in
`--timezone`, America/Chicago by default) through the collector's client and key (`ATELIER_FATHOM_API_KEY`, else
`FATHOM_API_KEY`), writes each as a native Fathom folder (`transcript.raw.json` as Fathom sent it, and its `metadata.json`)
under `--out`, which must be outside the repository (R48), imports the folders, normalises the new documents by the rules (no
model call: an ambiguous call waits for a person) and prints the embedding estimate with the commands of the paid step:

```bash
python -m backend_pipeline.storage_cli documents fathom-backfill --from 2026-10-05 --to 2026-10-19 --out <folder> --dry-run   # list; fetch and write nothing
python -m backend_pipeline.storage_cli documents fathom-backfill --from 2026-10-05 --to 2026-10-19 --out <folder>             # fetch, import, normalise
python -m backend_pipeline.storage_cli documents fathom-backfill --from 2026-10-05 --to 2026-10-19 --out <folder> --estimate  # the paid steps' cost
```

No call is added twice: a recording already stored is not fetched (the document's identity is the one the live collector
gives it, so a later live collection adds nothing), and a recording that starts within ten minutes of a stored document (the
Zoom file of the same call) or of another recording (a second note-taker), and shares most of its wording with it, is listed
with what it matches and not imported. A rerun adds nothing. `--embed live` also queues the embedding, which spends only under
a run plan.

A call is titled by its calendar event unless that title names nothing (Zoom's "Impromptu Zoom Meeting"), when the
recording's own name in Fathom is used: the rules read the call's type from the title (`fathom_title`, N4).

**The week's calls, by themselves** (Phase N7; the owner, 25 October 2026). From Sunday 1 November 2026, 04:00
America/Chicago, the scheduler's weekly run (`cycle/schedule.py`, keyed by its scheduled day) brings in every Fathom recording
of the seven days before that is not yet a document (the backfill above, run by the scheduler into a temporary folder,
embedding queued live), activates the hourly collector the first time (exactly one collector, on production: 7.B6's
connector step), and starts the week's cycle under `cycle.schedule.actor`'s standing approval. After that the collector
collects every hour, the weekly run catches up anything it missed, and the week's review document (Markdown and Word) is
made when the cycle finishes and kept with the run (`input_refs.review_document`). Nothing is emailed. The settings:
`cycle.timezone`, `cycle.weekday` (6, Sunday), `cycle.hour` (4), `cycle.schedule.enabled`, `cycle.schedule.first_day`,
`cycle.schedule.actor` (an approver and intake administrator: the shared WIA account). The scheduler needs
`ATELIER_ALLOW_GENERATION`, `ATELIER_ALLOW_ENCODING` and `ATELIER_FATHOM_API_KEY`; the intake worker needs
`ATELIER_ALLOW_INTAKE_ENCODING=true`, or the collector's chunk embeddings fail as "not cached".

**What the system now does after every import, by itself** (Phase N10's autonomy pass):
- **Scenes within the hour.** Every hour the scheduler queues the extraction of each included document no extraction has read
  yet, and embeds the scenes that have no vector (`upkeep.py`), so account memory, search and the founder-note picker see a call
  the same day. A document read under an earlier scene profile is never re-extracted here.
- **Second recordings.** A recording of the same meeting by a second note-taker (another source, starting within ten minutes,
  sharing most of its wording) is linked to the first and excluded, by the live collector's normalisation as by the backfill.
- **New accounts.** A client or prospect call whose speakers and title match no account adds the account its title names,
  anonymised, with its outside speakers as people (no pronouns), marked as added by the system (`clients.source` `call`,
  `reviewed` empty) for a person to check; another spelling of an existing account joins it as an alias. A title that names
  nothing ("Impromptu Zoom Meeting") adds nothing.
- **Private matters.** A title naming WIA's own tax, legal, financial or health matters is a vendor call by rule, excluded
  before any model or person sees it (`classify-rules-v4`).

**The week's calls by hand** stays the fallback when the schedule is off (`cycle.schedule.enabled` false). Production's
database and API have no public address, so the commands run from a checkout through a temporary TCP proxy
(`railway tcp-proxy create --port 5432 --service postgres --json`; delete it afterwards with
`railway tcp-proxy delete <id> --yes`), with production's variables loaded and every `ATELIER_ALLOW_*` switch left out, so the
paid work is done by production's own workers under the standing budgets. Run each script through
`research/packs-2026-10/np5/remote.py`, which waits 30 seconds for a connection and stops a run that fell back to default
settings, and `research/golive-2026-10/cli.py`, which is `storage_cli` as a script:

```bash
python -I ../research/packs-2026-10/np5/remote.py ../research/golive-2026-10/cli.py documents fathom-backfill --from <first day> --to <last day> --out <folder outside the repo> --dry-run
python -I ../research/packs-2026-10/np5/remote.py ../research/golive-2026-10/cli.py documents fathom-backfill --from <first day> --to <last day> --out <folder outside the repo>
python -I ../research/packs-2026-10/np5/remote.py ../research/golive-2026-10/cli.py documents reembed --estimate
ATELIER_ALLOW_ENCODING=true python -I ../research/packs-2026-10/np5/remote.py ../research/golive-2026-10/cli.py documents reembed --mode live --actor <approver>
```

The switch only lets the command queue a live job; the job itself runs on production's bulk worker, and the hourly upkeep
extracts the new calls' scenes. Then the cycle starts from the app.

**Reference data** (once, then whenever the roster or the client list changes):

```bash
python -m backend_pipeline.storage_cli people sync          # people mirror the confirmed roster; `people check` shows any gap
python -m backend_pipeline.storage_cli clients import --file <clients.csv|json>   # name, aliases, consent, status, notes
python -m backend_pipeline.storage_cli glossary import --file <glossary.json>     # term, kind, variants
```

The client list is **kept outside the repository** and supplied by WIA; consent defaults to `anonymise_only`. Saving a roster
item in the Knowledge screens updates the matching `people` row in the same transaction.

**Removal on request** (plan 6.B12, `backend_pipeline/removal.py`): when a client asks for their material to be removed, an
administrator runs, in one transaction:

```bash
python -m backend_pipeline.storage_cli clients remove --client-id <id> --actor <admin email> --dry-run   # what it would do
python -m backend_pipeline.storage_cli clients remove --client-id <id> --actor <admin email> --confirm <id> [--delete-account]
```

It deletes the client's documents and their copies, their chunks, their scenes with their topic links and the founder notes
about those calls; finished jobs and the intake's revisions keep their record without the document (the collector never
brings the call back). Every card, brief and pack that cited them, or was built on one that did, is **marked, never
deleted**: the removal's `decisions` row (action `remove_on_request`) lists them with counts and ids (never a name or text),
and the app shows "Built on material removed at a client's request" on the card (not for public use; it cannot be developed),
as a brief's blocker (it cannot be approved or consumed), as a pack's blocking finding (it cannot be marked ready) and in the
review document. The account is kept with consent `no_use` unless `--delete-account` unlinks its people and deletes it. A
queued, running or waiting job on one of the documents refuses the removal until it is done. The original uploads stay in the
artifact store (it has no delete): the answer lists their keys (`originals_kept_in_store`) for the operator to delete in the
bucket. Nightly dumps taken before the removal still hold the material until the dump's pruning drops them (up to twelve
months for the monthly ones, `backup.py`).

**Preparing the backfill** (plan 1.B9, in the production environment from S.B10's originals): import the 170 transcripts, let
the `document_normalise` jobs run on the `bulk` queue (they classify, resolve speakers, date from filename and content, segment
and link copies), then date the rest and embed:

```bash
python -m backend_pipeline.storage_cli documents report                      # what is classified, excluded (with reasons), dated, embedded
python -m backend_pipeline.storage_cli documents normalise --all --estimate  # with models.document_classification set: the model calls and tokens first
python -m backend_pipeline.storage_cli documents normalise --all             # under a run plan for that stage and model; without one, ambiguous calls wait for a person
python -m backend_pipeline.storage_cli documents agreement <corpus/zoom/transcripts.json>   # our call types against the Command Center index
python -m backend_pipeline.storage_cli documents classify <id> --call-type client_1to1 --reason "..." --actor <email>   # a person resolves a disagreement
python -m backend_pipeline.storage_cli documents dates --zoom-listing <zoom.csv> --zoom-timezone America/Chicago [--calendar <cal.ics>] [--apply]
python -m backend_pipeline.storage_cli documents reembed --estimate          # states the cost first (about USD 0.02 per million input tokens)
python -m backend_pipeline.storage_cli documents reembed --mode live         # needs ATELIER_ALLOW_ENCODING=true and an active run plan
```

`documents dates` lists what it would set and writes only with `--apply`. A date comes only from evidence: the provider, a name,
a header line, Zoom's recording list (matched on topic and length) or a calendar export. A match that is not unique stays
undated. `documents report` gives the undated count.

The Zoom backfill's week folders (filed by recording time in Asia/Kolkata, Week 1 = 1 to 7 June 2026) are a **window**, not a
date (N8, 1.B11): a spoken cue that says what today is ("happy Tuesday", "today is the 19th") or a recording-list event that
is unique for its topic inside that week dates the call; otherwise it is dated to its week (`date_evidence.window`,
`occurred_at` stays null, `documents report` counts it as `dated_to_week`). What supports each date is kept in
`transcripts.date_evidence`. The hello@ account's recording list of 1 June to 24 October is
`research/n8-2026-10/zoom-recordings-hello-20260601-20261024.csv` (account time zone America/Chicago).

**Identities** (N8, 1.B12's extension): people and accounts with every spelling the records use (a meeting handle, a
nickname, a device label, a mis-heard transcription), pronouns from evidence, a former team member's leaving date, and two
flags no consent overrides: never name, and never link to a named piece of published work (with the markers that identify
it, such as the case study's figures). The reviewed list is `research/n8-2026-10/identities.json` (a delegated review, D21).

```bash
python -m backend_pipeline.storage_cli identities import --file ../research/n8-2026-10/identities.json --actor <reviewer email>
python -m backend_pipeline.storage_cli identities apply --dry-run     # the documents whose speakers or account change
python -m backend_pipeline.storage_cli identities apply               # re-normalises them (no model call); scenes follow
python -m backend_pipeline.storage_cli documents reembed --estimate   # the re-headed chunks need vectors (cents)
ATELIER_ALLOW_ENCODING=true python -m backend_pipeline.storage_cli documents reembed --mode live --actor <approver>
python -m backend_pipeline.storage_cli identities show --document <transcript id>   # what the strategist and the writer read
```

Run `identities import` again after `people sync` (the roster owns its rows' aliases; the list adds the transcripts'
spellings). A spelling may belong to one person only: the import refuses a list where two people share one. Strategist v8
reads the identities frozen with its cycle; writer v5.2 those frozen with its brief; the card and brief checks block a
never-named identity in public copy, or a never-link marker in copy that names the identity or is built on its calls. A
content pack freezes the identities when it is queued and checks its own copy the same way, the approved brief's copy
included (a brief approved before the identities existed may carry a name they forbid); a pack queued earlier reads the
current ones.

Against a remote database over a TCP proxy, `identities apply` runs one document a minute or more (every query is a round
trip). Queue the same re-normalisation for the workers instead: `documents normalise --ids <the dry run's documents>`, after
`documents normalise --ids ... --estimate` shows no classification call (a queued job asks the classification model about a
document a model classified, where `identities apply` keeps its call type; run those few with `identities apply`'s path).

**Internal meetings as team practice** (N8, 1.B13's extension, D24): add `internal` to `documents.included_call_types`
(`settings apply`), then admit the internal meetings excluded only for being internal; anything excluded for another reason
stays out. Their scenes are team practice (`key_moments.evidence_class`): they may show how WIA works, never a client's
quote, name or figure (the card and brief checks block a client name or figure only an internal meeting carries). Extract
them under scene profile v4, which records how the team works:

```bash
python -m backend_pipeline.storage_cli documents team-practice --actor <approver>            # lists what would be admitted
python -m backend_pipeline.storage_cli documents team-practice --actor <approver> --apply
python -m backend_pipeline.storage_cli moments extract --all-pending --estimate
ATELIER_ALLOW_GENERATION=true python -m backend_pipeline.storage_cli moments extract --all-pending --mode live --actor <approver>
```

**Founder notes** (N8, L.B13, D29): in the seed form, "Founder note" is one line on what stood out in one call, with the
call chosen from the last three weeks. Strategist v8 reads it with its call named and pairs it with that call's scenes or
with none; the week's review document lists each note as used in a card, paired, or unanswered.

**Choosing documents for a cycle** is by date window or explicit set, never by week:

```bash
python -m backend_pipeline.storage_cli documents select --from 2026-10-12T00:00:00-05:00 --to 2026-10-19T00:00:00-05:00 --dry-run
python -m backend_pipeline.storage_cli documents select --from 2026-10-12T00:00:00-05:00 --mode live       # queues the cycle for those documents
```

**Documents API** (`GET /storage/documents`, `GET /storage/documents/{id}`, `POST /storage/documents/{id}/classification`,
`POST /storage/documents/import`): any team member reads; an editor sets a call type, and a person's decision is never
overwritten by a rule or the model. `needs_review=true` lists the calls the rules could not place, which wait for a person; the
Sources screen offers editors the control on each. An editor can also upload one transcript file there (a Zoom export or any
`.txt`/`.vtt` call, sent as JSON: `filename`, `content`, optional `occurred_at` and `source_type`), which goes through the
same import as `documents import`. The
response models are in `backend/openapi.json` and the frontend's generated types.

**Settings** this adds: `documents.included_call_types`, `documents.staff_email_domains`, `documents.fragment_words`,
`documents.slack_export.excluded_channels`, `documents.segmentation.*` and `models.document_classification` (blank: rules only,
and an ambiguous call is marked for a person).

## Moments ledger, search and topics (plan Phase 2)

The order to run it on the real corpus, and what is left: `backend/docs/Phase-2-Moments-Handover.md`. Search, embeddings, topics and the API in detail, with request and response examples: `backend/docs/Phase-2-Search-Notes.md`; extraction, checks, import and backfill: `backend/docs/Phase-2-Extraction-Notes.md`.

```bash
python -m backend_pipeline.storage_cli moments-embed queue --estimate   # count, tokens, USD and the run plan's input set; no call
python -m backend_pipeline.storage_cli moments-embed report             # is every searchable moment embedded under the contract?
python -m backend_pipeline.storage_cli topics assign --estimate         # moments needing a topic, and how many need a model call
python -m backend_pipeline.storage_cli search query "how fast should we reply" --k 5 --text-only
```

A live embedding or topic run needs the encoding (and for topics the generation) catch, an active run plan created for the printed input set, and a queue worker on the
`bulk` queue. **Search in the API** embeds each new query through the same module, so the API process needs `ATELIER_ALLOW_ENCODING=true`, an embedding key and
`ATELIER_RUN_PLAN_ID` naming a plan created with `--input-set-hash '*'` for the `embedding` stage; without them `POST /storage/search` still answers, on the words alone,
and says so in `query_embedding_status`. Routes: `POST /storage/search`, `GET /storage/moments` (and `/facets`, `/{id}`), `GET /storage/topics`,
`POST /storage/topics/{id}/rename|merge|block|unblock` (approver), `POST /storage/moments/{id}/topics` (editor), `GET /storage/documents/extraction-health`.

**Settings** this adds: `search.rrf_k`, `search.candidates`, `search.semantic_min_cosine`, `moments.embedding.batch_size`, `topics.candidates` and `topics.attach_similarity`.
## Moments ledger: extraction (plan Phase 2, `backend/docs/Phase-2-Extraction-Notes.md`)

Each included document gets one `moment_extraction` job on a `document_extraction` run (no week); a scene whose quote binds is
stored with `quote_verified = true`, one that cannot bind as a record with `quote_verified = false` that is never proof.
The backfill is a command, not a run. A live extraction needs an active run plan bound to the input set, which the estimate prints:

```bash
python -m backend_pipeline.storage_cli moments extract --pilot 10 --estimate                  # documents, input tokens, USD estimate; calls nothing
python -m backend_pipeline.storage_cli plan create --purpose "moments pilot" --stage moment_extraction --model <model> \
    --input-set-hash <the hash the estimate printed> --max-calls <n> --max-cost-usd <usd> --approver <email>   # then ATELIER_RUN_PLAN_ID=<plan>
python -m backend_pipeline.storage_cli moments extract --pilot 10 --mode live                 # queues on bulk; refused without the plan
python -m backend_pipeline.storage_cli moments report                                         # verified-quote share, roles, types, zero-scene documents, invariants
python -m backend_pipeline.storage_cli moments extract --all-pending --mode live             # the backfill, after a person has read the pilot
python -m backend_pipeline.storage_cli moments recheck                                        # after a direct database change (normalisation and a consent change re-derive on their own)
python -m backend_pipeline.storage_cli moments recall --golden <golden.json>                  # scene recall per extractor version
python -m backend_pipeline.storage_cli moments import-saved <folder of saved artifacts> [--dry-run]   # Weeks 1 and 2, no provider call
```

`--mode cached` (the default) replays saved responses and never calls a provider; `--mode synthetic` is for a synthetic database.
**Settings** this adds: `moments.extraction_profile`, `moments.estimate.*` and `documents.slack_triage.*`.

## Users and roles

One identity decides what a person may do: the verified email the Node server takes from the Command Center session and sends as both `X-Atelier-Actor` and `X-Atelier-Email` (R37; the session's user ID is never sent). Every `/storage` route checks the shared secret, then resolves that email to a role in one place (`backend_pipeline/gates/roles.py`, used through `gates/access.py`). A header that is not an email address holds no role, and email matching ignores case.

| Role | Allows (each includes the ones above it) |
| --- | --- |
| `viewer` | Read. Anyone Command Center admits as `team` and who is on no list is a viewer. |
| `editor` | Edit cards and briefs, rescore, reassess, retry jobs, submit replay runs, add founder seeds, start a brief. |
| `approver` | Gate 1 and Gate 2 decisions, live runs, knowledge-base review. WIA reviewers are `team` users with this role (R50). |
| `admin` | Everything above, intake administration (activate, collect, retry) and `storage_cli users set`. |

**Precedence.** A person with a row in the `users` table (migration 005) has exactly that row's role: the environment lists are then not consulted for them, so a row can demote someone who is still on a list. A person with no row gets their role from the lists, so a deployment that has not seeded `users` (or has not applied 005) behaves as it did before: `ATELIER_BRIEF_APPROVERS` gives approver, `ATELIER_BRIEF_EDITORS` editor, `ATELIER_INTAKE_ADMINS` admin (for users and intake only: on the lists an intake administrator is not an approver). A person on no row and no list is a viewer. Identity approvers (`ATELIER_IDENTITY_APPROVERS`, Whitney, rulings 2.5) stay a separate, narrower environment list in both cases. Packs and the calendar are outside this scope (R31) and keep their lists (`ATELIER_PACK_EDITORS`, `ATELIER_PACK_APPROVERS`, `ATELIER_CALENDAR_SCHEDULERS`) when there is no row; with a row they follow the role (editor generates and schedules, approver approves a pack).

**Seed and manage the table.** Run once per environment after `migrate`, then as people change:

```bash
python -m backend_pipeline.storage_cli users seed --actor <your email>
python -m backend_pipeline.storage_cli users list
python -m backend_pipeline.storage_cli users set --actor <an admin's email> --email <person> --role approver --slack-user-id <U123>
```

`seed` creates a row for every email on the lists (the highest list wins: admin, approver, editor; identity approvers who are on no other list become viewers), skips entries that are not email addresses, and records who ran it and what it did (the `settings` row `users.seed.last`). It is idempotent and never changes an existing row, so a role set with `users set` survives a second run; `--overwrite` makes the rows follow the lists again. Read its `gains_beyond_the_lists` output: one role cannot say "intake administrator but not approver" or "scheduler but not card editor", so a row may allow more than the lists did; lower it with `users set`. Each `set` is recorded in `users.last_change`; only an administrator may run it.

**`GET /storage/me`** (through the Node server, `GET /api/atelier/me`) answers for the signed-in person: `email`, `role`, `roles`, `source` (`users` or `lists`), `identity_approver` and `can` (`edit_cards`, `edit_briefs`, `decide`, `approve_briefs`, `review_knowledge`, `identity_review`, `manage_users`, `manage_intake`, `generate_packs`, `approve_packs`, `schedule_calendar`). It is read-only and open to any signed-in person; the screens use it to decide what to offer, and the server checks every action again.

## Command Center

- Command Center is the one sign-in for both apps (S.C1, 24 October 2026). The Atelier's `/login` sends the browser to Command Center's PKCE hand-off whenever `COMMAND_CENTER_PUBLIC_ORIGIN` is set (every deployment sets it); a signed-out visitor signs in on Command Center and comes back to the page they asked for. `/login?direct=1` keeps the Atelier's own form, which checks the same accounts.
- One sign-out ends the session in both apps. The Atelier's Sign out (`GET /api/auth/signout`) revokes the session in Command Center over the backchannel (both apps hold the same token, and Command Center refuses a revoked one on every check), clears the Atelier's cookie and passes the browser through Command Center's `/api/auth/signout?from=atelier`, which clears its cookie and ends on its sign-in page. Command Center's Log out does the same in the other direction (`?from=command-center`).
- Command Center's `VITE_CONTENT_ATELIER_URL` points at the Atelier frontend; its launcher signs users into the Atelier through `/api/auth/sso` (PKCE code hand-off).
- Accounts are Command Center's (`AUTH_EMAIL` and `AUTH_PASSWORD_HASH`, then `USER_n_*`; `WIA-Command-Center/DEPLOY.md`). For go-live there is one standard account, `ai@weddingindustryads.com` (the owner, 24 October); it is `admin` in the Atelier's `users` table and on every approver list. Personal accounts for Whitney and the team are added as `USER_n_*`, with a `users` row each, when WIA names them (X.1).
- `ATELIER_WIA_REVIEWERS` stays blank while the account is shared: a decision made on it cannot be told apart from the engineer's, so it is kept with the delegated label (R55) rather than as WIA's.

## Slack notifications for saved content schedules

The existing scheduler can send piece-specific notices through the existing Slack bot. Apply migration 012 and the
prepared backend/deploy/slack-schedule-notifications.settings.json mapping (currently both routes use testing channel C0C3FT6DZAS),
then configure ATELIER_SLACK_BOT_TOKEN on the scheduler only. The optional environment fallbacks are
ATELIER_SLACK_EMAIL_CHANNEL_ID, ATELIER_SLACK_SOCIAL_CHANNEL_ID and ATELIER_PUBLIC_APP_URL; settings table values win.
Without a bot token the sender is off. Initial activation skips historical schedules. No model, frontend configuration,
new worker or external publishing integration is required.

See [Slack schedule notifications](backend/docs/Slack-Schedule-Notifications.md) for activation, message behavior,
delivery retries, status queries and schema-compatible rollback.

The combined publication UI release also needs the [publication workflow alignment](backend/docs/Publication-Workflow-Alignment.md).
Deploy its backend before its frontend: the new calendar and pack-library filters require the updated API and relay.
This alignment adds no migration beyond the Slack feature's 012 and retains existing approval/publication history.

| Setting | Default | Environment fallback |
| --- | --- | --- |
| `slack.schedule_notifications.email_channel_id` | unset (disabled) | `ATELIER_SLACK_EMAIL_CHANNEL_ID` |
| `slack.schedule_notifications.social_channel_id` | unset (disabled) | `ATELIER_SLACK_SOCIAL_CHANNEL_ID` |
| `slack.schedule_notifications.public_app_url` | unset | `ATELIER_PUBLIC_APP_URL` |

`ATELIER_SLACK_BOT_TOKEN` is an environment-only secret and is never a stored setting.

## Railway settings for the frontend service

| Setting | Value |
| --- | --- |
| Root directory | `/frontend` |
| Builder | Dockerfile |
| Healthcheck | `/health`, 60 seconds |
| Restart | On failure, at most 3 retries |

Railway injects `PORT`. Deployments of `main` wait for approval in the Railway dashboard.
