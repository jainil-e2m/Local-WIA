/* ────────────────────────────────────────────────────────────────
   Pure auth primitives for the Command Center server.

   Extracted from index.mjs so the account-resolution, session-token
   and password logic can be unit-tested in isolation (see
   auth-core.test.mjs) without booting the Express listener. Nothing
   here reads process.env or touches the network — index.mjs owns all
   configuration and wiring.
   ──────────────────────────────────────────────────────────────── */

import crypto from "node:crypto";

export const ROLES = ["team", "client"];

/** Highest USER_n_* slot index scanned. A cap keeps the boot-time scan bounded
    and makes a typo'd USER_99_EMAIL surface as "never applied" rather than
    silently costing nothing; raise it if a deployment ever outgrows it. */
export const MAX_EXTRA_USERS = 20;

/**
 * Collect the numbered USER_n_* accounts into plain descriptors.
 *
 * `readEnv(name)` is injected rather than read from process.env here, keeping
 * this module free of configuration (index.mjs owns that) and letting the tests
 * drive it from a literal object.
 *
 * Slots are scanned 1..MAX_EXTRA_USERS and gaps are skipped silently, so
 * deleting USER_2_* in Railway does not disable USER_3_*. A slot with SOME of
 * its vars set is reported by resolveUsers, not swallowed — that is the shape
 * a half-finished Railway edit takes, and it must not fail silently.
 *
 * @returns {Array<{slot:number,email?:string,name?:string,passwordHash?:string,role?:string}>}
 */
export function collectExtraUsers(readEnv) {
  const found = [];
  for (let slot = 1; slot <= MAX_EXTRA_USERS; slot += 1) {
    const email = readEnv(`USER_${slot}_EMAIL`);
    const passwordHash = readEnv(`USER_${slot}_PASSWORD_HASH`);
    const name = readEnv(`USER_${slot}_NAME`);
    const role = readEnv(`USER_${slot}_ROLE`);
    if (!email && !passwordHash && !name && !role) continue; // empty slot
    found.push({ slot, email, name, passwordHash, role });
  }
  return found;
}

/**
 * Resolve the configured accounts into an ordered user list.
 *
 * The team account always exists (it keeps its committed defaults in
 * index.mjs). The client account is added ONLY when both its email and
 * password hash are present, so an un-configured deployment behaves
 * exactly as the previous single-account build did.
 *
 * `extraUsers` (from collectExtraUsers) appends any number of further accounts
 * from numbered USER_n_* variables. They are validated exactly like the client
 * account — both email and hash required, duplicates rejected — so adding the
 * fourth, fifth… login is a Railway variable change and nothing more.
 *
 * Every warning names the offending variable, because the only person who ever
 * reads them is an operator staring at a login that will not work.
 *
 * @returns {{ users: Array<{email:string,name:string,hash:string,role:"team"|"client"}>, warnings: string[] }}
 */
