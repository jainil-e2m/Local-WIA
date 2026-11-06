import test from 'node:test';
import assert from 'node:assert/strict';
import { plainMessage } from './plainText';

test('server text loses commands, plan codes, delegation notes and internal ids, and keeps its sentence', () => {
  assert.equal(plainMessage('It renews on Monday 26 October at 00:00 UTC, or an approver can raise it (storage_cli budgets set).. They start by themselves.'),
    'It renews on Monday 26 October at 00:00 UTC, or an approver can raise it. They start by themselves.');
  assert.equal(plainMessage('Excluded: private business finance, never content (N4, decided under delegation, D12)'), 'Excluded: private business finance, never content');
  assert.equal(plainMessage('Superseded: the backfill runs on profile v2 (2.B11); v1 kept'), 'Superseded: the backfill runs on profile v2; v1 kept');
  assert.equal(plainMessage('Develop by the team under delegation (D12)'), 'Develop by the team');
  assert.equal(plainMessage('restore it, or regenerate the brief (storage_cli brief --regenerate)'), 'restore it, or regenerate the brief');
  assert.equal(plainMessage('A plain sentence (with a note) stays as it is.'), 'A plain sentence (with a note) stays as it is.');
  assert.equal(plainMessage('Promotes: the ELEVATE waitlist (F-megaemail-1, 2026-10, team). A guided launch (R-7).'), 'Promotes: the ELEVATE waitlist. A guided launch.');
  assert.equal(plainMessage('3 months of support (D-delivery-2, 2026-07-17)'), '3 months of support');
  assert.equal(plainMessage(null), '');
});
