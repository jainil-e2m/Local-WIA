import React from 'react';
import { Layers, Mail, Video, Sparkles, ChevronDown } from 'lucide-react';
import { ContentIdea } from '../types/atelier';
import { PageHeading } from './PageHeading';
import { PackSchedulePopover } from './PackSchedulePopover';
import { groupPacksByMonth } from '../utils/packMonths';

interface ContentPacksViewProps {
  ideas: ContentIdea[];
  onSelectIdea: (idea: ContentIdea) => void;
  onSchedule?: (id: string, date: string, time: string) => void;
}

export const ContentPacksView: React.FC<ContentPacksViewProps> = ({ ideas, onSelectIdea, onSchedule }) => {
  const packsWithContent = ideas.filter((i) => i.pack !== undefined);
  const months = groupPacksByMonth(packsWithContent);

  return (
    <div className="space-y-6">
      <div className="atelier-page-hero [&_.atelier-page-title]:text-[36px] max-sm:[&_.atelier-page-title]:text-[30px]">
        <PageHeading title="Content Packs & Deliverable Scripts" description="Content suites generated from approved briefs. Each pack contains an email, a carousel, three reel scripts, and captions. Scheduling and the publishing handoff follow generation." />
      </div>

      <div className="space-y-4">
      {months.map((month, index) => <details key={month.key} open={index === 0} className="group/pack-month rounded-2xl border border-[#E6E9F0] bg-white overflow-hidden">
        <summary className="list-none cursor-pointer flex items-center justify-between gap-3 px-5 py-4 [&::-webkit-details-marker]:hidden"><span className="text-[14px] font-semibold text-[#34445F]">{month.label}</span><span className="flex items-center gap-3"><span className="rounded-full bg-[#EFF3FF] px-3 py-1 text-[11px] text-[#5070FF]">{month.ideas.length} {month.ideas.length === 1 ? 'pack' : 'packs'}</span><ChevronDown aria-hidden="true" className="h-4 w-4 text-[#667184] transition-transform group-open/pack-month:rotate-180" /></span></summary>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 border-t border-[#EEF0F4] bg-[#F7F8FB] p-4">
        {month.ideas.map((idea) => {
          if (!idea.pack) return null;

          return (
            <div
              key={idea.id}
              className="bg-white rounded-2xl p-5 border border-[#E6E9F0] shadow-saas-card hover:shadow-md transition-shadow duration-200 flex flex-col justify-between space-y-4"
            >
              <div className="space-y-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-[#5070FF] bg-[#EFF3FF] px-2.5 py-0.5 rounded-md font-semibold border border-[#D1DBFF]">
                    {idea.suggestedCta} Track
                  </span>
                  <span className="text-[11px] shrink-0">
                    {idea.scheduledAt ? (
                      <span className="inline-flex text-emerald-700 font-semibold bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                        Scheduled
                      </span>
                    ) : (
                      <span className="inline-flex text-orange-700 font-semibold bg-orange-50 px-2.5 py-1 rounded-full border border-orange-200">
                        To be scheduled
                      </span>
                    )}
                  </span>
                </div>

                <h3 className="font-editorial text-[22px] font-semibold tracking-[-0.015em] text-[#173354] leading-[1.25]">
                  {idea.title}
                </h3>

                <p className="text-xs text-[#4B4137] leading-relaxed line-clamp-2">
                  {idea.brief.coreInsight}
                </p>

                {/* Deliverables breakdown list */}
                <div className="pt-1 grid grid-cols-3 gap-2 text-[11px]">
                  <div className="px-2.5 py-2 rounded-xl bg-[#F7F8FB] border border-[#E6E9F0] flex items-center gap-2">
                    <Mail strokeWidth={1.5} className="w-3.5 h-3.5 text-[#5070FF]" />
                    <span className="truncate text-[#221E17] font-medium">1 Email</span>
                  </div>
                  <div className="px-2.5 py-2 rounded-xl bg-[#F7F8FB] border border-[#E6E9F0] flex items-center gap-2">
                    <Layers strokeWidth={1.5} className="w-3.5 h-3.5 text-[#C39878]" />
                    <span className="truncate text-[#221E17] font-medium">{idea.pack.carousel.slides.length} Slides</span>
                  </div>
                  <div className="px-2.5 py-2 rounded-xl bg-[#F7F8FB] border border-[#E6E9F0] flex items-center gap-2">
                    <Video strokeWidth={1.5} className="w-3.5 h-3.5 text-[#4B4137]" />
                    <span className="truncate text-[#221E17] font-medium">3 Reels</span>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-[#E6E9F0] flex flex-wrap items-center justify-between gap-3">
                <button
                  onClick={() => onSelectIdea(idea)}
                  className="text-xs font-semibold text-[#5070FF] hover:text-[#405FE6] flex items-center gap-1.5 pressable"
                >
                  <Sparkles strokeWidth={1.5} className="w-3.5 h-3.5" />
                  Inspect & Edit Full Suite →
                </button>

                <PackSchedulePopover idea={idea} onSchedule={onSchedule} />
              </div>
            </div>
          );
        })}
      </div>
      </details>)}
      {!months.length && <p className="rounded-2xl border border-dashed border-[#DCE1EA] p-8 text-center text-[12px] text-[#8B93A3]">No generated content packs yet.</p>}
      </div>
    </div>
  );
};
