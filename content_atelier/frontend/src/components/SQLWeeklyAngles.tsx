import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import type { ComparisonReport, StoredAngle, StrategistCard as Card, WeekReview } from '../api/schema';
import type { PackSummaryV2, StoredBrief } from '../api/types';
import { useMomentEvidence } from '../api/evidence';
import { queryKey, useApiQuery, useInvalidate } from '../api/query';
import { storageRequest } from '../utils/weeklyStorage';
import { CardReview, ConsideredItem } from './CardReview';
import { AngleResearch } from './BriefStatus';
import { StageProgress } from './shared/JobProgress';
import { ActionError, ConflictNotice, useGuardedAction } from './shared/conflict';
import { focusKey, useWriteFeedback, type WriteTarget } from './shared/a11y';
import { EmptyState, ErrorState, LoadingState } from './shared/states';
import { ArchivedWeekNote, useWeekList } from './shared/WeekPicker';
import { paths, parseStudioLink } from '../app/routes';
import { useMe } from '../utils/me';
import { isCycleOverview, useCycleSummary, useFeatureFlags } from '../utils/workspace';
import { AngleCard } from './studio/AngleCard';
import { cardOfferText, cardSearchText } from './studio/CardRationale';
import { CardGrid, EmptyStage, Fold, StageSection, StagePanel, StudioModal, cardDay, matches, type OfferFilter } from './studio/parts';
import { cardGroup, currentCards, currentPacks, useStudioContext, weekBriefsArgs, weekPacksArgs } from './studio/studioWeek';
import { Select } from './ThemedSelect';
import { TAKES } from './studio/GenerationTime';
export { AngleResearchPanel, angleLink, briefLink } from './BriefStatus';
export { parseStudioLink };

const names = ['audience', 'tension', 'argument', 'take', 'mechanism', 'reader_decision'] as const;
const scoreNames = ['grounding', 'source_relevance', 'audience_fit', 'specificity', 'editorial_usefulness'] as const;
const button = 'rounded-lg border border-[#C4CBD7] px-3 py-2 text-sm disabled:opacity-40';
const label = (s: string) => s.replaceAll('_', ' ');

/** What the old Gate 1 screen may offer for an angle without sending a request the server refuses (S.F1).

Legacy angles keep edit, rescore, approve and reject. Strategic opportunities and strategist cards are
edited in their own fields (the card screen, E.F2), so the legacy edit and rescore forms are disabled with
the reason. Cards are approved on the card screen, which records the verify-before-publishing
acknowledgements. Comparison angles can be rejected. */
export function gateOneActions(a: Pick<StoredAngle, 'content_body' | 'base_score' | 'has_replacement' | 'approval_status' | 'can_approve' | 'can_edit' | 'can_reject'>) {
  const card = !!a.content_body.card;
  const strategic = !!a.content_body.strategy;
  const editReason = card ? 'Strategist cards are edited on the card screen, in their own fields.'
    : strategic ? 'Strategic opportunities are edited in their own fields on the card screen; this legacy form would be refused.'
    : a.has_replacement ? 'A newer version of this angle exists.' : a.can_edit === false ? 'Editing needs an editor or approver role.' : null;
  return {
    edit: editReason === null, editReason,
    rescore: !card && !strategic && a.base_score === null && a.can_edit !== false,
    approve: !card && !!a.can_approve,
    approveReason: card ? 'Approve cards on the card screen, which records the verify-before-publishing acknowledgements.' : null,
    reject: a.approval_status === 'pending' && a.can_reject !== false && !a.has_replacement,
  };
}

const RUNNING = ['queued', 'running'];

