import { ThemedSelect } from '../components/ThemedSelect';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AlertTriangle, ArrowRight, Ban, CalendarDays, Check, CheckCircle2, Clipboard, Clock3, Download, FileText, History, ListPlus, Mail, Printer, RefreshCw, Send, Sparkles, Target, UserRound, Wand2 } from 'lucide-react';
import { DEMO_DATE, EVIDENCE, VIEWERS, addDays, clientById, dateLabel, isOutstanding, isOverdue, ownerLabel, timeLabel } from '../data';
import { recordFor } from '../records';
import { isFinanceAdmin } from '../finance';
import { assessmentFor } from '../health';
import { CALL_META, RECAPS, SECTION_LABELS, TEMPLATES, TIMEZONES, UNMATCHED_EVENTS, templateFor, type Brief, type CallMeta, type CallTypeKey, type SectionKey } from '../calls';
import { Avatar, Badge, Dialog, Empty, PageHeading, Panel, SourceLink } from '../components/UI';
import { CategoryChip } from './Health';
import type { Tone, WorkspaceProps } from '../types';
import './CallPrep.css';

type Instr = { focusText: string; focusChips: string[]; tone: string[]; toneText: string; hidden: SectionKey[]; scope: 'call' | 'template'; refused: string[] };
type Version = { n: number; by: string; at: string; instr: Instr | null; note?: string };
export const FOCUS_CHIPS = ['Last call only', 'Since onboarding', 'Client’s open asks', 'Support issues', 'Lead outcomes', 'Commitments only'];
export const TONE_CHIPS = ['Shorter', 'More detail', 'Bullets only', 'More direct', 'Softer, relationship-first', 'For a new team member'];
const STATE_TONE: Record<string, Tone> = { Ready: 'green', Stale: 'amber', Scheduled: 'blue', 'Needs type': 'gold', Cancelled: 'neutral' };

const nowLabel = () => '10:12 AM';
const clientTime = (m: CallMeta) => { const tz = TIMEZONES[m.clientId]; const [h, mi] = m.time.split(':').map(Number); let t = h * 60 + mi + tz.offsetFromIST * 60; t = ((t % 1440) + 1440) % 1440; const hh = Math.floor(t / 60), mm = Math.round(t % 60); return `${tz.label}: ${hh % 12 || 12}:${String(mm).padStart(2, '0')} ${hh >= 12 ? 'PM' : 'AM'}`; };
const describe = (i: Instr | null) => !i ? 'Default template' : [i.focusChips.join(', '), i.focusText && `focus “${i.focusText}”`, [...i.tone, i.toneText].filter(Boolean).join(', '), i.hidden.length ? `hid ${i.hidden.length} section${i.hidden.length > 1 ? 's' : ''}` : ''].filter(Boolean).join(' · ');

export function refusals(text: string, viewer: string) {
  const out: string[] = [];
  if (/website|instagram|facebook page|google search|their site/i.test(text)) out.push('Website and social research isn’t an approved source, so that part was skipped.');
  if (/invoice|payment|paid|overdue bill|contract value|price|fee/i.test(text) && !isFinanceAdmin(viewer)) out.push(`Finance is admins only; ${viewer} can’t add invoice or payment details.`);
  return out;
}

