import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { AlertTriangle, ArrowRight, Check, CircleSlash, Link2, Minus, Plus, RefreshCw, Sparkles, Unlink, X } from 'lucide-react';
import { Dialog, SearchField } from './UI';
import { ThemedSelect } from './ThemedSelect';
import LeadLockMapping from './LeadLockMapping';
import './ClientConnections.css';

/*
 * Connections, client by client (5 Nov). One row per client, one column per intake channel, one state per cell;
 * a cell opens a modal with that channel's options for that client. Reads GET /api/v1/connections/clients
 * (backend/services/clients/client_connections.py); every change goes through the S2 mapping commands.
 * With `client` set it shows that one client's five channels (its Accounts & sources tab).
 * Without the local KB API (the static preview build) it renders nothing and reports `onLive(false)`.
 */
type ChannelId = 'leadlock' | 'slack' | 'clickup' | 'drive' | 'contacts';
type CellState = 'linked' | 'paused' | 'suggested' | 'missing' | 'not_applicable' | 'not_connected';
interface Ref { kind: 'scope' | 'location' | 'contact'; id: string }
interface Item { ref: Ref; name: string; parent?: string | null; records?: number; last_synced_at?: string | null; revision: number | null; reason?: string | null; collection?: string | null; display_name?: string | null; origin?: string }
interface Cell { state: CellState; linked: Item[]; suggested: Item[]; not_applicable: string | null }
interface Channel { id: ChannelId; label: string; kind: 'dedicated' | 'shared'; unit: string }
interface ClientRow { slug: string; name: string; status: 'active' | 'inactive'; revision: number; cells: Record<ChannelId, Cell>; needs_attention: boolean }
interface Payload {
  channels: Channel[]; clients: ClientRow[]; options: Record<string, Item[]>; accounts: Record<string, string>;
  unassigned_leadlock: { count: number; by_state: Record<string, number> };
}

const STATE_LABEL: Record<CellState, string> = {
  linked: 'Linked', paused: 'Paused', suggested: 'To confirm', missing: 'Not linked', not_applicable: 'Not used', not_connected: 'Not connected',
};
const plural = (n: number, unit: string) => `${n} ${unit}${n === 1 ? '' : 's'}`;
const fmt = (iso: string) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

async function call<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, body === undefined ? undefined : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = (json as { detail?: { code?: string; message?: string } }).detail;
    throw new Error(detail?.code === 'changed_elsewhere' ? 'Someone changed this meanwhile. The view has been reloaded.' : detail?.message || `HTTP ${response.status}`);
  }
  return json as T;
}

function cellText(cell: Cell, channel: Channel) {
  const n = cell.linked.length;
  switch (cell.state) {
    case 'linked': return plural(n, channel.unit);
    case 'paused': return plural(n, channel.unit);
    case 'suggested': return `${cell.suggested.length} suggested`;
    case 'missing': return 'Nothing linked';
    case 'not_applicable': return 'Not used';
    default: return 'Not connected';
  }
}

function StateMark({ state }: { state: CellState }) {
  const icon = state === 'linked' ? <Check size={11} /> : state === 'suggested' ? <Sparkles size={11} /> : state === 'paused' ? <Minus size={11} /> : state === 'not_applicable' ? <CircleSlash size={11} /> : null;
  return <i className={`cc-mark is-${state}`} aria-hidden="true">{icon}</i>;
}

