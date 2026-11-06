# Saved experiment audit: per-call facts

Offline reconstruction only; no new inference calls. This table records configuration and counts, not creative approval. Full independent-variable and causal-limit analysis is in the root-cause report.

| Cell | Model | Stage role | Returned counts | Local validation | Input / completion tokens reported | Explicit output cap | Cost USD |
|---|---|---|---|---|---|---|---|
| A-w4-sol | openai/gpt-6.1-sol | candidate_generation | angles=11, internal_insights=7, processed_moment_ids=17, coverage_notes=8 | completed | 96645 / 13988 | None | 0.381491 |
| B-w3-sol | openai/gpt-6.1-sol | candidate_generation | angles=10, internal_insights=13, processed_moment_ids=18, coverage_notes=12 | completed | 103195 / 16029 | None | 0.4055224 |
| B-w4-sol | openai/gpt-6.1-sol | candidate_generation | angles=9, internal_insights=8, processed_moment_ids=17, coverage_notes=9 | completed | 97196 / 14329 | None | 0.3862785 |
| C-source-w3-luna-pro | openai/gpt-6-luna-pro | source_understanding_and_moment_discovery | moments=17, processed_meetings=5, coverage_notes=4 | completed | 248721 / 50838 | None | 0.04429134 |
| C-source-w4-luna-pro | openai/gpt-6-luna-pro | source_understanding_and_moment_discovery | moments=15, processed_meetings=6, coverage_notes=5 | completed | 292805 / 63594 | None | 0.09601107 |
| C-w3-sol | openai/gpt-6.1-sol | candidate_generation | angles=9, internal_insights=9, processed_moment_ids=17, coverage_notes=10 | completed | 101777 / 13463 | None | 0.3776398 |
| C-w4-sol | openai/gpt-6.1-sol | candidate_generation | angles=10, internal_insights=9, processed_moment_ids=15, coverage_notes=10 | completed | 123765 / 15968 | None | 0.4576598 |
| D-w3-sol | openai/gpt-6.1-sol | selection_without_rewrite | assessments=10, priority_keys=2, reserve_keys=1, coverage_notes=5 | failed | 105808 / 3359 | None | 0.2981085 |
| D-w4-sol | openai/gpt-6.1-sol | selection_without_rewrite | assessments=11, priority_keys=2, reserve_keys=1, coverage_notes=4 | completed | 99635 / 3492 | None | 0.284006 |
| E-review-w3-sol | openai/gpt-6.1-sol | comparative_editorial_selection_and_formulation | recommendations=3, decisions=8, processed_moment_ids=18, coverage_notes=10 | failed | 107837 / 6403 | None | 0.333621 |
| E-review-w4-sol | openai/gpt-6.1-sol | comparative_editorial_selection_and_formulation | recommendations=3, decisions=9, processed_moment_ids=17, coverage_notes=14 | failed | 101470 / 7931 | None | 0.3277755 |
| E-w3-luna-pro | openai/gpt-6-luna-pro | candidate_generation | angles=7, internal_insights=9, processed_moment_ids=18, coverage_notes=6 | completed | 357383 / 41386 | None | 0.08340946 |
| E-w3-sol | openai/gpt-6.1-sol | candidate_generation | angles=8, internal_insights=13, processed_moment_ids=18, coverage_notes=10 | completed | 106151 / 14745 | None | 0.412826 |
| E-w3-sonnet | anthropic/claude-sonnet-5.5 | candidate_generation | angles=9, internal_insights=10, processed_moment_ids=18, coverage_notes=7 | completed | 146999 / 25805 | None | 0.552048 |
| E-w4-sol | openai/gpt-6.1-sol | candidate_generation | angles=9, internal_insights=8, processed_moment_ids=17, coverage_notes=9 | completed | 100152 / 11211 | None | 0.3489621 |
| E-w4-sol-repeat2 | openai/gpt-6.1-sol | candidate_generation | angles=10, internal_insights=8, processed_moment_ids=17, coverage_notes=9 | completed | 100152 / 15745 | None | 0.1674709 |

All sixteen returned `finish_reason=stop`, included high reasoning, omitted temperature and explicit max_tokens, and used JSON-object mode. Cross-model token counts are provider-reported and do not imply identical tokenization or compute.

The Week 4 exact repeat had identical messages/settings but different cache usage: first run 5,636 cached prompt tokens; repeat 100,149. Completion tokens were 11,211 versus 15,745. Cost differences therefore do not establish efficiency improvements.

The ten new generation calls returned 92 candidate records. Two source calls returned 32 moments. Four editorial calls returned selection/refinement records; three of those four failed additional research guards. All returned parseable JSON; those three failures were not JSON syntax failures.
