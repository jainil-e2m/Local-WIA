/* ────────────────────────────────────────────────────────────────
   The Meta track fixture — SYNTHETIC, and that is the point.

   WHY THIS EXISTS. The console could only ever process one session: Google,
   12 February, the one real transcript we hold. So the second track had no
   demonstration, and neither did the two exception cases the client's own
   format guarantees will happen — a member who joins, listens and leaves
   without speaking, and a member who says one line and goes.

   WHY IT IS NOT CARVED OUT OF THE REAL ONE. `rollCallTranscript.ts` is a
   genuine members' session with genuine members in it. Editing it to insert
   a brief speaker would make a real record say something that was never
   said, and would quietly destroy the one fixture whose attendance
   derivation is checkable against reality. So the exception cases live here
   instead, in a file whose first line says it is invented.

   WHAT IT DEMONSTRATES, in order:
     · Shannon Lee — a full consultation. Clears the engagement floor.
     · Marcus Hale — “morning, just listening in today.” ONE turn, well under
       the floor. Scored absent unless a human confirms he was there. This is
       the brief-attendee case.
     · Rosa Delgado — does not appear at all. She was on the call. She is the
       silent-attendee case, and she can only be added from the roster,
       because there is no speaker row of hers to correct.
     · Michael & Diana Powell — enrolled here, and absent. Their appearance in
       the GOOGLE fixture is the cross-track signal; here they simply miss.

   Nothing in this file is a record of anything. It is a test case for the
   review controls, and it is listed as invented in the data inventory on
   Source Coverage.
   ──────────────────────────────────────────────────────────────── */

export const META_SESSION_META = {
  title: "Meta Ads Office Hours — 2.12.26 (synthetic fixture)",
  host: "Jacqueline Hood",
  date: "2026-02-12",
  sourceLabel: "Meta Ads office hours, 12 Feb 2026 — INVENTED for the exception cases",
} as const;

export const META_TRANSCRIPT = `Meta Ads Office Hours - 2.12.26 - February 12
VIEW RECORDING - 41 mins (No highlights):

---

0:00 - Jacqueline Hood (weddingindustryads.com)
Morning everyone, give it a minute for people to come in. As always this is a drop-in, so bring whatever you have got and we will work through it. If you would rather just listen that is completely fine too.

0:44 - Marcus Hale
Morning, just listening in today.

1:02 - Jacqueline Hood (weddingindustryads.com)
No problem at all Marcus, good to have you. Shannon, I can see you are on — did you want to start? I know you had the creative question from last week.

1:20 - Shannon Lee
Yes please. So we swapped the hero image on the client attraction set like you suggested, and the cost per lead came down but the volume dropped with it. I am not sure whether that is a win or not.

1:52 - Jacqueline Hood (weddingindustryads.com)
That is the right question to be asking, and it is the same one Whitney covers in the landing page session. Cost per lead on its own is not the scoreboard. What happened to the quality? Are the inquiries coming through better qualified, are more of them booking tours?

2:21 - Shannon Lee
Better, honestly. We had four inquiries last week and three of them booked a tour. Before that we were getting maybe eight or nine and one would book.

2:48 - Jacqueline Hood (weddingindustryads.com)
Then that is a win and I would not touch it. Three tours out of four inquiries is a completely different business than one out of nine. Your team is spending less time on people who were never going to book.

3:15 - Shannon Lee
That makes sense. Should I roll the same image into the retargeting set?

3:30 - Jacqueline Hood (weddingindustryads.com)
Not yet. Retargeting is a different audience — they already know you, so the job of that creative is to remind rather than to introduce. Let the client attraction set run another two weeks first so we have enough data to say the drop in volume is stable and not just a slow fortnight.

4:10 - Shannon Lee
Understood. And the budget, do I leave it where it is?

4:22 - Jacqueline Hood (weddingindustryads.com)
Leave it. If you raise spend now you change two things at once and you will not know which one moved the number. One change at a time.

5:03 - Shannon Lee
Perfect, thank you. That is all I had.

5:20 - Jacqueline Hood (weddingindustryads.com)
Great. Anyone else want to bring something up? I am happy to look at accounts if you want to share your screen.

12:40 - Jacqueline Hood (weddingindustryads.com)
All right, I will leave the room open for a bit in case anyone comes in late. Recording stays on. If you are watching this back, the short version is: judge the creative on booked tours, not on cost per lead, and change one thing at a time.

41:00 - Jacqueline Hood (weddingindustryads.com)
That is us for this week. Same time next Thursday, and drop anything urgent in the channel before then.
`;
