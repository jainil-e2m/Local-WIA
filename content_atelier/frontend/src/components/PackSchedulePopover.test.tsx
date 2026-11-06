import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { PackSchedulePopover, ScheduleDateGrid } from './PackSchedulePopover';
import { scheduleMonthDays, changeScheduleMonth, scheduleDateLabel } from '../utils/scheduleCalendar';
import { INITIAL_IDEAS } from '../data/mockData';
import { approvePackForScheduling, schedulePack } from '../utils/publishingSchedule';
import { generateContentPackForIdea } from '../utils/packGenerator';

test('custom calendar has correct weekdays, leap years and month navigation', () => {
  const october = scheduleMonthDays(2026, 9);
  assert.equal(october.filter(Boolean).length, 31);
  assert.equal(october.findIndex(Boolean), 3);
  assert.equal(october[3]?.date, '2026-10-01');
  assert.equal(scheduleMonthDays(2028, 1).filter(Boolean).length, 29);
  assert.deepEqual(changeScheduleMonth(2026, 11, 1), { year: 2027, month: 0 });
  assert.deepEqual(changeScheduleMonth(2026, 0, -1), { year: 2025, month: 11 });
  assert.ok(scheduleDateLabel('2026-10-10').includes('Sat'));
});

test('date selection is themed, accessible and disables past days without native picker controls', () => {
  const html = renderToStaticMarkup(<ScheduleDateGrid cursor={{ year: 2026, month: 9 }} today="2026-10-06" date="2026-10-10" onSelect={() => {}} />);
  assert.equal((html.match(/<button/g) ?? []).length, 31);
  assert.equal((html.match(/disabled=""/g) ?? []).length, 5);
  assert.equal((html.match(/aria-pressed="true"/g) ?? []).length, 1);
  assert.ok(html.includes('bg-[#5070FF] text-white'));
  assert.ok(!html.includes('<input'));
  assert.ok(!html.includes('<select'));
});

test('schedule and reschedule triggers use the new popup instead of clipboard actions', () => {
  for (const scheduled of [false, true]) {
    const html = renderToStaticMarkup(<PackSchedulePopover idea={{ ...INITIAL_IDEAS[0], scheduledAt: scheduled ? '2026-10-10T04:00:00Z' : undefined }} onSchedule={() => {}} />);
    assert.ok(html.includes(scheduled ? 'Reschedule' : '>Schedule</button>'));
    assert.ok(html.includes('aria-haspopup="dialog"'));
    assert.ok(html.includes('aria-expanded="false"'));
    assert.ok(!html.includes('Copy for Canva'));
    assert.ok(html.includes('ml-auto inline-flex shrink-0'));
    assert.ok(html.includes('role="status" class="sr-only"'));
  }
});

test('confirming a pack schedule validates before changing approval and publishing date', () => {
  const source = { ...INITIAL_IDEAS[0], gate: 'gate3_pack' as const, pack: generateContentPackForIdea(INITIAL_IDEAS[0]), publishingApprovedAt: undefined };
  const snapshot = JSON.stringify(source);
  const now = Date.parse('2026-10-06T00:00:00Z');
  assert.throws(() => schedulePack(approvePackForScheduling(source), '2026-10-05', '09:00', now), /future/);
  assert.equal(JSON.stringify(source), snapshot);
  const saved = schedulePack(approvePackForScheduling(source), '2026-10-10', '09:30', now);
  assert.ok(saved.publishingApprovedAt);
  assert.equal(saved.scheduledAt, '2026-10-10T04:00:00.000Z');
  assert.equal(saved.pack, source.pack);
});
