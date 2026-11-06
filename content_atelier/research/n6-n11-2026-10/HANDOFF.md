# Handoff: Phases N6, N10, N7 and N11 (paused 25 October 2026, about 16:30 UTC; resumed about 16:35 UTC)

## Progress after the resume (kept current; read this first)

**Complete (25 October, about 23:00 UTC).** Everything in `TASK.md` is done and on production: `main` at `ad95ab5` (PRs
#28 to #33), every service deployed. N6, N10, N7 and N11 built; the benchmark and E.X8 on copy D; last week regenerated on
production with two packs ready to publish; three drills passed; the screens realigned with the 20 October mockup
(desktop); production on the Client key (USD 4.20 left; the internal key untouched); standing caps USD 4.20 a week; the
first scheduled run is **Sunday 1 November 2026, 04:00 America/Chicago**. Records: `README.md` (benchmark, production,
drills, the screens), DEPLOYMENT.md, the runbook, plan revision 8.13. No proxy left open; the local copy of production's
variables deleted.

**Open, by design:** X.1 (personal accounts) stays the owner's; raise the standing caps when the team develops on a funded
key (DEPLOYMENT.md); `features.calendar` stays off until something schedules pack pieces.

---

Paused on the owner's instruction before a context summary. Everything that runs was stopped; nothing is lost. Read
`DECISIONS.md` first (the owner's decisions of 25 October, the run's scope of record), then this file.

## Where the code is

- **Main checkout** `WIA-Content-Atelier`, branch `phase/n6-reliability` (not pushed), commits `78ce473` to `7837290` on top
  of `main` `a570276`. All backend tests touched pass; ruff clean. Built here:
  - N6: `alerts.py` + migration `011_alerts.sql` (+ catalogue) + scheduler scan + `GET/POST /storage/alerts`; `backup.py`
    `nightly` (the monthly restore check by itself, results in `settings`); E.B24's warnings decided (`first_touch.py`,
    `asset_checks.py`, `EB24-decisions.md`).
  - Autonomy (N10): second recordings linked (`documents/duplicates.py`), accounts added from a client call's title
    (`identities.provisional_account`, wired in `documents/jobs.py`), private matters excluded (`classify-rules-v4`), hourly
    `upkeep.py` (extracts never-extracted documents only, `extraction_status='pending'`; embeds new scenes, skipped while an
    extraction runs), tone changes released by the approver (`context.release.benchmark_required`, false in production),
    offer statuses set in the app (`offers.status`, `cycle/strategy_brief.with_changes`), week archiving
    (`week_archive.py`, `storage_cli weeks archive|restore`, `GET /weeks` hides archived).
  - N7: `cycle/schedule.py` (Sunday 04:00 Chicago from 2026-11-01: backfill the window, activate the collector once, start the
    cycle under `cycle.schedule.actor`; review document after the cycle), settings `cycle.weekday` default 6,
    `cycle.schedule.*`; `GET /storage/schedule`.
  - N10 routes: `GET /storage/summary` (`summary.py`, Home), `GET /storage/weeks/{id}/measures` (6.B13 monitoring in
    `week_measures.py`); `backend/docs/Operations-Runbook.md` (6.B9); DEPLOYMENT.md partly updated (6.X3).
  - N11: strategist v9 (`angle_generation.wia_strategist_v9.md`, registered everywhere v8 is), now in
    `deploy/production-settings.json` with the schedule and release keys.
- **Command Center**: PR #5 (6.C1, 6.C2, 6.C4) merged at `c2b2631` and **deployed (SUCCESS)**.
- **Backend subagent** (stopped; resume with SendMessage to `a3e8a42816b44d747`), worktree `atelier-np-a`, branch
  `n10/backend-pieces`: `fa71f91` 5.B14 .docx (template in the image), `062bf93` 6.B12 `clients remove`, `56582ef` 6.B7
  `GET /storage/costs` + `storage_cli costs`, `e1784d9` 6.B8 legacy `/runs` removed. Its tree is clean; it was re-checking the
  generated OpenAPI types. Test DB for it: `atelier-test-pg-b` (port 25452, user `atelier`, password `atelier_ci_only`).
