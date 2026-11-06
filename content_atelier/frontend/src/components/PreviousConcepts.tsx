import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ChevronDown, FileText, Lightbulb, Search } from 'lucide-react';
import type { StoredWeek } from '../api/schema';
import { useApiQuery } from '../api/query';
import { paths } from '../app/routes';
import { useMe } from '../utils/me';
import { archiveWeekHeading, weekLabel } from '../utils/editorialWeeks';
import { isCycleOverview, useCycleSummary, useFeatureFlags } from '../utils/workspace';
import { PageHeading } from './PageHeading';
import { ThemedSelect } from './ThemedSelect';
import { AngleReviewModal, WeekAngles, useAngleActions } from './SQLWeeklyAngles';
import { BriefCard, briefOfferText, briefSearchText } from './studio/BriefCard';
import { CardGrid, EmptyStage, OFFER_FILTERS, StageSection, matches, type OfferFilter } from './studio/parts';
import { currentPacks, weekBriefsArgs, weekPacksArgs } from './studio/studioWeek';
import { ActionError, ConflictNotice } from './shared/conflict';
import { useWeekList } from './shared/WeekPicker';
import { ErrorState, LoadingState } from './shared/states';

/* Previous Concepts (the 20 October mockup's item): the earlier weeks' concepts, one week at a time, in the Weekly Studio's
   card style. The stepper switches between the weeks' content angles and their briefs. Each week opens on request and reads its
   own cards; the decisions that exist (develop, reframe, hold, skip, revive a considered idea) work here as in the Weekly
   Studio, and a card's full screen opens in the same review dialog. Archived weeks are listed behind the existing toggle. */

type Stage = 'angles' | 'briefs';

function PreviousWeek({ week, stage, query, offer }: { week: string; stage: Stage; query: string; offer: OfferFilter }) {
  const navigate = useNavigate();
  const { me } = useMe();
  const flags = useFeatureFlags();
  const review = useApiQuery('/weeks/{week_id}', { path: { week_id: week } });
  const briefs = useApiQuery('/briefs', weekBriefsArgs(week));
  const packs = useApiQuery('/packs', weekPacksArgs(week), { enabled: flags.packs });
  const actions = useAngleActions(week, () => review.refetch());
  const [open, setOpen] = useState<string | null>(null);
  const weekPacks = currentPacks(packs.data?.items);
  if (review.error && !review.data) return <ErrorState message={review.error.message} onRetry={() => void review.refetch()} />;
  if (!review.data) return <LoadingState>Loading this week…</LoadingState>;
  const shownBriefs = (briefs.data?.items ?? []).filter(b => !b.has_replacement && matches(briefSearchText(b), briefOfferText(b), query, offer));
  const filtering = !!query.trim() || offer !== 'all';
  return <div className="space-y-6">
    {actions.feedback.region}
    {!open && <ConflictNotice conflict={actions.guard.conflict} onReload={() => void actions.guard.reloadLatest()} onDismiss={actions.guard.clear} />}
    {!open && <ActionError message={actions.guard.error} />}
    {stage === 'angles' ? <WeekAngles review={review.data} week={week} briefs={briefs.data?.items} packs={packs.data?.items} query={query} offer={offer}
      canDecide={me.can.decide} busy={actions.busy} perform={actions.perform} onReview={setOpen} />
      : <>
        {[['Awaiting approval', 'pending', 'Briefs from this week waiting for a decision.'], ['Approved', 'approved', 'The briefs behind this week’s content packs.']].map(([title, status, description]) => {
          const list = shownBriefs.filter(b => b.approval_status === status);
          return <StageSection key={status} title={title} count={list.length} label={`${title} briefs`} description={description}>
            {list.length ? <CardGrid>{list.map(b => {
              const href = `${paths.brief(b.brief_id)}?week=${encodeURIComponent(week)}`;
              return <BriefCard key={b.brief_id + b.content_hash} brief={b} week={week} pack={weekPacks.find(p => p.source_brief_id === b.brief_id)} packsOn={flags.packs}
                busy={actions.busy} onApprove={() => navigate(href)} fullBriefHref={href} />;
            })}</CardGrid> : <EmptyStage>{filtering ? 'No briefs match this view.' : status === 'pending' ? 'No briefs awaiting approval in this week.' : 'No approved briefs in this week.'}</EmptyStage>}
          </StageSection>;
        })}
      </>}
    {open && <AngleReviewModal review={review.data} week={week} angleId={open} briefs={briefs.data?.items} packs={packs.data?.items}
      canDecide={me.can.decide} busy={actions.busy} perform={actions.perform} guard={actions.guard} onClose={() => setOpen(null)} />}
  </div>;
}

