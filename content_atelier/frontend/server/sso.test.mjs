import { test } from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import http from 'node:http';
import express from 'express';
import { createSsoRouter, localReturnTo } from './sso.mjs';

const code = 'c'.repeat(43);
const user = { email: 'whitney@example.invalid', name: 'Whitney Fixture', role: 'team' };
const session = { sessionToken: 'fixture.signature', expiresIn: 3600, user };

async function fixture(t, options = {}) {
  const calls = [];
  let clock = 100_000;
  const app = express();
  app.use('/api/auth/sso', createSsoRouter({ authOrigin: 'https://command.example.invalid', publicAuthOrigin: 'https://command.example.invalid', production: false, now: () => clock, fetcher: async (url, init) => { calls.push({ url, init }); return Response.json(session); }, ...options }));
  const server = http.createServer(app);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const base = `http://127.0.0.1:${server.address().port}`;
  const request = (route, options = {}) => fetch(base + route, { redirect: 'manual', ...options });
  const start = async (returnTo = '/', cookie) => {
    const response = await request('/api/auth/sso/start?returnTo=' + encodeURIComponent(returnTo), { headers: cookie ? { cookie } : {} });
    return { response, authorize: new URL(response.headers.get('location')), cookie: response.headers.get('set-cookie').split(';')[0] };
  };
  const finish = (started, overrides = {}, cookie = started.cookie) => request('/api/auth/sso/callback?' + new URLSearchParams({ code, state: started.authorize.searchParams.get('state'), ...overrides }), { headers: cookie ? { cookie } : {} });
  return { base, calls, request, start, finish, advance: milliseconds => { clock += milliseconds; } };
}

test('return destinations stay within the Atelier and cannot redirect through auth routes', () => {
  assert.equal(localReturnTo('/workspace?source=command-center'), '/workspace?source=command-center');
  for (const value of ['https://evil.invalid', '//evil.invalid', '/\\evil.invalid', '/%2f%2fevil.invalid', '/%5cevil.invalid', '/.//evil.invalid', '/%2e//evil.invalid', '/path/..//evil.invalid', '/api/auth/sso/start', '/login', '/%0d%0aLocation:evil']) assert.equal(localReturnTo(value), '/');
});

test('receiver binds the browser state, holds the PKCE verifier server-side, and issues a host-only session', async t => {
  const f = await fixture(t);
  const started = await f.start('/workspace?source=command-center');
  assert.equal(started.authorize.origin, 'https://command.example.invalid');
  assert.equal(started.authorize.pathname, '/api/auth/content-atelier/authorize');
  assert.equal(started.authorize.searchParams.get('code_challenge_method'), 'S256');
  assert.equal(started.authorize.searchParams.get('redirect_uri'), f.base + '/api/auth/sso/callback');
  assert.ok(!started.authorize.searchParams.has('code_verifier'));
  assert.match(started.response.headers.get('set-cookie'), /HttpOnly; SameSite=Lax/);
  const response = await f.finish(started);
  assert.equal(response.status, 302);
  assert.equal(response.headers.get('location'), '/workspace?source=command-center');
  const cookies = response.headers.getSetCookie();
  assert.ok(cookies.some(cookie => cookie.includes('atelier_sso_state=;') && cookie.includes('Max-Age=0')));
  assert.ok(cookies.some(cookie => cookie.startsWith('wahha_session=fixture.signature;') && cookie.includes('Path=/; HttpOnly; SameSite=Lax; Max-Age=3600')));
  assert.ok(cookies.every(cookie => !cookie.includes('Domain=')));
  const { url, init } = f.calls[0];
  assert.equal(url, 'https://command.example.invalid/api/auth/content-atelier/exchange');
  assert.equal(init.method, 'POST');
  assert.equal(init.redirect, 'manual');
  const body = JSON.parse(init.body);
  assert.equal(body.redirect_uri, started.authorize.searchParams.get('redirect_uri'));
  assert.equal(crypto.createHash('sha256').update(body.code_verifier).digest('base64url'), started.authorize.searchParams.get('code_challenge'));
  assert.equal((await f.finish(started)).status, 400);
  assert.equal(f.calls.length, 1);
});

test('missing or forged browser state, expired transactions, and malformed codes never exchange', async t => {
  const f = await fixture(t);
  const started = await f.start();
  assert.equal((await f.finish(started, {}, '')).status, 400);
  assert.equal((await f.finish(started, { state: 'x'.repeat(43) })).status, 400);
  assert.equal((await f.finish(started, { code: 'bad' })).status, 400);
  assert.equal(f.calls.length, 0);
  f.advance(180_001);
  assert.equal((await f.finish(started)).status, 400);
  assert.equal(f.calls.length, 0);
});

test('failed or malformed exchanges cannot set an authenticated cookie', async t => {
  for (const result of [
    new Response(null, { status: 401 }),
    new Response(null, { status: 302 }),
    new Response('<html>wrong host</html>'),
    Response.json({ ...session, user: { ...user, role: 'admin' } }),
    Response.json({ ...session, sessionToken: 'bad\r\nSet-Cookie: injected' }),
    Response.json({ ...session, expiresIn: -1 }),
  ]) {
    const f = await fixture(t, { fetcher: async () => result });
    const started = await f.start();
    const response = await f.finish(started);
    assert.equal(response.status, 502);
    assert.ok(!response.headers.get('set-cookie').includes('wahha_session='));
  }
});

test('production uses HTTPS callbacks and Secure cookies even behind Railway TLS termination', async t => {
  const f = await fixture(t, { production: true });
  const started = await f.start();
  assert.equal(new URL(started.authorize.searchParams.get('redirect_uri')).protocol, 'https:');
  assert.match(started.response.headers.get('set-cookie'), /; Secure/);
  const response = await f.finish(started);
  assert.ok(response.headers.getSetCookie().every(cookie => cookie.endsWith('; Secure')));
});

test('private auth origins need a public browser origin only for SSO; retries replace pending state', async t => {
  const unconfigured = await fixture(t, { authOrigin: 'http://command.railway.internal:8080', publicAuthOrigin: undefined, production: true });
  assert.equal((await unconfigured.request('/api/auth/sso/start')).status, 503);
  const f = await fixture(t, { capacity: 1 });
  const first = await f.start();
  const next = await f.start('/', first.cookie);
  assert.equal(next.response.status, 302);
  assert.equal((await f.finish(first)).status, 400);
  assert.equal((await f.finish(next)).status, 302);
});
