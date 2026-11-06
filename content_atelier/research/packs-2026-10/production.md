# NP-6: content packs on production (24 October 2026)

This is the content-packs plan's NP-6, done unattended with the owner's go-ahead: deploy anything on production except a
Railway billing change; USD 6 of OpenRouter for the phase. WIA's reviews were done under delegation (D12, R55). Times
are UTC.

## Steps

| Step | What was done | Result |
| --- | --- | --- |
| 1. Variables | `ATELIER_ALLOW_PACK_GENERATION=true` on `api` and `editorial-worker`, set with `--skip-deploys` so it arrived with the merge's deployments. `ATELIER_ALLOW_GENERATION` was already `true` | Both services carry it |
| 2. A fresh dump | `backend_pipeline.backup dump` through a temporary TCP proxy on `postgres`, run in the backend image (PostgreSQL 17 client), before migration 009 could run | `backups/db/atelier-20261024T152922Z.dump`: 50.6 MB, 41 tables, 12,632 rows, migration 008, snapshot `00000052-000004DD-1` |
| 3. Merge | PR #17 (Phase NP, NP-1 to NP-5) merged after all five CI jobs passed | `main` at `f1576d0` |
| 4. Deployments | The newest deployment of each service was checked to be `f1576d0` and approved: `api` first (its pre-deploy `storage_cli migrate` ran 009 at 15:37:37), then `scheduler`, `editorial-worker`, `bulk-worker`, `intake-worker`, `db-backup` and Frontend. Older deployments waiting since 11:18 and 11:29 (`bf80ed0`, `78c9add`) were left unapproved | All seven on `f1576d0`, `SUCCESS`; the API healthy |
| 5. Settings and budget | `settings apply --file backend/deploy/production-settings.json` (`features.packs` on, the pack models, efforts and profiles); `budgets set --purpose packs --weekly-usd 6.00 --weekly-calls 60` (D43f) | A diff of every settings row against scratch copy B showed only the budgets and the pack profiles differing |
| 6. Saved answers | Copy B's `pack-cache` and `pack-attempts` (92 files) copied into the `artifacts` bucket with `backend_pipeline.artifacts copy` (never replace, every upload read back) | 92 copied, 0 skipped, 0 different, 0 failed |
| 7. Gate 2 | N2's three briefs went through Gate 2 with `np5/gate2.py` and exactly the proof's `np5/gate2-actions.json`, as the named team account under delegation, through the proxy. The pack runs were queued in replay mode: the local runner had no live switch, so a miss would wait and spend nothing | All three approved with the delegated label. Outputs: `np5/gate2-production-*.json`. Two problems and their fixes are below |
| 8. The packs replay | Brief 1's first replay missed. The fix (PR #18, `c381095`) was merged after green CI, and its six deployments approved after checking the commit (the Frontend's was skipped as unchanged). The runs were then retried and replaced (`np5/review-recreate-*.json`), and the three packs replayed | Briefs 1 and 2 and brief 3's first pack: 12 calls, all `replayed`, USD 0. Every piece, note and client quote is identical to the proof's (`np5/prodread.py`) |
| 9. Brief 3's Finish again | Profiles set to v2, then Finish again on brief 3 in live mode (`np5/review-finish-again.json`). The proof's v2 answers could not replay (the edited schema, below) | Live, USD 0.60 (finisher 0.51, check 0.09), 0 of 27 statements flagged. The stance Reel is labelled "written" |
| 10. The delegated review | `np5/review-production.json` (result `np5/review-production-result.json`), four edits, each a new version locking the line as the team's (D12, R55): the blind reading's two clauses (briefs 1 and 2's carousel captions), brief 1's stance caption (a planned review told as done), and brief 3's stance caption ("Only the client's team could", a certainty its check let through and copy B's check had repaired) | Three packs in review, no blocker: brief 1 `pack_b11090ba822c42aab5be8e6abc571d20`, brief 2 `pack_2795c2aa99c740bc86e40ed310531e91`, brief 3 `pack_d3247dee217649db8fd144db2c72ebab` |
| 11. The week | The week's listing and proposed plan (`production/week_2026-10-12.week.json`), and the week's document (`storage_cli pack-document`) | Publishing week 26 October to 1 November: Monday Instagram 1 (brief 1's story Reel), the Tuesday email (brief 1), Wednesday Instagram 2 (brief 2's carousel), Friday Instagram 3 (brief 1's stance Reel), a bank of 11, no week finding. The document is 80,580 characters (`production/week-2026-10-12-packs.md`) |
| 12. Clean-up | The TCP proxy was deleted, and the local file with production's credentials removed | No public address on `postgres` |

## Two problems, and what was fixed

**1. A docstring voided the saved answers (fixed by PR #18 at its cause, with a test).**
- **What happened:** brief 1's replay missed with "No compatible pack response is cached". The run's frozen contract
  showed different `schema_hashes` for `pack_finish` and `pack_check`.
- **Why:** a pydantic model's docstring is part of the stage's wire schema, and so part of the request that keys a saved
  answer. Registering the v2 profiles (`870064b`) had changed two of them ("pack_finish.v1" became "pack_finish.v1 and
  v2").
- **The fix:** PR #18 restored the two docstrings word for word, so the hashes equal the proof's v1 runs again. It also
  pins all four hashes in `test_the_pack_stages_wire_schemas_are_pinned_because_a_saved_answer_replays_only_under_its_schema`.
- **What it cost:** the proof's v2 answers (brief 3's Finish again, the held-out pack) had been saved under the edited
  schema, so brief 3's Finish again ran live on production (USD 0.60). That also proved production's live pack path end
  to end.

**2. A repeated sentence in brief 2 (fixed in the runner, and corrected under D12).**
- **What happened:** over the proxy, each Gate 2 step took 3 to 12 minutes, because each re-reads the evidence's
  transcripts. So the briefs were run side by side and restarted twice:
  - once to stop a run that had fallen back to default settings (the settings loader's 3-second connect timeout;
    `np5/remote.py` now gives connections 30 seconds and stops a run on that fallback);
  - once after brief 2's approval was refused because brief 1's approval had changed its related prior use. Copy B ran
    the briefs in order.
- **The defect:** brief 2's Reel-script edit has new text that contains its old text, and the runner's resume check
  re-applied it on each restart. The approved brief repeated one sentence three times.
- **The correction:** the team edited it back to the single sentence the proof approved (`np5/gate2-fix-brief2.json`),
  re-checked the claims and approved again. Its pack then replayed identical to the proof's.
- **The runner fix:** `gate2.py` now treats an edit as applied when its new text is present and either its old text is
  gone or the new text contains it.

## Cost

| Item | USD |
| --- | --- |
| Production's pack calls | 0.60: brief 3's Finish again, live. The other 12 calls replayed at 0 |
| **Phase NP total** (the internal key; the owner's limit USD 6) | **4.83**: the capped call 0.03, the held-out brief 1.30, the proof's five pack runs 2.90, production 0.60 |
| The Client key | 0 (the free-model shakedown only) |

No Railway billing change was made. The deployments, variables, the TCP proxy (created and deleted) and the settings are
the only production changes.

## Open

- **The screens' visual check on production.** It needs a WIA sign-in, and the agent enters no password. The screens are
  unit-tested, built by CI and deployed with `f1576d0`.
- **WIA's review of the three packs.** Each lists its before-publishing notes (the client's okay), the pack notes for
  Whitney (repeated locked wording, naming Carmen, the program name) and the blind reading's style suggestions
  (`np5/blind/verdicts.json`).
- **NP-7:**
  - the check's sources to include the approved brief's WIA perspective (`pack-check.v3`);
  - labelled check cases from the proof (NP.X5);
  - the .docx export;
  - the packs budget back to USD 3.50 a week from 2 November (D43f).
