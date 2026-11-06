import { describe, it, expect } from "vitest";
import {
  AUDIT_ACTION,
  auditActionLabel,
  buildResumePlan,
  requiresQueryApproval,
  resolveAuditAction,
  type ActionableAudit,
} from "./auditActions";
import { buildConfirmQueriesPayload, type QuerySection } from "./queryReview";

/** Ported from f-o_ai_readiness's pastAuditsFlow and multiAuditScenario tests. */

const audit = (overrides: Partial<ActionableAudit> = {}): ActionableAudit => ({
  status: "running",
  backendStatus: "running",
  ...overrides,
});

describe("resolveAuditAction", () => {
  it("asks for approval when a run is parked on its query review", () => {
    expect(resolveAuditAction(audit({ backendStatus: "pending_user_review" }))).toBe(
      AUDIT_ACTION.REQUIRE_APPROVAL,
    );
  });

  it("recognises the awaiting_review flag on its own", () => {
    // The flag is what a client gets when the raw status was translated away.
    expect(resolveAuditAction(audit({ backendStatus: "running", awaitingReview: true }))).toBe(
      AUDIT_ACTION.REQUIRE_APPROVAL,
    );
  });

  it("shows progress for a run that is simply working", () => {
    expect(resolveAuditAction(audit({ backendStatus: "generating_queries" }))).toBe(
      AUDIT_ACTION.VIEW_PROGRESS,
    );
    expect(resolveAuditAction(audit({ status: "queued", backendStatus: "queued" }))).toBe(
      AUDIT_ACTION.VIEW_PROGRESS,
    );
  });

  it("offers the report only once it exists", () => {
    expect(resolveAuditAction(audit({ status: "completed", reportReady: true }))).toBe(
      AUDIT_ACTION.VIEW_REPORT,
    );
    expect(resolveAuditAction(audit({ status: "completed", reportReady: false }))).toBe(
      AUDIT_ACTION.NONE,
    );
    expect(
      resolveAuditAction(audit({ status: "completed", reportReady: false }), { hasReport: true }),
    ).toBe(AUDIT_ACTION.VIEW_REPORT);
  });

  it("offers nothing for a failed run, or no run at all", () => {
    expect(resolveAuditAction(audit({ status: "failed" }))).toBe(AUDIT_ACTION.NONE);
    expect(resolveAuditAction(null)).toBe(AUDIT_ACTION.NONE);
  });
});

describe("auditActionLabel", () => {
  it.each([
    [{ backendStatus: "pending_user_review" }, "Review queries"],
    [{ backendStatus: "generating_queries" }, "View progress"],
    [{ status: "completed", reportReady: true }, "View report"],
    [{ status: "failed" }, ""],
  ])("labels %o as %s", (overrides, expected) => {
    expect(auditActionLabel(audit(overrides))).toBe(expected);
  });

  it("says a finished run is finalizing rather than showing nothing", () => {
    expect(auditActionLabel(audit({ status: "completed", reportReady: false }))).toBe("Finalizing…");
  });
});

describe("requiresQueryApproval", () => {
  it("only applies to a run that is still in flight", () => {
    // A finished run cannot be awaiting review, whatever a stale row says.
    expect(
      requiresQueryApproval(audit({ status: "completed", backendStatus: "pending_user_review" })),
    ).toBe(false);
  });
});

describe("buildResumePlan", () => {
  it("fetches the query set when reopening a parked run with nothing in memory", () => {
    const plan = buildResumePlan(audit({ backendStatus: "pending_user_review" }), null);
    expect(plan.stage).toBe("retrieving");
    expect(plan.shouldFetchQueries).toBe(true);
    expect(plan.shouldClearQueries).toBe(true);
  });

  it("keeps unconfirmed edits instead of refetching over them", () => {
    const queries: QuerySection[] = [
      {
        aspectNumber: 1,
        aspectKey: "brand_entity_recognition",
        title: "Entity / Brand Discovery",
        categoryName: "Entity / Brand Discovery",
        queries: [{ query_number: 1, query_text: "edited by hand" }],
      },
    ];

    const plan = buildResumePlan(audit({ backendStatus: "pending_user_review" }), {
      stage: "showing",
      queries,
    });

    expect(plan.stage).toBe("showing");
    expect(plan.preserveQueries).toBe(true);
    expect(plan.shouldFetchQueries).toBe(false);
    expect(plan.shouldClearQueries).toBe(false);
  });

  it("drops another run's queries when reopening a different one", () => {
    // The cross-contamination guard: an audit with no queries of its own must
    // not inherit whatever was last on screen.
    const plan = buildResumePlan(audit({ backendStatus: "pending_user_review" }), {
      stage: "showing",
      queries: [],
    });
    expect(plan.preserveQueries).toBe(false);
    expect(plan.shouldClearQueries).toBe(true);
  });

  it("reopens a run already past review straight into confirmed", () => {
    for (const backendStatus of ["running_evals", "running", "complete"]) {
      expect(buildResumePlan(audit({ backendStatus }), null).stage).toBe("confirmed");
    }
  });
});

describe("the multi-audit scenario", () => {
  it("tracks three runs independently and only flags the parked one", () => {
    // Ported from multiAuditScenario.test.js: audit A parked on review, B
    // generating, C queued. Only A asks for approval; resuming A must not
    // disturb B or C.
    const a = audit({ backendStatus: "pending_user_review" });
    const b = audit({ backendStatus: "generating_queries" });
    const c = audit({ status: "queued", backendStatus: "queued" });

    expect(auditActionLabel(a)).toBe("Review queries");
    expect(auditActionLabel(b)).toBe("View progress");
    expect(auditActionLabel(c)).toBe("View progress");

    const planA = buildResumePlan(a, null);
    expect(planA.shouldFetchQueries).toBe(true);
    expect(planA.stage).toBe("retrieving");

    // A's queries arrive and are confirmed; B then parks on its own review.
    const queriesA: QuerySection[] = [
      {
        aspectNumber: 1,
        aspectKey: "brand_entity_recognition",
        title: "Entity / Brand Discovery",
        categoryName: "Entity / Brand Discovery",
        queries: [{ query_number: 1, query_text: "acme dental phoenix" }],
      },
    ];
    expect(buildConfirmQueriesPayload(queriesA).queries).toHaveLength(1);

    const bReview = audit({ backendStatus: "pending_user_review" });
    // B starts from nothing — A's confirmed set must not leak across.
    const planB = buildResumePlan(bReview, { stage: "showing", queries: [] });
    expect(planB.shouldClearQueries).toBe(true);
    expect(planB.shouldFetchQueries).toBe(true);

    // A, now evaluating, is back to a plain progress row.
    expect(auditActionLabel(audit({ backendStatus: "running_evals" }))).toBe("View progress");
    expect(
      resolveAuditAction(audit({ status: "completed", backendStatus: "complete", reportReady: true })),
    ).toBe(AUDIT_ACTION.VIEW_REPORT);
  });
});
