"""Gate 2 on the migrated database (5.F1, 5.F4, 5.F5, 5.B6, 5.B7, 5.F2): a person edits any line of a v3 brief by its path,
the edit locks that line only, a refresh with feedback (writer v4.1, faked) keeps the edited line verbatim and rewrites
its siblings, a draft with no place for a locked line is refused, the versions list says who made each version and why,
context and attested facts are added at both gates, and the blockers are named. Synthetic fixtures and fake providers
only; the corrections are anonymised."""
from __future__ import annotations

import json

import pytest

from backend_pipeline.briefs import gate_two
from backend_pipeline.tests import test_brief_v3_db as v3db
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_sql_storage import drain

SUBJECT = "Why we ask about the first reply before the ads"
# WIA's 20 October correction W8, anonymised: who made the changes in the account.
CORRECTION_LINE = "Her AI assistant made the changes to the account."
CORRECTION_FACT = "The client's AI assistant made the changes to the account, not the client herself."


def refresher(provider, draft):
    """Make the fake writer answer a refresh (a packet with `current_brief`) with `draft(current_brief)`."""
    original = provider.json_call

    def json_call(*, stage, system, user, schema, fingerprint):
        packet = json.loads(user)
        if stage == "brief_write" and "current_brief" in packet:
            provider.packets["refresh"] = (system, packet)
            return draft(json.loads(json.dumps(packet["current_brief"]))), {"fake": True}
        return original(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
    provider.json_call = json_call


def rewrites_everything(brief):
    """A refresh that rewrites the preview and slide 1, and also (wrongly) the person's subject line."""
    email, slides = brief["format_plan"]["email"], brief["format_plan"]["carousel"]["slides"]
    email["subject_options"][0] = "A subject the writer preferred"
    email["preview"] = "What the first reply tells us about your ads."
    slides[0]["text"] = "Your ads start the conversation; the first reply decides it."
    return brief


def child_of(repo, brief_id):
    with repo.connection() as conn:
        row = conn.execute("SELECT brief_id FROM content_briefs WHERE supersedes_id=%s", (brief_id,)).fetchone()
    return gate_two.get(repo, row["brief_id"], APPROVER) if row else None


def run_error(repo, brief_id):
    with repo.connection() as conn:
        return [r["error_summary"] for r in conn.execute("""SELECT j.error_summary FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id)
            WHERE r.input_refs->>'revision_of'=%s AND j.error_summary IS NOT NULL""", (brief_id,))]


def test_an_edited_subject_line_survives_a_refresh_that_rewrites_its_siblings(platform_setup, monkeypatch):  # noqa: F811
    repo, provider, _, row, _, client, headers = v3db.build(platform_setup, monkeypatch=monkeypatch)
    bid = row["brief_id"]
    before = row["content_body"]["document"]["body"]["format_plan"]
    edited = client.patch(f"/storage/briefs/{bid}", headers=headers, json={
        "expected_hash": row["content_hash"], "changes": {"format_plan.email.subject_options[0]": SUBJECT}})
    assert edited.status_code == 200, edited.text
    row = gate_two.get(repo, edited.json()["brief_id"], APPROVER)
    plan = row["content_body"]["document"]["body"]["format_plan"]
    assert plan["email"]["subject_options"] == [SUBJECT, before["email"]["subject_options"][1]]
    assert row["content_body"]["review"]["locked_fields"] == ["format_plan.email.subject_options[0]"], "the line, not format_plan"
    assert row["locked_fields"] == ["format_plan.email.subject_options[0]"]
    # Nothing changed, an unknown path and a path outside the writer's sections are refused.
    for changes in ({"format_plan.email.subject_options[0]": SUBJECT}, {"format_plan.reels[7].cover_text": "x"}, {"claims[0].text": "x"}):
        assert client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers,
                            json={"expected_hash": row["content_hash"], "changes": changes}).status_code == 409, changes

    refresher(provider, rewrites_everything)
    queued = client.post(f"/storage/briefs/{row['brief_id']}/revise", headers=headers,
                         json={"expected_hash": row["content_hash"], "instructions": "Make the preview about the reader's ads.",
                               "mode": "replay"})
    assert queued.status_code == 202, queued.text
    with repo.connection() as conn:
        refs = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (queued.json()["run_id"],)).fetchone()["input_refs"]
    assert refs["writer"] == "v4.1", "a refresh of a v3 brief uses the writer that reads the instructions"
    assert refs["locked_fields"] == [{"path": "format_plan.email.subject_options[0]", "value": SUBJECT}]
    # Replay mode has no saved response for this new request; the synthetic run is the faked equivalent.
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_jobs SET status='failed' WHERE run_id=%s", (queued.json()["run_id"],))
        conn.execute("UPDATE pipeline_runs SET status='failed' WHERE run_id=%s", (queued.json()["run_id"],))
    gate_two.revise(repo, row["brief_id"], row["content_hash"], "Make the preview about the reader's ads.", APPROVER, "synthetic")
    drain(provider.worker, 20)
    child = child_of(repo, row["brief_id"])
    assert child, run_error(repo, row["brief_id"])
    system, packet = provider.packets["refresh"]
    assert "Make the preview about the reader's ads." in system and f'`format_plan.email.subject_options[0]`: "{SUBJECT}"' in system
    assert "## Lines a person wrote: keep them exactly" in system and "{{" not in system.split("Hi {{contact.first_name}}")[-1].replace(
        "{{contact.first_name}}", "")
    assert "current_brief" in packet
    after = child["content_body"]["document"]["body"]["format_plan"]
    assert after["email"]["subject_options"][0] == SUBJECT, "the edited line is identical"
    assert after["email"]["preview"] != plan["email"]["preview"] and after["carousel"]["slides"][0]["text"] != plan["carousel"]["slides"][0]["text"]
    review = child["content_body"]["review"]
    assert review["locked_fields"] == ["format_plan.email.subject_options[0]"]
    assert review["locks_restored"] == [{"path": "format_plan.email.subject_options[0]", "draft": "A subject the writer preferred",
                                         "stage": "writer"}]
    # The versions list: who made each version and why.
    versions = client.get(f"/storage/briefs/{child['brief_id']}/versions", headers=headers).json()
    assert [v["kind"] for v in versions] == ["generated", "edit", "refresh"]
    assert versions[1]["author"] == APPROVER and versions[1]["fields"] == ["format_plan.email.subject_options[0]"]
    assert versions[2]["reason"] == "Refreshed with feedback: Make the preview about the reader's ads." and versions[2]["author"] == APPROVER
    assert versions[0]["reason"].startswith("Written by the system")


