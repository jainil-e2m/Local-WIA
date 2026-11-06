# Duplicate cutoff labels (E.B6), 19 October 2026

What `matching.duplicate` (the card collapse cutoff) was calibrated on.

- **Cards:** the 129 distinct cards in `research/benchmark-v1/runs` (Weeks 1 and 2, every profile and sample). Each was embedded with matching's own card signature (`contracts.signature_from_fields`, `openai/text-embedding-3-small`, 1,536 dimensions), under a run plan, for less than USD 0.001.
- **Labels:** the engineer read every card and gave it the argument it makes (D21; `cards-and-labels.json`). Thirteen arguments in all. A pair is a duplicate when both cards make the same argument. Three judgement calls matter most:
  - Week 1: "each campaign stage has its own creative job" is a different argument from "the ads still have a job after a couple books a tour".
  - Week 2: "we build it, then support you for three months" is a different argument from "Carmen gathers evidence after the click before judging".
  - Week 2: "a smaller first step that fits the help a business is ready for" is a different argument from "we review what you have built before recommending a rebuild".
- **Pairs:** all 4,152 same-week pairs (`pairs.json`), including same-run pairs (the cohort the collapse acts on) and same-source pairs (most cards share their source moments).
- **Sweep** (`sweep.json`): F1 is highest at 0.85 (0.785) and is 0.779 at 0.86. The Week 2 buying-research pair from the stored angles is 0.867 apart. 0.90 had let it through (K6), and 0.87 would too.
- **Chosen: 0.86.** It collapses that pair, with precision 0.90 and recall 0.69 over the labelled pairs. Within one run, it would collapse one pair that makes two different arguments (0.861). A collapsed card stays visible and revivable (R43), so that cost is small.

The vectors are not kept; `atelier-work/tools/eb6_cards.py` and `eb6_fit.py` on the engineer's machine rebuild them from the runs.
