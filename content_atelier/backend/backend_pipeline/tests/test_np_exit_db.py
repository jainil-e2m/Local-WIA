"""The NP exit test (NP.X2; the content-packs plan, section 6, NP-5): an approver walks the content pack path through the API.

On M1's live fixture (the configuration of record applied as settings rows, live calls on, standing weekly budgets, no
run-plan variable, every model request through the real live provider to `FakeOpenRouter`), with packs switched on:
- a two-Reel v4 brief approved at Gate 2 queues its pack by itself, paid from this week's `packs` budget;
- the pack finishes into three Reels (the stance Reel written), a flagged sentence is repaired, a flag that survives the
  repair in a piece the brief had puts back the brief's sentence, and one in the written Reel stays an open finding;
- Ready is blocked by that finding, which an approver attests (R57); Ready is then allowed, with the client-permission
  note still listed (a note, never a gate);
- an edit locks its line, and Finish again keeps it word for word;
- the week's pack document exports every piece, a piece is marked published, and the person's edit reaches the learning
  loop's edit diffs.
The failure cases: a provider refusal for credit (402), a spent packs budget and its release, and a worker killed
mid-finish, each with its reason through the API and recovered. Synthetic data and fake providers only (R48).
"""
from __future__ import annotations

import json

import pytest

from backend_pipeline import settings_store
from backend_pipeline.database import connect
from backend_pipeline.llm import standing
from backend_pipeline.packs import contracts_v2 as c2
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_m1_exit_db import (Brain, WorkerKilled, current_cards, developed, ok, run, settle_gate_two,  # noqa: F401
                                                     live, start_cycle)

ADDED = "Every owner we work with agreed to change their reply time."            # repaired
REPAIRED = "Owners we work with often look at their reply time first."
DRIFT = "The owner said she was thrilled with the change right away."            # survives in a brief piece: put back
INVENTED = "We doubled her tours within a month of that call."                   # survives in the written Reel: attested
FACT = "The owner's tours rose after the reply time changed, per WIA's records."
EDIT = "The reply is where a booking starts, and we read it first."
MODEL_HOOK = "A hook the model wrote over a person's line."


def caption(hook, body, ending):
    return {"hook": hook, "body": body, "ending": ending}


