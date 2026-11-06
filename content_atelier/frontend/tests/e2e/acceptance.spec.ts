/// <reference types="node" />
/* 6.X1: the acceptance path in a real browser, through the real Node server. Chromium signs in with a session cookie that the
   stubbed Command Center accepts; the Node server (server/index.mjs, as deployed) serves the real build and relays the app's
   requests to the stubbed backend: Home shows the cycle summary, the Weekly Studio shows a card (its full screen in the review
   dialog), the card is developed at Gate 1 from its card, its brief (read in full in the brief dialog) is approved at Gate 2
   from its card, the content pack opens, and the week's documents download. */
import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { startAtelier, type Atelier } from './server';
import { DOCX_BYTES, SESSION_COOKIE, SESSION_TOKEN, WEEK_ID } from './stubs';

let atelier: Atelier;
test.beforeAll(async () => { atelier = await startAtelier(); });
test.afterAll(async () => { await atelier?.stop(); });

test('6.X1: Home, Gate 1, Gate 2, the content pack and the week\'s documents, in a real browser through the Node server', async ({ page, context }) => {
  const { origin, stubs } = atelier;
  await context.addCookies([{ name: SESSION_COOKIE, value: SESSION_TOKEN, url: origin, httpOnly: true, sameSite: 'Lax' }]);
  const failures: string[] = [];
  page.on('pageerror', error => failures.push(error.message));

  // Home: the cycle summary, a few plain lines with links.
  await page.goto(`${origin}/home`);
  const home = page.getByRole('region', { name: 'This week' });
  await expect(home.getByText('1 angle waiting for your review.')).toBeVisible();
  await expect(home.getByText(/^Next cycle: Sunday 1 November at \d{1,2}:\d{2} a\.m\. Chicago time\.$/)).toBeVisible();
  await home.getByRole('listitem').filter({ hasText: 'angle waiting for your review' }).getByRole('link', { name: 'Review' }).click();

  // The Weekly Studio, as the 20 October mockup: the stepper, and the week's card awaiting approval.
  await expect(page).toHaveURL(`${origin}/studio/angles/${WEEK_ID}`);
  await expect(page.getByRole('navigation', { name: 'Editorial pipeline' })).toContainText('1 waiting · 0 approved · 0 generated');
  const waiting = page.getByRole('region', { name: 'Angles awaiting approval' });
  await expect(waiting.getByRole('heading', { name: 'Why we read the reply first' })).toBeVisible();
  // The week's machinery is not in the Studio any more (it is on Sources, for administrators).
  await expect(page.getByText('Cycle details', { exact: true })).toHaveCount(0);

  // "Review angle" opens the full card screen in the review dialog, at the card's own URL.
  await waiting.getByRole('button', { name: 'Review angle: Why we read the reply first' }).click();
  await expect(page).toHaveURL(`${origin}/studio/angles/${WEEK_ID}/angle_1`);
  const dialog = page.getByRole('dialog', { name: 'Review angle: Why we read the reply first' });
  await expect(dialog.getByRole('button', { name: 'Save decision' })).toBeVisible();
  await dialog.getByRole('button', { name: 'Done' }).click();
  await expect(page).toHaveURL(`${origin}/studio/angles/${WEEK_ID}`);

  // Gate 1 from the card: "Approve & create brief" develops it (nothing to confirm on this card).
  await waiting.getByRole('button', { name: 'Approve & create brief' }).click();
  await expect.poll(() => stubs.writes.map(w => `${w.method} ${w.path}`)).toContain('POST /angles/angle_1/decision');
  expect(stubs.writes[0].body).toMatchObject({ disposition: 'develop', expected_hash: 'hash_card', cta: { choice: 'decide_in_development' } });
  // Said twice: to a screen reader, and in the visible confirmation.
  await expect(page.getByText('Approved. Its brief is being written, which takes 15 to 30 minutes.').first()).toBeAttached();
  await expect(page.locator('[data-confirmation]')).toHaveText('Approved. Its brief is being written, which takes 15 to 30 minutes.');

  // Gate 2: the approved card leads to its brief in the Content Briefing step; the full brief opens in its dialog.
  const approvedCards = page.getByRole('region', { name: 'Approved angles' });
  await approvedCards.getByRole('link', { name: 'Open brief' }).click();
  await expect(page).toHaveURL(`${origin}/studio/briefs?week=${WEEK_ID}#brief-brief_v4`);
  const briefs = page.getByRole('region', { name: 'Briefs awaiting approval' });
  await briefs.getByRole('link', { name: 'Read full brief: Why we read the reply first' }).click();
  await expect(page).toHaveURL(`${origin}/studio/briefs/brief_v4?week=${WEEK_ID}`);
  const briefDialog = page.getByRole('dialog', { name: /Brief: / });
  await expect(briefDialog.getByRole('button', { name: 'Approve brief and create content pack' })).toBeVisible();
  await briefDialog.getByRole('button', { name: 'Done' }).click();
  await expect(page).toHaveURL(`${origin}/studio/briefs?week=${WEEK_ID}`);

  // "Approve & generate pack" on the card: the approval creates the content pack.
  await briefs.getByRole('button', { name: 'Approve & generate pack' }).click();
  await expect.poll(() => stubs.writes.map(w => `${w.method} ${w.path}`)).toContain('POST /briefs/brief_v4/decision');
  expect(stubs.writes.at(-1)?.body).toMatchObject({ decision: 'approved', expected_hash: 'h4' });
  const approvedBriefs = page.getByRole('region', { name: 'Approved briefs' });
  await approvedBriefs.getByRole('link', { name: 'Open pack' }).click();

  // The content pack opens.
  await expect(page).toHaveURL(`${origin}/studio/packs/pack_1`);
  await expect(page.getByRole('heading', { name: 'Why we read the reply first' }).first()).toBeVisible();
  await expect(page.getByRole('tablist', { name: 'Content pack pieces' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Copy the whole pack/ })).toBeVisible();
  // The review panel beside the pack is gone (26 October): no notes, versions or "Finish again" on the page.
  await expect(page.getByRole('complementary', { name: 'Review the pack' })).toHaveCount(0);

  // The week's documents, as Word files, byte for byte: the packs from the Content Packs step, the review from the Weekly
  // Studio's "Download review".
  const download = async (name: string) => {
    const [file] = await Promise.all([page.waitForEvent('download'), page.getByRole('link', { name, exact: true }).first().click()]);
    return { name: file.suggestedFilename(), bytes: await readFile(await file.path()) };
  };
  await page.goto(`${origin}/studio/packs?week=${WEEK_ID}`);
  const packsDocx = await download("Download the week's packs");
  expect(packsDocx.name).toBe(`content-atelier-packs-${WEEK_ID}.docx`);
  expect(packsDocx.bytes.equals(DOCX_BYTES)).toBe(true);

  await page.goto(`${origin}/studio/angles/${WEEK_ID}`);
  const reviewDocx = await download('Download review');
  expect(reviewDocx.name).toBe(`content-atelier-review-${WEEK_ID}.docx`);
  expect(reviewDocx.bytes.equals(DOCX_BYTES)).toBe(true);

  expect(stubs.unanswered, 'every backend request the path made had an answer').toEqual([]);
  expect(failures, 'no error on the page').toEqual([]);
});
