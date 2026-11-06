# Blind brief reading 2 (N2, 24 October 2026; D39, R55)

**What was compared.** Six briefs, rendered by the app's own Markdown export with `../blind-reading/blind.py`, cut before the evidence, claims, prior coverage and checks, and shuffled under neutral letters with its fixed seed:

- N2's three briefs, writer v5 with contract v4 (`../brief-1.json`, `../brief-2.json`, `../brief-3.json`);
- the three writer v4 briefs of 20 October, contract v3 (`research/eb23-brief-contract-2026-10-20/results/brief-*.json`).

They are on different cards, so the reading compares craft, not ideas.

**Who read.** The implementing agent is the judge (D39, D40). It had watched the briefs being made, so for this comparison it used a subagent of its own session: no paid model and no outside judge. The subagent read only the six files and the plan's sections 3.2 and 4.3, was told to treat layout as neutral, and had no access to the key (`key.json`, kept outside the repository until it had scored and ranked them). Section order differs between contracts v3 and v4, so the reading is blind to the configuration names but not fully to the layout.

**Result.**

| Rank | Brief | Configuration (from the key) | First-touch | Story fidelity | Voice | Structure (4.3) | Publishable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | E | writer v5: brief 3 | 4 | 5 | 4 | 5 | 4 |
| 2 | B | writer v5: brief 1 | 4 | 5 | 3 | 5 | 4 |
| 3 | C | writer v5: brief 2 | 4 | 3 | 3 | 3 | 3 |
| 4 | D | writer v4 (`brief-d0e9fbc9`) | 3 | 4 | 2 | 2 | 3 |
| 5 | F | writer v4 (`brief-d4f2db12`) | 3 | 3 | 3 | 2 | 2 |
| 6 | A | writer v4 (`brief-1f79f6d4`) | 2 | 3 | 2 | 1 | 1 |

**All three writer v5 briefs rank above all three writer v4 briefs.** Brief 1 (B here) ranked first of four in the first blind reading and second of six here.

**The reader's summary.** Only E and B deliver the whole 4.3 skeleton, and both keep the actors exact; E edges B because its story is concrete. C has the best subject line, but out of caution never tells what the client said. The v4 briefs lose the send header, the second Reel and the carousel title; D refers to Whitney in the third person in her own email; A repeats "office hours" in every asset. The full findings per brief are in `reader.md`.

**The limit of a blind reading.** The reader sees the brief, not the call. Its fidelity score of 5 for brief 3 stands against the brief alone; against the evidence, brief 3's "nearby venue ... before considering theirs" is a paraphrase the call does not support (`../readings.md`, "Brief 3 reading"), a Gate 2 fix.
