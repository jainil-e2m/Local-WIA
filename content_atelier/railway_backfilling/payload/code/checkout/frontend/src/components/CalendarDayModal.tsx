import React, { useId, useState } from 'react';
import { createPortal } from 'react-dom';
import { ArrowUpRight, CalendarDays, Clock3, Layers, Mail, Video, X } from 'lucide-react';
import { CalendarEntry, CalendarFormat } from '../types/calendar';
import { daySchedule } from '../utils/calendarDisplay';
import { useModalBehavior } from './useModalBehavior';

interface Props {
  date: { year: number; month: number; day: number };
  entries: CalendarEntry[];
  onClose: () => void;
  onOpenContent: (entry: CalendarEntry) => void;
}

const formatStyles = {
  Email: { icon: Mail, color: 'text-[#6D60C8]', background: 'bg-[#F2F1FF]' },
  Carousel: { icon: Layers, color: 'text-[#AA8835]', background: 'bg-[#FBF7EF]' },
  Reel: { icon: Video, color: 'text-[#2A958D]', background: 'bg-[#EFF9FC]' },
};

export function CalendarDayModal({ date, entries, onClose, onOpenContent }: Props) {
  const modalRef = useModalBehavior(onClose);
  const titleId = useId();
  const [format, setFormat] = useState<CalendarFormat | 'All'>('All');
  const visible = daySchedule(entries, format);
  const day = new Date(Date.UTC(date.year, date.month, date.day, 12));
  const dateLabel = day.toLocaleDateString('en-US', { timeZone: 'Asia/Calcutta', month: 'long', day: 'numeric', year: 'numeric' });
  const weekday = day.toLocaleDateString('en-US', { timeZone: 'Asia/Calcutta', weekday: 'long' });
  const dialog = <div data-lenis-prevent className="atelier-modal-overlay fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6" onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div ref={modalRef} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} className="atelier-modal flex h-[80dvh] max-h-[92dvh] w-full max-w-3xl flex-col overflow-hidden border border-[#E6E9F0] bg-[#F7F8FB]">
      <div className="bg-white px-6 pt-6 pb-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#B99A43]"><CalendarDays className="h-3.5 w-3.5" />Daily publishing plan</p>
            <h2 id={titleId} className="mt-2 font-editorial text-[30px] leading-tight text-[#173354]">{dateLabel}</h2>
            <p className="mt-2 text-[12px] text-[#8B93A3]">{weekday} · {entries.length} content {entries.length === 1 ? 'item' : 'items'}</p>
          </div>
          <button type="button" aria-label="Close day schedule" onClick={onClose} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[#667184] hover:bg-[#F7F8FB]"><X className="h-4 w-4" /></button>
        </div>
        <div aria-label="Filter day schedule by format" className="mt-5 flex flex-wrap gap-2">
          {(['All', 'Email', 'Carousel', 'Reel'] as const).map(value => <button key={value} type="button" aria-pressed={format === value} onClick={() => setFormat(value)} className={`flex items-center gap-2 rounded-full px-3.5 py-2 text-[11px] font-medium ${format === value ? 'bg-[#5070FF] text-white' : 'border border-[#E6E9F0] bg-white text-[#667184] hover:bg-[#F7F8FB]'}`}>
            {value === 'All' ? 'All content' : value}<span className={format === value ? 'text-white/80' : 'text-[#9AA3B2]'}>{value === 'All' ? entries.length : entries.filter(entry => entry.channel === value).length}</span>
          </button>)}
        </div>
      </div>
      <div data-lenis-prevent className="atelier-modal-scroll min-h-0 flex-1 overflow-y-auto [scrollbar-gutter:stable] px-6 py-5">
        <p className="mb-4 text-[11px] text-[#8B93A3]">{visible.length} {visible.length === 1 ? 'item' : 'items'} · Select content to review its linked deliverable.</p>
        {visible.length ? <ol className="space-y-3" aria-label="Daily content list">{visible.map(entry => {
          const style = formatStyles[entry.channel];
          const Icon = style.icon;
          return <li key={entry.id}>
            <button type="button" onClick={() => onOpenContent(entry)} className="group flex w-full items-center gap-4 rounded-2xl border border-[#E6E9F0] bg-white p-4 text-left transition-colors hover:border-[#B9C7FC] hover:bg-[#FCFDFF]">
              <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${style.background} ${style.color}`}><Icon className="h-5 w-5" strokeWidth={1.6} /></span>
              <span className="min-w-0 flex-1">
                <span className="mb-1 flex flex-wrap items-center gap-3 text-[10px] font-medium"><span className={style.color}>{entry.channel}</span><span className="flex items-center gap-1 text-[#8B93A3]"><Clock3 className="h-3 w-3" />{entry.time}</span></span>
                {entry.warning && <span className="block text-xs text-amber-800">{entry.warning}</span>}
                <span className="block font-editorial text-[20px] leading-snug text-[#173354]">{entry.title}</span>
                <span className="mt-2 block text-[11px] font-medium text-[#5070FF]">View content</span>
              </span>
              <ArrowUpRight className="h-4 w-4 shrink-0 text-[#9AA3B2] group-hover:text-[#5070FF]" />
            </button>
          </li>;
        })}</ol> : <div className="flex min-h-48 flex-col items-center justify-center rounded-2xl border border-dashed border-[#DCE1EA] bg-white px-5 text-center"><CalendarDays className="mb-3 h-7 w-7 text-[#B99A43]" /><h3 className="font-editorial text-xl text-[#173354]">No {format === 'All' ? 'content' : format.toLowerCase()} for this day</h3><p className="mt-2 text-[12px] text-[#8B93A3]">{entries.length ? 'Choose another format to see the rest of the schedule.' : 'Content will appear here once it has a publishing date.'}</p></div>}
      </div>
      <div className="flex items-center justify-between gap-4 border-t border-[#E6E9F0] bg-white px-6 py-4"><span className="text-[11px] text-[#8B93A3]">Email · Carousel · Reel</span><button type="button" onClick={onClose} className="rounded-full bg-[#173354] px-5 py-2 text-[12px] font-medium text-white">Done</button></div>
    </div>
  </div>;
  return typeof document === 'undefined' ? dialog : createPortal(dialog, document.body);
}
