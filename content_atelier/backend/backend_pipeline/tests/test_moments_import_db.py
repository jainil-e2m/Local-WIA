"""Plan 2.B10: saved Week 1 and 2 extraction responses become ledger rows with their provenance, with no provider call and no
`llm_runs` row. The artifacts are generated here in the format the file-backed runs saved; the real ones are on the developer's
machine (S.B10). No network."""
from __future__ import annotations

import json

import pytest

from backend_pipeline.jobs.executor import run_job
from backend_pipeline.models import StageArtifact
from backend_pipeline.moments import imports, queue
from backend_pipeline.moments.scenes import SCENE_V2_PROFILE
from backend_pipeline.prompts import KEY_MOMENTS_WEEKLY_PREFIX
from backend_pipeline.store import canonical_hash
from backend_pipeline.tests.moments_fixtures import ScriptedProvider, import_documents, prepare_reference, standard_scripts
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)

WEEKLY = "2026-10-13.weekly.v3"


@pytest.fixture
def ready(platform_setup):  # noqa: F811
    repo, models, tmp_path = platform_setup
    prepare_reference(repo)
    return repo, models, tmp_path


def packet(documents, extra_meeting=False):
    lines = []
    for i, document in enumerate(documents, 1):
        lines.append("MEETING " + json.dumps({"source_id": f"m{i}", "filename_label": f"week1-{i}", "name": None}, separators=(",", ":")))
        for n, p in enumerate(document["passage_map"], 1):
            lines.append(f"m{i}.t{n:04d}|{n}+1|" + document["original_text"][p["start"]:p["end"]])
        lines.append(f"END_MEETING m{i}")
    if extra_meeting:
        i = len(documents) + 1
        lines += ["MEETING " + json.dumps({"source_id": f"m{i}"}), f"m{i}.t0001|1+1|Somebody: a call that is not stored", f"END_MEETING m{i}"]
    return "\n".join(lines)


def moment(key, ref, quote, kind="observation", first=None, last=None, **changes):
    value = {"local_key": key, "anchor_span_ids": [ref], "context_first_span_id": first or ref, "context_last_span_id": last or ref,
             "quote": quote, "context_summary": "Synthetic setup.", "moment_type": kind, "proposition": "A synthetic proposition.",
             "audience_relevance": "Synthetic.", "qualifications": [], "claim_status": "reported", "sensitivity": "public_candidate",
             "strength": 3.0, "reasons": ["Synthetic."],
             "discovery": {"lenses": ["audience_insight"], "destination": "public_opportunity", "wia_contribution": None,
                           "attention_reason": "Synthetic.", "research_questions": []}}
    value.update(changes)
    return value


def artifact_file(directory, documents, moments, *, extra_meeting=False, fingerprint="a" * 64, name="moment_extraction.json", **changes):
    meetings = [{"meeting_ref": f"m{i}", "first_span_id": f"m{i}.t0001", "last_span_id": f"m{i}.t{len(d['passage_map']):04d}",
                 "span_count": len(d["passage_map"])} for i, d in enumerate(documents, 1)]
    if extra_meeting:
        meetings.append({"meeting_ref": f"m{len(documents) + 1}", "first_span_id": f"m{len(documents) + 1}.t0001",
                         "last_span_id": f"m{len(documents) + 1}.t0001", "span_count": 1})
    output = {"moments": moments, "processed_meetings": meetings, "coverage_notes": []}
    values = dict(artifact_id="artifact_week1", run_id="week1-gpt6-luna-original", stage="moment_extraction", request_fingerprint=fingerprint,
                  prompt_version=WEEKLY, model_id="openai/gpt-6-luna", status="validated", input_hashes=["h"], output=output,
                  output_hash=canonical_hash(output),
                  request={"messages": [{"role": "system", "content": "S"},
                                        {"role": "user", "content": KEY_MOMENTS_WEEKLY_PREFIX + packet(documents, extra_meeting)}]})
    values.update(changes)
    artifact = StageArtifact(**values)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(artifact.model_dump(mode="json")), encoding="utf-8")
    return artifact


