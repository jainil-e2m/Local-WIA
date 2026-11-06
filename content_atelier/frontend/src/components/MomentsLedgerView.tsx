import React, { useState } from 'react';
import { ThemedSelect } from './ThemedSelect';
import {
  Layers,
  Search,
  CheckCircle2,
  Clock,
  Sparkles,
  ShieldCheck,
  Plus,
  RefreshCw,
  Radio,
  Volume2,
  Check,
  ExternalLink
} from 'lucide-react';
import { Moment, SourceType } from '../types/atelier';

interface MomentsLedgerViewProps {
  moments: Moment[];
  onPromoteToIdea: (moment: Moment) => void;
  onOpenFlagModal: () => void;
  onAddMoments?: (newMoments: Moment[]) => void;
}

export const MomentsLedgerView: React.FC<MomentsLedgerViewProps> = ({
  moments,
  onPromoteToIdea,
  onOpenFlagModal,
  onAddMoments,
}) => {
  const [sourceFilter, setSourceFilter] = useState<'all' | SourceType>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStep, setSyncStep] = useState<number>(0);
  const [syncCompleteNotification, setSyncCompleteNotification] = useState<string | null>(null);

  // Trigger simulated live ingestion from Fathom, Zoom, and Slack
  const handleSyncNow = () => {
    if (isSyncing) return;
    setIsSyncing(true);
    setSyncStep(1);
    setSyncCompleteNotification(null);

    // Step 1: Connecting to feeds
    setTimeout(() => {
      setSyncStep(2);
    }, 1100);

    // Step 2: Transcribing & audio speech-to-text extraction
    setTimeout(() => {
      setSyncStep(3);
    }, 2200);

    // Step 3: Privacy & clearance checks
    setTimeout(() => {
      setSyncStep(4);
      
      const newMinedMoments: Moment[] = [
        {
          id: `m-sync-${Date.now()}-1`,
          source: 'fathom',
          sourceName: 'Fathom AI · Client Advisory Call #44',
          speaker: 'Elena Rostova (Floral Sculptor, Miami)',
          clientName: 'Elena Rostova Atelier',
          date: 'Just now',
          timestamp: '22:15',
          audioDuration: '48m',
          type: 'Result',
          quote: "We raised our minimum floral investment package to $14,000 after launching the Elevate ad funnel, and booked 4 out of 5 couples this week with zero price resistance.",
          clearance: 'cleared',
          channelOrMeeting: 'Zoom / Fathom Recording #44',
          speakerVerified: true,
        },
        {
          id: `m-sync-${Date.now()}-2`,
          source: 'slack',
          sourceName: 'Slack #wins-and-breakthroughs',
          speaker: 'Marcus Sterling (Estate Venue Director)',
          clientName: 'Château Belleview',
          date: '10m ago',
          timestamp: '11:42 AM',
          type: 'Result',
          quote: "LeadLock captured 19 inquiries in 72 hours for our estate wedding open day. That's a $210k qualified booking pipeline created without touching our organic Instagram feed.",
          clearance: 'needs_consent',
          channelOrMeeting: 'Slack Channel #wins-and-breakthroughs',
          speakerVerified: true,
        },
        {
          id: `m-sync-${Date.now()}-3`,
          source: 'zoom',
          sourceName: 'Zoom Cloud · Founder Strategy Vault',
          speaker: 'Chloe & Liam (Bridal Cinematographers, Aspen)',
          clientName: 'Chloe & Liam Films',
          date: '25m ago',
          timestamp: '34:08',
          audioDuration: '52m',
          type: 'Teaching Point',
          quote: "Couples don't care about our camera gear or award badges; they booked us because our ad broke down the exact timeline to prevent family stress on the wedding day.",
          clearance: 'cleared',
          channelOrMeeting: 'Zoom Weekly Coaching Vault',
          speakerVerified: true,
        },
      ];

      if (onAddMoments) {
        onAddMoments(newMinedMoments);
      }

      setSyncCompleteNotification('Synced successfully: +3 fresh moments mined from Fathom, Slack & Zoom');

      setTimeout(() => {
        setIsSyncing(false);
        setSyncStep(0);
      }, 1600);
    }, 3200);
  };

  const filteredMoments = moments.filter((m) => {
    const matchesSource = sourceFilter === 'all' || m.source === sourceFilter;
    const matchesType = typeFilter === 'all' || m.type === typeFilter;
    const matchesSearch =
      search === '' ||
      m.quote.toLowerCase().includes(search.toLowerCase()) ||
      m.speaker.toLowerCase().includes(search.toLowerCase()) ||
      m.clientName.toLowerCase().includes(search.toLowerCase());
    return matchesSource && matchesType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header & Actions */}
      <div className="atelier-page-hero flex flex-col sm:flex-row sm:items-start justify-between gap-5">
        <div>
          <h1 className="atelier-page-title">
            The Moments Ledger
          </h1>
          <p className="atelier-page-subtitle max-w-2xl">
            Every meaningful moment mined from Zoom recordings, live Fathom calls, and Slack win channels. Quotes preserve verbatim audio timestamps, speaker checks, and clearance tags before weekly ranking.
          </p>
        </div>

        <div className="atelier-page-actions flex items-center gap-2.5 shrink-0 pt-2">
          {/* Sync Now Trigger */}
          <button
            onClick={handleSyncNow}
            disabled={isSyncing}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 flex items-center gap-2 shadow-wia-btn pressable tracking-wide cursor-pointer ${
              isSyncing
                ? 'bg-[#E3EAFF] text-[#5070FF] border border-[#D1DBFF] cursor-not-allowed'
                : 'bg-gradient-to-r from-[#5070FF] to-[#3B5BDB] text-white hover:shadow-[0_4px_16px_rgba(80,112,255,0.4)]'
            }`}
          >
            <RefreshCw
              strokeWidth={2}
              className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-[#5070FF]' : 'text-white'}`}
            />
            <span>{isSyncing ? 'Syncing Feeds...' : 'Sync Now'}</span>
          </button>

          <button
            onClick={onOpenFlagModal}
            className="px-4 py-2 bg-white text-[#221E17] hover:bg-[#FAF9F7] border border-[#E0DFE2] rounded-xl text-xs font-semibold transition-colors flex items-center gap-2 shadow-2xs pressable tracking-wide cursor-pointer"
          >
            <Plus strokeWidth={2} className="w-3.5 h-3.5 text-[#5070FF]" />
            <span>Record Moment</span>
          </button>
        </div>
      </div>

      {/* Live Sync Progress Drawer / Banner */}
      {isSyncing && (
        <div className="p-4 sm:p-5 bg-[#0B1124] text-white rounded-2xl border border-white/[0.12] shadow-[0_12px_32px_rgba(0,0,0,0.3)] space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#5070FF] opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#5070FF]"></span>
              </span>
              <span className="text-xs font-semibold tracking-wide text-white">
                Live Source Ingestion in Progress
              </span>
            </div>
            <span className="text-[11px] font-mono text-[#8DA1FD]">
              Step {syncStep} of 4
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 text-xs">
            <div
              className={`p-2.5 rounded-lg border transition-all ${
                syncStep >= 1
                  ? 'bg-white/[0.08] border-[#5070FF] text-white'
                  : 'bg-white/[0.02] border-white/[0.05] text-slate-500'
              }`}
            >
              <div className="font-semibold flex items-center gap-1.5">
                {syncStep > 1 ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Radio className="w-3.5 h-3.5 text-[#5070FF] animate-pulse" />}
                1. Connect Feeds
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">Fathom, Zoom & Slack</div>
            </div>

            <div
              className={`p-2.5 rounded-lg border transition-all ${
                syncStep >= 2
                  ? 'bg-white/[0.08] border-[#5070FF] text-white'
                  : 'bg-white/[0.02] border-white/[0.05] text-slate-500'
              }`}
            >
              <div className="font-semibold flex items-center gap-1.5">
                {syncStep > 2 ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : syncStep === 2 ? <RefreshCw className="w-3.5 h-3.5 text-[#5070FF] animate-spin" /> : null}
                2. Transcribing Audio
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">Speech-to-text parsing</div>
            </div>

            <div
              className={`p-2.5 rounded-lg border transition-all ${
                syncStep >= 3
                  ? 'bg-white/[0.08] border-[#5070FF] text-white'
                  : 'bg-white/[0.02] border-white/[0.05] text-slate-500'
              }`}
            >
              <div className="font-semibold flex items-center gap-1.5">
                {syncStep > 3 ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : syncStep === 3 ? <Volume2 className="w-3.5 h-3.5 text-[#C39878] animate-bounce" /> : null}
                3. Mining Quotes
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">Verbatim soundbites</div>
            </div>

            <div
              className={`p-2.5 rounded-lg border transition-all ${
                syncStep >= 4
                  ? 'bg-emerald-950/40 border-emerald-500/50 text-white'
                  : 'bg-white/[0.02] border-white/[0.05] text-slate-500'
              }`}
            >
              <div className="font-semibold flex items-center gap-1.5 text-emerald-300">
                <Check className="w-3.5 h-3.5" />
                4. Clearance Check
              </div>
              <div className="text-[10px] text-emerald-400/80 mt-0.5">+3 Moments Ready</div>
            </div>
          </div>
        </div>
      )}

      {/* Sync Complete Toast */}
      {syncCompleteNotification && !isSyncing && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-xl text-xs flex items-center justify-between animate-in fade-in duration-200">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-medium">{syncCompleteNotification}</span>
          </div>
          <button
            onClick={() => setSyncCompleteNotification(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold px-1.5"
          >
            ✕
          </button>
        </div>
      )}

      {/* Filter & Search Bar - Concentric Radii */}
      <div className="bg-white p-4 rounded-xl border border-[#E0DFE2] shadow-saas-card flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Source filters */}
          <div className="flex items-center gap-1 bg-[#FAF9F7] p-1 rounded-lg border border-[#E0DFE2] text-xs">
            <button
              onClick={() => setSourceFilter('all')}
              className={`px-3 py-1 rounded-md font-medium transition-all duration-150 pressable cursor-pointer ${
                sourceFilter === 'all'
                  ? 'bg-white text-[#5070FF] shadow-2xs font-semibold'
                  : 'text-[#4B4137] hover:text-[#221E17]'
              }`}
            >
              All Sources ({moments.length})
            </button>
            <button
              onClick={() => setSourceFilter('fathom')}
              className={`px-3 py-1 rounded-md font-medium transition-all duration-150 pressable cursor-pointer ${
                sourceFilter === 'fathom'
                  ? 'bg-white text-[#5070FF] shadow-2xs font-semibold'
                  : 'text-[#4B4137] hover:text-[#221E17]'
              }`}
            >
              Fathom Calls
            </button>
            <button
              onClick={() => setSourceFilter('zoom')}
              className={`px-3 py-1 rounded-md font-medium transition-all duration-150 pressable cursor-pointer ${
                sourceFilter === 'zoom'
                  ? 'bg-white text-[#5070FF] shadow-2xs font-semibold'
                  : 'text-[#4B4137] hover:text-[#221E17]'
              }`}
            >
              Zoom Backfill
            </button>
            <button
              onClick={() => setSourceFilter('slack')}
              className={`px-3 py-1 rounded-md font-medium transition-all duration-150 pressable cursor-pointer ${
                sourceFilter === 'slack'
                  ? 'bg-white text-[#5070FF] shadow-2xs font-semibold'
                  : 'text-[#4B4137] hover:text-[#221E17]'
              }`}
            >
              Slack Wins
            </button>
          </div>

          {/* Type filter */}
          <ThemedSelect aria-label="Filter by moment type"
            value={typeFilter}
            onChange={setTypeFilter}
            className="text-xs bg-[#FAF9F7] border border-[#E0DFE2] rounded-lg px-2.5 py-1.5 text-[#4B4137] focus:outline-none focus:ring-1 focus:ring-[#5070FF] cursor-pointer"
          >
            <option value="all">All Types</option>
            <option value="Result">Results & Wins</option>
            <option value="Soundbite">Soundbites</option>
            <option value="Teaching Point">Teaching Points</option>
            <option value="Question / Struggle">Objections & Struggles</option>
          </ThemedSelect>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <Search
            strokeWidth={1.5}
            className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#87725F]"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search transcripts..."
            className="w-full bg-[#FAF9F7] pl-8 pr-3 py-1.5 rounded-lg border border-[#E0DFE2] text-xs text-[#221E17] placeholder-[#87725F] focus:outline-none focus:ring-1 focus:ring-[#5070FF]"
          />
        </div>
      </div>

      {/* Moments List */}
      <div className="space-y-3">
        {filteredMoments.map((moment) => (
          <div
            key={moment.id}
            className="bg-white p-5 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-3 hover:border-[#5070FF]/40 transition-colors"
          >
            {/* Top row: Source, Speaker, Timestamp, Clearance */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-[#221E17] flex items-center gap-1.5">
                  <Layers strokeWidth={1.5} className="w-3.5 h-3.5 text-[#5070FF]" />
                  {moment.speaker}
                </span>
                <span className="text-[#87725F]">·</span>
                <span className="text-[#87725F]">{moment.clientName}</span>
                <span className="text-[#87725F]">·</span>
                <span className="font-mono text-[11px] text-[#5070FF] bg-[#EFF3FF] px-2 py-0.5 rounded-md border border-[#D1DBFF]">
                  {moment.sourceName}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="font-mono text-[11px] text-[#87725F] flex items-center gap-1">
                  <Clock strokeWidth={1.5} className="w-3 h-3" />
                  {moment.timestamp}
                </span>

                {/* Clearance Tag */}
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded-full flex items-center gap-1 ${
                    moment.clearance === 'cleared'
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : moment.clearance === 'needs_consent'
                      ? 'bg-amber-50 text-amber-800 border border-amber-200'
                      : 'bg-zinc-100 text-zinc-700 border border-zinc-200'
                  }`}
                >
                  <ShieldCheck strokeWidth={1.5} className="w-3 h-3" />
                  {moment.clearance === 'cleared'
                    ? 'Cleared for Public'
                    : moment.clearance === 'needs_consent'
                    ? 'Consent Needed'
                    : 'Anonymised'}
                </span>
              </div>
            </div>

            {/* Verbatim Quote */}
            <div className="bg-[#FAF9F7] p-4 rounded-xl border border-[#E0DFE2]">
              <p className="font-editorial text-base text-[#221E17] italic leading-relaxed">
                "{moment.quote}"
              </p>
            </div>

            {/* Footer: Metadata & Action to promote to Content Idea */}
            <div className="flex items-center justify-between pt-1 text-xs">
              <div className="flex items-center gap-2 text-[#87725F]">
                <span className="bg-[#FAF9F7] px-2.5 py-1 rounded-md border border-[#E0DFE2] text-[11px] font-medium text-[#4B4137]">
                  Category: {moment.type}
                </span>
                {moment.speakerVerified && (
                  <span className="flex items-center gap-1 text-[11px] text-emerald-700 font-medium">
                    <CheckCircle2 strokeWidth={1.5} className="w-3.5 h-3.5 text-emerald-600" /> Verified Audio Track
                  </span>
                )}
              </div>

              <button
                onClick={() => onPromoteToIdea(moment)}
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-[#5070FF] bg-[#EFF3FF] hover:bg-[#E3EAFF] border border-[#D1DBFF] transition-colors duration-150 flex items-center gap-1.5 pressable cursor-pointer shadow-2xs"
              >
                <Sparkles strokeWidth={1.5} className="w-3.5 h-3.5 text-[#5070FF]" />
                <span>Promote to Candidate Angle</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
