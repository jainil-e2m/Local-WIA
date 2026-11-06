import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { PageHeading } from './PageHeading';
import { ContentPacksView } from './ContentPacksView';
import { EditorialHub } from './EditorialHub';

test('page help is attached to an accessible focusable info icon, not a subtitle', () => {
  const html = renderToStaticMarkup(<PageHeading title="Previous Concepts" description="Earlier weeks, kept intact." />);
  assert.ok(html.includes('<h1 class="atelier-page-title">Previous Concepts</h1>'));
  assert.ok(html.includes('aria-label="About Previous Concepts"'));
  assert.ok(html.includes('aria-describedby='));
  assert.ok(html.includes('role="tooltip"'));
  assert.ok(html.includes('Earlier weeks, kept intact.'));
  assert.ok(html.includes('group-hover/page-info:visible'));
  assert.ok(html.includes('group-focus-within/page-info:visible'));
  assert.ok(html.includes('top-[3px] inline-flex items-center justify-center'));
  assert.ok(!html.includes('atelier-page-subtitle'));
});

test('all three requested sections use the shared title info tooltip', () => {
  const callbacks = { onReview: () => {}, onUpdateGate: () => {}, onSwitchSection: () => {}, onAddAngle: () => {}, onApprovePack: () => {}, onSchedule: () => {} };
  for (const mode of ['weekly', 'previous'] as const) {
    const html = renderToStaticMarkup(<EditorialHub mode={mode} ideas={[]} {...callbacks} />);
    assert.ok(html.includes(`aria-label="About ${mode === 'weekly' ? 'Weekly Studio' : 'Previous Concepts'}"`));
    assert.ok(html.includes('role="tooltip"'));
    assert.ok(!html.includes('atelier-page-subtitle'));
  }
  const packs = renderToStaticMarkup(<ContentPacksView ideas={[]} onSelectIdea={() => {}} />);
  assert.ok(packs.includes('aria-label="About Content Packs &amp; Deliverable Scripts"'));
  assert.ok(packs.includes('role="tooltip"'));
  assert.ok(!packs.includes('atelier-page-subtitle'));
});
