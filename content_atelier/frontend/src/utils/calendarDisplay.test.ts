import { test } from 'node:test';
import assert from 'node:assert/strict';
import { calendarDayPreview, calendarTimeMinutes, daySchedule } from './calendarDisplay';
import { CalendarEntry } from '../types/calendar';

const entries: CalendarEntry[] = [
  { id: 'reel', ideaId: 'source', day: 10, channel: 'Reel', time: '2:00 PM', title: 'Afternoon reel', contentOrder: 3 },
  { id: 'email', ideaId: 'source', day: 10, channel: 'Email', time: '09:00 IST', title: 'Morning email', contentOrder: 1 },
  { id: 'carousel', ideaId: 'source', day: 10, channel: 'Carousel', time: '11:30 AM', title: 'Carousel', contentOrder: 2 },
];

test('one daily preview retains all extra content behind an exact more count', () => {
  const snapshot = JSON.stringify(entries);
  assert.deepEqual(calendarDayPreview([]), { visible: [], more: 0 });
  assert.equal(calendarDayPreview(entries.slice(0, 1)).more, 0);
  const preview = calendarDayPreview(entries);
  assert.deepEqual(preview.visible.map(entry => entry.id), ['email']);
  assert.equal(preview.more, 2);
  assert.equal(JSON.stringify(entries), snapshot);
});

test('daily agenda sorts times and filters formats without losing source links', () => {
  assert.equal(calendarTimeMinutes('12:00 AM'), 0);
  assert.equal(calendarTimeMinutes('12:00 PM'), 720);
  assert.equal(calendarTimeMinutes('14:00 IST'), 840);
  assert.deepEqual(daySchedule(entries).map(entry => entry.id), ['email', 'carousel', 'reel']);
  assert.deepEqual(daySchedule(entries, 'Reel'), [entries[0]]);
  assert.equal(daySchedule(entries).length, 3);
});
