import '../testing/setupDom';
import React, { act, useState } from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch, type Mounted } from '../testing/dom';
import { renderScreen } from '../testing/render';
import { BRIEF_V2, INTAKE_OVERVIEW, ME_APPROVER, REVIEW, WEEK, seed, shell } from '../testing/fixtures';
import { PACK, piece, version } from '../testing/packFixtures';
import { createQueryClient, queryKey } from '../api/query';
import type { StoredPackV2 } from '../api/types';
import { SQLWeeklyAngles, angleWriteMessage, latestVersion } from './SQLWeeklyAngles';
import { SQLBriefs, briefWriteMessage } from './SQLBriefs';
import { ContentPacks } from './ContentPacks';
import { packWriteMessage, packWriteTarget } from './PackDetail';
import { CardReview, CardWeekPanel } from './CardReview';
import { BriefReaderV2 } from './BriefReaderV2';
import { BriefFieldEditor } from './BriefEditing';
import { HistoryDrawer } from './ContextKnowledge';
import { IntakeView } from './IntakeView';
import { CopyButton } from './packParts';
import type { Card, CardSelection, StoredAngle } from '../api/types';

/* 6.F6, done when: on both gates and the pack screens, focus lands somewhere sensible after every write and the result is
   said in a polite live region; a control that swaps itself for a form moves focus into it and back; the confirmation and
   the two drawers keep focus inside and give it back; radio groups are grouped and named; and no state rests on colour. */

type T = { after: (fn: () => unknown) => void };
const buttonNamed = (root: Element, name: string) => [...root.querySelectorAll<HTMLButtonElement>('button')]
  .find(b => (b.getAttribute('aria-label') ?? b.textContent?.trim()) === name && !b.closest('[hidden]')) ?? null;
const live = (ui: Mounted) => ui.container.querySelector('[data-live-region]')?.textContent ?? '';
const focusKeyOf = () => (document.activeElement as HTMLElement | null)?.getAttribute('data-focus-key');
const key = async (name: string, shiftKey = false) => {
  await act(async () => { (document.activeElement ?? document.body).dispatchEvent(new window.KeyboardEvent('keydown', { key: name, shiftKey, bubbles: true, cancelable: true })); });
};
/** jsdom lays nothing out, so every element reports no boxes; the dialogs' Tab order skips elements without boxes. */
function laidOut(t: T) {
  const original = window.Element.prototype.getClientRects;
  window.Element.prototype.getClientRects = function () { return [{}] as unknown as DOMRectList; };
  t.after(() => { window.Element.prototype.getClientRects = original; });
}

// ---- Gate 1

const CARD = {
  rank: 1, title: 'Why we read your thank-you emails first', pillar: 'WARM', content_type: 'behind_the_scenes', audience: 'Venue owners',
  core_perspective: 'How WIA learns a business before it advertises it.', why_it_matters: 'Couples book on feeling.', wia_in_action: 'Asked about winter tastings.',
  offer_connection: null, moment_ids: ['moment_a'], evidence_points: ['A question about the calendar.'], verify_before_publishing: [],
  why_selected: 'Shows the WIA move.', series: null,
};
const ANGLE = {
  angle_id: 'angle_card', run_id: 'run_1', content_hash: 'hash_1', moment_ids: ['moment_a'], has_replacement: false, workflow: null, supersedes_id: null,
  content_body: { card: CARD, title: CARD.title, argument: '', audience: '', tension: '', take: '', mechanism: '', reader_decision: '', qualifiers: [], risks: [], source_assertions: [], inference: null },
  base_score: null, adjusted_score: null, selection_status: 'visible', approval_status: 'pending', first_generated_at: '2026-10-08T11:28:56Z', selected_cta: null,
  matching_result: { status: 'complete', current_batch_flags: [] }, disposition: null, hold: null, can_approve: true, can_edit: true, can_reject: true,
};
const SELECTION = {
  run_id: 'run_1', week_summary: 'One call.', selection_hash: 'sel', ranking: [], unreferenced_moment_ids: [], internal_insights: [],
  considered_not_selected: [{ index: 0, moment_ids: ['moment_a'], idea: 'Negative keyword tips', reason: 'Too narrow.', disposition: null }],
};

