# Deploy Content Atelier to Railway

> **Calendar release, 16 October 2026:** the current app uses backend angle/brief
> review, real pack storage and backend schedules. Follow
> [Calendar Deployment](backend/docs/Calendar-Deployment.md) for the required
> migration, API/BFF variables, capabilities and editorial worker. Descriptions
> of the mock workflow below document the earlier deployment and are historical.


Deploy the **frontend** for the current Weekly Studio experience. It contains the
four source-based angles, complete briefs, saved pack templates and scheduling
simulation. It follows Command Center's deployment pattern: a multi-stage Docker
build and a Node/Express production server. Vite is used only during the build.

The Python backend is a separate intake/ledger service. Deploying that service by
itself does **not** deploy the Content Atelier UI.

## 1. Create the frontend service

Connect `jainil-e2m/WIA-Content-Atelier` to a new Railway service. This repository
contains `frontend/` and `backend/` at its root. Use these settings:

| Setting | WIA-Content-Atelier repository | Only the frontend folder as repository |
| --- | --- | --- |
| Root Directory | `/frontend` | Leave empty (`/`) |
| Dockerfile | `Dockerfile` within the service root | `Dockerfile` |
| Build command | Leave empty; Dockerfile runs `npm ci` and `npm run build` | Same |
| Start command | Leave empty; Dockerfile runs `node server/index.mjs` | Same |
| Healthcheck path | `/health` | `/health` |
| Healthcheck timeout | 60 seconds | 60 seconds |
| Restart policy | On failure, maximum 3 retries | Same |

Railway detects a Dockerfile in the service root. The server listens on Railway's
injected `PORT`; no port variable or custom start command is needed. Generate a
public domain in the service's Networking settings after the build succeeds.

