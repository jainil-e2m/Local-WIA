// S.C1: one sign-in and one sign-out for Command Center and the Atelier. Signing in happens on Command Center (the
// PKCE hand-off in sso.mjs); signing out in either app ends the session in both (Command Center revokes the shared token,
// and the browser passes through each host so each clears its own cookie).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { createApp } from './app.mjs';
import { publicCommandCenterOrigin } from './sso.mjs';

async function fixture(t, { publicAuthOrigin, production = false } = {}) {
  const calls = [];
  const upstream = http.createServer(async (req, res) => {
    let body = '';
    for await (const chunk of req) body += chunk;
    calls.push({ method: req.method, url: req.url, cookie: req.headers.cookie, body });
    res.setHeader('content-type', 'application/json');
    if (req.url === '/api/auth/logout') {
      res.setHeader('set-cookie', 'wahha_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0');
      return res.end('{"ok":true}');
    }
    // The hand-off's back channel (sso.mjs): a code for a session, as Command Center answers it.
    if (req.url === '/api/auth/content-atelier/exchange') {
      return res.end(JSON.stringify({ sessionToken: 'fixture.signature', expiresIn: 3600, user: { email: 'team@example.invalid', name: 'Team', role: 'team' } }));
    }
    res.writeHead(401); res.end('{"error":"Not authenticated."}');
  });
  await new Promise(resolve => upstream.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${upstream.address().port}`;
  const app = createApp({ authOrigin: origin, publicAuthOrigin, production });
  const server = http.createServer(app);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(async () => {
    for (const s of [server, upstream]) { s.closeAllConnections(); await new Promise(resolve => s.close(resolve)); }
  });
  const base = `http://127.0.0.1:${server.address().port}`;
  return { calls, request: (route, options = {}) => fetch(base + route, { redirect: 'manual', ...options }) };
}

const CC = 'https://command-center.example.invalid';

test('S.C1: with Command Center public, /login signs in there and keeps the page asked for', async t => {
  const f = await fixture(t, { publicAuthOrigin: CC });
  let response = await f.request('/login');
  assert.equal(response.status, 302);
  assert.equal(response.headers.get('location'), '/api/auth/sso/start');
  response = await f.request('/login?returnTo=%2Fweekly-studio%3Fweek%3D2026-10-19');
  assert.equal(response.headers.get('location'), '/api/auth/sso/start?returnTo=%2Fweekly-studio%3Fweek%3D2026-10-19');
  // A returnTo that would leave this host is dropped, as everywhere else (localReturnTo).
  response = await f.request('/login?returnTo=%2F%2Fevil.example.invalid');
  assert.equal(response.headers.get('location'), '/api/auth/sso/start');
  // The direct form stays reachable (it checks the same Command Center accounts).
  response = await f.request('/login?direct=1');
  assert.equal(response.status, 200);
  assert.match(await response.text(), /<form/);
});

test('6.F8: with Command Center public, a page asked for without a session goes straight to its hand-off and comes back to the page', async t => {
  const f = await fixture(t, { publicAuthOrigin: CC });
  const deep = '/studio/briefs/brief_1?status=pending';
  let response = await f.request(deep);
  assert.equal(response.status, 302);
  assert.equal(response.headers.get('location'), `/api/auth/sso/start?returnTo=${encodeURIComponent(deep)}`, 'one hop: not through /login');
  // The hand-off keeps the path: Command Center authorizes, the callback sets the session and opens the page asked for.
  response = await f.request(response.headers.get('location'));
  const authorize = new URL(response.headers.get('location'));
  assert.equal(authorize.origin, CC);
  const state = authorize.searchParams.get('state');
  const cookie = response.headers.get('set-cookie').split(';')[0];
  response = await f.request(`/api/auth/sso/callback?code=${'c'.repeat(43)}&state=${state}`, { headers: { cookie } });
  assert.equal(response.status, 302);
  assert.equal(response.headers.get('location'), deep);
  assert.ok(response.headers.getSetCookie().some(value => value.startsWith('wahha_session=fixture.signature;')));
  // The root has no path to keep; a path that would leave this host is dropped; an asset never starts a hand-off.
  assert.equal((await f.request('/')).headers.get('location'), '/api/auth/sso/start');
  assert.equal((await f.request('//evil.example.invalid/x')).headers.get('location'), '/api/auth/sso/start');
  assert.equal((await f.request('/assets/app.js')).headers.get('location'), '/login');
});

test('6.F8: every session check says how this host signs a person in', async t => {
  const withHandOff = await fixture(t, { publicAuthOrigin: CC });
  const signedOut = await withHandOff.request('/api/auth/session');
  assert.equal(signedOut.status, 401);
  assert.equal(signedOut.headers.get('x-atelier-sign-in'), 'command-center');
  const formOnly = await fixture(t);
  assert.equal((await formOnly.request('/api/auth/session')).headers.get('x-atelier-sign-in'), 'form');
  // Without a public origin a page keeps its path through this host's form instead (login.js follows it).
  assert.equal((await formOnly.request('/moments/m_1')).headers.get('location'), '/login?returnTo=%2Fmoments%2Fm_1');
});

test('S.C1: without a public Command Center origin, /login is this host\'s form', async t => {
  const f = await fixture(t);
  const response = await f.request('/login');
  assert.equal(response.status, 200);
});

test('S.C1: an Atelier sign-out revokes the session, clears this cookie and clears Command Center\'s', async t => {
  const f = await fixture(t, { publicAuthOrigin: CC });
  const response = await f.request('/api/auth/signout', { headers: { cookie: 'wahha_session=shared-token' } });
  assert.equal(response.status, 302);
  assert.equal(response.headers.get('location'), `${CC}/api/auth/signout?from=atelier`);
  assert.match(response.headers.get('set-cookie'), /^wahha_session=; Path=\/; HttpOnly; SameSite=Lax; Max-Age=0/);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  // Command Center was told over the backchannel, with the token both apps share, so it revokes it.
  assert.deepEqual(f.calls.map(c => [c.method, c.url, c.cookie]), [['POST', '/api/auth/logout', 'wahha_session=shared-token']]);
});

test('S.C1: the second leg of a Command Center sign-out ends on Command Center\'s sign-in page, never loops', async t => {
  const f = await fixture(t, { publicAuthOrigin: CC });
  const response = await f.request('/api/auth/signout?from=command-center');
  assert.equal(response.headers.get('location'), `${CC}/login`);
  assert.equal(f.calls.length, 0); // no cookie here: nothing to revoke
});

test('S.C1: sign-out still clears the cookie when Command Center is unreachable', async t => {
  const app = createApp({ authOrigin: 'http://127.0.0.1:9', publicAuthOrigin: CC, production: true, timeoutMs: 500 });
  const server = http.createServer(app);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const response = await fetch(`http://127.0.0.1:${server.address().port}/api/auth/signout`, { redirect: 'manual', headers: { cookie: 'wahha_session=x' } });
  assert.equal(response.status, 302);
  assert.match(response.headers.get('set-cookie'), /Max-Age=0; Secure/);
  assert.equal(response.headers.get('location'), `${CC}/api/auth/signout?from=atelier`);
});

test('S.C1: without a public Command Center origin, sign-out ends on this host\'s sign-in page', async t => {
  const f = await fixture(t);
  const response = await f.request('/api/auth/signout', { headers: { cookie: 'wahha_session=t' } });
  assert.equal(response.headers.get('location'), '/login');
});

test('publicCommandCenterOrigin accepts only a browser-safe origin', () => {
  assert.equal(publicCommandCenterOrigin('https://command-center-wia.up.railway.app', true), 'https://command-center-wia.up.railway.app');
  assert.equal(publicCommandCenterOrigin('http://localhost:18090', false), 'http://localhost:18090');
  for (const [value, production] of [['http://localhost:18090', true], ['http://command.railway.internal:8080', false], ['https://x.invalid/path', true], ['https://u:p@x.invalid', true], ['', true], [undefined, true]]) {
    assert.equal(publicCommandCenterOrigin(value, production), null);
  }
});
