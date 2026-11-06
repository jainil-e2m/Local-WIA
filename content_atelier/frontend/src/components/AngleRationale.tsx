import React from 'react';
import { ContentIdea } from '../types/atelier';
import { contentAngleRationale } from '../utils/angleRationale';
import { MarkdownDocument } from './MarkdownDocument';

export function AngleRationale({ idea }: { idea: ContentIdea }) {
  const rationale = contentAngleRationale(idea);
  // Use the original formatting even when browser storage contains older plain-text points.
  const suppliedFields = new Map(
    [...(idea.suppliedCopy?.angle ?? '').matchAll(/^### (.+)\n([\s\S]*?)(?=^### |$(?![\s\S]))/gm)]
      .map(match => [match[1], match[2].trim()]),
  );
  return <section aria-label="Content angle rationale" className="rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] p-4">
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#A38B61]">Topic & editorial rationale</span>
      {!idea.editorialContext && <span className="text-[10px] text-[#8B93A3]">{rationale.source === 'mock' ? 'Mock rationale' : rationale.source === 'llm' ? 'AI-generated rationale' : 'From existing editorial inputs'}</span>}
    </div>
    <ul className="space-y-2.5 pl-4 text-[12px] leading-relaxed text-[#667184] list-disc marker:text-[#A38B61]">
      {rationale.points.map((point, index) => {
        const text = suppliedFields.get(point.label) ?? point.text;
        const formatted = /\n|\*\*|^- /m.test(text);
        const pillar = point.label === 'Content pillar / type'
          ? /^(ATTRACT|WARM|CONVERT)\s*·\s*([\s\S]*)$/.exec(text)
          : null;
        return <li key={`${point.label}-${index}`}>
          <strong className="font-semibold text-[#34445F]">{point.label}: </strong>
          {pillar ? <>
            <span className="font-semibold text-[#5070FF]">{pillar[1]}</span>
            <span className="block mt-1">{pillar[2]}</span>
          </> : formatted ? <div className="mt-1 [&_article]:space-y-1.5 [&_article]:text-[12px] [&_p]:text-[#667184] [&_ul]:text-[#667184]">
            <MarkdownDocument markdown={text} />
          </div> : text}
        </li>;
      })}
    </ul>
  </section>;
}
