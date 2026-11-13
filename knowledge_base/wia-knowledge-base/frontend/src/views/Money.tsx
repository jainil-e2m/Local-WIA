import { ThemedSelect } from '../components/ThemedSelect';
import { useState, useSyncExternalStore } from 'react';
import { AlertTriangle, ArrowRight, ArrowUpRight, Bell, CalendarClock, Check, Clipboard, Clock3, FileCheck2, FileSignature, Inbox, Lock, Mail, ReceiptText, RefreshCw, ShieldCheck, Wallet } from 'lucide-react';
import { CLIENTS, DEMO_DATE, addDays, clientById, dateLabel, daysBetween } from '../data';
import { AGREEMENTS, FAILED_PAYMENTS, FINANCE_ADMINS, INVOICES2, PLANS, UNMATCHED, finDaysSince, finToday, invoiceStatus, usd, type Agreement, type Invoice2, type InvoiceStatus } from '../finance';
import { Avatar, Badge, Dialog, Empty, PageHeading, Panel } from '../components/UI';
import type { Tone, WorkspaceProps } from '../types';
import './Money.css';
import { me } from '../auth';

// ---- Shared chase log (the global tab and client sub-tab show the same chases) ----
type Chase = { invoiceId: string; date: string; by: string; slackNote: boolean };
let chases: Chase[] = [];
const listeners = new Set<() => void>();
const chaseStore = { subscribe: (l: () => void) => { listeners.add(l); return () => listeners.delete(l); }, get: () => chases, add: (c: Chase) => { chases = [...chases, c]; listeners.forEach(l => l()); } };
export const useChases = () => useSyncExternalStore(chaseStore.subscribe, chaseStore.get, chaseStore.get);

export const STATUS_TONE: Record<InvoiceStatus, Tone> = { Paid: 'green', 'Partially paid': 'gold', Overdue: 'amber', 'Due soon': 'gold', Open: 'blue', 'Payment reported': 'neutral', 'Status unavailable': 'neutral' };
const BASIS_HINT = { Reconciled: 'Read from the invoice record itself', Reported: 'From an alert email only. Can’t be Open or Overdue', Unknown: 'Linked record not readable' };

export function BasisBadge({ basis }: { basis: Invoice2['basis'] }) { return <span className={`basis-badge basis-${basis.toLowerCase()}`} title={BASIS_HINT[basis]}>{basis}</span>; }

export function NoFinanceAccess({ viewer, setViewer }: { viewer: string; setViewer?: (v: string) => void }) {
  return <Panel title="Invoices & contracts" eyebrow="ADMINS ONLY"><div className="coming-soon-box"><Lock size={22} /><div><h3>{viewer} doesn’t have access to finance</h3><p>Agreements, invoices and payments are visible to {FINANCE_ADMINS.join(' and ')} only. They’re also hidden from client History, Profile, Handover briefs and chat for everyone else.</p>{setViewer && <p className="hint">To preview finance, switch to {FINANCE_ADMINS.join(' or ')} from the account menu in the sidebar.</p>}</div></div></Panel>;
}

function lastReminder(i: Invoice2, log: Chase[]) {
  const all = [...i.reminders.map(r => ({ date: r.date, label: r.kind })), ...log.filter(c => c.invoiceId === i.id).map(c => ({ date: c.date, label: `Personal chase (hello@) · ${c.by}` }))].sort((a, b) => b.date.localeCompare(a.date));
  return all[0];
}
export const chasedBy = (i: Invoice2, log: Chase[]) => [...i.reminders.filter(r => r.kind.startsWith('Personal')).map(r => ({ date: r.date, by: r.by || '' })), ...log.filter(c => c.invoiceId === i.id)].filter(c => c.date >= i.due).sort((a, b) => b.date.localeCompare(a.date))[0];

