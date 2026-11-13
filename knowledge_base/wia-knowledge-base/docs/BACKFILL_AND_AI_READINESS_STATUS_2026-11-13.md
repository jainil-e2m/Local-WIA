# Backfill, Railway and AI readiness: status on 13 Nov 2026

**Question:** can the production backfill start on Railway now, and will the AI components built while it runs work on that data without a second backfill?

**Checked against:** the files on disk in this repo (branch `mvp`: local commit `189c68f` plus all uncommitted and untracked work), the local database, and the Railway project as the CLI shows it. Read-only review: no code was changed.

**Two passes:**
1. **First pass** (§0 to §9): the data path. That is the backfill engine, every adapter's normaliser, the schema, the AI sweep and skills, archive and reactivate logic, and the Railway runbook.
2. **Second pass** (§10): the rest of the local build. That is call prep and its `c11` migration, ad platforms, the AI runtime, the portfolio build, the worker and queue, every route and auth, people, outbound, the LeadLock app, config transfer, and the frontend data layer. Four parallel reviews ran, and each headline finding was then re-checked by hand.

**Tests: 372 passed** on the full local build, run against the local compose Postgres on 13 Nov.

> This file is in the repo, so it holds no client names, addresses or IDs.

---

## 0. Verdict

| Area | Verdict | One line |
|---|---|---|
| Architecture | ✅ Sound | Sources → versioned records → text units with locators. Everything AI makes is derived and re-runnable |
| Database | ✅ with 2 actions | 42 tables, one migration chain (head `c11a20261112`). The head migration is **untracked**, and pgvector is absent |
| Backfill engine | 🟡 Go after pre-flight | Resumable, idempotent and crash-safe in code. Stage 4 exit tests were never run; BF-5/6/7 are open; Gmail ignores `--days` |
| Railway | 🟡 Not started | The project has one service (the old MVP). No Postgres, web or worker services yet. The code to deploy isn't pushed |
| AI on backfilled data | ✅ Yes, with 3 caveats | No re-backfill needed for the 5 built skills or for future search/RAG. Caveats: Gmail bodies aren't stored, the AI sweep is forward-only, and AI approvals need named sign-in |

**After the full-build review (§10):**
- **Deploy and backfill the 4 active clients:** yes, after 3 small fixes before deploy (§10.2 A).
- **Activate all 24 clients with full history:** fixed on branch `fix/backfill-scale-stability` (§10.5). That covers the portfolio build at scale, crash loops, one build at a time, the LeadLock grant and people edits, plus `kb coverage` as the "done" check. Merge it first.
- **Switch the AI on:** not yet. 9 fixes come first (§10.2 C).

**Bottom line:** yes, start the backfill, after the 8 pre-flight items in §7 (about half a day). The storage design keeps raw facts separate from AI output, so AI can be built in parallel and run over the finished backfill later. Only one decision can force a source to be re-read: **storing Gmail bodies vs pointers (§6.3).** Settle it before the Gmail copy.

---

## 1. Where things stand today

| Item | State |
|---|---|
| Git | Branch `mvp`. `origin/mvp` = `1f63ef8` (4 Nov). Local commit `189c68f` (5–12 Nov, 187 files) **is not pushed**. On top of it: 29 modified and 13 untracked files (call prep, ad platforms, migration `c11`, a staged delete of `services/ai/call_types.py`) |
| Railway | Project "Client Knowledge Base", environment `production`, **one service** (`wia-knowledge-base`; most likely the old static MVP page). No Postgres, web, worker-bulk or worker-sync services yet. The local folder isn't linked to the project (`railway link` not run) |
| Stage (14-stage plan) | Stage 4 (engine) is code-complete for BF-1 to 4, 8 and 9. BF-5 is partial, BF-6 is open, BF-7 is undecided. **None of Stage 4's exit tests has run** (run twice → zero new versions; kill → resume; induced 403s) |
| Last production-like data | Only the local learning run from Oct–Nov (Gmail stopped at about 55%, on an older parser `gmail-v2` that kept bodies). Production starts empty |
| Tests | **372 passed** (13 Nov, full local build, compose Postgres) |
| AI layer | Built, `AI_MODE=off`, never run against production. 6 skills (incl. `call_focus`), prompts, contracts, quote checks, budget, run log |
| Doc vs code drift | `docs/DOCS_VS_IMPLEMENTATION_2026-11-12.md` lists 9 owner decisions where the 12 Nov architecture contradicts the build. **Don't follow `SOLUTION_ARCHITECTURE.md` §14.2 as written**: it would delete the working sync, audit and people tables |

---

## 2. Architecture ✅

```
Sources (7)                  Engine                                Stored facts (never AI-written)
Slack, ClickUp, Drive,  →  adapters → sync streams/runs  →  source_records → source_versions → content_units
Calendar, Fathom,            work_items (lanes: sync,          (+ record_associations to clients,
Gmail, LeadLock              bulk, maintenance, analysis)          scope_memberships, coverage_windows)
                                                                         │
                ┌────────────────────────────────────────────────────────┤
                ▼                                                        ▼
  Read model: portfolio snapshot                         AI layer (off): context.py reads content_units
  (read_model_snapshots, ETag)                           + live Gmail bodies → ai_runs, action_candidates,
                │                                        call_briefs (keyed by input hash + prompt hash)
                ▼                                                        │
  FastAPI /api/v1/* + React build ◄──────── present.py merges approved AI output ┘
```

**Why it suits AI:**
- **Facts and interpretations are separate tables.** The AI never writes into `source_*` or `content_units`. Every AI result can be thrown away and rebuilt from the stored facts.
- **Every text unit has a locator** (Slack channel+ts, ClickUp task/comment id, Doc paragraph/table row, Sheet row, PDF page, Fathom segment with timestamp). That is what citations and chunking for search both need.
- **Versions are immutable and content-hashed.** A citation to a version id stays valid. A re-run creates no new versions unless the source changed (`version_key` includes `parser_version`).
- **Rerun control already exists.** An AI run is skipped when its input hash, which includes the prompt-file hash, is unchanged. Editing a prompt reprocesses only that skill.

**Concerns:** none blocking. The drift between the documents and the code (9 decisions) is a planning risk, not a data risk. Only decision #2 (email text) touches stored data (§6.3).

---

## 3. Database ✅ (2 actions)

