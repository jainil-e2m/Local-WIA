# Week 3/4 — shared Luna Pro extraction and independent angle comparison

Prepared 15 October 2026. **Ready for the user's approval to test; no inference calls have been made.** This supersedes the earlier twelve-call design. The original prepared suite remains unchanged, and its runner/tests/report were snapshotted under `research/sources/model-comparison-independent-baseline-2026-10-15/` before revision.

## Final experiment

| Week | Complete supplied exports | Turns | Shared extractor | Independent angle models |
|---|---:|---:|---|---|
| 3 | 5 | 1,837 | `openai/gpt-6-luna-pro` | Luna Pro, GPT-6.1 Sol, Claude Sonnet 5.5 |
| 4 | 6 | 1,803 | `openai/gpt-6-luna-pro` | Luna Pro, GPT-6.1 Sol, Claude Sonnet 5.5 |

Each week has **one extraction call and three angle calls**. Across both weeks the maximum is **eight paid calls: two extractions plus six angle generations**. Every request uses high reasoning, JSON-object mode with the current strategic schema, omitted temperature, a 900-second timeout and no explicit output-token cap. Provider defaults and limits still apply. No global environment settings or editorial prompts were changed for this revision.

Sources are the existing Zoom export folders; Fathom intake records are not silently added. Their exact frozen packet hashes match the previous setup. Folder week labels do not establish recording dates. Prompt/engine/schema/source identities are recorded in the new private suite, `testing/.data/experiments/week3-week4-shared-luna-angle-quality-20261015/`.

## Sequence and shared evidence

1. Luna Pro reads the complete admitted week and returns the current `StrategicCompactMomentResponse`.
2. The normal whole-response schema, source-reference, literal-quote, context-containment, inventory and parser checks must pass. No partial acceptance or automatic repair is introduced.
3. The accepted permanent moments, original transcript views, reference map, supporting source passages and extraction lineage are frozen once for the week. A readable shortlist with original dialogue and coverage notes is written for inspection. The extraction command stops here; it never automatically launches angle calls.
4. All three concrete angle requests are rendered from the exact same frozen `moment_packet`, same upgraded angle instructions and empty historical signatures. Their system/user message arrays must be identical; only the requested model differs. Each receives the complete original context admitted for the shared moments, not the other angle models' interpretations.
5. Luna Pro, Sol and Sonnet are invoked separately, each at most once for that week. The pool is revalidated against the original accepted extraction before every child run. Angle-request hashes must match the frozen request previews.

The shortlist inspection is an experiment checkpoint, not Gate 1 approval or publication clearance. No extra human approval record is written into the application. Execution of all paid requests still awaits the user's approval of this setup.

A failed extraction blocks all three angle calls for that week; the other week's extraction remains independent. A valid empty shortlist is retained with coverage notes, and no empty angle call is purchased. A failed angle response affects only that model's result; the next model can use the unchanged frozen pool. No automatic repeat, fallback model, source trimming or retry is allowed.

## Isolation and preservation

There are eight separate stage datastores: one shared-extraction store per week and one angle store per model/week. Each has its own run ID, raw receipts, validated or failed artifacts, cost records and cache. Fresh runs refuse local cached generation reuse and repeat execution. The common extraction is reused deliberately as immutable evidence, rather than being rerun or treated as another model's angle output.

- No angle output, score, critique or failure is passed to another angle model.
- Week 3 outputs and moments are not supplied to Week 4.
- Historical signatures are empty for all angle calls. No archive/history retrieval, embeddings, matching, cosine calculations, ranking, recency adjustment, refinement, brief generation, SQL job or approval operation is invoked.
- Model self-scores and all valid candidate/internal-insight records remain available; no downstream threshold filters the samples. Existing whole-response canonical-duplicate validation remains unchanged.
- Original extraction responses are preserved in their shared stage store. Each angle store has only its own model response and a traceable copy of the common input evidence. Shared extraction costs are counted once per week, not once per angle model.
- Every angle run links to the shared extraction run ID and pool hash. It does not claim to have performed extraction itself.
- A suite-wide active-stage lock prevents overlapping stage execution. Exclusive started/dispatch markers block repeat calls, including retries after an uncertain provider response. Returned model identity must match the exact requested route.
- Live angle execution refuses synthetic/offline extraction evidence. Test fixtures cannot accidentally become real comparison inputs.

Raw responses are saved before local validation. Each successful angle result has a separate Markdown review with original timestamped supporting dialogue, including support for internal insights. These review projections are not fed back into generation. Extraction review and all model reviews remain distinct artifacts.

