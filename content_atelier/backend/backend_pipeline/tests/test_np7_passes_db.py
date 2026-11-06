"""NP-7's two person-started passes end to end through the API (NP.B14, NP.B15), on the NP exit test's live fixture (every
model request through the real live provider to `FakeOpenRouter`, the `packs` standing budget):
- a recorded take on a face-to-camera Reel becomes its script word for word, locked as the person's; the caption and covers
  are written from it by `pack_caption`; the check reads only what the pass wrote, with the take among its sources; a flag
  that survives stays an open finding (the brief's caption is never put back); the b-roll Reel is refused;
- a granted "stronger with permission" item re-finishes the pack (`pack_refinish`) with the grant as evidence, attested
  and kept on the pack, so Finish again keeps it too; granting is an approver's.
Synthetic data and fake providers only (R48)."""
from __future__ import annotations

import json

import pytest

from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_m1_exit_db import live, ok, run  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_np_exit_db import PackBrain, approved_brief, pack_of

SAID = ("Before we touch anyone's ads, we ask one thing. How do you answer a new inquiry? One owner told us it usually takes "
        "two days to reply. So that's where we started.")
ADDED_IN_CAPTION = "Every owner we asked fixed their reply time that week."   # survives: an open finding
GRANT = "The owner now replies the same day; we may say so."


class PassBrain(PackBrain):
    """The NP exit test's brain, answering the two passes from their packets and recording what each one received."""

    seen: dict

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if not hasattr(self, "seen"):
            self.seen = {}
        if stage == "pack_caption":
            self.stages.append(stage)
            packet = json.loads(user)
            self.seen[stage] = packet
            return {"cover_text": "The one question before we touch your ads",
                    "cover_alternates": ["We start with your reply", "Two days to reply"],
                    "caption": {"hook": "Most of the sale happens after the inquiry.",
                                "body": f"One owner told us replies usually take two days. {ADDED_IN_CAPTION}",
                                "ending": "Save this for your next review. -Whitney"},
                    "no_offer_ending": None, "notes": ["Check the owner's line against the video."]}, {"fake": True}
        if stage == "pack_refinish":
            self.stages.append(stage)
            packet = json.loads(user)
            self.seen[stage] = packet
            answer = self.finish(packet)
            answer["stronger_with_permission"] = []
            return answer, {"fake": True}
        if stage == "pack_finish":
            self.seen.setdefault("pack_finishes", []).append(json.loads(user))
        if stage in ("pack_check", "pack_recheck"):
            packet = json.loads(user)
            self.seen.setdefault(stage + "s", []).append(packet)
            body, meta = super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
            for piece, leaves in packet["pack"].items():
                for text in leaves.values():
                    if ADDED_IN_CAPTION in text:
                        body["statements"].append({"piece": piece, "text": ADDED_IN_CAPTION, "verdict": "unsupported", "source": "",
                                                   "why": "Not in the take", "in_moment": None})
            return body, meta
        if stage == "pack_repair" and any(ADDED_IN_CAPTION in f["text"] for f in json.loads(user)["flagged"]):
            self.stages.append(stage)
            return {"patches": [{"piece": "reel_1", "old": "Words the repair misremembered.", "new": "x"}]}, {"fake": True}
        return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)


@pytest.fixture
def passes(live, monkeypatch):
    repo, fake, api, documents = live
    fake.brain.__class__ = PassBrain
    s = repo.settings
    s.packs_enabled = s.pack_live_enabled = True
    s.pack_writer_model, s.pack_review_model = "anthropic/claude-opus-5.5", "anthropic/claude-sonnet-5.5"
    s.pack_editors = s.pack_approvers = (APPROVER,)
    brief, decided = approved_brief(api, repo)
    run(repo, run_id=decided["pack_run"]["run_id"])
    pack = pack_of(api, brief["brief_id"])
    assert pack["state"] == "in_review", (pack["state"], pack["state_reason"])
    return repo, fake, api, brief, pack


