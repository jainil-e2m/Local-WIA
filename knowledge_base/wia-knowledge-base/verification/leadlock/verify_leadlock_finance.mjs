/** Bounded GET-only finance probe for WIA's own GHL sub-account (Invoices & Contracts, decision F1).
 * Uses GHL_FINANCE_PIT + GHL_LOCATION_ID from frontend/.env (or the process environment).
 * Never prints or saves the token, contact names, emails or phone numbers; contact IDs are hashed.
 * Saves aggregates and record shapes only. Nothing is created, sent, voided or changed.
 * Run: node knowledge_base/wia-knowledge-base/verification/leadlock/verify_leadlock_finance.mjs
 */
import { readFile, writeFile } from 'node:fs/promises';
import { parseEnv } from 'node:util';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const out = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(out, '../../../..');
let token = process.env.GHL_FINANCE_PIT;
let locationId = process.env.GHL_LOCATION_ID;
let credentialSource = token ? 'process environment' : null;
for (const file of ['frontend/.env', 'frontend/.env.local']) {
  if (token && locationId) break;
  try {
    const values = parseEnv(await readFile(path.join(root, file), 'utf8'));
    if (!token && values.GHL_FINANCE_PIT) { token = values.GHL_FINANCE_PIT; credentialSource = `${file}:GHL_FINANCE_PIT`; }
    locationId ||= values.GHL_LOCATION_ID;
  } catch { /* Report missing credentials without revealing contents. */ }
}
if (!token || !locationId) { console.error('Missing GHL_FINANCE_PIT or GHL_LOCATION_ID.'); process.exit(1); }

const VERSION = '2021-07-28';
const HOST = 'https://services.leadconnectorhq.com';
const TODAY = new Date().toISOString().slice(0, 10);
const MAX_PAGES = 10;
const PAGE = 100;
const report = { review_date: TODAY, started_at_utc: new Date().toISOString(), mode: 'bounded_get_only_finance_probe',
  credential_source: credentialSource, configured_location_id: locationId, version_header: VERSION, calls: [], findings: {} };
const hash = value => value ? createHash('sha256').update(String(value)).digest('hex').slice(0, 12) : null;
const keys = row => row && typeof row === 'object' ? Object.keys(row).sort() : [];
const scrub = text => String(text ?? '').replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, '[email]').replace(/\+?\d[\d\s().-]{7,}\d/g, '[phone]').slice(0, 120);
const tally = list => list.reduce((acc, v) => { const k = v ?? '(none)'; acc[k] = (acc[k] || 0) + 1; return acc; }, {});
const top = (obj, n = 25) => Object.fromEntries(Object.entries(obj).sort((a, b) => b[1] - a[1]).slice(0, n));
const num = v => typeof v === 'number' ? v : Number(v) || 0;
const range = list => { const d = list.filter(Boolean).map(x => String(x).slice(0, 10)).sort(); return d.length ? { earliest: d[0], latest: d[d.length - 1] } : null; };

let requestCount = 0;
async function get(label, pathname, params = {}) {
  if (requestCount++) await new Promise(resolve => setTimeout(resolve, 650));
  const url = new URL(pathname, HOST);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, String(value));
  const record = { label, method: 'GET', path: pathname, query: params };
  report.calls.push(record);
  try {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${token}`, Version: VERSION, Accept: 'application/json' }, signal: AbortSignal.timeout(20000), redirect: 'error' });
    record.http_status = response.status;
    const text = await response.text();
    let data; try { data = JSON.parse(text); } catch { data = null; }
    record.ok = response.ok;
    record.top_level_keys = keys(data);
    if (!response.ok) { record.error = JSON.stringify(data?.message ?? data?.error ?? text.slice(0, 250)).replaceAll(token, '[REDACTED]').slice(0, 400); return null; }
    for (const k of ['total', 'totalCount', 'count']) if (typeof data?.[k] === 'number') record[k] = data[k];
    return data;
  } catch (error) {
    record.ok = false; record.error = 'network_or_response_error'; record.error_type = error.name;
    return null;
  }
}
const rows = (data, ...names) => { if (Array.isArray(data)) return data; for (const n of names) if (Array.isArray(data?.[n])) return data[n]; return []; };

/** Page through a location-scoped list until empty, the reported total, or MAX_PAGES. */
async function pageAll(label, pathname, names, extra = {}) {
  const all = []; let total = null;
  for (let page = 0; page < MAX_PAGES; page++) {
    const data = await get(`${label}#${page + 1}`, pathname, { altId: locationId, altType: 'location', limit: PAGE, offset: page * PAGE, ...extra });
    if (!data) return { ok: page > 0, rows: all, total, denied: page === 0 };
    const list = rows(data, ...names);
    total ??= data.total ?? data.totalCount ?? null;
    all.push(...list);
    if (list.length < PAGE || (total != null && all.length >= total)) break;
  }
  return { ok: true, rows: all, total, denied: false, truncated: total != null && all.length < total };
}

