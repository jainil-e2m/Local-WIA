import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { simulateMockStudio } from './mockStudioSimulation';
import { FATHOM_WEEKLY_ANGLES } from '../data/fathomWeeklyAngles';
import { mergeEditorialMocks } from '../data/editorialMockData';
import { INITIAL_IDEAS } from '../data/mockData';
import { ContentIdea, MockStudioStage } from '../types/atelier';
import { advanceEditorialItem } from './editorialWorkflow';
import { generateContentPackForIdea } from './packGenerator';
import { approvePackForScheduling, scheduleFields, schedulePack } from './publishingSchedule';
import { EditorialHub } from '../components/EditorialHub';
import { ContentCalendar, octoberDemoPosts, packCalendarPosts } from '../testing/legacyCalendar';

const now = '2026-10-06T12:00:00.000Z';
const library = mergeEditorialMocks(INITIAL_IDEAS);
const sourceIds = new Set(FATHOM_WEEKLY_ANGLES.map(idea => idea.id));
const sources = (ideas: ContentIdea[]) => ideas.filter(idea => sourceIds.has(idea.id));
const callbacks = { onReview: () => {}, onUpdateGate: () => {}, onSwitchSection: () => {}, onAddAngle: () => {}, onApprovePack: () => {}, onSchedule: () => {} };

test('the four saved mock templates produce distinct packs from their own briefs without generic case-study claims', () => {
  const packs = FATHOM_WEEKLY_ANGLES.map(generateContentPackForIdea);
  assert.equal(new Set(packs.map(pack => pack.email.body)).size, 4);
  assert.equal(new Set(packs.flatMap(pack => pack.reels.map(reel => reel.spokenScript))).size, 12);
  packs.forEach((pack, index) => {
    const seed = FATHOM_WEEKLY_ANGLES[index];
    assert.equal(pack.carousel.title, seed.title);
    assert.equal(pack.carousel.slides.length, 8);
    assert.equal(pack.reels.length, 3);
    assert.notEqual(pack, seed.mockContentPack);
    assert.equal(pack.email.ctaUrl, '');
    assert.ok(pack.email.body.split(/\s+/).length >= (seed.suggestedCta === 'LeadLock' ? 400 : 350));
    for (const reel of pack.reels) {
      assert.ok(reel.id.startsWith(seed.id));
      assert.equal(reel.spokenScriptVersion, 2);
      assert.ok(reel.spokenScript!.endsWith(reel.ctaText));
      assert.equal(reel.visualSequence!.length, 4);
    }
    assert.equal(pack.ruleChecks.overlapScore, null);
    assert.equal(pack.ruleChecks.voiceCriticPassed, false);
    assert.ok(!JSON.stringify(pack).includes('Sarah'));
    assert.ok(!JSON.stringify(pack).includes('$100k'));
    assert.ok(!JSON.stringify(pack).includes('42%'));
  });
});

test('all five previews retain analysis and archive records while giving each stage correct progress', () => {
  for (const stage of ['angles', 'briefs', 'packs', 'scheduling', 'scheduled'] as MockStudioStage[]) {
    const preview = simulateMockStudio(library, stage, now);
    const current = sources(preview);
    assert.equal(current.length, 4);
    for (const item of current) {
      const original = library.find(idea => idea.id === item.id)!;
      assert.equal(item.brief, original.brief);
      assert.equal(item.editorialContext, original.editorialContext);
      assert.equal(item.angleRationale, original.angleRationale);
      assert.equal(item.editorialWeek, original.editorialWeek);
      assert.equal(item.gate, stage === 'angles' ? 'gate1_angle' : stage === 'briefs' ? 'gate2_brief' : 'gate3_pack');
      assert.equal(!!item.pack, !['angles', 'briefs'].includes(stage));
      assert.equal(!!item.publishingApprovedAt, ['scheduling', 'scheduled'].includes(stage));
      assert.equal(!!item.scheduledAt, stage === 'scheduled');
      assert.equal(item.mockSimulation!.stage, stage);
    }
    for (const original of library.filter(idea => !sourceIds.has(idea.id))) assert.equal(preview.find(idea => idea.id === original.id), original);
    const restored = mergeEditorialMocks(JSON.parse(JSON.stringify(preview)));
    assert.deepEqual(restored, JSON.parse(JSON.stringify(preview)));
  }
});

