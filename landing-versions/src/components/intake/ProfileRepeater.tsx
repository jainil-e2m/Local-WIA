import { useRef } from "react";
import { Plus, Trash2 } from "lucide-react";
import { SelectMenu } from "@/components/ui/field-menu";
import { profileUrlError, type ProfileOption } from "@/data/auditIntake";
import {
  addRowButtonClass,
  compactInputClass,
  hintClass,
  invalidInputClass,
  labelClass,
  rowButtonClass,
} from "./fields";
import type { ProfileRow } from "./rows";

/**
 * A list of "platform + URL" rows where each platform may appear at most once.
 *
 * Used for both social profiles and the real-estate platforms AI Presence asks
 * about. The one-per-platform rule is structural rather than a check that could
 * be bypassed: a platform already claimed by a row cannot be chosen again.
 */
export function ProfileRepeater({
  idPrefix,
  noun,
  legend,
  options,
  rows,
  onRowsChange,
  disabled,
}: {
  /** Namespaces the generated element ids within the page. */
  idPrefix: string;
  /** Names the row kind in labels and hints — "Social", "Real estate". */
  noun: string;
  legend: string;
  options: readonly ProfileOption[];
  rows: ProfileRow[];
  onRowsChange: (rows: ProfileRow[]) => void;
  disabled?: boolean;
}) {
  const nextRowId = useRef(0);

  const claimed = new Set(rows.map((row) => row.platform));
  const unclaimed = options.filter((option) => !claimed.has(option.id));

  const addRow = () => {
    const next = unclaimed[0];
    if (!next) return;
    onRowsChange([
      ...rows,
      { id: nextRowId.current++, platform: next.id, url: "", touched: false },
    ]);
  };

  const updateRow = (id: number, patch: Partial<Omit<ProfileRow, "id">>) =>
    onRowsChange(rows.map((row) => (row.id === id ? { ...row, ...patch } : row)));

  const removeRow = (id: number) => onRowsChange(rows.filter((row) => row.id !== id));

  return (
    <fieldset disabled={disabled} className="min-w-0">
      <legend className={labelClass}>
        {legend} <span className="text-white/30">(optional)</span>
      </legend>

      {rows.length > 0 && (
        <div className="space-y-3">
          {rows.map((row, index) => {
            const platform = options.find((option) => option.id === row.platform);
            const error = profileUrlError(options, row.platform, row.url);
            const showError = row.touched && Boolean(error);
            const errorId = `${idPrefix}-${row.id}-error`;

            return (
              <div key={row.id}>
                <div className="flex items-start gap-2 sm:gap-3">
                  <SelectMenu
                    ariaLabel={`${noun} platform ${index + 1}`}
                    value={row.platform}
                    options={options.map((option) => ({
                      value: option.id,
                      label: option.label,
                      // Claimed elsewhere — one URL per platform.
                      disabled: option.id !== row.platform && claimed.has(option.id),
                    }))}
                    onChange={(next) =>
                      updateRow(row.id, {
                        platform: next,
                        // The URL is re-judged against the new platform, so hide a
                        // stale message until this row is blurred again.
                        touched: false,
                      })
                    }
                    compact
                    className="w-[42%] shrink-0 sm:w-[38%]"
                  />

                  <input
                    type="text"
                    inputMode="url"
                    aria-label={`${platform?.label ?? noun} profile URL`}
                    aria-invalid={showError || undefined}
                    aria-describedby={showError ? errorId : undefined}
                    value={row.url}
                    onChange={(event) => updateRow(row.id, { url: event.target.value })}
                    onBlur={() => updateRow(row.id, { touched: true })}
                    placeholder={platform?.example}
                    className={`${compactInputClass} min-w-0 flex-1 ${showError ? invalidInputClass : ""}`}
                  />

                  <button
                    type="button"
                    onClick={() => removeRow(row.id)}
                    aria-label={`Remove ${platform?.label ?? noun} profile`}
                    className={`${rowButtonClass} hover:border-red-400/50 hover:text-red-300`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                {showError && (
                  <p id={errorId} role="alert" className="mt-1.5 text-xs text-red-300">
                    {error}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      <button
        type="button"
        onClick={addRow}
        disabled={disabled || unclaimed.length === 0}
        className={`${addRowButtonClass} ${rows.length > 0 ? "mt-3" : ""}`}
      >
        <Plus className="h-4 w-4" />
        {rows.length === 0 ? `Add a ${noun.toLowerCase()} profile` : "Add another"}
      </button>

      <p className={hintClass}>
        {unclaimed.length === 0
          ? "Every supported platform has been added."
          : "One profile per platform."}
      </p>
    </fieldset>
  );
}
