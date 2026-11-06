# The N11 benchmark (25 October 2026): design

The owner chose the smaller benchmark (about USD 6 on the Client key, on a scratch copy of production; no LLM judge).
Every reading is the implementing agent's, recorded as delegated (D12, R55). This file is the design; the results go in
`README.md` beside it.

## What runs

| Week | What | Why |
| --- | --- | --- |
| Week 2 (calls of 8 to 14 June 2026, eleven calls with the internal meetings) | The cycle (strategist and scene profile of record), two cards developed into briefs, one Gate 2 refresh each, two packs | The only week with WIA's verdict on finished copy (her 20 October notes, W1 to W13) and with the ideas WIA's own ChatGPT work found |
| Week 1 (calls of the week of 1 June 2026) | The cycle only | Whitney's 13 October review of the Week 1 angles rated the batch 1 and gave six alternatives (landing-page relevance, accurate messaging, keyword decisions with client knowledge, venue value positioning, creative strategy, LeadLock's value) |

The copy is production's database (copy D, `atelier_np_d`, restored 25 October and migrated), so the cycle reads the
same identities, team-practice scenes, account memory, published-content log and prior cards production has. Week 2 was
already run once on it in N8 (`research/n8-2026-10/proof/d-week2-*.json`, strategist v8): that run is sample 1, and the
benchmark's Week 2 cycle is sample 2, so the two show what is stable.

## The reference (held out; never in a prompt, D28)

- **WIA's verdicts.** Plan section 3.2 (W1 to W13, from `research/packs-2026-10/20-october-call-transcript.md`), the
  13 October call (`research/week2-packs-rebuild-2026-10-21/feedback-13-october/`) and the Week 1 analysis
  (`research/2026-10-13-whitney-week1-feedback-analysis.md`).
- **Her taste in her own words.** Her reactions to hooks, subjects and CTAs and her sent subject lines
  (`research/week2-packs-rebuild-2026-10-21/notes/chatgpt_export_week2_findings.md`, section C).
- **The ideas found by hand.** The three v2 ideas she saw on 20 October (the budget approach, what strategy calls cover,
  understanding an AI-changed account), the ten ChatGPT Week 2 angles and the moment catalogue (section A.3).
- **What must not repeat.** Week 2's ideas already published (section 0, findings 4 and 5).
- **The standard.** Plan sections 4.2 (the card), 4.3 (the brief, the assets, the five first-touch rules) and
  Appendix E (rubric 2.3a, conditions 2.4, standard 2.4a).

## How each output is scored

1. **Cards.** For each card: the five point tests, one moment proving one belief, the guardrail, and rubric 2.3a's five
   criteria (1 to 5). For the slate: which of the hand-found ideas appear (or a card at least as strong in their place,
   with the reason), repeats of published ideas, and, on Week 2, agreement with sample 1.
2. **Briefs.** Conditions 2.4 and standard 2.4a; the 13 October structure; claims against the calls.
3. **Packs.** Every first-touch rule on every first-touch line (subject and preview, covers, on-screen hooks, the first
   b-roll screen, slide 1); each of W2 to W8 as a test (a subject that narrates a third party, an ambiguous slide 1, a cover
   without its subject, an insider term, who did what); sibling repetition (ideas may repeat, sentences and hooks may not);
   register; CTAs; and the automatic checks' findings.
4. **Blind comparison (E.X8 without a judge).** The pack pieces and Whitney's finished pieces on near themes are mixed,
   unlabelled, in a recorded random order; each is read for "would publish as is / after a light edit / would not
   publish", then unmasked.

A failure becomes a general rule in a new prompt version (a released profile is never edited; never her wording), and
the affected step is run once more.
