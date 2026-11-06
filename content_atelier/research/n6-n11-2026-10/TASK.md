# The task of record for Phases N6, N10, N7 and N11 (the owner's words, 25 October 2026)

Kept verbatim so a later context starts from the owner's own words. `DECISIONS.md` lists the decisions taken from them;
`HANDOFF.md` says where the work stands.

## The task

> Merge everything into main and begin working on -
> Phase N6. Reliability and the review document
> Phase N10. Hardening and operations
> Phase N7. Scheduling and automatic collection
> Phase N11. Diagnostics, the full gate and later
>
> Basically I want to complete this system, and have it fully benchmarked and made sure it is generating high quality
> content that aligns with WIA's standard.
> Check everything - content packs we showed to WIA - all the feedback- the transcripts of those as well, the chatgpt
> exports, the plans - even the UI visually needs to be done now.
> There can be no margin of errors now and we can not have anything pending as well - this system needs to work on it own.
>
> Now somethings to note here -
> I dont want to send out any alert emails or slack sent out currently, I want no LLM judge build - any content piece that
> needs reviewed - you do it, The next weekly intake shoudl start next sunday - 1st Nov.
> The system currently, should only have content pieces generated from the last weeks calls .
> I have increase openrouter budget - you have the remaining budget in both keys to complete this task - so use it wisely.

## The owner's decisions, in order

1. > forget about - OpenRouter privacy check
   > only calls for now no instagram or email connectors or dms and anything else - just call transcripts
   > budget is the hard celing for this task - generate less if needed but generate high quality content
   > Ok keep the older cards, briefs and packs - if they are verified of quality - but last weeks needs to be regenreated
   > and fully tested out to be proper
2. > go with the smaller USD 6 option.
   > Also, I get a feeling throughout this implementation we have built things that can not be autonomously maintaned - I
   > could be wrong here but make sure this is not the case.
   > Make sure that everything we are building, can be maintained by the system week after week by itslef - the client
   > context, account memeory - everything. But this does not mean we rei-introduce LLM judge that is still out of the
   > question.
3. (After the pause and summary, 25 October, about 18:00 UTC.)
   > i am going to leave this session unattended , so you will have no help from me here on out. Take any decsions you need
   > to the best of your judgement. IF something truly can not be done - defer it, but complete the task.

4. (25 October, after checking the app.)
   > I just checked the UI and it is leaps and bounds different from the mockup UI we presented to the client. I know we
   > changed things and added more things but it still needs to align somewhat with the mockup atleast the core parts.
   > And I feel we are giving too much information and too much technical details on pages that do not need it and is not
   > client facing. PLease re-align yourself here and make sure that UI fix is now also part of your task list. This is
   > unpresentable the way things are right now - no matter the quality of content.
   > Do this last once the actual content task is complete

## What the answers settled (agent's summary; the full list is in DECISIONS.md)

- Last week is Sunday 18 to Saturday 24 October (Chicago); it is regenerated on production and fully tested.
- The schedule starts Sunday 1 November 2026, 04:00 America/Chicago (collect 25 to 31 October, then the cycle, then the
  review document in the app); afterwards hourly collection and the Sunday cycle every week.
- Benchmark: the smaller option (about USD 6, the Client key, on a copy): Week 2 in full, Week 1 cards only, held out (D28).
- Merges: nothing on Atelier main was unmerged; the old `handoff/wave1-*` branches and Jainil's unreviewed Command Center
  `feat/marble-landing` stay out.
- Production screens are checked on a local copy of production's data (no password on production).
- From the third message on, the agent decides everything itself and defers only what truly cannot be done, recording why.
