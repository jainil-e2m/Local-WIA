import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createLeadsStore, sanitizeDetails, LeadsError, LIMITS } from "./leads-store.mjs";

let dir;
let file;
let opened;

beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "wahha-leads-"));
  file = path.join(dir, "nested", "leads.json");
  opened = [];
});

afterEach(async () => {
  // Let queued writes land before the directory disappears, otherwise an
  // in-flight rename races teardown and logs a spurious ENOENT.
  await Promise.all(opened.map((store) => store.flush().catch(() => {})));
  fs.rmSync(dir, { recursive: true, force: true });
});

const open = (options) => {
  const store = createLeadsStore(file, { now: () => 1_700_000_000_000, ...options });
  opened.push(store);
  return store;
};

const VALID = {
  name: "Sarah Jenkins",
  email: "sarah.j@apexindustrial.com",
  phone: "(919) 555-0142",
  domainUrl: "https://apexindustrial.com",
  type: "technical_seo",
  details: { score: 68, grade: "C+", passed: 7, warnings: 8, critical: 4 },
};

/** Write a store document straight to disk, bypassing the write queue. */
const seedFile = (leads) => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify({ version: 1, leads }), "utf8");
};

describe("sanitizeDetails (whitelist boundary)", () => {
  it("keeps only known fields with valid values", () => {
    expect(
      sanitizeDetails({
        score: 74.4,
        grade: "C+",
        passed: 8,
        warnings: 6,
        critical: 3,
        scheduler_cron: "FULL_AUDIT_COMPLETED",
        last_audit_time: "2026-08-13T10:00:00.000Z",
        enquiry: "retired field",
        __proto__x: "junk",
      }),
    ).toEqual({
      score: 74,
      grade: "C+",
      passed: 8,
      warnings: 6,
      critical: 3,
      scheduler_cron: "FULL_AUDIT_COMPLETED",
      last_audit_time: "2026-08-13T10:00:00.000Z",
    });
  });

  it("drops out-of-range and malformed values field-by-field", () => {
    expect(
      sanitizeDetails({ score: 101, passed: -1, warnings: 2.5, critical: "x", grade: "" }),
    ).toBeUndefined();
    expect(sanitizeDetails({ score: -5, passed: 3 })).toEqual({ passed: 3 });
    expect(sanitizeDetails({ last_audit_time: "not a date", score: 100 })).toEqual({ score: 100 });
  });

  it("returns undefined for junk input", () => {
    expect(sanitizeDetails(undefined)).toBeUndefined();
    expect(sanitizeDetails(null)).toBeUndefined();
    expect(sanitizeDetails("string")).toBeUndefined();
    expect(sanitizeDetails([1, 2])).toBeUndefined();
    expect(sanitizeDetails({})).toBeUndefined();
  });
});

describe("createLead", () => {
  it("stores a valid lead with a server id and timestamp", async () => {
    const store = open();
    const lead = await store.createLead(VALID);
    expect(lead.id).toMatch(/^lead_[0-9a-f-]{36}$/);
    expect(lead.timestamp).toBe("2023-11-14T22:13:20.000Z"); // fixed `now`
    expect(lead.name).toBe(VALID.name);
    expect(lead.email).toBe(VALID.email);
    expect(lead.type).toBe("technical_seo");
    expect(lead.details).toEqual(VALID.details);
    expect(store.read().leads).toHaveLength(1);
  });

  it("normalizes a bare-host domain and lowercases the email", async () => {
    const store = open();
    const lead = await store.createLead({
      ...VALID,
      email: "Sarah.J@ApexIndustrial.com",
      domainUrl: "apexindustrial.com",
    });
    expect(lead.email).toBe("sarah.j@apexindustrial.com");
    expect(lead.domainUrl).toBe("https://apexindustrial.com/");
  });

  it("drops an unusable domainUrl instead of losing the lead", async () => {
    const store = open();
    const lead = await store.createLead({ ...VALID, domainUrl: "javascript:alert(1)" });
    expect(lead.domainUrl).toBeUndefined();
    expect(store.read().leads).toHaveLength(1);
  });

  it("rejects a missing name, bad email, and retired or unknown types", async () => {
    const store = open();
    await expect(store.createLead({ ...VALID, name: "  " })).rejects.toMatchObject({
      code: "invalid_name",
    });
    await expect(store.createLead({ ...VALID, email: "not-an-email" })).rejects.toMatchObject({
      code: "invalid_email",
    });
    for (const type of ["contact_form", "seo_audit", "nonsense", undefined]) {
      await expect(store.createLead({ ...VALID, type })).rejects.toMatchObject({
        code: "invalid_type",
      });
    }
    expect(store.read().leads).toHaveLength(0);
  });

  it("enforces the lead cap with a 409", async () => {
    const store = open();
    seedFile(
      Array.from({ length: LIMITS.leads }, (_, i) => ({
        id: `lead_${i}`,
        name: `Lead ${i}`,
        email: `lead${i}@example.com`,
        type: "ai_seo",
        timestamp: "2026-01-01T00:00:00.000Z",
      })),
    );
    const full = open();
    await expect(full.createLead(VALID)).rejects.toMatchObject({
      code: "limit_reached",
      status: 409,
    });
    expect(store).toBeDefined(); // first store only exists to register cleanup
  });
});

