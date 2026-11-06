# WIA Client Knowledge Base: handover (4 Nov 2026)

You're taking over the build of the **WIA Client Knowledge Base (KB)** from Jainil Trivedi (E2M, associate AI executor on the WIA account). This file covers what was done in the last working session (29 Oct to 4 Nov), where everything stands, the decisions you must not reopen, and what's left to finish the pipeline.

> **This file is outside the git repo on purpose.** It names real clients and internal setup. Don't copy it into `wia-knowledge-base/`, because that repo is pushed to GitHub.
>
> **Older context:** the chat export from 30 Oct is `Wedding_Industry_Ads/WIA-KB-chat_Jainil-Trivedi_2026-10-30_1930-IST.md`. It also lists every file referenced up to that point.

---

## 1. What the product is

**Wedding Industry Ads (WIA)** is an ad agency for wedding venues and vendors. E2M builds them an internal **Client Knowledge Base**. It pulls everything about each client from:
- Slack;
- ClickUp;
- Gmail, using the shared hello@ mailbox;
- Google Drive and Calendar;
- Fathom call recordings;
- GHL/LeadLock.

From that it builds per-client records, an action list (what WIA owes the client and what the client owes WIA), and later health, call prep and invoices.

**Phase 1 = Client Portfolio + Action Hub, live with real data.** "Action Hub" is the new name for the "Action Register".

The build is split into **14 stages**. The stage doc is a shared Claude doc: https://claude.ai/artifact/8aJMARZCsVH4i3bLHS47Cu

| Layer | Stages |
|---|---|
| A Ingestion | S1 source access, S2 client mapping, S3 people/roster, S4 ingestion engine, S5 production backfill, S6 live sync |
| B Knowledge | S7 extraction (AI), S8 action domain, S9 read models |
| C Backend | S10 login/visibility, S11 API, S12 outbound (ClickUp write-back, Slack notify) |
| D Frontend | S13 |
| E Launch | S14 |

**Where it stands:**
- S1–S4 are built.
- S5 has only been run locally, as a learning run.
- S6 code exists but nothing runs it.
- **S7–S11 are the main work left.**
- S12 has its guard built.
- S13 is the React UI, still on static and sample data.

---

## 2. Repo, branch, how to run

- **Repo:** `Wedding_Industry_Ads/knowledge_base/wia-knowledge-base/`
- **Current branch:** `mvp`. It was cut from `feat/ingestion-backend`, and Railway auto-deploys from it.
- **Last commit:** `1f63ef8`. **There's a large amount of uncommitted work** (see §11). Jainil commits by hand.

**Backend** (FastAPI, SQLAlchemy, Alembic, PostgreSQL 16 in Docker):
- **Always run Python from the repo root** (`python -m backend.…`). Running inside `backend/` lets the `backend/logging/` package shadow the standard-library `logging`.
- **Ports:** Postgres on `127.0.0.1:5440` (databases `kb` and `kb_test`), API on `8010`. Ports 5433, 5434, 8000 and 8001 are taken by other projects on this PC.
- **Database:** `docker compose -f backend/docker-compose.yml up -d`. Docker Desktop must be running; it has stopped several times.
- **Migrations:** `python -m alembic -c backend/alembic.ini upgrade head`. The head is `c06a20261102`.
- **Tests:** run this from the repo root. The default pytest temp folder is permission-blocked on this machine, so `--basetemp` must point at a writable folder.
  ```bash
  backend/.venv/Scripts/python -m pytest backend/tests -q --basetemp=<writable dir>
  ```
  200 pass, as of 2 Nov.
- **CLI:** `python -m backend.scripts.kb …`. It covers clients, discovery, mapping, backfill, `clickup …` and `outbound …`.
- **Queue:** PostgreSQL only, no Redis.
- **Secrets:** `backend/.env` is git-ignored, and `.env.example` documents every variable. **Never commit `.env` or anything in `backend/.local/`.**

**Frontend** (Vite + React 19, `frontend/src`):
- `npm run dev` serves on port 3001.
- `npm run typecheck`.
- `npm run export` builds the single-file `frontend/exports/client-portfolio.html` with sample data.
- `npm run export:live` writes **real finance data**. Never share or deploy that output, or any `*.local.json` or `-wia` export.

