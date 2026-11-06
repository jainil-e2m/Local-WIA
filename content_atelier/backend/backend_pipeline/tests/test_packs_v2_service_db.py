"""NP.B2, NP.B3 and NP.B6 on the migrated database: Gate 2's approval of a v4 brief starts its content pack (and a v3 brief's
says why not); a pack is retried, superseded on a mode switch, and survives a failed queue; a pack's versions, edits, locks,
reverts, clearances, attestations, readiness, Finish again and published marks; the API round trip. Packs are written
synthetically from the brief's own copy (tests/pack_v2_service_fixtures.py), standing in for the stages; no model call (R48)."""
from __future__ import annotations

import pytest

from backend_pipeline.briefs import gate_two
from backend_pipeline.gates.roles import access_for
from backend_pipeline.packs import contracts_v2 as c2
from backend_pipeline.packs import model, queue, versions, views
from backend_pipeline.packs.contracts_v2 import PackAttest, PackClearance, PackCreate, PackDecisionV2, PackEdit
from backend_pipeline.production_common import ProductionError
from backend_pipeline.tests import pack_v2_service_fixtures as fx
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_brief_v3_db import v3  # noqa: F401 (fixture)
from backend_pipeline.tests.test_brief_v4_db import v4  # noqa: F401 (fixture)

PERMISSION_ANSWER = c2.CLIENT_OKAY_NOTE


def settle(repo, row):
    """Gate 2 settled the way the screen settles it: the CTA confirmed, every before-publishing item answered (a client's
    permission as the note for whoever posts), the claims checked."""
    row = gate_two.get(repo, gate_two.confirm_cta(repo, row["brief_id"], row["content_hash"],
                                                  {"choice": "explicit", "action": "Reply to this email"}, APPROVER)["brief_id"], APPROVER)
    answers = {f"P{i}": PERMISSION_ANSWER for i, _ in enumerate(row["content_body"]["document"]["body"]["before_publishing"], 1)}
    row = gate_two.get(repo, gate_two.answers(repo, row["brief_id"], row["content_hash"], answers, APPROVER)["brief_id"], APPROVER)
    claims = [c["claim_id"] for c in row["content_body"]["document"]["body"]["claims"]]
    row = gate_two.get(repo, gate_two.review(repo, row["brief_id"], row["content_hash"], claims, "Checked every claim", True,
                                             APPROVER)["brief_id"], APPROVER)
    assert row["can_approve"], row["blocker_items"]
    return row


@pytest.fixture
def ready(v4):  # noqa: F811
    repo, _, row, _, client, headers = v4
    repo.settings.packs_enabled = True
    return repo, settle(repo, row), client, headers


def approve(repo, row):
    return gate_two.decide(repo, row["brief_id"], row["content_hash"], "approved", "Ready.", APPROVER)


def made(repo, row, **kw):
    """An approved brief and its pack, finished synthetically; the pack roles set (list mode)."""
    started = approve(repo, row)["pack_run"]
    fx.finish(repo, started["pack_id"], **kw)
    repo.settings.pack_approvers, repo.settings.pack_editors = (APPROVER,), (EDITOR,)
    return started["pack_id"]


def detail(repo, pack_id, actor=APPROVER):
    return views.detail(repo, pack_id, actor)


def who(headers, email):
    return {**headers, "X-Atelier-Actor": email, "X-Atelier-Email": email}


def rows(repo, sql, *args):
    with repo.connection() as conn:
        return conn.execute(sql, args).fetchall()


# NP.B2: start on approval, and retry --------------------------------------------------------------------------------