/* The On-Page funnel saves the same lead twice — once at form submit, once when
   the audit resolves — reusing one capture id. Before these tests that second
   save created a DUPLICATE lead here (and raised a unique violation on the
   Postgres store, which the funnel swallows), so the audit summary never landed
   on the lead and every On-Page lead showed no score. */
describe("createLead is idempotent on captureId", () => {
  const CAPTURE = "cap_11111111-2222-3333-4444-555555555555";

  it("merges the second save into the first lead rather than adding a row", async () => {
    const store = open();
    const first = await store.createLead({
      ...VALID,
      details: undefined,
      captureId: CAPTURE,
    });
    const second = await store.createLead({
      ...VALID,
      details: { score: 82, passed: 14, critical: 0, warnings: 2, opportunities: 12 },
      captureId: CAPTURE,
    });

    expect(second.id).toBe(first.id);
    expect(store.read().leads.length).toBe(1);
    expect(second.details).toMatchObject({
      score: 82,
      passed: 14,
      critical: 0,
      warnings: 2,
      opportunities: 12,
    });
  });

  it("does not blank stored metrics when a later save omits them", async () => {
    const store = open();
    await store.createLead({ ...VALID, details: { score: 82, passed: 14 }, captureId: CAPTURE });
    const merged = await store.createLead({ ...VALID, details: { critical: 3 }, captureId: CAPTURE });

    expect(merged.details.score).toBe(82);
    expect(merged.details.passed).toBe(14);
    expect(merged.details.critical).toBe(3);
  });

  it("still creates separate leads when no captureId is supplied", async () => {
    const store = open();
    await store.createLead({ ...VALID });
    await store.createLead({ ...VALID });
    expect(store.read().leads.length).toBe(2);
  });

  it("keeps distinct captureIds distinct", async () => {
    const store = open();
    await store.createLead({ ...VALID, captureId: CAPTURE });
    await store.createLead({ ...VALID, captureId: "cap_99999999-8888-7777-6666-555555555555" });
    expect(store.read().leads.length).toBe(2);
  });
});

/* Technical and AI SEO mint `audit_`-prefixed ids; the On-Page snapshot service
   mints bare 32-char hex with no prefix. The original prefix-only pattern dropped
   every On-Page audit id, so those leads could not be correlated back to the
   audit that produced them.

   The guard is deliberately about CHARACTER SET, not shape: this value is
   rendered into a URL, and what must be impossible is a slash, dot, colon or
   percent escaping into it. A token that is merely unfamiliar is not a threat, so
   it is allowed through rather than silently discarded -- silent discarding is
   precisely what caused the bug. */
describe("sanitizeDetails and the audit id", () => {
  it("keeps an audit_-prefixed id (technical / ai seo)", () => {
    expect(sanitizeDetails({ audit_id: "audit_01HQ8XK3M2NPQR" })).toMatchObject({
      audit_id: "audit_01HQ8XK3M2NPQR",
    });
  });

  it("keeps a bare 32-char hex id (on-page snapshot)", () => {
    // A real id, from a production On-Page audit run against wahhadesign.com.
    expect(sanitizeDetails({ audit_id: "e990bb5318f84bffa13d7d999c4387b2" })).toMatchObject({
      audit_id: "e990bb5318f84bffa13d7d999c4387b2",
    });
  });

  it("keeps an unfamiliar but URL-safe token rather than dropping it silently", () => {
    /* Regression guard for the original bug: a shape nobody anticipated must not
       vanish. A fourth product with a fifth id format needs no code change. */
    expect(sanitizeDetails({ audit_id: "zzzz" })?.audit_id).toBe("zzzz");
  });

  it("rejects anything that could break out of the URL it is rendered into", () => {
    for (const hostile of [
      "../etc/passwd",
      "audit id with spaces",
      "audit/../../secret",
      "audit.id.with.dots",
      "http://evil.test",
      "audit%2Fescaped",
      "audit?query=1",
      "audit#fragment",
      "audit&next=2",
    ]) {
      expect(
        sanitizeDetails({ audit_id: hostile })?.audit_id,
        `${hostile} must never reach a URL`,
      ).toBeUndefined();
    }
  });
});

