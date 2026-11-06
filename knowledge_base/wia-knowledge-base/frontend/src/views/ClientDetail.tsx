import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, ArrowRight, ArrowUpRight, BellDot, Building2, CalendarCheck, CalendarDays, Check, Circle, FileCheck, FileText, FolderOpen, Hash, HeartPulse, History, LifeBuoy, Link2, ListChecks, Lock, Mail, MessageSquare, NotebookPen, PencilLine, RefreshCw, Send, Sparkles, TrendingUp, UserRound, Video, X } from 'lucide-react';
import { CALLS, DEMO_DATE, addDays, EVIDENCE, clientById, dateLabel, daysBetween, isOutstanding, isOverdue, timeLabel } from '../data';
import { COMMS, recordFor, type ClientRecord } from '../records';
import { Avatar, Badge, Empty, Panel, Segmented, SourceLink } from '../components/UI';
import ClientConnections from '../components/ClientConnections';
import { ActionRows, SlackNotifyDialog, type NotifyContext } from './Actions';
import { EngagementChips, LifecycleChip } from './Clients';
import { CommitmentHistory } from './CommitmentHistory';
import { isFinanceAdmin } from '../finance';
import { WAITING } from '../health';
import { coverById, savedCoverId } from '../clientCovers';
import ClientDetailsEditor from '../components/ClientDetailsEditor';
import ClientMeetings from '../components/ClientMeetings';
import LeadsTab from './LeadsTab';
import { HandoverBrief, HistoryTab, ProfileSections, SupportTab } from './RecordStory';
import type { Action, Client, ClientTab, SourceKind, WorkspaceProps } from '../types';

type Props = WorkspaceProps & { client: Client; record: ClientRecord; engagement: string };
const nextCallFor = (id: string) => CALLS.filter(c => c.clientId === id && c.date >= DEMO_DATE).sort((a, b) => `${a.date}${a.time}`.localeCompare(`${b.date}${b.time}`))[0];
const inEngagement = (e: string | undefined, selected: string) => selected === 'all' || !e || e === selected;

