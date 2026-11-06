# Blind brief reading (N2, 23 October 2026; D39, R55)

**What was compared.** Four briefs, rendered by the app's own Markdown export (`blind.py`: `render_v4.markdown_v4` for a v4 document, `gate_two.markdown_v2` for a v3 one), cut before the evidence, claims, prior coverage and checks, and shuffled under neutral letters with a fixed seed:

- the N2 brief, writer v5 with contract v4 (`brief-1.json`);
- the three writer v4 briefs of 20 October, contract v3 (`research/eb23-brief-contract-2026-10-20/results/brief-*.json`).

They are on different cards, so the reading compares craft, not ideas.

**Who read.** The implementing agent is the judge (D39, D40). It had watched brief 1 being made, so for this comparison it used a subagent of its own session: no paid model and no outside judge. The subagent had no access to the key or to anything else in the run. It read only the four files and the plan's sections 3.2 and 4.3, and was told to treat layout as neutral. It scored each brief and ranked them, and only then was the key (`key.json`) opened. Section order differs between contracts v3 and v4, so the reading is blind to the configuration names but not fully to the layout. That limit is recorded here.

**Result.**

| Brief | Configuration (from the key) | First-touch | Story fidelity | Voice | Structure (4.3) | Publishable with light edits |
| --- | --- | --- | --- | --- | --- | --- |
| A | writer v5, contract v4 (N2) | 4 | 4 | 3 | 4 | 3 |
| B | writer v4, contract v3 (`brief-1f79f6d4`) | 2 | 2 | 2 | 1 | 1 |
| C | writer v4, contract v3 (`brief-d0e9fbc9`) | 3 | 4 | 3 | 2 | 3 |
| D | writer v4, contract v3 (`brief-d4f2db12`) | 3 | 3 | 3 | 2 | 2 |

The ranking was A, C, D, B: **the reading prefers writer v5.**

**A's W3 to W8 hits:** none. The subject states WIA's point, the covers name the landing page, slide 1 carries the title, and the b-roll can be followed cold.

**A's rule findings:**
- The Reel 1 script has none of the client's own words.
- Reel 2's screen 2 says "before replacing them", which implies the replacement happened. The brief's own checks flag this as a warning.
- Some caption endings read as aphoristic kickers.
- The carousel slides are dense paragraphs, at the minimum of 7 slides.
- The prose is abstract, and sentences repeat across assets.

**B to D's findings, in summary:**
- Each lacks the email's send header and bold key line.
- Each has only one Reel and no carousel title.
- B repeats W6's "office hours" in every asset.
- B and D have vague covers (W5).
- C's Reel runs about 95 seconds.

**What separates A.** The reader's summary: A is the only brief that delivers the whole 4.3 skeleton, and every one of its first-touch lines names the concrete subject. It wins "on discipline against the standard rather than on prose". C has the most concrete recommendations and D the most natural first-person voice. A still needs a voice pass and the screen 2 fix before it could be published.
