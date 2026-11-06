# Content Atelier frontend

`npm run build` builds the real, API-backed app, as does the Dockerfile with no arguments (7.F2, 6.F3). Only an
explicit `VITE_ATELIER_MODE=mock` builds the saved demo instead; the variable is read **at build time**, and the
production bundle carries none of the demo (its screens, its examples or its browser storage).

The demo build (`VITE_ATELIER_MODE=mock npm run build`, or
`docker build --build-arg VITE_ATELIER_MODE=mock .`) runs the supplied mock Weekly Studio. `src/mock/App.tsx` owns
that flow and its original navigation, approval, pack scheduling and calendar components; the sample screens are at
`/sample/<view>` in the same build (`src/mock/sampleViews.ts`). It uses the shared three-angle content in `src/data/`
and saves progress in this browser's localStorage. It calls none of the weekly storage, generation or calendar APIs,
and needs no backend configuration; Command Center sign-in is still required. Each new build starts its mock concepts
at angle approval (the build stamps its own id); reloads of that build retain progress. Localhost and the deployed
domain have separate browser storage, so approvals and schedules made on localhost will not appear on the deployment.

The backend configuration described below applies to the real app.

React/Vite Weekly Studio with backend angle/brief review, versioned five-piece
production packs and a PostgreSQL-backed shared calendar. Authentication uses the existing
Command Center accounts.

## Local development

Use Node 24 (the same version as the production Docker image), pinned in
`.nvmrc`. `package.json` `engines` requires at least Node 22.12: Vite 8 needs
20.19+ or 22.12+, and `npm start` uses `--env-file-if-exists` (22.9+).

```powershell
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Run the Command Center auth server on port 8787, or set
`COMMAND_CENTER_AUTH_ORIGIN` in `.env.local` to its origin. Local Vite requests to
`/api/auth/*` are proxied there. Sign into the local Command Center at
`http://localhost:5173/login`; both localhost ports share the host-only cookie.
The workspace appears once the session is verified. Calendar reads and schedule saves require no model key. Pack generation requires
explicit backend configuration; replay uses saved responses only.

## Verify and serve a production build

```powershell
npm --prefix server ci --omit=dev
npm run lint
npm test
npm run build
npm start
```

Command Center's **View Here** button uses an automatic sign-in handoff. Deploy
both apps; no extra key is needed when `COMMAND_CENTER_AUTH_ORIGIN` is public HTTPS.
For a private auth origin, also set `COMMAND_CENTER_PUBLIC_ORIGIN` to the public
HTTPS Command Center origin. Keep one replica per app for this prototype.

The Node server requires `COMMAND_CENTER_AUTH_ORIGIN`, serves `dist/`, provides
`/health`, and listens on `PORT` (default 8080). Its `/login` page uses the same
Command Center account while issuing the session cookie for this app's domain.
Use this server for deployment; `vite preview` is only a build preview.

See [Railway deployment instructions](../DEPLOYMENT.md) for service roots,
variables, the Command Center destination link and the optional Python backend.

## Browser end-to-end test (6.X1)

```powershell
npx playwright install chromium
npm run test:e2e
```

`npm run test:e2e` builds the real app (`VITE_ATELIER_MODE=backend`) into `dist/`, then drives a real Chromium through
the acceptance path: Home shows the cycle summary, the Weekly Studio shows a card, the card is developed at Gate 1, its
brief is approved at Gate 2, the content pack opens, and the week's documents download (Markdown as text, Word byte for
byte). The browser talks to the real Node server (`server/index.mjs`, started as it is deployed), which checks the session
and relays to a stubbed Command Center session endpoint and a stubbed backend (`tests/e2e/stubs.ts`): recorded answers in
the generated API shapes, from the same synthetic fixtures as the unit tests, and the writes accepted and remembered. Any
backend request the stub cannot answer, or any error on the page, fails the test. `ATELIER_E2E_SKIP_BUILD=1` reuses a
build already in `dist/` (the CI job builds in the step before). Traces of a failed run are in `test-results/e2e/`.

## Session checks (6.X5)

The Node server asks Command Center to check the session on every request it serves behind sign-in: the page, each
compiled asset, every `/api/atelier` call, and the app's own `/api/auth/session` (once a minute while the tab is visible,
and on focus). That is deliberate: a session revoked in either app stops working here at once (`AUTH.md`; Command
Center's `DEPLOY.md`, "One sign-in and one sign-out").

Measured on 25 October 2026 with `tests/e2e/session-checks.spec.ts` (the stubbed Command Center counts the checks; the
page's clock is the test's, so five idle minutes pass in seconds):

| What the person does | Session checks |
|---|---|
| Opens Home (a full page load) | 10: the page, its script, its style sheet and 2 images; the app's session check; 4 reads (flags, me, summary, schedule) |
| Leaves Home open and idle for five minutes | 11: 5 session checks, 5 summary reads, 1 schedule read |
| Opens the Weekly Studio from Home, inside the app | 8: its reads only (no page or asset again) |
| Leaves the Weekly Studio open and idle for five minutes | 36: 5 session checks; 31 reads (the week and the cycles every 30 seconds, the summary and the week's measures every minute, the schedule every five minutes) |

Decision: leave it, with no session cache. A check is a signature check and an in-memory revocation lookup in Command
Center (`server/auth-core.mjs` `resolveSessionUser`): no database, no outside call and no rate limit on
`/api/auth/session`. The busiest idle screen makes about 7 checks a minute, so ten open tabs make about one a second, and
each relayed request waits one round trip on Railway's private network before the backend call it guards, which takes far
longer. A cache of a few seconds would save little (the polls are 30 seconds apart or more) and would let a revoked session
keep working for that long. The test fails if a change multiplies the counts (more than 15 for a page load, 20 for Home idle,
12 for opening the Weekly Studio, 50 for the Weekly Studio idle), which is when to look at this again.

## Real packs and calendar

See [calendar deployment](../backend/docs/Calendar-Deployment.md) for migration 004,
backend capabilities, exact production models and the editorial SQL worker.
Set ATELIER_BACKEND_ORIGIN and ATELIER_API_SECRET on this app's Node server.
Home, Content Packs and Weekly Studio Scheduled Content use backend records;
localStorage schedules and demo calendar postings are not imported. An unavailable
backend shows an error; no records produces an empty state. Saving a date does
not automatically post content to external channels.
