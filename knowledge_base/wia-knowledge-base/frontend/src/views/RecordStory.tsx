import { useMemo, useState } from 'react';
import { AlertTriangle, CalendarDays, CheckCircle2, ChevronDown, Clipboard, Download, History, LifeBuoy, ListChecks, MessageSquare, PencilLine, RefreshCw, Send, ShieldCheck, Sparkles } from 'lucide-react';
import { CALLS, DEMO_DATE, EVENTS, dateLabel, daysBetween, isOutstanding, isOverdue, ownerLabel } from '../data';
import { PROFILE_SCHEMA, type ClientRecord, type Moment, type MomentKind, type SourceLabel, type SupportIssue } from '../records';
import { MILESTONES, MOMENTS } from '../story';
import { WAITING } from '../health';
import { commercialEvents } from './Money';
import { isFinanceAdmin } from '../finance';
import { ThemedSelect } from '../components/ThemedSelect';
import { Badge, Dialog, Empty, Panel, Segmented, SourceLink } from '../components/UI';
import type { Client, EngagementEvent, WorkspaceProps } from '../types';
import './RecordStory.css';

export type RecordProps = WorkspaceProps & { client: Client; record: ClientRecord; engagement: string };

/** Live records say "Not extracted yet" where AI hasn't run; treat that as no value. */
const missing = (v?: string) => !v || v.startsWith('Not extracted') || v === 'Not recorded';
const AI_OFF = 'Not extracted yet: the KB writes this once its AI reading is switched on.';
const fullDate = (d: string) => dateLabel(d, { day: 'numeric', month: 'short', year: 'numeric' });

// ---- History ---------------------------------------------------------------------------------------------------

type Lane = EngagementEvent['lane'];
/** What one ball means on each lane. Every ball is one event after merging, never one raw message or file. */
const LANES: { lane: Lane; ball: string; source: string }[] = [
  { lane: 'Onboarding', ball: 'A setup step done, or the onboarding checklist created', source: 'ClickUp onboarding lists · questionnaire in Drive' },
  { lane: 'Communication', ball: 'One conversation on one day (an email thread or a Slack thread)', source: 'Gmail · the client’s Slack channel' },
  { lane: 'Meetings', ball: 'One meeting: its invite, recording and transcript together', source: 'Calendar · Fathom · Zoom' },
  { lane: 'Commitments', ball: 'A commitment made: a task created or an action agreed', source: 'ClickUp · actions agreed in meetings' },
  { lane: 'Work delivered', ball: 'Work finished that day', source: 'ClickUp tasks done · delivery messages' },
  { lane: 'Commercial', ball: 'An agreement signed or a payment received', source: 'Dubsado · GHL billing (admins only)' },
];
const KIND_TONE: Record<MomentKind, string> = { Milestone: 'gold', Decision: 'blue', 'Client signal': 'green', Commitment: 'neutral', Delivery: 'green', Risk: 'rose' };
const size = (n = 1) => n >= 5 ? 'l' : n >= 2 ? 'm' : 's';
/** One ball on the track: everything in one lane on one day (a week or a month on long ranges). */
type Ball = { key: string; lane: Lane; date: string; label: string; events: EngagementEvent[]; count: number; from?: EngagementEvent['from']; state?: EngagementEvent['state'] };
const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const mondayOf = (date: string) => { const d = new Date(`${date}T12:00:00`); d.setDate(d.getDate() - (d.getDay() + 6) % 7); return iso(d); };

