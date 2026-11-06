import React from "react";
import { test } from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import { ContentCalendar, buildCivilMonth } from "./ContentCalendar";
import { civilInstant, monthRange, calendarEntries } from "../utils/production";
import { SavedSchedule } from "../api/types";

const entry: SavedSchedule = {
  calendar_entry_id: "calendar_saved",
  asset_id: "asset_email",
  asset_content_hash: "hash",
  pack_id: "pack_saved",
  pack_manifest_hash: "manifest",
  scheduled_for: "2026-10-16T19:00:00Z",
  status: "scheduled",
  effective_status: "scheduled",
  revision: 1,
  display_timezone: "Asia/Kolkata",
  format: "email",
  slot_key: "email",
  title: "Persisted email at midnight",
  pack_title: "Real saved pack",
  week_id: "week_2026-10-12",
  warnings: [],
  overdue: false,
};
const render = (entries: SavedSchedule[], year = 2026, month = 9) =>
  renderToStaticMarkup(
    <ContentCalendar
      entries={entries}
      timezone="Asia/Kolkata"
      initialMonth={{ year, month }}
      onOpenEntry={() => {}}
    />,
  );
test("empty calendar never injects demo or local idea postings, including October", () => {
  const html = render([]);
  assert.equal((html.match(/Persisted email/g) || []).length, 0);
  assert.ok(!html.includes("planner who stopped"));
  assert.ok(!html.includes("Wedding Calendar"));
  assert.ok(html.includes("October 2026"));
});
test("only saved entries in the viewed local month appear, with the exact asset title", () => {
  const html = render([entry]);
  assert.ok(html.includes(entry.title));
  assert.ok(html.includes("00:30"));
  assert.ok(!render([entry], 2026, 10).includes(entry.title));
  assert.ok(
    render([{ ...entry, effective_status: "needs_review" }]).includes(
      "Needs attention",
    ),
  );
});

test('calendar completion comes from the backend and retains the original planned date', () => {
  const html = render([{ ...entry, effective_status: 'published', overdue: false,
    publication: { content_id: 'publication_one', piece: 'email', channel: 'email', published_on: '2026-10-17',
      url: null, by: 'editor@example.invalid', at: '2026-10-17T10:00:00Z' } }]);
  assert.match(html, /Sent · Manual/);
  assert.doesNotMatch(html, /Overdue|Needs attention/);
  assert.match(html, /00:30/);
});

test('publication does not hide genuine content warnings or turn a completed piece overdue again', () => {
  const html = render([{ ...entry, effective_status: 'published', overdue: false,
    warnings: ['A replacement pack exists'] }]);
  assert.match(html, /Sent · Manual/);
  assert.match(html, /Needs attention/);
  assert.doesNotMatch(html, /Overdue/);
});
test("IST range and civil conversion round-trip midnight across a UTC boundary", () => {
  assert.equal(
    civilInstant("2026-10-17", "00:30", "Asia/Kolkata"),
    "2026-10-17T00:30:00+05:30",
  );
  assert.equal(
    new Date(civilInstant("2026-10-17", "00:30", "Asia/Kolkata")).toISOString(),
    new Date(entry.scheduled_for).toISOString(),
  );
  assert.equal(
    monthRange(2026, 11, "Asia/Kolkata").to,
    "2027-01-01T00:00:00+05:30",
  );
  assert.equal(
    buildCivilMonth({ year: 2028, month: 1 }).filter((c) => c.inMonth).length,
    29,
  );
});
test("invalid dates, DST gaps and ambiguous folds are rejected", () => {
  assert.throws(() => civilInstant("2026-02-30", "09:00", "Asia/Kolkata"));
  assert.throws(
    () => civilInstant("2026-03-08", "02:30", "America/Chicago"),
    /does not exist/,
  );
  assert.throws(
    () => civilInstant("2026-11-01", "01:30", "America/Chicago"),
    /occurs twice/,
  );
});
test("calendar data loader follows all pages and propagates failures without mock fallback", async () => {
  const original = globalThis.fetch;
  let calls = 0;
  try {
    globalThis.fetch = async () =>
      Response.json({
        items: [{ ...entry, calendar_entry_id: "entry_" + calls }],
        next_cursor: ++calls === 1 ? 200 : null,
      });
    const entries = await calendarEntries(
      "2026-10-01T00:00:00Z",
      "2026-11-01T00:00:00Z",
    );
    assert.equal(entries.length, 2);
    assert.equal(calls, 2);
    globalThis.fetch = async () =>
      Response.json(
        { detail: { message: "Database unavailable", code: "unavailable" } },
        { status: 503 },
      );
    await assert.rejects(
      calendarEntries("2026-10-01T00:00:00Z", "2026-11-01T00:00:00Z"),
      /Database unavailable/,
    );
  } finally {
    globalThis.fetch = original;
  }
});
