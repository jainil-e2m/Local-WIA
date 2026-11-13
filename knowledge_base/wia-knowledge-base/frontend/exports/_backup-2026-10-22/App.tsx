import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowRight, Bell, BookOpen, CheckCircle2, ChevronRight, Command, Menu, Search, Sparkles, X } from 'lucide-react';
import { CALLS, CLIENTS, EVIDENCE, INITIAL_ACTIONS, clientById, isOutstanding, isOverdue } from './data';
import Sidebar, { NAV } from './components/Sidebar';
import EvidenceDrawer from './components/EvidenceDrawer';
import { Avatar, Badge, Dialog, Empty, SourceIcon } from './components/UI';
import Dashboard from './views/Dashboard';
import Clients from './views/Clients';
import ClientDetail from './views/ClientDetail';
import CallPrep from './views/CallPrep';
import Actions, { ActionRegisterTitle } from './views/Actions';
import WorkspaceTitle from './components/WorkspaceTitle';
import Health from './views/Health';
import Money, { NoFinanceAccess } from './views/Money';
import { isFinanceAdmin } from './finance';
import { CALL_META } from './calls';
import Sources from './views/Sources';
import Settings from './views/Settings';
import type { Action, ClientTab, ViewId, WorkspaceProps } from './types';

const STORAGE_KEY = 'wia-knowledge-preview-actions-v2';
const VIEWS = ['dashboard', 'clients', 'calls', 'actions', 'health', 'money', 'sources', 'settings'];
const TABS: ClientTab[] = ['now', 'profile', 'history', 'brief', 'commitments', 'meetings', 'health', 'support', 'money', 'attendance', 'sources'];
type Route = { view: ViewId; clientId?: string; tab: ClientTab; callId?: string };

function routeFromHash(): Route {
  const [view, item, tab] = window.location.hash.slice(1).split('/');
  const result: Route = { view: VIEWS.includes(view) ? view as ViewId : 'dashboard', tab: TABS.includes(tab as ClientTab) ? tab as ClientTab : 'now' };
  if (view === 'clients' && CLIENTS.some(c => c.id === item)) result.clientId = item;
  if (view === 'calls' && (CALLS.some(c => c.id === item) || CALL_META.some(c => c.id === item))) result.callId = item;
  if (result.tab === 'attendance' && result.clientId && clientById(result.clientId).type !== 'accelerator') result.tab = 'now';
  return result;
}

function loadActions(): Action[] {
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    if (Array.isArray(saved) && saved.length && saved.every((row: Action) => row && typeof row.id === 'string' && CLIENTS.some(c => c.id === row.clientId) && typeof row.title === 'string' && typeof row.owner === 'string' && typeof row.note === 'string' && /^(\d{4}-\d{2}-\d{2})?$/.test(row.due) && ['Open', 'In progress', 'Blocked', 'Done', 'Verified'].includes(row.status) && ['WIA', 'Client'].includes(row.side) && typeof row.acknowledged === 'boolean' && typeof row.sourceId === 'string')) return saved;
  } catch { /* The sample remains usable if browser storage is unavailable. */ }
  return INITIAL_ACTIONS.map(action => ({ ...action }));
}

