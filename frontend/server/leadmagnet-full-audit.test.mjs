import { describe, it, expect } from "vitest";
import {
  FULL_AUDIT_MAX_AGE_MS,
  FULL_AUDIT_PRODUCTS,
  fullAuditSubmitBody,
  missingIdentityFields,
  hasRunInFlight,
  isStaleRun,
  isSuccessStatus,
  isTerminalStatus,
  normalizeAuditStatus,
  readUpstreamStatus,
  seedUrlForLead,
} from "./leadmagnet-full-audit.mjs";

/**
 * These pin the decisions that are silent when wrong.
 *
 * The button they serve used to call the Lead Magnet backend for every lead
 * whatever its funnel — a real audit, but the ~50 second free snapshot rather
 * than the deep run being asked for, and labelled with the wrong product. None
 * of that threw; it just produced the wrong audit. So the routing table, the
 * status vocabulary and the in-flight guard are all asserted directly.
 */

describe("product routing", () => {
  it("routes each funnel to its own full-audit service", () => {
    expect(FULL_AUDIT_PRODUCTS.technical_seo.serviceId).toBe("technical-seo");
    expect(FULL_AUDIT_PRODUCTS.onpage_seo.serviceId).toBe("on-page-seo");
  });

  it("offers AI SEO, but only with its identity requirement declared", () => {
    // AI SEO is the one identity-aware product: a lead row is NOT a sufficient
    // payload for it. Registering it without declaring what it still needs would
    // submit runs that 422 upstream, so the requirement is part of the entry.
    expect(FULL_AUDIT_PRODUCTS.ai_seo.serviceId).toBe("ai-seo");
    expect(FULL_AUDIT_PRODUCTS.ai_seo.requiredIdentity).toEqual(["country", "state"]);
  });

  it("asks nothing extra of the two products a lead row already satisfies", () => {
    expect(FULL_AUDIT_PRODUCTS.technical_seo.requiredIdentity).toEqual([]);
    expect(FULL_AUDIT_PRODUCTS.onpage_seo.requiredIdentity).toEqual([]);
  });

  it("declares paths without the version prefix", () => {
    // basePath is the BFF service's business ("/v1" for On-Page, none for
    // Technical SEO). Repeating it here is how the two silently drift into
    // 404s against the service root.
    for (const product of Object.values(FULL_AUDIT_PRODUCTS)) {
      expect(product.submitPath.startsWith("/v")).toBe(false);
      expect(product.statusPath("abc").startsWith("/v")).toBe(false);
    }
  });

  it("percent-encodes the audit id into the status path", () => {
    expect(FULL_AUDIT_PRODUCTS.onpage_seo.statusPath("a/../b")).toBe("/audits/a%2F..%2Fb");
  });
});

describe("seedUrlForLead", () => {
  it("accepts a stored absolute URL", () => {
    expect(seedUrlForLead({ domainUrl: "https://wahhadesign.com" })).toBe(
      "https://wahhadesign.com/",
    );
  });

  it("rejects a scheme-less host rather than guessing one", () => {
    // Technical SEO answers 202 to this and only fails inside the worker, so
    // guessing would spend a real job slot to produce a failure minutes later.
    expect(seedUrlForLead({ domainUrl: "wahhadesign.com" })).toBeNull();
  });

  it("rejects a lead with no domain, and non-http schemes", () => {
    expect(seedUrlForLead({})).toBeNull();
    expect(seedUrlForLead({ domainUrl: "   " })).toBeNull();
    expect(seedUrlForLead({ domainUrl: "javascript:alert(1)" })).toBeNull();
    expect(seedUrlForLead({ domainUrl: "file:///etc/passwd" })).toBeNull();
  });
});

describe("readUpstreamStatus", () => {
  it("prefers the translated status when the service sends one", () => {
    // On-Page reports its own 14-value vocabulary in `status` and the shared one
    // in `dashboard_status`. Reading `status` here would have the lead row and
    // the tool page disagree about whether a run finished.
    expect(readUpstreamStatus({ status: "coverage_limited", dashboard_status: "completed_partial" }))
      .toBe("completed_partial");
  });

  it("falls back to the service's own status", () => {
    expect(readUpstreamStatus({ status: "running" })).toBe("running");
  });

  it("treats a missing status as queued rather than finished", () => {
    // Failing the other way would mark a run complete that never started.
    expect(readUpstreamStatus({})).toBe("queued");
    expect(readUpstreamStatus(null)).toBe("queued");
  });
});

