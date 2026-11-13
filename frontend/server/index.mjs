/* ────────────────────────────────────────────────────────────────
   Wedding Industry Ads Command Center — auth + static server.

   Replaces the previous nginx runtime: one small Express process
   serves the built SPA, exposes the session-cookie auth API under
   /api/auth/*, and provides authenticated backend-for-frontend
   proxies for every audit API (see AUDIT_SERVICES). Pre-seeded team
   account plus an optional client account — no registration, no user
   management, no database.

   Config (all optional — sensible defaults keep local dev and a
   fresh Railway deploy working out of the box):
     PORT                Railway injects this; defaults to 8787 locally.
     AUTH_EMAIL          Login email for the seeded account.
     AUTH_PASSWORD_HASH  scrypt hash (see hash-password.mjs) — overrides
                         the committed default so the plaintext password
                         never needs to appear anywhere in the repo.
                         REQUIRED when NODE_ENV=production: a production
                         start never falls back to the committed hash.
     AUTH_DISABLED       Development switch only. A production start
                         (NODE_ENV=production) refuses to run with it set.
     AUTH_NAME           Display name shown in the header pill.
     CLIENT_EMAIL        Optional second (client) login. The client account
     CLIENT_PASSWORD_HASH  is enabled only when BOTH the email and the hash
     CLIENT_NAME           are set; otherwise the server stays single-account.
     USER_n_EMAIL        Any number of further logins, n = 1..20 (gaps are fine).
     USER_n_PASSWORD_HASH  Same rule: email + hash required, name optional.
     USER_n_NAME           Defaults to the email's local part.
     USER_n_ROLE           "team" or "client"; defaults to "client".
     SESSION_SECRET      HMAC key for session cookies. REQUIRED when
                         NODE_ENV=production (the server refuses to start
                         without it). Outside production, when unset, a
                         random per-boot key is used (sessions simply
                         reset on restart/redeploy).
     TECHNICAL_SEO_AUDIT_URL       Public Tech SEO API origin. Server-only.
     TECHNICAL_SEO_API_AUTH_TOKEN  Bearer token for that API. Server-only.
     AI_SEO_AUDIT_URL              Public AI SEO API origin. Server-only.
     AI_SEO_API_AUTH_TOKEN         Bearer token for that API. Server-only.
     AI_PRESENCE_AUDIT_URL         Public AI Presence API origin. Server-only.
     AI_PRESENCE_API_AUTH_TOKEN    Bearer token for that API. Server-only.
     AI_PRESENCE_AUDIT_BASE_PATH   Path prefix that service serves the audit
                                   contract under; defaults to /api/v1.
     ON_PAGE_SEO_AUDIT_URL         Public On-Page SEO API origin. Server-only.
     ON_PAGE_SEO_API_AUTH_TOKEN    Bearer token for that API. Server-only.
     ON_PAGE_SEO_AUDIT_BASE_PATH   Path prefix that service serves the audit
                                   contract under; defaults to /v1.
     LEAD_MAGNET_AUDIT_URL         Public Lead Magnet Technical SEO API
                                   origin. Server-only. A different Railway
                                   project from TECHNICAL_SEO_AUDIT_URL, not
                                   an alias for it.
     LEAD_MAGNET_API_AUTH_TOKEN    Bearer token for that API. Server-only.
                                   That deployment runs without auth today,
                                   but the proxy refuses to forward with an
                                   empty token, so set any non-empty value.
     LEADS_FILE                    Lead Magnet interim lead store (JSON on
                                   disk; point at a mounted volume in prod).
     LEADMAGNET_CAPTURE_ORIGINS    Comma-separated origins allowed to POST
                                   captured leads (the public funnel site).
     ZCAL_WEBHOOK_SECRET           Shared secret zcal signs its booking webhook
                                   with (HMAC-SHA256, hex, in the
                                   x-zcal-webhook-signature header). Generate it
                                   here and paste the same value into zcal's
                                   webhook integration. Unset => the endpoint
                                   answers 503 rather than trusting callers.

   Both *_AUDIT_URL values must be https for any real host. Plain http is
   accepted only for a loopback address and only when NODE_ENV is not
   "production" — see upstream-url.mjs, which owns that policy and its tests.
   ──────────────────────────────────────────────────────────────── */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import compression from "compression";
import {
  collectExtraUsers,
  resolveUsers,
  createSessionCodec,
  createDecoyHash,
  authenticateCredentials,
  resolveSessionUser,
  createSessionRevocations,
} from "./auth-core.mjs";
import { createBookmarksStore, BookmarksError } from "./bookmarks-store.mjs";
import { createLeadsStore, LeadsError } from "./leads-store.mjs";
import { createLeadsDbStore } from "./leads-db.mjs";
import { HANDLED_TYPES, parseZcalEvent, verifyZcalSignature } from "./zcal-webhook.mjs";
import { parseDubsadoAlert } from "./onboarding-alert-parser.mjs";
import { createOnboardingStore, OnboardingError, OFFERS } from "./onboarding-store.mjs";
import { buildDraft, summarizeDraft, ANCHORS as CALL_ANCHORS } from "./onboarding-plan.mjs";
import {
  buildStagePlans,
  rehydrateSlackStage,
  summarizeStage,
} from "./onboarding-stages.mjs";
import { createFaviconCache, fetchFavicon } from "./favicon-resolver.mjs";
import { describeUpstreamUrlRejection, isAllowedUpstreamUrl } from "./upstream-url.mjs";
import { atelierOrigin, createAtelierSsoRouter } from "./atelier-sso.mjs";
import { readBasePath } from "./base-path.mjs";
import { assertProductionAuth } from "./production-auth.mjs";
import {
  FULL_AUDIT_PRODUCTS,
  fullAuditSubmitBody,
  hasRunInFlight,
  isStaleRun,
  missingIdentityFields,
  isSuccessStatus,
  isTerminalStatus,
  normalizeAuditStatus,
  readReportUrl,
  readUpstreamStatus,
  seedUrlForLead,
} from "./leadmagnet-full-audit.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DIST_DIR = path.join(__dirname, "..", "dist");

/** Read an env var, treating empty strings (docker-compose passthrough) as unset. */
const env = (name) => {
  const v = process.env[name];
  return v && v.trim() !== "" ? v.trim() : undefined;
};

/* S.C1: a production start without real authentication does not start. This runs
   before any account, key or route is read, so a misconfigured deploy fails at
   once with every problem named (see production-auth.mjs). */
try {
  assertProductionAuth(process.env);
} catch (error) {
  console.error(`[auth] ${error.message}`);
  process.exit(1);
}

const PORT = Number(env("PORT") ?? 8787);

// Seeded accounts. The committed team hash is an scrypt HASH of the shared team
// password — the plaintext itself is never stored in the repo, and every value
// can be rotated at any time via Railway service variables. A second "client"
// account is enabled only when CLIENT_EMAIL and CLIENT_PASSWORD_HASH are both
// set, so an un-configured deployment stays single-account and unchanged. Any
// further accounts come from the numbered USER_n_* variables (see auth-core).
/* The committed default is the Wedding Industry Ads address. An earlier pass
   left the inherited `team@wahha.design` in place for a good reason — it is
   the credential pair a running deployment may already be signing in with,
   and changing it alone would lock that deployment out — but the consequence
   was that a client signed in to their own hub using another agency's email.

   Both are true at once here: the default is corrected, AND the inherited
   address is registered as a second team login carrying the same password
   hash, so nothing that works today stops working. The alias is added ONLY
   when AUTH_EMAIL is unset — a deployment that names its own account gets
   exactly that account and no inherited extra. Drop LEGACY_AUTH_EMAIL once
   Railway sets AUTH_EMAIL explicitly.

   AUTH_NAME is display only: the header pill and the "Good afternoon · …"
   greeting on the landing page. */
const AUTH_EMAIL = (env("AUTH_EMAIL") ?? "team@weddingindustryads.com").toLowerCase();
const AUTH_NAME = env("AUTH_NAME") ?? "Wedding Industry Ads";
const AUTH_PASSWORD_HASH =
  env("AUTH_PASSWORD_HASH") ??
  "scrypt$16384$8$1$yimGslRzc0A7GbOC34rEhg==$1TUld5YfSSf6HbZH0eQh6pLLm++AEUEIq6UZyhQ55XdS7gFfzMMp7JSSKeWhLk7R9sEETv93y3tR230blhfcOw==";
const LEGACY_AUTH_EMAIL = "team@wahha.design";
const legacyTeamAlias = env("AUTH_EMAIL")
  ? []
  : [
      {
        slot: "legacy",
        email: LEGACY_AUTH_EMAIL,
        name: AUTH_NAME,
        passwordHash: AUTH_PASSWORD_HASH,
        role: "team",
      },
    ];

// role is re-derived from this list on every request, so removing an account's
// env vars instantly invalidates its sessions on the next boot.
const { users: USERS, warnings: userWarnings } = resolveUsers({
  authEmail: AUTH_EMAIL,
  authName: AUTH_NAME,
  authPasswordHash: AUTH_PASSWORD_HASH,
  clientEmail: env("CLIENT_EMAIL"),
  clientName: env("CLIENT_NAME"),
  clientPasswordHash: env("CLIENT_PASSWORD_HASH"),
  // The inherited address first (see LEGACY_AUTH_EMAIL), then any number of
  // further logins from USER_1_*, USER_2_*, … — adding one of those is a
  // Railway variable change plus a redeploy, with no code edit.
  extraUsers: [...legacyTeamAlias, ...collectExtraUsers(env)],
});
for (const warning of userWarnings) console.warn(`[auth] ${warning}`);