export default function App() {
  const [route, setRoute] = useState<Route>(routeFromHash);
  const [actions, setActions] = useState<Action[]>(loadActions);
  const [evidenceId, setEvidenceId] = useState<string | null>(null);
  const [viewer, setViewer] = useState('Jacqueline');
  const [searchOpen, setSearchOpen] = useState(false);
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
    const change = () => { setRoute(routeFromHash()); window.scrollTo({ top: 0, behavior: 'instant' }); };
    window.addEventListener('hashchange', change);
    const keys = (event: KeyboardEvent) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setSearchOpen(open => !open); } };
    window.addEventListener('keydown', keys);
    return () => { window.removeEventListener('hashchange', change); window.removeEventListener('keydown', keys); };
  }, []);
  const navigate = (view: ViewId) => { window.location.hash = view; setMobileOpen(false); };
  const openClient = (id: string, tab: ClientTab = 'now') => { window.location.hash = `clients/${id}/${tab}`; };
  const openCall = (id: string) => { window.location.hash = `calls/${id}`; };
  const updateAction = (id: string, patch: Partial<Action>) => setActions(existing => existing.map(action => action.id === id ? { ...action, ...patch } : action));
  const props: WorkspaceProps = { actions, navigate, openClient, openCall, updateAction, notify, showEvidence: setEvidenceId, viewer, setViewer };
  const label = NAV.find(item => item.id === route.view)?.label || (route.view === 'sources' ? 'Source library' : 'Connections');
  useEffect(() => { document.title = `${route.clientId ? clientById(route.clientId).name : label} · WIA Client Knowledge`; }, [route, label]);
  const overdue = actions.filter(isOverdue);
  return <div className={`app-shell ${collapsed ? 'sidebar-is-collapsed' : ''}`}>
    <a className="skip-link" href="#main-content" onClick={event => { event.preventDefault(); document.getElementById('main-content')?.focus(); }}>Skip to content</a>
    <div className="ambient" aria-hidden="true" />
    <Sidebar view={route.view} navigate={navigate} actionCount={actions.filter(isOutstanding).length} mobileOpen={mobileOpen} closeMobile={closeMobile} collapsed={collapsed} toggleCollapsed={() => setCollapsed(value => !value)} hiddenViews={isFinanceAdmin(viewer) ? [] : ['money']} />
    <div className="workspace"><header className="utility-header"><div className="header-leading"><button className="icon-button mobile-menu" aria-label="Open navigation" aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}><Menu size={20} /></button>{route.view !== 'actions' && !(route.view === 'clients' && !route.clientId) && <nav className="header-breadcrumbs" aria-label="Breadcrumb">
      <a href={`#${route.view}`} onClick={closeMobile} aria-current={!route.clientId && !route.callId ? 'page' : undefined}>{label}</a>
      {route.clientId && <><ChevronRight size={13} aria-hidden="true" /><a className="header-client" href={`#clients/${route.clientId}/now`} onClick={closeMobile} aria-current={route.tab === 'now' ? 'page' : undefined}>{clientById(route.clientId).name}</a></>}
    </nav>}{route.view === 'actions' && <ActionRegisterTitle />}{route.view === 'clients' && !route.clientId && <WorkspaceTitle title="Client Portfolio" description="See each client's engagement, progress, and open priorities in one place, with a direct path to their full record." />}</div><div className="header-tools"><button className="header-search" aria-label="Search the workspace" onClick={() => setSearchOpen(true)}><Search size={16} /><span>Search</span><kbd>⌘ K</kbd></button><button className="icon-button notification-button" aria-label="Open attention items" onClick={() => setAlertsOpen(true)}><Bell size={18} />{overdue.length > 0 && <i />}</button><button className="header-user" aria-label="About the Whitney preview account" onClick={() => setHelpOpen(true)}>WH</button></div></header>
    <main id="main-content" tabIndex={-1}>
      {route.view === 'dashboard' && <Dashboard {...props} />}
      {route.view === 'clients' && (route.clientId ? <ClientDetail {...props} id={route.clientId} tab={route.tab} /> : <Clients {...props} />)}
      {route.view === 'calls' && <CallPrep {...props} selectedId={route.callId} />}
      {route.view === 'actions' && <Actions {...props} addAction={action => setActions(existing => [...existing, action])} />}
      {route.view === 'health' && <Health {...props} />}
      {route.view === 'money' && (isFinanceAdmin(viewer) ? <Money {...props} /> : <NoFinanceAccess viewer={viewer} setViewer={setViewer} />)}
      {route.view === 'sources' && <Sources {...props} />}
      {route.view === 'settings' && <Settings {...props} resetPreview={() => { setActions(INITIAL_ACTIONS.map(action => ({ ...action }))); notify('Original sample records restored.'); }} />}
    </main><footer className="workspace-footer"><span>Wedding Industry Ads <i>✧</i> Client Knowledge Base</span><span>Frontend preview · October 9, 2026</span></footer></div>
    {evidenceId && <EvidenceDrawer id={evidenceId} onClose={() => setEvidenceId(null)} openClient={openClient} />}
    {searchOpen && <WorkspaceSearch {...props} close={() => setSearchOpen(false)} />}
    {helpOpen && <Dialog title="A shared memory. A clearer next step." subtitle="THE CLIENT KNOWLEDGE BASE" onClose={() => setHelpOpen(false)}><div className="about-icon"><BookOpen size={31} strokeWidth={1.3} /></div><p className="body-copy">A maintained picture of each client: their background, conversations, commitments, and the next thing that needs care.</p><div className="about-facts"><div><CheckCircle2 size={16} /><p>Six fictional client records make the views easy to explore.</p></div><div><CheckCircle2 size={16} /><p>Action edits stay in this browser and update the other views.</p></div><div><CheckCircle2 size={16} /><p>Call briefs, evidence, and handover context are available in one workspace.</p></div></div><p className="muted body-copy">No live accounts, AI generation, or client messages are connected. The Content Atelier history integration remains a separate later build.</p><button className="button button-primary" onClick={() => setHelpOpen(false)}>Back to the client desk<ArrowRight size={14} /></button></Dialog>}
    {alertsOpen && <Dialog title="A few things need attention." subtitle="THE OPEN LOOPS" drawer onClose={() => setAlertsOpen(false)}>{overdue.length ? overdue.map(action => <button className="alert-item" key={action.id} onClick={() => { setAlertsOpen(false); openClient(action.clientId, 'commitments'); }}><Badge tone="amber">Overdue</Badge><h3>{action.title}</h3><p>{clientById(action.clientId).name} · {action.owner}</p></button>) : <Empty title="No overdue commitments" />}<button className="button button-primary full-width" onClick={() => { setAlertsOpen(false); navigate('actions'); }}>Open the action register<ArrowRight size={14} /></button></Dialog>}
    {toast && <div className="toast" role="status"><CheckCircle2 size={17} /><span>{toast}</span><button className="icon-button" aria-label="Dismiss notification" onClick={() => setToast('')}><X size={14} /></button></div>}
  </div>;
}

