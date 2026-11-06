"""Plan 2.B11 and the checks' maintenance commands, on a real database: the pilot, the estimate, the live run's plan, the report and
its invariants, `recheck`, and scene recall against a golden file. Offline provider throughout; no paid call, no network."""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from psycopg.types.json import Jsonb

from backend_pipeline import storage_cli
from backend_pipeline.documents import select
from backend_pipeline.documents.api import ClassificationRequest, classify_by_person
from backend_pipeline.jobs.executor import run_job
from backend_pipeline.llm import run_plans
from backend_pipeline.moments import queue, recall, recheck, report
from backend_pipeline.moments.scenes import SCENE_PROFILE, SCENE_V2_PROFILE
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.moments_fixtures import (KB, MARK, ScriptedProvider, import_documents, prepare_reference, response, scene,
                                                     standard_scripts)
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)


@pytest.fixture
def ready(platform_setup):  # noqa: F811
    repo, models, tmp_path = platform_setup
    prepare_reference(repo)
    return repo, models, tmp_path


def rows(repo, sql, *params):
    with repo.connection() as conn:
        return conn.execute(sql, params).fetchall()


def extract(repo, models, docs, provider, *, profile=SCENE_V2_PROFILE):
    with repo.connection() as conn:
        found = select.by_set(conn, [d["transcript_id"] for d in docs.values()])
    result = queue.queue_extraction(repo, models, found, mode="synthetic", actor="tester", queue="bulk", profile=profile)
    for job in result["jobs"]:
        run_job(job, storage=repo.settings, models=models, provider=provider, successors=False)
    return result


def quiet_scripts():
    """Standard scripts, but the third document says there is nothing in it (a completed document with no scene)."""
    scripts = standard_scripts()
    scripts[MARK["C"]] = lambda inv, n, system: response(inv, notes=["Only scheduling talk."])
    return scripts


# ---- the pilot ---------------------------------------------------------------------------------------------------------------

def test_a_pilot_spreads_over_the_call_types_each_oldest_first():
    day = lambda d: datetime(2026, 3, d, tzinfo=UTC)  # noqa: E731
    docs = [{"transcript_id": "w1", "call_type": "workshop", "occurred_at": day(1)}, {"transcript_id": "c2", "call_type": "client_1to1", "occurred_at": day(2)},
            {"transcript_id": "c1", "call_type": "client_1to1", "occurred_at": day(1)}, {"transcript_id": "c3", "call_type": "client_1to1", "occurred_at": None},
            {"transcript_id": "p1", "call_type": "prospect", "occurred_at": day(5)}, {"transcript_id": "o1", "call_type": None, "occurred_at": day(9)}]
    assert [d["transcript_id"] for d in queue.pilot(docs, 4)] == ["c1", "p1", "o1", "w1"], "one of each kind (in name order) before any kind twice"
    assert [d["transcript_id"] for d in queue.pilot(docs, 6)] == ["c1", "p1", "o1", "w1", "c2", "c3"]
    assert len(queue.pilot(docs, 50)) == 6
    with pytest.raises(ValueError):
        queue.pilot(docs, 0)


# ---- the estimate and the live run's plan ----------------------------------------------------------------------------------------

def test_the_estimate_counts_documents_and_tokens_and_prices_them_without_a_call(ready):
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    with repo.connection() as conn:
        found = select.by_set(conn, [d["transcript_id"] for d in docs.values()])
    one = queue.estimate(repo, models, found, profile=SCENE_V2_PROFILE, mode="synthetic")
    assert one["documents"] == 3 and one["provider_calls_made"] == 0 and one["model"] == models.model_for("moment_extraction")
    assert one["input_tokens_estimate"] > 0 and one["input_token_allowance_conservative"] >= one["input_tokens_estimate"]
    assert one["output_tokens_assumed"] == 3 * 6000 and one["price_usd_per_million"] == {"input": 0.1, "output": 0.5}
    expected = round(one["input_tokens_estimate"] / 1e6 * 0.1 + one["output_tokens_assumed"] / 1e6 * 0.5, 4)
    assert one["estimated_cost_usd"] == expected and one["input_set_hash"].startswith("sha256:") and one["knowledge_base_version"]
    # A model that is not in the price table has no estimate unless the settings give a price.
    other = models.model_copy(update={"openrouter_moments_model": "someone/new-model"})
    assert queue.estimate(repo, other, found, profile=SCENE_V2_PROFILE, mode="synthetic")["estimated_cost_usd"] is None
    # Documents that already have their job are not counted again.
    extract(repo, models, {"A": docs["A"]}, ScriptedProvider(standard_scripts()))
    two = queue.estimate(repo, models, found, profile=SCENE_V2_PROFILE, mode="synthetic")
    assert two["documents"] == 2 and [e["status"] for e in two["already_have_a_job"]] == ["completed"]
    assert two["input_set_hash"] != one["input_set_hash"], "a plan is approved for the documents that would actually be sent"


