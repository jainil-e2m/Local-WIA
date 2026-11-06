import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import type { CycleSchedule } from '../api/schema';
import { json, mount, stubFetch } from '../testing/dom';
import { INTAKE_OVERVIEW } from '../testing/fixtures';
import { IntakeView } from './IntakeView';
import { NextRun, NextRunDetails } from './NextRun';

const ON: CycleSchedule = { enabled: true, at: '2026-11-01T04:00:00-06:00', timezone: 'America/Chicago', text: 'Sunday 04:00 America/Chicago',
  window: { start: '2026-10-25T04:00:00-05:00', end: '2026-11-01T04:00:00-06:00' } };
const OFF: CycleSchedule = { enabled: false, at: null, timezone: 'America/Chicago', text: 'Sunday 04:00 America/Chicago', window: null };
const now = new Date('2026-10-27T10:00:00Z');

test('3.B11: the scheduled day shows the schedule\'s own time zone next to the date, not the label', () => {
  const html = renderToStaticMarkup(<NextRunDetails schedule={ON} now={now} showCountdown={false} />);
  assert.ok(html.includes('atelier-next-run-label">Next Run</span>'));
  assert.ok(html.includes('atelier-next-run-date-row'));
  assert.ok(html.includes('Sunday, Nov 1'));
  assert.ok(html.includes('4:00 AM CST'));
  assert.ok(html.indexOf('Sunday, Nov 1') < html.indexOf('4:00 AM CST'));
  assert.ok(html.includes('dateTime="2026-11-01T10:00:00.000Z"'));
});

test('3.B11: the countdown hides the scheduled time, date and time zone', () => {
  const html = renderToStaticMarkup(<NextRunDetails schedule={ON} now={now} showCountdown />);
  assert.ok(html.includes('5d 00h 00m 00s'));
  for (const hidden of ['4:00 AM', 'CST', 'Sunday', 'atelier-next-run-time']) assert.ok(!html.includes(hidden));
});

test('3.B11: a schedule that is off says so; a failed or pending read says that, never an invented time', () => {
  assert.ok(renderToStaticMarkup(<NextRunDetails schedule={OFF} now={now} showCountdown={false} />).includes('Schedule off'));
  assert.ok(renderToStaticMarkup(<NextRunDetails schedule={undefined} failed now={now} showCountdown={false} />).includes('Schedule unavailable'));
  assert.ok(renderToStaticMarkup(<NextRunDetails schedule={undefined} now={now} showCountdown={false} />).includes('Checking the schedule'));
});

test('3.B11: the sidebar reads GET /schedule and says the cycle starts by itself, or that the schedule is off', async t => {
  let answer = ON;
  const network = stubFetch(url => url.endsWith('/schedule') ? json(answer) : json({ detail: 'Not found' }, 404));
  t.after(network.restore);
  const ui = await mount(<NextRun />);
  await ui.settle();
  const button = ui.container.querySelector('button')!;
  assert.match(button.getAttribute('aria-label')!, /^The cycle starts by itself Sunday 1 November at 4:00 a\.m\. Chicago time\. Show the countdown\.$/);
  assert.equal(button.getAttribute('aria-pressed'), 'false');
  assert.ok(!/Display only/.test(ui.container.innerHTML), 'it is no longer display only');
  await ui.click(button);
  assert.equal(button.getAttribute('aria-pressed'), 'true');
  await ui.unmount();

  answer = OFF;
  const off = await mount(<NextRun compact />);
  await off.settle();
  assert.equal(off.container.querySelector('button'), null, 'nothing to count down to: no toggle');
  const note = off.container.querySelector('[role="note"]')!;
  assert.match(note.getAttribute('aria-label')!, /^Next run: Schedule off\. The weekly cycle does not start by itself/);
  assert.equal(note.getAttribute('tabindex'), '0', 'the collapsed sidebar\'s tooltip is reachable by keyboard');
  assert.ok(network.calls.every(c => c.url === '/api/atelier/schedule'));
  await off.unmount();
});

test('3.B11: the intake\'s weekly completion falls back to the schedule\'s words, not a fixed Saturday', async t => {
  const network = stubFetch(url => url.endsWith('/schedule') ? json(ON) : url.endsWith('/me') ? json({ can: {} }) : json({ ...INTAKE_OVERVIEW, schedule: '' }));
  t.after(network.restore);
  const ui = await mount(<IntakeView />, { url: '/sources/intake' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.match(ui.text(), /this week's collection closes Sunday \d{1,2} \w+ at \d{1,2}:\d{2} [ap]\.m\. Chicago time/);
  assert.ok(!ui.text().includes('Saturday'));
});