/** What a Gate 1 write did, in a sentence for the live region (6.F6). */
export function angleWriteMessage(path: string, method = 'POST', body?: unknown): string {
  if (method === 'PATCH') return 'Saved as a new version of the card.';
  if (/\/considered\/\d+\/revive$/.test(path)) return 'Revived as a card. It is checked against earlier content before it can be developed.';
  if (/\/decision$/.test(path)) return (body as { disposition?: string } | undefined)?.disposition === 'develop' ? `Approved. Its brief is being written, which takes ${TAKES.brief}.` : 'Decision saved.';
  if (/\/refresh$/.test(path)) return `Refresh started. The new version shows here in ${TAKES.angleRefresh}.`;
  if (/\/context$/.test(path)) return 'Added to the card.';
  if (/\/stance$/.test(path)) return 'Public stance confirmed.';
  if (/\/quality$/.test(path)) return 'Quality assessment saved.';
  if (/\/retry$/.test(path)) return 'Trying that step again.';
  if (/\/reassess$/.test(path)) return 'Reassessing the saved angles.';
  if (/\/runs$/.test(path)) return `Started. This takes ${TAKES.week}, and this week refreshes by itself while it runs.`;
  return 'Saved.';
}

/** The newest version of an angle: an edit or a refresh makes a new angle that names the one it replaces. The week lists a
    replaced version only if the strategist chose it, so the version an open dialog was showing can leave the list. */
export function latestVersion(angles: Pick<StoredAngle, 'angle_id' | 'supersedes_id' | 'content_hash'>[], angleId: string) {
  let current = angles.find(a => a.angle_id === angleId) ?? angles.find(a => a.supersedes_id === angleId);
  for (let step = 0; current && step < angles.length; step++) {
    const id: string = current.angle_id;
    const next = angles.find(a => a.supersedes_id === id);
    if (!next) break;
    current = next;
  }
  return current ?? null;
}

/** The focus key of an angle's heading at one version. */
export const angleFocusKey = (a: Pick<StoredAngle, 'angle_id' | 'content_hash'>) => `angle:${a.angle_id}:${a.content_hash}`;

/** Writes on a week's cards (Gate 1), what they did and where focus goes after them (6.F6): shared by the Weekly Studio and
    Previous Concepts. `perform` resolves to true when the write succeeded, so a form can clear itself; a failure or conflict is
    shown by the guard. A card is keyed by its version, so a write that changes it replaces the control the person pressed:
    focus moves to the heading of the card's newest version, or of the considered idea, or to `target` when the caller names
    one (a card in the grid); a week-wide action gives focus back to its own button once it is enabled again. */
export function useAngleActions(week: string, refetch: () => unknown) {
  const invalidate = useInvalidate();
  const guard = useGuardedAction(refetch);
  const client = useQueryClient();
  const feedback = useWriteFeedback();
  const writeTarget = (path: string, origin: Element | null): WriteTarget => {
    const angleId = /^\/angles\/([^/]+)/.exec(path)?.[1];
    if (angleId) {
      const fresh = client.getQueryData<WeekReview>(queryKey('/weeks/{week_id}', { path: { week_id: week } }));
      const latest = latestVersion(fresh?.angles ?? [], angleId);
      return latest ? focusKey(angleFocusKey(latest)) : null;
    }
    const considered = /^\/weeks\/([^/]+)\/considered\/(\d+)\//.exec(path);
    if (considered) return focusKey(`considered:${considered[1]}:${considered[2]}`);
    return origin instanceof HTMLElement ? origin : null;
  };
  const perform: AnglePerform = async (path, method = 'POST', body, options = {}) => {
    const origin = document.activeElement;
    const ok = (await guard.run(async () => {
      await storageRequest(path, method, body);
      await invalidate('/weeks/{week_id}', '/weeks', '/briefs', '/angles/{angle_id}/research', '/seeds', '/summary');
      return true;
    })) === true;
    if (ok) feedback.announce(options.message ?? angleWriteMessage(path, method, body), options.target ? focusKey(options.target) : writeTarget(path, origin));
    return ok;
  };
  return { guard, feedback, perform, busy: guard.busy };
}
export type AnglePerform = (path: string, method?: string, body?: unknown, options?: { target?: string; message?: string }) => Promise<boolean>;

