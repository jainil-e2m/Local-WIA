/* Codegen: ClickUp snapshot -> server/onboarding-templates.json
 *
 *   node server/onboarding-templates-generate.mjs
 *
 * Reads the read-only snapshots produced by clickup-templates-fetch.mjs and
 * clickup-fields-fetch.mjs and emits the curated template data that
 * onboarding-plan.mjs consumes. Re-run it whenever they edit a template; the
 * output is generated, never hand-edited.
 *
 * Everything encoded here was MEASURED from their workspace, not inferred from
 * the call transcripts. Where a rule was derived from one real client the
 * provenance says so, because n=1 is a real caveat and it should travel with
 * the number rather than being lost.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SNAP_DIR = path.join(__dirname, "..", "..", ".clickup-snapshot");
const OUT = path.join(__dirname, "onboarding-templates.json");

/* ── WHICH LISTS ARE THE ONBOARDING TEMPLATES ─────────────────────────────
   Two of the six lists in "Onboarding Templates" are the onboarding pair.
   Google + Meta exists twice; v2 (901114303479) is the current one — it is a
   superset of v1 with the "Create custom GPT for the client" step Whitney
   described on Sept 2 as newly added. Three tasks live only in v1 and are
   ported below rather than lost. */
const LEADLOCK_LIST_ID = "901112080381";
const ADS_V2_LIST_ID = "901114303479";
const ADS_V1_LIST_ID = "901113178693";

/* Tasks present in v1 and absent from v2. "Send Referral Fee (If Applicable)"
   matters most: it is the ONLY written referral-fee procedure anywhere in the
   workspace (337-char description), and v2 dropped it. LeadLock's "Check if
   referral fee is needed" has an empty description, so nothing else covers it. */
const PORT_FROM_V1 = new Set([
  "Send Referral Fee (If Applicable)",
  "Share Google Drive Folder (add client email address)",
  "Review Sales Call",
]);

/* ── ROLE -> PERSON ───────────────────────────────────────────────────────
   `Role` is set on 299 of 308 template tasks; a real assignee on only 190.
   That 109-task gap is what this automation closes, and the map below is the
   observed pairing, not a guess:
     GHL Specialist    -> Danielle   66/66 tasks, unambiguous
     LeadLock Designer -> Tina       24/26
     Assistant         -> Gisselle   83/98  (her ClickUp account is "WIA Support")
     CEO               -> Whitney    4/11
     Marketing Asst.   -> Ivy        1/3
     Client            -> nobody     8 tasks, all unassigned - THEIR marker for
                                     client-gated work, which is exactly the
                                     `gated` due state
     Ads Manager       -> AMBIGUOUS  Carmen (Google) or Jacqueline (Meta).
                                     75 of 86 are unassigned in the template. */
const ROLE_TO_PERSON = {
  "GHL Specialist": { person: "Danielle McGinnis", confidence: "certain" },
  "LeadLock Designer": { person: "Tina Henares", confidence: "certain" },
  Assistant: { person: "Gisselle (WIA Support)", confidence: "certain" },
  CEO: { person: "Whitney Hodges", confidence: "certain" },
  "Marketing Assistant": { person: "Ivy Ayala", confidence: "likely" },
  "All Team Members": { person: null, confidence: "certain" },
  Client: { person: null, confidence: "certain" },
  "Ads Manager": { person: null, confidence: "ambiguous" },
};

/* Splitting Ads Manager. Verified against Ridgefield's real list, where Carmen
   took Keyword Research / Build out Google Ads / Google Tracking / GTM /
   Launch Google Ads and Jacqueline took Meta Tracking / Brief Ivy / Build
   campaign / Launch campaign / Present ads. A heuristic, so every row it
   decides is flagged for human confirmation in the review UI. */
const GOOGLE_HINTS = /google|gtm|ga4|keyword|search campaign|loom/i;
const META_HINTS = /meta|facebook|instagram|ivy|retarget|attraction|conversion ads/i;

const splitAdsManager = (taskName) => {
  if (GOOGLE_HINTS.test(taskName)) return { person: "Carmen Cruickshank", confidence: "heuristic" };
  if (META_HINTS.test(taskName)) return { person: "Jacqueline Hood", confidence: "heuristic" };
  return { person: null, confidence: "ambiguous" };
};

/* ── PHASE -> DUE-DATE OFFSET ─────────────────────────────────────────────
   The templates carry ZERO due dates (0 of 308). Ridgefield's live list
   carries 29. Diffing them recovers the rule Gisselle applies by hand, and it
   turns out to be a weekly cadence anchored on the kickoff call:

     Onboarding            week 0   (+0, +1)
     Project Initiation    week 1   (+7)
     Tech Setup            week 2   (+14)
     Design/Copy work      week 3   (+21)
     Final Implementation  week 3   (+21)
     Launch                week 4   (+28)

   DERIVED FROM ONE CLIENT. It reproduces Ridgefield's LeadLock dates almost
   exactly, but n=1 — it is a proposal to put in front of Gisselle, not a fact
   about how she works. The ads list does NOT follow it cleanly (offsets run
   +0,+2,+3,+6,+7,+14,+17,+21,+24,+28,+30,+35 and then a tail at +69,+71,+73),
   which is the "chasing" problem Whitney described, visible as data. */
