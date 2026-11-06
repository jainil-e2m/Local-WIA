import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createApp } from './app.mjs';
import { SETTABLE, routeAllowed, queryAllowed } from './allowlist.mjs';

const user = { id: 'u1', email: 'team@example.test', role: 'team' };
async function serve(t, options = {}) {
  const calls = [];
  let role = 'team';
  const fetcher = options.fetcher ?? (async (url, init) => {
    calls.push({ url, init });
    if (url.endsWith('/api/auth/session')) return Response.json({ user: { ...user, role } });
    return Response.json({ ok: true });
  });
  const server = http.createServer(createApp({ authOrigin: 'http://auth.example.test', backendOrigin: 'http://backend.example.test', backendSecret: 's', production: false, fetcher, ...options.app }));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const base = `http://127.0.0.1:${server.address().port}/api/atelier`;
  const headers = { cookie: 'wahha_session=t', 'content-type': 'application/json' };
  return { base, headers, calls, setRole: value => { role = value; } };
}

test('1.F5: the documents routes are allowlisted with a closed query, for a team session only', async t => {
  const { base, headers, calls, setRole } = await serve(t);
  const ok = ['/documents', '/documents/t_1', '/documents?source_type=attachment&call_type=slack_thread', '/documents?source_type=zoom&call_type=client_1to1&included=false&extraction_status=failed&date_state=undated&client_id=client_maple&q=follow-up&from=2026-01-01T00:00:00Z&to=2026-03-31T23:59:59%2B00:00&limit=200&offset=400'];
  for (const route of ok) assert.equal((await fetch(base + route, { headers })).status, 200, route);
  assert.equal(calls.at(-1).url.startsWith('http://backend.example.test/storage/documents?source_type=zoom'), true);
  const refused = ['/documents?source_type=email', '/documents?call_type=sales', '/documents?included=maybe', '/documents?extraction_status=x', '/documents?date_state=y',
    '/documents?client_id=a/b', '/documents?q=', `/documents?q=${'a'.repeat(201)}`, '/documents?q=a%00b', '/documents?from=2026-01-01', '/documents?to=tomorrowZ', '/documents?limit=0', '/documents?limit=201',
    '/documents?offset=-1', '/documents?offset=1000001', '/documents?limit=5&limit=6', '/documents?secret=x', '/documents/t_1?limit=5', '/documents/a/b', '/documents/'];
  for (const route of refused) assert.equal((await fetch(base + route, { headers })).status, 404, route);
  for (const method of ['POST', 'PATCH']) assert.equal((await fetch(base + '/documents', { method, headers, body: '{}' })).status, 404, method);
  assert.equal((await fetch(base + '/documents', { method: 'DELETE', headers })).status, 405);
  setRole('client');
  assert.equal((await fetch(base + '/documents', { headers })).status, 403);
  assert.equal((await fetch(base + '/documents/t_1', { headers })).status, 403);
  assert.equal((await fetch(base + '/documents')).status, 401);
});

test('1.F6, 1.F7: a waiting call is classified and a transcript uploaded through the relay, by a team session only', async t => {
  const { base, headers, calls } = await serve(t);
  const body = JSON.stringify({ call_type: 'client_1to1', reason: 'A member check-in' });
  const classified = await fetch(base + '/documents/t_1/classification', { method: 'POST', headers, body });
  assert.equal(classified.status, 200);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/documents/t_1/classification');
  assert.equal(calls.at(-1).init.method, 'POST');
  assert.equal(calls.at(-1).init.headers['x-atelier-actor'], 'team@example.test');
  assert.equal((await fetch(base + '/documents?needs_review=true', { headers })).status, 200);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/documents?needs_review=true');
  for (const route of ['/documents?needs_review=maybe', '/documents/t_1/classification?x=1', '/documents/a/b/classification', '/documents/t_1/decision', '/documents/import/x'])
    assert.equal((await fetch(base + route, { method: route.includes('?needs') ? 'GET' : 'POST', headers, body: route.includes('?needs') ? undefined : '{}' })).status, 404, route);
  // A transcript of a few hours fits the upload's limit; nothing larger, and no other write gets it.
  const transcript = JSON.stringify({ filename: 'call.vtt', content: 'Speaker: words and more words.\n'.repeat(60_000) });
  assert.ok(transcript.length > 1_000_000);
  assert.equal((await fetch(base + '/documents/import', { method: 'POST', headers, body: transcript })).status, 200);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/documents/import');
  assert.equal((await fetch(base + '/documents/import', { method: 'POST', headers, body: JSON.stringify({ content: 'x'.repeat(6_500_000) }) })).status, 413);
  assert.equal((await fetch(base + '/documents/t_1/classification', { method: 'POST', headers, body: transcript })).status, 413);
  // A client session's 403 on each write is in the role matrix (roles.test.mjs, 6.X2).
});

