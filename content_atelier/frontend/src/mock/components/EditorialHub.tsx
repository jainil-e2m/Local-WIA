import React, { useEffect, useRef, useState } from 'react';
import { ThemedSelect } from '../../components/ThemedSelect';
import { Check, FileText, Lightbulb, Search, Sparkles, Layers, Plus, ChevronDown, CalendarClock } from 'lucide-react';
import { ScheduledContent } from './ScheduledContent';
import { PageHeading } from '../../components/PageHeading';
import { RevivalApproval } from '../../components/RevivalApproval';
import { AngleRationale } from '../../components/AngleRationale';
import { AngleEvidence } from '../../components/AngleEvidence';
import { BriefingOverview } from '../../components/BriefingOverview';
import { octoberDemoPosts } from './ContentCalendar';
import { ContentIdea, GateStatus } from '../../types/atelier';
import { editorialWeeks, weekLabel, archiveWeekHeading, archiveStageItems, editorialStageCounts, hasWeeklyCapacity } from '../../utils/editorialWeeks';

export type EditorialTab = 'angles' | 'briefs' | 'packs' | 'scheduled';
export type InspectorTab = 'gates' | 'brief' | 'pack' | 'schedule' | 'research';

export function WeekStagePills({ stage, counts }: { stage: 'angles' | 'briefs' | 'packs'; counts: ReturnType<typeof editorialStageCounts> }) {
  const description = stage === 'angles'
    ? 'Waiting angles · Approved angles now in Briefs · Generated content packs. Totals are for this week.'
    : stage === 'briefs'
      ? 'Briefs awaiting approval · Content packs generated from approved briefs. Totals are for this week.'
      : 'Generated content packs for this week.';
  return <span title={description} className="flex flex-wrap gap-2 text-[11px]">
    {stage !== 'packs' && <span className="rounded-full bg-[#FFF8E9] px-3 py-1 text-[#947021]">{stage === 'briefs' ? counts.approved : counts.waiting} {stage === 'briefs' ? 'awaiting approval' : 'waiting'}</span>}
    {stage === 'angles' && <span className="rounded-full bg-[#EFF3FF] px-3 py-1 text-[#5070FF]">{counts.approved} approved</span>}
    <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">{counts.generated} generated</span>
  </span>;
}

interface Props {
  initialTab?: EditorialTab;
  ideas: ContentIdea[];
  mode: 'weekly' | 'previous';
  onReview: (idea: ContentIdea, tab: InspectorTab, contentOrder?: number) => void;
  onUpdateGate: (id: string, gate: GateStatus) => void;
  onSwitchSection: () => void;
  onAddAngle: () => void;
  onApprovePack: (id: string) => void;
  onSchedule: (id: string, scheduledAt: string) => void;
}

