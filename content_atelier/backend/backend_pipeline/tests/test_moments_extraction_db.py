"""Plan 2.B2 on a real database: one extraction job per included document, run through the queue executor with a scripted
offline provider. One unbindable quote costs no other scene, one failed document affects no other, and re-running a completed
document makes no provider call. No network."""
from __future__ import annotations

import pytest
from psycopg.types.json import Jsonb
from test_documents_db import INTERNAL_CALL

from backend_pipeline.documents import select
from backend_pipeline.jobs.executor import run_job
from backend_pipeline.moments import queue
from backend_pipeline.moments.scenes import SCENE_PROFILE, SCENE_V2_PROFILE
from backend_pipeline.tests.moments_fixtures import (FILES, MARK, ScriptedProvider, import_documents, prepare_reference, response,
                                                     scene, standard_scripts)
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)


@pytest.fixture
def ready(platform_setup):  # noqa: F811
    repo, models, tmp_path = platform_setup
    prepare_reference(repo)
    return repo, models, tmp_path


def queued(repo, models, docs, *, queue_name="bulk", profile=SCENE_V2_PROFILE, **kw):
    with repo.connection() as conn:
        rows = select.by_set(conn, [d["transcript_id"] for d in docs.values()])
    return queue.queue_extraction(repo, models, rows, mode="synthetic", actor="tester", queue=queue_name, profile=profile, **kw)


def execute(repo, models, provider, job_ids):
    return [run_job(j, storage=repo.settings, models=models, provider=provider, successors=False) for j in job_ids]


def rows(repo, sql, *params):
    with repo.connection() as conn:
        return conn.execute(sql, params).fetchall()


def duplicate_job(repo, original, job_id):
    """A second job for the very same extraction (what a duplicate dispatch or a manual re-queue would make)."""
    with repo.connection() as conn:
        conn.execute("""INSERT INTO pipeline_jobs(job_id,run_id,week_id,transcript_id,stage,idempotency_key,input_hash,executor,queue,
            progress_details) VALUES (%s,%s,NULL,%s,'moment_extraction',%s,%s,'rq','bulk',%s)""",
                     (job_id, original["run_id"], original["transcript_id"], "extract:" + job_id, original["input_hash"],
                      Jsonb({"dependencies": []})))
        conn.execute("UPDATE pipeline_runs SET status='queued' WHERE run_id=%s", (original["run_id"],))


def test_one_job_per_included_document_on_the_named_queue_and_excluded_documents_get_none(ready):
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    internal = import_documents(repo, models, tmp_path, {"Check-in with Gisselle.vtt": lambda: INTERNAL_CALL}, name="drop2")
    (excluded,) = internal.values()
    assert excluded["included"] is False
    result = queued(repo, models, docs)
    assert len(result["jobs"]) == 3 and result["queue"] == "bulk"
    jobs = rows(repo, "SELECT * FROM pipeline_jobs WHERE run_id=%s", result["run_id"])
    assert {j["transcript_id"] for j in jobs} == {d["transcript_id"] for d in docs.values()}
    assert {j["queue"] for j in jobs} == {"bulk"} and {j["stage"] for j in jobs} == {"moment_extraction"}
    assert all(j["week_id"] is None and j["status"] == "queued" for j in jobs)
    (run,) = rows(repo, "SELECT * FROM pipeline_runs WHERE run_id=%s", result["run_id"])
    assert run["run_scope"] == "document_extraction" and run["week_id"] is None
    assert {r["extraction_status"] for r in rows(repo, "SELECT extraction_status FROM transcripts WHERE transcript_id=ANY(%s)",
                                                 [d["transcript_id"] for d in docs.values()])} == {"queued"}
    # An excluded document is refused by name and creates no job; its status stays not_applicable.
    with pytest.raises(ValueError, match="excluded"):
        queue.queue_extraction(repo, models, [excluded], mode="synthetic", actor="tester", queue="bulk")
    assert not rows(repo, "SELECT 1 FROM pipeline_jobs WHERE transcript_id=%s AND stage='moment_extraction'", excluded["transcript_id"])
    assert rows(repo, "SELECT extraction_status FROM transcripts WHERE transcript_id=%s", excluded["transcript_id"])[0]["extraction_status"] == "not_applicable"
    assert excluded["transcript_id"] not in [d["transcript_id"] for d in queue_pending(repo)]
    # A cycle names the default queue.
    other = queue.queue_extraction(repo, models, [next(iter(docs.values()))], mode="synthetic", actor="tester", queue="default", profile=SCENE_PROFILE)
    assert other["queue"] == "default" and len(other["jobs"]) == 1, "another profile is another extraction"


