# NP.X1: the free-model shakedown of the pack path (24 October 2026)

The content-packs plan's section 7.1, as the main plan's section 5.0c applies it. **Scratch copy A** (`atelier_np_a`) is
production's nightly dump of 24 October 08:16 UTC (`backups/db/atelier-20261024T081611Z.dump`). Its counts matched the
dump's manifest: 41 tables and 12,632 rows. It ran in N1's stack, the production images in backend mode with every
worker of the production order (`research/packs-2026-10/np5/compose.np5.yml`).

**Models.** The finisher and the repair used `nvidia/nemotron-3.5-super-vl:free`. The check and the re-check used
`dots-studio/dots-3-note-preview:free` (`backend/deploy/shakedown-settings.json`), applied after the configuration of
record.

**Key and spend.** The calls went on the Client key, whose account allows free endpoints. **USD 0** was spent; every pack
call cost 0. The internal key's account refuses free endpoints (finding 4).

The model outputs' quality is irrelevant here; these runs are "pipeline path, not model quality". No prompt, schema,
check or retry was changed on free-model evidence alone (K70).

## The path covered

1. **Migration 009** applied by the stack's `migrate` service on copy A: `migrated`, version 009.
2. **N2's three briefs taken through Gate 2** with `gate2.py` and `gate2-actions.json`, the same file the paid proof and
   production use. The steps were the team's edits, the CTAs confirmed as proposed, the before-publishing answers (the
   client's permission as a before-posting note), the claims check and the approval. Each approval started its pack
   live, under the `packs` budget.
3. **Every pack reached review.** Each one assembled, finished, was checked, repaired, re-checked and finalized:

   | Brief | Check | Repair | Re-check | Finalize |
   | --- | --- | --- | --- | --- |
   | Brief 1 | 0 of 60 flagged | none needed | — | in review |
   | Brief 2 | 4 of 47 flagged | 4 applied | nothing left | in review |
   | Brief 3 | 7 of 37 flagged | 7 applied | 3 left | 1 put back into a piece the brief had; 2 open blocking findings on the written stance Reel |

   On brief 3, Ready was blocked by those two findings, named in plain words.
4. **The review flows through the API:**
   - An attestation cleared one finding, and an edit of the flagged sentence cleared the other, which also locked the line.
   - An edit with a stale hash was refused (409 `stale_pack`).
   - A revert of a line already as the brief wrote it answered "nothing changed". That line was written at Gate 2 and
     is locked.
   - Marking a before-publishing note done updated the version in place, outside the manifest.
   - Ready was bound to the manifest, with the client-permission note still listed and not done.
   - Marking a piece published left the pack `ready_to_publish` and wrote its `published_content` row. A future
     publish date was refused.
   - The week plan proposed one Tuesday email, three Instagram pieces with one offer post, and a bank of 11.
   - The week's pack document exported (80,645 characters).
5. **Finish again on brief 1's pack** assembled from the current pack (5 of 5 pieces). It finished, then was checked,
   repaired and re-checked: 44 of 140 flagged, 21 repairs applied, 5 patches not found and recorded, 15 settled at
   finalize.

## The failure cases

| Case | What happened | Result |
| --- | --- | --- |
| A spent budget | `packs` call cap set to the calls used (13), then Finish again | The finish step waited with "This week's content packs budget has used all 13 calls it allows, so the next call was not sent...", on the job and on the pack (`state_reason`). Raising the cap released it with no command |
| A worker killed mid-finish | `docker kill` of the editorial worker while the free finisher was answering | Once the lease expired, the step failed visibly ("The worker stopped while this step was running, after it sent a model call whose answer was not saved..."), shown on the pack; the orphaned call was closed as failed. A retry finished the pack |
| A missed patch | Arose by itself in the Finish again run | 5 patches whose old text was not in an unlocked flagged line were dropped and recorded as `missed_patch` |
| A malformed answer | Not provoked: both free models answered every pack stage within its contract | The repair path is covered offline (`llm/workflow.chat`, one repair call) and by the NP exit test |
| A 402 | Not provoked on a live key | Covered by the NP exit test (`test_np_exit_a_provider_refusal_for_credit...`) |

## Findings

Each finding was triaged as in N1's ledger. A pipeline defect was fixed at its cause, with a test that reproduces it
without a free model.

| # | Finding | Kind | Fix |
| --- | --- | --- | --- |
| 1 | Every pack's second stage failed: "Frozen pack execution contract changed". The frozen knowledge-base refs held tuples, which come back from the database as lists. It shows only against a database-backed knowledge base, which the offline tests do not use | Pipeline defect | `runtime_v2.stable_contract` compares as JSON, with the knowledge base reduced to its stable refs. Test `test_a_frozen_execution_contract_still_matches_after_the_database_round_trip` (`9fcf212`) |
| 2 | `storage_cli budgets set` listed six purposes by hand, so the packs cap could not be set (production's included) | Pipeline defect | The choices come from `standing.PURPOSES`. Test `test_budgets_set_accepts_the_packs_purpose` |
| 3 | Brief 2's Gate 2 clearance of Whitney's quotation was refused: "Upstream source restriction cannot be overridden by a brief". Every October call carries the collector's `public_use: false`, so no quotation of the team's words from it can ever be cleared. The finisher could have quoted Whitney and met a blocking finding no one could clear | Design defect (data rule) | Hand-off view v2 marks each evidence item `quotable`: a client's words always (a before-posting note), the team's only with public use or a clearance. The finisher tells the rest in reported speech, and brief 2's Gate 2 edit turns the quotation into reported speech in her voice. Test `test_the_team_s_words_are_quotable_only...` |
| 4 | The internal key's account refused free endpoints. The message named the paid policy, though the request was sent under the free one | Free-model artefact (an account setting, the owner's), plus a wording defect | The shakedown used the Client key; nothing changed in the account. `routing.raise_for_routing` now names the policy the request was sent under. Test `test_a_refused_free_request_names_the_free_policy_it_was_sent_under` |
| 5 | After the finisher prompt changed (finding 3), the runs frozen before it failed as "changed" on every retry, and creating the pack again only retried them | Pipeline defect | `queue.create` replaces a run stuck on a changed contract with a new run, as it does for a mode switch. Assembly starts from the brief when the replaced pack never finished. Test `test_a_pack_stuck_on_a_changed_contract_gets_a_new_run_from_the_brief` |
| 6 | The local Command Center image was built before S.C1, and its sign-in hand-off needs production's SSO configuration | Local stack only | Not changed. The screens were exercised through the API here, are unit-tested (NP.F1 to NP.F4), and are checked on production (NP-6) |

**Found before the shakedown, each fixed with a test:**
- NP.X2a's capped call: the live provider refused every pack stage.
- The NP exit test: the finisher's packet dropped the carousel's title, and `StageArtifact` refused the v2 pack stages.
- The full offline suite: an import-order-dependent OpenAPI enum, and the finisher prompt sharing an eight-word run with
  the judge (K45).

## Exit

No unclassified finding and no open pipeline defect remain. Each core fix has a test that reproduces it without a free
model. The exit holds.
