# Strategic content discovery revision

Release: `2026-10-13.wia-strategic-discovery.v1`, 13 October 2026, Asia/Calcutta.

Implemented from Whitney's Week 1 correction and the additional analyst feedback captured in [the feedback analysis](../../research/2026-10-13-whitney-week1-feedback-analysis.md). The analyst's examples calibrate the level of strategic interpretation; they do not establish transcript facts or approval of final copy.

## What changed

The two existing LLM stages remain. Their objective changes from extracting decision-oriented lessons to discovering opportunities that serve WIA's marketing and demonstrate its judgment, work or value. No additional strategy-judge call, model change, embedding reconnection or live generation is part of this release.

Both stages receive the same versioned `wia_strategy.md`, including the ATTRACT/WARM/CONVERT framework, content types, business objectives, five discovery lenses, voice principles and the six feedback contrasts. The source itself remains untrusted evidence. The strategy supplies editorial judgment and does not substitute for factual case support.

### Stage 1: strategic moment identification

The extractor now considers audience insights, expertise, service value, broader principles and attention worthiness. It preserves the interaction: setup, team questions, rationale, client contribution and any outcome or unresolved issue. A measured result or practical reader decision is unnecessary for a useful process moment.

The factual `proposition` stays separate from typed `discovery` metadata:

- `lenses`: applicable strategic lenses;
- `destination`: public opportunity, internal intelligence or further research;
- `wia_contribution`: the concrete contribution, or null;
- `attention_reason`: why the material matters;
- `research_questions`: missing details to investigate.

Source IDs, exact quotations, contiguous same-meeting context and delivery acknowledgements retain their strict validation. No automatic quote repair, invented speaker identity or partial-week success is introduced. Existing and lossless weekly prompt paths both use the revised strategy; preparation requests also use the current response schema.

### Stage 2: content opportunity discovery

The angle generator reconsiders the provisional moment interpretation against its full context. It creates the client's seven editorial components: opportunity, purpose/type, intended audience, core perspective, tension, expertise in action and source evidence. It also records the strategic rationale, selection reason, supported service relevance and evidence readiness.

`core_perspective` replaces mandatory separate Argument and Take. `reader_decision` is explicitly nullable. No exact action, CTA or format is needed for discovery. Audience selection follows the transferable perspective, rather than copying the recorded participant.

`internal_insights` retains useful audience or sales intelligence separately. A public hypothesis with a missing central detail remains `research_required` and must name a research question. It cannot be automatically selected as ready or approved for development. LeadLock praise without feature evidence therefore supports investigation, not an invented benefit.

One conversation can produce several substantive treatments across the purposes. Purpose labels, titles and formats alone do not establish distinctness. The canonical signature represents opportunity, audience, tension, core perspective and WIA contribution; it ignores titles and purpose/type labels. A stable source-family ID groups candidates from the same set of source conversations without treating the family as a single required angle.

### Evaluation and persistence

The new rubric contains grounding plus the four requested dimensions: strategic fit, distinctiveness, audience resonance and source strength. These remain provisional model assessments. The temporary base score is twenty times the lowest of those five dimensions. This conservative rule prevents strong factual grounding from compensating for weak strategic fit. It is not founder-calibrated weighting or an engagement prediction; score thresholds need review against actual new judgments.

Historical `Quality` objects retain their original weighted calculation. Old response contracts remain available for reading/validation of old artifacts; active requests strictly validate the new contracts and do not silently fill missing strategic fields.

New file-backed runs save:

- `moments.json`, including discovery metadata;
- `opportunities.json`, the authoritative flat strategic records and source-family IDs;
- `internal_insights.json`, separate non-public learning;
- `candidates.json`, typed pipeline objects preserving the strategic record;
- `review.json`, with research-required candidates and internal-insight counts;
- the original request, received response, billing and lineage artifacts.

SQL generation persists the strategic record and source-family ID inside the existing `content_body` JSON, discovery inside `moment_body`, and internal insights in the stage result/artifact. No database migration or historical-row rewrite is required. Historical context and the existing refinement stage receive the current strategy and record instructions.

Legacy `argument`, `take` and `mechanism` remain compatibility views for existing storage/brief consumers. For new candidates they are derived from the single core perspective and actual expertise; they are not independently requested from the LLM. New editorial interpretation should use the strategic record. Gate 1 edits update that record and its views together; strategic candidates require the new quality rubric. Briefs can preserve a null reader decision.

Source qualifications and handling risks are merged into both the strategic review record and the pipeline object. Historical generated files are not relabeled or modified. The old eight prompt templates are preserved in `prompt_templates/archive/2026-10-08-pre-strategy-revision/`. The profile and request/validation identity change, so revised requests cannot reuse an old response as though it satisfied this feedback. Old artifacts remain readable; reconstructing an old exact request from the current templates will produce a cache miss or profile rejection. Historical replay documentation must be interpreted with its original profile.

## Review and offline preparation

The exact template snapshot is [prompts-strategic-v1.md](../prompts-strategic-v1.md). Runtime templates and schemas remain the authority. Regenerate the snapshot and prepare full Week 1 request bodies locally:

```powershell
python scripts/prepare_strategic_revision.py --week 1
```

Run from `content_atelier/backend/`. The command reads the configured model settings and source files, writes review artifacts and checks the original source revisions. It never constructs a live provider or dispatches inference. Request bodies contain no credentials.

The Week 1 extraction preview includes nine exports and 3,238 source turns. The separate angle preview uses the seven validated historical moments and their original surrounding dialogue, not newly extracted strategic moments. It is useful for assessing the change of interpretation on fixed evidence; it cannot demonstrate improved whole-week discovery.

Previews and typed schema snapshots are in `.storage-artifacts/verification/strategic-discovery-v1/`. Their `readiness.json` records zero new inference and embedding requests, unchanged models and the source verification result.

## Verification and practical limits

The offline suite exercises source binding, current/legacy parsing, schema completeness, caching, reuse, optional decisions, shared-source treatments, non-public insights, research states and the strategy-score safeguard. Dedicated feedback tests use synthetic, manually specified outputs. They establish behavior of the contracts and pipeline, not how well a live LLM will discover ideas.

Release verification: **141 tests passed, 65 database-dependent tests skipped** in 25.24 seconds. Static undefined/unused-name checks passed for the changed implementation and feedback tests; Python compilation passed. Eleven dedicated strategic-discovery checks include synchronized Gate 1 edits and rejection of research-required approval. The Week 1 preview verified all original raw source revisions and retained the seven-moment partial-pool label.

PostgreSQL integration requires an isolated `atelier_test` database. No test database was configured and the Docker daemon was unavailable during this revision, so those integration checks were skipped. No production or client database was used as a substitute. SQL persistence, editing and approval changes still need those integration checks before deployment.

The next editorial evaluation should compare new output on the fixed Week 1 evidence, then evaluate extraction across the entire week and generalization to Week 2. Whitney should judge strategic usefulness, attention worthiness and how much central reframing she still needs to do. Score improvement or valid JSON alone does not establish that result. Her examples are preference cases, not permanent title formulas or a six-topic generation quota.

Prompt construction follows clear instructions, relevant context and differentiated examples as described in [OpenAI's prompt-engineering guidance](https://developers.openai.com/api/docs/guides/prompt-engineering). No model migration or model-weight fine-tuning was performed.
