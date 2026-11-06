import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  CONSENT_STATUSES, MOMENT_TYPES, NO_MOMENT_FILTERS, consentLabel, consentList, consentReasons, facetQuery, failedChecks, highlight, matchReason, momentFilterCount,
  momentQuery, momentRange, momentTypeLabel, readMomentFilters, repairNote, searchRequest, searching, speakerLabel, whenLine, writeMomentFilters,
} from './moments';

const read = (query: string) => readMomentFilters(new URLSearchParams(query));

test('2.F1: the plain ledger has a plain URL, and every filter round-trips through the query string', () => {
  assert.equal(writeMomentFilters(NO_MOMENT_FILTERS).toString(), '');
  assert.deepEqual(read(''), NO_MOMENT_FILTERS);
  const filters = {
    q: 'reply fast', from: '2026-01-01', to: '2026-03-31', client_id: 'client_maple', source_type: 'zoom', call_type: 'client_1to1', speaker_role: 'client', moment_type: 'data_point',
    consent_status: 'all', topic_id: 'topic_1', unverified: true, limit: 50, offset: 100,
  } as const;
  assert.deepEqual(read(writeMomentFilters(filters).toString()), filters);
  assert.equal(momentFilterCount(filters), 11);
  assert.equal(momentFilterCount({ ...filters, limit: 10, offset: 0 }), 11, 'the page is not a filter');
});

test('2.F1: anything in the URL that is not a known value is ignored', () => {
  const filters = read('source_type=email&call_type=sales&speaker_role=gossip&moment_type=rumour&consent_status=sure&client_id=a/b&topic_id=x y&from=2026-02-30&to=tomorrow&limit=7&offset=-3&unverified=yes');
  assert.deepEqual(filters, NO_MOMENT_FILTERS);
  assert.equal(read('offset=abc').offset, 0);
  assert.equal(read(`q=${'x'.repeat(300)}`).q.length, 200);
  assert.equal(read('q=%20%20').q, '');
});

test('2.F1: all twelve moment types, including the five new ones, are filters with plain names', () => {
  assert.equal(MOMENT_TYPES.length, 12);
  for (const type of ['testimonial', 'question', 'teaching', 'soundbite', 'data_point']) assert.ok(MOMENT_TYPES.includes(type as never), type);
  assert.equal(momentTypeLabel('data_point'), 'Data point');
  assert.equal(momentTypeLabel('mechanism'), 'How it works');
  assert.equal(momentTypeLabel('something_new'), 'Something new');
  assert.equal(momentTypeLabel(null), 'Untyped');
  for (const type of MOMENT_TYPES) assert.equal(read(`moment_type=${type}`).moment_type, type);
});

test('2.F1: roles and consent are named in plain words', () => {
  assert.equal(speakerLabel('staff'), 'WIA team');
  assert.equal(speakerLabel('client'), 'Client');
  assert.equal(speakerLabel('prospect'), 'Prospect');
  assert.equal(speakerLabel('ai_agent'), 'AI note-taker');
  assert.equal(speakerLabel(null), 'Role unknown');
  assert.deepEqual(CONSENT_STATUSES.map(consentLabel), ['Cleared for naming', 'Anonymise', 'Internal only', 'Do not use']);
  assert.equal(consentLabel('some_new_status'), 'Some new status');
});

test('2.F1: the list request carries the filters the API takes, and leaves consent to the API\'s default unless chosen', () => {
  assert.deepEqual(momentQuery(NO_MOMENT_FILTERS), { limit: 25, offset: 0 });
  assert.deepEqual(momentQuery({ ...NO_MOMENT_FILTERS, client_id: 'c', source_type: 'fathom', call_type: 'workshop', speaker_role: 'prospect', moment_type: 'soundbite', topic_id: 't', consent_status: 'internal_only', limit: 10, offset: 20 }),
    { client_id: 'c', source_type: 'fathom', call_type: 'workshop', speaker_role: 'prospect', moment_type: 'soundbite', consent_status: 'internal_only', topic_id: 't', limit: 10, offset: 20 });
  assert.equal(momentQuery({ ...NO_MOMENT_FILTERS, consent_status: 'all' }).consent_status, 'cleared,anonymise,internal_only,do_not_use');
  assert.equal(momentQuery({ ...NO_MOMENT_FILTERS, unverified: true }).quote_verified, 'any');
  assert.equal(momentQuery(NO_MOMENT_FILTERS).quote_verified, undefined, 'verified quotes only is the API\'s default');
  assert.equal(consentList(''), undefined);
  assert.deepEqual(consentList('do_not_use'), ['do_not_use']);
});

test('2.F1: the date window is sent with an offset, and its last day is included', () => {
  const query = momentQuery({ ...NO_MOMENT_FILTERS, from: '2026-01-01', to: '2026-12-31' });
  assert.equal(query.from, '2026-01-01T00:00:00Z');
  assert.equal(query.to, '2027-01-01T00:00:00Z');
  assert.equal(searchRequest({ ...NO_MOMENT_FILTERS, q: 'x', to: '2026-02-28' }).filters?.date_to, '2026-03-01T00:00:00Z');
});

test('2.F1: words are searched unless unverified quotes are asked for; the counts never carry a page, and carry no words while searching', () => {
  assert.equal(searching({ ...NO_MOMENT_FILTERS, q: 'reply' }), true);
  assert.equal(searching({ ...NO_MOMENT_FILTERS, q: 'reply', unverified: true }), false);
  assert.equal(searching(NO_MOMENT_FILTERS), false);
  assert.deepEqual(facetQuery({ ...NO_MOMENT_FILTERS, q: 'reply', client_id: 'c' }), { client_id: 'c' });
  assert.deepEqual(facetQuery({ ...NO_MOMENT_FILTERS, q: 'reply', unverified: true }), { q: 'reply', quote_verified: 'any' });
});

