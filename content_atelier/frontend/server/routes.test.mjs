import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { createApp } from './app.mjs';

// Routes added for Phases S and E. Each must be allowlisted, carry only the verified
// identity and reach the backend unchanged (plan section 0, "Working an item").
async function proxy(t, role = 'team') {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/api/auth/session')) return Response.json({ user: { email: 'whitney@example.invalid', role } });
    return Response.json({ ok: true }, { status: options.method === 'POST' ? 202 : 200 });
  };
  const app = createApp({ authOrigin: 'http://auth.example.invalid', backendOrigin: 'http://storage.example.invalid', backendSecret: 'fixture-secret', production: false, fetcher });
  const server = http.createServer(app);
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const send = (path, method = 'GET', body) => fetch(`${origin}/api/atelier${path}`, {
    method, headers: { cookie: 'wahha_session=fixture', 'content-type': 'application/json', origin, 'x-atelier-email': 'spoof@example.invalid' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  return { calls, send, origin };
}

test('S.B13: the brief retry route is allowlisted and forwards the verified email', async t => {
  const { calls, send } = await proxy(t);
  const response = await send('/angles/angle_one/brief/retry', 'POST', {});
  assert.equal(response.status, 202);
  const forwarded = calls.at(-1);
  assert.equal(forwarded.url, 'http://storage.example.invalid/storage/angles/angle_one/brief/retry');
  assert.equal(forwarded.options.headers['x-atelier-email'], 'whitney@example.invalid');
  assert.equal((await send('/angles/angle_one/brief/retry/extra', 'POST', {})).status, 404);
  assert.equal((await send('/angles/angle_one/brief/retry', 'GET')).status, 404);
});

test('S.B11: the flags route is allowlisted for team sessions', async t => {
  const { calls, send } = await proxy(t);
  assert.equal((await send('/flags')).status, 200);
  assert.equal(calls.at(-1).url, 'http://storage.example.invalid/storage/flags');
  assert.equal((await send('/flags', 'POST', {})).status, 404);
});

test('E.B20: the considered-idea routes are allowlisted and forward the verified email', async t => {
  const { calls, send } = await proxy(t);
  for (const action of ['revive', 'decision']) {
    assert.equal((await send(`/weeks/week_one/considered/2/${action}`, 'POST', {})).status, 202);
    const forwarded = calls.at(-1);
    assert.equal(forwarded.url, `http://storage.example.invalid/storage/weeks/week_one/considered/2/${action}`);
    assert.equal(forwarded.options.headers['x-atelier-email'], 'whitney@example.invalid');
  }
  assert.equal((await send('/weeks/week_one/considered/two/revive', 'POST', {})).status, 404);
  assert.equal((await send('/weeks/week_one/considered/2/revive', 'GET')).status, 404);
  assert.equal((await send('/weeks/week_one/considered/2/delete', 'POST', {})).status, 404);
});

test('E.B20: the card disposition route reaches the backend', async t => {
  const { calls, send } = await proxy(t);
  const body = { expected_hash: 'h', disposition: 'skip', reason_code: 'positioning' };
  assert.equal((await send('/angles/angle_one/decision', 'POST', body)).status, 202);
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), body);
});

test('E.F3: the seed routes are allowlisted, with a bounded status filter', async t => {
  const { calls, send } = await proxy(t);
  assert.equal((await send('/seeds')).status, 200);
  assert.equal((await send('/seeds?status=open')).status, 200);
  assert.equal(calls.at(-1).url, 'http://storage.example.invalid/storage/seeds?status=open');
  assert.equal((await send('/seeds?status=deleted')).status, 404);
  assert.equal((await send('/seeds?status=open&status=used')).status, 404);
  const seed = { kind: 'thought', text: 'Couples book faster when the first reply names a date.' };
  assert.equal((await send('/seeds', 'POST', seed)).status, 202);
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), seed);
  assert.equal(calls.at(-1).options.headers['x-atelier-email'], 'whitney@example.invalid');
  assert.equal((await send('/seeds/seed_one/withdraw', 'POST', {})).status, 202);
  assert.equal((await send('/seeds/seed_one', 'PATCH', {})).status, 404);
});

test('E.F4: the brief CTA confirmation route is allowlisted', async t => {
  const { calls, send } = await proxy(t);
  const body = { expected_hash: 'h', choice: 'no_explicit_ask' };
  assert.equal((await send('/briefs/brief_one/cta', 'POST', body)).status, 202);
  assert.equal(calls.at(-1).url, 'http://storage.example.invalid/storage/briefs/brief_one/cta');
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), body);
  assert.equal((await send('/briefs/brief_one/cta', 'GET')).status, 404);
});

