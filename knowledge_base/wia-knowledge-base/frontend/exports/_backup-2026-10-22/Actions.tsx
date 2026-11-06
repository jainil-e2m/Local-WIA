import { ThemedDatePicker } from '../components/ThemedDatePicker';
import { ThemedSelect } from '../components/ThemedSelect';
import { useState } from 'react';
import { ArrowUpRight, Check, CheckCheck, ChevronRight, CircleCheck, Clock3, ListChecks, Plus } from 'lucide-react';
import { CLIENTS, DEMO_DATE, TEAM, clientById, dateLabel, isOutstanding, isOverdue } from '../data';
import { Avatar, Badge, Dialog, Empty, SearchField, Segmented, SourceLink } from '../components/UI';
import type { Action, WorkspaceProps } from '../types';
import WorkspaceTitle from '../components/WorkspaceTitle';
import './Actions.css';

export function ActionRows(props: WorkspaceProps & { rows: Action[]; compact?: boolean }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = props.actions.find(action => action.id === selectedId);
  return <><div className={`action-rows ${props.compact ? 'compact' : ''}`}>
    {props.rows.map(action => { const client = clientById(action.clientId); return <div className={`action-row ${!isOutstanding(action) ? 'completed' : ''}`} key={action.id}>
      <button className={`action-checkbox ${!isOutstanding(action) ? 'checked' : ''}`} aria-label={isOutstanding(action) ? `Mark ${action.title} done` : `Reopen ${action.title}`} title={isOutstanding(action) ? 'Mark done' : 'Reopen action'} onClick={() => props.updateAction(action.id, { status: isOutstanding(action) ? 'Done' : 'Open' })}>{!isOutstanding(action) && <Check size={13} />}</button>
      <div className="action-main"><button className="action-title" onClick={() => setSelectedId(action.id)}>{action.title}</button><div className="action-subline"><button onClick={() => props.openClient(client.id)}>{client.name}</button><span>·</span><span>{action.side === 'Client' ? 'Waiting on client' : action.owner}</span>{!action.acknowledged && isOutstanding(action) && <span className="text-amber">· Not acknowledged</span>}</div></div>
      <div className="action-due"><span className={isOverdue(action) ? 'text-amber' : ''}>{isOverdue(action) ? 'Overdue · ' : action.due === DEMO_DATE ? 'Today · ' : ''}{dateLabel(action.due)}</span><Badge tone={action.status === 'Verified' ? 'green' : action.status === 'Done' ? 'blue' : action.status === 'In progress' ? 'gold' : 'neutral'} dot={false}>{action.status}</Badge></div>
      <SourceLink id={action.sourceId} onOpen={props.showEvidence} />
      {action.status === 'Done' ? <button className="button button-small button-outline" onClick={() => { props.updateAction(action.id, { status: 'Verified' }); props.notify('Verification recorded in the preview.'); }}><CheckCheck size={13} />Verify</button> : <button className="icon-button" aria-label={`Details for ${action.title}`} onClick={() => setSelectedId(action.id)}><ChevronRight size={17} /></button>}
    </div>; })}{!props.rows.length && <Empty title="All clear in this view" />}
  </div>
  {selected && <Dialog title="A commitment to keep" subtitle={clientById(selected.clientId).name} drawer onClose={() => setSelectedId(null)}><Badge tone={isOverdue(selected) ? 'amber' : 'blue'}>{isOverdue(selected) ? 'Overdue' : selected.status}</Badge><h3 className="drawer-action-title">{selected.title}</h3><p className="body-copy">{selected.note}</p>
    <div className="form-stack"><label>Owner<ThemedSelect aria-label="Owner" value={selected.owner} onChange={value => props.updateAction(selected.id, { owner: value })}>{[...new Set([...TEAM, selected.owner])].map(owner => <option key={owner}>{owner}</option>)}</ThemedSelect></label><label>Due date<ThemedDatePicker label="Due date" value={selected.due} onChange={due => props.updateAction(selected.id, { due })} /></label><label>Status<ThemedSelect aria-label="Status" value={selected.status} onChange={value => props.updateAction(selected.id, { status: value as Action['status'] })}>{['Open', 'In progress', 'Done', 'Verified'].map(status => <option key={status}>{status}</option>)}</ThemedSelect></label></div>
    <div className="acknowledgement"><CircleCheck size={17} /><span>{selected.acknowledged ? 'Acknowledged by the owner' : 'Awaiting acknowledgement'}</span><button className="text-button" onClick={() => props.updateAction(selected.id, { acknowledged: !selected.acknowledged })}>{selected.acknowledged ? 'Undo' : 'Acknowledge'}</button></div>
    <div className="source-section"><p className="small-label">WHERE THE COMMITMENT CAME FROM</p><SourceLink id={selected.sourceId} onOpen={id => { setSelectedId(null); props.showEvidence(id); }} label="Read the original context" /></div>
  </Dialog>}</>;
}