export default function CallPrep(props: WorkspaceProps & { selectedId?: string }) {
  const role = VIEWERS.find(v => v.name === props.viewer)!;
  const [view, setView] = useState('queue');
  const [scope, setScope] = useState<string>(role.defaultScope);
  const firstViewer = useRef(true);
  useEffect(() => { if (firstViewer.current) { firstViewer.current = false; return; } setScope(role.defaultScope); }, [role]);
  const [range, setRange] = useState('week');
  const [versions, setVersions] = useState<Record<string, Version[]>>(() => Object.fromEntries(CALL_META.filter(m => m.brief && m.state !== 'Scheduled').map(m => [m.id, [{ n: 1, by: 'KB (automatic)', at: m.builtAt ? dateLabel(m.builtAt.slice(0, 10)) + ' ' + (m.builtAt.slice(11) === '19:00' ? '7:00 PM' : '8:10 AM') : '', instr: null }]])));
  const [current, setCurrent] = useState<Record<string, number>>({});
  const [fresh, setFresh] = useState<Set<string>>(new Set());
  const [types, setTypes] = useState<Record<string, CallTypeKey>>({});
  const [prepDone, setPrepDone] = useState<Set<string>>(new Set());
  const [regen, setRegen] = useState(false);
  const [agendaFor, setAgendaFor] = useState<CallMeta | null>(null);
  const [slackDigest, setSlackDigest] = useState(false);
  const [suggestions, setSuggestions] = useState<{ type: CallTypeKey; by: string; text: string }[]>([]);
  const [recapId, setRecapId] = useState(RECAPS[0]?.id ?? '');
  const [staleSim, setStaleSim] = useState<Record<string, string>>({});

  const inScope = (m: CallMeta) => scope === 'all' || m.host === props.viewer || m.attendees.includes(props.viewer);
  const inRange = (m: CallMeta) => range === 'today' ? m.date === DEMO_DATE : range === 'tomorrow' ? m.date === addDays(DEMO_DATE, 1) : m.date >= DEMO_DATE && m.date <= addDays(DEMO_DATE, 6);
  const calls = CALL_META.filter(m => inScope(m) && inRange(m)).sort((a, b) => `${a.date}${a.time}`.localeCompare(`${b.date}${b.time}`));
  const selected = calls.find(c => c.id === props.selectedId) || calls[0];
  const typeOf = (m: CallMeta) => types[m.id] || m.type;
  const stateOf = (m: CallMeta) => staleSim[m.id] ? 'Stale' : m.state === 'Cancelled' ? 'Cancelled' : types[m.id] && m.state === 'Needs type' ? 'Ready' : m.state === 'Needs type' ? 'Needs type' : fresh.has(m.id) ? 'Ready' : versions[m.id]?.length ? m.state === 'Scheduled' ? 'Ready' : m.state : m.state;
  const addVersion = (id: string, v: Omit<Version, 'n'>) => { setVersions(x => { const list = x[id] || []; return { ...x, [id]: [...list, { ...v, n: list.length + 1 }] }; }); setCurrent(c => ({ ...c, [id]: (versions[id]?.length || 0) + 1 })); setFresh(f => new Set([...f, id])); };
  const today = CALL_META.filter(m => m.date === DEMO_DATE && inScope(m) && m.state !== 'Cancelled');

  return <div className="view callprep-view">
    <PageHeading eyebrow="STAGE 2 · BEFORE AND AFTER EACH CLIENT CALL" title="Call preparation" description="A short brief shaped by the type of call, cited line by line. Ask for a new version any time, and close the loop after the call." />
    <div className="register-topbar"><p className="sync-line"><RefreshCw size={12} />Calendar synced 9:41 AM · times in IST (viewer); hover for the client’s time</p></div>
    <div className="register-tabs" role="tablist">{[['queue', 'Calls & briefs'], ['after', 'After the call'], ['templates', 'Call-type templates']].map(([id, label]) => <button key={id} role="tab" aria-selected={view === id} className={view === id ? 'selected' : ''} onClick={() => setView(id)}>{label}{id === 'templates' && suggestions.length > 0 && <span>{suggestions.length}</span>}</button>)}</div>

    {view === 'queue' && <>
      <Panel className="digest-panel" title="Morning prep" eyebrow={`7:00 AM · FOR ${props.viewer.toUpperCase()}`} action={<label className="switch-row"><input type="checkbox" checked={slackDigest} onChange={e => setSlackDigest(e.target.checked)} />Also DM me on Slack</label>}>
        {today.length ? <ul className="digest-list">{today.map(m => { const b = m.brief; return <li key={m.id}><strong>{timeLabel(m.time)}</strong><span>{clientById(m.clientId).name} · {templateFor(typeOf(m)).name}</span><span className="hint">{b?.thirty[1] || 'Brief pending'}</span></li>; })}</ul> : <p className="hint">No client calls today for {props.viewer}.</p>}
      </Panel>
      <div className="toolbar"><div className="drawer-inline"><div className="segmented" role="group">{[['mine', 'My calls'], ['all', 'All calls']].map(([id, l]) => <button key={id} className={scope === id ? 'selected' : ''} onClick={() => setScope(id)}>{l}</button>)}</div><div className="segmented" role="group">{[['today', 'Today'], ['tomorrow', 'Tomorrow'], ['week', 'This week']].map(([id, l]) => <button key={id} className={range === id ? 'selected' : ''} onClick={() => setRange(id)}>{l}</button>)}</div></div><button className="text-button" onClick={() => props.notify(`${UNMATCHED_EVENTS} calendar events couldn’t be matched to a client. In the real app this opens the list to match or dismiss them.`)}><AlertTriangle size={12} />{UNMATCHED_EVENTS} events not matched to a client</button></div>
      <div className="call-workspace">
        <aside className="call-list"><p className="small-label">ON THE CALENDAR</p>{calls.length ? calls.map(m => { const c = clientById(m.clientId); const st = stateOf(m); const open = props.actions.filter(a => a.clientId === m.clientId && isOutstanding(a)); const asks = m.brief?.asks.length || 0; return <button key={m.id} className={`call-list-item ${selected?.id === m.id ? 'active' : ''} ${st === 'Cancelled' ? 'cancelled' : ''}`} onClick={() => props.openCall(m.id)}>
          <div className="call-list-date"><span>{m.date === DEMO_DATE ? 'TODAY' : dateLabel(m.date).toUpperCase()}</span><strong title={clientTime(m)}>{timeLabel(m.time)}</strong></div>
          <div className="call-list-client"><Avatar client={c} small /><div><h3>{c.name}</h3><p>{templateFor(typeOf(m)).name}{m.typeSource === 'Proposed by KB' && !types[m.id] ? ' · proposed' : ''}</p></div></div>
          <div className="call-signals">{asks > 0 && st !== 'Cancelled' && <span className="row-flag flag-blue">{asks} open ask{asks > 1 ? 's' : ''}</span>}{open.some(isOverdue) && st !== 'Cancelled' && <span className="row-flag flag-amber">overdue promise</span>}{prepDone.has(m.id) && <span className="row-flag"><Check size={10} />prepped</span>}</div>
          <div className="call-list-bottom"><span>{m.host} · {m.duration}</span><Badge tone={STATE_TONE[st]} dot={false}>{st}</Badge></div>
        </button>; }) : <Empty title="No calls in this range">{scope === 'mine' ? `${props.viewer} isn’t on any calls in this range.` : ''}</Empty>}</aside>
        {selected ? <BriefPanel {...props} m={selected} type={typeOf(selected)} state={stateOf(selected)} versions={versions[selected.id] || []} currentN={current[selected.id] || versions[selected.id]?.length || 0}
          setCurrentN={n => setCurrent(c => ({ ...c, [selected.id]: n }))} prepDone={prepDone.has(selected.id)} togglePrep={() => setPrepDone(s => { const n = new Set(s); if (n.has(selected.id)) n.delete(selected.id); else n.add(selected.id); return n; })}
          onBuild={() => addVersion(selected.id, { by: `${props.viewer} (built early)`, at: nowLabel(), instr: null })}
          onRebuild={() => { const last = (versions[selected.id] || []).slice(-1)[0]; const why = staleSim[selected.id] ? 'a new client message' : 'the action went overdue'; addVersion(selected.id, { by: 'KB (automatic rebuild)', at: nowLabel(), instr: last?.instr || null, note: last?.instr ? `Rebuilt with ${last.by.split(' ')[0]}’s instructions after ${why}.` : `Rebuilt after ${why}.` }); setStaleSim(x => { const n = { ...x }; delete n[selected.id]; return n; }); props.notify(last?.instr ? 'Brief rebuilt with the same instructions.' : 'Brief rebuilt.'); }}
staleNote={staleSim[selected.id]} simulateChange={() => setStaleSim(x => ({ ...x, [selected.id]: `New message from ${clientById(selected.clientId).contact.split(' ')[0]} at 11:05 AM (demo).` }))}
          onConfirmType={t => { setTypes(x => ({ ...x, [selected.id]: t })); addVersion(selected.id, { by: `KB after ${props.viewer} set the type`, at: nowLabel(), instr: null }); props.notify('Type confirmed; brief built from that template.'); }}
          openRegen={() => setRegen(true)} openAgenda={() => setAgendaFor(selected)} /> : <Empty title="No call selected" />}
      </div>
    </>}

    {view === 'after' && <AfterTheCall {...props} recapId={recapId} setRecapId={setRecapId} />}
    {view === 'templates' && <Templates viewer={props.viewer} notify={props.notify} suggestions={suggestions} resolve={(i, ok) => { setSuggestions(s => s.filter((_, j) => j !== i)); props.notify(ok ? 'Template updated (versioned; tested before release).' : 'Suggestion dismissed.'); }} />}

    {regen && selected && <RegenDialog viewer={props.viewer} m={selected} type={typeOf(selected)} close={() => setRegen(false)} last={(versions[selected.id] || []).find(v => v.n === (current[selected.id] || versions[selected.id]?.length))?.instr || null}
      submit={instr => { setRegen(false); addVersion(selected.id, { by: props.viewer, at: nowLabel(), instr }); if (instr.scope === 'template') setSuggestions(s => [...s, { type: typeOf(selected), by: props.viewer, text: describe(instr) }]); props.notify(instr.scope === 'template' ? 'New version built. Your instructions were also sent to admins as a template suggestion.' : 'New version built with your instructions.'); }} />}
    {agendaFor && <AgendaEmail m={agendaFor} viewer={props.viewer} close={() => setAgendaFor(null)} notify={props.notify} />}
  </div>;
}

