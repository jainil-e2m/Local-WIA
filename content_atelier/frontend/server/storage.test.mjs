import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { createApp } from './app.mjs';

test('weekly proxy verifies team sessions, strips spoofed identity and rejects CSRF', async t => {
  const calls = [];
  let role = 'team';
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/api/auth/session')) return Response.json({ user: { email: 'verified@example.invalid', role } });
    return Response.json({ saved: true });
  };
  const app = createApp({ authOrigin: 'http://auth.example.invalid', backendOrigin: 'http://storage.example.invalid', backendSecret: 'fixture-secret', production: false, fetcher });
  const server = http.createServer(app);
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const base = `http://127.0.0.1:${server.address().port}`;
  const headers = { cookie: 'wahha_session=fixture', 'content-type': 'application/json', 'x-atelier-actor': 'spoof', authorization: 'Bearer attacker' };
  assert.equal((await fetch(base + '/api/atelier/weeks')).status, 401);
  assert.equal(calls.length, 0);
  role = 'client';
  assert.equal((await fetch(base + '/api/atelier/weeks', { headers })).status, 403);
  assert.equal(calls.length, 1);
  role = 'team';
  assert.equal((await fetch(base + '/api/atelier/weeks', { headers })).status, 200);
  const forwarded = calls.at(-1);
  assert.equal(forwarded.url, 'http://storage.example.invalid/storage/weeks');
  assert.equal(forwarded.options.headers['x-atelier-actor'], 'verified@example.invalid');
  assert.equal(forwarded.options.headers.authorization, 'Bearer fixture-secret');
  assert.equal(forwarded.options.headers.cookie, undefined);
  const before = calls.length;
  assert.equal((await fetch(base + '/api/atelier/angles/angle_one', { method: 'PATCH', headers: { ...headers, origin: 'http://evil.example.invalid' }, body: '{}' })).status, 403);
  assert.equal(calls.length, before);
  assert.equal((await fetch(base + '/api/atelier/unknown', { headers })).status, 404);
  assert.equal((await fetch(base + '/api/atelier/weeks?redirect=evil', { headers })).status, 404);
  assert.equal((await fetch(base + '/api/atelier/angles/angle_one', { method: 'PATCH', headers: { ...headers, origin: base }, body: '{"expected_hash":"hash","changes":{"title":"Edited"}}' })).status, 200);
  assert.equal(calls.at(-1).options.method, 'PATCH');
});

test('comparison JSON and CSV exports retain team authorization and narrow allowlist', async t => {
  const calls = [];
  let role = 'team';
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/api/auth/session')) return Response.json({ user: { id: 'verified', email: 'verified@example.invalid', role } });
    if (url.endsWith('.csv')) return new Response('cutoff,selected_id\n0.78,angle_one\n', { headers: { 'content-type': 'text/csv' } });
    return Response.json({ completion_state: 'comparison_complete' });
  };
  const app = createApp({ authOrigin: 'http://auth.example.invalid', backendOrigin: 'http://storage.example.invalid', backendSecret: 'fixture', production: false, fetcher });
  const server = http.createServer(app);
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const base = `http://127.0.0.1:${server.address().port}/api/atelier`;
  const headers = { cookie: 'wahha_session=fixture' };
  assert.equal((await fetch(base + '/runs/run_one/comparison')).status, 401);
  role = 'client';
  assert.equal((await fetch(base + '/runs/run_one/comparison.csv', { headers })).status, 403);
  role = 'team';
  assert.equal((await fetch(base + '/runs/run_one/comparison', { headers })).status, 200);
  const csv = await fetch(base + '/runs/run_one/comparison.csv', { headers });
  assert.equal(csv.status, 200); assert.match(csv.headers.get('content-type'), /text\/csv/);
  assert.match(csv.headers.get('content-disposition'), /attachment/);
  assert.match(await csv.text(), /0.78,angle_one/);
  assert.equal(calls.at(-1).options.headers['x-atelier-actor'], 'verified@example.invalid');
  assert.notEqual(calls.at(-1).options.headers['x-atelier-actor'], 'verified');
  assert.equal((await fetch(base + '/runs/run_one/comparison.csv?cutoff=0.78', { headers })).status, 404);
  assert.equal((await fetch(base + '/runs/run_one/comparison.json', { headers })).status, 404);
});

