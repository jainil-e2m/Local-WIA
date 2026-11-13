import { describe, it, expect } from "vitest";
import crypto from "node:crypto";
import {
  collectExtraUsers,
  resolveUsers,
  createSessionCodec,
  verifyPassword,
  createDecoyHash,
  authenticateCredentials,
  resolveSessionUser,
  createSessionRevocations,
} from "./auth-core.mjs";

const TEAM = {
  authEmail: "team@wahha.design",
  authName: "Wahha Design",
  authPasswordHash: "scrypt$16384$8$1$abc$def",
};

/** Build a real scrypt$… value the way hash-password.mjs does. */
function hashPassword(password) {
  const salt = crypto.randomBytes(16);
  const hash = crypto.scryptSync(password, salt, 64, { N: 16384, r: 8, p: 1 });
  return ["scrypt", 16384, 8, 1, salt.toString("base64"), hash.toString("base64")].join("$");
}

describe("resolveUsers", () => {
  it("stays single-account when the client is not configured", () => {
    const { users, warnings } = resolveUsers(TEAM);
    expect(warnings).toEqual([]);
    expect(users).toHaveLength(1);
    expect(users[0]).toMatchObject({ email: "team@wahha.design", role: "team" });
  });

  it("adds the client account when both email and hash are set", () => {
    const { users, warnings } = resolveUsers({
      ...TEAM,
      clientEmail: "  Client@Acme.com ",
      clientPasswordHash: "scrypt$16384$8$1$ghi$jkl",
    });
    expect(warnings).toEqual([]);
    expect(users).toHaveLength(2);
    // Client email is trimmed + lowercased; missing name falls back to "Client".
    expect(users[1]).toMatchObject({ email: "client@acme.com", name: "Client", role: "client" });
  });

  it("honours an explicit client display name", () => {
    const { users } = resolveUsers({
      ...TEAM,
      clientEmail: "client@acme.com",
      clientName: "Acme Corp",
      clientPasswordHash: "scrypt$16384$8$1$ghi$jkl",
    });
    expect(users[1].name).toBe("Acme Corp");
  });

  it("ignores a client that duplicates the team email, with a warning", () => {
    const { users, warnings } = resolveUsers({
      ...TEAM,
      clientEmail: "TEAM@wahha.design",
      clientPasswordHash: "scrypt$16384$8$1$ghi$jkl",
    });
    expect(users).toHaveLength(1);
    expect(warnings[0]).toMatch(/CLIENT_EMAIL .* duplicates an account/);
  });

  it("warns when the client is only partially configured", () => {
    const { users, warnings } = resolveUsers({ ...TEAM, clientEmail: "client@acme.com" });
    expect(users).toHaveLength(1);
    expect(warnings[0]).toMatch(/partially configured/);
  });
});

/* The numbered USER_n_* slots are how a third, fourth… login gets added without
   a code change, so the parts an operator can get wrong in the Railway UI — a
   half-filled slot, a duplicate address, a mistyped role — are pinned here. */
