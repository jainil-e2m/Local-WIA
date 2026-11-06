import React, { useState } from 'react';
import { apiSend } from '../api/routes';
import { errorMessage } from '../api/client';
import { useApiQuery, useInvalidate } from '../api/query';
import { useMe } from '../utils/me';
import { WEEKDAYS, canChangeSettings, canReadSettings, fieldText, readSettings, settingInput, settingsView, type SettingRow } from '../utils/settings';
import { ErrorState, LoadingState } from './shared/states';
import { PageHeading } from './PageHeading';
import { DARK_BUTTON, FIELD, HEADING, LABEL, META, PANEL, StatusLine } from './AdminParts';
import { Select } from './ThemedSelect';

/* Settings, for the team members who may read them (an editor or an approver): the weekly schedule (day, hour, time zone) in
   one card, which an approver changes and saves together, and the weekly spending limits as a plain table (none at all with no
   weekly limits). The API has no
   version check on a setting, so after a save the screen says when someone else had changed a value since the page was
   read. */

const hour = (h: number) => `${String(h).padStart(2, '0')}:00`;
const SCHEDULE_KEYS = ['cycle.weekday', 'cycle.hour', 'cycle.timezone'] as const;
type ScheduleKey = typeof SCHEDULE_KEYS[number];
const LABELS: Record<ScheduleKey, string> = { 'cycle.weekday': 'Day', 'cycle.hour': 'Hour', 'cycle.timezone': 'Time zone' };

/** A value as it reads on the screen. */
export function valueText(key: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return 'Not set';
  if (key === 'cycle.weekday' && typeof value === 'number') return WEEKDAYS[value] ?? String(value);
  if (key === 'cycle.hour' && typeof value === 'number') return hour(value);
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
}

/** "Sunday at 04:00, America/Chicago". */
export const scheduleText = (values: Record<ScheduleKey, unknown>) =>
  `${valueText('cycle.weekday', values['cycle.weekday'])} at ${valueText('cycle.hour', values['cycle.hour'])}, ${valueText('cycle.timezone', values['cycle.timezone'])}`;

/** The weekly schedule: read-only for an editor; an approver changes the three values and saves them together. */
function ScheduleCard({ rows, canChange }: { rows: Record<ScheduleKey, SettingRow | undefined>; canChange: boolean }) {
  const invalidate = useInvalidate();
  const current = Object.fromEntries(SCHEDULE_KEYS.map(key => [key, fieldText(rows[key]?.value)])) as Record<ScheduleKey, string>;
  const [text, setText] = useState(current);
  // A newer value read from the server replaces a field's text, unless the person has typed something of their own.
  const [shown, setShown] = useState(current);
  if (SCHEDULE_KEYS.some(key => current[key] !== shown[key])) {
    setText(Object.fromEntries(SCHEDULE_KEYS.map(key => [key, text[key] === shown[key] ? current[key] : text[key]])) as Record<ScheduleKey, string>);
    setShown(current);
  }
  const [busy, setBusy] = useState(false);
  const [refusal, setRefusal] = useState('');
  const [saved, setSaved] = useState('');
  const values = Object.fromEntries(SCHEDULE_KEYS.map(key => [key, rows[key]?.value])) as Record<ScheduleKey, unknown>;
  if (!canChange) return <section aria-labelledby="settings-schedule" className={`${PANEL} p-6 space-y-2`}>
    <h2 id="settings-schedule" className={HEADING}>Weekly schedule</h2>
    <p className="text-[13px]">The week's collection closes and the cycle starts on {scheduleText(values)}.</p>
    <p className={META}>Only an approver can change it.</p>
  </section>;

  const changed = SCHEDULE_KEYS.filter(key => rows[key] && text[key] !== current[key]);
  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaved(''); setRefusal('');
    const inputs: [ScheduleKey, number | string][] = [];
    for (const key of changed) {
      const input = settingInput(key, text[key]);
      if ('error' in input) { setRefusal(input.error); return; }
      inputs.push([key, input.value]);
    }
    setBusy(true);
    const meanwhile: string[] = [];
    try {
      for (const [key, value] of inputs) {
        const result = await apiSend('put', '/settings/{key}', { path: { key }, body: { value } }) as { before?: unknown } | null;
        // No version check exists for a setting: when the value replaced is not the one this page showed, say so.
        if (result && result.before != null && fieldText(result.before) !== current[key]) meanwhile.push(`${LABELS[key].toLowerCase()} to ${valueText(key, result.before)}`);
      }
      const next = { ...values, ...Object.fromEntries(inputs) } as Record<ScheduleKey, unknown>;
      setSaved(`Saved: ${scheduleText(next)}.${meanwhile.length ? ` Someone had changed the ${meanwhile.join(' and the ')} since this page was read; your values replaced theirs.` : ''} The next run uses it.`);
      await invalidate('/settings', '/schedule');
    } catch (error) {
      // The backend's own words: a value it refuses (422) or a person who may not change settings (403).
      setRefusal(errorMessage(error, 'The schedule could not be saved. Try again.'));
    } finally {
      setBusy(false);
    }
  };
  return <form aria-label="Weekly schedule" onSubmit={e => void save(e)} className={`${PANEL} p-6 space-y-4`}>
    <div className="space-y-1">
      <h2 id="settings-schedule" className={HEADING}>Weekly schedule</h2>
      <p className={META}>When the week's collection closes and the weekly cycle starts.</p>
    </div>
    <div className="grid gap-4 sm:grid-cols-3">
      {rows['cycle.weekday'] && <label className={LABEL}>Day
        <Select className={FIELD} value={text['cycle.weekday']} onChange={e => setText({ ...text, 'cycle.weekday': e.target.value })}>{WEEKDAYS.map((day, i) => <option key={day} value={i}>{day}</option>)}</Select></label>}
      {rows['cycle.hour'] && <label className={LABEL}>Hour
        <Select className={FIELD} value={text['cycle.hour']} onChange={e => setText({ ...text, 'cycle.hour': e.target.value })}>{Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{hour(h)}</option>)}</Select></label>}
      {rows['cycle.timezone'] && <label className={LABEL}>Time zone
        <input className={FIELD} value={text['cycle.timezone']} placeholder="America/Chicago" onChange={e => setText({ ...text, 'cycle.timezone': e.target.value })} /></label>}
    </div>
    <div className="flex flex-wrap items-center gap-3">
      <button type="submit" className={DARK_BUTTON} disabled={busy || !changed.length}>{busy ? 'Saving…' : 'Save the schedule'}</button>
      <StatusLine tone="error">{refusal}</StatusLine>
      <StatusLine>{saved}</StatusLine>
    </div>
  </form>;
}

