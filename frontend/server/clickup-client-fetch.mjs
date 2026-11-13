/* ClickUp client-space reader — READ ONLY.
 *
 * Third and last of the read-only inspection scripts. The first two read the
 * TEMPLATES; this one reads what an actual onboarded client looks like, so the
 * mock flow can be built on a real path rather than an imagined one.
 *
 *   node --env-file-if-exists=../.env --env-file-if-exists=../.env.local \
 *        server/clickup-client-fetch.mjs "Ridgefield"
 *
 * GET only, same reasoning as its companions: CLICKUP_TOKEN is a personal token
 * carrying full account permissions, so read-only is a property of this file
 * rather than of the credential. There is no write path here and none should be
 * added — the onboarding feature is explicitly a no-write build.
 *
 * Walks every space -> folder -> list looking for a name match, then dumps the
 * matching lists with their tasks, resolved Role/Phase labels, and assignees.
 */

import fsp from "node:fs/promises";
import path from "node:path";

const API = "https://api.clickup.com/api/v2";
const TOKEN = process.env.CLICKUP_TOKEN;
const TEAM_ID = process.env.CLICKUP_TEAM_ID;

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
    throw new Error(`GET ${pathname} -> ${res.status} ${res.statusText} ${body.slice(0, 200)}`);
  }
  return res.json();
}

const toIso = (raw) => {
  if (raw === null || raw === undefined || raw === "") return null;
  const ms = Number(raw);
  return Number.isFinite(ms) ? new Date(ms).toISOString() : null;
};

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

/** orderindex -> label, per list, for every dropdown on that list. */
async function fieldLabels(listId) {
  const { fields = [] } = await request(`/list/${listId}/field`);
  const map = {};
  for (const f of fields) {
    map[f.name] = {};
    for (const o of f.type_config?.options ?? []) {
      map[f.name][o.orderindex] = (o.name ?? o.label ?? "").trim();
    }
  }
  return map;
}

async function main() {
  const needle = (process.argv[2] ?? "Ridgefield").toLowerCase();
  const teams = await request("/team");
  const team = teams.teams?.find((t) => t.id === TEAM_ID) ?? teams.teams?.[0];

  const { spaces = [] } = await request(`/team/${team.id}/space?archived=false`);
  const hits = [];

  for (const space of spaces) {
    const { folders = [] } = await request(`/space/${space.id}/folder?archived=false`);
    const { lists: folderless = [] } = await request(`/space/${space.id}/list?archived=false`);

    const candidates = [
      ...folders.flatMap((f) =>
        (f.lists ?? []).map((l) => ({ list: l, folder: f.name, space: space.name, spaceId: space.id })),
      ),
      ...folderless.map((l) => ({ list: l, folder: null, space: space.name, spaceId: space.id })),
    ];

    for (const f of folders) {
      if (f.name.toLowerCase().includes(needle)) {
        console.log(`FOLDER MATCH  ${space.name} / ${f.name}  (${(f.lists ?? []).length} lists)`);
      }
    }
    for (const c of candidates) {
      const inFolder = (c.folder ?? "").toLowerCase().includes(needle);
      if (c.list.name.toLowerCase().includes(needle) || inFolder) hits.push(c);
    }
  }

  console.log(`\nmatched ${hits.length} list(s) for "${process.argv[2] ?? "Ridgefield"}"\n`);

  const out = { fetchedAt: new Date().toISOString(), needle, lists: [] };

  for (const hit of hits) {
    const labels = await fieldLabels(hit.list.id);
    const tasks = await fetchAllTasks(hit.list.id);
    const resolved = tasks.map((t) => {
      const custom = {};
      for (const f of t.custom_fields ?? []) {
        if (f.value === undefined || f.value === null || f.value === "") continue;
        custom[f.name] = labels[f.name]?.[f.value] ?? f.value;
      }
      return {
        id: t.id,
        name: t.name,
        status: t.status?.status ?? null,
        assignees: (t.assignees ?? []).map((a) => a.username),
        dueDate: toIso(t.due_date),
        startDate: toIso(t.start_date),
        dateClosed: toIso(t.date_closed),
        dateCreated: toIso(t.date_created),
        subtaskOf: t.parent ?? null,
        custom,
        descriptionLength: (t.description ?? "").length,
      };
    });

    const done = resolved.filter((t) => t.status && /complete|done|closed/i.test(t.status)).length;
    const dated = resolved.filter((t) => t.dueDate).length;

    out.lists.push({
      space: hit.space,
      folder: hit.folder,
      id: hit.list.id,
      name: hit.list.name,
      taskCount: resolved.length,
      completed: done,
      withDueDate: dated,
      tasks: resolved,
    });

    console.log(
      `${hit.space} / ${hit.folder ?? "(no folder)"} / ${hit.list.name}\n` +
        `   id=${hit.list.id}  tasks=${resolved.length}  completed=${done}  withDueDate=${dated}`,
    );
  }

  const outFile = path.join("..", ".clickup-snapshot", "clickup-client.json");
  await fsp.writeFile(outFile, JSON.stringify(out, null, 2), "utf8");
  console.log(`\nwrote ${outFile}`);
}

main().catch((error) => {
  console.error(String(error.message ?? error));
  process.exit(1);
});
