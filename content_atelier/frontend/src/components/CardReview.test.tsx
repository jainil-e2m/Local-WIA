import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderScreen as renderToStaticMarkup } from '../testing/render';
import { CardReview, CardWeekPanel, DECIDE_IN_DEVELOPMENT, heldCards, cardDispositionBody, emptyForm, purposeMix, speakerLabel } from './CardReview';
import type { Card, CardSelection, RosterEntry, Rubric, StoredAngle } from '../api/types';

const card: Card = {
  rank: 1, title: 'Why we read your thank-you emails first', pillar: 'WARM', content_type: 'behind_the_scenes',
  audience: 'Venue owners', core_perspective: 'How WIA learns a business before it advertises it.', why_it_matters: 'Couples book on feeling.',
  wia_in_action: 'Carmen asked which couples book winter tastings.', offer_connection: null, moment_ids: ['moment_a'],
  evidence_points: ['Carmen asked about the calendar.'], verify_before_publishing: ['Confirm the client is happy to be named'],
  why_selected: 'Shows the WIA move.', series: 'Watch Us Build an Ad Strategy',
};
const angle = {
  angle_id: 'angle_one', run_id: 'run_one', content_hash: 'h1', moment_ids: ['moment_a'], has_replacement: false, can_approve: true,
  content_body: { card, title: card.title }, approval_status: 'pending', selection_status: 'visible',
  matching_result: { status: 'complete', current_batch_flags: [] }, disposition: null, hold: null,
} as unknown as StoredAngle;
const roster: RosterEntry[] = [
  { name: 'Carmen Cruickshank', role: 'Google Ads lead: keyword research', status: 'current', aliases: ['Carmen Cruickshank', 'Carmen'] },
  { name: 'Fallon Looney', role: 'Google, Meta and funnel strategist', status: 'former', aliases: ['Fallon Looney', 'Fallon'] },
];
const selection: CardSelection = {
  run_id: 'run_one', week_summary: 'One call shows how WIA diagnoses lead quality.', selection_hash: 'sel',
  ranking: [], unreferenced_moment_ids: [], publishing_order: [1], pillar_notes: [{ pillar: 'CONVERT', note: 'No offer decision this week.' }],
  seed_pairings: [{ seed_ref: 'F1', moment_ids: [], note: 'Whitney\'s note on first replies.' }],
  considered_not_selected: [{ index: 0, moment_ids: ['moment_a'], idea: 'Negative keyword tips', reason: 'Too narrow.', disposition: null }],
  internal_insights: [{ moment_ids: ['moment_a'], insight: 'A pricing objection.', use: 'Sales enablement.' }],
};

test('E.F1: develop defaults to "decide in development" and needs every verify item ticked', () => {
  const form = emptyForm();
  assert.deepEqual(cardDispositionBody(form, card, 'h1', false), { error: 'Tick every "verify before publishing" item first.' });
  const ok = cardDispositionBody({ ...form, verified: card.verify_before_publishing, author: 'Whitney Hodges' }, card, 'h1', false);
  assert.ok('body' in ok);
  assert.deepEqual(ok.body.cta, DECIDE_IN_DEVELOPMENT);
  assert.equal(ok.body.disposition, 'develop'); assert.equal(ok.body.author, 'Whitney Hodges'); assert.equal(ok.body.expected_hash, 'h1');
  assert.deepEqual(ok.body.verify_acknowledged, card.verify_before_publishing);
  const overlap = cardDispositionBody({ ...form, verified: card.verify_before_publishing }, card, 'h1', true);
  assert.match('error' in overlap ? overlap.error : '', /overlaps/);
});

test('E.F1: reframe, hold, internal and skip send what the API requires', () => {
  const form = { ...emptyForm(), reason_code: 'voice' };
  assert.match((cardDispositionBody({ ...form, disposition: 'skip', reason_code: '' }, card, 'h', false) as { error: string }).error, /reason/);
  assert.match((cardDispositionBody({ ...form, disposition: 'reframe' }, card, 'h', false) as { error: string }).error, /reframed/);
  assert.match((cardDispositionBody({ ...form, disposition: 'reframe', reframe_title: 'New' }, card, 'h', false) as { error: string }).error, /central point/);
  const reframe = cardDispositionBody({ ...form, disposition: 'reframe', reframe_title: ' New title ', central_point_kept: 'yes' }, card, 'h', false);
  assert.deepEqual('body' in reframe && [reframe.body.reframe, reframe.body.central_point_kept], [{ title: 'New title' }, true]);
  assert.match((cardDispositionBody({ ...form, disposition: 'hold', hold_until: '2026-10-18' }, card, 'h', false, '2026-10-18') as { error: string }).error, /after today/);
  const hold = cardDispositionBody({ ...form, disposition: 'hold', hold_until: '2026-11-01' }, card, 'h', false, '2026-10-18');
  assert.equal('body' in hold && hold.body.hold_until, '2026-11-01');
  const skip = cardDispositionBody({ ...form, disposition: 'skip' }, card, 'h', false);
  assert.deepEqual('body' in skip && skip.body, { expected_hash: 'h', disposition: 'skip', note: null, author: null, reason_code: 'voice' });
});