export function SettingsView() {
  const { me, loaded } = useMe();
  const canRead = canReadSettings(me);
  const canChange = canChangeSettings(me);
  const query = useApiQuery('/settings', undefined, { enabled: loaded && canRead });
  if (!loaded) return <LoadingState>Loading…</LoadingState>;
  if (!canRead) return <section role="status" className="space-y-3 py-10">
    <PageHeading title="Settings" />
    <p className="text-[13px] text-[#667184]">Settings are open to editors and approvers. Ask an approver if something here needs to change.</p>
  </section>;
  const listing = query.data === undefined ? null : readSettings(query.data);
  const view = listing ? settingsView(listing) : null;
  return <section className="space-y-5 pb-12">
    <PageHeading title="Settings" subtitle={view?.uncapped ? 'The weekly schedule' : 'The weekly schedule and spending limits'} />
    {query.error && <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />}
    {!listing && !query.error && <LoadingState>Loading the settings…</LoadingState>}
    {listing && listing.problems.length > 0 && <div role="alert" className="rounded-2xl bg-[#FFF8E9] p-4 text-[13px] text-[#947021]">
      <p className="font-semibold">Some saved settings could not be used, so their defaults apply:</p>
      <ul className="ml-5 list-disc">{listing.problems.map(problem => <li key={problem}>{problem}</li>)}</ul></div>}
    {view && <>
      <ScheduleCard rows={{ 'cycle.weekday': view.editable['cycle.weekday'], 'cycle.hour': view.editable['cycle.hour'], 'cycle.timezone': view.editable['cycle.timezone'] }} canChange={canChange} />
      {!view.uncapped && <section className={`${PANEL} p-6 space-y-3`} aria-labelledby="settings-budgets">
        <div className="space-y-1">
          <h2 id="settings-budgets" className={HEADING}>Weekly spending limits</h2>
          <p className={META}>The most each kind of work may spend in a week. Work that would go over waits until the limit renews.</p>
        </div>
        <table className="w-full text-[13px]">
          <caption className="sr-only">Weekly spending limits</caption>
          <thead><tr className="text-left text-[11px] text-[#8B93A3]"><th scope="col" className="py-2 pr-4 font-medium">Purpose</th>
            <th scope="col" className="py-2 font-medium text-right">Up to, each week</th></tr></thead>
          <tbody>{view.budgets.map(line => <tr key={line.purpose} className="border-t border-[#EEF0F4]">
            <th scope="row" className="py-2.5 pr-4 text-left font-normal text-[#1B2433]">{line.label}</th>
            <td className="py-2.5 text-right tabular-nums">{typeof line.usd?.value === 'number' ? `USD ${line.usd.value.toFixed(2)}` : 'No limit set'}</td>
          </tr>)}</tbody>
        </table>
      </section>}
    </>}
  </section>;
}
