"""The M1 exit test, offline (plan section 5, "M1 exit"): one approver walks the live path through the API the app reads.

On the migrated database, in live mode with the production order of switches (live calls on, standing weekly budgets, no
run-plan variable), an approver previews and starts a cycle for a date window; edits a card and refreshes it with feedback;
confirms its public stance and develops it, and the brief starts by itself, paid from this week's briefs budget; edits an
asset line, refreshes the brief with feedback (the edited line kept, an unlocked sibling rewritten), adds an attested fact
and approves; and exports the week's review document as Markdown. The failure cases: a provider refusal for lack of credit
(HTTP 402) and a budget-cap refusal each show their reason through the API the app reads, and a worker killed mid-brief
leaves a run that fails visibly and finishes on a retry.

Nothing leaves the machine and nothing is paid: every model and embedding request goes through the live provider (its run
plan reservation, privacy routing, llm_runs record and settlement) to `FakeOpenRouter`, which answers the HTTP request here
from the synthetic fixtures the other suites use (anonymised documents, the constructed knowledge base, writer v5's body).
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import math
import re

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import settings_store
from backend_pipeline.briefs import paths
from backend_pipeline.briefs.contracts_v4 import EDITABLE_V4
from backend_pipeline.config import BACKEND_ROOT, Settings
from backend_pipeline.database import connect
from backend_pipeline.llm import failures, standing
from backend_pipeline.llm.providers import LiveProvider
from backend_pipeline.moments.scenes import SCENE_V2_PROFILE
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.tests.brief_v4_fixtures import v4_body
from backend_pipeline.tests.moments_fixtures import FILES, ScriptedProvider, import_documents, prepare_reference, standard_scripts
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_brief_v4_db import BriefV4Provider
from backend_pipeline.tests.test_strategist_v7 import v7_card, v7_output
from backend_pipeline.tests.test_strategy_brief import constructed

WINDOW = "2026-03-09T00:00:00Z"  # the fixtures' calls are dated 10 and 11 March 2026
STANCE = "Ads tools can set up campaigns; they cannot decide what a business stands for."
EDITED_POINT = "We read the follow-up before we touch the ads, because the reply decides which inquiries book."
FEEDBACK = "Say why a planner who already gets plenty of inquiries should care, in her words."
EDITED_HOOK = "Your inquiries are up, so why are tours down?"
REVISION = "Make the email's preview about the reader's inquiries."
FACT = "The owner's first reply to an inquiry took two days before the change."
HEADERS = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": APPROVER, "X-Atelier-Email": APPROVER}
# The production configuration of record (deploy/production-settings.json), as `storage_cli settings apply` stores it: since
# N2's minimal gate (D40) strategist v7 with card verification v4, brief contract v4 with writer v5 and scene profile v3. The
# scene scripts this test shares with the moments suites answer scene profile v2, so extraction stays on v2 here; v3's
# extraction is tested in test_scenes_v3.py and ran on the paid model in N2 (research/n2-delivery-2026-10/readings.md).
PRODUCTION = json.loads((BACKEND_ROOT / "deploy" / "production-settings.json").read_text(encoding="utf-8"))
CONFIGURATION = {"settings": {**PRODUCTION["settings"],
                              "prompts.profile.strategist": "2026-10-23.wia-strategist.v7",
                              "prompts.profile.card_verification": "card-verification.v4",
                              "prompts.profile.brief": "brief_document_v4", "prompts.profile.brief_writer": "v5",
                              "moments.extraction_profile": SCENE_V2_PROFILE, "prompts.profile.extraction": SCENE_V2_PROFILE}}

STAGE = contextvars.ContextVar("stage", default=None)


class WorkerKilled(BaseException):
    """The worker process dies while a request is in flight: nothing below it catches this, as nothing survives a kill."""


def vector(text: str) -> list[float]:
    """A deterministic unit vector per text, so different texts are not near-duplicates of each other."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    raw = [((digest[i % 32] + 7 * i) % 251) / 251 - 0.5 for i in range(1536)]
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


