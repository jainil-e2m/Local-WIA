import React from 'react';
import { Sparkles, Check, CheckCircle2, Clock } from 'lucide-react';
import { ContentIdea, GateStatus } from '../types/atelier';

interface InboxApprovalsViewProps {
  ideas: ContentIdea[];
  onSelectIdea: (idea: ContentIdea) => void;
  onUpdateGate: (ideaId: string, newGate: GateStatus) => void;
}

export const InboxApprovalsView: React.FC<InboxApprovalsViewProps> = ({
  ideas,
  onSelectIdea,
  onUpdateGate,
}) => {
  const pendingGate1 = ideas.filter((i) => i.gate === 'gate1_angle');
  const pendingGate2 = ideas.filter((i) => i.gate === 'gate2_brief');
  const pendingGate3 = ideas.filter((i) => i.gate === 'gate3_pack');
  const approvedForPosting = ideas.filter((i) => i.gate === 'approved_for_giselle');

  return (
    <div className="space-y-6">
      <div className="atelier-page-hero">
        <h1 className="atelier-page-title">
          Inbox & Gate Checkpoints
        </h1>
        <p className="atelier-page-subtitle max-w-2xl">
          Three calm checkpoints designed for Whitney. Approving an angle triggers AI brief generation; approving a brief generates the complete content pack scripts; final approval queues the pack for scheduled posting.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Gate 1 Column */}
        <div className="bg-white p-5 rounded-2xl border border-[#E0DFE2] shadow-saas-card flex flex-col space-y-4">
          <div className="flex items-center justify-between border-b border-[#E0DFE2] pb-3">
            <div>
              <div className="text-xs font-mono font-bold text-[#5070FF]">GATE 1</div>
              <h3 className="font-editorial text-lg font-bold text-[#221E17]">
                Pick Angle (~2 min)
              </h3>
            </div>
            <span className="text-xs font-mono font-bold bg-[#EFF3FF] text-[#5070FF] px-2 py-0.5 rounded-md border border-[#D1DBFF] tabular-nums">
              {pendingGate1.length}
            </span>
          </div>

          <p className="text-[11px] text-[#4B4137]">
            Confirm the core angle. Approving immediately triggers AI brief generation in the background.
          </p>

          <div className="space-y-3 flex-1 overflow-y-auto">
            {pendingGate1.length === 0 ? (
              <div className="text-center py-8 text-xs text-[#87725F]">
                All angles cleared for this week.
              </div>
            ) : (
              pendingGate1.map((idea) => (
                <div
                  key={idea.id}
                  className="p-4 bg-[#FAF9F7] rounded-xl border border-[#E0DFE2] space-y-2 hover:border-[#5070FF]/40 transition-all text-xs"
                >
                  <div className="flex justify-between items-center text-[10px] font-mono text-[#87725F] tabular-nums">
                    <span>Score {idea.score}/100</span>
                    <span className="font-semibold text-[#5070FF]">{idea.suggestedCta}</span>
                  </div>
                  <h4 className="font-editorial text-base font-bold text-[#221E17] leading-tight">
                    {idea.title}
                  </h4>
                  <p className="italic text-[#4B4137] line-clamp-2 text-[11px]">
                    "{idea.primaryQuote}"
                  </p>
                  <div className="pt-2 flex items-center justify-between border-t border-[#E0DFE2]">
                    <button
                      onClick={() => onUpdateGate(idea.id, 'gate2_brief')}
                      className="px-3 py-1 bg-[#5070FF] text-white rounded-lg font-semibold text-[11px] hover:bg-[#405FE6] shadow-wia-btn pressable cursor-pointer flex items-center gap-1"
                    >
                      <Sparkles className="w-3 h-3" />
                      Approve & Gen Brief
                    </button>
                    <button
                      onClick={() => onSelectIdea(idea)}
                      className="text-[11px] text-[#4B4137] hover:text-[#5070FF] flex items-center gap-1 font-medium pressable cursor-pointer"
                    >
                      Review →
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Gate 2 Column */}
        <div className="bg-white p-5 rounded-2xl border border-[#E0DFE2] shadow-saas-card flex flex-col space-y-4">
          <div className="flex items-center justify-between border-b border-[#E0DFE2] pb-3">
            <div>
              <div className="text-xs font-mono font-bold text-[#C39878]">GATE 2</div>
              <h3 className="font-editorial text-lg font-bold text-[#221E17]">
                Approve Brief (~5 min)
              </h3>
            </div>
            <span className="text-xs font-mono font-bold bg-[#FDF8F4] text-[#7D573B] px-2 py-0.5 rounded-md border border-[#EBDCD0] tabular-nums">
              {pendingGate2.length}
            </span>
          </div>

          <p className="text-[11px] text-[#4B4137]">
            Review message spine & deliverable split. Approving generates the full deliverable scripts.
          </p>

          <div className="space-y-3 flex-1 overflow-y-auto">
            {pendingGate2.length === 0 ? (
              <div className="text-center py-8 text-xs text-[#87725F]">
                No pending briefs awaiting review.
              </div>
            ) : (
              pendingGate2.map((idea) => (
                <div
                  key={idea.id}
                  className="p-4 bg-[#FAF9F7] rounded-xl border border-[#E0DFE2] space-y-2 hover:border-[#C39878]/50 transition-all text-xs"
                >
                  <div className="flex justify-between items-center text-[10px] font-mono text-[#87725F] tabular-nums">
                    <span>{idea.research.googleTrendsScore === null ? 'Demand not measured' : `Trends: ${idea.research.googleTrendsScore}/100`}</span>
                    <span className="text-[#5070FF] font-semibold">{idea.suggestedCta}</span>
                  </div>
                  <h4 className="font-editorial text-base font-bold text-[#221E17] leading-tight">
                    {idea.title}
                  </h4>
                  <p className="text-[#4B4137] line-clamp-2 text-[11px]">
                    {idea.brief.coreInsight}
                  </p>
                  <div className="pt-2 flex items-center justify-between border-t border-[#E0DFE2]">
                    <button
                      onClick={() => onUpdateGate(idea.id, 'gate3_pack')}
                      className="px-3 py-1 bg-[#5070FF] text-white rounded-lg font-semibold text-[11px] hover:bg-[#405FE6] shadow-wia-btn pressable cursor-pointer flex items-center gap-1"
                    >
                      <Sparkles className="w-3 h-3" />
                      Approve & Gen Scripts
                    </button>
                    <button
                      onClick={() => onSelectIdea(idea)}
                      className="text-[11px] text-[#4B4137] hover:text-[#5070FF] flex items-center gap-1 font-medium pressable cursor-pointer"
                    >
                      Inspect Brief →
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Gate 3 Column */}
        <div className="bg-white p-5 rounded-2xl border border-[#E0DFE2] shadow-saas-card flex flex-col space-y-4">
          <div className="flex items-center justify-between border-b border-[#E0DFE2] pb-3">
            <div>
              <div className="text-xs font-mono font-bold text-[#4B4137]">GATE 3</div>
              <h3 className="font-editorial text-lg font-bold text-[#221E17]">
                Script Sign-off & Posting
              </h3>
            </div>
            <span className="text-xs font-mono font-bold bg-[#FAF9F7] text-[#4B4137] px-2 py-0.5 rounded-md border border-[#E0DFE2] tabular-nums">
              {pendingGate3.length}
            </span>
          </div>

          <p className="text-[11px] text-[#4B4137]">
            Whitney inspects full scripts (Email, Carousel, 3 Reels, Captions). Approving schedules multi-channel posting.
          </p>

          <div className="space-y-3 flex-1 overflow-y-auto">
            {pendingGate3.length === 0 ? (
              <div className="text-center py-8 text-xs text-[#87725F]">
                {approvedForPosting.length > 0 ? (
                  <div className="space-y-2">
                    <span className="text-emerald-700 font-semibold block">
                      ✓ {approvedForPosting.length} Content Pack(s) Scheduled for Posting!
                    </span>
                    <span className="text-[11px] text-slate-500">
                      Dispatched to Klaviyo, Instagram & TikTok schedulers.
                    </span>
                  </div>
                ) : (
                  'No packs awaiting final sign-off.'
                )}
              </div>
            ) : (
              pendingGate3.map((idea) => (
                <div
                  key={idea.id}
                  className="p-4 bg-[#FAF9F7] rounded-xl border border-[#E0DFE2] space-y-2 hover:border-[#4B4137]/40 transition-all text-xs"
                >
                  <div className="flex justify-between items-center text-[10px] font-mono text-[#87725F]">
                    <span className="text-emerald-700 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Checks Passed
                    </span>
                    <span>1 Email · 8 Slides · 3 Reels</span>
                  </div>
                  <h4 className="font-editorial text-base font-bold text-[#221E17] leading-tight">
                    {idea.title}
                  </h4>
                  <div className="pt-2 flex items-center justify-between border-t border-[#E0DFE2]">
                    <button
                      onClick={() => onUpdateGate(idea.id, 'approved_for_giselle')}
                      className="px-3 py-1 bg-emerald-700 text-white rounded-lg font-semibold text-[11px] hover:bg-emerald-800 pressable cursor-pointer flex items-center gap-1 shadow-2xs"
                    >
                      <Check className="w-3 h-3" />
                      Approve & Post
                    </button>
                    <button
                      onClick={() => onSelectIdea(idea)}
                      className="text-[11px] text-[#4B4137] hover:text-[#5070FF] flex items-center gap-1 font-medium pressable cursor-pointer"
                    >
                      Read Scripts →
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
