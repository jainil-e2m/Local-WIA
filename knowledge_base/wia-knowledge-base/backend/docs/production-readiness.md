# Production readiness tracker: backfill and phase 1

**Phase 1 = Client Portfolio + Action Hub, live.**

A working document. It records what has to change, what we observed, and the checks that say we're ready. Update it as items close. Started 4 Nov 2026.

How the whole v1 system works in production (sources, mapping, storage, sync, features, deployment, every decision) is described in [`docs/client_portfolio_deployment.md`](../../docs/client_portfolio_deployment.md). This file tracks the work to get there.

> No client names, personal addresses or IDs here: this file is in the repo. Real data and the local learning-run notes stay in `backend/.local/`.

---

## 0. Decisions that shape this

| Date | Decision |
|---|---|
| 6 Nov | **Shared sources keep a pointer for every item** (built 6 Nov: Gmail, Calendar and Fathom; P-02 `qualify.recheck` attaches them when a contact is approved). Linking to a client is a re-runnable rule pass over stored pointers: contact, domain, thread/series/recording propagation, sender rules. Anything else is only *suggested* |
| 6 Nov | **Operations review queue for unmatched items.** People with the "file senders" permission see each worthwhile unmatched item with a suggested client and the reason, and can: link it, link it *and* approve the sender (which re-links their stored history), mark the sender partner/team/blocked, ignore it, or move a wrong link. Decisions are audited, reversible, apply to the whole thread by default, and are never overridden by later automatic rules |
| 6 Nov | **Full client re-check freezes** that client's mapping (contacts, scopes, archive/activate, LeadLock) and holds its outbound; an admin can cancel. Reading stays open. **Action edits stay open:** afterwards each field changed both in the KB and in the sources during the run becomes a "Sources disagree" item for an approver; everything else merges automatically |
| 5 Nov | **`PRODUCTION_MODE` is the one switch.** false = local, on-demand intake, scheduler off. true = staging/production, scheduler on (pausable with `SYNC_SCHEDULER_ENABLED=false`), local-only routes closed, start-up refused until production requirements hold. Built 5 Nov (`config.py`, `tests/services/test_config.py`, `kb config`) |
| 4 Nov | **Production schema comes from one file,** `backend/sql/schema.sql`, applied once to the empty production database. After that, changes are normal migrations. Built and verified 4 Nov |
| 4 Nov | **No CI.** Deploys and redeploys are manual. The test suite is run by hand before each push (§6) |
| 4 Nov | **The backfill done so far was a local dev learning run,** not production. Its findings are in §2 |
| 30 Oct | **Email is stored as a pointer, not a copy:** message and thread IDs, subject, sender, recipients, date, and which client and why. The body is fetched only for AI processing or viewing. Each action keeps only its evidence quote |
| 30 Oct | AI processing runs as a **batch on an admin-set interval** |
| 29–30 Oct | Archiving a client pauses its sync. Partners never decide which client an email belongs to. Admins manage mapping in the UI |
| 2 Nov | Nothing reaches Slack or ClickUp without an approver typing **yes** for that exact request (outbound guard) |

---

## 1. Blockers before any production backfill

Status: ❌ open · 🟡 partly done · ✅ done

