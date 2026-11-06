import React, { useEffect, useId, useRef, useState } from 'react';
import { Check } from 'lucide-react';

export function RevivalApproval({ onApprove, atCapacity = false }: { onApprove: () => void; atCapacity?: boolean }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const reject = useRef<HTMLButtonElement>(null);
  const id = useId();
  const dismiss = () => { setOpen(false); trigger.current?.focus(); };
  useEffect(() => {
    if (!open) return;
    reject.current?.focus();
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); dismiss(); } };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape, true);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape, true); };
  }, [open]);
  return <div ref={root} className="relative ml-auto inline-flex">
    {open && <div id={id} role="group" aria-label="Confirm revival" className="absolute bottom-full right-0 z-20 mb-2 flex gap-1 rounded-xl border border-[#E6E9F0] bg-white p-1.5 shadow-[0_6px_24px_rgba(28,49,76,0.14)]">
      <button type="button" disabled={atCapacity} title={atCapacity ? 'Weekly Studio already has four concepts.' : undefined} onClick={() => { setOpen(false); onApprove(); }} className="rounded-lg bg-[#5070FF] px-4 py-2 text-[11px] font-medium text-white hover:bg-[#4260E8] disabled:cursor-not-allowed disabled:opacity-40">Approve</button>
      <button ref={reject} type="button" onClick={dismiss} className="rounded-lg px-4 py-2 text-[11px] font-medium text-[#667184] hover:bg-[#F7F8FB]">Reject</button>
    </div>}
    <button ref={trigger} type="button" aria-expanded={open} aria-controls={open ? id : undefined} onClick={() => setOpen(value => !value)} className="flex items-center gap-1.5 rounded-full bg-[#1B2838] px-3 py-2 text-[11px] font-medium text-white hover:bg-[#34445F]"><Check className="h-3 w-3" />Approve revival → Weekly Studio</button>
  </div>;
}