describe("resolveUsers with numbered USER_n_* accounts", () => {
  const extra = (slot, over = {}) => ({
    slot,
    email: `user${slot}@wahha.design`,
    passwordHash: "scrypt$16384$8$1$mno$pqr",
    ...over,
  });

  it("appends an extra account after the team and client ones", () => {
    const { users, warnings } = resolveUsers({
      ...TEAM,
      clientEmail: "client@acme.com",
      clientPasswordHash: "scrypt$16384$8$1$ghi$jkl",
      extraUsers: [extra(1, { name: "Dana" })],
    });
    expect(warnings).toEqual([]);
    expect(users).toHaveLength(3);
    expect(users[2]).toMatchObject({
      email: "user1@wahha.design",
      name: "Dana",
      role: "client",
    });
  });

  it("adds extra accounts even when no client account is configured", () => {
    const { users, warnings } = resolveUsers({ ...TEAM, extraUsers: [extra(4)] });
    expect(warnings).toEqual([]);
    expect(users.map((u) => u.email)).toEqual(["team@wahha.design", "user4@wahha.design"]);
  });

  it("normalizes the email and falls back to its local part for the name", () => {
    const { users } = resolveUsers({
      ...TEAM,
      extraUsers: [extra(1, { email: "  Priya@Wahha.Design " })],
    });
    expect(users[1]).toMatchObject({ email: "priya@wahha.design", name: "priya" });
  });

  it('defaults an extra account to the "client" role', () => {
    const { users } = resolveUsers({ ...TEAM, extraUsers: [extra(1)] });
    expect(users[1].role).toBe("client");
  });

  it('honours an explicit "team" role', () => {
    const { users, warnings } = resolveUsers({
      ...TEAM,
      extraUsers: [extra(1, { role: " Team " })],
    });
    expect(warnings).toEqual([]);
    expect(users[1].role).toBe("team");
  });

  it("falls back to client and warns on an unknown role", () => {
    const { users, warnings } = resolveUsers({
      ...TEAM,
      extraUsers: [extra(1, { role: "admin" })],
    });
    expect(users[1].role).toBe("client");
    expect(warnings[0]).toMatch(/USER_1_ROLE .*is not one of/);
  });

  it("skips a half-configured slot with a warning naming its variables", () => {
    const { users, warnings } = resolveUsers({
      ...TEAM,
      extraUsers: [{ slot: 3, email: "user3@wahha.design" }],
    });
    expect(users).toHaveLength(1);
    expect(warnings[0]).toMatch(/USER_3 is only partially configured/);
    expect(warnings[0]).toMatch(/USER_3_PASSWORD_HASH/);
  });

  it("rejects an extra account that duplicates the team or client email", () => {
    const { users, warnings } = resolveUsers({
      ...TEAM,
      clientEmail: "client@acme.com",
      clientPasswordHash: "scrypt$16384$8$1$ghi$jkl",
      extraUsers: [
        extra(1, { email: "TEAM@wahha.design" }),
        extra(2, { email: "client@acme.com" }),
      ],
    });
    expect(users).toHaveLength(2);
    expect(warnings[0]).toMatch(/USER_1_EMAIL .* duplicates an account/);
    expect(warnings[1]).toMatch(/USER_2_EMAIL .* duplicates an account/);
  });

  it("rejects a later slot that duplicates an earlier one", () => {
    const { users, warnings } = resolveUsers({
      ...TEAM,
      extraUsers: [
        extra(1, { email: "dupe@wahha.design" }),
        extra(2, { email: "dupe@wahha.design" }),
      ],
    });
    expect(users).toHaveLength(2);
    expect(warnings).toHaveLength(1);
    expect(warnings[0]).toMatch(/USER_2_EMAIL/);
  });

  it("keeps every configured slot distinct and signed-in-able", () => {
    const { users, warnings } = resolveUsers({
      ...TEAM,
      extraUsers: [extra(1), extra(2), extra(7, { role: "team" })],
    });
    expect(warnings).toEqual([]);
    expect(users).toHaveLength(4);
    expect(new Set(users.map((u) => u.email)).size).toBe(4);
  });
});

describe("collectExtraUsers", () => {
  /** Stand-in for index.mjs's env() — undefined for anything unset. */
  const reader = (vars) => (name) => vars[name];

  it("returns nothing when no USER_n_* variables are set", () => {
    expect(collectExtraUsers(reader({}))).toEqual([]);
  });

  it("collects a slot's four fields", () => {
    const found = collectExtraUsers(
      reader({
        USER_1_EMAIL: "dana@wahha.design",
        USER_1_PASSWORD_HASH: "scrypt$16384$8$1$mno$pqr",
        USER_1_NAME: "Dana",
        USER_1_ROLE: "team",
      }),
    );
    expect(found).toEqual([
      {
        slot: 1,
        email: "dana@wahha.design",
        passwordHash: "scrypt$16384$8$1$mno$pqr",
        name: "Dana",
        role: "team",
      },
    ]);
  });

  it("skips gaps so deleting USER_1_* does not disable USER_3_*", () => {
    const found = collectExtraUsers(
      reader({ USER_3_EMAIL: "c@wahha.design", USER_3_PASSWORD_HASH: "h" }),
    );
    expect(found.map((u) => u.slot)).toEqual([3]);
  });

  it("reports a half-filled slot rather than swallowing it", () => {
    // Only the email set: resolveUsers must get the slot so it can warn.
    const found = collectExtraUsers(reader({ USER_2_EMAIL: "b@wahha.design" }));
    expect(found).toEqual([
      {
        slot: 2,
        email: "b@wahha.design",
        passwordHash: undefined,
        name: undefined,
        role: undefined,
      },
    ]);
  });

  it("ignores slots past the scanned range", () => {
    const found = collectExtraUsers(
      reader({ USER_21_EMAIL: "too-far@wahha.design", USER_21_PASSWORD_HASH: "h" }),
    );
    expect(found).toEqual([]);
  });
});

