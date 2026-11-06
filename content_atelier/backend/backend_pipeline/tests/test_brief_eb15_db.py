"""E.B15's verified remainder on the migrated database: Gate 2 re-checks a brief, and re-checks it after a person's edit,
with the rules of the knowledge-base version the brief pins (from the store, else the archive folder), never the files as
they are now; and a knowledge-base change in mid-run no longer strands the card: an editor or approver regenerates its
brief (V13, 4.B1's counter) through the API or `storage_cli brief --regenerate`, the old run kept and marked superseded.
Synthetic fixtures and fake providers only."""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import gate_one, storage_cli
from backend_pipeline.angle_profiles import STRATEGIST_V4_PROFILE
from backend_pipeline.briefs import gate_two, rules
from backend_pipeline.briefs.contracts import WORKFLOW
from backend_pipeline.briefs.runtime import CONTEXT_CHANGED
from backend_pipeline.chunk_encoding import queue as encode_chunks
from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.knowledge_base import publish
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.store import canonical_hash
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_brief_eb15 import _rule, _version
from backend_pipeline.tests.test_brief_v3_db import BriefV3Provider, build, removes_the_line
from backend_pipeline.tests.test_cards_sql import DECIDE, W1, W2, ranked
from backend_pipeline.tests.test_sql_storage import drain
from backend_pipeline.tests.test_strategist_profile import write_kb

ARCHIVED = BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-20.c-b953624b"


def ids(messages, prefix):
    return [m for m in messages if m.startswith(prefix)]


# Gate 2 and the pinned version's rules -----------------------------------------------------------------------------

def test_gate_two_and_a_person_s_edit_recheck_a_v3_brief_with_its_pinned_version_s_rules(platform_setup, monkeypatch, tmp_path):  # noqa: F811
    repo, _, _, row, _, client, headers = build(platform_setup, monkeypatch=monkeypatch)
    pinned = rules.pinned_version(row["content_body"]["provenance"])
    assert pinned == "kb-test.v1"
    # Today's files are another version, banning a phrase in the brief; the archive keeps the brief's own version, which
    # bans another.
    root = _version(tmp_path / "kb-today", "kb-today", [_rule("RR-TODAY", r"\bsingle ad\b")])
    _version(root / "archive" / pinned, pinned, [_rule("RR-PINNED", r"\binquiry\b")])
    monkeypatch.setenv("CONTENT_ATELIER_KNOWLEDGE_BASE_DIR", str(root))
    row = gate_two.get(repo, row["brief_id"], APPROVER)
    assert ids(row["blockers"], "RR-PINNED") and not ids(row["blockers"], "RR-TODAY"), row["blockers"]
    body = row["content_body"]["document"]["body"]
    edited = client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers, json={
        "expected_hash": row["content_hash"], "changes": {"wia_perspective": body["wia_perspective"] + " Then we read the reply."}})
    assert edited.status_code == 200, edited.text
    row = gate_two.get(repo, edited.json()["brief_id"], APPROVER)
    stored = [f["message"] for f in row["content_body"]["review"]["findings"]]
    assert ids(stored, "RR-PINNED") and not ids(stored, "RR-TODAY"), "the re-check after an edit uses the pinned version too"
    # A version Gate 2 cannot find blocks; it never falls back to today's rules.
    monkeypatch.setenv("CONTENT_ATELIER_KNOWLEDGE_BASE_DIR", str(tmp_path / "nowhere"))
    row = gate_two.get(repo, row["brief_id"], APPROVER)
    assert any("knowledge base kb-test.v1" in b and "neither the store" in b for b in row["blockers"]) and not row["can_approve"]


def test_a_version_in_the_store_is_read_from_the_store_before_any_folder(platform_url, platform_setup, tmp_path, monkeypatch):  # noqa: F811
    repo, _, _ = platform_setup
    monkeypatch.setenv("CONTENT_ATELIER_KNOWLEDGE_BASE_DIR", str(tmp_path / "no-folder"))
    with repo.connection() as conn:
        version = publish(conn, ARCHIVED, approver=APPROVER)["version"]
        archived = json.loads((ARCHIVED / "rejection-rules.patterns.json").read_text(encoding="utf-8"))["rules"]
        assert rules.version_patterns(conn, version) == archived, "published from files with its patterns"
        conn.execute("""UPDATE settings SET value=jsonb_set(value,'{patterns}',%s::jsonb) WHERE key=%s""",
                     (json.dumps([_rule("RR-STORE", "x")]), "knowledge_base.manifest." + version))
        loaded, problem = rules.pinned_rules(conn, {"pinned_inputs": {"knowledge_base": {"version": version}}})
        assert problem is None and [r["id"] for r in loaded] == ["RR-STORE"], "the store wins over the archive folder"
        with pytest.raises(LookupError):
            rules.version_patterns(conn, "kb-never-published")


# V13: regenerate after the pinned context changed mid-run ----------------------------------------------------------

def approved_card(platform_setup):  # noqa: F811
    """A developed card approved at Gate 1, its brief run queued and not yet run; contract v3 with writer v4."""
    repo, models, tmp = platform_setup
    repo.settings.brief_enabled = True
    repo.settings.brief_schema, repo.settings.brief_writer = "brief_document_v3", "v4"
    repo.settings.brief_model, repo.settings.brief_review_model = "openai/gpt-test", "anthropic/claude-test"
    card_models = models.model_copy(update={"angle_prompt_profile": STRATEGIST_V4_PROFILE, "knowledge_base_root": write_kb(tmp / "kb")})
    worker = SQLWorker(repo.settings, card_models, provider=BriefV3Provider(removes_the_line))
    repo.submit(W1, "synthetic", models=card_models)
    drain(worker)
    for week in (W1, W2):
        encode_chunks(repo, card_models, week)
    drain(worker)
    top = ranked(repo.review(W1, APPROVER))[0]
    ledger_ids = [f["id"] for f in top["content_body"]["ledger"]["flags"] if f["severity"] == "block"]
    approval = gate_one.decide(repo, top["angle_id"], top["content_hash"], "approved", DECIDE, False, "Checked." if ledger_ids else None,
                               APPROVER, verified=top["content_body"]["card"]["verify_before_publishing"] + ledger_ids)
    return repo, worker, tmp, top["angle_id"], approval["brief_run"]["run_id"]


