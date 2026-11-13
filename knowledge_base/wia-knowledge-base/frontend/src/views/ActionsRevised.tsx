import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { AlertCircle, CalendarClock, CalendarDays, Check, CheckCircle2, ChevronRight, CircleCheck, Building2, Inbox, LayoutGrid, List, Plus, RefreshCw, RotateCcw, User, Users } from 'lucide-react';
import { CLIENTS, DEMO_DATE, INITIAL_ACTIONS, PROGRAMME_TASKS, REVIEW_ITEMS, SYNC_STATUS, addDays, clientById, dateLabel, daysBetween, isOutstanding, isOverdue, VIEWERS } from '../data';
import { Badge, Dialog, Empty, SearchField } from '../components/UI';
import { ThemedSelect } from '../components/ThemedSelect';
import { ActionDrawer, AddActionDialog, DoneDialog, ReviewQueue, VerifyDialog, decideDeadline, isAdmin } from './Actions';
import type { Action, Priority, ProgrammeTask, ReviewItem, WorkspaceProps } from '../types';
import './ActionsRevised.css';
import { me } from '../auth';

/*
 * Revised Action Hub: four buckets by who has the next move (me, my team, the client, done),
 * shown as a board or a list. Accelerator upkeep (programme ops) sits in the same list with its own hue.
 * Admins also get Needs review: the triage queue plus deadline-change requests waiting for approval.
 */

type Bucket = 'mine' | 'team' | 'client' | 'done';
const BUCKETS: { id: Bucket; label: string; kpi: string; detail: string; icon: typeof User }[] = [
  { id: 'mine', label: 'My pending', kpi: 'Pending (your actions)', detail: 'Items assigned to you', icon: User },
  { id: 'team', label: 'Team pending', kpi: 'Pending (team)', detail: 'Items assigned to your team', icon: Users },
  { id: 'client', label: 'Client pending', kpi: 'Pending (client)', detail: 'Waiting on client response', icon: Building2 },
  { id: 'done', label: 'Completed', kpi: 'Completed', detail: 'Done or verified', icon: CircleCheck },
];
const STATUS_LABEL: Record<Bucket, string> = { mine: 'Pending (You)', team: 'Pending (Team)', client: 'Pending (Client)', done: 'Completed' };
const PREVIEW_ROWS = 5;
type Range = 'today' | 'tomorrow' | 'week' | 'all';
const RANGES: [Range, string][] = [['today', 'Due today'], ['tomorrow', 'Due tomorrow'], ['week', 'This week'], ['all', 'All time']];

/** One row/card: a client action, or an internal programme-ops task. */
type Item = { kind: 'action'; id: string; a: Action; due: string; bucket: Bucket } | { kind: 'programme'; id: string; p: ProgrammeTask; due: string; bucket: Bucket };

// Older saved actions have no priority: fall back to the sample value, then Medium.
const priorityOf = (a: Action): Priority => a.priority || INITIAL_ACTIONS.find(x => x.id === a.id)?.priority || 'Medium';
const fullDate = (d: string) => d ? dateLabel(d, { day: 'numeric', month: 'short', year: 'numeric' }) : 'No date';
function relative(due: string, open: boolean, recurring = false) {
  if (!due || !open) return '';
  const days = daysBetween(DEMO_DATE, due);
  if (days === 0) return 'Today';
  if (days === 1) return 'Tomorrow';
  if (days < 0) return recurring ? 'Recurring' : `${-days} ${days === -1 ? 'day' : 'days'} late`;
  return `${days} days`;
}
const initials = (name: string) => name ? name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() : '?';
const roleOf = (owner: string, client: boolean) => client ? 'Client contact' : VIEWERS.find(v => v.name === owner)?.role || (owner ? 'WIA team' : 'Needs an owner');
const inRange = (due: string, range: Range) => range === 'all' || (!!due && (range === 'today' ? due === DEMO_DATE : range === 'tomorrow' ? due === addDays(DEMO_DATE, 1) : due >= DEMO_DATE && due <= addDays(DEMO_DATE, 6)));

