"""E.B15 and E.F4's API on the migrated database: a developed card gets a v2 brief, Gate 2 confirms its CTA, answers the
before-publishing items, reviews and decides it with a label, and v1 briefs and the v1-only pack gate are unchanged.
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
from backend_pipeline.tests.brief_v2_fixtures import v2_body
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_cards_sql import DECIDE, W1, W2, CardSQLProvider, ranked
from backend_pipeline.tests.test_sql_storage import drain
from backend_pipeline.tests.test_strategist_profile import write_kb


class BriefV2Provider(CardSQLProvider):
    def __init__(self):
        super().__init__()
        self.packets = {}

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage in ("brief_write", "brief_repair"):
            packet = json.loads(user)
            if "approved_angle" in packet or "brief" in packet:
                self.calls.append(stage)
                self.packets[stage] = (system, packet, schema)
                return (packet["brief"] if stage == "brief_repair" else v2_body(packet)), {"fake": True}
        return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)


@pytest.fixture
def v2(platform_setup, monkeypatch):  # noqa: F811
    return build(platform_setup, monkeypatch=monkeypatch)


def build(platform_setup, before_approval=None, *, monkeypatch):  # noqa: F811
    repo, models, tmp = platform_setup
    repo.settings.brief_enabled = True
    repo.settings.brief_schema = "brief_document_v2"
    card_models = models.model_copy(update={"angle_prompt_profile": STRATEGIST_V4_PROFILE, "knowledge_base_root": write_kb(tmp / "kb")})
    provider = BriefV2Provider()
    worker = SQLWorker(repo.settings, card_models, provider=provider)
    repo.submit(W1, "synthetic", models=card_models)
    drain(worker)
    for week in (W1, W2):
        encode_chunks(repo, card_models, week)
    drain(worker)
    if before_approval:
        before_approval(repo)
    top = ranked(repo.review(W1, APPROVER))[0]
    ledger_ids = [f["id"] for f in top["content_body"]["ledger"]["flags"] if f["severity"] == "block"]
    approval = gate_one.decide(repo, top["angle_id"], top["content_hash"], "approved", DECIDE, False, "Checked." if ledger_ids else None,
                               APPROVER, verified=top["content_body"]["card"]["verify_before_publishing"] + ledger_ids)
    drain(worker, 20)
    # Gate 2 re-checks the brief with the rules of the version it pins (briefs/rules.py): the test knowledge base is
    # that version, found where Gate 2 looks once the cards are made (it holds no lint patterns).
    monkeypatch.setenv("CONTENT_ATELIER_KNOWLEDGE_BASE_DIR", str(tmp / "kb"))
    with repo.connection() as conn:
        brief_id = conn.execute("SELECT brief_id FROM content_briefs WHERE angle_id=%s", (top["angle_id"],)).fetchone()["brief_id"]
        run = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (approval["brief_run"]["run_id"],)).fetchone()
    app = FastAPI()
    app.include_router(router(repo.settings))
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": APPROVER, "X-Atelier-Email": APPROVER}
    provider.worker = worker  # for tests that run a revision
    return repo, provider, top, gate_two.get(repo, brief_id, APPROVER), run["input_refs"], client, headers


def test_a_developed_card_gets_a_v2_brief_written_from_the_knowledge_base(v2):
    repo, provider, top, row, refs, _, _ = v2
    assert refs["schema_version"] == "brief_document_v2" and refs["channels"] == ["reel", "carousel", "email", "caption"]
    assert refs["execution_contract"]["knowledge_base"]["sha256"], "the knowledge base is in the run's execution contract"
    system, packet, schema = provider.packets["brief_write"]
    assert system.startswith("# ") and "Source passages, historical material" not in system, "the knowledge base is the prefix"
    assert packet["approved_angle"]["title"] == top["content_body"]["card"]["title"]
    assert "audit" not in json.dumps(packet) and packet["evidence"][0]["excerpt"]
    assert schema["$defs"]["FormatPlan"]["properties"]["stories"]["type"] == "null", "outside the channel set"
    document = row["content_body"]["document"]
    assert row["schema_version"] == "brief_document_v2" and document["header"]["cta"]["chosen_by"] == "writer"
    assert document["header"]["angle_id"] == top["angle_id"] and document["header"]["purpose"] == "WARM"
    assert set(document["header"]["pinned_inputs"]) == {"knowledge_base", "offer_sheet", "content_plan", "published_history"}
    assert not row["can_approve"] and not row["can_consume"]
    assert any("CTA is the writer's proposal" in b for b in row["blockers"])
    assert any("before-publishing" in b for b in row["blockers"])


def test_gate_two_confirms_the_cta_answers_reviews_and_decides_with_a_label(v2):
    repo, _, top, row, _, client, headers = v2
    repo.settings.wia_reviewers = ("Whitney Hodges",)  # the approver relays Whitney: the label is WIA's own
    bid = row["brief_id"]
    def post(path, body, email=APPROVER):
        return client.post(f"/storage/briefs/{bid}/{path}", headers={**headers, "X-Atelier-Actor": email, "X-Atelier-Email": email}, json=body)
    assert post("cta", {"expected_hash": row["content_hash"], "choice": "explicit"}).status_code == 409, "an explicit CTA needs its action"
    assert post("cta", {"expected_hash": row["content_hash"], "choice": "explicit", "action": "Reply $197"}).status_code == 409
    assert post("cta", {"expected_hash": "stale", "choice": "no_explicit_ask"}).status_code == 409
    assert post("cta", {"expected_hash": row["content_hash"], "choice": "no_explicit_ask"}, email="viewer@example.invalid").status_code == 403
    confirmed = post("cta", {"expected_hash": row["content_hash"], "choice": "explicit", "action": "Reply to this email"})
    assert confirmed.status_code == 200, confirmed.text
    row = gate_two.get(repo, confirmed.json()["brief_id"], APPROVER)
    assert row["content_body"]["document"]["header"]["cta"] == {"choice": "explicit", "track": None, "action": "Reply to this email",
                                                                "offer_connection": None, "chosen_by": "person"}
    assert not any("CTA" in b for b in row["blockers"])
    answered = gate_two.answers(repo, row["brief_id"], row["content_hash"], {"P1": "The client agreed on the call to be named."}, APPROVER)
    row = gate_two.get(repo, answered["brief_id"], APPROVER)
    with pytest.raises(ValueError, match="Unknown before-publishing item"):
        gate_two.answers(repo, row["brief_id"], row["content_hash"], {"P9": "x"}, APPROVER)
    claims = [c["claim_id"] for c in row["content_body"]["document"]["body"]["claims"]]
    reviewed = gate_two.review(repo, row["brief_id"], row["content_hash"], claims, "Checked every claim against the turns", True, APPROVER)
    row = gate_two.get(repo, reviewed["brief_id"], APPROVER)
    assert row["can_approve"], row["blockers"]
    edited = client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers,
                          json={"expected_hash": row["content_hash"], "changes": {"approved_angle": {"title": "x", "core_perspective": "y"}}})
    assert edited.status_code == 409, "the approved angle is not a section edit"
    decided = client.post(
        f"/storage/briefs/{row['brief_id']}/decision", headers=headers,
        json={"expected_hash": row["content_hash"], "decision": "approved", "note": "Ready for production.", "reason_code": "strong",
              "author": "Whitney Hodges"})
    assert decided.status_code == 200 and decided.json()["decision_id"], decided.text
    row = gate_two.get(repo, row["brief_id"], APPROVER)
    assert row["approval_status"] == "approved" and row["can_consume"], "an approved v2 brief with no blocker may be consumed (E.B23)"
    with repo.connection() as conn:
        decision = conn.execute("SELECT * FROM decisions WHERE item_kind='brief'").fetchone()
        label = conn.execute("SELECT * FROM calibration_labels WHERE item_kind='brief'").fetchone()
    assert decision["disposition"] == "approve" and decision["author"] == "Whitney Hodges" and decision["reason_code"] == "strong"
    assert label["decision_id"] == decision["decision_id"] and label["source"] == "gate"
    markdown = client.get(f"/storage/briefs/{row['brief_id']}/export.md", headers=headers).text
    assert markdown.index("## WIA perspective") < markdown.index("## Format plan") < markdown.index("## Evidence")
    assert "Reply to this email (confirmed by a person)" in markdown and "P1 (required)" in markdown
    contract = client.get("/storage/briefs/contract?schema_version=brief_document_v2", headers=headers).json()
    assert contract["title"] == "BriefDocumentV2"


def test_a_v2_section_edit_keeps_the_ledger_current(v2):
    repo, _, _, row, _, client, headers = v2
    body = row["content_body"]["document"]["body"]
    changed = client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers, json={
        "expected_hash": row["content_hash"], "changes": {"wia_perspective": body["wia_perspective"] + " We removed the old reply."}})
    assert changed.status_code == 200, changed.text
    new = gate_two.get(repo, changed.json()["brief_id"], APPROVER)
    assert "wia_perspective" in new["content_body"]["review"]["locked_fields"]
    assert any("review" in b for b in new["blockers"]), "a changed document needs its scoped review again"


def test_an_editor_cannot_answer_or_lower_a_before_publishing_item(v2):
    """E.B15, S.B3: answering a before-publishing item, or making a required one optional, is the approver's (the
    /answers route records who answered); an editor may still add or reword a check."""
    from backend_pipeline.tests.platform_db import EDITOR
    repo, _, _, row, _, client, _ = v2
    items = row["content_body"]["document"]["body"]["before_publishing"]
    assert any(i["required"] for i in items), "the fixture brief has a required item"

    def patch(email, before_publishing):
        headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": email, "X-Atelier-Email": email}
        return client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers,
                            json={"expected_hash": row["content_hash"], "changes": {"before_publishing": before_publishing}})
    answered = [{**i, "answer": "Checked with the client"} if i["required"] else i for i in items]
    lowered = [{**i, "required": False} for i in items]
    dropped = [i for i in items if not i["required"]]
    for change in (answered, lowered, dropped):
        assert patch(EDITOR, change).status_code == 403
    added = [*items, {"text": "Confirm the venue name is spelled as on its site.", "kind": "fact", "required": True, "answer": None}][:5]
    assert patch(EDITOR, added).status_code == 200


def test_a_client_without_consent_named_in_the_brief_blocks_until_a_clearance(platform_setup, monkeypatch):  # noqa: F811
    """Section 2.4 condition 7 on the pipeline: the reviewed client list (migration 007) reaches the v2 checks, a client
    named in public copy without consent to be named blocks Gate 2, and an approver's clearance on that client's own
    evidence lifts it. The fixture brief's carousel says "the first reply", which is this client's name here."""
    def client(repo):
        with repo.connection() as conn:
            conn.execute("INSERT INTO clients (client_id,name,aliases,consent) VALUES ('client_first','First Reply','[]','anonymise_only')")
            conn.execute("UPDATE transcripts SET client_id='client_first'")
    repo, _, _, row, _, _, _ = build(platform_setup, client, monkeypatch=monkeypatch)
    clients = row["content_body"]["provenance"]["clients"]
    assert [c["client_id"] for c in clients] == ["client_first"] and clients[0]["transcript_ids"]
    assert any("First Reply (a client)" in b for b in row["blockers"]), row["blockers"]
    evidence = next(e for e in row["selected_evidence"] if e["transcript_id"] in clients[0]["transcript_ids"])
    cleared = gate_two.clearance(repo, row["brief_id"], row["content_hash"], evidence["evidence_id"], "Owner agreed by email",
                                 "Owner", APPROVER)
    assert not any("First Reply" in b for b in gate_two.get(repo, cleared["brief_id"], APPROVER)["blockers"])


def revised_child(repo, provider, parent_id):
    drain(provider.worker, 20)
    with repo.connection() as conn:
        children = conn.execute("SELECT brief_id FROM content_briefs WHERE supersedes_id=%s", (parent_id,)).fetchall()
    assert len(children) == 1, children
    return gate_two.get(repo, children[0]["brief_id"], APPROVER)


def test_a_v2_revision_keeps_a_section_a_person_edited(v2):
    """Phase 5 exit (refine): an instruction produces a new version that keeps a previously edited section, and the
    lock carries forward; naming the section in the instruction (in words, as a person writes it) releases it."""
    repo, provider, _, row, _, _, _ = v2
    edited_text = row["content_body"]["document"]["body"]["wia_perspective"] + " We read the first reply before we touch the ads."
    edited = gate_two.edit(repo, row["brief_id"], row["content_hash"], {"wia_perspective": edited_text, "anchor": "carousel"}, APPROVER)
    gate_two.revise(repo, edited["brief_id"], edited["content_hash"], "Tighten the carousel", APPROVER, "synthetic")
    child = revised_child(repo, provider, edited["brief_id"])
    assert child["content_body"]["document"]["body"]["wia_perspective"] == edited_text, "the person's edit survives the revision"
    assert child["anchor"]["key"] == "carousel" and child["anchor"]["chosen_by"] == "person", "so does the anchor a person chose"
    assert "anchor" not in child["content_body"]["review"]["locked_fields"]
    assert "wia_perspective" in child["content_body"]["review"]["locked_fields"], "the lock carries forward"
    gate_two.revise(repo, child["brief_id"], child["content_hash"], "Rewrite the WIA perspective in plainer words", APPROVER, "synthetic")
    released = revised_child(repo, provider, child["brief_id"])
    assert released["content_body"]["document"]["body"]["wia_perspective"] != edited_text, "an explicit instruction releases it"


def test_packs_stay_off_by_flag_and_refuse_an_approved_v2_brief_without_breaking_it(v2):
    """E.B15 (b), R31: the pack gate is off by flag; switched on, it refuses a v2 brief by name (packs are mapped to v1),
    and the approved v2 row still reads, exports and blocks nothing."""
    from backend_pipeline.packs import workflow as packs
    from backend_pipeline.packs.contracts import Generate
    from backend_pipeline.production_common import ProductionError
    repo, _, _, row, _, client, headers = v2
    row = gate_two.get(repo, gate_two.confirm_cta(repo, row["brief_id"], row["content_hash"], {"choice": "no_explicit_ask"}, APPROVER)["brief_id"], APPROVER)
    row = gate_two.get(repo, gate_two.answers(repo, row["brief_id"], row["content_hash"], {"P1": "Checked."}, APPROVER)["brief_id"], APPROVER)
    claims = [c["claim_id"] for c in row["content_body"]["document"]["body"]["claims"]]
    row = gate_two.get(repo, gate_two.review(repo, row["brief_id"], row["content_hash"], claims, "Checked", True, APPROVER)["brief_id"], APPROVER)
    gate_two.decide(repo, row["brief_id"], row["content_hash"], "approved", "Ready.", APPROVER)
    payload = Generate(request_id="request_pack_v2", expected_brief_hash=row["content_hash"])
    repo.settings.pack_editors = (APPROVER,)
    with pytest.raises(ProductionError) as off:
        packs.queue(repo, row["brief_id"], payload, APPROVER)
    assert off.value.code == "packs_disabled"
    repo.settings.packs_enabled = True
    with pytest.raises(ProductionError) as unmapped:
        packs.queue(repo, row["brief_id"], payload, APPROVER)
    assert unmapped.value.code == "brief_v2_unmapped"
    approved = gate_two.get(repo, row["brief_id"], APPROVER)
    # E.B23: can_consume is honest for v2 (approved, no blocker); the pack workflow still refuses v2 by name, and production
    # reads the hand-off view when packs come into scope.
    assert approved["approval_status"] == "approved" and approved["blockers"] == [] and approved["can_consume"]
    assert client.get(f"/storage/briefs/{row['brief_id']}/export.md", headers=headers).status_code == 200
    view = client.get(f"/storage/briefs/{row['brief_id']}/handoff", headers=headers).json()
    assert view["schema_version"] == "brief_document_v2" and view["can_consume"] is True
    assert [(p["key"], p["anchor"]) for p in view["pieces"]] == [("reel_1", True), ("carousel", False), ("email", False), ("caption", False)]
    assert view["anchor"] == {**view["anchor"], "key": "reel_1", "chosen_by": "rule"}
    assert view["pieces"][0]["evidence_ids"], "a v2 piece keeps the evidence it cites"
    assert set(view["pieces"][2]["direction"]) == {"argument", "transformation"}
    assert view["cta"] == {"choice": "no_explicit_ask", "track": None, "action": None, "offer_connection": None, "chosen_by": "person"}
    assert view["before_publishing"][0]["id"] == "P1" and view["before_publishing"][0]["answer"] == "Checked."


def test_a_revision_does_not_treat_its_own_angle_as_prior_coverage(v2):
    """V14, 5.B12: the brief's own earlier versions are not prior coverage the revision must differ from."""
    repo, provider, top, row, _, _, _ = v2
    gate_two.revise(repo, row["brief_id"], row["content_hash"], "Tighten the carousel", APPROVER, "synthetic")
    child = revised_child(repo, provider, row["brief_id"])
    assert top["angle_id"] not in [p["angle_id"] for p in child["prior_content_context"]]
    assert top["angle_id"] not in [p["angle_id"] for p in provider.packets["brief_write"][1]["prior_coverage"]]

