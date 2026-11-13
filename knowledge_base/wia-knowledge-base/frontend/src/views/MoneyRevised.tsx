import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, AlertTriangle, ArrowRight, ArrowUpRight, CalendarClock, CalendarDays, ChevronRight, Clock3, FileSignature, FileText, History, Inbox, Info, Link2, Lock, Mail, ReceiptText, RefreshCw, Send, ShieldCheck, Sparkles, UserPlus } from 'lucide-react';
import { CLIENTS, clientById, dateLabel, daysBetween } from '../data';
import { AGREEMENTS, FAILED_PAYMENTS, FINANCE_ADMINS, FINANCE_CLIENTS, FINANCE_META, INVOICES2, PLANS, UNMATCHED, finDaysSince, finToday, invoiceStatus, usd, type Agreement, type Invoice2, type InvoiceStatus } from '../finance';
import { ThemedSelect } from '../components/ThemedSelect';
import { Avatar, Badge, Dialog, Empty, SearchField } from '../components/UI';
import { ActivityFeed, BasisBadge, activity, ChaseDialog, InvoiceDetails, InvoiceDrawer, InvoiceTable, STATUS_TONE, chasedBy, useChases } from './Money';
import type { Client, WorkspaceProps } from '../types';
import './MoneyRevised.css';

/*
 * Invoices & Contracts v2: v1's five sub-views condensed to three, one concern each.
 *   Today                — action: overdue chases, missing invoices, new deals, renewals, unmatched alerts (v1 Overview + Coming up).
 *   Invoices             — evidence and history: the ledger with trust badges, and the timeline of the same events (v1 Invoices + Activity).
 *   Clients & contracts  — terms and expectation: what each client signed and how they're billed (v1 Agreements + Billing plans).
 */

// A function: the live loader runs after this module is evaluated.
const financeSources = () => FINANCE_META.live ? [{ source: 'GHL invoices & payments', at: FINANCE_META.syncedAt, failed: '' }, ...(FINANCE_META.dubsadoSyncedAt ? [{ source: 'Gmail · Dubsado alerts', at: FINANCE_META.dubsadoSyncedAt, failed: '' }] : [])] : [{ source: 'GHL invoices & payments', at: '9:42 AM', failed: '' }, { source: 'Gmail · Dubsado alerts', at: '9:38 AM', failed: '' }];
const financeClients = () => FINANCE_CLIENTS.length ? FINANCE_CLIENTS : CLIENTS;
const RENEWAL_WINDOW = 60;
const fullDate = (d: string) => dateLabel(d, { day: 'numeric', month: 'short', year: 'numeric' });
const open = (i: Invoice2) => i.basis === 'Reconciled' && i.paid < i.amount;

type Standing = { label: string; tone: 'late' | 'warn' | 'ok' | 'muted'; detail: string };
const STANDING_ORDER: Record<Standing['tone'], number> = { late: 0, warn: 1, muted: 2, ok: 3 };
type ClientRow = { contractLink?: string; past: boolean; lastService: string; lastBilled: string; client: Client; plans: typeof PLANS; agreements: Agreement[]; invoices: Invoice2[]; standing: Standing; next: string; contract: string; contractTone: '' | 'warn' };

function buildRow(client: Client): ClientRow | null {
  const agreements = AGREEMENTS.filter(a => a.clientId === client.id);
  const plans = PLANS.filter(p => p.clientId === client.id);
  const invoices = INVOICES2.filter(i => i.clientId === client.id).sort((a, b) => b.due.localeCompare(a.due));
  if (!agreements.length && !plans.length && !invoices.length) return null;
  const overdue = invoices.filter(i => invoiceStatus(i) === 'Overdue');
  const missing = plans.filter(p => p.missing);
  const soon = invoices.filter(i => ['Due soon', 'Open'].includes(invoiceStatus(i))).sort((a, b) => a.due.localeCompare(b.due));
  const unreconciled = invoices.length > 0 && invoices.every(i => i.basis !== 'Reconciled');
  const standing: Standing = overdue.length ? { label: `${usd(overdue.reduce((s, i) => s + i.amount - i.paid, 0))} overdue`, tone: 'late', detail: `${finDaysSince(overdue[overdue.length - 1].due)} days · ${overdue.length} invoice${overdue.length > 1 ? 's' : ''}` }
    : missing.length ? { label: 'Invoice not issued', tone: 'warn', detail: missing[0].missing! }
    : !plans.length && !agreements.some(a => a.signed && finDaysSince(a.signed) <= 180) ? { label: 'No active plan', tone: 'muted', detail: (() => { const last = invoices.flatMap(i => i.payments).sort((a, b) => b.date.localeCompare(a.date))[0]; return last ? `Last paid ${dateLabel(last.date)} · ${usd(last.amount)}` : 'No payments recorded'; })() }
    : unreconciled ? { label: 'Paid (reported)', tone: 'muted', detail: 'From Dubsado alerts only; ledger not readable' }
    : { label: 'Up to date', tone: 'ok', detail: (() => { const last = invoices.flatMap(i => i.payments).sort((a, b) => b.date.localeCompare(a.date))[0]; return last ? `Last paid ${dateLabel(last.date)} · ${usd(last.amount)}` : 'No payments yet'; })() };
  const nextPlan = plans.filter(p => p.nextInvoice).sort((a, b) => a.nextInvoice!.localeCompare(b.nextInvoice!))[0];
  const instal = plans.find(p => p.instalments && p.instalments.paid < p.instalments.of);
  const next = soon[0] ? `${usd(soon[0].amount)} due ${dateLabel(soon[0].due)}` : instal ? `Instalment ${instal.instalments!.paid + 1} of ${instal.instalments!.of}` : nextPlan ? `Issues ${dateLabel(nextPlan.nextInvoice!)}` : plans.length && plans.every(p => p.interval === 'One-off') ? 'Paid in full' : '—';
  const renewal = agreements.find(a => a.status === 'Signed' && a.terms && a.terms.start > finToday());
  const active = agreements.filter(a => a.status === 'Active' || a.status === 'Superseded');
  const ending = active.find(a => a.terms?.end && daysBetween(finToday(), a.terms.end) <= RENEWAL_WINDOW);
  const unread = active.find(a => !a.terms);
  const linked = [...agreements].filter(a => a.link).sort((x, y) => (y.signed ?? '').localeCompare(x.signed ?? ''))[0];
  const contract = !agreements.length ? 'Terms not connected' : renewal ? `Renewed · ${renewal.terms!.fee} from ${dateLabel(renewal.terms!.start)}` : ending ? `Ends ${dateLabel(ending.terms!.end!)}` : unread && linked ? `Signed ${dateLabel(linked.signed!, { day: 'numeric', month: 'short', year: 'numeric' })}` : unread ? 'Terms not read yet' : active[0]?.terms?.notice ? `Rolling · ${active[0].terms.notice}` : 'Active';
  const recentlySigned = agreements.some(a => a.signed && finDaysSince(a.signed) <= 180);
  const past = !plans.length && !recentlySigned && !overdue.length && !soon.length;
  return { contractLink: linked?.link, past, lastService: invoices[0]?.engagement ?? '', lastBilled: invoices[0]?.issued ?? '', client, plans, agreements, invoices, standing, next, contract, contractTone: !agreements.length || (ending && !renewal) || (unread && !linked) ? 'warn' : '' };
}

