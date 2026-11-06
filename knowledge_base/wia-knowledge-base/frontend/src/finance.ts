import { DEMO_DATE, SLACK_ADMINS, addDays, daysBetween } from './data';
import type { Client } from './types';

// The mockup's reference date. The local live export moves it to the real date so real invoices age correctly.
let financeToday = DEMO_DATE;
export const finToday = () => financeToday;
export const setFinanceToday = (date: string) => { financeToday = date; };
export const finDaysSince = (date: string) => daysBetween(date, financeToday);

// Fictional finance records for the Invoices & Contracts scope (kb_tab_scope/03-invoices-contracts.md).
// Dubsado: proposal, agreement and first invoice (alerts in hello@). GHL: ongoing invoices and payments (F1).

export const FINANCE_ADMINS = SLACK_ADMINS; // F2: Whitney and Gisselle only
export const isFinanceAdmin = (viewer: string) => FINANCE_ADMINS.includes(viewer);

export type Basis = 'Reconciled' | 'Reported' | 'Unknown';
export type FinSource = 'GHL' | 'Dubsado';

export interface Agreement {
  id: string; clientId: string; name: string; engagements: string[]; source: FinSource;
  proposalSent?: string; signed?: string; signer?: string; status: 'Sent' | 'Signed' | 'Active' | 'Ended' | 'Superseded';
  terms?: { fee: string; interval: string; start: string; minTerm?: string; end?: string; notice?: string; included: string[]; adSpend?: string };
  termsNote?: string;
  /** Public Dubsado contract link from the signing alert (local live export only). */
  link?: string;
}

export interface Invoice2 {
  id: string; clientId: string; engagement: string; source: FinSource; basis: Basis;
  issued: string; due: string; amount: number; paid: number; currency: 'USD';
  instalment?: { n: number; of: number };
  lines: string[];
  payments: { date: string; amount: number; note: string }[];
  reminders: { date: string; kind: 'Automatic (GHL)' | 'Personal chase (hello@)'; by?: string }[];
  agreementId?: string;
  evidence: string;
  /** Public Dubsado invoice link from the payment alert (local live export only). */
  link?: string;
}

export interface BillingPlan {
  clientId: string; engagement: string; plan: string; amount: number; interval: string; source: FinSource;
  nextInvoice?: string; instalments?: { paid: number; of: number }; missing?: string;
  /** When the missing invoice should have been issued. */
  expectedDate?: string;
}

export interface Unmatched { id: string; date: string; text: string; reason: string; amount?: number }

