import { describe, it, expect } from "vitest";
import {
  buildConfirmQueriesPayload,
  canConfirmVisibilityQueries,
  countVisibilityQueries,
  getMaxQueryNumber,
  mapBackendStatusToVisibilityStage,
  mapQueriesToSections,
  QUERY_FETCH_STATUS,
  resolveVisibilityStageTransition,
  shouldFetchVisibilityQueries,
  shouldResumeConfirmedStage,
  type QuerySection,
} from "./queryReview";

/** Ported from f-o_ai_readiness's visibilityLoadingFlow tests. */

const section = (overrides: Partial<QuerySection> = {}): QuerySection => ({
  aspectNumber: 1,
  aspectKey: "brand_entity_recognition",
  title: "Entity / Brand Discovery",
  categoryName: "Entity / Brand Discovery",
  queries: [],
  ...overrides,
});

describe("buildConfirmQueriesPayload", () => {
  it("sends every surviving query, not just the edited ones", () => {
    // The whole point: confirm DELETEs the run's rows and re-inserts exactly
    // what it receives, so anything omitted here is destroyed.
    const sections = [
      section({
        queries: [
          { query_number: 1, query_text: "acme dental phoenix" },
          { query_number: 2, query_text: "acme dental reviews" },
        ],
      }),
      section({
        aspectNumber: 2,
        aspectKey: "core_solution_keyword",
        title: "Core Offering / Solution Intent",
        categoryName: "Core Offering / Solution Intent",
        queries: [{ query_number: 3, query_text: "best dentist near me" }],
      }),
    ];

    expect(buildConfirmQueriesPayload(sections).queries).toEqual([
      {
        query_number: 1,
        query_text: "acme dental phoenix",
        aspect_key: "brand_entity_recognition",
        category_name: "Entity / Brand Discovery",
      },
      {
        query_number: 2,
        query_text: "acme dental reviews",
        aspect_key: "brand_entity_recognition",
        category_name: "Entity / Brand Discovery",
      },
      {
        query_number: 3,
        query_text: "best dentist near me",
        aspect_key: "core_solution_keyword",
        category_name: "Core Offering / Solution Intent",
      },
    ]);
  });

  it("expresses a removal by omission", () => {
    const before = [
      section({
        queries: [
          { query_number: 1, query_text: "keep me" },
          { query_number: 2, query_text: "drop me" },
        ],
      }),
    ];
    const after = [section({ queries: [{ query_number: 1, query_text: "keep me" }] })];

    expect(buildConfirmQueriesPayload(before).queries).toHaveLength(2);
    expect(buildConfirmQueriesPayload(after).queries).toEqual([
      expect.objectContaining({ query_text: "keep me" }),
    ]);
  });

  it("numbers a query added during review instead of dropping it", () => {
    const sections = [section({ queries: [{ query_text: "typed by hand" }] })];
    expect(buildConfirmQueriesPayload(sections).queries).toEqual([
      expect.objectContaining({ query_number: 1, query_text: "typed by hand" }),
    ]);
  });

  it("trims text and drops rows left blank", () => {
    const sections = [
      section({
        queries: [
          { query_number: 1, query_text: "  padded  " },
          { query_number: 2, query_text: "   " },
        ],
      }),
    ];
    expect(buildConfirmQueriesPayload(sections).queries).toEqual([
      expect.objectContaining({ query_text: "padded" }),
    ]);
  });

  it("reads the legacy `query` alias", () => {
    const sections = [section({ queries: [{ query_number: 1, query: "from the alias" }] })];
    expect(buildConfirmQueriesPayload(sections).queries[0].query_text).toBe("from the alias");
  });

  it("returns an empty set for no sections", () => {
    expect(buildConfirmQueriesPayload(undefined).queries).toEqual([]);
  });
});

describe("counters", () => {
  it("totals queries across sections", () => {
    expect(
      countVisibilityQueries([
        section({ queries: [{ query_text: "a" }, { query_text: "b" }] }),
        section({ aspectNumber: 2, queries: [{ query_text: "c" }] }),
      ]),
    ).toBe(3);
    expect(countVisibilityQueries([])).toBe(0);
  });

  it("finds the highest query number so a new row can follow it", () => {
    expect(
      getMaxQueryNumber([
        section({ queries: [{ query_number: 3 }, { query_number: 9 }] }),
        section({ aspectNumber: 2, queries: [{ query_number: 5 }] }),
      ]),
    ).toBe(9);
    // A hand-added query has no number and must not break the scan.
    expect(getMaxQueryNumber([section({ queries: [{ query_text: "no number" }] })])).toBe(0);
  });
});

