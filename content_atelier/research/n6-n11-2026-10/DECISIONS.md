# Phases N6, N10, N7 and N11: the owner's decisions (25 October 2026)

On 25 Oct 2026 the owner approved running Phases N6, N10, N7 and N11 (plan order N6, N10, N7, N11; names kept) to
complete the system, with these changed requirements.

1. **Calls only.** No Instagram, email-platform or DM/applications connectors (6.B16, 6.B17 out). Account memory and
   client context come from call transcripts (client calls + internal meetings) only. 3.B17's Week 2 venue "what we
   built" is a recorded calls-only limit, not pending work.
2. **S.B1's OpenRouter dashboard check dropped** ("forget about it").
3. **No alert emails, no Slack.** Alerts are recorded and shown in the app; an email sender may exist but stays off; the
   week's review document waits in the app, never sent.
4. **No LLM judge, ever** (E.B3 paid run, E.B3 extension, E.B24's caption-framework model check: dropped). Every content
   review is the agent's own blind reading, recorded under D12.
5. **Budget is a hard ceiling: the credits both OpenRouter keys had left on 25 Oct, and nothing else** (Client USD 16.17;
   internal USD 0.74). **The internal key's weekly reset (USD 15 from Monday 00:00 UTC) is not this task's to spend** (the
   owner, 25 Oct, correcting the agent's earlier reading). Generate less if needed, never lower quality. Each run under USD 5.
   Since the internal key's USD 0.74 cannot pay for last week's regeneration, production was switched to the Client key on
   25 Oct (OPENROUTER_API_KEY and EMBEDDING_API_KEY on api, scheduler and the three workers), bringing forward the switch the
   owner plans for go-live; the internal key is left untouched from then on. Nothing is held back for WIA's first live week
   (the owner: "Forget about next weeks go live wia first week ... Complete the task").
6. **Benchmark = the smaller option (~USD 6, Client key, on a copy):** Week 2 in full (re-extract, cycle, 2 briefs with a
   refresh each, 2 packs) + Week 1 cards only. Held out (D28: never in prompts). Scored against WIA's 13/20 Oct notes,
   the stories her ChatGPT found, her published pieces, the automatic checks, and a blind mixed reading. Fixes go in new
   prompt versions (released ones never edited); one re-test.
7. **Content on production:** older cards/briefs/packs stay if they pass the agent's reading (failures archived, not
   deleted). Last week = Sun 18 to Sat 24 Oct: regenerated and fully tested end to end.
8. **Schedule:** weekly intake starts Sunday 1 Nov 2026, 04:00 America/Chicago: collect the 25-31 Oct calls, then the
   cycle, then the review document in the app; afterwards hourly collection and the cycle every Sunday 04:00 Chicago (the
   plan's Saturday slot moved). No automatic collection before then.
9. **Autonomy rule:** everything must be maintained by the system week after week by itself (intake, classification,
   identities/accounts, account memory, client context/KB learning, budgets, backups, monitoring, review document) with
   no manual weekly step and no LLM judge. Human steps only where they are the product (Gate 1/2 decisions, founder notes).
10. **Merges:** Atelier main had nothing unmerged; the 19 Oct `handoff/wave1-*` branches are superseded and left out;
    Jainil's Command Center `feat/marble-landing` (no PR, unreviewed) left out.
11. **Decided by the agent:** E.B5 and 3.B4 closed (no scoring call without evidence, R43); E.B8/E.B18 measured free on
    held-out data where possible; X.1 stays the owner's; production screens checked on a local copy of production data;
    hosted CI is blocked by GitHub billing, so CI runs locally and the agent self-merges on green, deploys allowed.
12. **Unattended from 25 Oct, about 18:00 UTC** (the owner's words in `TASK.md`): the agent takes every decision itself, defers
    only what truly cannot be done (with the reason recorded), and completes the task.
13. **The UI realigned with the mockup WIA was shown, last** (the owner, 25 Oct, `TASK.md` item 4): after the content work is
    complete, the app's core screens are brought back in line with the mockup presented to the client (its layout, look and
    flow for the core parts, keeping what was added since), and team-facing pages lose technical detail (ids, models,
    profiles, versions, stages, costs, raw statuses), which moves to Sources or Settings behind an administrators' section.
    The app as it stands is unpresentable; this is part of the task, not a follow-up. The mockup is the demo build WIA was
    walked through on 20 October (plan section 3.1: `MockStudioApp`, now `frontend/src/mock/MockApp.tsx`, built with
    `VITE_ATELIER_MODE=mock`); the realignment runs it beside the real app in the browser and compares the screens visually,
    one by one (the owner: "Visually check and compare with a copy of mockup").
14. **Visual verification on desktop only** (the owner, 25 Oct): the screens are compared and checked at 1440 px; tablet and
    phone widths are not verified visually (they must not break).
