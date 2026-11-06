import { test } from "vitest";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import http from "node:http";
import express from "express";
import { atelierOrigin, createAtelierSsoRouter } from "./atelier-sso.mjs";
import { createSessionCodec, createSessionRevocations, resolveSessionUser } from "./auth-core.mjs";

const destination = "https://atelier.example.invalid/workspace?source=command-center";
const callback = "https://atelier.example.invalid/api/auth/sso/callback";
const state = "s".repeat(43);
const verifier = "v".repeat(64);
const challenge = crypto.createHash("sha256").update(verifier).digest("base64url");

async function fixture(t, options = {}) {
  let clock = 100_000;
  let enabled = true;
  const user = { email: "whitney@example.invalid", name: "Whitney Fixture", role: "team" };
  const codec = createSessionCodec({ secret: "test-fixture-only", ttlMs: 3600_000, now: () => clock });
  const token = codec.createSessionToken(user);
  const readToken = req => decodeURIComponent((req.headers.cookie || "").split(";").map(p => p.trim()).find(p => p.startsWith("wahha_session="))?.slice(14) || "");
  const isRevoked = options.revocations?.isRevoked ?? (() => false);
  const resolveUser = req => resolveSessionUser(readToken(req), codec.verifySessionToken, email => enabled && email === user.email ? user : null, isRevoked);
  const app = express();
  app.use("/api/auth/content-atelier", createAtelierSsoRouter({ atelierUrl: destination, nodeEnv: "production", resolveUser, readToken, sessionExpiry: value => codec.verifySessionToken(value)?.exp, now: () => clock, ...options, revocations: undefined }));
  const server = http.createServer(app);
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  t.onTestFinished(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const base = `http://127.0.0.1:${server.address().port}/api/auth/content-atelier`;
  const request = (route, options = {}) => fetch(base + route, { redirect: "manual", ...options });
  const authorize = (overrides = {}, withSession = true) => request("/authorize?" + new URLSearchParams({ redirect_uri: callback, state, code_challenge: challenge, code_challenge_method: "S256", ...overrides }), { headers: withSession ? { cookie: `wahha_session=${token}` } : {} });
  const exchange = (code, overrides = {}) => request("/exchange", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ code, redirect_uri: callback, code_verifier: verifier, ...overrides }) });
  return { user, token, request, authorize, exchange, advance: milliseconds => { clock += milliseconds; }, revoke: () => { enabled = false; } };
}

test("launch uses the configured receiver and requires a real signed-in session", async t => {
  const f = await fixture(t);
  // Signed out: Command Center's sign-in, returning to the launch once signed in.
  assert.equal((await f.request("/launch")).headers.get("location"), "/login?next=%2Fapi%2Fauth%2Fcontent-atelier%2Flaunch");
  const response = await f.request("/launch", { headers: { cookie: `wahha_session=${f.token}` } });
  const url = new URL(response.headers.get("location"));
  assert.equal(url.origin, "https://atelier.example.invalid");
  assert.equal(url.pathname, "/api/auth/sso/start");
  assert.equal(url.searchParams.get("returnTo"), "/workspace?source=command-center");
  assert.ok(!url.href.includes(f.token));
});

test("handoff transfers the current identity only over the PKCE backchannel, once", async t => {
  const f = await fixture(t);
  const response = await f.authorize();
  assert.equal(response.status, 302);
  assert.equal(response.headers.get("referrer-policy"), "no-referrer");
  const url = new URL(response.headers.get("location"));
  assert.equal(url.origin + url.pathname, callback);
  assert.equal(url.searchParams.get("state"), state);
  assert.ok(!url.href.includes(f.token));
  const code = url.searchParams.get("code");
  const exchanged = await f.exchange(code);
  assert.equal(exchanged.status, 200);
  assert.deepEqual(await exchanged.json(), { user: f.user, sessionToken: f.token, expiresIn: 3600 });
  assert.equal((await f.exchange(code)).status, 401);
});

test("callback allowlist, PKCE S256 and session checks reject forged authorization", async t => {
  const f = await fixture(t);
  for (const redirect_uri of ["https://attacker.example.invalid/api/auth/sso/callback", "https://atelier.example.invalid/other", callback + "?evil=1", "https://atelier.example.invalid.attacker.invalid/api/auth/sso/callback"]) {
    assert.equal((await f.authorize({ redirect_uri })).status, 400);
  }
  assert.equal((await f.authorize({ state: "short" })).status, 400);
  assert.equal((await f.authorize({ code_challenge_method: "plain" })).status, 400);
  assert.equal((await f.authorize({ code_challenge: "invalid" })).status, 400);
  const signIn = new URL((await f.authorize({}, false)).headers.get("location"), "https://cc.example.invalid");
  assert.equal(signIn.pathname, "/login");
  // The whole authorize request comes back after sign-in, so the hand-off finishes without a second click.
  const resumed = new URL(signIn.searchParams.get("next"), "https://cc.example.invalid");
  assert.equal(resumed.pathname, "/api/auth/content-atelier/authorize");
  assert.equal(resumed.searchParams.get("redirect_uri"), callback);
  assert.equal(resumed.searchParams.get("state"), state);
});

test("a signed-out session cannot start a hand-off", async t => {
  const revocations = createSessionRevocations();
  const f = await fixture(t, { revocations });
  revocations.revoke(f.token);
  assert.equal(new URL((await f.authorize()).headers.get("location"), "https://cc.example.invalid").pathname, "/login");
});

test("atelierOrigin accepts only an allowed public Atelier URL", () => {
  assert.equal(atelierOrigin("https://content-atelier.up.railway.app/workspace", "production"), "https://content-atelier.up.railway.app");
  assert.equal(atelierOrigin("http://localhost:18080", "development"), "http://localhost:18080");
  assert.equal(atelierOrigin("http://localhost:18080", "production"), null);
  assert.equal(atelierOrigin("", "production"), null);
  assert.equal(atelierOrigin(undefined, "production"), null);
});

test("stolen codes cannot be redeemed without the receiver verifier and callback", async t => {
  const f = await fixture(t);
  const code = new URL((await f.authorize()).headers.get("location")).searchParams.get("code");
  assert.equal((await f.exchange(code, { code_verifier: "x".repeat(64) })).status, 401);
  assert.equal((await f.exchange(code, { redirect_uri: "https://attacker.example.invalid" })).status, 400);
  assert.equal((await f.exchange(code, { code_verifier: "bad" })).status, 400);
  assert.equal((await f.exchange(code)).status, 200);
});

test("expiration and account revocation invalidate an already-issued code", async t => {
  const f = await fixture(t);
  const code = new URL((await f.authorize()).headers.get("location")).searchParams.get("code");
  f.advance(60_001);
  assert.equal((await f.exchange(code)).status, 401);
  const next = new URL((await f.authorize()).headers.get("location")).searchParams.get("code");
  f.revoke();
  assert.equal((await f.exchange(next)).status, 401);
});

test("unconfigured/insecure destinations fail closed; pending-code storage is bounded", async t => {
  const invalid = await fixture(t, { atelierUrl: "http://atelier.example.invalid" });
  assert.equal((await invalid.request("/launch")).status, 503);
  const f = await fixture(t, { capacity: 1 });
  assert.equal((await f.authorize()).status, 302);
  assert.equal((await f.authorize()).status, 503);
  f.advance(60_001);
  assert.equal((await f.authorize()).status, 302);
});
