# Deploying to Railway

Runbook for this service. Written to be followed cold, in order, by someone
who has not read the rest of the repo.

- **Repo:** `jainil-e2m/WIA-Command-Center` — **this directory is the repo root**
- **Ships as:** one Docker image. Node build stage → `dist/`, served by the
  Express server in `server/`, which also owns `/api/*`
- **Verified on:** 2026-09-08, against the exact container command
  (`node server/index.mjs`, no env files)

---

## 0. Two things to settle before you push

**a) The repository HAS commits.** This was written when it did not, and the
instruction to treat the first push as the first commit is now stale — `git
log` shows tracked history on `main`. Check the working tree before pushing
rather than assuming everything is untracked:

```bash
git log --oneline | head
git status --short
```

The `.gitignore` review below still matters, because the client data note in
(b) still applies.

**b) Confirm the GitHub repo is private.** `server/onboarding-templates.json`
is generated from the client's real ClickUp workspace: real list names, real
task names, real assignees. It is committed on purpose — the onboarding console
needs it — but it is client operational data. If that repo is public, make it
private before the first push.

```bash
gh repo view jainil-e2m/WIA-Command-Center --json visibility
```

Separately: `.env.local` holds a live personal ClickUp `pk_` token that was
pasted into a chat transcript. It is gitignored and never enters the image
(`.dockerignore` strips every `.env*`), so it will not leak through this
deploy — but it should still be revoked in ClickUp. Nothing in the running app
reads it; only the three offline fetch scripts do.

---

## 1. Push

```bash
git add -A
```

Check what that staged before committing — the first commit sets the tone for
the repo's history:

```bash
git status --short
```

You should see `src/`, `server/`, `public/`, `Dockerfile`, `railway.json`,
`package.json`, `README.md`, `DEPLOY.md` and friends. You should **not** see
`.env`, `.env.local`, `.env.bak-presync`, `node_modules/`, `dist/`,
`coverage/`, `.data/` or `.claude/settings.local.json`. If any of those appear,
stop and fix `.gitignore` first.

```bash
git commit -m "Initial commit: WIA Command Center"
```

```bash
git push -u origin main
```

## 2. Create the Railway service

1. Railway → **New Project** → **Deploy from GitHub repo** → select
   `jainil-e2m/WIA-Command-Center`.
