import React, { useState } from 'react';
import { ThemedSelect } from './ThemedSelect';
import { X, Sparkles } from 'lucide-react';
import { SourceType } from '../types/atelier';
import { useModalBehavior } from './useModalBehavior';

interface FlagIdeaModalProps {
  atCapacity?: boolean;
  onClose: () => void;
  onSubmit: (data: {
    title: string;
    quote: string;
    source: SourceType;
    client: string;
    suggestedCta: 'Elevate' | 'Accelerators' | 'LeadLock';
  }) => void;
}

export const FlagIdeaModal: React.FC<FlagIdeaModalProps> = ({ onClose, onSubmit, atCapacity = false }) => {
  const modalRef = useModalBehavior(onClose);
  const [title, setTitle] = useState('');
  const [quote, setQuote] = useState('');
  const [source, setSource] = useState<SourceType>('fathom');
  const [client, setClient] = useState('');
  const [suggestedCta, setSuggestedCta] = useState<'Elevate' | 'Accelerators' | 'LeadLock'>('Elevate');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || atCapacity) return;

    onSubmit({
      title,
      quote: quote || title,
      source,
      client: client || 'Private Advisory Client',
      suggestedCta,
    });
    onClose();
  };

  return (
    <div data-lenis-prevent className="atelier-modal-overlay fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-label="Add content angle"
        tabIndex={-1}
        className="atelier-modal bg-[#FAF9F7] w-full max-w-lg max-h-[92dvh] flex flex-col rounded-2xl border border-[#E0DFE2] shadow-saas-dropdown overflow-hidden text-[#221E17]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-[#E0DFE2] bg-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles strokeWidth={1.5} className="w-4 h-4 text-[#5070FF]" />
            <h3 className="font-editorial text-xl font-bold text-[#221E17]">
              Add a Content Angle
            </h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close Add Angle"
            className="w-8 h-8 rounded-lg hover:bg-[#FAF9F7] border border-transparent hover:border-[#E0DFE2] flex items-center justify-center text-[#4B4137] transition-colors pressable"
          >
            <X strokeWidth={1.5} className="w-4 h-4" />
          </button>
        </div>

        <form data-lenis-prevent onSubmit={handleSubmit} className="atelier-modal-scroll min-h-0 flex-1 overflow-y-auto p-6 space-y-4 text-xs">
          {atCapacity && <p role="status" className="rounded-xl bg-[#FFF8E9] p-3 text-[#947021]">This week has reached its four-concept limit across angles, briefs, and content packs. Approving an item advances it without freeing a new slot.</p>}
          <p className="text-[#4B4137] leading-relaxed">
            Just like Whitney tagging Giselle in Slack: "I had a client call that sparked an idea... taking that and running with it."
          </p>

          <div className="space-y-1">
            <label className="font-semibold text-[#221E17] block">Idea Angle / Working Title *</label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Why Weekend Welcome Parties Are Out-Earning Saturdays"
              className="w-full p-2.5 bg-white border border-[#E0DFE2] rounded-xl text-xs text-[#221E17] focus:outline-none focus:ring-2 focus:ring-[#5070FF]/25 focus:border-[#5070FF]"
            />
          </div>

          <div className="space-y-1">
            <label className="font-semibold text-[#221E17] block">Verbatim Quote or Moment Snippet</label>
            <textarea
              rows={3}
              value={quote}
              onChange={(e) => setQuote(e.target.value)}
              placeholder="Paste the raw line from the client call or Slack screenshot..."
              className="w-full p-2.5 bg-white border border-[#E0DFE2] rounded-xl text-xs text-[#221E17] focus:outline-none focus:ring-2 focus:ring-[#5070FF]/25 focus:border-[#5070FF]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="font-semibold text-[#221E17] block">Capture Source</label>
              <ThemedSelect aria-label="Capture source"
                value={source}
                onChange={(value) => setSource(value as SourceType)}
                className="w-full p-2.5 bg-white border border-[#E0DFE2] rounded-xl text-xs text-[#221E17] focus:outline-none"
              >
                <option value="fathom">Fathom (Client Call)</option>
                <option value="slack">Slack (#social-proof)</option>
                <option value="zoom">Zoom (Vault Masterclass)</option>
                <option value="manual">Manual Note / Whitney Thought</option>
              </ThemedSelect>
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-[#221E17] block">Target Offer CTA</label>
              <ThemedSelect aria-label="Target offer CTA"
                value={suggestedCta}
                onChange={(value) =>
                  setSuggestedCta(value as 'Elevate' | 'Accelerators' | 'LeadLock')
                }
                className="w-full p-2.5 bg-white border border-[#E0DFE2] rounded-xl text-xs text-[#221E17] focus:outline-none"
              >
                <option value="Elevate">Elevate (1-on-1 Advisory)</option>
                <option value="Accelerators">Accelerators (Cohort Program)</option>
                <option value="LeadLock">LeadLock (Rapid Conversion)</option>
              </ThemedSelect>
            </div>
          </div>

          <div className="space-y-1">
            <label className="font-semibold text-[#221E17] block">Client / Speaker Reference</label>
            <input
              type="text"
              value={client}
              onChange={(e) => setClient(e.target.value)}
              placeholder="e.g. Sarah Jenkins Events"
              className="w-full p-2.5 bg-white border border-[#E0DFE2] rounded-xl text-xs text-[#221E17] focus:outline-none"
            />
          </div>

          <div className="pt-3 border-t border-[#E0DFE2] flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-xl border border-[#E0DFE2] text-[#4B4137] hover:bg-[#FAF9F7] transition-colors pressable"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={atCapacity}
              className="px-4 py-2 rounded-xl bg-[#5070FF] text-white font-semibold hover:bg-[#405FE6] transition-colors shadow-wia-btn pressable tracking-wide"
            >
              Add to Weekly Digest
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
