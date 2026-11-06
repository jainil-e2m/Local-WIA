import React from 'react';
import { ContentIdea } from '../types/atelier';

export function AngleEvidence({ idea }: { idea: ContentIdea }) {
  const context = idea.editorialContext;
  if (!context) return null;
  return <div className="space-y-4 text-[12px] leading-relaxed text-[#667184]">
    <p className="rounded-lg bg-[#FFF8E9] p-3 text-[#947021]">Source-based mock proposal · Transcript passages matched. Speaker attribution and permission for public use still require review. Scores are editorial estimates; external demand is unmeasured.</p>
    {context.sources.map((source, index) => <section key={`${source.recordingId}-${source.timestamp}-${index}`} className="border-t border-[#E6E9F0] pt-3">
      <p className="font-semibold text-[#34445F]">{source.role} · {source.meeting}</p>
      <p className="mt-1 text-[11px]">{source.speaker} · {source.timestamp} · {source.recordedAt.slice(0, 10)}</p>
      <blockquote className="mt-2 border-l-2 border-[#D9BE87] pl-3 italic">“{source.quote}”</blockquote>
      <p className="mt-2">{source.interpretation}</p>
      <a href={source.url} target="_blank" rel="noreferrer" className="mt-2 inline-block font-medium text-[#5070FF]">Open recording · {source.timestamp} ↗</a>
    </section>)}
  </div>;
}

export function AngleResearch({ idea }: { idea: ContentIdea }) {
  const context = idea.editorialContext;
  if (!context) return null;
  return <div className="space-y-6 text-[12px] leading-relaxed text-[#667184]">
    <div><h3 className="font-editorial text-2xl font-bold text-[#221E17]">Sources & editorial context</h3><p className="mt-2">{idea.research.note}</p></div>
    <AngleEvidence idea={idea} />
    <section><h4 className="font-semibold text-[#34445F]">Founder documents informing this angle</h4><ul className="mt-2 list-disc space-y-2 pl-4">{context.brandReferences.map((reference, index) => <li key={index}><strong>{reference.title}</strong> · {reference.section}</li>)}</ul></section>
    <section><h4 className="font-semibold text-[#34445F]">External context · separate from client evidence</h4>{context.externalContext.map(source => <div key={source.url} className="mt-3"><a href={source.url} target="_blank" rel="noreferrer" className="font-medium text-[#5070FF]">{source.title} ↗</a><p className="mt-1">{source.summary}</p></div>)}</section>
    <section><h4 className="font-semibold text-[#34445F]">Audience questions to explore · editorial prompts</h4><ul className="mt-2 list-disc space-y-2 pl-4">{idea.research.peopleAlsoAsk.map(question => <li key={question}>{question}</li>)}</ul></section>
  </div>;
}