export function resolveUsers({
  authEmail,
  authName,
  authPasswordHash,
  clientEmail,
  clientName,
  clientPasswordHash,
  extraUsers = [],
}) {
  const warnings = [];

  const team = {
    email: String(authEmail).trim().toLowerCase(),
    name: authName,
    hash: authPasswordHash,
    role: "team",
  };
  const users = [team];

  /** Add one configured account, or explain in `warnings` why it was skipped. */
  const addUser = ({ email, name, hash, role, source, fallbackName }) => {
    const normalized = String(email).trim().toLowerCase();
    const clash = users.find((u) => u.email === normalized);
    if (clash) {
      warnings.push(
        `${source}_EMAIL (${normalized}) duplicates an account already configured ` +
          `(${clash.email}, role ${clash.role}) — the ${source} account was ignored.`,
      );
      return;
    }
    users.push({ email: normalized, name: name || fallbackName(normalized), hash, role });
  };

  if (clientEmail && clientPasswordHash) {
    addUser({
      email: clientEmail,
      name: clientName,
      hash: clientPasswordHash,
      role: "client",
      source: "CLIENT",
      fallbackName: () => "Client",
    });
  } else if (clientEmail || clientPasswordHash) {
    warnings.push(
      "Client account is only partially configured — set both CLIENT_EMAIL and " +
        "CLIENT_PASSWORD_HASH (CLIENT_NAME optional) to enable the second login.",
    );
  }

  for (const extra of extraUsers) {
    const source = `USER_${extra.slot}`;
    if (!extra.email || !extra.passwordHash) {
      warnings.push(
        `${source} is only partially configured — set both ${source}_EMAIL and ` +
          `${source}_PASSWORD_HASH (${source}_NAME and ${source}_ROLE optional) ` +
          "to enable that login.",
      );
      continue;
    }
    let role = "client";
    if (extra.role) {
      const requested = String(extra.role).trim().toLowerCase();
      if (ROLES.includes(requested)) {
        role = requested;
      } else {
        warnings.push(
          `${source}_ROLE ("${extra.role}") is not one of ${ROLES.join(", ")} — ` +
            'defaulting that account to "client".',
        );
      }
    }
    addUser({
      email: extra.email,
      name: extra.name,
      hash: extra.passwordHash,
      role,
      source,
      // No USER_n_NAME: fall back to the email's local part, which reads far
      // better in the header pill than a slot number would.
      fallbackName: (normalized) => normalized.split("@")[0],
    });
  }

  return { users, warnings };
}

/**
 * Session-token codec: `base64url(payload).hmac`.
 *
 * Token integrity only — it does NOT decide identity. index.mjs looks the
 * decoded email up in the live user list so configuration is always the
 * source of truth (removing the client env vars invalidates its sessions,
 * and a role is re-derived rather than trusted from the cookie). The role is
 * embedded for forward use; a legacy `{ email, exp }` cookie (issued before
 * roles existed) still verifies because role is never required here.
 */
export function createSessionCodec({ secret, ttlMs, now = () => Date.now() }) {
  const sign = (data) => crypto.createHmac("sha256", secret).update(data).digest("base64url");

  const createSessionToken = (user) => {
    const payload = Buffer.from(
      JSON.stringify({ email: user.email, role: user.role, exp: now() + ttlMs }),
    ).toString("base64url");
    return `${payload}.${sign(payload)}`;
  };

  const verifySessionToken = (token) => {
    if (typeof token !== "string") return null;
    const dot = token.lastIndexOf(".");
    if (dot < 1) return null;
    const payload = token.slice(0, dot);
    const sig = Buffer.from(token.slice(dot + 1));
    const expected = Buffer.from(sign(payload));
    if (sig.length !== expected.length || !crypto.timingSafeEqual(sig, expected)) return null;
    try {
      const data = JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
      if (typeof data.exp !== "number" || data.exp < now()) return null;
      return data;
    } catch {
      return null;
    }
  };

  return { createSessionToken, verifySessionToken };
}

const SCRYPT = { N: 16384, r: 8, p: 1 };

/**
 * Verify a plaintext password against a stored `scrypt$N$r$p$salt$hash` value.
 * Fails CLOSED on any malformed stored value — an empty/missing hash or salt
 * segment or non-integer params return false rather than throwing or (worse)
 * matching. This matters because operators now paste a second, hand-entered
 * CLIENT_PASSWORD_HASH; a truncated or mangled value must reject every password,
 * never accept them.
 */
export function verifyPassword(password, stored) {
  if (typeof password !== "string" || typeof stored !== "string") return false;
  const parts = stored.split("$");
  if (parts.length !== 6) return false;
  const [scheme, N, r, p, saltB64, hashB64] = parts;
  if (scheme !== "scrypt" || !saltB64 || !hashB64) return false;
  const expected = Buffer.from(hashB64, "base64");
  if (expected.length === 0) return false;
  let actual;
  try {
    actual = crypto.scryptSync(password, Buffer.from(saltB64, "base64"), expected.length, {
      N: Number(N),
      r: Number(r),
      p: Number(p),
    });
  } catch {
    return false; // non-integer / out-of-range params, etc.
  }
  return actual.length === expected.length && crypto.timingSafeEqual(actual, expected);
}

