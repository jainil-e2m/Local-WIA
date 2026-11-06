/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import Lenis from 'lenis';
import { motion, AnimatePresence } from 'motion/react';
import {
  Plus,
  Search,
  Lightbulb,
} from 'lucide-react';

import { ContentIdea, GateStatus, Moment } from './types/atelier';
import { INITIAL_IDEAS, INITIAL_MOMENTS } from './data/mockData';
import { mergeEditorialMocks } from './data/editorialMockData';
import { advanceEditorialItem, reviveEditorialItem } from './utils/editorialWorkflow';
import { resetStudioForDeployment } from './utils/studioDeployment';
import { editorialWeeks, stampEditorialItem, editorialWeekFor, hasWeeklyCapacity } from './utils/editorialWeeks';
import { AtelierCanvas } from './components/AtelierCanvas';
import { Sidebar, NavView } from './components/Sidebar';
import { TopHeader } from './components/TopHeader';
import { BackendCalendar } from './components/BackendCalendar';
import { BackendStudio } from './components/BackendStudio';
import { StoredPacks } from './components/StoredPacks';
import { IdeaCard } from './components/IdeaCard';
import { IdeaDetailModal } from './components/IdeaDetailModal';
import { MomentsLedgerView } from './components/MomentsLedgerView';
import { ResearchView } from './components/ResearchView';
import { SourcesView } from './components/SourcesView';
import { ContentPacksView } from './components/ContentPacksView';
import { InboxApprovalsView } from './components/InboxApprovalsView';
import { BrandKitModal } from './components/BrandKitModal';
import { FlagIdeaModal } from './components/FlagIdeaModal';
import { EditorialHub, InspectorTab, EditorialTab } from './components/EditorialHub';
import { approvePackForScheduling, scheduleContentPiece, schedulePack } from './utils/publishingSchedule';
import { useAuth } from './auth/AuthProvider';
import { userGreeting } from './auth/session';

const EDITORIAL_STORAGE_KEY = 'wia-editorial-library-v1';
function loadEditorialLibrary(): ContentIdea[] {
  try {
    const saved = JSON.parse(localStorage.getItem(EDITORIAL_STORAGE_KEY) || 'null');
    if (Array.isArray(saved) && saved.length && saved.every(item => item.id && item.title && item.brief && item.research && ['gate1_angle', 'gate2_brief', 'gate3_pack', 'approved_for_giselle'].includes(item.gate))) {
      return mergeEditorialMocks([...saved, ...INITIAL_IDEAS.filter(idea => !saved.some(item => item.id === idea.id))]).map(idea => stampEditorialItem(idea));
    }
  } catch { /* Use the supplied library when browser storage is unavailable. */ }
  return mergeEditorialMocks(INITIAL_IDEAS).map(idea => stampEditorialItem(idea));
}

