import { describe, expect, it } from "vitest";
import {
  DUBSADO_SENDER,
  normalizeProjectKey,
  parseDubsadoAlert,
  parseForwardedEnvelope,
  stripForwardPrefixes,
} from "./onboarding-alert-parser.mjs";

/* ────────────────────────────────────────────────────────────────
   The two subjects below are the REAL ones, transcribed from the
   alerts Whitney forwarded on Sept 5 2026. They are the only
   production evidence that exists for this trigger, so they are
   asserted verbatim rather than paraphrased.

   Note what they are NOT: a matched pair. Dogwood Reserve has only a
   PAID alert and The Elia has only a SIGNED alert — two halves
   belonging to two different clients. So no end-to-end conjunction
   can be tested against real data; the pairing tests below construct
   their pairs, and say so.
   ──────────────────────────────────────────────────────────────── */
const REAL_PAID = "Alina has paid 1997.00 USD - Dogwood Reserve";
const REAL_SIGNED = "Brittanie has signed your contract for The Elia";

/** A Gmail forward of `subject`, shaped like the samples that arrived. */
const gmailForward = (subject, { date = "Mon, Aug 24, 2026 at 10:43 AM" } = {}) =>
  [
    "---------- Forwarded message ---------",
    `From: Dubsado <${DUBSADO_SENDER}>`,
    `Date: ${date}`,
    `Subject: ${subject}`,
    "To: <hello@weddingindustryads.com>",
    "",
    "Hi Whitney,",
    "",
    "View the details in your Dubsado account.",
  ].join("\n");

/** An Outlook-style forward: header block, no Gmail marker line. */
const outlookForward = (subject) =>
  [
    `From: Dubsado <${DUBSADO_SENDER}>`,
    "Sent: Monday, August 24, 2026 10:43 AM",
    "To: hello@weddingindustryads.com",
    `Subject: ${subject}`,
    "",
    "Hi Whitney,",
  ].join("\n");

describe("parseDubsadoAlert — the two real alerts", () => {
  it("parses the real PAID alert into its four fields", () => {
    const result = parseDubsadoAlert({ subject: REAL_PAID, from: DUBSADO_SENDER });
    expect(result).toMatchObject({
      kind: "paid",
      firstName: "Alina",
      projectName: "Dogwood Reserve",
      projectKey: "dogwood reserve",
      amount: 1997,
      currency: "USD",
      source: "direct",
      senderIsDubsado: true,
    });
  });

  it("parses the real SIGNED alert, and carries no amount", () => {
    const result = parseDubsadoAlert({ subject: REAL_SIGNED, from: DUBSADO_SENDER });
    expect(result).toMatchObject({
      kind: "signed",
      firstName: "Brittanie",
      projectName: "The Elia",
      projectKey: "the elia",
      amount: null,
      currency: null,
    });
  });

  it("gives the signed alert no amount to offer-detect from", () => {
    /* This is the constraint that keeps offer selection a human step: the
       amount is the only price-shaped hint on any alert, and it is absent at
       signature. An offer cannot be inferred when the contract is signed —
       only later, when payment lands, and even then only as a guess. */
    const signed = parseDubsadoAlert({ subject: REAL_SIGNED });
    expect(signed.amount).toBeNull();
  });

  it("reads $1997.00 as a number, matching the published accelerator price", () => {
    /* 1997 is the published Google Search Accelerator price exactly — which is
       a HYPOTHESIS about the offer, not a determination. Asserted as a number
       so a caller can compare prices; deliberately not mapped to an offer. */
    const result = parseDubsadoAlert({ subject: REAL_PAID });
    expect(result.amount).toBe(1997);
    expect(typeof result.amount).toBe("number");
  });
});

