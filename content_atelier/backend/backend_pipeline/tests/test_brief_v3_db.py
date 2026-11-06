"""E.B23 on the migrated database: a developed card gets a v3 brief from writer v4, its claims ledger is built after
writing (the rules, then the verifier from another family), repair runs only on blocking findings and is rejected when it
adds checking language to the copy, and Gate 2 confirms, answers, edits, reviews, decides and exports the v3 brief.
Synthetic fixtures and fake providers only."""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import gate_one
from backend_pipeline.angle_profiles import STRATEGIST_V4_PROFILE
from backend_pipeline.briefs import gate_two
from backend_pipeline.chunk_encoding import queue as encode_chunks
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.tests.brief_v3_fixtures import v3_body
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_cards_sql import DECIDE, W1, W2, CardSQLProvider, ranked
from backend_pipeline.tests.test_sql_storage import drain
from backend_pipeline.tests.test_strategist_profile import write_kb

UNSUPPORTED = "We rebuilt every client's follow-up last spring."
VIEW = {"verdict": "view", "claim_class": "general_approach", "evidence_refs": [], "knowledge_base_document": None, "flag": None}


class BriefV3Provider(CardSQLProvider):
    """Writer v4 returns copy with one line the call does not support; the verifier says so; the repair is configurable."""

    def __init__(self, repair=None):
        super().__init__()
        self.packets, self.verifier_calls, self.repair = {}, [], repair

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage in ("brief_write", "brief_repair", "brief_verify"):
            packet = json.loads(user)
            self.calls.append(stage)
            self.packets[stage] = (system, packet, schema)
            if stage == "brief_write":
                return v3_body(packet, wia_perspective="We look at what happens after the inquiry before we change a single ad. "
                                                       + UNSUPPORTED), {"fake": True}
            if stage == "brief_verify":
                self.verifier_calls.append(packet["statements"])
                out = [{"id": s["id"], **({"verdict": "unsupported", "claim_class": "particular_interaction", "evidence_refs": [],
                                           "knowledge_base_document": None,
                                           "flag": {"kind": "tense", "severity": "block", "message": "The call only plans it"}}
                                          if s["text"] == UNSUPPORTED else VIEW)} for s in packet["statements"]]
                return {"statements": out}, {"fake": True}
            return self.repair(packet["brief"]), {"fake": True}
        return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)


def removes_the_line(brief):
    return {**brief, "wia_perspective": brief["wia_perspective"].replace(" " + UNSUPPORTED, "")}


def hedges_the_line(brief):
    return {**brief, "wia_perspective": brief["wia_perspective"].replace(
        UNSUPPORTED, "We may rebuild follow-up, although that remains an idea to explore.")}


def build(platform_setup, repair=removes_the_line, *, monkeypatch):  # noqa: F811
    repo, models, tmp = platform_setup
    repo.settings.brief_enabled = True
    repo.settings.brief_schema = "brief_document_v3"
    repo.settings.brief_writer = "v4"
    # The verifier is the review model, from another family than the writer's (R42).
    repo.settings.brief_model, repo.settings.brief_review_model = "openai/gpt-test", "anthropic/claude-test"
    card_models = models.model_copy(update={"angle_prompt_profile": STRATEGIST_V4_PROFILE, "knowledge_base_root": write_kb(tmp / "kb")})
    provider = BriefV3Provider(repair)
    worker = SQLWorker(repo.settings, card_models, provider=provider)
    repo.submit(W1, "synthetic", models=card_models)
    drain(worker)
    for week in (W1, W2):
        encode_chunks(repo, card_models, week)
    drain(worker)
    top = ranked(repo.review(W1, APPROVER))[0]
    ledger_ids = [f["id"] for f in top["content_body"]["ledger"]["flags"] if f["severity"] == "block"]
    approval = gate_one.decide(repo, top["angle_id"], top["content_hash"], "approved", DECIDE, False, "Checked." if ledger_ids else None,
                               APPROVER, verified=top["content_body"]["card"]["verify_before_publishing"] + ledger_ids)
    drain(worker, 20)
    # Gate 2 re-checks the brief with the rules of the version it pins (briefs/rules.py): the test knowledge base is
    # that version, found where Gate 2 looks once the cards are made (it holds no lint patterns).
    monkeypatch.setenv("CONTENT_ATELIER_KNOWLEDGE_BASE_DIR", str(tmp / "kb"))
    with repo.connection() as conn:
        found = conn.execute("SELECT brief_id FROM content_briefs WHERE angle_id=%s", (top["angle_id"],)).fetchone()
        errors = conn.execute("SELECT stage,status,error_summary FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at",
                              (approval["brief_run"]["run_id"],)).fetchall()
        assert found, [e["error_summary"] for e in errors if e["error_summary"]]
        brief_id = found["brief_id"]
        run = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (approval["brief_run"]["run_id"],)).fetchone()
    app = FastAPI()
    app.include_router(router(repo.settings))
    headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": APPROVER, "X-Atelier-Email": APPROVER}
    provider.worker = worker
    return repo, provider, top, gate_two.get(repo, brief_id, APPROVER), run["input_refs"], TestClient(app), headers