// 0. Sanity: the token reads WIA's location.
const loc = await get('location', `/locations/${locationId}`);
report.findings.location = loc ? { readable: true, name: scrub(loc.location?.name ?? loc.name), timezone: loc.location?.timezone ?? loc.timezone ?? null } : { readable: false };

// 1. Invoices: the ledger (overdue, balances, statuses).
const inv = await pageAll('invoices', '/invoices/', ['invoices', 'data']);
report.findings.invoices = inv.denied ? { access: 'denied' } : (() => {
  const r = inv.rows;
  const due = i => num(i.amountDue ?? (num(i.total) - num(i.amountPaid)));
  const open = r.filter(i => !['paid', 'void', 'draft'].includes(String(i.status).toLowerCase()) && due(i) > 0);
  const overdue = open.filter(i => i.dueDate && String(i.dueDate).slice(0, 10) < TODAY);
  const byStatus = {};
  for (const i of r) { const s = i.status ?? '(none)'; byStatus[s] ??= { count: 0, total: 0, amount_due: 0 }; byStatus[s].count++; byStatus[s].total += num(i.total); byStatus[s].amount_due += due(i); }
  return {
    access: 'granted', reported_total: inv.total, retrieved: r.length, truncated: inv.truncated ?? false,
    sample_row_keys: keys(r[0]), item_keys: keys((r[0]?.invoiceItems ?? r[0]?.items ?? [])[0]),
    live_mode: tally(r.map(i => String(i.liveMode))), currencies: tally(r.map(i => i.currency)),
    by_status: byStatus, issue_dates: range(r.map(i => i.issueDate)), due_dates: range(r.map(i => i.dueDate)),
    open_count: open.length, open_amount_due: open.reduce((s, i) => s + due(i), 0),
    overdue_count: overdue.length, overdue_amount_due: overdue.reduce((s, i) => s + due(i), 0),
    overdue_age_days: overdue.map(i => Math.round((Date.parse(TODAY) - Date.parse(String(i.dueDate).slice(0, 10))) / 86400000)).sort((a, b) => a - b),
    distinct_contacts: new Set(r.map(i => hash(i.contactDetails?.id ?? i.contactId))).size,
    invoice_titles: top(tally(r.map(i => scrub(i.name ?? i.title)))),
    line_item_names: top(tally(r.flatMap(i => (i.invoiceItems ?? i.items ?? []).map(it => scrub(it.name))))),
    from_schedule: tally(r.map(i => String(Boolean(i.scheduleId ?? i.recurringInvoiceId ?? i.schedule)))),
    partial_payments: r.filter(i => num(i.amountPaid) > 0 && due(i) > 0).length,
    reminders_fields_present: r.some(i => i.reminders || i.reminderSettings || i.automaticTaxesEnabled !== undefined),
    // "Paid" invoices that still carry an amount due: how were they marked paid?
    paid_with_amount_due: (() => { const p = r.filter(i => String(i.status) === 'paid' && num(i.amountDue) > 0); return {
      count: p.length, amount_due: p.reduce((s, i) => s + num(i.amountDue), 0), amount_paid_zero: p.filter(i => !num(i.amountPaid)).length,
      with_external_transactions: p.filter(i => (i.externalTransactions ?? []).length).length,
      with_manual_status_transition: p.filter(i => i.manualStatusTransitions && Object.keys(i.manualStatusTransitions).length).length,
      issue_dates: range(p.map(i => i.issueDate)) }; })(),
    reminders_configuration_keys: keys(r.find(i => i.remindersConfiguration)?.remindersConfiguration),
    reminders_enabled: tally(r.map(i => String(i.remindersConfiguration?.reminderSettings?.defaultEmailTemplateId ? 'template' : i.remindersConfiguration?.enabled ?? i.remindersConfiguration?.reminders?.length ?? 'unknown'))),
    late_fees_enabled: tally(r.map(i => String(i.lateFeesConfiguration?.enable ?? i.lateFeesConfiguration?.enabled ?? 'unknown'))),
    open_invoices: open.map(i => ({ status: i.status, title: scrub(i.name ?? i.title), amount_due: due(i), issue: String(i.issueDate).slice(0, 10), due: String(i.dueDate).slice(0, 10),
      days_past_due: Math.round((Date.parse(TODAY) - Date.parse(String(i.dueDate).slice(0, 10))) / 86400000), from_schedule: Boolean(i.scheduleId), sent: Boolean(i.sentAt), contact: hash(i.contactDetails?.id) })),
    issued_per_month_last_12: (() => { const m = tally(r.map(i => String(i.issueDate).slice(0, 7))); return Object.fromEntries(Object.entries(m).sort().slice(-12)); })(),
  };
})();