class PackBrain(Brain):
    """M1's brain, with a brief that has no stance Reel and the pack's four model stages answered from their packets."""

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage == "brief_write":
            body, meta = super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
            body["format_plan"]["reels"] = [r for r in body["format_plan"]["reels"] if r["kind"] != "stance"]
            return body, meta
        if stage == "pack_finish":
            self.stages.append(stage)
            return self.finish(json.loads(user)), {"fake": True}
        if stage in ("pack_check", "pack_recheck"):
            self.stages.append(stage)
            return self.check(json.loads(user)), {"fake": True}
        if stage == "pack_repair":
            self.stages.append(stage)
            return {"patches": [{"piece": "email", "old": ADDED, "new": REPAIRED},
                                {"piece": "reel_1", "old": "Words the repair misremembered.", "new": "x"},
                                {"piece": "reel_2", "old": "Other words the repair misremembered.", "new": "x"}]}, {"fake": True}
        return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)

    @staticmethod
    def finish(packet):
        p = packet["pieces"]
        story, broll, email, carousel = p["reel_1"], p["reel_3"], p["email"], p["carousel"]
        again = not p["reel_2"].get("missing")  # Finish again: the pack's own copy, the stance Reel already written

        def reel(src, kind, **over):
            base = {"kind": kind, "title": f"The {kind} Reel", "job": src.get("job") or f"The {kind} door",
                    "cover_text": src.get("cover_text") or "Your first reply is part of your ads",
                    "cover_alternates": ["The reply is the ad", "Follow-up sells the tour"],
                    "on_screen_hook": src.get("on_screen_hook") or "Your follow-up is advertising",
                    "spoken_opening": None if kind == "broll_text" else (src.get("spoken_opening") or "Here's what I believe."),
                    "script": None if kind == "broll_text" else (src.get("script") or "Here's what I believe about follow-up."),
                    "screens": (src.get("screens") or ["One"]) if kind == "broll_text" else None,
                    "beats": src.get("beats") or ["The point"],
                    "caption": src.get("caption") or caption("Follow-up is advertising.", "We read the reply first.", "-Whitney"),
                    "personal_lines": [], "read_time_seconds": src.get("read_time_seconds") or 40, "cta": "none",
                    "no_offer_ending": None, "offer_descriptor": None}
            return {**base, **over}
        stance_script = (p["reel_2"].get("script") if again else
                         f"Here's what I believe about follow-up. The reply is part of the advertising. {INVENTED}")
        return {
            "email": {"subject_options": [*email["subject_options"], "Your inquiries are up. Now what?"][:3], "preview": email["preview"],
                      "opening": email["opening"], "body": email["body"] if again else email["body"] + "\n\n" + ADDED,
                      "ending": email["ending"], "offer_descriptor": None, "cta": "reply"},
            "reels": [reel(story, "story", script=story["script"] if again else story["script"] + " " + DRIFT),
                      reel(p["reel_2"] if again else {}, "stance", script=stance_script),
                      reel(broll, "broll_text", caption={**broll["caption"], "hook": MODEL_HOOK})],
            "carousel": {"title": carousel["title"], "slides": [{"number": s["number"], "text": s["text"]} for s in carousel["slides"]],
                         "caption": carousel["caption"], "cta": "none", "no_offer_ending": None, "offer_descriptor": None},
            "client_quotes": [], "stronger_with_permission": ["The owner's tour numbers would make the story land harder."],
            "pack_notes": [], "change_notes": ["Finished every piece"]}

    @staticmethod
    def check(packet):
        out = []
        for piece, leaves in packet["pack"].items():
            for path, text in leaves.items():
                for sentence in (ADDED, DRIFT, INVENTED):
                    if sentence in text:
                        out.append({"piece": piece, "text": sentence, "verdict": "unsupported", "source": "",
                                    "why": "Not in the call", "in_moment": None})
                if REPAIRED in text:
                    out.append({"piece": piece, "text": REPAIRED, "verdict": "supported", "source": "the brief's claims",
                                "why": "A belief WIA states", "in_moment": None})
        return {"statements": out}


@pytest.fixture
def packs(live, monkeypatch):
    repo, fake, api, documents = live
    fake.brain.__class__ = PackBrain
    s = repo.settings
    s.packs_enabled = s.pack_live_enabled = True
    s.pack_writer_model, s.pack_review_model = "anthropic/claude-opus-5.5", "anthropic/claude-sonnet-5.5"
    # No users rows here: the lists decide, as on a deployment that has not seeded users (production has a users row).
    s.pack_editors = s.pack_approvers = (APPROVER,)
    return repo, fake, api


def approved_brief(api, repo):
    card, research = developed(api, repo)
    run(repo, run_id=research["run_id"])
    research = ok(api("GET", f"/angles/{card['angle_id']}/research"))
    brief = settle_gate_two(api, ok(api("GET", f"/briefs/{research['brief_id']}")))
    assert [r["kind"] for r in brief["content_body"]["document"]["body"]["format_plan"]["reels"]] == ["story", "broll_text"]
    decided = ok(api("POST", f"/briefs/{brief['brief_id']}/decision", {"expected_hash": brief["content_hash"], "decision": "approved",
                                                                        "reason_code": "strong", "note": "Ready.", "author": None}))
    return brief, decided


def pack_of(api, brief_id):
    page = ok(api("GET", "/packs", brief_id=brief_id))
    assert page["total"] == 1, page
    return ok(api("GET", f"/packs/{page['items'][0]['pack_id']}"))