**Preview servers** are defined in `Wedding_Industry_Ads/.claude/launch.json`:
- `knowledge-base`: dev server on 3001;
- `kb-export`: serves the exports folder on 8091;
- `kb-mvp`: serves `mvp/` on 8092;
- `kb-real`: real-data review copy on 8093;
- `kb-api`: API on 8010.

---

## 3. Hard rules (agreed with Jainil and with WIA)

1. **Nothing reaches Slack or ClickUp unless an approver types `yes` for that exact request.** This is the outbound guard (§5). Don't approve requests yourself or automate the approval.
2. **Don't commit or push** unless Jainil asks. The repo is on GitHub, so keep personal emails, Slack IDs, ClickUp IDs and client contact details out of code, tests and docs. Tests use `*-example.com`.
3. **Raw Slack, ClickUp and Gmail pulls stay local**, under `backend/.local/` (git-ignored).
4. **Don't start a worker or resume the paused Gmail run** without Jainil's go-ahead.
5. **Keep `KB_SECRET_KEY` safe.** It encrypts each user's ClickUp token, and losing it means everyone reconnects.
6. **No CI.** Deploys and redeploys are manual. Run the tests by hand before each push (checklist in `backend/docs/production-readiness.md` §6).
7. **The production schema comes from one file**, `backend/sql/schema.sql`, applied once to the empty production database. After that, every change is a normal migration.
8. **The deployed MVP page is public with no login and shows real data** for 4 pilot clients. Treat it as sensitive, and don't add anything more to it without asking.

---

## 4. Stage by stage: what was done and what's left

### S1 Source access: done, except one item
- **Google:** an OAuth client in WIA's GCP project "Client Knowledge Base", **Internal** audience, so tokens don't expire. hello@ is the only connected mailbox; staff mailboxes are an accepted gap. Scopes: gmail.readonly, drive.readonly, calendar read-only.
- **Slack:** the existing **WIA AI BOT** app (formerly "Content Atelier"). Scopes are the 7 read scopes plus `users:read.email`, `chat:write`, `im:read` and `im:write`. No separate dev app. Pilot channels: dogwood, dospalomasranch, funktastic, theelia.
- **ClickUp read:** the existing personal API key of the E2M AI member account (`CLICKUP_TOKEN`).
- **ClickUp write-back is per user.** Each KB user connects their own ClickUp through **WIA's ClickUp OAuth app**, which Jainil created via the hello@ admin account with Gisselle's approval. Writes use that person's encrypted token, so ClickUp shows the real person. There is **no fallback**: an unconnected or expired user can't make ClickUp edits.
- **Connect flow (built):**
  - Production-style: the KB sends you to ClickUp, ClickUp redirects back to the API callback, then you're redirected back to the KB.
  - Endpoints in `backend/routes/clickup.py`, mounted at `/api/v1/clickup`. The callback is `/api/v1/clickup/oauth/callback`.
  - Signed HMAC state, valid 10 minutes. Tokens are Fernet-encrypted with `KB_SECRET_KEY`.
  - `KB_APP_URL` is the redirect target; locally it's `http://127.0.0.1:3001`.
  - CLI: `kb clickup connect|list|verify|disconnect`, with `--paste` and `--no-browser`.
  - The local CLI listener binds both IPv4 and IPv6 and uses a threaded server with a 5s handler timeout. That fixed two bugs: the browser hitting `::1`, and an idle browser preconnect stalling the flow for 3–4 minutes.
- **Credential register:** `knowledge_base/credential_register.md`, outside the repo. It says where each credential lives and never holds the secret values.
- **Still open:** **the ClickUp sandbox edit.** It waits for WIA to approve a sandbox list.
  1. Put that list's ID in `OUTBOUND_SANDBOX_CLICKUP_LISTS`.
  2. Draft an edit with `kb outbound draft-edit`.
  3. Jainil approves it.
  4. Send it.

  The Slack sandbox tests (a DM to Jainil, and a post to the testing channel) are done.

### S2 Client mapping: done
- One **command service**, `services/clients/mapping.py`, called by both the CLI and the future API.
  - Every command is audited and checks revisions.
  - Commands: add, archive, activate, scope-add, not-applicable, discover per client.