def queue_pending(repo):
    with repo.connection() as conn:
        return queue.pending_documents(conn)


def test_each_scene_is_checked_alone_and_one_failed_document_affects_no_other(ready):
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    provider = ScriptedProvider(standard_scripts())
    result = queued(repo, models, docs)
    order = rows(repo, "SELECT job_id,transcript_id FROM pipeline_jobs WHERE run_id=%s ORDER BY transcript_id", result["run_id"])
    by_doc = {r["transcript_id"]: r["job_id"] for r in order}
    # The failing document goes first: the others still run.
    execute(repo, models, provider, [by_doc[docs["C"]["transcript_id"]], by_doc[docs["A"]["transcript_id"]], by_doc[docs["B"]["transcript_id"]]])

    jobs = {r["transcript_id"]: r for r in rows(repo, "SELECT * FROM pipeline_jobs WHERE run_id=%s", result["run_id"])}
    failed = jobs[docs["C"]["transcript_id"]]
    assert failed["status"] == "failed" and "not a list" not in (failed["error_summary"] or "x") and failed["error_summary"]
    assert jobs[docs["A"]["transcript_id"]]["status"] == "completed" and jobs[docs["B"]["transcript_id"]]["status"] == "completed"
    assert provider.calls.count(MARK["C"]) == 2, "a schema failure gets exactly one repair call, then the document fails"
    assert provider.calls.count(MARK["A"]) == 1 and provider.calls.count(MARK["B"]) == 1
    (run,) = rows(repo, "SELECT * FROM pipeline_runs WHERE run_id=%s", result["run_id"])
    assert run["status"] == "partially_completed" and run["has_partial_failures"]
    status = {r["transcript_id"]: r["extraction_status"] for r in rows(repo, "SELECT transcript_id,extraction_status FROM transcripts")}
    assert (status[docs["A"]["transcript_id"]], status[docs["B"]["transcript_id"]], status[docs["C"]["transcript_id"]]) == ("completed", "completed", "failed")

    # Document A: an exact quote and a near miss are verified (the repair recorded); the unbindable one is a record, never proof.
    a = rows(repo, "SELECT * FROM key_moments WHERE document_id=%s ORDER BY quote_verified DESC, moment_id", docs["A"]["transcript_id"])
    verified, unverified = [m for m in a if m["quote_verified"]], [m for m in a if not m["quote_verified"]]
    assert len(verified) == 2 and len(unverified) == 1
    repaired = next(m for m in verified if m["quote_repair"])
    assert repaired["quote_repair"]["original_quote"].endswith("follow up") and repaired["moment_body"]["quote"].endswith("follow-up")
    exact = next(m for m in verified if not m["quote_repair"])
    assert exact["moment_type"] == "result" and exact["speaker_role"] == "client" and exact["speaker_label"] == "Dana Lee"
    assert exact["evidence_kind"] == "direct_quote" and exact["extractor_version"] == SCENE_V2_PROFILE and exact["is_current"]
    assert exact["document_id"] == docs["A"]["transcript_id"] and exact["week_id"] is None and exact["run_id"] == result["run_id"]
    assert exact["checks"]["numbers"]["passed"] and exact["checks"]["extraction"]["local_key"] == "s1"
    assert exact["checks"]["extraction"]["scene"]["wia_moves"][0]["speaker"] == "Carmen Cruickshank"
    (record,) = unverified
    assert record["moment_id"].startswith("unverified_") and record["evidence_refs"] == [] and record["embedding"] is None
    assert "quote must match" in record["unverified_reason"] and record["extractor_version"] == SCENE_V2_PROFILE
    assert all(m["evidence_refs"] for m in verified)

    # Document B: staff praise is not a testimonial; a client's is; a figure absent from the source fails the number check.
    b = {m["checks"]["extraction"]["local_key"]: m for m in rows(repo, "SELECT * FROM key_moments WHERE document_id=%s", docs["B"]["transcript_id"])}
    assert b["p1"]["speaker_role"] == "staff" and b["p1"]["moment_type"] == "observation" and b["p1"]["evidence_kind"] == "team_report"
    assert b["p1"]["moment_body"]["moment_type"] == "testimonial" and b["p1"]["checks"]["role_plausibility"]["original_type"] == "testimonial"
    assert b["p2"]["speaker_role"] == "client" and b["p2"]["moment_type"] == "testimonial" and b["p2"]["evidence_kind"] == "direct_quote"
    assert b["p2"]["checks"]["numbers"]["passed"] is False and "60" in b["p2"]["checks"]["numbers"]["absent"][0]
    assert not rows(repo, "SELECT 1 FROM key_moments WHERE document_id=%s", docs["C"]["transcript_id"]), "the failed document stored nothing"

    # The prompt carried the call type, the speakers' roles and the glossary hint (2.B2).
    packet, system = next((u, s) for u, s in zip(provider.users, provider.systems, strict=True) if MARK["A"] in u)
    assert packet.startswith("One document's transcript turns") and "Carmen Cruickshank" in system, "the roster is in the packet"
    assert '"call_type":"client_1to1"' in system and '{"label":"Dana Lee","role":"client","inferred":true}' in system
    assert '"term":"LeadLock","kind":"product"' in system and "process catalogue" in system.lower()
    assert '"public_use":false' in system, "the document's handling travels with it"


