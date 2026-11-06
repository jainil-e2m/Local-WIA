import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../testing/dom';
import { renderScreen, type Seeded } from '../testing/render';
import { ME_APPROVER, seed, shell } from '../testing/fixtures';
import { BRIEF_V4, BRIEF_V4_APPROVED, PACK, SUMMARY, piece, version } from '../testing/packFixtures';
import { createQueryClient, queryKey } from '../api/query';
import type { StoredBriefV4, StoredPackV2 } from '../api/types';
import { ContentPacks } from './ContentPacks';
import { SQLBriefs } from './SQLBriefs';
import { BriefGateV4, DRAFT_COPY_NOTE } from './BriefReaderV4';

/* NP.F3, done when: Ready is blocked with a named reason until open findings are resolved; before-publishing notes show on
   the pack and never block Ready; approving a brief links to its pack. With them: attesting a finding, marking a note done,
   Finish again (confirmed first), marking a piece published, and the Gate 2 side of the hand-over (the button's words, the
   draft label, Create content pack, the brief page's capture hidden once a pack exists). */

const texts = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
type Answer = (url: string, options?: RequestInit) => Response | undefined;
const writes = (calls: { url: string; options?: RequestInit }[], method = 'POST') => calls.filter(c => c.options?.method === method);
const sent = (call: { options?: RequestInit }) => JSON.parse(String(call.options!.body));

async function openPack(t: { after: (fn: () => unknown) => void }, answer: Answer, pack: StoredPackV2 = PACK) {
  const network = stubFetch((url, options) => answer(url, options) ?? (url === `/api/atelier/packs/${pack.pack_id}` ? json(pack) : json({ detail: 'Not found' }, 404)));
  t.after(network.restore);
  const client = createQueryClient();
  for (const [route, args, data] of [...shell({ packs: true }), seed('/packs/{pack_id}', { path: { pack_id: pack.pack_id } }, pack)]) client.setQueryData(queryKey(route as never, args), data);
  const ui = await mount(<ContentPacks base="/studio/packs" />, { url: `/studio/packs/${pack.pack_id}`, pattern: '/studio/packs/:packId', client });
  t.after(() => ui.unmount());
  const review = () => ui.container.querySelector('aside[aria-label="Review the pack"]')!;
  const button = (text: string, within: Element = ui.container) => [...within.querySelectorAll<HTMLButtonElement>('button')]
    .find(b => (b.getAttribute('aria-label') ?? b.textContent?.trim()) === text && !b.closest('[hidden]')) ?? null;
  return { ui, network, review, button };
}

const BLOCKED: StoredPackV2 = {
  ...PACK,
  pieces: PACK.pieces.map(p => p.key === 'reel_3' ? piece('reel_3', { origin: 'written', brief_copy: null, findings: [{
    finding_id: 'f1', source: 'fidelity', piece: 'reel_3', path: 'screens[1]', sentence: 'Tours did not.', severity: 'blocking',
    message: 'The call does not say tours stayed flat: edit the sentence or attest it is true.', status: 'open', resolution: null, can_attest: true }] }) : p),
  ready_blockers: ['Reel 3: the call does not say tours stayed flat. Edit the sentence or attest it is true.'],
};
const ready = (within: Element) => [...within.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent?.trim() === 'Ready to publish') ?? null;