export default function ClientConnections({ client, notify, onLive, openRequest }: { client?: string; notify: (message: string) => void; onLive?: (live: boolean) => void; openRequest?: { channel: string } | null }) {
  const [data, setData] = useState<Payload | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [filter, setFilter] = useState<'all' | 'attention' | 'active' | 'archived'>('all');
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState<{ slug: string; channel: ChannelId } | null>(null);
  const [reviewing, setReviewing] = useState(false);

  const load = useCallback(() => call<Payload>('/api/v1/connections/clients')
    .then(json => { setData(json); setFailed(null); onLive?.(true); })
    // 404 = no KB API in this build (static preview): the page shows its sample cards instead. Any other failure
    // is the real API being down: say so, and keep the sample cards hidden so they can't pass for real data.
    .catch((error: Error) => { if (/HTTP 404|local_only/.test(error.message)) { setUnavailable(true); onLive?.(false); } else { setFailed(error.message); onLive?.(true); } }), [onLive]);
  useEffect(() => { void load(); }, [load]);
  // Another control on the page (Accounts & sources' "Edit mapping") asks for a channel's modal; a new object per click.
  useEffect(() => { if (client && openRequest) setOpen({ slug: client, channel: openRequest.channel as ChannelId }); }, [client, openRequest]);

  const rows = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    return data.clients.filter(c => (!client || c.slug === client) && (!q || c.name.toLowerCase().includes(q))
      && (filter === 'all' || (filter === 'attention' && c.needs_attention) || (filter === 'active' && c.status === 'active') || (filter === 'archived' && c.status === 'inactive')));
  }, [data, client, query, filter]);

  if (unavailable) return null;
  if (!data && failed) return <section className="cc-panel cc-failed"><AlertTriangle size={18} /><div><h3>Connections couldn’t load</h3><p className="cc-sub">The local KB API on port 8010 didn’t answer ({failed}). Check its Terminal tab, then retry.</p></div><button className="button button-small button-outline" onClick={() => { setFailed(null); void load(); }}><RefreshCw size={13} />Retry</button></section>;
  if (!data) return null;

  const openRow = open ? data.clients.find(c => c.slug === open.slug) : undefined;
  const openChannel = open ? data.channels.find(ch => ch.id === open.channel) : undefined;
  const modal = openRow && openChannel && <ChannelModal row={openRow} channel={openChannel} options={data.options[openChannel.id] ?? []} account={data.accounts[openChannel.id === 'contacts' ? 'gmail' : openChannel.id]}
    notify={notify} reload={load} onClose={() => setOpen(null)} />;

  // One client (Accounts & sources tab): no cards; the tab's Linked accounts table opens the channel modal via openRequest.
  if (client) return modal || null;

  const counts = {
    all: data.clients.length, attention: data.clients.filter(c => c.needs_attention).length,
    active: data.clients.filter(c => c.status === 'active').length, archived: data.clients.filter(c => c.status === 'inactive').length,
  };
  const un = data.unassigned_leadlock;
  return <section className="cc-panel">
    <header className="cc-head">
      <div><p className="cc-eyebrow">Connections · client by client</p><h3>Where each client’s record comes from</h3>
        <p className="cc-sub">One row per client. LeadLock, Slack, ClickUp and Drive are read only once linked to the client. Email and meetings come from hello@ and attach to a client through its contacts. Click any cell to see or change it.</p></div>
    </header>
    <div className="cc-tools">
      <div className="cc-filters" role="group" aria-label="Show">
        {([['all', 'All clients'], ['attention', 'Needs attention'], ['active', 'Active'], ['archived', 'Archived']] as const).map(([id, label]) =>
          <button key={id} aria-pressed={filter === id} className={filter === id ? 'selected' : ''} onClick={() => setFilter(id)}>{label}<span>{counts[id]}</span></button>)}
      </div>
      <SearchField value={query} onChange={setQuery} placeholder="Search clients" label="Search clients" />
    </div>

    <div className="cc-grid" role="table" aria-label="Clients and their intake channels" style={{ ['--cc-cols' as string]: data.channels.length }}>
      <div className="cc-row cc-row-head" role="row"><span role="columnheader">Client</span>{data.channels.map(ch => <span role="columnheader" key={ch.id}>{ch.label}</span>)}</div>
      {rows.map(row => <div className={`cc-row ${row.status === 'inactive' ? 'is-archived' : ''}`} role="row" key={row.slug}>
        <span role="rowheader" className="cc-client"><strong>{row.name}</strong>{row.status === 'inactive' && <em>Archived</em>}</span>
        {data.channels.map(ch => {
          const cell = row.cells[ch.id];
          return <button role="cell" key={ch.id} className={`cc-cell is-${cell.state}`} disabled={cell.state === 'not_connected'}
            aria-label={`${row.name}, ${ch.label}: ${STATE_LABEL[cell.state]}, ${cellText(cell, ch)}`} onClick={() => setOpen({ slug: row.slug, channel: ch.id })}>
            <span className="cc-cell-state"><StateMark state={cell.state} />{STATE_LABEL[cell.state]}</span>
            <small>{cellText(cell, ch)}</small>
          </button>;
        })}
      </div>)}
      {!rows.length && <p className="cc-empty">No client matches.</p>}
    </div>
    <p className="cc-legend"><span><StateMark state="linked" />Linked: read and kept up to date</span><span><StateMark state="suggested" />To confirm: a match is waiting</span><span><StateMark state="missing" />Not linked</span><span><StateMark state="paused" />Paused: client archived, nothing read</span><span><StateMark state="not_applicable" />Not used by this client</span></p>

    {un.count > 0 && <div className="cc-unassigned">
      <div><strong>{un.count} LeadLock sub-accounts aren’t linked to any client</strong>
        <p>{[un.by_state.needs_client && `${un.by_state.needs_client} match no client`, un.by_state.suggested && `${un.by_state.suggested} look like WIA’s own or demo accounts`, un.by_state.access_failed && `${un.by_state.access_failed} refused access`, un.by_state.not_a_client && `${un.by_state.not_a_client} marked not a client`].filter(Boolean).join(' · ')}. None of them is read.</p></div>
      <button className="button button-small button-outline" onClick={() => setReviewing(true)}>Review them<ArrowRight size={13} /></button>
    </div>}

    {modal}
    {reviewing && <Dialog title="LeadLock sub-accounts with no client" subtitle="Not read until linked" size="lg" onClose={() => { setReviewing(false); void load(); }}>
      <LeadLockMapping notify={notify} only="unassigned" />
    </Dialog>}
  </section>;
}

