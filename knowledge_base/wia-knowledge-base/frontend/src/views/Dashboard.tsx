import { ArrowRight, ArrowUpRight, CalendarDays, CheckCircle2, ChevronRight, Clock3, HeartHandshake, ListChecks, Quote, Sparkles, Users } from 'lucide-react';
import { CALLS, CLIENTS, DEMO_DATE, clientById, dateLabel, isOutstanding, isOverdue, timeLabel } from '../data';
import { Avatar, Badge, Empty, Panel, SourceLink, Sparkline, Stat } from '../components/UI';
import type { WorkspaceProps } from '../types';
import kbLive from '@kb-live';

export default function Dashboard(props: WorkspaceProps) {
  if (kbLive.meta) return <LiveOverview {...props} />;
  const today = CALLS.filter(call => call.date === DEMO_DATE);
  const first = today[0];
  const client = clientById(first.clientId);
  const outstanding = props.actions.filter(isOutstanding);
  const overdue = props.actions.filter(isOverdue);
  const watch = CLIENTS.filter(c => c.health === 'Needs attention');
  return <div className="view dashboard-view">
    <div className="dashboard-hero"><div><p className="eyebrow"><span className="tiny-star">✧</span> YOUR CLIENT DESK · FRIDAY, OCTOBER 9</p><h1>Good morning, Whitney<span className="gold-period">.</span></h1><p>Every client has a story. Here’s what matters today.</p></div><button className="button button-gold" onClick={() => props.openCall(first.id)}><CalendarDays size={16} />Prepare for today’s calls<ArrowUpRight size={15} /></button></div>
    <div className="stats-grid"><Stat label="Clients in your care" value={CLIENTS.length.toString().padStart(2, '0')} detail="4 retainers · 2 Accelerators" icon={<Users size={17} />} /><Stat label="On the calendar" value={today.length.toString().padStart(2, '0')} detail="Your next call is at 2:00 PM" icon={<CalendarDays size={17} />} /><Stat label="Open commitments" value={outstanding.length.toString().padStart(2, '0')} detail={`${overdue.length} need a little extra attention`} tone="gold" icon={<ListChecks size={17} />} /><Stat label="Clients to check in on" value={watch.length.toString().padStart(2, '0')} detail="A conversation could make a difference" tone="amber" icon={<HeartHandshake size={17} />} /></div>
    <div className="dashboard-grid">
      <div className="dashboard-main">
        <Panel title="A thoughtful start to your next call" eyebrow="THE NEXT CONVERSATION" action={<span className="ready-label"><CheckCircle2 size={13} />Brief ready</span>} className="featured-brief">
          <div className="featured-client"><Avatar client={client} /><div><h3>{client.name}</h3><p>{first.type} <span>·</span> {timeLabel(first.time)} <span>·</span> {first.duration}</p></div><Badge tone="amber">Needs attention</Badge></div>
          <div className="brief-context"><p className="small-label">WHERE THINGS STAND</p><p>{first.context}</p></div>
          <div className="insight-box"><div className="insight-icon"><Sparkles size={17} strokeWidth={1.5} /></div><div><h4>The conversation to have</h4><p>Start with Sarah’s question about inquiry quality. Close the page approval loop, then agree on one next step together.</p><div className="inline-sources"><SourceLink id="bloom-email" onOpen={props.showEvidence} label="Client’s latest email" /><SourceLink id="bloom-call" onOpen={props.showEvidence} label="Last strategy call" /></div></div></div>
          <div className="featured-bottom"><span><Clock3 size={13} />Updated from 3 sample sources</span><button className="text-button" onClick={() => props.openCall(first.id)}>Read the call brief<ArrowRight size={15} /></button></div>
        </Panel>
        <Panel title="Your clients, at a glance" eyebrow="THE PORTFOLIO" action={<button className="text-button" onClick={() => props.navigate('clients')}>View all clients<ArrowUpRight size={14} /></button>} className="portfolio-panel">
          <div className="table-scroll"><table className="portfolio-table"><thead><tr><th>Client</th><th>Relationship</th><th>Open actions</th><th>Activity</th><th /></tr></thead><tbody>{CLIENTS.slice(0, 4).map(c => <tr key={c.id}><td><button className="table-client" onClick={() => props.openClient(c.id)}><Avatar client={c} small /><span><strong>{c.name}</strong><small>{c.service}</small></span></button></td><td><Badge tone={c.health === 'On track' ? 'green' : c.tone}>{c.health}</Badge></td><td><span className="action-count">{outstanding.filter(a => a.clientId === c.id).length}</span><span className="muted small-text"> open</span></td><td><Sparkline values={c.activity} tone={c.tone} /></td><td><button className="icon-button" onClick={() => props.openClient(c.id)} aria-label={`Open ${c.name}`}><ChevronRight size={17} /></button></td></tr>)}</tbody></table></div>
        </Panel>
      </div>
      <div className="dashboard-aside">
        <Panel title="Today’s conversations" eyebrow="MAKE ROOM FOR THE CLIENT" action={<span className="count-pill">{today.length}</span>} className="call-queue">
          <div className="queue-list">{today.map((call, index) => { const c = clientById(call.clientId); return <button key={call.id} className={`queue-item ${index === 0 ? 'next' : ''}`} onClick={() => props.openCall(call.id)}><div className="queue-time"><strong>{timeLabel(call.time).split(' ')[0]}</strong><small>{timeLabel(call.time).split(' ')[1]}</small></div><div className="queue-line"><i /></div><div className="queue-info"><h3>{c.name}</h3><p>{call.type}</p><small>{call.host} · {call.duration}</small></div><ArrowUpRight size={14} /></button>; })}</div><div className="panel-footnote">Oct 9 · All times in IST</div>
        </Panel>
        <Panel title="A few loops to close" eyebrow="FOLLOW THROUGH" action={<span className="attention-dot" />} className="loops-panel">
          {outstanding.filter(a => isOverdue(a) || !a.acknowledged).slice(0, 3).map(action => <button className="loop-item" key={action.id} onClick={() => props.openClient(action.clientId, 'commitments')}><span className={`loop-marker ${isOverdue(action) ? 'overdue' : ''}`}><ListChecks size={13} /></span><span><strong>{action.title}</strong><small>{clientById(action.clientId).name} · {action.owner}</small><span className={`loop-date ${isOverdue(action) ? 'text-amber' : ''}`}>{isOverdue(action) ? 'Overdue' : 'Due today'} · {dateLabel(action.due)}</span></span><ChevronRight size={14} /></button>)}<button className="text-button" onClick={() => props.navigate('actions-v3')}>Open Action Hub<ArrowRight size={14} /></button>
        </Panel>
      </div>
    </div>
    <div className="listening-note"><Quote size={19} strokeWidth={1.4} /><p>“Could we talk through which couples are a good fit?” <span>Sarah, Bloom Manor · Oct 8</span></p><button className="text-button" onClick={() => props.showEvidence('bloom-email')}>Listen to the context<ArrowUpRight size={14} /></button></div>
  </div>;
}

