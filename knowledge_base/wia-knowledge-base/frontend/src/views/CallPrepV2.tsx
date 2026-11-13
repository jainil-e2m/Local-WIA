import { useEffect, useState, type ReactNode } from 'react';
import kbLive from '@kb-live';
import { AlertTriangle, ArrowLeft, Lock, Plus, RotateCcw, X, ShieldCheck, Ban, Wand2, LayoutGrid, List, ArrowRight, BarChart3, CalendarDays, Check, ChevronRight, Clock3, ExternalLink, FileText, Lightbulb, ListChecks, MessageSquareQuote, RefreshCw, ShieldAlert, Target, TrendingDown, TrendingUp, Users } from 'lucide-react';
import { CALLS, DEMO_DATE, TEAM, VIEWERS, addDays, clientById, dateLabel, daysBetween, isOutstanding, isOverdue, sourceById } from '../data';
import { CALL_META, DEFAULT_SKILL_SPEC, EXCLUDED_CALLS, RECAPS, SECTION_LABELS, SKILL_FILES, TEMPLATES, TIMEZONES, resetSkill, saveSkill, skillEdits, skillFor, templateFor, type AdPlatform, type Brief, type CallMeta, type CallTypeKey, type LiveVersion, type SectionKey, type Skill, type SkillKey } from '../calls';
import { RECORDS } from '../records';
import { assessmentFor, categoryOf } from '../health';
import { PERFORMANCE, perfStatus, type ChannelPerf } from '../performance';
import { Avatar, Dialog, SourceIcon } from '../components/UI';
import { refusals } from './CallPrep';
import { ThemedSelect } from '../components/ThemedSelect';
import type { Action, WorkspaceProps } from '../types';
import './CallPrepV2.css';
import { me } from '../auth';

/*
 * Call Preparation v2. The Overview is a one-minute read: the goal of the call, an account pulse,
 * what to settle, what changed, the top talking points, one watch-out and what the brief couldn't see.
 * Everything else (last call, full changes, performance, asks & owed, all talking points, sources) sits in sub-tabs.
 * In production each call type is a skill that fills the same sections; this mock reads the sample records.
 */