export function ActionRegisterTitle() {
  return <WorkspaceTitle title="Action Register" description="Track what WIA owes each client, what's needed from the client, and who's responsible for the next step." />;
}

function ClientActionGroups(props: WorkspaceProps & { rows: Action[]; filter: string; narrowed: boolean; onAddAction: () => void }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const completed = props.filter === 'done';
  const actionLabel = completed ? 'completed' : props.filter === 'open' ? 'pending' : 'matching';
  const groups = CLIENTS.map(client => ({ client, actions: props.rows.filter(action => action.clientId === client.id) }))
    .filter(group => group.actions.length > 0)
    .sort((a, b) => completed ? a.client.name.localeCompare(b.client.name) : a.actions[0].due.localeCompare(b.actions[0].due) || a.client.name.localeCompare(b.client.name));

  return <section className="client-action-section" aria-label="Actions by client">
    <div className="client-action-intro"><div><h2>{completed ? 'Completed by client' : props.filter === 'open' ? 'Pending by client' : 'Actions by client'}</h2><p>Select a client to view their {actionLabel} actions.</p></div><button className="button button-gold add-client-action" onClick={props.onAddAction}><Plus size={16} />Add an action</button></div>
    <div className="panel client-action-panel">
      {groups.length ? <>
        <div className="client-action-columns" aria-hidden="true"><span>CLIENT</span><span>{actionLabel.toUpperCase()} ACTIONS</span><span>{completed ? 'COMPLETION' : 'FOLLOW-UP'}</span><span>{completed ? 'OWNERS' : 'NEXT DUE'}</span><span /></div>
        <ul className="client-action-list">{groups.map(({ client, actions }) => {
          const expanded = expandedId === client.id;
          const pending = actions.filter(isOutstanding);
          const overdue = actions.filter(isOverdue).length;
          const waiting = pending.filter(action => action.side === 'Client').length;
          const done = actions.filter(action => action.status === 'Done').length;
          const verified = actions.filter(action => action.status === 'Verified').length;
          const owners = [...new Set(actions.map(action => action.owner))];
          const nextDue = pending[0]?.due;
          const detailsId = `client-actions-${client.id}`;
          return <li className={`client-action-group ${expanded ? 'is-expanded' : ''}`} key={client.id}>
            <button className="client-action-toggle" id={`${detailsId}-toggle`} aria-expanded={expanded} aria-controls={detailsId} onClick={() => setExpandedId(expanded ? null : client.id)}>
              <span className="client-action-identity"><Avatar client={client} small /><span><strong>{client.name}</strong><small>{client.service}</small></span></span>
              <span className="client-action-total"><strong>{actions.length.toString().padStart(2, '0')}</strong><span className="sr-only"> {actionLabel} {actions.length === 1 ? 'action' : 'actions'}</span></span>
              <span className="client-action-signals">{completed ? <><span>{done} awaiting verification</span><span>{verified} verified</span></> : <><span className={overdue ? 'text-amber' : ''}>{overdue} overdue</span><span>{waiting} waiting on client</span></>}</span>
              <span className="client-action-next"><small>{completed ? 'Owners' : nextDue ? 'Next due' : 'Pending work'}</small><span>{completed ? owners.join(', ') : nextDue ? dateLabel(nextDue) : 'None'}</span></span>
              <ChevronRight className="client-action-chevron" size={18} aria-hidden="true" />
            </button>
            <div id={detailsId} role="region" aria-labelledby={`${detailsId}-toggle`} hidden={!expanded}>
              {expanded && <div className="client-action-details"><div className="action-table-heading"><span aria-hidden="true" /><span>ACTION ITEM</span><span>DUE & STATUS</span><span>EVIDENCE</span><span className="sr-only">Details</span></div><ActionRows {...props} rows={actions} /><div className="client-action-details-footer"><button className="text-button" onClick={() => props.openClient(client.id, 'commitments')}>Open client record<ArrowUpRight size={14} /></button></div></div>}
            </div>
          </li>;
        })}</ul>
      </> : <Empty title="No clients match this view">{props.narrowed ? 'Try another client, action or owner, or change the status filter.' : completed ? 'Clients will appear here when they have Done or Verified actions.' : 'There are no actions in this category.'}</Empty>}
    </div>
  </section>;
}

