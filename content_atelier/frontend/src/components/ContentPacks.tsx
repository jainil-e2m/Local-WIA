import React from 'react';
import { Download } from 'lucide-react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useApiQuery } from '../api/query';
import { paths } from '../app/routes';
import { weekWords } from '../utils/editorialWeeks';
import { button } from './packParts';
import { PageHeading } from './PageHeading';
import { ThemedSelect } from './ThemedSelect';
import { PackCard } from './studio/PackCard';
import { CardGrid, EmptyStage, matches } from './studio/parts';
import { currentPacks, useStudioContext, weekPacksArgs } from './studio/studioWeek';
import { PackDetail } from './PackDetail';
import { PackWeek } from './PackWeek';
import { ErrorState, LoadingState } from './shared/states';
import { useWriteFeedback } from './shared/a11y';

/* The content packs (NP.F1, NP.F4; the content-packs plan, section 5.7), replacing the v1 list and detail. `base` is the list's
   own path (`/studio/packs` in the Weekly Studio, `/packs` from the sidebar); `<base>/<packId>` opens a pack and
   `<base>/week/<weekId>` a week's plan (NP.F4). The list shows each current pack with its state, its pieces and what is open on it,
   filtered by week and state in the query string, so a refresh keeps the view. */

const PAGE = 20;
const FILTER_STATES = ['finishing', 'waiting', 'generated'] as const;
const STATE_WORDS: Record<string, string> = { finishing: 'Being written', waiting: 'Waiting', generated: 'Generated' };

/** The content packs of every week (`/packs`), as the mockup's "Content Packs & Deliverable Scripts": one state filter, then the
    packs grouped by week, newest first. A week in the query string (a link from Home) shows that week alone. */
export function PackList({ base }: { base: string }) {
  const [search, setSearch] = useSearchParams();
  const week = search.get('week') ?? '', state = search.get('state') ?? '', offset = Math.max(0, Number(search.get('offset')) || 0);
  const setFilter = (name: string, value: string) => setSearch(prev => { const next = new URLSearchParams(prev); if (value) next.set(name, value); else next.delete(name); next.delete('offset'); return next; }, { replace: true });
  const setOffset = (value: number) => setSearch(prev => { const next = new URLSearchParams(prev); if (value) next.set('offset', String(value)); else next.delete('offset'); return next; }, { replace: true });
  // Saved links using either former approval state now open the combined generated view.
  const mappedState = state === 'in_review' || state === 'ready_to_publish' ? 'generated' : state;
  const validState = (FILTER_STATES as readonly string[]).includes(mappedState) ? mappedState as typeof FILTER_STATES[number] : undefined;
  const list = useApiQuery('/packs', { query: { week_id: week || undefined, state: validState, limit: PAGE, offset } },
    { refetchInterval: data => data?.items.some(p => p.state === 'finishing' || p.state === 'waiting') ? 10_000 : 30_000 });
  const items = list.data?.items ?? [], total = list.data?.total ?? 0;
  const weeks = [...new Set(items.map(p => p.week_id))];
  return <section className="space-y-6">
    <PageHeading title="Content Packs & Deliverable Scripts"
      subtitle={list.data ? `${total} ${total === 1 ? 'pack' : 'packs'}${week ? ` · ${weekWords(week)}` : ''}` : undefined}
      actions={<ThemedSelect aria-label="State" value={validState ?? ''} onChange={value => setFilter('state', value)} className="h-10 px-4 text-[12px]">
        <option value="">All packs</option>{FILTER_STATES.map(s => <option key={s} value={s}>{STATE_WORDS[s]}</option>)}</ThemedSelect>} />
    {week && <p className="text-[12px] text-[#8B93A3]">Showing the {weekWords(week)} · <button type="button" className="font-medium text-[#5070FF] hover:underline" onClick={() => setFilter('week', '')}>Show every week</button></p>}
    {list.error && <ErrorState message={list.error.message} onRetry={() => void list.refetch()} />}
    {list.isPending && !list.error && <LoadingState>Loading content packs…</LoadingState>}
    {list.data && !items.length && <EmptyStage>No content packs here yet. Approving a brief creates its pack. <Link className="text-[#5070FF]" to={paths.briefs}>Open the briefs</Link></EmptyStage>}
    {weeks.map(w => {
      const packs = items.filter(p => p.week_id === w);
      return <section key={w} aria-label={weekWords(w)} className="rounded-3xl border border-[#E6E9F0] bg-white/70">
        <div className="flex items-center justify-between gap-3 border-b border-[#EEF0F4] px-6 py-4">
          <h2 className="font-sans text-[14px] font-semibold text-[#1B2433]">{capitalise(weekWords(w))}</h2>
          <span className="flex items-center gap-4"><DownloadPacks weekId={w} />
            <span className="rounded-full bg-[#EFF3FF] px-2.5 py-1 text-[11px] font-medium text-[#5070FF]">{packs.length} {packs.length === 1 ? 'pack' : 'packs'}</span></span>
        </div>
        <div className="p-5"><CardGrid>{packs.map(p => <PackCard key={p.pack_id} pack={p} base={base} />)}</CardGrid></div>
      </section>;
    })}
    {total > PAGE && <div className="flex items-center gap-3 text-[12px] text-[#667184]"><button type="button" className={button} disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</button>
      <span>{offset + 1} to {Math.min(total, offset + PAGE)} of {total}</span>
      <button type="button" className={button} disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>Next</button></div>}
  </section>;
}

