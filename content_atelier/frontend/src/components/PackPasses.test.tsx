import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../testing/dom';
import { seed, shell } from '../testing/fixtures';
import { PACK, version } from '../testing/packFixtures';
import { createQueryClient, queryKey } from '../api/query';
import type { StoredPackV2 } from '../api/types';
import { ContentPacks } from './ContentPacks';
import { recordedTakeRequest, refinishRequest } from './packFields';

/* NP-7's two person-started passes on the pack screen. NP.B14: a face-to-camera Reel takes "Paste what you said", which posts
   the recorded take for its caption and covers (never on the b-roll Reel). NP.B15: an approver grants a "stronger with
   permission" item in their own words, or states a fact, and the pack is finished again with them; what was granted shows. */

const TAKE = 'Before we touch anyone\'s ads, we ask one thing. How do you answer a new inquiry? That is where we start.';
const writes = (calls: { url: string; options?: RequestInit }[]) => calls.filter(c => c.options?.method === 'POST');
const sent = (call: { options?: RequestInit }) => JSON.parse(String(call.options!.body));

async function openPack(t: { after: (fn: () => unknown) => void }, answer: (url: string, options?: RequestInit) => Response | undefined,
  pack: StoredPackV2 = PACK) {
  const network = stubFetch((url, options) => answer(url, options) ?? (url === `/api/atelier/packs/${pack.pack_id}` ? json(pack) : json({ detail: 'Not found' }, 404)));
  t.after(network.restore);
  const client = createQueryClient();
  for (const [route, args, data] of [...shell({ packs: true }), seed('/packs/{pack_id}', { path: { pack_id: pack.pack_id } }, pack)]) client.setQueryData(queryKey(route as never, args), data);
  const ui = await mount(<ContentPacks base="/studio/packs" />, { url: `/studio/packs/${pack.pack_id}`, pattern: '/studio/packs/:packId', client });
  t.after(() => ui.unmount());
  const panel = (key: string) => ui.container.querySelector(`#pack-piece-panel-${key}`)!;
  const review = () => ui.container.querySelector('aside[aria-label="Review the pack"]')!;
  const button = (text: string, within: Element = ui.container) => [...within.querySelectorAll<HTMLButtonElement>('button')]
    .find(b => (b.getAttribute('aria-label') ?? b.textContent?.trim()) === text) ?? null;
  return { ui, network, panel, review, button };
}

test('NP.B14: a face-to-camera Reel takes the recorded take and posts it for its caption and covers; the b-roll Reel does not', async t => {
  const { ui, network, panel, button } = await openPack(t, (url, options) => {
    if (options?.method === 'POST' && url.endsWith('/pieces/reel_1/recorded')) return json({ pack_id: 'pack_5', manifest_hash: null, state: 'finishing', run_id: 'run_5' });
    if (url === '/api/atelier/packs/pack_5') return json(version('pack_5', { state: 'finishing', run_active: true, manifest_hash: null, state_reason: 'Writing the caption and covers from what was said' }));
    return undefined;
  });
  assert.equal(button('Paste what you said', panel('reel_3')), null, 'the b-roll Reel has no recorded take');
  await ui.click(ui.container.querySelector('#pack-piece-tab-reel_1'));
  await ui.click(button('Paste what you said', panel('reel_1')));
  const form = panel('reel_1').querySelector('form[aria-label="Reel 1: paste what you said"]')!;
  assert.match(form.textContent ?? '', /becomes this Reel's script word for word/);
  await ui.type(form.querySelector('textarea')!, 'Too short.');
  await ui.click(button('Write the caption and covers from it', form));
  assert.equal(writes(network.calls).length, 0, 'a fragment is refused before anything is sent');
  assert.match(form.textContent ?? '', /Paste the whole take/);
  await ui.type(form.querySelector('textarea')!, TAKE);
  await ui.click(button('Write the caption and covers from it', form));
  await ui.settle();
  const [take] = writes(network.calls);
  assert.equal(take.url, '/api/atelier/packs/pack_1/pieces/reel_1/recorded');
  assert.deepEqual({ ...sent(take), request_id: undefined }, { expected_manifest_hash: 'manifest_1', said: TAKE, request_id: undefined });
  await ui.settle();
  assert.match(ui.text(), /The caption and covers are being written from what you said\./, 'the result is said');
  assert.match(ui.text(), /The pack is being written\. This page updates by itself\./, 'the new version is being written');
});

test('NP.B15: "Stronger with permission" and its grants are no longer on the pack page; the items are listed in the closed "Before publishing"', async t => {
  const granted = version('pack_6', { granted: [{ item_id: 'S1', item: 'Naming the venue would make the story Reel concrete.', statement: 'The client agreed we may name the venue.',
    by: 'approver@example.com', at: '2026-10-26T10:00:00+00:00', delegated: false }] });
  const { ui, button } = await openPack(t, () => undefined, granted);
  assert.equal(ui.container.querySelector('aside[aria-label="Review the pack"]'), null);
  for (const removed of ['Stronger with permission', 'Granted', 'The client agreed we may name the venue.', 'approver@example.com']) {
    assert.ok(!ui.text().includes(removed), `not on the pack page: ${removed}`);
  }
  const fold = ui.container.querySelector('details[aria-label="Before publishing"]');
  assert.ok(fold && !fold.hasAttribute('open'), 'the before-publishing list is closed');
  assert.match(fold.textContent ?? '', /Would be stronger with the client's permissionNaming the venue would make the story Reel concrete\./);
  assert.equal(button('Finish again with these'), null);
  assert.equal(button('Grant: Naming the venue would make the story Reel concrete.'), null);
});

test('NP-7: the pass requests refuse what the API would refuse, in words', () => {
  assert.deepEqual(recordedTakeRequest('m', ' short '), { error: 'Paste the whole take: what Whitney said, start to end.' });
  assert.deepEqual(recordedTakeRequest('m', TAKE), { body: { expected_manifest_hash: 'm', said: TAKE } });
  assert.ok('error' in refinishRequest('m', [{ item_id: 'S1', statement: '  ' }]));
  assert.ok('error' in refinishRequest('m', [{ item_id: null, statement: 'ok' }]), 'a grant needs a few words');
});
