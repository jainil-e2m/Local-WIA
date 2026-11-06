/* ClickUp onboarding-template reader — READ ONLY.
 *
 * Pulls the real onboarding templates out of the Wedding Industry Ads
 * workspace so onboarding-plan.mjs can stop guessing. Run it again whenever
 * they edit a template; the output is meant to be regenerated, not hand-edited.
 *
 *   node --env-file-if-exists=../.env --env-file-if-exists=../.env.local \
 *        server/clickup-templates-fetch.mjs [outDir]
 *
 * ── WHY THIS FILE CONTAINS NO VERB BUT GET ────────────────────────────────
 * CLICKUP_TOKEN is a PERSONAL token (pk_...). It carries the full permissions
 * of the account that minted it, including write and delete — there is no such
 * thing as a read-only personal token in ClickUp. So the read-only property has
 * to come from this file, not from the credential: `request()` hard-codes GET
 * and there is no other call path. Do not add one. A provisioning writer, if it
 * is ever built, belongs in its own module with its own approval gate.
 *
 * ── WHAT IT ANSWERS ───────────────────────────────────────────────────────
 * Four questions that blocked onboarding-plan.mjs:
 *   1. the real task list for each template (names, order, subtask nesting)
 *   2. whether tasks already carry ASSIGNEES  — if so, that leg of the
 *      automation is worth nothing and the value is dates plus visibility
 *   3. whether tasks already carry DUE DATES  — if so the date backfill is
 *      arithmetic rather than a build
 *   4. which of the two identically-named "Google + Meta Onboarding" lists is
 *      real, by giving both an id and a task count to compare
 */

import fsp from "node:fs/promises";
import path from "node:path";

const API = "https://api.clickup.com/api/v2";
const TOKEN = process.env.CLICKUP_TOKEN;
const TEAM_ID = process.env.CLICKUP_TEAM_ID;
const SPACE_ID = process.env.CLICKUP_TEMPLATES_SPACE_ID;

if (!TOKEN) {
  console.error("CLICKUP_TOKEN is not set. Put it in frontend/.env.local and re-run.");
  process.exit(1);
}

/** The ONLY network call in this module, and it is a GET. See the header. */
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

/** ClickUp epoch-millis-as-string -> ISO, or null. */
const toIso = (raw) => {
  if (raw === null || raw === undefined || raw === "") return null;
  const ms = Number(raw);
  if (!Number.isFinite(ms)) return null;
  return new Date(ms).toISOString();
};

/** Reduce a ClickUp task to the fields the planner actually needs. */
const reduceTask = (task) => ({
  id: task.id,
  name: task.name,
  orderindex: task.orderindex,
  status: task.status?.status ?? null,
  /* THE HEDGE Whitney could not resolve: "I don't know if you're manually
     going in and assigning things every time" (Sept 2 @21:34). */
  assignees: (task.assignees ?? []).map((a) => ({
    id: a.id,
    username: a.username,
    email: a.email,
  })),
  /* THE CERTAINTY: "she's definitely manually going in and having to set due
     dates for everything." If these come back populated the template already
     carries them and the backfill is arithmetic. */
  dueDate: toIso(task.due_date),
  startDate: toIso(task.start_date),
  timeEstimate: task.time_estimate ?? null,
  parent: task.parent ?? null,
  subtaskOf: task.top_level_parent && task.top_level_parent !== task.id ? task.top_level_parent : null,
  priority: task.priority?.priority ?? null,
  tags: (task.tags ?? []).map((t) => t.name),
  customFields: (task.custom_fields ?? [])
    .filter((f) => f.value !== undefined && f.value !== null && f.value !== "")
    .map((f) => ({ name: f.name, type: f.type, value: f.value })),
  descriptionLength: (task.description ?? "").length,
  checklistCount: (task.checklists ?? []).length,
  checklistItems: (task.checklists ?? []).flatMap((c) =>
    (c.items ?? []).map((i) => i.name),
  ),
});

/** Page through a list's tasks — ClickUp caps a page at 100. */
async function fetchAllTasks(listId) {
  const all = [];
  for (let page = 0; page < 20; page += 1) {
    const qs = new URLSearchParams({
      page: String(page),
      subtasks: "true",
      include_closed: "true",
      order_by: "created",
      reverse: "false",
    });
    const { tasks = [], last_page: lastPage } = await request(`/list/${listId}/task?${qs}`);
    all.push(...tasks);
    if (lastPage || tasks.length === 0) break;
  }
  return all;
}

async function main() {
  const outDir = process.argv[2] ?? path.join("..", ".clickup-snapshot");
  await fsp.mkdir(outDir, { recursive: true });

  const snapshot = { fetchedAt: new Date().toISOString(), team: null, spaces: [], templates: [] };

  /* 1. Workspace, to confirm we are pointed at the right one. */
  const teams = await request("/team");
  const team = teams.teams?.find((t) => t.id === TEAM_ID) ?? teams.teams?.[0];
  snapshot.team = team ? { id: team.id, name: team.name } : null;
  console.log(`workspace: ${snapshot.team?.name} (${snapshot.team?.id})`);

  /* 2. Every space — this is the DESTINATION map. The sidebar is organised by
        OFFER (ELEVATE Clients, Foolproof Follow-Up Advantage, Google Search
        Accelerator, Meta Ads Accelerator, VIP Days, ARCHIVES - Full Service),
        not folder-per-client, which changes where a provisioned list lands. */
  const { spaces = [] } = await request(`/team/${team.id}/space?archived=false`);
  snapshot.spaces = spaces.map((s) => ({ id: s.id, name: s.name, private: s.private }));
  console.log(`spaces: ${spaces.length}`);

  /* 3. Folders in the Templates space. */
  const { folders = [] } = await request(`/space/${SPACE_ID}/folder?archived=false`);
  console.log(`folders in Templates space: ${folders.map((f) => f.name).join(", ") || "(none)"}`);

  /* 4. Every list in every folder, plus folderless lists, then their tasks. */
  const lists = [];
  for (const folder of folders) {
    for (const list of folder.lists ?? []) {
      lists.push({ ...list, folderName: folder.name, folderId: folder.id });
    }
  }
  const { lists: folderless = [] } = await request(`/space/${SPACE_ID}/list?archived=false`);
  for (const list of folderless) lists.push({ ...list, folderName: null, folderId: null });

  for (const list of lists) {
    const tasks = await fetchAllTasks(list.id);
    const reduced = tasks.map(reduceTask);
    const withAssignee = reduced.filter((t) => t.assignees.length > 0).length;
    const withDueDate = reduced.filter((t) => t.dueDate).length;
    snapshot.templates.push({
      id: list.id,
      name: list.name,
      folder: list.folderName,
      folderId: list.folderId,
      taskCountReported: list.task_count ?? null,
      taskCountFetched: reduced.length,
      /* The two numbers that decide how much of this automation is worth
         building. Printed per list so the answer is impossible to miss. */
      tasksWithAssignee: withAssignee,
      tasksWithDueDate: withDueDate,
      tasks: reduced,
    });
    console.log(
      `  ${String(list.name).padEnd(34)} id=${list.id}  tasks=${reduced.length}` +
        `  assignees=${withAssignee}  dueDates=${withDueDate}`,
    );
  }

  const outFile = path.join(outDir, "clickup-templates.json");
  await fsp.writeFile(outFile, JSON.stringify(snapshot, null, 2), "utf8");
  console.log(`\nwrote ${outFile}`);
}

main().catch((error) => {
  console.error(String(error.message ?? error));
  process.exit(1);
});
