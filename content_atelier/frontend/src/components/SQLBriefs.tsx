import React, {useEffect, useState} from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import type { AngleResearch, BriefWriteResult, StoredBriefDocument as BriefDocument, BriefEvidence, BriefVersion, CalendarConfig, StoredBrief, StoredBriefV1 } from '../api/types';
import type { FormatDirection as BriefFormat, Claim as BriefClaim } from '../api/schema';
import { useQueryClient } from '@tanstack/react-query';
import { queryKey, useApiQuery, useInvalidate } from '../api/query';
import {storageRequest} from '../utils/weeklyStorage';
import {useFeatureFlags} from '../utils/workspace';
import { useMe } from '../utils/me';
import { BriefReaderV2, briefDecisionRequest } from './BriefReaderV2';
import { BriefGateV4, briefTitle } from './BriefReaderV4';
import { PublishedCapture } from './PublishedCapture';
import { PackHandover, handoverNote, isV4Brief, type HandOver } from './PackHandover';
import {AngleResearchPanel, angleLink} from './BriefStatus';
import { paths } from '../app/routes';
import { StageProgress } from './shared/JobProgress';
import { ActionError, ConflictNotice, useGuardedAction } from './shared/conflict';
import { focusKey, focusKeyPrefix, useWriteFeedback } from './shared/a11y';
import { EmptyState, ErrorState, LoadingState } from './shared/states';
import { useWeekList } from './shared/WeekPicker';
import { BriefCard, briefCardFocusKey, briefOfferText, briefSearchText } from './studio/BriefCard';
import { CardGrid, EmptyStage, Fold, StageSection, StudioModal, cardDay, matches } from './studio/parts';
import { currentPacks, useStudioContext, weekBriefsArgs, weekPacksArgs } from './studio/studioWeek';
import { weekWords } from '../utils/editorialWeeks';
import { Select } from './ThemedSelect';
import { TAKES, TimeNote } from './studio/GenerationTime';
const button='rounded-lg border px-3 py-2 text-sm disabled:opacity-40';
const label=(s:string)=>s.replaceAll('_',' ');