test('publication: content checks remain editable without a whole-pack approval step', async t => {
  const edited: StoredPackV2 = version('pack_2', { ready_blockers: [], pieces: BLOCKED.pieces.map(p => p.key === 'reel_3'
    ? { ...p, content: { ...p.content!, screens: ['Her inquiries were up.', 'Tours stayed where they were.'] }, findings: [] } : p) });
  let decided = false;
  const { ui, network, button } = await openPack(t, (url, options) => {
    if (options?.method === 'PATCH' && url.endsWith('/pieces/reel_3')) return json({ pack_id: 'pack_2', manifest_hash: 'manifest_pack_2', state: 'in_review', run_id: 'run_1' });
    if (options?.method === 'POST' && url.endsWith('/decision')) { decided = true; return json({ pack_id: 'pack_2', manifest_hash: 'manifest_pack_2', state: 'ready_to_publish', run_id: 'run_1' }); }
    if (url === '/api/atelier/packs/pack_2') return json(decided ? { ...edited, state: 'ready_to_publish', approval_status: 'approved', approved_by: 'whitney@example.invalid' } : edited);
    return undefined;
  }, BLOCKED);
  assert.equal(ready(ui.container), null, 'pack approval has been retired');
  assert.ok(button('Mark as Published'), 'manual recording remains available independently of checks');
  const box = () => ui.container.querySelector('[aria-label="Content checks"]');
  assert.match(box()?.textContent ?? '', /Content checks to review:Reel 3: the call does not say tours stayed flat\. Edit the sentence or attest it is true\./);
  const reel = () => ui.container.querySelector('#pack-piece-panel-reel_3')!;
  assert.match(reel().querySelector('[data-path="screens[1]"]')?.textContent ?? '', /To resolve: /, 'the line that blocks says so where it is');
  assert.equal(button('Attest it is true'), null, 'the review panel is gone from the page');
  await ui.click(ui.container.querySelector('#pack-piece-tab-reel_3'));
  await ui.click(reel().querySelector<HTMLButtonElement>('[data-path="screens[1]"] button[aria-label^="Edit "]'));
  await ui.type(reel().querySelector<HTMLInputElement>('[data-path="screens[1]"] input, [data-path="screens[1]"] textarea')!, 'Tours stayed where they were.');
  await ui.click(button('Save 1 change'));
  await ui.settle();
  const [patch] = writes(network.calls, 'PATCH');
  assert.equal(patch.url, '/api/atelier/packs/pack_1/pieces/reel_3');
  assert.deepEqual(sent(patch).changes, { 'screens[1]': 'Tours stayed where they were.' });
  assert.equal(sent(patch).expected_manifest_hash, 'manifest_1');
  await ui.settle();
  assert.equal(box(), null, 'resolved checks disappear');
  assert.ok(button('Mark as Published'), 'the action follows the selected Reel after the edit');
  assert.equal(writes(network.calls).filter(call => call.url.endsWith('/decision')).length, 0, 'no pack decision is sent');
  assert.match(ui.text(), /Mark each piece published or sent when it goes out\./);
  assert.equal(ready(ui.container), null);
  assert.doesNotMatch(ui.text(), /whitney@example.invalid/, 'a person, never an address');
  assert.equal(button('Back to review'), null);
});

test('NP.F3: the pack page is the title, its week, Copy all and the one next step, then the pieces; the review panel is gone', async t => {
  const { ui, button } = await openPack(t, () => undefined);
  const words = texts(ui.container.innerHTML);
  for (const text of ['Why we read the reply first', 'WARM · Week of', 'Copy all', 'Mark as Published', 'Generated',
    'Mark each piece published or sent when it goes out.', 'Email', 'Carousel', 'Reel 1', 'Reel 2', 'Reel 3']) {
    assert.ok(words.includes(text), text);
  }
  assert.match(ui.container.querySelector('a[href="/studio/packs"]')?.textContent ?? '', /^←\s+Content packs$/, 'the quiet way back to the library');
  const tabs = [...ui.container.querySelectorAll('[role="tab"]')].map(tab => tab.textContent);
  assert.deepEqual(tabs, ['Email', 'Carousel', 'Reel 1', 'Reel 2', 'Reel 3'], 'pill tabs without ordinals');
  assert.equal(ui.container.querySelector('aside[aria-label="Review the pack"]'), null);
  // What to check before publishing is one closed line under the pieces (Round 2); the review panel's other parts stay off the page.
  const fold = ui.container.querySelector('details[aria-label="Before publishing"]')!;
  assert.ok(fold && !fold.hasAttribute('open'), 'the before-publishing list is closed until opened');
  assert.equal(texts(fold.querySelector('summary > span')!.innerHTML).trim(), 'Before publishing · 3 to check');
  const outside = texts(ui.container.innerHTML.replace(fold.outerHTML, ''));
  for (const removed of ['Confirm the client may be referenced in the story Reel.', 'We never answered on weekends.', 'Naming the venue would make the story Reel concrete.']) {
    assert.ok(!outside.includes(removed), `only in the fold: ${removed}`);
  }
  for (const removed of ['Stronger with permission', 'Checks to consider', 'Notes from the system',
    'Finish again', 'Versions (', 'Details: how this pack was made', 'Written by the system', 'under delegation', 'Finished from the brief', 'approver@example.invalid']) {
    assert.ok(!words.includes(removed), `not on the pack page: ${removed}`);
  }
  assert.equal(button('Finish again'), null);
  assert.ok(button('Mark as Published') && !button('Mark as Published')!.disabled, 'open notes do not prevent recording actual publication');
  assert.equal(ui.container.querySelector('[aria-label="What stops Ready"]'), null);
});