describe("read ordering", () => {
  it("returns leads newest-first (the prior-audit lookup depends on it)", async () => {
    let tick = 1_700_000_000_000;
    const store = open({ now: () => (tick += 60_000) });
    const first = await store.createLead({ ...VALID, name: "Older" });
    const second = await store.createLead({ ...VALID, name: "Newer" });
    const { leads } = store.read();
    expect(leads.map((lead) => lead.id)).toEqual([second.id, first.id]);
  });
});

describe("updateLead", () => {
  it("merges details per-field and keeps id/type/timestamp immutable", async () => {
    const store = open();
    const lead = await store.createLead(VALID);
    const updated = await store.updateLead(lead.id, {
      id: "lead_hijack",
      type: "ai_seo",
      timestamp: "1999-01-01T00:00:00.000Z",
      details: { score: 79, scheduler_cron: "FULL_AUDIT_COMPLETED" },
    });
    expect(updated.id).toBe(lead.id);
    expect(updated.type).toBe("technical_seo");
    expect(updated.timestamp).toBe(lead.timestamp);
    expect(updated.details).toEqual({
      score: 79,
      grade: "C+",
      passed: 7,
      warnings: 8,
      critical: 4,
      scheduler_cron: "FULL_AUDIT_COMPLETED",
    });
  });

  it("validates patched contact fields and clears emptied optionals", async () => {
    const store = open();
    const lead = await store.createLead(VALID);
    await expect(store.updateLead(lead.id, { email: "nope" })).rejects.toMatchObject({
      code: "invalid_email",
    });
    const cleared = await store.updateLead(lead.id, { phone: "", domainUrl: "" });
    expect(cleared.phone).toBeUndefined();
    expect(cleared.domainUrl).toBeUndefined();
  });

  it("404s for an unknown id", async () => {
    const store = open();
    await expect(store.updateLead("lead_missing", {})).rejects.toMatchObject({
      code: "not_found",
      status: 404,
    });
  });
});

describe("seq (human-readable display number)", () => {
  it("starts at 1 and increments by 1", async () => {
    let tick = 1_700_000_000_000;
    const store = open({ now: () => (tick += 60_000) });
    const first = await store.createLead(VALID);
    const second = await store.createLead(VALID);
    const third = await store.createLead(VALID);
    expect([first.seq, second.seq, third.seq]).toEqual([1, 2, 3]);
  });

  it("never reuses a number after a delete", async () => {
    let tick = 1_700_000_000_000;
    const store = open({ now: () => (tick += 60_000) });
    const first = await store.createLead(VALID);
    const second = await store.createLead(VALID);
    await store.removeLead(second.id);
    const third = await store.createLead(VALID);
    // 2 is retired with the lead that owned it — reusing it would make two
    // different leads share an id in someone's notes.
    expect(third.seq).toBe(3);
    expect(first.seq).toBe(1);
  });

  it("survives a disk round-trip and keeps counting from where it left off", async () => {
    let tick = 1_700_000_000_000;
    const store = open({ now: () => (tick += 60_000) });
    await store.createLead(VALID);
    await store.createLead(VALID);
    await store.flush();

    const reopened = open({ now: () => (tick += 60_000) });
    expect(
      reopened
        .read()
        .leads.map((lead) => lead.seq)
        .sort(),
    ).toEqual([1, 2]);
    const next = await reopened.createLead(VALID);
    expect(next.seq).toBe(3);
  });

  it("backfills leads written before seq existed, oldest first", async () => {
    // Two legacy rows with no seq — the earliest capture must become lead_1.
    seedFile([
      {
        id: "lead_newer",
        name: "Newer",
        email: "newer@x.com",
        type: "ai_seo",
        timestamp: "2026-02-01T00:00:00.000Z",
      },
      {
        id: "lead_older",
        name: "Older",
        email: "older@x.com",
        type: "technical_seo",
        timestamp: "2026-01-01T00:00:00.000Z",
      },
    ]);
    const store = open();
    const bySeq = Object.fromEntries(store.read().leads.map((lead) => [lead.id, lead.seq]));
    expect(bySeq).toEqual({ lead_older: 1, lead_newer: 2 });
    const next = await store.createLead(VALID);
    expect(next.seq).toBe(3);
  });

  it("writes the backfill to disk so numbers aren't re-derived every boot", async () => {
    seedFile([
      {
        id: "lead_a",
        name: "A",
        email: "a@x.com",
        type: "ai_seo",
        timestamp: "2026-01-01T00:00:00.000Z",
      },
    ]);
    const store = open();
    await store.flush();
    const onDisk = JSON.parse(fs.readFileSync(file, "utf8"));
    expect(onDisk.leads[0].seq).toBe(1);
    expect(onDisk.nextSeq).toBe(2);
  });

  it("is immutable — a patch cannot renumber a lead", async () => {
    const store = open();
    const lead = await store.createLead(VALID);
    const patched = await store.updateLead(lead.id, { seq: 999, notes: "x" });
    expect(patched.seq).toBe(lead.seq);
  });
});

