import { useMemo, useState, type ReactNode } from 'react';
import { ArrowDownRight, ArrowLeft, ArrowRight, ArrowUpRight, CalendarCheck, Clock3, Database, Info, MessageSquareReply, Minus, Plus, Send } from 'lucide-react';
import { CLIENTS, DEMO_DATE, addDays, clientById, dateLabel, daysBetween } from '../data';
import { ACTIVE_IDS, AS_OF, CONFIG, DELIVERY_LABEL, FEEL_LABEL, METRICS, THEMES, TONE_LABEL, WEEK_ENDS, ZONE_MOVE, book, businessDays, coverageFor, fmtHours, fmtScore, isPlaced, nextMove, ownerOf, pct, recordFor, severity, snapshot, themeTrend, type Book, type Message, type MetricId, type RecordEvent, type Snapshot, type Theme, type ToneScore, type ZoneV3 } from '../health-v3';
import { ThemedSelect } from '../components/ThemedSelect';
import { isAdmin } from './Actions';
import { Avatar, Dialog, SourceLink } from '../components/UI';
import type { Action, WorkspaceProps } from '../types';
import './HealthRevised.css';
import './HealthV3.css';

/*
 * Health & Sentiment v3: the production view. Every number is computed by health-v3.ts from raw records
 * (client messages, reply threads, commitments, support issues), and every number can explain itself:
 * the (i) next to it gives the formula, source, window and target.
 */

type Props = WorkspaceProps & { addAction: (a: Action) => void };
const LAST_WEEK = WEEK_ENDS[6];
const zoneClass = (z: ZoneV3) => ({ Steady: 'z-steady', 'Fix our side': 'z-fix-our-side', 'Reach out': 'z-reach-out', Rescue: 'z-rescue' } as Record<string, string>)[z] || 'z-none';
const toneClass = (t: number) => `tone-${Math.max(0, Math.min(4, Math.round(t) + 2))}`;
const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const shortDate = (at: string) => dateLabel(at.slice(0, 10));

// ---- Shared bits ---------------------------------------------------------------------------------------
/** The (i) every metric carries: what it answers, how it's computed, from what, over what window. */
function MetricInfo({ id }: { id: MetricId }) {
  const [open, setOpen] = useState(false);
  const d = METRICS[id];
  return <span className="h3-info">
    <button aria-label={`How “${d.label}” is calculated`} aria-expanded={open} onClick={e => { e.stopPropagation(); setOpen(!open); }} onBlur={() => setOpen(false)}><Info size={12} /></button>
    {open && <span className="h3-pop" role="tooltip">
      <b>{d.question}</b>
      <span>{d.formula}</span>
      <dl><dt>Source</dt><dd>{d.source}</dd><dt>Window</dt><dd>{d.window}</dd>{d.target && <><dt>Target</dt><dd>{d.target}</dd></>}</dl>
    </span>}
  </span>;
}

type Status = 'ok' | 'warn' | 'bad' | 'none';
function Delta({ now, before, better, fmt }: { now: number | null; before: number | null; better: 'up' | 'down'; fmt: (n: number) => string }) {
  if (now === null || before === null) return <span className="h3-delta flat">no comparison</span>;
  const d = now - before;
  if (Math.abs(d) < 1e-9) return <span className="h3-delta flat"><Minus size={11} />same as last week</span>;
  const good = (d > 0) === (better === 'up');
  return <span className={`h3-delta ${good ? 'good' : 'bad'}`}>{d > 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}{fmt(Math.abs(d))} vs last week</span>;
}

function Kpi({ id, value, sub, status, delta }: { id: MetricId; value: ReactNode; sub: ReactNode; status: Status; delta: ReactNode }) {
  return <div className={`h3-kpi s-${status}`}>
    <div className="h3-kpi-top"><span>{METRICS[id].label}</span><MetricInfo id={id} /></div>
    <strong>{value}</strong>
    <small>{sub}</small>
    {delta}
  </div>;
}

function ZonePill({ zone }: { zone: ZoneV3 }) { return <span className={`hv-zone-pill ${zoneClass(zone)}`}>{zone}</span>; }

function ScoreChip({ s }: { s: Snapshot }) {
  if (s.score === null) return <span className="h3-score muted">Not enough to read</span>;
  const d = s.priorScore === null ? 0 : s.score - s.priorScore;
  return <span className={`h3-score ${toneClass(s.score)}`} title={`Tone score ${fmtScore(s.score)} (was ${fmtScore(s.priorScore)} 28 days ago)`}>
    <b>{FEEL_LABEL[s.feel!]}</b><em>{fmtScore(s.score)}</em>
    {s.priorScore !== null && (Math.abs(d) < 0.1 ? <Minus size={11} className="flat" /> : d < 0 ? <ArrowDownRight size={12} className="down" /> : <ArrowUpRight size={12} className="up" />)}
  </span>;
}

/** Tone score at each week end: the same computation run eight times. */
function ToneSpark({ id }: { id: string }) {
  const pts = WEEK_ENDS.map(w => snapshot(id, w).score);
  const w = 120, h = 30, step = w / 7, y = (v: number) => h / 2 - v / 2 * (h / 2 - 3);
  const path = pts.reduce((d, v, i) => v === null ? d : `${d}${d && pts[i - 1] !== null ? ' L' : ' M'}${(i * step).toFixed(1)} ${y(v).toFixed(1)}`, '');
  const last = pts[7];
  return <svg className="hv-spark h3-spark" viewBox={`-3 0 ${w + 6} ${h}`} aria-label="Tone score, last 8 weeks"><line x1="0" x2={w} y1={y(0)} y2={y(0)} className="spark-mid" /><path d={path} />{last !== null && <circle cx={w} cy={y(last)} r="3" />}</svg>;
}

// ---- Relationship map (positions computed, last week's position from the same computation) --------
const W = 680, H = 430, PAD = { l: 96, r: 16, t: 28, b: 62 };
const PW = W - PAD.l - PAD.r, PH = H - PAD.t - PAD.b;
const xOf = (d: number) => PAD.l + (d + 0.5) / 4 * PW;
const yOf = (f: number) => PAD.t + (3 - f + 0.5) / 4 * PH;
const X_SPLIT = PAD.l + PW / 2, Y_SPLIT = PAD.t + PH / 2, GAP = 4;

