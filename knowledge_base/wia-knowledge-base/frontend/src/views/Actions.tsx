import { ThemedDatePicker } from '../components/ThemedDatePicker';
import { ThemedSelect } from '../components/ThemedSelect';
import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { CalendarDays, AlertTriangle, AtSign, RotateCcw, Hash, Send, ArrowUpRight, BellOff, CalendarClock, Check, CheckCheck, ChevronRight, CircleCheck, Clock3, Hand, Inbox, Plus, RefreshCw, ShieldCheck, Sparkles, UserX, Users } from 'lucide-react';
import { CALLS, CLIENTS, DEMO_DATE, PROGRAMME_TASKS, REVIEW_ITEMS, SLACK_ADMINS, SLACK_CHANNELS, SYNC_STATUS, TEAM, VIEWERS, addDays, clientById, dateLabel, daysBetween, isOutstanding, isOverdue, ownerLabel } from '../data';
import { Avatar, Badge, Dialog, Empty, SearchField, Segmented, SourceLink } from '../components/UI';
import type { Action, ActionOrigin, ProgrammeTask, ReviewItem, Tone, WorkspaceProps } from '../types';
import WorkspaceTitle from '../components/WorkspaceTitle';
import { OwnerPick, SlackPing } from '../mvpActions';
import './Actions.css';
import { me } from '../auth';

// Business rules shown in this preview (see kb_tab_scope/01-action-register.md).
const STALE_DAYS = 30;
const ACK_GRACE_DAYS = 1;
const CALL_WINDOW_DAYS = 2;
export const VERIFY_TYPES = ['Landing page', 'LeadLock / GHL setup', 'Tracking / UTM fix', 'Ad / campaign change', 'Client approval'];

export const isSnoozed = (a: Action) => !!a.snoozedUntil && a.snoozedUntil > DEMO_DATE && isOutstanding(a);
export const nextCallFor = (clientId: string) => CALLS.filter(c => c.clientId === clientId && c.date >= DEMO_DATE).sort((a, b) => `${a.date}${a.time}`.localeCompare(`${b.date}${b.time}`))[0];
export const dueBeforeCall = (a: Action) => { const call = nextCallFor(a.clientId); return isOutstanding(a) && !!call && daysBetween(DEMO_DATE, call.date) <= CALL_WINDOW_DAYS; };
export const awaitingAck = (a: Action) => isOutstanding(a) && a.side === 'WIA' && !!a.owner && !a.acknowledged && !!a.assignedOn && daysBetween(a.assignedOn) >= ACK_GRACE_DAYS;
export const awaitingVerification = (a: Action) => a.status === 'Done' && !!a.verifyRequired;
const isClosed = (a: Action) => a.status === 'Verified' || (a.status === 'Done' && !a.verifyRequired);
const statusTone = (a: Action): Tone => a.status === 'Verified' ? 'green' : a.status === 'Done' ? 'blue' : a.status === 'Blocked' ? 'rose' : a.status === 'In progress' ? 'gold' : 'neutral';
const isTeam = (name: string) => TEAM.includes(name);

type TileId = 'overdue' | 'week' | 'ack' | 'waiting' | 'review' | 'verify';
const TILES: { id: TileId; label: string; detail: string; icon: typeof Clock3; test?: (a: Action) => boolean }[] = [
  { id: 'overdue', label: 'Overdue', detail: 'Known date passed. No-date items never count', icon: Clock3, test: isOverdue },
  { id: 'week', label: 'Due this week', detail: 'Known date in the next 7 days', icon: CalendarClock, test: a => isOutstanding(a) && !!a.due && a.due >= DEMO_DATE && a.due <= addDays(DEMO_DATE, 6) },
  { id: 'ack', label: 'Awaiting acknowledgement', detail: `Owner hasn't accepted after ${ACK_GRACE_DAYS} day`, icon: Hand, test: awaitingAck },
  { id: 'waiting', label: 'Waiting on client', detail: 'Client-side items still open', icon: Users, test: a => isOutstanding(a) && a.side === 'Client' },
  { id: 'review', label: 'Needs review', detail: 'Unclear, stale or proposed items', icon: Inbox },
  { id: 'verify', label: 'Awaiting verification', detail: 'Done, flagged type, not yet checked', icon: ShieldCheck, test: awaitingVerification },
];

export function OriginChip({ origin }: { origin?: ActionOrigin }) {
  if (!origin) return null;
  return <span className={`origin-chip origin-${origin.toLowerCase().replace(/\s+/g, '-')}`}>{origin === 'AI proposal' && <Sparkles size={10} />}{origin}</span>;
}

function DueCell({ action }: { action: Action }) {
  const overdue = isOverdue(action);
  const label = !action.due ? 'No date' : `${overdue ? 'Overdue · ' : action.due === DEMO_DATE ? 'Today · ' : ''}${dateLabel(action.due)}`;
  return <div className="action-due"><span className={overdue ? 'text-amber' : !action.due ? 'muted' : ''}>{action.conflict && <AlertTriangle size={11} className="conflict-icon" aria-label="Sources disagree on the deadline" />}{label}</span><Badge tone={statusTone(action)} dot={false}>{action.status}</Badge></div>;
}

export type RowProps = WorkspaceProps & { rows: Action[]; compact?: boolean; viewer?: string; onRequestDone?: (a: Action) => void; onRequestVerify?: (a: Action) => void; onRequestNotify?: (ctx: NotifyContext) => void; deadlineRequests?: boolean; presentation?: 'drawer' | 'modal'; table?: boolean };

const initialsOf = (name?: string) => (name || '?').split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase();

/** Action Hub list look (one client, so no Client column): same rows, same window, Done and reopen. */
function ActionTable({ rows, viewer, open, toggle }: { rows: Action[]; viewer?: string; open: (a: Action) => void; toggle: (a: Action) => void }) {
  return <div className="rb-table-wrap rb-vars"><table className="rb-table">
    <thead><tr><th className="rb-col-check"><span className="sr-only">Done</span></th><th>Action item</th><th>Assigned to</th><th>Due date</th><th>Status</th><th><span className="sr-only">Open</span></th></tr></thead>
    <tbody>{rows.map(a => { const done = !isOutstanding(a); const mine = !!viewer && a.owner === viewer; const bucket = done ? 'done' : a.side === 'Client' ? 'client' : mine ? 'mine' : 'team';
      return <tr key={a.id} onClick={() => open(a)}>
        <td className="rb-col-check" onClick={e => e.stopPropagation()}><button className={`rb-check ${done ? 'checked' : ''}`} aria-label={done ? `Reopen “${a.title}”` : `Mark “${a.title}” done`} title={done ? 'Reopen' : 'Mark done'} onClick={() => toggle(a)}>{done && <Check size={11} />}</button></td>
        <td><button className="rb-title" onClick={e => { e.stopPropagation(); open(a); }}>{a.title}</button></td>
        <td><span className="rb-person"><span className={`rb-avatar ${mine ? 'is-me' : ''}`}>{initialsOf(a.owner)}</span><strong>{mine ? 'You' : a.side === 'Client' ? `Waiting on ${a.owner || 'client'}` : a.owner || 'Unassigned'}</strong></span></td>
        <td><span className={`rb-due ${isOverdue(a) ? 'is-late' : ''}`}><CalendarDays size={13} />{a.due ? dateLabel(a.due, { day: 'numeric', month: 'short', year: 'numeric' }) : 'No date'}</span></td>
        <td><span className={`rb-pill status-${bucket}`}>{{ mine: 'Pending (You)', team: 'Pending (Team)', client: 'Pending (Client)', done: 'Completed' }[bucket]}</span></td>
        <td><ChevronRight size={15} className="rb-chev" /></td>
      </tr>; })}</tbody>
  </table>{!rows.length && <Empty title="All clear in this view" />}</div>;
}

