# N4: production go-live (24 October 2026)

This is Phase N4 of the main plan (M4 steps 8 and 9), done unattended on the owner's instruction. WIA's reviews were done
under delegation (D12, R55) as the shared team account `ai@weddingindustryads.com`. Times are UTC.

**Scope (the owner, 25 October IST).**
- **The Fathom collector (6.B1) is left off.** Weekly automatic collection is deferred as late as possible, to Phase N7.
  Until then the week's calls are imported by hand with `documents fathom-backfill`.
- **The Loom is dropped.**
- **No password is entered on production.** The owner does not have the shared account's password. The agent neither
  resets it nor types it into production's sign-in page, so the pack screens were checked on the local copy (step 5).

## Steps

| Step | What was done | Result |
| --- | --- | --- |
| 1. Access | `main` at `e33526a`. A temporary TCP proxy to `postgres` and one to `api` port 8000. Scripts ran from a checkout through `research/packs-2026-10/np5/remote.py`, with production's variables minus every `ATELIER_ALLOW_*` switch, so no local process could make a paid call | The OpenRouter key showed USD 4.64 left of its USD 15 weekly limit. The standing budgets: briefs spent (USD 3.18 of 2.70, N2's spend carried by the restore), the others with room |
| 2. The October backlog (6.B18) | `documents fathom-backfill --from 2026-10-01 --to 2026-10-24`, a dry run first (the listing without invitee metadata: `backfill-2026-10-01-to-24.json`) | 39 meetings listed: 23 already documents, 11 second recordings of stored calls (not imported), 5 new (21 to 23 October). Production's bulk worker normalised them within seconds. Every October call is now a dated document, and none waits |
| 2a. Two titles and a tax call | The document builder took Zoom's "Impromptu Zoom Meeting" over the recording's name, so "Ads Consultation with Peter Larsen" was filed as a client call. This was fixed at its cause (`731dedc`, `fathom_title`, classify-rules-v3). The two new documents were retitled with `retitle.py` (no scenes or vectors yet) and normalised again by the rules. "WIA + Whitney Tax Planning Call" was excluded by a person's decision (`documents classify`, vendor, delegated) | The consultation is now `prospect` (internal-insight lane, never public proof, O11); the kickoff stays `client_1to1`. Every Fathom document already carried `public_use: false`, so nothing could have reached public proof. 11 older documents keep the Zoom title (open item below) |
| 3. Embedding and scenes | `documents reembed --mode live` (54 chunks, 3 included documents), then `moments extract --from 2026-10-20 --to 2026-10-25 --mode live` (scene profile v3), both queued for production's bulk worker | 54 chunks encoded and verified. 54 scenes from the 3 new included calls (27, 17 and 10), 2 quotes repaired, 2 scenes unverified and kept out of proof. **A new call went from import to scenes on production** |
| 4. 7.X1 through production's API | On the restored October cycle (week `week_2026-10-12`), card 4 (`angle_36f6b25c…`, held by the verifier's one blocking flag, an invented reason). Each request went to production's API with the app's secret and the team account, exactly as the Atelier's Node server sends it. The actions are in `gate2-x1.json` and the results in `x1-*.json` | Every step below ran on production's API and workers |
| 4a. Gate 1 edit | The point now says only what the call shows; the private supplier timing left the evidence | New version `angle_f83f7067…`; the blocking flag cleared |
| 4b. Refresh with feedback | Live, under the refreshes budget (`card_refresh_7d9b5e2c…`) | `angle_3e423f56…`: the edited point kept word for word, "why it matters" rewritten from Whitney's two moves alone, no blocking flag |
| 4c. Develop | Decision `decision_f80d1e3b…`, the permission item acknowledged as a before-publishing note | Brief run `brief_run_0d600190…` started by itself in live mode. **Its research waited with its reason in words:** "This week's briefs budget is spent (USD 3.18 of USD 2.70) … an approver can raise it" |
| 4d. The budget released | `budgets set --purpose briefs` to 4.70, then 5.20 (validation's worst case, USD 0.48, passed the room left), a delegated decision: the week's spend was N2's, from before production went live | The waiting jobs were queued again and the brief finished: `brief_f1eb04cb…`, ready for Gate 2 |
| 4e. Gate 2 edit | The two quotations in Reel 1's script told in reported speech (the call is `public_use: false`, as NP-6 did for brief 2), the matching beat, Reel 1's cover named its subject | `brief_bf6bc10b…`; the quotation blocker cleared; three lines locked as the team's |
| 4f. Gate 2 refresh with feedback | Live (`brief_run_2be51b45…`), the refreshes cap raised to 1.50 for it (the writing step's worst case passed the room left) | `brief_3bce289f…`: the three locked lines word for word; Reel 2's cover names its subject; the sibling-repetition and cover warnings gone. The research steps replayed their saved answers at USD 0 |
| 4g. Approve | CTA confirmed (no explicit ask), the five before-publishing items answered (the client's okay a note, never a gate), every claim checked, approved (`brief_fcc397e2…`, decision `decision_f87fbb76…`) | **The pack started by itself:** `pack_run_e672693d…` in live mode |
| 4h. The pack | Assemble, finish (Opus 5.5), check (Sonnet 5.5), repair, recheck, finalize | `pack_e672693d…` in review: 4 pieces from the brief, the stance Reel written. 1 of 14 statements flagged, repaired, rechecked clean, no open finding |
| 4i. Pack edit | Carousel slides 4 and 7 (`x1-pack-edit.json`): Whitney's "That's future, see?" restored in place of the repair's vaguer line, and the email's repeated wording removed | `pack_9f451db3…`: both lines locked as the team's, labelled delegated; the sibling-overlap warning cleared |
| 4j. Export | `GET /weeks/week_2026-10-12/review.md`, `packs.md` and `pack-plan`, all 200 | Review document 98,974 characters (`x1-week-2026-10-12.review.md`), pack document 110,184 (`x1-week-2026-10-12.packs.md`). The plan keeps Monday to Friday as before; the new pack's five pieces go to the bank |
| 4k. Caps restored | `budgets set`: briefs back to 2.70 (D42), refreshes back to 0.50 (D36) | Both read `exhausted` until the renewal on Monday 26 October 00:00 UTC |
| 5. The pack screens | On the local copy (scratch copy B, the same packs as production), through Command Center's sign-on handoff, signed in on localhost with Command Center's development mode. Desktop (1600, 1366), laptop (1024), tablet (768) and phone (375) | The list, the detail with its five tabs, editing (Edit, Save, Cancel), comparing with the brief, the brief's line, review (Ready, before-publishing notes), the week view and its export, and the approved brief's link to its pack all work. **Two layout defects found and fixed** (`d9adebb`): in a narrow piece column the email's three header tiles overlapped ("Recipients" under its links), and a note with an unbroken id ran past its box on a phone |
| 6. 6.C3 | Command Center's Atelier card read "In development" | Command Center PR #4: "Live" wherever the Atelier's URL is configured. Live on production since 24 October: Command Center PR #4 merged at the owner's request (`be38d25`) and its deployment approved; the production card reads "Live" |
| 7. Deployment | The fixes and this record | PR #20 was merged at the owner's request (`main` at `77235ee`, all five CI jobs green) and the newest deployment of each of the seven Atelier services approved; all seven run `77235ee` and the API passes its health check, so the three fixes are on production |

## Defects found and fixed (each with a test that fails without the fix)

1. **"Impromptu Zoom Meeting" titles** (`731dedc`): the consultation was filed as a client call. `fathom_title` now names the
   call for the document builder, the backfill listing and the collector, and the rules treat Zoom's default as saying
   nothing.
2. **The carousel CTA check** (`18745b3`) knew only "you" and "your"; the finisher wrote both readers in the third person.
3. **The pack detail's layout** (`d9adebb`): a container query for the email's header tiles, the links on their own row in
   a narrow tile, and long ids wrapping in notes and quotes.

## Cost (the internal key; production's `llm_runs`, which match the key to the cent)

| Item | USD |
| --- | --- |
| Embedding (54 chunks) | 0.0007 |
| Scene extraction (3 calls) | 0.0331 |
| The card refresh | 0.0782 |
| The brief (two research rounds, writing, validation with one repair) | 1.2554 |
| The Gate 2 refresh (writing and validation; research replayed at 0) | 0.7422 |
| The pack (finish 0.5050, check 0.0553, repair 0.0833, recheck 0.0388) | 0.6824 |
| **N4 total** | **2.7918** |

The key had USD 4.64 left of its USD 15 weekly limit before N4 and USD 1.85 after. The Client key was not used. Three
calls were refused before sending by the standing budgets and cost nothing.

## Open

- **11 older documents titled "Impromptu Zoom Meeting".** Each has scenes or vectors and feeds approved briefs, so a
  person decides their type in the app (Sources, Classify), never a script. With the recording's name, the two Google Ads
  office hours (9 and 15 October) would be `office_hours` and the Matlai consultation (7 October) `prospect`. Every one
  is already `public_use: false`.
- **The collector (6.B1)** moves to N7. When it is switched on, the calls since the last manual import are imported
  first, because the collector never fetches a call older than its activation.
- **A visual check on production** needs a person signed in with the shared account. The screens are the same build,
  and the fixes are deployed (`77235ee`).

## Clean-up

Both TCP proxies were deleted. The local file with production's variables was removed, as was the temporary local
Command Center container.