- **Frontend subagent A** (stopped; resume with SendMessage to `ae37ac3c307689df6`), worktree `atelier-np-b`, branch
  `n10/frontend-a`: no commits yet; **uncommitted** accessibility work (6.F6) in 13 components plus
  `components/shared/a11y.tsx` and `components/accessibility.test.tsx`. Its other items (6.F3/6.F4 mock out of the backend
  build, 6.F8, 6.F7 settings view, 7.F1 fixes, 6.X2) are not started or not committed.
- **Frontend batch B** is written but not launched: `scratchpad/n6/frontend_b_brief.md` (6.F2 Home, 6.F5 alerts and costs,
  Next run from `/schedule`, monitoring and .docx on the cycle panel, archived weeks toggle, 6.X5, 6.X1 Playwright). Launch it
  on a branch `n10/frontend-b` cut from the integration branch after A and the backend agent are merged in (at most two
  subagents at once).

## To finish (in order)

1. Resume the two subagents (or finish their work by hand); review; merge `n10/backend-pieces` and `n10/frontend-a` into
   `phase/n6-reliability` (expect small conflicts in `storage_cli.py`, `storage_api.py`, `cycle/api.py`, DEPLOYMENT.md).
   Then make `cycle/schedule.review_documents` call the backend agent's .docx renderer (it looks for
   `review_document.render_docx(text, week_id=...)` by `getattr`; match the real function name and add it to the test).
2. Launch frontend batch B; merge it.
3. Full local CI (hosted CI is blocked by GitHub billing): backend suite with
   `ATELIER_TEST_DATABASE_URL=postgresql://atelier:atelier_ci_only@127.0.0.1:25458/atelier_test` (~27 min, background),
   `ruff`, schema catalogue check, OpenAPI drift; frontend lint, unit, server, both builds, types drift, Playwright.
4. PR from `phase/n6-reliability`, merge (self-merge authorised), approve the newest deployment of each backend service (api
   first, so migration 011 runs) and the Frontend (`scratchpad/n8/deps.sh` lists them; `railway api 'mutation {
   deploymentApprove(id: "...") }'`).