export default function ClientDetail(props: WorkspaceProps & { id: string; tab: ClientTab; addAction?: (action: Action) => void }) {
  const client = clientById(props.id);
  const record = recordFor(client.id);
  const [engagement] = useState('all');
  // Read on every render: the client editor saves the cover and re-renders the app.
  const cover = coverById(savedCoverId(client.id, client.coverId));
  const [editorOpen, setEditorOpen] = useState(false);
  const open = props.actions.filter(a => a.clientId === client.id && isOutstanding(a));
  const openSupport = record.support.filter(s => s.state !== 'Resolved').length;
  const tabs: { id: ClientTab; label: string; count?: number; soon?: boolean; admin?: boolean }[] = [
    { id: 'now', label: 'Now' }, { id: 'profile', label: 'Profile' }, { id: 'commitments', label: 'Commitments', count: open.length }, { id: 'meetings', label: 'Meetings', count: record.meetings.length },
    { id: 'history', label: 'History' }, { id: 'brief', label: 'Handover brief' }, { id: 'support', label: 'Support', count: openSupport }, { id: 'leads', label: 'Leads' },
    { id: 'health', label: 'Health', soon: true }, { id: 'money', label: 'Invoices & terms', soon: true },
    ...(client.type === 'accelerator' ? [{ id: 'attendance' as ClientTab, label: 'Attendance' }] : []),
    { id: 'sources', label: 'Accounts & sources' },
  ];
  const quick = [
    { id: 'slack', logo: '/logos/slack_glass.png', label: 'Slack', destination: record.links.slack },
    { id: 'drive', logo: '/logos/google_drive_glass.png', label: 'Google Drive', destination: record.links.drive },
    { id: 'clickup', logo: '/logos/clickup_glass.png', label: 'ClickUp', destination: record.links.clickup },
    { id: 'leadlock', logo: '/logos/leadlock_glass.png', label: 'LeadLock', destination: record.links.leadlock },
  ];
  const p: Props = { ...props, client, record, engagement };
  const tabIcons = { now: Sparkles, profile: UserRound, history: History, brief: FileText, commitments: ListChecks, meetings: Video, health: HeartPulse, support: LifeBuoy, leads: TrendingUp, money: FileCheck, attendance: CalendarCheck, sources: Link2 };
  const firstEngagement = record.engagements.map(e => e.start).filter(Boolean).sort()[0] || client.since;
  const fullDate = (value?: string) => value ? dateLabel(value, { day: 'numeric', month: 'short', year: 'numeric' }) : 'Not recorded';
  return <div className="view client-detail">
    <section className="client-cover" aria-label={`${client.name} client record`}>
      <img className="client-cover-image" key={cover.id} src={cover.image} alt="" style={{ objectPosition: cover.position }} onError={event => { event.currentTarget.style.visibility = 'hidden'; }} />
      <button className="edit-client-cover" aria-label={`Edit cover for ${client.name}`} title="Change the cover, logo and client details" onClick={() => setEditorOpen(true)}><PencilLine size={14} /><span>Edit cover</span></button>
      <div className="client-cover-content"><Avatar client={client} />
        <div className="cover-identity"><h1>{client.name}</h1><p className="cover-location">{client.category || 'Client'}{client.location && ` · ${client.location}`}</p>
          <div className="portfolio-chips"><LifecycleChip id={client.id} /><EngagementChips id={client.id} /></div>
          <dl className="cover-client-facts"><div><UserRound size={16} /><div><dt>Account owner</dt><dd>{record.owner || 'Unassigned'}</dd></div></div><div><Building2 size={16} /><div><dt>{client.category || 'Business'}</dt><dd>{client.location || 'Location not recorded'}</dd></div></div></dl>
        </div>
        {/* Record card: the three record dates and the account shortcuts, in the cover's right column. */}
        <aside className="cover-record-card" aria-label="Record dates and account shortcuts">
          <dl className="record-dates">{[{ icon: CalendarDays, label: 'Client since', value: firstEngagement }, { icon: NotebookPen, label: 'Earliest evidence', value: record.earliestEvidence }, { icon: RefreshCw, label: 'Processed through', value: record.processedThrough }].map(item => <div key={item.label}><span className="record-date-icon"><item.icon size={13} /></span><div><dt>{item.label}</dt><dd>{fullDate(item.value)}</dd></div></div>)}</dl>
          <div className="quick-links client-service-links" role="group" aria-label="Client account shortcuts">{quick.map(q => <button key={q.id} className={`quick-link service-logo-button service-button-${q.id}`} aria-label={`${q.label}: ${q.destination || 'No account linked'}`} aria-describedby={`service-tooltip-${q.id}`} onClick={() => { if (q.destination) props.notify(`Opens ${q.destination} in ${q.label} in the real app.`); else { props.openClient(client.id, 'sources'); props.notify(`No ${q.label} account linked for ${client.name}.`); } }}><span className={`service-logo-frame service-logo-${q.id}`}><img src={q.logo} alt="" /></span><span className="service-logo-tooltip" role="tooltip" id={`service-tooltip-${q.id}`}>{q.label}</span></button>)}</div>
        </aside>
      </div>
    </section>
    <div className="client-record-body">
    {record.related && <p className="related-note"><Link2 size={13} />Related business: <strong>{record.related.name}</strong> · {record.related.note}</p>}
    <div className="client-tabs" role="group" aria-label="Client record sections">{tabs.map(tab => { const Icon = tabIcons[tab.id]; return <button key={tab.id} className={props.tab === tab.id ? 'active' : ''} aria-pressed={props.tab === tab.id} disabled={tab.soon} aria-disabled={tab.soon || undefined} title={tab.soon ? `${tab.label} · coming soon` : undefined} onClick={() => tab.soon || props.openClient(client.id, tab.id)}><Icon size={14} />{tab.label}{tab.count !== undefined && tab.count > 0 && <span>{tab.count}</span>}{tab.soon && <em className="soon-tag">Soon</em>}{tab.admin && <em className="soon-tag admin-tag">Admin</em>}</button>; })}</div>
    {props.tab === 'now' && <NowTab key={client.id} {...p} />}
    {props.tab === 'profile' && <ProfileTab {...p} />}
    {props.tab === 'history' && <HistoryTab key={client.id} {...p} />}
    {props.tab === 'brief' && <HandoverBrief key={client.id} {...p} />}
    {props.tab === 'commitments' && <Commitments {...p} />}
    {props.tab === 'meetings' && <MeetingsTab {...p} />}
    {props.tab === 'support' && <SupportTab key={client.id} {...p} />}
    {props.tab === 'leads' && <LeadsTab key={client.id} clientId={client.id} clientName={client.name} />}
    {props.tab === 'attendance' && <AttendanceTab {...p} />}
    {props.tab === 'sources' && <SourcesTab {...p} />}
    </div>
    {editorOpen && <ClientDetailsEditor client={client} viewer={props.viewer} initialTab="cover" onClose={() => setEditorOpen(false)} notify={props.notify} />}
  </div>;
}