type Confirm = { item: Item; reactivate: boolean };

/*
 * One client's one channel, in the KB's shared modal frame (Dialog, 560px): eyebrow = the channel, title = the
 * client, meta = its state in one line, body = what's linked / suggested / addable as white blocks, and the
 * sticky footer holds the actions. Linking is a step of its own: the body narrows to "what will happen" and the
 * footer swaps Done for Cancel + the confirming action, so actions always sit in the same place.
 */
function ChannelModal({ row, channel, options, account, notify, reload, onClose }: {
  row: ClientRow; channel: Channel; options: Item[]; account?: string; notify: (m: string) => void; reload: () => Promise<void>; onClose: () => void;
}) {
  const cell = row.cells[channel.id];
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<Confirm | null>(null);
  const [contact, setContact] = useState('');
  const archived = row.status !== 'active';
  const shared = channel.kind === 'shared';
  const linkedIds = new Set(cell.linked.map(i => i.ref.id));
  const pickable = options.filter(o => !linkedIds.has(o.ref.id) && !cell.suggested.some(s => s.ref.id === o.ref.id));
  const records = cell.linked.reduce((a, i) => a + (i.records ?? 0), 0);

  const run = async (fn: () => Promise<string | void>) => {
    setBusy(true);
    try { const message = await fn(); if (message) notify(message); } catch (error) { notify((error as Error).message); }
    finally { setBusy(false); setConfirm(null); await reload(); }
  };
  const link = (c: Confirm) => run(async () => {
    const out = await call<{ collection?: string; moved_records?: number }>('/api/v1/connections/link',
      { client: row.slug, channel: channel.id, ref: c.item.ref, expected_revision: c.item.revision, reactivate: c.reactivate });
    const next = { started: 'Copying its history now.', resumed: 'Its stopped copy resumes where it left off.', queued_by_scheduler: 'The scheduler starts its copy shortly.', not_started: 'Saved, but its copy didn’t start: an admin runs kb backfill.', already_running: 'A copy is already running.', waiting_client_archived: 'Collection starts when the client is reactivated.', waiting_access: 'Collection starts once access works.', via_contacts: 'Matching email and meetings will attach to this client.' }[out.collection ?? ''] ?? '';
    return `${c.item.name} is linked to ${row.name}. ${out.moved_records ? `${out.moved_records} records moved. ` : ''}${next}`;
  });
  const unlink = (item: Item) => run(async () => {
    await call('/api/v1/connections/unlink', { channel: channel.id, ref: item.ref, expected_revision: item.revision });
    return shared ? `${item.name} no longer attaches mail or meetings to ${row.name}.` : `${item.name} is unlinked. Nothing more is collected from it.`;
  });

  const section = (title: string, items: Item[], render: (i: Item) => ReactNode, empty?: string) => <section className="cc-section">
    <h4>{title}</h4>
    {items.length ? <ul className="cc-items">{items.map(i => <li key={i.ref.id}>{render(i)}</li>)}</ul> : empty && <p className="cc-none">{empty}</p>}
  </section>;

  const meta = <>
    <span className={`cc-meta-state is-${cell.state}`}><StateMark state={cell.state} />{STATE_LABEL[cell.state]}</span>
    <span>{cellText(cell, channel)}{!shared && records > 0 ? ` · ${records.toLocaleString('en-US')} records` : ''}</span>
    {archived && <span className="cc-meta-archived">Client archived</span>}
  </>;

  const footer = confirm
    ? <>
      <p className="hint">{shared ? 'Takes effect for mail and meetings read from now on.' : 'You can unlink it later; what was collected stays.'}</p>
      <div className="cc-footer-actions">
        <button className="button button-outline" disabled={busy} onClick={() => setConfirm(null)}>Back</button>
        <button className="button button-primary" disabled={busy} onClick={() => void link(confirm)}><Link2 size={14} />{shared ? 'Approve contact' : archived && !confirm.reactivate ? 'Link only' : 'Link and start collecting'}</button>
      </div>
    </>
    : <>
      <p className="hint">Changes apply at once and are recorded with who made them.</p>
      <button className="button button-outline" onClick={onClose}>Done</button>
    </>;

  return <Dialog title={row.name} subtitle={`${channel.label} · ${shared ? 'Email, calendar & Fathom' : 'Intake channel'}`} meta={meta} footer={footer} className="cc-modal" onClose={onClose}>
    {confirm ? <div className="cc-confirm">
      <h3>{shared ? <>Approve {confirm.item.name} as a contact of {row.name}?</> : <>Link the {channel.label} {channel.unit} “{confirm.item.name}” to {row.name}?</>}</h3>
      <ul className="cc-confirm-points">
        {shared
          ? <li>Email to {account || 'hello@'}, team calendar events and Fathom recordings with this contact on them will attach to {row.name}.</li>
          : <><li>The KB copies this {channel.unit}’s full history now, then keeps it updated.</li>
            {channel.id === 'leadlock' && <li>It keeps counts, stages, sources and dates. Never couples’ names, contact details or messages.</li>}
            {cell.linked.length > 0 && <li>{row.name} already has {plural(cell.linked.length, channel.unit)} linked; this one is added alongside.</li>}</>}
      </ul>
      {archived && !shared && <div className="cc-switch-row"><div><strong>Also reactivate {row.name}</strong><p>{row.name} is archived, so nothing is collected for it. Reactivating resumes all of its channels, not only this one.</p></div>
        <button role="switch" aria-checked={confirm.reactivate} aria-label={`Reactivate ${row.name}`} className={`switch ${confirm.reactivate ? 'on' : ''}`} onClick={() => setConfirm({ ...confirm, reactivate: !confirm.reactivate })}><span /></button></div>}
    </div> : <>
      <p className="cc-explain">{shared
        ? <>Email to {account || 'hello@'}, the team calendars and Fathom recordings are read for every client. A message or meeting attaches to <strong>{row.name}</strong> when one of these contacts is on it.</>
        : <>A {channel.unit} is read only once it’s linked to a client. Linking copies its full history, then keeps it updated.</>}</p>
      {archived && <p className="cc-warn"><AlertTriangle size={14} />{row.name} is archived, so nothing is collected for it, even from linked {shared ? 'contacts' : `${channel.unit}s`}.</p>}

      {section(shared ? 'Contacts' : 'Linked', cell.linked, i => <>
        <div><strong>{i.name}</strong><small>{shared ? (i.display_name || (i.origin === 'manual' ? 'added by an admin' : 'approved suggestion'))
          : i.collection === 'collecting' ? 'Copying its history…' : `${(i.records ?? 0).toLocaleString('en-US')} records${i.last_synced_at ? ` · copied ${fmt(i.last_synced_at)}` : ''}${i.parent && i.parent !== 'LeadLock' ? ` · ${i.parent}` : ''}`}</small></div>
        <button className="text-button" disabled={busy} onClick={() => void unlink(i)}>{shared ? <><X size={12} />Remove</> : <><Unlink size={12} />Unlink</>}</button>
      </>, shared ? 'No contacts yet, so no email or meetings attach to this client.' : `No ${channel.unit} linked.`)}

      {cell.suggested.length > 0 && section('Suggested', cell.suggested, i => <>
        <div><strong>{i.name}</strong><small>{i.reason || (shared ? 'found in hello@ mail' : 'suggested by discovery')}</small></div>
        <span className="cc-item-actions">
          {shared && <button className="text-button" disabled={busy} onClick={() => void unlink(i)}><X size={12} />Reject</button>}
          <button className="button button-small button-primary" disabled={busy} onClick={() => setConfirm({ item: i, reactivate: archived })}><Check size={12} />{shared ? 'Approve' : 'Link'}</button>
        </span>
      </>)}

      {!shared && <section className="cc-section"><h4>Link another {channel.unit}</h4>
        {pickable.length
          ? <ThemedSelect aria-label={`Link a ${channel.unit} to ${row.name}`} value="" onChange={id => { const item = pickable.find(p => p.ref.id === id); if (item) setConfirm({ item, reactivate: archived }); }}>
            <option value="">{`Choose a ${channel.unit}…`}</option>
            {pickable.map(p => <option key={p.ref.id} value={p.ref.id}>{p.parent && p.parent !== 'LeadLock' ? `${p.name} · ${p.parent}` : p.name}</option>)}
          </ThemedSelect>
          : <p className="cc-none">{`No unlinked ${channel.unit}s left to choose from.`}</p>}
      </section>}

      {shared && <form className="cc-section cc-add" onSubmit={e => { e.preventDefault(); const value = contact.trim(); if (value) void run(async () => { await call('/api/v1/connections/contacts', { client: row.slug, value }); setContact(''); return `${value} now attaches email and meetings to ${row.name}.`; }); }}>
        <h4>Add a contact</h4>
        <div><input value={contact} onChange={e => setContact(e.target.value)} placeholder="name@venue.com or venue.com" aria-label="Email address or domain" /><button className="button button-small button-primary" disabled={busy || contact.trim().length < 3}><Plus size={12} />Add</button></div>
        <small>A domain attaches anyone writing from it. Public domains like gmail.com need the person’s full address.</small>
      </form>}

      <section className="cc-section">
        <h4>Use</h4>
        <div className="cc-switch-row">
          <div><strong>{channel.label} is part of this client’s work</strong><p>{cell.not_applicable ? `Marked not used: ${cell.not_applicable}` : cell.linked.length ? 'On while something is linked.' : 'Turn off when the client doesn’t use it, so it isn’t counted as missing.'}</p></div>
          <button role="switch" aria-checked={!cell.not_applicable} aria-label={`${channel.label} is used by ${row.name}`} className={`switch ${cell.not_applicable ? '' : 'on'}`} disabled={busy || (!!cell.linked.length && !cell.not_applicable)}
            onClick={() => void run(async () => { await call('/api/v1/connections/applicable', { client: row.slug, channel: channel.id, applicable: !!cell.not_applicable }); return cell.not_applicable ? `${channel.label} counts for ${row.name} again.` : `${channel.label} marked not used by ${row.name}.`; })}><span /></button>
        </div>
      </section>
    </>}
  </Dialog>;
}
