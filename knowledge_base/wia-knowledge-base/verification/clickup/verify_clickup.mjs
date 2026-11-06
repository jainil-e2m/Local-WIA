/** GET-only ClickUp KB feasibility probe. No tasks/comments/settings are changed.
 * Reads frontend/.env.local; saves reduced metadata and bounded content samples.
 * node knowledge_base/wia-knowledge-base/verification/clickup/verify_clickup.mjs
 */
import { readFile, writeFile } from 'node:fs/promises';
import { parseEnv } from 'node:util';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const out = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(out, '../../../..');
const env = parseEnv(await readFile(path.join(root, 'frontend/.env.local'), 'utf8'));
const token = env.CLICKUP_TOKEN?.trim();
const teamId = env.CLICKUP_TEAM_ID?.trim();
const oldClient = JSON.parse(await readFile(path.join(root, '.clickup-snapshot/clickup-client.json'), 'utf8'));
const report = { review_date: '2026-10-19', started_at_utc: new Date().toISOString(),
  credential_present: Boolean(token), credential_source: 'frontend/.env.local:CLICKUP_TOKEN',
  configured_workspace_id: teamId, mode: 'GET_only',
  limits: { spaces: 12, client_lists: 3, programme_lists: 2, task_pages_per_list: 2,
    task_details: 4, comment_pages_per_task: 1, threaded_comment_samples: 2 },
  calls: [], workspaces: [], spaces: [], hierarchy: [], list_samples: [], task_samples: [],
  full_workspace_task_backfill: false };
const shape = x => x && typeof x === 'object' ? Object.keys(x).sort() : [];
const clean = s => typeof s === 'string' && token ? s.replaceAll(token, '[REDACTED]') : s;
const iso = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v))
  ? new Date(Number(v)).toISOString() : null;