def test_approving_a_v4_brief_starts_exactly_one_pack_and_an_approver_outside_the_pack_lists_gets_it(ready):
    repo, row, client, headers = ready
    assert not access_for(repo.settings, APPROVER).can("edit_packs"), "list mode: the approver is on no pack list"
    decided = approve(repo, row)
    started = decided["pack_run"]
    assert started["status"] == "queued" and started["mode"] == "synthetic" and "pack_note" not in decided
    assert started["run_id"].startswith("pack_run_") and started["pack_id"] == "pack_" + started["run_id"][len("pack_run_"):]
    (run,) = rows(repo, "SELECT * FROM pipeline_runs WHERE run_scope='pack_generation'")
    refs = run["input_refs"]
    assert run["run_id"] == started["run_id"] and run["trigger_type"] == "manual" and run["triggered_by"] == APPROVER
    assert refs["workflow"] == c2.VERSION and refs["mode"] == "synthetic" and refs["synthetic"] is True and refs["trigger"] == "gate_two"
    assert refs["brief"] == {"brief_id": row["brief_id"], "approved_hash": row["content_hash"], "week_id": row["week_id"],
                             "angle_id": row["angle_id"], "schema_version": "brief_document_v4"}
    assert refs["supersedes"] is None and refs["previous_manifest"] is None and refs["pack_id"] == started["pack_id"]
    assert refs["approval_delegated"] is True and refs["queued_by"] == APPROVER and "settings_snapshot" in refs
    expected = queue.run_and_pack(queue.intent(row["brief_id"], row["content_hash"], "synthetic"))
    assert (run["run_id"], started["pack_id"]) == expected, "the run id is the frozen contract's intent"
    (pack,) = rows(repo, "SELECT * FROM content_packs")
    assert pack["content_body"] is None and pack["contract_version"] == c2.VERSION and pack["production_run_id"] == run["run_id"]
    assert pack["title"] == row["content_body"]["document"]["body"]["approved_angle"]["title"]
    assert pack["source_brief_hash"] == row["content_hash"] and pack["supersedes_id"] is None
    jobs = sorted(rows(repo, "SELECT * FROM pipeline_jobs WHERE run_id=%s", run["run_id"]), key=lambda j: c2.STAGES.index(j["stage"]))
    assert [j["stage"] for j in jobs] == list(c2.STAGES) and {j["queue"] for j in jobs} == {"interactive"}
    assert [j["progress_details"]["dependencies"] for j in jobs] == [[]] + [[j["job_id"]] for j in jobs[:-1]]
    assert all(j["idempotency_key"] == f"{run['run_id']}:{j['stage']}" and j["pack_id"] == pack["pack_id"] for j in jobs)
    assert jobs[0]["job_id"] == queue.job_id(run["run_id"], "pack_assemble")
    events = rows(repo, "SELECT event_type,message,details FROM pipeline_events WHERE run_id=%s", run["run_id"])
    assert [e["event_type"] for e in events] == ["pack_queued"] and events[0]["details"]["pack_id"] == pack["pack_id"]
    brief_run = row["content_body"]["provenance"]["run_id"]
    said = rows(repo, "SELECT message FROM pipeline_events WHERE run_id=%s AND event_type='gate_two_approved'", brief_run)
    assert said[0]["message"] == "Gate 2 decision recorded; content pack queued"
    # Creating it again answers the same pack: approving or creating twice makes one pack.
    repo.settings.pack_editors = (EDITOR,)
    again = client.post(f"/storage/briefs/{row['brief_id']}/pack", headers=who(headers, EDITOR), json={"request_id": "request_create_again"})
    assert again.status_code == 202, again.text
    assert again.json() == {"pack_id": pack["pack_id"], "run_id": run["run_id"], "status": "finishing", "mode": "synthetic"}
    assert len(rows(repo, "SELECT 1 FROM content_packs")) == 1


@pytest.mark.parametrize("switches,mode", [((True, True), "live"), ((True, False), "replay"), ((False, False), "replay")])
def test_the_pack_runs_live_only_with_both_switches_on_and_in_replay_otherwise(ready, switches, mode):
    repo, row, _, _ = ready
    repo.settings.synthetic = False
    repo.settings.generation_enabled, repo.settings.pack_live_enabled = switches
    started = approve(repo, row)["pack_run"]
    assert started["mode"] == mode and started["status"] == "queued"
    (run,) = rows(repo, "SELECT input_refs FROM pipeline_runs WHERE run_scope='pack_generation'")
    assert run["input_refs"]["mode"] == mode and run["input_refs"]["synthetic"] is False


def test_with_packs_off_an_approval_starts_no_pack_and_says_why(ready):
    repo, row, _, _ = ready
    repo.settings.packs_enabled = False
    decided = approve(repo, row)
    assert decided["approval_status"] == "approved" and decided["pack_note"] == "Content packs are off" and "pack_run" not in decided
    assert not rows(repo, "SELECT 1 FROM pipeline_runs WHERE run_scope='pack_generation'")
    assert not rows(repo, "SELECT 1 FROM content_packs")


def test_a_v3_approval_starts_no_pack_says_why_and_create_refuses_it(v3):  # noqa: F811
    repo, _, _, row, _, client, headers = v3
    repo.settings.packs_enabled = True
    row = settle(repo, row)
    decided = approve(repo, row)
    assert decided["approval_status"] == "approved" and "pack_run" not in decided
    assert decided["pack_note"] == "Re-develop this brief as a v4 brief to get a content pack"
    assert not rows(repo, "SELECT 1 FROM pipeline_runs WHERE run_scope='pack_generation'")
    repo.settings.pack_editors = (APPROVER,)
    refused = client.post(f"/storage/briefs/{row['brief_id']}/pack", headers=headers, json={"request_id": "request_v3_pack"})
    assert refused.status_code == 409 and refused.json()["detail"] == {
        "code": "brief_not_v4", "message": "Re-develop this brief as a v4 brief to get a content pack"}


