import React, { useCallback, useEffect, useState } from "react";
import { CalendarConfig, SavedSchedule } from "../types/production";
import { storageRequest } from "../utils/weeklyStorage";
import { calendarEntries, civilFields, monthRange } from "../utils/production";
import { ContentCalendar } from "./ContentCalendar";
import { StoredPackDetail } from "./StoredPacks";

export function BackendCalendar({ query = "" }: { query?: string }) {
  const [config, setConfig] = useState<CalendarConfig | null>(null),
    [entries, setEntries] = useState<SavedSchedule[]>([]);
  const [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [reload, setReload] = useState(0);
  const [month, setMonth] = useState<{ year: number; month: number } | null>(
    null,
  );
  const [selected, setSelected] = useState<SavedSchedule | null>(null);
  const changed = useCallback(
    (value: { year: number; month: number }) =>
      setMonth((old) =>
        old?.year === value.year && old?.month === value.month ? old : value,
      ),
    [],
  );
  useEffect(() => {
    let active = true;
    setLoading(true);
    storageRequest<CalendarConfig>("/calendar/config")
      .then(async (c) => {
        if (!active) return;
        setConfig(c);
        if (!c.enabled)
          throw new Error("The backend calendar is not enabled yet.");
        const date = civilFields(new Date(), c.display_timezone).date;
        const current = month || {
          year: Number(date.slice(0, 4)),
          month: Number(date.slice(5, 7)) - 1,
        };
        const range = monthRange(
          current.year,
          current.month,
          c.display_timezone,
        );
        const result = await calendarEntries(range.from, range.to);
        if (active) {
          setEntries(result);
          setError("");
        }
      })
      .catch((e) => {
        if (active) {
          setEntries([]);
          setError(e.message);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [month, reload]);
  useEffect(() => {
    const refresh = () => setReload((v) => v + 1);
    const timer = window.setInterval(refresh, 30000);
    window.addEventListener("focus", refresh);
    window.addEventListener("atelier-production-changed", refresh);
    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", refresh);
      window.removeEventListener("atelier-production-changed", refresh);
    };
  }, []);
  return (
    <div className="space-y-3">
      {loading && (
        <p role="status" className="text-sm text-slate-500">
          Loading saved calendar…
        </p>
      )}
      {error && (
        <div role="alert" className="rounded-xl bg-amber-50 p-4">
          {error}
          <button
            className="ml-4 underline"
            onClick={() => setReload((v) => v + 1)}
          >
            Retry
          </button>
        </div>
      )}
      {!loading && !error && !entries.length && (
        <p className="rounded-xl border border-dashed p-4 text-sm">
          No scheduled content in this month.
        </p>
      )}
      {config && (
        <ContentCalendar
          entries={entries}
          timezone={config.display_timezone}
          query={query}
          onMonthChange={changed}
          onOpenEntry={setSelected}
        />
      )}
      {selected && (
        <StoredPackDetail
          packId={selected.pack_id}
          assetId={selected.asset_id}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