function BriefPanel(props: WorkspaceProps & { m: CallMeta; type: CallTypeKey; state: string; versions: Version[]; currentN: number; setCurrentN: (n: number) => void; prepDone: boolean; togglePrep: () => void; onBuild: () => void; onRebuild: () => void; staleNote?: string; simulateChange: () => void; onConfirmType: (t: CallTypeKey) => void; openRegen: () => void; openAgenda: () => void }) {
  const { m } = props; const c = clientById(m.clientId); const t = templateFor(props.type);
  const [pickType, setPickType] = useState<CallTypeKey>('checkin');
  const v = props.versions.find(x => x.n === props.currentN);
  const head = <div className="call-brief-heading"><div><p className="eyebrow">YOUR CALL BRIEF</p><h2>{c.name}</h2><p className="hint">{m.title}</p><div className="call-meta"><span><CalendarDays size={13} />{dateLabel(m.date)}</span><span title={clientTime(m)}><Clock3 size={13} />{timeLabel(m.time)} IST</span><span><UserRound size={13} />{m.host} · {m.attendees.join(', ')}</span></div></div><div className="call-heading-right"><Badge tone={STATE_TONE[props.state]}>{props.state}</Badge></div></div>;
  const typeLine = <div className="call-type-line"><Badge tone="blue" dot={false}>{t.name}</Badge><span className="hint">{m.typeSource === 'Proposed by KB' && props.state === 'Needs type' ? 'Proposed by KB' : `Type from ${m.typeSource === 'Calendar title' ? 'the calendar title' : 'host confirmation'}`} · {m.duration}</span><CategoryChip id={m.clientId} /><button className="text-button" onClick={() => props.openClient(m.clientId)}>Client record<ArrowRight size={13} /></button>{props.ask && <button className="text-button" onClick={() => props.ask!({ kind: 'call', clientId: m.clientId, id: m.id, label: m.title })}>Ask about this call<ArrowRight size={13} /></button>}</div>;
  if (props.state === 'Cancelled') return <div className="call-brief">{head}<div className="coming-soon-box"><Ban size={22} /><div><h3>Call cancelled</h3><p>{m.stateNote}</p><p className="hint">A future invite is never treated as a call that happened.</p></div></div></div>;
  if (props.state === 'Needs type') return <div className="call-brief">{head}<div className="coverage-banner suggestion"><Sparkles size={15} /><p>{m.stateNote} Without a confirmed type the brief would guess what the call needs, so it isn’t built yet.</p></div><div className="drawer-inline"><ThemedSelect aria-label="Call type" value={pickType} onChange={v => setPickType(v as CallTypeKey)}>{TEMPLATES.map(x => <option key={x.key} value={x.key}>{x.name}</option>)}</ThemedSelect><button className="button button-small button-primary" onClick={() => props.onConfirmType(pickType)}><Check size={13} />Confirm type & build</button></div></div>;
  if (v && !m.brief) return <div className="call-brief">{head}{typeLine}<div className="coverage-banner"><RefreshCw size={15} /><p>Building the brief from the “{t.name}” template…</p></div></div>;
  if (!v) return <div className="call-brief">{head}{typeLine}<div className="coverage-banner"><Clock3 size={15} /><p>{m.stateNote} You can build it now; it will still refresh automatically if anything changes.</p><button className="button button-small button-primary" onClick={props.onBuild}>Build now</button></div></div>;
  return <div className="call-brief">{head}{typeLine}
    {props.state === 'Stale' && <div className="stale-note stale-banner"><AlertTriangle size={13} /><span>{props.staleNote || m.stateNote} This version is still shown until the rebuild finishes.</span><button className="button button-small button-outline" onClick={props.onRebuild}><RefreshCw size={12} />Rebuild now</button></div>}
    <div className="version-bar"><History size={13} /><ThemedSelect aria-label="Brief version" value={String(props.currentN)} onChange={n => props.setCurrentN(Number(n))}>{props.versions.map(x => <option key={x.n} value={String(x.n)}>{`v${x.n} · ${x.by} · ${x.at}${x.n === props.versions.length ? ' (latest)' : ''}`}</option>)}</ThemedSelect><button className="text-button demo-btn" onClick={props.simulateChange} title="Demo only">Simulate a new client message</button><button className="button button-small button-primary" onClick={props.openRegen}><Wand2 size={13} />Regenerate with instructions…</button></div>
    {v.instr && <div className="instr-banner"><Wand2 size={13} /><div><strong>Instructions for v{v.n}:</strong> {describe(v.instr)}{v.instr.scope === 'template' && <em> · also suggested for the template</em>}{v.note && <p className="hint">{v.note}</p>}{v.instr.refused.map(r => <p key={r} className="refused"><Ban size={11} />{r}</p>)}</div></div>}
    {!v.instr && v.note && <p className="hint">{v.note}</p>}
    <BriefBody key={m.id + v.n} {...props} brief={m.brief!} instr={v.instr} />
    <div className="call-footer brief-actions-bar"><button className={`button button-small ${props.prepDone ? 'button-primary' : 'button-outline'}`} onClick={props.togglePrep}><CheckCircle2 size={13} />{props.prepDone ? 'Prep done' : 'Mark prep done'}</button><button className="button button-small button-outline" onClick={props.openAgenda}><Mail size={13} />Send agenda to client…</button><button className="button button-small button-outline" onClick={() => copyBrief(props, v)}><Clipboard size={13} />Copy</button><button className="button button-small button-outline" onClick={() => downloadBrief(props, v)}><Download size={13} />Download</button><button className="button button-small button-outline" onClick={() => window.print()}><Printer size={13} />Print</button></div>
  </div>;
}

