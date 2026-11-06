import crypto from "node:crypto";
import express from "express";
import { isAllowedUpstreamUrl } from "./upstream-url.mjs";

const CALLBACK_PATH = "/api/auth/sso/callback";
const validChallenge = value => typeof value === "string" && /^[A-Za-z0-9_-]{43}$/.test(value);
const validState = value => typeof value === "string" && /^[A-Za-z0-9_-]{32,128}$/.test(value);

function destination(value, nodeEnv) {
  if (!isAllowedUpstreamUrl(value, { nodeEnv })) return null;
  const url = new URL(value);
  return url.username || url.password || url.hash ? null : url;
}

/** The Content Atelier's origin from VITE_CONTENT_ATELIER_URL, or null when it is unset or not allowed. The sign-out
 * round trip (index.mjs, /api/auth/signout) redirects only here, so it can never become an open redirect. */
export function atelierOrigin(value, nodeEnv = process.env.NODE_ENV) {
  return destination(value, nodeEnv)?.origin ?? null;
}

/** Command Center's sign-in, returning to `path` (this router's own route) once signed in, so the hand-off to the
 * Atelier resumes instead of leaving the person on the dashboard. LoginPage follows `next` only for these routes. */
const signIn = path => `/login?next=${encodeURIComponent(path)}`;

/** One-time authorization codes. The original session stays on the backchannel;
 * the browser receives only a short-lived code bound to a PKCE challenge.
 * Codes are process-local and fail closed across restarts or other replicas.
 */
export function createAtelierSsoRouter({ atelierUrl, resolveUser, readToken, sessionExpiry, nodeEnv = process.env.NODE_ENV, now = Date.now, lifetimeMs = 60_000, capacity = 1000 }) {
  const target = destination(atelierUrl, nodeEnv);
  const callback = target ? new URL(CALLBACK_PATH, target.origin).href : null;
  const codes = new Map();
  const router = express.Router();
  router.use((_req, res, next) => {
    res.set({ "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" });
    next();
  });
  const configured = res => {
    if (target) return true;
    res.status(503).json({ error: "Set VITE_CONTENT_ATELIER_URL to the public Content Atelier URL on Command Center." });
    return false;
  };
  const purge = () => {
    for (const [code, entry] of codes) if (entry.expiresAt <= now()) codes.delete(code);
  };

  router.get("/launch", (req, res) => {
    if (!configured(res)) return;
    if (!resolveUser(req)) return res.redirect(302, signIn(req.originalUrl));
    const start = new URL("/api/auth/sso/start", target.origin);
    start.searchParams.set("returnTo", target.pathname + target.search);
    res.redirect(302, start.href);
  });

  router.get("/authorize", (req, res) => {
    if (!configured(res)) return;
    const { redirect_uri, state, code_challenge, code_challenge_method } = req.query;
    // Exact callback matching closes open redirects and code exfiltration.
    if (redirect_uri !== callback || !validState(state) || !validChallenge(code_challenge) || code_challenge_method !== "S256") {
      return res.status(400).json({ error: "Invalid Content Atelier sign-in request." });
    }
    const user = resolveUser(req);
    if (!user) return res.redirect(302, signIn(req.originalUrl));
    const token = readToken(req);
    const exp = sessionExpiry(token);
    if (!token || !Number.isFinite(exp) || exp <= now()) return res.redirect(302, signIn(req.originalUrl));
    purge();
    if (codes.size >= capacity) return res.status(503).json({ error: "Sign-in is busy. Please retry shortly." });
    const code = crypto.randomBytes(32).toString("base64url");
    const key = crypto.createHash("sha256").update(code).digest("hex");
    codes.set(key, { token, challenge: code_challenge, expiresAt: Math.min(now() + lifetimeMs, exp) });
    const redirect = new URL(callback);
    redirect.searchParams.set("code", code);
    redirect.searchParams.set("state", state);
    res.redirect(302, redirect.href);
  });

  router.post("/exchange", express.json({ limit: "4kb" }), (req, res) => {
    if (!configured(res)) return;
    purge();
    const { code, redirect_uri, code_verifier } = req.body || {};
    if (typeof code !== "string" || !/^[A-Za-z0-9_-]{43}$/.test(code) || redirect_uri !== callback || typeof code_verifier !== "string" || !/^[A-Za-z0-9._~-]{43,128}$/.test(code_verifier)) {
      return res.status(400).json({ error: "Invalid sign-in exchange." });
    }
    const key = crypto.createHash("sha256").update(code).digest("hex");
    const entry = codes.get(key);
    if (!entry) return res.status(401).json({ error: "Sign-in code expired or was already used. Open Content Atelier again." });
    const challenge = crypto.createHash("sha256").update(code_verifier).digest("base64url");
    if (!crypto.timingSafeEqual(Buffer.from(challenge), Buffer.from(entry.challenge))) {
      return res.status(401).json({ error: "Invalid sign-in proof." });
    }
    // Consume before returning anything: concurrent redemption cannot succeed.
    codes.delete(key);
    const user = resolveUser({ headers: { cookie: `wahha_session=${encodeURIComponent(entry.token)}` } });
    const expiresIn = Math.floor((sessionExpiry(entry.token) - now()) / 1000);
    if (!user || !Number.isFinite(expiresIn) || expiresIn < 1) return res.status(401).json({ error: "Command Center session has expired." });
    res.json({ sessionToken: entry.token, expiresIn, user: { email: user.email, name: user.name, role: user.role } });
  });
  return router;
}
