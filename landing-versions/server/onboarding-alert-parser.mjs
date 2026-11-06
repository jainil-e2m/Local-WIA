/* Dubsado signature-alert parser — the trigger for client onboarding.
 *
 * Whitney's gate is a CONJUNCTION, stated twice on the Sept 2 call:
 *   @23:38  "we get alerts in the Gmail inbox when they have signed the
 *            contract AND have paid the invoice"
 *   @24:09  "the trigger is that, like, we see in the inbox that they have
 *            signed the contract and paid the invoice"
 *
 * So one alert is never a green light. This module turns a single Dubsado
 * notification into a typed HALF-signal. Correlating two halves into one
 * client — and refusing to fire on a half — is onboarding-store.mjs's job.
 *
 * Kept apart from index.mjs for the same reason zcal-webhook.mjs is: the
 * subject grammar is somebody else's contract that will drift, and it has to
 * be unit-testable without a server or a mailbox.
 *
 * ── THE TWO SUBJECT SHAPES ────────────────────────────────────────────────
 * Verified against two real alerts Whitney forwarded on Sept 5:
 *   paid    "Alina has paid 1997.00 USD - Dogwood Reserve"
 *   signed  "Brittanie has signed your contract for The Elia"
 * i.e.
 *   {FirstName} has paid {Amount} {Currency} - {ProjectName}
 *   {FirstName} has signed your contract for {ProjectName}
 *
 * Both alerts are SUBJECT-LINE-ONLY as signals: the bodies carry a greeting to
 * Whitney and a link, nothing structured. Every field below is parsed from the
 * subject. The body is read for exactly one purpose — recovering a forwarded
 * envelope (see SOURCE below).
 *
 * ── WHY SENDER MATCHING IS NOT ENOUGH ─────────────────────────────────────
 * A `from:noreply@dubsado.com` filter catches EVERY Dubsado notification —
 * form submissions, proposal views, bookings, reminders, receipts. Only these
 * two subject shapes are signature signals, so anything else returns null
 * rather than being mistaken for a trigger half. Subject matching is the real
 * filter; the sender is corroboration.
 *
 * ── SOURCE: FORWARDED vs DIRECT, AND WHY IT IS ON THE RECORD ──────────────
 * Gmail scope on hello@weddingindustryads.com was never requested, so the only
 * samples that exist are FORWARDS sitting in an engineer's mailbox. On a
 * forward the outer envelope belongs to the forwarder — Whitney, Sept 5 — and
 * the real sender and date live as text inside the body. This module recovers
 * them and stamps `source`, so a provisioning record can say plainly where its
 * trigger came from instead of implying a production signal it never had.
 *
 * ── WHAT THIS DELIBERATELY DOES NOT DECIDE ────────────────────────────────
 * The OFFER. Template selection is offer-dependent and additive (Sept 2
 * @19:59: "if they're just doing the foolproof follow-up advantage ... that's
 * its own thing, versus if they're signing on for ads management as well, then
 * ... we're going off both of those onboarding templates"), and the offer name
 * appears on NEITHER subject. `amount` is a hint only, and a weak one:
 *   - $1,997.00 matches the published Google Search Accelerator price exactly
 *   - $1,697 is ambiguous between the Meta Accelerator and LeadLock setup
 *   - a retainer's first payment will not equal list price at all
 *   - the amount is absent from the SIGNED alert, so it can never help at
 *     signature — only after payment lands
 * Offer selection therefore stays a human step. See onboarding-plan.mjs.
 *
 * ── IDENTITY IS THE PROJECT, NOT THE PERSON ───────────────────────────────
 * "Alina / Dogwood Reserve", "Brittanie / The Elia" — the person is the
 * signatory, the project is the venue. The payer and the signer can differ, so
 * correlation keys on `projectKey`. `firstName` is retained for display only
 * and must never be used to pair two halves.
 */

/** The only two subjects that mean "a client crossed the signature line". */
export const ALERT_KINDS = Object.freeze(["signed", "paid"]);

/** Corroborating sender. Policy (whether to require it) belongs to the store. */
export const DUBSADO_SENDER = "noreply@dubsado.com";

/* RFC 5322 caps a header line at 998 octets, so anything longer is not a
   subject line we were sent. The rest bound a display field, not a document. */
const MAX = Object.freeze({
  subject: 998,
  firstName: 200,
  projectName: 300,
  sender: 320,
  date: 120,
  body: 512 * 1024,
});

/* Repeated forward/reply prefixes accumulate on a forwarded thread:
   "Fwd: Re: FW: <real subject>". Strip them all before matching. */
const FORWARD_PREFIX_RE = /^\s*(?:(?:fwd?|re|aw|wg|tr|rv|enc)\s*:\s*|\[fwd?\]\s*)+/i;

