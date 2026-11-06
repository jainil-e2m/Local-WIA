# Week 1 GPT-6 Luna: uncapped retry A3

Recorded 8 October 2026, using Asia/Calcutta client time. Run: `week1-gpt6-luna-generation-only-20261008-a3`. Engineering/editorial observations below are not Whitney approval.

## Outcome

The newly configured key authenticated and the full weekly extraction returned normally from exact `openai/gpt-6-luna`, provider OpenAI. **No application input/output token cap was applied.** Call 1 proposed nine moments, seven individually source-valid in offline review. The full response failed two exact quote-to-anchor checks, so Call 2 was not attempted. No Luna angles, embeddings or vector ranking were generated. The run remains failed rather than being quietly accepted as a partial success.

The source remains nine original exports and 3,238 turns, sent in one physical extraction request. All source bytes/hash archives match, every source speaker name/dialogue/time/order remains present, and all eight prompt-template hashes still match their ledger snapshots. No source was split, summarized, truncated or edited. Missing Zoom occurrence metadata remains unknown.

## User-requested cap removal

The user supplied a working new key and explicitly requested no input/output token limits for this retry. Actual/template environment now uses:

```dotenv
OPENROUTER_MOMENTS_MODEL=openai/gpt-6-luna
OPENROUTER_ANGLES_MODEL=openai/gpt-6-luna
CONTENT_ATELIER_LLM_COMPLETION_TOKENS=
CONTENT_ATELIER_LLM_INPUT_LIMITS_ENABLED=false
CONTENT_ATELIER_EMBEDDINGS_ENABLED=false
```

Blank completion tokens resolves to None. The safe stored request contains **neither `max_tokens` nor `max_completion_tokens`**, and no substitute output reserve was added. The explicit input flag bypasses both the compact-week conservative byte-budget rejection and the legacy character rejection. Its `preflight.json` is now diagnostics only: 377,352 serialized request characters, 374,700 message-text bytes, no local input limit enforcement, null requested output cap and no input truncation. The retained legacy safeguard is inactive in this test; setting it does not impose a cap while checks are disabled.

