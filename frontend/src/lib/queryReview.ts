import {
  FALLBACK_ASPECT_NUMBER,
  QUERY_ASPECTS,
  QUERY_ASPECT_BY_KEY,
  type QueryAspect,
} from "@/data/queryAspects";

/**
 * The AI Presence query-review gate, ported from f-o_ai_readiness
 * (`features/audit/utils/visibilityLoadingFlow.js` plus the stage mapper from
 * `auditPipeline.js` and the counters from `visibilityState.js`).
 *
 * A presence run pauses at `pending_user_review` after generating its query set
 * and does not proceed until someone confirms it. Everything here is pure so the
 * behaviour can be tested without a component, which is how the original was
 * built and why the port is faithful rather than a reinterpretation.
 */

/* ── Stages ────────────────────────────────────────────────────── */

export const VISIBILITY_STAGES = ["queued", "retrieving", "showing", "confirmed"] as const;
export type VisibilityStage = (typeof VISIBILITY_STAGES)[number];

export const QUERY_FETCH_STATUS = {
  IDLE: "idle",
  LOADING: "loading",
  DONE: "done",
  ERROR: "error",
} as const;
export type QueryFetchStatus = (typeof QUERY_FETCH_STATUS)[keyof typeof QUERY_FETCH_STATUS];

/* ── Query shapes ──────────────────────────────────────────────── */

/** One row of GET /audits/:id/queries. */
export interface BackendQuery {
  query_number?: number;
  query_text?: string;
  /** The original also tolerated a `query` alias; kept so ported data still reads. */
  query?: string;
  is_branded?: boolean;
  category_name?: string | null;
  aspect_key?: string | null;
  category_id?: number;
}

/** One aspect's worth of queries, as the review screen edits them. */
export interface QuerySection {
  aspectNumber: number;
  aspectKey: string;
  title: string;
  categoryName: string;
  queries: BackendQuery[];
}

/** One entry of the confirm payload. */
export interface ReviewedQuery {
  query_number: number;
  query_text: string;
  aspect_key: string;
  category_name: string;
}

export const queryTextFromBackend = (query: BackendQuery | string | null | undefined): string => {
  if (typeof query === "string") return query;
  return query?.query || query?.query_text || "";
};

/* ── Counters ──────────────────────────────────────────────────── */

export const countVisibilityQueries = (sections: QuerySection[] | null | undefined): number =>
  (sections ?? []).reduce((total, section) => total + (section.queries?.length ?? 0), 0);

/** Highest existing query_number, so a newly added query can take the next one. */
export const getMaxQueryNumber = (sections: QuerySection[] | null | undefined): number =>
  (sections ?? []).reduce(
    (max, section) =>
      (section.queries ?? []).reduce((sectionMax, query) => {
        const value = Number(query?.query_number);
        return Number.isFinite(value) ? Math.max(sectionMax, value) : sectionMax;
      }, max),
    0,
  );

/* ── Confirm payload ───────────────────────────────────────────── */

/**
 * The complete final query set, flattened out of the edited sections.
 *
 * Deliberately walks EVERY section and EVERY query rather than tracking edits:
 * the confirm endpoint deletes the run's existing rows and re-inserts exactly
 * what it receives, so a partial payload silently discards the rest of the set.
 * Removing a query is therefore expressed by it no longer being in `sections`,
 * and this function's only job is to be exhaustive.
 *
 * Blank text is dropped — an empty row is an abandoned edit, not a query.
 */
export function buildConfirmQueriesPayload(sections: QuerySection[] | null | undefined): {
  queries: ReviewedQuery[];
} {
  let fallbackNumber = 1;

  const queries = (sections ?? []).flatMap((section) =>
    (section.queries ?? [])
      .map((query): ReviewedQuery | null => {
        const queryText = queryTextFromBackend(query).trim();
        if (!queryText) return null;

        // query_number back-references the generated row so the API can inherit
        // its aspect and category. A query added during review has none, so it
        // gets a running number instead; the API renumbers everything on write.
        const queryNumber = query?.query_number ?? fallbackNumber;
        fallbackNumber += 1;

        return {
          query_number: queryNumber,
          query_text: queryText,
          aspect_key: section.aspectKey,
          category_name: section.categoryName || section.title,
        };
      })
      .filter((query): query is ReviewedQuery => query !== null),
  );

  return { queries };
}

export const canConfirmVisibilityQueries = (stage: VisibilityStage, totalQueries: number) =>
  stage === "showing" && totalQueries > 0;

export const shouldFetchVisibilityQueries = ({
  backendStatus,
  hasQueries,
  queryFetchStatus,
}: {
  backendStatus: string | undefined;
  hasQueries: boolean;
  queryFetchStatus: QueryFetchStatus;
}) =>
  backendStatus === "pending_user_review" &&
  !hasQueries &&
  queryFetchStatus !== QUERY_FETCH_STATUS.LOADING &&
  queryFetchStatus !== QUERY_FETCH_STATUS.DONE;

/* ── Stage machine ─────────────────────────────────────────────── */

/**
 * The stage the review panel should be in for a given backend status.
 *
 * The two leading guards matter: once the user is `showing` or has `confirmed`,
 * a late status poll must not drag them backwards into a spinner.
 */
export function mapBackendStatusToVisibilityStage(
  backendStatus: string | undefined,
  {
    visibilityQueriesStage,
    hasQueries = false,
  }: { visibilityQueriesStage?: VisibilityStage; hasQueries?: boolean } = {},
): VisibilityStage {
  if (visibilityQueriesStage === "confirmed") return "confirmed";
  if (visibilityQueriesStage === "showing" && hasQueries) return "showing";

  if (backendStatus === "pending_user_review") return hasQueries ? "showing" : "retrieving";
  if (backendStatus === "running_evals" || backendStatus === "running") return "confirmed";
  if (backendStatus === "complete") return "confirmed";
  if (backendStatus === "generating_queries") return "retrieving";
  if (backendStatus === "queued") return "queued";
  return visibilityQueriesStage ?? "retrieving";
}

