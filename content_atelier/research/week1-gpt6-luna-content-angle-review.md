# Week 1 GPT-6 Luna: saved-moment continuation to content angles

Recorded 8 October 2026, 17:01:23 Asia/Calcutta (11:31:23 UTC result/audit checkpoint). Assistant engineering/editorial review, not Whitney approval.

## What happened and why Call 2 originally did not execute

The angle-generation step was **not rejected**. The ordinary orchestrator calls extraction, validates its whole response, then calls angle generation. When A3's extraction failed two quote-to-anchor checks, an exception stopped execution before any angle request. That fail-fast behavior protected the complete-week acceptance claim but also blocked prompt testing against the seven individually valid records. It was a backend gate, not an OpenRouter refusal or token-cap failure.

The user explicitly authorised either a future two-stage run or reuse of this run's key moments to proceed. We chose reuse to avoid paying for extraction again. The existing explicit partial-pool diagnostic was used **without application or prompt edits**: it revalidated the saved records against the original source bytes/reference map, retained the two rejected records unchanged, and sent only the seven individually valid moments plus their exact contiguous surrounding dialogue to Call 2.

Source parent: `week1-gpt6-luna-generation-only-20261008-a3`, still failed. Continuation: **`week1-gpt6-luna-partial-angle-diagnostic-20261008-a4`**, status partial. Model: exact `openai/gpt-6-luna`, returned provider OpenAI. The angle response finished normally and passed its schema, moment-reference/coverage, source-assertion-prefix and exact canonical-duplicate checks. **Six content-angle candidates were generated and saved.** This is successful Call 2 testing from a partial valid pool, not successful complete-week extraction or publication approval.

No new extraction, quotation capitalization repair, anchor substitution, embedding, history/similarity comparison, recency scoring, database startup, additional LLM judge, content brief or pack was performed. The uncapped settings remain: both output-cap fields omitted, local input-size rejection disabled, embeddings false. Full source/prompt evidence is unchanged. The standard full-week runner's fail-fast behavior was not quietly changed for future runs; partial continuation is explicit, not an automatic fallback.

## The six generated directions

The titles below are the model's actual internal candidate titles, not finished public hooks or captions. Summaries describe their argument and decision; the authoritative full fields remain in candidates.json.

### 1. Position candid work without promising no guidance

Argument: a wedding photographer can distinguish candid coverage from staged imagery without implying couples will be left unguided when they want portrait help. The actual exchange corrected “no posing” because the photographer's candid style coexists with posing support on request.

Reader decision: audit prominent messaging for absolutes that misdescribe the experience. Source: `moment_785018422b4139ca4026de0a`; model base score 83/100. Good specific positioning mechanism, with no claim that the revised wording launched or increased bookings. Keep this service-specific distinction; do not turn it into a universal statement about photographers or guaranteed buyer response.

### 2. Give distinct wedding markets distinct landing-page context

Argument: when target regions have different visual expectations, a market-specific page can make an offer more coherent than asking one page to represent both. The source is a photographer's Orlando/Denver choice and her reported difference in mountain imagery expectations, not a performance experiment.

Reader decision: decide whether regions genuinely need different imagery/context and whether to focus on one market first. Source: `moment_b6124b0d757caa01f992b313`; model base score 80/100. The body is conditional and appropriately bounded. In later public wording, preserve that conditionality: the title must not become a blanket requirement to build a separate page for every location.

### 3. Check buyer meaning before excluding a style keyword

Argument: a phrase that looks stylistically mismatched is not automatically a negative keyword if buyers use style labels imprecisely and some inquiries may still fit. The photographer reported one of roughly four or five people mentioning the phrase became a client; this is a tiny approximate account, not an ad-attributed conversion rate.

Reader decision: review search, inquiry and booking context before excluding a term. Source: `moment_b7b07bed96246fbb1a9d122f`; model base score 88/100. The candidate respects the uncertainty and does not repeat the source's dismissive buyer-language as a public assertion. Any claimed connection between those inquiries and paid search remains unestablished; the candidate's qualifier explicitly preserves that limit.