/** The Content Angle step of the Weekly Studio for a week (`/studio/angles/:weekId`), as the 20 October mockup: the cards
    awaiting approval in two columns, a short folded note on why these ideas, the approved cards linked to their briefs, and the
    held, skipped and considered ideas folded away below. When the URL names a card (`/studio/angles/:weekId/:angleId`) its
    full card screen opens in the review dialog. The week's machinery (calls, cycles, budgets, seeds, monitoring, processing)
    is in the folded "Cycle details" at the bottom, for an approver or an editor. Without a week in the URL the latest week is
    shown at its own URL. */
export function SQLWeeklyAngles() {
  const { weekId, angleId } = useParams();
  const navigate = useNavigate();
  // What this person may do (0.B9): decisions need the approver role, the team tools and seeds the editor role. Nothing is
  // offered until the answer arrives, so no one is shown a control the server would refuse (S.F1).
  const { me } = useMe();
  const canDecide = me.can.decide, canEdit = me.can.edit_cards;
  const flags = useFeatureFlags();
  const { weeks, latest } = useWeekList();
  const week = weekId ?? latest;
  useEffect(() => {
    if (!weekId && week) navigate(paths.week(week), { replace: true });
  }, [weekId, week, navigate]);
  // The poll refreshes the data only: a message from the reviewer's last action stays until their next one.
  const reviewQuery = useApiQuery('/weeks/{week_id}', { path: { week_id: week } }, {
    enabled: !!week,
    refetchInterval: data => data?.runs.some(r => RUNNING.includes(r.status)) ? 8_000 : 30_000,
  });
  const briefs = useApiQuery('/briefs', weekBriefsArgs(week), { enabled: !!week });
  const packs = useApiQuery('/packs', weekPacksArgs(week), { enabled: !!week && flags.packs });
  const review = reviewQuery.data?.week.week_id === week ? reviewQuery.data : undefined;
  const { query, offer } = useStudioContext();
  const actions = useAngleActions(week, () => reviewQuery.refetch());
  const loadError = weeks.error?.message || (reviewQuery.data ? '' : reviewQuery.error?.message || '');
  return <section aria-label="Content angles" className="space-y-8">
    {actions.feedback.region}
    {/* A write from the review dialog says its refusal or conflict inside the dialog; from the cards, here above them. */}
    {!angleId && <ConflictNotice conflict={actions.guard.conflict} onReload={() => void actions.guard.reloadLatest()} onDismiss={actions.guard.clear} />}
    {!angleId && <ActionError message={actions.guard.error} />}
    {loadError && <ErrorState message={loadError} onRetry={() => { void weeks.refetch(); void reviewQuery.refetch(); }} />}
    {weeks.isPending && !loadError && <LoadingState>Loading stored weeks…</LoadingState>}
    {weeks.data && !weeks.data.length && <EmptyState>No week has been stored yet. Weeks appear here once their calls are admitted.</EmptyState>}
    {week && !review && !loadError && <LoadingState>Loading this week…</LoadingState>}
    {review && <>
      <WeekAngles review={review} week={week} briefs={briefs.data?.items} packs={packs.data?.items} query={query} offer={offer}
        canDecide={canDecide} busy={actions.busy} perform={actions.perform} onReview={id => navigate(paths.angle(week, id))} />
      {week === latest && <EarlierWaiting week={week} />}
      {angleId && <AngleReviewModal review={review} week={week} angleId={angleId} briefs={briefs.data?.items} packs={packs.data?.items}
        canDecide={canDecide} busy={actions.busy} perform={actions.perform} guard={actions.guard} onClose={() => navigate(paths.week(week))} />}
    </>}
  </section>;
}

/** The cards waiting in earlier weeks, from Home's summary: one line with the way to Previous Concepts. */
function EarlierWaiting({ week }: { week: string }) {
  const summary = useCycleSummary();
  if (!isCycleOverview(summary.data)) return null;
  const earlier = summary.data.waiting.cards_at_gate_1.by_week.filter(w => w.week_id !== week).reduce((n, w) => n + w.n, 0);
  if (!earlier) return null;
  return <p className="text-[12px] text-[#8B93A3]">{earlier} more {earlier === 1 ? 'angle waits' : 'angles wait'} for approval in earlier weeks · <Link className="text-[#5070FF] font-medium" to={paths.previous}>Previous Concepts <span aria-hidden="true">→</span></Link></p>;
}

