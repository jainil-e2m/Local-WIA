import { CalendarEntry, CalendarFormat } from '../types/calendar';

export function calendarTimeMinutes(time: string): number {
  const match = time.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)?/i);
  if (!match) return 0;
  let hour = Number(match[1]);
  if (match[3]) hour = hour % 12 + (match[3].toUpperCase() === 'PM' ? 12 : 0);
  return hour * 60 + Number(match[2]);
}

export function daySchedule(entries: CalendarEntry[], format: CalendarFormat | 'All' = 'All'): CalendarEntry[] {
  return entries.filter(entry => format === 'All' || entry.channel === format)
    .sort((a, b) => calendarTimeMinutes(a.time) - calendarTimeMinutes(b.time) || a.id.localeCompare(b.id));
}

export function calendarDayPreview(entries: CalendarEntry[]) {
  const sorted = daySchedule(entries);
  return { visible: sorted.slice(0, 1), more: Math.max(0, sorted.length - 1) };
}
