import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createApp } from './app.mjs';
import { queryAllowed, routeAllowed } from './allowlist.mjs';

/* Phase 2 (2.B6, 2.B7, 2.B8, 2.B12): the search route, the moments ledger, the topic registry and the extraction health are relayed,
   with closed queries, for a team session only. */

const user = { id: 'u1', email: 'team@example.test', role: 'team' };
async function serve(t) {
  const calls = [];
  let role = 'team';
  const fetcher = async (url, init) => {
    calls.push({ url, init });
    if (url.endsWith('/api/auth/session')) return Response.json({ user: { ...user, role } });
    return Response.json({ ok: true });
  };
  const server = http.createServer(createApp({ authOrigin: 'http://auth.example.test', backendOrigin: 'http://backend.example.test', backendSecret: 's', production: false, fetcher }));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  return { base: `http://127.0.0.1:${server.address().port}/api/atelier`, headers: { cookie: 'wahha_session=t', 'content-type': 'application/json' }, calls, setRole: value => { role = value; } };
}

test('2.B8: the moments ledger, its facets and one moment are allowlisted with a closed query', async t => {
  const { base, headers, calls } = await serve(t);
  const filters = 'q=follow-up&client_id=client_maple&topic_id=topic_1&document_id=t_1&extractor_version=2026-10-19.scenes.v2&source_type=fathom&call_type=slack_thread'
    + '&speaker_role=client,prospect&moment_type=testimonial,data_point&consent_status=cleared,do_not_use'
    + '&from=2026-01-01T00:00:00Z&to=2026-03-31T23:59:59%2B00:00&quote_verified=any&is_current=false&limit=200&offset=400';
  for (const route of ['/moments', '/moments/facets', '/moments/m_1', `/moments?${filters}`, `/moments/facets?${filters.replace(/&limit=200&offset=400/, '')}`]) {
    assert.equal((await fetch(base + route, { headers })).status, 200, route);
  }
  assert.equal(calls.at(-1).url.startsWith('http://backend.example.test/storage/moments/facets?q=follow-up'), true);
  const refused = [
    '/moments?speaker_role=gossip', '/moments?speaker_role=client,gossip', '/moments?speaker_role=client,client', '/moments?speaker_role=client,', '/moments?speaker_role=',
    '/moments?moment_type=story,nonsense', '/moments?consent_status=sure', '/moments?source_type=email', '/moments?call_type=sales',
    '/moments?quote_verified=maybe', '/moments?is_current=1', '/moments?from=2026-01-01', '/moments?to=tomorrowZ', '/moments?limit=0', '/moments?limit=201',
    '/moments?offset=-1', '/moments?limit=5&limit=6', '/moments?q=', `/moments?q=${'a'.repeat(201)}`, '/moments?q=a%00b', '/moments?client_id=a/b',
    '/moments?secret=x', '/moments/facets?limit=5', '/moments/facets?offset=5', '/moments/m_1?limit=5', '/moments/a/b', '/moments/',
  ];
  for (const route of refused) assert.equal((await fetch(base + route, { headers })).status, 404, route);
  // PUT is a relayed method since the Settings screen's changes (6.F7), so an unlisted path answers 404 for it, as for PATCH.
  for (const method of ['PATCH', 'PUT']) assert.equal((await fetch(base + '/moments/m_1', { method, headers, body: '{}' })).status, 404, method);
  assert.equal((await fetch(base + '/moments/m_1', { method: 'DELETE', headers })).status, 405, 'a method the relay never forwards');
  assert.equal((await fetch(base + '/moments', { method: 'POST', headers, body: '{}' })).status, 404, 'nothing creates a moment from the browser');
});

test('2.B6: POST /search is relayed, a GET is not, and only a team session may use it', async t => {
  const { base, headers, calls } = await serve(t);
  const body = JSON.stringify({ text: 'how fast should we reply', k: 10, scope: 'all', filters: { client_id: 'client_maple', moment_type: ['result'] } });
  assert.equal((await fetch(base + '/search', { method: 'POST', headers, body })).status, 200);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/search');
  assert.equal((await fetch(base + '/search/transcripts', { method: 'POST', headers, body })).status, 404, 'the earlier transcript search has no screen, so it is not relayed');
  assert.equal((await fetch(base + '/search', { headers })).status, 404);
  assert.equal((await fetch(base + '/search?x=1', { method: 'POST', headers, body })).status, 404, 'a write takes no query');
  assert.equal((await fetch(base + '/search/other', { method: 'POST', headers, body })).status, 404);
  assert.equal((await fetch(base + '/search', { method: 'POST', headers, body: JSON.stringify({ text: 'x'.repeat(70_000) }) })).status, 413);
  // The 401 without a session and a client session's 403, on each write, are in the role matrix (roles.test.mjs, 6.X2).
});

