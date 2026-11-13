import kbLive from '@kb-live';
import { ThemedSelect } from '../components/ThemedSelect';
import { createPortal } from 'react-dom';
import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { ArrowRight, ArrowUpRight, BookMarked, Check, ChevronDown, Copy, Download, Expand, FileDown, FileText, Info, Lock, MessageSquareQuote, MoreHorizontal, PanelRight, Pencil, RefreshCw, MessagesSquare, Pin, PinOff, Plus, Search, Send, Sparkles, Square, Trash2, X } from 'lucide-react';
import { CALLS, CLIENTS, DEMO_DATE, EVIDENCE, VIEWERS, addDays, daysBetween, viewerByName, clientById, dateLabel, isOutstanding, isOverdue, ownerLabel, timeLabel } from '../data';
import { recordFor } from '../records';
import { isFinanceAdmin, INVOICES2, invoiceStatus, usd } from '../finance';
import { assessmentFor, categoryOf, VOICE, WAITING } from '../health';
import { CALL_META } from '../calls';
import type { Action, AskContext, ClientTab, WorkspaceProps } from '../types';
import './Client360.css';

// ---------- Answer model (mirrors the answer contract in chatbot_KB.md §6) ----------
type Status = 'Answered' | 'Partial' | 'Need to clarify' | 'No evidence' | 'Unavailable' | 'Conflict';
type Block = { label: 'Fact' | 'Interpretation' | 'Suggestion' | 'Definition'; text: string; cites?: number[] };
type Cite = { n: number; label: string; date?: string; sourceId?: string };
type Link = { label: string; kind: 'client' | 'call' | 'actions' | 'money'; id?: string; tab?: ClientTab };
export interface Answer { status: Status; scope: string; summary: string; blocks: Block[]; more?: Block[]; cites: Cite[]; gaps: string[]; links: Link[]; followUps: string[]; looked: { what: string; detail: string }[]; clarify?: { label: string; question: string }[]; note?: string }
type Msg = { role: 'user'; text: string; context?: AskContext } | { role: 'assistant'; answer: Answer; id: string };
interface Thread { id: string; title: string; clientId: string | 'all'; group: 'Today' | 'This week' | 'Older'; messages: Msg[]; pinned?: boolean; at?: string }
interface PinItem { id: string; title: string; clientId: string; answer: Answer; pinnedOn: string; changed?: string }

