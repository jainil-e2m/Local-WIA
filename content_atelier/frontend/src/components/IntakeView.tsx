import { nextCycleWords } from '../utils/nextRun';
import React, { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import type { IntakeSource, IntakeSearchHit } from '../api/types';
import type { IntakeJob } from '../api/schema';
import { apiPost } from '../api/routes';
import { useApiQuery, useInvalidate } from '../api/query';
import { storageRequest } from '../utils/weeklyStorage';
import { useMe } from '../utils/me';
import { paths } from '../app/routes';
import { failureParts } from './shared/JobProgress';
import { useGuardedAction } from './shared/conflict';
import { ErrorState, LoadingState } from './shared/states';
import { PageHeading } from './PageHeading';
import { ConfirmDialog, Dialog, HEADER_QUIET, HEADING, META, PANEL, Pill, QUIET_BUTTON, SearchBox, StatusLine, TEXT_BUTTON, plainReason, shortDay, type Tone } from './AdminParts';

/* Sources → Intake: the connector (Fathom) and whether they are collecting, the weekly buckets, what was received
   lately, and what is being processed now. "Processing" lists only the work that is waiting or running and what failed in
   the last seven days, by plain names; work that was replaced or cancelled is never listed, and older failures are behind
   "Show earlier". A source (`/sources/intake/sources/:sourceId`) and a bucket (`/sources/intake/buckets/:bucketId`) have
   paths of their own. */

const PROVIDER_NAMES = { fathom: 'Fathom', slack: 'Slack' } as const;
const RECENT_DAYS = 7;
const BUCKETS_SHOWN = 6;

/** Work as a person names it. */
export const STAGE_NAMES: Record<string, string> = {
  intake_fathom: 'Collecting from Fathom', intake_slack: 'Collecting from Slack', source_admission: 'Taking in a call', history_admission: 'Taking in a call',
  document_normalise: 'Preparing a document', document_classification: 'Sorting a call', transcript_chunk_preparation: 'Preparing a call for search',
  transcript_chunk_embedding: 'Making a call searchable', moment_extraction: 'Scenes from a call', moment_embedding: 'Making scenes searchable',
  topic_assignment: 'Topics for scenes', angle_generation: 'Writing content angles', angle_embedding: 'Comparing angles', angle_matching: 'Comparing angles with earlier weeks',
  angle_initial_assessment: 'Checking angles', angle_final_assessment: 'Checking angles', angle_refinement: 'Improving angles', angle_initial_embedding: 'Comparing angles',
  angle_refined_embedding: 'Comparing angles', angle_editor_validation: 'Checking angles', card_verification: 'Checking angles', card_refresh: 'Refreshing an angle',
  brief_prepare: 'Preparing a brief', brief_context: 'Preparing a brief', brief_research: 'Research for a brief', brief_writing: 'Writing a brief', brief_validation: 'Brief check',
  pack_assemble: 'Putting a pack together', pack_finish: 'Pack finishing', pack_check: 'Pack check', pack_repair: 'Pack repair', pack_recheck: 'Pack check again',
  pack_finalize: 'Pack final touches', pack_validation: 'Pack check', context_mining: 'Learning from the week', evaluation_run: 'Quality check',
};
export const stageName = (stage: string) => STAGE_NAMES[stage] ?? (stage.charAt(0).toUpperCase() + stage.slice(1).replaceAll('_', ' '));

/** A job that was replaced or cancelled: never listed. */
export const isReplaced = (job: Pick<IntakeJob, 'status' | 'error_summary'>) =>
  ['cancelled', 'superseded'].includes(job.status) || (job.status === 'failed' && /^\s*(superseded|cancelled|canceled)\b/i.test(job.error_summary ?? ''));

/** What "Processing" shows: waiting or running work (not the steps that wait behind a failure), the failures of the last
    seven days, and the older failures for "Show earlier". */
export function processingRows(jobs: IntakeJob[], now = Date.now()): { active: IntakeJob[]; recent: IntakeJob[]; earlier: IntakeJob[] } {
  const listed = jobs.filter(job => !isReplaced(job));
  const failedRuns = new Set(listed.filter(job => job.status === 'failed' && job.run_id).map(job => job.run_id));
  const active = listed.filter(job => ['queued', 'running', 'waiting'].includes(job.status) && !(job.status === 'queued' && job.run_id && failedRuns.has(job.run_id)));
  const failed = listed.filter(job => job.status === 'failed');
  const when = (job: IntakeJob) => Date.parse(job.updated_at ?? job.created_at ?? '');
  const recent = failed.filter(job => !Number.isFinite(when(job)) || now - when(job) <= RECENT_DAYS * 86_400_000);
  return { active, recent, earlier: failed.filter(job => !recent.includes(job)) };
}

const STATUS: Record<string, { text: string; tone: Tone }> = {
  queued: { text: 'Waiting to start', tone: 'quiet' }, running: { text: 'Running', tone: 'progress' }, waiting: { text: 'Waiting', tone: 'waiting' },
  failed: { text: 'Failed', tone: 'alert' },
};

function JobRow({ job, canRetry, busy, onRetry }: { job: IntakeJob; canRetry: boolean; busy: boolean; onRetry: () => void }) {
  const status = STATUS[job.status] ?? { text: job.status, tone: 'quiet' as Tone };
  const reason = plainReason(job.status === 'failed' ? failureParts(job.error_summary).reason : job.status === 'waiting' ? (job.current_message ?? '') : '');
  const day = shortDay(job.updated_at ?? job.created_at);
  return <li className="flex flex-wrap items-start justify-between gap-3 border-b border-[#EEF0F4] py-3 last:border-b-0" data-stage={job.stage} data-status={job.status}>
    <div className="min-w-0 space-y-0.5">
      <p className="text-[13px] font-medium text-[#1B2433]">{stageName(job.stage)}</p>
      <p className={META}>{day ? `${job.status === 'failed' ? 'Failed' : 'Since'} ${day}` : ''}{reason ? `${day ? ' · ' : ''}${reason}` : ''}</p>
    </div>
    <div className="flex items-center gap-2">
      <Pill tone={status.tone}>{status.text}</Pill>
      {canRetry && ['failed', 'waiting'].includes(job.status) && <button type="button" disabled={busy} className={QUIET_BUTTON} onClick={onRetry}>Retry</button>}
    </div>
  </li>;
}

function Processing({ jobs, canAdmin, busy, onRetry }: { jobs: IntakeJob[]; canAdmin: boolean; busy: boolean; onRetry: (job: IntakeJob) => void }) {
  const { active, recent, earlier } = processingRows(jobs);
  const row = (job: IntakeJob) => <JobRow key={job.job_id} job={job} canRetry={canAdmin} busy={busy} onRetry={() => onRetry(job)} />;
  return <section aria-label="Processing" className={`${PANEL} p-5 space-y-2`}>
    <h2 className={HEADING}>Processing</h2>
    {!active.length && !recent.length && <p className="text-[13px] text-[#8B93A3]">Nothing is waiting or running, and nothing failed in the last {RECENT_DAYS} days.</p>}
    {(active.length > 0 || recent.length > 0) && <ul>{active.map(row)}{recent.map(row)}</ul>}
    {earlier.length > 0 && <details><summary className={`cursor-pointer ${TEXT_BUTTON}`}>Show earlier ({earlier.length})</summary><ul className="mt-2">{earlier.map(row)}</ul></details>}
  </section>;
}

/** What a pressed button did, said beside it. */
export function doneText(path: string): string {
  if (path === 'refresh') return 'Collecting new calls and threads now.';
  if (path === 'complete') return 'The current bucket closes once everything in it is ready.';
  const provider = /^connections\/(fathom|slack)\/activate$/.exec(path)?.[1] as keyof typeof PROVIDER_NAMES | undefined;
  if (provider) return `${PROVIDER_NAMES[provider]} is active. New ${provider === 'fathom' ? 'calls' : 'threads'} come in from now on.`;
  return 'Sent to run again.';
}

const safeUrl = (value?: string | null) => value && /^https?:\/\//i.test(value) ? value : undefined;

function SourceDialog({ sourceId, onClose }: { sourceId: string; onClose: () => void }) {
  const navigate = useNavigate();
  const detail = useApiQuery('/intake/sources/{source_id}', { path: { source_id: sourceId } });
  const data = detail.data;
  return <Dialog title={data?.source.title ?? 'Source'} label="Source original and revisions" wide onClose={onClose}>
    {detail.isPending && !detail.error && <LoadingState>Loading the source…</LoadingState>}
    {detail.error && <ErrorState message={detail.error.message} onRetry={() => void detail.refetch()} />}
    {data && <>
      {safeUrl(data.source.source_url) && <a className={`inline-flex items-center gap-1 ${TEXT_BUTTON}`} href={safeUrl(data.source.source_url)} target="_blank" rel="noreferrer">Open the original<ExternalLink size={12} aria-hidden="true" /></a>}
      {!data.revisions.length && !data.assets.length && <p className="text-[#8B93A3]">Nothing has been received for this source yet.</p>}
      {data.revisions.map((r, i) => <article key={r.revision_id} className="rounded-xl border border-[#E6E9F0] bg-white p-4 space-y-2">
        <p className={META}>{i === 0 ? 'Latest' : 'Earlier'} · received {shortDay(r.received_at)}{r.deleted ? ' · deleted at the source' : ''}</p>
        <p className="whitespace-pre-wrap">{r.original_text || 'No readable text in this version.'}</p>
      </article>)}
      {data.assets.map(a => <article key={a.asset_id} className="flex flex-wrap items-center gap-3 rounded-xl border border-[#E6E9F0] bg-white p-3">
        <span className="font-medium">{a.filename}</span>
        {a.raw_artifact && <a className={TEXT_BUTTON} href={`/api/atelier/intake/assets/${a.asset_id}/content`}>Download</a>}
        {a.source_id && <button type="button" className={TEXT_BUTTON} onClick={() => navigate(paths.intakeSource(a.source_id!))}>Its text</button>}
        {safeUrl(a.metadata.permalink) && <a className={TEXT_BUTTON} href={safeUrl(a.metadata.permalink)} target="_blank" rel="noreferrer">Open at the source</a>}
        {a.metadata.error && <p className="basis-full text-[12px] text-[#947021]">{plainReason(failureParts(String(a.metadata.error)).reason)}</p>}
      </article>)}
    </>}
  </Dialog>;
}

/** A received source's state in one word. */
export function sourceState(s: Pick<IntakeSource, 'status' | 'collection_status' | 'extraction_status' | 'indexing_status' | 'error_summary'>): { text: string; tone: Tone } {
  const states = [s.collection_status, s.extraction_status, s.indexing_status, s.status].filter(Boolean) as string[];
  if (s.error_summary || states.includes('failed')) return { text: 'Failed', tone: 'alert' };
  if (['ready', 'completed', 'indexed'].includes(s.indexing_status ?? '') || (!s.indexing_status && ['ready', 'completed'].includes(s.status ?? ''))) return { text: 'Ready', tone: 'approved' };
  return { text: 'Processing', tone: 'progress' };
}

export function IntakeView() {
  const { sourceId, bucketId } = useParams();
  const navigate = useNavigate();
  const invalidate = useInvalidate();
  // What this person may administer comes from GET /me, the same resolution the server checks every action against.
  const canAdmin = useMe().me.can.manage_intake;
  const overview = useApiQuery('/intake/overview', undefined, { refetchInterval: 15_000 });
  // The weekly completion in words when the overview does not carry it: the schedule the sidebar reads, never a fixed day.
  const schedule = useApiQuery('/schedule', undefined, { staleTime: 60_000 });
  const bucket = useApiQuery('/intake/buckets/{bucket_id}', { path: { bucket_id: bucketId ?? '' } }, { enabled: !!bucketId });
  const guard = useGuardedAction(() => overview.refetch());
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<IntakeSearchHit[] | null>(null);
  const [done, setDone] = useState('');
  const [activating, setActivating] = useState<'fathom' | 'slack' | null>(null);
  const [allBuckets, setAllBuckets] = useState(false);
  const data = overview.data;
  const act = (path: string) => { setDone(''); return guard.run(async () => {
    await storageRequest(`/intake/${path}`, 'POST', {});
    setDone(doneText(path));
    await invalidate('/intake/overview', '/intake/buckets/{bucket_id}');
  }); };
  const sources: IntakeSource[] = bucketId ? bucket.data?.sources ?? [] : data?.sources ?? [];
  const error = guard.error || overview.error?.message || (bucketId && bucket.error ? bucket.error.message : '');
  // In the words the rest of the app uses ("Sunday 1 November at 4:00 a.m. Chicago time"), else the server's own words.
  const when = nextCycleWords(schedule.data) || data?.schedule || schedule.data?.text || 'not known yet';
  const buckets = data ? (allBuckets ? data.buckets : data.buckets.slice(0, BUCKETS_SHOWN)) : [];
  const search = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    void guard.run(async () => { setHits(await apiPost('/intake/search', { body: { text: query, k: 20 } })); });
  };
  return <section className="space-y-6 text-[#1B2433]">
    <PageHeading title="Sources" subtitle={`Intake · this week's collection closes ${when}`} actions={canAdmin ? <>
      <button type="button" disabled={guard.busy || !data?.connections.length} title={data?.connections.length ? undefined : 'Activate a connector first'} className={HEADER_QUIET} onClick={() => void act('refresh')}>Collect now</button>
      <button type="button" disabled={guard.busy || !data?.connections.length} title={data?.connections.length ? undefined : 'Activate a connector first'} className={HEADER_QUIET} onClick={() => void act('complete')}>Close the current bucket</button>
    </> : undefined} />
    {/* A refused action (409) is said in its words beside the buttons; nothing on this page is a form to keep. */}
    <StatusLine tone="error">{error || (guard.conflict ? plainReason(guard.conflict.message) : '')}</StatusLine>
    <StatusLine>{done}</StatusLine>
    {overview.isPending && !overview.error && <LoadingState>Loading intake…</LoadingState>}
    {data && <>
      {/* Only Fathom has a card; Slack's connector stays in the API but is not offered here. */}
      <div className="grid gap-4">
        {(['fathom'] as const).map(provider => {
          const connection = data.connections.find(c => c.connection_id === provider);
          const catching = data.requests.filter(r => r.connection_id === provider);
          const failing = !!connection?.error_summary;
          return <article key={provider} className={`${PANEL} p-5 space-y-2`} aria-label={PROVIDER_NAMES[provider]}>
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-editorial text-xl">{PROVIDER_NAMES[provider]}</h2>
              <Pill tone={!connection ? 'quiet' : failing ? 'alert' : 'approved'}>{!connection ? 'Not active' : failing ? 'Needs attention' : 'Collecting'}</Pill>
            </div>
            {connection
              ? <p className={META}>Active since {shortDay(connection.activated_at)}{connection.checkpoint ? ` · collected up to ${shortDay(connection.checkpoint)}` : ''}</p>
              : <p className={META}>Activating starts collecting from now on. Earlier history is not brought in.</p>}
            {failing && <p className="text-[12px] text-[#947021]">{plainReason(failureParts(connection!.error_summary).reason)}</p>}
            {catching.length > 0 && <p className={META}>Catching up on {catching.map(r => `${shortDay(r.window_start)} – ${shortDay(r.window_end)}`).join(', ')}</p>}
            {!connection && canAdmin && <button type="button" disabled={guard.busy} className={QUIET_BUTTON} onClick={() => setActivating(provider)}>Activate {PROVIDER_NAMES[provider]}</button>}
          </article>;
        })}
      </div>

      <section aria-label="Weekly buckets" className={`${PANEL} p-5 space-y-2`}>
        <h2 className={HEADING}>Weekly buckets</h2>
        {!data.buckets.length && <p className="text-[13px] text-[#8B93A3]">Activate a connector to start the first bucket.</p>}
        <ul>{buckets.map(b => <li key={b.bucket_id} className="border-b border-[#EEF0F4] last:border-b-0">
          <Link to={paths.intakeBucket(b.bucket_id)} onClick={() => setHits(null)} aria-current={bucketId === b.bucket_id ? 'page' : undefined}
            className="flex items-center justify-between gap-4 py-2.5 text-[13px] hover:text-[#5070FF]">
            <span>{shortDay(b.starts_at)} – {b.cutoff ? shortDay(b.cutoff) : 'now'}</span>
            <Pill tone={b.status === 'completed' ? 'approved' : 'progress'}>{b.status === 'completed' ? 'Closed' : 'Open'}</Pill>
          </Link></li>)}</ul>
        {data.buckets.length > BUCKETS_SHOWN && <button type="button" className={TEXT_BUTTON} onClick={() => setAllBuckets(!allBuckets)}>{allBuckets ? 'Show fewer' : `Show all ${data.buckets.length}`}</button>}
      </section>

      <section aria-label="Received" className={`${PANEL} p-5 space-y-3`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className={HEADING}>{hits ? 'Search results' : bucketId && bucket.data ? `Received in the bucket of ${shortDay(bucket.data.bucket.starts_at)}` : 'Recently received'}</h2>
          <form className="flex flex-wrap items-center gap-2" onSubmit={search}>
            <SearchBox label="Search ready source text" value={query} onChange={setQuery} placeholder="Search what was received…" />
            {hits && <button type="button" className={TEXT_BUTTON} onClick={() => { setHits(null); setQuery(''); }}>Clear</button>}
            {bucketId && !hits && <Link className={TEXT_BUTTON} to={paths.intake}>All recent sources</Link>}
          </form>
        </div>
        {hits ? <ul>{!hits.length && <li className="text-[13px] text-[#8B93A3]">Nothing received matches.</li>}{hits.map(hit => <li key={hit.chunk_id} className="border-b border-[#EEF0F4] py-3 last:border-b-0">
          <button type="button" className="text-left text-[13px] font-medium hover:underline" disabled={!hit.source_id} onClick={() => hit.source_id && navigate(paths.intakeSource(hit.source_id))}>{hit.title}</button>
          <p className="mt-1 line-clamp-2 text-[12px] text-[#667184]">{hit.chunk_text}</p>
        </li>)}</ul> : <>
          {bucketId && bucket.isPending && !bucket.error && <LoadingState>Loading the bucket…</LoadingState>}
          {!sources.length && !(bucketId && bucket.isPending) && <p className="text-[13px] text-[#8B93A3]">Nothing received here yet.</p>}
          <ul>{sources.map((s, i) => {
            const state = sourceState(s);
            return <li key={`${s.source_id}-${i}`} className="border-b border-[#EEF0F4] last:border-b-0">
              <Link to={paths.intakeSource(s.source_id)} className="flex items-center justify-between gap-4 py-2.5 hover:text-[#5070FF]">
                <span className="min-w-0"><span className="block truncate text-[13px] font-medium">{s.title}</span>
                  <span className={META}>{PROVIDER_NAMES[s.kind as keyof typeof PROVIDER_NAMES] ?? s.kind} · received {shortDay(s.received_at)}</span></span>
                <Pill tone={state.tone}>{state.text}</Pill>
              </Link></li>;
          })}</ul>
        </>}
      </section>

      <Processing jobs={data.jobs} canAdmin={canAdmin} busy={guard.busy} onRetry={job => void act(`jobs/${job.job_id}/retry`)} />
    </>}
    {activating && <ConfirmDialog title={`Activate ${PROVIDER_NAMES[activating]}?`} confirm={`Activate ${PROVIDER_NAMES[activating]}`} busy={guard.busy}
      onCancel={() => setActivating(null)} onConfirm={() => { const provider = activating; setActivating(null); void act(`connections/${provider}/activate`); }}>
      <p>The system starts collecting new {activating === 'fathom' ? 'calls' : 'threads'} from {PROVIDER_NAMES[activating]} from now on. Earlier history is not brought in, and collection cannot be switched off here.</p>
    </ConfirmDialog>}
    {sourceId && <SourceDialog key={sourceId} sourceId={sourceId} onClose={() => navigate(bucketId ? paths.intakeBucket(bucketId) : paths.intake)} />}
  </section>;
}
