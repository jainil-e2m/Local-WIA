# The 12 November documents vs the implementation

**Checked:** 12 November 2026
**Documents:** `docs/SYSTEM_AUDIT_AND_GAP_ANALYSIS.md` (the audit) and `docs/SOLUTION_ARCHITECTURE.md` (the architecture)
**Implementation:** this folder on branch `mvp`. That is `origin/mvp` @ `1f63ef8` (4 Nov) plus 152 uncommitted changes made 5–12 November.

> Nothing in the code or the two documents was changed. Every mismatch below was traced to a file and line. The headline ones were re-checked by hand.

---

## 1. Why they differ

1. **Both documents describe the code as committed on 4 November** (`origin/mvp` @ `1f63ef8`). The audit says so (its header). The architecture builds on the audit.
2. **The work done since then was never committed or pushed.** That covers the scheduler wiring, Connections, the LeadLock app, the outbound guard, the shared team password, the live portfolio, the AI layer and the Railway image. It is 152 changed or new files that the authors could not see.
3. **The architecture is a redesign.** Several of its decisions conflict with things built between 5 and 12 November. §14.2, "what happens to the existing code", would remove some of them without knowing they exist.

So most of the gaps are not errors of reasoning. The documents and the code have different baselines. A few claims were wrong even on 4 November; they are listed in §2.2.

---

## 2. The audit

### 2.1 True on 4 November, no longer true

| Audit claim (section, line) | Now | Where |
|---|---|---|
| **F1 / §5.1 / §7.1:** no model call, prompt, retrieval or evaluation anywhere; extraction jobs are queued and never consumed | An AI layer is built and switched off: an OpenRouter client, 5 skills, 11 prompt files, output contracts, quote checks, a run log, a monthly budget, and a sweep in the worker. The per-record `record.extract` jobs are gone. **Still true:** no retrieval or search, no evaluation set, and the chat is a regex mock | `backend/services/ai/*`; migration `c09`; `config.py` `AI_MODE=off` |
| **F6 / §8.2:** zero Viktor references in the backend | Viktor's Slack posts are an input ("attributed analysis") to `meeting_digest` and `call_brief`. There is no Viktor API, credential or task | `services/ai/context.py` (`viktor_posts`); `skills.py:50,54` |
| **F4 / §5.4 / §7.1:** the backend stores full text for every source | Gmail is pointer-only (`gmail-v3`); the body is read from Gmail when needed. Slack, Drive and Fathom still keep text. Calendar and Fathom now keep pointers for unmatched items | `adapters/gmail.py:1-5,67`; `requalify.py` |
| **§3.3 / §5.6 / §10.3 / App A:** durable sync is unwired and imports a missing `rate_limits` module | Wired. The worker calls `sync.sweep`, and backfill, Connections and requalify use `sync.request_run`. The bad import is gone | `workers/runner.py:187,203-206`; `services/intake/sync.py` |
| **§3.3:** no product API, no sign-in, no AI call | `/api/v1/portfolio`, the clients and connections APIs, a shared team password, and the AI layer (off) | `app.py`; `routes/*.py`; `routes/access.py` |
| **§3.3:** deployment: none; no Railway config | A root `Dockerfile` builds one image for the web, worker-bulk and worker-sync services. There is a runbook | `Dockerfile`; `backend/README.md` "Deploying to Railway" |
| **§3.4 / §10.3:** the frontend makes no backend calls and has no data layer; connecting a backend means rewriting every view | The production build loads `/api/v1/portfolio` before rendering, and Connections and Leads call the API. No view had to be rewritten | `frontend/src/main.tsx`; `kb-live.runtime.ts` |
| **F7 / §5.8 / §5.9:** the MVP is hand-patched, can't be regenerated, and has screens not in React | The Action Hub and Slack ping were ported into React. The deployable product is now the React build behind a password. The old public MVP page still exists | `frontend/src/mvpActions.tsx`; `mvp/README.md` |
| **§3.5 / §10.1:** GoHighLevel client data needs a per-location OAuth app that isn't built | A LeadLock (HighLevel) Marketplace app is built: agency grant, per-sub-account tokens and webhooks. It isn't installed in production yet | `services/intake/leadlock_app.py`; `routes/leadlock.py`; migration `c07` |
| **App B AR-04 / AR-05:** no sign-in; outbound undesigned | Interim shared password. An outbound guard with approval and a log (Slack posts and DMs, ClickUp updates), default off | `routes/access.py`; `services/outbound/*`; migration `c06` |
| **§10.3:** Drive misattribution (inferred), untested readers, every 403 treated as access denied | Misattribution confirmed and fixed, with a repair script. Calendar and Fathom readers are tested. 403s are told apart | `pipeline.py` (`membership_scope`); `tests/services/test_pointers_and_recheck.py`; `shared/http.py` |
| **§3.3 / App C:** sizes | Backend about 7,600 → about 13,000 lines (not counting tests). Tests 103 → 243 functions (325 cases run). Tables 28 → 36. Migrations 5 → 10. Routes 5 → 24. CLI commands 15 → 24. New packages: `services/ai` (1,407 lines), `read_models` (887), `outbound` (444) | `models/db/*.py`; `sql/migrations/versions/` |
| **Header:** `main` @ `1326db9`; working tree clean | `main` is `692d2fa` (it carries these two documents). The checkout is `mvp` with 152 uncommitted changes | `git status` |