function BriefBody(props: WorkspaceProps & { m: CallMeta; type: CallTypeKey; brief: Brief; instr: Instr | null }) {
  const { brief: b, instr, m } = props; const c = clientById(m.clientId); const r = recordFor(m.clientId);
  const tone = new Set(instr?.tone || []); const chips = new Set(instr?.focusChips || []);
  const short = tone.has('Shorter'); const detail = tone.has('More detail'); const bullets = tone.has('Bullets only');
  const lim = <T,>(xs: T[]) => short ? xs.slice(0, 2) : xs;
  let order: SectionKey[] = templateFor(props.type).sections.filter(s => !(instr?.hidden || []).includes(s));
  if (chips.has('Commitments only')) order = order.filter(s => s === 'owed' || s === 'limits');
  if (chips.has('Client’s open asks')) order = ['asks', ...order.filter(s => s !== 'asks')];
  const [open, setOpen] = useState<Set<SectionKey>>(new Set());
  const more = (k: SectionKey) => b.more[k] && <>{(detail || open.has(k)) ? <p className="more-text">{b.more[k]}</p> : <button className="text-button" onClick={() => setOpen(s => new Set([...s, k]))}>More detail</button>}</>;
  const actions = props.actions.filter(a => a.clientId === m.clientId && isOutstanding(a));
  const since = chips.has('Last call only') ? b.since.slice(0, 1) : b.since;
  const focusHits = instr?.focusText ? [...EVIDENCE.filter(e => e.clientId === m.clientId && instr.focusText.toLowerCase().split(/\W+/).filter(w => w.length > 3 && !['focus', 'also', 'their', 'check', 'with', 'about', 'what'].includes(w)).some(w => `${e.title} ${e.excerpt}`.toLowerCase().includes(w.slice(0, 6))))] : [];
  const render: Record<SectionKey, ReactNode> = {
    since: <section className="brief-section" key="since"><h3>{SECTION_LABELS.since}</h3>{chips.has('Since onboarding') && <p className="hint">Including onboarding: started {dateLabel(r.engagements[0].start)}; {r.meetings.length} recorded meetings.</p>}<ul className="brief-list">{lim(since).map(s => <li key={s.text}><span className="hint">{dateLabel(s.date)}</span> {s.text} {s.sourceId && <SourceLink id={s.sourceId} onOpen={props.showEvidence} />}</li>)}</ul>{more('since')}</section>,
    asks: <section className="brief-section" key="asks"><h3>{SECTION_LABELS.asks}</h3>{b.asks.length ? lim(b.asks).map(a => <blockquote className="origin-quote" key={a.quote}>“{a.quote}”<footer>{a.who} · {dateLabel(a.date)} {a.sourceId && <SourceLink id={a.sourceId} onOpen={props.showEvidence} />}</footer></blockquote>) : <p className="hint">No open client asks.</p>}</section>,
    owed: <section className="brief-section" key="owed"><h3>{SECTION_LABELS.owed}</h3><div className="owed-cols"><div><p className="small-label">WIA OWES</p>{actions.filter(a => a.side === 'WIA').map(a => <p key={a.id} className={isOverdue(a) ? 'text-amber' : ''}>• {a.title} <span className="hint">· {ownerLabel(a.owner)} · {a.due ? dateLabel(a.due) : 'no date'}</span></p>)}</div><div><p className="small-label">CLIENT OWES</p>{actions.filter(a => a.side === 'Client').map(a => <p key={a.id}>• {a.title} <span className="hint">· {a.due ? dateLabel(a.due) : 'no date'}</span></p>)}</div></div></section>,
    agenda: <section className="brief-section" key="agenda"><h3>{SECTION_LABELS.agenda}</h3><ol className="agenda-list">{(tone.has('Softer, relationship-first') ? [...b.agenda].sort((x, y) => Number(/ask|question/i.test(y.why)) - Number(/ask|question/i.test(x.why))) : b.agenda).map((a, i) => <li key={a.item}><span>{String(i + 1).padStart(2, '0')}</span><p>{a.item}{!bullets && !short && <small className="block hint">Why: {a.why}</small>}</p></li>)}</ol>{more('agenda')}</section>,
    questions: b.questions.length ? <section className="brief-section" key="questions"><h3>{SECTION_LABELS.questions}</h3><ul className="brief-list">{lim(b.questions).map(q => <li key={q}>{q}</li>)}</ul></section> : null,
    watch: b.watch.length ? <section className="brief-section watch-section" key="watch"><h3>{tone.has('Softer, relationship-first') ? 'Handle with care' : SECTION_LABELS.watch}</h3><ul className="brief-list">{lim(b.watch).map(w => <li key={w}>{w}</li>)}</ul>{more('watch')}</section> : null,
    opportunity: b.opportunity ? <div className="insight-box" key="opportunity"><Sparkles size={19} /><div><h4>One opportunity · proposal</h4><p>{b.opportunity.text}</p>{!short && <small>Why it’s top: {b.opportunity.why}</small>}{b.opportunity.sourceId && <SourceLink id={b.opportunity.sourceId} onOpen={props.showEvidence} />}</div></div> : null,
    typeBlock: b.typeBlock.length ? <section className="brief-section" key="typeBlock"><h3>{templateFor(props.type).typeBlock || 'Context'}</h3><dl className="terms-list">{b.typeBlock.filter(x => isFinanceAdmin(props.viewer) || !/invoice|payment/i.test(x.label)).map(x => <div key={x.label}><dt>{x.label}</dt><dd>{x.value}</dd></div>)}</dl></section> : null,
    limits: <section className="brief-section limits-section" key="limits"><h3>{SECTION_LABELS.limits}</h3><ul className="brief-list">{b.limits.map(l => <li key={l}>{l}</li>)}</ul></section>,
  };
  return <>
    <div className={`thirty-box ${tone.has('More direct') ? 'direct' : ''}`}><Target size={18} /><div><p className="small-label">{tone.has('More direct') ? 'BOTTOM LINE' : 'IN 30 SECONDS'}</p><ul>{(short ? b.thirty.slice(0, 2) : b.thirty).map(x => <li key={x}>{x}</li>)}</ul></div></div>
    {tone.has('For a new team member') && <section className="brief-section new-member"><h3>Context for someone new</h3><p>{c.story}</p><p className="hint">People: {r.contacts.map(p => `${p.name} (${p.role})`).join('; ')}. Account owner: {r.owner}.</p></section>}
    {instr?.focusText && <section className="brief-section focus-section"><h3>Your focus: “{instr.focusText}”</h3>{focusHits.length ? <ul className="brief-list">{focusHits.map(e => <li key={e.id}>{e.title} <span className="hint">· {dateLabel(e.date)}</span>: “{e.excerpt.split('\n')[0].slice(0, 160)}…” <SourceLink id={e.id} onOpen={props.showEvidence} /></li>)}</ul> : <p className="hint">Nothing in the approved sources mentions this for {c.name}. Said plainly rather than guessed.</p>}</section>}
    {chips.has('Support issues') && <section className="brief-section"><h3>Support issues</h3>{r.support.length ? <ul className="brief-list">{r.support.map(s => <li key={s.id}>{s.title} · {s.state} · {s.owner}</li>)}</ul> : <p className="hint">None found ({r.supportCoverage})</p>}</section>}
    {chips.has('Lead outcomes') && <section className="brief-section"><h3>Lead outcomes</h3>{assessmentFor(m.clientId).leadNumbers ? <p>Inquiries {assessmentFor(m.clientId).leadNumbers!.inquiries[0]} (prior {assessmentFor(m.clientId).leadNumbers!.inquiries[1]}) · bookings {assessmentFor(m.clientId).leadNumbers!.booked[0]}</p> : <p className="hint">{assessmentFor(m.clientId).dims.leads.level === 'na' ? 'Not a LeadLock client.' : 'Unavailable: LeadLock access pending.'}</p>}</section>}
    {order.map(k => render[k])}
  </>;
}

