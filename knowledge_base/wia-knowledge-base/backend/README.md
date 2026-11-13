# KB backend: intake slice

FastAPI + SQLAlchemy 2 + psycopg 3 + Alembic + PostgreSQL. The work queue is PostgreSQL-only (decision D-4). This slice ingests approved sources into versioned, citable content units. Design: [docs/Ingestion-Pipeline-Design.md](../docs/Ingestion-Pipeline-Design.md). Known test shortcuts: [before_production.md](before_production.md).

> **Always run Python from the repository root** (`python -m backend.…`). Running from inside `backend/` makes the SOP's `backend/logging/` package shadow the standard library.

## Local setup

```bash
cp backend/.env.example backend/.env          # fill in credentials; never commit
python -m venv backend/.venv && backend/.venv/Scripts/python -m pip install -r backend/requirements.txt
docker compose -f backend/docker-compose.yml up -d db       # Postgres on 127.0.0.1:5440
backend/.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/Scripts/python -m pytest backend/tests -q
```

The full stack (API on 127.0.0.1:8010 + worker) runs with `docker compose -f backend/docker-compose.yml up -d`.

Tests create and drop their own `kb_test` database in the same Postgres; they never touch `kb`.

### Local vs production: `PRODUCTION_MODE`

One variable decides how the backend runs; `python -m backend.scripts.kb config` shows the result.

| | `PRODUCTION_MODE=false` (default, local) | `PRODUCTION_MODE=true` (Railway staging / production) |
|---|---|---|
| Intake | On demand: `kb backfill`, then `worker --drain` | Scheduled: the sync scheduler is on (`SYNC_SCHEDULER_ENABLED=false` pauses it) |
| `ENVIRONMENT` | `local` (empty follows the mode) | `production` or `staging`; `local` is refused |
| Local-only API routes (no login yet) | Open | Closed |
| Start-up checks | `OUTBOUND_MODE=live` refused | Also refuses a local `DATABASE_URL`, a missing `KB_SECRET_KEY` or `OPS_TOKEN`, a set `INGEST_WINDOW_DAYS`, and local or non-https OAuth addresses for configured OAuth apps |

Refusals name the settings, never their values. `/health/ready` reports `mode`, `environment` and `sync_scheduler`.

### Migrations

`upgrade head` applies the whole chain. An existing local database only needs the same command to pick up the new revisions:

| Revision | Adds |
|---|---|
| `18e642a0961c` | Initial intake schema |
| `b05a20261028` | Durable sync (B-05): `sync_streams`, run modes/checkpoints, `scope_memberships`, `webhook_receipts`, connector leases |
| `c02a20261029` | Client mapping (S2): `client_source_decisions` ("not applicable" per source), revisions on scopes/contacts, archive dates |
| `c03a20261030` | `sender_rules`: team, partner and blocked addresses or domains |
| `c04a20261030` | People and roster (S3): `people`, `person_addresses`, `mailbox_holders`, `account_team_members` |
| `c05a20261102` | `clickup_connections`: per-person ClickUp OAuth tokens (encrypted) |
| `c06a20261102` | `outbound_requests`: the approve-every-send log |
| `c07a20261104` | LeadLock Marketplace app: `leadlock_installations`, `leadlock_locations`, `leadlock_app_events` |