def test_np_exit_an_approved_brief_becomes_a_checked_pack_that_a_person_reviews_edits_and_publishes(packs):
    repo, fake, api = packs
    brief, decided = approved_brief(api, repo)

    # 1. Gate 2 approval queues the pack by itself, live, under this week's packs budget (D43c, D43f).
    started = decided["pack_run"]
    assert started and started["mode"] == "live" and started["pack_id"], decided
    run(repo, run_id=started["run_id"])
    pack = pack_of(api, brief["brief_id"])
    assert pack["state"] == "in_review", (pack["state"], pack["state_reason"])
    with repo.connection() as conn:
        plan = conn.execute("SELECT * FROM run_plans WHERE plan_id LIKE 'plan_standing_packs_%'").fetchone()
    assert plan and plan["calls_used"] >= 4, "finish, check, repair and re-check spent the packs budget"
    assert [s for s in fake.brain.stages if s.startswith("pack_")] == ["pack_finish", "pack_check", "pack_repair", "pack_recheck"]

    # 2. Three Reels of the three kinds; the repaired sentence, the put-back sentence and the open finding.
    pieces = {p["key"]: p for p in pack["pieces"]}
    assert [pieces[k]["kind"] for k in ("reel_1", "reel_2", "reel_3")] == ["story", "stance", "broll_text"]
    assert pieces["reel_2"]["origin"] == "written" and pieces["reel_1"]["origin"] == "finished"
    assert REPAIRED in pieces["email"]["content"]["body"] and ADDED not in pieces["email"]["content"]["body"]
    assert DRIFT not in pieces["reel_1"]["content"]["script"], "a surviving flag in a brief piece puts back the brief's sentence"
    assert any(c["kind"] == "put_back" for c in pieces["reel_1"]["changes"])
    (finding,) = [f for f in pieces["reel_2"]["findings"] if f["source"] == "fidelity"]
    assert finding["status"] == "open" and finding["severity"] == "blocking" and INVENTED in finding["sentence"]

    # 3. Ready is blocked by the open finding, in words; the before-publishing notes never block.
    assert pack["ready_blockers"], "an open finding on the written Reel blocks Ready, in words"
    refused = api("POST", f"/packs/{pack['pack_id']}/decision", {"request_id": "np-ready-1", "expected_manifest_hash": pack["manifest_hash"],
                                                               "decision": "ready_to_publish", "note": None})
    assert refused.status_code == 409, refused.text
    assert any(n["client_permission"] for n in pack["before_publishing"]), "the client's okay is a note on the pack"
    ok(api("POST", f"/packs/{pack['pack_id']}/findings/{finding['finding_id']}/attest",
           {"request_id": "np-attest-1", "expected_manifest_hash": pack["manifest_hash"], "statement": FACT}))
    pack = pack_of(api, brief["brief_id"])
    (finding,) = [f for f in {p["key"]: p for p in pack["pieces"]}["reel_2"]["findings"] if f["source"] == "fidelity"]
    assert finding["status"] == "attested" and finding["resolution"]["note"] == FACT
    assert not [b for b in pack["ready_blockers"] if "attest" in b.lower() or "Reel 2" in b], pack["ready_blockers"]

    # 4. An edit locks its line; Finish again keeps it word for word.
    edited = ok(api("PATCH", f"/packs/{pack['pack_id']}/pieces/reel_3",
                    {"request_id": "np-edit-1", "expected_manifest_hash": pack["manifest_hash"], "changes": {"caption.hook": EDIT}}))
    pack = ok(api("GET", f"/packs/{edited['pack_id']}"))
    reel3 = {p["key"]: p for p in pack["pieces"]}["reel_3"]
    assert reel3["content"]["caption"]["hook"] == EDIT and any(lock["path"] == "caption.hook" for lock in reel3["locks"])
    again = ok(api("POST", f"/packs/{pack['pack_id']}/finish", {"request_id": "np-finish-1", "expected_manifest_hash": pack["manifest_hash"]}), 202)
    run(repo, run_id=again["run_id"])
    pack = pack_of(api, brief["brief_id"])
    assert pack["pack_id"] == again["pack_id"] and pack["state"] == "in_review", (pack["state"], pack["state_reason"])
    reel3 = {p["key"]: p for p in pack["pieces"]}["reel_3"]
    assert reel3["content"]["caption"]["hook"] == EDIT, "the model wrote over the person's line; it was put back"
    assert any(c["kind"] == "restored_lock" for c in reel3["changes"])

    # 5. Ready, with the client-permission note still listed; export; published; the learning diff.
    for blocker_round in range(3):
        if not pack["ready_blockers"]:
            break
        for p in pack["pieces"]:
            for f in p["findings"]:
                if f["status"] == "open" and f.get("can_attest"):
                    ok(api("POST", f"/packs/{pack['pack_id']}/findings/{f['finding_id']}/attest",
                           {"request_id": f"np-attest-{blocker_round}-{f['finding_id']}", "expected_manifest_hash": pack["manifest_hash"],
                            "statement": FACT}))
                    pack = pack_of(api, brief["brief_id"])
    assert not pack["ready_blockers"], pack["ready_blockers"]
    ready = ok(api("POST", f"/packs/{pack['pack_id']}/decision", {"request_id": "np-ready-2", "expected_manifest_hash": pack["manifest_hash"],
                                                                 "decision": "ready_to_publish", "note": "Ready."}))
    assert ready["state"] == "ready_to_publish"
    pack = pack_of(api, brief["brief_id"])
    assert any(n["client_permission"] and not n.get("done") for n in pack["before_publishing"]), "still listed for whoever posts"
    exported = api("GET", f"/weeks/{pack['week_id']}/packs.md")
    assert exported.status_code == 200 and exported.headers["content-type"].startswith("text/markdown")
    for p in pack["pieces"]:
        content = p["content"]
        first = content.get("script") or content.get("body") or (content.get("screens") or [""])[0] or content["slides"][0]["text"]
        assert first.splitlines()[0] in exported.text, p["key"]
    email = {p["key"]: p for p in pack["pieces"]}["email"]
    final = email["content"]["opening"] + "\n\n" + email["content"]["body"] + "\n\nOne line Whitney added before sending."
    published = ok(api("POST", f"/packs/{pack['pack_id']}/pieces/email/published",
                       {"request_id": "np-pub-1", "published_on": "2026-03-17", "channel": "email", "final_text": final, "url": None}))
    assert published["state"] == "ready_to_publish", "a published mark is outside the manifest"
    with repo.connection() as conn:
        row = conn.execute("SELECT * FROM published_content WHERE content_id=%s", (published["content_id"],)).fetchone()
    assert row["source_ref"] == f"pack:{brief['brief_id']}:email" and row["details"].get("edit")


