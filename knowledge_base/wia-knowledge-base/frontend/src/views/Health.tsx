import { ThemedSelect } from '../components/ThemedSelect';
import { useState } from 'react';
import { AlertTriangle, ArrowRight, Flag, Hourglass, ListPlus, Quote, RefreshCw, Send, Sparkles, TrendingDown, TrendingUp } from 'lucide-react';
import { CLIENTS, clientById, dateLabel } from '../data';
import { recordFor } from '../records';
import { ASSESSMENTS, DIMENSIONS, VOICE, WAITING, assessmentFor, categoryOf, type Assessment, type Category, type DimId, type DimState } from '../health';
import { Avatar, Dialog, Empty, PageHeading, Panel, Segmented, SourceLink } from '../components/UI';
import type { WorkspaceProps } from '../types';
import './Health.css';

const CATEGORIES: Category[] = ['Needs attention', 'Watch', 'Settling in', 'Steady', 'Unassessed'];
const catClass = (c: Category) => `cat-${c.toLowerCase().replace(/\s/g, '-')}`;
export const categoryFor = (id: string) => categoryOf(assessmentFor(id), recordFor(id).lifecycle === 'Onboarding');

export function CategoryChip({ id, withCause = false }: { id: string; withCause?: boolean }) {
  const { category, causes } = categoryFor(id);
  return <span className={`category-chip ${catClass(category)}`} title={causes.join(' · ')}>{category}{withCause && category !== 'Steady' ? ` · ${causes[0]}` : ''}</span>;
}

function DimChip({ s, onClick }: { s: DimState; onClick?: () => void }) {
  return <button className={`dim-chip level-${s.level}`} onClick={onClick} disabled={!onClick}>{s.state}</button>;
}

function Drivers({ s, props }: { s: DimState; props: WorkspaceProps }) {
  return <ul className="driver-list">{s.drivers.map((d, i) => <li key={i}><span className={`driver-kind kind-${d.kind.toLowerCase()}`}>{d.kind}</span><span>{d.text}{d.date ? <span className="hint"> · {dateLabel(d.date)}</span> : null}</span>{d.sourceId && <SourceLink id={d.sourceId} onOpen={props.showEvidence} />}</li>)}</ul>;
}

function Trend({ a }: { a: Assessment }) {
  return <div className="trend-strip" aria-label="Category over the last 8 weeks">{a.history.map((c, i) => <span key={i} className={catClass(c)} title={`${8 - i} weeks ago: ${c}`} />)}<small className="hint">8 weeks</small></div>;
}

