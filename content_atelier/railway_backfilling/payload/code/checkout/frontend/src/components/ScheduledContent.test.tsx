import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { ScheduledContent } from './ScheduledContent';
import { INITIAL_IDEAS } from '../data/mockData';
import { generateContentPackForIdea } from '../utils/packGenerator';

test('waiting and scheduled packs share the Content Packs custom scheduling popup', () => {
  const source = INITIAL_IDEAS[0];
  const ready = { ...source, editorialWeek: '2026-10-05', pack: generateContentPackForIdea(source), publishingApprovedAt: '2026-10-06T00:00:00Z' };
  const html = renderToStaticMarkup(<ScheduledContent ideas={[{ ...ready, id: 'waiting', scheduledAt: undefined }, { ...ready, id: 'scheduled', scheduledAt: '2026-10-10T04:00:00Z' }]} onSchedule={() => {}} onReview={() => {}} />);
  assert.ok(html.includes('>Schedule</button>'));
  assert.ok(html.includes('>Reschedule</button>'));
  assert.equal((html.match(/aria-haspopup="dialog"/g) ?? []).length, 10);
  assert.equal((html.match(/ml-auto inline-flex shrink-0/g) ?? []).length, 10);
  assert.ok(!html.includes('type="date"'));
  assert.ok(!html.includes('type="time"'));
  assert.ok(html.includes('Review content'));
});

test('scheduled cards show generation week separately from the posting date without mock prefixes', () => {
  const source = INITIAL_IDEAS[0];
  const idea = { ...source, isMock: true, editorialWeek: '2026-09-21', briefApprovedAt: '2026-09-30T10:00:00Z', pack: generateContentPackForIdea(source), publishingApprovedAt: '2026-10-06T00:00:00Z', scheduledAt: '2026-10-10T04:00:00Z' };
  const html = renderToStaticMarkup(<ScheduledContent ideas={[idea]} onSchedule={() => {}} onReview={() => {}} />);
  assert.ok(!html.includes('Mock ·'));
  assert.ok(html.includes('Generated week: 28 Sept – 4 Oct, 2026'));
  assert.ok(html.includes('text-right text-[11px]'));
});
