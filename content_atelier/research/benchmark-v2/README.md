# Benchmark version 2 (E.B27): whole-week packets from the moments ledger

Built on 23 October 2026 by `python -m evaluation packets --name <week1|week2|october>` (from `backend/`, with
`ATELIER_DATABASE_URL` set to the processed working copy `atelier_work`), with no model call. Each packet is every verified,
current scene of every included call of its window, in the strategist's packet shape (human lines and counter-expected
decisions first), and its scene coverage: every call of the window, included or not (with the reason), its scenes and the
packet's size. These files carry call text, so they live here (R48). Benchmark v1 (`research/benchmark-v1/`) stays for
replay. `python -m evaluation run --weeks week1_v2,week2_v2` runs a configuration on them (M3; paid, under a run plan).

| Packet | Window | Calls (included) | Verified scenes in the packet | Size (strategist v7 message + 30,000 prefix) | State |
| --- | --- | --- | --- | --- | --- |
| `week1.json` | benchmark Week 1, admitted week of 1 June 2026 | 9 (5) | 97 of 97 | 87,753 tokens | complete; reference: Whitney's Week 1 rewrites |
| `week2.json` | benchmark Week 2, admitted week of 8 June 2026 | 11 (5) | 96 of 96 | 128,269 tokens | complete; reference: the gate's three target ideas and the rejected ones (hand-built, R58) |
| `october.json` | 12 to 19 October 2026 (held out; no prompt has seen it) | 15 (8) | 10 | 36,103 tokens so far | **pending**: 7 of the 8 included calls imported by 6.B18 are not scene-extracted |

Notes:

- The six excluded Week 2 calls are internal (only WIA staff speak); they enter as "team practice" evidence only with 1.B13's
  extension (D24).
- No scene is of the new types yet (`first_scene_types: 0`): the ledger holds scene profile v2. Rebuild all three packets after
  E.B31's re-extraction (scene profile v3, paid, after 26 October), then check that Week 2 holds T01's budget reset, T02's
  "beyond the ads", T10's "on paper... it's just all fine" and T11's "I don't know what we changed" as scenes of the new types.
- **Pending paid run (the October packet):** scene extraction of the pending October calls under a run plan, estimated first:
  `python -m backend_pipeline.storage_cli moments extract --from 2026-10-12T00:00:00-05:00 --to 2026-10-20T00:00:00-05:00
  --profile 2026-10-23.scenes.v3 --estimate` (23 October: about 269,000 input tokens, USD 0.05), then the same with `--mode live` under the plan; then
  `python -m evaluation packets --name october --from 2026-10-12 --to 2026-10-19` (no model call).