5. Production (temporary TCP proxy: `railway tcp-proxy create --port 5432 --service Postgres --json`, then
   `railway variables --service api --json | python scratchpad/n8/prod_env.py <host> <port> scratchpad/n6/prod.env`, then
   `bash scratchpad/n6/prod.sh <storage_cli args>`; delete the proxy and `prod.env` afterwards):
   - `settings apply --file deploy/production-settings.json --actor ai@weddingindustryads.com` (`--dry-run` first): strategist
     v9, the schedule keys, `context.release.benchmark_required` false.
   - `railway variables --service intake-worker --set ATELIER_ALLOW_INTAKE_ENCODING=true` (the collector's chunk embeddings).
   - Caps for the week of 26 October (key USD 15): e.g. cycle 1.5, briefs 5, refreshes 2, packs 4.5, extraction 0.6, embedding
     0.1, context mining 0.1; leave room for Sunday 1 November's run, which falls in the same OpenRouter week.
   - Archive `week_2026-06-01` and `week_2026-06-08` (diagnostics WIA rated 1 of 5).
   - **After 00:00 UTC Monday 26 October** (internal key renews; it has USD 0.74 now): regenerate last week, the calls of
     Sunday 18 to Saturday 24 October (Chicago): all are already documents (8 calls: four internal on 19 Oct, LeadLock sync
     and a prospect consult on 21 Oct, a new client's kickoff on 22 Oct, a client strategy call on 23 Oct; the tax call is
     excluded). Start the cycle through the API (proxy on `api` port 8000, `research/packs-2026-10/np5/api.py`), read the
     cards, develop the best (delegated Gate 1, `research/n6-n11-2026-10/gate1.py`), Gate 2 (`np5/gate2.py` with an actions
     file; a refresh is `POST /briefs/{id}/revise` mode live), approve, read the packs; then archive `week_2026-10-20`.
   - Drills (6.X4) during that work: flush Redis while jobs are queued; restart `editorial-worker` mid-brief; a budget cap set
     below the next call (refusal, alert, release). There is no web provider wired (`briefs/external.py` is unused): record N/A.
   - Check the alerts screen/API, `/summary`, `/schedule` (next run Sunday 1 November 04:00 Chicago), the hourly upkeep
     (production has 5 included documents never extracted and no scene embedded: the first passes extract and embed them,
     about USD 0.1).
6. Visual pass of every screen at 1440 and 375 px on the local stack with production data (dev Command Center
   `atelier-cc-dev`, any address signs in locally; never a password on production), fix what looks wrong.
7. Records: `README.md` here (production results, drills, E.X8), the plan doc (revision 8.13: status table, 5.0a/5.0b rows,
   M6, Appendix D), DEPLOYMENT.md "What is deployed today", memory. Offer the owner a check on Sunday 1 November.

## The benchmark (copy D, Client key) — where it stopped

- Done: Week 1 cycle (strategist v8, `week_2026-05-31`), Week 2 cycle (v9, `week_2026-06-10`, run
  `run_48c63094ca784feab03325f2ed3c99ca`), readings in `README.md`; scenes embedded (2.B11 measured); E.B18 measured.
- Developed at Gate 1: `angle_e433d15abd5303981d557ef8` (keyword research, WARM) → **brief `brief_2281b5362b934922f063e626`
  written, waiting for Gate 2**; `angle_12a3131518bd475997b0d47f548fa2f5` (post-tour follow-up, CONVERT, point reframed at
  Gate 1) → brief run `brief_run_b9a88757c1aa7151214f8bf8` **interrupted at brief_writing** (restarting the workers lets the
  reconcile pass run it again).
- Next: read both briefs against section 4.3 and WIA's notes; at most one refresh each (budget); approve through `gate2.py`;
  read both packs (first-touch rules, W2 to W8, sibling repetition, register, CTAs); E.X8 = a mixed, unlabelled reading of the
  pack pieces beside Whitney's finished pieces (`backend/knowledge_base/15-exemplars.md`, `19-transformations.md`). A failure
  becomes a new prompt version (writer v5.3 or `pack_finish.v3`), never an edit of a released one, and one re-test.
- Budget: Client key **USD 11.99 left** (USD 4.18 spent in this run); the benchmark's share was about USD 6, so finish it with
  the two packs and at most one refresh; internal key USD 0.74 until Monday's renewal, then USD 15.
- To restart copy D's stack: from `backend/`, `SHAKEDOWN_OPENROUTER_KEY` = the Client key from `.env` (never printed),
  `STACK_DATABASE_URL=postgresql://atelier:atelier_local_only@postgres:5432/atelier_np_d`,
  `SHAKEDOWN_ARTIFACTS_DIR=../../atelier-work/np-artifacts-d`, then
  `docker compose -p atelier-shakedown -f compose.yml -f ../research/packs-2026-10/np5/compose.np5.yml up -d --build api scheduler editorial-worker bulk-worker intake-worker`
  (rebuild: the stopped images predate the upkeep fix) and `docker start atelier-cc-dev atelier-shakedown-frontend-1` for the
  screens. Copy D's caps were raised for the benchmark (cycle 6, briefs 20, refreshes 20, packs 20, embedding 2); copy only.
- Copy D incident, handled: the first upkeep build queued 136 extractions (it judged "new" by ingestion date, but the whole
  archive was ingested in October); they were cancelled before running and the rule changed to never-extracted documents.

## Stopped and cleaned

Both subagents and every background waiter stopped; the scratch stack's app containers stopped (databases left up); the
production TCP proxy deleted and the local copy of production's variables removed. Nothing was pushed except Command Center
PR #5.
