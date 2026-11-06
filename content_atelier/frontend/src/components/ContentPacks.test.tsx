import '../testing/setupDom';
import React, { act } from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { json, mount, stubFetch } from '../testing/dom';
import { renderScreen } from '../testing/render';
import { seed, shell } from '../testing/fixtures';
import { PACK, SUMMARY, piece } from '../testing/packFixtures';
import { createQueryClient, queryKey } from '../api/query';
import type { StoredPackV2 } from '../api/types';
import { ContentPacks, PackList } from './ContentPacks';
import { StateLine } from './packParts';
import { DELEGATED_LINE, PROVENANCE_LINE, STATE_LABELS, packPlainText, pieceMeta, piecePlainText, pieceSections, pieceTitle } from './packFields';

/* NP.F1, done when: unit tests render each piece kind with its labelled sections, the Copy and Copy all text, and each state
   with its chip and reason. Since the declutter (26 October) the page carries no provenance or delegation line. The packs are
   synthetic (packFixtures.ts). */

const texts = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
const detail = (pack: StoredPackV2 = PACK, url = '/studio/packs/pack_1') => renderScreen(<ContentPacks base="/studio/packs" />,
  { url, pattern: '/studio/packs/:packId', seed: [...shell({ packs: true }), seed('/packs/{pack_id}', { path: { pack_id: pack.pack_id } }, pack)] });
/** The markup of one piece's panel. */
const panel = (html: string, key: string) => {
  const start = html.indexOf(`id="pack-piece-panel-${key}"`);
  assert.ok(start > 0, `the ${key} panel is on the page`);
  const end = html.indexOf('id="pack-piece-panel-', start + 30);
  return html.slice(start, end > 0 ? end : undefined);
};

test('NP.F1: the pack opens with a tab list in the mock\'s order, with order badges, and one panel per piece', () => {
  const html = detail();
  assert.match(html, /role="tablist"[^>]*aria-label="Content pack pieces"/);
  const tabs = [...html.matchAll(/role="tab"[^>]*id="pack-piece-tab-(\w+)"/g)].map(m => m[1]);
  assert.deepEqual(tabs, ['email', 'carousel', 'reel_1', 'reel_2', 'reel_3']);
  const visible = texts(html);
  const labels = [...html.matchAll(/role="tab"[^>]*>([^<]+)</g)].map(m => m[1]);
  assert.deepEqual(labels, ['Email', 'Carousel', 'Reel 1', 'Reel 2', 'Reel 3'], 'pill tabs without ordinals');
  assert.match(html, /id="pack-piece-tab-email"[^>]*aria-selected="true"/);
  assert.match(html, /aria-controls="pack-piece-panel-email"/);
  // The other panels are in the page but hidden, so a draft in one survives switching tabs.
  assert.match(html, /id="pack-piece-panel-carousel"[^>]*hidden=""/);
  assert.ok(visible.includes('Why we read the reply first') && visible.includes('Copy all'));
});

test('NP.F1: the email renders Date, Send time and Recipients, every subject option best first, the preview and the email itself', () => {
  const email = texts(panel(detail(), 'email'));
  for (const text of ['Email', 'DATE', 'Tuesday 3 November', 'SEND TIME', '9:00 AM Eastern', 'RECIPIENTS', 'All subscribers', 'SUBJECT OPTIONS',
    'Subject 1 (best)', 'Why we read the reply first', 'Subject 2', 'The inquiry is only the start', 'Subject 3', 'Before we touch the ads', 'PREVIEW',
    'It starts after the inquiry.', 'Opening', 'Hi {{contact.first_name}},', 'Body', 'Every week a venue owner asks us for more leads.', 'Ending', 'Talk soon,'])
    assert.ok(email.toUpperCase().includes(text.toUpperCase()), text);
  for (const origin of ['Finished from the brief', 'Written by the system', "The brief's copy"]) assert.ok(!email.includes(origin), `no origin line: ${origin}`);
  // The three header fields share a three-column grid once the piece column is wide enough (a container query, N4); the rest span it.
  assert.match(panel(detail(), 'email'), /class="@container"><div class="grid grid-cols-1 gap-3 @lg:grid-cols-3"/);
  assert.match(panel(detail(), 'email'), /aria-label="Preview" class="[^"]*@lg:col-span-3/);
});

