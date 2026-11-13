import { useMemo, useRef, useState, type ReactNode } from 'react';
import { Building2, CalendarDays, ChevronDown, Copy, Trash2, Inbox, Info, SlidersHorizontal, User } from 'lucide-react';
import { CLIENTS, DEMO_DATE, PROGRAMME_TASKS, REVIEW_ITEMS, TEAM, VIEWERS, addDays, clientById, dateLabel, daysBetween, isOutstanding, sourceById } from '../data';
import { Avatar, Badge, Dialog, Empty, SearchField, SourceLink } from '../components/UI';
import { SyncPill } from './ActionsTeams';
import { ReviewQueue, isAdmin } from './Actions';
import type { Action, ReviewItem, WorkspaceProps } from '../types';
import './ActionHubV2.css';
import { me } from '../auth';

/*
 * Action Hub v2 (Solution Architecture §9.1): a reading list of everything outstanding between WIA and its clients,
 * both ways, each item showing where it was said. Not a task manager: ClickUp tasks change in ClickUp; a found item
 * (said in Slack, email or a call, with no ClickUp task) only takes Done or Not an action.
 * Layout from the action-hub.html reference: browse by client, person or due date; a rail of groups; a pane with
 * We owe / Client owes / Unconfirmed. Quotes show only in the detail modal. Unconfirmed items (implied, or no activity for 30 days) are never counted.
 */

type Browse = 'client' | 'person' | 'due';
type Tab = 'we' | 'they' | 'unc';
type Status = 'all' | 'overdue' | 'notCu' | 'differs' | 'reported';
type Origin = 'all' | 'ClickUp' | 'Slack' | 'Gmail' | 'Meeting';
type DateMode = 'any' | 'due' | 'said';

interface Row {
  id: string; title: string; clientId?: string; programme?: string; tab: Tab; owner: string; due: string; origin: string;
  said: string; quote?: string; speaker?: string; sourceId?: string; clickupUrl?: string; overdue: boolean; notInClickUp: boolean;
  differs?: string; reported?: string; reason?: string; history?: { date: string; text: string }[]; action?: Action;
}
interface Group { key: string; name: string; sub: string; avatar: ReactNode }

const BROWSE_KEY = 'wia-action-hub-v2-browse';
const STALE_DAYS = 30;
const WINDOWS: [string, string, string][] = [
  ['overdue', 'Overdue', 'A stated date has passed'], ['week', 'Due this week', 'Due in the next 7 days'],
  ['later', 'Later', 'Due after this week'], ['none', 'No date', 'No source states a date'],
];
const STATUSES: [Status, string][] = [['all', 'Everything'], ['overdue', 'Overdue'], ['notCu', 'Not in ClickUp'], ['differs', 'Date differs'], ['reported', 'Reported done']];
const ORIGINS: [Origin, string][] = [['all', 'All sources'], ['ClickUp', 'ClickUp'], ['Slack', 'Slack'], ['Gmail', 'Gmail'], ['Meeting', 'Meeting']];
const DATES: [DateMode, string][] = [['any', 'Any time'], ['due', 'Due date'], ['said', 'Said / activity']];
const TABS: [Tab, string][] = [['we', 'We owe'], ['they', 'Client owes'], ['unc', 'Unconfirmed']];

const initials = (name: string) => name.split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase();
const ago = (date: string) => { const d = daysBetween(date); return d <= 0 ? 'today' : d === 1 ? 'yesterday' : `${d} days ago`; };
// Just the date: overdue shows as the red colour here and the Overdue pill below.
const dueText = (r: Row) => r.due ? dateLabel(r.due) : 'No date';
const chipClass = (origin: string) => `source-link source-${origin === 'Meeting' ? 'zoom' : origin.toLowerCase()}`;
const windowOf = (r: Row) => !r.due ? 'none' : r.overdue ? 'overdue' : r.due <= addDays(DEMO_DATE, 6) ? 'week' : 'later';
// "Overdue" needs a stated date; a date-only deadline is overdue from the next day.
const isLate = (due: string) => !!due && due < DEMO_DATE;
const matches = (r: Row, s: Status) => s === 'all' || (s === 'overdue' ? r.overdue : s === 'notCu' ? r.notInClickUp : s === 'differs' ? !!r.differs : !!r.reported);

