import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mount, json, stubFetch } from '../testing/dom';
import { PACK } from '../testing/packFixtures';
import { PackScheduling, ScheduleDialog } from './PackScheduling';
import { createQueryClient, queryKey } from '../api/query';
import type { CalendarConfig, StoredPackV2 } from '../api/types';

const config: CalendarConfig = { enabled: true, can_schedule: true, display_timezone: 'Asia/Kolkata', server_time: '2026-11-03T00:00:00Z',
  packs_enabled: true, can_generate: true, live_generation_enabled: false };
const pack: StoredPackV2 = { ...PACK, state: 'ready_to_publish', pieces: PACK.pieces.map(p => ({ ...p, asset_id: `asset_${p.key}`, content_hash: `hash_${p.key}`, schedule: null, published: [] })) };
const button = (root: Element, text: string) => [...root.querySelectorAll('button')].find(b => b.textContent?.trim() === text) ?? null;

async function open(t: { after: (fn: () => unknown) => void }, answer: Parameters<typeof stubFetch>[0], source = pack) {
  const net = stubFetch(answer); t.after(net.restore);
  let saved = 0;
  const ui = await mount(<ScheduleDialog pack={source} initialPiece="reel_2" config={config} onClose={() => {}} onSaved={async () => { saved++; }} />);
  t.after(() => ui.unmount());
  return { ui, net, saved: () => saved };
}

async function chooseFutureDate(ui: Awaited<ReturnType<typeof open>>['ui'], day = '15', time = '10:30') {
  await ui.click(ui.container.querySelector('[aria-label="Next month"]'));
  await ui.click(ui.container.querySelector(`button[data-date-day="${day}"]`));
  await ui.click(button(ui.container, 'Next: choose a time'));
  await ui.type(ui.container.querySelector('input[placeholder="09:00"]')!, time);
}

test('schedules the active piece only, using a real offset and unchanged pack/asset hashes', async t => {
  const { ui, net, saved } = await open(t, () => json({ entries: [] }));
  assert.equal((ui.container.querySelector('[aria-label="Include Reel 2"]') as HTMLInputElement).checked, true);
  assert.equal((button(ui.container, 'Save all schedules') as HTMLButtonElement).disabled, true);
  await chooseFutureDate(ui);
  await ui.click(button(ui.container, 'Save schedule'));
  assert.equal(net.calls.length, 0, 'the per-piece button stages a schedule without a backend request');
  assert.equal(saved(), 0);
  await ui.click(button(ui.container, 'Save all schedules'));
  assert.equal(saved(), 1);
  const payload = JSON.parse(String(net.calls[0].options?.body));
  assert.equal(net.calls[0].url, '/api/atelier/packs/pack_1/schedule');
  assert.equal(payload.whole_pack, false);
  assert.equal(payload.items.length, 1);
  assert.equal(payload.items[0].asset_id, 'asset_reel_2');
  assert.equal(payload.items[0].expected_asset_hash, 'hash_reel_2');
  assert.match(payload.items[0].scheduled_for, /T10:30:00\+05:30$/);
  assert.equal(payload.expected_pack_manifest_hash, pack.manifest_hash);
});

test('batch scheduling is explicit and a failed save keeps selections and request ID for retry', async t => {
  const { ui, net, saved } = await open(t, () => net.calls.length === 1 ? json({ detail: { message: 'Another scheduler changed this entry', code: 'stale_schedule' } }, 409) : json({ entries: [] }));
  for (const [i, piece] of pack.pieces.entries()) {
    await ui.click(ui.container.querySelector(`[aria-label="Schedule ${piece.label}"]`));
    await chooseFutureDate(ui, String(15 + i), `${10 + i}:30`);
    await ui.click(button(ui.container, 'Save schedule'));
  }
  assert.equal(net.calls.length, 0);
  await ui.click(button(ui.container, 'Save all schedules'));
  assert.equal(saved(), 0);
  assert.match(ui.container.querySelector('[role="alert"]')?.textContent ?? '', /Another scheduler/);
  assert.equal(ui.container.querySelectorAll('input[type="checkbox"]:checked').length, 5);
  await ui.click(button(ui.container, 'Save all schedules'));
  assert.equal(saved(), 1);
  const first = JSON.parse(String(net.calls[0].options?.body)), second = JSON.parse(String(net.calls[1].options?.body));
  assert.deepEqual(first, second);
  assert.equal(first.whole_pack, true);
  assert.equal(first.items.length, 5);
  assert.equal(new Set(first.items.map((item: { scheduled_for: string }) => item.scheduled_for)).size, 5, 'each piece retains its different date and time');
});

