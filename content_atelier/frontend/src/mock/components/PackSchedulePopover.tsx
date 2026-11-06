import React, { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { CalendarClock, ChevronLeft, ChevronRight, X } from 'lucide-react';
import { ContentIdea } from '../../types/atelier';
import { publishingZone, scheduleFields } from '../utils/publishingSchedule';
import { changeScheduleMonth, scheduleDateLabel, scheduleMonthDays } from '../../utils/scheduleCalendar';

interface Props {
  idea: ContentIdea;
  onSchedule?: (id: string, date: string, time: string) => void;
}

export function ScheduleDateGrid({ cursor, today, date, onSelect }: { cursor: { year: number; month: number }; today: string; date: string; onSelect: (date: string) => void }) {
  const grid = useRef<HTMLDivElement>(null);
  return <>
    <div className="mt-2 grid grid-cols-7 gap-1">{['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((label, index) => <span key={index} className="py-1 text-center text-[9px] font-semibold text-[#9AA3B2]">{label}</span>)}</div>
    <div ref={grid} role="group" aria-label="Publishing date" className="grid grid-cols-7 gap-1">{scheduleMonthDays(cursor.year, cursor.month).map((cell, index) => cell ? <button key={cell.date} type="button" disabled={cell.date < today} aria-label={scheduleDateLabel(cell.date)} aria-pressed={date === cell.date} onClick={() => onSelect(cell.date)} onKeyDown={event => {
      const delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
      if (delta === undefined) return;
      event.preventDefault();
      grid.current?.querySelector<HTMLButtonElement>(`[data-date-day="${cell.day + delta}"]:not(:disabled)`)?.focus();
    }} data-date-day={cell.day} className={`aspect-square rounded-full text-[12px] font-medium disabled:cursor-not-allowed disabled:opacity-25 ${date === cell.date ? 'bg-[#5070FF] text-white' : cell.date === today ? 'border border-[#D9BE87] text-[#A38B61] hover:bg-[#FBF7EF]' : 'text-[#34445F] hover:bg-[#EFF3FF]'}`}>{cell.day}</button> : <span key={`blank-${index}`} />)}</div>
  </>;
}

export function PackSchedulePopover({ idea, onSchedule }: Props) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<'date' | 'time'>('date');
  const today = scheduleFields(new Date().toISOString()).date;
  const [date, setDate] = useState('');
  const [time, setTime] = useState('09:00');
  const [cursor, setCursor] = useState({ year: Number(today.slice(0, 4)), month: Number(today.slice(5, 7)) - 1 });
  const [error, setError] = useState('');
  const zone = publishingZone(date || today, /^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(time) ? time : '12:00');
  const [position, setPosition] = useState({ left: 0, top: 0, width: 320, maxHeight: 500 });
  const [saved, setSaved] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const id = useId();
  const close = () => { setOpen(false); trigger.current?.focus(); };
  const reveal = () => {
    const fields = idea.scheduledAt ? scheduleFields(idea.scheduledAt) : { date: today, time: '09:00' };
    const start = fields.date >= today ? fields.date : today;
    setDate(idea.scheduledAt && fields.date >= today ? fields.date : '');
    setTime(fields.time);
    setCursor({ year: Number(start.slice(0, 4)), month: Number(start.slice(5, 7)) - 1 });
    setStep('date'); setError(''); setSaved(false); setOpen(true);
  };
  useLayoutEffect(() => {
    if (!open || !trigger.current || !panel.current) return;
    const rect = trigger.current.getBoundingClientRect();
    const width = Math.min(320, window.innerWidth - 24);
    const maxHeight = Math.min(500, window.innerHeight - 24);
    const height = Math.min(panel.current.scrollHeight, maxHeight);
    const above = rect.top - height - 8;
    const below = rect.bottom + 8;
    const top = above >= 12 ? above : below + height <= window.innerHeight - 12 ? below : Math.max(12, Math.min(above, window.innerHeight - height - 12));
    setPosition({ left: Math.max(12, Math.min(rect.right - width, window.innerWidth - width - 12)), top, width, maxHeight });
  }, [open, step, error, cursor]);
  useEffect(() => {
    if (!open) return;
    panel.current?.querySelector<HTMLButtonElement>('button')?.focus();
    const outside = (event: PointerEvent) => { if (!trigger.current?.contains(event.target as Node) && !panel.current?.contains(event.target as Node)) setOpen(false); };
    const scroll = (event: Event) => { if (!panel.current?.contains(event.target as Node)) setOpen(false); };
    const resize = () => setOpen(false);
    document.addEventListener('pointerdown', outside);
    window.addEventListener('scroll', scroll, true);
    window.addEventListener('resize', resize);
    return () => { document.removeEventListener('pointerdown', outside); window.removeEventListener('scroll', scroll, true); window.removeEventListener('resize', resize); };
  }, [open]);
  return <>
    <span className="ml-auto inline-flex shrink-0">
    <button ref={trigger} type="button" disabled={!onSchedule} aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? id : undefined} onClick={() => open ? close() : reveal()} className="flex items-center gap-1.5 rounded-xl border border-[#D1DBFF] bg-[#EFF3FF] px-3.5 py-1.5 text-xs font-medium text-[#5070FF] transition-colors hover:bg-[#E5EBFF] disabled:opacity-50"><CalendarClock className="h-3.5 w-3.5" />{idea.scheduledAt ? 'Reschedule' : 'Schedule'}</button>
    <span role="status" className="sr-only">{saved ? 'Schedule saved' : ''}</span>
    </span>
    {open && typeof document !== 'undefined' && createPortal(<div ref={panel} id={id} role="dialog" aria-label={`Schedule ${idea.title}`} data-lenis-prevent style={position} className="fixed z-[70] overflow-y-auto rounded-2xl border border-[#E6E9F0] bg-white p-4 shadow-[0_12px_40px_rgba(28,49,76,0.18)]" onKeyDown={event => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(); }
      if (event.key === 'Tab') {
        const targets = Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled)') ?? []);
        const first = targets[0], last = targets.at(-1);
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    }}>
      <div className="flex items-center justify-between gap-3"><h3 className="font-editorial text-xl text-[#173354]">{step === 'date' ? 'Choose a date' : 'Choose a time'}</h3><button type="button" aria-label="Close scheduling" onClick={close} className="rounded-full p-1.5 text-[#667184] hover:bg-[#F7F8FB]"><X className="h-4 w-4" /></button></div>
      <p className="mt-1 truncate text-[11px] text-[#8B93A3]">{idea.title}</p>
      {step === 'date' ? <>
        <div className="mt-4 flex items-center justify-between"><button type="button" aria-label="Previous month" disabled={`${cursor.year}-${String(cursor.month + 1).padStart(2, '0')}` <= today.slice(0, 7)} onClick={() => setCursor(changeScheduleMonth(cursor.year, cursor.month, -1))} className="rounded-full p-2 text-[#667184] hover:bg-[#F7F8FB] disabled:opacity-30"><ChevronLeft className="h-4 w-4" /></button><span className="text-[13px] font-semibold text-[#34445F]">{new Date(Date.UTC(cursor.year, cursor.month, 1)).toLocaleDateString('en-IN', { timeZone: 'UTC', month: 'long', year: 'numeric' })}</span><button type="button" aria-label="Next month" onClick={() => setCursor(changeScheduleMonth(cursor.year, cursor.month, 1))} className="rounded-full p-2 text-[#667184] hover:bg-[#F7F8FB]"><ChevronRight className="h-4 w-4" /></button></div>
        <ScheduleDateGrid cursor={cursor} today={today} date={date} onSelect={value => { setDate(value); setError(''); }} />
        <div className="mt-4 flex items-center justify-between gap-3 border-t border-[#EEF0F4] pt-3"><span className="text-[11px] text-[#8B93A3]">{date ? scheduleDateLabel(date) : 'Select a publishing date'}</span><button type="button" disabled={!date} onClick={() => setStep('time')} className="rounded-full bg-[#173354] px-4 py-2 text-[11px] font-medium text-white disabled:opacity-35">Next →</button></div>
      </> : <form onSubmit={event => {
        event.preventDefault();
        try { onSchedule?.(idea.id, date, time); setSaved(true); close(); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save the schedule.'); }
      }}>
        <button type="button" onClick={() => { setStep('date'); setError(''); }} className="mt-4 rounded-xl bg-[#F7F8FB] px-3 py-2 text-[12px] text-[#34445F]">← {scheduleDateLabel(date)}</button>
        <label className="mt-4 block text-[12px] font-medium text-[#34445F]">Publishing time ({zone.abbreviation})<input autoFocus required type="text" inputMode="numeric" pattern="([01][0-9]|2[0-3]):[0-5][0-9]" placeholder="09:00" value={time} onChange={event => setTime(event.target.value)} className="mt-2 w-full rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] px-3 py-2.5 text-[14px]" /><span className="mt-1 block text-[10px] font-normal text-[#8B93A3]">24-hour format · HH:MM · Texas Central Time · {zone.offset}</span></label>
        <p className="mt-3 text-[11px] leading-relaxed text-[#8B93A3]">Confirmation approves this pack for publishing and saves its date to the calendar. No content is automatically posted.</p>
        {error && <p role="alert" className="mt-3 text-[11px] text-red-700">{error}</p>}
        <button type="submit" className="mt-4 w-full rounded-full bg-[#5070FF] px-4 py-2.5 text-[12px] font-semibold text-white">Confirm schedule</button>
      </form>}
    </div>, document.body)}
  </>;
}
