import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { PublishedList, ReviewCard, ReviewQueueList, batchRequest, decisionRequest, groupQueue, initialForm, kindTabs, pageLabel,
  progressLabel, publishedConfirmRequest } from './ContextReview';
import type { ContextItem, ContextQueue, ContextSummary } from '../api/types';

const html = (s: string) => s.replaceAll("'", '&#x27;').replaceAll('"', '&quot;');

const seedPrice: ContextItem = {
  item_id: 'item_0123456789abcdef0123456789abcdef', kind: 'price', key: 'price:google-search-audit', body: { offer: 'Google Search Audit', amount: '$297' },
  text: 'Google Search Audit: $297 (5 a year)', valid_from: null, valid_to: null, status: 'candidate', visibility: 'public', sensitivity: 'none',
  permission: null, source_kind: 'export_seed', source_ref: 'research/x.md#a', statement_date: '2026-09-12',
  source_detail: { draft: 'research/chatgpt-export-2026-10-18/kb-candidates/05-offer-sheet.md', section: '3. Prices', date_text: '12 September 2026',
    conversations: ['2026-09-12_audit-pricing-4f2a'], attachments: ['attachments B1'], date_from: 'section' },
  author: 'model (the 18 October export analysis, from WIA\'s material)', model_written: true, confidence: 'medium', hash: 'hash_price_0001',
  would_change: { document: 'offer_sheet', layer: 'operating (takes effect when confirmed)', replaces: { item_id: 'item_old', text: 'Google Search Audit: $247' }, summary: 'Replaces the confirmed entry in offer_sheet' },
  suggestion: { action: 'accept', reason: 'The latest quote for this offer; internal, so it never reaches public copy', changes: { visibility: 'internal' } },
  can_decide: true,
};
const phrase = (n: number): ContextItem => ({ ...seedPrice, item_id: `item_phrase${n}`, kind: 'audience_phrase', key: `audience:p${n}`, text: `Phrase ${n}`,
  hash: `hash_phrase_${n}`, body: { phrase: `Phrase ${n}`, theme: 'leads' }, suggestion: { action: 'accept', reason: 'Her own words' }, would_change: undefined });
const rule: ContextItem = { ...seedPrice, item_id: 'item_rule', kind: 'rule', key: 'rule:no-hype', text: 'Never call a result "insane".', hash: 'hash_rule_0001',
  source_kind: 'brief_edit', model_written: false, author: 'Gisselle Jiménez', statement_date: '2026-10-16',
  source_detail: { category: 'voice', diffs: [{ field: 'hook', before: 'Insane results', after: 'Steady bookings' }, { field: 'hook', before: 'Crazy ROI', after: 'More tours' }] },
  suggestion: { action: 'review', reason: 'Low confidence in the draft' }, can_decide: false };

test('L.F1: the form pre-selects the suggestion and its reason, with its suggested settings', () => {
  const f = initialForm(seedPrice);
  assert.equal(f.action, 'accept');
  assert.equal(f.reason, seedPrice.suggestion!.reason);
  assert.equal(f.visibility, 'internal');
  assert.equal(initialForm(rule).action, '', 'a "review" suggestion selects nothing');
});

test('L.F1: accept, edit and reject build the API request, bound to the item hash, with a reason', () => {
  const f = initialForm(seedPrice);
  const accept = decisionRequest(seedPrice, f);
  assert.ok('body' in accept);
  assert.equal(accept.path, `/context/items/${seedPrice.item_id}/decision`);
  assert.deepEqual(accept.body, { expected_hash: 'hash_price_0001', action: 'accept', reason: f.reason, changes: { visibility: 'internal' } });
  assert.deepEqual(decisionRequest(seedPrice, { ...f, reason: '  ' }), { error: 'Write a reason. It is kept with the decision.' });
  assert.match((decisionRequest(seedPrice, { ...f, action: '' }) as { error: string }).error, /Choose/);
  assert.match((decisionRequest(seedPrice, { ...f, action: 'edit' }) as { error: string }).error, /Change the wording/);
  const edit = decisionRequest(seedPrice, { ...f, action: 'edit', text: 'Google Search Audit: $297', visibility: 'public', author: 'Whitney Hodges' });
  assert.deepEqual('body' in edit && edit.body, { expected_hash: 'hash_price_0001', action: 'edit', reason: f.reason, author: 'Whitney Hodges', changes: { text: 'Google Search Audit: $297' } });
  const reject = decisionRequest(seedPrice, { ...f, action: 'reject', reason: 'Out of date', visibility: 'public', text: 'changed' });
  assert.deepEqual('body' in reject && reject.body, { expected_hash: 'hash_price_0001', action: 'reject', reason: 'Out of date' }, 'a rejection takes a reason only');
  assert.match((decisionRequest(seedPrice, { ...f, sensitivity: 'client_private', visibility: 'public' }) as { error: string }).error, /internal/);
  assert.match((decisionRequest(seedPrice, { ...f, valid_from: '2026-11-01', valid_to: '2026-10-01' }) as { error: string }).error, /end date/);
  const result = { ...seedPrice, kind: 'result' as const, permission: null };
  assert.match((decisionRequest(result, { ...initialForm(result), permission: '' }) as { error: string }).error, /permission/);
  const dated = decisionRequest(seedPrice, { ...f, valid_from: '2026-11-01' });
  assert.deepEqual('body' in dated && dated.body.changes, { visibility: 'internal', valid_from: '2026-11-01' });
});