test('N4: in a third-width header tile the Edit and Copy links sit under the text, not over the heading', () => {
  // On a 1024-pixel screen the Recipients tile is about 140 pixels wide, and its heading ran under the links.
  const email = panel(detail(), 'email');
  const tile = (label: string) => {
    const start = email.indexOf(`aria-label="${label}"`);
    assert.ok(start > 0, label);
    return email.slice(start, email.indexOf('</section>', start));
  };
  for (const label of ['Date', 'Send time', 'Recipients']) {
    assert.doesNotMatch(tile(label), /absolute right-4/, `${label}: the links are in the flow`);
    assert.doesNotMatch(tile(label), /pr-24/, `${label}: no room is held for links over the heading`);
    assert.match(tile(label), /mt-1 flex items-center gap-3/, label);
    assert.ok(tile(label).indexOf('mt-1 flex items-center gap-3') > tile(label).indexOf('<p'), `${label}: the links come after the text`);
  }
  // A full-width one-line section (the preview) keeps its links on the heading row.
  assert.match(tile('Preview'), /absolute right-4 top-3/);
});

test('NP.F1: a story Reel, a b-roll Reel and the carousel render their own labelled sections', () => {
  const html = detail();
  const story = texts(panel(html, 'reel_1'));
  for (const text of ['Reel 1 · face to camera, story', 'The reply that lost the tour', 'Title', 'Cover', 'Cover: story', 'Alternate 1', 'First alternate cover for story',
    'Alternate 2', 'On-screen hook', 'Script', 'The ads were never the problem.', 'Caption', 'Hook', 'Most inquiries stall at the first reply.', 'Body', 'Ending',
    'Follow-up is part of the ad.', 'Caption ending without the offer', 'Personal lines', 'I still think about that call.'])
    assert.ok(story.includes(text), `story Reel: ${text}`);
  const broll = texts(panel(html, 'reel_3'));
  for (const text of ['Reel 3 · b-roll with on-screen text', 'Screens', 'Screen 1', 'Inquiries went up.', 'Screen 3', 'So we read the reply.']) assert.ok(broll.includes(text), `b-roll Reel: ${text}`);
  assert.ok(!broll.includes('Script'), 'a b-roll Reel has screens, not a script');
  const carousel = texts(panel(html, 'carousel'));
  for (const text of ['Carousel · 7 slides', 'When more inquiries are not enough', 'Slides', 'Slide 1', 'Slide 1, line one.', 'Slide 7', 'Caption']) assert.ok(carousel.includes(text), `carousel: ${text}`);
});

test('NP.F1: a piece the pack did not write says so, with its reason', () => {
  const pack = { ...PACK, pieces: PACK.pieces.map(p => p.key === 'reel_3' ? piece('reel_3', { origin: 'not_written', content: null, brief_copy: null,
    not_written_reason: 'The brief had no b-roll Reel and finishing was off, so this Reel was not written.' }) : p) };
  const reel = texts(panel(detail(pack), 'reel_3'));
  assert.ok(reel.includes('Not written') && reel.includes('The brief had no b-roll Reel and finishing was off'));
  assert.ok(piecePlainText(pack.pieces[4]).startsWith('5. Reel 3 · b-roll with on-screen text: Not written'));
});

