import { useState } from 'react';
import { ArrowRight, CalendarDays, CheckCircle2, Clipboard, Clock3, Download, ListChecks, Sparkles, Target, UserRound } from 'lucide-react';
import { CALLS, DEMO_DATE, clientById, dateLabel, isOutstanding, sourceById, timeLabel } from '../data';
import { Avatar, Badge, Empty, PageHeading, Panel, Segmented, SourceLink } from '../components/UI';
import type { Call, WorkspaceProps } from '../types';

export function callMarkdown(call: Call, actions: WorkspaceProps['actions']) {
  const client = clientById(call.clientId);
  const evidence = call.sourceIds.map(id => {
    const source = sourceById(id);
    return source ? `- ${source.kind}: ${source.title} — ${dateLabel(source.date)}, ${source.locator}\n  ${source.excerpt.replace(/\n/g, '\n  ')}` : `- Source unavailable: ${id}`;
  }).join('\n\n');
  return `# ${client.name} — ${call.type}\n\nFrontend preview · fictional sample record\n${dateLabel(call.date)} · ${timeLabel(call.time)} IST · ${call.host}\n\n## Objective\n${call.objective}\n\n## Current position\n${call.context}\n\n## Suggested agenda\n${call.agenda.map((item, index) => `${index + 1}. ${item}`).join('\n')}\n\n## What we need from the client\n${call.needs.map(item => `- ${item}`).join('\n')}\n\n## Outstanding commitments\n${actions.filter(a => a.clientId === client.id && isOutstanding(a)).map(a => `- ${a.title} — ${a.owner}, due ${dateLabel(a.due)} (${a.status})`).join('\n') || 'None'}\n\n## Evidence\n${evidence}\n`;
}

export default function CallPrep(props: WorkspaceProps & { selectedId?: string }) {
  const [range, setRange] = useState('all');
  const calls = CALLS.filter(call => range === 'all' || range === 'today' && call.date === DEMO_DATE || range === 'upcoming' && call.date > DEMO_DATE);
  const selected = calls.find(call => call.id === props.selectedId) || calls[0];
  const copy = async () => { if (!selected) return; try { await navigator.clipboard.writeText(callMarkdown(selected, props.actions)); props.notify('Call brief copied to your clipboard.'); } catch { props.notify('Clipboard is unavailable. Use Download brief to save a copy.'); } };
  const download = () => { if (!selected) return; const url = URL.createObjectURL(new Blob([callMarkdown(selected, props.actions)], { type: 'text/markdown' })); const link = document.createElement('a'); link.href = url; link.download = `${selected.clientId}-${selected.date}-call-brief.md`; link.click(); URL.revokeObjectURL(url); props.notify('Sample call brief downloaded.'); };
  return <div className="view">
    <PageHeading eyebrow="BEFORE THE CONVERSATION" title="Walk in with context." description="A concise, cited brief, shaped around the purpose of each call."><button className="button button-outline" onClick={download}><Download size={15} />Download brief</button></PageHeading>
    <div className="toolbar"><Segmented label="Call date range" value={range} onChange={setRange} options={[{ id: 'all', label: 'All scheduled', count: 6 }, { id: 'today', label: 'Today', count: 3 }, { id: 'upcoming', label: 'Next week', count: 3 }]} /><span className="muted small-text"><CalendarDays size={13} />October 9–14, 2026 · IST</span></div>
    <div className="call-workspace"><aside className="call-list"><p className="small-label">ON YOUR CALENDAR</p>{calls.map(call => { const c = clientById(call.clientId); return <button key={call.id} className={`call-list-item ${selected?.id === call.id ? 'active' : ''}`} onClick={() => props.openCall(call.id)}><div className="call-list-date"><span>{call.date === DEMO_DATE ? 'TODAY' : dateLabel(call.date).toUpperCase()}</span><strong>{timeLabel(call.time)}</strong></div><div className="call-list-client"><Avatar client={c} small /><div><h3>{c.name}</h3><p>{call.type}</p></div></div><div className="call-list-bottom"><span>{call.host} · {call.duration}</span><CheckCircle2 size={13} /></div></button>; })}<div className="calendar-note"><CalendarDays size={18} /><p>Calendar events are matched to a client and call type before a brief is prepared.</p></div></aside>
    {selected ? <div className="call-brief"><div className="call-brief-heading"><div><p className="eyebrow">YOUR CALL BRIEF</p><h2>{clientById(selected.clientId).name}</h2><div className="call-meta"><span><CalendarDays size={13} />{dateLabel(selected.date)}</span><span><Clock3 size={13} />{timeLabel(selected.time)} IST</span><span><UserRound size={13} />{selected.host}</span></div></div><div className="call-heading-right"><Badge tone="green">Ready to review</Badge><button className="icon-button" aria-label="Copy call brief" title="Copy brief" onClick={copy}><Clipboard size={17} /></button></div></div>
    <div className="call-type-line"><Badge tone="blue" dot={false}>{selected.type}</Badge><span>{selected.duration} · {selected.sourceIds.length} sources</span><button className="text-button" onClick={() => props.openClient(selected.clientId)}>Client record<ArrowRight size={13} /></button></div>
    <div className="call-objective"><Target size={20} /><div><p className="small-label">THE PURPOSE OF THIS CALL</p><h3>{selected.objective}</h3></div></div>
    <section className="brief-section"><h3>Where things stand</h3><p>{selected.context}</p><div className="inline-sources">{selected.sourceIds.slice(0, 2).map(id => <SourceLink key={id} id={id} onOpen={props.showEvidence} />)}</div></section>
    <div className="brief-two-col"><section className="brief-section"><h3>A suggested agenda</h3><ol className="agenda-list">{selected.agenda.map((item, index) => <li key={item}><span>{String(index + 1).padStart(2, '0')}</span><p>{item}</p></li>)}</ol></section><section className="brief-section"><h3>What we need from the client</h3><ul className="need-list">{selected.needs.map(need => <li key={need}><span /><p>{need}</p></li>)}</ul></section></div>
    <div className="insight-box"><Sparkles size={19} /><div><h4>An opportunity worth exploring</h4><p>{selected.opportunity}</p><small>Suggested interpretation · confirm together on the call</small></div></div>
    <Panel title="Keep these commitments in view" action={<ListChecks size={17} />} className="brief-actions-panel">{props.actions.filter(a => a.clientId === selected.clientId && isOutstanding(a)).map(action => <div className="brief-action" key={action.id}><span className="small-circle" /><div><strong>{action.title}</strong><small>{action.owner} · due {dateLabel(action.due)}</small></div><SourceLink id={action.sourceId} onOpen={props.showEvidence} /></div>)}</Panel>
    <div className="call-footer"><CheckCircle2 size={14} /><span>Sample brief assembled from the client record.</span><button className="text-button" onClick={copy}>Copy brief<Clipboard size={13} /></button></div></div> : <Empty title="No calls in this range" />}</div>
  </div>;
}
