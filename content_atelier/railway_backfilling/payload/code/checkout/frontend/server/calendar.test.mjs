import { test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { createApp } from "./app.mjs";

test("production/calendar proxy authenticates, bounds routes and preserves server actor", async (t) => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith("/api/auth/session"))
      return Response.json({
        user: { id: "scheduler", email: "team@example.invalid", role: "team" },
      });
    return Response.json({ items: [], entries: [] });
  };
  const app = createApp({
    authOrigin: "http://auth.invalid",
    backendOrigin: "http://backend.invalid",
    backendSecret: "fixture",
    production: false,
    fetcher,
  });
  const server = http.createServer(app);
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  t.after(
    () =>
      new Promise((r) => {
        server.closeAllConnections();
        server.close(r);
      }),
  );
  const base = "http://127.0.0.1:" + server.address().port + "/api/atelier";
  const headers = {
    cookie: "wahha_session=fixture",
    "content-type": "application/json",
    "x-atelier-actor": "forged",
  };
  assert.equal((await fetch(base + "/calendar/config")).status, 401);
  const range =
    "?from=2026-10-01T00%3A00%3A00Z&to=2026-11-01T00%3A00%3A00Z&cursor=0";
  assert.equal(
    (await fetch(base + "/calendar" + range, { headers })).status,
    200,
  );
  assert.match(calls.at(-1).url, /backend.invalid\/storage\/calendar\?/);
  assert.equal(calls.at(-1).options.headers["x-atelier-actor"], "scheduler");
  for (const path of [
    "/packs?limit=20&offset=0",
    "/packs/pack_one",
    "/packs/pack_one/production",
    "/calendar/config",
  ]) {
    assert.equal((await fetch(base + path, { headers })).status, 200, path);
  }
  for (const path of [
    "/packs/pack_one/schedule",
    "/packs/pack_one/decision",
    "/briefs/brief_one/pack",
    "/calendar/entry_one/cancel",
  ]) {
    assert.equal(
      (await fetch(base + path, { method: "POST", headers, body: "{}" }))
        .status,
      200,
      path,
    );
  }
  assert.equal(
    (
      await fetch(base + "/calendar/entry_one", {
        method: "PATCH",
        headers,
        body: "{}",
      })
    ).status,
    200,
  );
  for (const path of [
    "/calendar?from=bad&to=bad",
    "/calendar" + range + "&extra=1",
    "/calendar" + range + "&cursor=1",
    "/packs?limit=0",
  ]) {
    assert.equal((await fetch(base + path, { headers })).status, 404, path);
  }
  assert.equal(
    (
      await fetch(base + "/packs/pack_one/schedule", {
        method: "POST",
        headers: { ...headers, origin: "https://foreign.invalid" },
        body: "{}",
      })
    ).status,
    403,
  );
});
