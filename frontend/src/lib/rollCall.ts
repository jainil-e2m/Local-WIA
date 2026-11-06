import { similarity, type NormalizedTranscript } from "./internalMeeting";

/* ────────────────────────────────────────────────────────────────
   Roll call — the parts that are REAL.

   THE HARD CONSTRAINT, in Gisselle's own words on the audit sheet: "Just needs
   to flag, we will manually follow up." Nothing here sends a DM or an email.
   The output is a flag with an owner, and that is the whole product.

   THE HONEST LIMIT OF THIS APPROACH. Fathom's share payload carries NO
   attendee list — `byline` is literally "Unknown" and the call object has no
   participant field — so attendance can only be inferred from who SPOKE.
   Whitney described the format as an open drop-in (26 Aug @12:00, "it's really
   like an open meeting for clients to come in", and @13:32, "they can join
   like at any moment during that hour"), which means a member who joins,
   listens and leaves silently is scored ABSENT — and that is precisely the
   disengaged member the 2-week flag exists to catch.

   So speaker-derived attendance is sound at CURRENT VOLUME (3 members on the
   12 Feb session), not sound by format. Every derived absence is therefore a
   flag for a human to check, never an automatic action, and the UI says so.

   WHAT PRODUCTION SHOULD READ INSTEAD. Office Hours are Zoom meetings hosted
   on their own account (Sept 2 @5:24), and Zoom's past-meeting participant
   report lists every join and leave — including the members who never spoke,
   which is exactly the cohort this method is blind to. That report is the
   primary source for MP-01; this transcript pass is the documented fallback
   for a session where it is unavailable, and it is what this console runs
   because no Zoom scope has been granted yet. The access ask is in the
   Blueprint (Zoom API, participant report) and the choice of source is its
   first open question, so this is a sequencing gap rather than a dead end.
   ──────────────────────────────────────────────────────────────── */

export type TrackId = "google" | "meta";

export interface Track {
  id: TrackId;
  /** The GHL Communities channel this roster comes from. */
  channel: string;
  label: string;
  host: string;
  /** Who owns the follow-up when a flag fires, per 26 Aug @14:47. */
  followUpOwner: string;
  slot: string;
  /** Fills {{TIME}} in the 4-week email. */
  sessionTime: string;
}

export const TRACKS: Record<TrackId, Track> = {
  google: {
    id: "google",
    channel: "Google Search Accelerator",
    label: "Google Ads office hours",
    host: "Carmen Cruickshank",
    followUpOwner: "Carmen Cruickshank",
    slot: "Thursdays, 11:00 CST",
    sessionTime: "11:00 AM CST",
  },
  meta: {
    id: "meta",
    channel: "Meta Ads Accelerator",
    label: "Meta Ads office hours",
    host: "Jacqueline Hood",
    followUpOwner: "Jacqueline Hood",
    slot: "Thursdays, 15:30 CST",
    sessionTime: "3:30 PM CST",
  },
};

/** Staff never count as attendees. Matched by name, not by email domain —
    the `(weddingindustryads.com)` suffix misses Jacqueline, who hosts on
    jacquelinehood.com, and Gisselle, who is on dotandcompany.co. */
export const STAFF_KEYS = [
  "carmen",
  "jacqueline",
  "whitney",
  "gisselle",
  "ivy",
  "tina",
  "danielle",
];

export const isStaffLabel = (label: string) => {
  const lower = label.toLowerCase();
  return STAFF_KEYS.some((key) => lower.startsWith(key));
};

/* ── Attendance thresholds ────────────────────────────────────────
   A label that says "hi" and nothing else is not evidence of a working
   session. Two turns AND forty words is deliberately low but non-zero: on the
   12 Feb transcript it separates the three genuine consultations from noise
   without excluding anybody who actually engaged. Tunable, and the numbers are
   printed on screen so a reviewer can see what they mean. */
export const ATTENDANCE_MIN_TURNS = 2;
export const ATTENDANCE_MIN_WORDS = 40;

export interface ObservedSpeaker {
  label: string;
  turns: number;
  words: number;
  firstDisplay: string;
  lastDisplay: string;
  /** Failed the engagement floor — present in the transcript, not counted. */
  belowThreshold: boolean;
}

