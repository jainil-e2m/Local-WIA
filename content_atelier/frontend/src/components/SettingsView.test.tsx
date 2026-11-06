import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../testing/dom';
import { SettingsView } from './SettingsView';
import { navigationItems } from './navigation';
import { FLAGS_OFF } from '../utils/workspace';
import { readSettings, settingInput, settingsView } from '../utils/settings';

/* 6.F7: the Settings screen. An editor reads the weekly schedule and the spending limits; an approver changes the schedule;
   a value the backend refuses is shown in its words. */

const can = (edit: boolean, decide: boolean) => ({ edit_cards: edit, edit_briefs: edit, decide, approve_briefs: decide, review_knowledge: false,
  identity_review: false, manage_users: false, manage_intake: false, generate_packs: false, approve_packs: decide, schedule_calendar: false });
const me = (role: string, edit: boolean, decide: boolean) => ({ email: `${role}@example.invalid`, name: role, role, roles: [role], source: 'users', identity_approver: false, can: can(edit, decide) });
const EDITOR = me('editor', true, false), APPROVER = me('approver', true, true), VIEWER = me('viewer', false, false);

const row = (key: string, value: unknown, type: string, extra: Record<string, unknown> = {}) => ({
  key, value, source: 'default', default: value, type, choices: null, env: null, settable: true, restart_required: false, description: key, ...extra,
});
const LISTING = {
  problems: [],
  settings: [
    row('models.default', 'openai/gpt-6-luna', 'str'),
    row('models.card_verification', null, 'str?'),
    row('models.brief', 'openai/gpt-6.1-sol', 'str?', { source: 'table', updated_by: 'approver@example.invalid', updated_at: '2026-10-24T10:00:00Z' }),
    row('models.reasoning_effort.default', 'high', 'enum?'),
    row('prompts.profile.strategist', '2026-10-25.wia-strategist.v8', 'enum', { source: 'table', updated_by: 'approver@example.invalid', updated_at: '2026-10-25T08:00:00Z' }),
    row('prompts.profile.pack_finish', '2026-10-25.pack-finish.v2', 'enum'),
    row('knowledge_base.version', null, 'str?'),
    row('matching.duplicate', 0.86, 'float'),
    row('cycle.timezone', 'America/Chicago', 'zone'),
    row('cycle.weekday', 5, 'int'),
    row('cycle.hour', 4, 'int', { source: 'table', updated_by: 'approver@example.invalid', updated_at: '2026-10-20T09:00:00Z' }),
    row('budgets.weekly_usd.cycle', 1.2, 'float?'), row('budgets.weekly_calls.cycle', 80, 'int'),
    row('budgets.weekly_usd.packs', null, 'float?'), row('budgets.weekly_calls.packs', 60, 'int'),
  ],
};

/** The screen against a stub API: /me as this person, /settings as the listing, a PUT answered by `put`. */
async function open(t: { after: (fn: () => unknown) => void }, person: unknown, put: (url: string, body: unknown) => Response = (url, body) => json({ key: url.split('/').pop(), before: null, value: (body as { value: unknown }).value })) {
  const network = stubFetch((url, options) => {
    if (url.endsWith('/api/atelier/me')) return json(person);
    if (url.endsWith('/api/atelier/settings')) return json(LISTING);
    if (options?.method === 'PUT') return put(url, JSON.parse(String(options.body)));
    return json({ detail: 'Not found' }, 404);
  });
  t.after(network.restore);
  const ui = await mount(<SettingsView />);
  t.after(() => ui.unmount());
  await ui.settle();
  await ui.settle();
  return { ui, network, puts: () => network.calls.filter(call => call.options?.method === 'PUT') };
}

const form = (ui: { container: HTMLElement }, label: string) => ui.container.querySelector<HTMLFormElement>(`form[aria-label="${label}"]`)!;

test('6.F7: an editor reads the weekly schedule and the spending limits, and is offered no change; models, prompts and the cutoff are not shown', async t => {
  const { ui, puts } = await open(t, EDITOR);
  const text = ui.text();
  for (const expected of ['Settings', 'Weekly schedule', 'Saturday at 04:00, America/Chicago', 'Only an approver can change it.', 'Weekly spending limits',
    'Weekly cycle', 'USD 1.20', 'Content packs', 'No limit set']) assert.ok(text.includes(expected), `shows ${expected}`);
  for (const hidden of ['openai/gpt-6-luna', '2026-10-25.wia-strategist.v8', 'Not pinned', 'Duplicate cutoff', '0.86', 'Calls, each week', 'Set by approver@example.invalid'])
    assert.ok(!text.includes(hidden), `no ${hidden}`);
  assert.equal(ui.container.querySelectorAll('input, select, button[type="submit"]').length, 0, 'nothing to change');
  assert.deepEqual(puts(), []);
});

test('no weekly limits: Settings shows only the schedule, with no spending section', async t => {
  const listing = LISTING;
  const uncapped = { ...listing, settings: [...listing.settings, row('budgets.uncapped', true, 'bool', { source: 'table', updated_by: 'approver@example.invalid' })] };
  const network = stubFetch(url => url.endsWith('/api/atelier/me') ? json(EDITOR) : url.endsWith('/api/atelier/settings') ? json(uncapped) : json({ detail: 'Not found' }, 404));
  t.after(network.restore);
  const ui = await mount(<SettingsView />);
  t.after(() => ui.unmount());
  await ui.settle();
  await ui.settle();
  const text = ui.text();
  for (const expected of ['The weekly schedule', 'Weekly schedule']) assert.ok(text.includes(expected), `shows ${expected}`);
  for (const hidden of ['spending', 'USD 1.20', 'No limit set', 'Up to, each week', 'budgets.uncapped']) assert.ok(!text.includes(hidden), `no ${hidden}`);
  assert.equal(ui.container.querySelector('table'), null);
});

