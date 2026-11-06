# Phase N3 and S.C1 on production, 24 October 2026

This records Phase N3 (M4 steps 1 to 5) and the Command Center sign-in (S.C1, built at the owner's request on 24 October)
on Railway. The run was unattended, on the owner's go-ahead in the request, which covered every production change below
(D13). The OpenRouter ceiling was USD 5, and nothing touched billing: Railway's volume backups need a Pro workspace, so
they were replaced by a nightly dump rather than an upgrade. Times are UTC; the local clock is IST, UTC+5:30.

## Step 1. Inventory (before any change, 21:35 UTC on 23 October)

| Project | What ran | Compared with plan section 2.4 |
| --- | --- | --- |
| Content Atelier, `production` | **`postgres`:** `pgvector/pgvector:0.8.2-pg17`, `postgres-volume` (5 GB, 134 MB used); database `atelier` with no tables, only `plpgsql` | As recorded |
| | **`Redis`:** `redis:8.2`, `redis-volume` | Recorded as Redis; the image is 8.2, not 7.4 |
| | **Buckets:** `artifacts` (0 objects; endpoint `t3.storageapi.dev`, virtual-host addressing) and `transfer-inbox` | As recorded |
| | **`Frontend`:** repository `kenil-e2m/WIA-Content-Atelier`, root `/frontend`, watch path `/frontend/**`, `content-atelier.up.railway.app`, the one variable `COMMAND_CENTER_AUTH_ORIGIN`. Newest deployment `591e0b2e` (23 October) waited for approval; every other queued one was already `SKIPPED` | The repositories now live under `kenil-e2m`; GitHub redirects `jainil-e2m` |
| | No API, worker or scheduler; no TCP proxy; no backup schedule and no backups | As recorded |
| Command-Center, `production` | `WIA-Command-Center` from `kenil-e2m/WIA-Command-Center`, deployment `5c18383c` of 6 October (`a1e98b5`), `command-center-wia.up.railway.app`. Variables `AUTH_DISABLED=1` and `VITE_CONTENT_ATELIER_URL`; no `SESSION_SECRET` | As recorded (K64) |

No queued Frontend deployment was approved; the one approved later builds the merged N3 commit (step 4).

## Step 2. Backups and the restore rehearsal

- **Railway volume backups were refused.** `volumeInstanceBackupScheduleUpdate` answered "Manual backups and backup schedules are only available for Pro workspaces". A workspace upgrade is a billing change and the owner's (24 October: never make one), so it was not made.
- **In their place, the nightly dump (6.B6).** `backend_pipeline/backup.py` writes a custom-format `pg_dump` and a manifest to the artifact store under `backups/db/`. The manifest holds exact row counts per table, taken in the dump's own snapshot, plus the newest migration, the size and the SHA-256. It reads the dump back, then prunes to the newest 14, one a week for 8 weeks and one a month for 12 months. `backup verify` restores a dump into a scratch database, compares every count and drops the scratch database. The backend image carries the PostgreSQL 17 client for it.
- **The cron service.** `db-backup` runs the dump at 08:15 UTC every night, with only the database URL and the bucket credentials.
- **The rehearsal.**
  - A fresh dump of the working copy `atelier_work` (`pg_dump -Fc`, 50.6 MB, schema at migration 008, 41 tables) was taken after N2.
  - It was restored into the scratch database `atelier_rehearsal_n3` on production's server: 41 of 41 tables and 12,609 of 12,609 rows matched the working copy's exact counts.
  - The scratch database was dropped (4 min 20 s, through the temporary TCP proxy).

## Step 3. The data

- **Database.** The same dump was restored into the empty `atelier` database (`pg_restore --no-owner --no-acl --exit-on-error`, exit 0). Production's exact counts equal the working copy's: 41 tables, 12,609 rows, no table different. This brings over:
  - N2's October cycle and its five cards;
  - the five briefs, N2's three among them (`brief_579f970d…`, `brief_b2ad6960…`, `brief_57502d22…`);
  - the context store (L.B1, L.B2);
  - knowledge base 9, active;
  - the settings of record;
  - the run plans with this week's spend (USD 4.0721).
- **Artifacts.** 8,224 files (575 MB) from `atelier-work/artifacts` went into the `artifacts` bucket. The copy used the same rules as `backend_pipeline.artifacts copy`, run 16 at a time: never replace, never delete, every upload read back and compared. Result: 8,224 copied, 0 skipped, 0 different, 0 failed. The bucket reports 8,224 objects and 574.0 MB.

## Step 4. Services

- **Created on 24 October.** `api`, `scheduler`, `editorial-worker` (`interactive,default`), `bulk-worker` (`bulk`) and `intake-worker` (`intake`), per DEPLOYMENT.md's table:
  - source: repository `main`, root `/backend`, `backend/Dockerfile`, watch path `/backend/**`;
  - pre-deploy `storage_cli migrate` on each (lock-guarded);
  - `api` has health check `/health` and `PORT=8000`.
- **Variables.**
  - The database URL references `${{postgres.…}}` (private domain), and the Redis URL is `${{Redis.REDIS_URL}}` (`redis.railway.internal`).
  - The artifact store is the bucket (`ATELIER_ARTIFACT_STORE=s3` and `ATELIER_S3_*`).
  - `ATELIER_API_SECRET` is generated, and equal on the Frontend.
  - The internal OpenRouter key serves as both `OPENROUTER_API_KEY` and `EMBEDDING_API_KEY`, with the embedding contract as in the working copy.
  - The paid-stage switches are on (`ATELIER_ALLOW_GENERATION`, `_ENCODING`, `_REFINEMENT` and `_BRIEF_GENERATION`): money is bounded by the standing budgets.
  - `ATELIER_FATHOM_API_KEY` is set.
  - The approver, editor, intake-admin and identity-approver lists hold `ai@weddingindustryads.com`.
  - `ATELIER_WIA_REVIEWERS` is left blank: see "Decisions taken".
- **Deployments.**
  - The first deployments built `main` at `087769f` and all started. `api` answered `/health`, each worker listened on its queues, and `jobs health` reported the scheduler's pass within 30 seconds, no lost job and `ok: true` (the failed counts are the working copy's history).
  - After the code merge (`f58c6c4`), every service's deployment waited for approval. Only that commit's newest deployment was approved, on each service.