- **Admins map clients in the UI in production.** YAML (`backend/.local/clients.yaml`) is only a dev bootstrap.
- **Archiving a client pauses its sync.** Its scopes stop but keep their cursors. Shared-source records matching only that client aren't attached. Reactivating resumes from the cursors, and a requalify pass covers the gap. The code is `services/intake/scoping.py`.
- **Discovery:**
  - ClickUp reads the `CLICKUP_CLIENT_SPACES` setting and includes archived lists.
  - The window is `DISCOVERY_WINDOW_DAYS` (365), and the backfill window is env-configurable.
  - Contact filters drop subdomains of system and vendor domains, automated senders, team addresses and partners. Only direct correspondents qualify.
  - Before the filters, 137 of 201 contact suggestions were noise.
- **Sender rules** (migration `c03`) decide which automated mail still counts. Platform alerts are handled by rules, not by AI reading subject lines.
- **Mapping decisions:**
  - **Past clients:** 43 archived ones are not backfilled. Whether they belong in the KB at all is in the call file.
  - **Partners are never client contacts:** Tirzah is a partner linked to Dogwood, and Celebrate Creative is a web agency. hustleandgather.com is left out for now.
  - **Calendars:** Jacqueline's, Gisselle's and Tina's are approved.
  - **Excluded:** the DEJA Drive folder.
  - **Kept:** active clients' archived ClickUp lists, for history only.
- **11 mapping gaps remain.** Evergreen and SK have no contacts, and 3 clients have no Drive folder.

### S3 People / roster: done and verified
- Plan: `backend/docs/stage-3-people-roster-plan.md`. Validation: `backend/docs/people-roster-validation.md`.
- People are resolved across Slack, ClickUp, Google and Fathom (`services/people/resolve.py`). The roster is in `backend/.local/roster.yaml`.
- **Bots are classified as party `"bot"`:** a service account with `bot` in its functions. `"bot"` was added to the person functions list.
- WIA still has to sign off owners and roles.

### S4 Ingestion engine: built
Adapters exist for Slack, ClickUp, Gmail, Drive, Calendar and Fathom.

**Fixes from this period (in code, uncommitted):**
- **Drive misattribution:** the legacy pipeline filed records under the running scope. It now uses the batch memberships. The test is `test_drive_attribution.py`, and `scripts/repair_drive_associations.py` fixes data already stored.
- **Drive Sheets ranges:** a range containing `+` made every Drive call fail with a 400. Fixed.
- **Exporter:** it crashed on some calendar status strings. Fixed.
- **Gmail:** 403 rate limits were retried with backoff on 3 threads in the dev pull, outside the repo. The pipeline itself now handles them (BF-1, 4 Nov).

### S5 Production backfill: not started
- **The full-history backfill run so far was LOCAL DEV ONLY**, a learning run to discover extraction scenarios. It is not production data.
  - Drive full history is complete.
  - Gmail was stopped on purpose at about 55% of hello@ (roughly 34.6k messages), and the run is left paused in the dev database.
  - Funktastic's email before 27 Oct 2025 is missing.
- Pilot clients are **Dogwood Reserve, Dos Palomas Ranch, Funktastic/DJ Hybrid and The Elia**. The other 20 active clients are archived in dev. Whether to reactivate them for production is undecided.
- **Blockers BF-1 to BF-9 must close before any production backfill.** Full table in `backend/docs/production-readiness.md` §1.

  | # | Blocker | Status |
  |---|---|---|
  | BF-1 | Google rate limits as HTTP 403: read the error `reason`, retry `rateLimitExceeded`, deny only real permission errors | Done (uncommitted, 4 Nov): `shared/http.py` + `tests/services/test_http.py` |
  | BF-2 | **Email stored as a pointer, not a body** (decision below) | Storage done (uncommitted, 4 Nov): `gmail-v3` stores no body; `kb email <id>` reads it from Gmail. The AI step's fetch-and-quote part waits for S7 |
  | BF-3 | One Gmail query for every contact can exceed the URL limit: batch it and de-duplicate | Open |
  | BF-4 | Resume a stopped full-history run (the legacy `start_backfill` path restarts from scratch) | Partly done |
  | BF-5 | Parser-version fingerprint test | Partly done |
  | BF-6 | Dubsado / finance mail sender rule | Open |
  | BF-7 | Retention rule for Slack, Drive and Fathom text, plus WIA sign-off | Partly done |
  | BF-8 | Drive attribution | Done (uncommitted) |
  | BF-9 | Sheets range / calendar status | Done (uncommitted) |