### 4. Make an all-inclusive venue comparison about scope, not just fees

Argument: show what each option includes and what couples would need to arrange separately rather than presenting unlike rental fees as equivalent offers. The owner described an existing helpful comparison chart and estimated outside costs used in follow-up; making it visible on the ad landing page was suggested, not tested.

Reader decision: check whether comparison materials distinguish included scope, estimated costs and outside planning responsibilities. Source: `moment_1af5cbd5b9123bd11a87aa81`; model base score 93/100. The candidate avoids calculating a price difference from ambiguous spoken figures, does not call existing effort useless, and makes no booking-lift promise. Estimated competitor costs are not independently verified prices.

### 5. Match wedding-venue ad creative to the buyer's next question

Argument: introductory creative, inquiry/tour invitations and warm-audience choice/objection messages can have different jobs. Whitney's labelled source exchange explains the proposed creative/funnel approach for one venue, including possible use of existing Reels; it does not report campaign results.

Reader decision: identify what each audience knows and the next question or action the ad should support before choosing its message. Source: `moment_879f76eea08eb4ff18b3c947`; model base score 85/100. A useful decision-led mechanism, not a mandate to use three ad types or a guarantee of inquiries/tours/bookings. Source speaker labels remain unverified attribution, not identity/public permission.

### 6. Separate setup value from the recurring software commitment

Argument: recurring subscription cost can remain the decisive objection even when setup work and features seem valuable. The source is one small UK photographer's present circumstances and stated objection, including a roughly 20-wedding maximum and low-cost/free existing tools.

Reader decision: assess ongoing cost separately from implementation cost against actual workload, business scale and alternatives. Source: `moment_ec72e945440dc4b558b8c064`; model base score 80/100. The candidate introduces no invented payback, booking requirement, exchange-rate comparison or current-price assertion. Do not convert the prospect's stated lack of fit on this call into proof of her eventual purchase history or a universal affordability threshold.

## Why seven moments produced six angles

No fixed count or one-angle-per-moment mapping was imposed. Call 2 acknowledges all seven moments, then omits the agency's own LeadLock pricing/scope debate (`moment_0970f2b9fe2f51afe37a96f2`) as a standalone direction. Its coverage note explains that this internal commercial discussion, without a final decision/test outcome, is less directly useful to wedding-business readers than the prospect's recurring-cost objection. That is a defensible relevance choice, not a backend four-angle cap or a technical loss of a moment.

The other two extraction proposals were excluded **before** this call because their literal quotation/binding failed. Their unchanged originals and rejection reasons are saved. They were not reinterpreted as weak angles or silently normalized. This limits the evidence pool and is why the continuation remains partial.

## Quality and Whitney-fit assessment

These six directions generally follow the existing corpus-derived policy: specific strategic decisions, capable owners, buyer understanding, truthful trade-offs and mechanisms, with planned/inferred effects separated from reported facts. Reviewed material source claims match the selected dialogue, and the output retains attribution/price/implementation uncertainty rather than inflating results. This is an assistant source review, not a calibrated model comparison or a comprehensive truth certificate.

The six reader decisions are distinguishable within this small pool: service-positioning accuracy, regional page scope, keyword exclusion, included-value comparison, creative's buyer-stage job, and recurring-cost fit. Exact canonical signatures are unique, but semantic near-duplicate/history validation is **not** complete: no vectors, cosine search, recency penalties or final visibility decisions ran. Self-assigned scores of 80–93 are stored diagnostics, not verified quality probabilities or a founder-approved ranking.

Qualifications are retained both from Call 2 and upstream moments. Exact-string deduplication leaves some semantically repeated caveats; this is a future readability issue, not permission to delete material boundaries. Candidate proposals are deliberately more analytical than finished ads. Public hooks, tone polish, permissions, factual clearance and format allocation remain later work.

## Costs: original extraction versus new continuation

