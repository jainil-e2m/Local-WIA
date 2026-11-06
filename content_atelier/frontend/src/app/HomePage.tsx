import React, { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';
import { userGreeting } from '../auth/session';
import { BackendCalendar } from '../components/BackendCalendar';
import { HomeSummary } from '../components/HomeSummary';
import { PageHeading } from '../components/PageHeading';
import { SeedCaptureModal } from '../components/SeedCapture';
import { useWriteFeedback } from '../components/shared/a11y';
import { useInvalidate } from '../api/query';
import { useCycleSummary, useFeatureFlags } from '../utils/workspace';
import { seesDetails, useMe } from '../utils/me';

/** Home, as the 20 October mockup: the greeting, the gold line, the calendar's search and "Flag idea" (a seed for the next
    cycle), then what waits for whom in a few plain lines (6.F2), then the saved calendar when it is switched on. The search
    filters the calendar, so it is shown only with the calendar; "Flag idea" is an editor's (the server checks it again). The
    calendar's month and the piece open on it are in the query string (see BackendCalendar). */
export function HomePage() {
  const { user } = useAuth();
  const flags = useFeatureFlags();
  const location = useLocation();
  const summary = useCycleSummary();
  const { me } = useMe();
  const invalidate = useInvalidate();
  const feedback = useWriteFeedback();
  const [searchQuery, setSearchQuery] = useState('');
  const [flagging, setFlagging] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const flagRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if ((location.state as { focusSearch?: boolean } | null)?.focusSearch) searchRef.current?.focus();
  }, [location.state, flags.calendar]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      // Only when there is a search to focus (the calendar is on); otherwise the key does nothing here (7.F1).
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k' && searchRef.current) { event.preventDefault(); searchRef.current.focus(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
  const canFlag = me.can.edit_cards;
  return <div className="atelier-home-content space-y-5">
    {feedback.region}
    <PageHeading title={userGreeting(user)} subtitle={flags.calendar ? 'Weekly content packs calendar & live publishing tracker' : 'What is waiting for you this week, and what happens next'}
      actions={(flags.calendar || canFlag) ? <>
        {flags.calendar && <div className="relative max-w-full">
          <Search strokeWidth={1.75} className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#A0A8B6] pointer-events-none" />
          <input ref={searchRef} type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} aria-label="Search the calendar"
            placeholder="Search the publishing calendar…"
            className="w-[280px] max-w-full h-10 bg-white text-[12px] text-[#173354] placeholder:text-[#8B97A8] pl-9 pr-12 rounded-full border border-[#D7C99F] focus:outline-none focus:ring-2 focus:ring-[#1B2838]/10" />
          <kbd className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-[#9AA3B2] bg-[#F4F6F9] border border-[#E6E9F0] rounded-md px-1.5 py-0.5">⌘K</kbd>
        </div>}
        {canFlag && <button ref={flagRef} type="button" onClick={() => setFlagging(true)}
          className="atelier-page-primary rounded-full px-5 text-[12px] inline-flex items-center gap-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8DA1FD]">
          <Plus strokeWidth={2} className="w-3.5 h-3.5" /><span>Flag idea</span>
        </button>}
      </> : undefined} />
    <HomeSummary summary={summary.data} error={summary.error?.message ?? ''} onRetry={() => void summary.refetch()}
      packs={flags.packs} administration={seesDetails(me) || me.can.manage_intake} />
    {flags.calendar && <BackendCalendar query={searchQuery} />}
    {flagging && canFlag && <SeedCaptureModal onClose={() => setFlagging(false)}
      onSaved={() => { void invalidate('/seeds'); feedback.announce('Flagged for the next cycle.', flagRef.current); }} />}
  </div>;
}
