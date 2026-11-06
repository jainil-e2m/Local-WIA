import type { NextCycle } from '../api/schema';

/* The weekly cycle's schedule in the app (3.B11). The backend's GET /schedule says whether the cycle starts by itself and
   when (`at`, in the cycle's own time zone, with the schedule in words); the app shows that and never a time of its own. */

type Schedule = Pick<NextCycle, 'enabled' | 'at' | 'timezone'>;

/** The next scheduled start as a date, or null while the schedule is off or the answer has no usable time. */
export function nextRunDate(schedule: Schedule | null | undefined): Date | null {
  if (!schedule?.enabled || !schedule.at) return null;
  const at = new Date(schedule.at);
  return Number.isNaN(at.getTime()) ? null : at;
}

/** The schedule's own time zone if the browser knows it, else UTC (an unknown zone name must not break the screen). */
export function scheduleZone(schedule: Pick<NextCycle, 'timezone'> | null | undefined): string {
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: schedule?.timezone });
    return schedule?.timezone || 'UTC';
  } catch {
    return 'UTC';
  }
}

/** When the next scheduled cycle starts, in words and in the cycle's time zone ("Sunday 1 November at 4:00 a.m. Chicago
    time"), or null while the schedule is off. */
export function nextCycleWords(schedule: Schedule | null | undefined): string | null {
  const at = nextRunDate(schedule);
  if (!at) return null;
  const timeZone = scheduleZone(schedule);
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-GB', {
    timeZone, weekday: 'long', day: 'numeric', month: 'long', hour: 'numeric', minute: '2-digit', hourCycle: 'h12',
  }).formatToParts(at).map(part => [part.type, part.value]));
  const period = String(parts.dayPeriod ?? '').toLowerCase().startsWith('p') ? 'p.m.' : 'a.m.';
  const place = timeZone === 'UTC' ? 'UTC' : `${timeZone.split('/').pop()!.replaceAll('_', ' ')} time`;
  return `${parts.weekday} ${parts.day} ${parts.month} at ${parts.hour}:${parts.minute} ${period} ${place}`;
}

export function runCountdown(now: Date, run: Date): string {
  const seconds = Math.max(0, Math.ceil((run.getTime() - now.getTime()) / 1000));
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${Math.floor(seconds / 86400)}d ${pad(Math.floor(seconds / 3600) % 24)}h ${pad(Math.floor(seconds / 60) % 60)}m ${pad(seconds % 60)}s`;
}
