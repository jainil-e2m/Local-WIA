# Week 2 handbook prompt test

Jainil requested testing both printed handbook prompts on Week 2, preserving/commenting the previous system prompts and making only the necessary changes. The exact model was carried forward as `openai/gpt-6-luna-pro`. Earlier explicit OpenRouter transfer permission and the new instruction to make the calls authorized these two new requests. No additional confirmation was requested; no third model call or paid retry occurred.

## Implementation scope

The reviewed outputs were incompatible with the existing strategic-v1 schema. A separate explicit `handbook_v2` profile was therefore created with the old system prompts preserved in inactive HTML comments, exact reviewed active text, and a matching test-only contract/packet adapter. Existing production defaults, prompt builders, strategic-v1 contracts, SQL storage, UI, provider adapter and environment defaults remain unchanged.

New files: `backend_pipeline/handbook_contracts.py`, `backend_pipeline/handbook_testing.py`, `backend_pipeline/prompt_templates/handbook_v2/`, `scripts/run_week2_handbook.py`, and `tests/test_handbook_prompt_profile.py`. Eighteen meaningful source-boundary/contract tests passed. The dedicated renderer strips old comments, checks the reviewed active-text hash, and hydrates evidence directly from source refs instead of model-authored quotation strings.

## Actual outcome

- Run: `week2-handbook-luna-pro-20261013-b1`.
- All 11 Week 2 exports / 5,218 turns supplied; current files and archived raw copies match the earlier hashes.
- Moment call: 7 proposals, 2 passed initial record/source-binding checks, 5 rejected. Reasons included exact speaker-label mismatches and assertions/contributions outside declared context regions. One budget record failed only on `Lauren` versus `Lauren Christensen`; do not interpret every rejection as fabricated content.
- Angle call used only the two validated moments and original surrounding context. It returned 2 candidates and 1 INTERNAL finding; initial angle-contract checks passed.
- Candidates: “Let local client knowledge shape the map” (WARM/process) and “Reviews and buying research answer different questions” (ATTRACT/thought_shift). Both come from the same recording. The proposed LeadLock survey workflow remained INTERNAL.
- Both responses returned exact `openai/gpt-6-luna-pro`, provider OpenAI, finish reason stop. Reasoning stayed low and JSON-object mode stayed configured; completion cap remained null. No embedding, third judge, drafting or publication.
- Costs: extraction `$0.11630392`; angle selection `$0.01035358`; total **$0.12665750**. Provider billing includes cache/reasoning usage; purchase fees are not included.

## Important post-run findings

The initial extraction validator did not validate every excluded-material reference. A later audit found 10 nonexistent refs in its m4 exclusion note. Recording acknowledgements and initial empty coverage-contract errors are not proof of complete source interpretation or valid exclusion reasoning.

Both selected angles' nearest-alternative `candidate_key` values point back to themselves while their prose describes different points. The initial structural check allowed this; comparison metadata remains defective. The research-versus-reviews point substantially overlaps the prior v1 test and its title is identical. Relabeling it ATTRACT is not evidence of new discovery. Its thought_shift type versus the handbook's WARM taxonomy needs review.

Some source exclusions still rely too much on missing completion/results, including the phase/campaign explanation and chat-widget evaluation. The assistant inspected original supporting turns and retained seven audit excerpts, clearly separated from model-selected output. They are evidence for review, not recovered/approved angles.

Current verified offer records, current content plan and recent published history were not provided. These absences are explicit in the requests. No historical novelty or campaign-mix claim can be inferred. The result is a partial two-call diagnostic, not successful whole-week acceptance or founder approval.

## Artifacts and next work

Readable review: `research/week2-handbook-luna-pro-test-review-2026-10-13.md`.

The run directory retains exact requests, raw receipts, untouched model outputs, moment context refs, rejected records, initial validation, `postrun-diagnostics.json`, `assistant-assessment.md`, and `final-summary.json`. Offline `review` regenerates the document without inference. The two paid dispatch markers must remain intact; do not repair the historical model outputs or issue another paid call without further instruction.

Focused next corrections are source-label hydration, fewer redundant ref declarations or stronger all-reference/context consistency, validating skip refs, preventing self-referencing alternatives, and preserving proposed/process/internal material without requiring outcomes. Then test a full valid pool and obtain Whitney's review of points and omissions. This task did not implement those follow-on corrections or rerun inference.
