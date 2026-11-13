import { useMemo, useState } from 'react';
import { ArrowDownRight, ArrowLeft, ArrowRight, ArrowUpRight, CalendarCheck, Clock3, Flag, MessageSquareReply, Minus, Plus, Send, ShieldAlert, Sparkles, TrendingDown, TrendingUp, Wrench } from 'lucide-react';
import { CLIENTS, DEMO_DATE, addDays, clientById, dateLabel, daysBetween, isOutstanding, isOverdue } from '../data';
import { RECORDS } from '../records';
import { WAITING, assessmentFor } from '../health';
import { DELIVERY, DELIVERY_RULES, FEEL, FEEL_RULES, MOODS, PULSE, feelTone, THEMES, WEEKS, ZONES, pulseFor, toneKind, zoneOf, zoneRank, type Feel, type OurEvent, type Pulse, type Theme, type Tone, type ToneReading, type Zone } from '../health-v2';
import { ThemedSelect } from '../components/ThemedSelect';
import { awaitingAck, isAdmin } from './Actions';
import { Avatar, Dialog, SourceLink } from '../components/UI';
import type { Action, WorkspaceProps } from '../types';
import './HealthRevised.css';
import { me } from '../auth';

/*
 * Revised Health & Sentiment: one page answering "whose move is it?".
 * Two measures stay separate: how the client feels (LLM reading of their own words) and how WIA is
 * doing (facts from code). Where they meet gives the zone; last week's position gives the movement.
 */

const now = (p: Pulse) => ({ mood: p.mood[7], delivery: p.delivery[7], zone: p.settling ? null : zoneOf(p.mood[7], p.delivery[7]) });
const before = (p: Pulse) => ({ mood: p.mood[6], delivery: p.delivery[6], zone: p.settling ? null : zoneOf(p.mood[6], p.delivery[6]) });
const moodDelta = (p: Pulse) => (p.mood[7] ?? 0) - (p.mood[6] ?? p.mood[7] ?? 0);
const zoneClass = (z: Zone | null) => z ? `z-${z.toLowerCase().replace(/\s+/g, '-')}` : 'z-none';
const slid = (p: Pulse) => !p.settling && zoneRank(now(p).zone) > zoneRank(before(p).zone);
const recovered = (p: Pulse) => !p.settling && zoneRank(now(p).zone) < zoneRank(before(p).zone);
const waitingFor = (id: string) => WAITING.filter(w => w.clientId === id);

type Chip = 'slid' | 'recovered' | 'waiting' | 'rescue';
const CHIPS: { id: Chip; label: (n: number) => string; icon: typeof TrendingDown; test: (p: Pulse) => boolean }[] = [
  { id: 'slid', label: n => `${n} slid this week`, icon: TrendingDown, test: slid },
  { id: 'recovered', label: n => `${n} recovered`, icon: TrendingUp, test: recovered },
  { id: 'waiting', label: n => `${n} waiting on our reply`, icon: MessageSquareReply, test: p => waitingFor(p.clientId).length > 0 },
  { id: 'rescue', label: n => `${n} in rescue`, icon: ShieldAlert, test: p => now(p).zone === 'Rescue' },
];

// ---- Relationship map ------------------------------------------------------
// An even 4 x 4 grid. Each axis splits in the middle: positive vs negative tone, nothing late vs something late.
const W = 680, H = 430, PAD = { l: 96, r: 16, t: 28, b: 62 };
const PW = W - PAD.l - PAD.r, PH = H - PAD.t - PAD.b;
const xOf = (d: number) => PAD.l + (d + 0.5) / 4 * PW;
const yOf = (f: number) => PAD.t + (3 - f + 0.5) / 4 * PH;
const X_SPLIT = PAD.l + PW / 2, Y_SPLIT = PAD.t + PH / 2, GAP = 4;

function RelationshipMap({ pulses, focus, open }: { pulses: Pulse[]; focus: Set<string> | null; open: (id: string) => void }) {
  // Clients sharing a cell fan out sideways so every dot stays clickable.
  const offsets = new Map<string, number>();
  const seen = new Map<string, number>();
  pulses.forEach(p => { const k = `${now(p).delivery}-${now(p).mood}`; const n = seen.get(k) || 0; offsets.set(p.clientId, n); seen.set(k, n + 1); });
  const quad = (x: number, y: number, z: Zone, label: string, anchor: 'start' | 'end', top: boolean) => <g className={`map-quad ${zoneClass(z)}`}>
    <rect x={x} y={y} width={PW / 2 - GAP} height={PH / 2 - GAP} rx="12" />
    <text x={anchor === 'start' ? x + 14 : x + PW / 2 - GAP - 14} y={top ? y + 20 : y + PH / 2 - GAP - 12} textAnchor={anchor} className="map-quad-label">{label}</text>
  </g>;
  return <svg className="hv-map" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Relationship map: how each client feels against how WIA is doing, with last week's position">
    <defs><marker id="hv-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 8 4 0 8z" className="map-arrow" /></marker></defs>
    {quad(PAD.l, PAD.t, 'Steady', 'STEADY', 'start', true)}
    {quad(X_SPLIT + GAP, PAD.t, 'Fix our side', 'FIX OUR SIDE', 'end', true)}
    {quad(PAD.l, Y_SPLIT + GAP, 'Reach out', 'REACH OUT', 'start', false)}
    {quad(X_SPLIT + GAP, Y_SPLIT + GAP, 'Rescue', 'RESCUE', 'end', false)}
    {/* Step lines inside each half: mild steps near the centre, strong ones at the edges. */}
    {[1, 3].map(i => <line key={`v${i}`} x1={PAD.l + i / 4 * PW} x2={PAD.l + i / 4 * PW} y1={PAD.t + 6} y2={PAD.t + PH - 6} className="map-step" />)}
    {[1, 3].map(i => <line key={`h${i}`} y1={PAD.t + i / 4 * PH} y2={PAD.t + i / 4 * PH} x1={PAD.l + 6} x2={PAD.l + PW - 6} className="map-step" />)}
    {FEEL.map((f, i) => <text key={f} x={PAD.l - 10} y={yOf(i) + 3} textAnchor="end" className="map-axis"><title>{`${f}: ${FEEL_RULES[i]}`}</title>{f}</text>)}
    {DELIVERY.map((d, i) => <text key={d} x={xOf(i)} y={PAD.t + PH + 18} textAnchor="middle" className="map-axis"><title>{`${d}: ${DELIVERY_RULES[i]}`}</title>{d}</text>)}
    <text x={14} y={(PAD.t + Y_SPLIT) / 2} className="map-half" transform={`rotate(-90 14 ${(PAD.t + Y_SPLIT) / 2})`} textAnchor="middle">POSITIVE</text>
    <text x={14} y={(Y_SPLIT + PAD.t + PH) / 2} className="map-half" transform={`rotate(-90 14 ${(Y_SPLIT + PAD.t + PH) / 2})`} textAnchor="middle">NEGATIVE</text>
    <text x={(PAD.l + X_SPLIT) / 2} y={PAD.t + PH + 38} textAnchor="middle" className="map-half">NOTHING LATE YET</text>
    <text x={(X_SPLIT + PAD.l + PW) / 2} y={PAD.t + PH + 38} textAnchor="middle" className="map-half">SOMETHING LATE</text>
    <text x={PAD.l} y={PAD.t - 10} className="map-axis-title">↑ HOW THEY FEEL</text>
    <text x={W - PAD.r} y={H - 4} textAnchor="end" className="map-axis-title">HOW WE’RE DOING →</text>
    {pulses.map(p => {
      const n = now(p), b = before(p); if (n.mood === null) return null;
      const k = offsets.get(p.clientId)!;
      const o = (k % 2 ? -1 : 1) * Math.ceil(k / 2) * 40;
      const x = xOf(n.delivery) + o, y = yOf(n.mood);
      const bx = b.mood === null ? x : xOf(b.delivery) + o, by = b.mood === null ? y : yOf(b.mood);
      const moved = Math.hypot(x - bx, y - by) > 4;
      const dim = focus && !focus.has(p.clientId);
      const c = clientById(p.clientId);
      return <g key={p.clientId} className={`map-client ${zoneClass(n.zone)} ${dim ? 'is-dim' : ''}`} role="button" tabIndex={0} aria-label={`${c.name}: ${FEEL[n.mood]}, ${DELIVERY[n.delivery]}. ${n.zone}. Open details`} onClick={() => open(p.clientId)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(p.clientId); } }}>
        {moved && <><circle cx={bx} cy={by} r="6" className="map-ghost" /><line x1={bx} y1={by} x2={x - (x - bx) * 0.2} y2={y - (y - by) * 0.2} className="map-trail" markerEnd="url(#hv-arrow)" /></>}
        <circle cx={x} cy={y} r="15" className="map-dot" />
        <text x={x} y={y + 3.5} textAnchor="middle" className="map-initials">{c.initials}</text>
        <text x={x} y={y + 31} textAnchor="middle" className="map-name">{c.name}</text>
      </g>;
    })}
  </svg>;
}

