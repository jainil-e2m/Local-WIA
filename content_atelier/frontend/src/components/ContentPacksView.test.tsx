import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { ContentPacksView } from './ContentPacksView';
import { INITIAL_IDEAS } from '../data/mockData';
import { generateContentPackForIdea } from '../utils/packGenerator';

test('compact pack cards retain their content, two-column layout and actions', () => {
  const source = INITIAL_IDEAS[0];
  const idea = { ...source, pack: generateContentPackForIdea(source) };
  const html = renderToStaticMarkup(<ContentPacksView ideas={[idea]} onSelectIdea={() => {}} />);
  assert.ok(html.includes('md:grid-cols-2 gap-5'));
  assert.ok(html.includes('rounded-2xl p-5'));
  assert.ok(html.includes('text-[22px] font-semibold'));
  assert.ok(html.includes('atelier-page-title]:text-[36px]'));
  assert.ok(html.includes(idea.title));
  for (const label of ['1 Email', '8 Slides', '3 Reels', 'Inspect &amp; Edit Full Suite', 'Schedule']) assert.ok(html.includes(label));
  assert.ok(!html.includes('Copy for Canva'));
  assert.ok(html.includes('aria-haspopup="dialog"'));
});

test('pack status pills use saved schedules rather than legacy gate status', () => {
  const source = INITIAL_IDEAS[0];
  const pack = generateContentPackForIdea(source);
  const waiting = renderToStaticMarkup(<ContentPacksView ideas={[{ ...source, pack, gate: 'approved_for_giselle', scheduledAt: undefined }]} onSelectIdea={() => {}} />);
  assert.ok(waiting.includes('To be scheduled'));
  assert.ok(waiting.includes('text-orange-700'));
  assert.ok(!waiting.includes('Pack generated · ready to schedule'));
  assert.ok(!waiting.includes('Approved &amp; Scheduled for Posting'));
  const scheduled = renderToStaticMarkup(<ContentPacksView ideas={[{ ...source, pack, gate: 'gate3_pack', scheduledAt: '2026-10-10T04:00:00Z' }]} onSelectIdea={() => {}} />);
  assert.ok(scheduled.includes('Scheduled'));
  assert.ok(scheduled.includes('text-emerald-700'));
  assert.ok(!scheduled.includes('To be scheduled'));
});

test('monthly dropdowns wrap unchanged pack cards, with the latest month open', () => {
  const source = INITIAL_IDEAS[0];
  const pack = generateContentPackForIdea(source);
  const ideas = [
    { ...source, id: 'sept', title: 'September pack', pack, briefApprovedAt: '2026-09-15T00:00:00Z' },
    { ...source, id: 'oct', title: 'October pack', pack, briefApprovedAt: '2026-10-02T00:00:00Z' },
  ];
  const html = renderToStaticMarkup(<ContentPacksView ideas={ideas} onSelectIdea={() => {}} />);
  assert.equal((html.match(/<details/g) ?? []).length, 2);
  assert.equal((html.match(/open=""/g) ?? []).length, 1);
  assert.ok(html.indexOf('October 2026') < html.indexOf('September 2026'));
  for (const title of ['September pack', 'October pack']) assert.ok(html.includes(title));
  assert.equal((html.match(/Inspect &amp; Edit Full Suite/g) ?? []).length, 2);
  assert.equal((html.match(/rounded-2xl p-5/g) ?? []).length, 2);
});