def saved_week(tmp_path, docs):
    """A saved Week 1 in the file store's layout, with the files around an artifact that an import must ignore."""
    root = tmp_path / "saved"
    a, b = docs["A"], docs["B"]
    moments = [
        moment("exact", "m1.t0002", "We had 45 bookings in March.", kind="result"),
        moment("near", "m1.t0004", "Lead Lock has helped a lot with the follow up", first="m1.t0003", last="m1.t0004"),
        moment("praise", "m2.t0002", "Dana loves the new inquiry form so much.", kind="result", first="m2.t0001", last="m2.t0003"),
        moment("bound-nowhere", "m2.t0003", "Nobody said this at all, ever.", first="m2.t0002", last="m2.t0004"),
        moment("crossing", "m1.t0002", "We had 45 bookings in March.", first="m1.t0002", last="m2.t0002"),
        moment("invented", "m1.t0002", "We had 45 bookings in March.", kind="result", context_summary="She booked 60 weddings"),
    ]
    artifact = artifact_file(root / "experiments" / "default" / "runs" / "week1-original", [a, b], moments, extra_meeting=True)
    # Files an import must not trust or read as artifacts.
    artifact_file(root / "failed", [a], [], fingerprint="b" * 64, status="failed", name="moment_extraction.failed.json", output=None,
                  output_hash=None, error="schema")
    (root / "cache" / "artifacts").mkdir(parents=True)
    (root / "cache" / "artifacts" / f"{artifact.request_fingerprint}.json").write_text(json.dumps({"artifact_path": "x"}))
    (root / "notes.json").write_text(json.dumps(["not", "an", "artifact"]))
    (root / "broken.json").write_text("{not json")
    other = artifact.model_dump(mode="json") | {"stage": "angle_generation", "request_fingerprint": "c" * 64}
    (root / "angle_generation.json").write_text(json.dumps(other))
    return root, artifact


def ledger(repo):
    with repo.connection() as conn:
        return conn.execute("SELECT * FROM key_moments ORDER BY moment_id").fetchall()


def test_saved_moments_are_imported_with_their_provenance_and_no_provider_call(ready):
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    root, artifact = saved_week(tmp_path, docs)
    with repo.connection() as conn:
        runs_before = conn.execute("SELECT count(*) n FROM llm_runs").fetchone()["n"]
    report = imports.import_saved(repo, root, actor="tester@example.invalid")
    assert len(report["artifacts"]) == 1, "only the validated moment-extraction artifact is read"
    assert report["provider_calls"] == 0 and report["unmatched_meetings"] == 1
    entry = report["artifacts"][0]
    assert [m.get("document_id") for m in entry["meetings"][:2]] == [docs["A"]["transcript_id"], docs["B"]["transcript_id"]]
    assert "no stored document" in entry["meetings"][2]["skipped"]

    rows = ledger(repo)
    assert len(rows) == report["moments"] + report["unverified"] and report["repaired"] == 1
    assert all(r["extractor_version"] == "imported:" + WEEKLY for r in rows)
    assert all(r["is_current"] for r in rows) and all(r["run_id"] is None and r["week_id"] is None for r in rows)
    exact = next(r for r in rows if r["moment_body"]["quote"] == "We had 45 bookings in March." and r["moment_type"] == "result"
                 and r["moment_body"]["context_summary"] == "Synthetic setup.")
    source = exact["checks"]["imported_from"]
    assert source["artifact_id"] == "artifact_week1" and source["request_fingerprint"] == artifact.request_fingerprint
    assert source["original_run_id"] == "week1-gpt6-luna-original" and source["prompt_version"] == WEEKLY
    assert source["model_id"] == "openai/gpt-6-luna" and source["local_key"] == "exact" and source["meeting"] == "m1"
    assert source["matched_by"] == "turn_text" and source["source_content_hash"] == docs["A"]["content_hash"]
    assert source["upstream_id"] == docs["A"]["upstream_id"] and source["imported_by"] == "tester@example.invalid"
    assert exact["document_id"] == docs["A"]["transcript_id"] and exact["speaker_role"] == "client" and exact["quote_verified"]
    assert exact["checks"]["numbers"]["passed"] and exact["sensitivity"] == "public_candidate" and exact["destination"] == "public_opportunity"
    assert exact["evidence_refs"], "the evidence resolves into the stored original"

    near = next(r for r in rows if r["quote_repair"] and r["moment_body"]["quote"].startswith("Lead Lock has helped"))
    assert near["quote_repair"]["original_quote"].endswith("follow up")
    praise = next(r for r in rows if r["moment_body"]["quote"].startswith("Dana loves"))
    assert praise["speaker_role"] == "staff" and praise["evidence_kind"] == "team_report" and praise["moment_type"] == "result"
    invented = next(r for r in rows if r["moment_body"]["context_summary"] == "She booked 60 weddings")
    assert invented["checks"]["numbers"]["passed"] is False and invented["checks"]["numbers"]["absent"] == ["60 weddings"]
    unverified = [r for r in rows if not r["quote_verified"]]
    assert {r["checks"]["local_key"] for r in unverified} == {"bound-nowhere", "crossing"}
    assert all(r["evidence_refs"] == [] and r["unverified_reason"] and r["checks"]["imported_from"]["request_fingerprint"] for r in unverified)
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM llm_runs").fetchone()["n"] == runs_before, "no llm_runs row: nothing was sent"


