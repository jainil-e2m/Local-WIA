/** Bounded GET-only LeadLock/HighLevel feasibility probe.
 * Uses existing GHL_PIT + GHL_LOCATION_ID, never prints credentials or contact PII.
 * No invoices, workflows, messages, forms, or calendar records are changed.
 * Run: node knowledge_base/wia-knowledge-base/verification/leadlock/verify_leadlock.mjs
 */
import { readFile, writeFile } from 'node:fs/promises';
import { parseEnv } from 'node:util';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const out = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(out, '../../../..');
let token = process.env.GHL_PIT;
let locationId = process.env.GHL_LOCATION_ID;
let credentialSource = token ? 'process environment' : null;
for (const file of ['frontend/.env', 'frontend/.env.local']) {
  if (token && locationId) break;
  try {
    const values = parseEnv(await readFile(path.join(root, file), 'utf8'));
    if (!token && values.GHL_PIT) { token = values.GHL_PIT; credentialSource = `${file}:GHL_PIT`; }
    locationId ||= values.GHL_LOCATION_ID;
  } catch { /* Report missing credentials without revealing contents. */ }
}
const VERSION = '2021-07-28';
const HOST = 'https://services.leadconnectorhq.com';
const report = { review_date: '2026-10-19', started_at_utc: new Date().toISOString(),
  mode: 'bounded_get_only_api_probe', credential_present: Boolean(token),
  credential_source: credentialSource, configured_location_id: locationId ?? null,
  version_header: VERSION, full_backfill: false, calls: [], observations: {} };
const hash = value => value ? createHash('sha256').update(String(value)).digest('hex').slice(0, 12) : null;
const id = row => row?._id ?? row?.id ?? null;
const keys = row => row && typeof row === 'object' ? Object.keys(row).sort() : [];
const present = (row, names) => Object.fromEntries(names.map(k => [k,
  Array.isArray(row?.[k]) ? row[k].length > 0 : row?.[k] != null && row[k] !== '']));