export function ActionRows(props: RowProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [doneFor, setDoneFor] = useState<Action | null>(null);
  const [verifyFor, setVerifyFor] = useState<Action | null>(null);
  const selected = props.actions.find(action => action.id === selectedId);
  // In modal mode, rows behave like the Action Hub: Done and Verify ask for their basis first.
  const hub = props.presentation === 'modal';
  const requestDone = (a: Action) => props.onRequestDone ? props.onRequestDone(a) : hub ? setDoneFor(a) : props.updateAction(a.id, { status: 'Done' });
  const requestVerify = (a: Action) => props.onRequestVerify ? props.onRequestVerify(a) : hub ? setVerifyFor(a) : props.updateAction(a.id, { status: 'Verified' });
  const reopen = (a: Action) => props.updateAction(a.id, { status: 'Open', verification: undefined, history: [...(a.history || []), { date: DEMO_DATE, text: `Reopened${props.viewer ? ` by ${me(props.viewer)}` : ''}; any earlier verification is superseded.` }] });
  return <>{props.table ? <ActionTable rows={props.rows} viewer={props.viewer} open={a => setSelectedId(a.id)} toggle={a => isOutstanding(a) ? requestDone(a) : reopen(a)} /> : <div className={`action-rows ${props.compact ? 'compact' : ''}`}>
    {props.rows.map(action => {
      const client = clientById(action.clientId);
      const ackAge = action.assignedOn ? daysBetween(action.assignedOn) : 0;
      const waitAge = action.side === 'Client' && action.lastActivity ? daysBetween(action.lastActivity) : 0;
      return <div className={`action-row ${!isOutstanding(action) ? 'completed' : ''}`} key={action.id}>
        <button className={`action-checkbox ${!isOutstanding(action) ? 'checked' : ''}`} aria-label={isOutstanding(action) ? `Mark ${action.title} done` : `Reopen ${action.title}`} title={isOutstanding(action) ? 'Mark done' : 'Reopen action'} onClick={() => isOutstanding(action) ? requestDone(action) : reopen(action)}>{!isOutstanding(action) && <Check size={13} />}</button>
        <div className="action-main"><button className="action-title" onClick={() => setSelectedId(action.id)}>{action.title}</button>
          <div className="action-subline">
            <button onClick={() => props.openClient(client.id)}>{client.name}</button><span>·</span>
            <span className={!action.owner ? 'text-amber' : ''}>{action.side === 'Client' ? `Waiting on ${action.owner || 'client'}` : ownerLabel(action.owner)}</span>
            {action.suggestedOwner && <span className="row-flag" title={action.suggestedWhy}>Suggested: {action.suggestedOwner}</span>}
            {!props.compact && <OriginChip origin={action.origin} />}
            {awaitingAck(action) && <span className="row-flag flag-amber">Not acknowledged · {ackAge}d</span>}
            {isOutstanding(action) && waitAge > 0 && <span className="row-flag">Waiting {waitAge}d</span>}
            {isSnoozed(action) && <span className="row-flag"><BellOff size={10} />Snoozed to {dateLabel(action.snoozedUntil!)}</span>}
            {action.verifyRequired && isOutstanding(action) && !props.compact && <span className="row-flag flag-blue"><ShieldCheck size={10} />Needs verification</span>}
            {dueBeforeCall(action) && !props.compact && <span className="row-flag flag-gold"><CalendarClock size={10} />Before {dateLabel(nextCallFor(action.clientId)!.date)} call</span>}
          </div></div>
        <DueCell action={action} />
        {action.sourceId ? <SourceLink id={action.sourceId} onOpen={props.showEvidence} /> : <OriginChip origin={action.origin} />}
        {awaitingVerification(action) ? <button className="button button-small button-outline" onClick={() => requestVerify(action)}><CheckCheck size={13} />Verify</button> : <button className="icon-button" aria-label={`Details for ${action.title}`} onClick={() => setSelectedId(action.id)}><ChevronRight size={17} /></button>}
      </div>;
    })}{!props.rows.length && <Empty title="All clear in this view" />}
  </div>}
  {selected && <ActionDrawer {...props} action={selected} close={() => setSelectedId(null)} requestDone={requestDone} requestVerify={requestVerify} />}
  {doneFor && <DoneDialog action={doneFor} viewer={props.viewer} updateAction={props.updateAction} notify={props.notify} close={() => setDoneFor(null)} />}
  {verifyFor && <VerifyDialog action={verifyFor} viewer={props.viewer} updateAction={props.updateAction} notify={props.notify} close={() => setVerifyFor(null)} />}</>;
}

export function ActionDrawer(props: RowProps & { action: Action; close: () => void; requestDone: (a: Action) => void; requestVerify: (a: Action) => void }) {
  if (props.presentation === 'modal') return <ActionDetailModal {...props} />;
  return <ActionDetailDrawer {...props} />;
}

type ActionDetailProps = Parameters<typeof ActionDrawer>[0];
type StatusBucket = 'mine' | 'team' | 'client';
const STATUS_MOVES: [StatusBucket, string][] = [['mine', 'Pending (you)'], ['team', 'Pending (team)'], ['client', 'Pending (client)']];

