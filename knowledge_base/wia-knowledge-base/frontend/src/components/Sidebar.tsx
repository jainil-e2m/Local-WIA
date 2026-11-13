import { useEffect, useRef, useState } from 'react';
import { MessagesSquare, Check, ChevronsUpDown, BookOpen, LogOut, CalendarCheck, CalendarDays, FolderOpen, HeartHandshake, HeartPulse, House, ListChecks, ListTodo, Plug, ReceiptText, X } from 'lucide-react';
import floral from '../assets/sidebar-floral-blue.png';
import SidebarOrbit from './SidebarOrbit';
import SidebarEdgeToggle from './SidebarEdgeToggle';
import { VIEWERS, viewerByName } from '../data';
import { SIGN_OUT_HREF, auth, type SignedInUser } from '../auth';
import type { ViewId } from '../types';

export const NAV = [
  { id: 'dashboard' as const, label: 'Overview', icon: House },
  { id: 'clients' as const, label: 'Client portfolio', icon: FolderOpen },
  { id: 'calls' as const, label: 'Call preparation', icon: CalendarDays },
  { id: 'calls-v2' as const, label: 'Call preparation', icon: CalendarCheck },
  { id: 'actions-v3' as const, label: 'Action Hub', icon: ListChecks },
  { id: 'actions-v2' as const, label: 'Action Hub v2', icon: ListTodo },
  { id: 'health' as const, label: 'Health & sentiment', icon: HeartHandshake },
  { id: 'health-v2' as const, label: 'Health & sentiment', icon: HeartPulse },
  { id: 'health-v3' as const, label: 'Health & sentiment', icon: HeartPulse },
  { id: 'assistant' as const, label: 'Client 360', icon: MessagesSquare },
  { id: 'money' as const, label: 'Invoices & contracts', icon: ReceiptText },
];

/** Sections shown as "Coming soon" in this release (their routes are blocked in App). */
const COMING_SOON = [
  { label: 'Overview', icon: House },
  { label: 'Health & Sentiment', icon: HeartHandshake },
  { label: 'Client 360', icon: MessagesSquare },
  { label: 'Invoices & Contracts', icon: ReceiptText },
];
const SOON_VIEWS: ViewId[] = ['dashboard', 'calls', 'health', 'health-v2', 'health-v3', 'assistant', 'money'];

interface Props {
  view: ViewId;
  navigate: (id: ViewId) => void;
  mobileOpen: boolean;
  closeMobile: () => void;
  collapsed: boolean;
  toggleCollapsed: () => void;
  hiddenViews?: ViewId[];
  viewer: string;
  setViewer: (name: string) => void;
}

export default function Sidebar({ view, navigate, mobileOpen, closeMobile, collapsed, toggleCollapsed, hiddenViews = [], viewer, setViewer }: Props) {
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
      <div className="sidebar-brand"><img src="/logos/wia_logo.webp" alt="Wedding Industry Ads" /><div><span>Client Knowledge</span></div><button className="icon-button mobile-close" aria-label="Close navigation" onClick={closeMobile}><X size={18} /></button></div>
      <nav aria-label="Main navigation"><p className="nav-label">THE CLIENT DESK</p>{NAV.filter(item => !hiddenViews.includes(item.id) && !SOON_VIEWS.includes(item.id)).map(({ id, label, icon: Icon }) => <button key={id} onClick={() => go(id)} aria-current={view === id ? 'page' : undefined} aria-label={label} title={label} className={`nav-item ${view === id ? 'active' : ''}`}><Icon size={19} strokeWidth={1.65} /><span>{label}</span></button>)}
        <div className="nav-divider" /><p className="nav-label">COMING SOON</p>{COMING_SOON.map(({ label, icon: Icon }) => <div key={label} className="nav-item nav-soon" aria-disabled="true" title={`${label} · coming soon`}><Icon size={19} strokeWidth={1.65} /><span>{label}</span><b className="nav-new">Soon</b></div>)}</nav>
      <nav aria-label="The foundation" className="nav-foundation"><div className="nav-divider" /><p className="nav-label">THE FOUNDATION</p><button className={`nav-item ${view === 'sources' ? 'active' : ''}`} onClick={() => go('sources')} aria-current={view === 'sources' ? 'page' : undefined} title="Source library"><BookOpen size={19} strokeWidth={1.65} /><span>Source library</span></button><button className={`nav-item ${view === 'settings' ? 'active' : ''}`} onClick={() => go('settings')} aria-current={view === 'settings' ? 'page' : undefined} title="Connections"><Plug size={19} strokeWidth={1.65} /><span>Connections</span></button></nav>
      <div className="sidebar-bottom"><Account viewer={viewer} setViewer={setViewer} /></div>
      {/* on the phone drawer it closes the drawer; elsewhere it collapses / opens the sidebar */}
      <SidebarEdgeToggle collapsed={collapsed} onToggle={() => mobileOpen && window.matchMedia('(max-width: 700px)').matches ? closeMobile() : toggleCollapsed()} />
    </aside>
  </>;
}

