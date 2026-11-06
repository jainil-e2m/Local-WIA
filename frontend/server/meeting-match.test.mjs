import { describe, expect, it } from "vitest";
import {
  MATCH_WINDOW_DAYS,
  bookingDiffersFromLead,
  chooseLeadForBooking,
  matchRank,
} from "./meeting-match.mjs";

const NOW = Date.parse("2026-08-31T12:00:00.000Z");
const daysAgo = (days) => new Date(NOW - days * 24 * 60 * 60 * 1000).toISOString();

const lead = (overrides = {}) => ({
  id: "lead_1",
  name: "Charles Schein",
  email: "charles@scheinnc.com",
  phone: "704-275-2607",
  timestamp: daysAgo(1),
  ...overrides,
});

const event = (overrides = {}) => ({
  eventId: "evt_1",
  bookedEmail: "charles@scheinnc.com",
  bookedName: "Charles Schein",
  bookedPhone: "+17042752607",
  ...overrides,
});

describe("matchRank", () => {
  it("ranks a previously seen booking first", () => {
    expect(matchRank(lead({ meetingEventId: "evt_1" }), event())).toBe(0);
  });

  it("matches on email, ignoring case", () => {
    expect(matchRank(lead(), event({ bookedEmail: "CHARLES@ScheinNC.com" }))).toBe(1);
  });

  it("falls back to name when the email differs", () => {
    expect(matchRank(lead(), event({ bookedEmail: "charles@gmail.com" }))).toBe(2);
  });

  it("falls back to phone when both name and email differ", () => {
    const rank = matchRank(
      lead(),
      event({ bookedEmail: "someone@else.com", bookedName: "Someone Else" }),
    );
    expect(rank).toBe(3);
  });

  it("matches a phone written in different formats", () => {
    // The funnel stores what was typed; zcal returns E.164.
    const e = event({ bookedEmail: "x@y.com", bookedName: "X", bookedPhone: "+1 704 275 2607" });
    expect(matchRank(lead({ phone: "(704) 275-2607" }), e)).toBe(3);
  });

  it("does not match on a short phone fragment", () => {
    const e = event({ bookedEmail: "x@y.com", bookedName: "X", bookedPhone: "2607" });
    expect(matchRank(lead(), e)).toBeNull();
  });

  it("returns null when nothing lines up", () => {
    const e = event({ bookedEmail: "x@y.com", bookedName: "X", bookedPhone: "+19998887777" });
    expect(matchRank(lead(), e)).toBeNull();
  });
});

describe("chooseLeadForBooking", () => {
  it("returns null when there are no candidates", () => {
    expect(chooseLeadForBooking([], event(), { now: NOW })).toBeNull();
    expect(chooseLeadForBooking(null, event(), { now: NOW })).toBeNull();
  });

  it("prefers a stronger match over a more recent one", () => {
    const byName = lead({ id: "lead_new", email: "other@example.com", timestamp: daysAgo(0) });
    const byEmail = lead({ id: "lead_old", timestamp: daysAgo(5) });
    const chosen = chooseLeadForBooking([byName, byEmail], event(), { now: NOW });
    expect(chosen.id).toBe("lead_old");
  });

  it("prefers a lead with no booking over one already booked elsewhere", () => {
    const alreadyBooked = lead({ id: "lead_booked", meetingEventId: "evt_other", timestamp: daysAgo(0) });
    const free = lead({ id: "lead_free", timestamp: daysAgo(2) });
    const chosen = chooseLeadForBooking([alreadyBooked, free], event(), { now: NOW });
    expect(chosen.id).toBe("lead_free");
  });

  it("breaks a tie on the most recent capture", () => {
    const older = lead({ id: "lead_older", timestamp: daysAgo(9) });
    const newer = lead({ id: "lead_newer", timestamp: daysAgo(2) });
    expect(chooseLeadForBooking([older, newer], event(), { now: NOW }).id).toBe("lead_newer");
  });

  it("ignores leads captured outside the matching window", () => {
    const ancient = lead({ timestamp: daysAgo(MATCH_WINDOW_DAYS + 1) });
    expect(chooseLeadForBooking([ancient], event(), { now: NOW })).toBeNull();
  });

  it("still finds a known booking outside the window", () => {
    // A call booked in time can be cancelled months later.
    const ancient = lead({ timestamp: daysAgo(400), meetingEventId: "evt_1" });
    expect(chooseLeadForBooking([ancient], event(), { now: NOW })?.id).toBe("lead_1");
  });

  it("updates the same lead on a reschedule rather than picking another", () => {
    const booked = lead({ id: "lead_booked", meetingEventId: "evt_1", timestamp: daysAgo(10) });
    const newer = lead({ id: "lead_newer", timestamp: daysAgo(1) });
    const chosen = chooseLeadForBooking([booked, newer], event({ eventId: "evt_1" }), { now: NOW });
    expect(chosen.id).toBe("lead_booked");
  });
});

describe("chooseLeadForBooking — cancellations", () => {
  const cancel = (over = {}) => event({ type: "event.cancelled", status: "cancelled", ...over });

  it("cancels the booking it names", () => {
    const booked = lead({ meetingEventId: "evt_1" });
    expect(chooseLeadForBooking([booked], cancel(), { now: NOW })?.id).toBe("lead_1");
  });

  it("will not cancel a booking it does not name, even on a perfect email match", () => {
    // The lead holds a different, live booking. A cancellation for evt_1 must not
    // reach in and mark that one cancelled.
    const otherBooking = lead({ meetingEventId: "evt_other" });
    expect(chooseLeadForBooking([otherBooking], cancel({ eventId: "evt_1" }), { now: NOW })).toBeNull();
  });

  it("will not attach a cancellation to a lead that never booked", () => {
    expect(chooseLeadForBooking([lead()], cancel(), { now: NOW })).toBeNull();
  });

  it("still applies a reschedule found by its event id", () => {
    const booked = lead({ meetingEventId: "evt_1" });
    const rescheduled = event({ type: "event.rescheduled" });
    expect(chooseLeadForBooking([booked], rescheduled, { now: NOW })?.id).toBe("lead_1");
  });
});

describe("bookingDiffersFromLead", () => {
  it("is false when the booking used the submitted details", () => {
    expect(
      bookingDiffersFromLead(lead(), {
        bookedEmail: "charles@scheinnc.com",
        bookedName: "Charles Schein",
      }),
    ).toBe(false);
  });

  it("ignores case differences", () => {
    expect(
      bookingDiffersFromLead(lead(), {
        bookedEmail: "Charles@ScheinNC.com",
        bookedName: "charles schein",
      }),
    ).toBe(false);
  });

  it("is true when the email differs", () => {
    expect(
      bookingDiffersFromLead(lead(), {
        bookedEmail: "charles@gmail.com",
        bookedName: "Charles Schein",
      }),
    ).toBe(true);
  });

  it("is true when the name differs", () => {
    expect(
      bookingDiffersFromLead(lead(), {
        bookedEmail: "charles@scheinnc.com",
        bookedName: "Chuck S",
      }),
    ).toBe(true);
  });

  it("does not report a mismatch when the booking gave no name", () => {
    expect(
      bookingDiffersFromLead(lead(), { bookedEmail: "charles@scheinnc.com", bookedName: null }),
    ).toBe(false);
  });
});