describe("createSessionCodec", () => {
  const secret = "unit-test-secret";

  it("round-trips a token carrying the user's role", () => {
    const codec = createSessionCodec({ secret, ttlMs: 1000, now: () => 1000 });
    const token = codec.createSessionToken({ email: "client@acme.com", role: "client" });
    expect(codec.verifySessionToken(token)).toMatchObject({
      email: "client@acme.com",
      role: "client",
      exp: 2000,
    });
  });

  it("rejects a tampered signature", () => {
    const codec = createSessionCodec({ secret, ttlMs: 1000, now: () => 1000 });
    const token = codec.createSessionToken({ email: "team@wahha.design", role: "team" });
    expect(codec.verifySessionToken(`${token}x`)).toBeNull();
  });

  it("rejects a token signed with a different secret", () => {
    const a = createSessionCodec({ secret: "secret-a", ttlMs: 1000, now: () => 1000 });
    const b = createSessionCodec({ secret: "secret-b", ttlMs: 1000, now: () => 1000 });
    const token = a.createSessionToken({ email: "team@wahha.design", role: "team" });
    expect(b.verifySessionToken(token)).toBeNull();
  });

  it("rejects an expired token", () => {
    const issued = createSessionCodec({ secret, ttlMs: 100, now: () => 1000 }); // exp = 1100
    const later = createSessionCodec({ secret, ttlMs: 100, now: () => 5000 });
    const token = issued.createSessionToken({ email: "team@wahha.design", role: "team" });
    expect(later.verifySessionToken(token)).toBeNull();
  });

  it("still verifies a legacy pre-role cookie (backward compatibility)", () => {
    const sign = (d) => crypto.createHmac("sha256", secret).update(d).digest("base64url");
    const payload = Buffer.from(JSON.stringify({ email: "team@wahha.design", exp: 9000 })).toString(
      "base64url",
    );
    const legacyToken = `${payload}.${sign(payload)}`;
    const codec = createSessionCodec({ secret, ttlMs: 100, now: () => 1000 });
    expect(codec.verifySessionToken(legacyToken)).toMatchObject({ email: "team@wahha.design" });
  });

  it("returns null for non-string / malformed input", () => {
    const codec = createSessionCodec({ secret, ttlMs: 1000, now: () => 1000 });
    expect(codec.verifySessionToken(undefined)).toBeNull();
    expect(codec.verifySessionToken("no-dot")).toBeNull();
  });
});

describe("verifyPassword", () => {
  it("accepts the correct password and rejects a wrong one", () => {
    const stored = hashPassword("correct horse battery staple");
    expect(verifyPassword("correct horse battery staple", stored)).toBe(true);
    expect(verifyPassword("wrong password", stored)).toBe(false);
  });

  it("rejects a non-scrypt scheme and non-string inputs", () => {
    expect(verifyPassword("x", "bcrypt$abc$def")).toBe(false);
    expect(verifyPassword(undefined, hashPassword("x"))).toBe(false);
    expect(verifyPassword("x", undefined)).toBe(false);
  });

  it("fails CLOSED on malformed stored hashes (never fail-open)", () => {
    // Empty hash segment must NOT accept every password.
    expect(verifyPassword("anything", "scrypt$16384$8$1$c2FsdA==$")).toBe(false);
    expect(verifyPassword("", "scrypt$16384$8$1$c2FsdA==$")).toBe(false);
    // Empty salt segment.
    expect(verifyPassword("x", "scrypt$16384$8$1$$aGFzaA==")).toBe(false);
    // Non-integer params must return false, not throw.
    expect(verifyPassword("x", "scrypt$abc$8$1$c2FsdA==$aGFzaA==")).toBe(false);
    // Wrong number of segments.
    expect(verifyPassword("x", "scrypt$16384$8$1")).toBe(false);
  });
});

describe("authenticateCredentials", () => {
  const users = [
    { email: "team@wahha.design", name: "Team", hash: hashPassword("team-pw"), role: "team" },
    { email: "client@acme.com", name: "Client", hash: hashPassword("client-pw"), role: "client" },
  ];
  const findUser = (e) => users.find((u) => u.email === e);
  const decoy = createDecoyHash();

  it("returns the matching user for correct credentials (email trimmed + lowercased)", () => {
    expect(authenticateCredentials("  TEAM@wahha.design ", "team-pw", findUser, decoy)?.role).toBe(
      "team",
    );
    expect(authenticateCredentials("client@acme.com", "client-pw", findUser, decoy)?.role).toBe(
      "client",
    );
  });

  it("returns null for a wrong password", () => {
    expect(authenticateCredentials("team@wahha.design", "nope", findUser, decoy)).toBeNull();
  });

  it("returns null for an unknown email without throwing (decoy path)", () => {
    expect(authenticateCredentials("ghost@acme.com", "whatever", findUser, decoy)).toBeNull();
  });

  it("returns null for non-string inputs", () => {
    expect(authenticateCredentials(undefined, "x", findUser, decoy)).toBeNull();
    expect(authenticateCredentials("team@wahha.design", undefined, findUser, decoy)).toBeNull();
  });
});