test('6.F6: after a Gate 1 decision focus moves to the heading of the card\'s new version, and the result is said', async t => {
  const before = { ...REVIEW, angles: [ANGLE], selection: SELECTION, roster: [], runs: [] };
  const after = { ...before, angles: [{ ...ANGLE, content_hash: 'hash_2', approval_status: 'rejected', disposition: { disposition: 'skip', reason_code: 'timing', author: 'approver@example.invalid' } }] };
  let review: unknown = before;
  const client = createQueryClient();
  for (const [route, args, data] of [...shell(), seed('/weeks/{week_id}', { path: { week_id: WEEK.week_id } }, before), seed('/seeds', { query: { status: 'open' } }, [])]) client.setQueryData(queryKey(route as never, args), data);
  const network = stubFetch((url, options) => {
    if (options?.method === 'POST') { review = after; return json({ ok: true }); }
    return url.includes('/me') ? json(ME_APPROVER) : url.includes('/seeds') ? json([]) : url.endsWith('/weeks') ? json([WEEK]) : url.includes('/weeks/') ? json(review) : json([]);
  });
  t.after(network.restore);
  const ui = await mount(<SQLWeeklyAngles />, { url: `/studio/angles/${WEEK.week_id}/angle_card`, pattern: '/studio/angles/:weekId/:angleId', client });
  t.after(() => ui.unmount());
  const article = ui.container.querySelector('#angle-angle_card')!;
  await ui.tick([...article.querySelectorAll('label')].find(l => l.textContent === 'Skip')!.querySelector('input')!);
  await ui.choose([...article.querySelectorAll('label')].find(l => l.textContent?.startsWith('Reason'))!.querySelector('select')!, 'timing');
  const save = buttonNamed(article, 'Save decision')!;
  save.focus();
  await ui.click(save);
  await ui.settle();
  assert.ok(network.calls.some(c => c.options?.method === 'POST' && c.url.endsWith('/angles/angle_card/decision')), 'the decision was sent');
  assert.equal(focusKeyOf(), 'angle:angle_card:hash_2', 'focus is on the heading of the version the decision made');
  assert.equal(document.activeElement?.textContent, CARD.title);
  assert.equal(live(ui), 'Decision saved.');
  assert.ok(!buttonNamed(ui.container, 'Save decision'), 'the old form is gone');
});

test('6.F6: a Gate 1 write names the new version of an edited card, and says what it did in words', () => {
  const angles = [{ angle_id: 'a1', supersedes_id: null, content_hash: 'h1' }, { angle_id: 'a2', supersedes_id: 'a1', content_hash: 'h2' }, { angle_id: 'a3', supersedes_id: 'a2', content_hash: 'h3' }];
  assert.equal(latestVersion(angles, 'a1')?.angle_id, 'a3', 'an edit of an edit is followed to the newest');
  assert.equal(latestVersion(angles, 'a3')?.angle_id, 'a3');
  assert.equal(latestVersion(angles, 'gone'), null);
  // The week lists a replaced version only if the strategist chose it: the dialog still finds its way to what replaced it.
  assert.equal(latestVersion(angles.filter(a => a.angle_id !== 'a1'), 'a1')?.angle_id, 'a3', 'a version that left the list leads to its replacement');
  assert.equal(angleWriteMessage('/angles/a1', 'PATCH'), 'Saved as a new version of the card.');
  assert.equal(angleWriteMessage('/angles/a1/refresh'), 'Refresh started. The new version shows here in about a minute.');
  assert.match(angleWriteMessage('/weeks/w/considered/0/revive'), /^Revived as a card/);
  assert.equal(angleWriteMessage('/weeks/w/considered/0/decision'), 'Decision saved.');
  assert.equal(briefWriteMessage('/briefs/b/decision', 'POST', { decision: 'approved' }), 'Brief approved.');
  assert.equal(briefWriteMessage('/briefs/b/decision', 'POST', { decision: 'rejected' }), 'Brief rejected.');
  assert.equal(briefWriteMessage('/briefs/b', 'PATCH'), 'Saved as a new version of the brief.');
  assert.equal(packWriteMessage('/packs/p/pieces/email', 'PATCH', {}, true), 'Saved. The new version is open.');
  assert.equal(packWriteMessage('/packs/p/clearances', 'POST', { item_id: 'P1' }, false), 'Marked done.');
  assert.equal(packWriteTarget('/packs/p/pieces/reel_1/revert', {}, 'p2'), '[data-focus-key="pack:p2:piece:reel_1"]');
  assert.equal(packWriteTarget('/packs/p/clearances', { item_id: 'Q1' }, 'p'), '[data-focus-key="pack:p:done:Q1"]');
  assert.equal(packWriteTarget('/packs/p/finish', {}, 'p3'), '[data-focus-key="pack:p3:title"]');
});

