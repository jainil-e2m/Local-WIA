# Strategic discovery prompt upgrade — implementation and local verification

Recorded 15 October 2026. The supplied Key Moments and Content Angle candidates are installed in the normal strategic prompt builders, with only the three user-approved wording reconciliations. Initial generation and refinement passed local prompt/schema/parser checks. Editorial effectiveness has not been evaluated with a model, and the SQL integration cases were skipped because no isolated test database was configured. No provider calls, database operations, approval changes, deployment or GitHub push occurred.

## Baseline and authorized scope

Repository: `C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier`, branch `feat/content_brief`, baseline commit `aafa8c24246daaa6e89e7f3bb7d717dd0f1b8b23`. All four runtime target files were already tracked and matched that commit before editing. Substantial unrelated intake/backfill/frontend work was present and was left untouched. No baseline commit was made containing that work, and this upgrade has not been committed or staged.

No applicable `AGENTS.md` was found in the inspected workspace/repository/target directories. The implementation brief and the user's three approved reconciliations supplied the task constraints. Embedded historical/audit examples were treated as reference material, not independent implementation authority or newly verified founder evidence.

Original packages remain unchanged at their supplied Downloads paths. Byte-identical snapshots, including both handoffs and the angle static-check manifest, are preserved under [sources/prompt-upgrade-2026-10-15](sources/prompt-upgrade-2026-10-15/), retaining the original folder names. Original and installed hashes are recorded separately in the [verification record](2026-10-15-strategic-prompt-upgrade-verification.json).

## Changed application files

| Destination | Installed material and change |
|---|---|
| `backend/backend_pipeline/prompt_templates/moment_extraction.weekly_v3.md` | Complete supplied Key Moments candidate, with bounded offer context and targeted source/handling safeguards. |
| `backend/backend_pipeline/prompts.py` | Exact supplied weekly prefix becomes `KEY_MOMENTS_WEEKLY_PREFIX`; `weekly_moment_prompt()` appends the unchanged complete source packet once. Its signature, inventory and return structure remain unchanged. |
| `backend/backend_pipeline/prompt_templates/angle_generation.system.md` | Supplied angle system with one conditional paragraph clarification for initial generation/comparison versus refinement. |
| `backend/backend_pipeline/prompt_templates/angle_generation.user.md` | Byte-identical supplied candidate; no reconciliation edits. |

The [candidate-to-installed reconciliation diff](2026-10-15-strategic-prompt-reconciliations.diff) separates the narrowly scoped edits from the overall replacement of the older templates. No old supplement was indiscriminately appended to a candidate.

Verification-only changes are `backend/backend_pipeline/tests/test_prompt_upgrade.py` and two wording assertions in the existing `test_strategic_discovery.py` and `test_prompt_contracts.py`. The latter now recognize the candidate's equivalent privacy-of-reasoning and untrusted-source language as well as the previous phrasing. No validator expectation or acceptance rule was weakened.

## The three reconciliations

1. **Offer context:** Replaced the concrete offer-description paragraph with the bounded paragraph specified in the implementation brief. ELEVATE, the Ads Accelerators and LeadLock remain strategic background; their names do not establish current scope, capabilities, ownership, pricing, availability or delivery in a particular exchange. Missing details remain uncertainties or precise questions. Historical dialogue is not rewritten.
2. **Extraction safeguards:** Added explicit timed-cue syntax, real meeting-local references, delivered ordinal order despite overlapping/unknown times, inclusive expansion of every context cue, real reference-based coverage notes, `unknown` sensitivity when handling permission is absent, and distinctions among inquiries, appointments, bookings, attribution and comparable spend periods/cost bases. Existing literal one-anchor quote rules and support for `CUE_SETTINGS`, `UNTIMED` and `TIMESTAMPED` remain intact. The richer discovery procedure, second semantic coverage pass, collaboration, audience intelligence and absence of quotas are preserved.
3. **Refinement:** The shared system now limits `internal_insights` output to initial generation and historical comparison under their active contract. During refinement, internal intelligence is context for evaluating a replacement or explaining why none is supported. The model must not output that field or imply that additional intelligence records are being created. The existing `outcomes` envelope and schema remain unchanged. No additional intelligence persistence path was added.

## Actual execution paths and invariants

Inspected `prompts.py`, `pipeline.py`, `sql_pipeline.py`, `strategy_contracts.py`, `contracts.py`, `weekly.py`, `prepare.py`, `provider.py`, `refinement.py`, the comparison/refinement supplements and relevant tests.

- Weekly systems retain base extraction → shared strategy → shared editorial policy → weekly supplement → trusted inventory. Provider-managed schema handling is unchanged.
- The default angle builder retains per-moment original `source_evidence` and receives an empty prior-signature list in the inspected normal callers. That is not evidence of historical novelty.
- SQL comparison/refinement retain deduplicated `evidence_by_id`, current moment references and historical context. Both exact user-template split markers are preserved once and in order. Initial-generation envelope instructions remain outside the refinement prefix.
- Placeholder substitution remains nonrecursive. Token-like strings in source text are preserved as data, including after SQL evidence deduplication.
- Local extraction keys remain proposal labels. Backend resolution/parsing still establishes canonical source passages and permanent moment IDs before angle generation. Source revisions, discovery metadata, qualifications and handling risks survive the boundary.
- Shared policy/strategy, base extraction, legacy user template, schemas, validators, scoring, thresholds, historical eligibility, embeddings, Gate 1 and provider settings were not changed. Their protected file hashes match the pre-edit snapshot.
- Whole-response validation remains intact. No partial acceptance, automatic repair, extra extraction calls, new roles or dynamic runtime profile loader was introduced.
- The shared strategy/version constants remain unchanged. Candidate IDs identify supplied designs, not a new runtime profile. Full changed request contents still feed existing cache identity; no caches or artifact dates were reset.