function readBrowse(): Browse {
  try { const v = localStorage.getItem(BROWSE_KEY); return v === 'person' || v === 'due' ? v : 'client'; } catch { return 'client'; }
}

/** Every outstanding item as one row: client actions, unconfirmed finds, and programme operations. */
function buildRows(actions: Action[]): Row[] {
  const rows: Row[] = [];
  for (const a of actions) {
    if (!isOutstanding(a) || a.kind === 'programme') continue;
    const source = sourceById(a.sourceId);
    const notInClickUp = a.origin !== 'ClickUp' && !a.clickupUrl;
    // An open ClickUp task is always Open (§8.3); only a found item goes Unconfirmed after 30 quiet days.
    const quiet = notInClickUp && a.lastActivity ? daysBetween(a.lastActivity) : 0;
    rows.push({
      id: a.id, title: a.title, clientId: a.clientId, tab: quiet > STALE_DAYS ? 'unc' : a.side === 'WIA' ? 'we' : 'they',
      owner: a.owner, due: a.due, origin: a.origin || source?.kind || 'Manual', said: source?.date || a.assignedOn || a.lastActivity || '',
      quote: a.quote, speaker: source?.author, sourceId: a.sourceId, clickupUrl: a.clickupUrl, overdue: isLate(a.due),
      notInClickUp, differs: a.conflict, reported: a.reportedDone,
      reason: quiet > STALE_DAYS ? `No activity for ${quiet} days` : undefined, history: a.history, action: a,
    });
  }
  for (const r of REVIEW_ITEMS) {
    if (!r.clientId || (r.reason !== 'Possibly stale' && r.reason !== 'Owner unclear')) continue;
    rows.push({
      id: r.id, title: r.title, clientId: r.clientId, tab: 'unc', owner: r.reason === 'Owner unclear' ? '' : r.author, due: '',
      origin: r.origin, said: r.date, quote: r.quote, speaker: r.author, overdue: false, notInClickUp: r.origin !== 'ClickUp',
      reason: r.reason === 'Possibly stale' ? 'No activity for 30+ days' : 'Implied: nobody took it on',
    });
  }
  for (const p of PROGRAMME_TASKS) {
    if (p.status !== 'Open') continue;
    rows.push({ id: p.id, title: p.title, programme: p.programme, tab: 'we', owner: p.owner, due: p.due, origin: 'ClickUp', said: '', overdue: isLate(p.due), notInClickUp: false, history: p.history });
  }
  return rows;
}