test('E.F2: speakers appear by roster name and role; anyone else is a client or prospect', () => {
  assert.equal(speakerLabel('Carmen', roster), 'Carmen Cruickshank (WIA, Google Ads lead)');
  assert.equal(speakerLabel('Fallon Looney', roster), 'Fallon Looney (former WIA team member)');
  assert.equal(speakerLabel('Shannon Lee', roster, 'Week 1 client call'), 'Client');
  assert.equal(speakerLabel('Shannon Lee', roster, 'Ads Strategy Call _ Example Venue'), 'Prospect');
  assert.equal(speakerLabel(null, roster), 'Client');
});

test('E.F2: the card shows its fields, series, verify items and the disposition control', () => {
  const html = renderToStaticMarkup(<CardReview angle={angle} card={card} roster={roster} busy={false} perform={async () => {}} />);
  for (const text of [card.title, 'WARM', 'Behind the scenes', 'Watch Us Build an Ad Strategy', 'Venue owners', card.core_perspective,
    card.why_it_matters, card.wia_in_action!, card.evidence_points[0], 'Confirm the client is happy to be named', 'Your decision',
    'Develop', 'Reframe', 'Hold', 'Internal', 'Skip', 'Decide the CTA in development', 'What was said on the call']) {
    assert.ok(html.includes(text.replaceAll("'", '&#x27;')), text);
  }
  for (const removed of ['Offer connection', 'Why it was chosen', '>Details<', 'Whose decision is this?', 'Rate this card', 'Decision:']) {
    assert.ok(!html.includes(removed), `not on the card screen: ${removed}`);
  }
  const approved = renderToStaticMarkup(<CardReview angle={{ ...angle, approval_status: 'approved', disposition: { disposition: 'develop', author: 'Avery Lane', created_at: '2026-10-25T09:00:00Z' } } as unknown as StoredAngle}
    card={card} roster={roster} busy={false} perform={async () => {}} />);
  assert.ok(approved.includes('Approved · 25 Oct 2026') && !approved.includes('Developed') && !approved.includes('Your decision'));
  assert.ok(!approved.includes('Verify before publishing') && !approved.includes('Avery Lane'), 'the checks are for a card that waits; no decider is named');
});

test('E.F2: the why-these panel shows the summary, mix, order, pillars, seeds, dropped ideas and internal insights', () => {
  const html = renderToStaticMarkup(<CardWeekPanel weekId="week_one" selection={selection} cards={[{ angle, card }]} roster={roster} busy={false} perform={async () => {}} />);
  for (const text of ['Why these ideas', selection.week_summary, 'Purpose mix:', '1 WARM', 'Proposed publishing order', 'CONVERT: No offer decision this week.',
    'No call evidence.', 'Considered and dropped (1)', 'Negative keyword tips', 'Revive as a card',
    'Internal insights (1)', 'A pricing objection.']) {
    assert.ok(html.includes(text.replaceAll("'", '&#x27;')), text);
  }
  assert.ok(!html.includes('F1:'), 'a seed shows its words or its status, never its reference (R50)');
  assert.ok(!html.includes('Dropped because') && !html.includes('Too narrow.'), 'a considered idea shows its title and its actions only');
  assert.equal(purposeMix([card, { ...card, pillar: 'ATTRACT' }, card]), '1 ATTRACT · 2 WARM');
});