export function InvoiceTable({ rows, onOpen, onChase, showClient = true }: { rows: Invoice2[]; onOpen: (i: Invoice2) => void; onChase: (i: Invoice2) => void; showClient?: boolean }) {
  const log = useChases();
  if (!rows.length) return <Empty title="No invoices in this view" />;
  return <div className="table-scroll"><table className="invoice-table fin-table"><thead><tr>{showClient && <th>Client</th>}<th>Invoice</th><th>Amount · paid</th><th>Due</th><th>Status</th><th>Reminders</th><th /></tr></thead><tbody>{rows.map(i => { const c = clientById(i.clientId); const st = invoiceStatus(i); const last = lastReminder(i, log); return <tr key={i.id}>
    {showClient && <td><span className="table-client"><Avatar client={c} small /><span><strong>{c.name}</strong><small>{i.engagement}</small></span></span></td>}
    <td><button className="text-button" onClick={() => onOpen(i)}>{i.id}</button><small className="block muted">{i.source}{i.instalment ? ` · ${i.instalment.n} of ${i.instalment.of}` : ''}</small></td>
    <td><strong>{usd(i.amount)}</strong><small className="block muted">{i.basis === 'Reconciled' ? `paid ${usd(i.paid)} · balance ${usd(i.amount - i.paid)}` : i.paid ? `${usd(i.paid)} reported` : 'balance unknown'}</small></td>
    <td>{dateLabel(i.due)}{st === 'Overdue' && <small className="block text-amber">{finDaysSince(i.due)} days overdue</small>}</td>
    <td><Badge tone={STATUS_TONE[st]} dot={false}>{st}</Badge> <BasisBadge basis={i.basis} /></td>
    <td>{last ? <small>{dateLabel(last.date)} · {last.label}</small> : <small className="muted">None</small>}</td>
    <td>{st === 'Overdue' ? <button className="button button-small button-outline" onClick={() => onChase(i)}><Mail size={13} />Chase…</button> : <button className="icon-button" aria-label={`Open ${i.id}`} onClick={() => onOpen(i)}><ArrowRight size={15} /></button>}</td>
  </tr>; })}</tbody></table></div>;
}

export function InvoiceDrawer({ invoice, close, onChase }: { invoice: Invoice2; close: () => void; onChase: (i: Invoice2) => void }) {
  return <Dialog title={invoice.id} subtitle={`${clientById(invoice.clientId).name} · Invoice details`} size="lg" className="finance-record-modal" onClose={close} footer={<button className="button button-outline" onClick={close}>Close</button>}>
    <InvoiceDetails invoice={invoice} onChase={item => { close(); onChase(item); }} />
  </Dialog>;
}

