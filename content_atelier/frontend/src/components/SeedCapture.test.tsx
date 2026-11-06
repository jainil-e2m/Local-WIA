import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { SeedCaptureModal, SeedList, seedRequest, type Seed } from './SeedCapture';

const form = { kind: 'thought' as const, text: '', target_offer: '', source_url: '', author: '', always_true: false };

test('E.F3: a seed is a thought, draft or asset with an optional offer; an asset needs its link', () => {
  assert.deepEqual(seedRequest(form), { error: 'Write the seed.' });
  assert.deepEqual(seedRequest({ ...form, kind: 'asset', text: 'Our tour Reel' }), { error: 'Add the link to the published asset.' });
  assert.match((seedRequest({ ...form, text: 'x', source_url: 'javascript:alert(1)' }) as { error: string }).error, /http/);
  assert.deepEqual(seedRequest({ ...form, text: ' Couples book faster when the first reply names a date. ', target_offer: 'LeadLock', author: 'Whitney Hodges' }),
    { body: { kind: 'thought', text: 'Couples book faster when the first reply names a date.', target_offer: 'LeadLock', source_url: null, author: 'Whitney Hodges', always_true: false } });
});

test('E.F3: open seeds are listed with their author, offer and a withdraw action', () => {
  const seed: Seed = { seed_id: 'seed_one', kind: 'draft', text: 'Draft opening line.', target_offer: 'ELEVATE', source_url: null, author: 'Whitney Hodges', status: 'open', always_true: true, created_at: '', used_in_run_id: null };
  const html = renderToStaticMarkup(<SeedList seeds={[seed]} busy={false} onWithdraw={() => {}} />);
  for (const text of ['Draft', 'Whitney Hodges', 'for ELEVATE', 'every cycle', 'Draft opening line.', 'Withdraw']) assert.ok(html.includes(text), text);
  assert.ok(renderToStaticMarkup(<SeedList seeds={[]} busy={false} onWithdraw={() => {}} />).includes('No open seeds'));
});

test('L.B13: a founder note is one line about one named call, with no offer, link or every-cycle flag', () => {
  const note = { ...form, kind: 'founder_note' as const };
  assert.deepEqual(seedRequest(note), { error: 'Write what stood out to you.' });
  assert.deepEqual(seedRequest({ ...note, text: 'What stood out was how calm she was.' }), { error: 'Choose the call the note is about.' });
  assert.match((seedRequest({ ...note, text: 'x'.repeat(601), transcript_id: 'transcript_a' }) as { error: string }).error, /one line/);
  assert.deepEqual(seedRequest({ ...note, text: ' What stood out was how calm she was. ', transcript_id: 'transcript_a', author: 'Whitney Hodges', target_offer: 'ELEVATE', always_true: true }),
    { body: { kind: 'founder_note', text: 'What stood out was how calm she was.', transcript_id: 'transcript_a', author: 'Whitney Hodges' } });
  const seed: Seed = { seed_id: 'seed_n', kind: 'founder_note', text: 'What stood out was the follow-up.', target_offer: null, source_url: null, author: 'Whitney Hodges', status: 'open', always_true: false, created_at: '', used_in_run_id: null, transcript_id: 'transcript_a' };
  const html = renderToStaticMarkup(<SeedList seeds={[seed]} busy={false} />);
  for (const text of ['Founder note', 'about one call', 'What stood out was the follow-up.']) assert.ok(html.includes(text), text);
});

test('E.F3: the dialog is "Flag an idea": the idea, an optional offer and link, every week or next week, and no author field', () => {
  const html = renderToStaticMarkup(<SeedCaptureModal onClose={() => {}} onSaved={() => {}} />);
  for (const text of ['Flag an idea', 'Your idea *', 'Target offer (optional)', 'Use it every week, not just next week', '>Flag idea</button>']) assert.ok(html.includes(text), text);
  assert.ok(!html.includes('Whose seed?') && !html.includes('Whose decision'), 'no author field: the seed is the signed-in person\'s');
});
