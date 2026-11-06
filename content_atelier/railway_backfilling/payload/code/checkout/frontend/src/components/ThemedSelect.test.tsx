import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { ThemedSelect } from './ThemedSelect';

test('themed select renders an accessible custom trigger, not a native select', () => {
  const html = renderToStaticMarkup(<ThemedSelect aria-label="Filter by offer" value="Elevate" onChange={() => {}}><option value="all">All offers</option>{['Elevate', 'LeadLock'].map(value => <option key={value}>{value}</option>)}</ThemedSelect>);
  assert.ok(html.includes('role="combobox"'));
  assert.ok(html.includes('aria-expanded="false"'));
  assert.ok(html.includes('aria-label="Filter by offer"'));
  assert.ok(html.includes('Elevate'));
  assert.ok(!html.includes('<select'));
  assert.ok(!html.includes('<option'));
});

test('uncontrolled placeholders and disabled fields retain their labels', () => {
  const html = renderToStaticMarkup(<ThemedSelect aria-label="Pass with reason" defaultValue="" disabled onChange={() => {}}><option value="" disabled>Pass with reason…</option><option value="weak">Weak proof</option></ThemedSelect>);
  assert.ok(html.includes('Pass with reason…'));
  assert.ok(html.includes('disabled=""'));
});
