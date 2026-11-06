import React from 'react';
import { ContentIdea } from '../types/atelier';
import { briefingOverview, briefingSimilarity } from '../utils/briefingOverview';
import { MarkdownDocument } from './MarkdownDocument';

export function BriefingOverview({ idea }: { idea: ContentIdea }) {
  if (idea.suppliedCopy?.brief) {
    const fields = [...idea.suppliedCopy.brief.matchAll(/^### (.+)\n([\s\S]*?)(?=^### |$(?![\s\S]))/gm)];
    return <section aria-label="Content brief overview" className="rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] p-4">
      <h4 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#A38B61]">Content brief</h4>
      <ul className="space-y-3 pl-4 list-disc marker:text-[#A38B61] text-[12px] leading-relaxed text-[#667184] [&>li+li]:border-t [&>li+li]:border-[#E0DFE2] [&>li+li]:pt-3">
        {fields.map(([, label, body]) => {
          const text = body.trim();
          const stage = label === 'Strategic purpose' ? /^(ATTRACT|WARM|CONVERT)\.\s*([\s\S]*)$/.exec(text) : null;
          // Emphasise narrative and format lead-ins without changing the supplied copy.
          const markdown = (stage ? stage[2] : text).replace(/^(- )([^:\n]+): /gm, '$1**$2:** ');
          return <li key={label}>
            <strong className="font-semibold text-[#34445F]">{label}: </strong>
            {stage && <span className="font-semibold text-[#5070FF]">{stage[1]}</span>}
            <div className="mt-1 [&_article]:space-y-1.5 [&_article]:text-[12px] [&_p]:text-[#667184] [&_ul]:text-[#667184]">
              <MarkdownDocument markdown={markdown} />
            </div>
          </li>;
        })}
      </ul>
    </section>;
  }
  const review = briefingSimilarity(idea);
  const direction = idea.brief.productionBrief;
  return <div className="space-y-4">
    {direction && <section aria-label="Brief strategic assignment" className="rounded-xl border border-[#E6E9F0] bg-white p-4 text-[12px] leading-relaxed text-[#667184]">
      <div className="mb-3 flex flex-wrap justify-between gap-2"><h4 className="font-semibold text-[#34445F]">Editorial & production brief</h4><span className="text-[10px] text-[#8B93A3]">Prepared {direction.preparedAt.slice(0, 10)}</span></div>
      <p className="font-medium text-[#34445F]">{idea.editorialContext?.funnelStage} · {idea.editorialContext?.pillar}</p>
      <p className="mt-2"><strong>For:</strong> {idea.editorialContext?.audience ?? idea.client}</p>
      <p className="mt-2"><strong>Reader takeaway:</strong> {direction.readerPromise}</p>
      <p className="mt-2"><strong>Belief shift:</strong> {idea.editorialContext?.beliefShift ?? idea.brief.coreInsight}</p>
      <p className="mt-3 border-t border-[#EEF0F4] pt-3 text-[11px]">Full brief includes the narrative, evidence boundaries, email outline, eight-slide plan, reel treatments, CTA, assets, and review checklist.</p>
    </section>}
    <section aria-label="Planned content overview" className="rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] p-4">
      <h4 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#A38B61]">What we will generate</h4>
      <ul className="space-y-3 text-[12px] leading-relaxed text-[#667184]">{briefingOverview(idea).map(piece => <li key={piece.label}><p className="font-semibold text-[#34445F]">{piece.label} · {piece.purpose}</p><p className="mt-1">{piece.gist}</p></li>)}</ul>
    </section>
    <section aria-label="Past four months similarity review" className="rounded-xl border border-[#E6E9F0] bg-white p-4 text-[12px] leading-relaxed text-[#667184]">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2"><h4 className="font-semibold text-[#34445F]">Past four months · Similarity review</h4><span className={`rounded-full px-2.5 py-1 text-[10px] ${review.status === 'No similar content found' ? 'bg-emerald-50 text-emerald-700' : 'bg-[#FFF8E9] text-[#947021]'}`}>{review.status}</span></div>
      <p>{review.summary}</p>
      {review.matches.map((match, index) => <div key={`${match.title}-${index}`} className="mt-3 border-t border-[#EEF0F4] pt-3"><p className="font-semibold text-[#34445F]">{match.title} · {match.publishedAt.slice(0, 10)}</p><p className="mt-1">Overlap: {match.similarity}</p><p className="mt-2 font-medium text-[#34445F]">How this version differs</p>{match.modifications.length ? <ul className="mt-1 list-disc space-y-1 pl-4">{match.modifications.map((change, i) => <li key={i}>{change}</li>)}</ul> : <p className="mt-1 text-[#947021]">Changes have not been documented yet. Define a distinct angle before approval.</p>}</div>)}
    </section>
  </div>;
}