/** Look a normalized (trimmed, lowercased) email up in the configured accounts. */
const findUser = (email) => USERS.find((u) => u.email === email);

const SESSION_SECRET = env("SESSION_SECRET") ?? crypto.randomBytes(32).toString("hex");
if (!env("SESSION_SECRET")) {
  console.warn(
    "[auth] SESSION_SECRET not set — using a random per-boot key " +
      "(existing sessions are invalidated on every restart).",
  );
}

const COOKIE_NAME = "wahha_session";
const SESSION_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

/* One entry per independently deployed audit service reached through the BFF.
   All hold the same contract (POST /audits, GET /audits, GET /audits/:id,
   GET /audits/:id/progress), so one proxy implementation serves them all.

   `url` must be the service ORIGIN with no path: the proxy forwards the
   request's absolute path, and per the URL spec an absolute path discards any
   path component on the base URL. A service that serves the contract under a
   prefix declares it as `basePath` instead — appending it to `url` would be
   silently dropped, and the proxy would 404 against the service root. */
const AUDIT_SERVICES = [
  {
    id: "technical-seo",
    mountPath: "/api/technical-seo",
    url: env("TECHNICAL_SEO_AUDIT_URL")?.replace(/\/+$/, ""),
    token: env("TECHNICAL_SEO_API_AUTH_TOKEN"),
    urlVariable: "TECHNICAL_SEO_AUDIT_URL",
    tokenVariable: "TECHNICAL_SEO_API_AUTH_TOKEN",
    errorCode: "technical_seo_not_configured",
    label: "Technical SEO",
  },
  {
    id: "ai-seo",
    mountPath: "/api/ai-seo",
    url: env("AI_SEO_AUDIT_URL")?.replace(/\/+$/, ""),
    token: env("AI_SEO_API_AUTH_TOKEN"),
    urlVariable: "AI_SEO_AUDIT_URL",
    tokenVariable: "AI_SEO_API_AUTH_TOKEN",
    // errorCode is a machine identifier, not copy: it is paired with the
    // AI_SEO_* variable names above and is not matched anywhere in src/.
    errorCode: "ai_seo_not_configured",
    label: "AI Crawlability Readiness Checker",
  },
  {
    id: "ai-presence",
    mountPath: "/api/ai-presence",
    url: env("AI_PRESENCE_AUDIT_URL")?.replace(/\/+$/, ""),
    token: env("AI_PRESENCE_API_AUTH_TOKEN"),
    /* Unlike the other two, that service mounts its routers under API_PREFIX,
       which defaults to /api/v1 — so its audit routes live at /api/v1/audits,
       not /audits. Set AI_PRESENCE_AUDIT_BASE_PATH to whatever API_PREFIX the
       deployment uses, or to an empty string when it serves them at the root. */
    basePath: readBasePath(process.env, "AI_PRESENCE_AUDIT_BASE_PATH", "/api/v1"),
    urlVariable: "AI_PRESENCE_AUDIT_URL",
    tokenVariable: "AI_PRESENCE_API_AUTH_TOKEN",
    errorCode: "ai_presence_not_configured",
    label: "AI Presence Checker",
  },
  {
    id: "on-page-seo",
    mountPath: "/api/on-page-seo",
    url: env("ON_PAGE_SEO_AUDIT_URL")?.replace(/\/+$/, ""),
    token: env("ON_PAGE_SEO_API_AUTH_TOKEN"),
    /* That service versions its whole HTTP surface, so the dashboard-shaped
       audit routes live at /v1/audits rather than /audits. Set
       ON_PAGE_SEO_AUDIT_BASE_PATH to whichever version prefix the deployment
       serves them under, or to an empty string when it serves them at the root. */
    basePath: readBasePath(process.env, "ON_PAGE_SEO_AUDIT_BASE_PATH", "/v1"),
    urlVariable: "ON_PAGE_SEO_AUDIT_URL",
    tokenVariable: "ON_PAGE_SEO_API_AUTH_TOKEN",
    errorCode: "on_page_seo_not_configured",
    label: "On-Page SEO",
  },
  {
    /* The Lead Magnet Technical SEO deployment — deliberately NOT the same
       service as `technical-seo` above.

       They are two Railway projects sharing one Git repository and nothing at
       runtime. The Lead project runs FULL_AUDIT_ENABLED=false, so it answers
       422 to the Full-shaped submission startAudit() sends; pointing
       TECHNICAL_SEO_AUDIT_URL at it would break the dashboard's existing
       Technical SEO tool rather than adding a new one.

       Lead submissions must carry audit_type: "lead_magnet" — see
       services/api/leadMagnetAudit.ts, which is separate from audits.ts for
       exactly that reason.

       No basePath: that deployment serves the audit contract at the root,
       unlike ai-presence and on-page-seo above. */
    id: "lead-magnet",
    mountPath: "/api/lead-magnet",
    url: env("LEAD_MAGNET_AUDIT_URL")?.replace(/\/+$/, ""),
    token: env("LEAD_MAGNET_API_AUTH_TOKEN"),
    urlVariable: "LEAD_MAGNET_AUDIT_URL",
    tokenVariable: "LEAD_MAGNET_API_AUTH_TOKEN",
    errorCode: "lead_magnet_not_configured",
    label: "Lead Magnet Technical SEO",
  },
];

/* Bookmarks live in a single JSON document. Point this at a mounted volume
   (e.g. /data/bookmarks.json) to survive redeploys; the default keeps the
   container's own filesystem, which Railway replaces on each deploy. */
const BOOKMARKS_FILE = env("BOOKMARKS_FILE") ?? path.join(__dirname, "..", ".data", "bookmarks.json");

/* Lead Magnet interim lead store — same storage contract as bookmarks. Stands
   in for the three per-service Lead Magnet backends until they exist; the
   funnel site POSTs captured leads here and /leadmagnetdashboard reads them. */
const LEADS_FILE = env("LEADS_FILE") ?? path.join(__dirname, "..", ".data", "leads.json");

/* Origins allowed to POST lead captures from a browser. The funnel site is a
   different origin (its own Railway service / localhost:3000 in dev), so the
   capture route is the ONE deliberately CORS-opened, session-exempt endpoint.
   Compared as exact origins (scheme://host[:port]), trailing slashes stripped. */
const LEADMAGNET_CAPTURE_ORIGINS = (env("LEADMAGNET_CAPTURE_ORIGINS") ?? "http://localhost:3000")
  .split(",")
  .map((origin) => origin.trim().replace(/\/+$/, ""))
  .filter(Boolean);

/* Upstream URL policy lives in upstream-url.mjs so it can be unit-tested without
   importing this file (which listens on a port at module scope). https is required
   for every real host; plain http is accepted only for a loopback address and only
   outside production. */

/* ── Session tokens: base64url(payload).hmac ──────────────────────
   The codec (auth-core.mjs) only proves token integrity; identity and role
   are resolved from USERS per request, so a legacy pre-role cookie still
   verifies and configuration always wins over the cookie's contents. */
const { createSessionToken, verifySessionToken } = createSessionCodec({
  secret: SESSION_SECRET,
  ttlMs: SESSION_TTL_MS,
});

// Sessions signed out before they expire (auth-core.mjs): one sign-out ends the
// session in Command Center and in the Content Atelier, which holds the same token.
const revocations = createSessionRevocations();

// Generated once per boot; equalizes login timing for unknown emails so
// account existence can't be probed via response latency.
const DECOY_PASSWORD_HASH = createDecoyHash();

/* ── Tiny in-memory login rate limit (per IP) ─────────────────── */

const WINDOW_MS = 15 * 60 * 1000;
const MAX_ATTEMPTS = 10;
const attempts = new Map(); // ip → { count, resetAt }

function rateLimited(ip) {
  const now = Date.now();
  const entry = attempts.get(ip);
  if (!entry || entry.resetAt < now) {
    attempts.set(ip, { count: 1, resetAt: now + WINDOW_MS });
    return false;
  }
  entry.count += 1;
  return entry.count > MAX_ATTEMPTS;
}

setInterval(() => {
  const now = Date.now();
  for (const [ip, entry] of attempts) if (entry.resetAt < now) attempts.delete(ip);
}, WINDOW_MS).unref();

/* ── App ──────────────────────────────────────────────────────── */

const app = express();
app.disable("x-powered-by");
// Railway terminates TLS in front of the container; trust its
// X-Forwarded-Proto so req.secure (→ Secure cookie flag) is accurate.
app.set("trust proxy", 1);
app.use(
  compression({
    filter(req, res) {
      // SSE must be flushed chunk-by-chunk. Disabling compression at request
      // selection time is more reliable than depending on a later no-transform
      // response header through Express/Railway proxy layers.
      if (req.headers.accept?.includes("text/event-stream")) return false;
      return compression.filter(req, res);
    },
  }),
);
// The Tech SEO API permits a 1 MiB JSON submission. Keep the BFF boundary
// aligned so an operator-supplied URL list is not rejected by the dashboard.
/* `verify` is used only to keep a copy of the bytes as received.
 *
 * The zcal booking webhook is signed over the raw body, and this parser runs
 * before every route — so by the time that route is reached the buffer is gone
 * and only the parsed object remains. Re-serialising that object would mean
 * verifying a signature against something the sender never sent. Cheap: the
 * buffer already exists, this keeps the reference rather than copying it. */
