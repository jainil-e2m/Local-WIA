# Shared Luna extraction, independent angle models — approval pending

The user accepted changing the comparison to one Luna Pro extraction per week and requested making the revised setup end to end before approving paid testing. No inference calls have been made.

Active suite: `testing/.data/experiments/week3-week4-shared-luna-angle-quality-20261015/`. It has two extraction plans and six angle plans: at most eight paid calls. Week 3: 5 exports/1,837 turns. Week 4: 6 exports/1,803 turns. Source packet hashes match the prior preparation. Key Moments always uses exact `openai/gpt-6-luna-pro`, high reasoning. Angle models are Luna Pro, `openai/gpt-6.1-sol`, and `anthropic/claude-sonnet-5.5`, all high. JSON-object mode, omitted temperature, timeout 900 seconds, no explicit output cap; no global config or editorial prompt changes in this revision.

The revised `model_experiment.py` exposes separate `run_extraction()` and angle-only `run_cell()` stages using the existing Pipeline contracts, validators, raw/cost preservation and evidence builders. Extract once, require whole-response validation, freeze permanent moments, transcript views, reference map and original source context, render a readable shortlist, and stop. The three angle requests are then created from identical system/user messages and empty history. Before each angle call, revalidate the pool against the original accepted extraction and verify frozen request hashes. Angle run lineage points to the common extraction. Separate data roots/caches preserve each response. No embeddings, matching, history, recency, ranking, refinement, SQL, approval or publishing occurs. No repeated calls or automatic repairs/partial acceptance. Shared extraction failure blocks that week's angles; angle failure affects only its own model. Empty shared evidence triggers no paid angle calls. Synthetic evidence cannot feed live angle execution.

CLI after explicit user approval, from backend:
`python scripts/prepare_week3_week4_comparison.py extract --week 3 --live`
Inspect `shared/week3/review.md` and coverage, then invoke `angles --week 3 --model luna-pro --live`, `sol`, and `sonnet` separately. Repeat for Week 4 as authorized. Each command is one call maximum. The old `run` command is removed. The readable-shortlist inspection is an experiment checkpoint, not an additional publication/Gate 1 approval.

Old twelve-call suite is retained untouched and never dispatched. Its uncommitted runner/tests/reports were snapshotted under `research/sources/model-comparison-independent-baseline-2026-10-15/`. The old report now points to the revised report. Do not delete markers, recreate the sealed suite, or relabel prior outputs.

Checks: 67 passed in shared-isolation/existing generation-cache-cost suite; final shared-isolation plus prompt-upgrade checks 48 passed (overlapping counts), Ruff passed. Guarded live code path was exercised with a mocked provider and outbound HTTP forbidden. Real preparation produced zero started/dispatch markers. Exact angle packets await real extraction; no model quality comparison exists yet.

Full details: `research/2026-10-15-week3-week4-shared-extraction-setup.md` and companion JSON. Prior model comparison context is superseded by this file.
