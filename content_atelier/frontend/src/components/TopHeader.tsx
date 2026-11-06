import React, { useEffect, useRef, useState } from 'react';
import { Bell, ChevronDown } from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';
import { commandCenterLoginUrl, userInitials } from '../auth/session';

interface TopHeaderProps {
  leading?: React.ReactNode;
  onOpenInbox: () => void;
  /** Omitted until the knowledge base has a real screen (L.F2); the old one showed fixture text (S.F2). */
  onOpenBrandKit?: () => void;
  pendingCount: number;
  /** Open failure alerts (6.B4), shown beside the approvals; the bell links to them on Sources (6.F5). */
  alertCount?: number;
  onOpenAlerts?: () => void;
}

/**
 * Top utility bar for the atelier desk.
 * Sits in the main column, aligned with the sidebar wordmark.
 */
export const TopHeader: React.FC<TopHeaderProps> = ({
  leading,
  onOpenInbox,
  onOpenBrandKit,
  pendingCount,
  alertCount = 0,
  onOpenAlerts,
}) => {
  const { user, status, error, refresh, logout } = useAuth();
  const accountName = user?.name || (status === 'loading' ? 'Checking session…' : status === 'error' ? 'Session unavailable' : 'Not signed in');
  const [bellOpen, setBellOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setBellOpen(false);
        setMenuOpen(false);
      }
    };
    window.addEventListener('mousedown', onPointerDown);
    return () => window.removeEventListener('mousedown', onPointerDown);
  }, []);

  return (
    <header ref={rootRef} className="atelier-utility-header relative z-20 flex items-start justify-between gap-x-6 min-h-[56px] pb-6">
      <div className="min-w-0 flex-1">{leading}</div>

      <div className="flex items-center gap-3 shrink-0 pt-1.5">
        <div className="relative">
          <button
            type="button"
            aria-label={`Open notifications: ${pendingCount ? `${pendingCount} waiting` : 'nothing waiting'}, ${alertCount ? `${alertCount} open alert${alertCount === 1 ? '' : 's'}` : 'no open alerts'}`}
            aria-expanded={bellOpen}
            onClick={() => {
              setBellOpen((open) => !open);
              setMenuOpen(false);
            }}
            className="relative w-8 h-8 rounded-full flex items-center justify-center text-[#5E6878] hover:bg-white hover:text-[#1C2434] transition-colors cursor-pointer"
          >
            <Bell className="w-4 h-4" strokeWidth={1.75} />
            {/* The mark says something is waiting or an alert is open; it is drawn only when the API's counts say so (S.F2, 6.F5). */}
            {(pendingCount > 0 || alertCount > 0) && <span data-unread className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-[#F5A524] ring-2 ring-[#F6F7FB]" />}
          </button>

          {bellOpen && (
            <div className="absolute right-0 top-[calc(100%+8px)] w-64 rounded-2xl bg-white border border-[#E8EBF1] shadow-[0_16px_40px_-20px_rgba(16,24,40,0.35)] p-3.5 z-30">
              <div className="text-[11px] font-semibold tracking-[0.14em] uppercase text-[#9AA3B2]">
                Waiting for you
              </div>
              <p className="mt-1.5 text-[13px] text-[#1C2434] font-medium">
                {pendingCount > 0
                  ? `${pendingCount} ${pendingCount === 1 ? 'item' : 'items'} to review`
                  : 'Nothing waiting on you'}
              </p>
              <button
                type="button"
                onClick={() => {
                  setBellOpen(false);
                  onOpenInbox();
                }}
                className="mt-3 w-full h-8 rounded-full bg-[#1B2838] text-white text-[12px] font-medium cursor-pointer"
              >
                Open the Weekly Studio
              </button>
              <div className="mt-4 text-[11px] font-semibold tracking-[0.14em] uppercase text-[#9AA3B2]">
                Alerts
              </div>
              <p className="mt-1.5 text-[13px] text-[#1C2434] font-medium">
                {alertCount > 0 ? `${alertCount} open alert${alertCount === 1 ? '' : 's'}` : 'No open alerts'}
              </p>
              {onOpenAlerts && <button
                type="button"
                onClick={() => {
                  setBellOpen(false);
                  onOpenAlerts();
                }}
                className="mt-3 w-full h-8 rounded-full border border-[#D8DFE8] bg-white text-[#1B2838] text-[12px] font-medium cursor-pointer"
              >
                Open the alerts
              </button>}
            </div>
          )}
        </div>

        <div className="relative">
          <button
            type="button"
            aria-label="Account menu"
            aria-expanded={menuOpen}
            disabled={status === 'loading'}
            onClick={() => {
              setMenuOpen((open) => !open);
              setBellOpen(false);
            }}
            className="flex items-center gap-2 pl-1 pr-1.5 py-1 rounded-full hover:bg-white transition-colors cursor-pointer"
          >
            <span className="w-8 h-8 rounded-full bg-[#1B2838] text-white text-[10px] font-semibold flex items-center justify-center">
              {user ? userInitials(user.name) : '—'}
            </span>
            <span title={accountName} className="hidden sm:block text-[13px] font-semibold text-[#1C2434] max-w-48 truncate">{accountName}</span>
            <ChevronDown className="w-3.5 h-3.5 text-[#A8B0BE]" strokeWidth={1.75} />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-[calc(100%+8px)] w-56 rounded-2xl bg-white border border-[#E8EBF1] shadow-[0_16px_40px_-20px_rgba(16,24,40,0.35)] p-2 z-30">
              <div className="px-2.5 py-2">
                <div className="text-[13px] font-semibold text-[#1C2434] break-words">{accountName}</div>
                {user && <><div className="text-[11px] text-[#9AA3B2]">{user.role === 'team' ? 'Team' : 'Client'} · WIA</div><div className="mt-1 text-[11px] text-[#667184] break-all">{user.email}</div></>}
                {error && <p role="alert" className="mt-2 text-[11px] text-amber-700">{error}</p>}
              </div>
              {!user && <a href={commandCenterLoginUrl()} className="block px-2.5 py-2 rounded-xl text-[12px] font-medium text-[#5070FF] hover:bg-[#EFF3FF]">Sign in</a>}
              {status === 'error' && <button type="button" onClick={() => void refresh()} className="w-full text-left px-2.5 py-2 rounded-xl text-[12px] text-[#667184] hover:bg-[#F4F6FA]">Try signing in again</button>}
              {user && <button type="button" onClick={() => { setMenuOpen(false); void logout(); }} className="w-full text-left px-2.5 py-2 rounded-xl text-[12px] text-[#667184] hover:bg-[#F4F6FA]">Sign out</button>}
              {onOpenBrandKit && <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  onOpenBrandKit();
                }}
                className="w-full text-left px-2.5 py-2 rounded-xl text-[12.5px] text-[#1C2434] hover:bg-[#F4F6FA] cursor-pointer"
              >
                Brand Kit & Voice
              </button>}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
