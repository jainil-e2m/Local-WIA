# Content Atelier: Implementation Plan for Content Packs (Phase NP)

**Date:** 24 October 2026 · **Revision:** 1.2 (Phase NP done: NP-1 to NP-6 built, proved and live on production, 24 October; the status blocks in section 6); 1.1 (the independent review applied, Appendix D; revised at the owner's direction on 24 October: client permission is never a system gate, all three N2 briefs go through Gate 2, and the plan gives order and dependencies, never days) · **Status:** Phase NP done: NP-0 to NP-6 live on production (24 October), and NP-7 built, proved and live (26 October; the status under NP-7, `research/n5-2026-10/README.md`). **D43 decided by the owner on 24 October:** the composition, then D43b to D43j as section 9 recommends (recorded in the main plan's section 7.2). NP-0 is done. · **Basis:** `main` at `3848f03` (the code survey was made at `03a3c98`; the difference is documentation only). The main plan (`Content-Atelier-Implementation-Plan-Brief-Generation.md`, revision 8.7) keeps the phase list and points here for NP's detail. · **Evidence:** `research/packs-2026-10/` (the 20 October transcript, the ChatGPT-export pack study, the repository survey, the planning probe).

**Direction (the owner, 24 October).**
- **Packs before N4.** Content packs are built and live on production before N4 (the Fathom collector and 7.X1) starts.
- **The composition is fixed:** every pack is **1 email, 1 carousel and 3 Reels**.
- **No fumbles.** Packs must reach WIA's standard consistently, and the brief stage may change where packs need it.
- **Unchanged:**
  - 27 October is the delivery date.
  - Phase names stay.
  - Free models come first for every new model-backed step.
  - There is no paid judge.
  - There is no Railway billing change.
  - At most two subagents run at a time.

---

## Read this first

**What a content pack is.** A content pack is the publish-ready set WIA posts from for one approved idea: **one email, three Reels (story, stance, b-roll text) and one carousel**, each Reel and the carousel with its caption. Every line is in Whitney's voice and checked against the call.

In the pack, Whitney can:
- copy each piece;
- edit any line, which is then kept word for word;
- clear what needs clearing;
- mark the pack ready, and later mark each piece published.

A week view proposes which pieces go out that week, and the week's document exports for review.

**Where it sits in the flow WIA saw on 20 October.** Whitney approves the angle (Gate 1), reads the brief (Gate 2), and approving the brief creates the content pack. On that call she was promised three things:
- feedback-driven refresh exists up to the brief;
- in the pack she edits by hand, and her text is kept word for word;
- the week reaches her as a document she can comment on.

Source: `research/packs-2026-10/20-october-call-transcript.md`, 7:54 to 8:31 and 16:58.

**Why a pack is more than the brief's copy.** Brief contract v4 already writes every asset. But N2's three briefs read well below the v2 packs WIA saw:
- abstract, repeated wording ("scrutiny", "contribution");
- carousel slides written as paragraphs;
- captions that skip the reader's world;
- generic covers;
- British spelling;
- stories that never tell the moment.

All three briefs also have only two Reels. A pack stage that only copied the brief would hand WIA that copy. The planning probe showed that a **finishing step after Gate 2**, with a fidelity loop around it, fixes most of it (section 3.4, `research/packs-2026-10/README.md`).

**The trade-off the design makes (D43b).**
- **Gate 2 approves** the brief's strategy and every line a person wrote there.
- **The rest of the copy becomes a draft** that the pack finishes, and Gate 2 labels it a draft.
- **No model ever changes a line a person wrote,** at Gate 2 or in the pack.

The alternative is finishing before Gate 2, so Gate 2 approves final copy. It costs more and departs from the flow WIA was shown (section 5.10).

**The design in short.** When Gate 2 approves a v4 brief, a pack job starts by itself under a new `packs` weekly budget. It has six stages:
1. **Assemble (no model).** It reads only the brief's hand-off view, extended to version 2 (strategy, call date, claim fields, locks), never the contract-specific document (R56). It keeps each piece in the v4 leaf shape, so locks, checks, comparing and reverting all work line by line.
2. **Finish (Opus 5.5).** It edits each piece to WIA's house style, writes any missing Reel kind, and adds no fact the brief and the call do not hold.
3. **Check (Sonnet 5.5).** It lists every factual statement as supported, unsupported or guardrail. It skips lines a person wrote and Whitney's flagged personal lines.
4. **Repair (Opus 5.5).** It patches only the flagged sentences.
5. **Re-check.**
6. **Finalize (no model).** It:
   - puts locked lines back;
   - runs the deterministic checks: first touch, insider terms, consent and names, exact quotes, no new numbers or names, composition and format;
   - puts the brief's sentence back wherever a flag survives in a piece the brief had;
   - opens the pack for review.

A finding left on a Reel the finisher wrote stays open until a person edits that sentence or attests it is true (R57).

A job takes about 4 to 6 minutes and costs USD 0.55 to 0.85 at medium effort. The week view and the export are deterministic.

**The plan in one table.**

| Step | Delivers | Exit (checkable) | Needs |
| --- | --- | --- | --- |
| **NP-0** Decide (**done 24 October**) | D43b to D43j confirmed (section 9); the budget; the route of N2's briefs to Gate 2 | Decisions recorded in the main plan's section 7.2 | — |
| **NP-1** Pack foundation | Migration 009; hand-off view v2; the v2 pack contract in the v4 leaf shape; assembly; start on Gate 2 approval; versions, edits, locks and states; deterministic pack checks; the `packs` budget, settings and model plumbing; the API | An approved v4 brief gets a pack of 1 email, 3 Reels and 1 carousel with no model call (finishing off), in a database test, and Gate 2 locks survive | NP-0 |
| **NP-2** The finisher and its fidelity loop | `pack-finish.v1`, `pack-check.v1`, `pack-repair.v1`, the re-check, finalize with sentence-level put-back and attestation, replay and pinning | Offline tests with recorded responses: three Reels from a two-Reel brief; locks kept through finishing and repair; a flagged sentence repaired or put back; a written-Reel finding cleared by attestation; replay at USD 0 | NP-1's contract |
| **NP-3** The pack screen | The pack view WIA saw on 20 October, on real data (tabs, Copy, Copy all); edit any line; what the finisher changed; use the brief's line; attest; ready and published; Gate 2 hands over to the pack | Frontend tests; the flow works in the stack | NP-1's frozen contract |
| **NP-4** Week plan, export, learning | The week's allocation (one Tuesday email, three Instagram pieces, one offer post) and the bank; the week's pack document; pack edits feeding learning | Database tests; the export renders the proof's packs unabbreviated | NP-1 |
| **NP-5** Prove it | The free-model shakedown of the pack path; the NP exit test; one capped live Opus call through the pipeline; the paid proof on N2's three briefs and one held-out brief, on a fresh scratch copy, with readings | Section 7's readings pass; the exit test and CI green | NP-1 to NP-4 |
| **NP-6** Production | Deployed and migrated; settings, budget, variables; N2's three briefs through Gate 2 under delegation (D43g), client permissions as before-publishing notes; their packs replayed from the proof (or made live); read | Packs live on production and recorded; then N4 starts | NP-5; the owner's go-ahead (D13) |
| **NP-7** First live weeks | The post-recording pass (caption and cover from what Whitney actually said); finishing again with a permission; writer v5.1 (three Reels in the brief) with its reading; Whitney's pack edits into the tone loop | Per item | NP-6 |

