import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import type { BlockerItem, Card, StoredAngle, StoredPackV2 } from '../api/types';
import { renderScreen } from '../testing/render';
import { seed, shell } from '../testing/fixtures';
import { BRIEF_V4, PACK } from '../testing/packFixtures';
import { BlockerList, RemovedMaterialNote, blockerName } from './BriefEditing';
import { CardReview, developBlocker, publicReasons } from './CardReview';
import { ContentPacks } from './ContentPacks';
import { SQLBriefs } from './SQLBriefs';

/* 6.B12 in the app: an item built on material removed at a client's request is marked, never deleted (backend removal.py).
   Each screen shows the removal's note, with its day, where it shows the item's other blockers, so a person sees why the card
   cannot be developed, the brief approved or the pack marked ready. The note is synthetic. */

const NOTE = "Built on material removed at a client's request on 25 October 2026. Do not use it; develop a new card from other calls.";
const REMOVED = { decision_id: 'decision_removal', removed_at: '2026-10-25T10:00:00+00:00', note: NOTE };
const text = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/\s+/g, ' ');

test('6.B12: the new blocker kind has a plain name, and the note says why', () => {
  assert.equal(blockerName('removed_material'), 'Removed on request');
  assert.equal(text(renderScreen(<RemovedMaterialNote removed={REMOVED} />)).trim(), `Removed on request: ${NOTE}`);
  assert.equal(renderScreen(<RemovedMaterialNote removed={null} />), '');
});

test('6.B12: a brief\'s removed-material blocker carries the removal\'s note with its day; one the list lacks is added first', () => {
  // The backend's item: its title and action in a reviewer's words, no detail (briefs/gate_two.py plain_blocker).
  const item: BlockerItem = { kind: 'removed_material', title: "This brief is built on material removed at a client's request.",
    action: 'Do not approve or publish it; develop a new card from other calls.', detail: null };
  const listed = text(renderScreen(<BlockerList items={[item]} removed={REMOVED} />));
  assert.ok(listed.includes("Removed on request: This brief is built on material removed at a client's request."));
  assert.ok(listed.includes(NOTE) && listed.includes('Do not approve or publish it'));
  const added = text(renderScreen(<BlockerList items={[]} removed={REMOVED} />));
  assert.ok(added.includes(`Removed on request: ${NOTE}`) && !added.includes('Nothing stops approval'));
  assert.ok(renderScreen(<BlockerList items={[]} />).includes('Nothing stops approval.'));
});

test('6.B12: at Gate 2 the brief built on removed material says so among its checks', () => {
  const brief = { ...BRIEF_V4, removed_material: REMOVED, blockers: [NOTE],
    blocker_items: [{ kind: 'removed_material', title: "This brief is built on material removed at a client's request.", action: 'Do not approve or publish it; develop a new card from other calls.', detail: null }] };
  const page = text(renderScreen(<SQLBriefs />, { url: '/studio/briefs/brief_v4', pattern: '/studio/briefs/:briefId',
    seed: [...shell({ briefs: true }), seed('/briefs', { query: { limit: 20, offset: 0 } }, { items: [brief], total: 1, limit: 20, offset: 0 }),
      seed('/briefs/{brief_id}', { path: { brief_id: 'brief_v4' } }, brief)] }));
  assert.ok(page.includes('Removed on request:'), 'the blocker by its name');
  assert.ok(page.includes('25 October 2026'), 'with the day of the removal');
});

test('6.B12: at Gate 1 a card built on removed material shows the note and cannot be developed', () => {
  const card = { rank: 1, title: 'A card on removed material', pillar: 'WARM', content_type: 'behind_the_scenes', series: null, point: 'A point.',
    moment_ids: [], verify_before_publishing: [], why_selected: 'Shows the move.' } as unknown as Card;
  // The backend puts the note first among the public-use reasons too (repository.py); the card says it once, on its own line.
  const angle = { angle_id: 'angle_removed', run_id: 'run_1', content_hash: 'h1', moment_ids: [], has_replacement: false, can_approve: true, can_edit: true,
    content_body: { card, title: card.title }, approval_status: 'pending', selection_status: 'visible', matching_result: { status: 'complete', current_batch_flags: [] },
    disposition: null, hold: null, refresh: null, stance_confirmation: null, removed_material: REMOVED,
    public_use: { allowed: false, reasons: [NOTE], kinds: ['removed_material'] } } as unknown as StoredAngle;
  assert.equal(developBlocker(angle, card), `${NOTE} It cannot be developed.`);
  assert.deepEqual(publicReasons(angle), [], 'the note is not repeated as a public-use reason');
  const html = text(renderScreen(<CardReview angle={angle} card={card} roster={[]} busy={false} perform={async () => true} />));
  assert.ok(html.includes(`Removed on request: ${NOTE}`));
  assert.equal(html.split(NOTE).length - 1 >= 1, true);
  assert.ok(!html.includes('Not for public content as it stands'), 'no second note saying the same');
  assert.equal(developBlocker({ ...angle, removed_material: null, public_use: null }, card), null, 'without the mark the card can be developed');
});

test('6.B12: removed material remains visible as a content check after retiring pack approval', () => {
  const pack = { ...PACK, state: 'in_review', removed_material: REMOVED, ready_blockers: [NOTE, 'Email: a line to fix'] } as StoredPackV2;
  const html = renderScreen(<ContentPacks base="/studio/packs" />, { url: '/studio/packs/pack_1', pattern: '/studio/packs/:packId',
    seed: [...shell({ packs: true }), seed('/packs/{pack_id}', { path: { pack_id: pack.pack_id } }, pack)] });
  const ready = text(html.slice(html.indexOf('aria-label="Content checks"'), html.indexOf('aria-label="Content pack pieces"')));
  assert.ok(ready.includes('Content checks to review:'));
  assert.ok(ready.includes(`Removed on request: ${NOTE}`));
  assert.equal(ready.split('25 October 2026').length - 1, 1, 'the note is said once in the Ready section');
  assert.ok(ready.includes('Email: a line to fix'));
  assert.ok(!html.includes('Ready to publish'), 'pack approval is no longer offered');
  assert.ok(html.includes('Mark as Published'), 'manual publication records what actually went out');
});
