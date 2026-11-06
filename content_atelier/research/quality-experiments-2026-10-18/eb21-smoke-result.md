# E.B21 smoke result: strategist profile v4 against v5 (18 October 2026)

## Set-up

| Item | Value |
|---|---|
| Weeks | Development Weeks 1 and 2 (`sources/week1.json`, `sources/week2.json`); Weeks 5 and 6 untouched |
| Prompts | Built by the backend: `angle_profiles.strategist_angle_prompt` with knowledge base `wia-kb-2026-10-18.v2` at the strategist stage (`exp_profiles.py`) |
| Generator | `openai/gpt-6.1-sol`, reasoning effort high, one sample per week and profile |
| Judge | The calibrated configuration from plan section 1.8 (T1, J2): `anthropic/claude-sonnet-5.5` with the knowledge base and the export's "how Whitney edits" pack, on `exp_judge.py`'s pairwise rubric |
| Orders | Each week judged in both presentation orders (four judgments) |
| Routing and plan | Every call through `provider.send` with routing `2026-10-18.deny-collection-zdr.v1` (S.B1), under file run plan `plan_d040de102f594c6c8080` (E.B1), cap USD 1.00 |
| Cost | 8 calls, USD 0.697 (generation 0.428, judging 0.269); the plan is closed |

All four generations passed the product's own contract check (`WeeklyAngleCards` for v4, `WeeklyAngleCardsV5` for v5).

## Judgments

| Week | Set X | Set Y | Preferred | Rating X | Rating Y |
|---|---|---|---|---|---|
| 1 | v4 | v5 | v4 | 3.2 | 3.0 |
| 1 | v5 | v4 | tie | 2.8 | 3.0 |
| 2 | v4 | v5 | v5 | 2.5 | 3.2 |
| 2 | v5 | v4 | v4 | 2.5 | 3.0 |

Mean estimated Whitney rating, both orders:

| Week | v4 | v5 |
|---|---|---|
| 1 | 3.10 | 2.90 |
| 2 | 2.75 | 2.85 |
| Both | 2.93 | 2.88 |

Overall preferences: v4 twice, v5 once, one tie. In Week 2 the set shown second won in both orders, so that week's preference reflects position, not profile.

What the judge said, in brief:

- **Week 1:** both profiles chose nearly the same three scenes and the same internal items. v4 had sharper hooks and plainer language. v5 was stronger on strategic fit, series and attribution care.
- **Week 2:** in one order the judge praised v5's link to Whitney's beliefs and series and its founder-forward idea. In the other it preferred v4's tighter claim boundaries and process idea.
- **Factual problems:** both profiles had small overreaches, three or four per set, of the same kind (a planned audit described as done; a looser reading of what a strategist committed to). Neither invented results, prices or people.

## Reading

The difference between v4 and v5 is within the noise of one sample per week, and position bias is visible. The smoke result favours neither profile.

## Decision for E.B13 (recorded before the run)

**E.B13 runs strategist profile v5.** Because the smoke result is a tie, the choice rests on what each profile carries. v5 adds:

- the fields the rest of Phase E depends on: seed pairing (E.B19), series and the publishing order (E.F2), and pillar notes (3.B14);
- the export's positioning rules, which v4 does not carry.

v4 stays available for replay. E.B13's three samples per week, together with Whitney's dispositions on held-out Week 5 (E.X3), are the real comparison. If they rate v5 below the v4 baseline, E.B13 records it and the next cycle reverts to v4.

Open point for a later prompt revision, not tuned on these development weeks (to avoid fitting the judge): in Week 1 the judge found v4's hooks sharper and plainer.
