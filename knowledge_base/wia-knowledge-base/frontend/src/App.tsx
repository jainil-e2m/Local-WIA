import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { clientDetailsVersion, subscribeClientDetails } from './clientDetails';
import { allEdits, editOf, isSaving, saveEdit } from './sharedEdits';
import { initialViewer } from './auth';
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
import ActionHubV2 from './views/ActionHubV2';
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

const VIEWS = ['dashboard', 'clients', 'calls', 'calls-v2', 'actions-v2', 'actions-v3', 'health', 'health-v2', 'health-v3', 'assistant', 'money', 'sources', 'settings'];
/** Views that are "Coming soon" in this release: reachable by no link, and blocked if opened by URL. */
export const COMING_SOON_VIEWS: ViewId[] = ['dashboard', 'calls', 'health', 'health-v2', 'health-v3', 'assistant', 'money'];
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
  if (/^#actions(\/|$)/.test(hash)) {
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

// Fields the source (ClickUp) also sets. An edit records what the source said at the time (`_base`); once the source
// says something else, the source is newer and wins again. Notes, history and the like are the KB's own and stay.
const SOURCE_FIELDS = ['status', 'owner', 'due', 'title', 'side'] as const;
type ActionEdit = Partial<Action> & { created?: boolean; _base?: Partial<Record<typeof SOURCE_FIELDS[number], unknown>> };

/** An action as the KB built it, with everyone's saved edits on top (sharedEdits.ts). */
function withEdits(id: string): Action | undefined {
  const base = INITIAL_ACTIONS.find(a => a.id === id);
  const { created, _base, ...edit } = (editOf('action', id)?.data ?? {}) as ActionEdit;
  if (base) {
    for (const f of SOURCE_FIELDS) {
      if (f in edit && _base && f in _base && JSON.stringify(_base[f]) !== JSON.stringify(base[f])) delete edit[f];
    }
    return { ...base, ...edit };
  }
  return created && CLIENTS.some(c => c.id === edit.clientId) ? edit as Action : undefined;
}

/** The changes to save, plus what the source said for any source field they change (see SOURCE_FIELDS). */
function withSourceBase(id: string, patch: Partial<Action>): Record<string, unknown> {
  const base = INITIAL_ACTIONS.find(a => a.id === id);
  const changed = SOURCE_FIELDS.filter(f => f in patch);
  if (!base || !changed.length) return patch;
  const before = (editOf('action', id)?.data as ActionEdit | undefined)?._base ?? {};
  return { ...patch, _base: { ...before, ...Object.fromEntries(changed.map(f => [f, base[f]])) } };
}

function loadActions(): Action[] {
  const ids = new Set(INITIAL_ACTIONS.map(a => a.id));
  const added = allEdits('action').map(([id]) => id).filter(id => !ids.has(id));
  return [...INITIAL_ACTIONS.map(a => a.id), ...added].map(withEdits).filter((a): a is Action => !!a);
}

export default function App() {
  const [route, setRoute] = useState<Route>(() => resolveRoute().route);
  const [soonNotice, setSoonNotice] = useState(false);
  const [actions, setActions] = useState<Action[]>(loadActions);
  const [evidenceId, setEvidenceId] = useState<string | null>(null);
  // The view: Whitney's for everyone while role-based views are off (auth.ts), the person's own once they're on.
  const [viewer, setViewer] = useState(initialViewer);
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
  // Every action change is a button someone pressed: shown at once and saved for everyone. Once the item's last
  // save lands, the screen shows what the server holds: their own change, or a colleague's newer version (with
  // the reason) when a save was refused or failed. An action only this browser knows (an AI proposal approved a
  // moment ago, before the KB rebuilt) keeps its local copy.
  const settle = (id: string) => {
    if (isSaving('action', id)) return;
    setActions(existing => existing.map(action => action.id === id ? withEdits(id) ?? action : action));
  };
  const updateAction = (id: string, patch: Partial<Action>) => {
    setActions(existing => existing.map(action => action.id === id ? { ...action, ...patch } : action));
    saveEdit('action', id, withSourceBase(id, patch), viewer)
      .then(() => settle(id), (error: Error) => { settle(id); notify(error.message); });
  };
  const addAction = (action: Action) => {
    setActions(existing => [...existing, action]);
    // An approved AI proposal is already saved by its decision and joins the KB's own list.
    if (action.id.startsWith('ai-')) return;
    saveEdit('action', action.id, { ...action, created: true }, viewer).catch((error: Error) => {
      if (!editOf('action', action.id)) setActions(existing => existing.filter(a => a.id !== action.id));
      notify(error.message);
    });
  };
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
    <div className="workspace"><header className="utility-header"><div className="header-leading"><button className="icon-button mobile-menu" aria-label="Open navigation" aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}><Menu size={20} /></button>{route.view !== 'actions-v3' && route.view !== 'actions-v2' && route.view !== 'calls-v2' && route.view !== 'health-v2' && route.view !== 'health-v3' && route.view !== 'money' && route.view !== 'assistant' && !(route.view === 'clients' && !route.clientId) && <nav className="header-breadcrumbs" aria-label="Breadcrumb">
      <a href={`#${route.view}`} onClick={closeMobile} aria-current={!route.clientId && !route.callId ? 'page' : undefined}>{label}</a>
      {route.clientId && <><ChevronRight size={13} aria-hidden="true" /><a className="header-client" href={`#clients/${route.clientId}/now`} onClick={closeMobile} aria-current={route.tab === 'now' ? 'page' : undefined}>{clientById(route.clientId).name}</a></>}
    </nav>}</div><div className="header-tools"><button className="icon-button notification-button" aria-label="Open attention items" onClick={() => setAlertsOpen(true)}><Bell size={18} />{(overdue.length > 0 || requests.length > 0) && <i />}</button><button className="header-user" aria-label={`About this preview, viewing as ${viewerByName(viewer).fullName}`} onClick={() => setHelpOpen(true)}>{viewerByName(viewer).initials}</button></div></header>
    <main id="main-content" tabIndex={-1}>
      {route.view === 'dashboard' && <Dashboard {...props} />}
      {route.view === 'clients' && (route.clientId ? <ClientDetail key={route.clientId} {...props} id={route.clientId} tab={route.tab} addAction={addAction} /> : <Clients {...props} />)}
      {route.view === 'calls' && <CallPrep {...props} selectedId={route.callId} />}
      {route.view === 'calls-v2' && <CallPrepV2 {...props} />}
      {route.view === 'actions-v3' && <ActionsTeams {...props} addAction={addAction} />}
      {route.view === 'actions-v2' && <ActionHubV2 {...props} addAction={addAction} />}
      {route.view === 'health-v2' && <HealthRevised key={route.clientScope || 'all'} clientId={route.clientScope} {...props} addAction={addAction} />}
      {route.view === 'health-v3' && <HealthV3 {...props} addAction={addAction} />}
      {route.view === 'health' && <Health {...props} />}
      {route.view === 'assistant' && <Client360 {...props} />}
      {route.view === 'money' && (isFinanceAdmin(viewer) ? <MoneyRevised clientId={route.clientScope} {...props} /> : <NoFinanceAccess viewer={viewer} setViewer={setViewer} />)}
      {route.view === 'sources' && <Sources {...props} />}
      {route.view === 'settings' && <Settings {...props} resetPreview={() => { setActions(INITIAL_ACTIONS.map(action => ({ ...action }))); notify('Original sample records restored.'); }} />}
    </main><footer className="workspace-footer"><span>Wedding Industry Ads <i>✧</i> Client Knowledge Base</span><span>{kbLive.meta ? `Real KB records (local only) · as of ${dateLabel(DEMO_DATE, { day: 'numeric', month: 'long', year: 'numeric' })}` : 'Frontend preview · October 9, 2026'}</span></footer></div>
    {evidenceId && <EvidenceDrawer id={evidenceId} onClose={() => setEvidenceId(null)} openClient={openClient} />}
    {helpOpen && <Dialog title="A shared memory. A clearer next step." subtitle="THE CLIENT KNOWLEDGE BASE" onClose={() => setHelpOpen(false)}><div className="about-icon"><BookOpen size={31} strokeWidth={1.3} /></div><p className="body-copy">A maintained picture of each client: their background, conversations, commitments, and the next thing that needs care.</p><div className="about-facts"><div><CheckCircle2 size={16} /><p>Six fictional client records make the views easy to explore.</p></div><div><CheckCircle2 size={16} /><p>Action edits are saved for the whole team when you press a button that commits them.</p></div><div><CheckCircle2 size={16} /><p>Call briefs, evidence, and handover context are available in one workspace.</p></div></div><p className="muted body-copy">No live accounts, AI generation, or client messages are connected. The Content Atelier history integration remains a separate later build.</p><button className="button button-primary" onClick={() => setHelpOpen(false)}>Back to the client desk<ArrowRight size={14} /></button></Dialog>}
    {alertsOpen && <Dialog title="Notifications" drawer onClose={() => setAlertsOpen(false)}>{requests.map(action => <button className="alert-item" key={`req-${action.id}`} onClick={() => { setAlertsOpen(false); window.location.hash = 'actions-v3'; }}><Badge tone="blue">Approve date</Badge><h3>{action.title}</h3><p>{action.deadlineRequest!.by} asks to move it to {dateLabel(action.deadlineRequest!.to)} · {clientById(action.clientId).name}</p></button>)}{overdue.length ? overdue.map(action => <button className="alert-item" key={action.id} onClick={() => { setAlertsOpen(false); openClient(action.clientId, 'commitments'); }}><Badge tone="amber">Overdue</Badge><h3>{action.title}</h3><p>{clientById(action.clientId).name} · {action.owner}</p></button>) : !requests.length && <Empty title="No overdue commitments" />}<button className="button button-primary full-width" onClick={() => { setAlertsOpen(false); navigate('actions-v3'); }}>Open the Action Hub<ArrowRight size={14} /></button></Dialog>}
    {soonNotice && <div className="mvp-soon-toast" role="status">Coming soon. This section isn’t part of this preview yet.</div>}
    {toast && <div className="toast" role="status"><CheckCircle2 size={17} /><span>{toast}</span><button className="icon-button" aria-label="Dismiss notification" onClick={() => setToast('')}><X size={14} /></button></div>}
  </div>;
}

