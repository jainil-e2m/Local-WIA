import React, { useEffect, useRef, useState } from 'react';
import { Clock3 } from 'lucide-react';
import type { CycleSchedule } from '../api/schema';
import { useApiQuery } from '../api/query';
import { nextCycleWords, nextRunDate, runCountdown, scheduleZone } from '../utils/nextRun';

/* The sidebar's "Next run" (3.B11): when the weekly cycle starts by itself, from the backend's schedule (GET /schedule), or
   that the schedule is off. It is the real schedule now, not a display of a fixed Saturday. */

const OFF = 'The weekly cycle does not start by itself: an approver starts a cycle from the Weekly Studio.';

/** Whether an answer has the schedule's shape (a screen test may stub other routes). */
const isSchedule = (value: unknown): value is CycleSchedule => !!value && typeof value === 'object' && typeof (value as CycleSchedule).enabled === 'boolean';

export function NextRunDetails({ schedule, failed = false, now, showCountdown }: { schedule: CycleSchedule | undefined; failed?: boolean; now: Date; showCountdown: boolean }) {
  const nextRun = nextRunDate(schedule);
  const label = <span className="atelier-next-run-label">Next Run</span>;
  if (!schedule || !nextRun) {
    const words = schedule ? 'Schedule off' : failed ? 'Schedule unavailable' : 'Checking the schedule…';
    return <>{label}<span className="atelier-next-run-countdown">{words}</span></>;
  }
  const timeZone = scheduleZone(schedule);
  const day = nextRun.toLocaleDateString('en-US', { timeZone, weekday: 'long', month: 'short', day: 'numeric' });
  const time = nextRun.toLocaleTimeString('en-US', { timeZone, hour: 'numeric', minute: '2-digit', timeZoneName: 'short' });
  return <>
    {label}
    <time className="atelier-next-run-countdown" dateTime={nextRun.toISOString()}>
      {showCountdown ? runCountdown(now, nextRun) : <span className="atelier-next-run-date-row"><span>{day}</span><span className="atelier-next-run-time">{time}</span></span>}
    </time>
  </>;
}

export function NextRun({ compact = false }: { compact?: boolean }) {
  const query = useApiQuery('/schedule', undefined, { staleTime: 60_000, refetchInterval: 5 * 60_000 });
  const schedule = isSchedule(query.data) ? query.data : undefined;
  const nextRun = nextRunDate(schedule);
  const [now, setNow] = useState(() => new Date());
  const [showCountdown, setShowCountdown] = useState(false);
  const scheduled = nextRun?.getTime() ?? null;
  // The clock ticks only while there is a scheduled time to count down to.
  useEffect(() => {
    if (scheduled === null) return;
    const tick = () => setNow(new Date());
    const timer = window.setInterval(tick, 1000);
    document.addEventListener('visibilitychange', tick);
    return () => { window.clearInterval(timer); document.removeEventListener('visibilitychange', tick); };
  }, [scheduled]);
  // Once the scheduled time has passed, the schedule is read again for the next one (once per scheduled time).
  const asked = useRef<number | null>(null);
  const { refetch } = query;
  useEffect(() => {
    if (scheduled === null || now.getTime() < scheduled || asked.current === scheduled) return;
    asked.current = scheduled;
    void refetch();
  }, [now, scheduled, refetch]);

  const content = <NextRunDetails schedule={schedule} failed={!!query.error} now={now} showCountdown={showCountdown} />;
  const words = nextCycleWords(schedule);
  const tooltip = compact && <span className="absolute left-full bottom-0 ml-3 z-30 whitespace-nowrap bg-white border border-[#E6E9F0] shadow-saas-dropdown rounded-2xl p-3 opacity-0 invisible group-hover/next-run:opacity-100 group-hover/next-run:visible group-focus-within/next-run:opacity-100 group-focus-within/next-run:visible">{content}</span>;
  if (!nextRun || !words) {
    // Nothing to count down to: the state in words, reachable by keyboard in the collapsed sidebar for its tooltip.
    const said = schedule ? `Schedule off. ${OFF}` : query.error ? 'The schedule is unavailable.' : 'Checking the schedule.';
    return <div className="relative group/next-run">
      <div className={`atelier-next-run w-full ${compact ? 'atelier-next-run-compact' : ''}`} tabIndex={compact ? 0 : undefined} role="note" aria-label={`Next run: ${said}`} title={schedule ? OFF : undefined}>
        <Clock3 aria-hidden="true" className="w-4 h-4 shrink-0 text-[#B99A43]" strokeWidth={1.75} />
        {!compact && <span className="min-w-0 flex-1">{content}</span>}
      </div>
      {tooltip}
    </div>;
  }
  return <div className="relative group/next-run">
    <button type="button" className={`atelier-next-run w-full ${compact ? 'atelier-next-run-compact' : ''}`} aria-pressed={showCountdown}
      aria-label={showCountdown ? `The cycle starts by itself in ${runCountdown(now, nextRun)}. Show the scheduled day.` : `The cycle starts by itself ${words}. Show the countdown.`}
      onClick={() => setShowCountdown(show => !show)}
      title={showCountdown ? 'Click to show the scheduled day.' : `The weekly cycle starts by itself: ${words}. Click to show the countdown.`}>
      <Clock3 aria-hidden="true" className="w-4 h-4 shrink-0 text-[#B99A43]" strokeWidth={1.75} />
      {!compact && <span className="min-w-0 flex-1">{content}</span>}
    </button>
    {tooltip}
  </div>;
}