def test_a_failed_document_is_retried_on_its_own_and_completes_the_run(ready):
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    scripts = standard_scripts()
    provider = ScriptedProvider(scripts)
    result = queued(repo, models, docs)
    execute(repo, models, provider, result["jobs"])
    c_job = next(r["job_id"] for r in rows(repo, "SELECT job_id FROM pipeline_jobs WHERE stage='moment_extraction' AND transcript_id=%s", docs["C"]["transcript_id"]))
    before = len(provider.calls)
    scripts[MARK["C"]] = lambda inv, n, system: {"scenes": [], "processed_meetings": inv, "coverage_notes": ["Only scheduling talk."]}
    repo.retry(c_job, "tester")
    execute(repo, models, provider, [c_job])
    assert rows(repo, "SELECT status FROM pipeline_jobs WHERE job_id=%s", c_job)[0]["status"] == "completed"
    assert len(provider.calls) == before + 1
    (run,) = rows(repo, "SELECT status FROM pipeline_runs WHERE run_id=%s", result["run_id"])
    assert run["status"] == "completed"
    assert rows(repo, "SELECT extraction_status FROM transcripts WHERE transcript_id=%s", docs["C"]["transcript_id"])[0]["extraction_status"] == "completed"
    assert not rows(repo, "SELECT 1 FROM key_moments WHERE document_id=%s", docs["C"]["transcript_id"]), "a document with no scene stores none"


