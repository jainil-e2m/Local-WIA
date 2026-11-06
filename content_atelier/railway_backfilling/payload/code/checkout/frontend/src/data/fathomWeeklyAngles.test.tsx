import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { FATHOM_WEEKLY_ANGLES, FATHOM_EDITORIAL_WEEK } from './fathomWeeklyAngles';
import { EDITORIAL_MOCK_IDEAS, mergeEditorialMocks } from './editorialMockData';
import { INITIAL_IDEAS } from './mockData';
import { AngleResearch } from '../components/AngleEvidence';
import { EditorialHub } from '../components/EditorialHub';

test('the four selected weekly angles await angle approval with their prepared briefs attached', () => {
  const library = mergeEditorialMocks(INITIAL_IDEAS);
  const current = library.filter(idea => idea.editorialWeek === FATHOM_EDITORIAL_WEEK);
  assert.deepEqual(current.map(idea => idea.id), FATHOM_WEEKLY_ANGLES.map(idea => idea.id));
  assert.equal(new Set(current.map(idea => idea.editorialContext!.beliefShift)).size, 4);
  for (const idea of current) {
    assert.equal(idea.gate, 'gate1_angle');
    assert.equal(idea.pack, undefined);
    assert.equal(idea.angleApprovedAt, undefined);
    assert.equal(idea.briefApprovedAt, undefined);
    assert.ok(idea.brief.productionBrief);
    assert.equal(idea.research.googleTrendsScore, null);
    assert.deepEqual(idea.research.forumDiscussions, []);
    assert.equal(idea.scoreBasis, 'editorial');
  }
});

// Raw client recordings are private and intentionally excluded from Git.
// The source audit runs locally; the remaining mock workflow tests run in CI.
const exportRoot = new URL('../../../backend/corpus/fathom/latest_6_meetings/run-2026-10-06T11-42-00-097Z/', import.meta.url);
test('every displayed passage matches its recording, timestamp, speaker and exact text', { skip: !existsSync(exportRoot) }, () => {
  for (const idea of FATHOM_WEEKLY_ANGLES) {
    for (const source of idea.editorialContext!.sources) {
      const meeting = JSON.parse(readFileSync(new URL(`${source.recordingId}/meeting.json`, exportRoot), 'utf8'));
      const match = meeting.transcript.find((segment: { timestamp: string; speaker: { display_name: string }; text: string }) => segment.timestamp === source.timestamp && segment.speaker.display_name === source.speaker && segment.text === source.quote);
      assert.ok(match, `${idea.id}: unmatched source ${source.recordingId} ${source.timestamp}`);
      assert.equal(source.recordedAt, meeting.recording_start_time);
      assert.equal(source.speakerVerified, false);
      assert.ok(source.url.startsWith(`${meeting.url}?timestamp=`));
    }
  }
});

test('source research renders real passages and context without fictional corroboration or Trends claims', () => {
  for (const idea of FATHOM_WEEKLY_ANGLES) {
    const html = renderToStaticMarkup(<AngleResearch idea={idea} />);
    assert.ok(html.includes('Sources &amp; editorial context'));
    assert.ok(html.includes('Open recording'));
    assert.ok(html.includes('Speaker attribution'));
    assert.ok(!html.includes('Google Trends Index'));
    assert.ok(!html.includes('Elena Rostova'));
    assert.ok(!html.includes('Aethel Floral'));
  }
  const html = renderToStaticMarkup(<EditorialHub mode="weekly" initialTab="angles" ideas={mergeEditorialMocks(INITIAL_IDEAS)} onReview={() => {}} onUpdateGate={() => {}} onSwitchSection={() => {}} onAddAngle={() => {}} onApprovePack={() => {}} onSchedule={() => {}} />);
  for (const idea of FATHOM_WEEKLY_ANGLES) assert.ok(html.includes(idea.title));
  assert.ok(html.includes('4 waiting'));
  assert.ok(!html.includes('The Inquiry That Arrived After Midnight'));
});

test('cached fictional concepts move to the archive without losing edits or approvals', () => {
  const oldSeeds = EDITORIAL_MOCK_IDEAS.filter(idea => idea.id.startsWith('mock-editorial-v1-'));
  const saved = oldSeeds.map((idea, index) => ({ ...idea, mockLayoutVersion: 2, editorialWeek: index < 4 ? FATHOM_EDITORIAL_WEEK : idea.editorialWeek }));
  saved[0] = { ...saved[0], title: 'Saved user edit', gate: 'gate2_brief', angleApprovedAt: '2026-10-05T12:30:00.000Z' };
  const migrated = mergeEditorialMocks([...INITIAL_IDEAS, ...saved]);
  const retained = migrated.find(idea => idea.id === saved[0].id)!;
  assert.equal(retained.title, 'Saved user edit');
  assert.equal(retained.angleApprovedAt, saved[0].angleApprovedAt);
  assert.equal(retained.gate, 'gate2_brief');
  assert.ok(retained.editorialWeek! < FATHOM_EDITORIAL_WEEK);
  assert.equal(migrated.filter(idea => idea.editorialWeek === FATHOM_EDITORIAL_WEEK).length, 4);
  assert.deepEqual(mergeEditorialMocks(migrated), migrated);
});