// 2. Recurring invoice schedules: billing plans and the missing-invoice check.
const sch = await pageAll('invoice_schedules', '/invoices/schedule', ['schedules', 'data']);
report.findings.invoice_schedules = sch.denied ? { access: 'denied' } : {
  access: 'granted', reported_total: sch.total, retrieved: sch.rows.length, sample_row_keys: keys(sch.rows[0]),
  statuses: tally(sch.rows.map(s => s.status)), live_mode: tally(sch.rows.map(s => String(s.liveMode))),
  intervals: tally(sch.rows.map(s => s.schedule?.rrule?.intervalType ?? s.schedule?.rrule?.frequency ?? s.schedule?.intervalType ?? '(unknown)')),
  amounts: tally(sch.rows.map(s => num(s.total ?? s.amount))), titles: top(tally(sch.rows.map(s => scrub(s.name ?? s.title)))),
  distinct_contacts: new Set(sch.rows.map(s => hash(s.contactDetails?.id ?? s.contactId))).size,
  schedule_keys: keys(sch.rows[0]?.schedule), rrule_keys: keys(sch.rows[0]?.schedule?.rrule),
  auto_payment: tally(sch.rows.map(s => String(s.autoPayment?.enable ?? s.autoPayment?.enabled ?? Boolean(s.autoPayment)))),
  active_monthly_total: sch.rows.filter(s => s.status === 'active').reduce((t, s) => t + num(s.total), 0),
  active_next_dates: sch.rows.filter(s => s.status === 'active').map(s => String(s.schedule?.rrule?.nextExecutionDate ?? s.schedule?.nextExecutionDate ?? s.schedule?.executeAt ?? '').slice(0, 10)).sort(),
};

// 3. Transactions: payments received, failures, refunds.
const tx = await pageAll('transactions', '/payments/transactions', ['data', 'transactions']);
report.findings.transactions = tx.denied ? { access: 'denied' } : (() => {
  const r = tx.rows; const byStatus = {};
  for (const t of r) { const s = t.status ?? '(none)'; byStatus[s] ??= { count: 0, amount: 0 }; byStatus[s].count++; byStatus[s].amount += num(t.amount); }
  return { access: 'granted', reported_total: tx.total, retrieved: r.length, truncated: tx.truncated ?? false, sample_row_keys: keys(r[0]),
    by_status: byStatus, live_mode: tally(r.map(t => String(t.liveMode))), currencies: tally(r.map(t => t.currency)),
    entity_source_type: tally(r.map(t => t.entitySourceType)), entity_source_name: top(tally(r.map(t => scrub(t.entitySourceName)))),
    payment_provider: tally(r.map(t => t.paymentProviderType ?? t.paymentProvider?.type)), dates: range(r.map(t => t.createdAt)),
    distinct_contacts: new Set(r.map(t => hash(t.contactId))).size };
})();