function RelationshipMap({ now, before, open }: { now: Snapshot[]; before: Snapshot[]; open: (id: string) => void }) {
  const placed = now.filter(isPlaced);
  const offsets = new Map<string, number>(); const seen = new Map<string, number>();
  placed.forEach(s => { const k = `${s.delivery}-${s.feel}`; const n = seen.get(k) || 0; offsets.set(s.clientId, n); seen.set(k, n + 1); });
  const quad = (x: number, y: number, z: ZoneV3, label: string, anchor: 'start' | 'end', top: boolean) => <g className={`map-quad ${zoneClass(z)}`}>
    <rect x={x} y={y} width={PW / 2 - GAP} height={PH / 2 - GAP} rx="12" />
    <text x={anchor === 'start' ? x + 14 : x + PW / 2 - GAP - 14} y={top ? y + 20 : y + PH / 2 - GAP - 12} textAnchor={anchor} className="map-quad-label">{label}</text>
  </g>;
  return <svg className="hv-map" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Relationship map: tone band against delivery level, with last week's position">
    <defs><marker id="h3-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 8 4 0 8z" className="map-arrow" /></marker></defs>
    {quad(PAD.l, PAD.t, 'Steady', 'STEADY', 'start', true)}
    {quad(X_SPLIT + GAP, PAD.t, 'Fix our side', 'FIX OUR SIDE', 'end', true)}
    {quad(PAD.l, Y_SPLIT + GAP, 'Reach out', 'REACH OUT', 'start', false)}
    {quad(X_SPLIT + GAP, Y_SPLIT + GAP, 'Rescue', 'RESCUE', 'end', false)}
    {[1, 3].map(i => <line key={`v${i}`} x1={PAD.l + i / 4 * PW} x2={PAD.l + i / 4 * PW} y1={PAD.t + 6} y2={PAD.t + PH - 6} className="map-step" />)}
    {[1, 3].map(i => <line key={`h${i}`} y1={PAD.t + i / 4 * PH} y2={PAD.t + i / 4 * PH} x1={PAD.l + 6} x2={PAD.l + PW - 6} className="map-step" />)}
    {FEEL_LABEL.map((f, i) => <text key={f} x={PAD.l - 10} y={yOf(i) + 3} textAnchor="end" className="map-axis"><title>{`Tone score ${['below −1', '−1 to 0', '0 to +1', '+1 or more'][i]}`}</title>{f}</text>)}
    {DELIVERY_LABEL.map((d, i) => <text key={d} x={xOf(i)} y={PAD.t + PH + 18} textAnchor="middle" className="map-axis">{d}</text>)}
    <text x={14} y={(PAD.t + Y_SPLIT) / 2} className="map-half" transform={`rotate(-90 14 ${(PAD.t + Y_SPLIT) / 2})`} textAnchor="middle">SCORE ≥ 0</text>
    <text x={14} y={(Y_SPLIT + PAD.t + PH) / 2} className="map-half" transform={`rotate(-90 14 ${(Y_SPLIT + PAD.t + PH) / 2})`} textAnchor="middle">SCORE &lt; 0</text>
    <text x={(PAD.l + X_SPLIT) / 2} y={PAD.t + PH + 38} textAnchor="middle" className="map-half">NOTHING LATE YET</text>
    <text x={(X_SPLIT + PAD.l + PW) / 2} y={PAD.t + PH + 38} textAnchor="middle" className="map-half">SOMETHING LATE</text>
    <text x={PAD.l} y={PAD.t - 10} className="map-axis-title">↑ HOW THEY SOUND (tone score)</text>
    <text x={W - PAD.r} y={H - 4} textAnchor="end" className="map-axis-title">HOW WE’RE DOING (highest rule fired) →</text>
    {placed.map(s => {
      const b = before.find(x => x.clientId === s.clientId)!;
      const k = offsets.get(s.clientId)!; const o = (k % 2 ? -1 : 1) * Math.ceil(k / 2) * 40;
      const x = xOf(s.delivery) + o, y = yOf(s.feel!);
      const hasBefore = b && isPlaced(b);
      const bx = hasBefore ? xOf(b.delivery) + o : x, by = hasBefore ? yOf(b.feel!) : y;
      const moved = Math.hypot(x - bx, y - by) > 4; const c = clientById(s.clientId);
      return <g key={s.clientId} className={`map-client ${zoneClass(s.zone)}`} role="button" tabIndex={0} aria-label={`${c.name}: ${FEEL_LABEL[s.feel!]} (${fmtScore(s.score)}), ${DELIVERY_LABEL[s.delivery]}. ${s.zone}. Open`} onClick={() => open(s.clientId)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(s.clientId); } }}>
        {moved && <><circle cx={bx} cy={by} r="6" className="map-ghost" /><line x1={bx} y1={by} x2={x - (x - bx) * 0.2} y2={y - (y - by) * 0.2} className="map-trail" markerEnd="url(#h3-arrow)" /></>}
        <circle cx={x} cy={y} r="15" className="map-dot" />
        <text x={x} y={y + 3.5} textAnchor="middle" className="map-initials">{c.initials}</text>
        <text x={x} y={y + 31} textAnchor="middle" className="map-name">{c.name}</text>
      </g>;
    })}
  </svg>;
}

// ---- 1. This week -----------------------------------------------------------------------------------------
/** Why a client moved between two runs, stated as the facts that differ. */
function changeReasons(now: Snapshot, before: Snapshot) {
  const out: string[] = [];
  if (now.score !== null && before.score !== null && Math.abs(now.score - before.score) >= 0.25) out.push(`Tone score ${fmtScore(before.score)} → ${fmtScore(now.score)} (${plural(now.scored.length, 'scored message')})`);
  if (now.delivery !== before.delivery) out.push(`Delivery ${DELIVERY_LABEL[before.delivery]} → ${DELIVERY_LABEL[now.delivery]}${now.triggers[0] && now.delivery > before.delivery ? `: ${now.triggers[0].text}` : ''}`);
  return out;
}

