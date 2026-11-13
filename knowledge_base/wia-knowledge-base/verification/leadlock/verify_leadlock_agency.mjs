/** Verify GHL_AGENCY_PIT with GET-only requests, preserving previous token reports.
 * Lists bounded agency metadata and tests one known client location's read access.
 * Does not create location tokens, change permissions, or retain contact PII.
 */
import { readFile, writeFile } from 'node:fs/promises';
import { parseEnv } from 'node:util';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const out = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(out, '../../../..');
let token = process.env.GHL_AGENCY_PIT;
let source = token ? 'process environment:GHL_AGENCY_PIT' : null;
for (const file of ['frontend/.env', 'frontend/.env.local']) {
  if (token) break;
  try {
    const values = parseEnv(await readFile(path.join(root, file), 'utf8'));
    if (values.GHL_AGENCY_PIT) { token = values.GHL_AGENCY_PIT; source = `${file}:GHL_AGENCY_PIT`; }
  } catch { /* Only report key presence. */ }
}
const prior = JSON.parse(await readFile(path.join(out, 'live_probe.json'), 'utf8'));
const companyId = prior.observations.location.company_id;
const wiaLocationId = prior.configured_location_id;
const report = { review_date: '2026-10-19', started_at_utc: new Date().toISOString(),
  credential_present: Boolean(token), credential_source: source, mode: 'agency_token_get_only_verification',
  version_header: '2021-07-28', seed_company_id: companyId, seed_source: 'prior verified WIA location response',
  calls: [], observations: {}, limits: { location_page_size: 20, location_max_pages: 10,
    client_data_locations: 1, client_data_sample_limit: 2 }, full_client_data_backfill: false };