// ---- Small pieces -------------------------------------------------------------
function Sparkline({ values }: { values: (Feel | null)[] }) {
  const w = 120, h = 30, step = w / (values.length - 1);
  const yv = (v: number) => h - 4 - v / 3 * (h - 8);
  const pts = values.map((v, i) => v === null ? null : [i * step, yv(v)] as const);
  const path = pts.reduce((d, pt, i) => pt ? `${d}${d && pts[i - 1] ? ' L' : ' M'}${pt[0].toFixed(1)} ${pt[1].toFixed(1)}` : d, '');
  const last = pts[pts.length - 1];
  return <svg className="hv-spark" viewBox={`-3 0 ${w + 6} ${h}`} aria-hidden="true"><line x1="0" x2={w} y1={yv(1.5)} y2={yv(1.5)} className="spark-mid" /><path d={path} />{last && <circle cx={last[0]} cy={last[1]} r="3" />}</svg>;
}

function MoodChange({ p }: { p: Pulse }) {
  const d = moodDelta(p); const m = p.mood[7];
  if (m === null) return <span className="hv-mood muted">Not enough to read</span>;
  return <span className={`hv-mood tone-${feelTone(m)}`} title={FEEL_RULES[m]}>{FEEL[m]}{d < 0 ? <ArrowDownRight size={13} className="down" aria-label="down" /> : d > 0 ? <ArrowUpRight size={13} className="up" aria-label="up" /> : <Minus size={12} className="flat" aria-label="no change" />}</span>;
}

// ---- Client record: one chart for both sides -------------------------------------
// Tone line and message dots on top; under the week labels, the zone each week sat in and what happened on our side.
const TL = { w: 620, h: 236, l: 70, r: 14, t: 12, b: 64 };
const start = new Date(`${WEEKS[0]}T12:00:00Z`).getTime() - 6 * 86400000, end = new Date(`${WEEKS[7]}T12:00:00Z`).getTime();
const tx = (date: string) => TL.l + (new Date(`${date}T12:00:00Z`).getTime() - start) / (end - start) * (TL.w - TL.l - TL.r);
const ty = (tone: number) => TL.t + (4 - tone) / 4 * (TL.h - TL.t - TL.b);

function Timeline({ p, picked, pick }: { p: Pulse; picked?: ToneReading; pick: (r: ToneReading) => void }) {
  const line = p.mood.map((m, i) => m === null ? null : [tx(WEEKS[i]), ty(feelTone(m))] as const);
  const path = line.reduce((d, pt, i) => pt ? `${d}${d && line[i - 1] ? ' L' : ' M'}${pt[0].toFixed(1)} ${pt[1].toFixed(1)}` : d, '');
  const base = TL.h - TL.b;
  return <svg className="hv-timeline" viewBox={`0 0 ${TL.w} ${TL.h}`} role="img" aria-label="Eight weeks: how the client sounded, the zone each week, and what happened on our side">
    {MOODS.map((m, i) => <g key={m}><line x1={TL.l} x2={TL.w - TL.r} y1={ty(i)} y2={ty(i)} className="tl-grid" /><text x={TL.l - 8} y={ty(i) + 3} textAnchor="end" className="tl-axis">{m}</text></g>)}
    {WEEKS.map(w => <text key={w} x={tx(w)} y={base + 14} textAnchor="middle" className="tl-axis">{dateLabel(w)}</text>)}
    <text x={TL.l - 8} y={base + 30} textAnchor="end" className="tl-axis">Zone</text>
    {WEEKS.map((w, i) => { const z = weekZone(p, i); const x0 = i ? tx(WEEKS[i - 1]) : TL.l; return <rect key={w} x={x0 + 1.5} y={base + 23} width={tx(w) - x0 - 3} height={9} rx="3" className={`tl-zone ${cellClass(z)}`}><title>{`Week of ${dateLabel(w)}: ${z}`}</title></rect>; })}
    <path d={path} className="tl-line" />
    {line.map((pt, i) => pt && <circle key={i} cx={pt[0]} cy={pt[1]} r="3" className="tl-week" />)}
    {p.readings.map((r, i) => <circle key={i} cx={tx(r.date)} cy={ty(r.tone) + (i % 2 ? 4 : -4)} r={r === picked ? 7 : 5.5} className={`tl-read tone-${r.tone} ${r.confidence === 'Low' ? 'is-low' : ''} ${r === picked ? 'is-picked' : ''}`} role="button" tabIndex={0} aria-label={`${dateLabel(r.date)}, ${MOODS[r.tone]}: ${r.quote}`} onClick={() => pick(r)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(r); } }}><title>{`${MOODS[r.tone]} · ${r.speaker}, ${dateLabel(r.date)}`}</title></circle>)}
    <text x={TL.l - 8} y={TL.h - 9} textAnchor="end" className="tl-axis">Our side</text>
    {p.ourSide.map((e, i) => { const x = tx(e.date), y = TL.h - 12; return <g key={i} className={`tl-event ${e.kind}`}><path d={e.kind === 'slip' ? `M${x - 5} ${y - 4} L${x + 5} ${y - 4} L${x} ${y + 4} Z` : `M${x - 5} ${y + 4} L${x + 5} ${y + 4} L${x} ${y - 4} Z`} /><title>{`Our side · ${dateLabel(e.date)}: ${e.text}`}</title></g>; })}
  </svg>;
}