def fail_mid_run(repo, worker, tmp, run_id, version):
    """The run freezes its context at its first stage; the knowledge base then changes, and its next stage fails."""
    drain(worker, 1)
    write_kb(tmp / "kb", version=version)
    drain(worker, 20)
    with repo.connection() as conn:
        run = conn.execute("SELECT status,error_summary,input_refs FROM pipeline_runs WHERE run_id=%s", (run_id,)).fetchone()
    assert run["status"] == "failed" and CONTEXT_CHANGED in run["error_summary"], run
    assert "--regenerate" in run["error_summary"], "the failure says what to do"
    return run


def runs_for(repo, angle_id):
    with repo.connection() as conn:
        return conn.execute("""SELECT run_id,status,input_refs,current_message FROM pipeline_runs WHERE run_scope='brief_generation'
            AND input_refs->'angle'->>'angle_id'=%s ORDER BY created_at""", (angle_id,)).fetchall()


def test_a_knowledge_base_change_mid_run_is_regenerated_with_a_counted_run_key(platform_setup, monkeypatch, capsys):  # noqa: F811
    repo, worker, tmp, angle_id, first = approved_card(platform_setup)
    fail_mid_run(repo, worker, tmp, first, "kb-test.v2")
    with repo.connection() as conn:
        packet_hash = conn.execute("SELECT approved_hash FROM content_angles WHERE angle_id=%s", (angle_id,)).fetchone()["approved_hash"]
    assert first == "brief_run_" + canonical_hash([WORKFLOW, angle_id, packet_hash])[:24], "the first run keeps its key"
    assert gate_two.research(repo, angle_id)["status"] == "failed"

    app = FastAPI()
    app.include_router(router(repo.settings))
    client = TestClient(app)
    start = f"/storage/angles/{angle_id}/brief"
    as_ = {"Authorization": "Bearer test-secret"}
    viewer = {**as_, "X-Atelier-Actor": "viewer@example.invalid", "X-Atelier-Email": "viewer@example.invalid"}
    editor = {**as_, "X-Atelier-Actor": EDITOR, "X-Atelier-Email": EDITOR}
    assert client.post(start, headers=viewer, json={"mode": "synthetic", "regenerate": True}).status_code == 403
    again = client.post(start, headers=editor, json={"mode": "synthetic"}).json()
    assert again == {"run_id": first, "status": "failed"}, "queueing again still finds the failed run"
    regenerated = client.post(start, headers=editor, json={"mode": "synthetic", "regenerate": True})
    assert regenerated.status_code == 202, regenerated.text
    second = regenerated.json()
    assert second["regeneration"] == 1 and second["regenerates"] == first and second["status"] == "queued"
    assert second["run_id"] == "brief_run_" + canonical_hash([WORKFLOW, angle_id, packet_hash, {"regeneration": 1}])[:24]
    old, new = runs_for(repo, angle_id)
    assert old["run_id"] == first and old["status"] == "failed", "the old run is kept as it ended"
    assert old["input_refs"]["superseded_by"]["run_id"] == second["run_id"] and old["input_refs"]["superseded_by"]["actor"] == EDITOR
    assert new["input_refs"]["regeneration"] == 1 and new["input_refs"]["regenerates"] == first
    with repo.connection() as conn:
        job = conn.execute("SELECT job_id FROM pipeline_jobs WHERE run_id=%s AND status='failed'", (first,)).fetchone()
        events = [e["event_type"] for e in conn.execute("SELECT event_type FROM pipeline_events WHERE run_id IN (%s,%s)", (first, second["run_id"]))]
    with pytest.raises(ValueError, match="superseded"):
        repo.retry(job["job_id"], APPROVER)
    assert {"brief_run_superseded", "brief_regenerated"} <= set(events)
    refused = client.post(start, headers=editor, json={"mode": "synthetic", "regenerate": True})
    assert refused.status_code == 409 and "pinned context changed" in refused.json()["detail"], "only a run that failed so"

    # The regenerated run fails the same way after another change; the command line regenerates it again, counting on.
    fail_mid_run(repo, worker, tmp, second["run_id"], "kb-test.v3")
    monkeypatch.setattr(storage_cli.StorageSettings, "from_env", classmethod(lambda cls: repo.settings))
    storage_cli.main(["brief", "--angle-id", angle_id, "--actor", APPROVER, "--regenerate"])
    third = json.loads(capsys.readouterr().out)
    assert third["regeneration"] == 2 and third["regenerates"] == second["run_id"]
    assert runs_for(repo, angle_id)[-1]["input_refs"]["mode"] == "synthetic", "without --mode, the replaced run's mode"
    drain(worker, 20)
    with repo.connection() as conn:
        brief = conn.execute("SELECT content_body FROM content_briefs WHERE angle_id=%s", (angle_id,)).fetchone()
    assert brief and brief["content_body"]["provenance"]["run_id"] == third["run_id"], "the regenerated run writes the brief"
    assert brief["content_body"]["provenance"]["pinned_inputs"]["knowledge_base"]["version"] == "kb-test.v3"
    research = gate_two.research(repo, angle_id)
    assert research["run_id"] == third["run_id"] and research["brief_id"]