def test_a_released_line_is_rewritten_and_a_draft_without_the_locked_line_is_refused(platform_setup, monkeypatch):  # noqa: F811
    repo, provider, _, row, _, client, headers = v3db.build(platform_setup, monkeypatch=monkeypatch)
    edited = client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers, json={
        "expected_hash": row["content_hash"], "changes": {"format_plan.reels[0].cover_text": "The one question we ask first",
                                                          "format_plan.email.subject_options[0]": SUBJECT}})
    row = gate_two.get(repo, edited.json()["brief_id"], APPROVER)
    assert row["content_body"]["review"]["locked_fields"] == ["format_plan.email.subject_options[0]", "format_plan.reels[0].cover_text"]
    with pytest.raises(ValueError, match="Only a locked line"):
        gate_two.revise(repo, row["brief_id"], row["content_hash"], "x", APPROVER, "synthetic", unlock=["format_plan.email.preview"])
    # Released for this refresh: the writer's subject stands, and the lock is gone from the new version.
    refresher(provider, rewrites_everything)
    gate_two.revise(repo, row["brief_id"], row["content_hash"], "Try another subject.", APPROVER, "synthetic",
                    unlock=["format_plan.email.subject_options[0]"])
    drain(provider.worker, 20)
    child = child_of(repo, row["brief_id"])
    assert child, run_error(repo, row["brief_id"])
    assert child["content_body"]["document"]["body"]["format_plan"]["email"]["subject_options"][0] == "A subject the writer preferred"
    assert child["content_body"]["review"]["locked_fields"] == ["format_plan.reels[0].cover_text"]
    assert child["content_body"]["document"]["body"]["format_plan"]["reels"][0]["cover_text"] == "The one question we ask first"
    # A draft that drops the locked Reel has no place for the person's line: refused, the current version stands.
    refresher(provider, lambda brief: {**brief, "format_plan": {**brief["format_plan"], "reels": []}})
    gate_two.revise(repo, child["brief_id"], child["content_hash"], "Drop the Reel.", APPROVER, "synthetic")
    drain(provider.worker, 20)
    assert child_of(repo, child["brief_id"]) is None
    assert any("no place for the locked line format_plan.reels[0].cover_text" in e for e in run_error(repo, child["brief_id"]))