def test_a_recorded_take_becomes_the_script_and_the_caption_and_covers_are_written_from_it(passes):
    repo, fake, api, brief, pack = passes
    broll = api("POST", f"/packs/{pack['pack_id']}/pieces/reel_3/recorded",
                {"request_id": "np7-take-broll", "expected_manifest_hash": pack["manifest_hash"], "said": SAID})
    assert broll.status_code == 422 and broll.json()["detail"]["code"] == "not_spoken", broll.text
    started = ok(api("POST", f"/packs/{pack['pack_id']}/pieces/reel_1/recorded",
                     {"request_id": "np7-take-1", "expected_manifest_hash": pack["manifest_hash"], "said": SAID}), 202)
    assert started["state"] == "finishing" and started["pack_id"] != pack["pack_id"]
    with repo.connection() as conn:
        jobs = [r["stage"] for r in conn.execute("SELECT stage FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at,job_id",
                                                 (started["run_id"],)).fetchall()]
    assert "pack_caption" in jobs and "pack_finish" not in jobs
    run(repo, run_id=started["run_id"])
    new = pack_of(api, brief["brief_id"])
    assert new["pack_id"] == started["pack_id"] and new["state"] == "in_review", (new["state"], new["state_reason"])
    reel = {p["key"]: p for p in new["pieces"]}["reel_1"]
    assert reel["content"]["script"] == SAID, "the take, word for word"
    assert any(lock["path"] == "script" and lock["origin"] == "pack" for lock in reel["locks"])
    assert reel["content"]["cover_text"] == "The one question before we touch your ads"
    assert reel["content"]["cover_alternates"] == ["We start with your reply", "Two days to reply"]
    # The pass's model saw what was said; the check read only the caption and covers, with the take as a source.
    assert fake.brain.seen["pack_caption"]["reel"]["said"] == SAID
    check = fake.brain.seen["pack_checks"][-1]
    assert set(check["pack"]) == {"reel_1"} and "script" not in check["pack"]["reel_1"]
    assert check["sources"]["recorded_take"] == {"reel_1": SAID}
    # The invented caption sentence survived the repair: an open finding on the Reel, never the brief's caption put back.
    (finding,) = [f for f in reel["findings"] if f["source"] == "fidelity" and f["status"] == "open"]
    assert ADDED_IN_CAPTION in finding["sentence"] and ADDED_IN_CAPTION in reel["content"]["caption"]["body"]
    assert new["change"]["kind"] == "recorded_take" and new["change"]["by"] == APPROVER
    assert any("Check the owner's line" in n for n in new["pack_notes"])
    assert "pack_caption" in fake.brain.stages and "pack_finish" not in fake.brain.stages[fake.brain.stages.index("pack_caption"):]
    # A later run (Finish again) still checks the caption against what was said (NP-7's shakedown finding).
    again = ok(api("POST", f"/packs/{new['pack_id']}/finish", {"request_id": "np7-take-again", "expected_manifest_hash": new["manifest_hash"]}), 202)
    run(repo, run_id=again["run_id"])
    assert fake.brain.seen["pack_checks"][-1]["sources"]["recorded_take"] == {"reel_1": SAID}


