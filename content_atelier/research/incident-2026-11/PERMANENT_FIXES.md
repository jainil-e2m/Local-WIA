# First production week: deferred and permanent fixes

Written 3 November 2026, after WIA's first live week. This is the one list of everything deferred: what is still only worked around, in priority order, with the cause, where the code is and what done looks like. Nothing here is built yet. What the owner must decide, what was left in place on purpose and what already shipped are at the end.

The fixes that shipped are in PRs #50 to #62. The record of the 2 November recovery is `implementation_changes(2 Nov 2026).md`, kept outside this repo.

## 1. Weekly input-size refusal: can stop next Sunday's run

**What happens.** The weekly call is refused before it is sent: "Whole-week token budget exceeded". On 2 November it was worked around by hand, sending 284 of 291 scenes for that one run. Nothing permanent changed, so any week of about this size can fail the same way. The next scheduled run is Sunday 8 November.

**Cause.** `backend_pipeline/token_budget.py`, `byte_budget_preflight`, counts one token per UTF-8 byte, then adds a 10% margin. That is far above real usage:

| Measure, recovered week | Value |
| --- | --- |
| Allowance sent to the check | 816,111 |
| Tokens the provider actually counted | 216,072 |
| Real ratio | 3.78 bytes per token |
| Prompt limit on the saved route | 922,000 |

**Fix.**
- Count at most one token per 2 bytes. That is still almost twice the measured density, and it keeps the 10% margin and the limit. A packet would then need to reach about 1.68 MB before a refusal, against about 840 KB today.
- Update `tests/test_luna_costs.py::test_luna_preflight_blocks_overflow_without_editing_payload`, which uses a 1.05 MB packet, and the matching wording in `moments/queue.py::estimate`.
- For a week that still does not fit, leave out `internal_only` scenes first and record the coverage honestly, as the hand recovery did. Never drop a public-eligible scene silently.

**Done when.** The recovered week's real 291-scene request passes the check, an oversized packet is still refused, and the 8 November run reaches Gate 1 with no hand steps.

## 2. Brief timing: needs evaluating

**Status: needs evaluating.** Nothing has been changed yet, and the causes below are measurements from a few runs, not a finished diagnosis. The owner asked for this to be evaluated properly.

**What happens.** Briefs are the slowest step WIA waits on. On production, a first brief has taken 13 to 53 minutes, most near 25, and a new version from feedback 13 to 59. The steps run strictly one after another. The screens say 15 to 30 minutes (`frontend/src/components/studio/GenerationTime.tsx`), so an evidence-heavy card can run well past what WIA is told.

**Measured so far, second live run (a light card, 3 scenes):**

| Step | Time | Note |
| --- | --- | --- |
| Evidence search | about 4.5 min | No model involved. About 30 seconds per search. Seen on the new version, whose model answers were all replayed. |
| Planning and grading | about 7 min, first version only | Each round sends about 70,000 tokens. Each grading answer is 16,000 to 19,000 tokens. |
| Writing | 2 to 3.5 min | One call, about 8,000 to 9,000 tokens out. |
| Checking against the calls | about 2 min | One call, about 18,000 tokens out. |
| Automatic repair, then recheck | about 2 min | Ran on all three briefs measured. |
| Gaps between steps | about 2 min in all | 15 to 20 seconds rebuilding and re-checking inputs before each call. |

**What makes it worse.** An evidence-heavy card sends about 157,000 tokens per call, more than double. One provider rate-limit failure cost 24 minutes on the first test card (`brief_repair` failed at 23:46, retried at 00:10).