function briefText(props: WorkspaceProps & { m: CallMeta; type: CallTypeKey }, v: Version) {
  const b = props.m.brief!; const c = clientById(props.m.clientId);
  return `# ${c.name} · ${templateFor(props.type).name}\n${dateLabel(props.m.date)} ${timeLabel(props.m.time)} IST · host ${props.m.host}\nVersion ${v.n} (${v.by}, ${v.at})${v.instr ? ` · ${describe(v.instr)}` : ''}\n\n## In 30 seconds\n${b.thirty.map(x => `- ${x}`).join('\n')}\n\n## Agenda\n${b.agenda.map((a, i) => `${i + 1}. ${a.item}`).join('\n')}\n\n## They asked\n${b.asks.map(a => `- "${a.quote}" (${a.who}, ${a.date})`).join('\n') || '- None'}\n\n## Sources & limits\n${b.limits.map(l => `- ${l}`).join('\n')}\n`;
}
async function copyBrief(props: WorkspaceProps & { m: CallMeta; type: CallTypeKey }, v: Version) { try { await navigator.clipboard.writeText(briefText(props, v)); props.notify(`Brief v${v.n} copied.`); } catch { props.notify('Clipboard is unavailable. Use Download.'); } }
function downloadBrief(props: WorkspaceProps & { m: CallMeta; type: CallTypeKey }, v: Version) { const url = URL.createObjectURL(new Blob([briefText(props, v)], { type: 'text/markdown' })); const a = document.createElement('a'); a.href = url; a.download = `${props.m.clientId}-${props.m.date}-brief-v${v.n}.md`; a.click(); URL.revokeObjectURL(url); }