test('E.B23: the hand-off view of a brief is allowlisted for reading only, with the verified email', async t => {
  const { calls, send } = await proxy(t);
  assert.equal((await send('/briefs/brief_one/handoff')).status, 200);
  assert.equal(calls.at(-1).url, 'http://storage.example.invalid/storage/briefs/brief_one/handoff');
  assert.equal(calls.at(-1).options.headers['x-atelier-email'], 'whitney@example.invalid', 'never the browser-supplied email');
  for (const method of ['POST', 'PATCH']) assert.equal((await send('/briefs/brief_one/handoff', method, {})).status, 404, method);
  assert.equal((await send('/briefs/brief_one/handoff/extra')).status, 404);
});

test('L.B9: the published-final routes of a brief are allowlisted and forward the verified email', async t => {
  const { calls, send } = await proxy(t);
  const body = { channel: 'email', piece: 1, title: 'The question', text: 'Final copy.', published_on: '2026-10-18', url: null, metrics: [] };
  assert.equal((await send('/briefs/brief_one/published', 'POST', body)).status, 202);
  assert.equal(calls.at(-1).url, 'http://storage.example.invalid/storage/briefs/brief_one/published');
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), body);
  assert.equal(calls.at(-1).options.headers['x-atelier-email'], 'whitney@example.invalid', 'never the browser-supplied email');
  assert.equal((await send('/briefs/brief_one/published')).status, 200);
  assert.equal((await send('/briefs/brief_one/published', 'PATCH', body)).status, 404);
});

// Raw request: fetch() normalises "..", so traversal attempts are sent byte for byte.
function raw(origin, path, method = 'GET') {
  return new Promise((resolve, reject) => {
    const url = new URL(origin);
    const request = http.request({ host: url.hostname, port: url.port, path: `/api/atelier${path}`, method,
      headers: { cookie: 'wahha_session=fixture', 'content-type': 'application/json', origin } }, response => { response.resume(); resolve(response.statusCode); });
    request.on('error', reject);
    request.end(method === 'GET' ? undefined : '{}');
  });
}

const CONTEXT_GETS = ['/context/summary', '/context/kinds', '/context/queue', '/context/items', '/context/published', '/context/versions',
  '/context/warnings', '/context/items/item_0123456789abcdef0123456789abcdef/history',
  '/context/versions/wia-kb-2026-10-20.c-1a2b3c4d/diff'];
const CONTEXT_POSTS = ['/context/batch', '/context/items', '/context/published', '/context/published/confirm', '/context/published/import',
  '/context/versions', '/context/items/item_0123456789abcdef0123456789abcdef/decision',
  '/context/published/published_ab12/performance', '/context/published/published_ab12/link',
  '/context/versions/wia-kb-2026-10-20.c-1a2b3c4d/approve', '/context/versions/wia-kb-2026-10-20.c-1a2b3c4d/benchmark'];

test('L.F1 to L.F3: every context route is allowlisted and forwards the verified email, not the spoofed header', async t => {
  const { calls, send } = await proxy(t);
  for (const path of CONTEXT_GETS) {
    assert.equal((await send(path)).status, 200, path);
    assert.equal(calls.at(-1).url, `http://storage.example.invalid/storage${path}`, path);
    assert.equal(calls.at(-1).options.headers['x-atelier-email'], 'whitney@example.invalid', path);
  }
  for (const path of CONTEXT_POSTS) {
    const body = { reason: 'Checked', expected_hash: 'hash_0123456789' };
    assert.equal((await send(path, 'POST', body)).status, 202, path);
    const forwarded = calls.at(-1);
    assert.equal(forwarded.url, `http://storage.example.invalid/storage${path}`, path);
    assert.equal(forwarded.options.method, 'POST');
    assert.equal(forwarded.options.headers['x-atelier-email'], 'whitney@example.invalid', path);
    assert.deepEqual(JSON.parse(forwarded.options.body), body, path);
  }
});