function NowTab(props: Props) {
  return <>
    <div className="detail-grid now-meetings">
      <NextMeetingCard {...props} />
      <LastMeetingCard {...props} />
    </div>
    <div className="now-lower">
      <ActionItemsCard {...props} />
      <SentimentCard />
    </div>
    <CommunicationCard {...props} />
  </>;
}

// A brief is prepared automatically the day before a call; further out, someone generates it on demand.
const briefReady = (date: string) => daysBetween(DEMO_DATE, date) <= 1;
const daysAgo = (date: string) => { const d = daysBetween(date); return d === 0 ? 'today' : d === 1 ? 'yesterday' : `${d} days ago`; };
const daysUntil = (date: string) => { const d = daysBetween(DEMO_DATE, date); return d === 0 ? 'Today' : d === 1 ? 'Tomorrow' : `In ${d} days`; };

function NextMeetingCard(props: Props) {
  const { client, record } = props;
  const call = nextCallFor(client.id);
  const [brief, setBrief] = useState<'none' | 'generating' | 'ready'>(call && briefReady(call.date) ? 'ready' : 'none');
  const last = record.meetings.filter(m => m.date <= DEMO_DATE).sort((a, b) => b.date.localeCompare(a.date))[0];
  if (!call) return <Panel className="now-card next-meeting" title="Next meeting" eyebrow="ON THE CALENDAR">
    <div className="now-empty"><CalendarDays size={22} /><div><strong>No meeting booked</strong><p>{last ? `The last one was ${daysAgo(last.date)} (${dateLabel(last.date)}).` : 'No meetings in the record yet.'} The calendar is connected, so this isn’t a sync gap.</p></div></div>
  </Panel>;
  const generate = () => { setBrief('generating'); window.setTimeout(() => { setBrief('ready'); props.notify(`Brief ready for the ${call.type.toLowerCase()} on ${dateLabel(call.date)}.`); }, 1100); };
  return <Panel className="now-card next-meeting" title="Next meeting" eyebrow="ON THE CALENDAR" action={<span className="when-chip">{daysUntil(call.date)}</span>}>
    <div className="meeting-head"><div className="meeting-date"><span>{dateLabel(call.date, { month: 'short' })}</span><strong>{dateLabel(call.date, { day: 'numeric' })}</strong></div>
      <div><h3>{call.type}</h3><p className="hint">{timeLabel(call.time)} · {call.duration} · Host {call.host}</p></div></div>
    <p className="body-copy">{call.objective}</p>
    {brief === 'ready' && <div className="brief-preview"><span className="small-label">FROM THE BRIEF · TO RAISE</span><ul>{call.needs.slice(0, 2).map(n => <li key={n}>{n}</li>)}</ul></div>}
    {brief === 'none' && <p className="hint brief-state"><FileText size={12} />No brief yet. Briefs are prepared automatically the day before a call.</p>}
    <div className="now-card-actions">
      {brief === 'ready' && <button className="button button-small button-primary" onClick={() => props.openCall(call.id)}><FileText size={13} />View brief</button>}
      {brief === 'none' && <button className="button button-small button-gold" onClick={generate}><Sparkles size={13} />Generate brief</button>}
      {brief === 'generating' && <button className="button button-small button-outline" disabled><RefreshCw size={13} className="spin" />Generating…</button>}
    </div>
  </Panel>;
}