### S6 Live sync: code exists, nothing runs it
- It needs a scheduler process on Railway that calls `sync.sweep`.
- Calendar has to use `syncToken`, because `updatedMin` only reaches back about 3 weeks.
- Target: 72 hours of running with p95 lag under 15 minutes.

### S7–S11: the main remaining build
- **S7 Extraction (AI):**
  - Runs over client threads, meetings and Slack **as a batch over everything since the last run, on an admin-set interval**.
  - Evidence quotes must be verified.
  - A 50-thread accuracy test happens while the system prompt is drafted.
  - The hand-written overlays used for the real-data MVP are the **gold set**: `backend/.local/raw_pull/real/overlay/*.json`, covering profile facts, meeting summaries, commitments, done-proofs and 14–18 milestones per client, every fact cited.
- **S8 Action model:**
  - Open → Done, plus Acknowledged. ClickUp's "in progress" is rarely used and is mirrored only where it's real.
  - Includes history, a review queue, commands, and ClickUp write-back through the guard.
- **S9 Read models:** the Portfolio and Action Hub cards read live tables, not the snapshot plus overlays.
- **S10 Login and visibility:** KB login, roles, account-team visibility, finance access, and the ClickUp Connect step.
- **S11 API:** client, action, review and coverage endpoints. Today only ops endpoints and ClickUp connect exist.
- **The input for designing S7–S9 is `docs/mvp-card-to-data-map.md`.** It maps every element of both tabs to its source (source data, extraction, or derived) and lists the extraction backlog and the open decisions.

### S12 Outbound: guard built (§5)
Still needed: wire Action Hub write-back and Slack notify through the guard.

### S13 Frontend: React is now the single source
See §6.

### Production infrastructure (Railway, manual deploys)
Nothing is created yet except the static MVP service. Still needed:
- **Production Postgres:** apply `schema.sql` once, turn on backups or point-in-time recovery, rehearse a restore.
- **Web (API) service:** the Dockerfile runs uvicorn; health checks are `/health/live` and `/health/ready`.
- **Worker service:** `python -m backend.workers.runner`.
- **Scheduler:** set `SYNC_SCHEDULER_ENABLED=true` only when live sync is ready.
- **Staging project:** set `OUTBOUND_MODE=off`.
- **Secrets:** move every value into Railway variables.
- **ClickUp OAuth app:** add the production redirect URL.

Details are in `production-readiness.md` §5 and §7.

---

## 5. Outbound guard: how it works

Jainil's requirement: **"I have to approve it before it does anything that makes changes to ClickUp or Slack."**

**Code:**
- `backend/services/outbound/`: `guard.py`, `requests.py`, `clickup_oauth.py`;
- models in `backend/models/db/outbound.py`: `ClickUpConnection` and `OutboundRequest`;
- migrations `c05a20261102` and `c06a20261102`;
- tests `test_outbound.py` and `test_clickup_oauth.py`.

**Settings:**
- `OUTBOUND_MODE`: `off`, `sandbox` or `live`. Locally it's `sandbox`; production stays `off` until it's deliberately changed.
- `OUTBOUND_KILL_SWITCH`.
- `OUTBOUND_APPROVERS=["jainil"]`.
- Sandbox allow-lists: the testing Slack channel, Jainil's own DM, and `OUTBOUND_SANDBOX_CLICKUP_LISTS` (empty until WIA approves a sandbox list).

**Lifecycle:**
1. **Draft:** `kb outbound draft-post`, `draft-dm` or `draft-edit`.
2. **Approve:** `kb outbound approve` needs an interactive terminal and a typed `yes`. The approval is tied to the payload hash and expires after 24 hours.
3. **Send:** `kb outbound send` sends exactly once.

Also available: `list`, `show`, `reject` and `status`.

**ClickUp edits are limited** to status, due date and assignees, use the person's own token, and never set "Closed".

**Open product question:** the MVP UI has a one-click "Ping on Slack" button, which conflicts with approving every send. The options are in `docs/mvp-card-to-data-map.md` §6.

---

## 6. Frontend: MVP vs React, and the port finished today

