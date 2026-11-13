/* ────────────────────────────────────────────────────────────────
   Internal Meeting + Action Items — the parts that are REAL.

   The extraction is pre-computed for this build (there is no LLM call). But
   three things below genuinely run on the pasted text every time, and they are
   what make the output checkable rather than asserted:

     1. NORMALIZATION      — the transcript is actually parsed into turns.
     2. QUOTE VERIFICATION — every displayed quote must be a literal substring
                             of the normalized body. One demo item deliberately
                             fails this, and the failure is real, not staged.
     3. MM:SS DERIVATION    — a timestamp is DERIVED from the turn containing
                             the quote. It is never taken from the item data,
                             because a hand-typed timestamp is exactly the class
                             of error a substring check cannot catch.
     4. LEDGER MATCHING     — a content fingerprint, computed here, is what
                             recognises last run's item. No external task id is
                             involved anywhere, which is why this survives with
                             no ClickUp integration at all.

   One turn in this transcript runs seven minutes (the block at 33:01). A quote
   from inside it must NOT be rendered as though it were spoken at 33:01 on the
   dot, so `deriveCitation` marks any long turn `segment` and the UI says
   "in the segment starting @33:01".
   ──────────────────────────────────────────────────────────────── */

/** Who can own a ClickUp task. Anyone not on this list is unmapped_external. */
export const WIA_ROSTER = [
  "Whitney Hodges",
  "Gisselle Jimenez",
  "Carmen Cruickshank",
  "Jacqueline Hood",
  "Ivy",
  "Tina",
  "Danielle",
] as const;

/* A positive roster, NOT an email-domain test. The `(weddingindustryads.com)`
   suffix looks like a clean internal signal and is not one: Gisselle is on
   dotandcompany.co and Jacqueline hosts Fathom on jacquelinehood.com, so a
   domain heuristic silently misclassifies two of the seven. */
const ROSTER_KEYS = WIA_ROSTER.map((name) => name.split(" ")[0].toLowerCase());

export interface Turn {
  /** Seconds from the start of the recording. */
  offsetSeconds: number;
  /** As written in the transcript, e.g. "33:01". */
  display: string;
  speaker: string;
  text: string;
  /** Offsets into `NormalizedTranscript.body`. The authoritative anchor. */
  charStart: number;
  charEnd: number;
}

export interface SpeakerSummary {
  label: string;
  /** Membership of the WIA roster, resolved by name — never by email domain. */
  org: "wia" | "external";
  turns: number;
}

export interface NormalizedTranscript {
  /** Exactly what was pasted. Retained so nothing is silently rewritten. */
  raw: string;
  /** Turn bodies joined with newlines. Every quote is checked against THIS. */
  body: string;
  turns: Turn[];
  speakers: SpeakerSummary[];
  lineCount: number;
  charCount: number;
  durationSeconds: number;
  firstDisplay: string;
  lastDisplay: string;
  /** Recovered from a Fathom WATCH url, when the paste carries one. */
  fathomCallId: string | null;
  /** Which tool produced the paste, when the text says so. See detectSource. */
  sourceKind: SourceKind;
  /** Fathom's own inline "ACTION ITEM:" lines — the free baseline to beat. */
  fathomActionItems: string[];
  /** True when a deep link can be built; false for plain pasted text. */
  canDeepLink: boolean;
}

/* ── Where the paste came from ────────────────────────────────────
   Asserted only when the text itself says so, and "unknown" otherwise. The
   evidence modal shows a tool logo, and a logo is a claim about provenance —
   guessing Fathom because the shape matches would put a vendor mark on a file
   that might have come from anywhere.

   Fathom's clipboard copy opens with a `VIEW RECORDING - 48 mins` header even
   when it carries no call url, which is why detection is not just a url test:
   the demo paste is a genuine Fathom copy with the call id stripped, so it is
   known to be Fathom AND cannot be deep-linked. Those are two separate facts
   and the UI states both. */
export type SourceKind = "fathom" | "zoom" | "unknown";

