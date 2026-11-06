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

test('the three selected weekly angles await angle approval with their prepared briefs attached', () => {
  const library = mergeEditorialMocks(INITIAL_IDEAS);
  const current = library.filter(idea => idea.editorialWeek === FATHOM_EDITORIAL_WEEK);
  assert.deepEqual(current.map(idea => idea.id), FATHOM_WEEKLY_ANGLES.map(idea => idea.id));
  assert.equal(new Set(current.map(idea => idea.editorialContext!.beliefShift)).size, 3);
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

test('the supplied angles retain the audience, process, evidence and guardrails without invented source links', () => {
  assert.equal(FATHOM_WEEKLY_ANGLES.length, 3);
  for (const idea of FATHOM_WEEKLY_ANGLES) {
    const labels = idea.angleRationale!.points.map(point => point.label);
    for (const field of ['Content pillar / type', 'Audience', 'Why this matters', "WIA's expertise or process", 'Editorial guardrail / next step']) assert.ok(labels.includes(field));
    assert.ok(idea.sourceDetails.length > 0);
    assert.deepEqual(idea.editorialContext!.sources, []);
    assert.equal(idea.research.googleTrendsScore, null);
  }
  const html = renderToStaticMarkup(<EditorialHub mode="weekly" ideas={mergeEditorialMocks(INITIAL_IDEAS)} onReview={() => {}} onUpdateGate={() => {}} onSwitchSection={() => {}} onAddAngle={() => {}} onApprovePack={() => {}} onSchedule={() => {}} />);
  for (const idea of FATHOM_WEEKLY_ANGLES) assert.ok(html.includes(renderToStaticMarkup(<>{idea.title}</>)));
  assert.ok(html.includes('3 waiting'));
  assert.ok(!html.includes('Before You Fix the Form'));
});
test('cached fictional weeks before October no longer repopulate the archive', () => {
  const saved = EDITORIAL_MOCK_IDEAS.filter(idea => idea.id.startsWith('mock-editorial-v1-'));
  const migrated = mergeEditorialMocks([...INITIAL_IDEAS, ...saved]);
  assert.equal(migrated.length, 3);
  assert.deepEqual(migrated.map(idea => idea.id), FATHOM_WEEKLY_ANGLES.map(idea => idea.id));
  assert.deepEqual(mergeEditorialMocks(migrated), migrated);
});