// ---- Shared helpers ------------------------------------------------------------------
type Props = WorkspaceProps & { addAction: (a: Action) => void };
const ownerOf = (id: string) => RECORDS[id]?.owner || '';
const MONTH_AGO = addDays(DEMO_DATE, -30);
const allReadings = () => PULSE.flatMap(p => p.readings.map(r => ({ ...r, clientId: p.clientId }))).sort((a, b) => b.date.localeCompare(a.date));
const latestReading = (p: Pulse) => [...p.readings].sort((x, y) => y.date.localeCompare(x.date))[0];
const lastHeard = (p: Pulse) => p.readings.length ? `last heard ${daysBetween(latestReading(p).date)}d ago` : 'no readings yet';
const isLeadLock = (id: string) => { const a = assessmentFor(id); return !!a.leadNumbers || a.dims.leads.level === 'unavailable'; };
const slippingPromises = (actions: Action[]) => actions.filter(a => a.side === 'WIA' && isOutstanding(a) && (isOverdue(a) || awaitingAck(a))).sort((a, b) => (a.due || '9999').localeCompare(b.due || '9999'));
const openSupport = (id: string) => (RECORDS[id]?.support || []).filter(s => s.state !== 'Resolved').sort((a, b) => (b.repeats || 0) - (a.repeats || 0));
const ZONE_ORDER: (Zone | 'Settling in' | 'Not enough')[] = ['Rescue', 'Fix our side', 'Reach out', 'Steady', 'Settling in', 'Not enough'];
const weekZone = (p: Pulse, i: number) => p.settling ? (p.mood[i] === null ? 'Not enough' : 'Settling in') : zoneOf(p.mood[i], p.delivery[i]) || 'Not enough';
const cellClass = (z: string) => `${zoneClass(z as Zone)} ${z === 'Settling in' ? 'is-settling' : ''} ${z === 'Not enough' ? 'is-none' : ''}`;

function ClientTag({ id, open }: { id: string; open: (id: string) => void }) {
  const c = clientById(id);
  return <button className="hv-ctag" onClick={e => { e.stopPropagation(); open(id); }}><Avatar client={c} small />{c.name}</button>;
}

/** Funnel and lead handling for one LeadLock client. Kept separate from how they feel. */
function LeadBlock({ id }: { id: string }) {
  const a = assessmentFor(id);
  if (!a.leadNumbers) return <div className="hv-pending"><strong>Access pending</strong><p>{a.dims.leads.drivers[0]?.text}</p></div>;
  const L = a.leadNumbers;
  return <>
    <div className="hv-funnel">{([['Inquiries', L.inquiries], ['Tours', L.tours], ['Booked', L.booked]] as [string, [number, number]][]).map(([l, [cur, prev]], i, arr) => <div key={l} className="hv-funnel-step"><span>{l}</span><strong>{cur}</strong><small className={cur >= prev ? 'up' : 'down'}>{cur >= prev ? '▲' : '▼'} from {prev}</small>{i < arr.length - 1 && <em className="hv-rate">{Math.round(arr[i + 1][1][0] / cur * 100)}% →</em>}</div>)}</div>
    <div className="hv-handling"><div><span>Median first reply</span><strong>{L.firstResponse}</strong></div><div className={L.uncontacted ? 'is-hot' : ''}><span>Uncontacted 48 h+</span><strong>{L.uncontacted}</strong></div><div className={L.stalled ? 'is-hot' : ''}><span>Stalled 14 days+</span><strong>{L.stalled}</strong></div></div>
    <details className="hv-defs"><summary>Definitions used</summary><ul>{L.definitions.map(d => <li key={d}>{d}</li>)}</ul></details>
  </>;
}

// ---- 1. This week ----------------------------------------------------------------------
function WeekTab({ pulses, actions, viewer, open, notify, goActions }: { pulses: Pulse[]; actions: Action[]; viewer: string; open: (id: string) => void; notify: (m: string) => void; goActions: () => void }) {
  const [chip, setChip] = useState<Chip | null>(null);
  const [mine, setMine] = useState(!isAdmin(viewer));
  const chipDef = CHIPS.find(c => c.id === chip);
  const focus = chipDef ? new Set(pulses.filter(chipDef.test).map(p => p.clientId)) : null;
  const rows = [...pulses].sort((a, b) => zoneRank(now(b).zone) - zoneRank(now(a).zone) || moodDelta(a) - moodDelta(b));
  const stories = rows.filter(p => p.story && !p.settling);
  const settling = pulses.filter(p => p.settling);
  const inScope = (id: string) => pulses.some(p => p.clientId === id) && (!mine || ownerOf(id) === viewer);
  const waiting = [...WAITING].filter(w => inScope(w.clientId)).sort((a, b) => b.businessDays - a.businessDays);
  const promises = slippingPromises(actions).filter(a => inScope(a.clientId));
  return <>
    <div className="hv-chips" role="group" aria-label="What changed">
      {CHIPS.map(c => { const n = pulses.filter(c.test).length; const Icon = c.icon; return <button key={c.id} className={`hv-chip chip-${c.id} ${chip === c.id ? 'selected' : ''}`} aria-pressed={chip === c.id} disabled={!n} onClick={() => setChip(chip === c.id ? null : c.id)}><Icon size={15} />{c.label(n)}</button>; })}
      {chip && <button className="text-button" onClick={() => setChip(null)}>Show everyone</button>}
    </div>
    <div className="hv-top">
      <section className="hv-card hv-map-card" aria-label="Relationship map">
        <header><h2>Relationship map</h2><p>Dots are clients now. Hover a client to see their name and where they were last week.</p></header>
        <RelationshipMap pulses={pulses.filter(p => !p.settling)} focus={focus} open={open} />
        {settling.length > 0 && <div className="hv-offmap"><span className="small-label">NOT ON THE MAP</span>{settling.map(p => <button key={p.clientId} className="hv-offmap-client" onClick={() => open(p.clientId)}><Avatar client={clientById(p.clientId)} small />{clientById(p.clientId).name}<em>Settling in</em></button>)}</div>}
      </section>
      <section className="hv-card hv-week" aria-label="This week">
        <header><h2>This week</h2><p>What moved, in the client’s words.</p></header>
        <ol>{stories.map(p => { const n = now(p), b = before(p); const c = clientById(p.clientId); const q = latestReading(p); return <li key={p.clientId} className={zoneClass(n.zone)}>
          <button className="hv-story" onClick={() => open(p.clientId)}>
            <span className="hv-story-head"><strong>{c.name}</strong><span className="hv-shift">{b.zone && b.zone !== n.zone ? <>{b.zone}<ArrowRight size={11} /></> : null}<span className="hv-zone-pill">{n.zone}</span></span></span>
            <span className="hv-story-text">{p.story}</span>
            {q && <span className="hv-story-quote">“{q.quote.length > 110 ? `${q.quote.slice(0, 108)}…` : q.quote}” <em>{q.speaker.split(' ')[0]}, {dateLabel(q.date)}</em></span>}
            <span className="hv-story-move">{ZONES.find(z => z.id === n.zone)?.move} <b>{ownerOf(p.clientId)}</b></span>
          </button>
        </li>; })}</ol>
      </section>
    </div>

    <section className="hv-card hv-owe" aria-label="What we owe today">
      <header className="hv-list-head"><div><h2>What we owe today</h2><p>The part of our side a client can feel right now: replies they’re waiting for and promises slipping.</p></div>
        <div className="rb-layout" role="group" aria-label="Whose clients"><button className={mine ? 'selected' : ''} aria-pressed={mine} onClick={() => setMine(true)}>My clients</button><button className={!mine ? 'selected' : ''} aria-pressed={!mine} onClick={() => setMine(false)}>Everyone</button></div>
      </header>
      <div className="hv-owe-grid">
        <div><h3><MessageSquareReply size={15} />Waiting on our reply<span className="hv-count">{waiting.length}</span></h3>
          {waiting.length ? <ul className="hv-issues">{waiting.map(w => <li key={w.clientId + w.date} className={w.businessDays >= 3 ? 'is-hot' : ''} style={{ ['--z' as string]: 'var(--fix)' }}><div className="hv-issue-top"><ClientTag id={w.clientId} open={open} /><span className="hv-age">{w.businessDays} business {w.businessDays === 1 ? 'day' : 'days'}</span></div><p className="hv-issue-quote">“{w.text}”</p><small>{w.from} · {w.channel} · {dateLabel(w.date)} · owner {ownerOf(w.clientId)}</small><div className="drawer-inline"><button className="button button-small button-outline" onClick={() => notify(`Preview: this opens the ${w.channel} thread to reply to ${w.from.split(' ')[0]}.`)}>Open thread</button></div></li>)}</ul> : <p className="rb-empty">Nobody is waiting on us{mine ? ' on your clients' : ''}.</p>}
        </div>
        <div><h3><Clock3 size={15} />Promises slipping<span className="hv-count">{promises.length}</span></h3>
          {promises.length ? <ul className="hv-issues">{promises.map(a => <li key={a.id} className={isOverdue(a) ? 'is-hot' : ''} style={{ ['--z' as string]: 'var(--rescue)' }}><div className="hv-issue-top"><ClientTag id={a.clientId} open={open} /><span className="hv-age">{isOverdue(a) ? `${daysBetween(a.due)}d late` : 'Not acknowledged'}</span></div><p className="hv-issue-title">{a.title}</p><small>{a.owner || 'Unassigned'}{a.due ? ` · due ${dateLabel(a.due)}` : ''}</small><div className="drawer-inline"><button className="button button-small button-outline" onClick={goActions}>Open in Action Hub</button></div></li>)}</ul> : <p className="rb-empty">Every promise is on track{mine ? ' for your clients' : ''}.</p>}
        </div>
      </div>
    </section>
  </>;
}