/**
 * A well-formed but unmatchable scrypt hash. Used to equalize login timing for
 * unknown emails (see authenticateCredentials) so account existence cannot be
 * probed via response latency.
 */
export function createDecoyHash() {
  const salt = crypto.randomBytes(16);
  const hash = crypto.scryptSync(crypto.randomBytes(32), salt, 64, SCRYPT);
  return [
    "scrypt",
    SCRYPT.N,
    SCRYPT.r,
    SCRYPT.p,
    salt.toString("base64"),
    hash.toString("base64"),
  ].join("$");
}

/**
 * Resolve a login attempt to the matching user record, or null.
 *
 * Always runs exactly one scrypt verification — against the real hash when the
 * email is known, otherwise against `decoyHash` — so a wrong password and an
 * unknown email cost the same time and return the same (null) result. This
 * removes the user-enumeration timing side channel while keeping the identical
 * generic 401 the caller already returns.
 */
export function authenticateCredentials(email, password, findUser, decoyHash) {
  const normalized = typeof email === "string" ? email.trim().toLowerCase() : "";
  const user = normalized ? findUser(normalized) : undefined;
  const ok = verifyPassword(password, user?.hash ?? decoyHash);
  return user && ok ? user : null;
}

/**
 * Resolve a raw session cookie value to the authoritative user record, or null.
 *
 * Identity comes from the token payload's email, but `name`/`role` are re-read
 * from the live user list via `findUser` — the token's own role (if any) is
 * never trusted. This is what makes a legacy pre-role cookie still work and a
 * forged role in a cookie irrelevant; configuration is always the source of
 * truth.
 */
export function resolveSessionUser(rawToken, verifySessionToken, findUser, isRevoked = () => false) {
  if (isRevoked(rawToken)) return null;
  const payload = verifySessionToken(rawToken);
  if (!payload || typeof payload.email !== "string") return null;
  return findUser(payload.email) ?? null;
}

/**
 * Signed-out sessions, so one sign-out ends the session everywhere it is used.
 *
 * The session token is stateless (an HMAC over email and expiry), and the
 * Content Atelier holds the very same token in its own cookie after the
 * sign-in hand-off (atelier-sso.mjs). Clearing one cookie therefore cannot end
 * the other. Instead a sign-out records the token here (by its SHA-256, never
 * the token itself) until it would have expired, and every session check
 * refuses it: the Atelier checks each request against /api/auth/session, so a
 * sign-out in either app takes effect in both on the next request.
 *
 * Process memory, bounded by `capacity` (oldest entries go first). A restart
 * forgets it, which is why sign-out also clears both browsers' cookies (the
 * /api/auth/signout round trip in index.mjs): the revocation covers a cookie
 * that survived elsewhere, the cookie clearing covers a restart.
 */
export function createSessionRevocations({ now = () => Date.now(), capacity = 10_000 } = {}) {
  const revoked = new Map(); // sha256(token) → epoch ms until which it stays refused
  const digest = (token) => crypto.createHash("sha256").update(token).digest("hex");
  const purge = () => {
    for (const [key, until] of revoked) if (until <= now()) revoked.delete(key);
  };

  /** Refuse `token` from now until `until` (its expiry). Returns false for a missing token. */
  const revoke = (token, until) => {
    if (typeof token !== "string" || !token) return false;
    purge();
    while (revoked.size >= capacity) revoked.delete(revoked.keys().next().value);
    revoked.set(digest(token), Number.isFinite(until) ? until : now() + 7 * 24 * 60 * 60 * 1000);
    return true;
  };

  const isRevoked = (token) => {
    if (typeof token !== "string" || !token) return false;
    const until = revoked.get(digest(token));
    return until !== undefined && until > now();
  };

  return { revoke, isRevoked, size: () => revoked.size };
}
