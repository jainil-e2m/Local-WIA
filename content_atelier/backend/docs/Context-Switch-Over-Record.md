# Switch from ChatGPT: seed, switch-over and raw-export record (L.X1, L.X2)

**Status, 19 October 2026.** L.X1 and L.X2 are recorded. The seeded queue is reviewed (decision D12). By the owner's decision of 19 October (plan D14), the raw export stays in the owner's custody outside every repository, as a one-time reference that is never re-imported. The switch-over date moves to production go-live (plan D16). This file is the written record L.X2 asks for. Each later step adds a dated line under "Record".

## L.X1: permission, review owner, custom GPT material

| What | Recorded | Where |
| --- | --- | --- |
| WIA's permission for a one-time use of the export (D11) | **Granted.** The owner relayed Whitney's "full permission … to use the chatgpt exports to set this system up for success" (18 October 2026). | Plan section 15.1, D11 |
| The review owner | **Gisselle Jiménez**, about 15 minutes a week. She escalates identity changes (rules, exemplars, voice) to Whitney, who approves them (`ATELIER_IDENTITY_APPROVERS`). | `WIA-Rulings-2026-10-18.md` section 2.5 |
| The custom GPT instructions and ChatGPT memory (E.X1) | **Declined as a source, and not in the export.** On 18 October the export was checked: there is no memory file, and `user_settings.json` holds only interface flags, with no custom instructions. ChatGPT memory is never imported as fact (R52). | `WIA-Rulings-2026-10-18.md` section 1 |

## The one-time seed (L.B2)

- **Run on:** the local test database only, 18 October 2026, by the test suite. Each environment runs `storage_cli context-seed` once, after migration 006. The command reads only committed files, so it gives the same result on every machine.
- **What it loads:**
  - 91 entries from KB 04, 05 and 06, as confirmed items, because WIA confirmed them in E.X2. The approver is the reviewer, and the ruling is the review note.
  - 692 candidates from `research/chatgpt-export-2026-10-18/kb-candidates/` and the exemplar bank.
  - 56 published pieces, as unconfirmed, with the 8 outcomes the export records.
- **Left out:** one entry with an HR detail and one with WIA's own financials. They are counted, and their text is not stored.
- **Citations.** 546 of the 692 candidates cite a conversation file or an export attachment.
  - 413 of those cite it in the analysis drafts themselves. A check on 18 October against the raw export found that every one of the 533 conversation IDs the drafts cite names a real conversation.
  - 133 were resolved once from the raw export, by finding each entry's quoted words in the conversation's text. The IDs and dates, with no export text, are committed in `research/chatgpt-export-2026-10-18/citations-resolved.json`.
  - 135 cite a chunk report (a group of conversations on one topic) and a date. They contain no quoted words to find.
  - 11 cite only their draft: they are the analysis's own summary lines, and the queue marks them low confidence.
  - Two other methods were tested and rejected. Matching by date gave the wrong conversation in 9 of 35 checkable cases, and matching by wording was right only 73% of the time.

## L.X2: switch-over date and disposal

**Switch-over date: production go-live (plan 7.X2; D16, 19 October 2026).** It was first set to Monday 19 October 2026 under D12. It moves because WIA cannot plan content in Content Atelier before the system runs in production; until then WIA keeps working as it does. At go-live an approver brings offers, prices, the team, the content plan and the last 90 days' published pieces up to date through the operating-facts editor (L.F2, L.B10), which R52 allows, so nothing created in ChatGPT in the meantime is lost. From go-live, new facts go through L.F2, and new rules and exemplars come only from WIA's approved work (L.B6) and what WIA publishes (L.B9). WIA can move the date; the owner records the change here.

**Where copies of the raw export are, as checked on 18 October 2026:**

| Location | What | Status |
| --- | --- | --- |
| `C:\Users\KENIL\Desktop\wedding_industry_ads\gpt_export\` on the owner's machine (not a repository) | The full raw export, about 2.5 GB in 979 files: the conversation files, `chat.html`, attachments and settings | **Kept by the owner** (D14, 19 October 2026), outside every repository; the owner carries it to the next machine as a reference. It is never re-imported (R52). |
| `WIA-Content-Atelier`, every branch and commit (61) | No raw-export file appears anywhere in git history. Only the analysis is in git (`research/chatgpt-export-2026-10-18/`, kept under D7 and D11) | Clean |
| `WIA-Command-Center`, its git history | No raw-export file | Clean |
| The machine where the 18 October analysis ran | It ran on the owner's machine; its working copies were session scratch folders outside the repository | Covered by D14 (the owner's custody) |

**What is kept, and who can read it, after retirement:**

- the analysis in `research/chatgpt-export-2026-10-18/`: drafts, synthesis, tests and their outputs, and the citation IDs. It is in the private repository, readable by the repository's collaborators.
- the confirmed items, each keeping its source summary (the conversation file ID and date).

If WIA asks, the research folder's drafts are removed with `storage_cli context-delete-source` and a commit (R52, step 5).

## Record

- 18 October 2026: L.X1 recorded. The seed was built and tested, and the citations were checked against the raw export. The raw export was found on the owner's machine and left in place until the seed is reviewed.
- 18 October 2026: the seeded queue was reviewed under D12: every candidate (704) and published-log entry decided with its reason (`research/chatgpt-export-2026-10-18/seed-review-2026-10-18.json`, applied by `storage_cli context-review-apply`). Knowledge-base version 3 was compiled from it, benchmarked and committed (`backend/knowledge_base/`).
- 18 October 2026: switch-over date set to Monday 19 October 2026.
- 19 October 2026: the owner decided that the raw export stays in the owner's custody outside every repository and moves with the owner to the next machine (plan D14); it is never re-imported (R52). The switch-over date moves to production go-live (plan D16). Before anything else could depend on the export, the Week 2 ChatGPT simulation's angles and scenes (needed by E.B18) were extracted as a derived, model-written reference: `research/final-reconciliation-2026-10-19/week2-chatgpt-simulation.md`.
