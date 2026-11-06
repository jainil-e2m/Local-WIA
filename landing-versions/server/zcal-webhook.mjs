/* zcal booking webhook — signature check and payload reduction.
 *
 * zcal POSTs here when a call is booked, moved or cancelled on the invite the
 * Lead Magnet funnels embed. Its payload describes the event; this module turns
 * it into the handful of fields the console renders, and refuses anything whose
 * signature does not check out.
 *
 * Kept apart from index.mjs so both halves are unit-testable without a server:
 * the signature rules are security-relevant, and the payload shape is somebody
 * else's contract that will drift.
 *
 * Payload reference (verified against zcal's published spec):
 *   type        "event.created" | "event.rescheduled" | "event.cancelled"
 *   created_at  ISO 8601
 *   data.id, data.startDate, data.duration, data.cancelled, data.eventName
 *   data.location.onlineMeeting.url
 *   data.hosts[]      { name, email }
 *   data.attendees[]  { name, email, timezone, phoneNumber, type, customQuestionAnswers }
 *   data.invite       { id, name, inviteType, description }
 *
 * Note what is NOT in it: UTM parameters. zcal only forwards those to a
 * redirect-on-booking URL, so a booking cannot be attributed by campaign tags —
 * it is matched to a lead by attendee identity instead. See matchLeadFor* in the
 * stores.
 */

import crypto from "node:crypto";

export class ZcalWebhookError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "ZcalWebhookError";
    this.code = code;
  }
}

const MAX_LEN = {
  id: 128,
  email: 320,
  name: 200,
  timezone: 64,
  url: 500,
  status: 32,
};

const trimTo = (raw, maxLength) =>
  typeof raw === "string" && raw.trim() ? raw.trim().slice(0, maxLength) : null;

/** Room for a considered paragraph, not for a pasted document. */
const MAX_ANSWER_LEN = 2000;
/** More than this many questions on one invite is a form, not a booking. */
const MAX_ANSWERS = 5;

/**
 * The prospect's answers to the invite's own questions.
 *
 * zcal keys answers by the question's text — there is no stable id — so both
 * halves are kept: the console shows the answer, and the question text is what
 * makes a second question distinguishable from the first if the client ever adds
 * one.
 *
 * A checkbox answer arrives as an array (zcal's own sample shows
 * `answer: ["Option 1", "Option 3"]`), so it is flattened here rather than
 * leaving every consumer to handle two shapes. Empty answers are dropped: an
 * optional question nobody filled in is not content.
 */
function parseQuestionAnswers(raw) {
  if (!Array.isArray(raw)) return null;

  const answers = [];
  for (const entry of raw) {
    if (!entry || typeof entry !== "object") continue;
    const question = trimTo(entry.question, 300);
    const answer = Array.isArray(entry.answer)
      ? trimTo(entry.answer.filter((v) => typeof v === "string").join(", "), MAX_ANSWER_LEN)
      : trimTo(entry.answer, MAX_ANSWER_LEN);
    if (!answer) continue;
    answers.push({ question, answer });
    if (answers.length >= MAX_ANSWERS) break;
  }
  return answers.length ? answers : null;
}

/**
 * Constant-time check of the `x-zcal-webhook-signature` header.
 *
 * zcal signs with HMAC-SHA256 over the request body, hex encoded. Their own
 * published example hashes `JSON.stringify(payload)`, which is the same bytes as
 * long as the sender serialises once and signs what it sends — so the raw body is
 * tried first, and a re-serialisation of the parsed body second. That fallback
 * costs one hash and covers a sender whose JSON differs from ours only in
 * whitespace or escaping; without it a mismatch would be indistinguishable from
 * an attack.
 *
 * `rawBody` must be the bytes as received. Verifying a re-encoded body only
 * would mean signing something the sender never sent.
 */
