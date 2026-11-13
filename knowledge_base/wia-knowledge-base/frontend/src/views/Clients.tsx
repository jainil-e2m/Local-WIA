import { ThemedSelect } from '../components/ThemedSelect';
import './Portfolio.css';
import './ClientPortfolio.css';
import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { ArrowLeft, ArrowRight, Check, ChevronRight, ImageOff, Info, LayoutGrid, List, MapPin, MoreHorizontal, PencilLine, Pin, PinOff, Plus, UserRound } from 'lucide-react';
import ClientDetailsEditor from '../components/ClientDetailsEditor';
import { CALLS, CLIENTS, DEMO_DATE, TEAM, VIEWERS, dateLabel, isOutstanding, isOverdue, timeLabel } from '../data';
import { ENGAGEMENT_TYPES, LIFECYCLES, ownerText, recordFor } from '../records';
import { Dialog, Empty } from '../components/UI';
import type { Client, WorkspaceProps } from '../types';
import { CategoryChip, categoryFor } from './Health';
import type { Category } from '../health';
import { LOGOS } from '../logos';
import { editOf, saveEdit } from '../sharedEdits';

const nextCall = (id: string) => CALLS.filter(c => c.clientId === id && c.date >= DEMO_DATE).sort((a, b) => `${a.date}${a.time}`.localeCompare(`${b.date}${b.time}`))[0];

export function LifecycleChip({ id }: { id: string }) {
  const r = recordFor(id);
  return <span className={`lifecycle-chip lifecycle-${r.lifecycle.toLowerCase()}`}>{r.lifecycle}{r.onboarding ? ` · ${r.onboarding.phase}` : ''}</span>;
}

export function EngagementChips({ id }: { id: string }) {
  return <span className="engagement-chips">{recordFor(id).engagements.map(e => <span className="service-label" key={e.type}>{e.type}</span>)}</span>;
}

export function HealthComingSoon({ id }: { id: string }) {
  // Stage 3 is built in this mockup, so the badge shows the Health category (it read "Coming soon" before, per P1).
  return <CategoryChip id={id} />;
}

const ENGAGEMENT_TONE: Record<string, string> = { 'Elevate': 'blue', 'LeadLock': 'violet', 'Google Search Accelerator': 'green', 'Meta Ads Accelerator': 'sky' };
const HEALTH: Category[] = ['Needs attention', 'Watch', 'Settling in', 'Steady', 'Unassessed'];

// Archive is shared (the client's shared edit, sharedEdits.ts): it hides the client from everyone's portfolio
// list. It doesn't pause the client's syncing; that is the client's status in Connections. Pins are each
// person's own shortcut, so they stay in this browser.
const PINNED_KEY = 'wia-mvp-pinned-clients';
const archivedIds = () => CLIENTS.filter(c => editOf('client', c.id)?.data.archived === true).map(c => c.id);
function loadIds(key: string): string[] {
  try { const ids = JSON.parse(localStorage.getItem(key) || '[]'); return Array.isArray(ids) ? ids : []; } catch { return []; }
}
function saveIds(key: string, ids: string[]) {
  try { localStorage.setItem(key, JSON.stringify(ids)); } catch { /* storage blocked: keep it for this visit */ }
}

/** Background and the size chosen in the client editor, for the banner and the list thumbnail. */
const logoStyle = (id: string): CSSProperties | undefined => { const logo = LOGOS[id]; return logo ? { background: logo.tint, ['--logo-user-scale' as string]: logo.userScale ?? 1 } as CSSProperties : undefined; };

/** Logo banner: the extracted logo on a tint of its own colour, or initials when no logo was found. */
function LogoBanner({ client }: { client: Client }) {
  const logo = LOGOS[client.id];
  return <div className={`cp-banner ${logo ? '' : 'is-fallback'}`} style={logoStyle(client.id)} title={logo ? `Logo from ${logo.source}: ${logo.file} (${logo.source === 'Uploaded in the KB' ? 'uploaded' : 'extracted'} ${dateLabel(logo.extracted)})` : 'No logo found yet in Drive or email signatures'}>
    {logo ? logo.mark : <span className="cp-pending"><ImageOff size={12} />Logo pending</span>}
  </div>;
}

