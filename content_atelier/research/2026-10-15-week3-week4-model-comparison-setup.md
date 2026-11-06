# Week 3 and Week 4 — independent model comparison setup

**Superseded:** The user selected one shared Luna Pro extraction per week. Use the [revised eight-call setup](2026-10-15-week3-week4-shared-extraction-setup.md). This historical twelve-call plan was never dispatched; its original runner and report were archived before revision. The former `run` CLI action is no longer active.

Prepared 15 October 2026. **Ready for approval of a controlled pilot; no inference calls have been made.** This setup is separate from the application datastore, SQL workflows and the earlier Week 2 handbook experiment. The user explicitly reserved approval of paid execution for a later turn.

## Six comparisons, two stages each

| Week | Admitted files | Delivered turns | Models |
|---|---:|---:|---|
| 3 | 5 | 1,837 | Luna Pro, GPT-6.1 Sol, Claude Sonnet 5.5 |
| 4 | 6 | 1,803 | Luna Pro, GPT-6.1 Sol, Claude Sonnet 5.5 |

The admitted sources are the existing `backend/zoom_backfill_meetings/week3` and `week4` exports. This does not silently add Fathom records from the separate backfill work. Week numbers are folder labels; recording dates are not inferred from them. Exact original bytes were frozen into the experiment's private input snapshot and checksummed.

Each cell independently performs:

1. Full-week Key Moments Identification through the upgraded `weekly_moment_prompt` and `StrategicCompactMomentResponse`.
2. Content Angle Generation through the upgraded `angle_prompt` and `StrategicAngleResponse`, using only that cell's fully validated moments and their original surrounding evidence.

This is **six complete two-stage runs, up to twelve paid requests**, not six angle-only requests. No previously generated or approved angle is an input. The final angle requests cannot be rendered before the respective extraction response exists; their builder, schema, strategy and prompt files are frozen now.

| Slug | Exact OpenRouter ID for both stages | Prepared reasoning |
|---|---|---|
| `luna-pro` | `openai/gpt-6-luna-pro` | `high` |
| `sol` | `openai/gpt-6.1-sol` | `high` |
| `sonnet` | `anthropic/claude-sonnet-5.5` | `high` |

The user explicitly requested high reasoning for Luna Pro. High is also prepared for Sol and Sonnet to make the intended effort setting explicit, subject to the user's review before approval. Equal effort labels do not establish equal internal compute or reasoning tokens across vendors. All six use JSON-object mode with the entire current response contract appended by the existing provider adapter. Temperature is omitted. There is no explicit output-token cap; provider defaults and limits still apply. Request timeout is 900 seconds per request. No new prompt count quota was introduced to force a particular number of samples.

## Isolation guarantees

The suite is `testing/.data/experiments/week3-week4-model-quality-20261015/`. Each cell has its own plan, private pipeline data root, run ID, source projections, artifact cache, raw receipts, costs, candidates and review. The only shared material is the frozen input sources, frozen strategy/prompts and public route metadata.

- All three extraction requests for a week have **identical system/user messages**. Only the requested model differs in the model-facing request configuration.
- The three angle calls naturally have different moment pools because each model discovers its own evidence. No model sees a sibling pool, angle, score, critique or failure. This compares the complete discovery-to-angle behavior, not the angle model alone on an identical pool.
- Week 3 outputs are not supplied to Week 4, including within the same model. Previous eligible signatures are empty in every angle request. No historical/archive retrieval occurs.
- Embeddings are disabled. The pipeline's generation-only branch returns before embedding, ranking, matching, similarity thresholds, recency penalties or historical loading. No SQL/API job, Gate 1 record, refinement call, publishing or brief generation is involved.
- All schema-valid candidates are preserved in the model's returned order, including research-required opportunities and low-self-scoring proposals. No downstream quality/visibility cutoff filters these samples. Existing exact canonical-duplicate checks remain part of whole-response validation; they are not a new similarity pass.
- A single active-cell lock prevents concurrent suite execution. The CLI runs one week/model cell at a time. Intended order is Week 3 Luna → Sol → Sonnet, followed by Week 4 in the same order, with review between weeks.
- Repeated execution of a started cell is blocked. Fresh cells cannot reuse cached generated outputs. Each live stage has a separate exclusive dispatch marker. No automatic retries, repairs, truncation, splitting, model substitutions or partial-pool continuation are permitted.
- If extraction fails validation, that cell's angle request is not sent. Its untouched response and failure/cost records remain available; sibling cells can still be run independently. Failures are not silently converted into successful sample angles.
- Prompt/engine/schema/source identity is rechecked before execution and before each live provider request. Drift requires review rather than silently using different instructions in later comparisons. A returned model ID must exactly match the requested ID.

These safeguards govern this local comparison harness. Remote provider availability and behavior can still change; a catalog check is not a paid endpoint acceptance test.

## Model compatibility and capacity

Public OpenRouter metadata was fetched for each exact route without sending credentials or private transcripts. All three routes were advertised and listed reasoning/response-format support. Snapshots are retained in `backend/.storage-artifacts/verification/week3-week4-models-20261015/` and summarized in the sealed suite catalogs.