// Live (the deployed portfolio): facts come computed from the KB, brief text from stored versions, and every change
// goes to the call prep API (backend/routes/callprep.py). The sample build keeps computing everything here.
const LIVE = !!kbLive.meta;
async function api<T>(path: string, method: 'GET' | 'POST' | 'PUT' = 'GET', body?: unknown): Promise<T> {
  const res = await fetch(path, body === undefined ? { method } : { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail?.message || `The KB answered ${res.status}.`);
  return data as T;
}
const toVersion = (v: LiveVersion): BriefVersion => ({ n: v.n, by: v.by, at: v.at, skill: v.skill, prompt: v.prompt, refused: v.declined ? [v.declined] : [] });
const keyOf = (name: string) => TEMPLATES.find(t => t.name === name)?.key;

type Tab = 'overview' | 'last' | 'changed' | 'performance' | 'owed' | 'points' | 'sources';
const TABS: [Tab, string][] = [['overview', 'Overview'], ['last', 'Last call'], ['changed', 'What’s changed'], ['performance', 'Performance'], ['owed', 'Asks & owed'], ['points', 'Talking points'], ['sources', 'Sources']];

const strip = (s: string, prefix: RegExp) => { const t = s.replace(prefix, '').trim(); return t.charAt(0).toUpperCase() + t.slice(1); };
const ago = (date: string) => { const d = daysBetween(date); return d === 0 ? 'today' : d === 1 ? '1 day ago' : `${d} days ago`; };
const until = (date: string) => { const d = daysBetween(DEMO_DATE, date); return d === 0 ? 'Today' : d === 1 ? 'Tomorrow' : d < 0 ? `${-d} days ago` : `In ${d} days`; };
const time12 = (t: string) => { const [h, m] = t.split(':').map(Number); return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`; };
const endTime = (t: string, duration: string) => { const [h, m] = t.split(':').map(Number); const total = h * 60 + m + parseInt(duration, 10); return time12(`${Math.floor(total / 60) % 24}:${total % 60}`); };
const isClientPerson = (name: string) => !!name && !TEAM.includes(name);
const initials = (name: string) => name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
const money = (n: number) => `$${n.toLocaleString('en-US')}`;

// Briefs build automatically 2 hours before each call with the default skill; the call-type skill runs on demand.
// Preview clock: the sample day (Oct 9) at 12:30 PM, so some of today's briefs are built and some aren't yet.
const NOW = '12:30';
const DEFAULT_SKILL = 'Default call prep';
const typeOverride = new Map<string, CallTypeKey>();
const typeOf = (c: CallMeta) => typeOverride.get(c.id) ?? c.type;
const typeConfirmed = (c: CallMeta) => typeOverride.has(c.id) || c.typeSource === 'Calendar title';
const autoBuildAt = (c: CallMeta) => {
  const [h, m] = c.time.split(':').map(Number); const t = h * 60 + m - 120;
  const mins = ((t % 1440) + 1440) % 1440;
  return { date: t < 0 ? addDays(c.date, -1) : c.date, time: `${String(Math.floor(mins / 60)).padStart(2, '0')}:${String(mins % 60).padStart(2, '0')}` };
};
const autoBuilt = (c: CallMeta) => {
  if (!c.brief || c.state === 'Cancelled' || c.state === 'Needs type') return false;
  const b = autoBuildAt(c);
  return b.date < DEMO_DATE || (b.date === DEMO_DATE && b.time <= NOW);
};
const buildLabel = (c: CallMeta) => { const b = autoBuildAt(c); return `${b.date === DEMO_DATE ? '' : `${dateLabel(b.date)}, `}${time12(b.time)}`; };

function Source({ id, onOpen }: { id?: string; onOpen: (id: string) => void }) {
  const s = id ? sourceById(id) : undefined;
  if (!s) return null;
  return <button className="cp2-source" onClick={() => onOpen(s.id)}><SourceIcon kind={s.kind} size={12} />Source: {s.kind} ({dateLabel(s.date)})</button>;
}

function Card({ icon, title, onMore, children, className = '' }: { icon: ReactNode; title: string; onMore?: () => void; children: ReactNode; className?: string }) {
  return <section className={`cp2-card ${className}`}>
    <header><span className="cp2-card-icon">{icon}</span><h3>{title}</h3>{onMore && <button className="icon-button" aria-label={`Open ${title}`} onClick={onMore}><ChevronRight size={16} /></button>}</header>
    {children}
  </section>;
}

export default function CallPrepV2(props: WorkspaceProps) {
  const fromHash = () => window.location.hash.split('/')[1];
  const [callId, setCallId] = useState<string | null>(() => CALL_META.some(c => c.id === fromHash()) ? fromHash() : null);
  const [tab, setTab] = useState<Tab>('overview');
  const [details, setDetails] = useState(false);
  useEffect(() => { const sync = () => { const id = fromHash(); setCallId(CALL_META.some(c => c.id === id) ? id : null); setTab('overview'); }; window.addEventListener('hashchange', sync); return () => window.removeEventListener('hashchange', sync); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const open = (id: string | null) => { window.location.hash = `calls-v2/${id || 'all'}`; };

  if (!callId) return <CallQueue {...props} open={open} />;

  const meta = CALL_META.find(c => c.id === callId)!;
  return <CallView key={meta.id} {...props} meta={meta} tab={tab} setTab={setTab} back={() => open(null)} details={details} setDetails={setDetails} />;
}

function CallView(props: WorkspaceProps & { meta: CallMeta; tab: Tab; setTab: (t: Tab) => void; back: () => void; details: boolean; setDetails: (v: boolean) => void }) {
  const { meta, tab, setTab } = props;
  const client = clientById(meta.clientId);
  const record = RECORDS[meta.clientId];
  const call = CALLS.find(c => c.id === meta.id);
  const fullBrief = meta.brief;
  const template = templateFor(typeOf(meta));
  const assessment = assessmentFor(meta.clientId);
  const health = categoryOf(assessment, record.lifecycle === 'Onboarding');
  const perf = PERFORMANCE[meta.clientId];
  const live = meta.facts;
  const lastRecap = RECAPS.filter(r => r.clientId === meta.clientId && r.date < meta.date && r.transcript).sort((a, b) => b.date.localeCompare(a.date))[0];
  const lastMeeting = record.meetings.filter(m => m.date < meta.date).sort((a, b) => b.date.localeCompare(a.date))[0];
  const lastDate = lastRecap?.date || lastMeeting?.date;
  const actions = props.actions.filter(a => a.clientId === meta.clientId);
  const open = actions.filter(isOutstanding);
  const byId = new Map(props.actions.map(a => [a.id, a]));
  const fromLive = (ids: { id: string }[]) => ids.map(x => byId.get(x.id)).filter((a): a is Action => !!a);
  const weOwe = live ? fromLive(live.owed.we) : open.filter(a => a.side === 'WIA'); const theyOwe = live ? fromLive(live.owed.they) : open.filter(a => a.side === 'Client');
  const contact = record.contacts[0];
  const others = meta.attendees.filter(n => n !== meta.host && n !== contact?.name);
  const tz = TIMEZONES[meta.clientId];
  const show = props.showEvidence;
  const readyVersions = (meta.versions || []).filter(v => v.outcome === 'ready');
  const [versions, setVersions] = useState<BriefVersion[]>(() => LIVE ? readyVersions.map(toVersion) : autoBuilt(meta) ? [{ n: 1, by: 'Automatic', at: `${buildLabel(meta)} (2 h before)`, skill: DEFAULT_SKILL }] : []);
  const [current, setCurrent] = useState(() => LIVE ? Math.max(0, readyVersions.length - 1) : 0);
  const [loaded, setLoaded] = useState<Record<number, Brief>>({});
  const [regenOpen, setRegenOpen] = useState(false);
  const [building, setBuilding] = useState(false);
  const [running, setRunning] = useState(template.name);
  const version = versions[current] as BriefVersion | undefined;
  const latestReady = readyVersions[readyVersions.length - 1]?.n;
  const brief = !version ? undefined : !LIVE ? fullBrief : loaded[version.n] ?? (version.n === latestReady ? fullBrief : undefined);
  const loadVersions = () => api<{ versions: LiveVersion[] }>(`/api/v1/calls/${meta.id}/briefs`).then(r => { setLoaded(Object.fromEntries(r.versions.filter(v => v.brief).map(v => [v.n, v.brief!]))); return r.versions; });
  useEffect(() => { if (LIVE && version && !brief) loadVersions().catch(e => props.notify(e.message)); }, [version?.n]); // eslint-disable-line react-hooks/exhaustive-deps
  const limit = version?.tone?.includes('Shorter') ? 2 : version?.tone?.includes('More detail') ? 5 : 3;
  const regenerate = (v: Omit<BriefVersion, 'n' | 'by' | 'at'>) => {
    setRegenOpen(false); setBuilding(true); setRunning(v.skill);
    if (LIVE) {
      const known = (meta.versions || []).length;
      let tries = 0;
      const poll = () => loadVersions().then(all => {
        if (all.length > known) {
          const last = all[all.length - 1];
          setBuilding(false);
          if (last.outcome === 'rejected') { props.notify(`The new version failed its checks (${(last.rejected || []).join('; ') || 'see Sources'}). The facts and the earlier version stay.`); return; }
          const ready = all.filter(x => x.outcome === 'ready').map(toVersion);
          setVersions(ready); setCurrent(ready.length - 1); props.notify(`Version ${last.n} is ready.`);
        } else if (++tries < 40) setTimeout(poll, 3000);
        else { setBuilding(false); props.notify('Still building, or nothing changed since the last version. Reopen the call in a minute.'); }
      });
      const typeKey = keyOf(v.skill);
      const setType = typeKey && typeKey !== typeOf(meta) ? api(`/api/v1/calls/${meta.id}/override`, 'PUT', { call_type: typeKey, viewer: props.viewer }) : Promise.resolve();
      setType.then(() => api(`/api/v1/calls/${meta.id}/briefs`, 'POST', { instructions: v.prompt || null, viewer: props.viewer }))
        .then(() => setTimeout(poll, 3000)).catch(e => { setBuilding(false); props.notify(e.message); });
      return;
    }
    const now = new Date(); const at = time12(`${now.getHours()}:${now.getMinutes()}`);
    const n = versions.length + 1;
    setTimeout(() => { setRunning(v.skill); setVersions(list => [...list, { ...v, n, by: me(props.viewer), at }]); setCurrent(n - 1); setBuilding(false); props.notify(`Built with the ${v.skill} skill.`); }, 1300);
  };
  useEffect(() => { const req = pendingGeneration.get(meta.id); if (req) { pendingGeneration.delete(meta.id); regenerate(req); } }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Overview pieces, all derived from the brief and the live records.
  const goal = brief ? strip(brief.thirty[1] || '', /^Must achieve:\s*/i) : call?.objective || '';
  const standing = brief?.thirty[0] || call?.context || '';
  const risk = brief ? strip(brief.thirty[2] || '', /^Risk:\s*/i) : '';
  const settle: { who: string; text: string; age: string; tone: 'late' | 'ask' | 'wait'; sourceId?: string }[] = live ? live.settle : [
    ...weOwe.filter(isOverdue).map(a => ({ who: `We owe · ${a.owner || 'no owner'}`, text: a.title, age: `${daysBetween(a.due)} day${daysBetween(a.due) === 1 ? '' : 's'} late`, tone: 'late' as const, sourceId: a.sourceId })),
    ...(brief?.asks || []).map(q => ({ who: `${q.who} asked`, text: `“${q.quote.length > 110 ? `${q.quote.slice(0, 107)}…` : q.quote}”`, age: ago(q.date), tone: 'ask' as const, sourceId: q.sourceId })),
    ...weOwe.filter(a => a.status === 'Blocked').concat(theyOwe.filter(a => !!a.due && a.due <= meta.date)).map(a => ({ who: a.side === 'Client' ? `Waiting on ${a.owner}` : `Blocked · ${a.owner}`, text: a.title, age: a.lastActivity ? ago(a.lastActivity) : '', tone: 'wait' as const, sourceId: a.sourceId })),
  ].slice(0, 3);
  const changes = live ? live.changed.map(c => ({ text: c.text, date: c.date, sourceId: c.sourceId, from: c.from })) : (brief?.since || []).map(s => { const ev = s.sourceId ? sourceById(s.sourceId) : undefined; return { ...s, from: ev && isClientPerson(ev.author) ? 'Client' : 'Internal' }; }).sort((a, b) => b.date.localeCompare(a.date));
  const points = brief?.agenda || (call?.agenda || []).map(item => ({ item, why: '' }));
  const status = perfStatus(perf);
  const unanswered = brief?.asks.length || 0;
  const overdue = weOwe.filter(isOverdue).length;
  const pulse = live ? (([['Ads', live.pulse.ads, 'performance'], ['Leads', live.pulse.leads, 'performance'], ['Delivery', live.pulse.delivery, 'owed'], ['Client', live.pulse.client, 'owed']]) as [string, { value: string; note: string; tone: string }, Tab][])
    .map(([label, c, tab]) => ({ label, value: c.value, note: c.note, tone: c.tone, tab })) : [
    { label: 'Ads', value: status, note: perf?.empty ? 'No spend yet' : perf?.channels.find(c => c.status !== 'On track')?.note.split(';')[0] || 'All channels on track', tone: status === 'Watch' ? 'watch' : status === 'Problem' ? 'bad' : status === 'No data' ? 'none' : 'ok', tab: 'performance' as Tab },
    { label: 'Leads', value: assessment.leadNumbers ? `${assessment.leadNumbers.inquiries[0]} inquiries` : 'Unavailable', note: assessment.leadNumbers ? `${assessment.leadNumbers.tours[0]} tours · ${assessment.leadNumbers.booked[0]} booked` : 'Not a LeadLock client or not readable', tone: assessment.leadNumbers ? 'ok' : 'none', tab: 'performance' as Tab },
    { label: 'Delivery', value: overdue ? `${overdue} overdue` : 'On time', note: `${weOwe.length} open on our side`, tone: overdue ? 'bad' : 'ok', tab: 'owed' as Tab },
    { label: 'Client', value: unanswered ? `${unanswered} ask${unanswered === 1 ? '' : 's'} unanswered` : 'No open asks', note: `Last contact ${ago(record.lastContact.date)} · ${record.lastContact.channel}`, tone: unanswered ? 'watch' : 'ok', tab: 'owed' as Tab },
  ];
  const limits = brief?.limits?.length ? brief.limits : live?.limits || [];
  const sources = [...new Set([...(live ? [...live.changed.map(c => c.sourceId), ...live.settle.map(s => s.sourceId)] : []), ...(call?.sourceIds || []), ...(brief?.since.map(s => s.sourceId) || []), ...(brief?.asks.map(a => a.sourceId) || []), ...actions.map(a => a.sourceId)].filter(Boolean) as string[])].map(id => sourceById(id)!).filter(Boolean);

  const Settle = ({ limit }: { limit?: number }) => <ul className="cp2-settle">{settle.slice(0, limit).map((s, i) => <li key={i} className={`tone-${s.tone}`}><span className="cp2-settle-who">{s.who}</span><p>{s.text}</p><span className="cp2-settle-foot"><span>{s.age}</span><Source id={s.sourceId} onOpen={show} /></span></li>)}{!settle.length && <li className="cp2-empty">Nothing outstanding to settle.</li>}</ul>;
  const ownerLine = (a: Action) => <li key={a.id}><span className={`cp2-dot ${isOverdue(a) ? 'late' : a.status === 'Blocked' ? 'wait' : ''}`} /><div><strong>{a.title}</strong><small>{a.owner || 'Unassigned'} · {a.due ? `due ${dateLabel(a.due)}${isOverdue(a) ? ' (late)' : ''}` : 'no date agreed'} · {a.status}</small></div><Source id={a.sourceId} onOpen={show} /></li>;
  const channelRow = (c: ChannelPerf) => { const delta = c.leads ? Math.round((c.leads[0] - c.leads[1]) / Math.max(c.leads[1], 1) * 100) : 0; const cpl = (x: 0 | 1) => c.spend && c.leads && c.leads[x] ? money(Math.round(c.spend[x] / c.leads[x])) : '—'; return <tr key={c.channel}>
    <td><strong>{c.channel}</strong></td><td><span className={`cp2-pill st-${c.status.toLowerCase().replace(' ', '-')}`}>{c.status}</span></td>
    <td>{c.spend ? <>{money(c.spend[0])}<small>prev {money(c.spend[1])}</small></> : '—'}</td>
    <td>{c.leads ? <>{c.leads[0]} <span className={`cp2-delta ${delta < 0 ? 'down' : 'up'}`}>{delta < 0 ? <TrendingDown size={12} /> : <TrendingUp size={12} />}{Math.abs(delta)}%</span><small>prev {c.leads[1]}</small></> : '—'}</td>
    <td>{cpl(0)}<small>prev {cpl(1)}</small></td><td className="cp2-note">{c.note}</td></tr>; };

  const adRow = (p: AdPlatform) => { const c = p.current; const prev = p.previous; const delta = c && prev && prev.leads ? Math.round((c.leads - prev.leads) / prev.leads * 100) : null; return <tr key={p.provider}>
    <td><strong>{p.label}</strong>{p.accounts?.map(a => <small key={a.id}>{a.name}{a.error ? ' · last pull failed' : ''}</small>)}</td>
    {c ? <><td>{money(Math.round(c.spend))}{prev && <small>prev {money(Math.round(prev.spend))}</small>}</td>
      <td>{c.leads}{delta !== null && <span className={`cp2-delta ${delta < 0 ? 'down' : 'up'}`}>{delta < 0 ? <TrendingDown size={12} /> : <TrendingUp size={12} />}{Math.abs(delta)}%</span>}{prev && <small>prev {prev.leads}</small>}</td>
      <td>{c.cpl ? money(Math.round(c.cpl)) : '—'}{prev?.cpl ? <small>prev {money(Math.round(prev.cpl))}</small> : null}</td>
      <td className="cp2-note">{[c.ctr != null && `CTR ${c.ctr}%`, c.link_ctr != null && `link CTR ${c.link_ctr}%`, c.lpv_rate != null && `landing views ${c.lpv_rate}% of link clicks`, c.budget_lost_is != null && `${c.budget_lost_is}% impression share lost to budget`].filter(Boolean).join(' · ')}</td></>
      : <td colSpan={4} className="cp2-note">{p.state === 'not_connected' ? 'Not connected: no credentials for this platform yet' : 'No ad account mapped to this client'}</td>}
  </tr>; };
  const overview = brief ? <>
    <section className="cp2-hero">
      <div className="cp2-hero-top">
        <h2>Quick brief</h2>
        {version && <span className="cp2-hero-actions">
          <select className="cp2-skill-select" aria-label="Skill used for this brief" title="Skill used to build this brief" value={current} onChange={e => setCurrent(Number(e.target.value))}>{versions.map((v, i) => <option key={v.n} value={i}>{v.skill}{versions.filter(x => x.skill === v.skill).length > 1 ? ` · ${v.at}` : ''}</option>)}</select>
          <span className="cp2-read" title={`Version ${version.n} of ${versions.length}`}>v{version.n}</span>
        </span>}
      </div>
      {version && (version.prompt || version.refused?.length) && <p className="cp2-instructions"><strong>Instructions:</strong> {version.prompt && `“${version.prompt}”`}{version.refused?.map(r => <span key={r} className="cp2-refused"><Ban size={11} />{r}</span>)}</p>}
      {building && <div className="cp2-building"><RefreshCw size={14} className="spin" />Running the {running} skill…</div>}
      <dl className="cp2-goal">
        <div className="is-goal"><dt><Target size={14} />This call must</dt><dd>{goal}</dd></div>
        <div><dt>Where things stand</dt><dd>{standing}</dd></div>
        {risk && <div className="is-risk"><dt><AlertTriangle size={13} />Main risk</dt><dd>{risk}</dd></div>}
      </dl>
    </section>
    <div className="cp2-pulse" role="list" aria-label="Account pulse">{pulse.map(p => <button key={p.label} role="listitem" className={`cp2-chip tone-${p.tone}`} onClick={() => setTab(p.tab)}><span>{p.label}</span><strong>{p.value}</strong><small>{p.note}</small></button>)}</div>
    <div className="cp2-grid">
      <Card icon={<ListChecks size={16} />} title="Settle on this call" onMore={() => setTab('owed')}><Settle limit={limit} /></Card>
      <Card icon={<RefreshCw size={16} />} title="What changed since the last call" onMore={() => setTab('changed')}><ul className="cp2-list">{changes.slice(0, limit).map((c, i) => <li key={i}><span className={`cp2-tag ${c.from === 'Client' ? 'client' : ''}`}>{c.from}</span><p>{c.text}</p><span className="cp2-settle-foot"><span>{dateLabel(c.date)}</span><Source id={c.sourceId} onOpen={show} /></span></li>)}</ul></Card>
      <Card icon={<MessageSquareQuote size={16} />} title="Talking points" onMore={() => setTab('points')}><ol className="cp2-points">{points.slice(0, limit).map((p, i) => <li key={i}><strong>{p.item}</strong>{p.why && <small>{p.why}</small>}</li>)}</ol></Card>
      {brief.watch.length > 0 && <Card icon={<ShieldAlert size={16} />} title="Watch-out" className="is-watch" onMore={() => setTab('points')}><ul className="cp2-list plain">{brief.watch.slice(0, limit === 2 ? 1 : 2).map((w, i) => <li key={i}><p>{w}</p></li>)}</ul></Card>}
    </div>
    <p className="cp2-ready"><Clock3 size={12} />Built {meta.builtAt ? `${dateLabel(meta.builtAt.slice(0, 10))}, ${time12(meta.builtAt.slice(11, 16))}` : 'automatically'}{meta.stateNote ? ` · ${meta.stateNote}` : ''} · {limits.filter(l => !l.startsWith('Sources:')).join(' · ')}</p>
  </> : live && meta.state !== 'Cancelled' ? <>
    <section className="cp2-hero">
      <div className="cp2-hero-top"><h2>Facts for this call</h2><span className="cp2-read">Brief text not built</span></div>
      <dl className="cp2-goal">
        <div className="is-goal"><dt><Target size={14} />This call must</dt><dd>{template.decide || template.purpose}</dd></div>
        <div><dt>Where things stand</dt><dd>{live.settle.length ? `${live.settle.length} thing${live.settle.length === 1 ? '' : 's'} to settle${live.owed.overdue ? `, ${live.owed.overdue} late on our side` : ''}.` : 'Nothing outstanding to settle.'}</dd></div>
        {live.attendance && <div className="is-risk"><dt><AlertTriangle size={13} />Attendance</dt><dd>{live.attendance}</dd></div>}
      </dl>
      <p className="cp2-muted">{meta.stateNote}</p>
      {building && <div className="cp2-building"><RefreshCw size={14} className="spin" />Running the {running} skill…</div>}
    </section>
    <div className="cp2-pulse" role="list" aria-label="Account pulse">{pulse.map(p => <button key={p.label} role="listitem" className={`cp2-chip tone-${p.tone}`} onClick={() => setTab(p.tab)}><span>{p.label}</span><strong>{p.value}</strong><small>{p.note}</small></button>)}</div>
    <div className="cp2-grid">
      <Card icon={<ListChecks size={16} />} title="Settle on this call" onMore={() => setTab('owed')}><Settle limit={4} /></Card>
      <Card icon={<RefreshCw size={16} />} title="What changed since the last call" onMore={() => setTab('changed')}><ul className="cp2-list">{changes.slice(0, 4).map((c, i) => <li key={i}><span className={`cp2-tag ${c.from === 'Client' ? 'client' : ''}`}>{c.from}</span><p>{c.text}</p><span className="cp2-settle-foot"><span>{dateLabel(c.date)}</span><Source id={c.sourceId} onOpen={show} /></span></li>)}{!changes.length && <li className="cp2-empty">Nothing recorded since the last call.</li>}</ul></Card>
    </div>
    <p className="cp2-ready"><Clock3 size={12} />{limits.join(' · ')}</p>
  </> : <section className="cp2-hero"><h2>Brief not built yet</h2><p className="cp2-muted">{meta.state === 'Cancelled' ? 'This call was cancelled; no brief is needed.' : meta.state === 'Needs type' ? 'Set the call type so the right skill can build the brief.' : `It builds automatically at ${buildLabel(meta)}, 2 hours before the call, with the default call prep skill. Need it sooner? Generate it now with the ${template.name} skill.`}</p>{!LIVE && fullBrief && meta.state !== 'Cancelled' && meta.state !== 'Needs type' && <button className="button button-primary cp2-generate-now" onClick={() => setRegenOpen(true)} disabled={building}><Wand2 size={14} />Generate now with the {template.name} skill</button>}{building && <div className="cp2-building"><RefreshCw size={14} className="spin" />Running the {running} skill…</div>}</section>;

  const body: Record<Tab, ReactNode> = {
    overview,
    last: live?.promised.recap ? <Card icon={<FileText size={16} />} title={`${live.promised.recap.title} · ${dateLabel(live.promised.recap.date)}`}><div className="cp2-sections">
        <div><p className="small-label">DECISIONS</p><ul className="cp2-list plain">{live.promised.recap.decisions.map((d, i) => <li key={i}><p>{d}</p></li>)}{!live.promised.recap.decisions.length && <li><p>None recorded.</p></li>}</ul></div>
        <div><p className="small-label">PROMISED, AND WHERE IT STANDS NOW</p><ul className="cp2-owed">{live.promised.items.map((c, i) => <li key={i}><span className={`cp2-dot ${c.now === 'Done' ? 'done' : ''}`} /><div><strong>{c.text}</strong><small>{c.who} · promised {c.when} · now: {c.now}</small></div></li>)}{!live.promised.items.length && <li className="cp2-empty">No commitments recorded.</li>}</ul></div>
        <div><p className="small-label">LEFT OPEN</p><ul className="cp2-list plain">{live.promised.recap.covered.filter(c => !c.done).map((c, i) => <li key={i}><p>{c.item}: not covered</p></li>)}{!live.promised.recap.covered.some(c => !c.done) && <li><p>Everything planned was covered.</p></li>}</ul></div>
        <Source id={live.promised.recap.sourceId} onOpen={show} />
      </div></Card> : <Card icon={<FileText size={16} />} title={lastRecap ? `${lastRecap.title} · ${dateLabel(lastRecap.date)}` : lastMeeting ? `${lastMeeting.title} · ${dateLabel(lastMeeting.date)}` : 'Last call'}>
      {lastRecap ? <div className="cp2-sections">
        <div><p className="small-label">DECISIONS</p><ul className="cp2-list plain">{lastRecap.decisions.map((d, i) => <li key={i}><p>{d}</p></li>)}</ul></div>
        <div><p className="small-label">PROMISED, AND WHERE IT STANDS NOW</p><ul className="cp2-owed">{lastRecap.commitments.map((c, i) => { const a = c.actionId ? props.actions.find(x => x.id === c.actionId) : undefined; return <li key={i}><span className={`cp2-dot ${a && isOverdue(a) ? 'late' : a && !isOutstanding(a) ? 'done' : ''}`} /><div><strong>{c.text}</strong><small>{c.who} · promised {c.when} · now: {a ? (isOverdue(a) ? 'late' : a.status) : 'not tracked'}</small></div></li>; })}</ul></div>
        <div><p className="small-label">LEFT OPEN</p><ul className="cp2-list plain">{lastRecap.covered.filter(c => !c.done).map((c, i) => <li key={i}><p>{c.item}: not covered</p></li>)}{!lastRecap.covered.some(c => !c.done) && <li><p>Everything planned was covered.</p></li>}</ul></div>
        <Source id={lastRecap.sourceId} onOpen={show} />
      </div> : <p className="cp2-muted">{lastMeeting ? `${lastMeeting.title} (${lastMeeting.source}): transcript ${lastMeeting.transcript.toLowerCase()}. Without a transcript, the KB can't say what was agreed; that doesn't mean nothing was.` : 'No earlier call found for this client.'}</p>}
    </Card>,
    changed: <Card icon={<RefreshCw size={16} />} title={`Since ${lastDate ? dateLabel(lastDate) : 'the last call'}`}>
      <div className="cp2-two">{(['Internal', 'Client'] as const).map(side => <div key={side}><p className="small-label">{side === 'Internal' ? 'INTERNAL (TEAM, SLACK, CLICKUP)' : 'FROM THE CLIENT'}</p><ul className="cp2-list">{changes.filter(c => c.from === side).map((c, i) => <li key={i}><p>{c.text}</p><span className="cp2-settle-foot"><span>{dateLabel(c.date)}</span><Source id={c.sourceId} onOpen={show} /></span></li>)}{!changes.some(c => c.from === side) && <li className="cp2-empty">Nothing recorded.</li>}</ul></div>)}</div>
      {brief?.more.since && <p className="cp2-muted">{brief.more.since}</p>}
    </Card>,
    performance: live ? <Card icon={<BarChart3 size={16} />} title={`Ad performance · last ${live.ads.period_days} days to ${dateLabel(live.ads.through)}`}>
      <div className="cp2-table-wrap"><table className="cp2-table"><thead><tr><th>Platform</th><th>Spend</th><th>Leads</th><th>Cost per lead</th><th>What it shows</th></tr></thead><tbody>{live.ads.platforms.map(adRow)}</tbody></table></div>
      {live.leads ? <div className="cp2-funnel"><p className="small-label">LEADLOCK OUTCOMES · LAST 30 DAYS</p><div>{([['Inquiries', live.leads.inquiries], ['Tours', live.leads.tours], ...(live.leads.won ? [['Booked', live.leads.won]] : [])] as [string, [number | null, number | null]][]).map(([l, v]) => <span key={l}><strong>{v[0] ?? '—'}</strong>{l}<small>prev {v[1] ?? '—'}</small></span>)}</div></div> : <p className="cp2-muted">LeadLock isn’t linked for this client, so there are no inquiry or tour figures.</p>}
      <p className="cp2-attrib">Read by the KB from the ad platforms and LeadLock (campaign totals only). Figures are what the platforms report; interpretation is labelled in the brief.</p>
    </Card> : <Card icon={<BarChart3 size={16} />} title="Ad performance since the last call">
      {perf?.channels.length ? <div className="cp2-table-wrap"><table className="cp2-table"><thead><tr><th>Channel</th><th>Status</th><th>Spend</th><th>Leads</th><th>Cost per lead</th><th>What it means</th></tr></thead><tbody>{perf.channels.map(channelRow)}</tbody></table></div> : <p className="cp2-muted">{perf?.empty || 'No ad data.'}</p>}
      <p className={`cp2-tracking ${perf?.tracking.ok ? 'ok' : ''}`}>{perf?.tracking.ok ? <Check size={13} /> : <AlertTriangle size={13} />}Tracking: {perf?.tracking.note}</p>
      {assessment.leadNumbers && <div className="cp2-funnel"><p className="small-label">LEADLOCK OUTCOMES · {assessment.period}</p><div>{([['Inquiries', assessment.leadNumbers.inquiries], ['Tours', assessment.leadNumbers.tours], ['Booked', assessment.leadNumbers.booked]] as [string, [number, number]][]).map(([l, v]) => <span key={l}><strong>{v[0]}</strong>{l}<small>prev {v[1]}</small></span>)}</div></div>}
      <p className="cp2-attrib">{perf?.source === 'Viktor’s analysis' ? `Viktor’s analysis, ${dateLabel(perf.asOf)}. Paid media isn’t a connected KB source, so these figures are attributed, not verified.` : `${perf?.source}, ${perf ? dateLabel(perf.asOf) : ''}.`}</p>
    </Card>,
    owed: <div className="cp2-stack">
      <Card icon={<ListChecks size={16} />} title="Settle on this call"><Settle /></Card>
      <div className="cp2-two">
        <Card icon={<Users size={16} />} title={`We owe (${weOwe.length})`}><ul className="cp2-owed">{weOwe.map(ownerLine)}{!weOwe.length && <li className="cp2-empty">Nothing open.</li>}</ul></Card>
        <Card icon={<Users size={16} />} title={`They owe (${theyOwe.length})`}><ul className="cp2-owed">{theyOwe.map(ownerLine)}{!theyOwe.length && <li className="cp2-empty">Nothing open.</li>}</ul></Card>
      </div>
      {!!brief?.asks.length && <Card icon={<MessageSquareQuote size={16} />} title="They asked, we haven’t answered">{brief.asks.map((q, i) => <blockquote key={i} className="cp2-quote">“{q.quote}”<footer>{q.who} · {dateLabel(q.date)} <Source id={q.sourceId} onOpen={show} /></footer></blockquote>)}</Card>}
    </div>,
    points: <div className="cp2-stack">
      <Card icon={<MessageSquareQuote size={16} />} title="Talking points"><p className="small-label">MUST COVER</p><ol className="cp2-points">{points.slice(0, 3).map((p, i) => <li key={i}><strong>{p.item}</strong>{p.why && <small>{p.why}</small>}</li>)}</ol>{points.length > 3 && <><p className="small-label">IF TIME</p><ol className="cp2-points" start={4}>{points.slice(3).map((p, i) => <li key={i}><strong>{p.item}</strong>{p.why && <small>{p.why}</small>}</li>)}</ol></>}{brief?.more.agenda && <p className="cp2-muted">{brief.more.agenda}</p>}</Card>
      <div className="cp2-two">
        {!!brief?.questions.length && <Card icon={<Lightbulb size={16} />} title="Questions to ask"><ul className="cp2-list plain">{brief.questions.map((q, i) => <li key={i}><p>{q}</p></li>)}</ul></Card>}
        {!!brief?.watch.length && <Card icon={<ShieldAlert size={16} />} title="Watch-outs" className="is-watch"><ul className="cp2-list plain">{brief.watch.map((w, i) => <li key={i}><p>{w}</p></li>)}</ul></Card>}
      </div>
      {brief?.opportunity && <Card icon={<Lightbulb size={16} />} title="One opportunity (suggestion, not a commitment)"><p className="cp2-body">{brief.opportunity.text}</p><p className="cp2-muted">Why it’s worth raising: {brief.opportunity.why}</p><Source id={brief.opportunity.sourceId} onOpen={show} /></Card>}
      {!!brief?.typeBlock.length && <Card icon={<FileText size={16} />} title={template.typeBlock || 'For this call type'}><dl className="cp2-facts">{brief.typeBlock.map(f => <div key={f.label}><dt>{f.label}</dt><dd>{f.value}</dd></div>)}</dl></Card>}
    </div>,
    sources: <Card icon={<FileText size={16} />} title="Sources & limits">
      <ul className="cp2-sources">{sources.map(s => <li key={s.id}><button onClick={() => show(s.id)}><SourceIcon kind={s.kind} size={15} /><span><strong>{s.title}</strong><small>{s.kind} · {s.author} · {dateLabel(s.date)}</small></span><ExternalLink size={13} /></button></li>)}</ul>
      {!!limits.length && <><p className="small-label">WHAT THIS BRIEF COULDN’T SEE</p><ul className="cp2-list plain">{limits.map((l, i) => <li key={i}><p>{l}</p></li>)}</ul></>}
      {brief?.declined && <p className="cp2-m-note"><Ban size={13} />Skipped from the instructions: {brief.declined}</p>}
      <p className="cp2-attrib">Built by the “{template.name}” skill. Every line links to its source; suggestions are labelled and are not commitments.</p>
    </Card>,
  };

  return <div className="view cp2-view">
    <button className="cp2-back" onClick={props.back}><ArrowLeft size={14} />Back to calls</button>
    <header className="cp2-head"><h1>Call preparation</h1><p>Everything you need to be ready for your client call, in under 2 minutes.</p></header>
    <div className="cp2-layout">
      <aside className="cp2-rail">
        <section className="cp2-callcard">
          <div className="cp2-badges">{meta.state === 'Cancelled' ? <span className="cp2-badge muted">Cancelled</span> : <span className={`cp2-pill cat-${health.category.toLowerCase().replace(' ', '-')}`} title={`Client signal: ${health.causes.join('; ')}`}>{health.category}</span>}<span className="cp2-badge muted">{until(meta.date)}</span></div>
          <h2><button onClick={() => props.openClient(client.id)}>{client.name}<ExternalLink size={14} /></button></h2>
          <p className="cp2-type">{template.name}{!typeConfirmed(meta) ? ' · proposed type' : ''}</p>
          <p className="cp2-time"><CalendarDays size={15} /><span>{dateLabel(meta.date, { day: 'numeric', month: 'short', year: 'numeric' })} · {time12(meta.time)} – {endTime(meta.time, meta.duration)} <small>({meta.duration})</small><small>IST · client in {tz?.label}</small></span></p>
          <div className="cp2-people">
            <span><b className="host">{initials(meta.host)}</b>{meta.host === props.viewer ? 'You' : meta.host}<small>(Host)</small></span>
            {contact && <span><b>{initials(contact.name)}</b>{contact.name}<small>(Client)</small></span>}
            {others.length > 0 && <span><b className="more">+{others.length}</b>Others<small>{others.join(', ')}</small></span>}
          </div>
          <button className="button button-primary cp2-details" onClick={() => props.setDetails(true)}>Open call details<ArrowRight size={14} /></button>
        </section>
        <section className="cp2-panel"><h3>Quick context</h3>
          <dl className="cp2-facts">
            <div><dt>Client type</dt><dd>{client.category}</dd></div>
            <div><dt>Account stage</dt><dd>{record.lifecycle} · {client.service}</dd></div>
            <div><dt>Last call</dt><dd>{lastDate ? <>{dateLabel(lastDate, { day: 'numeric', month: 'short', year: 'numeric' })}<small>({daysBetween(lastDate)} days ago)</small></> : 'None found'}</dd></div>
          </dl>
        </section>
        <button className="cp2-panel cp2-sourcenote" onClick={() => setTab('sources')}><FileText size={15} /><span>All information is sourced and linked ({[...new Set(sources.map(s => s.kind))].join(', ')}).</span><ChevronRight size={15} /></button>
      </aside>
      <section className="cp2-main">
        <div className="cp2-tabbar"><nav className="cp2-tabs" role="tablist" aria-label="Brief sections">{TABS.map(([id, label]) => <button key={id} role="tab" aria-selected={tab === id} className={tab === id ? 'selected' : ''} onClick={() => setTab(id)}>{label}</button>)}</nav>{(LIVE ? meta.state !== 'Cancelled' : fullBrief && meta.state !== 'Cancelled' && meta.state !== 'Needs type') && <button className="button button-primary cp2-regen" onClick={() => setRegenOpen(true)} disabled={building}><Wand2 size={14} />Regenerate brief</button>}</div>
        <div className="cp2-body">{body[tab]}</div>
      </section>
    </div>
    {regenOpen && <RegenerateDialog viewer={props.viewer} clientName={client.name} skill={template.name} last={versions[versions.length - 1]} nextN={versions.length + 1} close={() => setRegenOpen(false)} submit={regenerate} />}
    {props.details && <Dialog title={meta.title} subtitle="Call details" onClose={() => props.setDetails(false)}><dl className="cp2-facts">
      <div><dt>When</dt><dd>{dateLabel(meta.date, { weekday: 'long', day: 'numeric', month: 'long' })}, {time12(meta.time)} IST ({meta.duration}) · client in {tz?.label}</dd></div>
      <div><dt>Call type</dt><dd>{template.name} · {typeOverride.has(meta.id) ? 'changed by the team' : meta.typeSource === 'Calendar title' ? 'from the calendar title' : 'proposed by the KB, needs confirming'}</dd></div>
      <div><dt>Attendees</dt><dd>{meta.attendees.join(', ')}</dd></div>
      <div><dt>Brief</dt><dd>{meta.state}{meta.stateNote ? `. ${meta.stateNote}` : ''}</dd></div>
      <div><dt>Purpose of this call type</dt><dd>{template.purpose}. Leaves out: {template.leaveOut}.</dd></div>
    </dl></Dialog>}
  </div>;
}

// ---- Meetings board / list (landing) ----------------------------------------
type Bucket = 'today' | 'tomorrow' | 'week' | 'month';
const BUCKETS: [Bucket, string][] = [['today', 'Today'], ['tomorrow', 'Tomorrow'], ['week', 'This week'], ['month', 'This month']];
const bucketOf = (date: string): Bucket | null => {
  if (date === DEMO_DATE) return 'today';
  if (date === addDays(DEMO_DATE, 1)) return 'tomorrow';
  if (date > DEMO_DATE && date <= addDays(DEMO_DATE, 6)) return 'week';
  if (date > DEMO_DATE && date.slice(0, 7) === DEMO_DATE.slice(0, 7)) return 'month';
  return null;
};
const stateClass = (s: string) => `st-${s.toLowerCase().replace(' ', '-')}`;

const pendingGeneration = new Map<string, Omit<BriefVersion, 'n' | 'by' | 'at'>>();

function CallQueue(props: WorkspaceProps & { open: (id: string) => void }) {
  const admin = VIEWERS.find(v => v.name === props.viewer)?.defaultScope === 'all';
  const [scope, setScope] = useState<'mine' | 'all'>(admin ? 'all' : 'mine');
  const [layout, setLayout] = useState<'board' | 'list'>('board');
  useEffect(() => { setScope(admin ? 'all' : 'mine'); }, [admin]);
  const calls = CALL_META.filter(c => scope === 'all' || c.host === props.viewer || c.attendees.includes(props.viewer)).filter(c => bucketOf(c.date)).sort((a, b) => `${a.date}${a.time}`.localeCompare(`${b.date}${b.time}`));
  // Changes since the brief was built: actions that went overdue or had new activity, and newer brief sources.
  const updatesSince = (c: CallMeta) => {
    if (c.state !== 'Stale' || !c.builtAt) return 0;
    const built = c.builtAt.slice(0, 10);
    const actions = props.actions.filter(a => a.clientId === c.clientId && ((isOverdue(a) && a.due >= built) || (!!a.lastActivity && a.lastActivity > built))).length;
    return actions + (c.brief?.since.filter(x => x.date > built).length || 0);
  };
  const needsType = (c: CallMeta) => c.state === 'Needs type' && !typeOverride.has(c.id);
  const liveLabel = (c: CallMeta) => c.state === 'Scheduled' ? 'Facts only' : c.state === 'Stale' ? `${c.changedReasons?.length || 1} update${(c.changedReasons?.length || 1) === 1 ? '' : 's'}` : c.state;
  const stateLabel = (c: CallMeta) => LIVE ? liveLabel(c) : pendingGeneration.has(c.id) ? 'New brief queued' : c.state === 'Cancelled' || needsType(c) ? c.state : !autoBuilt(c) ? `Builds ${buildLabel(c)}` : c.state === 'Stale' ? `${Math.max(updatesSince(c), 1)} update${Math.max(updatesSince(c), 1) === 1 ? '' : 's'}` : 'Ready';
  const stateOf = (c: CallMeta) => LIVE ? c.state : pendingGeneration.has(c.id) ? 'Stale' : c.state === 'Cancelled' || needsType(c) ? (c.state === 'Cancelled' ? c.state : 'Needs type') : !autoBuilt(c) ? 'Scheduled' : c.state === 'Stale' ? 'Stale' : 'Ready';
  const [skillsOpen, setSkillsOpen] = useState(false);
  const [namesShown, setNamesShown] = useState<Set<string>>(new Set());
  const [genFor, setGenFor] = useState<CallMeta | null>(null);
  const [, rerender] = useState(0);
  const [typeChange, setTypeChange] = useState<{ call: CallMeta; to: CallTypeKey } | null>(null);
  const applyType = (c: CallMeta, to: CallTypeKey, rebuild: boolean) => {
    if (LIVE) {
      api(`/api/v1/calls/${c.id}/override`, 'PUT', { call_type: to, viewer: props.viewer })
        .then(() => { typeOverride.set(c.id, to); rerender(n => n + 1); props.notify(`Call type set to ${templateFor(to).name}. ${rebuild ? 'The brief rebuilds with that skill on the next run.' : 'The brief will use that skill.'}`); })
        .catch(e => props.notify(e.message));
      return;
    }
    typeOverride.set(c.id, to);
    const skill = templateFor(to).name;
    if (rebuild) { pendingGeneration.set(c.id, { skill, prompt: '', refused: [] }); props.notify(`Call type changed to ${skill}. A new brief is queued and builds when the call opens.`); }
    else props.notify(`Call type set to ${skill}. The brief will build with the ${skill} skill.`);
    rerender(n => n + 1);
  };
  const changeType = (c: CallMeta, to: CallTypeKey) => { if (to === typeOf(c)) return; if (autoBuilt(c) || pendingGeneration.has(c.id)) setTypeChange({ call: c, to }); else applyType(c, to, false); };
  const typePicker = (c: CallMeta) => <span className="cp2-type-pick" onClick={e => e.stopPropagation()} onKeyDown={e => e.stopPropagation()}>{c.state === 'Cancelled' ? <small>{templateFor(typeOf(c)).name}</small> : <ThemedSelect aria-label={`Call type for ${clientById(c.clientId).name}`} value={typeOf(c)} onChange={v => changeType(c, v as CallTypeKey)}>{TEMPLATES.map(t => <option key={t.key} value={t.key}>{t.name}</option>)}</ThemedSelect>}{!typeConfirmed(c) && <em>proposed</em>}</span>;
  const toggleName = (id: string) => setNamesShown(set => { const next = new Set(set); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  const card = (c: CallMeta) => { const client = clientById(c.clientId); const near = bucketOf(c.date) === 'today' || bucketOf(c.date) === 'tomorrow'; return <li key={c.id}><div role="button" tabIndex={0} aria-label={`Open the brief for ${client.name}`} className={`cp2-meet ${c.state === 'Cancelled' ? 'is-cancelled' : ''}`} onClick={() => props.open(c.id)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); props.open(c.id); } }}>
    <span className="cp2-meet-top"><Avatar client={client} small /><span className="cp2-meet-time">{near ? '' : `${dateLabel(c.date, { weekday: 'short', day: 'numeric', month: 'short' })} · `}{time12(c.time)}<small>{c.duration}</small></span></span>
    <span className="cp2-meet-client"><span><strong>{client.name}</strong>{typePicker(c)}</span></span>
    <span className="cp2-meet-foot"><button type="button" className={`cp2-host ${namesShown.has(c.id) ? 'is-open' : ''}`} title={`Host: ${c.host === props.viewer ? `You (${c.host})` : c.host}`} aria-pressed={namesShown.has(c.id)} aria-label={`Host ${c.host}`} onClick={e => { e.stopPropagation(); toggleName(c.id); }}>{namesShown.has(c.id) && <span>{c.host === props.viewer ? 'You' : c.host}</span>}<b>{initials(c.host)}</b></button><span className={`cp2-state ${stateClass(stateOf(c))}`} title={c.state === 'Stale' ? c.stateNote : undefined}>{stateLabel(c)}</span>{stateOf(c) === 'Scheduled' && (LIVE || c.brief) && <button type="button" className="cp2-gen-icon" title="Generate the brief now" aria-label={`Generate the brief for ${clientById(c.clientId).name} now`} onClick={e => { e.stopPropagation(); setGenFor(c); }}><Wand2 size={12} /></button>}</span>
  </div></li>; };
  const dayLabel = (id: Bucket) => id === 'today' ? dateLabel(DEMO_DATE, { weekday: 'short', day: 'numeric', month: 'short' }) : id === 'tomorrow' ? dateLabel(addDays(DEMO_DATE, 1), { weekday: 'short', day: 'numeric', month: 'short' }) : '';
  return <div className="view cp2-view">
    <header className="cp2-head"><h1>Call preparation</h1><p>Everything you need to be ready for your client call, in under 2 minutes.</p></header>
    <div className="cp2-bar">
      <div className="cp2-seg" role="group" aria-label="Whose calls">{([['mine', 'My calls'], ['all', 'All calls']] as const).map(([id, label]) => <button key={id} className={scope === id ? 'selected' : ''} aria-pressed={scope === id} onClick={() => setScope(id)}>{label}</button>)}</div>
      <div className="cp2-bar-end"><button className="button button-small button-outline cp2-skills-btn" onClick={() => setSkillsOpen(true)}><Wand2 size={13} />Call-type skills<span>{TEMPLATES.length}</span></button>
      <div className="cp2-seg" role="group" aria-label="Layout"><button className={layout === 'board' ? 'selected' : ''} aria-pressed={layout === 'board'} onClick={() => setLayout('board')}><LayoutGrid size={13} />Board</button><button className={layout === 'list' ? 'selected' : ''} aria-pressed={layout === 'list'} onClick={() => setLayout('list')}><List size={13} />List</button></div></div>
    </div>
    {typeChange && (() => { const from = templateFor(typeOf(typeChange.call)); const to = templateFor(typeChange.to); return <Dialog title="Change the call type?" subtitle={`${clientById(typeChange.call.clientId).name} · ${dateLabel(typeChange.call.date, { weekday: 'short', day: 'numeric', month: 'short' })}, ${time12(typeChange.call.time)}`} className="cp2-modal cp2-modal-sm" onClose={() => setTypeChange(null)}>
      <div className="cp2-m-compare">
        <div className="cp2-m-tile"><span className="cp2-m-label">Current</span><strong>{from.name}</strong><small>{from.purpose}</small></div>
        <span className="cp2-m-arrow" aria-hidden="true"><ArrowRight size={16} /></span>
        <div className="cp2-m-tile is-new"><span className="cp2-m-label">New</span><strong>{to.name}</strong><small>{to.purpose}</small></div>
      </div>
      <div className="cp2-m-callout"><span className="cp2-m-callout-icon"><RefreshCw size={15} /></span><div><strong>A new brief will be generated</strong><p>This call already has a brief. Changing the type regenerates the call preparation brief with the {to.name} skill. The current brief stays available as an earlier version.</p></div></div>
      <footer className="cp2-m-footer"><span className="cp2-m-meta"><Clock3 size={13} />Builds when the call is next opened</span><div className="cp2-m-actions"><button className="button button-outline" onClick={() => setTypeChange(null)}>Keep {from.name}</button><button className="button button-primary" onClick={() => { applyType(typeChange.call, typeChange.to, true); setTypeChange(null); }}><Wand2 size={14} />Change and regenerate</button></div></footer>
    </Dialog>; })()}
    {genFor && <RegenerateDialog title="Generate the brief" viewer={props.viewer} clientName={`${clientById(genFor.clientId).name} · ${dateLabel(genFor.date, { weekday: 'short', day: 'numeric', month: 'short' })}, ${time12(genFor.time)}`} skill={templateFor(typeOf(genFor)).name} nextN={1} close={() => setGenFor(null)} submit={v => { pendingGeneration.set(genFor.id, v); setGenFor(null); props.open(genFor.id); }} />}
    {skillsOpen && <SkillsDialog viewer={props.viewer} admin={admin} upcoming={k => calls.filter(c => typeOf(c) === k).length} notify={props.notify} close={() => setSkillsOpen(false)} />}
    {LIVE && EXCLUDED_CALLS.length > 0 && <details className="cp2-panel cp2-excluded"><summary>Not client calls ({EXCLUDED_CALLS.length}): set aside, no brief</summary><ul className="cp2-list plain">{EXCLUDED_CALLS.map(x => <li key={x.id}><p><strong>{x.title}</strong> · {dateLabel(x.date, { weekday: 'short', day: 'numeric', month: 'short' })}, {time12(x.time)}</p><small>{x.why}</small> <button type="button" className="text-button" onClick={() => api(`/api/v1/calls/${x.id}/override`, 'PUT', { excluded: false, viewer: props.viewer }).then(() => props.notify('Marked as a client call. It appears in the queue after the next refresh.')).catch(e => props.notify(e.message))}>This is a client call</button></li>)}</ul></details>}
    {layout === 'board' ? <div className="cp2-board">{BUCKETS.map(([id, label]) => { const list = calls.filter(c => bucketOf(c.date) === id); return <section key={id} className="cp2-col" aria-label={label}>
      <header><h2>{label}</h2><span className="cp2-count">{list.length}</span><small>{dayLabel(id)}</small></header>
      {list.length ? <ul>{list.map(card)}</ul> : <p className="cp2-empty">No calls.</p>}
    </section>; })}</div>
    : <div className="cp2-table-wrap cp2-meet-table"><table className="cp2-table"><thead><tr><th>When</th><th>Client</th><th>Call type</th><th>Host</th><th>Brief</th><th /></tr></thead>
      <tbody>{BUCKETS.flatMap(([id, label]) => { const list = calls.filter(c => bucketOf(c.date) === id); return list.length ? [<tr key={id} className="cp2-group"><td colSpan={6}>{label} · {list.length}</td></tr>, ...list.map(c => { const client = clientById(c.clientId); return <tr key={c.id} className={c.state === 'Cancelled' ? 'is-cancelled' : ''} onClick={() => props.open(c.id)}>
        <td><strong>{dateLabel(c.date, { weekday: 'short', day: 'numeric', month: 'short' })}</strong><small>{time12(c.time)} · {c.duration}</small></td>
        <td><span className="cp2-meet-client"><Avatar client={client} small /><strong>{client.name}</strong></span></td>
        <td>{typePicker(c)}</td>
        <td>{c.host === props.viewer ? 'You' : c.host}</td>
        <td><span className="cp2-state-wrap"><span className={`cp2-state ${stateClass(stateOf(c))}`}>{stateLabel(c)}</span>{stateOf(c) === 'Scheduled' && (LIVE || c.brief) && <button type="button" className="cp2-gen-icon" title="Generate the brief now" aria-label={`Generate the brief for ${clientById(c.clientId).name} now`} onClick={e => { e.stopPropagation(); setGenFor(c); }}><Wand2 size={12} /></button>}</span></td>
        <td><ChevronRight size={15} /></td></tr>; })] : []; })}</tbody></table>{!calls.length && <p className="cp2-empty">No calls in this range.</p>}</div>}
  </div>;
}

// ---- Regenerate with a custom prompt ------------------------------------------
type BriefVersion = { n: number; by: string; at: string; skill: string; prompt?: string; focus?: string[]; tone?: string[]; scope?: 'call' | 'template'; refused?: string[] };

function RegenerateDialog({ title = 'Regenerate the brief', viewer, clientName, skill, last, nextN, close, submit }: { title?: string; viewer: string; clientName: string; skill: string; last?: BriefVersion; nextN: number; close: () => void; submit: (v: Omit<BriefVersion, 'n' | 'by' | 'at'>) => void }) {
  const [prompt, setPrompt] = useState(last?.prompt || '');
  const [chosen, setChosen] = useState(skill);
  const [picking, setPicking] = useState(false);
  const refused = refusals(prompt, viewer);
  const options = [{ name: DEFAULT_SKILL, purpose: 'The same core sections for every call (runs automatically 2 hours before)' }, ...TEMPLATES.map(t => ({ name: t.name, purpose: t.purpose }))];
  const current = options.find(o => o.name === chosen)!;
  const MAX = 500;
  return <Dialog title={title} subtitle={clientName} className="cp2-modal" onClose={close}>
    <section className="cp2-m-section">
      <p className="cp2-m-label">Skill</p>
      <button type="button" className="cp2-m-skill" aria-expanded={picking} onClick={() => setPicking(v => !v)}>
        <span className="cp2-m-skill-icon"><Wand2 size={16} /></span>
        <span className="cp2-m-skill-text"><strong>{current.name}</strong><small>{current.purpose}</small></span>
        <span className="cp2-m-chip">{picking ? 'Done' : 'Switch'}<ChevronRight size={13} className={picking ? 'is-open' : ''} /></span>
      </button>
      {picking && <ul className="cp2-m-options" role="listbox" aria-label="Skills">{options.map(o => <li key={o.name}><button type="button" role="option" aria-selected={o.name === chosen} className={o.name === chosen ? 'selected' : ''} onClick={() => { setChosen(o.name); setPicking(false); }}><span><strong>{o.name}</strong>{o.name === skill && <em>This call’s type</em>}<small>{o.purpose}</small></span>{o.name === chosen && <Check size={15} />}</button></li>)}</ul>}
    </section>
    <section className="cp2-m-section">
      <label className="cp2-m-label" htmlFor="cp2-m-prompt">Additional instructions <span>Optional</span></label>
      <textarea id="cp2-m-prompt" className="cp2-m-textarea" rows={4} maxLength={MAX} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Add context for this brief, e.g. “Focus on why she missed office hours and what she said about budget”" />
      <div className="cp2-m-under"><span>Added on top of the selected skill.</span><span>{prompt.length}/{MAX}</span></div>
    </section>
    {refused.map(r => <div key={r} className="cp2-m-callout is-warn"><span className="cp2-m-callout-icon"><Ban size={15} /></span><div><strong>Part of this will be skipped</strong><p>{r}</p></div></div>)}
    <p className="cp2-m-note"><ShieldCheck size={13} />Instructions can narrow or re-focus the brief, never widen it beyond approved sources or your access. Facts stay cited.</p>
    <footer className="cp2-m-footer"><span className="cp2-m-meta"><FileText size={13} />Creates version {nextN}; earlier versions stay available</span><div className="cp2-m-actions"><button className="button button-outline" onClick={close}>Cancel</button><button className="button button-primary" onClick={() => submit({ prompt: prompt.trim(), skill: chosen, refused })}><Wand2 size={14} />{title === 'Regenerate the brief' ? 'Regenerate brief' : 'Generate brief'}</button></div></footer>
  </Dialog>;
}

// ---- Call-type skills: list, then the clicked skill's full content (editable by admins) ----
const ALL_SECTIONS = Object.keys(SECTION_LABELS) as SectionKey[];
const same = (a: Skill, b: Skill) => JSON.stringify(a) === JSON.stringify(b);

function SkillsDialog({ viewer, admin, upcoming, notify, close }: { viewer: string; admin: boolean; upcoming: (k: CallTypeKey) => number; notify: (m: string) => void; close: () => void }) {
  const [openKey, setOpenKey] = useState<SkillKey | null>(null);
  const [draft, setDraft] = useState<Skill | null>(null);
  const [, rerender] = useState(0);
  const open = (k: SkillKey) => { setOpenKey(k); setDraft(structuredClone(skillFor(k))); };
  const back = () => { setOpenKey(null); setDraft(null); };
  const edited = (k: SkillKey) => LIVE ? (SKILL_FILES.get(k)?.edited ? { by: SKILL_FILES.get(k)!.edited!.by.split(' · ')[0], on: SKILL_FILES.get(k)!.edited!.at.slice(0, 10) } : undefined) : skillEdits.get(k);
  const card = (sk: Skill, state: ReactNode) => <button type="button" className={`cp2-skill ${sk.key === 'default' ? 'is-default' : ''}`} key={sk.key} onClick={() => open(sk.key)}>
    <header><strong>{sk.name}</strong>{state}</header>
    <p>{sk.purpose}. {sk.key !== 'default' && <span className="cp2-muted">Detected by: {sk.detect}.</span>}</p>
    <div className="chip-row">{sk.sections.map(sec => <span key={sec} className="pick-chip on static">{SECTION_LABELS[sec]}</span>)}</div>
    <p className="cp2-muted">Leaves out: {sk.leaveOut}</p>
    <span className="cp2-skill-open">{edited(sk.key) ? <em>Edited by {edited(sk.key)!.by}</em> : <span />}{admin ? 'Open & edit' : 'Open'}<ChevronRight size={13} /></span>
  </button>;

  if (!openKey || !draft) return <Dialog title="Call-type skills" subtitle="HOW BRIEFS ARE BUILT" className="slack-dialog cp2-skills" onClose={close}>
    <p className="hint">Every brief builds automatically <strong>2 hours before the call</strong> with the default skill. Anyone preparing the call can run the call-type skill on demand, with extra instructions if they want. Click a skill to see exactly what it does{admin ? ' and edit it' : ''}.</p>
    <div className="cp2-skill-grid">
      {card(DEFAULT_SKILL_SPEC, <span className="cp2-state st-ready">Automatic · 2 h before</span>)}
      {TEMPLATES.map(t => { const n = upcoming(t.key); return card(t, <span className="cp2-state st-scheduled">On demand{n ? ` · ${n} upcoming` : ''}</span>); })}
    </div>
  </Dialog>;

  const original = skillFor(openKey);
  const isDefault = openKey === 'default';
  const dirty = !same(draft, original);
  const set = (patch: Partial<Skill>) => setDraft(d => ({ ...d!, ...patch }));
  const toggleSection = (sec: SectionKey) => sec !== 'limits' && set({ sections: draft.sections.includes(sec) ? draft.sections.filter(x => x !== sec) : ALL_SECTIONS.filter(x => x === sec || draft.sections.includes(x)) });
  const save = () => {
    if (LIVE) {
      const file = SKILL_FILES.get(openKey);
      if (!file) return;
      const text = skillText(file.text, draft);
      api<{ version: number }>(`/api/v1/call-skills/${openKey}`, 'POST', { text, viewer })
        .then(r => { SKILL_FILES.set(openKey, { ...file, text, edited: { by: me(viewer), at: new Date().toISOString(), version: r.version } }); saveSkill({ ...draft }, viewer, DEMO_DATE); rerender(n => n + 1); setDraft(structuredClone(skillFor(openKey))); notify(`${draft.name} saved as version ${r.version}. Upcoming briefs of this type rebuild with it.`); })
        .catch(e => notify(e.message));
      return;
    }
    saveSkill({ ...draft, name: draft.name.trim() || original.name, agenda: draft.agenda.map(a => a.trim()).filter(Boolean) }, viewer, DEMO_DATE); rerender(n => n + 1); setDraft(structuredClone(skillFor(openKey))); notify(`${draft.name} saved. Briefs built from now on use the new version.`); };
  const reset = () => {
    if (LIVE) { api(`/api/v1/call-skills/${openKey}/revert/1`, 'POST', { viewer }).then(() => notify(`${original.name}: the first version is current again. Reopen the dialog after the next refresh to see it.`)).catch(e => notify(e.message)); return; }
    resetSkill(openKey); setDraft(structuredClone(skillFor(openKey))); rerender(n => n + 1); notify(`${original.name} restored to the original.`); };
  const ro = !admin;
  return <Dialog title={draft.name || original.name} subtitle="CALL-TYPE SKILL" className="slack-dialog cp2-skills cp2-skill-detail" onClose={close}>
    <div className="cp2-sd-top">
      <button type="button" className="text-button" onClick={() => { if (!dirty || window.confirm('Discard your unsaved changes?')) back(); }}><ArrowLeft size={13} />All skills</button>
      <span className={`cp2-state ${isDefault ? 'st-ready' : 'st-scheduled'}`}>{isDefault ? 'Automatic · 2 h before' : 'On demand'}</span>
      {edited(openKey) && <span className="cp2-muted">Edited by {edited(openKey)!.by} · {dateLabel(edited(openKey)!.on)}</span>}
    </div>
    {ro && <p className="cp2-sd-lock"><Lock size={12} />Read-only. Only admins (Whitney, Gisselle) edit skills.</p>}
    <div className="cp2-sd-form">
      {!isDefault && <label className="cp2-sd-field">Name<input value={draft.name} disabled={ro} maxLength={60} onChange={e => set({ name: e.target.value })} /></label>}
      <label className="cp2-sd-field">Purpose<input value={draft.purpose} disabled={ro} maxLength={120} onChange={e => set({ purpose: e.target.value })} /></label>
      <label className="cp2-sd-field">When it’s used<input value={draft.detect} disabled={ro || isDefault || LIVE} maxLength={140} onChange={e => set({ detect: e.target.value })} /><small>{isDefault ? 'Runs for every call; this can’t change.' : 'How a calendar event is matched to this call type.'}</small></label>
      <div className="cp2-sd-field"><span>Sections in the brief</span><div className="chip-row">{ALL_SECTIONS.filter(sec => !(isDefault && sec === 'typeBlock')).map(sec => <button type="button" key={sec} disabled={ro || sec === 'limits'} aria-pressed={draft.sections.includes(sec)} className={`pick-chip ${draft.sections.includes(sec) ? 'on' : ''}`} onClick={() => toggleSection(sec)} title={sec === 'limits' ? 'Always included: every brief states its sources and gaps' : undefined}>{draft.sections.includes(sec) && <Check size={11} />}{sec === 'typeBlock' ? (draft.typeBlock || SECTION_LABELS[sec]) : SECTION_LABELS[sec]}</button>)}</div><small>Sources &amp; limits is always included.</small></div>
      {!isDefault && <label className="cp2-sd-field">Type-specific block<input value={draft.typeBlock} disabled={ro} maxLength={60} onChange={e => set({ typeBlock: e.target.value })} placeholder="e.g. Access checklist & what was sold" /><small>The extra card this call type adds to the brief.</small></label>}
      <div className="cp2-sd-field"><span>Suggested agenda</span>
        <ol className="cp2-sd-agenda">{draft.agenda.map((item, i) => <li key={i}><input value={item} disabled={ro} maxLength={100} aria-label={`Agenda item ${i + 1}`} onChange={e => set({ agenda: draft.agenda.map((x, j) => j === i ? e.target.value : x) })} />{!ro && <button type="button" className="icon-button" aria-label={`Remove agenda item ${i + 1}`} onClick={() => set({ agenda: draft.agenda.filter((_, j) => j !== i) })}><X size={13} /></button>}</li>)}</ol>
        {!ro && draft.agenda.length < 8 && <button type="button" className="text-button" onClick={() => set({ agenda: [...draft.agenda, ''] })}><Plus size={12} />Add an agenda item</button>}
      </div>
      <label className="cp2-sd-field">Guidance for the brief writer<textarea rows={4} value={draft.guidance || ''} disabled={ro} maxLength={600} onChange={e => set({ guidance: e.target.value })} /><small>How the brief should read for this call type. It can narrow or re-focus a brief, never widen its sources.</small></label>
      <label className="cp2-sd-field">Leaves out<input value={draft.leaveOut} disabled={ro} maxLength={120} onChange={e => set({ leaveOut: e.target.value })} /></label>
    </div>
    {admin && <footer className="cp2-sd-footer">
      {edited(openKey) ? <button type="button" className="text-button" onClick={reset}><RotateCcw size={12} />Restore original</button> : <span />}
      <div className="cp2-m-actions"><button className="button button-outline" disabled={!dirty} onClick={() => setDraft(structuredClone(original))}>Discard</button><button className="button button-primary" disabled={!dirty} onClick={save}><Check size={14} />Save changes</button></div>
    </footer>}
  </Dialog>;
}

/** The skill file with the dialog's fields written back: frontmatter values and the body sections. Detection
 *  patterns are kept as they are (the KB validates the whole file and refuses a broken one). */
function skillText(text: string, d: Skill): string {
  const front = (src: string, key: string, value: string) => src.replace(new RegExp(`^${key}:.*$`, 'm'), `${key}: ${value}`);
  const section = (src: string, heading: string, body: string) => src.replace(new RegExp(`(## ${heading}\\n)[\\s\\S]*?(?=\\n## |$)`), (_m, h) => `${h}${body.trim()}\n`);
  let out = front(text, 'name', JSON.stringify(d.name));
  out = front(out, 'purpose', JSON.stringify(d.purpose));
  out = front(out, 'type_block', JSON.stringify(d.typeBlock || ''));
  out = front(out, 'sections', `[${d.sections.join(', ')}]`);
  out = section(out, 'Agenda skeleton', d.agenda.map((a, i) => `${i + 1}. ${a}`).join('\n'));
  out = section(out, 'Guidance', d.guidance || '');
  out = section(out, 'Leave out', d.leaveOut);
  return out;
}
