import '../testing/setupDom';
import React, { act } from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../testing/dom';
import { createQueryClient, queryKey } from '../api/query';
import { seed, shell } from '../testing/fixtures';
import { AppRoutes } from './AppRoutes';
import { paths } from './routes';
import { CalendarDayModal } from '../components/CalendarDayModal';
import { ContentCalendar } from '../components/ContentCalendar';
import type { SavedSchedule } from '../api/types';
import { weekBriefsArgs } from '../components/studio/studioWeek';

/* 7.F1: the shell's smaller defects. The account block is not dressed as a menu, ⌘K does something only where there is a
   search to open, and the calendar's day view is written in the calendar's own time zone. */

const BRIEFS = seed('/briefs', weekBriefsArgs('week_1'), { items: [], total: 0, limit: 50, offset: 0 });

async function app(t: { after: (fn: () => unknown) => void }, flags: { calendar: boolean }, url: string = paths.briefs) {
  const network = stubFetch(url => url.includes('/calendar/config') ? json({ enabled: true, display_timezone: 'America/Chicago', worker_ready: true })
    : url.includes('/calendar') ? json({ items: [], next_cursor: null }) : json({ detail: 'Not found' }, 404));
  t.after(network.restore);
  const client = createQueryClient();
  for (const [route, args, data] of [...shell({ packs: true, ...flags }), BRIEFS]) client.setQueryData(queryKey(route as never, args), data);
  const ui = await mount(<AppRoutes />, { url, client });
  t.after(() => ui.unmount());
  await ui.settle();
  return ui;
}

/** Presses ⌘K (Ctrl+K) on the page; says whether a handler took the key. */
async function commandK() {
  let taken = false;
  await act(async () => {
    taken = !window.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'k', metaKey: true, ctrlKey: true, bubbles: true, cancelable: true }));
  });
  return taken;
}

test('7.F1: the sidebar\'s account block names the person and does not pretend to be a menu', async t => {
  const ui = await app(t, { calendar: false });
  const account = ui.container.querySelector('aside [title*="Team"]');
  assert.ok(account, 'the account block is there');
  assert.equal(account!.querySelector('svg'), null, 'no chevron: nothing opens from here (sign-out is in the header\'s account menu)');
  assert.ok(!account!.matches('button, [role="button"], [aria-haspopup]'));
});

test('7.F1: with no search on Home, ⌘K is left alone and the page stays where it is', async t => {
  const ui = await app(t, { calendar: false });
  assert.match(ui.text(), /Approve an angle to bring its brief here/);
  assert.equal(await commandK(), false, 'the key is not taken');
  await ui.settle();
  assert.match(ui.text(), /Approve an angle to bring its brief here/, 'not sent to Home');
  assert.equal(ui.container.querySelector('input[aria-label="Search the calendar"]'), null);
});

test('7.F1: with the calendar on, ⌘K opens Home with its search focused', async t => {
  const ui = await app(t, { calendar: true });
  assert.equal(await commandK(), true);
  await ui.settle();
  const search = ui.container.querySelector('input[aria-label="Search the calendar"]');
  assert.ok(search, 'Home with its search');
  assert.equal(document.activeElement, search);
});

const props = { entries: [], onClose: () => {}, onOpenContent: () => {} };

test('7.F1: the day view names the calendar\'s time zone, and its date is the calendar\'s date in any zone', async t => {
  // The modal renders into document.body (a portal), so it is read from the page.
  const dialogText = async (timeZone?: string) => {
    const ui = await mount(<CalendarDayModal {...props} date={{ year: 2026, month: 9, day: 31 }} timeZone={timeZone} />);
    const text = document.querySelector('[role="dialog"]')?.textContent ?? '';
    await ui.unmount();
    return text;
  };
  for (const timeZone of ['Pacific/Kiritimati', 'Pacific/Pago_Pago', 'America/Chicago']) {
    const text = await dialogText(timeZone);
    assert.ok(text.includes('October 31, 2026'), `${timeZone}: the calendar's date, not a day either side`);
    assert.ok(text.includes('Saturday · 0 content items'), timeZone);
    assert.ok(text.includes(`Times in ${timeZone}`), timeZone);
  }
  assert.ok(!(await dialogText()).includes('Times in'), 'no zone given, none named');
  t.diagnostic('the day is written from its own date, so a zone twelve or more hours from UTC cannot move it');
});

test('7.F1: the saved calendar opens its day view in its own display time zone', async t => {
  const entry: SavedSchedule = {
    calendar_entry_id: 'c1', asset_id: 'a1', asset_content_hash: 'h', pack_id: 'p1', pack_manifest_hash: 'm', scheduled_for: '2026-10-16T19:00:00Z',
    status: 'scheduled', effective_status: 'scheduled', revision: 1, display_timezone: 'America/Chicago', format: 'email', slot_key: 'email',
    title: 'Saved email', pack_title: 'Saved pack', week_id: 'week_2026-10-12', warnings: [], overdue: false,
  };
  const ui = await mount(<ContentCalendar entries={[entry]} timezone="America/Chicago" initialMonth={{ year: 2026, month: 9 }} onMonthChange={() => {}} onOpenEntry={() => {}} />);
  t.after(() => ui.unmount());
  const day = [...ui.container.querySelectorAll('button')].find(button => button.textContent?.trim() === '16');
  await ui.click(day ?? null);
  const dialog = document.querySelector('[role="dialog"]');
  assert.ok(dialog, 'the day view is open');
  assert.match(dialog!.textContent ?? '', /October 16, 2026/);
  assert.match(dialog!.textContent ?? '', /Times in America\/Chicago/);
  await ui.click(dialog!.querySelector('button[aria-label="Close day schedule"]'));
});

test('the top bar holds the page\'s own title and buttons; no eyebrow, tooltip or footer line; the bell and the account menu in plain words', async t => {
  const ui = await app(t, { calendar: false });
  const header = ui.container.querySelector('header.atelier-utility-header')!;
  assert.equal(header.querySelector('h1')?.textContent, 'Weekly Studio', 'the page title is drawn in the top bar');
  assert.ok(!header.textContent?.includes('Content Atelier'), 'no "Content Atelier" eyebrow');
  assert.equal(ui.container.querySelector('main h1'), null, 'the page does not repeat its title');
  assert.ok(!ui.text().includes('Monday–Sunday weeks'), 'no footer line');
  assert.equal(ui.container.querySelector('[role="tooltip"]'), null, 'no info tooltips');
  await ui.click(header.querySelector('button[aria-label^="Open notifications"]'));
  assert.match(header.textContent ?? '', /Waiting for you/);
  assert.match(header.textContent ?? '', /\d+ items? to review|Nothing waiting on you/);
  assert.match(header.textContent ?? '', /Open the Weekly Studio/);
  await ui.click(header.querySelector('button[aria-label="Account menu"]'));
  assert.match(header.textContent ?? '', /Sign out/);
  assert.ok(!header.textContent?.includes('Refresh session') && !header.textContent?.includes('Try signing in again'), 'a signed-in person is offered sign-out only');
});
