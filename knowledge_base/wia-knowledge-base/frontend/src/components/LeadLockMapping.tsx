import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Ban, Check, Link2, RefreshCw, RotateCcw, Sparkles, Unlink } from 'lucide-react';
import { Badge, Dialog, SearchField } from './UI';
import { ThemedSelect } from './ThemedSelect';
import './LeadLockMapping.css';

/*
 * LeadLock sub-account ↔ client mapping (S2 decided 29 Oct; Connections shape approved 5 Nov).
 * Reads and writes /api/v1/connections/leadlock (backend/services/clients/connections.py). The same component
 * is the source-side view on Connections (every sub-account) and the client-side view on a client's
 * Accounts & sources tab (`client` set). Mapping is what starts collection: an unmapped sub-account is never
 * read. Without the local KB API (the static preview build) it renders nothing.
 */
type State = 'mapped' | 'suggested' | 'needs_client' | 'not_a_client' | 'access_failed';
interface ClientRef { slug: string; name: string; status: 'active' | 'inactive'; revision: number }
interface Row {
  location_id: string; name: string; state: State; access: string; access_error: string | null; is_new: boolean;
  client: ClientRef | null; collection: string | null; records: number; last_synced_at: string | null; revision: number | null;
  suggestion: { kind: 'client'; client: ClientRef; reason: string } | { kind: 'not_a_client'; reason: string } | null;
}
interface Payload { rows: Row[]; counts: Partial<Record<State, number>>; clients: ClientRef[] }

const STATES: { id: State | 'all'; label: string }[] = [
  { id: 'all', label: 'All' }, { id: 'suggested', label: 'Suggested' }, { id: 'needs_client', label: 'Needs a client' },
  { id: 'mapped', label: 'Mapped' }, { id: 'not_a_client', label: 'Not a client' }, { id: 'access_failed', label: 'Access failed' },
];
const STATE_BADGE: Record<State, { label: string; tone: 'green' | 'blue' | 'neutral' | 'amber' | 'gold' }> = {
  mapped: { label: 'Mapped', tone: 'green' }, suggested: { label: 'Suggested', tone: 'blue' },
  needs_client: { label: 'Needs a client', tone: 'gold' }, not_a_client: { label: 'Not a client', tone: 'neutral' },
  access_failed: { label: 'Access failed', tone: 'amber' },
};
const NEW_CLIENT = '__new__';
const n = (v: number) => v.toLocaleString('en-US');
const when = (iso: string) => new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });

function collectionText(row: Row) {
  switch (row.collection) {
    case 'collecting': return 'Copying its history…';
    case 'up_to_date': return `${n(row.records)} records · copied ${row.last_synced_at ? when(row.last_synced_at) : ''}`;
    case 'paused_client_archived': return 'Paused: the client is archived';
    case 'no_access': return 'Mapped, but LeadLock refused access';
    case 'waiting': return 'Waiting for its first copy';
    default: return '';
  }
}

async function call<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, body === undefined ? undefined : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = (json as { detail?: { code?: string; message?: string } }).detail;
    throw new Error(detail?.code === 'changed_elsewhere' ? 'Someone changed this sub-account meanwhile. The list has been reloaded.' : detail?.message || `HTTP ${response.status}`);
  }
  return json as T;
}

type Pending =
  | { kind: 'map'; row: Row; client: ClientRef; reactivate: boolean }
  | { kind: 'unmap'; row: Row }
  | { kind: 'new-client'; row: Row; name: string };

