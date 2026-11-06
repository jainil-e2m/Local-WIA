import { defineConfig, devices } from '@playwright/test';

/* The browser end-to-end test (6.X1): a real Chromium against the real Node server (server/index.mjs) serving the real build,
   with Command Center's session endpoint and the Python backend stubbed (tests/e2e/stubs.ts). `npm run test:e2e` builds the
   app first (tests/e2e/build.ts); `npx playwright install chromium` provides the browser. */
export default defineConfig({
  testDir: 'tests/e2e',
  testMatch: '*.spec.ts',
  globalSetup: './tests/e2e/build.ts',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? [['list'], ['github']] : 'list',
  outputDir: 'test-results/e2e',
  use: {
    ...devices['Desktop Chrome'],
    viewport: { width: 1440, height: 1000 },
    timezoneId: 'America/Chicago',
    locale: 'en-US',
    acceptDownloads: true,
    trace: 'retain-on-failure',
  },
});