function WeekRow({ week, waiting, stage, query, offer }: { week: StoredWeek; waiting: number; stage: Stage; query: string; offer: OfferFilter }) {
  const [opened, setOpened] = useState(false);
  return <details className="group/editorial-week rounded-2xl border border-[#E6E9F0] bg-white overflow-hidden" onToggle={e => { if (e.currentTarget.open) setOpened(true); }}>
    <summary className="list-none cursor-pointer flex flex-wrap items-center justify-between gap-3 px-5 py-4 [&::-webkit-details-marker]:hidden">
      <span className="flex flex-wrap items-center gap-x-4 gap-y-1"><span className="text-[14px] font-semibold text-[#34445F]">{archiveWeekHeading(week.week_start)}</span>
        <span className="text-[12px] text-[#8B93A3]">{weekLabel(week.week_start)}</span></span>
      <span className="flex items-center gap-3">
        {waiting > 0 && <span className="rounded-full bg-[#FFF8E9] px-3 py-1 text-[11px] text-[#947021]">{waiting} waiting</span>}
        <ChevronDown aria-hidden="true" className="w-4 h-4 text-[#667184] transition-transform group-open/editorial-week:rotate-180" /></span>
    </summary>
    <div className="border-t border-[#EEF0F4] bg-[#F7F8FB] p-4 sm:p-5">{opened && <PreviousWeek week={week.week_id} stage={stage} query={query} offer={offer} />}</div>
  </details>;
}

export function PreviousConcepts() {
  const [search, setSearch] = useSearchParams();
  const stage: Stage = search.get('stage') === 'briefs' ? 'briefs' : 'angles';
  const setStage = (value: Stage) => setSearch(prev => { const next = new URLSearchParams(prev); if (value === 'briefs') next.set('stage', value); else next.delete('stage'); return next; }, { replace: true });
  const { weeks, latest } = useWeekList();
  const summary = useCycleSummary();
  const [query, setQuery] = useState('');
  const [offer, setOffer] = useState<OfferFilter>('all');
  const earlier = (weeks.data ?? []).filter(w => w.week_id !== latest && w.status !== 'prepared');
  const waitingBy = new Map(isCycleOverview(summary.data) ? summary.data.waiting.cards_at_gate_1.by_week.map(w => [w.week_id, w.n] as const) : []);
  const waitingTotal = earlier.reduce((n, w) => n + (waitingBy.get(w.week_id) ?? 0), 0);
  return <div className="space-y-6">
    <PageHeading title="Previous Concepts"
      subtitle={weeks.data ? `${earlier.length} previous ${earlier.length === 1 ? 'week' : 'weeks'}${waitingTotal ? ` · ${waitingTotal} ${waitingTotal === 1 ? 'angle' : 'angles'} awaiting approval` : ''}` : undefined}
      actions={<Link to={paths.studio} className="inline-flex h-10 items-center rounded-full border border-[#E6E9F0] bg-white px-4 text-[12px] text-[#34445F] hover:bg-[#F7F8FB]"><span aria-hidden="true">←&nbsp;</span>Weekly Studio</Link>} />
    <nav aria-label="Editorial pipeline" className="editorial-pipeline">
      {([['angles', 'Content Angle', Lightbulb, 'Each week’s angles'], ['briefs', 'Content Briefing', FileText, 'Each week’s briefs']] as const).map(([id, label, Icon, note]) => {
        const selected = id === stage;
        return <button key={id} type="button" aria-pressed={selected} onClick={() => setStage(id)} className={`editorial-pipeline-step ${selected ? 'is-selected' : ''}`}>
          <svg aria-hidden="true" className="editorial-pipeline-shape" viewBox="0 0 320 56" preserveAspectRatio="none"><path d="M28 1 H293 L318 28 L293 55 H28 A27 27 0 0 1 28 1 Z" vectorEffect="non-scaling-stroke" /></svg>
          <span className="editorial-pipeline-content"><Icon aria-hidden="true" className="w-4 h-4 shrink-0" /><span className="flex flex-col items-start gap-0.5"><span className="font-semibold">{label}</span><span className="editorial-pipeline-count">{note}</span></span></span>
        </button>;
      })}
    </nav>
    <div className="flex flex-wrap justify-between items-center gap-4 border-b border-[#E3E7EF] pb-4">
      <p className="text-[12px] text-[#8B93A3]">Open a week to review its {stage === 'angles' ? 'angles' : 'briefs'}.</p>
      <div className="flex flex-wrap items-center gap-2 max-w-full">
        <div className="relative max-w-full"><Search aria-hidden="true" className="absolute top-3 left-3 w-3.5 h-3.5 text-[#9AA3B2]" />
          <input aria-label="Search the open weeks" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search the open weeks…"
            className="h-9 w-60 max-w-full rounded-full border border-[#E6E9F0] bg-white pl-9 pr-3 text-[11px] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#8DA1FD]" /></div>
        <ThemedSelect aria-label="Filter by offer" value={offer} onChange={value => setOffer(value as OfferFilter)} className="h-9 px-3 text-[11px]">
          <option value="all">All offers</option>{OFFER_FILTERS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</ThemedSelect>
      </div>
    </div>
    {weeks.error && <ErrorState message={weeks.error.message} onRetry={() => void weeks.refetch()} />}
    {weeks.isPending && !weeks.error && <LoadingState>Loading stored weeks…</LoadingState>}
    {weeks.data && <section aria-label="Earlier weeks" className="space-y-3">
      {earlier.length ? earlier.map(w => <WeekRow key={w.week_id} week={w} waiting={waitingBy.get(w.week_id) ?? 0} stage={stage} query={query} offer={offer} />)
        : <EmptyStage>No earlier weeks with concepts yet.</EmptyStage>}
    </section>}
  </div>;
}