test('NP.F1: Copy gives a piece in full and Copy all every piece in full, in tab order', () => {
  const email = piecePlainText(PACK.pieces[0]);
  assert.ok(email.startsWith('1. Email: Why we read the reply first'));
  for (const line of ['Date\nTuesday 3 November', 'Send time\n9:00 AM Eastern', 'Recipients\nAll subscribers', '1. Why we read the reply first\n2. The inquiry is only the start\n3. Before we touch the ads',
    'Preview\nIt starts after the inquiry.', 'Hi {{contact.first_name}},\n\nEvery week a venue owner', 'Talk soon,\nWhitney']) assert.ok(email.includes(line), line);
  const story = piecePlainText(PACK.pieces[2]);
  for (const line of ['3. Reel 1 · face to camera, story: The reply that lost the tour', 'Alternate 1: First alternate cover for story', 'Script\nThe ads were never the problem.',
    'Caption\nMost inquiries stall at the first reply.\n\nWe read the reply', 'Personal lines (for Whitney to keep or cut)\n1. I still think about that call.']) assert.ok(story.includes(line), line);
  const all = packPlainText(PACK);
  assert.ok(all.startsWith('CONTENT PACK: Why we read the reply first'));
  const order = ['1. Email', '2. Carousel', '3. Reel 1', '4. Reel 2', '5. Reel 3'].map(h => all.indexOf(h));
  assert.ok(order.every((at, i) => at > 0 && (i === 0 || at > order[i - 1])), 'every piece, in tab order');
  // Nothing is abbreviated: every line of every piece is in the text.
  for (const p of PACK.pieces) for (const s of pieceSections(p)) for (const f of s.fields) assert.ok(all.includes(f.text), `${p.key} ${f.path}`);
  assert.equal(pieceMeta(PACK.pieces[1]), 'Carousel · 7 slides');
  assert.equal(pieceTitle(PACK.pieces[0]), 'Why we read the reply first');
});

test('NP.F1: the Copy buttons put the piece, one line, or the whole pack on the clipboard', async t => {
  const copied: string[] = [];
  Object.defineProperty(navigator, 'clipboard', { value: { writeText: async (text: string) => { copied.push(text); } }, configurable: true });
  const network = stubFetch(() => json({ detail: 'Not found' }, 404));
  t.after(network.restore);
  const client = createQueryClient();
  for (const [route, args, data] of [...shell({ packs: true }), seed('/packs/{pack_id}', { path: { pack_id: 'pack_1' } }, PACK)]) client.setQueryData(queryKey(route as never, args), data);
  const ui = await mount(<ContentPacks base="/studio/packs" />, { url: '/studio/packs/pack_1', pattern: '/studio/packs/:packId', client });
  t.after(() => ui.unmount());
  const byLabel = (label: string) => ui.container.querySelector(`button[aria-label="${label}"]`);
  await ui.click(byLabel('Copy the whole pack, every piece in full'));
  assert.equal(copied.at(-1), packPlainText(PACK));
  assert.match(ui.text(), /Copied/);
  await ui.click(byLabel('Copy Email, every section'));
  assert.equal(copied.at(-1), piecePlainText(PACK.pieces[0]));
  await ui.click(byLabel('Copy Email: Subject 2'));
  assert.equal(copied.at(-1), 'The inquiry is only the start');
  await ui.click(byLabel('Copy Reel 1: Caption'));
  assert.equal(copied.at(-1), 'Most inquiries stall at the first reply.\n\nWe read the reply before we touch the ads. A couple who waits two days for an answer books someone else.\n\nFollow-up is part of the ad.');
});