def live_ready(repo):
    repo.settings = repo.settings.model_copy(update={"generation_enabled": True, "synthetic": False})


def test_a_live_run_is_refused_without_an_active_plan_bound_to_the_input_set(ready, tmp_path, monkeypatch):
    repo, models, tmp = ready
    docs = import_documents(repo, models, tmp)
    with repo.connection() as conn:
        found = select.by_set(conn, [d["transcript_id"] for d in docs.values()])
    model = models.model_for("moment_extraction")
    base = dict(purpose="pilot", stages=["moment_extraction"], models=[model], max_calls=10, max_cost_usd=1.0, approver="whitney@example.invalid")
    digest = queue.input_set_hash(found)

    def attempt(**kw):
        return queue.queue_extraction(repo, models, found, mode="live", actor="tester", queue="bulk", profile=SCENE_V2_PROFILE, **kw)

    # Generation is off by default: nothing is queued.
    with pytest.raises(ValueError, match="generation permission is disabled"):
        attempt()
    live_ready(repo)
    monkeypatch.delenv("ATELIER_RUN_PLAN_ID", raising=False)
    monkeypatch.delenv("ATELIER_RUN_PLAN_FILE", raising=False)
    with pytest.raises(run_plans.RunPlanError, match="needs an active run plan"):
        attempt()
    store = lambda name, **kw: run_plans.FilePlanStore(run_plans.write_file_plan(tmp_path / name, **{**base, "input_set_hash": digest, **kw}) and tmp_path / name)  # noqa: E731
    with pytest.raises(run_plans.RunPlanError, match="another input set"):
        attempt(plan=store("other.json", input_set_hash="sha256:" + "0" * 64))
    with pytest.raises(run_plans.RunPlanError, match="does not cover stage"):
        attempt(plan=store("stage.json", stages=["angle_generation"]))
    with pytest.raises(run_plans.RunPlanError, match="does not cover model"):
        attempt(plan=store("model.json", models=["someone/else"]))
    with pytest.raises(run_plans.RunPlanError, match="calls left for 3 documents"):
        attempt(plan=store("few.json", max_calls=2))
    plan_file = store("ok.json")
    plan_file.close("closed by a person")
    with pytest.raises(run_plans.RunPlanError, match="is closed"):
        attempt(plan=plan_file)
    assert not rows(repo, "SELECT 1 FROM pipeline_runs WHERE run_scope='document_extraction'"), "every refusal happened before a run existed"
    # An active plan for exactly this input set (or for any) lets the run be queued; the environment names it the way workers do.
    good = store("good.json")
    queued = attempt(plan=good)
    assert len(queued["jobs"]) == 3 and queued["plan"]["calls_left"] == 10
    (run,) = rows(repo, "SELECT input_refs FROM pipeline_runs WHERE run_id=%s", queued["run_id"])
    assert run["input_refs"]["mode"] == "live" and run["input_refs"]["queue"] == "bulk"
    monkeypatch.setenv("ATELIER_RUN_PLAN_FILE", str(store("any.json", input_set_hash="*").path))
    again = attempt()
    assert again["jobs"] == [] and {s["status"] for s in again["skipped"]} == {"queued"}, "a second ask queues nothing twice"


# ---- the command line --------------------------------------------------------------------------------------------------------------

@pytest.fixture
def cli(ready, monkeypatch, capsys):
    repo, models, tmp_path = ready
    monkeypatch.setattr(StorageSettings, "from_env", classmethod(lambda cls: repo.settings))
    monkeypatch.setattr(type(models), "from_env", classmethod(lambda cls: models.model_copy(update={"knowledge_base_root": KB})))

    def run(*argv):
        capsys.readouterr()
        storage_cli.main(list(argv))
        return json.loads(capsys.readouterr().out)
    return run, repo, models, tmp_path