/** Who spoke, how much, and when — computed off the parsed turns. */
export function deriveAttendance(transcript: NormalizedTranscript): ObservedSpeaker[] {
  const acc = new Map<string, { turns: number; words: number; first: string; last: string }>();
  for (const turn of transcript.turns) {
    if (isStaffLabel(turn.speaker)) continue;
    const words = turn.text.split(/\s+/).filter(Boolean).length;
    const prev = acc.get(turn.speaker);
    acc.set(turn.speaker, {
      turns: (prev?.turns ?? 0) + 1,
      words: (prev?.words ?? 0) + words,
      first: prev?.first ?? turn.display,
      last: turn.display,
    });
  }
  return [...acc.entries()]
    .map(([label, v]) => ({
      label,
      turns: v.turns,
      words: v.words,
      firstDisplay: v.first,
      lastDisplay: v.last,
      belowThreshold: v.turns < ATTENDANCE_MIN_TURNS || v.words < ATTENDANCE_MIN_WORDS,
    }))
    .sort((a, b) => b.words - a.words);
}

export interface Member {
  memberId: string;
  /** Fills {{First Name}}. Explicit, never split off accountName — a
      two-person membership must not be greeted as one of the two. */
  firstName: string;
  /** The account name as GHL holds it. Attendance is keyed PER ACCOUNT. */
  accountName: string;
  business: string;
  /** Display names this account is known to join under. */
  aliases: string[];
  /** Channel membership, straight off the members-portal roster. */
  tracks: TrackId[];
  /** ISO date the membership starts. Sessions before it are NOT misses —
      a member who joined in February cannot have missed January, and
      counting those would produce a four-week flag on their first week. */
  enrolledFrom?: string;
}

export type MatchMethod = "alias" | "fuzzy" | "ambiguous" | "unknown";

export interface RosterMatch {
  member: Member | null;
  score: number;
  method: MatchMethod;
  /** Populated when two or more members are equally plausible. */
  candidates: Member[];
}

/**
 * Resolve a Zoom display name to a portal member.
 *
 * Keyed per ACCOUNT, not per person — "Michael & Diana" is one label covering
 * two humans on one membership, and that is the correct unit because the
 * membership is what gets DM'd. Partial first names ("Jillian") are the real
 * risk: where two members share one, this returns `ambiguous` and the row
 * goes to a human rather than guessing.
 */
export function matchToRoster(label: string, roster: Member[]): RosterMatch {
  const clean = label.replace(/\s*\([^)]*\)\s*/g, "").trim().toLowerCase();

  const aliasHits = roster.filter((m) =>
    m.aliases.some((alias) => alias.toLowerCase() === clean),
  );
  if (aliasHits.length === 1) {
    return { member: aliasHits[0], score: 1, method: "alias", candidates: [] };
  }
  if (aliasHits.length > 1) {
    return { member: null, score: 1, method: "ambiguous", candidates: aliasHits };
  }

  const scored = roster
    .map((m) => ({
      member: m,
      score: Math.max(
        similarity(clean, m.accountName.toLowerCase()),
        ...m.aliases.map((a) => similarity(clean, a.toLowerCase())),
      ),
    }))
    .filter((s) => s.score >= 0.4)
    .sort((a, b) => b.score - a.score);

  if (!scored.length) return { member: null, score: 0, method: "unknown", candidates: [] };
  /* Two near-equal candidates is ambiguity, not a winner by a nose. */
  if (scored.length > 1 && scored[0].score - scored[1].score < 0.15) {
    return {
      member: null,
      score: scored[0].score,
      method: "ambiguous",
      candidates: scored.slice(0, 3).map((s) => s.member),
    };
  }
  return { member: scored[0].member, score: scored[0].score, method: "fuzzy", candidates: [] };
}

/* ── The monthly grid ─────────────────────────────────────────────
   One row per member, one column per session. This is the shape of Gisselle's
   two real sheets, which carry members, consecutive misses, last attended and
   the two flag columns (26 Aug @10:36). Reproducing that shape means there is
   nothing to reconcile when she looks at both. */

