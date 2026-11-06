import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { RevivalApproval } from './RevivalApproval';
import { IdeaDetailModal } from './IdeaDetailModal';
import { INITIAL_IDEAS } from '../data/mockData';

test('revival uses a collapsed, anchored confirmation trigger rather than an immediate action', () => {
  const html = renderToStaticMarkup(<RevivalApproval atCapacity onApprove={() => {}} />);
  assert.ok(html.includes('relative ml-auto inline-flex'));
  assert.ok(html.includes('aria-expanded="false"'));
  assert.ok(html.includes('Approve revival → Weekly Studio'));
  assert.ok(!html.includes('role="dialog"'));
});

test('both archived inspector stages use the shared revival confirmation', () => {
  for (const gate of ['gate1_angle', 'gate2_brief'] as const) {
    const html = renderToStaticMarkup(<IdeaDetailModal idea={{ ...INITIAL_IDEAS[0], gate, pack: undefined }} initialTab={gate === 'gate1_angle' ? 'gates' : 'brief'} revivalApproval revivalAtCapacity onClose={() => {}} onUpdateGate={() => {}} onUpdateCta={() => {}} />);
    assert.ok(html.includes('Approve revival → Weekly Studio'));
    assert.ok(html.includes('aria-expanded="false"'));
    assert.ok(!html.includes('Approve Angle &amp; Write Brief'));
    assert.ok(!html.includes('Approve Brief &amp; Generate Content Pack'));
  }
});
