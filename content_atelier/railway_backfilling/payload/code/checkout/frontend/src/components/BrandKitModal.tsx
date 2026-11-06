import React from 'react';
import { X, ShieldCheck, Sparkles, BookOpen } from 'lucide-react';
import { BRAND_KIT_REFERENCE } from '../data/mockData';
import { useModalBehavior } from './useModalBehavior';

interface BrandKitModalProps {
  onClose: () => void;
}

export const BrandKitModal: React.FC<BrandKitModalProps> = ({ onClose }) => {
  const modalRef = useModalBehavior(onClose);
  return (
    <div data-lenis-prevent className="atelier-modal-overlay fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-label="Brand Kit & Founder Voice"
        tabIndex={-1}
        className="atelier-modal bg-[#FAF9F7] w-full max-w-3xl max-h-[88dvh] rounded-2xl border border-[#E0DFE2] shadow-saas-dropdown flex flex-col overflow-hidden text-[#221E17]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div className="px-6 py-4 border-b border-[#E0DFE2] bg-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-editorial text-2xl font-bold text-[#221E17]">
              WIA Brand Kit & Founder Voice
            </span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close Brand Kit"
            className="w-8 h-8 rounded-lg hover:bg-[#FAF9F7] border border-transparent hover:border-[#E0DFE2] flex items-center justify-center text-[#4B4137] transition-colors pressable"
          >
            <X strokeWidth={1.5} className="w-4 h-4" />
          </button>
        </div>

        {/* Content body */}
        <div data-lenis-prevent className="atelier-modal-scroll min-h-0 flex-1 p-6 overflow-y-auto space-y-6 text-xs">
          {/* Section 1: Founder Voice Doc */}
          <div className="bg-white p-5 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#221E17]">
              <Sparkles strokeWidth={1.5} className="w-4 h-4 text-[#5070FF]" />
              Founder Voice Document (Whitney’s Cadence)
            </div>
            <p className="text-[#4B4137] leading-relaxed">
              <strong>Tone:</strong> {BRAND_KIT_REFERENCE.founderVoice.tone}
            </p>
            <div className="bg-[#FAF9F7] p-3.5 rounded-xl border border-[#E0DFE2] space-y-1">
              <span className="font-semibold text-[#221E17] block">Perspective Rule:</span>
              <p className="text-[#4B4137]">
                {BRAND_KIT_REFERENCE.founderVoice.personGuidelines}
              </p>
            </div>
            <div className="bg-[#EFF3FF] p-3.5 rounded-xl border border-[#D1DBFF] space-y-1">
              <span className="font-semibold text-[#5070FF] block">Anti-AI Critic Guidelines:</span>
              <p className="text-[#221E17]">
                {BRAND_KIT_REFERENCE.founderVoice.antiAiCritic}
              </p>
            </div>
          </div>

          {/* Section 2: Strategy Pillars */}
          <div className="bg-white p-5 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#221E17]">
              <BookOpen strokeWidth={1.5} className="w-4 h-4 text-[#C39878]" />
              Content Strategy Pillars (WIA Consultant Blueprint)
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {BRAND_KIT_REFERENCE.strategyPillars.map((p, idx) => (
                <div
                  key={idx}
                  className="p-3.5 bg-[#FAF9F7] rounded-xl border border-[#E0DFE2] space-y-1"
                >
                  <span className="font-semibold text-[#221E17] block">{p.pillar}</span>
                  <p className="text-[#4B4137]">{p.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Section 3: Golden Exemplar */}
          <div className="bg-white p-5 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#221E17]">
              <ShieldCheck strokeWidth={1.5} className="w-4 h-4 text-[#5070FF]" />
              Golden Exemplar Calibration
            </div>
            <div className="bg-[#FAF9F7] p-3.5 rounded-xl border border-[#E0DFE2] space-y-1">
              <span className="font-semibold text-[#221E17]">
                {BRAND_KIT_REFERENCE.goldenExemplar.title}
              </span>
              <p className="text-[#4B4137]">
                Source: {BRAND_KIT_REFERENCE.goldenExemplar.sourceCall}
              </p>
              <p className="text-emerald-800 font-medium">
                Benchmark: {BRAND_KIT_REFERENCE.goldenExemplar.performance}
              </p>
            </div>
          </div>
        </div>

        <div className="px-6 py-3.5 bg-white border-t border-[#E0DFE2] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-[#5070FF] text-white text-xs font-semibold hover:bg-[#405FE6] transition-colors shadow-wia-btn pressable tracking-wide"
          >
            Close Brand Kit
          </button>
        </div>
      </div>
    </div>
  );
};