class Brain(BriefV4Provider):
    """What the provider answers, by the stage the live provider was asked for: the scene scripts of the moments suites,
    one strategist v7 card that takes a public stance, a clean model pass, a refreshed card, and writer v5's body (a refresh
    of the brief rewrites the email's preview and, ignoring the lock, the edited hook, which the lock then puts back)."""

    def __init__(self):
        super().__init__()
        self.scenes = ScriptedProvider(standard_scripts())
        self.stages: list[str] = []

    def json_call(self, *, stage, system, user, schema, fingerprint):
        self.stages.append(stage)
        if stage == "moment_extraction":
            return self.scenes.json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        if stage == "angle_generation":
            refs = re.findall(r"^## Scene (S\d+) ", user, re.MULTILINE)
            card = v7_card(refs[0], 1, title="How we read a planner's follow-up before the ads",
                           point="We read the follow-up before the ads, because the first reply decides which inquiries book.",
                           public_stance={"takes_stance": True, "stance": STANCE},
                           offer_fit={"offer": "Retainer Offer", "cta_slot": "soft_invitation",
                                      "calendar_note": "Retainer Offer is on the waitlist this window."},
                           verify_before_publishing=["Confirm the client may be referenced."])
            return v7_output([card], considered_not_selected=[]), {"fake": True}
        if stage == "card_verification" and user.startswith("Reviewer's feedback:"):
            view = json.loads(user.rsplit("Card to refresh:\n", 1)[1])
            return {"title": view["title"], "audience": view["audience"],
                    "core_perspective": "The model's own wording of the point.",
                    "why_it_matters": "A planner with a full inbox still loses the couples nobody answers the same day.",
                    "wia_in_action": view["wia_in_action"], "offer_connection": None,
                    "reason": "Says why it matters to a planner who already has inquiries."}, {"fake": True}
        if stage == "card_verification":
            ranks = sorted({int(r) for r in re.findall(r'"rank": (\d+)', user)}) or [1]
            return {"cards": [{"rank": r, "bindings": [], "flags": [], "qualifiers": [],
                               "critic": {"wia_is_the_subject": "pass", "worth_attention": "pass", "reason": "WIA's judgement is the subject."},
                               "point_tests": {"point_is_about": "wia_standard", "takeaway_instructs": False,
                                               "frustration_framing": False, "reason": "A WIA standard."}} for r in ranks]}, {"fake": True}
        if stage == "brief_write":
            packet = json.loads(user)
            self.calls.append(stage)
            self.packets.setdefault(stage, []).append((system, packet, schema))
            body = v4_body(packet)
            if packet.get("current_brief"):
                body["format_plan"]["email"]["preview"] = "It starts with how fast your inquiries hear back."
            return body, {"fake": True}
        return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)


class FakeOpenRouter:
    """The provider's HTTP API, answered on this machine. `refuse` answers every request with that status (402: out of
    credit); `kill_at` makes the worker die while that stage's request is in flight."""

    def __init__(self, brain: Brain):
        self.brain, self.requests, self.refuse, self.kill_at = brain, [], None, None

    def __call__(self, transport, request: httpx.Request) -> httpx.Response:
        stage, url = STAGE.get(), str(request.url)
        assert url.startswith("https://openrouter.ai/") or url.startswith("https://api.openai.com/"), url
        if request.method == "GET" and url.endswith("/endpoints"):
            # The public route catalog `token_budget --model <model> --store` snapshots once per model (DEPLOYMENT.md).
            model = url.split("/api/v1/models/", 1)[1].rsplit("/endpoints", 1)[0]
            return httpx.Response(200, request=request, json={"data": {"id": model, "endpoints": [
                {"provider_name": "Fake", "context_length": 400000, "max_prompt_tokens": None, "max_completion_tokens": 128000,
                 "supported_parameters": ["response_format", "structured_outputs", "max_tokens", "reasoning"]}]}})
        body = json.loads(request.content)
        self.requests.append((stage, url))
        if self.kill_at and stage == self.kill_at:
            self.kill_at = None
            raise WorkerKilled(stage)
        if self.refuse:
            return httpx.Response(self.refuse, json={"error": {"code": self.refuse, "message": "Insufficient credits. Add more using https://openrouter.ai/settings/credits"}},
                                  request=request)
        if url.endswith("/embeddings"):
            texts = body["input"] if isinstance(body["input"], list) else [body["input"]]
            return httpx.Response(200, request=request, json={"object": "list", "model": body["model"],
                                  "data": [{"object": "embedding", "index": i, "embedding": vector(t)} for i, t in enumerate(texts)],
                                  "usage": {"prompt_tokens": 12 * len(texts), "total_tokens": 12 * len(texts), "cost": 0.00001}})
        system, user = body["messages"][0]["content"], body["messages"][1]["content"]
        schema = (body.get("response_format") or {}).get("json_schema", {}).get("schema") or {}
        output, _ = self.brain.json_call(stage=stage, system=system, user=user, schema=schema, fingerprint="")
        return httpx.Response(200, request=request, json={
            "id": f"gen-m1-{len(self.requests)}", "model": body["model"], "provider": "Fake",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": json.dumps(output)}}],
            "usage": {"prompt_tokens": 3000, "completion_tokens": 900, "cost": 0.004}})