## Prepared artifacts

```text
week3-week4-shared-luna-angle-quality-20261015/
  suite.json + seal.json
  inputs/week3/…
  inputs/week4/…
  catalogs/…
  schemas/…
  extractions/week3/
  extractions/week4/
    plan.json
    prepared-extraction.request.json
    data/                              # one extraction response/cost per week
  shared/week3/                        # created after valid extraction
  shared/week4/
    evidence-packet.json
    freeze.json
    review.md
  cells/week3/{luna-pro,sol,sonnet}/
  cells/week4/{luna-pro,sol,sonnet}/
    plan.json
    prepared-angle-system.json
    prepared-angle.request.json        # created from actual shared moments
    data/                              # one model's angle response/cost
    review.md
```

The two extraction requests already exist and pass conservative local byte-budget checks against the saved public route catalogs. Their serialized sizes are 217,835 characters for Week 3 and 286,117 for Week 4. Native token counts and paid endpoint acceptance remain untested. Final angle sizes depend on the actual shortlist and are checked when it is frozen and again before dispatch. A budget problem preserves the validated extraction for inspection and blocks angle dispatch; it does not trim evidence.

Public route metadata was verified in the preceding setup. The exact models remain `openai/gpt-6-luna-pro`, `openai/gpt-6.1-sol` and `anthropic/claude-sonnet-5.5`. High effort is explicit for all three, although equal effort labels are not equal compute budgets. Native provider prefix caching can affect cost but does not reuse another model's generated angles. Missing usage or uncertain timeout charges remain unknown.

## Later execution, only after approval

From `content_atelier/backend`, first run the shared Week 3 extractor:

```powershell
python scripts/prepare_week3_week4_comparison.py extract --week 3 --live
```

Inspect `shared/week3/review.md`, the source context and coverage notes. Then run the three separate angle requests:

```powershell
python scripts/prepare_week3_week4_comparison.py angles --week 3 --model luna-pro --live
python scripts/prepare_week3_week4_comparison.py angles --week 3 --model sol --live
python scripts/prepare_week3_week4_comparison.py angles --week 3 --model sonnet --live
```

Repeat that sequence with `--week 4` when proceeding to the second week. Each command makes at most one paid model call. The previous `run` action was removed so an old command cannot silently invoke the revised experiment. Do not rerun preparation over the sealed suite or delete started/dispatch markers to force a retry.

## Verification actually performed

The first shared-extraction isolation plus existing generation/cache/cost suite passed **67 tests**. After final lint cleanup and adding guarded live-path tests, the final checks were:

```powershell
python -m pytest backend_pipeline/tests/test_model_experiment.py backend_pipeline/tests/test_prompt_upgrade.py -q -ra --basetemp=.test-runs/week3-week4-shared-final --junitxml=.storage-artifacts/verification/week3-week4-models-20261015/shared-evidence-tests.xml
python -m ruff check backend_pipeline/model_experiment.py backend_pipeline/tests/test_model_experiment.py scripts/prepare_week3_week4_comparison.py
```

**48 passed; Ruff passed.** Counts overlap and are not additive. All responses in these checks were synthetic and outbound HTTP was forbidden. Checks cover an eight-call two-week sequence, identical angle inputs, strict source/quote validation, failures isolated correctly, pool/request/original-output tampering, synthetic-to-live promotion refusal, no embedding/history/ranking, one-call dispatch guards, and the guarded live code path with a mocked provider rather than real network calls. A pre-existing requests dependency warning was non-failing.

Actual preparation then captured the real sources and two extraction requests locally. No real pool or model angles exist yet. Final inspection confirms zero started stages and zero dispatch markers. Original source files and the earlier sealed suite remain unchanged. No paid calls, database operations, commits, pushes or deployment occurred.

## Conclusion

The revised setup is ready to test after approval. It now isolates **angle-generation quality on identical evidence**, conditional on Luna's discovery. It does not compare the three models' extraction ability and cannot recover a valuable exchange Luna omitted. Inspect source coverage as well as quotation validity before interpreting the comparison. A single response per model/week supports a qualitative pilot, not a statistically stable model ranking or proof of founder acceptance.

Machine-readable plans and identities are in the [shared-extraction setup JSON](2026-10-15-week3-week4-shared-extraction-setup.json). The previous twelve-call implementation and report are retained as a historical baseline; the active runner targets only this new eight-call suite.
