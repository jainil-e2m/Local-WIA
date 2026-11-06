# Wedding Industry Ads — AI Command Center

Central dashboard for Wedding Industry Ads to reach every automation from one
place, plus the client-facing mockups that accompany the AI Blueprint: the AI
Operations Hub (`/ops-hub`), Client Onboarding (`/onboarding`), Internal Meeting
+ Action Items (`/internal-meeting`) and Office Hours Roll Call (`/roll-call`).

Forked from the Wahha Design automation hub, which is why some inherited audit
products (Technical SEO, AI SEO, AI Presence, On-Page SEO, Lead Magnet) are
still in `src/data/tools.ts` marked `hidden: true` — live at their own URLs,
kept out of this client's library.

## Tech stack

The Lovable "classic" stack:

- **React 18** + **TypeScript**
- **Vite** (build tool / dev server)
- **Tailwind CSS** + **shadcn/ui** (Button, Badge in `src/components/ui/`) on Radix primitives
- **Framer Motion** for all animation
- **React Router** (ready for adding tool sub-pages)
- **lucide-react** icons

No SSR — it's a client-side SPA served (together with its auth API) by a small
**Express** server in `server/`. Deployed on **Railway** via the Dockerfile in
this repo (see [Deployment](#deployment)).

## Getting started

```bash
npm install
npm run dev:api    # auth/static server on http://localhost:8787 (separate terminal)
npm run dev        # http://localhost:5173 (proxies /api → :8787)
npm run build      # outputs to dist/
npm run preview    # preview the production build (no /api — use docker compose)
```

Node version is pinned in `.nvmrc` (run `nvm use`). Run `npm install` inside
`server/` once before the first `npm run dev:api`.

## Authentication

The dashboard is protected by a single pre-seeded account (no registration or
user management). The Express server in `server/index.mjs`:

- verifies the password against an **scrypt hash** (plaintext is never stored),
- issues an **HMAC-signed, HttpOnly session cookie** (`SameSite=Lax`, `Secure`
  behind HTTPS, 7-day TTL),
- rate-limits `/api/auth/login` per IP,
- exposes `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/session`.
- proxies authenticated Technical SEO API and SSE calls under
  `/api/technical-seo/*`, adding the private upstream bearer token server-side.

The landing page (`/`) and `/login` are public; every other route redirects to
`/login` until signed in (see `src/components/RequireAuth.tsx` and
`src/context/AuthContext.tsx`).

Defaults ship in the image so a fresh deploy works out of the box; override via
env vars (see `.env.example`): `AUTH_EMAIL`, `AUTH_PASSWORD_HASH` (generate with
`node server/hash-password.mjs "new-password"`), `AUTH_NAME`, and
`SESSION_SECRET`. In production (`NODE_ENV=production`) `AUTH_PASSWORD_HASH` and `SESSION_SECRET` are required
and `AUTH_DISABLED` is refused: the server exits at start, naming what is missing (S.C1).

**Adding another sign-in.** Accounts are configuration, not code. Beyond the
seeded `AUTH_*` account and the optional `CLIENT_*` one, set a numbered slot —
`USER_1_EMAIL` + `USER_1_PASSWORD_HASH` (plus optional `USER_1_NAME` and
`USER_1_ROLE`, which is `team` or `client` and defaults to `client`) — and
redeploy. Slots run `USER_1_*` to `USER_20_*` and gaps are ignored. Generate the
hash with `node server/hash-password.mjs "their-password"` and paste only the
`scrypt$…` output; the plaintext never enters the repo or the variables. The
boot log lists every account it resolved, and any half-configured or duplicate
slot is reported there as an `[auth]` warning.

## Quality & testing

```bash
npm run lint          # ESLint (flat config, eslint.config.js)
npm run lint:fix      # ESLint with autofix
npm run format        # Prettier — write
npm run format:check  # Prettier — check only (CI-friendly)
npm run type-check    # tsc project references, no emit
npm test              # Vitest (run once)
npm run test:watch    # Vitest watch mode
npm run test:coverage # Vitest with V8 coverage report
```

Tests use **Vitest** + **React Testing Library** (jsdom). Test files live next to
the code they cover as `*.test.ts(x)`; global setup is in `src/test/setup.ts`.

## Wiring the automation dashboards

Everything is driven by one typed config: **`src/data/tools.ts`**.

Each tool object:

```ts
{
  id: "technical-seo",
  name: "Technical SEO",
  description: "...",
  tags: ["Crawl audits", "Core Web Vitals", "Indexing"],
  status: "live",        // "live" | "development"
  url: "",               // ← paste the dashboard URL here
  icon: Gauge,           // any lucide-react icon
  from: "#27338c",       // icon gradient start
  to: "#49559f",         // icon gradient end
}
```

- Set **`url`** to the live dashboard link → the "Open dashboard" button
  opens it in a new tab.
- Set **`status`** to `"live"` to show the green Live badge; `"development"`
  shows the orange In-Development badge, and with an empty `url` the button
  locks to "Coming soon".
- The **hero counters** (Automations / Live / In development) are derived from
  this list automatically — no need to update them by hand.

## Project structure

```
src/
  App.tsx                 # page composition
  main.tsx                # entry + router (lazy routes, auth-guarded)
  index.css               # Tailwind + brand tokens
  vite-env.d.ts           # custom VITE_* env var typings
  context/AuthContext.tsx # session state + login/logout
  data/tools.ts           # ← edit tool links here
  hooks/useCountUp.ts
  lib/utils.ts            # cn() helper
  pages/LoginPage.tsx     # public sign-in page
  services/api/           # per-audit clients + same-origin auth service
  components/
    Header.tsx  Hero.tsx
    RequireAuth.tsx       # route guard (redirects guests to /login)
    HeroVisual.tsx        # alpha-keyed liquid-sphere video (right side of hero)
    ToolsSection.tsx  ToolCard.tsx
    Footer.tsx  Magnetic.tsx
    ui/                   # shadcn components (button, badge)
public/
  logo-white.svg  favicon.png
  liquid-sphere.webm      # VP9 + alpha (yellow plate keyed out offline with ffmpeg)
server/
  index.mjs               # Express: session auth API + serves dist/
  hash-password.mjs       # CLI to generate AUTH_PASSWORD_HASH values
Dockerfile                # multi-stage: node build -> node (Express) serve
docker-compose.yml        # local parity with the production container
railway.json              # Railway builder + deploy config (Dockerfile, /health)
```

Brand tokens (colors, radius, fonts) live in `tailwind.config.js` under
`theme.extend.colors.brand` and in `src/index.css` `:root`. All motion respects
`prefers-reduced-motion`.

## Deployment

Ships as a Docker image — a multi-stage build (Node → static `dist/`) served
by the Express server in `server/`. Copy `.env.example` to `.env.local` for
local dev; Vite env vars need the `VITE_` prefix to reach the client bundle.

### Railway

**Leave the Railway service's Root Directory empty (`/`).** This directory *is*
the git repository root — `git rev-parse --show-toplevel` resolves here, and
`Dockerfile` + `railway.json` sit at the top level of the repo
(`jainil-e2m/WIA-Command-Center`). Railway finds them with no root override and
builds with this directory as the context.

> Earlier revisions of this section told you to set Root Directory to
> `frontend`. That was written for a layout where the whole project folder was
> the repo. It is not: only this directory is tracked, so setting `frontend`
> makes Railway look for `frontend/Dockerfile` *inside* this repo, find
> nothing, fall back to Nixpacks and fail the build. If a deploy fails
> immediately with "no Dockerfile found", check this setting first.

The parent folder (`Wedding_Industry_Ads/`) holds the client dossiers, scope
documents and `.clickup-snapshot/` — none of it is tracked here, so none of it
reaches GitHub or the image.

Railway injects `PORT` at runtime; `server/index.mjs` listens on whatever value
that is. Optionally set `SESSION_SECRET` (and `AUTH_*` overrides — see
[Authentication](#authentication)) in the service's **Variables** tab.

**Audit BFF variables.** No audit service is called from browser code. Set these
server-only runtime variables on the Express/Railway service:

- `TECHNICAL_SEO_AUDIT_URL` — required public HTTPS Tech SEO API origin.
- `TECHNICAL_SEO_API_AUTH_TOKEN` — required private bearer token for that API.
- `AI_SEO_AUDIT_URL` — required public HTTPS AI SEO API origin.
- `AI_SEO_API_AUTH_TOKEN` — required private bearer token for that API.
- `AI_PRESENCE_AUDIT_URL` / `AI_PRESENCE_API_AUTH_TOKEN` — AI Presence Checker.
- `ON_PAGE_SEO_AUDIT_URL` / `ON_PAGE_SEO_API_AUTH_TOKEN` — On-Page SEO.

Two services serve the shared audit contract under a path prefix rather than at
their origin root, so the proxy prepends one:

- `AI_PRESENCE_AUDIT_BASE_PATH` — defaults to `/api/v1` (that service's own
  `API_PREFIX`).
- `ON_PAGE_SEO_AUDIT_BASE_PATH` — defaults to `/v1` (that service versions its
  whole HTTP surface).

Leave both unset unless the upstream deployment differs. An explicit empty value
is meaningful — it says the service serves the contract at its root — and is not
read as "unset".

Do not use a `VITE_` prefix for any of these. The browser sends its HttpOnly
dashboard session cookie only; Express adds the bearer token to upstream API and
SSE requests.

Each URL must be the service **origin** with no path and no trailing slash. The
proxy forwards the request's absolute path, and per the URL spec an absolute path
discards any path on the base URL — so a value like `https://host/api/v1` would
still resolve to `https://host/audits`.

**Build-time variables.** No audit URL is inlined into the bundle any more —
every audit product goes through the BFF. Build-time values include the
per-automation enable flags (`VITE_TOOL_<ID>_ENABLED`, see
`src/data/toolFlags.ts`). Railway passes those to the Docker build as build
args, so changing one needs a redeploy; the audit BFF values are runtime-only.

**Content Atelier destination.** Set `VITE_CONTENT_ATELIER_URL` on the Command
Center service to the deployed Content Atelier app URL, then redeploy. Every
Atelier entry (the landing's "View Here" button and Campaigns destination, and
the Ops Hub's sidebar, Home card and palette) opens
`/api/auth/content-atelier/launch`, a full-page navigation that signs the
current user into Atelier automatically; Command Center has no Atelier screen
of its own. Both repositories must be deployed with the
handoff endpoints. Keep this URL available at runtime as well as build time.
The server issues a 60-second authorization code for the configured Atelier
callback; Atelier redeems it with a server-held PKCE verifier. Session tokens
and passwords are never passed in a browser URL. Keep one replica per service
for this prototype's process-local, one-use code/transaction storage. A restart
during handoff requires reopening the link; session verification remains backed
by Command Center. Direct Atelier `/login` remains available as a fallback.

The handoff stays in the same tab and preserves the configured destination's
local path and query. For local use, set the URL in `.env.local`, then restart
both Vite and the API server. A blank or invalid URL leaves those entries
disabled (the palettes leave them out). The landing's Content Atelier card reads
"Live" wherever the URL is configured and "In development" otherwise; Client
Knowledge Base and Paid Media Reporting display "Coming soon".

### Local Docker parity

```bash
# First set TECHNICAL_SEO_* and AI_SEO_* URL/token pairs in the ignored .env file.
docker compose up --build   # http://localhost:8080
```

Or without compose:

```bash
docker build -t wahha-automation-hub .
docker run -p 8080:8080 -e PORT=8080 -e TECHNICAL_SEO_AUDIT_URL=https://your-technical-seo-audit -e TECHNICAL_SEO_API_AUTH_TOKEN=your-private-token wahha-automation-hub
```

Docker Compose reads the server-only Technical SEO and AI SEO values from `.env`.

`/health` returns `200 ok` — used by the Dockerfile `HEALTHCHECK` and wired as
the Railway deploy health check in `railway.json`.

## Independent audit integrations

`src/services/api/audits.ts` routes every audit product through the dashboard's
same-origin BFF. Starting an audit, reading status/history, downloading reports,
and opening progress SSE therefore share dashboard session authentication while
the upstream bearer token remains server-only. On-Page SEO exposes no progress
stream yet, so its runs rely on the status polling the History page already does
whenever a stream is unavailable.

## Preview access and data — read before sharing a link

Two statements that were in tension across this repository, resolved here.

**Access.** The Railway preview runs with `AUTH_DISABLED=1` and
`VITE_AUTH_DISABLED=1` — no login, every `/api/*` route open. Anywhere this or
the proposal describes the preview as "protected" or "internal", that is wrong
unless those variables have been removed. `DEPLOY.md § Demo mode` has the
switch-back procedure; from the S.C1 release a production start refuses `AUTH_DISABLED` and requires `SESSION_SECRET`
and `AUTH_PASSWORD_HASH` (`DEPLOY.md § Cutting over to real accounts`). Verify the live configuration at the moment of sharing;
env vars change without a commit.

**Data.** "Synthetic demo data" is true of the AI Operations Hub and not of
everything here. Three kinds of material are present:

| Origin | Where | Shareable |
|---|---|---|
| Invented | `src/data/opsHub.ts`, `src/data/rollCall.ts`, `src/data/rollCallMetaTranscript.ts` | Yes |
| Derived from real material | `src/data/rollCallTranscript.ts`, `src/data/internalMeetingTranscript.ts`, the Vault content in `PACKAGES` | Internal only — real names and real client analytics |
| Real client data | `server/onboarding-templates.json`, the onboarding sample client | Internal only — read from the live WIA ClickUp workspace on 7 Sep 2026, GET only |

The same table renders in-app on **Source Coverage**, so it stays visible to
whoever is running the walkthrough.

**Inherited routes.** `/leadmagnetdashboard`, `/automations/:toolId` and
`/history` come from the engagement this repo was forked from. They are hidden
from the WIA launcher but still routable, and their upstream services are
unconfigured here (`.env.example` leaves every `*_AUDIT_URL` blank), so they
return errors rather than data. They are outside the scope of the four WIA
review mockups and should be described that way if anyone finds them.

**Demo state.** The onboarding console's store is shared and no longer resets
on every page load — it seeds only when empty, and "Start over" is a button.
Two people can walk through it without wiping each other. It is still a demo
store, not operational persistence.