def test_the_approval_commits_when_the_pack_cannot_be_queued(ready, monkeypatch):
    repo, row, _, _ = ready
    real = queue.insert

    def broken(conn, table, record, **kw):
        if table == "content_packs":
            raise RuntimeError("storage refused the pack row")
        return real(conn, table, record, **kw)
    monkeypatch.setattr(queue, "insert", broken)
    decided = approve(repo, row)
    started = decided["pack_run"]
    assert started["status"] == "failed" and started["pack_id"] is None and "storage refused the pack row" in started["error"]
    assert gate_two.get(repo, row["brief_id"], APPROVER)["approval_status"] == "approved", "the approval stands"
    runs = rows(repo, "SELECT run_id,status,error_summary,input_refs FROM pipeline_runs WHERE run_scope='pack_generation'")
    assert [(r["run_id"].startswith("pack_run_unqueued_"), r["status"]) for r in runs] == [(True, "failed")], \
        "the savepoint rolled back the pack's own run; the failure is recorded apart"
    assert runs[0]["input_refs"]["queue_failure"].startswith("RuntimeError") and not rows(repo, "SELECT 1 FROM pipeline_jobs WHERE pack_id IS NOT NULL")


def test_a_failed_pack_is_retried_in_place_and_a_mode_switch_starts_a_run_that_supersedes_it(ready):
    repo, row, client, headers = ready
    started = approve(repo, row)["pack_run"]
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_jobs SET status='failed',error_summary='The assemble step stopped' WHERE run_id=%s AND stage='pack_assemble'",
                     (started["run_id"],))
        conn.execute("UPDATE pipeline_runs SET status='failed' WHERE run_id=%s", (started["run_id"],))
    pack = detail(repo, started["pack_id"])
    assert pack["state"] == "waiting" and "The assemble step stopped" in pack["state_reason"] and pack["pieces"] == []
    repo.settings.pack_editors = (APPROVER,)
    retried = client.post(f"/storage/briefs/{row['brief_id']}/pack", headers=headers, json={"request_id": "request_retry_pack"})
    assert retried.status_code == 202 and retried.json() == {**started, "status": "queued"}
    jobs = rows(repo, "SELECT status,current_message FROM pipeline_jobs WHERE run_id=%s AND stage='pack_assemble'", started["run_id"])
    assert jobs[0]["status"] == "queued" and "retry" in jobs[0]["current_message"]
    assert rows(repo, "SELECT status FROM pipeline_runs WHERE run_id=%s", started["run_id"])[0]["status"] == "queued"
    assert detail(repo, started["pack_id"])["state"] == "finishing"
    # The same request id answers the same receipt; a replay run once a person asks for replay is a new run that supersedes.
    assert client.post(f"/storage/briefs/{row['brief_id']}/pack", headers=headers,
                       json={"request_id": "request_retry_pack"}).json() == retried.json()
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_jobs SET status='failed' WHERE run_id=%s AND stage='pack_assemble'", (started["run_id"],))
    switched = client.post(f"/storage/briefs/{row['brief_id']}/pack", headers=headers, json={"request_id": "request_replay_pack", "mode": "replay"})
    assert switched.status_code == 202, switched.text
    new = switched.json()
    assert new["mode"] == "replay" and new["pack_id"] != started["pack_id"] and new["status"] == "queued"
    assert rows(repo, "SELECT supersedes_id FROM content_packs WHERE pack_id=%s", new["pack_id"])[0]["supersedes_id"] == started["pack_id"]
    assert detail(repo, started["pack_id"])["state"] == "superseded"


def test_a_pack_stuck_on_a_changed_contract_gets_a_new_run_from_the_brief(ready):
    """NP.X1: a run whose frozen contract changed (a new prompt profile) fails the same way on every retry, so creating the
    pack again starts a new run that supersedes it; the new run assembles from the brief, since the stuck one never
    finished."""
    from backend_pipeline.packs.runtime_v2 import CONTEXT_CHANGED_MESSAGE
    repo, row, client, headers = ready
    started = approve(repo, row)["pack_run"]
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_jobs SET status='failed',error_summary=%s WHERE run_id=%s AND stage='pack_assemble'",
                     (CONTEXT_CHANGED_MESSAGE, started["run_id"]))
        conn.execute("UPDATE pipeline_runs SET status='failed' WHERE run_id=%s", (started["run_id"],))
    repo.settings.pack_editors = (APPROVER,)
    again = client.post(f"/storage/briefs/{row['brief_id']}/pack", headers=headers, json={"request_id": "request_stuck_pack"})
    assert again.status_code == 202, again.text
    new = again.json()
    assert new["pack_id"] != started["pack_id"] and new["run_id"] != started["run_id"] and new["status"] == "queued"
    assert rows(repo, "SELECT supersedes_id FROM content_packs WHERE pack_id=%s", new["pack_id"])[0]["supersedes_id"] == started["pack_id"]
    from backend_pipeline.packs import stages
    assert stages.previous_pack(type("W", (), {"repo": repo})(), started["pack_id"]) is None, "it never finished: start from the brief"