| # | Item | Status | What's wrong today | What "fixed" means | Where |
|---|---|---|---|---|---|
| BF-1 | **Google rate limits as HTTP 403** (B-01) | ✅ in code, uncommitted (4 Nov) | Was: every 403 became "scope denied", so a quota 403 recorded false "inaccessible" gaps, and on a list page blocked the job and failed the whole run | `ProviderClient` reads the error reason (`errors[].reason` and `details[].reason`). `rateLimitExceeded`, `userRateLimitExceeded`, `quotaExceeded`, `RATE_LIMIT_EXCEEDED` → up to 3 inline waits (exponential, 2–9 s), then `ThrottledError` (worker retries in 60 s, no attempt used). `dailyLimitExceeded` → `ThrottledError`, retry in 1 hour. Every other 403 stays `scope_denied`. Tests: `tests/services/test_http.py`, including "a throttled item is retried, not recorded as a gap". Still to prove on staging (§7 checklist) | `services/shared/http.py` |
| BF-2 | **Email pointer storage** (30 Oct decision; P-01) | ✅ storage, uncommitted (4 Nov) | Was: Gmail stored body text as content units | `gmail-v3`: every message is a pointer (message and thread IDs, RFC Message-ID, subject, from/to/cc, dates, labels, attachment names, `body_sha256` fingerprint) with **no content units**. The body is read live with `GmailAdapter.fetch_body` / `kb email <id>` (client emails only; nothing stored). No migration was needed: the pointer fits `source_versions.attributes`. Tests: `tests/services/test_gmail_pointer.py`, including a full backfill that finds zero content units and no body text. **Left for the AI step (S7):** the `record.extract` hand-off only queues records that have units, so Gmail queues nothing; S7 must queue admitted threads itself, fetch them, and keep only verified evidence quotes. The local dev DB still holds `gmail-v2` versions with bodies from the learning run; production starts empty | `adapters/gmail.py`, `scripts/kb.py` |
| BF-3 | **One Gmail search for every contact** (B-06) | ✅ not needed (6 Nov) | The backfill no longer searches by contact: it lists every message and qualifies each one (`readers.read_gmail`); discovery searches per client | — | `adapters/readers.py` |
| BF-4 | **Resume a stopped full-history run** (B-03) | ✅ in code, uncommitted (6 Nov) | Was: production callers used the restarting legacy `start_backfill`; the resumable path imported a module that doesn't exist (`rate_limits`), so it had never run against a real source; and `sync.resume` refused to resume a run an archive/unlink had stopped | `kb backfill`, Connections linking and the scheduler all use `sync.request_run(..., "backfill")`. The dead hook is removed. Resume resets the stopped page's work item. Tests: `tests/services/test_sync_scheduler.py` (LeadLock copy end to end on this path; archive mid-copy → reactivate → the same run continues from page 2). `pipeline.start_backfill` remains for local learning runs and its tests | `sync.py`, `execution.py`, `scripts/kb.py` |
| BF-5 | **Parser versions enforced** (B-07) | 🟡 | Every adapter has a `parser_version`, but nothing catches a parser change without a bump | A test fingerprints each normaliser's output on fixtures and fails if it changes without a version bump | tests |
| BF-6 | **Dubsado / finance mail rule** (P-03) | ❌ | Dubsado mail carries no client address, so it never qualifies | Sender rule: Dubsado notifications qualify, domain `finance`, client from the project label | `admission.py`, `adapters/gmail.py` |
| BF-7 | **Retention** (B-09 / P-07) | 🟡 | Everything is kept forever | Email is covered by BF-2. Confirm the rule for Slack, Drive and Fathom text (keep, or expire N days after extraction) and record WIA's sign-off | decision, then a `retention.expire` job if needed |
| BF-8 | **Drive attribution repair** | ✅ in code, uncommitted | The legacy pipeline filed Drive records under the running scope | `pipeline.membership_scope` uses memberships. A test covers it. The repair script exists for already-stored data | `pipeline.py`, `scripts/repair_drive_associations.py` |
| BF-9 | **Drive Sheets range / calendar status strings** | ✅ in code, uncommitted | A Sheets range with "+" made every Drive call fail with 400; the exporter crashed on some calendar status strings | Fixed. Keep the regression tests | `adapters/drive.py`, exporter |

**Not blocking the first backfill:**
- P-02: re-qualify when a contact is approved later. ✅ built 6 Nov (`services/intake/requalify.py`): Gmail attaches from its pointer, Calendar and Fathom get a one-item refresh;
- P-05: Calendar `syncToken` (needed for live sync, §3);
- P-06: deletion detection;
- G-07: programme channels (accelerator channels mix clients).

---

## 2. Observations from the local learning backfill (Oct–Nov)

What the real data taught us, and what each finding means for production and for extraction. Real figures are in `backend/.local/`.

| # | Observation | Consequence |
|---|---|---|
| O-1 | Gmail full history is large: roughly 60k+ messages in hello@; the learning run stopped at about 55% | Size Postgres storage and worker time **after** BF-2, since bodies won't be stored. Plan the Gmail backfill as a resumable multi-hour run |
| O-2 | About 71% of hello@ is automated: platforms, newsletters, ClickUp and Meta notices. Client threads are ~12 emails a day across 7–8 threads | Filter by rules first (done: discovery filters, sender rules). Only client threads go to the AI |
| O-3 | Discovery proposed 137 false contacts out of 201 (platforms, team addresses, partners) | Fixed: subdomain and automated filters, roster-aware internal check, partners, direct correspondents only |
| O-4 | Drive full history attributed files to the wrong client in the legacy path | Fixed (BF-8). Re-running a backfill never repairs old misfiles: use the repair script |
| O-5 | Gmail `attachmentId` changes on every fetch, which faked new versions | Never hash fetch-scoped fields (fixed, with a regression test) |
| O-6 | PDF text can contain NUL bytes, which PostgreSQL rejects | Fixed in `normalise_text` |
| O-7 | Calendar `updatedMin` is limited to about 3 weeks | Live sync must use `syncToken` (P-05) |
| O-8 | Archived ClickUp lists are mostly finished onboarding templates | Keep active clients' archived lists for history, but **never show their tasks as open actions** |
| O-9 | The ClickUp status-history ClickApp is off. The team works to do → done/complete; "in progress" is rare | The action model is Open → Done (+ Acknowledged). Mirror ClickUp's in-progress only where it's real |
| O-10 | One Fathom team key; client calls in the calendar outnumber recordings about 2:1 | The coverage report must show calls with no recording |
| O-11 | LeadLock-only clients mostly use hello@leadlockpro.com, which isn't connected | A known gap until that mailbox is connected |
| O-12 | Client sub-account leads in GHL return 401 for every token; WIA's own invoices are readable | Leads aren't a phase-1 source. Invoices only with admin and finance visibility |
| O-13 | Contracts and pricing were tagged as profile documents | A filename rule now tags them finance; production needs document classification (G-13) |

