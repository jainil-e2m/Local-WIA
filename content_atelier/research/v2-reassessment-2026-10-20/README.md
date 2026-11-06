# The v2 reassessment, 20 October 2026 (plan revision 7.3)

The evidence behind section 1.11 of the plan (`backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md`) and its pack standard (section 2.4b).

The owner judged the 21 October packs (`../week2-packs-rebuild-2026-10-21/`) as repeating the mistakes WIA had rejected. An independent reassessment reread the client's feedback, every client and prospect call of Week 2 and about 30 of Whitney's content threads in the ChatGPT export, and rebuilt the packs by hand three times:
1. after a first blind review;
2. after the owner's review of tone, titles and format;
3. after a second blind review.

**The v2 packs are the target the system is built to reach. They are not system output** (D26). Week 2 stays out of prompts and exemplars (D28).

Internal. Client material is kept here under R48. Never publish any of it.

## Read in this order

| File | What it is |
| --- | --- |
| `Diagnosis-Why-The-WIA-Packs-Keep-Missing.md` | Why the packs kept missing. The system tests the subject of an idea, never its point. Ranking by evidence volume picks mechanics. The human layer of a call is drowned. Also: pack-by-pack comparisons, the tone and format review (section 8) and both blind reviews (sections 7 and 9) |
| `Reproducibility-and-System-Findings.md` | The method as a 9-step procedure (plan section 1.11.2), what stayed human, and the mapping to plan items |
| `packs/WIA-Content-Packs-Week-of-8-14-June-2026-v2.md` | **The target.** Three packs, each with an angle (Whitney's tab format), a brief, an email, three Reels (story, stance, b-roll text) and a carousel. Also: how the ideas were chosen, a content bank, team notes, and an appendix of timestamped source moments |
| `packs/WIA-Content-Packs-Week-of-8-14-June-2026-v2.docx` | The three packs only, in the layout WIA reviews (built by `tools/packs2docx.py`) |
| `packs/superseded/` | The v2 packs before the tone review, and before the second blind review. Kept so each review's changes can be diffed |
| `blind-review/whitney-finished-pieces.md` | Whitney's finished pieces, verbatim: the bundle the second blind judge read first. It contains her 10 June, 29 June and 15 September emails, her 25 June and 1 October captions, her recorded 18 August Reel, and her approved $22K and 10-week carousels. It is the seed for knowledge-base document 19 (L.B12) and the comparison set for E.X8 |

The full findings, recommendations 16 to 33 and the house style by format, are in sections 0A and 14 of `../week2-packs-rebuild-2026-10-21/Content-Atelier-Findings-and-System-Improvements.md`.

## How the plan uses this

| Plan item | What here it rests on |
| --- | --- |
| E.B30 (the five-test gate) | Diagnosis sections 2 to 4; Reproducibility, step 4 |
| E.B31 (human-line and counter-expected scenes) | Reproducibility, step 2; the v2 packs' appendix of moments |
| E.B32 (her angle card and title rule) | Diagnosis section 8 (T1, T2); the v2 packs' angle cards |
| E.B33 (writer v4) and E.B24's extensions | Plan section 2.4b; Diagnosis sections 8 and 9 |
| 5.B13 (packs) | The v2 packs; `tools/packs2docx.py` for the review document (recommendation 39) |
| L.B12 (KB 19) and E.X8 (blind comparison) | `blind-review/whitney-finished-pieces.md`; the blind review records |

## Tools

Paths are hard-coded to the owner's machine; edit them before use. No credentials.

| File | What it does |
| --- | --- |
| `packs2docx.py` | Renders the three packs of a pack Markdown file into the client review layout. It uses the 13 October review document as its template (`../week2-packs-rebuild-2026-10-21/feedback-13-october/WIA-Content-Atelier-Review-13-October-packs.docx`) and keeps its header, logo and title block. Usage: `python packs2docx.py <template.docx> <packs.md> <out.docx>` |
| `aiphrase.py` | Counts the constructions her team flagged as "AI phrases" in ChatGPT: paired "it's not X, it's Y" contrasts, "not because… but because", "the real X is", "you don't have an X problem", staccato runs, em dashes. A prototype for E.B24's extension; it does not yet catch aphoristic kickers |
| `gptx.py` | The export parser (a copy of `../week2-packs-rebuild-2026-10-21/tools/gptx.py`, which the three scripts below import from their own folder). It reads the raw export from the owner's machine, never from the repository (D14) |
| `finals.py` | Writes `blind-review/whitney-finished-pieces.md` from the export, by conversation and message ID |
| `useronly.py`, `ctx.py` | Dump the user turns of chosen conversations, and a message with the turns after it, from the parsed export |

**Cost.** No paid call. The blind reviews used Claude subagents.