@pytest.fixture
def v3(platform_setup, monkeypatch):  # noqa: F811
    return build(platform_setup, monkeypatch=monkeypatch)


def test_a_v3_brief_is_written_without_citations_and_its_ledger_is_built_after_writing(v3):
    repo, provider, top, row, refs, _, _ = v3
    assert refs["schema_version"] == "brief_document_v3" and refs["writer"] == "v4"
    contract = refs["execution_contract"]
    assert contract["writer"] == "v4" and set(contract["prompt_hashes"]) >= {"brief_write", "brief_repair", "brief_verify"}
    system, packet, schema = provider.packets["brief_write"]
    assert "You do not cite evidence or list claims" in system and system.startswith("# ")
    assert packet["evidence"] and all("evidence_id" not in e for e in packet["evidence"]), "the writer cites nothing"
    assert "evidence_ids" not in json.dumps(schema) and "claims" not in schema["properties"]
    verify_system, verify_packet, _ = provider.packets["brief_verify"]
    assert "attributed_experience" in verify_system and not verify_system.startswith("Source passages")
    assert "evidence_id" not in json.dumps(verify_packet), "turns reach the verifier as E1, E2, ..."
    assert provider.calls.count("brief_verify") == 1, "nothing new after the repair, so no second verifier call"
    assert provider.calls.count("brief_repair") == 1
    body = row["content_body"]
    assert row["schema_version"] == "brief_document_v3" and body["schema_version"] == "brief_document_v3"
    assert body["review"]["repair"] == {"used": True, "accepted": True, "findings": body["review"]["repair"]["findings"]}
    assert any(UNSUPPORTED in m for m in body["review"]["repair"]["findings"])
    assert UNSUPPORTED not in body["document"]["body"]["wia_perspective"], "the accepted repair removed the line"
    assert body["review"]["ledger"]["verifier"]["status"] == "run" and body["review"]["ledger"]["verifier"]["model"] == "anthropic/claude-test"
    assert body["provenance"]["beliefs"] is None or "statements" in body["provenance"]["beliefs"]
    assert not any(UNSUPPORTED in b for b in row["blockers"])
    assert any("CTA is the writer's proposal" in b for b in row["blockers"]) and not row["can_consume"]


def test_a_repair_that_adds_checking_language_is_rejected_and_the_finding_goes_to_gate_two(platform_setup, monkeypatch):  # noqa: F811
    repo, provider, _, row, _, _, _ = build(platform_setup, repair=hedges_the_line, monkeypatch=monkeypatch)
    review = row["content_body"]["review"]
    assert review["repair"]["used"] and review["repair"]["accepted"] is False
    assert "remains an idea" in review["repair"]["rejected_because"]
    perspective = row["content_body"]["document"]["body"]["wia_perspective"]
    assert UNSUPPORTED in perspective and "remains an idea" not in perspective, "the writer's copy stands"
    assert any(UNSUPPORTED in b for b in row["blockers"]), "the unsupported line blocks at Gate 2"


