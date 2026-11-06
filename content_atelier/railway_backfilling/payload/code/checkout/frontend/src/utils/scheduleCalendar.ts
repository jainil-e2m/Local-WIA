export function scheduleMonthDays(year: number, month: number) {
  const first = new Date(Date.UTC(year, month, 1));
  const leading = (first.getUTCDay() + 6) % 7;
  const count = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  return [...Array.from({ length: leading }, () => null), ...Array.from({ length: count }, (_, index) => ({ day: index + 1, date: `${year}-${String(month + 1).padStart(2, '0')}-${String(index + 1).padStart(2, '0')}` }))];
}

export function changeScheduleMonth(year: number, month: number, delta: number) {
  const next = new Date(Date.UTC(year, month + delta, 1));
  return { year: next.getUTCFullYear(), month: next.getUTCMonth() };
}

export function scheduleDateLabel(date: string) {
  return new Date(`${date}T12:00:00Z`).toLocaleDateString('en-IN', { timeZone: 'Asia/Calcutta', weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
}