/** A small menu that closes on an outside click or Escape. */
function useMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => { if (!ref.current?.contains(event.target as Node)) setOpen(false); };
    const keys = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.stopPropagation(); setOpen(false); } };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', keys, true);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', keys, true); };
  }, [open]);
  return { open, setOpen, ref };
}

/** The account area: the person signed in through Command Center (the live app), or the preview switcher. */
function Account({ viewer, setViewer }: { viewer: string; setViewer: (name: string) => void }) {
  return auth.user ? <SignedInAccount user={auth.user} viewer={viewer} /> : <AccountSwitcher viewer={viewer} setViewer={setViewer} />;
}

/** The person who signed in, as Command Center knows them. No switching: while role-based views are off
 *  (RBAC_ENABLED=false) everyone works in the shared full view. */
function SignedInAccount({ user, viewer }: { user: SignedInUser; viewer: string }) {
  const { open, setOpen, ref } = useMenu();
  const initials = user.name.split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]?.toUpperCase()).join('') || '?';
  return <div className="sidebar-person" ref={ref}>
    <button className="account-trigger" aria-haspopup="menu" aria-expanded={open} aria-label={`Signed in as ${user.name}. Account menu`} title={user.email} onClick={() => setOpen(value => !value)}>
      <span className="person-avatar">{initials}</span>
      <span className="account-name"><strong>{user.name}</strong><small>{user.email}</small></span>
      <ChevronsUpDown size={14} className="account-chevron" />
    </button>
    {open && <div className="account-menu" role="menu" aria-label="Account">
      <p className="account-menu-label">SIGNED IN THROUGH COMMAND CENTER</p>
      <div className="account-option is-current"><span className="person-avatar">{initials}</span><span className="account-name"><strong>{user.name}</strong><small>{user.email}</small></span></div>
      {!auth.rbac && <p className="account-menu-note">Everyone has the full team view in this release ({viewerByName(viewer).fullName}’s).</p>}
      <a className="account-option" role="menuitem" href={SIGN_OUT_HREF}><LogOut size={14} /><span className="account-name"><strong>Sign out</strong><small>Of the Knowledge Base, Command Center and the Atelier</small></span></a>
    </div>}
  </div>;
}

/** The sample preview (no KB behind it): switches which team member the workspace is shown as. */
function AccountSwitcher({ viewer, setViewer }: { viewer: string; setViewer: (name: string) => void }) {
  const { open, setOpen, ref } = useMenu();
  const current = viewerByName(viewer);
  const pick = (name: string) => { setViewer(name); setOpen(false); };
  return <div className="sidebar-person" ref={ref}>
    <button className="account-trigger" aria-haspopup="menu" aria-expanded={open} aria-label={`Signed in as ${current.fullName}, ${current.role}. Switch preview account`} title="Switch preview account" onClick={() => setOpen(value => !value)}>
      <span className="person-avatar">{current.initials}</span>
      <span className="account-name"><strong>{current.fullName}</strong><small>{current.role} · Wedding Industry Ads</small></span>
      <ChevronsUpDown size={14} className="account-chevron" />
    </button>
    {open && <div className="account-menu" role="menu" aria-label="Preview as">
      <p className="account-menu-label">PREVIEW AS</p>
      {VIEWERS.map(v => <button key={v.name} role="menuitemradio" aria-checked={v.name === viewer} className={`account-option ${v.name === viewer ? 'is-current' : ''}`} onClick={() => pick(v.name)}>
        <span className="person-avatar">{v.initials}</span><span className="account-name"><strong>{v.fullName}</strong><small>{v.role}</small></span>{v.name === viewer && <Check size={14} />}
      </button>)}
      <p className="account-menu-note">Preview only. Switching changes what this team member would see; no sign-in happens.</p>
    </div>}
  </div>;
}