def test_an_attested_correction_at_gate_two_passes_the_ledger(platform_setup, monkeypatch):  # noqa: F811
    # The writer's line says who made the changes; the call does not, so the verifier blocks it and the rejected repair
    # leaves it for Gate 2, as the 20 October brief did.
    monkeypatch.setattr(v3db, "UNSUPPORTED", CORRECTION_LINE)
    repo, _, top, row, _, client, headers = v3db.build(platform_setup, repair=v3db.hedges_the_line, monkeypatch=monkeypatch)
    assert any(CORRECTION_LINE in b for b in row["blockers"])
    assert any(i["kind"] == "blocking_finding" and CORRECTION_LINE in i["detail"] for i in row["blocker_items"])
    editor = {**headers, "X-Atelier-Actor": EDITOR, "X-Atelier-Email": EDITOR}
    body = {"kind": "attested_fact", "text": CORRECTION_FACT}
    assert client.post(f"/storage/briefs/{row['brief_id']}/context", headers=editor, json=body).status_code == 403, "an approver attests"
    added = client.post(f"/storage/briefs/{row['brief_id']}/context", headers=headers, json=body)
    assert added.status_code == 201, added.text
    new = gate_two.get(repo, added.json()["brief_id"], APPROVER)
    claims = new["content_body"]["document"]["body"]["claims"]
    line = next(c for c in claims if c["text"] == CORRECTION_LINE)
    assert line["status"] == "attested" and line["settled_by"] == "person" and line["attested"]["by"] == APPROVER
    assert line["attested"]["kind"] == "attested_fact" and len(line["attested"]["on"]) == 10
    fact = next(c for c in claims if c["field"] == "context_items")
    assert fact["text"] == CORRECTION_FACT and fact["status"] == "attested" and "attested at a gate by " + APPROVER in fact["note"]
    assert not any(CORRECTION_LINE in b for b in new["blockers"]), new["blockers"]
    assert not [f for f in new["content_body"]["review"]["findings"] if f["severity"] == "blocking" and f.get("claim_id") == line["claim_id"]]
    assert new["context_items"] == [{**new["context_items"][0], "kind": "attested_fact", "text": CORRECTION_FACT, "author": APPROVER,
                                     "gate": "gate_two", "in_brief": True}]
    versions = client.get(f"/storage/briefs/{new['brief_id']}/versions", headers=headers).json()
    assert versions[-1]["kind"] == "context" and versions[-1]["reason"] == f"Added an attested fact: {CORRECTION_FACT}"
    markdown = client.get(f"/storage/briefs/{new['brief_id']}/export.md", headers=headers).text
    assert f"attested by {APPROVER}" in markdown

    # A paraphrase of the client's words supports the copy, but is never put in quotation marks.
    para = client.post(f"/storage/briefs/{new['brief_id']}/context", headers=editor,
                       json={"kind": "paraphrase", "text": "She felt the ads were working until the replies slowed down."})
    assert para.status_code == 201, para.text
    new = gate_two.get(repo, para.json()["brief_id"], APPROVER)
    quoted = client.patch(f"/storage/briefs/{new['brief_id']}", headers=headers, json={
        "expected_hash": new["content_hash"],
        "changes": {"format_plan.caption.body": 'She told us "the ads were working until the replies slowed down". The reply carries it.'}})
    assert quoted.status_code == 200, quoted.text
    new = gate_two.get(repo, quoted.json()["brief_id"], APPROVER)
    assert any("is a paraphrase of the client's words" in b for b in new["blockers"]), new["blockers"]


