import { useRef } from "react";
import { Plus, Trash2 } from "lucide-react";
import {
  addRowButtonClass,
  compactInputClass,
  invalidInputClass,
  labelClass,
  rowButtonClass,
} from "./fields";
import { competitorError, type CompetitorRow } from "./rows";

/**
 * Brands to compare the audited business against. Both halves of a row are
 * required by the API (`brandName` and `domainUrl` are each `min_length=1`), so a
 * half-filled row is caught here rather than rejected as a 422.
 */
export function CompetitorRepeater({
  idPrefix,
  rows,
  onRowsChange,
  disabled,
}: {
  idPrefix: string;
  rows: CompetitorRow[];
  onRowsChange: (rows: CompetitorRow[]) => void;
  disabled?: boolean;
}) {
  const nextRowId = useRef(0);

  const addRow = () =>
    onRowsChange([
      ...rows,
      { id: nextRowId.current++, brandName: "", domainUrl: "", touched: false },
    ]);

  const updateRow = (id: number, patch: Partial<Omit<CompetitorRow, "id">>) =>
    onRowsChange(rows.map((row) => (row.id === id ? { ...row, ...patch } : row)));

  const removeRow = (id: number) => onRowsChange(rows.filter((row) => row.id !== id));

  return (
    <fieldset disabled={disabled} className="min-w-0">
      <legend className={labelClass}>
        Competitors <span className="text-white/30">(optional)</span>
      </legend>

      {rows.length > 0 && (
        <div className="space-y-3">
          {rows.map((row, index) => {
            const error = competitorError(row);
            const showError = row.touched && Boolean(error);
            const errorId = `${idPrefix}-${row.id}-error`;
            const position = index + 1;

            return (
              <div key={row.id}>
                <div className="flex items-start gap-2 sm:gap-3">
                  <input
                    type="text"
                    aria-label={`Competitor ${position} brand name`}
                    aria-invalid={showError || undefined}
                    aria-describedby={showError ? errorId : undefined}
                    value={row.brandName}
                    onChange={(event) => updateRow(row.id, { brandName: event.target.value })}
                    onBlur={() => updateRow(row.id, { touched: true })}
                    placeholder="Competitor name"
                    className={`${compactInputClass} w-[42%] shrink-0 sm:w-[38%] ${showError ? invalidInputClass : ""}`}
                  />

                  <input
                    type="text"
                    inputMode="url"
                    aria-label={`Competitor ${position} domain`}
                    aria-invalid={showError || undefined}
                    aria-describedby={showError ? errorId : undefined}
                    value={row.domainUrl}
                    onChange={(event) => updateRow(row.id, { domainUrl: event.target.value })}
                    onBlur={() => updateRow(row.id, { touched: true })}
                    placeholder="competitor.com"
                    className={`${compactInputClass} min-w-0 flex-1 ${showError ? invalidInputClass : ""}`}
                  />

                  <button
                    type="button"
                    onClick={() => removeRow(row.id)}
                    aria-label={`Remove competitor ${position}`}
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
        disabled={disabled}
        className={`${addRowButtonClass} ${rows.length > 0 ? "mt-3" : ""}`}
      >
        <Plus className="h-4 w-4" />
        {rows.length === 0 ? "Add a competitor" : "Add another"}
      </button>
    </fieldset>
  );
}