function RegenDialog({ viewer, m, type, last, close, submit }: { viewer: string; m: CallMeta; type: CallTypeKey; last: Instr | null; close: () => void; submit: (i: Instr) => void }) {
  const [focusText, setFocusText] = useState(last?.focusText || '');
  const [focusChips, setFocusChips] = useState<string[]>(last?.focusChips || []);
  const [tone, setTone] = useState<string[]>(last?.tone || []);
  const [toneText, setToneText] = useState(last?.toneText || '');
  const [hidden, setHidden] = useState<SectionKey[]>(last?.hidden || []);
  const [scope, setScope] = useState<'call' | 'template'>('call');
  const toggle = (_list: string[], set: (f: (x: string[]) => string[]) => void, v: string) => set(list => list.includes(v) ? list.filter(x => x !== v) : [...list, v]);
  const refused = refusals(`${focusText} ${toneText}`, viewer);
  return <Dialog title="Regenerate with instructions" subtitle={`${clientById(m.clientId).name} · ${templateFor(type).name}`} className="slack-dialog regen-dialog" onClose={close}>
    <div className="form-stack">
      <label>What else should it look at?<textarea rows={3} value={focusText} onChange={e => setFocusText(e.target.value)} placeholder="e.g. “focus on inquiry quality and what Sarah said about tours”, or “Danielle is joining, add the LeadLock setup status”" /></label>
      <div><p className="small-label">QUICK FOCUS</p><div className="chip-row">{FOCUS_CHIPS.map(ch => <button key={ch} type="button" className={`pick-chip ${focusChips.includes(ch) ? 'on' : ''}`} onClick={() => toggle(focusChips, setFocusChips, ch)}>{ch}</button>)}</div></div>
      <div><p className="small-label">TONE AND LENGTH</p><div className="chip-row">{TONE_CHIPS.map(ch => <button key={ch} type="button" className={`pick-chip ${tone.includes(ch) ? 'on' : ''}`} onClick={() => toggle(tone, setTone, ch)}>{ch}</button>)}</div></div>
      <label>Anything else about tone?<input value={toneText} onChange={e => setToneText(e.target.value)} placeholder="e.g. “write it as talking points I can read out”" /></label>
      <div><p className="small-label">SECTIONS IN THIS VERSION</p><div className="chip-row">{templateFor(type).sections.map(s => <button key={s} type="button" className={`pick-chip ${!hidden.includes(s) ? 'on' : ''}`} onClick={() => setHidden(h => h.includes(s) ? h.filter(x => x !== s) : [...h, s])}>{SECTION_LABELS[s]}</button>)}</div></div>
      <div className="scope-row"><label className="check-row"><input type="radio" checked={scope === 'call'} onChange={() => setScope('call')} />This call only</label><label className="check-row"><input type="radio" checked={scope === 'template'} onChange={() => setScope('template')} />Also suggest for the “{templateFor(type).name}” template (admins approve)</label></div>
      {refused.map(r => <p key={r} className="stale-note"><Ban size={13} />{r}</p>)}
      <p className="hint">Instructions can narrow or re-focus the brief, not widen it beyond approved sources or your access. Facts stay cited whatever the tone. Later automatic rebuilds keep these instructions.</p>
    </div>
    <div className="slack-footer"><span className="hint">Creates a new version; earlier versions stay available.</span><button className="button button-primary" onClick={() => submit({ focusText: focusText.trim(), focusChips, tone, toneText: toneText.trim(), hidden, scope, refused })}><Wand2 size={14} />Generate new version</button></div>
  </Dialog>;
}

