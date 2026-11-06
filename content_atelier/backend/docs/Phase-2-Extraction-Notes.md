# Phase 2 extraction: hand-over notes

Covers 2.B2 (per-document extraction), 2.B4 (deterministic checks), 2.B9 (Slack triage), 2.B10 (import of saved Week 1 and 2
moments) and 2.B11 (the backfill command, the report, golden-scene recall). Search, embeddings, the moments API and topics
(2.B5 to 2.B8) are a separate piece of work and are not described here.

## What was built

| Module (`backend_pipeline/`) | What it does |
|---|---|
| `moments/scenes.py` | Scene profile v1 (unchanged) and the new `2026-10-19.scenes.v2`: its contract (`SceneResponseV2`, twelve moment types), prompt file (`prompt_templates/scene_extraction.v2.md`) and packet (roster and process catalogue, call type, speaker roles, glossary hints, handling tags). The provenance of the v2 prompt's examples is `SCENE_V2_EXAMPLES` (all invented). |
| `moments/extract.py` | `partition_scenes`: one document's response checked as a whole (schema, delivered-meeting coverage, unique keys, not empty without a reason: a failure is a repairable `SchemaViolation`), then scene by scene with E.B12a's rule (exact, repaired and recorded, or an unverified record). |
| `moments/jobs.py` | The `moment_extraction` handler for one document. Dispatched from `SQLWorker.execute` for a job that names a `transcript_id`; the weekly per-run path is unchanged. |
| `moments/queue.py` | `queue_extraction` (the run and one job per document), `estimate`, `pilot`, `require_plan`, `settle_run`. |
| `moments/store.py` | The one ledger writer, used by the weekly paths and the document job. Also the currency rules (`settle_currency`, `align_currency`). |
| `moments/checks.py` | Pure functions: role plausibility, number check, consent. |
| `moments/recheck.py`, `report.py`, `recall.py`, `imports.py`, `cli.py` | `moments recheck`, `report`, `recall`, `import-saved` and the command group. |
| `normalise/classify.py` (`triage_slack`), `documents/jobs.py`, `documents/slack_export.py` | Slack triage (2.B9). |

Small edits elsewhere, all additive: `repository.py` (`save_moments` delegates to the writer; `claim`, `finish` and `fail` settle a
document run, and `mark_extraction` is per document for a job that names one), `sql_pipeline.py` (the dispatch line; the two weekly
paths pass their extractor version, unverified records and repairs to the writer), `cycle/verification.py` (`digits_in` and
`figures_in`, shared with the number check; `verify_card` uses `digits_in`, behaviour unchanged), `llm/providers.py` (the offline
`FakeProvider` answers a scene schema with an empty, explained result), `costs.py` (the price table), `settings_store.py`
(six settings), `storage_cli.py` (one registration and one dispatch line), `DEPLOYMENT.md` (the settings rows and a runbook block).

## Per-document extraction (2.B2)

* `queue_extraction` creates a run with `run_scope = 'document_extraction'` and no week, and **one `moment_extraction` job per
  document** (`transcript_id` set, `queue` named by the caller: `bulk` for a backfill, `default` for a cycle). The idempotency key is
  the stage, the document, its content hash, the extractor profile and the knowledge base's stable refs (version, manifest and
  identity documents; not the dated roster items). Asking again for a document that has a job reports it (`skipped`: completed,
  failed, queued) and creates nothing; `--retry-failed` queues a failed job again.
* The run freezes the documents (id, hash, view hash), the profile, the extraction model and the knowledge base. The handler refuses
  a changed document, model or knowledge base before spending anything.
* One failed document fails its own job. `settle_run` keeps the run `running` while any job is open, then `completed`,
  `partially_completed` or `failed`; a failed job can be retried (`repo.retry`) on its own.
* A re-run makes no provider call: the handler stops when a completed job or a stored moment already carries this extraction's key,
  and the call itself is keyed by its request, so a saved validated response is reused whatever the job.
* **Identity and extractor versions.** A verified moment's ID is `Pipeline._moment`'s content hash, so extracting the same scene
  again stores nothing. The same scene from two extractors is **one moment** (`checks.also_extracted_by` names the others, with their
  provenance), and `moments report --extractor` and `moments recall --profile` count it for each. A document extracted under a
  newer extractor has its older moments set `is_current = false` (never deleted); extractor versions order by their date prefix
  (`imported:<profile>` by the profile). A newer extraction that found nothing it can prove retires nothing. An extraction under an
  older extractor than one already stored is stored not current.
* An unverified record has ID `unverified_<md5(<document>:<extractor>:<local key>:<draft hash>)[:24]>`, `evidence_refs = []`, a reason,
  and is never embedded or proof (`quote_verified = false`). The two weekly paths still keep theirs in the job's `result_refs`
  (E.B12a, and an existing test says so); passing `unverified=` to `repo.save_moments` there would store them as rows too, a
  one-line change for the integrator once the weekly paths are retired in favour of the per-document job.