test('E.B10: a blocking ledger flag must be checked and explained before develop; the ledger shows collapsed', () => {
  const ledger = { version: 'ledger-2026-10-18.v1', readiness: 'research_required' as const, ledger_hash: 'lh', model_pass: 'not_run',
    qualifiers: ['The links were to be removed, not removed yet.'], bindings: [], critic: null,
    flags: [{ id: 'flag_a', kind: 'tense', severity: 'block' as const, field: 'wia_in_action', text: 't', message: 'States removed; the call only says it will be done', source: 'deterministic' },
            { id: 'flag_b', kind: 'frequency', severity: 'check' as const, field: 'why_it_matters', text: 't', message: 'every week is a frequency claim', source: 'deterministic' }] };
  const form = { ...emptyForm(), verified: card.verify_before_publishing };
  assert.match((cardDispositionBody(form, card, 'h', false, undefined, ledger) as { error: string }).error, /blocking evidence flag/);
  assert.match((cardDispositionBody({ ...form, verified: [...form.verified, 'flag_a'] }, card, 'h', false, undefined, ledger) as { error: string }).error, /note/);
  const ok = cardDispositionBody({ ...form, verified: [...form.verified, 'flag_a'], note: 'Checked: Carmen said she would remove them.' }, card, 'h', false, undefined, ledger);
  assert.deepEqual('body' in ok && ok.body.verify_acknowledged, [...card.verify_before_publishing, 'flag_a']);
  const html = renderToStaticMarkup(<CardReview angle={{ ...angle, content_body: { ...angle.content_body, ledger } } as unknown as StoredAngle} card={card} roster={roster} busy={false} perform={async () => {}} />);
  for (const text of ['a blocking problem to resolve', 'Must be resolved', 'Worth a look', 'Must stay true when developed', 'Checked by rule only']) assert.ok(html.includes(text), text);
});

import { AUTHOR_LABEL, LedgerPanel, fieldLabel, modelCheckNote } from './CardReview';

test('R50: the ledger names card parts in plain words and never names the model', () => {
  assert.equal(fieldLabel('evidence_points[2]'), 'evidence point 3');
  assert.equal(fieldLabel('moment_ids'), 'the scenes it cites');
  assert.equal(fieldLabel('core_perspective'), 'the point');
  assert.equal(modelCheckNote('anthropic/claude-sonnet-5.5'), 'Also checked a second time.');
  assert.match(modelCheckNote('unavailable'), /unavailable this week/);
  const ledger = { version: 'ledger-2026-10-18.v1', readiness: 'research_required' as const, ledger_hash: 'lh', model_pass: 'anthropic/claude-sonnet-5.5',
    flags: [{ id: 'f1', kind: 'unchecked_point', severity: 'block' as const, field: 'evidence_points[1]', text: 't', message: 'Check this point', source: 'deterministic' }],
    qualifiers: [], bindings: [], critic: null };
  const html = renderToStaticMarkup(<LedgerPanel ledger={ledger} checked={[]} onCheck={() => {}} editable />);
  assert.ok(html.includes('(evidence point 2)') && !html.includes('evidence points[') && !html.includes('claude'));
});

test('E.F2: without a roster, a speaker shows as the transcript names them, never as "Client"', () => {
  assert.equal(speakerLabel('Carmen Cruickshank', []), 'Carmen Cruickshank');
  assert.equal(speakerLabel(null, []), 'Speaker');
});

test('E.F1, E.B19: seeds show their words, and an unanswered one says it stays', () => {
  const selection = { run_id: 'r', week_summary: 'One call.', selection_hash: 'sh', ranking: [], considered_not_selected: [], internal_insights: [],
    unreferenced_moment_ids: [], seed_pairings: [{ seed_ref: 'F1', moment_ids: [], note: 'n', seed_text: 'Couples book faster', unanswered: true }] } as unknown as CardSelection;
  const html = renderToStaticMarkup(<CardWeekPanel weekId="w" selection={selection} cards={[]} roster={[]} busy={false} perform={async () => {}} />);
  assert.ok(html.includes('Couples book faster') && html.includes('stays for the next cycle') && !html.includes('F1:'));
  assert.match(AUTHOR_LABEL, /Whose decision/);
});

test('L.B10: a stale content plan shows beside the week summary, and nothing shows once the plan is current', () => {
  const base = { run_id: 'r', week_summary: 'One call.', selection_hash: 'sh', ranking: [], considered_not_selected: [], internal_insights: [],
    unreferenced_moment_ids: [] };
  const warning = 'The content plan was last updated on 2026-09-01, 48 days ago, so strategic fit ranks against nothing current.';
  const stale = renderToStaticMarkup(<CardWeekPanel weekId="w" selection={{ ...base, plan_warning: warning } as unknown as CardSelection} cards={[]} roster={[]} busy={false} perform={async () => {}} />);
  assert.ok(stale.includes(warning) && stale.includes('role="status"'));
  const current = renderToStaticMarkup(<CardWeekPanel weekId="w" selection={base as unknown as CardSelection} cards={[]} roster={[]} busy={false} perform={async () => {}} />);
  assert.ok(!current.includes('content plan') && !current.includes('role="status"'));
});