const PHASE_WEEK = {
  Onboarding: 0,
  "Project Initiation": 1,
  "Tech Setup": 2,
  "Design/Copy work": 3,
  "Final Implementation": 3,
  Launch: 4,
};

const read = (name) => JSON.parse(fs.readFileSync(path.join(SNAP_DIR, name), "utf8"));

function main() {
  const snap = read("clickup-templates.json");
  const fields = read("clickup-fields.json");

  /* orderindex -> label, per (listId, fieldName). A task stores the dropdown's
     orderindex, so labels must be resolved per list. */
  const labels = {};
  for (const list of fields.lists) {
    for (const field of list.fields) {
      for (const option of field.options) {
        labels[`${list.id}|${field.name}|${option.orderindex}`] = (option.name ?? "").trim();
      }
    }
  }
  const cf = (listId, task, fieldName) => {
    const found = (task.customFields ?? []).find((f) => f.name === fieldName);
    if (!found) return null;
    return labels[`${listId}|${fieldName}|${found.value}`] ?? null;
  };
  const phaseOf = (listId, task) => {
    for (const f of task.customFields ?? []) {
      if (f.name.startsWith("Phase")) return labels[`${listId}|${f.name}|${f.value}`] ?? null;
    }
    return null;
  };

  const byId = Object.fromEntries(snap.templates.map((t) => [t.id, t]));

  const buildTemplate = (listId, key, extraTasks = []) => {
    const list = byId[listId];
    const tasks = [...list.tasks, ...extraTasks].map((task) => {
      const role = cf(listId, task, "Role") ?? cf(ADS_V1_LIST_ID, task, "Role");
      const phase = phaseOf(listId, task) ?? phaseOf(ADS_V1_LIST_ID, task);
      let owner = ROLE_TO_PERSON[role] ?? { person: null, confidence: "unknown" };
      if (role === "Ads Manager") owner = splitAdsManager(task.name);

      /* Their own Role=Client marker IS the gated state. Everything else is
         phase-driven; a task with no phase cannot be dated. */
      const dueState = role === "Client" ? "gated" : phase && phase in PHASE_WEEK ? "dated" : "pending";

      return {
        sourceId: task.id,
        name: task.name.trim(),
        parentId: task.subtaskOf ?? task.parent ?? null,
        orderindex: task.orderindex,
        role,
        phase,
        assigneeInTemplate: (task.assignees ?? []).map((a) => a.username)[0] ?? null,
        resolvedAssignee: owner.person,
        assigneeConfidence: owner.confidence,
        dueState,
        offsetDays: dueState === "dated" ? PHASE_WEEK[phase] * 7 : null,
        hasDescription: (task.descriptionLength ?? 0) > 0,
        checklistItems: task.checklistItems ?? [],
        portedFromV1: extraTasks.includes(task),
      };
    });

    return {
      key,
      listId,
      listName: list.name.trim(),
      taskCount: tasks.length,
      tasks,
    };
  };

  const v1 = byId[ADS_V1_LIST_ID];
  const ported = v1.tasks.filter((t) => PORT_FROM_V1.has(t.name.trim()));

  const out = {
    generatedAt: new Date().toISOString(),
    generatedBy: "server/onboarding-templates-generate.mjs",
    source: {
      workspace: snap.team?.name ?? null,
      fetchedAt: snap.fetchedAt,
      note: "Read-only snapshot. No ClickUp write has ever been issued by this project.",
    },
    roleToPerson: ROLE_TO_PERSON,
    phaseWeek: PHASE_WEEK,
    phaseWeekProvenance:
      "Derived by diffing the zero-dated templates against Ridgefield Weddings and Events' live " +
      "LeadLock list (29 real due dates). n=1 — a proposal for Gisselle to confirm, not an " +
      "established rule.",
    templates: {
      leadlock: buildTemplate(LEADLOCK_LIST_ID, "leadlock"),
      ads: buildTemplate(ADS_V2_LIST_ID, "ads", ported),
    },
    /* Measured from Ridgefield: the destination is Space -> per-client Folder
       -> one List per template. NOT one merged list, which resolves the
       ambiguity in Whitney's "we're going off both of those onboarding
       templates" — it is two lists side by side, plus Client Management. */
    destination: {
      model: "space -> client folder -> one list per template",
      spacesByOffer: Object.fromEntries(
        snap.spaces.filter((s) => s.name !== "Templates").map((s) => [s.name, s.id]),
      ),
      exampleClient: {
        name: "Ridgefield Weddings and Events",
        space: "ELEVATE Clients",
        folder: "Ridgefield Weddings and Events",
        lists: ["LeadLock Onboarding", "Google + Meta Onboarding", "Client Management"],
      },
    },
  };

  fs.writeFileSync(OUT, JSON.stringify(out, null, 2), "utf8");

  for (const t of Object.values(out.templates)) {
    const dated = t.tasks.filter((x) => x.dueState === "dated").length;
    const gated = t.tasks.filter((x) => x.dueState === "gated").length;
    const pending = t.tasks.filter((x) => x.dueState === "pending").length;
    const resolved = t.tasks.filter((x) => x.resolvedAssignee).length;
    console.log(
      `${t.listName.padEnd(36)} ${String(t.taskCount).padStart(3)} tasks  ` +
        `dated=${dated} pending=${pending} gated=${gated}  assignee-resolved=${resolved}`,
    );
  }
  console.log(`\nwrote ${OUT}`);
}

main();