@pytest.fixture
def live(platform_setup, monkeypatch):  # noqa: F811
    """Two anonymised calls in the March window, the constructed knowledge base, the configuration of record applied as
    settings rows, and the server switched to live: model calls on, standing budgets, no run-plan variable, no injected
    provider. Every request reaches FakeOpenRouter through the live provider."""
    repo, models, tmp = platform_setup
    url = repo.settings.database_url
    kb = constructed(tmp)
    prepare_reference(repo)
    documents = import_documents(repo, models, tmp, {k: v for k, v in FILES.items() if not k.endswith("C.vtt")})
    for name in ("ATELIER_RUN_PLAN_ID", "ATELIER_RUN_PLAN_FILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ATELIER_DATABASE_URL", url)
    monkeypatch.setenv("CONTENT_ATELIER_LIVE", "true")
    monkeypatch.setenv("CONTENT_ATELIER_KNOWLEDGE_BASE_DIR", str(kb))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    with connect(url, vectors=False) as conn:
        settings_store.apply_profile(conn, CONFIGURATION, APPROVER)
        conn.commit()
    settings_store.invalidate()
    s = repo.settings
    s.synthetic = False  # a live database: develop, refresh and the cycle run live
    s.generation_enabled = s.brief_live_enabled = s.encoding_enabled = s.brief_enabled = True
    s.brief_schema, s.brief_writer = "brief_document_v4", "v5"
    s.brief_model, s.brief_review_model = "openai/gpt-6.1-sol", "anthropic/claude-sonnet-5.5"
    brain = Brain()
    fake = FakeOpenRouter(brain)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda transport, request: fake(transport, request))
    # Production's one-time step: each live model's public route, cached where a live call is sized against it.
    from backend_pipeline import token_budget
    from backend_pipeline.artifacts import store_for
    for model in token_budget.BYTE_BUDGET_MODELS:
        token_budget.cache_byte_budget_route(store_for(s), model)
    original_json, original_embed, original_many = LiveProvider.json_call, LiveProvider.embed, LiveProvider.embed_many

    def staged(method, name=None):
        def call(self, *args, **kwargs):
            token = STAGE.set(name or kwargs.get("stage"))
            try:
                return method(self, *args, **kwargs)
            finally:
                STAGE.reset(token)
        return call
    monkeypatch.setattr(LiveProvider, "json_call", staged(original_json))
    monkeypatch.setattr(LiveProvider, "embed", staged(original_embed, "embedding"))
    monkeypatch.setattr(LiveProvider, "embed_many", staged(original_many, "embedding"))
    # The calls' chunks embedded under the standing embedding budget, as `documents reembed` does for imported calls (6.B18)
    # and intake does for collected ones: the brief's research searches them.
    # The two weeks admitted the older way (the platform fixture's) are encoded as `storage_cli encode` does.
    from backend_pipeline import chunk_encoding
    from backend_pipeline.documents import reembed
    loaded = Settings.from_env(database_url=url)
    assert reembed.queue(repo, loaded, mode="live", actor=APPROVER)["chunks"]
    for week in ("week_2026-06-01", "week_2026-06-08"):
        chunk_encoding.queue(repo, loaded, week, mode="live", actor=APPROVER)
    run(repo)
    with repo.connection() as conn:
        assert not reembed.pending_chunks(conn), "every chunk of the two calls is embedded"
    app = FastAPI()
    app.include_router(router(s))
    client = TestClient(app)

    def api(method, path, body=None, email=APPROVER, **params):
        headers = {**HEADERS, "X-Atelier-Actor": email, "X-Atelier-Email": email}
        return client.request(method, "/storage" + path, json=body, headers=headers, params=params or None)
    return repo, fake, api, documents