export function EditorialHub({ ideas: library, mode, initialTab = 'angles', onReview, onUpdateGate, onSwitchSection, onAddAngle, onApprovePack, onSchedule }: Props) {
  const weeks = editorialWeeks(library);
  const previousWeeks = weeks.slice(1);
  const week = weeks[0];
  const ideas = library.filter(idea => mode === 'weekly' ? idea.editorialWeek === week : previousWeeks.includes(idea.editorialWeek!));
  const title = mode === 'weekly' ? 'Weekly Studio' : 'Previous Concepts';
  const [tab, setTab] = useState<EditorialTab>(mode === 'previous' && (initialTab === 'packs' || initialTab === 'scheduled') ? 'angles' : initialTab);
  const [query, setQuery] = useState('');
  const [offer, setOffer] = useState('all');
  const [linkedId, setLinkedId] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const panelRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!linkedId) return;
    const card = Array.from(panelRef.current?.querySelectorAll<HTMLElement>('[data-editorial-idea-id]') ?? []).find(element => element.dataset.editorialIdeaId === linkedId);
    card?.scrollIntoView?.({ block: 'start', behavior: 'smooth' });
    card?.focus({ preventScroll: true });
  }, [tab, linkedId]);
  const stageCounts = editorialStageCounts(ideas);
  const schedulingIdeas = library.filter(idea => idea.editorialWeek === week && (!linkedId || idea.id === linkedId) && (offer === 'all' || idea.suggestedCta === offer) && `${idea.title} ${idea.client}`.toLowerCase().includes(query.trim().toLowerCase()));
  const demoSchedule = octoberDemoPosts(library).filter(post => (offer === 'all' || library.find(idea => idea.id === post.ideaId)?.suggestedCta === offer) && `${post.title} ${post.channel}`.toLowerCase().includes(query.trim().toLowerCase()));
  const isAngleApproved = (idea: ContentIdea) => idea.gate !== 'gate1_angle';
  const isBriefApproved = (idea: ContentIdea) => ['gate3_pack', 'approved_for_giselle'].includes(idea.gate);
  const matching = ideas.filter(idea =>
    (tab === 'angles' || (tab === 'packs' || tab === 'scheduled' ? !!idea.pack : isAngleApproved(idea))) &&
    (!linkedId || idea.id === linkedId) &&
    (offer === 'all' || idea.suggestedCta === offer) &&
    `${idea.title} ${idea.client} ${idea.primaryQuote} ${idea.brief.coreInsight}`.toLowerCase().includes(query.trim().toLowerCase())
  );
  const archiveMatching = archiveStageItems(matching, tab === 'scheduled' ? 'packs' : tab);
  const pending = matching.filter(idea => tab === 'angles' ? !isAngleApproved(idea) : !isBriefApproved(idea));
  const approved = matching.filter(idea => tab === 'angles' ? isAngleApproved(idea) : isBriefApproved(idea));

  const followLink = (id: string, nextTab: EditorialTab) => {
    // Completed stages are not in archive queues; inspect their retained source directly.
    if (mode === 'previous') {
      const idea = library.find(item => item.id === id);
      if (idea) onReview(idea, nextTab === 'angles' ? 'gates' : nextTab === 'briefs' ? 'brief' : 'pack');
      return;
    }
    setTab(nextTab);
    setLinkedId(id);
    setQuery('');
    setOffer('all');
    setNotice('');
  };
  const approve = (idea: ContentIdea) => {
    if (mode === 'previous') {
      onUpdateGate(idea.id, tab === 'angles' ? 'gate2_brief' : 'gate3_pack');
      return;
    }
    if (tab === 'angles' && idea.gate === 'gate1_angle') {
      onUpdateGate(idea.id, 'gate2_brief');
      followLink(idea.id, 'briefs');
    } else if (tab === 'briefs' && idea.gate === 'gate2_brief') {
      onUpdateGate(idea.id, 'gate3_pack');
      followLink(idea.id, 'packs');
    }
  };

  const renderCard = (idea: ContentIdea, isApproved: boolean) => (
    <article key={idea.id} data-editorial-idea-id={idea.id} tabIndex={-1} className={`rounded-2xl border p-5 flex flex-col gap-4 shadow-[0_3px_18px_rgba(28,36,52,0.035)] ${idea.revivedAt ? 'border-[#D9CCED] bg-[#F8F3FC]' : 'border-[#E6E9F0] bg-white'}`}>
      {idea.revivedAt && <p className="text-[11px] font-medium text-[#8260A1]">Revived from {weekLabel(idea.originalEditorialWeek!)} · {isApproved ? 'Source retained' : 'Awaiting approval in Weekly Studio'}</p>}
      <div className="flex items-start justify-between gap-3">
        <h3 className="min-w-0 font-editorial text-[23px] leading-tight text-[#1B2433]">{idea.title}</h3>
        <span className={`shrink-0 text-[10px] rounded-full px-2.5 py-1 font-medium ${isApproved ? 'bg-emerald-50 text-emerald-700' : 'bg-[#FFF8E9] text-[#947021]'}`}>
          {isApproved ? 'Approved' : 'Awaiting approval'}
        </span>
      </div>
      <p className="-mt-2 text-[11px] text-[#9199A7]">{idea.client && idea.client !== 'Anonymised wedding professional' ? `${idea.client} · ` : ''}{idea.createdAt ? new Date(idea.createdAt).toLocaleDateString('en-IN', { timeZone: 'Asia/Calcutta', day: 'numeric', month: 'short', year: 'numeric' }) : idea.daysAgo} · {idea.suggestedCta}</p>
      {tab === 'angles' ? <AngleRationale idea={idea} /> : <BriefingOverview idea={idea} />}

      {tab === 'angles' ? (
        <details className="rounded-xl bg-[#F7F8FB] p-3 text-[11px] text-[#667184]">
          <summary className="cursor-pointer font-medium text-[#34445F]">Source moment & research <span className="float-right text-[#5070FF]">{idea.scoreBasis === 'editorial' ? 'Editorial ' : 'Score '}{idea.score}/100</span></summary>
          {idea.editorialContext ? <div className="mt-3"><AngleEvidence idea={idea} /></div> : <>
          <blockquote className="mt-3 border-l-2 border-[#D9BE87] pl-3 italic leading-relaxed">“{idea.primaryQuote}”</blockquote>
          <p className="mt-2">{idea.sourceDetails} · {idea.timestamp}</p>
          <p className="mt-3 font-medium text-[#34445F]">Research: {idea.research.searchQuery}</p>
          <p className="mt-1">Demand score {idea.research.googleTrendsScore}/100 · {idea.research.trendDirection}</p>
          <ul className="list-disc pl-4 mt-2 space-y-1">{idea.research.peopleAlsoAsk.slice(0, 3).map(question => <li key={question}>{question}</li>)}</ul>
          <button onClick={() => onReview(idea, 'research')} className="mt-3 text-[#5070FF] font-medium">Read full research →</button>
          </>}
        </details>
      ) : idea.suppliedCopy?.brief ? (
        <button onClick={() => followLink(idea.id, 'angles')} className="self-start text-[12px] font-medium text-[#5070FF]">← View source angle</button>
      ) : (
        <div className="rounded-xl bg-[#F7F8FB] p-3 text-[11px] text-[#667184]">
          <span className="uppercase text-[9px] tracking-wider font-semibold text-[#9199A7]">Message spine</span>
          <ol className="mt-2 list-decimal pl-4 space-y-1.5">{idea.brief.messageSpine.slice(0, 3).map((line, index) => <li key={index}>{line}</li>)}</ol>
          <button onClick={() => followLink(idea.id, 'angles')} className="mt-3 text-[#5070FF] font-medium">← View source angle</button>
        </div>
      )}

      {isApproved && (
        <div className="text-[11px] rounded-xl border border-[#E6EAF2] p-3 flex items-center justify-between gap-2">
          <span className="flex items-center gap-2 text-[#667184]">{idea.pack ? <Layers className="w-3.5 h-3.5 text-[#5070FF]" /> : <FileText className="w-3.5 h-3.5 text-[#5070FF]" />}
            {tab === 'angles' ? isBriefApproved(idea) ? 'Brief approved · pack generated' : 'Brief awaiting approval' : idea.pack ? 'Pack generated · retained source brief' : 'Approved · pack unavailable'}
          </span>
          {tab === 'angles' ? <button onClick={() => followLink(idea.id, 'briefs')} className="text-[#5070FF] font-semibold shrink-0">View brief →</button> : idea.pack ? <button onClick={() => onReview(idea, 'pack')} className="text-[#5070FF] font-semibold shrink-0">Open pack →</button> : null}
        </div>
      )}
      {isApproved && (tab === 'angles' ? idea.angleApprovedAt : idea.briefApprovedAt) && <p className="text-[10px] text-[#9199A7]">Approved {new Date((tab === 'angles' ? idea.angleApprovedAt : idea.briefApprovedAt)!).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Calcutta' })} IST</p>}
      <div className="mt-auto pt-3 border-t border-[#EEF0F4] flex flex-wrap items-center gap-2">
        <button onClick={() => onReview(idea, tab === 'angles' ? 'gates' : 'brief')} className="text-[11px] font-medium text-[#34445F] rounded-full border border-[#E6E9F0] px-3 py-2 hover:bg-[#F7F8FB]">{tab === 'angles' ? 'Review angle' : 'Read full brief'}</button>
        {!isApproved && (mode === 'previous' ? <RevivalApproval onApprove={() => approve(idea)} atCapacity={!hasWeeklyCapacity(library, week)} /> : <button onClick={() => approve(idea)} className="ml-auto flex items-center gap-1.5 text-[11px] font-medium bg-[#1B2838] text-white rounded-full px-3 py-2 hover:bg-[#34445F]"><Check className="w-3 h-3" />{tab === 'angles' ? 'Approve & create brief' : 'Approve & generate pack'}</button>)}
      </div>
    </article>
  );

  const renderPackCard = (idea: ContentIdea) => (
    <article key={idea.id} data-editorial-idea-id={idea.id} tabIndex={-1} className={`rounded-2xl border p-5 space-y-4 ${idea.revivedAt ? 'border-[#D9CCED] bg-[#F8F3FC]' : 'border-[#E6E9F0] bg-white'}`}>
      {idea.revivedAt && <p className="text-[11px] font-medium text-[#8260A1]">Revived from {weekLabel(idea.originalEditorialWeek!)}</p>}
      <div className="flex justify-between items-center gap-3 text-[11px]"><span className="text-[#8B93A3]">{idea.isMock ? 'Mock · ' : ''}{idea.suggestedCta} · {idea.id}</span><span className="bg-emerald-50 text-emerald-700 rounded-full px-3 py-1">{idea.scheduledAt ? 'Scheduled' : idea.publishingApprovedAt ? 'Awaiting scheduling' : 'Ready for publishing review'}</span></div>
      <h3 className="font-editorial text-[23px] text-[#1B2433]">{idea.title}</h3>
      <p className="text-[12px] text-[#667184] leading-relaxed">{idea.brief.coreInsight}</p>
      <p className="rounded-xl bg-[#F7F8FB] p-3 text-[12px] text-[#667184]">1 email · {idea.pack!.carousel.slides.length} carousel slides · {idea.pack!.reels.length} reels · captions</p>
      <button onClick={() => onReview(idea, 'pack')} className="rounded-full bg-[#1B2838] text-white text-[12px] px-4 py-2.5">Open content pack →</button>
      <button onClick={() => { if (!idea.publishingApprovedAt) onApprovePack(idea.id); followLink(idea.id, 'scheduled'); }} className="ml-2 rounded-full bg-[#5D64FF] text-white text-[12px] px-4 py-2.5">{idea.scheduledAt ? 'View schedule →' : idea.publishingApprovedAt ? 'Schedule content →' : 'Approve for publishing →'}</button>
    </article>
  );

  return (
    <div className="space-y-6">
      <div className="atelier-page-hero flex flex-wrap items-start justify-between gap-5">
        <div>
          <PageHeading title={title} description={mode === 'weekly' ? 'The latest available week, from content angles to approved briefs and generated packs.' : 'Earlier weeks, kept intact. Revisit unused angles and progress their briefs whenever you are ready.'} />
          {mode === 'weekly' && week && <p className="mt-3 text-[12px] font-medium text-[#A38B61]">{weekLabel(week)} · Latest week · {ideas.length}/4 concepts across all stages</p>}
          {mode === 'previous' && <p className="mt-3 text-[12px] font-medium text-[#A38B61]">{previousWeeks.length} previous weeks · {ideas.length} concepts · Revive into Weekly Studio for approval</p>}
        </div>
        <div className="atelier-page-actions flex flex-wrap items-center gap-3 pt-2">
          <button onClick={onSwitchSection} className="rounded-full border border-[#E6E9F0] bg-white px-4 py-2.5 text-[12px] text-[#34445F]">{mode === 'weekly' ? 'Previous Concepts →' : '← Weekly Studio'}</button>
          {mode === 'weekly' && <button onClick={onAddAngle} className="atelier-page-primary flex items-center gap-2 rounded-full px-5 text-[12px]"><Plus className="w-3.5 h-3.5" /> Add angle</button>}
        </div>
      </div>
      <nav aria-label="Editorial pipeline" className="editorial-pipeline">
        {[
          { id: 'angles', label: 'Content Angle', count: `${stageCounts.waiting} waiting · ${stageCounts.approved} approved · ${stageCounts.generated} generated`, icon: Lightbulb },
          { id: 'briefs', label: 'Content Briefing', count: `${stageCounts.approved} waiting · ${stageCounts.generated} generated`, icon: FileText },
          { id: 'packs', label: 'Content Packs', count: `${stageCounts.generated} generated`, icon: Layers },
          { id: 'scheduled', label: 'Scheduled Content', count: `${library.filter(idea => idea.pack && idea.publishingApprovedAt && !idea.scheduledAt).length} waiting · ${demoSchedule.length + library.filter(idea => idea.pack && idea.publishingApprovedAt && idea.scheduledAt).length} scheduled`, icon: CalendarClock },
        ].filter(stage => mode === 'weekly' || stage.id === 'angles' || stage.id === 'briefs').map(stage => {
          const Icon = stage.icon;
          const selected = stage.id === tab;
          return (
            <button
              key={stage.id}
              id={`editorial-${stage.id}-tab`}
              type="button"
              aria-pressed={selected}
              aria-controls="editorial-panel"
              onClick={() => {
                setTab(stage.id as EditorialTab);
                setLinkedId(null);
                setNotice('');
              }}
              className={`editorial-pipeline-step ${selected ? 'is-selected' : ''}`}
            >
              <svg aria-hidden="true" className="editorial-pipeline-shape" viewBox="0 0 320 56" preserveAspectRatio="none">
                <path d="M28 1 H293 L318 28 L293 55 H28 A27 27 0 0 1 28 1 Z" vectorEffect="non-scaling-stroke" />
              </svg>
              <span className="editorial-pipeline-content"><Icon className="w-4 h-4 shrink-0" /><span className="flex flex-col items-start gap-0.5"><span className="font-semibold">{stage.label}</span><span className="editorial-pipeline-count">{stage.count}</span></span></span>
            </button>
          );
        })}
      </nav>
      <div className="flex flex-wrap justify-between items-center gap-4 border-b border-[#E3E7EF] pb-4">
        <p className="text-[12px] text-[#8B93A3]">{tab === 'scheduled' ? 'Publishing plan across weeks · Synced with the Home calendar.' : mode === 'previous' ? 'Expand a week below to review its waiting concepts.' : week ? `Showing only ${weekLabel(week)}` : 'No concepts yet.'}</p>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative"><Search className="absolute top-3 left-3 w-3.5 h-3.5 text-[#9AA3B2]" /><input aria-label={`Search ${title}`} value={query} onChange={event => setQuery(event.target.value)} placeholder={tab === 'scheduled' ? 'Search scheduled content…' : mode === 'previous' ? 'Search all previous weeks…' : 'Search this week…'} className="h-9 w-60 rounded-full border border-[#E6E9F0] bg-white pl-9 pr-3 text-[11px]" /></div>
          <ThemedSelect aria-label="Filter by offer" value={offer} onChange={setOffer} className="h-9 px-3 text-[11px]"><option value="all">All offers</option>{['Elevate', 'Accelerators', 'LeadLock'].map(track => <option key={track}>{track}</option>)}</ThemedSelect>
        </div>
      </div>
      {notice && <div role="status" className="flex flex-wrap justify-between gap-3 rounded-xl bg-emerald-50 border border-emerald-100 px-4 py-3 text-[12px] text-emerald-800"><span>{notice}</span><button onClick={() => { setTab(tab === 'angles' ? 'briefs' : 'packs'); setLinkedId(null); setNotice(''); }} className="font-semibold">{tab === 'angles' ? 'Go to Briefs →' : 'Go to Content Packs →'}</button></div>}
      {linkedId && <div className="flex justify-between rounded-xl bg-[#EFF3FF] p-3 text-[12px] text-[#5070FF]"><span>{tab === 'angles' ? 'Angle' : tab === 'briefs' ? 'Brief' : 'Content pack'} · {library.find(idea => idea.id === linkedId)?.title}</span><button onClick={() => setLinkedId(null)} className="font-semibold">Show all {tab}</button></div>}
      <div ref={panelRef} id="editorial-panel" role="region" aria-labelledby={`editorial-${tab}-tab`} className="space-y-8">
        {tab === 'scheduled' ? <ScheduledContent ideas={schedulingIdeas} demoPosts={demoSchedule} onSchedule={onSchedule} onReview={(idea, order) => onReview(idea, idea.pack ? 'pack' : 'brief', order)} /> : mode === 'previous' ? <section aria-label={tab === 'packs' ? 'Previous content packs' : `${tab} Awaiting approval`}>
          <div className="mb-3 flex items-center gap-3"><h2 className="font-editorial text-2xl text-[#1B2433]">{tab === 'packs' ? 'Generated content packs' : 'Awaiting approval'}</h2><span className="rounded-full border border-[#E6E9F0] bg-white px-3 py-1 text-[11px] text-[#8B93A3]">{archiveMatching.length}</span></div>
          <p className="mb-5 text-[12px] text-[#8B93A3]">{tab === 'packs' ? 'Generated packs retain their source links.' : `Approve revival to move this ${tab === 'angles' ? 'angle' : 'brief'} into the same awaiting-approval section in Weekly Studio. It will not advance stages until approved there.`}</p>
          <div className="space-y-3">
            {previousWeeks.map(value => {
              const items = archiveMatching.filter(idea => idea.editorialWeek === value);
              const counts = editorialStageCounts(ideas.filter(idea => idea.editorialWeek === value));
              if (!items.length && (query || offer !== 'all')) return null;
              return <details key={`${tab}-${value}`} className="group/editorial-week rounded-2xl border border-[#E6E9F0] bg-white overflow-hidden">
                <summary className="list-none cursor-pointer flex flex-wrap items-center justify-between gap-3 px-5 py-4 [&::-webkit-details-marker]:hidden">
                  <span className="flex flex-wrap items-center gap-x-4 gap-y-1"><span className="text-[14px] font-semibold text-[#34445F]">{archiveWeekHeading(value)}</span><span className="text-[12px] text-[#8B93A3]">{weekLabel(value)}</span></span>
                  <span className="flex items-center gap-3"><WeekStagePills stage={tab} counts={counts} /><ChevronDown aria-hidden="true" className="w-4 h-4 text-[#667184] transition-transform group-open/editorial-week:rotate-180" /></span>
                </summary>
                <div className="border-t border-[#EEF0F4] bg-[#F7F8FB] p-4 grid grid-cols-1 xl:grid-cols-2 gap-4">{items.length ? items.map(idea => tab === 'packs' ? renderPackCard(idea) : renderCard(idea, false)) : <p className="col-span-full py-4 text-center text-[12px] text-[#8B93A3]">{tab === 'packs' ? 'No generated packs for this week yet.' : `No ${tab} awaiting approval for this week. View the next stage to see progressed concepts.`}</p>}</div>
              </details>;
            })}
            {(!previousWeeks.length || (!archiveMatching.length && (query || offer !== 'all'))) && <div className="rounded-2xl border border-dashed border-[#DCE1EA] py-8 text-center text-[12px] text-[#8B93A3]">{!previousWeeks.length ? 'No previous weeks yet.' : 'No items match these filters.'}</div>}
          </div>
        </section> : tab === 'packs' ? <section aria-label="Weekly content packs">
          <h2 className="font-editorial text-2xl text-[#1B2433]">Generated content packs <span className="text-sm text-[#8B93A3]">({matching.length})</span></h2>
          <p className="mt-2 mb-4 text-[12px] text-[#8B93A3]">Linked to this week's approved briefs. Publishing and scheduling are not a third approval gate.</p>
          {matching.length ? <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">{matching.map(renderPackCard)}</div> : <div className="rounded-2xl border border-dashed border-[#DCE1EA] py-8 text-center text-[12px] text-[#8B93A3]">{query || offer !== 'all' ? 'No packs match these filters.' : 'No packs for this week yet. Approve a brief to generate its content pack.'}</div>}
        </section> : [{ name: 'Awaiting approval', list: pending, approved: false, description: tab === 'angles' ? 'Review at your pace. Unused angles stay available in their original week.' : 'Generated from approved angles. Review the brief before creating its pack.' }, { name: 'Approved', list: approved, approved: true, description: tab === 'angles' ? 'Your approved angles remain here, linked to their briefs.' : 'The source briefs behind your generated content packs. Approval history stays visible.' }].map(section => (
          <section key={section.name} aria-label={`${tab} ${section.name}`}>
            <div className="mb-4 flex items-center gap-3"><h2 className="font-editorial text-2xl text-[#1B2433]">{section.name}</h2><span className="bg-white rounded-full border border-[#E6E9F0] px-2.5 py-1 text-[10px] text-[#8B93A3]">{section.list.length}</span></div>
            <p className="text-[12px] text-[#8B93A3] mb-4">{section.description}</p>
            {section.list.length ? <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">{section.list.map(idea => renderCard(idea, section.approved))}</div> : <div className="rounded-2xl border border-dashed border-[#DCE1EA] py-8 text-center text-[12px] text-[#8B93A3]">{query || offer !== 'all' || linkedId ? 'No items match this view.' : section.approved ? `Approved ${tab} will be retained here.` : tab === 'briefs' ? 'Approve an angle to bring its brief here.' : 'No angles awaiting approval.'}</div>}
          </section>
        ))}
      </div>
      <p className="text-[10px] text-[#9AA3B2] flex items-center gap-2"><Sparkles className="w-3 h-3" /> Monday–Sunday weeks · Latest available week in Weekly Studio · Older weeks in Previous Concepts · Saved in this browser.</p>
    </div>
  );
}