function EngagementCard({ id, props, compact = false }: { id: string; props: WorkspaceProps; compact?: boolean }) {
  const a = assessmentFor(id); const c = clientById(id); const r = recordFor(id); const { category, causes } = categoryFor(id);
  const quotes = VOICE.filter(v => v.clientId === id).sort((x, y) => y.date.localeCompare(x.date)).slice(0, 2);
  const dims = DIMENSIONS.filter(d => a.dims[d.id].level !== 'na' && d.id !== 'leads' && d.id !== 'handling');
  return <article className={`panel engagement-card ${catClass(category)}-edge`}>
    {!compact && <div className="engagement-head"><Avatar client={c} small /><div><button className="plain-link" onClick={() => props.openClient(id, 'health')}><h3>{c.name}</h3></button><p className="hint">{r.engagements.map(e => e.type).join(' + ')} · owner {r.owner}</p></div><Trend a={a} /></div>}
    <div className="category-line"><span className={`category-chip ${catClass(category)}`}>{category}</span><span className="hint">{causes.join(' · ')} · {a.period}, assessed {dateLabel(a.assessedOn)}</span></div>
    <div className="why-box"><span className="ai-label"><Sparkles size={11} />AI-written · every claim cited below</span><p>{a.why}</p><div className="drawer-inline"><button className="text-button" onClick={() => props.notify('Flagged. The summary goes to review and is regenerated.')}><Flag size={11} />Flag as wrong</button>{props.ask && <button className="text-button" onClick={() => props.ask!({ kind: 'health', clientId: id, label: `${c.name} health` })}>Ask why in Client 360<ArrowRight size={11} /></button>}</div></div>
    <div className="dim-blocks">{dims.map(d => <div className="dim-block" key={d.id}><div className="dim-block-head"><strong>{d.label}</strong><DimChip s={a.dims[d.id]} /></div><Drivers s={a.dims[d.id]} props={props} /></div>)}</div>
    {quotes.length > 0 && <div className="quote-row">{quotes.map(q => <blockquote key={q.id} className="origin-quote"><Quote size={12} /> {q.quote}<footer>{q.speaker} · {dateLabel(q.date)} · {q.channel}</footer></blockquote>)}</div>}
    {a.viktor && <p className="viktor-line"><span className={`rag rag-${a.viktor.rating.toLowerCase()}`}>{a.viktor.rating}</span>Ads (Viktor, {dateLabel(a.viktor.date)}): {a.viktor.note}. <span className="hint">Attributed context; doesn’t change the category.</span></p>}
    <div className="next-step-box"><div><span className="small-label">SUGGESTED NEXT STEP · PROPOSAL</span><p>{a.nextStep}</p></div><div className="drawer-inline"><button className="button button-small button-outline" onClick={() => props.notify('Added to the Action Hub’s Needs review as an AI proposal.')}><ListPlus size={13} />Add as action</button><button className="button button-small button-outline" onClick={() => props.notify(`Preview only: would open the Slack review screen to notify ${r.owner}.`)}><Send size={13} />Notify {r.owner}</button></div></div>
    <p className="hint coverage-line">Couldn’t see: {a.coverage.join(' · ')}</p>
  </article>;
}

function LeadOutcomes({ id, props }: { id: string; props: WorkspaceProps }) {
  const a = assessmentFor(id); const c = clientById(id); const n = a.leadNumbers;
  const delta = (x: [number, number]) => { const d = x[0] - x[1]; return <span className={d > 0 ? 'up' : d < 0 ? 'down' : ''}>{d > 0 ? <TrendingUp size={12} /> : d < 0 ? <TrendingDown size={12} /> : null}{d > 0 ? '+' : ''}{d} vs prior</span>; };
  if (a.dims.leads.level === 'na') return null;
  return <article className="panel lead-card"><div className="engagement-head"><Avatar client={c} small /><div><h3>{c.name}</h3><p className="hint">LeadLock · last 30 days vs prior 30</p></div><DimChip s={a.dims.leads} /></div>
    {n ? <><div className="lead-stats">{([['Inquiries', n.inquiries], ['Tours booked', n.tours], ['Bookings', n.booked]] as [string, [number, number]][]).map(([l, v]) => <div key={l}><span className="small-label">{l.toUpperCase()}</span><strong>{v[0]}</strong><small>{delta(v)}</small></div>)}<div><span className="small-label">INQUIRY → TOUR</span><strong>{Math.round(n.tours[0] / n.inquiries[0] * 100)}%</strong><small>prior {Math.round(n.tours[1] / n.inquiries[1] * 100)}%</small></div><div><span className="small-label">TOUR → BOOKED</span><strong>{Math.round(n.booked[0] / n.tours[0] * 100)}%</strong><small>prior {Math.round(n.booked[1] / n.tours[1] * 100)}%</small></div></div>
      <div className="lead-handling"><strong>Lead handling</strong><DimChip s={a.dims.handling} /><span>Median first response {n.firstResponse}</span><span className={n.uncontacted ? 'text-amber' : ''}>{n.uncontacted} uncontacted after 48 h</span><span>{n.stalled} stalled over 14 days</span></div>
      <Drivers s={a.dims.handling} props={props} />
      <details className="definitions"><summary>Definitions used for {c.name}</summary><ul>{n.definitions.map(d => <li key={d}>{d}</li>)}</ul></details>
      <p className="hint">No “leads from ads” claim unless the source field is reliable. Ad spend and cost per lead are out of scope (paid media deferred).</p></>
      : <div className="unavailable-box"><AlertTriangle size={14} /><div><strong>Unavailable</strong><p>{a.dims.leads.drivers[0].text} Numbers appear once read access to this LeadLock location is granted. Shown as unavailable, never as zero.</p></div></div>}
  </article>;
}