def test_the_backfill_is_a_command_with_an_estimate_a_pilot_and_a_synthetic_run(cli):
    run, repo, models, tmp_path = cli
    docs = import_documents(repo, models, tmp_path)
    estimate = run("moments", "extract", "--all-pending", "--estimate")
    assert estimate["documents"] == 3 and estimate["provider_calls_made"] == 0 and not rows(repo, "SELECT 1 FROM pipeline_runs WHERE run_scope='document_extraction'")
    pilot = run("moments", "extract", "--pilot", "2", "--mode", "synthetic", "--now")
    assert pilot["selected"] == 2 and pilot["queue"] == "bulk" and pilot["ran"] == 2 and pilot["job_states"] == {"completed": 2}
    done = rows(repo, "SELECT transcript_id,extraction_status FROM transcripts WHERE extraction_status='completed' AND week_id IS NULL")
    assert len(done) == 2, "the offline provider records scenes as there being none; the jobs completed and the documents are marked"
    rest = run("moments", "extract", "--all-pending", "--mode", "synthetic", "--queue", "default")
    assert len(rest["jobs"]) == 1 and rest["queue"] == "default"
    assert run("moments", "extract", "--ids", *[d["transcript_id"] for d in docs.values()], "--mode", "synthetic")["jobs"] == [], "nothing twice"
    with pytest.raises(SystemExit):
        run("moments", "extract")
    with pytest.raises(SystemExit):
        run("moments", "extract", "--from", "2026-03-01T00:00:00+00:00")
    window = run("moments", "extract", "--from", "2026-03-10T00:00:00+00:00", "--to", "2026-03-13T00:00:00+00:00", "--estimate")
    assert window["documents"] == 0 and len(window["already_have_a_job"]) == 3, "a window finds the three dated calls, each already has its job"
    report_ = run("moments", "report")
    assert report_["ok"] is True and report_["documents"]["with_zero_scenes"]["count"] == 2


def test_the_backfill_includes_documents_the_weekly_path_already_read(cli):
    """A document a weekly run read is marked `completed` (the run's extraction, or migration 007 for Weeks 1 to 5), yet it has
    no scene from the per-document profile. `--all-pending` and `--pilot` are the backfill's selection, so they must still pick
    it; a document the profile itself has extracted is not picked again."""
    run, repo, models, tmp_path = cli
    docs = import_documents(repo, models, tmp_path)
    weekly = docs["A"]["transcript_id"]
    with repo.connection() as conn:
        conn.execute("UPDATE transcripts SET extraction_status='completed' WHERE transcript_id=%s", (weekly,))
    estimate = run("moments", "extract", "--all-pending", "--estimate")
    assert estimate["documents"] == 3, "the weekly path's document has no scene from this profile yet"
    pilot = run("moments", "extract", "--pilot", "3", "--mode", "synthetic", "--now")
    assert pilot["selected"] == 3 and pilot["job_states"] == {"completed": 3}
    assert run("moments", "extract", "--all-pending", "--estimate")["documents"] == 0, "nothing is picked twice"
    other = run("moments", "extract", "--all-pending", "--estimate", "--profile", SCENE_PROFILE)
    assert other["documents"] == 3, "another profile has not read them"


# ---- the report and its invariants ----------------------------------------------------------------------------------------------