let count = 0;
async function get(label, endpoint, params = {}) {
  if (count++) await new Promise(resolve => setTimeout(resolve, 650));
  const url = new URL(endpoint, 'https://services.leadconnectorhq.com');
  for (const [key,value] of Object.entries(params)) url.searchParams.set(key, String(value));
  const call = { label, method: 'GET', path: endpoint, query: params };
  report.calls.push(call);
  try {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${token}`,
      Version: report.version_header, Accept: 'application/json' },
      redirect: 'error', signal: AbortSignal.timeout(18000) });
    call.http_status = response.status; call.ok = response.ok;
    if (response.status === 429) call.retry_after = response.headers.get('retry-after');
    const text = await response.text();
    let data; try { data = JSON.parse(text); } catch { data = null; }
    call.top_level_keys = data && typeof data === 'object' ? Object.keys(data).sort() : [];
    if (!response.ok) {
      call.error = JSON.stringify(data?.message ?? data?.error ?? text.slice(0, 200)).replaceAll(token, '[REDACTED]').slice(0, 350);
      return null;
    }
    for (const key of ['total','totalCount','count']) if (typeof data?.[key] === 'number') call[key] = data[key];
    return data;
  } catch (error) {
    call.ok = false; call.error = 'network_or_response_error'; call.error_type = error.name;
    call.cause_code = error.cause?.code ?? null; return null;
  }
}
const id = row => row?.id ?? row?._id ?? null;
const shape = row => row && typeof row === 'object' ? Object.keys(row).sort() : [];
function rows(data, names) {
  if (Array.isArray(data)) return data;
  for (const name of names) if (Array.isArray(data?.[name])) return data[name];
  return [];
}
async function main() {
  if (!token) { report.result = 'agency_credential_missing'; return; }
  const company = await get('company', `/companies/${encodeURIComponent(companyId)}`);
  if (company) {
    const value = company.company ?? company;
    report.observations.company = { id: id(value), name: value.name ?? null, keys: shape(value) };
  }
  const locations = new Map();
  let skip = 0;
  let complete = false;
  for (let page = 0; page < report.limits.location_max_pages; page++) {
    const data = await get(`location_page_${page+1}`, '/locations/search', { companyId, skip, limit: 20 });
    if (!data) break;
    const list = rows(data, ['locations']);
    report.calls.at(-1).returned_rows = list.length;
    if (!Array.isArray(data.locations)) { report.location_shape_unrecognised = true; break; }
    if (!list.length) { complete = true; break; }
    const before = locations.size;
    for (const row of list) locations.set(id(row), { id: id(row), name: row.name ?? null,
      timezone: row.timezone ?? null, company_id: row.companyId ?? null,
      created_at: row.dateAdded ?? null });
    if (locations.size === before) { report.location_pagination_error = 'repeated_page_no_new_ids'; break; }
    skip += list.length;
  }
  report.observations.locations = [...locations.values()];
  report.location_inventory_complete_by_empty_page = complete;
  report.location_count_returned = locations.size;
  const selected = [...locations.values()].find(x => /^Dogwood Reserve$/i.test(x.name ?? ''));
  for (const [label, target] of [['wia_location',wiaLocationId],['client_location', selected?.id]]) {
    if (!target) continue;
    const data = await get(label, `/locations/${encodeURIComponent(target)}`);
    if (data) {
      const value = data.location ?? data;
      report.observations[label] = { id: id(value), name: value.name, timezone: value.timezone,
        keys: shape(value), business_keys: shape(value.business) };
    }
  }
  for (const [label, target] of [['wia_users',wiaLocationId],['client_users',selected?.id]]) {
    if (!target) continue;
    const data = await get(label, '/users/', { locationId: target });
    if (data) {
      const list = rows(data, ['users']);
      report.calls.at(-1).returned_rows = list.length;
      report.observations[label] = list.map(x => ({ id: id(x), has_name: Boolean(x.firstName || x.name),
        role: x.roles?.role ?? null, user_type: x.roles?.type ?? null,
        associated_location_count: Array.isArray(x.roles?.locationIds) ? x.roles.locationIds.length : null,
        keys: shape(x) }));
    }
  }
  if (selected) {
    report.selected_client = selected;
    const client = selected.id;
    const tests = [
      ['client_contacts','/contacts/',{ locationId: client, limit: 2 },['contacts']],
      ['client_pipelines','/opportunities/pipelines',{ locationId: client },['pipelines']],
      ['client_opportunities','/opportunities/search',{ location_id: client, limit: 2 },['opportunities']],
      ['client_calendars','/calendars/',{ locationId: client },['calendars']],
      ['client_invoices','/invoices/',{ altId: client, altType: 'location', limit: 2, offset: 0 },['invoices']],
      ['client_surveys','/surveys/',{ locationId: client, limit: 2, skip: 0 },['surveys']],
      ['client_forms','/forms/',{ locationId: client, limit: 2, skip: 0 },['forms']],
      ['client_conversations','/conversations/search',{ locationId: client, limit: 2 },['conversations']],
    ];
    for (const [label, endpoint, params, arrays] of tests) {
      const data = await get(label, endpoint, params);
      if (!data) continue;
      const list = rows(data, arrays);
      report.calls.at(-1).returned_rows = list.length;
      report.observations[label] = { sample_count: list.length, sample_row_keys: shape(list[0]),
        record_ids: list.slice(0, 2).map(id) };
    }
  }
  report.result = report.calls.some(x => x.ok) ? 'agency_probe_completed' : 'all_agency_reads_failed';
}
const usersOnly = process.argv.includes('--users');
if (usersOnly && token) {
  report.mode = 'agency_user_search_followup';
  const earlier = JSON.parse(await readFile(path.join(out, 'agency_probe.json'), 'utf8'));
  for (const [label, params] of [
    ['agency_user_search', { companyId, limit: 3, skip: 0 }],
    ['client_user_search', { companyId, locationId: earlier.selected_client.id, limit: 3, skip: 0 }],
  ]) {
    const data = await get(label, '/users/search', params);
    if (!data) continue;
    const list = rows(data, ['users']);
    report.calls.at(-1).returned_rows = list.length;
    report.observations[label] = list.map(x => ({ id: id(x), has_name: Boolean(x.firstName || x.name),
      role: x.roles?.role ?? null, user_type: x.roles?.type ?? null,
      associated_location_count: Array.isArray(x.roles?.locationIds) ? x.roles.locationIds.length : null,
      keys: shape(x) }));
  }
  report.result = 'agency_user_search_followup_completed';
} else await main();
report.finished_at_utc = new Date().toISOString();
await writeFile(path.join(out, usersOnly ? 'agency_users_probe.json' : 'agency_probe.json'), JSON.stringify(report, null, 2)+'\n');
console.log(JSON.stringify(report, null, 2));