describe("resolveSessionUser (identity/role re-derived from config)", () => {
  const secret = "unit-test-secret";
  const users = [
    { email: "team@wahha.design", name: "Team", hash: "scrypt$16384$8$1$a$b", role: "team" },
    { email: "client@acme.com", name: "Client", hash: "scrypt$16384$8$1$a$b", role: "client" },
  ];
  const findUser = (e) => users.find((u) => u.email === e);
  const codec = createSessionCodec({ secret, ttlMs: 100000, now: () => 1000 });

  it("re-derives role from USERS for a legacy pre-role cookie (invariant #2)", () => {
    const sign = (d) => crypto.createHmac("sha256", secret).update(d).digest("base64url");
    const payload = Buffer.from(JSON.stringify({ email: "client@acme.com", exp: 50000 })).toString(
      "base64url",
    );
    const legacy = `${payload}.${sign(payload)}`;
    expect(resolveSessionUser(legacy, codec.verifySessionToken, findUser)).toMatchObject({
      role: "client",
    });
  });

  it("ignores a forged role in the cookie — config wins (invariant #4)", () => {
    const forged = codec.createSessionToken({ email: "client@acme.com", role: "team" });
    expect(resolveSessionUser(forged, codec.verifySessionToken, findUser)?.role).toBe("client");
  });

  it("returns null for an unknown email or a tampered token", () => {
    const ghost = codec.createSessionToken({ email: "ghost@acme.com", role: "team" });
    expect(resolveSessionUser(ghost, codec.verifySessionToken, findUser)).toBeNull();
    const good = codec.createSessionToken({ email: "team@wahha.design", role: "team" });
    expect(resolveSessionUser(`${good}tamper`, codec.verifySessionToken, findUser)).toBeNull();
  });
});

describe("createSessionRevocations (one sign-out for Command Center and the Atelier)", () => {
  const user = { email: "ai@weddingindustryads.com", name: "WIA", role: "team" };
  const findUser = (email) => (email === user.email ? user : undefined);

  it("refuses a signed-out token everywhere it is presented, until it would have expired", () => {
    let clock = 1_000;
    const codec = createSessionCodec({ secret: "s", ttlMs: 10_000, now: () => clock });
    const revocations = createSessionRevocations({ now: () => clock });
    const token = codec.createSessionToken(user);
    expect(resolveSessionUser(token, codec.verifySessionToken, findUser, revocations.isRevoked)).toBe(user);
    expect(revocations.revoke(token, codec.verifySessionToken(token).exp)).toBe(true);
    expect(resolveSessionUser(token, codec.verifySessionToken, findUser, revocations.isRevoked)).toBeNull();
    // Another session of the same account is untouched.
    clock += 1;
    const other = codec.createSessionToken(user);
    expect(resolveSessionUser(other, codec.verifySessionToken, findUser, revocations.isRevoked)).toBe(user);
    // Past the token's own expiry the entry is dropped (the token is refused by its expiry anyway).
    clock += 20_000;
    expect(revocations.isRevoked(token)).toBe(false);
    revocations.revoke(other, clock + 1);
    expect(revocations.size()).toBe(1);
  });

  it("ignores missing tokens and stays within its capacity, oldest first", () => {
    const revocations = createSessionRevocations({ now: () => 0, capacity: 2 });
    expect(revocations.revoke(undefined)).toBe(false);
    expect(revocations.revoke("")).toBe(false);
    expect(revocations.isRevoked(undefined)).toBe(false);
    revocations.revoke("a", 10);
    revocations.revoke("b", 10);
    revocations.revoke("c", 10);
    expect([revocations.isRevoked("a"), revocations.isRevoked("b"), revocations.isRevoked("c")]).toEqual([false, true, true]);
  });

  it("keeps resolveSessionUser's old three-argument behaviour", () => {
    const codec = createSessionCodec({ secret: "s", ttlMs: 10_000 });
    expect(resolveSessionUser(codec.createSessionToken(user), codec.verifySessionToken, findUser)).toBe(user);
  });
});