**To evaluate, in this order.**
1. Profile the evidence search (`briefs/workflow.py::research`, `retrieval.search`, `retrieval.expand`). 30 seconds a search is very slow and costs nothing in model spend. Check the indexes and what `expand` reads.
2. Check whether the second grading round re-grades everything. Both rounds sent the same amount (70,533 tokens), which suggests it does. If so, grade only the new evidence: about 2 to 3 minutes and USD 0.30 a brief.
3. Find out why repair runs every time: about 2 minutes and USD 0.20. The writer is probably being asked for something the checker keeps rejecting.
4. Check why `brief_plan` needs the whole evidence set (about 70,000 tokens in, about 400 out), and whether a smaller input or prompt caching would serve.
5. Look at the 15 to 20 seconds before each call.
6. Consider running independent steps at the same time, and sending only a scene's anchor passages to research (item 9).

Measure each change on the same card, and include one evidence-heavy card.

**Done when.** There is a measured breakdown across at least one light and one evidence-heavy card, a decision on which changes to make, a typical brief under 15 minutes if the evaluation supports it, and the on-screen times updated to match.

## 3. Fathom collector backlog

**What happens.** 103 collection requests sit in `pending_transcript`, some on their 106th attempt, making about 200 Fathom calls an hour and drawing repeated HTTP 429s. New calls are still discovered, but the connection reads as pending and the rate limit is spent on nothing.

**Cause.** `backend_pipeline/intake/fathom.py`, `collect`:
- Recording `197260974` ("Impromptu Zoom Meeting") answers 404, although a revision of it has been stored since 28 October.
- A 404 sets `unavailable` on whichever request happens to be running, so one bad recording holds every request open.
- `pending` includes any source whose `last_checked_at` is over a day old. A 404 never updates that time, so the recording is fetched again on every retry of every request.
- A 429 only delays the job that received it, so the others keep calling (`intake/runtime.py`, `execute`).

**Fix.**
- A request waits only for recordings discovered in its own window that have no stored revision. Rechecks of older sources are best-effort and never hold a request open.
- On 404 or pending, always write `last_checked_at`. If the source already has a revision, keep that revision and do not set `pending_transcript`.
- Recheck a source with no revision no more than every few minutes, and give up after about 3 days with a visible status and alert.
- A 429 pushes `retry_at` forward for every waiting `intake_fathom` job, in the same transaction.

**Done when.** The 103 requests settle with no manual reset, the stored revision of `197260974` is unchanged, Fathom calls fall to a few an hour, and connection health reads ready.

**Also seen.** The stuck intake queue raises `job_stuck` alerts that resolve themselves and fire again, 11 between the evening of 2 November and early on 3 November. This is the likely cause of the bell briefly showing "1 open alert" during the first live test, though that was not traced. The alerts should stop once the backlog settles; check this as part of the fix.

## 4. A failed weekly run has no self-service recovery

**What happens.** Three failed attempts exhaust the claim `schedule.weekly_cycle.<date>`. A redeploy does not re-arm it, so recovery on 2 November meant editing the claim's attempt counter in the database by hand.

**Fix.** Add an approver action on the alert (or a documented command) that re-arms one exhausted claim under the scheduler's lock, refuses if a cycle for that window exists, and records who did it.

**Done when.** A missed run can be recovered without touching the database.

## 5. Role checks that bypass the `users` table

**What happens.** `gates.roles.access_for` resolves a bare string from the environment lists only. That caused the stuck card: the worker held WIA's address as text, read them as a viewer, and the new version's check waited forever. PR #50 fixes the worker paths with `access_in`.

**Fix.**
- Make the bare-string path impossible by taking the connection and resolving through `users`, or fail loudly.
- Retire `ATELIER_BRIEF_APPROVERS`, `ATELIER_BRIEF_EDITORS` and `ATELIER_INTAKE_ADMINS` once every person has a `users` row.
- Add a test environment in which only `users` rows exist. Every test account so far was also on a list, which is why no test found this.

**Done when.** The end-to-end suite passes with the lists empty.

## 6. A check that waits should never wait silently

**What happens.** A version's check that needs an embedding it will never receive stays `waiting` indefinitely. The card only says the version has not been checked.

**Fix.** Upkeep picks up a check waiting more than a few minutes and either runs it live or raises an alert. The card shows the real reason.

**Done when.** No card can sit unchecked without someone being told.