def test_np_exit_a_provider_refusal_for_credit_shows_its_reason_and_a_retry_finishes(packs):
    repo, fake, api = packs
    brief, decided = approved_brief(api, repo)
    fake.refuse = 402
    run(repo, run_id=decided["pack_run"]["run_id"])
    pack = pack_of(api, brief["brief_id"])
    assert pack["state"] == "waiting" and "out of credit" in (pack["state_reason"] or ""), pack["state_reason"]
    fake.refuse = None
    retried = ok(api("POST", f"/briefs/{brief['brief_id']}/pack", {"request_id": "np-retry-1"}), 202)
    run(repo, run_id=retried["run_id"])
    assert pack_of(api, brief["brief_id"])["state"] == "in_review"


def test_np_exit_a_spent_packs_budget_waits_with_its_reason_and_finishes_when_raised(packs):
    repo, fake, api = packs
    with connect(repo.settings.database_url, vectors=False) as conn:
        # Production runs uncapped (budgets.uncapped, 27 October); the capped mode this checks is switched on here.
        from backend_pipeline.settings_store import set_value
        set_value(conn, "budgets.uncapped", False, APPROVER)
        standing.set_cap(conn, "packs", APPROVER, usd=0.01)
        conn.commit()
    brief, decided = approved_brief(api, repo)
    run(repo, run_id=decided["pack_run"]["run_id"])
    pack = pack_of(api, brief["brief_id"])
    assert pack["state"] == "waiting" and pack["state_reason"].startswith("This week's content packs budget"), pack["state_reason"]
    with connect(repo.settings.database_url, vectors=False) as conn:
        assert standing.set_cap(conn, "packs", APPROVER, usd=6.0)["released_jobs"]
        conn.commit()
    run(repo, run_id=decided["pack_run"]["run_id"])
    assert pack_of(api, brief["brief_id"])["state"] == "in_review"