describe("parseDubsadoAlert — forwarded envelopes", () => {
  it("recovers the real sender and date from a Gmail forward", () => {
    const result = parseDubsadoAlert({
      subject: `Fwd: ${REAL_PAID}`,
      body: gmailForward(REAL_PAID),
      from: "whitney@weddingindustryads.com",
      receivedAt: "2026-09-05T03:29:00.000Z",
    });
    expect(result).toMatchObject({
      kind: "paid",
      projectKey: "dogwood reserve",
      source: "forwarded",
      sender: DUBSADO_SENDER,
      originalDate: "Mon, Aug 24, 2026 at 10:43 AM",
    });
  });

  it("does not mistake the forwarder for the sender", () => {
    /* The whole reason `source` exists. On a forward the envelope belongs to
       Whitney, so a naive sender check would reject a genuine alert — or
       worse, record Whitney as the origin. */
    const result = parseDubsadoAlert({
      subject: `Fwd: ${REAL_SIGNED}`,
      body: gmailForward(REAL_SIGNED),
      from: "whitney@weddingindustryads.com",
    });
    expect(result.sender).toBe(DUBSADO_SENDER);
    expect(result.senderIsDubsado).toBe(true);
  });

  it("keeps the forward date out of originalDate", () => {
    /* Sept 5 3:29 AM is when Whitney pressed forward. Using it as the
       signature date would make every backlogged client look like it signed
       the same morning — and every computed due date would be wrong. */
    const result = parseDubsadoAlert({
      subject: `Fwd: ${REAL_PAID}`,
      body: gmailForward(REAL_PAID),
      receivedAt: "2026-09-05T03:29:00.000Z",
    });
    expect(result.originalDate).toBe("Mon, Aug 24, 2026 at 10:43 AM");
    expect(result.receivedAt).toBe("2026-09-05T03:29:00.000Z");
  });

  it("normalizes the forwarded header date to something Date can parse", () => {
    /* REGRESSION. Gmail writes "Thu, Aug 27, 2026 at 11:02 AM" — the " at "
       makes it Invalid Date. Left unnormalized, every signature-anchored due
       date silently computed to null and the review card rendered empty date
       fields with no explanation of why. */
    const result = parseDubsadoAlert({
      subject: `Fwd: ${REAL_SIGNED}`,
      body: gmailForward(REAL_SIGNED, { date: "Thu, Aug 27, 2026 at 11:02 AM" }),
    });
    expect(result.originalDate).toBe("Thu, Aug 27, 2026 at 11:02 AM");
    expect(result.originalDateIso).toBe(new Date("Thu, Aug 27, 2026 11:02").toISOString());
    expect(Number.isNaN(Date.parse(result.originalDateIso))).toBe(false);
  });

  it("normalizes an Outlook Sent: date too", () => {
    const result = parseDubsadoAlert({
      subject: `FW: ${REAL_SIGNED}`,
      body: outlookForward(REAL_SIGNED),
    });
    expect(Number.isNaN(Date.parse(result.originalDateIso))).toBe(false);
  });

  it("leaves originalDateIso null rather than guessing at an unparseable date", () => {
    const result = parseDubsadoAlert({
      subject: `Fwd: ${REAL_SIGNED}`,
      body: gmailForward(REAL_SIGNED, { date: "sometime last Tuesday" }),
    });
    expect(result.originalDate).toBe("sometime last Tuesday");
    expect(result.originalDateIso).toBeNull();
  });

  it("gives a direct alert no originalDateIso", () => {
    const result = parseDubsadoAlert({ subject: REAL_SIGNED, from: DUBSADO_SENDER });
    expect(result.originalDateIso).toBeNull();
  });

  it("handles an Outlook forward with no marker line", () => {
    const result = parseDubsadoAlert({
      subject: `FW: ${REAL_SIGNED}`,
      body: outlookForward(REAL_SIGNED),
    });
    expect(result).toMatchObject({ source: "forwarded", projectKey: "the elia" });
  });

  it("labels a direct alert as direct, which is the production shape", () => {
    const result = parseDubsadoAlert({
      subject: REAL_PAID,
      body: "Hi Whitney,\n\nView the details in your Dubsado account.",
      from: `Dubsado <${DUBSADO_SENDER}>`,
    });
    expect(result.source).toBe("direct");
    expect(result.originalDate).toBeNull();
  });

  it("recovers the subject from the body when the envelope subject is mangled", () => {
    const result = parseDubsadoAlert({
      subject: "Fwd: (no subject)",
      body: gmailForward(REAL_PAID),
    });
    expect(result).toMatchObject({ kind: "paid", projectKey: "dogwood reserve" });
  });
});

