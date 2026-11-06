import React, { useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import type { BriefWriteResult, PackSummaryV2, StoredBrief } from '../api/types';
import { apiPost } from '../api/routes';
import { useInvalidate } from '../api/query';
import { paths } from '../app/routes';
import { productionChanged, requestId } from '../utils/production';
import { StateLine, button, primary } from './packParts';
import { packLeft } from './studio/PackCard';
import { TAKES } from './studio/GenerationTime';
import { ActionError, useGuardedAction } from './shared/conflict';

/* The Gate 2 hand-over (NP.F3; the content-packs plan, sections 4.1 and 5.7): approving a v4 brief with packs on starts its
   content pack (the decision answers `pack_run`, or why none started in `pack_note`), and the brief page then shows the
   pack's state and a link to it. On a reload the pack is found by the brief (GET /packs?brief_id=...). A person who may
   create packs can create one for an approved v4 brief that has none, or try a failed one again. */

/** What the approval answered about the pack it started. */
export type HandOver = Pick<BriefWriteResult, 'pack_run' | 'pack_note'>;

export const isV4Brief = (brief: Pick<StoredBrief, 'schema_version'>) => brief.schema_version === 'brief_document_v4';

/** What follows approval, in one line (S.F2): with packs off the approved brief is the final output; a v4 brief's approval
    creates its content pack; an earlier contract is re-developed as v4 to get one (section 4.2). */
export function handoverNote(brief: Pick<StoredBrief, 'approval_status' | 'schema_version'>, packsEnabled: boolean): string {
  if (!packsEnabled) return brief.approval_status === 'approved'
    ? 'Approved. No content pack is generated: content packs are switched off, so this brief is the final output.'
    : 'No content pack will be generated: content packs are switched off.';
  if (!isV4Brief(brief)) return 'This brief is in an earlier format: develop the angle again to get a content pack.';
  if (brief.approval_status === 'approved') return 'Approved. Its content pack is below.';
  if (brief.approval_status === 'rejected') return 'Rejected: no content pack is made from this version.';
  return 'Approving this brief creates its content pack.';
}

/** The pack panel on an approved v4 brief's page. `packs` is the brief's current packs (newest first), `started` what the
    approval answered, `canCreate` whether this person may create or retry one. */
export function PackHandover({ brief, packs, loading, started, canCreate }: {
  brief: StoredBrief; packs: PackSummaryV2[]; loading: boolean; started?: HandOver; canCreate: boolean;
}) {
  const navigate = useNavigate();
  const invalidate = useInvalidate();
  const pending = useRef<{ key: string; id: string } | null>(null);
  const guard = useGuardedAction();
  const pack = packs[0];
  const run = started?.pack_run ?? null;
  const startedId = run?.pack_id ?? null;
  const failed = !!run && (run.status === 'failed' || !!run.error) && !startedId;
  const create = () => guard.run(async () => {
    const key = brief.brief_id + brief.content_hash;
    if (pending.current?.key !== key) pending.current = { key, id: requestId() };
    const result = await apiPost('/briefs/{brief_id}/pack', { path: { brief_id: brief.brief_id }, body: { request_id: pending.current.id, expected_brief_hash: brief.content_hash } });
    pending.current = null;
    productionChanged();
    await invalidate('/packs');
    if (result.error) throw new Error(result.error);
    if (result.pack_id) navigate(paths.studioPack(result.pack_id));
  });
  return <section aria-label="Content pack" className="space-y-3 rounded-xl border border-[#D1DBFF] bg-[#F7F9FF] p-4">
    <h3 className="font-semibold text-[#173354]">Content pack</h3>
    {pack ? <>
      <p className="font-editorial text-xl text-[#173354]">{pack.title}</p>
      <StateLine pack={pack} />
      <p className="text-sm text-slate-600">{pack.pieces.length} pieces{packLeft(pack) ? ` · ${packLeft(pack)}` : ''}</p>
      <div className="flex flex-wrap gap-2">
        <Link className={primary} to={paths.studioPack(pack.pack_id)}>Open the content pack</Link>
        {pack.state === 'waiting' && canCreate && <button type="button" className={button} disabled={guard.busy} onClick={() => void create()}>Try the content pack again</button>}
      </div>
    </> : startedId ? <>
      <p className="text-sm">The content pack is being made from this brief. It takes {TAKES.pack}.</p>
      <Link className={primary} to={paths.studioPack(startedId)}>Open the content pack</Link>
    </> : loading ? <p role="status" className="text-sm text-slate-500">Looking for this brief's content pack…</p>
      : <p className="text-sm">No content pack yet.</p>}
    {failed && <p role="alert" className="text-sm text-amber-900">The content pack did not start{run?.error ? `: ${run.error}` : ''}. The approval stands.</p>}
    {started?.pack_note && <p className="text-sm text-slate-600">{started.pack_note}</p>}
    {!pack && !startedId && !loading && canCreate && <button type="button" className={primary} disabled={guard.busy} onClick={() => void create()}>Create content pack</button>}
    <ActionError message={guard.error || guard.conflict?.message || ''} />
  </section>;
}