/** Shared, tab-free invoice content: standalone modal or inline within a client record. */
export function InvoiceDetails({ invoice, onChase, showAgreement = true }: { invoice: Invoice2; onChase: (i: Invoice2) => void; showAgreement?: boolean }) {
  const log = useChases();
  const st = invoiceStatus(invoice);
  const agreement = AGREEMENTS.find(a => a.id === invoice.agreementId);
  const reminders = [...invoice.reminders.map(r => ({ date: r.date, text: `${r.kind}${r.by ? ` · ${r.by}` : ''}` })), ...log.filter(x => x.invoiceId === invoice.id).map(x => ({ date: x.date, text: `Personal chase (hello@) · ${x.by}${x.slackNote ? ' · Whitney noted on Slack' : ''}` }))].sort((a, b) => a.date.localeCompare(b.date));
  return <div className="invoice-detail-content">
    <div className="drawer-badges"><Badge tone={STATUS_TONE[st]}>{st}</Badge><BasisBadge basis={invoice.basis} /><Badge tone="neutral" dot={false}>{invoice.source}</Badge></div>
    <dl className="detail-list"><div><dt>Engagement</dt><dd>{invoice.engagement}{invoice.instalment ? ` · instalment ${invoice.instalment.n} of ${invoice.instalment.of}` : ''}</dd></div><div><dt>Issued · due</dt><dd>{dateLabel(invoice.issued)} · {dateLabel(invoice.due)}</dd></div><div><dt>Amount</dt><dd>{usd(invoice.amount)}</dd></div><div><dt>Balance</dt><dd>{invoice.basis === 'Reconciled' ? usd(invoice.amount - invoice.paid) : 'Unknown (not reconciled)'}</dd></div></dl>
    <div className="drawer-section"><p className="small-label">LINE ITEMS</p>{invoice.lines.map(l => <p key={l} className="hint">{l}</p>)}</div>
    <div className="drawer-section"><p className="small-label">PAYMENTS</p>{invoice.payments.length ? invoice.payments.map(p => <p key={p.date} className="hint"><Check size={11} /> {dateLabel(p.date)} · {usd(p.amount)} · {p.note}</p>) : <p className="hint">No payment recorded.</p>}</div>
    <div className="drawer-section"><p className="small-label">REMINDERS & CHASES</p>{reminders.length ? <ol className="history-list">{reminders.map((r, i) => <li key={i}><span>{dateLabel(r.date)}</span>{r.text}</li>)}</ol> : <p className="hint">None.</p>}<p className="hint">A reminder never proves the money is still owed. The balance comes from the invoice record.</p></div>
    {showAgreement && agreement && <div className="drawer-section"><p className="small-label">AGREEMENT</p><p className="hint">{agreement.name} · signed {agreement.signed ? dateLabel(agreement.signed) : '—'}{agreement.terms ? ` · ${agreement.terms.fee}` : ''}</p></div>}
    <div className="drawer-section"><p className="small-label">SOURCE</p><p className="hint">{invoice.evidence}</p>{invoice.link ? <a className="text-button" href={invoice.link} target="_blank" rel="noopener noreferrer">Open in {invoice.source}<ArrowUpRight size={11} /></a> : <button className="text-button">Open in {invoice.source}<ArrowUpRight size={11} /></button>}</div>
    {st === 'Overdue' && <div className="drawer-section"><button className="button button-primary button-small" onClick={() => { onChase(invoice); }}><Mail size={13} />Chase…</button></div>}
  </div>;
}

const invoicePhrase = (i: Invoice2) => { const [what, period] = (i.lines[0] || 'invoice').split(' · '); if (!period) return what.toLowerCase(); return period.startsWith('instalment') ? `${what} ${period} invoice` : `${period} ${what} invoice`; };

