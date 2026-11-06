import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { INITIAL_IDEAS } from '../data/mockData';
import { approvePackForScheduling, schedulePack, scheduleFields } from './publishingSchedule';
import { generateContentPackForIdea } from './packGenerator';
import { ContentCalendar } from '../testing/legacyCalendar';
import { ScheduledContent } from '../components/ScheduledContent';

const base = { ...INITIAL_IDEAS[0], gate: 'gate3_pack' as const, editorialWeek: '2026-10-05', pack: generateContentPackForIdea(INITIAL_IDEAS[0]) };
const now = Date.parse('2026-10-05T00:00:00Z');

test('publishing approval and scheduling preserve both gates, pack and original week', () => {
  const ready = approvePackForScheduling(base, new Date(now).toISOString());
  const result = schedulePack(ready, '2026-10-10', '09:30', now);
  assert.equal(result.gate, base.gate);
  assert.equal(result.editorialWeek, base.editorialWeek);
  assert.equal(result.pack, base.pack);
  assert.equal(result.scheduledAt, '2026-10-10T04:00:00.000Z');
  assert.deepEqual(scheduleFields(result.scheduledAt!), { date: '2026-10-10', time: '09:30' });
  assert.equal(approvePackForScheduling(result).publishingApprovedAt, ready.publishingApprovedAt);
});
test('invalid, past and unapproved schedules are rejected', () => {
  const ready = approvePackForScheduling(base);
  assert.throws(() => schedulePack(base, '2026-10-10', '09:30', now), /Approve/);
  for (const [date, time] of [['2026-10-04', '09:30'], ['2026-02-30', '09:30'], ['2026-10-10', '25:30'], ['', '']]) assert.throws(() => schedulePack(ready, date, time, now));
  assert.equal(approvePackForScheduling({ ...base, gate: 'gate1_angle', pack: undefined }).publishingApprovedAt, undefined);
});
test('scheduled pack is visible in the correct calendar month and scheduling queue', () => {
  const scheduled = schedulePack(approvePackForScheduling(base), '2026-10-10', '09:30', now);
  const html = renderToStaticMarkup(<ContentCalendar initialMonth={{ year: 2026, month: 9 }} ideas={[scheduled]} onSelectIdea={() => {}} />);
  assert.ok(html.includes('October'));
  assert.ok(html.includes('2026'));
  assert.ok(html.includes(scheduled.pack!.email.subjectLines[0].replace(/&/g, '&amp;')));
  assert.ok(html.includes('>Email</span>'));
  assert.ok(html.includes('>4 more</button>'));
  assert.ok(!html.includes('>Content Pack</span>'));
  assert.ok(html.includes('09:30 IST'));
  const queue = renderToStaticMarkup(<ScheduledContent ideas={[scheduled]} onSchedule={() => {}} onReview={() => {}} />);
  assert.ok(queue.includes('Scheduled'));
  assert.ok(queue.includes('Reschedule'));
  assert.ok(queue.includes('aria-haspopup="dialog"'));
  assert.ok(!queue.includes('type="date"'));
  assert.ok(!queue.includes('type="time"'));
  assert.ok(queue.includes('Awaiting scheduling'));
});
