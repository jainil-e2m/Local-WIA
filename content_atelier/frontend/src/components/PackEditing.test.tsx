import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../testing/dom';
import { renderScreen } from '../testing/render';
import { seed, shell } from '../testing/fixtures';
import { PACK, piece, version } from '../testing/packFixtures';
import { createQueryClient, queryKey } from '../api/query';
import type { StoredPackV2 } from '../api/types';
import { ContentPacks } from './ContentPacks';
import { diffWords, editRequest, isEditablePath, lockFor, pieceSections } from './packFields';

/* NP.F2, done when: an edit locks and saves; a stale hash shows the conflict with the input kept; an edit during a run is
   refused with its reason; a revert restores the brief's leaf. Edits go by dotted path relative to the piece's content, with
   the manifest hash of the version they were made on (PATCH /packs/{id}/pieces/{key}). */

const texts = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/\s+/g, ' ');
type Answer = (url: string, options?: RequestInit) => Response | undefined;

async function open(t: { after: (fn: () => unknown) => void }, answer: Answer, pack: StoredPackV2 = PACK) {
  const network = stubFetch((url, options) => answer(url, options) ?? (url === `/api/atelier/packs/${pack.pack_id}` ? json(pack) : json({ detail: 'Not found' }, 404)));
  t.after(network.restore);
  const client = createQueryClient();
  for (const [route, args, data] of [...shell({ packs: true }), seed('/packs/{pack_id}', { path: { pack_id: pack.pack_id } }, pack)]) client.setQueryData(queryKey(route as never, args), data);
  const ui = await mount(<ContentPacks base="/studio/packs" />, { url: `/studio/packs/${pack.pack_id}`, pattern: '/studio/packs/:packId', client });
  t.after(() => ui.unmount());
  const button = (label: string) => ui.container.querySelector<HTMLButtonElement>(`button[aria-label="${label}"]`)
    ?? [...ui.container.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent?.trim() === label && !b.closest('[hidden]')) ?? null;
  return { ui, network, button };
}

const writes = (calls: { url: string; options?: RequestInit }[], method: string) => calls.filter(c => c.options?.method === method);

test('NP.F2: an edit saves by its path with the manifest hash, then the new version shows the line, without a lock badge', async t => {
  const saved = version('pack_2', { pieces: PACK.pieces.map(p => p.key === 'email' ? piece('email', {
    content: { ...p.content, preview: 'The inquiry is where it starts.' },
    locks: [{ path: 'preview', author: 'whitney@example.invalid', delegated: false, at: '2026-10-24T11:00:00Z', origin: 'pack' }],
    changes: [{ path: 'preview', kind: 'edited', before: 'It starts after the inquiry.', after: 'The inquiry is where it starts.', note: null }] }) : p) });
  const { ui, network, button } = await open(t, (url, options) => {
    if (options?.method === 'PATCH') return json({ pack_id: 'pack_2', manifest_hash: 'manifest_pack_2', state: 'in_review', run_id: 'run_1' });
    if (url === '/api/atelier/packs/pack_2') return json(saved);
    return undefined;
  });
  await ui.click(button('Edit Email: Preview'));
  const field = ui.container.querySelector<HTMLInputElement>('#pack-email-preview');
  assert.ok(field, 'the preview is open for editing');
  assert.equal(field.value, 'It starts after the inquiry.');
  await ui.type(field, 'The inquiry is where it starts.');
  assert.match(ui.text(), /1 line changed\./);
  assert.ok(!ui.text().includes('Saving puts the pack back in review'), 'a pack in review is not sent back to review');
  await ui.click(button('Save 1 change'));
  await ui.settle();
  const [patch] = writes(network.calls, 'PATCH');
  assert.equal(patch.url, '/api/atelier/packs/pack_1/pieces/email');
  const body = JSON.parse(String(patch.options!.body));
  assert.deepEqual(body.changes, { preview: 'The inquiry is where it starts.' });
  assert.equal(body.expected_manifest_hash, 'manifest_1');
  assert.match(body.request_id, /^[0-9a-f-]{36}$/);
  await ui.settle();
  // The new version opens in place with the person's line; who wrote it is no longer printed beside it.
  assert.ok(network.calls.some(c => c.url === '/api/atelier/packs/pack_2'), 'the new version is read');
  const email = ui.container.querySelector('#pack-piece-panel-email')!;
  assert.match(email.textContent ?? '', /The inquiry is where it starts\./);
  assert.ok(!/Locked|whitney@example\.invalid/.test(email.textContent ?? ''), 'no lock badge and no author on the line');
  assert.equal(ui.container.querySelector('#pack-email-preview'), null, 'the draft was saved, not kept');
});

