// 6.X2: the role matrix through the Node server, over every write it relays. The list is derived, not typed: every write the
// backend declares (backend/openapi.json) that the allowlist forwards, with each placeholder filled the way the allowlist
// accepts it; a check proves every entry of the allowlist's write table is reached by at least one of them, so a write added
// to the allowlist is in the matrix without anyone listing it here.
//
// What the Node server decides, and this file proves for each write: no session is a 401, a client-role session is a 403, a
// write from another site is a 403, and none of them reaches the backend; a team session is forwarded with the email Command
// Center verified (and the server's own secret), whatever identity the browser sent. Which team member may do what (viewer,
// editor, approver) is the backend's decision from that email, proved there: backend/backend_pipeline/tests/test_roles.py
// (every mutating route resolves roles by email; viewer, editor and approver outcomes), test_gate_one_roles.py (Gate 1) and
// test_settings_db.py (settings: editors read, approvers write); test_users_db.py has dismissing an alert (6.B4: an editor or
// approver; a viewer reads the alerts), which the app offers to an editor or approver only (AlertsAndCosts.tsx mayDismiss).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { createApp } from './app.mjs';
import { SETTABLE, WRITE_ROUTES, routeAllowed } from './allowlist.mjs';

const VERIFIED = 'verified.team@example.test';

/** Concrete paths for a backend route: an identifier for each placeholder, a valid value where the allowlist wants one. */
function concrete(route) {
  const path = route.replace(/^\/storage/, '').replace('{index}', '1').replace('{provider}', 'slack').replace('/pieces/{key}', '/pieces/email');
  if (path === '/settings/{key}') return SETTABLE.map(key => `/settings/${key}`);
  return [path.replace(/\{\w+\}/g, 'x1')];
}

const api = JSON.parse(readFileSync(new URL('../../backend/openapi.json', import.meta.url), 'utf8'));
const WRITES = Object.entries(api.paths).filter(([route]) => route.startsWith('/storage/'))
  .flatMap(([route, operations]) => Object.keys(operations).filter(verb => verb !== 'get')
    .flatMap(verb => concrete(route).map(path => [verb.toUpperCase(), path])))
  .filter(([method, path]) => routeAllowed(method, path));

/** The top-level alternatives of one allowlist entry ("a|b(?:c|d)" is "a" and "b(?:c|d)"). */
function alternatives(entry) {
  const parts = [];
  let depth = 0, start = 0;
  for (let i = 0; i < entry.length; i++) {
    const c = entry[i];
    if (c === '\\') { i++; continue; }
    if (c === '(') depth++;
    else if (c === ')') depth--;
    else if (c === '|' && depth === 0) { parts.push(entry.slice(start, i)); start = i + 1; }
  }
  return [...parts, entry.slice(start)];
}

test('6.X2: the matrix covers every write the allowlist forwards', () => {
  assert.ok(WRITES.length > 40, `the matrix has ${WRITES.length} writes; the reading must be broken`);
  const uncovered = [];
  for (const [method, entries] of Object.entries(WRITE_ROUTES)) {
    for (const entry of entries) for (const alternative of alternatives(entry)) {
      const pattern = new RegExp(`^/(?:${alternative})$`);
      if (!WRITES.some(([m, path]) => m === method && pattern.test(path))) uncovered.push(`${method} ${alternative}`);
    }
  }
  assert.deepEqual(uncovered, [], 'an allowlisted write no backend route matches: remove it from server/allowlist.mjs, or the backend lost a route');
  assert.ok(WRITES.some(([method]) => method === 'PATCH') && WRITES.some(([method]) => method === 'PUT'), 'every write method is in the matrix');
  // 6.F5's write, an editor's or approver's at the backend, is in the matrix like every other.
  assert.ok(WRITES.some(([method, path]) => method === 'POST' && path === '/alerts/x1/dismiss'), 'dismissing an alert is in the matrix');
});

test('6.X2: every write: no session 401, a client session 403, another site 403, a team session forwarded with its verified email', async t => {
  const calls = [];
  let role = 'team';
  const fetcher = async (url, init) => {
    calls.push({ url, init });
    if (url.endsWith('/api/auth/session')) return Response.json({ user: { id: 'u1', email: VERIFIED, role } });
    return Response.json({ ok: true });
  };
  const server = http.createServer(createApp({ authOrigin: 'http://auth.example.test', backendOrigin: 'http://backend.example.test', backendSecret: 'server-secret', production: false, fetcher }));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const base = `http://127.0.0.1:${server.address().port}/api/atelier`;
  // A browser that tries to name its own identity and credentials: none of these may reach the backend.
  const spoofed = { cookie: 'wahha_session=t', 'content-type': 'application/json', 'x-atelier-email': 'approver@example.test', 'x-atelier-actor': 'approver@example.test', authorization: 'Bearer browser' };
  const send = (method, path, headers) => fetch(base + path, { method, headers, body: '{}' });
  const storage = () => calls.filter(call => call.url.startsWith('http://backend.example.test/')).length;
  const wrong = [];
  for (const [method, path] of WRITES) {
    const before = storage();
    role = 'team';
    const anonymous = (await send(method, path, { 'content-type': 'application/json' })).status;
    const foreign = (await send(method, path, { ...spoofed, 'sec-fetch-site': 'cross-site' })).status;
    role = 'client';
    const client = (await send(method, path, spoofed)).status;
    if (anonymous !== 401 || foreign !== 403 || client !== 403 || storage() !== before) {
      wrong.push(`${method} ${path}: no session ${anonymous}, another site ${foreign}, client ${client}, reached the backend ${storage() - before} times`);
      continue;
    }
    role = 'team';
    const team = (await send(method, path, spoofed)).status;
    const forwarded = calls.at(-1);
    const headers = forwarded.init.headers;
    if (team !== 200 || forwarded.url !== `http://backend.example.test/storage${path}` || forwarded.init.method !== method
      || headers['x-atelier-email'] !== VERIFIED || headers['x-atelier-actor'] !== VERIFIED || headers.authorization !== 'Bearer server-secret' || headers.cookie !== undefined) {
      wrong.push(`${method} ${path}: team ${team}, forwarded to ${forwarded.url} as ${headers?.['x-atelier-email']}`);
    }
  }
  assert.deepEqual(wrong, []);
});
