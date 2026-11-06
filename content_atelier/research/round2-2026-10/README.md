# Round 2: WIA's feedback of 26 October 2026, built and re-tested (27 October 2026)

WIA's "E2M Content Atelier | Round 2 Feedback" reviewed the hand-built v2 packs of 20 October (week of 8 to 14 June). Its
gap is between the quality of the angles and the quality of the finished content. This folder records what was changed in
the system to close it, the requirement matrix (`REQUIREMENTS.md`), and the paid re-test against every point
(`proof/`, `VERIFICATION.md`). Readings here are the implementing agent's, under delegation (D12, R55); none is WIA's.

## What the system does now

**One theme, five pieces.** The email, the carousel and Reel 1 share the central story, each developed for its format.
Reels 2 and 3 each carry a premise of their own from the source material. How a Reel is made (face to camera, or
on-screen text over b-roll) is a production choice beside its premise, never what makes it different. Every Reel states
its premise, its takeaway, why it differs from the other two and where its material is in the calls.

- Writer v5.3 (`prompt_templates/brief_write.v5.3.md`, `briefs/contracts_v4.py` `BriefWriteV53`) writes the brief that way,
  and lists the three to six premises it weighed before choosing (`format_plan.premise_options`), so Gate 2 approves the
  directions.
- Finisher v3 works in two calls in one step: the plan (`pack_plan.v1.md`) sets each Reel's premise and production and
  weighs two to four openings for every piece; the writing call (`pack_finish.v3.md`) writes to that plan. An earlier
  brief's or pack's stance and b-roll Reels, which retold the central story, become source material and are replaced by
  premises of their own. (The writing answer is at the model provider's grammar limit, which is why the plan is its own
  small answer.)
- Check v4 (`pack_check.v4.md`) reads the pack twice: the fidelity reading as before, then an editorial one: what a
  prospect would infer, inherited work, lead quality, causation, generalisations, technical asides, slogans, agency
  comparisons, repetition, overlapping premises, weak hooks, broad lessons, format fit and takeaways, and how strong each
  piece is. Repair v2 works on those notes with the fidelity flags; what survives becomes a finding. One that could
  misrepresent WIA, a client or a result blocks Ready until a person edits the line or keeps it with a reason.
- E2M's craft and editorial guide (`craft_editorial.v1.md`), shared by the writer, the plan and the finisher: what makes a
  hook, an email, a short video and a carousel work and when, persuasion without invented pain, the six questions before
  featuring a detail, voice, and how to find several independent ideas in one source. Principles, not formulas.
- A person's edit in a pack can say why; an explained edit becomes a rule candidate for WIA to approve into the knowledge
  base (`knowledge/mining.py`).
- The pack page shows each Reel's premise, takeaway and why it differs, the openings weighed, the editor's notes, and a
  Before publishing section (timestamps, notes, client quotes to clear), all apart from the copy.

## WIA's five questions, as the system answers them now

1. **Foundational guidance beyond WIA's materials:** `craft_editorial.v1.md` (hooks, email, short-form video, carousels,
   persuasion, editorial judgment, voice, creative development, self-check), written by E2M and included in every writing
   step, beside WIA's own knowledge base.
2. **Instructions for hooks, subject lines, emails, Reels and carousels:** the guide's format sections, the first-touch rules
   in the writer and finisher, and the plan's weighing of openings for every piece.
3. **How strength and suitability are assessed before delivery:** check v4's editorial reading and per-piece strength, repair
   v2, the re-check, and findings that block Ready when a line could misrepresent WIA, a client or a result.
4. **Several creative approaches compared:** the writer lists the premises it weighed; the plan weighs two to four openings
   per piece and records why it chose one; both are shown to the reviewer.
5. **Learning from approved examples, rejected drafts and the reasons for edits:** an edit's reason is kept and becomes a
   rule candidate; published finals and approved briefs already become exemplar candidates; WIA approves what enters the
   knowledge base. WIA's own reworked examples can enter that way once they are published or entered as exemplars.

## Settings (production)

`prompts.profile.brief_writer` v5.3, `prompts.profile.pack_finish` 2026-10-27.pack-finish.v3, `pack_check`
2026-10-27.pack-check.v4, `pack_repair` 2026-10-27.pack-repair.v2, `pack_refinish` 2026-10-27.pack-refinish.v2. The
switch-backs are v5.2, pack-finish.v2, pack-check.v3, pack-repair.v1 and pack-refinish.v1. The code's defaults stay the
earlier profiles, so packs made before replay unchanged.
