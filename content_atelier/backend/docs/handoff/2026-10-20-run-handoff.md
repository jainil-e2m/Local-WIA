# Handoff: the unattended run of 20 October 2026

This continues `2026-10-19-run-handoff.md`, whose standing rules (section 2) still hold. The plan's status section
("Implementation status", revision 7.1) and each item's row are the source of truth; this note is the short version.

## 1. Where the work happened

The owner's Windows machine. The working copy was restored there from stamp `kenil-2026-10-19b`: database `atelier_work`
in the long-lived container `atelier-work-pg` (127.0.0.1:25440, named volume), artifacts in
`atelier-work/artifacts` beside the repository. Jainil's original handover is restored too, as `restored_atelier`.
Helper scripts with this machine's paths are in `atelier-work/scripts/` (outside the repository): `aw.sh` (a command
against the working copy; `AW_KEY=internal|client` for a paid one), `dbtest.sh` (the suite on a throwaway container;
`DBTEST_BACKEND`, `DBTEST_NAME`, `DBTEST_PORT`, `DBTEST_FRESH=1`), `keys.sh` (the keys' remaining limits, numbers
only). The frontend needs Node 22.12+; a portable Node 24 is in `atelier-work/tools/`.

## 2. What is on `main`

| Item | State |
| --- | --- |
| 2.B11 | The 27 documents re-partitioned from their saved responses under the current repair rules: 1,605 of 1,669 scenes verified (96.2%), USD 0. Left: the Funktastic chain (production data). |
| L.B9, L.B11 | Done: published-content capture; context that keeps itself current. |
| E.B11, E.X7, E.B26, E.B25 | Done. Knowledge base version 8 (`wia-kb-2026-10-20.c-6bf62f94`) is the committed default after three benchmarks (6 against 5, 7 against 6, 8 against 7); versions 5 to 7 are archived. Strategist v6 is the production strategist. |
| E.B3 | The pairwise judge (`python -m evaluation judge-compare`) built and used; its paid re-calibration was not run (section 1.8 already calibrated this configuration; the real calibration waits for E.X3). |
| E.B23 | Brief contract v3 with writer v4: measured on the live week (4 of 5 judgements, 2 of 3 briefs with no repair and no new accuracy problem) and the production brief configuration; the hand-off fields of section 1.9.7 (piece keys, anchor, message spine, `GET /briefs/{id}/handoff`, `can_consume` for v2 and v3). |
| E.B15 | Its engineering remainders repaired (pinned rules at Gate 2, regeneration after a mid-run knowledge-base change, conditions 3 and 4, the v2 reviewer warning). |
| E.B1 | A call whose worst case would pass a run plan's cap is refused before it is sent. |
| S.B8 | Partly done: a container from the documented variables ran a brief's research live, and a fresh container replayed it with no call; the writer step waits for budget (`research/sb8-container-2026-10-20/README.md`). |
| Verifier | False positives found on real samples and repaired: a named colleague read as credited speech, scene timestamps read as figures, the reader's own work read as WIA's. |
| Cards | A publishing order may hold a card for a later week (WIA publishes about three pieces a week). |

## 3. Budget

The run's budget was what the two keys had at its start: internal USD 2.85, client USD 1.51 (the owner later raised the
client key's limit by USD 3.5; that is not for this run). Spent: internal about USD 2.93 (about 0.08 past its weekly limit,
on S.B8's research, before the plan fix), client USD 1.30. The internal key resets weekly.

## 4. Next

1. S.B8's writer step (about USD 0.1 to 0.3): the commands are in its README.
2. E.B13 (held-out Week 5) when the owner funds it; it runs on strategist v6, knowledge base 8 and brief contract v3.
3. Phase 3 engineering on synthetic data ("Where to resume", step 3.2).
4. Owner decisions: D15, D17, D18, S.C1, and where the scheduled knowledge-base benchmark worker runs in production (L.B11).

## 5. Gotchas learned here

- Four suites at once exhaust Windows' local ports: a test fails with "Address already in use"; rerun that file alone.
- OpenRouter refuses (HTTP 402) a request whose worst case exceeds what the key has left; lower
  `CONTENT_ATELIER_LLM_COMPLETION_TOKENS` for a run near the end of a key.
- Anthropic's structured output refuses complex JSON schemas ("too complex for compilation"): send a plain wire schema
  (`ledger_v3.wire_schema`) and validate against the full contract.
- A replay of saved moment-extraction responses under the backfill's own live run needs `CONTENT_ATELIER_LIVE=true`
  with no key and no run plan, so a cache miss is refused rather than sent.
- The closeout tests were written on 19 October: the review's edits valid from 20 October retire their predecessors
  when entered on or after that day; the version 5 test builds the store as on 19 October.
