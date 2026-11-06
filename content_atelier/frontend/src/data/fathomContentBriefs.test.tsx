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

test('each supplied brief retains its narrative, format directions, boundaries and original wording', () => {
  assert.equal(FATHOM_WEEKLY_ANGLES.length, 3);
  for (const [index, idea] of FATHOM_WEEKLY_ANGLES.entries()) {
    const direction = idea.brief.productionBrief!;
    assert.equal(direction.preparedAt, FATHOM_BRIEFS_PREPARED_AT);
    assert.deepEqual(direction.narrative.map(beat => beat.beat), ['Hook', 'Problem', 'Main point', 'Transformation', 'CTA']);
    assert.equal(direction.carousel.slides.length, [10, 10, 9][index]);
    assert.equal(direction.reels.length, 3);
    assert.ok(direction.evidencePolicy.established[0].length > 0);
    assert.ok(direction.evidencePolicy.excludedClaims[0].length > 0);
    assert.equal(idea.pack, undefined);
    assert.equal(idea.briefApprovedAt, undefined);
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

test('the full brief export preserves the supplied fields without adding generated copy', () => {
  for (const idea of FATHOM_WEEKLY_ANGLES) {
    const markdown = composeContentBriefMarkdown(idea);
    assert.equal(markdown, idea.suppliedCopy!.brief);
    for (const heading of ['Central point', 'Strategic purpose', 'Audience and reason to care', 'WIA perspective', 'Supporting example', 'Narrative outline', 'Format and creative approach', 'CTA and essential boundaries']) assert.ok(markdown.includes('### ' + heading));
    assert.ok(markdown.includes(idea.brief.coreInsight));
    assert.ok(markdown.includes(idea.sourceDetails));
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
  assert.ok(!html.includes('Complete content brief'));
  assert.ok(!html.includes('A source-based production brief for the email'));
  assert.ok(html.includes('Content Brief'));
  assert.ok(html.includes('Content brief overview'));
  assert.ok(html.includes('Brief awaiting approval'));
  assert.ok(html.includes('AI makes it easy to change your ads'));
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
