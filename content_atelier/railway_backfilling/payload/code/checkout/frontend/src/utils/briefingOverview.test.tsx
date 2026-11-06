import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { briefingOverview, briefingSimilarity } from './briefingOverview';
import { BriefingOverview } from '../components/BriefingOverview';
import { composeContentBriefMarkdown } from '../stages/ideaStages';
import { INITIAL_IDEAS } from '../data/mockData';
import { EDITORIAL_MOCK_IDEAS } from '../data/editorialMockData';

const base = INITIAL_IDEAS[0];
const now = new Date('2026-10-06T12:00:00Z');
const review = { checkedAt: now.toISOString(), periodStart: '2026-06-06T00:00:00Z', periodEnd: '2026-10-06T00:00:00Z', publishedHistoryComplete: true, matches: [] };

test('every brief outlines five deliverables with three distinct reel roles', () => {
  for (const idea of [...INITIAL_IDEAS, ...EDITORIAL_MOCK_IDEAS]) {
    const plan = briefingOverview(idea);
    assert.deepEqual(plan.map(piece => piece.label), ['Email', 'Carousel', 'Reel 1', 'Reel 2', 'Reel 3']);
    assert.equal(new Set(plan.slice(2).map(piece => piece.purpose)).size, 3);
    assert.equal(new Set(plan.slice(2).map(piece => piece.gist)).size, 3);
    const markdown = composeContentBriefMarkdown(idea);
    for (const piece of plan) assert.ok(markdown.includes(piece.gist));
    assert.ok(markdown.includes('Past four months · Similarity review'));
  }
});

test('unreviewed, stale, incomplete and short-window histories cannot claim content is new', () => {
  assert.equal(briefingSimilarity(base, now).status, 'Not verified');
  for (const override of [{ publishedHistoryComplete: false }, { periodStart: '2026-09-01T00:00:00Z' }, { periodEnd: '2026-08-01T00:00:00Z' }]) {
    assert.equal(briefingSimilarity({ ...base, brief: { ...base.brief, similarityReview: { ...review, ...override } } }, now).status, 'Not verified');
  }
  assert.equal(briefingSimilarity({ ...base, brief: { ...base.brief, similarityReview: review } }, now).status, 'No similar content found');
  assert.equal(briefingSimilarity({ ...base, scheduledAt: now.toISOString() }, now).status, 'Not verified');
});

test('similarity reviews retain published sources and document the modifications', () => {
  const match = { title: 'Previous qualification checklist', publishedAt: '2026-08-20T00:00:00Z', similarity: 'Both address early client qualification.', modifications: ['Shift from planners to florists.', 'Replace the checklist with a budget-fit conversation.'] };
  const idea = { ...base, brief: { ...base.brief, similarityReview: { ...review, matches: [match, { ...match, publishedAt: '2025-01-01T00:00:00Z' }] } } };
  const result = briefingSimilarity(idea, now);
  assert.equal(result.status, 'Similar past content found');
  assert.deepEqual(result.matches, [match]);
});

test('saved format plans are honored and cards expose missing publication evidence', () => {
  const plan = { email: 'Personal founder story.', carousel: 'A visual decision checklist.', reels: ['Myth.', 'Demonstration.', 'Next step.'] as [string, string, string] };
  const idea = { ...base, brief: { ...base.brief, contentPlan: plan } };
  assert.deepEqual(briefingOverview(idea).map(piece => piece.gist), [plan.email, plan.carousel, ...plan.reels]);
  const html = renderToStaticMarkup(<BriefingOverview idea={idea} />);
  for (const gist of [plan.email, plan.carousel, ...plan.reels]) assert.ok(html.includes(gist));
  assert.ok(html.includes('Not verified'));
  assert.ok(html.includes('not evidence of publication'));
});