// ---------- Shared store: the tab and the side panel see the same conversations ----------
let state: { threads: Thread[]; pins: PinItem[]; activeId: string } = { threads: [], pins: [], activeId: '' };
const subs = new Set<() => void>();
const store = {
  sub: (f: () => void) => { subs.add(f); return () => subs.delete(f); },
  get: () => state,
  set: (fn: (s: typeof state) => typeof state) => { state = fn(state); subs.forEach(f => f()); },
};
const useStore = () => useSyncExternalStore(store.sub, store.get);
let seq = 100;
const nowStamp = () => { const d = new Date(); return `${DEMO_DATE}T${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };
/** Today: the time. This week: "N days ago". Older: the date. */
const threadStamp = (t: Thread) => {
  if (!t.at) return '';
  const day = t.at.slice(0, 10); const ago = daysBetween(day);
  if (ago <= 0) return timeLabel(t.at.slice(11, 16));
  if (ago === 1) return 'Yesterday';
  if (ago < 7) return `${ago} days ago`;
  return dateLabel(day, { day: 'numeric', month: 'short', year: 'numeric' });
};
const uid = (p: string) => `${p}-${++seq}`;

// ---------- Answer engine over the mock records ----------
const has = (q: string, re: RegExp) => re.test(q.toLowerCase());
const clientFromText = (q: string) => CLIENTS.find(c => q.toLowerCase().includes(c.name.toLowerCase().split(' ')[0].toLowerCase()) || q.toLowerCase().includes(c.contact.split(' ')[0].toLowerCase()))?.id;

function cite(list: Cite[], label: string, date?: string, sourceId?: string) { const n = list.length + 1; list.push({ n, label, date, sourceId }); return n; }

export function answerQuestion(q: string, scopeClient: string | 'all', ctx: AskContext | undefined, viewer: string, actions: Action[]): Answer {
  const cites: Cite[] = [];
  const clientId = ctx?.clientId || (scopeClient !== 'all' ? scopeClient : clientFromText(q));
  const c = clientId ? clientById(clientId) : undefined;
  const scopeName = c ? c.name : 'All clients';
  const base = (status: Status, summary: string, extra: Partial<Answer> = {}): Answer => ({ status, scope: scopeName, summary, blocks: [], cites, gaps: [], links: [], followUps: [], looked: [], ...extra });

  // Definitions: answered directly, no AI
  if (has(q, /what (does|is) .*(verified|done|stale|needs review|acknowledg|unassessed)|how is .*(category|health) (set|decided)|what does .* mean/)) {
    const defs: [RegExp, string][] = [
      [/verified/, '“Verified” means a named WIA person checked that a finished task actually worked (for example, conversions recording after a tracking fix). Only flagged types need it; everything else closes at Done.'],
      [/done/, '“Done” means the work was reported complete, from a closed ClickUp task or a delivery message. It isn’t the same as Verified.'],
      [/stale/, '“Stale” means something changed after a brief or summary was built, such as a new client message or an overdue action. The old version stays visible until it’s rebuilt.'],
      [/needs review/, '“Needs review” holds items the KB isn’t sure are real, current obligations: old asks, unclear owners, possible duplicates, AI proposals. A person accepts or dismisses each one.'],
      [/acknowledg/, 'An action is acknowledged when its owner accepts it: by replying, clicking Acknowledge, or using a configured emoji. Being assigned doesn’t count.'],
      [/unassessed/, '“Unassessed” means there isn’t enough evidence to judge a client’s health. It’s never treated as healthy.'],
      [/category|health/, 'The health category follows the client’s worst dimension and always names the cause, for example “Needs attention · follow-through: broken promise”. There’s no combined score.'],
    ];
    const d = defs.find(([re]) => re.test(q.toLowerCase()));
    return base('Answered', d ? d[1] : 'That term isn’t in the glossary yet.', { scope: 'Glossary', blocks: [{ label: 'Definition', text: 'Answered from the agreed glossary; no AI used.' }], looked: [{ what: 'Glossary', detail: 'Approved definitions' }], followUps: ['What does Needs review mean?', 'How is the health category set?'] });
  }

  // Read-only boundary
  if (has(q, /\b(add|create|make)\b.*\b(task|action)\b|\b(send|email|draft|message|notify|remind)\b.*\b(her|him|them|client|team|slack)\b|\bmark\b.*\b(done|verified|acknowledged)\b|\bassign\b/)) {
    return base('Unavailable', 'I can’t make changes or send anything. Client 360 is read-only. You can do this where the record lives:', { blocks: [{ label: 'Fact', text: 'Tasks are added in the Action Hub; messages go through the review-before-send screen there or in the client’s Commitments tab.' }], links: [{ label: 'Open the Action Hub', kind: 'actions' }, ...(c ? [{ label: `${c.name} · Commitments`, kind: 'client' as const, id: c.id, tab: 'commitments' as ClientTab }] : [])], looked: [] });
  }

  // Unapproved sources
  if (has(q, /website|instagram|facebook page|google search results|their site/)) {
    return base('Unavailable', 'Websites and social media aren’t approved sources for the knowledge base, so I can’t look there.', { blocks: [{ label: 'Fact', text: 'Approved sources: Gmail, Slack, ClickUp, historical Zoom, Fathom, Drive, LeadLock and Calendar.' }], followUps: c ? [`What does ${c.name} do?`] : [] });
  }

  // Finance (admins only)
  if (has(q, /invoice|paid|payment|owe us|contract|billing|renew/)) {
    if (!isFinanceAdmin(viewer)) return base('Unavailable', 'Finance information is visible to admins only, so I can’t answer this for you.', { blocks: [{ label: 'Fact', text: 'Ask Whitney or Gisselle.' }] });
    const inv = INVOICES2.filter(i => !c || i.clientId === c.id);
    const overdue = inv.filter(i => invoiceStatus(i) === 'Overdue');
    const n = cite(cites, 'GHL invoice records', '2026-10-09');
    return base('Answered', overdue.length ? `${overdue.length} overdue: ${overdue.map(i => `${clientById(i.clientId).name} ${i.id} (${usd(i.amount - i.paid)}, due ${dateLabel(i.due)})`).join('; ')}.` : `Nothing overdue${c ? ` for ${c.name}` : ''}.`, { blocks: [{ label: 'Fact', text: `${inv.filter(i => i.basis === 'Reconciled').length} reconciled invoices checked; ${inv.filter(i => i.basis !== 'Reconciled').length} from alerts only, which can’t show overdue.`, cites: [n] }], links: [{ label: 'Invoices & contracts', kind: 'money' }], looked: [{ what: 'Invoices', detail: `${inv.length} records · GHL 9:42 AM` }], note: 'Admins only' });
  }

  // Waiting on us (portfolio-wide OK)
  if (has(q, /waiting on (us|a reply)|haven.?t (replied|answered)|no reply|unanswered/)) {
    const rows = WAITING.filter(w => !c || w.clientId === c.id);
    rows.forEach(w => cite(cites, `${w.from} · ${w.channel}`, w.date, w.sourceId));
    return base(rows.length ? 'Answered' : 'Answered', rows.length ? `${rows.length} client message${rows.length > 1 ? 's are' : ' is'} waiting on a WIA reply.` : 'No client messages are waiting on a reply.', { blocks: rows.map((w, i) => ({ label: 'Fact' as const, text: `${clientById(w.clientId).name}: ${w.from} asked “${w.text}”, ${w.businessDays} business day${w.businessDays > 1 ? 's' : ''} ago.`, cites: [i + 1] })), looked: [{ what: 'Gmail and Slack', detail: 'Client messages and WIA replies · 9:40 AM' }], followUps: ['What’s overdue for my clients?'] });
  }

  // Actions / owed / overdue / assigned
  const person = [...VIEWERS.map(v => v.name as string), 'Danielle', 'Ivy'].find(n => q.toLowerCase().includes(n.toLowerCase()) && has(q, /assigned|owe|on .*plate|for /));
  if (has(q, /outstanding|overdue|owe|owed|open (items|actions|tasks)|assigned|to.?do|on my plate|my (tasks|actions)|waiting on (the )?client/)) {
    const mine = has(q, /\bmy (tasks|actions|plate)|on my plate|assigned to me/);
    let rows = actions.filter(a => isOutstanding(a) && (!c || a.clientId === c.id));
    if (mine) rows = rows.filter(a => a.owner === viewer);
    else if (person) rows = rows.filter(a => a.owner === person);
    if (has(q, /overdue/)) rows = rows.filter(isOverdue);
    if (has(q, /waiting on (the )?client|client owes/)) rows = rows.filter(a => a.side === 'Client');
    const wia = rows.filter(a => a.side === 'WIA'), cl = rows.filter(a => a.side === 'Client');
    const blocks: Block[] = [];
    if (wia.length) blocks.push({ label: 'Fact', text: `WIA owes: ${wia.map(a => `${a.title} (${ownerLabel(a.owner)}, ${a.due ? (isOverdue(a) ? `overdue since ${dateLabel(a.due)}` : `due ${dateLabel(a.due)}`) : 'no date agreed'}${!c ? `, ${clientById(a.clientId).name}` : ''})`).join('; ')}.`, cites: wia.filter(a => a.sourceId).slice(0, 3).map(a => cite(cites, a.title, a.lastActivity, a.sourceId)) });
    if (cl.length) blocks.push({ label: 'Fact', text: `Client owes: ${cl.map(a => `${a.title} (${a.due ? dateLabel(a.due) : 'no date'})`).join('; ')}.`, cites: cl.filter(a => a.sourceId).slice(0, 2).map(a => cite(cites, a.title, a.lastActivity, a.sourceId)) });
    const unknown = rows.filter(a => !a.owner || !a.due).length;
    return base('Answered', rows.length ? `${rows.length} open item${rows.length > 1 ? 's' : ''}${mine ? ` for you` : person ? ` for ${person}` : ''}${c ? ` at ${c.name}` : ' across your clients'}: ${wia.length} WIA owes, ${cl.length} the client owes, ${rows.filter(isOverdue).length} overdue.` : 'Nothing open matches that.', { blocks, gaps: unknown ? [`${unknown} item${unknown > 1 ? 's have' : ' has'} no owner or no agreed date; they’re never counted as overdue.`] : [], links: [{ label: 'Open the Action Hub', kind: 'actions' }, ...(c ? [{ label: `${c.name} · Commitments`, kind: 'client' as const, id: c.id, tab: 'commitments' as ClientTab }] : [])], looked: [{ what: 'Action Hub', detail: `${actions.length} actions, counted in full (not search hits)` }, { what: 'ClickUp', detail: 'Synced 9:42 AM' }], followUps: c ? [`What did ${c.contact.split(' ')[0]} ask that we haven’t answered?`, 'Who hasn’t acknowledged their tasks?'] : ['Which clients are waiting on a reply from us?'] });
  }

  // Anything below needs one client
  if (!c) {
    const mine = CLIENTS.filter(x => recordFor(x.id).owner === viewer);
    return base('Need to clarify', 'Which client do you mean?', { scope: 'No client selected', clarify: (mine.length ? mine : CLIENTS).slice(0, 4).map(x => ({ label: x.name, question: `${q} (${x.name})` })) });
  }
  const r = recordFor(c.id);

  // Ask about a specific action
  if (ctx?.kind === 'action' && ctx.id) {
    const a = actions.find(x => x.id === ctx.id);
    if (a) {
      const n1 = a.sourceId ? cite(cites, `Origin · ${a.origin || 'source'}`, a.lastActivity, a.sourceId) : undefined;
      return base('Answered', `${a.title}: ${a.status}${isOverdue(a) ? ', overdue' : ''}. Owner ${ownerLabel(a.owner)}${a.acknowledged ? ' (acknowledged)' : ' (not acknowledged yet)'}; ${a.due ? `due ${dateLabel(a.due)}` : 'no date agreed'}.`, { scope: `${c.name} · action`, blocks: [
        ...(a.quote ? [{ label: 'Fact' as const, text: `It came from: “${a.quote}”`, cites: n1 ? [n1] : [] }] : []),
        ...(a.conflict ? [{ label: 'Fact' as const, text: a.conflict }] : []),
        ...(a.verifyRequired ? [{ label: 'Fact' as const, text: a.status === 'Verified' ? `Verified by ${a.verification?.by}.` : 'This type needs a separate Verified check after Done.' }] : []),
      ], more: (a.history || []).map(h => ({ label: 'Fact' as const, text: `${dateLabel(h.date)}: ${h.text}` })), links: [{ label: `${c.name} · Commitments`, kind: 'client', id: c.id, tab: 'commitments' }], looked: [{ what: 'Action history', detail: `${(a.history || []).length} changes` }], followUps: ['Who assigned this, and when?', 'What did the client ask for?'] });
    }
  }

  // Last call / discussed / agreed
  if (has(q, /last call|discussed|agreed|decided|meeting|recap/)) {
    const withContent = r.meetings.filter(m => m.transcript === 'Available' || m.transcript === 'Summary only').sort((a, b) => b.date.localeCompare(a.date));
    const types = [...new Set(r.meetings.map(m => m.type))];
    if (has(q, /last call/) && types.length > 1 && !has(q, new RegExp(types.join('|').toLowerCase()))) return base('Need to clarify', `${c.name} has had different kinds of calls. Which one?`, { clarify: types.map(t => ({ label: `Last ${t.toLowerCase()} call`, question: `What was agreed on the last ${t.toLowerCase()} call with ${c.name}?` })) });
    const m = withContent.find(x => types.length === 1 || has(q, new RegExp(x.type.toLowerCase())) || !has(q, /last call/)) || withContent[0];
    if (!m) return base('No evidence', `I couldn’t find a call with a transcript or summary for ${c.name}.`, { looked: [{ what: 'Fathom, Zoom, Drive', detail: 'No readable call content' }] });
    const n = cite(cites, `${m.title} · ${m.source}`, m.date, m.sourceId);
    const later = r.meetings.filter(x => x.date > m.date && x.transcript === 'Not found');
    return base(later.length ? 'Partial' : 'Answered', `The last call with content was the ${m.title} on ${dateLabel(m.date)}: ${m.decisions[0] || 'no decisions recorded'}`, { scope: `${c.name} · ${m.title} (${dateLabel(m.date)})`, blocks: [
      ...m.decisions.map(d => ({ label: 'Fact' as const, text: d, cites: [n] })),
      ...(m.actionIds.length ? [{ label: 'Fact' as const, text: `Commitments made: ${m.actionIds.map(id => { const a = actions.find(x => x.id === id); return a ? `${a.title} (${ownerLabel(a.owner)}, now ${a.status})` : ''; }).filter(Boolean).join('; ')}.`, cites: [n] }] : []),
    ], gaps: later.map(x => `A later session on ${dateLabel(x.date)} is on the calendar but no transcript was found. That doesn’t mean nothing was said.`), links: [{ label: `${c.name} · Meetings`, kind: 'client', id: c.id, tab: 'meetings' }], looked: [{ what: 'Meetings', detail: `${r.meetings.length} known, ${withContent.length} with content` }, { what: 'Fathom', detail: 'Synced 9:15 AM' }], followUps: ['Which of those is still open?', `What has ${c.contact.split(' ')[0]} asked since then?`] });
  }

  // Client voice
  if (has(q, /ask(ed)?|concern|worr|complain|said|feedback|happy|praise/)) {
    const type = has(q, /concern|worr|complain/) ? 'Concern' : has(q, /happy|praise/) ? 'Praise' : undefined;
    const rows = VOICE.filter(v => v.clientId === c.id && (!type || v.type === type) && (type || v.type !== 'Decision')).sort((a, b) => b.date.localeCompare(a.date));
    if (!rows.length) return base('No evidence', `I couldn’t find any ${type ? type.toLowerCase() + 's' : 'statements like that'} from ${c.name} in the approved sources.`, { gaps: ['Silence isn’t a sign of anything by itself.'], looked: [{ what: 'Gmail, Slack, calls', detail: 'Direct client statements only' }] });
    return base('Answered', `${rows.length} thing${rows.length > 1 ? 's' : ''} ${c.contact.split(' ')[0]} said, newest first:`, { blocks: rows.slice(0, 4).map(v => ({ label: 'Fact' as const, text: `${v.type} · “${v.quote}”`, cites: [cite(cites, `${v.speaker} · ${v.channel}`, v.date, v.sourceId)] })), links: [{ label: `${c.name} · Health`, kind: 'client', id: c.id, tab: 'health' }], looked: [{ what: 'Client voice', detail: 'Direct client words only; never staff or Viktor' }], followUps: ['Is anything they asked still unanswered?'] });
  }

  // Health / how are things
  if (has(q, /how (are|is) (things|it)|health|status|going|attention|risk/)) {
    const a = assessmentFor(c.id); const cat = categoryOf(a, r.lifecycle === 'Onboarding');
    const blocks: Block[] = [{ label: 'Interpretation', text: a.why }];
    Object.values(a.dims).filter(d => d.level === 'worst' || d.level === 'middle').forEach(d => d.drivers.filter(x => x.kind === 'Fact').forEach(x => blocks.push({ label: 'Fact', text: x.text, cites: x.sourceId ? [cite(cites, x.text.slice(0, 40) + '…', x.date, x.sourceId)] : [] })));
    if (a.viktor) blocks.push({ label: 'Fact', text: `Viktor’s Monday ad rating: ${a.viktor.rating.toLowerCase()} (${a.viktor.note}). This is Viktor’s analysis, not the KB’s.` });
    blocks.push({ label: 'Suggestion', text: a.nextStep });
    return base('Answered', `${c.name} is “${cat.category}”: ${cat.causes.join('; ')}.`, { blocks, gaps: a.coverage, links: [{ label: `${c.name} · Health`, kind: 'client', id: c.id, tab: 'health' }], looked: [{ what: 'Health assessment', detail: `Assessed ${dateLabel(a.assessedOn)}` }], followUps: ['What did they ask that we haven’t answered?', 'What’s outstanding?'] });
  }

  // Prep / up to speed
  if (has(q, /up to speed|prep|before (the|my) call|next call|brief/)) {
    const meta = CALL_META.find(m => m.clientId === c.id && m.date >= DEMO_DATE && m.state !== 'Cancelled');
    if (!meta?.brief) return base('No evidence', `${c.name} has no upcoming call on the calendar.`, { links: [{ label: `${c.name} · Now`, kind: 'client', id: c.id, tab: 'now' }] });
    return base('Answered', `Next: ${meta.title} on ${dateLabel(meta.date)} at ${timeLabel(meta.time)} IST.`, { blocks: meta.brief.thirty.map(t => ({ label: 'Fact' as const, text: t })), links: [{ label: 'Open the full call brief', kind: 'call', id: meta.id }], looked: [{ what: 'Call brief', detail: `State: ${meta.state}` }], followUps: ['What did we agree on the last call?'] });
  }

  // Leads
  if (has(q, /lead|inquir|booking|tour|conversion/)) {
    const a = assessmentFor(c.id);
    if (a.dims.leads.level === 'na') return base('Unavailable', `${c.name} isn’t a LeadLock client, so there are no lead outcomes in the KB.`, { gaps: ['Ad performance isn’t connected (paid media is deferred). Viktor’s posts may cover it.'] });
    if (!a.leadNumbers) return base('Unavailable', `${c.name}’s LeadLock data can’t be read yet (access pending), so I won’t guess.`, { gaps: ['Shown as unavailable, never as zero.'] });
    const L = a.leadNumbers;
    return base('Answered', `Last 30 days: ${L.inquiries[0]} inquiries (prior ${L.inquiries[1]}), ${L.tours[0]} tours (prior ${L.tours[1]}), ${L.booked[0]} bookings (prior ${L.booked[1]}).`, { blocks: [{ label: 'Fact', text: `Median first response ${L.firstResponse}; ${L.uncontacted} inquiries uncontacted after 48 h; ${L.stalled} stalled over 14 days.` }, { label: 'Fact', text: `Definitions: ${L.definitions.join('; ')}.` }], links: [{ label: `${c.name} · Health`, kind: 'client', id: c.id, tab: 'health' }], looked: [{ what: 'LeadLock', detail: 'Counted in code, not by the AI' }] });
  }

  // Background
  if (has(q, /what (does|do) .*do|background|who (are|is) (they|this)|about (this|the) (client|business)|tell me about|goal|audience|voice/)) {
    const n = cite(cites, 'Onboarding questionnaire', c.since, c.profileSource);
    const prof = r.profile;
    const f = (s: string, l: string) => prof.find(x => x.section === s)?.facts.find(x => x.label === l)?.value;
    return base('Answered', c.story, { blocks: [{ label: 'Fact', text: `Ideal client: ${c.audience}`, cites: [n] }, { label: 'Fact', text: `What sets them apart: ${c.differentiator}`, cites: [n] }, { label: 'Fact', text: `Goal: ${c.goal}`, cites: [n] }], more: [{ label: 'Fact', text: `Offer: ${f('Offer', 'Packages & pricing')}` }, { label: 'Fact', text: `Voice: ${c.voice} Avoid: ${f('Voice', 'Words to avoid')}` }, { label: 'Fact', text: `People: ${r.contacts.map(x => `${x.name} (${x.role})`).join('; ')}` }], links: [{ label: `${c.name} · Profile`, kind: 'client', id: c.id, tab: 'profile' }], looked: [{ what: 'Client Marketing Profile', detail: `${prof.reduce((s, x) => s + x.facts.length, 0)} facts` }], followUps: ['How are things going with them?', 'What did we agree on the last call?'] });
  }

  // Fallback: search evidence
  const STOP = ['what', 'they', 'their', 'them', 'does', 'did', 'the', 'and', 'for', 'use', 'uses', 'with', 'about', 'have', 'has', 'who', 'how', 'why', 'when', 'this', 'that', 'are', 'was', 'our', 'any'];
  const words = q.toLowerCase().split(/\W+/).filter(w => w.length >= 3 && !STOP.includes(w));
  const hits = EVIDENCE.filter(e => e.clientId === c.id && words.some(w => `${e.title} ${e.excerpt}`.toLowerCase().includes(w.slice(0, 6))));
  if (hits.length) return base('Partial', `I found ${hits.length} source${hits.length > 1 ? 's' : ''} that mention this for ${c.name}, but no maintained fact answers it directly:`, { blocks: hits.slice(0, 3).map(e => ({ label: 'Fact' as const, text: `${e.title}: “${e.excerpt.split('\n')[0].slice(0, 180)}”`, cites: [cite(cites, `${e.kind} · ${e.author}`, e.date, e.id)] })), looked: [{ what: 'Retained excerpts', detail: `${EVIDENCE.filter(e => e.clientId === c.id).length} for ${c.name}` }] });
  return base('No evidence', `I couldn’t find anything about that for ${c.name} in the approved sources. I won’t guess.`, { looked: [{ what: 'Records and excerpts', detail: `${c.name}, all sections you can access` }], followUps: [`What does ${c.name} do?`, 'What’s outstanding?'] });
}

// ---------- Seed conversations ----------
let seeded = false;
export function seed(viewer: string, actions: Action[]) {
  if (seeded || kbLive.meta) return; // the WIA export starts with no (fictional) sample conversations
  seeded = true;
  const q1 = 'What’s outstanding for Bloom Manor?';
  const q2 = 'What does Harbor House do?';
  const a1 = answerQuestion(q1, 'bloom', undefined, viewer, actions);
  const a2 = answerQuestion(q2, 'harbor', undefined, viewer, actions);
  store.set(x => ({
    threads: [...x.threads,
      { id: 't-1', title: 'Bloom: what’s outstanding', clientId: 'bloom', group: 'Today', at: `${DEMO_DATE}T09:48`, messages: [{ role: 'user', text: q1 }, { role: 'assistant', answer: a1, id: 'm-1' }] },
      { id: 't-2', title: 'Harbor background', clientId: 'harbor', group: 'This week', at: `${addDays(DEMO_DATE, -2)}T16:05`, messages: [{ role: 'user', text: q2 }, { role: 'assistant', answer: a2, id: 'm-2' }] },
      { id: 't-3', title: 'Who’s waiting on us?', clientId: 'all', group: 'Older', at: '2026-09-28T11:20', messages: [{ role: 'user', text: 'Which clients are waiting on a reply from us?' }, { role: 'assistant', answer: answerQuestion('Which clients are waiting on a reply from us?', 'all', undefined, viewer, actions), id: 'm-3' }] },
    ],
    pins: [...x.pins,
      { id: 'p-1', title: 'Harbor House background', clientId: 'harbor', answer: a2, pinnedOn: '2026-10-07' },
      { id: 'p-2', title: 'Bloom open items', clientId: 'bloom', answer: a1, pinnedOn: '2026-10-06', changed: 'Sources changed since you pinned this (an action became overdue).' },
    ],
    activeId: x.activeId || 't-1',
  }));
}

// ---------- UI pieces ----------
const STATUS_CLASS: Record<Status, string> = { Answered: 'st-ok', Partial: 'st-partial', 'Need to clarify': 'st-clarify', 'No evidence': 'st-none', Unavailable: 'st-none', Conflict: 'st-partial' };

function AnswerCard({ a, props, onAsk, onPin, pinned, compact }: { a: Answer; props: WorkspaceProps; onAsk: (q: string) => void; onPin?: () => void; pinned?: boolean; compact?: boolean }) {
  const [more, setMore] = useState(false);
  const [copied, setCopied] = useState(false);
  const copy = async () => { if (await copyText(answerToMarkdown(a))) { setCopied(true); setTimeout(() => setCopied(false), 1600); } else props.notify('Clipboard is unavailable in this browser.'); };
  const go = (l: Link) => { if (l.kind === 'client' && l.id) props.openClient(l.id, l.tab); else if (l.kind === 'call' && l.id) props.openCall(l.id); else if (l.kind === 'actions') props.navigate('actions-v3'); else if (l.kind === 'money') props.navigate('money'); };
  const citeLink = (n: number) => { const ci = a.cites.find(x => x.n === n); return <button key={n} className="cite" title={ci?.label} onClick={() => ci?.sourceId && props.showEvidence(ci.sourceId)}>[{n}]</button>; };
  return <div className={`answer-card ${compact ? 'compact' : ''}`}>
    <div className="answer-head"><span className={`answer-status ${STATUS_CLASS[a.status]}`}>{a.status}</span><span className="hint">{a.scope}</span>{a.note && <span className="admin-chip"><Lock size={10} />{a.note}</span>}<button className={`answer-copy ${copied ? 'is-done' : ''}`} onClick={copy} aria-label="Copy this response" title="Copy response with its sources">{copied ? <><Check size={12} />Copied</> : <><Copy size={12} />Copy</>}</button>{onPin && <button className="icon-button pin-btn" aria-label={pinned ? 'Unpin answer' : 'Pin answer'} title={pinned ? 'Unpin' : 'Pin this answer'} onClick={onPin}>{pinned ? <PinOff size={14} /> : <Pin size={14} />}</button>}</div>
    <p className="answer-summary">{a.summary}</p>
    {a.clarify && <div className="clarify-row">{a.clarify.map(c => <button key={c.label} className="pick-chip" onClick={() => onAsk(c.question)}>{c.label}</button>)}</div>}
    {a.blocks.length > 0 && <ul className="answer-blocks">{a.blocks.map((b, i) => <li key={i}><span className={`blk blk-${b.label.toLowerCase()}`}>{b.label}</span><span>{b.text} {b.cites?.map(citeLink)}</span></li>)}</ul>}
    {a.more && a.more.length > 0 && (more ? <ul className="answer-blocks">{a.more.map((b, i) => <li key={i}><span className={`blk blk-${b.label.toLowerCase()}`}>{b.label}</span><span>{b.text}</span></li>)}</ul> : <button className="text-button" onClick={() => setMore(true)}><ChevronDown size={12} />More detail</button>)}
    {a.gaps.length > 0 && <div className="answer-gaps">{a.gaps.map(g => <p key={g}>⚠ {g}</p>)}</div>}
    {a.cites.length > 0 && <ol className="answer-cites">{a.cites.map(ci => <li key={ci.n}><button className="text-button" onClick={() => ci.sourceId ? props.showEvidence(ci.sourceId) : undefined} disabled={!ci.sourceId}>[{ci.n}] {ci.label}{ci.date ? ` · ${dateLabel(ci.date.slice(0, 10))}` : ''}{ci.sourceId && <ArrowUpRight size={10} />}</button></li>)}</ol>}
    {(a.links.length > 0 || a.followUps.length > 0) && <div className="answer-foot">{a.links.map(l => <button key={l.label} className="text-button" onClick={() => go(l)}>{l.label}<ArrowRight size={11} /></button>)}{a.followUps.map(f => <button key={f} className="pick-chip follow" onClick={() => onAsk(f)}>{f}</button>)}</div>}
  </div>;
}

const STEPS = ['Understanding the question…', 'Checking records you can access…', 'Reading the evidence…'];

function useConversation(props: WorkspaceProps) {
  const s = useStore();
  const [thinking, setThinking] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => { seed(props.viewer, props.actions); }, [props.viewer, props.actions]);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  const active = s.threads.find(t => t.id === s.activeId);
  const ask = (text: string, context?: AskContext, scopeOverride?: string | 'all') => {
    if (!text.trim() || thinking) return;
    let threadId = s.activeId;
    if (!active) { threadId = uid('t'); store.set(x => ({ ...x, activeId: threadId, threads: [{ id: threadId, title: text.slice(0, 40), clientId: scopeOverride ?? context?.clientId ?? 'all', group: 'Today', at: nowStamp(), messages: [] }, ...x.threads] })); }
    store.set(x => ({ ...x, threads: x.threads.map(t => t.id === threadId ? { ...t, title: t.messages.length === 0 && (t.title === 'New conversation' || t.title.startsWith('About ')) ? text.slice(0, 40) : t.title, messages: [...t.messages, { role: 'user', text, context }] } : t) }));
    setThinking(1);
    let step = 1;
    const tick = () => { step += 1; if (step <= STEPS.length) { setThinking(step); timer.current = setTimeout(tick, 380); } else {
      const scope = store.get().threads.find(t => t.id === threadId)?.clientId ?? 'all';
      const answer = answerQuestion(text, scope, context, props.viewer, props.actions);
      store.set(x => ({ ...x, threads: x.threads.map(t => t.id === threadId ? { ...t, messages: [...t.messages, { role: 'assistant', answer, id: uid('m') }] } : t) }));
      setThinking(0);
    } };
    timer.current = setTimeout(tick, 380);
  };
  const stop = () => { if (timer.current) clearTimeout(timer.current); setThinking(0); };
  const newThread = (clientId: string | 'all') => { const id = uid('t'); store.set(x => ({ ...x, activeId: id, threads: [{ id, title: 'New conversation', clientId, group: 'Today', at: nowStamp(), messages: [] }, ...x.threads] })); return id; };
  const setScope = (clientId: string | 'all') => store.set(x => ({ ...x, threads: x.threads.map(t => t.id === x.activeId ? { ...t, clientId } : t) }));
  const togglePin = (msgId: string, a: Answer, title: string, clientId: string | 'all') => store.set(x => x.pins.some(p => p.id === msgId) ? { ...x, pins: x.pins.filter(p => p.id !== msgId) } : { ...x, pins: [{ id: msgId, title, clientId: clientId === 'all' ? '' : clientId, answer: a, pinnedOn: DEMO_DATE }, ...x.pins] });
  return { s, active, thinking, ask, stop, newThread, setScope, togglePin };
}

function Messages({ conv, props, compact, onQuote }: { conv: ReturnType<typeof useConversation>; props: WorkspaceProps; compact?: boolean; onQuote?: (text: string) => void }) {
  const [sel, setSel] = useState<{ text: string; x: number; y: number } | null>(null);
  const pick = () => {
    const s = window.getSelection(); const text = s?.toString().trim() || '';
    if (!onQuote || !s || s.rangeCount === 0 || text.length < 3) { setSel(null); return; }
    const node = s.anchorNode instanceof Element ? s.anchorNode : s.anchorNode?.parentElement;
    if (!node?.closest('.answer-card')) { setSel(null); return; }
    const r = s.getRangeAt(0).getBoundingClientRect();
    setSel({ text, x: r.left + r.width / 2, y: r.top });
  };
  useEffect(() => { if (!sel) return; const hide = () => setSel(null); window.addEventListener('scroll', hide, true); return () => window.removeEventListener('scroll', hide, true); }, [sel]);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ block: 'end' }); }, [conv.active?.messages.length, conv.thinking]);
  const t = conv.active;
  if (!t || !t.messages.length) return <EmptyState onAsk={q => conv.ask(q)} />;
  const me = viewerByName(props.viewer).initials;
  return <div className="messages" onMouseUp={pick} onKeyUp={pick}>{sel && <button className="quote-pop" style={{ left: sel.x, top: sel.y }} onMouseDown={e => e.preventDefault()} onClick={() => { onQuote?.(sel.text); setSel(null); window.getSelection()?.removeAllRanges(); }}><MessageSquareQuote size={13} />Add to context</button>}<div className="messages-inner">{t.messages.map((m, i) => m.role === 'user'
    ? <div className="msg-row is-user" key={i}><div className="msg-user">{m.context && <span className={`ctx-chip ${m.context.kind === 'quote' ? 'is-quote' : ''}`}>{m.context.kind === 'quote' ? <><MessageSquareQuote size={11} />{m.context.label}</> : <>About: {m.context.label}</>}</span>}<p>{m.text}</p></div><span className="msg-avatar is-user" aria-hidden="true">{me}</span></div>
    : <div className="msg-row is-assistant" key={m.id}><span className="msg-avatar" aria-hidden="true"><Sparkles size={14} /></span><div className="msg-body"><span className="msg-name">Client 360</span><AnswerCard a={m.answer} props={props} compact={compact} onAsk={q => conv.ask(q)} /></div></div>)}
    {conv.thinking > 0 && <div className="msg-row is-assistant"><span className="msg-avatar is-thinking" aria-hidden="true"><Sparkles size={14} /></span><div className="msg-body"><span className="msg-name">Client 360</span><div className="thinking"><span className="dots"><i /><i /><i /></span>{STEPS[conv.thinking - 1]}<button className="text-button" onClick={conv.stop}><Square size={10} />Stop</button></div></div></div>}<div ref={end} /></div></div>;
}

function EmptyState({ onAsk }: { onAsk: (q: string) => void }) {
  if (kbLive.meta) return <LiveEmptyState onAsk={onAsk} />;
  const cats: [string, string][] = [['Client background', 'What does Bloom Manor do?'], ['Last call', 'What was agreed on the last call with Everly?'], ['Who owes what', 'What’s outstanding for Harbor House?'], ['Find what they said', 'What has Maya asked recently?'], ['How it’s going', 'How are things going with Rosewood?'], ['Before a call', 'Bring me up to speed before the Bloom call'], ['Lead outcomes', 'How are Rosewood’s inquiries converting?'], ['Definitions', 'What does Verified mean?']];
  return <div className="empty-chat"><MessagesSquare size={26} /><h3>Ask about any client you can access</h3><p className="hint">Answers come from the knowledge base, with sources. Client 360 is read-only: it never changes records or sends anything.</p><div className="cat-grid">{cats.map(([c, q]) => <button key={c} onClick={() => onAsk(q)}><strong>{c}</strong><span>{q}</span></button>)}</div></div>;
}

function Composer({ conv, context, clearContext, placeholder }: { conv: ReturnType<typeof useConversation>; context?: AskContext; clearContext?: () => void; placeholder?: string }) {
  const [text, setText] = useState('');
  const send = () => { conv.ask(text, context); setText(''); clearContext?.(); };
  return <div className="composer">{context && <span className={`ctx-chip ${context.kind === 'quote' ? 'is-quote' : ''}`}>{context.kind === 'quote' ? <><MessageSquareQuote size={11} />{context.label}</> : <>About: {context.label}</>}{clearContext && <button aria-label="Remove context" onClick={clearContext}><X size={10} /></button>}</span>}<div className="composer-box"><textarea rows={2} value={text} placeholder={placeholder || 'Ask about a client, a call, an action…'} onChange={e => setText(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }} aria-label="Ask Client 360" /><button className="button button-primary" disabled={!text.trim() || !!conv.thinking} onClick={send} aria-label="Send"><Send size={15} /></button></div><p className="hint">Read-only · answers cite their sources · only you see this conversation</p></div>;
}

function ScopeBar({ conv, viewer, sourcesOpen, toggleSources }: { conv: ReturnType<typeof useConversation>; viewer: string; sourcesOpen?: boolean; toggleSources?: () => void }) {
  const t = conv.active;
  const [relative, setRelative] = useState(false);
  const sections = `Actions · Meetings · Profile · Health · Support${isFinanceAdmin(viewer) ? ' · Finance' : ''}`;
  // Only the client this conversation is about; sources sit behind the info icon; sync time toggles to "x mins ago".
  return <div className="scope-bar">
    <span className="small-label">ABOUT</span>
    <ThemedSelect aria-label="Client this conversation is about" value={t?.clientId || 'all'} onChange={v => t ? conv.setScope(v) : conv.newThread(v)}><option value="all">All clients</option>{CLIENTS.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</ThemedSelect>
    <span className="scope-info"><button type="button" className="icon-button" aria-label="What Client 360 reads" aria-describedby="scope-sources"><Info size={15} /></button><span className="scope-tip" id="scope-sources" role="tooltip"><strong>Answers come from</strong>{sections}<small>Read-only. Sources you can’t access are never used.</small></span></span>
    <button type="button" className="scope-sync" onClick={() => setRelative(v => !v)} title={relative ? 'Show the sync time' : 'Show how long ago'}><RefreshCw size={12} />{relative ? 'Last synced 12 mins ago' : 'Last synced: 9:42 AM'}</button>
    {toggleSources && <button type="button" className={`scope-sources-btn ${sourcesOpen ? 'on' : ''}`} aria-pressed={sourcesOpen} onClick={toggleSources} title="What Client 360 looked at for the latest answer"><PanelRight size={14} />Sources</button>}
  </div>;
}

export default function Client360(props: WorkspaceProps) {
  const conv = useConversation(props);
  const [search, setSearch] = useState('');
  const [openPin, setOpenPin] = useState<PinItem | null>(null);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [quote, setQuote] = useState<AskContext | undefined>(undefined);
  const [exportFor, setExportFor] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const [menuPos, setMenuPos] = useState<{ top: number; left: number } | null>(null);
  useEffect(() => { if (!menuFor) return; const close = () => setMenuFor(null); window.addEventListener('resize', close); document.querySelector('.c360-threads')?.addEventListener('scroll', close); return () => { window.removeEventListener('resize', close); document.querySelector('.c360-threads')?.removeEventListener('scroll', close); }; }, [menuFor]);
  const [confirmDelete, setConfirmDelete] = useState(false);
  useEffect(() => { if (!menuFor) return; const close = (e: PointerEvent) => { if (!(e.target as HTMLElement).closest('.thread-more, .thread-menu')) setMenuFor(null); }; document.addEventListener('pointerdown', close); return () => document.removeEventListener('pointerdown', close); }, [menuFor]);
  const [draft, setDraft] = useState('');
  const saveName = (id: string) => { const title = draft.trim(); if (title) store.set(x => ({ ...x, threads: x.threads.map(y => y.id === id ? { ...y, title } : y) })); setRenaming(null); };
  const groups: Thread['group'][] = ['Today', 'This week', 'Older'];
  const threads = conv.s.threads.filter(t => t.title.toLowerCase().includes(search.toLowerCase()));
  const lastAnswer = [...(conv.active?.messages || [])].reverse().find(m => m.role === 'assistant') as { answer: Answer } | undefined;
  return <div className="view c360-view">
    <header className="c360-head"><p className="c360-eyebrow">Client intelligence</p><div className="c360-title-row"><h1>Client 360</h1><span className="scope-info c360-heading-info"><button type="button" className="icon-button" aria-label="About Client 360" aria-describedby="c360-description"><Info size={17} /></button><span className="scope-tip" id="c360-description" role="tooltip">Ask anything about your clients and get a short, cited answer. Read-only.</span></span></div></header>
    <div className={`c360-shell ${sourcesOpen ? 'with-sources' : ''}`}>
      <aside className="c360-threads">
        <button className="button button-primary new-thread" onClick={() => conv.newThread('all')}><Plus size={14} />New chat</button>
        <label className="thread-search"><Search size={13} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search past chats" /></label>
        {(() => {
          const item = (t: Thread) => <div key={t.id} className={`thread-item ${t.id === conv.s.activeId ? 'active' : ''} ${t.pinned ? 'is-pinned' : ''}`}>{renaming === t.id
            ? <form className="thread-rename" onSubmit={e => { e.preventDefault(); saveName(t.id); }}><input autoFocus value={draft} maxLength={60} aria-label="Chat name" onChange={e => setDraft(e.target.value)} onBlur={() => saveName(t.id)} onKeyDown={e => { if (e.key === 'Escape') { e.preventDefault(); setRenaming(null); } }} /><small>Enter to save · Esc to cancel</small></form>
            : <button onClick={() => store.set(x => ({ ...x, activeId: t.id }))} onDoubleClick={() => { setRenaming(t.id); setDraft(t.title); }}><span>{t.title}</span><small>{t.clientId === 'all' ? 'All clients' : clientById(t.clientId).name}{t.at && <em className="thread-stamp"> · {threadStamp(t)}</em>}</small></button>}{renaming !== t.id && <span className="thread-actions"><button className="icon-button" aria-label={t.pinned ? 'Unpin chat' : 'Pin chat'} title={t.pinned ? 'Unpin chat' : 'Pin chat'} aria-pressed={!!t.pinned} onClick={() => store.set(x => ({ ...x, threads: x.threads.map(y => y.id === t.id ? { ...y, pinned: !y.pinned } : y) }))}>{t.pinned ? <PinOff size={12} /> : <Pin size={12} />}</button><span className="thread-more"><button className={`icon-button ${menuFor === t.id ? 'is-open' : ''}`} aria-label="Chat options" aria-haspopup="menu" aria-expanded={menuFor === t.id} title="Chat options" onClick={e => { const r = e.currentTarget.getBoundingClientRect(); setMenuPos({ top: r.bottom + 4, left: Math.max(8, r.right - 200) }); setMenuFor(menuFor === t.id ? null : t.id); setConfirmDelete(false); setExportFor(null); }}><MoreHorizontal size={14} /></button>
              {menuFor === t.id && menuPos && createPortal(<div className="thread-menu" role="menu" style={{ top: menuPos.top, left: menuPos.left }} onKeyDown={e => { if (e.key === 'Escape') setMenuFor(null); }}>
                {confirmDelete
                  ? <div className="thread-menu-confirm"><p>Delete “{t.title}”? This can’t be undone.</p><div><button className="button button-small button-outline" onClick={() => setConfirmDelete(false)}>Cancel</button><button className="button button-small cp-danger" onClick={() => { store.set(x => ({ ...x, threads: x.threads.filter(y => y.id !== t.id), activeId: x.activeId === t.id ? '' : x.activeId })); setMenuFor(null); props.notify('Chat deleted.'); }}>Delete</button></div></div>
                  : exportFor === t.id ? <><p className="thread-menu-label">EXPORT CHAT</p>
                    <button role="menuitem" autoFocus onClick={async () => { const ok = await copyText(chatToMarkdown(t)); setMenuFor(null); setExportFor(null); props.notify(ok ? 'Chat copied with its sources.' : 'Clipboard is unavailable in this browser.'); }}><Copy size={13} />Copy chat</button>
                    <button role="menuitem" onClick={() => { downloadPdf(t); setMenuFor(null); setExportFor(null); }}><FileDown size={13} />Download PDF</button>
                    <button role="menuitem" onClick={() => { downloadMarkdown(t); setMenuFor(null); setExportFor(null); props.notify('Markdown file downloaded.'); }}><FileText size={13} />Download Markdown</button>
                    <button role="menuitem" className="is-back" onClick={() => setExportFor(null)}><ChevronDown size={13} className="rot" />Back</button></>
                  : <><button role="menuitem" autoFocus onClick={() => { setRenaming(t.id); setDraft(t.title); setMenuFor(null); }}><Pencil size={13} />Rename</button>
                    <button role="menuitem" onClick={() => setExportFor(t.id)}><Download size={13} />Export chat<ChevronDown size={12} className="rot end" /></button>
                    <button role="menuitem" className="is-danger" onClick={() => setConfirmDelete(true)}><Trash2 size={13} />Delete</button></>}
              </div>, document.body)}</span></span>}</div>;
          const pinned = threads.filter(t => t.pinned);
          return <>
            {pinned.length > 0 && <div className="thread-group"><p className="small-label"><Pin size={11} /> PINNED</p>{pinned.map(item)}</div>}
            {groups.map(g => { const ts = threads.filter(t => t.group === g && !t.pinned); return ts.length ? <div className="thread-group" key={g}><p className="small-label">{g.toUpperCase()}</p>{ts.map(item)}</div> : null; })}
            {!threads.length && <p className="hint thread-empty">{search ? 'No chats match your search.' : 'Your past chats appear here.'}</p>}
          </>;
        })()}
        <p className="hint privacy-note"><Lock size={11} /> Only you see your conversations. Admins see usage, not content.</p>
      </aside>
      <section className="c360-main">
        <ScopeBar conv={conv} viewer={props.viewer} sourcesOpen={sourcesOpen} toggleSources={() => setSourcesOpen(v => !v)} />
        <Messages conv={conv} props={props} onQuote={text => setQuote({ kind: 'quote', clientId: conv.active?.clientId === 'all' ? '' : conv.active?.clientId || '', quote: text, label: `“${text.length > 70 ? `${text.slice(0, 67)}…` : text}”` })} />
        <Composer conv={conv} context={quote} clearContext={() => setQuote(undefined)} placeholder={quote ? 'Ask about the selected text…' : undefined} />
      </section>
      {sourcesOpen && <aside className="c360-looked">
        <div className="looked-head"><p className="small-label">WHAT I LOOKED AT</p><button className="icon-button" aria-label="Close sources" onClick={() => setSourcesOpen(false)}><X size={14} /></button></div>
        {lastAnswer ? <>{lastAnswer.answer.looked.map(l => <div key={l.what} className="looked-row"><strong>{l.what}</strong><span className="hint">{l.detail}</span></div>)}{lastAnswer.answer.gaps.length > 0 && <><p className="small-label">OUT OF REACH</p>{lastAnswer.answer.gaps.map(g => <p key={g} className="hint">{g}</p>)}</>}<p className="hint">Never lists anything you don’t have access to.</p></> : <p className="hint">Sources for the latest answer appear here.</p>}
      </aside>}
    </div>
    {openPin && <div className="pin-overlay" role="dialog" aria-label="Pinned answer"><div className="pin-sheet"><div className="answer-head"><strong>{openPin.title}</strong><button className="icon-button" aria-label="Close" onClick={() => setOpenPin(null)}><X size={15} /></button></div>{openPin.changed && <p className="stale-note">{openPin.changed} <button className="text-button" onClick={() => { const a = answerQuestion(openPin.answer.summary.startsWith('Next') ? 'prep' : openPin.title.includes('open') ? 'What’s outstanding?' : 'What does this business do?', openPin.clientId || 'all', undefined, props.viewer, props.actions); store.set(x => ({ ...x, pins: x.pins.map(p => p.id === openPin.id ? { ...p, answer: a, changed: undefined, pinnedOn: DEMO_DATE } : p) })); setOpenPin(null); props.notify('Pinned answer refreshed from current sources.'); }}>Refresh</button></p>}<AnswerCard a={openPin.answer} props={props} onAsk={q => { setOpenPin(null); conv.ask(q); }} /></div></div>}
  </div>;
}

export function Client360Panel(props: WorkspaceProps & { context?: AskContext; close: () => void; openFull: () => void }) {
  const conv = useConversation(props);
  const [ctx, setCtx] = useState<AskContext | undefined>(props.context);
  const [dismissed, setDismissed] = useState(false);
  useEffect(() => { setCtx(props.context); setDismissed(false); }, [props.context]);
  const t = conv.active;
  const mismatch = ctx && t && t.messages.length > 0 && t.clientId !== ctx.clientId && !dismissed;
  return <aside className="c360-panel" role="complementary" aria-label="Client 360">
    <div className="panel-head"><MessagesSquare size={16} /><strong>Client 360</strong><span className="hint">{t ? (t.clientId === 'all' ? 'All clients' : clientById(t.clientId).name) : 'New conversation'}</span><button className="icon-button" aria-label="Open full Client 360" title="Open the full tab" onClick={props.openFull}><Expand size={14} /></button><button className="icon-button" aria-label="Close Client 360" onClick={props.close}><X size={15} /></button></div>
    {mismatch && <div className="switch-note"><p>This conversation is about <strong>{clientById(t!.clientId === 'all' ? ctx!.clientId : t!.clientId).name}</strong>. You opened <strong>{ctx!.label}</strong>.</p><div className="drawer-inline"><button className="button button-small button-primary" onClick={() => { conv.newThread(ctx!.clientId); setDismissed(true); }}>New conversation about it</button><button className="text-button" onClick={() => { conv.setScope(ctx!.clientId); setDismissed(true); }}>Switch this one</button></div></div>}
    {!t && ctx && <p className="hint panel-intro">Starting a conversation about <strong>{ctx.label}</strong>.</p>}
    <Messages conv={conv} props={props} compact />
    <Composer conv={conv} context={ctx} clearContext={() => setCtx(undefined)} placeholder={ctx ? `Ask about ${ctx.label}…` : undefined} />
  </aside>;
}

export function startContextThread(ctx: AskContext) {
  const s = store.get();
  const current = s.threads.find(t => t.id === s.activeId);
  if (!current || !current.messages.length) {
    const id = uid('t');
    store.set(x => ({ ...x, activeId: id, threads: [{ id, title: `About ${ctx.label}`.slice(0, 40), clientId: ctx.clientId, group: 'Today', at: nowStamp(), messages: [] }, ...x.threads.filter(t => t.messages.length || t.id !== x.activeId)] }));
  }
}

export const nextCallLabel = (id: string) => { const c = CALLS.find(x => x.clientId === id && x.date >= DEMO_DATE); return c ? `${c.type} ${dateLabel(c.date)}` : ''; };

// ---------- Copy and export ----------
async function copyText(text: string) { try { await navigator.clipboard.writeText(text); return true; } catch { return false; } }

function answerToMarkdown(a: Answer) {
  const lines = [`**${a.status}** · ${a.scope}`, '', a.summary];
  if (a.blocks.length) lines.push('', ...a.blocks.map(b => `- *${b.label}:* ${b.text}${b.cites?.length ? ` ${b.cites.map(n => `[${n}]`).join('')}` : ''}`));
  if (a.gaps.length) lines.push('', ...a.gaps.map(g => `> ⚠ ${g}`));
  if (a.cites.length) lines.push('', 'Sources:', ...a.cites.map(c => `[${c.n}] ${c.label}${c.date ? ` · ${c.date.slice(0, 10)}` : ''}`));
  return lines.join('\n');
}

function chatToMarkdown(t: Thread) {
  const head = [`# ${t.title}`, `Client 360 · ${t.clientId === 'all' ? 'All clients' : clientById(t.clientId).name} · exported ${dateLabel(DEMO_DATE, { day: 'numeric', month: 'short', year: 'numeric' })}`, ''];
  const body = t.messages.map(m => m.role === 'user'
    ? `## You\n${m.context?.kind === 'quote' ? `> ${m.context.quote}\n\n` : ''}${m.text}`
    : `## Client 360\n${answerToMarkdown(m.answer)}`);
  return [...head, ...body].join('\n\n') + '\n\n---\nRead-only answers from the WIA Client Knowledge Base. Each claim cites its source.\n';
}