export function HistoryTab(props: RecordProps) {
  const { client, record } = props;
  const [lane, setLane] = useState('all');
  const [sinceCall, setSinceCall] = useState(false);
  const [period, setPeriod] = useState('all');
  const [month, setMonth] = useState(DEMO_DATE.slice(0, 7));
  const [year, setYear] = useState(DEMO_DATE.slice(0, 4));
  const [selected, setSelected] = useState<Ball | null>(null);
  const [allMonths, setAllMonths] = useState(false);
  const admin = isFinanceAdmin(props.viewer);
  const lanes = LANES.filter(l => l.lane !== 'Commercial' || admin);
  const earliest = record.earliestEvidence || DEMO_DATE;
  const lastMeeting = [...record.meetings].filter(m => m.date <= DEMO_DATE).sort((a, b) => b.date.localeCompare(a.date))[0];
  const years = Array.from({ length: Math.max(1, +DEMO_DATE.slice(0, 4) - +earliest.slice(0, 4) + 1) }, (_, i) => String(+DEMO_DATE.slice(0, 4) - i));
  const monthEnd = `${month}-${String(new Date(+month.slice(0, 4), +month.slice(5, 7), 0).getDate()).padStart(2, '0')}`;
  const [rangeStart, rangeEnd] = period === 'month' ? [`${month}-01`, monthEnd] : period === 'year' ? [`${year}-01-01`, `${year}-12-31`] : [earliest, DEMO_DATE];
  const inView = (date: string, l?: Lane) => (lane === 'all' || !l || l === lane) && (!sinceCall || !lastMeeting || date >= lastMeeting.date) && date >= rangeStart && date <= rangeEnd;
  const commercial: EngagementEvent[] = admin ? commercialEvents(client.id).map((e, i) => ({ id: `fin-${i}`, clientId: client.id, date: e.date, lane: 'Commercial', title: e.kind === 'Signed' ? 'Agreement signed' : 'Payment received', detail: `${e.text} · admins only`, sourceId: '' })) : [];
  const events = [...EVENTS.filter(e => e.clientId === client.id), ...commercial].filter(e => inView(e.date, e.lane)).sort((a, b) => a.date.localeCompare(b.date));
  const milestones = MILESTONES.filter(m => m.clientId === client.id && inView(m.date)).sort((a, b) => a.date.localeCompare(b.date));
  const moments = MOMENTS.filter(m => m.clientId === client.id && inView(m.date, m.lane)).sort((a, b) => b.date.localeCompare(a.date));
  const start = new Date(`${rangeStart}T12:00:00`).getTime();
  const span = Math.max(new Date(`${rangeEnd}T12:00:00`).getTime() - start, 1);
  const pos = (date: string) => Math.max(1, Math.min(98, (new Date(`${date}T12:00:00`).getTime() - start) / span * 100));
  const at = (date: string) => `${pos(date)}%`;
  // Milestones close together alternate their labels between two rows so they never overlap.
  const rows = milestones.reduce<number[]>((acc, m, i) => [...acc, i && pos(m.date) - pos(milestones[i - 1].date) < 12 ? 1 - acc[i - 1] : 0], []);
  const months = useMemo(() => {
    const byMonth = new Map<string, EngagementEvent[]>();
    [...events].reverse().forEach(e => byMonth.set(e.date.slice(0, 7), [...(byMonth.get(e.date.slice(0, 7)) || []), e]));
    return [...byMonth.entries()];
  }, [events]);
  const shownMonths = allMonths ? months : months.slice(0, 3);
  const counts = Object.fromEntries(lanes.map(l => [l.lane, events.filter(e => e.lane === l.lane).length]));
  const unit = span / 86_400_000 <= 120 ? 'day' : span / 86_400_000 <= 730 ? 'week' : 'month';
  const balls = useMemo(() => {
    const byKey = new Map<string, Ball>();
    for (const e of events) {
      const date = unit === 'day' ? e.date : unit === 'week' ? mondayOf(e.date) : `${e.date.slice(0, 7)}-15`;
      const key = `${e.lane}|${date}`;
      const b = byKey.get(key) || { key, lane: e.lane, date, events: [], count: 0, label: unit === 'day' ? fullDate(date) : unit === 'week' ? `Week of ${fullDate(date)}` : dateLabel(date, { month: 'long', year: 'numeric' }) };
      b.events.push(e);
      b.count += e.count || 1;
      byKey.set(key, b);
    }
    for (const b of byKey.values()) {
      const client = b.events.some(e => e.from === 'Client' || e.from === 'Both'), wia = b.events.some(e => e.from === 'WIA' || e.from === 'Both');
      b.from = client && wia ? 'Both' : client ? 'Client' : wia ? 'WIA' : undefined;
      b.state = b.events.some(e => e.state === 'missed') ? 'missed' : b.events.every(e => e.state === 'no-transcript') ? 'no-transcript' : undefined;
    }
    return [...byKey.values()];
  }, [events, unit]);
  const picked = new Set(selected?.events.map(e => e.id));

  return <>
    <div className="toolbar history-toolbar"><div className="history-period">
      <Segmented label="History period" value={period} onChange={setPeriod} options={[{ id: 'all', label: 'All time' }, { id: 'month', label: 'Month' }, { id: 'year', label: 'Year' }]} />
      {period === 'month' && <input type="month" className="history-period-input" aria-label="Month" value={month} min={earliest.slice(0, 7)} max={DEMO_DATE.slice(0, 7)} onChange={e => e.target.value && setMonth(e.target.value)} />}
      {period === 'year' && <ThemedSelect aria-label="Year" value={year} onChange={setYear}>{years.map(y => <option key={y} value={y}>{y}</option>)}</ThemedSelect>}
    </div><div className="toolbar-right">{lastMeeting && <button className={`filter-pill ${sinceCall ? '' : 'off'}`} onClick={() => setSinceCall(v => !v)}>{sinceCall ? '✓ ' : ''}Since last call ({dateLabel(lastMeeting.date)})</button>}
      <ThemedSelect aria-label="History lane" value={lane} onChange={setLane}><option value="all">All lanes</option>{lanes.map(l => <option key={l.lane}>{l.lane}</option>)}</ThemedSelect></div></div>

    <Panel title="The shape of the engagement" eyebrow="EVERY THREAD OF THE ACCOUNT ON ONE TIMELINE">
      <div className="story-spine-scroll"><div className="story-spine">
        <div className="story-spine-dates"><span>{fullDate(rangeStart)}</span><span>{period === 'all' ? `Processed through ${fullDate(record.processedThrough)}` : fullDate(rangeEnd)}</span></div>
        <div className="story-lane milestones-lane"><div className="story-lane-label"><strong>Milestones</strong><small>Account turning points</small></div>
          <div className="story-track">{milestones.map((m, i) => <span key={m.id} className={`milestone-mark basis-${m.basis === 'Rule' ? 'rule' : 'kb'} row-${rows[i]}`} style={{ left: at(m.date) }} title={`${fullDate(m.date)} · ${m.label} (${m.basis})`}><i /><em>{m.label}</em></span>)}</div></div>
        {lanes.filter(l => lane === 'all' || l.lane === lane).map((l, i) => <div className="story-lane" key={l.lane}>
          <div className="story-lane-label"><strong>{l.lane}<span>{counts[l.lane]}</span></strong><small>{l.ball}</small></div>
          <div className={`story-track lane-tone-${i}`}>{balls.filter(b => b.lane === l.lane).map(b => <button key={b.key} style={{ left: at(b.date) }}
            className={`story-ball size-${size(b.count)}${b.from ? ` from-${b.from.toLowerCase()}` : ''}${b.state ? ` state-${b.state}` : ''}${selected?.key === b.key ? ' is-selected' : ''}`}
            aria-label={`${b.events[0].title}${b.events.length > 1 ? ` and ${b.events.length - 1} more` : ''}, ${b.label}`} title={`${b.label} · ${b.events[0].title}${b.events.length > 1 ? ` +${b.events.length - 1} more` : ''}`} onClick={() => setSelected(b)} />)}</div>
        </div>)}
      </div></div>
      {selected ? <div className="story-selected"><div className="drawer-inline"><span className="small-label">{selected.lane.toUpperCase()} · {selected.label.toUpperCase()} · {selected.events.length} EVENT{selected.events.length === 1 ? '' : 'S'}</span><button className="text-button" onClick={() => setSelected(null)}>Close</button></div>
        <ul>{selected.events.slice(0, 6).map(e => <li key={e.id}><div><strong>{e.title}</strong><small>{dateLabel(e.date)} · {e.detail}{e.state === 'missed' ? ' · date passed while still open' : ''}</small></div>{e.sourceId && <SourceLink id={e.sourceId} onOpen={props.showEvidence} />}</li>)}</ul>
        {selected.events.length > 6 && <p className="hint">+{selected.events.length - 6} more, highlighted in All activity below.</p>}</div>
        : <p className="hint story-hint">Each ball is everything in one lane on one {unit}; bigger means more happened. Select one to see what it holds.</p>}
      <div className="story-legend">
        <div><span className="story-ball size-s demo" />1 item that {unit}</div><div><span className="story-ball size-m demo" />2–4</div><div><span className="story-ball size-l demo" />5 or more</div>
        <div><span className="story-ball size-s demo from-client" />Client wrote</div><div><span className="story-ball size-s demo from-wia" />Only WIA wrote</div>
        <div><span className="story-ball size-s demo state-no-transcript" />Meeting without transcript</div><div><span className="story-ball size-s demo state-missed" />Date missed</div>
        <div><span className="milestone-mark demo basis-rule"><i /></span>Milestone (rule)</div><div><span className="milestone-mark demo basis-kb"><i /></span>Milestone (KB reading)</div>
      </div>
    </Panel>

    <Panel title="Moments that shaped the account" eyebrow="CHOSEN BY THE KB FROM MEETINGS AND ACTIVITY · EVERY ONE CITED">
      {moments.length ? <div className="moment-list">{moments.map(m => <MomentRow key={m.id} m={m} {...props} />)}</div>
        : MOMENTS.some(m => m.clientId === client.id) ? <Empty title="No moments in this view">Change the period or lane.</Empty>
          : <div className="story-empty"><Sparkles size={18} /><div><strong>Not extracted yet</strong><p>The KB picks the 5–15 events that explain this account from its meeting digests and the activity below, once its AI reading is switched on. The timeline and All activity are complete without it.</p></div></div>}
    </Panel>

    <Panel title="All activity" eyebrow="EVERY EVENT, MERGED AND NEWEST FIRST" action={<span className="hint">{events.length} events</span>}>
      {shownMonths.length ? <div className="activity-months">{shownMonths.map(([m, list]) => <section key={m}><h3>{dateLabel(`${m}-01`, { month: 'long', year: 'numeric' })}<span>{list.length}</span></h3>
        <ul>{list.map(e => <li key={e.id} className={picked.has(e.id) ? 'is-selected' : ''}><span className="activity-date">{dateLabel(e.date)}</span><span className={`activity-lane lane-${e.lane.replace(/\s+/g, '-').toLowerCase()}`}>{e.lane}</span>
          <div><strong>{e.title}</strong><small>{e.detail}</small></div>
          {e.count && e.count > 1 ? <span className="activity-count">{e.count}</span> : <span />}
          {e.state === 'missed' ? <Badge tone="rose" dot={false}>Date missed</Badge> : e.state === 'no-transcript' ? <Badge tone="neutral" dot={false}>No transcript</Badge> : <span />}
          {e.sourceId ? <SourceLink id={e.sourceId} onOpen={props.showEvidence} /> : <span />}</li>)}</ul></section>)}
        {months.length > 3 && <button className="text-button" onClick={() => setAllMonths(v => !v)}><ChevronDown size={13} />{allMonths ? 'Show the last 3 months' : `Show ${months.length - 3} earlier month${months.length - 3 === 1 ? '' : 's'}`}</button>}</div>
        : <Empty title="No events in this view">A gap means no records in that period, not that nothing happened.</Empty>}
    </Panel>
    <div className="note-box"><History size={17} /><p>Client since {record.engagements[0]?.start ? fullDate(record.engagements.map(e => e.start).sort()[0]) : 'not recorded'}; earliest evidence {fullDate(earliest)}; processed through {fullDate(record.processedThrough)}. Each ball merges what belongs together (a thread’s messages that day, a meeting’s invite and recording). A gap means no records in that period, not that nothing happened.</p></div>
  </>;
}

