import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { FATHOM_WEEKLY_ANGLES, FATHOM_STARTER_PLANS } from './fathomWeeklyAngles';
import { FATHOM_BRIEFS_PREPARED_AT, prepareFathomContentBrief } from './fathomContentBriefs';
import { mergeEditorialMocks } from './editorialMockData';
import { composeContentBriefMarkdown } from '../stages/ideaStages';
import { briefingOverview } from '../utils/briefingOverview';
import { MarkdownDocument } from '../components/MarkdownDocument';
import { IdeaDetailModal } from '../components/IdeaDetailModal';

test('each requested brief gives executable direction for five distinct deliverables and bounded evidence', () => {
  for (const idea of FATHOM_WEEKLY_ANGLES) {
    const direction = idea.brief.productionBrief!;
    assert.equal(direction.preparedAt, FATHOM_BRIEFS_PREPARED_AT);
    assert.deepEqual(direction.narrative.map(beat => beat.beat), ['Hook', 'Problem', 'Main point', 'Transformation', 'CTA']);
    assert.deepEqual(direction.carousel.slides.map(slide => slide.number), [1, 2, 3, 4, 5, 6, 7, 8]);
    assert.equal(direction.reels.length, 3);
    assert.equal(new Set(direction.reels.map(reel => reel.role)).size, 3);
    assert.equal(new Set(direction.reels.map(reel => reel.hookDirection)).size, 3);
    assert.ok(direction.email.outline.length >= 5);
    assert.ok(direction.evidencePolicy.established.length && direction.evidencePolicy.hypotheses.length && direction.evidencePolicy.excludedClaims.length);
    assert.ok(direction.cta.destination && direction.success.measurementNote && direction.reviewChecklist.length);
    assert.equal(idea.pack, undefined);
    assert.equal(idea.briefApprovedAt, undefined);
    assert.deepEqual(briefingOverview(idea).slice(2).map(piece => piece.purpose), direction.reels.map(reel => reel.role));
    assert.deepEqual(briefingOverview(idea).map(piece => piece.gist), [direction.email.summary, direction.carousel.summary, ...direction.reels.map(reel => reel.summary)]);
  }
});

test('cached proposal plans upgrade to the complete brief while custom format edits survive', () => {
  const seed = FATHOM_WEEKLY_ANGLES[0];
  const starter = FATHOM_STARTER_PLANS[seed.id]!;
  const saved = { ...seed, gate: 'gate1_angle' as const, angleApprovedAt: undefined, brief: { ...seed.brief, productionBrief: undefined, contentPlan: { ...starter, reels: [starter.reels[0], 'Custom saved reel two', starter.reels[2]] as [string, string, string] } } };
  const upgraded = mergeEditorialMocks([saved]).find(idea => idea.id === seed.id)!;
  assert.equal(upgraded.brief.contentPlan!.email, seed.brief.productionBrief!.email.summary);
  assert.equal(upgraded.brief.contentPlan!.reels[1], 'Custom saved reel two');
  assert.equal(upgraded.brief.contentPlan!.reels[2], seed.brief.productionBrief!.reels[2].summary);
  assert.equal(upgraded.brief.contentPlan!.reels[0], seed.brief.productionBrief!.reels[0].summary);
});

