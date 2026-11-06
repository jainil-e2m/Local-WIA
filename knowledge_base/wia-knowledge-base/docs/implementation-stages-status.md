# Implementation stages: plan vs where we are

Written 4 Nov 2026. It compares the 14-stage plan (29 Oct, the shared stage doc, text in the 30 Oct chat export) with the code and data as they are today. It covers the path to getting the **Client Portfolio and the Action Hub** (formerly Action Register) into production.

> Repo file: no client names or personal data. Real figures stay in `backend/.local/`.

**Where we are: still Stage 4.** Stages 1–3 are done to their exit criteria, except items that wait on WIA. Two later pieces were built early:
- the outbound guard (part of Stage 12);
- the React port of the MVP (part of Stage 13).

None of Stage 4's exit tests have been run, and nothing in Stages 5–11 exists. The deployed MVP is a static page made from a snapshot plus hand-written overlays. It is not Stage 13.

---

## 1. The plan in one view

```
A Ingestion   1 Access → 2 Mapping → 3 People → 4 Engine → 5 Backfill → 6 Live sync
B Knowledge                         4's dry-run data → 7 Extraction → 8 Actions → 9 Read models
C Backend     3 → 10 Users & visibility → 11 API → 13 Frontend wired      8 → 12 Outbound
E Launch      14 (gap report signed, pilot, monitoring, training)
```

The stages say *what* has to exist; dates are separate. Stages 10, 11 and 13 can be built against fixtures while 4–6 run. Stage 8 can start on ClickUp-only data before Stage 7.

## 2. Status by stage

Status: ✅ done to exit criteria · 🟡 partly · ❌ not started.

| # | Stage | Plan's "done when" | Status 4 Nov | What's actually there | What's left |
|---|---|---|---|---|---|
| 1 | Source access | Every connector verifies as the expected WIA identity; scopes recorded; credential register filled; secrets in Railway | 🟡 | Google OAuth (Internal, hello@ only), WIA AI BOT Slack app (11 scopes), ClickUp read key, Fathom team key, per-user ClickUp OAuth app, credential register (outside the repo) | ClickUp sandbox write test (waits on a WIA list); secrets into Railway; **GHL: lead scopes missing, one token now invalid, GHL absent from the credential register** (§4) |
| 2 | Client and source mapping | Every active client mapped in every applicable source; "not applicable" explicit; WIA confirms the client list | 🟡 | Mapping command service with audit + revisions, discovery filters, sender rules, archive pauses sync | 11 mapping gaps; WIA to confirm the client list and whether the 20 paused clients return; past clients undecided |
| 3 | People and roster | Every author resolves to a person or the unknown queue; contractors internal; every client has an owner and team | 🟡 | Tables, resolution across 4 providers, bots as a party, roster validated | **No owner or team is confirmed** (suggestions only; one pilot client has none). WIA sign-off |
| **4** | **Ingestion engine, production-ready** | Second full run creates zero new versions; a killed run resumes; induced 403s retry, not "inaccessible"; inventory numbers exist; WIA closes the freeze list | **🟡 current** | Adapters for 6 providers, versioned units, atomic page publication, Drive attribution and Sheets fixes | See §3: BF-1/2/3/6 open, **the resume path crashes** (missing module), no inventory/coverage command, extraction enqueue still on, no staging dry run, freeze list open |
| 5 | Production backfill + gap report | Every approved scope complete or gaps listed; draft gap report with WIA; one restore succeeded | ❌ | Only a local learning run (Gmail stopped at ~55%) | Everything; blocked by Stage 4 |
| 6 | Live sync | 72 h running, p95 lag < 15 min; deletions seen; expired cursor recovers | 🟡 code only | `sync.py`, incremental readers, `resume()` (committed) | Scheduler loop (nothing calls `sweep`), Calendar `syncToken`, deletion handling, streams created disabled |
| 7 | Extraction (AI) | 100% valid citations; no invented owner/date; action precision ≥ 0.8; cost projected; re-run stable | ❌ | Gold set = the hand-written overlays (4 clients) | Contracts, planner, LLM client with cap, quote verification, 50-case eval |
| 8 | Action domain | Replay gives same state; concurrency tests pass; review load fits WIA | ❌ | Rules exist only in the frontend TypeScript; model decided: Open → Done + Acknowledged | Schema, history, review queue, reducer (ClickUp ∪ extracted), commands, archived-template exclusion |
| 9 | Client record assembly | Rebuild = incremental; p95 < 1 s for 10 users; no finance leakage | 🟡 prototype | `export_frontend_snapshot.py` + `build_real_index.py` overlays | Read models in the DB. Most Portfolio/record cards need no AI (`docs/deterministic-vs-ai-card-map.md`) |
| 10 | Users, access, visibility | Per-role tests pass; no cross-team or finance leakage | ❌ | Ops token only | KB login (Command Center hand-off or Google), roles, account-team visibility, finance restriction |
| 11 | API | Contract tests pass; every change revision-checked | 🟡 | Ops endpoints (`/connectors`, `/scopes`, `/runs`) and ClickUp connect | Client, action, review, coverage, search, citation endpoints; `allowed_actions`; generated TS client |
| 12 | Outbound | Staging never sends; no double posts; failed write reverts visibly | 🟡 guard | Draft → typed-yes approval → send-once; modes; kill switch; Slack sandbox tested | Wire Action Hub write-back and Slack notify through it; "pending sync" + echo suppression; ClickUp sandbox test; decide one-click "Ping on Slack" vs approval |
| 13 | Frontend integration | Every Stage-1 screen on live data; Playwright per role; TS presentation-only | 🟡 UI only | React is again the single source (MVP edits ported 4 Nov, verified); deployed static page with real data | API client replacing `data.ts`/`records.ts`/`kbLive.ts`; real session; archive/pin/brief stamp off localStorage |
| 14 | Launch readiness | FS §10 / SA §11.5 gates pass; WIA signs off | ❌ | — | Signed gap report, eval on production data, 2-owner pilot, monitoring, backups, restore drill, training |

