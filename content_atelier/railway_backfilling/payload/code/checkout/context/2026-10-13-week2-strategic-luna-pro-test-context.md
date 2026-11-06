# Week 2 strategic discovery test — exact GPT-6 Luna Pro

Client date: 13 October 2026, Asia/Calcutta. Jainil explicitly requested both revised LLM stages on Week 2 using `openai/gpt-6-luna-pro`. After automatic approval review required destination-specific authorization, he explicitly approved sending all eleven Week 2 transcripts and then their extracted moments/context to OpenRouter for both paid calls. That permission was received before any inference.

## Execution and actual outcome

- Exact route was verified through OpenRouter's public model endpoint. It advertises response formatting/reasoning and does not advertise temperature. The provider adapter now omits temperature and requests usage for this exact Pro ID, with regression coverage alongside the existing Luna and Sol routes.
- Both requested stages returned exact `openai/gpt-6-luna-pro`, provider OpenAI, finish reason `stop`.
- Models were overridden for this test only. The `.env` defaults were not changed. Existing uncapped local input/output settings, JSON-object contract validation and low reasoning effort were retained; embeddings stayed disabled.
- All eleven files / 5,218 turns were supplied to extraction under `2026-10-13.wia-strategic-discovery.v1`.
- Parent `week2-luna-pro-strategic-20261013-a1` returned seven proposed moments but failed exact quote binding. Five passed individual validation; two rejected records remain unmodified. Parent status remains failed.
- The second approved call was deliberately completed through the explicit partial-pool calibration runner, without re-extraction or quote/anchor repair. Child `week2-luna-pro-strategic-angles-20261013-a2` produced four public candidates and one internal sales insight, status partial.
- Real cache-only replay `week2-luna-pro-strategic-angles-20261013-r1` reproduced all four candidate records, IDs and original lineage. No provider dispatch and $0 new cost.

This is successful angle generation from a valid partial pool, not successful whole-week extraction or a full end-to-end acceptance result.

## Saved directions

All four are WARM: buying research versus reviews (thought shift), venue tour follow-up that fits buyer timing and venue capacity (behind the scenes), whole-path campaign diagnosis (campaign breakdown), and chat-widget information/human-handoff evaluation (process). The prospect's learning preference, budget and proposed audit remain internal sales intelligence. Every reader decision is null. No multi-treatment source family, ATTRACT candidate or CONVERT candidate emerged.

The first two provide particularly clear demonstrations of strategic thinking/collaboration in this small pool. The corporate-campaign example must retain its actual context and justify relevance to wedding businesses. The chat pilot is proposed work, not a confirmed current client service. No founder approval or demonstrated performance should be inferred. All four pipeline base scores tie at 80 and remain model self-assessments.

## Costs and failures

Extraction reported $0.09423364, 540,032 input / 11,801 completion tokens. Angle generation reported $0.05797840, 361,190 input / 9,042 completion tokens. Combined new inference cost: **$0.15221204**. Returned billing includes cache effects; reasoning is already in completion usage. Purchase fees excluded.

Rejected quotation strings were `a pretty drastic decline` and `I have my own systems all built out`. Neither was found literally in its declared anchors or by exact same-meeting search. The latter omitted qualifying words visible in the source. Do not normalize or promote the failed records into a validated artifact to create an artificial success.

The technical next issue is literal-quote fidelity. Editorial next issues are founder usefulness, attention worthiness, meaningful cross-purpose exploration and recall of other worthwhile source passages. This run changes both model and pool relative to the earlier Week 2 test; do not call it a controlled prompt-only comparison.

## Artifacts and reproducibility

- Readable review: `research/week2-luna-pro-strategic-test-review-2026-10-13.md`, also `review.md` in the angle run.
- Valid strategic records: `testing/.data/experiments/default/runs/week2-luna-pro-strategic-angles-20261013-a2/opportunities.json`.
- Internal insight: `internal_insights.json` in that run. Source moments, rejected records, raw receipts, exact requests and cost summaries are preserved.
- Route, request preview, source manifest, individual validation, quote diagnosis and final audit: `backend/.storage-artifacts/verification/strategic-week2-luna-pro/`.
- Final audit verified all original source archive hashes, identical replay, original failed-parent status and zero supplied API-key-value hits in 40 scanned JSON artifacts.
- `scripts/run_week2_luna_pro.py` defaults to replay. Any new paid execution requires explicit `--mode live`; use fresh run IDs and preserve actual failures. The saved partial-pool replay needs `--continue-from-run week2-luna-pro-strategic-20261013-a1`.

No embedding, similarity ranking, third LLM judge, content brief or publication was performed.
