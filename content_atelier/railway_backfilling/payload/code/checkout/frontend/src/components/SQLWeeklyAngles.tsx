import React, { useEffect, useState } from 'react';
import { StoredAngle, StoredWeek, WeekReview, MomentEvidence, ComparisonReport } from '../types/weeklyStorage';
import { storageRequest } from '../utils/weeklyStorage';

const names = ['audience', 'tension', 'argument', 'take', 'mechanism', 'reader_decision'] as const;
const scoreNames = ['grounding', 'source_relevance', 'audience_fit', 'specificity', 'editorial_usefulness'] as const;
const button = 'rounded-lg border border-[#C4CBD7] px-3 py-2 text-sm disabled:opacity-40';
const label = (s: string) => s.replaceAll('_', ' ');

export function SQLWeeklyAngles() {
  const [weeks, setWeeks] = useState<StoredWeek[]>([]);
  const [week, setWeek] = useState('');
  const [review, setReview] = useState<WeekReview | null>(null);
  const [error, setError] = useState('');
  const [all, setAll] = useState(true);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    storageRequest<StoredWeek[]>('/weeks').then(rows => { if (active) { setWeeks(rows); setWeek(rows[0]?.week_id || ''); } }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (!week) return;
    let active = true;
    setReview(null);
    const refresh = () => storageRequest<WeekReview>(`/weeks/${week}`).then(r => { if (active) { setReview(r); setError(''); } }).catch(e => { if (active) setError(e.message); });
    void refresh(); const id = window.setInterval(refresh, 8000);
    return () => { active = false; window.clearInterval(id); };
  }, [week]);
  const refresh = async () => { if (week) setReview(await storageRequest<WeekReview>(`/weeks/${week}`)); };
  const perform = async (path: string, method = 'POST', body?: unknown) => {
    setBusy(true); setError('');
    try { await storageRequest(path, method, body); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Request failed.'); }
    finally { setBusy(false); }
  };
  const active = review?.runs.some(r => ['queued', 'running'].includes(r.status));
  const angles = review?.angles.filter(a => all || a.workflow === 'historical_comparison_v1' || a.selection_status === 'visible') || [];
  return <section className="py-6 space-y-5 max-w-6xl mx-auto">
    <header><h1 className="font-editorial text-3xl text-[#173354]">Weekly angle review</h1><p className="mt-2 text-sm text-slate-600">Stored sources, generated angles and actual processing status.</p></header>
    {error && <div role="alert" className="rounded-xl bg-red-50 p-4 text-red-800">{error}</div>}
    <div className="flex flex-wrap gap-3 items-center">
      <label>Week <select value={week} onChange={e => setWeek(e.target.value)} className="ml-2 rounded-lg border p-2">{weeks.map(w => <option key={w.week_id} value={w.week_id}>{w.week_start} – {w.week_end}</option>)}</select></label>
      <button className={button} disabled={!week || busy} onClick={() => void refresh().catch(e => setError(e.message))}>Refresh</button>
      <button className={button} disabled={!week || busy || active} onClick={() => void perform(`/weeks/${week}/runs`, 'POST', { mode: 'replay', workflow: 'historical_comparison_v1' })}>Prepare comparison from saved responses</button>
      <button className={button} disabled={!review?.angles.length || busy || active} onClick={() => void perform(`/weeks/${week}/reassess`)}>Reassess saved angles</button>
    </div>
    {!weeks.length && !error && <p role="status">Loading stored weeks…</p>}
    {review && <>
      <div className="rounded-xl bg-white border p-4"><p>{review.transcripts.length} stored transcripts · {review.angles.length} angles · {label(review.week.status)}</p>
        {review.runs.some(r => r.has_partial_failures) && <p className="mt-2 text-amber-800">This week includes a partial extraction. Its accepted moments are preserved; full source coverage is not confirmed.</p>}
        <details className="mt-3"><summary>Source transcripts</summary><ul className="mt-2 space-y-2">{review.transcripts.map(t => <li key={t.transcript_id}><TranscriptInspect transcript={t} /></li>)}</ul></details>
      </div>
      <details open className="rounded-xl bg-white border p-4"><summary className="font-medium">Processing</summary>
        <ul className="mt-3 space-y-3">{review.jobs.map(j => <li key={j.job_id} className="border-t pt-2 text-sm"><strong>{label(j.stage)}</strong> · {label(j.status)} · attempt {j.attempt_count}
          <p>{j.current_message || j.error_summary}</p>{j.total_units !== null && j.completed_units !== null && <p>{j.completed_units} of {j.total_units} completed</p>}
          {j.status === 'running' && j.heartbeat_at && <p>Last worker update: {new Date(j.heartbeat_at).toLocaleTimeString()}</p>}
          {j.result_refs?.coverage_notes?.map((note, i) => <p key={i}>{note}</p>)}
          {['failed', 'waiting'].includes(j.status) && <button className={`${button} mt-2`} disabled={busy} onClick={() => void perform(`/jobs/${j.job_id}/retry`)}>Retry saved stage</button>}
        </li>)}</ul>
        <details className="mt-4"><summary>Process updates</summary><ul className="mt-2 text-sm space-y-2">{review.events.map(e => <li key={e.event_id}><time>{new Date(e.created_at).toLocaleString()}</time> · {e.message}</li>)}</ul></details>
      </details>
      {review.comparisons?.map(c => <section key={c.run_id} className="rounded-xl border bg-white p-4 space-y-3">
        <p className="font-medium">Historical comparison · {label(c.completion_state)}</p>
        <p className="text-sm">{review.approval_cutoff ? `Configured approval cutoff: ${review.approval_cutoff}. Only selected family members can be approved.` : 'Threshold selection is pending. Gate 1 approval is disabled.'} Counts measure quality and historical separation; real embedding tests and editorial review are still required.</p>
        {c.report ? <ComparisonSummary report={c.report} /> : <p>No qualified counts are available until all matching checks complete.</p>}
        {c.report && <p className="flex gap-4 text-sm"><a className="underline" href={`/api/atelier/runs/${c.run_id}/comparison`} target="_blank" rel="noreferrer">Read JSON report</a><a className="underline" href={`/api/atelier/runs/${c.run_id}/comparison.csv`}>Export CSV report</a></p>}
      </section>)}
      <label className="flex gap-2"><input type="checkbox" checked={all} onChange={e => setAll(e.target.checked)} />Show all candidates, including those awaiting matching or below the selection score</label>
      {!angles.length && <p>{review.angles.length ? 'No angles are ready for review under this filter.' : review.jobs.some(j => j.stage === 'angle_generation' && j.status === 'completed') ? 'Generation completed without valid angles. Review the processing notes above.' : 'Angles have not been generated for this week yet.'}</p>}
      <div className="space-y-5">{angles.map(a => <AngleReview key={a.angle_id + a.content_hash} angle={a} busy={busy} perform={perform} />)}</div>
    </>}
  </section>;
}

