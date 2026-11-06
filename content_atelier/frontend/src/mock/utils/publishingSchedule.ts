import { ContentIdea } from '../../types/atelier';

export const PUBLISHING_TIME_ZONE = 'America/Chicago';

// Test both Central offsets against the IANA zone. This also rejects skipped
// spring-forward times and consistently chooses the first repeated fall hour.
function publishingInstant(date: string, time: string): Date | undefined {
  return ['-05:00', '-06:00'].map(offset => new Date(`${date}T${time}:00${offset}`)).find(instant => {
    if (!Number.isFinite(instant.getTime())) return false;
    const fields = scheduleFields(instant.toISOString());
    return fields.date === date && fields.time === time;
  });
}

export function scheduleZone(iso: string) {
  const instant = new Date(iso);
  const abbreviation = new Intl.DateTimeFormat('en-US', { timeZone: PUBLISHING_TIME_ZONE, timeZoneName: 'short' }).formatToParts(instant).find(part => part.type === 'timeZoneName')!.value;
  const offset = new Intl.DateTimeFormat('en-US', { timeZone: PUBLISHING_TIME_ZONE, timeZoneName: 'shortOffset' }).formatToParts(instant).find(part => part.type === 'timeZoneName')!.value.replace('GMT', 'UTC');
  return { abbreviation, offset };
}

export function publishingZone(date: string, time = '12:00') {
  return scheduleZone((publishingInstant(date, time) ?? new Date(`${date}T12:00:00Z`)).toISOString());
}

export function approvePackForScheduling(idea: ContentIdea, now = new Date().toISOString()): ContentIdea {
  if (!idea.pack || !['gate3_pack', 'approved_for_giselle'].includes(idea.gate)) return idea;
  return { ...idea, publishingApprovedAt: idea.publishingApprovedAt ?? now };
}

export function schedulePack(idea: ContentIdea, date: string, time: string, now = Date.now()): ContentIdea {
  if (!idea.pack || !idea.publishingApprovedAt) throw new Error('Approve the content pack for publishing first.');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^\d{2}:\d{2}$/.test(time)) throw new Error('Choose a valid date and time.');
  const instant = publishingInstant(date, time);
  if (!instant) throw new Error('Choose a valid date and time in Texas Central Time.');
  if (instant.getTime() <= now) throw new Error('Choose a publishing time in the future.');
  return { ...idea, scheduledAt: instant.toISOString() };
}

export function scheduleFields(iso: string) {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: PUBLISHING_TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date(iso));
  const value = (type: string) => parts.find(part => part.type === type)!.value;
  return { date: `${value('year')}-${value('month')}-${value('day')}`, time: `${value('hour')}:${value('minute')}` };
}

export function scheduleLabel(iso: string) {
  return `${new Date(iso).toLocaleString('en-US', { timeZone: PUBLISHING_TIME_ZONE, dateStyle: 'medium', timeStyle: 'short' })} ${scheduleZone(iso).abbreviation}`;
}