export const AGREEMENTS: Agreement[] = [
  { id: 'ag-bloom', clientId: 'bloom', name: 'Elevate · Bloom Manor 2026', engagements: ['Elevate'], source: 'Dubsado', proposalSent: '2026-03-30', signed: '2026-04-02', signer: 'Sarah Mitchell', status: 'Active', terms: { fee: '$2,500 per month', interval: 'Monthly, invoiced on the 1st, due on the 5th', start: '2026-04-06', minTerm: '6 months', notice: '30 days written notice', included: ['Google + Meta campaign management', 'Monthly strategy call', 'Landing-page updates (up to 2 per month)', 'Monthly performance summary'], adSpend: 'Paid by the client directly to Google and Meta' } },
  { id: 'ag-rose-e', clientId: 'rosewood', name: 'Elevate · Rosewood Estate', engagements: ['Elevate'], source: 'Dubsado', proposalSent: '2026-02-05', signed: '2026-02-09', signer: 'Dana Whitfield', status: 'Active', terms: { fee: '$2,500 per month', interval: 'Monthly, due on the 5th', start: '2026-02-12', minTerm: '6 months (passed 12 Aug)', notice: '30 days written notice', included: ['Google + Meta campaign management', 'Monthly strategy call', 'Monthly performance summary'], adSpend: 'Paid by the client directly' } },
  { id: 'ag-rose-l', clientId: 'rosewood', name: 'LeadLock · Rosewood Estate', engagements: ['LeadLock'], source: 'Dubsado', proposalSent: '2026-02-20', signed: '2026-02-24', signer: 'Dana Whitfield', status: 'Active', terms: { fee: '$1,697 setup + $147 per month', interval: 'Monthly on the 1st', start: '2026-03-01', notice: 'Cancel any time before the next billing date', included: ['LeadLock setup and follow-up workflows', 'Ongoing workflow support'] } },
  { id: 'ag-willow', clientId: 'willow', name: 'Meta Ads Accelerator · Willow & Pine', engagements: ['Meta Ads Accelerator'], source: 'Dubsado', proposalSent: '2026-07-08', signed: '2026-07-10', signer: 'Maya Stone', status: 'Active', termsNote: 'Signing alert read; the agreement page in Dubsado has not been read yet.' },
  { id: 'ag-everly', clientId: 'everly', name: 'Elevate · Everly Films', engagements: ['Elevate'], source: 'Dubsado', proposalSent: '2026-05-12', signed: '2026-05-14', signer: 'Nina Cole', status: 'Superseded', terms: { fee: '$2,200 per month', interval: 'Monthly, due on the 10th', start: '2026-05-18', minTerm: '6 months', end: '2026-11-17', notice: '30 days', included: ['Google + Meta campaign management', 'Monthly strategy call'] } },
  { id: 'ag-everly-2', clientId: 'everly', name: 'Elevate renewal · Everly Films 2027', engagements: ['Elevate'], source: 'Dubsado', proposalSent: '2026-10-02', signed: '2026-10-06', signer: 'Nina Cole', status: 'Signed', terms: { fee: '$2,400 per month', interval: 'Monthly, due on the 10th', start: '2026-11-18', minTerm: '12 months', end: '2027-11-17', notice: '30 days', included: ['Google + Meta campaign management', 'Monthly strategy call', 'Quarterly creative refresh'] } },
  { id: 'ag-harbor-e', clientId: 'harbor', name: 'Elevate · Harbor House', engagements: ['Elevate'], source: 'Dubsado', proposalSent: '2026-09-16', signed: '2026-09-19', signer: 'Elise Bennett', status: 'Active', terms: { fee: '$2,500 per month', interval: 'Monthly, due on the 1st', start: '2026-09-21', minTerm: '6 months', notice: '30 days', included: ['Google + Meta campaign management', 'Monthly strategy call', 'Messaging & positioning'], adSpend: 'Paid by the client directly' } },
  { id: 'ag-harbor-l', clientId: 'harbor', name: 'Foolproof Follow-Up Advantage (LeadLock)', engagements: ['LeadLock'], source: 'GHL', signed: '2026-09-19', signer: 'Elise Bennett', status: 'Active', terms: { fee: '$1,697 setup + $147 per month', interval: 'Monthly on the 21st', start: '2026-09-21', included: ['LeadLock setup', 'Follow-up workflows'] }, termsNote: 'Sold through the GHL checkout (offer already migrated from Dubsado).' },
  { id: 'ag-magnolia', clientId: 'magnolia', name: 'Google Search Accelerator · Magnolia Events', engagements: ['Google Search Accelerator'], source: 'Dubsado', proposalSent: '2026-05-27', signed: '2026-05-29', signer: 'Tessa Ruiz', status: 'Active', terms: { fee: '$1,997 paid in full', interval: 'One-off', start: '2026-06-02', end: '2026-12-01', included: ['16-week programme', 'Weekly Google office hours', '6 months of support'] } },
];

const inv = (x: Partial<Invoice2> & Pick<Invoice2, 'id' | 'clientId' | 'engagement' | 'source' | 'basis' | 'issued' | 'due' | 'amount' | 'paid'>): Invoice2 => ({ currency: 'USD', lines: [], payments: [], reminders: [], evidence: x.source === 'GHL' ? 'GHL invoice record' : 'Dubsado alert in hello@', ...x });