**Background:**
- `mvp/index.html` started as a copy of `npm run export` and was then **hand-edited** for review rounds. The 54 change notes are in `mvp/readme_changes.md`.
- `mvp/real_index.html` is the same UI with real data.
  - It's built by `backend/.local/raw_pull/scripts/build_real_index.py`, which layers `base.json` (from the exporter) with hand-written `overlay/*.json`.
  - It is **the deployed page**, at `knowledge-base-wia.up.railway.app`. Caddy serves it at `/` via `mvp/Caddyfile.template`.
  - The build strips the review toolbar. A review copy with the toolbar sits at `backend/.local/raw_pull/real/real_index.html`.
- Jainil's status: the **Action Hub design is final**; the **Client Portfolio is still being designed**, so treat it as provisional.

**Today: every MVP hand edit was ported into `frontend/src`** (uncommitted).

*App shell* (`App.tsx`, `components/Sidebar.tsx`, new `mvp.css` imported last in `main.tsx`):
- The default view is Clients.
- Old `#actions` and `#actions-v2` links redirect to `#actions-v3` (the Action Hub).
- Overview, Call Prep, Health, Client 360, Invoices, and a client's Health or Invoices tabs are blocked: they show a "Coming soon" toast and go back to the last allowed page.
- Workspace search and ⌘K are removed.
- The sidebar has a "Coming soon" section, and Foundation moved to the bottom.

*Action Hub* (`views/ActionsTeams.tsx`, plus the new `src/mvpActions.tsx`):
- Title with an ⓘ tooltip; KPI tooltips; the KPI label is now "Pending (you)".
- The filter bar keeps only Needs review.
- Cards show the client's initials, a hover tooltip (time left or late, and when the Slack ping was sent) and a Slack mark.
- **Drag and drop** between columns, or onto KPI tiles when only one column shows. Dropping on Pending (team) asks "Who should own it?".
- "Programme ops" is now "Internal", and Internal items open the full detail modal.

*Detail modal and Add action* (`views/Actions.tsx`):
- **Change status** menu: Pending (you), Pending (team) with the owner picker, Pending (client).
- **Ping on Slack** with a 2-minute cooldown. It's preview only and writes to the action's history.
- Source and ClickUp links removed from the header; one-line comment box.
- Internal items get their own badges and hint.
- Add action no longer has a Type field; new actions default to Admin.

*Portfolio* (`views/Clients.tsx`):
- Card menu: Open client record, Pin to top, Mark as archived. The **Archived** tab has an empty state.
- Pinned clients sort first.
- The client name is a link.
- The health pill is removed from cards and the list.

*Client record* (`views/ClientDetail.tsx`):
- **Tabs:** Now, Profile, Commitments, Meetings, History, Handover brief, Support, Health (Soon), Invoices (Soon), Attendance for accelerators, Sources.
- **Removed:** the cover health link and the engagement switch.
- **Now:** shows 3 action rows plus a "+N more" link; the Client sentiment card shows "Coming soon".
- **Profile:** the source-label legend is removed.
- **Commitments:** 10 per page, soonest due first.
- **History:** filter by period (All time, Month, Year, Custom range).
- **Handover brief:** a Regenerate button with a "Generated …" stamp.

*Elsewhere:*
- "Action Register" is renamed "Action Hub" in every string.
- `kbLive.ts` passes logo `scale` and `source` through.
- The fit-screen script is inline in `frontend/index.html`. At 1280–1919px wide it shrinks the 1920px layout and patches rect and pointer APIs. **Before scripted browser tests**, set `localStorage['wia-fit-screen-v1']='off'`.

**Verified:** a fresh `npm run export` matches `mvp/index.html`:
- visible text on 9 routes;
- DOM structure (every element and its classes) on 7 routes;
- 20 scripted interactions: pin and archive, status menu, owner picker, Slack ping, Internal modal, single-column view, history period, pagination, drag and drop.

`npm run typecheck` passes.

**Still to do in the frontend:**
- Archive, pin and the brief stamp are **per-browser `localStorage` for now**. In the backend, archiving is global and pauses sync; the map doc §6 covers the mismatch.
- **Not decided yet:** whether to rebuild `mvp/` from the React export. `mvp/real_index.html` is still built from `mvp/index.html`, so any rebuild must keep the real-data build working.
- **Later (S13):** wire the cards to the API once S9 and S11 exist.

