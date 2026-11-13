# Client Knowledge Base v1: how it works in production

**What this is.** The single description of the first production version of the WIA Client Knowledge Base (KB): what it does, where its data comes from, how clients are mapped, how data is stored, how it stays in sync, how it is deployed, and every decision behind it. It is written so someone new can understand how the system will behave in production without reading the code.

**Status:** started 6 Nov 2026. A living document: update it as items are built or decided. Sections marked *To be detailed* are deliberately short until the technical work is done (worker setup §11.10, DB schema §7.6, backfill procedure §12).

> **Repo file:** no client names, staff names, personal addresses or provider IDs. Pilot clients are "the pilot clients". Real figures stay in `backend/.local/`.

**Legend used throughout**

| Mark | Meaning |
|---|---|
| ✅ | Built (may be uncommitted; see §19) |
| 🟡 | Partly built |
| ❌ | Not built |
| ⏳ | Waiting on a WIA decision or action |
| **DET** | Deterministic: a fixed rule over stored data, no AI |
| **PROV** | Text written by the provider (e.g. Fathom's own summary), shown as-is and labelled |
| **HUMAN** | A person sets or confirms the value once |
| **AI** | Needs the KB's own LLM step (S7). **Not in v1**: AI comes after v1 |
| **Soon** | Shown in the UI as "Coming soon"; not in v1 |

**Companion documents**

| Topic | Document |
|---|---|
| Production tracker (blockers, checklists, infrastructure) | [`backend/docs/production-readiness.md`](../backend/docs/production-readiness.md) |
| Every card mapped to its data source | [`docs/mvp-card-to-data-map.md`](mvp-card-to-data-map.md) |
| What each card can show without AI | [`docs/deterministic-vs-ai-card-map.md`](deterministic-vs-ai-card-map.md) |
| 14-stage plan vs status | [`docs/implementation-stages-status.md`](implementation-stages-status.md) |
| Intake design | [`docs/Ingestion-Pipeline-Design.md`](Ingestion-Pipeline-Design.md) |
| Backend setup and CLI | [`backend/README.md`](../backend/README.md) |
| Known test shortcuts | [`backend/before_production.md`](../backend/before_production.md) |

---

## 1. What v1 is

WIA is an ad agency for wedding venues and vendors. Everything about a client is spread across Slack, ClickUp, the shared hello@ mailbox, Google Drive and Calendar, Fathom call recordings and the client's LeadLock (white-labelled HighLevel) sub-account. The KB pulls it together into one record per client and one list of what is owed by whom.

**v1 = the Client Portfolio and the Action Hub, live on real data, kept up to date automatically.**

| In v1 | Not in v1 |
|---|---|
| Client Portfolio (all clients, cards and list) | Overview dashboard (Soon) |
| Client record with its deterministic tabs (§13.2) | Call preparation / call briefs (Soon, AI) |
| Action Hub (what we owe / what the client owes) | Health & sentiment (Soon, AI) |
| Leads tab (LeadLock), once per-venue "booked" is defined | Client 360 (Soon) |
| Connections and Accounts & sources (mapping) | Invoices & contracts (Soon) |
| Operations review queue for unmatched items | Anything that needs the KB's own AI (profile facts, decisions, curated milestones, sentiment, commitments found in calls/email) |
| Automatic sync from every source, plus "Sync client now" | Zoom transcripts (blocked, §4.9) |
| Login, roles and per-team visibility | Writing anywhere except through the outbound guard (§15) |

**Who uses it:** WIA admins, the operations lead(s) who handle mapping and unmatched items, account team members (owners, ads specialists), and finance (admin-only data). See §16.

---

## 2. Decisions log (settled; don't re-ask)

| Date | Decision |
|---|---|
| 29 Oct | Finish source access (S1) before moving on. No separate dev Slack app: test through the outbound guard's sandbox mode |
| 29 Oct | ClickUp write-back uses **each person's own ClickUp OAuth token**, with no fallback to a shared account |
| 29 Oct | **Admins map clients in the UI.** YAML is a dev bootstrap only. **Archiving a client pauses its sync.** Past clients are not backfilled |
| 30 Oct | **Email is stored as a pointer, not a copy** (IDs, headers, labels, attachment names, a fingerprint, client and reason). The body is read from Gmail on demand. Each action keeps only its evidence quote. **Built 4 Nov (BF-2)** |
| 30 Oct | The AI step runs as a **batch over everything since the last run, on an admin-set interval**. Deferred until after v1 |
| 30 Oct | The permission to file a new sender (client / partner / blocked) is **granted per user**. Prospects and accelerator members are in scope |
| 2 Nov | **Nothing reaches Slack or ClickUp unless an approver types "yes" for that exact request** (outbound guard) |
| 3 Nov | Pilot = **4 clients**. History shows curated milestones, not a raw message dump. **No dollar amounts in history** |
| 4 Nov | The production schema comes from **one SQL file** (`backend/sql/schema.sql`), applied once to the empty production database; later changes are migrations. **No CI**: deploys are manual and tests are run by hand. The backfill done so far was a local dev learning run |
| 4 Nov | The React app is the single frontend source (the MVP's hand edits were ported back) |
| 4 Nov | Google rate-limit 403s are retried, not recorded as "access denied" (**BF-1, built**) |
| 4 Nov | LeadLock is read through **one private HighLevel Marketplace app installed by the agency**, with a token per sub-account. Metadata only, no couple personal data |
| 5 Nov | **Mapping happens in the UI:** Connections (source side) and each client's Accounts & sources tab (client side), both calling the same mapping commands. A **dedicated** source is never read until it is mapped. **Shared** sources are read account-wide and attach to a client only through approved contacts |
| 5 Nov | **`PRODUCTION_MODE` is the one switch** between local (on demand, scheduler off) and production (scheduler on, local-only routes closed, unsafe settings refused). **Built** |
| 5–6 Nov | **The sync scheduler runs inside the worker**, not as a Railway cron job |
| 6 Nov | **"Sync client now"**: an on-demand action, in both modes, that brings every source of one client up to date. Quick and Full depths |
| 6 Nov | **Shared sources keep a pointer for every item.** Linking to clients is a re-runnable rule pass over stored pointers; anything uncertain is only suggested |
| 6 Nov | **Operations review queue** for unmatched items: suggestion, override, decisions apply where they belong, audited and reversible |
| 6 Nov | **A Full client re-check freezes that client's mapping and holds its outbound**; reading stays open. **Action edits stay open**; conflicting fields become "Sources disagree" items for an approver afterwards |

Open decisions are in §20.

---

## 3. The system at a glance

```
 PROVIDERS (read-only)                    KB BACKEND (Railway)                                  PEOPLE
 ─────────────────────                    ────────────────────                                  ──────
 Slack  ClickUp  Gmail(hello@)            worker (sync lane)  ◄─┐  scheduler thread              admins
 Drive  Calendar  Fathom  LeadLock  ───►  worker (bulk lane)  ◄─┤  (sweep every 30 s,            ops lead
                                              │  pages         │   one leader via PG lock)      account team
                                              ▼                │                                finance
                                     ┌──────────────────────────────────────────┐
                                     │ PostgreSQL                               │
                                     │  registry & mapping  (clients, contacts, │
                                     │                       scopes, rules)     │
                                     │  source layer  (records, versions,       │
                                     │                 units, pointers)         │
                                     │  links  (record ↔ client, with basis)    │
                                     │  sync state  (streams, runs, coverage)   │
                                     │  work queue  (jobs, leases)              │
                                     │  later: actions, read models, AI facts   │
                                     └──────────────────────────────────────────┘
                                              ▲
                                              │ read models (DET, computed from stored data)
                                     api (FastAPI)  ◄──── /api ────  frontend (React, same origin)
                                              │
                                     outbound guard ──(typed "yes")──► Slack post / ClickUp edit
```

**Principles**
1. **Read-only intake.** Every provider credential is read-only, except per-person ClickUp tokens and the Slack bot's `chat:write`, which are only usable through the outbound guard.
2. **Store cleaned data, never raw payloads.** Provider responses are normalised into records, versions and citable text units. Email bodies and LeadLock personal data are never stored.
3. **Every item is accounted for.** A run records what it saw, stored, skipped and could not read (coverage). Gaps are visible, never silent.
4. **Deterministic first.** v1 shows only what fixed rules, providers or people can establish. AI comes later.
5. **One place per rule.** Mapping commands, admission rules and the outbound guard each live in one module that the CLI, API and UI all call.

---

## 4. Sources

### 4.1 Summary

| Source | WIA's use | Credential (identity) | Kind | Unit mapped to a client | What is stored | v1 status |
|---|---|---|---|---|---|---|
| **Slack** | Internal team discussion per client (clients are never in Slack) | Bot token of the existing internal app "WIA AI BOT" | Dedicated (client channels) | Channel | Messages and thread replies, text, author | ✅ adapter |
| **ClickUp** | Tasks, onboarding checklists | Read: personal API key of the E2M AI member account. Write: each person's OAuth token | Dedicated | List (folders in client spaces) | Tasks: name, status, due, assignees, custom fields (`Role`, `Phase`), description | ✅ adapter |
| **Gmail** | The shared hello@ mailbox | Google OAuth refresh token for hello@ | Shared | Contact (email or domain) | **Pointer only** (§4.4) | ✅ adapter, pointer built |
| **Google Drive** | Client folders: questionnaires, brand files, contracts, call recordings | Same Google OAuth (hello@) | Dedicated | Folder | File metadata; text of Docs, Sheets, PDFs, DOCX, text transcripts; images/video as metadata | ✅ adapter |
| **Google Calendar** | Team calendars with client calls | Same Google OAuth | Shared | Contact | Events: title, time, attendees, organiser, recurrence, conference link | ✅ adapter (non-client events dropped today, §8) |
| **Fathom** | Call recordings (recent calls) | Team-plan API key (covers every WIA user) | Shared | Contact | Recording metadata, Fathom summary, action items, transcript segments | ✅ adapter (non-client meetings dropped today, §8) |
| **LeadLock** | Each client's lead management (couples' inquiries, tours) | Private Marketplace app: agency grant + a token per sub-account | Dedicated | Sub-account | Metadata only: pipelines, contacts, opportunities, conversations, form submissions, appointments, invoices, transactions. **No names, emails, phones, message text or free-text answers** | ✅ adapter, 5 pilot sub-accounts backfilled locally |

Not connected in v1: Zoom (transcripts), WIA's own GHL billing (invoices, Soon), staff personal mailboxes, the separate LeadLock support mailbox. See §4.9.

### 4.2 Slack
- **App:** the existing internal app "WIA AI BOT" (renamed from "Content Atelier"). 11 scopes: 7 read scopes plus `users:read.email`, `chat:write`, `im:read`, `im:write`. As an internal (customer-built) app it keeps Slack's higher API limits.
- **What it reads:** each approved channel's full history (messages, thread replies, edits, deletions on re-scan). Attachments are referenced, not downloaded.
- **Who's in it:** WIA staff and bots only. The whole team is in every channel and account teams rotate, so **channel membership never decides who may see a client** (§16).
- **Mapping:** a channel whose name matches a client is suggested; an admin links it. Programme channels (accelerators) mix clients and are excluded (G-07).
- **Writes:** posts and DMs only through the outbound guard (§15).

### 4.3 ClickUp
- **Read:** the E2M AI member account's personal API key (`CLICKUP_TOKEN`, `CLICKUP_TEAM_ID`). Limit: 100 requests/minute per token on WIA's plan.
- **Client spaces:** `CLICKUP_CLIENT_SPACES` lists the spaces where each folder is one client; every folder there is proposed for mapping even before a client matches it.
- **Archived lists:** active clients' archived lists are kept **for history only** and **never shown as open actions** (they are mostly finished onboarding templates, O-8).
- **Fields that matter:** `Role` (whose task: WIA or Client) and `Phase` (onboarding phase) custom fields, status, due date, assignees. Priority is used on ~0% of tasks; status history is off; the team works "to do → done".
- **Write-back (per person):** each KB user connects their own ClickUp through WIA's ClickUp OAuth app. Tokens are encrypted with `KB_SECRET_KEY`. Edits are limited to status, due date and assignees, never "Closed", and always go through the outbound guard. A user who hasn't connected cannot edit ClickUp from the KB.

### 4.4 Gmail (hello@)
- **Connection:** an OAuth client in WIA's Google Cloud project "Client Knowledge Base", **Internal** audience (tokens don't expire). Read-only scopes. hello@ is the only connected mailbox.
- **Pointer storage (BF-2, `gmail-v3`):** for **every** message in hello@ the KB stores message and thread IDs, the RFC Message-ID, subject, from/to/cc, dates, labels, attachment names and types, and a SHA-256 fingerprint of the body. **No body text is stored.** A changed body still creates a new version, through the fingerprint.
- **Reading a body on demand:** `GmailAdapter.fetch_body` (CLI: `kb email <message-id>`). Client emails only; nothing is saved. Deleted emails show "no longer available in Gmail".
- **Linking to a client:** only through approved contacts and the rules in §8. About 71% of hello@ is automated (platforms, newsletters); bulk mail never qualifies a contact.
- **Finance mail:** Dubsado notifications carry no client address; they need a sender rule (BF-6, ❌).
- **Limits:** 250 quota units per second per user; `messages.get` costs 5, `history.list` 2. Rate-limit 403s are retried (BF-1).