const CONSIDERED_SHOWN = 5;

/** A week's cards in the mockup's sections. Used by the Weekly Studio and by each week of Previous Concepts. */
export function WeekAngles({ review, week, briefs, packs, query = '', offer = 'all', canDecide, busy, perform, onReview }: {
  review: WeekReview; week: string; briefs?: StoredBrief[]; packs?: PackSummaryV2[]; query?: string; offer?: OfferFilter;
  canDecide: boolean; busy: boolean; perform: AnglePerform; onReview: (angleId: string) => void;
}) {
  const roster = review.roster || [];
  const all = currentCards(review);
  const cards = all.map(a => ({ angle: a, card: a.content_body.card as unknown as Card }))
    .filter(({ card }) => matches(cardSearchText(card), cardOfferText(card), query, offer))
    .sort((x, y) => byRank(x.angle, y.angle));
  const waiting = cards.filter(c => cardGroup(c.angle) === 'waiting');
  const approved = cards.filter(c => cardGroup(c.angle) === 'approved');
  const other = cards.filter(c => cardGroup(c.angle) === 'other');
  const considered = review.selection?.considered_not_selected ?? [];
  const [showAll, setShowAll] = useState(false);
  const filtering = !!query.trim() || offer !== 'all';
  const briefFor = (angleId: string) => briefs?.find(b => b.angle_id === angleId);
  const packFor = (brief?: StoredBrief) => brief ? currentPacks(packs).find(p => p.source_brief_id === brief.brief_id) : undefined;
  const render = ({ angle, card }: { angle: StoredAngle; card: Card }, compact = false) => {
    const brief = briefFor(angle.angle_id);
    return <AngleCard key={angle.angle_id + angle.content_hash} angle={angle} card={card} week={week} roster={roster} brief={brief} pack={packFor(brief)}
      canDecide={canDecide} busy={busy} perform={perform} onReview={() => onReview(angle.angle_id)} compact={compact} />;
  };
  const notReady = all.length ? '' : review.jobs.some(j => j.stage === 'angle_generation' && j.status === 'completed')
    ? 'This week produced no usable ideas.' : 'This week’s ideas are not ready yet.';
  return <div className="space-y-8">
    <ArchivedWeekNote week={review.week} />
    <StageSection title="Awaiting approval" count={waiting.length} label="Angles awaiting approval" description="Review at your pace. Unused angles stay available in their original week.">
      {waiting.length ? <CardGrid>{waiting.map(c => render(c))}</CardGrid>
        : <EmptyStage>{filtering ? 'No angles match this view.' : notReady || 'No angles awaiting approval.'}</EmptyStage>}
    </StageSection>
    <StageSection title="Approved" count={approved.length} label="Approved angles" description="Your approved angles remain here, linked to their briefs.">
      {approved.length ? <CardGrid>{approved.map(c => render(c))}</CardGrid>
        : <EmptyStage>{filtering ? 'No angles match this view.' : 'Approved angles will be retained here.'}</EmptyStage>}
    </StageSection>
    {(other.length > 0 || considered.length > 0) && <Fold label="Other ideas this week" summary={`Other ideas this week (${other.length + considered.length})`}>
      {other.length > 0 && <CardGrid>{other.map(c => render(c, true))}</CardGrid>}
      {considered.length > 0 && review.selection && <section aria-label="Considered and not chosen" className="space-y-3">
        <h3 className="font-editorial text-lg text-[#1B2433]">Considered, not chosen ({considered.length})</h3>
        <ul className="divide-y divide-[#EEF0F4] rounded-xl border border-[#E6E9F0] bg-white">{(showAll ? considered : considered.slice(0, CONSIDERED_SHOWN)).map(idea => <li key={idea.index} className="px-4 py-3">
          <ConsideredItem idea={idea} weekId={review.week.week_id} selection={review.selection!} busy={busy} perform={perform} canDecide={canDecide} />
        </li>)}</ul>
        {considered.length > CONSIDERED_SHOWN && <button type="button" className="text-[12px] font-medium text-[#5070FF] hover:underline" onClick={() => setShowAll(v => !v)}>
          {showAll ? 'Show fewer' : `Show all ${considered.length}`}</button>}
      </section>}
    </Fold>}
  </div>;
}

