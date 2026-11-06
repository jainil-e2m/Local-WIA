import React, { useState } from 'react';
import { Search, TrendingUp, HelpCircle, MessageSquare, Database, Sparkles } from 'lucide-react';
import { ContentIdea } from '../types/atelier';
import { AngleResearch } from './AngleEvidence';

interface ResearchViewProps {
  ideas: ContentIdea[];
  onSelectIdea: (idea: ContentIdea) => void;
}

export const ResearchView: React.FC<ResearchViewProps> = ({ ideas, onSelectIdea }) => {
  const [selectedIdeaId, setSelectedIdeaId] = useState<string>(ideas[0]?.id || '');
  const activeIdea = ideas.find((i) => i.id === selectedIdeaId) || ideas[0];

  return (
    <div className="space-y-6">
      <div className="atelier-page-hero">
        <h1 className="atelier-page-title">
          External Research & Internal Corroboration
        </h1>
        <p className="atelier-page-subtitle max-w-2xl">
          Review the evidence and context behind each angle. Source-based proposals distinguish transcript passages, founder guidance, and external framing from measured search signals.
        </p>
      </div>

      {/* Selector pills for ideas */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {ideas.map((idea) => (
          <button
            key={idea.id}
            onClick={() => setSelectedIdeaId(idea.id)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors duration-150 pressable ${
              selectedIdeaId === idea.id
                ? 'bg-[#5070FF] text-white shadow-wia-btn font-semibold'
                : 'bg-white text-[#4B4137] hover:bg-[#FAF9F7] border border-[#E0DFE2]'
            }`}
          >
            {idea.title}
          </button>
        ))}
      </div>

      {activeIdea?.editorialContext ? <div className="rounded-xl border border-[#E0DFE2] bg-white p-6"><AngleResearch idea={activeIdea} /></div> : activeIdea && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main SerpAPI Signals Card */}
          <div className="lg:col-span-2 space-y-5">
            {/* Google Trends & Search Query */}
            <div className="bg-white p-6 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#E0DFE2] pb-4">
                <div>
                  <div className="text-xs font-mono text-[#87725F] uppercase font-semibold">Active Research Query</div>
                  <div className="font-editorial text-xl font-bold text-[#221E17]">
                    "{activeIdea.research.searchQuery}"
                  </div>
                </div>

                <div className="flex items-center gap-2 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200">
                  <TrendingUp strokeWidth={2} className="w-4 h-4 text-emerald-700" />
                  <span className="text-xs font-mono font-bold text-emerald-800 tabular-nums">
                    Trends: {activeIdea.research.googleTrendsScore}/100 ({activeIdea.research.trendDirection})
                  </span>
                </div>
              </div>

              {/* People Also Ask questions */}
              <div className="space-y-3">
                <h4 className="text-xs font-mono uppercase tracking-wider text-[#87725F] flex items-center gap-1.5 font-semibold">
                  <HelpCircle strokeWidth={1.5} className="w-3.5 h-3.5 text-[#5070FF]" />
                  People Also Ask (Hook Inspiration for Whitney):
                </h4>
                <div className="space-y-2">
                  {activeIdea.research.peopleAlsoAsk.map((q, i) => (
                    <div
                      key={i}
                      className="p-3.5 bg-[#FAF9F7] rounded-xl border border-[#E0DFE2] text-xs text-[#221E17] flex items-start gap-2.5"
                    >
                      <span className="font-mono font-bold text-[#5070FF] tabular-nums">Q{i + 1}</span>
                      <span>{q}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Autocomplete query variations */}
              <div className="space-y-2 pt-2">
                <h4 className="text-xs font-mono uppercase tracking-wider text-[#87725F] font-semibold">
                  Google Autocomplete Queries:
                </h4>
                <div className="flex flex-wrap gap-2">
                  {activeIdea.research.autocomplete.map((query, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 bg-[#FAF9F7] border border-[#E0DFE2] rounded-lg text-xs font-mono text-[#4B4137]"
                    >
                      {query}
                    </span>
                  ))}
                </div>
              </div>

              {/* Reddit / Forum mentions */}
              {activeIdea.research.forumDiscussions.length > 0 && (
                <div className="space-y-2 pt-2">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-[#87725F] flex items-center gap-1.5 font-semibold">
                    <MessageSquare strokeWidth={1.5} className="w-3.5 h-3.5 text-[#C39878]" />
                    Real Forum Discussions (Google Forums Engine):
                  </h4>
                  {activeIdea.research.forumDiscussions.map((d, i) => (
                    <div
                      key={i}
                      className="p-3.5 bg-[#FAF9F7] rounded-xl border border-[#E0DFE2] text-xs space-y-1"
                    >
                      <div className="flex justify-between items-center text-[10px] font-mono text-[#87725F]">
                        <span className="font-semibold text-[#5070FF]">{d.source}</span>
                        <span>{d.date}</span>
                      </div>
                      <p className="italic text-[#4B4137]">"{d.snippet}"</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Internal Corroboration & Proof Ledger Matches */}
          <div className="space-y-5">
            <div className="bg-white p-6 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-4">
              <div className="flex items-center gap-2">
                <Database strokeWidth={1.5} className="w-4 h-4 text-[#5070FF]" />
                <h3 className="font-editorial text-lg font-bold text-[#221E17]">
                  Internal Corroboration
                </h3>
              </div>

              <p className="text-xs text-[#4B4137] leading-relaxed">
                Checking whether other clients experienced the same bottleneck or result in the 3-month transcript window.
              </p>

              <div className="space-y-3 pt-2">
                <div className="bg-[#FAF9F7] p-3.5 rounded-xl border border-[#E0DFE2] space-y-1">
                  <div className="flex justify-between items-center text-[10px] font-mono text-[#87725F]">
                    <span>Fathom Call #38</span>
                    <span className="text-emerald-700 font-semibold">Matched</span>
                  </div>
                  <div className="text-xs font-semibold text-[#221E17]">
                    Elena Rostova Studios
                  </div>
                  <p className="text-xs text-[#4B4137] italic">
                    "Cut organic posting by 80% to focus on venue referrals and paid ads."
                  </p>
                </div>

                <div className="bg-[#FAF9F7] p-3.5 rounded-xl border border-[#E0DFE2] space-y-1">
                  <div className="flex justify-between items-center text-[10px] font-mono text-[#87725F]">
                    <span>Slack #social-proof</span>
                    <span className="text-emerald-700 font-semibold">Matched</span>
                  </div>
                  <div className="text-xs font-semibold text-[#221E17]">
                    Aethel Floral Design
                  </div>
                  <p className="text-xs text-[#4B4137] italic">
                    "Booked $84k quarter without single viral reel."
                  </p>
                </div>
              </div>

              <div className="pt-3 border-t border-[#E0DFE2]">
                <button
                  onClick={() => onSelectIdea(activeIdea)}
                  className="w-full py-2 bg-[#EFF3FF] hover:bg-[#E3EAFF] border border-[#D1DBFF] text-xs font-semibold text-[#5070FF] rounded-xl transition-colors flex items-center justify-center gap-1.5 pressable"
                >
                  <Sparkles strokeWidth={1.5} className="w-3.5 h-3.5" />
                  Open Strategic Brief for this Idea →
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