### 2.2 Wrong even on 4 November

| Audit claim | Fact |
|---|---|
| §3.2, App D: `knowledgebase_changes.md`, `backend_build.md`, `viktor_at_wia.md` and the source scope files were "not found on this machine" | They are on this machine, one folder above the repo: `Wedding_Industry_Ads/knowledgebase_changes.md`, `backend_build.md`, `WIA_Meeting_Analysis/viktor_at_wia.md`, and `slack_scope.md`, `gmail_scope.md`, `clickup_scope.md`, `fathom_scope.md`, `leadlock_scope.md`. The owner's O-14 later set them aside, but the "not found" basis was wrong |
| §10.3, App C #3: `--days` works for Slack and ClickUp only | Calendar honours it too, so it is 3 of 6 connectors (`readers.py:170-171`) |
| App C: `content_units` is read only by export and report scripts | It was read by `persist.py`, `admission.py` and `people/resolve.py` on 4 Nov. It is now also read by the AI context and the portfolio |
| App C: `sync_cursors` and `association_reviews` are written and never read | Both are read: `execution.py`, `pipeline.py`, and `persist.py` (deduplicating reviews) |
| §3.3: about 900 lines of sync code | `sync.py` + `execution.py` + `positions.py` are 542 lines now, and fewer on 4 Nov |
| §3.4: 54 technical notes | Numbered to 54, but 59 entries (34–38 repeat). Minor |

### 2.3 Still accurate

- **Documents and requirements:** the 21 October Solution Architecture is unchanged, with 171 requirement IDs in 18 areas and the TG/ARCH counts. The doc line counts and timeline dates are exact.
- **Not built:** no retention job (BF-7), no search or embeddings, no evaluation set, and the chat is a regex mock.
- **Unused or dead code:** `service_engagements` and `webhook_receipts` are never used; `audit_events` and `record_changes` are never read. The dead profile bypass, `version_hint` and Slack lookback findings still stand.
- **Source gaps:**
  - Dubsado mail is not admitted (BF-6).
  - ClickUp is read with a personal token.
  - The Gmail reader includes spam and trash.
  - The default database URL has a password.
  - Probe JSON and `mvp/real_index.html` are in git.
- **Command Center auth facts** match the code copy at `Wedding_Industry_Ads/frontend`. The audit's commit refs for that repo can't be checked: it isn't present as its own repo.

### 2.4 The seven headline findings, today

| # | Finding | Today |
|---|---|---|
| 1 | AI not started | **No longer holds.** Built, off, never run in production. "Answer quality unproven" still holds: no evaluation or search |
| 2 | Redefined as a system of record | **Holds** for the documents. The build adds a little state (`action_candidates` with approval) |
| 3 | One product became about seven | Holds |
| 4 | Retention and all-history-first work against a KB | **Partly.** Retention is still undecided. Gmail moved further from full text |
| 5 | Machinery sized for another system | Holds for the documents. The build runs one image as three services |
| 6 | Viktor in documents, not code | **Partly.** Viktor is in the code as a read-only context block |
| 7 | The MVP bypasses the architecture | **Partly.** The React build is the deployable path now. The old public page remains |

