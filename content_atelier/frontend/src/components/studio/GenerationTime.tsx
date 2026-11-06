import React from 'react';
import { Clock } from 'lucide-react';

/* How long generation takes, in one place, so every screen says the same thing. Measured on production runs, 3 November 2026:
   a refreshed angle 20 to 45 seconds plus its check; a brief or a brief's new version 13 to 53 minutes, most near 25 (an
   evidence-heavy card takes the longest); a content pack 2 to 32 minutes, most near 5; a weekly cycle 6 to 25 minutes. */
export const TAKES = {
  angleRefresh: 'about a minute',
  brief: '15 to 30 minutes',
  pack: '5 to 10 minutes',
  week: '10 to 25 minutes',
} as const;

/** One line saying how long something takes, beside the button that starts it or the state that is waiting on it. */
export function TimeNote({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <p className={`flex items-center gap-1.5 text-[11px] leading-snug text-[#7A8496] ${className}`}>
    <Clock aria-hidden="true" strokeWidth={1.6} className="w-3 h-3 shrink-0 text-[#A38B61]" /><span>{children}</span></p>;
}