def test_importing_twice_adds_nothing_and_a_dry_run_writes_nothing(ready):
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    root, _ = saved_week(tmp_path, docs)
    dry = imports.import_saved(repo, root, apply=False)
    assert dry["applied"] is False and dry["moments"] > 0 and ledger(repo) == []
    first = imports.import_saved(repo, root)
    before = ledger(repo)
    again = imports.import_saved(repo, root)
    assert ledger(repo) == before, "the same rows, byte for byte"
    assert again["moments"] == 0 and again["already_present"] == first["moments"] and again["unverified"] == first["unverified"]


def test_a_moment_the_sql_weekly_path_already_stored_is_left_as_it_is(ready):
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    root, _ = saved_week(tmp_path, docs)
    imports.import_saved(repo, root)
    exact = next(r for r in ledger(repo) if r["moment_body"]["quote"] == "We had 45 bookings in March." and r["moment_type"] == "result"
                 and r["moment_body"]["context_summary"] == "Synthetic setup.")
    with repo.connection() as conn:
        conn.execute("UPDATE key_moments SET extractor_version='2026-10-13.weekly.v3',checks='{}' WHERE moment_id=%s", (exact["moment_id"],))
    again = imports.import_saved(repo, root)
    assert again["moments"] == 0
    stored = next(r for r in ledger(repo) if r["moment_id"] == exact["moment_id"])
    assert stored["extractor_version"] == "2026-10-13.weekly.v3", "the existing row is not rewritten"
    assert stored["moment_body"] == exact["moment_body"] and stored["evidence_refs"] == exact["evidence_refs"]
    # What is added is the note that the import also produced this scene, with the import's provenance, once.
    (also,) = stored["checks"]["also_extracted_by"]
    assert also["extractor_version"] == "imported:2026-10-13.weekly.v3" and also["imported_from"]["artifact_id"] == "artifact_week1"
    assert set(stored["checks"]) == {"also_extracted_by"}
    imports.import_saved(repo, root)
    assert next(r for r in ledger(repo) if r["moment_id"] == exact["moment_id"]) == stored


def test_an_imported_scene_has_the_id_the_weekly_path_gave_it(ready):
    """The weekly path hashed each moment over every source of its week; the import hashes over every matched document of the
    packet, so the weekly path's row for a scene is recognised instead of stored twice (the real Weeks 1 and 2)."""
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    a, b = docs["A"], docs["B"]
    moments = [moment("exact", "m1.t0002", "We had 45 bookings in March.", kind="result"),
               moment("praise", "m2.t0002", "Dana loves the new inquiry form so much.", kind="result", first="m2.t0001", last="m2.t0003")]
    artifact = artifact_file(tmp_path / "week", [a, b], moments)
    meetings = imports.parse_packet(imports.user_message(artifact))
    refs = {**imports.meeting_refs(meetings[0], a), **imports.meeting_refs(meetings[1], b)}
    week, _, _ = imports.reconstruct([a, b])
    resolved, unresolved = imports.resolve_moment_references_partial(artifact.output, refs)
    weekly = imports._Checker()._partition_moments(resolved, "weekly-run", week, unresolved=unresolved)
    report = imports.import_saved(repo, tmp_path / "week", apply=False)
    assert report["moments"] == 2
    imports.import_saved(repo, tmp_path / "week")
    assert {r["moment_id"] for r in ledger(repo) if r["quote_verified"]} == {m.moment_id for m in weekly.moments}