def test_gate_two_confirms_answers_edits_reviews_decides_and_exports_a_v3_brief(v3):
    repo, _, _, row, _, client, headers = v3
    bid = row["brief_id"]
    confirmed = client.post(f"/storage/briefs/{bid}/cta", headers=headers,
                            json={"expected_hash": row["content_hash"], "choice": "explicit", "action": "Reply to this email"})
    assert confirmed.status_code == 200, confirmed.text
    row = gate_two.get(repo, confirmed.json()["brief_id"], APPROVER)
    row = gate_two.get(repo, gate_two.answers(repo, row["brief_id"], row["content_hash"], {"P1": "Checked with the client."}, APPROVER)["brief_id"], APPROVER)
    body = row["content_body"]["document"]["body"]
    # A person's edit rebuilds the ledger without a model call; claims are not a section a person edits.
    assert client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers,
                        json={"expected_hash": row["content_hash"], "changes": {"claims": []}}).status_code == 409
    edited = client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers, json={
        "expected_hash": row["content_hash"], "changes": {"wia_perspective": body["wia_perspective"] + " The owner told us replies were slow."}})
    assert edited.status_code == 200, edited.text
    row = gate_two.get(repo, edited.json()["brief_id"], APPROVER)
    claims = row["content_body"]["document"]["body"]["claims"]
    added = next(c for c in claims if "The owner told us" in c["text"])
    assert added["status"] == "unchecked" and row["content_body"]["review"]["ledger"]["verifier"]["rebuilt_after_edit"]
    assert any("Check against the call" in f["message"] for f in row["content_body"]["review"]["findings"])
    reviewed = gate_two.review(repo, row["brief_id"], row["content_hash"], [c["claim_id"] for c in claims], "Checked each line", True, APPROVER)
    row = gate_two.get(repo, reviewed["brief_id"], APPROVER)
    assert row["can_approve"], row["blockers"]
    # E.B23: a person chooses the anchor through the edit route; it is not part of the reviewed document, so the check stands.
    assert row["anchor"]["key"] == "reel_1" and row["anchor"]["chosen_by"] == "rule"
    assert [o["key"] for o in row["anchor"]["options"]] == ["reel_1", "carousel", "email", "caption"]
    assert client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers,
                        json={"expected_hash": row["content_hash"], "changes": {"anchor": "reel_9"}}).status_code == 409
    anchored = client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers,
                            json={"expected_hash": row["content_hash"], "changes": {"anchor": "email"}})
    assert anchored.status_code == 200, anchored.text
    row = gate_two.get(repo, anchored.json()["brief_id"], APPROVER)
    assert row["anchor"]["key"] == "email" and row["anchor"]["chosen_by"] == "person" and row["anchor"]["actor"] == APPROVER
    assert row["can_approve"], row["blockers"]
    assert "anchor" not in row["content_body"]["review"]["locked_fields"]
    pending = client.get(f"/storage/briefs/{row['brief_id']}/handoff", headers=headers).json()
    assert pending["approval_status"] == "pending" and pending["can_consume"] is False
    decided = client.post(f"/storage/briefs/{row['brief_id']}/decision", headers=headers,
                          json={"expected_hash": row["content_hash"], "decision": "approved", "note": "Ready.", "reason_code": "strong"})
    assert decided.status_code == 200, decided.text
    markdown = client.get(f"/storage/briefs/{row['brief_id']}/export.md", headers=headers).text
    assert markdown.index("## WIA perspective") < markdown.index("## Format plan") < markdown.index("## Claims")
    assert "### Caption" in markdown and "Script:" in markdown and "- Do:" not in markdown, "the reader decision is optional"
    exported = client.get(f"/storage/briefs/{row['brief_id']}/export.json", headers=headers).json()
    assert exported["schema_version"] == "brief_document_v3" and exported["approval_status"] == "approved"
    assert exported["can_consume"] is True, "an approved v3 brief with no blocker may be consumed (E.B23)"
    handoff = client.get(f"/storage/briefs/{row['brief_id']}/handoff", headers=headers)
    assert handoff.status_code == 200, handoff.text
    view = handoff.json()
    assert view["handoff_version"] == "brief_handoff_v1" and view["schema_version"] == "brief_document_v3" and view["can_consume"] is True
    assert view["content_hash"] == row["content_hash"] and view["approved_hash"] == row["content_hash"]
    assert [(p["key"], p["channel"], p["platform"], p["anchor"]) for p in view["pieces"]] == [
        ("reel_1", "reel", "instagram", False), ("carousel", "carousel", "instagram", False), ("email", "email", "email", True),
        ("caption", "caption", "instagram", False)]
    assert view["anchor"]["key"] == "email" and view["anchor"]["chosen_by"] == "person"
    reel = view["pieces"][0]
    assert reel["copy"]["script"] and reel["direction"]["beats"] and reel["evidence_ids"] == []
    body = row["content_body"]["document"]["body"]
    assert view["message_spine"]["text"] == body["approved_angle"]["core_perspective"] and view["message_spine"]["source"] == "approved_angle"
    assert body["wia_perspective"] in view["message_spine"]["supporting"]
    assert view["cta"]["action"] == "Reply to this email" and view["cta"]["chosen_by"] == "person"
    assert view["before_publishing"] == [{**view["before_publishing"][0], "id": "P1", "answer": "Checked with the client."}]
    assert {c["claim_id"] for c in view["claims"]} == {c["claim_id"] for c in body["claims"]} and all(c["status"] for c in view["claims"])
    assert view["series"] is None and view["publishing_order"]["known"] is False, "a v4 strategist run has no publishing order"
    assert isinstance(view["topics"], list) and view["topic"] == (view["topics"][0] if view["topics"] else None)
    linked = [e for e in view["evidence"] if e["moment_ids"]]
    assert linked and all(e["consent_basis"] == "moments" and e["consent_status"] in ("cleared", "anonymise", "internal_only", "do_not_use")
                          for e in linked)
    with repo.connection() as conn:
        statuses = {r["moment_id"]: r["consent_status"] for r in conn.execute("SELECT moment_id,consent_status FROM key_moments")}
    assert all(e["consent_status"] == statuses[e["moment_ids"][0]] for e in linked if len(e["moment_ids"]) == 1)
    assert all(e["consent_status"] == "unknown" for e in view["evidence"] if not e["moment_ids"] and e["role"] != "external_framing")
    cited = {e["evidence_id"] for e in body["evidence"]} | {i for c in body["claims"] for i in c["evidence_ids"]}
    assert {e["evidence_id"] for e in view["evidence"] if e["cited"]} == cited
    assert {e["evidence_id"] for e in view["evidence"]} == {e["evidence_id"] for e in row["selected_evidence"]}
    # Consent is read on every request: a moment's client who allows no use shows at once (enforcing it is 4.B8's).
    moment_id = linked[0]["moment_ids"][0]
    with repo.connection() as conn:
        conn.execute("INSERT INTO clients (client_id,name,aliases,consent) VALUES ('client_none','No Use Venue','[]','no_use')")
        conn.execute("UPDATE key_moments SET consent_status='do_not_use', client_id='client_none' WHERE moment_id=%s", (moment_id,))
    again = client.get(f"/storage/briefs/{row['brief_id']}/handoff", headers=headers).json()
    item = next(e for e in again["evidence"] if moment_id in e["moment_ids"])
    assert item["consent_status"] == "do_not_use" and item["client_consent"] == "no_use"
    assert client.get("/storage/briefs/brief_missing/handoff", headers=headers).status_code in (404, 409)
    contract = client.get("/storage/briefs/contract?schema_version=brief_document_v3", headers=headers).json()
    assert contract["title"] == "BriefDocumentV3"
    listed = client.get("/storage/briefs", headers=headers).json()
    assert any(i["schema_version"] == "brief_document_v3" for i in listed["items"])


def test_a_v3_revision_keeps_the_contract_and_writer(v3):
    repo, provider, _, row, _, _, _ = v3
    gate_two.revise(repo, row["brief_id"], row["content_hash"], "Tighten the carousel", APPROVER, "synthetic")
    drain(provider.worker, 20)
    with repo.connection() as conn:
        child = conn.execute("SELECT brief_id FROM content_briefs WHERE supersedes_id=%s", (row["brief_id"],)).fetchone()
    child = gate_two.get(repo, child["brief_id"], APPROVER)
    assert child["schema_version"] == "brief_document_v3"
    _, packet, _ = provider.packets["brief_write"]
    assert "claims" not in packet["current_brief"] and "evidence" not in packet["current_brief"], "the writer revises copy, not the ledger"