export type CellState = "attended" | "missed" | "not_enrolled" | "no_session";

export interface Session {
  sessionId: string;
  track: TrackId;
  /** ISO date of the Thursday. */
  date: string;
  label: string;
  /** Account names present. Absent = missed by everyone enrolled. */
  attended: string[];
  /** False until a transcript for it has actually been read. */
  recorded: boolean;
  /** The session did not happen. Nobody missed it — a cancelled week that
      counts as an absence is how a member reaches four weeks having never
      skipped one. */
  cancelled?: boolean;
  /** Why, so the grid can say rather than just showing a gap. */
  cancelledReason?: string;
}

export interface GridRow {
  member: Member;
  cells: { session: Session; state: CellState }[];
  consecutiveMisses: number;
  lastAttended: string | null;
  flag: FlagTier;
  /** True when this run is what pushed the member over a threshold. */
  crossedThisRun: boolean;
}

export type FlagTier = "none" | "two_week" | "four_week";

export const FLAG_META: Record<Exclude<FlagTier, "none">, {
  label: string;
  action: string;
  misses: number;
}> = {
  /* Different outcomes by design, per 26 Aug @6:03 and @14:47: the two-week
     flag is a portal DM from the track's own host; four weeks escalates to an
     email. Neither is sent from here. */
  two_week: {
    label: "2 weeks missed",
    action: "portal DM from the track host",
    misses: 2,
  },
  four_week: {
    label: "4 weeks missed",
    action: "email — escalated from the DM",
    misses: 4,
  },
};

const tierFor = (misses: number): FlagTier =>
  misses >= FLAG_META.four_week.misses
    ? "four_week"
    : misses >= FLAG_META.two_week.misses
      ? "two_week"
      : "none";

/**
 * Build one track's grid.
 *
 * `crossedThisRun` is what stops the DM treadmill. A flag fires ONCE, on the
 * run that crosses the threshold — not every week thereafter. Without it, a
 * member at six consecutive misses would generate a fresh "DM them" task every
 * Thursday forever, which is how a flag stops being read.
 */
export function buildGrid(
  track: TrackId,
  roster: Member[],
  sessions: Session[],
  latestSessionId: string | null,
): GridRow[] {
  const trackSessions = sessions
    .filter((s) => s.track === track)
    .sort((a, b) => a.date.localeCompare(b.date));

  return roster
    .filter((m) => m.tracks.includes(track))
    .map((member) => {
      const cells = trackSessions.map((session) => {
        if (session.cancelled) return { session, state: "no_session" as CellState };
        if (!session.recorded) return { session, state: "no_session" as CellState };
        /* Before the membership started. Reachable now that enrolment dates
           exist: the previous form tested channel membership, which the
           filter above had already guaranteed, so it never fired. */
        if (member.enrolledFrom && session.date < member.enrolledFrom)
          return { session, state: "not_enrolled" as CellState };
        return {
          session,
          state: session.attended.includes(member.accountName)
            ? ("attended" as CellState)
            : ("missed" as CellState),
        };
      });

      /* Consecutive misses counted backwards from the newest recorded session.
         Attendance resets it — Gisselle, 26 Aug @9:18: "if a member of our
         portal, like a client, attends office hours a day, that kind of like
         resets". */
      let consecutive = 0;
      let lastAttended: string | null = null;
      for (let i = cells.length - 1; i >= 0; i -= 1) {
        const cell = cells[i];
        if (cell.state === "no_session" || cell.state === "not_enrolled") continue;
        if (cell.state === "attended") {
          lastAttended = cell.session.date;
          break;
        }
        consecutive += 1;
      }

      /* Did the newest run cross a threshold, or was it already over it? */
      const priorMisses = Math.max(0, consecutive - 1);
      const crossedThisRun =
        latestSessionId !== null &&
        trackSessions.some((s) => s.sessionId === latestSessionId) &&
        tierFor(consecutive) !== "none" &&
        tierFor(consecutive) !== tierFor(priorMisses);

      return {
        member,
        cells,
        consecutiveMisses: consecutive,
        lastAttended,
        flag: tierFor(consecutive),
        crossedThisRun,
      };
    })
    /* Ranked by consecutive misses descending. At low attendance the flag list
       is long, so the order has to answer "who first?" rather than leaving a
       flat list of everyone. */
    .sort((a, b) => b.consecutiveMisses - a.consecutiveMisses);
}