function LastMeetingCard(props: Props) {
  const { record } = props;
  const past = record.meetings.filter(m => m.date <= DEMO_DATE && inEngagement(m.engagement, props.engagement)).sort((a, b) => b.date.localeCompare(a.date));
  const meeting = past[0];
  const previous = meeting && !meeting.summary ? past.find(m => m.summary) : undefined;
  if (!meeting) return <Panel className="now-card" title="Last meeting" eyebrow="MOST RECENT CALL"><div className="now-empty"><History size={22} /><div><strong>No meetings yet</strong><p>Nothing recorded since {dateLabel(record.earliestEvidence, { day: 'numeric', month: 'short', year: 'numeric' })}.</p></div></div></Panel>;
  const created = props.actions.filter(a => meeting.actionIds.includes(a.id));
  const done = created.filter(a => !isOutstanding(a)).length;
  return <Panel className="now-card last-meeting" title="Last meeting" eyebrow="MOST RECENT CALL" action={<span className="when-chip muted-chip">{daysAgo(meeting.date)}</span>}>
    <div className="meeting-head"><div className="meeting-date past"><span>{dateLabel(meeting.date, { month: 'short' })}</span><strong>{dateLabel(meeting.date, { day: 'numeric' })}</strong></div>
      <div><h3>{meeting.title}</h3><p className="hint">{meeting.type} · {meeting.attendees}</p></div></div>
    {meeting.summary ? <p className="body-copy">{meeting.summary}</p>
      : <p className="hint brief-state"><AlertTriangle size={12} />{meeting.transcript === 'Not found' ? 'No transcript or recording found for this call, so there’s no summary.' : `Transcript state: ${meeting.transcript.toLowerCase()}. No summary yet.`}</p>}
    {previous && <div className="brief-preview"><span className="small-label">PREVIOUS CALL WITH A SUMMARY · {dateLabel(previous.date).toUpperCase()}</span><p className="body-copy">{previous.summary}</p></div>}
    {meeting.decisions.length > 0 && <div className="brief-preview"><span className="small-label">DECIDED</span><ul>{meeting.decisions.slice(0, 2).map(d => <li key={d}>{d}</li>)}</ul></div>}
    <div className="now-card-foot">
      {created.length > 0 && <span className="hint"><ListChecks size={12} />{created.length} action{created.length === 1 ? '' : 's'} created · {done} done</span>}
      {meeting.shared && <span className="hint">Group session · only this client’s parts</span>}
      <button className="text-button" onClick={() => props.openClient(props.client.id, 'meetings')}>Open in Meetings<ArrowRight size={13} /></button>
    </div>
  </Panel>;
}

