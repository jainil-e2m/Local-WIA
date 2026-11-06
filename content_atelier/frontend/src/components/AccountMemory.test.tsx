import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import type { AccountMemory } from '../api/schema';
import { AccountMemoryPanel, entryDate } from './AccountMemory';

/* 3.B17: beside a client story card (Gate 1) and its brief (Gate 2), the account's naming, current state and what happened
   after the card's call; internal meetings' remarks apart, for the reviewer only. Synthetic account. */

const ACCOUNT = {
  client_id: 'client_fern', name: 'Fernbrook Estate', business: 'wedding venue', status: 'active', naming: 'anonymise', calls: 2,
  last_call: { date: '2026-09-15', precision: 'day', title: 'Fernbrook monthly call' },
  latest: [{ date: '2026-09-15', precision: 'day', kind: 'measured', text: 'The owner reported fewer cancelled tours.', source: { kind: 'call', title: 'Fernbrook monthly call' } }],
  cautions: [], card_call_date: '2026-06-10',
  what_happened_next: [{ date: '2026-09-15', precision: 'day', kind: 'measured', text: 'The owner reported fewer cancelled tours.', source: { kind: 'call', title: 'Fernbrook monthly call' } }],
  internal_since: [{ date: '2026-09-07', precision: 'week', kind: 'internal', text: 'Tina added the owner video to the first text.', source: { kind: 'internal_meeting', title: 'WIA Weekly Meeting' } }],
} as unknown as AccountMemory;

test('3.B17: the panel shows the account, its naming, the last call, what happened next and internal remarks apart', () => {
  const html = renderToStaticMarkup(<AccountMemoryPanel accounts={[ACCOUNT]} />);
  for (const text of ['Fernbrook Estate', 'Anonymise in public copy', '2 calls on record', 'the last 15 Sept 2026', 'What happened after this card',
    'fewer cancelled tours', 'From internal meetings (for you, never for copy)', 'week of 7 Sept 2026', 'Internal meeting']) assert.ok(html.includes(text), text);
  assert.equal(renderToStaticMarkup(<AccountMemoryPanel accounts={[]} />), '', 'a card with no account shows nothing');
  const quiet = renderToStaticMarkup(<AccountMemoryPanel accounts={[{ ...ACCOUNT, what_happened_next: [], internal_since: [] }]} />);
  assert.ok(quiet.includes('Nothing on record after this card'));
});

test('3.B17: a date known only to its week says so', () => {
  assert.equal(entryDate('2026-06-08', 'week'), 'week of 8 Jun 2026');
  assert.equal(entryDate(null, 'undated'), 'Undated');
});