test('NP.F2: a stale manifest hash shows the conflict notice and keeps what the person typed', async t => {
  const { ui, network, button } = await open(t, (_url, options) => options?.method === 'PATCH'
    ? json({ detail: { message: 'The pack changed since you opened it: reload it before saving.', code: 'stale_pack' } }, 409) : undefined);
  await ui.click(button('Edit Reel 1: On-screen hook'));
  const field = ui.container.querySelector<HTMLInputElement>('#pack-reel_1-on-screen-hook')!;
  await ui.type(field, 'A hook the person wrote.');
  const reads = () => network.calls.filter(c => !c.options?.method || c.options.method === 'GET').length;
  const before = reads();
  // The save bar is in the Reel 1 panel; open its tab first, as a person would.
  await ui.click(ui.container.querySelector('#pack-piece-tab-reel_1'));
  await ui.click(button('Save 1 change'));
  await ui.settle();
  const notice = ui.container.querySelector('[data-conflict]');
  assert.ok(notice, 'the conflict is shown');
  assert.match(notice.textContent ?? '', /The pack changed since you opened it/);
  assert.match(notice.textContent ?? '', /still in the form/);
  assert.equal(ui.container.querySelector<HTMLInputElement>('#pack-reel_1-on-screen-hook')?.value, 'A hook the person wrote.', 'the input is kept');
  assert.equal(reads(), before, 'nothing reloads on its own');
  assert.equal(writes(network.calls, 'PATCH').length, 1);
});

test('NP.F2: an edit while a run is active is refused with its reason, and the input is kept', async t => {
  const { ui, button } = await open(t, (_url, options) => options?.method === 'PATCH'
    ? json({ detail: { message: "The pack's run is still active: edits wait until it ends.", code: 'pack_running' } }, 409) : undefined);
  await ui.click(button('Edit Email: Body'));
  const field = ui.container.querySelector<HTMLTextAreaElement>('#pack-email-body')!;
  await ui.type(field, 'A body the person wrote.');
  await ui.click(button('Save 1 change'));
  await ui.settle();
  assert.equal(ui.container.querySelector('[data-conflict]'), null, 'a run is not a conflict to reload');
  const alert = [...ui.container.querySelectorAll('[role="alert"]')].map(a => a.textContent).join(' ');
  assert.match(alert, /The pack's run is still active: edits wait until it ends\./);
  assert.match(alert, /still in the form/);
  assert.equal(ui.container.querySelector<HTMLTextAreaElement>('#pack-email-body')?.value, 'A body the person wrote.');
});

test('NP.F2: while the pack is finishing, its lines cannot be edited, and the page says it is being written', () => {
  const html = texts(renderScreen(<ContentPacks base="/studio/packs" />, { url: '/studio/packs/pack_1', pattern: '/studio/packs/:packId',
    seed: [...shell({ packs: true }), seed('/packs/{pack_id}', { path: { pack_id: 'pack_1' } }, { ...PACK, state: 'finishing', run_active: true, state_reason: 'Finishing the copy' })] }));
  assert.ok(html.includes('The pack is being written. This page updates by itself.'));
  assert.ok(!/aria-label="Edit /.test(html) && !html.includes(' Edit '), 'no line offers an edit');
  assert.ok(!html.includes('Ready to publish'), 'no decision while it is written');
});

test('NP.F2: the piece no longer shows what the system changed, the brief\'s line, lock badges or the version list', async t => {
  const locked = version('pack_2', { pieces: PACK.pieces.map(p => p.key === 'email'
    ? piece('email', { locks: [{ path: 'preview', author: 'team@example.invalid', delegated: true, at: null, origin: 'gate_two' }] }) : p) });
  const { ui } = await open(t, () => undefined, locked);
  await ui.settle();
  const panel = ui.container.querySelector('#pack-piece-panel-email')!;
  assert.equal(panel.querySelectorAll('button[aria-pressed]').length, 0, 'no toggles on the piece');
  const words = ui.text();
  for (const removed of ['What the system changed', "Use the brief's line", "The brief's line", 'Compared with the brief', 'Finished from the brief', 'Written by the system',
    'Locked', 'team@example.invalid', '(delegated)', 'Versions (', 'Version 2 (this one)']) {
    assert.ok(!words.includes(removed), `not on the pack page: ${removed}`);
  }
  assert.equal(panel.querySelector('[aria-label="Compared with the brief"]'), null);
  assert.equal(lockFor(locked.pieces[0], 'preview')?.author, 'team@example.invalid', 'the lock is still read from the pack');
  assert.equal(lockFor(locked.pieces[0], 'body'), null);
});

test('NP.F2: the editable leaves follow the piece, and the edit body carries only the changed lines', () => {
  const carousel = PACK.pieces[1];
  assert.ok(isEditablePath(carousel, 'slides[2].text'));
  assert.ok(!isEditablePath(carousel, 'slides[2].number'), "a slide's number is not copy");
  assert.ok(!isEditablePath(PACK.pieces[2], 'read_time_seconds'));
  assert.ok(isEditablePath(PACK.pieces[0], 'send_header.date'));
  const fields = pieceSections(PACK.pieces[0]).flatMap(s => s.fields);
  assert.deepEqual(editRequest('m', fields, { preview: 'It starts after the inquiry.', body: 'New body.' }), { body: { expected_manifest_hash: 'm', changes: { body: 'New body.' } } });
  assert.deepEqual(editRequest('m', fields, { preview: '  ' }), { error: 'Preview cannot be empty.' });
  assert.deepEqual(editRequest('m', fields, {}), { error: 'Nothing changed.' });
  assert.deepEqual(diffWords('a b c', 'a c d').map(p => p.kind), ['same', 'removed', 'same', 'added']);
});