describe("stripForwardPrefixes", () => {
  it("strips a single prefix", () => {
    expect(stripForwardPrefixes(`Fwd: ${REAL_PAID}`)).toBe(REAL_PAID);
  });

  it("strips stacked prefixes from a forwarded thread", () => {
    expect(stripForwardPrefixes(`Fwd: Re: FW: ${REAL_SIGNED}`)).toBe(REAL_SIGNED);
  });

  it("leaves an unprefixed subject untouched", () => {
    expect(stripForwardPrefixes(REAL_PAID)).toBe(REAL_PAID);
  });

  it("returns null for nothing", () => {
    expect(stripForwardPrefixes("")).toBeNull();
    expect(stripForwardPrefixes(undefined)).toBeNull();
  });
});

describe("parseDubsadoAlert — subject grammar edge cases", () => {
  it("keeps a hyphen that belongs to the project name", () => {
    /* The separator is the FIRST ' - ' after the currency code; everything
       past it is the project. A greedy tail is what makes this work. */
    const result = parseDubsadoAlert({
      subject: "Alina has paid 1997.00 USD - Smith-Jones Estate",
    });
    expect(result.projectName).toBe("Smith-Jones Estate");
  });

  it("keeps a project name that itself contains ' - '", () => {
    const result = parseDubsadoAlert({
      subject: "Alina has paid 1997.00 USD - The Barn - North Wing",
    });
    expect(result.projectName).toBe("The Barn - North Wing");
  });

  it("parses a thousands separator", () => {
    const result = parseDubsadoAlert({
      subject: "Alina has paid 1,997.00 USD - Dogwood Reserve",
    });
    expect(result.amount).toBe(1997);
  });

  it("parses an amount with no decimal part", () => {
    const result = parseDubsadoAlert({
      subject: "Alina has paid 1697 USD - Dogwood Reserve",
    });
    expect(result.amount).toBe(1697);
  });

  it("accepts an en dash separator", () => {
    const result = parseDubsadoAlert({
      subject: "Alina has paid 1997.00 USD – Dogwood Reserve",
    });
    expect(result.projectName).toBe("Dogwood Reserve");
  });

  it("parses a multi-word first name", () => {
    const result = parseDubsadoAlert({
      subject: "Mary Anne has signed your contract for The Elia",
    });
    expect(result.firstName).toBe("Mary Anne");
    expect(result.projectName).toBe("The Elia");
  });

  it("normalizes a non-breaking space out of the subject", () => {
    const result = parseDubsadoAlert({
      subject: "Brittanie has signed your contract for The Elia",
    });
    expect(result.projectKey).toBe("the elia");
  });
});

describe("parseDubsadoAlert — everything that must NOT fire", () => {
  /* Every Dubsado notification shares one sender, so the subject IS the
     filter. Each of these arrives from noreply@dubsado.com and none of them
     means a client crossed the signature line. */
  const nonSignatureSubjects = [
    "Alina submitted a form - Dogwood Reserve",
    "Alina viewed your proposal - Dogwood Reserve",
    "Your invoice reminder is scheduled - Dogwood Reserve",
    "Receipt for your payment",
    "New booking request from Alina",
    "Your Dubsado subscription renews soon",
    "Alina has scheduled an appointment",
    "",
  ];

  it.each(nonSignatureSubjects)("returns null for %j", (subject) => {
    expect(parseDubsadoAlert({ subject, from: DUBSADO_SENDER })).toBeNull();
  });

  it("refuses a subject that merely contains the paid phrase mid-line", () => {
    /* The ^ anchor alone is not enough — a permissive name capture swallows
       the prefix and reports a client called "Receipt: Alina". Excluding a
       colon from the name class is what makes a quoted phrase inert. */
    expect(
      parseDubsadoAlert({ subject: "Receipt: Alina has paid 1997.00 USD - Dogwood Reserve" }),
    ).toBeNull();
  });

  it("refuses a subject that merely contains the signed phrase mid-line", () => {
    expect(
      parseDubsadoAlert({
        subject: "Notification: Brittanie has signed your contract for The Elia",
      }),
    ).toBeNull();
  });

  it("still parses names with hyphens, apostrophes and initials", () => {
    /* The colon exclusion must not cost real names. */
    for (const name of ["Mary Anne", "Smith-Jones", "O'Brien", "J. Smith"]) {
      const result = parseDubsadoAlert({
        subject: `${name} has signed your contract for The Elia`,
      });
      expect(result?.firstName, name).toBe(name);
    }
  });

  it("survives garbage input without throwing", () => {
    expect(parseDubsadoAlert()).toBeNull();
    expect(parseDubsadoAlert({})).toBeNull();
    expect(parseDubsadoAlert({ subject: null })).toBeNull();
    expect(parseDubsadoAlert({ subject: 42 })).toBeNull();
    expect(parseDubsadoAlert({ subject: REAL_PAID, body: 42 })).not.toBeNull();
  });

  it("does not hang or blow up on an oversized subject", () => {
    const huge = `${"x".repeat(50_000)} has paid 1997.00 USD - Dogwood Reserve`;
    /* Truncated past the RFC line limit, so it no longer matches — the point
       is that it returns rather than running away. */
    expect(parseDubsadoAlert({ subject: huge })).toBeNull();
  });
});