def worker(repo):
    """A worker as production starts one: the settings from the database and the environment, no injected provider."""
    return SQLWorker(repo.settings, Settings.from_env(database_url=repo.settings.database_url))


def run(repo, limit=40, *, run_id=None):
    w = worker(repo)
    for _ in range(limit):
        if not w.once(run_id=run_id):
            break


def ok(response, status=200):
    assert response.status_code == status, f"{response.status_code}: {response.text[:1500]}"
    return response.json()


def current_cards(api, week_id):
    review = ok(api("GET", f"/weeks/{week_id}"))
    return review, [a for a in review["angles"] if a["content_body"].get("card") and not a["has_replacement"]]


def start_cycle(api, repo):
    """Preview a window and start its cycle, as the cycle panel does; run the workers until the cards are checked."""
    preview = ok(api("GET", "/cycles/preview", **{"from": WINDOW}))
    started = ok(api("POST", "/cycles", {"window_start": preview["window"]["start"], "window_end": preview["window"]["end"],
                                          "selection_hash": preview["selection_hash"], "mode": "live", "include_undated": []}), 202)
    run(repo)
    return preview, started


def develop_body(angle):
    """The develop decision the card screen sends: every verify item and blocking flag ticked, with a note."""
    body = angle["content_body"]
    blocking = [f["id"] for f in (body.get("ledger") or {}).get("flags", []) if f["severity"] == "block"]
    return {"expected_hash": angle["content_hash"], "disposition": "develop", "note": "Checked against the call.",
            "author": None, "reason_code": None, "cta": {"choice": "decide_in_development"},
            "verify_acknowledged": body["card"]["verify_before_publishing"] + blocking, "overlap_acknowledged": False}