test('3.B2, 6.B3, 5.B14, 6.B13: the cycle, budget, review-document and measures routes are relayed with a closed query; nothing else of theirs', async t => {
  const { base, headers, calls } = await serve(t);
  const ok = ['/cycles', '/cycles?limit=20', '/cycles/preview?from=2026-10-12T00:00:00Z&to=2026-10-19T00:00:00Z', '/cycles/preview?from=2026-10-12T00:00:00%2B00:00',
    '/cycles/run_abc', '/budgets'];
  for (const route of ok) assert.equal((await fetch(base + route, { headers })).status, 200, route);
  // The review document is relayed; it must come back as Markdown, so this fake's JSON answer is refused (storage.test.mjs
  // has the Markdown case, which this test passed by accepting JSON before the N1 shakedown).
  assert.equal((await fetch(base + '/weeks/week_2026-10-12/review.md', { headers })).status, 502);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/weeks/week_2026-10-12/review.md');
  // The Word file is relayed too (5.B14 in the app); it must come back labelled .docx, so this JSON answer is refused here as well
  // (storage.test.mjs has the Word case).
  assert.equal((await fetch(base + '/weeks/week_2026-10-12/review.docx', { headers })).status, 502);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/weeks/week_2026-10-12/review.docx');
  // The week's measures with its editorial monitoring (6.B13).
  assert.equal((await fetch(base + '/weeks/week_2026-10-12/measures', { headers })).status, 200);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/weeks/week_2026-10-12/measures');
  assert.equal((await fetch(base + '/cycles', { method: 'POST', headers, body: JSON.stringify({ window_start: '2026-10-12T00:00:00Z', selection_hash: 'abcdef12' }) })).status, 200);
  const refused = ['/cycles/preview?to=2026-10-19T00:00:00Z', '/cycles/preview?from=2026-10-12', '/cycles/preview?from=x&from=y', '/cycles?limit=101',
    '/cycles?week=1', '/budgets?purpose=briefs', '/cycles/a/b', '/weeks/w/review.pdf', '/weeks/w/review.docx.md', '/weeks/w/review.md?x=1', '/weeks/w/review.docx?x=1',
    '/weeks/w/measures?week=1', '/weeks/a/b/measures', '/weeks/w/measures/x'];
  for (const route of refused) assert.equal((await fetch(base + route, { headers })).status, 404, route);
  for (const [method, route] of [['POST', '/budgets'], ['PATCH', '/cycles/run_abc'], ['POST', '/cycles/preview'], ['POST', '/cycles/run_abc'], ['POST', '/weeks/w/measures'], ['POST', '/weeks/w/review.docx']]) {
    assert.equal(routeAllowed(method, route), false, `${method} ${route}`);
  }
  assert.equal((await fetch(base + '/cycles')).status, 401, 'a session is required');
});

test('archived weeks: the week list takes ?include_archived and nothing else', async t => {
  const { base, headers, calls } = await serve(t);
  for (const route of ['/weeks', '/weeks?include_archived=true', '/weeks?include_archived=false']) {
    assert.equal((await fetch(base + route, { headers })).status, 200, route);
    assert.equal(calls.at(-1).url, `http://backend.example.test/storage${route}`);
  }
  for (const route of ['/weeks?include_archived=yes', '/weeks?include_archived=true&include_archived=true', '/weeks?archived=true', '/weeks/w?include_archived=true']) {
    assert.equal((await fetch(base + route, { headers })).status, 404, route);
  }
});