def test_a_failed_document_is_queued_again_under_a_new_extraction_model(ready):
    """Found by the N1 shakedown: once the extraction model changed, a failed document could only be revived with the model
    its job was frozen with, which the worker refuses, so it could never be extracted again. Queued again, it gets a job of
    its own under today's model; the failed job stays as the record, and documents without a failure are left alone."""
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    scripts = standard_scripts()
    provider = ScriptedProvider(scripts)
    first = queued(repo, models, docs)
    execute(repo, models, provider, first["jobs"])
    c = docs["C"]["transcript_id"]
    (failed,) = rows(repo, "SELECT job_id FROM pipeline_jobs WHERE stage='moment_extraction' AND transcript_id=%s AND status='failed'", c)
    models.openrouter_moments_model = "another/extraction-model"
    scripts[MARK["C"]] = lambda inv, n, system: {"scenes": [], "processed_meetings": inv, "coverage_notes": ["Only scheduling talk."]}
    again = queued(repo, models, docs, retry_failed=True)
    assert again["requeued_for_new_model"] == [c] and again["retried"] == [] and len(again["jobs"]) == 1
    assert {s["transcript_id"] for s in again["skipped"]} == {d["transcript_id"] for k, d in docs.items() if k != "C"}
    (run,) = rows(repo, "SELECT input_refs FROM pipeline_runs WHERE run_id=%s", again["run_id"])
    assert run["input_refs"]["models"]["moment_extraction"] == "another/extraction-model"
    execute(repo, models, provider, again["jobs"])
    assert rows(repo, "SELECT status FROM pipeline_jobs WHERE job_id=%s", again["jobs"][0])[0]["status"] == "completed"
    assert rows(repo, "SELECT status FROM pipeline_jobs WHERE job_id=%s", failed["job_id"])[0]["status"] == "failed", "the record stays"
    assert queued(repo, models, docs, retry_failed=True)["jobs"] == [], "nothing is queued twice"


def test_re_running_a_completed_document_makes_no_provider_call(ready):
    repo, models, tmp_path = ready
    docs = {k: v for k, v in import_documents(repo, models, tmp_path).items() if k != "C"}
    provider = ScriptedProvider(standard_scripts())
    result = queued(repo, models, docs)
    execute(repo, models, provider, result["jobs"])
    calls = len(provider.calls)
    ids = {r["moment_id"] for r in rows(repo, "SELECT moment_id FROM key_moments")}
    assert calls == 2 and ids
    # 1. Asking again creates no job at all: the extraction key is the same.
    again = queued(repo, models, docs)
    assert again["jobs"] == [] and {s["status"] for s in again["skipped"]} == {"completed"} and again["run_id"] is None
    # 2. A second job for the same input (as a retry or a duplicate dispatch would make) stops before the call: the ledger
    # already holds this extraction.
    original = rows(repo, "SELECT * FROM pipeline_jobs WHERE stage='moment_extraction' AND transcript_id=%s", docs["A"]["transcript_id"])[0]
    duplicate_job(repo, original, "extjob_forced")
    execute(repo, models, provider, ["extjob_forced"])
    forced = rows(repo, "SELECT * FROM pipeline_jobs WHERE job_id='extjob_forced'")[0]
    assert forced["status"] == "completed" and forced["result_refs"]["provider_calls"] == 0 and forced["result_refs"]["dispatched"] is False
    assert len(provider.calls) == calls
    # 3. Even with the ledger and the earlier jobs gone, the saved validated response answers the call (artifact reuse in the
    # llm module): the handler goes through, the provider is not called, and the moments come back by identity.
    with repo.connection() as conn:
        conn.execute("DELETE FROM key_moments WHERE document_id=%s", (docs["A"]["transcript_id"],))
        conn.execute("UPDATE pipeline_jobs SET input_hash='forgotten' WHERE job_id IN ('extjob_forced',%s)", (original["job_id"],))
    duplicate_job(repo, original, "extjob_forced2")
    execute(repo, models, provider, ["extjob_forced2"])
    third = rows(repo, "SELECT * FROM pipeline_jobs WHERE job_id='extjob_forced2'")[0]
    assert third["status"] == "completed", third["error_summary"]
    assert third["result_refs"]["dispatched"] is False and third["result_refs"]["cache_reused"] is True
    assert len(provider.calls) == calls, "no provider call"
    assert {r["moment_id"] for r in rows(repo, "SELECT moment_id FROM key_moments")} == ids, "the same moments, by identity"
    assert len(rows(repo, "SELECT 1 FROM key_moments WHERE document_id=%s", docs["A"]["transcript_id"])) == 3