export default function App() {
  const { user } = useAuth();
  const [ideas, setIdeas] = useState<ContentIdea[]>(loadEditorialLibrary);
  const [studioReady, setStudioReady] = useState(false);
  const [studioError, setStudioError] = useState(false);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 10_000);
    const initialize = async () => {
      try {
        let deploymentId = 'local-development';
        if (!import.meta.env.DEV) {
          const response = await fetch('/api/studio/deployment', {
            credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: controller.signal,
          });
          if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('Unavailable');
          const config = await response.json();
          if (typeof config.deploymentId !== 'string' || !config.deploymentId) throw new Error('Invalid studio configuration');
          deploymentId = config.deploymentId;
        }
        if (!active || controller.signal.aborted) return;
        setIdeas(existing => resetStudioForDeployment(mergeEditorialMocks(existing), deploymentId).map(idea => stampEditorialItem(idea)));
        setStudioReady(true);
      } catch {
        if (active) setStudioError(true);
      } finally { window.clearTimeout(timeout); }
    };
    void initialize();
    return () => { active = false; window.clearTimeout(timeout); controller.abort(); };
  }, []);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('gates');
  const [studioInitialTab, setStudioInitialTab] = useState<EditorialTab>('angles');
  const [inspectorContentOrder, setInspectorContentOrder] = useState(1);
  const [moments, setMoments] = useState<Moment[]>(INITIAL_MOMENTS);
  const [currentView, setCurrentView] = useState<NavView>('editorial');
  const [activeFilter, setActiveFilter] = useState<'top' | 'calls' | 'slack' | 'saved'>('top');
  const [homeTabMode, setHomeTabMode] = useState<'calendar' | 'ideas'>('calendar');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIdea, setSelectedIdea] = useState<ContentIdea | null>(null);
  const [isBrandKitOpen, setIsBrandKitOpen] = useState(false);
  const [isFlagModalOpen, setIsFlagModalOpen] = useState(false);
  const [savedIdeaIds, setSavedIdeaIds] = useState<string[]>(['idea-1']);
  const searchRef = useRef<HTMLInputElement>(null);
  const [armSearch, setArmSearch] = useState(false);

  useEffect(() => {
    if (!studioReady) return;
    try { localStorage.setItem(EDITORIAL_STORAGE_KEY, JSON.stringify(ideas)); }
    catch { /* Keep the in-memory workflow usable when storage is blocked. */ }
  }, [ideas, studioReady]);

  const reviewEditorialItem = (idea: ContentIdea, tab: InspectorTab, contentOrder = 1) => {
    setInspectorContentOrder(contentOrder);
    setInspectorTab(tab);
    setSelectedIdea(idea);
  };

  useEffect(() => {
    if (!armSearch) return;
    if (currentView !== 'home' && currentView !== 'ideas') return;
    searchRef.current?.focus();
    setArmSearch(false);
  }, [armSearch, currentView]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        if (currentView !== 'home' && currentView !== 'ideas') {
          setCurrentView('home');
          setHomeTabMode('calendar');
          setArmSearch(true);
          return;
        }
        searchRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [currentView]);

  const focusSearch = () => {
    if (currentView !== 'home' && currentView !== 'ideas') {
      setCurrentView('home');
      setHomeTabMode('calendar');
      setArmSearch(true);
      return;
    }
    searchRef.current?.focus();
  };

  // Initialize Lenis smooth inertial scrolling
  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.1,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      orientation: 'vertical',
      smoothWheel: true,
      prevent: import.meta.env.DEV ? node => !!node.closest('[data-agentation-root], [data-agentation-portal]') : undefined,
    });

    let rafId: number;
    function raf(time: number) {
      lenis.raf(time);
      rafId = requestAnimationFrame(raf);
    }
    rafId = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(rafId);
      lenis.destroy();
    };
  }, []);

  // Update gate status for an idea
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
        setStudioInitialTab(source.gate === 'gate1_angle' ? 'angles' : 'briefs');
        setCurrentView('editorial');
      } catch { /* A full studio leaves the archived concept unchanged. */ }
      return;
    }
    setIdeas(prev => prev.map(idea => idea.id === ideaId ? advanceEditorialItem(idea, newGate, approvedAt, note) : idea));
    setSelectedIdea(prev => prev?.id === ideaId ? advanceEditorialItem(prev, newGate, approvedAt, note) : prev);
  };

  const handleApprovePack = (id: string) => {
    const update = (idea: ContentIdea) => idea.id === id ? approvePackForScheduling(idea) : idea;
    setIdeas(prev => prev.map(update));
    setSelectedIdea(prev => prev ? update(prev) : prev);
  };
  const handleLibrarySchedule = (id: string, date: string, time = '09:00', contentOrder?: number) => {
    const source = ideas.find(idea => idea.id === id);
    if (!source) throw new Error('This content pack is no longer available.');
    const ready = contentOrder === undefined ? approvePackForScheduling(source) : source;
    const result = contentOrder === undefined ? schedulePack(ready, date, time) : scheduleContentPiece(ready, contentOrder, date, time);
    const update = (idea: ContentIdea) => idea.id === id ? { ...idea, publishingApprovedAt: result.publishingApprovedAt, scheduledAt: result.scheduledAt, contentSchedules: result.contentSchedules } : idea;
    setIdeas(prev => prev.map(update));
    setSelectedIdea(prev => prev ? update(prev) : prev);
  };

  // Add freshly synced moments from Fathom, Zoom, or Slack
  const handleAddMoments = (newMoments: Moment[]) => {
    setMoments((prev) => [...newMoments, ...prev]);
  };

  // Update target CTA
  const handleUpdateCta = (
    ideaId: string,
    newCta: 'Elevate' | 'Accelerators' | 'LeadLock'
  ) => {
    setIdeas((prev) =>
      prev.map((idea) => (idea.id === ideaId ? { ...idea, suggestedCta: newCta } : idea))
    );
    if (selectedIdea && selectedIdea.id === ideaId) {
      setSelectedIdea((prev) => (prev ? { ...prev, suggestedCta: newCta } : null));
    }
  };

  // Promote a raw moment into a content idea
  const handlePromoteMomentToIdea = (moment: Moment) => {
    if (!hasWeeklyCapacity(ideas, editorialWeekFor(new Date().toISOString()))) {
      window.alert('This week already has four concepts across angles, briefs, and packs. Approval advances a concept; it does not free another slot.');
      return;
    }
    const newIdea: ContentIdea = {
      id: `idea-${Date.now()}`,
      title: `${moment.speaker.split(' ')[0]}’s Breakthrough: ${moment.type}`,
      subtitle: `Mined directly from ${moment.sourceName}.`,
      badge:
        moment.source === 'slack'
          ? 'Slack Win'
          : moment.source === 'zoom'
          ? 'Workshop Vault'
          : 'Client Call',
      daysAgo: 'Just now',
      timestamp: moment.date,
      primaryQuote: moment.quote,
      client: moment.clientName,
      sourceType: moment.source,
      sourceDetails: `${moment.channelOrMeeting} · ${moment.timestamp}`,
      score: 93,
      scoresBreakdown: {
        proof: 96,
        audiencePain: 92,
        offerFit: 94,
        recurrence: 89,
        novelty: 90,
        demand: 88,
      },
      suggestedCta: 'Elevate',
      gate: 'gate1_angle',
      brief: {
        coreInsight: moment.quote,
        messageSpine: [
          'High-converting wedding marketing starts with real client proof, not theory.',
          moment.quote,
          'Systems replace stamina.',
        ],
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
        peopleAlsoAsk: [
          'How to increase wedding business revenue without working weekends?',
          'What is the highest ROI marketing for luxury wedding planners?',
        ],
        autocomplete: ['wedding vendor lead generation', 'scaling wedding planning business'],
        forumDiscussions: [],
      },
    };

    const stampedIdea = stampEditorialItem({ ...newIdea, createdAt: new Date().toISOString() });
    setIdeas((prev) => [stampedIdea, ...prev]);
    setSelectedIdea(stampedIdea);
  };

  // Flag an idea directly like Whitney in Slack
  const handleFlagNewIdea = (data: {
    title: string;
    quote: string;
    source: any;
    client: string;
    suggestedCta: 'Elevate' | 'Accelerators' | 'LeadLock';
  }) => {
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
      sourceDetails: `Direct Slack Flag · Whitney`,
      score: 95,
      scoresBreakdown: {
        proof: 96,
        audiencePain: 95,
        offerFit: 95,
        recurrence: 90,
        novelty: 95,
        demand: 90,
      },
      suggestedCta: data.suggestedCta,
      gate: 'gate1_angle',
      brief: {
        coreInsight: data.quote,
        messageSpine: [
          data.title,
          'Direct insight flagged by Whitney.',
          'Proof-driven luxury wedding positioning.',
        ],
        audiencePain: 'Tired of generic marketing advice.',
        formatSplit: {
          emailFocus: 'Founder narrative.',
          carouselFocus: 'Actionable breakdown slides.',
          reelsFocus: '3 concise video angles.',
        },
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

    const stampedIdea = stampEditorialItem({ ...newIdea, createdAt: new Date().toISOString() });
    setIdeas((prev) => [stampedIdea, ...prev]);
    setSelectedIdea(stampedIdea);
  };

  // Filter ideas based on search and active filter tab
  const filteredIdeas = ideas.filter((idea) => {
    const matchesSearch =
      searchQuery === '' ||
      idea.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      idea.primaryQuote.toLowerCase().includes(searchQuery.toLowerCase()) ||
      idea.client.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (activeFilter === 'calls') {
      return idea.sourceType === 'fathom' || idea.sourceType === 'zoom';
    }
    if (activeFilter === 'slack') {
      return idea.sourceType === 'slack';
    }
    if (activeFilter === 'saved') {
      return savedIdeaIds.includes(idea.id);
    }
    return true; // 'top'
  });

  const latestWeek = editorialWeeks(ideas)[0];
  const pendingGatesCount = ideas.filter((i) => i.gate === 'gate1_angle' || i.gate === 'gate2_brief').length;
  const weeklyPendingCount = ideas.filter(i => i.editorialWeek === latestWeek && (i.gate === 'gate1_angle' || i.gate === 'gate2_brief')).length;

  if (!studioReady) return <main className="min-h-screen bg-[#F6F7FB] flex items-center justify-center text-[#173354]">
    {studioError ? <div role="alert" className="text-center space-y-3"><p>Content Atelier could not be loaded.</p><button className="underline" onClick={() => window.location.reload()}>Retry</button></div> : <p role="status">Loading Content Atelier…</p>}
  </main>;

  return (
    <div className="min-h-screen bg-[#F6F7FB] text-[#1B2433] relative flex font-sans antialiased overflow-x-clip selection:bg-[#1B2838]/10 selection:text-[#1B2838]">
      <AtelierCanvas />

      <Sidebar
        currentView={currentView}
        onNavigate={(view) => {
          setCurrentView(view);
          if (view === 'home') setHomeTabMode('calendar');
          if (view === 'ideas') setHomeTabMode('ideas');
        }}
        pendingGatesCount={weeklyPendingCount}
      />

      <div className={`atelier-main flex-1 flex flex-col min-w-0 z-10 relative px-3 sm:px-7 lg:px-10 pt-4 ${currentView === 'home' ? 'atelier-home' : ''}`}>
        <TopHeader
          leading={
            (
              <div className="flex items-center gap-3">
                <span className="h-px w-6 bg-[#C6A56A]" />
                <span className="text-[10px] font-medium tracking-[0.22em] uppercase text-[#173354]">
                  Content Atelier
                </span>
              </div>
            )
          }
          onOpenInbox={() => setCurrentView('editorial')}
          onOpenBrandKit={() => setIsBrandKitOpen(true)}
          pendingCount={pendingGatesCount}
        />

        <main className="flex-1 pb-10 w-full">
          {(currentView === 'home' || currentView === 'ideas') && (
            <div className="atelier-home-content space-y-5">
              <div className="atelier-home-hero flex flex-col xl:flex-row xl:items-start justify-between gap-5">
                <div className="min-w-0">
                  <h1 className="font-editorial text-[36px] leading-tight font-medium tracking-[-0.02em] text-[#173354]">
                    {userGreeting(user)}
                  </h1>
                  <div className="mt-3 flex items-center gap-3">
                    <p className="text-[12px] text-[#B99A43]">
                      {homeTabMode === 'calendar' && currentView === 'home'
                        ? 'Scheduled content packs & publishing plan'
                        : "This week's ranked angles, mined from calls and client wins"}
                    </p>
                  </div>
                </div>

                <div className="atelier-home-tools flex flex-col items-stretch sm:items-end gap-7 shrink-0 pt-2">
                  <div className="flex flex-wrap items-center justify-end gap-2">
                    <div className="relative">
                      <Search
                        strokeWidth={1.75}
                        className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#A0A8B6] pointer-events-none"
                      />
                      <input
                        ref={searchRef}
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search moments, ideas or client wins..."
                        className="w-[312px] max-w-full h-8 bg-white text-[10px] text-[#173354] placeholder:text-[#8B97A8] pl-9 pr-12 rounded-full border border-[#D7C99F] shadow-[0_4px_18px_rgba(167,139,64,0.06)] focus:outline-none focus:ring-2 focus:ring-[#1B2838]/10"
                      />
                      <kbd className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-[#9AA3B2] bg-[#F4F6F9] border border-[#E6E9F0] rounded-md px-1.5 py-0.5">
                        ⌘K
                      </kbd>
                    </div>

                    <button
                      type="button"
                      onClick={() => setIsFlagModalOpen(true)}
                      className="h-8 px-5 rounded-full bg-[#C8A83E] text-white text-[10px] font-medium inline-flex items-center gap-2 hover:bg-[#B89934] transition-colors cursor-pointer"
                    >
                      <Plus strokeWidth={2} className="w-3.5 h-3.5" />
                      <span>Flag idea</span>
                    </button>
                  </div>

                </div>
              </div>

              {/* RENDER CONTENT CALENDAR IF IN CALENDAR MODE ON HOME */}
              {currentView === 'home' && homeTabMode === 'calendar' && (
              <BackendCalendar query={searchQuery} />
              )}

              {/* RENDER IDEAS GRID IF IN IDEAS MODE OR IDEAS VIEW */}
              {(currentView === 'ideas' || (currentView === 'home' && homeTabMode === 'ideas')) && (
                <div className="space-y-6">
                  {/* Filter Tabs matching screenshot & better-ui concentric styling */}
                  <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-[#E0DFE2]">
                    <button
                      onClick={() => setActiveFilter('top')}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs transition-colors duration-150 cursor-pointer whitespace-nowrap pressable ${
                        activeFilter === 'top'
                          ? 'bg-[#EFF3FF] text-[#5070FF] font-semibold border border-[#D1DBFF] shadow-2xs'
                          : 'text-[#4B4137] hover:bg-[#FAF9F7] hover:text-[#221E17]'
                      }`}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-[#5070FF]" />
                      <span>Top Ideas</span>
                      <span className="font-mono text-[11px] text-[#87725F] tabular-nums font-semibold">{ideas.length}</span>
                    </button>

                    <button
                      onClick={() => setActiveFilter('calls')}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs transition-colors duration-150 cursor-pointer whitespace-nowrap pressable ${
                        activeFilter === 'calls'
                          ? 'bg-[#EFF3FF] text-[#5070FF] font-semibold border border-[#D1DBFF] shadow-2xs'
                          : 'text-[#4B4137] hover:bg-[#FAF9F7] hover:text-[#221E17]'
                      }`}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-[#87725F]" />
                      <span>From Client Calls</span>
                    </button>

                    <button
                      onClick={() => setActiveFilter('slack')}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs transition-colors duration-150 cursor-pointer whitespace-nowrap pressable ${
                        activeFilter === 'slack'
                          ? 'bg-[#EFF3FF] text-[#5070FF] font-semibold border border-[#D1DBFF] shadow-2xs'
                          : 'text-[#4B4137] hover:bg-[#FAF9F7] hover:text-[#221E17]'
                      }`}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-[#87725F]" />
                      <span>From Slack</span>
                    </button>

                    <button
                      onClick={() => setActiveFilter('saved')}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs transition-colors duration-150 cursor-pointer whitespace-nowrap pressable ${
                        activeFilter === 'saved'
                          ? 'bg-[#EFF3FF] text-[#5070FF] font-semibold border border-[#D1DBFF] shadow-2xs'
                          : 'text-[#4B4137] hover:bg-[#FAF9F7] hover:text-[#221E17]'
                      }`}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-[#87725F]" />
                      <span>Saved</span>
                    </button>
                  </div>

                  {/* 3-Card Grid Matching User Screenshot Layout */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredIdeas.map((idea) => (
                      <IdeaCard
                        key={idea.id}
                        idea={idea}
                        onSelect={(selected) => setSelectedIdea(selected)}
                      />
                    ))}
                  </div>
                </div>
              )}

            </div>
          )}

          {currentView === 'editorial' && <BackendStudio />}
          {currentView === 'previous' && (
            <EditorialHub
              key={currentView}
              mode='previous'
              initialTab='angles'
              ideas={ideas}
              onReview={reviewEditorialItem}
              onApprovePack={() => {}}
              onSchedule={() => {}}
                  onUpdateGate={handleUpdateGate}
              onSwitchSection={() => setCurrentView(currentView === 'previous' ? 'editorial' : 'previous')}
              onAddAngle={() => setIsFlagModalOpen(true)}
            />
          )}

          {/* VIEW: MOMENTS LEDGER */}
          {currentView === 'moments' && (
            <MomentsLedgerView
              moments={moments}
              onPromoteToIdea={handlePromoteMomentToIdea}
              onOpenFlagModal={() => setIsFlagModalOpen(true)}
              onAddMoments={handleAddMoments}
            />
          )}

          {/* VIEW: RESEARCH */}
          {currentView === 'sources' && <SourcesView />}
          {currentView === 'research' && (
            <ResearchView
              ideas={ideas}
              onSelectIdea={(idea) => setSelectedIdea(idea)}
            />
          )}

          {/* VIEW: CONTENT PACKS */}
          {currentView === 'packs' && <StoredPacks />}

          {currentView === 'inbox' && (
            <InboxApprovalsView
              ideas={ideas}
              onSelectIdea={(idea) => setSelectedIdea(idea)}
              onUpdateGate={handleUpdateGate}
            />
          )}
        </main>
      </div>

      {/* Interactive 3-Gate Idea Inspector & Deliverable Studio Modal */}
      <AnimatePresence initial={false}>
        {selectedIdea && (
          <IdeaDetailModal
            idea={selectedIdea}
            initialTab={inspectorTab}
            initialContentOrder={inspectorContentOrder}
            revivalApproval={!!selectedIdea.editorialWeek && selectedIdea.editorialWeek < editorialWeeks(ideas)[0]}
            revivalAtCapacity={!hasWeeklyCapacity(ideas, editorialWeeks(ideas)[0])}
            onClose={() => { setSelectedIdea(null); setInspectorTab('gates'); }}
            onUpdateGate={handleUpdateGate}
            onUpdateCta={handleUpdateCta}
          />
        )}
      </AnimatePresence>

      {/* Brand Kit & Founder Voice Modal */}
      <AnimatePresence initial={false}>
        {isBrandKitOpen && (
          <BrandKitModal onClose={() => setIsBrandKitOpen(false)} />
        )}
      </AnimatePresence>

      {/* Flag Idea for Giselle Modal */}
      <AnimatePresence initial={false}>
        {isFlagModalOpen && (
          <FlagIdeaModal
            atCapacity={!hasWeeklyCapacity(ideas, editorialWeekFor(new Date().toISOString()))}
            onClose={() => setIsFlagModalOpen(false)}
            onSubmit={handleFlagNewIdea}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