* Zero scenes is a valid outcome if the response says why (`coverage_notes`); the document is `completed` and listed by the report.
* The structured scene (setup, WIA moves, client contribution, left open) is kept in `checks.extraction.scene`, with the artifact
  and request fingerprint. `moment_body` holds the compact moment shape the strategist stage already reads.

## The checks (2.B4)

| Check | Rule | Stored in |
|---|---|---|
| Role plausibility | A `result` or `testimonial` spoken by anyone but a client or prospect gets `evidence_kind = team_report`. A `testimonial` by anyone else is retagged `observation`; the model's tag stays in `moment_body.moment_type` and `checks.role_plausibility.original_type`, and the stored type is always re-derived from it. A speaker the roster cannot place (`unknown`) is treated as a relay. | `evidence_kind`, `moment_type`, `checks.role_plausibility` |
| Numbers | Every figure in the quote, setup or record (`cycle/verification.figures_in`) must appear in the **anchor** passages' text (`digits_in`). Absent figures are listed (`absent`) and fail; a figure only in the surrounding context is listed (`context_only`) and also fails. Spelled-out counts are not figures, as in the card check. The record's `Process step:` label is ignored. The moment stays stored; consumers read `passed`. | `checks.numbers` |
| Consent | `do_not_use` if the client is `no_use`; else `internal_only` if sensitivity is `internal_only`; else `cleared` only if the client is `may_name`, sensitivity `public_candidate` and evidence `direct_quote`; else `anonymise`. `test_the_python_rules_and_migration_008s_sql_agree` runs migration 008's own statements over 240 combinations and compares. | `consent_status`, `checks.consent` |

The speaker is the speaker of the anchor passage **that holds the quote** (migration 008 promoted old moments by their first
anchor; the two agree for single-anchor moments, and `moments recheck` brings the rest in line). A document with no speaker map yet
falls back to the roster (`checks.fallback_role`): staff if the roster knows the name, otherwise `unknown`, never `client`.

`moments recheck [--ids ... | --document ... | --client ...] [--dry-run]` re-derives speaker, role, client, date, type, evidence kind,
consent and the derived checks from each moment's own record and evidence, after a document is normalised again or a client's
consent changes; it keeps provenance keys, never touches the quote, evidence, body, version or vector, and is idempotent.
Normalisation (for the document it normalises) and `documents clients import --update-consent` (for a client whose consent
changed) run the same derivation in their own transaction, so the command is needed only after a direct database change.

A document that is excluded (by a person, a rule or triage) has its moments set not current (`align_currency`, from
`normalise`); including it again brings the newest extractor's back.

## Slack triage (2.B9)

At normalisation, a `slack_thread` document is excluded with a visible reason and `classification.triage = {rule, version}` when:
its channel is excluded (`documents.slack_export.excluded_channels` by name, or a `slack_channels` row with `included = false`);
every message is a join, leave or channel-housekeeping line; every speaker is automation (`documents.slack_triage.bot_names`, or a
name ending in "bot"); or the thread says fewer than `documents.slack_triage.min_words` words, default 3 (links, mentions, emoji and
punctuation do not count: "Lunch?" and "ok thanks :thumbsup:" go, "Wedding inquiry follow-up improved." stays; five was tried and
dropped a four-word statement of a result). A person's decision (`classification.method == 'person'`) is never triaged, in either direction. The Slack
export import also drops a message that carries a `bot_id`. An excluded document is `not_applicable`, is never returned by the
selection helpers and `queue_extraction` refuses it by name, so it has no job.

## Commands

```bash
# What would it cost? Nothing is sent. Prints documents, input tokens, the price used, the cost estimate and the input-set hash.
python -m backend_pipeline.storage_cli moments extract --pilot 10 --estimate
# A plan for exactly those documents (the hash comes from the estimate), then the pilot on the bulk queue. Live is refused without it.
python -m backend_pipeline.storage_cli plan create --purpose "moments pilot" --stage moment_extraction --model <model> \
    --input-set-hash sha256:<from the estimate> --max-calls 20 --max-cost-usd 2 --approver <email>
ATELIER_RUN_PLAN_ID=<plan id> ATELIER_ALLOW_GENERATION=true python -m backend_pipeline.storage_cli moments extract --pilot 10 --mode live
python -m backend_pipeline.storage_cli moments report                     # a person reads the pilot and this
python -m backend_pipeline.storage_cli moments extract --all-pending --mode live      # then the backfill (its own plan and hash)
python -m backend_pipeline.storage_cli moments extract --ids <id> ... --mode cached   # replay saved responses only: never a call
python -m backend_pipeline.storage_cli moments extract --from 2026-03-09T00:00:00-05:00 --to 2026-03-16T00:00:00-05:00 --queue default
python -m backend_pipeline.storage_cli moments recheck --client <client id>
python -m backend_pipeline.storage_cli moments recall --golden golden.json [--profile 2026-10-18.scenes.v1 2026-10-19.scenes.v2]
python -m backend_pipeline.storage_cli moments import-saved <saved artifacts folder> --dry-run
python -m backend_pipeline.storage_cli moments import-saved <saved artifacts folder> --actor <email>
```