function VoiceFeed({ clientId, props }: { clientId?: string; props: WorkspaceProps }) {
  const [type, setType] = useState('all');
  const [client, setClient] = useState(clientId || 'all');
  const rows = VOICE.filter(v => (type === 'all' || v.type === type) && (client === 'all' || v.clientId === client)).sort((a, b) => b.date.localeCompare(a.date));
  return <><div className="toolbar"><Segmented label="Statement type" value={type} onChange={setType} options={[{ id: 'all', label: 'All' }, ...['Praise', 'Concern', 'Question', 'Request', 'Decision'].map(t => ({ id: t, label: t }))]} />{!clientId && <ThemedSelect aria-label="Client" value={client} onChange={setClient}><option value="all">All clients</option>{CLIENTS.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</ThemedSelect>}</div>
    <Panel title="In the client’s own words" eyebrow="DIRECT STATEMENTS ONLY · NEVER STAFF OR VIKTOR">{rows.length ? <ul className="voice-feed">{rows.map(v => <li key={v.id}><span className={`voice-type type-${v.type.toLowerCase()}`}>{v.type}</span><div><p>“{v.quote}”</p><span className="hint">{v.speaker}{!clientId ? ` · ${clientById(v.clientId).name}` : ''} · {dateLabel(v.date)} · {v.channel}</span></div>{v.sourceId && <SourceLink id={v.sourceId} onOpen={props.showEvidence} />}</li>)}</ul> : <Empty title="No statements for this filter" />}</Panel></>;
}

export default function Health(props: WorkspaceProps) {
  const [view, setView] = useState('overview');
  const [cat, setCat] = useState<string>('all');
  const [cell, setCell] = useState<{ id: string; dim: DimId } | null>(null);
  const [posting, setPosting] = useState(false);
  const cats = CLIENTS.map(c => ({ c, ...categoryFor(c.id) }));
  const order = (x: Category) => CATEGORIES.indexOf(x);
  const sorted = [...cats].sort((a, b) => order(a.category) - order(b.category));
  const monday = sorted.map(x => `• ${x.c.name}: ${x.category}${x.category !== 'Steady' ? ` (${x.causes[0]})` : ''}${assessmentFor(x.c.id).viktor ? ` · Ads (Viktor): ${assessmentFor(x.c.id).viktor!.rating.toLowerCase()}` : ''} · owner ${recordFor(x.c.id).owner}`).join('\n');
  const [mondayText, setMondayText] = useState(`*Monday client review · relationship + ads*\n${monday}\n\nWaiting on us: ${WAITING.map(w => `${clientById(w.clientId).name} (${w.businessDays} business ${w.businessDays === 1 ? 'day' : 'days'})`).join(', ')}.`);
  return <div className="view health-view">
    <PageHeading eyebrow="STAGE 3 · ENGAGEMENT AND OUTCOMES, KEPT SEPARATE" title="Health & sentiment" description="Which clients need care, and why. Every flag names its cause and links to the evidence. No combined score." />
    <div className="register-topbar"><p className="sync-line"><RefreshCw size={12} />Dimensions update with each change · summaries rebuilt Mon 7:00 and when a category worsens</p></div>
    <div className="register-tabs" role="tablist">{[['overview', 'Overview'], ['grid', 'Health grid'], ['engagement', 'Engagement'], ['leads', 'Lead outcomes'], ['voice', 'Client voice']].map(([id, label]) => <button key={id} role="tab" aria-selected={view === id} className={view === id ? 'selected' : ''} onClick={() => setView(id)}>{label}</button>)}</div>

    {view === 'overview' && <>
      <section className="register-tiles cat-tiles">{CATEGORIES.map(c => { const n = cats.filter(x => x.category === c).length; return <button key={c} className={`register-tile ${catClass(c)}-tile`} onClick={() => { setCat(c); setView('engagement'); }}><span className="register-tile-label"><span>{c}</span></span><strong>{String(n).padStart(2, '0')}</strong><small>{c === 'Unassessed' ? 'Not enough coverage to judge' : c === 'Settling in' ? 'In onboarding' : c === 'Needs attention' ? 'A dimension in its worst state' : c === 'Watch' ? 'A dimension slipping' : 'All assessed dimensions fine'}</small></button>; })}</section>
      <div className="detail-grid">
        <Panel title="Changed this week" eyebrow="CATEGORY MOVES">{ASSESSMENTS.filter(a => a.changed).map(a => { const now = categoryFor(a.clientId).category; return <div className="mini-row" key={a.clientId}><AlertTriangle size={14} /><div><strong>{clientById(a.clientId).name}</strong><p className="hint">{a.changed!.from} → <span className={`cat-text ${catClass(now)}`}>{now}</span> · {dateLabel(a.changed!.date)} · {a.changed!.reason}</p></div></div>; })}</Panel>
        <Panel title="Waiting on us" eyebrow="CLIENT MESSAGES WITH NO WIA REPLY"><p className="hint">Flagged after 1 business day. Counts toward Follow-through.</p>{WAITING.sort((a, b) => b.businessDays - a.businessDays).map(w => <div className="mini-row" key={w.clientId}><Hourglass size={14} className={w.businessDays > 3 ? 'text-amber' : ''} /><div><strong>{clientById(w.clientId).name} · {w.businessDays} business {w.businessDays === 1 ? 'day' : 'days'}</strong><p className="hint">{w.from} · {w.channel} · {dateLabel(w.date)}: “{w.text}”</p></div>{w.sourceId && <SourceLink id={w.sourceId} onOpen={props.showEvidence} />}</div>)}</Panel>
      </div>
      <Panel title="Needs attention" eyebrow="WHY, AND WHAT TO DO">{sorted.filter(x => x.category === 'Needs attention').map(x => <div className="attention-row" key={x.c.id}><Avatar client={x.c} small /><div><button className="plain-link" onClick={() => props.openClient(x.c.id, 'health')}><strong>{x.c.name}</strong></button><p className="hint">{x.causes.join(' · ')}</p><p>{assessmentFor(x.c.id).nextStep}</p></div><span className="hint">Owner {recordFor(x.c.id).owner}</span><button className="text-button" onClick={() => { setCat('Needs attention'); setView('engagement'); }}>Why<ArrowRight size={12} /></button></div>)}</Panel>
      <Panel title="Monday review" eyebrow="FOR THE MONDAY GOOGLE & META MEETINGS" action={<button className="button button-small button-outline" onClick={() => setPosting(true)}><Send size={13} />Post to Slack…</button>}>
        <div className="monday-table"><div className="monday-row head"><span>Client</span><span>Relationship (KB)</span><span>Ads (Viktor)</span><span>Owner</span><span>Focus this week</span></div>{sorted.map(x => { const a = assessmentFor(x.c.id); return <div className="monday-row" key={x.c.id}><strong>{x.c.name}</strong><span><span className={`category-chip ${catClass(x.category)}`}>{x.category}</span>{x.category !== 'Steady' && <small className="block hint">{x.causes[0]}</small>}</span><span>{a.viktor ? <><span className={`rag rag-${a.viktor.rating.toLowerCase()}`}>{a.viktor.rating}</span><small className="block hint">{a.viktor.note}</small></> : <span className="hint">No Viktor rating</span>}</span><span>{recordFor(x.c.id).owner}</span><span className="hint">{a.nextStep}</span></div>; })}</div>
        <p className="hint">Viktor’s rating is shown as he posted it (attributed). It never changes the KB category.</p>
      </Panel>
    </>}

    {view === 'grid' && <Panel title="Health grid" eyebrow="CLICK ANY CELL FOR ITS REASONS"><div className="table-scroll"><table className="health-grid-table"><thead><tr><th>Client</th><th>Category</th>{DIMENSIONS.map(d => <th key={d.id}>{d.short}</th>)}<th>Ads (Viktor)</th></tr></thead><tbody>{sorted.map(x => { const a = assessmentFor(x.c.id); return <tr key={x.c.id}><td><button className="plain-link" onClick={() => props.openClient(x.c.id, 'health')}>{x.c.name}</button><small className="block hint">{recordFor(x.c.id).owner}</small></td><td><span className={`category-chip ${catClass(x.category)}`}>{x.category}</span></td>{DIMENSIONS.map(d => <td key={d.id}><DimChip s={a.dims[d.id]} onClick={a.dims[d.id].level === 'na' ? undefined : () => setCell({ id: x.c.id, dim: d.id })} /></td>)}<td>{a.viktor ? <span className={`rag rag-${a.viktor.rating.toLowerCase()}`}>{a.viktor.rating}</span> : <span className="hint">—</span>}</td></tr>; })}</tbody></table></div>
      <div className="grid-legend"><span><i className="level-good" />Fine</span><span><i className="level-middle" />Slipping / watch</span><span><i className="level-worst" />Worst state</span><span><i className="level-unavailable" />Unavailable (no access)</span><span><i className="level-na" />Not applicable</span></div></Panel>}

    {view === 'engagement' && <><div className="toolbar"><Segmented label="Category" value={cat} onChange={setCat} options={[{ id: 'all', label: 'All', count: cats.length }, ...CATEGORIES.map(c => ({ id: c, label: c, count: cats.filter(x => x.category === c).length }))]} /></div>
      <div className="engagement-list">{sorted.filter(x => cat === 'all' || x.category === cat).map(x => <EngagementCard key={x.c.id} id={x.c.id} props={props} />)}{!sorted.some(x => cat === 'all' || x.category === cat) && <Empty title={`No clients are ${cat}`}>Unassessed appears when a client has too little coverage to judge.</Empty>}</div></>}

    {view === 'leads' && <><div className="coverage-banner"><AlertTriangle size={15} /><p>Lead outcomes need read access to each client’s LeadLock location (decision H6). Rosewood is shown as if access were granted; Harbor shows the unavailable state. Clients without LeadLock aren’t listed.</p></div><div className="engagement-list">{CLIENTS.map(c => <LeadOutcomes key={c.id} id={c.id} props={props} />)}</div></>}

    {view === 'voice' && <VoiceFeed props={props} />}

    {cell && (() => { const a = assessmentFor(cell.id); const d = DIMENSIONS.find(x => x.id === cell.dim)!; return <Dialog title={d.label} subtitle={clientById(cell.id).name} drawer onClose={() => setCell(null)}><div className="drawer-badges"><DimChip s={a.dims[cell.dim]} /></div><Drivers s={a.dims[cell.dim]} props={props} /><p className="hint">Fact = calculated from records. Interpretation = AI reading of the evidence.</p><button className="text-button" onClick={() => { setCell(null); props.openClient(cell.id, 'health'); }}>Open the client’s Health tab<ArrowRight size={12} /></button></Dialog>; })()}
    {posting && <Dialog title="Post the Monday review" subtitle="#monday-ads-meeting (internal)" className="slack-dialog" onClose={() => setPosting(false)}><p className="hint">Internal channel only. Review before sending.</p><textarea rows={12} value={mondayText} onChange={e => setMondayText(e.target.value)} /><div className="slack-footer"><span className="hint">Sent as the WIA KB Slack app on behalf of <strong>{props.viewer}</strong>. Preview only.</span><button className="button button-primary" onClick={() => { setPosting(false); props.notify('Monday review posted to #monday-ads-meeting. Preview only: nothing was posted.'); }}><Send size={14} />Send</button></div></Dialog>}
  </div>;
}

export function ClientHealth(props: WorkspaceProps & { clientId: string }) {
  const a = assessmentFor(props.clientId);
  return <>
    <div className="health-sub-head"><span className="small-label">CATEGORY, LAST 8 WEEKS</span><Trend a={a} /></div>
    <EngagementCard id={props.clientId} props={props} compact />
    {a.dims.leads.level !== 'na' && <LeadOutcomes id={props.clientId} props={props} />}
    <VoiceFeed clientId={props.clientId} props={props} />
  </>;
}