def test_the_report_gives_the_quote_share_roles_types_zero_scene_documents_and_keeps_the_invariants(ready):
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    extract(repo, models, docs, ScriptedProvider(quiet_scripts()))
    with repo.connection() as conn:
        out = report.report(conn)
    moments = out["moments"]
    assert (moments["moments_stored"], moments["verified"], moments["unverified"]) == (5, 4, 1)
    assert moments["verified_quote_share"] == 0.8 and moments["quote_repairs"] == 1
    assert moments["role_distribution"] == {"client": 3, "staff": 1}
    assert moments["type_distribution"] == {"observation": 2, "result": 1, "testimonial": 1}, "the staff praise line is not a testimonial"
    assert moments["evidence_kind_distribution"] == {"direct_quote": 3, "team_report": 1}
    assert moments["number_check"] == {"checked": 4, "failed": 1}
    client_calls = moments["by_call_type"]["client_1to1"]
    assert client_calls["documents_with_moments"] == 2 and client_calls["verified_quote_share"] == 0.8
    assert client_calls["role_distribution"] == {"client": 3, "staff": 1}
    assert out["documents"]["with_zero_scenes"]["count"] == 1 and out["documents"]["with_zero_scenes"]["documents"][0]["transcript_id"] == docs["C"]["transcript_id"]
    assert out["documents"]["by_extraction_status"]["completed"] == 3
    assert out["ok"] is True and out["invariants"]["no_current_moment_for_an_excluded_document"] == {"ok": True, "documents": []}

    # A person excludes a document that was extracted: its moments stay readable but are no longer current.
    classify_by_person(repo, docs["A"]["transcript_id"], ClassificationRequest(call_type="internal", included=False, reason="Not a client call"),
                       "whitney@example.invalid", models)
    with repo.connection() as conn:
        after = report.report(conn)
        assert after["ok"] is True and after["invariants"]["moments_kept_readable_for_documents_excluded_since"] == 3
        assert after["moments"]["moments_stored"] == 2 and after["all_stored"]["moments_stored"] == 5
        # The invariant is a real check: a current moment on an excluded document is reported by name.
        conn.execute("UPDATE key_moments SET is_current=true WHERE document_id=%s", (docs["A"]["transcript_id"],))
        broken = report.report(conn)
    assert broken["ok"] is False and broken["invariants"]["no_current_moment_for_an_excluded_document"]["documents"] == [docs["A"]["transcript_id"]]
    # Re-including it brings the newest extractor's moments back.
    classify_by_person(repo, docs["A"]["transcript_id"], ClassificationRequest(call_type="client_1to1", included=True, reason="It was"),
                       "whitney@example.invalid", models)
    with repo.connection() as conn:
        assert report.report(conn)["moments"]["moments_stored"] == 5
    # And one extractor alone can be reported, to compare two profiles.
    with repo.connection() as conn:
        assert report.report(conn, extractor_version="nothing")["moments"]["moments_stored"] == 0


# ---- recheck -----------------------------------------------------------------------------------------------------------------------

def test_recheck_rederives_consent_roles_and_checks_after_the_facts_change_and_is_idempotent(ready):
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    with repo.connection() as conn:  # the account unknown at extraction, as for a title that names no one (N10 adds it otherwise)
        conn.execute("UPDATE transcripts SET client_id=NULL WHERE client_id IS NOT NULL")
        conn.execute("DELETE FROM people WHERE source='call'")
        conn.execute("DELETE FROM clients WHERE source='call'")
    extract(repo, models, {"A": docs["A"], "B": docs["B"]}, ScriptedProvider(standard_scripts()))
    with repo.connection() as conn:
        conn.execute("INSERT INTO clients(client_id,name,consent) VALUES ('client_dana','Dana Lee','may_name')")
        conn.execute("UPDATE transcripts SET client_id='client_dana' WHERE transcript_id=ANY(%s)", ([docs["A"]["transcript_id"], docs["B"]["transcript_id"]],))
    first = recheck.recheck(repo)
    assert first["changed"] == 5 and first["columns_changed"]["client_id"] == 5 and first["skipped_without_document"] == 0
    exact = rows(repo, "SELECT * FROM key_moments WHERE checks->'extraction'->>'local_key'='s1'")[0]
    assert exact["client_id"] == "client_dana" and exact["consent_status"] == "cleared", "may_name, public candidate, a direct quote"
    near = rows(repo, "SELECT * FROM key_moments WHERE checks->'extraction'->>'local_key'='s2'")[0]
    assert near["consent_status"] == "anonymise", "the sensitivity is unknown"
    unverified = rows(repo, "SELECT * FROM key_moments WHERE NOT quote_verified")[0]
    assert unverified["client_id"] == "client_dana" and unverified["checks"]["extraction"]["extraction_key"], "provenance is kept"
    assert recheck.recheck(repo)["changed"] == 0, "idempotent"
    # The client withdraws consent: every moment, the unverified record included, carries do_not_use.
    with repo.connection() as conn:
        conn.execute("UPDATE clients SET consent='no_use' WHERE client_id='client_dana'")
    again = recheck.recheck(repo, client_id="client_dana")
    assert again["changed"] == 5 and again["columns_changed"] == {"consent_status": 5, "checks": 5}
    assert {r["consent_status"] for r in rows(repo, "SELECT consent_status FROM key_moments")} == {"do_not_use"}
    assert recheck.recheck(repo)["changed"] == 0
    # A dry run reports and changes nothing.
    with repo.connection() as conn:
        conn.execute("UPDATE clients SET consent='anonymise_only' WHERE client_id='client_dana'")
    dry = recheck.recheck(repo, apply=False)
    assert dry["changed"] == 5 and dry["applied"] is False
    assert {r["consent_status"] for r in rows(repo, "SELECT consent_status FROM key_moments")} == {"do_not_use"}
    # Placing a speaker differently re-derives the type: the tag the model gave comes back when the line is a client's.
    praise = rows(repo, "SELECT * FROM key_moments WHERE checks->'extraction'->>'local_key'='p1'")[0]
    assert praise["moment_type"] == "observation" and praise["evidence_kind"] == "team_report"
    with repo.connection() as conn:
        speaker_map = conn.execute("SELECT speaker_map FROM transcripts WHERE transcript_id=%s", (docs["B"]["transcript_id"],)).fetchone()["speaker_map"]
        speaker_map["Carmen Cruickshank"]["role"] = "client"
        conn.execute("UPDATE transcripts SET speaker_map=%s WHERE transcript_id=%s", (Jsonb(speaker_map), docs["B"]["transcript_id"]))
    recheck.recheck(repo)
    praise = rows(repo, "SELECT * FROM key_moments WHERE moment_id=%s", praise["moment_id"])[0]
    assert praise["moment_type"] == "testimonial" and praise["evidence_kind"] == "direct_quote" and praise["speaker_role"] == "client"
    assert praise["moment_body"]["moment_type"] == "testimonial", "the body, the quote and the evidence are never touched"
    only = recheck.recheck(repo, ids=[praise["moment_id"]], apply=False)
    assert only["read"] == 1 and only["changed"] == 0