function WorkspaceSearch(props: WorkspaceProps & { close: () => void }) {
  const [query, setQuery] = useState('');
  const needle = query.trim().toLowerCase();
  const clients = CLIENTS.filter(client => `${client.name} ${client.contact} ${client.service}`.toLowerCase().includes(needle));
  const sources = needle ? EVIDENCE.filter(source => `${source.title} ${source.excerpt}`.toLowerCase().includes(needle)).slice(0, 5) : [];
  const actions = needle ? props.actions.filter(action => action.title.toLowerCase().includes(needle)).slice(0, 4) : [];
  return <Dialog title="Find a little context." subtitle="SEARCH THE WORKSPACE" className="search-dialog" onClose={props.close}><label className="global-search"><Search size={19} /><input autoFocus placeholder="A client, a promise, or a phrase…" aria-label="Search all clients and sources" value={query} onChange={e => setQuery(e.target.value)} /><kbd>ESC</kbd></label>{clients.length > 0 && <div className="search-group"><p className="small-label">CLIENTS</p>{clients.map(client => <button className="search-result" key={client.id} onClick={() => { props.close(); props.openClient(client.id); }}><Avatar client={client} small /><div><strong>{client.name}</strong><span>{client.service} · {client.contact}</span></div><ArrowRight size={14} /></button>)}</div>}{actions.length > 0 && <div className="search-group"><p className="small-label">COMMITMENTS</p>{actions.map(action => <button className="search-result" key={action.id} onClick={() => { props.close(); props.openClient(action.clientId, 'commitments'); }}><Sparkles size={17} /><div><strong>{action.title}</strong><span>{clientById(action.clientId).name} · {action.status}</span></div><ArrowRight size={14} /></button>)}</div>}{sources.length > 0 && <div className="search-group"><p className="small-label">SOURCE CONTEXT</p>{sources.map(source => <button className="search-result" key={source.id} onClick={() => { props.close(); props.showEvidence(source.id); }}><SourceIcon kind={source.kind} size={18} /><div><strong>{source.title}</strong><span>{clientById(source.clientId).name} · {source.kind}</span></div><ArrowRight size={14} /></button>)}</div>}{!clients.length && !sources.length && !actions.length && <Empty title="No matching context" />}<div className="search-footer"><Command size={12} /> Ctrl / ⌘ K to open · Escape to close</div></Dialog>;
}