**What the owner decided** (section 9, 24 October): D43a, then D43b to D43j as recommended. Three of them change cost or what WIA sees:
- **D43b:** the finisher and its trade-off.
- **D43f:** the `packs` budget, USD 6.00 for the week of 26 October and then USD 3.50 a week.
- **D43g** (revised at the owner's direction): the team takes N2's three briefs through Gate 2 under delegation, so their packs exist at delivery and in the Loom. A client's permission to tell their story is a before-publishing note for whoever posts, never a gate.

---

## 0. How to use this document

| Section | Contents |
| --- | --- |
| Read this first | What a pack is, the trade-off, the design, the plan in one table |
| 1 | Sources and how this plan was verified |
| 2 | What WIA asked for and was promised: the requirements, each with its source |
| 3 | Where the system stands for packs today: code, output quality, the probe |
| 4 | The target: the pack, its standard, the week, what a pack never does, success measures |
| 5 | The design: flow, hand-off view v2, data, the finisher, the fidelity loop, the API, the screens, budget and model plumbing, learning, alternatives |
| 6 | The steps NP-0 to NP-7: every item with its "done when", and each step's exit |
| 7 | Verification: free models first, the exit test, the capped live call, the paid proof and its readings |
| 8 | The schedule to 27 October, the cut list and the fallbacks |
| 9 | Decisions |
| 10 | Risks |
| 11 | Definition of done for Phase NP |
| Appendices | A: requirement-to-item trace. B: settings and production values. C: changes to the main plan and the prompts. D: the independent review and what changed |

**Item IDs.** `NP.B` backend, `NP.F` frontend, `NP.X` cross-system or run work, following the main plan's section 0. They replace the old pack item 5.B13. Priorities are the main plan's: P0 for go-live, P1 for complete and reliable, P2 for hardening.

**Working an item.** Follow the main plan's section 0, "Working an item (developer conventions)":
- a branch named `item/<IDs>-<name>`;
- new prompt profiles as new files (E.B17);
- migrations as new numbered files;
- new routes on the Node allowlist, each with a server test;
- tests for every "done when";
- **synthetic fixtures only in tests** (R48: real call text stays under `research/`);
- paid calls only under the standing budget;
- a pull request titled with the IDs.

---

## 1. Sources and how this plan was verified

| Source | What it gave | Where |
| --- | --- | --- |
| The 20 October call, full transcript | The flow WIA saw; what was promised about editing and refresh; Whitney's notes W1 to W13 | `research/packs-2026-10/20-october-call-transcript.md`; main plan section 3 |
| The 13 October call, full transcript | Not how-to; zoom out; subject and slide 1; scripts casual; carousel copy only for Canva; three angles a week; a bank; repetition after one to two months; emoji at most once or twice a month | `research/week2-packs-rebuild-2026-10-21/feedback-13-october/` |
| The v2 packs (hand-built, shown 20 October) | The target pack piece by piece, and its "before you publish" and suggested-week sections | `research/v2-reassessment-2026-10-20/packs/` |
| The diagnosis and the v2 findings | Why packs missed (the point, the moment, format bloat, kickers); the house style by format (section 14.9) | `research/v2-reassessment-2026-10-20/`, `research/week2-packs-rebuild-2026-10-21/Content-Atelier-Findings-and-System-Improvements.md` |
| WIA's ChatGPT export, read for packs | What a week was in WIA's own workflow; the gaps against contract v4; requirements R1 to R20 | `research/packs-2026-10/sources/chatgpt-export-pack-workflow.md` |
| The knowledge base | Cadence (KB 14, rulings R-10 and R-11), formats (KB 09), workflow (KB 08), edits (KB 17), voice and exemplars (KB 02, 15, 18, 19) | `backend/knowledge_base/` |
| The repository at `03a3c98` | The old `packs/` module, the hand-off view, contract v4, checks, Gate 2, budgets, the calendar, the frontend, capture, tests | `research/packs-2026-10/sources/repository-survey.md` |
| N2's briefs and readings | Today's output quality and costs; the team's Gate 2 points for Whitney | `research/n2-delivery-2026-10/` |
| The planning probe (24 October, USD 3.82) | A finishing step works on Opus 5.5; drift is real and varies by run; the repair loop converges; costs and times | `research/packs-2026-10/README.md` and `probe/` |
| An independent adversarial review of this plan's draft (24 October) | 6 blocking, 22 important and 15 minor findings, all applied (Appendix D) | The planning session's record |

Every code reference below was read in the survey or the review, with its file and line.

The probe's readings are the planning session's own (D39, R55), one sample per configuration. They are evidence for the design. NP-5 is the gate.

---

## 2. What WIA asked for and was promised

| # | Requirement | Source | What it means for the pack |
| --- | --- | --- | --- |
| RQ1 | Approve the angle, read the brief, **generate the content pack**, then review the final content: "the key element... is the brief... and then the final content" | 20 Oct, 2:00 to 7:54 | Approving a brief creates its pack; the pack is where the final copy is reviewed |
| RQ2 | An email, a carousel and three Reels (story face to camera, stance face to camera, b-roll text), each Reel with cover, on-screen hook, script or screens and caption | 20 Oct, 9:00 to 10:20; v2 packs; **the owner, 24 Oct** | Fixed composition (D43a) |
| RQ3 | A **copy button** per piece | 20 Oct, about 6:30; the mock's Copy and Copy all | Copy per piece, per field and for the whole pack |
| RQ4 | **Overwrite anything** in the pack, available "next week"; pack edits kept word for word; feedback refresh stops at the brief | 20 Oct, 7:54 to 8:31 | Edit any line from go-live; a person's line is locked; no feedback refresh in the pack (D43d) |
| RQ5 | The week reaches her **in a document format** to comment on | 20 Oct, 16:58; 13 Oct, 11:36 | The week's pack document (NP.B12) |
| RQ6 | Carousels as **copy only**; Gisselle pastes them into Canva; no font or design direction "for now" | 13 Oct, 23:23 to 24:21; the export | Slide text only, ready to paste |
| RQ7 | **Three strong angles a week**, fewer when calls are thin, and a bank to reach back to | 13 Oct, 26:42 to 28:15 | Up to three packs a week; ready pieces not yet planned form the bank |
| RQ8 | Repeating a point after **one or two months** is fine | 13 Oct, 28:53 to 29:21 | The week plan respects the repeat window (D23) |
| RQ9 | **Emoji in a subject at most once or twice a month** | 13 Oct, 13:28 | A week check (warning) |
| RQ10 | CTAs vary (reply, sales page, DM); email, Reels and carousel share a common CTA idea | 13 Oct, 5:25 to 7:14, 16:28 to 16:39 | The brief's CTA decision is kept; the week plan names the week's one offer post |
| RQ11 | Email with more personality; scripts casual and less polished; punchier hooks | 13 Oct, 16:17, 19:37 | The finisher's register by format |
| RQ12 | Not how-to or DIY: reflect the conversation; a specific example, a zoomed-out lesson | 13 Oct, 3:29 to 4:36, 8:57 to 11:06 | Kept from the card and brief; DIY drift checked again |
| RQ13 | First touch: specific covers, slide 1 carries the promise, no third-party subject narration, no insider terms, who did what | 20 Oct, W2 to W8 | E.B34's checks run on the pack |
| RQ14 | Posting on **Instagram and Facebook** (the same pieces) | 13 Oct, 26:42; the export | No separate Facebook copy |
| RQ15 | A **change-request tracker** for tone | 20 Oct, 2:00 | X.2; pack edits feed it (NP.B13, NP.X4) |
| RQ16 | **Live calls next week**, with angles, briefs and packs to go through; a Loom before 27 October | 20 Oct, 16:58, 19:19 | Packs live before N4 and the Loom; the go-live week's budget covers WIA's packs (D43f) |
| RQ17 | WIA's week: **one Tuesday email, three Instagram pieces (two without an offer CTA, one with)**; order graphic, Reel, carousel; covers as a set | KB 14, R-10, R-11; KB 09; the export | The week plan (NP.B11) |
| RQ18 | Captions and covers for recorded Reels are written **after recording, from what she said** | The export, July to October 2026 (very high centrality) | The post-recording pass (NP.B14, first live week) |
| RQ19 | Each later piece derives from the approved anchor piece, not afresh | The export ("too many liberties") | The finisher edits from the brief's copy, anchor first |
| RQ20 | The places she always rewrote: the email subject, carousel slide 1, the Reel hook, covers, any line carrying a fact | The export, raw-to-final chains | The finisher's effort and the screen's first fields go there; cover alternates; three subject options |
| RQ21 | One consolidated, unabbreviated document for the week, nothing "as before" | The export, March 2026 | The export renders every piece in full |

**Out of the weekly pack.** From the same sources, these stay out:
- Stories, Threads and TikTok;
- LinkedIn and blogs;
- graphics and audio;
- Story Highlight funnels, landing pages and launch sequences;
- ad and trial variants;
- a cut sheet for WIA's own footage. Our sources are client calls, which are never posted as clips.

Each can return if WIA asks.

---

## 3. Where the system stands for packs today (verified 24 October)

### 3.1 Code

| Part | State | Verdict |
| --- | --- | --- |
| The hand-off view (`briefs/handoff.py`, `GET /storage/briefs/{id}/handoff`, `brief_handoff_v1`) | Version-independent pieces with positional keys (`reel_1..n`, `carousel`, `email`); copy and direction split; anchor, message spine, claims, before-publishing items, evidence with consent, `can_consume`. **It lacks** the supporting example, narrative outline, strategic purpose, intended shift, CTA reason, the call date, each claim's `field`, and the locks (`handoff.py:209, 304-341`) | **Extend to `brief_handoff_v2`** (NP.B1). The pack reads only v2 (R56) |
| The old `packs/` module | Reads v1 fields only. Refuses v2 to v4 by name (`packs/workflow.py:35-39`). Requires five fixed slots (`contracts.py:9`). Rewrites every asset with a generic prompt. Freezes `max_tokens`. Allows 8 chat calls per run (`runtime.py:79-83`). Counts the whole request against 120,000 characters (`runtime.py:94-95`) | **Replace** the contracts, queue, execute and prompts. **Reuse** the service's manifest, lock, decision and audit pattern, with NP.B3's and NP.B9's fixes |
| Tables `content_packs`, `content_assets`, `mutation_receipts` (migrations 001, 004) | `content_assets` has generic columns, with unique indexes `(pack_id, slot_key)` and `(pack_id, ordinal)`. Approval is bound to the manifest hash (`pack_approval_is_bound`). **`content_packs` has no body or content-hash column, and `decisions.item_kind` has no pack kind** (`008_moments_ledger.sql:173-174`) | **Reuse, plus migration 009** (NP.B1): `content_packs.content_body`, `content_hash`; `decisions.item_kind` gains `pack` |
| Gate 2 approval (`gate_two.decide`, l.421-437) | Queues nothing ("no production jobs queued") | **Add** the start in the approval's transaction (Gate 1's savepoint pattern, `gate_one.py:385-388`) |
| Checks (`first_touch.py`; `asset_checks.py` with the week checks; `validation_v2.public_copy_checks` and `copy_quote_checks`; `validation_v4.checks_v4`) | Deterministic, over a **v4 body**; they already run at Gate 2 | **Reuse on a pack body kept in the v4 leaf shape** |
| Rendering (`render_v4.asset_lines`, `review_document.py`) | The week's review document in the "# Pack N" layout WIA reviewed | **Reuse** for the export |
| Standing budgets (`llm/standing.py`) | Six purposes, none for packs (l.27-30). A week's plan freezes its stage list when created (l.100-117). A stage outside it **fails** rather than waits (`run_plans.py:113-114`, `sql_pipeline.py:89-97`) | **Add** a `packs` purpose, with every pack stage NP and NP-7 will use registered now |
| Model plumbing (`llm/request.py`, `costs.py`, `config.py`, `settings_store.py`) | **Opus 5.5 is not configured.**<br>• It is missing from `NO_TEMPERATURE` (`request.py:14`), so requests send `temperature: 0.2` with `require_parameters` and do not ask for usage. Cost would settle at 0 (`run_plans.py:56-61`).<br>• It is missing from the price table (`costs.py:16-20`), so there is no worst case and no estimate.<br>• New stage names fall back to `high` effort (`config.py:127-130`, `settings_store.py:160-169, 214`) | **Wire it in** (NP.B5), and prove it with one capped live call (NP.X2a) |
| Frontend | The real app has v1 pack screens behind `flags.packs` (`StoredPacks.tsx`: list, detail, "Approve exact pack", schedule picker). `SQLBriefs.packMapped` refuses non-v1 briefs. The layout WIA saw exists only in `frontend/src/mock/` | **Build** the v2 pack list and detail by porting the mock's layout onto real data |
| Learning capture (`knowledge/capture.py`) | `source_ref = capture:<brief_id>:<channel>:<piece>` (l.51), using the brief's numbering. `brief_copy` misses v4 screens, captions and the carousel title (l.59-100) | **Add** pack captures with their own reference (NP.B3) |
| Calendar (`calendar/`) | Schedules exact pack assets. It is off, bound to the v1 slot check, and has no publishing integration | **Later**, only if WIA wants dates in the app |
| Node allowlist | Has the v1 pack routes; no `PATCH packs/...` | **Add** the new routes |

### 3.2 Output quality: the copy a pack would start from

These scores come from the second blind reading of N2 (`research/n2-delivery-2026-10/blind-reading-2/reader.md`), each out of 5.

| Brief | First touch | Fidelity | Voice | Structure | Publishable | What holds it back |
| --- | --- | --- | --- | --- | --- | --- |
| 3, competing venues | 4 | 5 | 4 | 5 | 4 | Generic covers ("needed context"); mildly aphoristic closes; the "nearby... before considering theirs" paraphrase (a Gate 2 point) |
| 1, comparing WIA's landing page | 4 | 5 | 3 | 5 | 4 | Abstract principle-speak in captions; dense paragraph slides; the story's turn kept out by a guardrail |
| 2, a client who doesn't love a new ad | 4 | 3 | 3 | 3 | 3 | The story is gutted (it never tells what the client said); Reel 1 tells no story; no offer and no reply CTA |

All three briefs have **two Reels**: the stance Reel was dropped under D30, which the owner has now superseded. The rendered briefs title each Reel with its creative direction, and the writer uses British spelling.

### 3.3 What WIA's own workflow adds

The ChatGPT-export study confirms that contract v4 already carries almost everything WIA published from July to October 2026. The real gaps are in process and at the level of the week:
1. **The post-recording pass.** Captions and covers were written from the recorded transcript.
2. **Week-level allocation.** One email a week, three Instagram pieces and one offer CTA. With three packs a week, the extra emails wait for later weeks.
3. **One consolidated week document.**
4. **Cover sets with options.**

Stories and Threads stopped after June 2026, and TikTok was dropped by R-10.

### 3.4 The planning probe (24 October; record in `research/packs-2026-10/README.md`)

| Finding | Evidence | Consequence |
| --- | --- | --- |
| **Opus 5.5 in edit mode lifts every brief.** It brings spoken register, the client's or Whitney's own words, captions that open in the reader's world, stacked short slides, specific first touches and US spelling | Briefs 1 to 3, at USD 0.35 to 0.55 and 95 to 203 seconds each, at medium effort | The finisher runs on Opus 5.5, in edit mode, at medium effort (NP.B7) |
| Sonnet 5.5 gains little, and writing fresh gains nothing over editing | Sonnet runs, USD 0.10 to 0.13 | Sonnet is the cheaper switch-back, a stated quality trade-off |
| **A missing stance Reel can be written** that keeps the same point and is not a sub-lesson | Round 2 on briefs 1, 2 and 3 | The pack guarantees three Reels; the brief writer follows in NP-7 |
| **Drift is real and varies by run.** Seen: invented reflections and dialogue, "explained" turned into "agreed", a quote moved to another moment, a price hint, widened commitments, a hedge stated as certain | Brief 3: 4 issues in round 1, 12 in round 2 | Check, repair and re-check every time; deterministic checks; a person's review |
| **A model check alone is noisy.** The same pack gave 3 flags, then 9 | Brief 3's check runs | Version 2's sources and rules; skip person-written and personal lines; treat it as a net, not a gate; findings can be cleared by an edit or an attestation |
| **The repair converges.** 13 patches applied; the re-check found 33 supported and 0 flagged | Brief 3, round 2, USD 0.20 | One repair and one re-check |
| The repair can flatten a line or shorten a caption below 150 words | The repaired brief 3 | Format checks after the repair, shown at review |
| The finisher cannot fix a paraphrase that the brief's claims hold, nor add a detail a guardrail keeps out | Brief 3's "before considering theirs"; brief 1's comparison result | Gate 2 edits come first and are kept; "stronger with permission" goes to Whitney |
| The probe's finisher prompt was written while reading these three briefs | `probe/pack_probe_v2.py` names brief 1's words and kicker | NP.X3 adds a held-out brief (section 7.3) |

---

## 4. The target

### 4.1 The pack and its lifecycle

| State | Meaning | Set by |
| --- | --- | --- |
| `finishing` | Jobs running (assemble, finish, check, repair, re-check, finalize); **derived** from the pack run's jobs | The system, on Gate 2 approval or "Create content pack" |
| `waiting` | A job waits on the budget, or a step failed and can be retried, with the reason in words; derived from the jobs | The system |
| `in_review` | Finished and checked; Whitney reads, copies and edits. Derived when no run is active and `approval_status` is `pending` | The system |
| `ready_to_publish` | A named person marked it ready (`approval_status = approved`, bound to the manifest hash). Requires no open blocking finding. Client-permission items and client quotes are listed on the pack and in the export as before-publishing notes for whoever posts the piece; they never block Ready.<br>An edit makes a new pack version, which starts in review | A person |
| Each piece: `published` | Someone marks it with its date, channel and final text. The mark is recorded through capture (`published_content`, with its own reference), **outside the pack's copy**, so it never changes the manifest or the pack's readiness. The final text feeds the published register and the learning loop | A person |

### 4.2 Contents and order (the v2 pack contract, in the v4 leaf shape)

Each piece keeps **v4's leaf names**, with the pack's extra fields beside them. This means:
- Gate 2 locks translate by a fixed table, where only the Reel index changes;
- the existing checks run unchanged;
- comparing and reverting work leaf by leaf.

