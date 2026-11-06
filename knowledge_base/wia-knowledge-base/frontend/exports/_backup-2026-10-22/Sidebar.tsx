import { useEffect, useRef } from 'react';
import { ArrowLeftToLine, BookOpen, CalendarDays, FolderOpen, HeartHandshake, House, ListChecks, Menu, PanelLeftClose, Plug, ReceiptText, X } from 'lucide-react';
import floral from '../assets/sidebar-floral-blue.png';
import SidebarOrbit from './SidebarOrbit';
import type { ViewId } from '../types';

export const NAV = [
  { id: 'dashboard' as const, label: 'Overview', icon: House },
  { id: 'clients' as const, label: 'Client portfolio', icon: FolderOpen },
  { id: 'calls' as const, label: 'Call preparation', icon: CalendarDays },
  { id: 'actions' as const, label: 'Action register', icon: ListChecks },
  { id: 'health' as const, label: 'Health & sentiment', icon: HeartHandshake },
  { id: 'money' as const, label: 'Invoices & contracts', icon: ReceiptText },
];

interface Props {
  view: ViewId;
  navigate: (id: ViewId) => void;
  actionCount: number;
  mobileOpen: boolean;
  closeMobile: () => void;
  collapsed: boolean;
  toggleCollapsed: () => void;
  hiddenViews?: ViewId[];
}

export default function Sidebar({ view, navigate, actionCount, mobileOpen, closeMobile, collapsed, toggleCollapsed, hiddenViews = [] }: Props) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!mobileOpen || !window.matchMedia('(max-width: 700px)').matches) return;
    const previous = document.activeElement as HTMLElement | null;
    const sidebar = ref.current;
    const buttons = sidebar?.querySelectorAll<HTMLButtonElement>('button');
    const visible = () => Array.from(buttons || []).filter(button => button.getClientRects().length > 0);
    visible()[0]?.focus();
    const keys = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeMobile();
      if (event.key !== 'Tab') return;
      const controls = visible();
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    document.addEventListener('keydown', keys);
    return () => { document.removeEventListener('keydown', keys); previous?.focus(); };
  }, [mobileOpen, closeMobile]);
  const go = (id: ViewId) => { navigate(id); closeMobile(); };
  return <>
    {mobileOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={closeMobile} />}
    <aside ref={ref} className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="sidebar-floral" aria-hidden="true"><img src={floral} alt="" /></div>
      <SidebarOrbit />
      <div className="sidebar-brand"><img src="/logos/wia_logo.webp" alt="Wedding Industry Ads" /><div><span>Client Knowledge</span><small>A little more understood.</small></div><button className="icon-button mobile-close" aria-label="Close navigation" onClick={closeMobile}><X size={18} /></button></div>
      <nav aria-label="Main navigation"><p className="nav-label">THE CLIENT DESK</p>{NAV.filter(item => !hiddenViews.includes(item.id)).map(({ id, label, icon: Icon }) => <button key={id} onClick={() => go(id)} aria-current={view === id ? 'page' : undefined} aria-label={id === 'actions' && actionCount > 0 ? `${label} ${actionCount}` : label} title={label} className={`nav-item ${view === id ? 'active' : ''}`}><Icon size={19} strokeWidth={1.65} /><span>{label}</span>{id === 'actions' && actionCount > 0 && <b>{actionCount}</b>}</button>)}<div className="nav-divider" /><p className="nav-label">THE FOUNDATION</p><button className={`nav-item ${view === 'sources' ? 'active' : ''}`} onClick={() => go('sources')} aria-current={view === 'sources' ? 'page' : undefined} title="Source library"><BookOpen size={19} strokeWidth={1.65} /><span>Source library</span></button><button className={`nav-item ${view === 'settings' ? 'active' : ''}`} onClick={() => go('settings')} aria-current={view === 'settings' ? 'page' : undefined} title="Connections"><Plug size={19} strokeWidth={1.65} /><span>Connections</span></button></nav>
      <div className="sidebar-bottom"><div className="sidebar-person"><div className="person-avatar">WH</div><div><strong>Whitney Hodges</strong><small>Founder · Wedding Industry Ads</small></div><button className="icon-button collapse-button" onClick={toggleCollapsed} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>{collapsed ? <Menu size={17} /> : <PanelLeftClose size={17} />}</button></div><span className="sidebar-footnote"><ArrowLeftToLine size={11} /> A shared memory for your team</span></div>
    </aside>
  </>;
}
