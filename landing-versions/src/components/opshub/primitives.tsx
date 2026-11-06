/* ────────────────────────────────────────────────────────────────
   Ops Hub primitives — the eight pieces every screen is built from.

   Kept in one file on purpose. These are small, they change together, and
   splitting a 20-line Pill into its own module buys nothing. Anything that
   grows past a screenful moves out.
   ──────────────────────────────────────────────────────────────── */

import { useState, type ReactNode } from "react";
import { Check, ChevronDown } from "lucide-react";
import { useDismiss } from "@/hooks/useDismiss";
import { cn } from "@/lib/utils";
import {
  AUTO_BADGE,
  GLYPH_CLASS,
  SOURCE_META,
  TONE_CLASS,
  type AutoSystem,
  type SourceKey,
  type Tone,
} from "@/lib/opsHub";

/* ── Pill ─────────────────────────────────────────────────────── */

export function Pill({
  tone = "neutral",
  children,
  className,
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-[3px] text-[10.5px] font-bold uppercase leading-none tracking-[0.06em]",
        TONE_CLASS[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/* ── Source chip — coloured dot + name ────────────────────────── */

export function SourceChip({
  source,
  label,
  className,
}: {
  source: SourceKey;
  label?: string;
  className?: string;
}) {
  const meta = SOURCE_META[source];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border border-brand-mist bg-white px-2 py-[3px] text-[10.5px] font-bold uppercase tracking-[0.06em]",
        className,
      )}
      style={{ color: meta.color }}
    >
      <span
        className="h-[5px] w-[5px] flex-none rounded-full"
        style={{ background: meta.color }}
        aria-hidden
      />
      {label ?? meta.label}
    </span>
  );
}

export function SourceDot({ source }: { source: SourceKey }) {
  return (
    <span
      className="h-[6px] w-[6px] flex-none rounded-full"
      style={{ background: SOURCE_META[source].color }}
      aria-hidden
    />
  );
}

/* ── Automation attribution badge ─────────────────────────────── */

export function AutoBadge({ system }: { system: AutoSystem }) {
  const b = AUTO_BADGE[system];
  return <Pill tone={b.tone}>{b.label}</Pill>;
}

/* ── Panel ────────────────────────────────────────────────────── */

export function Panel({
  title,
  subtitle,
  right,
  children,
  className,
  bodyClassName,
}: {
  title?: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-2xl border border-brand-mist bg-white shadow-[0_10px_30px_-22px_rgba(34,30,23,0.18)]",
        className,
      )}
    >
      {(title || right) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-brand-mist/70 px-5 py-4">
          <div className="min-w-0">
            {title && (
              <h2 className="text-[15px] font-bold leading-tight tracking-[-0.01em] text-brand-ink">
                {title}
              </h2>
            )}
            {subtitle && (
              <p className="mt-1 text-[12px] leading-snug text-brand-gray">{subtitle}</p>
            )}
          </div>
          {right && <div className="flex flex-none items-center gap-2">{right}</div>}
        </header>
      )}
      <div className={cn("px-5 py-4", bodyClassName)}>{children}</div>
    </section>
  );
}

/* ── Card — a bordered block inside a panel ───────────────────── */

export function Card({
  children,
  className,
  accent,
  onClick,
}: {
  children: ReactNode;
  className?: string;
  accent?: string;
  onClick?: () => void;
}) {
  const interactive = typeof onClick === "function";
  return (
    <div
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      className={cn(
        "rounded-xl border border-brand-mist bg-white p-4",
        interactive &&
          "cursor-pointer transition-colors hover:border-brand-stone hover:bg-brand-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/40",
        className,
      )}
      style={accent ? { borderLeft: `3px solid ${accent}` } : undefined}
    >
      {children}
    </div>
  );
}

/* ── Stat tile ────────────────────────────────────────────────── */

export function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl border border-brand-mist bg-brand-surface px-4 py-3">
      <p className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-brand-gray">
        {label}
      </p>
      <p className="mt-1.5 text-[28px] font-bold leading-none tracking-[-0.03em] text-brand-ink">
        {value}
      </p>
    </div>
  );
}

/* ── Tabs ─────────────────────────────────────────────────────── */

