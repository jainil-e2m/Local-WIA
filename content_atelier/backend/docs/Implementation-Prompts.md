# Content Atelier: implementation prompts

Three prompts for implementing `backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md` (the plan), plus a filled example for the next step. Paste each into a new chat, opened in the folder that contains `WIA-Content-Atelier` (and `WIA-Command-Center`, if present).

| Prompt | When to use it |
| --- | --- |
| 1. Grounding | Once, before implementation starts, or when you continue on a different machine |
| 2. Implementation | For each milestone or set of items you want built. Replace `{{ITEMS}}` with milestones or item IDs (for example "M3" or "6.B4, 5.B14's .docx") |
| 3. Verification and repair | After one or more implementation runs, to check and fix what was built since the last verification |
| 4. The next step, filled in | Phase N5 with NP-7 as prompt 2: the system made ready for the WIA team to use, with the content-packs plan's first-live-week items. Phase NP's filled prompt (NP-1 to NP-6, done 24 October) is in this file's git history |

The plan is the single source of truth. Every run records its outcome in the plan: the item rows (or section 5.0a for the 23 October build), the "Implementation status" table, and Appendix D (the implementation and verification logs).

**The phases, in the order to implement them** (defined in the plan's section 5.0b; paste one or more names into `{{ITEMS}}`). Phases are N-numbered so they are never confused with the priorities P0 to P3 in the plan's item tables. The names stay as they are; revision 8.4 added NP and took Slack out of N7, and revision 8.10 put the Fathom collector into N7 and moved N7 last.

**The go-live path** (27 October, content packs included):

1. Phase N1. Free-model shakedown (done 23 October)
2. Phase N2. Minimal paid delivery run (done 24 October; the brief-done checkpoint holds)
3. Phase N3. M4 production foundation (done 24 October, with S.C1 and the Frontend in backend mode)
4. Phase NP. Content packs (NP-0 to NP-6 done 24 October; NP-7 runs with N5)
5. Phase N4. M4 production go-live (done 24 October: the October backlog, 7.X1, 6.C3; the collector moved to N7, the Loom dropped)
6. **Phase N5. M5 delivery and first live weeks, with NP-7 (next; section 4 below)**

**After go-live, in priority order** (revision 8.8: N8 is core; revision 8.10: N7 last):

7. Phase N8. Evidence and account memory
8. Phase N6. Reliability and the review document
9. Phase N10. Hardening and operations
10. Phase N7. Scheduling and automatic collection (the Fathom collector, 6.B1, and the cycle on a schedule; last, so weekly automatic collection starts as late as possible, the owner, 25 October)
11. Phase N11. Diagnostics, the full gate and later (when funded)

**Not planned:** Phase N9. Cycle, research and brief re-plumbing (carry-over from the original design).

**Where things are in the plan (revision 8.10, 24 October 2026).** "Direction", "Start here" and "Read this first" (scope, state, the plan in one table, the implementation status, "Where to resume"); section 0 (conventions, including "Working an item (developer conventions)"); section 2 (the verified state); section 3 (WIA's review of 20 October); section 4 (the target: the card standard 4.2, the brief and asset standard and first-touch rules 4.3, reproducibility 4.4, success measures 4.5); section 5 (the remaining work: 5.0 the schedule to 27 October, **5.0a what was built on 23 October, N1 and N2's record, the next step and the brief-done checkpoint, 5.0b the phases (N1 to N11 and NP), 5.0c the verification strategy for paid runs (the free-model shakedown first, then one minimal paid run)**, then milestones M0 to M6, each item with its "done when" and each milestone with its exit); section 6 (out of scope); section 7 (decisions); section 8 (risks); section 9 (definition of done); Appendix A (where every item ID went); Appendix B (rulings in force); Appendix C (configuration for go-live); Appendix D (revision history and the logs); Appendix E (the standards the code cites, read by `test_rubric.py`). Item histories, the architecture and rulings R1 to R55 are in the archived revision 7.3, `backend/docs/archive/Content-Atelier-Implementation-Plan-Brief-Generation-r7.3.md`.

**Standing owner rules for every run.**
- **The date.** Delivery to WIA is fixed on 27 October 2026 (D35). Plan backward from it and never propose another date.
- **Packs.** Content packs are live on production since 24 October. The content-packs plan, `backend/docs/Content-Atelier-Implementation-Plan-Content-Packs.md`, sets what a pack is and how it is built. Every pack is 1 email, 1 carousel and 3 Reels (the owner's decision, D43a), and the owner confirmed the rest (D43b to D43j) as recommended there on 24 October. Build nothing it does not set.
- **Weekly automatic collection waits for N7, which runs last** (the owner, 25 October). Never activate the Fathom collector (6.B1) or put the cycle on a schedule before N7. The week's calls come in by hand (DEPLOYMENT.md, "The week's calls by hand, while the collector is off").
- **No extra scope.** Build only what an item's "done when" needs; no buttons or screens that later work replaces.
- **Slack is out for now.**
- **Phase names stay as they are.** Do not rename them.
- **Models.** Free models first, then one minimal paid run. No paid judge (D39): the implementing agent reads the output itself, and a blind comparison uses a subagent of its own session.
- **Spend.** Stay inside the ceiling the owner gives for the run; set the app's standing caps so the app itself stops there.
- **Subagents.** At most two run at a time.
- **The auth layer.** Command Center's sign-in (S.C1) is live since 24 October: one sign-in and one sign-out for both apps, one standard account. Change it only when the request names it.
- **Passwords and messages.** The agent never types, sets or resets a password on production; screens are checked on the local copy (`research/golive-2026-10/README.md`). What the owner tells WIA is the owner's: the agent neither writes nor sends messages to WIA.
- **Client names** never go in a code comment or a commit message (R52).
- **Production access** for scripts and API checks is a temporary TCP proxy, deleted afterwards, with production's variables minus every `ATELIER_ALLOW_*` switch, so production's workers do the paid work (DEPLOYMENT.md; `research/golive-2026-10/README.md`, step 1).
- **Pushing.** Push finished work to `main` when the owner asks for it.

---

## 1. Grounding prompt (use once per machine or new start)

```text
You are taking over implementation of Content Atelier, a content engine for Wedding Industry Ads (WIA). Before anyone writes code, get fully grounded on this machine and report what is ready and what is missing. Do not implement plan items in this run.

Repository: find WIA-Content-Atelier under the current folder (WIA-Command-Center may sit beside it). The plan of record is backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md.

Rules for this run:
- Read-only except: installing dependencies into a local virtual environment or node_modules, and writing the grounding report described below.
- Never print, paste or log a secret value. Report only whether a credential is present, and where.
- No paid model calls. No change to any Railway service, variable or deployment. No push.

Steps:
1. Repository state.
   - git fetch; report the current branch, the HEAD commit, ahead and behind against origin/main, uncommitted changes, stashes, worktrees, and local and remote branches.
   - Compare HEAD with the last rows of the plan's Appendix D (implementation log and verification log). List the commits made after the last recorded row.
   - Check the latest GitHub Actions runs with gh.
2. Read the plan in this order:
   - "Start here", "Read this first", "Implementation status" and "Where to resume";
   - section 5.0a (what was built on 23 October, the decisions taken, and the "Next step" list);
   - section 0 (including "Working an item");
   - section 5.0 (the schedule to 27 October) and the milestone tables M0 to M6;
   - sections 2 and 3 (the verified state and WIA's review of 20 October);
   - section 4 (the target, especially 4.2, 4.3 and 4.5);
   - sections 7 (decisions), 8 (risks) and 9 (definition of done);
   - Appendices B, C and D.

   Also skim backend/docs/Angle-Prompt-Profiles.md and DEPLOYMENT.md ("Production services on Railway", "Standing budgets").
3. Toolchain. Report versions and whether each works:
   - Python 3.12 with a working venv for backend/ (backend/.venv);
   - Node 22.12 or later (frontend/.nvmrc says 24) and npm ci in frontend/;
   - Docker, with a throwaway pgvector container (pgvector/pgvector:0.8.2-pg17) for the database suites, and the working copy's container if it is on this machine (atelier-work-pg, database atelier_work);
   - gh;
   - the Railway CLI (signed in or not);
   - psql or pg_dump.
4. Tests. Run the backend offline tests and the frontend type check, unit tests, server tests and production build, exactly as CI does (.github/workflows/ci.yml). If Docker is available, also run both database suites. Report the counts, and any failure that the plan does not already list (risk K69: a failure that moves between runs can be the database clock stepping backwards; see the plan).
5. Credentials (presence only).
   - backend/.env and the other env files: which of OPENROUTER_API_KEY_INTERNAL (and any client key), database URLs, ATELIER_* secrets, and ATELIER_FATHOM_API_KEY or FATHOM_API_KEY are set.
   - Each OpenRouter key's remaining limit and its reset date, read from https://openrouter.ai/api/v1/key without printing the key.
   - gh auth status.
   - railway whoami and railway list. Read-only: list the services, environments and variable names, never values, for the "Content Atelier" and "Command-Center" projects. Note whether the bulk-worker exists, and confirm Command Center production has no AUTH_DISABLED (K64, closed 24 October by S.C1).
6. Data.
   - Is the processed working copy (atelier_work: the October calls of 6.B18, the moments ledger, knowledge base versions) on this machine, and at which migration? Are the dumps of section 5.0a and research/restore-checks-2026-10-23/ present?
   - Check Phase N1's ledger (research/shakedown-2026-10/) and Phase N2's readings (research/n2-delivery-2026-10/). How many of N2's three briefs exist with their readings? Does the brief-done checkpoint (plan section 5.0a) hold? Is D43 recorded as decided (main plan section 7.2; decided 24 October), and is anything in it changed since?
   - Is research/chatgpt-export-2026-10-18/ present? Is the raw ChatGPT export anywhere it should not be (L.X2, D14)? It must never be inside a repository.
   - Are content_guides/ and backend/knowledge_base/ present? The committed default should be version 9 (wia-kb-2026-10-22.c-a1a75795), with version 8 under archive/.
7. Decisions. Confirm section 7.1 is empty (revision 8.8: every WIA-side question is decided under the delegation, D12, and recorded in 7.2). Only money (funding N11) and production go-aheads (D13) stay the owner's. Never list a WIA question as a blocker; decide it under D12 and record it.
8. Write the grounding report to backend/docs/grounding/<YYYY-MM-DD>-<hostname>.md (do not commit it). It contains:
   - a ready or blocked table for each check above;
   - anything that contradicts the plan, such as a status that differs from the code;
   - the exact next step to take, from section 5.0a's "Next step" list (or the milestone that follows it), with its prerequisites and whether they are met;
   - what the owner must supply or decide first.

   Then give a short summary in chat.
```

---

## 2. Implementation prompt (reusable; replace `{{ITEMS}}`)

```text
Implement the following from the Content Atelier implementation plan, fully and to production quality: {{ITEMS}}

Repository: WIA-Content-Atelier. Plan: backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md. Follow section 0, "Working an item (developer conventions)", throughout.

1. Ground.
   - git fetch and pull main; report HEAD.
   - Read "Start here", "Implementation status", "Where to resume", section 5.0a, the latest rows of Appendix D, and the full rows of the requested items in section 5 (their milestone's opening paragraph, each row's work and "done when", the milestone's exit). Also read every ruling (Appendix B), decision (section 7), risk (section 8) and section they cite, and for an item with a long history its rows in the archived revision 7.3.
   - Read the code each item touches before changing it.
2. Check prerequisites. For every requested item, check its prerequisites (the order section 5's opening paragraph fixes, its milestone's "Needs") against the code and the logs, not only the plan text. If a prerequisite outside the request is unmet:
   - if it is small and clearly blocking, say so and include it;
   - otherwise stop that item and report it.

   List any open decision (section 7.1) or WIA input that blocks an item. Never invent the answer; where section 7 gives a recommended default and the item cannot wait, apply the default and record it as such.
3. Plan the work. Write a short, ordered work list that follows section 5's order, and keep it updated as you go. At most two subagents run at a time.
4. Implement, item by item, on a branch named item/<IDs>-<short-name>:
   - Code where section 0 says. Migrations are new numbered files applied by storage_cli migrate. New prompt profiles are new files; a released profile is never edited (E.B17). New routes go on the Node server allowlist (frontend/server/allowlist.mjs), with tests, and only when the app calls them.
   - Tests for every "done when": offline unit tests, database-suite tests where persistence is involved, and frontend unit and server tests for screens.
   - Free models first: a stage runs on paid models only after it has passed the free-model shakedown (plan section 5.0c), and a free-model quirk is absorbed only in the shakedown adapter, never in the core pipeline. Paid model calls only under the standing weekly budget (6.B3) or a run plan, through the llm module with S.B1 routing; never from tests. Run --estimate first and state the cost before any paid run; stop for approval if a single run exceeds USD 5 or the run would pass the funded budget (D36).
   - Content packs: build what the content-packs plan sets. The pack stage reads the brief's hand-off view and acts only on a brief it can consume, and every line a person wrote is kept word for word. Slack is out for now: no Slack work. The Fathom collector and the cycle's schedule stay off until N7.
   - Production changes (Railway services or variables, settings, data transfer, deletions) only when the requested items include them and the owner has approved them (D13). Confirm with the owner immediately before each irreversible step, such as the data cut-over, removing a variable, or deleting data. Change Command Center's sign-in (S.C1, live since 24 October) only when the requested items name it.
   - Never weaken or skip a test to make it pass. Never commit secrets, the raw ChatGPT export, or client material outside research/ and backend/knowledge_base/ (R48, R52). Week 2 text and WIA's 20 October corrections never go into a prompt or exemplar (D28).
5. Verify. Run everything CI runs (backend lint, the OpenAPI check and offline tests, both database suites, frontend type check, unit tests, server tests and build, both Docker builds), plus any live or production checks the "done when" requires (there is one environment, production: D13). For each item, record the evidence against each clause of its "done when". An item is Done only when the whole "done when" is met. Otherwise it is Partly done, with an actionable remainder.
6. Record, in the same branch:
   - each item row, marked "Done (`sha`)" or "Partly done (`sha`): remaining ...", and section 5.0a's "Next step" list (strike what is done, add what is now next);
   - the "Implementation status" table at the top, and "Start here" if the next step changed;
   - a new row in Appendix D's implementation log (date, items, commits, done or partly done, evidence, next recommended);
   - any runbook or doc the change affects (Angle-Prompt-Profiles.md, DEPLOYMENT.md, a hand-over note; a new setting in Appendix C or DEPLOYMENT.md).
7. Deliver.
   - Commit in logical steps with messages starting with the item IDs, ending with the required attribution line.
   - Push the branch and open a pull request to main. Merge it after CI is green only if the owner has authorised self-merge for this run; otherwise leave it for review.
   - Confirm CI on the pushed commit.
8. Report in chat:
   - what was built;
   - each item's status, with its evidence;
   - tests and CI;
   - cost spent, per key;
   - anything left open or blocked, and why;
   - the next step to pick up, from section 5.0a and section 5, given what is now done and what is still blocked.

Note: Never end your turn to wait for a background task or agent, keep the turn active always until you have finished the work. I have other instructions in queue and this will seriously hamper my plans. Please keep this in mind always. 
Also, I am leaving this session unattended, so you will not have any help for me whatsover. Take all the required decisions to the best of your ability aiming towards the goal of generating the highest possible quality output from this system. If there are decisions that truly require my input - defer them and complete as much of the assigned task as you can. some of the blockers seems like menial things that you can unblock yourself . I will repeat this again we have full permissions from the WIA team to do whatever is needed to get this system to be the best possbile engine for them. Stop being lazy and implement the given phase fully please and complete it to the best of your ability
```

---

## 3. Verification and repair prompt (reusable)

```text
Verify and repair what has been implemented in Content Atelier since the last verification.

Repository: WIA-Content-Atelier. Plan: backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md. Follow section 0's conventions.

1. Find the range. Read the last row of Appendix D's verification log. Its "Next run starts from" commit is the start. git fetch and pull main. The range is that commit to HEAD. List the commits in the range, and map them to plan items using commit messages, Appendix D's implementation log, section 5.0a and the item rows.
2. Build the verification list:
   - every item marked Done, Built or Partly done in the range (section 5.0a lists the 23 October build);
   - every item whose code the range touched;
   - the earlier items those changes could break: shared modules, migrations, the context-assembly service, the gate routes, the standing budgets, the Node allowlist.
3. Verify each item independently. Do not trust the logs or the item rows.
   - Read the code and tests. Check every clause of the "done when" against reality, with tests you run yourself. Add a test where a clause is unproven.
   - Run everything CI runs, plus the database suites (twice if a failure moves between runs; risk K69, the database clock). Run production checks where the "done when" requires them (one environment, D13); production checks must be read-only unless a repair needs a change, and then confirm with the owner first.
   - Check the plan for consistency: the item rows, section 5.0a, the "Implementation status" table and Appendix D agree; section 5's order still holds; no ruling (Appendix B) is broken by what was built; the definition-of-done lines (section 9) that the range claims are actually met.
   - Look for gaps: unhandled failure paths (a refusal, a 402, a killed worker must show its reason in the app), missing role checks, secrets in code or logs, client data outside the allowed folders, paid calls outside the standing budgets and run plans, mock or fixture paths reachable from the production build, missing migrations or tests, and any core change made for a free model's behaviour, or a free model or the shakedown routing exception reachable outside a database marked shakedown (plan section 5.0c; risks K70, K71).
4. Repair.
   - Fix each confirmed defect properly, at its cause, with a test that fails before the fix. Commit with "fix(<item ID>): ..." on a branch named verify/<YYYY-MM-DD>.
   - Re-run the checks.
   - If a repair is too large for this run, do not paper over it. Downgrade the item to Partly done, with an actionable remainder.
   - Never weaken a test or a "done when" to make something pass.
5. Record, in the same branch:
   - corrected item rows, section 5.0a and the "Implementation status" table;
   - a new row in Appendix D's verification log: date, range, items verified, issues found, repairs (commits), open after, and the HEAD commit as "Next run starts from".

   Push the branch, open a pull request to main, and merge after CI is green only if the owner has authorised it.
6. Report in chat:
   - the range verified;
   - each item's verdict (confirmed, repaired, or downgraded, with its remainder);
   - the repairs made;
   - anything needing the owner;
   - where the next verification should start.
```

---

## 4. The next step, filled in (Phase N5 with NP-7)

Prompt 2 with its items filled in for Phase N5 and NP-7, which the plan runs together (main plan section 5.0b; next-step rows 5 to 7 of section 5.0a). The run's job is to make the system ready for the WIA team to use. When it ends, NP-7 is built, proved and live, and everything WIA needs for N5's items works on production.

The detail is in:
- the main plan: N5's row in section 5.0b, M5's rows (E.X9, X.2, 7.X2), section 4.5 and Appendix C;
- the content-packs plan: NP-7's rows (NP.B14, NP.B15, NP.B10, NP.X4, NP.X5), NP.B12's .docx and section 4.6;
- the open lists of `research/packs-2026-10/production.md` and `np5-proof.md` (`pack-check.v3`, the labelled cases), and `research/golive-2026-10/README.md` (the 11 documents).

**What the run builds.**

NP-7:
1. Recorded-Reel captions (NP.B14): a paste box on each Reel in a pack, and a new step, `pack_caption.v1`, that writes the caption and three cover options from the pasted take.
2. Pack check v3 (`pack-check.v3`, NP.X5): the fact-check reads the approved brief, so it stops flagging lines the team approved, plus labelled test cases.
3. Word export (NP.B12): the week's pack document as .docx, with a download link.
4. Rewrite with a permission (NP.B15): `pack_refinish` rewrites a pack with a granted permission or an added fact, keeping locked lines.
5. Brief writer v5.1 (NP.B10): the brief writes all three Reels.
6. Pack finisher v3 (NP.X4): a new finisher profile, released through the rule-proposal flow with a release record.

N5:
1. A `storage_cli` command that prints a week's numbers against section 4.5's measures.
2. Fixes to deciding and rating in the app, or to the tone-request flow, only where a test shows them broken.

Set up on production (configuration, not code): personal accounts for Whitney and Gisselle (X.1; the owner sets the passwords), the weekly caps, the 11 "Impromptu Zoom Meeting" documents classified, and the latest calls imported with that week's cycle run.

**Before pasting.** Check the run-authority lines at the top of the prompt. They hold the recommended values, and they are the owner's to change.

```text
Implement the following from the Content Atelier implementation plans, fully and to production quality, so the system is ready for the WIA team to use:

Phase N5 (M5 delivery and the first live weeks) with NP-7 (the content-packs plan's first-live-week items), run together as the main plan's section 5.0b orders:
- NP-7:
  - NP.B14 (the post-recording pass);
  - NP.X4 (the tone loop for packs);
  - NP.B15 (finish again with a permission);
  - NP.B10 (writer v5.1 with three Reels);
  - NP.X5 (labelled check cases);
  - NP.B12's .docx;
  - `pack-check.v3`: the check's sources include the approved brief's WIA perspective (research/packs-2026-10/production.md, "Open").
- N5's system side, so the team can use it from delivery:
  - E.X9: every Gate 1 and Gate 2 decision, and every rating on rubric 2.3a for cards and briefs, works in the app on production and is stored as WIA's when its author is a WIA reviewer.
  - X.2 and NP.X4: the tone loop runs end to end. A tone request, or an edit given twice at either gate or in a pack, travels as a rule or exemplar candidate (L.B3, L.B14) to a compiled knowledge-base version or a new finisher profile. The release is recorded together with the agent's reading of the change.
  - 7.X2: section 4.5's measures for any week can be read from production's data.
  - The standing caps fit a full week of use, and the rule for resetting them after the first live week is written down.
  - From section 5.0a's next-step table: X.1's personal accounts, and the 11 October documents titled "Impromptu Zoom Meeting".
  - Production is current at hand-over. The calls since the last import are in, and their week's cycle has run.

Out of scope:
- WIA's own use of the system: their decisions, ratings, requests and sign-off. Never make or rate a decision for them.
- What the owner tells WIA (D26 and anything else). That is the owner's.
- N7's work, which runs last (the owner, 25 October): the Fathom collector (6.B1), 7.B6's connector step and the cycle on a schedule (3.B11). Never activate the collector or a schedule. Calls come in by hand.
- Slack.
- Any button or screen an item's "done when" does not need.

Run authority (the owner's; recommended values, edit before pasting):
- Spend: at most USD 9 on the internal key for this run's paid calls (NP-7's proofs and the catch-up week's cycle). Never pass the key's weekly limit (USD 15, renewed Monday 00:00 UTC). The Client key is not used.
- Production (D13), go-ahead for:
  - merging and approving deployments;
  - `settings apply` for profiles whose reading passed;
  - the standing caps;
  - the 11 documents' classification;
  - X.1's accounts, except their passwords, which the owner sets.
  - No Railway billing change.
- Self-merge after CI is green: yes.
- Unattended: take every decision the plans leave to the team, and keep the turn active until the work is done (never end it to wait for a background task or agent). Defer only what truly needs the owner, and record it.

Repository: WIA-Content-Atelier (WIA-Command-Center beside it, for X.1). Plans:
- backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md (the plan of record);
- backend/docs/Content-Atelier-Implementation-Plan-Content-Packs.md (NP-7's detail).
Follow the main plan's section 0, "Working an item (developer conventions)", throughout.

1. Ground.
   - git fetch and pull main; report HEAD.
   - In the main plan, read:
     - "Start here";
     - section 4.5;
     - section 5.0a ("N4" and the next-step table);
     - section 5.0b (N5's row and the order);
     - M5's rows;
     - section 7 (D12, D36, D42, D43f, D43i, D43j);
     - section 8 (K76, K79);
     - Appendices B and C.
     In the archived revision 7.3, read the rows of E.F1, E.F2, E.F4, E.X7 and 5.B2.
   - In the content-packs plan, read sections 4.3, 4.6, 5.4, 5.5, 5.8, 5.9, NP-7 and Appendix B.
   - Read research/packs-2026-10/production.md and np5-proof.md (their "Open" lists), and research/golive-2026-10/README.md.
   - Read DEPLOYMENT.md: "What is deployed today", "Standing budgets", and "The week's calls by hand, while the collector is off".
   - Read the code each item touches before changing it.
   - Before any paid step:
     - read the internal key's remaining limit and its reset (never print the key);
     - read production's budgets (`storage_cli budgets show`, through a temporary TCP proxy).

2. NP-7's build comes first (NP.B14 is P0). Work on branches item/NP-7-<name>, with tests for every "done when":
   a. NP.B14, the post-recording pass:
      - On a Reel, "Paste what you said": the take's transcript becomes the Reel's script, word for word and locked.
      - pack_caption.v1 (Opus 5.5, medium effort, a new profile file) writes the caption and three cover options from what was said and the brief's claims.
      - The fidelity check and the deterministic checks run, and the pack version returns to review.
      - The `pack_caption` stage is already registered under the `packs` budget.
   b. `pack-check.v3` and NP.X5:
      - pack_check.v3, a new profile file, takes the approved brief's WIA perspective among its sources, so a stance line the team approved is not flagged.
      - The two clauses the check missed in the proof (np5-proof.md, pairs 2 and 6) become labelled test cases for pack_check.
      - Each factual correction made on a pack later becomes a case the same way.
   c. NP.B12's .docx:
      - the week's pack document as .docx through python-docx (added to requirements.txt), with no client template;
      - `GET /weeks/{id}/packs.docx` beside `packs.md` (and on the Node allowlist);
      - `storage_cli pack-document --format docx`;
      - one download link beside the Markdown one in the pack week view;
      - it opens in Word and in Google Docs.
   d. NP.B15, finish again with a permission:
      - a reviewer grants a "stronger with permission" item, or states an attested fact (R57), in the pack;
      - `pack_refinish` re-runs the finisher with it as evidence, keeping every lock.
   e. NP.B10, writer v5.1:
      - a new file, with contract v4, writing three Reels (story, stance, b-roll text) when Instagram is a channel;
      - the three-Reel schema applies only to v5.1, so N2's v5 briefs still replay at USD 0, byte for byte.
   Everywhere in NP-7:
   - New prompt profiles are new files; a released profile is never edited (E.B17).
   - Test fixtures are synthetic; real call text stays under research/ (R48).
   - Paid calls only under the standing budgets or a run plan, never from tests.

3. N5's system side, with tests:
   - Ratings and decisions (E.X9, E.F1, E.F2, E.F4, 5.B2):
     - check on the local copy that a card and a brief can each be decided and rated on rubric 2.3a in the app;
     - check that a decision whose author is in ATELIER_WIA_REVIEWERS is stored with WIA's label, and any other decision with the delegated one;
     - build only what a check shows missing.
   - The tone loop (X.2, NP.X4):
     - run one request and one repeated edit on the local copy, from entry to a compiled version (and, for packs, to a candidate finisher profile), with the release record and the agent's reading;
     - build only the missing links;
     - the benchmark run of a release happens only when the owner funds it.
   - Acceptance measures (7.X2): one `storage_cli` command prints section 4.5's measures for a given week from the database, with a database-suite test.
   - The standing caps:
     - set so a week of use fits inside the key's weekly room: three briefs, their Gate 2 refreshes and three packs. Recommended: cycle 1.20, briefs 4.00, refreshes 1.50, packs 6.00 for the go-live week (D43f), embedding 0.10, extraction 0.40, context mining 0.10;
     - write the reset after the first live week (packs to USD 3.50, the rest from measured spend) into DEPLOYMENT.md and Appendix C.

4. Prove NP-7: free models first (main plan section 5.0c), then the capped paid proofs.
   - The free-model shakedown runs on scratch copy A, restored from production's latest nightly dump:
     - every new stage goes through the shakedown adapter;
     - failure cases: a 402, a budget cap and its release, a malformed answer, and a worker killed mid-pass;
     - no unclassified finding is left, and each core fix has a test.
   - The paid proofs run on scratch copy B, inside the run's ceiling, with --estimate first for each:
     - NP.B14 on a passage of Whitney's own words from an October call, used as the recorded take;
     - NP.B15 on the probe's brief 1 case (the comparison result);
     - `pack-check.v3` re-checking the October week's packs and the proof's packs against the labelled cases;
     - NP.B10: one paid v5.1 brief with its reading, and a blind reading by a subagent against N2's v5 briefs.
   - Read every output yourself (no paid judge, D39). production-settings.json names a new profile only after its reading passes. A profile that fails stays at today's version, recorded with the reason.

5. Production (D13, given above):
   - Merge after CI is green. On Railway, approve only the newest deployment of each changed service, after checking its commit.
   - Take a fresh db-backup dump, then:
     - `settings apply` with the profiles that passed;
     - set the caps.
   - X.1, personal accounts for Whitney and Gisselle:
     - their WIA addresses come from the records;
     - on Command Center, USER_n_EMAIL, USER_n_NAME and USER_n_ROLE; the owner sets each USER_n_PASSWORD_HASH;
     - a `users` row each;
     - ATELIER_WIA_REVIEWERS set to their addresses.
     If the passwords are not set by the end of the run, record X.1 as waiting only on them. Never invent or reset a password.
   - The 11 documents titled "Impromptu Zoom Meeting":
     - classify each through the app's classify route as the team (delegated), with the recording's name as the evidence;
     - first check that no approved brief or pack loses its evidence;
     - record each decision.
   - Bring production current:
     - import the calls since the last import by hand (DEPLOYMENT.md);
     - production's workers embed them and extract their scenes;
     - start that week's cycle through production's API, exactly as the app starts it.
   - Check the new pack controls on the local copy, signed in with Command Center's development mode, at desktop and phone widths.

6. Verify. Run everything CI runs: backend lint, the OpenAPI check, offline tests, both database suites, the frontend type check, lint, unit tests, server tests and build, and both Docker builds. For each item, record the evidence against each clause of its "done when".

7. Record:
   - research/n5-2026-10/README.md: what was built and deployed, the proofs and readings, and the cost per key;
   - the item rows and exits in both plans: NP-7's items, and N5's system side marked ready for WIA's use;
   - section 5.0a's next-step table, "Start here", the status table and Appendix D;
   - DEPLOYMENT.md and Appendix C.
   Delete every TCP proxy and every local file holding production's variables.

8. Deliver.
   - Commit in logical steps. Messages start with the item IDs and end with the required attribution line.
   - No client name in a commit message or a code comment (R52).
   - Push and open pull requests. Merge after CI is green, as authorised above.

9. Report:
   - what is built and live;
   - each item's status, with its evidence;
   - tests and CI;
   - the cost per key;
   - anything that waits on the owner;
   - the next phase (N8).
```