function MomentRow({ m, ...props }: { m: Moment } & RecordProps) {
  return <article className="moment-row">
    <div className="moment-date">{dateLabel(m.date)}<small>{m.date.slice(0, 4)}</small></div>
    <div className="moment-node"><span className={`tone-${KIND_TONE[m.kind]}`} /></div>
    <div className="moment-copy"><div className="drawer-inline"><Badge tone={KIND_TONE[m.kind] as never} dot={false}>{m.kind}</Badge><span className="hint">{m.lane}</span></div><h3>{m.title}</h3><p>{m.why}</p></div>
    <div className="moment-sources">{m.sourceIds.length ? m.sourceIds.map(id => <SourceLink key={id} id={id} onOpen={props.showEvidence} />) : <span className="hint">From activity</span>}</div>
  </article>;
}

// ---- Handover brief --------------------------------------------------------------------------------------------

/** WIA's usual scope per engagement type. The signed scope (Stage 3) replaces it per client. */
const USUAL_SCOPE: Record<string, string[]> = {
  Elevate: ['Google and Meta ads run by WIA', 'Landing page and inquiry journey', 'Monthly strategy call', 'Monthly performance report'],
  LeadLock: ['Inquiry follow-up by text and email, set up and maintained', 'Tour-booking calendar', 'CRM handoff and setup', 'Regular LeadLock review'],
  'Google Search Accelerator': ['Weekly group office hours', 'Programme lessons and templates', 'The member runs their own campaigns; WIA reviews'],
  'Meta Ads Accelerator': ['Weekly group office hours', 'Programme lessons and templates', 'The member runs their own campaigns; WIA reviews'],
};
// Live engagement types come from the ClickUp space name ("ELEVATE Clients"), so match by name.
const scopeFor = (type: string) => Object.entries(USUAL_SCOPE).find(([k]) => type.toLowerCase().includes(k.toLowerCase()))?.[1] || [];
type Origin = 'From the record' | 'KB draft' | 'Record + KB reading';
type Line = { text: string; sourceId?: string; tone?: 'warn' | 'muted' };