test('2.F1: the search request is the words with the same filters, as the lists the API takes', () => {
  assert.deepEqual(searchRequest({ ...NO_MOMENT_FILTERS, q: 'how fast' }), { text: 'how fast', k: 50, scope: 'moments', filters: {} });
  assert.deepEqual(searchRequest({ ...NO_MOMENT_FILTERS, q: 'x', client_id: 'c', source_type: 'zoom', call_type: 'workshop', speaker_role: 'client', moment_type: 'result', topic_id: 't', consent_status: 'all', from: '2026-01-01' }).filters,
    { client_id: 'c', source_type: 'zoom', call_type: 'workshop', speaker_role: ['client'], moment_type: ['result'], consent_status: ['cleared', 'anonymise', 'internal_only', 'do_not_use'], topic_id: 't', date_from: '2026-01-01T00:00:00Z' });
});

test('2.F1: a match says why it was found, in words', () => {
  assert.equal(matchReason(['phrase', 'semantic']), 'Matches your words and their meaning');
  assert.equal(matchReason(['phrase']), 'Matches your words');
  assert.equal(matchReason(['semantic']), 'Close in meaning to your search');
  assert.equal(matchReason([]), 'Matches your search');
});

test('2.F1: dates and ranges read plainly', () => {
  assert.equal(whenLine('2026-03-04T15:00:00Z'), '4 Mar 2026');
  assert.equal(whenLine(null), 'Date not recorded');
  assert.equal(momentRange(40, 25, 15), '26 to 40 of 40');
  assert.equal(momentRange(0, 0, 0), 'No moments');
});

test('2.F2: the reasons behind a consent status come from what the backend recorded, in words', () => {
  assert.deepEqual(consentReasons({ consent: { status: 'cleared', client_consent: 'may_name', sensitivity: 'public_candidate', evidence_kind: 'direct_quote' } }),
    ['The client has agreed to be named.', 'The line looks suitable for public use.', 'It is in the speaker\'s own words.']);
  assert.deepEqual(consentReasons({ consent: { status: 'do_not_use', client_consent: 'no_use', sensitivity: 'internal_only', evidence_kind: 'team_report' } }),
    ['The client has asked that nothing from them is used.', 'The line was marked as for the team only.', 'A team member relayed it; the client did not say it themselves.']);
  assert.deepEqual(consentReasons({ consent: { status: 'anonymise', client_consent: null } }), ['No permission is recorded for this client.']);
  assert.deepEqual(consentReasons({}), []);
});

test('2.F2: failed checks are named in words: a figure the source does not contain, one found only around the quote, a claim from the wrong voice', () => {
  const absent = failedChecks({ numbers: { passed: false, absent: ['$14,000'], context_only: [], figures: [] }, role_plausibility: { passed: true } });
  assert.deepEqual(absent, { recorded: true, failures: ['The source does not contain the figure $14,000.'] });
  const context = failedChecks({ numbers: { passed: false, absent: [], context_only: ['12'] } });
  assert.deepEqual(context.failures, ['The figure 12 appears only in the conversation around the quote, not in the line itself.']);
  const role = failedChecks({ role_plausibility: { passed: false, speaker_role: 'staff', original_type: 'testimonial', moment_type: 'observation', evidence_kind: 'team_report', reason: 'A testimonial is the client\'s to claim' } });
  assert.deepEqual(role.failures, ['It was first tagged as a testimonial, but it was said by someone on the WIA team, and that is the client\'s to claim. It is shown as an observation instead.']);
  const relay = failedChecks({ role_plausibility: { passed: false, speaker_role: 'unknown', original_type: 'result', moment_type: 'result' } });
  assert.match(relay.failures[0], /said by someone whose role could not be worked out/);
  assert.match(relay.failures[0], /treated as a team member relaying it/);
  assert.deepEqual(failedChecks({ numbers: { passed: true, absent: [], context_only: [] } }), { recorded: true, failures: [] });
  assert.deepEqual(failedChecks({}), { recorded: false, failures: [] });
});

test('2.F2: a repaired quote is described as matched to the transcript\'s own wording', () => {
  assert.equal(repairNote(null), null);
  assert.deepEqual(repairNote({ rule: 'normalised-whitespace-punctuation.v1', original_quote: 'we reply', repaired_quote: 'We reply', anchor_span_id: 'p_1' }),
    { note: 'The quote was matched to the transcript\'s own wording.', before: 'we reply', after: 'We reply' });
});

test('2.F2: the quote is marked inside the passage that holds it, by its place and failing that by its words', () => {
  const passage = { text: 'Honestly, We reply fast. It changed.', start: 100, end: 136, anchor: true, cited: true };
  assert.deepEqual(highlight(passage, { start: 110, end: 124, quote: 'We reply fast.' }, null), ['Honestly, ', 'We reply fast.', ' It changed.']);
  // A place that does not hold the quote (for instance offsets counted differently) falls back to finding the words.
  assert.deepEqual(highlight(passage, { start: 105, end: 119, quote: 'We reply fast.' }, null), ['Honestly, ', 'We reply fast.', ' It changed.']);
  assert.equal(highlight({ ...passage, cited: false, anchor: false }, null, 'We reply fast.'), null, 'a passage that is only context is not marked');
  assert.equal(highlight(passage, null, 'Something else'), null);
  assert.equal(highlight(passage, null, null), null);
});