// 4. Subscriptions: recurring charges (e.g. LeadLock monthly).
const sub = await pageAll('subscriptions', '/payments/subscriptions', ['data', 'subscriptions']);
report.findings.subscriptions = sub.denied ? { access: 'denied' } : {
  access: 'granted', reported_total: sub.total, retrieved: sub.rows.length, sample_row_keys: keys(sub.rows[0]),
  statuses: tally(sub.rows.map(s => s.status)), live_mode: tally(sub.rows.map(s => String(s.liveMode))),
  entity_source_type: tally(sub.rows.map(s => s.entitySourceType)), entity_source_name: top(tally(sub.rows.map(s => scrub(s.entitySourceName)))),
  amounts: tally(sub.rows.map(s => num(s.amount))), currencies: tally(sub.rows.map(s => s.currency)),
  provider: tally(sub.rows.map(s => s.paymentProviderType)), created: range(sub.rows.map(s => s.createdAt)),
  distinct_contacts: new Set(sub.rows.map(s => hash(s.contactId))).size,
};

// 5. Orders: checkout purchases (e.g. the offer already sold through GHL checkout).
const ord = await pageAll('orders', '/payments/orders', ['data', 'orders']);
report.findings.orders = ord.denied ? { access: 'denied' } : {
  access: 'granted', reported_total: ord.total, retrieved: ord.rows.length, sample_row_keys: keys(ord.rows[0]),
  statuses: tally(ord.rows.map(o => o.status)), payment_status: tally(ord.rows.map(o => o.paymentStatus)),
  live_mode: tally(ord.rows.map(o => String(o.liveMode))), source_type: tally(ord.rows.map(o => o.source?.type ?? o.sourceType)),
  source_name: top(tally(ord.rows.map(o => scrub(o.source?.name ?? o.sourceName)))), amounts: tally(ord.rows.map(o => num(o.amount))),
  created: range(ord.rows.map(o => o.createdAt)), distinct_contacts: new Set(ord.rows.map(o => hash(o.contactId))).size,
};

// 6. Products and prices: list prices only (FIN-V-01), never contract values.
const prodData = await get('products', '/products/', { locationId, limit: 100 });
const products = rows(prodData, 'products', 'data');
report.findings.products = !prodData ? { access: 'denied' } : { access: 'granted', count: products.length, sample_row_keys: keys(products[0]), items: [] };
if (prodData) for (const p of products.slice(0, 25)) {
  const priceData = await get(`prices:${hash(p._id)}`, `/products/${p._id}/price`, { locationId });
  const prices = rows(priceData, 'prices', 'data');
  report.findings.products.items.push({ name: scrub(p.name), type: p.productType ?? null, prices_access: priceData ? 'granted' : 'denied',
    prices: prices.map(pr => ({ name: scrub(pr.name), type: pr.type, amount: pr.amount, currency: pr.currency, interval: pr.recurring?.interval ?? null, interval_count: pr.recurring?.intervalCount ?? null })) });
}

report.finished_at_utc = new Date().toISOString();
report.request_count = requestCount;
report.access_summary = Object.fromEntries(Object.entries(report.findings).map(([k, v]) => [k, v.access ?? (v.readable ? 'granted' : 'denied')]));
const file = path.join(out, `finance_probe_${TODAY}.json`);
await writeFile(file, JSON.stringify(report, null, 2));
console.log(JSON.stringify({ saved: path.relative(root, file), requests: requestCount, access: report.access_summary,
  statuses: report.calls.map(c => `${c.label} ${c.http_status ?? c.error}`) }, null, 1));
