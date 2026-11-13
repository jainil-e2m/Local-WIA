/* The Postgres store, checked WITHOUT a Postgres.
   
   Why this file exists. leads-db.mjs is imported by index.mjs only when
   LEADS_DATABASE_URL is set, so nothing in the suite ever loaded it — and a
   syntax error inside it was therefore invisible to a green test run while being
   fatal in production, where the variable IS set. That happened: a prose comment
   written inside the createLead SQL used backticks around a column name, and
   because the SQL is a JS template literal the pair terminated the string. The
   file did not parse. Tests still passed.
   
   Importing the module is the whole point of the first test: `new pg.Pool` lives
   inside createLeadsDbStore, so import is side-effect-free and any parse or
   import failure surfaces here instead of at boot. */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SOURCE = fs.readFileSync(path.join(HERE, "leads-db.mjs"), "utf8");

describe("leads-db.mjs loads at all", () => {
  it("imports without throwing, and exports the factory index.mjs expects", async () => {
    const mod = await import("./leads-db.mjs");
    expect(typeof mod.createLeadsDbStore).toBe("function");
  });

  it("keeps every method the JSON store exposes, so index.mjs need not branch", async () => {
    const mod = await import("./leads-db.mjs");
    // Source-level, because building a real store needs a database. The two
    // stores are drop-in replacements; a method present in one and missing in
    // the other is a 500 the moment a deploy sets LEADS_DATABASE_URL.
    for (const method of [
      "createLead",
      "updateLead",
      "removeLead",
      "getLead",
      "setAuditRun",
      "applyAuditSummary",
    ]) {
      expect(SOURCE, `leads-db.mjs is missing ${method}`).toContain(`${method}(`);
    }
    expect(typeof mod.createLeadsDbStore).toBe("function");
  });
});

describe("the createLead upsert", () => {
  it("upserts on capture_id instead of plain-inserting", () => {
    /* The On-Page funnel saves one lead twice with a single capture id: once at
       form submit, once when the audit resolves. capture_id is UNIQUE, so a
       plain INSERT raised a unique violation on the second arrival, and because
       captureRemotely is fire-and-forget the failure was swallowed. The score,
       check counts and severity never reached the lead. */
    expect(SOURCE).toContain("ON CONFLICT (capture_id) DO UPDATE SET");
  });

  it("COALESCEs every metric so a later save cannot blank a stored value", () => {
    for (const column of [
      "score",
      "checks_passed",
      "checks_indeterminate",
      "severity_critical",
      "audit_completed_at",
    ]) {
      expect(SOURCE, `${column} is not COALESCEd in the upsert`).toContain(
        `COALESCE(EXCLUDED.${column}, leadmagnet_leads.${column})`,
      );
    }
  });

  it("does not update identity on conflict — the second save is enrichment", () => {
    /* Both arrivals carry the same name and email, so rewriting them buys
       nothing and would let a malformed replay overwrite a good record. */
    const upsert = SOURCE.slice(
      SOURCE.indexOf("ON CONFLICT (capture_id) DO UPDATE SET"),
      SOURCE.indexOf("RETURNING", SOURCE.indexOf("ON CONFLICT (capture_id)")),
    );
    expect(upsert).not.toMatch(/^\s*name\s*=/m);
    expect(upsert).not.toMatch(/^\s*email\s*=/m);
    expect(upsert).not.toMatch(/\bnotes\s*=/);
  });
});