---

## 7. Analyses done this period (inputs for S7 and S8)

All are in `kb_tab_scope/Action_Register_analysis.md` §8–§12 (untracked).

> **Before committing:** check these two `kb_tab_scope` files for real names or IDs. They were written from real pulls.

- **Slack and ClickUp patterns:** how requests arrive, how tasks are created, and the daily volumes. About 71% of hello@ is automated; client threads run at about 12 emails a day across 7–8 threads.
- **ClickUp usage:**
  - Mostly templated onboarding checklists, created by a shared "WIA Support" user.
  - About 22% of open tasks have dates; comments and priority are barely used.
  - The status-history ClickApp is off. The team works "to do → done/complete", and "in progress" is rare. This was checked against real tasks.
- **Platform alerts** (Meta, Google, LeadLock) are handled by sender and subject rules, not AI.
- **Fathom:** one team API key covers every WIA user. Client calls in the calendar outnumber recordings about 2 to 1, so the coverage report must show calls that have no recording.
- **GHL:** WIA's own invoices are readable. Client sub-account leads return 401 for every token, so leads are **not** a phase-1 source.
- **Two rounds of WIA (Gisselle) answers** were analysed, with cross-questions and Slack reply drafts. Suggested deadlines and repeating tasks are features for after testing. "Mark complete" is a KB feature.

---

## 8. Decisions log (settled, don't re-ask)

| Date | Decision |
|---|---|
| 29 Oct | Finish S1 before moving on. No dev Slack app; test through the `OUTBOUND_MODE` guard |
| 29 Oct | ClickUp writes use each user's own OAuth token, with no fallback to the E2M AI account |
| 29 Oct | Admins map clients in the UI; YAML is for dev only. Archiving pauses sync. Past clients aren't backfilled |
| 30 Oct | **Email stored as pointers:** message and thread IDs, subject, sender, recipients, date, client and reason. No bodies; bodies are fetched on demand. Each action keeps only its evidence quote |
| 30 Oct | AI runs as a batch over all mail since the last run, on an admin-set interval |
| 30 Oct | Permission to file senders is granted per user. Prospects and accelerator members are in scope. AR-23 approved. The extraction accuracy test runs while the prompt is drafted |
| 2 Nov | Approve-every-outbound guard (§5) |
| 3 Nov | Pilot = 4 clients. History shows curated milestones, not a raw message dump. No dollar amounts in history |
| 4 Nov | The production schema comes from one SQL file. No CI. The backfill so far was dev-only |
| 4 Nov | Port the MVP edits to React (done) |

---

## 9. Waiting on WIA

The full list is in `kb_tab_scope/tobeaskedinnextcall.md` §4–§9:
- a ClickUp **sandbox list** for the S1 write test;
- confirmation of the **client list**, and whether the 20 other active clients are reactivated for production;
- whether **past clients** belong in the KB at all;
- **sign-off on owners and roles** (S3);
- the **retention rule** for Slack, Drive and Fathom text (BF-7);
- mailbox access beyond hello@: staff mailboxes, and `hello@leadlockpro.com`, which most LeadLock-only clients use;
- the product decisions in `docs/mvp-card-to-data-map.md` §6:
  - archive semantics;
  - "Ping on Slack" vs approving every send;
  - priority, which has no ClickUp source;
  - whether the deployed MVP may stay public.

---

## 10. Suggested order to finish the pipeline

1. **Commit what's here** with Jainil: check `git status`, and make sure nothing under `backend/.local/` and no `.env` is staged. Then run the tests.
2. **Close BF-1 to BF-7.** BF-2 (email pointers) is the biggest, because it changes the Gmail adapter, normaliser, persistence, evidence checks and adds a migration. After any new migration, regenerate `schema.sql` with `python -m backend.scripts.schema_export`.
3. **Stand up Railway staging:** Postgres, web, worker and `OUTBOUND_MODE=off`. Do a dry run on 2–3 clients with full history, run twice; the second run must create zero new versions. Also check that a run killed mid-way resumes cleanly, and that an induced 403 retries instead of marking access denied.
4. **Production:** Postgres with backups, apply `schema.sql`, run the full backfill, and review the coverage report with WIA.
5. **S6 live sync:** the scheduler and Calendar `syncToken`.
6. **Design S7–S9** from `docs/mvp-card-to-data-map.md`:
   - extraction contracts, then the actions and read-model tables;
   - build extraction and test it against the overlay gold set;
   - then the action model, with write-back through the outbound guard.
