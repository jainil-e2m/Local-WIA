"""E.B33, E.B34 and E.B24 on the migrated database: a developed card gets a contract v4 brief from writer v5 with the
first-touch data in its packet and its provenance; Gate 2 edits an asset line by its path and the first-touch checks run
on the edit; an attested fact settles the line that states it; a refresh with feedback keeps the edited line through
writer v5; the hand-off view, the Markdown export and the week's review document render v4. Synthetic fixtures and fake
providers only."""
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
from backend_pipeline.tests.brief_v4_fixtures import v4_body
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_cards_sql import DECIDE, W1, W2, CardSQLProvider, ranked
from backend_pipeline.tests.test_sql_storage import drain
from backend_pipeline.tests.test_strategist_profile import write_kb

VIEW = {"verdict": "view", "claim_class": "general_approach", "evidence_refs": [], "knowledge_base_document": None, "flag": None}


class BriefV4Provider(CardSQLProvider):
    """Writer v5 returns the v4 fixture (a refresh returns it again, so a locked line must be put back); the verifier calls
    every unsettled line WIA's view."""

    def __init__(self):
        super().__init__()
        self.packets = {}

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage in ("brief_write", "brief_repair", "brief_verify"):
            packet = json.loads(user)
            self.calls.append(stage)
            self.packets.setdefault(stage, []).append((system, packet, schema))
            if stage == "brief_verify":
                return {"statements": [{"id": s["id"], **VIEW} for s in packet["statements"]]}, {"fake": True}
            return v4_body(packet) if stage == "brief_write" else packet["brief"], {"fake": True}
        return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)


@pytest.fixture
def v4(platform_setup, monkeypatch):  # noqa: F811
    return develop(platform_setup, monkeypatch, "v5")


def develop(platform_setup, monkeypatch, writer):  # noqa: F811
    """A card developed into a contract v4 brief by `writer` (v5 here; writer v5.1's tests reuse it)."""
    repo, models, tmp = platform_setup
    repo.settings.brief_enabled = True
    repo.settings.brief_schema = "brief_document_v4"
    repo.settings.brief_writer = writer
    repo.settings.brief_model, repo.settings.brief_review_model = "openai/gpt-test", "anthropic/claude-test"
    card_models = models.model_copy(update={"angle_prompt_profile": STRATEGIST_V4_PROFILE, "knowledge_base_root": write_kb(tmp / "kb")})
    provider = BriefV4Provider()
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
    monkeypatch.setenv("CONTENT_ATELIER_KNOWLEDGE_BASE_DIR", str(tmp / "kb"))
    with repo.connection() as conn:
        found = conn.execute("SELECT brief_id FROM content_briefs WHERE angle_id=%s", (top["angle_id"],)).fetchone()
        errors = conn.execute("SELECT stage,status,error_summary FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at",
                              (approval["brief_run"]["run_id"],)).fetchall()
        assert found, [e["error_summary"] for e in errors if e["error_summary"]]
        run = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (approval["brief_run"]["run_id"],)).fetchone()
    app = FastAPI()
    app.include_router(router(repo.settings))
    headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": APPROVER, "X-Atelier-Email": APPROVER}
    provider.worker = worker
    return repo, provider, gate_two.get(repo, found["brief_id"], APPROVER), run["input_refs"], TestClient(app), headers


def test_a_v4_brief_is_written_by_writer_v5_with_the_first_touch_data(v4):
    repo, provider, row, refs, _, _ = v4
    assert refs["schema_version"] == "brief_document_v4" and refs["writer"] == "v5"
    assert refs["execution_contract"]["writer"] == "v5" and refs["execution_contract"]["first_touch_data"]
    system, packet, schema = provider.packets["brief_write"][0]
    assert "different doors" in system and "This is a refresh" not in system and "{{#" not in system
    assert {t["term"] for t in packet["insider_terms"]} >= {"office hours"}
    assert {o["offer"] for o in packet["offer_descriptors"]} >= {"ELEVATE", "Ads Accelerators"}
    assert "evidence_id" not in json.dumps(packet["evidence"]) and "ReelPlanV4" in schema["$defs"]
    body = row["content_body"]
    assert body["schema_version"] == "brief_document_v4" and body["review"]["review_kind"] == "ledger_v4"
    assert body["provenance"]["insider_terms"]["terms"] and body["provenance"]["offer_descriptors"]["offers"]
    assert body["document"]["header"]["schema_version"] == "brief_document_v4"
    assert not [f for f in body["review"]["findings"] if (f.get("check") or "").startswith("first_touch.")]