### How the plan changed since 29 Oct (decisions that altered stage content)

| Stage | Planned | Decided instead |
|---|---|---|
| 1 | Dedicated KB Slack app; a WIA ClickUp integration user for writes | Reuse WIA AI BOT; each user's own ClickUp OAuth token, no fallback |
| 4 | P-01: store Gmail metadata for every message | BF-2: email stored as a pointer (IDs, subject, from/to, date, client + reason); bodies fetched on demand |
| 5 | All active clients | Pilot of 4; the other 20 paused in dev |
| 8 | Lifecycle with in-progress / blocked / verified | Open → Done + Acknowledged |
| 12 | Send after a person presses Send | Every send needs a listed approver's typed "yes" |
| infra | Railway with PITR | No CI, manual deploys; production schema from one SQL file |

## 3. Stage 4 exit checklist, checked against the code (4 Nov)

| Exit item | State | Evidence |
|---|---|---|
| Uncommitted work committed | ❌ | 32 modified + 16 new files on branch `mvp` |
| **`rate_limits` import fixed** (named in the 29 Oct plan) | ❌ **still broken** | `services/intake/execution.py:103` imports `backend.services.intake.rate_limits`; the module doesn't exist. Every real page on the **resumable sync path** raises before fetching. Tests pass because fake adapters have no `http` attribute |
| BF-1: Google 403 rate limits retried | ❌ | `services/shared/http.py:89` maps every 403 to scope denied |
| BF-2: email pointers | ❌ | Gmail still stores body units |
| BF-3: contact query batching | ⚠️ re-check | The backfill reader lists the whole mailbox; no contact query on that path |
| BF-4: resume a stopped run | ❌ in practice | `kb backfill` uses the legacy path (no resume); the sync path has `resume()` but no CLI and the import bug above |
| BF-5: parser-version fingerprint test | 🟡 | — |
| BF-6: Dubsado sender rule | ❌ | — |
| BF-7: retention rule | 🟡 waits on WIA | — |
| BF-8 / BF-9 | ✅ uncommitted | Drive attribution, Sheets range, calendar status |
| Extraction enqueue off for the backfill | ❌ | `pipeline.py:140` and `execution.py:186` still queue `record.extract` |
| `kb inventory` / coverage report | ❌ | No such commands; `kb report` covers per-client counts only |
| Re-derivation jobs (reclassify / requalify) | 🟡 | Requalify on reactivation only |
| Staging dry run, run twice, zero new versions | ❌ | No staging project |
| WIA freeze list closed | ❌ | Mailboxes, retention, history floor, roster, credentials |

## 4. GHL access, verified 4 Nov (read-only probe)

One GET per scope, per token, against WIA's own location and one client's LeadLock sub-account. Evidence kept locally, not in the repo.

| Token | Valid | Readable | Not readable |
|---|---|---|---|
| `GHL_PIT` (WIA location) | ❌ **"Invalid Private Integration token"** — revoked or deleted since 20 Oct | — | — |
| `GHL_FINANCE_PIT` (WIA location) | ✅ | location, **contacts (1,789)**, campaigns, invoices (352), invoice schedules (53), transactions (397), subscriptions (5), orders (12) | opportunities, pipelines, conversations, calendars, forms, surveys, custom fields, users, products, workflows. Any other location: "not accessible from this token" |
| `GHL_AGENCY_PIT` (agency) | ✅ | agency location search (59 sub-accounts), company, single location profiles | every sub-account feature scope (contacts, opportunities, conversations, calendars, …): "not authorized for this scope" |