7. **S10 login and visibility, S11 API, S13** wiring the React cards to the API. Then the pilot with 2 account owners and WIA sign-off.

---

## 11. Uncommitted files on `mvp` (as of 4 Nov)

**Modified:**
- Backend: `.env.example`, `app.py`, `config.py`, `models/db/__init__.py`, `requirements.txt` (adds `cryptography==43.0.3`), `scripts/export_frontend_snapshot.py`, `scripts/kb.py`, `services/intake/adapters/drive.py`, `services/intake/pipeline.py`, `sql/README.md`.
- Frontend: `exports/client-portfolio.html`, `index.html`, `src/App.tsx`, `src/components/Sidebar.tsx`, `src/health-v3.ts`, `src/kbLive.ts`, `src/main.tsx`, `src/teams.ts`, `src/types.ts`, and `src/views/` Actions, ActionsRevised, ActionsTeams, CallPrep, Client360, ClientDetail, ClientPortfolio.css, Clients, CommitmentHistory, Dashboard, Health, HealthRevised, HealthV3.

**New:**
- Backend docs: `backend/docs/production-readiness.md` (**the living tracker**).
- Backend code: `backend/models/db/outbound.py`, `backend/routes/clickup.py`, `backend/scripts/repair_drive_associations.py`, `backend/scripts/schema_export.py`, `backend/services/outbound/`, `backend/services/shared/secrets.py`.
- Migrations: `backend/sql/migrations/versions/c05a20261102_clickup_connections.py` and `c06a20261102_outbound_requests.py`.
- Schema: `backend/sql/schema.sql`.
- Tests: `backend/tests/integration/test_drive_attribution.py`, `backend/tests/services/test_clickup_oauth.py`, `backend/tests/services/test_outbound.py`.
- Docs: `docs/mvp-card-to-data-map.md`.
- Frontend: `frontend/src/mvp.css`, `frontend/src/mvpActions.tsx`.
- Analysis (check them for real data before committing): `kb_tab_scope/Action_Register_analysis.md`, `kb_tab_scope/tobeaskedinnextcall.md`.

**Already committed** by Jainil: S2/S3 and the MVP work (`e3557d5`, `6f96dec`, `c9dba1b`, `df45d22`, `1f63ef8`). They include `backend/docs/schema.dbml` and `stage-3-people-roster-plan.md`.

**Never commit:**
- `backend/.local/`: `clients.yaml`, `roster.yaml`, `approval*.yaml`, raw pulls, overlays, `contact_noise.md`, `past_clients.md`;
- `backend/.env`;
- `frontend/src/*.local.json`.

---

## 12. Document index

| What | Where |
|---|---|
| Production tracker (blockers, observations, stage table, infrastructure, checklists) | `backend/docs/production-readiness.md` |
| Card → data source map, extraction backlog, open decisions | `docs/mvp-card-to-data-map.md` |
| Schema: diagram / single SQL file / how to apply | `backend/docs/schema.dbml` / `backend/sql/schema.sql` / `backend/sql/README.md` |
| Stage 3 plan and validation | `backend/docs/stage-3-people-roster-plan.md`, `people-roster-validation.md` |
| Ingestion pipeline design and architecture | `docs/Ingestion-Pipeline-Design.md`, `docs/Client-Knowledge-Base-Solution-Architecture.md` |
| Per-tab scope | `kb_tab_scope/01-…06-*.md` |
| Action Hub analysis; questions for the next WIA call | `kb_tab_scope/Action_Register_analysis.md`, `kb_tab_scope/tobeaskedinnextcall.md` |
| MVP hand-edit notes, deployment | `mvp/readme_changes.md`, `mvp/README.md`, `mvp/Caddyfile.template` |
| Credential register (no secret values) | `knowledge_base/credential_register.md` |
| 14-stage breakdown | https://claude.ai/artifact/8aJMARZCsVH4i3bLHS47Cu |
| Earlier chat export (to 30 Oct) | `Wedding_Industry_Ads/WIA-KB-chat_Jainil-Trivedi_2026-10-30_1930-IST.md` |