test('6.F7: an approver changes the schedule in one card, chosen from the days and hours the backend accepts, and saved as numbers', async t => {
  const { ui, puts } = await open(t, APPROVER);
  const schedule = form(ui, 'Weekly schedule');
  const [day, hour] = [...schedule.querySelectorAll('select')];
  assert.equal(day.options.length, 7);
  assert.equal(day.value, '5');
  assert.equal(hour.options.length, 24);
  const save = schedule.querySelector('button[type="submit"]') as HTMLButtonElement;
  assert.equal(save.disabled, true, 'nothing changed yet');
  await ui.choose(day, '0');
  await ui.choose(hour, '6');
  await ui.click(save);
  await ui.settle();
  assert.deepEqual(puts().map(put => [put.url.split('/').pop(), JSON.parse(String(put.options?.body))]), [['cycle.weekday', { value: 0 }], ['cycle.hour', { value: 6 }]],
    'only the changed values, as numbers');
  assert.equal(schedule.querySelector('[role="alert"]')?.textContent ?? '', '');
  assert.match(schedule.querySelector('[role="status"]')?.textContent ?? '', /Saved: Monday at 06:00, America\/Chicago\. The next run uses it\./);
});

test('6.F7: a time zone the screen knows is wrong is refused before any request', async t => {
  const { ui, puts } = await open(t, APPROVER);
  const schedule = form(ui, 'Weekly schedule');
  await ui.type(schedule.querySelector('input')!, 'Mars/Olympus');
  await ui.click(schedule.querySelector('button[type="submit"]'));
  assert.ok(schedule.querySelector('[role="alert"]')?.textContent, 'it says why');
  assert.deepEqual(puts(), [], 'refused on the screen, as the backend would');
});

test('6.F7: a save the backend refuses shows the backend\'s reason', async t => {
  const reason = "value (setting cycle.timezone): 'Europe/Atlantis' is not a time zone name (for example America/Chicago)";
  const { ui, puts } = await open(t, APPROVER, () => json({ detail: reason }, 422));
  const schedule = form(ui, 'Weekly schedule');
  await ui.type(schedule.querySelector('input')!, 'Europe/London');
  await ui.click(schedule.querySelector('button[type="submit"]'));
  await ui.settle();
  assert.equal(puts().length, 1);
  assert.equal(schedule.querySelector('[role="alert"]')?.textContent, reason);
  assert.equal(schedule.querySelector('input')!.value, 'Europe/London', 'what the person typed stays');
});

test('6.F7: a save that replaced someone else\'s change says so (the API has no version check)', async t => {
  const { ui } = await open(t, APPROVER, (_url, body) => json({ key: 'cycle.timezone', before: 'Europe/Paris', value: (body as { value: string }).value, updated_by: 'approver@example.invalid' }));
  const schedule = form(ui, 'Weekly schedule');
  await ui.type(schedule.querySelector('input')!, 'Europe/London');
  await ui.click(schedule.querySelector('button[type="submit"]'));
  await ui.settle();
  assert.match(schedule.querySelector('[role="status"]')?.textContent ?? '', /Someone had changed the time zone to Europe\/Paris since this page was read/);
});

test('6.F7: a viewer is told who may read settings, and nothing is read', async t => {
  const { ui, network } = await open(t, VIEWER);
  assert.match(ui.text(), /Settings are open to editors and approvers/);
  assert.ok(!network.calls.some(call => call.url.endsWith('/settings')));
});

test('6.F7: the navigation offers Settings to a team member who may read them', () => {
  const access = (isTeam: boolean, canReadSettings: boolean) => ({ isTeam, canReadSettings, administration: true });
  assert.ok(navigationItems(FLAGS_OFF, 0, access(true, true)).some(item => item.id === 'settings' && item.path === '/settings' && item.group === 'admin'));
  assert.ok(!navigationItems(FLAGS_OFF, 0, access(true, false)).some(item => item.id === 'settings'));
  assert.ok(!navigationItems(FLAGS_OFF, 0, access(false, true)).some(item => item.id === 'settings'), 'never for a client session');
});

test('6.F7: values are checked the way the backend checks them', () => {
  assert.deepEqual(settingInput('matching.duplicate', ' 0.86 '), { value: 0.86 });
  for (const bad of ['', 'high', '0.49', '1.01', 'NaN']) assert.ok('error' in settingInput('matching.duplicate', bad), bad);
  assert.deepEqual(settingInput('cycle.weekday', '6'), { value: 6 });
  for (const bad of ['7', '-1', '2.5', '']) assert.ok('error' in settingInput('cycle.weekday', bad), bad);
  assert.deepEqual(settingInput('cycle.hour', '23'), { value: 23 });
  assert.ok('error' in settingInput('cycle.hour', '24'));
  assert.deepEqual(settingInput('cycle.timezone', 'Asia/Kolkata'), { value: 'Asia/Kolkata' });
  assert.ok('error' in settingInput('cycle.timezone', 'Mars/Olympus'));
  assert.ok('error' in settingInput('cycle.timezone', ' '));
  const view = settingsView(readSettings(LISTING));
  assert.deepEqual(view.models.map(m => m.row.key), ['models.default', 'models.card_verification', 'models.brief']);
  assert.deepEqual(view.budgets.map(b => [b.purpose, b.usd?.value, b.calls?.value]), [['cycle', 1.2, 80], ['packs', null, 60]]);
  assert.deepEqual(readSettings({ settings: [{ value: 1 }, null, 'x'], problems: [3, 'a problem'] }), { settings: [], problems: ['a problem'] });
});
