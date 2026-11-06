import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { createApp } from './app.mjs';
import { routeAllowed, queryAllowed } from './allowlist.mjs';

/* NP.B6, NP.F1 to NP.F3: the content pack routes the app calls are relayed, each with its method, its path and its query
   rules, carrying the verified email as the actor; nothing else of theirs is. */

const user = { id: 'u1', email: 'team@example.test', role: 'team' };
async function serve(t, answer = () => Response.json({ ok: true })) {
  const calls = [];
  let role = 'team';
  const fetcher = async (url, init) => {
    calls.push({ url, init });
    if (url.endsWith('/api/auth/session')) return Response.json({ user: { ...user, role } });
    return answer(url, init);
  };
  const server = http.createServer(createApp({ authOrigin: 'http://auth.example.test', backendOrigin: 'http://backend.example.test', backendSecret: 's', production: false, fetcher }));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const base = `http://127.0.0.1:${server.address().port}/api/atelier`;
  const headers = { cookie: 'wahha_session=t', 'content-type': 'application/json', 'x-atelier-actor': 'forged@example.test' };
  return { base, headers, calls, setRole: value => { role = value; } };
}

test('NP.B6: the pack list is relayed with its closed query (week, brief, state, paging), and nothing else', async t => {
  const { base, headers, calls } = await serve(t);
  const ok = ['/packs', '/packs?week_id=week_2026-10-26', '/packs?brief_id=brief_v4&limit=5', '/packs?state=in_review&limit=20&offset=40',
    '/packs?state=finishing', '/packs?state=waiting', '/packs?week_id=week_2026-10-26&state=ready_to_publish&limit=100&offset=0'];
  for (const route of ok) assert.equal((await fetch(base + route, { headers })).status, 200, route);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/packs?week_id=week_2026-10-26&state=ready_to_publish&limit=100&offset=0');
  const before = calls.length;
  const refused = ['/packs?state=superseded', '/packs?state=draft', '/packs?status=pending', '/packs?brief_id=a/b', '/packs?week_id=', '/packs?limit=0', '/packs?limit=101',
    '/packs?offset=-1', '/packs?limit=5&limit=6', '/packs?secret=1', '/packs/pack_1?limit=1', '/packs/pack_1/production?x=1'];
  for (const route of refused) assert.equal((await fetch(base + route, { headers })).status, 404, route);
  assert.equal(calls.length, before, 'a refused query never reaches the backend');
});

test('NP.B6: one pack and its run are read; the piece edit is a PATCH by piece key only', async t => {
  const { base, headers, calls } = await serve(t);
  for (const route of ['/packs/pack_1', '/packs/pack_1/production']) assert.equal((await fetch(base + route, { headers })).status, 200, route);
  for (const key of ['email', 'carousel', 'reel_1', 'reel_2', 'reel_3']) {
    const body = JSON.stringify({ expected_manifest_hash: 'm', changes: { 'caption.hook': 'A line a person wrote.' }, request_id: 'r' });
    assert.equal((await fetch(`${base}/packs/pack_1/pieces/${key}`, { method: 'PATCH', headers, body })).status, 200, key);
    assert.equal(calls.at(-1).url, `http://backend.example.test/storage/packs/pack_1/pieces/${key}`);
    assert.equal(calls.at(-1).init.method, 'PATCH');
    assert.deepEqual(JSON.parse(calls.at(-1).init.body).changes, { 'caption.hook': 'A line a person wrote.' });
  }
  for (const route of ['/packs/pack_1/pieces/reel_4', '/packs/pack_1/pieces/script', '/packs/pack_1/pieces/email/x', '/packs/pack_1', '/packs/pack_1/pieces/email?x=1'])
    assert.equal((await fetch(base + route, { method: 'PATCH', headers, body: '{}' })).status, 404, `PATCH ${route}`);
  for (const route of ['/packs/pack_1/pieces/email', '/packs/pack_1/versions', '/packs/pack_1/assets'])
    assert.equal((await fetch(base + route, { headers })).status, 404, `GET ${route}`);
});