type SyncSource = { source: string; at: string; failed: string };
// Register default: one failed source so the failure state can be reviewed.
const REGISTER_SOURCES: SyncSource[] = SYNC_STATUS.map(s => s.source === 'Fathom' ? { ...s, failed: 'Sign-in expired. Meeting notes after 9:15 AM are missing.' } : { ...s, failed: '' });

/** Last-sync pill: green when every source synced, red with the failed source and Retry when one didn't. */
export function SyncPill({ initial = REGISTER_SOURCES }: { initial?: SyncSource[] }) {
  const [sources, setSources] = useState(initial);
  const [syncing, setSyncing] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  const failed = sources.filter(s => s.failed);
  const latest = sources.map(s => s.at).sort().pop();
  const retry = () => { setSyncing(true); timer.current = setTimeout(() => { setSources(list => list.map(s => ({ ...s, at: '10:02 AM', failed: '' }))); setSyncing(false); }, 1200); };
  return <div className={`rb-sync ${failed.length ? 'is-failed' : 'is-ok'}`}>
    <button className="rb-sync-pill" aria-describedby="rb-sync-detail">{syncing ? <RefreshCw size={12} className="spin" /> : failed.length ? <AlertCircle size={12} /> : <CheckCircle2 size={12} />}{syncing ? 'Syncing…' : failed.length ? `${failed.length} source${failed.length > 1 ? 's' : ''} failed to sync` : `All sources synced · ${latest}`}</button>
    <div className="rb-sync-pop" id="rb-sync-detail" role="tooltip">
      <ul>{sources.map(s => <li key={s.source} className={s.failed ? 'failed' : ''}><span>{s.failed ? <AlertCircle size={12} /> : <Check size={12} />}{s.source}</span><small>{s.failed ? 'Failed' : s.at}</small>{s.failed && <p>{s.failed}</p>}</li>)}</ul>
      <button className="rb-sync-retry" onClick={retry} disabled={syncing}><RefreshCw size={12} className={syncing ? 'spin' : ''} />{syncing ? 'Syncing all sources…' : 'Sync all now'}</button>
    </div>
  </div>;
}