test('3.B11: the schedule is read through the relay, with no query and no write', async t => {
  const { base, headers, calls, setRole } = await serve(t);
  assert.equal((await fetch(base + '/schedule', { headers })).status, 200);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/schedule');
  assert.equal((await fetch(base + '/schedule?week=1', { headers })).status, 404, 'the read takes no query');
  for (const method of ['POST', 'PATCH', 'PUT']) assert.equal(routeAllowed(method, '/schedule'), false, method);
  assert.equal(routeAllowed('GET', '/schedule/next'), false);
  setRole('client');
  assert.equal((await fetch(base + '/schedule', { headers })).status, 403);
});

test('6.F2: Home\'s cycle summary is read through the relay, with no query and no write', async t => {
  const { base, headers, calls, setRole } = await serve(t);
  assert.equal((await fetch(base + '/summary', { headers })).status, 200);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/summary');
  assert.equal((await fetch(base + '/summary?week=1', { headers })).status, 404, 'the read takes no query');
  for (const method of ['POST', 'PATCH', 'PUT']) assert.equal(routeAllowed(method, '/summary'), false, method);
  setRole('client');
  assert.equal((await fetch(base + '/summary', { headers })).status, 403);
});

test('6.F5: the alerts (with ?resolved=true) and the costs are read through the relay, and an alert is dismissed as a write only', async t => {
  const { base, headers, calls, setRole } = await serve(t);
  for (const route of ['/alerts', '/alerts?resolved=true', '/alerts?resolved=false', '/costs']) {
    assert.equal((await fetch(base + route, { headers })).status, 200, route);
    assert.equal(calls.at(-1).url, `http://backend.example.test/storage${route}`);
  }
  assert.equal((await fetch(base + '/alerts/alert_1/dismiss', { method: 'POST', headers, body: '{}' })).status, 200);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/alerts/alert_1/dismiss');
  assert.equal(calls.at(-1).init.method, 'POST');
  const before = calls.length;
  for (const route of ['/alerts?resolved=yes', '/alerts?resolved=true&resolved=false', '/alerts?limit=5', '/costs?from=2026-10-01T00:00:00Z', '/alerts/alert_1', '/alerts/a/b/dismiss']) {
    assert.equal((await fetch(base + route, { headers })).status, 404, route);
  }
  assert.equal((await fetch(base + '/alerts/alert_1/dismiss', { headers })).status, 404, 'GET of the write is not relayed');
  assert.equal((await fetch(base + '/alerts/alert_1/dismiss?x=1', { method: 'POST', headers, body: '{}' })).status, 404, 'a write takes no query');
  assert.equal((await fetch(base + '/alerts/alert_1/dismiss', { method: 'POST', headers: { ...headers, 'sec-fetch-site': 'cross-site' }, body: '{}' })).status, 403);
  for (const [method, route] of [['POST', '/alerts'], ['PATCH', '/alerts/alert_1'], ['POST', '/costs'], ['POST', '/alerts/alert_1/resolve']]) {
    assert.equal(routeAllowed(method, route), false, `${method} ${route}`);
  }
  assert.equal(calls.length, before, 'none of the refused requests reached the backend');
  setRole('client');
  assert.equal((await fetch(base + '/alerts', { headers })).status, 403);
  assert.equal((await fetch(base + '/costs', { headers })).status, 403);
});

test('1.F5: unknown paths and methods are still refused', () => {
  for (const [method, route] of [['GET', '/secrets'], ['GET', '/weeks/a/b'], ['POST', '/weeks'], ['PATCH', '/weeks/w'], ['PUT', '/settings/x'], ['PUT', '/settings'], ['GET', '/settings/cycle.hour'],['GET', '/context/versions/../diff'],
    // Reads no screen makes are not relayed either.
    ['GET', '/topics/topic_1'], ['GET', '/context/mining']]) {
    assert.equal(routeAllowed(method, route), false, `${method} ${route}`);
  }
  assert.equal(queryAllowed('POST', '/seeds', new URLSearchParams('status=open')), false);
  assert.equal(queryAllowed('GET', '/weeks', new URLSearchParams('x=1')), false);
});