export default function ActionHubV2(props: WorkspaceProps & { addAction: (action: Action) => void }) {
  const [browse, setBrowseState] = useState<Browse>(readBrowse);
  const notesRef = useRef<HTMLTextAreaElement>(null);
  // Admins approve the KB's proposed actions before anyone sees them here. One approved already is an action (same id).
  const admin = isAdmin(props.viewer);
  const [reviewing, setReviewing] = useState(() => window.location.hash.endsWith('/review'));
  const [proposals, setProposals] = useState<ReviewItem[]>(() => REVIEW_ITEMS.filter(i => i.reason === 'AI proposal' && !props.actions.some(a => a.id === i.id)));
  const [resolved, setResolved] = useState<{ title: string; outcome: string }[]>([]);
  const resolve = (item: ReviewItem, outcome: string, action?: Action) => {
    if (action) props.addAction(action);
    setProposals(list => list.filter(i => i.id !== item.id));
    setResolved(r => [{ title: item.title, outcome }, ...r]);
    props.notify(action ? 'Approved. It is now in the Action Hub.' : 'Dismissed. It won’t reach the Action Hub.');
  };
  const [selected, setSelected] = useState('all');
  const [tab, setTab] = useState<Tab>('we');
  const [status, setStatus] = useState<Status>('all');
  const [origin, setOrigin] = useState<Origin>('all');
  const [dateMode, setDateMode] = useState<DateMode>('any');
  const [showProgramme, setShowProgramme] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [openId, setOpenId] = useState<string | null>(null);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [picked, setPicked] = useState<string[]>([]);

  const rows = useMemo(() => buildRows(props.actions), [props.actions]);
  const setBrowse = (b: Browse) => { setBrowseState(b); setSelected('all'); try { localStorage.setItem(BROWSE_KEY, b); } catch { /* the choice just isn't remembered */ } };

  const keyOf = (r: Row) => browse === 'client' ? (r.programme ? `p:${r.programme}` : r.clientId!) : browse === 'person' ? (r.owner || '—') : windowOf(r);
  const groupOf = (key: string): Group => {
    if (browse === 'due') { const [, name, sub] = WINDOWS.find(w => w[0] === key)!; return { key, name, sub, avatar: <span className="ah2-avatar is-due"><CalendarDays size={14} /></span> }; }
    if (browse === 'person') {
      const staff = TEAM.includes(key);
      return key === '—' ? { key, name: 'No owner stated', sub: 'Shown only when a source names one', avatar: <span className="ah2-avatar">—</span> }
        : { key, name: key, sub: staff ? VIEWERS.find(v => v.name === key)?.role || 'WIA team' : 'Client contact', avatar: <span className={`ah2-avatar ${staff ? '' : 'is-client'}`}>{initials(key)}</span> };
    }
    if (key.startsWith('p:')) return { key, name: key.slice(2), sub: 'Programme operations', avatar: <span className="ah2-avatar is-programme">{initials(key.slice(2))}</span> };
    const c = clientById(key);
    return { key, name: c.name, sub: c.service, avatar: <Avatar client={c} small /> };
  };
  const nameOf = (r: Row) => r.programme || clientById(r.clientId!).name;

  const q = query.trim().toLowerCase();
  const visible = rows.filter(r => (showProgramme || !r.programme) && (origin === 'all' || r.origin === origin)
    && (!q || [r.title, r.quote, r.owner, nameOf(r)].some(t => t?.toLowerCase().includes(q))));
  const keys = [...new Set(visible.map(keyOf))];
  const order = browse === 'due' ? WINDOWS.map(w => w[0]) : browse === 'client' ? [...CLIENTS.map(c => c.id), ...keys.filter(k => k.startsWith('p:'))] : keys.sort((a, b) => a === '—' ? 1 : b === '—' ? -1 : a.localeCompare(b));
  const groups = order.filter(k => keys.includes(k)).map(groupOf);
  const scopeKey = groups.some(g => g.key === selected) ? selected : 'all';
  const scoped = visible.filter(r => scopeKey === 'all' || keyOf(r) === scopeKey);
  // Counters, rail figures and tab badges read the same rows; unconfirmed items are never counted.
  const counted = scoped.filter(r => r.tab !== 'unc');
  const counters = { we: counted.filter(r => r.tab === 'we').length, they: counted.filter(r => r.tab === 'they').length, overdue: counted.filter(r => r.overdue).length, notCu: counted.filter(r => r.notInClickUp).length };
  const tabCount = (t: Tab) => scoped.filter(r => r.tab === t && matches(r, status)).length;
  const list = scoped.filter(r => r.tab === tab && matches(r, status)).sort((a, b) =>
    dateMode === 'said' ? b.said.localeCompare(a.said)
      : dateMode === 'due' ? (a.due || '9999').localeCompare(b.due || '9999')
        : Number(b.overdue) - Number(a.overdue) || (a.due || '9999').localeCompare(b.due || '9999') || a.title.localeCompare(b.title));
  const scope = scopeKey === 'all' ? null : groupOf(scopeKey);
  const allLabel = browse === 'client' ? 'All clients' : browse === 'person' ? 'Everyone' : 'All dates';
  const activeFilters = [status !== 'all', origin !== 'all', dateMode !== 'any', showProgramme].filter(Boolean).length;
  const open = rows.find(r => r.id === openId);
  // Kept in the order ticked; a removed item drops out on its own.
  const pickedRows = picked.map(id => rows.find(r => r.id === id)).filter((r): r is Row => !!r);

  const pick = (key: string) => {
    setSelected(key);
    const inScope = visible.filter(r => key === 'all' || keyOf(r) === key);
    if (!inScope.some(r => r.tab === tab)) setTab(TABS.map(t => t[0]).find(t => inScope.some(r => r.tab === t)) || 'we');
  };
  const counter = (id: 'we' | 'they' | 'overdue' | 'notCu', label: string) => {
    const on = id === 'we' || id === 'they' ? tab === id && status === 'all' : status === id;
    return <button className={`ah2-counter ${on ? 'selected' : ''} ${id === 'overdue' && counters.overdue ? 'is-hot' : ''}`} aria-pressed={on}
      onClick={() => { if (id === 'we' || id === 'they') { setTab(id); setStatus('all'); } else { setStatus(status === id ? 'all' : id); if (tab === 'unc') setTab('we'); } }}>
      <span>{label}</span><strong>{counters[id]}</strong></button>;
  };
  const decide = (r: Row, notAction: boolean) => {
    const a = r.action!;
    props.updateAction(a.id, {
      status: 'Done', completedOn: DEMO_DATE, completionBasis: notAction ? `Not an action (${me(props.viewer)})` : `Marked done in the Action Hub (${props.viewer})`,
      history: [...(a.history || []), { date: DEMO_DATE, at: new Date().toISOString(), text: notAction ? `Marked not an action by ${me(props.viewer)}.` : `Marked done by ${me(props.viewer)}.` }],
    });
    setOpenId(null);
    props.notify(notAction ? 'Marked as not an action. It has left every list.' : 'Marked done.');
  };
  // No hard delete: the action comes from its source (ClickUp) on every load, so removal is a logged close, like "Not an action".
  const remove = (r: Row) => {
    const a = r.action!;
    props.updateAction(a.id, {
      status: 'Done', completedOn: DEMO_DATE, completionBasis: `Removed by ${me(props.viewer)}`,
      history: [...(a.history || []), { date: DEMO_DATE, at: new Date().toISOString(), text: `Removed from the Action Hub by ${me(props.viewer)}.` }],
    });
    setOpenId(null); setConfirmRemove(false);
    props.notify('Removed. It has left every list.');
  };
  /** Slack-formatted summary on the clipboard; nothing is posted. */
  // One item or many: each item keeps the same Slack text, separated by a blank line.
  const copyForSlack = (items: Row[]) => {
    const text = items.map(r => { const note = r.action?.note?.trim(); return [
      `*${r.title}*`,
      `${nameOf(r)} · ${r.tab === 'they' ? 'Client owes' : r.tab === 'we' ? 'We owe' : 'Unconfirmed'}`,
      `Owner: ${r.owner || 'Not assigned'} · ${r.due ? `Due ${dateLabel(r.due, { day: 'numeric', month: 'short' })}${r.overdue ? ' (overdue)' : ''}` : 'No due date'}`,
      note && `Notes: ${note}`,
      r.quote && `> “${r.quote}” — ${r.speaker || 'Unknown'}${r.said ? `, ${dateLabel(r.said, { day: 'numeric', month: 'short' })}` : ''}`,
      r.clickupUrl && `ClickUp: ${r.clickupUrl}`,
    ].filter(Boolean).join('\n'); }).join('\n\n');
    navigator.clipboard.writeText(text).then(() => props.notify(items.length > 1 ? `Copied ${items.length} items. Paste them into the Slack channel.` : 'Copied. Paste it into the Slack channel.'), () => props.notify('Couldn’t copy: the browser blocked clipboard access.'));
  };
  const seg = <T extends string>(value: T, options: [T, string][], set: (v: T) => void, label: string) =>
    <div className="segmented" role="group" aria-label={label}>{options.map(([id, text]) => <button key={id} className={value === id ? 'selected' : ''} aria-pressed={value === id} onClick={() => set(id)}>{text}</button>)}</div>;

  return <div className="view rb-view ah2-view">
    <header className="rb-head">
      <div>
        <div className="mvp-title-row"><h1>Action Hub v2</h1><span className="scope-info mvp-title-info"><button type="button" className="icon-button" aria-label="About this view" aria-describedby="ah2-tip"><Info size={17} /></button><span className="scope-tip" id="ah2-tip" role="tooltip">A reading list of everything outstanding between WIA and each client, with where it was said. Change owners, dates and status of ClickUp tasks in ClickUp.</span></span></div>      </div>
      <div className="ah2-head-tools">
        {admin && <button className={`ah2-review-btn ${reviewing ? 'selected' : ''}`} aria-pressed={reviewing} title="Proposed actions waiting for an admin" onClick={() => setReviewing(v => !v)}><Inbox size={14} />Needs review<b>{proposals.length}</b></button>}
        <SyncPill />
      </div>
    </header>

    {reviewing && admin ? <div className="ah2-review">
      <button type="button" className="text-button" onClick={() => setReviewing(false)}>← Back to the Action Hub</button>
      <ReviewQueue items={proposals} actions={props.actions} resolve={resolve} resolved={resolved} viewer={props.viewer} />
    </div> : <>

    <div className="ah2-toolbar">
      <div className="ah2-browse" role="group" aria-label="Browse by">
        {([['client', 'Client', Building2], ['person', 'Person', User], ['due', 'Due date', CalendarDays]] as const).map(([id, text, Icon]) =>
          <button key={id} className={browse === id ? 'selected' : ''} aria-pressed={browse === id} onClick={() => setBrowse(id)}><Icon size={14} />{text}</button>)}
      </div>
      <SearchField label="Search outstanding items" placeholder="Search titles, quotes, people, clients…" value={query} onChange={setQuery} />
      <button className={`ah2-filters-btn ${filtersOpen || activeFilters ? 'active' : ''}`} aria-expanded={filtersOpen} onClick={() => setFiltersOpen(v => !v)}>
        <SlidersHorizontal size={14} />Filters{activeFilters > 0 && <b>{activeFilters}</b>}<ChevronDown size={14} className={filtersOpen ? 'is-open' : ''} />
      </button>
    </div>

    {filtersOpen && <div className="ah2-filters">
      <div><span>Status</span>{seg(status, STATUSES, s => { setStatus(s); if (s !== 'all' && tab === 'unc') setTab('we'); }, 'Status')}</div>
      <div><span>Source</span>{seg(origin, ORIGINS, setOrigin, 'Source')}</div>
      <div><span>Date</span>{seg(dateMode, DATES, setDateMode, 'Order by date')}</div>
      <div><span>Programme</span>{seg(showProgramme ? 'shown' : 'hidden', [['hidden', 'Hide programme operations'], ['shown', 'Show programme operations']], v => setShowProgramme(v === 'shown'), 'Programme operations')}</div>
    </div>}

    <div className="ah2-split">
      <aside className="ah2-rail" aria-label={browse === 'client' ? 'Clients' : browse === 'person' ? 'People' : 'Due windows'}>
        <div className="ah2-rail-head"><h2>{browse === 'client' ? 'Clients' : browse === 'person' ? 'People' : 'Due windows'}</h2><span>{groups.length}</span></div>
        <ul>
          {[{ key: 'all', name: allLabel, sub: `${visible.filter(r => r.tab !== 'unc').length} outstanding`, avatar: <span className="ah2-avatar is-all">All</span> }, ...groups].map(g => {
            const own = visible.filter(r => r.tab !== 'unc' && (g.key === 'all' || keyOf(r) === g.key));
            const late = own.filter(r => r.overdue).length;
            return <li key={g.key}><button className={`ah2-group ${scopeKey === g.key ? 'selected' : ''}`} aria-pressed={scopeKey === g.key} onClick={() => pick(g.key)}>
              {g.avatar}
              <span className="ah2-group-copy"><strong>{g.name}</strong><small>{g.sub}</small></span>
              <span className="ah2-group-stats">{late > 0 && <em>{late} overdue</em>}<span className="is-we">{own.filter(r => r.tab === 'we').length} we</span><span className="is-they">{own.filter(r => r.tab === 'they').length} them</span></span>
            </button></li>;
          })}
        </ul>
      </aside>

      <section className="ah2-pane" aria-label="Outstanding items">
        <div className="ah2-pane-head">
          <div className="ah2-identity">
            {scope ? scope.avatar : <span className="ah2-avatar is-all">All</span>}
            <div><h2>{scope ? scope.name : allLabel}</h2><p>{scope ? (browse === 'client' && !scope.key.startsWith('p:') ? `${clientById(scope.key).contact} · ${scope.sub}` : scope.sub) : 'Everything outstanding, both ways'}</p></div>
          </div>
          <div className="ah2-counters" role="group" aria-label="Counters">{counter('we', 'We owe')}{counter('they', 'Client owes')}{counter('overdue', 'Overdue')}{counter('notCu', 'Not in ClickUp')}</div>
        </div>
        <div className="ah2-tabs" role="tablist" aria-label="Items in this scope">
          {TABS.map(([id, text]) => <button key={id} role="tab" aria-selected={tab === id} className={`tab-${id} ${tab === id ? 'selected' : ''}`} onClick={() => setTab(id)}>{text}<b>{tabCount(id)}</b></button>)}
        </div>
        <div className="ah2-body">
          {tab === 'unc' && <p className="ah2-note">Implied items, or items with no activity for 30 days. They aren’t counted until someone confirms them.</p>}
          {pickedRows.length > 0 && <div className="ah2-bulk" role="status"><span>{pickedRows.length} selected</span><button className="text-button" onClick={() => setPicked([])}>Clear</button><button className="button button-primary" onClick={() => copyForSlack(pickedRows)}><Copy size={14} />Copy {pickedRows.length} for Slack</button></div>}
          {list.length ? <div className="ah2-grid">{list.map(r => <div key={r.id} className={`ah2-cell ${picked.includes(r.id) ? 'is-picked' : ''}`}>
            <input type="checkbox" className="ah2-pick" aria-label={`Select “${r.title}” for Slack`} checked={picked.includes(r.id)} onChange={() => setPicked(p => p.includes(r.id) ? p.filter(id => id !== r.id) : [...p, r.id])} />
            <button className={`ah2-card side-${r.tab}`} onClick={() => setOpenId(r.id)}>
            <span className="ah2-card-top"><span className={`ah2-due ${r.overdue ? 'is-hot' : ''}`}>{dueText(r)}</span><span className="ah2-owner">{r.owner || '—'}</span></span>
            {scopeKey === 'all' || browse !== 'client' ? <span className="ah2-client">{nameOf(r)}</span> : null}
            <h3>{r.title}</h3>
            <span className="ah2-meta">
              <span className={chipClass(r.origin)}>{r.origin}{r.said && ` · ${ago(r.said)}`}</span>
              {r.reason && <Badge tone="gold" dot={false}>{r.reason}</Badge>}
              {r.overdue && <Badge tone="rose" dot={false}>Overdue</Badge>}
              {r.notInClickUp && <Badge tone="neutral" dot={false}>Not in ClickUp</Badge>}
              {r.differs && <Badge tone="amber" dot={false}>Date differs</Badge>}
              {r.reported && <Badge tone="green" dot={false}>Reported done</Badge>}
            </span>
          </button></div>)}</div>
            : <Empty title={tab === 'unc' ? 'Nothing unconfirmed here' : tab === 'we' ? 'Nothing we currently owe' : 'Nothing waiting on the client'}>{q || activeFilters ? 'Try a different search or filter.' : 'Nothing is outstanding in this scope.'}</Empty>}
        </div>
      </section>
    </div>
    </>}

    {open && <Dialog title={open.title} subtitle={`${nameOf(open)} · ${open.tab === 'we' ? 'We owe' : open.tab === 'they' ? 'Client owes' : 'Unconfirmed'}`} onClose={() => { setOpenId(null); setConfirmRemove(false); }}
      footer={confirmRemove
        ? <><p className="ah2-confirm" role="alert">Remove this action item? It leaves every list; its history keeps a note.</p><div className="ah2-decide"><button className="button button-outline" onClick={() => setConfirmRemove(false)}>Keep it</button><button className="button ah2-remove-confirm" onClick={() => remove(open)}><Trash2 size={14} />Remove</button></div></>
        : <>{open.action ? <button className="text-button ah2-remove" onClick={() => setConfirmRemove(true)}><Trash2 size={14} />Remove</button> : <span />}
          <div className="ah2-decide"><button className="button button-outline" onClick={() => copyForSlack([open])}><Copy size={14} />Copy for Slack</button>
            {open.action && open.notInClickUp && <><button className="button button-outline" onClick={() => decide(open, true)}>Not an action</button><button className="button button-primary" onClick={() => decide(open, false)}>Done</button></>}</div></>}>
      <section className="action-detail-section">
        {open.clickupUrl && <a className="ah2-clickup" href={open.clickupUrl} target="_blank" rel="noreferrer" aria-label="Open in ClickUp" title="Open in ClickUp (owner, date and status change there)"><img src="/logos/clickup_glass.png" alt="" /></a>}
        <dl className="ah2-facts">
          <div><dt>Direction · owner</dt><dd>{open.tab === 'they' ? 'Client owes' : 'We owe'} · {open.owner || '— (no source names an owner)'}</dd></div>
          <div><dt>Due</dt><dd className={open.overdue ? 'is-hot' : ''}>{open.due ? `${dateLabel(open.due, { day: 'numeric', month: 'long' })}${open.overdue ? ' · overdue' : ''}` : 'No date (no source states one)'}</dd></div>
          <div><dt>Came from</dt><dd className="ah2-came">{open.origin}{open.said && ` · ${dateLabel(open.said, { day: 'numeric', month: 'long' })}`}
            {open.sourceId && <> · <SourceLink id={open.sourceId} onOpen={props.showEvidence} label="Open the source" /></>}</dd></div>
        </dl>
        {open.reason && <p className="hint"><strong>Unconfirmed:</strong> {open.reason}. Not counted until confirmed.</p>}
        {open.differs && <p className="hint"><strong>Date differs:</strong> {open.differs}</p>}
        {open.reported && <p className="hint"><strong>Reported done:</strong> {open.reported}. The ClickUp task is still open.</p>}
      </section>
      {open.quote && <section className="action-detail-section">
        <h3>Where it was said</h3>
        <blockquote className="ah2-said"><q>{open.quote}</q><footer>{open.speaker || 'Unknown speaker'}{open.said && ` · ${dateLabel(open.said, { day: 'numeric', month: 'short', year: 'numeric' })}`}</footer></blockquote>
      </section>}
      <section className="action-detail-section">
        <h3><label htmlFor="ah2-notes">Notes</label></h3>
        {open.action
          ? <><textarea id="ah2-notes" className="ah2-notes" key={open.id} ref={notesRef} defaultValue={open.action.note} rows={4} placeholder="Add a description or notes for the team…" />
              <button type="button" className="button button-small button-outline" onClick={() => {
                const note = (notesRef.current?.value ?? '').trim();
                if (note === (open.action!.note || '')) { props.notify('No changes to save.'); return; }
                props.updateAction(open.id, { note }); props.notify('Notes saved for the team.');
              }}>Save notes</button></>
          : <p className="hint">Notes can be added once this item is confirmed as an action.</p>}
        <p className="hint">Saved for everyone when you press Save notes. Kept in the KB only; not sent to ClickUp.</p>
      </section>
    </Dialog>}
  </div>;
}