function CardMenu({ client, props, archived, pinned, toggleArchive, togglePin, edit }: { client: Client; props: WorkspaceProps; archived: boolean; pinned: boolean; toggleArchive: (c: Client) => void; togglePin: (c: Client) => void; edit: (c: Client) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const away = (e: PointerEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('pointerdown', away); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('pointerdown', away); document.removeEventListener('keydown', esc); };
  }, [open]);
  return <div className="cp-menu" ref={ref}>
    <button className="icon-button" aria-label={`More for ${client.name}`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(v => !v)}><MoreHorizontal size={17} /></button>
    {open && <div className="cp-menu-list" role="menu">
      <button role="menuitem" onClick={() => props.openClient(client.id)}>Open client record</button>
      <button role="menuitem" className="mvp-menu-pin" onClick={() => { setOpen(false); edit(client); }}><PencilLine size={13} />Edit client details</button>
      {!archived && <button role="menuitem" className="mvp-menu-pin" onClick={() => { setOpen(false); togglePin(client); }}>{pinned ? <PinOff size={13} /> : <Pin size={13} />}{pinned ? 'Unpin' : 'Pin to top'}</button>}
      <button role="menuitem" className={archived ? '' : 'mvp-menu-archive'} onClick={() => { setOpen(false); toggleArchive(client); }}>{archived ? 'Restore from archive' : 'Mark as archived'}</button>
    </div>}
  </div>;
}