export function HandoverBrief(props: RecordProps) {
  const { client, record } = props;
  const [stamp, setStamp] = useState(DEMO_DATE);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<Set<number>>(new Set());
  const open = props.actions.filter(a => a.clientId === client.id && isOutstanding(a)).sort((a, b) => Number(isOverdue(b)) - Number(isOverdue(a)) || (a.due || '9999').localeCompare(b.due || '9999'));
  const past = record.meetings.filter(m => m.date <= DEMO_DATE).sort((a, b) => b.date.localeCompare(a.date));
  const next = CALLS.filter(c => c.clientId === client.id && c.date >= DEMO_DATE).sort((a, b) => `${a.date}${a.time}`.localeCompare(`${b.date}${b.time}`))[0];
  const owe = (side: 'WIA' | 'Client'): Line[] => { const rows = open.filter(a => a.side === side); return rows.length ? [...rows.slice(0, 5).map(a => ({ text: `${a.title} · ${ownerLabel(a.owner)} · ${a.due ? dateLabel(a.due) : 'no date'}${isOverdue(a) ? ' · overdue' : ''}`, tone: isOverdue(a) ? 'warn' as const : undefined, sourceId: a.sourceId })), ...(rows.length > 5 ? [{ text: `+${rows.length - 5} more in Commitments`, tone: 'muted' as const }] : [])] : [{ text: 'Nothing open.', tone: 'muted' }]; };
  const agreements = past.flatMap(m => m.decisions.map(d => ({ text: `${d} (${m.type}, ${dateLabel(m.date)})`, sourceId: m.sourceId }))).slice(0, 6);
  const waiting = WAITING.filter(w => w.clientId === client.id);
  const support = record.support.filter(s => s.state !== 'Resolved');
  const watch: Line[] = [
    ...open.filter(isOverdue).map(a => ({ text: `Overdue: ${a.title} (${ownerLabel(a.owner)}, due ${dateLabel(a.due)})`, tone: 'warn' as const, sourceId: a.sourceId })),
    ...waiting.map(w => ({ text: `${w.from}’s ${dateLabel(w.date)} ${w.channel === 'Gmail' ? 'email' : 'message'} is waiting for our reply (${w.businessDays} business day${w.businessDays === 1 ? '' : 's'})`, tone: 'warn' as const, sourceId: w.sourceId })),
    ...support.map(s => ({ text: `Open support issue: ${s.title} (${s.state.toLowerCase()})` })),
    ...props.actions.filter(a => a.clientId === client.id && a.conflict).map(a => ({ text: `Deadline conflict on “${a.title}”` })),
    ...(record.sensitivities || []).map(s => ({ text: s.text, sourceId: s.sourceId })),
  ];
  const gaps: Line[] = [...record.sources.filter(s => ['Blocked', 'Partial', 'Not linked'].includes(s.state)).map(s => ({ text: `${s.source}: ${s.note || s.state}` })), { text: `Nothing before ${fullDate(record.earliestEvidence)}.` }];
  const sections: { title: string; origin: Origin; note?: string; groups: { label?: string; lines: Line[] }[] }[] = [
    { title: 'The account in brief', origin: 'KB draft', note: record.narrative.status === 'Approved' ? `Approved by ${record.narrative.approvedBy} · ${dateLabel(record.narrative.approvedOn)}` : `Draft · ${record.narrative.status.toLowerCase()}`,
      groups: [{ lines: missing(client.story) ? [{ text: AI_OFF, tone: 'muted' }] : [{ text: client.story }, { text: client.summary }] }] },
    { title: 'What we do for them', origin: 'From the record', groups: [
      { label: 'Engagements', lines: record.engagements.map(e => ({ text: `${e.type}${e.programme ? ` (${e.programme})` : ''} · since ${e.start ? fullDate(e.start) : 'not recorded'}${e.phase ? ` · ${e.phase}` : ''}` })) },
      { label: 'Usually included · confirm against the signed agreement', lines: [...new Set(record.engagements.flatMap(e => scopeFor(e.type)))].map(text => ({ text })) },
      { label: 'Rhythm', lines: record.cadence?.length ? record.cadence.map(text => ({ text })) : [{ text: 'No recurring meetings found yet.', tone: 'muted' }] },
      { label: 'WIA team', lines: record.team.length ? record.team.map(t => ({ text: `${t.name} · ${t.role}` })) : [{ text: 'Not confirmed in the KB.', tone: 'muted' }] },
    ] },
    { title: 'Where things stand', origin: 'Record + KB reading', groups: [
      { label: 'Current focus', lines: missing(client.focus) ? [{ text: AI_OFF, tone: 'muted' }] : [{ text: client.focus }] },
      ...(record.onboarding ? [{ label: 'Onboarding', lines: [{ text: `${record.onboarding.phase} · ${record.onboarding.steps.filter(s => s.done).length} of ${record.onboarding.steps.length} steps done; waiting on the client: ${record.onboarding.steps.filter(s => !s.done && s.side === 'Client').map(s => s.label).join(', ') || 'nothing'}` }] }] : []),
      { label: 'Last meeting', lines: past[0] ? [{ text: `${past[0].title} · ${fullDate(past[0].date)}${past[0].summary ? `. ${past[0].summary}` : ''}`, sourceId: past[0].sourceId }] : [{ text: 'No meetings recorded.', tone: 'muted' }] },
      { label: 'Next meeting', lines: next ? [{ text: `${next.type} · ${fullDate(next.date)} · host ${next.host}` }] : [{ text: 'None booked.', tone: 'muted' }] },
    ] },
    { title: 'What’s owed', origin: 'From the record', groups: [{ label: `WIA owes (${open.filter(a => a.side === 'WIA').length})`, lines: owe('WIA') }, { label: `Client owes (${open.filter(a => a.side === 'Client').length})`, lines: owe('Client') }] },
    { title: 'Agreements still in force', origin: 'Record + KB reading', groups: [{ lines: agreements.length ? agreements : [{ text: 'No decisions recorded from meetings yet.', tone: 'muted' }] }] },
    { title: 'People and how to work with them', origin: 'Record + KB reading', groups: [
      { label: 'Client side', lines: record.contacts.length ? record.contacts.map(c => ({ text: `${c.name} · ${c.role}${c.email && !c.email.startsWith('Not') ? ` · ${c.email}` : ''}${c.note ? `. ${c.note}` : ''}` })) : [{ text: 'No approved contacts.', tone: 'muted' }] },
    ] },
    { title: 'Watch-outs', origin: 'Record + KB reading', groups: [{ lines: watch.length ? watch : [{ text: 'Nothing flagged.', tone: 'muted' }] }] },
    { title: 'What this brief can’t tell you', origin: 'From the record', groups: [{ lines: gaps }] },
  ];
  const checklist = [
    `Ask to join ${record.links.slack || 'the client’s Slack channel'}`,
    `Get access to the Drive folder (${record.links.drive || 'not linked'})`,
    `Get added to the ClickUp list (${record.links.clickup || 'not linked'})`,
    ...(record.links.leadlock ? [`Get a LeadLock login for ${record.links.leadlock}`] : []),
    ...(record.contacts[0] ? [`Introduce yourself to ${record.contacts[0].name}`] : []),
    ...(past[0] ? [`Read the last meeting (${dateLabel(past[0].date)}) in Meetings`] : []),
    ...(next ? [`Join the next call (${dateLabel(next.date)})`] : []),
  ];
  const md = `# ${client.name} · Handover brief\n\nBuilt ${dateLabel(stamp)} · account owner ${record.owner || 'unassigned'}\n\n${sections.map(s => `## ${s.title}\n${s.groups.map(g => `${g.label ? `**${g.label}**\n` : ''}${g.lines.map(l => `- ${l.text}`).join('\n')}`).join('\n')}`).join('\n\n')}\n\n## Before you start\n${checklist.map(c => `- [ ] ${c}`).join('\n')}\n`;
  const copy = async () => { try { await navigator.clipboard.writeText(md); props.notify('Handover brief copied.'); } catch { props.notify('Clipboard access is unavailable in this browser.'); } };
  const download = () => { const url = URL.createObjectURL(new Blob([md], { type: 'text/markdown' })); const a = document.createElement('a'); a.href = url; a.download = `${client.id}-handover-${stamp}.md`; a.click(); URL.revokeObjectURL(url); };
  const rebuild = () => { setBusy(true); window.setTimeout(() => { setBusy(false); setStamp(DEMO_DATE); props.notify('Rebuilt from the current record. KB-drafted parts keep their approval state.'); }, 700); };
  const since = record.changes.filter(c => c.date >= stamp).length;
  return <div className="handover-layout">
    <Panel className="handover-main" title="Take over this account without a catch-up call" eyebrow={`HANDOVER BRIEF · BUILT ${fullDate(stamp).toUpperCase()}`} action={<div className="drawer-inline">
      <button className="button button-outline button-small" disabled={busy} onClick={rebuild}><RefreshCw size={14} className={busy ? 'spin' : ''} />{busy ? 'Rebuilding…' : 'Rebuild'}</button>
      <button className="button button-outline button-small" onClick={copy}><Clipboard size={14} />Copy</button>
      <button className="button button-outline button-small" onClick={download}><Download size={14} />Download</button>
      <button className="button button-outline button-small" onClick={() => props.notify('Send on Slack opens the review-before-send screen in the real app. Preview only: nothing is posted.')}><Send size={14} />Send on Slack</button></div>}>
      <div className="handover-intro"><ShieldCheck size={24} /><p>For whoever takes over {client.name}: what we do for them, where it stands, what’s owed, and what to watch. Each section says where it comes from. Parts marked <strong>From the record</strong> are rebuilt exactly from the data; <strong>KB draft</strong> parts are written by the KB and approved by the account owner.</p></div>
      {since > 0 && <p className="handover-stale"><AlertTriangle size={13} />{since} change{since === 1 ? '' : 's'} on the record since this was built. Rebuild to include them.</p>}
      <div className="handover-sections">{sections.map((s, i) => <section key={s.title}><span>{String(i + 1).padStart(2, '0')}</span><div>
        <div className="handover-head"><h3>{s.title}</h3><em className={`origin origin-${s.origin === 'From the record' ? 'record' : s.origin === 'KB draft' ? 'kb' : 'mixed'}`}>{s.origin}</em>{s.note && <small className="hint">{s.note}</small>}</div>
        {s.groups.map((g, j) => <div className="handover-group" key={j}>{g.label && <p className="small-label">{g.label.toUpperCase()}</p>}<ul>{g.lines.map((l, k) => <li key={k} className={l.tone ? `tone-${l.tone}` : ''}>{l.text}{l.sourceId && <SourceLink id={l.sourceId} onOpen={props.showEvidence} />}</li>)}</ul></div>)}
      </div></section>)}</div>
    </Panel>
    <aside className="handover-side">
      <Panel title="Before you start" eyebrow="FIRST WEEK ON THE ACCOUNT"><ul className="handover-checklist">{checklist.map((c, i) => <li key={c}><label><input type="checkbox" checked={done.has(i)} onChange={() => setDone(d => { const n = new Set(d); if (n.has(i)) n.delete(i); else n.add(i); return n; })} />{c}</label></li>)}</ul>
        <p className="hint">Ticks are for you only; they aren’t saved to the record.</p></Panel>
      <Panel title="How this brief is built" eyebrow="SOURCES"><ul className="handover-howto">
        <li><strong>From the record</strong> engagements, team, open actions, meetings and coverage, re-read on every rebuild.</li>
        <li><strong>KB draft</strong> the account summary and focus, drafted after calls and approved by the account owner.</li>
        <li><strong>Record + KB reading</strong> record facts plus what the KB read in calls and email: decisions still in force, preferences, sensitive topics.</li></ul></Panel>
    </aside>
  </div>;
}