def test_a_newer_extractor_leaves_the_older_moments_readable_but_not_current(ready):
    repo, models, tmp_path = ready
    docs = {k: v for k, v in import_documents(repo, models, tmp_path).items() if k == "A"}
    provider = ScriptedProvider(standard_scripts())
    # v1 first (seven types), then v2: the document's v1 moments stop being current and none is deleted.
    first = queued(repo, models, docs, profile=SCENE_PROFILE)
    old = scene(local_key="old1", anchor_span_ids=["m1.t0001"], context_first_span_id="m1.t0001", context_last_span_id="m1.t0002",
                quote="Welcome Dana", setup="The call opens.", moment_type="observation", client_contribution=None)
    old_scripts = {MARK["A"]: lambda inv, n, system: response(inv, old, scene())}
    execute(repo, models, ScriptedProvider(old_scripts), first["jobs"])
    v1 = rows(repo, "SELECT * FROM key_moments WHERE document_id=%s", docs["A"]["transcript_id"])
    assert len(v1) == 2 and {m["extractor_version"] for m in v1} == {SCENE_PROFILE} and all(m["is_current"] for m in v1)
    second = queued(repo, models, docs, profile=SCENE_V2_PROFILE)
    execute(repo, models, provider, second["jobs"])
    everything = rows(repo, "SELECT moment_id,extractor_version,is_current,quote_verified FROM key_moments WHERE document_id=%s",
                      docs["A"]["transcript_id"])
    # old1 is only v1's: not current. s1 is the very same scene under both extractors (one identity): it is v2's too, so it
    # stays current. s2 is new in v2.
    assert sorted((r["extractor_version"], r["is_current"]) for r in everything if r["quote_verified"]) == [
        (SCENE_PROFILE, False), (SCENE_PROFILE, True), (SCENE_V2_PROFILE, True)]
    assert {m["moment_id"] for m in v1} <= {r["moment_id"] for r in everything}, "never deleted"


def test_a_later_extraction_under_the_same_profile_replaces_the_earlier_one_as_current(ready):
    """A document extracted again under the same profile (a new knowledge-base version is a new extraction key, and
    `moments extract --from/--to` selects completed documents too) must leave one current set of scenes, not two: the
    earlier extraction's scenes that the later one did not reproduce stay readable but are not current, and a later
    re-normalisation does not make them current again."""
    from backend_pipeline.documents.jobs import normalise
    from backend_pipeline.reference import add_glossary_term
    repo, models, tmp_path = ready
    docs = {k: v for k, v in import_documents(repo, models, tmp_path).items() if k == "A"}
    document_id = docs["A"]["transcript_id"]
    scripts = standard_scripts()
    provider = ScriptedProvider(scripts)
    first = queued(repo, models, docs)
    execute(repo, models, provider, first["jobs"])
    earlier = {r["moment_id"]: r for r in rows(repo, "SELECT * FROM key_moments WHERE document_id=%s", document_id)}
    assert len(earlier) == 3 and all(r["is_current"] for r in earlier.values())
    # The roster or glossary changed (the prompt differs, so the provider is asked again) and the extraction key is new.
    with repo.connection() as conn:
        add_glossary_term(conn, "Dana Lee", "client", ["Dana"])
    scripts[MARK["A"]] = lambda inv, n, system: response(inv, scene(), scene(
        local_key="s9", anchor_span_ids=["m1.t0003"], context_first_span_id="m1.t0003", context_last_span_id="m1.t0004",
        quote="Good, let us look at the follow up.", setup="The strategist turns to follow-up.", moment_type="decision",
        wia_moves=[{"speaker": "Carmen Cruickshank", "move": "decided", "what": "To review the follow-up"}], client_contribution=None))
    (original,) = rows(repo, "SELECT * FROM pipeline_jobs WHERE job_id=%s", first["jobs"][0])
    with repo.connection() as conn:
        conn.execute("""INSERT INTO pipeline_jobs(job_id,run_id,week_id,transcript_id,stage,idempotency_key,input_hash,executor,queue,
            progress_details) VALUES ('extjob_newkb',%s,NULL,%s,'moment_extraction','extract:newkb','newkb','rq','bulk',%s)""",
                     (original["run_id"], document_id, Jsonb({"dependencies": []})))
        conn.execute("UPDATE pipeline_runs SET status='queued' WHERE run_id=%s", (original["run_id"],))
    calls = len(provider.calls)
    execute(repo, models, provider, ["extjob_newkb"])
    assert rows(repo, "SELECT status FROM pipeline_jobs WHERE job_id='extjob_newkb'")[0]["status"] == "completed"
    assert len(provider.calls) == calls + 1, "the changed prompt is a new call"
    later = rows(repo, "SELECT * FROM key_moments WHERE document_id=%s", document_id)
    current = {r["checks"].get("extraction", {}).get("local_key") or r["checks"].get("local_key") for r in later if r["is_current"]}
    assert current == {"s1", "s9"}, "only the later extraction's scenes are current (s1 is the same scene, one identity)"
    assert {r["moment_id"] for r in later} >= set(earlier), "nothing is deleted"
    with repo.connection() as conn:
        assert conn.execute("""SELECT count(*) n FROM key_moments WHERE document_id=%s AND quote_verified AND is_current""",
                            (document_id,)).fetchone()["n"] == 2
    normalise(repo, document_id, models=models)
    after = {r["moment_id"]: r["is_current"] for r in rows(repo, "SELECT moment_id,is_current FROM key_moments WHERE document_id=%s", document_id)}
    assert sum(after.values()) == 2, "a re-normalisation does not bring the replaced scenes back"
    # Scene recall measures the profile's current extraction, not the union of every extraction it ever made.
    from backend_pipeline.moments import recall
    golden = {"scenes": [{"id": "only_earlier", "document": {"transcript_id": document_id}, "anchor": "Lead Lock has helped a lot"},
                         {"id": "both", "document": {"transcript_id": document_id}, "anchor": "We had 45 bookings in March"}]}
    with repo.connection() as conn:
        measured = recall.measure(conn, golden, extractor_version=SCENE_V2_PROFILE)
    assert measured["found"] == 1 and measured["missed"] == ["only_earlier"]