/* Gmail writes "---------- Forwarded message ---------"; Outlook writes a bare
   header block with no marker. Either counts as evidence of a forward. */
const FORWARD_MARKER_RE = /^[\s>|*_-]*forwarded message[\s>|*_-]*$/im;

/* Leading "> " and "*" survive quoted-printable forwards, so tolerate them. */
const HEADER_RE = Object.freeze({
  from: /^[\s>|*]*from\s*:\s*(.+)$/im,
  subject: /^[\s>|*]*subject\s*:\s*(.+)$/im,
  date: /^[\s>|*]*(?:date|sent)\s*:\s*(.+)$/im,
});

/* WHY THE NAME CLASS EXCLUDES A COLON, AND WHY IT MATTERS
   A Dubsado {FirstName} never contains one, and excluding it is what makes the
   ^ anchor actually bite. With a permissive (.+?) head, "Receipt: Alina has
   paid 1997.00 USD - Dogwood Reserve" parses as a payment alert for a client
   named "Receipt: Alina" — a receipt quoting the phrase would fire the
   trigger. Names with spaces, hyphens, apostrophes and initials ("Mary Anne",
   "Smith-Jones", "O'Brien", "J. Smith") all still parse. The length bound
   keeps the non-greedy head from backtracking on a pathological subject. */

/* Separator between currency and project on the paid alert. The sample uses a
   plain hyphen; en/em dashes are cheap insurance against Dubsado restyling the
   template, at no ambiguity cost because all three are space-surrounded.

   The project tail is GREEDY on purpose: project names can themselves contain
   a hyphen ("Smith-Jones Estate"), so the separator is the FIRST " - " after
   the currency code and everything past it is the project. */
const PAID_RE =
  /^([^:]{1,200}?) has paid ([\d,]+(?:\.\d{1,2})?) ([A-Za-z]{3}) [-–—] (.+)$/;

const SIGNED_RE = /^([^:]{1,200}?) has signed your contract for (.+)$/;

/* Collapse the whitespace variants that survive mail transport. Written as
   escapes, not literals, so the class stays visible to whoever reads this
   next: U+00A0 no-break, U+2007 figure, U+202F narrow no-break space. */
const collapseWhitespace = (raw) =>
  raw.replace(/[\s\u00a0\u2007\u202f]+/g, " ").trim();

const trimTo = (raw, maxLength) => {
  if (typeof raw !== "string") return null;
  const value = collapseWhitespace(raw).slice(0, maxLength);
  return value || null;
};

/**
 * The correlation key for a client.
 *
 * Case- and spacing-insensitive, and tolerant of trailing punctuation a mail
 * client may append. Deliberately does NOT strip leading articles: "The Elia"
 * and "Elia" stay distinct, because collapsing them would silently merge two
 * real venues ("The Reserve" / "Reserve") to save a keystroke nobody typed.
 */
export const normalizeProjectKey = (projectName) => {
  const value = trimTo(projectName, MAX.projectName);
  if (!value) return null;
  return value.toLowerCase().replace(/[.,;:!?]+$/, "").trim() || null;
};

/** "Dubsado <noreply@dubsado.com>" -> "noreply@dubsado.com" */
const extractEmail = (rawFrom) => {
  const value = trimTo(rawFrom, MAX.sender);
  if (!value) return null;
  const angled = value.match(/<([^<>@\s]+@[^<>@\s]+)>/);
  if (angled) return angled[1].toLowerCase();
  const bare = value.match(/([^<>@\s]+@[^<>@\s]+)/);
  return bare ? bare[1].toLowerCase().replace(/[.,;:]+$/, "") : null;
};

/** Strip every accumulated Fwd:/Re: prefix. Exported for the store's logging. */
export const stripForwardPrefixes = (subject) => {
  const value = trimTo(subject, MAX.subject);
  if (!value) return null;
  let previous = value;
  for (let i = 0; i < 8; i += 1) {
    const next = previous.replace(FORWARD_PREFIX_RE, "").trim();
    if (next === previous) break;
    previous = next;
  }
  return previous || null;
};

/**
 * Recover the original alert's headers from a forwarded body.
 *
 * Returns null when the body shows no sign of a forward, which is the shape a
 * real production signal will have once Gmail scope on hello@ exists. A
 * forwarded Subject: line is treated as sufficient evidence even without
 * Gmail's marker, because Outlook forwards omit the marker entirely.
 */