def test_m1_exit_an_approver_runs_the_live_path_from_a_window_to_the_review_document(live):
    repo, fake, api, documents = live

    # 1. Preview and start a cycle for a date window (3.B2/3.B3): the calls, the estimate and the strategy brief first.
    preview, started = start_cycle(api, repo)
    assert preview["document_count"] == 2 and preview["estimate"]["total_usd"] > 0
    assert preview["strategy_brief"]["beliefs_to_prove"], "the window's strategy brief is shown before the start (E.B28)"
    cycle = ok(api("GET", f"/cycles/{started['run_id']}"))
    assert cycle["status"] == "waiting_for_review", (cycle["error_summary"], cycle["stages"])
    assert [s["status"] for s in cycle["stages"]] == ["completed"] * 4, "extraction, strategist, embedding and matching: no command"
    assert {d["transcript_id"] for d in cycle["documents"]} == {d["transcript_id"] for d in documents.values()}
    assert cycle["scene_coverage"]["state"] == "complete" and cycle["strategy_brief"]["brief_hash"] == cycle["strategy_brief_hash"]
    review, (card,) = current_cards(api, started["week_id"])
    assert review["strategy_brief"]["brief_hash"] == cycle["strategy_brief_hash"], "Gate 1 shows the cycle's strategy brief"
    assert card["content_body"]["card"]["point"] and card["public_use"] is None
    with repo.connection() as conn:
        spent = {r["plan_id"]: r for r in conn.execute("SELECT plan_id,calls_used,cost_used_usd FROM run_plans")}
    assert any(p.startswith("plan_standing_cycle_") and r["calls_used"] for p, r in spent.items()), spent
    assert any(p.startswith("plan_standing_extraction_") and r["calls_used"] for p, r in spent.items()), spent

    # 2. Edit a card field and refresh the card with feedback (3.B7): the edited point is kept, another field changes.
    edited = ok(api("PATCH", f"/angles/{card['angle_id']}", {"expected_hash": card["content_hash"], "changes": {"point": EDITED_POINT}}, EDITOR))
    _, (card,) = current_cards(api, started["week_id"])
    assert card["angle_id"] == edited["angle_id"] and card["content_body"]["person_edits"] == ["point"]
    asked = ok(api("POST", f"/angles/{card['angle_id']}/refresh", {"expected_hash": card["content_hash"], "feedback": FEEDBACK,
                                                                    "author": "Whitney Hodges"}), 202)
    assert asked["mode"] == "live" and asked["kept"] == ["point"]
    run(repo)
    _, (card,) = current_cards(api, started["week_id"])
    refreshed = card["content_body"]
    assert refreshed["refresh"]["maker"] == "model" and refreshed["refresh"]["kept"] == ["point"]
    assert refreshed["card"]["point"] == EDITED_POINT, "the person's point is kept word for word"
    assert refreshed["card"]["why_it_matters"].startswith("A planner with a full inbox"), "a field she did not edit changed"
    assert "core_perspective" not in refreshed["card"]
    assert card["check"]["status"] == "checked", card["check"]

    # 3. Confirm the public stance (D31) and develop: the brief starts by itself, live, within the standing budget (4.B1, 6.B3).
    refused = api("POST", f"/angles/{card['angle_id']}/decision", develop_body(card))
    assert refused.status_code == 409 and "public stance" in refused.json()["detail"]
    ok(api("POST", f"/angles/{card['angle_id']}/stance", {"expected_hash": card["content_hash"], "note": "Confirmed with Whitney."}))
    _, (card,) = current_cards(api, started["week_id"])
    assert card["stance_confirmation"]["by"] == APPROVER
    developed = ok(api("POST", f"/angles/{card['angle_id']}/decision", develop_body(card)))
    research = ok(api("GET", f"/angles/{card['angle_id']}/research"))
    assert research["mode"] == "live" and research["status"] == "queued", research
    assert developed.get("brief_run", {}).get("run_id") == research["run_id"]
    run(repo, run_id=research["run_id"])
    research = ok(api("GET", f"/angles/{card['angle_id']}/research"))
    stages = [(j["stage"], j["status"], j["error_summary"]) for j in research["jobs"]]
    assert research["status"] == "waiting_for_review" and research["brief_id"], (research["error_summary"], stages)
    with repo.connection() as conn:
        briefs_plan = conn.execute("SELECT * FROM run_plans WHERE plan_id LIKE 'plan_standing_briefs_%'").fetchone()
    assert briefs_plan and briefs_plan["calls_used"] >= 2 and float(briefs_plan["cost_used_usd"]) <= float(briefs_plan["max_cost_usd"])

    # 4. Gate 2: edit an asset line, refresh with feedback, add an attested fact, approve (5.F1, 5.B6, 5.F5, 5.B7, 5.F2).
    brief = ok(api("GET", f"/briefs/{research['brief_id']}"))
    assert brief["schema_version"] == "brief_document_v4"
    before = brief["content_body"]["document"]["body"]["format_plan"]
    edited = ok(api("PATCH", f"/briefs/{brief['brief_id']}", {"expected_hash": brief["content_hash"],
                                                              "changes": {"format_plan.reels[0].on_screen_hook": EDITED_HOOK}}))
    brief = ok(api("GET", f"/briefs/{edited['brief_id']}"))
    assert brief["locked_fields"] == ["format_plan.reels[0].on_screen_hook"]
    ok(api("POST", f"/briefs/{brief['brief_id']}/revise", {"expected_hash": brief["content_hash"], "instructions": REVISION,
                                                           "mode": "live", "evidence_ids": [], "unlock": []}), 202)
    run(repo)
    research = ok(api("GET", f"/angles/{card['angle_id']}/research"))
    brief = ok(api("GET", f"/briefs/{research['brief_id']}"))
    after = brief["content_body"]["document"]["body"]["format_plan"]
    assert after["reels"][0]["on_screen_hook"] == EDITED_HOOK, "the edited line is kept through the refresh"
    assert after["email"]["preview"] != before["email"]["preview"], "an unlocked sibling was rewritten"
    assert brief["content_body"]["review"]["locks_restored"][0]["path"] == "format_plan.reels[0].on_screen_hook"
    versions = ok(api("GET", f"/briefs/{brief['brief_id']}/versions"))
    assert len(versions) == 3
    with repo.connection() as conn:
        refreshes_plan = conn.execute("SELECT * FROM run_plans WHERE plan_id LIKE 'plan_standing_refreshes_%'").fetchone()
    assert refreshes_plan and refreshes_plan["calls_used"] >= 1, "a brief revision spends the refreshes budget"
    added = ok(api("POST", f"/briefs/{brief['brief_id']}/context", {"kind": "attested_fact", "text": FACT}), 201)
    brief = ok(api("GET", f"/briefs/{added['brief_id']}"))
    assert any(i["kind"] == "attested_fact" and i["text"] == FACT for i in brief["context_items"])
    assert any(c["status"] == "attested" and c["attested"]["by"] == APPROVER for c in brief["content_body"]["document"]["body"]["claims"]),         "the attested fact enters the ledger as attested, with the person"
    assert brief["approval_status"] == "pending"
    brief = settle_gate_two(api, brief)
    ok(api("POST", f"/briefs/{brief['brief_id']}/decision", {"expected_hash": brief["content_hash"], "decision": "approved",
                                                              "reason_code": "strong", "note": "Ready.", "author": None}))
    assert ok(api("GET", f"/briefs/{brief['brief_id']}"))["approval_status"] == "approved"

    # 5. Export the week's review document as Markdown (5.B14).
    exported = api("GET", f"/weeks/{started['week_id']}/review.md")
    assert exported.status_code == 200 and exported.headers["content-type"].startswith("text/markdown")
    text = exported.text
    assert text.startswith("# Content Atelier Review") and "(brief contract v4)" in text and "Gate 2: approved" in text
    assert f"**Central point:** {EDITED_POINT}" in text and EDITED_HOOK in text
    assert "(confirmed by " + APPROVER in text, "the confirmed public stance is in the document"
    # Nothing was sent anywhere but the fake provider, and every call was recorded and settled against a standing plan.
    with repo.connection() as conn:
        calls = conn.execute("SELECT status,plan_id FROM llm_runs WHERE routing_policy<>'replay'").fetchall()
    assert calls and all(c["status"] == "succeeded" and (c["plan_id"] or "").startswith("plan_standing_") for c in calls), calls


