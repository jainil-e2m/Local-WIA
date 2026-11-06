# NP.X3: the paid proof of content packs (24 October 2026)

This is the content-packs plan's section 7.3, as the main plan's section 5.0c applies it. The free-model shakedown that
came before it is `np5/shakedown-ledger.md` (NP.X1). The capped live Opus call is `np5/x2a/` (NP.X2a). The reviews,
decisions and readings here were done by the implementing agent under delegation (D12, D39, R55).

## Setup

- **Scratch copy B** (`atelier_np_b`) is production's nightly dump of 24 October 08:16 UTC. NP.X1 never touched it.
  Migration 009 ran on it at 13:54 UTC.
- **The stack** was N1's: the production images with every worker
  (`np5/compose.np5.yml`).
- **Settings:** the settings of record (`backend/deploy/production-settings.json`):
  - the finisher and the repair on `anthropic/claude-opus-5.5`, the check and the re-check on
    `anthropic/claude-sonnet-5.5`, all at medium effort;
  - knowledge base `wia-kb-2026-10-22.c-a1a75795`.
- **Key and caps:** the internal OpenRouter key. The copy's own caps (briefs USD 5.30, packs USD 4.00) are the scratch
  copy's, not production's. The phase's limit was USD 6 on the key.
- **Gate 2:** N2's three briefs went through Gate 2 with `np5/gate2.py` and `np5/gate2-actions.json` (output
  `np5/gate2-copyB.json`):
  - The team's points from `research/n2-delivery-2026-10/readings.md` became edits by the named team account:
    - brief 3's "bigger venue" correction;
    - covers that name their subject;
    - brief 2's untold client reaction.
  - Each client-permission item was answered "Before posting: WIA confirms the client's okay".
  - Brief 2's quotation of Whitney's own words could not be cleared: every October call carries the collector's
    `public_use: false` (NP.X1, finding 3). So the team told it in reported speech in her voice. No permission reference
    was invented.
  - Each approval started its pack.
- **The held-out brief** is card `angle_a3e9ed535b9e4158aa14aa8a3ed0a637`, an October card the finisher prompt was not
  written from: card 4 after its Gate 1 fix.
  - It was developed with writer v5 (run `brief_run_c4c6d28679baf3e1584cfc4c`, USD 1.30). It then went through Gate 2
    with `np5/gate2-heldout.json` (output `np5/gate2-heldout-copyB.json`).
  - Both of its quotations, the owner's question and Whitney's reply, come from a `public_use: false` call, so both were
    told in reported speech. Nothing else in its copy was changed, so its pack shows what the finisher does with the
    writer's copy.

## The packs

| Pack | Profiles | Cost (USD) | Step time | Check | Outcome |
| --- | --- | --- | --- | --- | --- |
| Brief 1 | finish v1, check v1 | 0.69 | 3 min 12 s | 2 of 26 flagged, 2 repaired | In review, no blocker |
| Brief 2 | finish v1, check v1 | 0.47 | 2 min 56 s | 1 of 25 flagged, repaired, put back at finalize | In review, no blocker; one client quote listed as a before-posting note |
| Brief 3 (first) | finish v1, check v1 | 0.51 | 2 min 29 s | 2 of 36 flagged, 2 repaired | In review, but the fidelity reading failed (below) |
| Brief 3 (retry, Finish again) | finish v2, check v2 | 0.66 | 2 min 22 s | 4 of 28 flagged, 4 repaired, 2 survived: 1 put back, 1 open finding | In review; the open finding blocks Ready until attested |
| Held-out brief | finish v2, check v2 | 0.57 | 6 min 4 s (the finisher call 5 min 25 s) | 0 of 40 flagged | In review, no blocker |

Every pack has all five pieces: 1 email, 1 carousel (8 or 9 slides) and 3 Reels. In each, the story and b-roll text
Reels are finished from the brief, and the stance Reel is written by the finisher (none of the four briefs had one).

## The readings (section 7.3)

**Composition and checks: pass.** Every pack has 1 email, 3 Reels of the three kinds and 1 carousel. After finalize, the
only open blocking finding is brief 3's on its written stance Reel. That finding is the R57 path working: it is cleared
by an attestation in the review below.