test('L.F1 to L.F3: wrong methods and extra path segments are not forwarded', async t => {
  const { calls, send } = await proxy(t);
  const before = calls.length;
  for (const path of ['/context/summary', '/context/kinds', '/context/queue', '/context/warnings', '/context/items/item_one/history', '/context/versions/v1.c-1/diff']) {
    assert.equal((await send(path, 'POST', {})).status, 404, `POST ${path}`);
  }
  for (const path of ['/context/batch', '/context/published/confirm', '/context/published/import', '/context/items/item_one/decision',
    '/context/published/published_ab/link', '/context/versions/v1/approve', '/context/versions/v1/benchmark']) {
    assert.equal((await send(path)).status, 404, `GET ${path}`);
  }
  for (const path of ['/context/items/item_one/decision', '/context/batch']) assert.equal((await send(path, 'PATCH', {})).status, 404, `PATCH ${path}`);
  // The mining pass has no screen (it runs from the scheduler or the command line), so neither its read nor its run is relayed.
  for (const method of ['GET', 'POST']) assert.equal((await send('/context/mining', method, method === 'GET' ? undefined : {})).status, 404, `${method} /context/mining`);
  for (const path of ['/context/summary/extra', '/context/items/item_one/history/extra', '/context/versions/v1/diff/extra', '/context/unknown', '/context', '/context/']) {
    assert.equal((await send(path)).status, 404, `GET ${path}`);
  }
  for (const path of ['/context/items/item_one/decision/extra', '/context/published/published_ab/performance/extra', '/context/versions/v1/approve/extra',
    '/context/items/item%20one/decision', '/context/batch/extra', '/context/published/confirm/extra']) {
    assert.equal((await send(path, 'POST', {})).status, 404, `POST ${path}`);
  }
  assert.equal(calls.length, before, 'nothing reached the backend or the session check');
});

test('L.F1 to L.F3: a client-role session cannot reach the context routes', async t => {
  const { calls, send } = await proxy(t, 'client');
  assert.equal((await send('/context/summary')).status, 403);
  // A client session's 403 on each write is in the role matrix (roles.test.mjs, 6.X2).
  assert.ok(calls.every(c => c.url.endsWith('/api/auth/session')), 'no client request reached storage');
});

test('L.F3: a version with dots is accepted; ".." traversal is not', async t => {
  const { calls, send, origin } = await proxy(t);
  assert.equal((await send('/context/versions/wia-kb-2026-10-20.c-1a2b3c4d/diff?against=wia-kb-2026-10-14')).status, 200);
  assert.equal(calls.at(-1).url, 'http://storage.example.invalid/storage/context/versions/wia-kb-2026-10-20.c-1a2b3c4d/diff?against=wia-kb-2026-10-14');
  const before = calls.length;
  for (const path of ['/context/versions/../approve', '/context/versions/../../weeks/w/runs', '/context/versions/a..b/approve', '/context/versions/./approve',
    '/context/versions/.hidden/approve', '/context/versions/%2e%2e/approve', '/context/versions/v1/../../batch']) {
    assert.equal(await raw(origin, path, 'POST'), 404, path);
  }
  assert.equal(await raw(origin, '/context/versions/../diff'), 404);
  assert.equal(await raw(origin, '/context/versions/v1/diff?against=..'), 404);
  assert.equal(await raw(origin, '/context/versions/v1/diff?against=a..b'), 404);
  assert.equal(calls.length, before, 'no traversal reached the backend');
});

test('L.F1 and L.F2: context query parameters pass strict validation', async t => {
  const { calls, send } = await proxy(t);
  for (const path of ['/context/queue?kind=price&status=candidate&limit=50&offset=0', '/context/queue?status=confirmed&limit=200',
    '/context/items?kind=roster_member&on=2026-10-18', '/context/items?on=2026-02-28', '/context/published?status=unconfirmed&limit=500&offset=100',
    '/context/published?status=confirmed']) {
    assert.equal((await send(path)).status, 200, path);
    assert.equal(calls.at(-1).url, `http://storage.example.invalid/storage${path}`, path);
  }
  const before = calls.length;
  for (const path of ['/context/queue?kind=secrets', '/context/queue?status=pending', '/context/queue?limit=201', '/context/queue?limit=0',
    '/context/queue?offset=-1', '/context/queue?kind=price&kind=rule', '/context/queue?on=2026-10-18', '/context/items?on=2026-13-01',
    '/context/items?on=2026-02-30', '/context/items?on=18-10-2026', '/context/items?status=candidate', '/context/published?status=candidate',
    '/context/published?limit=501', '/context/summary?kind=price', '/context/versions?on=2026-10-18', '/context/warnings?x=1',
    '/context/versions/v1/diff?against=v0&against=v2', '/context/versions/v1/diff?kind=price']) {
    assert.equal((await send(path)).status, 404, path);
  }
  assert.equal((await send('/context/items?kind=price', 'POST', {})).status, 404, 'query strings stay GET-only');
  assert.equal(calls.length, before, 'no invalid query reached the backend');
});