export const INVOICES2: Invoice2[] = [
  inv({ id: 'GHL-2041', clientId: 'bloom', engagement: 'Elevate', source: 'GHL', basis: 'Reconciled', issued: '2026-10-01', due: '2026-10-05', amount: 2500, paid: 0, agreementId: 'ag-bloom', lines: ['Elevate retainer · October'], reminders: [{ date: '2026-10-03', kind: 'Automatic (GHL)' }, { date: '2026-10-06', kind: 'Automatic (GHL)' }] }),
  inv({ id: 'GHL-1987', clientId: 'bloom', engagement: 'Elevate', source: 'GHL', basis: 'Reconciled', issued: '2026-09-01', due: '2026-09-05', amount: 2500, paid: 2500, agreementId: 'ag-bloom', lines: ['Elevate retainer · September'], payments: [{ date: '2026-09-09', amount: 2500, note: 'Card · GHL payment' }], reminders: [{ date: '2026-09-06', kind: 'Automatic (GHL)' }, { date: '2026-09-08', kind: 'Personal chase (hello@)', by: 'Gisselle' }] }),
  inv({ id: 'GHL-2042', clientId: 'rosewood', engagement: 'Elevate', source: 'GHL', basis: 'Reconciled', issued: '2026-10-01', due: '2026-10-05', amount: 2500, paid: 2500, agreementId: 'ag-rose-e', lines: ['Elevate retainer · October'], payments: [{ date: '2026-10-03', amount: 2500, note: 'ACH · GHL payment' }] }),
  inv({ id: 'GHL-2039', clientId: 'rosewood', engagement: 'LeadLock', source: 'GHL', basis: 'Reconciled', issued: '2026-10-01', due: '2026-10-01', amount: 147, paid: 147, agreementId: 'ag-rose-l', lines: ['LeadLock subscription · October'], payments: [{ date: '2026-10-01', amount: 147, note: 'Card · automatic' }] }),
  inv({ id: 'GHL-2043', clientId: 'everly', engagement: 'Elevate', source: 'GHL', basis: 'Reconciled', issued: '2026-10-01', due: '2026-10-10', amount: 2200, paid: 0, agreementId: 'ag-everly', lines: ['Elevate retainer · October'], reminders: [{ date: '2026-10-07', kind: 'Automatic (GHL)' }] }),
  inv({ id: 'DUB-0918', clientId: 'harbor', engagement: 'Elevate', source: 'Dubsado', basis: 'Reported', issued: '2026-09-19', due: '2026-09-19', amount: 2500, paid: 2500, agreementId: 'ag-harbor-e', lines: ['Elevate · first month'], payments: [{ date: '2026-09-19', amount: 2500, note: 'Dubsado payment alert (notification time)' }], evidence: 'Dubsado alert: "Elise Bennett paid 2,500.00 USD for Elevate · Harbor House"' }),
  inv({ id: 'GHL-2001', clientId: 'harbor', engagement: 'LeadLock', source: 'GHL', basis: 'Reconciled', issued: '2026-09-19', due: '2026-09-19', amount: 1697, paid: 1697, agreementId: 'ag-harbor-l', lines: ['LeadLock setup'], payments: [{ date: '2026-09-19', amount: 1697, note: 'GHL checkout' }] }),
  inv({ id: 'GHL-2050', clientId: 'harbor', engagement: 'LeadLock', source: 'GHL', basis: 'Reconciled', issued: '2026-10-14', due: '2026-10-21', amount: 147, paid: 0, agreementId: 'ag-harbor-l', lines: ['LeadLock subscription · first month'] }),
  inv({ id: 'DUB-0710', clientId: 'willow', engagement: 'Meta Ads Accelerator', source: 'Dubsado', basis: 'Reported', issued: '2026-07-10', due: '2026-07-10', amount: 566, paid: 566, instalment: { n: 1, of: 3 }, agreementId: 'ag-willow', lines: ['Meta Ads Accelerator · instalment 1 of 3'], payments: [{ date: '2026-07-10', amount: 566, note: 'Dubsado payment alert' }] }),
  inv({ id: 'GHL-1902', clientId: 'willow', engagement: 'Meta Ads Accelerator', source: 'GHL', basis: 'Reconciled', issued: '2026-08-03', due: '2026-08-10', amount: 566, paid: 566, instalment: { n: 2, of: 3 }, agreementId: 'ag-willow', lines: ['Meta Ads Accelerator · instalment 2 of 3'], payments: [{ date: '2026-08-10', amount: 566, note: 'Card · automatic' }] }),
  inv({ id: 'GHL-2044', clientId: 'willow', engagement: 'Meta Ads Accelerator', source: 'GHL', basis: 'Reconciled', issued: '2026-10-03', due: '2026-10-10', amount: 565, paid: 0, instalment: { n: 3, of: 3 }, agreementId: 'ag-willow', lines: ['Meta Ads Accelerator · instalment 3 of 3'] }),
  inv({ id: 'DUB-0529', clientId: 'magnolia', engagement: 'Google Search Accelerator', source: 'Dubsado', basis: 'Unknown', issued: '2026-05-29', due: '2026-05-29', amount: 1997, paid: 1997, agreementId: 'ag-magnolia', lines: ['Google Search Accelerator · paid in full'], payments: [{ date: '2026-05-29', amount: 1997, note: 'Dubsado payment alert' }], evidence: 'Dubsado alert read; linked invoice page not readable' }),
];

