import '../testing/setupDom';
import React, { act } from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import type { AlertList, CostSummary } from '../api/schema';
import { json, mount, stubFetch } from '../testing/dom';
import { renderScreen } from '../testing/render';
import { ALERTS, COSTS, ME_ADMIN, ME_APPROVER } from '../testing/fixtures';
import { seesDetails } from '../utils/me';
import { AlertsAndCosts, AlertsPanel, CostsView, canDismiss, mayDismiss, splitAlerts, usd } from './AlertsAndCosts';
import { TopHeader } from './TopHeader';

const VIEWER = { ...ME_APPROVER, role: 'viewer', roles: ['viewer'], can: Object.fromEntries(Object.keys(ME_APPROVER.can).map(k => [k, false])) as Record<keyof typeof ME_APPROVER.can, boolean> };
const EDITOR = { ...VIEWER, role: 'editor', roles: ['viewer', 'editor'], can: { ...VIEWER.can, edit_cards: true, edit_briefs: true } };
const list = ALERTS as unknown as AlertList;

function backend(me: unknown, alerts: unknown = ALERTS) {
  const writes: string[] = [];
  let current = alerts as typeof ALERTS;
  const network = stubFetch((url, options) => {
    if (url.endsWith('/me')) return json(me);
    if (options?.method === 'POST') {
      writes.push(url);
      const id = /\/alerts\/([^/]+)\/dismiss$/.exec(url)?.[1];
      current = { ...current, open: current.open - 1, alerts: current.alerts.filter(a => a.alert_id !== id) };
      return json({ alert_id: id, kind: 'job_failed', subject: 'job_1' });
    }
    if (url.includes('/alerts')) return json(url.includes('resolved=true') ? current : { ...current, alerts: current.alerts.filter(a => !a.resolved_at) });
    if (url.endsWith('/costs')) return json(COSTS);
    return json({ detail: 'Not found' }, 404);
  });
  return { network, writes };
}

test('6.F5: open alerts come first, resolved ones apart; only a stored open alert can be dismissed, and only by an editor or approver', () => {
  const { open, resolved } = splitAlerts(list);
  assert.deepEqual(open.map(a => a.kind), ['scheduler_silent', 'job_failed', 'budget_refused']);
  assert.deepEqual(resolved.map(a => a.alert_id), ['alert_old']);
  assert.deepEqual(list.alerts.map(canDismiss), [false, true, true, false], 'not the live silence, not a resolved one');
  assert.equal(mayDismiss(VIEWER), false);
  assert.equal(mayDismiss(EDITOR), true);
  assert.equal(mayDismiss(ME_APPROVER), true);
  // The technical details are an approver's or an administrator's (the owner, 25 October 2026).
  assert.equal(seesDetails(EDITOR), false);
  assert.equal(seesDetails(ME_APPROVER), true);
  assert.equal(seesDetails({ ...VIEWER, roles: ['viewer', 'admin'] }), true);
});

test('6.F5: an editor reads each alert by its severity and kind in words, without its technical message, and dismisses one', async t => {
  const { network, writes } = backend(EDITOR);
  t.after(network.restore);
  const ui = await mount(<AlertsPanel />, { url: '/sources/alerts' });
  t.after(() => ui.unmount());
  await ui.settle();
  const text = ui.text();
  assert.match(text, /Alerts \(3 open\)/);
  for (const words of ['Error · The scheduler is silent', 'Error · A job failed', 'Warning · Waiting for budget', 'None are emailed']) assert.ok(text.includes(words), words);
  assert.ok(!text.includes('the provider timed out') && !text.includes('seen 4 times'), 'no technical detail for an editor');
  assert.equal(ui.container.querySelector('details'), null);
  const buttons = [...ui.container.querySelectorAll('button')].filter(b => b.textContent === 'Dismiss');
  assert.equal(buttons.length, 2, 'the two stored alerts, not the live silence');
  assert.match(buttons[0].getAttribute('aria-label')!, /^Dismiss: A job failed, last seen Oct 25, 2026/);
  await ui.click(buttons[0]);
  await ui.settle();
  assert.deepEqual(writes, ['/api/atelier/alerts/alert_job/dismiss']);
  assert.match(ui.text(), /Alerts \(2 open\)/);
  assert.ok(!ui.text().includes('A job failed'), 'the dismissed alert left the list');
  assert.equal(ui.container.querySelector('[data-live-region]')?.textContent, 'Alert dismissed.');
  assert.equal(document.activeElement?.id, 'alerts-heading', 'focus goes to the panel heading');
});

test('6.F5: an approver has each alert\'s message and when and how often it was seen, folded under Details', async t => {
  const { network } = backend(ME_APPROVER);
  t.after(network.restore);
  const ui = await mount(<AlertsPanel />, { url: '/sources/alerts' });
  t.after(() => ui.unmount());
  await ui.settle();
  const details = [...ui.container.querySelectorAll('details')];
  assert.equal(details.length, 3);
  assert.ok(details.every(d => !d.open), 'folded until opened');
  for (const words of ['A brief job failed: the provider timed out', 'seen 4 times', 'seen once', 'First seen Oct 24, 2026', 'Read live: it clears by itself']) {
    assert.ok(details.some(d => d.textContent?.includes(words)), words);
  }
});

