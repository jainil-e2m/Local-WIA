# Content Atelier: Implementation Plan Through Brief Generation and Content Packs

**Date:** 25 October 2026 · **Revision:** 8.13, Phases N6, N10, N7 and N11 done (reliability, autonomy, the Sunday schedule from 1 November, the benchmark, last week regenerated on production; the screens realigned with the mockup last); 8.12, Phase N8 done (evidence and account memory): identities with aliases, pronouns, staff dates and never-name and never-link flags enforced in cards, briefs and packs; internal meetings admitted as team practice (D24) with scene profile v4; account memory beside a client story card at both gates and in writer v5.2's evidence; founder notes as seeds linked to their call, in strategist v8 and the review document; every Zoom transcript dated to its day or its week; the Funktastic chain's golden fixture measured on production; strategist v8, scene profile v4 and writer v5.2 in the configuration of record; 8.11, Phase N5's system side and NP-7 done: the system is ready for the WIA team to use (the post-recording pass, finishing again with a permission, `pack-check.v3` with labelled cases, writer v5.1, the week's .docx, brief ratings at Gate 2, the week's measures, the tone loop end to end, the caps for a week of use, production current with the week's cycle); WIA's own use and personal accounts (X.1, the owner's) remain; 8.10, Phase N4 done: the October backlog imported, 7.X1's live check end to end on production (a card edited and refreshed, a brief developed, edited, refreshed and approved, its pack finished, edited and exported) and 6.C3; the Fathom collector deferred to N7 and the Loom dropped (the owner, 25 October); 8.9, Phase NP done: content packs built, proved and live on production (NP-1 to NP-6, 24 October; the content-packs plan revision 1.2); 8.8, the owner's direction: N8 is core, every WIA-side question is decided under the delegation (section 7.2), client permission is never a system gate, and phases come in priority order with dependencies, never days; 8.7, content packs planned: Phase NP's detail is in `Content-Atelier-Implementation-Plan-Content-Packs.md`, after the owner set the composition (1 email, 1 carousel, 3 Reels) and put packs on production before N4 (24 October); 8.6, Phase N3 on production and Command Center's sign-in (S.C1) live (24 October); 8.5, N2 completed and the brief-done checkpoint reached (24 October), on revision 8.4's direction of 23 October (content packs go live on 27 October; Slack out; a short after-go-live list) · **Status:** the plan of record · **Basis:** revision 8 rests on `main` at `130e09b`; revision 8.1 records the build merged at `51db019` (section 5.0a); revision 8.3 records the free-model shakedown (N1) and the minimal paid delivery run (N2) of 23 October, every claim below checked against the code, the tests, the research records and the client's words, except what section 1 lists as unverifiable while Railway is out of reach.

