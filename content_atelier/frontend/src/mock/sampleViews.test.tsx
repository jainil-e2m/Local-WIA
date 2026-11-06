import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { mount, stubFetch } from '../testing/dom';
import { SampleDataWorkspace } from './SampleDataWorkspace';
import { FIXTURE_COMPONENT_FILES, SAMPLE_VIEWS, type SampleViewEntry } from './sampleViews';
import MockApp from './MockApp';

/* 1.F4, done when: every sample screen shows the marker. 6.F3: the sample screens are the demo build's, at /sample/<view>. */

const here = path.dirname(fileURLToPath(import.meta.url));

/** The sample screens whose rendering lacks the marker; the check takes the renderer so it can be shown to catch a miss. */
export async function unmarked(render: (view: SampleViewEntry) => Promise<string>) {
  const missing: string[] = [];
  for (const view of SAMPLE_VIEWS) if (!(await render(view)).includes('data-sample-data')) missing.push(view.id);
  return missing;
}

test('1.F4: every sample screen shows the Sample data marker, and asks the server for nothing (6.F4)', async t => {
  const network = stubFetch(() => { throw new Error('a sample screen made a request'); });
  t.after(network.restore);
  const missing = await unmarked(async view => {
    const ui = await mount(<SampleDataWorkspace view={view.sample} />);
    await ui.settle();
    const html = ui.container.innerHTML;
    await ui.unmount();
    return html;
  });
  assert.deepEqual(missing, []);
  assert.equal(SAMPLE_VIEWS.length, 6);
  assert.deepEqual(network.calls, [], 'the demo needs no start-up request: its id is the build\'s');
});

test('1.F4: the check fails for a sample screen that has no marker', async () => {
  assert.deepEqual(await unmarked(async () => '<div>examples</div>'), SAMPLE_VIEWS.map(view => view.id));
});

test('6.F3: the demo build opens a sample screen at its own path, with a way back to the demo', async t => {
  const network = stubFetch(() => { throw new Error('the demo made a request'); });
  t.after(network.restore);
  const ui = await mount(<MockApp />, { url: '/sample/moments' });
  t.after(() => ui.unmount());
  assert.ok(ui.container.querySelector('[data-sample-view="moments"] [data-sample-data]'), 'the sample ledger, marked');
  assert.ok([...ui.container.querySelectorAll('a')].some(a => a.getAttribute('href') === '/' && /Back to the demo/.test(a.textContent ?? '')));
});

test('1.F4: a component that imports the examples is a registered fixture component', () => {
  const components = path.join(here, '..', 'components');
  const unregistered = readdirSync(components).filter(file => /\.tsx?$/.test(file) && !/\.test\./.test(file)).filter(file => {
    const text = readFileSync(path.join(components, file), 'utf8');
    return /from '\.\.\/(data\/|types\/atelier)/.test(text) && !(FIXTURE_COMPONENT_FILES as readonly string[]).includes(file);
  });
  assert.deepEqual(unregistered, [], 'register it in FIXTURE_COMPONENT_FILES and keep it out of the real app');
});

test('1.F4: every sample screen has a path of its own under /sample/', () => {
  const paths = SAMPLE_VIEWS.map(view => view.path);
  assert.equal(new Set(paths).size, paths.length);
  assert.ok(SAMPLE_VIEWS.every(view => view.path === `/sample/${view.sample}`));
  assert.ok((FIXTURE_COMPONENT_FILES as readonly string[]).includes('MomentsLedgerView.tsx'), 'the sample ledger is still a fixture component');
});