def test_np_exit_a_worker_killed_mid_finish_fails_visibly_and_finishes_on_a_retry(packs):
    repo, fake, api = packs
    brief, decided = approved_brief(api, repo)
    fake.kill_at = "pack_finish"
    with pytest.raises(WorkerKilled):
        run(repo, run_id=decided["pack_run"]["run_id"])
    with repo.connection() as conn:
        (lost,) = conn.execute("SELECT * FROM pipeline_jobs WHERE run_id=%s AND status='running'", (decided["pack_run"]["run_id"],)).fetchall()
        assert lost["stage"] == "pack_finish"
        conn.execute("UPDATE pipeline_jobs SET lease_expires_at=now()-interval '1 minute' WHERE job_id=%s", (lost["job_id"],))
    run(repo, run_id=decided["pack_run"]["run_id"])
    pack = pack_of(api, brief["brief_id"])
    assert pack["state"] == "waiting" and "worker stopped" in (pack["state_reason"] or "").lower(), pack["state_reason"]
    ok(api("POST", f"/jobs/{lost['job_id']}/retry", {}), 202)
    run(repo, run_id=decided["pack_run"]["run_id"])
    assert pack_of(api, brief["brief_id"])["state"] == "in_review"


def test_np_the_pack_stages_are_the_contracts():
    assert c2.STAGES == ("pack_assemble", "pack_finish", "pack_check", "pack_repair", "pack_recheck", "pack_finalize")


def piece_copies(pack):
    return {p["key"]: (p["origin"], p["content"], p["brief_copy"]) for p in pack["pieces"]}


def test_np_a_finished_pack_replays_byte_for_byte_at_usd_0_with_the_switch_off(packs):
    """NP.B9: the same approved brief, with the pack's runs and rows gone (as in a fresh database restored from the same
    data) and the live switch off, gives the same pack from the saved answers: no request leaves, every call is a replay."""
    repo, fake, api = packs
    brief, decided = approved_brief(api, repo)
    run(repo, run_id=decided["pack_run"]["run_id"])
    first = pack_of(api, brief["brief_id"])
    assert first["state"] == "in_review", first["state_reason"]
    with repo.connection() as conn:
        runs = [r["run_id"] for r in conn.execute("SELECT run_id FROM pipeline_runs WHERE run_scope='pack_generation'")]
        conn.execute("DELETE FROM pipeline_events WHERE run_id=ANY(%s)", (runs,))
        conn.execute("DELETE FROM content_assets WHERE pack_id IN (SELECT pack_id FROM content_packs WHERE source_brief_id=%s)", (brief["brief_id"],))
        conn.execute("DELETE FROM pipeline_jobs WHERE run_id=ANY(%s)", (runs,))
        conn.execute("DELETE FROM content_packs WHERE source_brief_id=%s", (brief["brief_id"],))
        conn.execute("DELETE FROM pipeline_runs WHERE run_id=ANY(%s)", (runs,))
    repo.settings.pack_live_enabled = False
    sent = len(fake.requests)
    replayed = ok(api("POST", f"/briefs/{brief['brief_id']}/pack", {"request_id": "np-replay-1"}), 202)
    assert replayed["mode"] == "replay"
    run(repo, run_id=replayed["run_id"])
    second = pack_of(api, brief["brief_id"])
    assert second["state"] == "in_review", second["state_reason"]
    assert len(fake.requests) == sent, "nothing was sent: every pack call answered from the saved responses"
    assert piece_copies(second) == piece_copies(first), "the same pieces, byte for byte"
    with repo.connection() as conn:
        calls = conn.execute("SELECT status,cost_usd FROM llm_runs WHERE stage LIKE 'pack_%%' AND details->>'run_id'=%s",
                             (replayed["run_id"],)).fetchall()
    assert calls and all(c["status"] == "replayed" and float(c["cost_usd"] or 0) == 0 for c in calls), calls


def test_np_raising_the_output_cap_mid_run_does_not_void_the_pack_run(packs):
    """NP.B9 (K74): the output cap is an operating limit outside the frozen contract, so a pack run started at one cap
    finishes after the cap is raised."""
    repo, fake, api = packs
    brief, decided = approved_brief(api, repo)
    run(repo, limit=2, run_id=decided["pack_run"]["run_id"])  # assemble and finish
    with connect(repo.settings.database_url, vectors=False) as conn:
        settings_store.set_value(conn, "models.completion_tokens", 48000, APPROVER)
        conn.commit()
    settings_store.invalidate()
    run(repo, run_id=decided["pack_run"]["run_id"])
    pack = pack_of(api, brief["brief_id"])
    assert pack["state"] == "in_review", pack["state_reason"]