export const parseForwardedEnvelope = (body) => {
  if (typeof body !== "string" || !body) return null;
  const text = body.slice(0, MAX.body);
  const subject = stripForwardPrefixes(text.match(HEADER_RE.subject)?.[1] ?? null);
  const hasMarker = FORWARD_MARKER_RE.test(text);
  if (!subject && !hasMarker) return null;
  return {
    subject,
    sender: extractEmail(text.match(HEADER_RE.from)?.[1] ?? null),
    date: trimTo(text.match(HEADER_RE.date)?.[1] ?? null, MAX.date),
  };
};

/**
 * Normalize a forwarded header date to ISO.
 *
 * Forwarded header dates are human-readable, not machine-readable: Gmail
 * writes "Mon, Aug 24, 2026 at 10:43 AM" and Outlook "Monday, August 24, 2026
 * 10:43 AM". Date parses both once Gmail's " at " is removed — without that
 * the string is Invalid Date, every signature-anchored due date silently
 * computes to null, and the review card renders empty date fields.
 *
 * Returned ALONGSIDE the raw string rather than replacing it: the evidence
 * panel shows the header verbatim, and only the arithmetic wants ISO.
 */
const toIsoDate = (raw) => {
  if (typeof raw !== "string" || !raw.trim()) return null;
  const parsed = new Date(raw.replace(/\s+at\s+/i, " "));
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
};

/** Amounts arrive with thousands separators; store a number, not a string. */
const parseAmount = (raw) => {
  const value = Number.parseFloat(String(raw).replace(/,/g, ""));
  return Number.isFinite(value) ? value : null;
};

const matchSubject = (subject) => {
  const paid = subject.match(PAID_RE);
  if (paid) {
    const [, firstName, amount, currency, projectName] = paid;
    return {
      kind: "paid",
      firstName: trimTo(firstName, MAX.firstName),
      projectName: trimTo(projectName, MAX.projectName),
      amount: parseAmount(amount),
      currency: currency.toUpperCase(),
    };
  }
  const signed = subject.match(SIGNED_RE);
  if (signed) {
    const [, firstName, projectName] = signed;
    return {
      kind: "signed",
      firstName: trimTo(firstName, MAX.firstName),
      projectName: trimTo(projectName, MAX.projectName),
      amount: null,
      currency: null,
    };
  }
  return null;
};

/**
 * Parse one Dubsado notification into a signature half-signal, or null.
 *
 * Null is the answer for every Dubsado email that is not one of the two
 * signature alerts — and there are many, since every Dubsado notification
 * shares one sender. Null is not an error; it is the filter working.
 *
 * @param {object} input
 * @param {string} input.subject      Envelope subject, Fwd:/Re: prefixes and all.
 * @param {string} [input.body]       Read only to recover a forwarded envelope.
 * @param {string} [input.from]       Envelope sender — the FORWARDER on a forward.
 * @param {string} [input.receivedAt] ISO date the mailbox received it.
 * @returns {object|null}
 */
export const parseDubsadoAlert = ({ subject, body, from, receivedAt } = {}) => {
  const envelopeSubject = stripForwardPrefixes(subject);
  const forwarded = parseForwardedEnvelope(body);

  /* Prefer the forwarded block's subject: on a forward the envelope subject is
     the forwarder's, and a mail client may have truncated or re-wrapped it. */
  const candidates = [forwarded?.subject, envelopeSubject].filter(Boolean);
  let parsed = null;
  for (const candidate of candidates) {
    parsed = matchSubject(candidate);
    if (parsed) break;
  }
  if (!parsed || !parsed.firstName || !parsed.projectName) return null;

  const projectKey = normalizeProjectKey(parsed.projectName);
  if (!projectKey) return null;

  const isForwarded = Boolean(forwarded);
  /* On a forward the real sender is inside the body; the envelope sender is
     whoever pressed forward. Fall back to the envelope only when direct. */
  const sender = isForwarded ? forwarded.sender : extractEmail(from);

  return {
    kind: parsed.kind,
    firstName: parsed.firstName,
    projectName: parsed.projectName,
    projectKey,
    amount: parsed.amount,
    currency: parsed.currency,
    /* "forwarded" is the honest label for every sample that exists today, and
       it belongs on the provisioning card verbatim — the production signal is
       a Gmail filter on hello@, a scope that was never requested. */
    source: isForwarded ? "forwarded" : "direct",
    sender,
    senderIsDubsado: sender === DUBSADO_SENDER,
    /* The original alert's own date when recoverable. On a forward the
       envelope date is when Whitney pressed forward (Sept 5), which would make
       every backlogged client look like it signed the same morning. */
    originalDate: isForwarded ? forwarded.date : null,
    /* The same instant, machine-readable. Due-date arithmetic reads this;
       the evidence panel reads originalDate. */
    originalDateIso: isForwarded ? toIsoDate(forwarded.date) : null,
    receivedAt: trimTo(receivedAt, MAX.date),
  };
};