// Routes the review screens use (E.F1, E.F2, E.F4, S.F4) and their allowed methods (plan section 0).
test('E.F1, E.F2, E.F4, S.F4: the review screens reach their routes, with the verified email', async t => {
  const { calls, send } = await proxy(t);
  const reach = [
    ['/weeks/week_one', 'GET'], ['/moments/moment_one', 'GET'], ['/angles/angle_one/research', 'GET'],
    ['/briefs/brief_one', 'GET'], ['/briefs/brief_one/versions', 'GET'], ['/jobs/job_one/retry', 'POST'],
    ['/briefs/brief_one', 'PATCH'], ['/briefs/brief_one/answers', 'POST'], ['/briefs/brief_one/decision', 'POST'],
    ['/briefs/brief_one/cta', 'POST'], ['/briefs/brief_one/clearance', 'POST'], ['/briefs/brief_one/review', 'POST'],
  ];
  for (const [path, method] of reach) {
    const response = await send(path, method, method === 'GET' ? undefined : { expected_hash: 'h' });
    assert.ok(response.status < 300, `${method} ${path}: ${response.status}`);
    const forwarded = calls.at(-1);
    assert.equal(forwarded.url, `http://storage.example.invalid/storage${path}`);
    assert.equal(forwarded.options.method, method);
    assert.equal(forwarded.options.headers['x-atelier-email'], 'whitney@example.invalid', 'never the browser-supplied email');
  }
  for (const [path, method] of [['/briefs/brief_one/decision', 'GET'], ['/weeks/week_one', 'POST'], ['/jobs/job_one/retry', 'GET'],
    ['/briefs/brief_one/clearance/extra', 'POST'], ['/moments/moment_one', 'PATCH']]) {
    assert.equal((await send(path, method, method === 'GET' ? undefined : {})).status, 404, `${method} ${path}`);
  }
});

// 0.F1: GET /me through the Node server, and the actor is always the verified email (R37).
async function sessionProxy(t, user) {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/api/auth/session')) return Response.json({ user });
    if (url.endsWith('/storage/me')) return Response.json({ email: user.email, role: 'approver', roles: ['viewer', 'editor', 'approver'], can: { decide: true } });
    return Response.json({ ok: true }, { status: options.method === 'POST' ? 202 : 200 });
  };
  const app = createApp({ authOrigin: 'http://auth.example.invalid', backendOrigin: 'http://storage.example.invalid', backendSecret: 'fixture-secret', production: false, fetcher });
  const server = http.createServer(app);
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const send = (path, method = 'GET', body, extra = {}) => fetch(`${origin}/api/atelier${path}`, {
    method, headers: { cookie: 'wahha_session=fixture', 'content-type': 'application/json', origin, ...extra },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  return { calls, send, origin };
}

test('0.F1: GET /me returns the signed-in user\'s roles through the Node server', async t => {
  const { calls, send } = await sessionProxy(t, { id: 'cc-user-77', email: 'whitney@example.invalid', role: 'team' });
  const response = await send('/me');
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.email, 'whitney@example.invalid');
  assert.deepEqual(body.roles, ['viewer', 'editor', 'approver']);
  const forwarded = calls.at(-1);
  assert.equal(forwarded.url, 'http://storage.example.invalid/storage/me');
  assert.equal(forwarded.options.method, 'GET');
  assert.equal(forwarded.options.headers.authorization, 'Bearer fixture-secret');
  // The browser says nothing about who it is: the server says, from the verified session.
  const spoofed = await send('/me', 'GET', undefined, { 'x-atelier-email': 'admin@example.invalid', 'x-atelier-actor': 'admin@example.invalid' });
  assert.equal(spoofed.status, 200);
  assert.equal(calls.at(-1).options.headers['x-atelier-email'], 'whitney@example.invalid');
  assert.equal(calls.at(-1).options.headers['x-atelier-actor'], 'whitney@example.invalid');
  // Read-only and unparameterised.
  for (const [path, method] of [['/me', 'POST'], ['/me', 'PATCH'], ['/me/roles', 'GET'], ['/me?email=admin@example.invalid', 'GET']]) {
    assert.equal((await send(path, method, method === 'GET' ? undefined : {})).status, 404, `${method} ${path}`);
  }
});