function ActionItemsCard(props: Props) {
  const { client } = props;
  const [side, setSide] = useState('all');
  const open = props.actions.filter(a => a.clientId === client.id && isOutstanding(a));
  const sorted = [...open].sort((a, b) => Number(isOverdue(b)) - Number(isOverdue(a)) || (a.due || '9999').localeCompare(b.due || '9999'));
  const rows = sorted.filter(a => side === 'all' || a.side === side);
  const counts = { WIA: open.filter(a => a.side === 'WIA').length, Client: open.filter(a => a.side === 'Client').length, overdue: open.filter(isOverdue).length };
  return <Panel className="now-card" title="Action items" eyebrow="OPEN ON THIS ACCOUNT" action={<button className="text-button" onClick={() => props.openClient(client.id, 'commitments')}>View all<ArrowRight size={13} /></button>}>
    <div className="now-counts inline-counts"><div><strong>{counts.WIA}</strong><span>we owe</span></div><div><strong>{counts.Client}</strong><span>client owes</span></div><div className={counts.overdue ? 'is-overdue' : ''}><strong>{counts.overdue}</strong><span>overdue</span></div></div>
    <Segmented label="Whose actions" value={side} onChange={setSide} options={[{ id: 'all', label: 'All', count: open.length }, { id: 'WIA', label: 'We owe', count: counts.WIA }, { id: 'Client', label: 'Client owes', count: counts.Client }]} />
    {rows.length ? <ActionRows {...props} rows={rows.slice(0, 3)} compact /> : <Empty title="Nothing open">No open actions on this side.</Empty>}
    {rows.length > 3 && <button className="text-button now-more-link" onClick={() => props.openClient(client.id, 'commitments')}>+{rows.length - 3} more in Commitments<ArrowRight size={13} /></button>}
  </Panel>;
}

function SentimentCard() {
  return <Panel className="now-card sentiment-card is-soon" title="Client sentiment" eyebrow="LAST 30 DAYS" action={<em className="soon-tag">Soon</em>}>
    <div className="now-soon"><strong>Coming soon</strong><p>Client sentiment arrives with Health &amp; sentiment.</p></div>
  </Panel>;
}

const COMM_ICON: Partial<Record<SourceKind, typeof Mail>> = { Gmail: Mail, Slack: Hash, Zoom: Video, Fathom: Video };

function CommunicationCard(props: Props) {
  const { client, record } = props;
  const weekStart = addDays(DEMO_DATE, -6);
  const comms = (COMMS[client.id] || []).filter(c => c.date >= weekStart && c.date <= DEMO_DATE).sort((a, b) => b.date.localeCompare(a.date));
  const waiting = WAITING.find(w => w.clientId === client.id);
  const lastFrom = (side: 'Client' | 'WIA') => comms.find(c => c.from === side || c.from === 'Call');
  const channels = [...new Set(comms.map(c => c.channel))].map(ch => ({ ch, n: comms.filter(c => c.channel === ch).length }));
  const range = `${dateLabel(weekStart)} – ${dateLabel(DEMO_DATE)}`.toUpperCase();
  return <Panel className="now-card comms-card" title="Communication this week" eyebrow={range} action={<button className="text-button" onClick={() => props.openClient(client.id, 'history')}>Full history<ArrowRight size={13} /></button>}>
    {comms.length === 0 ? <div className="now-empty"><MessageSquare size={22} /><div><strong>No communication with the client this week</strong><p>Last contact {daysAgo(record.lastContact.date)} ({dateLabel(record.lastContact.date)}, {record.lastContact.channel}).</p></div></div>
      : <div className="comms-layout">
        <div className="comms-summary">
          <div className="now-counts inline-counts"><div><strong>{comms.filter(c => c.from === 'Client').length}</strong><span>from client</span></div><div><strong>{comms.filter(c => c.from === 'WIA').length}</strong><span>from WIA</span></div><div><strong>{comms.filter(c => c.from === 'Call').length}</strong><span>calls</span></div></div>
          <p className="hint">{channels.map(x => `${x.ch} ${x.n}`).join(' · ')}</p>
          <dl className="comms-last"><div><dt>Client last wrote</dt><dd>{lastFrom('Client') ? daysAgo(lastFrom('Client')!.date) : 'Not this week'}</dd></div><div><dt>We last wrote</dt><dd>{lastFrom('WIA') ? daysAgo(lastFrom('WIA')!.date) : 'Not this week'}</dd></div></dl>
          {waiting && <p className="comms-waiting"><AlertTriangle size={13} /><span><strong>Awaiting our reply · {waiting.businessDays} business day{waiting.businessDays === 1 ? '' : 's'}</strong>{waiting.from}’s {dateLabel(waiting.date)} {waiting.channel === 'Gmail' ? 'email' : 'message'} hasn’t been answered.</span></p>}
        </div>
        <ul className="comms-list">{comms.map(c => { const Icon = COMM_ICON[c.channel] || MessageSquare; return <li key={c.id}>
          <span className="comms-date">{dateLabel(c.date)}</span>
          <span className={`comms-icon from-${c.from.toLowerCase()}`}><Icon size={13} /></span>
          <div><p><strong>{c.who}</strong><span className={`comms-dir from-${c.from.toLowerCase()}`}>{c.from === 'Call' ? 'Call' : c.from === 'Client' ? 'From client' : 'To client'}</span></p><p className="comms-text">{c.text}</p></div>
          {c.sourceId && <SourceLink id={c.sourceId} onOpen={props.showEvidence} />}
        </li>; })}</ul>
      </div>}
  </Panel>;
}