test('6.F6: "Revive as a card" and "Record a decision" say whether their form is open', async t => {
  const ui = await mount(<CardWeekPanel weekId="w" selection={SELECTION as unknown as CardSelection} cards={[]} roster={[]} busy={false} perform={async () => true} />);
  t.after(() => ui.unmount());
  const revive = buttonNamed(ui.container, 'Revive as a card')!, record = buttonNamed(ui.container, 'Record a decision')!;
  assert.equal(revive.getAttribute('aria-expanded'), 'false');
  assert.equal(record.getAttribute('aria-expanded'), 'false');
  await ui.click(revive);
  assert.equal(revive.getAttribute('aria-expanded'), 'true');
  assert.ok(ui.container.querySelector(`#${revive.getAttribute('aria-controls')}`), 'it names the form it opened');
  await ui.click(record);
  assert.equal(revive.getAttribute('aria-expanded'), 'false');
  assert.equal(record.getAttribute('aria-expanded'), 'true');
});

test('6.F6: the reframe question is a named group with a legend', async t => {
  const ui = await mount(<CardReview angle={ANGLE as unknown as StoredAngle} card={CARD as unknown as Card} roster={[]} busy={false} perform={async () => true} />);
  t.after(() => ui.unmount());
  await ui.tick([...ui.container.querySelectorAll('label')].find(l => l.textContent === 'Reframe')!.querySelector('input')!);
  const group = [...ui.container.querySelectorAll('fieldset')].find(f => f.querySelector(':scope > legend')?.textContent === 'Is the central point the same?');
  assert.ok(group, 'the question is the legend of its own fieldset');
  const radios = [...group.querySelectorAll<HTMLInputElement>('input[type="radio"]')];
  assert.equal(radios.length, 2);
  assert.ok(radios.every(r => r.name === 'central-point-angle_card'), 'both answers share one name');
});

// ---- Gate 2

test('6.F6: after a Gate 2 write focus moves to the status line of the brief\'s new version, and the result is said', async t => {
  const BRIEF = { ...BRIEF_V2, can_review: true, can_approve: false };
  let current: unknown = BRIEF;
  const client = createQueryClient();
  for (const [route, args, data] of [...shell({ briefs: true }), seed('/briefs', { query: { limit: 20, offset: 0 } }, { items: [BRIEF], total: 1, limit: 20, offset: 0 }),
    seed('/briefs/{brief_id}', { path: { brief_id: 'brief_1' } }, BRIEF)]) client.setQueryData(queryKey(route as never, args), data);
  const network = stubFetch((url, options) => {
    if (options?.method === 'POST' && url.endsWith('/briefs/brief_1/review')) { current = { ...BRIEF, content_hash: 'h2' }; return json({ brief_id: 'brief_1' }); }
    if (url === '/api/atelier/briefs/brief_1') return json(current);
    if (url.startsWith('/api/atelier/briefs?')) return json({ items: [current], total: 1, limit: 20, offset: 0 });
    return json({ detail: 'Not found' }, 404);
  });
  t.after(network.restore);
  const ui = await mount(<SQLBriefs />, { url: '/studio/briefs/brief_1', pattern: '/studio/briefs/:briefId', client });
  t.after(() => ui.unmount());
  await ui.type([...ui.container.querySelectorAll('label')].find(l => l.textContent?.startsWith('What you checked'))!.querySelector('textarea')!, 'Checked against the call.');
  await ui.tick([...ui.container.querySelectorAll('label')].find(l => l.textContent?.includes('I checked every claim'))!.querySelector('input')!);
  await ui.click(buttonNamed(ui.container, 'Record the check'));
  await ui.settle();
  assert.equal(focusKeyOf(), 'brief:brief_1:h2:pending', 'focus is on the new version\'s status line');
  assert.equal(live(ui), 'Your check is recorded.');
});

