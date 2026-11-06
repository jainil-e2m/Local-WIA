import React from 'react';
import { CalendarClock } from 'lucide-react';
import { ContentIdea } from '../types/atelier';
import { contentScheduleFor, scheduleLabel } from '../utils/publishingSchedule';
import { DraftContentPiece, selectDraftContents } from '../stages/ideaStages';
import { PackSchedulePopover } from './PackSchedulePopover';
import { editorialWeekFor, weekLabel } from '../utils/editorialWeeks';
import { CalendarEntry } from '../types/calendar';
import { OCTOBER_DEMO_MONTH } from '../data/calendarDemo';

interface Props {
  ideas: ContentIdea[];
  onSchedule: (id: string, date: string, time: string, contentOrder?: number) => void;
  onReview: (idea: ContentIdea, contentOrder?: number) => void;
  demoPosts?: CalendarEntry[];
}

function GenerationWeek({ idea }: { idea?: ContentIdea }) {
  const week = idea?.briefApprovedAt ? editorialWeekFor(idea.briefApprovedAt)
    : idea?.originalEditorialWeek || idea?.editorialWeek || (idea?.createdAt ? editorialWeekFor(idea.createdAt) : undefined);
  return <p className="text-right text-[11px] text-[#8B93A3]" aria-label="Content generation week">{week ? `Generated week: ${weekLabel(week)}` : 'Generation week unavailable'}</p>;
}

function ScheduleCard({ idea, piece, onSchedule, onReview }: { idea: ContentIdea; piece: DraftContentPiece } & Omit<Props, 'ideas'>) {
  const date = contentScheduleFor(idea, piece.order);
  return <article className="rounded-2xl border border-[#E6E9F0] bg-white p-5 space-y-4">
    <div className="flex justify-between gap-3 text-[11px] text-[#8B93A3]"><span>{piece.meta}</span><span className="rounded-full bg-[#EFF3FF] px-3 py-1 text-[#5070FF]">{date ? 'Scheduled' : 'Awaiting scheduling'}</span></div>
    <h3 className="font-editorial text-[23px] text-[#1B2433]">{piece.title}</h3>
    <p className="text-[11px] text-[#8B93A3]">Original week: {weekLabel(idea.editorialWeek!)} · {idea.suggestedCta}</p>
    {date && <p className="text-[12px] text-emerald-700 flex items-center gap-2"><CalendarClock className="w-4 h-4" />{scheduleLabel(date)}</p>}
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#EEF0F4] pt-3">
      <button type="button" onClick={() => onReview(idea, piece.order)} className="rounded-full border border-[#E6E9F0] px-4 py-2 text-[12px] text-[#34445F]">Review content</button>
      <PackSchedulePopover idea={idea} contentOrder={piece.order} onSchedule={onSchedule} />
    </div>
    <GenerationWeek idea={idea} />
  </article>;
}

export function ScheduledContent({ ideas, demoPosts = [], ...callbacks }: Props) {
  const ready = ideas.filter(idea => idea.pack && idea.publishingApprovedAt).flatMap(idea => selectDraftContents(idea.pack).map(piece => ({ idea, piece, date: contentScheduleFor(idea, piece.order) })));
  return <div className="space-y-8">
    <p className="text-[12px] text-[#8B93A3]">Each email, carousel, and reel keeps its own publishing date and source week. Dates sync to the Home calendar. This is a local publishing plan, not automatic posting or a Slack notification.</p>
    {[{ title: 'Awaiting scheduling', items: ready.filter(item => !item.date) }, { title: 'Scheduled', items: ready.filter(item => item.date).sort((a, b) => a.date!.localeCompare(b.date!)) }].map(section => <section key={section.title} aria-label={section.title}>
      <h2 className="font-editorial text-2xl text-[#1B2433] mb-4">{section.title} <span className="text-sm text-[#8B93A3]">({section.items.length + (section.title === 'Scheduled' ? demoPosts.length : 0)})</span></h2>
      {section.title === 'Scheduled' && demoPosts.length > 0 && <div className="mb-5 space-y-4"><p className="text-[12px] text-[#8B93A3]">October {OCTOBER_DEMO_MONTH.year} · {demoPosts.length} mock individual postings · Matches the Home calendar; not evidence of live publication.</p><div className="grid grid-cols-1 xl:grid-cols-2 gap-4">{demoPosts.map(post => {
        const source = ideas.find(idea => idea.id === post.ideaId);
        return <article key={post.id} className="rounded-2xl border border-[#E6E9F0] bg-white p-5 space-y-3"><div className="flex justify-between gap-3 text-[11px]"><span className="text-[#8B93A3]">{post.channel}</span><span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">Scheduled</span></div><h3 className="font-editorial text-[23px] text-[#1B2433]">{post.title}</h3><p className="flex items-center gap-2 text-[12px] text-emerald-700"><CalendarClock className="h-4 w-4" />{post.day} October {OCTOBER_DEMO_MONTH.year} · {post.time}</p>{source && <button type="button" onClick={() => callbacks.onReview(source, post.contentOrder ?? (post.channel === 'Email' ? 1 : post.channel === 'Carousel' ? 2 : 3))} className="rounded-full border border-[#E6E9F0] px-4 py-2 text-[12px] text-[#34445F]">Review linked content →</button>}<GenerationWeek idea={source} /></article>;
      })}</div></div>}
      {section.items.length ? <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">{section.items.map(({ idea, piece }) => <ScheduleCard key={`${idea.id}-${piece.order}`} idea={idea} piece={piece} {...callbacks} />)}</div> : !(section.title === 'Scheduled' && demoPosts.length) && <p className="rounded-2xl border border-dashed border-[#DCE1EA] py-8 text-center text-[12px] text-[#8B93A3]">{section.title === 'Scheduled' ? 'No scheduled content yet.' : 'Approve a generated pack for publishing in Content Packs to bring it here.'}</p>}
    </section>)}
  </div>;
}
