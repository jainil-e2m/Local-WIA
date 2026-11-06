/// <reference types="node" />
/* 6.X5: how many Command Center session checks the Node server makes for a typical page load, and for an open tab left idle
   for five minutes. The server checks the session with Command Center on every request it serves behind sign-in (the page,
   each compiled asset, every /api/atelier call) and relays the app's own session checks (/api/auth/session), so that a
   revoked session stops working at once (frontend/AUTH.md; Command Center's DEPLOY.md). The stubbed Command Center counts
   them; the page's clock is the test's, so five idle minutes pass in seconds. The numbers and the decision are in
   frontend/README.md ("Session checks"); the bounds below catch a change that multiplies them. */
import { expect, test } from '@playwright/test';
import { startAtelier, type Atelier } from './server';
import { SESSION_COOKIE, SESSION_TOKEN } from './stubs';

let atelier: Atelier;
test.beforeAll(async () => { atelier = await startAtelier(); });
test.afterAll(async () => { await atelier?.stop(); });

/** Which kind of request a path is, for the breakdown: each one behind sign-in costs one session check; only the favicon is
    served without one (server/app.mjs). */
const kind = (path: string) => path === '/api/auth/session' ? 'app session check' : path.startsWith('/api/atelier/') ? 'API read'
  : path === '/logos/wia_favicon.png' ? 'public' : 'page or asset';

test('6.X5: the session checks of a page load and of an idle tab over five minutes', async ({ page, context }) => {
  const { origin, stubs } = atelier;
  await context.addCookies([{ name: SESSION_COOKIE, value: SESSION_TOKEN, url: origin, httpOnly: true, sameSite: 'Lax' }]);
  await page.clock.install();
  const requests: string[] = [];
  page.on('request', request => { const url = new URL(request.url()); if (url.origin === origin) requests.push(url.pathname); });
  const tally = (paths: string[]) => paths.reduce<Record<string, number>>((out, path) => ({ ...out, [kind(path)]: (out[kind(path)] ?? 0) + 1 }), {});

  // A typical page load: Home, signed in, until its reads have settled.
  const atStart = stubs.sessionChecks.length;
  await page.goto(`${origin}/home`);
  await expect(page.getByRole('region', { name: 'This week' })).toBeVisible();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);
  const load = stubs.sessionChecks.length - atStart;
  const loadRequests = [...requests];

  // An idle tab: five minutes pass with nobody touching the page, in half-minute steps, the shortest poll's period, so no timer
  // is passed over (a jump fires a due timer at most once).
  const idleFor = async () => {
    const atIdle = stubs.sessionChecks.length, from = requests.length;
    for (let step = 1; step <= 10; step++) {
      await page.clock.fastForward('00:30');
      await page.waitForTimeout(500);
    }
    return { checks: stubs.sessionChecks.length - atIdle, paths: requests.slice(from) };
  };
  const homeIdle = await idleFor();

  // Opening the Weekly Studio from Home, inside the app: no page or asset is loaded again, only the screen's reads.
  const atStudio = stubs.sessionChecks.length;
  const studioFrom = requests.length;
  await page.getByRole('region', { name: 'This week' }).getByRole('listitem').filter({ hasText: 'angle waiting for your review' }).getByRole('link', { name: 'Review' }).click();
  await expect(page.getByRole('heading', { name: 'Why we read the reply first' })).toBeVisible();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);
  const studio = stubs.sessionChecks.length - atStudio;
  const studioRequests = requests.slice(studioFrom);

  // The tab left open and idle for five minutes on that screen: the app's polls and its once-a-minute session check.
  const studioIdle = await idleFor();

  const said = `page load (Home): ${load} session checks ${JSON.stringify(tally(loadRequests))}; Home left idle five minutes: ${homeIdle.checks} `
    + `${JSON.stringify(tally(homeIdle.paths))}; opening the Weekly Studio in the app: ${studio} ${JSON.stringify(tally(studioRequests))}; `
    + `the Weekly Studio left idle five minutes: ${studioIdle.checks} ${JSON.stringify(tally(studioIdle.paths))}`;
  test.info().annotations.push({ type: '6.X5 session checks', description: said });
  console.log(`6.X5 ${said}`);

  // Every request behind sign-in is one check, and nothing else makes one.
  const behindSignIn = (paths: string[]) => paths.filter(path => kind(path) !== 'public').length;
  expect(load).toBe(behindSignIn(loadRequests));
  expect(homeIdle.checks).toBe(behindSignIn(homeIdle.paths));
  expect(studio).toBe(behindSignIn(studioRequests));
  expect(studioIdle.checks).toBe(behindSignIn(studioIdle.paths));
  // The measured counts (README.md: 10, 11, 8 and 36), with room for a read or two more, but not for a check per second or a
  // poll per component.
  expect(load).toBeLessThanOrEqual(15);
  expect(homeIdle.checks).toBeLessThanOrEqual(20);
  expect(studio).toBeLessThanOrEqual(12);
  expect(studioIdle.checks).toBeLessThanOrEqual(50);
});