/** The review dialog of one card: the whole card screen (E.F2) inside the mockup's "Content Angle" panel, with the stage tabs
    leading to its brief and its content pack. The URL names the card, so a refresh or a shared link opens it again. */
export function AngleReviewModal({ review, week, angleId, briefs, packs, canDecide, busy, perform, guard, onClose }: {
  review: WeekReview; week: string; angleId: string; briefs?: StoredBrief[]; packs?: PackSummaryV2[]; canDecide: boolean; busy: boolean;
  perform: AnglePerform; guard?: ReturnType<typeof useAngleActions>['guard']; onClose: () => void;
}) {
  const navigate = useNavigate();
  const newest = latestVersion(review.angles, angleId);
  const a = newest ? review.angles.find(x => x.angle_id === newest.angle_id) : undefined;
  // The URL follows the version on screen, so a second edit or refresh finds its way too.
  const moved = a && a.angle_id !== angleId ? a.angle_id : null;
  useEffect(() => { if (moved) navigate(paths.angle(week, moved), { replace: true }); }, [moved, week, navigate]);
  if (!a) return <StudioModal title="This angle" onClose={onClose}><EmptyState>A newer version of this angle has replaced it. Close this and open the angle from the week.</EmptyState></StudioModal>;
  const card = a.content_body.card as unknown as Card | undefined;
  const brief = briefs?.find(b => b.angle_id === a.angle_id);
  const pack = brief ? currentPacks(packs).find(p => p.source_brief_id === brief.brief_id) : undefined;
  const title = card?.title ?? a.content_body.title;
  const approved = a.approval_status === 'approved';
  return <StudioModal title={title} label={`Review angle: ${title}`} onClose={onClose} footerNote={`Recorded: ${cardDay(a.first_generated_at)}`}
    tabs={[
      { id: 'angle', label: 'Content Angle', selected: true },
      { id: 'brief', label: 'Content Brief', disabled: !brief, title: brief ? undefined : 'The brief is written once the angle is approved.', onSelect: () => brief && navigate(`${paths.brief(brief.brief_id)}?week=${encodeURIComponent(week)}`) },
      { id: 'pack', label: 'Content Pack', disabled: !pack, title: pack ? undefined : 'The content pack is made once the brief is approved.', onSelect: () => pack && navigate(paths.studioPack(pack.pack_id)) },
      { id: 'schedule', label: 'Schedule', disabled: true, title: 'Publishing dates are proposed with the week’s content packs.' },
    ]}>
    {guard && <ConflictNotice conflict={guard.conflict} onReload={() => void guard.reloadLatest()} onDismiss={guard.clear} />}
    {guard && <ActionError message={guard.error} />}
    <StagePanel step={1} title="Content Angle" status={approved ? <span className="text-emerald-700">Approved</span> : cardGroup(a) === 'waiting' ? <span className="text-amber-700">Awaiting approval</span> : undefined}>
      {card ? <CardReview angle={a} card={card} roster={review.roster || []} rubric={review.rubric} busy={busy} perform={perform} canDecide={canDecide} bare />
        : <AngleReview angle={a} busy={busy} perform={perform} />}
      {/* Its brief's progress, the reason it stopped and the retry; nowhere else shows a brief that never arrived. */}
      {card && approved && <div className="mt-4 rounded-xl border border-[#E6E9F0] bg-white p-4 text-[13px]"><AngleResearch angleId={a.angle_id} canRetry={canDecide} /></div>}
    </StagePanel>
  </StudioModal>;
}

// Cards in rank order; earlier angles keep their saved order after them.
const byRank = (x: StoredAngle, y: StoredAngle) => (rankOf(x) ?? 1e9) - (rankOf(y) ?? 1e9);
const rankOf = (a: StoredAngle) => (a.content_body.card as { rank?: number } | undefined)?.rank;