const user = u => u ? { id: u.id ?? null, name: u.username ?? u.name ?? null } : null;
let calls = 0;
async function get(label, endpoint, params = {}) {
  if (calls++) await new Promise(r => setTimeout(r, 700));
  const url = new URL(`https://api.clickup.com/api/v2${endpoint}`);
  for (const [k,v] of Object.entries(params)) url.searchParams.set(k, String(v));
  const call = { label, method: 'GET', path: endpoint, query: params }; report.calls.push(call);
  try {
    const res = await fetch(url, { method: 'GET', headers: { Authorization: token, Accept: 'application/json' },
      redirect: 'error', signal: AbortSignal.timeout(22000) });
    call.http_status = res.status; call.ok = res.ok;
    call.rate_limit_remaining = res.headers.get('x-ratelimit-remaining');
    const text = await res.text(); let data; try { data = JSON.parse(text); } catch { data = null; }
    call.top_level_keys = shape(data);
    if (!res.ok) { call.error = clean(JSON.stringify(data?.err ?? data?.error ?? text.slice(0, 200))); return null; }
    return data;
  } catch (e) { call.ok = false; call.error = e.name; call.cause_code = e.cause?.code ?? null; return null; }
}
function field(f) {
  return { id: f.id, name: f.name, type: f.type, value: f.value ?? null,
    options: (f.type_config?.options ?? []).map(o => ({ id: o.id, orderindex: o.orderindex,
      name: o.name ?? o.label ?? null })) };
}
function task(t) {
  const text = t.markdown_description ?? t.text_content ?? t.description ?? '';
  return { id: t.id, custom_id: t.custom_id ?? null, name: t.name, url: t.url,
    status: t.status ?? null, assignees: (t.assignees ?? []).map(user),
    creator: user(t.creator), watchers_count: t.watchers?.length ?? null,
    due_date: iso(t.due_date), start_date: iso(t.start_date),
    created_at: iso(t.date_created), updated_at: iso(t.date_updated),
    done_at: iso(t.date_done), closed_at: iso(t.date_closed),
    due_date_time: t.due_date_time ?? null, parent: t.parent ?? null,
    list: t.list ? { id: t.list.id, name: t.list.name } : null,
    folder: t.folder ? { id: t.folder.id, name: t.folder.name } : null,
    space: t.space?.id ?? null, archived: t.archived ?? null,
    priority: t.priority?.priority ?? null, tags: (t.tags ?? []).map(x => x.name),
    description_characters: text.length, description_excerpt: clean(text.slice(0, 600)),
    custom_fields: (t.custom_fields ?? []).map(field),
    checklists: (t.checklists ?? []).map(c => ({ id: c.id, name: c.name,
      resolved: c.resolved, unresolved: c.unresolved, item_count: c.items?.length ?? 0,
      items_sample: (c.items ?? []).slice(0, 4).map(i => ({ id: i.id, name: i.name,
        resolved: i.resolved, assignee: user(i.assignee) })) })),
    dependencies: t.dependencies ?? [], linked_task_count: t.linked_tasks?.length ?? null,
    attachment_count: t.attachments?.length ?? null,
    attachments: (t.attachments ?? []).slice(0, 4).map(a => ({ id: a.id, title: a.title,
      extension: a.extension, date: a.date })),
    time_estimate_ms: t.time_estimate ?? null, time_spent_ms: t.time_spent ?? null,
    response_keys: shape(t) };
}
function comment(c) {
  const text = c.comment_text ?? (c.comment ?? []).map(s => s.text ?? '').join('');
  return { id: c.id, date: iso(c.date), author: user(c.user), text_characters: text.length,
    text_excerpt: clean(text.slice(0, 900)), resolved: c.resolved ?? null,
    assignee: user(c.assignee), assigned_by: user(c.assigned_by), reply_count: c.reply_count ?? null,
    response_keys: shape(c) };
}
async function main() {
  if (!token) { report.result = 'credential_missing'; return; }
  const me = await get('authorized_user', '/user'); report.authorized_user = user(me?.user);
  const workspace = await get('authorized_workspaces', '/team');
  report.workspaces = (workspace?.teams ?? []).map(t => ({ id: t.id, name: t.name,
    member_count: t.members?.length ?? null }));
  const selected = report.workspaces.find(t => String(t.id) === teamId);
  if (!selected) { report.result = 'configured_workspace_not_authorized'; return; }
  report.selected_workspace = selected;
  const spaces = await get('workspace_spaces', `/team/${teamId}/space`, { archived: false });
  report.spaces = (spaces?.spaces ?? []).map(s => ({ id: s.id, name: s.name, private: s.private,
    statuses: s.statuses ?? [], archived: s.archived ?? null }));
  for (const s of report.spaces.slice(0, report.limits.spaces)) {
    const folders = await get(`folders_${s.id}`, `/space/${s.id}/folder`, { archived: false });
    const lists = await get(`folderless_lists_${s.id}`, `/space/${s.id}/list`, { archived: false });
    report.hierarchy.push({ space_id: s.id, space_name: s.name,
      folders_read_ok: folders !== null, folderless_read_ok: lists !== null,
      folders: (folders?.folders ?? []).map(f => ({ id: f.id, name: f.name, archived: f.archived,
        lists: (f.lists ?? []).map(l => ({ id: l.id, name: l.name,
          task_count_reported: l.task_count ?? null, archived: l.archived ?? null })) })),
      folderless_lists: (lists?.lists ?? []).map(l => ({ id: l.id, name: l.name,
        task_count_reported: l.task_count ?? null, archived: l.archived ?? null })) });
  }
  const candidates = report.hierarchy.flatMap(s => [
    ...s.folders.flatMap(f => f.lists.map(l => ({ ...l, folder_name: f.name,
      folder_id: f.id, space_name: s.space_name, space_id: s.space_id }))),
    ...s.folderless_lists.map(l => ({ ...l, folder_name: null, folder_id: null,
      space_name: s.space_name, space_id: s.space_id }))]);
  const selectedLists = [];
  for (const old of oldClient.lists.slice(0, report.limits.client_lists)) {
    const found = candidates.find(c => String(c.id) === String(old.id));
    if (found) selectedLists.push({ ...found, selection: 'previously inspected Ridgefield client list, rediscovered live' });
  }
  for (const name of ['Google Search Accelerator', 'Meta Ads Accelerator']) {
    const c = candidates.find(c => c.space_name === name && !c.archived);
    if (c) selectedLists.push({ ...c, selection: 'first available list in programme space; client semantics require review' });
  }
  report.selection_missing_prior_client_lists = oldClient.lists.filter(l => !selectedLists.some(s => String(s.id) === String(l.id))).map(l => l.id);
  for (const l of selectedLists) {
    const result = { metadata: l, fields: [], tasks: [], pagination_complete: false };
    const defs = await get(`list_fields_${l.id}`, `/list/${l.id}/field`);
    result.fields = (defs?.fields ?? []).map(field);
    for (let page = 0; page < report.limits.task_pages_per_list; page++) {
      const data = await get(`list_tasks_${l.id}_${page}`, `/list/${l.id}/task`, {
        page, subtasks: true, include_closed: true, include_timl: true,
        include_markdown_description: true, archived: false, order_by: 'updated', reverse: true });
      if (!data) break;
      const rows = data.tasks ?? []; report.calls.at(-1).item_count = rows.length;
      result.tasks.push(...rows.map(task));
      if (data.last_page === true || rows.length < 100) { result.pagination_complete = true; break; }
    }
    result.unique_task_count = new Set(result.tasks.map(t => t.id)).size;
    report.list_samples.push(result);
  }
  const all = [...new Map(report.list_samples.flatMap(l => l.tasks).map(t => [t.id, t])).values()];
  const samples = [];
  const add = t => { if (t && !samples.some(s => s.id === t.id)) samples.push(t); };
  add(all.find(t => t.status?.type === 'closed' || t.status?.type === 'done'));
  add(all.find(t => t.status?.type !== 'closed' && t.status?.type !== 'done' && t.due_date));
  for (const l of report.list_samples.slice(3)) add(l.tasks[0]);
  for (const t of all) { if (samples.length >= report.limits.task_details) break; add(t); }
  let threadRequests = 0;
  for (const t of samples.slice(0, report.limits.task_details)) {
    const detail = await get(`task_detail_${t.id}`, `/task/${t.id}`, { include_subtasks: true,
      include_markdown_description: true });
    const data = await get(`task_comments_${t.id}`, `/task/${t.id}/comment`);
    const comments = (data?.comments ?? []).map(comment);
    const threaded = [];
    for (const c of comments.filter(c => Number(c.reply_count) > 0)) {
      if (threadRequests >= report.limits.threaded_comment_samples) break;
      threadRequests++;
      const replies = await get(`comment_replies_${c.id}`, `/comment/${c.id}/reply`);
      threaded.push({ parent_comment_id: c.id, replies: (replies?.comments ?? []).map(comment) });
    }
    report.task_samples.push({ task: detail?.id ? task(detail) : null, task_id: t.id,
      comment_count_returned: comments.length, comments, threaded_replies: threaded });
  }
  report.result = 'probe_completed';
}
const followup = process.argv.includes('--onboarding');
async function onboardingFollowup() {
  if (!token) { report.result = 'credential_missing'; return; }
  const prior = JSON.parse(await readFile(path.join(out, 'live_probe.json'), 'utf8'));
  report.seed_source = 'live_probe.json: rediscovered Dogwood onboarding folder and programme task lists';
  const space = prior.hierarchy.find(s => s.space_name === 'ONBOARDING CLIENTS');
  const folder = space?.folders.find(f => f.name === 'Dogwood Reserve');
  if (!folder) { report.result = 'known_onboarding_folder_not_found'; return; }
  for (const l of folder.lists.filter(l => /Google \+ Meta Onboarding|LeadLock Onboarding/.test(l.name)).slice(0, 2)) {
    const result = { metadata: { ...l, space_id: space.space_id, space_name: space.space_name,
      folder_id: folder.id, folder_name: folder.name, selection: 'live Dogwood onboarding list' },
      fields: [], tasks: [], pagination_complete: false };
    const defs = await get(`onboarding_fields_${l.id}`, `/list/${l.id}/field`);
    result.fields = (defs?.fields ?? []).map(field);
    for (let page = 0; page < report.limits.task_pages_per_list; page++) {
      const data = await get(`onboarding_tasks_${l.id}_${page}`, `/list/${l.id}/task`, {
        page, subtasks: true, include_closed: true, include_timl: true,
        include_markdown_description: true, archived: false });
      if (!data) break;
      const rows = data.tasks ?? []; report.calls.at(-1).item_count = rows.length;
      result.tasks.push(...rows.map(task));
      if (data.last_page === true || rows.length < 100) { result.pagination_complete = true; break; }
    }
    result.unique_task_count = new Set(result.tasks.map(t => t.id)).size;
    report.list_samples.push(result);
  }
  // Two onboarding details plus one task from each programme, all with comment reads.
  const chosen = [];
  for (const l of report.list_samples) {
    const t = l.tasks.find(t => /welcome|kick.?off|client|access|form/i.test(t.name) && t.description_characters)
      ?? l.tasks.find(t => t.description_characters) ?? l.tasks[0];
    if (t) chosen.push(t);
  }
  for (const l of prior.list_samples.filter(l => /Accelerator/.test(l.metadata.space_name))) {
    const t = l.tasks.find(t => /review|client|feedback/i.test(t.name) && t.description_characters) ?? l.tasks[0];
    if (t) chosen.push(t);
  }
  let threadRequests = 0;
  for (const t of chosen) {
    const detail = await get(`followup_detail_${t.id}`, `/task/${t.id}`, { include_subtasks: true,
      include_markdown_description: true });
    const data = await get(`followup_comments_${t.id}`, `/task/${t.id}/comment`);
    const comments = (data?.comments ?? []).map(comment);
    const threaded = [];
    for (const c of comments.filter(c => Number(c.reply_count) > 0)) {
      if (threadRequests >= report.limits.threaded_comment_samples) break;
      threadRequests++;
      const replies = await get(`followup_replies_${c.id}`, `/comment/${c.id}/reply`);
      threaded.push({ parent_comment_id: c.id, replies: (replies?.comments ?? []).map(comment) });
    }
    report.task_samples.push({ task: detail?.id ? task(detail) : null, task_id: t.id,
      comment_count_returned: comments.length, comments, threaded_replies: threaded });
  }
  report.result = 'onboarding_followup_completed';
}
try { if (followup) await onboardingFollowup(); else await main(); }
catch(e) { report.result = 'probe_error'; report.error_type = e.name; }
report.finished_at_utc = new Date().toISOString();
const filename = followup ? 'onboarding_probe.json' : 'live_probe.json';
await writeFile(path.join(out, filename), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ result: report.result, calls: report.calls.length,
  statuses: report.calls.reduce((x,c) => { const k = c.http_status ?? 'network_error'; x[k] = (x[k] ?? 0) + 1; return x; }, {}),
  workspace: report.selected_workspace, spaces: report.spaces.map(s => s.name),
  lists: report.list_samples.map(l => ({ space: l.metadata.space_name, folder: l.metadata.folder_name,
    name: l.metadata.name, tasks: l.unique_task_count, pagination_complete: l.pagination_complete })),
  sample_comments: report.task_samples.map(s => ({task_id:s.task_id, comments:s.comment_count_returned})),
  report: `knowledge_base/wia-knowledge-base/verification/clickup/${filename}` }, null, 2));