def test_gate_two_edits_an_asset_line_by_path_and_the_first_touch_checks_run_on_it(v4):
    repo, _, row, _, client, headers = v4
    edited = client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers, json={
        "expected_hash": row["content_hash"], "changes": {"format_plan.reels[1].cover_text": "Did I set this up wrong?"}})
    assert edited.status_code == 200, edited.text
    row = gate_two.get(repo, edited.json()["brief_id"], APPROVER)
    assert row["content_body"]["review"]["locked_fields"] == ["format_plan.reels[1].cover_text"]
    findings = row["content_body"]["review"]["findings"]
    assert any(f.get("check") == "first_touch.specific" and f["field"] == "format_plan.reels[1].cover_text" for f in findings)
    fixed = client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers, json={
        "expected_hash": row["content_hash"], "changes": {"format_plan.reels[1].cover_text": "Did I set my ads up wrong?"}})
    row = gate_two.get(repo, fixed.json()["brief_id"], APPROVER)
    assert not any(f.get("check") == "first_touch.specific" for f in row["content_body"]["review"]["findings"])
    # The hook gets an insider term: a blocking finding a person must clear before approval.
    blocked = client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers, json={
        "expected_hash": row["content_hash"], "changes": {"format_plan.reels[1].on_screen_hook": "One question from office hours"}})
    row = gate_two.get(repo, blocked.json()["brief_id"], APPROVER)
    assert any("office hours" in b for b in row["blockers"])


def test_a_refresh_keeps_the_edited_line_through_writer_v5(v4):
    repo, provider, row, _, client, headers = v4
    line = "Your inquiries deserve a faster first reply"
    edited = client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers, json={
        "expected_hash": row["content_hash"], "changes": {"format_plan.reels[1].cover_text": line}})
    row = gate_two.get(repo, edited.json()["brief_id"], APPROVER)
    gate_two.revise(repo, row["brief_id"], row["content_hash"], "Make the email's preview about the reader's ads.", APPROVER, "synthetic")
    drain(provider.worker, 20)
    system, packet, _ = provider.packets["brief_write"][-1]
    assert "Make the email's preview about the reader's ads." in system and f'`format_plan.reels[1].cover_text`: "{line}"' in system
    assert packet["current_brief"]["format_plan"]["reels"][1]["cover_text"] == line
    with repo.connection() as conn:
        child = conn.execute("SELECT brief_id FROM content_briefs WHERE supersedes_id=%s", (row["brief_id"],)).fetchone()
    child = gate_two.get(repo, child["brief_id"], APPROVER)
    assert child["content_body"]["document"]["body"]["format_plan"]["reels"][1]["cover_text"] == line
    assert child["content_body"]["review"]["locks_restored"][0]["path"] == "format_plan.reels[1].cover_text"
    assert child["content_body"]["change"]["writer"] == "v5"


def test_an_attested_fact_settles_the_line_and_the_who_did_what_check_reads_it(v4):
    repo, _, row, _, client, headers = v4
    fact = "Her inquiries were up, and the first reply took two days."
    added = client.post(f"/storage/briefs/{row['brief_id']}/context", headers=headers, json={"kind": "attested_fact", "text": fact})
    assert added.status_code == 201, added.text
    row = gate_two.get(repo, added.json()["brief_id"], APPROVER)
    claims = row["content_body"]["document"]["body"]["claims"]
    assert any(c["status"] == "attested" and c["field"] == "context_items" for c in claims)
    assert any(c["status"] == "attested" and c["field"].startswith("format_plan.reels[3]") for c in claims)


def test_the_v4_brief_renders_in_the_hand_off_the_export_and_the_review_document(v4):
    repo, _, row, _, client, headers = v4
    view = client.get(f"/storage/briefs/{row['brief_id']}/handoff", headers=headers)
    assert view.status_code == 200, view.text
    view = view.json()
    assert view["schema_version"] == "brief_document_v4" and [p["key"] for p in view["pieces"]] == ["reel_1", "reel_2", "reel_3", "carousel", "email"]
    assert view["channels_without_piece"] == [], "the captions travel with the Reels and the carousel"
    assert view["pieces"][2]["copy"]["screens"] and view["pieces"][4]["direction"]["send_header"]
    markdown = client.get(f"/storage/briefs/{row['brief_id']}/export.md", headers=headers).text
    assert markdown.index("## Central point") < markdown.index("## CTA and essential boundaries") < markdown.index("## Email")
    assert "**On-screen hook:**" in markdown and "**DATE:**" in markdown
    detail = client.get(f"/storage/briefs/{row['brief_id']}", headers=headers).json()
    assert detail["schema_version"] == "brief_document_v4" and detail["content_body"]["document"]["body"]["central_point"]
    contract = client.get("/storage/briefs/contract", headers=headers, params={"schema_version": "brief_document_v4"}).json()
    assert "BriefBodyV4" in json.dumps(contract)
    from backend_pipeline.briefs.review_document import render_week
    text = render_week(repo, row["week_id"])
    assert "(brief contract v4)" in text and "**On-screen hook:**" in text and "**Format:** b-roll with on-screen text" in text