def test_create_refuses_a_brief_not_yet_approved_and_needs_the_pack_role(ready):
    repo, row, client, headers = ready
    refused = client.post(f"/storage/briefs/{row['brief_id']}/pack", headers=headers, json={"request_id": "request_no_role"})
    assert refused.status_code == 403, "creating a pack needs edit_packs"
    repo.settings.pack_editors = (APPROVER,)
    pending = client.post(f"/storage/briefs/{row['brief_id']}/pack", headers=headers, json={"request_id": "request_pending"})
    assert pending.status_code == 409 and pending.json()["detail"]["code"] == "brief_not_approved"
    repo.settings.packs_enabled = False
    off = client.post(f"/storage/briefs/{row['brief_id']}/pack", headers=headers, json={"request_id": "request_packs_off"})
    assert off.status_code == 503 and off.json()["detail"]["code"] == "packs_disabled"


# NP.B3: versions, edits, locks, states, readiness, published --------------------------------------------------------

def test_an_edit_locks_the_line_makes_a_new_version_reruns_the_checks_and_refuses_a_stale_hash(ready):
    repo, row, client, headers = ready
    pack_id = made(repo, row)
    pack = detail(repo, pack_id, EDITOR)
    assert pack["state"] == "in_review" and pack["can_edit"] and not pack["can_decide"], "an editor edits; an approver decides"
    line = "The question we ask before we touch your ads"
    edited = client.patch(f"/storage/packs/{pack_id}/pieces/reel_1", headers=who(headers, EDITOR), json={
        "request_id": "request_edit_cover", "expected_manifest_hash": pack["manifest_hash"], "changes": {"cover_text": line}})
    assert edited.status_code == 200, edited.text
    saved = edited.json()
    assert saved["pack_id"] != pack_id and saved["state"] == "in_review" and saved["run_id"] == pack["run_id"]
    new = detail(repo, saved["pack_id"], EDITOR)
    reel = next(p for p in new["pieces"] if p["key"] == "reel_1")
    assert reel["content"]["cover_text"] == line and reel["brief_copy"]["cover_text"] != line
    (lock,) = [lock for lock in reel["locks"] if lock["path"] == "cover_text"]
    assert lock["author"] == EDITOR and lock["origin"] == "pack" and lock["delegated"] is True and lock["at"]
    assert reel["changes"][-1] == {"path": "cover_text", "kind": "edited", "before": pack["pieces"][2]["content"]["cover_text"],
                                   "after": line, "note": None}
    assert [v["kind"] for v in new["versions"]] == ["generated", "edit"] and new["versions"][1]["paths"] == ["cover_text"]
    assert new["change"]["kind"] == "edit" and new["change"]["by"] == EDITOR and new["supersedes_id"] == pack_id
    assert detail(repo, pack_id)["state"] == "superseded"
    stored = rows(repo, "SELECT validation_result FROM content_packs WHERE pack_id=%s", saved["pack_id"])[0]["validation_result"]
    assert stored["version"] == "pack_checks.v1" and isinstance(stored["findings"], list)
    decision = rows(repo, "SELECT * FROM decisions WHERE item_kind='pack' AND item_id=%s", saved["pack_id"])[0]
    assert decision["action"] == "pack_edit" and decision["actor"] == EDITOR and decision["details"]["paths"] == ["cover_text"]
    # The same request id answers the same version; a stale hash, the superseded version and a direction field are refused.
    assert client.patch(f"/storage/packs/{pack_id}/pieces/reel_1", headers=who(headers, EDITOR), json={
        "request_id": "request_edit_cover", "expected_manifest_hash": pack["manifest_hash"], "changes": {"cover_text": line}}).json() == saved
    stale = client.patch(f"/storage/packs/{saved['pack_id']}/pieces/reel_1", headers=who(headers, EDITOR), json={
        "request_id": "request_edit_stale", "expected_manifest_hash": pack["manifest_hash"], "changes": {"cover_text": "Another"}})
    assert stale.status_code == 409 and stale.json()["detail"] == {"code": "stale_pack", "message": "The pack changed; reload it"}
    old = client.patch(f"/storage/packs/{pack_id}/pieces/reel_1", headers=who(headers, EDITOR), json={
        "request_id": "request_edit_old", "expected_manifest_hash": pack["manifest_hash"], "changes": {"cover_text": "Another"}})
    assert old.status_code == 409 and old.json()["detail"]["code"] == "stale_pack"
    direction = client.patch(f"/storage/packs/{saved['pack_id']}/pieces/reel_1", headers=who(headers, EDITOR), json={
        "request_id": "request_edit_kind", "expected_manifest_hash": saved["manifest_hash"], "changes": {"kind": "stance"}})
    assert direction.status_code == 422 and direction.json()["detail"]["code"] == "not_editable"
    viewer = client.patch(f"/storage/packs/{saved['pack_id']}/pieces/reel_1", headers=who(headers, "viewer@example.invalid"), json={
        "request_id": "request_edit_view", "expected_manifest_hash": saved["manifest_hash"], "changes": {"cover_text": "x y z"}})
    assert viewer.status_code == 403