/** Local WIA export: the Overview (Stage 3) isn't built on real data, so show only what the intake test supports. */
function LiveOverview(props: WorkspaceProps) {
  const outstanding = props.actions.filter(isOutstanding);
  const overdue = props.actions.filter(isOverdue);
  const upcoming = CALLS.filter(call => call.date >= DEMO_DATE).sort((a, b) => `${a.date}${a.time}`.localeCompare(`${b.date}${b.time}`));
  const next = upcoming[0];
  const meta = kbLive.meta!;
  return <div className="view dashboard-view">
    <div className="dashboard-hero"><div><p className="eyebrow"><span className="tiny-star">✧</span> REAL RECORDS · AS OF {dateLabel(DEMO_DATE, { weekday: 'long', month: 'long', day: 'numeric' }).toUpperCase()}</p><h1>Overview<span className="gold-period">.</span></h1><p>The full Overview is Stage 3 and isn’t built on real data yet. These figures come straight from the intake test ({meta.windowStart ? `${dateLabel(meta.windowStart)} – ${dateLabel(meta.windowEnd)}` : 'full history'}).</p></div><button className="button button-gold" onClick={() => props.navigate('clients')}>Open client portfolio<ArrowUpRight size={15} /></button></div>
    <div className="stats-grid"><Stat label="Clients in the test" value={CLIENTS.length.toString().padStart(2, '0')} detail="Mapped and approved in the KB" icon={<Users size={17} />} /><Stat label="Upcoming calls" value={upcoming.length.toString().padStart(2, '0')} detail={next ? `Next: ${dateLabel(next.date)} · ${timeLabel(next.time)} IST` : 'None on the calendar'} icon={<CalendarDays size={17} />} /><Stat label="Open ClickUp tasks" value={outstanding.length.toString().padStart(2, '0')} detail={`${overdue.length} past their ClickUp due date`} tone="gold" icon={<ListChecks size={17} />} /><Stat label="Clients to check in on" value="—" detail="Health isn’t assessed yet (Stage 3)" tone="amber" icon={<HeartHandshake size={17} />} /></div>
    <div className="dashboard-grid">
      <div className="dashboard-main">
        <Panel title="The next conversation" eyebrow="FROM THE CALENDAR">
          {next ? <div className="featured-client"><Avatar client={clientById(next.clientId)} /><div><h3>{clientById(next.clientId).name}</h3><p>{next.type} <span>·</span> {dateLabel(next.date)} <span>·</span> {timeLabel(next.time)} IST{next.duration ? <> <span>·</span> {next.duration}</> : null}</p><p className="muted small-text">{next.objective}</p></div></div>
            : <Empty title="No upcoming calls">No client call is on the approved calendars.</Empty>}
        </Panel>
        <Panel title="Your clients, at a glance" eyebrow="THE PORTFOLIO" action={<button className="text-button" onClick={() => props.navigate('clients')}>View all clients<ArrowUpRight size={14} /></button>} className="portfolio-panel">
          <div className="table-scroll"><table className="portfolio-table"><thead><tr><th>Client</th><th>Open ClickUp tasks</th><th>Last contact</th><th /></tr></thead><tbody>{CLIENTS.map(c => <tr key={c.id}><td><button className="table-client" onClick={() => props.openClient(c.id)}><Avatar client={c} small /><span><strong>{c.name}</strong><small>{c.service}</small></span></button></td><td><span className="action-count">{outstanding.filter(a => a.clientId === c.id).length}</span><span className="muted small-text"> open</span></td><td className="muted small-text">{c.lastTouch ? dateLabel(c.lastTouch) : 'None in window'}</td><td><button className="icon-button" onClick={() => props.openClient(c.id)} aria-label={`Open ${c.name}`}><ChevronRight size={17} /></button></td></tr>)}</tbody></table></div>
        </Panel>
      </div>
      <div className="dashboard-aside">
        <Panel title="Upcoming calls" eyebrow="NEXT ON THE CALENDAR" action={<span className="count-pill">{upcoming.length}</span>} className="call-queue">
          {upcoming.length ? <div className="queue-list">{upcoming.slice(0, 6).map((call, index) => <button key={call.id} className={`queue-item ${index === 0 ? 'next' : ''}`} onClick={() => props.openClient(call.clientId, 'meetings')}><div className="queue-time"><strong>{dateLabel(call.date)}</strong><small>{timeLabel(call.time)}</small></div><div className="queue-line"><i /></div><div className="queue-info"><h3>{clientById(call.clientId).name}</h3><p>{call.type}</p></div><ArrowUpRight size={14} /></button>)}</div> : <Empty title="Nothing scheduled" />}
          <div className="panel-footnote">All times in IST</div>
        </Panel>
        <Panel title="Past due in ClickUp" eyebrow="FOLLOW THROUGH" className="loops-panel">
          {overdue.length ? overdue.slice(0, 4).map(action => <button className="loop-item" key={action.id} onClick={() => props.openClient(action.clientId, 'commitments')}><span className="loop-marker overdue"><ListChecks size={13} /></span><span><strong>{action.title}</strong><small>{clientById(action.clientId).name} · {action.owner || 'Unassigned'}</small><span className="loop-date text-amber">Due {dateLabel(action.due)} in ClickUp</span></span><ChevronRight size={14} /></button>) : <Empty title="Nothing past due" />}
          <button className="text-button" onClick={() => props.navigate('actions-v3')}>Open Action Hub<ArrowRight size={14} /></button>
        </Panel>
      </div>
    </div>
  </div>;
}
