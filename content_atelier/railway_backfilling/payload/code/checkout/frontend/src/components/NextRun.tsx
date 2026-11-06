import React, { useEffect, useState } from 'react';
import { Clock3 } from 'lucide-react';
import { nextRunAt, runCountdown, RUN_TIME_ZONE } from '../utils/nextRun';

export function NextRunDetails({ nextRun, now, showCountdown }: { nextRun: Date; now: Date; showCountdown: boolean }) {
  const day = nextRun.toLocaleDateString('en-US', { timeZone: RUN_TIME_ZONE, weekday: 'long', month: 'short', day: 'numeric' });
  const time = nextRun.toLocaleTimeString('en-US', { timeZone: RUN_TIME_ZONE, hour: 'numeric', minute: '2-digit', timeZoneName: 'short' });
  return <>
    <span className="atelier-next-run-label">Next Run</span>
    <time className="atelier-next-run-countdown" dateTime={nextRun.toISOString()}>
      {showCountdown ? runCountdown(now, nextRun) : <span className="atelier-next-run-date-row"><span>{day}</span><span className="atelier-next-run-time">{time}</span></span>}
    </time>
  </>;
}

export function NextRun({ compact = false }: { compact?: boolean }) {
  const [now, setNow] = useState(() => new Date());
  const [showCountdown, setShowCountdown] = useState(false);
  const nextRun = nextRunAt(now);
  const label = nextRun.toLocaleString('en-US', { timeZone: RUN_TIME_ZONE, weekday: 'long', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' });
  useEffect(() => {
    const tick = () => setNow(new Date());
    const timer = window.setInterval(tick, 1000);
    document.addEventListener('visibilitychange', tick);
    return () => { window.clearInterval(timer); document.removeEventListener('visibilitychange', tick); };
  }, []);

  const content = <NextRunDetails nextRun={nextRun} now={now} showCountdown={showCountdown} />;
  return <div className="relative group/next-run">
    <button type="button" className={`atelier-next-run w-full ${compact ? 'atelier-next-run-compact' : ''}`} aria-pressed={showCountdown} aria-label={showCountdown ? `Next run in ${runCountdown(now, nextRun)}. Show scheduled day.` : `Next run ${label}. Show countdown.`} onClick={() => setShowCountdown(show => !show)} title={showCountdown ? 'Click to show the scheduled day. Display only; no job is scheduled.' : `Next run: ${label}. Click to show the countdown. Display only; no job is scheduled.`}>
      <Clock3 aria-hidden="true" className="w-4 h-4 shrink-0 text-[#B99A43]" strokeWidth={1.75} />
      {!compact && <span className="min-w-0 flex-1">{content}</span>}
    </button>
    {compact && <span className="absolute left-full bottom-0 ml-3 z-30 whitespace-nowrap bg-white border border-[#E6E9F0] shadow-saas-dropdown rounded-2xl p-3 opacity-0 invisible group-hover/next-run:opacity-100 group-hover/next-run:visible group-focus-within/next-run:opacity-100 group-focus-within/next-run:visible">{content}</span>}
  </div>;
}