def test_a_revert_puts_the_brief_s_line_back_as_the_person_s_choice(ready):
    repo, row, _, _ = ready
    pack_id = made(repo, row)
    pack = detail(repo, pack_id)
    brief_line = pack["pieces"][0]["brief_copy"]["subject_options"][0]
    edited = versions.edit(repo, pack_id, "email", PackEdit(request_id="request_edit_subject", expected_manifest_hash=pack["manifest_hash"],
                                                           changes={"subject_options[0]": "Your inquiries deserve a faster first reply"}), EDITOR)
    reverted = versions.revert(repo, edited["pack_id"], "email", c2.PackRevert(
        request_id="request_revert_subject", expected_manifest_hash=edited["manifest_hash"], paths=["subject_options[0]"]), APPROVER)
    back = detail(repo, reverted["pack_id"])
    email = back["pieces"][0]
    assert email["content"]["subject_options"][0] == brief_line and email["changes"][-1]["kind"] == "reverted"
    assert [(lock["path"], lock["author"]) for lock in email["locks"]] == [("subject_options[0]", APPROVER)], "the person's choice, locked"
    assert [v["kind"] for v in back["versions"]] == ["generated", "edit", "revert"]
    with pytest.raises(ProductionError) as same:
        versions.revert(repo, reverted["pack_id"], "email", c2.PackRevert(
            request_id="request_revert_again", expected_manifest_hash=back["manifest_hash"], paths=["subject_options[0]"]), APPROVER)
    assert same.value.code == "no_change"


def test_ready_is_bound_to_the_manifest_an_open_client_permission_note_never_blocks_it_and_an_edit_after_ready_starts_in_review(ready):
    repo, row, client, headers = ready
    quote = {"quote_id": "Q1", "piece": "reel_1", "quote": "We improved the follow-up.", "speaker": "Alice", "evidence_id": None, "cleared": None}
    pack_id = made(repo, row, client_quotes=[quote])
    pack = detail(repo, pack_id)
    permission = [n for n in pack["before_publishing"] if n["client_permission"]]
    assert permission and not permission[0]["done"] and pack["client_quotes"][0]["cleared"] is None
    assert pack["ready_blockers"] == [] and pack["can_decide"], pack["ready_blockers"]
    decided = client.post(f"/storage/packs/{pack_id}/decision", headers=headers, json={
        "request_id": "request_ready_pack", "expected_manifest_hash": pack["manifest_hash"], "decision": "ready_to_publish", "note": "Good."})
    assert decided.status_code == 200, decided.text
    assert decided.json() == {"pack_id": pack_id, "manifest_hash": pack["manifest_hash"], "state": "ready_to_publish", "run_id": pack["run_id"]}
    (stored,) = rows(repo, "SELECT * FROM content_packs WHERE pack_id=%s", pack_id)
    assert stored["approval_status"] == "approved" and stored["approved_hash"] == stored["manifest_hash"] and stored["approved_by"] == APPROVER
    (decision,) = rows(repo, "SELECT * FROM decisions WHERE item_kind='pack' AND action='pack_ready_to_publish'")
    assert decision["disposition"] == "approve" and decision["expected_hash"] == pack["manifest_hash"]
    # A note marked done after Ready changes nothing about readiness: the marks are outside the manifest.
    cleared = versions.clearance(repo, pack_id, PackClearance(request_id="request_clear_p1", expected_manifest_hash=pack["manifest_hash"],
                                                              item_id=permission[0]["id"], reference="Client email of 3 October"), APPROVER)
    assert cleared == {"pack_id": pack_id, "manifest_hash": pack["manifest_hash"], "state": "ready_to_publish", "run_id": pack["run_id"]}
    versions.clearance(repo, pack_id, PackClearance(request_id="request_clear_q1", expected_manifest_hash=pack["manifest_hash"],
                                                    item_id="Q1", note="The client approved the words"), APPROVER)
    after = detail(repo, pack_id)
    done = next(n for n in after["before_publishing"] if n["id"] == permission[0]["id"])["done"]
    assert done["by"] == APPROVER and done["reference"] == "Client email of 3 October" and done["delegated"] is True
    assert after["client_quotes"][0]["cleared"]["reference"] is None, "no reference given, none invented"
    assert after["state"] == "ready_to_publish" and after["manifest_hash"] == pack["manifest_hash"]
    with pytest.raises(ProductionError) as twice:
        versions.clearance(repo, pack_id, PackClearance(request_id="request_clear_p1_again", expected_manifest_hash=pack["manifest_hash"],
                                                        item_id=permission[0]["id"], reference="x"), APPROVER)
    assert twice.value.code == "already_done"
    edited = versions.edit(repo, pack_id, "carousel", PackEdit(request_id="request_edit_after_ready", expected_manifest_hash=pack["manifest_hash"],
                                                              changes={"title": "When more inquiries still aren't turning into tours"}), EDITOR)
    assert edited["state"] == "in_review" and edited["pack_id"] != pack_id, "an edit after Ready makes a version that starts in review"
    back = versions.decide(repo, edited["pack_id"], PackDecisionV2(request_id="request_ready_again", expected_manifest_hash=edited["manifest_hash"],
                                                                  decision="ready_to_publish"), APPROVER)
    assert back["state"] == "ready_to_publish"
    review = versions.decide(repo, edited["pack_id"], PackDecisionV2(request_id="request_back_to_review", expected_manifest_hash=edited["manifest_hash"],
                                                                    decision="in_review", note="One more look"), APPROVER)
    assert review["state"] == "in_review" and rows(repo, "SELECT approved_hash FROM content_packs WHERE pack_id=%s", edited["pack_id"])[0]["approved_hash"] is None