## 7. Revived cards start with placeholders

**What happens.** A revived idea in a v7 week is now a full v7 card (PR #50), but its point tests, offer and belief start as plain placeholders until someone edits it or asks for a refresh.

**Fix.** Fill them with one model call at revive time, using the v2 refresh prompt with the idea and its scenes.

**Done when.** A revived card reads like a generated one, without a manual refresh.

## 8. Test and CI health

- **Backend database suite.** Main was already red before this work: 9 failures on commit `66e0dbb` (CI run 41455645611). It is now 10 failed of 2,112 on `0b8c05c` (CI run 41558974261), and those failures read as weekly-limit tests, not these changes, but that was not traced test by test. Identify and fix them, so a red run means something again. They are:
  - `test_a_call_limit_reached_is_said_as_calls_not_as_money_spent`
  - `test_a_raised_call_limit_queues_a_job_its_call_limit_stopped`
  - `test_a_raised_cap_or_the_next_week_queues_the_waiting_job_again`
  - `test_a_worker_with_no_variable_spends_its_purposes_weekly_plan`
  - `test_m1_exit_an_approver_runs_the_live_path_from_a_window_to_the_review_document`
  - `test_the_call_that_would_pass_the_cap_is_refused_before_sending`
  - `test_the_nightly_run_records_its_dump_and_runs_the_monthly_restore_check_only_when_due`
  - `test_the_status_lists_every_purpose_with_what_is_left_and_waits`
  - `test_the_worst_case_check_holds_the_cap_for_the_call_itself`
  - `test_uncapped_lets_every_call_through_lifts_an_exhausted_week_and_still_records_the_spend`
  - The log also names `test_future_intake.py::test_scanned_pdf_resource_handling_and_page_locations`, which makes 11 names against a count of 10. Confirm which one is not a failure.
- **Browser test (6.X1).** PR #60 changed the approval message and broke `frontend/tests/e2e/acceptance.spec.ts`, which then went unnoticed because merges stopped waiting for CI. It is corrected alongside this document. Merging without waiting for CI is the owner's decision, so check CI after the merge instead, including this browser test, which unit tests do not cover.
- **Windows.** 29 frontend test files fail on Windows with `Cannot read properties of undefined (reading 'bind')`. They pass on Linux. To run them locally, use a `node:22-bookworm-slim` container with a copy of `frontend` and run `npm run test:unit`.

## 9. Brief size limit and cost on evidence-heavy cards

`briefs.max_characters` was 120,000. It is now 600,000 on production as a settings row, while the code default is still 120,000. A scene can cite about 290 passages, and that card's brief cost USD 2.82. Set the code default to match, and consider sending only a scene's anchor passages to the research stage, which would cut most of that cost.

**Production-only settings.** `briefs.max_characters` and `gates.one_click` both live only as rows in the production settings table. A restored or new database would silently go back to 120,000 and to the old approval screens. Decide the code defaults for both.

## 10. Reading a brief is still slow

Reading each transcript once took a heavy brief from about 11 seconds to about 5. It still checks every passage against the original on every read, and the list does it for every brief. Check once when a brief is saved, then trust the hash on reads.

The week's review (`GET /weeks/{id}`, `repository.review`) returns every run with its full inputs, every job's results and every event of the week: over 6 seconds on the recovered week, and it grows with each action. Under load it passed the relay's 10 seconds, and Weekly Studio showed "backend unavailable". The relay now waits longer for it, which only buys time. Return what the screens read and move the rest behind its own route.

**3 November, evening: the review's largest cost is fixed; its size is not.** With three people on Weekly Studio the API sat at one core and the screens timed out. Account memory re-read a whole transcript with every internal-meeting scene, 41 MB for each card's account. Each transcript is now read once per request, each account's timeline built once, a pack's calendar checks run once a listing, a brief's checks once a read, and the API runs three processes. On a copy of production the review went from 2.1 to 0.5 seconds and the calendar from 1.1 to 0.2. The review still returns 1.2 MB and a brief still checks its passages on every read: those two remain to do, as above.

## 11. Decide what `gates.one_click` leaves behind

With the setting on, the screens ask only for feedback and approval. The public stance, verify items, CTA, before-publishing answers, public-quotation clearance and claims check no longer stop an approval or show on the screen. Decide with WIA whether any should return as a check on the finished pack before it is published, since nobody is now asked to clear client permission to use quotes. Material a client asked to remove, a stale version and a card rejected for public use still stop an approval.

Once this is decided, remove the screens the setting hides: the old field-by-field `BriefFieldEditor`, the stance, CTA, answers, claims and clearance forms. Both editors exist today only because the code default is still off.

## 12. A transient database error fails a brief step

A deadlock failed a brief's validation step with no automatic retry, and the screen said "deadlock detected". It was caused by a hand-run transaction on production during a run, so it is unlikely in normal use. Retry such errors automatically, and word them plainly on screen. **Never hold a write transaction on production while a run is active.**

## 13. An old link to a replaced card

The dialog follows a replaced card one version forward, because the week lists replaced versions only if the strategist chose them. A link two or more versions old says the card was replaced, and a chosen original can open on its old version. Fix: have `GET /weeks/{id}` return each replaced id's newest version.

## Waiting on the owner

These need the owner, not code.
- **Item 11:** decide what `gates.one_click` leaves behind, including who clears client permission to quote.
- **Slack reply to WIA:** the owner sends it. The draft is in the local handoff, `research/incident-2026-11/HANDOFF.md`.
- **Redis password (optional):** `ATELIER_REDIS_URL`, with its password, was printed in a session's output on 2 to 3 November. It is reachable only inside Railway. Rotate it if wanted.

## Left in place on purpose

- **Older weeks, packs and costs stay.** The owner narrowed the cleanup to this session's test leftovers, so the weeks of June and of 12, 18 and 20 October, their 34 packs, and all costs on the costs page stay. If they are ever cleared, keep the `weekly_angles` run rows: `cycle/window.py` reads them to know which documents a cycle has read, and without them old documents return as late arrivals. Also trim `matching_result` on the current week's cards, which cites older angles. Take a backup first: none was taken for this cleanup, on the owner's word, though it only removed the throwaway card and failed-call records.
- **Both test runs stay in WIA's week**, with their cost logs: packs `pack_12ac486d1e600f06c18d991e` and `pack_f562a07d71f4fe3affee0503`. Their verify items were handled for testing only, so nothing from either should be published without real checks. The second pack has six review notes open.
- **Two cancelled check runs stay** on WIA's week, `run_14a7c455fba241a1bf072de64eff30b0` and `run_86db59dd971e4df09c1b15e0553761ed`. They are not from the test runs.

**Closed since this list was first written.**
- OpenRouter credit: the account is on automatic top-up (the owner, 3 November).
- Clean-up after the live test: the temporary TCP proxies are deleted, `run_86db59dd…` is cancelled, and the owner decided the test items stay.

**Not yet seen live.** The pack-time lines added in PR #62, on the brief dialog and the pack page, passed tests but no pack was running after they deployed. Look at them during the next pack.

## Live test on production, 3 November

A discarded idea went all the way through on production: revive, refresh with feedback, re-check, approve, brief, brief feedback, one-click approval, then a pack of 1 email, 1 carousel and 3 Reels with no blockers.

One-click approval of a card with an unconfirmed stance was not exercised in this run. The second run proved it live.

## Live test on production, second run, 3 November

Revive, refresh (exact stance, 35 seconds), one-click approval of an unconfirmed stance, brief (22 minutes), a saved text edit, brief feedback (13 minutes, the edited line kept word for word), a second saved edit, one-click approval, pack (4 minutes 26 seconds, USD 1.28; whole run USD 3.73). The pack is in review with six review notes.

Found by it and fixed in PRs #60 to #62: the review dialog ended on "not part of the week" when a refresh finished while it was open; the old version stayed approvable meanwhile; "Edit the text" read as missing at the foot of a long brief.

## 6 November: hardened for the 8 November run (PR #65)

Done, deployed on `a54c620`, and exercised on production (then removed: DEPLOYMENT.md, "6 November").

- **Item 1, closed.** The byte allowance counts a token per 3 bytes, not 1 (measured 3.78). This week's real request was
  250,248 tokens, larger than the refused one of 2 November, so it would have been refused again at one a byte; it passed.
  A week still too large leaves out its `internal_only` scenes (`size_dropped`, coverage `incomplete`), never a
  public-eligible one.
- **Item 3, closed.** A 404 on a recording with a stored transcript no longer holds any request; a request waits only for
  its own window's new recordings, for at most 3 days; a 429 holds every waiting collection. Production went from 183
  requests pending (some on attempt 187) to all 237 completed within the hour.
- **Item 4, partly.** A failed scheduled task now waits 10 minutes per failed attempt, and the weekly cycle has 8 attempts
  (about 4.5 hours) instead of 3 in 90 seconds; the alert says when it is still retrying. There is still no self-service
  re-arm after the eighth.
- **New: the weekly run waits out the provider.** Scene extraction and card generation wait out a 429, 5xx, refused
  connection or an answer ending in the provider's own error (`finish_reason: error`, nothing written: the "cut off" scene
  failure of 4 November) for about 14 minutes. A read timeout is not resent.