const retained = (row, names) => Object.fromEntries(names.filter(k => row?.[k] != null).map(k => [k, row[k]]));
const cache = {};
let requestCount = 0;
async function get(label, pathname, params = {}) {
  if (requestCount++) await new Promise(resolve => setTimeout(resolve, 650));
  const url = new URL(pathname, HOST);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, String(value));
  const record = { label, method: 'GET', path: pathname, query: params };
  report.calls.push(record);
  try {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${token}`,
      Version: VERSION, Accept: 'application/json' }, signal: AbortSignal.timeout(18000), redirect: 'error' });
    record.http_status = response.status;
    if (response.status === 429) record.retry_after = response.headers.get('retry-after');
    const text = await response.text();
    let data; try { data = JSON.parse(text); } catch { data = null; }
    record.ok = response.ok;
    record.top_level_keys = keys(data);
    if (!response.ok) {
      record.error = JSON.stringify(data?.message ?? data?.error ?? text.slice(0, 250)).replaceAll(token, '[REDACTED]').slice(0, 450);
      return null;
    }
    if (data?.meta) record.meta = Object.fromEntries(Object.entries(data.meta).filter(([k,v]) => /total|page|next|prev|limit|skip|offset/i.test(k) && typeof v !== 'object'));
    for (const k of ['total', 'totalCount', 'count']) if (typeof data?.[k] === 'number') record[k] = data[k];
    cache[label] = data;
    return data;
  } catch (error) {
    record.ok = false; record.error = 'network_or_response_error';
    record.error_type = error.name; record.cause_code = error.cause?.code ?? null;
    return null;
  }
}
function rows(data, ...names) {
  if (Array.isArray(data)) return data;
  for (const name of names) if (Array.isArray(data?.[name])) return data[name];
  return [];
}
function overview(label, data, names) {
  if (!data) return [];
  const list = rows(data, ...names);
  const call = report.calls.find(c => c.label === label);
  call.returned_rows = list.length;
  call.sample_row_keys = keys(list[0]);
  return list;
}
async function main() {
  if (!token || !locationId) { report.result = 'credential_or_location_missing'; return; }
  const identity = await get('location', `/locations/${encodeURIComponent(locationId)}`);
  if (!identity) { report.result = 'location_check_failed'; return; }
  const loc = identity.location ?? identity;
  report.observations.location = { id: id(loc), name: loc.name ?? null,
    company_id: loc.companyId ?? null, timezone: loc.timezone ?? null,
    keys: keys(loc), business_keys: keys(loc.business) };
  if (loc.companyId) {
    const data = await get('location_search', '/locations/search', { companyId: loc.companyId, limit: 5, skip: 0 });
    const list = overview('location_search', data, ['locations']);
    report.observations.locations = list.map(x => ({ id: id(x), name: x.name }));
  }
  const contactData = await get('contacts', '/contacts/', { locationId, limit: 3 });
  const contacts = overview('contacts', contactData, ['contacts']);
  report.observations.contact_shapes = contacts.map(x => ({ id: id(x),
    identity_hash: hash(x.email ?? x.phone ?? id(x)), keys: keys(x),
    fields_present: present(x, ['firstName','lastName','email','phone','companyName','dateAdded','source','tags','customFields']) }));
  const plans = [
    ['invoices', '/invoices/', { altId: locationId, altType: 'location', limit: 5, offset: 0, sortField: 'issueDate', sortOrder: 'descend' }, ['invoices']],
    ['transactions', '/payments/transactions', { altId: locationId, altType: 'location', limit: 5, offset: 0 }, ['data','transactions']],
    ['subscriptions', '/payments/subscriptions', { altId: locationId, altType: 'location', limit: 5, offset: 0 }, ['data','subscriptions']],
    ['orders', '/payments/orders', { altId: locationId, altType: 'location', limit: 5, offset: 0 }, ['data','orders']],
    ['products', '/products/', { locationId, limit: 5, offset: 0 }, ['products','data']],
    ['pipelines', '/opportunities/pipelines', { locationId }, ['pipelines']],
    ['opportunities', '/opportunities/search', { location_id: locationId, limit: 5 }, ['opportunities']],
    ['calendars', '/calendars/', { locationId }, ['calendars']],
    ['surveys', '/surveys/', { locationId, limit: 5, skip: 0 }, ['surveys']],
    ['survey_submissions', '/surveys/submissions', { locationId, limit: 3, page: 1 }, ['submissions']],
    ['forms', '/forms/', { locationId, limit: 5, skip: 0 }, ['forms']],
    ['form_submissions', '/forms/submissions', { locationId, limit: 3, page: 1 }, ['submissions']],
    ['conversations', '/conversations/search', { locationId, limit: 3 }, ['conversations']],
    ['custom_fields', `/locations/${encodeURIComponent(locationId)}/customFields`, {}, ['customFields']],
  ];
  for (const [label, pathname, params, arrayNames] of plans) {
    const data = await get(label, pathname, params);
    const list = overview(label, data, arrayNames);
    if (!data) continue;
    if (label === 'invoices') report.observations.invoices = list.map(x => ({
      id: id(x), invoiceNumber: x.invoiceNumber, ...retained(x, ['status','liveMode','currency','total','amountDue','amountPaid','issueDate','dueDate','createdAt','updatedAt']),
      issuer_name: x.businessDetails?.name ?? null, contact_id: x.contactDetails?.id ?? null,
      contact_identity_hash: hash(x.contactDetails?.email ?? x.contactDetails?.id),
      item_labels: (x.invoiceItems ?? []).map(y => y.name),
      reminder_keys: keys(x.remindersConfiguration), has_terms: Boolean(x.termsNotes || x.terms || x.termsAndConditions),
      keys: keys(x) }));
    if (['transactions','orders','subscriptions'].includes(label)) report.observations[label] = list.map(x => ({
      id: id(x), ...retained(x, ['status','currency','amount','amountRefunded','liveMode','createdAt','updatedAt','entityType','entityId','entitySourceType','entitySourceSubType','subscriptionId','contactId']), keys: keys(x) }));
    if (label === 'products') {
      report.observations.products = [];
      for (const x of list.slice(0, 3)) {
        const product = { id: id(x), name: x.name, keys: keys(x) };
        const priceData = await get(`prices_${id(x)}`, `/products/${encodeURIComponent(id(x))}/price`, { locationId, limit: 5, offset: 0 });
        product.prices = rows(priceData, 'prices').map(y => ({ id: id(y), ...retained(y, ['name','type','currency','amount','recurring']), keys: keys(y) }));
        report.observations.products.push(product);
      }
    }
    if (label === 'pipelines') report.observations.pipelines = list.map(x => ({ id: id(x), name: x.name,
      stages: (x.stages ?? []).map(y => ({ id: id(y), name: y.name, position: y.position })) }));
    if (label === 'opportunities') report.observations.opportunities = list.map(x => ({ id: id(x),
      ...retained(x, ['pipelineId','pipelineStageId','status','monetaryValue','source','createdAt','updatedAt','lastStatusChangeAt','lastStageChangeAt']), keys: keys(x) }));
    if (['calendars','surveys','forms'].includes(label)) report.observations[label] = list.map(x => ({ id: id(x), name: x.name, keys: keys(x) }));
    if (label === 'custom_fields') report.observations.custom_fields = list.map(x => ({ id: id(x), name: x.name, fieldKey: x.fieldKey, dataType: x.dataType }));
    if (['survey_submissions','form_submissions'].includes(label)) report.observations[label] = list.map(x => ({ id: id(x), keys: keys(x), has_contact: Boolean(x.contactId), created_at: x.createdAt ?? null }));
  }
  const calendar = rows(cache.calendars, 'calendars')[0];
  if (calendar) {
    const end = Date.parse('2026-10-20T00:00:00Z');
    const data = await get('calendar_events', '/calendars/events', { locationId, calendarId: id(calendar), startTime: end - 7*86400000, endTime: end });
    const list = overview('calendar_events', data, ['events']);
    report.observations.appointment_shapes = list.slice(0, 5).map(x => ({ id: id(x),
      ...retained(x, ['calendarId','startTime','endTime','appointmentStatus']), keys: keys(x) }));
  }
  report.result = 'bounded_probe_completed';
}
const followup = process.argv.includes('--followup');
if (followup) {
  report.mode = 'bounded_followup_reads';
  if (token && locationId) {
    const audit = JSON.parse(await readFile(path.join(out, 'local_audit.json'), 'utf8'));
    for (const target of audit.unique_referenced_location_ids.filter(x => x !== locationId).slice(0, 2)) {
      const data = await get(`referenced_location_${target}`, `/locations/${encodeURIComponent(target)}`);
      if (data) {
        const loc = data.location ?? data;
        report.observations[target] = { id: id(loc), name: loc.name, keys: keys(loc) };
      }
    }
    for (const query of ['Funktastic', 'Dogwood', 'Luxury Travel']) {
      const label = `contact_query_${query}`;
      const data = await get(label, '/contacts/', { locationId, query, limit: 3 });
      const list = overview(label, data, ['contacts']);
      report.observations[label] = list.map(x => ({ id: id(x),
        identity_hash: hash(x.email ?? x.phone ?? id(x)), keys: keys(x),
        company_name_matches_query: (x.companyName ?? '').toLowerCase().includes(query.toLowerCase()),
        fields_present: present(x, ['companyName','dateAdded','source','tags','customFields']) }));
    }
    report.result = 'bounded_followup_completed';
  } else report.result = 'credential_or_location_missing';
} else await main();
report.finished_at_utc = new Date().toISOString();
await writeFile(path.join(out, followup ? 'followup_probe.json' : 'live_probe.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