const capitalise = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

/** The week's pack document as a Word file (NP.B12): every pack of the week in one document, to share or print. */
export function DownloadPacks({ weekId, className }: { weekId: string; className?: string }) {
  return <a href={`/api/atelier/weeks/${encodeURIComponent(weekId)}/packs.docx`} download
    className={className ?? 'inline-flex items-center gap-1.5 text-[12px] font-medium text-[#5070FF] hover:underline'}>
    <Download aria-hidden="true" className="w-3.5 h-3.5" />Download the week's packs</a>;
}

/** The Content Packs step of the Weekly Studio (`/studio/packs?week=<week>`): the week's packs as cards. */
export function StudioPacks({ base }: { base: string }) {
  const { week, query } = useStudioContext();
  const [search] = useSearchParams();
  const shown = week || search.get('week') || '';
  const list = useApiQuery('/packs', weekPacksArgs(shown), { enabled: !!shown,
    refetchInterval: data => data?.items.some(p => p.state === 'finishing' || p.state === 'waiting') ? 10_000 : 30_000 });
  const packs = currentPacks(list.data?.items).filter(p => matches(p.title, '', query, 'all'));
  return <section aria-label="Weekly content packs" className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-3"><h2 className="font-editorial text-2xl text-[#1B2433]">Generated content packs</h2>
        <span className="bg-white rounded-full border border-[#E6E9F0] px-2.5 py-1 text-[10px] text-[#8B93A3]">{packs.length}</span></div>
      {shown && packs.length > 0 && <DownloadPacks weekId={shown} />}
    </div>
    <p className="text-[12px] text-[#8B93A3]">Each approved brief becomes a pack: one email, one carousel and three Reels.</p>
    {list.error && <ErrorState message={list.error.message} onRetry={() => void list.refetch()} />}
    {shown && list.isPending && !list.error && <LoadingState>Loading content packs…</LoadingState>}
    {list.data && (packs.length ? <CardGrid>{packs.map(p => <PackCard key={p.pack_id} pack={p} base={base} />)}</CardGrid>
      : <EmptyStage>{query.trim() ? 'No packs match this view.' : 'No packs for this week yet. Approve a brief to generate its content pack.'}</EmptyStage>)}
  </section>;
}

/** The route's screen: the list, one pack (`:packId`) or one week (`:weekId`). A pack is keyed by its id, so opening a new
    version of it starts from that version; what a write did is said here, above the pack, so it outlives that remount (6.F6). */
export function ContentPacks({ base = paths.studioPacks }: { base?: string }) {
  const { packId, weekId } = useParams();
  const feedback = useWriteFeedback();
  if (weekId) return <PackWeek key={weekId} weekId={weekId} base={base} />;
  if (packId) return <>{feedback.region}<PackDetail key={packId} packId={packId} base={base} announce={feedback.announce} /></>;
  return base === paths.studioPacks ? <StudioPacks base={base} /> : <PackList base={base} />;
}
