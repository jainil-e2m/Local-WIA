import { AI_ASSISTANTS } from "@/data/auditIntake";
import { labelClass, RequiredMark } from "./fields";

/**
 * Which AI assistants the Presence Checker should query.
 *
 * At least one is required. An empty `llm_eval_targets` means "every target" to
 * the backend, so silently sending nothing would run a far larger audit than the
 * form appears to describe — the form refuses instead.
 */
export function AiAssistantPicker({
  idPrefix,
  selected,
  onChange,
  disabled,
  invalid,
}: {
  idPrefix: string;
  selected: string[];
  onChange: (selected: string[]) => void;
  disabled?: boolean;
  /** Set once submit has been attempted with nothing selected. */
  invalid?: boolean;
}) {
  const errorId = `${idPrefix}-assistants-error`;
  const chosen = new Set(selected);

  const toggle = (id: string) =>
    onChange(chosen.has(id) ? selected.filter((value) => value !== id) : [...selected, id]);

  return (
    <fieldset disabled={disabled} className="min-w-0">
      <legend className={labelClass}>
        AI Platforms to evaluate
        <RequiredMark />
      </legend>

      {/* flex-wrap is kept deliberately: the row is sized to fit on one line at the
          form's full width, but must still fold on a narrow phone viewport. */}
      <div
        className="flex flex-wrap gap-1.5"
        role="group"
        aria-label="AI Platforms to evaluate"
        aria-invalid={invalid || undefined}
        aria-describedby={invalid ? errorId : undefined}
      >
        {AI_ASSISTANTS.map((assistant) => {
          const isSelected = chosen.has(assistant.id);
          /* One branch per state rather than a selected/unselected pair with the
             invalid classes appended: two `border-*` utilities on one element have
             equal specificity, so which wins depends on their order in the built
             stylesheet, not in this string. */
          /* Selected borrows the primary Button's treatment (see ui/button.tsx):
             solid brand-orange, white content, the same drop glow and hover lift.
             `border-2` is on every state so the pill does not resize when picked. */
          const stateClass = invalid
            ? // `invalid` is only set when nothing is selected, so every pill is off.
              "border-red-400/70 bg-white/[0.06] text-white/55"
            : isSelected
              ? "border-brand-orange bg-brand-orange text-white shadow-[0_12px_30px_-10px_rgba(246,157,47,0.55)] hover:-translate-y-0.5"
              : "border-white/15 bg-white/[0.06] text-white/55 hover:border-white/30 hover:text-white/80";

          return (
            <button
              key={assistant.id}
              type="button"
              aria-pressed={isSelected}
              onClick={() => toggle(assistant.id)}
              /* Horizontal padding is tuned so all five pills sit on one line
                 inside the form's max-w-xl (576px): measured at Inter 13px bold,
                 the row needs 541px at px-3, against 649px at px-5. Widening the
                 padding, the gaps, or a label will wrap Gemini onto its own row. */
              className={`inline-flex items-center gap-1.5 rounded-full border-2 px-3 py-2.5 text-[13px] font-bold tracking-[0.06em] transition-all duration-300 disabled:cursor-not-allowed disabled:opacity-40 ${stateClass}`}
            >
              {assistant.label}
              {/* Decorative: the label already names the assistant, so a second
                  reading of it would be noise.

                  On the orange fill the marks are forced white rather than left in
                  brand colour — Claude's mark is itself orange and would disappear
                  into the fill, and Gemini's four-colour star clashes with it.
                  White throughout matches the label and keeps all five legible. */}
              <img
                src={assistant.logo}
                alt=""
                aria-hidden
                className={`h-4 w-auto shrink-0 transition-all ${
                  isSelected ? "brightness-0 invert" : "opacity-40 grayscale"
                }`}
              />
            </button>
          );
        })}
      </div>

      {invalid && (
        <p id={errorId} role="alert" className="mt-2 text-xs text-red-300">
          Pick at least one platform to evaluate.
        </p>
      )}
    </fieldset>
  );
}