def test_an_import_leaves_another_extractors_rows_current(ready):
    """Real Week 2: the weekly path stored the same scenes (one identity) under a newer version, plus a scene this import does
    not reproduce. Importing notes the shared rows and never changes their currency."""
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    root, _ = saved_week(tmp_path, docs)
    imports.import_saved(repo, root)
    a = docs["A"]["transcript_id"]
    with repo.connection() as conn:
        conn.execute("UPDATE key_moments SET extractor_version='2026-10-14.weekly.v4',checks='{}' WHERE document_id=%s AND quote_verified", (a,))
        one = conn.execute("SELECT moment_id FROM key_moments WHERE document_id=%s AND quote_verified LIMIT 1", (a,)).fetchone()["moment_id"]
        columns = [r["column_name"] for r in conn.execute("""SELECT column_name FROM information_schema.columns
            WHERE table_name='key_moments' AND table_schema=current_schema() AND is_generated='NEVER' AND column_name<>'moment_id'""")]
        listed = ",".join(columns)
        conn.execute(f"INSERT INTO key_moments (moment_id,{listed}) SELECT 'moment_only_the_newer_extractor_found',{listed} "
                     "FROM key_moments WHERE moment_id=%s", (one,))
    newer = {r["moment_id"]: r["is_current"] for r in ledger(repo) if r["document_id"] == a and r["quote_verified"]}
    assert all(newer.values())
    imports.import_saved(repo, root)
    after = {r["moment_id"]: r for r in ledger(repo) if r["document_id"] == a and r["quote_verified"]}
    assert {k: r["is_current"] for k, r in after.items()} == newer, "the newer extractor's rows keep their currency"
    assert all(r["extractor_version"] == "2026-10-14.weekly.v4" for r in after.values())
    shared = [r for k, r in after.items() if k != "moment_only_the_newer_extractor_found"]
    assert shared and all(r["checks"]["also_extracted_by"][0]["extractor_version"] == "imported:" + WEEKLY for r in shared)


def test_an_excluded_document_gets_no_imported_moment(ready):
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    root, _ = saved_week(tmp_path, docs)
    with repo.connection() as conn:
        conn.execute("UPDATE transcripts SET included=false,exclusion_reason='A person excluded it' WHERE transcript_id=%s",
                     (docs["B"]["transcript_id"],))
    report = imports.import_saved(repo, root)
    assert "excluded" in report["artifacts"][0]["meetings"][1]["skipped"]
    assert not [r for r in ledger(repo) if r["document_id"] == docs["B"]["transcript_id"]]


def test_an_import_after_a_newer_extraction_is_stored_but_not_current(ready):
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    with repo.connection() as conn:
        rows = [conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (docs["A"]["transcript_id"],)).fetchone()]
    result = queue.queue_extraction(repo, models, rows, mode="synthetic", actor="tester", queue="bulk", profile=SCENE_V2_PROFILE)
    run_job(result["jobs"][0], storage=repo.settings, models=models, provider=ScriptedProvider(standard_scripts()), successors=False)
    root, _ = saved_week(tmp_path, docs)
    imports.import_saved(repo, root)
    mine = [r for r in ledger(repo) if r["document_id"] == docs["A"]["transcript_id"]]
    imported = [r for r in mine if r["extractor_version"].startswith("imported:")]
    current = [r for r in mine if r["extractor_version"] == SCENE_V2_PROFILE]
    assert imported and current and all(r["is_current"] for r in current)
    assert not any(r["is_current"] for r in imported if r["quote_verified"]), "the older extractor's moments are not current"


def failed_attempt(root, documents, moments, *, fingerprint="e" * 64):
    """A failed attempt in the layout the stage caller writes: the artifact without output, the received response beside it."""
    attempt = root / "service_calls" / fingerprint / "attempts" / "artifact_failed"
    artifact = artifact_file(attempt, documents, moments, fingerprint=fingerprint, name="artifact.json", status="failed",
                             artifact_id="artifact_failed", run_id="week1-gpt6-luna-generation-only-a3",
                             error="Moment quote must match an existing anchor span")
    data = json.loads((attempt / "artifact.json").read_text(encoding="utf-8"))
    (attempt / "output.received.json").write_text(json.dumps(data["output"]), encoding="utf-8")
    (attempt / "artifact.json").write_text(json.dumps(data | {"output": None, "output_hash": None}), encoding="utf-8")
    return attempt, artifact


