import React, { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { CalendarDays, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { changeScheduleMonth, scheduleMonthDays } from '../utils/scheduleCalendar';

/* The platform's date field: the trigger in the field's own style and, in place of the browser's calendar (which cannot be
   themed), the scheduling calendar's look — a white rounded card, Monday-first weeks, round days, today ringed in gold and
   the chosen day in blue. It takes the props of a native <input type="date">: `value`, `min` and `max` are YYYY-MM-DD and
   `onChange` receives `{ target: { value } }`, '' when cleared. */

interface Props {
  value?: string;
  onChange?: (event: { target: { value: string } }) => void;
  min?: string;
  max?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  id?: string;
  name?: string;
  placeholder?: string;
  ref?: React.Ref<HTMLButtonElement>;
  'aria-label'?: string;
}

const pad = (n: number) => String(n).padStart(2, '0');
const localToday = () => { const now = new Date(); return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`; };
const isDate = (value: string | undefined): value is string => !!value && /^\d{4}-\d{2}-\d{2}$/.test(value);
const shiftDays = (date: string, days: number) => new Date(Date.parse(`${date}T00:00:00Z`) + days * 86_400_000).toISOString().slice(0, 10);
const words = (date: string, options: Intl.DateTimeFormatOptions) => new Date(`${date}T00:00:00Z`).toLocaleDateString('en-GB', { timeZone: 'UTC', ...options });
const monthOf = (date: string) => ({ year: Number(date.slice(0, 4)), month: Number(date.slice(5, 7)) - 1 });

export function DateInput({ value = '', onChange, min, max, className = '', disabled, required, id: fieldId, name, placeholder = 'Choose a date', ref, 'aria-label': label }: Props) {
  const [open, setOpen] = useState(false);
  const [focus, setFocus] = useState(value || localToday());
  const [position, setPosition] = useState({ left: 0, top: 0 });
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const id = useId();
  const today = localToday();
  const cursor = monthOf(focus);
  const allowed = (date: string) => (!isDate(min) || date >= min) && (!isDate(max) || date <= max);
  const setTrigger = (element: HTMLButtonElement | null) => {
    trigger.current = element;
    if (typeof ref === 'function') ref(element); else if (ref) ref.current = element;
  };
  // A field-width trigger (`block`, `w-full`) stays a full-width row; a filter's stays inline.
  const display = /(^|\s)(block|w-full)(\s|$)/.test(className) ? 'flex w-full' : 'inline-flex';

  const reveal = () => {
    const start = isDate(value) ? value : allowed(today) ? today : isDate(min) && today < min ? min : isDate(max) ? max : today;
    setFocus(start);
    setOpen(true);
  };
  const close = () => { setOpen(false); trigger.current?.focus(); };
  const choose = (date: string) => { if (date !== value) onChange?.({ target: { value: date } }); close(); };
  const moveMonth = (delta: number) => {
    const next = changeScheduleMonth(cursor.year, cursor.month, delta);
    const last = new Date(Date.UTC(next.year, next.month + 1, 0)).getUTCDate();
    setFocus(`${next.year}-${pad(next.month + 1)}-${pad(Math.min(Number(focus.slice(8, 10)), last))}`);
  };

  useLayoutEffect(() => {
    if (!open || !trigger.current || !panel.current) return;
    const rect = trigger.current.getBoundingClientRect();
    const width = panel.current.offsetWidth, height = panel.current.offsetHeight;
    const below = rect.bottom + 6;
    const top = below + height <= window.innerHeight - 12 || rect.top - height - 6 < 12 ? below : rect.top - height - 6;
    setPosition({ left: Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)), top: Math.max(12, top) });
  }, [open, cursor.year, cursor.month]);
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => { if (!trigger.current?.contains(event.target as Node) && !panel.current?.contains(event.target as Node)) setOpen(false); };
    const scroll = (event: Event) => { if (!panel.current?.contains(event.target as Node)) setOpen(false); };
    const resize = () => setOpen(false);
    document.addEventListener('pointerdown', outside);
    window.addEventListener('scroll', scroll, true);
    window.addEventListener('resize', resize);
    return () => { document.removeEventListener('pointerdown', outside); window.removeEventListener('scroll', scroll, true); window.removeEventListener('resize', resize); };
  }, [open]);
  // The focused day takes the keyboard focus as it moves, also across months.
  useEffect(() => { if (open) panel.current?.querySelector<HTMLButtonElement>(`[data-date="${focus}"]`)?.focus({ preventScroll: true }); }, [open, focus]);

  const nav = 'flex h-7 w-7 items-center justify-center rounded-full text-[#667184] hover:bg-[#F7F8FB]';
  return <>
    <button ref={setTrigger} id={fieldId} type="button" aria-label={label} aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? id : undefined} aria-required={required || undefined} disabled={disabled}
      className={`atelier-select-trigger ${display} items-center justify-between gap-3 text-left ${className.replace(/(^|\s)block(?=\s|$)/g, ' ')}`}
      onClick={() => open ? setOpen(false) : reveal()} onKeyDown={event => { if (event.key === 'ArrowDown' && !open) { event.preventDefault(); reveal(); } }}>
      <span className={`min-w-0 truncate ${isDate(value) ? '' : 'text-[#A3AAB8]'}`}>{isDate(value) ? words(value, { day: 'numeric', month: 'short', year: 'numeric' }) : placeholder}</span>
      <CalendarDays aria-hidden="true" className="h-3.5 w-3.5 shrink-0 text-[#8B93A3]" />
    </button>
    {/* A hidden native mirror carries the date into the form: its name, min and max, and its own check that a required date
        is given (focus it lands on goes back to the trigger). A date typed into it directly is taken as chosen. */}
    <input type="date" tabIndex={-1} aria-hidden="true" className="sr-only" name={name} required={required} disabled={disabled} min={min} max={max} value={value}
      onFocus={() => trigger.current?.focus()} onChange={event => { if (event.target.value !== value) onChange?.({ target: { value: event.target.value } }); }} />    {open && createPortal(<div ref={panel} id={id} role="dialog" aria-label={label ? `${label}: choose a date` : 'Choose a date'} data-lenis-prevent style={position}
      className="fixed z-[100] w-[288px] max-w-[calc(100vw-24px)] rounded-2xl border border-[#E6E9F0] bg-white p-3.5 shadow-[0_12px_36px_rgba(28,49,76,0.14)]"
      onKeyDown={event => {
        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(); return; }
        if (event.key === 'Tab') {
          // Tab stays inside the calendar while it is open.
          const targets = Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled):not([tabindex="-1"])') ?? []);
          const at = targets.indexOf(document.activeElement as HTMLElement);
          event.preventDefault();
          targets[(at + (event.shiftKey ? -1 : 1) + targets.length) % targets.length]?.focus();
          return;
        }
        if (!(event.target as HTMLElement).dataset.date) return;
        const days = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
        if (days !== undefined) { event.preventDefault(); setFocus(shiftDays(focus, days)); }
        else if (event.key === 'PageUp' || event.key === 'PageDown') { event.preventDefault(); moveMonth((event.key === 'PageDown' ? 1 : -1) * (event.shiftKey ? 12 : 1)); }
      }}>
      <div className="flex items-center justify-between gap-1">
        <span className="flex"><button type="button" aria-label="Previous year" className={nav} onClick={() => moveMonth(-12)}><ChevronsLeft className="h-4 w-4" /></button>
          <button type="button" aria-label="Previous month" className={nav} onClick={() => moveMonth(-1)}><ChevronLeft className="h-4 w-4" /></button></span>
        <span aria-live="polite" className="text-[13px] font-semibold text-[#34445F]">{words(`${cursor.year}-${pad(cursor.month + 1)}-01`, { month: 'long', year: 'numeric' })}</span>
        <span className="flex"><button type="button" aria-label="Next month" className={nav} onClick={() => moveMonth(1)}><ChevronRight className="h-4 w-4" /></button>
          <button type="button" aria-label="Next year" className={nav} onClick={() => moveMonth(12)}><ChevronsRight className="h-4 w-4" /></button></span>
      </div>
      <div aria-hidden="true" className="mt-2 grid grid-cols-7 gap-1">{['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((day, index) => <span key={index} className="py-1 text-center text-[9px] font-semibold text-[#9AA3B2]">{day}</span>)}</div>
      <div role="group" className="grid grid-cols-7 gap-1">{scheduleMonthDays(cursor.year, cursor.month).map((cell, index) => cell
        ? <button key={cell.date} type="button" data-date={cell.date} tabIndex={cell.date === focus ? 0 : -1} disabled={!allowed(cell.date)} aria-pressed={cell.date === value}
          aria-label={words(cell.date, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })} onClick={() => choose(cell.date)}
          className={`aspect-square rounded-full text-[12px] font-medium focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[#8DA1FD] disabled:cursor-not-allowed disabled:opacity-25 ${cell.date === value ? 'bg-[#5070FF] text-white' : cell.date === today ? 'border border-[#D9BE87] text-[#A38B61] hover:bg-[#FBF7EF]' : 'text-[#34445F] hover:bg-[#EFF3FF]'}`}>{cell.day}</button>
        : <span key={`blank-${index}`} />)}</div>
      <div className="mt-3 flex items-center justify-between border-t border-[#EEF0F4] pt-2.5 text-[12px] font-medium">
        {required ? <span /> : <button type="button" className="rounded-full px-2.5 py-1 text-[#667184] hover:bg-[#F7F8FB] disabled:opacity-40" disabled={!value} onClick={() => choose('')}>Clear</button>}
        <button type="button" className="rounded-full px-2.5 py-1 text-[#5070FF] hover:bg-[#EFF3FF] disabled:opacity-40" disabled={!allowed(today)} onClick={() => choose(today)}>Today</button>
      </div>
    </div>, document.body)}
  </>;
}
