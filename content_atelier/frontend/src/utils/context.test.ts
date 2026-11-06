import { test } from 'node:test';
import assert from 'node:assert/strict';
import { authorLabel, changeInWords, contextError, documentLabel, formatDate, kindLabel, sourceInWords, todayIso, validityLabel, whoDecides } from './context';

const status = (code: number, message = 'x') => Object.assign(new Error(message), { status: code });

test('L.F1: dates, validity and kinds read as plain words', () => {
  assert.equal(formatDate('2026-10-14'), '14 October 2026');
  assert.equal(formatDate('2026-06-01T09:00:00+00:00'), '1 June 2026');
  assert.equal(formatDate('June 2025'), 'June 2025');
  assert.equal(formatDate(null), '');
  assert.equal(todayIso(new Date(2026, 9, 18)), '2026-10-18');
  assert.equal(validityLabel('2026-11-01', null), 'In use from 1 November 2026');
  assert.equal(validityLabel(null, '2026-12-31'), 'In use until 31 December 2026');
  assert.equal(validityLabel('2026-06-01', '2026-10-31'), 'In use from 1 June 2026 to 31 October 2026');
  assert.equal(validityLabel(null, null), 'In use with no set dates');
  assert.equal(kindLabel('roster_member'), 'Team member');
  assert.equal(kindLabel('audience_phrase', true), 'Audience phrases');
  assert.equal(documentLabel('offer_sheet'), 'the offer sheet');
  assert.equal(documentLabel('new_doc'), 'the new doc');
});

test('L.F1: the source of a seed candidate is told in words, with its conversations as a sources line', () => {
  const seed = sourceInWords({ source_kind: 'export_seed', statement_date: '2026-05-14',
    source_detail: { section: '4. Rejection rules', subsection: 'Hype words', conversations: ['2026-05-14_voice-notes-9a1b'], chunks: ['C12'], citations_from: 'section', date_from: 'section' } });
  assert.equal(seed.from, "From Whitney's ChatGPT, Rejection rules · Hype words, 14 May 2026");
  assert.equal(seed.sources, 'Sources: conversation 2026-05-14_voice-notes-9a1b; report C12');
  assert.deepEqual(seed.notes, ['Sources cited by its section', 'Date from its section']);
  const uncited = sourceInWords({ source_kind: 'export_seed', statement_date: null, source_detail: { section: 'Notes', citations_from: 'draft', date_text: 'June 2025' } });
  assert.equal(uncited.from, "From Whitney's ChatGPT, Notes, June 2025");
  assert.equal(uncited.sources, null);
  assert.deepEqual(uncited.notes, ['No conversation cited']);
});

test('L.F1: live-work sources name the decision, card, brief or edit they came from', () => {
  const at = (source_kind: string, source_detail = {}) => sourceInWords({ source_kind, source_detail, statement_date: '2026-10-16' }).from;
  assert.equal(at('approved_card'), 'From a card WIA approved, 16 October 2026');
  assert.equal(at('approved_card', { disposition: 'reframe' }), 'From a reframed card WIA approved, 16 October 2026');
  assert.equal(at('approved_brief', { section: 'wia_perspective' }), 'From a brief WIA approved, its WIA perspective section, 16 October 2026');
  assert.equal(at('gate_decision', { category: 'voice', decisions: ['d1', 'd2'] }), 'From 2 gate decisions giving the same voice reason, 16 October 2026');
  assert.equal(at('gate_decision', { corrects: 'item_x', correction: { from: '10 weeks', to: '12 weeks' } }), 'From a correction recorded at a gate decision ("10 weeks" should read "12 weeks"), 16 October 2026');
  assert.equal(at('gate_decision'), 'From a reason recorded at a gate decision, 16 October 2026');
  assert.equal(at('brief_edit', { category: 'format', diffs: [{}, {}, {}] }), 'From 3 edits to approved briefs (format), 16 October 2026');
  assert.equal(at('published_piece'), 'From a published piece linked to the brief behind it, 16 October 2026');
  assert.equal(at('seed'), 'From a founder seed marked "always true", 16 October 2026');
  assert.equal(at('approver_entry'), 'Entered by an approver, 16 October 2026');
});

test('L.F1: authors, what a decision changes and who can decide', () => {
  assert.equal(authorLabel('model (the 18 October export analysis, from WIA\'s material)'), 'The model (from WIA\'s material)');
  assert.equal(authorLabel('team (Gisselle Jiménez or another WIA team member)'), 'A WIA team member');
  assert.equal(authorLabel('Whitney'), 'Whitney');
  assert.equal(authorLabel(null), 'Not recorded');
  assert.equal(changeInWords({ kind: 'price', would_change: { document: 'offer_sheet', layer: '', replaces: null, summary: '' } }), 'Adds an entry to the offer sheet. It takes effect when confirmed.');
  assert.match(changeInWords({ kind: 'rule', would_change: { document: 'rejection_rules', layer: '', replaces: { item_id: 'i', text: 't' }, summary: '' } }), /^Replaces the current entry in the rules\. .*benchmark/);
  assert.match(whoDecides('exemplar'), /Only Whitney/);
  assert.match(whoDecides('price'), /approver/);
});

test('L.F1: errors read plainly; a stale or refused decision asks for a reload, and never reloads on its own', () => {
  assert.deepEqual(contextError(status(503)), { message: 'The knowledge store is not set up yet.', reload: false });
  assert.equal(contextError(status(403, 'Knowledge-base review needs an approver (ATELIER_BRIEF_APPROVERS)')).message.includes('ATELIER'), false);
  assert.deepEqual(contextError(status(409, 'This entry changed since it was shown; reload the queue')),
    { message: 'This entry changed since it was shown; reload the queue.', reload: true });
  assert.deepEqual(contextError(new Error('Weekly request failed.')), { message: 'Weekly request failed.', reload: false });
});