describe("normalizeProjectKey — the correlation key", () => {
  it("is case and whitespace insensitive", () => {
    expect(normalizeProjectKey("The Elia")).toBe("the elia");
    expect(normalizeProjectKey("  THE   ELIA  ")).toBe("the elia");
  });

  it("drops trailing punctuation a mail client may append", () => {
    expect(normalizeProjectKey("The Elia.")).toBe("the elia");
  });

  it("keeps 'The Elia' and 'Elia' distinct", () => {
    /* Deliberate. Stripping articles would silently merge two real venues —
       'The Reserve' and 'Reserve' — to save a keystroke nobody typed. */
    expect(normalizeProjectKey("The Elia")).not.toBe(normalizeProjectKey("Elia"));
  });

  it("returns null for nothing", () => {
    expect(normalizeProjectKey("")).toBeNull();
    expect(normalizeProjectKey(undefined)).toBeNull();
  });
});

describe("correlation identity — project, never person", () => {
  it("pairs two halves whose signatory and payer differ", () => {
    /* THE CORE GUARANTEE. 'Alina / Dogwood Reserve' and 'Brittanie / The
       Elia' show the person is the signatory and the project is the venue —
       so a venue whose owner signs and whose bookkeeper pays must still
       correlate. Matching on firstName would strand both halves forever.

       CONSTRUCTED PAIR: no real matched pair was ever provided. */
    const signed = parseDubsadoAlert({
      subject: "Brittanie has signed your contract for The Elia",
    });
    const paid = parseDubsadoAlert({
      subject: "Marcus has paid 1997.00 USD - The Elia",
    });
    expect(signed.projectKey).toBe(paid.projectKey);
    expect(signed.firstName).not.toBe(paid.firstName);
  });

  it("does not pair two projects that share a signatory", () => {
    /* The mirror of the above: one person signing for two venues is two
       clients, not one. */
    const first = parseDubsadoAlert({
      subject: "Alina has signed your contract for Dogwood Reserve",
    });
    const second = parseDubsadoAlert({
      subject: "Alina has signed your contract for The Elia",
    });
    expect(first.projectKey).not.toBe(second.projectKey);
  });

  it("confirms the real samples are two halves of two different clients", () => {
    /* Documents the evidence gap rather than papering over it. */
    const paid = parseDubsadoAlert({ subject: REAL_PAID });
    const signed = parseDubsadoAlert({ subject: REAL_SIGNED });
    expect(paid.kind).toBe("paid");
    expect(signed.kind).toBe("signed");
    expect(paid.projectKey).not.toBe(signed.projectKey);
  });
});

describe("parseForwardedEnvelope", () => {
  it("returns null when there is no forward", () => {
    expect(parseForwardedEnvelope("Hi Whitney,\n\nView the details.")).toBeNull();
    expect(parseForwardedEnvelope("")).toBeNull();
    expect(parseForwardedEnvelope(undefined)).toBeNull();
  });

  it("extracts subject, sender and date from a Gmail forward", () => {
    expect(parseForwardedEnvelope(gmailForward(REAL_PAID))).toEqual({
      subject: REAL_PAID,
      sender: DUBSADO_SENDER,
      date: "Mon, Aug 24, 2026 at 10:43 AM",
    });
  });

  it("reads Outlook's Sent: as the date", () => {
    expect(parseForwardedEnvelope(outlookForward(REAL_SIGNED))).toMatchObject({
      subject: REAL_SIGNED,
      date: "Monday, August 24, 2026 10:43 AM",
    });
  });

  it("tolerates quote markers on the header lines", () => {
    const quoted = gmailForward(REAL_PAID)
      .split("\n")
      .map((line) => `> ${line}`)
      .join("\n");
    expect(parseForwardedEnvelope(quoted)).toMatchObject({ subject: REAL_PAID });
  });
});