describe("notes (dashboard-authored, session-only)", () => {
  it("is ignored on create — the capture endpoint is public", async () => {
    const store = open();
    const lead = await store.createLead({ ...VALID, notes: "injected by a stranger" });
    expect(lead.notes).toBeUndefined();
    expect(store.read().leads[0].notes).toBeUndefined();
  });

  it("is set, replaced and cleared through updateLead", async () => {
    const store = open();
    const lead = await store.createLead(VALID);

    const withNote = await store.updateLead(lead.id, {
      notes: "  Called 14:00, asked for pricing.  ",
    });
    expect(withNote.notes).toBe("Called 14:00, asked for pricing.");

    const replaced = await store.updateLead(lead.id, { notes: "Follow up Tuesday." });
    expect(replaced.notes).toBe("Follow up Tuesday.");

    const cleared = await store.updateLead(lead.id, { notes: "   " });
    expect(cleared.notes).toBeUndefined();
  });

  it("leaves notes untouched when the patch omits them", async () => {
    const store = open();
    const lead = await store.createLead(VALID);
    await store.updateLead(lead.id, { notes: "Keep me" });
    const patched = await store.updateLead(lead.id, { details: { score: 90 } });
    expect(patched.notes).toBe("Keep me");
  });

  it("caps length and survives a disk round-trip", async () => {
    const store = open();
    const lead = await store.createLead(VALID);
    await store.updateLead(lead.id, { notes: "n".repeat(LIMITS.notesLength + 500) });
    await store.flush();
    const reopened = open();
    expect(reopened.read().leads[0].notes).toHaveLength(LIMITS.notesLength);
  });
});

describe("removeLead — a SOFT delete", () => {
  it("hides the lead, then 404s on a repeat", async () => {
    const store = open();
    const lead = await store.createLead(VALID);
    const removed = await store.removeLead(lead.id);
    expect(removed.id).toBe(lead.id);
    expect(store.read().leads).toHaveLength(0);
    await expect(store.removeLead(lead.id)).rejects.toMatchObject({ code: "not_found" });
  });

  it("keeps the record — it is hidden, not destroyed", async () => {
    // The point of the whole change: a prospect record is the output of paid
    // acquisition, and a misclick used to take the identity, the score, the
    // operator's notes and the booked call with no undo.
    const store = open();
    const lead = await store.createLead({ ...VALID, notes: undefined });
    await store.updateLead(lead.id, { notes: "spoke Tuesday, wants a callback" });
    await store.removeLead(lead.id);

    await store.flush();
    const raw = JSON.parse(fs.readFileSync(file, "utf8"));
    const stored = raw.leads.find((row) => row.id === lead.id);
    expect(stored).toBeDefined();
    expect(stored.leadActive).toBe(false);
    expect(stored.notes).toBe("spoke Tuesday, wants a callback");
    expect(stored.email).toBe(VALID.email);
  });

  it("stays hidden across a reload", async () => {
    // sanitizeState re-validates every field on read; dropping leadActive there
    // would un-delete every hidden lead on the next restart.
    const store = open();
    const lead = await store.createLead(VALID);
    await store.removeLead(lead.id);
    await store.flush();

    const reopened = open();
    expect(reopened.read().leads).toHaveLength(0);
    await expect(reopened.removeLead(lead.id)).rejects.toMatchObject({ code: "not_found" });
  });

  it("cannot be un-hidden through the store's own API", async () => {
    // Restoring is deliberately a manual decision made against the database.
    // No method here writes leadActive back to true — updateLead ignores it
    // because a hidden lead does not resolve in the first place.
    const store = open();
    const lead = await store.createLead(VALID);
    await store.removeLead(lead.id);
    await expect(
      store.updateLead(lead.id, { leadActive: true, name: "Restored" }),
    ).rejects.toMatchObject({ code: "not_found" });
    expect(store.read().leads).toHaveLength(0);
  });

  it("takes a hidden lead out of booking matching", async () => {
    // A booking must never attach to a lead the console has removed.
    const store = open();
    const lead = await store.createLead(VALID);
    await store.removeLead(lead.id);
    const matched = await store.applyMeeting({
      eventId: "evt_1",
      startsAt: new Date(Date.now() + 86_400_000).toISOString(),
      bookedEmail: VALID.email,
      bookedName: VALID.name,
      status: "booked",
    });
    expect(matched).toBeNull();
  });
});