test('manual approval and scheduling work after replay without reseeding or discarding the saved analysis', () => {
  const start = sources(simulateMockStudio(library, 'angles', now))[0];
  assert.equal(advanceEditorialItem(start, 'gate3_pack', now), start);
  const brief = advanceEditorialItem(start, 'gate2_brief', now);
  const generated = advanceEditorialItem(brief, 'gate3_pack', now);
  const scheduled = schedulePack(approvePackForScheduling(generated, now), '2026-10-10', '09:30', Date.parse(now));
  assert.equal(scheduled.brief, start.brief);
  assert.equal(scheduled.editorialContext, start.editorialContext);
  assert.equal(scheduled.editorialWeek, start.editorialWeek);
  assert.deepEqual(scheduleFields(scheduled.scheduledAt!), { date: '2026-10-10', time: '09:30' });
  assert.equal(scheduled.pack!.carousel.title, start.title);
  const saved = mergeEditorialMocks(JSON.parse(JSON.stringify(library.map(idea => idea.id === start.id ? scheduled : idea))));
  assert.equal(saved.find(idea => idea.id === start.id)!.scheduledAt, scheduled.scheduledAt);
  const edited = { ...scheduled, title: 'Saved title', brief: { ...scheduled.brief, coreInsight: 'Saved insight' } };
  const reset = sources(simulateMockStudio([edited], 'angles', now))[0];
  assert.equal(reset.title, edited.title);
  assert.equal(reset.brief, edited.brief);
  assert.equal(reset.pack, undefined);
  assert.equal(reset.scheduledAt, undefined);
});

test('scheduled previews use future IST dates and expose twenty source-linked calendar pieces', () => {
  const preview = simulateMockStudio(library, 'scheduled', now);
  const current = sources(preview);
  assert.deepEqual(current.map(idea => scheduleFields(idea.scheduledAt!).date), ['2026-10-07', '2026-10-08', '2026-10-09', '2026-10-10']);
  const postings = current.flatMap(idea => packCalendarPosts(idea, Number(scheduleFields(idea.scheduledAt!).date.slice(-2)), '10:00 IST'));
  assert.equal(postings.length, 20);
  assert.equal(new Set(postings.map(post => post.id)).size, 20);
  assert.deepEqual(postings.slice(0, 5).map(post => post.channel), ['Email', 'Carousel', 'Reel', 'Reel', 'Reel']);
  assert.ok(octoberDemoPosts(preview).every(post => !sourceIds.has(post.ideaId)));
  const late = sources(simulateMockStudio(library, 'scheduled', '2026-10-06T18:45:00.000Z'));
  assert.equal(scheduleFields(late[0].scheduledAt!).date, '2026-10-08');
  const html = renderToStaticMarkup(<ContentCalendar ideas={preview} initialMonth={{ year: 2026, month: 9 }} onSelectIdea={() => {}} />);
  for (const idea of current) assert.ok(html.includes(idea.pack!.email.subjectLines[0]));
  assert.ok(html.includes('10:00 IST'));
});

test('the weekly studio renders each stage without replay controls', () => {
  for (const [stage, tab] of [['angles', 'angles'], ['briefs', 'briefs'], ['packs', 'packs'], ['scheduling', 'scheduled'], ['scheduled', 'scheduled']] as const) {
    const preview = simulateMockStudio(library, stage, now);
    const html = renderToStaticMarkup(<EditorialHub {...callbacks} mode="weekly" initialTab={tab} ideas={preview} />);
    for (const label of ['Fathom mock week', 'Start at angles', 'Preview briefs', 'Preview packs', 'Ready to schedule', 'Preview scheduled']) assert.ok(!html.includes(label));
    for (const idea of sources(preview)) assert.ok(html.includes(idea.title));
    if (stage === 'scheduling') assert.ok(html.includes('Awaiting scheduling'));
    if (stage === 'scheduled') assert.ok(html.includes('10:00'));
  }
  const previous = renderToStaticMarkup(<EditorialHub {...callbacks} mode="previous" ideas={library} />);
  assert.ok(!previous.includes('Fathom mock week replay'));
});

test('older saved mocks gain the pack templates without overwriting an existing draft or progress', () => {
  const seed = FATHOM_WEEKLY_ANGLES[0];
  const stored = { ...seed, mockContentPack: undefined, pack: { ...generateContentPackForIdea(seed), carousel: { ...generateContentPackForIdea(seed).carousel, title: 'Saved pack edit' } }, gate: 'gate3_pack' as const, briefApprovedAt: now };
  const hydrated = mergeEditorialMocks([stored]).find(idea => idea.id === seed.id)!;
  assert.ok(hydrated.mockContentPack);
  assert.equal(hydrated.pack, stored.pack);
  assert.equal(hydrated.pack!.carousel.title, 'Saved pack edit');
  assert.equal(hydrated.briefApprovedAt, now);
});