test('6.F6: Gate 2\'s CTA choice is a named group with a legend, and its text field has a label', () => {
  const html = renderScreen(<BriefReaderV2 brief={BRIEF_V2 as never} busy={false} perform={async () => {}} versions={[]} onOpen={() => {}} />);
  assert.match(html, /<fieldset[^>]*><legend[^>]*>Which CTA should the brief use\?<\/legend>/);
  assert.equal((html.match(/type="radio" name="cta-brief_1"/g) ?? []).length, 2, 'both choices share one name');
  assert.match(html, /<label[^>]*>What the CTA asks the reader to do<input/, 'the CTA field is labelled');
});

test('6.F6: Edit on a brief field moves focus into the field, and Cancel moves it back to Edit', async t => {
  const body = BRIEF_V2.content_body.document.body as unknown as Record<string, unknown>;
  const ui = await mount(<BriefFieldEditor body={body} schemaVersion="brief_document_v2" locks={[]} expected="h" briefId="brief_1" canEdit busy={false} perform={async () => {}} />);
  t.after(() => ui.unmount());
  const edit = buttonNamed(ui.container, 'Edit')!;
  const row = edit.closest('.py-1')!;
  await ui.click(edit);
  // A choice field is the themed dropdown's trigger; its hidden native mirror (tabindex -1) never takes focus.
  const field = row.querySelector('input:not([tabindex="-1"]),textarea,[role="combobox"]');
  assert.ok(field && document.activeElement === field, 'focus is in the field');
  await ui.click(buttonNamed(row, 'Cancel'));
  assert.equal(document.activeElement, buttonNamed(row, 'Edit'), 'focus is back on Edit');
});

// ---- content packs

async function openPack(t: T, answer: (url: string, options?: RequestInit) => Response | undefined, pack: StoredPackV2 = PACK) {
  const network = stubFetch((url, options) => answer(url, options) ?? (url === `/api/atelier/packs/${pack.pack_id}` ? json(pack) : json({ detail: 'Not found' }, 404)));
  t.after(network.restore);
  const client = createQueryClient();
  for (const [route, args, data] of [...shell({ packs: true }), seed('/packs/{pack_id}', { path: { pack_id: pack.pack_id } }, pack)]) client.setQueryData(queryKey(route as never, args), data);
  const ui = await mount(<ContentPacks base="/studio/packs" />, { url: `/studio/packs/${pack.pack_id}`, pattern: '/studio/packs/:packId', client });
  t.after(() => ui.unmount());
  const review = () => ui.container.querySelector('aside[aria-label="Review the pack"]')!;
  return { ui, network, review };
}

