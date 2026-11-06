# Week 1 GPT-6 Luna comparison: execution, costs and evidence review

Recorded 8 October 2026, 16:23:43 Asia/Calcutta (10:53:43 UTC checkpoint). Author: assistant engineering/editorial review, not Whitney approval. Runtime outputs are private local records; no content was published.

## Outcome

Both LLM stages are configured for exact `openai/gpt-6-luna`, and per-stage cost tracking is implemented. The paid comparison did **not** complete both stages: Call 1 returned 14 proposed moments but failed strict validation. Offline review finds 11 individually source-valid records, two invalid quote bindings and one invalid enum. The pipeline stopped before Call 2; **zero Luna content angles and zero embeddings were generated**. No failed response was repaired, accepted into the validated cache or quietly replaced by Apodex output.

This is a useful extraction/model-calibration result, not a successful weekly pipeline or a verdict that Luna's angle generation is better. A second-stage model-quality comparison is still untested.

## Exact execution and boundaries

The user requested the same pipeline with a funded OpenRouter key, exact Luna model, both stage costs and saved output. Existing generation-only authority remains: no embeddings, similarity, recency ranking, database startup, Slack, briefs/packs or public use. No credits were purchased and no different model was substituted.

The source remains all nine Week 1 exports and 3,238 turns in one physical extraction request. Original names, dialogue, greetings/endings, timing and order remain present. Missing Zoom meeting metadata remains null; folder names do not establish June occurrence dates. Production Fathom integration remains later work.

The corpus-grounded v2 system templates/editorial policy, active weekly v3 extraction supplement, JSON-object response contract and strict local validators are unchanged. The profile identifier `2026-10-08.apodex-weekly-generation.v3` is historical naming of the contract, not the requested/returned model: both actual model fields are Luna. The same Call 2 prompt templates are configured but were not sent in this test.

