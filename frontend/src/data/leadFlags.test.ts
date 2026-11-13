import { describe, expect, it } from "vitest";
import type { Lead, LeadType } from "../services/api/leadMagnet";
import {
  buildLeadRows,
  normalizeDomain,
  normalizeEmail,
  rowMatchesQuery,
} from "./leadFlags";

let n = 0;
function lead(over: Partial<Lead> & { email: string; type: LeadType }): Lead {
  n += 1;
  return {
    id: over.id ?? `id-${n}`,
    name: over.name ?? `Person ${n}`,
    email: over.email,
    type: over.type,
    // Distinct, ascending timestamps unless a test pins one.
    timestamp: over.timestamp ?? new Date(Date.UTC(2026, 0, n)).toISOString(),
    domainUrl: over.domainUrl,
    phone: over.phone,
    details: over.details,
    notes: over.notes,
    seq: over.seq,
  };
}

describe("normalizeEmail", () => {
  it("ignores case and surrounding space", () => {
    expect(normalizeEmail("  Jai@Wahha.com ")).toBe("jai@wahha.com");
  });

  it("keeps plus-addressing distinct — it is a different mailbox to reply to", () => {
    expect(normalizeEmail("a+seo@x.com")).not.toBe(normalizeEmail("a@x.com"));
  });
});

describe("normalizeDomain", () => {
  it("strips protocol, www and trailing slashes", () => {
    const forms = [
      "https://www.wahhadesign.com/",
      "http://wahhadesign.com",
      "WWW.WahhaDesign.com//",
      " wahhadesign.com ",
    ];
    for (const f of forms) expect(normalizeDomain(f)).toBe("wahhadesign.com");
  });

  it("keeps different hosts apart", () => {
    expect(normalizeDomain("https://a.com")).not.toBe(normalizeDomain("https://b.com"));
  });
});

describe("buildLeadRows — repeats", () => {
  it("leaves distinct people as their own rows", () => {
    const rows = buildLeadRows([
      lead({ email: "a@x.com", type: "technical_seo" }),
      lead({ email: "b@x.com", type: "technical_seo" }),
    ]);
    expect(rows).toHaveLength(2);
    expect(rows.every((r) => r.flags)).toBe(true);
    expect(rows.flatMap((r) => r.flags)).toHaveLength(0);
  });

  it("collapses the same email + same type into one row", () => {
    const rows = buildLeadRows([
      lead({ id: "old", email: "a@x.com", type: "technical_seo" }),
      lead({ id: "new", email: "A@X.com", type: "technical_seo" }),
    ]);
    expect(rows).toHaveLength(1);
    expect(rows[0].submissions).toHaveLength(2);
    expect(rows[0].flags).toEqual([{ kind: "repeat", count: 2, type: "technical_seo" }]);
  });

  it("shows the newest submission as the row, whatever order they arrive in", () => {
    const rows = buildLeadRows([
      lead({ id: "older", email: "a@x.com", type: "ai_seo", timestamp: "2026-01-01T00:00:00Z" }),
      lead({ id: "newest", email: "a@x.com", type: "ai_seo", timestamp: "2026-03-01T00:00:00Z" }),
      lead({ id: "middle", email: "a@x.com", type: "ai_seo", timestamp: "2026-02-01T00:00:00Z" }),
    ]);
    expect(rows[0].lead.id).toBe("newest");
    expect(rows[0].submissions.map((s) => s.id)).toEqual(["newest", "middle", "older"]);
  });

  it("does NOT collapse the same email across different audit types", () => {
    const rows = buildLeadRows([
      lead({ email: "a@x.com", type: "technical_seo" }),
      lead({ email: "a@x.com", type: "onpage_seo" }),
    ]);
    expect(rows).toHaveLength(2);
    expect(rows.flatMap((r) => r.flags)).toHaveLength(0);
  });

  it("never merges leads that have no email", () => {
    const rows = buildLeadRows([
      lead({ id: "x", email: "", type: "ai_seo" }),
      lead({ id: "y", email: "   ", type: "ai_seo" }),
    ]);
    expect(rows).toHaveLength(2);
    expect(rows.flatMap((r) => r.flags)).toHaveLength(0);
  });

  it("a malformed timestamp cannot become the representative", () => {
    const rows = buildLeadRows([
      lead({ id: "real", email: "a@x.com", type: "ai_seo", timestamp: "2026-05-01T00:00:00Z" }),
      lead({ id: "broken", email: "a@x.com", type: "ai_seo", timestamp: "not a date" }),
    ]);
    expect(rows[0].lead.id).toBe("real");
  });
});