function WeekTab({ cur, prev, viewer, open, goActions, notify }: { cur: Book; prev: Book; viewer: string; open: (id: string) => void; goActions: () => void; notify: (m: string) => void }) {
  const [mine, setMine] = useState(!isAdmin(viewer));
  const onTime = pct(cur.kept, cur.due), onTimePrev = pct(prev.kept, prev.due);
  const cov = pct(cur.readable, cur.active)!;
  const changes = cur.snaps.map(s => ({ s, b: prev.snaps.find(x => x.clientId === s.clientId)! }))
    .filter(({ s, b }) => s.zone !== b.zone || (s.score !== null && b.score !== null && Math.abs(s.score - b.score) >= 0.5))
    .sort((x, y) => (severity(y.s.zone) - severity(y.b.zone)) - (severity(x.s.zone) - severity(x.b.zone)) || severity(y.s.zone) - severity(x.s.zone));
  const inScope = (id: string) => !mine || ownerOf(id) === viewer;
  const waits = cur.snaps.filter(s => inScope(s.clientId)).flatMap(s => s.waiting.map(w => ({ ...w, clientId: s.clientId }))).sort((a, b) => b.days - a.days);
  const promises = cur.snaps.filter(s => inScope(s.clientId)).flatMap(s => [...s.overdue.map(o => ({ c: o.c, late: o.days })), ...s.dueSoon.map(c => ({ c, late: 0 }))]).sort((a, b) => b.late - a.late || a.c.due.localeCompare(b.c.due));
  return <>
    <div className="h3-kpis">
      <Kpi id="needMove" value={cur.needMove} sub={`of ${cur.placed} clients on the map`} status={cur.needMove ? 'warn' : 'ok'} delta={<Delta now={cur.needMove} before={prev.needMove} better="down" fmt={n => `${n}`} />} />
      <Kpi id="waiting" value={cur.waiting} sub={cur.waiting ? `oldest ${plural(cur.oldestWait, 'business day')}` : 'nobody waiting 1+ business day'} status={cur.oldestWait >= CONFIG.waitBroken ? 'bad' : cur.waiting ? 'warn' : 'ok'} delta={<Delta now={cur.waiting} before={prev.waiting} better="down" fmt={n => `${n}`} />} />
      <Kpi id="reply" value={fmtHours(cur.replyMedian)} sub={`target ≤ ${CONFIG.replyTargetHours} business hours`} status={cur.replyMedian === null ? 'none' : cur.replyMedian <= CONFIG.replyTargetHours ? 'ok' : 'warn'} delta={<Delta now={cur.replyMedian} before={prev.replyMedian} better="down" fmt={fmtHours} />} />
      <Kpi id="onTime" value={onTime === null ? '—' : `${onTime}%`} sub={`${cur.kept} of ${cur.due} due in 28 days`} status={onTime === null ? 'none' : onTime >= CONFIG.onTimeTarget * 100 ? 'ok' : onTime >= 75 ? 'warn' : 'bad'} delta={<Delta now={onTime} before={onTimePrev} better="up" fmt={n => `${n} pts`} />} />
      <Kpi id="overdue" value={cur.overdue} sub={cur.overdue ? `longest ${plural(cur.maxLate, 'business day')} late` : 'nothing past due'} status={cur.maxLate > CONFIG.lateBrokenDays ? 'bad' : cur.overdue ? 'warn' : 'ok'} delta={<Delta now={cur.overdue} before={prev.overdue} better="down" fmt={n => `${n}`} />} />
      <Kpi id="coverage" value={`${cov}%`} sub={`${cur.readable} of ${cur.active} clients have enough to read`} status={cov >= 80 ? 'ok' : 'warn'} delta={<Delta now={cov} before={pct(prev.readable, prev.active)} better="up" fmt={n => `${n} pts`} />} />
    </div>

    <div className="hv-top">
      <section className="hv-card hv-map-card" aria-label="Relationship map">
        <header><h2>Relationship map</h2><p>Where each client sits on tone score and delivery level today. Hover a client to see where the same computation put them last week.</p></header>
        <RelationshipMap now={cur.snaps} before={prev.snaps} open={open} />
        {cur.snaps.some(s => !isPlaced(s)) && <div className="hv-offmap"><span className="small-label">NOT ON THE MAP</span>{cur.snaps.filter(s => !isPlaced(s)).map(s => <button key={s.clientId} className="hv-offmap-client" onClick={() => open(s.clientId)}><Avatar client={clientById(s.clientId)} small />{clientById(s.clientId).name}<em>{s.zone}</em></button>)}</div>}
      </section>
      <section className="hv-card hv-week" aria-label="What changed since last week">
        <header><h2>What changed since {dateLabel(LAST_WEEK)}</h2><p>Clients whose zone moved or whose tone score shifted by 0.5 or more, with the facts that changed.</p></header>
        {changes.length ? <ol>{changes.map(({ s, b }) => { const c = clientById(s.clientId); const worse = severity(s.zone) > severity(b.zone) || (s.score ?? 0) < (b.score ?? 0); const ev = [...s.scored].filter(x => worse ? x.msg.tone! < 0 : x.msg.tone! > 0).sort((x, y) => y.msg.at.localeCompare(x.msg.at))[0]?.msg; return <li key={s.clientId} className={zoneClass(s.zone)}>
          <button className="hv-story" onClick={() => open(s.clientId)}>
            <span className="hv-story-head"><strong>{c.name}</strong><span className="hv-shift">{b.zone !== s.zone && <>{b.zone}<ArrowRight size={11} /></>}<span className="hv-zone-pill">{s.zone}</span></span></span>
            <ul className="h3-reasons">{changeReasons(s, b).map(r => <li key={r}>{r}</li>)}</ul>
            {ev && <span className="hv-story-quote">“{ev.quote!.length > 110 ? `${ev.quote!.slice(0, 108)}…` : ev.quote}” <em>{ev.speaker.split(' ')[0]}, {shortDate(ev.at)} · {TONE_LABEL[ev.tone!]}</em></span>}
            <span className="hv-story-move">{nextMove(s).text} <b>{ownerOf(s.clientId)}</b></span>
          </button>
        </li>; })}</ol> : <p className="rb-empty">No zone changes and no large tone shifts this week.</p>}
      </section>
    </div>

    <section className="hv-card hv-owe" aria-label="What we owe today">
      <header className="hv-list-head"><div><h2>What we owe today</h2><p>Open replies and promises, oldest first. These are the facts that set each client’s delivery level.</p></div>
        <div className="rb-layout" role="group" aria-label="Whose clients"><button className={mine ? 'selected' : ''} aria-pressed={mine} onClick={() => setMine(true)}>My clients</button><button className={!mine ? 'selected' : ''} aria-pressed={!mine} onClick={() => setMine(false)}>Everyone</button></div>
      </header>
      <div className="hv-owe-grid">
        <div><h3><MessageSquareReply size={15} />Waiting on our reply<span className="hv-count">{waits.length}</span><MetricInfo id="waiting" /></h3>
          {waits.length ? <ul className="hv-issues">{waits.map(w => <li key={w.thread.id} className={w.days >= CONFIG.waitBehind ? 'is-hot' : ''} style={{ ['--z' as string]: w.days >= CONFIG.waitBroken ? 'var(--rescue)' : 'var(--fix)' }}><div className="hv-issue-top"><button className="hv-ctag" onClick={() => open(w.clientId)}><Avatar client={clientById(w.clientId)} small />{clientById(w.clientId).name}</button><span className="hv-age">{w.days ? plural(w.days, 'business day') : 'today'}</span></div><p className="hv-issue-quote">“{w.thread.text}”</p><small>{w.thread.from} · {w.thread.channel} · {shortDate(w.thread.at)} · owner {ownerOf(w.clientId)}</small><div className="drawer-inline"><button className="button button-small button-outline" onClick={() => notify(`Preview: opens the ${w.thread.channel} thread to reply to ${w.thread.from.split(' ')[0]}.`)}>Open thread</button></div></li>)}</ul> : <p className="rb-empty">Nobody is waiting on us{mine ? ' on your clients' : ''}.</p>}
        </div>
        <div><h3><Clock3 size={15} />Promises late or due in 2 days<span className="hv-count">{promises.length}</span><MetricInfo id="overdue" /></h3>
          {promises.length ? <ul className="hv-issues">{promises.map(({ c, late }) => <li key={c.id} className={late ? 'is-hot' : ''} style={{ ['--z' as string]: late ? 'var(--rescue)' : 'var(--fix)' }}><div className="hv-issue-top"><button className="hv-ctag" onClick={() => open(c.clientId)}><Avatar client={clientById(c.clientId)} small />{clientById(c.clientId).name}</button><span className="hv-age">{late ? `${plural(late, 'business day')} late` : c.due === AS_OF ? 'due today' : `due ${dateLabel(c.due)}`}</span></div><p className="hv-issue-title">{c.title}</p><small>{c.owner} · promised {dateLabel(c.madeOn)} on {c.source} · due {dateLabel(c.due)}</small><div className="drawer-inline"><button className="button button-small button-outline" onClick={goActions}>Open in Action Hub</button></div></li>)}</ul> : <p className="rb-empty">Every promise is on track{mine ? ' for your clients' : ''}.</p>}
        </div>
      </div>
    </section>
  </>;
}

// ---- 2. Clients -----------------------------------------------------------------------------------------
const ZONE_FILTERS: ('all' | ZoneV3)[] = ['all', 'Rescue', 'Fix our side', 'Reach out', 'Steady', 'Not enough to read', 'Settling in'];

function ClientsTab({ cur, props, openId, setOpenId }: { cur: Book; props: Props; openId: string | null; setOpenId: (id: string | null) => void }) {
  const [zone, setZone] = useState<'all' | ZoneV3>('all');
  const [owner, setOwner] = useState('all');
  const [layout, setLayout] = useState<'table' | 'cards'>('table');
  if (openId) return <ClientView s={cur.snaps.find(s => s.clientId === openId)!} props={props} back={() => setOpenId(null)} />;
  const owners = [...new Set(cur.snaps.map(s => ownerOf(s.clientId)).filter(Boolean))];
  const list = cur.snaps.filter(s => (zone === 'all' || s.zone === zone) && (owner === 'all' || ownerOf(s.clientId) === owner))
    .sort((a, b) => severity(b.zone) - severity(a.zone) || b.delivery - a.delivery || (a.score ?? 9) - (b.score ?? 9));
  return <>
    <div className="hv-clients-bar">
      <div className="hv-zone-filter" role="group" aria-label="Zone">{ZONE_FILTERS.map(z => { const n = z === 'all' ? cur.snaps.length : cur.snaps.filter(s => s.zone === z).length; if (!n && z !== 'all') return null; return <button key={z} className={`${zone === z ? 'selected' : ''} ${z !== 'all' ? zoneClass(z) : ''}`} aria-pressed={zone === z} onClick={() => setZone(z)}>{z === 'all' ? 'All clients' : z}<span>{n}</span></button>; })}</div>
      <div className="hv-list-tools">
        <ThemedSelect aria-label="Owner" value={owner} onChange={setOwner}><option value="all">All owners</option>{owners.map(o => <option key={o} value={o}>{o}</option>)}</ThemedSelect>
        <div className="rb-layout" role="group" aria-label="Layout"><button className={layout === 'table' ? 'selected' : ''} aria-pressed={layout === 'table'} onClick={() => setLayout('table')}>Table</button><button className={layout === 'cards' ? 'selected' : ''} aria-pressed={layout === 'cards'} onClick={() => setLayout('cards')}>Cards</button></div>
      </div>
    </div>
    {layout === 'table' ? <div className="hv-card h3-table-wrap"><table className="h3-table">
      <thead><tr><th>Client</th><th>Zone</th><th>Tone score <MetricInfo id="tone" /></th><th>Negative <MetricInfo id="negShare" /></th><th>Last heard <MetricInfo id="lastHeard" /></th><th>Waiting <MetricInfo id="waiting" /></th><th>Late <MetricInfo id="overdue" /></th><th>On time <MetricInfo id="onTime" /></th><th>First reply <MetricInfo id="reply" /></th><th>Issues <MetricInfo id="issues" /></th></tr></thead>
      <tbody>{list.map(s => { const c = clientById(s.clientId); const w = s.waiting[0]; const ot = pct(s.onTime.kept, s.onTime.due); return <tr key={s.clientId} onClick={() => setOpenId(s.clientId)} tabIndex={0} onKeyDown={e => { if (e.key === 'Enter') setOpenId(s.clientId); }}>
        <td><span className="hv-client"><Avatar client={c} small /><span><strong>{c.name}</strong><small>{ownerOf(s.clientId) || 'No owner'}</small></span></span></td>
        <td><ZonePill zone={s.zone} /></td>
        <td><ScoreChip s={s} /></td>
        <td>{s.negShare === null ? '—' : `${Math.round(s.negShare * 100)}%`}</td>
        <td>{s.lastHeard ? `${daysBetween(s.lastHeard.at.slice(0, 10), AS_OF)}d ago` : '—'}</td>
        <td className={w && w.days >= CONFIG.waitAtRisk ? 'is-bad' : ''}>{s.waiting.length ? `${s.waiting.length} · ${w.days}bd` : '0'}</td>
        <td className={s.overdue.length ? 'is-bad' : ''}>{s.overdue.length ? `${s.overdue.length} · ${s.overdue[0].days}bd` : '0'}</td>
        <td className={ot !== null && ot < CONFIG.onTimeTarget * 100 ? 'is-warn' : ''}>{ot === null ? '—' : `${ot}%`}<small> {s.onTime.kept}/{s.onTime.due}</small></td>
        <td className={s.replyMedian !== null && s.replyMedian > CONFIG.replyTargetHours ? 'is-warn' : ''}>{fmtHours(s.replyMedian)}</td>
        <td className={s.issues.some(i => i.repeat) ? 'is-bad' : ''}>{s.issues.length ? `${s.issues.length}${s.issues.some(i => i.repeat) ? ' · repeat' : ''}` : '0'}</td>
      </tr>; })}</tbody>
    </table>{!list.length && <p className="rb-empty">No clients match these filters.</p>}</div>
      : <div className="hv-client-grid">{list.map(s => { const c = clientById(s.clientId); return <button key={s.clientId} className={`hv-client-card ${zoneClass(s.zone)}`} onClick={() => setOpenId(s.clientId)}>
        <span className="hv-cc-top"><Avatar client={c} small /><span className="hv-cc-name"><strong>{c.name}</strong><small>{c.service} · {ownerOf(s.clientId) || 'No owner'}</small></span><span className="hv-zone-pill">{s.zone}</span></span>
        <span className="hv-cc-spark"><ToneSpark id={s.clientId} /><small>tone, 8 weeks</small></span>
        <span className="hv-cc-facts"><span><small>Tone score</small><ScoreChip s={s} /></span><span><small>Delivery</small><b className={`hv-deliv d-${s.delivery}`}>{DELIVERY_LABEL[s.delivery]}</b></span></span>
        <span className="h3-cc-why">{s.triggers[0] ? s.triggers[0].text : 'No delivery rule fired.'}</span>
        <span className="hv-cc-foot"><span>{s.lastHeard ? `last heard ${daysBetween(s.lastHeard.at.slice(0, 10), AS_OF)}d ago` : 'not heard yet'}</span>{s.waiting[0]?.days ? <span className="hv-cc-flag">Waiting {s.waiting[0].days}bd</span> : null}</span>
      </button>; })}{!list.length && <p className="rb-empty">No clients match these filters.</p>}</div>}
    <p className="hv-rules">Computed {dateLabel(AS_OF)} from client messages, reply threads, the Action Hub and support issues. Tone uses only words the client wrote or said. Tone and delivery are never combined into one score; the zone is where they meet.</p>
  </>;
}