function ProfileTab(props: Props) {
  const { record } = props;
  const call = record.meetings[0];
  return <div className="profile-grid">
    <ProfileSections {...props} />
    <div className="profile-side">
      <Panel title="People"><p className="small-label">CLIENT SIDE</p><ul className="people-list">{record.contacts.map(c => <li key={c.name + c.role}><strong className={c.name === 'Unknown' ? 'text-amber' : ''}>{c.name}</strong><span>{c.role}</span><small>{c.email}</small>{c.note && <em>{c.note}</em>}</li>)}</ul><p className="small-label">WIA TEAM</p><ul className="people-list">{record.team.map(t => <li key={t.name}><strong>{t.name}</strong><span>{t.role}</span></li>)}</ul></Panel>
      <Panel title="Engagements"><dl className="detail-list">{record.engagements.filter(e => inEngagement(e.type, props.engagement)).map(e => <div key={e.type}><dt>{e.type}{e.programme ? <small className="block muted">{e.programme}</small> : null}</dt><dd>Since {dateLabel(e.start, { day: 'numeric', month: 'short', year: 'numeric' })}{e.phase ? ` · ${e.phase}` : ''}{e.signed && isFinanceAdmin(props.viewer) && <small className="block muted">Signed {dateLabel(e.signed)} (admins only)</small>}</dd></div>)}</dl></Panel>
      {record.links.leadlock && <Panel title="LeadLock account"><button className="quick-link" onClick={() => props.notify('Opens the LeadLock location in the real app.')}><Link2 size={13} />{record.links.leadlock}<ArrowUpRight size={11} /></button><p className="hint">Lead figures are on the Leads tab.</p></Panel>}
      <div className="note-box"><FileText size={17} /><p>Every client has the same sections and fields, so gaps are visible. Editors propose corrections; a resolver applies them, and a reviewed value is kept even if the source is re-read. {call ? `Last updated from the ${call.type.toLowerCase()} on ${dateLabel(call.date)}.` : ''}</p></div>
    </div>
  </div>;
}

const PAGE_SIZE = 10;