This override does not remove source/schema/quote/context validation, relax approval requirements or reconnect embeddings. It is also not “infinite tokens”: omitted output limits defer to external defaults. [OpenRouter documents the cap fields as optional](https://openrouter.ai/docs/api_reference/parameters); [OpenAI documents Luna's finite context/output capacity](https://developers.openai.com/api/docs/models/gpt-6-luna). Provider defaults, account credit/quotas and the existing 900-second response timeout still apply. The OpenAI Docs skill informed verification of this distinction. No automatic reserve reduction, credit purchase, model substitution or additional retry occurred.

Existing constrained-size checks remain available behind the explicit setting for later constrained experiments; the Settings class default is true. In this actual test it is false for **both** stages. JSON-object format, full schema at system authority, low reasoning and prompts remain unchanged for comparability. A different response format/strict-provider-schema or prompt refinement would be a separate deliberate test, not something changed silently here.

## Returned usage and costs

| Stage | Result | Input tokens | Completion tokens | Reported new cost (USD) |
|---|---|---:|---:|---:|
| Call 1 — extraction | Nine proposals; full response rejected | 116,370 | 4,160 | **$0.016626175** |
| Call 2 — angles | Not attempted | 0 | 0 | **$0** |

A3 reported total: **$0.016626175**, approximately 1.66 US cents. Total tokens: 120,530; reasoning tokens: 231 already included in completion. Cached input: 0, cache-write tokens: 116,367. Returned upstream input charge is $0.014546175 and completion charge $0.00208. Actual returned usage/cost is retained before validation, so content rejection does not erase the paid call. Credit-purchase fees are excluded.

The response finished with `finish_reason:stop`, not `length`. The shorter output than A2 does not demonstrate a hidden application cap: the request lacks both output fields and the response stopped normally. Omission cannot establish an infinite or specific provider-default budget. The earlier 16,384-token A2 cap also exceeded that response's 6,631-token completion; the A2 failure was not truncation either. Quote copying/binding, not demonstrated token pressure or authentication, is the present blocker.

Earlier A2's reported cost remains $0.017861675 in its own preserved run; A1's HTTP 402 still has unknown billing. The known reported subtotal across A2+A3 is $0.03448785, but a fully reconciled all-attempt total remains unknown because A1 returned no usage. Do not label historical Apodex output as Luna or assume a key change alters stored request compatibility; credentials are deliberately excluded from artifact fingerprints.

## Individual audit and editorial meaning

| Proposal | Reader-level direction | Individual strict check |
|---|---|---|
| `m1-positioning-without-overpromising` | Candid positioning without promising no portrait guidance | Pass |
| `m3-focus-one-market-page` | Coherent market-specific page before expansion | Pass |
| `m3-ambiguous-style-searches` | Assess inquiry evidence before excluding an ambiguous style term | Pass |
| `m5-pmax-free-credit-tradeoff` | Assess campaign relevance even when using promotional credit | **Fail: capitalization changed in quote** |
| `m7-venue-follow-up-customization` | Shared core vs client-specific optional workflows | **Fail: quoted cue omitted from anchors** |
| `m7-pricing-scope-choice` | Scope/pricing trade-off and testing, not assumed buyer acceptance | Pass |
| `m8-all-inclusive-value-comparison` | Compare included scope rather than unlike headline fees | Pass |
| `m8-different-funnel-objectives` | Different buyer stages need different creative jobs | Pass |
| `m9-ongoing-cost-objection` | Recurring expense can matter more than accepted setup cost | Pass |

The m5 quotation is returned as `it's definitely not getting us any leads`; the declared actual source `m5.t0422` says `It's definitely not getting us any leads`. The statement is substantively supported, but it does not satisfy the agreed exact-copy contract. It was **not** recased automatically. The m7 quote `everyone's not consistently using them` is real at `m7.t0119`, inside the selected context, but the returned anchors list only t0097, t0098, t0121 and t0124. No source ID was silently added. These failures are quotation representation/binding defects, not evidence that both underlying discussions were invented.

Seven passes mean per-record mechanical source/schema validation only. They do not mean complete weekly acceptance, semantic certainty, founder approval or public permission. The offline audit neither changed original response content nor sent the valid subset to Call 2. No successful `moments.json`/`candidates.json` was written.

The proposals retain useful bounded choices for Whitney's strategic approach: honest positioning, market coherence, optional implementation rather than a one-size-fits-all promise, and ongoing-cost fit. The all-inclusive proposal does not calculate a price difference from ambiguous spoken figures, and the pricing-scope proposal explicitly notes it concerns agency service decisions rather than automatically treating them as wedding-vendor sales proof. These are useful boundaries, not a judgement of unseen Luna angle quality. Nine vs A2's fourteen moments is not a completeness or quality score; exhaustive semantic coverage still requires human calibration. The m5 context spans 327 turns, so it retains the relevant discussion but is not obviously the smallest sufficient context interval.

All nine meeting inventories match. A regex audit of IDs actually cited in coverage notes finds no nonexistent IDs this time; that is a local syntactic observation, not proof each exclusion was sound or all useful moments were found. It does not implement the proposed future production coverage-note validator.

## Saved output and verification

- [Per-stage cost JSON](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/testing/.data/experiments/default/runs/week1-gpt6-luna-generation-only-20261008-a3/cost_summary.json>) and [cost Markdown](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/testing/.data/experiments/default/runs/week1-gpt6-luna-generation-only-20261008-a3/cost_summary.md>).
- [Original nine proposed moments](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/testing/.data/service_calls/4deaf2e32a987abdb7ba881dbb86bcca647d41087e057b2ed6648e78167fc9ba/attempts/artifact_fa24c3cf880e4596/output.received.json>).
- [Uncapped-request diagnostics](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/testing/.data/service_calls/4deaf2e32a987abdb7ba881dbb86bcca647d41087e057b2ed6648e78167fc9ba/attempts/artifact_fa24c3cf880e4596/preflight.json>).
- [Offline moment audit](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/testing/.data/experiments/default/runs/week1-gpt6-luna-generation-only-20261008-a3/offline_moment_audit.json>) and [integrity audit](<C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/testing/.data/experiments/default/runs/week1-gpt6-luna-generation-only-20261008-a3/final_integrity_audit.json>).

Exact safe request, raw provider response, failed stage artifact and cost record remain alongside these files. Earlier attempts are unchanged. A 13-file attempt/run JSON scan found zero supplied-credential-value hits; no keys were displayed or included in documentation. No database was started and no embedding call or vector was generated.

**112 offline tests passed in 25.45 seconds**; Ruff lint, changed-file format checks, compilation and Git whitespace checks pass. Five new synthetic tests cover omitted output fields, bypass of both input-gate modes, unchanged quote rejection/billing and environment configuration. These tests use mocks, not additional paid calls. Offline audits also made zero provider requests. The active live session 61458 finished and is closed.

The requested cap removal and retry are complete. The two-stage pipeline is still blocked at exact quotation/source binding. A deliberate prompt/contract refinement or explicitly labelled partial-pool diagnostic would be a separate next decision. Neither further payment nor relaxed validation is inferred from this failed retry.