type Tab = 'today' | 'ledger' | 'clients';
const TABS: { id: Tab; label: string; question: string }[] = [
  { id: 'today', label: 'Overview', question: 'What needs doing now: chases, missing invoices, new deals, renewals.' },
  { id: 'clients', label: 'Clients & contracts', question: 'What each client signed, how they are billed, and where they stand.' },
  { id: 'ledger', label: 'Invoices', question: 'What is owed and how sure we are, and every payment, reminder and chase in order.' },
];
const PAGE_SIZE = 20;
const UNMATCHED_PREVIEW = 4;
const STATUSES: InvoiceStatus[] = ['Overdue', 'Due soon', 'Open', 'Partially paid', 'Paid', 'Payment reported', 'Status unavailable'];

export default function MoneyRevised(props: WorkspaceProps & { clientId?: string }) {
  const log = useChases();
  const [tab, setTab] = useState<Tab>(props.clientId ? 'clients' : 'today');
  const [ledgerView, setLedgerView] = useState<'invoices' | 'timeline'>('invoices');
  const [status, setStatus] = useState('all');
  const [client, setClient] = useState(props.clientId || 'all');
  useEffect(() => { setClient(props.clientId || 'all'); }, [props.clientId]);
  const [source, setSource] = useState('all');
  const [kind, setKind] = useState('all');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [clientScope, setClientScope] = useState<'current' | 'past'>('current');
  const [nudge, setNudge] = useState(true);
  const [done, setDone] = useState<Set<string>>(new Set());
  const [clientModal, setClientModal] = useState<string | null>(null);
  const [invoice, setInvoice] = useState<Invoice2 | null>(null);
  const [chase, setChase] = useState<Invoice2 | null>(null);
  const [allUnmatched, setAllUnmatched] = useState(false);
  useEffect(() => setPage(1), [status, client, source, query, tab, ledgerView]);
  const resolve = (id: string, message: string) => { setDone(s => new Set(s).add(id)); props.notify(message); };

  const inScope = (id: string) => client === 'all' || id === client;
  const scopedInvoices = INVOICES2.filter(item => inScope(item.clientId));
  const scopedPlans = PLANS.filter(item => inScope(item.clientId));
  const scopedAgreements = AGREEMENTS.filter(item => inScope(item.clientId));
  const scopedFailed = FAILED_PAYMENTS.filter(item => inScope(item.clientId));
  const scopedUnmatched = client === 'all' ? UNMATCHED : [];
  const scopedLog = log.filter(item => client === 'all' || scopedInvoices.some(invoice => invoice.id === item.invoiceId));
  const clientOptions = [...financeClients(), ...CLIENTS.filter(item => !financeClients().some(other => other.id === item.id))];
  const selectClient = (id: string) => { setClient(id); window.location.hash = id === 'all' ? 'money' : `money/${id}`; };
  const allRows = useMemo(() => financeClients().map(buildRow).filter((r): r is ClientRow => !!r).sort((a, b) => STANDING_ORDER[a.standing.tone] - STANDING_ORDER[b.standing.tone] || a.client.name.localeCompare(b.client.name)), []);
  const rows = allRows.filter(row => inScope(row.client.id));
  const failed = scopedFailed.filter(f => !f.resolved && !done.has(`fp-${f.id}`));
  const overdue = scopedInvoices.filter(i => invoiceStatus(i) === 'Overdue');
  const dueSoon = scopedInvoices.filter(i => invoiceStatus(i) === 'Due soon').sort((a, b) => a.due.localeCompare(b.due));
  const missing = scopedPlans.filter(p => p.missing);
  const outstanding = scopedInvoices.filter(open);
  const unreconciled = scopedInvoices.filter(i => i.basis !== 'Reconciled').length;

  const toLedger = (s: string) => { setTab('ledger'); setLedgerView('invoices'); setStatus(s); setSource('all'); setQuery(''); };

  const needle = query.trim().toLowerCase();
  const pastCount = rows.filter(r => r.past).length;
  const shownRows = rows.filter(r => client !== 'all' || !pastCount || (clientScope === 'past') === r.past).filter(r => !needle || `${r.client.name} ${r.plans.map(p => p.engagement).join(' ')}`.toLowerCase().includes(needle));
  const shownInvoices = scopedInvoices.filter(i => (status === 'all' || invoiceStatus(i) === status) && (client === 'all' || i.clientId === client) && (source === 'all' || i.source === source) && (!needle || `${i.id} ${clientById(i.clientId).name} ${i.engagement}`.toLowerCase().includes(needle))).sort((a, b) => b.due.localeCompare(a.due));
  const pageCount = Math.max(1, Math.ceil(shownInvoices.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pageInvoices = shownInvoices.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  const selected = rows.find(r => r.client.id === clientModal);
  const nudgeText = `${overdue.length} invoice${overdue.length === 1 ? '' : 's'} overdue (${usd(overdue.reduce((s, i) => s + i.amount - i.paid, 0))})${missing.length ? ` · ${missing.length} expected invoice missing` : ''} · ${dueSoon.length} due this week`;

  // ---- Overview: tiles, what needs attention, what's new, what's unmatched, what just happened ----
  const month = finToday().slice(0, 7);
  const paidMonth = scopedInvoices.filter(i => i.basis === 'Reconciled').flatMap(i => i.payments).filter(p => p.date.startsWith(month));
  const signedMonth = scopedAgreements.filter(a => a.signed?.startsWith(month));
  const chasesMonth = scopedInvoices.flatMap(i => i.reminders.filter(r => r.kind.startsWith('Personal') && r.date.startsWith(month))).length + scopedLog.length;
  const unmatched = scopedUnmatched.filter(u => !done.has(`un-${u.id}`));
  const newThisWeek = scopedAgreements.filter(a => a.signed && finDaysSince(a.signed) <= 7);
  const renewals = scopedAgreements.filter(a => a.status === 'Active' && a.terms?.end && daysBetween(finToday(), a.terms.end) <= RENEWAL_WINDOW && !scopedAgreements.some(b => b.clientId === a.clientId && b.status === 'Signed' && b.terms && b.terms.start > finToday()));
  const recent = activity(log, client === 'all' ? undefined : client).filter(e => e.date <= finToday()).slice(0, 3);
  const toTimeline = (k: string) => { setTab('ledger'); setLedgerView('timeline'); setKind(k); };
  const usDate = (d: string) => dateLabel(d, { month: 'short', day: 'numeric', year: 'numeric' });
  const tiles = [
    { id: 'overdue', label: 'Overdue', value: String(overdue.length).padStart(2, '0'), detail: usd(overdue.reduce((s, i) => s + i.amount - i.paid, 0)), icon: AlertTriangle, tone: 'late', act: () => toLedger('Overdue') },
    { id: 'soon', label: 'Due in 7 days', value: String(dueSoon.length).padStart(2, '0'), detail: usd(dueSoon.reduce((s, i) => s + i.amount - i.paid, 0)), icon: CalendarDays, tone: '', act: () => toLedger('Due soon') },
    { id: 'paid', label: 'Paid this month', value: usd(paidMonth.reduce((s, p) => s + p.amount, 0)), detail: `${paidMonth.length} reconciled payments`, icon: RefreshCw, tone: '', act: () => toTimeline('Payment') },
    FINANCE_META.live
      ? { id: 'failed', label: 'Failed payments', value: String(failed.length).padStart(2, '0'), detail: `Unresolved · ${scopedFailed.length} failed in total`, icon: AlertTriangle, tone: failed.length ? 'late' : '', act: () => toTimeline('Failed payment') }
      : { id: 'signed', label: 'Signed this month', value: String(signedMonth.length).padStart(2, '0'), detail: `${signedMonth.length} new agreement${signedMonth.length === 1 ? '' : 's'}`, icon: FileText, tone: '', act: () => setTab('clients') },
    { id: 'chases', label: 'Chases this month', value: String(chasesMonth).padStart(2, '0'), detail: 'Personal emails sent', icon: Send, tone: '', act: () => toTimeline('Chase') },
    FINANCE_META.live
      ? { id: 'recurring', label: 'Recurring plans', value: String(scopedPlans.filter(p => !p.plan.includes('starts')).length).padStart(2, '0'), detail: `${usd(scopedPlans.filter(p => !p.plan.includes('starts')).reduce((t, p) => t + p.amount, 0))}/month · ${scopedPlans.filter(p => !p.plan.includes('starts') && p.plan.includes('auto-pay')).length} on auto-pay`, icon: RefreshCw, tone: '', act: () => { setTab('clients'); setClientScope('current'); } }
      : { id: 'unmatched', label: 'Unmatched', value: String(unmatched.length).padStart(2, '0'), detail: 'Needs review', icon: AlertTriangle, tone: unmatched.length ? 'warn' : '', act: () => document.getElementById('fv-unmatched')?.scrollIntoView({ behavior: 'smooth', block: 'center' }) },
  ];

  const today = <>
    <section className="fo-tiles" aria-label="Money summary">{tiles.map(t => <button key={t.id} className={`fo-tile tone-${t.tone || 'plain'}`} onClick={t.act}>
      <span className="fo-tile-label"><t.icon size={15} />{t.label}</span>
      <strong>{t.value}</strong>
      <small>{t.detail}</small>
      <ChevronRight size={15} className="fo-tile-chev" />
    </button>)}</section>

    <div className="fo-grid">
      <section className="panel fo-attention" aria-labelledby="fo-att">
        <header className="fo-panel-head"><h2 id="fo-att"><AlertCircle size={20} className="fo-head-icon late" />Needs attention</h2><button className="text-button" onClick={() => toLedger('all')}>View all invoices<ArrowRight size={12} /></button></header>

        {overdue.filter(i => !done.has(`od-${i.id}`)).map(i => { const c = clientById(i.clientId); const ch = chasedBy(i, log); return <div className="fo-alert tone-late" key={i.id}>
          <div className="fo-row">
            <Avatar client={c} small />
            <span className="fo-who"><strong>{c.name}</strong><small>{i.source} · {i.lines[0].replace(' · ', ' · ')}</small></span>
            <span className="fo-when"><span>{usDate(i.due)}</span><small>Invoice {i.id}</small></span>
            <span className="fo-amount"><strong>{usd(i.amount - i.paid)}</strong><span className="fo-chip late">{finDaysSince(i.due)} days overdue</span></span>
            <BasisBadge basis={i.basis} />
            <button className="button button-small button-primary" onClick={() => setChase(i)}><Mail size={13} />Prepare chase</button>
          </div>
          <p className="fo-note"><Info size={13} />This prepares a draft for you to review. It does not send an email. {ch ? `Last chased ${dateLabel(ch.date)} by ${ch.by}.` : `${i.reminders.filter(r => r.kind.startsWith('Auto')).length} automatic GHL reminders so far; not chased personally yet.`}</p>
        </div>; })}

        {failed.map(f => { const c = clientById(f.clientId); const inv = scopedInvoices.find(i => i.id === f.invoiceId); return <div className="fo-alert tone-late" key={f.id}>
          <div className="fo-row">
            {c ? <Avatar client={c} small /> : <span />}
            <span className="fo-who"><strong>{c?.name ?? 'Unknown contact'}</strong><small>GHL · Stripe · {f.source}</small></span>
            <span className="fo-when"><span>{usDate(f.date)}</span><small>{f.invoiceId ? `Invoice ${f.invoiceId}` : 'No invoice linked'}</small></span>
            <span className="fo-amount"><strong>{usd(f.amount)}</strong><span className="fo-chip late">Payment failed</span></span>
            <span />
            <span className="fo-cta">{inv && <button className="button button-small button-primary" onClick={() => setInvoice(inv)}>Open invoice</button>}<button className="text-button" onClick={() => resolve(`fp-${f.id}`, 'Noted. It reappears if the invoice is still unpaid after the next sync.')}>Dismiss</button></span>
          </div>
          <p className="fo-note"><Info size={13} />The card or bank payment was declined. The invoice stays unpaid until the client updates payment details or pays another way.</p>
        </div>; })}

        {missing.filter(p => !done.has(`mi-${p.clientId}-${p.engagement}`)).map(p => { const c = clientById(p.clientId); const id = `mi-${p.clientId}-${p.engagement}`; return <div className="fo-alert tone-warn" key={id}>
          <div className="fo-row">
            <Avatar client={c} small />
            <span className="fo-who"><strong>{c.name}</strong><small>{p.source} · {p.engagement}{p.expectedDate ? ` · ${new Intl.DateTimeFormat('en-US', { month: 'long' }).format(new Date(`${p.expectedDate}T12:00:00Z`))}` : ''}</small></span>
            <span className="fo-when"><span>Expected {p.expectedDate ? usDate(p.expectedDate) : '—'}</span><small>No invoice found</small></span>
            <span className="fo-amount"><strong>{usd(p.amount)}</strong><span className="fo-chip warn">Not invoiced</span></span>
            <span />
            <span className="fo-cta"><button className="button button-small button-primary" onClick={() => resolve(id, 'Noted: invoice issued in GHL. It will show here after the next sync.')}>Mark issued</button><button className="text-button" onClick={() => resolve(id, 'Marked as not due this month. The reason is recorded.')}>Not due</button></span>
          </div>
        </div>; })}

        {dueSoon.length > 0 && <><h3 className="fo-sub"><Clock3 size={16} />Due soon</h3>
          <ul className="fo-list">{dueSoon.map(i => { const c = clientById(i.clientId); return <li key={i.id}><button className="fo-row" onClick={() => setInvoice(i)}>
            <Avatar client={c} small />
            <span className="fo-who"><strong>{c.name}</strong><small>{i.source}{i.instalment ? ` · instalment ${i.instalment.n} of ${i.instalment.of}` : ''}</small></span>
            <span className="fo-when"><span>{usDate(i.due)}</span><small>Invoice {i.id}</small></span>
            <span className="fo-amount"><strong>{usd(i.amount - i.paid)}</strong></span>
            <BasisBadge basis={i.basis} />
            <ChevronRight size={16} className="rb-chev" />
          </button></li>; })}</ul></>}

        {renewals.filter(a => !done.has(`rn-${a.id}`)).length > 0 && <><h3 className="fo-sub"><CalendarClock size={16} />Ending soon</h3>
          <ul className="fo-list">{renewals.filter(a => !done.has(`rn-${a.id}`)).map(a => { const c = clientById(a.clientId); return <li key={a.id}><button className="fo-row" onClick={() => setClientModal(c.id)}>
            <Avatar client={c} small />
            <span className="fo-who"><strong>{c.name}</strong><small>{a.engagements[0]} · {a.source}</small></span>
            <span className="fo-when"><span>Ends {usDate(a.terms!.end!)}</span><small>{daysBetween(finToday(), a.terms!.end!)} days left · paid in full</small></span>
            <span className="fo-amount"><span className="fo-chip info">No renewal yet</span></span>
            <span />
            <ChevronRight size={16} className="rb-chev" />
          </button></li>; })}</ul></>}

        <footer className="fo-attention-foot"><label className="fv-nudge" title={nudge ? `Tomorrow 9:00 AM: “${nudgeText}”` : 'Paused'}><input type="checkbox" checked={nudge} onChange={e => { setNudge(e.target.checked); props.notify(e.target.checked ? 'Daily overdue nudge on: Slack DM to Whitney and Gisselle at 9:00 AM.' : 'Daily overdue nudge paused.'); }} /><span>Daily overdue nudge to admins · {nudge ? 'On' : 'Off'}</span></label></footer>
      </section>

      <div className="fo-side">
        <section className="panel fo-new" aria-labelledby="fo-new">
          <header className="fo-panel-head"><h2 id="fo-new"><Sparkles size={18} className="fo-head-icon" />New this week</h2></header>
          <ul className="fo-side-list">
            {newThisWeek.map(a => { const c = clientById(a.clientId); const renewal = a.terms && a.terms.start > finToday(); return <li key={a.id}><Avatar client={c} small /><span className="fo-who"><strong>{c.name}</strong><small>{renewal ? `Renewal signed · ${a.terms!.fee} from ${dateLabel(a.terms!.start)}` : `Agreement signed · first payment expected`}</small><small>{usDate(a.signed!)}</small></span><button className="text-button" onClick={() => setClientModal(c.id)}>Open terms<ArrowRight size={12} /></button></li>; })}
            {client === 'all' && !FINANCE_META.live && !done.has('deal-lakeside') && <li><span className="client-avatar small fo-new-avatar" aria-hidden="true">GL</span><span className="fo-who"><strong>GSA - Lakeside 0417</strong><small>Signed · paid $1,400 · no client record yet</small><small>{usDate('2026-10-08')}</small></span><button className="text-button" onClick={() => resolve('deal-lakeside', 'In the real app this opens onboarding with the Dubsado details filled in.')}>Start onboarding<ArrowRight size={12} /></button></li>}
          </ul>
        </section>

        <section className="panel fo-unmatched" id="fv-unmatched" aria-labelledby="fo-un">
          <header className="fo-panel-head"><h2 id="fo-un"><AlertCircle size={18} className="fo-head-icon warn" />Unmatched<span className="fo-count">· {unmatched.length} to review</span></h2><span className="fo-admin">ADMIN ONLY</span></header>
          {unmatched.length ? <ul className="fo-side-list">{unmatched.slice(0, UNMATCHED_PREVIEW).map(u => <UnmatchedItem key={u.id} u={u} resolve={text => resolve(`un-${u.id}`, text)} />)}</ul> : <p className="hint">Everything is matched.</p>}
          {unmatched.length > UNMATCHED_PREVIEW && <button className="text-button fo-view-more" onClick={() => setAllUnmatched(true)}>View all {unmatched.length} unmatched<ArrowRight size={12} /></button>}
          <p className="fo-fine">Only reconciled invoice and payment records count toward totals; reported alerts are never treated as overdue.</p>
        </section>
      </div>
    </div>

    <section className="panel fo-recent" aria-labelledby="fo-recent">
      <h2 id="fo-recent" className="fo-recent-title"><History size={16} />Recent activity</h2>
      <ul>{recent.map((e, n) => <li key={n}><span className="fo-recent-icon"><Link2 size={13} /></span><div><small>{usDate(e.date)} · {e.kind} · {clientById(e.clientId).name}</small><p>{e.text}</p><span className="fo-source">Source: <b>{e.source}</b></span></div></li>)}</ul>
      <button className="text-button" onClick={() => toTimeline('all')}>View all activity<ArrowRight size={12} /></button>
    </section>
  </>;

  const ledger = <>
    <div className="fv-toolbar">
      <div className="rb-layout" role="group" aria-label="Ledger view"><button className={ledgerView === 'invoices' ? 'selected' : ''} aria-pressed={ledgerView === 'invoices'} onClick={() => setLedgerView('invoices')}><ReceiptText size={13} />Invoices</button><button className={ledgerView === 'timeline' ? 'selected' : ''} aria-pressed={ledgerView === 'timeline'} onClick={() => setLedgerView('timeline')}><History size={13} />Timeline</button></div>
      {ledgerView === 'invoices' ? <div className="fv-filters">
        <ThemedSelect aria-label="Status" value={status} onChange={setStatus}><option value="all">All statuses</option>{STATUSES.map(s => <option key={s} value={s}>{s}</option>)}</ThemedSelect>
        <ThemedSelect aria-label="Source" value={source} onChange={setSource}><option value="all">GHL + Dubsado</option><option value="GHL">GHL</option><option value="Dubsado">Dubsado</option></ThemedSelect>
      </div> : <div className="fv-filters"><ThemedSelect aria-label="Event type" value={kind} onChange={setKind}><option value="all">All events</option>{['Proposal', 'Signed', 'Invoice', 'Reminder', 'Chase', 'Payment', 'Failed payment'].map(k => <option key={k} value={k}>{k}</option>)}</ThemedSelect></div>}
    </div>
    {ledgerView === 'invoices' ? <>
      <div className="panel fv-ledger"><InvoiceTable rows={pageInvoices} onOpen={setInvoice} onChase={setChase} /></div>
      {shownInvoices.length > PAGE_SIZE && <Pager page={currentPage} pages={pageCount} total={shownInvoices.length} onPage={n => { setPage(n); document.querySelector('.fv-tabbar')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }} />}
      <div className="fv-legend">{(['Reconciled', 'Reported', 'Unknown'] as const).map(b => <span key={b}><BasisBadge basis={b} />{b === 'Reconciled' ? 'From the invoice record itself' : b === 'Reported' ? 'From an alert email only; never shown as Open or Overdue' : 'Linked record not readable'}</span>)}</div>
      <p className="fv-total">Totals only count reconciled invoices: {usd(outstanding.reduce((s, i) => s + i.amount - i.paid, 0))} outstanding across {outstanding.length} invoices · {unreconciled} more not reconciled.</p>
    </> : <div className="panel fv-ledger fv-timeline"><ActivityFeed kind={kind} clientId={client === 'all' ? undefined : client} /><p className="hint">One event per payment, even when it arrived as several emails. The same events appear in each client’s History → Commercial lane.</p></div>}
  </>;

  const clients = <>
    <div className="rb-table-wrap"><table className="rb-table fv-table">
      <thead><tr><th>Client</th><th>Service</th><th>Standing</th><th>Next invoice</th><th>Contract</th><th><span className="sr-only">Open</span></th></tr></thead>
      <tbody>{shownRows.map(r => <tr key={r.client.id} onClick={() => setClientModal(r.client.id)}>
        <td><span className="rb-person"><Avatar client={r.client} small /><span><button className="rb-link" onClick={e => { e.stopPropagation(); setClientModal(r.client.id); }}>{r.client.name}</button><small>{r.client.contact}</small></span></span></td>
        <td>{!r.plans.length && r.lastService && <span className="fv-plan"><strong>{r.lastService}</strong><small>Last billed {dateLabel(r.lastBilled, { day: 'numeric', month: 'short', year: 'numeric' })}</small></span>}{r.plans.map(p => <span className="fv-plan" key={p.engagement}><strong>{p.engagement}</strong><small>{p.interval === 'Monthly' ? `${usd(p.amount)}/mo` : p.interval === 'One-off' ? `${usd(p.amount)} one-off` : `${usd(p.amount)} · ${p.instalments ? `${p.instalments.paid} of ${p.instalments.of} paid` : p.interval.toLowerCase()}`}</small></span>)}</td>
        <td><span className={`fv-standing tone-${r.standing.tone}`}>{r.standing.label}</span><small className="fv-sub">{r.standing.detail}</small></td>
        <td className="fv-nowrap">{r.next}</td>
        <td><span className={r.contractTone === 'warn' ? 'fv-warn' : ''}>{r.contract}</span>{r.contractLink && <a className="fv-contract-link" href={r.contractLink} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}>View contract<ArrowUpRight size={11} /></a>}<small className="fv-sub">{r.agreements.filter(a => a.status !== 'Superseded' && a.status !== 'Ended').length} agreement{r.agreements.filter(a => a.status !== 'Superseded' && a.status !== 'Ended').length === 1 ? '' : 's'}</small></td>
        <td><ChevronRight size={15} className="rb-chev" /></td>
      </tr>)}</tbody>
    </table>{!shownRows.length && <Empty title="No matching clients" />}</div>
  </>;

  const counts: Record<Tab, number> = { today: failed.length + overdue.filter(i => !done.has(`od-${i.id}`)).length + missing.filter(p => !done.has(`mi-${p.clientId}-${p.engagement}`)).length + dueSoon.length + renewals.length + unmatched.length, ledger: scopedInvoices.length, clients: rows.length };
  return <div className="view fv-view">
    {FINANCE_META.live && <p className="fv-live-banner"><Lock size={13} /><strong>Local build · real WIA billing data from GHL</strong> (pulled {FINANCE_META.syncedAt}){FINANCE_META.dubsadoSyncedAt ? ' plus Dubsado alerts from hello@' : ''}. Do not share, publish or attach this file. {FINANCE_META.dubsadoSyncedAt ? 'Dubsado payments are reported from alert emails; contract terms are not read.' : 'Dubsado signing and contract terms are not connected here.'}</p>}
    <header className="fv-head fo-head">
      <div>
        <p className="rb-eyebrow">Admin only · Stage 3</p>
        <h1>Invoices &amp; Contracts</h1>
        <p className="fv-lede fo-lede">A trusted view of what clients agreed to pay, what has been paid, and what needs attention.<span className="fo-visible"><Lock size={11} />Visible to {FINANCE_ADMINS.join(' & ')}</span></p>
        <p className="fo-sync"><RefreshCw size={12} />{financeSources().map(f => `${f.source.startsWith('GHL') ? 'GHL invoices synced' : 'Dubsado alerts'} ${f.at}`).join(' · ')} · Read-only</p>
      </div>
      <ul className="fo-legend" aria-label="How far each record can be trusted">
        <li><i className="reconciled" />Reconciled = from invoice/payment record</li>
        <li><i className="reported" />Reported = alert only</li>
        <li><i className="unknown" />Unknown = record unreadable</li>
      </ul>
    </header>

    <div className="workspace-client-filter"><span className="small-label">Client</span><ThemedSelect aria-label="Finance client filter" value={client} onChange={selectClient}><option value="all">All clients</option>{clientOptions.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</ThemedSelect>{client !== 'all' && <button className="text-button" onClick={() => selectClient('all')}>Clear client filter</button>}</div>
    <div className="fv-tabbar">
      <nav className="fv-tabs" role="tablist" aria-label="Invoices & contracts sections">{TABS.map(t => <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? 'selected' : ''} onClick={() => { setTab(t.id); setQuery(''); }}>{t.label}<span>{counts[t.id]}</span></button>)}</nav>
      {tab === 'clients' && <div className="fv-tabbar-tools">{pastCount > 0 && <div className="rb-layout" role="group" aria-label="Which clients"><button className={clientScope === 'current' ? 'selected' : ''} aria-pressed={clientScope === 'current'} onClick={() => setClientScope('current')}>Current · {rows.length - pastCount}</button><button className={clientScope === 'past' ? 'selected' : ''} aria-pressed={clientScope === 'past'} onClick={() => setClientScope('past')}>Past · {pastCount}</button></div>}<SearchField label="Search clients" placeholder="Search clients…" value={query} onChange={setQuery} /></div>}
      {tab === 'ledger' && ledgerView === 'invoices' && <div className="fv-tabbar-tools"><SearchField label="Search invoices" placeholder="Invoice ID or client…" value={query} onChange={setQuery} /></div>}
    </div>

    {tab === 'today' ? today : tab === 'ledger' ? ledger : clients}

    <p className="fv-foot"><ShieldCheck size={13} />Visible to {FINANCE_ADMINS.join(' and ')} only. Dubsado covers signing and first payments; GHL is the ledger for ongoing invoices.</p>

    {selected && <ClientCommercialModal row={selected} close={() => setClientModal(null)} chase={setChase} openClient={props.openClient} />}
    {invoice && <InvoiceDrawer invoice={invoice} close={() => setInvoice(null)} onChase={setChase} />}
    {allUnmatched && <Dialog title={`Unmatched · ${unmatched.length} to review`} subtitle="Admin only" className="fo-unmatched-dialog" onClose={() => setAllUnmatched(false)}>
      <p className="hint">Alerts and payments the KB couldn’t tie to a client. Assign each one, or mark it as not a client event. They never go to the shared review queue.</p>
      {unmatched.length ? <ul className="fo-side-list fo-unmatched-all">{unmatched.map(u => <UnmatchedItem key={u.id} u={u} resolve={text => resolve(`un-${u.id}`, text)} />)}</ul> : <Empty title="Everything is matched" />}
    </Dialog>}
    {chase && <ChaseDialog invoice={chase} viewer={props.viewer} close={() => setChase(null)} notify={props.notify} />}
  </div>;
}

/** Everything about one client's money: what they signed, how they're billed, every invoice. */
function ClientCommercialModal({ row, close, chase, openClient }: { row: ClientRow; close: () => void; chase: (i: Invoice2) => void; openClient: (id: string) => void }) {
  const overdue = row.invoices.filter(i => invoiceStatus(i) === 'Overdue');
  const current = row.agreements.filter(a => a.status !== 'Superseded' && a.status !== 'Ended');
  const past = row.agreements.filter(a => a.status === 'Superseded' || a.status === 'Ended');
  const paid = row.invoices.filter(i => i.basis === 'Reconciled').reduce((sum, invoice) => sum + invoice.paid, 0);
  const unreconciled = row.invoices.filter(i => i.basis !== 'Reconciled').length;
  const chaseInvoice = (invoice: Invoice2) => { close(); chase(invoice); };
  return <Dialog title={row.client.name} subtitle="Commercial record" size="lg" className="finance-record-modal commercial-record-modal" onClose={close} meta={<span>{row.client.contact} · Agreements, billing & activity</span>} footer={<><button className="text-button" onClick={() => { close(); openClient(row.client.id); }}>Open full client record<ArrowRight size={12} /></button><button className="button button-outline" onClick={close}>Close</button></>}>
    <dl className="commercial-summary"><div><dt>Services</dt><dd>{row.plans.map(plan => plan.engagement).join(' + ') || row.lastService || 'Not recorded'}</dd></div><div><dt>Next invoice</dt><dd>{row.next}</dd></div><div><dt>Paid to date</dt><dd>{usd(paid)}</dd><small>{unreconciled ? `${unreconciled} invoice${unreconciled === 1 ? '' : 's'} not reconciled; excluded` : 'Reconciled payments'}</small></div></dl>
    {(row.standing.tone === 'late' || row.standing.tone === 'warn') && <section className={`commercial-standing tone-${row.standing.tone}`} aria-label="Commercial standing"><div><span className={`fv-standing tone-${row.standing.tone}`}>{row.standing.label}</span><p>{row.standing.detail}</p></div>{overdue.length > 0 && <div className="commercial-chases">{overdue.map(invoice => <button key={invoice.id} className="button button-small button-primary" onClick={() => chaseInvoice(invoice)}><Mail size={13} />Chase {invoice.id}…</button>)}</div>}</section>}
    <section className="commercial-section" aria-label="Billing plans"><header><h3>Billing</h3><span>{row.plans.length} plan{row.plans.length === 1 ? '' : 's'}</span></header>
      {row.plans.length ? row.plans.map(plan => {
        const parts = plan.plan.split(/\s*·\s*/);
        const renewal = parts.find(part => /^renews\b/i.test(part));
        const description = parts.filter(part => part !== renewal).join(' · ');
        return <div className="fv-plan-row" key={plan.engagement}><div><strong>{plan.engagement}</strong><p className="hint">{description} · {plan.source}</p></div><div className="fv-plan-right"><strong>{usd(plan.amount)}</strong>{renewal && <span className="fv-renewal-pill"><RefreshCw size={11} aria-hidden="true" /><span>{renewal.charAt(0).toUpperCase() + renewal.slice(1)}</span></span>}<small>{plan.interval}</small>{plan.instalments && <small>{plan.instalments.paid} of {plan.instalments.of} paid</small>}{plan.missing && <span className="fv-warn">Invoice not issued · {plan.missing}</span>}</div></div>;
      }) : <p className="hint">No current billing plan recorded.</p>}
    </section>
    <section className="commercial-section" aria-label="Agreements and terms"><header><h3>Agreements &amp; terms</h3><span>{current.length} current</span></header>
      {current.length ? current.map(agreement => <AgreementBlock key={agreement.id} a={agreement} />) : <p className="hint">No current agreement recorded.</p>}
      {past.length > 0 && <details className="fv-past"><summary>{past.length} earlier agreement{past.length === 1 ? '' : 's'}</summary>{past.map(agreement => <AgreementBlock key={agreement.id} a={agreement} />)}</details>}
    </section>
    <section className="commercial-section" aria-label="Client invoices"><header><div><h3>Invoices</h3><p>Expand an invoice for payments, reminders and source details.</p></div><span>{row.invoices.length} total</span></header>
      {row.invoices.length ? <div className="commercial-invoices">{row.invoices.map(invoice => { const status = invoiceStatus(invoice); return <details className="commercial-invoice" key={invoice.id}><summary><ChevronRight size={14} className="commercial-invoice-chevron" /><span className="commercial-invoice-name"><strong>{invoice.lines[0] || invoice.engagement}</strong><small>{invoice.id} · Due {fullDate(invoice.due)}</small></span><span className="commercial-invoice-amount">{usd(invoice.amount)}</span><span className="commercial-invoice-badges"><Badge tone={STATUS_TONE[status]} dot={false}>{status}</Badge><BasisBadge basis={invoice.basis} /></span></summary><div className="commercial-invoice-expanded"><InvoiceDetails invoice={invoice} onChase={chaseInvoice} showAgreement={false} /></div></details>; })}</div> : <p className="hint">No invoices matched to this client.</p>}
    </section>
    <section className="commercial-section" aria-label="Commercial activity"><header><h3>Activity</h3></header><ActivityFeed clientId={row.client.id} /></section>
  </Dialog>;
}

function AgreementBlock({ a }: { a: Agreement }) {
  const t = a.terms;
  return <div className="fv-agreement">
    <div className="fv-agreement-head"><FileSignature size={14} /><strong>{a.name}</strong><Badge tone={a.status === 'Active' ? 'green' : a.status === 'Signed' ? 'blue' : 'neutral'} dot={false}>{a.status}</Badge></div>
    <p className="hint">{a.signed ? `Signed ${fullDate(a.signed)} by ${a.signer}` : 'Not signed'} · {a.source}</p>
    {t ? <dl className="fv-terms"><div><dt>Fee</dt><dd>{t.fee}</dd></div><div><dt>Billing</dt><dd>{t.interval}</dd></div>{t.minTerm && <div><dt>Minimum term</dt><dd>{t.minTerm}</dd></div>}{t.end && <div><dt>Ends</dt><dd>{fullDate(t.end)}</dd></div>}{t.notice && <div><dt>Notice</dt><dd>{t.notice}</dd></div>}{t.adSpend && <div><dt>Ad spend</dt><dd>{t.adSpend}</dd></div>}<div className="fv-terms-wide"><dt>Included</dt><dd>{t.included.join(' · ')}</dd></div></dl>
      : a.link ? <p className="hint">Terms aren’t extracted into the KB yet. Open the signed contract to read them.</p> : <p className="fv-unread"><AlertTriangle size={12} />Terms not read yet. {a.termsNote}</p>}
    {a.link && <a className="fv-contract-link" href={a.link} target="_blank" rel="noopener noreferrer"><FileSignature size={12} />View contract in Dubsado<ArrowUpRight size={11} /></a>}
  </div>;
}

/** An alert the KB couldn't tie to a client: assign it, or mark it as not a client event. */
function UnmatchedItem({ u, resolve }: { u: (typeof UNMATCHED)[number]; resolve: (text: string) => void }) {
  const [assigning, setAssigning] = useState(false);
  const [pick, setPick] = useState(financeClients()[0].id);
  const internal = u.text.includes('internal');
  const title = internal ? 'Reminder sent to an internal address' : u.amount ? 'Dubsado payment — no client match' : 'Dubsado signing — no client match';
  return <li className="fo-un-item"><span className="fo-un-icon"><Link2 size={14} /></span>
    <span className="fo-who"><strong>{title}</strong><small>{u.text.replace(/^Dubsado: /, '')} · {dateLabel(u.date)}</small><small title={u.reason}>{u.reason}</small></span>
    {internal ? <button className="button button-small button-outline" onClick={() => resolve('Marked as not a client event.')}>Not a client event</button>
      : assigning ? <span className="fo-assign"><ThemedSelect aria-label="Client" value={pick} onChange={setPick}>{financeClients().map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</ThemedSelect><button className="button button-small button-primary" onClick={() => resolve(`Matched to ${clientById(pick).name}.`)}>Match</button></span>
      : <button className="button button-small button-outline" onClick={() => setAssigning(true)}>Assign client<ChevronRight size={13} /></button>}
  </li>;
}

/** Page numbers with gaps: first, last, and the pages around the current one (1 2 3 4 … 18). */
function pageList(page: number, pages: number): (number | '…')[] {
  if (pages <= 7) return Array.from({ length: pages }, (_, n) => n + 1);
  const keep = new Set([1, pages, page - 1, page, page + 1]);
  if (page <= 4) [2, 3, 4, 5].forEach(n => keep.add(n));
  if (page >= pages - 3) [pages - 4, pages - 3, pages - 2, pages - 1].forEach(n => keep.add(n));
  const list = [...keep].filter(n => n >= 1 && n <= pages).sort((a, b) => a - b);
  return list.flatMap((n, k) => k && n - list[k - 1] > 1 ? ['…' as const, n] : [n]);
}

function Pager({ page, pages, total, onPage }: { page: number; pages: number; total: number; onPage: (n: number) => void }) {
  const from = (page - 1) * PAGE_SIZE + 1, to = Math.min(page * PAGE_SIZE, total);
  return <nav className="fv-pager" aria-label="Invoice pages">
    <span className="fv-pager-count">Showing {from}–{to} of {total} invoices</span>
    <div className="fv-pager-pages">
      <button className="fv-pager-step" disabled={page === 1} onClick={() => onPage(page - 1)} aria-label="Previous page"><ChevronRight size={14} className="flip" />Previous</button>
      {pageList(page, pages).map((n, k) => n === '…' ? <span key={`gap-${k}`} className="fv-pager-gap">…</span> : <button key={n} className={n === page ? 'selected' : ''} aria-current={n === page ? 'page' : undefined} aria-label={`Page ${n}`} onClick={() => onPage(n)}>{n}</button>)}
      <button className="fv-pager-step" disabled={page === pages} onClick={() => onPage(page + 1)} aria-label="Next page">Next<ChevronRight size={14} /></button>
    </div>
  </nav>;
}
