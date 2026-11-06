import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw, Search, FileText, X } from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';

type Source = {
  source_id: string; title: string; kind: string; status: string; source_url?: string;
  occurred_at?: string; received_at: string; collection_status?: string;
  extraction_status?: string; indexing_status?: string; error_summary?: string;
};
type Overview = {
  can_admin: boolean; schedule: string; sources: Source[];
  connections: { connection_id: string; activated_at: string; checkpoint: string; health: string; error_summary?: string }[];
  buckets: { bucket_id: string; starts_at: string; cutoff?: string; status: string }[];
  requests: { request_id: string; connection_id: string; window_start: string; window_end: string; status: string; coverage: Record<string, unknown> }[];
  jobs: { job_id: string; stage: string; status: string; error_summary?: string }[];
};
type Detail = {
  source: Source;
  revisions: { revision_id: string; received_at: string; original_text?: string; indexing_status: string; deleted: boolean; passage_map?: unknown[] }[];
  assets: { asset_id: string; filename: string; status: string; source_id?: string; raw_artifact?: string; metadata: { permalink?: string; error?: string } }[];
};

async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/atelier/intake/${path}`, {
    credentials: 'same-origin', cache: 'no-store', redirect: 'error',
    ...(body !== undefined ? { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) } : {}),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || result.error || 'Source intake is unavailable.');
  return result;
}
const date = (value?: string) => value ? new Date(value).toLocaleString() : '—';
const safeUrl = (value?: string) => value && /^https?:\/\//i.test(value) ? value : undefined;
const button = 'px-3 py-2 rounded-lg border border-[#D8DFE8] text-sm bg-white hover:bg-slate-50 disabled:opacity-50';

export function SourcesView() {
  const { user } = useAuth();
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<{ chunk_id: string; source_id?: string; title: string; chunk_text: string }[] | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [bucket, setBucket] = useState<{ bucket: { starts_at: string }; sources: Source[] } | null>(null);
  const [original, setOriginal] = useState<unknown>(null);
  const load = useCallback(async () => {
    if (user?.role !== 'team') return;
    try { setData(await api<Overview>('overview')); setError(''); }
    catch (e) { setError((e as Error).message); }
  }, [user?.role]);
  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 15000);
    return () => window.clearInterval(timer);
  }, [load]);
  const act = async (path: string) => {
    setBusy(true); setError('');
    try { await api(path, {}); await load(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  const open = async (id: string) => {
    setOriginal(null);
    try { setDetail(await api<Detail>(`sources/${id}`)); }
    catch (e) { setError((e as Error).message); }
  };
  if (user?.role !== 'team') return <p className="p-8">Sources are available to the internal team.</p>;
  return <section className="pb-12 text-[#1B2838] space-y-6">
    <header className="flex items-start justify-between gap-5">
      <div><h1 className="text-3xl font-semibold">Sources</h1>
        <p className="text-sm text-slate-500 mt-2">New meeting transcripts and Slack conversations. Weekly completion: {data?.schedule || 'Saturday 04:00 America/Chicago'}.</p></div>
      <div className="flex gap-2 shrink-0">
        <button className={button} onClick={() => void load()} aria-label="Reload intake status"><RefreshCw size={16} /></button>
        {data?.can_admin && <>
          <button disabled={busy} className={button} onClick={() => void act('refresh')}>Collect through now</button>
          <button disabled={busy} className={button} onClick={() => void act('complete')}>Complete current bucket</button>
        </>}
      </div>
    </header>
    {error && <p role="alert" className="p-4 rounded-lg bg-amber-50 text-amber-900">{error}</p>}
    {!data && !error && <p>Loading intake status…</p>}
    {data && <>
      <div className="grid md:grid-cols-2 gap-4">
        {(['fathom', 'slack'] as const).map(provider => {
          const connection = data.connections.find(c => c.connection_id === provider);
          return <article key={provider} className="p-5 rounded-xl border border-slate-200 bg-white/80">
            <h2 className="font-semibold capitalize">{provider} <span className="font-normal text-sm text-slate-500">· {connection?.health || 'Inactive'}</span></h2>
            {connection ? <p className="text-sm text-slate-500 mt-2">Activated {date(connection.activated_at)}<br />Collected through {date(connection.checkpoint)}</p>
              : <p className="text-sm text-slate-500 mt-2">Activation starts future collection. Earlier history is excluded.</p>}
            {connection?.error_summary && <p className="text-sm text-amber-800 mt-2">{connection.error_summary}</p>}
            {!connection && data.can_admin && <button disabled={busy} className={`${button} mt-3`} onClick={() => void act(`connections/${provider}/activate`)}>Activate {provider}</button>}
          </article>;
        })}
      </div>
      <div className="rounded-xl border border-slate-200 overflow-hidden bg-white/70">
        <h2 className="font-semibold p-4 border-b border-slate-200">Weekly intake buckets</h2>
        {!data.buckets.length && <p className="p-4 text-sm text-slate-500">Activate a connector to start the first bucket.</p>}
        {data.buckets.map(b => <button key={b.bucket_id} onClick={async () => {
          try { setBucket(await api(`buckets/${b.bucket_id}`)); setHits(null); }
          catch (e) { setError((e as Error).message); }
        }} className="w-full text-left p-4 border-b last:border-b-0 border-slate-100 hover:bg-white flex justify-between gap-4 text-sm">
          <span>{date(b.starts_at)} → {b.cutoff ? date(b.cutoff) : 'current'}</span><strong className="capitalize">{b.status}</strong>
        </button>)}
      </div>
      <form className="flex gap-2" onSubmit={async e => {
        e.preventDefault(); setBusy(true); setError('');
        try { setHits(await api('search', { text: query, k: 20 })); }
        catch (err) { setError((err as Error).message); }
        finally { setBusy(false); }
      }}>
        <input aria-label="Search ready source text" value={query} maxLength={2000} onChange={e => setQuery(e.target.value)} placeholder="Search indexed source text…" className="flex-1 p-3 rounded-lg border border-slate-200 bg-white" />
        <button disabled={busy || !query.trim()} className={button}><Search size={17} /></button>
        {hits && <button type="button" className={button} onClick={() => setHits(null)}>Clear</button>}
      </form>
      {hits ? <div className="space-y-3">{!hits.length && <p>No matching indexed sources.</p>}{hits.map(hit => <article key={hit.chunk_id} className="p-4 rounded-xl border border-slate-200 bg-white">
        <button className="font-semibold text-left" disabled={!hit.source_id} onClick={() => hit.source_id && void open(hit.source_id)}>{hit.title}</button>
        <p className="mt-2 text-sm whitespace-pre-wrap">{hit.chunk_text}</p>
      </article>)}</div> : <div className="rounded-xl border border-slate-200 overflow-hidden bg-white/70">
        <div className="p-4 border-b border-slate-200 flex justify-between items-center"><h2 className="font-semibold">{bucket ? `Bucket starting ${date(bucket.bucket.starts_at)}` : 'Recently received sources'}</h2>
          {bucket && <button className={button} onClick={() => setBucket(null)}>All recent sources</button>}</div>
        {!(bucket?.sources || data.sources).length && <p className="p-4 text-sm text-slate-500">No sources received in this view.</p>}
        {(bucket?.sources || data.sources).map((s, i) => <button key={`${s.source_id}-${i}`} className="w-full text-left p-4 border-b last:border-b-0 border-slate-100 hover:bg-white flex justify-between gap-4" onClick={() => void open(s.source_id)}>
          <span><span className="font-medium">{s.title}</span><span className="block text-xs text-slate-500 mt-1">{s.kind} · Occurred {date(s.occurred_at)} · Received {date(s.received_at)}</span></span>
          <span className="text-xs leading-5 text-right shrink-0">Collection: {s.collection_status || s.status}<br />Extraction: {s.extraction_status || 'pending'}<br />Index: {s.indexing_status || 'pending'}</span>
        </button>)}
      </div>}
      {!!data.requests.length && <details className="p-4 border border-slate-200 rounded-xl"><summary className="cursor-pointer font-medium">Awaiting collection coverage ({data.requests.length})</summary>
        {data.requests.map(r => <div key={r.request_id} className="text-sm mt-3"><p>{r.connection_id} · {date(r.window_start)} → {date(r.window_end)} · {r.status}</p><pre className="overflow-auto text-xs mt-1">{JSON.stringify(r.coverage, null, 2)}</pre></div>)}
      </details>}
      {!!data.jobs.length && <div className="p-4 border border-slate-200 rounded-xl space-y-3"><h2 className="font-medium">Processing</h2>
        {data.jobs.map(j => <div key={j.job_id} className="flex justify-between gap-3 text-sm"><div>{j.stage} · {j.status}{j.error_summary && <p className="text-amber-800 mt-1">{j.error_summary}</p>}</div>
          {data.can_admin && ['failed', 'waiting'].includes(j.status) && <button disabled={busy} className={button} onClick={() => void act(`jobs/${j.job_id}/retry`)}>Retry</button>}
        </div>)}
      </div>}
    </>}
    {detail && <div className="fixed inset-0 bg-black/30 z-50 flex justify-end" onClick={() => setDetail(null)}>
      <aside role="dialog" aria-modal="true" aria-label="Source original and revisions" className="w-full max-w-3xl overflow-y-auto bg-[#FAFBFC] p-7 space-y-5 shadow-xl" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between gap-4"><h2 className="text-xl font-semibold">{detail.source.title}</h2><button aria-label="Close source" onClick={() => setDetail(null)}><X /></button></div>
        {safeUrl(detail.source.source_url) && <a className="underline text-sm" href={safeUrl(detail.source.source_url)} target="_blank" rel="noreferrer">Open provider original</a>}
        {detail.revisions.map(r => <article key={r.revision_id} className="p-4 bg-white rounded-xl border border-slate-200 space-y-3">
          <p className="text-sm text-slate-500">Received {date(r.received_at)} · {r.deleted ? 'Deleted upstream' : r.indexing_status}</p>
          <pre className="whitespace-pre-wrap font-sans text-sm">{r.original_text || 'No readable text in this revision.'}</pre>
          <div className="flex gap-3"><button className={button} onClick={async () => {
            try { setOriginal(await api(`revisions/${r.revision_id}/original`)); }
            catch (e) { setError((e as Error).message); }
          }}><FileText size={14} className="inline mr-1" />Original payload</button>
            <details><summary className="text-sm cursor-pointer py-2">Source locations</summary><pre className="text-xs whitespace-pre-wrap">{JSON.stringify(r.passage_map, null, 2)}</pre></details></div>
        </article>)}
        {detail.assets.map(a => <article key={a.asset_id} className="p-4 border border-slate-200 rounded-xl text-sm space-x-3">
          <span>{a.filename} · {a.status}</span>
          {a.raw_artifact && <a className="underline" href={`/api/atelier/intake/assets/${a.asset_id}/content`}>Download original</a>}
          {a.source_id && <button className="underline" onClick={() => void open(a.source_id!)}>Extracted text</button>}
          {safeUrl(a.metadata.permalink) && <a className="underline" href={safeUrl(a.metadata.permalink)} target="_blank" rel="noreferrer">Provider link</a>}
          {a.metadata.error && <p className="text-amber-800">{a.metadata.error}</p>}
        </article>)}
        {original !== null && <pre className="p-4 bg-slate-100 rounded-xl text-xs whitespace-pre-wrap break-words">{JSON.stringify(original, null, 2)}</pre>}
      </aside>
    </div>}
  </section>;
}