export function Tabs({
  tabs,
  active,
  counts,
  onSelect,
}: {
  tabs: [string, string][];
  active: string;
  counts?: Record<string, number>;
  onSelect: (id: string) => void;
}) {
  return (
    <div
      role="tablist"
      className="flex flex-wrap items-center gap-1.5 rounded-xl border border-brand-mist bg-white p-1.5"
    >
      {tabs.map(([id, label]) => {
        const on = active === id;
        const count = counts?.[id];
        return (
          <button
            key={id}
            role="tab"
            aria-selected={on}
            onClick={() => onSelect(id)}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-[12.5px] transition-colors",
              on
                ? "bg-brand-primary font-bold text-white"
                : "font-medium text-brand-secondary hover:bg-brand-mist/50",
            )}
          >
            {label}
            {!!count && (
              <span
                className={cn(
                  "rounded px-1.5 py-px text-[10.5px] font-bold tabular-nums",
                  on ? "bg-white/20 text-white" : "bg-brand-mist/80 text-brand-gray",
                )}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ── Action button row ────────────────────────────────────────── */

export type ActionSpec = {
  label: string;
  onClick: () => void;
  variant?: "primary" | "secondary" | "ghost" | "done";
  disabled?: boolean;
};

const ACTION_CLASS: Record<string, string> = {
  primary:
    "bg-brand-ink text-white border-brand-ink hover:bg-brand-secondary hover:border-brand-secondary",
  secondary:
    "bg-brand-primary/10 text-brand-primary border-transparent hover:bg-brand-primary/20",
  ghost:
    "bg-brand-mist/50 text-brand-secondary border-transparent hover:bg-brand-mist",
  done: "bg-console-good/10 text-console-good border-transparent cursor-default",
};

export function Actions({ actions }: { actions: ActionSpec[] }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {actions.map((a) => (
        <button
          key={a.label}
          type="button"
          onClick={a.onClick}
          disabled={a.disabled || a.variant === "done"}
          className={cn(
            "inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-[12px] font-bold transition-colors disabled:opacity-100",
            ACTION_CLASS[a.variant ?? "primary"],
          )}
        >
          {a.label}
        </button>
      ))}
    </div>
  );
}

/* ── Evidence row — the cross-source context stack ────────────── */

export function EvidenceRow({
  source,
  label,
  excerpt,
  time,
  onClick,
}: {
  source: SourceKey;
  label: string;
  excerpt: string;
  time: string;
  onClick?: () => void;
}) {
  const interactive = typeof onClick === "function";
  return (
    <div
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      className={cn(
        "flex items-start gap-3 rounded-lg px-3 py-2.5",
        interactive &&
          "cursor-pointer transition-colors hover:bg-brand-mist/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/40",
      )}
    >
      <span className="mt-[7px]">
        <SourceDot source={source} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-2">
          <p className="text-[12.5px] font-bold text-brand-ink">{label}</p>
          <span className="text-[10.5px] uppercase tracking-[0.08em] text-brand-slate">
            {SOURCE_META[source].label}
          </span>
        </div>
        <p className="mt-0.5 text-[12px] leading-snug text-brand-secondary">{excerpt}</p>
      </div>
      <span className="flex-none text-[11px] tabular-nums text-brand-gray">{time}</span>
    </div>
  );
}

/* ── Glyph — the operating-queue status square ────────────────── */

export function Glyph({ icon, tone }: { icon: string; tone: Tone }) {
  return (
    <span
      className={cn(
        "grid h-5 w-5 flex-none place-items-center rounded-md text-[11px] font-bold",
        GLYPH_CLASS[tone],
      )}
      aria-hidden
    >
      {icon}
    </span>
  );
}

/* ── Key/value fact grid ──────────────────────────────────────── */

export function Facts({ facts }: { facts: [string, string][] }) {
  return (
    <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
      {facts.map(([k, v]) => (
        <div key={k} className="min-w-0">
          <dt className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-brand-slate">
            {k}
          </dt>
          {/* `break-words` because these carry addresses and Drive paths,
              which have no spaces to wrap on and otherwise widen the grid
              until the first column clips. */}
          <dd className="mt-0.5 break-words text-[12.5px] text-brand-secondary">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

/* ── Monospace-ish preview block for drafts and posts ─────────── */

export function DraftBlock({ text, label }: { text: string; label?: string }) {
  return (
    <div className="rounded-xl border border-brand-mist bg-brand-surface p-4">
      {label && (
        <p className="mb-2 text-[10.5px] font-bold uppercase tracking-[0.1em] text-brand-slate">
          {label}
        </p>
      )}
      <p className="whitespace-pre-wrap break-words text-[12.5px] leading-relaxed text-brand-secondary">
        {text}
      </p>
    </div>
  );
}

/* ── Section label ────────────────────────────────────────────── */

export function SectionLabel({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "text-[10.5px] font-bold uppercase tracking-[0.12em] text-brand-slate",
        className,
      )}
    >
      {children}
    </p>
  );
}

/* ── Empty state ──────────────────────────────────────────────── */

export function Empty({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-xl border border-dashed border-brand-mist bg-brand-surface px-4 py-8 text-center text-[12.5px] text-brand-gray">
      {children}
    </p>
  );
}

/* ── Menu — a light-themed picker ─────────────────────────────────
   Not a native <select>. The OS draws that popup, so it takes neither the
   hub's palette nor the per-option hint text and tone dots this needs — the
   same reason `ui/field-menu` exists for the dark intake forms. That control
   cannot be reused here: it is painted for the navy hero and would arrive as
   white-on-white inside a panel.

   Deliberately not a combobox. Both uses are closed sets of five to seven
   choices, so there is nothing to type and nothing to filter. */

export type MenuOption = {
  value: string;
  label: string;
  /** Second line, for what a choice actually means. */
  hint?: string;
  /** Dot colour, so status choices read at the same glance as their pills. */
  tone?: Tone;
  /** Trailing count, for the queues. */
  count?: number;
};

export function Menu({
  trigger,
  value,
  options,
  onChange,
  ariaLabel,
  className,
}: {
  trigger: ReactNode;
  value: string;
  options: MenuOption[];
  onChange: (value: string) => void;
  ariaLabel: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useDismiss(open, () => setOpen(false));

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <button
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg border px-2.5 py-1.5 text-[11.5px] font-bold transition-colors",
          open
            ? "border-brand-primary/40 bg-brand-primary/[0.07] text-brand-primary"
            : "border-brand-mist bg-white text-brand-secondary hover:border-brand-stone hover:bg-brand-surface",
        )}
      >
        {trigger}
        <ChevronDown
          className={cn("h-3.5 w-3.5 flex-none transition-transform", open && "rotate-180")}
          aria-hidden
        />
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label={ariaLabel}
          className="absolute right-0 top-[calc(100%+6px)] z-50 w-[248px] overflow-hidden rounded-xl border border-brand-mist bg-white py-1 shadow-[0_18px_40px_-14px_rgba(34,30,23,0.30)]"
        >
          {options.map((o) => {
            const on = o.value === value;
            return (
              <li key={o.value}>
                <button
                  type="button"
                  role="option"
                  aria-selected={on}
                  onClick={() => {
                    setOpen(false);
                    /* No-op on re-picking the current value: the toast would
                       claim a change that did not happen. */
                    if (!on) onChange(o.value);
                  }}
                  className={cn(
                    "flex w-full items-start gap-2 px-3 py-2 text-left transition-colors",
                    on ? "bg-brand-primary/[0.07]" : "hover:bg-brand-mist/50",
                  )}
                >
                  {o.tone && (
                    <span
                      className={cn(
                        "mt-[5px] h-2 w-2 flex-none rounded-full",
                        GLYPH_CLASS[o.tone],
                      )}
                      aria-hidden
                    />
                  )}
                  <span className="min-w-0 flex-1">
                    <span
                      className={cn(
                        "block truncate text-[12.5px] font-bold",
                        on ? "text-brand-primary" : "text-brand-ink",
                      )}
                    >
                      {o.label}
                    </span>
                    {o.hint && (
                      <span className="mt-0.5 block text-[11px] leading-snug text-brand-gray">
                        {o.hint}
                      </span>
                    )}
                  </span>
                  {typeof o.count === "number" && (
                    <span className="mt-px flex-none rounded bg-brand-mist/80 px-1.5 py-px text-[10.5px] font-bold tabular-nums text-brand-gray">
                      {o.count}
                    </span>
                  )}
                  {on && (
                    <Check
                      className="mt-0.5 h-3.5 w-3.5 flex-none text-brand-primary"
                      aria-hidden
                    />
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
