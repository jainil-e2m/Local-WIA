import React, { useCallback, useState } from "react";
import { createPortal } from 'react-dom';
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useQueries, useQuery } from "@tanstack/react-query";
import { queryKey, useApiQuery } from "../api/query";
import { apiGet } from '../api/routes';
import type { SavedSchedule } from '../api/types';
import { calendarEntries, civilFields, monthRange } from "../utils/production";
import { ContentCalendar } from "./ContentCalendar";
import { paths } from "../app/routes";
import { ErrorState, LoadingState } from "./shared/states";
import { CalendarPublication, publicationUnavailable } from './PiecePublication';

type Month = { year: number; month: number };

/** `?month=2026-10` as a month (January is 0), or null when it is absent or not a month. */
export function parseMonth(value: string | null): Month | null {
  const match = /^(\d{4})-(0[1-9]|1[0-2])$/.exec(value ?? "");
  return match ? { year: Number(match[1]), month: Number(match[2]) - 1 } : null;
}
export const formatMonth = ({ year, month }: Month) => `${year}-${String(month + 1).padStart(2, "0")}`;

/** The saved calendar. The month is in the query string (`?month=2026-10`), so a refresh or a shared link shows the same
    thing. An entry opens its content pack's page; an earlier link with `?pack=...` goes there too. */
export function BackendCalendar({ query = "" }: { query?: string }) {
  const [search, setSearch] = useSearchParams();
  const config = useApiQuery("/calendar/config", undefined, { staleTime: 30_000 });
  const zone = config.data?.display_timezone;
  const current = parseMonth(search.get("month"));
  const today = zone ? civilFields(new Date(), zone).date : null;
  const month = current ?? (today ? { year: Number(today.slice(0, 4)), month: Number(today.slice(5, 7)) - 1 } : null);
  const range = zone && month && config.data?.enabled ? monthRange(month.year, month.month, zone) : null;
  const entries = useQuery({
    queryKey: queryKey("/calendar", range),
    queryFn: ({ signal }) => calendarEntries(range!.from, range!.to, signal),
    enabled: !!range,
    refetchInterval: 30_000,
  });
  const [publication, setPublication] = useState<SavedSchedule | null>(null);
  const [message, setMessage] = useState('');
  // One cached detail read per pack, shared with the pack page. Calendar schedules do not contain publication marks.
  const packIds = [...new Set((entries.data ?? []).map(entry => entry.pack_id))];
  const packs = useQueries({ queries: packIds.map(pack_id => ({
    queryKey: queryKey('/packs/{pack_id}', { path: { pack_id } }),
    queryFn: ({ signal }: { signal: AbortSignal }) => apiGet('/packs/{pack_id}', { path: { pack_id } }, { signal }),
    staleTime: 5_000,
    refetchInterval: 30_000,
  })) });
  const packById = new Map(packIds.map((id, index) => [id, packs[index].data]));
  const publicationByEntry = Object.fromEntries((entries.data ?? []).flatMap(entry => {
    const piece = packById.get(entry.pack_id)?.pieces.find(piece => piece.key === entry.slot_key);
    const published = entry.publication || entry.effective_status === 'published' || piece?.published.length;
    return published ? [[entry.calendar_entry_id, entry.format === 'email' ? 'Sent' as const : 'Published' as const]] : [];
  }));
  const changed = useCallback(
    (value: Month) => {
      if (formatMonth(value) === search.get("month")) return;
      setSearch((prev) => { const next = new URLSearchParams(prev); next.set("month", formatMonth(value)); return next; }, { replace: true });
    },
    [search, setSearch],
  );
  const navigate = useNavigate();
  const packId = search.get("pack");
  const disabled = config.data && !config.data.enabled ? "The backend calendar is not enabled yet." : "";
  const error = config.error?.message || disabled || entries.error?.message || "";
  const loading = (config.isPending && !config.error) || (!!range && entries.isPending && !entries.error);
  return (
    <div className="space-y-3">
      {loading && <LoadingState>Loading saved calendar…</LoadingState>}
      {error && <ErrorState message={error} onRetry={() => { void config.refetch(); void entries.refetch(); }} />}
      {config.data && month && (
        <ContentCalendar
          entries={error ? [] : entries.data ?? []}
          timezone={config.data.display_timezone}
          query={query}
          initialMonth={month}
          onMonthChange={changed}
          onOpenEntry={(entry) => navigate(`${paths.studioPack(entry.pack_id)}?piece=${encodeURIComponent(entry.slot_key)}`)}
          publicationByEntry={publicationByEntry}
          onMarkPublished={entry => { setMessage(''); setPublication(entry); }}
          canMarkEntry={entry => {
            const pack = packById.get(entry.pack_id);
            const piece = pack?.pieces.find(piece => piece.key === entry.slot_key);
            return !!pack && !!piece && !publicationUnavailable(pack, piece);
          }}
        />
      )}
      {message && <p role="status" className="text-[12px] text-emerald-700">{message}</p>}
      {publication && createPortal(<CalendarPublication packId={publication.pack_id} pieceKey={publication.slot_key}
        onClose={() => setPublication(null)} onSaved={() => setMessage(`${publication.title} marked ${publication.format === 'email' ? 'sent' : 'published'}.`)} />, document.body)}
      {packId && <Navigate to={paths.studioPack(packId)} replace />}
    </div>
  );
}
