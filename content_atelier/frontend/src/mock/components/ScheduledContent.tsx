import React from 'react';
import { CalendarClock } from 'lucide-react';
import { ContentIdea } from '../../types/atelier';
import { scheduleLabel, schedulePack } from '../utils/publishingSchedule';
import { PackSchedulePopover } from './PackSchedulePopover';
import { editorialWeekFor, weekLabel } from '../../utils/editorialWeeks';
import { CalendarEntry } from '../../types/calendar';
import { OCTOBER_DEMO_MONTH } from '../../data/calendarDemo';

interface Props {
  ideas: ContentIdea[];
  onSchedule: (id: string, scheduledAt: string) => void;
  onReview: (idea: ContentIdea, contentOrder?: number) => void;
  demoPosts?: CalendarEntry[];
}

function GenerationWeek({ idea }: { idea?: ContentIdea }) {
  const week = idea?.briefApprovedAt ? editorialWeekFor(idea.briefApprovedAt)
    : idea?.originalEditorialWeek || idea?.editorialWeek || (idea?.createdAt ? editorialWeekFor(idea.createdAt) : undefined);
  return <p className="text-right text-[11px] text-[#8B93A3]" aria-label="Content generation week">{week ? `Generated week: ${weekLabel(week)}` : 'Generation week unavailable'}</p>;
}

function ScheduleCard({ idea, onSchedule, onReview }: { idea: ContentIdea } & Omit<Props, 'ideas'>) {
  return <article data-editorial-idea-id={idea.id} tabIndex={-1} className="rounded-2xl border border-[#E6E9F0] bg-white p-5 space-y-4">
    <div className="flex justify-between gap-3 text-[11px] text-[#8B93A3]"><span>{idea.suggestedCta}</span><span className="rounded-full bg-[#EFF3FF] px-3 py-1 text-[#5070FF]">{idea.scheduledAt ? 'Scheduled' : 'Awaiting scheduling'}</span></div>
    <h3 className="font-editorial text-[23px] text-[#1B2433]">{idea.title}</h3>
    <p className="text-[11px] text-[#8B93A3]">Original week: {weekLabel(idea.editorialWeek!)} · Full content pack</p>
    {idea.scheduledAt && <p className="text-[12px] text-emerald-700 flex items-center gap-2"><CalendarClock className="w-4 h-4" />{scheduleLabel(idea.scheduledAt)}</p>}
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#EEF0F4] pt-3">
      <button type="button" onClick={() => onReview(idea)} className="rounded-full border border-[#E6E9F0] px-4 py-2 text-[12px] text-[#34445F]">Review pack</button>
      <PackSchedulePopover idea={idea} onSchedule={(id, date, time) => {
        const result = schedulePack(idea, date, time);
        onSchedule(id, result.scheduledAt!);
      }} />
    </div>
    <GenerationWeek idea={idea} />
  </article>;
}

export function ScheduledContent({ ideas, demoPosts = [], ...callbacks }: Props) {
  const ready = ideas.filter(idea => idea.pack && idea.publishingApprovedAt);
  return <div className="space-y-8">
    <p className="text-[12px] text-[#8B93A3]">Approved packs stay linked to their original week. Dates sync to the Home calendar. This is a local publishing plan, not automatic posting or a Slack notification.</p>
    {[{ title: 'Awaiting scheduling', items: ready.filter(idea => !idea.scheduledAt) }, { title: 'Scheduled', items: ready.filter(idea => idea.scheduledAt).sort((a, b) => a.scheduledAt!.localeCompare(b.scheduledAt!)) }].map(section => <section key={section.title} aria-label={section.title}>
      <h2 className="font-editorial text-2xl text-[#1B2433] mb-4">{section.title} <span className="text-sm text-[#8B93A3]">({section.items.length + (section.title === 'Scheduled' ? demoPosts.length : 0)})</span></h2>
      {section.title === 'Scheduled' && demoPosts.length > 0 && <div className="mb-5 space-y-4"><p className="text-[12px] text-[#8B93A3]">October {OCTOBER_DEMO_MONTH.year} · {demoPosts.length} mock individual postings · Matches the Home calendar; not evidence of live publication.</p><div className="grid grid-cols-1 xl:grid-cols-2 gap-4">{demoPosts.map(post => {
        const source = ideas.find(idea => idea.id === post.ideaId);
        return <article key={post.id} className="rounded-2xl border border-[#E6E9F0] bg-white p-5 space-y-3"><div className="flex justify-between gap-3 text-[11px]"><span className="text-[#8B93A3]">{post.channel}</span><span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">Scheduled</span></div><h3 className="font-editorial text-[23px] text-[#1B2433]">{post.title}</h3><p className="flex items-center gap-2 text-[12px] text-emerald-700"><CalendarClock className="h-4 w-4" />{post.day} October {OCTOBER_DEMO_MONTH.year} · {post.time}</p>{source && <button type="button" onClick={() => callbacks.onReview(source, post.contentOrder ?? (post.channel === 'Email' ? 1 : post.channel === 'Carousel' ? 2 : 3))} className="rounded-full border border-[#E6E9F0] px-4 py-2 text-[12px] text-[#34445F]">Review linked content →</button>}<GenerationWeek idea={source} /></article>;
      })}</div></div>}
      {section.items.length ? <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">{section.items.map(idea => <ScheduleCard key={idea.id} idea={idea} {...callbacks} />)}</div> : !(section.title === 'Scheduled' && demoPosts.length) && <p className="rounded-2xl border border-dashed border-[#DCE1EA] py-8 text-center text-[12px] text-[#8B93A3]">{section.title === 'Scheduled' ? 'No scheduled content yet.' : 'Approve a generated pack for publishing in Content Packs to bring it here.'}</p>}
    </section>)}
  </div>;
}