def settle_gate_two(api, brief):
    """Whatever stops approval, resolved the way the screen resolves each named blocker (5.F2): the CTA confirmed, the
    before-publishing items answered and the claims check recorded."""
    for _ in range(6):
        kinds = {b["kind"] for b in brief.get("blocker_items") or []}
        if not kinds - {"role"}:
            return brief
        if "cta_unconfirmed" in kinds:
            done = ok(api("POST", f"/briefs/{brief['brief_id']}/cta", {"expected_hash": brief["content_hash"], "choice": "explicit",
                                                                     "action": "Reply to this email"}))
        elif "open_question" in kinds:
            answers = {f"P{i}": "Confirmed with the client by email." for i, _ in
                       enumerate(brief["content_body"]["document"]["body"]["before_publishing"], 1)}
            done = ok(api("POST", f"/briefs/{brief['brief_id']}/answers", {"expected_hash": brief["content_hash"], "answers": answers}))
        elif "blocking_finding" in kinds:
            # The one the fixture's copy raises: the client is named without clearance, and a call collected for research
            # cannot be cleared for public use from a brief. The reviewer edits the lines that name her.
            (finding,) = [b for b in brief["blocker_items"] if b["kind"] == "blocking_finding"]
            assert "named in the public narrative without clearance" in finding["detail"], finding
            name = finding["detail"].split()[0]
            body = brief["content_body"]["document"]["body"]
            changes = {path: value.replace(name, "the owner") for path, value in paths.leaves(body)
                       if isinstance(value, str) and re.search(rf"\b{name}\b", value) and paths.section(path) in EDITABLE_V4}
            assert changes, [(p, v) for p, v in paths.leaves(body) if isinstance(v, str) and name in v]
            done = ok(api("PATCH", f"/briefs/{brief['brief_id']}", {"expected_hash": brief["content_hash"], "changes": changes}))
        elif "claims_check" in kinds:
            claims = [c["claim_id"] for c in brief["content_body"]["document"]["body"]["claims"]]
            done = ok(api("POST", f"/briefs/{brief['brief_id']}/review", {"expected_hash": brief["content_hash"], "claim_ids": claims,
                                                                         "reason": "Checked every claim against the call.",
                                                                         "history_acknowledged": True}))
        else:
            raise AssertionError(f"An unexpected blocker: {brief['blocker_items']}")
        brief = ok(api("GET", f"/briefs/{done.get('brief_id') or brief['brief_id']}"))
    raise AssertionError(f"Blockers remain: {brief['blocker_items']}")


