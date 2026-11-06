"""E.B12's default switch on a real database: the weekly cycle reads the moments ledger's per-document scene profile v2
(2.B2) instead of its own extraction. A document the ledger already holds costs no call; any other is extracted once, by the
same function a document's own job runs, and stays in the ledger for the next cycle. No network."""
from __future__ import annotations

import pytest

from backend_pipeline import settings_store
from backend_pipeline.config import Settings
from backend_pipeline.documents import select
from backend_pipeline.jobs.executor import run_job
from backend_pipeline.moments import queue
from backend_pipeline.moments.scenes import SCENE_V2_PROFILE
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.tests.moments_fixtures import FILES, MARK, ScriptedProvider, import_documents, prepare_reference, standard_scripts
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)

AB = {name: make for name, make in FILES.items() if not name.endswith("C.vtt")}


@pytest.fixture
def ready(platform_setup):  # noqa: F811
    repo, models, tmp_path = platform_setup
    prepare_reference(repo)
    return repo, models, tmp_path


def rows(repo, sql, *params):
    with repo.connection() as conn:
        return conn.execute(sql, params).fetchall()


def week_job(repo, run_id):
    (job,) = rows(repo, "SELECT * FROM pipeline_jobs WHERE run_id=%s AND stage='moment_extraction'", run_id)
    return job


def test_the_ledger_profile_is_the_weekly_default():
    assert settings_store.default("prompts.profile.extraction") == SCENE_V2_PROFILE
    assert Settings().extraction_profile == SCENE_V2_PROFILE
    assert settings_store.definition("prompts.profile.extraction").choices == (
        SCENE_V2_PROFILE, "2026-10-13.weekly.v3", "2026-10-18.scenes.v1", "2026-10-23.scenes.v3", "2026-10-25.scenes.v4"), \
        "weekly v3 and v1 stay selectable for replay; scene v3 (E.B31) and v4 (N8) are selectable, not the default"


def test_the_weekly_cycle_reads_the_ledger_and_extracts_only_the_documents_it_lacks(ready):
    repo, models, tmp_path = ready
    models = models.model_copy(update={"extraction_profile": SCENE_V2_PROFILE})
    docs = import_documents(repo, models, tmp_path, AB)
    a, b = docs["A"], docs["B"]
    provider = ScriptedProvider(standard_scripts())

    # The backfill extracted document A with its own job (2.B2).
    with repo.connection() as conn:
        backfill = queue.queue_extraction(repo, models, select.by_set(conn, [a["transcript_id"]]), mode="synthetic",
                                          actor="tester", queue="bulk", profile=SCENE_V2_PROFILE)
    (backfill_job,) = backfill["jobs"]
    run_job(backfill_job, storage=repo.settings, models=models, provider=provider, successors=False)
    assert provider.calls == [MARK["A"]]
    ledger_a = {r["moment_id"] for r in rows(repo, """SELECT moment_id FROM key_moments WHERE document_id=%s AND is_current
        AND quote_verified AND extractor_version=%s""", a["transcript_id"], SCENE_V2_PROFILE)}
    assert len(ledger_a) == 2, "one exact quote, one repaired; the unbindable one is an unverified record"

    # A weekly cycle over A and B: A comes from the ledger with no call; only B is extracted, by the document function.
    run = repo.submit("week_2026-06-01", "synthetic", models=models, documents=[a, b], selected_by="documents")
    (frozen,) = rows(repo, "SELECT input_refs FROM pipeline_runs WHERE run_id=%s", run["run_id"])
    assert frozen["input_refs"]["extraction_profile"] == SCENE_V2_PROFILE
    worker = SQLWorker(repo.settings, models, provider=provider)
    worker.once(run_id=run["run_id"])
    job = week_job(repo, run["run_id"])
    assert job["status"] == "completed", job["error_summary"]
    assert provider.calls == [MARK["A"], MARK["B"]], "A was not sent again"
    refs = job["result_refs"]
    by_doc = {d["transcript_id"]: d for d in refs["documents"]}
    assert by_doc[a["transcript_id"]]["reused_from_job"] == backfill_job and by_doc[a["transcript_id"]]["provider_calls"] == 0
    assert "reused_from_job" not in by_doc[b["transcript_id"]]
    assert refs["extraction_profile"] == SCENE_V2_PROFILE and refs["unverified_usable_as_proof"] is False
    assert ledger_a <= set(refs["moment_ids"]), "the week uses the ledger's own rows for A"
    assert len(refs["unverified_ids"]) == 1 and not set(refs["unverified_ids"]) & set(refs["moment_ids"])
    # B's scenes are ledger rows like A's: week-less, under v2, keyed by the per-document extraction key.
    b_rows = rows(repo, """SELECT * FROM key_moments WHERE document_id=%s AND is_current AND extractor_version=%s""",
                  b["transcript_id"], SCENE_V2_PROFILE)
    assert len(b_rows) == 2 and {r["week_id"] for r in b_rows} == {None}
    with repo.connection() as conn:
        kb, kb_refs = queue.knowledge_base(repo, models, "synthetic")
        expected = queue.extraction_key(select.by_set(conn, [b["transcript_id"]])[0], SCENE_V2_PROFILE, kb_refs)
    assert {r["checks"]["extraction"]["extraction_key"] for r in b_rows} == {expected}
    # The week's moments reach the strategist stage as its evidence.
    assert set(refs["moment_ids"]) == {r["moment_id"] for r in b_rows} | ledger_a

    # The next cycle over the same documents makes no call at all, and a document's own job for B would find it done.
    run2 = repo.submit("week_2026-06-08", "synthetic", models=models, documents=[a, b], selected_by="documents")
    worker.once(run_id=run2["run_id"])
    job2 = week_job(repo, run2["run_id"])
    assert job2["status"] == "completed", job2["error_summary"]
    assert provider.calls == [MARK["A"], MARK["B"]]
    assert set(job2["result_refs"]["moment_ids"]) == set(refs["moment_ids"])
    with repo.connection() as conn:
        again = queue.queue_extraction(repo, models, select.by_set(conn, [b["transcript_id"]]), mode="synthetic", actor="tester",
                                       queue="bulk", profile=SCENE_V2_PROFILE)
    for job_id in again["jobs"]:
        run_job(job_id, storage=repo.settings, models=models, provider=provider, successors=False)
    assert provider.calls == [MARK["A"], MARK["B"]], "the ledger's extraction of B is the document job's too"


