import React, { useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { CalendarClock, ChevronLeft, ChevronRight, X } from 'lucide-react';
import type { CalendarConfig, SavedSchedule, StoredPackV2 } from '../api/types';
import { storageRequest } from '../api/client';
import { useApiQuery, useInvalidate } from '../api/query';
import { civilFields, civilInstant, productionChanged, requestId } from '../utils/production';
import { changeScheduleMonth, scheduleDateLabel } from '../utils/scheduleCalendar';
import { useFeatureFlags } from '../utils/workspace';
import { ScheduleDateGrid } from './PackSchedulePopover';
import { pieceTitle } from './packFields';
import { button, input, primary } from './packParts';
import { useModalBehavior } from './useModalBehavior';

type Draft = { date: string; time: string };
type Props = { pack: StoredPackV2; active: string; busy: boolean };
const eligible = (piece: StoredPackV2['pieces'][number]) => !!piece.asset_id && !!piece.content_hash && !!piece.content && !piece.published.length;
const dateLabel = (at: string, zone: string) => new Intl.DateTimeFormat('en-IN', { timeZone: zone, dateStyle: 'medium', timeStyle: 'short' }).format(new Date(at));

/** Scheduling is review metadata on existing assets, separate from the copy and from publication marks. */
export function PackScheduling({ pack, active, busy }: Props) {
  const flags = useFeatureFlags();
  const config = useApiQuery('/calendar/config', undefined, { enabled: flags.calendar, staleTime: 30_000 });
  const [open, setOpen] = useState(false);
  const invalidate = useInvalidate();
  if (!flags.calendar) return null;
  const zone = config.data?.display_timezone;
  const saved = pack.pieces.filter(p => p.schedule).length;
  const current = pack.pieces.find(p => p.key === active)?.schedule;
  const reason = config.error?.message || (!config.data ? 'Loading scheduling…' : !config.data.enabled ? 'Calendar scheduling is disabled.'
    : !config.data.can_schedule ? 'You do not have permission to schedule content.' : (!['in_review', 'ready_to_publish'].includes(pack.state) || !pack.manifest_hash) && !saved ? 'The pack must finish before scheduling.'
    : pack.run_active && !saved ? 'The pack is still being written.' : !pack.pieces.some(eligible) && !saved ? 'No unpublished pieces are available to schedule.' : '');
  return <div className="flex flex-wrap items-center justify-end gap-3 text-xs">
    {zone && <span className="text-[#667184]">{current ? `Scheduled: ${dateLabel(current.scheduled_for, zone)} · ${zone}` : saved ? `${saved} of ${pack.pieces.length} pieces scheduled` : ''}</span>}
    <button type="button" className={`${button} inline-flex items-center gap-2 !text-xs`} aria-haspopup="dialog" disabled={busy || !!reason}
      title={reason || undefined} onClick={() => setOpen(true)}><CalendarClock className="h-4 w-4" />Schedule</button>
    {open && config.data && createPortal(<ScheduleDialog pack={pack} initialPiece={active} config={config.data} onClose={() => setOpen(false)}
      onSaved={async () => { productionChanged(); await invalidate('/packs/{pack_id}', '/calendar'); setOpen(false); }} />, document.body)}
  </div>;
}

export function ScheduleDialog({ pack, initialPiece, config, onClose, onSaved }: {
  pack: StoredPackV2; initialPiece: string; config: CalendarConfig; onClose: () => void; onSaved: () => Promise<void>;
}) {
  const zone = config.display_timezone;
  const today = civilFields(new Date(), zone).date;
  const canSave = ['in_review', 'ready_to_publish'].includes(pack.state) && !!pack.manifest_hash && !pack.run_active && config.enabled && config.can_schedule;
  const first = pack.pieces.find(p => p.key === initialPiece && (eligible(p) || p.schedule)) ?? pack.pieces.find(p => eligible(p) || p.schedule);
  const [active, setActive] = useState(first?.key ?? 'email');
  const [selected, setSelected] = useState<string[]>(first && canSave && eligible(first) ? [first.key] : []);
  const [pending, setPending] = useState<Record<string, Draft>>({});
  const [copied, setCopied] = useState<string[]>([]);
  const [message, setMessage] = useState('');
  const [drafts, setDrafts] = useState<Record<string, Draft>>(() => Object.fromEntries(pack.pieces.map(p =>
    [p.key, p.schedule ? civilFields(p.schedule.scheduled_for, zone) : { date: '', time: '09:00' }])));
  const [step, setStep] = useState<'date' | 'time'>('date');
  const initialDate = first?.schedule ? civilFields(first.schedule.scheduled_for, zone).date : today;
  const [cursor, setCursor] = useState({ year: Number(initialDate.slice(0, 4)), month: Number(initialDate.slice(5, 7)) - 1 });
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const ids = useRef(new Map<string, string>());
  const modal = useModalBehavior(() => { if (!busy) onClose(); });
  const piece = pack.pieces.find(p => p.key === active)!;
  const draft = drafts[active];
  const selectionReady = selected.length > 0 && selected.every(key => pending[key]
    && pending[key].date === drafts[key].date && pending[key].time === drafts[key].time);
  const update = (change: Partial<Draft>) => { setDrafts(prev => ({ ...prev, [active]: { ...prev[active], ...change } })); setCopied([]); setError(''); setMessage(''); };
  const choose = (key: typeof active) => {
    setActive(key); setStep('date'); setCopied([]); setError(''); setMessage('');
    if (canSave && eligible(pack.pieces.find(p => p.key === key)!)) setSelected(prev => prev.includes(key) ? prev : [...prev, key]);
    const date = drafts[key].date || today;
    setCursor({ year: Number(date.slice(0, 4)), month: Number(date.slice(5, 7)) - 1 });
  };
  const instant = (p: StoredPackV2['pieces'][number], value: Draft) => {
    if (!eligible(p)) throw new Error(`${p.label} cannot be scheduled.`);
    if (!value.date) throw new Error(`Choose a date for ${p.label}.`);
    const at = civilInstant(value.date, value.time, zone);
    if (Date.parse(at) <= Date.now()) throw new Error(`Choose a future time for ${p.label}.`);
    return at;
  };
  const stage = () => {
    setError('');
    try {
      instant(piece, draft);
      setPending(prev => ({ ...prev, [active]: { ...draft } }));
      setSelected(prev => prev.includes(active) ? prev : [...prev, active]);
      setMessage(`${piece.label} schedule added. Choose another piece or save all schedules.`);
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Check the selected date and time.'); }
  };
  const unscheduled = pack.pieces.filter(p => p.key !== active && eligible(p) && !p.schedule && !pending[p.key] && !drafts[p.key].date);
  const copySchedule = (checked: boolean) => {
    setError('');
    if (!checked) {
      setPending(prev => Object.fromEntries(Object.entries(prev).filter(([key]) => !copied.includes(key))));
      setDrafts(prev => ({ ...prev, ...Object.fromEntries(copied.map(key => [key, { date: '', time: '09:00' }])) }));
      setSelected(prev => prev.filter(key => !copied.includes(key)));
      setCopied([]); setMessage('');
      return;
    }
    try {
      instant(piece, draft);
      const keys = [active, ...unscheduled.map(p => p.key)];
      const values = Object.fromEntries(keys.map(key => [key, { ...draft }]));
      setPending(prev => ({ ...prev, ...values })); setDrafts(prev => ({ ...prev, ...values }));
      setSelected(prev => [...new Set([...prev, ...keys])]);
      setCopied(unscheduled.map(p => p.key));
      setMessage(`Same schedule added to ${unscheduled.length} other unscheduled pieces.`);
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Check the selected date and time.'); }
  };
  const save = async () => {
    setError('');
    try {
      if (!selected.length) throw new Error('Select at least one piece.');
      const items = pack.pieces.filter(p => selected.includes(p.key)).map(p => {
        const staged = pending[p.key];
        if (!staged || staged.date !== drafts[p.key].date || staged.time !== drafts[p.key].time)
          throw new Error(`Click Save schedule for ${p.label} to add its latest date and time.`);
        const at = instant(p, staged);
        return { asset_id: p.asset_id, expected_asset_hash: p.content_hash, scheduled_for: at, display_timezone: zone,
          ...(p.schedule ? { entry_id: p.schedule.calendar_entry_id, expected_revision: p.schedule.revision } : {}) };
      });
      const data = { expected_pack_manifest_hash: pack.manifest_hash, whole_pack: items.length === pack.pieces.length, items };
      const key = JSON.stringify(data);
      if (!ids.current.has(key)) ids.current.set(key, requestId());
      setBusy(true);
      await storageRequest<{ entries: SavedSchedule[] }>(`/packs/${pack.pack_id}/schedule`, 'POST', { ...data, request_id: ids.current.get(key) });
      ids.current.delete(key);
      await onSaved();
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Could not save the schedule.'); }
    finally { setBusy(false); }
  };
  return <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/35 p-4" onClick={e => { if (e.target === e.currentTarget && !busy) onClose(); }}>
    <div ref={modal} role="dialog" aria-modal="true" aria-labelledby="schedule-pack-title" tabIndex={-1}
      className="max-h-[90dvh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-5 shadow-xl sm:p-6">
      <header className="flex items-start justify-between gap-3"><div><h2 id="schedule-pack-title" className="font-editorial text-2xl text-[#173354]">Schedule content pack</h2>
        <p className="mt-1 text-xs text-[#667184]">{pack.title}</p></div>
        <button type="button" aria-label="Close scheduling" disabled={busy} onClick={onClose} className="rounded-full p-2"><X className="h-4 w-4" /></button></header>
      <p className="my-4 text-xs text-[#667184]">Select pieces and set their date and time. Click Save schedule for each, then Save all schedules when you are finished. All times: {zone}.</p>
      <fieldset disabled={busy} className="grid gap-5 sm:grid-cols-2">
        <legend className="sr-only">Content schedules</legend>
        <div className="space-y-2">{pack.pieces.map(p => <div key={p.key} className={`flex items-start gap-2 rounded-xl border p-3 ${p.key === active ? 'border-[#5070FF] bg-[#EFF3FF]' : 'border-[#E6E9F0]'}`}>
          <input type="checkbox" aria-label={`Include ${p.label}`} className="mt-1" disabled={!canSave || !eligible(p)} checked={selected.includes(p.key)}
            onChange={e => { if (e.target.checked) choose(p.key); else setSelected(prev => prev.filter(k => k !== p.key)); setError(''); }} />
          <button type="button" aria-label={`Schedule ${p.label}`} aria-pressed={p.key === active} className="min-w-0 flex-1 text-left disabled:opacity-50" disabled={!p.asset_id} onClick={() => choose(p.key)}>
            <span className="block text-sm font-semibold text-[#173354]">{p.label}</span><span className="block truncate text-xs text-[#667184]">{pieceTitle(p)}</span>
            <span className="mt-1 block text-xs text-[#667184]">{p.published.length ? 'Already published' : !p.content ? 'Not written' : p.schedule ? `Saved: ${dateLabel(p.schedule.scheduled_for, zone)}` : 'Not scheduled'}</span>
            {selected.includes(p.key) && pending[p.key] && <span className="mt-1 block text-xs text-[#5070FF]">Ready to save: {scheduleDateLabel(pending[p.key].date)} · {pending[p.key].time}</span>}
            {selected.includes(p.key) && pending[p.key] && (pending[p.key].date !== drafts[p.key].date || pending[p.key].time !== drafts[p.key].time)
              && <span className="mt-1 block text-xs text-amber-800">Date or time changed. Click Save schedule to update.</span>}
          </button>
        </div>)}</div>
        <div className="rounded-xl border border-[#E6E9F0] p-4">
          <h3 className="font-semibold text-[#173354]">{piece.label}: {step === 'date' ? 'choose a date' : 'choose a time'}</h3>
          {!canSave || !eligible(piece) ? <p className="mt-4 text-sm text-[#667184]">{piece.published.length ? 'This piece is already marked published.' : 'This piece is not available for scheduling.'}</p> : step === 'date' ? <>
            <div className="mt-3 flex items-center justify-between"><button type="button" aria-label="Previous month" disabled={`${cursor.year}-${String(cursor.month + 1).padStart(2, '0')}` <= today.slice(0, 7)} onClick={() => setCursor(changeScheduleMonth(cursor.year, cursor.month, -1))}><ChevronLeft className="h-5 w-5" /></button>
              <span className="text-sm">{new Date(Date.UTC(cursor.year, cursor.month, 1)).toLocaleDateString('en-IN', { month: 'long', year: 'numeric', timeZone: 'UTC' })}</span>
              <button type="button" aria-label="Next month" onClick={() => setCursor(changeScheduleMonth(cursor.year, cursor.month, 1))}><ChevronRight className="h-5 w-5" /></button></div>
            <ScheduleDateGrid cursor={cursor} today={today} date={draft.date} onSelect={date => update({ date })} />
            <button type="button" className={`${primary} mt-4 w-full`} disabled={!draft.date} onClick={() => setStep('time')}>Next: choose a time</button>
          </> : <>
            <button type="button" className="mt-3 text-sm text-[#5070FF]" onClick={() => setStep('date')}>← {scheduleDateLabel(draft.date)}</button>
            <label className="mt-4 block text-sm">Publishing time<input type="text" inputMode="numeric" placeholder="09:00" required pattern="([01][0-9]|2[0-3]):[0-5][0-9]" className={input} value={draft.time} onChange={e => update({ time: e.target.value })} /></label>
            <p className="mt-1 text-xs text-[#667184]">24-hour format · HH:MM</p>
            <button type="button" className={`${button} mt-4 w-full !text-xs`} onClick={stage}>Save schedule</button>
            <label className="mt-4 flex items-start gap-2 text-xs text-[#667184]">
              <input type="checkbox" className="mt-0.5 shrink-0" checked={copied.length > 0} disabled={!unscheduled.length && !copied.length}
                onChange={e => copySchedule(e.target.checked)} />
              <span>Want the same schedule for the other unscheduled items?</span>
            </label>
          </>}
        </div>
      </fieldset>
      <p role="status" className="mt-3 text-xs text-emerald-800">{message}</p>
      {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800">{error} Your selections have been kept. Refresh the pack if someone else changed it.</p>}
      <footer className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[#E6E9F0] pt-4"><p className="text-xs text-[#667184]">{selected.length} of {pack.pieces.length} pieces selected. No content is automatically posted.</p>
        <button type="button" className={primary} disabled={busy || !canSave || !selectionReady} onClick={() => void save()}>{busy ? 'Saving…' : 'Save all schedules'}</button></footer>
    </div>
  </div>;
}