test('rescheduling includes the saved revision and the removed cancellation control stays absent', async t => {
  const future = new Date(); future.setUTCMonth(future.getUTCMonth() + 2);
  const source = { ...pack, pieces: pack.pieces.map(p => p.key === 'reel_2' ? { ...p, schedule: {
    calendar_entry_id: 'calendar_saved', revision: 3, scheduled_for: future.toISOString(), display_timezone: 'Asia/Kolkata', status: 'scheduled' } } : p) };
  const { ui, net } = await open(t, () => json({ entries: [] }), source);
  await ui.click(button(ui.container, 'Next: choose a time'));
  await ui.click(button(ui.container, 'Save schedule'));
  await ui.click(button(ui.container, 'Save all schedules'));
  const item = JSON.parse(String(net.calls[0].options?.body)).items[0];
  assert.equal(item.entry_id, 'calendar_saved'); assert.equal(item.expected_revision, 3);
  assert.equal(button(ui.container, 'Cancel Reel 2 schedule'), null);
  assert.equal(ui.text().includes('Adds only'), false);
});

test('published pieces cannot be selected and empty dates never dispatch a request', async t => {
  const source = { ...pack, pieces: pack.pieces.map(p => p.key === 'email' ? { ...p, published: [{ content_id: 'pub1', piece: 'email', channel: 'email', published_on: '2026-11-01', by: 'tester', at: '2026-11-01' }] } : p) };
  const { ui, net } = await open(t, () => json({}), source);
  assert.equal((ui.container.querySelector('[aria-label="Include Email"]') as HTMLInputElement).disabled, true);
  assert.equal((button(ui.container, 'Save all schedules') as HTMLButtonElement).disabled, true);
  await chooseFutureDate(ui);
  await ui.type(ui.container.querySelector('input[placeholder="09:00"]')!, '');
  await ui.click(button(ui.container, 'Save schedule'));
  assert.equal(net.calls.length, 0);
  assert.match(ui.container.querySelector('[role="alert"]')?.textContent ?? '', /Choose a valid date and time/);
});

test('a superseded pack shows its saved schedule without allowing scheduling', async t => {
  const source = { ...pack, state: 'superseded' as const, pieces: pack.pieces.map(p => p.key === 'reel_2' ? { ...p, schedule: {
    calendar_entry_id: 'old_calendar', revision: 1, scheduled_for: '2026-11-05T04:00:00Z', display_timezone: 'Asia/Kolkata', status: 'scheduled' } } : p) };
  const { ui, net } = await open(t, () => json({}), source);
  assert.equal((button(ui.container, 'Save all schedules') as HTMLButtonElement).disabled, true);
  assert.equal(button(ui.container, 'Cancel Reel 2 schedule'), null);
  assert.equal(net.calls.length, 0);
});

test('two selected schedules keep different times and exclude unstaged edits until saved again', async t => {
  const { ui, net } = await open(t, () => json({ entries: [] }));
  await chooseFutureDate(ui, '15', '10:30');
  await ui.click(button(ui.container, 'Save schedule'));
  await ui.click(ui.container.querySelector('[aria-label="Schedule Carousel"]'));
  await chooseFutureDate(ui, '16', '14:45');
  await ui.click(button(ui.container, 'Save schedule'));
  await ui.type(ui.container.querySelector('input[placeholder="09:00"]')!, '15:45');
  assert.equal((button(ui.container, 'Save all schedules') as HTMLButtonElement).disabled, true);
  await ui.click(button(ui.container, 'Save all schedules'));
  assert.equal(net.calls.length, 0, 'a staged schedule cannot silently use an unconfirmed edit');
  assert.match(ui.text(), /Date or time changed. Click Save schedule to update/);
  await ui.click(button(ui.container, 'Save schedule'));
  await ui.click(button(ui.container, 'Save all schedules'));
  const data = JSON.parse(String(net.calls[0].options?.body));
  assert.equal(data.items.length, 2);
  assert.equal(data.whole_pack, false);
  assert.match(data.items.find((p: { asset_id: string }) => p.asset_id === 'asset_reel_2').scheduled_for, /T10:30:00/);
  assert.match(data.items.find((p: { asset_id: string }) => p.asset_id === 'asset_carousel').scheduled_for, /T15:45:00/);
});

