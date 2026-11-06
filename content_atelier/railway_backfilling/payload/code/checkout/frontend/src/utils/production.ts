import { storageRequest } from "./weeklyStorage";
import { CalendarPage, SavedSchedule } from "../types/production";

export const productionChanged = () =>
  window.dispatchEvent(new Event("atelier-production-changed"));
export const requestId = () => crypto.randomUUID();
export function civilFields(instant: Date | string, zone: string) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: zone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(instant));
  const get = (key: string) => parts.find((p) => p.type === key)!.value;
  return {
    date: `${get("year")}-${get("month")}-${get("day")}`,
    time: `${get("hour")}:${get("minute")}`,
  };
}

/** Resolve a civil time, reject DST gaps, and require an explicit choice for DST folds. */
export function civilInstant(date: string, time: string, zone: string): string {
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
    !/^([01]\d|2[0-3]):[0-5]\d$/.test(time)
  )
    throw new Error("Choose a valid date and time.");
  const wall = Date.parse(`${date}T${time}:00Z`);
  if (
    !Number.isFinite(wall) ||
    new Date(wall).toISOString().slice(0, 10) !== date
  )
    throw new Error("Choose a valid date.");
  const candidates = new Set<number>();
  for (const hours of [-24, 0, 24]) {
    const probe = wall + hours * 3600000;
    const local = civilFields(new Date(probe), zone);
    const offset = Date.parse(`${local.date}T${local.time}:00Z`) - probe;
    const candidate = wall - offset;
    const roundtrip = civilFields(new Date(candidate), zone);
    if (roundtrip.date === date && roundtrip.time === time)
      candidates.add(candidate);
  }
  if (candidates.size !== 1)
    throw new Error(
      candidates.size
        ? "This time occurs twice because of daylight saving. Choose another time."
        : "This local time does not exist. Choose another time.",
    );
  const instant = [...candidates][0];
  const offsetMinutes = (wall - instant) / 60000;
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const abs = Math.abs(offsetMinutes);
  return `${date}T${time}:00${sign}${String(Math.floor(abs / 60)).padStart(2, "0")}:${String(abs % 60).padStart(2, "0")}`;
}

export function monthRange(year: number, month: number, zone: string) {
  const first = new Date(Date.UTC(year, month, 1)).toISOString().slice(0, 10);
  const next = new Date(Date.UTC(year, month + 1, 1))
    .toISOString()
    .slice(0, 10);
  return {
    from: civilInstant(first, "00:00", zone),
    to: civilInstant(next, "00:00", zone),
  };
}

export async function calendarEntries(
  from: string,
  to: string,
): Promise<SavedSchedule[]> {
  const result: SavedSchedule[] = [];
  let cursor: number | null = 0;
  const seen = new Set<number>();
  while (cursor !== null) {
    if (seen.has(cursor))
      throw new Error("Calendar pagination did not complete. Retry.");
    seen.add(cursor);
    const query = new URLSearchParams({ from, to, cursor: String(cursor) });
    const page = await storageRequest<CalendarPage>(`/calendar?${query}`);
    result.push(...page.items);
    cursor = page.next_cursor;
  }
  return result;
}