---

## 3. The architecture

### 3.1 Wrong about the existing code

| Architecture claim (section, line) | Fact |
|---|---|
| §6.5 (l.511), §14.1 (l.1440), §14.2 (l.1509), D-15: incremental sync is "about 900 lines, unwired". **Remove** | Wired and running in the worker loop. 542 lines. Connections, requalify and the runbook depend on it |
| §14.2 (l.1513): 12 tables are listed for removal | 10 of the 12 are in use: the sync tables, `audit_events` (used by 9 modules: outbound, ClickUp OAuth, LeadLock, config transfer and more), `account_team_members` (the AI context and name checks) and `mailbox_holders` (people resolution). Only `service_engagements` and `webhook_receipts` are unused |
| A.4 (l.1636), §14.1, §7.7: `ai_runs` is a new table | It exists, with different columns (`skill`, `skill_version`, `state`, `prompt_tokens`, `completion_tokens`, `refs`, `checks`, `is_current`; no `tokens_cached`). `action_candidates` also exists and is not mentioned (A.3 treats items as new) |
| §3.4, Appendix A: the existing tables are 16, kept | There are 36. Twenty are not mentioned anywhere: no keep or drop. These are listed in §3.1 below |
| §6.1 (l.446): Gmail is one record per message, with passages split into authored and quoted text | Gmail stores pointers only and keeps no passages. The body is read live |
| §4.3 (l.315): "PostgreSQL 17 … already in use", holding vectors | Compose runs `postgres:16`. There is no pgvector anywhere |
| §4.2 (l.305): the worker is `python -m backend.jobs.worker`, running on threads | It is `python -m backend.workers.runner`, one job at a time per process, with lanes (sync, bulk, maintenance, analysis) |
| A.1: `businesses` gets `services text[]` and `status` | `status` exists. Services live in `service_engagements` |
| A.1, §6.8: scope states are candidate/approved/excluded; add `synced_through` | There is also `retired`. `last_successful_sync_at` exists |
| §6.3: party values are wia/client/bot/third_party/unknown | internal, shared_mailbox, client, partner, automated, bot, unknown |
| §6.6: removed records are marked `removed`; there are no retention fields | `availability='deleted_upstream'`; `content_units` has `retention_category` and `retention_state` |
| §2.6, §6.1: GoHighLevel client data is blocked until an OAuth app exists | The LeadLock Marketplace app is built |
| §14.2 (l.1504): the `record.extract` enqueue becomes `read.conversation` | It was already removed. AI work runs as `ai.run` |
| §14.2 (l.1502): six connectors, about 1,700 lines | Seven (LeadLock included), 2,089 lines |
| §14.2 (l.1511), §10.4, §14.2 (l.1516): remove the snapshot export; the static MVP is not a build target | The export is now a 24-line wrapper around the live portfolio build, and production already reads `/api/v1/portfolio`. The deployable product is the React build served by FastAPI |
| §14.1 (l.1443): deploying web, worker and Postgres is future Phase 0 work | The image and runbook exist: three services from one `Dockerfile` |
| §11.3 (l.1238): no screen or template has a Viktor-specific element | `meeting_digest` and `call_brief` read `viktor_posts` |
| §11.2 (l.1223): the gateway "should start from" Content Atelier | Already done: `services/ai/openrouter.py` is lifted and trimmed from it |
| §12.2 (l.1277): `require_user` "today checks … role `team`" | No such function. `require_team` checks only that the shared-password hash is set. There are no users or roles |
| §14.3: of the tab scopes, only the parts on acknowledgement, verification and review are superseded | `kb_tab_scope/02-client-portfolio.md` holds 6 November decisions that §9.3 contradicts without saying so (16 fixed profile fields with five labels; History; Handover brief as a tab; Support). §14.3 also omits the documents written 5–12 November |

