import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { CalendarDayModal } from './CalendarDayModal';
import { packCalendarPosts } from '../testing/legacyCalendar';
import { INITIAL_IDEAS } from '../data/mockData';
import { generateContentPackForIdea } from '../utils/packGenerator';

const idea = { ...INITIAL_IDEAS[0], pack: generateContentPackForIdea(INITIAL_IDEAS[0]) };
const entries = packCalendarPosts(idea, 10, '09:30 IST');
const props = { date: { year: 2026, month: 9, day: 10 }, onClose: () => {}, onOpenContent: () => {} };

test('day modal exposes the full five-piece schedule with themed filters and internal scrolling', () => {
  const html = renderToStaticMarkup(<CalendarDayModal {...props} entries={entries} />);
  assert.ok(html.includes('role="dialog"'));
  assert.ok(html.includes('aria-modal="true"'));
  assert.ok(html.includes('October 10, 2026'));
  assert.ok(html.includes('Saturday · 5 content items'));
  assert.ok(html.includes('All content'));
  for (const format of ['Email', 'Carousel', 'Reel']) assert.ok(html.includes(format));
  assert.equal((html.match(/<li(?:\s|>)/g) ?? []).length, 5);
  assert.equal((html.match(/>View</g) ?? []).length, 5);
  assert.ok(html.includes('overflow-y-auto'));
  assert.ok(html.includes('data-lenis-prevent="true"'));
  assert.ok(html.includes('Close day schedule'));
  assert.ok(html.includes('>Done</button>'));
});

test('empty days have a useful calendar modal empty state', () => {
  const html = renderToStaticMarkup(<CalendarDayModal {...props} entries={[]} />);
  assert.ok(html.includes('No content for this day'));
  assert.ok(html.includes('once it has a publishing date'));
});
