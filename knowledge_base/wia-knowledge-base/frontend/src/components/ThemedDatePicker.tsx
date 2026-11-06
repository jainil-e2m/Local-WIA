import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { CalendarDays, ChevronLeft, ChevronRight, X } from 'lucide-react';

const iso = (date: Date) => date.toISOString().slice(0, 10);
const labelFor = (date: string) => new Date(`${date}T12:00:00Z`).toLocaleDateString('en-IN', { timeZone: 'Asia/Calcutta', day: 'numeric', month: 'short', year: 'numeric' });

// Adapted from Content Atelier's ScheduleDateGrid. Historical due dates remain selectable.
export function ThemedDatePicker({ value, defaultValue = '', onChange, name, label, clearable = false }: {
  value?: string; defaultValue?: string; onChange?: (date: string) => void; name?: string; label: string; clearable?: boolean;
}) {
  const [internal, setInternal] = useState(defaultValue);
  const date = value ?? internal;
  const today = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Calcutta' });
  const [cursor, setCursor] = useState(() => new Date(`${date || today}T12:00:00Z`));
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ left: 12, top: 12, width: 320, maxHeight: 480 });
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const id = useId();
  const close = () => { setOpen(false); trigger.current?.focus(); };
  const choose = (next: string) => { setInternal(next); onChange?.(next); close(); };
  const month = cursor.getUTCMonth(), year = cursor.getUTCFullYear();
  const count = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  const leading = (new Date(Date.UTC(year, month, 1)).getUTCDay() + 6) % 7;
  const move = (delta: number) => setCursor(new Date(Date.UTC(year, month + delta, 1, 12)));
  useLayoutEffect(() => {
    if (!open || !trigger.current || !panel.current) return;
    const rect = trigger.current.getBoundingClientRect();
    const width = Math.min(320, window.innerWidth - 24);
    const top = rect.bottom + 8;
    setPosition({ left: Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)), top, width, maxHeight: Math.max(0, window.innerHeight - top - 12) });
  }, [open, month, year]);
  useEffect(() => {
    if (!open) return;
    (panel.current?.querySelector<HTMLButtonElement>('[aria-pressed="true"]') || panel.current?.querySelector<HTMLButtonElement>('[data-day]'))?.focus({ preventScroll: true });
    const outside = (event: PointerEvent) => {
      if (!trigger.current?.contains(event.target as Node) && !panel.current?.contains(event.target as Node)) setOpen(false);
    };
    const scroll = (event: Event) => { if (!panel.current?.contains(event.target as Node)) setOpen(false); };
    const resize = () => setOpen(false);
    document.addEventListener('pointerdown', outside);
    window.addEventListener('scroll', scroll, true);
    window.addEventListener('resize', resize);
    return () => { document.removeEventListener('pointerdown', outside); window.removeEventListener('scroll', scroll, true); window.removeEventListener('resize', resize); };
  }, [open]);
  return <>
    <input type="hidden" name={name} value={date} />
    <button ref={trigger} type="button" className="atelier-date-trigger" aria-label={label} aria-describedby={`${id}-value`} aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? id : undefined} onClick={() => {
      if (open) close(); else { setCursor(new Date(`${date || today}T12:00:00Z`)); setOpen(true); }
    }}><span id={`${id}-value`}>{date ? labelFor(date) : 'Choose a date'}</span><CalendarDays size={16} /></button>
    {open && createPortal(<div ref={panel} id={id} role="dialog" aria-label={`Choose ${label.toLowerCase()}`} className="atelier-calendar" style={position} onKeyDown={event => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(); }
      if (event.key === 'Tab') {
        const controls = Array.from(panel.current?.querySelectorAll<HTMLButtonElement>('button') || []);
        const first = controls[0], last = controls.at(-1);
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    }}>
      <div className="atelier-calendar-title"><h3>Choose a date</h3><button type="button" className="icon-button" aria-label="Close calendar" onClick={close}><X size={16} /></button></div>
      <div className="atelier-calendar-month"><button type="button" className="icon-button" aria-label="Previous month" onClick={() => move(-1)}><ChevronLeft size={16} /></button><strong aria-live="polite">{cursor.toLocaleDateString('en-IN', { timeZone: 'UTC', month: 'long', year: 'numeric' })}</strong><button type="button" className="icon-button" aria-label="Next month" onClick={() => move(1)}><ChevronRight size={16} /></button></div>
      <div className="atelier-calendar-grid">{['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((day, index) => <span className="atelier-weekday" key={index}>{day}</span>)}
        {Array.from({ length: leading }, (_, index) => <span key={`blank-${index}`} />)}
        {Array.from({ length: count }, (_, index) => {
          const day = index + 1, next = iso(new Date(Date.UTC(year, month, day, 12)));
          return <button type="button" key={next} data-day={day} aria-label={labelFor(next)} aria-pressed={date === next} aria-current={next === today ? 'date' : undefined} className={date === next ? 'selected' : next === today ? 'today' : ''} onClick={() => choose(next)} onKeyDown={event => {
            const delta = ({ ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 } as Record<string, number>)[event.key];
            if (delta === undefined) return;
            event.preventDefault();
            panel.current?.querySelector<HTMLButtonElement>(`[data-day="${day + delta}"]`)?.focus();
          }}>{day}</button>;
        })}
      </div>
      <div className="atelier-calendar-footer"><span>{date ? labelFor(date) : 'Select a date'}</span><div className="atelier-calendar-actions">{clearable && date && <button type="button" className="text-button" onClick={() => choose('')}>Clear date</button>}<button type="button" className="text-button" onClick={() => choose(today)}>Today</button></div></div>
    </div>, trigger.current?.closest('dialog') || document.body)}
  </>;
}