function Commitments(props: Props) {
  const [page, setPage] = useState(0);
  const [side, setSide] = useState('all');
  const [notify, setNotify] = useState<NotifyContext | null>(null);
  const [history, setHistory] = useState(false);
  const rows = props.actions.filter(a => a.clientId === props.client.id && isOutstanding(a));
  const shown = rows.filter(a => side === 'all' || a.side === side).sort((a, b) => (a.due || '9999-12-31').localeCompare(b.due || '9999-12-31') || a.title.localeCompare(b.title));
  const pages = Math.max(1, Math.ceil(shown.length / PAGE_SIZE));
  const current = Math.min(page, pages - 1);
  useEffect(() => setPage(0), [props.client.id, side]);
  const completed = props.actions.filter(a => a.clientId === props.client.id && !isOutstanding(a)).length;
  const send = (messages: { to: string; actionIds: string[] }[]) => {
    const sent = new Map<string, string[]>(); messages.forEach(m => m.actionIds.forEach(id => sent.set(id, [...(sent.get(id) || []), m.to])));
    sent.forEach((to, id) => { const a = props.actions.find(x => x.id === id); if (a) props.updateAction(id, { history: [...(a.history || []), { date: DEMO_DATE, text: `Slack: notified ${to.join(', ')} (sent by ${props.viewer}).` }] }); });
    setNotify(null); props.notify(`${messages.length} Slack ${messages.length === 1 ? 'message' : 'messages'} sent. Preview only: nothing was posted.`);
  };
  return <><div className="toolbar"><Segmented label="Commitment side" value={side} onChange={setSide} options={[{ id: 'all', label: 'All' }, { id: 'WIA', label: 'What we owe them' }, { id: 'Client', label: 'What we need from them' }]} /><div className="toolbar-right"><button className="button button-small button-outline" onClick={() => setNotify({ mode: 'client', title: props.client.name, actions: rows })}><Send size={13} />Post to {props.record.links.slack}</button><button className="text-button" onClick={() => props.navigate('actions-v3')}>Open in Action Hub<ArrowRight size={13} /></button></div></div>
    <Panel className="commitments-panel"><ActionRows {...props} rows={shown.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE)} compact />
      {shown.length > 0 && <nav className="commitments-pagination" aria-label="Commitment pages"><span role="status">{current * PAGE_SIZE + 1}–{Math.min((current + 1) * PAGE_SIZE, shown.length)} of {shown.length} actions</span><div>
        <button type="button" className="button button-small button-outline" disabled={current === 0} onClick={() => setPage(current - 1)} aria-label="Previous commitments page">Previous</button>
        <span>Page {current + 1} of {pages}</span>
        <button type="button" className="button button-small button-outline" disabled={current === pages - 1} onClick={() => setPage(current + 1)} aria-label="Next commitments page">Next</button>
      </div></nav>}<button className="show-completed" onClick={() => setHistory(true)}><History size={14} />Show completed<span>{completed}</span></button></Panel>
    <p className="hint">Same records as the Action Hub. Changes here show there too.</p>
    {notify && <SlackNotifyDialog ctx={notify} viewer={props.viewer} close={() => setNotify(null)} send={send} />}
    {history && <CommitmentHistory {...props} client={props.client} close={() => setHistory(false)} />}</>;
}

function MeetingsTab(props: Props) {
  return <ClientMeetings {...props} />;
}

function ComingSoon() {
  return <Panel title="Invoices & terms" eyebrow="COMING SOON · STAGE 3"><div className="coming-soon-box"><Lock size={22} /><div><h3>Not switched on yet</h3><p>The full invoice and agreement view arrives with Stage 3. The data is still being collected now: signing and payment events already appear in this client’s History (Commercial lane), and signing dates show under Profile → Engagements.</p><p className="hint">No balances or “overdue invoice” claims are shown until payments are reconciled.</p></div></div></Panel>;
}

