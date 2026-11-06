import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { contentAngleRationale } from './angleRationale';
import { INITIAL_IDEAS } from '../data/mockData';
import { EDITORIAL_MOCK_IDEAS } from '../data/editorialMockData';
import { AngleRationale } from '../components/AngleRationale';

test('legacy angles retain a topic and 100–150-word, five-point decision rationale', () => {
  for (const idea of [...INITIAL_IDEAS, ...EDITORIAL_MOCK_IDEAS.filter(idea => !idea.editorialContext)]) {
    const snapshot = JSON.stringify(idea);
    const rationale = contentAngleRationale(idea);
    const words = rationale.points.map(point => `${point.label} ${point.text}`).join(' ').split(/\s+/).length;
    assert.ok(words >= 100 && words <= 150, `${idea.id}: ${words} words`);
    assert.equal(rationale.topic, idea.title);
    assert.equal(rationale.points.length, 5);
    assert.ok(rationale.points.some(point => point.text.includes(idea.suggestedCta)));
    assert.equal(JSON.stringify(idea), snapshot);
  }
});

test('sourced angles provide a fuller rationale without mutating their editorial direction', () => {
  for (const idea of EDITORIAL_MOCK_IDEAS.filter(idea => idea.editorialContext)) {
    const snapshot = JSON.stringify(idea);
    const rationale = contentAngleRationale(idea);
    const words = rationale.points.map(point => `${point.label} ${point.text}`).join(' ').split(/\s+/).length;
    assert.ok(words >= 150 && words <= 300, `${idea.id}: ${words} words`);
    assert.ok(rationale.topic.length > 0);
    assert.equal(rationale.points.length, 6);
    assert.ok(rationale.points.some(point => point.label === 'Commercial opportunity' && point.text.length > 0));
    assert.ok(idea.editorialContext!.suggestedInvitation.length > 0);
    assert.equal(JSON.stringify(idea), snapshot);
  }
});

test('saved AI rationales are preserved, while backfills are honestly labeled', () => {
  const stored = { topic: 'Client qualification', points: [{ label: 'Gist', text: 'Stored rationale from the generation service.' }], source: 'llm' as const };
  assert.equal(contentAngleRationale({ ...INITIAL_IDEAS[0], angleRationale: stored }), stored);
  const mock = renderToStaticMarkup(<AngleRationale idea={EDITORIAL_MOCK_IDEAS.find(idea => !idea.editorialContext)!} />);
  assert.ok(mock.includes('Mock rationale'));
  assert.equal((mock.match(/<li>/g) ?? []).length, 5);
  assert.ok(mock.includes('Commercial opportunity'));
  assert.ok(mock.includes('Expected impact'));
  const legacy = renderToStaticMarkup(<AngleRationale idea={INITIAL_IDEAS[0]} />);
  assert.ok(legacy.includes('From existing editorial inputs'));
  assert.ok(!legacy.includes('AI-generated rationale'));
});