function TranscriptInspect({ transcript: t }: { transcript: WeekReview['transcripts'][number] }) {
  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const load = async () => {
    if (loading || text !== null) return;
    setLoading(true);
    try {
      const source = await storageRequest<{ original_text: string }>(`/transcripts/${t.transcript_id}`);
      setText(source.original_text); setError('');
    } catch (e) { setError(e instanceof Error ? e.message : 'Transcript could not be loaded.'); }
    finally { setLoading(false); }
  };
  const sourceHref = t.source_url && /^https?:\/\//i.test(t.source_url) ? t.source_url : null;
  return <details onToggle={e => { if (e.currentTarget.open) void load(); }}>
    <summary className="cursor-pointer">{t.title} · Read stored original</summary>
    <p className="text-sm my-2">{t.occurred_at ? `Meeting date: ${new Date(t.occurred_at).toLocaleString()}` : 'Meeting date is unverified.'}</p>
    {sourceHref && <a href={sourceHref} target="_blank" rel="noreferrer" className="underline text-sm">Open source recording</a>}
    {loading && <p role="status">Loading original transcript…</p>}
    {error && <p role="alert">{error} <button className="underline" onClick={() => void load()}>Retry</button></p>}
    {text !== null && <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap text-sm p-3 bg-slate-50 rounded-lg">{text}</pre>}
  </details>;
}

export function AngleReview({ angle: a, busy, perform }: { angle: StoredAngle; busy: boolean; perform: (path: string, method?: string, body?: unknown) => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(a.content_body);
  const [cta, setCta] = useState(a.selected_cta?.text || '');
  const [note, setNote] = useState('');
  const [ack, setAck] = useState(false);
  const [evidence, setEvidence] = useState<MomentEvidence[]>([]);
  const [evidenceError, setEvidenceError] = useState('');
  const [scores, setScores] = useState(Object.fromEntries(scoreNames.map(n => [n, 4])) as Record<typeof scoreNames[number], number>);
  const [reason, setReason] = useState('');
  const matches = a.matching_result?.history || [];
  const flags = a.matching_result?.current_batch_flags || [];
  const comparison = a.workflow === 'historical_comparison_v1' || a.matching_result?.workflow === 'historical_comparison_v1';
  const ready = a.can_approve ?? (!comparison && a.selection_status === 'visible' && a.matching_result?.status === 'complete');
  const showEvidence = async () => {
    try { setEvidence(await Promise.all(a.moment_ids.map(id => storageRequest<MomentEvidence>(`/moments/${id}`)))); setEvidenceError(''); }
    catch (e) { setEvidenceError(e instanceof Error ? e.message : 'Evidence could not be loaded.'); }
  };
  return <article id={`angle-${a.angle_id}`} className="rounded-2xl bg-white border p-5 space-y-4">
    <div><h2 className="font-editorial text-2xl">{a.content_body.title}</h2><p className="text-sm mt-1">{label(a.selection_status)} · {label(a.approval_status)} · score {a.adjusted_score === null ? 'awaiting matching' : Number(a.adjusted_score).toFixed(2)}</p></div>
    {comparison && <p className="text-sm">{a.supersedes_id ? `Refinement or edit of ${a.supersedes_id}` : `Original family ${a.angle_id}`} · baseline quality {a.base_score === null ? 'pending' : Number(a.base_score).toFixed(2)}. Freshness-adjusted score is for ranking. {ready ? 'Selected by the configured approval policy.' : 'Approval awaits threshold selection or current eligibility.'}</p>}
    <dl className="space-y-2">{names.map(n => <div key={n}><dt className="text-xs uppercase tracking-wide text-slate-500">{label(n)}</dt><dd>{a.content_body[n]}</dd></div>)}</dl>
    {a.content_body.inference && <p><strong>Editorial inference:</strong> {a.content_body.inference}</p>}
    <p className="text-sm"><strong>Qualifications:</strong> {a.content_body.qualifiers.join(' · ') || 'None recorded'}</p>
    <p className="text-sm"><strong>Handling notes:</strong> {a.content_body.risks.join(' · ')}</p>
    <div className="text-sm rounded-lg bg-slate-50 p-3">
      {!a.matching_result || !['complete', 'comparison_complete', 'comparison_initial'].includes(a.matching_result.status) ? <p>Matching is incomplete. This angle is awaiting compatible embeddings or reassessment.</p> : <>
        <p>{a.matching_result.history_count} historical arguments checked · repetition risk {((a.matching_result.historical_risk || 0) * 100).toFixed(1)}%</p>
        {comparison && a.matching_result.max_historical_cosine !== undefined && <p>Maximum historical cosine: {a.matching_result.max_historical_cosine.toFixed(6)} (display rounding only).</p>}
        {!!a.matching_result.partial_history_ids?.length && <p className="text-amber-800">History includes the explicitly accepted partial Week 1 baseline.</p>}
        {matches.length > 0 && <details className="mt-2"><summary>Closest historical arguments</summary><MatchList matches={matches.slice(0, 5)} />{matches.length > 5 && <details><summary>Show all comparisons ({matches.length})</summary><MatchList matches={matches} /></details>}</details>}
      </>}
      {flags.length > 0 && <p className="mt-2 text-amber-800">Potential overlap with {flags.length} current-batch angle(s). Review the distinct treatment before approval.</p>}
    </div>
    <button className={button} onClick={() => void showEvidence()}>Inspect original evidence</button>
    {evidenceError && <p role="alert">{evidenceError}</p>}
    {evidence.map((m, i) => <details key={i}><summary>{m.moment.moment_body.quote}</summary><p className="my-2 text-sm">{m.moment.moment_body.context_summary}</p>{m.passages.map(p => <p className="whitespace-pre-wrap text-sm border-l-2 pl-3 mb-2" key={p.passage_id}><strong>{p.title}{p.start_ms !== null ? ` · ${(p.start_ms / 1000).toFixed(1)}s` : ''}</strong><br />{p.text}</p>)}</details>)}
    <button className={button} disabled={busy || a.has_replacement} onClick={() => setEditing(!editing)}>Edit angle</button>
    {editing && <form className="space-y-3" onSubmit={e => { e.preventDefault(); void perform(`/angles/${a.angle_id}`, 'PATCH', { expected_hash: a.content_hash, changes: Object.fromEntries(['title', ...names].map(n => [n, body[n as keyof typeof body]])) }); }}>
      {(['title', ...names] as const).map(n => <label key={n} className="block text-sm">{label(n)}<textarea required className="block w-full border rounded-lg p-2 mt-1" value={body[n]} onChange={e => setBody({ ...body, [n]: e.target.value })} /></label>)}
      <p className="text-sm">Saving an edit requires a fresh quality assessment and matching. The original evidence and generation date are preserved.</p><button className={button} disabled={busy}>Save edit</button>
    </form>}
    {a.base_score === null && <form className="rounded-lg border p-3 space-y-3" onSubmit={e => { e.preventDefault(); void perform(`/angles/${a.angle_id}/quality`, 'POST', { expected_hash: a.content_hash, scores: { ...scores, reasons: [reason] } }); }}>
      <p>Assess the edited angle against its original evidence.</p><div className="flex gap-3 flex-wrap">{scoreNames.map(n => <label key={n} className="text-sm">{label(n)}<input type="number" min="0" max="5" step="0.1" required value={scores[n]} onChange={e => setScores({ ...scores, [n]: Number(e.target.value) })} className="block border p-1 w-20 rounded" /></label>)}</div>
      <label className="block">Assessment reason<textarea required value={reason} onChange={e => setReason(e.target.value)} className="block w-full border p-2 rounded" /></label><button className={button} disabled={busy}>Save quality assessment</button>
    </form>}
    {a.approval_status !== 'approved' && <div className="border-t pt-4 space-y-3">
      <label className="block text-sm">Selected CTA<input value={cta} onChange={e => setCta(e.target.value)} className="block w-full border rounded-lg p-2 mt-1" /></label>
      <label className="block text-sm">Review note<textarea value={note} onChange={e => setNote(e.target.value)} className="block w-full border rounded-lg p-2 mt-1" /></label>
      {flags.length > 0 && <label className="flex gap-2 text-sm"><input type="checkbox" checked={ack} onChange={e => setAck(e.target.checked)} />I reviewed the overlap and explained the distinct treatment in the note.</label>}
      <div className="flex gap-3"><button className={button} disabled={busy || !ready || !cta.trim() || (flags.length > 0 && (!ack || !note.trim()))} onClick={() => void perform(`/angles/${a.angle_id}/decision`, 'POST', { expected_hash: a.content_hash, decision: 'approved', cta: { text: cta }, overlap_acknowledged: ack, note })}>Approve angle</button>
        <button className={button} disabled={busy || comparison} onClick={() => void perform(`/angles/${a.angle_id}/decision`, 'POST', { expected_hash: a.content_hash, decision: 'rejected', note })}>Reject angle</button></div>
    </div>}
    {a.approval_status === 'approved' && <AngleResearch angleId={a.angle_id} />}
  </article>;
}

function AngleResearch({angleId}:{angleId:string}) {
  const [data,setData]=useState<{status:string;jobs:{stage:string;status:string;current_message:string|null}[]}|null>(null),[error,setError]=useState('');
  useEffect(()=>{let active=true;const load=()=>storageRequest<{status:string;jobs:{stage:string;status:string;current_message:string|null}[]}>(`/angles/${angleId}/research`).then(d=>{if(active)setData(d);}).catch(e=>{if(active)setError(e.message);});
    void load();const timer=window.setInterval(load,8000);return()=>{active=false;window.clearInterval(timer);};},[angleId]);
  return <details><summary>Content brief research · {label(data?.status||'loading')}</summary>{error&&<p role="alert">{error}</p>}{data?.jobs.map(j=><p key={j.stage}>{label(j.stage)} · {label(j.status)} · {j.current_message}</p>)}<p>Open Content Brief Review to inspect a saved draft and its original evidence.</p></details>;
}

export function ComparisonSummary({ report }: { report: ComparisonReport }) {
  const [cutoff, setCutoff] = useState(.78);
  const scenario = report.scenarios.find(s => s.cutoff === cutoff) || report.scenarios[0];
  return <div className="space-y-4">
    <div className="grid gap-3 md:grid-cols-3">{report.scenarios.map(s => <div key={s.cutoff} className="rounded-lg bg-slate-50 p-3">
      <strong>Historical cosine &lt; {s.cutoff.toFixed(2)}</strong>
      <p>{s.counts.initial_qualified} initial → {s.counts.final_qualified} final quality/history-qualified families</p>
      <p className="text-sm">{s.counts.recovered} recovered · {s.counts.retained_original_fallbacks} original fallbacks</p>
      <p className="text-sm">{s.counts.current_batch_flagged} candidates with current-batch conflicts · {s.counts.qualified_without_batch_flags} qualified without conflicts</p>
      <p className="text-sm">Still failing: {s.counts.failing_quality} quality · {s.counts.failing_history} history · {s.counts.failing_both} both</p>
      <p className="text-sm">{s.counts.no_supported_alternative} no supported alternatives</p>
    </div>)}</div>
    <label className="text-sm">Inspect scenario <select className="ml-2 border rounded p-2" value={cutoff} onChange={e => setCutoff(Number(e.target.value))}>{report.scenarios.map(s => <option key={s.cutoff} value={s.cutoff}>{s.cutoff.toFixed(2)}</option>)}</select></label>
    <p className="text-sm">These are saved assessment snapshots. Changing the displayed cutoff runs no inference or encoding. Edits need a new comparison assessment.</p>
    {scenario?.families.map(f => <details key={f.original_id} className="text-sm border-t pt-2">
      <summary>{f.original_id} · {f.selected_id ? `qualifies: ${f.selected_id}` : 'no qualifying candidate'}</summary>
      <p>{f.explanation}</p><p>Original: {f.original_reasons.join(', ') || 'qualifies'} · Replacement: {f.replacement_id ? f.replacement_reasons?.join(', ') || 'qualifies' : 'none'}</p>
      <p>Selected current-batch conflicts: {f.selected_id ? scenario.current_batch_flags[f.selected_id]?.length || 0 : 0}</p>
      <p><a className="underline" href={`#angle-${f.original_id}`}>Original argument and evidence</a>{f.replacement_id && <> · <a className="underline" href={`#angle-${f.replacement_id}`}>Refinement argument and evidence</a></>}</p>
    </details>)}
  </div>;
}

function MatchList({ matches }: { matches: NonNullable<StoredAngle['matching_result']>['history'] }) {
  return <ul className="mt-2 space-y-2">{matches?.map(m => <li key={m.angle_id}><details><summary>{m.title || 'Historical argument'} · similarity {m.cosine.toFixed(3)} · age {m.age_days.toFixed(1)} days · risk {(m.risk * 100).toFixed(1)}%</summary><p>{m.argument}</p>{m.week_start && <p>Week beginning {m.week_start} · {m.approval_status || 'pending'}</p>}</details></li>)}</ul>;
}
