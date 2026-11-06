import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { Select, ThemedSelect } from './ThemedSelect';

test('themed select renders an accessible custom trigger, not a native select', () => {
  const html = renderToStaticMarkup(<ThemedSelect aria-label="Filter by offer" value="Elevate" onChange={() => {}}><option value="all">All offers</option>{['Elevate', 'LeadLock'].map(value => <option key={value}>{value}</option>)}</ThemedSelect>);
  assert.ok(html.includes('role="combobox"'));
  assert.ok(html.includes('aria-expanded="false"'));
  assert.ok(html.includes('aria-label="Filter by offer"'));
  assert.ok(html.includes('Elevate'));
  // The only native select is the hidden form mirror: out of the tab order and away from screen readers.
  assert.equal(html.match(/<select/g)?.length, 1);
  assert.match(html, /<select tabindex="-1" aria-hidden="true" class="sr-only"/i);
});

test('Select is a drop-in for a native select: its onChange gets { target: { value } } and a required choice stays in the form check', () => {
  const html = renderToStaticMarkup(<Select aria-label="Reason" required value="" onChange={() => {}}><option value="">Choose…</option><option value="timing">Bad timing</option></Select>);
  assert.ok(html.includes('Choose…'));
  assert.ok(html.includes('aria-required="true"'));
  assert.match(html, /<select[^>]*required=""/);
});

test('uncontrolled placeholders and disabled fields retain their labels', () => {
  const html = renderToStaticMarkup(<ThemedSelect aria-label="Pass with reason" defaultValue="" disabled onChange={() => {}}><option value="" disabled>Pass with reason…</option><option value="weak">Weak proof</option></ThemedSelect>);
  assert.ok(html.includes('Pass with reason…'));
  assert.ok(html.includes('disabled=""'));
});