// ---- Support ---------------------------------------------------------------------------------------------------

const STATE_TONE: Record<SupportIssue['state'], string> = { Open: 'amber', 'Waiting on client': 'blue', Resolved: 'green', Unknown: 'neutral' };
const median = (xs: number[]) => { if (!xs.length) return null; const s = [...xs].sort((a, b) => a - b); return s[Math.floor(s.length / 2)]; };

export function SupportTab(props: RecordProps) {
  const { record } = props;
  const [showResolved, setShowResolved] = useState(false);
  const [openTimeline, setOpenTimeline] = useState<string | null>(null);
  const openIssues = record.support.filter(s => s.state !== 'Resolved').sort((a, b) => a.raised.localeCompare(b.raised));
  const resolved = record.support.filter(s => s.state === 'Resolved').sort((a, b) => (b.resolved || b.raised).localeCompare(a.resolved || a.raised));
  const toFix = median(resolved.filter(s => s.resolved).map(s => daysBetween(s.raised, s.resolved!)));
  const live = !record.support.length && record.supportCoverage.startsWith('Not extracted');
  const stats = [
    { n: openIssues.filter(s => s.state === 'Open').length, label: 'Open', tone: 'amber' },
    { n: openIssues.filter(s => s.state === 'Waiting on client').length, label: 'Waiting on client', tone: 'blue' },
    { n: resolved.filter(s => daysBetween(s.resolved || s.raised) <= 90).length, label: 'Fixed in the last 90 days', tone: 'green' },
    { n: toFix === null ? '–' : `${toFix} d`, label: 'Typical time to fix', tone: 'neutral' },
    { n: openIssues.filter(s => (s.repeats || 0) >= 2).length, label: 'Keep coming back', tone: 'rose' },
  ];
  const issue = (s: SupportIssue) => <article className={`support-card state-${s.state.replace(/\s+/g, '-').toLowerCase()}`} key={s.id}>
    <div className="support-card-head"><div><div className="drawer-inline"><span className="support-area">{s.area}</span><Badge tone={STATE_TONE[s.state] as never} dot={false}>{s.state}</Badge>{(s.repeats || 0) >= 2 && <span className="row-flag flag-amber"><RefreshCw size={10} />{s.repeats}× in 30 days</span>}</div>
      <h3>{s.title}</h3>
      <p className="hint">Raised by {s.by}{s.channel ? ` via ${s.channel}` : ''} · {fullDate(s.raised)} · owner {s.owner} · {s.state === 'Resolved' && s.resolved ? `fixed in ${daysBetween(s.raised, s.resolved)} day${daysBetween(s.raised, s.resolved) === 1 ? '' : 's'}` : `${daysBetween(s.raised)} days open`}</p></div>
      {s.actionId && <button className="button button-small button-outline" onClick={() => props.navigate('actions-v3')}><ListChecks size={13} />Fix in Action Hub</button>}</div>
    <p className="support-latest"><strong>{s.state === 'Resolved' ? 'Resolved' : 'Latest'}:</strong> {s.latest}</p>
    {s.evidence && <p className="support-evidence"><CheckCircle2 size={12} />{s.evidence}</p>}
    {s.state === 'Resolved' && !s.evidence && <p className="support-evidence missing"><AlertTriangle size={12} />Marked resolved without evidence of the fix.</p>}
    {s.timeline?.length ? <><button className="text-button" onClick={() => setOpenTimeline(openTimeline === s.id ? null : s.id)}><ChevronDown size={13} />{openTimeline === s.id ? 'Hide' : 'Show'} what happened ({s.timeline.length})</button>
      {openTimeline === s.id && <ol className="support-timeline">{s.timeline.map((t, i) => <li key={i}><span>{dateLabel(t.date)}</span><p>{t.text}</p>{t.sourceId && <SourceLink id={t.sourceId} onOpen={props.showEvidence} />}</li>)}</ol>}</> : null}
  </article>;
  return <>
    <div className="coverage-banner"><LifeBuoy size={15} /><p>{record.supportCoverage} <strong>No issues listed doesn’t mean there are no problems.</strong></p></div>
    <div className="support-stats">{stats.map(s => <div key={s.label} className={`tone-${s.tone}`}><strong>{s.n}</strong><span>{s.label}</span></div>)}</div>
    <Panel title="Open issues" eyebrow="WHAT’S BROKEN OR BEING FIXED">
      {openIssues.length ? <div className="support-cards">{openIssues.map(issue)}</div>
        : live ? <div className="story-empty"><Sparkles size={18} /><div><strong>Not extracted yet</strong><p>The KB finds support issues in the client’s email and Slack once its AI reading is switched on. Until then nothing is listed here.</p></div></div>
          : <Empty title="No open issues">Nothing broken or waiting on a fix, within the sources above.</Empty>}
    </Panel>
    {resolved.length > 0 && <Panel title="Resolved" eyebrow="FIXED, WITH EVIDENCE" action={<button className="text-button" onClick={() => setShowResolved(v => !v)}><ChevronDown size={13} />{showResolved ? 'Hide' : `Show ${resolved.length}`}</button>}>
      {showResolved ? <div className="support-cards">{resolved.map(issue)}</div> : <p className="hint">{resolved.length} resolved issue{resolved.length === 1 ? '' : 's'}; the latest was fixed {dateLabel(resolved[0].resolved || resolved[0].raised)}.</p>}</Panel>}
    <div className="note-box"><MessageSquare size={17} /><p><strong>What counts as a support issue:</strong> something WIA set up or manages that isn’t working: a form or follow-up, the booking calendar, tracking, the domain, a login, a page. New work goes to Commitments; a question goes to Now. An issue is resolved only with evidence the fix worked.</p></div>
  </>;
}