describe("mapBackendStatusToVisibilityStage", () => {
  it.each([
    ["queued", "queued"],
    ["generating_queries", "retrieving"],
    ["running_evals", "confirmed"],
    ["running", "confirmed"],
    ["complete", "confirmed"],
  ])("maps %s to %s", (backendStatus, expected) => {
    expect(mapBackendStatusToVisibilityStage(backendStatus)).toBe(expected);
  });

  it("waits at retrieving until the queries actually arrive", () => {
    expect(mapBackendStatusToVisibilityStage("pending_user_review")).toBe("retrieving");
    expect(mapBackendStatusToVisibilityStage("pending_user_review", { hasQueries: true })).toBe(
      "showing",
    );
  });

  it("never drags a user backwards out of review", () => {
    // A late poll must not replace the editor with a spinner.
    expect(
      mapBackendStatusToVisibilityStage("generating_queries", {
        visibilityQueriesStage: "confirmed",
      }),
    ).toBe("confirmed");
    expect(
      mapBackendStatusToVisibilityStage("queued", {
        visibilityQueriesStage: "showing",
        hasQueries: true,
      }),
    ).toBe("showing");
  });
});

describe("resolveVisibilityStageTransition", () => {
  it("holds at queued while the backend is still queued", () => {
    expect(
      resolveVisibilityStageTransition({
        backendStatus: "queued",
        currentStage: "queued",
        hasQueries: false,
      }),
    ).toBe("queued");
  });

  it("advances to retrieving once generation starts", () => {
    expect(
      resolveVisibilityStageTransition({
        backendStatus: "generating_queries",
        currentStage: "queued",
        hasQueries: false,
      }),
    ).toBe("retrieving");
  });

  it("advances to showing when the queries are in hand", () => {
    expect(
      resolveVisibilityStageTransition({
        backendStatus: "pending_user_review",
        currentStage: "retrieving",
        hasQueries: true,
      }),
    ).toBe("showing");
  });
});

describe("gates", () => {
  it("only allows confirming a non-empty set that is on screen", () => {
    expect(canConfirmVisibilityQueries("showing", 3)).toBe(true);
    expect(canConfirmVisibilityQueries("showing", 0)).toBe(false);
    expect(canConfirmVisibilityQueries("retrieving", 3)).toBe(false);
    expect(canConfirmVisibilityQueries("confirmed", 3)).toBe(false);
  });

  it("fetches queries once, and only while awaiting review", () => {
    const base = { backendStatus: "pending_user_review", hasQueries: false };
    expect(shouldFetchVisibilityQueries({ ...base, queryFetchStatus: QUERY_FETCH_STATUS.IDLE })).toBe(
      true,
    );
    // Not while one is in flight, and not a second time.
    expect(
      shouldFetchVisibilityQueries({ ...base, queryFetchStatus: QUERY_FETCH_STATUS.LOADING }),
    ).toBe(false);
    expect(shouldFetchVisibilityQueries({ ...base, queryFetchStatus: QUERY_FETCH_STATUS.DONE })).toBe(
      false,
    );
    // A failed attempt is allowed to retry.
    expect(
      shouldFetchVisibilityQueries({ ...base, queryFetchStatus: QUERY_FETCH_STATUS.ERROR }),
    ).toBe(true);
    expect(
      shouldFetchVisibilityQueries({
        backendStatus: "running_evals",
        hasQueries: false,
        queryFetchStatus: QUERY_FETCH_STATUS.IDLE,
      }),
    ).toBe(false);
  });

  it("jumps a reopened run straight to confirmed once evaluation is under way", () => {
    expect(shouldResumeConfirmedStage("running_evals", "showing")).toBe(true);
    expect(shouldResumeConfirmedStage("complete", "retrieving")).toBe(true);
    expect(shouldResumeConfirmedStage("running_evals", "confirmed")).toBe(false);
    expect(shouldResumeConfirmedStage("pending_user_review", "showing")).toBe(false);
  });
});

describe("mapQueriesToSections", () => {
  it("buckets by aspect_key and returns all seven aspects in display order", () => {
    const sections = mapQueriesToSections([
      { query_number: 1, query_text: "brand one", aspect_key: "brand_entity_recognition" },
      { query_number: 2, query_text: "trust one", aspect_key: "trust_validation" },
    ]);

    expect(sections).toHaveLength(7);
    expect(sections.map((s) => s.aspectKey)).toEqual([
      "brand_entity_recognition",
      "core_solution_keyword",
      "persona_audience",
      "local_geographic",
      "situation_problem_trigger",
      "competitive_comparative",
      "trust_validation",
    ]);
    expect(sections[0].queries).toHaveLength(1);
    expect(sections[6].queries[0].query_text).toBe("trust one");
  });

  it("falls back to keywords when no aspect_key is sent", () => {
    const sections = mapQueriesToSections([
      { query_text: "a", category_name: "Comparison and alternatives" },
      { query_text: "b", category_name: "Local geo intent" },
    ]);
    const byKey = Object.fromEntries(sections.map((s) => [s.aspectKey, s.queries.length]));
    expect(byKey.competitive_comparative).toBe(1);
    expect(byKey.local_geographic).toBe(1);
  });

  it("puts an unrecognisable query in Core Offering rather than dropping it", () => {
    const sections = mapQueriesToSections([{ query_text: "mystery", category_name: "???" }]);
    expect(sections.find((s) => s.aspectKey === "core_solution_keyword")!.queries).toHaveLength(1);
  });

  it("skips blank queries", () => {
    expect(countVisibilityQueries(mapQueriesToSections([{ query_text: "   " }]))).toBe(0);
  });
});
