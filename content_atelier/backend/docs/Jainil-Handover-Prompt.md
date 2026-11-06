# Prompt for Jainil: paste this into Claude Code

Needs only: the Railway CLI installed and logged in (`railway whoami` works), Git and Python 3.12. Open Claude Code in your WIA-Content-Atelier checkout and paste everything below the line. It does the whole handover on its own. There are no keys to copy: the tools read the upload bucket's access from your Railway login.

---

Hand over everything Content Atelier has on this machine to WIA's Railway storage, on your own, start to finish, without asking me questions. It is a copy: delete nothing, stop nothing, change nothing on this machine. The data includes confidential client transcripts: never print their text or any secret.

1. **Tools.** Do not touch my working tree. Run `git clone https://github.com/jainil-e2m/WIA-Content-Atelier.git ~/wia-handover-tools`, then in `~/wia-handover-tools/backend` create a venv (`python -m venv .venv`, activate it) and `pip install boto3 "psycopg[binary]"`. Remember my own checkout as `$REPO` (the folder that holds `backend/` and `frontend/`). The upload bucket's access comes from the Railway CLI login: if `railway whoami` fails, run `railway login` and finish the browser sign-in; the tools do the rest (they link the Content Atelier project and read the `transfer-inbox` bucket's credentials into memory). Never print or store those credentials.
2. **Find everything.** Without asking me:
   - the Postgres database(s): `docker ps` (the compose stack's Postgres, normally database `atelier`, user `atelier`, port 15432) or `ATELIER_DATABASE_URL` in `$REPO/backend/.env*` (also an older separate intake database if one exists). Use the URL to connect only; never print it;
   - the artifact tree: `$REPO/backend/.storage-artifacts/` (or wherever `ATELIER_ARTIFACT_ROOT` points);
   - the Zoom backfill: the originals of the 170 transcripts (`.vtt`, `.txt`, `transcript.raw.json`) and whatever was used to date them (a Zoom recording list, a calendar export, the backfill scripts); search `$REPO`, Desktop, Documents and Downloads;
   - code that is not in git, saved without touching the checkout: `git -C $REPO bundle create <tmp>/code/all.bundle --all`, `git -C $REPO stash list > <tmp>/code/stashes.txt`, `git -C $REPO diff HEAD > <tmp>/code/uncommitted.patch`, and copy the untracked files (never `.env*`) into `<tmp>/code/untracked/`.
3. **Inventory.** From `~/wia-handover-tools/backend`: `python scripts/transfer/inventory.py --repo "$REPO" --database atelier=<url> [--database intake=<url>] --artifacts <artifact tree> --search-dir ~/Desktop --search-dir ~/Documents --search-dir ~/Downloads --out ./transfer-work`.
4. **Upload everything found**: every database, the artifact tree, the Zoom backfill folders, and the code folder from step 2:
   `python scripts/transfer/pack_and_upload.py --upload --stamp <today YYYY-MM-DD> --database atelier=<url> [--database intake=<url>] --artifacts <artifact tree> --extra zoom-backfill=<folder> [--extra dating-inputs=<folder>] --extra code=<tmp>/code --report-dir ./transfer-work --work ./transfer-work/pack`
   The tool dumps the database itself: with the local `pg_dump` when it works, otherwise inside the Postgres Docker container it finds from the URL's port (or name one with `--docker-container <name>`; with no URL use `--database atelier=`). If it is interrupted, run the identical command again. It leaves out `.env*`, keys and any file that looks like a credential; leave those out too.
5. **Verify.** `python scripts/transfer/fetch_and_verify.py list` must show your stamp as `complete`.
6. **Report** (no secrets, no client text), to paste back to the owner: the stamp; per database its name, Postgres and pgvector versions, schema versions, dump size and row counts (transcripts, chunks, chunk embeddings, moments, angles, briefs); per folder the file count, size and the files left out; anything not handed over and why; any error.

Keep `./transfer-work` and all original data until the owner confirms.