test('publication: legacy approved packs use the same per-piece action without Back to review', async t => {
  const { ui, button } = await openPack(t, () => undefined, { ...PACK, state: 'ready_to_publish', approval_status: 'approved' });
  assert.equal(ready(ui.container), null, 'Ready is the in-review step only');
  assert.equal(button('Back to review'), null);
  assert.ok(button('Mark as Published'));
  assert.match(ui.text(), /Mark each piece published or sent when it goes out\./);
  await ui.click(button('Edit Email: Preview'));
  await ui.type(ui.container.querySelector<HTMLInputElement>('#pack-email-preview')!, 'The inquiry is where it starts.');
  assert.match(ui.text(), /1 line changed\. Saving creates a new version\./);
});

test('NP.F3: a piece is marked published with its date, channel and final text, prefilled with its copy, and the mark shows on the piece', async t => {
  let published = false;
  const { ui, network, button } = await openPack(t, (url, options) => {
    if (options?.method === 'POST' && url.endsWith('/pieces/email/published')) { published = true; return json({ pack_id: 'pack_1', piece: 'email', content_id: 'content_1', state: 'in_review' }); }
    if (url === '/api/atelier/packs/pack_1' && published) return json({ ...PACK, pieces: PACK.pieces.map(p => p.key === 'email' ? { ...p, published: [{ content_id: 'content_1', piece: 'email', channel: 'email',
      published_on: '2026-11-03', url: null, by: 'whitney@example.invalid', at: '2026-11-03T15:00:00Z' }] } : p) });
    return undefined;
  });
  const email = () => ui.container.querySelector('#pack-piece-panel-email')!;
  await ui.click(button('Mark as Published'));
  const form = document.querySelector('form[aria-label="Mark Email sent"]')!;
  const dialogButton = (text: string) => [...form.querySelectorAll('button')].find(button => button.textContent === text) ?? null;
  const finalText = form.querySelector('textarea')!;
  assert.match(finalText.value, /Subject options \(best first\)\n1\. Why we read the reply first/);
  assert.match(finalText.value, /Every week a venue owner asks us for more leads\./);
  assert.equal(form.querySelector('select')!.value, 'email');
  await ui.type(form.querySelector<HTMLInputElement>('input[inputmode="url"]')!, 'not a link');
  await ui.click(dialogButton('Confirm Sent'));
  assert.match(form.textContent ?? '', /full web address/);
  assert.equal(writes(network.calls).length, 0);
  await ui.type(form.querySelector<HTMLInputElement>('input[inputmode="url"]')!, '');
  await ui.click(dialogButton('Confirm Sent'));
  await ui.settle();
  const [mark] = writes(network.calls);
  assert.equal(mark.url, '/api/atelier/packs/pack_1/pieces/email/published');
  assert.deepEqual({ ...sent(mark), published_on: undefined, final_text: undefined, request_id: undefined }, { published_on: undefined, channel: 'email', url: null, final_text: undefined, request_id: undefined });
  assert.match(sent(mark).final_text, /Talk soon,\nWhitney/);
  await ui.settle();
  assert.match(email().textContent ?? '', /Sent Nov 3, 2026 · Email/);
  assert.match(email().textContent ?? '', /Manually marked · Not verified on platform/);
  assert.doesNotMatch(email().textContent ?? '', /marked by|whitney@example\.invalid/, 'no marker named on the piece');
});