def test_a_consent_change_or_a_renormalisation_rederives_the_stored_moments_without_a_manual_recheck(ready):
    """2.B4 exit criterion ("a moment from a client with no_use consent carries do_not_use") must hold whenever the client's
    consent or the document's client changes after extraction, not only once someone remembers `moments recheck`."""
    from backend_pipeline import reference
    from backend_pipeline.documents.jobs import normalise
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    extract(repo, models, {"A": docs["A"]}, ScriptedProvider(standard_scripts()))
    document_id = docs["A"]["transcript_id"]
    before = rows(repo, "SELECT client_id,consent_status FROM key_moments WHERE document_id=%s", document_id)
    (added,) = {r["client_id"] for r in rows(repo, "SELECT client_id FROM transcripts WHERE transcript_id=%s", document_id)}
    assert added and {r["client_id"] for r in before} == {added}, "the account the title names was added at import (N10)"
    assert "do_not_use" not in {r["consent_status"] for r in before}, "the system's guess is anonymise_only"
    # 1. The reviewed client list arrives with this client as no_use: the first reviewed value replaces the system's guess.
    clients = tmp_path / "clients.json"
    clients.write_text(json.dumps([{"name": "Dana Lee", "consent": "no_use"}]), encoding="utf-8")
    with repo.connection() as conn:
        reference.import_clients(conn, clients)
    normalise(repo, document_id, models=models)
    (client_id,) = {r["client_id"] for r in rows(repo, "SELECT client_id FROM transcripts WHERE transcript_id=%s", document_id)}
    assert client_id, "the fixture's title names the client"
    after = rows(repo, "SELECT client_id,consent_status FROM key_moments WHERE document_id=%s", document_id)
    assert {(r["client_id"], r["consent_status"]) for r in after} == {(client_id, "do_not_use")}
    # 2. The client later allows naming: the consent change alone re-derives the client's moments.
    clients.write_text(json.dumps([{"name": "Dana Lee", "consent": "may_name"}]), encoding="utf-8")
    with repo.connection() as conn:
        reference.import_clients(conn, clients, update_consent=True)
    exact = rows(repo, "SELECT consent_status FROM key_moments WHERE checks->'extraction'->>'local_key'='s1'")[0]
    assert exact["consent_status"] == "cleared", "may_name, a public candidate and a direct quote"
    assert "do_not_use" not in {r["consent_status"] for r in rows(repo, "SELECT consent_status FROM key_moments")}
    assert recheck.recheck(repo)["changed"] == 0, "nothing was left for a manual recheck"


