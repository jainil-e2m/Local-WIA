import '../testing/setupDom';
import React, { act, useState } from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { createRoot } from 'react-dom/client';
import { PageHeading, PageHeaderSlot } from './PageHeading';
import { ContentPacksView } from './ContentPacksView';
import { EditorialHub } from './EditorialHub';

/* The page header (the owner, 26 October 2026): the page's own title, one short subtitle line and its main buttons, drawn in
   the shell's top bar. No info tooltips: the description older callers pass is no longer shown. */

test('the page header is the title, one subtitle line and the page\'s buttons; no info tooltip', () => {
  const html = renderToStaticMarkup(<PageHeading title="Previous Concepts" subtitle="2 earlier weeks" description="Earlier weeks, kept intact."
    actions={<button type="button">Flag idea</button>} />);
  assert.ok(html.includes('<h1 class="atelier-page-title">Previous Concepts</h1>'));
  assert.ok(html.includes('2 earlier weeks'));
  assert.ok(html.includes('<button type="button">Flag idea</button>'));
  for (const removed of ['Earlier weeks, kept intact.', 'role="tooltip"', 'aria-label="About Previous Concepts"', 'aria-describedby=']) {
    assert.ok(!html.includes(removed), `no page help: ${removed}`);
  }
  const bare = renderToStaticMarkup(<PageHeading title="Sources" />);
  assert.ok(bare.includes('<h1 class="atelier-page-title">Sources</h1>') && !bare.includes('<p'), 'no subtitle line without a subtitle');
});

test('inside the shell the header is drawn in the top bar\'s slot, not in the page', async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  function Shell() {
    const [slot, setSlot] = useState<HTMLElement | null>(null);
    return <PageHeaderSlot.Provider value={slot}>
      <header data-top-bar ref={setSlot} />
      <main><PageHeading title="Weekly Studio" subtitle="18 Oct – 24 Oct, 2026 · Latest week" /><p>The page</p></main>
    </PageHeaderSlot.Provider>;
  }
  await act(async () => { root.render(<Shell />); });
  const top = container.querySelector('[data-top-bar]')!;
  const main = container.querySelector('main')!;
  assert.equal(top.querySelector('h1')?.textContent, 'Weekly Studio');
  assert.ok(top.textContent?.includes('18 Oct – 24 Oct, 2026 · Latest week'));
  assert.equal(main.querySelector('h1'), null, 'the page itself starts with its content');
  await act(async () => root.unmount());
  container.remove();
});

test('the mockup\'s sections use the same header, without a tooltip', () => {
  const callbacks = { onReview: () => {}, onUpdateGate: () => {}, onSwitchSection: () => {}, onAddAngle: () => {}, onApprovePack: () => {}, onSchedule: () => {} };
  for (const mode of ['weekly', 'previous'] as const) {
    const html = renderToStaticMarkup(<EditorialHub mode={mode} ideas={[]} {...callbacks} />);
    assert.ok(html.includes(`<h1 class="atelier-page-title">${mode === 'weekly' ? 'Weekly Studio' : 'Previous Concepts'}</h1>`));
    assert.ok(!html.includes('role="tooltip"'));
  }
  const packs = renderToStaticMarkup(<ContentPacksView ideas={[]} onSelectIdea={() => {}} />);
  assert.ok(packs.includes('<h1 class="atelier-page-title">Content Packs &amp; Deliverable Scripts</h1>'));
  assert.ok(!packs.includes('role="tooltip"'));
});