**Current Railway configuration behavior:** new services use dashboard settings
or Railway IaC. The included `frontend/railway.json` preserves the Command Center
format for existing legacy services. It does not configure a newly created
service. Set the healthcheck and restart settings above in the dashboard. Railway
documents a hard cutoff of December 1, 2026 for legacy config files; Dockerfile
builds remain supported. See [Railway config reference](https://docs.railway.com/config-as-code/reference),
[IaC](https://docs.railway.com/infrastructure-as-code) and
[Dockerfiles](https://docs.railway.com/builds/dockerfiles).

For a legacy monorepo service only, the config-file path is
`/frontend/railway.json`. If the frontend is its own repository,
the file is already at the root. These paths describe the two repository layouts;
do not add `/frontend` to a repository whose top level is already this folder.

## 2. Set the frontend runtime variable

| Variable | Value |
| --- | --- |
| `COMMAND_CENTER_AUTH_ORIGIN` | The deployed Command Center server origin, e.g. `https://your-command-center.up.railway.app` |
| `COMMAND_CENTER_PUBLIC_ORIGIN` | Only needed if the auth origin above is private: the public HTTPS Command Center origin for browser redirects |

Use an origin with no `/login`, `/api`, credentials, query string or other path.
The public HTTPS origin works across Railway projects. If both services share a
Railway project/environment, you can use Command Center's private HTTP origin
with its listening port instead, e.g. `http://command-center.railway.internal:8080`.
Use the actual service hostname and port from Railway. With a private auth origin,
set `COMMAND_CENTER_PUBLIC_ORIGIN` as well so the browser can reach the login handoff.

`NODE_ENV=production` is already set by the Dockerfile. The server refuses to
start when `COMMAND_CENTER_AUTH_ORIGIN` is missing or invalid. API keys, database
credentials and `SESSION_SECRET` are **not** frontend variables. There are no
required `VITE_` build variables for this deployment.

## 3. Sign in and connect the Command Center link

When signed into Command Center, click **View Here**. Its launcher redirects through
Atelier's `/api/auth/sso/start`, then Command Center validates the existing session
and issues a 60-second code for the exact Atelier callback. Atelier verifies its
browser state and redeems that code with a server-held PKCE verifier. It sets its
own signed, HttpOnly session cookie and opens the workspace as the same user.
The session token stays on the server backchannel. Both apps must be redeployed
with these endpoints for automatic sign-in to work.

Visiting Atelier directly still provides `/login`. It forwards credentials to the
existing Command Center account service. Session checks and logout also use that
service. Account and password configuration stay in Command Center.
Use its production account configuration and a stable `SESSION_SECRET` there.
Unset Command Center's `AUTH_DISABLED` and `VITE_AUTH_DISABLED` demo bypasses for
production account verification.

Separate Railway domains retain separate host-only cookies; the handoff connects
them without broadening cookie domains. Signing out of Atelier clears its cookie;
an existing Command Center tab retains its own cookie. The copied session retains
its original expiry. Keep both app services at one replica for this prototype's
process-local code and state stores; interrupted handoffs fail closed and can be
restarted from Command Center. Existing session verification still runs there.

On the **Command Center** Railway service, set
`VITE_CONTENT_ATELIER_URL=https://your-content-atelier.up.railway.app` and redeploy
that service to update its Content Atelier destination button and pin the handoff
callback. Keep this public URL available at runtime and build time; use the frontend
domain, not the Python API domain. No additional shared secret is required.

The Atelier server validates the session before serving HTML and compiled assets
because the mock library includes meeting-derived material. It exposes the three
existing account endpoints and the constrained SSO handshake, not Command Center's
other APIs. The code flow follows [PKCE and redirect protections](https://www.rfc-editor.org/rfc/rfc9700.html).

## 4. What the deployed mock supports

- Weekly Studio: angles → briefs → packs → publishing review → simulated scheduling.
- The content inspector includes a Schedule tab, enabled after the pack is approved
  for publishing. Its shared date/time picker saves to Scheduled Content and Home.
- The four saved analyses and pack templates are included in the production build.
- All four current concepts start in Content Angles. Use individual approvals to
  move them into Briefing and Content Packs; there are no replay controls.
- Edits, approvals and schedule dates persist in that browser's local storage.
  Each new Atelier deployment resets the four sourced mock concepts to Content
  Angles and clears their approval/schedule progress; source analysis, brief edits
  and saved pack templates remain attached. Refreshing within the same deployment
  retains progress. Other library records retain their progress.
  The server uses Railway's runtime `RAILWAY_DEPLOYMENT_ID` automatically (see
  [Railway variables](https://docs.railway.com/variables/reference)); no new variable
  is required. Outside Railway, a server restart starts a new mock run.
- No database, AI provider key, Fathom key or Slack key is required for this UI.
- Local storage is specific to the browser and domain. It is not a shared team
  database, and changing domains does not migrate existing local edits.
- Scheduling remains a simulation; deploying the UI does not publish to external
  channels or connect the mock workflow to the Python ledger.

`.dockerignore` excludes environment files, dependency folders, test fixtures,
local caches and raw corpus exports. The Dockerfile copies only UI build inputs
and the production server. The backend corpus stays outside this build context.

## 5. Local verification

Run from `frontend` within this repository:

```powershell
npm ci
npm --prefix server ci --omit=dev
npm run lint
npm test
npm run build
$env:COMMAND_CENTER_AUTH_ORIGIN = 'http://localhost:8787'
$env:PORT = '8080'
npm start
```

This local server uses the running Command Center auth server. `npm start` reads
`.env` and `.env.local` if present; explicit environment variables take precedence.
For local HTTP verification, leave `NODE_ENV` unset. Production Docker sets it to
`production` and issues Secure cookies for the Railway HTTPS domain.

With Docker Desktop running, from the same directory:

```powershell
$env:COMMAND_CENTER_AUTH_ORIGIN = 'http://host.docker.internal:8787'
docker compose up --build
```

`host.docker.internal` reaches the Windows host from Docker; `localhost` inside a
container would refer to the container itself. Compose overrides `NODE_ENV` for
local HTTP verification. Railway uses the Docker image's production default and
Secure cookies behind its HTTPS ingress.

After deployment, confirm `/health` returns 200, an anonymous `/` redirects to
`/login`, a valid account opens the studio, an invalid password is rejected, the
Weekly Studio starts with four waiting angles, individual approvals advance them,
and signing out hides the workspace.

## Optional: deploy the live Python backend

Create another Railway service with Root Directory `/backend`
(or `/` if that folder is its own repository). Its existing Dockerfile starts
FastAPI on `PORT`. Configure `/health`, a 120-second startup healthcheck timeout,
On Failure restart policy and one replica. The startup hook applies the existing
idempotent database schema; no extra start/pre-deploy command is required.

Add a **separate** Railway Postgres and set:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Reference the Atelier Postgres connection string |
| `ATELIER_API_TOKEN` | Private service bearer token |
| `ATELIER_WHITNEY_EMAIL` | Account permitted to approve live ledger gates |
| `OPENROUTER_API_KEY` | Required for extraction, triage and model generation |
| `FATHOM_API_KEY` / `FATHOM_WEBHOOK_SECRET` | Live Fathom intake credentials |

For nightly Slack intake, configure the `SLACK_*` variables described in
[`backend/.env.example`](backend/.env.example) and keep the service running. Its
scheduler runs in the API process. Brand context/corpus seeding is an explicit
step; raw local transcripts and founder documents are not baked into the image.
See [`backend/README.md`](backend/README.md) for the existing seed/backfill CLIs.

Command Center's backend-for-frontend can connect to this separate API with its
server-only `CONTENT_ATELIER_URL` and matching `CONTENT_ATELIER_API_TOKEN`.
`VITE_CONTENT_ATELIER_URL` still points to the UI. These are three different
settings; deploying both services does not itself replace the UI's local mocks
with live API data.