def test_context_on_a_card_reaches_the_brief_writer(platform_setup, monkeypatch):  # noqa: F811
    repo, provider, top, row, _, client, headers = v3db.build(platform_setup, monkeypatch=monkeypatch)
    viewer = {**headers, "X-Atelier-Actor": "nobody@example.invalid", "X-Atelier-Email": "nobody@example.invalid"}
    note = {"kind": "context", "text": "Keep the story about the first reply; the owner is proud of the change."}
    assert client.post(f"/storage/angles/{top['angle_id']}/context", headers=viewer, json=note).status_code == 403
    assert client.post(f"/storage/angles/{top['angle_id']}/context", headers=headers, json={"kind": "rumour", "text": "x"}).status_code == 422
    added = client.post(f"/storage/angles/{top['angle_id']}/context", headers=headers, json=note)
    assert added.status_code == 201, added.text
    assert added.json()["context_items"][0]["text"] == note["text"] and added.json()["gate"] == "gate_one"
    week = client.get(f"/storage/weeks/{v3db.W1}", headers=headers).json()
    card = next(a for a in week["angles"] if a["angle_id"] == top["angle_id"])
    assert [i["text"] for i in card["context_items"]] == [note["text"]]
    shown = gate_two.get(repo, row["brief_id"], APPROVER)["context_items"]
    assert shown[0]["in_brief"] is False, "given after the brief was written: the next refresh carries it"
    refresher(provider, rewrites_everything)
    gate_two.revise(repo, row["brief_id"], row["content_hash"], "Use the note on the card.", APPROVER, "synthetic")
    drain(provider.worker, 20)
    child = child_of(repo, row["brief_id"])
    assert child, run_error(repo, row["brief_id"])
    _, packet = provider.packets["refresh"]
    assert packet["reviewer_context"] == [{"kind": "context", "text": note["text"], "given_by": APPROVER,
                                          "on": packet["reviewer_context"][0]["on"], "use": packet["reviewer_context"][0]["use"]}]
    assert [(i["text"], i["in_brief"]) for i in child["context_items"]] == [(note["text"], True)]


def test_gate_two_names_each_blocker(platform_setup, monkeypatch):  # noqa: F811
    repo, _, _, row, _, client, headers = v3db.build(platform_setup, repair=v3db.hedges_the_line, monkeypatch=monkeypatch)
    kinds = {i["kind"]: i for i in row["blocker_items"]}
    assert {"cta_unconfirmed", "open_question", "blocking_finding", "claims_check"} <= set(kinds), kinds
    assert kinds["cta_unconfirmed"]["title"] == "The call to action is still the writer's suggestion."
    assert kinds["open_question"]["action"] == 'Answer each required item under "Before publishing".'
    assert all("_" not in (i["detail"] or "") or "brief_" not in i["detail"] for i in row["blocker_items"])
    editor = gate_two.get(repo, row["brief_id"], EDITOR)
    assert any(i["kind"] == "role" and i["title"] == "Only an approver can approve this brief." for i in editor["blocker_items"])
    assert not any(i["kind"] == "role" for i in row["blocker_items"]), "an approver is not told about the role"
    edited = client.patch(f"/storage/briefs/{row['brief_id']}", headers=headers, json={
        "expected_hash": row["content_hash"], "changes": {"format_plan.email.preview": "It starts after the inquiry, every time."}})
    old = gate_two.get(repo, row["brief_id"], APPROVER)
    assert any(i["kind"] == "stale" and i["title"] == "A newer version of this brief exists." for i in old["blocker_items"])
    assert edited.status_code == 200