test('6.F6: Edit on a pack line moves focus into the field; Cancel moves it back; a save focuses the piece in the new version', async t => {
  const saved = version('pack_2', { pieces: PACK.pieces.map(p => p.key === 'email' ? piece('email', { content: { ...p.content, preview: 'The inquiry is where it starts.' } }) : p) });
  const { ui } = await openPack(t, (url, options) => {
    if (options?.method === 'PATCH') return json({ pack_id: 'pack_2', manifest_hash: 'manifest_pack_2', state: 'in_review', run_id: 'run_1' });
    if (url === '/api/atelier/packs/pack_2') return json(saved);
    return undefined;
  });
  await ui.click(buttonNamed(ui.container, 'Edit Email: Preview'));
  const field = ui.container.querySelector<HTMLInputElement>('#pack-email-preview')!;
  assert.equal(document.activeElement, field, 'focus is in the field');
  await ui.click(buttonNamed(ui.container, 'Cancel editing Email: Preview'));
  assert.equal(document.activeElement, buttonNamed(ui.container, 'Edit Email: Preview'), 'focus is back on Edit');
  await ui.click(buttonNamed(ui.container, 'Edit Email: Preview'));
  await ui.type(ui.container.querySelector<HTMLInputElement>('#pack-email-preview')!, 'The inquiry is where it starts.');
  await ui.click(buttonNamed(ui.container, 'Save 1 change'));
  await ui.settle();
  await ui.settle();
  assert.equal(focusKeyOf(), 'pack:pack_2:piece:email', 'focus is on the piece\'s heading in the new version');
  assert.equal(live(ui), 'Saved. The new version is open.');
});

test('6.F6: recording publication announces the selected piece and preserves keyboard access', async t => {
  let decided = false;
  const { ui, network } = await openPack(t, (url, options) => {
    if (options?.method === 'POST' && url.endsWith('/pieces/email/published')) { decided = true; return json({ pack_id: 'pack_1', piece: 'email', content_id: 'publication_1' }); }
    if (url === '/api/atelier/packs/pack_1') return json(PACK);
    return undefined;
  });
  // The review panel's Attest, Grant and Finish again are no longer on the page; Mark done is in the folded "Before publishing".
  for (const gone of ['Finish again', 'Attest it is true']) assert.ok(buttonNamed(ui.container, gone) === null, gone);
  assert.ok(buttonNamed(ui.container, 'Mark done: Confirm the client may be referenced in the story Reel.')?.closest('details:not([open])'), 'Mark done waits in the closed fold');
  await ui.click(buttonNamed(ui.container, 'Mark as Published'));
  assert.ok(document.querySelector('[role="dialog"][aria-label="Mark Email as sent"]'));
  await ui.click(buttonNamed(document.body, 'Confirm Sent'));
  await ui.settle();
  await ui.settle();
  assert.ok(decided && network.calls.some(c => c.options?.method === 'POST' && c.url.endsWith('/packs/pack_1/pieces/email/published')));
  assert.equal(focusKeyOf(), 'pack:pack_1:piece:email', 'focus returns to the selected piece');
  assert.equal(live(ui), 'Email marked sent.');
  // Said once to a screen reader (the live region) and shown once on screen (the confirmation, hidden from screen readers).
  const shown = ui.container.querySelector('[data-confirmation]');
  assert.equal(shown?.textContent, 'Email marked sent.');
  assert.equal(shown?.getAttribute('aria-hidden'), 'true');
});

