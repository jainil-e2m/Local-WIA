import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, apiRequest, isConflict } from './client';
import { apiGet, apiPatch, apiPost, routePath } from './routes';

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
function stub(t: { after: (fn: () => void) => void }, answer: (url: string, options?: RequestInit) => Response) {
  const calls: { url: string; options?: RequestInit }[] = [];
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = (async (url: string, options?: RequestInit) => { calls.push({ url, options }); return answer(url, options); }) as typeof fetch;
  return calls;
}

test('1.F1: a route is filled from its path parameters and a query without empty values', () => {
  assert.equal(routePath('/weeks/{week_id}', { path: { week_id: 'week_1' } }), '/weeks/week_1');
  assert.equal(routePath('/documents/{transcript_id}', { path: { transcript_id: 'a b/c' } }), '/documents/a%20b%2Fc');
  assert.equal(routePath('/briefs', { query: { status: 'pending', week_id: '', limit: 20, offset: undefined, q: null } }), '/briefs?status=pending&limit=20');
  assert.equal(routePath('/flags'), '/flags');
  assert.throws(() => routePath('/weeks/{week_id}', { path: {} }), /Missing path parameter week_id/);
});

test('1.F1: typed reads and writes go to the relay with the same-origin session and the generated paths', async t => {
  const calls = stub(t, () => json({ ok: true }));
  await apiGet('/weeks/{week_id}', { path: { week_id: 'week_1' } });
  await apiGet('/briefs', { query: { status: 'approved', limit: 100 } });
  await apiPost('/seeds/{seed_id}/withdraw', { path: { seed_id: 'seed_1' }, body: {} as never });
  await apiPatch('/briefs/{brief_id}', { path: { brief_id: 'brief_1' }, body: { expected_hash: 'h', changes: {} } });
  assert.deepEqual(calls.map(c => [c.options?.method, c.url]), [
    ['GET', '/api/atelier/weeks/week_1'], ['GET', '/api/atelier/briefs?status=approved&limit=100'],
    ['POST', '/api/atelier/seeds/seed_1/withdraw'], ['PATCH', '/api/atelier/briefs/brief_1'],
  ]);
  for (const call of calls) {
    assert.equal(call.options?.credentials, 'same-origin');
    assert.equal(call.options?.redirect, 'error');
    assert.equal(call.options?.cache, 'no-store');
  }
  assert.equal(JSON.parse(String(calls[3].options?.body)).expected_hash, 'h');
});

test('1.F2: a 409 is a conflict with the backend\'s message; other failures are not', async t => {
  stub(t, url => url.includes('conflict') ? json({ detail: 'Brief content hash changed; refresh before saving' }, 409)
    : url.includes('coded') ? json({ detail: { code: 'stale_pack', message: 'Pack changed; refresh' } }, 409) : json({ error: 'Request could not be processed.' }, 500));
  const conflict = await apiRequest('/conflict').catch(error => error);
  assert.ok(conflict instanceof ApiError && isConflict(conflict) && conflict.status === 409);
  assert.equal(conflict.message, 'Brief content hash changed; refresh before saving');
  const coded = await apiRequest('/coded').catch((error: ApiError) => error) as ApiError;
  assert.equal(coded.code, 'stale_pack');
  assert.equal(coded.message, 'Pack changed; refresh');
  const broken = await apiRequest('/broken').catch((error: ApiError) => error) as ApiError;
  assert.equal(isConflict(broken), false);
  assert.equal(broken.status, 500);
});

test('1.F1: an answer that is not JSON is reported as unavailable, not parsed', async t => {
  stub(t, () => new Response('<html>wrong host</html>', { status: 200, headers: { 'content-type': 'text/html' } }));
  await assert.rejects(apiRequest('/weeks'), /Weekly storage is unavailable/);
});

test('a request that runs out of time says so in plain words, not the browser\'s "signal timed out"', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = (async () => { throw new DOMException('signal timed out', 'TimeoutError'); }) as typeof fetch;
  await assert.rejects(apiRequest('/weeks/week_1'), (error: unknown) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 504);
    assert.doesNotMatch(error.message, /signal/);
    return true;
  });
});