// ---- Client page ----------------------------------------------------------------------------------------
function Tile({ id, value, sub, status }: { id: MetricId; value: ReactNode; sub: ReactNode; status: Status }) {
  return <div className={`h3-tile s-${status}`}><div className="h3-kpi-top"><span>{METRICS[id].label}</span><MetricInfo id={id} /></div><strong>{value}</strong><small>{sub}</small></div>;
}

const TL = { w: 620, h: 236, l: 86, r: 14, t: 12, b: 64 };
const tStart = new Date(`${WEEK_ENDS[0]}T12:00:00Z`).getTime() - 6 * 86400000, tEnd = new Date(`${WEEK_ENDS[7]}T12:00:00Z`).getTime();
const tx = (date: string) => TL.l + (new Date(`${date.slice(0, 10)}T12:00:00Z`).getTime() - tStart) / (tEnd - tStart) * (TL.w - TL.l - TL.r);
const ty = (score: number) => TL.t + (2 - score) / 4 * (TL.h - TL.t - TL.b);
const BAD_KINDS = new Set(['missed', 'late', 'slow-reply', 'waiting', 'issue-open', 'issue-reopen']);

function ClientChart({ id, picked, pick }: { id: string; picked?: Message; pick: (m: Message) => void }) {
  const weeks = WEEK_ENDS.map(w => snapshot(id, w));
  const line = weeks.map((s, i) => s.score === null ? null : [tx(WEEK_ENDS[i]), ty(s.score)] as const);
  const path = line.reduce((d, pt, i) => pt ? `${d}${d && line[i - 1] ? ' L' : ' M'}${pt[0].toFixed(1)} ${pt[1].toFixed(1)}` : d, '');
  const msgs = recordFor(id).filter(e => e.kind === 'said').map(e => e.msg!);
  const ours = recordFor(id).filter(e => e.side === 'us' && e.kind !== 'promised');
  const base = TL.h - TL.b;
  return <svg className="hv-timeline" viewBox={`0 0 ${TL.w} ${TL.h}`} role="img" aria-label="Eight weeks: weekly tone score, each scored message, the zone each week and what happened on our side">
    {([2, 1, 0, -1, -2] as ToneScore[]).map(t => <g key={t}><line x1={TL.l} x2={TL.w - TL.r} y1={ty(t)} y2={ty(t)} className={t === 0 ? 'tl-grid h3-zero' : 'tl-grid'} /><text x={TL.l - 8} y={ty(t) + 3} textAnchor="end" className="tl-axis">{t > 0 ? `+${t}` : t} {TONE_LABEL[t].replace('Very ', 'v. ')}</text></g>)}
    {WEEK_ENDS.map(w => <text key={w} x={tx(w)} y={base + 14} textAnchor="middle" className="tl-axis">{dateLabel(w)}</text>)}
    <text x={TL.l - 8} y={base + 30} textAnchor="end" className="tl-axis">Zone</text>
    {weeks.map((s, i) => { const x0 = i ? tx(WEEK_ENDS[i - 1]) : TL.l; return <rect key={i} x={x0 + 1.5} y={base + 23} width={tx(WEEK_ENDS[i]) - x0 - 3} height={9} rx="3" className={`tl-zone ${zoneClass(s.zone)} ${isPlaced(s) ? '' : 'is-none'}`}><title>{`Week to ${dateLabel(WEEK_ENDS[i])}: ${s.zone} · tone ${fmtScore(s.score)} · ${DELIVERY_LABEL[s.delivery]}`}</title></rect>; })}
    <path d={path} className="tl-line" />
    {line.map((pt, i) => pt && <circle key={i} cx={pt[0]} cy={pt[1]} r="3" className="tl-week"><title>{`Tone score at ${dateLabel(WEEK_ENDS[i])}: ${fmtScore(weeks[i].score)}`}</title></circle>)}
    {msgs.map((msg, i) => <circle key={msg.id} cx={tx(msg.at)} cy={ty(msg.tone!) + (i % 2 ? 3 : -3)} r={msg === picked ? 7 : 5.5} className={`tl-read ${toneClass(msg.tone!)} ${msg.confidence === 'Low' ? 'is-low' : ''} ${msg === picked ? 'is-picked' : ''}`} role="button" tabIndex={0} aria-label={`${shortDate(msg.at)}, ${TONE_LABEL[msg.tone!]}: ${msg.quote}`} onClick={() => pick(msg)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(msg); } }}><title>{`${TONE_LABEL[msg.tone!]}${msg.confidence === 'Low' ? ' (low confidence, not counted)' : ''} · ${shortDate(msg.at)}`}</title></circle>)}
    <text x={TL.l - 8} y={TL.h - 9} textAnchor="end" className="tl-axis">Our side</text>
    {ours.map((e, i) => { const x = tx(e.date), y = TL.h - 12, bad = BAD_KINDS.has(e.kind); return <g key={i} className={`tl-event ${bad ? 'slip' : 'fix'}`}><path d={bad ? `M${x - 5} ${y - 4} L${x + 5} ${y - 4} L${x} ${y + 4} Z` : `M${x - 5} ${y + 4} L${x + 5} ${y + 4} L${x} ${y - 4} Z`} /><title>{`${dateLabel(e.date)}: ${e.text}`}</title></g>; })}
  </svg>;
}

