# Week 2 packs rebuild, 21 October 2026 (plan revision 7.2)

The evidence behind section 1.10 of the plan (`backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md`).

An unattended run rebuilt the three content packs WIA rejected on 13 October, from the same source week: benchmark Week 2, the Zoom batch of 8 to 14 June 2026, recordings T01 to T11. The packs were built mostly by hand. They are **not system output** (D26).

The owner then rejected these packs as repeating the same mistakes. The reassessment that followed is in `../v2-reassessment-2026-10-20/` (plan section 1.11). Read the two together: this folder records what the system reads and how it chooses; the reassessment records why complete inputs still were not enough.

Internal. Client material is kept here under R48 (private repository; transcript text only under `research/`). Never publish any of it.

## The findings

| File | What it is |
| --- | --- |
| `Content-Atelier-Findings-and-System-Improvements.md` | The findings document. Recommendations 1 to 15 (section 9) became revision 7.2. Section 0A and section 14 were added by the reassessment: the point tests, the tone and format review, the house style by format (14.9) and both blind reviews (14.7, 14.10). They became revision 7.3, which numbers the second review's lessons as recommendations 34 to 39 |

## The packs and the client's feedback

| File | What it is |
| --- | --- |
| `packs/WIA-Content-Packs-Week-of-8-14-June-2026-21-October.md` | The 21 October packs. Rejected by the owner. A negative example: the blind reviews judged "Meta takes your instructions literally" and the office-hours pack "reject the idea", and the "When more inquiries aren't enough" pack "light edits" |
| `feedback-13-october/WIA-Content-Atelier-Review-13-October-packs.docx` | The 13 October angles, briefs and packs as WIA reviewed them (written by the developer in Whitney's ChatGPT, not by the system). Its layout is the template for the client review document (`../v2-reassessment-2026-10-20/tools/packs2docx.py`, recommendation 39) |
| `feedback-13-october/13-october-feedback-call-transcript.md` | The 13 October call where WIA reviewed those packs: her line-by-line notes (subject lines, slide 1, casual scripts, "zoom out", not DIY) |
| `client-documents/angle_review.md`, `atelier_review.md` | Text of the Angle Review (with Whitney's rewrite tab of preferred angles) and the Atelier Review. The Angle Review's .docx is `client_documents/WIA - Content Angle Review.docx` |
| `client-documents/` (the other three) | Text versions of Savannah's strategy, the Tier 1 Accelerator strategy and the founder voice guide (originals in `client_documents/content_guides/`) |

## The source week and working notes

| File | What it is |
| --- | --- |
| `transcripts-compact/T01` to `T11` | The eleven Week 2 recordings, compacted from the Zoom VTT (speaker turns with timestamps). The full-week input that benchmark v2 (E.B27) and the new scene types (E.B31) are tested on. Kept out of every prompt and exemplar (D28) |
| `notes/client_calls_notes.md`, `client_calls_notes_T10_T11.md` | Reading notes on the client and prospect calls, with timestamps |
| `notes/internal_calls_extraction.md` | The five internal calls: what is WIA practice and what must stay internal (1.B13's extension, D24) |
| `notes/chatgpt_export_week2_findings.md` | What Whitney's ChatGPT export says about this week and her drafting (L.B2's extension) |
| `notes/diamond_later_mentions.txt` | Later records of the T02 venue account (what was built by September): the case for account memory (3.B17) |
| `notes/critic_sol.md`, `critic_sol_v2.md`, `critic_v1_scores.txt` | The two GPT-6.1 Sol critic passes (USD 0.31) and their scores. The case for a critic that sees the ledger and her finals (E.B3's extensions) |
| `handoff/HANDOFF.md`, `TASK_INSTRUCTIONS.md` | The run's handoff and its task brief |

## Tools

Research scripts as used in the run. Most have paths hard-coded to the owner's machine; edit them before use (`critic.py` uses repository paths). None holds a credential (`critic.py` and `fathom_check.py` read `backend/.env` at run time). Paid calls belong under a run plan (E.B1).

| File | What it does |
| --- | --- |
| `compact_vtt.py` | Zoom VTT to compact speaker turns |
| `export_week.py`, `week2_evidence.py` | Export a week's transcripts and evidence from the working copy |
| `grep_context.py` | Search the transcripts with context |
| `gptx.py` | ChatGPT export parser: rebuilds branches from `parent` links, reads attachments, attributes user turns (L.B2's extension) |
| `docx2md.py` | .docx to Markdown (the client documents above) |
| `lint_packs.py` | Runs `backend/knowledge_base/rejection-rules.patterns.json` over pack copy |
| `critic.py` | The second-family critic. Rewritten when it was committed, to send through the product's `dispatch` (privacy routing, a file run plan and its cost cap), as `test_privacy_routing.py` requires of every script under `research/`; run `plan` first, then `run`. Its prompt is the one the run used |
| `fathom_check.py` | Lists Fathom meetings for a date range (6.B1's extension) |
