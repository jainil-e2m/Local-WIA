# Round 2 feedback: what the system must do (27 October 2026)

WIA's "E2M Content Atelier | Round 2 Feedback" (26 October 2026) reviewed the hand-built v2 packs of 20 October (week of
8 to 14 June). Each requirement below is taken from that document, with where the system now meets it and how it is
verified. "Built" is the code; "Verified" is the paid re-test on Week 2 and production (see `README.md`).

| # | WIA's requirement (section) | Built in |
| --- | --- | --- |
| R1 | Five pieces per approved angle: one email, three Reels, one carousel (3) | unchanged; composition check |
| R2 | Email, carousel and Reel 1 share the central story, each developed for its format, never copied and rearranged (3, 8, 10) | writer v5.3, finisher v3 "One theme, five pieces"; check v4 `format_rearranged` |
| R3 | Reel 2: a distinct premise that merits its own piece, not a paraphrase of Reel 1 (3) | kinds `central`/`second`/`third`; premise fields; check v4 `premise_overlap` |
| R4 | Reel 3: a third distinct premise; b-roll and on-screen text are production choices, not angles (3) | `production` separate from `kind`; finisher replaces an earlier brief's stance/b-roll Reels |
| R5 | For each Reel: its premise, hook, audience takeaway, and why it differs from the other Reels (3) | `premise`, `on_screen_hook`, `takeaway`, `distinct_because` on every Reel; shown in the app and the Word export |
| R6 | One coherent weekly theme across the five pieces (3, 10) | craft guide 7; writer and finisher "same theme" |
| R7 | Strong content: the most compelling detail, a hook, narrative momentum, WIA's perspective, a worthwhile takeaway; not a sensible principle restated (2) | craft guide 1 and 2; check v4 `broad_lesson`, `weak_hook`, `weak_takeaway`, piece strength |
| R8 | Editorial judgment: what to share, what to emphasise, how a prospect could read it (4) | craft guide 5 (the six questions); check v4 editorial reading |
| R8a | Inherited campaign performance named as inherited (4, Pack 1) | craft guide 5; check v4 `missing_context` (blocking) |
| R8b | No implication that WIA's ads brought poor leads; no unsupported lead-quality conclusion (4, Pack 2) | craft guide 5; check v4 `lead_quality` (blocking) |
| R8c | The central argument never rests on a conversational or technical aside; technical assertions to a specialist (4) | craft guide 5; check v4 `technical_aside`; Before publishing / pack notes |
| R8d | No unsupported generalisations, agency comparisons or causation (AI did not cause the drop) (4, Pack 3) | craft guide 5 and 6; check v4 `generalization`, `unsupported_causation` (blocking), `agency_comparison`; deterministic `pack.voice` |
| R8e | Keep the factual guardrails: plans vs done, tracked vs total, separate stories (4) | unchanged fidelity rules and check |
| R9 | Voice: no manufactured lines, slogans, dramatic contrasts or agency put-downs; confident explanations of real decisions (5) | "most agencies" instruction removed; craft guide 6; check v4 `slogan`, `repetition`, `agency_comparison` |
| R10 | Specific strategic decisions over broad lessons (5) | central point and perspective rewritten in v5.3; finisher "the lesson stays specific" |
| R11 | Foundational craft beyond WIA's materials: hooks, email, short video, carousels, persuasion, creative development and QA; principles, not formulas (6) | `craft_editorial.v1.md`, included in writer v5.3 and finisher v3 |
| R12 | Assess content strength and editorial suitability before delivery; editorial QA on every asset (6, 8) | check v4 (editorial notes + piece strength) -> repair v2 -> re-check -> findings |
| R13 | Generate and compare several creative approaches, not the first plausible draft (6) | writer v5.3 `premise_options`; finisher v3 `creative_choices` |
| R14 | Workflow: one central direction first, adapt, then discover independent premises for Reels 2 and 3 (8) | writer v5.3 and finisher v3 task order |
| R15 | Timestamps, implementation evidence and verification flags kept separately from copy; briefly why creative directions were chosen (1, 8) | Reel timestamps; Before publishing section on the pack page; "Openings considered"; Word export |
| R16 | Learn from approved edits and the reasons behind them (9) | `reason` on a pack edit; an explained edit becomes a rule candidate for WIA to approve (`knowledge/mining.py`) |
| R17 | WIA's five questions answered (6) | `README.md`, "What the system does now" |
| R18 | Pack-specific notes (7): inherited context, budget as stewardship, the owner's market knowledge (Pack 1); LeadLock built with the client, no ghosting lead, no show-rate claims (Pack 2); no AI causation, no enrolment, guided learning (Pack 3) | covered by R8a to R8d; re-tested on the Week 2 calls the system has cards for |