test('same-schedule checkbox copies only untouched unscheduled pieces and can undo its own selection', async t => {
  const source = { ...pack, pieces: pack.pieces.map(p => p.key === 'email' ? { ...p, schedule: {
    calendar_entry_id: 'existing_email', revision: 2, scheduled_for: '2027-01-05T04:00:00Z', display_timezone: 'Asia/Kolkata', status: 'scheduled' } } : p) };
  const { ui, net } = await open(t, () => json({ entries: [] }), source);
  await ui.click(ui.container.querySelector('[aria-label="Schedule Carousel"]'));
  await chooseFutureDate(ui, '16', '16:45');
  await ui.click(button(ui.container, 'Save schedule'));
  await ui.click(ui.container.querySelector('[aria-label="Schedule Reel 2"]'));
  await chooseFutureDate(ui, '15', '10:30');
  await ui.click(button(ui.container, 'Save schedule'));
  const same = () => ui.container.querySelector('label input[type="checkbox"]') as HTMLInputElement;
  await ui.tick(same());
  assert.equal(net.calls.length, 0, 'checking the option stages choices without a request');
  assert.equal(ui.container.querySelectorAll('input[aria-label^="Include"]:checked').length, 4);
  assert.equal((ui.container.querySelector('[aria-label="Include Email"]') as HTMLInputElement).checked, false);
  await ui.tick(same());
  assert.equal(ui.container.querySelectorAll('input[aria-label^="Include"]:checked').length, 2, 'unchecking removes only copied schedules');
  await ui.tick(same());
  await ui.click(button(ui.container, 'Save all schedules'));
  const data = JSON.parse(String(net.calls[0].options?.body));
  assert.equal(data.items.length, 4);
  assert.equal(data.whole_pack, false);
  assert.ok(!data.items.some((p: { asset_id: string }) => p.asset_id === 'asset_email'));
  assert.match(data.items.find((p: { asset_id: string }) => p.asset_id === 'asset_carousel').scheduled_for, /T16:45:00/);
  for (const key of ['reel_1', 'reel_2', 'reel_3']) {
    assert.equal(data.items.find((p: { asset_id: string }) => p.asset_id === `asset_${key}`).scheduled_for,
      data.items.find((p: { asset_id: string }) => p.asset_id === 'asset_reel_2').scheduled_for);
  }
});

test('a pack in review can stage and save a schedule without marking it ready', async t => {
  const source = { ...pack, state: 'in_review' as const, approval_status: 'pending', approved_by: null, approved_at: null };
  const { ui, net, saved } = await open(t, () => json({ entries: [] }), source);
  await chooseFutureDate(ui);
  await ui.click(button(ui.container, 'Save schedule'));
  await ui.click(button(ui.container, 'Save all schedules'));
  assert.equal(saved(), 1);
  assert.equal(net.calls.length, 1);
  assert.equal(net.calls[0].url, '/api/atelier/packs/pack_1/schedule');
  assert.equal(source.state, 'in_review');
  assert.equal(source.approval_status, 'pending');
});

test('the Schedule trigger is enabled for an in-review pack with no existing schedules', async t => {
  const client = createQueryClient();
  client.setQueryData(queryKey('/flags'), { calendar: true, packs: true, briefs: true, context: false });
  client.setQueryData(queryKey('/calendar/config'), config);
  const net = stubFetch(() => json(config)); t.after(net.restore);
  const ui = await mount(<PackScheduling pack={{ ...pack, state: 'in_review', approval_status: 'pending' }} active="email" busy={false} />, { client });
  t.after(() => ui.unmount());
  const trigger = button(ui.container, 'Schedule') as HTMLButtonElement;
  assert.equal(trigger.disabled, false);
  await ui.click(trigger);
  assert.ok(document.querySelector('[role="dialog"]'));
});

test('selecting a piece immediately checks it without staging or submitting its schedule', async t => {
  const { ui, net } = await open(t, () => json({ entries: [] }));
  const included = (label: string) => ui.container.querySelector(`[aria-label="Include ${label}"]`) as HTMLInputElement;
  assert.equal(included('Reel 2').checked, true);
  await ui.click(ui.container.querySelector('[aria-label="Schedule Carousel"]'));
  assert.equal(included('Carousel').checked, true);
  assert.equal(included('Reel 2').checked, true);
  assert.equal(included('Email').disabled, false);
  await ui.tick(included('Email'));
  assert.equal(included('Email').checked, true);
  assert.match(ui.text(), /Email: choose a date/);
  assert.equal(net.calls.length, 0);
  assert.equal((button(ui.container, 'Save all schedules') as HTMLButtonElement).disabled, true);
});
