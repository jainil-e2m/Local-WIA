import React, { useEffect, useRef, useState } from 'react';
import { ThemedSelect } from './ThemedSelect';
import { RevivalApproval } from './RevivalApproval';
import { AngleRationale } from './AngleRationale';
import { AngleResearch } from './AngleEvidence';
import { PackSchedulePopover } from './PackSchedulePopover';
import { contentScheduleFor, contentScheduleProgress, scheduleLabel } from '../utils/publishingSchedule';
import {
  X,
  CheckCircle2,
  Check,
  ShieldAlert,
  Search,
  Sparkles,
  HelpCircle,
  Copy,
  Mail,
  Layers,
  Video,
  CalendarClock,
} from 'lucide-react';
import { ContentIdea, GateStatus } from '../types/atelier';
import { MarkdownDocument } from './MarkdownDocument';
import { BriefingOverview } from './BriefingOverview';
import { useModalBehavior } from './useModalBehavior';
import {
  composeContentBriefMarkdown,
  draftPackToText,
  draftPieceToText,
  selectContentAngle,
  selectDraftContents,
} from '../stages/ideaStages';

interface IdeaDetailModalProps {
  idea: ContentIdea;
  initialTab?: 'gates' | 'brief' | 'pack' | 'schedule' | 'research';
  initialContentOrder?: number;
  revivalApproval?: boolean;
  revivalAtCapacity?: boolean;
  onClose: () => void;
  onUpdateGate: (ideaId: string, newGate: GateStatus, note?: string) => void;
  onUpdateCta: (ideaId: string, newCta: 'Elevate' | 'Accelerators' | 'LeadLock') => void;
  onApprovePack?: (ideaId: string) => void;
  onSchedule?: (ideaId: string, date: string, time: string, contentOrder?: number) => void;
}

