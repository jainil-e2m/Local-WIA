// Run only against an isolated fixture deployment. Authentication cookie is test-only.
import assert from "node:assert/strict";
const { chromium, expect } = await import(
  process.env.PLAYWRIGHT_MODULE || "@playwright/test"
);
const origin = process.env.ATELIER_E2E_ORIGIN;
if (!origin || !/^http:\/\/127\.0\.0\.1:\d+$/.test(origin))
  throw new Error("Set a loopback-only ATELIER_E2E_ORIGIN.");
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROME_PATH,
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  timezoneId: "Asia/Kolkata",
});
await context.addCookies([
  { name: "wahha_session", value: "calendar-test-only", url: origin },
]);
const page = await context.newPage();
const failures = [];
page.on("pageerror", (e) => failures.push(e.message));
const calendar = async (p) => {
  const response = await p.request.get(
    origin +
      "/api/atelier/calendar?" +
      new URLSearchParams({
        from: new Date(Date.now() - 86400000).toISOString(),
        to: new Date(Date.now() + 60 * 86400000).toISOString(),
      }),
  );
  assert.equal(response.status(), 200, await response.text());
  return (await response.json()).items;
};
const date = (days) =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(Date.now() + days * 86400000));
try {
  await page.goto(origin);
  await page.getByRole("button", { name: "Home", exact: true }).click();
  await expect(
    page.getByText("No scheduled content in this month."),
  ).toBeVisible();
  assert.equal((await calendar(page)).length, 0);
  await page
    .getByRole("button", { name: "Weekly Studio", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Content Briefing", exact: true })
    .click();
  await page
    .getByRole("button", { name: /A bounded follow-up review.*approved/ })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Generate saved content pack", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Saved content pack" });
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Approve exact pack", exact: true }),
  ).toBeVisible({ timeout: 90000 });
  await dialog.getByRole("checkbox").check();
  await dialog
    .getByRole("button", { name: "Approve exact pack", exact: true })
    .click();
  await expect(
    dialog.getByRole("button", {
      name: "Schedule all five pieces",
      exact: true,
    }),
  ).toBeEnabled();
  await dialog
    .getByRole("button", { name: "Schedule all five pieces", exact: true })
    .click();
  await dialog.getByLabel("Publishing date", { exact: true }).fill(date(1));
  await dialog.getByLabel("Publishing time", { exact: true }).fill("10:15");
  // A failed save must keep the picker and proposed time, without adding any entry.
  await page.route(
    "**/api/atelier/packs/*/schedule",
    (r) =>
      r.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ error: "Temporary acceptance failure" }),
      }),
    { times: 1 },
  );
  await dialog
    .getByRole("button", { name: "Confirm schedule", exact: true })
    .click();
  await expect(dialog.getByRole("alert")).toContainText(
    "Temporary acceptance failure",
  );
  await expect(
    dialog.getByLabel("Publishing date", { exact: true }),
  ).toHaveValue(date(1));
  assert.equal((await calendar(page)).length, 0);
  await dialog
    .getByRole("button", { name: "Confirm schedule", exact: true })
    .click();
  await expect(dialog.getByText(/5\/5 pieces scheduled/)).toBeVisible();
  assert.equal((await calendar(page)).length, 5);
  await dialog.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("button", { name: "Home", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Content Calendar", exact: true }),
  ).toBeVisible();
  const first = (await calendar(page))[0];
  await page
    .getByRole("button")
    .filter({ hasText: first.title })
    .first()
    .click();
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("heading", { name: first.title, exact: true }),
  ).toBeVisible();
  await dialog.getByRole("button", { name: "Reschedule", exact: true }).click();
  await dialog.getByLabel("Publishing date", { exact: true }).fill(date(2));
  await dialog.getByLabel("Publishing time", { exact: true }).fill("11:45");
  await dialog
    .getByRole("button", { name: "Confirm schedule", exact: true })
    .click();
  await expect(
    dialog.getByRole("button", { name: "Confirm schedule", exact: true }),
  ).toHaveCount(0);
  await expect
    .poll(
      async () =>
        (await calendar(page)).find(
          (e) => e.calendar_entry_id === first.calendar_entry_id,
        )?.revision,
    )
    .toBe(2);
  await dialog.getByRole("button", { name: "Close", exact: true }).click();
  await page.reload();
  await page.getByRole("button", { name: "Home", exact: true }).click();
  assert.equal((await calendar(page)).length, 5);
  const other = await browser.newContext({ timezoneId: "Asia/Kolkata" });
  await other.addCookies([
    { name: "wahha_session", value: "calendar-test-only", url: origin },
  ]);
  const second = await other.newPage();
  await second.goto(origin);
  await second.getByRole("button", { name: "Home", exact: true }).click();
  assert.equal((await calendar(second)).length, 5);
  await second
    .getByRole("button", { name: "Weekly Studio", exact: true })
    .click();
  await second
    .getByRole("button", { name: "Scheduled Content", exact: true })
    .click();
  await expect(
    second.getByText("Saved backend content · 5 scheduled pieces"),
  ).toBeVisible();
  await page
    .getByRole("button")
    .filter({ hasText: first.title })
    .first()
    .click();
  await dialog
    .getByRole("button", { name: "Cancel schedule", exact: true })
    .click();
  await expect(
    dialog.getByRole("button", { name: "Cancel schedule", exact: true }),
  ).toHaveCount(0);
  assert.equal((await calendar(page)).length, 4);
  await dialog.getByRole("button", { name: "Close", exact: true }).click();
  await page.screenshot({
    path: process.env.ATELIER_E2E_SCREENSHOT || "../.qa/calendar-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".atelier-sidebar")).toHaveAttribute(
    "data-collapsed",
    "true",
  );
  await page
    .getByLabel("Calendar selected date", { exact: true })
    .fill(date(1));
  await expect(
    page.getByRole("heading", { name: "Content Calendar", exact: true }),
  ).toBeVisible();
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  );
  await page.screenshot({ path: "../.qa/calendar-mobile.png", fullPage: true });
  await other.close();
  assert.deepEqual(failures, []);
  console.log(
    "PASS: real brief replay → pack approval → failed-save recovery → five schedules → asset drilldown → reschedule → refresh/second browser → cancellation. No external model calls.",
  );
} catch (error) {
  await page.screenshot({
    path: "../.qa/calendar-failure.png",
    fullPage: true,
  });
  throw error;
} finally {
  await context.close();
  await browser.close();
}