test('NP.B6: the pack writes are relayed as POSTs with their bodies and the verified email, never the forged one', async t => {
  const { base, headers, calls } = await serve(t);
  const writes = ['/packs/pack_1/clearances', '/packs/pack_1/findings/finding_1/attest', '/packs/pack_1/finish', '/packs/pack_1/decision', '/briefs/brief_v4/pack',
    ...['email', 'carousel', 'reel_1', 'reel_2', 'reel_3'].flatMap(key => [`/packs/pack_1/pieces/${key}/published`])];
  for (const route of writes) {
    const body = JSON.stringify({ expected_manifest_hash: 'm', request_id: 'r', route });
    assert.equal((await fetch(base + route, { method: 'POST', headers, body })).status, 200, route);
    assert.equal(calls.at(-1).url, `http://backend.example.test/storage${route}`);
    assert.equal(calls.at(-1).init.headers['x-atelier-actor'], 'team@example.test');
    assert.equal(JSON.parse(calls.at(-1).init.body).route, route, 'the body is forwarded');
  }
  // Writes no screen makes are not relayed: the v1 schedule, a write on the piece itself, a pack-wide revert, any query.
  for (const route of ['/packs/pack_1/schedule', '/packs/pack_1/pieces/email', '/packs/pack_1/revert', '/packs/pack_1/pieces/email/revert', '/packs/pack_1/pieces/reel_9/published', '/packs/pack_1/findings/a/b/attest',
    '/packs/pack_1/finish?mode=live', '/calendar/entry_1/cancel'])
    assert.equal((await fetch(base + route, { method: 'POST', headers, body: '{}' })).status, 404, route);
  for (const route of ['/packs/pack_1/clearances', '/packs/pack_1/finish', '/packs/pack_1/decision'])
    assert.equal((await fetch(base + route, { headers })).status, 404, `a write is not read: ${route}`);
});

test('NP.B6: a write from another site is refused, and a client session reaches no pack route', async t => {
  const { base, headers, setRole } = await serve(t);
  assert.equal((await fetch(base + '/packs/pack_1/decision', { method: 'POST', headers: { ...headers, origin: 'https://foreign.example.test' }, body: '{}' })).status, 403);
  setRole('client');
  for (const route of ['/packs', '/packs/pack_1']) assert.equal((await fetch(base + route, { headers })).status, 403, route);
  // A client session's 403 on each write is in the role matrix (roles.test.mjs, 6.X2).
  assert.equal((await fetch(base + '/packs')).status, 401, 'a session is required');
});

test('NP.B6: the allowlist reads the pack routes exactly', () => {
  assert.equal(routeAllowed('PATCH', '/packs/p/pieces/reel_3'), true);
  assert.equal(routeAllowed('PATCH', '/packs/p/pieces/reel_0'), false);
  // Using the brief's line again is no longer on the pack page (26 Oct), so the revert write is not relayed.
  assert.equal(routeAllowed('POST', '/packs/p/pieces/carousel/revert'), false);
  assert.equal(routeAllowed('POST', '/packs/p/schedule'), false);
  assert.equal(queryAllowed('GET', '/packs', new URLSearchParams('brief_id=brief_1&limit=5')), true);
  assert.equal(queryAllowed('POST', '/packs/p/finish', new URLSearchParams('x=1')), false);
});

test("NP.F4: the week's plan is read as JSON and the week's pack document downloads as Markdown, with the longer timeout", async t => {
  const slow = async (url, init) => {
    if (url.endsWith('/api/auth/session')) return Response.json({ user });
    await new Promise((resolve, reject) => { const timer = setTimeout(resolve, 150); init.signal.addEventListener('abort', () => { clearTimeout(timer); reject(new Error('timed out')); }); });
    return url.endsWith('/packs.md') ? new Response('# Content packs, week of 26 October', { headers: { 'content-type': 'text/markdown; charset=utf-8' } }) : Response.json({ week_id: 'w', slots: [] });
  };
  const server = http.createServer(createApp({ authOrigin: 'http://auth.example.test', backendOrigin: 'http://backend.example.test', backendSecret: 's', production: false,
    fetcher: slow, timeoutMs: 60, longReadTimeoutMs: 1000 }));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const base = `http://127.0.0.1:${server.address().port}/api/atelier`;
  const headers = { cookie: 'wahha_session=t' };
  const document = await fetch(`${base}/weeks/week_2026-10-26/packs.md`, { headers });
  assert.equal(document.status, 200, 'the document waits for the longer timeout, and Markdown is accepted for it');
  assert.match(document.headers.get('content-type'), /text\/markdown/);
  assert.equal(document.headers.get('content-disposition'), 'attachment; filename="content-atelier-packs-week_2026-10-26.md"');
  assert.equal(await document.text(), '# Content packs, week of 26 October');
  assert.equal((await fetch(`${base}/weeks/week_2026-10-26/pack-plan`, { headers })).status, 503, 'the plan is an ordinary read with the short timeout');
});

