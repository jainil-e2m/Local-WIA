import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { clientDetailsVersion, subscribeClientDetails } from './clientDetails';
import { ArrowRight, Bell, BookOpen, CheckCircle2, ChevronRight, Menu, X } from 'lucide-react';
import kbLive from '@kb-live';
import { CALLS, CLIENTS, DEMO_DATE, INITIAL_ACTIONS, clientById, dateLabel, isOverdue, viewerByName } from './data';
import Sidebar, { NAV } from './components/Sidebar';
import EvidenceDrawer from './components/EvidenceDrawer';
import { Badge, Dialog, Empty } from './components/UI';
import Dashboard from './views/Dashboard';
import Clients from './views/Clients';
import ClientDetail from './views/ClientDetail';
import { clientSectionHash } from './clientDestinations';
import CallPrep from './views/CallPrep';
import { isAdmin } from './views/Actions';
import HealthRevised from './views/HealthRevised';
import HealthV3 from './views/HealthV3';
import ActionsTeams from './views/ActionsTeams';
import CallPrepV2 from './views/CallPrepV2';
import WorkspaceTitle from './components/WorkspaceTitle';
import Health from './views/Health';
import { NoFinanceAccess } from './views/Money';
import MoneyRevised from './views/MoneyRevised';
import { FINANCE_CLIENTS, isFinanceAdmin } from './finance';
import { CALL_META } from './calls';
import Client360, { seed as seedClient360 } from './views/Client360';
import Sources from './views/Sources';
import Settings from './views/Settings';
import type { Action, ClientTab, ViewId, WorkspaceProps } from './types';

const STORAGE_KEY = 'wia-knowledge-preview-actions-v2';
const VIEWS = ['dashboard', 'clients', 'calls', 'calls-v2', 'actions-v3', 'health', 'health-v2', 'health-v3', 'assistant', 'money', 'sources', 'settings'];
/** Views that are "Coming soon" in this release: reachable by no link, and blocked if opened by URL. */
export const COMING_SOON_VIEWS: ViewId[] = ['dashboard', 'calls', 'calls-v2', 'health', 'health-v2', 'health-v3', 'assistant', 'money'];
const TABS: ClientTab[] = ['now', 'profile', 'history', 'brief', 'commitments', 'meetings', 'health', 'support', 'leads', 'money', 'attendance', 'sources'];
type Route = { view: ViewId; clientId?: string; clientScope?: string; tab: ClientTab; callId?: string };

export function routeFromHash(hash = window.location.hash): Route {
  const [view, item, tab] = hash.slice(1).replace(/^money-v2\b/, 'money').split('/');
  const result: Route = { view: VIEWS.includes(view) ? view as ViewId : 'clients', tab: TABS.includes(tab as ClientTab) ? tab as ClientTab : 'now' };
  if (view === 'clients' && CLIENTS.some(c => c.id === item)) result.clientId = item;
  if ((view === 'money' || view === 'health-v2') && (view === 'money' ? [...CLIENTS, ...FINANCE_CLIENTS] : CLIENTS).some(c => c.id === item)) result.clientScope = item;
  if (result.clientId && (result.tab === 'health' || result.tab === 'money')) {
    result.view = result.tab === 'health' ? 'health-v2' : 'money';
    result.clientScope = result.clientId;
    delete result.clientId;
  }
  if (view === 'calls' && (CALLS.some(c => c.id === item) || CALL_META.some(c => c.id === item))) result.callId = item;
  if (result.tab === 'attendance' && result.clientId && clientById(result.clientId).type !== 'accelerator') result.tab = 'now';
  return result;
}

let lastAllowedHash = '#clients';

/** The route to show, applying this release's rules: old Action Hub links open the Action Hub, and
 * Coming-soon sections are blocked (the URL goes back to the last allowed page). */
function resolveRoute(): { route: Route; blocked: boolean } {
  const hash = window.location.hash;
  if (/^#actions(-v2)?(\/|$)/.test(hash)) {
    window.history.replaceState(null, '', '#actions-v3');
    return resolveRoute();
  }
  const route = routeFromHash(hash);
  if (COMING_SOON_VIEWS.includes(route.view)) {
    window.history.replaceState(null, '', lastAllowedHash);
    return { route: routeFromHash(lastAllowedHash), blocked: true };
  }
  if (hash) lastAllowedHash = hash;
  return { route, blocked: false };
}

function loadActions(): Action[] {
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    if (Array.isArray(saved) && saved.length && saved.every((row: Action) => row && typeof row.id === 'string' && CLIENTS.some(c => c.id === row.clientId) && typeof row.title === 'string' && typeof row.owner === 'string' && typeof row.note === 'string' && /^(\d{4}-\d{2}-\d{2})?$/.test(row.due) && ['Open', 'In progress', 'Blocked', 'Done', 'Verified'].includes(row.status) && ['WIA', 'Client'].includes(row.side) && typeof row.acknowledged === 'boolean' && typeof row.sourceId === 'string')) {
      // Keep the visitor's edits, and add sample records introduced since they were saved (e.g. commitment history).
      const ids = new Set((saved as Action[]).map(a => a.id));
      return [...(saved as Action[]), ...INITIAL_ACTIONS.filter(a => !ids.has(a.id)).map(a => ({ ...a }))];
    }
  } catch { /* The sample remains usable if browser storage is unavailable. */ }
  return INITIAL_ACTIONS.map(action => ({ ...action }));
}