test('L.F1: batch decisions only for audience phrases; published pieces confirm in a batch', () => {
  assert.match((batchRequest([phrase(1), seedPrice], 'accept', 'ok', ['audience_phrase']) as { error: string }).error, /Only audience phrases/);
  assert.match((batchRequest([], 'accept', 'ok', ['audience_phrase']) as { error: string }).error, /Tick/);
  assert.match((batchRequest([phrase(1)], 'accept', ' ', ['audience_phrase']) as { error: string }).error, /reason/);
  assert.deepEqual(batchRequest([phrase(1), phrase(2)], 'reject', ' Not hers ', ['audience_phrase']),
    { body: { action: 'reject', reason: 'Not hers', entries: [{ item_id: 'item_phrase1', expected_hash: 'hash_phrase_1' }, { item_id: 'item_phrase2', expected_hash: 'hash_phrase_2' }] } });
  assert.deepEqual(publishedConfirmRequest(['published_ab'], 'WIA published it'), { body: { content_ids: ['published_ab'], reason: 'WIA published it' } });
  assert.match((publishedConfirmRequest([], 'x') as { error: string }).error, /Tick/);
});

test('L.F1: candidates sharing an entry are grouped, in queue order', () => {
  const a = { ...seedPrice, item_id: 'a' }, b = { ...seedPrice, item_id: 'b' }, c = { ...rule, item_id: 'c' };
  assert.deepEqual(groupQueue([a, b, c], { [seedPrice.key]: ['a', 'b'] }).map(g => g.items.map(i => i.item_id)), [['a', 'b'], ['c']]);
  assert.deepEqual(groupQueue([a, c], {}).map(g => g.items.length), [1, 1]);
});

test('L.F1: tabs carry counts, and progress says how many are left', () => {
  const summary: ContextSummary = { kinds: { price: { candidate: 12, confirmed: 3 }, rule: { candidate: 300 }, offer: { confirmed: 4 } }, candidates: 312, published: { unconfirmed: 0 } };
  assert.deepEqual(kindTabs(summary).map(t => [t.label, t.count]), [['Everything', 312], ['Prices', 12], ['Rules', 300], ['Published pieces', 0]]);
  assert.equal(progressLabel(summary), '312 left to review');
  assert.equal(progressLabel({ ...summary, candidates: 0 }), 'Nothing left to review');
  assert.equal(progressLabel({ ...summary, published: { unconfirmed: 1000 } }), '1,312 left to review');
  assert.equal(pageLabel({ offset: 50, total: 312 }, 50), 'Showing 51 to 100 of 312');
});

test('L.F1: a candidate shows where it came from, who said it, what it changes, the suggestion and the three actions, without system badges', () => {
  const out = renderToStaticMarkup(<ReviewCard item={seedPrice} busy={false} selectable={false} selected={false} onSelect={() => {}} onDecide={() => {}} />);
  for (const text of ['Price', seedPrice.text, "From Whitney's ChatGPT, Prices, 12 September 2026", 'Who said it', 'The model (from WIA\'s material)',
    'Replaces the current entry in the offer sheet.', 'Current entry: Google Search Audit: $247',
    'Suggested: Accept.', 'The latest quote', 'Accept', 'Edit and accept', 'Reject', 'Reason *', 'Save decision']) {
    assert.ok(out.includes(html(text)), text);
  }
  for (const hidden of [seedPrice.item_id, seedPrice.hash, seedPrice.key, 'offer_sheet', 'export_seed', 'Written by the model', 'Sources: conversation', 'Date from its section'])
    assert.ok(!out.includes(hidden), `no ${hidden} on screen`);
});

test('L.F1: an identity entry the reviewer cannot decide is disabled and says who can; edits it came from are shown', () => {
  const out = renderToStaticMarkup(<ReviewCard item={rule} busy={false} selectable={false} selected={false} onSelect={() => {}} onDecide={() => {}} />);
  assert.ok(out.includes('Only Whitney can decide rules'));
  assert.match(out, /<fieldset class="[^"]*" disabled=""/);
  assert.ok(out.includes('Suggested: Look closely before deciding'));
  assert.ok(out.includes('From 2 edits to approved briefs (voice), 16 October 2026') && out.includes('Steady bookings') && out.includes('Gisselle Jiménez'));
  assert.ok(!out.includes('Written by the model'));
});

test('L.F1: the queue groups shared entries and offers batch selection only for audience phrases', () => {
  const queue: ContextQueue = { items: [{ ...seedPrice, item_id: 'a' }, { ...seedPrice, item_id: 'b' }, phrase(1)], groups: { [seedPrice.key]: ['a', 'b'] },
    total: 3, limit: 50, offset: 0, batch_kinds: ['audience_phrase'] };
  const out = renderToStaticMarkup(<ReviewQueueList queue={queue} batchKinds={['audience_phrase']} busy={false} selected={[]} onSelect={() => {}} onDecide={() => {}} />);
  assert.ok(out.includes('2 suggestions for the same price'));
  assert.equal(out.split('type="checkbox"').length - 1, 1, 'only the audience phrase can be selected');
  assert.ok(renderToStaticMarkup(<ReviewQueueList queue={{ ...queue, items: [] }} batchKinds={[]} busy={false} selected={[]} onSelect={() => {}} onDecide={() => {}} />).includes('Nothing waiting here'));
  const pieces = renderToStaticMarkup(<PublishedList pieces={[{ content_id: 'published_ab', published_on: '2026-06-10', channel: 'email', title: 'Buyer research email', status: 'unconfirmed',
    source_kind: 'export_seed', details: null, angle_id: null, brief_id: null, performance: [] }]} selected={[]} busy={false} onSelect={() => {}} />);
  assert.ok(pieces.includes('Buyer research email') && pieces.includes('email · 10 June 2026') && pieces.includes('Select all 1') && !pieces.includes('published_ab'));
});