describe("terminal and success vocabulary", () => {
  it("counts every ending as terminal", () => {
    for (const status of ["completed", "completed_partial", "failed", "cancelled", "interrupted"]) {
      expect(isTerminalStatus(status)).toBe(true);
    }
    expect(isTerminalStatus("queued")).toBe(false);
    expect(isTerminalStatus("running")).toBe(false);
  });

  it("counts a partial run as a success", () => {
    // On-Page reports partial on essentially every run; treating it as failure
    // would mark almost every On-Page audit broken.
    expect(isSuccessStatus("completed_partial")).toBe(true);
    expect(isSuccessStatus("completed")).toBe(true);
    expect(isSuccessStatus("failed")).toBe(false);
    expect(isSuccessStatus("interrupted")).toBe(false);
  });
});

describe("fullAuditSubmitBody", () => {
  const TECH = FULL_AUDIT_PRODUCTS.technical_seo;
  const AI = FULL_AUDIT_PRODUCTS.ai_seo;

  it("sends the two-key shape for a product that needs no identity", () => {
    expect(
      fullAuditSubmitBody({ name: "Schein Dental" }, "https://scheindentalnc.com/", TECH, {}),
    ).toEqual({
      seed_urls: ["https://scheindentalnc.com/"],
      business_name: "Schein Dental",
    });
  });

  it("omits an unusable name rather than failing the run", () => {
    // business_name is optional everywhere and, for the two non-AI products,
    // only seeds the PDF cover — a bad one must not cost the operator the audit.
    expect(fullAuditSubmitBody({ name: "   " }, "https://x.com/", TECH, {})).toEqual({
      seed_urls: ["https://x.com/"],
    });
    expect(fullAuditSubmitBody({}, "https://x.com/", TECH, {})).toEqual({
      seed_urls: ["https://x.com/"],
    });
  });

  it("never leaks identity fields to a product that did not ask for them", () => {
    // The same rule IDENTITY_AWARE_AUDIT_TYPES enforces in audits.ts: withheld
    // rather than sent and ignored.
    expect(
      fullAuditSubmitBody({ name: "X" }, "https://x.com/", TECH, {
        country: "United States",
        state: "Texas",
      }),
    ).toEqual({ seed_urls: ["https://x.com/"], business_name: "X" });
  });

  it("lets the operator's business name override the lead's own", () => {
    // The lead row's name is a fallback, not the truth: the funnel field behind
    // it is labelled "Name*" and often holds a contact. For AI SEO that value is
    // the primary Knowledge Graph query term, so the correction has to win.
    const body = fullAuditSubmitBody({ name: "Jainil" }, "https://wahhadesign.com/", AI, {
      businessName: "Wahha Design",
      country: "United States",
      state: "North Carolina",
    });
    expect(body.business_name).toBe("Wahha Design");
    // and never as a stray camelCase key the backend would ignore
    expect(body.businessName).toBeUndefined();
  });

  it("keeps the lead's name when no override is given", () => {
    const body = fullAuditSubmitBody({ name: "Schein Dental" }, "https://x.com/", AI, {
      businessName: "   ",
      country: "United States",
      state: "Texas",
    });
    expect(body.business_name).toBe("Schein Dental");
  });

  it("cannot have its name overridden on a product that never asked", () => {
    // technical_seo declares no identity, so a stray businessName in the body is
    // ignored rather than silently rewriting the run's name.
    const body = fullAuditSubmitBody({ name: "Schein Dental" }, "https://x.com/", TECH, {
      businessName: "Something Else",
    });
    expect(body.business_name).toBe("Schein Dental");
  });

  it("carries the declared identity for AI SEO", () => {
    expect(
      fullAuditSubmitBody({ name: "Wahha Design" }, "https://wahhadesign.com/", AI, {
        country: "United States",
        state: "North Carolina",
        city: "Wilmington",
        businessType: "Marketing Agency",
      }),
    ).toEqual({
      seed_urls: ["https://wahhadesign.com/"],
      business_name: "Wahha Design",
      country: "United States",
      state: "North Carolina",
      city: "Wilmington",
      businessType: "Marketing Agency",
    });
  });

  it("omits a blank optional identity field rather than padding it", () => {
    // The whole reason this product asks instead of defaulting: the backend
    // treats an absent field as "not known" and drops it from the provider
    // query, whereas a padded one resolves to a different company.
    expect(
      fullAuditSubmitBody({ name: "Wahha" }, "https://x.com/", AI, {
        country: "United States",
        state: "Texas",
        city: "   ",
        businessType: "",
      }),
    ).toEqual({
      seed_urls: ["https://x.com/"],
      business_name: "Wahha",
      country: "United States",
      state: "Texas",
    });
  });
});

