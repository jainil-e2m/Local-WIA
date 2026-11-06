# Content packs: sources and the planning probe (24 October 2026)

This folder backs the content-packs plan, `backend/docs/Content-Atelier-Implementation-Plan-Content-Packs.md` (Phase NP). It holds client material, so it lives under `research/` (R48). Nothing here is system output shown to WIA (R58). Times are UTC.

## Files

| File | What it is |
| --- | --- |
| `20-october-call-transcript.md` | The full transcript of the 20 October sync, where WIA saw the hand-built v2 packs in the app. The owner supplied it on 24 October. Plan section 3 of revision 8 summarised it; this is the record |
| `sources/chatgpt-export-pack-workflow.md` | What a weekly pack was in WIA's own ChatGPT workflow (349 conversations, 91 of them WIA's own marketing). It was read locally, and no export text was copied beyond short paraphrases (R52). Written by a research subagent and read in full by the planning session |
| `sources/repository-survey.md` | A read-only survey of the code a pack stage touches, at `main` `03a3c98`: the old `packs/` module, the hand-off view, the v4 contract, checks, Gate 2, budgets, the calendar, the frontend, learning capture and tests, with file and line references |
| `probe/` | The planning probe: scripts, with every pack, rendering and check result in `probe/outputs/` (below) |

The 13 October call transcript is in `research/week2-packs-rebuild-2026-10-21/feedback-13-october/`, and the v2 packs WIA saw are in `research/v2-reassessment-2026-10-20/packs/`.

## The probe: can a finishing step lift the system's copy to the pack standard?

**Question.** N2's three briefs (contract v4, writer v5) passed their readings. But their copy reads well below the v2 packs WIA saw on 20 October: abstract and repetitive wording, carousel slides written as paragraphs, captions that skip the reader's world, generic covers, British spelling, and stories that never tell the moment (`research/n2-delivery-2026-10/blind-reading-2/reader.md`). Can a dedicated step after Gate 2 finish that copy into publishable packs without breaking fidelity?

**Inputs.**
- The three N2 briefs (`research/n2-delivery-2026-10/brief-1.json` to `brief-3.json`): the strategy sections, the asset copy, the supported claims and the call evidence.
- Knowledge-base documents 02, 09, 10, 15, 17, 18 and 19 (voice, formats, CTAs, exemplars, edits, spoken voice, raw-to-final chains). No Week 2 text and none of WIA's 20 October corrections went into any prompt (D28).