`--pilot N` takes N of the selected documents (default selection: all pending) spread over the call types: types in name order,
each type's documents oldest first (undated last), one from each type in turn. `--mode live` needs `ATELIER_ALLOW_GENERATION=true`,
models set explicitly (section 4.10), the knowledge base free of held-out text, and an active plan that covers the stage and model,
is bound to this run's input set (or to `*`) and has a call left for every document. The estimate's input tokens are the prompt each
document would send at about four characters a token, beside the conservative one-token-a-byte allowance the card preflight uses;
output tokens are the assumption `moments.estimate.output_tokens_per_document` (reasoning included) until the pilot measures them.
`--now` runs the jobs inline instead of leaving them to the queue workers.

`moments report` gives: stored, verified and unverified moments and the **verified-quote share**; quote repairs; the number
check's checked and failed counts; role, type, evidence-kind and consent distributions; the same per call type; documents by
extraction status and the documents extracted with zero scenes; and the invariants
(`no_current_moment_for_an_excluded_document`, `no_open_extraction_job_for_an_excluded_document`). `ok` is false, and the offending
documents are named, if one breaks. `--extractor` reports one extractor version.

## Importing the saved Week 1 and 2 moments (2.B10)

`moments import-saved <folder>` reads every validated `moment_extraction` `StageArtifact` JSON under the folder (the file runs'
`<run>/moment_extraction.json`, `service_calls/<fingerprint>/attempts/<id>/artifact.json`; pointers, failed attempts, other stages
and an artifact whose output no longer matches its hash are ignored; one per request fingerprint). It parses the weekly packet in the
artifact's request and matches each meeting to the stored document whose passages say **exactly those turns** (content, not path).
A meeting with no document, an excluded document or a copy is reported and skipped. Each meeting's moments are resolved against its
document alone and checked one by one. Rows get `extractor_version = imported:<original prompt profile>`, `week_id` of the
document (null for a week-less one), no run, and `checks.imported_from` = artifact, request fingerprint, original run, prompt
version, model, meeting, local key, match, the document's content hash and upstream id, importer and time. A moment the SQL weekly path already stored is left as it
is, with the import noted in `checks.also_extracted_by`. No provider is touched and no `llm_runs` row is written; importing again
stores nothing. The tests generate synthetic artifacts in this format (`tests/test_moments_import_db.py`).

## Golden file format (`moments recall --golden`)

```json
{"version": 1, "name": "funktastic-chain",
 "scenes": [
   {"id": "g1",
    "document": {"transcript_id": "transcript_...", "content_hash": "...", "title": "..."},
    "anchor": "an exact or near-exact phrase the scene is built on",
    "kind": "quote",
    "min_overlap": 0.6,
    "note": "why a person marked it"}]}
```

`document` names the document by any one of `transcript_id`, `content_hash` or `title`. `kind` is `quote` (default) or `paraphrase`
(`min_overlap`: the share of the anchor's content words found, default 0.6). A scene is **found** when a verified moment of that
extractor quotes the anchor (either contains the other, ignoring case, spacing and punctuation), has an anchor passage containing it,
or (paraphrase) covers enough of its content words. It is **lost to a quote mismatch** when the match exists only among the
unverified records. The result gives recall per extractor version, which scenes each found, the lost and the missed ones. With no
`--profile`, every extractor version stored for the golden documents is compared, so v1 and v2 are measured on the same scenes.

## What needs real data or a person (not done here)

* **S.B10:** the real transcripts, the real Week 1 and 2 artifacts and the production database are on another machine. Run
  `import-saved --dry-run` there first and read what it matched.
* **The pilot:** 10 documents extracted under a run plan and **read by a person** (2.B11's gate), then the backfill's own plan; the
  verified-quote share and role distribution recorded from `moments report`.
* **The golden scenes:** the Funktastic chain and the benchmark weeks' golden scenes are listed by a person in the format above; scene
  recall of v2 against v1 on them (Phase 2 exit: "at least the previous prompt's"; E.B12's default switch).
* **The live preflight:** a live call is sized against the model's saved public route (`python -m backend_pipeline.token_budget --model
  <model> --store` caches it in the artifact store the workers read, the bucket on the platform), as the weekly extraction is; do it once in the production environment before the pilot.
* **Output token assumption** for the estimate, replaced by the pilot's measured usage.
* **Real client consent** values come with the reviewed client list (1.B2); until then every client is `anonymise_only`, so nothing is `cleared`.

## Known limits

* Fixed in the verification of 19 October (0.B5): a document run, extraction or an import's normalisation, is as finished as
  its jobs (`jobs.policy.PER_DOCUMENT_SCOPES`, `moments.queue.settle_run`): a failed or lost document fails its own job and
  the run's other documents are still claimed.
* Spelled-out numbers ("three") are not checked (the card check does not either); `$5k` against `5,000` compare by digits and disagree, as they do in the card check.
* The shared `atelier_test` database stays at the baseline schema for the older suites; the writer falls back to the pre-008 columns there (`store.has_ledger`). Every migrated database takes the full path.