*(Add new findings here as they come up.)*

---

## 3. Phase 1 build: what has to exist before the Portfolio and Action Hub are live

| Stage | Status | Needed for phase 1 |
|---|---|---|
| S1 Access | ✅ (ClickUp sandbox edit pending WIA) | — |
| S2 Mapping | ✅ | WIA confirms the client list; the other 20 clients reactivated for production |
| S3 People | ✅ | WIA signs off owners and roles |
| S4 Engine | ✅ + §1 blockers | §1 |
| S5 Production backfill | ❌ (local learning run only) | §1 closed → staging dry run → production run |
| S6 Live sync | 🟡 the scheduler runs in the workers (6 Nov); switched on after the production backfills | A scheduler process on Railway; Calendar `syncToken`; 72 hours with p95 lag under 15 minutes. **Plus "Sync client now" (requested 6 Nov):** one on-demand action that brings every source of one client up to date. It works in both modes, because it isn't the scheduler. Quick = an incremental run on each of the client's own streams (Slack channel, ClickUp lists, Drive, LeadLock) and on the shared ones (hello@, calendars, Fathom). Full = re-read the client's own streams, plus a client-targeted read of the shared sources by the client's approved contacts, never a whole-mailbox read. It is the same read that re-qualifies history when a contact is approved later (P-02). It shows per-source progress, has a cooldown, and is exposed through `kb sync client <slug> [--full]`, an API and the client record / Connections |
| S7 Extraction | 🟡 built, off (6 Nov): `services/ai/`, four skills, prompts, checks, run log, budget | Switch on (`AI_MODE=live`, a budget, a `worker-ai`) after `kb ai preview` review; the 50-thread accuracy test |
| S8 Action model | ❌ | actions, history, review queue, commands, ClickUp write-back through the outbound guard |
| S9 Read models | 🟡 the portfolio is a live build (`read_model_snapshots`, `GET /api/v1/portfolio`), rebuilt after each copy | Split per tab when a rebuild passes ~30 s |
| S10 Login and visibility | 🟡 shared team password (6 Nov, interim) | Named Google sign-in, roles, account-team visibility, finance access; AI approvals wait for it |
| S11 API | 🟡 ops + ClickUp connect only | Client, action, review and coverage endpoints |
| S12 Outbound | 🟡 guard, approval and log built | Action Hub write-back and Slack notify through it |
| S13 Frontend | 🟡 MVP UI with static data | Cards wired to the API (§4) |

---

## 4. Next workstream: map the frontend cards to the backend

Before designing the S7–S9 tables:
1. **Compare** the current frontend (`frontend/src/views/*`) with the finalised MVP page (`mvp/real_index.html`). List what's new or changed:
   - **Action Register:** finalised.
   - **Client Portfolio:** still being designed. Note it as provisional.
2. **For every card and field:** where its data comes from (source, extraction, derived), and which table or read model will hold it.
3. **Check every card against the learning-run data:** what's missing, ambiguous or wrong in real data. Those are the resilience cases that future intakes must handle.
4. Only then design the extraction contracts and the S8/S9 tables.

**Done 4 Nov:** see `docs/mvp-card-to-data-map.md` for the MVP vs React differences, the element-by-element source map for both tabs, the extraction backlog, and the decisions needed.

**Done 4 Nov: the MVP's hand edits are now ported into `frontend/src`,** so the React app is the source again. A fresh `npm run export` matches `mvp/index.html` on visible text and DOM structure across 7 routes, and on the archive/pin, status menu, owner picker, Slack ping, internal item, drag-and-drop, history period and pagination flows. The Action Hub's shared pieces are in `src/mvpActions.tsx`. Archive, pin and brief stamps are still per-browser `localStorage` until S8–S10 exist.