export const IdeaDetailModal: React.FC<IdeaDetailModalProps> = ({
  idea,
  onClose,
  onUpdateGate,
  onApprovePack,
  onSchedule,
  initialTab = 'gates',
  initialContentOrder = 1,
  revivalApproval = false,
  revivalAtCapacity = false,
}) => {
  const modalRef = useModalBehavior(onClose);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<'gates' | 'brief' | 'pack' | 'schedule' | 'research'>(initialTab);
  const [copiedSection, setCopiedSection] = useState<string | null>(null);
  const [isGeneratingBrief, setIsGeneratingBrief] = useState(false);
  const [isGeneratingPack, setIsGeneratingPack] = useState(false);

  const angle = selectContentAngle(idea);
  const briefMarkdown = composeContentBriefMarkdown(idea);
  const draftContents = selectDraftContents(idea.pack);
  const [activeContentOrder, setActiveContentOrder] = useState(initialContentOrder);
  const [copyError, setCopyError] = useState('');
  const packReady = !!idea.pack && ['gate3_pack', 'approved_for_giselle'].includes(idea.gate);
  const publishingApproved = packReady && !!idea.publishingApprovedAt;
  const scheduleProgress = contentScheduleProgress(idea);

  useEffect(() => {
    setActiveTab(initialTab);
    setCopiedSection(null);
    setActiveContentOrder(initialContentOrder);
    setCopyError('');
  }, [idea.id, initialTab, initialContentOrder]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [idea.id, activeTab, activeContentOrder]);

  const handleCopy = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyError('');
      setCopiedSection(label);
      setTimeout(() => setCopiedSection(null), 2000);
    } catch {
      setCopyError('Could not copy. Please allow clipboard access and try again.');
    }
  };

  // Immediate AI Brief generation upon angle approval (Question 1 answer)
  const handleApproveAngleWithAiBrief = () => {
    if (isGeneratingBrief || idea.gate !== 'gate1_angle') return;
    if (revivalApproval) { onUpdateGate(idea.id, 'gate2_brief'); return; }
    setIsGeneratingBrief(true);
    setTimeout(() => {
      onUpdateGate(idea.id, 'gate2_brief');
      setIsGeneratingBrief(false);
      setActiveTab('brief');
    }, 1300);
  };

  // Immediate Content Pack scripts generation upon brief approval
  const handleApproveBriefWithPackGeneration = () => {
    if (isGeneratingPack || idea.gate !== 'gate2_brief') return;
    if (revivalApproval) { onUpdateGate(idea.id, 'gate3_pack'); return; }
    setIsGeneratingPack(true);
    setTimeout(() => {
      onUpdateGate(idea.id, 'gate3_pack');
      setIsGeneratingPack(false);
      setActiveTab('pack');
    }, 1500);
  };

  const getGateProgressIndex = (gate: GateStatus) => {
    switch (gate) {
      case 'gate1_angle':
        return 1;
      case 'gate2_brief':
        return 2;
      case 'gate3_pack':
        return 3;
      case 'approved_for_giselle':
        return 4;
      default:
        return 1;
    }
  };

  const currentGateIndex = getGateProgressIndex(idea.gate);

  return (
    <div data-lenis-prevent className="atelier-modal-overlay fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6">
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-label={idea.title}
        tabIndex={-1}
        className="atelier-modal bg-[#FAF9F7] w-full max-w-5xl h-[92dvh] max-h-[92dvh] rounded-2xl border border-[#E0DFE2] shadow-saas-dropdown flex flex-col overflow-hidden text-[#221E17]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Hero Title & Spine Banner */}
        <div className="px-6 pt-5 pb-4 bg-white border-b border-[#E0DFE2] space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
            <h2 className="font-editorial text-2xl sm:text-3xl font-bold tracking-tight text-[#221E17]">
              {idea.title}
            </h2>
            <button type="button" onClick={onClose} aria-label="Close modal" className="w-8 h-8 shrink-0 flex items-center justify-center text-[#667184] hover:bg-[#F7F8FB] rounded-full"><X className="w-4 h-4" /></button>
          </div>

          <nav aria-label="Content stages" className="atelier-modal-tabs flex items-center gap-1 p-1 rounded-full border border-[#E6E9F0] bg-[#F7F8FB] text-xs">
            {([{ id: 'gates', label: 'Content Angle' }, { id: 'brief', label: 'Content Brief' }, { id: 'pack', label: 'Content Pack' }, { id: 'schedule', label: 'Schedule' }] as const).map(stage => <button
              key={stage.id} type="button" aria-pressed={activeTab === stage.id}
              disabled={stage.id === 'schedule' && !publishingApproved}
              title={stage.id === 'schedule' && !publishingApproved ? 'Approve the content pack for publishing to schedule it.' : undefined}
              onClick={() => setActiveTab(stage.id)}
              className={`px-4 py-2 rounded-full font-medium disabled:opacity-40 disabled:cursor-not-allowed ${activeTab === stage.id ? 'bg-white text-[#5070FF] font-semibold' : 'text-[#667184]'}`}
            >{stage.label}</button>)}
          </nav>
        </div>

        {/* Modal Scrollable Body */}
        <div ref={scrollRef} data-lenis-prevent className="atelier-modal-scroll min-h-0 flex-1 overflow-y-scroll [scrollbar-gutter:stable] p-6 space-y-6">
          {/* STAGE: Approvals & Gates — content angle beside the brief that arrived */}
          {activeTab === 'gates' && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 gap-4 items-start">
                <section className="bg-white p-5 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <span className="w-6 h-6 rounded-md bg-[#EFF3FF] text-[#5070FF] font-mono text-xs font-bold flex items-center justify-center border border-[#D1DBFF]">
                        1
                      </span>
                      <h3 className="font-editorial text-lg font-bold text-[#221E17]">Content Angle</h3>
                    </div>
                    <span className="text-xs font-mono text-[#87725F] tabular-nums">
                      {currentGateIndex >= 2 ? (
                        <span className="text-emerald-700 font-bold">Approved</span>
                      ) : (
                        <span className="text-amber-700 font-bold">Awaiting Whitney</span>
                      )}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <h4 className="font-editorial text-xl font-bold leading-snug text-[#221E17]">{angle.title}</h4>
                  </div>
                  <AngleRationale idea={idea} />

                  <div className="bg-[#FAF9F7] p-3.5 rounded-xl border border-[#E0DFE2] space-y-2">
                    <p className="text-xs italic text-[#4B4137] leading-relaxed">“{angle.quote}”</p>
                    <div className="flex items-center justify-between gap-2 text-[11px] font-mono text-[#87725F]">
                    <span>{angle.client}</span>
                      <span className="text-[#5070FF] font-semibold tabular-nums">{idea.scoreBasis === 'editorial' ? 'Editorial ' : ''}{angle.score}/100</span>
                    </div>
                  </div>

                  <p className="text-[11px] text-[#87725F] leading-relaxed">{angle.sourceDetails}</p>

                  <div className="grid grid-cols-2 gap-2">
                    {angle.scores.map((score) => (
                      <div
                        key={score.label}
                        className="flex items-center justify-between rounded-lg border border-[#E0DFE2] bg-[#FAF9F7] px-2.5 py-1.5 text-[11px]"
                      >
                        <span className="text-[#4B4137]">{score.label}</span>
                        <span className="font-mono font-semibold text-[#221E17] tabular-nums">{score.value}</span>
                      </div>
                    ))}
                  </div>

                  <button type="button" onClick={() => setActiveTab('research')} className="text-xs font-medium text-[#5070FF]">View source research →</button>
                  {currentGateIndex === 1 && (
                    <div className="pt-3 border-t border-[#E0DFE2] space-y-3">
                      {isGeneratingBrief ? (
                        <div className="p-4 bg-[#EFF3FF] border border-[#D1DBFF] rounded-xl flex items-center gap-3 text-xs text-[#5070FF]">
                          <Sparkles className="w-4 h-4 animate-spin shrink-0" />
                          <div>
                            <div className="font-semibold">{idea.isMock && idea.brief.productionBrief ? 'Opening the saved content brief...' : 'Writing the content brief...'}</div>
                            <div className="text-[11px] text-[#5070FF]/80">
                              {idea.isMock && idea.brief.productionBrief ? 'The saved analysis and production direction stay linked to this mock angle.' : 'The model is turning this angle and the received brief into the one-page markdown brief.'}
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="flex flex-wrap items-center gap-2.5">
                          <button
                            onClick={() => {
                              const note = prompt(
                                'Enter steer note for the Atelier team (e.g. "Highlight weekend welcome party budgets"):'
                              );
                              if (note) onUpdateGate(idea.id, 'gate2_brief', note);
                            }}
                            className="px-3.5 py-2 rounded-xl text-xs font-medium text-[#221E17] bg-[#FAF9F7] hover:bg-[#EFF3FF] hover:text-[#5070FF] border border-[#E0DFE2] transition-colors duration-150 pressable cursor-pointer"
                          >
                            Steer Angle...
                          </button>
                          <ThemedSelect aria-label="Pass with reason"
                            onChange={(value) => {
                              if (value) {
                                alert(
                                  `Passed on angle (${value}). Learning loop recorded this signal to tune future scoring.`
                                );
                              }
                            }}
                            defaultValue=""
                            className="px-3 py-2 rounded-xl text-xs text-[#4B4137] bg-[#FAF9F7] border border-[#E0DFE2] hover:bg-white transition-colors cursor-pointer"
                          >
                            <option value="" disabled>
                              Pass with reason...
                            </option>
                            <option value="Done before">Done before</option>
                            <option value="Off brand voice">Off brand voice</option>
                            <option value="Weak proof">Weak proof</option>
                            <option value="Not now / seasonal lull">Not now / seasonal</option>
                          </ThemedSelect>
                        </div>
                      )}
                    </div>
                  )}
                </section>


              </div>


            </div>
          )}

          {/* STAGE: Content Brief — the model's markdown write-up */}
          {activeTab === 'brief' && (
            <div className="bg-white p-5 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <span className="w-6 h-6 rounded-md bg-[#EFF3FF] text-[#5070FF] font-mono text-xs font-bold flex items-center justify-center border border-[#D1DBFF]">2</span>
                  <h3 className="font-editorial text-lg font-bold text-[#221E17]">Content Brief</h3>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={`text-xs font-mono font-bold ${currentGateIndex >= 3 ? 'text-emerald-700' : 'text-amber-700'}`}>{currentGateIndex >= 3 ? 'Approved' : 'Awaiting Whitney'}</span>
                  <button
                    onClick={() => handleCopy(briefMarkdown, 'brief_md')}
                    className="px-3 py-1.5 rounded-lg bg-[#FAF9F7] hover:bg-[#EFF3FF] text-[#5070FF] font-semibold text-xs flex items-center gap-1.5 border border-[#E0DFE2] pressable"
                  >
                    {copiedSection === 'brief_md' ? (
                      <>
                        <Check strokeWidth={2} className="w-3.5 h-3.5 text-emerald-600" /> Copied
                      </>
                    ) : (
                      <>
                        <Copy strokeWidth={1.5} className="w-3.5 h-3.5" /> Copy
                      </>
                    )}
                  </button>
                </div>
              </div>

              <h4 className="font-editorial text-xl font-bold leading-snug text-[#221E17]">{angle.title}</h4>
              {idea.suppliedCopy?.brief ? <BriefingOverview idea={idea} /> : <div className="rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] p-4"><MarkdownDocument markdown={briefMarkdown} /></div>}
              <div className="border-t border-[#E6E9F0] pt-4 flex flex-wrap items-center gap-3">
                <span className="text-xs text-[#667184]">{currentGateIndex >= 3 ? 'Brief approved · content pack generated' : currentGateIndex === 2 ? isGeneratingPack ? 'Generating content pack…' : 'Brief awaiting approval' : 'Approve the content angle before approving its brief.'}</span>
              </div>
            </div>
          )}

          {/* STAGE: Draft Pack — the five generated contents */}
          {activeTab === 'pack' && (
            <div className="space-y-4">
              {draftContents.length > 0 ? (
                <>
                  <div className="atelier-pack-sticky sticky top-0 z-20 isolate">
                  <div role="tablist" aria-label="Content pack deliverables" className="atelier-modal-tabs flex gap-1 rounded-full border border-[#E6E9F0] bg-white p-1 text-xs">
                    {['Email', 'Carousel', 'Reel 1', 'Reel 2', 'Reel 3'].map((label, index) => <button
                      key={label} type="button" role="tab" id={`pack-piece-tab-${index + 1}`}
                      aria-selected={activeContentOrder === index + 1} aria-controls="pack-piece-panel"
                      tabIndex={activeContentOrder === index + 1 ? 0 : -1}
                      disabled={!draftContents.some(piece => piece.order === index + 1)}
                      onClick={() => setActiveContentOrder(index + 1)}
                      onKeyDown={event => {
                        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
                        event.preventDefault();
                        const orders = draftContents.map(piece => piece.order);
                        const current = orders.indexOf(activeContentOrder);
                        const next = event.key === 'Home' ? orders[0] : event.key === 'End' ? orders[orders.length - 1] : orders[(current + (event.key === 'ArrowRight' ? 1 : -1) + orders.length) % orders.length];
                        setActiveContentOrder(next);
                        event.currentTarget.parentElement?.querySelector<HTMLButtonElement>(`#pack-piece-tab-${next}`)?.focus();
                      }}
                      className={`px-4 py-2 font-medium disabled:opacity-40 ${activeContentOrder === index + 1 ? 'text-[#5070FF]' : 'text-[#667184]'}`}
                    >{label}</button>)}
                  </div>
                  </div>

                  {draftContents.filter(piece => piece.order === activeContentOrder).map((piece) => {
                    const KindIcon =
                      piece.kind === 'email' ? Mail : piece.kind === 'carousel' ? Layers : Video;
                    return (
                      <article
                        key={piece.id}
                        id="pack-piece-panel" role="tabpanel" aria-labelledby={`pack-piece-tab-${piece.order}`}
                        className="bg-white p-5 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-4"
                      >
                        <div className="flex items-start justify-between gap-3 border-b border-[#E0DFE2] pb-3">
                          <div className="flex items-start gap-2.5 min-w-0">
                            <span className="w-7 h-7 rounded-md bg-[#EFF3FF] text-[#5070FF] font-mono text-xs font-bold flex items-center justify-center border border-[#D1DBFF] shrink-0 tabular-nums">
                              {String(piece.order).padStart(2, '0')}
                            </span>
                            <div className="min-w-0">
                              <div className={`flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider ${piece.kind === 'reel' ? 'text-[#A38B61] font-semibold' : 'text-[#87725F]'}`}>
                                <KindIcon strokeWidth={1.5} className="w-3.5 h-3.5" />
                                {piece.meta}
                              </div>
                              <h4 className="font-editorial text-lg font-bold text-[#221E17] leading-snug">
                                {piece.title}
                              </h4>
                            </div>
                          </div>
                          <button
                            onClick={() => handleCopy(draftPieceToText(piece), piece.id)}
                            className="text-xs text-[#5070FF] hover:underline flex items-center gap-1 font-medium pressable shrink-0"
                          >
                            {copiedSection === piece.id ? 'Copied!' : 'Copy'}
                          </button>
                        </div>

                        <div className={piece.kind === 'email' ? 'grid grid-cols-1 sm:grid-cols-3 gap-3' : 'space-y-3'}>
                          {piece.sections.filter(section => !(piece.kind === 'email' && piece.sourceText && section.label === 'Subject') && !(piece.kind === 'reel' && section.label === 'Format')).map((section) => (
                            <section key={section.label} aria-label={section.label} className={`bg-[#F7F8FB] p-4 rounded-xl border border-[#E6E9F0] ${piece.kind === 'email' && !['Date', 'Send time', 'Recipients'].includes(section.label) ? 'sm:col-span-3' : ''}`}>
                              <h5 className="text-[10px] uppercase tracking-[0.12em] text-[#5070FF] font-semibold block mb-2">
                                {section.label}
                              </h5>
                              {section.heading && <p className="text-[13px] font-semibold text-[#34445F] leading-relaxed mb-2">{section.heading}</p>}
                              <p className="text-[12px] text-[#667184] whitespace-pre-line leading-relaxed">{section.text}</p>
                            </section>
                          ))}
                        </div>
                      </article>
                    );
                  })}
                </>
              ) : (
                <div className="bg-white p-12 rounded-xl border border-[#E0DFE2] text-center space-y-4">
                  <Sparkles strokeWidth={1.5} className="w-8 h-8 text-[#5070FF] mx-auto opacity-70" />
                  <div className="max-w-md mx-auto space-y-1">
                    <h4 className="font-editorial text-xl font-bold text-[#221E17]">
                      Five contents land after the brief is approved
                    </h4>
                    <p className="text-xs text-[#4B4137] leading-relaxed">
                      Approving the received brief writes the email, the carousel, and three reels.
                    </p>
                  </div>
                  <button
                    onClick={() => setActiveTab(currentGateIndex >= 2 ? 'brief' : 'gates')}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-[#5070FF] hover:bg-[#405FE6] transition-colors shadow-wia-btn pressable"
                  >
                    Review content angle
                  </button>
                </div>
              )}
            </div>
          )}
          {activeTab === 'schedule' && (
            <section aria-label="Content pack schedule" className="bg-white p-6 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2.5"><span className="w-6 h-6 rounded-md bg-[#EFF3FF] text-[#5070FF] font-mono text-xs font-bold flex items-center justify-center border border-[#D1DBFF]">4</span><h3 className="font-editorial text-2xl font-bold">Schedule</h3></div>
                {publishingApproved && <span className={`rounded-full px-3 py-1 text-xs font-medium ${scheduleProgress.waiting === 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-[#EFF3FF] text-[#5070FF]'}`}>{scheduleProgress.scheduled ? `${scheduleProgress.scheduled}/${scheduleProgress.total} scheduled` : 'Awaiting scheduling'}</span>}
              </div>
              {publishingApproved ? <>
                <p className="text-xs text-[#4B4137] leading-relaxed">Your content pack is approved for publishing. Schedule each email, carousel, and reel individually.</p>
                <div className="space-y-2">{draftContents.map(piece => {
                  const date = contentScheduleFor(idea, piece.order);
                  return <div key={piece.id} className="rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] px-4 py-3 flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0 flex-1"><p className="text-[10px] uppercase tracking-wider text-[#87725F]">{piece.meta}</p><p className="mt-1 text-sm font-medium text-[#173354]">{piece.title}</p><p className={`mt-2 flex items-center gap-1.5 text-[11px] ${date ? 'text-emerald-700' : 'text-[#8B93A3]'}`}><CalendarClock className="w-3.5 h-3.5 shrink-0" />{date ? scheduleLabel(date) : 'Not scheduled yet'}</p></div>
                    <PackSchedulePopover idea={idea} contentOrder={piece.order} onSchedule={onSchedule} />
                  </div>;
                })}</div>
                <p className="text-[11px] text-[#8B93A3]">The saved schedule appears in Scheduled Content and the Home calendar. No content is automatically posted.</p>
              </> : <div className="space-y-3"><p className="text-xs text-[#4B4137]">Approve the content pack for publishing before scheduling.</p><button type="button" onClick={() => setActiveTab('pack')} className="text-xs font-medium text-[#5070FF]">Review content pack →</button></div>}
            </section>
          )}
          {/* SOURCE RESEARCH */}
          {activeTab === 'research' && (idea.editorialContext ? <div className="rounded-xl border border-[#E0DFE2] bg-white p-6"><button type="button" onClick={() => setActiveTab('gates')} className="mb-4 text-xs text-[#5070FF]">← Content Angle</button><AngleResearch idea={idea} /></div> : (
            <div className="bg-white p-6 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-6">
              <button type="button" onClick={() => setActiveTab('gates')} className="text-xs text-[#5070FF]">← Content Angle</button>
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-mono uppercase tracking-wider text-[#5070FF] font-semibold">
                    External Demand & Hook Signals
                  </span>
                  <h3 className="font-editorial text-2xl font-bold text-[#221E17]">
                    SerpAPI Market Grounding
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-[#87725F]">
                    Google Trends Index:
                  </span>
                  <span className="text-base font-bold font-mono text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-lg border border-emerald-200 tabular-nums">
                    {idea.research.googleTrendsScore === null ? 'Not measured' : `${idea.research.googleTrendsScore}/100 (${idea.research.trendDirection})`}
                  </span>
                </div>
              </div>

              {/* People Also Ask */}
              <div className="space-y-2">
                <h4 className="text-xs font-mono uppercase tracking-wider text-[#87725F] flex items-center gap-1.5">
                  <Search strokeWidth={1.5} className="w-3.5 h-3.5 text-[#5070FF]" />
                  People Also Ask (Hook Inspiration for Reels & Carousel Slide 2):
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {idea.research.peopleAlsoAsk.map((q, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-[#FAF9F7] rounded-xl border border-[#E0DFE2] text-xs text-[#221E17] flex items-start gap-2"
                    >
                      <span className="text-[#5070FF] font-mono font-bold">?</span>
                      <span>{q}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Modal Bottom Sticky Bar */}
        <footer aria-label="Content actions" className="px-6 py-3.5 bg-white border-t border-[#E0DFE2] flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3 text-[#87725F]">
            <span>Recorded: {idea.editorialContext ? idea.timestamp : idea.daysAgo}</span>
          </div>

          <div className="flex flex-wrap justify-end items-center gap-2">
            {copyError && <span role="alert" className="text-xs text-red-700 max-w-56">{copyError}</span>}
            {activeTab === 'gates' && (currentGateIndex === 1 ? revivalApproval ? <RevivalApproval onApprove={handleApproveAngleWithAiBrief} atCapacity={revivalAtCapacity} /> : <button type="button" disabled={isGeneratingBrief} onClick={handleApproveAngleWithAiBrief} className="px-4 py-2 rounded-full bg-[#5070FF] text-white text-xs font-semibold flex items-center gap-2 disabled:opacity-60"><CheckCircle2 className="w-3.5 h-3.5" />{isGeneratingBrief ? 'Opening content brief…' : 'Approve Angle & Write Brief'}</button> : <button type="button" onClick={() => setActiveTab('brief')} className="px-4 py-2 rounded-full bg-[#5070FF] text-white text-xs font-semibold">View Content Brief</button>)}
            {activeTab === 'brief' && (currentGateIndex === 2 ? revivalApproval ? <RevivalApproval onApprove={handleApproveBriefWithPackGeneration} atCapacity={revivalAtCapacity} /> : <button type="button" disabled={isGeneratingPack} onClick={handleApproveBriefWithPackGeneration} className="px-4 py-2 rounded-full bg-[#5070FF] text-white text-xs font-semibold flex items-center gap-2 disabled:opacity-60"><CheckCircle2 className="w-3.5 h-3.5" />{isGeneratingPack ? 'Generating content pack…' : 'Approve Brief & Generate Content Pack'}</button> : idea.pack ? <button type="button" onClick={() => setActiveTab('pack')} className="px-4 py-2 rounded-full bg-[#5070FF] text-white text-xs font-semibold">View content pack →</button> : null)}
            {activeTab === 'pack' && packReady && <button type="button" disabled={!publishingApproved && !onApprovePack} onClick={() => {
              if (!publishingApproved) onApprovePack?.(idea.id);
              setActiveTab('schedule');
            }} className="px-4 py-2 rounded-full bg-[#5070FF] text-white text-xs font-semibold flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"><CheckCircle2 className="w-3.5 h-3.5" />{publishingApproved ? scheduleProgress.scheduled ? 'View Schedule' : 'Go to Schedule' : 'Approve Content Pack & Schedule'}</button>}
            <button type="button" disabled={!draftContents.length} onClick={() => handleCopy(draftPackToText(idea.title, draftContents), 'full_pack')} className="px-4 py-2 rounded-full bg-[#EFF3FF] text-[#5070FF] text-xs font-semibold flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed">
              {copiedSection === 'full_pack' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              {copiedSection === 'full_pack' ? 'Copied all content' : 'Copy all Content'}
            </button>
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-full border border-[#E6E9F0] text-[#667184] font-medium">Done</button>
          </div>
        </footer>
      </div>
    </div>
  );
};
