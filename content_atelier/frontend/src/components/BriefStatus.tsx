import React from 'react';
import { Link } from 'react-router-dom';
import type { AngleResearch as AngleResearchAnswer } from '../api/schema';
import { useApiQuery, useInvalidate } from '../api/query';
import { storageRequest } from '../utils/weeklyStorage';
import { paths } from '../app/routes';
import { FailureText, StageProgress, words, type JobRowLike } from './shared/JobProgress';
import { ConflictNotice, useGuardedAction } from './shared/conflict';
import { TAKES, TimeNote } from './studio/GenerationTime';

/* A developed card's brief (S.F4): its status, the reason a stage failed and a retry, and the link to the brief.
   Shared by the card screen (E.F2) and the earlier angle screen. */

const button = 'rounded-lg border border-[#C4CBD7] px-3 py-2 text-sm disabled:opacity-40';

/** Deep links between a card and its brief (S.F4): /studio/angles/<week>/<angle> and /studio/briefs/<brief>. */
export const angleLink = paths.angle;
export const briefLink = paths.brief;

const ACTIVE = ['queued', 'running'];

/** What the panel reads of the research answer; the job rows are the progress contract (1.F2). */
export type AngleResearchStatus = Pick<AngleResearchAnswer, 'status' | 'error_summary' | 'brief_id'>
  & Partial<Pick<AngleResearchAnswer, 'waiting_reason' | 'mode'>> & { jobs: JobRowLike[] };

// What each brief stage does, in the reviewer's words (R50).
const STAGES: Record<string, string> = {
  brief_prepare: 'Preparing the research', brief_plan: 'Planning the research', brief_research: 'Gathering evidence from the calls',
  brief_grade: 'Checking the evidence', brief_write: 'Writing the brief', brief_review: 'Reviewing the draft', brief_repair: 'Fixing the draft',
};
const STATUS: Record<string, string> = { queued: 'waiting to start', running: 'in progress', completed: 'done', failed: 'failed', waiting: 'waiting' };

export function AngleResearchPanel({ data, error, busy, canRetry, onRetry, onRetryStage }: {
  data: AngleResearchStatus | null; error: string; busy: boolean; canRetry: boolean; onRetry: () => void; onRetryStage?: (jobId: string) => void;
}) {
  // A brief that could not be queued has no jobs; its reason lives on the run (S.B13).
  const unqueued = data?.status === 'failed' && !data.jobs.length;
  return <details open={data?.status === 'failed'}><summary>The brief · {STATUS[data?.status || ''] || words(data?.status || 'loading')}</summary>{error && <p role="alert">{error}</p>}
    {ACTIVE.includes(data?.status ?? '') && <TimeNote className="mt-2">The brief takes {TAKES.brief} to write. You can close this and come back.</TimeNote>}
    {data?.status === 'failed' && data.error_summary && <div role="alert" className="text-red-800"><FailureText prefix="Brief generation failed: " summary={data.error_summary} /></div>}
    {/* A spent standing budget (6.B3): the brief waits, and starts by itself when the budget renews or is raised (4.B1). */}
    {data?.waiting_reason && <p role="status" className="text-amber-800">The brief is waiting for budget: {data.waiting_reason}</p>}
    {data?.jobs.map(j => <div key={j.job_id || j.stage}><StageProgress job={j} stageNames={STAGES} statusNames={STATUS} showUpdated={false} />
      {['failed', 'waiting'].includes(j.status) && canRetry && j.job_id && onRetryStage && <button className={button} disabled={busy} onClick={() => onRetryStage(j.job_id!)}>Try this step again</button>}</div>)}
    {unqueued && canRetry && <button className={button} disabled={busy} onClick={onRetry}>Retry brief generation</button>}
    {data?.brief_id && <p><Link className="underline" to={briefLink(data.brief_id)}>Open the brief</Link></p>}
  </details>;
}

export function AngleResearch({ angleId, canRetry }: { angleId: string; canRetry: boolean }) {
  const research = useApiQuery('/angles/{angle_id}/research', { path: { angle_id: angleId } }, {
    refetchInterval: data => ACTIVE.includes(data?.status ?? '') ? 8_000 : 30_000,
  });
  const invalidate = useInvalidate();
  const guard = useGuardedAction(() => research.refetch());
  const act = (path: string) => guard.run(async () => {
    await storageRequest(path, 'POST', {});
    await invalidate('/angles/{angle_id}/research', '/briefs');
  });
  return <>
    <ConflictNotice conflict={guard.conflict} onReload={() => void guard.reloadLatest()} onDismiss={guard.clear} />
    <AngleResearchPanel data={research.data ?? null} error={guard.error || research.error?.message || ''} busy={guard.busy} canRetry={canRetry}
      onRetry={() => void act(`/angles/${angleId}/brief/retry`)} onRetryStage={jobId => void act(`/jobs/${jobId}/retry`)} />
  </>;
}
