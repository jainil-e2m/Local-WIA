/* Deciding which lead a zcal booking belongs to.
 *
 * The booking arrives with no correlation key. zcal's webhook carries the event
 * and its attendees and nothing else — no UTM parameters, no reference field —
 * so the only handles are the details the funnel pre-filled into the booking
 * form: the prospect's name, email and (when it was in international form) phone.
 *
 * The prospect can edit all three before booking, which is exactly why this is a
 * ranked ladder rather than one lookup. It lives in its own module because both
 * stores must decide identically: the Postgres store fetches candidates with SQL
 * and the JSON store scans an array, but the policy has to be one thing.
 */

/** How far back a booking may reach for a lead.
 *
 *  A booking is made minutes to weeks after the audit. Sixty days is generous for
 *  that and still stops a stranger who happens to share a name with a lead from
 *  two years ago inheriting their call. */
export const MATCH_WINDOW_DAYS = 60;

const digitsOf = (raw) => (typeof raw === "string" ? raw.replace(/\D/g, "") : "");
const lower = (raw) => (typeof raw === "string" ? raw.trim().toLowerCase() : "");

/**
 * How strongly a lead matches a booking. Lower is better; null means no match.
 *
 *   0  same booking, seen before      — a reschedule or cancellation
 *   1  email                          — the ordinary case, both pre-filled by us
 *   2  name                           — the prospect booked under another address
 *   3  phone                          — last resort, when they changed name and email
 *
 * Rank 2 is what makes the console's "booked under different details" state
 * reachable at all: on an email match the two addresses are equal by definition.
 */
export function matchRank(lead, event) {
  if (!lead || !event) return null;

  if (event.eventId && lead.meetingEventId && lead.meetingEventId === event.eventId) return 0;
  if (event.bookedEmail && lower(lead.email) === lower(event.bookedEmail)) return 1;
  if (event.bookedName && lower(lead.name) === lower(event.bookedName)) return 2;

  const bookedDigits = digitsOf(event.bookedPhone);
  const leadDigits = digitsOf(lead.phone);
  /* Compare the last ten digits, not the whole string: the funnel takes a phone
     as free text, so the same number arrives as "704-275-2607" here and
     "+17042752607" from zcal. Ten is the shortest national length the funnel
     accepts, and requiring that much stops short fragments colliding. */
  if (bookedDigits.length >= 10 && leadDigits.length >= 10) {
    if (bookedDigits.slice(-10) === leadDigits.slice(-10)) return 3;
  }

  return null;
}

/**
 * Pick the lead a booking should attach to, or null if none qualifies.
 *
 * `candidates` may contain anything; this filters. Ordering, in order of
 * precedence:
 *
 *   1. match strength (see matchRank)
 *   2. a lead with no booking yet, over one that already has a different booking
 *      — a repeat visitor booking a second call should not overwrite the first
 *   3. most recently captured, since that is the audit they were just looking at
 */
export function chooseLeadForBooking(candidates, event, { now = Date.now() } = {}) {
  if (!Array.isArray(candidates) || !event) return null;

  const cutoff = now - MATCH_WINDOW_DAYS * 24 * 60 * 60 * 1000;

  /* A cancellation may only touch the booking it names.
   *
   * Cancellations arrive for events this dashboard may never have stored — a call
   * booked from a link shared by hand, or one whose booking never matched a lead.
   * Without this, such a cancellation would fall through to a name or phone match
   * and mark somebody's live, unrelated booking as cancelled. Identity matching is
   * for discovering a booking; only its own id may retract one. */
  const cancellation = event.status === "cancelled" || event.type === "event.cancelled";

  const ranked = [];
  for (const lead of candidates) {
    const rank = matchRank(lead, event);
    if (rank === null) continue;
    if (cancellation && rank !== 0) continue;

    // A known event id overrides the window: a call booked inside the window can
    // be rescheduled or cancelled long after it.
    if (rank > 0) {
      const capturedAt = Date.parse(lead.timestamp ?? lead.capturedAt ?? "");
      if (Number.isFinite(capturedAt) && capturedAt < cutoff) continue;
    }

    const hasOtherBooking =
      Boolean(lead.meetingEventId) && lead.meetingEventId !== event.eventId ? 1 : 0;
    const capturedMs = Date.parse(lead.timestamp ?? lead.capturedAt ?? "") || 0;
    ranked.push({ lead, rank, hasOtherBooking, capturedMs });
  }

  if (!ranked.length) return null;

  ranked.sort(
    (a, b) =>
      a.rank - b.rank || a.hasOtherBooking - b.hasOtherBooking || b.capturedMs - a.capturedMs,
  );

  return ranked[0].lead;
}

/**
 * Did the prospect book under details other than the ones they submitted?
 *
 * Drives the console's little "i" beside the booking's email and name. Compared
 * case-insensitively, and only where both sides actually have a value, so a lead
 * with no name on file is not reported as a mismatch.
 */
export function bookingDiffersFromLead(lead, meeting) {
  if (!lead || !meeting) return false;
  const emailDiffers =
    Boolean(meeting.bookedEmail) && Boolean(lead.email) &&
    lower(meeting.bookedEmail) !== lower(lead.email);
  const nameDiffers =
    Boolean(meeting.bookedName) && Boolean(lead.name) &&
    lower(meeting.bookedName) !== lower(lead.name);
  return emailDiffers || nameDiffers;
}