/** The v2 detail view uses the shared large modal; older layouts retain their drawer. */
function ActionDetailModal(props: ActionDetailProps) {
  const a = props.action;
  const viewer = props.viewer;
  const [note, setNote] = useState('');
  const [description, setDescription] = useState(a.note);
  const [statusOpen, setStatusOpen] = useState(false);
  const [picking, setPicking] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const descriptionId = useId();
  const outstanding = isOutstanding(a);
  const programme = a.kind === 'programme';
  // Tick once a second while a Slack ping is recent, so "Sent N mins ago" and the cooldown stay current.
  useEffect(() => { if (!a.slackPingedAt) return; setNow(Date.now()); const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, [a.slackPingedAt]);
  useEffect(() => {
    if (!statusOpen) return;
    const close = (event: PointerEvent) => { if (!(event.target as HTMLElement).closest?.('.mvp-status')) setStatusOpen(false); };
    document.addEventListener('pointerdown', close, true);
    return () => document.removeEventListener('pointerdown', close, true);
  }, [statusOpen]);
  const canAck = !!viewer && viewer === a.owner;
  const log = (text: string) => [...(a.history || []), { date: DEMO_DATE, at: new Date().toISOString(), text }];
  const current: StatusBucket = a.side === 'Client' ? 'client' : a.owner === viewer ? 'mine' : 'team';
  const moveTo = (bucket: StatusBucket, label: string) => {
    if (bucket === 'team') { setPicking(true); return; }
    setStatusOpen(false);
    props.updateAction(a.id, { side: bucket === 'client' ? 'Client' : 'WIA', ...(bucket === 'mine' && viewer ? { owner: viewer } : {}), history: log(`Moved to ${label} by ${me(viewer) || 'Someone'}.`) });
    props.notify(`Moved to ${label}.`);
  };
  const assignTeam = (owner: string) => {
    setStatusOpen(false); setPicking(false);
    props.updateAction(a.id, { side: 'WIA', owner, acknowledged: false, ackMethod: undefined, assignedOn: DEMO_DATE, history: log(`Moved to Pending (team) by ${me(viewer) || 'Someone'}; assigned to ${owner}. New owner must acknowledge.`) });
    props.notify(`Moved to Pending (team) · assigned to ${owner}.`);
  };
  const activity = [
    ...(a.history || []).map((entry, index) => ({ ...entry, kind: 'change' as const, by: '', order: index })),
    ...(a.notes || []).map((entry, index) => ({ ...entry, kind: 'comment' as const, order: (a.history?.length || 0) + index })),
  ].sort((x, y) => (y.at || y.date).localeCompare(x.at || x.date) || y.order - x.order);
  const activityDate = (entry: { at?: string; date: string }) => entry.at
    ? new Date(entry.at).toLocaleString('en-IN', { timeZone: 'Asia/Calcutta', day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' })
    : dateLabel(entry.date, { day: 'numeric', month: 'short', year: 'numeric' });
  const progressControls = <>
    {outstanding && (a.side === 'Client' || a.owner !== viewer) && <SlackPing action={a} viewer={viewer} now={now} update={props.updateAction} log={log} />}
    {outstanding && <div className="mvp-status" onKeyDown={event => { if (event.key === 'Escape' && statusOpen) { event.stopPropagation(); setStatusOpen(false); } }}>
      <button type="button" className="button button-small button-outline mvp-status-trigger" aria-haspopup="menu" aria-expanded={statusOpen} onClick={() => { setStatusOpen(o => !o); setPicking(false); }}>Change status<span className="mvp-status-caret" aria-hidden>▴</span></button>
      {statusOpen && <div className={`mvp-status-menu ${picking ? 'is-picking' : ''}`} role="menu">{picking
        ? <OwnerPick item={a} viewer={viewer} current={a.owner} onBack={() => setPicking(false)} onPick={assignTeam} />
        : STATUS_MOVES.filter(([id]) => id !== current && !(programme && id === 'client')).map(([id, label]) => <button key={id} type="button" role="menuitem" className="mvp-status-option" onClick={() => moveTo(id, label)}><span className={`mvp-status-dot mvp-status-dot-${id}`} />{label}{id === 'team' && <span className="mvp-status-more" aria-hidden>›</span>}</button>)}</div>}
    </div>}
    {outstanding && <button className="button button-small button-primary" onClick={() => { props.close(); props.requestDone(a); }}><Check size={14} />Mark done…</button>}
    {awaitingVerification(a) && <button className="button button-small button-primary" onClick={() => { props.close(); props.requestVerify(a); }}><CheckCheck size={14} />Verify…</button>}
    {!outstanding && <button className="button button-small button-outline" onClick={() => { props.updateAction(a.id, { status: 'Open', verification: undefined, history: log(`Reopened${viewer ? ` by ${me(viewer)}` : ''}; any earlier verification is superseded.`) }); props.notify('Reopened. It is back in the pending list.'); }}><RotateCcw size={14} />Reopen</button>}
  </>;

  // Recurring internal upkeep is never shown as overdue.
  const overdue = isOverdue(a) && !a.recurring;
  return <Dialog title={a.title} subtitle={programme ? `Internal · ${a.programme}` : `Action Hub · ${clientById(a.clientId).name}`} size="lg" className="action-detail-modal" onClose={props.close}
    meta={<><Badge tone={overdue ? 'amber' : statusTone(a)}>{overdue ? `Overdue · ${a.status}` : a.status}</Badge>{programme
      ? <><Badge tone="neutral" dot={false}>Internal</Badge>{a.recurring && <Badge tone="neutral" dot={false}>{a.recurring}</Badge>}</>
      : <><Badge tone={a.priority === 'High' ? 'amber' : 'neutral'} dot={false}>Priority: {a.priority || 'Not set'}</Badge><Badge tone={a.verifyRequired ? 'blue' : 'neutral'} dot={false}>{awaitingVerification(a) ? 'Awaiting verification' : a.verifyRequired ? 'Verification required' : 'Closes at Done'}</Badge></>}</>}
    footer={<><button className="button button-small button-outline" onClick={props.close}>Close</button><div className="action-detail-controls">{progressControls}</div></>}>
    <div className="action-detail-panel" role="region" aria-label="Action details and history" tabIndex={0}>
      <div className="action-detail-grid">
        <div className="action-detail-main">
          <section className="action-detail-section"><h3><label htmlFor={descriptionId}>Description</label></h3>
            <textarea id={descriptionId} className="action-detail-description" value={description} rows={5} onChange={event => setDescription(event.target.value)} placeholder="Describe what needs to happen" />
            {description !== a.note && <div className="action-detail-description-actions"><button className="button button-small button-primary" onClick={() => { props.updateAction(a.id, { note: description, history: log(`${viewer || 'Someone'} updated the description from “${a.note || '(empty)'}” to “${description || '(empty)'}”.`) }); props.notify('Description saved.'); }}>Save description</button><button className="text-button" onClick={() => setDescription(a.note)}>Cancel</button></div>}
          </section>
          {programme && <p className="hint">Accelerator upkeep is internal work: it isn't counted as any client's open action{a.recurring ? ', and recurring tasks are never shown as overdue' : ''}.</p>}
          {(a.completionBasis || a.verification) && <section className="action-detail-section"><h3>Completion & check</h3>
            {a.completionBasis && <p className="body-copy">{a.completionBasis}</p>}
            {a.verification && <p className="action-detail-verification"><ShieldCheck size={15} /><span><strong>Verified by {a.verification.by} · {dateLabel(a.verification.date)}</strong>{a.verification.check}</span></p>}
          </section>}
        </div>
        <aside className="action-detail-assignment" aria-label="Responsibility and deadline">
          <div className="action-detail-owner-heading"><h3>Owner & deadline</h3><button type="button" className={`action-detail-acceptance ${a.owner && a.acknowledged ? 'is-acknowledged' : ''}`} disabled={!a.owner || a.acknowledged || !canAck || !isTeam(a.owner)} aria-label={!a.owner ? 'Unassigned' : a.acknowledged ? 'Acknowledged' : canAck ? 'Assigned — click to acknowledge' : `Assigned — awaiting ${a.owner}'s acknowledgement`} title={!a.owner ? 'Unassigned' : a.acknowledged ? `Acknowledged${a.ackMethod ? ` · ${a.ackMethod}` : ''}` : canAck && isTeam(a.owner) ? 'Assigned to you. Click to acknowledge.' : `Assigned to ${a.owner}. Awaiting acknowledgement.`} onClick={() => { if (!canAck || a.acknowledged || !isTeam(a.owner)) return; props.updateAction(a.id, { acknowledged: true, ackMethod: 'KB · Acknowledge button', history: log(`${a.owner} acknowledged in the KB.`) }); }}>{!a.owner ? <UserX size={17} /> : a.acknowledged ? <CheckCheck size={17} /> : <Check size={17} />}<span>{!a.owner ? 'Unassigned' : a.acknowledged ? 'Acknowledged' : 'Assigned'}</span></button></div>
          <div className="form-stack"><label>Owner<ThemedSelect aria-label="Owner" value={a.owner} onChange={value => props.updateAction(a.id, { owner: value, acknowledged: false, ackMethod: undefined, assignedOn: value ? DEMO_DATE : undefined, history: log(`Owner changed from ${ownerLabel(a.owner)} to ${ownerLabel(value)}${viewer ? ` by ${me(viewer)}` : ''}. New owner must acknowledge.`) })}><option value="">Unassigned</option>{[...new Set([...TEAM, ...(a.owner ? [a.owner] : [])])].map(owner => <option key={owner} value={owner}>{owner}</option>)}</ThemedSelect></label>
            {props.deadlineRequests && !isAdmin(viewer) ? <><div className="action-detail-deadline"><span>Agreed deadline</span><strong className={isOverdue(a) ? 'text-amber' : ''}>{a.due ? dateLabel(a.due, { day: 'numeric', month: 'short', year: 'numeric' }) : 'No date agreed'}</strong>{!a.due && <p className="hint">This action is not overdue without an agreed date.</p>}</div>{!a.deadlineRequest && outstanding && <details className="action-detail-request"><summary>Request a new deadline</summary><DeadlineRequest {...props} compact /></details>}</> : <label>Agreed deadline<ThemedDatePicker label="Agreed deadline" value={a.due} clearable onChange={due => props.updateAction(a.id, { due, history: log(due ? `Deadline set to ${dateLabel(due)}${viewer ? ` by ${me(viewer)}` : ''}.` : `Deadline cleared${viewer ? ` by ${me(viewer)}` : ''}.`) })} /></label>}
          </div>
          {a.deadlineRequest && <DeadlineRequestNote action={a} viewer={viewer} updateAction={props.updateAction} notify={props.notify} />}
          {outstanding && props.onRequestNotify && <button className="button button-small button-outline" onClick={() => { props.close(); props.onRequestNotify!({ mode: 'single', title: a.title, actions: [a] }); }}><Send size={13} />Notify on Slack…</button>}
        </aside>
      </div>

      {a.conflict && <section className="conflict-box action-detail-conflict"><h3><AlertTriangle size={14} />Sources disagree</h3><p>{a.conflict}</p></section>}

      <div className="action-detail-history">
        <h3>History</h3>
        <form className="action-detail-comment-form form-stack" onSubmit={event => { event.preventDefault(); if (!note.trim()) return; props.updateAction(a.id, { notes: [...(a.notes || []), { by: me(viewer) || 'You', date: DEMO_DATE, at: new Date().toISOString(), text: note.trim() }] }); setNote(''); props.notify('Comment added.'); }}><textarea value={note} onChange={event => setNote(event.target.value)} rows={1} aria-label="Add a comment" placeholder="Add a comment…" /><button className="button button-small button-outline" disabled={!note.trim()} type="submit">Post comment</button></form>
        {activity.length ? <ol className="action-detail-timeline" aria-label="History entries">{activity.map(entry => <li key={`${entry.kind}-${entry.order}`} className={`is-${entry.kind}`}><span className="action-detail-timeline-icon" aria-hidden="true">{entry.kind === 'comment' ? <AtSign size={13} /> : <RotateCcw size={13} />}</span><div><div className="action-detail-event-meta"><strong>{entry.kind === 'comment' ? `${entry.by} commented` : 'Task change'}</strong><time dateTime={entry.at || entry.date}>{activityDate(entry)}</time></div><p>{entry.text}</p></div></li>)}</ol> : <p className="hint">No history yet.</p>}
      </div>
    </div>
  </Dialog>;
}

function ActionDetailDrawer(props: ActionDetailProps) {
  const a = props.action;
  const [note, setNote] = useState('');
  const [snoozeDays, setSnoozeDays] = useState('7');
  const [snoozeReason, setSnoozeReason] = useState('Waiting on a third party');
  const viewer = props.viewer;
  const call = nextCallFor(a.clientId);
  const log = (text: string) => [...(a.history || []), { date: DEMO_DATE, text }];
  const canAck = !!viewer && viewer === a.owner;
  return <Dialog title="A commitment to keep" subtitle={clientById(a.clientId).name} drawer onClose={props.close}>
    <div className="drawer-badges"><Badge tone={isOverdue(a) ? 'amber' : statusTone(a)}>{isOverdue(a) ? 'Overdue' : a.status}</Badge>{a.actionType && <Badge tone="neutral" dot={false}>{a.actionType}</Badge>}{a.verifyRequired ? <Badge tone="blue" dot={false}>Verification required</Badge> : <Badge tone="neutral" dot={false}>Closes at Done</Badge>}</div>
    <h3 className="drawer-action-title">{a.title}</h3><p className="body-copy">{a.note}</p>

    {a.quote && <div className="drawer-section"><p className="small-label">WHERE IT CAME FROM</p><blockquote className="origin-quote">“{a.quote}”</blockquote><div className="drawer-inline"><OriginChip origin={a.origin} />{a.sourceId && <SourceLink id={a.sourceId} onOpen={id => { props.close(); props.showEvidence(id); }} label="Open the original" />}{a.clickupUrl && <a className="text-button" href={a.clickupUrl} target="_blank" rel="noreferrer">ClickUp task<ArrowUpRight size={11} /></a>}</div></div>}

    {a.conflict && <div className="drawer-section conflict-box"><p className="small-label"><AlertTriangle size={11} /> SOURCES DISAGREE</p><p>{a.conflict}</p></div>}

    <div className="form-stack">
      <label>Owner<ThemedSelect aria-label="Owner" value={a.owner} onChange={value => props.updateAction(a.id, { owner: value, acknowledged: false, ackMethod: undefined, assignedOn: value ? DEMO_DATE : undefined, history: log(`Owner changed from ${ownerLabel(a.owner)} to ${ownerLabel(value)}${viewer ? ` by ${me(viewer)}` : ''}. New owner must acknowledge.`) })}><option value="">Unassigned</option>{[...new Set([...TEAM, ...(a.owner ? [a.owner] : [])])].map(owner => <option key={owner} value={owner}>{owner}</option>)}</ThemedSelect></label>
      {props.deadlineRequests && !isAdmin(viewer) ? <DeadlineRequest {...props} action={a} /> : <label>Agreed deadline<ThemedDatePicker label="Agreed deadline" value={a.due} clearable onChange={due => props.updateAction(a.id, { due, history: log(due ? `Deadline set to ${dateLabel(due)}${viewer ? ` by ${me(viewer)}` : ''}.` : `Deadline cleared${viewer ? ` by ${me(viewer)}` : ''}.`) })} /></label>}
    </div>

    <div className="drawer-section"><p className="small-label">ACKNOWLEDGEMENT</p>
      <div className="acknowledgement"><CircleCheck size={17} /><span>{a.acknowledged ? `Acknowledged · ${a.ackMethod || 'recorded'}` : a.owner ? `Awaiting acknowledgement from ${a.owner}` : 'No owner to acknowledge yet'}</span>
        {!a.acknowledged && a.owner && isTeam(a.owner) && <button className="text-button" disabled={!canAck} title={canAck ? '' : `Only ${a.owner} can acknowledge`} onClick={() => props.updateAction(a.id, { acknowledged: true, ackMethod: 'KB · Acknowledge button', history: log(`${a.owner} acknowledged in the KB.`) })}>{canAck ? 'Acknowledge' : `Only ${a.owner} can acknowledge`}</button>}
      </div>
      <p className="hint">Counts when the owner replies accepting, clicks Acknowledge, or uses a configured emoji. Being assigned doesn't count.</p>
    </div>

    {a.deadlineRequest && <DeadlineRequestNote action={a} viewer={viewer} updateAction={props.updateAction} notify={props.notify} />}

    <div className="drawer-section"><p className="small-label">PROGRESS</p>
      <div className="drawer-inline">
        {isOutstanding(a) && a.status !== 'Blocked' && <button className="button button-small button-outline" onClick={() => props.updateAction(a.id, { status: 'Blocked', history: log('Marked Blocked.') })}>Mark blocked</button>}
        {a.status === 'Blocked' && <button className="button button-small button-outline" onClick={() => props.updateAction(a.id, { status: 'In progress', history: log('Unblocked.') })}>Unblock</button>}
        {isOutstanding(a) && <button className="button button-small button-primary" onClick={() => { props.close(); props.requestDone(a); }}><Check size={13} />Mark done…</button>}
        {awaitingVerification(a) && <button className="button button-small button-primary" onClick={() => { props.close(); props.requestVerify(a); }}><CheckCheck size={13} />Verify…</button>}
        {!isOutstanding(a) && <button className="button button-small button-outline" onClick={() => { props.updateAction(a.id, { status: 'Open', verification: undefined, history: log(`Reopened${viewer ? ` by ${me(viewer)}` : ''}; any earlier verification is superseded.`) }); props.notify('Reopened. It is back in the pending list.'); }}><RotateCcw size={13} />Reopen</button>}
      </div>
      {a.completionBasis && <p className="hint"><strong>Completion basis:</strong> {a.completionBasis}</p>}
      {a.verification && <p className="hint"><strong>Verified by {a.verification.by} · {dateLabel(a.verification.date)}:</strong> {a.verification.check}</p>}
    </div>

    {isOutstanding(a) && props.onRequestNotify && <div className="drawer-section"><p className="small-label">SLACK</p><div className="drawer-inline"><button className="button button-small button-outline" onClick={() => { props.close(); props.onRequestNotify!({ mode: 'single', title: a.title, actions: [a] }); }}><Send size={13} />Notify on Slack…</button><span className="hint">{`Posts to ${SLACK_CHANNELS[a.clientId].channel}${a.side === 'WIA' && a.owner && isTeam(a.owner) ? `, or DM ${a.owner} personally` : ''}`}</span></div></div>}

    {isOutstanding(a) && !props.deadlineRequests && <div className="drawer-section"><p className="small-label">SNOOZE</p>
      {isSnoozed(a) ? <div className="drawer-inline"><span className="hint">Snoozed to {dateLabel(a.snoozedUntil!)} · {a.snoozeReason}</span><button className="text-button" onClick={() => props.updateAction(a.id, { snoozedUntil: undefined, snoozeReason: undefined, history: log('Snooze removed.') })}>Unsnooze</button></div>
        : <div className="drawer-inline snooze-row"><ThemedSelect aria-label="Snooze length" value={snoozeDays} onChange={setSnoozeDays}><option value="3">3 days</option><option value="7">7 days</option><option value="14">14 days</option></ThemedSelect><ThemedSelect aria-label="Snooze reason" value={snoozeReason} onChange={setSnoozeReason}><option>Waiting on a third party</option><option>Client asked to pause</option><option>Scheduled for a later call</option></ThemedSelect><button className="button button-small button-outline" onClick={() => { const until = addDays(DEMO_DATE, Number(snoozeDays)); props.updateAction(a.id, { snoozedUntil: until, snoozeReason, history: log(`Snoozed to ${dateLabel(until)}: ${snoozeReason}.`) }); props.notify('Snoozed. It drops out of the counts until then.'); }}><BellOff size={13} />Snooze</button></div>}
    </div>}

    {props.ask && <div className="drawer-section"><button className="text-button" onClick={() => { props.close(); props.ask!({ kind: 'action', clientId: a.clientId, id: a.id, label: a.title }); }}>Ask Client 360 about this action<ArrowUpRight size={11} /></button></div>}
    {call && <div className="drawer-section"><p className="small-label">NEXT CALL</p><button className="text-button" onClick={() => { props.close(); props.openCall(call.id); }}>{call.type} · {dateLabel(call.date)} at {call.time}<ArrowUpRight size={11} /></button></div>}

    <div className="drawer-section"><p className="small-label">INTERNAL NOTES</p>
      {(a.notes || []).map((n, i) => <p className="note-line" key={i}><strong>{n.by}</strong> · {dateLabel(n.date)}: {n.text}</p>)}
      <form className="note-form" onSubmit={e => { e.preventDefault(); if (!note.trim()) return; props.updateAction(a.id, { notes: [...(a.notes || []), { by: me(viewer) || 'You', date: DEMO_DATE, text: note.trim() }] }); setNote(''); }}><input value={note} onChange={e => setNote(e.target.value)} placeholder="Add a note for the team" aria-label="Add a note" /><button className="button button-small button-outline" type="submit">Add</button></form>
    </div>

    {!!a.history?.length && <div className="drawer-section"><p className="small-label">HISTORY</p><ol className="history-list">{[...a.history].reverse().map((h, i) => <li key={i}><span>{dateLabel(h.date)}</span>{h.text}</li>)}</ol></div>}
  </Dialog>;
}


// ---- Slack notifications --------------------------------------------------
// Routing rules: client-related tasks post to that client's Slack channel; individuals get a DM;
// admins get a summary. Nothing is sent until a person reviews the messages and presses Send.

export type NotifyMode = 'bulk' | 'person' | 'client' | 'single';
export type NotifyContext = { mode: NotifyMode; title: string; actions: Action[]; person?: string };
type SlackMessage = { key: string; kind: 'channel' | 'dm' | 'admin'; to: string; detail: string; warning?: string; text: string; actionIds: string[]; include: boolean };

const dueText = (a: Action) => isOverdue(a) ? `*overdue* (was due ${dateLabel(a.due)})` : !a.due ? 'no date agreed' : a.due === DEMO_DATE ? 'due today' : `due ${dateLabel(a.due)}`;
const whoText = (a: Action) => a.side === 'Client' ? `waiting on ${a.owner || 'client'}` : a.owner ? `@${a.owner}` : 'no owner yet';

function buildMessages(ctx: NotifyContext): SlackMessage[] {
  const open = ctx.actions.filter(a => isOutstanding(a) && !isSnoozed(a));
  const messages: SlackMessage[] = [];
  const isSingle = ctx.mode === 'single';

  // 1. Client channels: one message per client, containing only that client's items.
  for (const client of CLIENTS) {
    const items = open.filter(a => a.clientId === client.id);
    if (!items.length) continue;
    const slack = SLACK_CHANNELS[client.id];
    const programme = slack.audience === 'programme';
    const lines = items.map(a => `• ${a.title} · ${whoText(a)} · ${dueText(a)}${awaitingAck(a) ? ' · please acknowledge' : ''}`).join('\n');
    messages.push({ key: `ch-${client.id}`, kind: 'channel', to: slack.channel, detail: `${client.name} · ${items.length} ${items.length === 1 ? 'item' : 'items'}`,
      warning: programme ? 'Shared programme channel: other accelerator members will see this. Prefer a DM.' : undefined,
      text: `*Open actions · ${client.name}*\n${lines}\n\nReply ✅ if an item is yours and you're on it. Full detail is in the Client Knowledge Base.`,
      actionIds: items.map(a => a.id), include: !programme && (ctx.mode === 'bulk' || ctx.mode === 'client' || isSingle) });
  }

  // 2. Personal DMs: one per WIA team owner. Client contacts are only reached through their channel.
  const owners = [...new Set(open.filter(a => a.side === 'WIA' && a.owner && isTeam(a.owner)).map(a => a.owner))];
  for (const owner of owners) {
    const items = open.filter(a => a.side === 'WIA' && a.owner === owner);
    const unacked = items.filter(awaitingAck).length;
    const lines = items.map(a => `• ${a.title} · ${clientById(a.clientId).name} · ${dueText(a)}${awaitingAck(a) ? ' · not yet acknowledged' : ''}`).join('\n');
    messages.push({ key: `dm-${owner}`, kind: 'dm', to: `@${owner}`, detail: `Direct message · ${items.length} ${items.length === 1 ? 'item' : 'items'}`,
      text: `Hi ${owner}, ${isSingle ? 'a quick nudge on this one' : "here's what's on your list"}:\n${lines}${unacked ? `\n\n${unacked} still ${unacked === 1 ? 'needs' : 'need'} your acknowledgement. Reply ✅ or click Acknowledge in the KB.` : ''}`,
      actionIds: items.map(a => a.id), include: ctx.mode === 'person' || (ctx.mode !== 'bulk' && items.some(a => SLACK_CHANNELS[a.clientId].audience === 'programme')) });
  }

  // 3. Admin summary: counts plus the items that need someone to step in.
  if (!isSingle) {
    const overdue = open.filter(isOverdue), unowned = open.filter(a => !a.owner), unacked = open.filter(awaitingAck);
    const list = (rows: Action[]) => rows.map(a => `• ${a.title} · ${clientById(a.clientId).name} · ${whoText(a)} · ${dueText(a)}`).join('\n');
    const sections = [overdue.length && `*Overdue*\n${list(overdue)}`, unowned.length && `*Needs an owner*\n${list(unowned)}`, unacked.length && `*Not acknowledged*\n${list(unacked)}`].filter(Boolean).join('\n\n');
    messages.push({ key: 'admins', kind: 'admin', to: SLACK_ADMINS.map(a => `@${a}`).join(', '), detail: 'Admin summary · group DM',
      text: `*Action summary · ${ctx.title}*\n${open.length} open · ${overdue.length} overdue · ${unacked.length} not acknowledged · ${unowned.length} without an owner${sections ? `\n\n${sections}` : '\n\nNothing needs stepping in on.'}`,
      actionIds: open.map(a => a.id), include: ctx.mode !== 'client' });
  }
  return messages;
}

export function SlackNotifyDialog(props: { ctx: NotifyContext; viewer: string; close: () => void; send: (messages: SlackMessage[]) => void }) {
  const [messages, setMessages] = useState(() => buildMessages(props.ctx));
  const patch = (key: string, change: Partial<SlackMessage>) => setMessages(ms => ms.map(m => m.key === key ? { ...m, ...change } : m));
  const chosen = messages.filter(m => m.include);
  const groups: [SlackMessage['kind'], string, string][] = [['channel', 'CLIENT CHANNELS', 'Client-related tasks go to that client’s channel.'], ['dm', 'PERSONAL DMs', 'Each owner gets only their own items.'], ['admin', 'ADMINS', `Summary for ${SLACK_ADMINS.join(' and ')}.`]];
  return <Dialog title="Notify on Slack" subtitle={props.ctx.title} className="slack-dialog" onClose={props.close}>
    {!messages.length ? <Empty title="Nothing to send">There are no open, unsnoozed actions in this selection.</Empty> : <>
      <p className="hint">Review each message before sending. Untick anything that shouldn't go, or edit the wording.</p>
      {groups.map(([kind, label, help]) => { const list = messages.filter(m => m.kind === kind); if (!list.length) return null; return <div className="slack-group" key={kind}>
        <div className="slack-group-head"><p className="small-label">{label}</p><span className="hint">{help}</span></div>
        {list.map(m => <div className={`slack-message ${m.include ? '' : 'excluded'}`} key={m.key}>
          <label className="slack-target"><input type="checkbox" checked={m.include} onChange={e => patch(m.key, { include: e.target.checked })} /><span className="slack-to">{kind === 'channel' ? <Hash size={13} /> : kind === 'dm' ? <AtSign size={13} /> : <ShieldCheck size={13} />}{m.to.replace(/[#@]/g, '')}</span><span className="hint">{m.detail}</span></label>
          {m.warning && <p className="slack-warning"><AlertTriangle size={12} />{m.warning}</p>}
          {m.include && <textarea aria-label={`Message to ${m.to}`} value={m.text} rows={Math.min(10, m.text.split('\n').length + 1)} onChange={e => patch(m.key, { text: e.target.value })} />}
        </div>)}
      </div>; })}
      <div className="slack-footer"><span className="hint">Sent as the WIA KB Slack app on behalf of <strong>{props.viewer}</strong>. Preview only: nothing is posted.</span><button className="button button-primary" disabled={!chosen.length} onClick={() => props.send(chosen)}><Send size={14} />Send {chosen.length} {chosen.length === 1 ? 'message' : 'messages'}</button></div>
    </>}
  </Dialog>;
}

export function ActionRegisterTitle() {
  return <WorkspaceTitle title="Action Hub" description="Track what WIA owes each client, what's needed from the client, and who's responsible for the next step." />;
}

type GroupBy = 'person' | 'client' | 'due';
type Group = { key: string; label: string; sub: string; avatar?: ReturnType<typeof clientById>; actions: Action[] };

function buildGroups(rows: Action[], by: GroupBy): Group[] {
  if (by === 'client') return CLIENTS.map(client => ({ key: client.id, label: client.name, sub: client.service, avatar: client, actions: rows.filter(a => a.clientId === client.id) })).filter(g => g.actions.length);
  if (by === 'person') {
    const owners = [...new Set(rows.map(a => a.side === 'Client' ? `client:${a.owner}` : a.owner))];
    return owners.map(key => {
      const isClient = key.startsWith('client:'); const name = isClient ? key.slice(7) : key;
      const actions = rows.filter(a => (a.side === 'Client' ? `client:${a.owner}` : a.owner) === key);
      return { key, label: isClient ? `${name || 'Client'} (client)` : ownerLabel(name), sub: isClient ? clientById(actions[0].clientId).name : name ? 'WIA team' : 'Needs an owner', actions };
    }).sort((a, b) => Number(a.key.startsWith('client:')) - Number(b.key.startsWith('client:')) || Number(!a.key) - Number(!b.key) || a.label.localeCompare(b.label));
  }
  const buckets: [string, string, (a: Action) => boolean][] = [
    ['overdue', 'Overdue', isOverdue], ['today', 'Due today', a => isOutstanding(a) && a.due === DEMO_DATE], ['week', 'This week', a => isOutstanding(a) && !!a.due && a.due > DEMO_DATE && a.due <= addDays(DEMO_DATE, 6)],
    ['later', 'Later', a => isOutstanding(a) && !!a.due && a.due > addDays(DEMO_DATE, 6)], ['nodate', 'No date agreed', a => isOutstanding(a) && !a.due], ['closed', 'Completed', a => !isOutstanding(a)],
  ];
  return buckets.map(([key, label, test]) => ({ key, label, sub: '', actions: rows.filter(test) })).filter(g => g.actions.length);
}

function groupNotifyContext(group: Group, by: GroupBy): NotifyContext {
  if (by === 'client' || group.key.startsWith('client:')) return { mode: 'client', title: by === 'client' ? group.label : clientById(group.actions[0].clientId).name, actions: group.actions };
  if (by === 'person' && group.key) return { mode: 'person', title: `${group.label}'s actions`, actions: group.actions, person: group.label };
  return { mode: 'bulk', title: by === 'person' ? 'Unassigned actions' : group.label, actions: group.actions };
}
function groupNotifyLabel(group: Group, by: GroupBy) {
  if (by === 'client' || group.key.startsWith('client:')) return `Post to ${SLACK_CHANNELS[group.actions[0].clientId].channel}`;
  if (by === 'person' && group.key) return `Notify ${group.label} on Slack`;
  if (by === 'person') return 'Notify admins on Slack';
  return 'Notify on Slack';
}
function groupNotifyHint(group: Group, by: GroupBy) {
  if (by === 'client' || group.key.startsWith('client:')) return 'Client channel. Option to DM owners and admins too.';
  if (by === 'person' && group.key) return `DM to ${group.label}, summary to admins.`;
  if (by === 'person') return 'Nobody owns these yet. Admins decide who takes them.';
  return 'Client channels, DMs and admin summary.';
}

function GroupedActions(props: RowProps & { rows: Action[]; groupBy: GroupBy; onAddAction: () => void }) {
  const groups = buildGroups(props.rows, props.groupBy);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const toggle = (key: string) => setCollapsed(s => { const n = new Set(s); if (n.has(key)) n.delete(key); else n.add(key); return n; });
  return <section className="client-action-section" aria-label="Actions">
    <div className="client-action-intro"><div><h2>{props.groupBy === 'person' ? 'Team' : props.groupBy === 'client' ? 'Owed by clients' : 'By due date'}</h2><p>{props.rows.length} {props.rows.length === 1 ? 'action' : 'actions'} in this view.</p></div><button className="button button-gold add-client-action" onClick={props.onAddAction}><Plus size={16} />Add an action</button></div>
    <div className="panel client-action-panel">
      {groups.length ? <ul className="client-action-list">{groups.map(group => {
        const expanded = !collapsed.has(group.key);
        const pending = group.actions.filter(isOutstanding);
        const overdue = group.actions.filter(isOverdue).length;
        const unacked = group.actions.filter(awaitingAck).length;
        const nextDue = pending.filter(a => a.due).sort((a, b) => a.due.localeCompare(b.due))[0]?.due;
        const id = `group-${group.key.replace(/[^a-z0-9]/gi, '-')}`;
        return <li className={`client-action-group ${expanded ? 'is-expanded' : ''}`} key={group.key}>
          <button className="client-action-toggle" id={`${id}-toggle`} aria-expanded={expanded} aria-controls={id} onClick={() => toggle(group.key)}>
            <span className="client-action-identity">{group.avatar ? <Avatar client={group.avatar} small /> : <span className={`client-avatar small person-avatar ${!group.key ? 'unassigned' : ''}`} aria-hidden="true">{group.key ? group.label.replace(/[^A-Za-z ]/g, '').split(' ').map(w => w[0]).join('').slice(0, 2) : '?'}</span>}<span><strong>{group.label}</strong>{group.sub && <small>{group.sub}</small>}</span></span>
            <span className="client-action-total"><strong>{group.actions.length.toString().padStart(2, '0')}</strong></span>
            <span className="client-action-signals"><span className={overdue ? 'text-amber' : ''}>{overdue} overdue</span><span className={unacked ? 'text-amber' : ''}>{unacked} not acknowledged</span></span>
            <span className="client-action-next"><small>Next due</small><span>{nextDue ? dateLabel(nextDue) : pending.length ? 'No date' : '—'}</span></span>
            <ChevronRight className="client-action-chevron" size={18} aria-hidden="true" />
          </button>
          <div id={id} role="region" aria-labelledby={`${id}-toggle`} hidden={!expanded}>
            {expanded && <div className="client-action-details">{props.onRequestNotify && group.actions.some(isOutstanding) && <div className="group-notify"><button className="button button-small button-outline" onClick={() => props.onRequestNotify!(groupNotifyContext(group, props.groupBy))}><Send size={13} />{groupNotifyLabel(group, props.groupBy)}</button><span className="hint">{groupNotifyHint(group, props.groupBy)}</span></div>}<div className="action-table-heading"><span aria-hidden="true" /><span>ACTION ITEM</span><span>DUE & STATUS</span><span>EVIDENCE</span><span className="sr-only">Details</span></div><ActionRows {...props} rows={group.actions} /></div>}
          </div>
        </li>;
      })}</ul> : <Empty title="Nothing in this view">Try another tile, person or status filter.</Empty>}
    </div>
  </section>;
}

export function ReviewQueue(props: { items: ReviewItem[]; actions: Action[]; resolve: (item: ReviewItem, outcome: string, action?: Action) => void; resolved: { title: string; outcome: string }[]; viewer?: string }) {
  return <section className="review-queue" aria-label="Needs review">
    <div className="client-action-intro"><div><h2>Needs review</h2><p>Items that failed the live-list test. Each shows why it's here. Dismissed items won't come back on the next sync.</p></div></div>
    {props.items.length ? <div className="review-grid">{props.items.map(item => <ReviewCard key={item.id} item={item} actions={props.actions} resolve={props.resolve} viewer={props.viewer} />)}</div> : <div className="panel"><Empty title="Review queue is clear">Everything has been triaged.</Empty></div>}
    {!!props.resolved.length && <div className="panel resolved-log"><p className="small-label">RESOLVED IN THIS SESSION</p><ul>{props.resolved.map((r, i) => <li key={i}><CircleCheck size={13} />{r.title} <span className="muted">→ {r.outcome}</span></li>)}</ul></div>}
  </section>;
}

/** A KB proposal (id "ai-" + the candidate's id): the admin's decision is saved by the KB, not just this browser. */
const isKbProposal = (item: ReviewItem) => /^ai-[0-9a-f]{32}$/.test(item.id);

function ReviewCard({ item, actions, resolve, viewer }: { item: ReviewItem; actions: Action[]; resolve: (item: ReviewItem, outcome: string, action?: Action) => void; viewer?: string }) {
  const [owner, setOwner] = useState(item.suggestedOwner || '');
  const [title, setTitle] = useState(item.title);
  const [due, setDue] = useState(item.suggestedDue || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const proposal = item.reason === 'AI proposal';
  const owners = [...new Set([...TEAM, ...(item.suggestedOwner ? [item.suggestedOwner] : [])])];
  // Saves an approve/reject on a KB proposal first; sample items resolve in this browser only.
  const decide = async (decision: 'approve' | 'reject', outcome: string, action?: Action, reason = '') => {
    const decided = { ...item, title: title.trim() || item.title };  // the log shows the title as approved
    if (!isKbProposal(item)) { resolve(decided, outcome, action); return; }
    setSaving(true); setError('');
    try {
      const res = await fetch(`/api/v1/actions/proposals/${item.id}/decision`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, admin: viewer || 'Admin', reason, edits: decision === 'approve' ? { title: title.trim(), due, ...(item.side === 'WIA' ? { owner } : {}) } : {} }) });
      if (!res.ok) {
        const message: string = (await res.json().catch(() => null))?.detail?.message || `the KB answered ${res.status}`;
        // Decided earlier (another admin, or before the portfolio rebuilt): nothing left to do here.
        if (message.startsWith('this proposal was already')) { resolve(decided, `Already decided: ${message.replace('this proposal was ', '')}`); return; }
        throw new Error(message);
      }
      resolve(decided, outcome, action);
    } catch (e) { setError(`Not saved: ${(e as Error).message}.`); } finally { setSaving(false); }
  };
  const [clientId, setClientId] = useState(item.clientId || item.candidateClients?.[0] || CLIENTS[0].id);
  const [dismissing, setDismissing] = useState(false);
  const [reason, setReason] = useState('Not a real ask');
  const dup = item.duplicateOf ? actions.find(a => a.id === item.duplicateOf) : undefined;
  const toAction = (overrides: Partial<Action> = {}): Action => ({ id: isKbProposal(item) ? item.id : `rv-${item.id}-${Date.now()}`, clientId, title: title.trim() || item.title, owner: item.side === 'Client' ? '' : owner, due, status: 'Open', side: item.side, acknowledged: false, sourceId: '', note: `Accepted from Needs review (${item.reason.toLowerCase()}).`, origin: item.origin, quote: item.quote, assignedOn: owner ? DEMO_DATE : undefined, lastActivity: DEMO_DATE, history: [{ date: item.date, text: `Found in ${item.origin} (${item.author}).` }, { date: DEMO_DATE, text: `Accepted from Needs review: ${item.reason}.` }], ...overrides });
  const tone: Tone = item.reason === 'AI proposal' ? 'gold' : item.reason === 'Possibly stale' ? 'neutral' : item.reason === 'Possible duplicate' ? 'blue' : 'amber';
  return <article className="panel review-card">
    <div className="review-card-head"><Badge tone={tone}>{item.reason}</Badge><span className="hint">{item.clientId ? clientById(item.clientId).name : 'Client unknown'}</span></div>
    {proposal ? <label className="review-field">Action<input className="review-title" value={title} maxLength={300} onChange={e => setTitle(e.target.value)} aria-label="Action title" /></label> : <h3>{item.title}</h3>}<p className="review-why">{item.explanation}</p>
    <blockquote className="origin-quote">“{item.quote}”<footer><OriginChip origin={item.origin} /> {item.author} · {dateLabel(item.date)}</footer></blockquote>
    {dup && <p className="hint">Existing action: <strong>{dup.title}</strong> ({ownerLabel(dup.owner)}, {dateLabel(dup.due)})</p>}
    {item.reason === 'Client match unclear' && <label className="review-field">Which client?<ThemedSelect aria-label="Which client" value={clientId} onChange={setClientId}>{(item.candidateClients || CLIENTS.map(c => c.id)).map(id => <option key={id} value={id}>{clientById(id).name}</option>)}</ThemedSelect></label>}
    {(item.reason === 'Owner unclear' || item.reason === 'AI proposal' || item.reason === 'Client match unclear') && <label className="review-field">Owner<ThemedSelect aria-label="Owner" value={owner} onChange={setOwner}><option value="">Leave unassigned</option>{owners.map(p => <option key={p} value={p}>{p}</option>)}</ThemedSelect></label>}
    {proposal && <label className="review-field">Due<ThemedDatePicker label="Due date" value={due} clearable onChange={setDue} /></label>}
    {error && <p className="review-error" role="alert"><AlertTriangle size={12} />{error}</p>}
    {dismissing ? <div className="review-actions"><ThemedSelect aria-label="Dismiss reason" value={reason} onChange={setReason}><option>Not a real ask</option><option>Already handled</option><option>Out of scope</option><option>Duplicate</option></ThemedSelect><button className="button button-small button-primary" disabled={saving} onClick={() => void decide('reject', `Dismissed: ${reason}`, undefined, reason)}>Confirm dismiss</button><button className="text-button" onClick={() => setDismissing(false)}>Cancel</button></div>
      : <div className="review-actions">
        {item.reason === 'Possibly stale' && <><button className="button button-small button-primary" onClick={() => resolve(item, 'Still open → added to register', toAction())}>Still open</button><button className="button button-small button-outline" onClick={() => resolve(item, 'Already done (closed, kept in history)')}>Already done</button></>}
        {(item.reason === 'Owner unclear' || item.reason === 'Client match unclear') && <button className="button button-small button-primary" onClick={() => resolve(item, `Accepted · owner ${ownerLabel(owner)}`, toAction())}>Accept as action</button>}
        {proposal && <button className="button button-small button-primary" disabled={saving || !title.trim()} onClick={() => void decide('approve', `Approved · owner ${ownerLabel(owner)}`, toAction({ note: `Proposed by the KB; approved by ${viewer || 'an admin'}.`, assignedOn: owner ? DEMO_DATE : undefined }))}><Check size={13} />{saving ? 'Saving…' : 'Approve'}</button>}
        {item.reason === 'Possible duplicate' && <><button className="button button-small button-primary" onClick={() => resolve(item, `Merged into "${dup?.title}" as supporting evidence`)}>Merge into existing</button><button className="button button-small button-outline" onClick={() => resolve(item, 'Kept as a separate action', toAction({ owner: dup?.owner || '' }))}>Keep separate</button></>}
        {item.reason === 'Checklist incomplete' && <><button className="button button-small button-primary" onClick={() => resolve(item, 'Confirmed done (checklist out of date)')}>Confirm done</button><button className="button button-small button-outline" onClick={() => resolve(item, 'Reopened as an action', toAction({ owner: 'Danielle', assignedOn: DEMO_DATE, verifyRequired: true, actionType: 'LeadLock / GHL setup', title: `Finish: ${item.title} (SPF/DKIM, test form)` }))}>Reopen</button></>}
        <button className="text-button" onClick={() => setDismissing(true)}>Dismiss…</button>
      </div>}
  </article>;
}

export function ProgrammeOps({ tasks, toggle }: { tasks: ProgrammeTask[]; toggle: (id: string) => void }) {
  const programmes = [...new Set(tasks.map(t => t.programme))];
  return <section aria-label="Programme operations">
    <div className="client-action-intro"><div><h2>Programme ops</h2><p>Accelerator upkeep: office hours, community posts, attendance. Tracked here and <strong>not counted</strong> as any client's open actions.</p></div></div>
    {programmes.map(p => <div className="panel programme-panel" key={p}><p className="small-label">{p.toUpperCase()}</p>
      {tasks.filter(t => t.programme === p).map(t => <div className={`action-row ${t.status === 'Done' ? 'completed' : ''}`} key={t.id}>
        <button className={`action-checkbox ${t.status === 'Done' ? 'checked' : ''}`} aria-label={`Toggle ${t.title}`} onClick={() => toggle(t.id)}>{t.status === 'Done' && <Check size={13} />}</button>
        <div className="action-main"><span className="action-title">{t.title}</span><div className="action-subline"><span>{t.owner}</span>{t.recurring && <><span>·</span><span className="row-flag"><RefreshCw size={10} />{t.recurring}, never shown as overdue</span></>}</div></div>
        <div className="action-due"><span>{dateLabel(t.due)}</span><Badge tone={t.status === 'Done' ? 'blue' : 'neutral'} dot={false}>{t.status}</Badge></div>
      </div>)}
    </div>)}
  </section>;
}

export default function Actions(props: WorkspaceProps & { addAction: (action: Action) => void }) {
  const viewer = props.viewer;
  const [scope, setScope] = useState<string>(() => VIEWERS.find(v => v.name === props.viewer)?.defaultScope || 'mine');
  const isOpsRole = (name: string) => VIEWERS.find(v => v.name === name)?.defaultScope === 'all';
  const [groupBy, setGroupBy] = useState<GroupBy>(() => isOpsRole(props.viewer) ? 'person' : 'due');
  const [tab, setTab] = useState('register');
  const [tile, setTile] = useState<TileId | null>(null);
  const [filter, setFilter] = useState('open');
  const [query, setQuery] = useState('');
  const [owner, setOwner] = useState('all');
  const [adding, setAdding] = useState(false);
  const [doneFor, setDoneFor] = useState<Action | null>(null);
  const [verifyFor, setVerifyFor] = useState<Action | null>(null);
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>(REVIEW_ITEMS);
  const [resolved, setResolved] = useState<{ title: string; outcome: string }[]>([]);
  const [programme, setProgramme] = useState<ProgrammeTask[]>(PROGRAMME_TASKS);
  const [notify, setNotify] = useState<NotifyContext | null>(null);
  const sendSlack = (messages: { to: string; actionIds: string[] }[]) => {
    const sentTo = new Map<string, string[]>();
    messages.forEach(m => m.actionIds.forEach(id => sentTo.set(id, [...(sentTo.get(id) || []), m.to])));
    sentTo.forEach((targets, id) => { const a = props.actions.find(x => x.id === id); if (a) props.updateAction(id, { history: log(a, `Slack: notified ${targets.join(', ')} (sent by ${me(viewer)}).`) }); });
    setNotify(null); props.notify(`${messages.length} Slack ${messages.length === 1 ? 'message' : 'messages'} sent. Preview only: nothing was posted.`);
  };

  const scoped = useMemo(() => scope === 'mine' ? props.actions.filter(a => a.owner === viewer) : props.actions, [props.actions, scope, viewer]);
  const live = scoped.filter(a => !isSnoozed(a));
  const tileCount = (t: (typeof TILES)[number]) => t.id === 'review' ? reviewItems.length : live.filter(t.test!).length;
  const activeTile = TILES.find(t => t.id === tile);
  // Team shows what WIA owes; Client shows only what clients owe WIA (for "Mine", the clients you work with).
  const myClients = new Set(props.actions.filter(a => a.owner === viewer).map(a => a.clientId));
  const base = groupBy === 'client' ? props.actions.filter(a => a.side === 'Client' && (scope === 'all' || myClients.has(a.clientId))) : groupBy === 'person' ? scoped.filter(a => a.side === 'WIA') : scoped;
  const rows = (activeTile?.test ? base.filter(a => !isSnoozed(a)).filter(activeTile.test) : base.filter(a => filter === 'all' || (filter === 'open' && isOutstanding(a) && !isSnoozed(a)) || (filter === 'snoozed' && isSnoozed(a)) || (filter === 'done' && !isOutstanding(a))))
    .filter(a => owner === 'all' || groupBy === 'client' || (owner === '__none' ? !a.owner : a.owner === owner))
    .filter(a => `${a.title} ${clientById(a.clientId).name} ${a.owner}`.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => (a.due || '9999').localeCompare(b.due || '9999') || a.id.localeCompare(b.id));

  // The account switcher lives in the sidebar; each change resets the register to that person's default view.
  const firstViewer = useRef(true);
  useEffect(() => { if (firstViewer.current) { firstViewer.current = false; return; } setScope(VIEWERS.find(x => x.name === viewer)!.defaultScope); setOwner('all'); setTile(null); setGroupBy(isOpsRole(viewer) ? 'person' : 'due'); }, [viewer]); // eslint-disable-line react-hooks/exhaustive-deps
  const pickTile = (id: TileId) => { if (id === 'review') { setTab('review'); return; } setTab('register'); setTile(tile === id ? null : id); };
  const log = (a: Action, text: string) => [...(a.history || []), { date: DEMO_DATE, text }];
  const resolve = (item: ReviewItem, outcome: string, action?: Action) => { if (action) props.addAction(action); setReviewItems(items => items.filter(i => i.id !== item.id)); setResolved(r => [{ title: item.title, outcome }, ...r]); props.notify(action ? 'Added to the live register.' : 'Resolved. It won’t be recreated by the next sync.'); };

  return <div className="view action-register-view">
    <div className="register-topbar">
      <p className="sync-line"><RefreshCw size={12} />Last synced {SYNC_STATUS.map(s => `${s.source} ${s.at}`).join(' · ')}</p>
    </div>

    <div className="register-tabs" role="tablist" aria-label="Register sections">
      {[{ id: 'register', label: 'Register', count: live.filter(isOutstanding).length }, { id: 'review', label: 'Needs review', count: reviewItems.length }, { id: 'programme', label: 'Programme ops', count: programme.filter(p => p.status === 'Open').length }].map(t => <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? 'selected' : ''} onClick={() => setTab(t.id)}>{t.label}<span>{t.count}</span></button>)}
    </div>

    {tab !== 'programme' && <section className="register-tiles" aria-label="Action summary">{TILES.map(t => { const Icon = t.icon; const n = tileCount(t); return <button key={t.id} className={`register-tile ${tile === t.id || (t.id === 'review' && tab === 'review') ? 'selected' : ''} ${n && (t.id === 'overdue' || t.id === 'ack') ? 'warn' : ''}`} onClick={() => pickTile(t.id)} aria-pressed={tile === t.id}>
      <span className="register-tile-label"><span>{t.label}</span><Icon size={15} /></span><strong>{n.toString().padStart(2, '0')}</strong><small>{t.detail}</small></button>; })}</section>}

    {tab === 'register' && <>
      <div className="action-register-controls">
        <div className="control-cluster">
          <Segmented label="Scope" value={scope} onChange={v => { setScope(v); setOwner('all'); }} options={[{ id: 'mine', label: 'My actions', count: props.actions.filter(a => a.owner === viewer && isOutstanding(a)).length }, { id: 'all', label: 'All clients', count: props.actions.filter(isOutstanding).length }]} />
          <Segmented label="Group by" value={groupBy} onChange={v => setGroupBy(v as GroupBy)} options={[...(isOpsRole(viewer) ? [{ id: 'person', label: 'Team' }] : []), { id: 'client', label: 'Client' }, { id: 'due', label: 'Due date' }]} />
        </div>
        <div className="action-register-filters">
          {tile ? <button className="filter-pill" onClick={() => setTile(null)}>Showing: {activeTile?.label} ✕</button> : <ThemedSelect aria-label="Status filter" value={filter} onChange={setFilter}><option value="open">Open</option><option value="snoozed">Snoozed</option><option value="done">Completed</option><option value="all">All statuses</option></ThemedSelect>}
          <SearchField label="Search clients or actions" placeholder="Search clients or actions" value={query} onChange={setQuery} />
          {scope === 'all' && <ThemedSelect aria-label="Filter by owner" value={owner} onChange={setOwner}><option value="all">All owners</option><option value="__none">Unassigned</option>{[...new Set(props.actions.map(a => a.owner).filter(Boolean))].map(o => <option key={o} value={o}>{o}</option>)}</ThemedSelect>}
          <button className="button button-small button-outline slack-button" onClick={() => setNotify({ mode: 'bulk', title: activeTile ? activeTile.label : scope === 'mine' ? `${viewer}'s actions` : 'All clients', actions: rows })}><Send size={13} />Notify on Slack</button>
        </div>
      </div>
      <div className="register-body">
        <GroupedActions {...props} viewer={viewer} rows={rows} groupBy={groupBy} onAddAction={() => setAdding(true)} onRequestDone={setDoneFor} onRequestVerify={setVerifyFor} onRequestNotify={setNotify} />
      </div>
      <div className="quiet-footer"><CheckCheck size={15} />“Done” records completion. Only flagged types ({VERIFY_TYPES.join(', ')}) need a separate “Verified” check.</div>
    </>}

    {tab === 'review' && <ReviewQueue items={reviewItems} actions={props.actions} resolve={resolve} resolved={resolved} />}
    {tab === 'programme' && <ProgrammeOps tasks={programme} toggle={id => setProgramme(ps => ps.map(p => p.id === id ? { ...p, status: p.status === 'Done' ? 'Open' : 'Done' } : p))} />}

    {notify && <SlackNotifyDialog ctx={notify} viewer={viewer} close={() => setNotify(null)} send={sendSlack} />}
    {doneFor && <DoneDialog action={doneFor} viewer={viewer} updateAction={props.updateAction} notify={props.notify} close={() => setDoneFor(null)} />}
    {verifyFor && <VerifyDialog action={verifyFor} viewer={viewer} updateAction={props.updateAction} notify={props.notify} close={() => setVerifyFor(null)} />}
    {adding && <AddActionDialog viewer={viewer} addAction={props.addAction} notify={props.notify} close={() => setAdding(false)} />}
  </div>;
}

// ---- Shared dialogs (used by both register layouts) -----------------------
type DialogBase = { viewer: string; notify: (message: string) => void; close: () => void };
type UpdateAction = WorkspaceProps['updateAction'];
const logOn = (a: Action, text: string) => [...(a.history || []), { date: DEMO_DATE, at: new Date().toISOString(), text }];

export function DoneDialog({ action, viewer, updateAction, notify, close }: DialogBase & { action: Action; updateAction: UpdateAction }) {
  return <Dialog title="What shows it's done?" subtitle={action.title} onClose={close}><form className="form-stack" onSubmit={e => {
    e.preventDefault(); const basis = String(new FormData(e.currentTarget).get('basis')).trim(); if (!basis) return;
    updateAction(action.id, { status: 'Done', completionBasis: basis, history: logOn(action, `Marked Done by ${me(viewer)}: ${basis}`) }); close();
    notify(action.verifyRequired ? 'Done. This type needs a follow-up check before it counts as Verified.' : 'Done. This type closes at Done.');
  }}><label>Completion basis<input name="basis" required maxLength={200} placeholder="Link or short note, e.g. 'Sent to Sarah, email Oct 9'" /></label><p className="hint">{action.verifyRequired ? `“${action.actionType}” is a flagged type: it will wait in Awaiting verification.` : 'Not a flagged type: this closes the action.'}</p><button className="button button-primary" type="submit"><Check size={15} />Mark done</button></form></Dialog>;
}

/** Owners can't verify their own work unless they are an admin/ops viewer (preview rule). */
export const canVerify = (viewer: string, action: Action) => viewer !== action.owner || VIEWERS.find(v => v.name === viewer)?.defaultScope === 'all';

export function VerifyDialog({ action, viewer, updateAction, notify, close }: DialogBase & { action: Action; updateAction: UpdateAction }) {
  return <Dialog title="Did it actually stick?" subtitle={action.title} onClose={close}>{!canVerify(viewer, action)
    ? <div className="form-stack"><p className="body-copy">{viewer} owns this action. Self-verification is an admin-configured permission and is off for {viewer} in this preview. Switch the account in the sidebar profile to Gisselle or Whitney to verify.</p><button className="button button-outline" onClick={close}>Close</button></div>
    : <form className="form-stack" onSubmit={e => {
      e.preventDefault(); const data = new FormData(e.currentTarget); const check = String(data.get('check')).trim(); if (!check) return;
      updateAction(action.id, { status: 'Verified', verification: { by: me(viewer), check, date: DEMO_DATE }, history: logOn(action, `Verified by ${me(viewer)}: ${check}`) }); close(); notify('Verification recorded.');
    }}><p className="hint">Completed: {action.completionBasis || 'no basis recorded'}</p><label>What did you check?<input name="check" required maxLength={200} placeholder="e.g. 'Test conversion recorded in GA4 and Google Ads'" /></label><label>Evidence link (optional)<input name="evidence" placeholder="Screenshot, report or message link" /></label><p className="hint">Recorded as verified by <strong>{viewer}</strong>.</p><button className="button button-primary" type="submit"><CheckCheck size={15} />Record verification</button></form>}</Dialog>;
}

export function AddActionDialog({ viewer, addAction, notify, close }: DialogBase & { addAction: (action: Action) => void }) {
  return <Dialog title="Give the next step an owner." subtitle="Add an action" onClose={close}><form className="form-stack" onSubmit={event => {
    event.preventDefault(); const data = new FormData(event.currentTarget); const clientId = data.get('client') as string; const title = String(data.get('title')).trim(); if (!title) return;
    const type = String(data.get('type') || 'Admin'); const who = String(data.get('owner')); const side = String(data.get('side')) as Action['side']; const where = String(data.get('where')).trim();
    addAction({ id: `local-${crypto.randomUUID()}`, priority: String(data.get('priority')) as Action['priority'], clientId, title, owner: who, due: String(data.get('due') || ''), side, status: 'Open', acknowledged: false, sourceId: '', origin: 'Manual', actionType: type, verifyRequired: VERIFY_TYPES.includes(type), assignedOn: who ? DEMO_DATE : undefined, lastActivity: DEMO_DATE, quote: where || undefined, note: `Added manually by ${me(viewer)}.`, history: [{ date: DEMO_DATE, text: `Created manually by ${me(viewer)}.` }] }); close(); notify('Action added.');
  }}><label>What needs to happen?<input name="title" required maxLength={160} placeholder="Write a concrete next step" /></label>
    <div className="form-two-col"><label>Client<ThemedSelect aria-label="Client" name="client">{CLIENTS.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</ThemedSelect></label><label>Who owes it?<ThemedSelect aria-label="Side" name="side"><option value="WIA">WIA</option><option value="Client">Client</option></ThemedSelect></label></div>
    <div className="form-two-col"><label>Owner (optional)<ThemedSelect aria-label="Owner" name="owner" defaultValue=""><option value="">Unassigned</option>{TEAM.map(person => <option key={person} value={person}>{person}</option>)}</ThemedSelect></label><label>Deadline (optional)<ThemedDatePicker label="Deadline" name="due" /></label></div>
    <div className="form-two-col"><label>Priority<ThemedSelect aria-label="Priority" name="priority" defaultValue="Medium"><option>High</option><option>Medium</option><option>Low</option></ThemedSelect></label></div>
    <label>Where was this agreed? (optional)<input name="where" maxLength={200} placeholder="e.g. 'Asked on the Oct 9 call'" /></label>
    <button className="button button-primary" type="submit"><Plus size={15} />Add action</button></form></Dialog>;
}

// ---- Deadline change requests (revised register) ---------------------------
// Instead of snoozing, the owner asks for a new deadline. Admins (Whitney, Gisselle) approve or decline it.
export const isAdmin = (viewer?: string) => !!viewer && VIEWERS.find(v => v.name === viewer)?.defaultScope === 'all';

function DeadlineRequest(props: RowProps & { action: Action; compact?: boolean }) {
  const a = props.action;
  const [to, setTo] = useState('');
  const [reason, setReason] = useState('');
  return <div className="deadline-request">
    {!props.compact && <><p className="small-label">AGREED DEADLINE</p>
    <p className="deadline-current">{a.due ? dateLabel(a.due, { weekday: 'short', day: 'numeric', month: 'short' }) : 'No date agreed'}</p></>}
    {a.deadlineRequest ? <p className="hint">A change to {dateLabel(a.deadlineRequest.to)} is waiting for an admin.</p> : isOutstanding(a) && <form className="form-stack" onSubmit={e => {
      e.preventDefault(); if (!to || !reason.trim()) return;
      props.updateAction(a.id, { deadlineRequest: { to, reason: reason.trim(), by: me(props.viewer) || 'You', on: DEMO_DATE }, history: logOn(a, `${props.viewer || 'Someone'} asked to move the deadline to ${dateLabel(to)}: ${reason.trim()}`) });
      props.notify('Deadline change sent to Whitney and Gisselle for approval.'); setTo(''); setReason('');
    }}>
      <label>{props.compact ? 'Requested deadline' : 'Request a new deadline'}<ThemedDatePicker label="New deadline" value={to} onChange={setTo} /></label>
      <label>Why it needs to move<input value={reason} onChange={e => setReason(e.target.value)} maxLength={160} placeholder="e.g. 'Waiting on Sarah's photos'" /></label>
      <button className="button button-small button-outline" type="submit" disabled={!to || !reason.trim()}><CalendarClock size={13} />Send for approval</button>
    </form>}
  </div>;
}

export function decideDeadline(a: Action, approve: boolean, viewer: string, updateAction: UpdateAction) {
  const r = a.deadlineRequest!;
  updateAction(a.id, approve
    ? { due: r.to, deadlineRequest: undefined, history: logOn(a, `${me(viewer)} approved ${r.by}'s request: deadline moved ${a.due ? `from ${dateLabel(a.due)} ` : ''}to ${dateLabel(r.to)}.`) }
    : { deadlineRequest: undefined, history: logOn(a, `${me(viewer)} declined ${r.by}'s request to move the deadline to ${dateLabel(r.to)}.`) });
}

function DeadlineRequestNote({ action: a, viewer, updateAction, notify }: { action: Action; viewer?: string; updateAction: UpdateAction; notify: (m: string) => void }) {
  const r = a.deadlineRequest!;
  return <div className="drawer-section conflict-box"><p className="small-label"><CalendarClock size={11} /> DEADLINE CHANGE REQUESTED</p>
    <p>{r.by} asked on {dateLabel(r.on)} to move it {a.due ? `from ${dateLabel(a.due)} ` : ''}to <strong>{dateLabel(r.to)}</strong>: “{r.reason}”</p>
    {isAdmin(viewer) && <div className="drawer-inline" style={{ marginTop: 10 }}><button className="button button-small button-primary" onClick={() => { decideDeadline(a, true, viewer!, updateAction); notify('Approved. The deadline is updated.'); }}><Check size={13} />Approve</button><button className="button button-small button-outline" onClick={() => { decideDeadline(a, false, viewer!, updateAction); notify('Declined. The original deadline stands.'); }}>Decline</button></div>}
  </div>;
}
