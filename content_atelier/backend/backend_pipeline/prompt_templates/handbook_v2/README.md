# Handbook prompt test profile

Version: `2026-10-13.wia-handbook.v2-test`.

Both system templates contain the previous strategic-v1 system prompt in an inactive HTML comment, followed by the exact behavioral prompt reviewed in `research/2026-10-13-handbook-system-prompts-proposal.md`. The dedicated renderer removes comments before transmission and checks the active prompt hash. It adds the curated handbook references, known input limitations, packet adapter, and typed output contract.

This is an explicit calibration profile. Existing `prompts.py`, default system/user templates, strategic-v1 contracts, provider code, SQL workflows, environment defaults, and UI were not migrated. Do not substitute this profile into the old runner without its matching contracts and packet adapter.

The two-call Week 2 run is `week2-handbook-luna-pro-20261013-b1`, using exact `openai/gpt-6-luna-pro`. Both dispatches have completed. The script refuses another dispatch for a stage whose marker exists. Do not remove those markers or change the run ID to purchase a retry without a new user instruction.

Offline review:

```powershell
python scripts/run_week2_handbook.py review
```

Run from `content_atelier/backend`. Requests, raw receipts, untouched model outputs, valid/rejected records, validation summaries, post-run diagnostics, and independent assessment are preserved under `testing/.data/experiments/default/runs/week2-handbook-luna-pro-20261013-b1/`. The readable review is `research/week2-handbook-luna-pro-test-review-2026-10-13.md`.

The result is partial: 7 proposed moments, 2 passing the initial source-binding contract, 5 rejected, followed by 2 model-selected angles and 1 internal insight. Additional post-run exclusion-reference and alternative-pointer defects remain. Source binding is not semantic verification, opportunity recall, founder approval, or publication clearance. See the review before changing any prompt or validation policy.

## Prepared full handbook angle call

The next angle-only request includes the complete content-only `wia_content_system_handbook.md`, the latest supplied `angle_generation_feedback.md`, and the actual `market_research_email.md` body for a limited overlap check. The handbook file has natural Markdown headings and tables, without extraction IDs, HTML tags, document-version labels, hashes, or audit wrappers. The historical email is an overlap reference, not verification of current offer scope.

The default command prepares and saves the request locally:

```powershell
python scripts/prepare_week2_full_handbook_angle.py
```

Its separate run ID is `week2-full-handbook-angle-20261013-c1`. It reuses only the two individually validated moments from `b1`, including all 114 original context turns. Rejected extraction records and prior requests/receipts remain untouched. The full handbook and latest feedback are inserted into the second-stage system context; the email and actual evidence are supplied as data. There is no current content plan or independently verified current offer record.

On 14 October, the user requested `high` reasoning before the next Week 2 call. The backend-local configuration and environment example now set `CONTENT_ATELIER_LLM_REASONING_EFFORT=high`, and the undispatched `c1` request has been refreshed accordingly. The earlier `b1` calls retain their original `low` setting in their saved requests. Preparation and execution both read the configured effort; a different process environment can override the local file, and execution rejects a request/configuration mismatch.

Paid execution is gated by an explicit `--live` option. Preparation does not instantiate a provider or dispatch inference. Execution checks that the saved request/configuration still matches, and it refuses a duplicate dispatch. No live call was made while setting up this request.

The pre-change local Git checkpoint is `c7d3eb6`. The full-handbook changes are tracked separately for rollback. No GitHub push is part of this setup.