| Operation | Reported inference cost (USD) | New spending in this continuation? |
|---|---:|---|
| Original A3 extraction | $0.016626175 | No; already recorded in parent run |
| New A4 angle generation | **$0.009089175** | Yes; one new Call 2 |
| Actual R1 cache-only replay | **$0** | No provider request |

**New cost this turn: $0.009089175** (about 0.91 US cents). Combined original A3 extraction plus A4 angle generation: **$0.02571535** (about 2.57 cents). Earlier failed Luna attempts are not included in this pair total; A1's unavailable billing remains unknown. Credit-purchase fees are excluded. The original extraction was not billed again.

Call 2 usage: **56,446 input**, **4,067 completion**, **60,513 total** tokens. Reasoning: 212 tokens already included in completion; cached input 0; cache-write 56,443. Returned upstream input cost $0.007055675 and completion cost $0.0020335. The complete provider usage/cost details were stored before output validation. The diagnostic run's standard cost summary lists extraction as not attempted, which is correct for new work; continuation_costs.json separately links the original paid parent rather than pretending the failed extraction artifact was a wholly validated cache hit.

## Saved artifacts and reuse verification

- [All six full candidates](<../testing/.data/experiments/default/runs/week1-gpt6-luna-partial-angle-diagnostic-20261008-a4/candidates.json>).
- [The seven accepted source-bound moments](<../testing/.data/experiments/default/runs/week1-gpt6-luna-partial-angle-diagnostic-20261008-a4/moments.json>) and [the two unchanged rejected records](<../testing/.data/experiments/default/runs/week1-gpt6-luna-partial-angle-diagnostic-20261008-a4/rejected_moments.json>).
- [New Call 2 cost summary](<../testing/.data/experiments/default/runs/week1-gpt6-luna-partial-angle-diagnostic-20261008-a4/cost_summary.json>) and [linked original/new costs](<../testing/.data/experiments/default/runs/week1-gpt6-luna-partial-angle-diagnostic-20261008-a4/continuation_costs.json>).
- [Review status](<../testing/.data/experiments/default/runs/week1-gpt6-luna-partial-angle-diagnostic-20261008-a4/review.json>) and [source/replay integrity audit](<../testing/.data/experiments/default/runs/week1-gpt6-luna-partial-angle-diagnostic-20261008-a4/continuation_integrity_audit.json>).

Exact request, raw response, parsed received output, validated angle artifact, usage and cost are saved under fingerprint `055ecd1046e9bac71940449005f28c5481594cf177694e733294227022b9bcd7`, artifact `artifact_d507d4a2a79a4c6d`. No credentials are stored. No original extraction response/manifest was modified or promoted into the whole-response cache.

Actual replay `week1-gpt6-luna-partial-angle-replay-20261008-r1` reproduced all six candidate JSON records with original IDs, generation times and lineage, with zero new service attempts and $0 new cost. The continuation adds exactly **one** request to the pre-dispatch inventory, stage angle_generation; no new extraction. All nine source hash/byte archives match, all candidate vectors/similarity/adjusted scores remain null, and 26 scanned attempt/run JSON files contain zero supplied-key-value hits. Audits are local and incur no provider calls. No database was started.

The existing implementation required no code change for this authorised continuation. The full synthetic regression suite was rerun: **112 tests passed in 24.06 seconds**, with no additional model/payment calls. Original extraction failures remain visible, the successful angle artifact is independently validated/reusable, and no final-angle status was fabricated.

## Execution decision for later runs

For this authorised test, Call 2 now **has executed** using saved valid moments. Continue refining/evaluating these exact saved proposals without re-paying unless prompt/model/input changes genuinely require new work. A future partial-pool policy should explicitly separate globally invalid/mismatched evidence from individually invalid records, preserve rejected records, require a nonempty valid pool, label partial status and track costs. That automatic policy is not implemented merely because this diagnostic succeeded. Whole-week success still requires repairing the generation behavior or deliberately agreeing a different acceptance contract, not hiding extraction errors.
