# Prompt for the next session (paste into Claude Code at the repo root)

---

You are continuing an implementation run on the WIA Content Atelier repository. The previous session ran out of usage on another machine and left a handoff. Work in three stages, in order, and do not skip the second.

## Stage 1: ground yourself (read only; no paid call, no Railway change, no push)

1. Run `git pull`. Then read `backend/docs/handoff/2026-10-19-run-handoff.md` in full; it is the source of truth for the rules, the state and the pending work. Section 9, at the bottom, records the exact state at handoff.
2. Read the plan's status parts in `backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md`:
   - the status table near the top;
   - the decision rows D15 to D21;
   - every row the handoff lists as pending or in progress, read in full, including its done-when (the last cell). Find a row with `grep -n '^| <ID> |'`.
3. Skim the two pushed branches:
   - `git log --stat main..origin/handoff/wave1-0B8-LB10-EB17`
   - `git log --stat main..origin/handoff/wave1-EB11-EX7-wip`
4. Write me a short grounding summary:
   - what the task is;
   - what is done;
   - what is in progress;
   - what is pending, in the order you will do it, with a wall-clock estimate and a spend estimate per item;
   - how you will run work in parallel. Use at most two background agents at a time, each in its own git worktree with its own throwaway Postgres container on a distinct port. Only you do paid work and pushes to `main`.

## Stage 2: check for blockers, and report them before starting anything

Check each of these and tell me the result. **If any is a blocker, stop after reporting and wait for my answer.**

1. **`backend/.env`** exists and has the variable names `OPENROUTER_API_KEY_INTERNAL`, `OPENROUTER_API_KEY_CLIENT`, a Fathom key and `RAILWAY_TOKEN`. Check the names only; never print a value. It is not in git: if it is missing, I must copy it over myself.
2. **Python:** a `backend/.venv` with Python 3.12, `pip install -r backend/requirements.txt` (plus `boto3`) done, and `python -c "import backend_pipeline"` works from `backend/`.
3. **Docker** runs and can pull `pgvector/pgvector:0.8.2-pg17`.
4. **The working-copy data** (handoff section 8 and section 9's stamp):
   - Is the handover stamp listed as complete in the `transfer-inbox` bucket?
   - Download it, verify it, restore `atelier_work` into a long-lived container (named volume, no `--rm`), migrate, and copy the artifacts.
   - Check the row counts against section 9.

   This step only reads the bucket; it changes nothing on Railway. If there is no stamp, the data never left the old machine: that is a blocker, so tell me.
5. **The Railway CLI** is used only for the bucket credentials, with the isolated-home and workspace-token pattern in handoff section 2. Never log in or out of any existing Railway account on this machine.
6. **The two OpenRouter keys' remaining limits:** call `https://openrouter.ai/api/v1/key` with each key and print only the numbers (`research/working-copy-2026-10-19/scripts/keys.sh` does this). Compare them with the budget the remaining paid work needs, from handoff section 6.
7. **The test suite** passes on `main`, with both database suites run against a throwaway container (`research/working-copy-2026-10-19/scripts/dbtest.sh`, paths adjusted to this machine). Read pytest's own result line, not a piped exit code.
8. **Helper scripts** in `research/working-copy-2026-10-19/scripts/` hard-code the old machine's paths (`/Users/kenilshah/Desktop/Wedding_industy_ads/...`). Make local copies with this machine's paths, outside the repo.

## Stage 3: do the work (only once Stage 2 shows no blocker)

Follow handoff sections 4 and 6:

1. Finish 2.B11/E.B12 from the restored v2 backfill: retry failed jobs, `moments report`, recall against the golden scenes, read 10 documents yourself, and decide the default.
2. Review, test and put the wave-1 branches on `main`; finish E.X7; benchmark knowledge-base version 6.
3. Then E.B3's judge, E.B26, E.B25 (c)–(f), L.B9, L.B11, E.B23 and S.B8, budget permitting, then the plan bookkeeping.

Keep to every rule in handoff section 2. In particular:
- you make all judgment calls yourself;
- push completed work straight to `main`;
- use the internal key first;
- never run E.B13;
- make no production or Railway changes;
- never commit `backend/docs/Implementation-Prompts.md` or a secret.

After each item is pushed, update its plan row. At the end, give me a short list of what is done and pushed, what is left, and why.

---
