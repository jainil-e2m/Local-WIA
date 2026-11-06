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
It serves only when `ENVIRONMENT=local` (no KB login yet, S10). The definitions are in the module docstring:
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

Endpoints (local only until S10 adds an admin session; the audit actor is a placeholder until then):
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
| Postgres | Railway template | Backups on. Watch the volume during the Gmail copy |
| web | image default (uvicorn on `$PORT`) | Pre-deploy: `alembic -c backend/alembic.ini upgrade head`. Healthcheck: `/health/ready`. Public domain |
| worker-bulk | `python -m backend.workers.runner --lanes bulk,maintenance` | No domain. 2 replicas during the first backfills, then 1 |
| worker-sync | `python -m backend.workers.runner --lanes sync` | No domain. Once the backfills are done, the only service with `SYNC_SCHEDULER_ENABLED=true` |
| worker-ai | not created | Later: `--lanes analysis` with `AI_MODE=live` |

### Shared variables

Set these at project level and reference them from every service.

**Core settings**
- `PRODUCTION_MODE=true`
- `DATABASE_URL`: a reference to the Postgres service's `DATABASE_URL`, as-is (the backend switches its `postgresql://` scheme to the psycopg 3 driver)
- `KB_SECRET_KEY`: a new one, not the local key
- `OPS_TOKEN`
- `KB_TEAM_PASSWORD_HASH`: from `kb password-hash`
- `KB_APP_URL=https://<domain>`
- `SYNC_SCHEDULER_ENABLED=false`
- `OUTBOUND_MODE=off`
- `AI_MODE=off`

**Connector credentials**
- `SLACK_BOT_TOKEN`
- `CLICKUP_TOKEN`, `CLICKUP_TEAM_ID`
- `FATHOM_API_KEY`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`
- `LEADLOCK_*`, with the production redirect URI

Leave `INGEST_WINDOW_DAYS` unset.

### Runbook

Use bash or Git Bash. `railway ssh -s SERVICE -- CMD` runs CMD inside the deployed service.

1. **Deploy.** Deploy `web` first; its pre-deploy step builds the schema. Then deploy the workers, which restart until the schema exists.
2. **Export the configuration** (locally): `python -m backend.scripts.kb config export backend/.local/prod_config.json`. The file holds clients, contacts, people and mappings. It has no source data, no tokens and no LeadLock.
3. **Import it into production:** `railway ssh -s web -- python -m backend.scripts.kb config import - < backend/.local/prod_config.json`. Then delete the file, and check with `kb config`, `kb connectors` and `kb status`.
4. **LeadLock.**
   - Point the Marketplace app's redirect and webhook URLs at the production domain.
   - Install it from the agency.
   - Stop using it locally: its refresh token rotates.
   - Check with `kb leadlock status`.
   - Map the sub-accounts in the production Connections tab. Each mapping queues its first copy.
5. **Backfills.** Each one runs only when you start it. Cheap sources first, Gmail last:
   - `railway ssh -s worker-bulk -- python -m backend.scripts.kb backfill --full slack clickup drive`
   - `railway ssh -s worker-bulk -- python -m backend.scripts.kb backfill --full fathom`
   - `railway ssh -s worker-bulk -- python -m backend.scripts.kb backfill --days 400 calendar`
   - `railway ssh -s worker-bulk -- python -m backend.scripts.kb backfill --days 365 gmail` (takes hours; resumable)
6. **Watch and control.**
   - `kb status` lists every copy with its run id, pages and counts.
   - `railway logs -s worker-bulk` shows the worker log.
   - `kb run stop <run-id>` and `kb run resume <run-id>` stop and resume a copy.
7. **The portfolio.** It rebuilds itself after each copy that stored changes, at most every 5 minutes. To rebuild mid-copy, run `kb portfolio refresh`.
8. **When every backfill is done**, set `SYNC_SCHEDULER_ENABLED=true` on worker-sync only, and put worker-bulk back to 1 replica.
9. **Cutover.**
   - Sign in on the new domain with the team password.
   - Check Clients, Leads and Connections.
   - Delete the old MVP service.
   - Remove `mvp/real_index.html` from the repo.

Keep local workers stopped while production copies, so the two don't spend the same Google and Slack rate limits.

## The portfolio in production

`services/read_models/portfolio.py` builds the whole portfolio, in the shape `kbLive.ts` reads. The `portfolio.refresh` job stores it in `read_model_snapshots`. Two routes serve it:

- `GET /api/v1/portfolio` returns the stored build with an ETag, so a repeat load is a 304.
- `GET /api/v1/portfolio/logos/<record id>` reads a chosen logo from Drive on request. The KB stores no image bytes.

The production frontend (`npm run build:live`) fetches the build before any view loads. If there is no build yet, it says so; it never shows sample data. Locally, `python -m backend.scripts.export_frontend_snapshot` still writes the same shape to `frontend/src/kb-live.local.json`.

### The team password

Until named Google sign-in exists, one shared team password protects everything except the signed provider callbacks, the ops API and the health checks. It uses HTTP Basic with any user name (`routes/access.py`). Approving AI actions waits for named sign-in.

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
| `present.py` | Puts the results into the portfolio |

### Off and live

`AI_MODE=off` is the default. Off means:
- no AI worker;
- a sweep that queues nothing;
- a job that refuses to run.

Live needs `OPENROUTER_API_KEY` and an `AI_MONTHLY_BUDGET_USD` above 0. Before switching it on, run:

- `kb ai check`: shows the settings and this month's spend, and checks each model id against OpenRouter's public model list.
- `kb ai due`: shows what would run now.
- `kb ai preview meeting_digest <fathom record id> --out backend/.local/preview.md`: writes the exact prompts built from real data, with refs and clipping. Nothing is sent. Add `--no-email` to skip reading Gmail.
- `kb ai runs`: the run log with tokens and cost.

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