The 20 tables the architecture never mentions:
- **Registry and people:** `service_engagements`, `mailbox_holders`, `account_team_members`
- **Sync:** `coverage_windows`, `sync_cursors`, `sync_streams`, `scope_memberships`, `drive_nodes`, `association_reviews`, `webhook_receipts`, `record_changes`
- **Audit:** `audit_events`
- **ClickUp and outbound:** `clickup_connections`, `outbound_requests`
- **LeadLock:** `leadlock_installations`, `leadlock_locations`, `leadlock_app_events`
- **Read models:** `read_model_snapshots`
- **AI:** `ai_runs`, `action_candidates`

### 3.2 Where the proposed design and the current build differ

| Topic | Architecture proposes | Built today | Size to align |
|---|---|---|---|
| Sync | Hourly polling with an overlap, one `read(scope, since)`, no cursors (§6.5, D-15) | Durable streams and checkpoints. Incremental every 300 s, LeadLock every 6 h, Fathom daily, daily reconcile, and requalify | Large, or adopt the build |
| Full text | Everything, indefinitely (O-4) | Gmail is pointer-only (BF-2, 30 Oct). Calendar and Fathom keep pointers for unmatched items | Medium: store Gmail bodies, re-backfill, retire `fetch_body` and requalify paths |
| AI unit of work | 8 tasks. Read each conversation once (Slack day, email thread, meeting, document), then Reconcile, Compile, Brief, Recap, Answer (§7.4, D-06) | 5 skills: `meeting_digest`, `team_meeting_digest`, `call_brief`, `email_actions` (24 h batches), `history_moments` (weekly). Extraction sees the open actions in one step, which is the alternative D-06 rejects. Slack is not read for items | Large |
| Action items | Reconciled `items` plus `item_decisions` (done, not an action). Status worked out by query. No approval queue (§8.3, D-08) | `action_candidates`: proposed, approved, rejected, superseded. Approval waits for named sign-in | Medium |
| Model routing | Settings live in the OpenRouter account; a `provider` block only from configuration; fallback models (O-5, §7.3) | Zero-retention and no-collection routing hard-coded, `allow_fallbacks: False`, fails closed | Small code change, but it **loosens a privacy safeguard**: decide deliberately |
| Model tiers | Haiku ("fast") for Read; Sonnet for the rest | Sonnet for meeting digests, briefs and history; Haiku only for email | Small |
| Citations | Per-request handles `p1…`; reject the whole result if too many claims fail | Typed refs (`T`, `E`, `S`, `V`, `A`, `C`, `H`, `D`), word-order quote match. A failing item is dropped, or an action is flagged unverified | Small |
| Retrieval | pgvector, chunks, hybrid search, embeddings | None | Large (new) |
| Sign-in | Command Center PKCE hand-off, `sessions` table (O-15, §11.1) | Shared team password. The code comments plan named Google sign-in, which conflicts with O-15 | Medium |
| Outbound | None in phases 1–4. The KB never changes a task (D-23, §9.1) | Outbound guard for Slack posts and DMs and ClickUp status, due date and assignee edits (default off). "Post to Slack" button in the record | Medium (a policy call) |
| API and screens | `/api/items`, `/api/calls`, `/api/clients/{id}`; screens query stored rows (§10.2, §9.3) | `/api/v1/{ops,clickup,leadlock,clients,connections,portfolio}`. One whole-portfolio snapshot with an ETag, rebuilt by a job | Large |
| Worker | One lane, a thread pool, `WORKER_THREADS` (§10.3) | Four lanes; one job at a time per process | Medium |
| Services | Two: web and worker (D-26) | Three, plus an AI worker when switched on | Small |
| Client record | Six sections; the handover brief is a button; Support waits (§9.3) | Twelve tabs, including History, the Handover brief, Support, Leads, and Accounts & sources | Medium |
| Profile | 8 fields labelled fact, interpretation or suggestion (§8.5) | 16 fixed fields with WIA's five source labels | Small |
| Call types | `brief_templates` editable in Settings, plus a `classify_call` model task | Title regex copied from the frontend templates | Small–medium |
| Brief timing | 24 h ahead, rebuilt at 2 h | 36 h ahead, rebuilt in the last 2 h if stale | Small |
| Budget | A monthly ceiling stops background jobs; interactive calls continue (§7.9) | `AI_MONTHLY_BUDGET_USD` reserves the worst case before every call and waits 6 h | Small |
| Viktor | No role | Viktor's posts are a cited context block | Small |
| LeadLock leads | Not covered | Marketplace app, leads read model, Leads tab | Medium (add to the doc) |
| Frontend | `features/` folders, generated types, TanStack Query, path routes | Hash routes, plain `fetch`, module datasets filled from the API | Large |
| Database | PostgreSQL 17 with pgvector | PostgreSQL 16, no vectors | Small (version), large (vectors) |
| Health check and settings | `/api/health`; `AI_MONTHLY_CEILING_USD`, `WORKER_THREADS`, `SESSION_SECRET` | `/health/live`, `/health/ready`; `AI_MONTHLY_BUDGET_USD`, `WORKER_LANES`, `KB_TEAM_PASSWORD_HASH`, `OUTBOUND_MODE`, `AI_MODE` | Small |

