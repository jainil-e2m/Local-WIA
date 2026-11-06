import {
  useEffect,
  useMemo,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from "react";
import { Check, ChevronDown } from "lucide-react";
import { useDismiss } from "@/hooks/useDismiss";

/**
 * Two themed replacements for form controls whose native popups cannot be styled.
 *
 * A native `<select>` renders its option list with the operating system, not the
 * page: on a dark theme the list keeps the OS's white background while inheriting
 * the white text from the control, so every option is invisible until hovered.
 * There is no CSS fix — the list is not in the document. Both controls here draw
 * their own list, so it inherits the app's palette.
 *
 *   SelectMenu — a closed set of choices, no typing (the social platform picker).
 *   ComboboxField — free text with suggestions (country / state / city), where a
 *     value the list does not contain is still valid.
 */

/** Shared trigger/input chrome, matching the intake form's text inputs. */
const CONTROL_CLASS =
  "w-full rounded-xl border border-white/15 bg-white/[0.06] text-[15px] text-white outline-none transition-colors focus:border-brand-sky/60 focus:bg-white/[0.09] disabled:cursor-not-allowed disabled:opacity-40";

/**
 * Popup panel. The background must be OPAQUE — a translucent `white/x` fill lets
 * the page's text show through the list. This literal sits between the hero
 * gradient's `#202a72` and `#141a45` (see `.bg-hero` in index.css); the brand
 * palette has no navy token to reference.
 */
const PANEL_CLASS =
  "absolute left-0 right-0 top-[calc(100%+6px)] z-50 overflow-hidden rounded-xl border border-white/15 bg-[#1a2250] shadow-[0_20px_44px_-12px_rgba(0,0,0,0.75)]";

/** Rows sized to the text plus ~3px of breathing room, so the list stays compact. */
const OPTION_CLASS =
  "flex w-full cursor-pointer items-center justify-between gap-2 px-3.5 py-[3px] text-left text-[14px] leading-6 transition-colors";

export interface SelectMenuOption {
  value: string;
  label: string;
  /** Rendered dimmed and unselectable — used for a platform another row claimed. */
  disabled?: boolean;
}

export function SelectMenu({
  value,
  options,
  onChange,
  disabled,
  ariaLabel,
  className = "",
  compact = false,
}: {
  value: string;
  options: readonly SelectMenuOption[];
  onChange: (value: string) => void;
  disabled?: boolean;
  ariaLabel: string;
  className?: string;
  /** Trigger sized to the text plus ~3px, for dense repeated rows. */
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useDismiss(open, () => setOpen(false));
  const selected = options.find((option) => option.value === value);

  const choose = (option: SelectMenuOption) => {
    if (option.disabled) return;
    onChange(option.value);
    setOpen(false);
  };

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        type="button"
        role="combobox"
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-haspopup="listbox"
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
        className={`${CONTROL_CLASS} flex items-center justify-between gap-2 px-3.5 ${
          compact ? "py-[3px] leading-6" : "py-3.5"
        }`}
      >
        <span className="truncate">{selected?.label ?? "Select"}</span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-white/45 transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden
        />
      </button>

      {open && (
        <ul role="listbox" aria-label={ariaLabel} className={`${PANEL_CLASS} py-1`}>
          {options.map((option) => {
            const isSelected = option.value === value;
            return (
              <li key={option.value}>
                <button
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  // aria-disabled, not the `disabled` attribute: a disabled
                  // button is removed from the accessibility tree and stops
                  // firing events, so the "already added" reason would be
                  // invisible to both screen readers and hover.
                  aria-disabled={option.disabled || undefined}
                  onClick={() => choose(option)}
                  title={option.disabled ? "Already added" : undefined}
                  className={`${OPTION_CLASS} ${
                    option.disabled
                      ? "cursor-not-allowed text-white/25"
                      : isSelected
                        ? "bg-white/[0.12] text-white"
                        : "text-white/75 hover:bg-white/[0.08] hover:text-white"
                  }`}
                >
                  <span className="truncate">{option.label}</span>
                  {isSelected && <Check className="h-3.5 w-3.5 shrink-0 text-brand-teal" aria-hidden />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export interface ComboboxSuggestion {
  /** Written into the field on selection. */
  value: string;
  /** Shown in the list — may add context the value omits ("Austin, Texas, US"). */
  label: string;
  /** Distinguishes same-named places (two Springfields) as a React key. */
  key: string;
  /**
   * Caller-owned payload handed back by `onSelect`, for values that should also
   * populate sibling fields — picking "Matthews, North Carolina" fills the state
   * too. It travels *with* the suggestion rather than being re-derived from
   * `value`, because a name alone is ambiguous: several states have a Springfield,
   * so a lookup by name could fill in the wrong one.
   */
  data?: Record<string, string>;
}

/**
 * Text input with a suggestion list, for a value that is *usually* one of a known
 * set. Typed text is always kept: the caller's dataset does not know every place
 * name, and refusing an unlisted one would block a legitimate audit.
 */
export function ComboboxField({
  id,
  value,
  suggestions,
  onChange,
  onSelect,
  placeholder,
  required,
  disabled,
  emptyHint,
}: {
  id: string;
  value: string;
  suggestions: readonly ComboboxSuggestion[];
  onChange: (value: string) => void;
  onSelect: (suggestion: ComboboxSuggestion) => void;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  /** Shown when typing matches nothing, to signal free text is accepted. */
  emptyHint?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const rootRef = useDismiss(open, () => setOpen(false));

  const listId = `${id}-suggestions`;
  const showList = open && (suggestions.length > 0 || Boolean(emptyHint));

  // Reset the highlight whenever the candidate set changes, so Enter can never
  // commit a suggestion that has scrolled out of the list.
  const suggestionKeys = useMemo(() => suggestions.map((s) => s.key).join("|"), [suggestions]);
  useEffect(() => setActiveIndex(-1), [suggestionKeys]);

  const commit = (suggestion: ComboboxSuggestion) => {
    onSelect(suggestion);
    setOpen(false);
    setActiveIndex(-1);
  };

  const onKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (!suggestions.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((prev) => (prev + 1) % suggestions.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((prev) => (prev <= 0 ? suggestions.length - 1 : prev - 1));
    } else if (event.key === "Enter") {
      // Only intercept Enter when a row is highlighted; otherwise let it submit
      // the form as usual.
      const target = activeIndex >= 0 ? suggestions[activeIndex] : undefined;
      if (target) {
        event.preventDefault();
        commit(target);
      }
    } else if (event.key === "Tab" && activeIndex >= 0) {
      commit(suggestions[activeIndex]);
    }
  };

  return (
    <div ref={rootRef} className="relative">
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={showList}
        aria-controls={showList ? listId : undefined}
        aria-autocomplete="list"
        autoComplete="off"
        value={value}
        required={required}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(event) => {
          onChange(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        className={`${CONTROL_CLASS} px-4 py-3.5 placeholder:text-white/35`}
      />

      {showList && (
        <ul id={listId} role="listbox" className={`${PANEL_CLASS} max-h-56 overflow-y-auto py-1`}>
          {suggestions.map((suggestion, index) => (
            <li key={suggestion.key}>
              <button
                type="button"
                // role/aria-selected belong on the focusable element, not the
                // wrapping <li> — an option must not contain an interactive
                // child, and a pointer press has to land on the handler itself.
                role="option"
                aria-selected={index === activeIndex}
                // onMouseDown, not onClick: the input's blur would otherwise close
                // the list before the click landed.
                onMouseDown={(event) => {
                  event.preventDefault();
                  commit(suggestion);
                }}
                onMouseEnter={() => setActiveIndex(index)}
                className={`${OPTION_CLASS} ${
                  index === activeIndex
                    ? "bg-white/[0.12] text-white"
                    : "text-white/75 hover:text-white"
                }`}
              >
                <span className="truncate">{suggestion.label}</span>
              </button>
            </li>
          ))}
          {suggestions.length === 0 && emptyHint && (
            <li className="px-3.5 py-[3px] text-[13px] leading-6 text-white/40">{emptyHint}</li>
          )}
        </ul>
      )}
    </div>
  );
}