describe("missingIdentityFields", () => {
  it("names what AI SEO is still missing", () => {
    expect(missingIdentityFields(FULL_AUDIT_PRODUCTS.ai_seo, {})).toEqual(["country", "state"]);
    expect(missingIdentityFields(FULL_AUDIT_PRODUCTS.ai_seo, { country: "United States" })).toEqual(
      ["state"],
    );
  });

  it("treats whitespace as missing", () => {
    // The upstream require_non_blank validator rejects "   " too; catching it
    // here turns a 502 into the console simply re-asking for the field.
    expect(
      missingIdentityFields(FULL_AUDIT_PRODUCTS.ai_seo, { country: "  ", state: "\t" }),
    ).toEqual(["country", "state"]);
  });

  it("asks nothing of the products that need nothing", () => {
    expect(missingIdentityFields(FULL_AUDIT_PRODUCTS.technical_seo, {})).toEqual([]);
    expect(missingIdentityFields(FULL_AUDIT_PRODUCTS.onpage_seo, {})).toEqual([]);
  });
});

describe("hasRunInFlight", () => {
  /** A run this console actually started — id AND start stamp together. */
  const started = (auditStatus) => ({
    auditId: "audit_1",
    auditStatus,
    fullAuditStartedAt: "2026-09-07T12:00:00.000Z",
  });

  it("blocks a second start while a run is going", () => {
    expect(hasRunInFlight(started("running"))).toBe(true);
    expect(hasRunInFlight(started("queued"))).toBe(true);
  });

  it("reopens once the run reaches any terminal state", () => {
    for (const status of ["completed", "completed_partial", "failed", "cancelled", "interrupted"]) {
      expect(hasRunInFlight(started(status))).toBe(false);
    }
  });

  it("does not wedge the button on a row written before statuses were tracked", () => {
    // An id with no status came from the older code path. Treating it as
    // in-flight would disable "Run full audit" on that lead permanently.
    expect(hasRunInFlight({ auditId: "audit_1", fullAuditStartedAt: "2026-09-07T12:00:00.000Z" }))
      .toBe(false);
    expect(hasRunInFlight({})).toBe(false);
  });

  /* The regression this whole provenance column exists for.

     Every ai_seo lead in production carried audit_id + audit_status="complete",
     pushed in by the funnel's own quick audit on a deployment this dashboard has
     no address for. Without a start stamp those rows read as "a full audit is
     already running", so POST /full-audit answered `attached` and never
     submitted anything — no AI SEO full audit was created for weeks, silently. */
  it("ignores an audit id the funnel pushed in, whatever its status", () => {
    // No fullAuditStartedAt: the summary webhook never sets one.
    expect(hasRunInFlight({ auditId: "funnel_1", auditStatus: "complete" })).toBe(false);
    expect(hasRunInFlight({ auditId: "funnel_1", auditStatus: "running" })).toBe(false);
    expect(hasRunInFlight({ auditId: "funnel_1", auditStatus: "queued" })).toBe(false);
  });

  it("normalizes the stored status before judging it", () => {
    // "complete" is AI SEO's own word for "completed". Read literally it is
    // non-terminal, which is precisely how the deadlock formed.
    expect(hasRunInFlight(started("complete"))).toBe(false);
    expect(hasRunInFlight(started("completed_with_errors"))).toBe(false);
    expect(hasRunInFlight(started("  RUNNING  "))).toBe(true);
  });
});