export function verifyZcalSignature(rawBody, signatureHeader, secret) {
  if (!secret) throw new ZcalWebhookError("secret_not_configured", "No webhook secret is set.");

  const provided = trimTo(signatureHeader, 200);
  if (!provided) return false;

  const candidates = [];
  const raw = Buffer.isBuffer(rawBody) ? rawBody : Buffer.from(String(rawBody ?? ""), "utf8");
  candidates.push(raw);
  try {
    candidates.push(Buffer.from(JSON.stringify(JSON.parse(raw.toString("utf8"))), "utf8"));
  } catch {
    // Not JSON — the raw comparison below is the only one that can apply.
  }

  return candidates.some((body) => {
    const expected = crypto.createHmac("sha256", secret).update(body).digest("hex");
    // Compare digests of the two hex strings: timingSafeEqual throws on a length
    // mismatch, and a caller can send a signature of any length.
    const a = crypto.createHash("sha256").update(expected).digest();
    const b = crypto.createHash("sha256").update(provided.toLowerCase()).digest();
    return crypto.timingSafeEqual(a, b);
  });
}

/** The event types worth acting on. Anything else is accepted and ignored. */
export const HANDLED_TYPES = new Set(["event.created", "event.rescheduled", "event.cancelled"]);

/**
 * Reduce a webhook payload to what the console stores.
 *
 * Throws only on payloads that cannot be stored at all — no event id, or no
 * usable start time. A missing invitee is not fatal on a cancellation, where
 * zcal has been observed to send the event alone.
 */
export function parseZcalEvent(payload) {
  if (!payload || typeof payload !== "object") {
    throw new ZcalWebhookError("invalid_payload", "Body is not an object.");
  }

  const type = trimTo(payload.type, MAX_LEN.status);
  if (!type) throw new ZcalWebhookError("invalid_payload", "Missing event type.");

  const data = payload.data && typeof payload.data === "object" ? payload.data : null;
  if (!data) throw new ZcalWebhookError("invalid_payload", "Missing event data.");

  const eventId = trimTo(data.id, MAX_LEN.id);
  if (!eventId) throw new ZcalWebhookError("invalid_payload", "Missing event id.");

  const startsAt = (() => {
    const raw = trimTo(data.startDate, 64);
    if (!raw) return null;
    const parsed = new Date(raw);
    return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
  })();
  if (!startsAt) throw new ZcalWebhookError("invalid_payload", "Missing or unparseable startDate.");

  const attendees = Array.isArray(data.attendees) ? data.attendees : [];
  /* The person who booked. zcal marks them type "invitee"; guests are additional
     attendees and must not be mistaken for the booker. Falling back to the first
     attendee covers a payload that omits the type, which is optional in the spec. */
  const invitee =
    attendees.find((a) => a && trimTo(a.type, 32) === "invitee") ?? attendees[0] ?? null;

  const duration =
    Number.isFinite(data.duration) && data.duration > 0 && data.duration <= 32_767
      ? Math.round(data.duration)
      : null;

  const cancelled = type === "event.cancelled" || data.cancelled === true;

  return {
    type,
    eventId,
    startsAt,
    durationMinutes: duration,
    status: cancelled ? "cancelled" : "booked",
    timezone: invitee ? trimTo(invitee.timezone, MAX_LEN.timezone) : null,
    meetingUrl: trimTo(data.location?.onlineMeeting?.url, MAX_LEN.url),
    inviteId: trimTo(data.invite?.id, MAX_LEN.id),
    // Identity as entered on the booking form — the only handle for matching a
    // booking to a captured lead, and what the console compares against.
    bookedEmail: invitee ? trimTo(invitee.email, MAX_LEN.email)?.toLowerCase() ?? null : null,
    bookedName: invitee ? trimTo(invitee.name, MAX_LEN.name) : null,
    bookedPhone: invitee ? trimTo(invitee.phoneNumber, 40) : null,
    // What they asked for ahead of the call — the one thing on that form the
    // funnel does not already know.
    questionAnswers: invitee ? parseQuestionAnswers(invitee.customQuestionAnswers) : null,
  };
}