def test_the_weekly_path_and_the_document_path_fill_the_same_ledger_columns(platform_setup):
    """The weekly scene path stores through the same writer: document, speaker, role, consent and the version are filled."""
    from test_scenes import SceneProvider  # noqa: PLC0415

    from backend_pipeline.sql_pipeline import SQLWorker
    repo, models, _ = platform_setup
    scenes = models.model_copy(update={"extraction_profile": SCENE_PROFILE})
    repo.submit("week_2026-06-01", "synthetic", models=scenes)
    SQLWorker(repo.settings, scenes, provider=SceneProvider()).once()
    stored = rows(repo, "SELECT * FROM key_moments ORDER BY quote_verified DESC, moment_id")
    verified = [m for m in stored if m["quote_verified"]]
    assert len(verified) == 2 and all(m["document_id"] and m["extractor_version"] == SCENE_PROFILE for m in verified)
    assert all(m["speaker_label"] == "Alice" and m["consent_status"] == "anonymise" and m["checks"]["consent"] for m in verified)
    assert len(stored) == 2, "the weekly path keeps its unverified moment in the job's result_refs (E.B12a), not as a row"
    (job,) = rows(repo, "SELECT result_refs FROM pipeline_jobs WHERE stage='moment_extraction'")
    assert job["result_refs"]["unverified_count"] == 1
    assert len(FILES) == 3


