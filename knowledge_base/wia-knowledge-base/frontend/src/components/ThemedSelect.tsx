import React, { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Check, ChevronDown } from 'lucide-react';

interface Props {
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  name?: string;
  id?: string;
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
  'aria-label': string;
}

export function ThemedSelect({ value, defaultValue = '', onChange, children, className = '', disabled, name, id: fieldId, 'aria-label': label }: Props) {
  const options = React.Children.toArray(children).filter(React.isValidElement).map(child => {
    const props = (child as React.ReactElement<{ value?: string; children: React.ReactNode; disabled?: boolean }>).props;
    return { value: props.value ?? String(props.children), label: props.children, disabled: props.disabled };
  });
  const [internalValue, setInternalValue] = useState(defaultValue || options[0]?.value || '');
  const selectedValue = value ?? internalValue;
  const selected = options.find(option => option.value === selectedValue);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [position, setPosition] = useState({ left: 0, top: 0, width: 200, maxHeight: 240 });
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const typeahead = useRef({ text: '', time: 0 });
  const id = useId();
  const enabled = options.map((option, index) => !option.disabled ? index : -1).filter(index => index >= 0);

  const reveal = () => {
    setActive(selected && !selected.disabled ? options.indexOf(selected) : enabled[0] ?? 0);
    setOpen(true);
  };
  const choose = (index: number) => {
    const option = options[index];
    if (!option || option.disabled) return;
    setInternalValue(option.value);
    onChange?.(option.value);
    setOpen(false);
    trigger.current?.focus();
  };
  useLayoutEffect(() => {
    if (!open || !trigger.current) return;
    const rect = trigger.current.getBoundingClientRect();
    const width = Math.min(Math.max(rect.width, 220), window.innerWidth - 24);
    const desiredHeight = Math.min(options.length * 40 + 12, 240);
    const below = window.innerHeight - rect.bottom - 16;
    const above = rect.top - 16;
    const flip = below < desiredHeight && above > below;
    const maxHeight = Math.max(40, Math.min(desiredHeight, flip ? above : below));
    setPosition({ left: Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)), top: flip ? rect.top - maxHeight - 6 : rect.bottom + 6, width, maxHeight });
  }, [open, options.length]);
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (!trigger.current?.contains(event.target as Node) && !menu.current?.contains(event.target as Node)) setOpen(false);
    };
    const scroll = (event: Event) => { if (!menu.current?.contains(event.target as Node)) setOpen(false); };
    const blur = (event: FocusEvent) => { if (!trigger.current?.contains(event.target as Node) && !menu.current?.contains(event.target as Node)) setOpen(false); };
    const close = () => setOpen(false);
    document.addEventListener('pointerdown', outside);
    document.addEventListener('focusin', blur);
    window.addEventListener('scroll', scroll, true);
    window.addEventListener('resize', close);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('focusin', blur); window.removeEventListener('scroll', scroll, true); window.removeEventListener('resize', close); };
  }, [open]);
  useEffect(() => {
    if (open) menu.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: 'nearest' });
  }, [open, active]);

  return <>
    <input type="hidden" name={name} value={selectedValue} disabled={disabled} /><button id={fieldId} ref={trigger} type="button" role="combobox" aria-label={label} aria-haspopup="listbox" aria-expanded={open} aria-controls={open ? id : undefined} aria-activedescendant={open ? `${id}-${active}` : undefined} disabled={disabled}
      className={`atelier-select-trigger inline-flex items-center justify-between gap-3 ${className}`} onClick={() => open ? setOpen(false) : reveal()}
      onKeyDown={event => {
        if (event.key === 'Escape' && open) { event.preventDefault(); event.stopPropagation(); setOpen(false); return; }
        if (event.key === 'Tab') { setOpen(false); return; }
        if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
          event.preventDefault();
          if (!open) { reveal(); return; }
          const index = enabled.indexOf(active);
          setActive(event.key === 'Home' ? enabled[0] : event.key === 'End' ? enabled[enabled.length - 1] : enabled[(index + (event.key === 'ArrowDown' ? 1 : -1) + enabled.length) % enabled.length]);
        } else if ((event.key === 'Enter' || event.key === ' ') && open) { event.preventDefault(); choose(active); }
        else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && event.key !== ' ') {
          event.preventDefault();
          const now = Date.now();
          typeahead.current = { text: (now - typeahead.current.time < 700 ? typeahead.current.text : '') + event.key.toLowerCase(), time: now };
          const match = enabled.find(index => String(options[index].label).toLowerCase().startsWith(typeahead.current.text));
          if (match !== undefined) { setActive(match); setOpen(true); }
        }
      }}><span className="truncate">{selected?.label ?? 'Select…'}</span><ChevronDown aria-hidden="true" className={`w-3.5 h-3.5 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} /></button>
    {open && createPortal(<div ref={menu} id={id} role="listbox" aria-label={label} data-lenis-prevent className="atelier-select-menu" style={position} onClick={event => event.stopPropagation()}>
      {options.map((option, index) => <div key={option.value} id={`${id}-${index}`} role="option" aria-selected={option.value === selectedValue} aria-disabled={option.disabled || undefined} data-index={index}
        className={`atelier-select-option ${active === index ? 'is-active' : ''} ${option.value === selectedValue ? 'is-selected' : ''}`} onPointerDown={event => event.preventDefault()} onPointerMove={() => !option.disabled && setActive(index)} onClick={() => choose(index)}>
        <span>{option.label}</span>{option.value === selectedValue && <Check aria-hidden="true" className="w-3.5 h-3.5 shrink-0" />}
      </div>)}
    </div>, trigger.current?.closest('dialog') || document.body)}
  </>;
}