test('NP.F1: the arrow keys, Home and End move between the pieces', async t => {
  const network = stubFetch(() => json({ detail: 'Not found' }, 404));
  t.after(network.restore);
  const client = createQueryClient();
  for (const [route, args, data] of [...shell({ packs: true }), seed('/packs/{pack_id}', { path: { pack_id: 'pack_1' } }, PACK)]) client.setQueryData(queryKey(route as never, args), data);
  const ui = await mount(<ContentPacks base="/studio/packs" />, { url: '/studio/packs/pack_1', pattern: '/studio/packs/:packId', client });
  t.after(() => ui.unmount());
  const key = async (name: string) => {
    const tab = ui.container.querySelector('[role="tab"][aria-selected="true"]')!;
    await act(async () => { tab.dispatchEvent(new window.KeyboardEvent('keydown', { key: name, bubbles: true })); });
  };
  const selected = () => ui.container.querySelector('[role="tab"][aria-selected="true"]')?.id;
  await key('ArrowRight');
  assert.equal(selected(), 'pack-piece-tab-carousel');
  assert.equal(document.activeElement?.id, 'pack-piece-tab-carousel', 'focus follows the selection');
  assert.ok(!ui.container.querySelector('#pack-piece-panel-carousel')!.hasAttribute('hidden'));
  assert.ok(ui.container.querySelector('#pack-piece-panel-email')!.hasAttribute('hidden'));
  await key('End');
  assert.equal(selected(), 'pack-piece-tab-reel_3');
  await key('ArrowRight');
  assert.equal(selected(), 'pack-piece-tab-email', 'it wraps around');
  await key('ArrowLeft');
  assert.equal(selected(), 'pack-piece-tab-reel_3');
  await key('Home');
  assert.equal(selected(), 'pack-piece-tab-email');
});

test('NP.F1: each state renders its chip and its reason in words', () => {
  const reasons: Record<string, string | null> = {
    finishing: 'Finishing the copy', waiting: 'The packs budget for this week is used up; it continues on Monday.', in_review: null,
    ready_to_publish: null, superseded: 'A newer version of this pack exists',
  };
  for (const [state, reason] of Object.entries(reasons)) {
    const html = renderToStaticMarkup(<StateLine pack={{ state: state as StoredPackV2['state'], state_reason: reason }} />);
    assert.match(html, new RegExp(`data-state="${state}"[^>]*>${STATE_LABELS[state as StoredPackV2['state']]}<`), state);
    const visible = texts(html);
    if (reason) assert.ok(visible.includes(reason), `${state} shows its reason`);
    else assert.ok(visible.length > STATE_LABELS[state as StoredPackV2['state']].length + 10, `${state} says what it means`);
  }
  // A failure shows its reason in words and folds the detail for the team away.
  const failed = renderToStaticMarkup(<StateLine pack={{ state: 'waiting', state_reason: 'A step failed and can be tried again: the model did not answer\nTraceback: provider timeout' }} />);
  assert.ok(texts(failed).includes('A step failed and can be tried again: the model did not answer') && failed.includes('Details for the team'));
  // On the page: a waiting pack shows its state and its reason in words, without the run's steps.
  const page = texts(renderScreen(<ContentPacks base="/studio/packs" />, { url: '/studio/packs/pack_1', pattern: '/studio/packs/:packId', seed: [...shell({ packs: true }),
    seed('/packs/{pack_id}', { path: { pack_id: 'pack_1' } }, { ...PACK, state: 'waiting', state_reason: 'The packs budget for this week is used up.' }),
    seed('/packs/{pack_id}/production', { path: { pack_id: 'pack_1' } }, { run_id: 'run_1', state: 'waiting', state_reason: null, costs: null,
      jobs: [{ job_id: 'j1', stage: 'pack_finish', status: 'waiting', current_message: 'Waiting for the weekly budget', error_summary: null, completed_units: null, total_units: null }] })] }));
  assert.ok(page.includes('Waiting') && page.includes('Waiting: the packs budget for this week is used up.'));
  assert.ok(!page.includes('Finishing the copy') && !page.includes('Waiting for the weekly budget'), 'no run steps on the page');
  // The hint for each state the page names.
  const hint = (state: StoredPackV2['state']) => texts(detail({ ...PACK, state, state_reason: null }));
  assert.ok(hint('in_review').includes('Mark each piece published or sent when it goes out.'));
  assert.ok(hint('ready_to_publish').includes('Mark each piece published or sent when it goes out.'));
  assert.ok(hint('finishing').includes('The pack is being written. This page updates by itself.'));
});