| Layer | Tables |
|---|---|
| Registry, people | `businesses`, `business_aliases`, `contacts`, `people`, `person_addresses`, `provider_identities`, `mailbox_holders`, `account_team_members`, `service_engagements` (unused), `sender_rules` |
| Sources (the backfill writes these) | `connector_accounts`, `source_scopes`, `source_records`, `source_versions`, `content_units`, `record_associations`, `scope_memberships`, `drive_nodes`, `association_reviews`, `client_source_decisions`, `record_changes` |
| Sync engine | `sync_streams`, `sync_runs`, `sync_cursors`, `coverage_windows`, `work_items`, `webhook_receipts` (unused) |
| Integrations | `clickup_connections`, `leadlock_installations`, `leadlock_locations`, `leadlock_app_events`, `outbound_requests`, `audit_events`, `meeting_links` |
| Derived (AI, read models) | `ai_runs`, `action_candidates`, `call_briefs`, `call_overrides`, `call_skills`, `read_model_snapshots`, `ad_accounts`, `ad_daily` |

- **Ready for backfill:** retention columns exist on `content_units` (`retention_category`, `retention_state`), with nothing expiring. Availability covers `deleted_upstream` and `access_lost`. Per-scope coverage windows record gaps.
- **Action 1:** migration `c11a20261112_call_prep.py` (`call_briefs`, `call_skills`, `call_overrides`, `ad_*`) is **untracked**, but `schema.sql` already says its head is `c11`. Once a migration runs in production, it can never be edited. The second pass (§10.3) checked `c11` against the models and `schema.sql`: it is **safe to commit as final**.
- **Action 2:** there is no `pgvector`. Search or chat over the KB will need it. Embeddings are derived from `content_units`, so adding them later needs no re-backfill. **Swapping the Postgres service after a 60k-message copy does** need a dump and restore, so pick a Postgres that has the extension now (§7, item 2).
- Local and compose run PostgreSQL 16; `schema.sql` was generated on 16. Railway's template may be newer, which is fine.

---

## 4. Backfill ✅ engine, 🟡 run conditions

### 4.1 What each source stores (this decides what the AI can use later)

| Source | Stored | Honours `--days` / `BACKFILL_DAYS`? | Gaps for AI |
|---|---|---|---|
| Slack | Message text units, author, thread ids, reactions, file names | ✅ (`oldest`) | `blocks`/`attachments`-only bot posts get no text (only `m["text"]` is read). Files are referenced, not parsed |
| ClickUp | Task name+description and comments as units. Attributes: status, assignees, watchers, due/start/done, custom fields, checklists, tags, parent | ✅ (`date_updated_gt`) | No priority, time estimate or subtask tree beyond `parent` |
| Drive | Docs (headings, paragraphs, table rows), Sheets rows, PDF and DOCX text, folder path | ❌ full history | Images, video and audio are referenced only (no OCR) |
| Calendar | Pointer: title, time, invitees, status, recurrence | ✅ (`timeMin`) | Fine for call prep |
| Fathom | Client meetings: transcript segments with speaker and timestamp, Fathom summary and action items (flagged `provider_generated`). Other meetings: pointer only | ❌ full history | Internal meetings need `kb ai team-meetings` (one-item refreshes, no re-backfill) |
| Gmail | **Pointer only** (`gmail-v3`): ids, thread, headers, labels, attachment names, `body_sha256`. The body is read live by `fetch_body` | ✅ (`after:`, fixed 13 Nov); spam and trash skipped | No stored body text: email search is impossible without a live fetch. Attachments aren't parsed |
| LeadLock | Metadata and counts only (no couple names, emails, phones or messages) | ❌ re-reads the sub-account | By design |

> ✅ **Fixed 13 Nov (branch `fix/backfill-scale-stability`).** The Gmail copy now honours its window: `--days N` or `BACKFILL_DAYS='{"gmail": N}'` is sent to Gmail as `after:`. Spam and trash are no longer listed, and new spam or trash reported by the change feed is never stored. Inbox, sent and archived mail are still read, because WIA's replies and archived client threads belong to the record. The daily full re-check still lists the whole mailbox (minus spam and trash), as it must to notice changes.

### 4.2 Resilience (verified in code)

- **Resumable:** `kb backfill` → `sync.request_run(..., "backfill")`. `kb run stop/resume <id>` works. A resumed run continues from the stopped page.
- **Crash-safe:** page effects and the work item commit together (B-02, `docs/atomic-publication.md`).
- **Idempotent:** the version key holds a content hash plus `parser_version`. An unchanged record counts as `unchanged`.
- **Rate limits:** Google quota 403s are retried or throttled, never recorded as "inaccessible" (BF-1, `shared/http.py`).
- **Late mapping is cheap:** Gmail, Calendar and Fathom keep a pointer for **every** item. Approving a contact later re-qualifies stored history (`qualify.recheck`, P-02) with no re-read. Slack, ClickUp and Drive scopes are read only once mapped; mapping one later starts a backfill of that scope alone.
- **Wrong mapping is fixable:** re-pointing a scope moves its records (`clients/mapping.py`). Drive misfiles have `scripts/repair_drive_associations.py`.

### 4.3 Active and inactive clients (all N clients, not only the pilot)

`businesses.status` is `active` or `inactive`. `services/intake/scoping.py` and `clients/mapping.py` decide what each one gets:

| | Active client | Inactive client |
|---|---|---|
| Its own scopes (Slack channel, ClickUp lists, Drive folders, LeadLock sub-account) | Copied by `kb backfill` | **Not read at all.** `live_scope()` skips scopes dedicated to an inactive client |
| Shared sources (hello@ Gmail, Calendar, Fathom) | Items with its approved contacts are admitted to it | Its contacts don't count. Its emails, events and meetings are still stored as **unlinked pointers**, because the whole mailbox and calendar are read |
| AI | Swept (`Business.status == "active"`) | Nothing runs |
| Reactivated later | — | `qualify.recheck` links the stored pointers at once. Its own scopes are copied **only** by the scheduler's sweep (`SYNC_SCHEDULER_ENABLED=true`) or a new `kb backfill` run. With the scheduler off during the backfill, a client you reactivate stays half-loaded until you re-run `kb backfill` |