test('1.F5: the body limit stays 64 KB except for the CSV import, which is bounded at 384 KB', async t => {
  const { base, headers } = await serve(t);
  const body = size => JSON.stringify({ text: 'x'.repeat(size) });
  assert.equal((await fetch(base + '/seeds', { method: 'POST', headers, body: body(70_000) })).status, 413);
  assert.equal((await fetch(base + '/seeds', { method: 'POST', headers, body: body(1000) })).status, 200);
  assert.equal((await fetch(base + '/context/published/import', { method: 'POST', headers, body: JSON.stringify({ csv: 'a,\n'.repeat(60_000 / 3) + '"é"'.repeat(3000) }) })).status, 200, 'a full 60,000 character file passes');
  assert.equal((await fetch(base + '/context/published/import', { method: 'POST', headers, body: body(400_000) })).status, 413);
});

test('1.F5: exports and original text get a longer relay timeout; everything else keeps the short one', async t => {
  const slow = async (url, init) => {
    if (url.endsWith('/api/auth/session')) return Response.json({ user });
    await new Promise((resolve, reject) => { const timer = setTimeout(resolve, 150); init.signal.addEventListener('abort', () => { clearTimeout(timer); reject(new Error('timed out')); }); });
    return url.includes('/export.md') ? new Response('# brief', { headers: { 'content-type': 'text/markdown' } }) : Response.json({ ok: true });
  };
  const { base, headers } = await serve(t, { fetcher: slow, app: { timeoutMs: 60, longReadTimeoutMs: 1000 } });
  assert.equal((await fetch(base + '/weeks', { headers })).status, 503, 'an ordinary read times out');
  assert.equal((await fetch(base + '/briefs/b1/export.md', { headers })).status, 200, 'an export waits');
  assert.equal((await fetch(base + '/documents/t_1', { headers })).status, 200, 'a document with its passages waits');
  assert.equal((await fetch(base + '/seeds', { method: 'POST', headers, body: '{}' })).status, 503, 'a write never gets the longer timeout');
});

test('1.F1: a page asked for without a session keeps its path through sign-in; a signed-in session gets the app at any path', async t => {
  // No public Command Center origin here: the fallback through this host's form. With one, a page goes straight to the
  // hand-off with the same returnTo (signout.test.mjs, 6.F8).
  const { base, headers } = await serve(t);
  const root = base.replace('/api/atelier', '');
  const asked = await fetch(`${root}/studio/briefs/brief_1?status=pending`, { redirect: 'manual' });
  assert.equal(asked.status, 302);
  assert.equal(asked.headers.get('location'), '/login?returnTo=%2Fstudio%2Fbriefs%2Fbrief_1%3Fstatus%3Dpending');
  assert.equal((await fetch(`${root}/`, { redirect: 'manual' })).headers.get('location'), '/login');
  assert.equal((await fetch(`${root}/assets/app.js`, { redirect: 'manual' })).headers.get('location'), '/login');
  assert.equal((await fetch(`${root}//evil.example.test/x`, { redirect: 'manual' })).headers.get('location'), '/login');
  // Signed in: the SPA's index.html is served for a path with no file extension (the file is missing here, so the server answers, not the login).
  const signedIn = await fetch(`${root}/sources/documents/t_1`, { headers: { cookie: headers.cookie }, redirect: 'manual' });
  assert.notEqual(signedIn.status, 302);
});

// ---- every route the app calls is allowlisted

const src = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'src');
function* files(directory) {
  for (const entry of readdirSync(directory)) {
    const full = path.join(directory, entry);
    if (statSync(full).isDirectory()) yield* files(full);
    else if (/\.(ts|tsx)$/.test(entry) && !/\.test\.tsx?$/.test(entry) && !entry.endsWith('.d.ts')) yield full;
  }
}