function AttendanceTab(props: Props) {
  const { client } = props;
  const rows = [
    { date: '2026-09-24', state: 'Attended', note: '', src: client.id === 'willow' ? 'willow-fathom' : undefined },
    { date: '2026-10-01', state: client.id === 'willow' ? 'Missed' : 'Attended', note: '' },
    { date: '2026-10-08', state: client.id === 'willow' ? 'Unknown' : 'Attended', note: client.id === 'willow' ? 'Sheet note: “Said she’d join late; not logged yet.” The miss counter says 2.' : '' },
  ];
  const tone = (s: string) => s === 'Attended' ? 'green' : s === 'Missed' ? 'amber' : 'neutral';
  return <Panel title="Programme attendance" eyebrow={recordFor(client.id).engagements[0].programme?.toUpperCase() || 'PROGRAMME'}><p className="body-copy">As reported in the programme’s attendance sheet. A calendar invite or a missing transcript is never treated as absence.</p><div className="attendance-list">{rows.map(r => <div key={r.date}><CalendarDays size={18} /><div><strong>{client.service.includes('Meta') ? 'Meta' : 'Google'} office hours</strong><small>{dateLabel(r.date)}{r.note ? ` · ${r.note}` : ''}</small></div><Badge tone={tone(r.state)}>{r.state}</Badge>{r.src ? <SourceLink id={r.src} onOpen={props.showEvidence} /> : <span className="muted small-text">Sheet row</span>}</div>)}</div>{client.id === 'willow' && <p className="stale-note"><AlertTriangle size={13} />The sheet’s notes and its miss counter disagree for Oct 8. Flagged for the programme team to confirm.</p>}<p className="hint">Streaks, percentages and alerts wait for WIA to define the attendance rule.</p></Panel>;
}

function SourcesTab(props: Props) {
  const { record } = props;
  const [suggestion, setSuggestion] = useState(record.mappingSuggestion);
  const tone = (s: string) => s === 'Linked' ? 'green' : s === 'Partial' ? 'gold' : s === 'Blocked' ? 'amber' : 'neutral';
  // "Edit mapping" opens the same channel modal as Connections; email, calendar and Fathom share the contacts channel.
  const [editing, setEditing] = useState<{ channel: string } | null>(null);
  const CHANNEL: Record<string, string> = { Slack: 'slack', ClickUp: 'clickup', Drive: 'drive', LeadLock: 'leadlock', Gmail: 'contacts', Calendar: 'contacts', Fathom: 'contacts' };
  return <>
    <ClientConnections client={props.client.id} notify={props.notify} openRequest={editing} />
    <Panel title="Linked accounts" eyebrow="WHERE THIS CLIENT’S RECORD COMES FROM"><div className="sources-table" role="table">
      <div className="sources-row head" role="row"><span>Source</span><span>Linked account</span><span>State</span><span>Last sync</span><span>History from</span><span>Items</span><span /></div>
      {record.sources.map(s => <div className="sources-row" role="row" key={s.source}><strong>{s.source}</strong><span>{s.account}{s.note && <small className="block hint">{s.note}</small>}</span><span><Badge tone={tone(s.state)} dot={false}>{s.state}</Badge></span><span>{s.lastSync || '—'}</span><span>{s.from ? dateLabel(s.from, { month: 'short', year: 'numeric' }) : '—'}</span><span>{s.items ?? '—'}</span><span>{CHANNEL[s.source] ? <button className="text-button" onClick={() => setEditing({ channel: CHANNEL[s.source] })}>Edit mapping</button>
        : s.state !== 'Not applicable' && <button className="text-button" onClick={() => props.notify(`Editing the ${s.source} mapping is an ops task in the real app.`)}>Edit mapping</button>}</span></div>)}
    </div></Panel>
    {suggestion && <div className="coverage-banner suggestion"><Sparkles size={15} /><p>{suggestion}</p><button className="button button-small button-primary" onClick={() => { setSuggestion(undefined); props.notify('Linked. The folder will be backfilled.'); }}>Link it</button><button className="text-button" onClick={() => { setSuggestion(undefined); props.notify('Got it. It won’t be suggested again.'); }}>Not this client</button></div>}
    <p className="hint"><X size={11} /> Not applicable means the source isn’t part of this client’s engagement, which is different from “not linked”.</p>
  </>;
}