function AgendaEmail({ m, viewer, close, notify }: { m: CallMeta; viewer: string; close: () => void; notify: (s: string) => void }) {
  const c = clientById(m.clientId); const first = c.contact.split(' ')[0];
  const [body, setBody] = useState(`Hi ${first},\n\nLooking forward to our call on ${dateLabel(m.date, { weekday: 'long', day: 'numeric', month: 'long' })}! Here's what I'd like us to cover:\n\n${m.brief!.agenda.map((a, i) => `${i + 1}. ${a.item}`).join('\n')}\n\nIf there's anything else you'd like to add, just reply to this email.\n\n${viewer}\nWedding Industry Ads`);
  return <Dialog title="Send agenda to client" subtitle={`${c.contact} <${c.email}>`} className="slack-dialog" onClose={close}><p className="hint">Drafted from the brief’s agenda, without internal notes or watch-outs. A person reviews and sends it from hello@.</p><textarea rows={12} value={body} onChange={e => setBody(e.target.value)} /><div className="slack-footer"><button className="button button-outline button-small" onClick={async () => { try { await navigator.clipboard.writeText(body); notify('Agenda copied.'); } catch { notify('Clipboard unavailable.'); } }}><Clipboard size={13} />Copy</button><button className="button button-primary" onClick={() => { close(); notify('Logged as sent. Preview only: nothing was emailed.'); }}><Check size={14} />I’ve sent it</button></div></Dialog>;
}

