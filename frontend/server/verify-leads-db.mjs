/* Exercise the Postgres lead store against a REAL PostgreSQL.
 *
 *   LEADS_VERIFY_DATABASE_URL=postgresql://user:pass@host:port/db \
 *     node server/verify-leads-db.mjs
 *
 * WHY THIS IS A SCRIPT AND NOT A TEST
 * leads-db.mjs needs a database, so vitest cannot cover it and never has. The
 * gap was not theoretical: two separate defects shipped inside it and a green
 * suite reported nothing.
 *
 *   1. A prose comment in the createLead SQL used backticks around a column
 *      name. The SQL is a JS template literal, so the pair terminated the
 *      string and the file did not parse at all. Tests passed; the module is
 *      only imported when LEADS_DATABASE_URL is set, which is production.
 *
 *   2. createLead did a plain INSERT. capture_id is UNIQUE and the On-Page
 *      funnel saves one lead twice with a single capture id, so the second
 *      arrival raised 23505. captureRemotely is fire-and-forget, so the funnel
 *      swallowed it: every On-Page lead landed with contact details and no
 *      score, indefinitely, with nothing in any log the console surfaces.
 *
 * Neither is reachable without a live database. Hence this file.
 *
 * DESTRUCTIVE: it TRUNCATEs leadmagnet_leads. Point it at a throwaway database,
 * never at production. A disposable one costs one command:
 *
 *   docker run -d --name lm-leads-verify-pg -e POSTGRES_PASSWORD=verify \
 *     -e POSTGRES_DB=leads -p 55433:5432 postgres:16-alpine
 */
import { createLeadsDbStore } from "./leads-db.mjs";

const DSN = process.env.LEADS_VERIFY_DATABASE_URL;
if (!DSN) {
  console.error(
    "LEADS_VERIFY_DATABASE_URL is required.\n" +
      "This script TRUNCATES leadmagnet_leads -- point it at a throwaway database.",
  );
  process.exit(2);
}

const store = createLeadsDbStore(DSN);
const pass = [];
const fail = [];
const T = (condition, message) => (condition ? pass : fail).push(message);

const IDENTITY = {
  name: "Test Prospect",
  email: "test@example.com",
  phone: "+91 98765 43210",
  domainUrl: "https://wahhadesign.com",
  type: "onpage_seo",
};
const CAP = "cap_11111111-2222-3333-4444-555555555555";
// A real id from a production On-Page run: bare 32-char hex, no prefix.
const AUDIT = "e990bb5318f84bffa13d7d999c4387b2";

// createLeadsDbStore applies the schema itself, so this is safe on an empty database.
await store.read();
const { Pool } = (await import("pg")).default;
const admin = new Pool({ connectionString: DSN });
await admin.query("TRUNCATE leadmagnet_leads");
await admin.end();

/* 1. The form-submit save. No metrics exist yet: the visitor has typed their
      details and the audit has not started. */
const first = await store.createLead({ ...IDENTITY, captureId: CAP });
T(first.captureId === CAP, "save 1 stores the capture id");
T(first.score == null, "save 1 carries no score yet");

/* 2. The audit-resolved save, reusing the SAME capture id. This is the arrival
      that used to raise 23505 and be swallowed. */
const second = await store.createLead({
  ...IDENTITY,
  captureId: CAP,
  details: {
    score: 82,
    passed: 12,
    warnings: 4,
    critical: 0,
    opportunities: 15,
    audit_id: AUDIT,
    last_audit_time: "2026-09-01T00:00:00.000Z",
  },
});
T(second.id === first.id, "save 2 updates the same lead rather than inserting");

const afterEnrichment = await store.read();
T(afterEnrichment.leads.length === 1, `exactly one lead exists (got ${afterEnrichment.leads.length})`);
const lead = afterEnrichment.leads[0];
T(lead.details?.score === 82, `the score reached the lead (got ${lead.details?.score})`);
T(lead.details?.passed === 12, "checks_passed reached the lead");
/* The column always existed and rowToLead always projected it, but the INSERT
   never wrote it -- so a lead could show its score and still have no way to
   reach the report behind it. */
T(lead.auditId === AUDIT, `audit_id reached the column (got ${lead.auditId})`);
T(lead.name === IDENTITY.name, "identity name is not rewritten by the enrichment");
T(lead.email === IDENTITY.email, "identity email is not rewritten by the enrichment");

/* 3. A replay that omits the metrics must not blank what is already stored --
      the reason every metric is COALESCEd rather than assigned. */
await store.createLead({ ...IDENTITY, captureId: CAP });
const replayed = (await store.read()).leads[0];
T(replayed.details?.score === 82, "a metric-less replay does not blank the score");
T(replayed.auditId === AUDIT, "a metric-less replay does not blank audit_id");

/* 4. NULL is not equal to NULL in a unique index, so a capture without an id
      still inserts its own row exactly as it did before the upsert. */
await store.createLead({ ...IDENTITY, email: "other@example.com" });
T((await store.read()).leads.length === 2, "a null capture_id still inserts a fresh row");

/* 5. And two genuinely different prospects stay two leads. */
await store.createLead({
  ...IDENTITY,
  email: "third@example.com",
  captureId: "cap_99999999-8888-7777-6666-555555555555",
});
T((await store.read()).leads.length === 3, "distinct capture ids remain distinct leads");

/* 6. Soft delete vs the upsert.

      removeLead no longer DELETEs -- it sets lead_active = FALSE, and read()
      filters on it. That creates an interaction with this upsert that exists in
      neither change alone: an enrichment arriving AFTER an operator hid the lead
      will match the hidden row on capture_id and update it.

      That must not resurrect it. The upsert deliberately does not assign
      lead_active, which matches how applyAuditSummary treats the same case:
      store the summary against the intact row, but leave visibility alone.
      Hiding is a one-way decision made by an operator, and no service-to-service
      write may undo it. */
const hidden = (await store.read()).leads.find((row) => row.captureId === CAP);
await store.removeLead(hidden.id);
const afterHide = await store.read();
T(
  !afterHide.leads.some((row) => row.id === hidden.id),
  "removeLead hides the lead from read()",
);

await store.createLead({
  ...IDENTITY,
  captureId: CAP,
  details: { score: 91, passed: 15, audit_id: AUDIT },
});
const afterReplay = await store.read();
T(
  !afterReplay.leads.some((row) => row.id === hidden.id),
  "an enrichment landing after the hide does NOT resurrect the lead",
);

/* And the row is genuinely intact underneath, which is the whole point of a
   soft delete: a restore has to bring the enrichment back with it. */
const raw = new Pool({ connectionString: DSN });
const { rows: hiddenRows } = await raw.query(
  "SELECT lead_active, score, audit_id FROM leadmagnet_leads WHERE id = $1",
  [hidden.id],
);
await raw.end();
T(hiddenRows[0]?.lead_active === false, "the row really is flagged inactive, not deleted");
T(hiddenRows[0]?.score === 91, `the later enrichment still landed on it (score ${hiddenRows[0]?.score})`);
T(hiddenRows[0]?.audit_id === AUDIT, "and so did the audit id");

console.log(`PASS (${pass.length})`);
for (const message of pass) console.log("  OK   " + message);
if (fail.length) {
  console.log(`\nFAIL (${fail.length})`);
  for (const message of fail) console.log("  FAIL " + message);
}
process.exit(fail.length ? 1 : 0);
