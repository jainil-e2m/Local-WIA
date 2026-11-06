# Restore rehearsal of the working copy (23 October 2026)

A local rehearsal of M4 steps 2 and 3 (6.B6 go-live subset, 7.B5's rehearsal), run on the owner's machine after the October
calls were imported (6.B18). No provider call; no production change.

| Step | Result |
| --- | --- |
| Backup before the October import | `atelier_work-before-6B18.dump` (46 MB, `pg_dump -Fc`), taken by 6.B18's run before any write |
| Fresh dump after the import | `atelier_work-2026-10-23.dump` (47.5 MB, `pg_dump -Fc` inside `atelier-work-pg`, Postgres 17 with pgvector 0.8.2) |
| Restore | `pg_restore --no-owner --exit-on-error` into a scratch database `restore_rehearsal` on the same server: no error |
| Counts | Every base table's row count compared between `atelier_work` and the restore: **41 of 41 tables identical** (for example `transcripts` 188, `pipeline_runs` 73) |
| Schema | Both at migration `008_moments_ledger.sql`, the newest in `backend/migrations/` on `main` (no track added a migration) |
| Clean-up | The scratch database dropped; the dump kept beside the repository at `atelier-wt/backups/` (outside git: client material, R48) |

The script is `pg_dump -Fc` / `pg_restore --no-owner` with a per-table `count(*)` over `information_schema.tables`; its
output is `counts-atelier_work.txt` and `counts-restore_rehearsal.txt` beside the dump.

**What it does not show.** The rehearsal is on the same Postgres server as the source; M4 step 2 repeats it on Railway's
volume with backups switched on. The dump holds the October calls normalised and dated but not yet embedded or
scene-extracted (those are paid runs after the internal key's weekly reset on 26 October, section 5.0a); M4 step 3 takes
the dump again after them and after M3.