app.use(
  express.json({
    limit: "1mb",
    verify: (req, _res, buf) => {
      req.rawBody = buf;
    },
  }),
);

// Same security headers the previous nginx config sent.
app.use((_req, res, next) => {
  res.set({
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
  });
  next();
});

const readSessionCookie = (req) => {
  const header = req.headers.cookie ?? "";
  for (const part of header.split(";")) {
    const [name, ...rest] = part.trim().split("=");
    if (name === COOKIE_NAME) return decodeURIComponent(rest.join("="));
  }
  return undefined;
};

const sessionCookie = (req, token, maxAgeMs) =>
  [
    `${COOKIE_NAME}=${token}`,
    "Path=/",
    "HttpOnly",
    "SameSite=Lax",
    `Max-Age=${Math.floor(maxAgeMs / 1000)}`,
    ...(req.secure ? ["Secure"] : []),
  ].join("; ");

app.get("/health", (_req, res) => res.type("text/plain").send("ok\n"));

app.post("/api/auth/login", (req, res) => {
  if (rateLimited(req.ip)) {
    return res.status(429).json({ error: "Too many attempts. Try again in a few minutes." });
  }
  const { email, password } = req.body ?? {};

  /* DEV-ONLY: any well-formed email plus any non-empty password signs in. The
     only rejection left is an unusable address, so the field validation still
     demonstrates itself. Real credential checking resumes the moment
     AUTH_DISABLED is unset. */
  if (AUTH_DISABLED) {
    const demo = demoUserFor(email);
    if (!demo || typeof password !== "string" || !password.length) {
      return res.status(401).json({ error: "Enter any email address and any password." });
    }
    res.setHeader("Set-Cookie", sessionCookie(req, createSessionToken(demo), SESSION_TTL_MS));
    return res.json({ user: demo });
  }

  const user = authenticateCredentials(email, password, findUser, DECOY_PASSWORD_HASH);
  if (!user) {
    return res.status(401).json({ error: "Incorrect email or password." });
  }
  res.setHeader("Set-Cookie", sessionCookie(req, createSessionToken(user), SESSION_TTL_MS));
  res.json({ user: { email: user.email, name: user.name, role: user.role } });
});

/* Sign-out ends the session, not only this browser's cookie: the token is
   refused from now on wherever it is presented (revocations above). The
   Content Atelier's own sign-out reaches here over its backchannel with the
   same token, so either app's sign-out ends both. */
const endSession = (req, res) => {
  const token = readSessionCookie(req);
  const payload = token ? verifySessionToken(token) : null;
  if (payload) revocations.revoke(token, payload.exp);
  res.setHeader("Set-Cookie", sessionCookie(req, "", 0));
};

app.post("/api/auth/logout", (req, res) => {
  endSession(req, res);
  res.json({ ok: true });
});

/* One sign-out for Command Center and the Content Atelier (S.C1). A top-level
   navigation, because each app's cookie is host-only and only a response from
   that host can clear it: this clears Command Center's cookie, then passes the
   browser to the Atelier's /api/auth/signout, which clears its cookie and comes
   back to /login. `from=atelier` marks the second leg of an Atelier-started
   sign-out, so the round trip never loops. Redirects go only to the configured
   Atelier origin (atelierOrigin) or to this host. */
const ATELIER_ORIGIN = atelierOrigin(env("VITE_CONTENT_ATELIER_URL"));
app.get("/api/auth/signout", (req, res) => {
  endSession(req, res);
  res.set({ "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" });
  if (ATELIER_ORIGIN && req.query.from !== "atelier") {
    return res.redirect(302, `${ATELIER_ORIGIN}/api/auth/signout?from=command-center`);
  }
  res.redirect(302, "/login");
});

app.get("/api/auth/session", (req, res) => {
  /* Falls back to a synthesised user when auth is disabled, so a demo sign-in
     as an arbitrary address stays signed in instead of bouncing straight back
     to the login screen. */
  const user = resolveUserOrDemo(req);
  if (!user) return res.status(401).json({ error: "Not authenticated." });
  res.json({ user: { email: user.email, name: user.name, role: user.role } });
});

/* DEV-ONLY AUTH BYPASS. Set AUTH_DISABLED=1 in .env.local to work on protected
   routes without signing in. Off unless explicitly set to "1", and a production
   start (NODE_ENV=production) refuses to run with it set at all (S.C1), so it
   cannot ship enabled; it is reverted by deleting one line from a git-ignored
   file rather than by remembering to undo a code edit.

   Mirrored on the client by VITE_AUTH_DISABLED. Both are needed: the React
   route guard and this API gate are separate boundaries, and bypassing only
   the first leaves every fetch 401-ing. */
const AUTH_DISABLED = process.env.AUTH_DISABLED === "1";
if (AUTH_DISABLED) {
  console.warn(
    JSON.stringify({
      event: "auth_disabled",
      note: "DEV ONLY - every /api route is served without authentication, and /api/auth/login accepts ANY email and password",
    }),
  );
  /* In production this branch is unreachable: assertProductionAuth (above) has
     already refused to start. It stays a development-only path. */
}

/**
 * DEV-ONLY: synthesise a user record from any email address.
 *
 * The demo needs the login FORM to work, not just the guard to be open —
 * otherwise a walkthrough hits "Incorrect email or password" on a screen that
 * is part of the story. With AUTH_DISABLED set, any well-formed address signs
 * in and gets a real session cookie, so the header greets whoever was typed.
 *
 * `gisselle@weddingindustryads.com` becomes "Gisselle". Role is always `team`,
 * the more privileged of the two, because a demo should not silently hide
 * tiles behind a role gate.
 */