export default function LeadLockMapping({ client, notify, only }: { client?: string; notify: (message: string) => void; only?: 'unassigned' }) {
  const [data, setData] = useState<Payload | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const [filter, setFilter] = useState<State | 'all'>('all');
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);

  const load = useCallback(() => call<Payload>(`/api/v1/connections/leadlock${client ? `?client=${encodeURIComponent(client)}` : ''}`)
    .then(json => { setData(json); setUnavailable(false); setFailed(null); })
    // 404 = no KB API here (the static preview build): show nothing. Anything else is a real failure: say so.
    .catch((error: Error) => { if (/HTTP 404|local_only/.test(error.message)) setUnavailable(true); else setFailed(error.message); }), [client]);
  useEffect(() => { void load(); }, [load]);

  // only=unassigned: sub-accounts that belong to no client (not mapped, and not suggested for a client).
  const base = useMemo(() => (data?.rows ?? []).filter(r => only !== 'unassigned' || (r.state !== 'mapped' && !(r.state === 'suggested' && r.suggestion?.kind === 'client'))), [data, only]);
  const rows = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    return base.filter(r => (filter === 'all' || r.state === filter) && (!q || r.name.toLowerCase().includes(q) || r.client?.name.toLowerCase().includes(q)));
  }, [data, base, filter, query]);

  if (unavailable) return null; // preview build: no KB API
  if (!data && failed) return <section className={`llm-panel llm-failed ${client ? 'llm-compact' : ''}`}><AlertTriangle size={18} /><div><h3>LeadLock mapping couldn’t load</h3><p className="llm-sub">The local KB API on port 8010 didn’t answer ({failed}). Check its Terminal tab, then retry.</p></div><button className="button button-small button-outline" onClick={() => { setFailed(null); void load(); }}><RefreshCw size={13} />Retry</button></section>;
  if (!data) return null;
  if (client && !data.rows.length) return <section className="llm-panel llm-compact"><header className="llm-head"><div><p className="llm-eyebrow">LeadLock</p><h3>No LeadLock sub-account for this client</h3><p className="llm-sub">Map one from Connections when the client uses LeadLock.</p></div></header></section>;

  const act = async (row: Row, fn: () => Promise<unknown>, done?: string) => {
    setBusy(row.location_id);
    try { await fn(); if (done) notify(done); } catch (error) { notify((error as Error).message); } finally { setBusy(null); await load(); }
  };
  const confirmMap = (row: Row, slug: string) => {
    if (slug === NEW_CLIENT) { setPending({ kind: 'new-client', row, name: row.name.trim() }); return; }
    const target = data.clients.find(c => c.slug === slug);
    if (target) setPending({ kind: 'map', row, client: target, reactivate: target.status !== 'active' });
  };
  const doMap = (p: Extract<Pending, { kind: 'map' }>) => act(p.row, async () => {
    const out = await call<{ collection: string; moved_records: number }>(`/api/v1/connections/leadlock/${p.row.location_id}/map`,
      { client: p.client.slug, expected_revision: p.row.revision, reactivate: p.reactivate });
    const next = { started: 'Copying its history now.', resumed: 'Its stopped copy resumes where it left off.', queued_by_scheduler: 'The scheduler starts its copy shortly.', already_running: 'A copy is already running.', waiting_client_archived: 'Collection starts when the client is reactivated.', waiting_access: 'Collection starts once LeadLock access works.' }[out.collection] ?? '';
    notify(`${p.row.name} is mapped to ${p.client.name}. ${out.moved_records ? `${n(out.moved_records)} records moved. ` : ''}${next}`);
  });

  const counts = data.counts;
  return <section className={`llm-panel ${client ? 'llm-compact' : ''}`}>
    <header className="llm-head">
      <div>
        <p className="llm-eyebrow">LeadLock · {client ? 'this client' : `${n(data.rows.length)} sub-accounts with the app`}</p>
        <h3>{client ? 'LeadLock sub-accounts' : 'Which client is each sub-account?'}</h3>
        <p className="llm-sub">{client ? 'Mapped sub-accounts feed this client’s Leads tab. Suggested ones match its name and wait for confirmation.' : 'Only mapped sub-accounts are read. Mapping one copies its full history, then keeps it updated. New sub-accounts wait here until someone maps them.'}</p>
      </div>
      {!client && <button className="button button-small button-outline" disabled={busy === 'refresh'} onClick={async () => {
        setBusy('refresh');
        try { const out = await call<{ installed: number; removed: number }>('/api/v1/connections/leadlock/refresh', {}); notify(`LeadLock lists ${out.installed} sub-accounts${out.removed ? `; ${out.removed} uninstalled` : ''}.`); }
        catch (error) { notify((error as Error).message); } finally { setBusy(null); await load(); }
      }}><RefreshCw size={13} className={busy === 'refresh' ? 'llm-spin' : ''} />Refresh from LeadLock</button>}
    </header>

    {!client && <div className="llm-tools">
      <div className="llm-filters" role="group" aria-label="Show">
        {STATES.filter(s => only !== 'unassigned' || s.id !== 'mapped').map(s => {
          const count = s.id === 'all' ? base.length : base.filter(r => r.state === s.id).length;
          return <button key={s.id} aria-pressed={filter === s.id} className={filter === s.id ? 'selected' : ''} onClick={() => setFilter(s.id)} disabled={s.id !== 'all' && !count}>{s.label}<span>{count}</span></button>;
        })}
      </div>
      <SearchField value={query} onChange={setQuery} placeholder="Search sub-accounts or clients" label="Search LeadLock sub-accounts" />
    </div>}

    <div className="llm-table" role="table" aria-label="LeadLock sub-accounts">
      <div className="llm-row llm-row-head" role="row"><span role="columnheader">Sub-account</span><span role="columnheader">State</span><span role="columnheader">Client</span><span role="columnheader" /></div>
      {rows.map(row => {
        const badge = STATE_BADGE[row.state];
        const working = busy === row.location_id;
        return <div className={`llm-row ${working ? 'is-busy' : ''}`} role="row" key={row.location_id}>
          <span role="cell" className="llm-name"><strong>{row.name}</strong>{row.is_new && <em className="llm-new">New</em>}</span>
          <span role="cell"><Badge tone={badge.tone} dot={false}>{badge.label}</Badge></span>
          <span role="cell" className="llm-client">
            {row.state === 'mapped' && row.client && <><strong>{row.client.name}</strong><small className={`llm-collection is-${row.collection}`}>{collectionText(row)}</small></>}
            {row.state === 'suggested' && row.suggestion?.kind === 'client' && <><span className="llm-suggest"><Sparkles size={12} />{row.suggestion.client.name}{row.suggestion.client.status !== 'active' && <em>archived</em>}</span><small>{row.suggestion.reason}</small></>}
            {row.state === 'suggested' && row.suggestion?.kind === 'not_a_client' && <><span className="llm-suggest"><Sparkles size={12} />Not a client</span><small>{row.suggestion.reason}</small></>}
            {row.state === 'needs_client' && <small>No client matches this name</small>}
            {row.state === 'not_a_client' && <small>Never read. Set by an admin.</small>}
            {row.state === 'access_failed' && <small className="llm-error"><AlertTriangle size={11} />{row.access_error || 'LeadLock refused access'}</small>}
          </span>
          <span role="cell" className="llm-actions">
            {row.state === 'suggested' && row.suggestion?.kind === 'client' && <button className="button button-small button-primary" disabled={working} onClick={() => confirmMap(row, (row.suggestion as { client: ClientRef }).client.slug)}><Check size={12} />Confirm</button>}
            {row.state === 'suggested' && row.suggestion?.kind === 'not_a_client' && <button className="button button-small button-primary" disabled={working} onClick={() => act(row, () => call(`/api/v1/connections/leadlock/${row.location_id}/not-a-client`, { expected_revision: row.revision, reason: row.suggestion?.reason }), `${row.name} is marked “not a client”.`)}><Ban size={12} />Not a client</button>}
            {(row.state === 'suggested' || row.state === 'needs_client' || row.state === 'mapped' || row.state === 'access_failed') &&
              <ThemedSelect aria-label={`Client for ${row.name}`} className="llm-select" value="" disabled={working} onChange={slug => slug && confirmMap(row, slug)}>
                <option value="">{row.state === 'mapped' ? 'Change client…' : row.state === 'suggested' ? 'Another client…' : 'Choose a client…'}</option>
                {data.clients.filter(c => c.slug !== row.client?.slug).map(c => <option key={c.slug} value={c.slug}>{c.status === 'active' ? c.name : `${c.name} (archived)`}</option>)}
                <option value={NEW_CLIENT}>+ New client…</option>
              </ThemedSelect>}
            {(row.state === 'needs_client' || (row.state === 'suggested' && row.suggestion?.kind === 'client')) && <button className="text-button" disabled={working} onClick={() => act(row, () => call(`/api/v1/connections/leadlock/${row.location_id}/not-a-client`, { expected_revision: row.revision }), `${row.name} is marked “not a client”.`)}><Ban size={12} />Not a client</button>}
            {row.state === 'mapped' && <button className="text-button" disabled={working} onClick={() => setPending({ kind: 'unmap', row })}><Unlink size={12} />Unmap</button>}
            {row.state === 'not_a_client' && <button className="text-button" disabled={working} onClick={() => act(row, () => call(`/api/v1/connections/leadlock/${row.location_id}/restore`, { expected_revision: row.revision }), `${row.name} is back in the unmapped list.`)}><RotateCcw size={12} />Undo</button>}
          </span>
        </div>;
      })}
      {!rows.length && <p className="llm-empty">Nothing matches.</p>}
    </div>

    {pending?.kind === 'map' && <Dialog title={`Map ${pending.row.name}?`} subtitle="LeadLock sub-account" onClose={() => setPending(null)}
      footer={<div className="llm-footer-actions"><button className="button button-outline" onClick={() => setPending(null)}>Cancel</button><button className="button button-primary" onClick={() => { const p = pending; setPending(null); void doMap(p); }}><Link2 size={14} />{pending.client.status === 'active' || pending.reactivate ? 'Map and start collecting' : 'Map only'}</button></div>}>
      <p className="body-copy">This sub-account will belong to <strong>{pending.client.name}</strong>. The KB copies its full lead history now, then keeps it updated. It keeps counts, stages, sources and dates, never couples’ names, contact details or messages.</p>
      {pending.row.state === 'mapped' && pending.row.client && <p className="llm-note"><AlertTriangle size={14} />It’s mapped to <strong>{pending.row.client.name}</strong> now. The {n(pending.row.records)} records already collected will move to {pending.client.name}.</p>}
      {pending.client.status !== 'active' && <div className="llm-switch-row">
        <div><strong>Also reactivate {pending.client.name}</strong><p>{pending.client.name} is archived, so nothing of it is collected. Reactivating resumes all of its sources, not only LeadLock.</p></div>
        <button role="switch" aria-checked={pending.reactivate} aria-label={`Reactivate ${pending.client.name}`} className={`switch ${pending.reactivate ? 'on' : ''}`} onClick={() => setPending({ ...pending, reactivate: !pending.reactivate })}><span /></button>
      </div>}
    </Dialog>}

    {pending?.kind === 'unmap' && <Dialog title={`Stop reading ${pending.row.name}?`} subtitle="LeadLock sub-account" onClose={() => setPending(null)}
      footer={<div className="llm-footer-actions"><button className="button button-outline" onClick={() => setPending(null)}>Cancel</button><button className="button button-primary" onClick={() => { const row = pending.row; setPending(null); void act(row, () => call(`/api/v1/connections/leadlock/${row.location_id}/unmap`, { expected_revision: row.revision }), `${row.name} is unmapped. Nothing more is collected.`); }}><Unlink size={14} />Unmap</button></div>}>
      <p className="body-copy">Nothing more is collected from this sub-account. The {n(pending.row.records)} records already collected stay with <strong>{pending.row.client?.name}</strong>. If it was mapped to the wrong client, choose the right client instead: that moves them.</p>
    </Dialog>}

    {pending?.kind === 'new-client' && <Dialog title="Add a client" subtitle={`For ${pending.row.name}`} onClose={() => setPending(null)}
      footer={<div className="llm-footer-actions"><button className="button button-outline" onClick={() => setPending(null)}>Cancel</button><button className="button button-primary" disabled={pending.name.trim().length < 2} onClick={async () => {
        const p = pending;
        try {
          const created = await call<ClientRef>('/api/v1/clients', { name: p.name });
          await load();
          setPending({ kind: 'map', row: p.row, client: created, reactivate: false });
        } catch (error) { notify((error as Error).message); }
      }}>Add client</button></div>}>
      <label className="llm-field"><span>Client name</span><input value={pending.name} onChange={e => setPending({ ...pending, name: e.target.value })} autoFocus /></label>
      <p className="hint">Adding a client also looks for its other sources (Slack, ClickUp, Drive, email contacts) as suggestions to review. Nothing is linked without a person confirming it.</p>
    </Dialog>}
  </section>;
}