def test_the_whole_week_path_stores_through_the_same_writer(platform_setup):
    from test_sql_storage import NonemptyProvider  # noqa: PLC0415

    from backend_pipeline.sql_pipeline import SQLWorker
    from backend_pipeline.tests.strategic_fixtures import strategic_output  # noqa: PLC0415

    class Provider(NonemptyProvider):
        def json_call(self, *, stage, system, user, schema, fingerprint):
            if stage != "moment_extraction":
                return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
            good = super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)[0]
            lost = {**good["moments"][0], "local_key": "lost", "quote": "Nobody said this at all, ever."}
            return {**good, "moments": [good["moments"][0], strategic_output({"moments": [lost]}, schema)["moments"][0]]}, {"fake": True}

    repo, models, _ = platform_setup
    repo.submit("week_2026-06-01", "synthetic", models=models)
    SQLWorker(repo.settings, models, provider=Provider()).once()
    (verified,) = rows(repo, "SELECT * FROM key_moments")
    assert verified["extractor_version"] == "2026-10-13.weekly.v3" and verified["document_id"] and verified["week_id"] == "week_2026-06-01"
    assert verified["destination"] == "public_opportunity" and verified["speaker_label"] == "Alice" and verified["checks"]["consent"]
    (job,) = rows(repo, "SELECT result_refs FROM pipeline_jobs WHERE stage='moment_extraction'")
    assert [u["local_key"] for u in job["result_refs"]["unverified_moments"]] == ["lost"], "kept in the job record, as before"


def test_a_cached_run_never_calls_a_provider_and_a_failed_job_is_queued_again_only_when_asked(ready):
    repo, models, tmp_path = ready
    docs = {k: v for k, v in import_documents(repo, models, tmp_path).items() if k == "A"}
    provider = ScriptedProvider(standard_scripts())
    with repo.connection() as conn:
        found = select.by_set(conn, [docs["A"]["transcript_id"]])
    result = queue.queue_extraction(repo, models, found, mode="replay", actor="tester", queue="bulk", profile=SCENE_V2_PROFILE)
    execute(repo, models, provider, result["jobs"])
    (job,) = rows(repo, "SELECT * FROM pipeline_jobs WHERE job_id=%s", result["jobs"][0])
    assert job["status"] == "failed" and "Replay cache miss" in job["error_summary"] and provider.calls == [], "no saved response, so no call"
    assert rows(repo, "SELECT extraction_status FROM transcripts WHERE transcript_id=%s", docs["A"]["transcript_id"])[0]["extraction_status"] == "failed"
    waiting = queue.queue_extraction(repo, models, found, mode="replay", actor="tester", queue="bulk", profile=SCENE_V2_PROFILE)
    assert waiting["jobs"] == [] and waiting["skipped"][0]["status"] == "failed" and waiting["retried"] == []
    again = queue.queue_extraction(repo, models, found, mode="replay", actor="tester", queue="bulk", profile=SCENE_V2_PROFILE, retry_failed=True)
    assert again["retried"] == result["jobs"] and rows(repo, "SELECT status FROM pipeline_jobs WHERE job_id=%s", result["jobs"][0])[0]["status"] == "queued"
    assert rows(repo, "SELECT extraction_status FROM transcripts WHERE transcript_id=%s", docs["A"]["transcript_id"])[0]["extraction_status"] == "queued"
    with pytest.raises(ValueError, match="queue must be"):
        queue.queue_extraction(repo, models, found, mode="replay", actor="tester", queue="media")
    with pytest.raises(ValueError, match="Unknown scene profile"):
        queue.queue_extraction(repo, models, found, mode="replay", actor="tester", queue="bulk", profile="nope")
    with pytest.raises(ValueError, match="mode must be"):
        queue.queue_extraction(repo, models, found, mode="cached", actor="tester", queue="bulk")


def test_a_lost_worker_fails_its_own_document_and_leaves_the_run_open_for_the_others(ready):
    from backend_pipeline.jobs import policy
    from backend_pipeline.jobs.recover import recover_expired
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    result = queued(repo, models, docs)
    lost = repo.claim(run_id=result["run_id"])  # a worker took it and died, and this was its last attempt
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_jobs SET lease_expires_at=now()-interval '1 second',attempt_count=%s WHERE job_id=%s",
                     (policy.MAX_ATTEMPTS, lost["job_id"]))
    (done,) = recover_expired(repo)
    assert done["outcome"] == "failed"
    (run,) = rows(repo, "SELECT status,has_partial_failures FROM pipeline_runs WHERE run_id=%s", result["run_id"])
    assert run["status"] == "running" and run["has_partial_failures"], "one lost document does not stop the run"
    assert repo.claim(run_id=result["run_id"]) is not None, "the other documents can still be claimed"
