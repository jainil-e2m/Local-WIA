# Content Atelier frontend

React/Vite Weekly Studio with backend angle/brief review, versioned five-piece
production packs and a PostgreSQL-backed shared calendar. Authentication uses the existing
Command Center accounts.

## Local development

Use Node 24 (the same version as the production Docker image).

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

## Real packs and calendar

See [calendar deployment](../backend/docs/Calendar-Deployment.md) for migration 004,
backend capabilities, exact production models and the editorial SQL worker.
Set ATELIER_BACKEND_ORIGIN and ATELIER_API_SECRET on this app's Node server.
Home, Content Packs and Weekly Studio Scheduled Content use backend records;
localStorage schedules and demo calendar postings are not imported. An unavailable
backend shows an error; no records produces an empty state. Saving a date does
not automatically post content to external channels.
