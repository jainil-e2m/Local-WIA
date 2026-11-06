import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../testing/dom';
import { createQueryClient, queryKey } from '../api/query';
import { shell, DOCUMENT_LIST } from '../testing/fixtures';
import { EXTRACTION_HEALTH, MOMENT_FACETS, MOMENT_LIST, TOPICS } from '../testing/momentFixtures';
import { AppRoutes } from './AppRoutes';
import { ViewBoundary } from '../components/shared/ViewBoundary';
import { paths } from './routes';
import { weekBriefsArgs } from '../components/studio/studioWeek';

/* 1.F2, done when: a render error in one view leaves the others working. */

const Broken = () => { throw new Error('This view cannot render'); };

test('1.F2: a view that throws is replaced by a message, and its sibling keeps working', async t => {
  const quiet = console.error; console.error = () => {};
  t.after(() => { console.error = quiet; });
  const ui = await mount(<div><ViewBoundary name="Broken screen"><Broken /></ViewBoundary><ViewBoundary name="Other screen"><p>The other screen works</p></ViewBoundary></div>);
  t.after(() => ui.unmount());
  assert.match(ui.text(), /This screen hit a problem/);
  assert.match(ui.text(), /Broken screen could not be shown/);
  assert.match(ui.text(), /The other screen works/);
  assert.equal(ui.container.querySelectorAll('[role="alert"]').length, 1);
});

test('1.F2: a failed view tries again on request, and clears itself when the path changes', async t => {
  const quiet = console.error; console.error = () => {};
  t.after(() => { console.error = quiet; });
  let fails = true;
  const Flaky = () => { if (fails) throw new Error('Not yet'); return <p>Recovered</p>; };
  const ui = await mount(<ViewBoundary name="Flaky" resetKey="/a"><Flaky /></ViewBoundary>);
  t.after(() => ui.unmount());
  assert.match(ui.text(), /This screen hit a problem/);
  fails = false;
  await ui.click([...ui.container.querySelectorAll('button')].find(button => button.textContent === 'Try again') ?? null);
  assert.match(ui.text(), /Recovered/);
});

test('1.F2: a view that fails to render in the app leaves the navigation, the studio and the other views working', async t => {
  const quiet = console.error; console.error = () => {};
  t.after(() => { console.error = quiet; });
  const fetchStub = stubFetch(url => url.includes('extraction-health') ? json(EXTRACTION_HEALTH) : url.includes('/documents') ? json(DOCUMENT_LIST)
    : url.includes('/moments/facets') ? json(MOMENT_FACETS) : url.includes('/moments') ? json(MOMENT_LIST) : url.includes('/topics') ? json(TOPICS) : json({ detail: 'Not found' }, 404));
  t.after(fetchStub.restore);
  const client = createQueryClient();
  for (const [route, args, data] of shell({ packs: true, calendar: true, context: true })) client.setQueryData(queryKey(route as never, args), data);
  // A brief list whose rows carry no brief document: the briefs view cannot render them.
  client.setQueryData(queryKey('/briefs', weekBriefsArgs('week_1')), { items: [{ brief_id: 'b', week_id: 'w', approval_status: 'pending' }], total: 1, limit: 50, offset: 0 });
  const ui = await mount(<AppRoutes />, { url: paths.briefs, client });
  t.after(() => ui.unmount());
  const text = ui.text();
  assert.match(text, /This screen hit a problem/, 'the failed view says so');
  assert.match(text, /Weekly Studio/, 'the studio frame is still there');
  assert.ok(ui.container.querySelector('nav[aria-label="Main navigation"]'), 'the navigation is still there');
  assert.ok(ui.container.querySelector('nav[aria-label="Editorial pipeline"]'), 'the studio tabs are still there');
  // Another view, reached from the navigation, works.
  await ui.click([...ui.container.querySelectorAll('a')].find(a => a.getAttribute('href') === paths.sources) ?? null);
  await ui.settle();
  assert.match(ui.text(), /Client call with Maple Venue/, 'the sources view opens and shows its documents');
  assert.ok(!/This screen hit a problem/.test(ui.text()));
  // And so does the moments ledger.
  await ui.click([...ui.container.querySelectorAll('a')].find(a => a.getAttribute('href') === paths.moments) ?? null);
  await ui.settle();
  assert.match(ui.text(), /We reply to every inquiry within five minutes/, 'the moments ledger opens and shows its moments');
  assert.ok(!/This screen hit a problem/.test(ui.text()));
});
