/* ClickUp custom-field definition reader — READ ONLY.
 *
 * Companion to clickup-templates-fetch.mjs. That script captured custom-field
 * VALUES, which for a dropdown are opaque option indexes (0, 1, 3, 4, 5...).
 * This one fetches the field DEFINITIONS so those indexes resolve to labels.
 *
 *   node --env-file-if-exists=../.env --env-file-if-exists=../.env.local \
 *        server/clickup-fields-fetch.mjs
 *
 * GET only, for the same reason as its companion: CLICKUP_TOKEN is a personal
 * token carrying full account permissions, so read-only has to be a property of
 * this file rather than of the credential.
 *
 * ── WHY THIS MATTERS MORE THAN IT LOOKS ───────────────────────────────────
 * Two fields turned up that the first pass missed entirely, and both bear on
 * questions the call transcripts left open:
 *
 *   Role   — set on 299 of 308 tasks, against only 190 with a real assignee.
 *            If it maps onto the named roster then ownership is already
 *            encoded on nearly every task, and the automation should read
 *            THIS rather than the assignee field.
 *
 *   Phase  — a per-template dropdown (Phase (LeadLock), Phase (Full Service),
 *            Phase (Google Ads VIP Day), Phase (Ads Traffic)). If its options
 *            correspond to the five call anchors, then the sequencing the
 *            transcripts said lived only in Gisselle's head is in fact already
 *            written down — as a phase grouping rather than as due dates.
 *            That would change the date backfill from rule-extraction into a
 *            mapping exercise.
 */

import fsp from "node:fs/promises";
import path from "node:path";

const API = "https://api.clickup.com/api/v2";
const TOKEN = process.env.CLICKUP_TOKEN;
const SPACE_ID = process.env.CLICKUP_TEMPLATES_SPACE_ID;

if (!TOKEN) {
  console.error("CLICKUP_TOKEN is not set. Put it in frontend/.env.local and re-run.");
  process.exit(1);
}

/** The ONLY network call in this module, and it is a GET. */
async function request(pathname) {
  const res = await fetch(`${API}${pathname}`, {
    method: "GET",
    headers: { Authorization: TOKEN, "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`GET ${pathname} -> ${res.status} ${res.statusText} ${body.slice(0, 300)}`);
  }
  return res.json();
}

async function main() {
  const snapPath = path.join("..", ".clickup-snapshot", "clickup-templates.json");
  const snapshot = JSON.parse(await fsp.readFile(snapPath, "utf8"));

  const out = { fetchedAt: new Date().toISOString(), lists: [] };

  for (const template of snapshot.templates) {
    const { fields = [] } = await request(`/list/${template.id}/field`);
    const reduced = fields.map((f) => ({
      id: f.id,
      name: f.name,
      type: f.type,
      /* Dropdown options carry both `orderindex` and an array position; a task's
         stored value is the orderindex, so index BY orderindex, not by position. */
      options: (f.type_config?.options ?? []).map((o) => ({
        id: o.id,
        name: o.name ?? o.label ?? null,
        orderindex: o.orderindex,
        color: o.color ?? null,
      })),
    }));
    out.lists.push({ id: template.id, name: template.name, fields: reduced });

    console.log(`\n${template.name}  (${template.taskCountFetched} tasks)`);
    for (const field of reduced) {
      if (!field.options.length) {
        console.log(`  ${field.name} [${field.type}]`);
        continue;
      }
      console.log(`  ${field.name} [${field.type}]`);
      for (const o of field.options) {
        console.log(`      ${String(o.orderindex).padStart(2)} = ${o.name}`);
      }
    }
  }

  const outFile = path.join("..", ".clickup-snapshot", "clickup-fields.json");
  await fsp.writeFile(outFile, JSON.stringify(out, null, 2), "utf8");
  console.log(`\nwrote ${outFile}`);
}

main().catch((error) => {
  console.error(String(error.message ?? error));
  process.exit(1);
});
