# N5 with NP-7: the system made ready for the WIA team (25 to 26 October 2026)

This records Phase N5's system side and the content-packs plan's NP-7, done unattended on the owner's instruction. The
reviews and readings here were made by the implementing agent under delegation (D12, D39, R55). Times are UTC. WIA's own
use of the system (their decisions, ratings, requests and sign-off) and what the owner tells WIA are out of scope.

**Run authority (the owner).** Production go-ahead for merging, deployments, `settings apply` of profiles whose reading
passed, the standing caps and the classification of the "Impromptu Zoom Meeting" documents; self-merge after CI; the
OpenRouter limit is what both keys had left (Client USD 7.64, internal USD 1.85 until Monday's renewal). No Railway billing
change. The agent sets no password (X.1 waits on the owner).

## What was built

| Item | What | Commits |
| --- | --- | --- |
| NP.B14 | The post-recording pass: "Paste what you said" on a face-to-camera Reel. The take becomes its script word for word, locked as the person's; `pack_caption.v1` (Opus 5.5) writes the caption and three covers from it; the check reads only what it wrote, with the take among its sources; a surviving flag stays an open finding | `5986284`, `2fd266b`, `737e060`, `7d64cc2` |
| NP.B15 | Finishing again with a permission: an approver grants a "stronger with permission" item or states a fact; `pack_refinish.v1` re-finishes with each as attested evidence (R57), every lock kept; grants stay on the pack for later runs | `5986284`, `2fd266b`, `7d64cc2` |
| `pack-check.v3`, NP.X5 | The approved brief's WIA perspective and central point among the check's sources; one moment widened into a practice is unsupported; a guardrail breaks by placement too. The proof's two missed clauses are the first labelled cases (`research/packs-2026-10/check-cases.json`); `packs/check_cases.py` scores a check against them and lists a week's person-made pack edits as candidate cases | `521367e`, `072ef6d` |
| NP.B10 | Brief writer v5.1: three Reels (story, stance, b-roll text) when Instagram is a channel; v5's request pinned byte for byte, so N2's briefs still replay at USD 0 | `e8efa9c`, `82114ce` (subagent), `7ad3242` |
| NP.B12 | The week's pack document as .docx (`GET /weeks/{id}/packs.docx`, `storage_cli pack-document --format docx`, a link in the week view) | `d596cf2` (subagent) |
| E.X9 | WIA rates briefs at Gate 2 on rubric 2.3a (cards were rated already); the label is WIA's only for a reviewer on `ATELIER_WIA_REVIEWERS` | `c9f9236` |
| 7.X2 | `storage_cli week-measures --week <id>`: section 4.5's and the packs plan's 4.6 measures for a week, WIA's rows apart from delegated ones | `4b9b392` (subagent) |
| X.2, NP.X4 | The tone loop end to end: a tone request and a correction given twice reach one compiled version, made active by the named reading, which the version keeps (`test_x2_tone_loop_db.py`); the runbook and the caps for a week of use in DEPLOYMENT.md | `4fa13c0` |

## Defects found and fixed (each with a test that fails without the fix)

1. **A recorded take was not a source on later runs** (`737e060`, copy A): a permission re-finish after a take flagged the
   caption's restatement of what Whitney said. The take is kept on the pack (`recorded_takes`) and given to every check.
2. **A repair that cut a whole list line left an empty string** (`7ed2376`, copy A): the pack failed at finalize and could
   not move. A cut cover alternate, screen or subject option is removed; finalize drops an empty line left by an older run,
   so its retry finishes (it did, on copy A).
3. **Research failed on every retry when a grading answer missed items** (`246667f`, copy B, paid): a 52-grade answer
   covered the pool unevenly, and the retry replayed the same saved answer. Grades for undelivered or repeated items are
   dropped and recorded, and the missed items are graded in a follow-up call; the coverage check is unchanged. The retried
   brief then finished.

Not a defect: the free models broke the research step's own query-plan contract twice on copy A (K70); the pipeline path
after it is covered by the database tests and was proved on paid models on copy B.

## The free-model shakedown (copy A, `atelier_np_a`; free models on the Client key, USD 0)

Copy A and copy B are production's latest nightly dump (24 October 08:16; the next is 25 October 08:15), run in the
production images with every worker (`research/packs-2026-10/np5/compose.np5.yml`), with `pack-check.v3` set.

| Run | Result |
| --- | --- |
| Post-recording pass on brief 1's pack (`pack_3d1c62b4…`) | Every step completed; the take is the script word for word and locked; covers and caption rewritten; 0 of 12 flagged |
| Permission re-finish (`pack_224f3b8b…`) | Completed; the grant used; the caption's restatement of the take flagged: **defect 1** |
| A second take after the fix (`pack_bd173a2b…`) | Finalize failed on two emptied cover alternates: **defect 2**; after the fix, a retry of the failed step finished it |
| Permission re-finish again (`pack_f3a51c77…`) | Completed; both grants and the take kept on the pack |
| Writer v5.1 on card 3 | Research failed twice on the free model's query plan (free-model artefact) |

The failure cases (a credit refusal, a spent packs budget and its release) are database tests with the fake provider
(`test_np7_passes_db.py`); a killed worker is the NP exit test's, on the same run path.

## The paid proofs (copy B, `atelier_np_b`; models of record; the Client key)

**`pack-check.v3` on the labelled cases** (`check_v3.py`, the check stage's exact request under v3, a capped run plan):

| Pack | Statements | Flagged |
| --- | --- | --- |
| Brief 1 (the proof's) | 22 | 2: **case np5-pair-02** (one page widened into a practice) and the email's line tying the story to a named program |
| Brief 2 | 28 | 1: **case np5-pair-06** (the placement that implies the kept-out judgement) |
| Brief 3 (v2 retry) | 44 | 0, with 13 statements credited to the approved perspective |
| Held-out brief | 25 | 1: the carousel close's promise of "real interest" (arguable) |

Both labelled cases caught; 22 statements credited to the approved perspective, none of them flagged. USD 0.29.
**Reading: pass** (the check is a net, K76). `production-settings.json` names `2026-10-26.pack-check.v3`.

**The post-recording pass** on brief 1's pack, with a passage of Whitney's own words from the call as the take
(`take-brief-1.txt`, a stand-in until she records one): `pack_07bcb847…`. The script is the take, word for word, locked;
the caption keeps her planned tense ("I'll send it back over"); the covers name their subject; 0 of 12 flagged; no blocker.
One soft spot: the caption adds a motive the take does not state outright. USD 0.27. **Reading: pass.**

**Finishing again with a permission** (the probe's brief 1 case, the comparison result), a stand-in grant marked as such
and never used on production: `pack_27967466…`. The granted result appears in the email, the caption, Reel 2, Reel 3 and a
new carousel slide, as the grant states it; the take and every locked line are unchanged; S1 left "stronger with
permission"; 0 of 31 flagged. It also rewrote two carousel slides it did not need to. USD 0.62. **Reading: pass.**

**Writer v5.1** on October card 3 (the one card never developed): `brief_ea7c31c5…`, ready for Gate 2 with story, stance
and b-roll text Reels; its only blockers are Gate 2's own steps. A blind reading by a subagent (`proof/v51/blind/`, the
key outside the reader's folder) against N2's v5 brief 1: v5.1 meets the three-kind rule with the stance on the same
point and is narrowly preferred against the full standard; its captions lack "-Whitney", its stance opening is abstract
and wording repeats across the Reels, all the finisher's job; v5's individual Reels read stronger. USD 1.02, the two
failed research attempts included. **Reading: pass, with those notes.** `production-settings.json` names `v5.1`; v5 is
the switch-back.

## The screens (local copy, signed in through Command Center's development mode)

The pack detail on copy B at 1024 px and at a 375 px phone width: "Paste what you said" on Reels 1 and 2 only (not the
b-roll Reel), its form and words; "Stronger with permission" with a Grant control per item, the fact box and the Granted
list. No horizontal scroll at phone width. Gate 2's rubric form for briefs and the .docx link are unit-tested.

**The .docx** opened in LibreOffice Writer (rendered to PDF); Word is not installed here and Google Docs would mean
uploading client text, so those two opens are still a manual check.

## Production

| Step | Result |
| --- | --- |
| Fresh dump | `backup dump` through a temporary proxy: 52.5 MB, 41 tables, 13,302 rows, migration 009, 25 October 01:06 |
| The "Impromptu Zoom Meeting" documents | 13 carry the title. Through the app's classify route as the team (delegated), with the recording's name: the Matlai consultation (7 October) is `prospect`, the Google Ads office hours of 9 and 15 October `office_hours`; all three stay included. The other ten were already right: six internal weekly meetings, four client calls. No approved brief or pack cites any of them (three pending briefs cite the 15 October office hours) (`classify/`, `impromptu-before.txt`) |
| Calls since the last import | None: the two recordings since 23 October are already documents |
| The week's cycle | Window 20 to 26 October (the three calls of 21 to 23 October), started through the API as the app starts it, after its preview (USD 0.62 estimated): `run_3e432949…`, three ranked cards for Gate 1 in `week_2026-10-20`. USD 0.39 |
| Standing caps | cycle 1.20, briefs 4.00, refreshes 1.50, embedding 0.10, extraction 0.40, context mining 0.10, packs 6.00: USD 13.30 a week, under the key's 15. This week's cycle cap was raised to 1.50 for the run, then set back. The reset after the first live week is in DEPLOYMENT.md |
| Merge, deployments, `settings apply` | PR #24 merged after all five CI jobs passed (`0b3e587`); the newest deployment of each of the seven services (`api` first, then `scheduler`, `editorial-worker`, `bulk-worker`, `intake-worker`, `db-backup`, Frontend) built `0b3e587` and was approved; all seven `SUCCESS`, the API's health check 200. `settings apply` of `production-settings.json` as the team account: `pack-check.v3`, writer `v5.1`, `pack-caption.v1` and `pack-refinish.v1` read back. On production the pack detail carries its grants and the team's edit and grant controls, and the week's .docx downloads (72 KB) |

## Cost

| Key | USD | What |
| --- | --- | --- |
| Client | 2.20 | `pack-check.v3` on the cases 0.29; the post-recording pass 0.27; the permission re-finish 0.62; writer v5.1's brief 1.02 |
| Internal | 0.39 | Production's cycle for 20 to 26 October |

The free-model shakedown cost USD 0.

## Clean-up

Both temporary TCP proxies (postgres, api) were deleted, as were the local files with production's variables and the
temporary development Command Center container. The scratch copies keep their stack.

## Waiting on the owner

- **X.1, personal accounts** for Whitney and Gisselle: the agent sets no password. Until they exist, WIA's decisions on the
  shared account carry the delegated label and do not count toward section 4.5 (E.X9, 7.X2).

## Not done by design

WIA's own decisions, ratings, tone requests, recorded takes and sign-off (E.X9's rows, 7.X2's two weeks), and what the
owner tells WIA (D26).
