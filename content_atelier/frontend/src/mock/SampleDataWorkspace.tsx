import React, { useEffect, useState } from 'react';
import { AnimatePresence } from 'motion/react';
import { useNavigate } from 'react-router-dom';
import { ContentIdea, GateStatus, Moment } from '../types/atelier';
import { INITIAL_MOMENTS } from '../data/mockData';
import { advanceEditorialItem, reviveEditorialItem } from '../utils/editorialWorkflow';
import { approvePackForScheduling, scheduleContentPiece } from '../utils/publishingSchedule';
import { editorialWeeks, stampEditorialItem, editorialWeekFor, hasWeeklyCapacity } from '../utils/editorialWeeks';
import { IdeaCard } from '../components/IdeaCard';
import { IdeaDetailModal } from '../components/IdeaDetailModal';
import { MomentsLedgerView } from '../components/MomentsLedgerView';
import { ResearchView } from '../components/ResearchView';
import { InboxApprovalsView } from '../components/InboxApprovalsView';
import { FlagIdeaModal } from '../components/FlagIdeaModal';
import { ContentPacksView } from '../components/ContentPacksView';
import { EditorialHub, InspectorTab } from '../components/EditorialHub';
import { SampleDataMarker } from './SampleDataMarker';
import { loadEditorialLibrary, saveEditorialLibrary } from './library';
import type { SampleView } from './sampleViews';

/* The screens that render from the built-in examples in src/data (plan 1.F4), in the demo build only (6.F3): each has a
   /sample/<view> URL (sampleViews.ts) and carries the "Sample data" marker. Their state is local to the browser
   (localStorage for the ideas, shared with the saved flow through library.ts). */

const FILTERS = [['top', 'Top Ideas'], ['calls', 'From Client Calls'], ['slack', 'From Slack'], ['saved', 'Saved']] as const;

function SampleHeading({ title }: { title: string }) {
  return <header className="mb-4"><h1 className="font-editorial text-4xl text-[#173354]">{title}</h1></header>;
}

