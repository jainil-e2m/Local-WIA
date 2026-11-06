# Final reconciliation, 19 October 2026 (plan revision 7)

The evidence behind section 1.9 of the plan (`backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md`).

## E.B22: brief writer v3 against v2 (section 1.9.8)

| File | What it is |
| --- | --- |
| `extract_inputs.py` | Exports the live development week's three developed cards, their first v2 briefs and the evidence those briefs used from the 18 October review store (`atelier_test_review2`) into `inputs/` |
| `inputs/angle_*.json` | Those inputs (call excerpts already committed under `research/`, R48) |
| `brief_write.v3.candidate.md` | The candidate prompt as tested; it ships unchanged as `backend/backend_pipeline/prompt_templates/brief_write.v3.md` |
| `exp_brief_writer.py` | The experiment: `plan` (a file run plan), `write` (six writer calls, the product's request shape), `judge` (six calibrated-judge calls in both orders), `report` |
| `run_plan*.json`, `*.calls.jsonl` | The run plans and their call ledgers (all closed or exhausted); the first judge plan's only call was refused by the privacy routing before sending |
| `runs/` | Every model response, with cost and token counts |
| `results/eb22-brief-writer.json` | The result: v3 won 6 of 6 judgements; edits needed 2.2 against 3.8; claim-boundary phrases in copy 0 against 9; USD 1.17 |

To repeat it on another machine: restore `atelier_test_review2` (or reuse `inputs/`), put `OPENROUTER_API_KEY` in `backend/.env`, make a new plan (`python exp_brief_writer.py plan` after moving the old one aside), then `write`, `judge` and `report`. Saved responses are reused, never paid for twice.

## The Week 2 ChatGPT simulation

`week2-chatgpt-simulation.md`: the angle review and briefs ChatGPT wrote for benchmark Week 2 on 13 October (model-written; derived from the raw export, which stays with the owner, D14). It is E.B18's reference set and a candidate list of Week 2 golden scenes (E.B2), never trusted text.