test('full brief export retains all direction, source passages, unresolved questions and reference links', () => {
  for (const idea of FATHOM_WEEKLY_ANGLES) {
    const markdown = composeContentBriefMarkdown(idea);
    const direction = idea.brief.productionBrief!;
    for (const section of ['Strategic assignment', 'Narrative framework', 'Evidence boundaries', 'Founder voice', 'What we will generate', 'CTA and commercial connection', 'Creative and asset direction', 'How to evaluate the content', 'Source passages for internal review', 'Production handoff checklist']) assert.ok(markdown.includes(`## ${section}`));
    for (const slide of direction.carousel.slides) assert.ok(markdown.includes(slide.detail) && markdown.includes(slide.visualDirection));
    for (const reel of direction.reels) for (const beat of reel.beats) assert.ok(markdown.includes(beat));
    for (const source of idea.editorialContext!.sources) assert.ok(markdown.includes(source.quote) && markdown.includes(source.url));
    for (const question of idea.brief.openQuestionsForWhitney) assert.ok(markdown.includes(question));
    const html = renderToStaticMarkup(<MarkdownDocument markdown={markdown} />);
    for (const source of idea.editorialContext!.sources) assert.ok(html.includes(`href="${source.url}"`));
    assert.ok(markdown.includes('Not verified'));
    assert.ok(!markdown.includes('All claims verified and cleared'));
  }
});

test('brief hydration retains angle status, saved edits and existing approvals', () => {
  const seed = FATHOM_WEEKLY_ANGLES[0];
  const saved = { ...seed, gate: 'gate1_angle' as const, angleApprovedAt: undefined, title: 'Saved title', brief: { ...seed.brief, productionBrief: undefined, coreInsight: 'Saved insight', openQuestionsForWhitney: ['Saved steer note'], contentPlan: { email: 'Saved email direction', carousel: 'Saved carousel', reels: ['Saved one', 'Saved two', 'Saved three'] as [string, string, string] } } };
  const migrated = mergeEditorialMocks([saved]);
  const item = migrated.find(idea => idea.id === saved.id)!;
  assert.equal(item.gate, 'gate1_angle');
  assert.equal(item.angleApprovedAt, undefined);
  assert.equal(item.title, saved.title);
  assert.equal(item.brief.coreInsight, saved.brief.coreInsight);
  assert.deepEqual(item.brief.contentPlan, saved.brief.contentPlan);
  assert.deepEqual(item.brief.openQuestionsForWhitney, saved.brief.openQuestionsForWhitney);
  assert.equal(item.briefApprovedAt, undefined);
  assert.equal(item.pack, undefined);
  assert.deepEqual(mergeEditorialMocks(migrated), migrated);
  const approved = { ...saved, gate: 'gate3_pack' as const, angleApprovedAt: '2026-10-06T10:00:00Z', briefApprovedAt: '2026-10-06T10:10:00Z' };
  const retained = prepareFathomContentBrief(approved);
  assert.equal(retained.gate, approved.gate);
  assert.equal(retained.angleApprovedAt, approved.angleApprovedAt);
  assert.equal(retained.briefApprovedAt, approved.briefApprovedAt);
  const edited = { ...item, brief: { ...item.brief, productionBrief: { ...item.brief.productionBrief!, readerPromise: 'Saved production edit' } } };
  assert.equal(prepareFathomContentBrief(edited), edited);
});

test('the brief modal renders professional direction without presenting it as a completed LLM response or pack', () => {
  const html = renderToStaticMarkup(<IdeaDetailModal idea={{ ...FATHOM_WEEKLY_ANGLES[2], gate: 'gate2_brief' }} initialTab="brief" onClose={() => {}} onUpdateGate={() => {}} onUpdateCta={() => {}} />);
  assert.ok(html.includes('Complete content brief'));
  assert.ok(html.includes('Editorial &amp; production direction'));
  assert.ok(html.includes('Brief awaiting approval'));
  assert.ok(html.includes('configuration'));
  assert.ok(html.includes('Approve Brief'));
  assert.ok(!html.includes('LLM response'));
  assert.ok(!html.includes('one-page brief'));
});

test('brief source links render as links while unsupported URL schemes remain text', () => {
  const html = renderToStaticMarkup(<MarkdownDocument markdown="[Source](https://fathom.video/calls/123?timestamp=12)\n\n[Unsafe](javascript:alert(1))" />);
  assert.ok(html.includes('href="https://fathom.video/calls/123?timestamp=12"'));
  assert.ok(html.includes('rel="noopener noreferrer"'));
  assert.ok(!html.includes('href="javascript:'));
});
