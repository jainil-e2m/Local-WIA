import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../testing/dom';
import { renderScreen } from '../testing/render';
import { seed, shell } from '../testing/fixtures';
import { EDITORIAL_BLOCKING, PACK, PACK_R2, piece } from '../testing/packFixtures';
import { createQueryClient, queryKey } from '../api/query';
import type { StoredPackV2 } from '../api/types';
import { ContentPacks } from './ContentPacks';
import { packWriteMessage } from './PackDetail';
import { choiceFor, editRequest, editorialText, keepRequest, pieceMeta, piecePlainText, reelDirection, reelKindWords, reelProduction, toCheck } from './packFields';

/* Round 2 on the pack page (WIA's feedback on the packs): Reel 1 is the central story and Reels 2 and 3 each have a premise of
   their own, said in the Reel's line with how it is made; "About this Reel" and the openings considered sit beside the copy,
   never in it; an editor's blocking finding is edited or kept with a reason, its craft notes are folded; an edit can say why;
   and what to check before publishing is one closed line under the pieces, its items marked done by an approver. */

const writes = (calls: { url: string; options?: RequestInit }[], method = 'POST') => calls.filter(c => c.options?.method === method);
const sent = (call: { options?: RequestInit }) => JSON.parse(String(call.options!.body));

async function openPack(t: { after: (fn: () => unknown) => void }, answer: (url: string, options?: RequestInit) => Response | undefined, pack: StoredPackV2 = PACK_R2) {
  const network = stubFetch((url, options) => answer(url, options) ?? (url === `/api/atelier/packs/${pack.pack_id}` ? json(pack) : json({ detail: 'Not found' }, 404)));
  t.after(network.restore);
  const client = createQueryClient();
  for (const [route, args, data] of [...shell({ packs: true }), seed('/packs/{pack_id}', { path: { pack_id: pack.pack_id } }, pack)]) client.setQueryData(queryKey(route as never, args), data);
  const ui = await mount(<ContentPacks base="/studio/packs" />, { url: `/studio/packs/${pack.pack_id}`, pattern: '/studio/packs/:packId', client });
  t.after(() => ui.unmount());
  const panel = (key: string) => ui.container.querySelector(`#pack-piece-panel-${key}`)!;
  const button = (text: string, within: Element = ui.container) => [...within.querySelectorAll<HTMLButtonElement>('button')]
    .find(b => (b.getAttribute('aria-label') ?? b.textContent?.trim()) === text && !b.closest('[hidden]')) ?? null;
  return { ui, network, panel, button };
}

test('Round 2: a new Reel reads "Reel 2 · Own premise · On-screen text"; an earlier Reel keeps its wording', () => {
  const [, , central, second, third] = PACK_R2.pieces;
  assert.equal(pieceMeta(central), 'Reel 1 · Central story · Face to camera');
  assert.equal(pieceMeta(second), 'Reel 2 · Own premise · On-screen text');
  assert.equal(pieceMeta(third), 'Reel 3 · Own premise · Face to camera');
  assert.equal(pieceMeta(PACK.pieces[2]), 'Reel 1 · face to camera, story');
  assert.equal(pieceMeta(PACK.pieces[4]), 'Reel 3 · b-roll with on-screen text');
  assert.equal(reelProduction(PACK.pieces[4]), 'on_screen_text', 'b-roll text is on-screen text');
  assert.equal(reelProduction(second), 'on_screen_text');
  assert.equal(reelKindWords('stance', 'face_to_camera'), 'face to camera, stance', 'an earlier kind is never given a production');
});

test('Round 2: the direction stays apart from the copy: Copy never carries the premise, takeaway or call times', () => {
  const second = PACK_R2.pieces[3];
  const direction = reelDirection(second)!;
  assert.equal(direction.premise, 'A slow reply tells a couple how the wedding day will feel.');
  assert.equal(reelDirection(PACK.pieces[2]), null, 'an earlier Reel has no premise');
  const copied = piecePlainText(PACK_R2.pieces[2]);
  for (const kept of ['A venue lost a tour', 'The reply is part of the ad.', 'It tells the story itself.', '4:12']) assert.ok(!copied.includes(kept), `not copied: ${kept}`);
  const choice = choiceFor(PACK_R2, 'email')!;
  assert.deepEqual(choice.options.map(o => o.chosen), [true, false, false]);
  assert.equal(choiceFor(PACK_R2, 'carousel'), null);
  // A chosen opening not among the considered ones is listed first.
  assert.deepEqual(choiceFor({ creative_choices: [{ piece: 'reel_1', considered: ['A', 'B'], chosen: 'C', why: 'w' }] }, 'reel_1')!.options.map(o => o.text), ['C', 'A', 'B']);
});