def test_an_open_fidelity_finding_on_a_written_reel_blocks_ready_until_attested_or_edited(ready):
    repo, row, _, _ = ready

    def flag(bodies):
        reel = bodies["reel_2"]
        reel["origin"] = "written"
        reel["brief_copy"] = None
        reel["findings"] = [fx.fidelity("fid_stance_1", "script", reel["content"]["script"].split(". ")[0])]
    pack_id = made(repo, row, edit=flag)
    pack = detail(repo, pack_id)
    (blocker,) = pack["ready_blockers"]
    assert blocker.startswith("Reel 2:") and "attest it is true" in blocker and "fid_" not in blocker, "plain words (R50)"
    finding = next(f for f in pack["pieces"][3]["findings"] if f["source"] == "fidelity")
    assert finding["can_attest"] and finding["status"] == "open"
    with pytest.raises(ProductionError) as refused:
        versions.decide(repo, pack_id, PackDecisionV2(request_id="request_ready_blocked", expected_manifest_hash=pack["manifest_hash"],
                                                      decision="ready_to_publish"), APPROVER)
    assert refused.value.code == "pack_blocked" and "Reel 2" in str(refused.value)
    with pytest.raises(PermissionError):
        versions.attest(repo, pack_id, "fid_stance_1", PackAttest(request_id="request_attest_editor", expected_manifest_hash=pack["manifest_hash"],
                                                                  statement="Whitney said this on the call."), EDITOR)
    attested = versions.attest(repo, pack_id, "fid_stance_1", PackAttest(
        request_id="request_attest_stance", expected_manifest_hash=pack["manifest_hash"], statement="Whitney said this on the call."), APPROVER)
    after = detail(repo, attested["pack_id"])
    stored = next(f for f in after["pieces"][3]["findings"] if f["source"] == "fidelity")
    assert stored["status"] == "attested" and stored["resolution"]["note"] == "Whitney said this on the call."
    assert stored["resolution"]["by"] == APPROVER and after["ready_blockers"] == [] and after["change"]["kind"] == "attest"
    assert rows(repo, "SELECT action FROM decisions WHERE item_kind='pack' AND item_id=%s", attested["pack_id"])[0]["action"] == "pack_attest"


def test_an_edit_of_the_flagged_sentence_clears_its_finding(ready):
    repo, row, _, _ = ready

    def flag(bodies):
        bodies["reel_2"].update(origin="written", brief_copy=None,
                                findings=[fx.fidelity("fid_stance_2", "caption.hook", bodies["reel_2"]["content"]["caption"]["hook"])])
    pack_id = made(repo, row, edit=flag)
    pack = detail(repo, pack_id)
    assert pack["ready_blockers"]
    edited = versions.edit(repo, pack_id, "reel_2", PackEdit(request_id="request_edit_flagged", expected_manifest_hash=pack["manifest_hash"],
                                                            changes={"caption.hook": "Follow-up is part of the advertising we do."}), EDITOR)
    after = detail(repo, edited["pack_id"])
    stored = next(f for f in after["pieces"][3]["findings"] if f["source"] == "fidelity")
    assert stored["status"] == "cleared" and stored["resolution"]["note"] == "Edited by a person" and after["ready_blockers"] == []


def test_a_two_reel_pack_shows_the_missing_kind_as_not_written_and_ready_names_that_reason(ready):
    repo, row, _, _ = ready
    pack_id = made(repo, row, kinds=("story", "broll_text"))
    pack = detail(repo, pack_id)
    stance = next(p for p in pack["pieces"] if p["key"] == "reel_2")
    assert stance["origin"] == "not_written" and stance["content"] is None and stance["not_written_reason"] == fx.NOT_WRITTEN
    assert pack["ready_blockers"] == [f"Reel 2 (stance) was not written: {fx.NOT_WRITTEN}"]
    with pytest.raises(ProductionError) as blocked:
        versions.decide(repo, pack_id, PackDecisionV2(request_id="request_ready_two", expected_manifest_hash=pack["manifest_hash"],
                                                      decision="ready_to_publish"), APPROVER)
    assert "Reel 2 (stance) was not written" in str(blocked.value)