// ---- Profile ---------------------------------------------------------------------------------------------------

const LABEL_TONE: Record<SourceLabel, string> = { 'Documented client fact': 'fact', 'Voice of customer': 'voc', 'Strategic interpretation': 'interp', 'Ads data': 'ads', 'WIA benchmark': 'bench' };
const inEngagement = (e: string | undefined, selected: string) => selected === 'all' || !e || e === selected;

export function ProfileSections(props: RecordProps) {
  const { record } = props;
  const [proposing, setProposing] = useState<string | null>(null);
  const factsFor = (section: string, label: string) => record.profile.find(s => s.section === section)?.facts.filter(f => f.label === label && !missing(f.value) && inEngagement(f.engagement, props.engagement)) || [];
  const fields = PROFILE_SCHEMA.flatMap(s => s.fields.map(f => ({ section: s.section, ...f, facts: factsFor(s.section, f.label) })));
  const filled = fields.filter(f => f.facts.length);
  const unreviewed = filled.filter(f => f.facts.some(x => x.sourceNote?.includes('not reviewed'))).length;
  const md = PROFILE_SCHEMA.map(s => `## ${s.section}\n${s.fields.map(f => `- **${f.label}:** ${factsFor(s.section, f.label).map(x => x.value).join(' / ') || 'not in the record yet'}`).join('\n')}`).join('\n\n');
  const copy = async () => { try { await navigator.clipboard.writeText(`# ${props.client.name} · Client Marketing Profile\n\n${md}\n`); props.notify('Profile copied for drafting.'); } catch { props.notify('Clipboard access is unavailable in this browser.'); } };
  return <div className="profile-sections">
    <div className="profile-completeness"><div><strong>{filled.length} of {fields.length}</strong><span>profile fields filled</span></div>
      <div className="profile-meter" aria-hidden="true"><i style={{ width: `${filled.length / fields.length * 100}%` }} /></div>
      <p className="hint">{fields.length - filled.length ? `Missing: ${fields.filter(f => !f.facts.length).map(f => f.label).join(', ')}.` : 'Every field has a value.'}{unreviewed ? ` ${unreviewed} filled from questionnaire answers that nobody has reviewed yet.` : ''}</p>
      <button className="button button-small button-outline" onClick={copy}><Clipboard size={13} />Copy for drafting</button></div>
    {PROFILE_SCHEMA.map(sec => { const rows = fields.filter(f => f.section === sec.section); return <Panel key={sec.section} title={sec.section} eyebrow="CLIENT MARKETING PROFILE" action={<span className="hint">{rows.filter(r => r.facts.length).length} of {rows.length}</span>}>
      <div className="fact-list">{rows.map(r => <div className={`fact-row${r.facts.length ? '' : ' is-empty'}`} key={r.label}>
        <div className="fact-head"><h3>{r.label}</h3>{r.facts.slice(0, 1).map(f => <span key="t" className={`fact-tag tag-${LABEL_TONE[f.tag]}`}>{f.tag}</span>)}{r.facts.map(f => f.engagement && <span key={f.engagement} className="service-label">{f.engagement}</span>)}</div>
        {r.facts.length ? r.facts.map((f, i) => <div key={i}><p>{f.value}</p><div className="drawer-inline">{f.sourceId ? <SourceLink id={f.sourceId} onOpen={props.showEvidence} /> : <span className="hint">{f.sourceNote}</span>}{f.sourceId && f.sourceNote && <span className="hint">{f.sourceNote}</span>}<button className="text-button" onClick={() => setProposing(`${sec.section} · ${r.label}`)}><PencilLine size={11} />Propose a correction</button></div></div>)
          : <div className="fact-empty"><p>Not in the record yet <span className="hint">· {r.hint}</span></p><button className="text-button" onClick={() => props.notify(`“${r.label}” added to the questions for the next call with ${props.client.name}. Preview only.`)}><CalendarDays size={11} />Ask on the next call</button></div>}
      </div>)}</div>
    </Panel>; })}
    {proposing && <Dialog title="Propose a correction" subtitle={proposing} onClose={() => setProposing(null)}><form className="form-stack" onSubmit={e => { e.preventDefault(); setProposing(null); props.notify('Proposal sent to a resolver. The current value stays until it’s applied.'); }}><label>Correct value<textarea rows={3} required /></label><label>Where is this from?<input placeholder="e.g. 'Sarah said this on the Oct 9 call'" /></label><button className="button button-primary" type="submit"><Send size={14} />Send proposal</button></form></Dialog>}
  </div>;
}