**What this means for go-live:**
- **Set every client's status before the first copy.** The backfill copies history only for clients active at that moment. A client switched to active afterwards needs the scheduler on (its sweep copies only streams never copied), or a re-link in Connections. Re-running `kb backfill` also works, but it starts a new full copy of **every** live scope for the providers named. That stores no duplicates, but repeats hours of reading, Gmail included.
- **Inactive clients get no Slack, ClickUp or Drive history.** If past clients' history should be searchable or used by the AI (for example, for winback or handover), decide now: either make them active for the backfill and archive them afterwards (their history stays; only syncing pauses), or accept that it is missing.
- Unmapped items (no approved contact, no mapped scope) are kept as pointers, so mapping or approving later never needs a full re-read for Gmail, Calendar or Fathom.

### 4.4 Still open

| Item | Impact on starting | Impact on AI later |
|---|---|---|
| Stage 4 exit tests (run twice, kill and resume, induced 403) never run | Do them as the pilot run (§7, item 6) | None if they pass |
| BF-5: no test catches a parser change without a version bump | Low | A silent change could mix two text shapes in one parser version |
| BF-6: Dubsado or finance mail is never admitted | None: the pointers are stored | A sender rule plus a re-qualify pass attaches them later, with no re-read |
| BF-7: retention undecided | None: everything is kept | **Must stay "keep"** until any historical AI pass is done (§6.3) |

---

## 5. Railway deployment 🟡

**Ready in code:**
- One root `Dockerfile` builds the React portfolio and the API.
- Services and start commands are documented in `backend/README.md` ("Deploying to Railway").
- `PRODUCTION_MODE=true` refuses to start without `KB_SECRET_KEY`, `OPS_TOKEN`, `KB_TEAM_PASSWORD_HASH` or a non-local DB, or with `INGEST_WINDOW_DAYS` set.
- `/health/ready` reports the schema revision, mode and AI state.
- The scheduler, AI and outbound are all off by default.
- Alembic resolves from `/srv` (`script_location = %(here)s/sql/migrations`).

**Not done:**
1. Postgres, web, worker-bulk and worker-sync services aren't created. The project holds only the MVP service.
2. The code to deploy exists only on this machine: 1 unpushed commit plus uncommitted work. A GitHub-sourced service would build the 4 Nov code. `railway up` would upload untracked files, including `c11`.
3. **Backups: built 13 Nov.** Railway backups need Pro, so a `db-backup` cron service runs `backend/scripts/backup.py` nightly: a snapshot-consistent dump to a private bucket, read back by SHA-256, a monthly restore check, then pruning (14 daily, 8 weekly, 12 monthly). Rehearsed end to end on Postgres 18 with an S3 stand-in, including a real restore. Setup: `backend/README.md`, "Backups".
4. No staging project. §7 item 6 replaces it with a pilot run on the empty production DB.
5. LeadLock production install. The agency refresh token rotates, so stop local LeadLock first (runbook step 4).
6. **Later, not blocking:** once the scheduler is on, Gmail's daily reconcile runs the `list` phase. That re-lists the mailbox and makes one metadata GET per message every day, on the bulk lane. Watch its duration in the first week.

---

## 6. Will the backfilled data serve the AI components? ✅

### 6.1 Built skills against the stored data

| Skill | Reads | In the backfill? | Re-backfill needed? |
|---|---|---|---|
| `meeting_digest` | Fathom transcript units, open actions, client email (live Gmail), internal Slack, Viktor's posts | Yes | No |
| `team_meeting_digest` | Internal meeting transcripts | Pointers only. `kb ai team-meetings` queues one-item refreshes | No |
| `call_brief` / `call_focus` | Calendar pointers, computed facts (`callprep/facts.py`), digests, lead and ad figures | Yes. Ads come from a separate `kb ads pull` (90 days) | No |
| `email_actions` | Gmail pointers and the **live** body | Pointers yes, bodies fetched at run time | No, but it needs Gmail access at AI time |
| `history_moments` | Portfolio events and digests | Yes | No |
| **Future** chat or search (RAG) | Chunks and embeddings from `content_units` | Text with locators: yes, except Gmail | No for Slack, ClickUp, Drive and Fathom. Email needs bodies (§6.3) |

### 6.2 Three caveats

1. **The AI sweep is forward-only.** `services/ai/sweep.py` digests meetings from the last **14 days** (`LOOKBACK`) and email only for the **latest closed batch window**. A window missed while the worker is down is never caught up. The backfilled history therefore won't become digests or proposed actions on its own. If the Action Hub should start populated from history, add a bounded, budget-capped `kb ai backfill --since` that reuses `sweep.due`. That is a small command, built once the cost is agreed. Without it, the AI starts from the day it's switched on.
2. **Email text isn't stored.** Every AI use of email depends on a live `fetch_body`: the mailbox must still hold the message, and the Google token must still work. That suits the 5 skills. It doesn't suit full-text email search.
3. **Making it usable in the frontend is gated on sign-in, not on data.** AI actions are proposals that an admin approves. Behind the shared team password, the server trusts whatever admin name the app sends (`decisions.py` shortcut). Named sign-in (S10) should exist before `AI_MODE=live` in production. Also run the S7 exit check first: `kb ai preview` review and the 50-case accuracy set.

### 6.3 What would force a re-read (decide before or during the backfill)

