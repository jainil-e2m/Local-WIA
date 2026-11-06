export const RUN_TIME_ZONE = 'America/Chicago';
const formatter = new Intl.DateTimeFormat('en-US', { timeZone: RUN_TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' });
function wallTime(date: Date): number {
  const parts = formatter.formatToParts(date);
  const part = (name: string) => Number(parts.find(value => value.type === name)!.value);
  return Date.UTC(part('year'), part('month') - 1, part('day'), part('hour'), part('minute'), part('second'));
}

/** Next Saturday at 04:00 Central; resolve with IANA timezone rules, not a fixed UTC offset. */
export function nextRunAt(now: Date): Date {
  const local = new Date(wallTime(now));
  const saturday = new Date(Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate() + (6 - local.getUTCDay() + 7) % 7, 4));
  const resolve = () => {
    const desired = saturday.getTime();
    let actual = desired;
    for (let pass = 0; pass < 3; pass++) actual += desired - wallTime(new Date(actual));
    return new Date(actual);
  };
  let run = resolve();
  if (run.getTime() <= now.getTime()) {
    saturday.setUTCDate(saturday.getUTCDate() + 7);
    run = resolve();
  }
  return run;
}

export function runCountdown(now: Date, run: Date): string {
  const seconds = Math.max(0, Math.ceil((run.getTime() - now.getTime()) / 1000));
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${Math.floor(seconds / 86400)}d ${pad(Math.floor(seconds / 3600) % 24)}h ${pad(Math.floor(seconds / 60) % 60)}m ${pad(seconds % 60)}s`;
}