**Routing.** Every call went through OpenRouter with `data_collection: deny` and `zdr: true` (S.B1's policy), on the internal key, within the owner's USD 5 ceiling for this planning task. On 24 October (Phase NP) the scripts were changed to dispatch through `backend_pipeline.llm.routing.send`, the one dispatch point the privacy-routing guard allows (`test_privacy_routing.py`), which applies the same policy; their prompts and outputs are unchanged.

**Scripts.**

| Script | What it does |
| --- | --- |
| `probe/pack_probe.py` | The finisher, round 1. Edit mode ("refine, don't replace") or fresh mode (write from the strategy). House style by format, first-touch rules and fidelity rules are in the prompt |
| `probe/pack_probe_v2.py` | Round 2. Always three Reels (story, stance, b-roll text), writing a missing kind. It adds round 1's fidelity lessons, cover alternates, no-offer endings and a list of client quotes |
| `probe/claim_probe.py` | The fidelity check. It lists each factual statement in the pack as supported, unsupported or guardrail, against the brief's claims, supporting example, before-publishing items and evidence. The second version adds the offer descriptors, the belief statements, the call date and the "hinting counts" rule |
| `probe/repair_probe.py` | The repair. It returns patches for the flagged sentences only, applies them, and the check runs again |
| `probe/render.py` | Renders a pack JSON as Markdown in the v2 layout, for reading |

### Results

| Run | Model | Cost (USD) | Time | What the reading found |
| --- | --- | --- | --- | --- |
| Brief 1, edit | Sonnet 5.5 | 0.1287 | 39 s | Format fixed: short slides, US spelling, one kicker removed. Still abstract; the story is unchanged; a kicker remained ("That's the standard we hold ourselves to.") |
| Brief 1, fresh | Sonnet 5.5 | 0.1192 | 35 s | Almost the same as the draft. It kept the b-roll line the verifier had flagged ("before replacing them") |
| Brief 2, edit | Sonnet 5.5 | 0.1018 | 26 s | Light gains |
| Brief 3, edit | Sonnet 5.5 | 0.1339 | 37 s | Light gains |
| **Brief 1, edit** | **Opus 5.5** | 0.3865 | 116 s | **Clearly better.** Spoken register in the script ("A little backstory for you", "right?"); Whitney's exact line from the evidence; captions open in the reader's world; slides as stacked short lines; first-touch lines name the landing page; the flagged b-roll line fixed; "stronger with permission" names the real turn (the new page converted less) that the brief keeps out |
| **Brief 2, edit** | **Opus 5.5** | 0.3844 | 124 s | **The story is finally told**, with the client's own words ("I don't think that I love them") and a punchier subject ("You don't owe your ad team a yes"). The quote needs clearance: brief 2's first before-publishing item holds it |
| **Brief 3, edit** | **Opus 5.5** | 0.3534 | 95 s | **The best pack.** It tells the real moment with Carmen's own lines, scripts are conversational, the carousel has a belief slide and a close for both readers. It also added a price hint ("which ones felt out of budget") and turned the client's explanation into agreement |
| Brief 1, v2 | Opus 5.5 | 0.4437 | 140 s | Three Reels. **The stance Reel it wrote** keeps the same point in Whitney's stance with the moment as one line of proof, and is not a sub-lesson. Cover alternates are good |
| Brief 3, v2 | Opus 5.5 | 0.3850 | 109 s | Three Reels and a good stance Reel. **More fidelity drift than round 1:** invented dialogue, a quote moved to another moment, "we take responsibility for the recommendation" |
| Brief 2, v2 | Opus 5.5 | 0.5504 | 203 s | Three Reels on the weakest brief. The stance Reel holds the point ("Just because our team made a new ad for you doesn't mean you have to approve it"), and the client's quote is listed for clearance. It wrote 20,489 output tokens, the most expensive run |

| Check or repair | Model | Cost (USD) | Result |
| --- | --- | --- | --- |
| Check, brief 1 (Opus edit), version 1 | Sonnet 5.5 | 0.0583 | 7 unsupported, 3 guardrail. Real catches: "I've been thinking about that conversation since" (an invented reflection) and "pages working" (implies a result). The other flags came from sources it lacked (offer descriptors, the call date) |
| Check, brief 3 (Opus edit), version 1, run 1 | Sonnet 5.5 | 0.0816 | 3 unsupported (offer wording only). **It missed the price hint and the "agreed"** |
| Check, brief 3 (Opus edit), version 1, run 2 | Sonnet 5.5 | 0.0727 | 9 unsupported. The same input as run 1 gave a different result: **a model check alone is a noisy net** |
| Check, brief 3 (Opus edit), version 2 | Sonnet 5.5 | 0.0781 | **It caught the price hint (guardrail) and all three "agreed" changes of who did what** |
| Check, brief 2 (Opus edit), version 1 | Sonnet 5.5 | 0.0636 | 2 unsupported. It did not flag the new client quote: a deterministic rule must route it to clearance |
| Check, brief 1 (v2), version 2 | Sonnet 5.5 | 0.0950 | 3 unsupported and 1 guardrail: a widened scope, a stretched "before changing anything", and the story placed next to ELEVATE (it hints the client is a member) |
| Check, brief 3 (v2), version 2 | Sonnet 5.5 | 0.1033 | 12 unsupported: invented dialogue, a quote attached to the wrong moment, accountability claims |
| Check, brief 2 (v2), version 2 | Sonnet 5.5 | 0.0790 | 2 unsupported. One is a line already listed as a personal line ("I'm proud of the work our team puts into every ad"), so the check should skip personal lines and leave them to Whitney. The other is a hedged "I think I emailed you back" stated as fact |
| **Repair, brief 3 (v2)** | Opus 5.5 | 0.1092 | 13 patches, all applied |
| **Re-check after the repair** | Sonnet 5.5 | 0.0930 | **33 supported, 0 unsupported, 0 guardrail.** The loop converges. The repair made some lines flatter, cut the Reel 1 caption below 150 words, and restored the brief's own "before considering theirs" paraphrase, which is a Gate 2 point for Whitney |

**Spend.** USD 3.82 on the internal key (finisher calls 2.99, checks and the repair 0.83), against the owner's USD 5 ceiling. The key's weekly figure is USD 5.54 of 15, including N2's 1.72.

### What the probe settles (carried into the plan)

1. **A finishing step after Gate 2 works.** Opus 5.5 in edit mode lifts every brief on voice, first touch, caption structure, carousel shape and telling the moment. Sonnet 5.5 is cheaper but gains little. Fresh writing gains nothing over editing.
2. **Three Reels can be guaranteed.** The finisher writes a missing stance Reel that holds the same point. The owner set the composition on 24 October: 1 email, 1 carousel, 3 Reels.
3. **Fidelity drift is real and varies by run.** Drift showed up as invented reflections and dialogue, changes of who did what, quotes moved to another moment, hints at kept-out details and widened commitments. Every pack needs a check, a repair and a re-check, plus deterministic quote and novelty checks and a person's review. A model check is a net, not a gate.
4. **The finisher cannot fix what the brief's claims hold.** A paraphrase that the claims mark as supported, such as brief 3's "before considering theirs", survives into the pack. Gate 2 edits must come first. They are locked, and the pack keeps them word for word.
5. **The story's strength is capped by the brief's keep-out items.** The finisher can only name the stronger version ("stronger with permission"). Whitney unlocks it at Gate 2 by permission or an attested fact (R57).
6. **Cost and time per pack.** About USD 0.55 to 0.85 and 4 to 6 minutes: the finisher 0.35 to 0.55 (95 to 203 s), the check 0.06 to 0.10, the repair about 0.11 and the re-check about 0.09.

These are the planning session's delegated readings (D39, R55), one sample per configuration. They are evidence for the design, not a gate. NP-5's readings are the gate.
