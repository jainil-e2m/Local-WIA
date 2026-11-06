import { test } from 'node:test';
import assert from 'node:assert/strict';
import { getMe, ME_NONE, readMe } from './me';

const approver = {
  email: 'whitney@example.invalid', name: 'Whitney', role: 'approver', roles: ['viewer', 'editor', 'approver'], source: 'users',
  identity_approver: true,
  can: { edit_cards: true, edit_briefs: true, decide: true, approve_briefs: true, review_knowledge: true, identity_review: true,
    manage_users: false, manage_intake: false, generate_packs: false, approve_packs: false, schedule_calendar: false },
};

test('0.F1: the answer of /me is read as roles and capabilities', () => {
  const me = readMe(approver);
  assert.equal(me.email, 'whitney@example.invalid');
  assert.equal(me.role, 'approver');
  assert.deepEqual(me.roles, ['viewer', 'editor', 'approver']);
  assert.equal(me.can.decide, true);
  assert.equal(me.can.manage_users, false);
  assert.equal(me.source, 'users');
});

test('0.F1: nothing is offered unless the server says exactly true', () => {
  assert.deepEqual(readMe(undefined), ME_NONE);
  assert.deepEqual(readMe(null), ME_NONE);
  assert.deepEqual(readMe('approver'), ME_NONE);
  const sloppy = readMe({ role: 'owner', roles: ['approver', 'owner', 7], source: 'cookie',
    can: { decide: 'true', edit_cards: 1, manage_intake: true, unknown_power: true } });
  assert.equal(sloppy.role, null);
  assert.deepEqual(sloppy.roles, ['approver']);
  assert.equal(sloppy.source, 'none');
  assert.equal(sloppy.can.decide, false);
  assert.equal(sloppy.can.edit_cards, false);
  assert.equal(sloppy.can.manage_intake, true);
  assert.ok(!('unknown_power' in sloppy.can));
  assert.ok(Object.values(ME_NONE.can).every(allowed => allowed === false));
});

test('0.F1: getMe asks the Node server for /me with the same-origin session', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/atelier/me');
    assert.equal(options?.credentials, 'same-origin');
    assert.equal(options?.method, 'GET');
    return new Response(JSON.stringify(approver), { status: 200, headers: { 'content-type': 'application/json' } });
  };
  assert.equal((await getMe()).can.approve_briefs, true);
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Verified actor email required' }), { status: 401, headers: { 'content-type': 'application/json' } });
  await assert.rejects(getMe(), /Verified actor email required|failed/);
});
