import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { FactEditor, HistoryDrawer, KnownList, PerformancePanel, PerformanceForms, WarningsList, briefOptions, csvRequest, emptyFact, entryRequest, factFromItem,
  figureLabel, groupByKind, historyAction, knownPath, linkRequest, metricRequest, pieceLabel, pieceRequest } from './ContextKnowledge';
import type { ContextItem, KnownItems, PublishedPiece } from '../api/types';

const price: ContextItem = {
  item_id: 'item_aaaabbbbccccddddeeeeffff00001111', kind: 'price', key: 'price:elevate', body: { offer: 'ELEVATE', amount: '$2,500/month', block_terms: ['$2,500'] },
  text: 'ELEVATE: $2,500/month', valid_from: '2026-06-01', valid_to: '2026-10-31', status: 'confirmed', visibility: 'internal', sensitivity: 'none',
  permission: null, source_kind: 'approver_entry', source_ref: 'entry_1', source_detail: {}, statement_date: '2026-06-01', author: 'Whitney Hodges',
  model_written: false, confidence: 'high', hash: 'hash_price_known', reviewed_by: 'whitney@example.invalid',
};
const scheduledPrice: ContextItem = { ...price, item_id: 'item_next', text: 'ELEVATE: $2,750/month', valid_from: '2026-11-01', valid_to: null, hash: 'hash_next' };
const member: ContextItem = { ...price, item_id: 'item_member', kind: 'roster_member', key: 'roster:fallon-looney', text: 'Fallon Looney: strategist (former; left 14 August 2026)',
  body: { name: 'Fallon Looney', role: 'strategist', state: 'former', left_on: '14 August 2026', aliases: ['Fallon'] }, visibility: 'public', valid_from: null, valid_to: null,
  source_kind: 'export_seed', source_detail: { section: '2. Team', date_text: 'August 2026' }, author: 'Whitney' };
const known: KnownItems = { on: '2026-10-18', items: [member, price], scheduled: [scheduledPrice] };

test('L.F2: the known-items path carries the kind and date only when set', () => {
  assert.equal(knownPath('price', '2026-10-18'), '/context/items?kind=price&on=2026-10-18');
  assert.equal(knownPath('', ''), '/context/items');
  assert.deepEqual(groupByKind([member, price]).map(g => g.kind), ['price', 'roster_member'], 'offers and prices first');
});

test('L.F2: a price is internal by default; a new fact sends its name, a change sends its key and start date', () => {
  const f = emptyFact('price');
  assert.equal(f.visibility, 'internal');
  assert.match((entryRequest(f) as { error: string }).error, /Offer/);
  assert.match((entryRequest({ ...f, fields: { offer: 'Audit', amount: 'free', terms: '' }, reason: 'x' }) as { error: string }).error, /figure/);
  assert.match((entryRequest({ ...f, fields: { offer: 'Audit', amount: '$297', terms: '' } }) as { error: string }).error, /reason/);
  assert.deepEqual(entryRequest({ ...f, fields: { offer: ' Google Search Audit ', amount: '$297', terms: '' }, reason: 'New audit price' }),
    { body: { kind: 'price', name: 'Google Search Audit', body: { offer: 'Google Search Audit', amount: '$297' }, visibility: 'internal', sensitivity: 'none', reason: 'New audit price' } });
  const change = { ...factFromItem(price, '2026-10-18'), fields: { offer: 'ELEVATE', amount: '$2,750/month', terms: '' }, valid_from: '2026-11-01', reason: 'Price rise from November' };
  const r = entryRequest(change, price);
  assert.ok('body' in r);
  assert.equal(r.body.key, 'price:elevate');
  assert.equal(r.body.valid_from, '2026-11-01');
  assert.equal(r.body.name, undefined);
  assert.deepEqual(r.body.body, { offer: 'ELEVATE', amount: '$2,750/month', block_terms: ['$2,500'] }, 'fields the form does not show are kept');
  assert.match((entryRequest({ ...change, valid_from: '' }, price) as { error: string }).error, /date the change takes effect/);
  assert.equal(factFromItem(price, '2026-10-18').valid_from, '2026-10-18');
});

test('L.F2: a result needs its permission, and a client-private result is internal', () => {
  const f = { ...emptyFact('result'), fields: { claim: '295% more enquiries', client_type: '', offer: '', first_published: '' }, reason: 'From the case study' };
  assert.match((entryRequest(f) as { error: string }).error, /permission/);
  assert.match((entryRequest({ ...f, permission: 'client_permission', client_private: true }) as { error: string }).error, /internal/);
  const ok = entryRequest({ ...f, permission: 'client_permission', client_private: true, visibility: 'internal' });
  assert.deepEqual('body' in ok && [ok.body.permission, ok.body.sensitivity, ok.body.visibility], ['client_permission', 'client_private', 'internal']);
  const cta = entryRequest({ ...emptyFact('cta'), fields: { wording: 'DM "AUDIT"', cta_type: 'dm_keyword', used_for: 'audit', channel: '', offer: '' }, reason: 'r' });
  assert.equal('body' in cta && cta.body.name, 'audit');
  const member = emptyFact('roster_member');
  assert.equal(member.fields.state, 'current');
});