test('NP.F4: the week routes take no query and no write, and the plan must be JSON', async t => {
  const { base, headers, calls } = await serve(t, url => url.endsWith('/packs.md') ? Response.json({ not: 'markdown' }) : Response.json({ week_id: 'w', slots: [] }));
  assert.equal((await fetch(base + '/weeks/week_1/pack-plan', { headers })).status, 200);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/weeks/week_1/pack-plan');
  assert.equal((await fetch(base + '/weeks/week_1/packs.md', { headers })).status, 502, 'a document that is not Markdown is refused');
  for (const route of ['/weeks/week_1/pack-plan?x=1', '/weeks/week_1/packs.md?x=1', '/weeks/week_1/packs.docx?x=1', '/weeks/week_1/packs.pdf',
    '/weeks/week_1/packs.docx.md', '/weeks/week_1/packs', '/weeks/a/b/pack-plan'])
    assert.equal((await fetch(base + route, { headers })).status, 404, route);
  for (const route of ['/weeks/week_1/pack-plan', '/weeks/week_1/packs.md', '/weeks/week_1/packs.docx'])
    assert.equal((await fetch(base + route, { method: 'POST', headers, body: '{}' })).status, 404, `POST ${route}`);
});

test("NP.B12: the week's pack document downloads as a Word file, relayed byte for byte, with the longer timeout", async t => {
  const DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  // A .docx is a zip archive: binary, with bytes that are not valid UTF-8 and would be changed by any text handling.
  const bytes = Buffer.from([0x50, 0x4b, 0x03, 0x04, 0x14, 0x00, 0x00, 0x08, 0xff, 0xfe, 0x80, 0x00, 0xc3, 0x28, 0x0d, 0x0a, 0x1a, 0x00, 0x50, 0x4b, 0x05, 0x06]);
  const slow = async (url, init) => {
    if (url.endsWith('/api/auth/session')) return Response.json({ user });
    await new Promise((resolve, reject) => { const timer = setTimeout(resolve, 150); init.signal.addEventListener('abort', () => { clearTimeout(timer); reject(new Error('timed out')); }); });
    return url.endsWith('/packs.docx') ? new Response(bytes, { headers: { 'content-type': DOCX } }) : Response.json({ week_id: 'w', slots: [] });
  };
  const server = http.createServer(createApp({ authOrigin: 'http://auth.example.test', backendOrigin: 'http://backend.example.test', backendSecret: 's', production: false,
    fetcher: slow, timeoutMs: 60, longReadTimeoutMs: 1000 }));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const base = `http://127.0.0.1:${server.address().port}/api/atelier`;
  const document = await fetch(`${base}/weeks/week_2026-10-26/packs.docx`, { headers: { cookie: 'wahha_session=t' } });
  assert.equal(document.status, 200, 'the Word file waits for the longer timeout');
  assert.equal(document.headers.get('content-type'), DOCX);
  assert.equal(document.headers.get('content-disposition'), 'attachment; filename="content-atelier-packs-week_2026-10-26.docx"');
  assert.deepEqual(Buffer.from(await document.arrayBuffer()), bytes, 'the bytes pass through unchanged');
});

test('NP.B12: a Word file the backend does not label as .docx is refused, and a backend error is relayed as it is', async t => {
  let answer = () => Response.json({ not: 'a word file' });
  const { base, headers, calls } = await serve(t, () => answer());
  assert.equal((await fetch(base + '/weeks/week_1/packs.docx', { headers })).status, 502, 'JSON where a .docx was expected');
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/weeks/week_1/packs.docx');
  answer = () => new Response('PK', { headers: { 'content-type': 'application/octet-stream' } });
  assert.equal((await fetch(base + '/weeks/week_1/packs.docx', { headers })).status, 502, 'an unlabelled binary');
  answer = () => Response.json({ detail: { code: 'not_found' } }, { status: 404 });
  const missing = await fetch(base + '/weeks/week_missing/packs.docx', { headers });
  assert.equal(missing.status, 404, "the backend's own error, as JSON");
  assert.deepEqual(await missing.json(), { detail: { code: 'not_found' } });
});
