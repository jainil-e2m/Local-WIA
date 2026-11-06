import { expect, test } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { PACK, SUMMARY } from '../../src/testing/packFixtures';
import type { SavedSchedule } from '../../src/api/types';
import { startAtelier, type Atelier } from './server';
import { SESSION_COOKIE, SESSION_TOKEN } from './stubs';

let atelier: Atelier;
test.beforeAll(async () => { atelier = await startAtelier(); });
test.afterAll(async () => { await atelier?.stop(); });

test('manual publication in the actual pack UI and calendar, with persisted marks and mobile layout', async ({ page, context }) => {
  let pack = structuredClone(PACK);
  const writes: { path: string; body: Record<string, unknown> }[] = [];
  const failures: string[] = [];
  let calendarWarning = false;
  page.on('pageerror', error => failures.push(error.message));
  const entry: SavedSchedule = { calendar_entry_id: 'calendar_carousel', asset_id: 'asset_carousel', asset_content_hash: 'hash_carousel',
    pack_id: PACK.pack_id, pack_manifest_hash: PACK.manifest_hash!, scheduled_for: '2026-11-04T05:30:00Z', status: 'scheduled', effective_status: 'scheduled',
    revision: 1, display_timezone: 'Asia/Kolkata', format: 'carousel', slot_key: 'carousel', title: 'When more inquiries are not enough',
    pack_title: PACK.title, week_id: PACK.week_id, warnings: [], overdue: true };
  // Synthetic provider responses exercise the real application without touching deployment data.
  await page.route('**/api/atelier/**', async route => {
    const request = route.request(), url = new URL(request.url()), endpoint = url.pathname.replace('/api/atelier', '');
    const send = (body: unknown) => route.fulfill({ json: body });
    if (endpoint === '/flags') return send({ briefs: true, packs: true, calendar: true, context: false });
    if (endpoint === '/calendar/config') return send({ enabled: true, display_timezone: 'Asia/Kolkata', can_schedule: true, worker_ready: true });
    if (endpoint === '/calendar') {
      expect(url.searchParams.get('status')).toBe('all');
      const publication = pack.pieces.find(piece => piece.key === 'carousel')?.published[0] ?? null;
      return send({ items: [{ ...entry, publication, effective_status: publication ? 'published' : 'scheduled', overdue: !publication,
        warnings: calendarWarning ? ['A replacement pack exists'] : [] }], next_cursor: null });
    }
    if (endpoint === '/packs') return send({ items: [{ ...SUMMARY, pieces: SUMMARY.pieces.map(piece => ({ ...piece,
      published: !!pack.pieces.find(item => item.key === piece.key)?.published.length })) }], total: 1 });
    if (endpoint === `/packs/${PACK.pack_id}`) return send(pack);
    const key = /^\/packs\/pack_1\/pieces\/([^/]+)\/published$/.exec(endpoint)?.[1];
    if (key && request.method() === 'POST') {
      const body = request.postDataJSON(); writes.push({ path: endpoint, body });
      pack = { ...pack, pieces: pack.pieces.map(piece => piece.key === key ? { ...piece, published: [{ content_id: `published_${key}`,
        piece: piece.key, channel: body.channel, published_on: body.published_on, url: body.url, by: 'approver@example.invalid', at: new Date().toISOString() }] } : piece) };
      return send({ pack_id: PACK.pack_id, piece: key, content_id: `published_${key}`, state: 'in_review' });
    }
    return route.continue();
  });
  await context.addCookies([{ name: SESSION_COOKIE, value: SESSION_TOKEN, url: atelier.origin, httpOnly: true, sameSite: 'Lax' }]);
  const screenshots = path.resolve('../.qa/publication-ui');
  await mkdir(screenshots, { recursive: true });
  await page.goto(`${atelier.origin}/studio/packs/pack_1?piece=carousel`);
  await expect(page.getByRole('button', { name: 'Mark as Published', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ready to publish', exact: true })).toHaveCount(0);
  await expect(page.getByRole('progressbar')).toHaveCount(0);
  await page.screenshot({ path: path.join(screenshots, 'pack.png') });
  await page.getByRole('button', { name: 'Mark as Published', exact: true }).click();
  let dialog = page.getByRole('dialog', { name: 'Mark Carousel as published' });
  await expect(dialog).toBeVisible();
  await page.screenshot({ path: path.join(screenshots, 'confirmation.png') });
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  await page.getByRole('tab', { name: 'Email', exact: true }).click();
  await page.getByRole('button', { name: 'Mark as Published', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm Sent', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Sent · View details', exact: true })).toBeVisible();
  expect(writes[0].path).toBe('/packs/pack_1/pieces/email/published');
  expect(writes[0].body.channel).toBe('email');

  await page.goto(`${atelier.origin}/calendar?month=2026-11`);
  const calendarAction = page.getByRole('button', { name: `Mark ${entry.title} as published`, exact: true });
  await expect(calendarAction).toBeVisible();
  await page.screenshot({ path: path.join(screenshots, 'calendar.png') });
  // The expanded day agenda offers the same action; its View action still opens the linked pack.
  await page.locator('.atelier-calendar-cell').filter({ has: calendarAction }).getByRole('button', { name: '4', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText(entry.title);
  await page.screenshot({ path: path.join(screenshots, 'day-agenda.png') });
  await page.getByRole('dialog').getByRole('button', { name: `Mark ${entry.title} as published`, exact: true }).click();
  dialog = page.getByRole('dialog', { name: 'Mark Carousel as published' });
  await dialog.getByRole('textbox', { name: 'Link to the post (optional)' }).fill('https://www.instagram.com/p/example/');
  await dialog.getByRole('button', { name: 'Confirm Published', exact: true }).click();
  await expect(page.getByText('✓ Published · Manual', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText('✓ Published · Manual', { exact: true })).toBeVisible();
  await expect(calendarAction).toHaveCount(0);
  calendarWarning = true;
  await page.reload();
  await expect(page.getByText('✓ Published · Manual', { exact: true })).toBeVisible();
  await expect(page.getByText('Needs attention', { exact: true })).toBeVisible();
  await expect(page.getByText('Overdue', { exact: true })).toHaveCount(0);
  expect(writes.map(write => write.path)).toEqual(['/packs/pack_1/pieces/email/published', '/packs/pack_1/pieces/carousel/published']);

  await page.goto(`${atelier.origin}/studio/packs/pack_1?piece=carousel`);
  await expect(page.getByRole('button', { name: 'Published · View details', exact: true })).toBeVisible();
  await expect(page.getByRole('list', { name: 'Carousel: published', exact: true }).getByText('Manually marked · Not verified on platform')).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Published · View details', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.screenshot({ path: path.join(screenshots, 'mobile-details.png') });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(failures).toEqual([]);
});