# The failure cases ----------------------------------------------------------------------------------------------------

def developed(api, repo):
    """A cycle run and its card developed (stance confirmed), with its brief queued live: what each failure case starts from."""
    _, started = start_cycle(api, repo)
    _, (card,) = current_cards(api, started["week_id"])
    ok(api("POST", f"/angles/{card['angle_id']}/stance", {"expected_hash": card["content_hash"], "note": None}))
    _, (card,) = current_cards(api, started["week_id"])
    ok(api("POST", f"/angles/{card['angle_id']}/decision", develop_body(card)))
    research = ok(api("GET", f"/angles/{card['angle_id']}/research"))
    assert research["mode"] == "live" and research["status"] == "queued", research
    return card, research


def test_m1_exit_a_provider_refusal_for_lack_of_credit_shows_its_reason_and_a_retry_finishes(live):
    repo, fake, api, _ = live
    card, research = developed(api, repo)
    fake.refuse = 402
    run(repo, run_id=research["run_id"])
    research = ok(api("GET", f"/angles/{card['angle_id']}/research"))
    (failed,) = [j for j in research["jobs"] if j["status"] == "failed"]
    assert research["status"] == "failed" and research["error_summary"].splitlines()[0] == failures.OUT_OF_CREDIT, research["error_summary"]
    assert failed["error_summary"].startswith("The model provider refused the request because the account is out of credit")
    assert "402 Payment Required" in failed["error_summary"], "the team still sees the provider's answer"
    with repo.connection() as conn:
        refused = conn.execute("SELECT status,error FROM llm_runs WHERE status<>'succeeded'").fetchall()
    assert refused and all(r["status"] == "failed" and "402" in r["error"] for r in refused), "settled as failed, never left sent"
    # Topped up: the reviewer retries the step from the card (the brief panel's "Try this step again"), and it finishes.
    fake.refuse = None
    ok(api("POST", f"/jobs/{failed['job_id']}/retry", {}), 202)
    run(repo, run_id=research["run_id"])
    research = ok(api("GET", f"/angles/{card['angle_id']}/research"))
    assert research["status"] == "waiting_for_review" and research["brief_id"], research["error_summary"]


