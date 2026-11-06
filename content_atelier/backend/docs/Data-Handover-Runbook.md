# Data handover: Jainil's machine to Railway to the owner's machine

Plan items: S.B10 (back up and share the real state), 7.B3 (inventory), 7.B5 (transfer runbook). This is the **early copy for development**, not the final cut-over (7.B6): nothing is deleted or stopped on Jainil's machine, and production does not start using the data. Prompt for Jainil's agent: `Jainil-Handover-Prompt.md`.

## What is set up on Railway (project `Content Atelier`, environment `production`)

| Piece | State | Purpose |
| --- | --- | --- |
| Bucket `transfer-inbox` (iad) | created 19 October 2026 | The handover vessel. Its own credentials, separate from production's, are the ones given to Jainil; reset them when the handover is done. |
| Bucket `artifacts` (iad) | created, empty | The production artifact store (`ATELIER_ARTIFACT_STORE=s3`). Not used until the API runs. |
| Service `postgres` (`pgvector/pgvector:0.8.2-pg17`, a 5 GB volume at `/var/lib/postgresql/data`) | online, empty database `atelier` | Where the data is restored for production (7.B5/7.B6). Private network only; no public address. |
| Service `redis` (Railway Redis) | online | The queue transport for the services to come. |
| Services `Frontend` (existing) | unchanged; a deployment of the latest `main` is waiting for approval in Railway | Not touched. |

Not created yet (they are not needed to receive data): `api`, `scheduler`, `editorial-worker`, `intake-worker`, `media-worker`, and the variables that tie them to the above. Their definitions are in `DEPLOYMENT.md`, "Production services on Railway". The order there stands: restore the data, then deploy.

Jainil's prompt is `backend/docs/Jainil-Handover-Prompt.md`. It holds no secret: the tools read the `transfer-inbox` bucket's access from the Railway CLI login (`railway link` to the project, then `railway bucket credentials`), so Jainil's login must have access to the Content Atelier project. They give read and write access to **the `transfer-inbox` bucket only**.

## How it works

`backend/scripts/transfer/` has three commands, all Python 3.12 with `boto3` (and `psycopg` for the inventory):

| Command | Where | Does |
| --- | --- | --- |
| `inventory.py` | Jainil | Read-only: databases (versions, pgvector, row counts, embeddings, models, dimensions), the artifact tree, transcript folders, env variable **names**, git state. Writes `inventory-report.md/.json`. No secret, no text. |
| `pack_and_upload.py` | Jainil | Dry run by default. With `--upload`: `pg_dump -Fc` of each database (directly or through `docker exec`), the artifact tree and extra folders packed into ~256 MB tar.gz parts (byte-for-byte repeatable, so a broken upload resumes), every part uploaded with its sha256, reports, then `manifest.json` **last**. Leaves out `.env*`, keys, and any file whose text looks like a credential, and says which. |
| `fetch_and_verify.py` | the owner | `list` shows handovers and whether each is complete; `download --stamp S --to DIR` checks every sha256, unpacks safely, checks each file again, and prints the restore commands. |

The bucket layout: `handover/<stamp>/{manifest.json, db/*.dump, artifacts/part-NNNN.tar.gz, extra-<name>/part-NNNN.tar.gz, reports/*}`. A handover without `manifest.json` is not complete.

## Steps

### A. Owner (once)

1. Send Jainil `backend/docs/Jainil-Handover-Prompt.md` (or its text). He needs the Railway CLI installed and logged in; he pastes it into Claude Code in his checkout and it does everything by itself.
2. Ask him to keep the machine quiet (no generation or backfill running) while it dumps.

### B. Jainil (his agent does this; about 30 minutes plus upload time)

1. Clone the tools into a separate folder, make a venv, `pip install boto3 "psycopg[binary]"`.
2. Run `inventory.py`; read the summary; decide per item: send, keep local, discard (the prompt asks).
3. Push any unpushed code to a branch `handover/jainil-<date>` (never `main`), without disturbing his working tree.
4. Dry run `pack_and_upload.py` and read what is left out.
5. On his yes, run it with `--upload`; confirm `Done ... manifest.json`; `fetch_and_verify.py list` shows the stamp as `complete`.
6. Send the owner the stamp and the short report (counts, sizes, left-out files, branch).

### C. Owner: get it onto your machine