- **Budgets and model routes.**
  - **Standing budgets:** D36's figures, with briefs at D42's USD 2.70 (three briefs), for a weekly total of USD 5.00:

    | Purpose | Weekly cap (USD) |
    | --- | --- |
    | Cycle | 1.20 |
    | Briefs | 2.70 |
    | Refreshes | 0.50 |
    | Embedding | 0.10 |
    | Extraction | 0.40 |
    | Context mining | 0.10 |

  - **This week's headroom:** this week's plans already carry N2's spend, so production can spend at most about USD 1.41 more before the renewal on 26 October.
  - **Model routes:** `token_budget --store` cached the public route of `openai/gpt-6-luna`, `openai/gpt-6.1-sol` and `anthropic/claude-sonnet-5.5` in the bucket. These are public catalogue data, with no private data sent.
- **Done when: "a test document passes through normalisation and embedding on production".**
  - The synthetic test call `transcript_31388a86dd2239147c20f3b0` (three lines, no client material) was imported.
  - Production's `bulk-worker` normalised it. The rules could not place it, so a Luna classification call ran (USD 0.000092, standing budget `extraction`) and it was left for a person.
  - A person's decision included it as a workshop, which gave one current chunk.
  - `documents reembed --mode live` queued `chunk_job_ccb8b4ab4cd8fa90bebcceac`. `bulk-worker` completed it ("All 1 transcript chunks encoded and verified"): a 1,536-dimension `openai/text-embedding-3-small` vector, USD 0.000002, standing budget `embedding`.
  - The document was then excluded by a person's decision (reason recorded), so it never enters a cycle.

## Step 5. Configuration

| Check | Result |
| --- | --- |
| Context bootstrap, from a checkout of `main` | `context-seed`: `already_seeded` (89 confirmed items, 704 candidates). `context-review-apply`: 0 applied, 704 already decided. `context-published-points`: 61 unchanged. `context-entries-apply`: 19 already entered |
| Knowledge base of record | `kb-compile --on 2026-10-22`: `unchanged`, version `wia-kb-2026-10-22.c-a1a75795` (knowledge base 9), active |
| `settings apply --file deploy/production-settings.json` | Dry run: 0 would change, 18 unchanged; applied: 0 applied, 18 unchanged (`mining_live` on, contract v4 with writer v5, strategist v7, card verification v4, scene profile v3, the 32,000 output cap) |
| `users seed` | One row: `ai@weddingindustryads.com`, `admin` |

## S.C1. One sign-in and one sign-out (Command Center and the Atelier)