Reels are ordered story, stance, b-roll text, and mapped from the brief by their `kind`, never by position. In the app the tabs follow the mock WIA saw (Email, Carousel, Reel 1, Reel 2, Reel 3). The exported document follows the v2 document's order (Email, Reel 1 to 3, Carousel).

| Piece | Leaves (v4 names) | Pack extras | Rules |
| --- | --- | --- | --- |
| `email` | `send_header` {date, send_time, recipients}; `subject_options` (three, best first); `preview`; `opening`; `body`; `ending`; `offer_descriptor` | `cta` {kind: reply or link} | Stands alone; no bullets; one bold line; never "DM"; "Talk soon, Whitney"; 250 to 450 words |
| `reel_1` story | `cover_text`; `on_screen_hook`; `spoken_opening`; `script`; `caption` {hook, body, ending}; `personal_lines`; `read_time_seconds`; `offer_descriptor` | `title` (a working title, never the creative direction); `cover_alternates` (two); `cta` (none, soft or offer); `no_offer_ending` | Spoken; 45 to 90 seconds; a crisp first line; no "Okay, so" |
| `reel_2` stance | As `reel_1` | As `reel_1` | The same point as Whitney's stance, with the moment as proof in a line or two; never a sub-lesson |
| `reel_3` b-roll text | `cover_text`; `on_screen_hook`; `screens` (one to three); `caption` {hook, body, ending} | As `reel_1`, without a script | A cold viewer follows the turn from the screens alone |
| `carousel` | `title`; `slides` [{number, text}] (7 to 12; stacked short lines, at most one bold line each); `caption` {hook, body, ending}; `offer_descriptor` | `cta`; `no_offer_ending` | Slide 1 carries the title's promise; the story runs over two to four slides; then the reader's situation, a belief slide, and a close for both readers |
| Every piece | — | `brief_key`; `brief_copy` (the approved leaves, for comparing and reverting); `source` (`brief`, `finished` or `written`); `locks` (leaf paths, each with its author and whether it was delegated); `findings` | — |
| Pack level (in `content_packs.content_body`) | — | `before_publishing` (carried from Gate 2 with its answers; client-permission items shown as notes for whoever posts); `pack_notes` (the finisher's own notes, kept apart from the brief's five); `client_quotes`, each with its clearance; `stronger_with_permission`; `change_notes`; the change record of this version; provenance (brief id and approved hash, profiles, models, knowledge-base version, run id, whether the approval was delegated) | Caveats only here, never in copy (R54) |

**Mapping rules.**
- A Reel kind the brief lacks is written (`source = written`).
- A duplicate kind (for example two story Reels) becomes source material for the missing kind.
- A Reel with `source: existing_clip` keeps the brief's copy and gets a before-publishing note.
- A person's Gate 2 anchor follows the remap.

**At go-live, only v4 briefs start a pack by themselves.** A v3 brief shows "Re-develop as a v4 brief to get a content pack."

### 4.3 The pack standard and its checks

The standard is the main plan's section 4.3 (asset rules and first-touch rules, R59) plus the house style by format (findings document, section 14.9). The finisher writes to it, and the checks enforce it as follows.

| Check | Blocking? | Exists | Notes |
| --- | --- | --- | --- |
| First-touch rules 1 to 5 | Insider terms block; the rest warn (as at Gate 2) | Yes (`first_touch.py`) | On the v4-shaped pack body |
| Outcome verbs; hook fidelity against the ledger | Blocking | Yes (`asset_checks.py`) | |
| **Consent and names** (`validation_v2.public_copy_checks`, `copy_quote_checks`) | **Blocking** | Yes, but `asset_findings` does not run it | A person's name is allowed only for WIA staff (roster), when the evidence's `client_consent` is `may_name`, or when a clearance exists |
| The rest of E.B24's asset checks (caveats in copy, kickers, detail density, sibling overlap, DIY drift, send header, "-Whitney", both readers, offer descriptor, register, banned CTA patterns) | Warnings | Yes | |
| **Quotes exact and attributed** | **Blocking** | **New** (NP.B4) | Every quoted span matches an evidence quote (fillers allowed) and is attributed to its speaker, through the ledger claim's `quote` and `field`. **Whether a quote sits in its own moment** is judged by the fidelity check and the review, not deterministically |
| **No new numbers or names** | **Blocking** | **New** | Numbers and capitalised names are compared with the claims, evidence, roster and offer descriptors, plus a short tools list (Google, Meta, Canva, ChatGPT...) |
| **Client quote listed** | A before-publishing note, not a gate | **New** | Every client quote in copy is listed for the client's okay before posting; Whitney's own lines follow the brief's clearance |
| **Fidelity** (model): an unsupported or guardrail statement left after the repair | In a piece the brief had: the brief's sentence is put back. In a written Reel: **blocks until a person edits the sentence or attests it is true** (R57) | **New** (NP.B8) | |
| **Composition**: exactly 1 email, 3 Reels of the three kinds, 1 carousel | Blocking | **New** | |
| **Format**: slide length (2 to 5 lines, about 20 to 55 words), caption 150 to 300 words, script 120 to 220 words, b-roll 1 to 3 screens, three subject options, Reel title not equal to its direction | Warnings | **New** | |
| **US spelling** (a list of British forms) | Warning | **New** | |
| **Week**, computed on read: one offer CTA a week on Instagram; hooks, covers and subjects distinct across the week; emoji in subjects at most twice a month; no central point repeated within 60 days | Warnings | Partly (the week checks); hooks, subjects, emoji and repeats are **new** | |

### 4.4 The week

WIA's week (KB 14, R-10, R-11) is one Tuesday email and three Instagram pieces, two without an offer CTA and one with. Posting order is graphic, Reel, carousel, with formats alternating. Three packs a week produce three emails and fifteen Instagram pieces, so most pieces wait in the bank.

When read, the **week plan** proposes, for the publishing week after approval:

| Slot | Default rule |
| --- | --- |
| Tuesday email | The highest-ranked pack's email (by the card's rank). The other emails wait for the following Tuesdays |
| Instagram 1 (Monday) | The story Reel of a WARM or ATTRACT pack, with no offer ask (its `no_offer_ending`) |
| Instagram 2 (Wednesday) | The carousel of a different pack, with no offer ask |
| Instagram 3 (Friday) | The week's one offer post: a piece of the CONVERT pack if there is one (else the strongest), with the brief's CTA, within the offer calendar (E.B28) |
| The bank | Every other unpublished piece, with a suggested order for the following weeks |

Dates are suggestions:
- They are computed when read and shown in the week view and the export.
- They are never stored on the pack's copy.
- Editing them in the app comes later, with the calendar.

The system neither schedules into any tool nor publishes (D43e).

### 4.5 What a pack never does

