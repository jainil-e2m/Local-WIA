import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { IdeaDetailModal } from './IdeaDetailModal';
import { INITIAL_IDEAS } from '../data/mockData';
import { generateContentPackForIdea } from '../utils/packGenerator';
import { draftPackToText, selectDraftContents } from '../stages/ideaStages';
import { FATHOM_WEEKLY_ANGLES } from '../data/fathomWeeklyAngles';

const source = INITIAL_IDEAS[0];
const idea = { ...source, gate: 'gate3_pack' as const, pack: generateContentPackForIdea(source) };
const callbacks = { onClose: () => {}, onUpdateGate: () => {}, onUpdateCta: () => {}, onApprovePack: () => {}, onSchedule: () => {} };

test('supplied packs separate email details, every slide and reel screens while exporting the original copy', () => {
  for (const [index, seed] of FATHOM_WEEKLY_ANGLES.entries()) {
    const pack = seed.mockContentPack!;
    const pieces = selectDraftContents(pack);
    assert.equal(pieces.length, 5);
    assert.deepEqual(pieces[0].sections.map(section => section.label), ['Date', 'Send time', 'Recipients', 'Subject', 'Preview text', 'Email body']);
    assert.ok(pieces[0].sections.at(-1)!.text.startsWith('Hi {{contact.first_name}},'));
    assert.equal(pieces[1].sections.filter(section => section.label.startsWith('Slide ')).length, [10, 10, 9][index]);
    assert.equal(pieces[1].sections.at(-1)!.label, 'Carousel caption');
    assert.equal(pieces[4].sections.filter(section => section.label.startsWith('Screen ')).length, [2, 6, 3][index]);
    assert.ok(!pieces[4].sections.some(section => section.label === 'Spoken script'));
    for (const reel of pieces.slice(2)) assert.equal(reel.sections.at(-1)!.label, 'Caption');
    const exported = draftPackToText(seed.title, pieces);
    for (const raw of [pack.suppliedCopy!.email, pack.suppliedCopy!.carousel, ...pack.suppliedCopy!.reels]) assert.ok(exported.includes(raw));
    const html = renderToStaticMarkup(<IdeaDetailModal idea={{ ...seed, gate: 'gate3_pack', pack }} initialTab="pack" initialContentOrder={2} {...callbacks} />);
    assert.equal((html.match(/aria-label="Slide \d+"/g) ?? []).length, [10, 10, 9][index]);
    assert.ok(!html.includes('Slides &amp; caption'));
  }
});

test('brief shows formatted content without Rendered and Markdown view options', () => {
  const html = renderToStaticMarkup(<IdeaDetailModal idea={idea} initialTab="brief" {...callbacks} />);
  assert.ok(!/>Rendered<\/button>/.test(html));
  assert.ok(!/>Markdown<\/button>/.test(html));
  assert.ok(!html.includes('<pre'));
  assert.ok(html.includes('Copy'));
  assert.ok(html.includes('View content pack'));
});

test('modal footer shows recorded date without the internal idea ID', () => {
  const html = renderToStaticMarkup(<IdeaDetailModal idea={idea} {...callbacks} />);
  assert.ok(html.includes('Recorded:'));
  assert.ok(!html.includes(`ID: ${idea.id}`));
});

test('every modal stage uses a fixed viewport height and an internal stable scroll area', () => {
  for (const tab of ['gates', 'brief', 'pack', 'schedule', 'research'] as const) {
    const html = renderToStaticMarkup(<IdeaDetailModal idea={idea} initialTab={tab} {...callbacks} />);
    assert.ok(html.includes(' h-[92dvh] max-h-[92dvh]'));
    assert.ok(html.includes('min-h-0 flex-1 overflow-y-scroll [scrollbar-gutter:stable]'));
    assert.ok(html.includes('data-lenis-prevent="true"'));
  }
});