**Two different "leads":**
1. **WIA's own leads** (prospects for WIA's services), in WIA's location: add read scopes to `GHL_FINANCE_PIT` (Private Integrations lets you edit scopes without a new token): `opportunities.readonly`, `conversations.readonly`, `calendars.readonly`, `calendars/events.readonly`, `forms.readonly`, `surveys.readonly`, `locations/customFields.readonly`. Contacts are already readable.
2. **Clients' leads** (couples inquiring with each venue), in each client's LeadLock sub-account: a WIA-location token can never reach them. Options, in order to try:
   - ~~Add the lead scopes to the agency Private Integration~~ **ruled out 4 Nov.** Its edit screen offers only 24 agency-level scopes: companies, locations, SaaS, snapshots, users, custom menu links, marketplace installer details, Twilio, phone numbers, number pools, Documents & Contracts and ad publishing. It offers no contacts, opportunities, conversations, calendars, invoices or payments scopes. The agency integration ("Client Knowledge Base", created 19 Oct) stays a discovery token: `companies.readonly`, `locations.readonly`, and optionally `saas/company.read` + `saas/location.read` for the LeadLock SaaS subscriptions;
   - a read-only Private Integration **created inside each client sub-account** (fast for 4 pilots, manual for 59);
   - one **private Marketplace OAuth app** (Target user: Sub-Account, installed by the agency), exchanging the company token for a location token per client (`verification/leadlock/access_test_plan.md`). It scales, but needs an OAuth callback and token refresh in the backend.

**Chosen 4 Nov: the private Marketplace app**, because clients come and go and nobody should configure anything per client. Status:
- **App created** in the developer portal: "WIA Client Knowledge Base", Private, Target User Sub-Account, Agency only, White-label, 19 read-only scopes. Redirect URL `http://localhost:8010/api/v1/leadlock/oauth/callback`; HighLevel refuses URLs containing "ghl".
- **Backend built:** install callback, signed webhooks, encrypted token storage with safe rotation, a per-sub-account token job, reconcile, and the `kb leadlock` CLI. Migration `c07a20261104`; 21 tests.
- **Installed 4 Nov (local callback):** agency grant stored, 19 scopes, **auto-install on new sub-accounts: on** (confirmed by HighLevel). 59 sub-accounts listed, **57 tokens minted**. The other 2 are refused by HighLevel as "Location is not active" (paused sub-accounts).
- **Verified on a pilot client's sub-account** (read-only, counts only): contacts, opportunities and pipelines, conversations, calendars, form submissions, custom fields all return data. Surveys, invoices, transactions and products return 200 with no records for that venue.
- **Adapter built 4 Nov** (provider `leadlock`, scope = sub-account, metadata only; no couple names, emails, phones, message text or free-text answers).
  - Real backfill of one pilot client: 733 records in 39 pages, no gaps (255 contacts, 155 opportunities, 237 conversations, 37 form submissions, 49 appointments). A re-run came back all unchanged.
  - 11 adapter tests; full suite 247 passing.
- **Not done yet:**
  - a webhook URL once the API is deployed (until then `kb leadlock reconcile` picks up new sub-accounts);
  - ~~map the other pilot clients' sub-accounts~~ **done 4 Nov.** All 5 pilot sub-accounts (4 clients; one client has two) are mapped and backfilled: about 10,400 records, 0 gaps, 0 records on more than one client, 0 emails or phone numbers stored;
  - **Leads tab built 5 Nov** (client record > Leads, local only):
    - KPI row: inquiries, tours booked, upcoming tours, awaiting reply, won;
    - charts: 12-month inquiries vs tours, outcomes, pipeline stages in LeadLock order, sources, channels, forms, tours;
    - data: `GET /api/v1/clients/{slug}/leads`, run with `npm run dev:wia` and kb-api; 7 read-model tests.
    - Funktastic's "250 unread" was mostly stale: over 90 days it's 71 waiting, with 181 older threads never opened in LeadLock.
  - **lead outcomes need per-client definitions** before they're shown. Two of four venues never close opportunities: one has 1,072 open, 0 won, 0 lost; another 191 of 196 open. So "won" by status means nothing for them. Stage names, or WIA's own rule per venue, must define booked (KB-V-03);
  - an incremental mode (each run re-reads the sub-account, which is cheap at current volumes);
  - WIA's own sub-account (WIA billing its clients) needs per-invoice client matching before it replaces `GHL_FINANCE_PIT`.

Lead data is not a phase-1 source today (O-12). Adding it is a Stage 1 change, and for client leads a new adapter in Stage 4.
