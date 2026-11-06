import React, { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Check, ChevronDown } from 'lucide-react';

/* The platform's dropdown: a pill or field trigger and a white rounded menu with the chosen row tinted blue and ticked, in
   place of the browser's own list (which cannot be themed). `ThemedSelect` reports the chosen value; `Select` takes the same
   props as a native <select> (its `onChange` receives `{ target: { value } }`), so a form swaps one for the other as is. */

interface Props {
  value?: string;
  defaultValue?: string;
  onChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  id?: string;
  name?: string;
  title?: string;
  ref?: React.Ref<HTMLButtonElement>;
  'aria-label'?: string;
}

type OptionProps = { value?: string | number; children?: React.ReactNode; disabled?: boolean; hidden?: boolean };

/** The <option>s among the children, through fragments and arrays. */
function optionsOf(children: React.ReactNode): { value: string; label: React.ReactNode; disabled?: boolean }[] {
  return React.Children.toArray(children).flatMap(child => {
    if (!React.isValidElement(child)) return [];
    if (child.type === React.Fragment) return optionsOf((child.props as { children?: React.ReactNode }).children);
    const props = child.props as OptionProps;
    if (props.hidden) return [];
    const text = React.Children.toArray(props.children).join('');
    return [{ value: props.value === undefined ? text : String(props.value), label: props.children, disabled: props.disabled }];
  });
}

const textOf = (label: React.ReactNode) => React.Children.toArray(label).join('');

export function ThemedSelect({ value, defaultValue = '', onChange, children, className = '', disabled, required, id: fieldId, name, title, ref, 'aria-label': label }: Props) {
  const options = optionsOf(children);
  const [internalValue, setInternalValue] = useState(defaultValue);
  const selectedValue = value ?? internalValue;
  const selected = options.find(option => option.value === selectedValue);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [position, setPosition] = useState({ left: 0, top: 0, width: 240, maxHeight: 320 });
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const typeahead = useRef({ text: '', time: 0 });
  const id = useId();
  const enabled = options.map((option, index) => !option.disabled ? index : -1).filter(index => index >= 0);
  const setTrigger = (element: HTMLButtonElement | null) => {
    trigger.current = element;
    if (typeof ref === 'function') ref(element); else if (ref) ref.current = element;
  };
  // A field-width trigger (`block`, `w-full`) stays a full-width row; a filter's stays inline.
  const display = /(^|\s)(block|w-full)(\s|$)/.test(className) ? 'flex w-full' : 'inline-flex';

  const reveal = () => {
    setActive(selected && !selected.disabled ? options.indexOf(selected) : enabled[0] ?? 0);
    setOpen(true);
  };
  const choose = (index: number) => {
    const option = options[index];
    if (!option || option.disabled) return;
    setInternalValue(option.value);
    // Like a native select, choosing the value already shown is no change.
    if (option.value !== selectedValue) onChange(option.value);
    setOpen(false);
    trigger.current?.focus();
  };
  useLayoutEffect(() => {
    if (!open || !trigger.current) return;
    const rect = trigger.current.getBoundingClientRect();
    const width = Math.min(Math.max(rect.width, 240), window.innerWidth - 24);
    // The list's own height (a long label wraps to two lines), up to 320px before it scrolls.
    const desiredHeight = Math.min((menu.current?.scrollHeight ?? options.length * 40) + 2, 320);
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
    if (open) menu.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView?.({ block: "nearest" });
  }, [open, active]);

  return <>
    <button ref={setTrigger} id={fieldId} title={title} type="button" role="combobox" aria-label={label} aria-haspopup="listbox" aria-expanded={open} aria-controls={open ? id : undefined} aria-activedescendant={open ? `${id}-${active}` : undefined} aria-required={required || undefined} disabled={disabled}
      className={`atelier-select-trigger ${display} items-center justify-between gap-3 text-left ${className.replace(/(^|\s)block(?=\s|$)/g, ' ')}`} onClick={() => open ? setOpen(false) : reveal()}
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
          const match = enabled.find(index => textOf(options[index].label).toLowerCase().startsWith(typeahead.current.text));
          if (match !== undefined) { setActive(match); setOpen(true); }
        }
      }}><span className="min-w-0 truncate">{selected?.label ?? 'Select…'}</span><ChevronDown aria-hidden="true" className={`w-3.5 h-3.5 shrink-0 text-[#8B93A3] transition-transform ${open ? 'rotate-180' : ''}`} /></button>
    {/* A hidden native mirror carries the value into the form: its name, and its own check that a required choice is made
        (focus it lands on goes back to the trigger). A change made to it directly is taken as a choice. */}
    <select tabIndex={-1} aria-hidden="true" className="sr-only" name={name} required={required} disabled={disabled} value={selectedValue}
      onFocus={() => trigger.current?.focus()} onChange={event => { const index = options.findIndex(option => option.value === event.target.value); if (index >= 0) choose(index); }}>
      {options.map((option, index) => <option key={`${option.value}-${index}`} value={option.value} disabled={option.disabled}>{textOf(option.label)}</option>)}
    </select>
    {open && createPortal(<div ref={menu} id={id} role="listbox" aria-label={label} data-lenis-prevent className="atelier-select-menu" style={position} onClick={event => event.stopPropagation()}>
      {options.map((option, index) => <div key={`${option.value}-${index}`} id={`${id}-${index}`} role="option" aria-selected={option.value === selectedValue} aria-disabled={option.disabled || undefined} data-index={index}
        className={`atelier-select-option ${active === index ? 'is-active' : ''} ${option.value === selectedValue ? 'is-selected' : ''}`} onPointerDown={event => event.preventDefault()} onPointerMove={() => !option.disabled && setActive(index)} onClick={() => choose(index)}>
        <span>{option.label}</span>{option.value === selectedValue && <Check aria-hidden="true" className="w-3.5 h-3.5 shrink-0" />}
      </div>)}
    </div>, document.body)}
  </>;
}

type SelectProps = Omit<Props, 'onChange' | 'value'> & { value?: string | number; onChange?: (event: { target: { value: string } }) => void };

/** A drop-in for a native <select>: same props, the platform's menu. */
export function Select({ onChange, value, ...props }: SelectProps) {
  return <ThemedSelect {...props} value={value === undefined ? undefined : String(value)} onChange={next => onChange?.({ target: { value: next } })} />;
}