/** The API paths the app's source names: typed calls ('/weeks/{week_id}'), request paths built in a template, and links to /api/atelier/... */
function calledPaths() {
  const found = new Map();
  const ids = text => text.replace(/\$\{[^}]*\}/g, 'x1').replace(/\{\w+\}/g, 'x1');
  const add = (raw, methods) => {
    // Placeholders stand for an identifier; the two that are numbers or a fixed set are filled with a valid one.
    const route = ids(raw).split('?')[0].replace('/considered/x1', '/considered/1').replace('/connections/x1/', '/connections/slack/')
      // A content pack's piece is one of five keys (NP.B6), not an identifier: fill it with one.
      .replace(/\/pieces\/x1(?=\/|$)/, '/pieces/email');
    if (route === '/weeks/x1/considered/1') { add('/weeks/x1/considered/1/revive', methods); add('/weeks/x1/considered/1/decision', methods); return; } // CardReview adds the action
    if (route === '/intake/x1') return; // the intake helper's own template; the routes it builds are named below
    // The Settings screen changes one of its keys by name (6.F7); the relay forwards those keys only.
    if (route === '/settings/x1') { for (const key of SETTABLE) add(`/settings/${key}`, methods); return; }
    found.set(route, new Set([...(found.get(route) ?? []), ...methods]));
  };
  const prefixes = 'weeks|angles|briefs|jobs|runs|seeds|search|moments|topics|transcripts|packs|calendar|context|intake|flags|me|documents|cycles|budgets|settings|schedule|alerts|costs|summary';
  const literal = new RegExp(`[\`'"](/(?:api/atelier/)?(?:${prefixes})(?:[/?][^\`'"\\s]*)?)[\`'"]`, 'g');
  for (const file of files(src)) {
    if (file.includes(`${path.sep}api${path.sep}`) && !/(?:documents|moments)\.ts$/.test(file)) continue;
    const text = readFileSync(file, 'utf8');
    for (const match of text.matchAll(literal)) {
      const value = match[1].replace(/^\/api\/atelier/, '');
      if (/^\/(?:documents|me|flags|weeks|briefs|seeds|calendar|packs|context|intake|search|moments|topics|cycles|budgets|settings|schedule|alerts|costs|summary)\b/.test(value) || /^\/(?:angles|jobs|runs|transcripts)\//.test(value)) add(value, ['GET', 'POST', 'PATCH', 'PUT']);
    }
    // Paths passed to a helper that adds a prefix: intake/${path} in IntakeView.
    for (const match of text.matchAll(/`(\/intake\/[^`]*)`/g)) add(match[1], ['GET', 'POST']);
    for (const match of text.matchAll(/act\(`((?:connections|jobs)\/[^`]*)`\)/g)) add(`/intake/${match[1]}`, ['POST']);
    for (const match of text.matchAll(/act\('(refresh|complete)'\)/g)) add(`/intake/${match[1]}`, ['POST']);
  }
  // The documents contract is written in documents.ts as route templates, plus the generated routes the typed client names.
  return found;
}

test('1.F5: the relay accepts no backend write that the app does not make', () => {
  // Every write the backend declares (backend/openapi.json), with its placeholders filled the way calledPaths fills them.
  // A write the relay would forward but the app never sends is surface with no use: it lets a browser session start
  // paid or administrative work (a live encoding, a live brief, a topic merge) that no screen offers.
  const api = JSON.parse(readFileSync(new URL('../../backend/openapi.json', import.meta.url), 'utf8'));
  const called = new Set(calledPaths().keys());
  const fill = route => route.replace(/^\/storage/, '').replace('{index}', '1').replace('{provider}', 'slack').replace('/pieces/{key}', '/pieces/email').replace(/\{\w+\}/g, 'x1');
  const writes = Object.entries(api.paths).filter(([route]) => route.startsWith('/storage/'))
    .flatMap(([route, operations]) => Object.keys(operations).filter(verb => verb !== 'get').map(verb => [verb.toUpperCase(), fill(route)]));
  assert.ok(writes.length > 40, `the OpenAPI document lists ${writes.length} writes; the reading must be broken`);
  const unused = writes.filter(([method, route]) => routeAllowed(method, route) && !called.has(route)).map(([method, route]) => `${method} ${route}`);
  assert.deepEqual(unused, [], 'remove these from server/allowlist.mjs, or call them from the app (with a test)');
});