export default function Clients(props: WorkspaceProps) {
  const role = VIEWERS.find(v => v.name === props.viewer)!;
  const [scope, setScope] = useState<string>(role.defaultScope);
  const [engagement, setEngagement] = useState('all');
  const [lifecycle, setLifecycle] = useState('all');
  const [owner, setOwner] = useState('all');
  const [health, setHealth] = useState('all');
  const [layout, setLayout] = useState('grid');
  const [adding, setAdding] = useState(false);
  const [archived, setArchived] = useState(archivedIds);
  const [pinned, setPinned] = useState(() => loadIds(PINNED_KEY));
  const [editing, setEditing] = useState<Client | null>(null);
  useEffect(() => { setScope(role.defaultScope); setOwner('all'); }, [props.viewer, role.defaultScope]);

  const counts = (c: Client) => { const open = props.actions.filter(a => a.clientId === c.id && isOutstanding(a)); return { open: open.length, overdue: open.filter(isOverdue).length }; };
  const live = CLIENTS.filter(c => !archived.includes(c.id));
  const archivedClients = CLIENTS.filter(c => archived.includes(c.id));
  const mine = live.filter(c => recordFor(c.id).owner === props.viewer);
  const base = scope === 'mine' ? mine : scope === 'archived' ? archivedClients : live;
  const isPinned = (id: string) => pinned.includes(id) && !archived.includes(id);
  const toggleArchive = (c: Client) => {
    const was = archived.includes(c.id);
    saveEdit('client', c.id, { archived: was ? null : true }, props.viewer)
      .then(() => props.notify(was ? `${c.name} restored to the portfolio for everyone.` : `${c.name} archived for everyone. Find it under Archived.`))
      .catch((error: Error) => props.notify(error.message))
      .finally(() => setArchived(archivedIds()));
  };
  const togglePin = (c: Client) => {
    const was = pinned.includes(c.id);
    const next = was ? pinned.filter(id => id !== c.id) : [c.id, ...pinned];
    saveIds(PINNED_KEY, next); setPinned(next);
    props.notify(was ? `${c.name} unpinned.` : `${c.name} pinned to the top.`);
  };
  // Pinned first (most recently pinned on top), then most overdue, then A to Z, so the clients needing care lead the grid.
  const filtered = base.filter(c => {
    const r = recordFor(c.id);
    return (engagement === 'all' || r.engagements.some(e => e.type === engagement)) && (lifecycle === 'all' || r.lifecycle === lifecycle) && (owner === 'all' || r.owner === owner) && (health === 'all' || categoryFor(c.id).category === health);
  }).sort((a, b) => (pinned.includes(a.id) && pinned.includes(b.id) ? pinned.indexOf(a.id) - pinned.indexOf(b.id) : Number(pinned.includes(b.id)) - Number(pinned.includes(a.id))) || counts(b).overdue - counts(a).overdue || a.name.localeCompare(b.name));

  const card = (client: Client) => {
    const r = recordFor(client.id); const n = counts(client);
    return <article className={`cp-card ${archived.includes(client.id) ? 'is-archived' : ''}`} key={client.id}>
      <LogoBanner client={client} />
      <span className="cp-avatar" aria-hidden="true">{client.initials}</span>
      {isPinned(client.id) && <span className="mvp-pin-badge" title="Pinned to top" aria-label="Pinned"><Pin size={13} /></span>}
      <CardMenu client={client} props={props} archived={archived.includes(client.id)} pinned={pinned.includes(client.id)} toggleArchive={toggleArchive} togglePin={togglePin} edit={setEditing} />
      <div className="cp-body">
        <a className="cp-name" href={`#clients/${client.id}/now`}>{client.name}</a>
        <p className="cp-place"><MapPin size={12} />{client.location}</p>
        <div className="cp-chips">{r.engagements.map(e => <span key={e.type} className={`cp-chip tone-${ENGAGEMENT_TONE[e.type] || 'blue'}`}>{e.type}</span>)}{r.lifecycle !== 'Active' && <span className="cp-chip tone-lifecycle">{r.lifecycle}</span>}</div>
        <p className="cp-owner"><UserRound size={13} />Owner: <strong>{r.owner}</strong></p>
        <div className="cp-stats">
          <div><strong>{r.engagements.length}</strong><span>{r.engagements.length === 1 ? 'Engagement' : 'Engagements'}</span></div>
          <div><strong>{n.open}</strong><span>Open actions</span></div>
          <div className={n.overdue ? 'is-late' : ''}><strong>{n.overdue}</strong><span>Overdue</span></div>
        </div>
        <div className="cp-foot"><span /><button className="icon-button" aria-label={`Open ${client.name}`} onClick={() => props.openClient(client.id)}><ChevronRight size={16} /></button></div>
      </div>
    </article>;
  };

  const list = <div className="cp-table-wrap"><table className="cp-table">
    <thead><tr><th>Client</th><th>Services</th><th>Owner</th><th>Engagements</th><th>Open actions</th><th>Overdue</th><th>Next call</th><th><span className="sr-only">Open</span></th></tr></thead>
    <tbody>{filtered.map(client => { const r = recordFor(client.id); const n = counts(client); const call = nextCall(client.id); const logo = LOGOS[client.id]; return <tr key={client.id} onClick={() => props.openClient(client.id)}>
      <td><span className="cp-row-client"><span className="cp-thumb" style={logoStyle(client.id)}>{logo ? logo.mark : client.initials}</span><span><strong>{client.name}{isPinned(client.id) && <span className="mvp-pin-inline" title="Pinned to top"><Pin size={12} /></span>}</strong><small>{client.location}</small></span></span></td>
      <td><div className="cp-chips">{r.engagements.map(e => <span key={e.type} className={`cp-chip tone-${ENGAGEMENT_TONE[e.type] || 'blue'}`}>{e.type}</span>)}</div></td>
      <td>{ownerText(r)}</td><td>{r.engagements.length}</td><td>{n.open}</td><td className={n.overdue ? 'is-late' : ''}>{n.overdue}</td>
      <td>{call ? `${dateLabel(call.date)} · ${timeLabel(call.time)}` : <span className="muted">None scheduled</span>}</td>
      <td><ChevronRight size={15} className="cp-chev" /></td>
    </tr>; })}</tbody>
  </table></div>;

  return <div className="view cp-view">
    <header className="cp-head">
      <div className="mvp-title-row"><h1>Client Portfolio</h1><span className="scope-info mvp-title-info"><button type="button" className="icon-button" aria-label="About the Client Portfolio" aria-describedby="cp-lede-tip"><Info size={17} /></button><span className="scope-tip" id="cp-lede-tip" role="tooltip">Your client relationships, at a glance. Quickly find, review and explore each client’s details, engagements and current status.</span></span></div>
      <button className="button button-gold cp-add" onClick={() => setAdding(true)}><Plus size={15} />Add client</button>
    </header>

    <div className="cp-toolbar">
      <div className="cp-scope" role="group" aria-label="Portfolio scope">{[['mine', 'My clients', mine.length], ['all', 'All clients', live.length], ['archived', 'Archived', archivedClients.length]].map(([id, label, n]) => <button key={id} className={scope === id ? 'selected' : ''} aria-pressed={scope === id} onClick={() => { setScope(String(id)); setOwner('all'); }}>{label}<span>{n}</span></button>)}</div>
      <div className="cp-filters">
        <ThemedSelect aria-label="Service type" value={engagement} onChange={setEngagement}><option value="all">All service types</option>{ENGAGEMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}</ThemedSelect>
        <ThemedSelect aria-label="Lifecycle stage" value={lifecycle} onChange={setLifecycle}><option value="all">All stages</option>{LIFECYCLES.map(l => <option key={l} value={l}>{l}</option>)}</ThemedSelect>
        {scope === 'all' && <ThemedSelect aria-label="Account owner" value={owner} onChange={setOwner}><option value="all">All owners</option>{[...new Set(CLIENTS.map(c => recordFor(c.id).owner))].map(o => <option key={o} value={o}>{o}</option>)}</ThemedSelect>}
        <ThemedSelect aria-label="Health and sentiment" value={health} onChange={setHealth}><option value="all">Health &amp; sentiment</option>{HEALTH.map(h => <option key={h} value={h}>{h}</option>)}</ThemedSelect>
        <div className="cp-layout" role="group" aria-label="Portfolio layout"><button className={layout === 'grid' ? 'selected' : ''} aria-label="Card view" aria-pressed={layout === 'grid'} onClick={() => setLayout('grid')}><LayoutGrid size={16} /></button><button className={layout === 'list' ? 'selected' : ''} aria-label="List view" aria-pressed={layout === 'list'} onClick={() => setLayout('list')}><List size={17} /></button></div>
      </div>
    </div>

    {!filtered.length ? <Empty title={scope === 'archived' && !archivedClients.length ? 'No archived clients' : scope === 'mine' && !mine.length ? `${props.viewer} doesn't own any clients` : 'No clients match'}>{scope === 'archived' && !archivedClients.length ? 'Archive a client from the ⋯ menu on its card. It moves here and out of My clients and All clients.' : scope === 'mine' ? 'Switch to All clients to see the whole portfolio.' : 'Try another filter.'}</Empty>
      : layout === 'grid' ? <div className="cp-grid">{filtered.map(card)}</div> : list}
    {adding && <AddClient close={() => setAdding(false)} notify={props.notify} />}
    {editing && <ClientDetailsEditor client={editing} viewer={props.viewer} onClose={() => setEditing(null)} notify={props.notify} />}
  </div>;
}

