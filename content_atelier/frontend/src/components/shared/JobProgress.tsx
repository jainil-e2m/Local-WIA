import React from 'react';
import type { JobRow } from '../../api/schema';

/* Staged progress read from job rows (plan 1.F2, "Job rows are the progress contract"). A stage shows its `status`, its
   `current_step` or message, `completed_units` of `total_units`, and when the row was last `updated_at`. Nothing here
   estimates progress from elapsed time: with no unit counts there is no bar, only the stage and its words. */

/** The part of a job row the progress display reads: the stage and its status, and whatever else the row reports. */
export type JobRowLike = Pick<JobRow, 'stage' | 'status'>
  & Partial<Pick<JobRow, 'job_id' | 'current_step' | 'current_message' | 'completed_units' | 'total_units' | 'error_summary' | 'updated_at' | 'heartbeat_at'>>;

export const words = (s: string) => s.replaceAll('_', ' ');
export const DEFAULT_STATUS_WORDS: Record<string, string> = { queued: 'waiting to start', running: 'in progress', completed: 'done', failed: 'failed', waiting: 'waiting' };

/** The row's unit counts as a share of 0 to 1, or null when the row does not report them (no bar is drawn then). */
export function unitShare(job: Pick<JobRowLike, 'completed_units' | 'total_units'>): number | null {
  const { completed_units: done, total_units: total } = job;
  if (typeof done !== 'number' || typeof total !== 'number' || !(total > 0) || done < 0) return null;
  return Math.min(1, done / total);
}

/** A stored failure as the reviewer reads it (R50): the worker puts the reason in words on the first line (a provider out of
    credit, a worker that stopped) and the technical detail for the team after it. */
export function failureParts(summary: string | null | undefined): { reason: string; detail: string } {
  const [reason = '', ...rest] = (summary || '').split('\n');
  return { reason, detail: rest.join('\n').trim() };
}

/** A failure's reason, with its detail for the team folded away beneath it. */
export function FailureText({ summary, prefix = '' }: { summary: string; prefix?: string }) {
  const { reason, detail } = failureParts(summary);
  return <>{prefix}{reason}{detail && <details className="text-xs text-slate-600"><summary className="cursor-pointer">Details for the team</summary>
    <p className="whitespace-pre-wrap">{detail}</p></details>}</>;
}

/** The step the worker reports now: a failed row shows its error's reason before its last message. */
export function stepText(job: JobRowLike): string {
  if (job.status === 'failed') return failureParts(job.error_summary).reason || job.current_message || job.current_step || '';
  return job.current_message || job.current_step || '';
}

export function StageProgress({ job, stageNames = {}, statusNames = DEFAULT_STATUS_WORDS, showUpdated = true }: {
  job: JobRowLike; stageNames?: Record<string, string>; statusNames?: Record<string, string>; showUpdated?: boolean;
}) {
  const share = unitShare(job);
  const step = stepText(job);
  const updated = job.updated_at || job.heartbeat_at;
  const stage = stageNames[job.stage] || words(job.stage);
  const status = statusNames[job.status] || words(job.status);
  return <div data-stage={job.stage} data-status={job.status} className="text-sm space-y-1">
    <p><strong>{stage}</strong> · {status}{step ? ` · ${step}` : ''}</p>
    {share !== null && <p className="flex items-center gap-2">
      <progress className="w-40" max={job.total_units!} value={job.completed_units!} aria-label={`${stage}: ${job.completed_units} of ${job.total_units}`} />
      <span className="tabular-nums">{job.completed_units} of {job.total_units}</span>
    </p>}
    {showUpdated && updated && <p className="text-xs text-slate-500">Last update <time dateTime={updated}>{new Date(updated).toLocaleTimeString()}</time></p>}
  </div>;
}