test('L.F2: performance requests: a piece, a figure, a brief link and a CSV import', () => {
  assert.match((pieceRequest({ published_on: '', channel: '', title: '', text: '', brief_id: '' }) as { error: string }).error, /date/);
  assert.deepEqual(pieceRequest({ published_on: '2026-06-10', channel: ' email ', title: 'Buyer research', text: '', brief_id: 'brief_1' }),
    { body: { published_on: '2026-06-10', channel: 'email', title: 'Buyer research', brief_id: 'brief_1' } });
  assert.deepEqual(metricRequest({ content_id: 'published_ab', on: '2026-06-12', metric: 'opens', value: '1,240', direction: 'positive' }),
    { path: '/context/published/published_ab/performance', body: { on: '2026-06-12', metric: 'opens', value: '1,240', direction: 'positive' } });
  assert.match((metricRequest({ content_id: '', on: '', metric: '', value: '', direction: '' }) as { error: string }).error, /piece/);
  assert.deepEqual(linkRequest('published_ab', 'brief_1'), { path: '/context/published/published_ab/link', body: { brief_id: 'brief_1' } });
  assert.match((linkRequest('published_ab', '') as { error: string }).error, /brief/);
  assert.match((csvRequest('date,channel,title\n') as { error: string }).error, /missing: piece, metric, value/);
  assert.deepEqual(csvRequest('﻿date,channel,piece,metric,value,brief_id\n2026-06-12,email,Buyer research,opens,1240,\n'),
    { body: { csv: 'date,channel,piece,metric,value,brief_id\n2026-06-12,email,Buyer research,opens,1240,' } });
  assert.match((csvRequest('') as { error: string }).error, /CSV/);
});

test('L.F2: labels for history, pieces, figures and briefs use plain words', () => {
  assert.equal(historyAction('context_edit'), 'Edited and accepted');
  assert.equal(historyAction('context_enter'), 'Entered by an approver');
  const piece: PublishedPiece = { content_id: 'published_ab', published_on: '2026-06-10', channel: 'email', title: 'Buyer research', status: 'confirmed', source_kind: null,
    details: null, angle_id: null, brief_id: null, performance: [{ date: '2026-06-12', metric: 'opens', value: '1240', direction: 'positive', source: 'manual entry' }] };
  assert.equal(pieceLabel(piece), 'Buyer research · email · 10 June 2026');
  assert.equal(figureLabel(piece.performance![0]), 'opens: 1240 (did well), 12 June 2026');
  assert.deepEqual(briefOptions([{ brief_id: 'b1', content_body: { document: { title: 'Thank-you emails' } } }, { brief_id: 'b2' }]),
    [{ brief_id: 'b1', title: 'Thank-you emails' }, { brief_id: 'b2', title: 'Untitled brief' }]);
});

test('L.F2: an entry shows its text and one quiet line (in use from, public or internal); where it came from is in its History', () => {
  const out = renderToStaticMarkup(<KnownList known={known} onHistory={() => {}} />);
  for (const text of ['Prices', 'Team', 'ELEVATE: $2,500/month', 'In use from 1 June 2026 to 31 October 2026 · Internal', 'History',
    'Coming up', 'ELEVATE: $2,750/month', 'Starts 1 November 2026 · Internal']) {
    assert.ok(out.includes(text), text);
  }
  for (const moved of ['Entered by an approver', 'Who said it', 'Confirmed by', 'ChatGPT']) assert.ok(!out.includes(moved), `${moved} is in the History, not the list`);
  for (const hidden of [price.item_id, price.hash, price.key]) assert.ok(!out.includes(hidden), hidden);
  assert.ok(renderToStaticMarkup(<WarningsList warnings={[{ scope: 'kind', kind: 'roster_member', since: '2026-09-30', message: '3 confirmed roster member entries are past their 30-day review' }]} />)
    .includes('Due for a review'));
  assert.equal(renderToStaticMarkup(<WarningsList warnings={[]} />), '');
});

test('L.F2: the editor explains internal prices; the history drawer lists versions and decisions', () => {
  const editor = renderToStaticMarkup(<FactEditor entries={[price]} busy={false} onSave={() => {}} />);
  for (const text of ['Add or change a fact', 'never stated in public copy', 'A new price', 'ELEVATE: $2,500/month', 'Reason *', 'Save the new fact']) assert.ok(editor.includes(text), text);
  const drawer = renderToStaticMarkup(<HistoryDrawer history={{ key: 'price:elevate', versions: [price, scheduledPrice],
    decisions: [{ action: 'context_enter', note: 'Price rise from November', actor: 'whitney@example.invalid', author: 'Whitney Hodges', created_at: '2026-10-18T09:00:00Z' }] }} onClose={() => {}} />);
  for (const text of ['Versions (2)', 'Entered by an approver', 'by Whitney Hodges on 18 October 2026', 'Why: Price rise from November']) assert.ok(drawer.includes(text), text);
  assert.ok(!drawer.includes('price:elevate'));
  const pieces = [{ content_id: 'published_ab', published_on: '2026-06-10', channel: 'email', title: 'Buyer research', status: 'confirmed',
    source_kind: null, details: null, angle_id: null, brief_id: 'b1', performance: [{ date: '2026-06-12', metric: 'opens', value: '1240' }] }];
  const panel = renderToStaticMarkup(<PerformancePanel pieces={pieces} onOpen={() => {}} />);
  for (const text of ['Published pieces and how they did', 'Add a figure', 'Link to a brief', 'Import figures', 'Buyer research · email · 10 June 2026 · linked to its brief', 'opens: 1240, 12 June 2026'])
    assert.ok(panel.includes(text), text);
  assert.ok(!panel.includes('<form'), 'the forms open in dialogs, they are not printed on the page');
  const forms = (['piece', 'figure', 'link', 'import'] as const).map(form => renderToStaticMarkup(<PerformanceForms form={form} pieces={pieces} briefs={[{ brief_id: 'b1', title: 'Thank-you emails' }]} busy={false} onPost={() => {}} />));
  for (const [i, text] of ['Record the piece', 'Add the figure', 'Link them', 'Import'].entries()) assert.ok(forms[i].includes(text), text);
  assert.ok(forms[0].includes('Thank-you emails') && forms[1].includes('Buyer research · email · 10 June 2026'));
});
