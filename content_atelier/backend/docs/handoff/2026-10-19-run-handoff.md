# Handoff: completing Phases S, E, L, 0, 1 and 2 (19 October 2026, evening)

The owner's machine ran out of usage partway through. This packet holds everything the next session needs. Read it whole before acting. Its prompt is `2026-10-19-next-session-prompt.md`.

## 1. The task

> "Now that you have grounded yourself in what we are doing here, and we have brought in the data that was on jainil's machine, this should unblock all the pending items from phase S,E,L, 0-2 and complete our implementation of these phases. … use the internal [OpenRouter key] first and if it is exhausted move over to the client key … do not run the 4$ held out run … Additionally, I have given you the fathom api key as well."

The plan is `backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md`. Each row's bold status says what remains, and its last cell is the done-when.

## 2. Standing rules (the owner's, 19 October)

- **Judgment calls are yours.** Every review the plan gives to "a person" is done by the engineer, fully: golden scenes, pilot reading, classification disagreements, labels, approvals under D12. This is recorded as plan row D21. WIA has given full approval. Whitney sees only the end product, and no human review is expected.
- **Git:** when something is complete, commit and push directly to `main`, with no PRs and no merges. End every commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (or the attribution your harness gives).
- **Never commit:**
  - `backend/docs/Implementation-Prompts.md` (the owner's own edit; leave it modified and unstaged);
  - `backend/.env` or any secret;
  - the raw ChatGPT export.
  
  Client material goes only in `research/` and `backend/knowledge_base/`.
- **Keys:** use `OPENROUTER_API_KEY_INTERNAL` first and `OPENROUTER_API_KEY_CLIENT` when it runs out. Pass the key as `OPENROUTER_API_KEY` (and `EMBEDDING_API_KEY`) per command; `scripts/aw.sh` does this with `AW_KEY=internal|client`. Never edit `backend/.env` or `~/.zshrc` without asking. Never print a secret.
- **Never run E.B13's held-out run** (about USD 4; no budget). Week 6 stays untouched.
- **Production is out of scope:** no change to any Railway service, variable or deployment. Railway is used only to move this handoff's data (transfer bucket).
- **Privacy:** no privacy theatre. The owner handles OpenRouter privacy settings later.
- **Real-corpus processing** runs on a local working copy (plan row D20). Production is later restored from it, not re-run.
- **Railway CLI:** on the original machine, the global login (ai@foxandowlmarketing.com) must never be touched. WIA work uses a workspace token, stored in `backend/.env` as `RAILWAY_TOKEN`, with an isolated home:
  ```
  HOME="$HOME/.railway-wia-home" RAILWAY_API_TOKEN=<token> RAILWAY_PROJECT_ID=3409333b-1844-456c-93f9-f572ba92eb92 \
    RAILWAY_ENVIRONMENT_ID=28239d73-fe52-4d23-bf80-94a8064c5eb5 env -u RAILWAY_TOKEN railway <cmd>
  ```
  Workspace tokens fail `whoami`, `list` and `link`. `scripts/transfer/common.py` skips those when a token is set (commit `a6679e6`).
- **Fathom key** (in `.env`) is WIA's account: reading and pulling whatever is needed is allowed.

## 3. What is on `main` (this run)

| Commit | What |
|---|---|
| `71c4bef`…`5ac4afa` | S.B10, E.B12a, 0.B4, S.B4, S.X1, 2.B10 done; S.B14 closed; D15, D17 and D18 answered; D20 and D21 recorded; replay checker; `research/restore-checks-2026-10-19/` |
| `15925ac` | 1.B4, 1.B11: four real-archive normalisation fixes (staff with their own email domain; offer-demo calls are prospect calls; a person's exclusion reason; an event fitting several documents dates none) |
| `40d98e1` | E.B12, 2.B11: **rebind rule.** A scene quote found verbatim in exactly one turn is re-anchored there (`unique-verbatim-turn.v1`); the model had cited turn timestamps as references. Golden scenes v1: `research/golden-scenes/benchmark-v1-scenes.json` |
| `0953388`, `22a9184` | E.B6: `matching.duplicate` = 0.86 from 4,152 labelled pairs (`research/duplicate-labels-2026-10-19/`) |
| `82d0f9c` | 0.B5: `guard()` locks the run before the job (a deadlock between two workers of one run); plan rows S.B5, 1.B6 and E.B6 marked Done |
| this commit | this packet; `research/working-copy-2026-10-19/` (helper tools, scripts, decisions, reports) |

Full suite at `82d0f9c`: **1341 passed, 6 skipped**. Run it with `research/working-copy-2026-10-19/scripts/dbtest.sh`, adjusting the paths. **Read pytest's own result line.** A `| tail` hides pytest's exit code, and that once let a failing commit through.

## 4. Branches to review, test and put on `main` (not yet merged)

Two background agents worked in git worktrees. They were stopped for the handoff and their work pushed as branches:

1. **`handoff/wave1-0B8-LB10-EB17`**: **merged to `main` on 19 October evening** (`a44f656`, `1d9d417`, `5d16cea`, after review and a full suite run; plan rows marked Done). Nothing left to do. For the record:
   - `77e3f4e` **0.B8, S.B8:** the SQL weekly path scores with the matching settings it froze, and every registered setting is read; the S.B8 documented-variables test blind spot is closed.
   - `f8f5255` **E.B17:** Week 5 is held out like Week 6, and no published knowledge-base version states its material.
   - `b6ce7ab` **L.B10:** a cycle whose content plan is older than 30 days says so in its week summary; a new monthly entry clears it.

2. **`handoff/wave1-EB11-EX7-wip`**:
   - `33e2f6a` **E.B11 (3):** the legacy profile's version 2 sends the Reel scripts in the system prompt, never beside the evidence.
   - `31352d4` **E.B11 (1), (2), (4):** rule categories reviewed and required at compile; the patterns file is derived from the compiled version; no client figure outside cleared material. This produces **knowledge base version 6, pending its benchmark.** The benchmark is paid (about USD 0.6, three samples per week on benchmark v1, like E.B25's). Run it against version 5; if there is no regression, approve version 6, pin it and commit.
   - `c788205` **WIP E.X7** (stopped mid-way, untested): `gates/rubric.py` (rubric 2.3a text and version `rubric-2.3a.v1`), rubric ratings in the Gate 1 decision API, the review form in `CardReview.tsx`, and regenerated `openapi.json` and `schema.d.ts`. The agent's last note was "add a DB test at the end of the file" (`test_gate_one_decisions_db.py`). Finish it, run the full suite and the frontend checks, then put it on `main`.

## 5. The local working copy (database `atelier_work`, artifact root `atelier-work/artifacts`)

The working copy is Jainil's restored data plus this run's real-corpus work. It travels through Railway (section 8). It holds:

- **Documents:** 16 people synced; normalised with the Luna classifier (USD 0.025). 49 delegated classification decisions applied (`decisions-1b4.tsv`), leaving 91 included documents. Dates come from the Fathom calendar (`fathom-calendar-2026.csv`): 5 included documents dated, 86 explicitly undated.
- **Chunks:** every included document has segmentation v2 chunks with vectors (1.B6).
- **Moments:**
  - Weeks 1 and 2: v1 weekly moments, imported (2.B10 / E.B12a).
  - Scene profile **v1** (`2026-10-18.scenes.v1`): the 11 golden documents (the pilot, run `docext_feef5f54c4e17d8289aa2321`), re-partitioned under the rebind rule (184 verified, 16 unverified), plus 34 documents from a backfill I stopped on finding that the default is v2 (run `docext_23307dfbf100ad9c5b708706`; its other 46 jobs are marked failed as "Superseded").
  - Scene profile **v2** (`2026-10-19.scenes.v2`, the default): **the backfill of all 91 documents**, run `docext_665ba0687c44bfa2d90d57c0`, plan `plan_141a5c5617d741f6960d` (cap USD 1.30). Its state at handoff is in section 6.
- **Settings rows** in the working copy: `models.default` and `models.moment_extraction` are set explicitly to `openai/gpt-6-luna`. Live mode refuses code defaults.

## 6. Where each item stands

### Done in this run (on `main`; "local" means on the working copy under D20)

- S.B10, S.B4, S.X1, S.B5 (local), 0.B4, 2.B10, E.B12a, 1.B4 (local), 1.B11 (local), 1.B6 (local), E.B6.
- S.B14 is closed.

### In progress

**2.B11 / E.B12, the v2 backfill.** The state at handoff, and what to do next, is recorded in section 9 (written at the last moment). Then:

1. Retry any failed v2 job: `moments extract --all-pending --profile 2026-10-19.scenes.v2 --mode live --retry-failed` under the plan. A failed job usually has its response saved, so it replays at no cost. One job failed on the deadlock that `82d0f9c` fixes.
2. Run `moments report` (verified-quote share, role distribution, repairs) and `moments recall --golden research/golden-scenes/benchmark-v1-scenes.json` (v2 against v1 and weekly v3).
3. Read 10 v2 documents yourself; that is the "pilot read by a person" for v2.
4. Write the numbers into 2.B11 and E.B12.

Measured so far, with strict recall where the anchor phrase must be quoted:

| Profile | Recall | Coverage |
|---|---|---|
| weekly v3 | 8/15 | Weeks 1–2 documents only |
| scenes v1 | 11/15 overall | 7/10 on the Weeks 1–2 scenes |

On scenes v1:
- g07 (buying research) and g09 (clicks without conversions) **are** extracted, but anchored on another turn of the same scene.
- g01 failed on a quote stitched across two turns.
- g14 is absent.

E.B12's done-when is "scene recall on golden scenes at least the current prompt's (weekly v3)". Decide the weekly default switch (`prompts.profile.extraction`, whose choices are only weekly v3 and scenes v1) from v2's numbers. The row recommends a v3 scene profile, measured by recall: prefer WIA's line as the quote, anchor both turns, and challenge or reframe moves.

### Pending, in a sensible order

| Item | What remains | Paid? |
|---|---|---|
| E.B11 branch | Section 4 (branch A is merged) | KB v6 benchmark ≈ USD 0.6 |
| E.X7 | Finish the WIP (section 4) | – |
| E.B3 | The calibrated pairwise judge: randomised order, rubric 2.3a scoring (import E.X7's rubric), agreement with dispositions and rank, the regression cases under the E.B3 table | calibration ≈ USD 0.2 |
| E.B26 | Strategist profile v6, the verifier and the writer accept a WIA person's first-person observation as attributed experience; ATTRACT may challenge an idea; pillar mix. Smoke against v5 on benchmark v1 (Week 2's buying-research and clicks scenes) | ≈ USD 0.6 |
| E.B25 (c)–(f) | Knowledge-base hygiene, after E.B11's version 6: (c) superseded lines in documents 01–03; (d) the prefix within 30,000 tokens, measured slim against full (two samples per arm, calibrated judge); (e) the editing guide if (d) shows it helps; (f) twelve months of published central points (from the export's published log; derived material is in `research/chatgpt-export-2026-10-18/`) | ≈ USD 0.6–1.2 |
| E.B23 | Brief contract v3 (section 1.9.2): a claims ledger after writing, `evidence_ids` dropped from Reels, slides and the email, an optional `IntendedShift.do`, a caption `body`, narrower repair. Done-when on the live week's cards | ≈ USD 1 |
| S.B8 | A container from the documented variables replays an E.B23 brief end to end (the v1 briefs no longer replay: S.B4 changed the prompt) | – |
| E.B2 | Week 5 labels wait for E.X3 (Whitney's live review; not this run). **Funktastic chain: blocked.** Its published pieces exist only in Command Center's production database; nothing local holds them (searched the extra corpus). Reading production needs the owner's word | – |
| E.B11 / E.X7 | Section 4 | – |
| L.B9 | Published-content capture: paste the final against an approved brief → a `published_content` row, the difference as an authored edit for L.B6, metrics as performance | – |
| L.B11 | Self-maintaining context: a standing run plan plus a scheduled benchmark of a waiting knowledge-base version, a multi-week support window, catch-up mining, a notice on the cycle | small |
| Plan bookkeeping | Update every row touched (2.B11, E.B12, E.B2, E.B11, E.X7, 0.B8, L.B10, E.B17, …), the status table, and Appendices G and H | – |

**Budget at handoff:** the internal key had USD 3.92 left (it resets weekly) and the client key USD 1.51. This run spent about USD 1.10, mostly on extraction. The paid work above totals about USD 3–3.6, so drop E.B23 (and with it S.B8) first if money runs short.

## 7. Operational gotchas learned here

- **Live extraction needs all of:**
  - `CONTENT_ATELIER_LIVE=true`
  - `ATELIER_ALLOW_GENERATION=true`
  - `CONTENT_ATELIER_LLM_COMPLETION_TOKENS=24000` (live requests need an explicit output cap)
  - `ATELIER_RUN_PLAN_ID=<plan>`
  - a key (`AW_KEY=internal`)
  - models set explicitly in settings (`storage_cli settings set --actor <you> models.moment_extraction openai/gpt-6-luna`, and `models.default`)
  - the public route snapshot in the artifact store (`python -m backend_pipeline.token_budget --store --model openai/gpt-6-luna`, and the same for `openai/gpt-6.1-sol`; free, sends no data)
- **Run plans name the call stage**, not the job stage: `embedding` for chunk and card vectors, `moment_extraction` for scenes. Bind the plan to the estimate's `input_set_hash` (or `'*'`).
- **Encoding** also needs `ATELIER_ALLOW_ENCODING=true`.
- **Workers:** `python -m backend_pipeline.jobs worker` needs Redis. Use `storage_cli worker --max-jobs N` instead; it reads Postgres with `SKIP LOCKED` and is safe to run several at once (8 ran fine after the deadlock fix). **Never run an inline `--now` extraction while workers run:** it claims other runs' jobs under the wrong plan.
- **Re-partitioning saved responses under a new rule:** a replayed job reuses current rows with the same extraction key. Set those rows `is_current=false`, mark the jobs failed, then `--mode cached --retry-failed`; that makes no provider call.
- **Throughput:** Luna takes 2–4 minutes per long call. The estimate (`--estimate`) understates real cost by about 2× (about USD 0.01 per document for v2).
- **`python -m backend_pipeline.artifacts`** works since `a6679e6`.

## 8. Moving the working copy (Railway transfer bucket)

This follows `Data-Handover-Runbook.md`. The stamp and contents are recorded in section 9 once the upload finishes. If section 9 has no stamp, the upload did not finish; the data is still only on the original machine (the `atelier-test-pg` container, database `atelier_work`, and `Desktop/Wedding_industy_ads/atelier-work/artifacts`).

To restore on the new machine:

```bash
cd WIA-Content-Atelier/backend
python scripts/transfer/fetch_and_verify.py list
python scripts/transfer/fetch_and_verify.py download --stamp <stamp> --to ../handover-<stamp>
```

Credentials: with a workspace token, read `railway bucket credentials --bucket transfer-inbox --json` (isolated-home pattern, section 2) and pass `TRANSFER_S3_*`.

Then:

1. Restore `db/atelier_work.dump` into a long-lived pgvector container (`pgvector/pgvector:0.8.2-pg17`, a named volume, no `--rm`; never the throwaway test container).
2. Run `storage_cli migrate`.
3. Copy the artifacts into the folder `ATELIER_ARTIFACT_ROOT` names.
4. Jainil's original handover (stamp `2026-10-19`) may still be in the bucket too; it is not needed if `atelier_work` arrives.

## 9. State at the moment of handoff (19 October, about 21:30 IST)

- **The v2 backfill is finished.** All 91 included documents are extracted on `2026-10-19.scenes.v2` (run `docext_665ba0687c44bfa2d90d57c0`; 91 calls, USD 0.94; the plan is closed). From `moments report --extractor 2026-10-19.scenes.v2`:
  - 1,669 scenes; 1,569 verified (**94.0%**) and 100 unverified records.
  - 82 quote repairs; 31 scenes failed the number check.
  - Roles: client 645, staff 556, prospect 364, outside 4.
  - No included document has zero scenes, and every invariant holds.
- **Golden-scene recall** (strict, updated after the handoff on the same evening): **v2 14/15 (0.93)**, v1 11/15, weekly v3 8/15. On the Weeks 1–2 scenes, v2 scores 9/10 against weekly v3's 8/10, which meets E.B12's done-when. Only g04 is missed, and **none is lost to a quote mismatch**.
  - g15 had been lost because the model capitalised a mid-sentence "and". `repair_quote` now lets the first word's case differ (commit after `7e48271`). Its document was re-partitioned from the saved response, with no call.
  - Reports: `research/working-copy-2026-10-19/reports/recall-golden-v2.json` and `moments-report-v2.json`.
  - **Restore stamp `kenil-2026-10-19b`**, uploaded after this re-partition. The older `kenil-2026-10-19` predates it; ignore it.
- **2.B11 and E.B12 plan rows are updated.** Still to do:
  - a person's read of 10 v2 documents (D21);
  - **the E.B12 default switch, which is code, not a setting.** The weekly path's scene branch (`sql_pipeline.scenes`) is hard-wired to v1, and `prompts.profile.extraction` offers only weekly v3 and v1. v1 does not reach weekly v3 on the comparable scenes; v2 does. Wire the weekly cycle to the per-document v2 extraction (2.B2's job, with its partition and repairs), then make it the default.
- **Nothing is running.** No workers, no agents, all run plans closed. The two agents' throwaway containers are stopped.
- **Keys:** internal USD 3.62 left (weekly reset), client USD 1.51. This run spent about USD 1.36 in all.
- **Working-copy row counts** (`atelier_work`): transcripts 170, transcript_chunks 5,163, key_moments 2,442, pipeline_jobs 294, content_angles 13.
- **Railway transfer:** stamp **`kenil-2026-10-19b`** in the `transfer-inbox` bucket (the earlier `kenil-2026-10-19` is superseded). It holds the database `atelier_work`, the artifacts (7,495 files, about 497 MB) and `extra-working-reports`. If `fetch_and_verify.py list` does not show it as `complete`, the upload did not finish, and the data is still only on the original machine.
