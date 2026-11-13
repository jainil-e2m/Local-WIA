/* The full-audit in-flight predicate.

   This is the console's half of a rule the server also implements: the row
   offers "Running" exactly when the server would ATTACH a start request to the
   existing run rather than launch a new one. The two live in different runtimes
   and cannot import each other, so the last test here reads the server's own
   vocabulary and asserts they still agree — the drift this file exists to catch
   would show up as a button that starts a duplicate run while claiming to watch
   one, and nothing else in the suite would notice. */
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { isFullAuditRunning, TERMINAL_AUDIT_STATUSES, type Lead } from "./leadMagnet";

const lead = (over: Partial<Lead> = {}): Lead => ({
  id: "lead-1",
  name: "Jamison Probst",
  email: "jamison@hickory.com",
  type: "technical_seo",
  timestamp: "2026-09-01T21:39:00.000Z",
  ...over,
});

/** A full run started from this console: id AND start stamp. */
const started = (over: Partial<Lead> = {}): Lead =>
  lead({ auditId: "a-1", fullAuditStartedAt: "2026-09-07T12:00:00.000Z", ...over });

describe("isFullAuditRunning", () => {
  it("is false for a lead that has never been audited", () => {
    expect(isFullAuditRunning(lead())).toBe(false);
  });

  it("is true for a queued run", () => {
    expect(isFullAuditRunning(started({ auditStatus: "queued" }))).toBe(true);
  });

  it("is true for a running run", () => {
    expect(isFullAuditRunning(started({ auditStatus: "running" }))).toBe(true);
  });

  it("is false once the run reaches any terminal status", () => {
    for (const status of TERMINAL_AUDIT_STATUSES) {
      expect(isFullAuditRunning(started({ auditStatus: status }))).toBe(false);
    }
  });

  /* The production regression. Every ai_seo lead carried an audit_id and
     audit_status "complete" pushed in by the funnel's quick audit — no full run
     had ever been started. Reading those as in-flight is what put the row on
     "Running" forever and made the start route attach instead of submit. */
  it("is false for an audit id the funnel pushed in (no start stamp)", () => {
    expect(isFullAuditRunning(lead({ auditId: "funnel-1", auditStatus: "complete" }))).toBe(false);
    expect(isFullAuditRunning(lead({ auditId: "funnel-1", auditStatus: "running" }))).toBe(false);
  });

  it("is false for an audit id with no recorded status", () => {
    // Written by an older code path that tracked none. Treating it as running
    // would pin the row on "Running" forever, with nothing able to clear it.
    expect(isFullAuditRunning(started())).toBe(false);
    expect(isFullAuditRunning(started({ auditStatus: "   " }))).toBe(false);
  });

  it("is false for a status with no audit id", () => {
    expect(isFullAuditRunning(lead({ auditStatus: "running", fullAuditStartedAt: "2026-09-07T12:00:00.000Z" }))).toBe(
      false,
    );
  });

  it("tolerates surrounding whitespace on the status", () => {
    expect(isFullAuditRunning(started({ auditStatus: " completed " }))).toBe(false);
  });

  it("matches the server's TERMINAL_FULL_AUDIT_STATUSES exactly", () => {
    // Resolved from the vitest root (frontend/), not from import.meta.url —
    // under vite's transform that is an http: URL, not a file: one.
    const source = readFileSync(resolve(process.cwd(), "server/leadmagnet-full-audit.mjs"), "utf8");
    const block = source.match(
      /export const TERMINAL_FULL_AUDIT_STATUSES = new Set\(\[([\s\S]*?)\]\)/,
    );
    expect(
      block,
      "server no longer declares TERMINAL_FULL_AUDIT_STATUSES as a literal Set",
    ).not.toBeNull();
    const serverStatuses = [...block![1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
    expect(serverStatuses.length).toBeGreaterThan(0);
    expect([...serverStatuses].sort()).toEqual([...TERMINAL_AUDIT_STATUSES].sort());
  });
});