**Fidelity: pass after the stop rule.**
- **Brief 1:** the check caught and repaired an offer pitch on carousel slide 8 (Instagram keeps no offer) and an email
  commitment the call does not make.
- **Brief 2:** the client's reaction stays in its moment, and the email body (locked whole by the team's Gate 2 edit)
  is kept verbatim.
- **Brief 3's first pack failed the agent's own reading.** Its written stance Reel added an outcome ("had ended up with
  them", a booking claim) and a sequence ("had sometimes looked at first", the order Gate 2 had removed). The check
  passed both.
- **The stop rule** (tighten the prompt as a new profile, retry once):
  - `pack-finish.v2` keeps the supporting example's own order and outcome and adds none.
  - `pack-check.v2` flags an added order or outcome.
  - The carousel's close asks for nothing when the brief keeps Instagram without an offer.
  - The retry (Finish again on brief 3) has neither drift line.
- **The held-out pack** adds one detail, "how they'd use the spaces and how the day would flow". It is Whitney's own
  prompt at 68:45 ("how they're using the spaces, how the event is flowing"), and the finisher still flagged it for her
  in its notes.

**The standard: pass on the agent's reading**, with these points:
- The emails keep the skeleton: opening, story, one bold belief line, the reader's world, the CTA. The subjects state
  the reader's question or WIA's decision.
- The scripts are spoken.
- The captions run problems and desires, then the story, then the reframe, and are signed.
- The carousels are stacked, with slide 1 carrying the promise, a "We believe" slide and a last slide for both readers.
- US spelling throughout.
- Brief 3's pack repeats the team's locked "couples who had looked at a bigger venue had come to them" across several
  pieces. Those lines are person-written, so the finisher left them and raised the repetition in its notes for Whitney.

**Better than the brief: 16 of 16 preferred.** A subagent read Whitney's finished pieces (KB 15, 18, 19) and the house
style (sections 4.1 to 4.6). It then read 16 pairs: briefs 1 and 2 and brief 3's retry, four pieces each, plus four of
the held-out brief's. Each pair was the brief's copy and the pack's copy, shuffled under A and B, with the same "what
happened" sources. The kit is `np5/blind.py`; the key stayed outside the reader's folder.

- **Preferred:** the pack copy in 16 of 16 pairs (the bar is 13).
- **Fidelity:** the same in 11 pairs. The pack was more faithful in 2:
  - brief 1's b-roll screen, where the brief implied the pages were replaced;
  - brief 2's story caption, where the brief widened one exchange into a standing practice.

  The reader judged the pack less faithful in 3:
  - **Pair 2, brief 1's carousel caption:** "We hold every page we build to that standard..." widens one page into a
    protocol. A real break.
  - **Pair 6, brief 2's carousel caption:** it lists an ad's flaws and then says "a client recently had that kind of
    reaction", which suggests the ads were poor, and P5 keeps that out. A real break.
  - **Pair 13, the held-out email's opening:** not a break. The line is Whitney's prompt at 68:45, which is in the
    evidence the finisher reads but not in the brief's own evidence list the kit showed.

- **The written stance Reels:** all 4 pass the standard on their own.
  - **Brief 1's** caption says a planned review happened ("before it went back to them for review"). This is a fidelity
    fix.
  - **Brief 2's** repeats one aphorism.
  - **Brief 3's** caption hook adds a second "X, not Y".
  - **The held-out Reel's** first line says "she's hosting" before any owner is introduced.

**The held-out brief: pass.** Its pack passed every reading above, so the result does not rest only on the briefs the
prompt was written from.

**W3 to W8: pass.** None of Whitney's 20 October patterns recurs:
- no subject that narrates a third party;
- slide 1 always carries the title's promise;
- the covers name their subject;
- no program insider terms on hooks or covers;
- no client line without its subject;
- the b-roll screens say what happened.

**Cost and time: pass on cost, at the limit on time.** Every pack cost at most USD 0.69 (the limit is 0.85). Four packs
took under 3 min 15 s of step time. The held-out pack took 6 min 4 s, because its Opus call ran 5 min 25 s; the limit is
6 minutes. DEPLOYMENT.md's estimate is now "2 to 6 minutes".

## Decisions under delegation (D12)

1. **The finisher stays on (`finish`) for every pack; the two fidelity clauses are edited by the team.**
   - Section 7.3's rule for a pack less faithful than its brief is to ship it in `missing_only`. Here that would discard
     eight pieces the blind reader preferred, to remove one clause in each of two captions.
   - The team's delegated review edits those clauses instead, and brief 1's stance caption line too, through the pack
     screen's own edit path. Each edit is a new version and locks the line as a person's.
   - So no shipped piece is less faithful than its brief. The steps are in `np5/review-production.json`. They were
     applied on copy B (`np5/review-copyB.json`: four new versions, no blocker left) and the same file runs on production.
2. **Brief 3's open finding is attested, not edited.** The sentence ("we stay responsible for the recommendation")
   restates the WIA perspective approved at Gate 2. The check flagged it because the approved perspective is not among
   its sources (see "Open").
3. **Style points stay WIA's.** The reader's suggestions on aphorisms, a second contrast and a pronoun are left for WIA's
   own review of the packs.
4. **Production replays rather than re-makes.** Briefs 1 and 2 and brief 3's first pack replayed on production under the
   v1 profiles they were made with: every piece identical, USD 0. Production then runs v2.

   Brief 3's Finish again could not replay. Its v2 answers were saved under a wire schema that a docstring edit had
   changed (fixed in PR #18), so it ran live on production: USD 0.60, 0 of 27 flagged. The agent read it, and the team
   edited one certainty in its stance caption. `production.md` has the details.

## Defects the proof found, each fixed with a test

| Defect | Fix |
| --- | --- |
| The pack's consent and lint checks read a Reel's beats (direction) as copy, so a beat raised a blocker no edit could clear | Checks judge copy only (`226a6b9`) |
| A written stance Reel added an order and an outcome the sources do not state | `pack-finish.v2`, `pack-check.v2`; v1 stays selectable so packs made under it replay (`870064b`) |
| Putting back a flagged sentence repeated the sentence beside it (the finisher had split the brief's sentence in two) | The brief's paragraph goes back instead (`8681aeb`) |
| Finish again labelled the finisher's own Reel "finished", as if the brief had it | It stays "written", with no brief copy (`3f60001`) |

`np5/proof/shipped.py` applies the last two fixes to the saved brief 3 retry, as production's finalize will. Finalize
makes no model call. The blind reading used that version (`proof/brief-3-v2.shipped.pack.json`).

## Cost

| Item | Key | USD |
| --- | --- | --- |
| NP.X1, the free-model shakedown | Client (free endpoints) | 0 |
| NP.X2a, the capped Opus call | Internal | 0.03 |
| The held-out brief (writer v5: research, write, verify, repair) | Internal | 1.30 |
| The five pack runs above | Internal | 2.90 |
| Production (NP-6): brief 3's Finish again live; 12 calls replayed at USD 0 | Internal | 0.60 |
| **Phase total** | Internal | **4.83** of the USD 6 limit |

The blind reading and every reading here were done by the agent and its subagent, with no paid judge.

## Open (NP-7)

- **The check's sources.** The approved brief's WIA perspective belongs among the check's sources, so a stance line the
  team approved is not flagged (as `pack-check.v3`).
- **Labelled cases (NP.X5).** The two clauses the check missed (pairs 2 and 6) become labelled cases for it.
- **The blind kit** should show the hand-off's whole evidence, not the brief's list, so the reader sees what the
  finisher saw.
- **Finisher time.** A finisher call of over five minutes was seen once; NP-7's first live weeks watch it against the
  six-minute line.

## Files

- `np5/gate2-actions.json`, `np5/gate2-heldout.json`: Gate 2 as applied. Outputs: `np5/gate2-copyB.json`,
  `np5/gate2-heldout-copyB.json`.
- `np5/proof/`:
  - `brief-N.brief.json`, `brief-N.pack.json`, `brief-3-v2.pack.json` (the retry as made) and
    `brief-3-v2.shipped.pack.json` (as finalized now);
  - `held-out.brief.json`, `held-out.pack.json`;
  - the reading files `*.read.txt` (from `readpack.py`);
  - `proof.json`, the blind kit's index;
  - `week-2026-10-12-packs.md`.
- `np5/blind.py`: the blind kit.
- `np5/review.py`, `np5/review-production.json`, `np5/review-copyB.json`: the delegated review.