OpenAI Docs skill instructions informed exact-model documentation/compatibility checking. The [official Luna page](https://developers.openai.com/api/docs/models/gpt-6-luna) and [actual OpenRouter route](https://openrouter.ai/openai/gpt-6-luna) were checked. The route advertises a 1,050,000-token context and supported reasoning/JSON parameters but does not advertise temperature, so the adapter omits temperature for Luna only. Other model request bodies retain their historical settings. `usage:{include:true}` requests returned accounting; OpenRouter documents usage/cost in its [API overview](https://openrouter.ai/docs/api_reference/overview).

### Attempts

| Run | Requested output reserve | Actual result | Call 2 |
|---|---:|---|---|
| `week1-gpt6-luna-generation-only-20261008-a1` | 65,536 | HTTP 402: account could reserve only 33,316 output tokens; no model output/usage | Not attempted |
| `week1-gpt6-luna-generation-only-20261008-a2` | 16,384 | Single announced bounded retry; 14 proposals; normal stop, then schema/source rejection | Not attempted |

Only the reserve changed between these attempts. The smaller reserve did not truncate the input. The response consumed 6,631 completion tokens and returned `finish_reason:stop`; its rejection is not an output-length failure. Reasoning effort stayed low, response format JSON-object, timeout 900 seconds. Default live mode remains false. The retry was announced explicitly, not an automatic retry loop. No further paid call was made after rejection.

Changing model, request parameters and model-specific temperature support means this is a controlled source/prompt comparison, not a perfectly isolated identical-sampling experiment. More useful proposals or a better-looking validation fraction do not establish statistical model superiority.

## Cost accounting: actual, not estimated

| Attempt / stage | Native input tokens | Native completion tokens | Reported new inference cost (USD) | Accounting interpretation |
|---|---:|---:|---:|---|
| A1 Call 1 | Unavailable | Unavailable | Unknown | Dispatched HTTP 402 supplied no usage; do not infer zero |
| A1 Call 2 | 0 | 0 | $0 | Not attempted |
| A2 Call 1 | 116,370 | 6,631 | **$0.017861675** | Billed returned response, even though content failed |
| A2 Call 2 | 0 | 0 | **$0** | Not attempted |

A2's known run total is **$0.017861675**, approximately 1.79 US cents. Across both attempts the known subtotal is the same, but a fully reconciled total is **unknown** because A1 returned no billing. Credit-purchase/transaction fees are not included. This distinction is preserved in A1's ledger and must not disappear when reporting only the retry.

Actual A2 provider is OpenAI; total usage is 123,001 tokens. Returned breakdown:

- Upstream input charge: $0.014546175.
- Upstream completion charge: $0.0033155.
- Cached input tokens: 0; reported cache-write tokens: 116,367.
- Reasoning tokens: 259, already included in the 6,631 completion tokens, not an additional charge to add again.

Use the provider's returned amounts rather than recalculating the bill from a standard input/output price card and overlooking route/cache-write accounting. Raw usage and the complete provider breakdown are retained for audit.

### Implemented accounting behavior

`backend_pipeline/costs.py` and the orchestrator record request identity/stage/model, dispatch status, returned generation/provider IDs, native usage, reported USD cost, validation outcome and artifact references. Records begin before dispatch and are updated immediately after saving the raw response, before parsing/source validation can fail. A paid failure remains visible as a paid failure. Null/missing/invalid cost is unknown, real zero is retained, and a never-dispatched request is not charged by this accounting.

Per-attempt `cost.json` and per-run `costs/<artifact-id>.json` are machine-readable records. `cost_summary.json` and `.md` include both stages, known subtotals, unknown totals and replay distinctions. A validated compatible cache hit retains original lineage/usage/cost but adds zero new cost. Original paid cost is never added again as replay spending. Raw failures are preserved for diagnosis, not silently promoted into reusable validated results.

There is no new budget enforcement, request lease, multi-writer transaction or exactly-once external billing claim. A process failure between dispatch and receipt remains billing-unknown. Saving costs is not a substitute for agreeing future experiment ceilings/retry policies.

## Capacity and transcript integrity

Installed tiktoken has no established `gpt-6-luna` mapping. The local preflight therefore does **not** pretend to provide native Luna token counts or reuse Apodex/GPT-OSS counts. It uses a clearly labelled conservative UTF-8 text-byte allowance, verifies the checksum of public exact-model route metadata, checks required parameters/prompt/output limits and reserves provider framing plus output capacity.

A2 preflight records 374,700 message bytes plus 22 format bytes, a 37,473 framing allowance, 16,384 output reserve and 621,421 allowance headroom against the saved 1,050,000 context / 922,000 prompt limit. Those allowances are not actual hosted-token measurements. The real response's **116,370 input tokens** confirms this exact supplied payload was processed within the route's capacity. It does not establish comprehension of every turn or future weeks' fit.

No character guard was increased, source split, source text dropped or summary substituted. The legacy-flat character safeguard remains unchanged; active compact-weekly uses the model-specific preflight. Original-byte/source archive checks are separately saved in the run integrity report.

## Extraction audit

The whole response fails first at proposal 11's enum: `buyer tension` is not allowed; the contract permits `tension`. **It was not silently mapped.** Offline per-record validation then applies the same strict schema, meeting inventory, exact anchors/quote and contiguous context checks independently, without sending another LLM request or using accepted records for Call 2.

| Proposal | Topic / reader decision | Individual strict result | Editorial observation, not approval |
|---|---|---|---|
| `m1-message-fit` | Candid positioning without falsely promising no posing support | Pass | Useful specific positioning trade-off; no performance uplift established |
| `m1-geographic-fit` | Separate work one might accept from work worth paying to attract | Pass | Grounded capacity/preference decision; no universal geographic exclusion rule |
| `m3-market-specific-pages` | Orlando vs Colorado visual/market fit | Pass | Useful context-specific page choice, not proof separate pages always win |
| `m3-ambiguous-style-term` | Monitor ambiguous buyer vocabulary before exclusion | Pass | Small reported inquiry sample, not an ad conversion rate; soften buyer-blaming language in future expression |
| `m4-service-clarity` | Explain the full service before an inquiry form | Pass | The 20% form-visit observation is within context and qualified; cause remains a team hypothesis |
| `m5-conversion-strategy-test` | Bounded bidding-strategy experiment | **Fail: quote anchor** | Exact quotation exists at `m5.t0264`, but that cue is absent from declared anchors; business-category/period claims also need scrutiny |
| `m5-destination-search-fit` | Evaluate relevant inquiries/searches, not just a promotional campaign's apparent price | Pass | Proposed one-week review, not a completed campaign outcome |
| `m7-nurture-customization` | Core system vs optional client-specific workflows | Pass | Distinguishes proposed onboarding/feature work from implemented universal policy |
| `m7-scope-and-pricing` | Scope clarity vs up-front package sticker shock | **Fail: nonliteral quote** | Quotation crosses spoken cue boundaries; no single source cue contains that exact text |
| `m7-text-follow-up` | Invite feedback and orient couples before tours | Pass | Reported staff observation plus proposed pre-tour message; not measured attendance/response lift |
| `m8-inclusive-value` | Compare included scope, not unlike headline prices | **Fail: enum** | Quote is real, but `buyer tension` violates schema; chart interpretation still needs editorial correction |
| `m8-funnel-specific-creative` | Different creative jobs for different buyer stages | Pass | Strategy explanation, not proof of live campaign success |
| `m9-fragmented-lead-sources` | CRM ownership vs reliable capture across channels | Pass | Specific operational tension; integrations and booking improvement remain unverified |
| `m9-buyer-fit-and-ongoing-cost` | Recurring cost vs business scale and existing tools | Pass | Spoken historical price/volume context preserved, no invented payback or current-offer assertion |

“Pass” means individual mechanical source/schema checks passed in an offline review. It is **not** full-batch acceptance, semantic fact-check certification, public permission, founder endorsement or a selected visible angle. The 11 valid records remain diagnostic observations; `moments.json` and `candidates.json` were not created as successful outputs.

### Additional limits found outside the first schema exception

The response exactly acknowledges all nine delivered meeting bounds/counts. Nevertheless, a coverage note cites `m6.t1106–m6.t1252`; m6 ends at `m6.t0283`. These invented references reveal a source-addressing problem even though the inventory acknowledgement is correct. Current strict anchor/context checks reject invalid moment references; `coverage_notes` is free text and its inline IDs are **not yet mechanically validated**. The offline note audit exposes this gap without claiming a new validator was implemented. Correct acknowledgement is not evidence of comprehensive reading.

The bidding-test proposal's qualifications say the client category is unestablished, while its coverage note identifies the earlier discussion as a waxing business. At minimum, the response's own category handling is inconsistent; do not use it as a wedding-business result. The all-inclusive chart summary calls the chart too simplified to communicate value, while the selected owner dialogue says it is helpful and could look better visually. That stronger content-value criticism is not established by the quoted passage. These need editorial review even after mechanical repair.

Some propositions still elevate plausible mechanisms: the pre-tour message may reduce arrival uncertainty, but that is not an observed outcome. Preserve the difference between a reasoned suggestion and a delivered result in any eventual angle. Conversely, the landing-page and recurring-price moments retain more material context than the earlier partial Apodex candidates, including historical prices within the actual selected interval. This is a useful review observation, not a quantitative model-quality ranking.

## Comparison with the earlier Apodex test

Apodex's latest full-week v3 extraction proposed seven moments, five individually valid; the full run failed. A separately labelled partial-pool diagnostic then produced five unapproved angles. Luna proposed 14 moments, 11 individually valid, but its full run also failed and **no Luna angle call occurred**. They are different candidate sets from the same week, not paired identical outputs or a fixed-count requirement. More moments alone is not the objective: useful, distinct and grounded choices are.

The existing Apodex angles remain saved and are not overwritten, substituted or labelled Luna. Existing successful Apodex cache-only replay remains historical evidence. Actual Luna replay was not performed because there is no validated extraction cache entry; synthetic replay/cost tests do verify zero-new-cost accounting.

## Storage and reuse

Authoritative private records:

- [A2 run directory and cost JSON](<../testing/.data/experiments/default/runs/week1-gpt6-luna-generation-only-20261008-a2/cost_summary.json>).
- [A2 human-readable costs](<../testing/.data/experiments/default/runs/week1-gpt6-luna-generation-only-20261008-a2/cost_summary.md>).
- [Original parsed 14-moment response](<../testing/.data/service_calls/b1c7631780798d3b4e528184b91d41aa73e62d0635e866440260928073c186df/attempts/artifact_d17e64eb31d64be3/output.received.json>).
- [Offline per-record audit](<../testing/.data/experiments/default/runs/week1-gpt6-luna-generation-only-20261008-a2/offline_moment_audit.json>).
- [Offline coverage-note audit](<../testing/.data/experiments/default/runs/week1-gpt6-luna-generation-only-20261008-a2/offline_coverage_note_audit.json>).
- [A1 rejection accounting](<../testing/.data/experiments/default/runs/week1-gpt6-luna-generation-only-20261008-a1/cost_summary.json>).

The attempt also retains exact safe request, preflight, raw response, failed stage artifact and billing. Its run retains source-packet pointer and failed manifest. Raw provider fields remain private for audit; the review does not reproduce account identifiers, credentials or provider reasoning. Failed received content can be inspected again without payment, but reusing it as accepted pipeline input is a separate deliberate correction/partial-diagnostic decision, not ordinary validated replay.

The [final integrity audit](<../testing/.data/experiments/default/runs/week1-gpt6-luna-generation-only-20261008-a2/final_integrity_audit.json>) confirms all nine original SHA-256 hashes and byte archives match, all 3,238 turns remain present, and all eight current prompt hashes occur in the unchanged template snapshots. A 49-file service/run JSON scan found zero supplied-credential-value hits. Both runs remain failed, with zero angle attempts, no successful moments/candidates files and no embeddings directory. These local audits made zero additional provider requests.

## Verification and next decision

**107 offline tests passed in 22.56 seconds**, Ruff lint and changed-file format checks passed, compilation passed. Eighteen new synthetic cases cover Luna body/preflight compatibility, missing/invalid/real-zero cost, timeout/not-sent states, rejected-output billing, two-stage sums and replay lineage/zero-new-charge behavior. An initial test run failed fixture setup because the sandbox temp directory could not be created; using a fresh explicit workspace temp directory resolved it. This is an environment issue, not a hidden product-test failure.

No further paid run should be mistaken for already approved automatic repair. Recommended next step: deliberately strengthen source-copy/enum instructions and coverage-note reference validation, consider provider-enforced strict schema on the verified Luna route as a **new test**, then run extraction again with all dialogue retained and an agreed spending limit. A strict schema could prevent the enum error, but it cannot guarantee exact quotations or correct editorial interpretation.

Alternative, only if the user chooses: an explicitly partial-pool Call 2 diagnostic using the 11 unchanged individually valid records, leaving the original failure intact. This skips the three rejected records, changes the evidence pool and is **not** a complete weekly comparison. It would cost a new angle request. No extra LLM judge, automatic quote repair, inference loop or embedding is introduced by this recommendation.

The current turn stops with saved costs/output and a documented failure. Successful two-stage generation, calibrated Whitney-quality angles and embedding approval remain outstanding.