export const shortDate = (iso: string) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });

/* ── The two follow-up messages ───────────────────────────────────
   Wedding Industry Ads' own templates, verbatim. The two tiers use DIFFERENT
   CHANNELS, which is the whole reason they are separate: the 2-week is a DM
   through the members portal from the track's own host (26 Aug @14:47, "they
   send them a direct message through our portal, the team member that's
   responsible for those attendees"), and the 4-week escalates to email.

   Placeholders resolve from data, never from typing:
     {{First Name}}          the member's own first name
     {{DATE}} / {{TIME}}     the next session for THIS track
     {{Carmen/Jacqueline}}   the track's followUpOwner — Carmen for Google,
                             Jacqueline for Meta
   ──────────────────────────────────────────────────────────────── */

export type MessageChannel = "portal_dm" | "email";

export interface DraftMessage {
  channel: MessageChannel;
  /** Email only — a portal DM has no subject line. */
  subject: string | null;
  body: string;
  /** Who it goes out as. */
  from: string;
  to: string;
  /** Every placeholder that was substituted, so the fill is auditable. */
  filled: { token: string; value: string }[];
}

const TWO_WEEK_DM = `Hey {{First Name}},

How are things going with your ads? Just wanted to give you a heads up that office hours are coming up this week if you'd like to join for feedback on your account or to ask any questions.

Hope to see you there!`;

const FOUR_WEEK_EMAIL = `Hi {{First Name}},

I wanted to follow up on the message I sent a couple weeks ago about office hours. I haven't seen you at a session yet, and I want to make sure you're getting the support you need.

Office hours is where you get direct feedback and can ask questions in real time. Our next session is {{DATE}} at {{TIME}}.

Let me know if there's anything I can do to help make it work for you.

Best,
{{Carmen/Jacqueline}}`;

/** The next occurrence of this track's weekly slot after a given date. */
export function nextSessionDate(after: string): string {
  const d = new Date(`${after}T00:00:00Z`);
  /* Office hours are weekly on a Thursday for both tracks, so the next one is
     always seven days on from the session just recorded. */
  d.setUTCDate(d.getUTCDate() + 7);
  return d.toISOString().slice(0, 10);
}

export const longDate = (iso: string) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  });

/**
 * Render the right message for a flag tier, with every placeholder filled.
 *
 * The tier decides the CHANNEL, not just the wording — a 2-week goes out as a
 * portal DM and a 4-week as an email, so the composer cannot offer the wrong
 * one for the tier.
 */
export function renderMessage(
  member: Member,
  track: Track,
  tier: Exclude<FlagTier, "none">,
  sessionDate: string,
): DraftMessage {
  const nextDate = longDate(nextSessionDate(sessionDate));
  const filled: { token: string; value: string }[] = [
    { token: "{{First Name}}", value: member.firstName },
  ];

  if (tier === "two_week") {
    return {
      channel: "portal_dm",
      subject: null,
      body: TWO_WEEK_DM.replace(/\{\{First Name\}\}/g, member.firstName),
      from: `${track.followUpOwner} · ${track.channel}`,
      to: `${member.accountName} — members portal`,
      filled,
    };
  }

  filled.push(
    { token: "{{DATE}}", value: nextDate },
    { token: "{{TIME}}", value: track.sessionTime },
    { token: "{{Carmen/Jacqueline}}", value: track.followUpOwner.split(" ")[0] },
  );
  return {
    channel: "email",
    subject: "Following Up on Office Hours",
    body: FOUR_WEEK_EMAIL.replace(/\{\{First Name\}\}/g, member.firstName)
      .replace(/\{\{DATE\}\}/g, nextDate)
      .replace(/\{\{TIME\}\}/g, track.sessionTime)
      .replace(/\{\{Carmen\/Jacqueline\}\}/g, track.followUpOwner.split(" ")[0]),
    from: `${track.followUpOwner} · hello@weddingindustryads.com`,
    to: member.accountName,
    filled,
  };
}
