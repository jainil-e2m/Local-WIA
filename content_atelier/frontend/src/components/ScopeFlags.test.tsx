import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { navigationItems } from './navigation';
import { studioTabs } from './BackendStudio';
import { HomeSummary } from './HomeSummary';
import { handoverNote } from './PackHandover';
import { TopHeader } from './TopHeader';
import { renderScreen } from '../testing/render';
import { FLAGS_OFF, readFlags, shellCounts } from '../utils/workspace';
import { SUMMARY } from '../testing/fixtures';

const TEAM_ADMIN = { isTeam: true, administration: true };
const CLIENT_SESSION = { isTeam: false, administration: true };
const labels = (flags = FLAGS_OFF, count = 0) => navigationItems(flags, count, TEAM_ADMIN).map(i => i.label);

test('S.B11: flags are off unless the answer says true', () => {
  assert.deepEqual(readFlags(undefined), FLAGS_OFF);
  assert.deepEqual(readFlags({ briefs: true, packs: 'yes', calendar: 1 }), { briefs: true, packs: false, calendar: false, context: false });
  assert.equal(readFlags({ context: true }).context, true);
  assert.equal(readFlags({ context: 'true' }).context, false);
});

test('S.F2: with all flags off, packs and scheduling are not reachable; the main navigation is the mockup four', () => {
  assert.deepEqual(labels(), ['Home', 'Weekly Studio', 'Previous Concepts', 'Sources', 'Moments']);
  assert.deepEqual(navigationItems(FLAGS_OFF, 0, TEAM_ADMIN).filter(i => i.group === 'main').map(i => i.label), ['Home', 'Weekly Studio', 'Previous Concepts']);
  assert.deepEqual(navigationItems({ ...FLAGS_OFF, packs: true }, 0, TEAM_ADMIN).filter(i => i.group === 'main').map(i => i.label), ['Home', 'Weekly Studio', 'Previous Concepts', 'Content Packs']);
  assert.deepEqual(studioTabs(FLAGS_OFF).map(([id]) => id), ['angles', 'briefs']);
  // The four-step stepper: with packs on, Scheduled Content shows what is ready to publish even while the calendar is off.
  assert.deepEqual(studioTabs({ ...FLAGS_OFF, packs: true }).map(([id]) => id), ['angles', 'briefs', 'packs', 'scheduled']);
  assert.deepEqual(studioTabs({ briefs: true, packs: true, calendar: true, context: false }).map(([id]) => id), ['angles', 'briefs', 'packs', 'scheduled']);
  assert.ok(labels({ ...FLAGS_OFF, packs: true }).includes('Content Packs'));
  assert.ok(!navigationItems(FLAGS_OFF, 0, CLIENT_SESSION).some(i => i.id === 'sources'));
  assert.ok(!navigationItems(FLAGS_OFF, 0, CLIENT_SESSION).some(i => i.id === 'moments'), 'the moments ledger is a team destination, like Sources');
});

test('Administration: Sources, Moments, Knowledge and Settings are a quiet group below the main four, for the people who use them', () => {
  const all = { briefs: true, packs: true, calendar: true, context: true };
  const items = navigationItems(all, 0, { ...TEAM_ADMIN, canReadSettings: true });
  assert.deepEqual(items.filter(i => i.group === 'admin').map(i => i.label), ['Sources', 'Moments', 'Knowledge', 'Settings']);
  assert.deepEqual(navigationItems(all, 0, { isTeam: true, canReadSettings: true, administration: false }).map(i => i.label),
    ['Home', 'Weekly Studio', 'Previous Concepts', 'Content Packs'], 'a team member without those tools sees the main four only');
});

test('L.F1: the Knowledge destination appears only with the context flag, for team sessions', () => {
  assert.ok(!labels().includes('Knowledge'));
  assert.deepEqual(labels({ ...FLAGS_OFF, context: true }), ['Home', 'Weekly Studio', 'Previous Concepts', 'Sources', 'Moments', 'Knowledge']);
  assert.ok(!navigationItems({ ...FLAGS_OFF, context: true }, 0, CLIENT_SESSION).some(i => i.id === 'knowledge'));
});

test('2.F1: the Moments destination is in the navigation for team sessions whatever the flags, and leads to the ledger', () => {
  for (const flags of [FLAGS_OFF, { briefs: true, packs: true, calendar: true, context: true }]) {
    const item = navigationItems(flags, 0, TEAM_ADMIN).find(i => i.id === 'moments');
    assert.deepEqual(item && [item.label, item.path, item.icon], ['Moments', '/moments', 'moments']);
  }
  assert.ok(!navigationItems({ briefs: true, packs: true, calendar: true, context: true }, 0, CLIENT_SESSION).some(i => i.id === 'moments'), 'not for a client session');
});

test('S.F2: shell counts come from the API summary, and a zero shows no badge', () => {
  assert.equal(navigationItems(FLAGS_OFF, 0, TEAM_ADMIN)[1].count, null);
  assert.equal(navigationItems(FLAGS_OFF, 3, TEAM_ADMIN)[1].count, '3');
  // 6.F2: the counts are GET /summary's: cards at Gate 1 for the badge; cards, held cards due back and briefs for the bell.
  assert.deepEqual(shellCounts(SUMMARY), { cards: 3, approvals: 6, alerts: 2 });
  assert.deepEqual(shellCounts(undefined), { cards: 0, approvals: 0, alerts: 0 });
  assert.deepEqual(shellCounts({ items: [] }), { cards: 0, approvals: 0, alerts: 0 }, 'an answer of another shape counts nothing');
  assert.ok(renderToStaticMarkup(<HomeSummary summary={undefined} error="" onRetry={() => {}} onOpenStudio={() => {}} packs={false} approver={false} />).includes('Loading this week'));
});

test('S.F2: the notification bell shows a waiting mark only when something is waiting', () => {
  // The mark is the small amber dot on the bell.
  const bell = (pendingCount: number) => renderScreen(<TopHeader onOpenInbox={() => {}} pendingCount={pendingCount} />);
  assert.ok(!bell(0).includes('bg-[#F5A524]'), 'nothing waiting: no mark');
  assert.ok(bell(2).includes('bg-[#F5A524]'), 'two approvals waiting: the mark');
});

test('S.F2, NP.F3: an approved brief says no pack follows when packs are off; with packs on only a v4 brief hands over to a pack', () => {
  const v4 = 'brief_document_v4' as const;
  assert.match(handoverNote({ approval_status: 'approved', schema_version: v4 }, false), /No content pack is generated/);
  assert.match(handoverNote({ approval_status: 'pending', schema_version: v4 }, false), /No content pack will be generated/);
  assert.equal(handoverNote({ approval_status: 'pending', schema_version: v4 }, true), 'Approving this brief creates its content pack.');
  assert.equal(handoverNote({ approval_status: 'approved', schema_version: v4 }, true), 'Approved. Its content pack is below.');
  // Section 4.2: at go-live only v4 briefs start a pack; an earlier contract says how to get one. The v1-only note is gone.
  for (const version of ['brief_document_v1', 'brief_document_v2', 'brief_document_v3'] as const) {
    const note = handoverNote({ approval_status: 'approved', schema_version: version }, true);
    assert.equal(note, 'This brief is in an earlier format: develop the angle again to get a content pack.');
    assert.doesNotMatch(note, /version 1 briefs only/);
  }
});