// ---- the Gate 2 hand-over ----

function briefClient(brief: unknown, extra: Seeded[] = [], me: unknown = ME_APPROVER) {
  const client = createQueryClient();
  for (const [route, args, data] of [...shell({ briefs: true, packs: true }, me), seed('/briefs', { query: { limit: 20, offset: 0 } }, { items: [brief], total: 1, limit: 20, offset: 0 }),
    seed('/briefs/{brief_id}', { path: { brief_id: 'brief_v4' } }, brief), ...extra]) client.setQueryData(queryKey(route as never, args), data);
  return client;
}

test('NP.F3: approving a v4 brief says it creates the content pack, and the brief then links to the pack it started', async t => {
  let approved = false;
  const network = stubFetch((url, options) => {
    if (options?.method === 'POST' && url === '/api/atelier/briefs/brief_v4/decision') {
      approved = true;
      return json({ brief_id: 'brief_v4', content_hash: 'h4', approval_status: 'approved', decision_id: 'decision_1',
        pack_run: { pack_id: 'pack_9', run_id: 'run_9', status: 'queued', mode: 'replay', error: null }, pack_note: null });
    }
    if (url === '/api/atelier/briefs/brief_v4') return json(approved ? BRIEF_V4_APPROVED : BRIEF_V4);
    if (url.startsWith('/api/atelier/packs?')) return json({ items: [], total: 0 });
    return json({ detail: 'Not found' }, 404);
  });
  t.after(network.restore);
  const ui = await mount(<SQLBriefs />, { url: '/studio/briefs/brief_v4', pattern: '/studio/briefs/:briefId', client: briefClient(BRIEF_V4) });
  t.after(() => ui.unmount());
  // No hand-over sentence and no draft label on the page: the button says what follows.
  assert.doesNotMatch(ui.text(), /Approving this brief creates its content pack/);
  assert.ok(!ui.text().includes(DRAFT_COPY_NOTE));
  const approve = [...ui.container.querySelectorAll('button')].find(b => b.textContent === 'Approve brief and create content pack');
  assert.ok(approve && !approve.hasAttribute('disabled'), 'the approve button says it creates the pack');
  await ui.click(approve);
  await ui.settle();
  await ui.settle();
  assert.equal(writes(network.calls)[0].url, '/api/atelier/briefs/brief_v4/decision');
  assert.ok(network.calls.some(c => c.url === '/api/atelier/packs?brief_id=brief_v4&limit=5'), 'the brief looks for its pack');
  const link = ui.container.querySelector<HTMLAnchorElement>('a[href="/studio/packs/pack_9"]');
  assert.ok(link, 'the brief links to the pack the approval started');
  assert.equal(link.textContent, 'Open the content pack');
  assert.match(ui.text(), /The content pack is being made from this brief/);
});