export default function App() {
  const [route, setRoute] = useState<Route>(() => resolveRoute().route);
  const [soonNotice, setSoonNotice] = useState(false);
  const [actions, setActions] = useState<Action[]>(loadActions);
  const [evidenceId, setEvidenceId] = useState<string | null>(null);
  const [viewer, setViewer] = useState('Whitney');
  // Re-render every view when a client's name, aliases, logo or cover is edited.
  const detailsVersion = useSyncExternalStore(subscribeClientDetails, clientDetailsVersion);
  useEffect(() => { seedClient360(viewer, actions); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const [helpOpen, setHelpOpen] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const closeMobile = useCallback(() => setMobileOpen(false), []);
  const [collapsed, setCollapsed] = useState(false);
  const [toast, setToast] = useState('');
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const notify = (message: string) => { if (toastTimer.current) clearTimeout(toastTimer.current); setToast(message); toastTimer.current = setTimeout(() => setToast(''), 4000); };
  useEffect(() => () => { if (toastTimer.current) clearTimeout(toastTimer.current); }, []);
  useEffect(() => { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(actions)); } catch { /* Keep in-memory updates available. */ } }, [actions]);
  useEffect(() => {
    let soonTimer: ReturnType<typeof setTimeout> | undefined;
    const change = () => {
      const { route: next, blocked } = resolveRoute();
      setRoute(next);
      if (blocked) {
        setSoonNotice(true);
        clearTimeout(soonTimer);
        soonTimer = setTimeout(() => setSoonNotice(false), 3000);
        return; // stay where the reader was: no scroll to top
      }
      window.scrollTo({ top: 0, behavior: 'instant' });
    };
    window.addEventListener('hashchange', change);
    return () => { window.removeEventListener('hashchange', change); clearTimeout(soonTimer); };
  }, []);
  const navigate = (view: ViewId) => { window.location.hash = view; setMobileOpen(false); };
  const openClient = (id: string, tab: ClientTab = 'now') => { window.location.hash = clientSectionHash(id, tab); };
  const openCall = (id: string) => { window.location.hash = `calls/${id}`; };
  const updateAction = (id: string, patch: Partial<Action>) => setActions(existing => existing.map(action => action.id === id ? { ...action, ...patch } : action));
  const props: WorkspaceProps = { actions, navigate, openClient, openCall, updateAction, notify, showEvidence: setEvidenceId, viewer, setViewer };
  const label = NAV.find(item => item.id === route.view)?.label || (route.view === 'sources' ? 'Source library' : 'Connections');
  useEffect(() => { document.title = `${route.clientId ? clientById(route.clientId).name : label} · WIA Client Knowledge`; }, [route, label, detailsVersion]);
  useEffect(() => {
    if (route.clientScope && window.location.hash.startsWith('#clients/')) window.history.replaceState(null, '', `#${route.view}/${route.clientScope}`);
  }, [route]);
  const overdue = actions.filter(isOverdue);
  // Deadline-change requests go to admins for approval.
  const requests = isAdmin(viewer) ? actions.filter(action => action.deadlineRequest) : [];
  return <div className={`app-shell ${collapsed ? 'sidebar-is-collapsed' : ''} ${route.clientId ? 'client-record-open' : ''}`}>
    <a className="skip-link" href="#main-content" onClick={event => { event.preventDefault(); document.getElementById('main-content')?.focus(); }}>Skip to content</a>
    <div className="ambient" aria-hidden="true" />
    <Sidebar view={route.view} navigate={navigate} mobileOpen={mobileOpen} closeMobile={closeMobile} collapsed={collapsed} toggleCollapsed={() => setCollapsed(value => !value)} hiddenViews={isFinanceAdmin(viewer) ? [] : ['money']} viewer={viewer} setViewer={setViewer} />
    <div className="workspace"><header className="utility-header"><div className="header-leading"><button className="icon-button mobile-menu" aria-label="Open navigation" aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}><Menu size={20} /></button>{route.view !== 'actions-v3' && route.view !== 'calls-v2' && route.view !== 'health-v2' && route.view !== 'health-v3' && route.view !== 'money' && route.view !== 'assistant' && !(route.view === 'clients' && !route.clientId) && <nav className="header-breadcrumbs" aria-label="Breadcrumb">
      <a href={`#${route.view}`} onClick={closeMobile} aria-current={!route.clientId && !route.callId ? 'page' : undefined}>{label}</a>
      {route.clientId && <><ChevronRight size={13} aria-hidden="true" /><a className="header-client" href={`#clients/${route.clientId}/now`} onClick={closeMobile} aria-current={route.tab === 'now' ? 'page' : undefined}>{clientById(route.clientId).name}</a></>}
    </nav>}</div><div className="header-tools"><button className="icon-button notification-button" aria-label="Open attention items" onClick={() => setAlertsOpen(true)}><Bell size={18} />{(overdue.length > 0 || requests.length > 0) && <i />}</button><button className="header-user" aria-label={`About this preview, viewing as ${viewerByName(viewer).fullName}`} onClick={() => setHelpOpen(true)}>{viewerByName(viewer).initials}</button></div></header>
    <main id="main-content" tabIndex={-1}>
      {route.view === 'dashboard' && <Dashboard {...props} />}
      {route.view === 'clients' && (route.clientId ? <ClientDetail key={route.clientId} {...props} id={route.clientId} tab={route.tab} addAction={action => setActions(existing => [...existing, action])} /> : <Clients {...props} />)}
      {route.view === 'calls' && <CallPrep {...props} selectedId={route.callId} />}
      {route.view === 'calls-v2' && <CallPrepV2 {...props} />}
      {route.view === 'actions-v3' && <ActionsTeams {...props} addAction={action => setActions(existing => [...existing, action])} />}
      {route.view === 'health-v2' && <HealthRevised key={route.clientScope || 'all'} clientId={route.clientScope} {...props} addAction={action => setActions(existing => [...existing, action])} />}
      {route.view === 'health-v3' && <HealthV3 {...props} addAction={action => setActions(existing => [...existing, action])} />}
      {route.view === 'health' && <Health {...props} />}
      {route.view === 'assistant' && <Client360 {...props} />}
      {route.view === 'money' && (isFinanceAdmin(viewer) ? <MoneyRevised clientId={route.clientScope} {...props} /> : <NoFinanceAccess viewer={viewer} setViewer={setViewer} />)}
      {route.view === 'sources' && <Sources {...props} />}
      {route.view === 'settings' && <Settings {...props} resetPreview={() => { setActions(INITIAL_ACTIONS.map(action => ({ ...action }))); notify('Original sample records restored.'); }} />}
    </main><footer className="workspace-footer"><span>Wedding Industry Ads <i>✧</i> Client Knowledge Base</span><span>{kbLive.meta ? `Real KB records (local only) · as of ${dateLabel(DEMO_DATE, { day: 'numeric', month: 'long', year: 'numeric' })}` : 'Frontend preview · October 9, 2026'}</span></footer></div>
    {evidenceId && <EvidenceDrawer id={evidenceId} onClose={() => setEvidenceId(null)} openClient={openClient} />}
    {helpOpen && <Dialog title="A shared memory. A clearer next step." subtitle="THE CLIENT KNOWLEDGE BASE" onClose={() => setHelpOpen(false)}><div className="about-icon"><BookOpen size={31} strokeWidth={1.3} /></div><p className="body-copy">A maintained picture of each client: their background, conversations, commitments, and the next thing that needs care.</p><div className="about-facts"><div><CheckCircle2 size={16} /><p>Six fictional client records make the views easy to explore.</p></div><div><CheckCircle2 size={16} /><p>Action edits stay in this browser and update the other views.</p></div><div><CheckCircle2 size={16} /><p>Call briefs, evidence, and handover context are available in one workspace.</p></div></div><p className="muted body-copy">No live accounts, AI generation, or client messages are connected. The Content Atelier history integration remains a separate later build.</p><button className="button button-primary" onClick={() => setHelpOpen(false)}>Back to the client desk<ArrowRight size={14} /></button></Dialog>}
    {alertsOpen && <Dialog title="Notifications" drawer onClose={() => setAlertsOpen(false)}>{requests.map(action => <button className="alert-item" key={`req-${action.id}`} onClick={() => { setAlertsOpen(false); window.location.hash = 'actions-v3'; }}><Badge tone="blue">Approve date</Badge><h3>{action.title}</h3><p>{action.deadlineRequest!.by} asks to move it to {dateLabel(action.deadlineRequest!.to)} · {clientById(action.clientId).name}</p></button>)}{overdue.length ? overdue.map(action => <button className="alert-item" key={action.id} onClick={() => { setAlertsOpen(false); openClient(action.clientId, 'commitments'); }}><Badge tone="amber">Overdue</Badge><h3>{action.title}</h3><p>{clientById(action.clientId).name} · {action.owner}</p></button>) : !requests.length && <Empty title="No overdue commitments" />}<button className="button button-primary full-width" onClick={() => { setAlertsOpen(false); navigate('actions-v3'); }}>Open the Action Hub<ArrowRight size={14} /></button></Dialog>}
    {soonNotice && <div className="mvp-soon-toast" role="status">Coming soon. This section isn’t part of this preview yet.</div>}
    {toast && <div className="toast" role="status"><CheckCircle2 size={17} /><span>{toast}</span><button className="icon-button" aria-label="Dismiss notification" onClick={() => setToast('')}><X size={14} /></button></div>}
  </div>;
}