2. **Leave Root Directory empty.** This directory is the repo root; `Dockerfile`
   and `railway.json` are at the top level. Setting `frontend` here is the one
   mistake that fails the build instantly — see the note in
   [README § Railway](README.md#railway).
3. Set the service settings by hand — see the table below.

> ### `railway.json` IS NOT READ BY THIS SERVICE
>
> Railway deprecated Config-as-Code, and **services that have never used it
> cannot opt in after 2026-08-28**. This service was created after that date
> with an empty *Railway Config File* field, so `railway.json` is inert: it is
> kept only as a record of intent (and for a future migration to Railway's
> Infrastructure-as-Code). **The dashboard is the source of truth.** If you
> change the health check or the builder, change it in the UI — editing
> `railway.json` will do nothing.

### Service settings (Settings tab)

| Setting | Value | Why |
|---|---|---|
| Root Directory | `/` | This directory *is* the repo root. `frontend` breaks the build. |
| Builder | **Dockerfile** | Not a preference — **mandatory**. The default is Railpack, and the root `package.json` has **no `start` script**, so Railpack builds and then has nothing to run. Its fallback (`vite preview`) serves static files with no `/api/*` and no auth, so login itself would break. |
| Custom Build Command | *empty* | The Dockerfile owns the build. |
| Custom Start Command | *empty* | Setting one overrides the image's `CMD ["node","server/index.mjs"]`. |
| Healthcheck Path | `/health` | Verified to return `200 ok`. Without it Railway marks a deploy live before Express is listening. |
| Restart Policy | On Failure | Retries at the plan cap (10) are fine. |
| Serverless / scale-to-zero | **OFF** | Scale-to-zero queues the first request while the container wakes. Fine for a hobby app, wrong for a live client walkthrough. |
| Watch Paths | *empty* | Only this directory is tracked, so nearly every commit should rebuild. |
| Under Attack Mode | OFF | Puts a browser challenge in front of the domain. |
| CDN Caching | OFF | Unnecessary. The server already sends `immutable` on `/assets` and `no-cache` on `index.html`; adding an edge layer only adds a way to serve a stale bundle. |
| Pre-deploy step / Cron | none | |
| Region / Replicas | US East, 1 | |

### Networking

Target port **8080**, matching `EXPOSE 8080` and the `PORT=8080` variable
below. Both halves must agree or the domain 502s against a listening server.

## 3. Variables

### Set these

**Three variables. That is the whole list.**

| Variable | Value | Why |
|---|---|---|
| `PORT` | `8080` | `server/index.mjs:112` reads `Number(env("PORT") ?? 8787)`. A Railway-injected `PORT` overrides the Dockerfile's `ENV PORT=8080`, so pinning it is what guarantees the server listens on the port the domain's target port sends to. Without it a mismatch is a 502 against a perfectly healthy server. |
| `AUTH_DISABLED` | `1` | Demo mode — see below. |
| `VITE_AUTH_DISABLED` | `1` | Demo mode — see below. |

There is no `openssl` on Windows PowerShell. Where a random hex value is needed
(only if you turn auth back on), use Node, which is already installed:

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### Demo mode: no login at all (the current choice)

### An unlisted URL is not an access boundary

This deployment runs with **auth fully bypassed**, and that is a real
decision rather than a detail. Two things follow from it, and they were in
tension with the README and parts of the proposal, which describe the preview
as protected or internal:

1. **Anyone with the URL is in.** No login, no session, every `/api/*` route
   open. "Unlisted" means unindexed, not private — a link forwarded once is a
   link that works forever.

2. **Not every dataset in this build is synthetic.** The Ops Hub is; the
   ClickUp onboarding templates are real WIA operational data, the roll-call
   Google transcript is a real members' session with real member names, and
   the Vault content walks real client analytics. The full breakdown is on the
   Source Coverage screen under "What each dataset actually is".

**Before sharing this URL outside WIA and E2M, pick one:** turn auth on (below),
or replace the real fixtures with sanitised ones. Verify the deployed
configuration at the time of sharing rather than trusting this document —
environment variables change without a commit.
That is a deliberate decision, not an oversight, and it needs **both** halves —
the React route guard and the API gate are separate boundaries:

| Variable | Value | Kind |
|---|---|---|
| `AUTH_DISABLED` | `1` | **Runtime.** Opens every `/api/*` route and makes `/api/auth/login` accept any email with any non-empty password. |
| `VITE_AUTH_DISABLED` | `1` | **Build arg.** Opens the route guard in `src/components/RequireAuth.tsx` so no login screen appears. |

Two things about this that will bite if you don't know them:

1. **`VITE_AUTH_DISABLED` needs an `ARG` in the Dockerfile, which it now has.**
   Railway exposes service variables as build args, and one with no `ARG`
   declared is *silently dropped*. Before this was added, setting it would have
   changed nothing while appearing to work — leaving the worst half-state: API
   wide open, login screen still in the way. Verified by building both ways:
   the entry chunk hashes differ (`index-DMw3HQNZ.js` guard on,
   `index-CQtMmdeS.js` guard off), so the flag really is compiled in.
2. **Being a build arg, it takes a REDEPLOY to change — not a restart.** Its
   server-side twin `AUTH_DISABLED` is runtime and takes effect on restart.
   Flip both together or you get a half-state.

With both set, `AUTH_EMAIL` / `AUTH_PASSWORD_HASH` / `AUTH_NAME` become
irrelevant — no credential is checked. `SESSION_SECRET` also stops mattering,
since nothing depends on a session surviving a restart.

Verified against a production build (`NODE_ENV=production`, `AUTH_DISABLED=1`,
guard-off bundle): `/api/onboarding` with no cookie → `200` (was `401`), login
with any credentials → `200`, and `/ops-hub` renders the hub directly with no
redirect to `/login`.

**What this means, stated plainly:** anyone with the URL has full access to
everything the app renders — including the two real verbatim call transcripts
and the client's real ClickUp task structure under `/onboarding`. That is
acceptable while the URL is unlisted and the data is a mock. It stops being
acceptable the moment the link is shared outside the team.

### To turn auth back on

Delete both variables and redeploy, then set `AUTH_EMAIL`,
`AUTH_PASSWORD_HASH` (via `node server/hash-password.mjs "…"`), `AUTH_NAME` and
`SESSION_SECRET`. Deleting only `AUTH_DISABLED` leaves the guard bypassed and
every fetch 401ing; deleting only `VITE_AUTH_DISABLED` leaves a login screen
that any password opens. The server prints a large boot banner whenever
`AUTH_DISABLED=1` meets `NODE_ENV=production` — that banner in the Railway
deploy logs is how you confirm which mode you are actually in.

### Deliberately not needed

- **Nothing for the Operations Hub.** `/ops-hub` is a mock end to end: eight
  screens running in the browser off `src/data/opsHub.ts`, no `/api/ops-hub`
  route, no connector, no persistence. No URL, token, flag or volume.
- **Nothing for `/onboarding`.** It reads the committed
  `server/onboarding-templates.json` and issues no ClickUp calls at all, so
  `CLICKUP_TOKEN` is not a production variable.
- **The audit BFF variables** (`TECHNICAL_SEO_*`, `AI_SEO_*`,
  `AI_PRESENCE_*`, `ON_PAGE_SEO_*`, `LEAD_MAGNET_*`). Leave them unset and
  those tiles report unusable at boot — which is accurate. The rest of the app,
  including the Ops Hub, is unaffected.
- **`VITE_TOOL_*_ENABLED` flags.** Blank means "the committed status in
  `src/data/tools.ts` wins". Note these are *build args*: changing one needs a
  **redeploy**, not a restart.

### Optional: a volume

Bookmarks and captured leads are JSON files on the container filesystem, which
Railway **replaces on every deploy**. The boot log warns about both. Neither
affects the Ops Hub or the onboarding console, so for a demo deployment this is
fine to skip. To make them survive, mount a volume at `/data` and set:

```
BOOKMARKS_FILE=/data/bookmarks.json
LEADS_FILE=/data/leads.json
```

## 4. Verify the deploy

Substitute your Railway domain. All four of these were confirmed locally
against the real container command before this was written.

```bash
curl -s -w " [%{http_code}]\n" https://YOUR-APP.up.railway.app/health
```

Expect `ok [200]`.

```bash
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" https://YOUR-APP.up.railway.app/ops-hub
```

Expect `200 text/html`. This is the check that matters for the new route: it
proves the SPA fallback serves `index.html` for a path React Router owns, so a
hard refresh or a pasted deep link works. The fallback is unconditional for
GET/HEAD, so every client route behaves the same way.

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://YOUR-APP.up.railway.app/api/onboarding
```

In **demo mode** (the current configuration) expect **`200`** — the API is
deliberately open. A `401` means `AUTH_DISABLED` did not take effect. With auth
switched back on, expect `401` instead. Either way, this is the single call
that tells you which mode you actually got, rather than which one you intended.

Then load `/ops-hub` in a browser — this checks the *other* half:

- **Renders the hub immediately** → both flags landed. Correct.
- **Redirects to `/login`** → the runtime flag is set but
  `VITE_AUTH_DISABLED` never reached the build. Confirm it is a service
  variable, confirm the Dockerfile still declares its `ARG`, and **redeploy**
  (a restart will not do it — it is a build arg).

Finally confirm the **Operations Hub** button on the hero (centred below *View
Automations* and the Website / Lead Lock / The Vault pill) lands on `/ops-hub`
with the sidebar and all eight screens.

## 5. Local parity, before you blame Railway

Build and run the same image locally:

```bash
docker compose up --build
```

Then hit `http://localhost:8080/health` and `http://localhost:8080/ops-hub`.

Or run the production server against a fresh build without Docker — this is the
closest reproduction of the container, because it loads no env files:

```bash
npm run build
```

```bash
PORT=8099 NODE_ENV=production node server/index.mjs
```

---

## Known state, so nothing surprises you

- **`nginx/default.conf.template` is dead code.** The Dockerfile's production
  stage is Node — its own comment says it replaced the earlier nginx stage — and
  nothing builds or copies that template any more. It is a trap for whoever
  next tries to change a cache header or a security header: the live policy is
  in `server/index.mjs` (the `express.static` `setHeaders` block and the
  fallback). Worth deleting; left in place because deleting it is your call.
- **Two tests fail, and they are pre-existing.** `640 passed, 2 failed`, both in
  `server/favicon-resolver.test.mjs` (SSRF boundary and PWA icon picking),
  documented as pre-existing and unrelated. Everything else passes; type-check
  and lint are clean.
- **`useLocationSuggestions` is an 8.7 MB chunk** (2.3 MB gzipped) — a location
  dataset, pre-existing, and the actual bundle problem in this repo. It is
  lazy-loaded, so it does not affect first paint. For contrast `OpsHubPage` is
  130 kB (34 kB gzipped).
- **`package.json` is still named `wahha-automation-hub`** and the server
  package `wahha-central-server`. Deliberate: the names tie into the Docker and
  repo configuration and renaming them was scoped out.
