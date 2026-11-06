import { useEffect, useId, useRef, type CSSProperties, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { ArrowUpRight, CalendarDays, Check, FileText, Mail, MessageSquare, Search, Video, X } from 'lucide-react';
import { sourceById } from '../data';
import type { Client, SourceKind, Tone } from '../types';

export function Badge({ children, tone = 'neutral', dot = true }: { children: ReactNode; tone?: Tone; dot?: boolean }) {
  return <span className={`badge badge-${tone}`}>{dot && <i aria-hidden="true" />}{children}</span>;
}

export function Avatar({ client, small = false }: { client: Client; small?: boolean }) {
  return <span className={`client-avatar ${small ? 'small' : ''} avatar-${client.tone}`} aria-hidden="true">{client.initials}</span>;
}

export function SourceIcon({ kind, size = 14 }: { kind: SourceKind; size?: number }) {
  const Icon = kind === 'Zoom' || kind === 'Fathom' ? Video : kind === 'Gmail' ? Mail : kind === 'Slack' ? MessageSquare : kind === 'Calendar' ? CalendarDays : FileText;
  return <Icon size={size} strokeWidth={1.7} />;
}

export function SourceLink({ id, onOpen, label }: { id: string; onOpen: (id: string) => void; label?: string }) {
  const source = sourceById(id);
  if (!source) return <span className="muted small-text">Source unavailable</span>;
  return <button className={`source-link source-${source.kind.toLowerCase()}`} onClick={() => onOpen(id)}><SourceIcon kind={source.kind} />{label || source.kind}<ArrowUpRight size={11} /></button>;
}

export function PageHeading({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: ReactNode }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div>{children && <div className="heading-actions">{children}</div>}</div>;
}

export function Panel({ title, eyebrow, children, action, className = '' }: { title?: string; eyebrow?: string; children: ReactNode; action?: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{title && <div className="panel-heading"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2>{title}</h2></div>{action}</div>}{children}</section>;
}

export function Empty({ title = 'Nothing here yet', children }: { title?: string; children?: ReactNode }) {
  return <div className="empty-state"><Search size={24} strokeWidth={1.4} /><h3>{title}</h3><p>{children || 'Try a different search or filter.'}</p></div>;
}

export function Sparkline({ values, tone = 'blue' }: { values: number[]; tone?: Tone }) {
  const max = Math.max(...values, 1);
  const points = values.map((value, index) => `${index * (100 / (values.length - 1))},${26 - value / max * 21}`).join(' ');
  return <svg className={`sparkline sparkline-${tone}`} viewBox="0 0 104 30" role="img" aria-label="Sample communication activity over the past twelve weeks"><polyline fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" points={points} /><circle cx="100" cy={26 - values[values.length - 1] / max * 21} r="2.5" fill="currentColor" /></svg>;
}

export function Coverage({ value }: { value: number }) {
  return <div className="coverage"><div className="coverage-track"><span style={{ width: `${value}%` }} /></div><span>{value}%</span></div>;
}

/**
 * The project's one modal/drawer frame: eyebrow + serif title (+ optional meta line), a scrolling body,
 * and an optional sticky footer for actions. `size="lg"` widens a modal for lists and tables.
 */
export function Dialog({ title, subtitle, meta, footer, size = 'md', onClose, children, drawer = false, className = '' }: { title: string; subtitle?: string; meta?: ReactNode; footer?: ReactNode; size?: 'md' | 'lg'; onClose: () => void; children: ReactNode; drawer?: boolean; className?: string }) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    const previous = document.activeElement as HTMLElement | null;
    dialog.showModal();
    return () => { dialog.close(); previous?.focus(); };
  }, []);
  return createPortal(<dialog ref={ref} className={`${drawer ? 'drawer' : `modal modal-${size}`} ${footer ? 'has-footer' : ''} ${className}`} aria-labelledby={titleId} onCancel={event => { event.preventDefault(); onClose(); }} onClick={event => { if (event.target === ref.current) { const rect = ref.current.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose(); } }}><div className="dialog-heading"><div>{subtitle && <p className="eyebrow">{subtitle}</p>}<h2 id={titleId}>{title}</h2>{meta && <div className="dialog-meta">{meta}</div>}</div><button className="icon-button dialog-close" aria-label="Close dialog" onClick={onClose}><X size={18} /></button></div><div className="dialog-body">{children}</div>{footer && <div className="dialog-footer">{footer}</div>}</dialog>, document.body);
}

export function Segmented({ value, options, onChange, label }: { value: string; options: { id: string; label: string; count?: number }[]; onChange: (id: string) => void; label: string }) {
  return <div className="segmented" role="group" aria-label={label}>{options.map(option => <button key={option.id} className={value === option.id ? 'selected' : ''} aria-pressed={value === option.id} onClick={() => onChange(option.id)}>{option.label}{option.count !== undefined && <span>{option.count}</span>}</button>)}</div>;
}

export function SearchField({ value, onChange, placeholder, label }: { value: string; onChange: (value: string) => void; placeholder: string; label: string }) {
  return <label className="search-field"><Search size={16} /><input aria-label={label} value={value} onChange={event => onChange(event.target.value)} placeholder={placeholder} />{value && <button aria-label={`Clear ${label.toLowerCase()}`} onClick={() => onChange('')}><X size={14} /></button>}</label>;
}

export function Stat({ label, value, detail, tone = 'blue', icon }: { label: string; value: ReactNode; detail: string; tone?: Tone; icon: ReactNode }) {
  return <div className="stat"><div className="stat-label"><span>{label}</span><span className={`stat-icon text-${tone}`}>{icon}</span></div><div className="stat-value">{value}</div><div className="stat-detail">{detail}</div></div>;
}

export const checkIcon = <Check size={14} />;
export const cssVar = (values: Record<string, string | number>) => values as CSSProperties;