- **Code.**
  - Command Center (kenil-e2m/WIA-Command-Center#3, merged `d5b82b5`): production refuses `AUTH_DISABLED` and requires `SESSION_SECRET` and `AUTH_PASSWORD_HASH`, from the earlier `s-c1-production-auth` branch. A sign-out revokes the session token itself, `GET /api/auth/signout` makes the cross-app round trip, and a signed-out hand-off resumes after sign-in (`/login?next=`).
  - The Atelier (kenil-e2m/WIA-Content-Atelier#13): `/login` hands off to Command Center when `COMMAND_CENTER_PUBLIC_ORIGIN` is set, and `GET /api/auth/signout` revokes the session, clears the Atelier's cookie and clears Command Center's.
- **Production.**
  - Command Center: `AUTH_EMAIL=ai@weddingindustryads.com`, `AUTH_NAME`, `AUTH_PASSWORD_HASH` (scrypt) and `SESSION_SECRET` set; `AUTH_DISABLED` removed.
  - Frontend: `ATELIER_BACKEND_ORIGIN=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:8000`, `ATELIER_API_SECRET`, and `COMMAND_CENTER_AUTH_ORIGIN` and `COMMAND_CENTER_PUBLIC_ORIGIN` (both the public Command Center origin; private networking does not cross projects).
  - The password is in the owner's local file `atelier-work/credentials/ai-weddingindustryads-login.txt`, never in git.
- **Checked on production with curl.**
  - **Command Center refuses** a request with no cookie, a wrong password and the old any-email demo login: 401 each.
  - **Sign-in.** The account signs in. An Atelier page asked for while signed out goes to Atelier `/login`, then the hand-off, then Command Center `/login?next=…`. After signing in, the hand-off continues and the browser lands on `/weekly-studio` with the page served.
  - **Real data.** `/api/atelier/me` answers `ai@weddingindustryads.com`, `admin`, from `users`. `/api/atelier/briefs` lists the five restored briefs, and `/api/atelier/budgets` gives cap 5.0 and spent 4.0722.
  - **Sign-out from the Atelier.** The Atelier's sign-out passes through Command Center's (`?from=atelier`) and ends on Command Center `/login`. Afterwards both `/api/atelier/me` and Command Center's `/api/auth/session` answer 401.
  - **Sign-out from Command Center.** `POST /api/auth/logout` ends the Atelier session too, even with the Atelier's cookie still present: `/api/atelier/me` answers 401 and a page redirects to sign-in. The `GET /api/auth/signout` round trip clears both cookies.

## The first production dump, and a defect it found

- **The first dump** (`backups/db/atelier-20261023T224448Z.dump`, 50.6 MB) was written and read back. Its restore check then reported a mismatch: the manifest's counts had five tables with one or two rows more than the dump.
- **The cause:** the counts were read a moment after `pg_dump` finished, while the test document was being imported.
- **Fixed in this record's commit.** The counts are now taken inside one REPEATABLE READ transaction whose exported snapshot `pg_dump` reads (`--snapshot`), so the manifest describes exactly the dumped rows. A unit test checks the flag, and a database test checks that a write after the snapshot is outside its counts.
- **The second dump, with the fix** (`backups/db/atelier-20261023T230057Z.dump`, snapshot `00000033-00000036-1`, 50.6 MB, 41 tables, 12,631 rows), then its restore check (`atelier_restore_check_20261023t230340z`): 41 tables, 12,631 rows, `matches: true`, scratch database dropped.
- **The cron service itself.** `db-backup` was moved briefly to 23:08 UTC to prove the platform path, then put back to 08:15 UTC (next run 24 October 08:15). It wrote `backups/db/atelier-20261023T231159Z.dump` (50.6 MB, 41 tables, 12,631 rows) from Railway. That run used `main` before this fix; the fix reaches it with this record's merge.

## Access left behind

The temporary TCP proxy on `postgres` (used for the rehearsal, the restore, the checks and the CLI steps) was deleted at the end of the run; production's database has no public address again. The Railway CLI stays signed in on the owner's machine.

## Spend

| Key | USD | What |
| --- | --- | --- |
| OpenRouter internal key (production's) | 0.000094 | The test document's classification call (0.000092) and embedding (0.000002) |
| OpenRouter Client key | 0 | — |
| Railway billing | No change | No plan change, no backup purchase; the services run on the existing workspace |

## Left open

- **Personal accounts and WIA's own labels.** Whitney's and the team's personal accounts (`USER_n_*` and a `users` row each) are added when WIA names them (X.1). Until then decisions on the shared account carry the delegated label (`ATELIER_WIA_REVIEWERS` blank).
- **The Fathom collector and the October backlog** (M4 step 8, 6.B1, 6.B18) and **7.X1's live verification** (step 9) are Phase N4's.
- **Volume-level backups** remain a Pro-plan feature; the nightly dump covers the database, and the artifacts bucket itself has no second copy.