def test_a_failed_attempt_is_re_checked_moment_by_moment_only_when_asked(ready):
    """E.B12a on saved responses: a response rejected whole for one quote still yields every moment that binds."""
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    root = tmp_path / "legacy"
    moments = [moment("exact", "m1.t0002", "We had 45 bookings in March.", kind="result"),
               moment("bound-nowhere", "m1.t0002", "Nobody said this at all, ever.")]
    attempt, _ = failed_attempt(root, [docs["A"]], moments)
    assert imports.import_saved(repo, root, apply=False)["artifacts"] == [], "failed attempts are not read by default"

    report = imports.import_saved(repo, root, include_failed=True, actor="tester@example.invalid")
    (entry,) = report["artifacts"]
    assert entry["original_error"] == "Moment quote must match an existing anchor span"
    assert entry["revalidated_from_attempt"] == str(attempt) and report["provider_calls"] == 0
    rows = ledger(repo)
    kept = [r for r in rows if r["quote_verified"]]
    assert [r["moment_body"]["quote"] for r in kept] == ["We had 45 bookings in March."]
    assert [r["checks"]["local_key"] for r in rows if not r["quote_verified"]] == ["bound-nowhere"]
    source = kept[0]["checks"]["imported_from"]
    assert source["revalidated_from_attempt"] == str(attempt) and source["original_error"].startswith("Moment quote must match")
    assert source["original_run_id"] == "week1-gpt6-luna-generation-only-a3"


def test_a_validated_artifact_wins_over_a_failed_attempt_for_the_same_request(tmp_path):
    docs = [{"passage_map": [{"start": 0, "end": 2}], "original_text": "hi"}]
    root = tmp_path / "saved"
    failed_attempt(root, docs, [], fingerprint="a" * 64)
    artifact_file(root / "validated", docs, [])
    (found,) = imports.discover(root, include_failed=True)
    assert found[1].status == "validated" and found[1].artifact_id == "artifact_week1"
    assert [a.status for _, a in imports.discover(root / "service_calls", include_failed=True)] == ["failed"]


def test_a_row_written_before_a_field_existed_holds_the_same_evidence():
    """The 12 October weekly rows have no `discovery` key; the same moment today says `discovery: null`."""
    from backend_pipeline.moments.store import same_evidence
    stored = {"moment_body": {"quote": "We had 45 bookings in March.", "strength": 3.0}, "evidence_refs": [{"passage": "p1"}]}
    assert same_evidence(stored, {"quote": "We had 45 bookings in March.", "strength": 3.0, "discovery": None}, [{"passage": "p1"}])
    assert not same_evidence(stored, {"quote": "We had 46 bookings in March.", "strength": 3.0}, [{"passage": "p1"}])
    assert not same_evidence(stored, {"quote": "We had 45 bookings in March.", "strength": 3.0, "discovery": {"lenses": []}},
                             [{"passage": "p1"}])
    assert not same_evidence(stored, {"quote": "We had 45 bookings in March.", "strength": 3.0}, [{"passage": "p2"}])


def test_discovery_ignores_what_is_not_a_trusted_artifact(tmp_path):
    root = tmp_path / "saved"
    docs = [{"passage_map": [{"start": 0, "end": 2}], "original_text": "hi"}]
    artifact_file(root, docs, [])
    artifact_file(root, docs, [], fingerprint="d" * 64, name="tampered.json", output_hash="0" * 64)
    (root / "garbage.json").write_text("[1]")
    found = imports.discover(root)
    assert [a.request_fingerprint for _, a in found] == ["a" * 64]
    meetings = imports.parse_packet(imports.user_message(found[0][1]))
    assert meetings[0]["ref"] == "m1" and meetings[0]["turns"] == [{"ref": "m1.t0001", "text": "hi"}]
    multi = "x\nMEETING " + json.dumps({"source_id": "m1"}) + "\nm1.t0001|1+2|first line\nsecond line\nCUE_SETTINGS {}\nm1.t0002|3+1|next\nEND_MEETING m1"
    assert imports.parse_packet(multi)[0]["turns"] == [{"ref": "m1.t0001", "text": "first line\nsecond line"}, {"ref": "m1.t0002", "text": "next"}]
