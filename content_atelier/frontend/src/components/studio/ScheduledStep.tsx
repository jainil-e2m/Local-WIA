import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { useApiQuery } from '../../api/query';
import { paths } from '../../app/routes';
import { useFeatureFlags } from '../../utils/workspace';
import { BackendCalendar } from '../BackendCalendar';
import { ErrorState, LoadingState } from '../shared/states';
import { PackCard } from './PackCard';
import { CardGrid, EmptyStage, StageSection } from './parts';
import { currentPacks, useStudioContext, weekPacksArgs } from './studioWeek';

/** Finished packs awaiting publication, independent of the former whole-pack approval step, plus the saved calendar.
    Each piece can be recorded as published from its pack or calendar item. */
export function ScheduledStep() {
  const flags = useFeatureFlags();
  const { week } = useStudioContext();
  const [search] = useSearchParams();
  const shown = week || search.get('week') || '';
  const packs = useApiQuery('/packs', weekPacksArgs(shown), { enabled: !!shown });
  const current = currentPacks(packs.data?.items).filter(p => p.state === 'in_review' || p.state === 'ready_to_publish');
  const published = current.filter(p => p.pieces.length > 0 && p.pieces.every(piece => piece.published));
  const ready = current.filter(p => !published.includes(p));
  return <section aria-label="Scheduled content" className="space-y-8">
    <StageSection title="Awaiting publication" count={ready.length} label="Awaiting publication"
      description="Mark each piece published or sent from its pack or the content calendar when it goes out.">
      {packs.error && <ErrorState message={packs.error.message} onRetry={() => void packs.refetch()} />}
      {shown && packs.isPending && !packs.error && <LoadingState>Loading content packs…</LoadingState>}
      {packs.data && (ready.length ? <CardGrid>{ready.map(p => <PackCard key={p.pack_id} pack={p} base={paths.studioPacks} />)}</CardGrid>
        : <EmptyStage>No content packs are awaiting publication this week.</EmptyStage>)}
    </StageSection>
    {published.length > 0 && <StageSection title="Published" count={published.length} label="Published" description="Every piece of these packs has gone out.">
      <CardGrid>{published.map(p => <PackCard key={p.pack_id} pack={p} base={paths.studioPacks} />)}</CardGrid>
    </StageSection>}
    {flags.calendar && <section aria-label="The publishing calendar" className="space-y-3">
      <h2 className="font-editorial text-2xl text-[#1B2433]">Scheduled Content</h2>
      <BackendCalendar />
    </section>}
  </section>;
}
