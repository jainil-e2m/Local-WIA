import crypto from "node:crypto";
import { describe, expect, it } from "vitest";
import {
  HANDLED_TYPES,
  ZcalWebhookError,
  parseZcalEvent,
  verifyZcalSignature,
} from "./zcal-webhook.mjs";

const SECRET = "test-secret-value";
const sign = (body, secret = SECRET) =>
  crypto.createHmac("sha256", secret).update(body).digest("hex");

/* A payload shaped exactly like zcal's published sample, trimmed to the parts
   this module reads. */
const samplePayload = (overrides = {}) => ({
  type: "event.created",
  created_at: "2026-08-31T05:01:11.469Z",
  data: {
    id: "evt_abc123",
    startDate: "2026-09-01T14:30:00.000Z",
    duration: 30,
    cancelled: false,
    eventName: "Blake Baxendell and Charles Schein",
    location: {
      locationType: "google_meet",
      onlineMeeting: { url: "https://meet.google.com/abc-defg-hij" },
    },
    hosts: [{ name: "Blake Baxendell", email: "blake@wahhadesign.com" }],
    attendees: [
      {
        name: "Charles Schein",
        email: "Charles@ScheinNC.com",
        timezone: "America/New_York",
        phoneNumber: "+17042752607",
        type: "invitee",
        customQuestionAnswers: [{ question: "Anything specific?", answer: "Schema markup" }],
      },
      { email: "guest@example.com", type: "guest" },
    ],
    invite: { id: "UlhbQQ90", name: "30 Minute Meeting", inviteType: "one_on_one" },
    ...overrides,
  },
});

describe("verifyZcalSignature", () => {
  it("accepts a signature over the raw body", () => {
    const raw = JSON.stringify(samplePayload());
    expect(verifyZcalSignature(raw, sign(raw), SECRET)).toBe(true);
  });

  it("accepts the header in upper case, as hex often arrives", () => {
    const raw = JSON.stringify(samplePayload());
    expect(verifyZcalSignature(raw, sign(raw).toUpperCase(), SECRET)).toBe(true);
  });

  it("accepts a body re-serialised by the sender", () => {
    // zcal's published example hashes JSON.stringify(payload), so a sender that
    // transmits prettified JSON still signs the compact form.
    const pretty = JSON.stringify(samplePayload(), null, 2);
    const compact = JSON.stringify(JSON.parse(pretty));
    expect(verifyZcalSignature(pretty, sign(compact), SECRET)).toBe(true);
  });

  it("rejects a signature made with the wrong secret", () => {
    const raw = JSON.stringify(samplePayload());
    expect(verifyZcalSignature(raw, sign(raw, "not-the-secret"), SECRET)).toBe(false);
  });

  it("rejects a tampered body", () => {
    const raw = JSON.stringify(samplePayload());
    const signature = sign(raw);
    const tampered = raw.replace("2026-09-01T14:30:00.000Z", "2026-09-02T14:30:00.000Z");
    expect(verifyZcalSignature(tampered, signature, SECRET)).toBe(false);
  });

  it("rejects a missing or empty signature rather than throwing", () => {
    const raw = JSON.stringify(samplePayload());
    expect(verifyZcalSignature(raw, undefined, SECRET)).toBe(false);
    expect(verifyZcalSignature(raw, "   ", SECRET)).toBe(false);
  });

  it("refuses to verify at all when no secret is configured", () => {
    // Silently returning false would look identical to an attack in the logs.
    expect(() => verifyZcalSignature("{}", "abc", "")).toThrow(ZcalWebhookError);
  });
});

