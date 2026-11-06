import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
// An asset URL rather than an import, so the sidebar also loads where no bundler is present (the view tests).
const sidebarFloral = new URL('../assets/sidebar-floral.png', import.meta.url).href;
import { NextRun } from './NextRun';
import { useAuth } from '../auth/AuthProvider';
import { userInitials } from '../auth/session';
import type { FeatureFlags } from '../utils/workspace';
import { seesDetails, useMe } from '../utils/me';
import { canReadSettings } from '../utils/settings';
import {
  House,
  Layers,
  Lightbulb,
  Search,
  BookOpen,
  Inbox,
  Archive,
  Library,
  Quote,
  SlidersHorizontal,
} from 'lucide-react';

import { navigationItems, NavView } from './navigation';
export type { NavView };

const ICONS = { home: House, studio: Layers, previous: Archive, packs: BookOpen, sources: Inbox, moments: Quote, knowledge: Library, settings: SlidersHorizontal };

interface SidebarProps {
  currentView: NavView | null;
  pendingGatesCount: number;
  flags: FeatureFlags;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  pendingGatesCount,
  flags,
}) => {
  const { user, status } = useAuth();
  const { me } = useMe();
  const accountName = user?.name || (status === 'loading' ? 'Checking session…' : status === 'error' ? 'Session unavailable' : 'Not signed in');
  const accountRole = user ? `${user.role === 'team' ? 'Team' : 'Client'} · WIA` : 'Command Center account';
  const [isCollapsed, setIsCollapsed] = useState(false);
  useEffect(() => {
    const media = window.matchMedia('(max-width: 768px)');
    const adapt = () => { if (media.matches) setIsCollapsed(true); };
    adapt(); media.addEventListener('change', adapt);
    return () => media.removeEventListener('change', adapt);
  }, []);
  const orbitRef = useRef<HTMLDivElement>(null);
  const orbitCanvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const element = orbitRef.current;
    const canvas = orbitCanvasRef.current;
    const context = canvas?.getContext('2d');
    if (!element || !canvas || !context) return;

    const padding = 16;
    const sampleCount = 1024;
    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
    let points: { x: number; y: number }[] = [];
    let perimeter = 1;
    let frameId = 0;
    let startedAt: number | null = null;
    let canvasWidth = 0;
    let canvasHeight = 0;

    // Cache the curved perimeter on resize; frames only interpolate cached points.
    const resize = () => {
      const { width, height } = element.getBoundingClientRect();
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
      canvasWidth = width + padding * 2;
      canvasHeight = height + padding * 2;
      canvas.width = Math.round(canvasWidth * pixelRatio);
      canvas.height = Math.round(canvasHeight * pixelRatio);
      context.setTransform(pixelRatio, 0, 0, pixelRatio, padding * pixelRatio, padding * pixelRatio);
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      const corners = getComputedStyle(element.parentElement!);
      const leftRadius = parseFloat(corners.borderTopLeftRadius) || 0;
      const rightRadius = parseFloat(corners.borderTopRightRadius) || 0;
      path.setAttribute('d', `M${leftRadius} 0 H${width - rightRadius} Q${width} 0 ${width} ${rightRadius} V${height - rightRadius} Q${width} ${height} ${width - rightRadius} ${height} H${leftRadius} Q0 ${height} 0 ${height - leftRadius} V${leftRadius} Q0 0 ${leftRadius} 0 Z`);
      perimeter = path.getTotalLength();
      points = Array.from({ length: sampleCount }, (_, index) => {
        const point = path.getPointAtLength(index / sampleCount * perimeter);
        return { x: point.x, y: point.y };
      });
    };

    const pointAt = (distance: number) => {
      const position = ((distance % perimeter + perimeter) % perimeter) / perimeter * sampleCount;
      const index = Math.floor(position);
      const fraction = position - index;
      const first = points[index];
      const second = points[(index + 1) % sampleCount];
      return { x: first.x + (second.x - first.x) * fraction, y: first.y + (second.y - first.y) * fraction };
    };

    const draw = (timestamp: number) => {
      context.clearRect(-padding, -padding, canvasWidth, canvasHeight);
      if (!motionPreference.matches && points.length) {
        startedAt ??= timestamp;
        const distance = ((timestamp - startedAt) % 16000) / 16000 * perimeter;
        const head = pointAt(distance);
        const tailLength = Math.min(135, perimeter * 0.07);
        const tail = pointAt(distance - tailLength);
        const gradient = context.createLinearGradient(tail.x, tail.y, head.x, head.y);
        gradient.addColorStop(0, 'rgba(229, 183, 68, 0)');
        gradient.addColorStop(0.45, 'rgba(229, 183, 68, 0.35)');
        gradient.addColorStop(1, '#e5b744');
        context.beginPath();
        for (let index = 0; index <= 48; index++) {
          const point = pointAt(distance - tailLength + index / 48 * tailLength);
          if (index === 0) context.moveTo(point.x, point.y);
          else context.lineTo(point.x, point.y);
        }
        context.strokeStyle = gradient;
        context.lineWidth = 2;
        context.lineCap = 'round';
        context.stroke();

        // Only the small ball receives a glow; the trail is one unfiltered stroke.
        context.shadowColor = '#e5af35';
        context.shadowBlur = 10;
        context.beginPath();
        context.arc(head.x, head.y, 3.5, 0, Math.PI * 2);
        context.fillStyle = '#fff1b8';
        context.fill();
        context.shadowBlur = 0;
        context.strokeStyle = '#dba632';
        context.lineWidth = 1;
        context.stroke();
      }
      frameId = requestAnimationFrame(draw);
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    frameId = requestAnimationFrame(draw);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frameId);
    };
  }, []);

  // The Administration group (Sources, Moments, Knowledge, Settings) is shown to an approver or an administrator, and to a team
  // member whose own tools live there (intake, the knowledge review queue, the card editor's settings).
  const administration = seesDetails(me) || me.can.manage_intake || me.can.review_knowledge || me.can.edit_cards;
  const navItems = navigationItems(flags, pendingGatesCount, { isTeam: user?.role === 'team', canReadSettings: canReadSettings(me), administration })
    .map(item => ({ ...item, icon: ICONS[item.icon] }));
  const groups = [
    { id: 'main', label: null, items: navItems.filter(item => item.group === 'main') },
    { id: 'admin', label: 'Administration', items: navItems.filter(item => item.group === 'admin') },
  ].filter(group => group.items.length);

  return (
    <aside data-collapsed={isCollapsed} className={`atelier-sidebar sticky self-start shrink-0 flex flex-col z-30 select-none ${isCollapsed ? 'top-3 h-[calc(100dvh-24px)] ml-3 my-3 w-[72px]' : 'top-0 h-[100dvh] w-[272px]'}`}>
      {!isCollapsed && <div className="atelier-sidebar-floral" aria-hidden="true"><img src={sidebarFloral} alt="" /></div>}
      <div ref={orbitRef} className="atelier-sidebar-orbit" aria-hidden="true">
        <canvas ref={orbitCanvasRef} className="atelier-sidebar-orbit-canvas" />
      </div>
      <div className={`${isCollapsed ? 'px-0' : 'px-6'} pt-7 pb-2 relative z-10`}>
        <div className={`flex items-center gap-3 ${isCollapsed ? 'justify-center' : ''}`}>
          <button
            type="button"
            onClick={() => setIsCollapsed((collapsed) => !collapsed)}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!isCollapsed}
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className={`${isCollapsed ? 'w-9 h-9' : 'w-14 h-14'} rounded-full flex items-center justify-center shrink-0 hover:bg-[#EFF3FF] cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#5070FF]`}
          >
            <img src="/logos/wia_logo.webp" alt="Wedding Industry Ads logo" className="w-full h-full object-contain" />
          </button>
          <div className={`min-w-0 leading-tight ${isCollapsed ? 'hidden' : ''}`}>
            <div className="font-editorial text-[22px] font-medium tracking-[-0.02em] text-[#B99A43]">
              Content Atelier
            </div>
          </div>
        </div>
      </div>

      <nav aria-label="Main navigation" className="px-3.5 pt-5 relative z-10">
        {groups.map(group => (
          <div key={group.id} data-nav-group={group.id} role={group.label ? 'group' : undefined} aria-label={group.label ?? undefined}
            className={group.label ? `${isCollapsed ? 'mt-4 pt-3 border-t border-[#E6E9F0] space-y-2' : 'mt-6 space-y-0.5'}` : isCollapsed ? 'space-y-2' : 'space-y-1'}>
            {group.label && !isCollapsed && <p className="px-3 pb-1 text-[10px] font-medium uppercase tracking-[0.16em] text-[#A0A8B6]">{group.label}</p>}
            {group.items.map((item) => {
            const isActive = currentView === item.id;
            const Icon = item.icon;
            return (
              <Link
                key={item.id}
                to={item.path}
                aria-current={isActive ? 'page' : undefined}
                aria-label={item.label}
                title={isCollapsed ? item.label : undefined}
                className={`relative w-full flex items-center ${isCollapsed ? 'justify-center h-10 px-0 rounded-full' : 'justify-between px-3 py-2.5 rounded-xl'} gap-2 text-[13px] transition-colors cursor-pointer ${
                  isActive
                    ? isCollapsed
                      ? 'bg-[#E3EDFF] text-[#5070FF] shadow-[0_0_14px_rgba(80,112,255,0.16)] before:absolute before:-left-1 before:top-2 before:bottom-2 before:w-0.5 before:rounded-full before:bg-[#5070FF]'
                      : 'bg-[#E9F0FA] text-[#173354] font-semibold before:absolute before:left-0 before:top-0 before:bottom-0 before:w-[3px] before:rounded-l-xl before:bg-[#2680EB]'
                    : 'text-[#5E6878] hover:bg-[#F4F6FA] hover:text-[#1C2434]'
                }`}
              >
                <span className="flex items-center gap-3 min-w-0">
                  <Icon
                    strokeWidth={1.75}
                    className={`w-[16px] h-[16px] shrink-0 ${
                      isActive ? 'text-[#173354]' : 'text-[#53637C]'
                    }`}
                  />
                  {!isCollapsed && <span className="truncate">{item.label}</span>}
                </span>
                {!isCollapsed && item.count && (
                  <span className="min-w-5 h-5 px-1 rounded-full bg-[#EEF0F4] flex items-center justify-center text-[10px] tabular-nums text-[#53637C] font-medium">
                    {item.count}
                  </span>
                )}
              </Link>
            );
          })}
          </div>
        ))}
      </nav>

      <div className="flex-1 min-h-4" aria-hidden="true" />
      <div className={`${isCollapsed ? 'mx-3.5' : 'mx-5'} pb-7 pt-4 space-y-5 relative z-10`}>
        <NextRun compact={isCollapsed} />

        {/* Who is signed in, and nothing more: it opens nothing, so it shows no menu arrow (7.F1). Sign-out is in the header's
            account menu. */}
        <div title={`${accountName} · ${accountRole}`} className={`flex items-center gap-3 py-1 ${isCollapsed ? 'justify-center' : 'px-1'}`}>
          <div className={`${isCollapsed ? 'w-8 h-8 text-[10px]' : 'w-10 h-10 text-[11px]'} rounded-full bg-[#1B2838] text-white flex items-center justify-center font-semibold tracking-wide shrink-0`}>
            {user ? userInitials(user.name) : '—'}
          </div>
          <div className={`min-w-0 flex-1 leading-tight ${isCollapsed ? 'hidden' : ''}`}>
            <div className="text-[13px] font-semibold text-[#1C2434] truncate">{accountName}</div>
            <div className="text-[11px] text-[#9AA3B2] mt-0.5">{accountRole}</div>
          </div>
        </div>
      </div>
    </aside>
  );
};