export const PLANS: BillingPlan[] = [
  { clientId: 'bloom', engagement: 'Elevate', plan: 'Monthly retainer', amount: 2500, interval: 'Monthly', source: 'GHL', nextInvoice: '2026-11-01' },
  { clientId: 'rosewood', engagement: 'Elevate', plan: 'Monthly retainer', amount: 2500, interval: 'Monthly', source: 'GHL', nextInvoice: '2026-11-01' },
  { clientId: 'rosewood', engagement: 'LeadLock', plan: 'Subscription after setup', amount: 147, interval: 'Monthly', source: 'GHL', nextInvoice: '2026-11-01' },
  { clientId: 'everly', engagement: 'Elevate', plan: 'Monthly retainer · renews 18 Nov at $2,400', amount: 2200, interval: 'Monthly', source: 'GHL', nextInvoice: '2026-11-01' },
  { clientId: 'harbor', engagement: 'Elevate', plan: 'Monthly retainer (first month paid in Dubsado)', amount: 2500, interval: 'Monthly', source: 'GHL', missing: 'October retainer expected by 1 Oct. No GHL invoice found.', expectedDate: '2026-10-01' },
  { clientId: 'harbor', engagement: 'LeadLock', plan: 'Setup paid + subscription', amount: 147, interval: 'Monthly', source: 'GHL', nextInvoice: '2026-11-21' },
  { clientId: 'willow', engagement: 'Meta Ads Accelerator', plan: 'Three instalments', amount: 1697, interval: 'Instalments', source: 'GHL', instalments: { paid: 2, of: 3 } },
  { clientId: 'magnolia', engagement: 'Google Search Accelerator', plan: 'Paid in full', amount: 1997, interval: 'One-off', source: 'Dubsado', instalments: { paid: 1, of: 1 } },
];

export const UNMATCHED: Unmatched[] = [
  { id: 'u1', date: '2026-10-08', text: 'Dubsado: "Jordan has signed your contract for GSA - Lakeside 0417"', reason: 'Project label isn’t mapped to a client' },
  { id: 'u2', date: '2026-10-08', text: 'Dubsado: "Jordan Reyes paid 1,400.00 USD for GSA - Lakeside 0417"', reason: 'Same unmapped project; likely a new Google Accelerator client', amount: 1400 },
  { id: 'u3', date: '2026-10-04', text: 'Dubsado payment reminder sent to support@ (internal address)', reason: 'Sent to an internal address; probably a test' },
];

/** Failed card/bank payments (live GHL data only; the sample has none). */
export interface FailedPayment { id: string; clientId: string; invoiceId?: string; date: string; amount: number; source: string; resolved: boolean }
export const FAILED_PAYMENTS: FailedPayment[] = [];
/** Clients shown on the finance tabs. Empty means "use the sample CLIENTS". */
export const FINANCE_CLIENTS: Client[] = [];
/** Set by the local live export (financeLive.ts); the shared build keeps the sample. */
export const FINANCE_META = { live: false, generatedAt: '', syncedAt: '', dubsadoSyncedAt: '' };

export type InvoiceStatus = 'Paid' | 'Partially paid' | 'Overdue' | 'Due soon' | 'Open' | 'Payment reported' | 'Status unavailable';
export function invoiceStatus(i: Invoice2): InvoiceStatus {
  if (i.basis !== 'Reconciled') return i.paid > 0 ? 'Payment reported' : 'Status unavailable';
  if (i.paid >= i.amount) return 'Paid';
  if (i.paid > 0) return 'Partially paid';
  if (i.due < financeToday) return 'Overdue';
  if (i.due <= addDays(financeToday, 7)) return 'Due soon';
  return 'Open';
}
export const usd = (n: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