**Direction (the owner, 23 October; revision 8.4).**
- **27 October is go-live for the whole system, content packs included,** not only briefs.
- **The brief is the step toward packs.** It is finished as soon as it reaches go-live quality, at the **brief-done checkpoint** (section 5.0a), and pack work starts there.
- **What packs must do (D43).** The owner set the composition on 24 October: every pack is 1 email, 1 carousel and 3 Reels. Packs go live on production **before N4**. The rest of D43 (D43b to D43j) was confirmed by the owner the same day, as the content-packs plan (`Content-Atelier-Implementation-Plan-Content-Packs.md`, which holds Phase NP's detail) recommends (section 7.2).
- **Slack is out for now:** the digest, one-tap approvals and live Slack intake.
- **After go-live:** a short list (Phases N6 and N7). Everything else is marked optional or not planned (section 5.0b).
- **Unchanged:** phase names; free models first, then one minimal paid run; no paid judge; the fixed 27 October date. The auth layer (S.C1) was the owner's until 24 October, when the owner asked for it to be built: one sign-in and one sign-out for Command Center and the Atelier, live on production.

**Start here (24 October, revision 8.10).** Phases N1, N2, N3, **NP and N4** are done. The **brief-done checkpoint holds**, and **production runs the brief system and content packs** (section 5.0a, "N3 and S.C1"; the content-packs plan's section 6):
- **Production.** Railway runs every service on the restored working copy: N2's cycle and briefs, knowledge base 9 and the configuration of record. A nightly dump replaces volume backups, which need a Pro workspace.
- **Sign-in.** Command Center and the Atelier share one sign-in and one sign-out, with the one standard account `ai@weddingindustryads.com` (S.C1, built at the owner's request).
- **The Atelier.** The Frontend serves the real app on real data at `https://content-atelier.up.railway.app`.
- **Content packs (Phase NP, 24 October).** Approving a v4 brief at Gate 2 creates its pack: 1 email, 1 carousel and 3
  Reels, finished by Opus 5.5 and checked by Sonnet 5.5. WIA reviews each pack, edits it (kept word for word) and marks
  it ready.
  - N2's three briefs went through Gate 2 on production under delegation. Their packs are in review: the proof's packs
    replayed at USD 0, brief 3 was finished again live under `pack-finish.v2`, and the team made four delegated edits.
  - Records: `research/packs-2026-10/np5-proof.md` (the paid proof: the blind reading preferred the pack copy on 16 of
    16 pairs) and `production.md`. The phase cost USD 4.83 of the owner's USD 6.

**Phase NP is done (revision 8.9)**: NP-0 to NP-6, in `Content-Atelier-Implementation-Plan-Content-Packs.md`, with NP-7 in the first live weeks.

**Phase N4 is done (revision 8.10;** section 5.0a, "N4"; `research/golive-2026-10/README.md`**).**
- **The October backlog:** every October call is a document. The calls of 21 to 23 October were imported by hand, normalised, embedded and extracted by production's workers.
- **7.X1:** the whole loop ran through production's API and workers, failure case included: a card edited and refreshed with feedback; a brief started by itself, waited on a spent budget with its reason in words, and was edited, refreshed and approved; its pack was finished, checked, edited and exported. USD 2.79.
- **6.C3:** Command Center's card says Live wherever the Atelier is configured. It has been live on production since 24 October: Command Center PR #4 merged at the owner's request (`be38d25`) and its deployment approved; the production card reads "Live".
- **Deployed:** PR #20 was merged at the owner's request (`main` at `77235ee`, all five CI jobs green) and the newest deployment of each of the seven Atelier services approved; all seven run `77235ee` and the API passes its health check, so the three fixes are on production.
- **The pack screens** were checked on the local copy, signed in on localhost, because nobody holds the shared account's password for production. The check found two layout defects, both fixed.
- **Deferred:** the Fathom collector (6.B1) waits for N7, and the week's calls come in by hand (DEPLOYMENT.md). The Loom is dropped (the owner, 25 October).

**Phase N5's system side and NP-7 are done (revision 8.11, 26 October;** section 5.0a, "N5 and NP-7";
`research/n5-2026-10/README.md`**).** Everything WIA needs for N5's items works on production:
- **Packs:** "Paste what you said" on a face-to-camera Reel writes its caption and covers from the recorded take; an
  approver grants a "stronger with permission" item and the pack is finished again with it, attested; the fidelity check
  is `pack-check.v3` (the approved stance is a source; it caught both of the proof's missed clauses); the week's pack
  document downloads as .docx too.
- **Briefs:** writer v5.1 writes all three Reels; WIA rates briefs at Gate 2 on rubric 2.3a, as cards.
- **The weeks:** `storage_cli week-measures` reads section 4.5's bar for any week; the tone loop runs from a request or a
  repeated correction to an active knowledge-base version with its release record; the caps fit a week of use.
- **Production is current:** the three calls of 21 to 23 October have their cycle (`week_2026-10-20`, three cards at
  Gate 1).
- **Waiting on the owner:** personal accounts for Whitney and Gisselle (X.1). Until then WIA's decisions on the shared
  account carry the delegated label.

**Phase N8 is done (revision 8.12, 25 October;** section 5.0a, "N8"; `research/n8-2026-10/README.md`**).**
- **Identities:** 30 accounts and 61 people from a reviewed list (delegated, D21), every spelling the records use, pronouns
  from evidence, a former team member's leaving date; a never-named identity or a never-link marker (the anonymised case study's
  figures) blocks a card, a brief or a pack; a wrong pronoun beside a named person is flagged. On production 75 calls are
  now tied to their account and their scenes carry its consent.
- **Internal meetings** are evidence of how WIA works (D24): 63 admitted as team practice, extracted under scene profile v4;
  a client name or figure only an internal meeting carries is blocked.
- **Account memory:** a client story card shows its account's state and what happened after its call, at Gate 1 and Gate 2;
  writer v5.2 gets the later records as evidence and keeps claims to what they show.
- **Founder notes** are seeds linked to their call: strategist v8 pairs them or leaves them unanswered, and the review
  document carries the line.
- **Every Zoom transcript is dated:** 63 to the day, 101 to the week of their source folder.
- **Configuration of record:** strategist v8, scene profile v4, writer v5.2, internal meetings included.

**Phases N6, N10, N7 and N11 are done (revision 8.13, 25 October;** `research/n6-n11-2026-10/README.md`, `TASK.md`,
`DECISIONS.md`**),** on the owner's instruction and changed requirements (calls only, no alert emails or Slack, no LLM judge,
the two keys' credits as the ceiling, unattended from the evening):
- **N6:** failure alerts recorded and shown in the app (migration 011), the monthly restore check by itself, E.B24's
  warnings decided, the week's review document as Word.
- **N10:** the autonomy pass (second recordings, accounts from call titles, private matters excluded, an hourly upkeep that
  extracts and embeds new calls and retries its own interrupted jobs, tone changes released by the approver, offer statuses
  in the app, archived weeks), Home's summary, alerts and costs, the schedule in the app, removal on request, the cost
  summary, the role matrix, the browser end-to-end test, the runbook.
- **N7:** the cycle starts by itself every Sunday at 04:00 America/Chicago; the first run is **Sunday 1 November 2026**.
- **N11:** the benchmark on a copy (Week 1 and Week 2 against WIA's notes, ChatGPT's moments and Whitney's finished pieces;
  no judge): strategist v9 adopted; two false blockers in the who-did-what check fixed. Production's last week regenerated
  and taken through both gates under delegation: two packs ready to publish; three failure drills passed.
- **Production** runs on the Client key; the internal key was left untouched (the owner's ceiling).
- **Last:** the screens realigned with the mockup WIA was shown (the owner, 25 October: "unpresentable"), in its own PR.

**Next:** the first scheduled run (Sunday 1 November); X.1 stays the owner's; raise the standing caps when the team starts
developing on a funded key (DEPLOYMENT.md).

**Earlier: Phase N6** (section 5.0b), then N10 and N7 last.
- **N1**, the free-model shakedown, ran the whole M1 exit through the app in the production images. It found and fixed 29 pipeline defects, each with a test, and its exit holds.
- **N2**, the minimal paid delivery run, did the following on the working copy (USD 4.07: 2.36 on the Client key, 1.72 on the new internal key within the owner's ceiling of 2.25):
  - embedded and extracted the October window with scene profile v3;
  - ran the October cycle with strategist v7 and card verification v4 (five cards);
  - wrote three briefs with contract v4 and writer v5, from cards 1, 2 and 5;
  - had every reading pass, so `production-settings.json` names the new configuration and knowledge base 9 is active;
  - had a blind reading rank all three briefs above all three writer v4 briefs of 20 October;
  - checked each brief's hand-off view;
  - showed that a fresh container replays a brief at USD 0.
  - It found and fixed six defects the free models could not show.

**What is left before 27 October:**
1. ~~**Phase NP, content packs**~~ **Done 24 October** (the content-packs plan, revision 1.2): approving a brief creates its pack on production, finished and checked after Gate 2 and edited by hand in the pack.
2. ~~**Phase N4's rest**~~ **Done 24 October** (revision 8.10): the October backlog (6.B18), 7.X1's live check and 6.C3. The Fathom collector (6.B1) moved to N7 and the Loom was dropped (the owner, 25 October).
3. **Phase N5:** delivery on 27 October.

**For Whitney at Gate 2** (not more brief engineering): brief 3 says couples considered "a nearby venue before considering theirs", where the call says couples who could not afford a bigger venue came to them; brief 2 never tells what the client said; several covers do not name their subject (`research/n2-delivery-2026-10/readings.md`).

**Cost.** A brief costs USD 0.86 to 1.06 (N2: 0.86, 0.87 and 1.06, each without its lost or cut-off call), so the weekly briefs cap of USD 1.20 covers one brief a week (D42). The output cap is now 32,000 tokens: a cap never improves quality, it only sets the budget's reserve, so it is set never to bind (K74).

Section 5.0b cuts all pending work into phases N1 to N11, with NP for packs.

**What this revision is.** Revision 8 replaces revision 7.3. It re-audits the whole system through brief generation against the code, the generated packs and their reproducibility, the client demo of 20 October and every earlier finding, and turns what remains into one ordered build path with exit checks. Revision 7.3 (635 KB: item histories, the architecture, rulings R1 to R55, the implementation and verification logs) is archived verbatim at `backend/docs/archive/Content-Atelier-Implementation-Plan-Brief-Generation-r7.3.md`; section references in earlier commits and documents point there. Appendix A says where every item ID went.

---

## Read this first

**What the system must do.** Turn WIA's calls into a weekly set of content ideas that show what WIA knows, how it thinks and how it works, for WIA's ideal client; let WIA choose among them (Gate 1); turn each chosen idea into a brief in WIA's voice that WIA approves without rewriting its point (Gate 2); turn each approved brief into the content pack WIA publishes from (its scope is the owner's, D43); run unattended on production, with every decision recorded; keep learning from WIA's approved work.

**Scope (revision 8.4).** Go-live on 27 October covers the whole system, **content packs included** (the owner, 23 October; D22 is superseded).

**The brief is the step toward packs.** It already carries the finished copy of every asset. Contract v4 writes:
- the email, with its send header;
- each Reel's cover, on-screen hook, script or screens, and caption;
- the carousel's title, slides and caption.

Its hand-off view is the interface a pack stage reads: `GET /storage/briefs/{id}/handoff`, which does not depend on the contract version and can be consumed once Gate 2 approves the brief (`can_consume`).

The brief work therefore stops as soon as it reaches go-live quality, at the **brief-done checkpoint** (section 5.0a), and pack work starts there. WIA's notes on the copy are brief work and stay in scope.

**What packs must do (D43)** is set in the content-packs plan, `Content-Atelier-Implementation-Plan-Content-Packs.md`. Every pack is 1 email, 1 carousel and 3 Reels (the owner, 24 October). It is finished after Gate 2 inside a fidelity loop, edited by hand in the pack and kept word for word, with a proposed week plan and the week's document. The existing `packs/` code (v1 briefs only, five fixed slots) is replaced for v3 and v4 briefs.

**Out of scope:** the client knowledge base, and Slack for now (section 6).

**Where it stands on 22 October 2026.**

1. **The machinery is built and verified** (19 and 20 October; section 2): intake, classified and dated documents, a moments ledger over all 91 included real documents (1,669 scenes, 96.2% verified), the context system and knowledge base version 8, strategist v6, cards with a ledger and Gate 1, brief contract v3 with writer v4 and its checks, Gate 2, run plans, replay. Offline tests pass except two broken by the 20 October mock-data commits; CI on `main` is red since then.
2. **What WIA saw on 20 October was hand-built.** The three v2 packs were loaded word for word into the app's mock flow; nothing on screen called the backend. Whitney said they "definitely look more aligned". No stage of the pipeline has produced output of that kind, and no automated reproduction has been attempted. The method behind v2 is written down (nine steps); four of them have no stage yet, and the current brief writer contradicts a fifth (section 2.2).
3. **There is no live path.** Production has an empty database and the mock Frontend; no API, workers or scheduler; Command Center sign-in accepts anyone (`AUTH_DISABLED=1`). In code: a cycle runs only from the command line; developing a card queues a brief in replay mode, which fails for a new card; Gate 1 has no "refresh with feedback"; Gate 2 edits 5 of 11 to 12 brief sections and its refresh works only for v1 briefs in replay mode; the October calls cannot come through the live Fathom collector.
4. **Delivery is on 27 October 2026** (the owner's decision, D35): WIA goes live on the tool with live calls, editing at every step and feedback-driven regeneration up to the brief, as promised on 20 October, and content packs from the approved briefs (the owner, 23 October; scope D43). Section 5.0 plans every milestone backward from that date.
5. **The OpenRouter keys are nearly empty** (client key about USD 2.98; the internal key resets weekly), and the Railway CLI here is signed out.
6. **23 October: M1's and M2's code is built** (section 5.0a). CI is green again; the real app is the production build; the October calls are documents in the working copy; a cycle runs from the app; developing a card starts its brief live under standing weekly budgets; both gates edit any field, refresh with feedback, keep a person's lines and take attested facts; strategist v7, card verification v4, scene profile v3, brief contract v4 with writer v5, the first-touch and asset checks and knowledge base 9 exist behind settings; the M1 exit test passes offline in a database with a fake provider. Item 3 above is therefore true of production only. What is left is paid or on production: the embedding and re-extraction of the October calls, the paid smoke runs, M3's gate and M4. The owner builds the Command Center auth layer later (S.C1 is the owner's, 23 October).
7. **23 October: N1 and N2 have run** (section 5.0a, "N1 and N2").
   - **N1:** the whole pipeline ran on free models in the production images, on a scratch copy of the working data. That is 50 findings: 29 pipeline defects fixed with tests, 10 handled as designed, 8 free-model artefacts absorbed in the free-model branch.
   - **N2:** the paid delivery run on the working copy, USD 4.07 (Client key 2.36, internal key 1.72). Embedding, extraction, the October cycle and three briefs, with readings that put strategist v7, card verification v4, scene profile v3, contract v4 with writer v5 and knowledge base 9 in force. S.B8 is closed, and six more defects were fixed.
   - **The brief-done checkpoint holds (24 October):** pack work (NP) starts from here.

**The plan in one table.**

| Milestone | Delivers | Exit (checkable) | Effort | Needs |
| --- | --- | --- | --- | --- |
| **M0** Decide and align | A budget, Railway access, the sign-in go-ahead, framing for WIA, WIA's open answers | Decisions recorded (section 7) | Owner, by Thursday 22 October | — |
| **M1** The live path in code (**code built 23 October**; the paid exit run waits for budget) | The October calls in the working copy (first, because M2 and M3 need them); CI green; the real app as a production build; cycles from the app; briefs start on approval under a standing budget; edit any field and refresh with feedback at both gates; attested facts; waiting calls resolved in the app; reliability fixes and failure alerts; the review document | The M1 exit test, failure cases included, passes in the production image on a scratch copy | Friday 23 to Saturday 24 October, three parallel tracks | D36 (about USD 2 for the paid exit test) |
| **M2** Output to the standard (**code built 23 October**; the re-extraction and smoke run wait for budget) | Benchmark v2 packets; the strategy brief as beliefs; scene types for human lines and counter-expected decisions; strategist v7 and card verification v4; brief contract v4 and writer v5; WIA's corrections as rules and checks; knowledge base version 9 | On `main`, behind profile settings, with its tests | Friday 23 to Saturday 24 October, two or three parallel tracks | 6.B18 (the October calls); D34 for KB 19; D36 (about USD 1) |
| **M3** Measure, lock, prove it repeats | The quality gate on benchmark v2 in three samples, the new configuration against the current one; the configuration of record; replay | The gate in section 5 passes and `production-settings.json` names the configuration | Sunday 25 October, about USD 15 | M2; D36 |
| **M4** Production | Backups, the restored working copy, every service including the bulk worker, settings, real sign-in, the real app, live intake, a live end-to-end verification | 7.X1 recorded on production | Monday 26 October | M1; M3's configuration and data; S.C1; the owner's go-ahead (D13) |
| **Packs** (Phase NP; revision 8.4, planned in 8.7, **done in 8.9**) | The pack stage on approved briefs: 1 email, 1 carousel and 3 Reels, finished and checked after Gate 2, edited in the pack, a week plan and the week's document (the content-packs plan) | The content-packs plan's section 11, on production before N4. **Met 24 October** (`research/packs-2026-10/production.md`) | Sunday 25 and Monday 26 October | The brief-done checkpoint; D43 (decided 24 October) |
| **M5** Delivery and the first live weeks | Delivery on Tuesday 27 October; WIA reviews real weeks in the app; tone requests are batched weekly into the knowledge base through the gate | Delivered on 27 October; section 4.5's bar on two consecutive live weeks; WIA's sign-off | From 27 October | M3, M4 |
| **M6** After go-live | A short list: failure alerts by email, the nightly dump, the review document's .docx, the cycle on a schedule (Phases N6 and N7). Everything else is optional or not planned (section 5.0b); Slack is out for now | Per item | — | — |

**The schedule.** Delivery is fixed on Tuesday 27 October (D35), and section 5.0 plans backward from it: decisions and access today; M1 and M2 built in parallel sessions on Friday 23 and Saturday 24 October; M3's gate on Sunday 25; production on Monday 26, with the Loom promised to WIA recorded on the verified production app that evening; delivery on the morning of the 27th. The schedule has no slack, so section 5.0 also names what moves to after delivery and a fallback for each step that depends on someone outside the team.

**Decisions:** none open (section 7.1, revision 8.8). Every WIA-side question is decided under the delegation and recorded in section 7.2; money (funding N11) and production go-aheads (D13) stay the owner's, and so does what the owner tells WIA. Command Center's sign-in (S.C1) is live since 24 October; personal accounts (X.1) wait on the owner's passwords.

### Implementation status (26 October 2026, revision 8.11: N5's system side and NP-7 recorded)

"Built 23 Oct" means built, tested offline and in the database suites, and merged on `main` (section 5.0a has each item's evidence); a remainder that needs a paid call or production is named beside it.

| Phase | Built and verified (19 and 20 October) | Built 23 October | Remaining in this phase | After go-live (M6) or out of scope |
| --- | --- | --- | --- | --- |
| S | S.X2, S.B2 to S.B7, S.B9 to S.B13, S.X1, S.F1 to S.F4 | S.B15 (CI green); S.B8 (N2: the production image wrote a v4 brief live and a fresh keyless container replayed it at USD 0, byte for byte); **S.C1 (24 October, at the owner's request): one sign-in and one sign-out for Command Center and the Atelier, live on production (`f58c6c4`, Command Center `d5b82b5`)** | Personal accounts when WIA names them (X.1) | S.B1's dashboard check (owner) |
| E | E.B3, E.B6, E.B7, E.B9, E.B10, E.B11, E.B12, E.B12a, E.B16, E.B17, E.B19 to E.B26, E.F3, E.X1, E.X2, E.X7 | E.B1 (extension), E.B24 (extension), E.B25 (i) (j) (version 9 active since N2), E.B27 (packets for Weeks 1 and 2), E.B28 (go-live subset), E.B29 (change), E.B30 to E.B34 (in force since N2's readings: E.B30, E.B31, E.B32, E.B33 in `production-settings.json`), E.B3's labelled set; N1 and N2 run (E.B31's delivery window extracted; the minimal gate passed, D40; three briefs, the brief-done checkpoint) | N11 when funded: E.B31 on Weeks 1 and 2, E.B27's October packet and runs, the v7 smoke runs, E.X4; M5: E.X9's system side **done (26 October: cards and briefs rated in the app, labelled WIA's for a WIA reviewer)**; E.F1, E.F2, E.F4 close with WIA's own decisions | E.B5, E.B8, E.B18, E.X8, E.B3's paid judge run (D39), the E.B3 and E.X7 extensions; E.X5 dropped |
| L | L.B3 to L.B11, L.F1 to L.F3, L.X1, L.X2 | L.B11 (profile from settings; skips with a reason in the image), L.B12 (KB 19 under D34's default), L.B14 (repeat corrections); **L.B13 (N8, 25 October: founder notes as seeds linked to their call)** | M4: L.B1, L.B2 production runs; `mining_live` on in `production-settings.json` | L.B13 (no build; ask now), L.B2 (extension) |
| 0 | 0.B3 to 0.B6, 0.B8, 0.B9, 0.B11, 0.B12, 0.F1, 0.F3 | 0.B6's weekly budget renewal; the live-run refusal of profiles left at the rated code default (0.B8); **0.B7 (24 October, N3): every service on Railway, the bulk worker included** | — | — |
| 1 | 1.B1 to 1.B3, 1.B5 to 1.B8, 1.B10, 1.B12, 1.B13, 1.B14, 1.F1 to 1.F5 | 1.F6, 1.F7, the Fathom key fallback; **N8 (25 October): 1.B11's Zoom dates, the 1.B12 extension (identities), the 1.B13 extension (internal meetings as team practice)** | M4: 1.B4, 1.B9 by the restore (D20) | — (done in N8) |
| 2 | 2.B1 to 2.B10, 2.B12, 2.F1 to 2.F3 | Scene profile v3 (with E.B31); cycles over a window from the app (with 3.B2/3.B3); **scene profile v4 (N8); 2.B11's Funktastic chain measured on production (partly done: one golden scene never extracted, archive-wide paraphrase search weak)** | Paid: the v3 re-extraction | 2.B11's remainder (N11); 2.B13 (P3) |
| 3 to 5 | 3.B16; 4.B9, 4.B12, 5.B1, 5.B3, 5.B4 (built in Phase E) | 3.B2/3.B3, 3.B5 (extension), 3.B7/3.F2, 4.B1, 5.B6, 5.B7, 5.F1, 5.F2, 5.F4, 5.F5 (go-live subsets); 5.B14 (Markdown); M1's exit run through the app in the production images (N1, free models, failure cases included; N2, paid, on the working copy) | M5: 5.B2 (closes with WIA's first real approval) | 5.B14's .docx (the pack document's .docx is done, NP.B12); the rest of Phases 3 to 5 (section 5, M6); 5.B13 out of scope |
| 6 | — | 6.B3 (go-live subset; production's caps set 24 October), 6.B18 (built and run: 22 October calls in the working copy; embedded in N2, USD 0.0033); **6.B5 (the Fathom key on production) and 6.B6's nightly dump with its restore check (N3, 24 October: the `db-backup` cron service, in place of Railway volume backups, which need a Pro workspace)** | 6.B4 (after delivery); **6.B18's October backlog done (N4, 24 October)**; **6.C3 done (live on production, Command Center `be38d25`)**; 6.B1 moved to N7 (the owner, 25 October) | The rest of Phase 6 |
| 7 | 7.B3 | 7.F2's build fix; 7.B5's restore rehearsed locally; **N3 (24 October): 7.B1, 7.B2 (one standard account, `ai@weddingindustryads.com`), 7.B5 on Railway, 7.F2 (the Frontend in backend mode on production)** | M0: 7.B4 (ask Jainil); **7.X1 done (N4, 24 October)**; 7.B6's connector step with 6.B1 in N7; M5: 7.X2 (**`week-measures` built, 26 October**; the two live weeks and WIA's sign-off remain) | 7.F1's full audit |

### Where to resume (start here on any machine)

1. **Ground the machine:** prompt 1 of `Implementation-Prompts.md`. Needs Python 3.12 with `backend/requirements.txt` (the repo's `.venv`), Node 22.12 or later (a portable Node 24 is in `atelier-work/tools/` on the owner's machine), Docker with a `pgvector/pgvector:0.8.2-pg17` container, `gh`, the Railway CLI **signed in** (it reports "Unauthorized" on 22 October), and `backend/.env` with the keys (never committed).
2. **Owner first:** M0's decisions (section 7). Nothing paid starts before D36 (or the internal key's weekly reset, 26 October 00:00 UTC).
3. **M1's and M2's code is done, and Phases N1, N2, N3 and NP are done (23 and 24 October; section 5.0a; the content-packs plan).** The brief-done checkpoint holds and production runs the brief system and content packs with one sign-in (S.C1). **N4 is done too (24 October):** the October backlog, 7.X1 and 6.C3 (section 5.0a, "N4"). **N5's system side and NP-7 are done too (26 October):** section 5.0a, "N5 and NP-7". **N8 is done too (25 October):** section 5.0a, "N8". Next: N6, then N10. The collector waits for N7.
4. **M3** was folded into N2 (D40); **M4** is N3 (done) and N4; **M5** follows on 27 October. Production changes need the owner's go-ahead (D13); the Railway CLI is signed in as the E2M AI workspace.
5. Each item follows section 0's conventions; each run adds a row to the logs (Appendix D).

---

## 0. How to use this document

| Section | Contents |
| --- | --- |
| Read this first | Scope, state, the plan in one table, the schedule to 27 October, the status, where to resume |
| 1 | How revision 8 was verified, and what could not be |
| 2 | The verified state: the path from a call to a brief, output quality, the frontend, production, tests, and the corrections to revision 7.3 |
| 3 | The client review of 20 October and what it means |
| 4 | The target: the workflow, the card standard, the brief and asset standard, reproducibility, success measures |
| 5 | The remaining work: the day-by-day schedule to 27 October (5.0), then M0 to M6, each item with its "done when", and each milestone with its exit |
| 6 | What this phase does not do |
| 7 | Decisions |
| 8 | Risks |
| 9 | Definition of done |
| Appendices | A: every item ID and where it went; B: rulings in force; C: configuration for go-live; D: revision history and logs; E: the rubric and brief standards the code cites (sections 2.3a, 2.4, 2.4a), verbatim |

**Priority labels.** P0: the live path or output WIA would accept cannot exist without it. P1: needed for the scoped system to be complete and reliable, not for go-live. P2: hardening. P3: deferred; listed so nobody builds it by accident.

**Item IDs.** Kept from earlier revisions (commits cite them): `S.`, `E.`, `L.` and `0.` to `7.` for the phase, then `B` backend, `F` Atelier frontend, `C` Command Center, `X` cross-system or client work. A **go-live subset** is the part of an older item this phase needs; the rest of that item is in M6. New items in revision 8: S.B15, E.B34, E.X9, L.B14, 1.F6, 1.F7, 5.B14, 6.B18, and the owner and WIA actions X.1 and X.2.

### Where the frontend lives

The Atelier app (`frontend/`) is the only Atelier UI: a React SPA and a Node server that checks the Command Center session and relays an allowlist of routes to the Python API. **Since `b02c54d` (20 October) the default build is the mock flow**; the real app is built only with `VITE_ATELIER_MODE=backend` (M1 makes this the production build). Command Center holds the link and the sign-in hand-off.

### Working an item (developer conventions)

1. **Pick** an item whose prerequisites in its milestone are met. Branch `item/<ID>-<short-name>` from `main`.
2. **Read** the row, the rulings it cites (Appendix B), and its "done when". Resolve ambiguity with the owner first and record the answer in the row.
3. **Code in the right place.** Backend in `backend/backend_pipeline/` (packages as in `README.md`). Prompts are new versioned files in `prompt_templates/`; a released profile is never edited (E.B17). Migrations are new numbered SQL files applied by `storage_cli migrate`. Frontend in `frontend/src`; every route the app calls goes on `frontend/server/allowlist.mjs` with a server test.
4. **Test.** Offline unit tests with the fake provider; the database suites for persistence; frontend unit and server tests. Every "done when" has an automated test or a recorded manual check named in the pull request.
5. **Paid calls** only under a run plan or the standing budget (E.B1, 6.B3), only through the `llm` module with its privacy routing (S.B1), never from tests, always with the cost recorded.
6. **Client data.** Client material only under `research/` and `backend/knowledge_base/` (R48; the CI guard enforces transcript shapes). No raw ChatGPT export in git (R52, D14). Fixtures are synthetic or redacted.
7. **Flags.** Anything a user can see stays behind its flag or profile setting until its milestone exits.
8. **Review.** Pull request titled `<ID>: <summary>`; CI green; the description lists the evidence for each "done when".
9. **Status.** In the same pull request: the item's row (**Done (`sha`)** or **Partly done (`sha`)** with the remainder), the status table at the top, and a log row (Appendix D).
10. **Docs.** When behaviour or configuration changes, update `DEPLOYMENT.md`, `Angle-Prompt-Profiles.md` or the hand-over note; a new setting goes into Appendix C or `DEPLOYMENT.md`. Appendix E is read by `test_rubric.py`: its rubric text changes only with a new rubric version.

---

## 1. How revision 8 was verified

| Area | Method | Result |
| --- | --- | --- |
| Repository | `git pull` of `main` (5 new commits: Jainil's mock-data and mock-UI work of 20 October, `5588578..130e09b`); every branch and pull request listed | `main` at `130e09b`; no open pull requests or issues in either repository |
| Backend against the plan | Every item marked Done on 19 and 20 October checked in code, its default, and its tests; the path from a new call to an approved brief traced through the code | Section 2.1; two stale rows (E.B22, E.B17) corrected |
| Offline backend tests | `pytest` with the repo's `.venv`, database suites excluded | 980 passed, 124 skipped, 2 failed (both from `5588578`; section 2.5) |
| Frontend | Lint, unit tests, server tests, production build with Node 24; the mock switch and the demo data traced | All pass; the demo data equals the v2 packs word for word |
| CI | `gh run list` on `main` | Red since `5588578` on the same two tests |
| Research and reproducibility | Both research folders read in full (the diagnosis, the reproducibility method, the findings, the notes, the 13 October call, the v2 and superseded packs, T11) | Section 2.2; with the backend and frontend checks, sixteen statements of revision 7.3 corrected (section 2.6) |
| Client review | The 20 October transcript read against the exact v2 text of each asset and against the 13 October call | Section 3 |
| Command Center | Code and configuration read | `AUTH_DISABLED` is honoured in production with a warning; S.C1's "done when" is not implemented |
| Production | **Not reachable.** `railway status` returns "Unauthorized. Please login"; Docker is not running on this machine | Production is described as last verified on 19 October (section 2.4); nothing about it is claimed as current |

**Not verified on 22 October** (and not treated as fact here): the production project's current services, database contents, variables, queued deployments and bucket contents; Command Center's production variables; whether Jainil deployed the mock for a Loom; whether `production-settings.json` and knowledge-base version 8 are applied in the local working copy `atelier_work`; the database test suites (Docker not running); whose Fathom account the local `FATHOM_API_KEY` belongs to.

---

## 2. Verified state on 22 October

### 2.1 The path from a new call to an approved brief

| # | Step | What is built | How it runs today | Gap for live use | Where it is closed |
| --- | --- | --- | --- | --- | --- |
| 1 | Intake | Fathom collector (hourly once activated; fetches only calls created after activation, `intake/fathom.py`); file import of TXT, VTT and native Fathom folders (`documents import`, idempotent); a Slack push endpoint (unused: Slack is out for now, revision 8.4) | Command-line imports on the working copy | The 5 to 19 October calls cannot come through the collector; native Fathom import needs a `metadata.json` envelope no script writes; an imported file is not embedded until `documents reembed` runs; the collector reads `ATELIER_FATHOM_API_KEY`, while `backend/.env` defines `FATHOM_API_KEY`; a Zoom transcript has no upload screen (command line only); no intake or bulk worker in production | 6.B18 (M1); 1.F7 (M6); M4 steps 4 and 8 |
| 2 | Normalise and date | Classification (rules; `models.document_classification` blank, so an ambiguous call waits for a person), speaker roles, dates from evidence, segmentation; automatic after import, as `document_normalise` jobs on the **bulk** queue | Automatic where a bulk worker runs | A call classified `other` waits for a person, and the route to resolve it (`POST /documents/{id}/classification`) is not relayed to the app, so it needs the command line | 1.F6 (M1); the bulk worker (M4) |
| 3 | Embed | One embedding contract; automatic for intake; `reembed` otherwise | Under run plans | A paid step needs a run plan id in a variable and a redeploy on Railway | 6.B3 (M1) |
| 4 | Scenes | The moments ledger: scene profile v2, each scene validated alone, repairs recorded; the weekly run extracts any selected document not yet in the ledger All 91 included documents extracted (USD 0.94); 1,605 of 1,669 scenes verified (96.2%) after 27 documents were re-partitioned on 20 October (2.B11) | No scene type for a human line or a counter-expected WIA decision, which is where the v2 ideas came from | E.B31 (M2) |
| 5 | Cycle | `documents select --from --to --mode live` freezes a window's included documents and queues the weekly run (`two_call_v1` workflow), whose strategist reads **the window's verified ledger scenes of whole calls** (`sql_pipeline.py`); only the benchmark harness uses the five-excerpt packets | Command line only. The app's run route (`POST /storage/weeks/{id}/runs`) reads only documents admitted to that week; the scheduler has no cycle task | An approver cannot start a window from the app | 3.B2/3.B3 go-live subset (M1); 3.B11 (M6) |
| 6 | Verification | Rule checks always; the model pass only when `models.card_verification` is set; the R40 critic reframes failing cards (`card_reframe.v1.md`) | Inside the cycle | Tests the subject of an idea, not its point | E.B30 (M2) |
| 7 | Gate 1 | Develop, reframe (a person types a new title or point; no model call), hold, internal, skip, revive, rubric ratings (E.X7) | In the app | The screen edits only the title and point (the backend's `PATCH /angles/{id}` accepts every field but `rank` and `moment_ids`); no "refresh with feedback"; the card is not in Whitney's format | 3.B7/3.F2 go-live subset (M1); E.B32 (M2) |
| 8 | Brief | Research (planned queries, hybrid search, grading, prior coverage), contract v3 with writer v4, the ledger built after writing, a verifier from another family, repair only on blocking findings, copy checks (E.B24) | **Developing a card queues the brief in replay mode** (`gate_one.py:344`), which fails for a new card until someone runs `storage_cli activate-brief` and retries. `POST /angles/{id}/brief` takes a mode but is deliberately not relayed, and the first brief's run key ignores the mode, so the replay run queued at approval also blocks a later live start | No live start from the app; writer v4 tells each Reel to make "a distinct point" (the micro-lesson split WIA rejected); no first-touch rules | 4.B1 (M1); E.B33, E.B34 (M2) |
| 9 | Gate 2 | Decision with disposition, CTA confirmation, before-publishing answers, anchor; `PATCH /briefs/{id}` saves a new version with locked fields; `POST /briefs/{id}/revise` sends instructions to the writer | In the app for v1 to v3 | The screen edits 5 of 11 to 12 sections of a v2 or v3 brief and no asset field one by one; refresh is offered only for v1 and always in replay mode, and only the v1 template tells the model how to use instructions; an edit locks a whole section (`EDITABLE_V3`), and every asset sits in one section (`format_plan`), so after a subject-line edit a refresh can change no asset unless the instructions name `format_plan`, which unlocks the edited line too (`briefs/validation.py`, `unlocked_fields`); "add context" means choosing existing evidence ids; no versions list for v2 or v3 | 5.F1, 5.B6, 5.B7, 5.F4, 5.F5 go-live subsets (M1) |
| 10 | Hand-off | `GET /briefs/{id}/handoff` (pieces with keys, anchor, message spine, consent per evidence item), `can_consume` for v1 to v3, Markdown export | Built | No export in the layout WIA reviews | 5.B14 (M1) |
| 11 | Learning | The review queue, compiled versions, the assembly service, the learning loop over edits (L.B6), published-content capture (L.B9), the context scheduler (L.B11) | Built | The learning loop's paid categoriser is off by default (`context.schedule.mining_live`); gate feedback is not mined, so a correction given twice is not noticed; L.B11's scheduled benchmark uses strategist v5 and cannot run in the production image (its inputs live in `research/`, R48) | M4 step 5 turns mining on under a standing budget; L.B14 (M6); M5's tone loop runs benchmarks from a checkout |

**The configuration.** The code defaults are still the configuration WIA rated "1's across the board" (strategist `reel-editorial.v2` on Luna, brief contract v1, writer v2, no model verifier). The candidate (strategist v6 on Sol, verification on Sonnet 5.5, contract v3 with writer v4) exists only in `backend/deploy/production-settings.json` and takes effect only through `storage_cli settings apply`. Knowledge-base version 8 (`wia-kb-2026-10-20.c-6bf62f94`) is the file default, but a database with an active compiled version uses that version instead (`knowledge/assembly.py`), so production must publish and activate the version of record. M4 step 5 does both.

**Dossiers** are written through the artifact-store interface, S3 in production (0.B7's verified row); a table for them (4.B2, 4.B5) can wait (M6).

### 2.2 Output quality: what has been measured, and what has not

| Output | Made by | What is known |
| --- | --- | --- |
| Week 1 batch (reviewed by 13 October) | The system's old configuration | Whitney: "1's across the board". The last WIA rating of system output |
| 13 October packs | Written by the developer in Whitney's ChatGPT | Rejected by WIA on 13 October (how-to drift in the brief; the subject line; slide 1; hooks and scripts to be punchier and more casual) |
| Strategist v6 on benchmark v1 (five excerpts per week), 20 October | The system | Template titles 0 of 29 (v5: 18 of 23); an ATTRACT card in every sample; Whitney's stance kept in 3 of 3 Week 2 samples. On Week 2, "reviews aren't market research" (published 10 June) ranked first in 3 of 3 samples, and one client story became two or three tactic cards |
| Brief contract v3 with writer v4 on the live development week's three cards, 20 October | The system | 4 of 5 parsed judgements against writer v3; 2 of 3 briefs needed no repair; no checking language or writer instruction in copy. Never measured against the pack standard or by WIA |
| The rejected rebuild (made 20 October; earlier documents also call it "the 21 October packs") | By hand, two critic passes | Rejected by the owner as repeating what WIA had rejected |
| **v2 packs** (shown 20 October) | **By hand**, three rounds, two blind reviews by Claude subagents; no OpenRouter call | WIA: "definitely looks more aligned", with eight specific notes (section 3) |

**Reproducibility, precisely.** No pipeline stage produced the 13 October packs, the rejected rebuild or v2. The only automated steps used were a lint over the rejection-rule patterns and a critic script. No automated reproduction of v2 has been attempted: the strategist has never run on the whole of Week 2 (only on benchmark v1's five excerpts), and no brief has been written on the v2 ideas. What exists is the method (`research/v2-reassessment-2026-10-20/Reproducibility-and-System-Findings.md`):

| Step of the v2 method | Today | Where it is built |
| --- | --- | --- |
| 1. Beliefs to prove this window, with offers and do-not-repeat | No | E.B28 (M2) |
| 2. Hunt for four kinds of moment over whole calls | Whole calls yes (live path); the two key scene types no | E.B31 (M2) |
| 3. Pair a moment with a belief; the point in one sentence | No | Strategist v7 with KB 19 (M2) |
| 4. Five tests on the point | No | E.B30 (M2) |
| 5. Compress the story (one moment, at most two details) | No | E.B33, E.B24 extension (M2) |
| 6. Same idea through different doors | Contrary (writer v4 asks each Reel for a distinct point) | E.B33 (M2) |
| 7. Write in her register, format by format | Partly (KB 09 and 17 loaded as background, not checked) | E.B33, E.B34, E.B24 extension, KB 18 (M2) |
| 8. Verify quotes, claims, identities | Yes for quotes and claims (the ledger); not hook fidelity or identities | E.B24 extension (M2); 1.B12 extension (M6) |
| 9. Compare with her work | A calibrated pairwise judge (`judge-compare`); her 20 October notes not yet a test set | N11: the paid judge left the go-live path (D39); M3 compares by a blind delegated reading |

What v2 drew from records the system cannot see: Pack 2's "what we built" beat (later emails and internal calls); Pack 3's AI stance as background (Whitney's 24 September email in the export); Whitney's own fact about the client's AI assistant (in no record). Pack 1's public copy needs nothing beyond Week 2. Account memory (3.B17) therefore improves some stories but is not on the critical path (M6).

### 2.3 The frontend: the real app and the demo

- **The switch** is build-time only: `frontend/src/App.tsx` renders `MockStudioApp` unless `VITE_ATELIER_MODE=backend`. `frontend/Dockerfile` has no argument for it, so **any Railway build of `main` is the mock**, and DEPLOYMENT.md's warning that approving the newest Frontend deployment "would replace the mockup with the real app" is now backwards.
- **The mock** shows the v2 packs word for word (formatting aside), adds invented scores (88, 91, 92), labels June calls "Current week", shows 48 fictional earlier concepts, a Chicago-time schedule popover and a static calendar, keeps all state in the browser, and offers no editing. It carries venue names and call references in `frontend/src/data/` (R48 allows client material only under `research/` and `backend/knowledge_base/`).
- **The real app** has the Weekly Studio with the card screen (E.F1, E.F2), the v2 and v3 brief reader with Gate 2 (E.F4), Sources, Moments, the review queue and knowledge-base screens; its gaps for WIA are in section 2.1, steps 5, 7 and 9.
- **Checks:** lint passes; 332 unit tests pass and 1 is skipped; 52 server tests pass; the build passes (one chunk over 500 kB, a `__dirname` warning in `vite.config.ts`).
- **`backend/docs/Calendar-Deployment.md`** (rewritten on 20 October) documents a variable no code reads (`ATELIER_E2E_ORIGIN`), a command that does not exist (`storage_cli calendar-migrate`) and compose files that do not exist; it is one of the two CI failures.

### 2.4 Production and operations (last verified 19 October; not reachable on 22 October; superseded on 24 October by N3, `research/production-2026-10/README.md` and DEPLOYMENT.md's "What is deployed today")

- **Railway project "Content Atelier"** (production, the only environment, D13): `postgres` (pgvector 0.8.2-pg17, 5 GB volume, empty database), `redis`, buckets `artifacts` and `transfer-inbox`, and the `Frontend` service at `https://content-atelier.up.railway.app` serving the 6 October mock; at least 11 deployments queued for approval then, and more since (PR #12 and Jainil's five pushes). No API, worker or scheduler.
- **Command Center** (`https://command-center-wia.up.railway.app`, `a1e98b5`): `AUTH_DISABLED=1` set and no `SESSION_SECRET` (19 October). The code honours the flag with a warning (`server/index.mjs`): any email signs in as `team`, and because the Atelier resolves roles by email, anyone can act as an approver once the Frontend points at the API. Removing it safely also needs `SESSION_SECRET`, `AUTH_PASSWORD_HASH` (or the committed default hash becomes the login), real accounts and removing the build-time `VITE_AUTH_DISABLED`. Command Center has no CI.
- **The real data** is the processed working copy `atelier_work` in the Docker container `atelier-work-pg` on the owner's machine, with 523 MB of artifacts in `atelier-work/artifacts`. Every dump on disk predates the 20 October work; production needs a fresh dump (M4).
- **Fathom:** 33 October meetings (5 to 19 October) were listed through the API on 20 October and never ingested.

### 2.5 Tests and CI

- **Offline backend:** 980 passed, 124 skipped, 2 failed, 73 s (database suites not run: Docker is not running). The Done items' own test files pass (93 tests).
- **The two failures,** both from `5588578` and both on CI: `test_client_material_guard.py` (the exception kept for `frontend/src/data/fathomWeeklyAngles.ts` is no longer needed and the test says to remove it) and `test_documented_variables.py` (`ATELIER_E2E_ORIGIN` documented in `Calendar-Deployment.md` and read by no code). CI on `main` has been red since; frontend checks and both image builds pass.

### 2.6 Corrections to revision 7.3

| # | Revision 7.3 said | Verified on 22 October |
| --- | --- | --- |
| 1 | Approving the newest Frontend deployment replaces the mockup with the real app | False since `b02c54d`: the default build is the mock; the real app needs `VITE_ATELIER_MODE=backend` at build time |
| 2 | CI green on `main` (S.B2) | Red since `5588578` (section 2.5) |
| 3 | E.B22: "the production configuration uses" writer v3 | Production names contract v3 with writer v4; writer v3 writes contract v2 only |
| 4 | E.B17 row: Week 5 has no guard | The guard exists (`knowledge/held_out.py`) |
| 5 | E.B27: the strategist reads five excerpts | Only the benchmark harness does; the live path reads every verified scene of the window's whole calls. E.B27 is benchmark v2, not a product change |
| 6 | E.B33 is "writer v4" | Writer v4 is E.B23's; E.B33 is writer v5 with contract v4 |
| 7 | 3.B17 raised to P0 because "every v2 pack's strongest beat came from later records" | One copy beat (Pack 2's "what we built") did; 3.B17 is P1 (M6) |
| 8 | Pack standard: carousels of 9 to 12 slides; subjects "about the problem, not the process" | KB 09 says usually 7 to 10; Whitney praised a subject that states WIA's decision. Reconciled in section 4.3 |
| 9 | E.B27, E.B31 and Q2 name different scenes to surface | One list: T01's budget reset, T02's "beyond the ads", T10's "on paper… it's just all fine", T11's "I don't know what we changed" |
| 10 | D26 frames the 13 and 21 October packs | The set shown to WIA was v2; D26 is re-scoped to it |
| 11 | D15: Whitney sees only the end product; reviews stay delegated (D12) until then | Overtaken: WIA reviewed v2 on 20 October and will review live weeks from M5 |
| 12 | D22 and 5.B13: a pack stage is the open question | Contract v3 already writes most of the asset copy and contract v4 (E.B33) adds the rest; the pack notes are brief work (M2); the pack stage was out of this phase (section 6) until the owner's direction of 23 October put packs into go-live (Phase NP, D43; revision 8.4) |
| 13 | Section 2.1, step 12: Gate 2 (edit, refine, add context) "built for v1 and v2" | Refine works in practice only for v1 in replay: the route accepts v2 and v3, but only the v1 template uses instructions and the screen sends replay; "add context" picks existing evidence only; edits lock whole sections |
| 14 | S.C1 | Its "done when" is not implemented in Command Center's code |
| 15 | The live Fathom collector covers the October intake (6.B1 extension) | It never fetches calls older than its activation; a one-off backlog import is needed (6.B18) |
| 16 | "Where to resume" step 3 | Most of it is done; replaced by section 5 |

---

## 3. The client review of 20 October 2026

### 3.1 What was shown, and how

Minu walked Whitney through three angles, their briefs and their packs inside the Atelier app:

1. "How we approach a new client's ad budget, and why 'spend more' isn't our first move" (ATTRACT);
2. "What our strategy calls actually cover, and why the most useful part often isn't about the ads" (WARM);
3. "How we help wedding pros understand their own ad accounts, now that AI can change them in minutes" (CONVERT).

They are the hand-built v2 packs for benchmark Week 2 (`research/v2-reassessment-2026-10-20/packs/WIA-Content-Packs-Week-of-8-14-June-2026-v2.md`), loaded as the app's mock data the same morning. The flow on screen (approve an angle, read the brief, "generate content pack") ran on that static data in the browser. The v2 document says in its own introduction that the packs "are not system output yet", but that introduction is not in the app, the .docx rendered for WIA carries only the packs, the app labels them "Current week" with scores, and the call presented the content as the reworked system's ("the AI, based on the tone and based on your ChatGPT context, is now turning up with much better subject lines"). WIA's expectation is therefore set at the v2 level (K60, D26). The call's full transcript is in `research/packs-2026-10/20-october-call-transcript.md` (supplied by the owner on 24 October). It also records the team's promise about packs: feedback refresh stops at the brief, and in the pack Whitney's own text is kept word for word (7:54 to 8:31).

### 3.2 What Whitney said, and what each point means

| # | Asset (v2 text) | What Whitney said | What it means | Where it lands |
| --- | --- | --- | --- | --- |
| W1 | All three packs | "It definitely looks more aligned"; "this is looking really good. It's very exciting" | The v2 method and the standard in section 4 are the target; the plain "How we… / What our…" titles and her angle fields drew no objection | D32 settled; 4.2 |
| W2 | Pack 1 email subject "Why we lowered a new client's ad budget" | Accepted as catchy ("driving curiosity") | A subject that states WIA's counter-expected decision works | 4.3, first-touch rule 3 |
| W3 | Pack 3 email subject "She used AI to set up her Google Ads" | "That's probably not a subject line that I would use" | Narrating what a third party did is weak. **Repeat** of 13 October ("a little bit more enticing… the problem than the process"; action item "revise email subject") | E.B34 (a) |
| W4 | Pack 3 carousel titled "The part of your ads AI can't do for you"; slide 1 is the bare quote "I don't know what I've done…" | Likes the title; "slide one is so ambiguous"; tie the title into slide 1, "the first thing that somebody would see" | Slide 1 carries the carousel's promise for a cold reader. **Repeat** of 13 October ("really makes people want to continue reading"; action item "punchier slide 1"). The contract has no carousel title, so nothing could tie it | E.B33 (carousel title); E.B34 (b) |
| W5 | Pack 3 Reel 1 cover "Something's working, and then it stops" | Make it about ads: "your ads are working, and then they stop"; the on-screen hook "is great" | Covers name the concrete subject. An earlier draft had it ("Her AI set up her ads. Then they went quiet."); a de-duplication pass stripped it, so specificity must outrank sibling distinctness | E.B34 (c) |
| W6 | Pack 3 Reel 2 hook "One of our members brought one question to office hours…"; the script says "office hours" twice | An audience not in the program may not know the term and it "could maybe be a bit of a turnoff"; "we met with one of our Accelerator members recently"; the term may be "sprinkled in" the spoken script, not also on the hook | WIA's program internals stay out of first-touch text and appear at most once in a body or script, explained. No rule or check covered vocabulary | E.B34 (d); a glossary in KB 05 |
| W7 | Pack 3 Reel 2 cover "Did I set this up wrong?" | "Did I set my ads up wrong?" | As W5: a client's line lifted without its subject | E.B34 (c) |
| W8 | Pack 3 Reel 3 (b-roll): cover "What changed?"; screens "…set up her Google Ads" / "Four good leads in the first week. Then she changed a few things." / the quote | Cover more specific; screen 1 good; screen 2 "then the AI assistant made a few changes"; screen 3 the client saying she doesn't know what changed and it isn't working; the AI was "plugged into her Google Ads API… doing the work for her, and she had no idea" | A text Reel tells the turn of the story in screens a cold viewer follows. **Her fact is in no record**: T11 says "I had to go in and optimize it and then something changed", and the pack's own guardrail pushed the copy the other way. The system must accept a fact Whitney attests at a gate and let it into copy | E.B34 (e); 5.B7 |
| W9 | Process | Asked to "go in and overwrite things that are there"; promised for next week "at each step" | Every angle and brief field editable, and an edited line kept verbatim through later regenerations. **Repeat** of 13 October ("the ability to edit at each spot") | 3.B7, 5.F1 (M1) |
| W10 | Process | Asked for "general feedback" that "would create a refreshed version" | The team's answer sets the scope: feedback regenerates the angle and the brief; after approval, copy is edited by hand and kept verbatim | 3.B7, 5.B6, 5.F5 (M1) |
| W11 | Process | Will review "in a document format" and leave comments | The week's cards and briefs export in WIA's review layout; comments come back as gate feedback entered by the team, with their author | 5.B14 (M1) |
| W12 | Commitments | "Next week is when we are going live"; next week "we actually start using some other live calls"; a Loom before 27 October if live; a change-request tracker for tone | Live intake and cycles on production; tone requests flow into the knowledge base through the review queue and the benchmark gate | D35; M4; M5 (X.2) |
| W13 | Scope | The client knowledge base starts after the week of 27 October; performance data is outside it | A separate Command Center product ("Coming soon" there); no Atelier work | Section 6 |

### 3.3 What the review teaches about the system

1. **Rules that are loaded but not checked are not followed.** KB 09 already asked for specific subjects and a strong slide 1, and Whitney asked for both on 13 October; the v2 rebuild, made by hand with those rules in front of it, still missed them. Each of her corrections becomes a check with her text as its test case (E.B34), and a correction given twice becomes a rule candidate on its own (L.B14).
2. **LLM judges miss what she sees.** The second blind judge rated Pack 3's hooks 4 of 5 and predicted "light edits"; it caught none of W3 to W8. Judges stay diagnostics; her notes become the checks' test cases (E.B34) and a labelled set for the judge, whose paid run left the go-live path (D39, N11).
3. **Fidelity and helpfulness conflict without a gate fact.** Source fidelity and de-duplication removed context from covers, and strict quote binding would block her own correction. Specificity outranks distinctness, and a fact Whitney attests at a gate is evidence (R57).
4. **The points held; the first touch was weak.** None of her notes is about which ideas were chosen. Every one is about the first thing a cold reader sees, vocabulary, or story fidelity: work for the writer, the contract and the checks.

---

## 4. Target: what "fully operational through brief generation" means

### 4.1 The workflow at the end of this phase

On production, every week, without a developer:

| # | Step | What happens | Who |
| --- | --- | --- | --- |
| 1 | Intake | New Fathom calls arrive through the collector (a Zoom transcript is imported by the team; an upload screen is 1.F7, M6); they are classified, dated, speaker-resolved, segmented and embedded; a call the rules cannot classify waits for an editor in the app | System; an editor for unclear calls |
| 2 | Scenes | Each included call is read whole into verified scenes, including human lines and counter-expected WIA decisions | System |
| 3 | Strategy brief | The window's beliefs to prove, live offers, what must not be repeated, the content plan | System, from the knowledge base |
| 4 | Cycle | One strategist call over the window's verified scenes proposes ranked cards that pass the five point tests, with considered ideas and internal insights | System, started from the app (on a schedule after go-live) |
| 5 | Gate 1 | Whitney, or a reviewer she names, reads each card in her own angle format; edits any field; asks for a refreshed version with feedback; adds context or an attested fact; chooses develop, reframe, hold, internal or skip | WIA |
| 6 | Brief | Developing a card starts research and the brief at once, within the standing budget. The brief has the 13 October structure and the finished copy of every asset, with its claims ledger and checks | System |
| 7 | Gate 2 | Whitney edits any field (kept verbatim from then on); asks for a refreshed version with feedback or added context; confirms the CTA; answers the before-publishing items; approves or rejects | WIA |
| 8 | Hand-off | The approved brief is read-only at its URL, exportable as Markdown and in WIA's review document; the hand-off view is the pack stage's input (Phase NP; what the pack does is D43) | System |
| 9 | Learning | Gate reasons, feedback, edits and published finals become candidates in the review queue; an approved knowledge-base version passes the benchmark gate before it is used | System and Gisselle |

Every step is persisted, recoverable, costed under a budget and replayable from its saved responses.

### 4.2 The angle card standard

The card is Whitney's own angle format (her preferred-angles tab; shown to her on 20 October without objection):

- **Title:** a plain description of WIA's work or perspective ("How we…", "What our…", "What goes into our…"). The hook belongs in the copy.
- **Fields, one to three sentences each:** content pillar and type; audience; why this matters; WIA's expertise or process; evidence in the referenced call (with timestamps); editorial guardrail and next step. Evidence detail sits in the ledger.
- **The point, tested.** Every public card states its point in one sentence and passes five tests: (1) the point is a WIA belief, standard or client experience, not a platform or tactic; (2) it would surprise an established owner who already runs ads; (3) the reader comes away thinking "I want a team that thinks like this", never "I should change this in my account"; (4) it is written for the established reader, never from desperation and never presenting ads or a WIA offer as frustrating; (5) it fits the offer calendar and is not a recent repeat.
- **One real moment proves one belief.** How often a topic recurs is context on the card, never a ranking input. One public card per client conversation.
- **A public stance** (for example, on AI) is flagged for Whitney's confirmation before development (D31).

### 4.3 The brief and asset standard

The conditions every brief must meet (section 2.4: the ledger, exact quotes, bound numbers, consent, the confirmed CTA, prior coverage, the pinned knowledge base, WIA's approval) and brief standard 2.4a stay in force (Appendix E). This section adds what WIA's own work and notes require.

**The brief** follows the 13 October structure, which WIA criticised for content, not shape: central point; strategic purpose and desired response; audience and reason to care; WIA perspective; supporting example with timestamps; narrative outline (hook; problems, desires and symptoms; main point; transformation; CTA); format and creative approach (each asset's job); CTA and essential boundaries (at most five before-publishing items). Then the finished copy of every asset.

**Same idea, different doors.** The email tells the whole story. Reel 1 is the story, face to camera. Reel 2 is the stance, face to camera. Reel 3 is b-roll with one to three screens of on-screen text. The carousel goes deeper. Two Reels are allowed when the idea does not support three (D30). No asset is a sub-lesson.

| Asset | Structure | Rules |
| --- | --- | --- |
| Email | DATE, SEND TIME, RECIPIENTS (proposed, for WIA to confirm; scheduling is downstream), SUBJECT, PREVIEW TEXT; "Hi {{contact.first_name}},"; an opening scene; short flowing paragraphs; one bold key line; the principle; the offer named with its approved descriptor as the solution; the CTA; "Talk soon, Whitney" | No bullet lists; never "DM" in an email; stands alone |
| Reel script | A crisp first line; backstory in plain speech; what WIA did or saw; the client's own words; the principle; a soft CTA or DM keyword | Spoken and casual; 45 to 90 seconds; no "Okay, so…" opener; personal reaction lines flagged for Whitney to keep or cut |
| B-roll text Reel | One to three screens telling the turn of the story | A cold viewer follows it from the screens alone; the caption carries the rest |
| Cover | A short, specific statement, often from her own sentences | Distinct within the pack and the week; most do not start with "Why" |
| Caption | Savannah's framework: a hook different from the Reel's; problems, desires and symptoms in the reader's world; the story as proof; the transformation; the CTA (CONVERT names the offer) | 150 to 300 words; clean and declarative; "-Whitney" on first-person captions; at most one "it's not X, it's Y"; no staccato chains; no aphoristic kickers |
| Carousel | A title; 7 to 12 slides (usually 9 or 10 for a story): slide 1 the title's promise as an insight about the reader; the story over two to four slides; the reader's situation and the reframe; a belief slide; a CTA slide for both DIY and done-for-you readers | Real text on every slide; "we" and "us"; stacked short lines and a bold key line allowed |
| Across the brief and the week | One offer CTA a week on Instagram, and covers distinct across the week (checked across the cycle's briefs, E.B24); offers named with approved descriptors; against "most agencies", never against the reader; ads and offers never presented as frustrating; no CTA pattern she never uses ("follow along"); text a reviewer gave is kept verbatim; caveats only in before-publishing | Repeat ideas, not sentences or lists of details; a subject may repeat the anchor Reel's hook (as Pack 1 does) |

**First-touch rules** (R59; from 20 October). First-touch text is what a cold reader sees before deciding to keep going: the email subject and preview, every Reel cover and on-screen hook, the first b-roll screen and carousel slide 1.

1. **Specific.** It names the concrete subject (ads, budget, Google, Meta, inquiries, bookings), so a cold reader knows what it is about: "Did I set my ads up wrong?", not "Did I set this up wrong?"; "Your ads are working, and then they stop", not "Something's working, and then it stops".
2. **Slide 1 carries the promise.** The carousel's title or promise appears on slide 1; a bare quote is not a slide 1.
3. **Subject lines** state WIA's counter-expected point or the reader's own question or problem ("Why we lowered a new client's ad budget"), never a narration of what a third party did ("She used AI to set up her Google Ads"). Two to four options, best first.
4. **No insider terms.** WIA's program internals (office hours, internal process and program names: the glossary in KB 05) never appear in first-touch text; in a script or body they appear at most once, explained in plain words ("we met with one of our Accelerator members recently"). The offer names themselves (ELEVATE, the Ads Accelerators) are not insider terms; they carry their approved descriptors.
5. **Who did what.** Story beats keep the actor the record names (the client, her AI assistant, our strategist), or the fact Whitney attested at a gate.

Specificity outranks sibling distinctness: when two openings would collide, the later one changes its angle, never drops its subject.

### 4.4 Reproducibility: what "consistent" means

| Property | Meaning | How it is shown |
| --- | --- | --- |
| Pinned | Every run records its settings snapshot, prompt profiles, models, knowledge-base version and hashes, and its input set | `llm_runs`, run snapshots, the brief's `pinned_inputs` (built) |
| Replayable | The same inputs and saved responses give the same output at no cost | 0.B4; S.B8's container replay (M1 finishes it) |
| Stable | Three samples of one configuration on one week agree on the ideas that matter and pass the same checks | The M3 gate: the target ideas in at least two of three samples; every brief without a blocking finding in three of three |
| Guarded | No prompt, model or knowledge-base change reaches production without the benchmark gate and a recorded result | R44; the checks; a blind delegated reading (D39); the M5 tone loop |
| Honest | System output is labelled as such; a hand-built reference is never presented as system output | R58; D26 |

### 4.5 Success measures

WIA's judgement on live weeks is the measure; benchmarks and judges are gates and diagnostics.

| Measure | First live round (M5) | Done |
| --- | --- | --- |
| Cards Whitney develops, or reframes keeping the point | At least half of a slate of at least four public cards | At least three of the top five on two consecutive live weeks, and no skip in the top three |
| Rubric 2.3a (`rubric-2.3a.v1`), rated in the app | 3 or more overall and on criterion 1 | 3.5 or more overall and 3 or more on every criterion, on two consecutive live weeks |
| Briefs approved without rewriting the central point | At least one in the first live week | At least three, on cards WIA chose |
| First-touch, insider-term and fidelity edits WIA makes at Gate 2 | Recorded by kind | None of a kind a check exists for |
| Factual problems WIA finds | Recorded | None the ledger did not flag |
| Repeats of published or prior content at Gate 1 | Recorded | None unflagged |

The rubric's five criteria: WIA is the subject; strategic purpose; audience; worth attention; sounds like Whitney (1 would not publish, 3 publishable after a light reframe, 5 publish as is). Its full text, with the conditions every brief must meet (2.4) and the brief standard (2.4a), is in Appendix E.

---

## 5. The remaining work

M1 and M2 run in parallel: M1 owns the live path, the gate screens, the frontend build and intake; M2 owns the prompts, the contracts, the knowledge base and the checks. Where they meet, the order is fixed: **6.B18 lands first** (M2's re-extraction and M3's held-out window need the October calls); M1 builds the gate editors, the refresh and the review document on contract v3, and E.B33 (M2) extends each of them to contract v4's new fields; the refresh's revision instructions go into writer v5 (M2), and into a new version of today's writer v4 (M1) so that contract v3 briefs can be refreshed before v5 exists; the card-screen changes for her six fields and the strategy brief (E.B32, E.B28) build on M1's editable card screen. M3 needs M2 and 6.B18. M4 needs M1, M3's configuration (and the working copy after M3, which holds the re-extracted scenes) and Railway. M5 needs M3 and M4. Effort: S under a day, M one to three days, L a week or more, for one engineer or one implementation session.

### 5.0 The schedule to 27 October

**Revision 8.8:** the owner sets the timing. The day plan below is the record from 22 October; the phases (section 5.0b) give priority and dependencies only.

Delivery is on **Tuesday 27 October 2026** (D35, the owner's decision). Delivered means: WIA signs in to the app on production with her own account; the week of 12 to 19 October is there as cards made by the configuration that passed M3's gate; she can edit any card or brief field, refresh either with feedback, add context, develop a card (its brief starts by itself) and approve; new Fathom calls arrive by themselves; the week's cards and briefs export for her review; and her approved briefs become content packs, to the scope the owner sets (D43; revision 8.4).

| Day | Work | Done by the end of the day |
| --- | --- | --- |
| **Thursday 22 October** (today) | M0: D36 funded; the Railway CLI signed in and the project's access confirmed; the go-ahead for the production changes (D13); D26 and X.1 sent to WIA, asking for answers by Friday | Budget, access and approvals in place; the questions sent |
| **Friday 23 October** | 6.B18 and S.B15 first (the morning); then M1 and M2 in parallel sessions: M1 in three tracks (the cycle button, 4.B1 and the standing budgets; the Gate 1 and Gate 2 editors and refresh with locks and attested facts; intake, the waiting-call control, the provider fix and the production build), M2 in two or three (E.B28 and E.B31 with the re-extraction; strategist v7 and card verification v4; contract v4, writer v5 and the checks) | The October calls in the working copy; CI green; each track's first half merged |
| **Saturday 24 October** | M1 and M2 finish; knowledge base 9 compiled; benchmark v2 packets built; M1's exit test in the production image | M1's exit passes; M2 merged behind profile settings |
| **Sunday 25 October** | M3: the gate on Week 2 and the October window (Week 1 for the cards only); the configuration of record written to `production-settings.json`; the fresh dump of the working copy taken | The gate's result recorded; the dump ready |
| **Monday 26 October** | M4: backups on and the restore rehearsed; the restore; the services, the bulk worker included; settings and users; the Frontend in backend mode; the Fathom collector; 7.X1 live verification on the October week; the Loom recorded on production | 7.X1 recorded; the Loom sent |
| **Tuesday 27 October** | Delivery: WIA signs in at the sync; the October week's review document is sent; M5 starts | WIA is using the tool |

**Moved to after delivery, so the date holds** (each stays in its row and moves to M6): the .docx layout of the review document (5.B14 delivers Markdown on 27 October, and the team renders the .docx with `research/v2-reassessment-2026-10-20/tools/packs2docx.py` for the first week); failure alerts (6.B4; the team watches the extraction-health panel during delivery week); S.B8's container replay (M3's replay check covers it); the E.B24 checks that do not block (detail density, aphoristic kickers, sibling overlap of detail lists, DIY drift on every asset, the week-level checks), while the first-touch checks (E.B34) and the blocking ones (insider terms, hook fidelity, outcome verbs) ship; KB 19 (L.B12) if D34 is not answered by Friday; same-point recency as a ranking penalty (3.B5's extension) if it is not merged by Saturday, since the same-point flag already shows at Gate 1.

**If a step depends on someone outside the team** (the date does not move):

| Dependency | By | If it is late |
| --- | --- | --- |
| Railway access and the owner's production go-ahead | Friday 23 October | M4 is rehearsed in full on the owner's machine on Saturday and run on Railway the moment access returns; on 27 October WIA receives the October week's output in the review document, and the app opens the same day access returns |
| Budget (D36) | Thursday 22 October | Without it the gate cannot run; the week is generated on the internal key's weekly allowance in one sample, and the other two samples follow in delivery week |
| WIA's answers (X.1) | Friday 23 October | Each unanswered decision keeps its recommended default (section 7) |
| M3's gate | Sunday 25 October | Deliver with the best combination that passes its part of the gate (for example strategist v7 with writer v4, or v6 with writer v5), recorded as such; the rest follows in M5 |

### 5.0a Built on 23 October, and the next step

An unattended run on 22 and 23 October built M1's and M2's code in seven tracks and an integration pass, each on its own branch, merged on `main` (`4188368` to `51db019`). No paid call was made: the only funded key (internal) holds USD 0 until 26 October 00:00 UTC. Evidence on `main` after the last merge: ruff and `openapi --check` clean; backend offline 1,166 passed; both database suites in full (CI's job) on each merge (1,712 passed, none failed, at track F's merge; on the final `main`, after the repair of K69, two full runs back to back with 1,748 passed and none failed; frontend type check clean, unit 367 passed, server 60 passed; both production images build with no argument.

| ID | Built (23 October) | Where | Remainder |
| --- | --- | --- | --- |
| S.B15 | The stale guard exception removed; the mock data anonymised; `Calendar-Deployment.md` matches the code; both failing tests pass | `test_client_material_guard.py`, `frontend/src/data/`, `backend/docs/Calendar-Deployment.md` | — |
| 7.F2 (build) | `ARG VITE_ATELIER_MODE=backend`; any other value than `backend` or `mock` fails the build; CI builds both; DEPLOYMENT.md names the flag, the bulk worker and `COMMAND_CENTER_PUBLIC_ORIGIN` (always set; `sso.mjs` falls back to the auth origin and returns 503 only when that origin is private) | `frontend/Dockerfile`, `ci.yml`, `server/build.test.mjs` | The production deployment (M4) |
| 6.B18 | `documents fathom-backfill` (the collector's client, native folders with `metadata.json`, the collector's identity, duplicate detection); **run** for 5 to 19 October into `atelier_work`: 33 meetings listed, 18 imported (documents 170 to 188), 15 already present, a twin, or a second recording; all 22 window calls dated by Fathom and normalised; none waiting | `documents/fathom_backfill.py`; run log in `atelier-work/fathom-backfill-2026-10/` (outside git) | — (embedded in N2: 241 chunks of 11 calls, USD 0.0033) |
| 1.F6, 1.F7, Fathom key | Classify a waiting call and upload a transcript (JSON body, editor role) from the Sources screen; `ATELIER_FATHOM_API_KEY` falls back to `FATHOM_API_KEY` | `DocumentActions.tsx`, `intake/config.py` | — |
| E.B1 (extension) | An empty answer at its length limit is retried once with a raised limit; both calls recorded | `llm/transport.py` | — |
| L.B11 | The scheduled benchmark reads the strategist profile from settings and records `skipped` with its reason where `research/` is absent | `knowledge/benchmarking.py` | — |
| 0.B8 | `production-settings.json` gains `context.schedule.mining_live: true` and `models.completion_tokens: 16000`; a live run refuses a strategist, brief or writer profile left at the rated code default and names `settings apply` (the code defaults stay, so released runs replay) | `settings_store.py`, `deploy/production-settings.json` | — |
| 3.B2/3.B3 | Preview (calls, late arrivals, undated calls, the estimate, budgets) and start a cycle for a window from the app; the run records its documents, why each was selected and the scenes the strategist saw | `cycle/window.py`, `cycle/api.py`, `CyclePanel.tsx` | — |
| 4.B1 | Develop queues the brief live; the run key includes the mode; developing twice makes one brief; over budget it waits with the reason on the card | `gate_one.py`, `briefs/workflow.py` | — |
| 6.B3, 0.B6 | Standing weekly budgets per purpose in the database, renewed by the scheduler, found without a variable; refused before sending; `storage_cli budgets show|set|renew`; caps USD 3.50 a week (cycle 1.20, briefs 1.20, refreshes 0.50, extraction 0.40, embedding 0.10, context mining 0.10) | `llm/standing.py`, DEPLOYMENT.md "Standing budgets" | Measure and reset the caps in the first live week (D36) |
| 5.B14 (Markdown) | The week's review document from the brief structure (v1 to v4) and v7 cards in Whitney's order, with the 13 October header and the headings `packs2docx.py` reads | `briefs/review_document.py`, `GET /weeks/{id}/review.md`, `storage_cli review-document` | The .docx (after delivery) |
| 3.B7/3.F2 | Gate 1 edits every card field from one field map (v5 to v7 cards); refresh with feedback (`card-reframe.feedback.v1`) keeps every field a person edited, word for word, under the refreshes budget; context panel; v7's public-use reasons and the stance confirmation (D31); the strategy brief shown | `cardFields.ts`, `CardReview.tsx`, `cycle/refresh.py` | — |
| 5.F1, 5.F4, 5.B6, 5.F5 | Gate 2 edits every field of v3 and v4 briefs by dotted path; refresh with feedback in live mode (writer `v4.1` for v3, `v5` for v4); an edit locks its line only; a draft that rewrites a locked line gets the person's line back, recorded; versions with author and reason | `briefs/paths.py`, `briefFields.ts`, `brief_write.v4.1.md`, `BriefGateV4` in `BriefReaderV4.tsx` | — |
| 5.B7, 5.F2 | Context and attested facts at both gates (R57; an attested fact enters the ledger as `attested` with person and date; card context reaches the writer); Gate 2 names its blockers in words | `briefs/context.py`, `shared/GateContext.tsx`, `blocker_items` | — |
| E.B28 | The window's strategy brief, deterministic, frozen with each cycle and shown at Gate 1; a card that undercuts a live offer is held, naming it | `cycle/strategy_brief.py`, `knowledge_base/beliefs-to-prove.json`, `offer-calendar.json` | WIA to confirm the two data files (added to X.1) |
| E.B31 | Scene profile `2026-10-23.scenes.v3` (human lines, counter-expected decisions with their departure), verbatim-checked like every scene; listed first in the packet | `scene_extraction.v3.md` | The delivery window extracted in N2 (7 calls, 147 verified scenes, USD 0.09; K13 holds); Weeks 1 and 2 in N11 |
| E.B30, E.B32, E.B29 (change) | Strategist `2026-10-23.wia-strategist.v7` (her six fields, the point fields, plain titles, one public card per conversation, recurrence as context, `guardrail` to the writer) and `card-verification.v4` (the five point tests; rejection reasons at Gate 1; stance confirmation before develop) | `card_contracts.py`, `angle_generation.wia_strategist_v7.md`, `card_verification.v4.md` | In production settings since N2's card reading; the Week 1 smoke run in N11 |
| E.B33 | Brief contract `brief_document_v4` and writer `v5` (same idea through different doors; Reel kinds, on-screen hooks, a caption per asset, b-roll screens, the carousel title, the email send header, register, offer descriptors; locked lines and revision instructions); rendered in Gate 2, the hand-off view, Markdown and the review document | `briefs/contracts_v4.py`, `brief_write.v5.md`, `render_v4.py` | In production settings since N2's brief reading (three briefs, 23 and 24 October) |
| E.B34, E.B24 (extension) | The five first-touch rules (insider terms blocking) and every check of E.B24's row and the week checks (outcome verbs and hook fidelity blocking) from `insider-terms.json` and `offer-descriptors.json`. On the v2 packs, W3 to W8 and the 13 October subject and slide-1 notes all fire and her corrected text passes; the other findings are real breaks of section 4.3 she did not name (18 sibling-overlap warnings, one email with four operational details, a b-roll Reel with six screens, two story Reels in Pack 3, two Instagram offer CTAs in Pack 3) | `briefs/first_touch.py`, `briefs/asset_checks.py`, `backend/scripts/pack_checks.py` | — |
| E.B25 (i) (j), L.B12 | Knowledge base 9 compiled from committed inputs, **active since N2's reading** (recorded as its benchmark, D40; the committed default since then, version 8 archived): `wia-kb-2026-10-22.c-a1a75795` (KB 18 from five recorded Reels; KB 19, six of her raw-to-final chains under D34's default; KB 05's descriptors and glossary from the two data files; KB 09's first-touch rules and her own subjects and covers, slide count 7 to 12; KB 13's giveaway at piece level). Prefixes 29,626 (strategist) and 29,264 (brief) tokens under `prefix-priority.v3`, which drops the audience-language document from both and KB 15 and the process catalogue from the brief: M3 judges that cut | `backend/knowledge_base/`, `test_kb9_db.py` | The $70K Reel waits for D38 |
| 3.B5 (extension) | A card repeating a point published within 60 days (30 for a fresh angle) ranks below new points, naming the post and when it may return | `cycle/recency.py` | — |
| E.B27 (packets), E.B3 | Benchmark v2 packets for Week 1 (97 of 97 verified scenes) and Week 2 (96 of 96, eleven calls); WIA's notes as the judge's labelled set (the recorded second blind review caught 0 of her 7 failures) | `research/benchmark-v2/`, `research/judge-labels/` | The October packet and the rebuild after the re-extraction; the paid judge run (N11, D39) |
| L.B14 | Gate notes, card-refresh feedback and brief-revise instructions feed the learning loop; a correction of one kind given twice is one rule candidate citing both, with no model call | `knowledge/repeats.py` | — |
| M1 exit (offline) | `test_m1_exit_db.py`: an approver previews and starts a window cycle, edits and refreshes a card, confirms its stance, develops it (the brief starts by itself under the briefs budget), edits an asset line and refreshes the brief (the line kept, a sibling rewritten), adds an attested fact, approves and exports the review document; a 402, a budget cap and a killed worker each show their reason and recover. Through the real live provider to a fake HTTP provider. It found and fixed five defects: a live cycle stalled until encoding was run by hand; editing a card from a window cycle crashed; card verification failed every live cycle on Sonnet 5.5 (its route had no byte budget); `models.completion_tokens` was missing, so live cycle calls were refused; refusals showed detail before the reason | `tests/test_m1_exit_db.py` | — (run through the app in the production images: N1 on free models with every failure case, N2 paid on the working copy; K13 holds) |
| 7.B5 (rehearsal) | A fresh dump of the working copy restored into a scratch database: 41 of 41 tables identical, schema at the newest migration | `research/restore-checks-2026-10-23/README.md` | On Railway in M4 |

**Decisions taken in the run** (under D12, recorded as delegated, R55; each can be reversed by setting): the code defaults stay and a live run refuses a profile left at them; a refresh that rewrites a locked line gets the person's line back; the standing caps above; KB 19 built under D34's recommended default; knowledge base 9's prefix cut; `beliefs-to-prove.json` and `offer-calendar.json` as the engineer's reading of KB 16, 01 and 05; the October duplicate rule (a start within ten minutes and shared wording); S.C1 left to the owner (a branch `s-c1-production-auth` in the Command Center repository was pushed before that instruction and is left unmerged).

**N1 and N2 (23 October).** Both phases ran on 23 October in the repository's own stack (`backend/compose.yml` with `research/shakedown-2026-10/compose.shakedown.yml`). The stack is the production images in backend mode with every worker of the production order, plus the Atelier Frontend and Command Center. N1 ran on a scratch copy of the working data, and N2 on the working copy. Every paid call went on the Client key (USD 2 limit), because the internal key was at USD 0 until 26 October.

**N1, the free-model shakedown (USD 0 for the model calls; USD 0.0034 for real embeddings).** The record is `research/shakedown-2026-10/ledger.md`.
- **Models:** two free models, `nvidia/nemotron-3.5-super-vl:free` and `dots-studio/dots-3-note-preview:free`.
- **Path covered:** the whole M1 exit through the app.
- **Failure cases:**
  - a real 403 key limit;
  - the budget cap and its release;
  - worker kills mid-extraction and mid-brief;
  - a timeout.
  - The 429 storm could not be provoked and is covered offline.
- **Visual check:** the app at desktop width, with no overlap or cut text left.
- **Findings, 50 in all:**
  - 29 pipeline defects (23 code, 4 design, 1 data, 1 test), each fixed at its cause with a test;
  - 10 handled as designed;
  - 8 free-model artefacts, 5 of them absorbed in the free-model branch of the dispatch (`llm/routing.py`, free ids only);
  - 8 M1-exit passes, and 1 not provoked.
- **Commits:** `58de109` to `05c5e25`.

**N2, the minimal paid delivery run (USD 4.0721: 2.3566 on the Client key, 1.7155 on the new internal key; done 24 October).** The record is `research/n2-delivery-2026-10/readings.md`, with the readings done as WIA's delegated reviewer (R55).

| # | Step | Result (23 October) | Cost (USD) |
| --- | --- | --- | --- |
| 2 | Routes cached for Luna, Sol and Sonnet 5.5 | Snapshots in the working copy's artifact store | 0 |
| 3 | Embed the October calls (6.B18) | 241 chunks of the 11 included calls; every current chunk embedded | 0.0033 (estimate 0.003) |
| 4 | Extract the delivery window with scene profile v3 (E.B31) | 7 calls, 147 verified scenes, 6 quotes repaired, all on the first attempt. **K13 holds:** the longest call, The Brightside, took 106 seconds against 3,600 | 0.0908 (estimate 0.046) |
| 5 | The October cycle from the app, strategist v7 and card verification v4 | Five cards. **The card reading passes:** no deterministic flag blocks; cards 1, 2 and 5 meet section 4.2; card 3 fails test 3; card 4 is held by the verifier's one blocking flag; every binding is bound to a verified scene. Contingency A was not run | 0.7976 (preview 0.63) |
| 6 | Develop the top cards: writer v5 with contract v4 | One brief, developed from card 1 after Gate 1 corrections. **The brief reading passes:** no content-level blocking finding (only Gate 2's own CTA and before-publishing items); none of W3 to W8's patterns; 4.3 met, with weaknesses noted; a blind reading ranked it above all three writer v4 briefs of 20 October. Contingency B was not run. **The replay check passes:** a fresh keyless container replayed the brief byte for byte at USD 0 (S.B8). **Briefs 2 and 3** (cards 2 and 5) followed on the Client key's remainder and the owner's new internal key (ceiling USD 2.25); both readings pass, with Gate 2 points for Whitney (brief 3's "nearby" paraphrase, brief 2's untold moment). A second blind reading ranked all three writer v5 briefs above all three writer v4 briefs. Each brief's hand-off view was checked | 1.0019 + 0.8738 + 1.3049 = 3.1807, including a lost answer of 0.1436 and a cut-off answer of 0.2459 |
| 7 | `production-settings.json` per part; the standing caps set to the week's remainder | Every part passed and is named: scene profile v3, strategist v7, card verification v4, contract v4 with writer v5. Knowledge base 9's reading passed narrowly (one blocking flag in five cards, equal to version 8's worst run): it is recorded as its benchmark, active, and the committed default. The caps total about USD 0.47 left, against the key's 0.60 | 0 |

**Defects found by the paid run, each fixed at its cause with a test:**
1. A call whose answer was lost after sending settled at USD 0 while the key was charged. It now counts at its worst case (`23701bb`).
2. One miscopied evidence ID in a grade failed the whole research stage. A one-character near-miss is now repaired and recorded (`ed4062c`).
3. The cycle preview counted scene records but not the call turns they carry, so it under-estimated the strategist by half (`32d65d3`).

None of the three could appear on free models. Finishing briefs 2 and 3 found three more:

4. A JSON answer cut off part way at its output limit was never retried; only an empty one was. Brief 3's claim check of 126 statements stopped at statement 100 of 16,000 tokens, 8,601 of them reasoning. It is now asked once more with a raised limit, as its own planned call.
5. A step retry replayed the cut-off answer and failed again without a call, and the output limit was frozen into the run, so raising it would have voided the run's research and writing. Recovery now skips a cut-off answer, and the output limit is an operating limit, outside the frozen contract. `models.completion_tokens` is 32,000 (K74).
6. The private-speaker check searched for a meeting label by its first word: "The Organic Moment Photo + Video" as "The" (eight false blocks on brief 2), "Steve’s iPhone" as "Steve’s". It now takes the first word that is a name, once.

**N2's exit is met in full (24 October).** The window is embedded and extracted; the October cycle exists with its card reading; three briefs exist with their readings and a blind reading; a fresh container replays a brief at USD 0; `production-settings.json` names the configuration that passed; the spend and remainder are recorded and the caps closed at the week's spend. Records: `research/n2-delivery-2026-10/readings.md`, `blind-reading-2/`.

**N3 and S.C1 (24 October; the owner's request, unattended).** Production runs the brief system. Record: `research/production-2026-10/README.md`.

| Step | What was done | Evidence |
| --- | --- | --- |
| 1. Inventory | Recorded before any change: an empty database, Redis, two buckets, the Frontend with one deployment waiting, no backend services, no backups; Command Center with `AUTH_DISABLED=1` | Step 1 of the record |
| 2. Backups | Railway volume backups need a Pro workspace (refused, and a plan change is the owner's). In their place, the nightly dump with its restore check, as the `db-backup` cron service (6.B6). The rehearsal restored the working copy's dump into a scratch database on production's server and dropped it | 41 of 41 tables, 12,609 rows matched |
| 3. Data | The same dump restored into production; the artifacts copied into the bucket and read back | Counts equal the working copy's; 8,224 files, 574 MB |
| 4. Services | `api`, `scheduler`, `editorial-worker`, `bulk-worker`, `intake-worker`, `db-backup` from `main`; the variables; the model routes cached; the standing caps (USD 5.00 a week) | A synthetic test document normalised and embedded by production's bulk worker, then excluded |
| 5. Configuration | The bootstrap commands, the knowledge base of record, the settings of record, the users | Nothing changed (the restore was faithful); knowledge base 9 unchanged; one user, `ai@weddingindustryads.com` |
| S.C1 and 7.F2 | Command Center's production auth (93be42a) and one sign-in and one sign-out for both apps; the Frontend in backend mode | Checked on production: every refusal, the deep-link sign-in, real data, both sign-out directions |

**Found and fixed on the way.** The first production dump's restore check failed. Its manifest counts were read just after `pg_dump`, while a document was being imported. The counts are now taken in the dump's own snapshot (`pg_dump --snapshot`), with a unit test and a database test.

**Decisions taken in this run** (delegated, D12; the owner may reverse any):
1. **Backups.** No Pro workspace and no billing change (the owner, 24 October); the nightly dump stands in for volume backups.
2. **The account.** One standard account, `ai@weddingindustryads.com` (the owner), as `admin` in `users` and on every approver list, the identity approvers included. Its password is in the owner's local `atelier-work/credentials/`, never in git.
3. **WIA reviewers.** `ATELIER_WIA_REVIEWERS` stays blank while the account is shared: a decision on it cannot be told from the engineer's, so it keeps the delegated label (R55) until Whitney has her own account.
4. **Key and caps.** Production uses the internal OpenRouter key, with the paid-stage switches on and the money bounded by the standing caps. The caps are D36's figures, with briefs at D42's USD 2.70 (three briefs a week): USD 5.00 a week in all. This week's plans already hold N2's spend, so production can spend at most about USD 1.41 more before the renewal on 26 October.
5. **Merging and approving.**
   - Both pull requests were merged after their checks passed. Production deploys from `main`, and the owner asked for it on production. Command Center has no CI, so its full test suite, type check, lint and build ran locally.
   - Railway holds each deployment from `main` for approval. Only the newest deployment of each service was approved, and only when it built the merged commit.

**N4 (24 October; the owner's instruction, unattended).** The October backlog, 7.X1's live check end to end and 6.C3. Record: `research/golive-2026-10/README.md`. The owner deferred the Fathom collector to N7 ("as late as you can") and dropped the Loom (25 October).

| Step | What was done | Evidence |
| --- | --- | --- |
| The October backlog (6.B18) | `documents fathom-backfill` for 1 to 24 October from a checkout, through a temporary TCP proxy and `remote.py`, with no live switch in the local process | 39 meetings: 23 already documents, 11 second recordings not imported, 5 imported; production's bulk worker normalised, embedded (54 chunks) and extracted them (54 scenes, scene profile v3) |
| Gate 1 (7.X1) | Card 4 of the October cycle, held by the verifier's one blocking flag (an invented reason): edited to what the call shows, refreshed with feedback, developed, through production's API as the team account | The blocking flag cleared; the edited point kept word for word; the brief started by itself in live mode |
| The budget refusal (7.X1) | The briefs budget was spent (N2's spend, carried by the restore) | The brief's research waited with the reason in words; raising the cap released it (a delegated decision; both caps put back to D36's and D42's figures afterwards) |
| Gate 2 (7.X1) | The two quotations told in reported speech (the call is `public_use: false`), Reel 1's cover named; refreshed with feedback; CTA, before-publishing answers and claims recorded; approved | The three locked lines kept word for word through the refresh; its research replayed at USD 0; no blocker left |
| The pack (7.X1) | Started by itself on approval; finished, checked (1 of 14 flagged), repaired, rechecked, finalized; two carousel lines edited by the team | `pack_9f451db3…` in review with no open finding; the edits locked and labelled delegated |
| Export (7.X1) | The week's review document, pack document and plan through the API | All 200; the new pack's pieces go to the bank |
| The pack screens | On the local copy through Command Center's sign-on, at 1600, 1366, 1024, 768 and 375 pixels | Every screen works; two layout defects fixed |
| 6.C3 | Command Center's Atelier card | "Live" wherever the Atelier's URL is configured. It has been live on production since 24 October: Command Center PR #4 merged at the owner's request (`be38d25`) and its deployment approved; the production card reads "Live" |
| Deployment | The fixes and this record | PR #20 was merged at the owner's request (`main` at `77235ee`, all five CI jobs green) and the newest deployment of each of the seven Atelier services approved; all seven run `77235ee` and the API passes its health check, so the three fixes are on production |

**Found and fixed on the way** (each with a test that fails without it):
1. A Fathom call took Zoom's "Impromptu Zoom Meeting" over its recording's name, so a consultation was filed as a client call. Now `fathom_title`, with classify-rules-v3 (`731dedc`).
2. The carousel CTA check knew only "you" and "your" (`18745b3`).
3. In a narrow piece column the email's header tiles overlapped, and a long id ran past its box on a phone (`d9adebb`).

**Decisions taken in this run** (delegated, D12; the owner may reverse any):
- The briefs and refreshes caps were raised for 7.X1's planned brief, then put back.
- WIA's founder's tax-planning call is excluded as private.
- The October cycle's card 4 was used instead of a new cycle, as 5.0b's least cost.
- The two new documents were retitled by script before any scene or vector existed. The 11 older ones are left for a person.

**Cost:** USD 2.7918 on the internal key; production's `llm_runs` agree with the key to the cent.

**N5 and NP-7 (26 October; `research/n5-2026-10/README.md`).** Phase N5's system side with the content-packs plan's
NP-7, unattended at the owner's instruction, so the system is ready for the WIA team to use.
- **Built:** the post-recording pass (NP.B14), finishing again with a permission (NP.B15), `pack-check.v3` with labelled
  cases (NP.X5), writer v5.1 (NP.B10), the week's pack document as .docx (NP.B12), rubric ratings on briefs at Gate 2
  (E.X9), `storage_cli week-measures` (7.X2), the tone loop end to end with its runbook (X.2, NP.X4).
- **Proved:** free models on scratch copy A (USD 0), then capped paid runs on copy B (Client key, USD 2.20): `pack-check.v3`
  caught both of the proof's missed clauses; the post-recording pass kept the take word for word; the permission re-finish
  used the grant, attested; writer v5.1's brief has the three kinds and passed a blind reading. Each is named in
  `production-settings.json`.
- **Fixed on the way:** a recorded take kept as a check source on later runs; a repair that cuts a list line removes it;
  research grades the items a grading answer missed instead of failing on every retry.
- **Production:** a fresh dump; three "Impromptu Zoom Meeting" documents classified from their recordings' names (the
  other ten already right); no calls since the last import; the cycle for 20 to 26 October (three cards at Gate 1, USD
  0.39); the caps for a week of use (USD 13.30); PR #24 merged after green CI (`0b3e587`), all seven services deployed and
  healthy, `settings apply` read back (`pack-check.v3`, writer v5.1, the two pass profiles).
- **Waiting on the owner:** X.1's personal accounts. **Out of scope:** WIA's own use, the two live weeks and their sign-off,
  and what the owner tells WIA.

**N8 (25 October; `research/n8-2026-10/README.md`).** Phase N8 unattended at the owner's instruction (full permissions
from the WIA team), PR #26 merged at `cb3ecc9` (hosted CI could not start: GitHub refused the jobs for the account's billing;
every CI job passed locally on the merged code).
- **Built:** migration 010; identities (`identities.py`, `storage_cli identities import|apply|show`, the reviewed list
  `research/n8-2026-10/identities.json`); `documents team-practice` and `key_moments.evidence_class`; scene profile v4;
  account memory (`accounts.py`, the panel at both gates); founder notes (a seed kind linked to its call, the seed form, the
  review document's line); strategist v8 and writer v5.2 (new files; v7 and v5.1 replay as before); dating by week folder,
  spoken cue and recording list (`date_evidence`); the Funktastic chain's golden scenes.
- **Proved:** free models on scratch copy C (production's dump of 25 October 07:34; USD 0), then the paid proofs on copy D
  (Client key, USD 4.27): strategist v8's Week 2 cycle (five cards: the Week 2 venue's story with its account panel and the
  stand-in founder note paired with its call's scenes, two team-practice cards whose guardrails keep client detail out,
  pronouns and naming as the identity records say), two writer v5.2 briefs on the venue's card, the golden fixture's
  recall and search.
- **Fixed on the way** (each with a test): a weekly run's extracted documents stay extracted when another fails; strategist
  v8 demotes a card still on an internal-only scene after its repair instead of failing the cycle; a founder note names its
  call as the scenes name it; a wrong pronoun is flagged; account memory's later records are at most eight, by their anchor
  passages (the first brief's research went over its preflight); an internal scene belongs to the one account its anchor
  passages name; a week-dated entry shows its folder's first day; and, found on production, a pack now freezes the identity
  records when queued and checks its own copy against them, the approved brief's copy included (a brief approved before the
  identities may carry a name they forbid: an approved brief of 24 October credits a never-named client contact; no pack's
  copy did).
- **Production:** identities loaded and applied (75 calls tied to their account), two calls the review found are not WIA's
  work excluded (delegated, D21), every Zoom transcript dated (63 to the day, 101 to the week), `settings apply` of
  `production-settings.json` (exactly five rows: strategist v8, scene profile v4, writer v5.2, internal meetings included),
  63 internal meetings admitted and extracted under v4 by production's queue (930 team-practice scenes, USD 0.68 on the
  internal key), 2,305 re-headed chunks re-embedded (USD 0.03), the account panel on every client story card of the last two
  weeks, the golden fixture measured (recall 4 of 5 for v1, v2 and v4; search 4 of 5 in the top 10 within the account, 1 of 5
  in the top 25 across the archive).

**Next step (start here).**

| # | Step | Phase | Cost (USD) |
| --- | --- | --- | --- |
| 1 | ~~Phase NP, content packs~~ **Done 24 October** (NP-0 to NP-6; PRs #17 and #18; `research/packs-2026-10/np5-proof.md` and `production.md`); NP-7 in the first live weeks | NP | About USD 2.7 to 5.3 (the planning probe spent USD 3.82 on 24 October) |
| 2 | ~~At the 26 October renewal: restore the standing caps on the working copy~~ Production carries the caps now (D36's figures, briefs per D42, set 24 October); the working copy is no longer the live system and keeps its caps closed | — | 0 |
| 4 | ~~Phase N4's rest~~ **Done 24 October** (section 5.0a, "N4"): the October backlog (6.B18), 7.X1 end to end on production, 6.C3. The collector (6.B1) moved to N7 (the owner, 25 October) | N4 | USD 2.79 (a brief 1.26, its Gate 2 refresh 0.74, its pack 0.68) |
| 5a | ~~Merge PR #20 and Command Center PR #4, then approve the deployments~~ **Done 24 October at the owner's request:** `main` at `77235ee` on all seven Atelier services; Command Center `be38d25`, its card reads "Live" | — | 0 |
| 6 | ~~Phase N5's system side with NP-7~~ **Done 26 October** (section 5.0a, "N5 and NP-7"; `research/n5-2026-10/README.md`): every NP-7 item built, proved on scratch copies and live; brief ratings, the week's measures, the tone loop, the caps for a week of use; the week's cycle on production. The packs budget goes back to USD 3.50 after the first live week (DEPLOYMENT.md, "Caps for a week of use") | N5, NP-7 | USD 2.20 (Client key, the proofs) and 0.39 (internal key, the cycle) |
| 7 | ~~The "Impromptu Zoom Meeting" documents~~ **Done 26 October**: 13 carry the title; three classified through the app as the team (delegated) from their recordings' names, the other ten already right | N5 | 0 |
| 5 | **For the owner:** personal accounts for Whitney and Gisselle (X.1): `USER_n_*` with a password hash each on Command Center (the owner sets the passwords), a `users` row each and `ATELIER_WIA_REVIEWERS` | N5 | 0 |
| 8 | ~~Phase N8, evidence and account memory~~ **Done 25 October** (section 5.0a, "N8"; `research/n8-2026-10/README.md`; PR #26). Left: 3.B17's "what we built" for the Week 2 venue waits on a record of the build in the corpus (WIA's sent emails and recaps, D25); 2.B11's fifth golden scene and archive-wide paraphrase search (N11) | N8 | USD 4.27 (Client key, the proofs) and USD 0.71 (internal key, production's extraction and embedding) |
| 9 | **Next: Phase N6**, reliability and the review document (section 5.0b): failure alerts by email, the review document's .docx, the nightly dump's monthly check, the E.B24 warnings; then N10; N7 last | N6 | About 0 |
| 3 | ~~Phase N3: M4 steps 1 to 5 on Railway~~ **Done 24 October** (section 5.0a, "N3 and S.C1"), with S.C1 and the Frontend in backend mode | N3 | USD 0.0001 |

**The brief-done checkpoint (revision 8.4): holds since 24 October** (`research/n2-delivery-2026-10/readings.md`, "The brief-done checkpoint"). This is the point where brief work stops and pack work starts. It holds when all three are true:
1. **N2's exit is met in full:** three briefs on the configuration of record, each with no content-level blocking finding and its reading recorded.
2. **Each brief's hand-off view** (`GET /storage/briefs/{id}/handoff`) carries every asset's copy with its piece key, the anchor and the message spine, read and checked against the brief. A pack stage consumes a brief only once Gate 2 has approved it (`can_consume`).
3. **The configuration of record is in `production-settings.json`** (done in N2; the output cap raised to 32,000 on 24 October).

After the checkpoint, a brief changes only for a defect that a live week (E.X9) or the pack stage finds. It is not refined further before packs.

Moved off the go-live path (N11, when funded): the re-extraction of Weeks 1 and 2, benchmark v2's rebuild with the October packet, the strategist v7 smoke runs on Weeks 1 and 2, the paid judge (D39) and the full gate (E.X4, D40).

### 5.0b The pending work as implementation phases

The work still open after 23 October, cut into phases for implementation runs (prompt 2 of `Implementation-Prompts.md` takes a phase name, or several, in place of its placeholder; prompt 3 verifies one or more of them). Phases N1 to N5, with NP for content packs, are the go-live path. After go-live, in priority order: N8, N7, N6 and N10 make the system fully operational (revision 8.8: N8 is core, the owner, 24 October); N11 runs when funded; N9 is not planned. Existing phase names are kept; NP was added and N7 lost Slack, without renumbering. Each phase's items keep their rows in section 5; a phase is done when its exit holds. Phases are named N1 to N11 (N for next), so they are never confused with the priorities P0 to P3 of section 0. Revision 8.2 merged revision 8.1's phases P1 (paid readiness runs), P2 (M1's paid exit) and P3 (the minimal gate) into N2 below, put the free-model shakedown before it as N1, and renumbered the rest.

| Phase | Items | Exit | Needs |
| --- | --- | --- | --- |
| **Phase N1. Free-model shakedown** (done 23 October; exit holds) | Section 5.0c, part 1: the shakedown profile and its isolation (a shakedown-only routing exception and adapter, guard tests that no paid or production path can use them); the whole M1 exit (section 5, "M1 exit") through the app on a scratch copy of the working data, every model-backed stage on free OpenRouter models, the production image in backend mode with every worker of the production order; the failure cases; every failure triaged into the shakedown ledger and every pipeline defect fixed at its cause with a test | Section 5.0c's N1 exit | D41 (the owner's permission, recorded); the free quota (1,000 requests a day on the internal key); no budget |
| **Phase N2. Minimal paid delivery run** (done 24 October; exit holds; the brief-done checkpoint holds) | Section 5.0c, part 2: steps 2 to 7 above on the working copy, in order, with their stop rules; the card and brief readings by the implementing agent (D39); the contingencies only on a failed reading; S.B8's writer step is the first brief, replayed in a fresh container; 6.B18's embedding; E.B31's extraction of the delivery window; the configuration of record written per part | Section 5.0c's N2 exit | N1's exit; the internal key's reset (26 October 00:00 UTC); about USD 2, at most about USD 3.8 with both contingencies |
| **Phase NP. Content packs** (new in revision 8.4; planned in revision 8.7: `Content-Atelier-Implementation-Plan-Content-Packs.md`, with an independent review applied) | NP-0 to NP-6 before N4: NP.X0 (done 24 October: D43 decided); NP.B1 to NP.B6 (migration 009, the hand-off view v2, the v2 pack contract in the v4 leaf shape and assembly, the start on Gate 2 approval, versions with edits, locks and states, the deterministic pack checks with consent, the `packs` budget with Opus 5.5's plumbing, the API); NP.B7 to NP.B9 (the finisher on Opus 5.5 at medium effort, the fidelity check, repair and re-check with sentence-level put-back and attestation, replay); NP.F1 to NP.F4 (the pack list and detail WIA saw on real data, editing and comparing, review and the Gate 2 hand-over, the week view); NP.B11 to NP.B13 (the week plan, the week's document, learning); NP.X1 to NP.X3 (the free-model shakedown, the NP exit test, one capped live Opus call, the paid proof on N2's three briefs and one held-out brief); NP-6 (production). **Done 24 October** (PRs #17 and #18; the content-packs plan's section 6 holds each item's status and evidence). NP-7 (**done 26 October**, the content-packs plan's NP-7 status): NP.B14 (the post-recording pass), NP.B15, NP.B10 (writer v5.1, three Reels in the brief, after its own reading), NP.X4, NP.X5, NP.B12's .docx, `pack-check.v3`. The old `packs/` path stays readable for v1 packs | The content-packs plan's section 11 on production: approving a v4 brief creates its pack (1 email, 3 Reels, 1 carousel), finished and checked, edited by hand and kept word for word, permissions left for WIA, with the week plan and document; the proof's three packs read and recorded | The brief-done checkpoint; D43 (decided 24 October); the owner's go-ahead for production (D13) |
| **Phase N3. M4 production foundation** (done 24 October; exit holds) | M4 steps 1 to 5: the Railway inventory; backups and the restore rehearsal on Railway (6.B6, 7.B5); the fresh dump after N2 restored into production (D20; L.B1 and L.B2 arrive with it; N2's October cycle and briefs with it); every service including the bulk worker, the standing budgets, `ATELIER_FATHOM_API_KEY` (0.B7, 6.B5, 7.B1); the context bootstrap, the knowledge-base version of record activated, `settings apply` with `mining_live` on, users seeded (7.B2) | Every service healthy; a test document normalised and embedded on production; settings, users and the active version match the record | N2; Railway signed in; the owner's go-ahead for each change (D13) |
| **Phase N4. M4 production go-live** (**done 24 October**; section 5.0a, "N4"; the collector moved to N7 and the Loom dropped, the owner, 25 October) | M4 steps 6 to 9: Command Center's sign-in (S.C1, done 24 October at the owner's request) and the Frontend in backend mode with its four variables (7.F2, done 24 October); the October backlog checked (6.B18, done); 7.X1 on the restored October cycle at the least cost (a card edited and refreshed with feedback, a brief edited and approved, the export) plus one new call through intake (done: imported by hand, extracted on production); 6.C3 (done) | 7.X1 recorded with run ids and cost; WIA signs in and sees real data (done for the shared account, 24 October) | N3 |
| **Phase N5. M5 delivery and first live weeks** (**system side done 26 October**, section 5.0a, "N5 and NP-7": everything WIA needs for these items works on production; what remains is WIA's own use, the two live weeks and their sign-off, and X.1's accounts, the owner's) | Delivery on 27 October (D35); E.X9 (WIA reviews live weeks; E.F1, E.F2, E.F4 and 5.B2 close with her decisions); X.2 (tone requests batched weekly; the benchmark run of each release only when funded, otherwise the agent's reading of the change on the last live week, recorded as delegated); 7.X2 (section 4.5's bar on two consecutive live weeks; sign-off); D26 said to WIA. A part of the configuration Whitney rejects is switched back by a setting at no cost | Section 4.5's bar met on two consecutive live weeks; WIA's sign-off recorded | N4; WIA |
| **Phase N6. Reliability and the review document** | 6.B4 (failure alerts: a failed or stuck job, a stopped intake connection, a budget refusal; the extraction-health panel); 5.B14's .docx (`python-docx`, the template in the image); 6.B6's nightly dump; the E.B24 checks still warning only, if any is to block | Each simulated failure produces one notification; one button and one command produce the week's .docx | N4 |
| **Phase N7. Scheduling and automatic collection** (revision 8.4: Slack removed; revision 8.10: the collector added and the phase moved last, the owner, 25 October) | First the calls since the last manual import (6.B18's command), then 6.B1 (the Fathom collector activated for new calls; 7.B6's connector step: exactly one collector, on production), then 3.B11 (the cycle on a schedule, Saturday 04:00 America/Chicago, O1), with the week's review document sent when the cycle finishes. Slack (3.B12, 5.B8, 6.B2: the digest, one-tap actions, live Slack intake; O27) is out for now (the owner, 23 October) | A new call arrives within the hour; the cycle starts by itself on its schedule and the review document follows | N4 |
| **Phase N8. Evidence and account memory** (core, revision 8.8; **done 25 October**, section 5.0a, "N8": the exit holds; 3.B17 and 2.B11 are partly done, their remainders data and search quality) | In order: 1.B12 (extension: identities, aliases and do-not-name flags, first because it makes the rest safe); 1.B13 (extension: internal calls as evidence of how WIA works, D24); 3.B17 (account memory beside a story card and in the writer's input, D25); L.B13 (weekly founder notes through the existing seeds, D29); 1.B11 (the 164 Zoom transcripts' dates, O13); 2.B11 (the Funktastic chain on production) | Identities and internal-call evidence used by the strategist and the brief writer with consent rules holding; account memory reaches a story card and the brief; the founder-note line works in the review document; the Zoom transcripts dated | N4 (decisions D24, D25 and D29 taken, section 7.2) |
| **Phase N9. Cycle, research and brief re-plumbing** (not planned) | Not planned (revision 8.4): carry-over from the original design that the working system does not need; an item returns only if a live week shows the need. Phase 3's re-plumbing (3.B1, 3.B9, 3.B5 rest, 3.B6 rest, 3.B8, 3.B13, 3.F1, 3.F3 to 3.F9); Phase 4's rest (4.B2, 4.B4, 4.B5, 4.B7, 4.B8, 4.B10, 4.B11, 4.B13, 4.B15, 4.F1 to 4.F4, 4.F6); Phase 5's rest (5.B5, 5.B9 to 5.B12, 5.F3, 5.F6, 5.F7); E.B28 (rest) and E.B29 (a) | Per item | N4 |
| **Phase N10. Hardening and operations** (core, after N6) | 6.B4 (rest), 6.B7 to 6.B9, 6.B12, 6.B13, 6.X1 to 6.X5, 6.F2 to 6.F8, 6.C1, 6.C2, 7.F1 (the frontend wiring audit), S.B1 (the OpenRouter dashboard check) | Per item | N4 |
| **Phase N11. Diagnostics, the full gate and later** (when funded) | When funded: the re-extraction of Weeks 1 and 2 with scene profile v3, benchmark v2 rebuilt with the October packet, the strategist v7 smoke runs, the full gate (E.X4 as written, about USD 14, D40); E.X8 (blind comparison with her finals), E.B3's paid judge run on WIA's labelled set (D39), the E.B3 and E.X7 extensions, L.B2 (extension), E.B24's caption-framework model check, E.B5, E.B8, E.B18 (after WIA's live labels), 6.B16, 6.B17, 6.C4, 3.B4 | Per item | N5 (WIA's live labels); funding |

Run them in this order: N1, then N2 to the brief-done checkpoint, N3 (done), then NP (the content-packs plan), then N4 once packs are live on production (the owner, 24 October), then N5 with NP-7. Then, in priority order: N8, N6, N10, and N7 last, so weekly automatic collection starts as late as possible (the owner, 25 October; revision 8.10); N11 when funded; N9 is not planned (revision 8.8). Verify after N1, after N2, after N4 and after each group of later phases (prompt 3).

### 5.0c Verification strategy for the paid runs (revision 8.2, 23 October)

The budget is the internal key's USD 5 a week (D36). Paid calls must therefore never be the place where a defect of the system is found: every defect the pipeline can show without a good model is found first on free models, and the one paid run that remains is the delivery itself. Quality is judged by the implementing agent's readings (D39) and the deterministic checks, not by a paid judge or repeated samples; Whitney's live weeks are the real measure (E.X9).

**Part 1. The free-model shakedown (Phase N1; USD 0).**

| Aspect | Rule |
| --- | --- |
| Data and place | A scratch database `atelier_shakedown`, restored from the latest dump of `atelier_work` (the real October calls; the owner's permission, D41), never the working copy or production. The production image built in backend mode, with the API, scheduler, editorial worker, bulk worker and intake worker of DEPLOYMENT.md's order |
| Models | Every model-backed stage on a free OpenRouter model (`:free`), chosen at run time from `GET /api/v1/models`: structured output (`response_format`) supported, context of at least 131,000 tokens (a whole week with the knowledge-base prefix is about 70,000), one model per role, recorded with its id in the shakedown record (on 23 October seven qualified, among them `nvidia/nemotron-3-super-120b-a12b:free`, `google/gemma-4-31b-it:free`, `nvidia/nemotron-3.5-super-vl:free`). Embeddings use the synthetic encoder in the shakedown (no free embedding model is assumed); the paid embedding of N2 step 3 proves the real route for USD 0.003 |
| Quota | 1,000 free requests a day on the internal key; the shakedown paces itself and records requests used. The first check of N1 is one free request: if the exhausted credit limit blocks free models, that is recorded and the owner is told (an OpenRouter privacy setting may need to allow free endpoints; the owner changes account settings) |
| Isolation (the core rule) | (1) A shakedown settings file (`deploy/shakedown-settings.json`) applied only to a database marked `run.environment = shakedown`. (2) A shakedown-only adapter in the `llm` package carries everything free models need that paid models do not: a routing exception allowing endpoints that collect data, for `:free` model ids only (S.B1's `deny-collection-zdr` policy stays the only policy anywhere else); dropping a parameter a free route does not support; pacing and backoff for its rate limits; its smaller output limits. (3) Guard tests: the live provider refuses a `:free` model, and the exception refuses to load, unless the database is marked shakedown; `production-settings.json` names no free model; a paid route never passes through the adapter. (4) No change to the core pipeline (prompts, schemas, validators, retry and repair counts, timeouts, budgets) is justified by free-model evidence alone |
| Triage, for every failure | Each failure goes into the shakedown ledger (`research/shakedown-2026-10/ledger.md`) as one of three kinds. **(a) Pipeline defect:** the system crashes, hangs, loses or duplicates work, writes a wrong state, shows no reason, or breaks a gate rule, whatever the model said. It is reproduced offline (the fake provider or a saved response), fixed at its cause with a test that fails before the fix, and the fix applies to paid runs too. **(b) Handled as designed:** the model's answer was bad (invalid JSON, a quote that does not bind, a missing field, a weak card) and the pipeline repaired it within its limits or failed visibly with the reason in the app. This is a pass: it proves the failure path paid runs will rely on. **(c) Free-model artefact:** behaviour paid models do not show (a rate limit, an unsupported parameter, a context or output limit, gibberish). It is absorbed in the shakedown adapter or recorded and ignored, never fixed in the core. A finding that would change what a paid call sends, or how its answer is judged, needs evidence beyond the free model (a saved paid response, or the code) before it is a defect |
| Coverage | Scene extraction (v3) on the delivery window; the strategy brief; a cycle from the app (strategist v7, card verification v4); a card edited and refreshed with feedback; a public-stance confirmation; develop, with the brief starting by itself (research planning, writing with writer v5 and contract v4, review, repair, verification); a brief line edited and refreshed with feedback (the line kept, a sibling rewritten); an attested fact; approval; the review document; the learning loop's categoriser (`mining_live`) on the gate feedback. Failure cases: a provider refusal for credit (HTTP 402, simulated at the adapter), a budget-cap refusal (a cap set below one call), a worker killed mid-brief, a 429 storm, a job past its timeout; each shows its reason in the app and recovers |

**N1 exit.** The whole M1 exit passes through the app at least once on free outputs (their quality is irrelevant); every failure case shows its reason and recovers; the ledger has no unclassified failure and no open pipeline defect; every core change made in N1 has a test that reproduces it without a free model; the guard tests pass; CI is green.

**Part 2. The minimal paid delivery run (Phase N2; about USD 2).** Steps 2 to 7 of the "Next step" table, on the working copy (after a fresh backup), each with `--estimate` first and inside the standing budget.

| Reading (the implementing agent, recorded as delegated, R55) | Passes when | If it fails |
| --- | --- | --- |
| **Cards** (step 5) | The deterministic flags raise nothing blocking; the slate holds at least three public cards that meet section 4.2 (Whitney's six fields, a plain title, the point passing the five tests: no platform or tactic lesson, no instruction to the reader, no frustration framing) and no idea of a kind WIA rejected; each card's evidence binds to a verified scene | Contingency A, once: the cycle again with strategist v6 (about USD 0.3 to 0.5), read the same way; the better slate is kept and the choice recorded |
| **Briefs** (step 6) | No blocking finding from the checks; none of W3 to W8's patterns; each asset follows section 4.3 on the agent's reading; a blind reading against the three recorded writer v4 briefs of 20 October (`research/eb23-brief-contract-2026-10-20/`, which are on other cards, so the reading compares craft, not content) does not prefer v4 | Contingency B, once per failed brief: that card again with writer v4 and contract v3 (about USD 0.43), read the same way |
| **Knowledge base 9** | The runs raise no more blocking accuracy flags than the recorded version 8 runs | Version 8 stays active; the runs' cards and briefs stand only if their own readings pass |

**Stop rules.** A paid step that fails in a way the shakedown should have caught stops the run: it is reproduced on free models or offline, fixed, and only then retried once. No paid step is retried more than once. A run whose estimate would pass the week's remainder is not started.

**N2 exit, status on 24 October: met** (section 5.0a, "N1 and N2"): three briefs on the working copy with their readings. **N1's exit holds** (`research/shakedown-2026-10/ledger.md`).

**N2 exit.** The delivery window is embedded and extracted; the October cycle and three briefs exist on the working copy with their readings recorded in `research/`; a fresh container replays one brief at USD 0; `production-settings.json` names, per part, the configuration that passed (one-sample result, D40), with the parts that failed at today's; the week's spend and remainder are recorded and the standing caps set to the remainder.

### M0. Decide and align (the owner; no build; today, 22 October)

| ID | Action | Done when |
| --- | --- | --- |
| D36 | Fund M1 to M3 and live operation (section 7 has the estimate) | Recorded 23 October: not funded now; the internal key's allowance and the fallback (section 7.2) |
| D26 | Tell WIA plainly that the 20 October packs were the hand-built target, what the first live weeks will look like, that scripts will need her voice pass, and how content packs reach her at go-live (D43) | Said, and recorded here with the date |
| S.C1 | Command Center's authentication. **Done 24 October at the owner's request** (`f58c6c4`; Command Center `d5b82b5`; `research/production-2026-10/README.md`): production refuses `AUTH_DISABLED` and needs `SESSION_SECRET` and `AUTH_PASSWORD_HASH`; one standard account `ai@weddingindustryads.com` (the owner); one sign-in (the Atelier's `/login` hands off to Command Center) and one sign-out (the session is revoked in Command Center and both cookies are cleared) | Done: checked on production with every refusal, the sign-in hand-off to a deep link, real data and both sign-out directions. Personal accounts follow X.1 |
| X.1 | Personal accounts for Whitney and Gisselle from their WIA addresses in the records (`USER_n_*` on Command Center, a `users` row each, `ATELIER_WIA_REVIEWERS`); the insider-term list, the beliefs-to-prove and offer-calendar files and Whitney's attested AI-assistant fact are the engineer's reading under D12 (revision 8.8: no question waits on WIA) | Accounts created in N4; the rest recorded as delegated |

### M1. The live path in code (P0; no Railway needed)

Build on the path the live development week of 18 October already ran (the window selection, the weekly runner on ledger scenes, the card screen, the v3 brief and Gate 2), not on Phase 3's re-plumbing. Test against a scratch copy of `atelier_work` in the production image.

| ID | P | Effort | Work | Done when |
| --- | --- | --- | --- | --- |
| 6.B18 | P0 | S | **Done (22 and 23 October): imported in the build, embedded in N2 (241 chunks, USD 0.0033).** **The October calls, first.** A one-off command: list Fathom meetings in a date range through the API, write each in the native Fathom folder shape (with its `metadata.json`), `documents import`, then `documents reembed` under a run plan (an imported file is not embedded on its own) | The 5 to 19 October calls are documents in the working copy, dated by Fathom, normalised and embedded; a later live collection adds no duplicate |
| S.B15 | P0 | S | **Green baseline.** Remove the stale exception for `frontend/src/data/fathomWeeklyAngles.ts` in `test_client_material_guard.py`; make `backend/docs/Calendar-Deployment.md` match the code or mark it historical; replace the venue names and call references in the mock data with anonymised text (R48 allows client material only under `research/` and `backend/knowledge_base/`) | CI green on `main` |
| 7.F2 (build) | P0 | S | **The real app is a production build.** `ARG VITE_ATELIER_MODE` in `frontend/Dockerfile`, `backend` for the production service; the mock only as an explicit demo build (`mock`) for Looms, never the production default; DEPLOYMENT.md names the flag, corrects the queued-deployment warning, and marks `COMMAND_CENTER_PUBLIC_ORIGIN` as always required (it says "when the auth origin is private", but `frontend/server/sso.mjs` returns 503 whenever it is unset) | A production image built without arguments serves the real app; the mock needs an explicit argument |
| 3.B2/3.B3 (go-live subset) | P0 | S to M | **A cycle over a date window, from the app.** An approver route and button wrapping `documents select` (window, document count, undated documents listed for a person, the estimate shown before the run starts); the run records every selected document and the scenes the strategist saw (scene coverage); a call that arrives after its window's cycle is listed for the next window (O25) | An approver starts a cycle for 12 to 19 October from the app; the run lists its documents and scene coverage; a test proves no verified scene of a selected call is dropped below the context budget |
| 4.B1 | P0 | S | **Developing a card starts its brief live**, under the standing budget: Gate 1 queues the first brief in live mode instead of replay (today the replay run it queues also blocks a later live start, because the first brief's run key ignores the mode); replay stays a test mode | Develop starts research and writing with no command; developing twice makes one brief; over budget, the brief waits with the reason shown on the card |
| 6.B3 (go-live subset) | P0 | S to M | **Standing weekly budgets.** A database run plan per purpose (cycle, briefs, refreshes, embedding, extraction, context mining) with a weekly cap, renewed by the scheduler and found by the workers without a per-plan variable, so a live week needs no new variable or redeploy (today the live provider reads its plan from `ATELIER_RUN_PLAN_ID`) | A week's cycle, three briefs, two refreshes and the learning loop run under standing plans; the call that would pass a cap is refused before sending (E.B1's check) and the refusal is shown in the app |
| E.B1 (extension) | P0 | S | **Provider failures that lose money.** A response with `content: null` and a length finish (Sonnet 5.5 through Google forces reasoning and returned null content at 9,000 to 16,000 output tokens on 20 October) is retried once with a raised limit or another route, and recorded; card verification and brief review run on Sonnet 5.5 in production | A test with a recorded null-content response retries and records both calls |
| 3.B7/3.F2 (go-live subset) | P0 | M | **Gate 1: edit any field, refresh with feedback, add context.** (a) Every card field editable from the card screen (`PATCH /angles/{id}` accepts all but `rank` and `moment_ids`). (b) "Refresh with feedback": a new card version from the reviewer's text through a feedback variant of `card_reframe` (a new prompt version), re-verified like any reframe, keeping fields the reviewer edited verbatim. (c) Context and attested facts (5.B7) | Each works from the screen; a refreshed card keeps the reviewer's edited title word for word and changes the fields she did not edit; a stale hash shows the conflict handler with the input kept |
| 5.F1, 5.B6, 5.F4, 5.F5 (go-live subsets) | P0 | M | **Gate 2: edit every field, refresh with feedback.** (a) Every section and every asset field editable on v3 (subject options, preview, body; each Reel's cover, opening and script; each slide; the caption), and v4's new fields when E.B33 lands. (b) Refresh with feedback for v3 and v4 in live mode through `POST /briefs/{id}/revise`, with revision instructions the writer template uses (today only the v1 template does). (c) **Locks at the level of the line:** a person's edit locks that asset field, not the whole `format_plan` section (`gate_two.py` locks top-level sections today), so a refresh keeps the edited line and still rewrites the rest; a draft that changes a locked line is refused. (d) The versions list for v3 and v4, with author and reason | On a v3 brief from the screen: after an edited subject line and a refresh, the subject line is identical **and** an unlocked sibling (the preview, a slide) has changed; versions are listed |
| 5.B7 | P0 | S | **Add context, including attested facts** (R57). Free-text context at either gate. A fact an approver states as true enters the ledger as `attested` with the person and date, may appear in copy, and is shown as attested at Gate 2; a paraphrase of a client's words is marked as a paraphrase, never quoted verbatim | W8's correction can be added at Gate 2 and passes the ledger without a blocking finding |
| 5.F2 | P0 | S | **Gate 2 names its blockers** (open question, blocking finding, stale, unconfirmed CTA, role), in words a non-technical reviewer reads (R50) | Each blocker is shown by name in a test |
| 1.F6 | P0 | S | **Resolve a waiting call in the app.** Relay `POST /documents/{id}/classification` (allowlist and server test) and give editors the control on the Sources screen, so a call the rules cannot classify does not need the command line | An editor classifies a waiting call from the screen; the decision is recorded and never overwritten by a rule |
| 6.B4 (go-live subset) | P1 | S (after delivery, section 5.0) | **Failures are seen.** A failed or stuck job, an intake connection that stops collecting, and a budget refusal notify the team by email (Slack is out for now) and show on the extraction-health panel (K36) | Each of the three, simulated, produces one notification |
| 5.B14 | P1 | M (Markdown by 27 October; the .docx after delivery) | **The week's review document:** one export of a cycle's cards and briefs with all asset copy, in the layout WIA reviews, rendered from the brief's structure (not by parsing Markdown, as `research/v2-reassessment-2026-10-20/tools/packs2docx.py` does), with `python-docx` added to `requirements.txt` and the template .docx shipped in the image; plus Markdown | One button and one command produce the .docx for a cycle; it opens in Word and Google Docs with the 13 October header |
| S.B8 | P1 | S (after delivery) | **Done (23 October, N2): the stack's editorial worker, the production image from the documented variables, wrote a v4 brief live; a fresh keyless container (`research/n2-delivery-2026-10/replay.env`) replayed it at USD 0, 8 calls replayed, the document byte-identical.** **The production image end to end:** its open writer step (one paid call; `research/sb8-container-2026-10-20/README.md`), then the replay in a fresh container | A container from the documented variables writes a v3 brief, and a fresh one replays it at USD 0 |

**M1 exit.** On a scratch copy of the working database, in the production image built in backend mode, with every worker the production order names: an approver runs a cycle for a date window from the app; edits a card and refreshes it with feedback; develops it, and the brief starts by itself within the standing budget; edits an asset line, refreshes the brief with feedback, adds an attested fact, approves; exports the week's review document as Markdown. **Failure cases:** a worker killed mid-brief leaves a run that resumes or fails visibly with a retry; a provider refusal for lack of credit (HTTP 402) and a budget-cap refusal each show their reason in the app; the longest October call extracts within its job timeout (K13). CI is green. **Met on 23 October:** through the app in the production images, on free models with every failure case (N1, `research/shakedown-2026-10/ledger.md`), then paid on the working copy (N2, `research/n2-delivery-2026-10/readings.md`; K13: 106 seconds for the longest call).

### M2. Output to the standard (P0; no Railway)

The v2 method's steps mapped onto stages (section 2.2). Every prompt change is a new profile; released profiles stay byte for byte (E.B17). Week 2 stays out of every prompt and exemplar (D28): contrastive pairs come from Week 1, whose review document holds Whitney's rewrites. Paid steps here (the re-extraction, one strategist v7 run on Week 1) cost about USD 1 under run plans (D36).

| ID | P | Effort | Work | Done when |
| --- | --- | --- | --- | --- |
| E.B27 (packets) | P0 | S | **Benchmark v2 packets**, built from the ledger with no model call, each reporting its scene coverage: Week 1 (Whitney's rewrites as reference), the whole of Week 2 (eleven calls), and a held-out October window no prompt has seen (after 6.B18). Rebuilt after E.B31's re-extraction. Benchmark v1 stays for replay | Every packet lists every included call and every verified scene within budget |
| E.B28 (go-live subset) | P0 | S | **The window's strategy brief, as beliefs to prove.** A deterministic assembler, no model call, from KB 14 (content plan), 16 (beliefs), 01 (Savannah's priority series), 05 (offers with status and do-not-undercut) and the published register: four to six `beliefs_to_prove`, each with its offer and its do-not-repeat pieces; live offers; recent central points; the season. Stored with the cycle and its hash, shown at Gate 1, passed to the strategist | Every cycle has one, shown at Gate 1; on a constructed offer calendar, a card that undercuts a live offer is held with the offer named |
| E.B31 | P0 | M | **Partly done (23 October, N2): the delivery window extracted with v3 on Luna, 147 verified scenes, USD 0.09, in production settings; Weeks 1 and 2 in N11.** **Scene profile v3: human lines and counter-expected decisions.** Two scene types beside v2's: a verbatim human line (feeling, a self-description, a business confession) and a WIA decision that went against the default or cost WIA something; the packet lists them first. Re-extract Weeks 1 and 2 and the October calls under a run plan (about USD 0.5: the 91-document backfill cost USD 0.94); v2 stays for replay | On Week 2, the four scenes of section 2.6 (item 9) are scenes of the new types |
| E.B30, E.B32, E.B29 (change) | P0 | M | **Done for go-live (23 October, N2): the October cycle on v7 and v4 passed the card reading and both are in production settings; the Week 1 smoke run is in N11.** **Strategist v7 and card verification v4.** The card contract is section 4.2: her six fields at her length, plus `point`, `point_is_about`, `surprise_for_experienced_advertiser`, `reader_takeaway`, `reader_fit` (matched against her ELEVATE and Accelerator buyer statements, KB 11 and 16), `belief_ref`, `offer_fit`, `public_stance` and a `guardrail` the writer reads; plain titles (v6's limit on "we"-led titles is dropped); one public card per client conversation; recurrence as context only; KB 19 as examples. The verifier rejects for public use a point about a platform or tactic, a takeaway that instructs the reader, and a reader fit that presents ads or an offer as frustrating, with the reason at Gate 1 (the card may still be internal); a `public_stance` card cannot be developed until confirmed. The card screen renders her six fields | On Week 1 (one paid run), cards such as "Give distinct markets distinct landing pages" are rejected or reframed with the reason shown; constructed cards trip each test once and a passing card raises nothing |
| E.B33 | P0 | M | **Done for go-live (24 October, N2): three briefs passed their readings, and a blind reading ranked all three above the writer v4 briefs; in production settings.** **Brief contract v4 and writer v5.** Contract: the sections in the 13 October order; each Reel with a `kind` (story, stance, broll_text), an `on_screen_hook`, its own caption and, for b-roll, one to three `screens`; a carousel `title` and caption; the email's send header (DATE, SEND TIME and RECIPIENTS proposed for WIA to confirm); a `register` per asset; an `offer_descriptor` where an offer is named. Writer: same idea through different doors (replacing v4's "each a distinct point"); register by format, scripts modelled on her recorded Reels (KB 18); offers with their approved descriptors; one moment and at most two concrete details, the right person credited; her real closings from the CTA catalogue and the ones she never uses banned; locked lines kept; revision instructions from a refresh (M1) used; section 4.3's first-touch rules as a checklist per asset. The reader, the Gate 2 editor, the hand-off view and the review document render v4 | A v4 brief renders and edits in every one of those places; v1 to v3 briefs still render and pass their gates |
| E.B34 | P0 | S | **WIA's corrections as rules, with her text as the tests** (R60): (a) subject lines (rule 3); (b) slide 1 carries the title's promise (rule 2); (c) covers, on-screen hooks and the first b-roll screen name the concrete subject (rule 1); (d) insider terms, extending the existing `block_terms` check (`briefs/validation_v2.py`) with a first-touch scope and one explained use in a script or body, and a glossary in KB 05 (rule 4); (e) who did what (rule 5). Specificity outranks distinctness | Each of W3 to W8, and the 13 October subject and slide-1 notes, is a test case the checks flag on the v2 text and pass on her corrected text |
| E.B24 (extension) | P0 | M | **The checks that enforce section 4.3** (R60), as Gate 2 findings, blocking only where marked. From revision 7.3's list: caveat language in copy; outcome verbs against the evidence (blocking); a self-audit last line; sibling overlap of sentences and of detail lists (a warning; a subject repeating the anchor Reel's hook is allowed); banned phrases; aphoristic kickers; detail density (more than three operational details in one story); hook fidelity against the ledger (who decided, what a tool did; blocking on a mismatch unless attested); the takeaway test and DIY drift on every asset. From the format rules: email send header and no bullet lists; "-Whitney" on first-person captions; a carousel CTA for both DIY and done-for-you readers; the offer descriptor on CONVERT assets; register (scripts spoken, emails and captions not); CTA patterns she never uses. Across the cycle's briefs: one offer CTA a week on Instagram; covers distinct across the week. The first-touch checks are E.B34's. Savannah's caption framework as a model check moves to M6 | Every check has a failing and a passing test from WIA's own text; the v2 packs raise only the findings W3 to W8 name |
| E.B25 (i), (j); L.B12; 3.B5 (extension) | P0 | M | **Knowledge-base version 9,** compiled like versions 5 to 8: KB 18 (spoken exemplars, her 18 August and $70K Reel transcripts first); KB 19 (six to eight of her raw-to-final chains, her own text only, D34); the published register at piece level (the 5 October giveaway's pieces with their own points); same-point recency as a ranking penalty inside the window (D23: 60 days, 30 for a fresh angle on the same point); offer descriptors and the insider-term glossary in KB 05; the first-touch rules stated in general terms and her own published subject lines and covers as exemplars in KB 09, whose slide count is reconciled with section 4.3. Her 20 October corrections concern Week 2 text, so they are tests (E.B34), never prompt exemplars, while Week 2 is a benchmark (D28) | Version 9 compiles from committed inputs, its hashes are recorded, and the prefix stays within its 30,000-token budget; its accuracy is measured inside M3's gate |

**M2 exit.** Everything above is on `main` behind profile settings, with its tests; nothing is the production default until M3 passes.

### M3. Measure, lock and prove it repeats (P0; paid; no Railway)

| ID | P | Effort | Work | Done when |
| --- | --- | --- | --- | --- |
| E.X4 (with E.B27's runs) | P0 | M | **For go-live the minimal gate replaces this row (D40; section 5.0c, N2's readings); the row stands as the full gate, optional, run only if the owner funds it.** **The minimal gate ran on 23 October (N2): the cards, the brief and knowledge base 9 passed their readings, one sample each (`research/n2-delivery-2026-10/readings.md`); `production-settings.json` names the configuration; two of the three briefs are still to read.** **The gate,** under run plans, on Sunday 25 October, on benchmark v2's packets (E.B27). **Configurations:** the new one (strategist v7, knowledge base 9, writer v5 with contract v4) against today's (strategist v6, knowledge base 8, writer v4 with contract v3). **Ideas:** both strategists, three samples per week. They pass when, on Week 2, the three v2 ideas (the budget approach, what strategy calls cover, understanding your own account) are in the slate or the considered list in at least two of three samples, with at least two in the slate; no slate holds a rejected idea (a platform lesson such as "Meta takes your instructions literally"; the office-hours walkthrough); every public card passes the five tests; titles are plain; and knowledge base 9 raises no more blocking accuracy flags than knowledge base 8 (its R44 record). **Briefs:** on the top three cards of one v7 sample for Week 2 and for the October window (six cards), writer v5 in three samples per card (stability) and writer v4 in one (the baseline of the blind reading). They pass when every v5 brief has no blocking finding in three of three samples, none of W3 to W8's patterns recurs, and a blind reading by an implementing agent, with the configurations hidden and the order shuffled, prefers v5, recorded as a delegated review (R55; D39 replaced the paid judge). **Independence:** the checks were written from Week 2's text, so Week 2's brief results are a regression check only; the brief gate's evidence is Week 1 and the held-out October window. A sample that differs is reported, not discarded | The result is in `research/`; `backend/deploy/production-settings.json` names the configuration that passed, or the gap is reported and section 5.0's fallback for the gate applies |
| — (replay) | P0 | S | **It replays:** the chosen runs replay in the production image at no cost (0.B4's mechanism, in S.B8's container) | Identical output, no provider call |

Expected cost of the full gate: about USD 14, from recorded runs: 24 briefs at about USD 0.43 each (E.B23's three briefs cost USD 1.30), 18 strategist runs on whole weeks with verification (about USD 3 to 4; benchmark v1's passes cost USD 0.5 to 0.8 on excerpts); the comparison is a blind delegated reading at no provider cost (D39). Each run is estimated with `--estimate` before its plan is created. The held-out October window is the most recent complete week of calls, so what WIA reads on 27 October (D35) is one sample of the gate's own October run, its index recorded before generation (the sample protocol of revision 7.3's E.B13): nothing is generated twice, no prompt was tuned on it, and the other two samples show the variation. Expectation to state to WIA (D26): ideas comparable to v2 on a week with real moments; emails and carousels publishable after light edits; scripts need Whitney's voice pass.

### M4. Production (P0; Monday 26 October; Railway access and the owner's go-ahead for each change, D13)

DEPLOYMENT.md's order ("Production services on Railway"), with these corrections: the data is a fresh dump of the processed working copy (D20); the Frontend builds in backend mode.

| Step | Work | Done when |
| --- | --- | --- |
| 1 | Sign the Railway CLI in; inventory the project against section 2.4; skip every queued Frontend deployment | **Done 24 October:** the inventory is recorded (`research/production-2026-10/README.md`, step 1) |
| 2 | Backups on; a restore rehearsal on a scratch database (6.B6 go-live subset; 7.B5's rehearsal) | **Done 24 October:** Railway volume backups need a Pro workspace (refused; no billing change), so the nightly dump (`backend_pipeline.backup`, the `db-backup` cron service) keeps them in the bucket; the rehearsal restored 41 of 41 tables and 12,609 rows into `atelier_rehearsal_n3`, then dropped it |
| 3 | A fresh `pg_dump` of `atelier_work` after N2 (the October calls, the re-extracted scenes, the October cycle, three briefs, knowledge base 9); restore into `postgres`; copy the artifacts; L.B1's and L.B2's production state arrives with the restore | **Done 24 October:** counts match the working copy (41 tables, 12,609 rows); 8,224 artifacts copied and read back (574 MB) |
| 4 | Services `api` (pre-deploy migration), `scheduler`, `editorial-worker` (`interactive,default`), **`bulk-worker`** (`bulk`), `intake-worker`, and `db-backup` (cron); variables per DEPLOYMENT.md; `token_budget --store` per model; the standing budgets (6.B3); `ATELIER_FATHOM_API_KEY` (7.B1, 6.B5) | **Done 24 October:** every service healthy; a synthetic test document normalised and embedded by production's bulk worker (USD 0.000094), then excluded |
| 5 | The context bootstrap check; the knowledge-base version of record active; `settings apply` with the configuration of record and `context.schedule.mining_live` on; `users seed` (7.B2, O2) | **Done 24 October:** the bootstrap commands change nothing; `kb-compile` reports version 9 unchanged; settings 18 of 18 unchanged; one user row, `ai@weddingindustryads.com` (`admin`), until WIA names its approvers |
| 6 | **S.C1:** Command Center refuses `AUTH_DISABLED` in production; `SESSION_SECRET`, `AUTH_PASSWORD_HASH` and real accounts; the Atelier card links to the app (6.C3) | **Done 24 October** (built at the owner's request): `AUTH_DISABLED` removed and refused, the standard account signs in, one sign-in and one sign-out with the Atelier. Personal accounts follow X.1 |
| 7 | The Frontend in backend mode with `ATELIER_BACKEND_ORIGIN`, `ATELIER_API_SECRET`, `COMMAND_CENTER_AUTH_ORIGIN` and `COMMAND_CENTER_PUBLIC_ORIGIN`; approve only the newest deployment (7.F2) | **Done 24 October:** the deployment of `f58c6c4` approved; a sign-in from Command Center opens the Weekly Studio on real data (the five restored briefs, the budgets) |
| 8 | The October backlog (6.B18); the Fathom collector activated for new calls (6.B1) | **Done for the backlog (24 October, N4):** 39 October meetings listed, 23 already documents, 11 second recordings not imported, 5 imported by hand and normalised, embedded and extracted by production's workers; every October call is a dated document. **The collector moved to N7** (the owner, 25 October), with "a new call arrives within the hour" |
| 9 | **7.X1, live verification** (7.B6 is the cut-over): one window of real calls end to end on production (intake, scenes, cycle, Gate 1 edit and refresh, brief, Gate 2 edit and refresh, approve, export), with its cost | **Done (24 October, N4;** `731dedc`, `18745b3`, `d9adebb`**):** recorded with run ids and cost in `research/golive-2026-10/README.md`. A new call imported, embedded and extracted; on the restored October cycle (5.0b's least cost) a card edited and refreshed, developed, its brief waiting on a spent budget with the reason and released, edited, refreshed and approved, its pack finished and edited, the review document and the pack document exported; USD 2.79. 7.B6's connector step moves to N7 with 6.B1 |

### M5. Delivery and the first live weeks (P0; from Tuesday 27 October; WIA)

| ID | Work | Done when |
| --- | --- | --- |
| E.X9 | **WIA reviews live weeks in the app** (replaces E.B13, E.X3 and E.X6's held-out Week 5, D37). Each week: the system runs the cycle; the team reads it for factual and consent problems only (recorded as delegated, R55); Whitney decides at Gate 1 and Gate 2 and rates cards and briefs on rubric 2.3a in the app (E.X7). E.F1, E.F2, E.F4 and 5.B2 close with her first real decisions. **System side done (`c9f9236`, 26 October):** Gate 2 takes the rubric ratings on briefs, as Gate 1 on cards, and a decision is WIA's label only when its reviewer is on `ATELIER_WIA_REVIEWERS` (`test_ex9_gate_two_rubric_db.py`). Her own decisions wait for her use, and on personal accounts (X.1) | Her decisions and ratings are rows labelled as hers |
| X.2 | **Tone change requests** (the tracker promised on 20 October), batched weekly: the week's requests enter the review queue as rule or exemplar candidates (L.B3), are compiled into one version, pass one benchmark run from a checkout (benchmark inputs stay in `research/`, R48) and are released with the result; an urgent request about a single brief is handled at Gate 2 by editing, not by a knowledge-base change. **System side done (`4fa13c0`, 26 October):** a request and a correction given twice reach one compiled version, made active by the named result, which the version's record keeps; the benchmark run happens when funded, otherwise the agent's reading, recorded as delegated (`test_x2_tone_loop_db.py`; DEPLOYMENT.md, "The weekly tone loop") | Each request has a record from request to release, and each release one benchmark result |
| 7.X2 | **Acceptance:** section 4.5's bar on two consecutive live weeks; WIA's sign-off. **Partly done (`4b9b392`):** `storage_cli week-measures --week <id> [--json]` reads section 4.5's and the content-packs plan's 4.6 measures for a week from the database, WIA's own rows apart from delegated ones (`DEPLOYMENT.md`, "Week measures"); the two live weeks and the sign-off remain | Recorded |

### M6. After go-live (P1 and P2; not on the go-live path)

Revision 8.4 cuts this to what the working system needs (the owner, 23 October). The short list comes first; the rest is optional, not planned, or out. L.B14 and 1.F7, listed here in revision 8, were built on 23 October (section 5.0a).

**The short list (Phases N6 and N7).**

| ID | Work | Done when |
| --- | --- | --- |
| 6.B4 (go-live subset) | Failure alerts by email: a failed or stuck job, an intake connection that stops collecting, a budget refusal; the extraction-health panel | Each of the three, simulated, sends one email |
| 6.B6 (nightly dump) | A nightly database dump kept off the database's volume, with a monthly restore check | A restore from last night's dump matches production's counts |
| 5.B14 (.docx) | The week's review document as .docx (`python-docx`, the template in the image), beside the Markdown | One button and one command produce it; it opens in Word and Google Docs |
| E.B24 (the warnings) | Each E.B24 check that still only warns either blocks, on evidence from live weeks, or stays a warning by decision | Recorded per check |
| 3.B11 | The cycle on a schedule (Saturday 04:00 America/Chicago, O1); the week's review document follows the cycle | The cycle starts by itself and the document follows |

**After the short list** (revision 8.8: Phases N8 and N10 are core; N11 runs when funded).

| ID | Work |
| --- | --- |
| 3.B17 | Account memory beside a story card and in the writer's input (D25). **Partly done (`f762030`, `0125d99`, `01fba86`, `7814344`):** the account's dated timeline from its calls, internal meetings, published content and sent emails (`accounts.py`); its state and what happened after the card's call beside a client story card at Gate 1 and Gate 2 (shown for the Week 2 venue's card on copy D at 1024 and 375 px); writer v5.2 receives the later records as evidence with their sources and keeps claims to what they show. Remaining: the Week 2 venue's "what we built" is not in a brief because no record in the database shows the June recommendation built (the 9 September meeting in the research notes is not in the corpus); the brief says so in its before-publishing item. A record of the build (WIA's sent emails or recaps in the context store, D25) completes it |
| 1.B12, 1.B13 (extensions) | Identities (aliases, do-not-name flags); internal calls as "team practice" evidence (D24). **Done (`ff29b40`, `f762030`, `95f4977`, `95f1370`, `7814344`):** the Week 2 venue owner's meeting handle and nicknames resolve to her and her account; a prospect's pronoun (she/her) is recorded and reaches the strategist and writer v5.2; a copy reference that would link a never-named client to her anonymised case study blocks a card, a brief and a pack (`test_n8_units.py`, `test_n8_evidence_db.py`). The Week 2 account review and survey service reached strategist v8 as team-practice scenes (copy D's paid cycle); a client name or figure only an internal meeting carries blocks a constructed card and brief |
| L.B13 | Weekly founder notes through the existing seeds (D29). **Done (`ff29b40`, `f762030`, `0125d99`, `95f1370`):** a founder note is a seed linked to its call (migration 010, the seed form); strategist v8 reads it with its call named as the scenes name it; paired with three scenes on copy D's paid cycle (and shown unanswered on copy C's free one); the week's review document carries the line |
| 6.B7 to 6.B9, 6.B12, 6.B13, 6.X1 to 6.X5, 6.F2 to 6.F8, 6.C1, 6.C2, 7.F1, S.B1 | Hardening: cost summary, runbook, removal on request, monitoring, role tests, failure drills, screens, the frontend wiring audit, the OpenRouter dashboard check |
| 1.B11, 2.B11 | The Zoom transcripts' dates (O13); the golden fixture chain on production. **1.B11 Done (`e7a2390`):** every Zoom transcript dated with a source or to its week folder (63 to the day, 101 to the week, `date_evidence`). **2.B11 Partly done (`95f4977`):** the golden scenes marked from the published pieces (`research/golden-scenes/funktastic-chain.json`) and measured on production; scenes v1 and v2 find 4 of 5, v4 3 of 5; search by paraphrase finds 4 of 5 in the top 10 within the account, 1 of 5 in the top 25 across the archive. Remaining (N11): the fifth scene (Whitney's summary relay) and archive-wide paraphrase ranking |
| E.B24 (model check), E.B28 (rest), E.B29 (a) | The caption-framework model check; buyer-world shifts and objections by offer; the cross-call synthesis pass |
| N11's list | The re-extraction of Weeks 1 and 2, benchmark v2's rebuild, the v7 smoke runs, the full gate (E.X4, D40), E.X8, E.B3's paid judge run (D39), the E.B3 and E.X7 extensions, L.B2 (extension), E.B5, E.B8, E.B18, 6.B16, 6.B17, 6.C4, 3.B4 |

**Not planned** (Phase N9: carry-over from the original design that the working system does not need; an item returns only if a live week shows the need):
- 3.B1, 3.B9, 3.B5 (rest), 3.B6 (rest), 3.B8, 3.B13, 3.F1, 3.F3 to 3.F9;
- 4.B2, 4.B4, 4.B5, 4.B7, 4.B8, 4.B10, 4.B11, 4.B13, 4.B15, 4.F1 to 4.F4, 4.F6;
- 5.B5, 5.B9 to 5.B12, 5.F3, 5.F6, 5.F7.

**Out for now** (the owner, 23 October): Slack, that is 3.B12, 5.B8 and 6.B2 (the digest, one-tap actions, live Slack intake; O27).

---

## 6. What this phase does not do

| Not in this phase | Why, and where it goes |
| --- | --- |
| Scheduling or publishing packs into any tool, designs, Stories, Threads, ad variants and performance attribution (the content-packs plan, sections 4.5 and 9) | Packs themselves are in scope for go-live (the owner, 23 October; Phase NP). The brief's hand-off view (`GET /storage/briefs/{id}/handoff`: keys, anchor, message spine, `can_consume`) is their interface. The existing `packs/` code accepts only v1 briefs and five fixed slots and stays off (`features.packs=false`) until NP replaces or extends it |
| Slack: the digest, one-tap approvals and live Slack intake (3.B12, 5.B8, 6.B2; O27) | Out for now (the owner, 23 October). The app is the decision surface, failure alerts go by email (6.B4), and the weekly cycle runs on a schedule (3.B11, N7) |
| Feedback-driven refresh of copy after Gate 2 | After approval, WIA edits the pack's copy by hand in the Atelier, and it is kept word for word (the team's promise on 20 October; the content-packs plan, NP.B3 and NP.F2). The feedback refresh stops at the brief, except NP-7's two passes a person starts with their own input (the post-recording pass from Whitney's recorded words, NP.B14; finishing again with a permission she grants, NP.B15). L.B9 captures the published final and its difference for learning |
| The client knowledge base (Command Center) and performance data in it | A separate product, starting after the week of 27 October |
| A held-out Week 5 judged by Whitney (E.B13, E.X3, E.X6) | Replaced by live weeks (E.X9, D37); the held-out October window stays in the internal gate |
| A staging environment | D13: production only, with restore rehearsals |
| The optional ChatGPT companion (E.X5) | Dropped; no stage reads ChatGPT or the raw export (R52) |

---

## 7. Decisions

### 7.1 Open, for the owner now

None (revision 8.8). Every WIA-side question is decided under the delegation (D12, the owner, 24 October) and recorded in 7.2. What stays the owner's is money (funding N11, about USD 14) and production go-aheads (D13).

### 7.2 Settled in revision 8

| # | Decision | Answer (22 October 2026) | Basis |
| --- | --- | --- | --- |
| D24 | Internal calls as evidence for public content | **Yes** (revision 8.8): they evidence how WIA works (process, standards, decisions); never names, figures, or a story about an unhappy client | Delegated (D12), the owner's direction, 24 October |
| D25 | Account-memory sources and consent | **All WIA records about the client:** later calls, WIA's sent emails and recaps in the context store, published content; Slack when a connector exists. Client stories stay anonymous unless the evidence's consent allows a name (O3) | Delegated (D12), 24 October |
| D26 | What to tell WIA about the 20 October packs | Said at delivery (N5): they were the hand-built target; what WIA receives is system output; the packs are finished by a step that keeps her lines word for word; scripts get her voice pass | Delegated (D12), 24 October |
| D27 | Permissions to publish results | Results the record supports may appear anonymised; a named result or a client's identifying story carries a before-publishing note for the client's okay, never a system gate | Delegated (D12), 24 October |
| D29 | Weekly founder notes | **Yes:** one optional "what stood out this week" line in the review document, entered through the existing seeds (L.B13) | Delegated (D12), 24 October |
| D31 | Stance confirmation before developing a public-stance card | Adopted (built in E.B30) | Delegated (D12) |
| D33 | Whether "here's how we worked through it" reads as instruction | **Ruling:** allowed when it narrates WIA's work with a client; the takeaway test (no instruction to the reader) stays | Delegated (D12), 24 October |
| D34 | Whitney's drafts and finals as KB 19 exemplars | Allowed (built in knowledge base 9) | Delegated (D12) |
| D38 | Release held-out Week 6 for the $70K Reel in KB 18 | Released for KB 18 only; Week 6 stays out of benchmarks | Delegated (D12), 24 October |
| D42 | The briefs budget | USD 2.70 a week on production (three briefs), set in N3 | The owner's ceiling; set 24 October |
| D43 | The pack design (Phase NP; revision 8.4, detailed in revision 8.7) | **Decided (the owner, 24 October).** D43a: every pack is 1 email, 1 carousel and 3 Reels (story, stance, b-roll text), live on production before N4. D43b to D43j as the content-packs plan's section 9 recommends:<br>• (b) a finisher after Gate 2 (Opus 5.5, medium effort) inside a fidelity loop (Sonnet 5.5 check, one repair, re-check, sentence-level put-back), with Gate 2's unedited copy a draft that the pack finishes and every line a person wrote kept word for word;<br>• (c) the pack starts by itself on Gate 2 approval of a v4 brief;<br>• (d) review in the pack (edit kept word for word, clear quotes, attest findings, WIA clears permissions, ready, published), with no feedback refresh;<br>• (e) a proposed week plan computed on read, with no scheduling or publishing;<br>• (f) a `packs` budget of USD 6.00 for the week of 26 October, then USD 3.50 a week (production's caps USD 11.00, then 8.50);<br>• (g) the team takes all three N2 briefs through Gate 2 under delegation, with each client-permission item answered as a before-publishing note (revised by the owner, 24 October; done on production 24 October);<br>• (h) the week's document in Markdown at go-live, with the .docx if time allows;<br>• (i) the post-recording pass in the first live week;<br>• (j) writer v5.1 in NP-7 after its own reading | The owner |
| D35 | The delivery date | **27 October 2026, fixed** (the owner, 22 October): WIA uses the tool on production with live calls, as section 5.0 defines; the milestones are planned backward from it | The owner |
| D36 | Budget for M1 to M3 | **Not funded now** (the owner, 23 October). Everything runs on the internal key's USD 5 a week, which resets on 26 October 00:00 UTC (05:30 IST) and next on 2 November. With the free-model shakedown first (N1, USD 0) and one minimal paid run (N2, section 5.0c) the go-live path costs about USD 2.1 in the week of 26 October (N2 about 2, N4's live check about 0.1), at most about USD 3.9 with both contingencies, leaving about USD 1.1 to 2.9 for WIA's first live days; the standing caps are set to the remainder until 2 November | The owner |
| D39 | The paid LLM judge (E.B3, `judge-compare`) on the go-live path | **Dropped** (the owner, 23 October). It caught none of Whitney's 20 October notes and 0 of her 7 recorded failures, so it cannot gate quality. M3 compares writer v4 with v5 by a blind reading by an implementing agent (configurations hidden, order shuffled), recorded as a delegated review (R55); the deterministic checks and Whitney's own ratings in live weeks (E.X9) remain the measures. The paid calibration run on her labelled set moves to N11; the labelled set and the judge code stay | The owner |
| D40 | The size of M3's gate | **The minimal gate** (the owner, 23 October: no budget for the full gate; revision 8.2). No paid run exists only to measure: the gate is the implementing agent's readings of the delivery run itself (N2: the cards, the briefs, knowledge base 9; section 5.0c), with a contingency run only when a reading fails. One sample; no writer v4 baseline regenerated (the recorded v4 briefs of 20 October are the baseline); each part of the new configuration goes live only if it passes, the rest stays at today's. Stability and the comparison with today's configuration are measured by Whitney's live weeks (E.X9); a part she rejects is switched back by a setting at no cost. The full gate (E.X4 as written, about USD 14) is in N11, run only if funded | The owner |
| D41 | Free models on the real data, for the shakedown | **Allowed** (the owner, 23 October, with WIA's permission): the free-model shakedown (N1) runs on a scratch copy of the real working data through free OpenRouter endpoints, which may collect prompts. The routing exception that allows it lives only in the shakedown adapter, applies only to `:free` model ids on a database marked shakedown, and is refused anywhere else by guard tests; S.B1's deny-collection, zero-retention policy stays in force for every paid and production call | The owner |
| D22 | Fund a pack stage now | **Superseded (the owner, 23 October): content packs go live on 27 October with the rest of the system.** Their scope is D43; the brief is the step toward them (R56 as revised) | The owner |
| D23 | The repetition window for a central point | 60 days, or 30 for a fresh angle on the same point; overridable by WIA | Whitney, 13 October ("maybe like a month, two months"); under D12 |
| D28 | Week 2 in prompts | Kept out of prompts and exemplars; Week 1 supplies contrastive pairs | Benchmark integrity |
| D30 | Two Reels when an idea does not support three | **Superseded (the owner, 24 October): every pack has three Reels** (story, stance, b-roll text). The pack writes a missing kind, and writer v5.1 writes all three once its own reading passes (NP-7; D43a, D43j) | The owner; WIA accepted the three-Reel set on 20 October |
| D32 | Angle titles | Plain descriptions of WIA's work ("How we…", "What our…") | Her preferred-angles tab; shown on 20 October without objection |
| D15 | Whitney sees only the end product | Superseded: she reviews live weeks from M5 | Go-live |
| D37 | Acceptance on a held-out Week 5 (E.B13, E.X3, E.X6) | Replaced by live weeks (E.X9); the internal gate keeps a held-out October window. The owner may reopen it | The client reviews real weeks from go-live, which is the stronger test |

Decisions D1 to D21 and O1 to O31 stand as recorded in revision 7.3 (archived, section 15), except where this table changes them. Still relevant: D12 and D21 (the engineer performs internal reviews, recorded as delegated, R55), D13 (one production environment), D14 (the raw export stays with the owner), D18 (now D36), D20 (production is restored from the processed working copy), O1 (cycle time), O2 (approvers, entered at M4), O3 (consent: anonymise by default), O8 (LeadLock as a CTA track: still open; the CTA catalogue governs until WIA answers), O25 (a call that arrives after its window's cycle goes to the next window, M1), O27 (Slack approvals: out for now, the owner, 23 October).

---

## 8. Risks

| # | Risk | Effect | Mitigation | Status |
| --- | --- | --- | --- | --- |
| K60 | **Expectation gap.** WIA saw hand-built packs presented in the app as the system's | The first live output is judged against v2; trust falls if it is weaker or if WIA learns the demo was hand-built | D26 before delivery; the M3 gate before WIA sees system output; R58 | New |
| K61 | **No slack before 27 October.** Every milestone lands on its day | A late step pushes the next one | Section 5.0's day plan, parallel sessions, the cut list and the fallbacks; each day ends with its "done by" checked, and anything missing moves to the cut list that evening | New |
| K62 | **Budget.** D36 not funded: the internal key's USD 5 a week covers the go-live path and WIA's first live days (26 October to 1 November). N2 measured a live week's parts: a cycle about USD 0.80, a brief about USD 0.86, extraction about USD 0.09 for a week of calls | A live week costs about USD 2 to 4; the week's allowance can run out before 2 November, and WIA's refreshes and new briefs then wait | The free-model shakedown finds the system's defects before any paid call (N1); the standing budget refuses before sending and shows why in the app (6.B3); caps set to the remainder; nothing is generated twice (N2's output is the delivery; 7.X1 reuses it); funding D36 at any point lifts it | Open (23 October) |
| K63 | **Railway access.** The CLI was signed out; production unverified since 19 October | M4 cannot start; unknown drift | M4 step 1 inventories before any change | Closed 24 October: signed in, inventoried, N3 done |
| K64 | **Command Center sign-in** honoured `AUTH_DISABLED` | Anyone could act as an approver once the Frontend points at the API | S.C1 | Closed 24 October: `AUTH_DISABLED` removed and refused in production; one shared account until personal ones (X.1), so decisions on it keep the delegated label |
| K65 | **The mock shipped by mistake.** The default build is the mock and many deployments are queued | WIA sees fixture data as the product, or client names in a bundle | 7.F2's build fix; S.B15; approve only the newest deployment | New |
| K66 | **Attested facts** can be wrong | A false claim in copy carries WIA's authority | Recorded with person and date, shown as attested at Gate 2, never invented by the system | New |
| K67 | **Thin evidence for the gate.** Three weeks, three samples, LLM judges that missed WIA's notes | The gate passes something WIA rejects | Her notes as the checks' test cases; the paid judge dropped from the gate (D39), its comparison a blind delegated reading; E.X9 as the real measure; X.2's weekly loop | Carried (K37) |
| K68 | **One copy of the processed data** on the owner's machine | Loss before restore | The fresh dump restored into production (N3); the nightly dump to the bucket with its restore check (6.B6) | Reduced 24 October: production holds the data and a nightly dump; Railway volume backups need a Pro workspace (the owner's to buy), and the bucket has no second copy |
| K69 | **The database clock can step backwards** (found 23 October: the local Docker VM's clock is pulled back about 0.5 s every 30 s; a managed database can also step) | A row written later gets an earlier `now()`: job recovery could send a paid call twice; "latest run", decision history and intake order could be wrong | Repaired (`track/j-flaky`): job recovery opens its window 5 s early (`CLOCK_STEP_SECONDS`); `pipeline_runs` and `decisions` rows are dated no earlier than the latest row; intake lists by window; tests identify rows by content; `test_clock_steps_db.py`. Found by shifting each transaction's `now()` back up to 0.6 s over three full runs | Repaired (23 October) |
| K70 | **Free-model behaviour shapes the core.** A workaround for a free model's quirk changes what paid calls send or how they are judged | Paid runs fail or degrade on a change made for a model that will never run them | Section 5.0c's isolation and triage: free-model needs only in the shakedown adapter; no core change on free-model evidence alone; guard tests; every core fix reproduced without a free model | New (23 October) |
| K71 | **Free endpoints may collect the real data** used in the shakedown | WIA's call content could be retained or used by a free provider | D41 (the owner's permission from WIA, recorded); the exception only on a scratch database marked shakedown; production and paid calls keep S.B1's policy, enforced by guard tests | Accepted by the owner (23 October) |
| K73 | **Packs by 27 October with their scope open.** Go-live includes packs; on 23 October their scope (D43) is undecided and two of the three briefs wait for budget | Packs miss the date, or are built on a brief that is still changing | The brief-done checkpoint fixes the brief's output first; the pack stage reads the hand-off view, which does not change with the contract version; D43 as early as possible; N3 runs alongside NP | Reduced (24 October): the composition decided, and the design planned and probed (the content-packs plan; its risks K75 to K83) |
| K1 | Privacy of model calls | Client confidentiality | Routing enforced on every call (S.B1); run plans | Holds |
| K53 | Reviews made under delegation are not WIA's labels | Calibration on the engineer's taste | R55 labels them; E.X9 brings WIA's own | Reduced by M5 |
| K13 | Long model calls under job timeouts | A long October call or a whole-week strategist call times out | Explicit timeouts per stage; M1's exit runs the longest October call | Checked (23 October, N2): the longest October call extracted in 106 seconds and the whole-week strategist call took 426 seconds, both against 3,600 |
| K74 | **An output cap that binds.** A reasoning model spends part of its output limit thinking; a long structured answer then stops part way (N2: brief 3's claim check, 126 statements, cut off at 16,000 tokens, USD 0.25 for nothing) | Money spent with nothing usable; before the fix the step could not be retried at all | The cap is not a quality setting (a call is billed for what it writes; the cap only sets the budget's reserve), so it is set never to bind: 32,000. A JSON answer cut off part way is retried once with a raised limit, checked by the budget first; a step retry asks again rather than replaying a cut-off answer; the cap is outside a run's frozen contract | Repaired (24 October) |
| K72 | **A lost answer is still paid.** A long call can be cut off on its way back (N2: Sonnet, 341 seconds) | Money spent with nothing written; before N2's fix the budget did not see it | Counted at its worst case since `23701bb`; the step is retried by a person, and research replays its saved answers at no cost | Repaired (23 October) |
| K36 | Intake stalls silently | Live weeks miss calls with nobody noticing | The bulk worker in M4; 6.B4's go-live subset (M1) | Carried |
| K44, K52 | Whitney's review time; review fatigue | Labels and context stop arriving | Her own card format; slates of three to five public cards; the review document; tone requests batched weekly (X.2) | Carried |

Revision 7.3's other risks (K2 to K55, archived section 15.3) stand where not superseded here. The overshoot of a run plan by its last call (20 October) is repaired: a call whose worst case would pass the cap is refused before it is sent (`278acef`), and the standing budgets (6.B3) use the same check.

---

## 9. Definition of done

This phase is done when every line holds on production:

**Intake and evidence.** New Fathom calls arrive within the hour; October's backlog is imported; every included call is dated, classified (an unclear one by an editor in the app), embedded and extracted into verified scenes with the new scene types.

**Cycle and Gate 1.** An approver starts a cycle for a window from the app (and, after M6, it runs on schedule); cards arrive in Whitney's format with the strategy brief, considered ideas and internal insights; she can edit any field, refresh with feedback, add context or an attested fact, and decide; every action writes a decision.

**Brief and Gate 2.** Developing a card starts the brief within the standing budget; the brief meets section 4.3 with no blocking finding; she can edit any field (kept verbatim), refresh with feedback, add context, confirm the CTA and approve; the approved brief is read-only at its URL with Markdown and the review document.

**Quality.** The configuration of record passed M3's gate; section 4.5's bar is met on two consecutive live weeks; no first-touch, insider-term or fidelity correction of a checked kind recurs.

**Packs.** Each approved brief becomes a content pack on production, as the content-packs plan's section 11 defines: 1 email, 1 carousel and 3 Reels, finished and checked, edited in the pack and kept word for word, with the week plan and the week's document.

**Reproducibility.** Every run is pinned and replayable at no cost; no prompt, model or knowledge-base change ships without the gate and a recorded result.

**Operations.** Real sign-in (the owner's auth layer, S.C1); every worker running, the bulk worker included; backups on; standing budgets with refusals shown; failures notify the team; CI green; DEPLOYMENT.md matches what runs; tone requests flow from request to release.

**Not required:** Slack, the client knowledge base, and scheduling or publishing packs into any tool (section 6).

---

## Appendix A. Every item ID and where it went

Status as of 22 October 2026. "Done" means verified on 19 or 20 October against its "done when" (the archived revision 7.3 holds each row's evidence); "M1" to "M6" name the milestone of section 5 that carries the item or its remainder.

| Phase | Done | Where the rest went |
| --- | --- | --- |
| S | S.B2, S.B3, S.B4, S.B5, S.B6, S.B7, S.B9, S.B10, S.B11, S.B12, S.B13, S.X1, S.X2, S.F1, S.F2, S.F3, S.F4; S.B14 closed (not needed) | S.B15 new (built 23 October); S.B8 (the writer step, paid); S.C1 (the owner's, 23 October); S.B1 (M6, the dashboard check) |
| E | E.B3 (the judge), E.B6, E.B7, E.B9, E.B10, E.B11, E.B12, E.B12a, E.B16, E.B17, E.B19, E.B20, E.B21, E.B22, E.B23, E.B24, E.B25 (a to h), E.B26, E.F3, E.X1, E.X2, E.X7; E.B4 superseded | M1: E.B1 (extension). M2: E.B24 (extension), E.B25 (i) (j), E.B27 (packets), E.B28 (go-live subset), E.B29 (change), E.B30, E.B31, E.B32, E.B33, E.B34 (new). M3: E.B27 (runs), E.X4. M5: E.X9 (new), E.F1, E.F2, E.F4. Replaced by E.X9: E.B13, E.X3, E.X6; E.B2's and E.B15's Week 5 remainders close with benchmark v2. M6: E.B5, E.B8, E.B18, E.X8, E.B28 (rest), E.B29 (a), E.B24's model check, the E.B3 and E.X7 extensions. Dropped: E.X5 |
| L | L.B3, L.B4, L.B5, L.B6, L.B7, L.B8, L.B9, L.B10, L.B11, L.F1, L.F2, L.F3, L.X1, L.X2 | M2: L.B12. M4: L.B1, L.B2 (production state by the restore). M6: L.B13 (no build), L.B14 (new), L.B2 (extension) |
| 0 | 0.B3, 0.B4, 0.B5, 0.B6, 0.B8, 0.B9, 0.B11, 0.B12, 0.F1, 0.F3 | M4: 0.B7 |
| 1 | 1.B1, 1.B2, 1.B3, 1.B5, 1.B6, 1.B7, 1.B8, 1.B10, 1.B12, 1.B13, 1.B14, 1.F1 to 1.F5 | M1: 1.F6 (new). M4: 1.B4, 1.B9 (by the restore, D20). M6: 1.F7 (new), 1.B11 (Zoom dates), the 1.B12 and 1.B13 extensions |
| 2 | 2.B1 to 2.B10, 2.B12, 2.F1, 2.F2, 2.F3 | M6: 2.B11 (the Funktastic chain). P3: 2.B13 |
| 3 | 3.B16 (in Phase E); 3.B14 moved to E.B21 | M1: 3.B2/3.B3, 3.B7/3.F2 (go-live subsets). M2: 3.B5 (extension); 3.B10's piece-level part via E.B25 (i) (its base import exists). M6: 3.B1, 3.B4, 3.B5 (rest), 3.B6 (rest; E.B6's cutoff is built), 3.B8, 3.B9, 3.B11, 3.B12, 3.B13, 3.B17, 3.F1, 3.F3 to 3.F9. P3: 3.B15 |
| 4 | 4.B3 (E.B11), 4.B6 (E.B15), 4.B9, 4.B12; 4.F5 moved to L.F2 and L.F3 | M1: 4.B1. M6: 4.B2, 4.B4, 4.B5, 4.B7, 4.B8, 4.B10, 4.B11, 4.B13, 4.B15, 4.F1 to 4.F4, 4.F6. P3: 4.B14, 4.B16 |
| 5 | 5.B1, 5.B3, 5.B4 | M1: 5.B6, 5.B7, 5.F1, 5.F2, 5.F4, 5.F5 (go-live subsets), 5.B14 (new). M5: 5.B2. M6: 5.B5, 5.B8, 5.B9, 5.B10, 5.B11, 5.B12 (partly done), 5.F3, 5.F6, 5.F7. Packs: 5.B13 replaced by Phase NP's items (NP.B1 to NP.B15, NP.F1 to NP.F4, NP.X0 to NP.X5; the content-packs plan, revision 8.7) |
| 6 | 6.F1 superseded; 6.B14 moved to L.B8 | M1: 6.B3 and 6.B4 (go-live subsets), 6.B18 (new). M4: 6.B1, 6.B5, 6.B6 (go-live subset), 6.C3. M6: the rest of 6.B, 6.C, 6.F and 6.X. P3: 6.B10, 6.B11 |
| 7 | 7.B3 | M1: 7.F2 (the build fix). M4: 7.B1, 7.B2, 7.B5, 7.B6, 7.F2, 7.X1. M5: 7.X2. M6: 7.F1. M0: 7.B4 (ask Jainil) |

**Built on 23 October (revision 8.1, section 5.0a).** S.B15; E.B1 (extension); E.B3 (labelled set); E.B24 (extension); E.B25 (i) (j); E.B27 (packets for Weeks 1 and 2); E.B28 (go-live subset); E.B29 (change); E.B30 to E.B34; L.B11 (profile from settings); L.B12; L.B14; 0.B6 (budget renewal); 1.F6; 1.F7; 3.B2/3.B3, 3.B5 (extension), 3.B7/3.F2, 4.B1, 5.B6, 5.B7, 5.F1, 5.F2, 5.F4, 5.F5 (go-live subsets); 5.B14 (Markdown); 6.B3 (go-live subset); 6.B18 (run; embedding pending); 7.F2 (the build fix). Their paid remainders are section 5.0a's next steps. **Run on 23 October (revision 8.3):** N1 and N2. S.B8 is done; 6.B18 is embedded; E.B31 has the delivery window; E.B30, E.B32 and E.B33 passed the minimal gate and are in production settings; E.B25's version 9 is active; M1's exit is met. **Done on 24 October (revision 8.5):** N2's briefs 2 and 3, the second blind reading, the hand-off views and the brief-done checkpoint; E.B1's retry extended to a cut-off JSON answer; the output cap 32,000.

**Revision 8.4 (the owner, 23 October).**
- **Packs:** the pack stage (5.B13) is on the go-live path as Phase NP, with scope D43.
- **Slack:** 3.B12, 5.B8 and 6.B2 (O27) are out for now.
- **After go-live:**
  - the short list: 6.B4, 6.B6, 5.B14's .docx, the E.B24 warnings and 3.B11 (N6, N7);
  - optional: the rest of M6 (N8, N10, N11);
  - not planned: N9's re-plumbing.

**New in revision 8.** S.B15 (green baseline), E.B34 (WIA's corrections as rules and checks), E.X9 (WIA reviews live weeks), L.B14 (repeat corrections become rules), 1.F6 (resolve a waiting call in the app), 1.F7 (upload a transcript), 5.B14 (the week's review document), 6.B18 (the October calls). Owner and WIA actions: X.1 (M0, the questions for WIA and Jainil), X.2 (M5, tone change requests). Their rows are in section 5.

---

## Appendix B. Rulings in force

R1 to R55 stand as registered in the archived revision 7.3 (its Appendix E and section 4.2), with these the most used in this phase: R31 (packs, calendar and the third gate outside scope; superseded for packs by the owner on 23 October: packs go live on 27 October, scope D43, and the calendar and a third gate only if D43 includes them), R40 (WIA is the subject), R41 (the knowledge base as the trusted prefix), R42 (the lean card with a separate ledger), R43 (one weekly strategist call, no numeric cap), R44 (models and prompts change only on a recorded result), R45 (dispositions), R46 (the CTA confirmed by a person), R48 (client material only under `research/` and `backend/knowledge_base/`), R50 (WIA reviewers are Command Center `team` users on the approver list), R51 and R52 (context grows only from WIA's work; the export was a one-time seed), R53 (formats are data), R54 (rigour beside the copy, never inside it), R55 (delegated reviews are not WIA's labels).

New in revision 8:

| # | Ruling |
| --- | --- |
| R56 | (Revised by the owner, 23 October; revision 8.7.) The brief carries the copy of every asset. From revision 8.7 its unedited copy is a draft that the pack finishes, while every line a person wrote is final. It is the step before the pack stage, which goes live on 27 October (D43). The pack stage reads the brief's hand-off view (version 2 from NP.B1), never the contract-specific document, and acts only on a brief it can consume (`can_consume`). After Gate 2, copy is edited by hand and kept verbatim. In the pack (24 October): a finishing step after Gate 2 may edit only lines no person wrote, inside the pack's fidelity loop, and every line a person wrote at Gate 2 or in the pack is kept word for word (the content-packs plan, section 5) |
| R57 | A fact an approver states at a gate is evidence: recorded in the ledger as `attested` with the person and date, allowed in copy, shown as attested. A paraphrase of a client's words is never presented as a verbatim quote |
| R58 | Output is labelled by its maker. A hand-built reference is never presented, in the app, a document or a call, as system output |
| R59 | First-touch text (subjects, previews, covers, on-screen hooks, the first b-roll screen, carousel slide 1) is specific, carries its promise, uses no insider term and keeps who did what; specificity outranks sibling distinctness (section 4.3) |
| R60 | A rule WIA has given is checked, not only loaded: every format or voice rule with a test case from WIA's own text becomes a check (E.B24, E.B34); a correction given twice becomes a rule candidate (L.B14) |

---

## Appendix C. Configuration for go-live

| What | Value of record | Where |
| --- | --- | --- |
| Editorial configuration | The one N2's minimal gate passed (D40, 23 October): scene profile `2026-10-23.scenes.v3` on `openai/gpt-6-luna` (output cap 32,000); strategist `2026-10-23.wia-strategist.v7` on `openai/gpt-6.1-sol`; `card-verification.v4` on `anthropic/claude-sonnet-5.5`; contract `brief_document_v4` with writer `v5.1` on Sol (26 October, NP.B10: v5 writing all three Reels; v5 is the switch-back); the pack check `pack-check.v3`, the post-recording pass `pack-caption.v1` and the permission re-finish `pack-refinish.v1` (NP-7); brief review on Sonnet 5.5; `models.completion_tokens` 32,000 (16,000 until 24 October; K74). A part WIA rejects goes back by its key: strategist v6, contract v3 with writer v4 | `backend/deploy/production-settings.json`, applied with `storage_cli settings apply` (the code defaults are the old configuration) |
| Knowledge base | Version 9, `wia-kb-2026-10-22.c-a1a75795`, **active** on the working copy since N2's reading (recorded as its benchmark), and the committed default; version 8 (`wia-kb-2026-10-20.c-6bf62f94`) is archived and is the switch-back. Production receives it with N3's dump | `backend/knowledge_base/manifest.json`; `kb-publish`, `kb-approve` |
| Frontend build | `VITE_ATELIER_MODE=backend` | M1 (7.F2) |
| Frontend variables | `ATELIER_BACKEND_ORIGIN`, `ATELIER_API_SECRET`, `COMMAND_CENTER_AUTH_ORIGIN`, `COMMAND_CENTER_PUBLIC_ORIGIN` | Railway, never git |
| Intake | `ATELIER_FATHOM_API_KEY` (not `FATHOM_API_KEY`), `ATELIER_INTAKE_ADMINS` | Railway |
| Paid stages | `ATELIER_ALLOW_GENERATION`, `_ENCODING`, `_REFINEMENT`, `_BRIEF_GENERATION` and `_PACK_GENERATION` on in production, `_BRIEF_WEB` off; standing budgets (6.B3) instead of a run-plan variable per run. Production's caps for a week of use (26 October, N5): cycle 1.20, briefs 4.00, refreshes 1.50, embedding 0.10, extraction 0.40, context mining 0.10, packs 6.00: USD 13.30 a week, under the internal key's USD 15. After the first live week packs go back to 3.50 and the rest are set from the measured spend (DEPLOYMENT.md, "Caps for a week of use"). The working copy's caps stay closed; it is no longer the live system | Railway; the database |
| Command Center | No `AUTH_DISABLED`, no `VITE_AUTH_DISABLED`; `SESSION_SECRET`; `AUTH_EMAIL=ai@weddingindustryads.com` with `AUTH_PASSWORD_HASH` (24 October); personal accounts as `USER_n_*` later | Railway (`WIA-Command-Center`); S.C1 |

Every other variable and setting: `DEPLOYMENT.md` and revision 7.3's Appendix D.

---

## Appendix D. Revision history and logs

| Revision | Date | Basis | Main change |
| --- | --- | --- | --- |
| 1 to 7.3 | 10 to 21 October 2026 | See the archived revision 7.3, Appendix F | From the first plan to the combined quality track |
| **8.1** | **23 October 2026** | `main` at `51db019` | The build of 22 and 23 October recorded: section 5.0a (what was built, the decisions taken, the next step), the status table, Appendix A; S.C1 the owner's; D38 opened; X.1 extended |
| 8.13 | 25 October 2026 | `main` at `bc38a32` (PRs #28 to #31) | Phases N6, N10, N7 and N11 done at the owner's instruction (unattended from the evening): failure alerts, the automatic restore check, the autonomy pass and the hourly upkeep, Home's summary, the Sunday schedule from 1 November, strategist v9 after the benchmark, last week regenerated on production with three drills, production on the Client key. Start here, `research/n6-n11-2026-10/` |
| 8.12 | 25 October 2026 | `main` at `cb3ecc9` (PR #26) | Phase N8 done, unattended at the owner's instruction: identities, internal meetings as team practice, account memory, founder notes, the Zoom dates, the Funktastic chain; strategist v8, scene profile v4 and writer v5.2 in the configuration of record; eight defects fixed from the shakedown, the proofs and production (the last, the pack identity check, in the records PR). Start here, the status table, 5.0a, 5.0b, M6 |
| 8.11 | 26 October 2026 | `main` at `6a89b75` and PR #24 | Phase N5's system side and NP-7 done, unattended at the owner's instruction: NP.B14, NP.B15, `pack-check.v3` with NP.X5's labelled cases, NP.B10 (writer v5.1), NP.B12's .docx; E.X9's brief ratings at Gate 2; 7.X2's `week-measures`; the tone loop (X.2, NP.X4) end to end; the caps for a week of use; the "Impromptu Zoom Meeting" documents; the week's cycle on production. Three defects fixed from the shakedown and the paid proof. Start here, the status table, 5.0a, 5.0b, M5, Appendix C |
| 8.10 | 24 October 2026 | `main` at `e33526a` and this branch | Phase N4 done, unattended at the owner's instruction. The October backlog imported by hand; 7.X1's live check end to end on production through its API and workers; 6.C3 (Command Center PR #4); the pack screens checked on the local copy (no password on production). Three defects fixed with tests. The owner's direction of 25 October: the Fathom collector deferred to N7, which moves last; the Loom dropped. Start here, the status table, where to resume, 5.0a (N4, the next-step table), 5.0b (N4, N7, the order), M4 steps 8 and 9, Appendix D; DEPLOYMENT.md's manual import |
| 8.9 | 24 October 2026 | `main` at `c381095` | Phase NP done, unattended at the owner's request. NP-1 to NP-5 merged in PR #17; PR #18 restores two contract docstrings so saved pack answers replay, and pins the wire schemas. NP-6 on production: migration 009, the settings and the packs budget, N2's three briefs through Gate 2 under delegation, their packs replayed at USD 0 with brief 3 finished again live under v2, and the team's delegated review. The paid proof's readings (16 of 16 pairs preferred blind; the stop rule's v2 profiles). Direction unchanged; Start here, the status table, the next-step table, the Phase NP row, D43 (g), Appendix D |
| 8.8 | 24 October 2026 | `main` at `bf80ed0` | The owner's direction: N8 is core (identities, internal-call evidence, account memory, founder notes, Zoom dates); every WIA-side decision taken under the delegation (D24, D25, D26, D27, D29, D33, D38 to 7.2; 7.1 holds none); client permission is a before-publishing note, never a gate, and all three N2 briefs go through Gate 2 (the content-packs plan 1.1); phases in priority order with dependencies, never days. The phase table, the order, M6, section 7, X.1 |
| 8.7 | 24 October 2026 | `main` at `3848f03` | Content packs planned: the content-packs plan (Phase NP's detail: the requirements from both calls and WIA's ChatGPT workflow, the code survey, the design, NP-0 to NP-7 with items and exits, the verification, the schedule, D43b to D43j, K75 to K83), after the owner set the composition (1 email, 1 carousel, 3 Reels) and put packs before N4; a planning probe on N2's three briefs (USD 3.82, `research/packs-2026-10/`); an independent adversarial review of the draft (6 blocking, 22 important, 15 minor findings), applied before commit; the 20 October transcript saved; D43 decided by the owner (D43a, then D43b to D43j as recommended), moved to section 7.2. Direction, Start here, the plan table, 5.0a, 5.0b, 6, 7 (D43, D30), K73, the definition of done, Appendix A, R56 |
| 8.6 | 24 October 2026 | `main` after `f58c6c4` | Phase N3 done on Railway (the inventory, the nightly dump in place of Pro-only volume backups, the rehearsal, the restore, the artifacts, every service, the configuration) and S.C1 built at the owner's request (one sign-in and one sign-out for Command Center and the Atelier, live on production); the Frontend in backend mode (7.F2). Start here, the status table, the phase table, M4's steps, S.C1, K63, K64, K68 and Appendix C updated |
| 8.5 | 24 October 2026 | `main` after `2034a5a` | N2 completed: briefs 2 and 3 on the owner's new internal key (USD 1.7155 of a USD 2.25 ceiling), their readings, a second blind reading (all three writer v5 briefs above all three writer v4 briefs), the hand-off views; the brief-done checkpoint holds. Three defects fixed (a cut-off JSON answer retried; a cut-off answer never replayed and the output cap outside the frozen contract; the private-speaker check's first-word match). The output cap 32,000 (K74). D42 updated. Start here rewritten for the pack and production steps |
| 8.4 | 23 October 2026 | `main` after `fdbed3c` | The owner's direction: go-live on 27 October includes content packs. Packs come into scope, with the brief as the step toward them: the brief-done checkpoint, Phase NP, D43 for the pack scope (not defined here), D22 superseded, R31 and R56 revised, section 6 and the definition of done. Slack is out (N7 becomes "Scheduling"; 3.B12, 5.B8, 6.B2, O27). M6 is cut to a short list (N6, N7) with the rest optional (N8, N10, N11) or not planned (N9). K73. Phase names are kept; NP was added |
| 8.3 | 23 October 2026 | `main` after N1 (`05c5e25`) and N2's fixes (`32d65d3`) | Phases N1 and N2 recorded (section 5.0a, "N1 and N2"): the shakedown ledger, N2's readings and the configuration of record; S.B8, 6.B18 and M1's exit done; E.B30, E.B31 (window), E.B32, E.B33 and knowledge base 9 in force; D42 opened; K13 checked; K72 |
| 8.2 | 23 October 2026 | `main` after `c62c487` | The verification strategy for paid runs (section 5.0c): the free-model shakedown first (N1, isolated from the core), then one minimal paid run that is also the delivery (N2, about USD 2); the agent's readings as the gate (D39, D40); D41 (free models on the real data, the owner's permission); K70, K71; phases renumbered N1 to P11 |
| 8 | 22 October 2026 | `main` at `130e09b` | The final audit after WIA's review of 20 October: every Done item re-checked in code and tests; the path from a call to a brief traced; the reproducibility of every pack set established (none was system output); the client's notes mapped to rules and checks; scope fixed at the brief, which carries every asset's copy; the remaining work as milestones M0 to M6 with exits; rulings R56 to R60; D35 decided by the owner (delivery fixed on 27 October, with the schedule in section 5.0), D36 opened, D37 taken (the owner may reopen it), and D15, D22, D23, D28, D30, D32 settled; eight new items. Revision 7.3 archived verbatim |

**Implementation log.** Each implementation run adds a row: date; items; commits or pull request; Done or Partly done with the remainder; evidence for each "done when"; next recommended. Rows before 22 October are in revision 7.3, Appendix G.

| Date | Items | Commits | Done or partly done | Evidence | Next recommended |
| --- | --- | --- | --- | --- | --- |
| 25 October 2026 (N8) | Phase N8: 1.B12 (extension), 1.B13 (extension), 3.B17, L.B13, 1.B11, 2.B11, unattended | PR #26: `ff29b40` to `d2c655a` (with `e7a2390` from a subagent), merged at `cb3ecc9` | Done: 1.B12 and 1.B13 extensions, L.B13, 1.B11. Partly done: 3.B17 (the Week 2 venue's "what we built" waits on a record of the build in the corpus), 2.B11 (one golden scene never extracted; archive-wide paraphrase search). Fixed: eight defects (the record; the pack identity check in the records PR). USD 4.27 on the Client key (copy D's proofs), 0 for copy C's shakedown, USD 0.71 on the internal key for production's extraction and embedding; no Railway billing change; hosted CI refused by GitHub billing, every job run locally | `research/n8-2026-10/README.md`; full backend suite 1,948 passed on PR #26 (one order-sensitive test passes alone), and the records PR's run; frontend 412 unit and 77 server tests, build; both images | N6, then N10; N7 last; X.1 when the owner sets the passwords |
| 26 October 2026 (N5, NP-7) | N5's system side (E.X9's brief ratings, X.2's tone loop, 7.X2's `week-measures`, the caps, the "Impromptu" documents, production current) and NP-7 (NP.B14, NP.B15, NP.B10, NP.X4, NP.X5, NP.B12's .docx, `pack-check.v3`), unattended; X.1 left to the owner (passwords) | PR #24: `521367e` to `7ad3242` (with `e8efa9c`, `82114ce`, `d596cf2`, `4b9b392` from two subagent branches) | Done: every NP-7 item, live with the configuration of record; E.X9, X.2 and 7.X2's system side. Fixed: a recorded take kept as a check source (`737e060`), a cut list line removed (`7ed2376`), research grading the items a grading answer missed (`246667f`). USD 2.20 on the Client key (proofs on copy B), 0.39 on the internal key (the cycle), 0 for the copy A shakedown; no Railway billing change | `research/n5-2026-10/README.md`; offline suite 1,298 passed; the pack, brief and new database suites; CI on PR #24; frontend 408 unit and 77 server tests | N8; X.1 when the owner sets the passwords |
| 24 October 2026 (N4) | Phase N4: 6.B18 (the October backlog), 7.X1, 6.C3; the pack screens' check; 6.B1 moved to N7 and the Loom dropped (the owner) | `731dedc`, `18745b3`, `d9adebb` and this record (this branch); Command Center PR #4 | Done: 6.B18's backlog, 7.X1, the screens' check (on the local copy). 6.C3 live on production (Command Center PR #4, `be38d25`). PR #20 merged (`77235ee`) and deployed to all seven services. Moved: 6.B1 and 7.B6's connector step to N7. USD 2.7918 on the internal key; USD 0 on the Client key; no Railway billing change | `research/golive-2026-10/README.md` and its `x1-*.json` files; the offline suite (1,262 passed); CI on this branch; Command Center 805 tests, type check, lint and build | N5 with NP-7's first-week items; the 11 "Impromptu Zoom Meeting" documents for a person |
| 24 October 2026 (NP) | Phase NP: NP.B1 to NP.B9, NP.B11 to NP.B13, NP.F1 to NP.F4, NP.X1, NP.X2, NP.X2a, NP.X3, NP-6 (the content-packs plan); NP.B10 is NP-7's | PR #17 (`5349c23` to `3f60001`, merged `f1576d0`), PR #18 (`4e1396e`, merged `c381095`) | Done: NP-1 to NP-6 and section 11, except the screens' visual check on production, which needs a WIA sign-in. USD 4.83 of the owner's USD 6 on the internal key (the capped call 0.03, the held-out brief 1.30, five proof pack runs 2.90, production 0.60); USD 0 on the Client key; no Railway billing change | `research/packs-2026-10/np5/shakedown-ledger.md`, `np5-proof.md`, `production.md`; the offline suite (1,260 passed) and CI on PRs #17 and #18 (both database suites, frontend, Docker images) | N4's rest: the October backlog, the Fathom collector and 7.X1, then the Loom; NP-7 in the first live weeks |
| 24 October 2026 (NP plan) | Phase NP planned (the content-packs plan); D43a recorded (the owner); a planning probe of the finisher, the fidelity check and the repair on N2's three briefs | This revision | Planned; no code changed. USD 3.82 on the internal key (the owner's ceiling USD 5) | `research/packs-2026-10/README.md` and `probe/` | NP-1 to NP-6 before N4 (NP-0 done: D43 decided on 24 October) |
| 22 and 23 October 2026 | M1 and M2 (code), L.B14, 1.F7, the M1 exit test (offline), 7.B5's local rehearsal | `4188368`, `4948b34`, `77a4d78`, `62d4b6e`, `aed2988`, `47d624c`, `ba2ef57`, `8687a0e`, `51db019` (tracks A, H, B, D, E, C, F, G and the integration), then the K69 repair | Done in code: every item of section 5.0a. Partly done: 6.B18 (embedding), E.B31 (re-extraction), E.B27 (October packet), E.B30 (the Week 1 run), E.B25 (activation after M3), M1's exit (the paid run in the image), all for want of budget (USD 0 until 26 October) | Section 5.0a; `test_m1_exit_db.py`; `research/restore-checks-2026-10-23/` | Section 5.0a's next steps, then M3 |
| 23 October 2026 (N1) | Phase N1: the free-model shakedown; every M1-exit step and failure case through the app in the production images; the desktop visual check | `58de109` to `05c5e25` | Done: N1's exit. 29 pipeline defects fixed with tests (screens, gates, budgets, extraction, the strategist packet, wording of failures), 5 free-model artefacts absorbed in the free branch only | `research/shakedown-2026-10/ledger.md`; offline 1,191 passed; both database suites passed; frontend type check, lint, unit 370, server 61 and build; both images built | N2 |
| 24 October 2026 (N3, S.C1) | Phase N3 (M4 steps 1 to 5: 0.B7, 6.B5, 6.B6, 7.B1, 7.B2, 7.B5), S.C1 and 7.F2 (M4 steps 6 and 7), at the owner's request, unattended | `1e8a065`, `9251768` (merged `f58c6c4`); Command Center `93be42a`, `33eab69` (merged `d5b82b5`); then this record with the snapshot fix | Done: N3's exit; S.C1; 7.F2 on production. Open: personal accounts (X.1), N4's backlog, collector and 7.X1. Spend USD 0.000094 on the internal key; no Railway billing change | `research/production-2026-10/README.md`; production checks by curl; offline and database tests; CI on PR #13; Command Center 805 tests, type check, lint and build | D43 and NP on production; N4's rest |
| 24 October 2026 (N2, briefs 2 and 3) | N2's briefs 2 and 3 on the owner's new internal key (ceiling USD 1.50, then 2.25); E.B1 (extension: a cut-off JSON answer), the output cap, 5.F1's step retry, the private-speaker check (E.B24); the brief-done checkpoint | This record and its fixes | Done: N2's exit and the brief-done checkpoint. USD 1.7155 on the internal key (brief 2's validation 0.4108, brief 3 1.3049 with a cut-off call of 0.2459) | `research/n2-delivery-2026-10/readings.md`, `blind-reading-2/`; the three hand-off views; offline and database tests of the fixes | D43 and Phase NP; Phase N3 alongside; at the 26 October renewal, the standing caps |
| 23 October 2026 (N2, brief 2) | N2's brief 2 on the Client key's remainder, as the owner asked; plan and prompts revision 8.4 (the owner's direction: packs at go-live, Slack out, a short after-go-live list) | `bdad149`, then this record | Partly done: brief 2's research and writing (USD 0.4630); its validation waits on the budget (Client key USD 0.14 left); brief 3 not started | `research/n2-delivery-2026-10/readings.md`; the briefs plan records USD 1.4650, equal to briefs 1 and 2 | After 26 October 00:00 UTC: brief 2's validation and brief 3, the brief-done checkpoint, then NP (D43) and N3 |
| 23 October 2026 (N2) | Phase N2: 6.B18 (embedding), E.B31 (window), the October cycle (E.B30, E.B32), one brief (E.B33), S.B8, the minimal gate (E.X4, D40), knowledge base 9, the configuration of record | `23701bb`, `ed4062c`, `32d65d3`, then the configuration and records | Done: every step and reading for one brief; S.B8; M1's exit. Partly done: N2's exit (briefs 2 and 3 wait for the key's reset; D42). USD 1.8936 on the Client key; internal key USD 0 | `research/n2-delivery-2026-10/readings.md` and its files; `backend/deploy/production-settings.json` | Briefs 2 and 3 after 26 October 00:00 UTC, then N3 |

**Verification log.** Each verification run adds a row: date; range; items verified; issues; repairs; open after; next run starts from. Rows before 22 October are in revision 7.3, Appendix H.

| Date | Range | Items verified | Issues found | Repairs | Open after | Next run starts from |
| --- | --- | --- | --- | --- | --- | --- |
| 22 October 2026 | `d2aeeff..130e09b`, and every item marked Done on 19 and 20 October | The backend items against code, defaults and tests; the path from a call to a brief; the frontend (mock and real); CI; Command Center's sign-in; intake; both research folders; the 20 October review | CI red (two tests from `5588578`); the production build is the mock; 4.B1, Gate 1 refresh and Gate 2 refresh for v3 absent; Fathom key name mismatch; the October backlog unreachable by the collector; S.C1 not implemented; sixteen statements of revision 7.3 wrong (section 2.6) | None (plan only) | Section 5 | `130e09b` |
| 22 October 2026 (second pass) | Revision 8's draft | An independent adversarial review of the plan against the code, DEPLOYMENT.md and both research folders; every item ID of revision 7.3 accounted for | 3 blocking (M4 had no bulk worker, so new calls would never be normalised; M3 needed the October calls that only M1 brought in; knowledge base 9's benchmark sat in M3 while M3 waited for M2), 9 important (the scope argument rested on contract v4; M1 and M2 share files; the lock test could pass vacuously; two steps still needed the command line; the budget was low; Week 2 was not independent of the checks; the calendar did not add up; reliability items were deferred; checks from revision 7.3 were dropped), and minor errors | Applied to revision 8 before it was committed | Section 5 | `130e09b` |

---

## Appendix E. Standards the code cites, kept verbatim

The rubric (2.3a), the conditions for a successful brief (2.4) and the brief standard (2.4a) are cited by number in the code (`gates/rubric.py`, `briefs/validation_v2.py`, `briefs/ledger_v3.py`, `briefs/workflow.py`) and pinned by `test_rubric.py`, so they are kept here word for word under their revision 7.3 numbers. They remain in force beside section 4.3, which adds the asset standard. References inside them (sections 4.3 and 4.5, Phases 4 and E, E.X3, E.X6) are to the archived revision 7.3; E.X9 now carries the reviews they name.

### 2.3a Review rubric v1

Used by Whitney in E.X3 and, as a smoke test only, by E.B3's judge. It replaces the team-written form, whose five criteria (audience relevance, complexity, angle fit to the brand, voice and tone, distinctiveness) do not measure either of Whitney's two complaints. Each card is rated 1 to 5, using anchors stated on the E.X7 form (1 = would not publish; 3 = publishable after a light reframe; 5 = publish as is):

1. **WIA is the subject.** The card shows what WIA knows, how it thinks or works with clients, or why its approach matters (R40; steps 4 and 6 of Whitney's seven-step framework in the review document). An education or opinion card passes when the view is WIA's own.
2. **Strategic purpose.** The pillar, content type and offer connection fit Savannah's strategy and the current content plan (framework step 2).
3. **Audience.** It speaks to WIA's market: established, growth-minded wedding businesses. It does not speak to the person on the call, or to an owner in a place of desperation (framework step 3).
4. **Worth attention.** It carries a real tension, and it is distinct from the week's other cards and from recent content (framework step 5; "distinctiveness" is her ranking criterion).
5. **Sounds like Whitney.** Plain, confident and specific to weddings; none of her rejected constructions.

Rules for the rubric:

- The text is frozen before any prompt change and is never copied from a candidate prompt.
- Whitney confirms it (E.X7; confirmed under D12 as `rubric-2.3a.v1`, overridable by WIA).
- A version change is recorded like a knowledge-base change.

### 2.4 What counts as a successfully generated brief

A brief is successful when all of the following hold. Conditions 1 to 10 are checked by code (Phase 4); condition 11 is WIA's judgement (Phase E).

1. It exists as a `content_briefs` row whose `angle_hash` equals the approved card's hash.
2. Every section of the contract of record is present (v2, section 4.5; v1 rows remain readable).
3. Every claim in the ledger cites at least one evidence ID in the linked dossier.
4. Every quoted passage is an exact substring of its preserved source passage.
5. Every number stated as fact appears in a source-bound claim. Claim labels such as `[C3]` and format numbering are not numbers.
6. No external research item is cited as proof of a WIA or client result.
7. No client is named and no quote is public unless that client's consent level or a recorded clearance allows it.
8. The CTA is the one a person confirmed at Gate 1 or Gate 2, or "no explicit ask" chosen by a person (R46).
9. Prior coverage lists the overlapping published or prior pieces, or says none were found and how complete the comparison set was.
10. The knowledge-base version and its hashes are pinned on the brief, and every banned-construction finding in the body is shown to the reviewer (as a warning until WIA rules on the conflicting guidance, V23).
11. **An approver at WIA has read it and approved it without rewriting its central point.**

### 2.4a Brief standard v1 (what makes a WIA brief excellent)

Conditions 1 to 11 check integrity and approval. This standard checks quality. Items (a), (d), (e), (g) and (h) are deterministic checks (4.B8; E.B15 for those that exist in week 4). Items (b), (c) and (f) are findings from a reviewer of a different model family.

- **(a) Refine, don't replace.** The approved title and core perspective appear unchanged in the header, including a Gate 1 reframe. Any sharpening is a separate `sharpened_point` with a reason, shown as a diff.
- **(b) WIA perspective first.** It is written as "we". "I" is used only for Whitney's own verified experience.
- **(c) One complete argument** in Savannah's framework: hook, problem, desire or symptom, main point, transformation, CTA. The transformation covers changed thinking, not only changed numbers.
- **(d) Every format in the confirmed channel set** follows its `format_guide` structure (section 4.3), including the caption and the Reel cover text.
- **(e) Distinct openings and CTAs.** Openings are distinct across assets, and the caption hook differs from the Reel hook. CTAs come from the CTA catalogue and vary across assets unless a person chose one.
- **(f) Credit and grounding.** The supporting example credits who did what. Belief claims cite a knowledge-base document.
- **(g) Clean public copy.** Public copy has no banned construction and no hedge (as warnings until E.X2 rules), and there are at most five before-publishing items.
- **(h) No one named who shouldn't be.** No former staff member and no uncleared client is named in public copy.

**2.4a rating.** At E.X6 and later Gate 2 reviews, the approver marks each of (a) to (h) met or not met and gives one overall score from 1 to 5, stored on the decision's calibration label.
