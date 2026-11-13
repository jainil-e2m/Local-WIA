import { useState } from 'react';
import { ArrowRight, CalendarDays, ExternalLink, FileText, PencilLine, Video } from 'lucide-react';
import { CALLS, DEMO_DATE, dateLabel, ownerLabel, timeLabel } from '../data';
import type { ClientRecord } from '../records';
import type { Call, Client, WorkspaceProps } from '../types';
import { Badge, Dialog, Empty, Panel, Segmented, SourceLink } from './UI';
import './ClientMeetings.css';

type Meeting = ClientRecord['meetings'][number];
type MeetingRow = { key: string; kind: 'recorded'; meeting: Meeting; date: string; title: string; type: string }
  | { key: string; kind: 'scheduled'; call: Call; date: string; title: string; type: string };
type Props = WorkspaceProps & { client: Client; record: ClientRecord; engagement: string };
const transcriptLabel = (meeting: Meeting) => meeting.transcript === 'Available' ? 'Transcript available' : meeting.transcript === 'Recording link only' ? 'Recording only' : meeting.transcript === 'Not found' ? 'Transcript not found' : meeting.transcript;

export default function ClientMeetings(props: Props) {
  const { client, record } = props;
  const [type, setType] = useState('all');
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  // Links saved in this visit, by meeting id (null = removed); the portfolio picks them up on its next refresh.
  const [links, setLinks] = useState<Record<string, string | null>>({});
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [linkMessage, setLinkMessage] = useState('');
  const linkOf = (m: Meeting) => m.id in links ? links[m.id] : m.link;
  const teamLink = (m: Meeting) => m.id in links ? !!links[m.id] : m.linkSource === 'Added by the team';
  const rows: MeetingRow[] = [
    ...record.meetings.filter(meeting => props.engagement === 'all' || !meeting.engagement || meeting.engagement === props.engagement).map(meeting => ({ key: `recorded:${meeting.id}`, kind: 'recorded' as const, meeting, date: meeting.date, title: meeting.title, type: meeting.type })),
    ...CALLS.filter(call => call.clientId === client.id && call.date >= DEMO_DATE && !record.meetings.some(meeting => meeting.id === call.id)).map(call => ({ key: `scheduled:${call.id}`, kind: 'scheduled' as const, call, date: call.date, title: call.type, type: call.type })),
  ].sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === 'scheduled' ? -1 : 1;
    return a.kind === 'scheduled' ? a.date.localeCompare(b.date) || (a.kind === 'scheduled' && b.kind === 'scheduled' ? a.call.time.localeCompare(b.call.time) : 0) : b.date.localeCompare(a.date);
  });
  const types = [...new Set(rows.map(row => row.type))];
  const filtered = rows.filter(row => type === 'all' || row.type === type);
  const selected = rows.find(row => row.key === selectedKey);
  const meeting = selected?.kind === 'recorded' ? selected.meeting : undefined;
  const call = selected?.kind === 'scheduled' ? selected.call : undefined;
  const close = () => { setSelectedKey(null); setEditing(false); setLinkMessage(''); };
  const startEdit = (m: Meeting) => { setDraft(linkOf(m) || ''); setLinkMessage(''); setEditing(true); };
  async function saveLink(m: Meeting, url: string | null) {
    setLinkMessage('');
    if (!m.recordId) {  // sample data has no KB record to save against
      setLinks(l => ({ ...l, [m.id]: url }));
      setEditing(false);
      setLinkMessage('Preview only: sample meetings aren’t saved.');
      return;
    }
    setSaving(true);
    try {
      const res = await fetch(`/api/v1/clients/${encodeURIComponent(client.id)}/meetings/${m.recordId}/link`, url === null
        ? { method: 'DELETE', credentials: 'same-origin' }
        : { method: 'PUT', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) });
      const json = await res.json().catch(() => ({})) as { link?: string | null; detail?: { message?: string } };
      if (!res.ok) throw new Error(json.detail?.message || `Couldn’t save the link (HTTP ${res.status}).`);
      setLinks(l => ({ ...l, [m.id]: json.link ?? null }));
      setEditing(false);
    } catch (e) {
      setLinkMessage(e instanceof Error && e.message !== 'Failed to fetch' ? e.message : 'Couldn’t reach the Knowledge Base. The link wasn’t saved.');
    } finally {
      setSaving(false);
    }
  }
  const openEvidence = (id: string) => { close(); props.showEvidence(id); };
  const fullDate = (date: string) => dateLabel(date, { day: 'numeric', month: 'short', year: 'numeric' });

  return <>
    <div className="toolbar client-meeting-toolbar"><Segmented label="Call type" value={type} onChange={setType} options={[{ id: 'all', label: 'All meetings' }, ...types.map(item => ({ id: item, label: item }))]} /></div>
    <Panel title="Meetings" eyebrow="ALL CLIENT CONVERSATIONS" className="client-meetings-panel" action={<span className="hint">{filtered.length} meeting{filtered.length === 1 ? '' : 's'}</span>}>
      {filtered.length ? <ul className="client-meeting-list">{filtered.map(row => <li key={row.key}><button className="client-meeting-row" aria-haspopup="dialog" aria-label={`Open meeting: ${row.title}, ${fullDate(row.date)}`} onClick={() => setSelectedKey(row.key)}>
        <span className={`client-meeting-icon ${row.kind === 'scheduled' ? 'is-scheduled' : ''}`}>{row.kind === 'scheduled' ? <CalendarDays size={18} /> : <Video size={18} />}</span>
        <span className="client-meeting-name"><strong>{row.title}</strong><span>{row.type} · {row.kind === 'scheduled' ? `Host ${row.call.host}` : row.meeting.attendees || 'Attendees not recorded'}</span></span>
        <span className="client-meeting-date">{fullDate(row.date)}<small>{row.kind === 'scheduled' ? `${timeLabel(row.call.time)} IST · ${row.call.duration}` : <>{row.meeting.source} · {linkOf(row.meeting) ? 'Link' : <span className="client-meeting-nolink"><PencilLine size={10} aria-hidden="true" />No link</span>}</>}</small></span>
        <span className="client-meeting-state"><Badge tone={row.kind === 'scheduled' ? 'blue' : row.meeting.transcript === 'Not found' ? 'amber' : 'neutral'} dot={false}>{row.kind === 'scheduled' ? 'Scheduled' : transcriptLabel(row.meeting)}</Badge></span>
        <ArrowRight size={15} className="client-meeting-arrow" />
      </button></li>)}</ul> : <Empty title={type === 'all' ? 'No meetings recorded yet' : 'No meetings for this filter'}>Scheduled calls and recorded conversations will appear here.</Empty>}
    </Panel>
    {selected && <Dialog title={selected.title} subtitle={client.name} size="lg" className="client-meeting-dialog" onClose={close} meta={<span>{fullDate(selected.date)} · {selected.type}</span>} footer={<><button className="button button-outline" onClick={close}>Close</button>{call && <button className="button button-primary" onClick={() => { close(); props.openCall(call.id); }}><FileText size={14} />Open call brief<ArrowRight size={14} /></button>}</>}>
      <dl className="client-meeting-details"><div><dt>{call ? 'Host' : 'Attendees'}</dt><dd>{call ? call.host : meeting?.attendees || 'Not recorded'}</dd></div><div><dt>{call ? 'Time & duration' : 'Source'}</dt><dd>{call ? `${timeLabel(call.time)} IST · ${call.duration}` : meeting?.source}</dd></div><div><dt>Status</dt><dd>{meeting ? transcriptLabel(meeting) : 'Scheduled'}</dd></div>{meeting?.engagement && <div><dt>Engagement</dt><dd>{meeting.engagement}</dd></div>}</dl>
      <section className="client-meeting-section"><h3>{call ? 'What this meeting is for' : 'What the meeting was about'}</h3><p>{call ? call.objective || 'No objective recorded yet.' : meeting?.summary || 'No summary recorded for this meeting yet.'}</p>{call?.context && <p>{call.context}</p>}</section>
      {meeting && <>
        {meeting.shared && <p className="client-meeting-note">Shared programme session. Only this client’s portion is included.</p>}
        <section className="client-meeting-section"><h3>Decisions</h3>{meeting.decisions.length ? <ul>{meeting.decisions.map((decision, index) => <li key={index}>{decision}</li>)}</ul> : <p className="hint">No decisions recorded.</p>}</section>
        <section className="client-meeting-section"><h3>Actions from this meeting</h3>{meeting.actionIds.length ? <ul className="client-meeting-actions">{meeting.actionIds.map(id => { const action = props.actions.find(item => item.id === id && item.clientId === client.id); return <li key={id}>{action ? <><strong>{action.title}</strong><span>{ownerLabel(action.owner)} · {action.status}{action.due ? ` · Due ${fullDate(action.due)}` : ' · No due date'}</span></> : <span>Linked action details are unavailable.</span>}</li>; })}</ul> : <p className="hint">No actions recorded.</p>}</section>
        <section className="client-meeting-section client-meeting-link-section"><h3>Recording link</h3>
          {editing ? <form className="client-meeting-link-form" onSubmit={event => { event.preventDefault(); void saveLink(meeting, draft.trim()); }}>
            <label htmlFor="meeting-link-input" className="sr-only">Recording link</label>
            <input id="meeting-link-input" type="url" required autoFocus value={draft} placeholder="https://zoom.us/rec/…" onChange={event => setDraft(event.target.value)} disabled={saving} />
            <button type="submit" className="button button-primary" disabled={saving || !draft.trim()}>{saving ? 'Saving…' : 'Save'}</button>
            <button type="button" className="button button-outline" onClick={() => { setEditing(false); setLinkMessage(''); }} disabled={saving}>Cancel</button>
          </form> : linkOf(meeting) ? <p className="client-meeting-link-row">
            <a href={linkOf(meeting)!} target="_blank" rel="noopener noreferrer">Open recording<ExternalLink size={12} aria-hidden="true" /></a>
            <span className="hint">{teamLink(meeting) ? 'Added by the team' : meeting.linkSource || meeting.source}</span>
            {teamLink(meeting) && <><button type="button" className="button button-outline button-small" onClick={() => startEdit(meeting)}><PencilLine size={12} />Edit</button>
              <button type="button" className="button button-outline button-small" disabled={saving} onClick={() => void saveLink(meeting, null)}>Remove</button></>}
          </p> : <p className="client-meeting-link-row"><span>No link</span>
            <button type="button" className="button button-outline button-small" onClick={() => startEdit(meeting)} aria-label="Add a recording link"><PencilLine size={12} />Add link</button></p>}
          {linkMessage && <p className="hint" role="status">{linkMessage}</p>}
        </section>
        <section className="client-meeting-section"><h3>Transcript & source</h3><p className="hint">{meeting.transcript === 'Not found' ? 'No transcript or client segment was found. This does not confirm whether the client attended.' : meeting.transcript === 'Recording link only' ? 'A recording link is recorded; no transcript is available.' : meeting.transcript === 'Summary only' ? 'A summary is recorded; the full transcript is not available here.' : 'The transcript is marked available in the client record.'}</p>{meeting.sourceId ? <SourceLink id={meeting.sourceId} onOpen={openEvidence} label="Read source excerpt" /> : <p className="hint">No source excerpt linked.</p>}</section>
      </>}
      {call && <>
        <section className="client-meeting-section"><h3>Agenda</h3>{call.agenda.length ? <ul>{call.agenda.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="hint">No agenda recorded yet.</p>}</section>
        {call.needs.length > 0 && <section className="client-meeting-section"><h3>What to settle</h3><ul>{call.needs.map((item, index) => <li key={index}>{item}</li>)}</ul></section>}
        {call.opportunity && <section className="client-meeting-section"><h3>Opportunity</h3><p>{call.opportunity}</p></section>}
        {call.sourceIds.length > 0 && <section className="client-meeting-section"><h3>Source context</h3><div className="drawer-inline">{call.sourceIds.map(id => <SourceLink key={id} id={id} onOpen={openEvidence} />)}</div></section>}
      </>}
    </Dialog>}
  </>;
}
