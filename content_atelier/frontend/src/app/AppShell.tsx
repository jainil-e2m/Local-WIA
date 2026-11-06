import React, { useEffect, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import Lenis from 'lenis';
import { AtelierCanvas } from '../components/AtelierCanvas';
import { Sidebar } from '../components/Sidebar';
import { TopHeader } from '../components/TopHeader';
import { PageHeaderSlot } from '../components/PageHeading';
import { ViewBoundary } from '../components/shared/ViewBoundary';
import { useInvalidate } from '../api/query';
import { shellCounts, useCycleSummary, useFeatureFlags } from '../utils/workspace';
import { legacyHashTarget, navViewOf, paths } from './routes';

/** The frame around every view: sidebar, header, and the place a view renders. The sidebar and header have their own
    error boundaries, so a failure in either leaves the view usable. */
export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const flags = useFeatureFlags();
  // The shell's counts come from Home's cycle summary (6.F2), one read every minute that every screen shares.
  const counts = shellCounts(useCycleSummary().data);
  const invalidate = useInvalidate();
  // Each page draws its own title and buttons into the top bar (PageHeading), so the page starts at the top.
  const [headerSlot, setHeaderSlot] = useState<HTMLElement | null>(null);

  // A card or brief link from before the app had paths (#studio/...) opens at its path.
  useEffect(() => {
    const target = legacyHashTarget(location.hash);
    if (target) navigate(target, { replace: true });
  }, [location.hash, navigate]);

  // A saved pack, schedule or cancellation anywhere refreshes the packs and the calendar everywhere.
  useEffect(() => {
    const refresh = () => void invalidate('/packs', '/packs/{pack_id}', '/packs/{pack_id}/production', '/calendar');
    window.addEventListener('atelier-production-changed', refresh);
    return () => window.removeEventListener('atelier-production-changed', refresh);
  }, [invalidate]);

  // ⌘K opens the calendar's search on Home. That search exists only with the calendar switched on; without it the key is
  // left alone rather than sending the person to a Home with nothing to type into (7.F1).
  useEffect(() => {
    if (!flags.calendar) return;
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k' && location.pathname !== paths.home) {
        event.preventDefault();
        navigate(paths.home, { state: { focusSearch: true } });
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [location.pathname, navigate, flags.calendar]);

  // Smooth inertial scrolling.
  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.1,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      orientation: 'vertical',
      smoothWheel: true,
      prevent: import.meta.env?.DEV ? node => !!node.closest('[data-agentation-root], [data-agentation-portal]') : undefined,
    });
    let rafId: number;
    function raf(time: number) { lenis.raf(time); rafId = requestAnimationFrame(raf); }
    rafId = requestAnimationFrame(raf);
    return () => { cancelAnimationFrame(rafId); lenis.destroy(); };
  }, []);

  const isHome = location.pathname === paths.home || location.pathname === paths.calendar;
  return (
    <div className="min-h-screen bg-[#F6F7FB] text-[#1B2433] relative flex font-sans antialiased overflow-x-clip selection:bg-[#1B2838]/10 selection:text-[#1B2838]">
      <AtelierCanvas />
      <ViewBoundary name="The navigation" resetKey="shell">
        <Sidebar currentView={navViewOf(location.pathname)} pendingGatesCount={counts.cards} flags={flags} />
      </ViewBoundary>
      <div className={`atelier-main flex-1 flex flex-col min-w-0 z-10 relative px-3 sm:px-7 lg:px-10 pt-7 ${isHome ? 'atelier-home' : ''}`}>
        <PageHeaderSlot.Provider value={headerSlot}>
          <ViewBoundary name="The header" resetKey="shell">
            <TopHeader
              leading={<div ref={setHeaderSlot} className="min-w-0" />}
              onOpenInbox={() => navigate(paths.studio)}
              pendingCount={counts.approvals}
              alertCount={counts.alerts}
              onOpenAlerts={() => navigate(paths.alerts)}
            />
          </ViewBoundary>
          <main className="flex-1 pb-10 w-full"><Outlet /></main>
        </PageHeaderSlot.Provider>
      </div>
    </div>
  );
}