```bash
cd WIA-Content-Atelier/backend
# with the Railway CLI logged in (the tools read the bucket access from it), or with a workspace token in
# RAILWAY_API_TOKEN (a token has no user, so the tools skip `whoami` and `link` and name the project by ID), then:
python scripts/transfer/fetch_and_verify.py list
python scripts/transfer/fetch_and_verify.py download --stamp <stamp> --to ../handover-<stamp>
```

It prints the exact restore commands. In short:

1. **Database(s)**: into a long-lived local pgvector Postgres of its own, with a named volume and no `--rm` (the CI image `pgvector/pgvector:0.8.2-pg17`; never the throwaway test container, whose cleanup would remove it): create an empty database, `pg_restore --no-owner --no-acl -d <db> db/<name>.dump`. Compare the row counts with Jainil's report. Then `ATELIER_DATABASE_URL=<that database> python -m backend_pipeline.storage_cli migrate` brings it from its version to the latest; the embedding-contract check (`startup.py`) must pass with **no** re-embedding (same endpoint, model, 1536 dimensions).
2. **Artifacts**: `python -m backend_pipeline.artifacts copy --from ../handover-<stamp>/artifacts --dry-run`, then without `--dry-run` (into the folder or bucket the environment names; it never replaces or deletes). Replay Week 2's saved extraction and check that no provider call is made (S.B10's "done when").
3. **Zoom backfill originals**: `storage_cli documents import <folder>`, then the order in `Phase-2-Moments-Handover.md` ("Running it on the real corpus"): `normalise`, `dates --apply` (with the Zoom recording list), `reembed --estimate`, `moments import-saved --dry-run`, the pilot, and so on. Anything that spends money still needs its estimate and a run plan.
4. **Code**: review branch `handover/jainil-<date>` (7.B4): merge what belongs, record what is discarded.

### D. Owner: close the handover

1. Confirm to Jainil that the data is restored and checked; only then may he stop treating his machine as the only copy (K21 stays open until the final cut-over).
2. Rotate the bucket credentials: `railway bucket credentials --bucket transfer-inbox --reset` (Jainil's copy stops working). Delete the handover objects once restored if you do not want client data to sit in the inbox bucket: `fetch_and_verify.py` never deletes; use the Railway dashboard or an S3 client with the bucket's new credentials.
3. Update the plan: S.B10, 1.B4, 1.B6, 1.B9, 1.B11, 0.B4, 2.B11 and the rest that waited for the data move on from there.

### E. Later, into Railway's own Postgres (7.B5/7.B6, not done here)

The empty `postgres` service is ready. The restore into it needs a client that can reach it: either deploy `api` (private network) and run `pg_restore` from a container image that has the matching client, or turn on a temporary TCP proxy for `postgres` in the Railway dashboard, run `docker run --rm -v <dump folder>:/d pgvector/pgvector:0.8.2-pg17 pg_restore --no-owner --no-acl -h <proxy host> -p <proxy port> -U atelier -d atelier /d/db/<name>.dump`, and remove the proxy straight after. Do it as a rehearsal on a scratch database first (D13), then at the cut-over. This step needs the owner's go-ahead at that moment.

## Safety notes

- Client call text is in the dumps and the artifact tree. It travels over TLS to a private bucket in WIA's own Railway project and sits there only as long as you keep it (step D). It is not committed anywhere (`.gitignore` covers `transfer-work/` and `handover-*/`).
- The tools never print a secret or a transcript line, and leave out credential files by name and by content pattern. A pattern match is a heuristic: if Jainil knows of a secret elsewhere in the tree, tell him to exclude it (move it out of the folder) before the upload.
- The Postgres password in `postgres`' variables was generated on Railway and is not stored in git; read it with `railway variable list -s postgres` when the restore needs it.
- The `Frontend` service has a deployment waiting for approval in Railway. Approving it publishes the latest `main` frontend with the Moments screens; it is not part of this handover.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `Set TRANSFER_S3_... first` | The variables are not in this terminal; set them from the credentials file. |
| `pg_dump ... server version newer than pg_dump` | Use `--docker-container <name>` so the dump runs inside the server's image. |
| Upload stops half way | Run the identical command again; parts already in the bucket are recognised by size and sha256 and skipped (the database dump is made again and re-sent). |
| `manifest.json already exists` | That stamp is finished; use a new `--stamp` for another handover. |
| `fetch_and_verify ... did not verify` | A part changed in transit or was truncated; run `download` again (it keeps what verified). |
