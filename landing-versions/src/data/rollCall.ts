import type { Member, Session } from "@/lib/rollCall";

/* ────────────────────────────────────────────────────────────────
   Roll call — the roster and the tracked month.

   THE ROSTER IS THE INTEGRATION. Membership comes from the two members-portal
   channels in GHL Communities — Google Search Accelerator and Meta Ads
   Accelerator — which is what decides whether an attendee "belongs" to the
   session that was pasted. Only accelerator members can join office hours at
   all; full-service Elevate clients are a different relationship entirely
   (Whitney, 26 Aug @15:50: "we work with clients in two different capacities").

   MOCKED, and labelled as such on screen: the GHL Communities invite has been
   sent but not accepted, so no roster has been read over the API yet. The
   shape below is what that read returns — account name, business, join
   aliases, channel membership — so swapping the fixture for a live call
   changes the loader and nothing else.

   THE TRACKED MONTH is the five Thursdays to 12 February 2026, because 12 Feb
   is the one office-hours transcript we actually hold. Everything before it is
   seeded history; 12 Feb itself is unrecorded until a transcript is pasted,
   which is what makes the flags move in front of you rather than arriving
   pre-computed.
   ──────────────────────────────────────────────────────────────── */

export const TRACKED_MONTH_LABEL = "Five Thursdays to 12 Feb 2026";

/** The session the demo transcript belongs to. Unrecorded until pasted. */
export const DEMO_SESSION_ID = "g-2026-02-12";

export const ROSTER: Member[] = [
  {
    memberId: "M-101",
    firstName: "Erin",
    accountName: "Erin Smith",
    business: "Brooklyn Garden Venue",
    aliases: ["Erin Smith", "Erin"],
    tracks: ["google"],
  },
  {
    /* One membership, two humans on the call. Attendance is keyed per ACCOUNT
       precisely so this resolves structurally rather than needing a rule. */
    memberId: "M-102",
    firstName: "Michael & Diana",
    accountName: "Michael & Diana Powell",
    business: "Powell Bridal House",
    aliases: ["Michael & Diana", "Michael and Diana", "Diana Powell"],
    /* META ONLY — and they turn up in the Google session. That is the
       cross-track signal the card exists to surface: either they joined the
       wrong room, or the roster is stale. Both need a human, not a flag. */
    tracks: ["meta"],
  },
  {
    /* Two Jillians, both of whom join as just "Jillian". This is the real
       identity risk, not a contrived one — the 12 Feb transcript labels her
       with a bare first name and nothing else. */
    memberId: "M-103",
    firstName: "Jillian",
    accountName: "Jillian Reyes",
    business: "Glow Bridal Beauty",
    aliases: ["Jillian", "Jillian Reyes"],
    tracks: ["google"],
  },
  {
    memberId: "M-104",
    firstName: "Jillian",
    accountName: "Jillian Alvarez",
    business: "Lumen Studio",
    aliases: ["Jillian", "Jillian Alvarez"],
    tracks: ["google"],
  },
  {
    memberId: "M-105",
    firstName: "Nora",
    accountName: "Nora Chen",
    business: "Fern & Field",
    aliases: ["Nora Chen", "Nora"],
    /* In both channels, so she appears on both tabs — and a Google miss does
       not clear a Meta miss. The two counters are genuinely independent,
       which is why the two sheets exist separately today. */
    tracks: ["google", "meta"],
  },
  {
    memberId: "M-106",
    firstName: "Tobias",
    accountName: "Tobias Wren",
    business: "Wren House",
    aliases: ["Tobias Wren", "Tobias", "Toby Wren"],
    tracks: ["google"],
  },
  {
    memberId: "M-107",
    firstName: "Priya",
    accountName: "Priya Raman",
    business: "Saffron Events",
    aliases: ["Priya Raman", "Priya"],
    tracks: ["google"],
  },

  {
    memberId: "M-108",
    firstName: "Dale",
    accountName: "Dale Okoro",
    business: "Okoro & Sons",
    aliases: ["Dale Okoro", "Dale"],
    tracks: ["google"],
  },
  {
    memberId: "M-109",
    firstName: "Shannon",
    accountName: "Shannon Lee",
    business: "Lee & Co Bridal",
    aliases: ["Shannon Lee", "Shannon"],
    tracks: ["meta"],
  },
  {
    memberId: "M-110",
    firstName: "Marcus",
    accountName: "Marcus Hale",
    business: "Hale Photography",
    aliases: ["Marcus Hale", "Marcus"],
    tracks: ["meta"],
  },
  {
    /* THE LATE JOINER. Enrolled 5 Feb, so the January sessions read "not
       enrolled" rather than as misses. Without the enrolment date she would
       arrive at her second week already carrying a four-week flag — exactly
       the false absence the client asked us to avoid. On Meta, so the
       Google track's engineered narrative above stays intact. */
    memberId: "M-111",
    firstName: "Rosa",
    accountName: "Rosa Delgado",
    business: "Delgado Barn",
    aliases: ["Rosa Delgado", "Rosa"],
    tracks: ["meta"],
    enrolledFrom: "2026-02-05",
  },
];