def test_m1_exit_a_budget_cap_refusal_shows_its_reason_and_the_brief_starts_when_the_cap_is_raised(live):
    repo, fake, api, _ = live
    with connect(repo.settings.database_url, vectors=False) as conn:
        # Production runs uncapped (budgets.uncapped, 27 October); the capped mode this checks is switched back on here.
        from backend_pipeline.settings_store import set_value
        set_value(conn, "budgets.uncapped", False, APPROVER)
        standing.set_cap(conn, "briefs", APPROVER, usd=0.01)  # this week's briefs budget cannot cover one call
        conn.commit()
    card, research = developed(api, repo)
    sent = len(fake.requests)
    run(repo, run_id=research["run_id"])
    research = ok(api("GET", f"/angles/{card['angle_id']}/research"))
    assert research["waiting_reason"].startswith("This week's briefs budget"), research
    assert "so it was not sent" in research["waiting_reason"] and research["status"] == "partially_completed"
    assert not [j for j in research["jobs"] if j["status"] == "failed"], "a spent budget waits; it does not fail the brief"
    assert len(fake.requests) == sent, "the call that would pass the cap was refused before it was sent"
    briefs = next(b for b in ok(api("GET", "/budgets"))["budgets"] if b["purpose"] == "briefs")
    assert briefs["waiting_jobs"] == 1 and briefs["cap_usd"] == 0.01
    with repo.connection() as conn:
        refused = conn.execute("SELECT details FROM llm_runs WHERE status='refused'").fetchall()
    assert refused and refused[0]["details"]["refused_by"] == "run_plan"
    # An approver raises the cap: the waiting step is queued again with no command, and the brief is written.
    with connect(repo.settings.database_url, vectors=False) as conn:
        assert standing.set_cap(conn, "briefs", APPROVER, usd=2.0)["released_jobs"]
        conn.commit()
    run(repo, run_id=research["run_id"])
    research = ok(api("GET", f"/angles/{card['angle_id']}/research"))
    assert research["status"] == "waiting_for_review" and research["brief_id"] and not research["waiting_reason"], research


def test_m1_exit_a_worker_killed_mid_brief_leaves_a_run_that_fails_visibly_and_finishes_on_a_retry(live):
    repo, fake, api, _ = live
    card, research = developed(api, repo)
    fake.kill_at = "brief_write"
    with pytest.raises(WorkerKilled):
        run(repo, run_id=research["run_id"])
    with repo.connection() as conn:
        (lost,) = conn.execute("SELECT * FROM pipeline_jobs WHERE run_id=%s AND status='running'", (research["run_id"],)).fetchall()
        assert lost["stage"] == "brief_writing"
        (orphan,) = conn.execute("SELECT llm_run_id FROM llm_runs WHERE status='sent'").fetchall()
        # The lease runs out: no heartbeat renews it.
        conn.execute("UPDATE pipeline_jobs SET lease_expires_at=now()-interval '1 minute' WHERE job_id=%s", (lost["job_id"],))
    # The next worker to look for work settles it (as the scheduler's reconcile does): the writer's call was sent and its
    # answer not saved, so the step is not paid for twice; it fails, visibly, with the reason first.
    run(repo, run_id=research["run_id"])
    research = ok(api("GET", f"/angles/{card['angle_id']}/research"))
    failed = next(j for j in research["jobs"] if j["job_id"] == lost["job_id"])
    assert research["status"] == "failed" and failed["status"] == "failed"
    assert research["error_summary"].startswith("The worker stopped while this step was running, after it sent a model call")
    assert "Retry this step" in research["error_summary"]
    with repo.connection() as conn:
        closed = conn.execute("SELECT status,error FROM llm_runs WHERE llm_run_id=%s", (orphan["llm_run_id"],)).fetchone()
    assert closed["status"] == "failed" and closed["error"].startswith("Orphaned")
    # The reviewer retries the step from the card; the brief is written and stored.
    ok(api("POST", f"/jobs/{lost['job_id']}/retry", {}), 202)
    run(repo, run_id=research["run_id"])
    research = ok(api("GET", f"/angles/{card['angle_id']}/research"))
    assert research["status"] == "waiting_for_review" and research["brief_id"], research["error_summary"]
    assert ok(api("GET", f"/briefs/{research['brief_id']}"))["schema_version"] == "brief_document_v4"
