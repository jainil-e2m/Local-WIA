import { test } from 'node:test';
import assert from 'node:assert/strict';
import { nextCycleWords, nextRunDate, runCountdown, scheduleZone } from './nextRun';

// GET /schedule's answer, as the backend writes it (cycle/schedule.py next_run): the time in the cycle's own zone.
const ON = { enabled: true, at: '2026-11-01T04:00:00-06:00', timezone: 'America/Chicago' };

test('3.B11: the next run is the schedule\'s own time, said in its own time zone', () => {
  assert.equal(nextRunDate(ON)?.toISOString(), '2026-11-01T10:00:00.000Z');
  assert.equal(nextCycleWords(ON), 'Sunday 1 November at 4:00 a.m. Chicago time');
  // Before the clocks change the same 04:00 is a different instant; the words stay the schedule's.
  assert.equal(nextCycleWords({ ...ON, at: '2026-11-01T16:30:00-06:00' }), 'Sunday 1 November at 4:30 p.m. Chicago time');
  assert.equal(nextCycleWords({ ...ON, at: '2026-10-25T04:00:00-05:00' }), 'Sunday 25 October at 4:00 a.m. Chicago time');
});

test('3.B11: a schedule that is off, or an answer without a usable time, has no next run', () => {
  assert.equal(nextRunDate({ enabled: false, at: null, timezone: 'America/Chicago' }), null);
  assert.equal(nextCycleWords({ enabled: false, at: null, timezone: 'America/Chicago' }), null);
  assert.equal(nextRunDate({ ...ON, at: 'not a time' }), null);
  assert.equal(nextRunDate(undefined), null);
});

test('3.B11: a time zone the browser does not know is shown in UTC rather than breaking the sidebar', () => {
  assert.equal(scheduleZone({ timezone: 'Mars/Olympus_Mons' }), 'UTC');
  assert.equal(nextCycleWords({ ...ON, timezone: 'Mars/Olympus_Mons' }), 'Sunday 1 November at 10:00 a.m. UTC');
});

test('countdown formats days, hours, minutes and seconds without negative values', () => {
  const now = new Date('2026-10-27T10:00:00Z');
  assert.equal(runCountdown(now, nextRunDate(ON)!), '5d 00h 00m 00s');
  assert.equal(runCountdown(now, new Date('2026-10-27T10:00:01Z')), '0d 00h 00m 01s');
  assert.equal(runCountdown(now, new Date('2026-10-26T10:00:00Z')), '0d 00h 00m 00s');
});