describe("parseZcalEvent", () => {
  it("reduces a booking to the fields the console stores", () => {
    const event = parseZcalEvent(samplePayload());
    expect(event).toMatchObject({
      type: "event.created",
      eventId: "evt_abc123",
      startsAt: "2026-09-01T14:30:00.000Z",
      durationMinutes: 30,
      status: "booked",
      timezone: "America/New_York",
      meetingUrl: "https://meet.google.com/abc-defg-hij",
      inviteId: "UlhbQQ90",
      bookedName: "Charles Schein",
      bookedPhone: "+17042752607",
    });
  });

  it("lower-cases the booked email, since matching is case-insensitive", () => {
    expect(parseZcalEvent(samplePayload()).bookedEmail).toBe("charles@scheinnc.com");
  });

  it("takes the invitee, not a guest, as the booker", () => {
    const payload = samplePayload();
    // Put the guest first: order must not decide who booked.
    payload.data.attendees.reverse();
    expect(parseZcalEvent(payload).bookedEmail).toBe("charles@scheinnc.com");
  });

  it("falls back to the first attendee when no type is given", () => {
    const payload = samplePayload();
    payload.data.attendees = [{ name: "Solo", email: "solo@example.com" }];
    expect(parseZcalEvent(payload).bookedEmail).toBe("solo@example.com");
  });

  it("marks a cancellation cancelled, from the type alone", () => {
    const payload = samplePayload();
    payload.type = "event.cancelled";
    // `cancelled` stays false in the data here on purpose: the type is enough.
    expect(parseZcalEvent(payload).status).toBe("cancelled");
  });

  it("marks it cancelled from the data flag too", () => {
    const payload = samplePayload({ cancelled: true });
    expect(parseZcalEvent(payload).status).toBe("cancelled");
  });

  it("keeps the booked time on a cancellation", () => {
    const payload = samplePayload();
    payload.type = "event.cancelled";
    // "booked then cancelled" must stay distinguishable from "never booked".
    expect(parseZcalEvent(payload).startsAt).toBe("2026-09-01T14:30:00.000Z");
  });

  it("survives a payload with no attendees at all", () => {
    const payload = samplePayload();
    payload.type = "event.cancelled";
    payload.data.attendees = [];
    const event = parseZcalEvent(payload);
    expect(event.bookedEmail).toBeNull();
    expect(event.bookedName).toBeNull();
    expect(event.status).toBe("cancelled");
  });

  it("drops a duration that is not a usable number", () => {
    expect(parseZcalEvent(samplePayload({ duration: "30" })).durationMinutes).toBeNull();
    expect(parseZcalEvent(samplePayload({ duration: -5 })).durationMinutes).toBeNull();
    expect(parseZcalEvent(samplePayload({ duration: 999_999 })).durationMinutes).toBeNull();
  });

  it("tolerates a missing location", () => {
    const payload = samplePayload();
    delete payload.data.location;
    expect(parseZcalEvent(payload).meetingUrl).toBeNull();
  });

  it("rejects payloads it could not store", () => {
    expect(() => parseZcalEvent(null)).toThrow(ZcalWebhookError);
    expect(() => parseZcalEvent({ type: "event.created" })).toThrow(/event data/i);
    expect(() => parseZcalEvent({ data: { id: "x" } })).toThrow(/event type/i);
    expect(() => parseZcalEvent(samplePayload({ id: "" }))).toThrow(/event id/i);
    expect(() => parseZcalEvent(samplePayload({ startDate: "not-a-date" }))).toThrow(/startDate/i);
  });

  it("keeps the answer to the invite's own question", () => {
    const event = parseZcalEvent(samplePayload());
    expect(event.questionAnswers).toEqual([
      { question: "Anything specific?", answer: "Schema markup" },
    ]);
  });

  it("flattens a checkbox answer, which zcal sends as an array", () => {
    const payload = samplePayload();
    payload.data.attendees[0].customQuestionAnswers = [
      { question: "Select all that apply:", answer: ["Option 1", "Option 3"] },
    ];
    expect(parseZcalEvent(payload).questionAnswers).toEqual([
      { question: "Select all that apply:", answer: "Option 1, Option 3" },
    ]);
  });

  it("drops questions nobody answered", () => {
    const payload = samplePayload();
    payload.data.attendees[0].customQuestionAnswers = [
      { question: "Anything specific?", answer: "   " },
      { question: "Second question", answer: "" },
    ];
    // An optional question left blank is not content, and must not render as an
    // empty "Question from client" block in the console.
    expect(parseZcalEvent(payload).questionAnswers).toBeNull();
  });

  it("returns null when the invite asks nothing", () => {
    const payload = samplePayload();
    delete payload.data.attendees[0].customQuestionAnswers;
    expect(parseZcalEvent(payload).questionAnswers).toBeNull();
  });

  it("caps the number of answers and their length", () => {
    const payload = samplePayload();
    payload.data.attendees[0].customQuestionAnswers = Array.from({ length: 9 }, (_, i) => ({
      question: `Q${i}`,
      answer: "x".repeat(5000),
    }));
    const answers = parseZcalEvent(payload).questionAnswers;
    expect(answers).toHaveLength(5);
    expect(answers[0].answer).toHaveLength(2000);
  });

  it("takes the invitee's answers, not a guest's", () => {
    const payload = samplePayload();
    payload.data.attendees[1].customQuestionAnswers = [
      { question: "Anything specific?", answer: "I am only a guest" },
    ];
    expect(parseZcalEvent(payload).questionAnswers?.[0].answer).toBe("Schema markup");
  });

  it("handles the three event types zcal sends", () => {
    expect([...HANDLED_TYPES]).toEqual(["event.created", "event.rescheduled", "event.cancelled"]);
  });
});