- It adds no fact, number, name, quote, motive, outcome or commitment that the brief's claims and the call's evidence do not hold.
- No model ever rewrites a line a person wrote, at Gate 2 or in the pack.
- It has no feedback refresh in the pack (the 20 October promise). "Finish again" re-runs the finisher with no new instruction, keeping every person's line. NP-7 adds two person-started passes that take a person's own input: the post-recording pass (Whitney's recorded words) and finishing again with a granted permission. They are not feedback refresh.
- A client's permission to tell their story or quote them is never a system gate. It is a before-publishing note on the pack and in the export, for whoever posts the piece. The team never invents a permission reference.
- It produces no designs, fonts or images. Carousels are copy only.
- It never schedules or publishes.

### 4.6 Success measures for packs (first live weeks, alongside the main plan's 4.5)

| Measure | First live week | Done (two consecutive live weeks) |
| --- | --- | --- |
| Packs WIA marks ready with light edits or none | At least half | At least 80% |
| Edits of a kind a pack check covers (first touch, insider term, who did what, quote, name) | Recorded by kind | None of a checked kind |
| Factual problems WIA finds in a pack | Recorded | None the fidelity loop did not flag |
| Pieces published from packs | Recorded | WIA publishes from the packs each week (RQ7) |
| Cost per pack | Recorded | At most USD 0.85 on average |

---

## 5. The design

### 5.1 The flow

```
Gate 2 approves a v4 brief ─► pack run (scope pack_generation, purpose packs, queue interactive)
   1 pack_assemble   hand-off view v2 → v4-shaped pieces (Reels by kind), locks translated; no model
   2 pack_finish     Opus 5.5 (models.pack_writer, medium): edit to the house style; write missing kinds;
                     cover alternates; no-offer endings; client_quotes; stronger_with_permission; notes
                     → paths.restore puts every locked line back
   3 pack_check      Sonnet 5.5 (models.pack_review, medium): statements supported / unsupported / guardrail
                     (locked lines and personal_lines skipped)
   4 pack_repair     Opus 5.5: patches for flagged sentences only (only if flagged) → paths.restore again
   5 pack_recheck    Sonnet 5.5: changed statements only (only if repaired)
   6 pack_finalize   paths.restore; sentence-level put-back where a flag survives in a brief piece;
                     open findings on written Reels; deterministic checks; manifest; state in_review
        ▼
Pack screen: read · Copy · Copy all · edit any line (locked, versioned) · what the finisher changed · use the brief's
             line · read the before-publishing notes · attest a finding · Finish again · Ready · per piece Published
        ▼
Week view: this week's allocation (1 email, 3 Instagram pieces, 1 offer post) · the bank · export the week's document
        ▼
Learning: person-made pack edits and published finals → edit diffs → repeat corrections → rule candidates (L.B6, L.B14);
          delegated and system-made versions excluded; published register → recency, prior coverage
```

### 5.2 Hand-off view v2 (part of NP.B1)

`brief_handoff_v2` is version-bumped, so v1 consumers keep working. It adds:
- `strategy`: supporting_example, narrative_outline, strategic_purpose, intended_shift and cta_why;
- `call_date` on each evidence item;
- each claim's `field`, mapped to a piece and leaf;
- `locks` as [{piece, leaf, value, author, delegated}], computed from `review.locked_fields` and the path locks.

The pack reads **only** hand-off v2, so R56 stands as written. Tests go in `test_brief_handoff.py`.

### 5.3 The data model (part of NP.B1; migration 009)

**Migration `009`.**
- It adds `content_packs.content_body jsonb` and `content_hash text`, for the pack-level fields of section 4.2.
- It adds `pack` to `decisions.item_kind`, so clearances, attestations, readiness and edits are audited like Gate 1 and Gate 2 decisions (R45).
- On production, a fresh `db-backup` dump is taken first (NP-6).

**Rows.** One `content_packs` row per pack version, and one `content_assets` row per piece: `slot_key` is the piece key, `asset_type` the piece type, `reader_contribution` the piece's job, plus `content_body`.

**Versions are kept per pack, as briefs keep theirs.** `content_assets` allows one row per piece per pack (its unique index). So each of these writes a new `content_packs` row whose `supersedes_id` is the previous one, with the five piece rows copied and the changed one replaced:
- a person's edit;
- a revert;
- an attestation that changes text;
- Finish again.

The change record is in the new version's body. The current pack is the one nothing supersedes. The versions list walks the chain, as `gate_two.versions` does for briefs.

**The manifest** hashes the pack body's hash together with the pieces' hashes. Published marks and week dates are outside it.

**The run.**
- It is `pack_run_<intent24>`, keyed on the brief id, its approved hash and the contract.
- A pack run binds to the approved hash and to "no replacement brief". It does **not** re-run the live Gate 2 blockers, so a prior-use change elsewhere cannot fail it part way.
- Any new run for a brief (Finish again, a mode switch) supersedes the brief's current pack.
- Edits and Finish again are refused while a run is active.
- Finish again takes the current manifest hash.

**The frozen contract** holds the profiles, models, knowledge-base version and schemas, without `max_tokens` (`packs/runtime.py` moves to a stable contract). Saved responses replay at USD 0 (0.B4).

### 5.4 The finisher (NP.B7)

| Aspect | Rule |
| --- | --- |
| Model | `anthropic/claude-opus-5.5`, through the existing `models.pack_writer`. `settings_store.py:168` maps `pack_write` and `pack_repair` to it, and `pack_finish` is added. Reasoning effort is **medium** (`models.reasoning_effort.pack_writer`), as in the probe. The switch-back is `anthropic/claude-sonnet-5.5`, set by setting, a stated quality trade-off |
| Prompt | `prompt_templates/pack_finish.v1.md` (profile `2026-10-25.pack-finish.v1`), built from the probe's `pack_probe_v2.py`. It contains:<br>• the role;<br>• knowledge-base documents 02, 09, 10, 15, 17, 18 and 19 from the active version, through the context-assembly service as a new stage `pack` (`knowledge/assembly.py`, `STAGES` l.40). That stage reads the documents the active version marks for `brief` (all seven are), with its own priority keeping them inside the prefix budget, so no new knowledge-base version is needed;<br>• the house style by format;<br>• the first-touch rules;<br>• the fidelity rules;<br>• the task: refine, don't replace; anchor first; three Reels, writing a missing kind as the same idea through a different door;<br>• the output contract in the v4 leaf shape (section 4.2), not the probe's flattened shape.<br>The probe's banned-word list, written while reading the three briefs, becomes general wording |
| Story constraint | The story's facts are exactly the hand-off's `strategy.supporting_example` (scene, what WIA did, what the client contributed, who did what, details the copy uses) and its supported claims.<br>• Reported speech restates a claim or an exact quote. There is never invented dialogue.<br>• A quote stays attached to its moment.<br>• A hedge stays a hedge.<br>• Reactions in Whitney's voice appear only in scripts and are listed in `personal_lines` |
| Inputs | Hand-off v2 only (the pieces' copy and direction, anchor, spine, CTA, strategy, claims with fields, before-publishing items with answers, evidence with consent and call dates, locks), plus the offer descriptors |
| Locks | Shown to the model as LOCKED. After the finisher, and again after the repair, `briefs/paths.restore` puts any changed locked line back and records it. If the model re-splits or renumbers a carousel that has a locked slide, the brief's carousel is kept and the event recorded, instead of failing the job |
| Output | The v2 pack contract, validated, with one repair for a malformed answer (as every stage) |
| Request | Strict `json_schema`, as production sends. NP.X2a proves it on Opus with ZDR routing. If it is refused there, the stage uses `json_object` with local validation (`chat_body`'s existing mode) |
| Limits | A flow budget of 12 chat calls per run (as briefs). The system prefix is excluded from `briefs.max_characters`, as briefs do (`briefs/runtime.py:259-262`). The output cap is `models.completion_tokens` (32,000, never binding, K74) |
| Cost and time | About USD 0.35 to 0.55 and 95 to 203 s at medium (probe) |
| Modes (`packs.finish_mode`) | `finish` (default); `missing_only` (copy verbatim, write only a missing Reel kind); `assemble` (no model call; a missing kind shows as "not written", with the reason) |

### 5.5 The fidelity loop (NP.B8)

| Stage | Model and prompt | Rule |
| --- | --- | --- |
| `pack_check` | Sonnet 5.5 through `models.pack_review` (medium), `pack_check.v1`, from `claim_probe.py` version 2 | Lists every statement about the real event, the client, WIA's actions, a person's words, a result or a commitment, and **whether each quote sits in its own moment**.<br>Its sources are the supported claims, the supporting example, the before-publishing items, the evidence, the offer descriptors, the belief statements (KB 16) and the call dates.<br>Hinting at a kept-out detail is a guardrail break. A hedge stated as certain is unsupported.<br>Locked lines (person-authored) and `personal_lines` are marked and skipped.<br>USD 0.06 to 0.10 |
| `pack_repair` | Opus 5.5 through `models.pack_writer`, `pack_repair.v1`, from `repair_probe.py` | Patches only (`piece`, `old`, `new`), only for flagged, unlocked sentences. It prefers cutting a detail to inventing one. A patch whose `old` is not found is dropped and recorded. `paths.restore` runs after. About USD 0.11 |
| `pack_recheck` | Sonnet 5.5, `pack_check.v1`, on the changed statements only, plus the caption of a Reel whose script changed | USD 0.03 to 0.09 |
| `pack_finalize` | No model | **A flag that survives in a piece the brief had:** the flagged sentence goes back to the brief's corresponding sentence, as a patch from the pack sentence to the brief sentence, falling back to the whole leaf. The change is recorded.<br>**A flag that survives in a written Reel:** it stays as an **open finding** attached to its sentence. It clears when a person edits that sentence or attests it is true (R57, recorded as `attested` with person and date).<br>Then come `paths.restore`, the deterministic checks (section 4.3), the manifest, and `in_review` |

A model check is a net. The deterministic checks and the review draw the line. WIA's corrections on packs become labelled cases for `pack_check` (NP.X5).

### 5.6 The API (NP.B6) and the allowlist

| Route | Purpose | Role |
| --- | --- | --- |
| `POST /storage/briefs/{id}/pack` | Create or retry the pack for an approved v4 brief; refused unless `can_consume` | Editor or approver |
| `GET /storage/packs?week_id=&state=` | The week's packs with state (new state values) | Reviewer |
| `GET /storage/packs/{id}` | The v2 pack: pieces, findings, quotes, confirmations, versions | Reviewer |
| `GET /storage/packs/{id}/production` | Jobs, costs, waiting reasons | Reviewer |
| `PATCH /storage/packs/{id}/pieces/{key}` | Edit leaves by dotted path (`briefs/paths.py`), with the expected hash; locks each edited line; re-runs the deterministic checks; refused while a run is active | Editor or approver |
| `POST /storage/packs/{id}/pieces/{key}/revert` | Use the brief's leaf | Editor or approver |
| `POST /storage/packs/{id}/clearances` | Record that a before-publishing note is done (a client's okay, a quote cleared), with person, date and reference | Approver |
| `POST /storage/packs/{id}/findings/{finding_id}/attest` | Attest that a flagged sentence is true (R57) | Approver |
| `POST /storage/packs/{id}/finish` | Finish again (new run, locks kept, current manifest hash) | Approver |
| `POST /storage/packs/{id}/decision` | `ready_to_publish` (bound to the manifest) or back to review | Approver |
| `POST /storage/packs/{id}/pieces/{key}/published` | Mark published (date, channel, final text): a capture with reference `pack:<brief_id>:<piece_key>` | Editor or approver |
| `GET /storage/weeks/{id}/pack-plan` | The week plan, week findings and the bank, computed on read | Reviewer |
| `GET /storage/weeks/{id}/packs.md` and `GET /storage/weeks/{id}/packs.docx` (NP.B12) | The week's pack document | Reviewer |

Each route gets:
- a response model in `api_models.py`;
- the OpenAPI file regenerated;
- the frontend types regenerated;
- an allowlist entry and a server test.

### 5.7 The screens (NP.F1 to NP.F4)

- **The pack list and detail** replace the v1 `StoredPacks` list and detail. They port the mock WIA saw (`frontend/src/mock/components/IdeaDetailModal.tsx:318-410`, `stages/ideaStages.ts:274-281`):
  - a sticky tab list (Email, Carousel, Reel 1, Reel 2, Reel 3) with order badges;
  - each piece as a card with labelled sections;
  - **Copy** per piece and per field, and **Copy all**;
  - a state chip;
  - a provenance line: "System output: finished by the content-pack step from the approved brief" (R58), plus "Approved by the team under delegation; Whitney has not reviewed it" where true.
- **Editing** works like Gate 2's editors: by dotted path, with conflict handling. An edited line shows a lock. Each piece has two toggles:
  - "What the finisher changed" (a diff against `brief_copy`);
  - "Use the brief's line", per field.
- **The review panel:**
  - blocking findings in plain words (R50), each with "Attest it is true" where allowed;
  - client quotes to clear;
  - before-publishing notes (client permissions and quotes, for whoever posts), each markable as done;
  - stronger with permission (read-only; acting on it is NP-7);
  - personal lines to keep or cut;
  - Finish again;
  - Ready to publish.
- **The Gate 2 hand-over:**
  - the approve button reads **"Approve brief and create content pack"**;
  - after approval, the brief page shows the pack's state and link;
  - `packMapped` and the v1-only note are removed;
  - the brief page's `PublishedCapture` is hidden once a pack exists;
  - Gate 2's asset copy is labelled "Draft copy: the content pack finishes it. Any line you edit here is kept word for word."
- **The week view:** the week's packs, the proposed allocation (date, piece, CTA; read-only), week findings, the bank, Published, and export.

### 5.8 Budget, settings and model plumbing (NP.B5)

- **The purpose.** A new purpose, `packs`, in `standing.py`:
  - `PURPOSES`, `LABELS` and `SCOPE_PURPOSE` (`pack_generation`);
  - `STAGE_PURPOSE` with **every pack stage now**, NP-7's included: `pack_finish`, `pack_check`, `pack_repair`, `pack_recheck`, `pack_caption` and `pack_refinish`. A week's frozen stage list then never refuses a later stage.
- **The cap.** `budgets.weekly_usd.packs`, set with `budgets set`:
  - **USD 6.00 for the week of 26 October.** It covers NP-6's packs if they are made live, about three of WIA's, two post-recording passes and one Finish again. 7.X1's brief approval also spends from it.
  - **USD 3.50 a week from 2 November:** three packs at up to USD 0.85, two passes and one Finish again.

  `budgets.weekly_calls.packs` is 60. A pack whose next call does not fit **waits**, with the reason on the pack, as briefs do.
- **Model plumbing.**
  - `anthropic/claude-opus-5.5` goes into `NO_TEMPERATURE` (`llm/request.py:14`), which also asks for usage, so cost settles from `usage.cost`.
  - It goes into `MODEL_PRICES_USD_PER_MILLION` at OpenRouter's listed USD 4 / 20 (`costs.py`), so its worst case is refused before sending and estimates work.
  - `STAGE_SUFFIX` maps `pack_finish` and `pack_repair` to `pack_writer`, and `pack_check` and `pack_recheck` to `pack_review` (`settings_store.py:160-169`).
  - The pack flow budget is 12 calls, and the system prefix is excluded from the character limit.
- **Settings in `production-settings.json`:**
  - `features.packs: true`;
  - `models.pack_writer: anthropic/claude-opus-5.5` and `models.pack_review: anthropic/claude-sonnet-5.5`;
  - `models.reasoning_effort.pack_writer: medium` and `models.reasoning_effort.pack_review: medium`;
  - `prompts.profile.pack_finish`, `pack_check` and `pack_repair`;
  - `packs.finish_mode: finish`.
- **The variable.** The live switch is `ATELIER_ALLOW_PACK_GENERATION=true` on `api` and `editorial-worker`. The value is `true`, because `storage_config.py:92` accepts only `'true'`.
- **Authority.** A Gate 2 approval itself authorises the pack's start, so an approver who is not on a pack-editor list still gets a pack (`packs/service.authorize`, tested in list mode).
- **Timing.** One worker runs `interactive,default`. A pack takes 4 to 6 minutes when no other pack is running, so three approvals in a row take about 12 to 18 minutes.

### 5.9 Learning (NP.B13)

- **Pack edits.** A person's pack edit is recorded as an authored edit (field, before, after, person, time). `knowledge/mining.edit_diffs` reads it beside Gate 2 diffs and published finals.
- **What mining excludes.** Delegated edits and system-made versions (finisher, put-back, Finish again) are left out. WIA's labels are never learned from the team's or the model's text (K53).
- **Published finals.** A published piece is captured with reference `pack:<brief_id>:<piece_key>` (`source_kind = 'approved_brief'`), so its edit difference is measured against the pack's copy.
- **The loop.** The weekly loop categorises edits (L.B6), and a correction given twice becomes a rule candidate (L.B14). Whitney's pack edits are the raw-to-final chains the diagnosis found missing. Each week's set feeds X.2's tone loop and the next finisher profile (NP.X4).

### 5.10 Alternatives considered

| Option | Why not, or why later |
| --- | --- |
| **Copy the brief verbatim (no model)** | WIA would get copy below v2 (section 3.2), and all three briefs lack the stance Reel. Kept as the `assemble` mode and the last fallback |
| **Finish before Gate 2** (as the brief's last step) | Gate 2 would approve final copy. But every brief, approved or not, and every refresh would pay for finishing, and it departs from "approve the brief, then the pack" (RQ1). Kept as the alternative in D43b |
| **Restructure the brief into strategy only, with all copy written by the pack** | Rewrites a built and verified brief path two days before go-live and breaks the brief-done checkpoint, for no gain the finisher does not give |
| **Write each piece fresh from the strategy** | No gain over editing in the probe. Editing keeps the verified claims and the anchor's lines (RQ19) |
| **Sonnet 5.5 as the finisher** | A third of the cost, little gain. Kept as a switch-back setting |
| **Writer v5.1 (three Reels in the brief) at go-live** | No reading yet, and a schema change would break the free replay of N2's briefs. NP-7 brings it with its own reading. Until then the finisher writes the stance Reel |
| **Scheduling with the calendar package at go-live** | Not requested. The calendar is bound to the v1 slot check and has no publishing integration. Later, if WIA asks (D43e) |

---

## 6. The steps

### NP-0. Decide (done 24 October)

| ID | Action | Done when |
| --- | --- | --- |
| NP.X0 | Confirm D43b to D43j (section 9); the composition (D43a) is decided | **Done (24 October):** the owner confirmed D43b to D43j as recommended; recorded in the main plan's section 7.2 |

**Exit:** the decisions are recorded. Any part left unanswered keeps its recommended default.

### NP-1. Pack foundation (Track A)

**First:** Track A ships the **frozen contract** that both tracks build on:
- `packs/contracts_v2.py`;
- the `api_models` response models;
- the OpenAPI file;
- the generated `schema.d.ts`;
- migration 009.

| ID | P | Effort | Work | Done when |
| --- | --- | --- | --- | --- |
| NP.B1 | P0 | M to L | **Hand-off v2, the data model, the contract and assembly:**<br>• `brief_handoff_v2` (section 5.2);<br>• migration 009 (section 5.3);<br>• `packs/contracts_v2.py` in the v4 leaf shape (section 4.2);<br>• `pack_assemble` builds the pack from hand-off v2, with Reels mapped by `kind` (a missing kind left for the finisher, a duplicate used as source material, `existing_clip` kept with a note), `brief_key` and `brief_copy`, Gate 2 locks translated (only the Reel index changes) and the anchor remapped;<br>• v1 packs stay readable through the old path; v3 briefs get "re-develop as v4" | Database tests:<br>• N2-shaped v4 briefs (two and three Reels) assemble into packs with the fixed keys, the brief's copy and locks;<br>• Gate 2 locks on the email opening, a caption hook and carousel slide 3 land on their pack leaves;<br>• a lock on a two-Reel brief's b-roll Reel lands on `reel_3`;<br>• hand-off v2 carries the strategy, call dates, claim fields and locks, and v1 consumers still pass;<br>• migration 009 applies and rolls forward from 008;<br>• no model call |
| NP.B2 | P0 | S | **Start on approval, and retry:**<br>• in `gate_two.decide`, when the brief is approved, is v4 and `features.packs` is on, queue the pack in the approval's transaction through a savepoint (Gate 1's pattern); a failure records a failed run without undoing the approval;<br>• the approval itself authorises the start;<br>• `POST /briefs/{id}/pack` creates or retries;<br>• live mode when `ATELIER_ALLOW_GENERATION=true` and `ATELIER_ALLOW_PACK_GENERATION=true`, else replay (synthetic in tests);<br>• the event text changes | Tests:<br>• approving makes exactly one pack run, live with both switches `true` and in replay otherwise;<br>• packs off makes none;<br>• a v3 approval makes none and says why;<br>• a retry resumes;<br>• the approval commits when queueing fails;<br>• an approver outside the pack-editor list still gets a pack |
| NP.B3 | P0 | M | **Versions, edits, locks, states, readiness, published:**<br>• `PATCH` by dotted path with the expected hash, locking each person's line with its author (delegated or WIA);<br>• each edit, revert or text-changing attestation is a new pack version (section 5.3), refused while a run is active;<br>• states derived (section 4.1);<br>• `ready_to_publish` bound to the manifest, with one condition: no open blocking finding (client permissions and quotes are before-publishing notes);<br>• decisions recorded as `item_kind = pack`;<br>• mark published through capture with reference `pack:<brief_id>:<piece_key>`, outside the manifest | Each transition is tested, including a stale hash, an edit during a run, an edit after ready, a revert, and a pack whose open client-permission note does not block Ready. Marking a piece published leaves the pack `ready_to_publish` and writes a `published_content` row with its edit difference against the pack copy |
| NP.B4 | P0 | M | **Pack checks** on the v4-shaped body:<br>• `first_touch_findings`;<br>• `asset_findings` (anchor from the hand-off);<br>• `public_copy_checks` and `copy_quote_checks` (consent and names, blocking);<br>• the new checks of section 4.3.<br>Week findings are computed on read (siblings are the week's other current packs). Checks re-run after every edit | Each new check has a failing and a passing test on **synthetic** fixtures reproducing the probe's failure patterns: an invented reflection, "explained" turned into "agreed", a price hint, a hedge stated as fact, a client name under `anonymise`. An optional real-text regression reads `research/` at run time and skips when absent. On the v2 packs, the checks that need no evidence raise no blocking finding |
| NP.B5 | P0 | S | **The budget, settings and model plumbing** (section 5.8):<br>• the `packs` purpose with every NP and NP-7 stage, and `BUDGET_DEFAULTS`;<br>• Opus in `NO_TEMPERATURE` and the price table;<br>• `STAGE_SUFFIX` for the new stages;<br>• a flow budget of 12, with the prefix excluded from the character limit;<br>• the settings (existing `features.packs`, `models.pack_writer`, `models.pack_review` and the effort keys; new `prompts.profile.pack_*` and `packs.finish_mode`), with defaults that keep packs off;<br>• the assembly service's `pack` stage;<br>• DEPLOYMENT.md and `production-settings.json` | Tests:<br>• an Opus request has no temperature and asks for usage;<br>• the Opus worst case is refused when it passes the remainder;<br>• `pack_finish` resolves to medium effort;<br>• a fresh week's `packs` plan lists `pack_caption` and `pack_refinish`;<br>• a call over the cap waits with its reason;<br>• `test_documented_variables` passes |
| NP.B6 | P0 | M | **The API** (section 5.6): response models, OpenAPI, frontend types, the allowlist and server tests. Every route answers 503 `packs_disabled` while the flag is off | OpenAPI check clean; server and allowlist tests pass; a v4 pack round-trips through the API in a database test |

**NP-1 exit.** In a database test with `packs.finish_mode = assemble`:
- approving a **three-Reel** v4 brief produces a pack with 1 email, 3 Reels and 1 carousel, and its Gate 2 locks hold;
- the pack can be edited, reverted, marked ready and published through the API;
- a two-Reel brief's pack shows the missing kind as "not written", and Ready is blocked with that reason;
- checks run, and CI is green.

**Status (24 October): done, merged in PR #17 (`f1576d0`).**
- **NP.B1 Done** (`5349c23`, `559d931`, `fce5e6f`):
  - hand-off view v2 (`briefs/handoff.py`: strategy, call dates, claim places, locks with author and delegated flag,
    `quotable` per evidence item);
  - migration 009;
  - the frozen `content_pack_v2` contract;
  - assembly by Reel kind.
- **NP.B2 Done** (`74ecb95`, `63d3a10`, `f4c1d8c`):
  - Gate 2's approval of a v4 brief queues its pack and answers `pack_run` and `pack_note`;
  - create and retry;
  - a run stuck on a changed contract gets a new run.
- **NP.B3 Done** (`365c326`): versions, edits with locks, reverts, clearances, attestations, derived states, readiness
  bound to the manifest, published marks.
- **NP.B4 Done** (`81a6c7a`, `226a6b9`): the deterministic checks, run on copy only (a Reel's beats are direction).
- **NP.B5 Done** (`5349c23`):
  - the `packs` purpose (USD 3.50 and 60 calls by default, production USD 6.00);
  - Opus 5.5 priced and without temperature;
  - the stage suffixes;
  - medium effort.
- **NP.B6 Done** (`5349c23`, `365c326`, `2fd92d4`, `fce5e6f`): the v2 routes, the response models, a deterministic
  OpenAPI, the allowlist, and the role matrix rows.

**NP-1 exit met.** The service and week database tests cover it (`test_packs_v2_service_db.py`,
`test_packs_v2_week_db.py`), and CI was green on PR #17.

### NP-2. The finisher and its fidelity loop (the main session)

| ID | P | Effort | Work | Done when |
| --- | --- | --- | --- | --- |
| NP.B7 | P0 | M | **The finisher** (section 5.4):<br>• `pack_finish.v1.md` and its profile;<br>• the `pack_finish` stage through `llm.workflow.chat` with S.B1 routing;<br>• validation and one repair;<br>• `paths.restore` after the call;<br>• locked-carousel protection;<br>• the three modes | With recorded responses:<br>• a two-Reel brief yields three Reels of the three kinds;<br>• a locked line the model changed is put back and recorded;<br>• a renumbered carousel with a locked slide keeps the brief's carousel and records it;<br>• `missing_only` changes no existing line;<br>• `assemble` makes no call |
| NP.B8 | P0 | M | **The fidelity loop** (section 5.5): `pack_check.v1` and `pack_repair.v1` with their stages; the re-check; `pack_finalize` with sentence-level put-back and open findings on written Reels; the attest route's backend | With recorded responses:<br>• a flagged sentence is repaired and passes;<br>• a locked line is never sent for repair;<br>• a missed patch is recorded;<br>• a surviving flag in a brief piece puts back that sentence only;<br>• a surviving flag in a written Reel blocks Ready until an edit of that sentence or an attestation (recorded as `attested`) clears it |
| NP.B9 | P0 | S | **Replay and pinning:**<br>• the stable contract without `max_tokens`;<br>• the settings snapshot in the run's inputs;<br>• saved responses replay at USD 0;<br>• the shakedown adapter covers the pack stages for free models (main plan 5.0c), with a canned-answer path for NP.X1 | A finished pack replays byte for byte at USD 0 in a fresh database; raising the output cap mid-run does not void it; the guard tests still pass |

**NP-2 exit.** In offline and database tests with recorded and fake responses:
- an approved two-Reel brief becomes a finished pack with three Reels;
- locks hold through finishing and repair;
- flagged sentences are repaired or put back;
- a written-Reel finding clears only by an edit or an attestation;
- the pack replays at USD 0;
- CI is green.

**Status (24 October): done, merged in PR #17.**
- **NP.B7 Done** (`559d931`, `349498a`, `2fd92d4`, `870064b`, `3f60001`):
  - the finisher with its three modes;
  - locks put back after the call;
  - the locked-carousel rule;
  - the K45 independence from the judge;
  - `pack-finish.v2` (NP.X3's stop rule; v1 stays selectable for replay);
  - Finish again keeps a written Reel "written".
- **NP.B8 Done** (`559d931`, `870064b`, `8681aeb`):
  - check, repair and re-check (`pack-check.v2`);
  - finalize with sentence-level put-back, falling back to the brief's paragraph when the sentence would repeat its
    neighbour;
  - open findings on a written Reel, cleared by an edit or an attestation.
- **NP.B9 Done** (`63bddbb`, `35c9f96`): the stable contract without `max_tokens`, replay at USD 0 through `pack-cache`,
  and the canned-answer path for the free-model shakedown. PR #18 (`4e1396e`) pins the pack stages' wire-schema hashes: a
  docstring is part of a stage's schema, so changing one voids every saved answer.

**NP-2 exit met.** It is covered by `test_packs_v2_finisher.py` (19 tests), `test_packs_v2_contract.py` and
`test_np_exit_db.py` (the replay and the output-cap tests). CI was green.

### NP-3. The pack screen (Track B)

| ID | P | Effort | Work | Done when |
| --- | --- | --- | --- | --- |
| NP.F1 | P0 | M | **The pack list and detail** (section 5.7), replacing the v1 screens: tabs, order badges, labelled sections, Copy per piece and field, Copy all, the state chip, provenance and delegated labels (R58, R55), and waiting and failure reasons in words | Unit tests render each piece kind, the Copy and Copy all text, each state and the delegated label; the allowlist test passes |
| NP.F2 | P0 | M | **Editing and comparing:** edit any leaf (Gate 2's editor pattern, with the conflict notice), lock marks, versions, "What the finisher changed" and "Use the brief's line" | Tests:<br>• an edit locks and saves;<br>• a stale hash shows the conflict with the input kept;<br>• an edit during a run is refused with its reason;<br>• a revert restores the brief's leaf |
| NP.F3 | P0 | S | **Review and hand-over:**<br>• the review panel: findings with attest, before-publishing notes (client permissions and quotes), personal lines, stronger with permission, Finish again, Ready;<br>• the Gate 2 button label, the pack link and the draft label;<br>• removing `packMapped` and the v1 note;<br>• hiding the brief page's capture once a pack exists | Tests:<br>• Ready is blocked with a named reason until open findings are resolved;<br>• before-publishing notes show on the pack and never block Ready;<br>• approving a brief links to its pack |
| NP.F4 | P1 | S | **The week view:** the allocation (read-only dates), week findings, the bank, Published, export | Tests: the view renders `GET /weeks/{id}/pack-plan`; marking a piece published moves it out of the plan |

**NP-3 exit.** In the stack, an approver:
- approves a brief and reaches its pack;
- copies pieces;
- edits and reverts a line;
- clears a quote and attests a finding;
- marks the pack ready and a piece published;
- opens the week view and its export.

The frontend type check, lint, unit and server tests, and build pass.

**Status (24 October): done, merged in PR #17** (`4157317`, `334b8ca`).
- **NP.F1 to NP.F4 Done:** the pack list and detail, editing and comparing, review and the Gate 2 hand-over, and the
  week view, each with unit tests. The frontend type check, unit and server tests and build passed in CI.

**NP-3 exit met in part.**
- In the shakedown stack, every flow was exercised through the API (NP.X1's ledger, step 4). The local Command Center
  image could not sign in (NP.X1's ledger, finding 6).
- The screens on production are NP-6 step 4's check.

### NP-4. Week plan, export and learning

| ID | P | Effort | Work | Done when |
| --- | --- | --- | --- | --- |
| NP.B11 | P0 | S | **The week plan** (section 4.4): deterministic and computed on read, from KB 14, the offer calendar, the packs' purposes and ranks, their `no_offer_ending` variants and the pieces already published. Also the bank and the week findings | Tests: three packs give one Tuesday email, three Instagram pieces with exactly one offer ask, distinct hooks, covers and subjects, and a bank; a published piece leaves the plan |
| NP.B12 | P0 (Markdown), P1 (.docx) | S to M | **The week's pack document:**<br>• extend `review_document.py` with a pack section per brief: the angle card, the brief's strategy, every piece in final form and unabbreviated, "Before you publish" with open permissions, and client quotes to clear;<br>• the week plan on top;<br>• `GET /weeks/{id}/packs.md` and `storage_cli pack-document`;<br>• the .docx through `python-docx` (added to `requirements.txt`), generated without a client template | The proof's packs render complete; the .docx opens in Word and Google Docs, or the cut list's fallback applies |
| NP.B13 | P1 | S | **Learning:** person-made pack edits as authored edits in `mining.edit_diffs`; delegated and system-made versions excluded | Tests:<br>• a WIA pack edit appears in the edit diffs;<br>• a delegated edit and a finisher version do not;<br>• a repeated correction becomes one rule candidate (L.B14) |

**NP-4 exit:** the week view and the export work on the proof's packs in the stack. Person-made edits and published pieces reach the learning tables. CI is green.

**Status (24 October): done, merged in PR #17.**
- **NP.B11 Done** (`2eac7c7`).
- **NP.B12 Done for Markdown** (`0b54377`, `storage_cli pack-document`). The .docx export moves to NP-7.
- **NP.B12's .docx Done** (`d596cf2`): `GET /weeks/{id}/packs.docx` and `storage_cli pack-document --format docx --out <file>`, rendered from the same Markdown by `python-docx` 1.2.0 with built-in styles and no client template; the week view links both. Opening the file in Word and in Google Docs is a manual check still to record.
- **NP.B13 Done** (`b396c87`).

**NP-4 exit met.**
- On copy A, the week plan proposed one Tuesday email, three Instagram pieces with one offer post, and a bank of 11.
- The week's document exported (NP.X1's ledger). On copy B it exported as `research/packs-2026-10/np5/proof/week-2026-10-12-packs.md`.

### NP-5. Prove it

| ID | P | Work | Done when |
| --- | --- | --- | --- |
| NP.X1 | P0 | **The free-model shakedown of the pack path** (main plan section 5.0c), on **scratch copy A**, restored from production's nightly dump. It uses the production image with every worker, and runs every pack stage on free models through the shakedown adapter.<br>When the free finisher fails its contract, as expected, each pack continues inside the shakedown adapter only:<br>• in `missing_only` and `assemble`;<br>• with a canned finisher answer replayed from the probe's output, so check, repair, finalize, review, edit, ready, published and export all run on real data. These runs are recorded as "pipeline path, not model quality".<br>Failure cases: a 402, a budget cap and its release, a worker killed mid-finish, a malformed answer, a missed patch. The first pass covers approve through review and edit; export joins the re-run after NP.B12 | No unclassified finding and no open pipeline defect; each core fix has a test |
| NP.X2 | P0 | **The NP exit test** `tests/test_np_exit_db.py`, on `test_m1_exit_db.py`'s `live` fixture and fake OpenRouter, with synthetic data. It walks through:<br>• Gate 2 approval queues the pack under the `packs` budget;<br>• it finishes into three Reels;<br>• a flagged sentence is repaired;<br>• a surviving flag puts back its sentence;<br>• a written-Reel finding is attested;<br>• an edit locks, and Finish again keeps it;<br>• Ready is blocked by an open finding, then allowed, with the client-permission note still listed;<br>• export, published, and the learning diff.<br>Failure cases: a 402, a cap and its release, a killed worker | Passes in both database suites; CI green |
| NP.X2a | P0 | **One capped live Opus call** through the pipeline's own `chat_body` (strict `json_schema`, `reasoning: medium`, S.B1 routing), with `max_tokens` about 2,000 and costing under USD 0.05 | `usage.cost` came back and was charged to the run, and the strict schema was accepted (or `json_object` is set, with the reason recorded) |
| NP.X3 | P0 | **The paid proof** on **scratch copy B**, a fresh restore that NP.X1 has not touched:<br>• **N2's three briefs** pass Gate 2 under delegation (R55, D12). The team's Gate 2 points from `readings.md` are applied as edits by a named team actor: brief 3's "before considering theirs"; brief 2's untold client words; covers that do not name their subject. Client-permission items are answered "Before posting: WIA confirms the client's okay" and carried as before-publishing notes. Brief 2's Gate 2 quotation clearance concerns Whitney's own words on the call; it is recorded under D12 with the transcript and timestamp as its reference, never an invented client permission.<br>• **One held-out brief** is added: an October card not used to write the prompt (card 4 after its Gate 1 fix, or card 3 reframed), developed with writer v5 (about USD 0.9).<br>• The four packs are made on the internal key under the `packs` cap and read (section 7.3) | Section 7.3's readings pass; cost and time recorded in `research/packs-2026-10/np5-proof.md` |

**NP-5 exit:** the shakedown ledger is clean, the exit test passes, the capped call proves the plumbing, the three packs pass their readings, and CI is green.

**Status (24 October): done.**
- **NP.X1 Done:** `research/packs-2026-10/np5/shakedown-ledger.md`. USD 0; six findings, every pipeline defect fixed with
  a test; the exit holds.
- **NP.X2 Done:** `test_np_exit_db.py`, 7 tests.
- **NP.X2a Done** (`12216e3`): one Opus 5.5 call, USD 0.03, with the strict schema accepted.
- **NP.X3 Done:** `research/packs-2026-10/np5-proof.md`.
  - **Five pack runs, USD 0.47 to 0.69 each:**
    - N2's three briefs;
    - brief 3's retry under the stop rule (`pack-finish.v2` and `pack-check.v2`);
    - the held-out brief (card 4).
  - **The blind reading preferred the pack copy on 16 of 16 pairs.** Two clauses, in two captions, were less faithful
    than the brief, and the team's delegated review edits them (D12, recorded in `np5-proof.md`).
  - **Four defects found and fixed with tests:** `226a6b9`, `870064b`, `8681aeb`, `3f60001`.

**NP-5 exit met.** The phase spent USD 4.23 of its USD 6 on the internal key, and USD 0 on the Client key.

### NP-6. Production (the owner's go-ahead, D13)

| Step | Work | Done when |
| --- | --- | --- |
| 1 | Set the variables first (`ATELIER_ALLOW_PACK_GENERATION=true` on `api` and `editorial-worker`). Then merge NP's pull requests, and on Railway approve only the newest deployment of each service after checking its commit: `api`, `scheduler`, `editorial-worker`, `bulk-worker`, `intake-worker`, `db-backup`, Frontend | Every service healthy at the merged commit |
| 2 | Take a fresh `db-backup` dump. Then run `storage_cli migrate` (009), `settings apply` with the new keys, and `budgets set` with `packs` at D43f's cap | Settings and budget match Appendix B; the dump's restore check passes |
| 3 | D43g: N2's three briefs go through Gate 2 on production under delegation, with exactly NP.X3's edits and answers, so their approved hashes match the proof's | Each approval carries its delegated label (R55); no invented permission reference |
| 4 | Their packs. **Replay the proof:** copy NP.X3's saved pack responses (`pack-cache`) into production's artifact store, so identical requests give identical packs at USD 0. If the hashes differ, the packs are made live, and a pack failing its reading switches to `missing_only` before the Loom. Read them, and check the screens on production at desktop width | Three packs `in_review`, read and recorded in `research/packs-2026-10/production.md` with run ids and cost |
| 5 | Record the main plan's NP row, status table and Appendix D, and update DEPLOYMENT.md | Recorded |

**NP-6 exit (Phase NP's go-live exit):** section 11. Then N4 starts:
- the October backlog;
- the Fathom collector;
- 7.X1, whose brief approval now makes a pack too.

The Loom is recorded on production with the packs in it. It shows the before-publishing notes as they are.

**Status (24 October): done; NP-6's exit, section 11, holds.** The record is `research/packs-2026-10/production.md`.

**Step 1.** `ATELIER_ALLOW_PACK_GENERATION=true` was set on `api` and `editorial-worker`. PR #17 merged (`f1576d0`). Then
the newest deployment of each of the seven services was approved after checking its commit: `api` first, whose
pre-deploy step ran migration 009 at 15:37 UTC.

**Step 2.** First a fresh dump (`atelier-20261024T152922Z.dump`: 41 tables, 12,632 rows, migration 008). Then the
settings of record and `budgets set packs 6.00/60`. A diff of every settings row against scratch copy B showed only the
budgets and the pack profiles differing.

**Step 3.** N2's three briefs went through Gate 2 with exactly the proof's actions file. Each approval carries its
delegated label, and no permission reference was invented. Two problems arose and were fixed:
- **A repeated sentence.** Resumed runs of `gate2.py` applied brief 2's Reel-script edit three times, because its new
  text contains its old text. The team (D12) edited the approved brief back to the proof's copy and approved it again.
  `gate2.py`'s resume rule is fixed.
- **Approval order.** Parallel runs had brief 2's approval refused ("Related prior use changed") until it was reviewed
  after brief 1's approval, as on copy B.

**Step 4: the packs replayed.** The first replay missed. Editing two contract docstrings (`870064b`) had changed the
pack stages' wire schema. PR #18 (`c381095`) restored them and pins the four schema hashes in a test. After that:
- briefs 1 and 2 and brief 3's first pack replayed at USD 0, with every piece, note and client quote identical to the
  proof's;
- brief 3 was finished again live under v2 (USD 0.60, 0 of 27 flagged), because the proof's v2 answers had been saved
  under the edited schema.

The team's delegated review (`np5/review-production.json`) then edited four clauses: the blind reading's two, brief 1's
stance caption, and one certainty in brief 3's stance caption.

The three packs are in review with no blocker. The week plan proposes Monday's Reel, Tuesday's email, Wednesday's
carousel and Friday's Reel, plus a bank of 11. The week's document exports (80,580 characters). Production's pack spend
was USD 0.60, and the phase's was USD 4.83 of USD 6.

**Not done: the screens' visual check on production.** It needs a WIA sign-in, and no password is entered by the agent.
The screens are unit-tested, built and deployed (`f1576d0`).

**Step 5.** Recorded in this plan, the main plan (revision 8.9), DEPLOYMENT.md and `research/packs-2026-10/`.

### NP-7. First live weeks

| ID | P | Work | Done when |
| --- | --- | --- | --- |
| NP.B14 | P0 (first week) | **The post-recording pass** (RQ18):<br>• on a Reel, "Paste what you said": the recorded take's transcript becomes the Reel's script, word for word and locked;<br>• `pack_caption.v1` (Opus 5.5, medium) writes the caption and three cover options from what was said and the brief's claims;<br>• the check and the deterministic checks run, and the pack version returns to review.<br>About USD 0.10 to 0.15 from `packs` | With a recorded take, the caption and covers keep to what was said and the said script is unchanged. Ready before Whitney's first recorded Reel is posted |
| NP.B15 | P1 | **Finish again with a permission.** Whitney grants a "stronger with permission" item, or states an attested fact (R57), in the pack. The finisher re-runs (`pack_refinish`) with it as evidence, with locks kept | The probe's brief 1 case (the comparison result) can be granted and appears in the re-finished copy, attested |
| NP.B10 | P1 | **The brief writes three Reels** (D43j; D30 superseded):<br>• writer `v5.1` (a new file) with contract v4, writing three Reels (story, stance, b-roll text) when Instagram is a channel;<br>• the three-Reel schema applies only to `v5.1`, so v5 replays stay byte-identical;<br>• one free-model run and one paid brief with its reading come before `production-settings.json` names it | A new v5.1 brief has the three kinds and passes its reading; N2's v5 briefs still replay at USD 0 |
| NP.X4 | P0 | **The tone loop for packs:**<br>• each week, Whitney's pack edits are read by kind;<br>• a correction given twice becomes a rule candidate (L.B14);<br>• a new finisher profile (`pack-finish.v3`; v2 was NP.X3's stop rule) ships only after the agent's reading of the change on the last live week's packs, replayed from saved inputs (X.2) | Each change has a record from request to release |
| NP.X5 | P1 | **Labelled cases for the check:** WIA's factual corrections on packs become test cases for `pack_check` | Recorded per week |
| Later | P2 | Each only if WIA asks:<br>• calendar dates in the app (the `calendar/` package, with its blockers moved to v2);<br>• a Stories sequence for a chosen piece;<br>• ad and trial variants;<br>• a cut sheet when the source is WIA's own footage | — |

**Status (26 October): done; every item below is built, tested, proved and named in `production-settings.json`.** The
record is `research/n5-2026-10/README.md`.
- **NP.B14 Done** (`5986284`, `2fd266b`, `737e060`): "Paste what you said" on Reel 1 or 2 (`POST /packs/{id}/pieces/{key}/recorded`)
  makes the take the script word for word, locked; `pack-caption.v1` writes the caption and three covers; the check reads
  them with the take as a source, and the take stays on the pack for every later check. Proved on copy B: the script is the
  take, the caption keeps her planned tense, 0 of 12 flagged, USD 0.27. The first real recorded take is WIA's to paste.
- **NP.B15 Done** (`5986284`, `2fd266b`): Grant on a "stronger with permission" item, or a stated fact, then "Finish again
  with these" (`POST /packs/{id}/refinish`); `pack-refinish.v1` uses each as attested evidence and the grants stay on the
  pack. Proved on copy B on the probe's brief 1 case (the comparison result), a stand-in grant: the result appears,
  attested, 0 of 31 flagged, USD 0.62.
- **NP.B10 Done** (`e8efa9c`, `82114ce`): writer v5.1 writes story, stance and b-roll text Reels; v5's request is pinned, so
  N2's briefs still replay at USD 0. One free-model run (research failed on the free model, K70), one paid brief (card 3,
  USD 1.02) and a blind reading (narrowly preferred against the standard; captions lack "-Whitney", the finisher's job).
- **NP.X4 Done** (`4fa13c0`): the tone loop end to end (`test_x2_tone_loop_db.py`) and its runbook; `pack-finish.v3` ships
  only when WIA's pack edits call for it, after the agent's reading, as the runbook says.
- **NP.X5 Done** (`072ef6d`): the proof's pairs 2 and 6 are the first labelled cases (`research/packs-2026-10/check-cases.json`),
  scored by `packs/check_cases.py`, which also lists a week's person-made pack edits as candidate cases.
- **`pack-check.v3` Done** (`521367e`): the approved brief's WIA perspective and central point among the check's sources.
  On copy B it caught both labelled cases and credited 22 approved-stance statements without flagging one (USD 0.29).
- **NP.B12's .docx Done** (`d596cf2`): opened in LibreOffice Writer; Word and Google Docs are a manual check still open.

---

## 7. Verification

### 7.1 Free models first (NP.X1)

The main plan's section 5.0c applies unchanged:
- a scratch database marked shakedown;
- the production image;
- free models only through the shakedown adapter;
- every failure triaged as a pipeline defect, handled as designed, or a free-model artefact.

**No prompt, schema, check or retry changes on free-model evidence alone (K70).** The canned-answer path lets the stages after the finisher run on real data without depending on a free model's quality.

### 7.2 The exit test and the capped live call (NP.X2, NP.X2a)

See section 6. The exit test covers the pack path end to end, through the real live provider to a fake OpenRouter, in both database suites on every pull request. The capped call proves that Opus requests settle their cost and accept the schema before any paid pack run.

### 7.3 The paid proof and its readings (NP.X3)

The implementing agent does the readings, recorded as delegated (D39, R55). For each of the four packs (N2's three briefs and the held-out brief):

| Reading | Passes when | If it fails |
| --- | --- | --- |
| **Composition and checks** | 1 email, 3 Reels of the three kinds, 1 carousel. No open blocking finding after finalize (before-publishing notes are not findings) | Fix the defect at its cause with a test; retry once (stop rule) |
| **Fidelity** | The re-check leaves nothing unsupported or guardrail. The agent's own reading of every piece against the evidence finds none of:<br>• a change of who did what;<br>• a quote out of its moment;<br>• a hinted kept-out detail;<br>• an invented reflection outside `personal_lines`;<br>• a hedge made certain;<br>• a widened commitment | Tighten the prompt (a new profile) and retry once. A pack still failing ships in `missing_only` |
| **The standard** (sections 4.2, 4.3) | Each piece meets its rules on the agent's reading:<br>• the email skeleton, with personality;<br>• spoken scripts;<br>• captions in Savannah's order, with the reader's world;<br>• the carousel shape, with stacked slides;<br>• specific first touches;<br>• US spelling;<br>• at most one contrast a piece, and no kickers | As above |
| **Better than the brief** | A subagent's blind reading of each paired piece's brief copy and pack copy, shuffled under neutral letters. The reader first reads Whitney's finished pieces (KB 15, 18, 19) and the house style. The pack copy must be preferred on **at least 13 of the 16 paired pieces** (three N2 packs of four pieces each, plus four of the held-out brief's pieces) and never be worse on fidelity. **Each written stance Reel must pass the standard reading on its own** | The finisher stays on only where it wins, set per pack through `missing_only`, and recorded |
| **The held-out brief** | Its pack passes every reading above, so the result does not rest only on the briefs the prompt was written from | Recorded as a limitation in `np5-proof.md` and D26; the prompt is fixed in NP-7 |
| **W3 to W8** | None of Whitney's 20 October patterns recurs | As above |
| **Cost and time** | At most USD 0.85 and 6 minutes per pack, at medium effort | Recorded; the cap and the estimate are adjusted |

**Stop rules** (main plan 5.0c):
- A paid step that fails in a way the shakedown should have caught stops the run. It is reproduced on free models or offline, fixed, and retried once.
- No paid step is retried more than once.
- A run whose estimate would pass the `packs` cap is not started. Opus now has a price, so this works (NP.B5).

**Subagents.** The blind reading starts only after both track subagents have stopped, or it takes one of the two slots.

**Expected cost.**

| Item | USD |
| --- | --- |
| The capped call | under 0.05 |
| The held-out brief | about 0.9 |
| The four proof packs | 2.2 to 3.4 |
| Production's three packs | 0 when replayed, up to 2.6 if made live |
| **Total** | **about 3.2 to 6.9**, on the internal key, within its USD 15 a week |

---

## 8. Order of work, cut list and fallbacks

The owner sets the timing. The order and its dependencies:

1. **The frozen contract** (Track A): `packs/contracts_v2.py`, the response models, OpenAPI, `schema.d.ts`, migration 009. Both tracks build on it.
2. **In parallel, at most two subagents:** Track A (NP.B1 to NP.B6) and Track B (NP.F1 to NP.F3). The main session builds NP.B7 to NP.B9, the quality-critical path, and integrates.
3. **NP.X1** (free models, scratch copy A) and **NP.X2a** (the capped live call), once NP-1 and NP-2 are in.
4. **NP.X2, NP.F4, NP.B11 to NP.B13**, then **NP.X3** and its readings, with the blind reading after the track subagents stop.
5. **NP-6**, production, with the owner's go-ahead.
6. **N4** (the main plan): the October backlog, the Fathom collector, 7.X1, the Loom.
7. **NP-7** with the first live weeks.

**Cut list.** Each item can follow in NP-7 without holding back go-live:
1. The .docx export. The team renders the first week from the Markdown with `research/v2-reassessment-2026-10-20/tools/packs2docx.py`.
2. The week view's screen (NP.F4). The week plan is in the export, and Published is on each piece.
3. Learning from pack edits (NP.B13). The edits are kept in their versions either way.
4. "Finish again" in the screen. The API route stays.

**Never cut:**
- the start on approval;
- three Reels;
- the fidelity loop;
- the deterministic checks, consent included;
- **editing with locks**;
- Copy;
- Ready with its conditions;
- the `packs` budget and the model plumbing;
- the Markdown export;
- production.

**Fallbacks.**

| If | Then |
| --- | --- |
| The finisher fails its readings on a pack after one retry | That pack ships in `missing_only`: the brief's copy verbatim, plus the missing Reel written and checked. Recorded as such |
| The finisher fails on all three | `packs.finish_mode = missing_only` for go-live. The finisher returns in NP-7 after a fix, recorded |
| The full editor (NP.F2) is not ready when the rest of NP is | `PATCH` ships with a plain text box per field, with locks and versions kept. Comparing and reverting move to the first live week |
| Strict schemas are refused for Opus (NP.X2a) | `json_object` with local validation, recorded |
| The owner's go-ahead for production arrives late | NP-6 is rehearsed in full on scratch copy B, and production follows the moment the go-ahead arrives; N4 follows it |
| The `packs` budget is not raised (D43f) | A cap taken from refreshes (USD 0.50), in `missing_only`. Finishing waits for D43f |

---

## 9. Decisions

**All decided by the owner on 24 October:** D43a as stated, and D43b to D43j as recommended below (the main plan's section 7.2).

| # | Decision | Decision (as recommended; the owner, 24 October) | Blocks |
| --- | --- | --- | --- |
| **D43a** | What a pack contains | **Decided by the owner (24 October): 1 email, 1 carousel, 3 Reels** (story, stance, b-roll text), each Reel and the carousel with its caption. D30's two-Reel allowance is superseded | — |
| D43b | A finishing step after Gate 2, and its trade-off | **Yes:** an Opus 5.5 finisher, a Sonnet 5.5 check, one repair and re-check, and sentence-level put-back (section 5).<br>**The trade-off:** Gate 2 approves the strategy and every person's line. The rest of the copy is a draft the pack finishes, labelled as such at Gate 2. No model touches a line a person wrote.<br>**Switch-backs:**<br>• Sonnet as the finisher (a third of the cost, little gain);<br>• `missing_only`;<br>• `assemble`;<br>• finishing before Gate 2 (Gate 2 approves final copy, at a higher cost) | NP-2 |
| D43c | When a pack starts | **On Gate 2 approval of a v4 brief, by itself.** "Create content pack" is there for a retry, or for a brief approved while packs were off | NP.B2 |
| D43d | Review in the pack | **In the pack, a reviewer can:**<br>• edit any line, kept word for word;<br>• clear new client quotes;<br>• attest flagged sentences;<br>• mark before-publishing notes done (client permissions and quotes are notes, never gates);<br>• mark the pack Ready to publish, and each piece Published.<br>**No feedback refresh in the pack** (the 20 October promise). "Finish again" takes no new instruction. NP-7's post-recording pass and permission re-finish take a person's own input.<br>This is a light review step, not a gate anything downstream waits on | NP-1, NP-3 |
| D43e | Planning, scheduling, publishing | **A proposed week plan, computed on read:** one Tuesday email, three Instagram pieces, one offer post, and a bank. Dates are read-only at go-live.<br>**No scheduling into tools and no publishing.** Editing dates in the app comes later, with the calendar, if WIA asks | NP.B11 |
| D43f | The budget | **A `packs` purpose at USD 6.00 for the week of 26 October, then USD 3.50 a week.** The first week's cap covers the proof's replayed packs (no cost), WIA's first packs, 7.X1's, two post-recording passes and one Finish again.<br>Production's weekly caps become USD 11.00, then USD 8.50, on the internal key (limit USD 15 a week). A pack costs about USD 0.55 to 0.85 at medium effort.<br>Not raising the cap means `missing_only` packs inside the existing caps, a quality trade-off | NP.B5, NP-6 |
| D43g | N2's briefs on production | **Revised at the owner's direction (24 October): the team takes N2's three briefs through Gate 2 under delegation (R55).**<br>• the team's Gate 2 points from `readings.md` are applied as edits by a named team actor;<br>• client-permission items are answered "Before posting: WIA confirms the client's okay" and carried as before-publishing notes, never a gate;<br>• brief 2's quotation clearance covers Whitney's own words and is recorded under D12 with the transcript reference; no client permission is ever invented.<br>Their packs are waiting at delivery and appear in the Loom, each approval and edit with its delegated label | NP-6 |
| D43h | The week's document | **Markdown at go-live, and the .docx in NP if time allows.** Otherwise the team renders the .docx for the first week | NP.B12 |
| D43i | The post-recording pass | **In the first live week** (NP.B14), ready before Whitney's first recorded Reel is posted | NP-7 |
| D43j | The brief writes three Reels | **Writer v5.1 in NP-7, after its own reading** (D30 superseded). Until then the finisher writes the missing stance Reel | NP.B10 |
| D26 (main plan) | What to tell WIA | **Add three points:**<br>• packs are the system's output, finished by a step that keeps her lines word for word;<br>• three packs are waiting, approved by the team under delegation, with any client's okay listed as a before-publishing note;<br>• the "stronger with permission" items show where her permission would make a story land harder | Delivery |

---

## 10. Risks

| # | Risk | Effect | Mitigation | Status |
| --- | --- | --- | --- | --- |
| K75 | **The finisher drifts from the record** after a person approved the brief | A false or unapproved claim in copy WIA posts | The story constraint and fidelity rules; check, repair and re-check; deterministic quote, novelty, consent and composition checks; sentence-level put-back; open findings on written Reels; quotes and permissions cleared at review; every change visible against the brief | New (probe: 4 to 12 flags a pack before repair, 0 after) |
| K76 | **The model check is noisy** (3 flags, then 9, on the same pack) | Misses, or false flags that cost a repair or block Ready | Version 2's sources and rules; person-written and personal lines skipped; treated as a net, not the gate; an edit or an attestation clears a finding; WIA's corrections become test cases (NP.X5) | New |
| K77 | **Two days to build, prove and deploy** | Packs late, or weak | The frozen contract first; the quality path in the main session; the cut list; the fallback modes; replay to production; stop rules | New |
| K78 | **Budget** | A pack waits for money | The go-live week's cap (D43f); Opus priced, so the cap holds before sending; waiting with a reason; `missing_only` inside existing caps | New |
| K79 | **The story's strength is capped by the brief's keep-out items** | Packs stay abstract where the brief removed the turn (brief 1) | "Stronger with permission" at review; Gate 2 permissions and attested facts; NP.B15 | New |
| K80 | **The expectation gap** (K60) | System packs judged against the hand-built v2 | The finisher closes most of the craft gap; D26; R58 labels; the held-out reading | Carried |
| K81 | **Three emails a week against a one-email cadence** | Too much at once, or emails lost | The week plan banks the rest for later Tuesdays | New |
| K82 | **Review fatigue:** Gate 2 plus the pack | Whitney stops reviewing | Gate 2 focuses on the strategy (copy labelled draft); the pack puts the places she always rewrites first (RQ20); Copy all and the week document | New |
| K83 | **A free-model quirk shapes the pack core** (K70) | Paid packs degrade | Section 5.0c's isolation; canned answers for the path; no core change on free evidence | Carried |
| K84 | **Consent invented under delegation** | A story or quote posted without the client's okay | A client's permission is a before-publishing note on every pack and in the export; the team never invents a permission reference; Whitney's own quotes are cleared under D12 with the transcript reference; delegated labels | New (review B4; revised 24 October) |
| K85 | **A new model's plumbing** (Opus: temperature, usage, price, effort, schema) | Costs uncounted, caps bypassed, requests refused, effort and cost doubled | NP.B5's plumbing with tests; NP.X2a's capped live call before any paid pack | New (review I1, I2) |
| K86 | **Delegated work learned as WIA's** | Rules drawn from the team's or the model's text | Delegated and system-made versions excluded from mining (NP.B13); delegated labels on locks and approvals | New (review I16) |

---

## 11. Definition of done for Phase NP

On production:
1. **Start.** Approving a v4 brief at Gate 2 creates its content pack by itself, within the `packs` budget, in about 4 to 6 minutes when no other pack is running. A budget wait or a failure shows its reason and can be retried.
2. **Composition.** Every pack has 1 email, 3 Reels (story, stance, b-roll text) and 1 carousel, each Reel and the carousel with its caption, in the house style.
3. **Fidelity.**
   - No unsupported or guardrail statement survives finalize in a piece from the brief.
   - A flag on a written Reel is open until a person edits or attests it.
   - Quotes are exact and attributed; whether each sits in its moment is judged by the fidelity check and the review.
   - Names follow consent.
   - Client quotes and client-permission items appear as before-publishing notes; no permission reference is ever invented.
   - Every line a person edited is word for word.
4. **Review.** Whitney can copy each piece and the whole pack, edit any line (kept word for word, versioned), see what the finisher changed, use the brief's line, mark the pack ready and mark each piece published.
5. **The week.** The week plan proposes one Tuesday email, three Instagram pieces with one offer post, and the bank. It appears in the week view, or, if that is cut, at the top of the export. The week's pack document exports unabbreviated.
6. **Proof.**
   - The proof's three packs (two N2 briefs and the held-out brief) passed section 7.3's readings and are recorded.
   - The NP exit test passes.
   - CI is green.
   - Packs replay at USD 0.

**Met on 24 October** (`research/packs-2026-10/production.md`).
- **1:** each approval created its pack; a failed replay waited with its reason and was retried. A live pack takes 2 to
  6 minutes.
- **2 and 3:** the composition and the fidelity loop held, with the team's four delegated edits.
- **4:** in the API and the screens' tests. The visual check on production waits for a WIA sign-in.
- **5:** the week plan and the export on production.
- **6:** NP.X3 in `np5-proof.md` covers the proof's packs (N2's three briefs and the held-out brief). The NP exit test
  passed, CI was green on PRs #17 and #18, and production replayed the proof at USD 0.

**Then:** N4, and the first live weeks with NP-7.

**Not required for NP:**
- scheduling or publishing into any tool;
- designs;
- Stories, Threads or ad variants;
- a cut sheet for WIA's own footage;
- writer v5.1 (NP-7).

---

## Appendix A. Requirement-to-item trace

| Requirement | Items |
| --- | --- |
| RQ1 approve the brief, then the pack | NP.B2, NP.F3 |
| RQ2 the composition | NP.B1, NP.B7, NP.B4 (composition), NP.B10 (NP-7) |
| RQ3 Copy | NP.F1 |
| RQ4 edit, kept word for word; no pack feedback refresh | NP.B3, NP.F2, D43d |
| RQ5, RQ21 the week's document | NP.B12 |
| RQ6 carousel copy only | NP.B7 (no design fields), NP.F1 |
| RQ7 three a week, the bank | NP.B11, NP.F4 |
| RQ8 repeat window; RQ9 emoji | NP.B4 (week warnings) |
| RQ10 CTAs | NP.B7 (`no_offer_ending`), NP.B11 |
| RQ11, RQ12 voice; not how-to | NP.B7, NP.B4 (DIY drift) |
| RQ13 first touch | NP.B4 (E.B34 on the pack) |
| RQ14 Instagram and Facebook | No separate copy; the pack's pieces serve both |
| RQ15 the tone tracker | NP.B13, NP.X4 |
| RQ16 live before N4, the Loom, the go-live week's packs | NP-6, D43f |
| RQ17 the week's cadence | NP.B11 |
| RQ18 the post-recording pass | NP.B14 |
| RQ19 refine from the anchor | NP.B7 |
| RQ20 the places she always rewrites | NP.B7 (cover alternates, subject options), NP.F1 (field order) |
| The export study's R2 (reuse the brief's copy; never rewrite approved lines) | D43b's trade-off: person-written lines are never touched; edit mode, not fresh writing |
| The export study's R4 (do not maximise volume) | Fixed composition; no clip splitting; the bank |
| The export study's R7 (distinct openings across the week) | NP.B4's week checks (hooks, covers, subjects) |
| The export study's R10 (cut sheet for existing footage) | Later, if WIA asks; `existing_clip` Reels keep the brief's copy |
| The export study's R16 (who approved what, and when it went out) | NP.B3 (decisions with `item_kind = pack`; published captures) |

## Appendix B. Settings and production values

| What | Value | Where |
| --- | --- | --- |
| `features.packs` | `true` | `production-settings.json` |
| `models.pack_writer` (existing key: the finisher and the repair) | `anthropic/claude-opus-5.5` (switch-back `anthropic/claude-sonnet-5.5`) | `production-settings.json` |
| `models.pack_review` (existing key: the check and re-check) | `anthropic/claude-sonnet-5.5` | `production-settings.json` |
| `models.reasoning_effort.pack_writer`, `.pack_review` | `medium`, `medium` | `production-settings.json` |
| `prompts.profile.pack_finish`, `pack_check`, `pack_repair`, `pack_caption`, `pack_refinish` | `2026-10-25.pack-finish.v2`, `2026-10-26.pack-check.v3`, `pack-repair.v1`, `2026-10-26.pack-caption.v1`, `2026-10-26.pack-refinish.v1` (every earlier profile stays selectable for replay) | `production-settings.json` |
| `packs.finish_mode` | `finish` (also `missing_only`, `assemble`) | `production-settings.json` |
| `budgets.weekly_usd.packs`, `budgets.weekly_calls.packs` | USD 6.00 for the week of 26 October, then 3.50; 60 calls (D43f). A post-recording pass measured USD 0.27 and a permission re-finish 0.62 | The database, `storage_cli budgets set` |
| `ATELIER_ALLOW_PACK_GENERATION` | `true` on `api` and `editorial-worker` (`storage_config.py:92` accepts only `'true'`) | Railway |
| Opus 5.5 in code | `NO_TEMPERATURE` (`llm/request.py`); `MODEL_PRICES_USD_PER_MILLION` 4.00 / 20.00 (`costs.py`) | NP.B5 |
| Migration | `009`: `content_packs.content_body`, `content_hash`; `pack` added to `decisions.item_kind` | `backend/migrations/` |
| Writer | `v5.1` with contract v4 since NP.B10's reading (26 October); `v5` the switch-back | `production-settings.json` |

## Appendix C. Changes to the main plan and the prompts (revision 8.7)

- **"Direction" and "Start here":** packs come before N4 (the owner, 24 October); the composition is decided; this plan is named as NP's detail.
- **Section 5.0b, Phase NP's row:** its items, its exit (section 11 here), and the order NP, then N4, then N5.
- **Section 6:**
  - pack editing in the Atelier is in scope (the 20 October promise);
  - feedback refresh after Gate 2 stays out, except NP-7's two person-started passes (NP.B14, NP.B15);
  - scheduling and publishing stay out.
- **Section 7:** D43 split into D43a (decided) and D43b to D43j (recommended); D30 superseded.
- **Section 8:** K73 updated; K75 to K86 referenced here.
- **Appendix A:** 5.B13 replaced by NP's items.
- **Appendix B:** R56 revised. The brief carries draft copy, which the pack finishes; every line a person wrote is kept word for word.
- **Appendix D:** revision 8.7's rows.
- **`Implementation-Prompts.md`:** prompt 4 filled in for NP from this plan, with no placeholder left.

## Appendix D. The independent review and what changed

An independent adversarial reviewer (a subagent of the planning session) read this plan's draft against:
- the code at `3848f03`;
- both transcripts;
- the probe and the survey;
- the main plan's revision 8.7 edits.

It found 6 blocking, 22 important and 15 minor issues. All were applied:

| Finding | Change |
| --- | --- |
| B1 the live switch accepts only `true` | `ATELIER_ALLOW_PACK_GENERATION=true` everywhere; NP.B2 tests the mode |
| B2 no home for pack-level data; no pack decision kind | Migration 009 (section 5.3); states derived; decisions with `item_kind = pack` |
| B3 flattened field shapes break locks, checks, revert and diff | Pieces keep the v4 leaf shape (section 4.2); locks translated by Reel index; the locked-carousel rule |
| B4 delegated approval would record client permission | The rule in 4.5: no invented permission; revised at the owner's direction so that client permission is a before-publishing note, never a gate, and all three N2 briefs go through Gate 2; K84 |
| B5 the finisher's inputs are not in the hand-off view | Hand-off view v2 (section 5.2); the pack reads only v2; R56 kept |
| B6 a written Reel's finding could never clear | Findings attached to sentences; an edit or an attestation clears them; the attest route |
| I1, I2 Opus plumbing and effort | NP.B5's plumbing; medium effort; NP.X2a; the `token_budget` step removed; K85 |
| I3, I4 the go-live week's budget; frozen stage lists | USD 6.00, then 3.50; every NP-7 stage registered now |
| I5 writer v5.1 unproven; replay break | Moved to NP-7 with its own reading; schema gated on `v5.1` |
| I6, I7 shakedown coverage; re-approving on one copy | Canned-answer path; scratch copies A and B |
| I8, I9 an overloaded first build stage; three subagents at once | Frozen contract first; the quality path in the main session; the blind-reading slot rule |
| I10 repair and put-back against locks | `paths.restore` after the repair and in finalize; locked lines never repaired; sentence-level put-back |
| I11 consent rules missing | `public_copy_checks` and `copy_quote_checks` blocking on the pack |
| I12 checks promising more than they can | "In its moment" moved to the model check and the review; novelty defined; the v2-pack test limited |
| I13 client text in test fixtures | Synthetic fixtures; real-text checks read `research/` at run time |
| I14 the 12-of-15 threshold | At least 13 of 16 paired pieces (three N2 packs and the held-out brief); written stance Reels read on their own |
| I15 a read-only fallback breaks a promise | Replaced by a plain-text editor fallback |
| I16 delegated work mislabelled and learned | "The team's Gate 2 points"; a named team actor; delegated labels; excluded from mining; K86 |
| I17 capture references collide | Pack captures use `pack:<brief_id>:<piece_key>`; the brief page's capture is hidden once a pack exists |
| I18 piece mapping for other shapes | Mapping by kind; duplicates; `existing_clip`; v4-only start; anchor remapped |
| I19 concurrency and supersession | Edits and Finish again refused during a run; new runs supersede; runs bind to the approved hash |
| I20 production repeats the paid run | The proof is replayed to production; a fallback if made live |
| I21 the design tension not put to the owner | D43b states the trade-off; R56 revised; section 6's exceptions named |
| I22 the proof is not independent of the prompt | A held-out brief in NP.X3 |
| M1 to M15 | Fixes:<br>• tab order stated;<br>• RQ14 and the study's requirements traced;<br>• NP-1's exit on a three-Reel brief;<br>• D43e aligned;<br>• one cost figure;<br>• flow budget 12;<br>• the prefix excluded from the character limit;<br>• variables set before deployments, and a dump before 009;<br>• v1 list and detail replaced, and the state filter changed;<br>• serial timing stated;<br>• `python-docx` added, with no client template;<br>• the finisher's notes kept apart from the brief's five, and readiness measured at pack level;<br>• week findings computed on read;<br>• the survey commit noted, and stale main-plan lines refreshed;<br>• the approval authorises the start |