- **New: one bad call no longer stops the week.** A minority of calls whose scenes fail are left out and named
  (`failed_documents`); most failing still fails the week.
- **New: scheduler memory.** It grew about 1 GB a day toward its 8 GB limit, a step at each hour. Not traced to one line
  (the hourly upkeep alone did not reproduce it in the image); it now returns freed heap after each pass and re-executes
  itself in place past 1 GB.
- **Item 10, a little.** A brief read compiles its patterns once: the `/briefs` list about a third faster. With 8 people
  reading at once on production it still takes 13 seconds typical, 18 at most (under the relay's 60), and the week's
  review 2.4 seconds. The remaining cost is still each brief's checks and account memory on every read.
- **Brief timing (item 2), measured on production with 2 editorial replicas:** two first briefs 16 and 18 minutes side by
  side, a revision with feedback 12 minutes (the edited line kept word for word), packs 4 to 8 minutes, a refinish 4.

Still open from this list: items 2, 4 (self-service), 5 to 9, 11 to 13; the job-failed alert for the 4 November call stays
open although that call's scenes now exist (resolve it on the alerts screen).

## What already shipped (PRs #50 to #62)

- Revive works in a window-cycle week; every revive there used to be refused (#51).
- A brief that stops says so on its card, with the reason and a retry (#52).
- A provider's passing 429 or 5xx is waited out on briefs, packs and refreshes, and refused calls no longer use up a run's call budget (#53).
- A heavy brief no longer takes down the Briefing page, because each transcript is read once and these reads get the longer relay timeout (#54).
- A public quotation can be cleared on the brief screen (#55).
- One-click approval and feedback-first screens, behind the setting `gates.one_click` (#56).
- A busy week no longer takes down Weekly Studio (#57).
- Workers and the scheduler resolve a person's role through `users` (`gates.roles.access_in`), so a refreshed card's check runs live.
- A refresh rewrites the whole v7 card, public stance and evidence included, on prompt `card-reframe.feedback.v2`. Wording given for the stance is used exactly, and fields a person wrote stay locked.
- A revived idea in a v7 week is a v7 card with the same gates as its siblings.
- The card shows what a refresh changed and why, with the feedback folded, says when a new version is being checked, and the stance panel says how to change the wording.
- The review dialog follows a refreshed card, and a card with a refresh on its way can be neither approved nor edited (#60).
- "Edit the text" swaps the card or brief for an editor where every line is already a field, from a button at the top and beside approving (#60, #61).
- Refreshes, briefs and packs say how long they take, from one file of measured times (#60, #62).
