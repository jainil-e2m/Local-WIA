# Shared Command Center session

Atelier uses the existing Command Center `/api/auth/session` and
`/api/auth/logout` endpoints. The authoritative user shape is the same as
`../../frontend/src/services/api/auth.ts`: `email`, `name`, and `role`
(`team` or `client`). No user identity, password, cookie token, or session
secret is copied into browser storage or query strings.

The account menu, sidebar profile, initials, and Home greeting use one shared
AuthProvider. It rechecks when the tab regains focus, becomes visible, and
once a minute while visible. An expired session clears the displayed identity;
network errors show a retry action instead of a fabricated demo user.

## Local development

1. In the workspace's `frontend` directory run `npm run dev:api` (default 8787).
   This reads the Command Center's existing server configuration.
2. Run its dashboard with `npm run dev` (default 5173) and sign in there.
3. Run Atelier with `npm run dev` (default 3000). Use `localhost` for both apps,
   not `localhost` for one and `127.0.0.1` for the other.

Vite proxies only `/api/auth/*` to the SAME Command Center server, preserving
the cookie. Configure `COMMAND_CENTER_AUTH_ORIGIN` if its API port changes;
`API_PORT` is also supported when the origin is omitted. Set
`VITE_COMMAND_CENTER_URL` to change the dashboard sign-in link. Clicking it
opens the existing dashboard login; return to Atelier after signing in.

Do not run a second independent auth server with a different SESSION_SECRET.
Do not enable AUTH_DISABLED or put a server-side secret in a VITE_ variable.
The frontend does not override any existing Command Center auth/demo flags.

## Production

The Node server in `server/` serves the built UI and provides `/login`. It
forwards login, session checks and logout to `COMMAND_CENTER_AUTH_ORIGIN`.
Command Center keeps the account configuration and signing secret; the
Atelier host receives its own signed `wahha_session` cookie with `HttpOnly`,
`SameSite=Lax`, `Path=/` and `Secure` in production.

Command Center's **View Here** launcher now signs into Atelier automatically
using a 60-second, one-use authorization code, browser state and a server-held
PKCE verifier. The callback is pinned to the configured Atelier origin. The
session token is transferred only on the server backchannel and retains its
original expiry. Deploy both apps to activate this flow.

Separate hosts still have separate cookies. Signing out of Atelier clears its
cookie; a Command Center tab retains its own session. No cookie domain is
broadened and no credentialed CORS is needed. Keep one replica per app for the
prototype's process-local code and state storage. If the auth origin is private,
set `COMMAND_CENTER_PUBLIC_ORIGIN` to its public HTTPS origin for browser redirects.

The server verifies the session before serving the SPA or its compiled mock
assets. `AuthGate` also hides the workspace when the session expires, sign-out
starts, or session verification fails. Live API operations retain their
separate server-side authorization boundary.

See [deployment instructions](../DEPLOYMENT.md) for Railway settings.