**Already aligned:**
- Results are reused by prompt version and input hash.
- Output is strict JSON schema, validated in code, with one repair.
- There is one owned OpenRouter module.
- Counts and dates come from queries.
- The KB drafts and people approve.

### 3.3 What §14.2 would break if followed as written

- **Removing the sync code and the sync tables** stops scheduled production sync, and breaks Connections, requalify and the runbook.
- **Dropping `audit_events`, `account_team_members` and `mailbox_holders`** breaks outbound auditing, LeadLock, config transfer, the AI context and people resolution.
- **"Remove the snapshot export" and "the static MVP is not a build target"** aim at the wrong thing. The runtime snapshot is how the deployed portfolio loads, and the MVP page is no longer the product.
- **The proposed AI module and API** would replace finished, tested work without a keep-or-remove decision: five skills, `action_candidates`, the portfolio route and the leads model.

---

## 4. Decisions the owner needs to make

The documents and the code disagree on these. Each needs one answer before more is built:

| # | Question | Documents | Code |
|---|---|---|---|
| 1 | Keep the durable sync, or replace it with hourly polling? | Replace (D-15) | Built and wired |
| 2 | Full email text, or pointers? | Full text forever (O-4) | Pointers (BF-2, 30 Oct) |
| 3 | AI shape: 8 conversation tasks, or the 5 built skills (adjusted)? | 8 tasks | 5 skills |
| 4 | Do action proposals need approval? | No queue (D-08) | Approve or reject, after named sign-in |
| 5 | Zero-retention routing on or off? | Team settings decide (O-5) | Forced on |
| 6 | Outbound in phase 1? | None (D-23) | Built, off |
| 7 | Sign-in: Command Center hand-off or Google? | Command Center (O-15) | Shared password now; Google planned |
| 8 | Client record: six sections, or the twelve tabs defined on 6 November? | Six (§9.3) | Twelve (`kb_tab_scope/02`) |
| 9 | Viktor's posts as cited context? | No role | Used |

A separate risk: the 5–12 November work exists only on one machine. Until it is committed and pushed, any review will keep auditing the 4 November code.

---

## 5. Method and limits

- **How it was checked.** Four independent reviews, each split by document section, plus a hand check of the headline items. Each claim was compared with `origin/mvp` @ `1f63ef8` and with the working tree on disk. Line numbers refer to the documents as committed in `692d2fa`.
- **Not checked:**
  - anything deployed or live on Railway;
  - live OpenRouter prices. The architecture's figures are $0.10/$0.50 and $2/$10 per million tokens. The code's cost caps assume about $1/$5 and $3/$15, so the §13.1 backfill estimate may be about ten times low;
  - frontend behaviour line by line against §9;
  - the audit's probe volumes other than the invoice count.
- **Test count.** The 243 is test functions found by grep; 325 cases run when parametrized cases are included.