export const SOURCE_KIND_META: Record<
  SourceKind,
  { label: string; logo: string | null }
> = {
  fathom: { label: "Fathom", logo: "/logos/sources/fathom.png" },
  zoom: { label: "Zoom", logo: "/logos/sources/zoom.png" },
  unknown: { label: "Pasted transcript", logo: null },
};

export function detectSource(raw: string): SourceKind {
  if (/fathom\.video/i.test(raw)) return "fathom";
  if (/^\s*VIEW RECORDING\b/im.test(raw)) return "fathom";
  if (/zoom\.us\/rec|^\s*Recording of\b/im.test(raw)) return "zoom";
  return "unknown";
}

const TURN_HEADER = /^(\d{1,2}:\d{2}(?::\d{2})?)\s+-\s+(.+?)\s*$/;

const toSeconds = (display: string) => {
  const parts = display.split(":").map(Number);
  return parts.length === 3
    ? parts[0] * 3600 + parts[1] * 60 + parts[2]
    : parts[0] * 60 + parts[1];
};

const orgFor = (speaker: string): "wia" | "external" => {
  const lower = speaker.toLowerCase();
  return ROSTER_KEYS.some((key) => lower.startsWith(key)) ? "wia" : "external";
};

/**
 * Parse a pasted Fathom copy or Zoom .txt into turns.
 *
 * Both sources emit the same shape — `MM:SS - Speaker Name` followed by
 * indented body lines — which is the whole reason one normalizer serves both
 * and why paste intake was chosen over an export or an API.
 */
export function normalizeTranscript(raw: string): NormalizedTranscript {
  const lines = raw.split(/\r?\n/);
  const turns: Turn[] = [];
  const fathomActionItems: string[] = [];
  let body = "";
  let current: { display: string; speaker: string; parts: string[] } | null = null;

  const flush = () => {
    if (!current) return;
    const text = current.parts.join(" ").replace(/\s+/g, " ").trim();
    if (text) {
      const charStart = body.length;
      body += text + "\n";
      turns.push({
        offsetSeconds: toSeconds(current.display),
        display: current.display,
        speaker: current.speaker,
        text,
        charStart,
        charEnd: charStart + text.length,
      });
    }
    current = null;
  };

  for (const line of lines) {
    const header = TURN_HEADER.exec(line.trim());
    if (header) {
      flush();
      current = { display: header[1], speaker: header[2], parts: [] };
      continue;
    }
    const trimmed = line.trim();
    if (!trimmed || trimmed === "---") continue;
    /* Fathom's own event lines are pulled OUT of the dialogue rather than
       parsed as speech. Leaving them in would count Fathom's free output as
       our extraction and destroy the only honest comparison available. */
    if (/^ACTION ITEM:/i.test(trimmed)) {
      fathomActionItems.push(trimmed.replace(/^ACTION ITEM:\s*/i, "").split(" - WATCH:")[0].trim());
      continue;
    }
    if (/^SCREEN SHARING:/i.test(trimmed)) continue;
    if (current) current.parts.push(trimmed);
  }
  flush();

  const counts = new Map<string, number>();
  for (const turn of turns) counts.set(turn.speaker, (counts.get(turn.speaker) ?? 0) + 1);

  const callId = /fathom\.video\/calls\/(\d+)/.exec(raw)?.[1] ?? null;

  return {
    raw,
    body,
    turns,
    speakers: [...counts.entries()]
      .map(([label, n]) => ({ label, org: orgFor(label), turns: n }))
      .sort((a, b) => b.turns - a.turns),
    lineCount: lines.filter((l) => l.trim()).length,
    charCount: raw.length,
    durationSeconds: turns.length ? turns[turns.length - 1].offsetSeconds : 0,
    firstDisplay: turns[0]?.display ?? "0:00",
    lastDisplay: turns[turns.length - 1]?.display ?? "0:00",
    fathomCallId: callId,
    sourceKind: detectSource(raw),
    fathomActionItems,
    canDeepLink: Boolean(callId),
  };
}