export default function ActionsRevised(props: WorkspaceProps & { addAction: (action: Action) => void }) {
  const viewer = props.viewer;
  const admin = isAdmin(viewer);
  const [panel, setPanel] = useState<'actions' | 'review'>(() => window.location.hash.endsWith('/review') ? 'review' : 'actions');
  const [layout, setLayout] = useState<'board' | 'list'>('board');
  const [bucket, setBucket] = useState<Bucket | 'all'>('all');
  const [range, setRange] = useState<Range>('all');
  const [client, setClient] = useState('all');
  const [query, setQuery] = useState('');
  const [expanded, setExpanded] = useState<Set<Bucket>>(new Set());
  const [openId, setOpenId] = useState<string | null>(null);
  const [openTask, setOpenTask] = useState<string | null>(null);
  const [doneFor, setDoneFor] = useState<Action | null>(null);
  const [verifyFor, setVerifyFor] = useState<Action | null>(null);
  const [adding, setAdding] = useState(false);
  const [programme, setProgramme] = useState<ProgrammeTask[]>(PROGRAMME_TASKS);
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>(REVIEW_ITEMS);
  const [resolved, setResolved] = useState<{ title: string; outcome: string }[]>([]);

  const firstViewer = useRef(true);
  useEffect(() => { if (firstViewer.current) { firstViewer.current = false; return; } setBucket('all'); if (!isAdmin(viewer)) setPanel('actions'); }, [viewer]);
  // The notifications drawer links admins straight to the review panel.
  useEffect(() => { const sync = () => { if (window.location.hash.endsWith('/review')) setPanel('review'); }; window.addEventListener('hashchange', sync); return () => window.removeEventListener('hashchange', sync); }, []);
  useEffect(() => { if (panel === 'actions' && window.location.hash.endsWith('/review')) history.replaceState(null, '', '#actions-v2'); }, [panel]);

  const needle = query.trim().toLowerCase();
  const items = useMemo(() => {
    const actions: Item[] = props.actions
      .filter(a => client === 'all' || a.clientId === client)
      .filter(a => !needle || `${a.title} ${a.note} ${clientById(a.clientId).name} ${a.owner}`.toLowerCase().includes(needle))
      .map(a => ({ kind: 'action', id: a.id, a, due: a.due, bucket: !isOutstanding(a) ? 'done' : a.side === 'Client' ? 'client' : a.owner === viewer ? 'mine' : 'team' }));
    const tasks: Item[] = client !== 'all' ? [] : programme
      .filter(p => !needle || `${p.title} ${p.programme} ${p.owner}`.toLowerCase().includes(needle))
      .map(p => ({ kind: 'programme', id: p.id, p, due: p.due, bucket: p.status === 'Done' ? 'done' : p.owner === viewer ? 'mine' : 'team' }));
    return [...actions, ...tasks].filter(i => inRange(i.due, range));
  }, [props.actions, programme, client, needle, viewer, range]);
  const groups = useMemo(() => {
    const map = new Map<Bucket, Item[]>(BUCKETS.map(b => [b.id, []]));
    items.forEach(i => map.get(i.bucket)!.push(i));
    map.forEach((list, id) => list.sort((x, y) => id === 'done' ? (y.due || '').localeCompare(x.due || '') : (x.due || '9999').localeCompare(y.due || '9999')));
    return map;
  }, [items]);
  const count = (id: Bucket) => groups.get(id)!.length;
  const total = BUCKETS.reduce((n, b) => n + count(b.id), 0);
  const visibleBuckets = BUCKETS.filter(b => bucket === 'all' || b.id === bucket);
  const listRows = visibleBuckets.flatMap(b => groups.get(b.id)!);
  const requests = props.actions.filter(a => a.deadlineRequest);
  const reviewCount = reviewItems.length + requests.length;

  const log = (a: Action, text: string) => [...(a.history || []), { date: DEMO_DATE, text }];
  const reopen = (a: Action) => { props.updateAction(a.id, { status: 'Open', verification: undefined, history: log(a, `Reopened by ${me(viewer)}; any earlier verification is superseded.`) }); props.notify('Reopened. It is back in the pending list.'); };
  const toggleTask = (id: string) => setProgramme(ps => ps.map(p => p.id === id ? { ...p, status: p.status === 'Done' ? 'Open' : 'Done' } : p));
  const check = (i: Item) => i.kind === 'programme' ? toggleTask(i.id) : isOutstanding(i.a) ? setDoneFor(i.a) : reopen(i.a);
  const open = (i: Item) => i.kind === 'programme' ? setOpenTask(i.id) : setOpenId(i.id);
  const resolve = (item: ReviewItem, outcome: string, action?: Action) => { if (action) props.addAction(action); setReviewItems(list => list.filter(i => i.id !== item.id)); setResolved(r => [{ title: item.title, outcome }, ...r]); props.notify(action ? 'Added to the live register.' : 'Resolved. It won’t be recreated by the next sync.'); };
  const selected = props.actions.find(a => a.id === openId);
  const task = programme.find(p => p.id === openTask);

  /** Card / row content that differs between client actions and programme tasks. */
  const view = (i: Item): { title: string; sub: string; owner: string; role: string; place: string; placeSub: string; placeInitials: string; closed: boolean; late: boolean; rel: string; pill: ReactNode; extra: ReactNode } => {
    if (i.kind === 'programme') { const p = i.p; const doneTask = p.status === 'Done'; return { title: p.title, sub: p.recurring ? `${p.recurring} accelerator upkeep` : 'Accelerator upkeep', owner: p.owner, role: roleOf(p.owner, false), place: p.programme, placeSub: 'Programme ops', placeInitials: p.programme.startsWith('Meta') ? 'MA' : 'GA', closed: doneTask, late: !doneTask && !p.recurring && !!p.due && p.due < DEMO_DATE, rel: relative(p.due, !doneTask, !!p.recurring), pill: <span className="rb-pill pill-programme">Programme ops</span>, extra: null }; }
    const a = i.a; const c = clientById(a.clientId); const pr = priorityOf(a);
    return { title: a.title, sub: a.note, owner: a.owner, role: roleOf(a.owner, a.side === 'Client'), place: c.name, placeSub: c.service, placeInitials: c.initials, closed: !isOutstanding(a), late: isOverdue(a), rel: relative(a.due, isOutstanding(a)),
      pill: i.bucket === 'done' ? <span className="rb-pill status-done">{a.status === 'Done' && a.verifyRequired ? 'Awaiting check' : 'Completed'}</span> : <span className={`rb-pill pri-${pr.toLowerCase()}`}>{pr}</span>,
      extra: a.deadlineRequest ? <span className="rb-flag"><CalendarClock size={11} />Deadline change pending</span> : null };
  };

  const Card = ({ i }: { i: Item }) => { const v = view(i); return <li>
    <div className={`rb-card tone-${i.bucket} ${i.kind === 'programme' ? 'is-programme' : ''} ${v.closed ? 'is-closed' : ''}`}>
      <button className={`rb-check round ${v.closed ? 'checked' : ''}`} aria-label={v.closed ? `Reopen “${v.title}”` : `Mark “${v.title}” done`} title={v.closed ? 'Reopen' : 'Mark done'} onClick={() => check(i)}>{v.closed && <Check size={11} />}</button>
      <button className="rb-card-open" onClick={() => open(i)}>
        <span className={`rb-avatar ${v.owner === viewer ? 'is-me' : ''}`}>{initials(v.owner)}</span>
        <span className="rb-card-body">
          <strong>{v.title}</strong>
          <small>{v.place}{i.kind === 'action' ? (v.owner ? ` · ${v.owner === viewer ? 'You' : v.owner}` : ' · Unassigned') : ` · ${v.owner}`}</small>
          {v.extra}
          <span className="rb-card-foot"><span className={`rb-date ${v.late ? 'is-late' : ''}`}><CalendarDays size={12} />{fullDate(i.due)}{v.rel && ` (${v.rel})`}</span>{v.pill}</span>
        </span>
        <ChevronRight size={15} className="rb-chev" />
      </button>
    </div></li>; };

  const board = <div className="rb-board">{visibleBuckets.map(b => {
    const list = groups.get(b.id)!; const Icon = b.icon; const all = expanded.has(b.id); const shown = all ? list : list.slice(0, PREVIEW_ROWS);
    return <section className={`rb-column tone-${b.id}`} key={b.id} aria-label={b.label}>
      <header><span className="rb-col-icon"><Icon size={16} /></span><h2>{b.label}</h2><span className="rb-count">{list.length}</span></header>
      {list.length ? <ul>{shown.map(i => <Card key={i.id} i={i} />)}</ul> : <p className="rb-empty">Nothing here.</p>}
      {list.length > PREVIEW_ROWS && <button className="rb-more" onClick={() => setExpanded(s => { const n = new Set(s); if (all) n.delete(b.id); else n.add(b.id); return n; })}><Plus size={12} />{all ? 'Show less' : `View more (${list.length - PREVIEW_ROWS})`}</button>}
    </section>;
  })}</div>;

  const list = <div className="rb-table-wrap"><table className="rb-table">
    <thead><tr><th className="rb-col-check"><span className="sr-only">Done</span></th><th>Action item</th><th>Client</th><th>Assigned to</th><th>Due date</th><th>Status</th><th>Priority</th><th><span className="sr-only">Open</span></th></tr></thead>
    <tbody>{listRows.map(i => { const v = view(i); return <tr key={i.id} className={i.kind === 'programme' ? 'is-programme' : ''} onClick={() => open(i)}>
      <td className="rb-col-check" onClick={e => e.stopPropagation()}><button className={`rb-check ${v.closed ? 'checked' : ''}`} aria-label={v.closed ? `Reopen “${v.title}”` : `Mark “${v.title}” done`} title={v.closed ? 'Reopen' : 'Mark done'} onClick={() => check(i)}>{v.closed && <Check size={11} />}</button></td>
      <td><button className="rb-title" onClick={e => { e.stopPropagation(); open(i); }}>{v.title}</button><small className="rb-sub">{v.sub}</small>{v.extra}</td>
      <td><span className="rb-person"><span className={`rb-avatar ${i.kind === 'programme' ? 'is-programme' : ''}`}>{v.placeInitials}</span><span>{i.kind === 'action' ? <button className="rb-link" onClick={e => { e.stopPropagation(); props.openClient(i.a.clientId); }}>{v.place}</button> : <strong>{v.place}</strong>}<small>{v.placeSub}</small></span></span></td>
      <td><span className="rb-person"><span className={`rb-avatar ${v.owner === viewer ? 'is-me' : ''}`}>{initials(v.owner)}</span><span><strong>{v.owner === viewer ? 'You' : v.owner || 'Unassigned'}</strong><small>{v.role}</small></span></span></td>
      <td><span className={`rb-due ${v.late ? 'is-late' : ''}`}><CalendarDays size={13} /><span>{fullDate(i.due)}{v.rel && <small>({v.rel})</small>}</span></span></td>
      <td><span className={`rb-pill status-${i.bucket}`}>{STATUS_LABEL[i.bucket]}</span></td>
      <td>{i.kind === 'programme' ? <span className="rb-pill pill-programme">Programme ops</span> : <span className={`rb-pill pri-${priorityOf(i.a).toLowerCase()}`}>{priorityOf(i.a)}</span>}</td>
      <td><ChevronRight size={15} className="rb-chev" /></td>
    </tr>; })}</tbody>
  </table>{!listRows.length && <Empty title="No matching actions">Try another date range, client or search.</Empty>}</div>;

  const review = <div className="rb-review">
    <section className="rb-requests" aria-label="Deadline change requests">
      <header className="rb-review-head"><h2>Deadline change requests<span>{requests.length}</span></h2><p>Owners ask for a new date instead of snoozing. Approving updates the deadline and records who decided.</p></header>
      {requests.length ? <ul>{requests.map(a => { const r = a.deadlineRequest!; return <li key={a.id}>
        <div><button className="rb-title" onClick={() => setOpenId(a.id)}>{a.title}</button><small className="rb-sub">{clientById(a.clientId).name} · {r.by} · {a.due ? fullDate(a.due) : 'No date'} → <strong>{fullDate(r.to)}</strong> · “{r.reason}”</small></div>
        <div className="drawer-inline"><button className="button button-small button-primary" onClick={() => { decideDeadline(a, true, viewer, props.updateAction); props.notify('Approved. The deadline is updated.'); }}><Check size={13} />Approve</button><button className="button button-small button-outline" onClick={() => { decideDeadline(a, false, viewer, props.updateAction); props.notify('Declined. The original deadline stands.'); }}>Decline</button></div>
      </li>; })}</ul> : <p className="rb-empty">No requests waiting.</p>}
    </section>
    <ReviewQueue items={reviewItems} actions={props.actions} resolve={resolve} resolved={resolved} />
  </div>;

  return <div className="view rb-view">
    <header className="rb-head">
      <div>
        <p className="rb-eyebrow">Client intelligence</p>
        <h1>Action Hub</h1>
        <p className="rb-lede">Track, manage and stay on top of every action across your clients, team and client contacts.</p>
      </div>
      <SyncPill />
    </header>

    <section className="rb-kpis" aria-label="Action summary">{BUCKETS.map(b => { const Icon = b.icon; return <button key={b.id} className={`rb-kpi tone-${b.id} ${bucket === b.id && panel === 'actions' ? 'selected' : ''}`} aria-pressed={bucket === b.id} onClick={() => { setPanel('actions'); setBucket(bucket === b.id ? 'all' : b.id); }}>
      <span className="rb-kpi-icon"><Icon size={20} /></span>
      <span className="rb-kpi-text"><span>{b.kpi}</span><strong>{String(count(b.id)).padStart(2, '0')}</strong><small>{b.detail}</small></span>
      <ChevronRight size={16} className="rb-kpi-chev" />
    </button>; })}</section>

    <div className="rb-bar">
      <div className="rb-filters" role="group" aria-label="Show">
        {([['all', 'All', total], ...BUCKETS.map(b => [b.id, b.label, count(b.id)])] as [Bucket | 'all', string, number][]).map(([id, label, n]) => <button key={id} className={panel === 'actions' && bucket === id ? 'selected' : ''} aria-pressed={panel === 'actions' && bucket === id} onClick={() => { setPanel('actions'); setBucket(id); }}>{label}<span>{n}</span></button>)}
        {admin && <button className={`rb-review-pill ${panel === 'review' ? 'selected' : ''}`} aria-pressed={panel === 'review'} onClick={() => setPanel(panel === 'review' ? 'actions' : 'review')}><Inbox size={13} />Needs review<span>{reviewCount}</span></button>}
      </div>
      {panel === 'actions' && <div className="rb-tools">
        <ThemedSelect aria-label="Due" value={range} onChange={v => setRange(v as Range)}>{RANGES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</ThemedSelect>
        <SearchField label="Search action items" placeholder="Search action items…" value={query} onChange={setQuery} />
        <ThemedSelect aria-label="Client" value={client} onChange={setClient}><option value="all">All clients</option>{CLIENTS.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</ThemedSelect>
        <div className="rb-layout" role="group" aria-label="Layout">
          <button className={layout === 'board' ? 'selected' : ''} aria-pressed={layout === 'board'} onClick={() => setLayout('board')}><LayoutGrid size={13} />Board</button>
          <button className={layout === 'list' ? 'selected' : ''} aria-pressed={layout === 'list'} onClick={() => setLayout('list')}><List size={13} />List</button>
        </div>
        <button className="button button-small button-primary rb-add" onClick={() => setAdding(true)}><Plus size={13} />Add action</button>
      </div>}
    </div>

    {panel === 'review' && admin ? review : layout === 'board' ? board : list}

    {selected && <ActionDrawer {...props} rows={[]} viewer={viewer} action={selected} close={() => setOpenId(null)} requestDone={setDoneFor} requestVerify={setVerifyFor} deadlineRequests />}
    {task && <Dialog title={task.title} subtitle="Programme ops" onClose={() => setOpenTask(null)}><div className="form-stack">
      <div className="drawer-badges"><Badge tone={task.status === 'Done' ? 'green' : 'neutral'} dot={false}>{task.status}</Badge><Badge tone="neutral" dot={false}>{task.programme}</Badge>{task.recurring && <Badge tone="neutral" dot={false}>{task.recurring}</Badge>}</div>
      <p className="body-copy">{task.owner} · due {fullDate(task.due)}. Accelerator upkeep is internal work: it isn't counted as any client's open action{task.recurring ? ', and recurring tasks are never shown as overdue' : ''}.</p>
      <button className="button button-primary" onClick={() => { toggleTask(task.id); setOpenTask(null); }}>{task.status === 'Done' ? <><RotateCcw size={14} />Reopen</> : <><Check size={14} />Mark done</>}</button>
    </div></Dialog>}
    {doneFor && <DoneDialog action={doneFor} viewer={viewer} updateAction={props.updateAction} notify={props.notify} close={() => setDoneFor(null)} />}
    {verifyFor && <VerifyDialog action={verifyFor} viewer={viewer} updateAction={props.updateAction} notify={props.notify} close={() => setVerifyFor(null)} />}
    {adding && <AddActionDialog viewer={viewer} addAction={props.addAction} notify={props.notify} close={() => setAdding(false)} />}
  </div>;
}