def test_a_granted_item_re_finishes_the_pack_with_it_as_attested_evidence_and_finish_again_keeps_it(passes):
    repo, fake, api, brief, pack = passes
    assert pack["stronger_with_permission"], "the finisher listed what a kept-out detail would add"
    item = pack["stronger_with_permission"][0]
    repo.settings.pack_approvers = ("someone-else@example.com",)
    refused = api("POST", f"/packs/{pack['pack_id']}/refinish",
                  {"request_id": "np7-grant-refused", "expected_manifest_hash": pack["manifest_hash"],
                   "grants": [{"item_id": "S1", "statement": GRANT}]})
    assert refused.status_code == 403, "granting is an approver's"
    repo.settings.pack_approvers = (APPROVER,)
    missing = api("POST", f"/packs/{pack['pack_id']}/refinish",
                  {"request_id": "np7-grant-missing", "expected_manifest_hash": pack["manifest_hash"],
                   "grants": [{"item_id": "S9", "statement": GRANT}]})
    assert missing.status_code == 404, missing.text
    started = ok(api("POST", f"/packs/{pack['pack_id']}/refinish",
                     {"request_id": "np7-grant-1", "expected_manifest_hash": pack["manifest_hash"],
                      "grants": [{"item_id": "S1", "statement": GRANT}]}), 202)
    run(repo, run_id=started["run_id"])
    new = pack_of(api, brief["brief_id"])
    assert new["pack_id"] == started["pack_id"] and new["state"] == "in_review", (new["state"], new["state_reason"])
    packet = fake.brain.seen["pack_refinish"]
    assert packet["mode"] == "refinish" and packet["granted"] == [{"item": item, "statement": GRANT}] and GRANT in packet["attested"]
    assert GRANT in fake.brain.seen["pack_checks"][-1]["sources"]["attested"], "the check counts the grant as supported"
    (grant,) = new["granted"]
    assert grant["statement"] == GRANT and grant["item"] == item and grant["by"] == APPROVER and grant["item_id"] == "S1"
    assert new["change"]["kind"] == "refinish" and new["stronger_with_permission"] == []
    # Finish again keeps the grant as evidence.
    again = ok(api("POST", f"/packs/{new['pack_id']}/finish", {"request_id": "np7-finish-1", "expected_manifest_hash": new["manifest_hash"]}), 202)
    run(repo, run_id=again["run_id"])
    later = pack_of(api, brief["brief_id"])
    assert later["pack_id"] == again["pack_id"] and later["granted"] == new["granted"]
    assert GRANT in fake.brain.seen["pack_finishes"][-1]["attested"], "Finish again keeps the grant as evidence"


def test_a_pass_refused_for_credit_says_why_and_a_retry_finishes_it(passes):
    repo, fake, api, brief, pack = passes
    started = ok(api("POST", f"/packs/{pack['pack_id']}/pieces/reel_1/recorded",
                     {"request_id": "np7-take-402", "expected_manifest_hash": pack["manifest_hash"], "said": SAID}), 202)
    fake.refuse = 402
    run(repo, run_id=started["run_id"])
    waiting = ok(api("GET", f"/packs/{started['pack_id']}"))
    assert waiting["state"] == "waiting" and "out of credit" in (waiting["state_reason"] or ""), waiting["state_reason"]
    fake.refuse = None
    with repo.connection() as conn:
        failed = [r["job_id"] for r in conn.execute("SELECT job_id FROM pipeline_jobs WHERE run_id=%s AND status IN ('failed','waiting')",
                                                     (started["run_id"],)).fetchall()]
    for job_id in failed:
        ok(api("POST", f"/jobs/{job_id}/retry", {}), 202)
    run(repo, run_id=started["run_id"])
    assert ok(api("GET", f"/packs/{started['pack_id']}"))["state"] == "in_review"


def test_a_pass_waits_on_a_spent_packs_budget_with_its_reason_and_finishes_when_raised(passes):
    from backend_pipeline.database import connect
    from backend_pipeline.llm import standing
    repo, fake, api, brief, pack = passes
    with connect(repo.settings.database_url, vectors=False) as conn:
        # Production runs uncapped (budgets.uncapped, 27 October); the capped mode this checks is switched on here.
        from backend_pipeline.settings_store import set_value
        set_value(conn, "budgets.uncapped", False, APPROVER)
        standing.set_cap(conn, "packs", APPROVER, usd=0.01)
        conn.commit()
    started = ok(api("POST", f"/packs/{pack['pack_id']}/refinish",
                     {"request_id": "np7-grant-budget", "expected_manifest_hash": pack["manifest_hash"],
                      "grants": [{"item_id": None, "statement": GRANT}]}), 202)
    run(repo, run_id=started["run_id"])
    waiting = ok(api("GET", f"/packs/{started['pack_id']}"))
    assert waiting["state"] == "waiting" and waiting["state_reason"].startswith("This week's content packs budget"), waiting["state_reason"]
    with connect(repo.settings.database_url, vectors=False) as conn:
        assert standing.set_cap(conn, "packs", APPROVER, usd=6.0)["released_jobs"]
        conn.commit()
    run(repo, run_id=started["run_id"])
    assert ok(api("GET", f"/packs/{started['pack_id']}"))["state"] == "in_review"