test('1.F5: every route the app calls is allowlisted, and the relay forwards it', async t => {
  const found = calledPaths();
  assert.ok(found.size > 45, `the scan found ${found.size} routes; the pattern must be broken`);
  // The Phase 2 screens (2.F1 to 2.F3) call these: the ledger and its counts, one moment and its topics, the search, the topic list and the extraction health.
  for (const must of ['/documents', '/documents/x1', '/documents/extraction-health', '/weeks/x1', '/context/published/import', '/intake/overview', '/briefs/x1/export.md',
    '/moments', '/moments/facets', '/moments/x1', '/moments/x1/topics', '/search', '/topics',
    // The content pack screens (NP.F1 to NP.F3) call these.
    '/packs', '/packs/x1', '/packs/x1/production', '/packs/x1/pieces/email', '/packs/x1/pieces/email/published',
    '/packs/x1/clearances', '/packs/x1/findings/x1/attest', '/packs/x1/finish', '/packs/x1/decision', '/briefs/x1/pack',
    // NP-7: the recorded take on a face-to-camera Reel (the scan fills a piece key with email) and finishing again with a permission.
    '/packs/x1/pieces/email/recorded', '/packs/x1/refinish',
    // A draft knowledge-base version can be discarded from the Versions tab.
    '/context/versions/x1/discard']) {
    assert.ok([...found.keys()].some(route => route === must), `the scan should find ${must}`);
  }
  const missing = [...found].filter(([route, methods]) => ![...methods].some(method => routeAllowed(method, route))).map(([route]) => route);
  assert.deepEqual(missing, [], 'add these routes to server/allowlist.mjs, with a test');
  const { base, headers, calls } = await serve(t);
  for (const [route, methods] of found) {
    const method = ['GET', 'POST', 'PATCH', 'PUT'].find(candidate => methods.has(candidate) && routeAllowed(candidate, route));
    const before = calls.length;
    const response = await fetch(base + route, { method, headers, ...(method === 'GET' ? {} : { body: '{}' }) });
    assert.notEqual(response.status, 404, `${method} ${route}`);
    assert.ok(calls.length > before, `${method} ${route} reached the backend`);
  }
});

test('5.B7: context and attested facts are relayed for a card and a brief, as writes only, for a team session', async t => {
  const { base, headers, calls } = await serve(t);
  const body = JSON.stringify({ kind: 'attested_fact', text: 'The client\'s AI assistant made the changes.' });
  for (const route of ['/angles/angle_1/context', '/briefs/brief_1/context']) {
    assert.equal((await fetch(base + route, { method: 'POST', headers, body })).status, 200, route);
    assert.equal(calls.at(-1).url, `http://backend.example.test/storage${route}`);
    assert.equal(calls.at(-1).init.body, body, 'the body reaches the backend as sent');
    assert.equal((await fetch(base + route, { headers })).status, 404, `GET ${route} is not relayed`);
    assert.equal((await fetch(base + route + '?kind=context', { method: 'POST', headers, body })).status, 404, 'a write takes no query');
  }
  for (const route of ['/angles/a/b/context', '/briefs/brief_1/context/x', '/weeks/w/context']) {
    assert.equal(routeAllowed('POST', route), false, route);
  }
  // A client session's 403 on each write is in the role matrix (roles.test.mjs, 6.X2).
});