// ---- 2. Clients ------------------------------------------------------------------------
function ClientsTab({ pulses, props, openId, setOpenId }: { pulses: Pulse[]; props: Props; openId: string | null; setOpenId: (id: string | null) => void }) {
  const [zone, setZone] = useState<'all' | Zone | 'Settling in'>('all');
  const [owner, setOwner] = useState('all');
  const [viktor, setViktor] = useState(false);
  if (openId) return <ClientView id={openId} props={props} viktor={viktor} back={() => setOpenId(null)} />;
  const owners = [...new Set(pulses.map(p => ownerOf(p.clientId)).filter(Boolean))];
  const list = [...pulses]
    .filter(p => zone === 'all' || (zone === 'Settling in' ? p.settling : !p.settling && now(p).zone === zone))
    .filter(p => owner === 'all' || ownerOf(p.clientId) === owner)
    .sort((a, b) => Number(!!a.settling) - Number(!!b.settling) || zoneRank(now(b).zone) - zoneRank(now(a).zone) || moodDelta(a) - moodDelta(b));
  return <>
    <div className="hv-clients-bar">
      <div className="hv-zone-filter" role="group" aria-label="Zone">{(['all', 'Rescue', 'Fix our side', 'Reach out', 'Steady', 'Settling in'] as const).map(z => { const n = z === 'all' ? pulses.length : pulses.filter(p => z === 'Settling in' ? p.settling : !p.settling && now(p).zone === z).length; return <button key={z} className={`${zone === z ? 'selected' : ''} ${z !== 'all' ? zoneClass(z === 'Settling in' ? null : z) : ''}`} aria-pressed={zone === z} onClick={() => setZone(z)}>{z === 'all' ? 'All clients' : z}<span>{n}</span></button>; })}</div>
      <div className="hv-list-tools">
        <ThemedSelect aria-label="Owner" value={owner} onChange={setOwner}><option value="all">All owners</option>{owners.map(o => <option key={o} value={o}>{o}</option>)}</ThemedSelect>
        <div className="rb-layout" role="group" aria-label="Ads context"><button className={!viktor ? 'selected' : ''} aria-pressed={!viktor} onClick={() => setViktor(false)}>Everyday</button><button className={viktor ? 'selected' : ''} aria-pressed={viktor} onClick={() => setViktor(true)}>With Ads (Viktor)</button></div>
      </div>
    </div>
    <div className="hv-client-grid">{list.map(p => { const c = clientById(p.clientId); const n = now(p); const a = assessmentFor(p.clientId); const w = waitingFor(p.clientId)[0]; return <button key={p.clientId} className={`hv-client-card ${p.settling ? 'z-none' : zoneClass(n.zone)}`} onClick={() => setOpenId(p.clientId)}>
      <span className="hv-cc-top"><Avatar client={c} small /><span className="hv-cc-name"><strong>{c.name}</strong><small>{c.service} · {ownerOf(p.clientId) || 'No owner'}</small></span><span className="hv-zone-pill">{p.settling ? 'Settling in' : n.zone}</span></span>
      <span className="hv-cc-spark"><Sparkline values={p.mood} /><small>8 weeks</small></span>
      <span className="hv-cc-facts"><span><small>How they feel</small><MoodChange p={p} /></span><span><small>How we’re doing</small><b className={`hv-deliv d-${n.delivery}`}>{DELIVERY[n.delivery]}</b></span></span>
      <span className="hv-cc-foot">
        <span>{lastHeard(p)}</span>
        {w && <span className="hv-cc-flag">Waiting on our reply {w.businessDays}d</span>}
        {isLeadLock(p.clientId) && (a.leadNumbers ? <span className="hv-cc-lead">Inquiries {a.leadNumbers.inquiries[0]} {a.leadNumbers.inquiries[0] >= a.leadNumbers.inquiries[1] ? '▲' : '▼'}</span> : <span className="hv-cc-lead muted">Leads: access pending</span>)}
        {viktor && (a.viktor ? <span className={`hv-viktor v-${a.viktor.rating.toLowerCase()}`} title={a.viktor.note}>Ads {a.viktor.rating}</span> : <span className="muted">No Viktor post</span>)}
      </span>
    </button>; })}{!list.length && <p className="rb-empty">No clients match these filters.</p>}</div>
    <p className="hv-rules">The AI reads only words the client wrote or said, never staff or Viktor text. A quiet client stays where they were; silence isn’t unhappiness. Only routine messages reads “Not enough to read”. How they feel and how we’re doing are never combined into a score.</p>
  </>;
}

/** Week index a date falls in (each week ends on its WEEKS date). */
const weekIndexOf = (date: string) => { const i = WEEKS.findIndex(w => date <= w); return i < 0 ? WEEKS.length - 1 : i; };
const isNegative = (r: ToneReading) => r.tone <= 1;

/** How long the client has sat in its current zone, and where it was before. */
function zoneStreak(p: Pulse) {
  const cur = weekZone(p, 7); let i = 7;
  while (i > 0 && weekZone(p, i - 1) === cur) i--;
  return { zone: cur, weeks: 8 - i, prev: i > 0 ? weekZone(p, i - 1) : null, since: i > 0 ? addDays(WEEKS[i], -6) : null, whole: i === 0 };
}

/** The latest week the tone fell, and the nearest slip on our side in the fortnight before it. */
function turningPoint(p: Pulse) {
  for (let i = 7; i > 0; i--) {
    const m = p.mood[i], b = p.mood[i - 1];
    if (m === null || b === null || m >= b) continue;
    const weekEnd = WEEKS[i], from = addDays(weekEnd, -20);
    const slip = p.ourSide.filter(e => e.kind === 'slip' && e.date <= weekEnd && e.date >= from).sort((x, y) => y.date.localeCompare(x.date))[0];
    const said = p.readings.filter(r => weekIndexOf(r.date) === i && isNegative(r)).sort((x, y) => y.date.localeCompare(x.date))[0];
    return { week: weekEnd, from: FEEL[b], to: FEEL[m], slip, said };
  }
  return null;
}