export function resolveVisibilityStageTransition({
  backendStatus,
  currentStage,
  hasQueries,
}: {
  backendStatus: string | undefined;
  currentStage: VisibilityStage;
  hasQueries: boolean;
}): VisibilityStage {
  const nextStage = mapBackendStatusToVisibilityStage(backendStatus, {
    visibilityQueriesStage: currentStage,
    hasQueries,
  });

  if (nextStage === "retrieving" && backendStatus === "generating_queries") {
    if (currentStage === "queued") return "retrieving";
  }

  // Hold at `queued` until the backend actually leaves it, so a first poll that
  // still reads "queued" does not flash the retrieving spinner.
  if (
    nextStage !== currentStage &&
    !(nextStage === "retrieving" && currentStage === "queued" && backendStatus === "queued")
  ) {
    return nextStage;
  }

  return currentStage;
}

export const shouldResumeConfirmedStage = (
  backendStatus: string | undefined,
  currentStage: VisibilityStage,
) =>
  currentStage !== "confirmed" &&
  (backendStatus === "running_evals" ||
    backendStatus === "running" ||
    backendStatus === "complete");

/* ── Bucketing ─────────────────────────────────────────────────── */

/**
 * Which aspect a query belongs to.
 *
 * `aspect_key` is authoritative when the API sends one. The keyword fallbacks
 * exist because a generated query can carry a free-text `category_name` with no
 * key, and dropping it would silently shrink the set the user reviews.
 */
export function aspectNumberFromQuery(query: BackendQuery): number {
  if (query?.category_id) return query.category_id;
  if (query?.aspect_key && QUERY_ASPECT_BY_KEY[query.aspect_key]) {
    return QUERY_ASPECT_BY_KEY[query.aspect_key].aspectNumber;
  }

  const label = `${query?.aspect_key ?? ""} ${query?.category_name ?? ""}`.toLowerCase();
  if (label.includes("brand") || label.includes("entity")) return 1;
  if (label.includes("core") || label.includes("solution") || label.includes("keyword")) return 2;
  if (label.includes("situation") || label.includes("problem") || label.includes("job")) return 3;
  if (label.includes("persona") || label.includes("audience")) return 4;
  if (label.includes("local") || label.includes("geo")) return 5;
  if (
    label.includes("competitive") ||
    label.includes("comparative") ||
    label.includes("comparison")
  ) {
    return 6;
  }
  if (label.includes("trust") || label.includes("validation") || label.includes("proof")) return 7;
  return FALLBACK_ASPECT_NUMBER;
}

/** Group a flat API response into the seven editable sections, in display order. */
export function mapQueriesToSections(
  queries: BackendQuery[] | null | undefined,
  aspects: readonly QueryAspect[] = QUERY_ASPECTS,
): QuerySection[] {
  const buckets = new Map<number, QuerySection>(
    aspects.map((aspect) => [
      aspect.aspectNumber,
      { ...aspect, categoryName: aspect.title, queries: [] },
    ]),
  );

  for (const query of queries ?? []) {
    const text = queryTextFromBackend(query).trim();
    if (!text) continue;

    const aspectNumber = aspectNumberFromQuery(query);
    const bucket = buckets.get(aspectNumber) ?? buckets.get(FALLBACK_ASPECT_NUMBER);
    bucket?.queries.push({ ...query, query_text: text });
  }

  return aspects.map((aspect) => buckets.get(aspect.aspectNumber)!);
}

/* ── Flat review view ──────────────────────────────────────────────
   The review screen shows one continuous list, not a block per aspect. The
   sections model stays underneath regardless, because the aspect still has to
   reach the service: apply_confirmed_queries rejects the WHOLE submission with
   422 "missing a valid aspect assignment" for any query whose aspect it cannot
   resolve, and confirm is the only route into evaluation. So the grouping stops
   being a layout and becomes purely the carrier for aspect_key. */

/** One row of the flat list, carrying the indices the section handlers need. */
export interface FlatQueryRow {
  sectionIndex: number;
  queryIndex: number;
  query: BackendQuery;
}

/**
 * Every query as a single ordered list, in the sections' own display order.
 *
 * Each row keeps its (sectionIndex, queryIndex) so the existing add / update /
 * remove handlers work unchanged — this is a view over the model, not a
 * replacement for it.
 */
export function flattenQuerySections(
  sections: QuerySection[] | null | undefined,
): FlatQueryRow[] {
  return (sections ?? []).flatMap((section, sectionIndex) =>
    (section.queries ?? []).map((query, queryIndex) => ({
      sectionIndex,
      queryIndex,
      query,
    })),
  );
}

/**
 * Which section a hand-added query belongs to when the UI shows no aspects.
 *
 * The fallback aspect — already where a generated query lands when its
 * aspect_key is missing or unrecognised, so an added query is classified the
 * same way as any other unclassified one rather than by a separate rule. Falls
 * back to the first section if that aspect is somehow absent, since returning
 * -1 would silently drop the query.
 */
export function defaultAddSectionIndex(sections: QuerySection[] | null | undefined): number {
  const list = sections ?? [];
  if (list.length === 0) return 0;
  const fallbackIndex = list.findIndex(
    (section) => section.aspectNumber === FALLBACK_ASPECT_NUMBER,
  );
  return fallbackIndex === -1 ? 0 : fallbackIndex;
}
