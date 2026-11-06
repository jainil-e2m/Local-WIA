/** Builds the LOCAL-ONLY live finance dataset for the Invoices & Contracts v2 mockup.
 * GET-only against WIA's own GHL sub-account (GHL_FINANCE_PIT + GHL_LOCATION_ID in frontend/.env).
 * Keeps client/company names, amounts, dates, statuses and service titles so the layout can be judged on
 * real data. Drops emails, phone numbers, addresses, payment-method details and IP addresses.
 * Output: knowledge_base/wia-knowledge-base/frontend/src/finance-live.local.json (gitignored; never ship it).
 * Run: node knowledge_base/wia-knowledge-base/verification/leadlock/build_finance_live.mjs
 */
import { readFile, writeFile } from 'node:fs/promises';
import { parseEnv } from 'node:util';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../../..');
const target = path.resolve(here, '../../frontend/src/finance-live.local.json');
const env = parseEnv(await readFile(path.join(root, 'frontend/.env'), 'utf8'));
const token = process.env.GHL_FINANCE_PIT || env.GHL_FINANCE_PIT;
const locationId = process.env.GHL_LOCATION_ID || env.GHL_LOCATION_ID;
if (!token || !locationId) { console.error('Missing GHL_FINANCE_PIT or GHL_LOCATION_ID.'); process.exit(1); }

const HOST = 'https://services.leadconnectorhq.com';
// reminderExecutionDetailsList may be an array or an object keyed by reminder.
const listOf = v => Array.isArray(v) ? v : v && typeof v === 'object' ? Object.values(v).flatMap(x => Array.isArray(x) ? x : [x]) : [];
const keys = o => o && typeof o === 'object' ? Object.keys(o).sort() : [];
const day = v => v ? String(v).slice(0, 10) : '';
const num = v => typeof v === 'number' ? v : Number(v) || 0;
const clean = t => String(t ?? '').replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, '').replace(/\+?\d[\d\s().-]{7,}\d/g, '').trim();
let n = 0;
async function get(p, params) {
  if (n++) await new Promise(r => setTimeout(r, 650));
  const url = new URL(p, HOST); for (const [k, v] of Object.entries(params)) url.searchParams.set(k, String(v));
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}`, Version: '2021-07-28', Accept: 'application/json' }, signal: AbortSignal.timeout(20000), redirect: 'error' });
  if (!res.ok) throw new Error(`${p} → HTTP ${res.status}`);
  return res.json();
}
async function all(p, names) {
  const out = [];
  for (let page = 0; page < 10; page++) {
    const data = await get(p, { altId: locationId, altType: 'location', limit: 100, offset: page * 100 });
    const list = names.map(k => data[k]).find(Array.isArray) ?? [];
    out.push(...list);
    if (list.length < 100) break;
  }
  return out;
}

const invoices = (await all('/invoices/', ['invoices', 'data'])).filter(i => i.liveMode !== false);
const schedules = (await all('/invoices/schedule', ['schedules', 'data'])).filter(s => s.liveMode !== false);
const transactions = (await all('/payments/transactions', ['data', 'transactions'])).filter(t => t.liveMode !== false);

// Shapes only (no values), so the adapter can be checked against real field names.
const shapes = { contactDetails: keys(invoices[0]?.contactDetails), reminderExecutionList: keys(invoices.find(i => i.remindersConfiguration?.reminderExecutionDetailsList)?.remindersConfiguration.reminderExecutionDetailsList), reminderExecution: keys(listOf(invoices.find(i => listOf(i.remindersConfiguration?.reminderExecutionDetailsList).length)?.remindersConfiguration.reminderExecutionDetailsList)[0]),
  scheduleRrule: keys(schedules[0]?.schedule?.rrule), transaction: keys(transactions[0]) };

const contact = c => ({ id: c?.id ?? c?._id ?? '', name: clean(c?.name), company: clean(c?.companyName) });
const clients = new Map();
const addClient = c => { const x = contact(c); if (x.id && !clients.has(x.id)) clients.set(x.id, x); return x.id; };

const data = {
  generated_at: new Date().toISOString(),
  today: new Date().toISOString().slice(0, 10),
  location: { id: locationId, timezone: 'America/Chicago' },
  note: 'Local-only real WIA billing data. Do not share, publish or commit.',
  shapes,
  invoices: invoices.map(i => ({
    id: i._id, number: `${i.invoiceNumberPrefix ?? ''}${i.invoiceNumber ?? ''}`, title: clean(i.name ?? i.title), clientId: addClient(i.contactDetails),
    status: i.status, total: num(i.total), paid: num(i.amountPaid), due: num(i.amountDue), issued: day(i.issueDate), dueDate: day(i.dueDate),
    sentAt: day(i.sentAt), scheduleId: i.scheduleId ?? null, items: (i.invoiceItems ?? []).map(it => ({ name: clean(it.name), amount: num(it.amount), qty: num(it.qty) || 1 })),
    reminders: listOf(i.remindersConfiguration?.reminderExecutionDetailsList).map(r => (r?.executedCount ?? 1) > 0 ? day(r?.executeAt ?? r?.executedAt ?? r?.createdAt) : "").filter(Boolean),
  })),
  schedules: schedules.map(s => ({
    id: s._id, title: clean(s.name ?? s.title), clientId: addClient(s.contactDetails), status: s.status, total: num(s.total),
    autoPay: Boolean(s.autoPayment?.enable ?? s.autoPayment?.enabled ?? s.autoPayment), rrule: s.schedule?.rrule ?? null,
    items: (s.items ?? []).map(it => ({ name: clean(it.name), amount: num(it.amount) })), createdAt: day(s.createdAt),
  })),
  transactions: transactions.map(t => ({ id: t._id, clientId: t.contactId ?? '', status: t.status, amount: num(t.amount), refunded: num(t.amountRefunded),
    date: day(t.createdAt), source: t.entitySourceType, sourceName: clean(t.entitySourceName), invoiceId: t.entityType === 'invoice' || t.entitySourceType === 'invoice' ? (t.entityId ?? t.entitySourceId ?? null) : null, provider: t.paymentProviderType })),
};
// Transaction-only contacts (calendar/funnel purchases) get a name from the transaction itself.
for (const t of transactions) if (t.contactId && !clients.has(t.contactId)) clients.set(t.contactId, { id: t.contactId, name: clean(t.contactName), company: '' });
data.clients = [...clients.values()];
await writeFile(target, JSON.stringify(data, null, 2));
console.log(JSON.stringify({ saved: path.relative(root, target), requests: n, invoices: data.invoices.length, schedules: data.schedules.length, transactions: data.transactions.length, clients: data.clients.length, shapes }, null, 1));