/* ── Seeded history ───────────────────────────────────────────────
   Engineered so the 12 Feb paste moves real numbers:

     Erin Smith    missed 29 Jan + 5 Feb, then attends -> RESETS to 0
     Nora Chen     missed 5 Feb, misses again -> CROSSES the 2-week flag
     Tobias Wren   missed 22 Jan onward -> CROSSES the 4-week flag
     Dale Okoro    missed everything -> already past 4 weeks, so NO new flag
     Priya Raman   attended 5 Feb, misses once -> 1 miss, no flag yet

   Dale is the important one. He is the case that proves the flag fires once on
   crossing rather than every week: without that rule he would generate a fresh
   "DM him" task every Thursday forever, and the flag would stop being read. */
export const SEEDED_SESSIONS: Session[] = [
  {
    sessionId: "g-2026-01-15",
    track: "google",
    date: "2026-01-15",
    label: "Google Ads office hours",
    attended: ["Erin Smith", "Tobias Wren", "Priya Raman", "Nora Chen"],
    recorded: true,
  },
  {
    sessionId: "g-2026-01-22",
    track: "google",
    date: "2026-01-22",
    label: "Google Ads office hours",
    attended: ["Erin Smith", "Priya Raman", "Nora Chen"],
    recorded: true,
  },
  {
    sessionId: "g-2026-01-29",
    track: "google",
    date: "2026-01-29",
    label: "Google Ads office hours",
    attended: ["Priya Raman", "Nora Chen"],
    recorded: true,
  },
  {
    sessionId: "g-2026-02-05",
    track: "google",
    date: "2026-02-05",
    label: "Google Ads office hours",
    attended: ["Priya Raman"],
    recorded: true,
  },
  {
    /* The demo target. `recorded: false` and no attendance until a transcript
       is read, so the grid visibly gains a column rather than arriving full. */
    sessionId: DEMO_SESSION_ID,
    track: "google",
    date: "2026-02-12",
    label: "Google Ads office hours",
    attended: [],
    recorded: false,
  },

  /* Meta runs on its own counter. Its 12 Feb session is deliberately left
     unrecorded with no transcript available — an honest "nothing pasted for
     this one yet" is more useful than a full-looking grid. */
  {
    sessionId: "m-2026-01-15",
    track: "meta",
    date: "2026-01-15",
    label: "Meta Ads office hours",
    attended: ["Shannon Lee", "Marcus Hale", "Michael & Diana Powell"],
    recorded: true,
  },
  {
    sessionId: "m-2026-01-22",
    track: "meta",
    date: "2026-01-22",
    label: "Meta Ads office hours",
    attended: ["Shannon Lee", "Michael & Diana Powell"],
    recorded: true,
  },
  {
    /* THE CANCELLED WEEK, on the Meta track. Nobody missed it, so it must
       not count against anyone's streak — a cancelled session scored as an
       absence is how a member who never skipped one reaches four weeks. It
       sits here rather than on Google because the Google track carries the
       engineered flag narrative above and moving one of its columns would
       silently rewrite four members' counters. */
    sessionId: "m-2026-01-29",
    track: "meta",
    date: "2026-01-29",
    label: "Meta Ads office hours",
    attended: [],
    recorded: false,
    cancelled: true,
    cancelledReason: "Jacqueline travelling — session cancelled, nobody missed it",
  },
  {
    sessionId: "m-2026-02-05",
    track: "meta",
    date: "2026-02-05",
    label: "Meta Ads office hours",
    attended: ["Shannon Lee", "Marcus Hale"],
    recorded: true,
  },
  {
    sessionId: "m-2026-02-12",
    track: "meta",
    date: "2026-02-12",
    label: "Meta Ads office hours",
    attended: [],
    recorded: false,
  },
];

/* ── Processing stages ────────────────────────────────────────────
   Three of four genuinely run against the pasted text. The fourth is the
   roster read, which is the mocked one and says so — a spinner with an
   invented label is the one part of a mock that costs more than it returns. */
export interface StageSpec {
  id: string;
  label: string;
  real: boolean;
  holdMs: number;
}

export const STAGES: StageSpec[] = [
  { id: "read", label: "Reading the transcript", real: true, holdMs: 1200 },
  { id: "attendance", label: "Working out who actually spoke, and for how long", real: true, holdMs: 1700 },
  { id: "roster", label: "Matching speakers to the members-portal roster", real: false, holdMs: 3200 },
  { id: "flags", label: "Counting consecutive misses and checking the flags", real: true, holdMs: 1500 },
];

export const REVIEW_DATE = "2026-02-12";
