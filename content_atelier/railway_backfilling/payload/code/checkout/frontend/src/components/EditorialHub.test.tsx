import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { EditorialHub, WeekStagePills } from './EditorialHub';
import { INITIAL_IDEAS } from '../data/mockData';
import { stampEditorialItem } from '../utils/editorialWeeks';
import { EDITORIAL_MOCK_IDEAS } from '../data/editorialMockData';
import { octoberDemoPosts } from '../testing/legacyCalendar';

const old = stampEditorialItem({ ...INITIAL_IDEAS[0], title: 'Archived concept fixture', gate: 'gate1_angle', pack: undefined });
const current = stampEditorialItem({ ...INITIAL_IDEAS[2], id: 'new-fixture', title: 'Latest concept fixture', createdAt: '2026-10-05T06:30:00Z', editorialWeek: undefined });
const callbacks = { onReview: () => {}, onUpdateGate: () => {}, onSwitchSection: () => {}, onAddAngle: () => {}, onApprovePack: () => {}, onSchedule: () => {} };

test('angle and briefing cards omit the internal metadata label while keeping their status', () => {
  for (const stage of ['angles', 'briefs'] as const) {
    const fixture = { ...current, id: 'internal-card-id-fixture', gate: stage === 'angles' ? 'gate1_angle' as const : 'gate2_brief' as const };
    const html = renderToStaticMarkup(<EditorialHub {...callbacks} mode="weekly" initialTab={stage} ideas={[fixture]} />);
    assert.ok(!html.includes('internal-card-id-fixture'));
    assert.ok(!html.includes('uppercase tracking-[0.12em] font-semibold text-[#8B93A3]'));
    assert.ok(html.includes('Awaiting approval'));
    assert.ok(html.includes(fixture.title));
  }
});

test('revived concepts appear in the same weekly waiting stage with a distinct hue and source week', () => {
  for (const stage of ['angles', 'briefs'] as const) {
    const revived = { ...old, editorialWeek: current.editorialWeek, originalEditorialWeek: old.editorialWeek, revivedAt: '2026-10-06T00:00:00Z', gate: stage === 'angles' ? 'gate1_angle' as const : 'gate2_brief' as const };
    const html = renderToStaticMarkup(<EditorialHub {...callbacks} mode="weekly" initialTab={stage} ideas={[current, revived]} />);
    assert.ok(html.includes('bg-[#F8F3FC]'));
    assert.ok(html.includes('Revived from'));
    assert.ok(html.includes('Awaiting approval in Weekly Studio'));
    assert.ok(html.includes(revived.title));
    const archive = renderToStaticMarkup(<EditorialHub {...callbacks} mode="previous" ideas={[current, revived]} />);
    assert.ok(!archive.includes(revived.title));
  }
});

test('week pills show only the statuses relevant to each selected stage', () => {
  const counts = { waiting: 2, approved: 1, generated: 1 };
  const angles = renderToStaticMarkup(<WeekStagePills stage="angles" counts={counts} />);
  assert.ok(angles.includes('2 waiting'));
  assert.ok(angles.includes('1 approved'));
  assert.ok(angles.includes('1 generated'));
  const briefs = renderToStaticMarkup(<WeekStagePills stage="briefs" counts={counts} />);
  assert.ok(briefs.includes('1 awaiting approval'));
  assert.ok(briefs.includes('1 generated'));
  assert.ok(!briefs.includes('2 waiting'));
  assert.ok(!briefs.includes('1 approved'));
  const packs = renderToStaticMarkup(<WeekStagePills stage="packs" counts={counts} />);
  assert.ok(packs.includes('1 generated'));
  assert.ok(!packs.includes('waiting'));
  assert.ok(!packs.includes('approved'));
  assert.equal((packs.match(/rounded-full/g) ?? []).length, 1);
});

test('brief and pack week pills retain meaningful zero counts', () => {
  const counts = { waiting: 4, approved: 0, generated: 0 };
  const briefs = renderToStaticMarkup(<WeekStagePills stage="briefs" counts={counts} />);
  assert.ok(briefs.includes('0 awaiting approval'));
  assert.ok(briefs.includes('0 generated'));
  const packs = renderToStaticMarkup(<WeekStagePills stage="packs" counts={counts} />);
  assert.ok(packs.includes('0 generated'));
  assert.equal((packs.match(/rounded-full/g) ?? []).length, 1);
});

test('Weekly Studio renders only the latest week with all four scoped stages', () => {
  const html = renderToStaticMarkup(<EditorialHub mode="weekly" ideas={[old, current]} {...callbacks} />);
  assert.ok(html.includes('Latest concept fixture'));
  assert.ok(!html.includes('Archived concept fixture'));
  for (const label of ['Weekly Studio', 'Content Angle', 'Content Briefing', 'Content Packs', 'Scheduled Content']) assert.ok(html.includes(label));
  assert.ok(!html.includes('Gate 1:'));
  assert.ok(!html.includes('Gate 2:'));
});

test('Previous Concepts renders waiting concepts in collapsible dated week groups', () => {
  const html = renderToStaticMarkup(<EditorialHub mode="previous" ideas={[old, current]} {...callbacks} />);
  assert.ok(html.includes('Archived concept fixture'));
  assert.ok(!html.includes('Latest concept fixture'));
  assert.ok(!html.includes('Select previous week'));
  assert.ok(!html.includes('Browse by original week'));
  assert.ok(html.includes('<details'));
  assert.ok(html.includes('Month Sept'));
  assert.ok(html.includes('Week 4'));
  assert.ok(html.includes('28 Sept'));
  assert.ok(html.includes('1 waiting'));
  assert.ok(html.includes('0 approved'));
  assert.ok(html.includes('0 generated'));
  assert.ok(!html.includes('aria-label="angles Approved"'));
  assert.ok(!html.includes('id="editorial-packs-tab"'));
  assert.ok(!html.includes('id="editorial-scheduled-tab"'));
});

test('archived prototype scheduling no longer injects demo postings', () => {
  const html=renderToStaticMarkup(<EditorialHub mode="weekly" initialTab="scheduled" ideas={[]} {...callbacks}/>);
  assert.ok(!html.includes('mock individual postings'));
  assert.ok(html.includes('No scheduled content yet.'));
});

test('Previous Concepts excludes approved angles and includes all older waiting weeks', () => {
  const older = stampEditorialItem({ ...old, id: 'older-fixture', title: 'Older waiting fixture', createdAt: '2026-09-07T06:30:00Z', editorialWeek: undefined });
  const approved = { ...old, id: 'approved-fixture', title: 'Already approved fixture', gate: 'gate2_brief' as const };
  const html = renderToStaticMarkup(<EditorialHub mode="previous" ideas={[older, old, approved, current]} {...callbacks} />);
  assert.ok(html.includes('Older waiting fixture'));
  assert.ok(html.includes('Archived concept fixture'));
  assert.ok(!html.includes('Already approved fixture'));
  assert.ok(html.includes('Week 1'));
  assert.ok(html.includes('Week 4'));
});

test('one week does not invent an archived week or duplicate current concepts', () => {
  const html = renderToStaticMarkup(<EditorialHub mode="previous" ideas={[current]} {...callbacks} />);
  assert.ok(html.includes('No previous weeks yet'));
  assert.ok(!html.includes('Latest concept fixture'));
});
