import { test } from 'node:test';
import assert from 'node:assert/strict';
import { FATHOM_WEEKLY_ANGLES } from '../data/fathomWeeklyAngles';
import { approvePackForScheduling, publishingZone, scheduleFields, scheduleLabel, schedulePack } from './utils/publishingSchedule';

const source = FATHOM_WEEKLY_ANGLES[0];
const approved = approvePackForScheduling({ ...source, gate: 'gate3_pack', pack: source.mockContentPack });
const now = Date.parse('2026-01-01T00:00:00Z');

test('Texas publishing times use CDT in October and CST after daylight saving ends', () => {
  const october = schedulePack(approved, '2026-10-24', '09:00', now).scheduledAt!;
  assert.equal(october, '2026-10-24T14:00:00.000Z');
  assert.deepEqual(scheduleFields(october), { date: '2026-10-24', time: '09:00' });
  assert.deepEqual(publishingZone('2026-10-24', '09:00'), { abbreviation: 'CDT', offset: 'UTC-5' });
  assert.match(scheduleLabel(october), /9:00 AM CDT$/);
  const november = schedulePack(approved, '2026-11-10', '09:00', now).scheduledAt!;
  assert.equal(november, '2026-11-10T15:00:00.000Z');
  assert.deepEqual(publishingZone('2026-11-10', '09:00'), { abbreviation: 'CST', offset: 'UTC-6' });
  assert.match(scheduleLabel(november), /9:00 AM CST$/);
});

test('Texas scheduling rejects nonexistent spring times and preserves saved instants', () => {
  assert.throws(() => schedulePack(approved, '2027-03-14', '02:30', now), /valid date and time/);
  const repeated = schedulePack(approved, '2026-11-01', '01:30', now).scheduledAt!;
  assert.equal(repeated, '2026-11-01T06:30:00.000Z');
  assert.deepEqual(scheduleFields('2026-10-24T03:30:00Z'), { date: '2026-10-23', time: '22:30' });
});