describe("normalizeAuditStatus", () => {
  it("maps every foreign word this dashboard has met to the shared vocabulary", () => {
    expect(normalizeAuditStatus("complete")).toBe("completed");
    expect(normalizeAuditStatus("completed_with_errors")).toBe("completed_partial");
    expect(normalizeAuditStatus("coverage_limited")).toBe("completed_partial");
    expect(normalizeAuditStatus("error")).toBe("failed");
    expect(normalizeAuditStatus("pending")).toBe("queued");
    expect(normalizeAuditStatus("in_progress")).toBe("running");
  });

  it("is case- and whitespace-insensitive", () => {
    expect(normalizeAuditStatus("  Complete ")).toBe("completed");
  });

  it("leaves an already-shared word alone", () => {
    for (const status of ["queued", "running", "completed", "completed_partial", "failed"]) {
      expect(normalizeAuditStatus(status)).toBe(status);
    }
  });

  it("returns empty for an absent value rather than guessing", () => {
    // Callers disagree about what absence means, so none of them may be handed
    // a default here: the status route substitutes "queued", the summary webhook
    // must leave the stored status untouched.
    expect(normalizeAuditStatus(undefined)).toBe("");
    expect(normalizeAuditStatus("")).toBe("");
    expect(normalizeAuditStatus("   ")).toBe("");
    expect(normalizeAuditStatus(null)).toBe("");
  });

  it("passes an unknown word through AND reports it", () => {
    const warnings = [];
    expect(normalizeAuditStatus("half_done", (m) => warnings.push(m))).toBe("half_done");
    expect(warnings).toHaveLength(1);
    expect(warnings[0]).toMatch(/unrecognised audit status "half_done"/);
  });

  it("says nothing about a word it knows", () => {
    const warnings = [];
    normalizeAuditStatus("complete", (m) => warnings.push(m));
    expect(warnings).toEqual([]);
  });
});

describe("readUpstreamStatus", () => {
  it("prefers the translated dashboard_status over the service's own word", () => {
    expect(
      readUpstreamStatus({ status: "completed_with_errors", dashboard_status: "completed_partial" }),
    ).toBe("completed_partial");
  });

  it("normalizes the service's own word when there is no translation", () => {
    // Technical SEO and AI SEO send no dashboard_status; AI SEO's native word
    // for a finished run is "complete".
    expect(readUpstreamStatus({ status: "complete" })).toBe("completed");
  });

  it("falls back to queued for a payload with no status at all", () => {
    expect(readUpstreamStatus({})).toBe("queued");
    expect(readUpstreamStatus(null)).toBe("queued");
  });
});

describe("isStaleRun", () => {
  const now = Date.parse("2026-09-01T12:00:00.000Z");

  it("writes off a run that has been going far too long", () => {
    // The case this exists for: an On-Page run sits at `queued` forever when the
    // control-plane relay is not running, and without a cutoff that lead's
    // duplicate-run guard would never reopen.
    const started = new Date(now - FULL_AUDIT_MAX_AGE_MS - 1000).toISOString();
    expect(isStaleRun({ started_at: started }, { now })).toBe(true);
  });

  it("leaves a merely slow run alone", () => {
    // Technical SEO's job_timeout is 86400s, so hours of silence is legitimate.
    const started = new Date(now - 6 * 60 * 60 * 1000).toISOString();
    expect(isStaleRun({ started_at: started }, { now })).toBe(false);
  });

  it("falls back to submitted_at, and never guesses without a timestamp", () => {
    const old = new Date(now - FULL_AUDIT_MAX_AGE_MS - 1000).toISOString();
    expect(isStaleRun({ submitted_at: old }, { now })).toBe(true);
    // A service that reports neither must never have its runs killed on a guess.
    expect(isStaleRun({}, { now })).toBe(false);
    expect(isStaleRun({ started_at: "not a date" }, { now })).toBe(false);
  });
});