test('6.F5: a viewer reads the alerts but is offered no Dismiss', async t => {
  const { network } = backend(VIEWER);
  t.after(network.restore);
  const ui = await mount(<AlertsPanel />, { url: '/sources/alerts' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.ok(ui.text().includes('A job failed'));
  assert.equal([...ui.container.querySelectorAll('button')].filter(b => b.textContent === 'Dismiss').length, 0);
});

test('6.F5: resolved alerts of the last 14 days are behind a toggle that reads ?resolved=true; an empty list says nothing is wrong', async t => {
  const { network } = backend(ME_APPROVER);
  t.after(network.restore);
  const ui = await mount(<AlertsPanel />, { url: '/sources/alerts' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.ok(!ui.text().includes('Collection stopped'), 'resolved ones are hidden at first');
  await ui.tick(ui.container.querySelector<HTMLInputElement>('input[type="checkbox"]')!);
  await ui.settle();
  assert.ok(network.calls.some(c => c.url === '/api/atelier/alerts?resolved=true'));
  assert.ok(ui.text().includes('Resolved in the last 14 days') && ui.text().includes('Error · Collection stopped'));
  assert.ok(ui.text().includes('dismissed by editor@example.invalid'));

  const quiet = renderScreen(<AlertsPanel />, { seed: [['/alerts', undefined, { open: 0, alerts: [], email: 'off' }]] });
  assert.ok(quiet.includes('No open alerts: nothing is wrong.'));
});

test('6.F5: the costs are an approver\'s or an administrator\'s, with the totals shown at once', async t => {
  const { network } = backend(EDITOR);
  t.after(network.restore);
  const editor = await mount(<AlertsAndCosts />, { url: '/sources/alerts' });
  await editor.settle();
  assert.ok(!editor.text().includes('Costs'), 'no costs for an editor');
  await editor.unmount();
  network.restore();

  const admin = backend(ME_ADMIN);
  t.after(admin.network.restore);
  const ui = await mount(<AlertsAndCosts />, { url: '/sources/alerts' });
  t.after(() => ui.unmount());
  await ui.settle();
  await ui.settle();
  const section = ui.container.querySelector('section[aria-labelledby="costs-heading"]')!;
  assert.ok(admin.network.calls.some(c => c.url === '/api/atelier/costs'));
  for (const words of ['Spent since Oct 20, 2026', 'This week', 'USD 1.20', 'Cost of each content pack'])
    assert.ok(section.textContent?.includes(words), words);
});

test('6.F5: the costs show this week and the recent weeks by purpose, stage and model, in USD', () => {
  const html = renderScreen(<CostsView costs={COSTS as unknown as CostSummary} />);
  const text = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  for (const words of ['This week (from Oct 19, 2026): USD 1.20 over 12 calls, 1 with no recorded cost', 'By purpose', 'weekly cycle 2 USD 0.90',
    'By stage', 'Writing content angles', 'By model', 'synthetic-large (openrouter) 12 USD 1.20', 'The last 2 weeks: USD 2.00 in all',
    'Oct 12, 2026 12 USD 0.80 weekly cycle USD 0.60, briefs USD 0.20', 'Recorded cost only. Weeks start on Monday at 00:00 UTC.']) {
    assert.ok(text.includes(words), words);
  }
  assert.ok(html.indexOf('Oct 19, 2026') < html.indexOf('Oct 12, 2026'), 'the newest week first');
  // The totals and each pack's cost come before the breakdown, which is folded.
  assert.ok(text.indexOf('Spent since Oct 20, 2026 USD 1.20') < text.indexOf('By week, purpose, stage and model'));
  for (const words of ['Cost of each content pack: USD 1.29 in all', 'How we lowered a budget · made again Week of Oct 18 Oct 21 USD 1.29',
    'How we read a new ad Week of Oct 12 Oct 14 No new charge (made from answers that cost USD 0.60 when first written)',
    'How we read a new ad · stopped Week of Oct 12 Oct 14 No calls recorded',
    'What the model provider charged for each call, as it reported it.']) assert.ok(text.includes(words), words);
  const none = renderScreen(<CostsView costs={{ ...COSTS, packs: [] } as unknown as CostSummary} />).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  assert.ok(none.includes('No content pack has been made yet.'));
  assert.equal(usd(0.0123), 'USD 0.0123');
  assert.equal(usd(0), 'USD 0.00');
  assert.equal(usd(3.5), 'USD 3.50');
});

test('6.F5: the bell counts open alerts beside the approvals and links to them', () => {
  const bell = renderScreen(<TopHeader onOpenInbox={() => {}} pendingCount={0} alertCount={2} onOpenAlerts={() => {}} />);
  assert.ok(bell.includes('aria-label="Open notifications: nothing waiting, 2 open alerts"'));
  assert.ok(bell.includes('bg-[#F5A524]'), 'an open alert alone draws the mark');
  const quiet = renderScreen(<TopHeader onOpenInbox={() => {}} pendingCount={0} />);
  assert.ok(quiet.includes('aria-label="Open notifications: nothing waiting, no open alerts"') && !quiet.includes('bg-[#F5A524]'));
});

test('6.F5: the bell\'s panel names the open alerts and opens them', async t => {
  let opened = 0;
  const ui = await mount(<TopHeader onOpenInbox={() => {}} pendingCount={1} alertCount={1} onOpenAlerts={() => { opened += 1; }} />);
  t.after(() => ui.unmount());
  await ui.click(ui.container.querySelector('button[aria-label^="Open notifications"]'));
  assert.ok(ui.text().includes('1 item to review') && ui.text().includes('1 open alert'));
  await ui.click([...ui.container.querySelectorAll('button')].find(b => b.textContent === 'Open the alerts')!);
  assert.equal(opened, 1);
});