export function AngleReview({ angle: a, busy, perform }: { angle: StoredAngle; busy: boolean; perform: (path: string, method?: string, body?: unknown) => Promise<unknown> }) {
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(a.content_body);
  const [cta, setCta] = useState(a.selected_cta?.text || '');
  const [note, setNote] = useState('');
  const [ack, setAck] = useState(false);
  const [showing, setShowing] = useState(false);
  const { evidence, error: evidenceError, retry } = useMomentEvidence(a.moment_ids, showing);
  const [scores, setScores] = useState(Object.fromEntries(scoreNames.map(n => [n, 4])) as Record<typeof scoreNames[number], number>);
  const [reason, setReason] = useState('');
  const matches = a.matching_result?.history || [];
  const flags = a.matching_result?.current_batch_flags || [];
  const comparison = a.workflow === 'historical_comparison_v1' || a.matching_result?.workflow === 'historical_comparison_v1';
  const actions = gateOneActions(a);
  const ready = actions.approve;
  return <article id={`angle-${a.angle_id}`} className="rounded-2xl bg-white border p-5 space-y-4">
    <div><h2 className="font-editorial text-2xl" tabIndex={-1} data-focus-key={angleFocusKey(a)}>{a.content_body.title}</h2><p className="text-sm mt-1">{label(a.selection_status)} · {label(a.approval_status)} · score {a.adjusted_score === null ? 'awaiting matching' : Number(a.adjusted_score).toFixed(2)}</p></div>
    {comparison && <p className="text-sm">{a.supersedes_id ? `Refinement or edit of ${a.supersedes_id}` : `Original family ${a.angle_id}`} · baseline quality {a.base_score === null ? 'pending' : Number(a.base_score).toFixed(2)}. Freshness-adjusted score is for ranking. {ready ? 'Selected by the configured approval policy.' : 'Approval awaits threshold selection or current eligibility.'}</p>}
    <dl className="space-y-2">{names.map(n => <div key={n}><dt className="text-xs uppercase tracking-wide text-slate-500">{label(n)}</dt><dd>{a.content_body[n]}</dd></div>)}</dl>
    {a.content_body.inference && <p><strong>Editorial inference:</strong> {a.content_body.inference}</p>}
    <p className="text-sm"><strong>Qualifications:</strong> {a.content_body.qualifiers.join(' · ') || 'None recorded'}</p>
    <p className="text-sm"><strong>Handling notes:</strong> {a.content_body.risks.join(' · ')}</p>
    <div className="text-sm rounded-lg bg-slate-50 p-3">
      {!a.matching_result || !['complete', 'comparison_complete', 'comparison_initial'].includes(a.matching_result.status) ? <p>Matching is incomplete. This angle is awaiting compatible embeddings or reassessment.</p> : <>
        <p>{a.matching_result.history_count} historical arguments checked · repetition risk {((a.matching_result.historical_risk || 0) * 100).toFixed(1)}%</p>
        {comparison && a.matching_result.max_historical_cosine != null && <p>Maximum historical cosine: {a.matching_result.max_historical_cosine.toFixed(6)} (display rounding only).</p>}
        {!!a.matching_result.partial_history_ids?.length && <p className="text-amber-800">History includes the explicitly accepted partial Week 1 baseline.</p>}
        {matches.length > 0 && <details className="mt-2"><summary>Closest historical arguments</summary><MatchList matches={matches.slice(0, 5)} />{matches.length > 5 && <details><summary>Show all comparisons ({matches.length})</summary><MatchList matches={matches} /></details>}</details>}
      </>}
      {flags.length > 0 && <p className="mt-2 text-amber-800">Potential overlap with {flags.length} current-batch angle(s). Review the distinct treatment before approval.</p>}
    </div>
    <button className={button} onClick={() => { if (showing) retry(); setShowing(true); }}>Inspect original evidence</button>
    {evidenceError && <p role="alert">{evidenceError}</p>}
    {evidence.map((m, i) => <details key={i}><summary>{m.moment.moment_body.quote}</summary><p className="my-2 text-sm">{m.moment.moment_body.context_summary}</p>{m.passages.map(p => <p className="whitespace-pre-wrap text-sm border-l-2 pl-3 mb-2" key={p.passage_id}><strong>{p.title}{p.start_ms !== null ? ` · ${(p.start_ms / 1000).toFixed(1)}s` : ''}</strong><br />{p.text}</p>)}</details>)}
    <button className={button} disabled={busy || !actions.edit} onClick={() => setEditing(!editing)}>Edit angle</button>
    {actions.editReason && <p className="text-sm text-slate-600">{actions.editReason}</p>}
    {editing && actions.edit && <form className="space-y-3" onSubmit={e => { e.preventDefault(); void perform(`/angles/${a.angle_id}`, 'PATCH', { expected_hash: a.content_hash, changes: Object.fromEntries(['title', ...names].map(n => [n, body[n as keyof typeof body]])) }); }}>
      {(['title', ...names] as const).map(n => <label key={n} className="block text-sm">{label(n)}<textarea required className="block w-full border rounded-lg p-2 mt-1" value={body[n]} onChange={e => setBody({ ...body, [n]: e.target.value })} /></label>)}
      <p className="text-sm">Saving an edit requires a fresh quality assessment and matching. The original evidence and generation date are preserved.</p><button className={button} disabled={busy}>Save edit</button>
    </form>}
    {actions.rescore && <form className="rounded-lg border p-3 space-y-3" onSubmit={e => { e.preventDefault(); void perform(`/angles/${a.angle_id}/quality`, 'POST', { expected_hash: a.content_hash, scores: { ...scores, reasons: [reason] } }); }}>
      <p>Assess the edited angle against its original evidence.</p><div className="flex gap-3 flex-wrap">{scoreNames.map(n => <label key={n} className="text-sm">{label(n)}<input type="number" min="0" max="5" step="0.1" required value={scores[n]} onChange={e => setScores({ ...scores, [n]: Number(e.target.value) })} className="block border p-1 w-20 rounded" /></label>)}</div>
      <label className="block">Assessment reason<textarea required value={reason} onChange={e => setReason(e.target.value)} className="block w-full border p-2 rounded" /></label><button className={button} disabled={busy}>Save quality assessment</button>
    </form>}
    {a.approval_status !== 'approved' && <div className="border-t pt-4 space-y-3">
      <label className="block text-sm">Selected CTA<input value={cta} onChange={e => setCta(e.target.value)} className="block w-full border rounded-lg p-2 mt-1" /></label>
      <label className="block text-sm">Review note<textarea value={note} onChange={e => setNote(e.target.value)} className="block w-full border rounded-lg p-2 mt-1" /></label>
      {flags.length > 0 && <label className="flex gap-2 text-sm"><input type="checkbox" checked={ack} onChange={e => setAck(e.target.checked)} />I reviewed the overlap and explained the distinct treatment in the note.</label>}
      <div className="flex gap-3"><button className={button} disabled={busy || !ready || !cta.trim() || (flags.length > 0 && (!ack || !note.trim()))} onClick={() => void perform(`/angles/${a.angle_id}/decision`, 'POST', { expected_hash: a.content_hash, decision: 'approved', cta: { text: cta }, overlap_acknowledged: ack, note })}>Approve angle</button>
        <button className={button} disabled={busy || !actions.reject} onClick={() => void perform(`/angles/${a.angle_id}/decision`, 'POST', { expected_hash: a.content_hash, decision: 'rejected', note })}>Reject angle</button></div>
      {actions.approveReason && <p className="text-sm text-slate-600">{actions.approveReason}</p>}
    </div>}
    {a.approval_status === 'approved' && <AngleResearch angleId={a.angle_id} canRetry={!!a.can_edit} />}
  </article>;
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
    <label className="text-sm">Inspect scenario <Select className="ml-2 border rounded p-2" value={cutoff} onChange={e => setCutoff(Number(e.target.value))}>{report.scenarios.map(s => <option key={s.cutoff} value={s.cutoff}>{s.cutoff.toFixed(2)}</option>)}</Select></label>
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
