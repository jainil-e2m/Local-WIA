import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderScreen } from '../testing/render';
import { KNOWLEDGE_TABS, KnowledgePage } from './KnowledgePage';

test('L.F1 to L.F3: the Knowledge page offers the three views as tabs, opening on the review queue', () => {
  assert.deepEqual(KNOWLEDGE_TABS.map(([, label]) => label), ['Review queue', 'What the system knows', 'Versions']);
  const out = renderScreen(<KnowledgePage />, { url: '/knowledge/review' });
  assert.ok(out.includes('<h1') && out.includes('Knowledge'));
  assert.match(out, /aria-current="page"[^>]*>Review queue</);
  assert.ok(out.includes('aria-label="Review queue"'));
  assert.ok(renderScreen(<KnowledgePage tab="versions" />, { url: '/knowledge/versions' }).includes('Compile a new version'));
});