def test_marking_a_piece_published_leaves_the_pack_ready_and_records_its_edit_against_the_pack_copy(ready):
    repo, row, client, headers = ready
    pack_id = made(repo, row)
    pack = detail(repo, pack_id)
    versions.decide(repo, pack_id, PackDecisionV2(request_id="request_ready_publish", expected_manifest_hash=pack["manifest_hash"],
                                                  decision="ready_to_publish"), APPROVER)
    reel = pack["pieces"][2]
    final = reel["content"]["script"].replace("we ask one thing", "we always ask one question") + "\n\nThat's where we start."
    marked = client.post(f"/storage/packs/{pack_id}/pieces/reel_1/published", headers=who(headers, EDITOR), json={
        "request_id": "request_publish_reel", "published_on": "2026-10-20", "channel": "instagram", "final_text": final,
        "url": "https://www.instagram.com/p/example"})
    assert marked.status_code == 200, marked.text
    answer = marked.json()
    assert answer["state"] == "ready_to_publish" and answer["piece"] == "reel_1" and answer["pack_id"] == pack_id
    (published,) = rows(repo, "SELECT * FROM published_content")
    assert published["source_ref"] == f"pack:{row['brief_id']}:reel_1" and published["source_kind"] == "approved_brief"
    assert published["sibling_group"] == row["brief_id"] and published["brief_id"] == row["brief_id"] and published["status"] == "confirmed"
    assert published["channel"] == "reel" and published["details"]["capture"]["platform"] == "instagram"
    edit = published["details"]["edit"]
    assert edit["field"] == "published_reel" and edit["author"] == EDITOR and "we always ask one question" in edit["after"]
    assert "That's where we start." in edit["after"] and "we ask one thing" in edit["before"]
    after = detail(repo, pack_id)
    assert after["state"] == "ready_to_publish" and after["manifest_hash"] == pack["manifest_hash"]
    assert [m["channel"] for m in after["pieces"][2]["published"]] == ["instagram"] and after["pieces"][2]["published"][0]["by"] == EDITOR
    listing = views.listing(repo, APPROVER, brief_id=row["brief_id"])
    assert listing["items"][0]["pieces"][2] == {"key": "reel_1", "label": "Reel 1", "kind": "story", "origin": "brief", "published": True}
    different = client.post(f"/storage/packs/{pack_id}/pieces/reel_1/published", headers=who(headers, EDITOR), json={
        "request_id": "request_publish_other", "published_on": "2026-10-20", "channel": "instagram", "final_text": "Something else"})
    assert different.status_code == 409, "a different final for the same piece is refused, never replaced"


def test_finish_again_supersedes_the_version_with_a_finishing_run_and_no_edit_runs_during_it(ready):
    repo, row, client, headers = ready
    pack_id = made(repo, row)
    pack = detail(repo, pack_id)
    again = client.post(f"/storage/packs/{pack_id}/finish", headers=headers, json={
        "request_id": "request_finish_again", "expected_manifest_hash": pack["manifest_hash"]})
    assert again.status_code == 202, again.text
    new = again.json()
    assert new["state"] == "finishing" and new["pack_id"] != pack_id and new["manifest_hash"] is None
    (run,) = rows(repo, "SELECT input_refs FROM pipeline_runs WHERE run_id=%s", new["run_id"])
    assert run["input_refs"]["trigger"] == "finish_again" and run["input_refs"]["supersedes"] == pack_id
    assert run["input_refs"]["previous_manifest"] == pack["manifest_hash"]
    assert detail(repo, pack_id)["state"] == "superseded"
    finishing = detail(repo, new["pack_id"])
    assert finishing["state"] == "finishing" and finishing["run_active"] and not finishing["can_edit"] and finishing["pieces"] == []
    during = client.patch(f"/storage/packs/{new['pack_id']}/pieces/reel_1", headers=who(headers, EDITOR), json={
        "request_id": "request_edit_during", "expected_manifest_hash": pack["manifest_hash"], "changes": {"cover_text": "Another cover"}})
    assert during.status_code == 409 and during.json()["detail"]["code"] == "pack_running", "an edit during a run is refused"
    editor = client.post(f"/storage/packs/{pack_id}/finish", headers=who(headers, EDITOR), json={
        "request_id": "request_finish_editor", "expected_manifest_hash": pack["manifest_hash"]})
    assert editor.status_code == 403, "Finish again is an approver's"


# NP.B6: the API ------------------------------------------------------------------------------------------------------