/** A turn longer than this is cited as a segment, not as a moment. */
const SEGMENT_SECONDS = 90;

export interface Citation {
  /** Verified as a literal substring of the normalized body. */
  verified: boolean;
  /** DERIVED from the containing turn — never supplied by the item data. */
  display: string | null;
  speaker: string | null;
  /** True when the containing turn is long enough that a point-in-time
      timestamp would misrepresent when the words were said. */
  segment: boolean;
  charStart: number | null;
  deepLink: string | null;
  /** Index into `transcript.turns` of the turn containing the quote, so the
      evidence modal can show the words either side of it. A quote read
      without its surrounding turn is how "we totally can" becomes a
      commitment. -1 when the quote was not found. */
  turnIndex: number;
}

/**
 * Verify one quote and derive its citation.
 *
 * A failed check is a first-class outcome, not an error: the item drops into
 * the review lane with its quotation marks removed, which is the only on-screen
 * proof that this check runs at all.
 */
export function deriveCitation(
  transcript: NormalizedTranscript,
  quote: string,
): Citation {
  const needle = quote.replace(/\s+/g, " ").trim();
  const at = needle ? transcript.body.indexOf(needle) : -1;
  if (at < 0) {
    return {
      verified: false,
      display: null,
      speaker: null,
      segment: false,
      charStart: null,
      deepLink: null,
      turnIndex: -1,
    };
  }
  const turnIndex = transcript.turns.findIndex(
    (t) => at >= t.charStart && at <= t.charEnd,
  );
  const turn = turnIndex >= 0 ? transcript.turns[turnIndex] : null;
  const next = turnIndex >= 0 ? transcript.turns[turnIndex + 1] : undefined;
  const span = turn && next ? next.offsetSeconds - turn.offsetSeconds : 0;
  return {
    verified: true,
    display: turn?.display ?? null,
    speaker: turn?.speaker ?? null,
    segment: span > SEGMENT_SECONDS,
    charStart: at,
    turnIndex,
    deepLink:
      transcript.fathomCallId && turn
        ? `https://fathom.video/calls/${transcript.fathomCallId}?timestamp=${turn.offsetSeconds}`
        : null,
  };
}

/* ── Ledger identity ──────────────────────────────────────────────
   The fingerprint deliberately excludes the OWNER. The flagship carry-over in
   the demo is an item whose owner changed between runs (Minu -> Asha); with
   owner inside the hash that match could never fire. Owner is a confidence
   signal, not identity. Producer is excluded for the same reason. */
const STOP = new Set([
  "the", "a", "an", "to", "of", "and", "for", "with", "on", "in", "that",
  "this", "we", "us", "our", "i", "you", "your", "it", "is", "are", "will",
  "would", "can", "just", "like", "so", "then", "at", "be", "by", "from",
  "them", "they", "he", "she", "as", "if", "or", "all", "any", "some", "yeah",
  "okay", "right", "um", "uh", "well", "also",
]);

/** Crude, deterministic and offline on purpose — no embedding model, no
    network, so the same paste always yields the same view. */
export function fingerprint(text: string): string {
  return [
    ...new Set(
      text
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, " ")
        .split(/\s+/)
        .filter((w) => w.length > 2 && !STOP.has(w))
        .map((w) => w.replace(/(ing|ed|es|s)$/, "")),
    ),
  ]
    .sort()
    .join("|");
}

/** Jaccard overlap on fingerprint tokens. Bands are declared by the caller. */
export function similarity(a: string, b: string): number {
  const left = new Set(a.split("|").filter(Boolean));
  const right = new Set(b.split("|").filter(Boolean));
  if (!left.size || !right.size) return 0;
  let shared = 0;
  for (const token of left) if (right.has(token)) shared += 1;
  return shared / (left.size + right.size - shared);
}

export const isOnRoster = (name: string | null) =>
  Boolean(name) && ROSTER_KEYS.some((key) => name!.toLowerCase().startsWith(key));

export const formatDuration = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
};