const weekIndexOf = (date: string) => { const i = WEEK_ENDS.findIndex(w => date <= w); return i < 0 ? 7 : i; };
const EVENT_LABEL: Record<RecordEvent['kind'], string> = { said: 'They said', promised: 'We promised', kept: 'Kept', late: 'Delivered late', missed: 'Missed', replied: 'Replied', 'slow-reply': 'Slow reply', waiting: 'Still waiting', 'issue-open': 'Issue reported', 'issue-reopen': 'Reported again', 'issue-fixed': 'Fixed' };

function ClientView({ s, props, back }: { s: Snapshot; props: Props; back: () => void }) {
  const id = s.clientId, c = clientById(id), owner = ownerOf(id);
  const [picked, setPicked] = useState<Message | undefined>();
  const [show, setShow] = useState<'all' | 'client' | 'us'>('all');
  const [theme, setTheme] = useState<Theme | null>(null);
  const weeks = useMemo(() => WEEK_ENDS.map(w => snapshot(id, w)), [id]);
  let streak = 1; while (streak < 8 && weeks[7 - streak].zone === s.zone) streak++;
  const prevZone = streak < 8 ? weeks[7 - streak].zone : null;
  const move = nextMove(s); const cov = coverageFor(id);
  const record = recordFor(id).filter(e => (show === 'all' || e.side === show) && (!theme || e.msg?.theme === theme));
  const recWeeks = [...new Set(record.map(e => weekIndexOf(e.date)))];
  const allMsgs = recordFor(id).filter(e => e.kind === 'said').map(e => e.msg!).filter(x => x.confidence === 'High');
  const themes = THEMES.map(t => ({ t, rs: allMsgs.filter(x => x.theme === t) })).filter(x => x.rs.length).sort((a, b) => b.rs.filter(x => x.tone! < 0).length - a.rs.filter(x => x.tone! < 0).length || b.rs.length - a.rs.length);
  const ot = pct(s.onTime.kept, s.onTime.due); const ratio = s.usual ? s.volume / s.usual : null;
  const totalW = s.scored.reduce((n, x) => n + x.weight, 0);
  const pick = (msg: Message) => { setPicked(msg); setShow('all'); setTheme(null); requestAnimationFrame(() => document.getElementById(`h3-rec-${msg.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })); };
  const addStep = () => { props.addAction({ id: `h3-${id}-${Date.now()}`, clientId: id, title: move.text, owner, due: '', status: 'Open', side: 'WIA', acknowledged: false, sourceId: '', origin: 'AI proposal', priority: s.zone === 'Rescue' ? 'High' : 'Medium', note: `Suggested by the Health & Sentiment rule: ${move.why}`, assignedOn: owner ? DEMO_DATE : undefined, lastActivity: DEMO_DATE, history: [{ date: DEMO_DATE, text: `Added from Health & Sentiment by ${props.viewer}.` }] }); props.notify('Added to the Action Hub as a proposed action.'); };

  return <div className="hv-client-view">
    <button className="text-button hv-back" onClick={back}><ArrowLeft size={13} />All clients</button>
    <header className={`hv-cv-head ${zoneClass(s.zone)}`}>
      <div className="hv-cv-id"><Avatar client={c} /><div><h2>{c.name}</h2><p>{c.service} · {owner || 'No owner'} · client since {dateLabel(c.since)}</p></div></div>
      <div className="hv-cv-state">
        <span className="hv-zone-pill">{s.zone}</span>
        <p>{ZONE_MOVE[s.zone]}</p>
        <dl><div><dt>Tone score</dt><dd><ScoreChip s={s} /></dd></div><div><dt>Delivery</dt><dd>{DELIVERY_LABEL[s.delivery]}</dd></div><div><dt>In this zone</dt><dd>{streak === 8 ? '8+ weeks' : plural(streak, 'week')}{prevZone ? ` · was ${prevZone}` : ''}</dd></div></dl>
      </div>
    </header>

    <div className="h3-scorecard">
      <section><p className="small-label">HOW THEY SOUND</p><div className="h3-tiles">
        <Tile id="tone" value={fmtScore(s.score)} sub={s.score === null ? `${plural(s.scored.length, 'scored message')}; needs ${CONFIG.minScored}` : `${FEEL_LABEL[s.feel!]} · was ${fmtScore(s.priorScore)} 28 days ago`} status={s.score === null ? 'none' : s.score >= 0 ? 'ok' : s.score >= -1 ? 'warn' : 'bad'} />
        <Tile id="negShare" value={s.negShare === null ? '—' : `${Math.round(s.negShare * 100)}%`} sub={`${s.scored.filter(x => x.msg.tone! < 0).length} of ${plural(s.scored.length, 'scored message')}`} status={s.negShare === null ? 'none' : s.negShare >= 0.5 ? 'bad' : s.negShare > 0 ? 'warn' : 'ok'} />
        <Tile id="volume" value={ratio === null ? '—' : `${Math.round(ratio * 100)}%`} sub={`${s.volume} messages vs about ${Math.round(s.usual)} usually`} status={ratio === null ? 'none' : ratio < CONFIG.quietRatio ? 'bad' : ratio < 0.75 ? 'warn' : 'ok'} />
        <Tile id="lastHeard" value={s.lastHeard ? `${daysBetween(s.lastHeard.at.slice(0, 10), AS_OF)}d` : '—'} sub={s.lastHeard ? `${s.lastHeard.speaker.split(' ')[0]} on ${s.lastHeard.channel}, ${shortDate(s.lastHeard.at)}` : 'No messages yet'} status={!s.lastHeard ? 'none' : daysBetween(s.lastHeard.at.slice(0, 10), AS_OF) > 14 ? 'warn' : 'ok'} />
      </div></section>
      <section><p className="small-label">HOW WE’RE DOING</p><div className="h3-tiles">
        <Tile id="waiting" value={s.waiting.length} sub={s.waiting[0] ? `oldest ${plural(s.waiting[0].days, 'business day')}` : 'nobody waiting'} status={!s.waiting.length ? 'ok' : s.waiting[0].days >= CONFIG.waitBehind ? 'bad' : 'warn'} />
        <Tile id="overdue" value={s.overdue.length} sub={s.overdue[0] ? `longest ${plural(s.overdue[0].days, 'business day')}` : s.dueSoon.length ? `${s.dueSoon.length} due within 2 days` : 'nothing late'} status={s.overdue.length ? 'bad' : s.dueSoon.length ? 'warn' : 'ok'} />
        <Tile id="onTime" value={ot === null ? '—' : `${ot}%`} sub={`${s.onTime.kept} of ${s.onTime.due} due in 28 days`} status={ot === null ? 'none' : ot >= CONFIG.onTimeTarget * 100 ? 'ok' : ot >= 75 ? 'warn' : 'bad'} />
        <Tile id="reply" value={fmtHours(s.replyMedian)} sub={`${plural(s.replyHours.length, 'thread')} answered in 28 days`} status={s.replyMedian === null ? 'none' : s.replyMedian <= CONFIG.replyTargetHours ? 'ok' : 'warn'} />
        <Tile id="issues" value={s.issues.length} sub={s.issues.some(i => i.repeat) ? 'includes a repeat issue' : s.issues.length ? `oldest ${plural(Math.max(...s.issues.map(i => i.days)), 'business day')}` : 'none open'} status={s.issues.some(i => i.repeat) ? 'bad' : s.issues.length ? 'warn' : 'ok'} />
      </div></section>
    </div>

    <div className="hv-cv-body">
      <div className="hv-cv-main">
        <section className="hv-card">
          <header><h2>Why {s.zone === 'Settling in' || s.zone === 'Not enough to read' ? 'this reading' : s.zone}</h2><p>The zone is where the two readings meet. Each is worked out below from the records, so you can check it.</p></header>
          <div className="h3-why">
            <div>
              <h3>Tone score {fmtScore(s.score)}{s.feel !== null && <> → <b>{FEEL_LABEL[s.feel]}</b></>}</h3>
              {s.scored.length ? <table className="h3-calc"><thead><tr><th>Message</th><th>Tone</th><th>Weight</th></tr></thead><tbody>{[...s.scored].sort((a, b) => b.msg.at.localeCompare(a.msg.at)).map(x => <tr key={x.msg.id}><td><span className="h3-calc-q">“{x.msg.quote!.length > 70 ? `${x.msg.quote!.slice(0, 68)}…` : x.msg.quote}”</span><small>{shortDate(x.msg.at)} · {x.msg.theme}</small></td><td className={toneClass(x.msg.tone!)}><span className="hv-tone">{x.msg.tone! > 0 ? '+' : ''}{x.msg.tone}</span></td><td>{Math.round(x.weight / totalW * 100)}%</td></tr>)}</tbody></table> : <p className="rb-empty">No scored messages in the last 28 days.</p>}
              <p className="h3-formula">Weighted average of {plural(s.scored.length, 'message')} from the last 28 days{s.lowExcluded ? `; ${s.lowExcluded} low-confidence ${s.lowExcluded === 1 ? 'reading' : 'readings'} left out` : ''}. Bands: below −1 Frustrated · −1 to 0 Uneasy · 0 to +1 Satisfied · +1 or more Delighted.</p>
            </div>
            <div>
              <h3>Delivery → <b>{DELIVERY_LABEL[s.delivery]}</b></h3>
              {s.triggers.length ? <ul className="h3-triggers">{s.triggers.map((t, i) => <li key={i} className={`lvl-${t.level}`}><span className="h3-lvl">{DELIVERY_LABEL[t.level]}</span><div><p>{t.text}</p><small>Rule: {t.rule}</small></div></li>)}</ul> : <p className="rb-empty">No rule fired: nothing late, nobody waiting, no open issues.</p>}
              <p className="h3-formula">The highest level of any rule that fires sets delivery. Rules and thresholds are listed under How it’s measured.</p>
            </div>
          </div>
        </section>

        <section className="hv-card">
          <header><h2>Eight weeks, both sides</h2><p>The line is the tone score recomputed at each week’s end. Dots are scored messages (hollow = low confidence, not counted). The band is that week’s zone. Triangles are our side: ▼ missed, late, slow or reported, ▲ kept, fixed or answered on time.</p></header>
          <ClientChart id={id} picked={picked} pick={pick} />
        </section>

        <section className="hv-card">
          <header className="hv-list-head"><div><h2>The record</h2><p>Everything both sides did, generated from the records and grouped by week.{theme ? <> Showing <b>{theme}</b> only. <button className="text-button" onClick={() => setTheme(null)}>Clear</button></> : null}</p></div>
            <div className="rb-layout" role="group" aria-label="Show">{([['all', 'Both sides'], ['client', 'They said'], ['us', 'We did']] as const).map(([k, l]) => <button key={k} className={show === k ? 'selected' : ''} aria-pressed={show === k} onClick={() => setShow(k)}>{l}</button>)}</div>
          </header>
          {recWeeks.length ? recWeeks.map(wi => { const ws = weeks[wi]; return <div key={wi} className="hv-rec-week">
            <div className={`hv-rec-week-head ${zoneClass(ws.zone)} ${isPlaced(ws) ? '' : 'is-none'}`}><span className="hv-rec-swatch" /><b>Week to {dateLabel(WEEK_ENDS[wi])}</b><span>{ws.zone}</span><span>tone {fmtScore(ws.score)} · {DELIVERY_LABEL[ws.delivery]}</span></div>
            <ul className="hv-feed">{record.filter(e => weekIndexOf(e.date) === wi).map((e, i) => e.msg
              ? <li key={i} id={`h3-rec-${e.msg.id}`} className={`${toneClass(e.msg.tone!)} ${e.msg === picked ? 'is-picked' : ''}`}><span className={`hv-tone-dot ${e.msg.confidence === 'Low' ? 'is-low' : ''}`} aria-hidden="true" /><div><p>“{e.msg.quote}”</p><footer><span>{e.msg.speaker} · {e.msg.channel} · {shortDate(e.msg.at)}</span>{e.msg.theme && <button className="hv-theme-tag" onClick={() => setTheme(e.msg!.theme!)}>{e.msg.theme}</button>}<span className="hv-tone">{TONE_LABEL[e.msg.tone!]} ({e.msg.tone! > 0 ? '+' : ''}{e.msg.tone}){e.msg.confidence === 'Low' ? ' · low confidence' : ''}</span>{e.msg.sourceId && <SourceLink id={e.msg.sourceId} onOpen={props.showEvidence} />}</footer></div></li>
              : <li key={i} className={`hv-rec-ours ${BAD_KINDS.has(e.kind) ? 'slip' : e.kind === 'promised' ? 'neutral' : 'fix'}`}><span className="hv-rec-mark" aria-hidden="true">{BAD_KINDS.has(e.kind) ? '▼' : e.kind === 'promised' ? '•' : '▲'}</span><div><p><b>{EVENT_LABEL[e.kind]}</b> · {e.text}</p><footer><span>Our side · {dateLabel(e.date)}</span></footer></div></li>)}</ul>
          </div>; }) : <p className="rb-empty">Nothing to show for this filter.</p>}
        </section>
      </div>

      <aside className="hv-cv-rail">
        <section className="hv-next"><p className="small-label">NEXT MOVE · PICKED BY RULE</p><p>{move.text}</p><p className="h3-why-line">{move.why}</p><div className="drawer-inline"><button className="button button-small button-primary" onClick={addStep}><Plus size={13} />Add as action</button><button className="button button-small button-outline" onClick={() => props.notify(`Preview: a Slack DM to ${owner || 'the owner'} would be drafted for review first.`)}><Send size={13} />Notify {owner || 'owner'}</button></div></section>
        {themes.length > 0 && <section className="hv-rail-block hv-cv-themes"><p className="small-label">WHAT THEY TALK ABOUT · 8 WEEKS</p><p className="hv-rail-hint">Scored messages by topic, coloured by tone. Click a topic to filter the record.</p>
          <ul>{themes.map(({ t, rs }) => <li key={t}><button className={theme === t ? 'selected' : ''} aria-pressed={theme === t} onClick={() => { setTheme(theme === t ? null : t); setShow('all'); }}>
            <span className="hv-ct-name">{t}<em>{rs.length}× · {rs.filter(x => x.tone! < 0).length} negative</em></span>
            <span className="hv-ct-bar">{[...rs].sort((a, b) => a.tone! - b.tone!).map(x => <i key={x.id} className={toneClass(x.tone!)} title={`${TONE_LABEL[x.tone!]} · ${shortDate(x.at)}`} />)}</span>
          </button></li>)}</ul>
        </section>}
        <section className="hv-rail-block h3-data"><p className="small-label"><Database size={11} /> WHAT THIS IS BASED ON · 28 DAYS</p>
          <dl><dt>Client messages read</dt><dd>{cov.messages}</dd><dt>Scored for tone</dt><dd>{cov.scored}</dd><dt>Low confidence, left out</dt><dd>{cov.low}</dd><dt>Routine (no tone)</dt><dd>{cov.routine}</dd><dt>Threads started</dt><dd>{cov.threads}</dd><dt>Promises in scope</dt><dd>{cov.commitments}</dd></dl>
          <p className="hv-coverage">Channels: {cov.channels.join(', ') || 'none'} · computed {dateLabel(AS_OF)}, 06:00 ET</p>
        </section>
      </aside>
    </div>
  </div>;
}

// ---- 3. Patterns ------------------------------------------------------------------------------------------
const STACK: ZoneV3[] = ['Rescue', 'Fix our side', 'Reach out', 'Steady', 'Not enough to read', 'Settling in'];

function PatternsTab({ books, open }: { books: Book[]; open: (id: string) => void }) {
  const [theme, setTheme] = useState<Theme | null>(null);
  const cur = books[7];
  const max = Math.max(...books.map(b => b.snaps.length));
  const themes = themeTrend();
  const owners = [...new Set(cur.snaps.map(s => ownerOf(s.clientId)).filter(Boolean))].map(o => {
    const ss = cur.snaps.filter(s => ownerOf(s.clientId) === o); const kept = ss.reduce((n, s) => n + s.onTime.kept, 0), due = ss.reduce((n, s) => n + s.onTime.due, 0);
    const replies = ss.flatMap(s => s.replyHours).sort((a, b) => a - b);
    return { o, n: ss.length, move: ss.filter(s => isPlaced(s) && s.zone !== 'Steady').length, waiting: ss.reduce((n, s) => n + s.waiting.filter(w => w.days >= 1).length, 0), late: ss.reduce((n, s) => n + s.overdue.length, 0), onTime: pct(kept, due), kept, due, reply: replies.length ? replies[Math.floor((replies.length - 1) / 2)] : null };
  }).sort((a, b) => b.move - a.move || b.late - a.late);
  const rows: { id: MetricId; label: string; get: (b: Book) => string; bad: (b: Book) => boolean }[] = [
    { id: 'needMove', label: 'Clients needing a move', get: b => `${b.needMove}`, bad: b => b.needMove > 0 },
    { id: 'waiting', label: 'Waiting 1+ business day', get: b => `${b.waiting}`, bad: b => b.waiting > 0 },
    { id: 'reply', label: 'Median first reply', get: b => fmtHours(b.replyMedian), bad: b => (b.replyMedian ?? 0) > CONFIG.replyTargetHours },
    { id: 'onTime', label: 'Promises kept on time', get: b => b.due ? `${pct(b.kept, b.due)}%` : '—', bad: b => !!b.due && pct(b.kept, b.due)! < CONFIG.onTimeTarget * 100 },
    { id: 'overdue', label: 'Promises late', get: b => `${b.overdue}`, bad: b => b.overdue > 0 },
    { id: 'coverage', label: 'Readable tone', get: b => `${pct(b.readable, b.active)}%`, bad: b => pct(b.readable, b.active)! < 80 },
  ];
  return <>
    <section className="hv-pattern" aria-label="Book over time">
      <header className="hv-pattern-head"><h2>The book, week by week</h2><p>Every column is the full computation re-run at that week’s end. Red and amber should shrink; team numbers should hold their targets.</p></header>
      <div className="hv-pattern-grid">
        <section className="hv-card"><header><h2>Clients per zone</h2></header>
          <div className="hv-stack" role="img" aria-label="Clients in each zone at each week end">{books.map((b, i) => <div key={b.asOf} className="hv-stack-col"><div className="hv-stack-bar">{STACK.map(z => { const n = b.snaps.filter(s => s.zone === z).length; return n ? <span key={z} className={`seg ${zoneClass(z)} ${z === 'Settling in' ? 'is-settling' : ''} ${z === 'Not enough to read' ? 'is-none' : ''}`} style={{ height: `${n / max * 100}%` }} title={`${z}: ${n}`}>{n}</span> : null; })}</div><small>{dateLabel(WEEK_ENDS[i])}</small></div>)}</div>
          <div className="hv-legend">{STACK.map(z => <span key={z}><i className={`${zoneClass(z)} ${z === 'Settling in' ? 'is-settling' : ''} ${z === 'Not enough to read' ? 'is-none' : ''}`} />{z}</span>)}</div>
        </section>
        <section className="hv-card"><header><h2>Team numbers</h2><p>Same metrics as the cards on This week, at each week’s end.</p></header>
          <div className="h3-table-scroll"><table className="h3-table h3-trend"><thead><tr><th>Metric</th>{WEEK_ENDS.map(w => <th key={w}>{dateLabel(w)}</th>)}</tr></thead>
            <tbody>{rows.map(r => <tr key={r.id} className="no-click"><td>{r.label} <MetricInfo id={r.id} /></td>{books.map(b => <td key={b.asOf} className={r.bad(b) ? 'is-warn' : ''}>{r.get(b)}</td>)}</tr>)}</tbody></table></div>
        </section>
      </div>
    </section>

    <section className="hv-pattern" aria-label="Concerns by topic">
      <header className="hv-pattern-head"><h2>Concerns by topic</h2><p>Negative, high-confidence client messages per fixed topic: last 28 days vs the 28 before. A topic rising across several clients is a process problem, not a client problem.</p></header>
      <div className="hv-theme-grid">{themes.map(t => { const d = t.now.length - t.before; return <button key={t.theme} className={`hv-theme ${theme === t.theme ? 'selected' : ''} ${t.now.length ? 'has-concern' : ''}`} aria-pressed={theme === t.theme} disabled={!t.now.length} onClick={() => setTheme(theme === t.theme ? null : t.theme)}><span>{t.theme}</span><strong>{t.now.length}</strong><small>{d > 0 ? `▲ ${d} vs prior 28 days` : d < 0 ? `▼ ${-d} vs prior 28 days` : 'same as prior 28 days'} · {plural(t.clients, 'client')}</small></button>; })}</div>
      {theme && <section className="hv-card hv-theme-quotes"><header className="hv-list-head"><div><h2>{theme}</h2><p>The negative messages behind this count.</p></div><button className="text-button" onClick={() => setTheme(null)}>Close</button></header>
        <ul className="hv-feed">{themes.find(t => t.theme === theme)!.now.map(x => <li key={x.id} className={toneClass(x.tone!)}><span className="hv-tone-dot" aria-hidden="true" /><div><p>“{x.quote}”</p><footer><button className="hv-ctag" onClick={() => open(x.clientId)}><Avatar client={clientById(x.clientId)} small />{clientById(x.clientId).name}</button><span>{x.speaker} · {shortDate(x.at)}</span><span className="hv-tone">{TONE_LABEL[x.tone!]}</span></footer></div></li>)}</ul>
      </section>}
    </section>

    <section className="hv-pattern" aria-label="By owner">
      <header className="hv-pattern-head"><h2>By owner</h2><p>When one person’s clients slip together, look at workload before the clients.</p></header>
      <div className="hv-card h3-table-wrap"><table className="h3-table"><thead><tr><th>Owner</th><th>Clients</th><th>Need a move</th><th>Waiting 1+ bd</th><th>Promises late</th><th>Kept on time</th><th>Median first reply</th></tr></thead>
        <tbody>{owners.map(o => <tr key={o.o} className="no-click"><td><span className="hv-client"><span className="person-avatar">{o.o[0]}</span><strong>{o.o}</strong></span></td><td>{o.n}</td><td className={o.move ? 'is-bad' : ''}>{o.move}</td><td className={o.waiting ? 'is-bad' : ''}>{o.waiting}</td><td className={o.late ? 'is-bad' : ''}>{o.late}</td><td className={o.onTime !== null && o.onTime < CONFIG.onTimeTarget * 100 ? 'is-warn' : ''}>{o.onTime === null ? '—' : `${o.onTime}%`} <small>{o.kept}/{o.due}</small></td><td className={o.reply !== null && o.reply > CONFIG.replyTargetHours ? 'is-warn' : ''}>{fmtHours(o.reply)}</td></tr>)}</tbody></table></div>
    </section>
  </>;
}

// ---- 4. How it's measured ---------------------------------------------------------------------------------
function MeasuredTab() {
  const steps = [
    { t: 'Ingest', d: 'Gmail, Slack, Fathom and Zoom messages; ClickUp commitments; support threads. Each record keeps its source link.' },
    { t: 'Score', d: 'The LLM scores each client-authored message: tone −2…+2, one of six fixed topics, and confidence. Staff and Viktor text is never scored. Routine logistics get no tone.' },
    { t: 'Compute', d: 'Every night at 06:00 ET the rules below run over the records. No number is typed in by hand.' },
    { t: 'Snapshot', d: 'Each night’s results are stored, so last week’s map and every trend are re-readable and auditable.' },
  ];
  const cfg: [string, string][] = [
    ['Rolling window', `${CONFIG.windowDays} days`], ['Recency half-life', `${CONFIG.halfLifeDays} days`], ['Minimum to read tone', `${CONFIG.minScored} scored messages`],
    ['Reply target', `${CONFIG.replyTargetHours} business hours`], ['Waiting: At risk / Behind / Broken', `${CONFIG.waitAtRisk} / ${CONFIG.waitBehind} / ${CONFIG.waitBroken}+ business days`],
    ['Late promise is Broken after', `${CONFIG.lateBrokenDays} business days`], ['Due soon', `within ${CONFIG.dueSoonDays} business days`], ['Support target', `${CONFIG.issueSlaDays} business days`],
    ['Repeat issue window', `${CONFIG.repeatWindowDays} days`], ['Quieter than usual', `under ${CONFIG.quietRatio * 100}% of usual`], ['Settling in', `first ${CONFIG.settlingDays} days`], ['On-time target', `${CONFIG.onTimeTarget * 100}%`],
  ];
  return <>
    <section className="hv-pattern"><header className="hv-pattern-head"><h2>From records to numbers</h2><p>The same pipeline produces every figure on this page.</p></header>
      <ol className="h3-pipeline">{steps.map((s, i) => <li key={s.t}><span>{i + 1}</span><b>{s.t}</b><p>{s.d}</p></li>)}</ol>
    </section>
    <section className="hv-pattern"><header className="hv-pattern-head"><h2>Metrics</h2><p>What each number answers, and exactly how it is computed.</p></header>
      <div className="hv-card h3-table-wrap"><table className="h3-table h3-defs"><thead><tr><th>Metric</th><th>Answers</th><th>How it’s computed</th><th>Source</th><th>Window</th><th>Target</th></tr></thead>
        <tbody>{(Object.keys(METRICS) as MetricId[]).map(k => { const d = METRICS[k]; return <tr key={k} className="no-click"><td><strong>{d.label}</strong></td><td>{d.question}</td><td>{d.formula}</td><td>{d.source}</td><td>{d.window}</td><td>{d.target || '—'}</td></tr>; })}</tbody></table></div>
    </section>
    <section className="hv-pattern"><header className="hv-pattern-head"><h2>Zones</h2><p>Two readings, never blended into one score. The zone is where they meet and says whose move it is.</p></header>
      <div className="h3-rules">
        <div className="hv-card"><h3>How they sound: tone score</h3><ul><li><b>Delighted</b> · +1 or more</li><li><b>Satisfied</b> · 0 to +1</li><li><b>Uneasy</b> · −1 to 0</li><li><b>Frustrated</b> · below −1</li><li><b>Not enough to read</b> · fewer than {CONFIG.minScored} scored messages</li></ul></div>
        <div className="hv-card"><h3>How we’re doing: the highest rule that fires</h3><ul>
          <li><b>Broken</b> · a promise more than {CONFIG.lateBrokenDays} business days late, a client waiting {CONFIG.waitBroken}+ business days, an issue reported again within {CONFIG.repeatWindowDays} days, or {CONFIG.overdueBrokenCount}+ promises late</li>
          <li><b>Behind</b> · any promise past due, a client waiting {CONFIG.waitBehind}–{CONFIG.waitBroken - 1} business days, or an issue open past {CONFIG.issueSlaDays} business days</li>
          <li><b>At risk</b> · a promise due within {CONFIG.dueSoonDays} business days, a client waiting {CONFIG.waitAtRisk} business day, or an issue open</li>
          <li><b>On track</b> · none of the above</li></ul></div>
        <div className="hv-card h3-matrix"><h3>Zone</h3><table><thead><tr><th /><th>On track / At risk</th><th>Behind / Broken</th></tr></thead><tbody><tr><th>Satisfied / Delighted</th><td className="z-steady">Steady</td><td className="z-fix-our-side">Fix our side</td></tr><tr><th>Uneasy / Frustrated</th><td className="z-reach-out">Reach out</td><td className="z-rescue">Rescue</td></tr></tbody></table></div>
      </div>
    </section>
    <section className="hv-pattern"><header className="hv-pattern-head"><h2>Thresholds</h2><p>Proposed values. All live in one config, so WIA can change one and every figure updates consistently.</p></header>
      <div className="h3-config">{cfg.map(([k, v]) => <div key={k}><span>{k}</span><b>{v}</b><em>Proposed · WIA to confirm</em></div>)}</div>
    </section>
  </>;
}

// ---- Monday review ------------------------------------------------------------------------------------------
function MondayDialog({ cur, prev, close, notify }: { cur: Book; prev: Book; close: () => void; notify: (m: string) => void }) {
  const agenda = cur.snaps.filter(s => s.zone !== 'Steady' && s.zone !== 'Settling in').sort((a, b) => severity(b.zone) - severity(a.zone) || b.delivery - a.delivery);
  const ot = pct(cur.kept, cur.due);
  return <Dialog title="Monday review" subtitle={`Computed ${dateLabel(AS_OF)}`} className="hv-monday" onClose={close}>
    <p className="hint">Team numbers: {cur.needMove} {cur.needMove === 1 ? 'client needs' : 'clients need'} a move (last week {prev.needMove}) · {cur.waiting} waiting on a reply · {ot ?? '—'}% of promises kept on time · median first reply {fmtHours(cur.replyMedian)}.</p>
    <ol className="hv-agenda">{agenda.map(s => <li key={s.clientId} className={zoneClass(s.zone)}>
      <div className="hv-agenda-top"><strong>{clientById(s.clientId).name}</strong><span className="hv-zone-pill">{s.zone}</span><small>{ownerOf(s.clientId)} · tone {fmtScore(s.score)} · {DELIVERY_LABEL[s.delivery]}</small></div>
      {s.triggers[0] && <p>{s.triggers[0].text}.</p>}<p className="hv-agenda-step">→ {nextMove(s).text}</p>
    </li>)}</ol>
    <div className="slack-footer"><span className="hint">Posts to #wia-monday. Preview only: nothing is sent.</span><button className="button button-primary" onClick={() => { close(); notify('Preview: the Monday review was posted after review. Nothing was sent.'); }}><Send size={14} />Post to Slack</button></div>
  </Dialog>;
}

// ---- Page ---------------------------------------------------------------------------------------------------
type TabId = 'week' | 'clients' | 'patterns' | 'measured';
const TABS: { id: TabId; label: string; question: string }[] = [
  { id: 'week', label: 'This week', question: 'Who needs us now, and whose move is it?' },
  { id: 'clients', label: 'Clients', question: 'How is each client, and what is that based on?' },
  { id: 'patterns', label: 'Patterns', question: 'Are we getting better as a team, and what keeps coming up?' },
  { id: 'measured', label: 'How it’s measured', question: 'Where every number comes from.' },
];

export default function HealthV3(props: Props) {
  const [tab, setTab] = useState<TabId>('week');
  const [openId, setOpenId] = useState<string | null>(null);
  const [mondayOpen, setMondayOpen] = useState(false);
  const ids = useMemo(() => ACTIVE_IDS.filter(id => CLIENTS.some(c => c.id === id)), []);
  const books = useMemo(() => WEEK_ENDS.map(w => book(w, ids)), [ids]);
  const cur = books[7], prev = books[6];
  const open = (id: string) => { setOpenId(id); setTab('clients'); window.scrollTo({ top: 0, behavior: 'smooth' }); };
  const pick = (t: TabId) => { setTab(t); if (t !== 'clients') setOpenId(null); };
  const moved = cur.snaps.filter(s => s.zone !== prev.snaps.find(b => b.clientId === s.clientId)?.zone).length;
  const neg = themeTrend().reduce((n, t) => n + t.now.length, 0);
  const badge: Record<TabId, { text: string; hot?: boolean }> = { week: { text: `${moved} moved`, hot: moved > 0 }, clients: { text: `${cur.needMove} need a move`, hot: cur.needMove > 0 }, patterns: { text: `${neg} concerns · 28d` }, measured: { text: `${Object.keys(METRICS).length} metrics` } };
  const current = TABS.find(t => t.id === tab)!;
  const lastWeekDays = businessDays(addDays(AS_OF, -7), AS_OF);

  return <div className="view hv-view h3-view">
    <header className="hv-head">
      <div><p className="rb-eyebrow">Client intelligence · v3</p><h1>Health &amp; Sentiment</h1><p className="hv-lede">How each client sounds, how we’re doing for them, and whose move it is. Every number is computed and explains itself.</p></div>
      <div className="hv-head-tools"><span className="hv-asof"><Database size={12} />Computed {dateLabel(AS_OF)}, 06:00 ET · compared with {dateLabel(LAST_WEEK)} ({lastWeekDays} business days)</span><button className="button button-small button-primary" onClick={() => setMondayOpen(true)}><CalendarCheck size={13} />Prepare Monday review</button></div>
    </header>

    <div className="hv-tabs" role="tablist" aria-label="Health views">
      {TABS.map(t => <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? 'selected' : ''} onClick={() => pick(t.id)}>{t.label}<span className={badge[t.id].hot ? 'is-hot' : ''}>{badge[t.id].text}</span></button>)}
    </div>
    {!(tab === 'clients' && openId) && <p className="hv-question">{current.question}</p>}

    {tab === 'week' && <WeekTab cur={cur} prev={prev} viewer={props.viewer} open={open} goActions={() => props.navigate('actions-v3')} notify={props.notify} />}
    {tab === 'clients' && <ClientsTab cur={cur} props={props} openId={openId} setOpenId={setOpenId} />}
    {tab === 'patterns' && <PatternsTab books={books} open={open} />}
    {tab === 'measured' && <MeasuredTab />}

    {mondayOpen && <MondayDialog cur={cur} prev={prev} close={() => setMondayOpen(false)} notify={props.notify} />}
  </div>;
}