export function SampleDataWorkspace({ view }: { view: SampleView }) {
  const [ideas, setIdeas] = useState<ContentIdea[]>(() => loadEditorialLibrary());
  useEffect(() => saveEditorialLibrary(ideas), [ideas]);

  const [moments, setMoments] = useState<Moment[]>(INITIAL_MOMENTS);
  const [selectedIdea, setSelectedIdea] = useState<ContentIdea | null>(null);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('gates');
  const [inspectorContentOrder, setInspectorContentOrder] = useState(1);
  const [flagOpen, setFlagOpen] = useState(false);
  const [filter, setFilter] = useState<typeof FILTERS[number][0]>('top');
  const [savedIdeaIds] = useState<string[]>(['idea-1']);

  const reviewEditorialItem = (idea: ContentIdea, tab: InspectorTab, contentOrder = 1) => {
    setInspectorContentOrder(contentOrder); setInspectorTab(tab); setSelectedIdea(idea);
  };

  const handleUpdateGate = (ideaId: string, newGate: GateStatus, note?: string) => {
    const approvedAt = new Date().toISOString();
    const source = ideas.find(idea => idea.id === ideaId);
    const latestWeek = editorialWeeks(ideas)[0];
    const isApproval = source && ((source.gate === 'gate1_angle' && newGate === 'gate2_brief') || (source.gate === 'gate2_brief' && newGate === 'gate3_pack'));
    if (isApproval && source.editorialWeek && source.editorialWeek < latestWeek) {
      try {
        const revived = reviveEditorialItem(source, ideas, approvedAt);
        setIdeas(prev => prev.map(idea => idea.id === ideaId ? revived : idea));
        setSelectedIdea(null);
      } catch { /* A full studio leaves the archived concept unchanged. */ }
      return;
    }
    setIdeas(prev => prev.map(idea => idea.id === ideaId ? advanceEditorialItem(idea, newGate, approvedAt, note) : idea));
    setSelectedIdea(prev => prev?.id === ideaId ? advanceEditorialItem(prev, newGate, approvedAt, note) : prev);
  };

  // The previous concepts' pack and schedule controls do what they say, in this browser (6.F3: they were no-ops).
  const navigate = useNavigate();
  const handleApprovePack = (ideaId: string) => setIdeas(prev => prev.map(idea => idea.id === ideaId ? approvePackForScheduling(idea) : idea));
  const handleSchedule = (ideaId: string, date: string, time?: string, contentOrder = 1) => {
    const source = ideas.find(idea => idea.id === ideaId);
    if (!source || !time) throw new Error('This content pack is no longer available.');
    const scheduled = scheduleContentPiece(approvePackForScheduling(source), contentOrder, date, time);
    setIdeas(prev => prev.map(idea => idea.id === ideaId ? scheduled : idea));
  };

  const handleUpdateCta = (ideaId: string, newCta: 'Elevate' | 'Accelerators' | 'LeadLock') => {
    setIdeas(prev => prev.map(idea => idea.id === ideaId ? { ...idea, suggestedCta: newCta } : idea));
    setSelectedIdea(prev => prev && prev.id === ideaId ? { ...prev, suggestedCta: newCta } : prev);
  };

  const handlePromoteMomentToIdea = (moment: Moment) => {
    if (!hasWeeklyCapacity(ideas, editorialWeekFor(new Date().toISOString()))) {
      window.alert('This week already has four concepts across angles, briefs, and packs. Approval advances a concept; it does not free another slot.');
      return;
    }
    const newIdea: ContentIdea = {
      id: `idea-${Date.now()}`,
      title: `${moment.speaker.split(' ')[0]}’s Breakthrough: ${moment.type}`,
      subtitle: `Mined directly from ${moment.sourceName}.`,
      badge: moment.source === 'slack' ? 'Slack Win' : moment.source === 'zoom' ? 'Workshop Vault' : 'Client Call',
      daysAgo: 'Just now',
      timestamp: moment.date,
      primaryQuote: moment.quote,
      client: moment.clientName,
      sourceType: moment.source,
      sourceDetails: `${moment.channelOrMeeting} · ${moment.timestamp}`,
      score: 93,
      scoresBreakdown: { proof: 96, audiencePain: 92, offerFit: 94, recurrence: 89, novelty: 90, demand: 88 },
      suggestedCta: 'Elevate',
      gate: 'gate1_angle',
      brief: {
        coreInsight: moment.quote,
        messageSpine: ['High-converting wedding marketing starts with real client proof, not theory.', moment.quote, 'Systems replace stamina.'],
        audiencePain: 'Wedding pros overwhelmed by marketing ambiguity.',
        formatSplit: {
          emailFocus: 'Personal reflection on this client case study.',
          carouselFocus: '5-step tactical implementation framework.',
          reelsFocus: 'Reel 1: The bold claim / Reel 2: The proof breakdown / Reel 3: Actionable CTA.',
        },
        claimsRequiringConsent: ['Check client clearance before citing exact metrics.'],
        openQuestionsForWhitney: ['Confirm whether this maps to Elevate or Accelerators.'],
      },
      research: {
        searchQuery: 'wedding industry client results',
        googleTrendsScore: 82,
        trendDirection: 'rising',
        peopleAlsoAsk: ['How to increase wedding business revenue without working weekends?', 'What is the highest ROI marketing for luxury wedding planners?'],
        autocomplete: ['wedding vendor lead generation', 'scaling wedding planning business'],
        forumDiscussions: [],
      },
    };
    const stamped = stampEditorialItem({ ...newIdea, createdAt: new Date().toISOString() });
    setIdeas(prev => [stamped, ...prev]);
    setSelectedIdea(stamped);
  };

  const handleFlagNewIdea = (data: { title: string; quote: string; source: any; client: string; suggestedCta: 'Elevate' | 'Accelerators' | 'LeadLock' }) => {
    if (!hasWeeklyCapacity(ideas, editorialWeekFor(new Date().toISOString()))) return;
    const newIdea: ContentIdea = {
      id: `idea-${Date.now()}`,
      title: data.title,
      subtitle: `Flagged directly for Giselle from ${data.source}.`,
      badge: 'Client Call',
      daysAgo: 'Today',
      timestamp: 'Today',
      primaryQuote: data.quote,
      client: data.client,
      sourceType: data.source,
      sourceDetails: 'Direct Slack Flag · Whitney',
      score: 95,
      scoresBreakdown: { proof: 96, audiencePain: 95, offerFit: 95, recurrence: 90, novelty: 95, demand: 90 },
      suggestedCta: data.suggestedCta,
      gate: 'gate1_angle',
      brief: {
        coreInsight: data.quote,
        messageSpine: [data.title, 'Direct insight flagged by Whitney.', 'Proof-driven luxury wedding positioning.'],
        audiencePain: 'Tired of generic marketing advice.',
        formatSplit: { emailFocus: 'Founder narrative.', carouselFocus: 'Actionable breakdown slides.', reelsFocus: '3 concise video angles.' },
        claimsRequiringConsent: [],
        openQuestionsForWhitney: [],
      },
      research: {
        searchQuery: data.title.toLowerCase(),
        googleTrendsScore: 85,
        trendDirection: 'rising',
        peopleAlsoAsk: ['How to market luxury wedding services?'],
        autocomplete: [data.title.toLowerCase()],
        forumDiscussions: [],
      },
    };
    const stamped = stampEditorialItem({ ...newIdea, createdAt: new Date().toISOString() });
    setIdeas(prev => [stamped, ...prev]);
    setSelectedIdea(stamped);
  };

  const filtered = ideas.filter(idea => filter === 'calls' ? idea.sourceType === 'fathom' || idea.sourceType === 'zoom'
    : filter === 'slack' ? idea.sourceType === 'slack' : filter === 'saved' ? savedIdeaIds.includes(idea.id) : true);

  return <div data-sample-view={view}>
    <SampleDataMarker />
    {view === 'ideas' && <div className="space-y-6">
      <SampleHeading title="Ideas" />
      <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-[#E0DFE2]">
        {FILTERS.map(([id, label]) => <button key={id} type="button" aria-pressed={filter === id} onClick={() => setFilter(id)}
          className={`px-4 py-2 rounded-xl text-xs whitespace-nowrap ${filter === id ? 'bg-[#EFF3FF] text-[#5070FF] font-semibold border border-[#D1DBFF]' : 'text-[#4B4137] hover:bg-[#FAF9F7]'}`}>{label}</button>)}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filtered.map(idea => <IdeaCard key={idea.id} idea={idea} onSelect={selected => setSelectedIdea(selected)} />)}
      </div>
    </div>}
    {view === 'previous' && <EditorialHub mode="previous" initialTab="angles" ideas={ideas} onReview={reviewEditorialItem} onApprovePack={handleApprovePack}
      onSchedule={handleSchedule} onUpdateGate={handleUpdateGate} onSwitchSection={() => navigate('/studio')} onAddAngle={() => setFlagOpen(true)} />}
    {view === 'moments' && <MomentsLedgerView moments={moments} onPromoteToIdea={handlePromoteMomentToIdea} onOpenFlagModal={() => setFlagOpen(true)}
      onAddMoments={added => setMoments(prev => [...added, ...prev])} />}
    {view === 'research' && <ResearchView ideas={ideas} onSelectIdea={idea => setSelectedIdea(idea)} />}
    {view === 'inbox' && <InboxApprovalsView ideas={ideas} onSelectIdea={idea => setSelectedIdea(idea)} onUpdateGate={handleUpdateGate} />}
    {view === 'packs' && <ContentPacksView ideas={ideas} onSelectIdea={idea => reviewEditorialItem(idea, 'pack')} />}

    <AnimatePresence initial={false}>
      {selectedIdea && <IdeaDetailModal idea={selectedIdea} initialTab={inspectorTab} initialContentOrder={inspectorContentOrder}
        revivalApproval={!!selectedIdea.editorialWeek && selectedIdea.editorialWeek < editorialWeeks(ideas)[0]}
        revivalAtCapacity={!hasWeeklyCapacity(ideas, editorialWeeks(ideas)[0])}
        onClose={() => { setSelectedIdea(null); setInspectorTab('gates'); }} onUpdateGate={handleUpdateGate} onUpdateCta={handleUpdateCta} />}
    </AnimatePresence>
    <AnimatePresence initial={false}>
      {flagOpen && <FlagIdeaModal atCapacity={!hasWeeklyCapacity(ideas, editorialWeekFor(new Date().toISOString()))} onClose={() => setFlagOpen(false)} onSubmit={handleFlagNewIdea} />}
    </AnimatePresence>
  </div>;
}