test('E.B30 (D31): a public stance is confirmed through the relay, as a write only, for a team session', async t => {
  const { base, headers, calls } = await serve(t);
  const body = JSON.stringify({ expected_hash: 'h1', note: 'Confirmed with Whitney on the call.' });
  const response = await fetch(base + '/angles/angle_1/stance', { method: 'POST', headers, body });
  assert.equal(response.status, 200);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/angles/angle_1/stance');
  assert.equal(calls.at(-1).init.body, body, 'the body reaches the backend as sent');
  assert.equal((await fetch(base + '/angles/angle_1/stance', { headers })).status, 404, 'GET is not relayed');
  assert.equal((await fetch(base + '/angles/angle_1/stance', { method: 'PATCH', headers, body })).status, 404, 'PATCH is not relayed');
  for (const route of ['/angles/a/b/stance', '/angles/angle_1/stance/x', '/briefs/brief_1/stance', '/weeks/w/stance']) {
    assert.equal(routeAllowed('POST', route), false, route);
  }
  // A client session's 403 on each write is in the role matrix (roles.test.mjs, 6.X2).
});

test('6.F7: the settings are read through the relay, and only the Settings screen\'s four keys may be changed', async t => {
  const { base, headers, calls, setRole } = await serve(t);
  assert.equal((await fetch(base + '/settings', { headers })).status, 200);
  assert.equal(calls.at(-1).url, 'http://backend.example.test/storage/settings');
  assert.equal(calls.at(-1).init.headers['x-atelier-email'], 'team@example.test', 'the backend decides editor or approver from the verified email');
  for (const key of ['matching.duplicate', 'cycle.timezone', 'cycle.weekday', 'cycle.hour']) {
    const body = JSON.stringify({ value: key === 'cycle.timezone' ? 'America/Chicago' : 1 });
    assert.equal((await fetch(`${base}/settings/${key}`, { method: 'PUT', headers, body })).status, 200, key);
    assert.equal(calls.at(-1).url, `http://backend.example.test/storage/settings/${key}`);
    assert.equal(calls.at(-1).init.method, 'PUT');
    assert.equal(calls.at(-1).init.body, body, 'the body reaches the backend as sent');
  }
  // Models, prompts, the knowledge-base pin and budgets are read-only on the screen, so no change to them is relayed.
  const before = calls.length;
  for (const key of ['models.default', 'prompts.profile.strategist', 'knowledge_base.version', 'budgets.weekly_usd.packs', 'matching.duplicatex', 'cycle']) {
    assert.equal((await fetch(`${base}/settings/${key}`, { method: 'PUT', headers, body: '{"value":1}' })).status, 404, key);
  }
  assert.equal((await fetch(base + '/settings?key=cycle.hour', { headers })).status, 404, 'the read takes no query');
  assert.equal((await fetch(base + '/settings/cycle.hour?x=1', { method: 'PUT', headers, body: '{}' })).status, 404, 'a write takes no query');
  assert.equal((await fetch(base + '/settings/cycle.hour', { method: 'POST', headers, body: '{}' })).status, 404, 'only PUT changes a setting');
  assert.equal((await fetch(base + '/settings/cycle.hour', { method: 'PUT', headers: { ...headers, 'sec-fetch-site': 'cross-site' }, body: '{}' })).status, 403, 'a cross-site change is refused');
  assert.equal(calls.length, before, 'none of these reached the backend');
  setRole('client');
  assert.equal((await fetch(base + '/settings', { headers })).status, 403);
});

test('6.F7: the relay\'s settable keys are the Settings screen\'s editable keys', () => {
  const source = readFileSync(new URL('../src/utils/settings.ts', import.meta.url), 'utf8');
  const listed = /EDITABLE_KEYS = \[([^\]]*)\]/.exec(source)?.[1].match(/'[^']+'/g)?.map(key => key.slice(1, -1));
  assert.deepEqual(listed, SETTABLE);
});

test('a draft knowledge-base version is discarded by a write the relay forwards, and only that write', () => {
  assert.ok(routeAllowed('POST', '/context/versions/wia-kb-2026-10-25.c-8ba81fcc/discard'), 'a version name with a dot');
  assert.ok(!routeAllowed('GET', '/context/versions/wia-kb-2026-10-25.c-8ba81fcc/discard'), 'a write, not a read');
  assert.ok(!routeAllowed('POST', '/context/versions/../discard'));
  assert.ok(!routeAllowed('DELETE', '/context/versions/wia-kb-2026-10-25.c-8ba81fcc'));
});