export function BriefRead({brief}:{brief:StoredBriefV1}) {
  const d=brief.content_body.document;
  return <div className="space-y-4">
    <h2 className="text-2xl font-editorial">{d.title}</h2>
    <p><strong>Approved angle:</strong> {d.angle_statement}</p><p><strong>Audience:</strong> {d.audience}</p>
    <p><strong>Reader decision:</strong> {d.reader_decision}</p><p><strong>CTA:</strong> {d.cta.text}</p>
    {(['reader_promise','positioning','why_now','core_insight','audience_pain','differentiation','similarity_review'] as const).map(k=><div key={k}><h3 className="font-medium capitalize">{label(k)}</h3><p>{d[k] || 'Not supplied'}</p></div>)}
    {(['message_spine','narrative','evidence_boundaries','voice','creative_direction','accessibility','distribution','evaluation_signals','claims_requiring_consent','handoff_checklist'] as const).map(k=><div key={k}><h3 className="font-medium capitalize">{label(k)}</h3><ul className="list-disc pl-5">{d[k].map((v,i)=><li key={i}>{v}</li>)}</ul></div>)}
    <h3 className="font-medium">Claims and grounding</h3>{d.claims.map(c=><div key={c.claim_id} className="border rounded p-3"><p>{c.text}</p><p className="text-sm">{label(c.kind)} · {c.source_status}</p><p>{c.qualifications.join('; ')}</p>{c.quote&&<blockquote>{c.quote}</blockquote>}{c.numeric_facts.map((f,i)=><p key={i}>{f.value} {f.unit} · {f.timeframe} · {f.subject}<br/>{f.source_quote} [{f.evidence_id}]</p>)}<p className="text-sm">Sources: {c.evidence_ids.join(', ')}</p></div>)}
    {[{name:'Email',...d.email},...d.reels.map((r,i)=>({name:`Reel ${i+1}`,...r}))].map(r=><div key={r.name}><h3 className="font-medium">{r.name} · {r.reader_job}</h3><p>{r.direction}</p><ol className="list-decimal pl-5">{r.outline.map((v,i)=><li key={i}>{v}</li>)}</ol></div>)}
    <div><h3 className="font-medium">Carousel · {d.carousel_reader_job}</h3><ol className="list-decimal pl-5">{d.carousel.map(s=><li key={s.number}>{s.direction}</li>)}</ol></div>
    <h3 className="font-medium">Prior coverage</h3>{brief.prior_content_context.map(p=><div key={p.angle_id} className="border p-3 rounded"><p>{p.argument}</p><p>Angle {p.approval_status}; {p.briefs.length} recorded briefs; {p.publications.length} calendar records.</p><p>{d.prior_differences[p.angle_id]}</p></div>)}
    <h3 className="font-medium">Evidence and research limits</h3><p>Legacy publication coverage is incomplete. Similarity and retrieval ranks do not establish factual support.</p>
    {brief.research_gaps.items.map((v,i)=><p key={i}>{v}</p>)}
    <EvidenceList items={brief.selected_evidence}/>
  </div>;
}
function EvidenceList({items}:{items:BriefEvidence[]}) {return <div className="space-y-2">{items.map(e=><details key={e.evidence_id} className="border rounded p-3"><summary>{e.title} · {label(e.role)} · {e.claim_status}</summary><blockquote className="whitespace-pre-wrap mt-2">{e.excerpt}</blockquote><p className="text-sm mt-2">{e.transcript_id} · {e.passage_id} · characters {e.start}–{e.end}</p><p>{e.qualifications.join('; ')}</p><p>Public use {e.public_use?'confirmed':'unconfirmed'} · attribution {e.attribution_verified?'confirmed':'unverified'}</p>{e.source_url&&/^https?:\/\//.test(e.source_url)&&<a className="underline" href={e.source_url} target="_blank" rel="noreferrer">Original source</a>}</details>)}</div>;}

function FormatEditor({name,value,onChange}:{name:string;value:BriefFormat;onChange:(v:BriefFormat)=>void}) {return <fieldset className="border rounded p-3"><legend>{name}</legend>{(['reader_job','direction','outline'] as const).map(k=><label key={k} className="block">{label(k)}<textarea className="border rounded p-2 block w-full" value={Array.isArray(value[k])?(value[k] as string[]).join('\n'):value[k] as string} onChange={e=>onChange({...value,[k]:k==='outline'?e.target.value.split('\n').filter(Boolean):e.target.value})}/></label>)}</fieldset>;}
function ClaimEditor({value,onChange,evidence}:{value:BriefClaim;onChange:(v:BriefClaim)=>void;evidence:BriefEvidence[]}) {return <fieldset className="border rounded p-3 space-y-2"><legend>{value.claim_id}</legend><label>Claim<textarea className="border rounded p-2 block w-full" value={value.text} onChange={e=>onChange({...value,text:e.target.value})}/></label><label>Claim kind<Select className="border p-2" value={value.kind} onChange={e=>onChange({...value,kind:e.target.value as BriefClaim['kind']})}>{['source_assertion','inference','hypothesis','instruction','external_context'].map(k=><option key={k} value={k}>{label(k)}</option>)}</Select></label><label className="block">Source status<input className="border p-2" value={value.source_status} onChange={e=>onChange({...value,source_status:e.target.value as BriefClaim['source_status']})}/></label><label className="block">Qualifications<textarea className="border rounded p-2 block w-full" value={value.qualifications.join('\n')} onChange={e=>onChange({...value,qualifications:e.target.value.split('\n').filter(Boolean)})}/></label><label className="block">Exact quotation<textarea className="border rounded p-2 block w-full" value={value.quote||''} onChange={e=>onChange({...value,quote:e.target.value||null})}/></label><label className="flex gap-2"><input type="checkbox" checked={value.public_quote} onChange={e=>onChange({...value,public_quote:e.target.checked})}/>Use quotation publicly; actual clearance is required</label><label className="block">Supporting passages<select multiple className="border p-2 block w-full" value={value.evidence_ids} onChange={e=>onChange({...value,evidence_ids:Array.from(e.target.selectedOptions,o=>o.value)})}>{evidence.map(e=><option key={e.evidence_id} value={e.evidence_id}>{e.title} · {e.passage_id||e.role}</option>)}</select></label>{value.numeric_facts.map((f,i)=><fieldset key={i} className="border rounded p-3"><legend>Source-bound quantity</legend>{(['value','unit','timeframe','subject','source_quote'] as const).map(k=><label className="block" key={k}>{label(k)}<input className="border rounded p-2 w-full" value={f[k]} onChange={e=>onChange({...value,numeric_facts:value.numeric_facts.map((x,n)=>n===i?{...x,[k]:e.target.value}:x)})}/></label>)}<label>Supporting evidence<Select className="border p-2" value={f.evidence_id} onChange={e=>onChange({...value,numeric_facts:value.numeric_facts.map((x,n)=>n===i?{...x,evidence_id:e.target.value}:x)})}><option value="">Choose passage</option>{evidence.filter(e=>value.evidence_ids.includes(e.evidence_id)).map(e=><option key={e.evidence_id} value={e.evidence_id}>{e.title} · {e.passage_id}</option>)}</Select></label><button className={button} onClick={()=>onChange({...value,numeric_facts:value.numeric_facts.filter((_,n)=>n!==i)})}>Remove quantity</button></fieldset>)}<button className={button} onClick={()=>onChange({...value,numeric_facts:[...value.numeric_facts,{value:'',unit:'',timeframe:'',subject:'',evidence_id:'',source_quote:''}]})}>Add a source-bound quantity</button></fieldset>;}

const ACTIVE = ['queued', 'running'];
/** A brief's approval status in a reviewer's words. */
export const BRIEF_STATUS: Record<string, string> = { pending: 'waiting for review', approved: 'approved', rejected: 'rejected' };
/** A week id as the dates it covers (utils/editorialWeeks), kept here for the screens that import it from the brief screen. */
export { weekWords };

/** What a Gate 2 write did, in a sentence for the live region (6.F6). */
export function briefWriteMessage(path: string, method = 'POST', body?: unknown): string {
  if (method === 'PATCH') return 'Saved as a new version of the brief.';
  if (/\/decision$/.test(path)) return (body as { decision?: string } | undefined)?.decision === 'rejected' ? 'Brief rejected.' : 'Brief approved.';
  if (/\/answers$/.test(path)) return 'Answers saved.';
  if (/\/review$/.test(path)) return 'Your check is recorded.';
  if (/\/clearance$/.test(path)) return 'Permission recorded.';
  if (/\/revise$/.test(path)) return `Refresh started. The new version opens here in ${TAKES.brief}.`;
  if (/\/cta$/.test(path)) return 'CTA confirmed.';
  if (/\/context$/.test(path)) return 'Added to the brief.';
  if (/\/pack$/.test(path)) return `Content pack started. It takes ${TAKES.pack}.`;
  if (/\/retry$/.test(path)) return 'Trying that step again.';
  return 'Saved.';
}

/** The focus key of a brief's status line at one version and approval (the panel is keyed the same way). */
export const briefFocusKey = (b: Pick<StoredBrief, 'brief_id' | 'content_hash' | 'approval_status'>) => `brief:${b.brief_id}:${b.content_hash}:${b.approval_status}`;

/** The Content Briefing step of the Weekly Studio (`/studio/briefs?week=<week>`), as the 20 October mockup: the week's briefs
    awaiting approval as cards, then the approved ones with their packs, with briefs that were not approved folded below. When
    the URL names a brief (`/studio/briefs/:briefId`) the whole Gate 2 reader and editor opens in the brief dialog over the week
    the brief belongs to. What a write did is said here, above the dialog, since the dialog's panel is keyed by the brief's
    version and starts afresh after a write (6.F6). */
export function SQLBriefs() {
  const { briefId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [search, setSearch] = useSearchParams();
  const flags = useFeatureFlags();
  const { latest, weeks: listed } = useWeekList();
  const named = search.get('week') ?? '';
  const brief = useApiQuery('/briefs/{brief_id}', { path: { brief_id: briefId ?? '' } }, { enabled: !!briefId });
  const week = named || brief.data?.week_id || latest;
  // A brief opened by its link alone shows its own week behind it.
  useEffect(() => {
    const own = brief.data?.week_id;
    if (briefId && !named && own) setSearch(prev => { const next = new URLSearchParams(prev); next.set('week', own); return next; }, { replace: true });
  }, [briefId, named, brief.data?.week_id, setSearch]);
  const list = useApiQuery('/briefs', weekBriefsArgs(week), { enabled: !!week });
  const packs = useApiQuery('/packs', weekPacksArgs(week), { enabled: !!week && flags.packs,
    refetchInterval: data => data?.items.some(p => p.state === 'finishing' || p.state === 'waiting') ? 10_000 : 30_000 });
  const pendingAll = useApiQuery('/briefs', { query: { status: 'pending', limit: 50, offset: 0 } });
  const angleId = brief.data?.angle_id;
  const research = useApiQuery('/angles/{angle_id}/research', { path: { angle_id: angleId ?? '' } }, {
    enabled: !!angleId, refetchInterval: data => ACTIVE.includes(data?.status ?? '') ? 8_000 : 30_000,
  });
  const versions = useApiQuery('/briefs/{brief_id}/versions', { path: { brief_id: briefId ?? '' } }, { enabled: !!briefId });
  const config = useApiQuery('/calendar/config', undefined, { staleTime: 30_000 });
  const { query, offer } = useStudioContext();
  // What each approval answered about the content pack it started (NP.F3). Kept here, above the brief's panel, because the
  // panel is keyed by the brief's version and approval, so it starts afresh once the brief is approved.
  const [started, setStarted] = useState<Record<string, HandOver>>({});
  const client = useQueryClient();
  const invalidate = useInvalidate();
  const feedback = useWriteFeedback();
  const written = (text: string, id: string) => {
    const fresh = client.getQueryData<StoredBrief>(queryKey('/briefs/{brief_id}', { path: { brief_id: id } }));
    feedback.announce(text, fresh ? focusKey(briefFocusKey(fresh)) : focusKeyPrefix(`brief:${id}:`));
  };
  // "Approve & generate pack" from a card: the same decision as the full brief's, with nothing left to settle.
  const guard = useGuardedAction(() => list.refetch());
  const approve = (b: StoredBrief) => guard.run(async () => {
    const request = briefDecisionRequest(b.content_hash, 'approved', '', '', '');
    if ('error' in request) throw new Error(request.error);
    const result = await storageRequest<BriefWriteResult>(`/briefs/${b.brief_id}/decision`, 'POST', request.body);
    if (result.pack_run || result.pack_note) setStarted(s => ({ ...s, [b.brief_id]: { pack_run: result.pack_run ?? null, pack_note: result.pack_note ?? null } }));
    await invalidate('/briefs', '/briefs/{brief_id}', '/briefs/{brief_id}/versions', '/packs', '/summary', '/weeks/{week_id}');
    return true;
  }).then(ok => { if (ok) feedback.announce(flags.packs && isV4Brief(b) ? `Brief approved. Its content pack is being made, which takes ${TAKES.pack}.` : 'Brief approved.', focusKey(briefCardFocusKey(b.brief_id))); });
  // "View brief →" from an angle card scrolls to the brief's card.
  useEffect(() => {
    const id = /^#brief-(.+)$/.exec(location.hash)?.[1];
    if (id && list.data) document.getElementById(`brief-${id}`)?.scrollIntoView?.({ block: 'start' });
  }, [location.hash, list.data]);
  const items = (list.data?.items ?? []).filter(b => !b.has_replacement && matches(briefSearchText(b), briefOfferText(b), query, offer));
  const filtering = !!query.trim() || offer !== 'all';
  const pending = items.filter(b => b.approval_status === 'pending');
  const approved = items.filter(b => b.approval_status === 'approved');
  const rejected = items.filter(b => b.approval_status === 'rejected');
  const weekPacks = currentPacks(packs.data?.items);
  const packFor = (b: StoredBrief) => weekPacks.find(p => p.source_brief_id === b.brief_id);
  const hrefFor = (b: StoredBrief) => `${paths.brief(b.brief_id)}?week=${encodeURIComponent(b.week_id || week)}`;
  // Only weeks Previous Concepts shows: an archived week's briefs are not waiting for anyone.
  const shownWeeks = new Set((listed.data ?? []).map(w => w.week_id));
  const earlier = (pendingAll.data?.items ?? []).filter(b => b.week_id !== week && shownWeeks.has(b.week_id)).length;
  const card = (b: StoredBrief) => <BriefCard key={b.brief_id + b.content_hash} brief={b} week={week} pack={packFor(b)} packsOn={flags.packs}
    packMaking={!!started[b.brief_id]?.pack_run?.pack_id} busy={guard.busy} onApprove={() => void approve(b)} fullBriefHref={hrefFor(b)} />;
  const closeTo = `${paths.briefs}${week ? `?week=${encodeURIComponent(week)}` : ''}`;
  return <section aria-label="Content briefs" className="space-y-8">
    {feedback.region}
    <ConflictNotice conflict={guard.conflict} onReload={() => void guard.reloadLatest()} onDismiss={guard.clear} />
    <ActionError message={guard.error} />
    {list.error && <ErrorState message={list.error.message} onRetry={() => void list.refetch()} />}
    {week && list.isPending && !list.error && <LoadingState>Loading briefs…</LoadingState>}
    {list.data && <>
      <StageSection title="Awaiting approval" count={pending.length} label="Briefs awaiting approval" description="Generated from approved angles. Review the brief before creating its pack.">
        {pending.length ? <CardGrid>{pending.map(card)}</CardGrid>
          : <EmptyStage>{filtering ? 'No briefs match this view.' : 'Approve an angle to bring its brief here.'}</EmptyStage>}
      </StageSection>
      {earlier > 0 && <p className="text-[12px] text-[#8B93A3]">{earlier} more {earlier === 1 ? 'brief waits' : 'briefs wait'} for approval in earlier weeks · <Link className="text-[#5070FF] font-medium" to={`${paths.previous}?stage=briefs`}>Previous Concepts <span aria-hidden="true">→</span></Link></p>}
      <StageSection title="Approved" count={approved.length} label="Approved briefs" description="The source briefs behind your generated content packs. Approval history stays visible.">
        {approved.length ? <CardGrid>{approved.map(card)}</CardGrid>
          : <EmptyStage>{filtering ? 'No briefs match this view.' : 'Approved briefs will be retained here.'}</EmptyStage>}
      </StageSection>
      {rejected.length > 0 && <Fold label="Briefs not approved" summary={`Not approved (${rejected.length})`}><CardGrid>{rejected.map(card)}</CardGrid></Fold>}
    </>}
    {briefId && <StudioModal title={brief.data ? briefTitle(brief.data) : 'The brief'} label={brief.data ? `Brief: ${briefTitle(brief.data)}` : 'The brief'} onClose={() => navigate(closeTo)}
      footerNote={brief.data?.created_at ? `Written ${cardDay(brief.data.created_at)}` : undefined}
      tabs={brief.data ? [
        { id: 'angle', label: 'Content Angle', onSelect: () => navigate(paths.angle(brief.data!.week_id, brief.data!.angle_id)) },
        { id: 'brief', label: 'Content Brief', selected: true },
        { id: 'pack', label: 'Content Pack', disabled: !packFor(brief.data), title: packFor(brief.data) ? undefined : 'The content pack is made once the brief is approved.',
          onSelect: () => { const p = brief.data && packFor(brief.data); if (p) navigate(paths.studioPack(p.pack_id)); } },
        { id: 'schedule', label: 'Schedule', disabled: true, title: 'Publishing dates are proposed with the week’s content packs.' },
      ] : undefined}>
      {brief.isPending && !brief.error && <LoadingState>Loading the brief…</LoadingState>}
      {brief.error && !brief.data && <ErrorState message={brief.error.message} onRetry={() => void brief.refetch()} />}
      {brief.data && <BriefPanel key={brief.data.brief_id + brief.data.content_hash + brief.data.approval_status} brief={brief.data} research={research.data ?? null} versions={versions.data ?? []}
        productionConfig={config.data ?? null} packsEnabled={flags.packs} reload={() => brief.refetch()} onOpen={id => navigate(`${paths.brief(id)}${week ? `?week=${encodeURIComponent(week)}` : ''}`)}
        started={started[brief.data.brief_id]} onStarted={(id, handover) => setStarted(s => ({ ...s, [id]: handover }))} onWritten={written} />}
    </StudioModal>}
  </section>;
}

/** One brief and everything typed into it. It is keyed by brief and version, so typed answers, a draft edit or a decision
    never carry over to another brief (E.F4); a refused write (409) leaves them in place and offers the reload (1.F2). */
function BriefPanel({ brief, research, versions, productionConfig, packsEnabled, reload, onOpen, started, onStarted, onWritten }: {
  brief: StoredBrief; research: AngleResearch | null; versions: BriefVersion[]; productionConfig: CalendarConfig | null; packsEnabled: boolean;
  reload: () => unknown; onOpen: (briefId: string) => void; started?: HandOver; onStarted: (briefId: string, handover: HandOver) => void;
  onWritten?: (text: string, briefId: string) => void;
}) {
  const invalidate = useInvalidate();
  const { me } = useMe();
  // The Gate 2 hand-over (NP.F3): an approved v4 brief's content pack, found by the brief on every load.
  const handsOver = packsEnabled && isV4Brief(brief) && brief.approval_status === 'approved';
  const packs = useApiQuery('/packs', { query: { brief_id: brief.brief_id, limit: 5 } }, {
    enabled: handsOver,
    refetchInterval: data => data?.items.some(p => p.state === 'finishing' || p.state === 'waiting') || (!!started?.pack_run?.pack_id && !data?.items.length) ? 8_000 : false,
  });
  const hasPack = !!packs.data?.items.length || !!started?.pack_run?.pack_id;
  const canCreatePack = handsOver && brief.can_consume && (me.can.generate_packs || !!productionConfig?.can_generate);
  const [editor,setEditor]=useState<BriefDocument|null>(null),[answers,setAnswers]=useState<Record<string,string>>({});
  const [reason,setReason]=useState(''),[ack,setAck]=useState(false),[instructions,setInstructions]=useState(''),[selected,setSelected]=useState<string[]>([]);
  const [clearance,setClearance]=useState({evidence_id:'',permission_reference:'',attribution_reference:''});
  const guard = useGuardedAction(reload);
  const busy = guard.busy;
  const handsOverAfter=(data:unknown)=>packsEnabled&&isV4Brief(brief)&&(data as {decision?:string}|undefined)?.decision==='approved';
  const perform=async(path:string,method='POST',data?:unknown)=>{
    const opened=await guard.run(async()=>{
      const result=await storageRequest<BriefWriteResult>(path,method,data);
      // An approval of a v4 brief answers the content pack it started, or why none did (NP.B2).
      if(result.pack_run||result.pack_note)onStarted(brief.brief_id,{pack_run:result.pack_run??null,pack_note:result.pack_note??null});
      await invalidate('/briefs','/briefs/{brief_id}','/briefs/{brief_id}/versions','/angles/{angle_id}/research','/packs');
      const next=result.brief_id&&result.brief_id!==brief.brief_id?result.brief_id:brief.brief_id;
      if(next!==brief.brief_id)onOpen(next);
      return next;
    });
    if(opened)onWritten?.(/\/decision$/.test(path)&&handsOverAfter(data)?`Brief approved. Its content pack is being made, which takes ${TAKES.pack}.`:briefWriteMessage(path,method,data),opened);
  };
  const expected={expected_hash:brief.content_hash};
  return <>
    <ConflictNotice conflict={guard.conflict} onReload={() => void guard.reloadLatest()} onDismiss={guard.clear} />
    <ActionError message={guard.error} />
    <article className="bg-white p-5 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-5 text-[13px] text-[#34445F] [overflow-wrap:anywhere]">
      <div className="flex items-center justify-between gap-3"><div className="flex items-center gap-2.5">
        <span className="w-6 h-6 rounded-md bg-[#EFF3FF] text-[#5070FF] text-xs font-bold flex items-center justify-center border border-[#D1DBFF]">2</span>
        <h3 className="font-editorial text-lg font-bold text-[#221E17]">Content Brief</h3></div>
        <span className={`text-xs font-bold ${brief.approval_status === 'approved' ? 'text-emerald-700' : brief.approval_status === 'pending' ? 'text-amber-700' : 'text-slate-600'}`}>{brief.approval_status === 'approved' ? 'Approved' : brief.approval_status === 'pending' ? 'Awaiting approval' : 'Not approved'}</span></div>
      <p tabIndex={-1} data-focus-key={briefFocusKey(brief)} className="sr-only">{BRIEF_STATUS[brief.approval_status] ?? brief.approval_status}.</p>
      {/* Once the pack exists it is one tab away; until then, its progress or the button that makes it. */}
      {handsOver && packs.data?.items.some(p => p.state === 'finishing') && <TimeNote>The content pack is being made. It takes {TAKES.pack}, and you can close this and come back.</TimeNote>}
      {handsOver && !packs.data?.items.length && <PackHandover brief={brief} packs={[]} loading={packs.isPending && !packs.error} started={started} canCreate={canCreatePack} />}
      {handsOver && productionConfig?.worker_ready === false && !hasPack && <p role="status" className="text-sm text-amber-800">The editorial worker has no recent heartbeat. A content pack waits until it starts.</p>}
      {/* This brief's last run failed or waits for budget (a refresh, or its first writing): the reason and a retry per step. A
          v2 to v4 brief showed only that a refresh was running, so a failed refresh vanished on reload (N1 shakedown). */}
      {['brief_document_v2','brief_document_v3','brief_document_v4'].includes(brief.schema_version ?? '') && research?.brief_id===brief.brief_id && (research.status==='failed' || !!research.waiting_reason) &&
        <AngleResearchPanel data={research} error="" busy={busy} canRetry={brief.can_edit}
          onRetry={()=>void perform(`/angles/${brief.angle_id}/brief/retry`)} onRetryStage={jobId=>void perform(`/jobs/${jobId}/retry`)} />}
      {/* Keyed by brief and version: typed answers, a draft edit or a decision never carry over to another brief (E.F4). */}
      {brief.schema_version==='brief_document_v2'||brief.schema_version==='brief_document_v3'?<BriefReaderV2 brief={brief} busy={busy} perform={perform} versions={versions} onOpen={onOpen}
        refreshing={ACTIVE.includes(research?.status ?? '') && research?.brief_id===brief.brief_id}/>
      :brief.schema_version==='brief_document_v4'?<BriefGateV4 brief={brief} busy={busy} perform={perform} versions={versions} onOpen={onOpen} packsEnabled={packsEnabled}
        refreshing={ACTIVE.includes(research?.status ?? '') && research?.brief_id===brief.brief_id}/>:<>
      {!!brief.blockers.length && <section className="rounded-lg bg-amber-50 p-3 text-sm" aria-label="What stops approval"><h3 className="font-medium">What stops approval ({brief.blockers.length})</h3><ul className="mt-1 ml-5 list-disc space-y-1">{brief.blockers.map((b,i)=><li key={i}>{b}</li>)}</ul></section>}<BriefRead brief={brief}/>
      {research?.status==='failed'&&research.error_summary&&<p role="alert" className="bg-red-50 text-red-800 p-3 rounded">Brief generation failed: {research.error_summary}</p>}
      <details><summary>Research progress and inspected context</summary>{research?.jobs.map(j=><div key={j.job_id} className="mt-2"><StageProgress job={j}/>{['failed','waiting'].includes(j.status)&&brief.can_edit&&<button className={button} disabled={busy} onClick={()=>void perform(`/jobs/${j.job_id}/retry`)}>Retry stage from saved inputs</button>}</div>)}
        {research?.dossier?.evidence.map(e=><label key={e.evidence_id} className="flex gap-2 mt-2"><input type="checkbox" checked={selected.includes(e.evidence_id)} onChange={v=>setSelected(v.target.checked?[...selected,e.evidence_id]:selected.filter(i=>i!==e.evidence_id))}/><span>{e.title} · {e.excerpt}</span></label>)}</details>
      <div className="flex gap-4"><a className="underline" href={`/api/atelier/briefs/${brief.brief_id}/export.md`}>Export Markdown</a><a className="underline" href={`/api/atelier/briefs/${brief.brief_id}/export.json`} target="_blank" rel="noreferrer">Export JSON</a></div>
      <details><summary>Versions</summary>{versions.map(v=><button key={v.brief_id} className={`${button} m-1`} onClick={()=>onOpen(v.brief_id)}>{v.approval_status} · {new Date(v.created_at).toLocaleString()}</button>)}</details>
      <h3 className="font-medium">Editorial edits</h3><button className={button} disabled={!brief.can_edit||busy} onClick={()=>setEditor(structuredClone(brief.content_body.document))}>Edit brief</button>
      {editor&&<div className="space-y-3">{(['title','reader_promise','why_now','core_insight','audience_pain','differentiation','similarity_review','message_spine','narrative','evidence_boundaries','voice','creative_direction','accessibility','distribution','evaluation_signals','handoff_checklist'] as const).map(k=><label key={k} className="block capitalize">{label(k)}<textarea className="block border rounded p-2 w-full" value={Array.isArray(editor[k])?(editor[k] as string[]).join('\n'):editor[k] as string} onChange={e=>setEditor({...editor,[k]:Array.isArray(editor[k])?e.target.value.split('\n').filter(Boolean):e.target.value})}/></label>)}
        <label className="block">Positioning<textarea className="border rounded p-2 w-full" value={editor.positioning||''} onChange={e=>setEditor({...editor,positioning:e.target.value||null})}/></label>
        <label className="block">Unresolved consent requirements<textarea className="border rounded p-2 w-full" value={editor.claims_requiring_consent.join('\n')} onChange={e=>setEditor({...editor,claims_requiring_consent:e.target.value.split('\n').filter(Boolean)})}/></label>
        {editor.claims.map((c,i)=><ClaimEditor key={c.claim_id} value={c} evidence={brief.selected_evidence} onChange={v=>setEditor({...editor,claims:editor.claims.map((x,n)=>n===i?v:x)})}/>)}
        <FormatEditor name="Email" value={editor.email} onChange={v=>setEditor({...editor,email:v})}/>
        {editor.reels.map((r,i)=><FormatEditor key={i} name={`Reel ${i+1}`} value={r} onChange={v=>setEditor({...editor,reels:editor.reels.map((x,n)=>n===i?v:x)})}/>)}
        {editor.carousel.map((s,i)=><label key={s.number} className="block">Carousel slide {s.number}<textarea className="border rounded p-2 w-full" value={s.direction} onChange={e=>setEditor({...editor,carousel:editor.carousel.map((x,n)=>n===i?{...x,direction:e.target.value}:x)})}/></label>)}
        {Object.entries(editor.prior_differences).map(([id,text])=><label key={id} className="block">Difference from {id}<textarea className="border rounded p-2 w-full" value={text} onChange={e=>setEditor({...editor,prior_differences:{...editor.prior_differences,[id]:e.target.value}})}/></label>)}
        <button className={button} disabled={busy} onClick={()=>{const changes=Object.fromEntries(Object.entries(editor).filter(([k,v])=>JSON.stringify(v)!==JSON.stringify(brief.content_body.document[k as keyof BriefDocument])));void perform(`/briefs/${brief.brief_id}`,'PATCH',{...expected,changes});}}>Save a new brief version</button></div>}
      <h3 className="font-medium">Open questions</h3>{brief.content_body.document.open_questions.map(q=><label key={q.question_id} className="block">{q.text} {q.required?'(required)':'(optional)'}<textarea className="border rounded p-2 block w-full" disabled={!brief.can_review} value={answers[q.question_id]??q.answer??''} onChange={e=>setAnswers({...answers,[q.question_id]:e.target.value})}/></label>)}
      <button className={button} disabled={!brief.can_review||busy||!Object.keys(answers).length} onClick={()=>void perform(`/briefs/${brief.brief_id}/answers`,'POST',{...expected,answers})}>Save answers as editorial context</button>
      <details><summary>Source permission and attribution</summary><label>Evidence <Select className="border p-2" value={clearance.evidence_id} onChange={e=>setClearance({...clearance,evidence_id:e.target.value})}><option value="">Select passage</option>{brief.selected_evidence.filter(e=>e.transcript_id).map(e=><option key={e.evidence_id} value={e.evidence_id}>{e.title} · {e.passage_id}</option>)}</Select></label>{(['permission_reference','attribution_reference'] as const).map(k=><label key={k} className="block">{label(k)}<input className="border rounded p-2 w-full" value={clearance[k]} onChange={e=>setClearance({...clearance,[k]:e.target.value})}/></label>)}<button className={button} disabled={!brief.can_review||busy||!clearance.evidence_id||!clearance.permission_reference||!clearance.attribution_reference} onClick={()=>void perform(`/briefs/${brief.brief_id}/clearance`,'POST',{...expected,...clearance})}>Record actual clearance</button></details>
      <label className="block">Review or rejection reason<textarea className="border rounded p-2 w-full" value={reason} onChange={e=>setReason(e.target.value)}/></label>
      <label className="flex gap-2"><input type="checkbox" checked={ack} onChange={e=>setAck(e.target.checked)}/>I reviewed all current claims and their sources, the distinct treatment and the incomplete legacy publication coverage.</label>
      <button className={button} disabled={!brief.can_review||busy||!reason.trim()||!ack} onClick={()=>void perform(`/briefs/${brief.brief_id}/review`,'POST',{...expected,claim_ids:brief.content_body.document.claims.map(c=>c.claim_id),reason,history_acknowledged:ack})}>Record scoped review</button>
      <div className="flex gap-3"><button className={button} disabled={!brief.can_approve||busy} onClick={()=>void perform(`/briefs/${brief.brief_id}/decision`,'POST',{...expected,decision:'approved',note:reason||null})}>Approve brief</button><button className={button} disabled={!brief.can_review||brief.approval_status!=='pending'||busy||!reason.trim()} onClick={()=>void perform(`/briefs/${brief.brief_id}/decision`,'POST',{...expected,decision:'rejected',note:reason})}>Reject brief</button></div>
      <label className="block">Refinement instructions<textarea className="border rounded p-2 w-full" value={instructions} onChange={e=>setInstructions(e.target.value)}/></label><p className="text-sm">Edits remain locked unless these instructions name a field to change. Selected context supplies original evidence; answers alone cannot establish facts.</p>
      {/* The screen refreshes live (5.B6); replay stays a test mode. */}
      <button className={button} disabled={!brief.can_edit||busy||!instructions.trim()} onClick={()=>void perform(`/briefs/${brief.brief_id}/revise`,'POST',{...expected,instructions,mode:'live',evidence_ids:selected})}>Refresh with feedback</button>
      </>}
      {/* After Gate 2: what WIA published from this approved brief (L.B9). Once the brief has a content pack, each piece is
          marked published on the pack instead (NP.F3). */}
      {brief.can_record_published && !hasPack && <PublishedCapture brief={brief}/>}
    </article>
  </>;
}