export function ChaseDialog({ invoice, viewer, close, notify }: { invoice: Invoice2; viewer: string; close: () => void; notify: (m: string) => void }) {
  const c = clientById(invoice.clientId);
  const first = c.contact.split(' ')[0];
  const [subject, setSubject] = useState(`${c.name} · invoice ${invoice.id}`);
  const [body, setBody] = useState(`Hi ${first},\n\nI hope you're having a good week! A quick note that the ${invoicePhrase(invoice)} (${usd(invoice.amount)}, due ${dateLabel(invoice.due, { day: 'numeric', month: 'long' })}) is still showing as open on our side. The automatic reminders sometimes land in spam or promotions, so here's the link again:\n\n[Invoice link from ${invoice.source}]\n\nIf it's already on its way, please ignore this. Thank you so much!\n\n${viewer}\nWedding Industry Ads`);
  const [slackNote, setSlackNote] = useState(viewer !== 'Whitney');
  const copy = async () => { try { await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`); notify('Email copied. Paste it into hello@ and send it from there.'); } catch { notify('Clipboard access is unavailable in this browser.'); } };
  return <Dialog title="Chase an overdue invoice" subtitle={`${invoice.id} · ${finDaysSince(invoice.due)} days overdue`} className="slack-dialog" onClose={close}>
    <p className="hint">The KB drafts it; you review and send it from hello@. It never emails a client by itself.</p>
    <div className="form-stack">
      <label>To<input value={`${c.contact} <${c.email}>`} readOnly /></label>
      <label>Subject<input value={subject} onChange={e => setSubject(e.target.value)} /></label>
      <label>Message<textarea rows={12} value={body} onChange={e => setBody(e.target.value)} /></label>
      <label className="check-row"><input type="checkbox" checked={slackNote} onChange={e => setSlackNote(e.target.checked)} />Also note Whitney on Slack: “{c.name} invoice {finDaysSince(invoice.due)} days overdue. Chase drafted by {viewer}.”</label>
    </div>
    <div className="slack-footer"><div className="drawer-inline"><button className="button button-outline button-small" onClick={copy}><Clipboard size={13} />Copy email</button><button className="button button-outline button-small" disabled title="Needs Gmail compose permission (decision F7)"><Mail size={13} />Create Gmail draft</button></div>
      <button className="button button-primary" onClick={() => { chaseStore.add({ invoiceId: invoice.id, date: finToday(), by: me(viewer), slackNote }); close(); notify(`Chase logged on ${invoice.id}${slackNote ? ' and Whitney noted on Slack' : ''}. Preview only: nothing was sent.`); }}><Check size={14} />I’ve sent it</button></div>
  </Dialog>;
}

function AgreementCards({ rows }: { rows: Agreement[] }) {
  if (!rows.length) return <Empty title="No agreements" />;
  const tone = (s: Agreement['status']): Tone => s === 'Active' ? 'green' : s === 'Signed' ? 'blue' : s === 'Superseded' || s === 'Ended' ? 'neutral' : 'gold';
  return <div className="agreement-grid">{rows.map(a => { const c = clientById(a.clientId); const ending = a.terms?.end && a.terms.end <= addDays(DEMO_DATE, 60) && a.status === 'Active'; return <article className="panel agreement-card" key={a.id}>
    <div className="agreement-head"><Avatar client={c} small /><div><h3>{a.name}</h3><p className="hint">{c.name} · {a.engagements.join(', ')} · {a.source}</p></div><Badge tone={tone(a.status)} dot={false}>{a.status}</Badge></div>
    <p className="hint">{a.proposalSent ? `Proposal sent ${dateLabel(a.proposalSent)} · ` : ''}{a.signed ? `Signed ${dateLabel(a.signed)} by ${a.signer}` : 'Not signed'}</p>
    {ending && <p className="stale-note"><CalendarClock size={13} />Ends {dateLabel(a.terms!.end!)}: renewal conversation due.</p>}
    {a.terms ? <dl className="terms-list"><div><dt>Fee</dt><dd>{a.terms.fee}</dd></div><div><dt>Billing</dt><dd>{a.terms.interval}</dd></div><div><dt>Start</dt><dd>{dateLabel(a.terms.start, { day: 'numeric', month: 'short', year: 'numeric' })}</dd></div>{a.terms.minTerm && <div><dt>Minimum term</dt><dd>{a.terms.minTerm}</dd></div>}{a.terms.end && <div><dt>End</dt><dd>{dateLabel(a.terms.end, { day: 'numeric', month: 'short', year: 'numeric' })}</dd></div>}{a.terms.notice && <div><dt>Notice</dt><dd>{a.terms.notice}</dd></div>}{a.terms.adSpend && <div><dt>Ad spend</dt><dd>{a.terms.adSpend}</dd></div>}<div><dt>Included</dt><dd>{a.terms.included.join(' · ')}</dd></div></dl>
      : <div className="unavailable-box"><FileSignature size={14} /><div><strong>Terms not yet read</strong><p>{a.termsNote}</p></div></div>}
    {a.terms && a.termsNote && <p className="hint">{a.termsNote}</p>}
    {a.link ? <a className="text-button" href={a.link} target="_blank" rel="noopener noreferrer">Open agreement in {a.source}<ArrowUpRight size={11} /></a> : <button className="text-button">Open agreement in {a.source}<ArrowUpRight size={11} /></button>}
  </article>; })}</div>;
}

function PlansTable({ clientId }: { clientId?: string }) {
  const rows = PLANS.filter(p => !clientId || p.clientId === clientId);
  return <div className="sources-table plans-table" role="table"><div className="sources-row head" role="row"><span>Client</span><span>Engagement · plan</span><span>Amount</span><span>Next invoice</span><span>Progress</span></div>
    {rows.map(p => <div className="sources-row" role="row" key={p.clientId + p.engagement}><strong>{clientById(p.clientId).name}</strong><span>{p.engagement}<small className="block hint">{p.plan} · {p.source}</small></span><span>{usd(p.amount)}<small className="block hint">{p.interval}</small></span><span>{p.missing ? <span className="row-flag flag-amber"><AlertTriangle size={10} />Missing invoice</span> : p.nextInvoice ? dateLabel(p.nextInvoice) : '—'}{p.missing && <small className="block hint">{p.missing}</small>}</span><span>{p.instalments ? <><span className="mini-bar"><i style={{ width: `${p.instalments.paid / p.instalments.of * 100}%` }} /></span><small className="hint">{p.instalments.paid} of {p.instalments.of} paid</small></> : <small className="hint">Recurring</small>}</span></div>)}
  </div>;
}

type Ev = { date: string; clientId: string; kind: 'Proposal' | 'Signed' | 'Invoice' | 'Reminder' | 'Chase' | 'Payment' | 'Failed payment'; text: string; source: 'GHL' | 'Dubsado' | 'Gmail' };
export function activity(log: Chase[], clientId?: string): Ev[] {
  const ev: Ev[] = [];
  AGREEMENTS.forEach(a => { if (a.proposalSent) ev.push({ date: a.proposalSent, clientId: a.clientId, kind: 'Proposal', text: `Proposal sent · ${a.name}`, source: 'Dubsado' }); if (a.signed) ev.push({ date: a.signed, clientId: a.clientId, kind: 'Signed', text: `Signed by ${a.signer} · ${a.name} (${a.source})`, source: a.source }); });
  INVOICES2.forEach(i => { ev.push({ date: i.issued, clientId: i.clientId, kind: 'Invoice', text: `Invoice ${i.id} issued · ${usd(i.amount)} · ${i.source}`, source: i.source }); i.reminders.forEach(r => ev.push({ date: r.date, clientId: i.clientId, kind: r.kind.startsWith('Personal') ? 'Chase' : 'Reminder', text: `${r.kind}${r.by ? ` by ${r.by}` : ''} · ${i.id}`, source: r.kind.startsWith('Personal') ? 'Gmail' : i.source })); i.payments.forEach(p => ev.push({ date: p.date, clientId: i.clientId, kind: 'Payment', text: `${usd(p.amount)} received · ${i.id} · ${p.note}`, source: i.source })); });
  FAILED_PAYMENTS.forEach(f => ev.push({ date: f.date, clientId: f.clientId, kind: 'Failed payment', text: `${usd(f.amount)} payment failed · ${f.source}${f.invoiceId ? ` · ${f.invoiceId}` : ''}${f.resolved ? ' · since resolved' : ''}`, source: 'GHL' }));
  log.forEach(c => { const i = INVOICES2.find(x => x.id === c.invoiceId)!; ev.push({ date: c.date, clientId: i.clientId, kind: 'Chase', text: `Personal chase (hello@) by ${c.by} · ${i.id}`, source: 'Gmail' }); });
  return ev.filter(e => !clientId || e.clientId === clientId).sort((a, b) => b.date.localeCompare(a.date));
}

export function ActivityFeed({ clientId, kind = 'all' }: { clientId?: string; kind?: string }) {
  const log = useChases();
  const rows = activity(log, clientId).filter(e => kind === 'all' || e.kind === kind);
  const icon = (k: Ev['kind']) => k === 'Payment' ? <Wallet size={14} /> : k === 'Signed' ? <FileSignature size={14} /> : k === 'Chase' ? <Mail size={14} /> : k === 'Reminder' ? <Bell size={14} /> : <ReceiptText size={14} />;
  return rows.length ? <ul className="fin-activity">{rows.map((e, i) => <li key={i} className={`kind-${e.kind.toLowerCase()}`}><span className="fin-activity-icon">{icon(e.kind)}</span><span className="hint">{dateLabel(e.date)}</span><div><strong>{e.kind}</strong>{!clientId && <span className="hint"> · {clientById(e.clientId).name}</span>}<p>{e.text}</p></div></li>)}</ul> : <Empty title="No events" />;
}

/*
 * Client record → Invoices & terms. Answers one question for an admin about one client:
 * "Are they up to date, what's billed next, and what did they sign?"
 * 1. Standing line: up to date / overdue (with Chase), billing, next invoice, paid to date.
 * 2. Standing and billing KPIs (left) beside Agreements & terms (right).
 * 3. One activity timeline, filterable, which also holds the chase history.
 * Totals only count Reconciled records and say how many were left out.
 */
const OPEN_STATES: InvoiceStatus[] = ['Overdue', 'Due soon', 'Open', 'Partially paid'];
const ACTIVITY_PREVIEW = 6;
type ActivityFilter = 'all' | 'money' | 'chases' | 'agreements';
const ACTIVITY_FILTERS: [ActivityFilter, string, Ev['kind'][]][] = [
  ['all', 'All', []], ['money', 'Invoices & payments', ['Invoice', 'Payment', 'Failed payment']],
  ['chases', 'Reminders & chases', ['Reminder', 'Chase']], ['agreements', 'Agreements', ['Proposal', 'Signed']],
];

export function ClientFinance(props: WorkspaceProps & { clientId: string }) {
  const log = useChases();
  const [chase, setChase] = useState<Invoice2 | null>(null);
  const [filter, setFilter] = useState<ActivityFilter>('all');
  const [allActivity, setAllActivity] = useState(false);
  const [showEarlier, setShowEarlier] = useState(false);

  const invoices = INVOICES2.filter(i => i.clientId === props.clientId).sort((a, b) => b.due.localeCompare(a.due));
  const reconciled = invoices.filter(i => i.basis === 'Reconciled');
  const overdue = invoices.filter(i => invoiceStatus(i) === 'Overdue');
  const outstanding = reconciled.filter(i => OPEN_STATES.includes(invoiceStatus(i)));
  const owed = outstanding.reduce((s, i) => s + i.amount - i.paid, 0);
  const overdueOwed = overdue.reduce((s, i) => s + i.amount - i.paid, 0);
  const paidReconciled = reconciled.reduce((s, i) => s + i.paid, 0);
  const notReconciled = invoices.length - reconciled.length;
  const plans = PLANS.filter(p => p.clientId === props.clientId);
  const missing = plans.filter(p => p.missing);
  const monthly = plans.filter(p => p.interval === 'Monthly').reduce((s, p) => s + p.amount, 0);
  const nextOpen = invoices.filter(i => ['Open', 'Due soon'].includes(invoiceStatus(i))).sort((a, b) => a.due.localeCompare(b.due))[0];
  const nextPlanned = plans.filter(p => p.nextInvoice).sort((a, b) => a.nextInvoice!.localeCompare(b.nextInvoice!))[0];
  const agreements = AGREEMENTS.filter(a => a.clientId === props.clientId);
  const current = agreements.filter(a => a.status !== 'Superseded' && a.status !== 'Ended');
  const earlier = agreements.filter(a => !current.includes(a));
  const events = activity(log, props.clientId).filter(e => filter === 'all' || ACTIVITY_FILTERS.find(f => f[0] === filter)![2].includes(e.kind));
  const lastChase = (i: Invoice2) => chasedBy(i, log);

  const standing = overdue.length
    ? { tone: 'late', icon: <AlertTriangle size={18} />, title: `${overdue.length} invoice${overdue.length > 1 ? 's' : ''} overdue · ${usd(overdueOwed)}`, sub: overdue.map(i => `${i.id} is ${finDaysSince(i.due)} days late${lastChase(i) ? ` · chased ${dateLabel(lastChase(i)!.date)} by ${lastChase(i)!.by}` : ' · not chased yet'}`).join(' · ') }
    : missing.length
      ? { tone: 'warn', icon: <CalendarClock size={18} />, title: 'Nothing overdue, but an invoice is missing', sub: missing.map(p => `${p.engagement}: ${p.missing}`).join(' · ') }
      // Alerts alone can't prove a client is up to date (Reported / Unknown basis).
      : invoices.length && !reconciled.length ? { tone: 'none', icon: <Inbox size={18} />, title: 'Can’t confirm yet', sub: `${invoices.length} invoice${invoices.length > 1 ? 's' : ''} known only from alert emails. Status shows once the invoice record is readable.` }
      : invoices.length || plans.length ? { tone: 'ok', icon: <Check size={18} />, title: 'Up to date', sub: owed ? `${usd(owed)} open, not yet due.` : 'No open balance on reconciled invoices.' }
        : { tone: 'none', icon: <Inbox size={18} />, title: 'No commercial records yet', sub: 'No agreement, invoice or payment has been matched to this client.' };

  const agreementCard = (a: Agreement) => {
    const plan = plans.find(p => a.engagements.includes(p.engagement));
    const ending = a.terms?.end && a.terms.end <= addDays(finToday(), 60) && a.status === 'Active';
    const tone: Tone = a.status === 'Active' ? 'green' : a.status === 'Signed' ? 'blue' : a.status === 'Sent' ? 'gold' : 'neutral';
    return <article className="cf-agreement" key={a.id}>
      <header><div><h4>{a.engagements.join(' + ')}</h4><p>{a.signed ? `Signed ${dateLabel(a.signed, { day: 'numeric', month: 'short', year: 'numeric' })} by ${a.signer}` : a.proposalSent ? `Proposal sent ${dateLabel(a.proposalSent)}, not signed` : 'Not signed'} · {a.source}</p></div><Badge tone={tone} dot={false}>{a.status}</Badge></header>
      {a.terms ? <dl>
        <div><dt>Fee</dt><dd>{a.terms.fee}</dd></div>
        <div><dt>Billing</dt><dd>{a.terms.interval}</dd></div>
        <div><dt>Term</dt><dd>{dateLabel(a.terms.start, { day: 'numeric', month: 'short', year: 'numeric' })}{a.terms.end ? ` → ${dateLabel(a.terms.end, { day: 'numeric', month: 'short', year: 'numeric' })}` : ''}{a.terms.minTerm ? ` · min. ${a.terms.minTerm}` : ''}</dd></div>
        {a.terms.notice && <div><dt>Notice</dt><dd>{a.terms.notice}</dd></div>}
      </dl> : <p className="cf-unread"><FileSignature size={13} />{a.termsNote || 'Terms not yet read.'}</p>}
      {plan?.instalments && <div className="cf-instalments"><span className="mini-bar"><i style={{ width: `${plan.instalments.paid / plan.instalments.of * 100}%` }} /></span><small>{plan.instalments.paid} of {plan.instalments.of} paid</small></div>}
      {ending && <p className="cf-renewal"><CalendarClock size={12} />Ends {dateLabel(a.terms!.end!)}. Renewal conversation due.</p>}
      {a.terms && <details className="cf-included"><summary>What’s included{a.terms.adSpend ? ' · ad spend' : ''}</summary><ul>{a.terms.included.map(x => <li key={x}>{x}</li>)}</ul>{a.terms.adSpend && <p>Ad spend: {a.terms.adSpend}</p>}{a.terms && a.termsNote && <p>{a.termsNote}</p>}</details>}
      {a.link ? <a className="text-button" href={a.link} target="_blank" rel="noopener noreferrer">Open in {a.source}<ArrowUpRight size={11} /></a> : <button className="text-button">Open in {a.source}<ArrowUpRight size={11} /></button>}
    </article>;
  };

  return <div className="cf">
    <div className="cf-overview">
    <section className={`cf-standing tone-${standing.tone}`} aria-label="Commercial standing">
      <div className="cf-standing-main"><span className="cf-standing-icon">{standing.icon}</span><div><p className="cf-eyebrow"><Lock size={10} />Admins only · {FINANCE_ADMINS.join(' and ')}</p><h3>{standing.title}</h3><p>{standing.sub}</p></div>
        {overdue.length > 0 && <div className="cf-standing-actions">{overdue.map(i => <button key={i.id} className="button button-small button-primary" onClick={() => setChase(i)}><Mail size={13} />Chase {i.id}…</button>)}</div>}</div>
      {missing.length > 0 && <div className="cf-standing-missing">{missing.map(p => <div className="cf-missing" key={p.engagement}><AlertTriangle size={13} /><div><strong>{p.engagement} invoice not issued</strong><small>{p.missing}</small></div></div>)}</div>}
      <dl className="cf-facts">
        <div><dt>Billing</dt><dd>{monthly ? `${usd(monthly)} / month` : plans[0] ? plans[0].plan : '—'}</dd><small>{plans.map(p => `${p.engagement}: ${p.plan}`).join(' · ') || 'No billing plan found'}</small></div>
        <div><dt>Next invoice</dt><dd>{nextOpen ? `${usd(nextOpen.amount)} · due ${dateLabel(nextOpen.due)}` : nextPlanned ? `Issues ${dateLabel(nextPlanned.nextInvoice!)}` : '—'}</dd><small>{nextOpen ? `${nextOpen.id} · ${invoiceStatus(nextOpen)}` : nextPlanned ? `${nextPlanned.engagement} · ${usd(nextPlanned.amount)}` : 'Nothing scheduled'}</small></div>
        <div><dt>Paid to date</dt><dd>{usd(paidReconciled)}</dd><small>{notReconciled ? `Reconciled only · ${notReconciled} more not yet reconciled` : 'All invoices reconciled'}</small></div>
      </dl>
    </section>

      <section className="cf-panel" aria-label="Agreements and terms">
        <header className="cf-panel-head"><h3>Agreements &amp; terms<span>{current.length}</span></h3><small>From the signed document; alerts never set terms</small></header>
        {current.length ? current.map(agreementCard) : <p className="cf-empty">No current agreement.</p>}
        {earlier.length > 0 && <><button className="text-button cf-more" onClick={() => setShowEarlier(v => !v)}>{showEarlier ? 'Hide' : 'Show'} earlier agreements ({earlier.length})</button>{showEarlier && earlier.map(agreementCard)}</>}
      </section>
    </div>

    <section className="cf-panel" aria-label="Commercial activity">
      <header className="cf-panel-head"><h3>Activity</h3><div className="cf-chips" role="group" aria-label="Filter activity">{ACTIVITY_FILTERS.map(([id, label]) => <button key={id} className={filter === id ? 'selected' : ''} aria-pressed={filter === id} onClick={() => { setFilter(id); setAllActivity(false); }}>{label}</button>)}</div></header>
      {events.length ? <ul className="cf-timeline">{(allActivity ? events : events.slice(0, ACTIVITY_PREVIEW)).map((e, n) => <li key={n} className={`kind-${e.kind.toLowerCase().replace(/\s/g, '-')}`}>
        <span className="cf-dot" aria-hidden="true" /><span className="cf-when">{dateLabel(e.date)}</span><span className="cf-kind">{e.kind}</span><span className="cf-text">{e.text}</span><span className="cf-src">{e.source}</span>
      </li>)}</ul> : <p className="cf-empty">Nothing in this view.</p>}
      {events.length > ACTIVITY_PREVIEW && <button className="text-button cf-more" onClick={() => setAllActivity(v => !v)}>{allActivity ? 'Show fewer' : `Show all ${events.length} events`}</button>}
    </section>

    {chase && <ChaseDialog invoice={chase} viewer={props.viewer} close={() => setChase(null)} notify={props.notify} />}
  </div>;
}

export function commercialEvents(clientId: string) {
  return activity(chaseStore.get(), clientId).filter(e => e.kind === 'Signed' || e.kind === 'Payment');
}