export default function Actions(props: WorkspaceProps & { addAction: (action: Action) => void }) {
  const [filter, setFilter] = useState('open');
  const [query, setQuery] = useState('');
  const [owner, setOwner] = useState('all');
  const [adding, setAdding] = useState(false);
  const pendingActions = props.actions.filter(isOutstanding);
  const overdueActions = props.actions.filter(isOverdue);
  const waitingActions = pendingActions.filter(action => action.side === 'Client');
  const completedActions = props.actions.filter(action => !isOutstanding(action));
  const awaitingVerification = props.actions.filter(action => action.status === 'Done');
  const pendingClients = new Set(pendingActions.map(action => action.clientId)).size;
  const rows = props.actions.filter(a => (filter === 'all' || filter === 'open' && isOutstanding(a) || filter === 'overdue' && isOverdue(a) || filter === 'waiting' && a.side === 'Client' && isOutstanding(a) || filter === 'done' && !isOutstanding(a)) && (owner === 'all' || a.owner === owner) && `${a.title} ${clientById(a.clientId).name}`.toLowerCase().includes(query.toLowerCase())).sort((a, b) => a.due.localeCompare(b.due));
  return <div className="view action-register-view">
    <section className="action-register-metrics" aria-label="Action summary">
      <div className="action-metric"><div className="action-metric-label"><span>Pending actions</span><span className="action-metric-icon"><ListChecks size={18} /></span></div><div className="action-metric-value"><strong>{pendingActions.length.toString().padStart(2, '0')}</strong><p>Across {pendingClients} {pendingClients === 1 ? 'client' : 'clients'}</p></div></div>
      <div className="action-metric"><div className="action-metric-label"><span>Overdue</span><span className="action-metric-icon"><Clock3 size={18} /></span></div><div className="action-metric-value"><strong>{overdueActions.length.toString().padStart(2, '0')}</strong><p>Past the agreed due date</p></div></div>
      <div className="action-metric"><div className="action-metric-label"><span>Awaiting verification</span><span className="action-metric-icon"><CheckCheck size={18} /></span></div><div className="action-metric-value"><strong>{awaitingVerification.length.toString().padStart(2, '0')}</strong><p>Completed, pending a follow-up check</p></div></div>
    </section>
    <div className="action-register-controls"><Segmented label="Action status filter" value={filter} onChange={setFilter} options={[{ id: 'open', label: 'Pending', count: pendingActions.length }, { id: 'overdue', label: 'Overdue', count: overdueActions.length }, { id: 'waiting', label: 'Waiting on client', count: waitingActions.length }, { id: 'done', label: 'Completed', count: completedActions.length }, { id: 'all', label: 'All', count: props.actions.length }]} /><div className="action-register-filters"><SearchField label="Search clients or actions" placeholder="Search clients or actions" value={query} onChange={setQuery} /><label className="sr-only" htmlFor="action-owner">Filter by owner</label><ThemedSelect aria-label="Filter by owner" id="action-owner" value={owner} onChange={value => setOwner(value)}><option value="all">All owners</option>{[...new Set(props.actions.map(a => a.owner))].map(o => <option key={o}>{o}</option>)}</ThemedSelect></div></div>
    <ClientActionGroups key={filter} {...props} rows={rows} filter={filter} narrowed={!!query.trim() || owner !== 'all'} onAddAction={() => setAdding(true)} /><div className="quiet-footer"><CheckCheck size={15} />“Done” records completion. “Verified” records a separate follow-up check.</div>
    {adding && <Dialog title="Give the next step an owner." subtitle="Add a sample action" onClose={() => setAdding(false)}><form className="form-stack" onSubmit={event => {
      event.preventDefault(); const data = new FormData(event.currentTarget); const clientId = data.get('client') as string; const title = String(data.get('title')).trim(); if (!title) return;
      props.addAction({ id: `local-${crypto.randomUUID()}`, clientId, title, owner: String(data.get('owner')), due: String(data.get('due')), side: 'WIA', status: 'Open', acknowledged: false, sourceId: clientById(clientId).profileSource, note: 'Manually added in the frontend preview. The linked background provides client context; it is not evidence that this action was agreed.' }); setAdding(false); props.notify('Action added to your preview workspace.');
    }}><label>What needs to happen?<input name="title" required maxLength={160} placeholder="Write a concrete next step" /></label><label>Client<ThemedSelect aria-label="Client" name="client">{CLIENTS.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</ThemedSelect></label><div className="form-two-col"><label>Owner<ThemedSelect aria-label="Owner" name="owner">{TEAM.map(person => <option key={person}>{person}</option>)}</ThemedSelect></label><label>Agreed due date<ThemedDatePicker label="Agreed due date" name="due" defaultValue={DEMO_DATE} /></label></div><button className="button button-primary" type="submit"><Plus size={15} />Add action</button></form></Dialog>}
  </div>;
}