## Local verification actually executed

From `content_atelier/backend`:

```powershell
python -m pytest backend_pipeline/tests/test_prompt_upgrade.py backend_pipeline/tests/test_strategic_discovery.py backend_pipeline/tests/test_prompt_contracts.py backend_pipeline/tests/test_comparison_workflow.py backend_pipeline/tests/test_citation_adapter.py backend_pipeline/tests/test_generation_only.py backend_pipeline/tests/test_preparation.py backend_pipeline/tests/test_luna_costs.py backend_pipeline/tests/test_reuse.py -q -ra --basetemp=.test-runs/prompt-upgrade-20261015-verified
```

Result: **142 passed, 22 skipped**. Skips are isolated PostgreSQL `atelier_test` comparison-workflow cases; no test database was provisioned or mutated. Existing autouse fixtures forbid outbound HTTP. Synthetic provider results establish engineering behavior, not real model editorial quality.

The first focused run found two assertions requiring previous prompt sentences verbatim: **57 passed, 22 skipped, 2 failed**. Both were reconciled to recognize the unchanged safeguards expressed by the candidate. The expanded suite above then passed.

After resolving the test fixture import's lint issue, the new module was rerun independently:

```powershell
python -m pytest backend_pipeline/tests/test_prompt_upgrade.py -q --basetemp=.test-runs/prompt-upgrade-20261015-final --junitxml=.storage-artifacts/verification/prompt-upgrade-20261015/focused-tests.xml
python -m ruff check backend_pipeline/prompts.py backend_pipeline/tests/test_prompt_upgrade.py
```

Results: **31 passed**, **Ruff passed**. A pre-existing requests dependency warning was emitted during pytest; it did not fail these tests. The new tests exercise actual builders and parsers, valid and invalid source/context/quote binding, required nullable fields, finite/range checks, citation prefixes, foreign IDs, internal-only initial output, both refinement outcomes, handling propagation and rejection of extra refinement intelligence fields.

Task-scoped `git diff --check` passed. A repository-wide check also encountered whitespace issues in unrelated pre-existing `repository.py` edits; those were not changed or included in a clean-check claim.

## Rendering, hashes and Week 2 size

Generated the three current strategic schemas and compared them with pre-upgrade snapshots: unchanged. The supplied angle hashes match its original manifest, the installed weekly prefix equals the supplied text exactly, and all seven original package files still match their archived snapshots.

Sixteen local synthetic request snapshots cover baseline/installed × weekly/initial/comparison/refinement × JSON-object/JSON-schema modes. They preserve one system and one user message and the active contract. Each changed request differs from its baseline counterpart. Full request-file, system and user hashes are in the verification JSON; request bodies are in the ignored local folder `backend/.storage-artifacts/verification/prompt-upgrade-20261015/`.

The complete archived Week 2 packet was also assembled locally through the real weekly builder: **11 sources, 5,218 turns**, with exact source content retained after the prefix. Under the unchanged configured model/format/settings, serialized request size grew from **545,931** to **557,333 characters**. No transcript trimming or additional dispatch occurred. These are character/byte diagnostics, not native token counts or newly verified model capacity. Existing local capacity validation is disabled in the current test configuration; it was not changed by this upgrade. The angle-stage size will depend on the new extractor output and cannot be established from this assembly check.

The guidance on clear instruction/data boundaries and evaluating prompt changes is consistent with [OpenAI's prompt engineering guide](https://developers.openai.com/api/docs/guides/prompt-engineering). This external reference supplies no WIA facts or evidence that these candidates improve output.

## Rollback

The baseline versions of all four runtime targets and both adjusted existing test files are available at `aafa8c24246daaa6e89e7f3bb7d717dd0f1b8b23`. Before any commit, inspect the current diff and reverse only this task's edits to those six files together. Remove the newly added verification test if rolling back the upgrade; preserve the source snapshots/report if they are still useful. Do not restore or reset the whole checkout, stage unrelated work, or delete runtime datasets. Check for later overlapping edits before restoring a path.

If this task is committed later, prefer reverting only its own commit(s). After either rollback, re-render the weekly/default/comparison/refinement requests and rerun relevant checks. No environment setting or database state needs rolling back for this file-only upgrade. Earlier provider charges and saved outputs are unaffected.

## Readiness

| Milestone | Status |
|---|---|
| Installed with targeted reconciliations | Complete in the local working tree. |
| Local prompt/schema/parser compatibility | Passed for initial generation, comparison assembly and refinement, including both provider response formats. |
| Durable SQL integration | Not rerun; 22 database-dependent cases skipped. |
| Model/editorial evaluation | Not run; no claim of better recall, founder approval or reduced rewriting. |
| Production promotion/deployment | Not established or performed. |

The next integrated Week 2 evaluation must start extraction from the full admitted source batch, then generate angles from the newly validated pool. A fixed-pool angle-only comparison remains a separate controlled experiment. A partial-pool continuation must not be represented as successful complete-week discovery.