/** Recurring topics in the client's own words, worst-sounding first. */
function themeSummary(p: Pulse) {
  return THEMES.map(t => { const rs = p.readings.filter(r => r.theme === t); return { theme: t, rs, neg: rs.filter(isNegative).length, last: rs.map(r => r.date).sort().pop() }; })
    .filter(t => t.rs.length).sort((a, b) => b.neg - a.neg || b.rs.length - a.rs.length);
}

type RecordFilter = 'all' | 'said' | 'did';

/**
 * One client's health. `embedded` is the client record's Health tab: the record already shows who the client is,
 * so the identity and back link are dropped and the long week-by-week record starts collapsed.
 */
export function ClientView({ id, props, viktor, back, embedded = false }: { id: string; props: Props; viktor: boolean; back?: () => void; embedded?: boolean }) {
  const p = pulseFor(id), a = assessmentFor(id), c = clientById(id), owner = ownerOf(id);
  const n = now(p);
  const leadlock = isLeadLock(id);
  const [picked, setPicked] = useState<ToneReading | undefined>(undefined);
  const [show, setShow] = useState<RecordFilter>('all');
  const [theme, setTheme] = useState<Theme | null>(null);
  const [recordOpen, setRecordOpen] = useState(!embedded);
  const ours = [a.dims.follow, a.dims.support].filter(d => d.level !== 'na');
  const engagement = [a.dims.onboarding, a.dims.programme].find(d => d.level !== 'na');
  const zone = ZONES.find(z => z.id === n.zone);
  const waiting = waitingFor(id);
  const promises = slippingPromises(props.actions).filter(x => x.clientId === id);
  const support = openSupport(id);
  const owed = waiting.length + promises.length + support.length;
  const streak = zoneStreak(p);
  const turn = p.settling ? null : turningPoint(p);
  const themes = themeSummary(p);
  // One complaint is a moment; the same topic twice is a pattern worth preparing for.
  const concern = themes.find(t => t.neg >= 2);
  const topic = [...themes].sort((x, y) => y.rs.length - x.rs.length)[0];
  const month = p.readings.filter(r => r.date >= MONTH_AGO);
  const latest = latestReading(p);
  const firstMood = p.mood.find(m => m !== null) ?? null;
  const evidence = (sid: string) => props.showEvidence(sid);

  // One record of both sides, grouped by week, newest first.
  const entries = [
    ...p.readings.filter(() => show !== 'did').filter(r => !theme || r.theme === theme).map(r => ({ date: r.date, said: r as ToneReading | undefined, did: undefined as OurEvent | undefined })),
    ...(theme ? [] : p.ourSide).filter(() => show !== 'said').map(e => ({ date: e.date, said: undefined as ToneReading | undefined, did: e as OurEvent | undefined })),
  ].sort((x, y) => y.date.localeCompare(x.date));
  const weeks = [...new Set(entries.map(e => weekIndexOf(e.date)))];
  const pick = (r: ToneReading) => { setPicked(r); setShow('all'); setTheme(null); setRecordOpen(true); requestAnimationFrame(() => document.getElementById(`hv-rec-${p.readings.indexOf(r)}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })); };

  const addStep = () => { props.addAction({ id: `hv-${id}-${Date.now()}`, clientId: id, title: a.nextStep, owner, due: '', status: 'Open', side: 'WIA', acknowledged: false, sourceId: '', origin: 'AI proposal', priority: n.zone === 'Rescue' ? 'High' : 'Medium', note: 'Suggested by the Health & Sentiment reading. The team chose to act on it.', assignedOn: owner ? DEMO_DATE : undefined, lastActivity: DEMO_DATE, history: [{ date: DEMO_DATE, text: `Added from Health & Sentiment by ${me(props.viewer)}.` }] }); props.notify('Added to the Action Hub as a proposed action.'); };

  return <div className={`hv-client-view ${embedded ? 'is-embedded' : ''}`}>
    {!embedded && back && <button className="text-button hv-back" onClick={back}><ArrowLeft size={13} />All clients</button>}
    <header className={`hv-cv-head ${p.settling ? 'z-none' : zoneClass(n.zone)}`}>
      {embedded ? <div className="hv-cv-id hv-cv-zone"><div><p className="small-label">WHOSE MOVE IS IT · WEEK OF {dateLabel(addDays(WEEKS[7], -6)).toUpperCase()}</p><h2>{p.settling ? 'Settling in' : n.zone}</h2><p className="hv-cv-move">{p.settling ? 'In onboarding. Placed on the map once it has settled (about 60 days).' : zone?.move}{zone && zone.who !== '—' ? ` Owner: ${zone.who === 'Owner' ? owner || 'unassigned' : `Whitney + ${owner || 'owner'}`}.` : ''}</p><p>{lastHeard(p)}</p></div></div>
        : <div className="hv-cv-id"><Avatar client={c} /><div><h2>{c.name}</h2><p>{c.service} · {owner || 'No owner'} · {lastHeard(p)}</p></div></div>}
      <div className="hv-cv-state">
        <span className="hv-zone-pill">{p.settling ? 'Settling in' : n.zone}</span>
        <p>{p.settling ? 'In onboarding. Not placed on the map until it has settled (about 60 days).' : zone?.move}</p>
        <dl><div><dt>How they feel</dt><dd><MoodChange p={p} /></dd></div><div><dt>How we’re doing</dt><dd title={DELIVERY_RULES[n.delivery]}>{DELIVERY[n.delivery]}</dd></div>{viktor && a.viktor && <div><dt>Ads (Viktor)</dt><dd><span className={`hv-viktor v-${a.viktor.rating.toLowerCase()}`} title={a.viktor.note}>{a.viktor.rating}</span></dd></div>}</dl>
        {!p.settling && <small className="hv-streak">{streak.whole ? `${streak.zone} for all 8 weeks shown` : `${streak.zone} for ${streak.weeks} ${streak.weeks === 1 ? 'week' : 'weeks'} · ${streak.prev} until ${dateLabel(streak.since!)}`}</small>}
      </div>
    </header>

    {/* At a glance: the four things you'd otherwise piece together from the record below. */}
    <div className="hv-glance">
      <div><small>Tone, 8 weeks</small><strong>{firstMood === null || p.mood[7] === null ? 'Not enough to read' : firstMood === p.mood[7] ? `Held at ${FEEL[p.mood[7]!]}` : `${FEEL[firstMood]} → ${FEEL[p.mood[7]!]}`}</strong><span>{month.length ? `${month.filter(isNegative).length} of ${month.length} messages negative this month` : 'No messages this month'}</span></div>
      <div className={owed ? 'is-hot' : 'is-ok'}><small>We owe them</small><strong>{owed ? `${owed} open ${owed === 1 ? 'item' : 'items'}` : 'Nothing open'}</strong><span>{waiting.length ? `Reply owed ${waiting[0].businessDays} business ${waiting[0].businessDays === 1 ? 'day' : 'days'}` : promises.length ? `${promises.length} ${promises.length === 1 ? 'promise' : 'promises'} slipping` : support.length ? `${support.length} support ${support.length === 1 ? 'issue' : 'issues'} open` : 'Our side is clear'}</span></div>
      {concern ? <div><small>Keeps raising</small><strong>{concern.theme}</strong><span>{concern.neg} negative mentions · last {dateLabel(concern.last!)}</span></div> : <div><small>Talks most about</small><strong>{topic?.theme || 'Nothing yet'}</strong><span>{topic ? `${topic.rs.length}× · no topic raised negatively twice` : 'Readings come from extraction'}</span></div>}
      <div><small>Last heard</small><strong>{latest ? `${daysBetween(latest.date)} ${daysBetween(latest.date) === 1 ? 'day' : 'days'} ago` : 'Not yet'}</strong><span>{latest ? `${latest.speaker.split(' ')[0]} on ${latest.channel} · ${MOODS[latest.tone]}` : 'Readings come from extraction'}</span></div>
    </div>

    <div className="hv-cv-body">
      <div className="hv-cv-main">
        {owed > 0 && <section className="hv-card hv-cv-owe">
          <header className="hv-list-head"><div><h2>What we owe them</h2><p>Open now, oldest first. These set “how we’re doing”.</p></div>{promises.length > 0 && <button className="button button-small button-outline" onClick={() => props.navigate('actions-v3')}>Open in Action Hub</button>}</header>
          {waiting.map(w => <div className="hv-fact lvl-worst" key={w.date}><strong><MessageSquareReply size={12} />Waiting on our reply · {w.businessDays} business {w.businessDays === 1 ? 'day' : 'days'}</strong><p>{w.from}: “{w.text}” · {w.channel}, {dateLabel(w.date)}</p></div>)}
          {promises.map(x => <div className={`hv-fact ${isOverdue(x) ? 'lvl-worst' : 'lvl-middle'}`} key={x.id}><strong><Clock3 size={12} />{isOverdue(x) ? `${daysBetween(x.due)}d late` : 'Not acknowledged'} · {x.owner || 'Unassigned'}</strong><p>{x.title}</p></div>)}
          {support.map(s => <div className={`hv-fact ${(s.repeats || 0) > 1 ? 'lvl-worst' : 'lvl-middle'}`} key={s.id}><strong><Wrench size={12} />{(s.repeats || 0) > 1 ? `Support issue reported ${s.repeats}×` : `Support issue · ${s.state}`}</strong><p>{s.title}. {s.latest}</p></div>)}
        </section>}

        <section className="hv-card">
          <header><h2>Eight weeks, both sides</h2><p>The line is how they sounded each week; dots are their messages (hollow = low confidence). The band is the zone they sat in. Triangles are our side: ▼ slipped, ▲ delivered. Click a dot to find it in the record.</p></header>
          <Timeline p={p} picked={picked} pick={pick} />
          {turn && <div className={`hv-turn ${turn.slip ? 'is-ours' : 'is-theirs'}`}>
            <p className="small-label">WHAT MOVED IT</p>
            <p>Tone fell from <b>{turn.from}</b> to <b>{turn.to}</b> the week of {dateLabel(addDays(turn.week, -6))}.{' '}
              {turn.slip ? <>Nearest slip on our side before it: <b>{turn.slip.text}</b> ({dateLabel(turn.slip.date)}). Fixing that is the likeliest way back.</> : <>Nothing slipped on our side in the fortnight before. The cause is probably on their end, so ask rather than fix.</>}</p>
            {turn.said && <p className="hv-turn-quote">“{turn.said.quote.length > 140 ? `${turn.said.quote.slice(0, 138)}…` : turn.said.quote}” <em>{turn.said.speaker.split(' ')[0]}, {dateLabel(turn.said.date)}</em></p>}
          </div>}
          {!turn && !p.settling && p.readings.length > 0 && <p className="hv-turn is-flat">No drop in tone across these eight weeks.</p>}
        </section>

        <section className="hv-card">
          <header className="hv-list-head"><div><h2>The record</h2><p>Everything they said and everything we did, week by week.{theme ? <> Showing <b>{theme}</b> only. <button className="text-button" onClick={() => setTheme(null)}>Clear</button></> : null}</p></div>
            {!recordOpen ? <button className="button button-small button-outline" onClick={() => setRecordOpen(true)}>Show {p.readings.length + p.ourSide.length} entries</button> : <div className="rb-layout" role="group" aria-label="Show">{([['all', 'Both sides'], ['said', 'They said'], ['did', 'We did']] as [RecordFilter, string][]).map(([k, l]) => <button key={k} className={show === k ? 'selected' : ''} aria-pressed={show === k} onClick={() => setShow(k)}>{l}</button>)}</div>}
          </header>
          {!recordOpen ? null : weeks.length ? weeks.map(wi => { const z = weekZone(p, wi); return <div key={wi} className="hv-rec-week">
            <div className={`hv-rec-week-head ${cellClass(z)}`}><span className="hv-rec-swatch" /><b>Week of {dateLabel(addDays(WEEKS[wi], -6))}</b><span>{z}</span><span>{p.mood[wi] === null ? 'Not enough to read' : FEEL[p.mood[wi]!]} · {DELIVERY[p.delivery[wi]]}</span></div>
            <ul className="hv-feed">{entries.filter(e => weekIndexOf(e.date) === wi).map((e, i) => e.said
              ? <li key={i} id={`hv-rec-${p.readings.indexOf(e.said)}`} className={`tone-${e.said.tone} ${e.said === picked ? 'is-picked' : ''}`}><span className={`hv-tone-dot ${e.said.confidence === 'Low' ? 'is-low' : ''}`} aria-hidden="true" /><div><p>“{e.said.quote}”</p><footer><span>{e.said.speaker} · {e.said.channel} · {dateLabel(e.said.date)}</span><button className="hv-theme-tag" onClick={() => setTheme(e.said!.theme)}>{e.said.theme}</button><span className={`hv-tone tone-${e.said.tone}`}>{MOODS[e.said.tone]}{e.said.confidence === 'Low' ? ' · low confidence' : ''}</span>{e.said.sourceId && <SourceLink id={e.said.sourceId} onOpen={evidence} />}</footer></div></li>
              : <li key={i} className={`hv-rec-ours ${e.did!.kind}`}><span className="hv-rec-mark" aria-hidden="true">{e.did!.kind === 'slip' ? '▼' : '▲'}</span><div><p><b>{e.did!.kind === 'slip' ? 'We slipped' : 'We delivered'}</b> · {e.did!.text}</p><footer><span>Our side · {dateLabel(e.did!.date)}</span></footer></div></li>)}</ul>
          </div>; }) : <p className="rb-empty">Nothing to show for this filter.</p>}
        </section>

        {leadlock && <section className="hv-card"><header><h2>Lead results</h2><p>{a.leadNumbers ? `${a.period} vs prior period. Kept separate from how they feel: good leads don’t cancel a frustrated client.` : 'LeadLock is linked but leads can’t be read yet.'}</p></header><LeadBlock id={id} /></section>}
      </div>

      <aside className="hv-cv-rail">
        <section className="hv-why"><span className="hv-ai"><Sparkles size={11} />AI reading · every claim cited</span><p>{a.why}</p><button className="text-button" onClick={() => props.notify('Flagged. The reading goes to review and is regenerated.')}><Flag size={11} />Flag as wrong</button></section>
        <section className="hv-next"><p className="small-label">SUGGESTED NEXT STEP</p><p>{a.nextStep}</p><div className="drawer-inline"><button className="button button-small button-primary" onClick={addStep}><Plus size={13} />Add as action</button><button className="button button-small button-outline" onClick={() => props.notify(`Preview: a Slack DM to ${owner || 'the owner'} would be drafted for review first.`)}><Send size={13} />Notify {owner || 'owner'}</button></div></section>
        {themes.length > 0 && <section className="hv-rail-block hv-cv-themes" onClick={() => setRecordOpen(true)}><p className="small-label">WHAT THEY TALK ABOUT</p><p className="hv-rail-hint">Their messages by topic, coloured by tone. Click one to filter the record.</p>
          <ul>{themes.map(t => <li key={t.theme}><button className={theme === t.theme ? 'selected' : ''} aria-pressed={theme === t.theme} onClick={() => { setTheme(theme === t.theme ? null : t.theme); setShow('all'); }}>
            <span className="hv-ct-name">{t.theme}<em>{t.rs.length}×</em></span>
            <span className="hv-ct-bar">{[...t.rs].sort((x, y) => x.tone - y.tone).map((r, i) => <i key={i} className={`tone-${r.tone}`} title={`${MOODS[r.tone]} · ${dateLabel(r.date)}`} />)}</span>
          </button></li>)}</ul>
        </section>}
        {ours.length > 0 && <section className="hv-rail-block"><p className="small-label">WHY “{DELIVERY[n.delivery].toUpperCase()}”</p>{ours.map((d, i) => <div className={`hv-fact lvl-${d.level}`} key={i}><strong>{d.state}</strong>{d.drivers.map((r, j) => <p key={j}>{r.text}{r.sourceId && <> <SourceLink id={r.sourceId} onOpen={evidence} /></>}</p>)}</div>)}</section>}
        {engagement && <section className="hv-rail-block"><p className="small-label">{a.dims.programme.level !== 'na' ? 'PROGRAMME' : 'ONBOARDING'}</p><div className={`hv-fact lvl-${engagement.level}`}><strong>{engagement.state}</strong>{engagement.drivers.map((r, j) => <p key={j}>{r.text}</p>)}</div></section>}
        <p className="hv-coverage">{a.coverage.join(' · ')}</p>
      </aside>
    </div>
  </div>;
}

// ---- 3. Patterns -----------------------------------------------------------------------
function PatternsTab({ pulses, actions, open }: { pulses: Pulse[]; actions: Action[]; open: (id: string) => void }) {
  const [theme, setTheme] = useState<Theme | null>(null);
  const counts = WEEKS.map((_, i) => ZONE_ORDER.map(z => pulses.filter(p => weekZone(p, i) === z).length));
  const risk = (z: string) => z === 'Rescue' || z === 'Fix our side';
  const streak = (p: Pulse) => { let n = 0; for (let i = 7; i >= 0 && risk(weekZone(p, i)); i--) n++; return n; };
  const atRiskNow = counts[7][0] + counts[7][1], atRiskThen = counts[0][0] + counts[0][1];
  const max = Math.max(pulses.length, 1);
  const month = allReadings().filter(r => r.date >= MONTH_AGO && pulses.some(p => p.clientId === r.clientId));
  const themeStats = THEMES.map(t => { const list = month.filter(r => r.theme === t); return { t, n: list.length, concerns: list.filter(r => toneKind(r.tone) === 'Concern').length, clients: new Set(list.map(r => r.clientId)).size }; }).filter(s => s.n).sort((a, b) => b.concerns - a.concerns || b.n - a.n);
  const cooling = pulses.filter(p => { const rs = [...p.readings].sort((a, b) => a.date.localeCompare(b.date)); const last = rs[rs.length - 1]; const earlier = rs.slice(0, -1); if (!last || last.confidence === 'Low' || earlier.length < 2) return false; return last.tone < earlier.reduce((s, r) => s + r.tone, 0) / earlier.length - 0.75; });
  const owners = [...new Set(CLIENTS.filter(c => pulses.some(p => p.clientId === c.id)).map(c => ownerOf(c.id)).filter(Boolean))].map(name => {
    const ids = pulses.filter(p => ownerOf(p.clientId) === name).map(p => p.clientId);
    return { name, clients: ids.length, atRisk: ids.filter(cid => { const p = PULSE.find(x => x.clientId === cid); return p && !p.settling && risk(now(p).zone || ''); }).length, waiting: WAITING.filter(w => ids.includes(w.clientId)).length, overdue: actions.filter(a => ids.includes(a.clientId) && a.side === 'WIA' && isOverdue(a)).length };
  }).sort((a, b) => b.atRisk - a.atRisk || b.overdue - a.overdue);
  return <>
    <section className="hv-pattern" aria-label="Book health">
      <header className="hv-pattern-head"><h2>Book health</h2><p>Is our book of clients getting healthier? Red and amber should shrink over time.</p></header>
      <div className="hv-move-head">
        <div className="hv-stat"><span>At risk now</span><strong>{atRiskNow}</strong><small>Rescue or Fix our side</small></div>
        <div className="hv-stat"><span>8 weeks ago</span><strong>{atRiskThen}</strong><small>{atRiskNow > atRiskThen ? `Up ${atRiskNow - atRiskThen}` : atRiskNow < atRiskThen ? `Down ${atRiskThen - atRiskNow}` : 'No change'}</small></div>
        <div className="hv-stat"><span>Steady now</span><strong>{counts[7][3]}</strong><small>of {pulses.length} clients</small></div>
      </div>
      <div className="hv-pattern-grid">
        <section className="hv-card"><header><h2>Clients per zone, by week</h2></header>
          <div className="hv-stack" role="img" aria-label="Number of clients in each zone for each of the last eight weeks">{counts.map((col, i) => <div key={WEEKS[i]} className="hv-stack-col"><div className="hv-stack-bar">{col.map((n, z) => n ? <span key={z} className={`seg ${cellClass(ZONE_ORDER[z])}`} style={{ height: `${n / max * 100}%` }} title={`${ZONE_ORDER[z]}: ${n}`}>{n}</span> : null)}</div><small>{dateLabel(WEEKS[i])}</small></div>)}</div>
          <div className="hv-legend">{ZONE_ORDER.map(z => <span key={z}><i className={cellClass(z)} />{z === 'Not enough' ? 'Not enough to read' : z}</span>)}</div>
        </section>
        <section className="hv-card"><header><h2>Longest at risk</h2><p>Weeks in a row in Rescue or Fix our side: the retention conversations to have.</p></header>
          <table className="hv-heat"><tbody>{[...pulses].sort((a, b) => streak(b) - streak(a)).map(p => <tr key={p.clientId} onClick={() => open(p.clientId)}>
            <td><span className="hv-client"><Avatar client={clientById(p.clientId)} small /><strong>{clientById(p.clientId).name}</strong></span></td>
            {WEEKS.map((w, i) => <td key={w}><span className={`hv-cell ${cellClass(weekZone(p, i))}`} title={`${dateLabel(w)}: ${weekZone(p, i)}`} /></td>)}
            <td>{streak(p) ? <strong className="hv-streak">{streak(p)}w</strong> : <span className="muted small-text">—</span>}</td>
          </tr>)}</tbody></table>
        </section>
      </div>
    </section>

    <section className="hv-pattern" aria-label="Themes across clients">
      <header className="hv-pattern-head"><h2>Themes across clients</h2><p>What clients keep raising this month. Fixed topics, so months compare. Concerns first.</p></header>
      {cooling.length > 0 && <div className="hv-cooling"><TrendingDown size={16} /><p><strong>Cooling tone:</strong> {cooling.map((p, i) => <span key={p.clientId}>{i ? ', ' : ''}<button className="text-button" onClick={() => open(p.clientId)}>{clientById(p.clientId).name}</button></span>)} {cooling.length === 1 ? 'sounds' : 'sound'} noticeably less positive than usual.</p></div>}
      <div className="hv-theme-grid">{themeStats.map(s => <button key={s.t} className={`hv-theme ${theme === s.t ? 'selected' : ''} ${s.concerns ? 'has-concern' : ''}`} aria-pressed={theme === s.t} onClick={() => setTheme(theme === s.t ? null : s.t)}><span>{s.t}</span><strong>{s.n}×</strong><small>{s.clients} {s.clients === 1 ? 'client' : 'clients'}{s.concerns ? ` · ${s.concerns} ${s.concerns === 1 ? 'concern' : 'concerns'}` : ''}</small></button>)}</div>
      {theme && <section className="hv-card hv-theme-quotes"><header className="hv-list-head"><div><h2>{theme}</h2><p>What clients said about it this month.</p></div><button className="text-button" onClick={() => setTheme(null)}>Close</button></header>
        <ul className="hv-feed">{month.filter(r => r.theme === theme).map((r, i) => <li key={i} className={`tone-${r.tone}`}><span className={`hv-tone-dot ${r.confidence === 'Low' ? 'is-low' : ''}`} aria-hidden="true" /><div><p>“{r.quote}”</p><footer><ClientTag id={r.clientId} open={open} /><span>{r.speaker} · {dateLabel(r.date)}</span><span className={`hv-tone tone-${r.tone}`}>{MOODS[r.tone]}</span></footer></div></li>)}</ul>
      </section>}
    </section>

    <section className="hv-pattern" aria-label="Workload by owner">
      <header className="hv-pattern-head"><h2>Workload by owner</h2><p>When one person’s clients slip together, it’s usually workload, not the clients.</p></header>
      <div className="hv-owners">{owners.map(o => <div key={o.name} className={`hv-owner ${o.atRisk ? 'is-hot' : ''}`}><span className="person-avatar">{o.name[0]}</span><div><strong>{o.name}</strong><small>{o.clients} {o.clients === 1 ? 'client' : 'clients'}</small></div><dl><div><dt>At risk</dt><dd>{o.atRisk}</dd></div><div><dt>Overdue</dt><dd>{o.overdue}</dd></div><div><dt>Waiting</dt><dd>{o.waiting}</dd></div></dl></div>)}</div>
    </section>
  </>;
}

// ---- Monday review -----------------------------------------------------------------
function MondayDialog({ pulses, close, notify }: { pulses: Pulse[]; close: () => void; notify: (m: string) => void }) {
  const agenda = [...pulses].filter(p => !p.settling).sort((a, b) => zoneRank(now(b).zone) - zoneRank(now(a).zone) || moodDelta(a) - moodDelta(b));
  return <Dialog title="Monday review" subtitle={`Week ending ${dateLabel(DEMO_DATE)}`} className="hv-monday" onClose={close}>
    <p className="hint">Built from This week and each client’s reading, with Viktor’s ad rating as context. Review before posting.</p>
    <ol className="hv-agenda">{agenda.map(p => { const a = assessmentFor(p.clientId); const n = now(p); return <li key={p.clientId} className={zoneClass(n.zone)}>
      <div className="hv-agenda-top"><strong>{clientById(p.clientId).name}</strong><span className="hv-zone-pill">{n.zone}</span>{a.viktor && <span className={`hv-viktor v-${a.viktor.rating.toLowerCase()}`}>Ads {a.viktor.rating}</span>}<small>{ownerOf(p.clientId)}</small></div>
      <p>{p.story || a.why}</p><p className="hv-agenda-step">→ {a.nextStep}</p>
    </li>; })}</ol>
    <div className="slack-footer"><span className="hint">Posts to #wia-monday as a summary. Preview only: nothing is sent.</span><button className="button button-primary" onClick={() => { close(); notify('Preview: the Monday review was posted after review. Nothing was sent.'); }}><Send size={14} />Post to Slack</button></div>
  </Dialog>;
}

// ---- Page ------------------------------------------------------------------------------
// Three views, three questions: who needs us now, how is this client, what patterns are forming.
type TabId = 'week' | 'clients' | 'patterns';
const TABS: { id: TabId; label: string; question: string }[] = [
  { id: 'week', label: 'This week', question: 'Who needs us now, and whose move is it?' },
  { id: 'clients', label: 'Clients', question: 'How is each client, and why?' },
  { id: 'patterns', label: 'Patterns', question: 'What is forming across clients?' },
];

export default function HealthRevised(props: Props & { clientId?: string }) {
  const [tab, setTab] = useState<TabId>(props.clientId ? 'clients' : 'week');
  const [openId, setOpenId] = useState<string | null>(props.clientId || null);
  const [mondayOpen, setMondayOpen] = useState(false);
  const pulses = PULSE.filter(p => CLIENTS.some(c => c.id === p.clientId) && (!props.clientId || p.clientId === props.clientId));
  // Opening a client from anywhere goes to its page in the Clients view.
  const open = (id: string) => { setOpenId(id); setTab('clients'); window.scrollTo({ top: 0, behavior: 'smooth' }); };
  const pick = (t: TabId) => { setTab(t); setOpenId(t === 'clients' ? props.clientId || null : null); };
  const moved = pulses.filter(p => slid(p) || recovered(p)).length;
  const atRisk = pulses.filter(p => !p.settling && (now(p).zone === 'Rescue' || now(p).zone === 'Fix our side')).length;
  const concerns = allReadings().filter(r => r.date >= MONTH_AGO && toneKind(r.tone) === 'Concern' && pulses.some(p => p.clientId === r.clientId)).length;
  const badge: Record<TabId, { text: string; hot?: boolean }> = { week: { text: `${moved} moved`, hot: moved > 0 }, clients: { text: `${atRisk} at risk`, hot: atRisk > 0 }, patterns: { text: `${concerns} concerns this month` } };
  const current = TABS.find(t => t.id === tab)!;

  return <div className="view hv-view">
    <header className="hv-head">
      <div><p className="rb-eyebrow">Client intelligence</p><h1>Health &amp; Sentiment</h1><p className="hv-lede">How each client feels, how we’re doing for them, and whose move it is.</p></div>
      <div className="hv-head-tools"><span className="hv-asof"><Sparkles size={12} />AI reading as of Mon 7:00 · Gmail, Slack, Fathom current</span><button className="button button-small button-primary" onClick={() => setMondayOpen(true)}><CalendarCheck size={13} />Prepare Monday review</button></div>
    </header>

    <div className="workspace-client-filter"><span className="small-label">Client</span><ThemedSelect aria-label="Health client filter" value={props.clientId || 'all'} onChange={id => { window.location.hash = id === 'all' ? 'health-v2' : `health-v2/${id}`; }}><option value="all">All clients</option>{CLIENTS.map(client => <option key={client.id} value={client.id}>{client.name}</option>)}</ThemedSelect>{props.clientId && <button className="text-button" onClick={() => { window.location.hash = 'health-v2'; }}>Clear client filter</button>}</div>
    <div className="hv-tabs" role="tablist" aria-label="Health views">
      {TABS.map(t => <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? 'selected' : ''} onClick={() => pick(t.id)}>{t.label}<span className={badge[t.id].hot ? 'is-hot' : ''}>{badge[t.id].text}</span></button>)}
    </div>
    {!(tab === 'clients' && openId) && <p className="hv-question">{current.question}</p>}

    {tab === 'week' && <WeekTab pulses={pulses} actions={props.actions} viewer={props.viewer} open={open} notify={props.notify} goActions={() => props.navigate('actions-v3')} />}
    {tab === 'clients' && <ClientsTab pulses={pulses} props={props} openId={openId} setOpenId={setOpenId} />}
    {tab === 'patterns' && <PatternsTab pulses={pulses} actions={props.actions} open={open} />}

    {mondayOpen && <MondayDialog pulses={pulses} close={() => setMondayOpen(false)} notify={props.notify} />}
  </div>;
}
