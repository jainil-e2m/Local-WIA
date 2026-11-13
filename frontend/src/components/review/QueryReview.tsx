import { Plus, RotateCcw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  addRowButtonClass,
  compactInputClass,
  labelClass,
  rowButtonClass,
} from "@/components/intake/fields";
import {
  defaultAddSectionIndex,
  flattenQuerySections,
  QUERY_FETCH_STATUS,
  type QueryFetchStatus,
  type QuerySection,
} from "@/lib/queryReview";

/**
 * The query-review gate for an AI Presence run.
 *
 * The run stops after generating its query set and does not evaluate anything
 * until this is confirmed, so the screen has to be editable, not a summary: the
 * set that leaves here is the set that gets audited.
 *
 * Presented as one flat list of every query, add/edit/remove in place. The
 * generator still works in seven intent aspects and the service still requires
 * an aspect per query, but that is a pipeline detail with nothing to offer a
 * reviewer, so it is not surfaced — see flattenQuerySections.
 */
export function QueryReview({
  sections,
  total,
  fetchStatus,
  error,
  confirming,
  onRetry,
  onAddQuery,
  onUpdateQueryText,
  onRemoveQuery,
  onConfirm,
}: {
  sections: QuerySection[];
  total: number;
  fetchStatus: QueryFetchStatus;
  error: string;
  confirming: boolean;
  onRetry: () => void;
  onAddQuery: (sectionIndex: number) => void;
  onUpdateQueryText: (sectionIndex: number, queryIndex: number, text: string) => void;
  onRemoveQuery: (sectionIndex: number, queryIndex: number) => void;
  onConfirm: () => void;
}) {
  if (fetchStatus === QUERY_FETCH_STATUS.LOADING || fetchStatus === QUERY_FETCH_STATUS.IDLE) {
    return (
      <div className="mx-auto max-w-2xl py-10 text-center">
        <span className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.2em] text-brand-teal">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-teal animate-pulse-ring" aria-hidden />
          Preparing your query set
        </span>
        <p className="mt-4 text-[15px] text-white/55">Loading the generated queries…</p>
      </div>
    );
  }

  if (fetchStatus === QUERY_FETCH_STATUS.ERROR) {
    return (
      <div className="mx-auto max-w-2xl py-10 text-center">
        <h2 className="text-2xl font-extrabold tracking-tight">Queries not ready</h2>
        <p className="mt-2 text-[15px] text-white/55">{error}</p>
        <Button variant="ghost" size="sm" onClick={onRetry} className="mt-6">
          <RotateCcw className="h-4 w-4" />
          Try again
        </Button>
      </div>
    );
  }

  const canConfirm = total > 0 && !confirming;
  // One continuous list. The aspect sections still exist underneath — they carry
  // aspect_key into the confirm payload — but they are not a layout here.
  const rows = flattenQuerySections(sections);

  return (
    <div className="mx-auto max-w-2xl">
      <div className="text-center">
        <span className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.2em] text-brand-orange">
          Action needed
        </span>
        <h2 className="mt-3 text-2xl font-extrabold tracking-tight">Review the query set</h2>
        <p className="mt-2 text-[15px] text-white/55">
          These are the prompts each AI platform will be asked. Edit, remove or add before running —
          {" "}
          <span className="font-semibold text-white/80">{total}</span> will be evaluated.
        </p>
      </div>

      <fieldset disabled={confirming} className="mt-8 min-w-0">
        <legend className={labelClass}>
          Queries <span className="text-white/30">({rows.length})</span>
        </legend>

        {rows.length > 0 && (
          <div className="space-y-2">
            {rows.map(({ sectionIndex, queryIndex, query }, rowIndex) => (
              <div
                // Falls back to the position only when a row has no number,
                // which the numbering rule normally prevents.
                key={query.query_number ?? `row-${rowIndex}`}
                className="flex items-start gap-2 sm:gap-3"
              >
                <span
                  aria-hidden
                  className="w-6 shrink-0 pt-2 text-right text-[12px] font-semibold tabular-nums text-white/30"
                >
                  {rowIndex + 1}
                </span>
                <input
                  type="text"
                  aria-label={`Query ${rowIndex + 1}`}
                  value={query.query_text ?? ""}
                  onChange={(event) =>
                    onUpdateQueryText(sectionIndex, queryIndex, event.target.value)
                  }
                  placeholder="Enter a query…"
                  className={`${compactInputClass} min-w-0 flex-1`}
                />
                <button
                  type="button"
                  onClick={() => onRemoveQuery(sectionIndex, queryIndex)}
                  aria-label={`Remove query ${rowIndex + 1}`}
                  className={`${rowButtonClass} hover:border-red-400/50 hover:text-red-300`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        <button
          type="button"
          onClick={() => onAddQuery(defaultAddSectionIndex(sections))}
          className={`${addRowButtonClass} ${rows.length > 0 ? "mt-2" : ""}`}
        >
          <Plus className="h-4 w-4" />
          Add a query
        </button>
      </fieldset>

      {error && (
        <p role="alert" className="mt-6 text-center text-sm text-red-300">
          {error}
        </p>
      )}

      <div className="mt-9 flex flex-col items-center gap-3">
        <Button type="button" onClick={onConfirm} disabled={!canConfirm}>
          {confirming ? "Confirming…" : `Confirm ${total} ${total === 1 ? "query" : "queries"}`}
        </Button>
        <p className="text-center text-xs text-white/35">
          {total === 0
            ? "Add at least one query to start the evaluation."
            : "Confirming starts the evaluation. Removed queries are not kept."}
        </p>
      </div>
    </div>
  );
}