describe("persistence", () => {
  it("round-trips through disk (create → flush → reopen)", async () => {
    const store = open();
    const lead = await store.createLead(VALID);
    await store.flush();
    const reopened = open();
    expect(reopened.read().leads).toEqual([lead]);
  });

  it("sanitizes a hand-edited file on load", async () => {
    seedFile([
      {
        id: "lead_ok",
        name: "Keep",
        email: "keep@x.com",
        type: "ai_seo",
        timestamp: "2026-01-01T00:00:00.000Z",
      },
      {
        id: "lead_retired",
        name: "Drop",
        email: "drop@x.com",
        type: "contact_form",
        timestamp: "2026-01-01T00:00:00.000Z",
      },
      {
        id: "lead_bad_email",
        name: "Drop",
        email: "junk",
        type: "ai_seo",
        timestamp: "2026-01-01T00:00:00.000Z",
      },
      {
        id: "lead_bad_time",
        name: "Drop",
        email: "t@x.com",
        type: "ai_seo",
        timestamp: "whenever",
      },
      { name: "no id", email: "n@x.com", type: "ai_seo", timestamp: "2026-01-01T00:00:00.000Z" },
      "not even an object",
    ]);
    const store = open();
    expect(store.read().leads.map((lead) => lead.id)).toEqual(["lead_ok"]);
  });

  it("starts empty on a corrupt file and reports the load error", () => {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, "{ not json", "utf8");
    const store = open();
    expect(store.read().leads).toEqual([]);
    expect(store.status().loadError).toBeTruthy();
  });

  describe("applyAuditSummary", () => {
    const capture = async (store) =>
      store.createLead({ ...VALID, type: "ai_seo", details: undefined, captureId: "cap_1" });

    it("records score and counts for a completed run", async () => {
      const store = open();
      await capture(store);
      const lead = await store.applyAuditSummary({
        capture_id: "cap_1",
        audit_id: "aud_1",
        status: "complete",
        score: 88,
        counts: { passed: 88, indeterminate: 7, critical: 2 },
      });
      expect(lead.auditId).toBe("aud_1");
      expect(lead.details.score).toBe(88);
      expect(lead.details.warnings).toBe(7);
    });

    // Regression: `Number(null)` is 0 and passes a 0..100 range check, so a
    // range-first guard stored a real-looking 0 for runs that never scored —
    // which the console then rendered as a genuine grade F.
    it("leaves score unset when a failed run reports score: null", async () => {
      const store = open();
      await capture(store);
      const lead = await store.applyAuditSummary({
        capture_id: "cap_1",
        audit_id: "aud_1",
        status: "failed",
        score: null,
        counts: null,
        error_message: "Site unreachable.",
      });
      expect(lead.auditStatus).toBe("failed");
      expect(lead.details?.score).toBeUndefined();
    });

    it("returns null when nothing matches the correlation keys", async () => {
      const store = open();
      await capture(store);
      expect(
        await store.applyAuditSummary({ capture_id: "cap_nope", status: "complete", score: 50 }),
      ).toBeNull();
    });

    it("rejects a summary carrying neither correlation key", async () => {
      const store = open();
      await expect(store.applyAuditSummary({ status: "complete" })).rejects.toThrow(LeadsError);
    });
  });

  it("LeadsError carries code and status for route mapping", () => {
    const error = new LeadsError("invalid_type", "msg", 400);
    expect(error).toBeInstanceOf(Error);
    expect(error.code).toBe("invalid_type");
    expect(error.status).toBe(400);
  });
});
