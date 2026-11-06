import { useApiQuery } from '../api/query';
import type { CycleOverview, Flags } from '../api/schema';

/** Which out-of-scope features are switched on (S.B11), and the context screens (Phase L, ATELIER_CONTEXT_ENABLED).
    Until the answer arrives, or if it fails, all are off. */
export type FeatureFlags = Pick<Flags, 'briefs' | 'packs' | 'calendar' | 'context'>;
export const FLAGS_OFF: FeatureFlags = { briefs: false, packs: false, calendar: false, context: false };

export function readFlags(value: unknown): FeatureFlags {
  const v = (value || {}) as Partial<Record<keyof FeatureFlags, unknown>>;
  return { briefs: v.briefs === true, packs: v.packs === true, calendar: v.calendar === true, context: v.context === true };
}

/** The flags from the shared cache. `loaded` is false until the server has answered or failed, so a deep link to a
    flagged screen waits for the answer instead of being sent away on the default. */
export function useFeatureFlagState(): { flags: FeatureFlags; loaded: boolean } {
  const query = useApiQuery('/flags', undefined, { staleTime: 60_000 });
  return { flags: query.data ? readFlags(query.data) : FLAGS_OFF, loaded: !query.isPending };
}

export const useFeatureFlags = (): FeatureFlags => useFeatureFlagState().flags;

/** The setting gates.one_click: approving is one click and the screens ask only for feedback. */
export function useOneClick(): boolean {
  return (useApiQuery('/flags', undefined, { staleTime: 60_000 }).data as { one_click?: boolean } | undefined)?.one_click === true;
}

/** Home's cycle summary (6.F2, GET /summary): what waits for whom, the latest and the next cycle, source health, the open
    alerts and the week's spend, in one read. The shell's counts (the sidebar badge, the bell) share the same cached answer.
    Read every minute, as Home's three reads were before. */
export function useCycleSummary(refreshMs = 60_000) {
  return useApiQuery('/summary', undefined, { refetchInterval: refreshMs });
}

/** Whether an answer has the summary's shape; a screen test may stub other routes, and a partial answer renders nothing. */
export const isCycleOverview = (value: unknown): value is CycleOverview => {
  const v = value as Partial<CycleOverview> | null | undefined;
  return !!v && typeof v === 'object' && !!v.waiting?.cards_at_gate_1 && !!v.next_cycle && !!v.sources && !!v.alerts && !!v.spend;
};

/** The counts the shell shows from the summary: cards at Gate 1 for the Weekly Studio's badge; the approvals waiting (cards at
    Gate 1, held cards due back, briefs at Gate 2) and the open alerts for the bell. Zero until a well-formed answer arrives. */
export function shellCounts(value: unknown): { cards: number; approvals: number; alerts: number } {
  if (!isCycleOverview(value)) return { cards: 0, approvals: 0, alerts: 0 };
  const w = value.waiting;
  return { cards: w.cards_at_gate_1.count, approvals: w.cards_at_gate_1.count + w.held_cards_due_back.count + w.briefs_at_gate_2.count, alerts: value.alerts.open };
}