const demoUserFor = (email) => {
  const normalized = typeof email === "string" ? email.trim().toLowerCase() : "";
  if (!normalized.includes("@") || normalized.startsWith("@") || normalized.endsWith("@")) {
    return null;
  }
  const local = normalized.slice(0, normalized.indexOf("@"));
  const name = local
    .split(/[._+-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
  return { email: normalized, name: name || normalized, role: "team" };
};

/**
 * Resolve a session, falling back to a synthesised user when auth is disabled.
 *
 * resolveSessionUser insists the cookie's email exists in USERS, which is
 * correct — but it means a demo login as an arbitrary address would mint a
 * cookie that /api/auth/session then rejects, leaving the app rendering
 * signed-out immediately after a successful sign-in.
 */
const resolveUserOrDemo = (req) => {
  const real = resolveSessionUser(readSessionCookie(req), verifySessionToken, findUser, revocations.isRevoked);
  if (real || !AUTH_DISABLED) return real;
  if (revocations.isRevoked(readSessionCookie(req))) return null;
  const payload = verifySessionToken(readSessionCookie(req));
  return payload?.email ? demoUserFor(payload.email) : null;
};

app.use("/api/auth/content-atelier", createAtelierSsoRouter({
  atelierUrl: env("VITE_CONTENT_ATELIER_URL"),
  resolveUser: resolveUserOrDemo,
  readToken: readSessionCookie,
  sessionExpiry: token => (revocations.isRevoked(token) ? undefined : verifySessionToken(token)?.exp),
}));

/* The Client Knowledge Base signs in the same way: its "View Here" opens /api/auth/knowledge-base/launch, and the
   KB's own server completes the hand-off (knowledge_base/wia-knowledge-base/backend/routes/auth.py). Its sign-out
   comes back through /api/auth/signout?from=knowledge-base, which goes on through the Atelier like ours. */
app.use("/api/auth/knowledge-base", createAtelierSsoRouter({
  atelierUrl: env("VITE_KNOWLEDGE_BASE_URL"),
  appName: "Knowledge Base",
  urlSetting: "VITE_KNOWLEDGE_BASE_URL",
  resolveUser: resolveUserOrDemo,
  readToken: readSessionCookie,
  sessionExpiry: token => (revocations.isRevoked(token) ? undefined : verifySessionToken(token)?.exp),
}));

function requireSession(req, res, next) {
  if (AUTH_DISABLED) {
    /* Prefer whoever actually signed in, so the header and any per-user copy
       reflect the demo login rather than a placeholder. */
    const user = resolveUserOrDemo(req);
    req.session = user
      ? { email: user.email, role: user.role }
      : { email: "dev@localhost", role: "team" };
    return next();
  }
  const user = resolveSessionUser(readSessionCookie(req), verifySessionToken, findUser, revocations.isRevoked);
  if (!user) return res.status(401).json({ error: "Not authenticated." });
  req.session = { email: user.email, role: user.role };
  return next();
}

/* Role gate. Compose AFTER requireSession, which is what populates req.session:
   `requireSession, requireRole("team")`. On its own this returns 403 for
   everyone, since req.session is undefined without it.

   Currently unused, and kept deliberately: the lead-magnet console was gated to
   `team` and is now open to every signed-in account, so the only remaining
   boundary on those routes is requireSession. Anything that later needs to be
   narrower than "any signed-in user" composes this rather than reinventing it.

   The role is re-derived from USERS on every request rather than trusted from the
   cookie, so removing an account from config revokes it immediately; this gate
   inherits that property. 403 not 404: the caller is authenticated, and hiding
   the route's existence from a signed-in colleague buys nothing. */
const requireRole =
  (...allowed) =>
  (req, res, next) => {
    if (!allowed.includes(req.session?.role)) {
      return res.status(403).json({ error: "forbidden", message: "Not permitted for this account." });
    }
    return next();
  };

/* ── Bookmarks ────────────────────────────────────────────────────
   One shared set for the whole dashboard, stored as JSON on disk. All
   routes require a session: bookmarks are private to signed-in users. */

const bookmarks = createBookmarksStore(BOOKMARKS_FILE);

/** Map a BookmarksError to its status; anything else is a real 500. */
const sendBookmarksError = (res, error, next) => {
  if (error instanceof BookmarksError) {
    return res.status(error.status).json({ error: error.code, message: error.message });
  }
  return next(error);
};

app.get("/api/bookmarks", requireSession, (_req, res) => res.json(bookmarks.read()));

/* Favicons are resolved here rather than in the browser: the /favicon.ico
   convention is often stale (app.clickup.com serves a legacy icon there while
   declaring the real mark via <link rel="icon">), a page's HTML can't be read
   cross-origin from the browser, and an <img> reports success even for a 404
   whose body happens to decode. Resolving server-side also means no favicon
   service ever learns which sites are bookmarked. */
const faviconCache = createFaviconCache(path.join(path.dirname(BOOKMARKS_FILE), "icons"));
const faviconInFlight = new Map();

app.get("/api/bookmarks/icon", requireSession, async (req, res) => {
  const target = typeof req.query.url === "string" ? req.query.url : "";
  if (!target) return res.status(400).json({ error: "missing_url" });

  const send = ({ contentType, buffer }) => {
    res.setHeader("Content-Type", contentType);
    // Immutable-ish: the resolver re-checks on its own TTL, and a wrong icon
    // shouldn't be pinned in the browser for long.
    res.setHeader("Cache-Control", "public, max-age=86400");
    return res.end(buffer);
  };

  const cached = faviconCache.read(target);
  if (cached) return send(cached);

  try {
    // Collapse concurrent requests for the same URL into one outbound fetch.
    let pending = faviconInFlight.get(target);
    if (!pending) {
      pending = fetchFavicon(target).finally(() => faviconInFlight.delete(target));
      faviconInFlight.set(target, pending);
    }
    const icon = await pending;
    if (!icon) return res.status(404).json({ error: "no_icon" });
    await faviconCache.write(target, icon);
    return send(icon);
  } catch (error) {
    // Blocked hosts / bad URLs are expected input, not server faults.
    return res.status(400).json({ error: error instanceof Error ? error.message : "failed" });
  }
});

app.post("/api/bookmarks", requireSession, async (req, res, next) => {
  try {
    const { url, name, groupId } = req.body ?? {};
    const bookmark = await bookmarks.addBookmark({ url, name, groupId });
    res.status(201).json({ bookmark, ...bookmarks.read() });
  } catch (error) {
    sendBookmarksError(res, error, next);
  }
});

app.patch("/api/bookmarks/:id", requireSession, async (req, res, next) => {
  try {
    const { url, name, groupId } = req.body ?? {};
    const patch = {};
    if (url !== undefined) patch.url = url;
    if (name !== undefined) patch.name = name;
    if (groupId !== undefined) patch.groupId = groupId;
    const bookmark = await bookmarks.updateBookmark(req.params.id, patch);
    res.json({ bookmark, ...bookmarks.read() });
  } catch (error) {
    sendBookmarksError(res, error, next);
  }
});

app.delete("/api/bookmarks/:id", requireSession, async (req, res, next) => {
  try {
    await bookmarks.removeBookmark(req.params.id);
    res.json(bookmarks.read());
  } catch (error) {
    sendBookmarksError(res, error, next);
  }
});

app.post("/api/bookmarks/groups", requireSession, async (req, res, next) => {
  try {
    const group = await bookmarks.addGroup({ name: req.body?.name });
    res.status(201).json({ group, ...bookmarks.read() });
  } catch (error) {
    sendBookmarksError(res, error, next);
  }
});

app.patch("/api/bookmarks/groups/:id", requireSession, async (req, res, next) => {
  try {
    const group = await bookmarks.updateGroup(req.params.id, { name: req.body?.name });
    res.json({ group, ...bookmarks.read() });
  } catch (error) {
    sendBookmarksError(res, error, next);
  }
});

app.delete("/api/bookmarks/groups/:id", requireSession, async (req, res, next) => {
  try {
    await bookmarks.removeGroup(req.params.id);
    res.json(bookmarks.read());
  } catch (error) {
    sendBookmarksError(res, error, next);
  }
});

/* ── Lead Magnet interim lead store ───────────────────────────────
   Captured leads from the public funnel pages. POST is the capture
   endpoint: session-EXEMPT (prospects are never logged in) but origin-
   checked, rate-limited and honeypot-guarded. Everything the dashboard
   uses (list / patch / delete) requires a session like every other API. */

/* Postgres when LEADS_DATABASE_URL is set, the JSON file otherwise.
   Not a hard switch: local development runs without Postgres, and a deploy that
   forgets the variable degrades to the file rather than failing to boot. The
   chosen backend is reported by /api/health so a misconfigured deploy is visible
   rather than silently writing to a container filesystem that vanishes. */
const LEADS_DATABASE_URL = (env("LEADS_DATABASE_URL") ?? "").trim();
const leads = LEADS_DATABASE_URL
  ? createLeadsDbStore(LEADS_DATABASE_URL)
  : createLeadsStore(LEADS_FILE);
if (!LEADS_DATABASE_URL) {
  console.warn(
    "[leadmagnet] LEADS_DATABASE_URL not set - using the JSON file store at " +
      LEADS_FILE +
      ". On Railway this lives in the container filesystem and is REPLACED on every deploy.",
  );
}

/** Map a LeadsError to its status; anything else is a real 500. */
const sendLeadsError = (res, error, next) => {
  if (error instanceof LeadsError) {
    return res.status(error.status).json({ error: error.code, message: error.message });
  }
  return next(error);
};

/* Capture rate limit — separate bucket from login so a burst of funnel
   submissions can never lock the team out (and vice versa). */
const CAPTURE_WINDOW_MS = 10 * 60 * 1000;
const CAPTURE_MAX_PER_WINDOW = 30;
const captureAttempts = new Map(); // ip → { count, resetAt }

function captureRateLimited(ip) {
  const now = Date.now();
  const entry = captureAttempts.get(ip);
  if (!entry || entry.resetAt < now) {
    captureAttempts.set(ip, { count: 1, resetAt: now + CAPTURE_WINDOW_MS });
    return false;
  }
  entry.count += 1;
  return entry.count > CAPTURE_MAX_PER_WINDOW;
}

setInterval(() => {
  const now = Date.now();
  for (const [ip, entry] of captureAttempts) if (entry.resetAt < now) captureAttempts.delete(ip);
}, CAPTURE_WINDOW_MS).unref();

/**
 * Apply CORS for the capture route. Returns false when a browser-sent Origin
 * is neither this host nor an allow-listed funnel origin. Requests without an
 * Origin header (curl, server-to-server) pass through: CORS is a browser
 * protection, not an authentication mechanism — the write is still bounded by
 * validation, the rate limit and the store cap.
 */
function leadCaptureCors(req, res) {
  const origin = req.headers.origin;
  if (!origin) return true;
  let sameOrigin = false;
  try {
    sameOrigin = new URL(origin).host === req.headers.host;
  } catch {
    return false; // malformed Origin header
  }
  if (!sameOrigin && !LEADMAGNET_CAPTURE_ORIGINS.includes(origin)) return false;
  res.setHeader("Access-Control-Allow-Origin", origin);
  res.setHeader("Vary", "Origin");
  return true;
}

app.options("/api/leadmagnet/leads", (req, res) => {
  if (!leadCaptureCors(req, res)) return res.status(403).end();
  res.setHeader("Access-Control-Allow-Methods", "POST");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Max-Age", "86400");
  return res.status(204).end();
});

app.post("/api/leadmagnet/leads", async (req, res, next) => {
  if (!leadCaptureCors(req, res)) {
    return res.status(403).json({ error: "origin_not_allowed" });
  }
  if (captureRateLimited(req.ip)) {
    return res.status(429).json({ error: "rate_limited", message: "Too many submissions." });
  }
  const body = req.body ?? {};
  // Honeypot: humans never see the `hp` field, so a filled value is a bot.
  // Answer 204 as if stored, so the bot learns nothing.
  if (typeof body.hp === "string" && body.hp.trim() !== "") return res.status(204).end();
  try {
    const lead = await leads.createLead({
      name: body.name,
      email: body.email,
      phone: body.phone,
      domainUrl: body.domainUrl,
      type: body.type,
      details: body.details,
      // Correlation key the funnel also sends to the audit intake. Accepted here
      // (unlike `notes`) because it carries no authority: it only lets a later
      // audit summary find this row. The store length-caps it, and the column is
      // UNIQUE so a replayed capture cannot fan one summary across several leads.
      captureId: body.captureId,
    });
    // Only the created record — this endpoint is public, and echoing
    // leads.read() here would hand the whole pipeline to any caller.
    return res.status(201).json({ lead });
  } catch (error) {
    return sendLeadsError(res, error, next);
  }
});

app.get("/api/leadmagnet/leads", requireSession, async (_req, res, next) => {
  try {
    res.json(await leads.read());
  } catch (error) {
    next(error);
  }
});

app.patch("/api/leadmagnet/leads/:id", requireSession, async (req, res, next) => {
  try {
    const { name, email, phone, domainUrl, details, notes } = req.body ?? {};
    const patch = {};
    if (name !== undefined) patch.name = name;
    if (email !== undefined) patch.email = email;
    if (phone !== undefined) patch.phone = phone;
    if (domainUrl !== undefined) patch.domainUrl = domainUrl;
    if (details !== undefined) patch.details = details;
    if (notes !== undefined) patch.notes = notes;
    const lead = await leads.updateLead(req.params.id, patch);
    res.json({ lead });
  } catch (error) {
    sendLeadsError(res, error, next);
  }
});

app.delete("/api/leadmagnet/leads/:id", requireSession, async (req, res, next) => {
  try {
    await leads.removeLead(req.params.id);
    res.json(await leads.read());
  } catch (error) {
    sendLeadsError(res, error, next);
  }
});

/* ── Full audit for one lead ───────────────────────────────────
   The console's "Run full audit" button. Starts the lead's OWN product's deep
   audit — Technical SEO leads go to the Technical SEO service, On-Page leads to
   On-Page — rather than the ~50s Lead Magnet snapshot every lead used to get.

   Two routes, and the GET is the interesting one. It is an idempotent TICK: one
   pass that reads upstream status and, if the run has ended, records it on the
   lead. Because the terminal write lives inside a GET that anyone may call, ANY
   caller finishes a run — the operator watching the modal, a page reload an hour
   later, or a different operator entirely. Closing the tab costs update latency
   and never the result, which matters because these runs are budgeted in hours
   (Technical SEO's RQ job_timeout is 86400s), not the seconds the old snapshot
   took. Run state lives in the lead row, so it also survives a redeploy of this
   service — which a server-side timer holding it in memory would not. */

/** The lead's product, resolved to a configured audit service. */
/* One reporter for every unrecognised status word, wherever it arrives from.
   Silence is what let `complete` (AI SEO's native word for `completed`) sit
   unmapped for weeks while every AI SEO full audit quietly refused to start. */
const warnAuditStatus = (message) => console.warn(`[full-audit] ${message}`);

function resolveFullAuditTarget(lead) {
  const product = FULL_AUDIT_PRODUCTS[lead?.type];
  if (!product) return { error: "unsupported_product" };
  const service = AUDIT_SERVICES.find((entry) => entry.id === product.serviceId);
  if (!service) return { error: "unsupported_product" };
  return { product, service };
}

/**
 * Call one audit service, adding its bearer token.
 *
 * Separate from createAuditProxy because that streams a browser request through
 * verbatim; this makes a request the browser never made, with a body this server
 * composed. Same token discipline, different direction.
 */
async function callAuditService(service, path, { method = "GET", body } = {}) {
  const url = new URL(`${service.basePath ?? ""}${path}`, `${service.url}/`);
  const response = await fetch(url, {
    method,
    headers: {
      authorization: `Bearer ${service.token}`,
      ...(body ? { "content-type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
    signal: AbortSignal.timeout(FULL_AUDIT_UPSTREAM_TIMEOUT_MS),
  });
  // Not every error body is JSON (a proxy 502 is usually HTML), so parsing is
  // best-effort and the status code stays the source of truth.
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  return { ok: response.ok, status: response.status, payload };
}

/* On-Page's submit is deliberately unbounded upstream — it probes candidate
   origins to decide which host the run pins to before answering — so this is
   sized for that walk rather than for a normal API call. */
const FULL_AUDIT_UPSTREAM_TIMEOUT_MS = 60_000;

app.post(
  "/api/leadmagnet/leads/:id/full-audit",
  requireSession,
  async (req, res, next) => {
    try {
      const lead = await leads.getLead(req.params.id);
      if (!lead) return res.status(404).json({ error: "not_found", message: "Lead not found." });

      const { product, service, error } = resolveFullAuditTarget(lead);
      if (error) {
        return res.status(422).json({
          error,
          message: "Full audits are not available for this lead's funnel yet.",
        });
      }
      if (!isAllowedUpstreamUrl(service.url) || !service.token) {
        return auditConfigurationError(res, service);
      }

      // Refuse before spending an upstream job slot rather than after. The old
      // path faked a run for a lead with no site and reported it as completed.
      const seedUrl = seedUrlForLead(lead);
      if (!seedUrl) {
        return res.status(422).json({
          error: "lead_has_no_domain",
          message: "This lead has no usable website URL to audit.",
        });
      }

      // A run already going is ATTACHED to, not duplicated. Returning its id lets
      // the caller start watching the existing run, which is what a second click
      // or a second operator actually wants.
      if (hasRunInFlight(lead)) {
        return res.status(200).json({
          auditId: lead.auditId,
          auditStatus: lead.auditStatus,
          toolId: product.toolId,
          attached: true,
        });
      }

      /* Identity the console collected from the operator. Only AI SEO declares
         any; for the other two `requiredIdentity` is empty and a body is neither
         expected nor read.

         Refused rather than defaulted. The upstream would reject a blank
         country/state anyway, but the reason not to fill them in here is
         stronger than that: the AI SEO backend measured that a plausible wrong
         identity resolves to the WRONG COMPANY in its Knowledge Graph lookup,
         which is worse than not running at all. So the missing names are
         returned and the console asks for them. */
      const identity = req.body && typeof req.body === "object" ? req.body : {};
      const missing = missingIdentityFields(product, identity);
      if (missing.length > 0) {
        return res.status(422).json({
          error: "identity_required",
          missing,
          message: `${product.label} needs ${missing.join(" and ")} before a full audit can start.`,
        });
      }

      const submit = await callAuditService(service, product.submitPath, {
        method: "POST",
        body: fullAuditSubmitBody(lead, seedUrl, product, identity),
      });
      if (!submit.ok) {
        return res.status(submit.status === 429 ? 429 : 502).json({
          error: "upstream_rejected",
          message:
            submit.payload?.detail ??
            submit.payload?.message ??
            `${product.label} could not start this audit (HTTP ${submit.status}).`,
        });
      }

      const auditId = submit.payload?.audit_id;
      if (typeof auditId !== "string" || !auditId.trim()) {
        return res.status(502).json({
          error: "upstream_rejected",
          message: `${product.label} accepted the audit but returned no id.`,
        });
      }

      // Recorded in the SAME request that started it. Any later failure leaves a
      // lead pointing at a real run rather than an orphan nothing references.
      const updated = await leads.setAuditRun(lead.id, {
        auditId: auditId.trim(),
        auditStatus: readUpstreamStatus(submit.payload, warnAuditStatus),
        auditError: "",
        fullAuditCompleted: false,
        // Stamped in the SAME write as the id, so the pair is never half-true.
        // This is what marks the id as OURS rather than the funnel's, and it is
        // the only place it is ever set.
        fullAuditStartedAt: new Date().toISOString(),
      });

      res.status(202).json({
        auditId: auditId.trim(),
        auditStatus: readUpstreamStatus(submit.payload, warnAuditStatus),
        toolId: product.toolId,
        attached: false,
        lead: updated,
      });
    } catch (error) {
      sendLeadsError(res, error, next);
    }
  },
);

app.get(
  "/api/leadmagnet/leads/:id/full-audit",
  requireSession,
  async (req, res, next) => {
    try {
      const lead = await leads.getLead(req.params.id);
      if (!lead) return res.status(404).json({ error: "not_found", message: "Lead not found." });
      if (!lead.auditId) return res.json({ state: "idle" });
      /* An audit id with no start stamp belongs to the funnel's own quick audit,
         which runs on a different deployment this dashboard has no address for.
         Asking OUR service about it can only ever 404, so there is nothing to
         report and nothing to poll — this run does not exist here. */
      if (!lead.fullAuditStartedAt) return res.json({ state: "idle" });

      const { product, service, error } = resolveFullAuditTarget(lead);
      if (error) return res.json({ state: "idle" });
      if (!isAllowedUpstreamUrl(service.url) || !service.token) {
        return auditConfigurationError(res, service);
      }

      const status = await callAuditService(service, product.statusPath(lead.auditId));
      if (!status.ok) {
        /* A 404 is not an outage, it is an answer: this service has no such run.
           Retrying it forever is what kept stranded leads spinning — the console
           polls every few seconds and `unknown` writes nothing, so nothing could
           ever end the loop. Recording it as interrupted ends the run honestly
           and lets the row offer a fresh start. Every other status really is
           "ask again later". */
        if (status.status === 404) {
          const updated = await leads.setAuditRun(lead.id, {
            auditStatus: "interrupted",
            auditError: `${product.label} has no record of run ${lead.auditId}.`,
            completedAt: new Date().toISOString(),
            fullAuditCompleted: false,
          });
          return res.json({
            state: "failed",
            auditId: lead.auditId,
            toolId: product.toolId,
            auditStatus: "interrupted",
            message: updated.auditError ?? "",
            lead: updated,
          });
        }
        // Upstream being briefly unreachable is not the run failing. Report it
        // and write nothing, so the next tick can still resolve the run.
        return res.status(200).json({
          state: "unknown",
          auditId: lead.auditId,
          toolId: product.toolId,
          message: `${product.label} did not answer (HTTP ${status.status}).`,
        });
      }

      const upstreamStatus = readUpstreamStatus(status.payload, warnAuditStatus);
      const finished = isTerminalStatus(upstreamStatus);
      const stalled = !finished && isStaleRun(status.payload);

      if (!finished && !stalled) {
        return res.json({
          state: "running",
          auditId: lead.auditId,
          toolId: product.toolId,
          auditStatus: upstreamStatus,
          percent: Number(status.payload?.progress_percent) || 0,
          stage: status.payload?.progress_stage ?? "",
        });
      }

      const resolvedStatus = stalled ? "interrupted" : upstreamStatus;
      const succeeded = !stalled && isSuccessStatus(resolvedStatus);
      const updated = await leads.setAuditRun(lead.id, {
        auditStatus: resolvedStatus,
        auditError: stalled
          ? "The run did not report back within 24 hours."
          : (status.payload?.failure_reason ?? ""),
        completedAt: status.payload?.finished_at ?? new Date().toISOString(),
        // Captured here because this is the only moment the console sees the
        // status payload; the lead row itself has no other route to it.
        reportUrl: succeeded ? readReportUrl(status.payload) : "",
        // Only a run that produced something counts as a completed full audit.
        // `completed_partial` does count: On-Page reports partial on nearly every
        // run, and treating that as failure would mark almost all of them broken.
        fullAuditCompleted: succeeded,
      });

      res.json({
        state: succeeded ? "completed" : "failed",
        auditId: lead.auditId,
        toolId: product.toolId,
        auditStatus: resolvedStatus,
        message: succeeded ? "" : (updated.auditError ?? ""),
        lead: updated,
      });
    } catch (error) {
      sendLeadsError(res, error, next);
    }
  },
);

/* ── Audit-summary intake (service-to-service) ─────────────────
   An audit backend calls this when a run reaches a terminal state, with a
   CONDENSED summary (~500 bytes, not the ~2 MB report). The dashboard keeps its
   own copy so the Lead Magnet console never queries the audit projects.

   Deliberately NOT the public POST /api/leadmagnet/leads route:
     - that route is CORS-locked to browser origins and a server-to-server call
       sends no Origin header, so it would bypass the check rather than pass it;
     - it shares a per-IP rate-limit bucket sized for humans filling a form;
     - it creates leads. This only ever UPDATES one, and must never be able to
       write `notes`.

   Auth is a shared bearer token, distinct from the session cookie (no browser is
   involved) and from each backend's own API token (which guards traffic in the
   other direction). Unset => 503, so a half-configured deploy is visible rather
   than silently accepting unauthenticated writes. */
const LEADMAGNET_SYNC_TOKEN = (env("LEADMAGNET_SYNC_TOKEN") ?? "").trim();

app.post("/api/leadmagnet/audit-summary", express.json({ limit: "16kb" }), async (req, res, next) => {
  if (!LEADMAGNET_SYNC_TOKEN) {
    return res.status(503).json({ error: "sync_not_configured" });
  }
  const provided = (req.get("authorization") ?? "").replace(/^Bearer\s+/i, "").trim();
  // timingSafeEqual needs equal lengths, so compare digests rather than raw bytes.
  const expected = crypto.createHash("sha256").update(LEADMAGNET_SYNC_TOKEN).digest();
  const actual = crypto.createHash("sha256").update(provided).digest();
  if (!provided || !crypto.timingSafeEqual(expected, actual)) {
    return res.status(401).json({ error: "unauthorized" });
  }

  try {
    /* Normalized at the boundary, exactly like the status route does.
       This is the line whose absence caused the whole failure: the store wrote
       `summary.status` verbatim, so AI SEO's native `complete` was stored as-is,
       never matched the terminal set, and left every funnel-captured lead
       looking like a full audit that had been running since the day it arrived.

       Absence is preserved rather than defaulted — an unset status must leave
       the stored one alone, so this never substitutes "queued" the way the
       status route legitimately does. */
    const summary = req.body ?? {};
    const normalized = normalizeAuditStatus(
      typeof summary.dashboard_status === "string" && summary.dashboard_status.trim()
        ? summary.dashboard_status
        : summary.status,
      warnAuditStatus,
    );
    const lead = await leads.applyAuditSummary(
      normalized ? { ...summary, status: normalized } : summary,
    );
    if (!lead) {
      // No matching lead. Not an error: an audit can be started outside the
      // funnel (direct API call, console re-run), and the pusher must not retry
      // forever against a lead that will never exist.
      return res.status(202).json({ matched: false });
    }
    res.json({ matched: true, lead });
  } catch (error) {
    sendLeadsError(res, error, next);
  }
});

/* ── zcal booking webhook ──────────────────────────────────────
   zcal POSTs here when a prospect books, moves or cancels a call on the invite
   the Lead Magnet funnels embed, and the booking is stored on the lead that made
   it. This is the only channel: zcal sends nothing to the page when a booking
   completes, so without this endpoint a booked call exists solely in the host's
   calendar.

   Public by necessity — zcal calls it from its own servers — so authenticity
   rests entirely on the HMAC signature, not on the network. The signature covers
   the bytes as sent, which is why the global JSON parser above keeps them on
   req.rawBody: verifying a re-encoded body would mean checking something the
   sender never signed.

   ZCAL_WEBHOOK_SECRET unset => 503, matching LEADMAGNET_SYNC_TOKEN above: a
   half-configured deploy should be loud rather than quietly accepting
   unauthenticated writes. */
const ZCAL_WEBHOOK_SECRET = (env("ZCAL_WEBHOOK_SECRET") ?? "").trim();

app.post("/api/leadmagnet/zcal-webhook", async (req, res, next) => {
  {
    if (!ZCAL_WEBHOOK_SECRET) {
      return res.status(503).json({ error: "zcal_webhook_not_configured" });
    }
    if (captureRateLimited(req.ip)) {
      return res.status(429).json({ error: "rate_limited" });
    }

    const raw = Buffer.isBuffer(req.rawBody) ? req.rawBody : Buffer.from("");

    /* Anything that is not a storable booking is answered 200 and dropped,
       WITHOUT consulting the signature — because zcal makes the operator click
       "Test Endpoint" before it will save the webhook, and that probe must
       succeed for the integration to exist at all. Nothing is written on this
       path, so answering a probe politely grants no authority. */
    let event = null;
    try {
      event = parseZcalEvent(req.body);
    } catch {
      return res.status(200).json({ received: true, stored: false, reason: "not_an_event" });
    }

    // A real event, so now the signature has to hold.
    let signatureOk = false;
    try {
      signatureOk = verifyZcalSignature(raw, req.get("x-zcal-webhook-signature"), ZCAL_WEBHOOK_SECRET);
    } catch (error) {
      return next(error);
    }
    if (!signatureOk) {
      console.warn("[leadmagnet] zcal webhook rejected: bad signature");
      return res.status(401).json({ error: "invalid_signature" });
    }

    if (!HANDLED_TYPES.has(event.type)) {
      return res.status(202).json({ received: true, stored: false, reason: "unhandled_type" });
    }

    try {
      const lead = await leads.applyMeeting(event);
      if (!lead) {
        /* No lead matches. Accepted rather than errored: a booking can come from
           a link shared by hand, or under details resembling no lead we hold, and
           zcal must not retry forever against a lead that will never exist. */
        console.info(
          `[leadmagnet] zcal ${event.type} ${event.eventId} matched no lead ` +
            `(${event.bookedEmail ?? "no email"})`,
        );
        return res.status(202).json({ received: true, matched: false });
      }
      return res.json({ received: true, matched: true, leadId: lead.id });
    } catch (error) {
      return sendLeadsError(res, error, next);
    }
  }
});

/* ── Audit backend-for-frontend proxies ───────────────────────── */

function auditConfigurationError(res, service) {
  return res.status(503).json({
    error: service.errorCode,
    message:
      `${service.label} integration is not configured on this dashboard service. ` +
      `Set ${service.urlVariable} and ${service.tokenVariable}.`,
  });
}

/**
 * Build a same-origin proxy for one independently deployed audit service. The
 * browser only sends its HttpOnly dashboard session cookie; this process adds the
 * private API bearer token before forwarding.
 *
 * This deliberately forwards only the audit API surface, and never exposes the
 * token or the upstream URL in the Vite bundle.
 */
function createAuditProxy(service) {
  return async function auditProxy(req, res, next) {
    if (!isAllowedUpstreamUrl(service.url) || !service.token) {
      return auditConfigurationError(res, service);
    }
    if (!new Set(["GET", "POST", "HEAD"]).has(req.method)) {
      return res.status(405).set("Allow", "GET, POST, HEAD").end();
    }

    const suffix = req.originalUrl.slice(service.mountPath.length) || "/";
    if (!suffix.startsWith("/") || suffix.startsWith("//")) {
      return res.status(400).json({ error: "invalid_proxy_path" });
    }

    let upstreamUrl;
    try {
      // basePath is "" for a service serving the contract at its root, so this
      // is a no-op for those and prepends the prefix for the ones that need it.
      upstreamUrl = new URL(`${service.basePath ?? ""}${suffix}`, `${service.url}/`);
    } catch {
      return auditConfigurationError(res, service);
    }

    const controller = new AbortController();
    const proxyStartedAt = Date.now();
    const requestId = crypto.randomUUID();
    const abort = () => controller.abort();
    req.once("aborted", abort);
    res.once("close", abort);

    try {
      const headers = {
        Authorization: `Bearer ${service.token}`,
        Accept: req.headers.accept ?? "application/json",
      };
      if (req.headers["last-event-id"]) headers["Last-Event-ID"] = req.headers["last-event-id"];

      const hasBody = req.method === "POST";
      if (hasBody) headers["Content-Type"] = "application/json";
      const upstream = await fetch(upstreamUrl, {
        method: req.method,
        headers,
        body: hasBody ? JSON.stringify(req.body ?? {}) : undefined,
        signal: controller.signal,
      });

      const contentType = upstream.headers.get("content-type");
      if (contentType) res.setHeader("Content-Type", contentType);
      for (const header of ["cache-control", "content-disposition"]) {
        const value = upstream.headers.get(header);
        if (value) res.setHeader(header, value);
      }
      res.status(upstream.status);

      console.log(
        JSON.stringify({
          event: "audit_proxy_response",
          service: service.id,
          request_id: requestId,
          method: req.method,
          path: suffix.split("?")[0],
          upstream_status: upstream.status,
          stream: Boolean(contentType?.includes("text/event-stream")),
        }),
      );

      if (contentType?.includes("text/event-stream")) {
        // compression middleware honours no-transform; without it an intermediary
        // can buffer SSE chunks and make live audit progress appear frozen.
        res.setHeader("Cache-Control", "no-cache, no-transform");
        res.setHeader("Connection", "keep-alive");
        res.setHeader("X-Accel-Buffering", "no");
        res.flushHeaders();
        if (upstream.body) {
          for await (const chunk of upstream.body) {
            if (!res.writableEnded) {
              res.write(chunk);
              res.flush?.();
            }
          }
        }
        console.log(
          JSON.stringify({
            event: "audit_progress_stream_closed",
            service: service.id,
            request_id: requestId,
            path: suffix.split("?")[0],
            duration_ms: Date.now() - proxyStartedAt,
            client_connected: !controller.signal.aborted,
          }),
        );
        return res.end();
      }

      const body = Buffer.from(await upstream.arrayBuffer());
      return res.end(body);
    } catch (error) {
      if (controller.signal.aborted) return undefined;
      console.error(
        JSON.stringify({
          event: "audit_proxy_error",
          service: service.id,
          request_id: requestId,
          method: req.method,
          path: suffix.split("?")[0],
          duration_ms: Date.now() - proxyStartedAt,
          error: error instanceof Error ? error.message : String(error),
        }),
      );
      return next(error);
    } finally {
      req.off("aborted", abort);
      res.off("close", abort);
    }
  };
}

/* ── Client onboarding provisioning ──────────────────────────────
   Board -> activate -> editable draft -> batch approve. The flow TERMINATES
   at approval: no ClickUp request is issued anywhere in this file, by design.
   See onboarding-store.mjs for why APPROVED is a terminal state. */

const ONBOARDING_FILE =
  env("ONBOARDING_FILE") ?? path.join(__dirname, "..", ".data", "onboarding.json");
const onboarding = createOnboardingStore(ONBOARDING_FILE);

/** Map an OnboardingError to its status; anything else is a real 500. */
const sendOnboardingError = (res, error, next) => {
  if (error instanceof OnboardingError) {
    return res.status(error.status).json({ error: error.code, message: error.message });
  }
  return next(error);
};

const onboardingJson = express.json({ limit: "256kb" });

app.get("/api/onboarding", requireSession, (_req, res) => {
  res.json({
    ...onboarding.read(),
    status: onboarding.status(),
    offers: OFFERS,
    callAnchors: CALL_ANCHORS,
  });
});

/* Mark the existing client book as already onboarded. Until this runs, ingest
   refuses — a first poll against an empty store would read 90 days of Dubsado
   history as a queue of brand-new signings. */
app.post("/api/onboarding/seed", requireSession, onboardingJson, async (req, res, next) => {
  try {
    res.json(await onboarding.seed({ projectNames: req.body?.projectNames, note: req.body?.note }));
  } catch (error) {
    sendOnboardingError(res, error, next);
  }
});

/* Empty the store and drop the seed flag, returning it to the state a first
   boot would find.
 *
 * WHY THIS IS SAFE TO EXPOSE. It clears OUR OWN JSON document and nothing
 * else. The whole onboarding feature is read-only against ClickUp — every
 * call in server/clickup-*.mjs is a hard-coded GET and there is no
 * provisioning writer — so there is no external state for a reset to
 * desynchronise from. The templates it reads are committed data, not
 * something this can damage.
 *
 * WHY IT EXISTS. The console is a demo surface, and a demo that resumes
 * mid-flow is worse than useless: the reviewer arrives at a board where the
 * interesting card is already APPROVED from someone else's walkthrough. The
 * client calls this on mount so every page load starts the flow over. It
 * leaves the store UNSEEDED on purpose — `ingest` refuses until `seed` runs,
 * and that gate is the thing that stops a first pass reading ninety days of
 * history as new signings, so a reset must not quietly satisfy it. */
app.post("/api/onboarding/reset", requireSession, onboardingJson, async (_req, res, next) => {
  try {
    await onboarding.reset();
    /* Same composite shape as GET /api/onboarding, not a bare read(): the
       client types this as a Board, and `offers` / `callAnchors` are part of
       that contract. Returning less would make the response unusable without
       an immediate follow-up GET. */
    res.json({
      ...onboarding.read(),
      status: onboarding.status(),
      offers: OFFERS,
      callAnchors: CALL_ANCHORS,
    });
  } catch (error) {
    sendOnboardingError(res, error, next);
  }
});

/* Ingest one alert. Today this is a paste: Gmail scope on hello@ was never
   requested, so there is no mailbox to poll. The route is deliberately shaped
   like a poller's inner loop — subject + body in, correlation outcome out —
   so swapping a real Gmail read in later changes the caller, not this. */
app.post("/api/onboarding/ingest", requireSession, onboardingJson, async (req, res, next) => {
  try {
    const alert = parseDubsadoAlert({
      subject: req.body?.subject,
      body: req.body?.body,
      from: req.body?.from,
      receivedAt: req.body?.receivedAt,
    });
    if (!alert) {
      return res.status(422).json({
        error: "not_a_signature_alert",
        message:
          "Not one of the two Dubsado signature alerts. Every Dubsado notification shares one sender, so the subject is the filter.",
      });
    }
    const result = await onboarding.ingest(alert, { messageId: req.body?.messageId });
    res.json({ ...result, alert });
  } catch (error) {
    sendOnboardingError(res, error, next);
  }
});

/* Offer selection is REQUIRED and cannot be derived — the offer name appears
   on neither alert subject (see onboarding-alert-parser.mjs). */
app.post("/api/onboarding/:projectKey/activate", requireSession, onboardingJson, async (req, res, next) => {
  try {
    const offers = Array.isArray(req.body?.offers) ? req.body.offers : [];
    const client = await onboarding.activate(req.params.projectKey, {
      offers,
      draft: buildDraft({
        offers,
        projectName: onboarding
          .read()
          .clients.find((c) => c.projectKey === req.params.projectKey.toLowerCase())?.projectName,
        signatureDate: req.body?.signatureDate,
        /* Normally empty — the calls are booked after signature, which is
           what makes this a multi-wave flow. */
        anchorDates: req.body?.anchorDates ?? {},
      }),
    });
    res.json({ client, summary: summarizeDraft(client.draft) });
  } catch (error) {
    sendOnboardingError(res, error, next);
  }
});

/* WAVE 2+. A call gets booked; the tasks hanging off THAT anchor date
   themselves and nothing else does. Preserves deliberate overrides and
   recomputes derived ones — see applyAnchorDate in onboarding-store.mjs. */
app.post("/api/onboarding/:projectKey/anchor", requireSession, onboardingJson, async (req, res, next) => {
  try {
    const { client, computed, preserved } = await onboarding.applyAnchorDate(
      req.params.projectKey,
      { anchor: req.body?.anchor, date: req.body?.date },
    );
    res.json({ client, computed, preserved, summary: summarizeDraft(client.draft) });
  } catch (error) {
    sendOnboardingError(res, error, next);
  }
});

/* A reviewer's edits: rename a task, reassign it, change a date, or drop it
   from the batch. Saved without approving. */
app.put("/api/onboarding/:projectKey/draft", requireSession, onboardingJson, async (req, res, next) => {
  try {
    const client = await onboarding.updateDraft(req.params.projectKey, { draft: req.body?.draft });
    res.json({ client, summary: summarizeDraft(client.draft) });
  } catch (error) {
    sendOnboardingError(res, error, next);
  }
});

/* The gate. Records what a human authorised — including the rows they
   excluded — and stops. No ClickUp mutation is issued. */
app.post("/api/onboarding/:projectKey/approve", requireSession, onboardingJson, async (req, res, next) => {
  try {
    const approved = await onboarding.approve(req.params.projectKey, {
      draft: req.body?.draft,
      /* "setup" (default) approves the pre-booking batch; "schedule"
         approves the dates once the calls are booked. */
      wave: req.body?.wave,
    });
    /* Approving the ClickUp batch is step 1 of four. Opening steps 2-4 here
       rather than on demand keeps the pattern the activate route already sets:
       the plan is built server-side from their real template content and
       handed to the store, which only ever sanitizes and persists.

       Only the setup wave opens them. The scheduling wave leaves the record
       SCHEDULED, and initStages requires APPROVED — calling it unconditionally
       would 409 on the second wave. initStages is itself idempotent, so a
       retried setup approval still costs nothing. */
    const client =
      approved.state === "APPROVED"
        ? await onboarding.initStages(req.params.projectKey, {
            stages: buildStagePlans(stageInputFor(approved)),
          })
        : approved;
    res.json({ client, summary: summarizeDraft(client.approvedBatch) });
  } catch (error) {
    sendOnboardingError(res, error, next);
  }
});

/* ── Steps 2-4 · Drive, the welcome email, Slack ─────────────────
   Same shape as step 1 and the same boundary: a plan a human edits, then
   approves, and nothing is written. There is no Drive, Gmail or Slack client
   anywhere in this codebase — see onboarding-stages.mjs. */

/** Everything the stage builders need, read off the approved record. */
const stageInputFor = (client, overrides = {}) => {
  const offerKey = client.offers?.[0];
  const rawLabel = OFFERS[offerKey]?.label ?? null;
  /* The ads kickoff has no home on the draft — step 1 only ever collects one
     date, and on the one live client that one is the LEADLOCK kickoff. So it
     lives on step 4's own plan and is read back from there. */
  const storedAds =
    client.stages?.find((s) => s.key === "slack")?.plan?.anchors?.ads ?? null;
  return {
    projectName: client.projectName,
    firstName: client.halves?.signed?.firstName ?? client.halves?.paid?.firstName ?? null,
    offers: client.offers ?? [],
    templates: client.approvedBatch?.templates ?? client.draft?.templates ?? [],
    kickoffDate:
      overrides.kickoffDate ??
      client.approvedBatch?.kickoffDate ??
      client.draft?.kickoffDate ??
      null,
    adsKickoffDate: overrides.adsKickoffDate ?? storedAds,
    /* Their team brief writes the retainer as "signed on for ELEVATE!" and the
       LeadLock offer in title case, so the parenthetical qualifier comes off
       and only Elevate is shouted. */
    offerLabel: offerKey === "elevate" ? "ELEVATE" : rawLabel?.replace(/\s*\(.*\)$/, "") ?? null,
  };
};

app.put(
  "/api/onboarding/:projectKey/stage/:stage",
  requireSession,
  onboardingJson,
  async (req, res, next) => {
    try {
      const client = await onboarding.updateStage(req.params.projectKey, {
        stage: req.params.stage,
        plan: req.body?.plan,
      });
      const stage = client.stages.find((s) => s.key === req.params.stage);
      res.json({ client, summary: summarizeStage(stage?.plan) });
    } catch (error) {
      sendOnboardingError(res, error, next);
    }
  },
);

app.post(
  "/api/onboarding/:projectKey/stage/:stage/approve",
  requireSession,
  onboardingJson,
  async (req, res, next) => {
    try {
      const client = await onboarding.approveStage(req.params.projectKey, {
        stage: req.params.stage,
        plan: req.body?.plan,
      });
      const stage = client.stages.find((s) => s.key === req.params.stage);
      res.json({ client, summary: summarizeStage(stage?.approvedPlan) });
    } catch (error) {
      sendOnboardingError(res, error, next);
    }
  },
);

/* The kickoff bookings arriving after step 1 was approved — the only way
   through step 4's gate.

   TWO dates, because their brief names two and the two timeline variants count
   weeks from different ones. `kickoffDate` is the LeadLock/phase anchor and
   also recomputes the ClickUp due dates; `adsKickoffDate` only feeds step 4's
   posts, since nothing in the ads template carries a cadence to compute from
   (`Phase (Full Service)`'s Google/Meta Ads Setup are absent from PHASE_WEEK
   entirely). Either may be sent alone. */
app.post(
  "/api/onboarding/:projectKey/stage-kickoff",
  requireSession,
  onboardingJson,
  async (req, res, next) => {
    try {
      const { kickoffDate, adsKickoffDate } = req.body ?? {};
      if (!kickoffDate && !adsKickoffDate) {
        throw new OnboardingError("invalid_date", "A kickoff date is required.");
      }
      let client = onboarding
        .read()
        .clients.find((c) => c.projectKey === req.params.projectKey.toLowerCase());
      let computed = 0;
      if (kickoffDate) {
        ({ client, computed } = await onboarding.recordKickoff(req.params.projectKey, {
          kickoffDate,
        }));
      }
      if (!client) throw new OnboardingError("not_found", "No onboarding record for that project.", 404);
      const slack = client.stages.find((s) => s.key === "slack");
      if (slack && slack.state !== "APPROVED") {
        await onboarding.updateStage(req.params.projectKey, {
          stage: "slack",
          plan: rehydrateSlackStage(slack.plan, stageInputFor(client, { adsKickoffDate })),
        });
      }
      const fresh = onboarding
        .read()
        .clients.find((c) => c.projectKey === req.params.projectKey.toLowerCase());
      res.json({ client: fresh ?? client, computed });
    } catch (error) {
      sendOnboardingError(res, error, next);
    }
  },
);

app.post("/api/onboarding/:projectKey/ignore", requireSession, onboardingJson, async (req, res, next) => {
  try {
    res.json({
      client: await onboarding.ignore(req.params.projectKey, {
        reason: req.body?.reason,
        note: req.body?.note,
      }),
    });
  } catch (error) {
    sendOnboardingError(res, error, next);
  }
});

app.post("/api/onboarding/expire", requireSession, onboardingJson, async (req, res, next) => {
  try {
    res.json(await onboarding.expireStalePairs({ ttlDays: req.body?.ttlDays }));
  } catch (error) {
    sendOnboardingError(res, error, next);
  }
});

for (const service of AUDIT_SERVICES) {
  app.use(service.mountPath, requireSession, createAuditProxy(service));
}

/* ── Static SPA ───────────────────────────────────────────────── */

// Vite fingerprints /assets filenames, so they're immutable; everything else
// (index.html, favicons) stays no-cache — same policy nginx applied.
app.use(
  express.static(DIST_DIR, {
    index: false,
    setHeaders(res, filePath) {
      if (filePath.includes(`${path.sep}assets${path.sep}`)) {
        res.setHeader("Cache-Control", "public, max-age=31536000, immutable");
      } else {
        res.setHeader("Cache-Control", "no-cache");
      }
    },
  }),
);

// SPA fallback: let React Router own every unmatched GET path.
app.use((req, res) => {
  if (req.method !== "GET" && req.method !== "HEAD") return res.status(404).end();
  const indexHtml = path.join(DIST_DIR, "index.html");
  if (!fs.existsSync(indexHtml)) {
    return res
      .status(503)
      .type("text/plain")
      .send("Frontend build not found — run `npm run build` first.\n");
  }
  res.setHeader("Cache-Control", "no-cache");
  res.sendFile(indexHtml);
});

app.listen(PORT, async () => {
  const accounts = USERS.map((u) => `${u.email} (${u.role})`).join(", ");
  console.log(`[command-center] listening on :${PORT} (accounts: ${accounts})`);

  const store = bookmarks.status();
  console.log(
    `[bookmarks] ${store.counts.bookmarks} bookmarks / ${store.counts.groups} groups at ${store.path}`,
  );
  if (store.loadError) {
    console.warn(
      `[bookmarks] existing file could not be read (${store.loadError}); starting empty. ` +
        "The unreadable file was left in place for inspection.",
    );
  }
  if (!env("BOOKMARKS_FILE")) {
    console.warn(
      "[bookmarks] BOOKMARKS_FILE not set — using the container filesystem, so bookmarks " +
        "reset on redeploy. Mount a Railway volume and point BOOKMARKS_FILE at it " +
        "(e.g. /data/bookmarks.json) to make them permanent.",
    );
  }

  const leadStore = await leads.status();
  console.log(
    `[leadmagnet] ${leadStore.counts.leads} leads via ${leadStore.backend ?? leadStore.path} ` +
      `(capture origins: ${LEADMAGNET_CAPTURE_ORIGINS.join(", ")})`,
  );
  if (leadStore.loadError) {
    console.warn(
      `[leadmagnet] existing file could not be read (${leadStore.loadError}); starting empty. ` +
        "The unreadable file was left in place for inspection.",
    );
  }
  if (!LEADS_DATABASE_URL && !env("LEADS_FILE")) {
    console.warn(
      "[leadmagnet] LEADS_FILE not set — using the container filesystem, so captured leads " +
        "reset on redeploy. Mount a Railway volume and point LEADS_FILE at it " +
        "(e.g. /data/leads.json) to make them permanent.",
    );
  }
  for (const service of AUDIT_SERVICES) {
    // Report WHICH half is wrong and why. A bare "not configured" is actively
    // misleading when the variable is set but its URL was rejected by policy.
    const urlProblem = describeUpstreamUrlRejection(service.url);
    const problems = [];
    if (urlProblem) problems.push(`${service.urlVariable}: ${urlProblem}`);
    if (!service.token) problems.push(`${service.tokenVariable}: not set`);
    if (problems.length) {
      console.warn(
        `[${service.id}] ${service.label} BFF is not usable — ${problems.join("; ")}.`,
      );
    }
  }
});