test('2.B7: the topic list is relayed with a closed query and a moment\'s topics as a POST without one; the administrator actions have no screen and are not relayed', async t => {
  const { base, headers, setRole } = await serve(t);
  for (const route of ['/topics', '/topics?status=blocked&q=reply&limit=200&offset=10']) {
    assert.equal((await fetch(base + route, { headers })).status, 200, route);
  }
  for (const route of ['/topics?status=gone', '/topics?q=', '/topics?limit=0', '/topics?limit=201', '/topics?client_id=x', '/topics/topic_1', '/topics/topic_1?status=active', '/topics/a/b']) {
    assert.equal((await fetch(base + route, { headers })).status, 404, route);
  }
  assert.equal((await fetch(base + '/moments/m_1/topics', { method: 'POST', headers, body: '{}' })).status, 200);
  assert.equal((await fetch(base + '/moments/m_1/topics?x=1', { method: 'POST', headers, body: '{}' })).status, 404, 'a write takes no query');
  // Rename, merge, block and unblock are an administrator's commands (storage_cli); a browser session cannot reach them.
  for (const route of ['/topics/topic_1/rename', '/topics/topic_1/merge', '/topics/topic_1/block', '/topics/topic_1/unblock',
    '/topics/topic_1/delete', '/topics/topic_1/unmerge', '/topics', '/moments/m_1/topics/extra']) {
    assert.equal((await fetch(base + route, { method: 'POST', headers, body: '{}' })).status, 404, route);
  }
  assert.equal((await fetch(base + '/topics/topic_1/rename', { method: 'PATCH', headers, body: '{}' })).status, 404);
  assert.equal((await fetch(base + '/topics/topic_1', { method: 'DELETE', headers })).status, 405);
  setRole('client');
  assert.equal((await fetch(base + '/topics', { headers })).status, 403);
  // A client session's 403 on each write is in the role matrix (roles.test.mjs, 6.X2).
});

test('2.B12: the extraction health is one read with no query', async t => {
  const { base, headers, calls } = await serve(t);
  assert.equal((await fetch(base + '/documents/extraction-health', { headers })).status, 200);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/documents/extraction-health');
  assert.equal((await fetch(base + '/documents/extraction-health?limit=5', { headers })).status, 404);
  assert.equal((await fetch(base + '/documents/extraction-health', { method: 'POST', headers, body: '{}' })).status, 404);
  assert.equal((await fetch(base + '/documents/t_1', { headers })).status, 200, 'a document is still read by its id');
});

test('Phase 2: every route the backend publishes for search, moments, topics and extraction health is relayed, except the topic administrator\'s', () => {
  const spec = JSON.parse(readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'backend', 'openapi.json'), 'utf8'));
  const phase2 = /^\/storage\/(?:search$|moments|topics|documents\/extraction-health$)/;
  // No screen reads one topic or renames, merges, blocks or unblocks one (2.F1, 2.F2); the relay forwards only what the app calls.
  const administrator = /^\/topics\/x1(?:\/(?:rename|merge|block|unblock))?$/;
  const found = [];
  for (const [route, operations] of Object.entries(spec.paths)) {
    if (!phase2.test(route)) continue;
    for (const method of Object.keys(operations)) {
      const relayed = route.replace(/^\/storage/, '').replace(/\{\w+\}/g, 'x1');
      found.push(`${method.toUpperCase()} ${relayed}`);
      assert.equal(routeAllowed(method.toUpperCase(), relayed), !administrator.test(relayed), `${method.toUpperCase()} ${relayed}`);
    }
  }
  assert.ok(found.length >= 12, `the document names ${found.length} Phase 2 operations: ${found.join(', ')}`);
  // And a read with a filter the backend accepts is not refused for it.
  assert.equal(queryAllowed('GET', '/moments', new URLSearchParams('consent_status=do_not_use&moment_type=data_point')), true);
  assert.equal(queryAllowed('GET', '/moments', new URLSearchParams('consent_status=do_not_use,do_not_use')), false);
});
