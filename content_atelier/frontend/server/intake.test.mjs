import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { createApp } from './app.mjs';

test('intake proxy verifies team identity, isolates service routes and forwards downloads', async t => {
  const calls = [];
  let role = 'team';
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/api/auth/session')) return Response.json({ user: { id: 'verified-id', email: 'admin@example.test', role } });
    if (url.endsWith('/content')) return new Response('original bytes', { headers: { 'content-type': 'application/octet-stream' } });
    return Response.json({ ok: true });
  };
  const server = http.createServer(createApp({ authOrigin: 'http://auth.example.test', backendOrigin: 'http://backend.example.test', backendSecret: 'backend-secret', production: false, fetcher }));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const base = `http://127.0.0.1:${server.address().port}/api/atelier/intake`;
  const headers = { cookie: 'wahha_session=test', 'content-type': 'application/json', 'x-atelier-email': 'spoof@example.test' };
  assert.equal((await fetch(base + '/overview')).status, 401);
  role = 'client';
  assert.equal((await fetch(base + '/overview', { headers })).status, 403);
  role = 'team';
  assert.equal((await fetch(base + '/overview', { headers })).status, 200);
  assert.equal(calls.at(-1).options.headers['x-atelier-email'], 'admin@example.test');
  assert.equal(calls.at(-1).options.headers['x-atelier-actor'], 'admin@example.test');
  assert.notEqual(calls.at(-1).options.headers['x-atelier-actor'], 'verified-id');
  for (const path of ['/refresh', '/complete', '/connections/slack/activate', '/jobs/intake_job_1/retry', '/search']) {
    assert.equal((await fetch(base + path, { method: 'POST', headers, body: '{}' })).status, 200);
  }
  const count = calls.length;
  for (const path of ['/slack/batches', '/requests', '/connections/other/activate']) {
    assert.equal((await fetch(base + path, { method: 'POST', headers, body: '{}' })).status, 404);
  }
  assert.equal((await fetch(base + '/overview?secret=x', { headers })).status, 404);
  assert.equal((await fetch(base + '/refresh', { method: 'POST', headers: { ...headers, origin: 'https://evil.example.test' }, body: '{}' })).status, 403);
  assert.equal(calls.length, count);
  const download = await fetch(base + '/assets/asset_123/content', { headers });
  assert.equal(download.status, 200);
  assert.equal(await download.text(), 'original bytes');
  assert.match(download.headers.get('content-disposition'), /asset_123/);
});