test('Round 2: "About this Reel" shows the premise, takeaway and why it differs, with the call times and the openings folded', async t => {
  const { ui, panel } = await openPack(t, () => undefined);
  await ui.click(ui.container.querySelector('#pack-piece-tab-reel_2'));
  const about = panel('reel_2').querySelector('section[aria-label="About this Reel"]')!;
  assert.ok(about, 'the Reel has its direction');
  const text = about.textContent ?? '';
  for (const line of ['A slow reply tells a couple how the wedding day will feel.', 'Takeaway · Speed reads as care.', "Why it's different · It is the couple's view, not the venue's."]) {
    assert.ok(text.includes(line), line);
  }
  const folds = [...about.querySelectorAll('details')];
  assert.deepEqual(folds.map(d => d.querySelector('summary')!.textContent!.replace('›', '').trim()), ['Where this comes from in the calls', 'Openings considered (2)']);
  assert.ok(folds.every(d => !d.hasAttribute('open')), 'both folds are closed');
  assert.match(folds[0].textContent ?? '', /11:05 – the strategist asks about replies/);
  assert.match(folds[1].textContent ?? '', /Chosen: A slow reply tells a couple how the day will feel\..*Owners answer on weekends too\..*Why this one · It gives the couple's view/);
  // The About block comes before the copy.
  const first = panel('reel_2').querySelector('section[aria-label]');
  assert.equal(first?.getAttribute('aria-label'), 'About this Reel');
  // The email has no About block, only its openings, folded under the header; the carousel has neither.
  assert.equal(panel('email').querySelector('section[aria-label="About this Reel"]'), null);
  assert.match(panel('email').querySelector('details')?.textContent ?? '', /^›Openings considered \(3\)/);
  assert.equal(panel('carousel').querySelector('details'), null);
  // The recorded take goes on a face-to-camera Reel 1 or 2, never on an on-screen-text one.
  assert.equal([...panel('reel_2').querySelectorAll('button')].find(b => b.textContent === 'Paste what you said'), undefined);
  assert.ok([...panel('reel_1').querySelectorAll('button')].some(b => b.textContent === 'Paste what you said'));
  // No internal words on the page.
  assert.doesNotMatch(ui.text(), /fidelity|editorial|premise_options|distinct_because|creative_choices|unsupported_causation/i);
});

test('Round 2: an editor\'s blocking finding is kept with a reason on the attestation route, and the confirmation says so', async t => {
  let kept = false;
  const after: StoredPackV2 = { ...PACK_R2, pack_id: 'pack_r3', manifest_hash: 'manifest_r3', ready_blockers: [],
    pieces: PACK_R2.pieces.map(p => p.key === 'reel_2' ? { ...p, findings: p.findings.map(f => f.finding_id === 'e1' ? { ...f, status: 'kept' as const, can_attest: false } : f) } : p) };
  const { ui, network, panel, button } = await openPack(t, (url, options) => {
    if (options?.method === 'POST' && url.endsWith('/findings/e1/attest')) { kept = true; return json({ pack_id: 'pack_r3', manifest_hash: 'manifest_r3', state: 'in_review', run_id: 'run_1' }); }
    if (url === '/api/atelier/packs/pack_r3' && kept) return json(after);
    return undefined;
  });
  await ui.click(ui.container.querySelector('#pack-piece-tab-reel_2'));
  const line = panel('reel_2').querySelector('[data-path="screens[0]"]')!;
  assert.match(line.textContent ?? '', /To resolve: "Inquiries went up\." states a cause the call does not show/, 'said where the line is, without the piece\'s name');
  assert.equal(button('It is true', line), null, 'an editor\'s finding is kept, not attested true');
  await ui.click(button('Keep it', line));
  const field = line.querySelector<HTMLInputElement>('input')!;
  assert.match(line.textContent ?? '', /Why is it fine as it is\?/);
  await ui.click(button('Confirm', line));
  assert.match(line.textContent ?? '', /Say why the line is fine as it is\./);
  assert.equal(writes(network.calls).length, 0, 'an empty reason is refused before anything is sent');
  await ui.type(field, 'The owner said so on the call.');
  await ui.click(button('Confirm', line));
  await ui.settle();
  const [attest] = writes(network.calls);
  assert.equal(attest.url, '/api/atelier/packs/pack_r2/findings/e1/attest');
  assert.deepEqual({ ...sent(attest), request_id: undefined }, { expected_manifest_hash: 'manifest_r2', statement: 'The owner said so on the call.', request_id: undefined });
  await ui.settle();
  assert.equal(ui.container.querySelector('[data-confirmation]')?.textContent, 'Kept, with your reason. The new version is open.');
  // The kept finding is no longer shown; the craft note stays folded.
  assert.doesNotMatch(panel('reel_2').textContent ?? '', /To resolve:/);
});

test('Round 2: an editor\'s craft notes are one closed line on the piece, each note one line', async t => {
  const { panel } = await openPack(t, () => undefined);
  const notes = [...panel('reel_2').querySelectorAll('details')].find(d => /Editor's notes/.test(d.querySelector('summary')?.textContent ?? ''))!;
  assert.ok(notes && !notes.hasAttribute('open'));
  assert.match(notes.querySelector('summary')!.textContent ?? '', /Editor's notes \(1\)/);
  assert.deepEqual([...notes.querySelectorAll('li')].map(li => li.textContent), ['"Follow-up is part of the ad." reads like a slogan rather than a real explanation']);
  // A warning is never shown as something to resolve.
  assert.doesNotMatch(panel('reel_2').querySelector('[data-path="caption.ending"]')?.textContent ?? '', /To resolve/);
});

test('Round 2: an edit can say why; the reason is sent with the edit, and left out when empty', async t => {
  const { ui, network, panel, button } = await openPack(t, (_url, options) => options?.method === 'PATCH'
    ? json({ pack_id: 'pack_r2', manifest_hash: 'manifest_r2', state: 'in_review', run_id: 'run_1' }) : undefined);
  await ui.click(button('Edit Email: Preview'));
  await ui.type(ui.container.querySelector<HTMLInputElement>('#pack-email-preview')!, 'The inquiry is where it starts.');
  const why = panel('email').querySelector<HTMLInputElement>('input[aria-label="Why this change? (optional, helps the system learn)"]')!;
  assert.ok(why, 'the save bar asks why');
  await ui.type(why, 'Shorter, and in her words.');
  await ui.click(button('Save 1 change'));
  await ui.settle();
  const [patch] = writes(network.calls, 'PATCH');
  assert.equal(sent(patch).reason, 'Shorter, and in her words.');
  assert.deepEqual(sent(patch).changes, { preview: 'The inquiry is where it starts.' });
  const fields = [{ path: 'preview', label: 'Preview', text: 'a', multiline: false }];
  assert.ok(!('reason' in (editRequest('m', fields, { preview: 'b' }, '  ') as { body: Record<string, unknown> }).body), 'no reason, no field');
  assert.ok('error' in editRequest('m', fields, { preview: 'b' }, 'x'.repeat(1001)));
});

test('Round 2: "Before publishing" is one closed line with its count; an approver marks a note done and a quote cleared', async t => {
  let step = 0;
  const done = { by: 'Whitney (approver)', at: '2026-10-27T10:00:00Z', delegated: false, reference: 'Email from the owner', note: null };
  const v2: StoredPackV2 = { ...PACK, pack_id: 'pack_2', manifest_hash: 'manifest_2', before_publishing: PACK.before_publishing.map(n => n.id === 'P1' ? { ...n, done } : n) };
  const v3: StoredPackV2 = { ...v2, pack_id: 'pack_3', manifest_hash: 'manifest_3', client_quotes: PACK.client_quotes.map(q => ({ ...q, cleared: done })) };
  const { ui, network, button } = await openPack(t, (url, options) => {
    if (options?.method === 'POST' && url.endsWith('/clearances')) { step += 1; return json({ pack_id: step === 1 ? 'pack_2' : 'pack_3', manifest_hash: 'm', state: 'in_review', run_id: 'run_1' }); }
    if (url === '/api/atelier/packs/pack_2') return json(v2);
    if (url === '/api/atelier/packs/pack_3') return json(v3);
    return undefined;
  }, PACK);
  const fold = () => ui.container.querySelector<HTMLDetailsElement>('details[aria-label="Before publishing"]')!;
  assert.equal(fold().querySelector('summary')!.textContent!.replace(/Show|Hide/g, '').trim(), 'Before publishing· 3 to check');
  assert.equal(toCheck(PACK), 3, 'two open notes and one quote to clear');
  const text = fold().textContent ?? '';
  for (const line of ['Confirm the client may be referenced in the story Reel.', 'Answer: It is open until December.', 'Client quotes to clear', '“We never answered on weekends.”',
    'the client · Reel 1', 'Also check', 'The stance Reel keeps the moment to two lines.', "Would be stronger with the client's permission"]) assert.ok(text.includes(line), line);
  fold().open = true;
  await ui.click(button('Mark done: Confirm the client may be referenced in the story Reel.'));
  await ui.type(fold().querySelector<HTMLInputElement>('input')!, 'Email from the owner');
  await ui.click(button('Mark done', fold()));
  await ui.settle();
  const [first] = writes(network.calls);
  assert.equal(first.url, '/api/atelier/packs/pack_1/clearances');
  assert.deepEqual({ ...sent(first), request_id: undefined }, { expected_manifest_hash: 'manifest_1', item_id: 'P1', reference: 'Email from the owner', note: null, request_id: undefined });
  await ui.settle();
  assert.equal(ui.container.querySelector('[data-confirmation]')?.textContent, 'Marked done.');
  assert.ok(fold().open, 'the list stays open in the new version');
  assert.match(fold().textContent ?? '', /Done by Whitney on Oct 27, 2026 · Email from the owner/);
  assert.match(fold().querySelector('summary')!.textContent ?? '', /2 to check/);
  await ui.click(button('Mark cleared: We never answered on weekends.'));
  await ui.click(button('Mark cleared', fold()));
  await ui.settle();
  assert.equal(sent(writes(network.calls)[1]).item_id, 'Q1');
  await ui.settle();
  assert.equal(ui.container.querySelector('[data-confirmation]')?.textContent, 'Marked cleared.');
  assert.match(fold().textContent ?? '', /Cleared by Whitney on Oct 27, 2026/);
  assert.match(fold().querySelector('summary')!.textContent ?? '', /1 to check/);
});

test('Round 2: only a person who can decide marks items done; with nothing left the line says "all done"', async t => {
  const reader: StoredPackV2 = { ...PACK, can_decide: false };
  const { ui, button } = await openPack(t, () => undefined, reader);
  assert.equal(button('Mark done: Confirm the client may be referenced in the story Reel.'), null);
  assert.equal(button('Mark cleared: We never answered on weekends.'), null);
  assert.ok(ui.text().includes('Confirm the client may be referenced in the story Reel.'), 'the notes are still listed');
  const finished = { by: 'a@example.invalid', at: '2026-10-27T10:00:00Z', delegated: false, reference: null, note: null };
  const all: StoredPackV2 = { ...PACK, before_publishing: PACK.before_publishing.map(n => ({ ...n, done: finished })), client_quotes: PACK.client_quotes.map(q => ({ ...q, cleared: finished })) };
  assert.equal(toCheck(all), 0);
  const html = renderScreen(<ContentPacks base="/studio/packs" />, { url: '/studio/packs/pack_1', pattern: '/studio/packs/:packId', seed: [...shell({ packs: true }), seed('/packs/{pack_id}', { path: { pack_id: 'pack_1' } }, all)] });
  assert.match(html, /Before publishing<span[^>]*>· all done<\/span>/);
  assert.match(html, /Done by the team on Oct 27, 2026/, 'an address is never shown: the team did it');
  // A pack with nothing to check has no line at all.
  const none = renderScreen(<ContentPacks base="/studio/packs" />, { url: '/studio/packs/pack_1', pattern: '/studio/packs/:packId', seed: [...shell({ packs: true }),
    seed('/packs/{pack_id}', { path: { pack_id: 'pack_1' } }, { ...PACK, before_publishing: [], client_quotes: [], pack_notes: [], stronger_with_permission: [] })] });
  assert.ok(!none.includes('Before publishing'));
});

test('Round 2: words for the writes and the findings, never the internal ones', () => {
  assert.equal(packWriteMessage('/packs/p/findings/e1/attest', 'POST', {}, false, PACK_R2), 'Kept, with your reason.');
  assert.equal(packWriteMessage('/packs/p/findings/f9/attest', 'POST', {}, false, PACK_R2), 'Attested.', 'a finding of the call is still attested');
  assert.equal(packWriteMessage('/packs/p/clearances', 'POST', { item_id: 'Q1' }, false, PACK), 'Marked cleared.');
  assert.equal(editorialText(EDITORIAL_BLOCKING, 'Reel 2'), '"Inquiries went up." states a cause the call does not show (the call never links the ads to the rise)');
  assert.deepEqual(keepRequest('m', ' '), { error: 'Say why the line is fine as it is.' });
  assert.deepEqual(keepRequest('m', ' It is in the call. '), { body: { expected_manifest_hash: 'm', statement: 'It is in the call.' } });
  // A recorded take still goes on Reels 1 and 2 only when they are face to camera.
  const onScreen = piece('reel_2', { kind: 'second', content: { ...PACK_R2.pieces[3].content } });
  assert.equal(reelProduction(onScreen), 'on_screen_text');
});
