import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { mkdtemp, writeFile, mkdir, rm, copyFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { createApp, validateAuthOrigin } from './app.mjs';

async function listen(server) {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  return `http://127.0.0.1:${server.address().port}`;
}
async function close(server) {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
const user = { email: 'fixture@example.invalid', name: 'Fixture', role: 'team' };

test('auth configuration refuses missing origins, embedded credentials and paths', () => {
  assert.equal(validateAuthOrigin('https://command.example.invalid/'), 'https://command.example.invalid');
  assert.equal(validateAuthOrigin('http://command.railway.internal:8080'), 'http://command.railway.internal:8080');
  for (const value of ['', 'file:///etc/passwd', 'https://user:secret@example.invalid', 'https://example.invalid/login', 'https://example.invalid?secret=yes']) {
    assert.throws(() => validateAuthOrigin(value));
  }
});

test('production server proxies real endpoint contracts and protects SPA assets through login/session/logout', async t => {
  const directory = await mkdtemp(path.join(tmpdir(), 'atelier-server-test-'));
  await mkdir(path.join(directory, 'assets'));
  await mkdir(path.join(directory, 'logos'));
  await copyFile(new URL('../public/logos/wia_favicon.png', import.meta.url), path.join(directory, 'logos', 'wia_favicon.png'));
  await writeFile(path.join(directory, 'index.html'), '<html>private studio</html>');
  await writeFile(path.join(directory, 'assets', 'studio.js'), 'const privateMeetingFixture = true;');
  const calls = [];
  const upstream = http.createServer(async (req, res) => {
    let body = '';
    for await (const chunk of req) body += chunk;
    calls.push({ url: req.url, headers: req.headers, body });
    res.setHeader('content-type', 'application/json');
    if (req.url === '/api/auth/login') {
      const input = JSON.parse(body);
      if (input.email !== user.email || input.password !== 'fixture-password') {
        res.writeHead(401); return res.end(JSON.stringify({ error: 'Incorrect email or password.' }));
      }
      res.setHeader('set-cookie', 'wahha_session=fixture-token; Domain=command.example.invalid; Path=/; HttpOnly; SameSite=Lax; Max-Age=3600');
      return res.end(JSON.stringify({ user }));
    }
    if (req.url === '/api/auth/logout') {
      res.setHeader('set-cookie', 'wahha_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0');
      return res.end('{"ok":true}');
    }
    if (req.headers.cookie === 'wahha_session=fixture-token') return res.end(JSON.stringify({ user }));
    res.writeHead(401); res.end('{"error":"Not authenticated."}');
  });
  const origin = await listen(upstream);
  const app = createApp({ authOrigin: origin, deploymentId: 'fixture-deployment', distDir: directory, production: false });
  const server = http.createServer(app);
  const base = await listen(server);
  t.after(async () => {
    await close(server);
    await close(upstream);
    // Delete only the absolute temporary directory created by this test.
    assert.equal(path.dirname(path.resolve(directory)), path.resolve(tmpdir()));
    assert.ok(path.basename(directory).startsWith('atelier-server-test-'));
    await rm(directory, { recursive: true, force: true });
  });
  const request = (route, options = {}) => fetch(`${base}${route}`, { redirect: 'manual', ...options });

  assert.equal((await request('/health')).status, 200);
  assert.equal((await request('/login')).status, 200);
  assert.equal((await request('/login.js')).status, 200);
  const favicon = await request('/logos/wia_favicon.png');
  assert.equal(favicon.status, 200);
  assert.match(favicon.headers.get('content-type'), /image\/png/);
  for (const route of ['/', '/weekly-studio', '/assets/studio.js', '/api/studio/deployment']) {
    const response = await request(route);
    assert.equal(response.status, 302);
    assert.equal(response.headers.get('location'), '/login');
  }
  assert.equal(calls.length, 0, 'requests without a session do not call the upstream');
  assert.equal((await request('/api/auth/session')).status, 401);
  const login = password => request('/api/auth/login', {
    method: 'POST', headers: { 'content-type': 'application/json', origin: base },
    body: JSON.stringify({ email: user.email, password }),
  });
  assert.equal((await login('wrong')).status, 401);
  const signedIn = await login('fixture-password');
  assert.equal(signedIn.status, 200);
  assert.deepEqual(await signedIn.json(), { user });
  const issued = signedIn.headers.get('set-cookie');
  assert.match(issued, /HttpOnly/);
  assert.match(issued, /SameSite=Lax/);
  assert.ok(!issued.includes('Domain='));
  const headers = { cookie: issued.split(';')[0] };
  assert.deepEqual(await (await request('/api/auth/session', { headers })).json(), { user });
  const deployment = await request('/api/studio/deployment', { headers });
  assert.equal(deployment.status, 200);
  assert.match(deployment.headers.get('cache-control'), /no-store/);
  assert.deepEqual(await deployment.json(), { deploymentId: 'fixture-deployment' });
  assert.deepEqual(await (await request('/api/studio/deployment', { headers })).json(), { deploymentId: 'fixture-deployment' });
  assert.equal(await (await request('/weekly-studio', { headers })).text(), '<html>private studio</html>');
  const asset = await request('/assets/studio.js', { headers: { cookie: `unrelated=secret; ${headers.cookie}` } });
  assert.equal(asset.status, 200);
  assert.match(asset.headers.get('cache-control'), /no-store/);
  assert.ok((await asset.text()).includes('privateMeetingFixture'));
  assert.equal(calls.at(-1).headers.cookie, headers.cookie, 'only the Command Center session is forwarded');
  assert.equal((await request('/assets/missing.js', { headers })).status, 404);
  assert.equal((await request('/assets/studio.js', { headers: { cookie: 'wahha_session=expired' } })).status, 302);
  const logout = await request('/api/auth/logout', { method: 'POST', headers: { ...headers, origin: base } });
  assert.equal(logout.status, 200);
  assert.match(logout.headers.get('set-cookie'), /Max-Age=0/);
  assert.equal((await request('/', { headers: { cookie: 'wahha_session=' } })).status, 302);

  assert.equal((await request('/api/auth/login')).status, 405);
  assert.equal((await request('/api/auth/arbitrary')).status, 404);
  const unknownApi = await request('/api/content-atelier');
  assert.equal(unknownApi.status, 404);
  assert.match(unknownApi.headers.get('content-type'), /application\/json/);
  assert.equal((await request('/api/auth/login', { method: 'POST', headers: { origin: 'https://attacker.example.invalid' } })).status, 403);
  assert.equal((await request('/api/auth/logout', { method: 'POST', headers: { 'sec-fetch-site': 'cross-site' } })).status, 403);
  assert.equal((await request('/api/auth/login', { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{invalid' })).status, 400);
  assert.equal((await request('/api/auth/login', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ password: 'a'.repeat(20_000) }) })).status, 413);
});

test('production preserves secure host-only cookies and forwards HTTPS to Command Center', async t => {
  let forwarded;
  const app = createApp({ authOrigin: 'https://command.example.invalid', fetcher: async (_url, options) => {
    forwarded = options;
    return Response.json({ user }, { headers: { 'set-cookie': 'wahha_session=signed; Path=/; HttpOnly; SameSite=Lax' } });
  } });
  const server = http.createServer(app);
  const base = await listen(server);
  t.after(() => close(server));
  const response = await fetch(`${base}/api/auth/login`, { method: 'POST', headers: { 'content-type': 'application/json', origin: base.replace('http:', 'https:') }, body: '{}' });
  assert.equal(response.status, 200);
  assert.match(response.headers.get('set-cookie'), /; Secure/);
  assert.equal(forwarded.headers['x-forwarded-proto'], 'https');
  assert.equal(forwarded.redirect, 'manual');
});

test('upstream errors and malformed sessions fail closed without exposing assets or inventing a guest', async t => {
  for (const fetcher of [
    async () => { throw new Error('offline'); },
    async () => new Response('<html>wrong host</html>'),
    async () => Response.json({ user: { ...user, role: 'admin' } }),
    async () => new Response(null, { status: 302, headers: { location: 'https://wrong.example.invalid' } }),
  ]) {
    const app = createApp({ authOrigin: 'https://command.example.invalid', production: false, fetcher });
    const server = http.createServer(app);
    const base = await listen(server);
    t.after(() => close(server));
    const response = await fetch(`${base}/assets/studio.js`, { headers: { cookie: 'wahha_session=unverified' }, redirect: 'manual' });
    assert.equal(response.status, 503);
    assert.ok(!(await response.text()).includes('privateMeetingFixture'));
  }
});
