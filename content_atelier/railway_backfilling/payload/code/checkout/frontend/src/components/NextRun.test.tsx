import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { NextRunDetails } from './NextRun';
import { nextRunAt } from '../utils/nextRun';

const now = new Date('2026-10-06T06:00:00Z');
const nextRun = nextRunAt(now);

test('scheduled-day display places Central time next to the date, not the label', () => {
  const html = renderToStaticMarkup(<NextRunDetails nextRun={nextRun} now={now} showCountdown={false} />);
  assert.ok(html.includes('atelier-next-run-label">Next Run</span>'));
  assert.ok(html.includes('atelier-next-run-date-row'));
  assert.ok(html.includes('Saturday, Oct 10'));
  assert.ok(html.includes('4:00 AM CDT'));
  assert.ok(html.indexOf('Saturday, Oct 10') < html.indexOf('4:00 AM CDT'));
});
test('countdown display hides the scheduled time, date and timezone', () => {
  const html = renderToStaticMarkup(<NextRunDetails nextRun={nextRun} now={now} showCountdown />);
  assert.ok(html.includes('4d 03h 00m 00s'));
  for (const hidden of ['4:00 AM', 'CDT', 'CT</', 'Saturday', 'atelier-next-run-time']) assert.ok(!html.includes(hidden));
});