test('modal removes duplicate headers and target selector and orders the four stages', () => {
  const html = renderToStaticMarkup(<IdeaDetailModal idea={idea} {...callbacks} />);
  assert.ok(!html.includes('aria-label="Target offer"'));
  assert.ok(!html.includes('Source:'));
  assert.ok(!html.includes('Approvals &amp; Gates'));
  assert.ok(!html.includes('Brief received'));
  assert.ok(!html.includes('Publishing handoff'));
  const nav = html.match(/<nav[^>]*aria-label="Content stages"[\s\S]*?<\/nav>/)?.[0] ?? '';
  assert.ok(nav.indexOf('Content Angle') < nav.indexOf('Content Brief'));
  assert.ok(nav.indexOf('Content Brief') < nav.indexOf('Content Pack'));
  assert.ok(nav.indexOf('Content Pack') < nav.indexOf('Schedule'));
  assert.equal((nav.match(/<button/g) ?? []).length, 4);
  assert.ok(html.includes('View source research'));
});

test('scheduling requires pack publishing approval and uses the shared schedule/reschedule control', () => {
  const packHtml = renderToStaticMarkup(<IdeaDetailModal idea={idea} initialTab="pack" {...callbacks} />);
  assert.ok(packHtml.includes('Approve Content Pack &amp; Schedule'));
  assert.match(packHtml, /<button[^>]*disabled=""[^>]*>Schedule<\/button>/);
  const locked = renderToStaticMarkup(<IdeaDetailModal idea={idea} initialTab="schedule" {...callbacks} />);
  assert.ok(locked.includes('Approve the content pack for publishing before scheduling.'));
  assert.ok(!locked.includes('aria-haspopup="dialog"'));
  const approved = { ...idea, publishingApprovedAt: '2026-10-06T12:00:00Z' };
  const ready = renderToStaticMarkup(<IdeaDetailModal idea={approved} initialTab="schedule" {...callbacks} />);
  assert.ok(ready.includes('Awaiting scheduling'));
  assert.ok(ready.includes('aria-haspopup="dialog"'));
  assert.ok(ready.includes('>Schedule</button>'));
  for (const piece of selectDraftContents(idea.pack)) assert.ok(ready.includes(renderToStaticMarkup(<p>{piece.title}</p>).slice(3, -4)));
  const scheduled = renderToStaticMarkup(<IdeaDetailModal idea={{ ...approved, scheduledAt: '2026-10-10T04:00:00Z' }} initialTab="schedule" {...callbacks} />);
  assert.ok(scheduled.includes('Reschedule'));
  assert.ok(scheduled.includes('IST'));
  assert.ok(scheduled.includes('Scheduled Content and the Home calendar'));
});

test('pack view has five deliverable tabs but renders only one content panel', () => {
  const html = renderToStaticMarkup(<IdeaDetailModal idea={idea} initialTab="pack" {...callbacks} />);
  for (const label of ['Email', 'Carousel', 'Reel 1', 'Reel 2', 'Reel 3']) assert.ok(html.includes(`>${label}</button>`));
  assert.equal((html.match(/role="tabpanel"/g) ?? []).length, 1);
  assert.ok(html.includes('aria-labelledby="pack-piece-tab-1"'));
  assert.ok(!html.includes('5 generated contents'));
  assert.ok(!html.includes('Voice check passed'));
  assert.ok(!html.includes('Overlap'));
  assert.ok(html.indexOf('Copy all Content') < html.indexOf('>Done</button>'));
});

test('brief approval remains available in the Content Brief stage', () => {
  const html = renderToStaticMarkup(<IdeaDetailModal idea={{ ...idea, gate: 'gate2_brief', pack: undefined }} initialTab="brief" {...callbacks} />);
  assert.ok(html.includes('Approve Brief &amp; Generate Content Pack'));
  assert.ok(html.includes('disabled=""'));
});

test('calendar links can open each matching deliverable directly', () => {
  for (const order of [1, 2, 3, 4, 5]) {
    const html = renderToStaticMarkup(<IdeaDetailModal idea={idea} initialTab="pack" initialContentOrder={order} {...callbacks} />);
    assert.equal((html.match(/role="tabpanel"/g) ?? []).length, 1);
    assert.ok(html.includes(`aria-labelledby="pack-piece-tab-${order}"`));
  }
});

test('copy all exports all five pieces and captions, not just the selected tab', () => {
  const pieces = selectDraftContents(idea.pack);
  const output = draftPackToText(idea.title, pieces);
  assert.equal(pieces.length, 5);
  for (const piece of pieces) for (const section of piece.sections) assert.ok(output.includes(section.text));
  assert.ok(output.includes(idea.pack.captions.linkedIn));
  assert.ok(output.includes(idea.pack.captions.longFormInstagram));
});