function AfterTheCall(props: WorkspaceProps & { recapId: string; setRecapId: (id: string) => void }) {
  const [email, setEmail] = useState<Record<string, string>>({});
  const [added, setAdded] = useState<Set<string>>(new Set());
  const [notes, setNotes] = useState('');
  const r = RECAPS.find(x => x.id === props.recapId);
  if (!r) return <Empty title="No call recaps yet">Recaps are drafted after a recorded call is extracted (Stage 2).</Empty>;
  const c = clientById(r.clientId);
  const body = email[r.id] ?? r.email;
  return <div className="call-workspace">
    <aside className="call-list"><p className="small-label">RECENT CALLS</p>{RECAPS.map(x => <button key={x.id} className={`call-list-item ${x.id === r.id ? 'active' : ''}`} onClick={() => props.setRecapId(x.id)}><div className="call-list-date"><span>{dateLabel(x.date).toUpperCase()}</span><Badge tone={x.transcript ? 'green' : 'amber'} dot={false}>{x.transcript ? 'Recap ready' : 'No transcript'}</Badge></div><div className="call-list-client"><Avatar client={clientById(x.clientId)} small /><div><h3>{clientById(x.clientId).name}</h3><p>{x.title}</p></div></div></button>)}</aside>
    <div className="call-brief">
      <div className="call-brief-heading"><div><p className="eyebrow">AFTER THE CALL</p><h2>{c.name}</h2><p className="hint">{r.title} · {dateLabel(r.date)} · {templateFor(r.type).name}</p></div>{r.sourceId && <SourceLink id={r.sourceId} onOpen={props.showEvidence} label="Transcript" />}</div>
      {!r.transcript ? <><div className="coverage-banner"><AlertTriangle size={15} /><p>The calendar shows this session happened, but no Fathom transcript or client segment was found. That doesn’t mean nothing was agreed.</p></div><label className="form-stack">Add notes by hand<textarea rows={5} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Decisions, asks and commitments from the call" /></label><button className="button button-small button-primary" onClick={() => props.notify('Notes saved with manual provenance; commitments go to Needs review.')}><Check size={13} />Save notes</button></> : <>
        <section className="brief-section"><h3>Decisions</h3><ul className="brief-list">{r.decisions.map(d => <li key={d}>{d}</li>)}</ul></section>
        <section className="brief-section"><h3>Commitments made</h3>{r.commitments.map(cm => <div className="commit-row" key={cm.text}><div><strong>{cm.text}</strong><p className="hint">{cm.who} · {cm.when}</p></div>{cm.status === 'In register' ? <Badge tone="green" dot={false}>In Action Hub</Badge> : added.has(cm.text) ? <Badge tone="blue" dot={false}>Sent to Needs review</Badge> : <button className="button button-small button-outline" onClick={() => { setAdded(s => new Set([...s, cm.text])); props.notify('Added to Needs review: no date was agreed on the call.'); }}><ListPlus size={13} />Add (proposal)</button>}</div>)}</section>
        {r.answered.length > 0 && <section className="brief-section"><h3>Asks answered on the call</h3><ul className="brief-list">{r.answered.map(a => <li key={a}><Check size={11} /> {a}</li>)}</ul></section>}
        <section className="brief-section"><h3>Brief vs reality</h3><ul className="covered-list">{r.covered.map(x => <li key={x.item} className={x.done ? 'done' : ''}>{x.done ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}{x.item}{!x.done && <span className="hint"> · not covered, carried to the next brief</span>}</li>)}</ul></section>
        <section className="brief-section"><h3>Follow-up email to {c.contact.split(' ')[0]}</h3><p className="hint">Drafted from the recap. A person reviews and sends it from hello@.</p><textarea className="email-box" rows={10} value={body} onChange={e => setEmail(x => ({ ...x, [r.id]: e.target.value }))} /><div className="drawer-inline"><button className="button button-small button-outline" onClick={async () => { try { await navigator.clipboard.writeText(body); props.notify('Email copied.'); } catch { props.notify('Clipboard unavailable.'); } }}><Clipboard size={13} />Copy</button><button className="button button-small button-primary" onClick={() => props.notify('Logged as sent. Preview only: nothing was emailed.')}><Check size={13} />I’ve sent it</button><button className="button button-small button-outline" onClick={() => props.notify(`Preview only: would open the Slack review screen to post a recap to ${recordFor(r.clientId).links.slack}.`)}><Send size={13} />Team recap on Slack…</button></div></section>
      </>}
    </div>
  </div>;
}

function Templates({ viewer, notify, suggestions, resolve }: { viewer: string; notify: (s: string) => void; suggestions: { type: CallTypeKey; by: string; text: string }[]; resolve: (i: number, ok: boolean) => void }) {
  const admin = isFinanceAdmin(viewer);
  return <>
    {suggestions.length > 0 && <Panel title="Suggested changes" eyebrow="FROM REGENERATED BRIEFS · ADMINS APPROVE">{suggestions.map((s, i) => <div className="mini-row" key={i}><Wand2 size={14} /><div><strong>{templateFor(s.type).name}</strong><p className="hint">{s.by}: {s.text}</p></div>{admin ? <div className="drawer-inline"><button className="button button-small button-primary" onClick={() => resolve(i, true)}>Apply</button><button className="text-button" onClick={() => resolve(i, false)}>Dismiss</button></div> : <span className="hint">Admins review</span>}</div>)}</Panel>}
    <div className="agreement-grid">{TEMPLATES.map(t => <article className="panel template-card" key={t.key}><div className="agreement-head template-head"><FileText size={16} /><div><h3>{t.name}</h3><p className="hint">{t.detect}</p></div>{admin ? <button className="text-button" onClick={() => notify('Template edits are versioned and tested before release.')}>Edit</button> : <span className="hint">View only</span>}</div><p><strong>Purpose:</strong> {t.purpose}</p><p className="small-label">SECTIONS</p><div className="chip-row">{t.sections.map(s => <span key={s} className="pick-chip on static">{SECTION_LABELS[s]}</span>)}</div>{t.agenda.length > 0 && <><p className="small-label">AGENDA SKELETON</p><ol className="brief-list numbered">{t.agenda.map(a => <li key={a}>{a}</li>)}</ol></>}<p className="hint"><strong>Leave out:</strong> {t.leaveOut}</p></article>)}</div>
    <p className="hint">Sales calls have no template: they’re outside the knowledge base.</p>
  </>;
}