test('6.F6: the selected piece and the pieces\' marks do not rest on colour', () => {
  const marked: StoredPackV2 = { ...PACK, pieces: PACK.pieces.map(p => p.key === 'reel_3' ? piece('reel_3', { origin: 'not_written', content: null, not_written_reason: 'No b-roll.' })
    : p.key === 'carousel' ? piece('carousel', { published: [{ content_id: 'c1', published_on: '2026-10-24', channel: 'instagram', url: null, by: 'a@example.invalid' }] as never }) : p) };
  const html = renderScreen(<ContentPacks base="/studio/packs" />, { url: '/studio/packs/pack_1', pattern: '/studio/packs/:packId', seed: [...shell({ packs: true }), seed('/packs/{pack_id}', { path: { pack_id: 'pack_1' } }, marked)] });
  const tab = (key: string) => {
    const start = html.lastIndexOf('<button', html.indexOf(`id="pack-piece-tab-${key}"`));
    return html.slice(start, html.indexOf('</button>', start));
  };
  assert.match(tab('email'), /aria-selected="true"/);
  // The mockup's pill tabs: the selected one is a filled pill with white text, the others plain text, so the choice reads by
  // shape and contrast, not by hue alone.
  assert.match(tab('email'), /class="[^"]*bg-\[#5070FF\][^"]*text-white/, 'the selected tab is a filled pill');
  assert.doesNotMatch(tab('carousel'), /bg-\[#5070FF\]/);
  assert.match(tab('carousel'), /aria-selected="false"/);
  assert.match(tab('reel_3'), /<span class="sr-only">, not written<\/span>/);
  assert.match(tab('carousel'), /<span class="sr-only">, published<\/span>/);
  assert.doesNotMatch(html, /aria-label="(?:not written|published)"/, 'no label on a plain span');

  // The comparison with the brief ("What the system changed") is no longer on the piece.
  assert.ok(!html.includes('What the system changed') && !html.includes('<ins'));
});

test('6.F6: Copy says "Copied" or "Could not copy" in a live region', async t => {
  let fail = false;
  Object.defineProperty(navigator, 'clipboard', { value: { writeText: async () => { if (fail) throw new Error('blocked'); } }, configurable: true });
  const ui = await mount(<CopyButton text="Follow-up is part of the ad." label="the line" />);
  t.after(() => ui.unmount());
  const region = ui.container.querySelector('[role="status"]')!;
  assert.equal(region.textContent, '');
  await ui.click(buttonNamed(ui.container, 'Copy the line'));
  assert.equal(region.textContent, 'Copied');
  fail = true;
  await ui.click(buttonNamed(ui.container, 'Copy the line'));
  assert.equal(region.textContent, 'Could not copy');
});

// ---- the two drawers

test('6.F6: the knowledge history drawer takes focus, keeps it, closes on Escape and gives focus back', async t => {
  laidOut(t);
  function Harness() {
    const [open, setOpen] = useState(false);
    return <><button type="button" onClick={() => setOpen(true)}>History</button>
      {open && <HistoryDrawer history={{ key: 'offer:a', versions: [], decisions: [] } as never} onClose={() => setOpen(false)} />}</>;
  }
  const ui = await mount(<Harness />);
  t.after(() => ui.unmount());
  const opener = buttonNamed(ui.container, 'History')!;
  opener.focus();
  await ui.click(opener);
  const dialog = ui.container.querySelector('[role="dialog"][aria-label="History"]')!;
  assert.ok(dialog.contains(document.activeElement), 'focus moved into the drawer');
  await key('Tab');
  assert.ok(dialog.contains(document.activeElement), 'Tab stays inside');
  await key('Escape');
  assert.equal(ui.container.querySelector('[role="dialog"]'), null, 'Escape closes it');
  assert.equal(document.activeElement, opener, 'focus is back on History');
});

test('6.F6: the intake source drawer takes focus and closes on Escape', async t => {
  const client = createQueryClient();
  for (const [route, args, data] of [...shell(), seed('/intake/overview', undefined, INTAKE_OVERVIEW),
    seed('/intake/sources/{source_id}', { path: { source_id: 's1' } }, { source: INTAKE_OVERVIEW.sources[0], revisions: [], assets: [] })]) client.setQueryData(queryKey(route as never, args), data);
  const network = stubFetch(url => url.includes('/intake/sources/') ? json({ source: INTAKE_OVERVIEW.sources[0], revisions: [], assets: [] }) : json(INTAKE_OVERVIEW));
  t.after(network.restore);
  const ui = await mount(<IntakeView />, { url: '/sources/intake/sources/s1', pattern: '/sources/intake/sources/:sourceId', client });
  t.after(() => ui.unmount());
  const dialog = ui.container.querySelector('[role="dialog"][aria-label="Source original and revisions"]')!;
  assert.ok(dialog, 'the drawer is open');
  assert.ok(dialog.contains(document.activeElement), 'focus moved into the drawer');
  await key('Escape');
  assert.equal(ui.container.querySelector('[role="dialog"]'), null, 'Escape closes it');
});