One necessary adapter change adds the exact Sonnet ID to the existing model-specific temperature-omission list in `provider.py`. The previous generic `temperature: 0.2` would be inappropriate for Sonnet 5.5. Its [official migration guide](https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide) requires removal of non-default sampling parameters. OpenAI's [GPT-6.1 Sol model page](https://developers.openai.com/api/docs/models/gpt-6.1-sol) and [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning) describe configurable reasoning effort independently of Pro mode. This setup changes no global `.env` values or prompt text.

Local conservative capacity checks use full message UTF-8 bytes plus a margin and the advertised maximum completion reserve. These are explicitly **not native token counts**. Every parameter-compatible endpoint in the saved route catalog must fit this conservative check; otherwise the request is blocked before dispatch. The check is repeated for each future angle request.

| Week | Approximate serialized extraction request | Message/format byte allowance | Extra margin | Advertised output reserve used for the check |
|---|---:|---:|---:|---:|
| 3 | 217,832–217,841 characters | 216,003 | 21,601 | 128,000 |
| 4 | 286,114–286,123 characters | 284,114 | 28,412 | 128,000 |

All six pass against the saved route catalogs. This is not a promise of final provider acceptance or an effective 128,000-token output setting: the actual request omits `max_tokens`. The angle request's final size and billed reasoning/output depend on the extractor's response. Prices are captured in the catalog; actual reported cost and usage are retained per stage. Missing or timed-out billing remains unknown rather than being labelled zero. Native provider prompt caching can alter billing; it is not a local reuse of another run's generated output.

## Prepared artifacts and execution gate

The [setup summary JSON](2026-10-15-week3-week4-model-comparison-setup.json) records the six plans, prompt/engine hashes, schema hashes and preparation status. Inside the ignored suite directory:

```text
suite.json + seal.json
inputs/week3/…
inputs/week4/…
catalogs/{luna-pro,sol,sonnet}.json
schemas/{moment_extraction,angle_generation}.json
cells/week3/{luna-pro,sol,sonnet}/
cells/week4/{luna-pro,sol,sonnet}/
  plan.json
  prepared-extraction.request.json
  data/                         # independent pipeline store
  review.md                     # created only after a successful run
```

Preparation has completed. The command below is **for later execution after user approval**, from `content_atelier/backend`; it runs only one cell:

```powershell
python scripts/prepare_week3_week4_comparison.py run --week 3 --model luna-pro --live
```

Use `sol` or `sonnet` for the other models and `--week 4` for the next week. There is no automatic command that launches all six. Do not delete dispatch markers or started-cell records to purchase an unapproved retry. A future retry needs its own reviewed attempt and preserved lineage.

Each successful cell produces immutable raw responses and parsed artifacts, complete candidate/internal-insight JSON, usage/cost records, and a Markdown review containing original timestamped dialogue for each supporting moment. Reviews are local projections and do not become history for later cells. Actual model responses remain unchanged; rendering supporting passages hydrates original source text.

## Checks actually run

```powershell
python -m pytest backend_pipeline/tests/test_model_experiment.py backend_pipeline/tests/test_generation_only.py backend_pipeline/tests/test_reuse.py backend_pipeline/tests/test_luna_costs.py -q -ra --basetemp=.test-runs/week3-week4-model-setup
```

**62 passed.** After final setup refinements:

```powershell
python -m pytest backend_pipeline/tests/test_model_experiment.py backend_pipeline/tests/test_prompt_upgrade.py -q --basetemp=.test-runs/week3-week4-model-setup-final --junitxml=.storage-artifacts/verification/week3-week4-models-20261015/offline-checks.xml
python -m ruff check backend_pipeline/model_experiment.py backend_pipeline/provider.py backend_pipeline/tests/test_model_experiment.py scripts/prepare_week3_week4_comparison.py
```

**41 passed; Ruff passed.** Counts overlap and should not be added as unique cases. The tests use synthetic responses with outbound HTTP forbidden. They run all six synthetic two-stage cells, verify no sibling-output/history/vector influence, reject model substitutions and repeat dispatch, reject source/prompt/plan drift, and demonstrate that a whole-response extraction failure blocks only its own angle call. Existing source/contract checks remain intact. A non-failing pre-existing requests dependency warning was emitted.

The actual prepare command then froze both real source weeks and all six extraction requests locally. Final verification found **zero dispatch markers and zero started cells**, and reconfirmed equal weekly messages and separate datastores.

## What can be concluded now

The prepared setup can test the requested full pipelines independently, one cell at a time, without embedding/matching feedback. It is ready for the user's approval of those paid calls. No conclusion about which model generates better angles is available yet. A single response per model/week will be a useful qualitative pilot, not a reliability estimate or a statistically stable model ranking. Scores will remain model self-assessments; compare the actual perspectives, evidence, omissions, attribution, internal findings, plain-language framing and editor rewriting effort.

Normal whole-response validation can produce a failed cell or legitimately few/no public angles. That is part of the comparison and must remain visible. The setup has made no paid inference requests, database changes, commits, pushes or deployment changes. Original source files and unrelated work remain untouched.
