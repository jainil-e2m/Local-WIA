import { test } from 'node:test';
import assert from 'node:assert/strict';
import { nextRunAt, runCountdown } from './nextRun';

test('Saturday at 4am Central is selected regardless of client timezone', () => {
  assert.equal(nextRunAt(new Date('2026-10-05T06:30:00Z')).toISOString(), '2026-10-10T09:00:00.000Z');
  assert.equal(nextRunAt(new Date('2026-10-10T08:59:59Z')).toISOString(), '2026-10-10T09:00:00.000Z');
  assert.equal(nextRunAt(new Date('2026-10-10T09:00:00Z')).toISOString(), '2026-10-17T09:00:00.000Z');
});

test('countdown handles daylight-saving transitions without fixed offsets', () => {
  assert.equal(nextRunAt(new Date('2026-03-06T12:00:00Z')).toISOString(), '2026-03-07T10:00:00.000Z');
  assert.equal(nextRunAt(new Date('2026-03-07T10:00:00Z')).toISOString(), '2026-03-14T09:00:00.000Z');
  assert.equal(nextRunAt(new Date('2026-10-31T09:00:00Z')).toISOString(), '2026-11-07T10:00:00.000Z');
});

test('countdown formats days, hours, minutes and seconds without negative values', () => {
  const now = new Date('2026-10-05T09:00:00Z');
  assert.equal(runCountdown(now, nextRunAt(now)), '5d 00h 00m 00s');
  assert.equal(runCountdown(now, new Date('2026-10-05T09:00:01Z')), '0d 00h 00m 01s');
  assert.equal(runCountdown(now, new Date('2026-10-04T09:00:00Z')), '0d 00h 00m 00s');
});
