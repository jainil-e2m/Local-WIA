import { useLocation, useOutletContext, useSearchParams } from 'react-router-dom';
import type { PackSummaryV2, StoredAngle, StoredBrief, WeekReview } from '../../api/types';
import { useApiQuery } from '../../api/query';
import { ID, paths } from '../../app/routes';
import { useWeekList } from '../shared/WeekPicker';
import type { OfferFilter } from './parts';

/* The week the Weekly Studio shows and what each of its stages holds (the mockup's stepper and gold line). The week is in the
   URL: `/studio/angles/<week>` on the angles step, `?week=<week>` on the others; without one, the latest live week. The
   reads share the cache with the stages below, so the counts cost no extra request. */

export type StageId = 'angles' | 'briefs' | 'packs' | 'scheduled';

/** The stage a Weekly Studio path belongs to. */
export function stageOf(pathname: string): StageId {
  if (pathname.startsWith(paths.briefs)) return 'briefs';
  if (pathname.startsWith(paths.studioPacks)) return 'packs';
  if (pathname.startsWith(paths.scheduled)) return 'scheduled';
  return 'angles';
}

/** The week a Weekly Studio URL names, or '' when it names none. */
export function weekInUrl(pathname: string, search: URLSearchParams): string {
  const angles = new RegExp(`^/studio/angles/(${ID})(?:/|$)`).exec(pathname);
  if (angles) return angles[1];
  const week = search.get('week') ?? '';
  return new RegExp(`^${ID}$`).test(week) ? week : '';
}

/** A stage's path for a week (the angles step carries it in the path, the others in the query string). */
export function stagePath(stage: StageId, week: string): string {
  if (stage === 'angles') return week ? paths.week(week) : paths.angles;
  const base = stage === 'briefs' ? paths.briefs : stage === 'packs' ? paths.studioPacks : paths.scheduled;
  return week ? `${base}?week=${encodeURIComponent(week)}` : base;
}

/** The week's cards as the studio shows them: the newest version of each strategist card. */
export const currentCards = (review: Pick<WeekReview, 'angles'> | undefined) =>
  (review?.angles ?? []).filter(a => !!a.content_body.card && !a.has_replacement);

export type CardGroup = 'waiting' | 'approved' | 'other';
/** Where a card sits on the angles step: waiting for a decision, approved (developed), or folded away (held, skipped, kept for
    internal use, folded into a better-ranked idea). */
export function cardGroup(a: Pick<StoredAngle, 'approval_status' | 'hold' | 'matching_result'>): CardGroup {
  if (a.approval_status === 'approved') return 'approved';
  if (a.approval_status !== 'pending' || a.hold) return 'other';
  if (a.matching_result?.selection?.selection_status === 'suppressed') return 'other';
  return 'waiting';
}

/** The week's current packs (a superseded pack is an older version of one). */
export const currentPacks = (packs: PackSummaryV2[] | undefined) => (packs ?? []).filter(p => p.state !== 'superseded');

export interface StageCounts { waiting: number; approved: number; generated: number; briefsWaiting: number; awaitingPublication: number; published: number;
  concepts: number; cards: number }

/** The stepper's counts, in the mockup's exclusive sense: an approved angle is one in Briefing whose pack is not made yet. */
export function stageCounts(review: Pick<WeekReview, 'angles'> | undefined, briefs: Pick<StoredBrief, 'approval_status'>[] | undefined, packs: PackSummaryV2[] | undefined): StageCounts {
  const cards = currentCards(review);
  const waiting = cards.filter(a => cardGroup(a) === 'waiting').length;
  const developed = cards.filter(a => cardGroup(a) === 'approved').length;
  const live = currentPacks(packs);
  return {
    waiting, approved: Math.max(0, developed - live.length), generated: live.length,
    briefsWaiting: (briefs ?? []).filter(b => b.approval_status === 'pending').length,
    awaitingPublication: live.filter(p => (p.state === 'in_review' || p.state === 'ready_to_publish')
      && p.pieces.length > 0 && !p.pieces.every(piece => piece.published)).length,
    published: live.reduce((n, p) => n + p.pieces.filter(piece => piece.published).length, 0),
    concepts: waiting + developed, cards: cards.length,
  };
}

/** The week's briefs and packs, as the stages read them (the same cache keys). */
export const weekBriefsArgs = (week: string) => ({ query: { week_id: week, limit: 50, offset: 0 } });
export const weekPacksArgs = (week: string) => ({ query: { week_id: week, limit: 50, offset: 0 } });

/** The pack or week a content pack page names (`/studio/packs/<pack>`, `/studio/packs/week/<week>`), so the frame shows its week. */
export function packPage(pathname: string): { packId: string; weekId: string } {
  const week = new RegExp(`^/studio/packs/week/(${ID})$`).exec(pathname)?.[1] ?? '';
  const pack = week ? '' : new RegExp(`^/studio/packs/(${ID})$`).exec(pathname)?.[1] ?? '';
  return { packId: pack, weekId: week };
}

/** The week the studio shows: `override` (the week of the pack page shown), else the URL's, else the latest live week. */
export function useStudioWeek(override = '') {
  const location = useLocation();
  const [search] = useSearchParams();
  const list = useWeekList();
  const named = override || weekInUrl(location.pathname, search);
  const week = named || list.latest;
  return { ...list, week, named, isLatest: !!week && week === list.latest, stage: stageOf(location.pathname) };
}

export function useWeekReads(week: string, packsOn: boolean) {
  const review = useApiQuery('/weeks/{week_id}', { path: { week_id: week } }, { enabled: !!week });
  const briefs = useApiQuery('/briefs', weekBriefsArgs(week), { enabled: !!week });
  const packs = useApiQuery('/packs', weekPacksArgs(week), { enabled: !!week && packsOn });
  return { review, briefs, packs };
}

/** What the studio frame hands its stages: the week and the search and offer filter of its toolbar. */
export interface StudioContext { week: string; query: string; offer: OfferFilter }
const NO_FILTER: StudioContext = { week: '', query: '', offer: 'all' };

/** The frame's context, or no filter when a stage is shown on its own (a screen test, Previous Concepts). */
export function useStudioContext(): StudioContext {
  return useOutletContext<StudioContext | undefined>() ?? NO_FILTER;
}