### 4.5 Google Drive
- **What it reads:** every file in approved client folders (one approved folder covers its subfolders). Text is extracted from Google Docs (by heading), Sheets (rows labelled with headers, up to 5,000 rows per tab, then marked partial), PDFs (per page), DOCX and plain-text transcripts. Images and videos are metadata only (no OCR, no transcription).
- **Tagging:** contracts, agreements, proposals, packages and pricing files are tagged **finance** (admins only). Questionnaires can hold sensitive answers (tax IDs, credentials, banking): those must be excluded before anything reaches a profile (G-14).
- **Call recordings:** client folders hold dated meeting videos (`YYYY-MM-DD - title - Recording`), some transcripts and summary docs. They join meetings by date (§13.2 Meetings).
- **Sync:** Drive's changes feed (one per shared drive plus My Drive); the stream is account-wide and routes each file to the approved folder it sits in.

### 4.6 Google Calendar
- **Approved calendars:** hello@ and the team members' calendars WIA approved.
- **What it reads:** events with recurrence (series and occurrences), attendees, organiser, conference link, status (cancellations kept).
- **Linking:** an event belongs to a client when an attendee is an approved contact; occurrences follow their series. Titles never decide (they only suggest).
- **Sync:** Calendar `syncToken` (Calendar's `updatedMin` only reaches back ~3 weeks). A 410 means the token expired: a full re-read follows automatically.

### 4.7 Fathom
- **Key:** one team API key covers every WIA user's recordings.
- **What it reads:** recordings, invitees, Fathom's own summary and action items (shown labelled "by Fathom", PROV), transcript segments.
- **Coverage reality:** client calls in the calendar outnumber recordings about 2 to 1, and older calls were recorded on Zoom. The coverage report shows calls without a recording.
- **Limits:** 60 calls/minute; summary and transcript calls are heavier (≈30/minute). Fathom's webhook fires once per new meeting and never again.

### 4.8 LeadLock (HighLevel sub-accounts)
- **App:** private Marketplace app "WIA Client Knowledge Base" (Target user: Sub-Account, installed by the agency, white-label, 19 read-only scopes). Auto-install for new sub-accounts is on.
- **Tokens:** one agency grant; a token is minted per sub-account. The agency refresh token **rotates on every refresh**, so it is refreshed under a row lock and stored at once. **Dev and production cannot share one grant**: production needs its own install, redirect URL and webhook URL (§17).
- **Webhooks:** `POST /api/v1/leadlock/webhooks` (signed, Ed25519) handles install/uninstall of sub-accounts. Until the API is deployed, `kb leadlock reconcile` picks up new sub-accounts.
- **What it reads, per sub-account, in phases:** pipelines → contacts → opportunities → conversations → form submissions → appointments → invoices → transactions (the last two are finance). Metadata only.
- **Limits:** 100 requests per 10 seconds and 200,000 per day, per sub-account.
- **Leads tab:** inquiries, tours booked, upcoming tours, awaiting reply, won; 12-month inquiries vs tours; outcomes, stages, sources, channels, forms. ⏳ **"Booked/won" needs a per-venue definition** before outcomes are shown: some venues never close opportunities in LeadLock (KB-V-03).
- **Scale:** 59 sub-accounts (57 tokens; 2 paused sub-accounts refused), 5 mapped (the 4 pilot clients, one has two). Whether LeadLock-only customers belong in the KB is open (§20).

### 4.9 Not connected in v1 (known gaps, shown in coverage)

| Gap | Effect | Path |
|---|---|---|
| **Zoom transcripts** | Most older client calls have a video in Drive but the transcript stays in Zoom | A read-only Zoom Server-to-Server app, which a Zoom admin must create ⏳. `zoom` is already a known provider |
| Staff personal mailboxes | A reply sent from a staff mailbox looks like "no reply" | Badges say "No reply from hello@", not "no reply" |
| The LeadLock support mailbox | Most LeadLock-only clients email it, not hello@; Support tab has no source | Connect it ⏳ |
| WIA's own GHL billing (invoices, payments) | Invoices & terms stays Soon | Needs per-invoice client matching |
| Dubsado | Finance notices arrive by email with no client address | Sender rule BF-6 |

---

## 5. Client mapping

### 5.1 The registry
- **Clients** (`businesses`): name, slug, aliases (former names too, so old records match), status (`active` / `inactive`), engagements (`service_engagements`).
- **Archiving** sets the client inactive and **pauses its sync**: scopes stop but keep their saved positions; shared-source records that match only that client aren't attached. Reactivating resumes from the saved positions, and a re-qualification pass covers the gap.
- **Past clients** are not backfilled. Whether they belong in the KB at all is open ⏳.
- **Every mapping command** writes an audit event and checks a revision (`expected_revision`), so two admins can't overwrite each other.

### 5.2 Channels and how each maps

Connections shows clients against five channels:

| Channel | Providers | Kind | Mapped unit | Rule |
|---|---|---|---|---|
| LeadLock | leadlock | Dedicated | Sub-account | Never read until linked; a remap moves the old client's links; unmap keeps history; "not a client" excludes it (undoable) |
| Slack | slack | Dedicated | Channel | Never read until linked |
| ClickUp | clickup | Dedicated | List / folder | Never read until linked; archived lists kept as history |
| Drive | drive | Dedicated | Folder | Never read until linked |
| Email & meetings | gmail, calendar, fathom | **Shared** | **Contact** (email or domain) | Read account-wide; an item attaches to a client only through that client's approved contacts (§8) |

Cell states: `linked`, `paused` (client archived), `suggested` (waiting for a person), `missing`, `not_applicable` (an admin said this channel isn't part of the engagement), `not_connected` (no KB account for that provider).

### 5.3 Contacts and sender rules
- **Contacts** are an email address or a domain, `candidate` → `approved` / `rejected`. **Public domains (gmail.com etc.) are never approved as a domain**; personal addresses are approved person by person.
- **Discovery** proposes contacts from direct correspondence only (who wrote to hello@, who hello@ wrote to), over `DISCOVERY_WINDOW_DAYS` (365). Filters drop platform and vendor domains, automated senders, team addresses and partners. Before the filters, 137 of 201 suggestions were noise.
- **Sender rules** (`team`, `partner`, `blocked`, by address or domain) keep those senders out of client contacts for every client. **Partners never decide which client an email belongs to**, even when linked to one client.

### 5.4 Where mapping happens
- **Connections** (source side): client by client, a grid of the five channels; a cell opens that channel's options (link, change client, unlink, not a client, add a client). Unassigned LeadLock sub-accounts sit behind "Review them".
- **Client record → Accounts & sources** (client side): the same component for one client.
- **CLI:** `kb client add|archive|activate`, `kb scope-add`, `kb not-applicable`, `kb sender-rule`, `kb mapping`, `kb leadlock …`.
- ⚠️ **Until login (S10) exists, the Connections, Leads and add-client routes are local-only** (closed when `PRODUCTION_MODE=true`). Production mapping before S10 means the CLI.

### 5.5 Mapping status (pilot, 5 Nov)
24 clients known, 4 active pilots, 20 paused from the pilot run (whether they return for production is open ⏳). 11 mapping gaps remain (clients without contacts or without a Drive folder). LeadLock: 5 sub-accounts mapped, 25 suggested, 27 with no match, 2 unreadable.

---

## 6. People and account teams
- **People** unify provider identities (Slack user, ClickUp user, email address, Fathom speaker) into one person. Shared mailboxes have their own identity with dated holder history.
- **Party** of every identity: `internal`, `shared_mailbox`, `client`, `partner`, `automated`, `bot`, `unknown`. Contractors are internal (from the roster, not the domain).
- **Roster:** loaded from a private file (`backend/.local/roster.yaml`, never committed); `kb people resolve --all` after edits. Admin links survive automatic resolution.
- **Account teams** (`account_team_members`): suggested from ClickUp assignee counts, **confirmed by WIA** ⏳ (none confirmed yet). They drive "My clients" and visibility (§16).

---

## 7. Data storage

### 7.1 Layers

| Layer | Holds | Status |
|---|---|---|
| **Registry & mapping** | Clients, aliases, engagements, contacts, scopes, source decisions, sender rules, people, account teams | ✅ |
| **Source layer** | One record per provider item, immutable versions, citable text units, provider identities | ✅ |
| **Links** | Record ↔ client, with the basis (`scope_mapping`, `verified_contact`, `series_mapping`, `manual_review`) | ✅ (manual review ❌) |
| **Sync state** | Streams, runs, coverage windows, cursors, work queue, webhook receipts | ✅ (scheduling ❌, §11) |
| **Outbound & connections** | Outbound requests and their approvals; per-person ClickUp connections; LeadLock installations and locations | ✅ |
| **Change outbox** | `record_changes`: every change, revision-fenced, for later reducers and read models | ✅ written, no consumer |
| **Action domain (S8)** | Actions, action events (field-level history), review items | ❌ |
| **Read models (S9)** | What the cards read | 🟡 Leads only (computed on request) |
| **AI facts (S7)** | Profile facts, decisions, milestones, evidence quotes | ❌ after v1 |

### 7.2 Source layer in detail
- **`source_records`**: one per provider item (`record_kind` + `external_id` per connector account), availability (`available`, `deleted_upstream`, `access_lost`, `out_of_scope`), whether it was admitted to a client, current version.
- **`source_versions`**: immutable. Each holds the normalised fields (`attributes`, never the raw payload), the parser version, and a content hash. A change creates a new version; old versions stay so old citations still resolve.
- **`content_units`**: the smallest citable text piece (a Slack message, a doc paragraph, a sheet row, a transcript segment) with a locator (where exactly it is), author, domain and retention state. **Email has none** (pointer only).
- **Domains** label every unit: registry, actions, communications, meetings, profile, support, programme, leads, health, **finance** (finance is admin-only).

### 7.3 What is never stored
- Raw provider payloads.
- Email bodies (read on demand).
- LeadLock couple names, emails, phone numbers, message text and free-text answers.
- Credentials in the database: connector accounts store only the *name* of the environment variable. Per-person tokens are stored encrypted (`KB_SECRET_KEY`).

### 7.4 Retention ⏳
Email is settled (pointer). For Slack, Drive and Fathom text: keep, or expire N days after the AI step has used it. The schema supports it (`retention_state`, and expired text is never fetched again), but WIA hasn't set the rule (BF-7).

### 7.5 From stored data to the screen
v1 cards read **read models**: queries over the source layer, links, mapping and (later) actions. The Leads tab shows the pattern: computed on request from live tables, so new synced data appears without any rebuild. Heavier aggregates can be kept current from the change outbox. The current static MVP page (snapshot + hand-written overlays) is replaced by these.

### 7.6 DB schema (*To be detailed*)
34 tables today, from migrations `18e642a0961c` → `c07a20261104`; production is created from `backend/sql/schema.sql` (regenerate with `python -m backend.scripts.schema_export` after any new migration). Diagram: `backend/docs/schema.dbml`.

Tables by group:
- **Registry & mapping:** `businesses`, `business_aliases`, `service_engagements`, `contacts`, `client_source_decisions`, `sender_rules`, `audit_events`
- **People:** `people`, `person_addresses`, `provider_identities`, `mailbox_holders`, `account_team_members`
- **Sources:** `connector_accounts`, `source_scopes`, `source_records`, `source_versions`, `content_units`, `record_associations`, `association_reviews`, `record_changes`, `drive_nodes`, `scope_memberships`
- **Sync & queue:** `sync_streams`, `sync_runs`, `sync_cursors`, `coverage_windows`, `webhook_receipts`, `work_items`
- **Outbound & connections:** `outbound_requests`, `clickup_connections`, `leadlock_installations`, `leadlock_locations`, `leadlock_app_events`
- `alembic_version`

To add for v1: client sync requests (§11.7), review items and manual link decisions (§9), the action domain (§14), per-user pins, and read-model tables where on-request queries are too slow.

---

## 8. Linking items to clients without missing any

A shared source can miss a client's item in two ways: **never recorded**, or **recorded but not linked**. They are handled separately.

### 8.1 Record everything (capture)

| Source | Rule | Status |
|---|---|---|
| Gmail | A pointer for every message in hello@ | ✅ |
| Calendar | A pointer for every event on approved calendars (title, time, attendees, organiser, series). Today non-client events are dropped | ❌ change needed |
| Fathom | A pointer for every meeting (title, time, invitees, recording ID). Transcript and summary are fetched only once linked. Today non-matching meetings are dropped | ❌ change needed |
| Dedicated sources | Everything in a linked scope belongs to that client | ✅ |

### 8.2 Link by rules (attribution)
Re-runnable over stored pointers, with no provider calls; each link records its basis. In order:
1. **Approved contact address** in from/to/cc, attendees or invitees. ✅
2. **The client's own domain** (never a public domain). ✅
3. **Propagation** ❌: every message in a Gmail thread follows the thread (a thread pointing to two clients goes to review); occurrences follow their series ✅; a Fathom recording follows the calendar event at the same time with the same invitees.
4. **Sender rules** for mail with no client address: Dubsado project labels (BF-6), platform alerts naming a client account ❌.
5. **Anything else is only suggested** to the operations review queue (§9), never linked automatically. Titles and names never decide.
6. **Known blind spots** are listed in coverage (§4.9).

Approving a new contact re-runs the rules over stored pointers, so that person's older history links in seconds (P-02). Only newly linked items fetch content (e.g. a Fathom transcript).

### 8.3 Prove nothing is missed
- **Capture check:** after each full re-read, compare stored pointers with the provider's own total (Gmail reports `messagesTotal`). A mismatch is an alert.
- **Attribution cross-check:** during a client's Full re-check, an independent Gmail search on the client's contacts and domain must return only messages that are already stored and linked. Missing → capture bug (fetch and alert). Linked but not returned → must be explained by rules 3–4.
- **Per-client coverage line**, e.g. "hello@: 412 linked (398 by contact, 14 by thread) · 3 possible matches to review".

---

## 9. Operations review queue (unmatched items)

**Who:** people with the "file senders" permission (granted per user by an admin; the operations lead by default). A proper role from S10 (§16).

**What is queued:** only items worth a person's time. Automated, bulk, internal and blocked-sender items stay as unlinked pointers that are counted, not queued. An item is queued when it has an external human sender and a signal:

| Suggestion | Signal | Strength |
|---|---|---|
| "Belongs to client X" | Same thread as an item already linked to X; a new address at X's domain | Strong |
| "Probably client X" | Sender name, domain, subject or meeting title matches X's name or aliases | Medium |
| "Who is this?" | No match, but the address has written to hello@ more than once | None |
| Conflicts | One thread points to two clients; a rule now disagrees with an existing link (`association_reviews`) | — |

**Choices and where they apply**

| Choice | Effect |
|---|---|
| Link to client X | A link with basis `manual_review`, for the whole thread by default (or this item only) |
| Link and approve the sender as X's contact (person or domain) | The contact is approved through the mapping commands; rules re-run over stored history; future items link automatically |
| Not a client: partner / team / blocked | A sender rule; the sender is never queued again |
| Move a wrong link | Old link removed, new one added; everything derived from the item is recomputed for the new client (AI-derived parts once S7 exists) |
| Ignore | Hidden from the queue, still counted in coverage |

**Rules:** a manual decision is never overridden by a later automatic rule; every decision is audited and reversible from the item's history; a decision that would change a client under a Full re-check is refused until it ends (§11.8).

**Where:** an "Unmatched" section in Connections with counts per source, and "N possible items" on each client's Accounts & sources tab.

Status: ❌ (needs §8.1 pointers, §8.2 rules, and S10 for the role).

---

## 10. Production and local configuration

One variable, `PRODUCTION_MODE`, decides how the backend runs. `python -m backend.scripts.kb config` prints the effective configuration (no secret values). ✅ Built 5 Nov.

| | `PRODUCTION_MODE=false` (default, local) | `PRODUCTION_MODE=true` (Railway staging / production) |
|---|---|---|
| Intake | On demand: `kb backfill`, `kb sync …`, `worker --drain` | Scheduled (§11); `SYNC_SCHEDULER_ENABLED=false` pauses it |
| `ENVIRONMENT` | `local` (empty follows the mode) | `production` or `staging`; `local` is refused |
| Local-only routes (no login yet) | Open | Closed (404) |
| Refused at start-up | `OUTBOUND_MODE=live` | Also: a local `DATABASE_URL`; missing `KB_SECRET_KEY` or `OPS_TOKEN`; `INGEST_WINDOW_DAYS` set; local or non-https OAuth addresses for configured OAuth apps |

Refusals name settings, never values. `/health/ready` reports `mode`, `environment`, `sync_scheduler` and the schema revision. Full variable list: §17.4.

---

## 11. Sync: how data stays current

### 11.1 Streams and runs
Each approved scope has a **stream** (Drive has one per account) with a saved position (`cursor`) and two timers: next incremental, next full re-read.

| Run | Reads | When | Queue lane |
|---|---|---|---|
| **Backfill / full re-read (reconcile)** | Everything in the scope, then re-checks every stored record it didn't see (deletion detection) | First load; then on the full re-read timer | `bulk` |
| **Incremental** | Only what changed since the saved position | Every interval per stream | `sync` |
| **Refresh** | One record | On demand | `sync` |
| **Client sync** (§11.7) | Every stream feeding one client | On demand | `sync` (Quick) / `bulk` (Full) |

Runs on the same stream never overlap: a request for a mode already queued or running joins it. Each page is saved in one transaction with its position, so a crash or redeploy resumes from the last saved page.

### 11.2 The scheduler
- Runs **inside the worker** as a background thread, only when `sync_scheduler_enabled` is true (production by default).
- Every `SCHEDULER_SWEEP_SECONDS` (30): for each enabled stream of an approved scope of an active client, with no run in progress: queue a full re-read if due, else an incremental if due.
- A **PostgreSQL advisory lock** makes exactly one worker the sweeper, even with several worker copies; the lock frees itself if that worker dies.
- **Why not a Railway cron job:** Railway cron runs must be ≥ 5 minutes apart, must exit, are skipped while the previous run is still going, and drift by minutes. The worker runs continuously anyway.

### 11.3 Per-source behaviour

| Source | Incremental | Full re-read | Proposed interval (incremental / full) |
|---|---|---|---|
| Gmail | Changes since the saved `historyId` (taken *before* each full listing, so nothing arriving mid-run is missed) | Lists all of hello@ (~60k header lookups) | 5 min / **weekly** |
| Calendar | `syncToken` | All events and occurrences | 15 min / daily |
| Drive | Changes feed | Walk all approved folders | 30 min / daily |
| ClickUp | Tasks updated since the saved time minus 5 minutes (move to one workspace-level query) | All tasks in each list | 10 min / daily |
| Slack | Today: re-reads the last 7 days of each channel. Change: read from the saved point | Full channel history | 5 min / daily |
| Fathom | Today: none. Change: meetings created since the last run | Lists every meeting | hourly / daily |
| LeadLock | Today: re-reads the whole sub-account. Change: "updated since" | Whole sub-account | hourly / daily |

Today one global `SYNC_INTERVAL_SECONDS` (300) and `RECONCILE_INTERVAL_SECONDS` (86400) apply; per-source intervals are to be added.

### 11.4 Day 0: the first load
1. Deploy with `PRODUCTION_MODE=true` and `SYNC_SCHEDULER_ENABLED=false`.
2. `kb sync run --mode backfill --all` (to build) queues a full-history run per stream on the resumable sync path.
3. The workers drain it. A run that ends with no gaps saves its position, sets its next full re-read for one interval later, and makes its first incremental due at once.
4. `kb report` and the coverage report are reviewed with WIA.
5. Remove `SYNC_SCHEDULER_ENABLED=false`; scheduled sync starts on the next sweep.

Expected duration: Gmail dominates. ~60k header lookups paced at 0.05 s take at least ~50 minutes before client fetches and per-page overhead; plan for several hours. Not yet measured.

### 11.5 From then on
Incrementals on each stream's interval; full re-reads on theirs, naturally spread out because each stream's timer starts when its own backfill finished. Archiving a client skips its streams and stops its runs, keeping the positions.

### 11.6 Events and failures

| Event | Behaviour |
|---|---|
| New client / newly linked dedicated scope | New stream; the next sweep runs its full history, then incrementals |
| New contact or Drive folder on a shared source | Linked through the rules over stored pointers (§8); missing content fetched. On approval a targeted read is triggered |
| Saved position no longer valid (Gmail 404, Calendar 410) | The stream bumps its generation and runs a full re-read automatically ✅ |
| Temporary error | Retries after 10 s, 30 s, 2 min, then the run fails (resumable) |
| Rate limit (429, Google 403 `rateLimitExceeded`) | Waits without using up attempts; daily limit → retry in 1 hour ✅ |
| Credential revoked / identity mismatch | The connector account is blocked; shows in ops and Connections |
| Run with gaps | Today: the position isn't saved (⚠️ every later incremental becomes a full read). Change: save the position, record the gaps, retry gaps individually |
| Pause everything | `SYNC_SCHEDULER_ENABLED=false`: no new runs; queued pages finish |

### 11.7 Sync client now
One action that brings every source of one client up to date. Works in both modes (it is on demand, not the scheduler).

| Depth | Client's own sources (Slack, ClickUp, Drive, LeadLock) | Shared sources (hello@, calendars, Fathom) |
|---|---|---|
| **Quick** ("Sync now") | Incremental on each stream; a never-loaded stream gets its first full load | One incremental each (updates every client at once, cheaply) |
| **Full** ("Re-check everything") | Full re-read with deletion check (Drive: only this client's folders) | Bring pointers current → re-run the linking rules for this client → cross-check search (§8.3) → fetch content for newly linked items. Never a whole-mailbox read |

- **Entry points:** `kb sync client <slug> [--full]`; `POST /api/v1/clients/{slug}/sync`; `GET …/sync` for per-source progress ("Slack ✓ · Gmail running · Fathom queued"); a button on the client record; status on Accounts & sources and Connections.
- **Guards:** joins runs already in progress; a 2-minute cooldown per client; one Full per client at a time.
- **After it finishes,** the client's tabs reload.
- **Who:** admins and the client's account team (S10).
- Status: ❌.

### 11.8 During a Full re-check
| Frozen for that client | Open |
|---|---|
| Mapping: contacts, scopes, archive/activate, LeadLock mapping, review-queue decisions ("Re-check in progress"; an admin can cancel) | Reading, with a banner ("Re-checking since 14:02 · 4 of 7 sources done") |
| Outbound: ClickUp edits and Slack pings are held, not sent | Action edits in the KB (status, owner, due, comments) |
| Scheduled updates for the client's own streams (automatic: the re-check is their active run) | Shared sources' schedule |

**After it ends,** each action is compared field by field: changed only in the KB → kept (held edits released, still via approval); changed only in the source → applied; both, same value → nothing; **both, different values → a "Sources disagree" item** for an approver with both values, who and when. Choosing the KB value queues a ClickUp write-back through the guard; choosing the source value updates the action and notes the override. An action whose source item was deleted or moved to another client also goes to review. A summary shows what changed ("+12 linked, 3 marked deleted, 1 for review"). The freeze lifts after 60 minutes even if the run is stuck (run marked partial).

### 11.9 Throughput
One worker processes one page at a time, oldest first; each connector account processes one page at a time (all Slack channels share the Slack account). **Two worker services** keep 5-minute updates from waiting behind a multi-hour full read:
- `python -m backend.workers.runner --lanes sync`
- `python -m backend.workers.runner --lanes bulk,maintenance`

### 11.10 Worker setup (*To be detailed*)
Lease 90 s with a heartbeat; retries `[10, 30, 120]` s; the queue is PostgreSQL only (`work_items`, claimed with `SKIP LOCKED`). Jobs: `intake.backfill_page`, `client.discover`, LeadLock token and reconcile jobs. `record.extract` jobs (the AI hand-off) have no consumer and must be switched off or pruned before the production backfill.

---

## 12. Production backfill (*To be detailed*)

**Prerequisites** (blockers, full table in the production tracker §1):

| # | Item | Status |
|---|---|---|
| BF-1 | Google 403 rate limits retried, not "denied" | ✅ |
| BF-2 | Email as pointers | ✅ |
| BF-3 | One Gmail query for every contact | ⚠️ likely obsolete (the backfill lists the mailbox) |
| BF-4 | Resume a stopped run (use the sync path) | 🟡 |
| BF-5 | Parser-version fingerprint test | 🟡 |
| BF-6 | Dubsado / finance sender rule | ❌ |
| BF-7 | Retention rule for Slack, Drive, Fathom text | ⏳ |
| BF-8 / BF-9 | Drive attribution; Sheets range and calendar status | ✅ |
| Phase A | `rate_limits` import fix (every real run on the sync path crashes today), scheduler thread, streams enabled, `kb sync` commands, position saved on partial runs, real-adapter sync test | ❌ |
| §8.1 | Calendar and Fathom pointers for every item | ❌ |

**Procedure:** staging first (2–3 clients, full history, run twice: the second run must create zero new versions; a killed run must resume with nothing duplicated or skipped; an induced 403 must retry). Then production as in §11.4. Then 72 hours of live sync with 95% of updates arriving within 15 minutes.

---

## 13. Frontend features (v1)

The React app (`frontend/src`) is the single source. Pages read the API under `/api`, served from the same address as the frontend (no CORS). Locally, Vite proxies `/api` to the API on port 8010.

### 13.1 Client Portfolio
| Element | Data | Class |
|---|---|---|
| Card: name, initials, logo | Registry; logo chosen once per client | DET / HUMAN |
| Service chips, engagements, lifecycle | Engagements through a fixed lookup table; lifecycle from ClickUp space + `Phase` | DET with a human gate ⏳ (WIA confirms the table and lifecycle rule) |
| Owner / account team | `account_team_members` | DET with a human gate ⏳ |
| Open / overdue counts, next call | Actions read model (archived template tasks excluded); earliest future calendar event with a client attendee | DET |
| Card menu: open, pin to top, mark as archived | Pin: per user. Archive: admin, global, pauses sync | DET ⏳ (today both are browser-only, §20) |
| Archived tab, list view, client name links | — | DET |
| Health | — | Soon |

### 13.2 Client record
**Header and strip:** client since (earliest commercial evidence, WIA may define it ⏳), earliest evidence, processed through (last successful sync), account owner, quick links (Slack, Drive, ClickUp, LeadLock), Sync client now (§11.7).

| Tab | v1 content | Class |
|---|---|---|
| **Now** | Next meeting (header), last meeting (header + Fathom summary, labelled), 3 action rows + "+N more", "Communication since the last call" (email and Slack counts, awaiting our reply) | DET + PROV; sentiment Soon; decisions AI later |
| **Profile** | People card (contacts with last contact and calls; WIA team), engagements and phase, LeadLock link. Marketing profile sections: AI later; questionnaire answers may show verbatim, flagged "Unreviewed", with sensitive questions excluded | DET + HUMAN (contact roles ⏳) |
| **Commitments** | The client's actions, 10 per page, soonest due first, "We owe / Client owes" | DET (from the Action Hub) |
| **Meetings** | Calendar + Fathom + Drive videos joined by date; type, attendees, host, recording/transcript state, provider summaries and next steps, upcoming agenda | DET + PROV |
| **History** | "All activity": lanes and timeline, de-duplicated event list (one row per thread/task/file per day), period filter. Curated "Moments" later. No dollar amounts | DET |
| **Handover brief** | 4 of 7 sections (what's owed, people, watch-outs, what the record can't tell you); Regenerate = re-query with a "Generated …" stamp | DET (rest AI later) |
| **Support** | Coverage banner and empty state (no source) | Blocked |
| **Leads** | LeadLock KPIs and charts (§4.8) | DET ⏳ outcome definitions |
| **Attendance** | Accelerator clients only | DET |
| **Accounts & sources** | The client's five channels, mapping, per-source state and last sync, possible items to review | DET |
| Health, Invoices & terms | — | Soon |

### 13.3 Action Hub (design final)
- **KPI tiles** (Pending (you), Pending (team), Pending (client), Completed) act as filters, with tooltips; the filter bar keeps only **Needs review**.
- **Board:** client initials, plain date (red when late), timing tooltip ("N days late", "No due date"), Slack mark when pinged, done check. **Drag and drop** between columns or onto a KPI tile; dropping on Pending (team) asks "Who should own it?" (the client's account team first, never yourself; the new owner must acknowledge); dropping on Completed asks "What shows it's done?".
- **Detail window:** Change status menu, owner picker, history, one-line comments, "Sources disagree" when values conflict; Internal (accelerator upkeep) tasks open the full window with their recurrence.
- **Ping on Slack:** on Pending (team/client) actions, to the client's channel (or the accelerator channel for Internal tasks), with a 2-minute cooldown and "Sent N mins ago". Through the outbound guard (§15) ⏳ (one-click vs approval is open).
- **Add action:** title, client, owner, due, priority (no Type field; saved as Admin).
- **List view, search, notifications** (deadline-change requests).
- Removed for v1: workspace search (⌘K), Overview/Call prep/Health/Client 360/Invoices (Soon, blocked by URL).

### 13.4 Connections
§5.4. Plus sync state per source (last incremental, last full re-read, failures), the Unmatched section (§9), and per-person "Connect ClickUp".

### 13.5 How data reaches the screen
Pages fetch from the API; after a sync or client sync finishes, they reload. A sync chip shows freshness and failures from `sync_streams` / `sync_runs`. Pins, archive and brief stamps move from browser storage to the database. Status: Leads and Connections read the API ✅ (local only); Portfolio and Action Hub still read the snapshot ❌.

---

## 14. Action model (S8, ❌)
- **States:** Open → Done, plus **Acknowledged** (the owner has seen it). ClickUp's "in progress" is mirrored only where it is really used.
- **Side:** we owe / client owes, from the ClickUp `Role` field or the action's origin.
- **Sources of actions:** ClickUp tasks (excluding archived onboarding templates, which show as checklist progress), manual "Add action", and later AI-found commitments (S7).
- **History:** every change is an event with field, old and new value, who, when and how (KB, ClickUp, Slack reply). Required for the post-re-check comparison (§11.8).
- **Review items (Needs review):** stale, owner unclear, client unclear, duplicate, sources disagree, checklist incomplete, and later AI proposals; plus "create in ClickUp?" for Slack-only asks.
- **Commands** use `expected_revision`; ClickUp write-back goes through the outbound guard with the person's own token.
- **Priority** has no ClickUp source: keep as a KB-only field or drop ⏳.

---

## 15. Outbound guard (S12)
- **Rule:** nothing reaches Slack or ClickUp unless a listed approver types **yes** at an interactive terminal for that exact request. The approval is tied to the payload hash and expires after 24 hours; a request is sent exactly once.
- **Lifecycle:** draft (`kb outbound draft-post | draft-dm | draft-edit`) → approve → send; also list, show, reject, status.
- **Settings:** `OUTBOUND_MODE` (`off` / `sandbox` / `live`; `live` refused outside production mode), `OUTBOUND_KILL_SWITCH`, `OUTBOUND_APPROVERS`, sandbox allow-lists (testing channel, the approver's own DM, sandbox ClickUp lists).
- **ClickUp edits:** status, due date, assignees only, never "Closed", with the person's own token.
- Status: ✅ guard; Slack sandbox tests done; ClickUp sandbox test ⏳ (needs a WIA sandbox list); wiring from the Action Hub ❌.

---

## 16. Access and visibility (S10, ❌)
- **Login:** KB login (Command Center hand-off or Google) ⏳.
- **Roles:**

| Role | Sees | Can do |
|---|---|---|
| Admin | Everything, including finance | Mapping, archive, roles, review queue, outbound approval (if listed), client sync |
| Operations ("file senders" permission) | Clients they're allowed to see | Review queue decisions, sender rules, client sync |
| Account team member | Their clients (from confirmed `account_team_members`) | Actions, comments, Ping, ClickUp edits with their own token, client sync |
| Finance | Finance-tagged data | — |

- **Visibility never comes from Slack channel membership** (everyone is in every channel).
- **Until S10:** routes without login are local-only; production mapping uses the CLI.
- ⚠️ **The current static MVP page is public with real data for the pilot clients.** Put it behind login or replace it before v1 goes live ⏳.

---

## 17. Deployment on Railway

### 17.1 Projects and services

| Project | Purpose | Settings |
|---|---|---|
| **Staging** | Dry runs (BF checks, backfill twice, 72-hour sync test) | `PRODUCTION_MODE=true`, `ENVIRONMENT=staging`, `OUTBOUND_MODE=off` |
| **Production** | Live | `PRODUCTION_MODE=true`, `ENVIRONMENT=production`, `OUTBOUND_MODE` set deliberately |

| Service (one image: `backend/Dockerfile`) | Command | Notes |
|---|---|---|
| **api** | default CMD: `uvicorn backend.app:app` on `$PORT` | Health checks `/health/live`, `/health/ready` |
| **worker-sync** | `python -m backend.workers.runner --lanes sync` | Runs the scheduler thread (leader via advisory lock) |
| **worker-bulk** | `python -m backend.workers.runner --lanes bulk,maintenance` | Backfills and full re-reads |
| **postgres** | Railway PostgreSQL 16 | Backups / PITR on; a restore rehearsed; created from `schema.sql` |
| **frontend** | Static build served with `/api` proxied to the api service (same origin) | Replaces the current static MVP service |

### 17.2 External registrations for production
- **ClickUp OAuth app:** add the production redirect URL; set `KB_APP_URL` and `CLICKUP_OAUTH_REDIRECT_URI`.
- **LeadLock Marketplace app:** production redirect URL and webhook URL (`https://<api>/api/v1/leadlock/webhooks`); **a separate install for production** (the rotating agency token can't be shared with dev).
- **Google OAuth:** the Internal app and hello@ refresh token move to Railway variables.
- **Fathom:** webhook optional later (`FATHOM_WEBHOOK_SECRETS`).

### 17.3 Deploy procedure (manual, no CI)
1. `git status`: nothing under `backend/.local/`, no `.env`.
2. Run the test suite by hand (all must pass).
3. New migration → staging first; if production is still empty, regenerate `schema.sql` instead.
4. Privacy scan of changed files.
5. After deploy: `/health/ready` shows the expected schema and mode; `kb config` and `kb outbound status` show the intended settings.

### 17.4 Environment variables

| Variable | Used by | Production value |
|---|---|---|
| `PRODUCTION_MODE` | all | `true` |
| `ENVIRONMENT` | all | `production` / `staging` |
| `DATABASE_URL` | all | Railway Postgres |
| `OPS_TOKEN` | api | required |
| `KB_SECRET_KEY` | api, workers | required; keep safe (losing it means everyone reconnects ClickUp and LeadLock tokens are lost) |
| `INGEST_WINDOW_DAYS` | workers | unset (full history) |
| `DISCOVERY_WINDOW_DAYS`, `CLICKUP_CLIENT_SPACES` | workers, CLI | as today |
| `SYNC_SCHEDULER_ENABLED` | worker-sync | unset (on), or `false` to pause |
| `SCHEDULER_SWEEP_SECONDS`, `SYNC_INTERVAL_SECONDS`, `RECONCILE_INTERVAL_SECONDS` | worker-sync | 30 / 300 / 86400 today; per-source to come |
| `WORKER_LANES`, `LEASE_SECONDS`, `RETRY_DELAYS_SECONDS` | workers | per service (§17.1) |
| `SLACK_BOT_TOKEN` | workers | WIA AI BOT |
| `CLICKUP_TOKEN`, `CLICKUP_TEAM_ID` | workers | read key |
| `CLICKUP_OAUTH_CLIENT_ID/SECRET/REDIRECT_URI`, `KB_APP_URL` | api | https production addresses |
| `GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN` | workers, api | hello@ grant |
| `FATHOM_API_KEY`, `FATHOM_WEBHOOK_SECRETS` | workers, api | team key |
| `LEADLOCK_APP_CLIENT_ID/SECRET`, `LEADLOCK_APP_ID`, `LEADLOCK_COMPANY_ID`, `LEADLOCK_REDIRECT_URI` | api, workers | production install |
| `OUTBOUND_MODE`, `OUTBOUND_KILL_SWITCH`, `OUTBOUND_APPROVERS`, `OUTBOUND_SANDBOX_*` | api, CLI | `off` until decided |

Where each credential lives is recorded in the credential register (outside the repo; no values).

### 17.5 Operations
- **Logs:** JSON to stdout, IDs and counts only (no content, no URLs with queries).
- **Watch:** `kb status`, `kb report`, ops API (`/api/v1/ops/connectors|scopes|runs`, `X-Ops-Token`), sync chip.
- **Alert when:** a stream's lag exceeds 3× its interval; a connector account is blocked; a capture-count mismatch (§8.3).
- Not yet: error tracker, external uptime check.

---

## 18. Rollout plan
1. **Commit** the current uncommitted work (after a privacy check of the analysis files).
2. **Phase A** (sync path runnable): `rate_limits` fix, real-adapter sync test, scheduler thread + advisory lock, streams enabled on approval, `kb sync status|run|resume|enable|disable|client`, position saved on partial runs, two worker lanes.
3. **Capture changes:** Calendar and Fathom pointers for every item; thread propagation; BF-6; switch off `record.extract` enqueue.
4. **Phase B** (per-source tuning, §11.3).
5. **Staging:** deploy, backfill 2–3 clients twice, resume and 403 tests, 72-hour sync with p95 lag < 15 min.
6. **Read models + API (S9, S11)** for the DET cards; **actions (S8)**; **login and visibility (S10)**; frontend wired (S13).
7. **Operations review queue** and **Sync client now**.
8. **Production:** Postgres with backups, `schema.sql`, backfill, coverage review with WIA, scheduler on.
9. **Pilot** with 2 account owners, then WIA sign-off.

---

## 19. Status (6 Nov)

| Area | Status |
|---|---|
| S1 Source access | ✅ (ClickUp sandbox write test ⏳) |
| S2 Client mapping | ✅ commands and UI (local); WIA client list ⏳ |
| S3 People | ✅ tables and resolution; owners/teams unconfirmed ⏳ |
| S4 Ingestion engine | ✅ adapters, pointers, BF-1/2/8/9; Phase A ❌ |
| S5 Production backfill | ❌ (local learning run only) |
| S6 Live sync | 🟡 code; not runnable (Phase A) |
| S7 Extraction (AI) | ❌ after v1 |
| S8 Actions | ❌ |
| S9 Read models | 🟡 Leads only |
| S10 Login and visibility | ❌ |
| S11 API | 🟡 ops, ClickUp connect, LeadLock, Connections, client leads |
| S12 Outbound | 🟡 guard built; wiring ❌ |
| S13 Frontend | 🟡 UI final for the Action Hub; Portfolio provisional; snapshot data |
| Production config switch | ✅ |
| Tests | 286 passing (5 Nov), run on an isolated Postgres |
| Committed | ❌ large uncommitted set on branch `mvp` |

---

## 20. Open decisions and things waiting on WIA

| # | Question | Owner |
|---|---|---|
| 1 | Confirm the client list; do the 20 paused clients return for production? Do past clients belong in the KB? Do LeadLock-only customers? | WIA |
| 2 | Retention for Slack, Drive and Fathom text (BF-7) | WIA |
| 3 | Confirm account owners and teams; contact roles (admin-entered or wait for AI) | WIA |
| 4 | Service lookup table, lifecycle rule (AR-22), "client since" definition | WIA |
| 5 | Per-venue definition of "booked/won" for Leads (KB-V-03) | WIA |
| 6 | Archive semantics: admin-only global archive + per-person "hide from my portfolio", or admin-only archive | Jainil |
| 7 | "Ping on Slack": approval per ping, or a per-user permission with a narrow template | Jainil |
| 8 | Priority: KB-only field or drop | Jainil |
| 9 | The public MVP page: login in front, or stub data, until v1 | Jainil |
| 10 | Rename the Now card to "Communication since the last call" (30-day fallback, Slack shown as "Team discussion"); the "awaiting our reply" rule (plain, or filtered by words/question mark) and badge wording; whether a Gmail snippet joins the pointer | Jainil |
| 11 | Show Fathom summaries as-is (labelled) in Now and Meetings | Jainil |
| 12 | History: ship "All activity" now, "Moments" later | Jainil |
| 13 | Gmail full re-read weekly; per-source intervals (§11.3); two worker services (§11.9) | Proposed |
| 14 | ClickUp sandbox list for the write test | WIA |
| 15 | Mailbox access beyond hello@ (staff mailboxes, the LeadLock support mailbox) | WIA |
| 16 | A Zoom Server-to-Server app for transcripts | WIA (Zoom admin) |
| 17 | Login method (Command Center hand-off or Google) | Jainil / WIA |

---

## 21. Glossary

| Term | Meaning |
|---|---|
| Scope | A provider container the KB may read: channel, list, folder, mailbox, calendar, recorder, sub-account |
| Dedicated / shared | A dedicated scope belongs to one client; a shared one serves all clients and links items by contact |
| Pointer | A stored record of an item without its content (email body never stored) |
| Stream | The sync state of one scope (Drive: one per account): saved position, timers |
| Incremental / full re-read (reconcile) | Read changes since the saved position / read everything again and detect deletions |
| Coverage | What a run saw, stored, skipped and couldn't read, per scope |
| Basis | Why a record is linked to a client: scope mapping, verified contact, series, manual review |
| Read model | A query or table shaped for one screen |
| Outbound guard | The approval gate for any write to Slack or ClickUp |
| `PRODUCTION_MODE` | The switch between local (on demand) and production (scheduled) behaviour |
