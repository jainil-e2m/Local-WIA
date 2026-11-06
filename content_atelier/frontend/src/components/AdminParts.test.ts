import { test } from 'node:test';
import assert from 'node:assert/strict';
import { plainReason, shortDay } from './AdminParts';

test('Admin screens: a sentence the server wrote is shown without codes, commands or delegation notes', () => {
  assert.equal(plainReason("Personal business finance, not client evidence (D4, decided under delegation, R12)"), 'Personal business finance, not client evidence');
  assert.equal(plainReason("Implementing engineer under WIA's delegation (D12, 18 October 2026)"), 'Implementing engineer');
  assert.equal(plainReason('Duplicate of the confirmed offer sheet entry (KB 05)'), 'Duplicate of the confirmed offer sheet entry');
  assert.equal(plainReason('Superseded: replaced by profile v2 (2.B11); v1 kept'), 'Superseded: replaced by profile v2; v1 kept');
  assert.equal(plainReason('Waiting for budget: raise it (storage_cli budgets set) today'), 'Waiting for budget: raise it today');
  assert.equal(plainReason('Sent to the list (about 840 people)'), 'Sent to the list (about 840 people)', 'ordinary brackets stay');
  assert.equal(plainReason('Spent (USD 1.50 of USD 2.00)'), 'Spent (USD 1.50 of USD 2.00)', 'amounts stay');
  assert.equal(plainReason(null), '');
});

test('Admin screens: a date reads "26 Oct 2026"', () => {
  assert.equal(shortDay('2026-10-26'), '26 Oct 2026');
  assert.equal(shortDay('2026-10-24T22:00:00Z'), '24 Oct 2026');
  assert.equal(shortDay(null), '');
});
