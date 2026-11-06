import React, { useState } from 'react';
import type { StoredWeek } from '../../api/schema';
import { useApiQuery } from '../../api/query';
import { weekLabel } from '../../utils/editorialWeeks';

/* The week pickers (the Weekly Studio's ideas and briefs, Content Packs). GET /weeks answers the live weeks only: a week whose
   cards, briefs and packs were superseded, or did not meet WIA's standard, is archived, never deleted (backend
   week_archive.py). A small toggle reads `?include_archived=true` and marks the archived weeks as such. */

export const ARCHIVED = 'archived';
export const isArchived = (week: Pick<StoredWeek, 'status'> | null | undefined) => week?.status === ARCHIVED;

/** A week as its picker option says it: the dates it covers, and "(archived)" for an archived week. */
export const weekOption = (week: Pick<StoredWeek, 'week_start' | 'status'>) => `${weekLabel(week.week_start)}${isArchived(week) ? ' (archived)' : ''}`;

/** The stored weeks, live ones only unless the person asks for the archived ones too. */
export function useWeekList() {
  const [showArchived, setShowArchived] = useState(false);
  const weeks = useApiQuery('/weeks', showArchived ? { query: { include_archived: true } } : undefined);
  // The latest live week, which a screen opens when the URL names none, whether or not archived weeks are listed.
  const latest = weeks.data?.find(week => !isArchived(week))?.week_id ?? weeks.data?.[0]?.week_id ?? '';
  return { weeks, latest, showArchived, setShowArchived };
}

export function ArchivedWeeksToggle({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  return <label className="flex items-center gap-2 text-[12px] text-[#34445F]"><input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />Show archived weeks</label>;
}

/** The note an archived week's screen shows, so a person opening one by its link knows it is not current. */
export function ArchivedWeekNote({ week }: { week: Pick<StoredWeek, 'status'> | null | undefined }) {
  if (!isArchived(week)) return null;
  return <p role="note" className="rounded-xl bg-slate-100 p-3 text-sm text-slate-700">This week is archived: its work was superseded or did not meet the standard. It is kept as the record and left out of the week lists.</p>;
}