test('S.F4: a developed card reads as its rationale only: no brief status, decision, editing or checks in the dialog', () => {
  const developed = { ...angle, approval_status: 'approved', can_edit: true } as unknown as StoredAngle;
  const html = renderToStaticMarkup(<CardReview angle={developed} card={card} roster={roster} busy={false} perform={async () => {}} />);
  assert.ok(html.includes('Topic &amp; editorial rationale') && html.includes('What was said on the call'));
  for (const removed of ['The brief', 'Your decision', 'Edit, add context or ask for a new version', 'Verify before publishing']) assert.ok(!html.includes(removed), removed);
});

// The rubric as GET /weeks/{week_id} carries it (backend gates/rubric.py), shortened.
const rubric: Rubric = {
  version: 'rubric-2.3a.v1', scale: [1, 2, 3, 4, 5], anchors: { 1: 'would not publish', 3: 'publishable after a light reframe', 5: 'publish as is' },
  instruction: 'Rate each card 1 to 5 on each criterion: 1 = would not publish; 3 = publishable after a light reframe; 5 = publish as is.',
  criteria: [{ key: 'wia_is_the_subject', name: 'WIA is the subject', text: 'The card shows what WIA knows.' },
    { key: 'worth_attention', name: 'Worth attention', text: 'It carries a real tension.' }],
  text: 'Review rubric 2.3a (rubric-2.3a.v1)', text_sha256: 'h',
};

test('E.X7: the decision form no longer asks for a rubric rating; a rating given in the body still goes with its version, every point or none', () => {
  const html = renderToStaticMarkup(<CardReview angle={angle} card={card} roster={roster} rubric={rubric} busy={false} perform={async () => {}} />);
  for (const removed of ['Rate this card', rubric.instruction, '1. WIA is the subject.', 'rubric-2.3a.v1']) assert.ok(!html.includes(removed), `no rubric on the decision: ${removed}`);
  const form = { ...emptyForm(), disposition: 'skip' as const, reason_code: 'distinctiveness' };
  const partial = cardDispositionBody({ ...form, rubric: { wia_is_the_subject: 2 } }, card, 'h', false, undefined, null, rubric);
  assert.match('error' in partial ? partial.error : '', /every rubric point/);
  const rated = cardDispositionBody({ ...form, rubric: { wia_is_the_subject: 2, worth_attention: 4 } }, card, 'h', false, undefined, null, rubric);
  assert.deepEqual('body' in rated && [rated.body.rubric_ratings, rated.body.rubric_version], [{ wia_is_the_subject: 2, worth_attention: 4 }, 'rubric-2.3a.v1']);
  const none = cardDispositionBody(form, card, 'h', false, undefined, null, rubric);
  assert.ok('body' in none && !('rubric_ratings' in none.body) && !('rubric_version' in none.body));
  const decided = { ...angle, approval_status: 'rejected', disposition: { disposition: 'skip', reason_code: 'distinctiveness', author: 'Whitney Hodges',
    actor: 'a', note: null, hold_until: null, resulting_item_id: null, central_point_kept: null, created_at: '2026-10-19',
    rubric_ratings: { version: 'rubric-2.3a.v1', criteria: { wia_is_the_subject: 2, worth_attention: 4 }, overall: 3 } } } as unknown as StoredAngle;
  const decidedHtml = renderToStaticMarkup(<CardReview angle={decided} card={card} roster={roster} rubric={rubric} busy={false} perform={async () => {}} />);
  assert.ok(decidedHtml.includes('Skipped · 19 Oct 2026'));
  assert.ok(!decidedHtml.includes('rated 3 of 5') && !decidedHtml.includes('Whitney Hodges'), 'the decision is said without its rating or its author');
});

test('A card left out of the publishing order is shown as held for a later week', () => {
  const second = { ...card, rank: 2, title: 'A second idea' };
  assert.deepEqual(heldCards([1], [card, second]).map(c => c.rank), [2]);
  assert.deepEqual(heldCards([2, 1], [card, second]), []);
});
