# ChatGPT export: full analysis and tests (18 October 2026)

**What this is.** The one-time analysis of Whitney Hodges' ChatGPT export (exported 14 October 2026). It is the input to the plan's one-time seed (plan section 4.12, R52, L.B2). Findings are summarised in section 1.8 of `backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md`.

**Status.** Committed after WIA answered decision D11 (permission for a one-time use, 18 October 2026). `storage_cli context-seed` (plan L.B2) loads `kb-candidates/` into the context store once, as candidates for review; after that, nothing from ChatGPT is accepted (R52).

- The drafts contain WIA's internal prices, marked "Internal".
- The test data contains Whitney's marketing copy.

The raw export is not here, and must never be committed.

## Contents

| Path | What it is |
| --- | --- |
| `synthesis.md` | Cross-cutting findings from all 309 business conversations, the attachments and the library files |
| `kb-candidates/` | Draft knowledge-base documents, each item cited to a conversation and date: rejection rules, offer facts, roster corrections, format guide, CTA catalogue, process catalogue, audience language, beliefs, case-study method, published-content log, content workflow, exemplar bank. All have status `draft`; none is confirmed by WIA |
| `data/t1_pairs.jsonl` | 38 preference pairs (an AI or team draft, and the version Whitney wrote or approved). WIA marketing copy only; none flagged as private client information |
| `data/t2_tasks.jsonl` | 10 real requests Whitney made of ChatGPT, with ChatGPT's first draft and her approved version |
| `data/pack_rules.md`, `data/pack_exemplars.jsonl` | The "how Whitney edits" pack used in the tests. It is independent of the test items: no shared conversation, and at most 0.35 similarity to any test text |
| `runner.py` | OpenRouter runner. It has a USD 3.70 cap, the "no data collection" provider preference, a ledger and saved responses. It never prints the key |
| `t1_judge.py` | T1: can a model judge predict which version Whitney chose? |
| `t2_write.py`, `t2_judge.py` | T2: does the export pack make first drafts closer to what Whitney approves? |
| `lint.py` | The style lint. It separates absolute bans from flags (plan E.B10) |
| `ledger.jsonl`, `runs/`, `results/` | Every call, its cost and its output |

## Method

1. **Inventory.** All 349 conversations were inventoried, and 40 personal ones were excluded.
2. **Reading.** The 309 business conversations were split into 12 chunks by topic. Each chunk was read in full by its own reader, with a shared brief covering how Whitney works, corrections with counts, exemplars, dated facts, context supplied, store and capture, contradictions, and surprises.
3. **Documents.** The 70 document attachments and the 336-entry library were analysed separately.
4. **Synthesis and drafts.** One synthesis pass produced the drafts and the test pack.

Privacy rules applied throughout:

- no personal contact details;
- no revenue, HR or bank data;
- client-private results are listed without figures;
- internal prices are marked.

## How to reproduce the tests

```
python t1_judge.py J0|J1|J2 <model>
python t2_write.py G1|G2
python t2_judge.py anthropic/claude-sonnet-5.5 gpt-6.1-sol
```

Saved responses in `runs/` are reused, so a re-run costs nothing unless an input changes.

## Results (18 October 2026)

**T1: share of 76 judgements (38 pairs, both orders) that picked Whitney's version.**

| Judge | J0 (no WIA context) | J1 (+ knowledge base) | J2 (+ export pack) |
| --- | --- | --- | --- |
| Claude Haiku 5.5 | 43% | 51% | 68% |
| GPT-6 Luna | 43% | 62% | 64% |
| Claude Sonnet 5.5 | not run | 61% | 86% (31 of 38 pairs right in both orders) |

**T2: Sonnet 5.5 judging against Whitney's approved version, both orders.**

- **Export-pack drafts (G2) against ChatGPT's first drafts:** 9 wins to 10.
- **Knowledge-base drafts (G1) against ChatGPT's first drafts:** 9 to 9.
- **G2 against G1:** 9 to 6.

Style-lint findings: G1 20, ChatGPT 14, G2 9, Whitney's finals 10.

**Spend:** USD 2.46 (see `ledger.jsonl`).