describe("buildLeadRows — contested domains", () => {
  const d = "https://shared.com";

  it("does not flag a domain below the audit threshold", () => {
    const rows = buildLeadRows([
      lead({ email: "a@x.com", type: "technical_seo", domainUrl: d }),
      lead({ email: "b@x.com", type: "technical_seo", domainUrl: d }),
    ]);
    expect(rows.flatMap((r) => r.flags)).toHaveLength(0);
  });

  it("does not flag one person auditing their own domain repeatedly", () => {
    // 3 audits, but a single person — that is a repeat, not a contested domain.
    const rows = buildLeadRows([
      lead({ email: "a@x.com", type: "technical_seo", domainUrl: d }),
      lead({ email: "a@x.com", type: "onpage_seo", domainUrl: d }),
      lead({ email: "a@x.com", type: "ai_seo", domainUrl: d }),
    ]);
    expect(rows.flatMap((r) => r.flags).filter((f) => f.kind === "contested-domain")).toHaveLength(
      0,
    );
  });

  it("flags once 3 audits come from 2+ different people", () => {
    const rows = buildLeadRows([
      lead({ email: "a@x.com", type: "technical_seo", domainUrl: d }),
      lead({ email: "b@x.com", type: "technical_seo", domainUrl: d }),
      lead({ email: "c@x.com", type: "technical_seo", domainUrl: d }),
    ]);
    expect(rows).toHaveLength(3);
    // Every row on that host carries the flag — the point is the host.
    for (const row of rows) {
      expect(row.flags).toContainEqual({
        kind: "contested-domain",
        host: "shared.com",
        audits: 3,
        people: 3,
      });
    }
  });

  it("counts audits before collapsing, not rows after", () => {
    // a@ submits twice (one row) + b@ once = 3 audits on the host, 2 people.
    const rows = buildLeadRows([
      lead({ email: "a@x.com", type: "technical_seo", domainUrl: d }),
      lead({ email: "a@x.com", type: "technical_seo", domainUrl: d }),
      lead({ email: "b@x.com", type: "technical_seo", domainUrl: d }),
    ]);
    expect(rows).toHaveLength(2);
    const flag = rows[0].flags.find((f) => f.kind === "contested-domain");
    expect(flag).toEqual({
      kind: "contested-domain",
      host: "shared.com",
      audits: 3,
      people: 2,
    });
  });

  it("matches hosts across protocol and www differences", () => {
    const rows = buildLeadRows([
      lead({ email: "a@x.com", type: "technical_seo", domainUrl: "https://www.shared.com/" }),
      lead({ email: "b@x.com", type: "technical_seo", domainUrl: "http://shared.com" }),
      lead({ email: "c@x.com", type: "technical_seo", domainUrl: "shared.com/" }),
    ]);
    expect(rows.flatMap((r) => r.flags).filter((f) => f.kind === "contested-domain")).toHaveLength(
      3,
    );
  });

  it("ignores leads with no domain", () => {
    const rows = buildLeadRows([
      lead({ email: "a@x.com", type: "technical_seo" }),
      lead({ email: "b@x.com", type: "technical_seo" }),
      lead({ email: "c@x.com", type: "technical_seo" }),
    ]);
    expect(rows.flatMap((r) => r.flags)).toHaveLength(0);
  });

  it("carries both flags when a row is a repeat on a contested domain", () => {
    const rows = buildLeadRows([
      lead({ email: "a@x.com", type: "technical_seo", domainUrl: d }),
      lead({ email: "a@x.com", type: "technical_seo", domainUrl: d }),
      lead({ email: "b@x.com", type: "technical_seo", domainUrl: d }),
    ]);
    const repeatRow = rows.find((r) => r.submissions.length === 2);
    expect(repeatRow?.flags.map((f) => f.kind).sort()).toEqual([
      "contested-domain",
      "repeat",
    ]);
  });
});

describe("rowMatchesQuery", () => {
  const rows = buildLeadRows([
    lead({ id: "new", email: "a@x.com", name: "Newer Name", type: "ai_seo", domainUrl: "https://n.com" }),
    lead({ id: "old", email: "a@x.com", name: "Older Name", type: "ai_seo", domainUrl: "https://o.com" }),
  ]);

  it("matches on the representative", () => {
    expect(rowMatchesQuery(rows[0], "Newer")).toBe(true);
  });

  it("also matches on a collapsed submission, so searching cannot hide the row", () => {
    expect(rowMatchesQuery(rows[0], "Older")).toBe(true);
    expect(rowMatchesQuery(rows[0], "o.com")).toBe(true);
  });

  it("returns everything for an empty query", () => {
    expect(rowMatchesQuery(rows[0], "   ")).toBe(true);
  });

  it("rejects a genuine miss", () => {
    expect(rowMatchesQuery(rows[0], "nobody")).toBe(false);
  });
});