Upgrade with no in-flight runs; pre-B-02 runs need the [cutover procedure](docs/atomic-publication.md#deployment-cutover). Full schema: [docs/schema.dbml](docs/schema.dbml).

## Intake flow

```bash
python -m backend.scripts.kb clients backend/.local/clients.yaml   # manual registry (see clients.example.yaml)
python -m backend.scripts.kb connectors --register                  # first time; afterwards verifies identity
python -m backend.scripts.kb discover --days 30                     # metadata only → .local/proposal.md + approval.yaml
python -m backend.scripts.kb approve backend/.local/approval.yaml    # admin decision
python -m backend.scripts.kb backfill --days 30                     # or --full / INGEST_WINDOW_DAYS unset
python -m backend.workers.runner --drain                            # or the docker `worker` service
python -m backend.scripts.kb status
python -m backend.scripts.kb report                                 # → .local/backfill_report.md
```

`backend/.local/` holds real client data (proposals, reports) and is gitignored.

`kb discover` searches `DISCOVERY_WINDOW_DAYS` (default 365), longer than the backfill, so quiet clients
still get contacts. ClickUp discovery includes archived folders and lists, and every folder in a
`CLICKUP_CLIENT_SPACES` space is proposed even before a client matches it.

## Client mapping and sender rules

Mapping commands live in `services/clients/mapping.py`; the CLI calls them now and the admin API/UI
will call the same functions. Each writes an audit event, and edits to existing objects check a revision.

```bash
python -m backend.scripts.kb client add "Example Venue" --alias "Example"  # queues discovery for it (run the worker)
python -m backend.scripts.kb discover --client example-venue
python -m backend.scripts.kb scope-add clickup list <list-id> --client example-venue   # approve a scope by ID
python -m backend.scripts.kb not-applicable example-venue fathom --reason "no calls recorded"
python -m backend.scripts.kb mapping                                # client × source coverage grid
python -m backend.scripts.kb client archive example-venue           # pauses its scopes and contacts; activate resumes
python -m backend.scripts.kb sender-rule team someone@example.com --reason "staff personal address"
python -m backend.scripts.kb sender-rule partner @agency.example --reason "serves several clients"
python -m backend.scripts.kb sender-rule list
```

Sender rules (`team`, `partner`, `blocked`, by address or domain) keep those senders out of client
contacts for every client. Archiving keeps cursors and history, so reactivation resumes where it stopped.

## People and roster

People unify exact provider identities across connectors. Shared inboxes have their
own identities and dated holder history. The roster also excludes internal
addresses from client-contact discovery; client associations stay unchanged.
Use `roster.example.yaml` for the format and keep the real roster in `.local/`.

```bash
python -m backend.scripts.kb roster load backend/.local/roster.yaml
python -m backend.scripts.kb people resolve --all
python -m backend.scripts.kb people list --kind contractor
python -m backend.scripts.kb people unknown --limit 50
python -m backend.scripts.kb people link <identity-id> "Alex Example"
python -m backend.scripts.kb team suggest --days 120
python -m backend.scripts.kb team list
python -m backend.scripts.kb team set example-client owner "Alex Example"
python -m backend.scripts.kb team end <member-id> --expected-revision 1
```

Suggestions use retained current ClickUp task versions; they do not establish
coverage for tasks that have never been ingested. Confirm owners and resolve
pending roster entries with the business before using account teams for access.
Run `people resolve --all` after roster or sender-rule edits. Commands write audit
events; explicit identity links survive later automatic resolution.

## LeadLock Marketplace app (client leads and finance)

One private HighLevel Marketplace app, "WIA Client Knowledge Base" (Target User: Sub-Account, Agency
only), gives the KB a token for every LeadLock client sub-account. It's installed once from the agency, and
new sub-accounts are picked up automatically. Code: `services/intake/leadlock_app.py`, `routes/leadlock.py`.

| Endpoint | Does |
|---|---|
| `GET /api/v1/leadlock/oauth/callback` | HighLevel sends the installing agency admin here. Exchanges the code for the agency (Company) token, keeps it only if it belongs to `LEADLOCK_COMPANY_ID`, stores it encrypted, and queues a sync |
| `POST /api/v1/leadlock/webhooks` | Install/uninstall events. Verifies HighLevel's Ed25519 `X-GHL-Signature`, ignores duplicates (`webhookId`), records a new sub-account and queues its token, drops the token on uninstall |

- The agency refresh token is the only rotating credential. It's refreshed under a row lock and committed at
  once; if HighLevel rejects a refresh the grant is revoked and the app must be reinstalled.
- Sub-account tokens are minted from the agency token (`leadlock.location_token` job) and re-minted near expiry.
- `leadlock.reconcile` lists the sub-accounts the app is installed on and adds or retires rows. It's the
  fallback when no webhook URL is set (webhooks need the API reachable from the internet).
- The URL path says `leadlock`, not `ghl`: HighLevel's white-label rules refuse redirect URLs that mention it.

**Adapter** (`services/intake/adapters/leadlock.py`, provider `leadlock`): scope = one sub-account
(`kind=location`, dedicated to one client, domain `leads`). Each run reads, page by page:
1. contacts
2. opportunities
3. conversations
4. form submissions
5. appointments (90-day windows from the sub-account's creation date to a year ahead)
6. invoices
7. transactions

Invoices and transactions are domain `finance`. A refused feature becomes a gap for that phase only. A paused
sub-account is scope-denied, so it never blocks the connector. Records are metadata only (no units, no AI
extraction).

**Privacy:** names, emails, phones, addresses, message text, free-text answers, appointment titles and
opportunity names are never stored. Custom fields are kept only when structured (date, number, money,
options, checkbox).

**Leads tab:** `GET /api/v1/clients/{slug}/leads?period=7d|14d|30d|90d|180d|12m|all`, or
`?start=YYYY-MM-DD&end=YYYY-MM-DD` for a custom range (whole UTC days, inclusive; compared with the same number
of days just before it) (`routes/clients.py`, `services/read_models/leads.py`) turns a client's stored LeadLock records into the frontend's Leads dashboard.
It is behind the team password (`routes/access.py`), like the rest of the API. The definitions are in the module docstring:
- won counts only if the venue closes 10% or more of its opportunities;
- awaiting reply counts in-period threads only, with older unread ones reported apart.

Locally: start `kb-api` (port 8010), then `npm run dev:wia` in `frontend/`, which serves real KB clients and
proxies `/api` to 8010.

**Mapping sub-accounts to clients (Connections, 5 Nov):** `services/clients/connections.py` + `routes/connections.py`.
The Connections screen lists every sub-account the app is installed on; a client's Accounts & sources tab shows
the same list filtered to that client (`?client=slug`). Both call the S2 mapping commands, so the rules live in
`services/clients/mapping.py`:
- **Unmapped sub-accounts are never read.** Mapping one queues its full-history copy (`start_backfill`, no window).
  It waits instead when the client is archived (the dialog can reactivate it) or LeadLock refused access.
- **LeadLock is dedicated-only:** `assign_scope` refuses a LeadLock scope without a client (its contacts are
  leads, so "shared, by contact" can never work).
- **A remap moves what was collected:** the old client's `scope_mapping` links become `rejected`, the new client
  gets them. Unmapping stops collection and keeps history with the client it was collected for.
- **Not a client** is an excluded scope, remembered and undoable (`restore`).
- Suggestions come from distinctive-word name matches against every client (archived included), plus a pattern
  for WIA's own, template and demo sub-accounts. They are never applied without a person confirming.
- A sub-account installed later queues a reconcile, so it appears by name, marked New, waiting for an admin.

The Connections screen itself is client by client (`services/clients/client_connections.py`,
`GET /api/v1/connections/clients`): one row per client, five channels (LeadLock, Slack, ClickUp, Drive, and
"Email & meetings" = the contacts that attach hello@ mail, calendars and Fathom), one state per cell (linked,
paused, to confirm, not linked, not used, not connected). A cell opens that channel's options: link/unlink,
confirm suggestions, approve/remove/add contacts, mark not used (`POST …/link`, `…/unlink`, `…/contacts`,
`…/applicable`). LeadLock sub-accounts with no client sit apart under "Review them".

Endpoints (behind the team password; the audit actor is a placeholder until people sign in):
`GET /api/v1/connections/leadlock[?client=]`, `POST …/leadlock/{location_id}/map|unmap|not-a-client|restore`
(each takes `expected_revision`; a stale one returns 409), `POST …/leadlock/refresh` (one LeadLock call), and
`POST /api/v1/clients` (add a client; queues its discovery).

```bash
python -m backend.scripts.kb connectors --register leadlock               # once, after the app is installed
python -m backend.scripts.kb scope-add leadlock location <location-id> --client <slug>   # or approve via discover
python -m backend.scripts.kb leadlock status      # config, agency grant, sub-account counts (no client data)
python -m backend.scripts.kb leadlock locations   # each sub-account: state, token expiry, last error
python -m backend.scripts.kb leadlock reconcile   # sync installed sub-accounts and mint missing tokens now
```

## Crash-safe page publication

Page effects and work-item success now commit together. The runner fences failure
effects on the current claim, including errors received after a successful commit.
Both publication paths reject duplicate or contradictory page positions.

See [the B-02 contract, failure tests and deployment cutover](docs/atomic-publication.md).
Pre-fix in-flight runs need reconciliation; their coverage is not repaired by upgrading.

## Durable sync

`services/intake/sync.py` keeps one sync stream per approved scope (one per account for Drive). It coalesces runs in `backfill`, `incremental`, `reconcile` and `refresh` modes, stores checkpoints, and provides `resume()`. `execution.py` runs pages through the B-02 publication path.

- **The scheduler.** When `SYNC_SCHEDULER_ENABLED` is on, each worker calls `sync.sweep()` every `SCHEDULER_SWEEP_SECONDS`, and an advisory lock lets only one through. A stream switches on when its first full copy finishes.
- **With the scheduler off**, nothing reads a provider until `kb backfill`, or a mapping in the Connections tab, queues it.
- **Pointers for every item.** Every Gmail message, calendar event and Fathom meeting keeps a pointer (who, when, title), even when no client contact was on it.
- **Late contacts (P-02).** Approving a contact or reactivating a client queues `qualify.recheck`. Gmail pointers attach at once; calendar events and Fathom meetings get a one-item refresh. A late contact never needs a full re-read.

## Deploying to Railway

One image runs everything: the root `Dockerfile` holds the API, the workers and the built portfolio. It runs as the services below, in one project with Postgres. Configure each service in the dashboard:

| Service | Start command | Settings |
|---|---|---|
| Postgres | Railway template | Watch the volume during the Gmail copy; keep room for a second copy (the monthly restore check). Railway's own backups need Pro, so `db-backup` does it |
| web | image default (uvicorn on `$PORT`) | Pre-deploy: `alembic -c backend/alembic.ini upgrade head`. Healthcheck: `/health/ready`. Public domain |
| worker-bulk | `python -m backend.workers.runner --lanes bulk,maintenance` | No domain. 2 replicas during the first backfills, then 1 |
| worker-sync | `python -m backend.workers.runner --lanes sync` | No domain. Once the backfills are done, the only service with `SYNC_SCHEDULER_ENABLED=true` |
| db-backup | `python -m backend.scripts.backup dump` | Cron `15 8 * * *` (UTC), restart policy Never, no domain. See "Backups" |
| worker-ai | not created | Later: `--lanes analysis` with `AI_MODE=live` |

### Shared variables

Set these at project level and reference them from every service.

**Core settings**
- `PRODUCTION_MODE=true`
- `DATABASE_URL`: a reference to the Postgres service's `DATABASE_URL`, as-is (the backend switches its `postgresql://` scheme to the psycopg 3 driver)
- `KB_SECRET_KEY`: a new one, not the local key
- `OPS_TOKEN`
- `COMMAND_CENTER_AUTH_ORIGIN` and `COMMAND_CENTER_PUBLIC_ORIGIN`: Command Center's https origin (both the same unless it has a private one). Sign-in then comes from Command Center (see "Sign-in"); `KB_TEAM_PASSWORD_HASH` is only the fallback where these aren't set
- `RBAC_ENABLED=false`, `KB_DEFAULT_VIEWER=Whitney`
- `KB_APP_URL=https://<domain>`: also the sign-in callback's base, so it must be exactly this KB's public URL
- `SYNC_SCHEDULER_ENABLED=false`
- `OUTBOUND_MODE=off`
- `AI_MODE=off`

**Connector credentials**
- `SLACK_BOT_TOKEN`
- `CLICKUP_TOKEN`, `CLICKUP_TEAM_ID`
- `FATHOM_API_KEY`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`
- `LEADLOCK_*`, with the production redirect URI

Leave `INGEST_WINDOW_DAYS` unset. To bound a source's first copy, set `BACKFILL_DAYS` (JSON, days per source, e.g. `{"gmail": 730}`); unlisted sources copy full history, and `kb backfill --full` overrides it.

### Runbook

Use bash or Git Bash. `railway ssh -s SERVICE -- CMD` runs CMD inside the deployed service.

1. **Deploy.** Deploy `web` first; its pre-deploy step builds the schema. Then deploy the workers, which restart until the schema exists.
2. **Export the configuration** (locally): `python -m backend.scripts.kb config export backend/.local/prod_config.json`. The file holds clients, contacts, people and mappings. It has no source data, no tokens and no LeadLock.
3. **Import it into production:** `railway ssh -s web -- python -m backend.scripts.kb config import - < backend/.local/prod_config.json`. Then delete the file, and check with `kb config`, `kb connectors` and `kb status`.
4. **LeadLock.** In this order:
   - Set `LEADLOCK_APP_CLIENT_ID`, `LEADLOCK_APP_CLIENT_SECRET`, `LEADLOCK_APP_ID`, `LEADLOCK_COMPANY_ID` and the https `LEADLOCK_REDIRECT_URI` on every service (workers refresh tokens too). Startup refuses a partial set.
   - In the Marketplace app: redirect URL `https://<web domain>/api/v1/leadlock/oauth/callback` (exactly `LEADLOCK_REDIRECT_URI`), webhook URL `https://<web domain>/api/v1/leadlock/webhooks` with INSTALL and UNINSTALL on.
   - Stop LeadLock locally first: remove `LEADLOCK_APP_CLIENT_SECRET` from `backend/.env` and run no local workers. The agency refresh token rotates, so only one place may use it.
   - Install from the agency (all sub-accounts, new ones automatically). The callback page says "LeadLock connected".
   - `railway ssh -s web -- python -m backend.scripts.kb leadlock status`, then `… kb leadlock reconcile` (lists sub-accounts and mints their tokens), then `… kb connectors --register leadlock`. Without the register step Connections shows LeadLock as not connected and mapping is refused.
   - `… kb leadlock locations`: map only sub-accounts shown `active`. One mapped earlier starts its first copy by itself once its access works.
   - Map them in Settings → Connections. Each mapping starts its first copy; with the scheduler off, leads stay as of that copy until `kb backfill --full leadlock`.
   - Never uninstall the app afterwards: the agency UNINSTALL webhook revokes production's access.
5. **Backfills.** Each one runs only when you start it. Cheap sources first, Gmail last:
   - `railway ssh -s worker-bulk -- python -m backend.scripts.kb backfill --full slack clickup drive`
   - `railway ssh -s worker-bulk -- python -m backend.scripts.kb backfill --full fathom`
   - `railway ssh -s worker-bulk -- python -m backend.scripts.kb backfill --days 400 calendar`
   - `railway ssh -s worker-bulk -- python -m backend.scripts.kb backfill --days 365 gmail` (takes hours; resumable). The window is sent to Gmail (`after:`), so only that year is read. Spam and trash are never read; inbox, sent and archived mail are. `BACKFILL_DAYS='{"gmail": 365}'` does the same without `--days`. Drive and Fathom always copy their full history.
6. **Watch and control.**
   - `kb status` lists every copy with its run id, pages and counts.
   - `railway logs -s worker-bulk` shows the worker log.
   - `kb run stop <run-id>` and `kb run resume <run-id>` stop and resume a copy.
   - `kb coverage` says whether it's done: one line per live source (`complete`, `complete_with_gaps`, `copying`, `incomplete` with the resume command, `not_started`, `blocked`). It exits 1 until every source holds its history.
   - A page whose worker keeps dying (out of memory, say) is tried 5 times, then its copy shows as `incomplete` (error `crash_loop`) instead of looping. Fix the cause, then `kb run resume`.
7. **The portfolio.** It rebuilds itself after each copy that stored changes, at most every 5 minutes. To rebuild mid-copy, run `kb portfolio refresh`.
8. **When every backfill is done** (`kb coverage` exits 0), set `SYNC_SCHEDULER_ENABLED=true` on worker-sync only, and put worker-bulk back to 1 replica.
9. **Cutover.**
   - On **Command Center**, set `VITE_KNOWLEDGE_BASE_URL=https://<KB domain>/` and redeploy it (the variable is read at build time for the tile and at run time for the hand-off). Its library's Client Knowledge Base tile turns Live.
   - Click **View Here** there: it lands here signed in as you.
   - Check Clients, Leads and Connections.
   - Delete the old MVP service.
   - Remove `mvp/real_index.html` from the repo.

Keep local workers stopped while production copies, so the two don't spend the same Google and Slack rate limits.

### Backups

Railway's volume backups need a Pro workspace, so the `db-backup` cron service keeps its own (the same pattern as the
Content Atelier's). Each night `backend/scripts/backup.py`:

1. dumps the database from one snapshot, so the dump and its row counts describe the same instant while workers write;
2. uploads the dump, streams it back and compares SHA-256 and size;
3. writes the manifest last (a dump without one is unfinished and never offered for restore);
4. every 28 days, restores that dump into a scratch database, compares every table's count, and drops the scratch;
5. only then prunes: the newest 14, one a week for 8 weeks, one a month for 12 months.

Any failure exits non-zero before anything is deleted, and the cron run shows as failed. Check the cron history weekly.

**Setup.**
1. In the KB project: **+ Create → Bucket** (e.g. `kb-backups`). It stays private.
2. **+ Create → GitHub repo**, the same repo and branch as `web`, Dockerfile `/Dockerfile`. Rename it `db-backup`.
3. Settings: custom start command `python -m backend.scripts.backup dump`, cron schedule `15 8 * * *`, restart policy Never. No pre-deploy, no healthcheck, no domain.
4. Variables, on `db-backup` only (not shared):
   - `DATABASE_URL=${{Postgres.DATABASE_URL}}`
   - `BACKUP_BUCKET`, `AWS_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`: references to the bucket's own variables (bucket name, endpoint, access key, secret key, region). Railway buckets use virtual-hosted URLs, the default; `BACKUP_S3_ADDRESSING=path` only for a bucket that says path-style.
5. Run it once by hand (the service's **Run now**) and check its log ends with `"matches": true`. The first run always does the restore check.

**Commands** (`railway ssh -s db-backup -- …`, or locally with the same variables):
- `python -m backend.scripts.backup list`: finished dumps, size, rows, migration, restore check.
- `python -m backend.scripts.backup verify [--key K]`: restore check by hand.
- `python -m backend.scripts.backup counts`: this database's exact counts.
- `python -m backend.scripts.backup fetch FILE [--key K]`: download a dump, checked against its manifest.

**Restore.** `fetch` the dump, create an empty database, then `pg_restore --no-owner --no-acl --exit-on-error -d <new db> FILE`
with a PostgreSQL 18 client (the image has one), compare `backup counts` with the manifest, and point `DATABASE_URL` at it.
Stop the workers first.

**Keep `KB_SECRET_KEY` somewhere safe outside Railway** (a password manager). Connection tokens in the dump are
encrypted with it, so a dump restored without that key has every connection to reconnect. Gmail bodies are never
stored, so they aren't in a dump either; they're read live from Gmail.

## The portfolio in production

`services/read_models/portfolio.py` builds the whole portfolio, in the shape `kbLive.ts` reads. The `portfolio.refresh` job stores it in `read_model_snapshots`. Two routes serve it:

- `GET /api/v1/portfolio` returns the stored build with an ETag, so a repeat load is a 304.
- `GET /api/v1/portfolio/logos/<record id>` reads a chosen logo from Drive on request. The KB stores no image bytes.

The production frontend (`npm run build:live`) fetches the build before any view loads. If there is no build yet, it says so; it never shows sample data. Locally, `python -m backend.scripts.export_frontend_snapshot` still writes the same shape to `frontend/src/kb-live.local.json`.

### Sign-in

**Through Command Center** (production), the same hand-off as the Content Atelier:
1. Command Center's **View Here** opens `/api/auth/knowledge-base/launch` there, which sends the browser to `/api/auth/sso/start` here.
2. This host sends the browser to Command Center's `authorize` with a PKCE challenge, and gets back a 60-second, one-use code.
3. On `/api/auth/sso/callback` it trades the code for the session token on the server backchannel, and keeps that token in its own `wahha_session` cookie (HttpOnly, SameSite=Lax, Secure), with the session's own expiry.
4. Every request is checked with Command Center (`/api/auth/session`), at most every 30 s per session. Team accounts only.

Details:
- A page opened without a session goes through the same sign-in and returns to it, `#route` included.
- **Sign out** revokes the session at Command Center and passes through Command Center's sign-out, which also signs out of the Atelier.
- A sign-out started in Command Center or the Atelier ends this host's session within 30 s.
- Every change (shared edits, AI decisions, skill edits) is recorded as the signed-in person, whatever the app sends.
- Pending sign-ins live in the web process: run one web replica, as the Atelier does.

**Views:** with `RBAC_ENABLED=false` everyone sees what `KB_DEFAULT_VIEWER` (Whitney) sees, and the account area shows the person who signed in, with no switching.

**Fallback:** where Command Center sign-in isn't configured, one shared team password (HTTP Basic, any user name, `KB_TEAM_PASSWORD_HASH`) protects everything. In both modes the signed provider callbacks, the ops API (its own token) and the health checks stay open.

## AI layer (built, off)

Decided 6 Nov: two calls per meeting plus email extraction, all through OpenRouter with zero-retention routing.

| Skill | Runs when | Model | Reasoning |
|---|---|---|---|
| `meeting_digest` (Call 1) | A Fathom transcript lands for an active client | Claude Sonnet 5.5 | medium |
| `team_meeting_digest` | An internal meeting matches `INTERNAL_MEETING_TITLE_PATTERN` | Claude Sonnet 5.5 | medium |
| `call_brief` (Call 2) | A client call is within `AI_BRIEF_LEAD_HOURS`; rebuilt in its last 2 h if stale | Claude Sonnet 5.5 | low |
| `email_actions` | Each client, every `AI_EMAIL_BATCH_HOURS` that has new email | Claude Haiku 5.5 | low |
| `history_moments` | Each client with activity, weekly (a new digest changes its inputs) | Claude Sonnet 5.5 | low |

### What's in `services/ai/`

| File | What it does |
|---|---|
| `skills.py` | The registry of skills |
| `prompts/` | System and user prompts, plus the shared evidence rules |
| `context.py` | Builds each prompt's inputs: transcript, client card, open actions, previous digest, client email (read live from Gmail), internal Slack, Viktor's posts, calendar event, call type, lead figures |
| `contracts.py` | Output schemas, shaped like the Recap and Brief screens |
| `validate.py` | Checks quotes word for word, guards deadlines, and allows owners and refs only from the input |
| `runner.py` | Hash, then AI_MODE, then monthly budget, then call, then checks; writes `ai_runs` and `action_candidates` |
| `sweep.py` | Finds what's due; runs on the AI worker only |
| `present.py` | Puts the results into the portfolio: proposed actions go to admins' review, approved ones become actions |
| `decisions.py` | An admin approves (optionally edited: title, owner, due, side) or rejects a proposed action, once, with an audit event |

### Admin approval of proposed actions

The AI only proposes actions (`action_candidates`, status `proposed`). They wait in the Action Hub's **Needs review**
panel, which only admins see, and reach the Action Hub only once an admin approves them
(`POST /api/v1/actions/proposals/{id}/decision`). Nothing is written to ClickUp.

Until named sign-in exists, the server records the admin the app names, behind the shared team password: anyone
with that password could call the endpoint directly (see the shortcut note in `decisions.py`).

To try the review locally while the AI is off, add a few marked test proposals and remove them afterwards:

```bash
python -m backend.scripts.seed_test_proposals            # "[TEST] …" proposals on up to 4 clients
python -m backend.scripts.seed_test_proposals --remove
```

### Off and live

`AI_MODE=off` is the default. Off means:
- no AI worker;
- a sweep that queues nothing;
- a job that refuses to run.

Live needs `OPENROUTER_API_KEY` and an `AI_MONTHLY_BUDGET_USD` above 0. Before switching it on, run:

- `kb ai check`: shows the settings and this month's spend, and checks each model id against OpenRouter's public model list.
- `kb ai due`: shows what would run now.
- `kb ai preview meeting_digest <fathom record id> --out backend/.local/preview.md`: writes the exact prompts built from real data, with refs and clipping. Nothing is sent. Add `--no-email` to skip reading Gmail.
- `kb ai runs`: the run log with tokens and cost. Failed runs are there too, with what they cost: a schema failure
  after the repair (both calls billed), a timeout (charged at the skill's reserve, `cost_estimated`), or anything
  that broke after a paid answer. The monthly budget counts them all.
- `kb ai retry [SKILL]`: queue AI jobs that failed for good again, once the cause is fixed.

When things go wrong:
- **OpenRouter down, slow or rate-limited:** the job retries over about 11 hours (1, 5, 30 min, 1, 3, 6 h), then
  fails visibly. Call briefs keep the short ladder (a late brief is useless; the sweep queues a fresh one).
- **Out of OpenRouter credits (402):** jobs wait 6 h, like the monthly budget. **Refused request (400/401/403/413)**
  or **schema still broken after the repair:** the job fails at once (retrying the same input can't help).
- **Gmail credential lost or throttled:** the run stops before anything is sent and waits; it never runs on half
  the email. A message deleted since intake is skipped and counted as clipped.
- **Missed email windows:** the sweep looks back 7 windows, so a window that closed while the AI worker was down is
  still read.
- **Re-digests:** a new Fathom version with the same transcript words is not digested again. When the words did
  change, the re-digest sees the meeting's approved actions as WIA's list, and code drops any proposal an admin
  already approved or rejected from that meeting (`already_decided` in the run's checks).
- **The client recap email:** the model writes it line by line with refs. Code keeps a line only when it cites the
  transcript or the client's own non-finance email, copies no 6-word run from internal Slack or Viktor, and uses no
  figure its sources don't hold. With nothing left, there is no draft and the host writes it.

## Call preparation

Design: `docs/CALL_PREPARATION_ARCHITECTURE.md`; build order: `docs/CALL_PREPARATION_IMPLEMENTATION_PLAN.md`.

- **Code computes, the model synthesises.** `services/callprep/facts.py` computes everything countable (owed,
  late, asks, emails awaiting our reply, promises from the last digest, what changed, lead and ad figures, limits).
  It runs on every portfolio build, so the screen is useful with the AI off.
- **One model call per brief** (`call_brief`), over a pack built from only the blocks the call type's skill asks for
  (`services/callprep/pack.py`). Checks before storing (`checks.py`): refs, no figure that isn't in the evidence,
  the skill's length caps and leave-out terms. A failed core gets one repair, then the brief is rejected and the
  facts and the previous version stay.
- **Skills** are files (`services/callprep/skills/*.md`), seeded into `call_skills` by `kb callprep seed` and
  edited in the app as new versions. Each brief records the skill version it used.
- **When:** the AI sweep builds a brief 24 h before the call, rebuilds at T-2 h only if its inputs changed (a
  fingerprint of pointers, never email bodies), and after a skill edit. *Regenerate with instructions* runs a short
  Haiku pass that may fetch up to 4 more of this client's items, then the brief.
- **No Viktor data:** bot-authored Slack threads are left out of the History lane call prep reads, and Viktor's
  posts are not a block.

Operator commands: `kb callprep seed | calls | facts CALL | preview CALL [--no-email] | due`.

### Ad platforms (Google Ads MCC, Meta)

Scripts, not an MCP: `services/ads/google_ads.py` (GAQL searches only) and `services/ads/meta.py` (GET insights only).
Figures are campaign totals per day in `ad_daily`, only for accounts mapped to a client.

1. Credentials in `backend/.env` (see `.env.example`). Google: `kb ads google-auth` prints the refresh token after
   you sign in with an account that can see the MCC. Meta: in WIA's Business portfolio, create a Business-type app and a system user,
   assign it each client ad account with *View performance* only, and generate a never-expiring token
   with `ads_read` only (`META_ACCESS_TOKEN`; `META_BUSINESS_ID` is not needed).
2. `kb ads discover` lists every account each platform shows, with a suggested client.
3. `kb ads map google_ads <account id> <client slug>` (or `meta`). `none` unmaps and deletes that account's figures.
4. `kb ads pull` reads 90 days the first time, then the last 7 every day (the worker queues one pull a day while
   any platform is configured). `kb ads summary <client slug>` shows what call prep will show.

## Layout (SOP)

| Path | Contents |
|---|---|
| `routes/` | Health, ops API (`X-Ops-Token`), team API and portfolio (`access.py`: the shared team password) |
| `services/intake/adapters/` | The only code that knows a provider API |
| `services/intake/` | Provider-neutral pipeline, persistence, discovery, connectors, durable sync |
| `services/clients/` | Client registry and mapping commands |
| `services/people/` | Roster, identity resolution, account teams |
| `services/read_models/` | Leads and the portfolio build |
| `services/ai/` | AI layer: skills, prompts, context, checks, runner (off by default) |
| `docs/` | Schema (DBML), B-02 publication contract, S3 plan and validation |
| `models/db/` | ORM mappings |
| `models/domain/` | Intake types |
| `sql/migrations/` | Alembic |
| `workers/` | Queue, runner, jobs |
| `scripts/kb.py` | Operator CLI |