# ---- recall -------------------------------------------------------------------------------------------------------------------------

def write_golden(tmp_path, docs, **changes):
    golden = {"version": 1, "name": "synthetic", "scenes": [
        {"id": "g1", "document": {"transcript_id": docs["A"]["transcript_id"]}, "anchor": "We had 45 bookings in March", "kind": "quote"},
        {"id": "g2", "document": {"content_hash": docs["A"]["content_hash"]}, "anchor": "Nobody said this at all, ever."},
        {"id": "g3", "document": {"title": docs["B"]["title"]}, "anchor": "the client stopped dreading Monday after the form changed",
         "kind": "paraphrase", "min_overlap": 0.5},
        {"id": "g4", "document": {"transcript_id": docs["A"]["transcript_id"]}, "anchor": "pricing for the premium package"}]}
    golden.update(changes)
    path = tmp_path / "golden.json"
    path.write_text(json.dumps(golden), encoding="utf-8")
    return path


def test_scene_recall_is_measured_per_golden_scene_and_comparable_between_profiles(ready):
    repo, models, tmp_path = ready
    docs = import_documents(repo, models, tmp_path)
    v1_scripts = {MARK["A"]: lambda inv, n, system: response(inv, scene()), MARK["B"]: lambda inv, n, system: response(inv, notes=["Nothing."]),
                  MARK["C"]: lambda inv, n, system: response(inv, notes=["Nothing."])}
    extract(repo, models, docs, ScriptedProvider(v1_scripts), profile=SCENE_PROFILE)
    extract(repo, models, docs, ScriptedProvider(quiet_scripts()), profile=SCENE_V2_PROFILE)
    golden = recall.load_golden(write_golden(tmp_path, docs))
    with repo.connection() as conn:
        v1 = recall.measure(conn, golden, extractor_version=SCENE_PROFILE)
        v2 = recall.measure(conn, golden, extractor_version=SCENE_V2_PROFILE)
        both = recall.compare(conn, golden)
    assert (v1["found"], v1["recall"]) == (1, 0.25) and v1["missed"] == ["g2", "g3", "g4"] and v1["lost_to_quote_mismatch"] == []
    assert (v2["found"], v2["recall"]) == (2, 0.5)
    by_id = {r["id"]: r for r in v2["results"]}
    assert by_id["g1"]["match"] == "quote" and by_id["g3"]["match"] == "paraphrase" and by_id["g3"]["found"]
    assert by_id["g2"]["found"] is False and by_id["g2"]["lost_to_quote_mismatch"] is True, "seen, but its quote could not be bound"
    assert v2["lost_to_quote_mismatch"] == ["g2"] and v2["missed"] == ["g4"]
    assert both["versions"] == [SCENE_PROFILE, SCENE_V2_PROFILE] and both["recall"] == {SCENE_PROFILE: 0.25, SCENE_V2_PROFILE: 0.5}
    assert both["only_found_by"] == {SCENE_PROFILE: [], SCENE_V2_PROFILE: ["g3"]}
    # An anchor inside the passage the moment is anchored to counts, even when the model quoted another line of the turn.
    anchor_only = {"scenes": [{"id": "x", "document": {"transcript_id": docs["A"]["transcript_id"]}, "anchor": "talked about inquiries follow-up"}]}
    with repo.connection() as conn:
        assert recall.measure(conn, anchor_only, extractor_version=SCENE_V2_PROFILE)["found"] == 1


def test_a_golden_file_is_checked_when_it_is_read(tmp_path):
    def golden(*scenes):
        path = tmp_path / "g.json"
        path.write_text(json.dumps({"scenes": list(scenes)}), encoding="utf-8")
        return path
    ok = {"id": "a", "document": {"title": "T"}, "anchor": "some phrase"}
    assert recall.load_golden(golden(ok))["scenes"][0]["id"] == "a"
    for bad, why in [({**ok, "id": ""}, "unique id"), ({**ok, "anchor": " , "}, "anchor"), ({**ok, "document": {}}, "names its document"),
                     ({**ok, "kind": "vibes"}, "quote or paraphrase")]:
        with pytest.raises(ValueError, match=why):
            recall.load_golden(golden(bad))
    with pytest.raises(ValueError, match="unique id"):
        recall.load_golden(golden(ok, ok))
    with pytest.raises(ValueError, match="non-empty"):
        recall.load_golden(golden())