test('NP.F1 (R58, R55): the pack page carries no provenance or delegation line, delegated or not', () => {
  for (const pack of [PACK, { ...PACK, approval_delegated: true }, { ...PACK, provenance: { ...PACK.provenance!, approval_delegated: true } }] as StoredPackV2[]) {
    const page = texts(detail(pack));
    assert.ok(!page.includes(PROVENANCE_LINE) && !page.includes(DELEGATED_LINE) && !page.includes('under delegation'), 'no provenance line on the page');
    assert.ok(!page.includes('Details: how this pack was made') && !page.includes('wia-kb'), 'no "how this pack was made"');
  }
});

test('NP.F1: the library shows the packs grouped by week with one state filter; each card its state and pieces in plain words', () => {
  const list = (url: string, query: Record<string, unknown>, items = [SUMMARY]) => texts(renderScreen(<ContentPacks base="/studio/packs" />, { url, seed: [...shell({ packs: true }),
    seed('/packs', { query }, { items, total: items.length })] }));
  const allHtml = renderScreen(<ContentPacks base="/packs" />, { url: '/packs', seed: [...shell({ packs: true }),
    seed('/packs', { query: { limit: 20, offset: 0 } }, { items: [SUMMARY, { ...SUMMARY, pack_id: 'pack_2', title: 'Inquiry season', state: 'finishing', state_reason: 'Checking every statement against the call', open_findings: 0, open_notes: 0,
      pieces: SUMMARY.pieces.map(p => p.key === 'reel_3' ? { ...p, origin: 'not_written' as const } : p) }], total: 2 })] });
  const all = texts(allHtml);
  for (const text of ['Content Packs & Deliverable Scripts', '2 packs', 'All packs', 'Week of', 'Why we read the reply first', 'Generated', '1 Email', '1 Carousel', '3 Reels',
    'Inquiry season', 'Being written', 'Being written from the approved brief. This takes 5 to 10 minutes.', '2 Reels', 'Open pack →']) assert.ok(all.includes(text), text);
  assert.equal((allHtml.match(/<h2[^>]*>Week of [^<]+<\/h2>/g) ?? []).length, 1, 'one week heading for the two packs of one week');
  // The state in plain words (the owner, 26 October): no counts of findings and notes, no "0/5 published", no week picker or archived toggle.
  for (const removed of ['0/5 published', 'open finding', '1 line to fix', 'notes to check', 'Checking every statement against the call', 'Reel 3 (not written)', 'Show archived weeks', 'Refresh']) {
    assert.ok(!all.includes(removed), `not in the library: ${removed}`);
  }
  // The Weekly Studio's step shows the week's packs; the week reaches the API as week_id.
  const week = list('/studio/packs?week=week_2026-10-26', { week_id: 'week_2026-10-26', limit: 50, offset: 0 });
  assert.ok(week.includes('Why we read the reply first') && week.includes('Generated content packs'));
  assert.ok(!week.includes("week's plan and export"), 'no link to the week\'s plan and export on the step');
  assert.ok(list('/studio/packs?week=week_2026-10-26', { week_id: 'week_2026-10-26', limit: 50, offset: 0 }, []).includes('No packs for this week yet'));
});

test('saved approval-state links use the combined generated filter and show both kinds of finished pack', async t => {
  const network = stubFetch(url => {
    if (url.startsWith('/api/atelier/packs?')) {
      assert.equal(new URL(url, 'http://local.test').searchParams.get('state'), 'generated');
      return json({ items: [SUMMARY, { ...SUMMARY, pack_id: 'legacy_approved', state: 'ready_to_publish', title: 'An earlier approved pack' }], total: 2 });
    }
    return json({ detail: 'Not found' }, 404);
  });
  t.after(network.restore);
  const ui = await mount(<PackList base="/packs" />, { url: '/packs?state=ready_to_publish' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.match(ui.text(), /Why we read the reply first/);
  assert.match(ui.text(), /An earlier approved pack/);
  assert.doesNotMatch(ui.text(), /Ready to publish|In review/);
});

test('NP.F1: a pack of the earlier contract is not shown as a content pack', () => {
  const html = texts(detail({ ...PACK, contract_version: 'content_pack_v1' as never, pieces: undefined as never }));
  assert.ok(html.includes('made in an earlier format'));
});