function AddClient({ close, notify }: { close: () => void; notify: (m: string) => void }) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [types, setTypes] = useState<string[]>(['Elevate']);
  const [owner, setOwner] = useState(TEAM[0]);
  const [contact, setContact] = useState('');
  const [email, setEmail] = useState('');
  const slug = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'new-client';
  const domain = email.split('@')[1] || 'their domain';
  const suggestions = [
    { source: 'Slack', match: `#client-${slug}`, why: 'Channel name matches' },
    { source: 'Drive', match: `${name || 'New client'} / Client folder`, why: 'Folder created from the onboarding template' },
    { source: 'ClickUp', match: `${name || 'New client'} · Onboarding`, why: 'List created from the onboarding template' },
    { source: 'Gmail', match: `Messages with ${domain}`, why: 'Contact email domain' },
    { source: 'Calendar', match: `Events with ${email || 'contact email'}`, why: 'Contact email' },
    ...(types.includes('LeadLock') ? [{ source: 'LeadLock', match: `${name || 'New client'} (location)`, why: 'Location name matches' }] : []),
  ];
  const [confirmed, setConfirmed] = useState<Set<string>>(new Set(['Slack', 'Drive', 'ClickUp', 'Gmail', 'Calendar', 'LeadLock']));
  const steps = ['Business', 'Engagements', 'Contacts', 'Link sources', 'Start backfill'];
  const can = step !== 0 || name.trim().length > 1;
  return <Dialog title="Add a client" subtitle={`Step ${step + 1} of ${steps.length} · ${steps[step]}`} className="add-client-dialog" onClose={close}>
    <ol className="wizard-steps">{steps.map((s, i) => <li key={s} className={i === step ? 'current' : i < step ? 'done' : ''}>{i < step ? <Check size={11} /> : i + 1}<span>{s}</span></li>)}</ol>
    <div className="form-stack">
      {step === 0 && <><label>Business name<input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Cedar Hollow Farm" autoFocus /></label><label>Also known as (optional)<input placeholder="Former or alternative names" /></label><div className="form-two-col"><label>Category<input placeholder="Wedding venue" /></label><label>Location<input placeholder="City, State" /></label></div></>}
      {step === 1 && <><p className="hint">One business can have several engagements. Each keeps its own start date and goals.</p><div className="check-list">{ENGAGEMENT_TYPES.map(t => <label key={t} className="check-row"><input type="checkbox" checked={types.includes(t)} onChange={e => setTypes(x => e.target.checked ? [...x, t] : x.filter(y => y !== t))} />{t}</label>)}</div><label>Account owner<ThemedSelect aria-label="Account owner" value={owner} onChange={setOwner}>{TEAM.map(p => <option key={p} value={p}>{p}</option>)}</ThemedSelect></label></>}
      {step === 2 && <><p className="hint">Contact emails are how Gmail, Calendar and Fathom are matched to this client.</p><div className="form-two-col"><label>Primary contact<input value={contact} onChange={e => setContact(e.target.value)} placeholder="Name" /></label><label>Email<input value={email} onChange={e => setEmail(e.target.value)} placeholder="name@business.com" /></label></div></>}
      {step === 3 && <><p className="hint">The KB suggests matches. A person confirms each one; nothing is linked automatically.</p>{suggestions.map(s => <label className="check-row suggestion-row" key={s.source}><input type="checkbox" checked={confirmed.has(s.source)} onChange={e => setConfirmed(x => { const n = new Set(x); if (e.target.checked) n.add(s.source); else n.delete(s.source); return n; })} /><strong>{s.source}</strong><span>{s.match}</span><small className="hint">{s.why}</small></label>)}</>}
      {step === 4 && <><p className="body-copy"><strong>{name || 'New client'}</strong> · {types.join(' + ') || 'No engagement'} · owner {owner}</p><p className="hint">{suggestions.filter(s => confirmed.has(s.source)).length} sources will be backfilled from their earliest available history. Progress shows on the client’s Accounts & sources tab. Until then, sections show “processing”, never zero.</p></>}
    </div>
    <div className="wizard-nav">{step > 0 ? <button className="button button-outline" onClick={() => setStep(step - 1)}><ArrowLeft size={14} />Back</button> : <span />}{step < steps.length - 1 ? <button className="button button-primary" disabled={!can} onClick={() => setStep(step + 1)}>Next<ArrowRight size={14} /></button> : <button className="button button-gold" onClick={() => { close(); notify(`Preview only: ${name || 'the client'} was not added. In the real app backfill would start now.`); }}><Check size={14} />Create & start backfill</button>}</div>
  </Dialog>;
}
