# Checks on the developer's handover (19 October 2026)

The handover `2026-10-19` (Data-Handover-Runbook step C) was restored on the owner's machine: database `restored_atelier`
(counts as in Jainil's report: 170 transcripts, 2,657 chunks and embeddings, 14 moments, 13 angles, 2 briefs), migrated to
008, embedding contract check passed; 3,410 artifacts copied and read back. Every check here ran on a copy of it
(`atelier_work`) with no OpenRouter key in the environment: **no provider call was possible, and none was made**
(`llm_runs` stayed empty). Reviews below were made by the implementing engineer under D12 (R55: delegated, not WIA's).

## S.B10 and E.B12a: the saved Week 1 and 2 extraction responses

`moments import-saved` matches each meeting of a saved weekly response to the stored transcript that says exactly those
turns and checks each moment alone with E.B12a's rule (a quote that binds is kept, the rest are unverified records).

| Response | Model, prompt | Then | Re-checked now (no call) |
| --- | --- | --- | --- |
| Week 2, `024e8c…` (`run_f92042c8…`, the weekly run's) | GPT-6 Luna, 2026-10-08 weekly v3 | validated | 11 of 11 meetings matched; **6 of 6 moments bind** |
| Week 1, `4deaf2e…` (`week1-gpt6-luna-generation-only-20261008-a3`) | GPT-6 Luna, 2026-10-08 weekly v3 | **failed whole**: "Moment quote must match an existing anchor span" | **7 bind, 2 unverified** |
| Week 2, `ec84d6…` (`week2-luna-pro-strategic-20261013-a1`) | GPT-6 Luna Pro, strategic discovery v1 | failed whole, same error | 5 bind, 2 unverified |

Week 2's saved extraction replays as stored, and a Week 1 response that the old all-or-nothing check threw away yields every
moment that binds: S.B10's and E.B12a's done-whens. The other legacy attempts are free-model trials or older contracts
(`import-saved-dry-legacy-failed.json`).

Imported into the ledger: one response a week, the one each week's run used (Week 2 `024e8c`, Week 1 `4deaf2e` with
`--include-failed`). Every bound scene is the weekly path's own row (the same identity); it was left as it was and gained an
`also_extracted_by` note with the import's provenance. Week 1's two quotes that do not bind are unverified records, never proof.

Found and repaired on the way (each with a test that fails before it): the importer hashed a moment over one document while
the weekly path hashed over the week, so the same scene got two IDs; a stored row without `discovery` was taken as different
evidence from the same moment with `discovery: null`; re-noting another extractor's row changed its currency; failed
attempts could not be re-checked from the files (`--include-failed`).

## 0.B4: replay of the saved artifacts

`python -m backend_pipeline.llm.replay_check <artifact root>`: for every cached artifact, the key is recomputed from its
recorded request with today's recipe, the store's replay lookup serves it, and the output is re-hashed. No provider exists.

| Store | Artifacts | Key recomputed | Output hash identical |
| --- | --- | --- | --- |
| `.storage-artifacts` (SQL path, both v1 brief runs) | 18 (2 weekly, 16 brief stages) | 18 | 18 |
| legacy file datastore | 3 (angle generation) | 3 | 3 |

The weekly artifacts of 8 to 12 October were keyed under validator version 3 (today's is 4). The key names the validator
deliberately, so they are served only after a re-check under today's rules, which is E.B12a's path above. A whole Week 1
run cannot be rebuilt request for request: its 8 October prompt profiles are archived and not selectable, so the requests
the product builds today are new requests. The pinned-key test in `test_llm_module.py` ended in `or True` and pinned
nothing; it now pins the value.

## S.B4: the two v1 briefs, re-validated

`scripts/revalidate_v1_briefs.py` rebuilds each v1 brief's dossier from its row (what Gate 2 reads) and runs today's
deterministic `checks()`; no model call. Result: `sb4-v1-brief-revalidation.json`.

Gone since the briefs were made (the N2 false positives): "Prior coverage differences must cover each supplied historical
argument" and "Numerical prose requires a structured source-bound claim" on both briefs.

Two more false positives were found and repaired in `briefs/validation.py` (tests in `test_phase_s.py`):

- **"Claim status exceeds the source status"** on Week 2's C1, C2 and C4 was computed from the placeholder `reported` that
  `checks()` substitutes for an invalid prose status; C2's own status reads "Planned proposal" on planned evidence. A claim
  already blocked for its status is no longer compared with its sources.
- **"Source qualifications were lost"** on Week 2's C2 was an exact-string match: the claim widened the caveat ("no client
  adoption, response rate, messaging change or marketing result is reported"). A qualification now counts as carried when
  every content word of it is stated; dropping part of it still blocks.

What remains is judged correct:

| Brief | Blocking finding | Judgement |
| --- | --- | --- |
| both | "Claim status must be one of …" on every claim | Correct: the briefs store prose statuses written before the six-value enum ("reported; private; excluded from public deliverables"). A person must restate them before approval. |
| both | "Unresolved consent requirements must be cleared" | Correct: each brief lists consent requirements nobody has cleared. |
| Week 2 | C1 "Source qualifications were lost" | Correct: C1 cites the survey passages and carries neither of their caveats ("not confirmed as implemented or currently offered"; its "no adoption or marketing result is established" drops response rate). |
| Week 2 | C4 "Source qualifications were lost" | Correct: C4 drops "shared spreadsheet" and "not … currently offered". |

**No false positive remains.** The warnings are expected: exemplar keys in `prior_differences` (exemplars travelled in the
dossier then), and the incomplete legacy publication catalogue.
