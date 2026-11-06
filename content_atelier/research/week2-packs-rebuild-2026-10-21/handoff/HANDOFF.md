# Handoff: WIA Week 2 content packs rebuild (20 to 21 October 2026)

Paste this file into the new chat first. It is written for a Claude session that has none of the earlier conversation. Everything below is what that session needs to pick up the work without re-deriving it.

The new chat runs **on the same machine** (Windows, user KENIL), so every path here works as written and nothing needs copying. Relative paths are under `C:\Users\KENIL\Desktop\wedding_industry_ads\`.

---

## 1. Who and what

- **Client:** Wedding Industry Ads (WIA). Founder and voice: **Whitney Hodges**. **Savannah Jordan** is an outside marketing consultant who wrote WIA's content strategy. **Carmen Cruickshank** is the Google Ads lead (audits, office hours). The roster is in knowledge base document `04-team-roster.md`.
- **Product:** Content Atelier. It turns WIA's call transcripts into weekly marketing content (emails, Reels, carousels) in Whitney's voice.
  - Repository: `jainil-e2m/WIA-Content-Atelier` on GitHub, default branch `main`. Developer: Jainil.
  - Owner and operator: Kenil.
- **The problem being solved.** On 13 October WIA rejected three content packs. The written feedback is in `Copy of WIA - Content Atelier Review.docx`, and there is also `Copy of WIA - Content Angle Review.docx`.
  - The client wanted: not DIY-oriented, a wider audience, punchy hooks, casual spoken scripts, problem-led subject lines, tension on slide 1, varied CTAs, and a clear "why these over everything else".
  - The 13 October packs were **not** system output. The developer generated them in Whitney's ChatGPT.
- **The request this run answered.** Rebuild client-ready packs for the 21 October presentation from the **same source material**. Answer the client's criticisms. Stay honest that the work was hand-built, and keep it realistic for the system to reproduce later. Separately, write an internal findings doc covering what was manual and what the system needs to reproduce it.

## 2. What was delivered (all finished)

| File | What it is |
|---|---|
| `deliverables_2026-10-21/WIA-Content-Packs-Week-of-8-14-June-2026.md` | **Client document**, about 16,100 words. It is assembled from `parts/00_front.md`, `10_pack1.md`, `20_pack2.md`, `30_pack3.md` and `40_bank.md`; edit the parts, then concatenate them in that order. |
| `deliverables_2026-10-21/Content-Atelier-Findings-and-System-Improvements.md` | **Internal findings**, about 6,800 words: findings F1 to F8, G1 to G7 and W1 to W9, 15 recommendations, and owner decisions. |
| `deliverables_2026-10-21/handoff/` | This packet, plus the working notes and scripts copied from the old session's temporary scratchpad (section 9). Use these copies, because the scratchpad under `AppData\Local\Temp` may be cleaned up. |

**The client document contains:**
- a table mapping each piece of feedback to what changed;
- an honest production note (hand-built target, not system output);
- the verified week and a table of the calls;
- five through-lines;
- a strategy brief written **before** angles were chosen;
- a selection table of 13 ideas with reasons;
- a suggested first week;
- three packs;
- a bank of 8 more ideas;
- "For your team, not for publishing";
- a source appendix with transcript timestamps for every quote.

**Each pack has:** an angle card, a brief, an email with send metadata, 3 Reels (cover text, on-screen hook, script, caption), a 9-slide carousel with caption, and a "Before you publish" checklist.

| Pack | Funnel | Angle | Built from |
|---|---|---|---|
| 1 | ATTRACT | "Meta takes your instructions literally" | Ivor, a prospect (T10), Whitney's "Meta is very literal"; The Penny (T01), Meta audit; Diamond A Ranch (T02), the biggest Meta campaign had zero tracked leads, so it was turned off |
| 2 | WARM | Office hours: "turn it off, or give it more time?" | T07 office hours with Carmen (Erin anonymised, Felipe); Noam (T11), a prospect, in Reel 3 with DM "ADS" |
| 3 | CONVERT (ELEVATE) | "When more inquiries aren't enough" | Diamond A Ranch account review (T02), plus what WIA built from July to September (welcome video, selfie and venue photos in follow-up texts) |

**Suggested first week**, assuming it starts Monday 26 October:
- Monday: Pack 1, Reel 1 (save CTA).
- Tuesday 27 October: Pack 3 email (reply CTA).
- Wednesday: Pack 2 carousel.
- Friday: Pack 3, Reel 1 (DM "ADS", the week's only offer CTA).

Pack 1's email is dated 3 November and Pack 2's email 10 November.

**Quality checks done:**
- The project's rejection-rule lint (`rejection-rules.patterns.json`, run by `scripts/lint_packs.py`) gives 0 hits.
- No em dashes.
- Erin is never named.
- Fallon appears only in planning tables, never as current staff.
- Every quote and claim was checked against the transcripts.
- Two critic passes with GPT-6.1 Sol.
  - Scores stayed mostly 2 to 3 out of 5. It was told to be harsh and had no transcripts.
  - The real problems it found were fixed.
  - Its remaining objection: "how we worked through it" in Pack 3 reads as instruction. That was kept deliberately, because it is Whitney's own model. **Ask Whitney.**

## 3. Facts established in this run (do not re-derive; do not get wrong)

**Source period.** The source week is **8 to 14 June 2026**: the Zoom batch "week2", which is benchmark Week 2 and `week_2026-06-08` in the database. It has 11 recordings, T01 to T11.
- In-transcript proof: the World Cup opener on 11 June (mentioned in T07), and a test lead dated 6/11.
- It is **not** the week of the 13 October feedback call.
- Fathom has **no June recordings**; the team used Zoom then. Fathom holds 33 meetings from 5 to 19 October that are not yet ingested.

**Privacy and identity:**
- **Erin** (the T07 office-hours venue owner) is the anonymised **$22K-to-$70K case-study client**. Never name her, and never link her to the case study.
- **Noam** (T11) is a **woman**. The 13 October packs called her "he".
- Diamond A Ranch's owner spells her name **"Ali"**. "aliepler" and "Allie" are the same person.
- **Fallon left on 14 August 2026.** Never present her as current staff.

**Factual corrections already made; keep them:**
- Felipe's experiment was **WIA's** suggestion, not Google's.
- Carmen had never seen the sitelink issue before.
- Clicks are not booked tours.
- Diamond A's campaign had "zero tracked leads", not "booked nothing".
- The discovery call is not "an account we worked on".

**Permissions still needed from WIA before anything is published:**
- The Penny's 0 to 105 tracked leads a month (left out of the copy for now);
- Diamond A Ranch's anonymised story and a LeadLock figure;
- Carmen's 75 to 100 click checkpoint;
- whether the office-hours member may be linked to her case study (default: no).

**Repeat risk.** The 5 to 16 October audit giveaway already argued that "Google's recommendations aren't always what's best". The `published-central-points.json` entry hides this. Because of it, the first ATTRACT idea, "platforms don't share your goals", was replaced and banked for December.

**Content framework.**
- Savannah's ATTRACT, WARM and CONVERT stages, and Whitney's angle framework.
- Knowledge base document 14's plan: one Tuesday email, three Instagram pieces, one offer CTA a week, DM "ADS".
- Offers: ELEVATE, LeadLock, the Ads Accelerators, the Google Search Accelerator. Live audits by Carmen mean "after your audit, who does the work?" waits until November.

## 4. The headline findings (for the plan, and the presentation's "why")

Most of the gap is **upstream of the writer**:

1. The strategist's Week 2 benchmark input is **five hand-picked excerpts** (99 turns, one per meeting).
   - Ivor's prospect call, half the office hours, The Penny's Meta audit and every internal call were never in it.
   - The "selection" WIA asked about happened before the strategist ran.
2. There is no weekly strategy brief, no cross-call synthesis and no account memory. So the system can't:
   - see four calls sharing one idea;
   - spot a repeat of recent content;
   - avoid undercutting a live offer;
   - know what happened to an account later.
3. Strategist v6 splits one client story into 2 or 3 narrow tactic cards. WIA wants one story: what happened, how we worked through it, the standard to expect.
4. Ruling **R31 parks packs**, but the client judges the system on packs. This needs an owner decision.

**What needed manual judgment:**
- connecting moments across calls;
- writing the strategy brief;
- checking freshness against what was actually published;
- resolving identities and privacy;
- following accounts forward in time;
- writing in Whitney's spoken register.

Each is a buildable stage, and none needs a new model.

## 5. State of the repository and PRs

- `main`: the implementation session "Wedding industry ads implementation (091c62)" finished about 04:00 IST on 20 October. Everything is pushed and CI is green. The plan is at revision 7.1, covering E.B23 done and the E.B15 remainders.
- **[PR #12](https://github.com/jainil-e2m/WIA-Content-Atelier/pull/12)**, branch `docs/plan-7.2-week2-findings`, commit `41f75f1`, **OPEN, all 5 CI checks passed. Not merged; merging is the owner's call.**
  - It changes the plan only (`backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md`) to revision 7.2.
  - New proposed items:
    - E.B27 (P0): full-week strategist input;
    - E.B28 (P0): a weekly strategy brief and offer calendar;
    - E.B29 (P0): cross-call synthesis, story cards, strategist v7;
    - **3.B17** (P1): account memory. The findings doc says "3.B14", but that ID was already used. **3.B17 is correct.**
    - 5.B13 (P1): a minimal pack stage, built only if D22 funds it.
  - Extensions to existing items: 1.B12, 1.B13, 3.B5, 3.B10, E.B24, E.B25 (i) and (j), E.X7, L.B2, E.B3, E.B1 and 6.B1.
  - New section 1.10, owner decisions **D22 to D27**, and "Where to resume" step 3.5.
- The local checkout at `C:\Users\KENIL\Desktop\wedding_industry_ads\WIA-Content-Atelier` currently has that PR branch checked out. There is one untracked transcript-export `.txt` at its root; it's harmless and shouldn't be committed.
- Production on Railway is untouched. Frontend deployments that are queued as NEEDS_APPROVAL should stay unapproved until 0.B7, and after that only the newest should be approved.

## 6. Open owner decisions

From the findings doc, section 12, recorded as D22 to D27 in PR #12:

1. **R31 and O24.** Fund a minimal pack stage now (recommendation 8)?
2. **Repetition window.** The knowledge base says 90 days; Whitney said one to two months. Proposed: 60 days, as a ruling.
3. **Internal calls as evidence.** Confirm with WIA: process only, never names or figures.
4. **Account memory sources and consent.** Which later emails and reports count, and how consent is recorded.
5. **Presentation framing.** Present both the 13 October packs and the new ones as non-system output; the new ones are the target.
6. **Permissions** (section 3 above).

Older decisions still open: D15 (early read by Whitney), D17 (fallback date), D18 (OpenRouter budget), and S.C1 (Command Center `AUTH_DISABLED=1` still set in production).

## 7. Recommended next work, in suggested order

The order follows the findings doc, section 9: 1, 3 and 4 first (cheap and high impact), then 5 and 2, then 7 and 10, then 8 after the R31 decision, then 6.

| # | Change | Plan item | Effort |
|---|---|---|---|
| 1 | Strategist on the full week's scenes, not excerpts; the benchmark reports scene coverage | E.B27, 3.B3 | M |
| 3 | Weekly strategy brief: KB documents 14, 05, 13, 01, 03 and 11, the register and an offer calendar; each card cites a brief need | E.B28 | M |
| 4 | Published register at piece level; recency as a ranking penalty or hold | E.B25 (i), 3.B5, 3.B10 | S to M |
| 5 | Cross-call synthesis and story card; strategist v7: one public card per client conversation | E.B29 | M to L |
| 2 | Internal calls as "team practice" evidence; names and figures blocked from copy | 1.B13 | M |
| 7 | Identity resolution: aliases, pronouns, staff dates, do-not-name and do-not-link flags | 1.B12 | S to M |
| 10 | Six new copy checks (caveats in copy, outcome verbs against evidence, self-audit lines, sibling overlap, CTA count, stock phrases) | E.B24 | M |
| 8 | Minimal pack stage over brief contract v3 | 5.B13 (needs D22) | L |
| 6 | Account memory: a per-client timeline of what was recommended, built and measured | 3.B17 | L |

Also:
- KB 18, spoken-voice exemplars (S);
- a second-family critic before Gate 2, about USD 0.16 per pack (S to M);
- handling null content with a `length` finish in `llm/request.py` (S);
- October Fathom intake for the 33 meetings (S to M);
- pack-level rubric anchors (S);
- reading the ChatGPT export properly: `.dat` attachments, branches, authorship (M).

## 8. Environment and budget

**Local database.** Postgres `atelier_work` at `127.0.0.1:25440`, user `atelier`. The password is the CI-only one in `.github/workflows/ci.yml`. It has the `transcripts` table and `week_2026-06-08`.
- It runs locally on this machine. If it isn't up, start it the way the repository's local setup does. The compact transcripts in this packet (section 9) are a fallback.
- Use psycopg 3 from the backend virtualenv; psycopg2 isn't installed.

**OpenRouter.** Keys are in the repository's `.env`, which is not in git: one internal key and one client key.
- Always send privacy routing `{"data_collection":"deny","zdr":true}`.
- Budget after this run: **the client key has about USD 2.98 left and the internal key is at USD 0.** This run spent USD 0.73.
- The owner's earlier rule was to spend sparingly. Confirm the budget before any paid run.

**Model quirks:**
- Sonnet 5.5 through OpenRouter (served by Google) forces reasoning and returned `content: null` with `finish_reason: length` at 9K to 16K max tokens. It's unusable as a critic as things stand.
- GPT-6.1 Sol works, at about USD 0.16 per critic pass.

**Fathom.** API at `https://api.fathom.ai/external/v1/meetings`, header `X-Api-Key` (key in `.env`).