test('0.F1: /me needs a session, and a client session reaches nothing', async t => {
  const { calls, send, origin } = await sessionProxy(t, { id: 'c1', email: 'client@example.invalid', role: 'client' });
  assert.equal((await send('/me')).status, 403);
  assert.ok(calls.every(c => c.url.endsWith('/api/auth/session')), 'no client request reached storage');
  assert.equal((await fetch(`${origin}/api/atelier/me`)).status, 401);
});

test('0.F1, R37: no relayed request carries the session user id as the actor', async t => {
  // The id differs from the email on purpose; it must appear in no header, path or body the relay sends.
  const user = { id: 'cc-user-77', email: 'whitney@example.invalid', role: 'team' };
  const { calls, send } = await sessionProxy(t, user);
  const requests = [
    ['/me'], ['/flags'], ['/weeks'], ['/weeks/week_one'], ['/briefs?status=pending&limit=20'], ['/seeds'],
    ['/angles/angle_one/decision', 'POST', {}], ['/angles/angle_one', 'PATCH', {}],
    ['/briefs/brief_one/decision', 'POST', {}], ['/weeks/week_one/considered/1/revive', 'POST', {}],
    ['/intake/overview'], ['/intake/refresh', 'POST', {}], ['/calendar/config'], ['/packs/pack_one/decision', 'POST', {}],
    ['/context/queue'], ['/context/items/item_one/decision', 'POST', {}], ['/search', 'POST', {}],
  ];
  for (const [path, method = 'GET', body] of requests) {
    const before = calls.length;
    const response = await send(path, method, body);
    assert.ok(response.status < 400, `${method} ${path} reached the backend (${response.status})`);
    assert.equal(calls.length, before + 2, `${method} ${path}: one session check and one relay`);
  }
  const relayed = calls.filter(c => !c.url.endsWith('/api/auth/session'));
  assert.equal(relayed.length, requests.length);
  for (const { url, options } of relayed) {
    assert.equal(options.headers['x-atelier-actor'], user.email, url);
    assert.equal(options.headers['x-atelier-email'], user.email, url);
    for (const [name, value] of Object.entries(options.headers)) assert.ok(!String(value).includes(user.id), `${url}: ${name} must not carry the user id`);
    assert.ok(!url.includes(user.id) && !String(options.body || '').includes(user.id), url);
  }
});

test('0.F1, R37: a session without a string id behaves the same, and a blank email sends nothing', async t => {
  const { calls, send } = await sessionProxy(t, { email: 'whitney@example.invalid', role: 'team' });
  assert.equal((await send('/flags')).status, 200);
  assert.equal(calls.at(-1).options.headers['x-atelier-actor'], 'whitney@example.invalid');
  const bad = await sessionProxy(t, { id: 'cc-user-77', email: '   ', role: 'team' });
  assert.equal((await bad.send('/flags')).status, 403);
  assert.equal(bad.calls.length, 1, 'only the session check ran; nothing was relayed under the id');
});

test('3.B7, 5.B7: Gate 1 refresh with feedback and card context are relayed with their bodies and the verified email', async t => {
  const { calls, send } = await proxy(t);
  const routes = [
    ['/angles/angle_one/refresh', { expected_hash: 'h', feedback: 'Lead with the form.', author: 'Whitney Hodges' }],
    ['/angles/angle_one/context', { kind: 'attested_fact', text: 'We ran the spring campaign.' }],
  ];
  for (const [path, body] of routes) {
    assert.equal((await send(path, 'POST', body)).status, 202);
    const forwarded = calls.at(-1);
    assert.equal(forwarded.url, `http://storage.example.invalid/storage${path}`);
    assert.equal(forwarded.options.headers['x-atelier-email'], 'whitney@example.invalid');
    assert.deepEqual(JSON.parse(forwarded.options.body), body);
    assert.equal((await send(path, 'GET')).status, 404, 'only the write is relayed');
    assert.equal((await send(`${path}/extra`, 'POST', body)).status, 404);
  }
  assert.equal((await send('/angles/angle_one/refresh?mode=live', 'POST', {})).status, 404, 'a write takes no query');
  assert.equal((await send('/angles/angle.one/refresh', 'POST', {})).status, 404);
});

