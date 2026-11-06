import raw from '@finance-live';
import dubsadoRaw from '@dubsado-live';
import { addDays, registerClients } from './data';
import { AGREEMENTS, FAILED_PAYMENTS, FINANCE_CLIENTS, FINANCE_META, INVOICES2, PLANS, UNMATCHED, setFinanceToday, type Agreement, type BillingPlan, type Invoice2, type Unmatched } from './finance';
import type { Client, Tone } from './types';

/*
 * Local live export only. '@finance-live' resolves to src/finance-live.local.json (real GHL data, gitignored)
 * in `npm run export:live`, and to an empty stub in every other build, where this module does nothing.
 * When data is present it replaces the finance sample in place, so every finance view reads real records.
 */

export interface LiveRaw {
  generated_at?: string; today?: string;
  clients: { id: string; name: string; company: string }[];
  invoices: { id: string; number: string; title: string; clientId: string; status: string; total: number; paid: number; due: number; issued: string; dueDate: string; sentAt: string; scheduleId: string | null; items: { name: string; amount: number; qty: number }[]; reminders: string[] }[];
  schedules: { id: string; title: string; clientId: string; status: string; total: number; autoPay: boolean; rrule: { dayOfMonth?: number; daysBefore?: number; interval?: number; startDate?: string } | null; items: { name: string; amount: number }[]; createdAt: string }[];
  transactions: { id: string; clientId: string; status: string; amount: number; refunded: number; date: string; source: string; sourceName: string; invoiceId: string | null; provider: string }[];
}

/** Dubsado notifications from hello@ (subject lines only): contract signings and payment alerts. */
export interface DubsadoRaw {
  generated_at?: string;
  events: { id: string; date: string; link?: string | null; type: 'signed' | 'paid'; person: string; amount?: number; currency?: string; label: string; offer: string | null; business: string; clientId: string | null }[];
}

const data = raw as LiveRaw;
const dubsado = dubsadoRaw as DubsadoRaw;
const TONES: Tone[] = ['blue', 'green', 'amber', 'rose', 'gold'];
const monthName = (d: string) => new Intl.DateTimeFormat('en-US', { month: 'long' }).format(new Date(`${d}T12:00:00Z`));
const ymd = (y: number, m: number, d: number) => { const last = new Date(Date.UTC(y, m + 1, 0)).getUTCDate(); return new Date(Date.UTC(y, m, Math.min(d, last))).toISOString().slice(0, 10); };

