import React from 'react';
import { ArrowRight } from 'lucide-react';
import { ContentIdea } from '../types/atelier';
import { EditorialCardVisual } from './EditorialCardVisual';

interface IdeaCardProps {
  idea: ContentIdea;
  onSelect: (idea: ContentIdea) => void;
}

export const IdeaCard: React.FC<IdeaCardProps> = ({ idea, onSelect }) => {
  const getBadgeStyle = (badge: string) => {
    switch (badge) {
      case 'Client Call':
        return {
          dotColor: 'bg-[#5070FF]',
          textColor: 'text-[#5070FF]',
          bgColor: 'bg-[#EFF3FF]',
          borderColor: 'border-[#D1DBFF]',
        };
      case 'Industry Trend':
        return {
          dotColor: 'bg-[#C39878]',
          textColor: 'text-[#7D573B]',
          bgColor: 'bg-[#FDF8F4]',
          borderColor: 'border-[#EBDCD0]',
        };
      case 'Client Story':
        return {
          dotColor: 'bg-[#4B4137]',
          textColor: 'text-[#4B4137]',
          bgColor: 'bg-[#F5F3F0]',
          borderColor: 'border-[#E0DFE2]',
        };
      default:
        return {
          dotColor: 'bg-[#221E17]',
          textColor: 'text-[#221E17]',
          bgColor: 'bg-[#FAF9F7]',
          borderColor: 'border-[#E0DFE2]',
        };
    }
  };

  const badgeStyle = getBadgeStyle(idea.badge);

  const getGateLabel = (gate: string) => {
    switch (gate) {
      case 'gate1_angle':
        return 'Gate 1 · Angle';
      case 'gate2_brief':
        return 'Gate 2 · Brief';
      case 'gate3_pack':
        return 'Gate 3 · Pack Ready';
      case 'approved_for_giselle':
        return 'Handed to Giselle';
      default:
        return 'Gate 1';
    }
  };

  return (
    <article
      onClick={() => onSelect(idea)}
      className="group bg-white rounded-2xl overflow-hidden border border-[#E0DFE2] shadow-saas-card transition-all duration-200 flex flex-col cursor-pointer pressable hover:-translate-y-0.5"
    >
      {/* Visual Header with 1px Image Outline */}
      <div className="relative">
        <EditorialCardVisual type={idea.badge} title={idea.title} />

        {/* Gate status badge top right */}
        <div className="absolute top-3.5 right-3.5 bg-black/60 backdrop-blur-md text-white/95 text-[10px] font-mono font-medium px-2.5 py-0.5 rounded-full border border-white/20 shadow-2xs">
          {getGateLabel(idea.gate)}
        </div>
      </div>

      {/* Card Content Area - Concentric Inner Padding */}
      <div className="p-5 flex-1 flex flex-col justify-between space-y-4 bg-white">
        <div className="space-y-2.5">
          {/* Badge & Metadata row */}
          <div className="flex items-center justify-between">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${badgeStyle.bgColor} ${badgeStyle.textColor} ${badgeStyle.borderColor}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${badgeStyle.dotColor}`} />
              {idea.badge}
            </span>
            <span className="text-[11px] font-mono text-[#87725F] tabular-nums font-medium">
              {idea.scoreBasis === 'editorial' ? 'Editorial' : 'Score'} {idea.score}/100
            </span>
          </div>

          {/* Title with balanced line wrap */}
          <h3 className="font-editorial text-xl sm:text-2xl font-bold text-[#221E17] tracking-tight group-hover:text-[#5070FF] transition-colors duration-150 line-clamp-2 leading-tight">
            {idea.title}
          </h3>

          {/* Clean Quote Preview */}
          <p className="text-xs text-[#4B4137]/80 line-clamp-2 italic leading-relaxed">
            "{idea.primaryQuote}"
          </p>
        </div>

        {/* Bottom row matching user screenshot */}
        <div className="pt-3 border-t border-[#E0DFE2]/70 flex items-center justify-between">
          <span className="text-xs text-[#87725F] font-medium tracking-wide">
            {idea.daysAgo}
          </span>

          {/* Circular arrow button with optical nudge */}
          <div
            aria-label={`Open ${idea.title}`}
            className="w-8 h-8 rounded-full bg-[#FAF9F7] group-hover:bg-[#5070FF] text-[#4B4137] group-hover:text-white flex items-center justify-center transition-colors duration-150 border border-[#E0DFE2] group-hover:border-[#5070FF] shadow-2xs"
          >
            <ArrowRight strokeWidth={2} className="w-3.5 h-3.5 transition-transform duration-150 group-hover:translate-x-0.5" />
          </div>
        </div>
      </div>
    </article>
  );
};
