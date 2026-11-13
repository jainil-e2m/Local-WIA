import { useMemo, useState } from 'react';
import { Check, CheckCheck, ChevronDown, RotateCcw, Search, ShieldCheck } from 'lucide-react';
import { DEMO_DATE, dateLabel, daysBetween, isOutstanding } from '../data';
import { Dialog, Empty, Segmented, SourceLink } from '../components/UI';
import type { Action, Client, WorkspaceProps } from '../types';
import './CommitmentHistory.css';
import { me } from '../auth';

/*
 * Commitment history for one client: every closed commitment, both ways, newest first, grouped by month.
 * Each row says who delivered it, when it closed against its agreed date, and whether it was checked.
 * Expanding a row shows the completion basis, the verification record and the source; it can be reopened.
 */

const closedOn = (a: Action) => a.completedOn || a.verification?.date || a.lastActivity || a.due;
const monthKey = (d: string) => d.slice(0, 7);

function timing(a: Action): { text: string; tone: string } | null {
  if (!a.due || !a.completedOn) return null;
  const late = daysBetween(a.due, a.completedOn);
  if (late > 0) return { text: `${late} ${late === 1 ? 'day' : 'days'} late`, tone: 'late' };
  if (late < 0) return { text: `${-late} ${late === -1 ? 'day' : 'days'} early`, tone: 'early' };
  return { text: 'On the day', tone: 'early' };
}

export function CommitmentHistory(props: WorkspaceProps & { client: Client; close: () => void }) {
  const [side, setSide] = useState('all');
  const [query, setQuery] = useState('');
  const [openId, setOpenId] = useState<string | null>(null);
  const closed = useMemo(() => props.actions.filter(a => a.clientId === props.client.id && !isOutstanding(a)).sort((a, b) => closedOn(b).localeCompare(closedOn(a))), [props.actions, props.client.id]);
  const needle = query.trim().toLowerCase();
  const rows = closed.filter(a => (side === 'all' || a.side === side) && (!needle || `${a.title} ${a.owner} ${a.actionType || ''}`.toLowerCase().includes(needle)));
  const months = [...new Set(rows.map(a => monthKey(closedOn(a))))];

  const stat = (list: Action[]) => { const timed = list.filter(a => a.due && a.completedOn); return { n: list.length, onTime: timed.filter(a => daysBetween(a.due, a.completedOn!) <= 0).length, timed: timed.length }; };
  const wia = stat(closed.filter(a => a.side === 'WIA'));
  const client = stat(closed.filter(a => a.side === 'Client'));
  const needCheck = closed.filter(a => a.verifyRequired);
  const verified = needCheck.filter(a => a.status === 'Verified').length;
  const since = closed.length ? dateLabel(closedOn(closed[closed.length - 1]), { month: 'short', year: 'numeric' }) : '';

  const reopen = (a: Action) => { props.updateAction(a.id, { status: 'Open', verification: undefined, history: [...(a.history || []), { date: DEMO_DATE, text: `Reopened by ${me(props.viewer)} from the commitment history; any earlier verification is superseded.` }] }); setOpenId(null); props.notify('Reopened. It is back in the open commitments.'); };

  return <Dialog title="Completed commitments" subtitle="Commitment history" size="lg" onClose={props.close}
    meta={<><strong>{props.client.name}</strong><span>·</span><span>{closed.length} closed{since ? ` since ${since}` : ''}</span></>}
    footer={<><p className="hint">Same records as the Action Hub. Reopening moves an item back to the open list.</p><button className="button button-primary button-small" onClick={props.close}>Done</button></>}>

    <div className="ch-summary">
      <div><span>We delivered</span><strong>{wia.n}</strong><small>{wia.timed ? `${wia.onTime} of ${wia.timed} on time` : 'No dated items'}</small></div>
      <div><span>They delivered</span><strong>{client.n}</strong><small>{client.timed ? `${client.onTime} of ${client.timed} on time` : 'No dated items'}</small></div>
      <div><span>Checked it stuck</span><strong>{verified}<em> / {needCheck.length}</em></strong><small>{needCheck.length ? `${needCheck.length - verified} still awaiting a check` : 'None needed a check'}</small></div>
    </div>

    <div className="ch-controls">
      <Segmented label="Who delivered" value={side} onChange={setSide} options={[{ id: 'all', label: 'All', count: closed.length }, { id: 'WIA', label: 'What we delivered', count: wia.n }, { id: 'Client', label: 'What they delivered', count: client.n }]} />
      <label className="ch-search"><Search size={14} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search history" aria-label="Search commitment history" /></label>
    </div>

    {!rows.length ? <Empty title={closed.length ? 'Nothing matches' : 'No completed commitments yet'}>{closed.length ? 'Try another filter or search.' : 'Closed commitments for this client will collect here.'}</Empty>
      : months.map(m => <section className="ch-month" key={m}>
        <h3>{dateLabel(`${m}-01`, { month: 'long', year: 'numeric' })}<span>{rows.filter(a => monthKey(closedOn(a)) === m).length}</span></h3>
        <ul>{rows.filter(a => monthKey(closedOn(a)) === m).map(a => { const t = timing(a); const expanded = openId === a.id; const awaiting = a.status === 'Done' && a.verifyRequired; return <li key={a.id} className={expanded ? 'is-open' : ''}>
          <button className="ch-row" aria-expanded={expanded} onClick={() => setOpenId(expanded ? null : a.id)}>
            <span className={`ch-mark ${a.status === 'Verified' ? 'verified' : ''}`} aria-hidden="true">{a.status === 'Verified' ? <CheckCheck size={12} /> : <Check size={12} />}</span>
            <span className="ch-what"><strong>{a.title}</strong><small><span className={`ch-side side-${a.side.toLowerCase()}`}>{a.side === 'WIA' ? 'We delivered' : 'They delivered'}</span>{a.owner}{a.actionType ? ` · ${a.actionType}` : ''}</small></span>
            <span className="ch-when"><span>Closed {dateLabel(closedOn(a))}</span>{t ? <small className={`tone-${t.tone}`}>{t.text}{a.due ? ` · due ${dateLabel(a.due)}` : ''}</small> : <small>{a.due ? `due ${dateLabel(a.due)}` : 'No agreed date'}</small>}</span>
            <span className={`ch-status ${a.status === 'Verified' ? 'verified' : awaiting ? 'awaiting' : ''}`}>{a.status === 'Verified' ? 'Verified' : awaiting ? 'Awaiting check' : 'Done'}</span>
            <ChevronDown size={15} className="ch-chev" />
          </button>
          {expanded && <div className="ch-detail">
            <dl>
              <div><dt>How we know it’s done</dt><dd>{a.completionBasis || 'No completion basis recorded.'}</dd></div>
              {a.verification ? <div><dt><ShieldCheck size={11} /> Checked by {a.verification.by} · {dateLabel(a.verification.date)}</dt><dd>{a.verification.check}</dd></div>
                : awaiting ? <div><dt><ShieldCheck size={11} /> Check</dt><dd>This type needs a follow-up check that hasn’t been recorded yet.</dd></div> : null}
              {a.quote && <div><dt>Where it was agreed</dt><dd>“{a.quote}”</dd></div>}
            </dl>
            <div className="ch-detail-actions">{a.sourceId && <SourceLink id={a.sourceId} onOpen={props.showEvidence} label="Open the source" />}<button className="button button-small button-outline" onClick={() => reopen(a)}><RotateCcw size={13} />Reopen</button></div>
          </div>}
        </li>; })}</ul>
      </section>)}
  </Dialog>;
}