if (data.invoices.length) {
  const today = data.today || new Date().toISOString().slice(0, 10);
  setFinanceToday(today);
  FINANCE_META.live = true;
  FINANCE_META.generatedAt = data.generated_at ?? '';
  FINANCE_META.syncedAt = data.generated_at ? new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(data.generated_at)) : '';

  // Clients: one record per GHL contact. Service = the active plan, or the latest invoice title.
  const latestTitle = new Map<string, string>();
  [...data.invoices].sort((a, b) => a.issued.localeCompare(b.issued)).forEach(i => latestTitle.set(i.clientId, i.title));
  const activePlan = new Map(data.schedules.filter(s => s.status === 'active').map(s => [s.clientId, s.title]));
  const clients: Client[] = data.clients.map((c, n) => {
    const name = c.company || c.name || 'Unnamed contact';
    return { id: c.id, name, initials: name.split(/\s+/).filter(Boolean).map(w => w[0]).join('').slice(0, 2).toUpperCase() || '?', contact: c.name || name, email: 'email on file in GHL',
      location: '', service: activePlan.get(c.id) ?? latestTitle.get(c.id) ?? '—', type: 'retainer', category: '', health: 'On track', tone: TONES[n % TONES.length],
      since: '', summary: '', focus: '', sentiment: '', lastTouch: '', coverage: 0, activity: [], story: '', audience: '', differentiator: '', voice: '', goal: '', profileSource: '' } as Client;
  });
  // Dubsado events with no GHL contact get a Dubsado-only client named after the project label.
  const slug = (t: string) => t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const dubClient = (e: DubsadoRaw['events'][number]) => e.clientId ?? `dub:${slug(e.business || e.label || e.person)}`;
  for (const e of dubsado.events) {
    const id = dubClient(e);
    if (clients.some(c => c.id === id)) continue;
    const name = e.business || e.label || e.person;
    clients.push({ ...clients[0], id, name, initials: name.split(/\s+/).filter(Boolean).map(w => w[0]).join('').slice(0, 2).toUpperCase() || '?', contact: e.person, service: e.offer ?? 'Dubsado project', tone: TONES[clients.length % TONES.length] } as Client);
  }
  registerClients(clients);

  // Invoices: GHL invoice records are the ledger, so every one is Reconciled.
  const succeeded = data.transactions.filter(t => t.status === 'succeeded' && t.invoiceId);
  const invoices: Invoice2[] = data.invoices.filter(i => i.status !== 'draft' && i.status !== 'void').map(i => ({
    id: i.number || i.id, clientId: i.clientId, engagement: i.title, source: 'GHL', basis: 'Reconciled', issued: i.issued, due: i.dueDate,
    amount: i.total, paid: i.status === 'paid' ? Math.max(i.paid, i.total) : i.paid, currency: 'USD',
    lines: i.items.length ? i.items.map(it => it.name) : [i.title],
    payments: succeeded.filter(t => t.invoiceId === i.id).map(t => ({ date: t.date, amount: t.amount, note: `${t.provider === 'manual' ? 'Manual' : 'Stripe'} · GHL payment` })),
    reminders: i.reminders.map(date => ({ date, kind: 'Automatic (GHL)' as const })),
    evidence: `GHL invoice ${i.number || i.id}${i.scheduleId ? ' · recurring schedule' : ' · one-off'}${i.status === 'paid' && !i.paid ? ' · marked paid with no payment recorded' : ''}`,
  }));
  const byGhlId = new Map(data.invoices.map(i => [i.id, i]));

  // Plans: active and upcoming recurring schedules. Due on dayOfMonth; GHL issues the invoice daysBefore that.
  const plans: BillingPlan[] = data.schedules.filter(s => s.status === 'active' || s.status === 'scheduled').map(s => {
    const r = s.rrule ?? {}; const dom = r.dayOfMonth ?? 1; const before = r.daysBefore ?? 0; const start = String(r.startDate ?? s.createdAt).slice(0, 10);
    const [y, m] = today.split('-').map(Number);
    const occurrences = [-2, -1, 0, 1, 2].map(k => ymd(y, m - 1 + k, dom)).filter(d => d >= start);
    const nextDue = occurrences.find(d => addDays(d, -before) >= today) ?? occurrences[occurrences.length - 1];
    // Missing: an occurrence whose issue date has passed but no invoice from this schedule is due within ±5 days of it.
    const generated = data.invoices.filter(i => i.scheduleId === s.id).map(i => i.dueDate);
    const missed = occurrences.filter(d => addDays(d, -before) <= today && d <= addDays(today, 7)).filter(d => !generated.some(g => Math.abs(Date.parse(g) - Date.parse(d)) <= 5 * 86400000));
    const lastMissed = missed[missed.length - 1];
    return { clientId: s.clientId, engagement: s.title, plan: `Recurring invoice · ${s.autoPay ? 'auto-pay' : 'manual payment'}${s.status === 'scheduled' ? ' · starts ' + start : ''}`, amount: s.total,
      interval: 'Monthly', source: 'GHL', nextInvoice: nextDue ? addDays(nextDue, -before) : undefined,
      missing: lastMissed ? `${monthName(lastMissed)} invoice expected by ${addDays(lastMissed, -before)} (due ${lastMissed}). No invoice from this schedule found.` : undefined,
      expectedDate: lastMissed ? addDays(lastMissed, -before) : undefined };
  });

  // Failed payments: unresolved while the linked invoice is still unpaid.
  const failed = data.transactions.filter(t => t.status === 'failed').map(t => {
    const inv = t.invoiceId ? byGhlId.get(t.invoiceId) : undefined;
    return { id: t.id, clientId: t.clientId, invoiceId: inv ? (inv.number || inv.id) : undefined, date: t.date, amount: t.amount, source: t.sourceName || t.source, resolved: !inv || inv.status === 'paid' };
  });

  // Finance tabs list clients with a current plan, an open invoice, or an invoice in the last 180 days.
  const recent = addDays(today, -180);
  const relevant = new Set([...plans.map(p => p.clientId), ...invoices.filter(i => i.paid < i.amount || i.issued >= recent).map(i => i.clientId)]);

  // Dubsado: signings become agreements (terms unread); payment alerts become Reported invoices (never Overdue).
  const agreements: Agreement[] = dubsado.events.filter(e => e.type === 'signed').map(e => ({
    id: `dub-${e.id}`, clientId: dubClient(e), name: e.label, engagements: [e.offer ?? 'Offer not named in the project label'], source: 'Dubsado', signed: e.date, signer: e.person,
    status: 'Active', link: e.link ?? undefined,
    termsNote: e.link ? 'Signing alert read from hello@. Terms are not extracted; the signed contract opens in Dubsado.' : 'Signing alert read from hello@. No contract link was found in the alert, so the terms are unknown.' }));
  const reported: Invoice2[] = dubsado.events.filter(e => e.type === 'paid').map(e => ({
    id: `DUB-${e.id.slice(-6).toUpperCase()}`, clientId: dubClient(e), engagement: e.offer ?? e.label, source: 'Dubsado', basis: 'Reported', issued: e.date, due: e.date,
    amount: e.amount ?? 0, paid: e.amount ?? 0, currency: 'USD', lines: [`${e.label} · payment (Dubsado alert)`],
    payments: [{ date: e.date, amount: e.amount ?? 0, note: 'Dubsado payment alert (notification time)' }], reminders: [], evidence: `Dubsado alert in hello@ · Gmail message ${e.id}`, agreementId: undefined, link: e.link ?? undefined }));
  // Recent events that match no GHL contact need a person: usually a new client not yet in GHL.
  const unmatched: Unmatched[] = dubsado.events.filter(e => !e.clientId && e.date >= addDays(today, -45)).map(e => ({
    id: e.id, date: e.date, text: `Dubsado: ${e.person} ${e.type === 'signed' ? 'signed the contract for' : `paid ${e.amount?.toLocaleString('en-US', { style: 'currency', currency: 'USD' })} for`} ${e.label}`,
    reason: 'No matching GHL contact. Likely a new client, or a different name in GHL.', amount: e.type === 'paid' ? e.amount : undefined }));
  if (dubsado.events.length) FINANCE_META.dubsadoSyncedAt = dubsado.generated_at ? new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(dubsado.generated_at)) : '';
  for (const a of agreements) if (a.signed! >= recent) relevant.add(a.clientId);
  invoices.push(...reported);

  INVOICES2.splice(0, INVOICES2.length, ...invoices);
  PLANS.splice(0, PLANS.length, ...plans);
  AGREEMENTS.splice(0, AGREEMENTS.length, ...agreements);
  UNMATCHED.splice(0, UNMATCHED.length, ...unmatched);
  FAILED_PAYMENTS.splice(0, FAILED_PAYMENTS.length, ...failed);
  FINANCE_CLIENTS.splice(0, FINANCE_CLIENTS.length, ...clients.filter(c => relevant.has(c.id)));
}