def test_a_document_whose_response_fails_its_schema_is_left_out_of_the_week_and_the_next_cycle_resends_only_it(ready):
    repo, models, tmp_path = ready
    models = models.model_copy(update={"extraction_profile": SCENE_V2_PROFILE})
    docs = import_documents(repo, models, tmp_path)
    provider = ScriptedProvider(standard_scripts())
    run = repo.submit("week_2026-06-01", "synthetic", models=models, documents=list(docs.values()), selected_by="documents")
    worker = SQLWorker(repo.settings, models, provider=provider)
    worker.once(run_id=run["run_id"])
    job = week_job(repo, run["run_id"])
    # One of three calls failing no longer stops the week, which runs unattended on Sunday (6 November 2026): it goes on with
    # the others' scenes and names the call it left out. Most of the calls failing still fails it.
    assert job["status"] == "completed", job["error_summary"]
    assert sorted(provider.calls) == sorted([MARK["A"], MARK["B"], MARK["C"], MARK["C"]]), "C had its one repair"
    # A (two verified scenes and one unverified record) and B (two scenes) are in the ledger; a new cycle sends only C again.
    assert len(rows(repo, "SELECT 1 FROM key_moments WHERE is_current AND extractor_version=%s AND document_id=ANY(%s)",
                    SCENE_V2_PROFILE, [docs["A"]["transcript_id"], docs["B"]["transcript_id"]])) == 5
    # The document is named by its title, not its id (N1 shakedown: the cycle listed raw transcript ids).
    refs = job["result_refs"]
    assert refs["coverage"] == "partial_documents_failed" and len(refs["failed_documents"]) == 1
    assert refs["failed_documents"][0].startswith(docs["C"]["title"]) and docs["C"]["transcript_id"] not in refs["failed_documents"][0]
    assert "1 could not be read" in job["current_message"]
    # The documents the week did extract stay extracted; only C is failed (N8 shakedown: all eleven were marked failed).
    status = {r["transcript_id"]: r["extraction_status"] for r in rows(repo, "SELECT transcript_id,extraction_status FROM transcripts "
                                                                        "WHERE transcript_id=ANY(%s)", [d["transcript_id"] for d in docs.values()])}
    assert status == {docs["A"]["transcript_id"]: "completed", docs["B"]["transcript_id"]: "completed", docs["C"]["transcript_id"]: "failed"}
    provider.calls.clear()
    run2 = repo.submit("week_2026-06-08", "synthetic", models=models, documents=list(docs.values()), selected_by="documents")
    worker.once(run_id=run2["run_id"])
    assert set(provider.calls) == {MARK["C"]}


def test_a_cycle_under_scene_profile_v3_extracts_the_new_kinds_with_its_own_template(ready):
    """E.B31: with prompts.profile.extraction set to v3, the week's documents are extracted by the v3 prompt, and a human
    line keeps its type in the ledger; the v2 ledger rows of the same document are not reused (another extraction key)."""
    from backend_pipeline.moments.scenes import SCENE_V3_PROFILE, TEMPLATE_V3

    def v3(script, kinds):
        def answer(inv, n, system):
            out = script(inv, n, system)
            for scene, kind in zip(out["scenes"], kinds):
                scene["departure"] = None
                scene["moment_type"] = kind or scene["moment_type"]
            return out
        return answer
    repo, models, tmp_path = ready
    models = models.model_copy(update={"extraction_profile": SCENE_V3_PROFILE})
    docs = import_documents(repo, models, tmp_path, AB)
    scripts = standard_scripts()
    scripts = {MARK["A"]: v3(scripts[MARK["A"]], [None, None, None]), MARK["B"]: v3(scripts[MARK["B"]], [None, "human_line"])}
    provider = ScriptedProvider(scripts)
    run = repo.submit("week_2026-06-01", "synthetic", models=models, documents=[docs["A"], docs["B"]], selected_by="documents")
    worker = SQLWorker(repo.settings, models, provider=provider)
    worker.once(run_id=run["run_id"])
    job = week_job(repo, run["run_id"])
    assert job["status"] == "completed", job["error_summary"]
    assert job["result_refs"]["extraction_profile"] == SCENE_V3_PROFILE
    assert all(system.startswith(TEMPLATE_V3.read_text(encoding="utf-8").strip()) for system in provider.systems)
    kinds = {r["moment_type"] for r in rows(repo, """SELECT moment_type FROM key_moments WHERE document_id=%s AND is_current
        AND quote_verified AND extractor_version=%s""", docs["B"]["transcript_id"], SCENE_V3_PROFILE)}
    assert "human_line" in kinds
