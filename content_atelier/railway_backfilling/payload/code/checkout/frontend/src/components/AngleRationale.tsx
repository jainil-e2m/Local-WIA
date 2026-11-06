import React from 'react';
import { ContentIdea } from '../types/atelier';
import { contentAngleRationale } from '../utils/angleRationale';

export function AngleRationale({ idea }: { idea: ContentIdea }) {
  const rationale = contentAngleRationale(idea);
  return <section aria-label="Content angle rationale" className="rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] p-4">
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#A38B61]">Topic & editorial rationale</span>
      <span className="text-[10px] text-[#8B93A3]">{idea.editorialContext ? 'Source-based editorial rationale' : rationale.source === 'mock' ? 'Mock rationale' : rationale.source === 'llm' ? 'AI-generated rationale' : 'From existing editorial inputs'}</span>
    </div>
    <p className="mb-3 text-[13px] font-semibold leading-relaxed text-[#173354]">{rationale.topic}</p>
    {idea.editorialContext && <div className="mb-4 space-y-2 border-b border-[#E6E9F0] pb-3 text-[12px] leading-relaxed text-[#667184]">
      <p className="font-medium text-[#34445F]">{idea.editorialContext.funnelStage} · {idea.editorialContext.pillar}</p>
      <p><strong>For:</strong> {idea.editorialContext.audience}</p>
      <p><strong>Belief shift:</strong> {idea.editorialContext.beliefShift}</p>
    </div>}
    <ul className="space-y-2.5 pl-4 text-[12px] leading-relaxed text-[#667184] list-disc marker:text-[#A38B61]">
      {rationale.points.map((point, index) => <li key={`${point.label}-${index}`}><span className="font-semibold text-[#34445F]">{point.label}: </span>{point.text}</li>)}
    </ul>
  </section>;
}