| Change | What it costs | When to decide |
|---|---|---|
| **Store Gmail bodies** (architecture O-4 / decision #2 vs code BF-2) | A re-read of the **client-admitted** messages only (thousands, not the 60k mailbox) via refresh or reconcile, plus a parser bump | **Before the Gmail copy.** Recommended: keep pointers now. Add a stored-body version for admitted mail only if chat or search over email is confirmed |
| Capture a field the parsers drop (Slack `blocks`/attachments text, ClickUp priority, parsed attachments) | Bump `parser_version`; the daily reconcile re-reads that source. Cheap for Slack, ClickUp and Drive | Anytime. To avoid it, add Slack `blocks`/`attachments` fallback text now (small) |
| Turn on retention expiry (BF-7) | Expired text is **never refetched** (`persist.py`: "retention: text refetch suppressed"). Irreversible for AI | Keep "keep forever" until the AI has processed history |
| A Postgres without pgvector | A DB dump and restore, not a re-read | Before the first copy (§7, item 2) |
| The 8 other doc-vs-code decisions (sync shape, AI shape, approvals, sign-in…) | None for stored data. They change code and derived tables only | During the AI build |

### 6.4 Building the AI while the backfill runs

- **Develop against production-shaped data, not the old local DB.** The local DB holds `gmail-v2` bodies and older parsers. Once the cheap sources finish (Slack, ClickUp, Drive, Calendar, Fathom), take a `pg_dump` of production. Restore it into the local compose DB, keeping it under `backend/.local/` (it holds client data). Build and `kb ai preview` against it. Gmail can keep copying in production meanwhile.
- **Keep local workers stopped** while production copies: they share Google, Slack and LeadLock limits, and LeadLock's rotating token. AI development needs no local workers. `kb ai preview --no-email` sends nothing and fetches no email.
- **AI migrations add only.** New derived tables are fine. Never alter or rewrite `source_records`, `source_versions` or `content_units` in an AI migration; that keeps the backfill reusable.
- **Ship AI as code plus migrations,** with `AI_MODE=off` until checked. Then create `worker-ai` (`--lanes analysis`), set the budget, and switch to `AI_MODE=live`. The stored data is untouched.

---

## 7. Pre-flight checklist (in order)

| # | Do | Size |
|---|---|---|
| 1 | Run the test suite locally (start compose Postgres). Then **commit and push** the working tree, freezing `c11` as final, or hold call prep and ads back from the first deploy | 1 h |
| 2 | Create Railway Postgres. Run `CREATE EXTENSION IF NOT EXISTS vector;`. If it fails, use Railway's pgvector Postgres template instead. **Add the `db-backup` cron service and a bucket** (backend/README.md, "Backups") | 30 min |
| 3 | Decide Gmail: **pointer (current, recommended)** or stored body for admitted mail. Record it in `production-readiness.md` §0 | decision |
| 4 | Gmail window: accept full history and fix the runbook line, or add `q=after:` to `readers.read_gmail` list phase. Consider dropping `includeSpamTrash` | 15 min |
| 5 | ✅ **Retention decided 13 Nov: keep all copied source text** (BF-7 closed). No expiry job | done |
| 5b | **Check each client's active or inactive status** and their contacts and scope mappings locally before `kb config export`. The export carries the status; nothing else is needed. **Past clients' history: out of scope for now** (decided 13 Nov) | 30 min |
| 6 | **Pilot run, which replaces the staging project:** on the empty production DB, `kb backfill --full slack clickup drive` for the pilot clients. Kill worker-bulk mid-run and `kb run resume`. Then run it again; `kb status` should show **zero new versions**. If anything is wrong, drop the DB and redo; nothing else is in it yet | 2–3 h |
| 7 | Stop local workers and remove the local `LEADLOCK_APP_CLIENT_SECRET` before the production LeadLock install | 5 min |
| 8 | Then follow the runbook: Fathom, Calendar, LeadLock, and Gmail last | hours (Gmail) |

Optional, small, and worth doing before Slack is copied: read Slack `blocks`/`attachments` fallback text when `text` is empty. It saves a later re-read of Slack.

---

## 8. Ponytail lens: what not to build now

**Skip (each named, none needed for a correct backfill):**
- a separate staging project (item 6 covers it);
- a retention or expiry job;
- embeddings and RAG (only choose a Postgres that can hold them);
- a historical AI pass (until its cost is agreed);
- per-provider interval settings;
- the architecture redesign in `SOLUTION_ARCHITECTURE.md` §14.

**Shortcut debt now in the code** (`shortcut:` comments). Production risk:

| Where | Limit | Matters when |
|---|---|---|
| `routes/access.py:30` | Login state is in process memory | The web service runs more than 1 process or replica |
| `services/ai/decisions.py:4` | Trusts the admin name the app sends | **AI goes live in production.** Needs named sign-in |
| `services/ai/runner.py:7` | The budget check can be passed by 2 AI workers at the edge | More than 1 `worker-ai` replica |
| `services/callprep/registry.py:4` | Only events already linked to a client become calls | Clients with unapproved contacts |
| `services/intake/execution.py:195` | LeadLock skips deletion checks | Deleted leads stay counted |
| `services/intake/requalify.py:30` | One approval re-checks a capped number of pointers, unindexed scan | Very large mailboxes after Gmail full history |
| `services/intake/sync.py:24` | Poll intervals hard-coded | WIA wants to tune them |
| `services/read_models/portfolio.py:12` | Every rebuild loads all records | Rebuild time passes ~30 s after the full backfill. **Watch this after Gmail** |

---

## 9. Not checked in this review

- What the existing Railway service actually serves.
- Railway's real behaviour: its Postgres image and extensions, connection limit, memory limit, whether its edge overwrites `X-Real-IP` and normalises `..` in paths.
- Live OpenRouter prices, and how OpenRouter splits reasoning tokens from `max_tokens`.
- Whether Google Ads API `v26` and Meta `v26.0` exist.
- How HighLevel handles a second install of the same app.
- Frontend views beyond the data layer, Action Hub and call prep.

---

## 10. Full local build review (second pass, 13 Nov)

### 10.1 What the local database holds today

Counts only, from the local learning-run database (schema head `c11a20261112`):

| | Count |
|---|---|
| Clients | **4 active, 20 inactive** |
| Approved scopes | ClickUp 51, Drive 27, Slack 5, LeadLock 5, Calendar 5, Fathom 2, Gmail 1 |
| Source records | 33k. Gmail 19.1k (620 linked to clients), LeadLock 12.8k, Slack 1.6k, ClickUp 678, Calendar 584, Drive 529, Fathom 5 |
| Records linked to a client | 16.4k |
| Text units | 19.6k (about 5 MB of text) |
| DB size; portfolio snapshot | 115 MB; 2.3 MB |
| AI tables | 4 `ai_runs`, 8 `action_candidates` (local tests; never exported) |

At 4 clients, LeadLock is already most of the linked records. **All 24 clients with full Slack, ClickUp, Drive and Fathom history will plausibly pass 65k linked records.** That matters for finding B1.

### 10.2 Findings by when they must be fixed

Each finding was checked by hand against the code.

**A. Before deploying (small)**

| # | Where | Problem | Fix |
|---|---|---|---|
| A1 | `read_models/portfolio.py` (`call_prep.calls(...)` in `build`) | Call prep runs inside the portfolio build with no guard. One bad calendar event, AI run or skill config fails **the whole portfolio**, with the AI off too | Wrap it in a try, and fall back to empty call lists with a logged error |
| A2 | `frontend/src/App.tsx` (localStorage `STORAGE_KEY`), `clientDetails.ts` | Action Hub edits (mark done, reassign, due date, title) and client-details edits are saved only in that browser, and win over the KB's data on reload. Colleagues never see them | Hide or disable those controls in the production build, or label them "this browser only" until the action API (S8) exists |
| A3 | Runbook order and `config.py` | With `PRODUCTION_MODE=true` the scheduler defaults to **on**. `kb config import` carries approved scopes, so if `SYNC_SCHEDULER_ENABLED=false` isn't set first, the sweep starts full-history copies of everything, Gmail included, on its next pass | Set `SYNC_SCHEDULER_ENABLED=false` on every service **before** the import. Review the exported scopes for test or pilot mappings |

**B. Before activating all clients or the full-history scale**

The data copies are fine at any scale. These break the screens and the worker.

| # | Where | Problem | Fix |
|---|---|---|---|
| B1 | `portfolio.py` `build` (`ContentUnit.version_id.in_(version_ids)`) | One query parameter per linked record. **Postgres refuses past 65,535**, and the error is retried, then the job fails, so the snapshot freezes. A 30 s `statement_timeout` (`db.py`) can hit first | Select the units with a join or subquery on `record_associations`, not a Python list |
| B2 | Same build | It loads every linked record and **every** text unit (all transcript segments, all Drive paragraphs), inactive clients included, but uses only the first unit, the summary and questionnaire units. Estimate: 1.5–2 GB at 100k records (unverified) → the bulk worker runs out of memory | Load only the unit kinds the build uses; skip inactive clients |
| B3 | `workers/queue.py` `claim` | A job whose lease expires is claimed again with `attempt` unchanged, with no cap. The runner has no SIGTERM handling. A job that crashes its process (for example from B2's memory) loops forever, on both bulk replicas | Increment `attempt` on reclaim and fail past a cap |
| B4 | `routes/portfolio.py`, `app.py` gzip | One snapshot holds the whole portfolio (about 1 KB of evidence per record, so roughly 100 MB at 100k records). Each load is gzipped at level 9 inside the single uvicorn event loop, which blocks every request, health checks included | Lower the gzip level, or split the snapshot per client |
| B5 | `portfolio.py` refresh cadence | During the backfill a rebuild runs every 5 minutes on the maintenance lane, shared with bulk copying. Builds slower than 5 minutes run on both replicas, and an older build can overwrite a newer one | Once B1 and B2 are fixed this mostly goes away. Otherwise rebuild after each source finishes |
| B6 | `intake/leadlock_app.py` `company_token` | A refresh that times out after HighLevel has already rotated the token rolls back, so the new token is lost. The next try with the old token gets 400, and **any 400 revokes the grant**. LeadLock syncing then stops until the agency reinstalls the app | Recoverable by reinstalling. To harden: don't revoke on the first 400; make the operator confirm |
| B7 | `leadlock_app.py`, `kb leadlock` | Nothing stops a non-production environment from spending the agency refresh token | Follow runbook step 4 (remove the local `LEADLOCK_APP_CLIENT_SECRET`). A production-only check is about 3 lines |
| B8 | `people/resolve.py` `__init__` (`with_for_update(read=True)` on every person) | Every intake page that meets a new identity share-locks every person row. With `lock_timeout=2s`, **admin roster, merge and team edits fail during the backfill** | Workaround: don't edit people while copying. Fix later: lock only the people touched |

**C. Before `AI_MODE=live`** (nothing below runs while the AI is off)

| # | Where | Problem |
|---|---|---|
| C1 | `ai/runner.py` (failed runs stored with `answer=None`), `openrouter.call` | **Spend on failed calls is recorded as $0.** That covers a failed repair, any exception after a paid answer, and retries (a `ProviderError` is retried 3 more times). One bad meeting can cost about 8 calls that `month_spend` never sees, so the **budget can be overrun** |
| C2 | `ai/context.py` (bare `except Exception` around `fetch`) | Every Gmail error (expired token, 5xx, rate limit) is treated as "message gone". An email batch then succeeds with no email, is billed, and is never redone. Swallow only `NotFoundError` |
| C3 | `openrouter._post` (httpx errors not caught), `workers/queue.enqueue` (`on_conflict_do_nothing` on signature) | A timeout or connection error is classed as a bug and fails at once, with no run row. A failed signature can never be re-queued, so that meeting or email window is lost for good |
| C4 | `context.py` hides all of a subject's proposals; `runner.py` supersedes only "proposed" ones | When a meeting gets a new version, its re-digest proposes again actions that were **already approved**. Duplicates in review, and billed again |
| C5 | `meeting_digest` prompts | The client recap email draft can draw on internal Slack, Viktor's posts or finance mail. Add a rule: the recap uses only what was said with the client |
| C6 | `callprep/registry.py` (`order_by(occurred_at, Business.name)`) | Copies of one meeting on several calendars have no tie-break, so the call's id can change between builds. Overrides vanish and a paid "first" brief is rebuilt. Add `SourceRecord.id` to the order |
| C7 | `callprep/skill_files.py` (block values unchecked) → `pack.py` | One bad value saved in the skill editor raises inside `sweep.due`, which **stops all AI work** (meeting digests and email too) until it is reverted |
| C8 | `services/ads` unmap | Unmapping keeps `last_pulled_at`. After a remap, only 7 days are pulled but shown as 30 days in briefs |
| C9 | `intake/adapters/fathom.py` speaker identity, `people/resolve.py` | A Fathom speaker with no matched email becomes one identity keyed by display name, across all meetings. It can resolve to a staff member with the same name, so the AI attributes a client's words to WIA |
| — | `ai/decisions.py`, `routes/callprep.py` (known) | Approvals and skill edits trust the name the browser sends. Named sign-in (S10) comes first |

**D. Cheap security fixes to the password gate (do soon)**
- `/health/../index.html` returns the frontend bundle without the password. The gate checks the raw path, and StaticFiles normalises `..`. Only app code and stub data are exposed, not client data.
- The brute-force limit trusts the `X-Real-IP` header from the caller (unverified whether Railway overwrites it).
- No CSRF guard: Basic credentials are sent automatically by the browser. Require a custom header on non-GET requests.
- `/health/ready` is open and shows mode, AI state and the schema revision. It returns 500, not 503, when the DB is down.
- The LeadLock OAuth callback has no `state` and echoes HighLevel's error text.

**A2 fixed 13 Nov (branch `fix/backfill-scale-stability`): edits are shared, saved on a button press**

| Edit | Before | Now |
|---|---|---|
| Action Hub (status, owner, due, acknowledge, notes, snooze, verification, deadline requests, added actions) | One browser's `localStorage`, and it overrode the KB | Saved on the KB server for everyone (`shared_edits`, migration `c12`), layered over the portfolio at load |
| Client details (name, aliases, owner, lifecycle, logo), cover, archive | One browser | The same, one row per client; details and cover save together |
| Call-type skills | Already saved to `/api/v1/call-skills` in the live app; a stale browser copy was also kept | Browser copy off in the live app |
| Pins, Action Hub browse mode | One browser | **Unchanged on purpose:** a person's own view, not a shared fact |

- **Only a deliberate press saves.** Every change goes through a button: Mark done (with its confirmation), the status, owner and date pickers, Acknowledge, Save notes (the notes box used to save when you clicked away; it now has a Save button), Save changes, and Archive.
- **Concurrent edits:** each save names the revision it was based on. A colleague's newer save wins: the stale one is refused (409), and the app shows their version with "X changed this since you opened it".
- **Rapid clicks:** saves to one item are queued, so two quick clicks never race.
- **Audit:** every save writes an audit line naming the fields changed, never their values.
- **Production boot:** if the shared edits can't be loaded, the app shows "unavailable" rather than a stale picture someone could act on.
- **The sample preview** keeps edits in memory for the visit.
- **Not yet:** edits stay in the KB; nothing is written to ClickUp (that's the outbound guard, S12). The editor's name is the one the app sends, until named sign-in.
- **Archive** hides a client from everyone's portfolio list, but doesn't pause syncing; that's the client status in Connections.
- **Verified:** 10 backend tests (merge, null clears a field, stale save refused with the current copy, field allow-list, unknown client, size cap, bad key, audit without values). In the browser, against the local API in production mode: a save, a fresh load showing it, a stale save refused with the colleague's version shown, archive, and client details. The test rows were removed afterwards.

**E. Minor:** validation picks a random owner when two people share a first name; a due date is checked against an unverified quote; ad currencies are summed; a revoked Google Ads token stops the Meta pull too; a non-string edit gives a 500; `kb outbound send` can double-send after a crash between the send and the commit; `KB_SECRET_KEY` validity isn't checked at start (a changed key makes every stored ClickUp and LeadLock token unreadable); the public-domain blocklist misses ISP domains; real staff names are hardcoded in `frontend/src/data.ts` and `teams.ts`.

### 10.3 Checked and fine

- **`c11` migration:** the chain is linear (`c10` → `c11`). Every table, constraint and index matches the models and `schema.sql`. **Safe to commit as final.**
- **Auth:** production refuses to start without the password hash and `OPS_TOKEN`. Every route except health, signed callbacks and ops is behind the gate. Local-only routes can't open with `PRODUCTION_MODE`. The ClickUp OAuth state is signed and expires.
- **Outbound:** with `OUTBOUND_MODE=off` or the kill switch on, nothing reaches Slack or ClickUp; the adapters only read. Approval is bound to the payload hash, a typed "yes" and a TTL.
- **External writes:** none from ads (GAQL search and Meta GET only) or call prep.
- **AI off:** sends nothing. Call-prep facts still render.
- **Per-client isolation in AI context:** split by `business_id`, with Slack split by per-client scope.
- **Production frontend:** never falls back to sample or `*.local.json` data. It shows an error if `/api/v1/portfolio` fails.
- **Config export:** carries no tokens, source data, LeadLock or AI tables (so no `[TEST]` proposals). Import refuses a database that already has clients.
- **Queue:** leases are fenced, and the heartbeat keeps long page jobs alive. LeadLock webhooks verify the Ed25519 signature and de-duplicate deliveries. Two workers refreshing LeadLock at once can't spend the token twice.
- **Inactive clients:** left out of clients, records, AI, call prep and collection.

### 10.4 The order this suggests

1. **Now:** §7 items 1–8, plus A3 (A1 and A2 are fixed). Deploy and backfill the **4 active clients**. That is pilot scale; the portfolio is 2.3 MB today.
2. **Before reactivating the other 20 clients:** B1–B8 and A1 are fixed on branch `fix/backfill-scale-stability` (§10.5). Merge it into what you deploy, then use `kb coverage` as the "done" signal.
3. **Build the AI in parallel** (§6.4), fixing C1–C9 as part of that work. Named sign-in before `AI_MODE=live`.
4. **When convenient:** D, then E.

### 10.5 Fixes for the 24-client, full-history backfill (13 Nov, branch `fix/backfill-scale-stability`)

**The question:** can the backfill stop half-way, or finish half-loaded, without anyone knowing?

**The data copy was already safe:**
- every page commits with its work item, or not at all;
- a failed or stopped copy resumes from its checkpoint;
- a re-run stores no duplicates;
- every gap is recorded per item.

**What could go wrong around it:**
- a worker stuck in a crash loop, so its copy never finishes and nothing says so;
- the portfolio build crashing the same bulk worker that copies;
- a LeadLock grant lost to a typo;
- no single "is it done?" answer.

| # | Fix | Where | Effect |
|---|---|---|---|
| B3 | Reclaiming a job whose worker died counts as an attempt. At 5 attempts (`CRASH_LIMIT`) the job fails with `crash_loop`, and its run shows `failed` and is resumable. Workers handle SIGTERM: they finish the current job and claim nothing new | `workers/queue.py` `claim`, `workers/runner.py`, `shared/errors.py` `CrashLoopError` | A page that keeps killing its worker can't loop forever, and it can't hide. A Railway redeploy no longer cuts a job mid-run unless the platform kills it first |
| B1 | The units query uses a subquery, not one parameter per record | `read_models/portfolio.py` `build`, `needed_units` | No 65,535-parameter limit at any size |
| B2 | The build loads only active clients' linked records, skips LeadLock (which has its own read model), and streams units, keeping only the 5 per record it reads (questionnaires keep all) | same | **Identical output on the real local data**, compared field by field. Peak memory 88 → 56 MB, 1.7 s warm. The saving grows with history: a transcript keeps 3–4 of its ~700 segments |
| B5 | One build at a time (Postgres advisory lock). A busy build queues the next instead of running in parallel | `portfolio.refresh` | No duplicate builds on both bulk workers, and an older build can never overwrite a newer one |
| A1 | A call-prep error is logged and leaves calls out. The rest of the portfolio still builds | `portfolio.build` | One odd calendar event can't freeze every screen |
| B4 | `/api/v1/portfolio` gzips each build once, at level 6, in the thread pool, and caches the bytes per ETag | `routes/portfolio.py` | Page loads no longer stall the single web process. Repeat loads cost one tiny query |
| B6 | The LeadLock grant is revoked only on `invalid_grant` (the refresh token is spent). Any other refusal raises "check the LEADLOCK_* settings" and keeps the grant | `intake/leadlock_app.py` `company_token` | A config typo no longer forces an agency reinstall |
| B8 | Person, team and identity edits wait up to 15 s for locks (`db.wait_for_locks`), not 2 s | `db.py`, `people/roster.py`, `teams.py`, `resolve.py` | Roster edits during the copy no longer fail. Intake pages keep their 2 s limit and their retries |
| new | **`kb coverage`**: one line per live source, with a verdict of `complete`, `complete_with_gaps` (only settled gaps: unsupported, inaccessible, deleted), `copying`, `incomplete` (with the resume command), `not_started` or `blocked`, plus its window and gap counts. **Exits 1 until every source holds its history** | `intake/sync.py` `coverage`, `scripts/kb.py`, runbook step 6 | The definition of done. Run it after each source finishes and before turning the scheduler on |

**Not changed, on purpose:**
- **B7** (a non-production environment spending the LeadLock grant): production installs its own grant, and its tokens are encrypted with production's `KB_SECRET_KEY`, so a local copy can't spend them. The runbook step (remove the local secret) covers the rest.
- **The snapshot is still one payload.** It grows by about 0.4 KB per linked record (evidence 1.5 MB for 3,500 records today). At full history for 24 clients, expect tens of MB uncompressed and a few MB gzipped. That works for a small team. Splitting it per client is the next step if loads get slow; it's marked as a `shortcut:` in `portfolio.py`.

**Verified:**
- 379 tests pass: 372, plus 7 new ones covering:
  - reduced units giving the same answers as the full list;
  - call-prep isolation;
  - gzip once per build;
  - one build at a time;
  - a crash loop failing the run, which then resumes to `complete`;
  - coverage for archived, blocked and legacy runs;
  - a LeadLock refusal that keeps the grant.
- `kb coverage` on the local learning data: 38 of 38 live sources complete, full history.

**Not verified:** Railway's SIGTERM grace period and memory limit; a build at real full-history scale (the local data is pilot-sized).

### 10.6 AI fixes C1–C5 (13 Nov, same branch)

The aim: no spend the budget doesn't see, no run that passes for complete when it isn't, no lost work, no repeat proposals, nothing internal in text the client reads.

**C1. Every billed attempt is recorded and counted** (`services/ai/openrouter.py`, `runner.py`, `callprep/service.py`)

| Scenario | Before | Now |
|---|---|---|
| Schema still broken after the one repair | Both calls billed, logged at $0, retried 3× (up to 8 paid calls) | `SchemaFailure`: both calls' cost logged, **not retried** (the same input fails the same way) |
| Timeout or dropped connection mid-request | No run row at all; class "bug", lost | Logged at the skill's **worst-case reserve** (`cost_estimated`), retried. The budget is over-counted, never under |
| Connect error, 429/5xx after the waits | Retried briefly | Logged at $0 (unbilled), retried on the AI ladder |
| Error inside a 200 (provider failed mid-answer) | Lost | Its reported usage is counted |
| 402 out of credits | Retried 3×, then failed | `OutOfCredits`: waits 6 h, like the monthly budget |
| 400/401/403/413 | Retried 3× | `ProviderRejected`: fails at once; fix the cause, then `kb ai retry` |
| Something breaks after a paid answer (checks, storing, a `due_phrase` over 200 chars) | No run row: paid, invisible | A failed run row with the answer's cost; `due_phrase` is clipped to fit |
| Call prep's repair call fails | Its cost dropped | Added to the brief's run |
| AI off or over budget | Read Gmail first, then refused | Refused before any Gmail read |

**C2. Gmail failures are told apart** (`context.read_email`, used by the digest, email actions and call prep)

| Scenario | Now |
|---|---|
| Message deleted since intake (404) | Skipped and counted as clipped; the run goes on |
| Credential expired or revoked, scope lost | `SourceUnavailable`: the run stops **before anything is sent**, waits 1 h, uses no attempt, and resumes once the credential is fixed |
| Throttled, 5xx | Raised: the job waits and retries; never a "succeeded" run with the email missing |

**C3. Nothing is lost to one bad moment** (`workers/runner.py retry_delays`, `ai/sweep.py`, `kb ai retry`)
- AI jobs retry on a ladder of about 11 hours (1, 5, 30 min, 1, 3, 6 h), then fail visibly (work item plus failed run rows).
- Call briefs keep the short ladder: a late brief is useless, and the sweep queues a fresh one.
- The crash-loop limit follows each job's ladder, so a long AI ladder isn't mistaken for a crash loop.
- The email sweep looks back **7 windows**, so a window that closed while the AI worker was down is still read.
- `kb ai retry [SKILL]` re-queues jobs that failed for good, after an outage, a prompt fix or a key fix.

**C4. No repeat proposals** (`ai/sweep.py`, `ai/context.py open_actions`, `runner._candidates`)
1. **A new Fathom version with the same transcript words** (Fathom adds its summary or action items, an invitee changes) is not digested again. Each digest stores a transcript fingerprint. This is the common case, and it now costs nothing.
2. **When the words did change**, the re-digest reads this meeting's approved actions as WIA's list, so it can mark them as matched.
3. **Code then drops any proposal an admin already approved or rejected from the same subject**, matched on the same title or the same quote. It shows as `already_decided` in the run's checks.
4. Pending proposals from the earlier digest are still superseded, as before.
5. Not covered on purpose: a different subject re-raising something rejected (for example, a client email after the meeting). That is new evidence, and it goes to review again.

**C5. The client recap email holds only what was said with the client** (`contracts.RecapEmail`, `validate.Checker.recap`, prompt)
1. **Structure:** the model now writes the recap as a greeting, cited lines and a sign-off, not free text (skill version 2).
2. **Code keeps a line only when:**
   - every ref it cites was shown to the model;
   - each ref is transcript `T#` or the client's own **non-finance** email `E#` (not `S#` Slack, `V#` Viktor, `A#` actions or finance email: Dubsado, or invoice, payment, overdue or contract subjects);
   - it copies no 6-word run from internal Slack or Viktor;
   - every figure in it appears in its sources.
3. **The greeting and sign-off** may hold no facts.
4. **With nothing left, there is no draft:** the host writes it.
5. **The prompt says the same,** and a person still sends the email.
6. **What can still slip through:** a reworded internal view with a transcript citation. The prompt and the reviewer are the guard there.

**Also fixed in passing:** lines clipped from a prompt no longer leave refs the model could cite (finding 10).

**Verified:** 10 new tests, covering:
- schema failure cost and no retry;
- timeout charged at the reserve, a connect error at $0;
- cost recorded after an answer that later breaks;
- credits wait while a refused request fails;
- Gmail credential, throttle and deleted-message cases;
- the full retry ladder, then `kb ai retry`;
- the email catch-up;
- the same transcript not re-digested;
- an approved action not re-proposed;
- recap line filtering in 9 cases.

**Still open from §10.2 C:**
- C6: calendar copy tie-break.
- C7: skill block validation.
- C8: ads unmap/remap.
- C9: Fathom speaker identity.
- Named sign-in before AI approvals.

None of them affects budget, data completeness or the recap.
- What the existing Railway service actually serves.
- Railway's current Postgres image and extensions.
- Live OpenRouter prices. The 12 Nov doc notes the code's cost caps assume about $3/$15 per M tokens for Sonnet.
- Frontend behaviour.

---

## 11. Pre-commit check (13 Nov, end of day): go

**Verdict: commit and deploy for the backfill.**

**Checked:**
- 404 tests pass.
- The production frontend builds.
- The production Docker image builds and runs end to end:
  - the pre-deploy migration builds an empty database to `c12`;
  - `/health/ready` reports production mode, scheduler off and AI off;
  - the API refuses requests without the team password (401) and accepts them with it;
  - the portfolio page is served;
  - a worker starts, and stops cleanly on SIGTERM.
- The production configuration (the runbook's variables) passes the start-up checks.
- A privacy scan of every change found no client names or emails in the code, tests or docs.

**Two independent reviews of the day's changes found no deploy blocker.** Fixed before commit:
- `kb coverage` no longer calls a source complete because of an earlier, shorter copy.
- The communication window is capped at a 90-day-old call.
- The portfolio build gets 300 s per statement.
- Two first saves of the same item at once now give a conflict (409), not a server error (500).
- The recap email may cite only emails the client wrote.

**Shared edits:**
- A save queued behind a refused one is refused too.
- The screen settles to the server's copy once an item's last save lands.
- The client editor closes on a conflict instead of letting a second Save undo a colleague's change.
- A field ClickUp also sets (status, owner, due date, title, side) follows ClickUp again once ClickUp changes after the edit.
- Saves go to the server only in builds that have one.

All of this was re-checked in the browser.

**Never commit:** `frontend/exports/httpsknowledge-base-wia.up.railway.app.html` and `kb_tab_scope/{Action_Register_analysis,tobeaskedinnextcall}.md`. They hold real client names, and are excluded locally in `.git/info/exclude`. `mvp/real_index.html`, already tracked, goes at cutover (runbook step 9).

**Before the team uses the app:**
- The cheap security fixes in §10.2 D, the CSRF guard first.
- Named sign-in before AI approvals.

**During the backfill:** avoid redeploying the workers. Each redeploy that kills a page mid-run counts as one of its 5 tries, and a run that uses them all needs a `kb run resume`.

---

## 12. Sign-in through Command Center (13 Nov)

The KB now signs in exactly like the Content Atelier: Command Center's **View Here** signs the person in with their own Command Center session, with no second login.

**How it works:**
- **The hand-off:** a PKCE hand-off with a 60-second, one-use code. The session token travels only server to server. The KB keeps it in its own HttpOnly cookie, with the session's original expiry.
- **Ongoing checks:** every request is checked with Command Center at most every 30 s. Team accounts only.
- **Sign-out:** signing out of the KB ends the session everywhere. A sign-out elsewhere reaches the KB within 30 s.
- **Shared password:** it stays only as the fallback where Command Center isn't configured.

**Views:** `RBAC_ENABLED=false` and `KB_DEFAULT_VIEWER=Whitney`. Everyone sees Whitney's view. The account area shows the person who signed in, with Sign out and no "preview as" switcher. Every change is recorded as the real person on the server (shared edits, AI decisions, skill edits), and the app's own "… by <name>" text uses their name too.

**Where the code is:**
- **KB:**
  - `backend/routes/auth.py` (start, callback, session, signout);
  - `backend/routes/access.py` (the session gate, `actor()`);
  - `config.py`: `COMMAND_CENTER_AUTH_ORIGIN`, `COMMAND_CENTER_PUBLIC_ORIGIN`, `RBAC_ENABLED`, `KB_DEFAULT_VIEWER`;
  - frontend: `src/auth.ts`, and the account area in `Sidebar.tsx`.
- **Command Center** (`Wedding_Industry_Ads/frontend`, outer repository, `main`):
  - `server/atelier-sso.mjs` takes the app's name;
  - `server/index.mjs` mounts it a second time at `/api/auth/knowledge-base`;
  - `src/lib/knowledgeBaseLaunch.ts`, and the Client Knowledge Base tile goes Live with View Here when `VITE_KNOWLEDGE_BASE_URL` is set;
  - `DEPLOY.md`.

**Verified:**
- **KB:** 12 new sign-in tests, and the full suite passes (416).
- **Command Center:**
  - the new router and tile tests pass;
  - type-check and build pass;
  - the full suite has one failure, the Client Hub "Spine" test, which times out under full-suite load, passes on its own, and is in code not touched here.
- **End to end, locally:** the real Command Center server and the KB, on separate hosts, with a made-up account in Command Center's development sign-in mode:
  - View Here landed on the KB signed in as that person;
  - a client deep link survived the sign-in;
  - a change was recorded as that person even though the app named Whitney;
  - signing out of the KB ended the Command Center session too.

**To deploy:**
1. **KB variables:** `COMMAND_CENTER_AUTH_ORIGIN` and `COMMAND_CENTER_PUBLIC_ORIGIN` (Command Center's https URL), `KB_APP_URL`, `RBAC_ENABLED=false`, `KB_DEFAULT_VIEWER=Whitney`.
2. **Command Center:** `VITE_KNOWLEDGE_BASE_URL=https://<KB domain>/`, then redeploy Command Center. Its code change is in the outer repository and needs its own commit.
3. **One web replica** on the KB, as on the Atelier: pending sign-ins live in the process.