---

## 5. Production infrastructure (manual deploys)

| Item | Status | Notes |
|---|---|---|
| Railway Postgres (production) | ❌ | Create it; the web service's pre-deploy `alembic upgrade head` builds the schema (same result as `schema.sql`). Turn on backups / PITR, rehearse a restore |
| Railway **web** service (API + portfolio) | ✅ in code (6 Nov): root `Dockerfile` builds the portfolio and serves it with the API | Runbook in `backend/README.md` ("Deploying to Railway"); health `/health/ready` reports schema, mode and AI |
| Railway **worker-bulk** service | ✅ in code, to create | Same image, start command `python -m backend.workers.runner --lanes bulk,maintenance`: full copies, full re-checks, discovery, LeadLock token/reconcile jobs |
| Railway **worker-sync** service | ✅ in code, to create | Same image, `python -m backend.workers.runner --lanes sync`: the small incremental reads, so a multi-hour Gmail copy never delays them. More than one of each adds little: a provider account runs one page at a time |
| Scheduler | ✅ in code (6 Nov) | No separate service: each worker calls `sync.sweep` every `SCHEDULER_SWEEP_SECONDS` (30) and a Postgres advisory lock lets one through. A sweep (3 queries when nothing is due) starts first copies for live sources nothing collects, resumes copies a mapping decision stopped, re-checks streams whose client was reactivated, and queues due incremental reads (every `SYNC_INTERVAL_SECONDS`=300; LeadLock every 6 h, Fathom only its daily re-check) and daily full re-checks (`RECONCILE_INTERVAL_SECONDS`). A stream is switched on when its first full copy finishes. Lock order everywhere: work item → run → stream → account → scope; due streams are taken `SKIP LOCKED`. `PRODUCTION_MODE=true` turns it on. Production starts with `SYNC_SCHEDULER_ENABLED=false` (backfills on command), then `true` on worker-sync only once they are done |
| AI worker (`analysis` lane) | ❌ deliberately | Built (6 Nov) with its monthly cap and pause (`AI_MODE`). Per-record `record.extract` jobs are gone; the AI sweep finds work. Create `worker-ai` only when switching the AI on |
| Staging | ❌ | A second Railway project for the dry run (BF items), with `OUTBOUND_MODE=off` |
| Secrets | ❌ | Move every `.env` value into Railway variables. `KB_SECRET_KEY` must be kept safe: losing it means everyone reconnects ClickUp. `OUTBOUND_MODE` stays `off` until it's deliberately set |
| ClickUp OAuth app | 🟡 | Add the production redirect URL; set `KB_APP_URL` and `CLICKUP_OAUTH_REDIRECT_URI` |
| Credential register | ✅ (outside the repo) | Update the "stored in" column to Railway |

---

## 6. Manual pre-deploy checklist (every push or redeploy)

1. `git status`: nothing under `backend/.local/`, no `.env`.
2. Tests: `backend/.venv/Scripts/python -m pytest backend/tests -q --basetemp=<writable temp dir>`. All pass (200 on 2 Nov).
3. New migration? → `alembic upgrade head` on staging first. If production is still empty, regenerate `schema.sql` instead (`python -m backend.scripts.schema_export`).
4. Privacy scan of changed files: no personal emails, Slack or ClickUp IDs in code, tests or docs.
5. After the deploy: `/health/ready` shows the expected schema revision; `kb outbound status` shows the intended mode.

---

## 7. "Ready" checklists

**Ready to run the production backfill**
- [ ] BF-1 to BF-7 closed
- [ ] Staging dry run: 2–3 clients, full history, run twice. The second run creates **zero** new versions
- [ ] A run killed mid-way resumes with nothing duplicated or skipped
- [ ] Induced 403 rate limits produce retries, not "inaccessible"
- [ ] Production Postgres has backups, and a restore was rehearsed
- [ ] The client list is confirmed and the 20 other clients are reactivated (or decided)

**Ready to deploy phase 1**
- [ ] Production backfill done; coverage report reviewed with WIA
- [ ] Live sync running for 72 hours, p95 under 15 minutes
- [ ] S7–S11 built for the Portfolio and Action Hub cards (§3, §4)
- [ ] Login and visibility tested per role, with no finance or other-team leakage
- [ ] `OUTBOUND_MODE` decided for production; approvers set
- [ ] WIA pilot with 2 account owners, then sign-off