def test_a_v4_pack_round_trips_through_the_api(ready):
    repo, row, client, headers = ready
    decided = client.post(f"/storage/briefs/{row['brief_id']}/decision", headers=headers, json={
        "expected_hash": row["content_hash"], "decision": "approved", "note": "Ready."})
    assert decided.status_code == 200, decided.text
    started = decided.json()["pack_run"]
    assert started["status"] == "queued" and started["mode"] == "synthetic"
    finishing = client.get(f"/storage/packs/{started['pack_id']}", headers=headers).json()
    assert finishing["state"] == "finishing" and finishing["pieces"] == [] and finishing["contract_version"] == c2.VERSION
    production = client.get(f"/storage/packs/{started['pack_id']}/production", headers=headers).json()
    assert production["state"] == "finishing" and [j["stage"] for j in production["jobs"]] == list(c2.STAGES)
    fx.finish(repo, started["pack_id"])
    repo.settings.pack_approvers = (APPROVER,)
    pack = client.get(f"/storage/packs/{started['pack_id']}", headers=headers).json()
    assert [p["key"] for p in pack["pieces"]] == list(c2.TAB_ORDER) and [p["ordinal"] for p in pack["pieces"]] == [1, 2, 3, 4, 5]
    assert [p["kind"] for p in pack["pieces"][2:]] == ["story", "stance", "broll_text"]
    assert pack["pieces"][0]["editable"] == list(c2.EDITABLE["email"]) and pack["state"] == "in_review"
    assert pack["can_edit"] and pack["can_decide"] and pack["can_finish_again"] and pack["can_mark_published"]
    assert pack["approval_delegated"] is True and pack["provenance"]["run_id"] == started["run_id"] and len(pack["versions"]) == 1
    listed = client.get("/storage/packs", headers=headers, params={"week_id": row["week_id"], "state": "in_review"}).json()
    assert listed["total"] == 1 and listed["items"][0]["pack_id"] == started["pack_id"] and listed["items"][0]["open_notes"] >= 1
    assert client.get("/storage/packs", headers=headers, params={"state": "ready_to_publish"}).json()["total"] == 0
    assert client.get("/storage/packs", headers=headers, params={"brief_id": row["brief_id"]}).json()["total"] == 1
    edited = client.patch(f"/storage/packs/{pack['pack_id']}/pieces/carousel", headers=headers, json={
        "request_id": "request_api_edit", "expected_manifest_hash": pack["manifest_hash"],
        "changes": {"slides[1].text": "More inquiries don't always mean more tours."}})
    assert edited.status_code == 200, edited.text
    reverted = client.post(f"/storage/packs/{edited.json()['pack_id']}/pieces/carousel/revert", headers=headers, json={
        "request_id": "request_api_revert", "expected_manifest_hash": edited.json()["manifest_hash"], "paths": ["slides[1].text"]})
    assert reverted.status_code == 200, reverted.text
    current = reverted.json()
    cleared = client.post(f"/storage/packs/{current['pack_id']}/clearances", headers=headers, json={
        "request_id": "request_api_clear", "expected_manifest_hash": current["manifest_hash"], "item_id": "P1", "reference": "Email"})
    assert cleared.status_code == 200 and cleared.json()["manifest_hash"] == current["manifest_hash"], cleared.text
    check = client.get(f"/storage/packs/{current['pack_id']}", headers=headers).json()
    some = next((f for p in check["pieces"] for f in p["findings"] if f["source"] == "check"), None)
    if some:
        refused = client.post(f"/storage/packs/{current['pack_id']}/findings/{some['finding_id']}/attest", headers=headers, json={
            "request_id": "request_api_attest", "expected_manifest_hash": current["manifest_hash"], "statement": "It is true."})
        assert refused.status_code == 409 and refused.json()["detail"]["code"] == "not_attestable"
    ready_now = client.post(f"/storage/packs/{current['pack_id']}/decision", headers=headers, json={
        "request_id": "request_api_ready", "expected_manifest_hash": current["manifest_hash"], "decision": "ready_to_publish"})
    assert ready_now.status_code == 200 and ready_now.json()["state"] == "ready_to_publish", ready_now.text
    published = client.post(f"/storage/packs/{current['pack_id']}/pieces/email/published", headers=headers, json={
        "request_id": "request_api_publish", "published_on": "2026-10-20", "channel": "email", "final_text": "The final email as sent."})
    assert published.status_code == 200 and published.json()["state"] == "ready_to_publish", published.text
    repo.settings.packs_enabled = False
    assert client.get(f"/storage/packs/{current['pack_id']}", headers=headers).status_code == 503
    assert client.get("/storage/packs", headers=headers).json()["detail"]["code"] == "packs_disabled"


def test_create_answers_an_approved_brief_s_existing_pack_unchanged(ready):
    repo, row, _, _ = ready
    pack_id = made(repo, row)
    answer = queue.create(repo, row["brief_id"], PackCreate(request_id="request_create_done"), EDITOR)
    assert answer["pack_id"] == pack_id and answer["status"] == "in_review"
    with repo.connection() as conn:
        assert model.current_for_brief(conn, row["brief_id"])["pack_id"] == pack_id and len(rows(repo, "SELECT 1 FROM content_packs")) == 1
