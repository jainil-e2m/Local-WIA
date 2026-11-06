# Live development week, 18 October 2026

One week run live through the product path on knowledge-base version 3 (`wia-kb-2026-10-18.c-3ccde8c5`), with every
review the plan assigns to WIA performed under its delegation (decision D12). It is the live week behind L.B6 and the
development-week evidence for E.B15, E.F1, E.F2 and E.F4. Week 5, the held-out week, still needs S.B10.

## Inputs

Benchmark Week 2's real call excerpts (`research/quality-experiments-2026-10-18/sources/week2.json`: five meetings,
99 turns) were written as one VTT per meeting and admitted with `ContentRepository.admit` as `week_2026-10-05`. Excerpts
only: the full transcripts are on the developer's machine (S.B10).

## What ran

| Step | Path | Result |
| --- | --- | --- |
| Extraction | SQL worker, Luna | 6 source-validated moments, 1 kept unverified (E.B12a) |
| Strategist | profile v5 on Sol, knowledge base as trusted prefix | 3 ranked cards, 5 considered ideas, 3 internal insights |
| Verification | E.B10 deterministic pass and model pass (Sonnet 5.5) | card 3: one blocking misattribution; check flags on all three |
| Gate 1 | two cards reframed (`gate_one.edit`), all three approved with notes | ledgers rebuilt; the blocking flag cleared by the reframe |
| Briefs | v2 (`ATELIER_BRIEF_SCHEMA=v2`), Sol writer, Luna plan, grade and review | 3 briefs, each repaired once |
| Gate 2 | section edits, before-publishing answers, CTA confirmed, scoped review, approve | 3 approved: one with the catalogue's DM keyword and email reply, two with no explicit ask |
| Learning loop | `context_mining`, edits categorised by Sonnet 5.5 (another family than the writer) | 12 candidates: 9 exemplars (3 cards, 6 brief sections), 3 rules from recurring edits, each citing its decision, brief or diffs |

Paid calls: 39, USD 1.19, all under run plan `plan_8a5e3f0cc1324a8fb2d7` (closed) with the recorded privacy routing.
Haiku 5.5 as categoriser was refused by the routing (no zero-retention endpoint for the request) before anything was
sent; Sonnet 5.5 replaced it.

## What the week found and fixed

- The weekly size guard counted the trusted prefix, so knowledge-base version 3 blocked every weekly run before any
  call (176,806 characters against 120,000). Fixed: the prefix no longer counts, as for briefs (`82887bd`).
- A card approved through the plain decision route wrote no decision row, so neither the decision log nor the learning
  loop saw it (R45). Fixed in `gate_one.decide`; this week's three Gate 1 decisions were backfilled and are marked as
  such in `record.json`.
- The runtime still needs a reviewed brand bundle beside the knowledge base (E.B11 (f), V3);
  `backend/knowledge_base/brief-brand-bundle.json` is the reviewed bundle for version 3, pointing to its documents by hash.

## Files

- `brief-1.md` to `brief-3.md`: the approved briefs as the app exports them.
- `record.json`: the cards (every version), the Gate 1 and Gate 2 decisions, the paid calls and the learning loop's
  candidates.

One correction to the record: the Gate 2 note on brief 1 says the former team member is no longer named. That holds
for the perspective and the example, which were edited; the format plan and the claims still name her as a former
team member, which the rejection rules permit (RR-27: never presented as current).
