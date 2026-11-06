/**
 * Chrome shared by every control on the audit intake form. Kept in one place so
 * the panel and its repeaters cannot drift into two slightly different inputs.
 */

const inputBaseClass =
  "w-full rounded-xl border border-white/15 bg-white/[0.06] px-4 text-[15px] text-white placeholder:text-white/35 outline-none transition-colors focus:border-brand-sky/60 focus:bg-white/[0.09] disabled:cursor-not-allowed disabled:opacity-40";

/** The primary intake fields. */
export const inputClass = `${inputBaseClass} py-3.5`;

/**
 * Repeater rows sit tighter than the fields above them: a 24px line box plus 3px
 * above and below, so a row is 32px tall including its border. Every control in
 * the row (platform trigger, URL, delete, add) is built to that same 32px so they
 * line up.
 */
export const COMPACT_ROW_PADDING = "py-[3px] leading-6";
export const COMPACT_ROW_HEIGHT = "h-8";
export const compactInputClass = `${inputBaseClass} ${COMPACT_ROW_PADDING}`;

export const invalidInputClass = "border-red-400/70 focus:border-red-400";

export const labelClass =
  "mb-2 block text-[11px] font-bold uppercase tracking-[0.14em] text-white/55";

export const hintClass = "mt-2 text-xs text-white/35";

/** Square 32px control that ends a repeater row (remove, confirm). */
export const rowButtonClass = `grid ${COMPACT_ROW_HEIGHT} w-9 shrink-0 place-items-center rounded-xl border border-white/15 bg-white/[0.06] text-white/50 transition-colors`;

/** Dashed "add another row" affordance. */
export const addRowButtonClass = `inline-flex ${COMPACT_ROW_HEIGHT} items-center gap-2 rounded-xl border border-dashed border-white/20 px-4 text-[13px] font-semibold text-white/60 transition-colors hover:border-brand-sky/50 hover:text-white/90 disabled:cursor-not-allowed disabled:opacity-40`;

/** Marks a field the form refuses to submit without. */
export function RequiredMark() {
  // aria-hidden because the control's own `required` is what assistive tech
  // announces; a read-out "star" on top of that is noise.
  return (
    <span className="ml-0.5 text-red-400" aria-hidden>
      *
    </span>
  );
}
