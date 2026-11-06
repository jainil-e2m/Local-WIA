import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../testing/dom';
import { createQueryClient, queryKey } from '../api/query';
import { BRIEF_V2, seed, shell } from '../testing/fixtures';
import { SQLBriefs } from './SQLBriefs';
import { SeedsPanel } from './SeedCapture';

/* 1.F2: one handler for a 409. The backend refuses a write because the thing changed (a hash moved on): the screen shows
   the backend's message, keeps what the person typed, and reloads only when they ask. */

const BRIEF = { ...BRIEF_V2, can_review: true, can_approve: false };
const LIST = { items: [BRIEF], total: 1, limit: 20, offset: 0 };

function seeded() {
  const client = createQueryClient();
  const entries = [...shell({ briefs: true }), seed('/briefs', { query: { limit: 20, offset: 0 } }, LIST),
    seed('/briefs/{brief_id}', { path: { brief_id: 'brief_1' } }, BRIEF)];
  for (const [route, args, data] of entries) client.setQueryData(queryKey(route as never, args), data);
  return client;
}

test('1.F2: a refused review keeps the typed reason, shows the message and reloads only on request', async t => {
  const network = stubFetch((url, options) => {
    if (options?.method === 'POST' && url.endsWith('/briefs/brief_1/review')) return json({ detail: 'Brief content hash changed; reload it before reviewing' }, 409);
    return json({ detail: 'Not found' }, 404);
  });
  t.after(network.restore);
  const ui = await mount(<SQLBriefs />, { url: '/studio/briefs/brief_1', pattern: '/studio/briefs/:briefId', client: seeded() });
  t.after(() => ui.unmount());
  const field = [...ui.container.querySelectorAll('label')].find(label => label.textContent?.startsWith('What you checked'))?.querySelector('textarea');
  assert.ok(field, 'the review form is on screen');
  await ui.type(field, 'I checked the claims against the call.');
  const ack = [...ui.container.querySelectorAll('label')].find(label => label.textContent?.includes('I checked every claim against the call'))?.querySelector('input');
  await ui.tick(ack as HTMLInputElement);
  const reads = () => network.calls.filter(call => !call.options?.method || call.options.method === 'GET').length;
  const readsBefore = reads();
  const record = [...ui.container.querySelectorAll('button')].find(button => button.textContent === 'Record the check');
  assert.ok(record && !record.hasAttribute('disabled'), 'the review can be recorded');
  await ui.click(record);
  await ui.settle();

  const notice = ui.container.querySelector('[data-conflict]');
  assert.ok(notice, 'the conflict is shown');
  assert.match(notice.textContent ?? '', /Brief content hash changed; reload it before reviewing/);
  assert.match(notice.textContent ?? '', /still in the form/);
  assert.equal(field.value, 'I checked the claims against the call.', 'what the person typed is still in the form');
  assert.equal(reads(), readsBefore, 'nothing was reloaded on its own');

  await ui.click([...ui.container.querySelectorAll('button')].find(button => button.textContent === 'Reload the latest version') ?? null);
  await ui.settle();
  assert.ok(reads() > readsBefore, 'the reload happens when the person asks for it');
  assert.ok(network.calls.some(call => call.url === '/api/atelier/briefs/brief_1' && (!call.options?.method || call.options.method === 'GET')), 'the brief itself is read again');
});

test('1.F2: any other refusal shows its message as an error, not as a conflict', async t => {
  const network = stubFetch((url, options) => options?.method === 'POST' ? json({ detail: 'Only an approver can do this' }, 403) : json([{ seed_id: 'seed_1', kind: 'thought', text: 'A thought', target_offer: null, source_url: null, author: 'Whitney', status: 'open', always_true: false, created_at: '2026-10-01T00:00:00Z', used_in_run_id: null }]));
  t.after(network.restore);
  const ui = await mount(<SeedsPanel />);
  t.after(() => ui.unmount());
  await ui.settle();
  const withdraw = [...ui.container.querySelectorAll('button')].find(button => button.textContent === 'Withdraw');
  assert.ok(withdraw, 'the open seed is listed');
  await ui.click(withdraw);
  await ui.settle();
  assert.match(ui.text(), /Only an approver can do this/);
  assert.equal(ui.container.querySelector('[data-conflict]'), null);
});