const fileName = (t: Thread, ext: string) => `client-360-${t.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}.${ext}`;

function downloadMarkdown(t: Thread) {
  const url = URL.createObjectURL(new Blob([chatToMarkdown(t)], { type: 'text/markdown' }));
  const a = document.createElement('a'); a.href = url; a.download = fileName(t, 'md'); a.click(); URL.revokeObjectURL(url);
}

/** Opens a print-ready copy of the chat; the browser's "Save as PDF" writes the file. */
function downloadPdf(t: Thread) {
  const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const msgs = t.messages.map(m => m.role === 'user'
    ? `<section class="q"><h3>You</h3>${m.context?.kind === 'quote' ? `<blockquote>${esc(m.context.quote || '')}</blockquote>` : ''}<p>${esc(m.text)}</p></section>`
    : `<section class="a"><h3>Client 360 <span>${esc(m.answer.status)} · ${esc(m.answer.scope)}</span></h3><p class="sum">${esc(m.answer.summary)}</p>${m.answer.blocks.length ? `<ul>${m.answer.blocks.map(b => `<li><b>${b.label}</b> ${esc(b.text)}${b.cites?.length ? ` <sup>${b.cites.map(n => `[${n}]`).join('')}</sup>` : ''}</li>`).join('')}</ul>` : ''}${m.answer.gaps.map(g => `<p class="gap">⚠ ${esc(g)}</p>`).join('')}${m.answer.cites.length ? `<ol class="src">${m.answer.cites.map(c => `<li>[${c.n}] ${esc(c.label)}${c.date ? ` · ${c.date.slice(0, 10)}` : ''}</li>`).join('')}</ol>` : ''}</section>`).join('');
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>${esc(fileName(t, 'pdf').replace(/\.pdf$/, ''))}</title><style>
    body{font:13px/1.6 Georgia,serif;color:#1b2838;max-width:720px;margin:40px auto;padding:0 24px}
    header{border-bottom:2px solid #173354;padding-bottom:12px;margin-bottom:24px} header h1{font-size:26px;margin:0} header p{margin:4px 0 0;color:#6e7f98;font:12px Arial,sans-serif}
    section{margin:0 0 18px;padding:14px 16px;border-radius:10px;font-family:Arial,sans-serif} .q{background:#173354;color:#fff;margin-left:20%} .a{border:1px solid #e3e8f1}
    h3{margin:0 0 6px;font-size:11px;letter-spacing:.08em;text-transform:uppercase} h3 span{font-weight:400;letter-spacing:0;text-transform:none;color:#6e7f98;margin-left:6px}
    .sum{font-size:14px} ul{padding-left:18px} li b{font-size:10px;color:#4266b4;margin-right:4px} .gap{color:#8a6a43} .src{font-size:11px;color:#6e7f98;padding-left:18px;border-top:1px dashed #e3e8f1;padding-top:8px}
    blockquote{margin:0 0 8px;padding:6px 10px;border-left:3px solid #b9c8e8;color:#dfe7f8;font-style:italic} footer{margin-top:28px;color:#8592a6;font:11px Arial,sans-serif}
    @media print{body{margin:0}}</style></head><body><header><h1>${esc(t.title)}</h1><p>Client 360 · ${esc(t.clientId === 'all' ? 'All clients' : clientById(t.clientId).name)} · exported ${dateLabel(DEMO_DATE, { day: 'numeric', month: 'short', year: 'numeric' })}</p></header>${msgs}<footer>Read-only answers from the WIA Client Knowledge Base. Each claim cites its source.</footer></body></html>`;
  // A hidden frame avoids pop-up blockers; the browser's print dialog offers "Save as PDF".
  const frame = document.createElement('iframe');
  frame.setAttribute('aria-hidden', 'true');
  Object.assign(frame.style, { position: 'fixed', right: '0', bottom: '0', width: '0', height: '0', border: '0' });
  document.body.appendChild(frame);
  const doc = frame.contentDocument!;
  doc.open(); doc.write(html); doc.close();
  setTimeout(() => { frame.contentWindow?.focus(); frame.contentWindow?.print(); setTimeout(() => frame.remove(), 60000); }, 250);
}

/** Local WIA export: starter questions name the real clients in the snapshot. */
function LiveEmptyState({ onAsk }: { onAsk: (q: string) => void }) {
  const [a, b = a, c = a] = CLIENTS;
  const cats: [string, string][] = a ? [['Client background', `What does ${a.name} do?`], ['Who owes what', `What’s outstanding for ${b.name}?`],
    ['Last call', `What was agreed on the last call with ${c.name}?`], ['Definitions', 'What does Verified mean?']] : [['Definitions', 'What does Verified mean?']];
  return <div className="empty-chat"><MessagesSquare size={26} /><h3>Ask about any client you can access</h3><p className="hint">This preview answers from source records only; nothing is AI-extracted yet, so many answers will be partial.</p><div className="cat-grid">{cats.map(([k, q]) => <button key={k} onClick={() => onAsk(q)}><strong>{k}</strong><span>{q}</span></button>)}</div></div>;
}