test('NP.F3: on a reload the approved brief with a pack shows no pack box and no published capture; without one it offers to create it', () => {
  const page = (packs: unknown[], me: unknown = ME_APPROVER) => texts(renderScreen(<SQLBriefs />, { url: '/studio/briefs/brief_v4', pattern: '/studio/briefs/:briefId',
    seed: [...shell({ briefs: true, packs: true }, me), seed('/briefs', { query: { limit: 20, offset: 0 } }, { items: [BRIEF_V4_APPROVED], total: 1, limit: 20, offset: 0 }),
      seed('/briefs/{brief_id}', { path: { brief_id: 'brief_v4' } }, BRIEF_V4_APPROVED), seed('/packs', { query: { brief_id: 'brief_v4', limit: 5 } }, { items: packs, total: packs.length })] }));
  const withPack = page([SUMMARY]);
  assert.ok(withPack.includes('Why we read the reply first') && withPack.includes('Download the brief'));
  // Once the pack exists it is one tab away ("Content Pack"); the brief page has no box or sentence about it.
  for (const removed of ['Approved. Its content pack is below.', 'Open the content pack', 'No content pack yet.', 'Open the approved card', 'notes to check']) {
    assert.ok(!withPack.includes(removed), `not on the brief page: ${removed}`);
  }
  assert.ok(!withPack.includes('What was published from this brief'), 'the brief page no longer records published pieces once a pack exists');
  assert.ok(!withPack.includes('Create content pack'));
  assert.ok(!/version 1 briefs only|Generate saved content pack/.test(withPack), 'the v1 hand-off is gone');
  // No pack yet: a person who may create packs can create one; the brief's capture is still offered.
  const without = page([]);
  assert.ok(without.includes('No content pack yet.') && without.includes('Create content pack') && without.includes('What was published from this brief'));
  const viewer = { ...ME_APPROVER, can: { ...ME_APPROVER.can, generate_packs: false } };
  assert.ok(!page([], viewer).includes('Create content pack'), 'only people who may create packs see the button');
});

test('NP.F3: Create content pack posts the approved brief with its hash and opens the pack', async t => {
  const network = stubFetch((url, options) => {
    if (options?.method === 'POST' && url === '/api/atelier/briefs/brief_v4/pack') return json({ pack_id: 'pack_7', run_id: 'run_7', status: 'queued', mode: 'replay', error: null }, 202);
    if (url.startsWith('/api/atelier/packs?')) return json({ items: [], total: 0 });
    if (url === '/api/atelier/packs/pack_7') return json(version('pack_7', { state: 'finishing', run_active: true }));
    return json({ detail: 'Not found' }, 404);
  });
  t.after(network.restore);
  const client = briefClient(BRIEF_V4_APPROVED, [seed('/packs', { query: { brief_id: 'brief_v4', limit: 5 } }, { items: [], total: 0 })]);
  const ui = await mount(<SQLBriefs />, { url: '/studio/briefs/brief_v4', pattern: '/studio/briefs/:briefId', client });
  t.after(() => ui.unmount());
  await ui.click([...ui.container.querySelectorAll('button')].find(b => b.textContent === 'Create content pack') ?? null);
  await ui.settle();
  const [create] = writes(network.calls);
  assert.equal(create.url, '/api/atelier/briefs/brief_v4/pack');
  assert.equal(sent(create).expected_brief_hash, 'h4');
  assert.match(sent(create).request_id, /^[0-9a-f-]{36}$/);
});

test('NP.F3: with packs on, Gate 2 shows a v4 brief\'s plan without the draft copy, and the approve button says what follows', () => {
  const brief = BRIEF_V4 as unknown as StoredBriefV4;
  const on = texts(renderScreen(<BriefGateV4 brief={brief} busy={false} perform={async () => {}} packsEnabled />));
  assert.ok(!on.includes('Draft copy:') && !on.includes('DATE: '), 'with packs on, the draft copy and its label are not shown: the pack holds the copy');
  assert.ok(on.includes('Format and creative approach') && on.includes('Approve brief and create content pack'));
  const off = texts(renderScreen(<BriefGateV4 brief={brief} busy={false} perform={async () => {}} />));
  assert.ok(!off.includes('Draft copy:') && off.includes('Approve the brief') && !off.includes('create content pack'));
});