test('brief proxy allows bounded filters, authenticated review and Markdown exports', async t => {
  const calls=[];
  const fetcher=async(url,options)=>{calls.push({url,options});if(url.endsWith('/api/auth/session'))return Response.json({user:{id:'reviewer',email:'team@example.invalid',role:'team'}});
    return url.endsWith('/export.md')?new Response('# Brief',{headers:{'content-type':'text/markdown'}}):Response.json({items:[],total:0});};
  const server=http.createServer(createApp({authOrigin:'http://auth.example.invalid',backendOrigin:'http://storage.example.invalid',backendSecret:'fixture',production:false,fetcher}));
  await new Promise(r=>server.listen(0,'127.0.0.1',r));t.after(()=>new Promise(r=>{server.closeAllConnections();server.close(r);}));
  const base=`http://127.0.0.1:${server.address().port}/api/atelier`,headers={cookie:'wahha_session=fixture','content-type':'application/json'};
  assert.equal((await fetch(base+'/briefs?week_id=week_2026-06-08&status=pending&limit=20&offset=0',{headers})).status,200);
  assert.match(calls.at(-1).url,/storage\/briefs\?week_id=week_2026-06-08/);
  const count=calls.length;
  for(const q of ['limit=101','limit=0','offset=-1','status=unknown','limit=20&limit=10','secret=x'])assert.equal((await fetch(base+`/briefs?${q}`,{headers})).status,404);
  assert.equal(calls.length,count);
  const md=await fetch(base+'/briefs/brief_one/export.md',{headers});assert.equal(md.status,200);assert.match(md.headers.get('content-type'),/text\/markdown/);
  assert.equal((await fetch(base+'/briefs/brief_one/review',{method:'POST',headers,body:'{}'})).status,200);
  assert.equal(calls.at(-1).options.headers['x-atelier-actor'],'team@example.invalid');assert.notEqual(calls.at(-1).options.headers['x-atelier-actor'],'reviewer');
  assert.equal((await fetch(base+'/briefs/brief_one/delete',{method:'POST',headers,body:'{}'})).status,404);
});

test("the week's review document downloads as Markdown through the relay (5.B14; found by the N1 shakedown)", async t => {
  const fetcher=async url=>url.endsWith('/api/auth/session')?Response.json({user:{email:'team@example.invalid',role:'team'}})
    :new Response('# Week of 12 October',{headers:{'content-type':'text/markdown; charset=utf-8'}});
  const server=http.createServer(createApp({authOrigin:'http://auth.example.invalid',backendOrigin:'http://storage.example.invalid',backendSecret:'fixture',production:false,fetcher}));
  await new Promise(r=>server.listen(0,'127.0.0.1',r));t.after(()=>new Promise(r=>{server.closeAllConnections();server.close(r);}));
  const answer=await fetch(`http://127.0.0.1:${server.address().port}/api/atelier/weeks/week_2026-10-12/review.md`,{headers:{cookie:'wahha_session=fixture'}});
  assert.equal(answer.status,200,'before the fix the relay answered 502: it took only JSON for this route');
  assert.match(answer.headers.get('content-type'),/text\/markdown/);
  assert.equal(answer.headers.get('content-disposition'),'attachment; filename="content-atelier-review-week_2026-10-12.md"');
  assert.equal(await answer.text(),'# Week of 12 October');
});

test("5.B14 in the app: the week's review document downloads as a Word file, byte for byte, only when the backend labels it .docx", async t => {
  const DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  // A .docx is a zip archive: bytes that are not valid UTF-8 and that any text handling would change.
  const bytes = Buffer.from([0x50, 0x4b, 0x03, 0x04, 0x14, 0x00, 0xff, 0xfe, 0x80, 0xc3, 0x28, 0x0d, 0x0a, 0x1a, 0x50, 0x4b, 0x05, 0x06]);
  let answer = () => new Response(bytes, { headers: { 'content-type': DOCX } });
  const calls = [];
  const fetcher = async (url, init) => {
    calls.push({ url, init });
    return url.endsWith('/api/auth/session') ? Response.json({ user: { email: 'team@example.invalid', role: 'team' } }) : answer();
  };
  const server = http.createServer(createApp({ authOrigin: 'http://auth.example.invalid', backendOrigin: 'http://storage.example.invalid', backendSecret: 'fixture', production: false, fetcher }));
  await new Promise(r => server.listen(0, '127.0.0.1', r)); t.after(() => new Promise(r => { server.closeAllConnections(); server.close(r); }));
  const base = `http://127.0.0.1:${server.address().port}/api/atelier`;
  const headers = { cookie: 'wahha_session=fixture' };
  const document = await fetch(`${base}/weeks/week_2026-10-12/review.docx`, { headers });
  assert.equal(document.status, 200, 'the relay refused this path before 5.B14 reached the app');
  assert.equal(calls.at(-1).url, 'http://storage.example.invalid/storage/weeks/week_2026-10-12/review.docx');
  assert.equal(document.headers.get('content-type'), DOCX);
  assert.equal(document.headers.get('content-disposition'), 'attachment; filename="content-atelier-review-week_2026-10-12.docx"');
  assert.deepEqual(Buffer.from(await document.arrayBuffer()), bytes, 'the bytes pass through unchanged');
  answer = () => Response.json({ not: 'a word file' });
  assert.equal((await fetch(`${base}/weeks/week_2026-10-12/review.docx`, { headers })).status, 502, 'JSON where a .docx was expected');
  answer = () => Response.json({ detail: 'Week not found: week_2030-01-07' }, { status: 404 });
  const missing = await fetch(`${base}/weeks/week_2030-01-07/review.docx`, { headers });
  assert.equal(missing.status, 404, "the backend's own error, as JSON");
  assert.deepEqual(await missing.json(), { detail: 'Week not found: week_2030-01-07' });
});