**Windows quirks:**
- `python-docx` is in user site-packages, so `docx2md.py` must run **without** `-I`.
- Heredocs mangle backslashes and quotes, so write edit scripts as files.
- Some scripts read or write folders inside the old scratchpad. Before running one, point it at this `handoff/` folder or at `deliverables_2026-10-21/parts/`.

**Working rules from the owner:**
- WIA approvals are delegated. In unattended runs, decide yourself and defer only owner-only steps.
- "Pause" means stop everything, including agents and background tasks.
- Never claim hand-built work was generated by the system.
- No commits, pushes or deploys without being asked.

## 9. What is in this packet folder

| Path | What |
|---|---|
| `HANDOFF.md` | This file |
| `TASK_INSTRUCTIONS.md` | The original task brief, verbatim, including the unattended-run note |
| `notes/client_calls_notes.md`, `notes/client_calls_notes_T10_T11.md` | Reading notes on the client and prospect calls, with timestamps |
| `notes/internal_calls_extraction.md` | Extraction from the internal calls (T03 to T06, T08 and T09) |
| `notes/chatgpt_export_week2_findings.md` | What the ChatGPT export shows about how the 13 October packs were made. Summaries only; the raw export stays with the owner (D14). |
| `notes/diamond_later_mentions.txt` | Later records on Diamond A Ranch (the July to September build), the basis of Pack 3's "what we built" |
| `notes/critic_sol.md`, `notes/critic_sol_v2.md`, `notes/critic_v1_scores.txt` | Critic outputs before and after revision |
| `scripts/` | `docx2md.py`, `compact_vtt.py`, `export_week.py`, `fathom_check.py`, `grep_context.py`, `lint_packs.py`, `critic.py`, `week2_evidence.py`, `gptx.py`, and the edit scripts from rounds 3 to 5 |
| `transcripts_compact/` | The 11 Week 2 transcripts in compact form (`week2c/`): the evidence base, for when the database isn't available |
| `client_docs/` | Markdown conversions of the review docs and of the strategy, voice and Tier 1 Accelerator docs |

**Not copied:**
- raw full transcripts (the compact form is enough, and they're in the database);
- the raw ChatGPT export and its dumps (the owner keeps those under D14);
- the export "evidence" and "pack copy" companions, which quote the raw export heavily.

**Contains client data.** The transcripts and notes name real clients and prospects. Keep it on this machine, and don't upload it anywhere public.

## 10. How to resume in the new chat

1. Read this file, then the findings doc's section 0 and section 12, then skim the client document's "Read this first".
2. Ask Kenil what came out of the 21 October presentation. Most next steps depend on that and on decisions D22 to D27.
3. Likely tasks:
   - revising the packs from WIA's reactions: edit `parts/`, re-concatenate, re-run `lint_packs.py`, recheck any new claim against the transcripts;
   - merging PR #12 if the owner approves;
   - starting E.B27, E.B28 and the E.B25 (i) register fix in the repository;
   - running the October Fathom intake.
4. Keep the section 3 cautions in force for any new copy.
