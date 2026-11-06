# Angle prompt profiles and the WIA knowledge base

Implements E.B9 (strategist profile and lean card), E.B11 (knowledge base), E.B21 (strategist profile v5) and the
downstream work of Phase E (plan revision 6): cards downstream (E.B16), per-moment extraction (E.B12a), prompt hygiene
(E.B17), the evidence ledger (E.B10), Gate 1 dispositions (E.B20), founder seeds (E.B19), brief v2 (E.B15), scene
extraction (E.B12) and the evaluation command (E.B3). The legacy profile is still the default for new cycles; E.X4
switches it once the held-out result (E.B13) meets the round-one bar.

## Profiles

| Profile | Prompt | Output | Default |
|---|---|---|---|
| `2026-10-19.reel-editorial.v2` | The five-template stack (`angle_generation.system.md` and the rest), then Whitney's six Reel scripts as labelled taste data; the user message and the comparison runner's evidence JSON carry only the evidence (E.B11 (3)) | `StrategicAngleResponse` (21-field drafts with self-scores) | Yes, until E.X4 |
| `2026-10-16.reel-editorial.v1` | The same stack with the Reel scripts after the evidence in the user message (inside the evidence JSON on the comparison runner) | `StrategicAngleResponse` | No; replay only, and benchmark v1's recorded default. Refused for new live runs |
| `2026-10-18.wia-strategist.v3` | Appendix A, verbatim (`prompt_templates/angle_generation.wia_strategist_v3.md`), followed by the WIA knowledge base | `WeeklyAngleCards` (lean card, `card_contracts.py`) | No; replay only. Refused for new live runs (it carries week-derived examples, E.B17) |
| `2026-10-18.wia-strategist.v4` | Version 3 with invented examples, scene references and handling tags (`angle_generation.wia_strategist_v4.md`), followed by the knowledge base | `WeeklyAngleCards` | No; kept for replay and comparison |
| `2026-10-18.wia-strategist.v5` | Version 4 plus Whitney's ranking order, the analysis's lenses, the export's positioning rules, series, a publishing order and founder seeds (`angle_generation.wia_strategist_v5.md`), followed by the knowledge base | `WeeklyAngleCardsV5`: cards with an optional `series`, plus `publishing_order`, `pillar_notes` and `seed_pairings` | No; the profile E.B13 runs |
| `2026-10-20.wia-strategist.v6` | Version 5 plus stance and experience (E.B26): a team member's first-person observation is attributed experience, never a prevalence claim; Whitney's view at the strength she said it; an ATTRACT idea may challenge an industry belief, never the reader; the content plan's pillar mix; at most one "Why/What/How we" title; evidence points without timestamps (`angle_generation.wia_strategist_v6.md`), followed by the knowledge base | `WeeklyAngleCardsV5`, as version 5 | No; opt-in until its paid smoke against v5 on benchmark v1 |
| `2026-10-23.wia-strategist.v7` | The v2 method (E.B30, E.B32, E.B29 change): the window's strategy brief (beliefs to prove, offers in force) after the seeds; human lines and counter-expected decisions first in the packet, marked; one real moment proves one belief; the five point tests as card fields; Whitney's own card format with a guardrail the writer reads; plain "How we..." titles (v6's limit dropped); one public card per client conversation; recurrence as context, never a ranking input; KB 19 used when present; contrasts rewritten from Week 1, never Week 2 (`angle_generation.wia_strategist_v7.md`), followed by the knowledge base | `WeeklyAngleCardsV7`: `AngleCardV7` (no `core_perspective`; `point` replaces it), and v5's week fields | No; opt-in until M3's gate |

Version 4 (E.B16 f and i, E.B17) differs from version 3 in three ways:

- **Invented examples.** The zoom-out list and illustration, the voice contrast and the missing-fact example came
  from Week 1 and Week 2 material. Version 4 replaces them with invented scenes (a cake designer's winter
  tastings, thank-you emails) and keeps Whitney's general rule about pricing objections as a rule.
  `EXAMPLE_PROVENANCE` in `angle_profiles.py` records the source of every example in every version; no version 4
  or 5 example derives from any week.
- **Scene tags.** Each scene shows its sensitivity, the extractor's suggested destination and its qualifications.
  An internal-only scene may feed `internal_insights` only.
- **Scene references.** Scenes are labelled S1, S2 and so on, and the model cites those. The server resolves them
  to moment IDs. An unknown or repeated reference, or an internal-only scene in an angle or considered idea, gets
  exactly one repair call that shows the model its answer and the problems; a second bad answer fails the stage.
  Both responses are cached, so a replay makes no call.

Version 5 (E.B21) adds:

- the ranking order: strategic fit, distinctiveness, audience resonance, then source strength;
- the lenses: misconceptions, objections, aha moments, strong recommendations, results and behind-the-scenes decisions;
- several ideas per strong call, when their central points differ, and a second look at prospect calls;
- pillar notes when the slate sits in one pillar;
- the export's positioning rules, which defer to the rejection rules;
- a `series` from the content strategy and a proposed publishing order;
- founder seeds (E.B19), paired with the scenes that support them or flagged as having no call evidence.

Whitney's Reel scripts move out of the user message into the knowledge base's `exemplars` document (E.B11 d).

### Version 7 and card verification v4 (E.B30, E.B32, E.B29 change, E.B28)

**The strategy brief (E.B28, `cycle/strategy_brief.py`).** A deterministic assembler (no model call) builds, for each cycle,
four to six `beliefs_to_prove` from `knowledge_base/beliefs-to-prove.json` (every belief rests on quotes from documents 16
and 01, checked word for word against the loaded documents; the mix follows document 14; a belief proved in the last 30
days waits; the season, Savannah's priority series and the longest wait come first), each with its offer (only an offer on
sale in the window) and its do-not-repeat pieces from the published register; `live_offers` from
`knowledge_base/offer-calendar.json` (status, window, `do_not_undercut`), checked against document 05; the last 90 days'
central points, the priority series, the content plan and the season. `repository.submit` freezes it with every card
cycle (`input_refs.strategy_brief`, `strategy_brief_hash`); the week review (`strategy_brief`), the cycle routes
(`/storage/cycles/{run_id}`, the preview) and `GET /storage/strategy-brief?on=` show it. Every card of a cycle with a brief
is checked against the calendar: a card whose point, title, why-it-matters or takeaway makes a do-not-undercut point gets a
blocking `offer_undercut` flag naming the offer and a Gate 1 hold until the offer's window ends.

**The card (`AngleCardV7`).** Her six fields at her length (`pillar` and `content_type`, `audience`, `why_it_matters`,
`wia_in_action` as "WIA's expertise or process", `evidence_points` (one to three, with timestamps), `guardrail`), then
`point`, `point_is_about` (wia_belief, wia_standard, client_experience, platform_or_tactic),
`surprise_for_experienced_advertiser` {surprising, reason}, `reader_takeaway`, `reader_fit` {buyer, buyer_statement, why},
`belief_ref`, `offer_fit` {offer, cta_slot, calendar_note}, `public_stance` {takes_stance, stance} and `recurrence`
(context only). Read a card's point with `card_contracts.card_point`; an edit of `core_perspective` on a v7 card edits its
`point`. v3 to v6 cards load, render, edit and replay as before.

**One public card per client conversation.** Two public cards citing scenes of the same recording are a problem for the
same one repair call as a bad scene reference; if the repaired slate still has some, the later-ranked card moves to the
considered ideas, recorded in `angle_reference_repair.json` (`demoted_same_conversation`).

**Card verification v4 (`prompts.profile.card_verification`, default v3).** On a v7 card the deterministic pass rejects for
public use a point about a platform or tactic (declared, platform-led without WIA's voice, or an instruction), a takeaway
that instructs the reader, and a reader fit, audience or point that presents ads or an offer as frustrating or writes from
desperation; the v4 model pass (`card_verification.v4.md`) judges the same three tests and adds its reason. A rejection is a
blocking flag that cannot be acknowledged (reframe the card, or mark it internal) and the ledger's `public_use` says why. A
card with `public_stance.takes_stance` gets a check, and Gate 1's develop path refuses it until an approver confirms the
stance (`POST /storage/angles/{angle_id}/stance`, D31); an edit that changes the stance or the point drops the confirmation.

**The brief writer** receives a v7 card's `guardrail`, `point`, `reader_takeaway`, `reader_fit`, `belief_ref`, `offer_fit`
and `public_stance` in its packet's `card`; an earlier card's packet is unchanged, so saved briefs replay.

**Pending paid run (after 26 October).** One Week 1 sample on benchmark v1, smoke only:
`python -m evaluation run --configs strategist_v7 --weeks week1 --samples 1 --smoke` under an active run plan
(`--dry` reports 148,653 characters, about 37,000 input tokens; with about 10,000 to 16,000 output tokens on
`openai/gpt-6.1-sol` that is USD 0.17 to 0.23).

**Smoke result (E.B21).** On development Weeks 1 and 2, judged by the calibrated judge (T1, J2) in both orders, v4
and v5 tied: mean estimated rating 2.93 against 2.88, with position bias visible in Week 2. E.B13 runs v5 because it
carries what Phase E needs, and v4 stays available. The record, with cost (USD 0.70 under a closed file plan), is
`research/quality-experiments-2026-10-18/eb21-smoke-result.md`.

**Held-out hygiene (E.B17).** Reel 5 and the client result behind it derive from benchmark Week 6, so knowledge base
version 2 withholds them. Version 3 (`c-3ccde8c5`) brought them back through the seed; the verification of 18 October
found it, and since then the guard in `knowledge/held_out.py` withholds held-out material from every compiled version,
the brief's exemplars and the situational block, and a live run refuses a knowledge base that states it. Version 9
(`wia-kb-2026-10-22.c-a1a75795`, E.B25 (i), (j), L.B12: version 8 with Whitney's spoken voice and her raw-to-final chains;
read against version 8's recorded runs in phase N2 on 23 October, D40) is the committed one; versions 3 to 8 are archived
for replay only. Profile v4's prompt
profile still carries all six Reel scripts in its user message, so profile v4 does not fully hold out Week 6; the
held-out run uses profile v5, which reads the Reels from the knowledge base.

## Switching profiles

The profile, the strategist model and the verifier are **settings** (plan 0.B8): change them in the database, with no
deploy and no restart, and the next weekly run uses them:

```bash
python -m backend_pipeline.storage_cli settings set prompts.profile.strategist 2026-10-18.wia-strategist.v5 --actor <your email>
python -m backend_pipeline.storage_cli settings set models.angle_generation openai/gpt-6.1-sol --actor <your email>
python -m backend_pipeline.storage_cli settings set models.card_verification anthropic/claude-sonnet-5.5 --actor <your email>   # optional: E.B10's model pass, another family
python -m backend_pipeline.storage_cli settings set models.reasoning_effort.angle_generation high --actor <your email>          # optional: per stage; blank follows models.reasoning_effort.default
```

The old variables still work as the value until a row exists (a row wins): `CONTENT_ATELIER_ANGLE_PROMPT_PROFILE`,
`OPENROUTER_ANGLE_GENERATION_MODEL`, `OPENROUTER_VERIFICATION_MODEL`, in `backend/.env` or as process variables.
`settings import-env` records them as rows. `CONTENT_ATELIER_KNOWLEDGE_BASE_DIR` stays an environment-only
development override (blank: `backend/knowledge_base/`); to run a compiled knowledge-base version rather than the
files or the active version, set `knowledge_base.version`. See DEPLOYMENT.md, "Settings".

- `models.angle_generation` is a per-stage override for strategist angle generation only: the default profile ignores
  it (E.B16 h). Extraction keeps `models.moment_extraction`. Blank means angle generation uses `models.default`
  (`OPENROUTER_ANGLES_MODEL`), as before.
- Set the model explicitly. The strategist prompt was tested on Sol (won 4–0) and on Luna (lost 0–4). A live run
  refuses to start while `models.moment_extraction` or `models.default` (or, under a strategist profile,
  `models.angle_generation`) is still the code default.
- The profile and models are frozen at submit, together with a `settings_snapshot` of the values and where each came
  from (default, env or table); a worker on another profile refuses the run before extraction. A queued run keeps the
  settings it was submitted under; create a new run after changing them.
- To go back, `settings unset prompts.profile.strategist` (the default is `2026-10-19.reel-editorial.v2`) or set it.

Every paid call needs an active run plan (`ATELIER_RUN_PLAN_ID`, or `ATELIER_RUN_PLAN_FILE` for a harness) and
leaves through the `llm` module (`backend_pipeline/llm/`) with the recorded privacy routing (S.B1) and writes an `llm_runs` row (model, prompt version,
knowledge-base version, tokens, cost). A weekly strategist run on Sol costs about USD 0.09 to 0.13 per call. A response that breaks its
schema gets exactly one repair call (0.B4), which is another call under the plan: size `--max-calls` with one spare per stage.

## The knowledge base

WIA's documents are committed in `backend/knowledge_base/` (the repository is private; the project owner decided
on 18 October 2026 to keep them in git so the work can continue on any machine). The committed version is
`wia-kb-2026-10-22.c-a1a75795` (version 9, manifest format 2, compiled from the reviewed context store; plans E.B25, E.B11,
L.B12): 19 documents under WIA's rulings (`WIA-Rulings-2026-10-18.md`). Each document records its status, effective date, review
interval, the stages that load it, and its provenance:

| Stage | Documents |
|---|---|
| Strategist | The three guides, roster, offer sheet, rejection rules, process catalogue, content workflow, audience language, results register, recent published, content plan, exemplars, belief statements, the editing guide and the transformations (within the prefix budget: see below) |
| Brief | The same without recent published, plus the format guide, CTA catalogue and spoken voice |
| Verifier (E.B10) | Roster, offer sheet, rejection rules and results register |
| Extraction (E.B12) | Roster and process catalogue only |

Statuses: the three guides are `supplied`; the other 16 are `confirmed` (the seed review of 18 October and E.X2, under
D12). Live runs record which version and documents they used. The rejection rules ship with
`rejection-rules.patterns.json`, which the E.B10 lint reads; the compiler writes it from the version's rules and the manifest binds it
by hash. Every rule names its category, and a confirmed rule without one stops the compile. Versions 1 to 8 are archived in
`knowledge_base/archive/` for replay (version 8 with the additions list it applied). Version 9 adds, through the same
additions list from 22 October, Whitney's spoken voice (`18-spoken-voice.md`: five Reels she recorded, verbatim, for the
brief writer only) and her raw-to-final chains (`19-transformations.md`: six, in her own words, under D34's default), and
carries document 05's approved descriptors and insider-term glossary (from `reviewed-entries.json`, derived from
`offer-descriptors.json` and `insider-terms.json`), document 09's first-touch rules and the published register at piece
level; it replaced version 8 after its reading in phase N2 (one sample, D40: one blocking accuracy flag in five cards, equal
to version 8's worst run, and no content-level blocking finding in the brief;
`research/n2-delivery-2026-10/kb9-reading.wia-kb-2026-10-22.c-a1a75795.json`). Version 8 adds the editing guide (`17-editing-guide.md`: how Whitney edits, her
corrections to drafts in her ChatGPT history as rules, reviewed under D21) through `knowledge_base/additions.json` (E.B25
(e)): a committed, dated list of supplied documents the compiler adds once, from their date, to a version whose base lacks
them, each bound to the hash of its reviewed text, so the runtime never reads the export (R52); it had replaced version 7 after
its E.B3 smoke run (strategist v6, three samples a week: no accuracy regression, and the calibrated judge preferred it in
7 of 11 judgements). Version 7 applies `knowledge_base/supersessions.json` (E.B25 (c): 26 reviewed
entries, each matched by its exact line and count, from 20 October; the supplied originals are never edited) to version 6,
which had replaced version 5 after its E.B3 smoke run (no regression on benchmark v1; its two blocking flags are verifier
misreadings of a named colleague, E.B26): eleven rules refiled under their reviewed category (words, author, date and origin kept) and the proof
rule without the figure a venue client vetoed, so the strategist receives no client result figure outside cleared material. Hashes are taken over normalised text, so a CRLF checkout records the same hashes (E.B11 e).

`storage_cli kb-publish` writes a version to `brand_kit_docs`, and `kb-check` proves the files and the table give the
same text and hashes. A change needs code-owner review (`.github/CODEOWNERS`).

## Where a stage's context comes from (Phase L)

Every stage gets its context from one service, `backend_pipeline/knowledge/assembly.py` (L.B5):

- **The prefix.**
  - With an empty context store, or before migration 006, the prefix is exactly the file knowledge base above, with the same text and hashes.
  - Once WIA confirms items, the operating documents are rendered from the confirmed items valid on the run's date: roster, offer sheet, CTA catalogue, results register, process catalogue and content plan. So a new price or team member reaches the next run without a new version, and an expired one never does.
  - Internal items are labelled "internal: never state publicly". Internal and gated prices are never written into any document.
  - **The budget is enforced** (E.B25 (d)): over `context.budget.prefix_tokens` (30,000), whole documents leave from the bottom of the recorded priority list (`prefix-priority.v2`: content workflow, Accelerator workbook, results register, process catalogue, recent published, content plan, audience language, exemplars, offer sheet, roster, content strategy, editing guide, voice guide, beliefs, rejection rules, lowest first) until it fits; a version holding document 18 or 19 is cut by `prefix-priority.v3` instead (spoken voice and transformations just below the protected documents and the editing guide, ahead of the exemplars; then process catalogue, audience language, content plan, recent published, results register, Accelerator workbook, content workflow, lowest last). The rejection rules, beliefs, voice guide, content strategy, roster and offer sheet never leave, nor does a document the list does not name. Version 8's strategist prefix is 38,525 tokens in full and 28,863 with the content workflow, the Accelerator workbook and the results register left out; the brief writer's also leaves out the process catalogue. Version 9's strategist prefix is 43,828 tokens in full and 29,626 without the content workflow, Accelerator workbook, results register, recent published, content plan and audience language; the brief writer's is 50,213 and 29,264, also without the process catalogue and the exemplars.
  - Identity documents (rules, exemplars, beliefs, audience language, format, the supplied documents, the editing guide, the spoken voice and the transformations) change only through an approved knowledge-base version, compiled from confirmed items. A version that changes them waits for its benchmark smoke result before it becomes the default: `storage_cli kb-compile`, `kb-approve`, then `python -m evaluation run --knowledge-base-version <v>` and `kb-benchmark`.
- **The strategist's user message** gains a dated situational block when the store has one: the content plan and campaigns valid that day, and the pieces published in the last 90 days with the strongest and weakest of them. It is context, not call evidence.
- **The brief writer** receives up to `ATELIER_CONTEXT_EXEMPLARS_K` confirmed exemplars for its channels, in place of the whole exemplar document.
- **The verifier** blocks internal figures (an internal price, for example), and names ChatGPT invented, in public card and brief copy.

Each run records what it used under `knowledge_base.context`: the source, the date, the version, each document's hash, and the IDs and hashes of the items, exemplars and situational entries. It also records any items excluded as expired, the token counts, the staleness warnings, and the prefix budget's record (`prefix_budget`: the priority list's version, the budget, the tokens before and after, and the documents dropped; a file-backed run records it only when something was dropped).

The knowledge itself grows only from WIA's work in the app. The review queue, the learning loop and the operating-facts editor are described in plan section 4.12. The one-time seed from the ChatGPT export (`storage_cli context-seed`) is recorded in `Context-Switch-Over-Record.md`.

## What a strategist run records

- **Input refs:** profile, angle model, knowledge-base version, stage, drafts used, manifest SHA-256, the SHA-256 of
  the assembled prefix, and each document's key, version, owner, status, file SHA-256 and length. The text itself is
  never recorded. The SQL workflow freezes them in `pipeline_runs.input_refs.angle_contract`; a retry whose knowledge
  base, model or profile no longer matches fails instead of mixing versions. Version 5 also freezes the open founder
  seeds (`input_refs.seeds`), so a retry sends the same prompt.
- **Settings snapshot (0.B8):** `input_refs.settings_snapshot` lists every behavioural setting the run uses (models,
  reasoning effort per stage, profiles, thresholds, budgets, the embedding contract) with its value and source, and
  the knowledge-base version a strategist profile loaded. A brief run, a pack run, an encoding run and a
  reassessment record the keys they use.
- **Angles:** each card becomes a `content_angles` row with `content_body.card`, `source_family_id` and its evidence
  ledger (`content_body.ledger`). There is no self-score.
- **Week-level reasoning:** `week_summary`, `ranked_angle_ids`, `internal_insights`, `considered_not_selected` and
  `unreferenced_moment_ids`, plus `publishing_order`, `pillar_notes` and `seed_pairings` (with each seed's ID) for
  version 5, in the angle job's `result_refs`.

## Cards downstream (E.B16)

- **Runners.** Cards run on both SQL workflows. On `historical_comparison_v1` refinement is skipped for cards.
- **Selection.** Matching treats a card as complete without scores. A card at or above the duplicate cosine
  (`matching.duplicate`, or `ATELIER_DUPLICATE_COSINE`; default 0.86, calibrated by E.B6 on labelled pairs) to a better-ranked visible card is collapsed into it.
- **History gaps.** An earlier angle never encoded under the current embedding contract is skipped and recorded as
  `history_gaps` in matching and `prior_gaps` in brief preparation.

## The evidence ledger (E.B10)

`cycle/verification.py` builds one ledger per card at the angle stage: bindings of evidence points to spans,
attribution against the roster and speakers, tense and status overclaims, unsupported numbers, an unknown result
stated as zero, frequency and prevalence claims, one scene generalised into "a WIA practice", former staff named, R40
(the WIA contribution binds to a roster member's turn) and the rejection-rule lint (style findings are warnings only).
With `OPENROUTER_VERIFICATION_MODEL` set, a model pass from another family binds the rest, judges overclaims and
invented reasons, lists qualifiers and records the rubric 2.3a critic (shown, never used for ranking). Its findings
block only for unsupported facts, misattribution, and consent in the public framing. The verifier also reads Whitney's
belief statements (`STAGE_EXTRAS` in `knowledge_base.py`, whatever a version's stage list says), and its prompt
(`card-verification.v2`) treats a quoted belief as WIA's stated view, never as words said on the call; a finding whose
flagged text only quotes a belief statement is a check (`belief_quote`), never a block. Edits and reframes rebuild the
ledger. A card with an unresolved blocking flag can be held or reframed, or developed only after an approver checks
each blocking flag by its ID with a note.

## Gate 1 (E.B20, E.F1, E.F2) and seeds (E.B19, E.F3)

- `POST /storage/angles/{id}/decision` takes a disposition (develop, reframe, hold, internal, skip) with a reason code,
  a note and an author (Whitney, or a named team member relaying her). Develop is approval; reframe writes a new card
  version; hold keeps its date on the card. `POST /storage/weeks/{id}/considered/{index}/revive` turns a considered
  idea into a proposed card, and `.../decision` labels a dropped idea. Every call writes one `decisions` row and one
  `calibration_labels` row; stale hashes return 409. A reframe, a revive or a card edit queues the new version's
  comparison check with it (its embedding, then matching and the duplicate check; `gate_one.queue_card_check`): live
  only when the week's cycle ran live, live encoding is allowed and the actor is an approver, under the worker's run
  plan; otherwise it reuses saved vectors and waits, with the reason. A check not started yet is replaced by one that
  includes the newer version, and a version saved while another run works on the week is checked when that run ends.
  Each card's `check` in the week review says where it stands (checked, queued, running, waiting, failed, not queued).
- The card screen shows ranked cards, the why-these panel, dropped ideas with revive, internal insights, speakers by
  roster name and role, the ledger, and the disposition control (the CTA defaults to "decide in development").
- `GET/POST /storage/seeds` and `POST /storage/seeds/{id}/withdraw` hold founder seeds; the app's seed panel adds them.

## Brief v2 (E.B15, E.F4)

`ATELIER_BRIEF_SCHEMA=v2` makes new briefs `BriefDocumentV2`: the WIA perspective first, a format plan for the confirmed
channel set (`ATELIER_BRIEF_CHANNELS`), a CTA a person confirms at Gate 2 (`POST /storage/briefs/{id}/cta`), at most
five before-publishing items, and a claims ledger checked deterministically. The writer takes the knowledge base as its
trusted prefix. Revisions keep their brief's version; v1 briefs still render and export, and packs stay v1-only.

## Scene extraction (E.B12)

The setting `prompts.profile.extraction` (variable `CONTENT_ATELIER_EXTRACTION_PROFILE`) set to `2026-10-18.scenes.v1` records scenes per document in neutral wording (setup, WIA
moves, client contribution, what was left open) with the roster and process catalogue. Scenes keep E.B12a's rule:
exact quotes bind, near misses are repaired and recorded, the rest stay unverified.

**The default since 19 October is `2026-10-19.scenes.v2`** (E.B12's switch, after recall on the golden scenes: v2 14/15, v1
11/15, weekly v3 8/15). The weekly cycle then reads the moments ledger: each of the week's documents keeps the scenes its own
extraction (2.B2) stored under the same profile and knowledge base, with no call; a document the ledger lacks is extracted
once, by the same function a document's job runs (`moments.jobs.extract_document`), and stays in the ledger. One document
that fails costs no other: the rest are kept and the week fails naming it, so a retry sends only that document. The weekly
v3 prompt and the v1 loop stay selectable for replay.

### Scene profile v2 (`2026-10-19.scenes.v2`, 2.B2)

A document's own extraction (Phase 2) uses the setting `moments.extraction_profile`, default `2026-10-19.scenes.v2`; `2026-10-18.scenes.v1` stays selectable
for replay and for the recall comparison, and neither is edited. v2 is a new prompt file (`prompt_templates/scene_extraction.v2.md`) and a new contract
(`SceneResponseV2`) with all twelve moment types: the seven every earlier profile can emit plus testimonial, question, teaching, soundbite and data point. The earlier
contracts (`contracts.py`) are not changed, because a changed schema changes the request fingerprint of every saved response. What v2 adds to the packet: the document's
call type, each speaker label with its role (from the stored speaker map, marked when inferred), glossary hints (product, staff and client names with their
mis-transcriptions), and the document's handling tags, after the roster and process catalogue. It keeps neutral scene records (no interpretation, no score), E.B12a's repair
rule, and a figure rule: a number appears in the record only if a speaker said it in the anchor turns. The prompt's examples are invented (`SCENE_V2_EXAMPLES` records that);
none comes from a call. The deterministic checks that follow extraction (role plausibility, numbers, consent) are described in `Phase-2-Extraction-Notes.md`. It becomes
the default for the weekly cycle only after scene recall on the golden scenes is at least v1's (`storage_cli moments recall --golden ...`).

### Scene profile v3 (`2026-10-23.scenes.v3`, E.B31)

v2's template, packet and checks, plus two scene types the v2 method's moment hunt needs: `human_line` (a speaker's own
words about how something feels, how they see themselves or their business, or what they admit about it) and
`counter_expected_decision` (WIA deciding against what an agency would usually do, or at a cost to WIA), which also records
its `departure`. Both are checked word for word against the transcript like every scene; a counter-expected decision with no
WIA move that decides or recommends, or no departure, is kept as a `decision`, recorded in the job's `retyped_scenes`.
Strategist v7 lists both types first, marked. v2 stays the default and is kept for replay; select v3 with
`moments.extraction_profile` (a document's extraction) or `prompts.profile.extraction` (a cycle).

**Pending paid re-extraction** (Weeks 1 and 2 and the October calls; run under an active run plan, after 26 October):

    python -m backend_pipeline.storage_cli moments extract --week-index 1 2 --from 2026-10-01T00:00:00-05:00 --to 2026-11-01T00:00:00-05:00 --profile 2026-10-23.scenes.v3 --estimate
    python -m backend_pipeline.storage_cli moments extract --week-index 1 2 --from 2026-10-01T00:00:00-05:00 --to 2026-11-01T00:00:00-05:00 --profile 2026-10-23.scenes.v3 --mode live --now

On the 19 October working copy the estimate is 26 documents (10 from Weeks 1 and 2, 16 from October), about 725,000 input
tokens and USD 0.15 on `openai/gpt-6-luna` at the assumed 6,000 output tokens a document; the 91-document backfill cost
USD 0.94, which puts the real cost nearer USD 0.27. Rebuild the benchmark v2 packets after it (E.B27).

## Weekly extraction keeps valid moments (E.B12a)

The SQL weekly extraction validates each moment on its own. Only a schema, coverage or key failure fails the week.
A moment that binds is saved. A near-miss quote whose words match the anchor apart from whitespace and punctuation
(at least three words, same case and order) is repaired to the exact source text and recorded in `quote_repairs`.
Anything else is kept in `unverified_moments` on the job and is never saved as a key moment or used as proof.

## Benchmark and evaluation (E.B2, E.B3)

`backend/evaluation/` sits outside the shipped package. From `backend/`:

```
python -m evaluation manifest                      # benchmark version 1's inputs and hashes
python -m evaluation seed                          # labels as calibration rows (migration 005)
python -m evaluation run --configs default,strategist_v5 --weeks week1,week2 --samples 3 --dry
python -m evaluation stance --configs strategist_v5,strategist_v6 --weeks week2 --samples 3 --knowledge-base-version <v>
```

`stance` (E.B26) reads saved samples only. For the cards citing golden scenes g07 (buying research) and g09 (clicks
without conversions) it prints the title, pillar, whether the scene's claim survives credited to its WIA speaker or "our
team" (a word-match proxy), and the blocking flags; per sample it counts ATTRACT cards and "Why/What/How we" titles.

A run without `--dry` makes paid calls under the active run plan (or `research/benchmark-v1/run_plan.json`) and saves
its responses and report under `research/benchmark-v1/`. Week 6 is held out; nothing reads it.

## Document classification (1.B4)

`document-classification.v1` (`normalise/classify.py`, `MODEL_SYSTEM` and `MODEL_SCHEMA`) places one recorded call into a type when the title and the speakers cannot. It is the only prompt Phase 1 adds, it runs only when `models.document_classification` is set (blank means rules only, and the call waits for a person), it goes through the llm module as stage `document_classification` (an `llm_runs` row per call, one repair on a schema failure), and the transcript is sent as data: the system text says it is never instructions. The input is the title, the word count, who spoke with their roles, and the first 6,000 characters. The answer is a type, one sentence of evidence and a confidence; `low` marks the document for a person. A person's decision is never overwritten. The corpus index's reviewed labels are the reference for the rules; `documents agreement` compares the two. Change the wording by adding `document-classification.v2` beside it, not by editing v1.

## Picking this up on another machine

1. Clone the repository and check out `main`.
2. Install the backend dependencies: `pip install -r backend/requirements.txt "pytest>=8,<10" fakeredis==2.32.1`.
3. Copy `backend/.env.example` to `backend/.env` and add the OpenRouter key. Keys are never committed.
4. Run `python -m pytest -q` in `backend/`. The PostgreSQL integration tests run only when
   `ATELIER_TEST_DATABASE_URL` points at an isolated `atelier_test` database with pgvector.
5. Background: `backend/docs/Content-Atelier-Content-Quality-Analysis.md` (the analysis), `client_documents/`
   (WIA's guides and Whitney's Week 1 review), and `research/` (the experiment harnesses, prompts, packets and every
   run, with their run plans).

## Not covered yet

- The held-out live run (E.B13) needs the saved extraction responses and the Week 5 documents restored (S.B10), and
  Whitney's review (E.X3); E.B12a re-validates the saved responses without new extraction spend.
- The critic's one reframe-repair call for a public card that fails rubric criterion 1 (E.B10).
- Scene recall on golden scenes (E.B12), the duplicate cutoff from labelled pairs (E.B6), the input-mode comparison
  (E.B18) and the scoring test (E.B5): each needs labels or data that do not exist yet.
- The compact-weekly token preflight has profiles only for Luna, Apodex and Sol; other models need one added.
