"""L.B5 "done when" on a migrated database: the strategist, brief writer, verifier and extraction get their context
from the assembly service and each run records its IDs and hashes; an expired price never reaches a run; an
internal-only item reaches the strategist labelled, and the verifier blocks it in public copy."""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from backend_pipeline.angle_profiles import STRATEGIST_V5_PROFILE
from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.cycle.verification import BLOCK, verify_card
from backend_pipeline.knowledge import assembly, compiler, items
from backend_pipeline.knowledge_base import load_knowledge_base
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_cards_sql import W1
from backend_pipeline.tests.test_seeds_db import SeedProvider
from backend_pipeline.tests.test_sql_storage import drain

ROOT = BACKEND_ROOT / "knowledge_base"
TODAY = date.today()


class CapturingProvider(SeedProvider):
    def __init__(self):
        super().__init__()
        self.card_systems = []

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage == "angle_generation":
            self.card_systems.append(system)
        return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)


def confirm(conn, kind, key, body, ref, **extra):
    return items.add_item(conn, kind=kind, key=key, body=body, status="confirmed", source_kind="approver_entry",
                          source_ref=ref, author="Whitney", created_by=APPROVER, reviewed_by=APPROVER, **extra)[0]


@pytest.fixture
def repo(platform_setup):  # noqa: F811
    return platform_setup[0]


def test_with_an_empty_store_every_stage_sees_exactly_the_file_knowledge_base(repo):
    for stage in assembly.STAGES:
        kb = assembly.assemble(stage, root=ROOT, connection=repo.connection)
        if stage == "pack":
            # The pack finisher's view (NP.B7) is a selection of the brief's documents, not a stage of the files themselves.
            assert kb.refs() == assembly.assemble("pack", root=ROOT).refs() and [d.entry.key for d in kb.documents] == list(assembly.PACK_DOCUMENTS)
            continue
        files = load_knowledge_base(ROOT, stage=stage)
        if assembly.tokens(files.text) <= assembly.budgets()["prefix"]:
            assert kb.refs() == files.refs() and kb.text == files.text and "context" not in kb.refs()
        else:
            # Over the prefix budget, the file-backed knowledge base is cut to it and the run records only that (E.B25 (d)).
            assert kb.refs() == assembly.assemble(stage, root=ROOT).refs() and set(kb.refs()["context"]) == {
                "source", "version", "prefix_budget"} and kb.refs()["context"]["source"] == "files"


def test_operating_items_reach_the_stage_and_the_run_records_them(repo):
    with repo.connection() as conn:
        hire = confirm(conn, "roster_member", "roster:new-hire", {"name": "Robin Vale", "role": "Ads coordinator", "state": "current"}, "r1")
        note = confirm(conn, "offer", "offer:elevate.capacity", {"name": "ELEVATE", "description": "November starts are being reserved"},
                       "o1", visibility="internal")
    strategist = assembly.assemble("strategist", root=ROOT, connection=repo.connection)
    roster = strategist.document("team_roster").text
    assert "Robin Vale" in roster
    assert "(internal: never state publicly) ELEVATE: November starts are being reserved" in strategist.document("offer_sheet").text
    refs = strategist.refs()["context"]
    assert refs["source"] == "files" and {i["id"] for i in refs["items"]["team_roster"]} == {hire}
    assert {i["id"] for i in refs["items"]["offer_sheet"]} == {note}
    assert {d["key"]: d["sha256"] for d in refs["documents"]}["team_roster"] == strategist.document("team_roster").sha256
    extraction = assembly.assemble("extraction", root=ROOT, connection=repo.connection)
    assert "Robin Vale" in extraction.document("team_roster").text and extraction.document("offer_sheet") is None
    assert any(r["name"] == "Robin Vale" for r in assembly.assemble("verifier", root=ROOT, connection=repo.connection).roster)


def test_an_expired_price_never_reaches_a_run(repo):
    with repo.connection() as conn:
        old = confirm(conn, "price", "price:audit", {"offer": "Google Ads Audit", "amount": "normally $297"}, "p1",
                      valid_to=TODAY - timedelta(days=1))
        internal = confirm(conn, "price", "price:elevate", {"offer": "ELEVATE", "amount": "$1,497/month"}, "p2",
                           visibility="internal", valid_to=TODAY - timedelta(days=1))
        live = confirm(conn, "price", "price:elevate-next", {"offer": "ELEVATE", "amount": "$1,697/month"}, "p3",
                       visibility="internal")
        confirm(conn, "offer", "offer:audit", {"name": "Google Ads Audit Giveaway", "description": "Annual audits"}, "o1")
    for stage in ("strategist", "brief", "verifier"):
        kb = assembly.assemble(stage, root=ROOT, connection=repo.connection)
        sheet = kb.document("offer_sheet").text
        assert "$297" not in sheet and "$1,497" not in sheet and "$1,697" not in sheet, "internal prices never enter a document"
        used = {i["id"] for ids in kb.refs()["context"]["items"].values() for i in ids}
        assert old not in used and internal not in used
    terms = assembly.assemble("verifier", root=ROOT, connection=repo.connection).internal_terms
    # The file knowledge base's own internal lines are blocked too (kind document_line); among store items, only the
    # valid internal price is.
    store_terms = [t["item_id"] for t in terms if t["kind"] != "document_line"]
    assert store_terms == [live], "only the valid internal price is blocked; the expired one is gone"
    # An approved version compiled while the price was valid records it as excluded once it has expired.
    with repo.connection() as conn:
        conn.execute("UPDATE brand_kit_items SET valid_to=NULL WHERE item_id=%s", (old,))
        settings = repo.settings.model_copy(update={"brief_approvers": (APPROVER,)})
        version = compiler.compile_version(conn, on=TODAY, actor=APPROVER, root=ROOT)["version"]
        compiler.approve(conn, settings, version, APPROVER, note="operating only")
        conn.execute("UPDATE brand_kit_items SET valid_to=%s WHERE item_id=%s", (TODAY - timedelta(days=1), old))
    kb = assembly.assemble("strategist", root=ROOT, connection=repo.connection)
    assert kb.refs()["context"]["source"] == "database" and kb.refs()["context"]["version"] == version
    assert old in kb.refs()["context"]["expired_excluded"] and "$297" not in kb.document("offer_sheet").text


def test_the_verifier_blocks_an_internal_figure_and_an_invented_name_in_public_copy(repo):
    with repo.connection() as conn:
        confirm(conn, "price", "price:elevate", {"offer": "ELEVATE", "amount": "$1,497/month"}, "p1", visibility="internal")
        confirm(conn, "roster_member", "roster:matt", {"name": "Matt", "role": "invented by ChatGPT", "state": "invented"}, "r1")
    kb = assembly.assemble("verifier", root=ROOT, connection=repo.connection)
    card = {"title": "What a $1,497 retainer buys", "core_perspective": "Matt explains the retainer.", "why_it_matters": "x",
            "evidence_points": [], "moment_ids": []}
    ledger = verify_card(card, {}, kb.roster, [], internal_terms=kb.internal_terms)
    kinds = {f["kind"]: f["severity"] for f in ledger["flags"]}
    assert kinds["internal_item"] == BLOCK and kinds["invented_person"] == BLOCK
    assert ledger["readiness"] == "research_required"


def test_an_internal_result_without_a_dollar_figure_is_blocked_in_public_copy(repo):
    """L.B5: a client-private result's quoted praise and figures never reach a public card or brief."""
    with repo.connection() as conn:
        result = confirm(conn, "result", "result:band-2025", {"claim": 'No attributable weddings, then "booking weddings like '
                         'clockwork"; 30 inquiries in a month', "client_type": "Band"}, "res1", visibility="internal",
                         permission="none")
    for stage in ("verifier", "brief"):
        terms = assembly.assemble(stage, root=ROOT, connection=repo.connection).internal_terms
        mine = {t["term"] for t in terms if t["item_id"] == result}
        assert {"booking weddings like clockwork", "30 inquiries"} <= mine, stage
    kb = assembly.assemble("verifier", root=ROOT, connection=repo.connection)
    card = {"title": "From no weddings to 30 inquiries", "core_perspective": "x", "why_it_matters": "x",
            "evidence_points": [], "moment_ids": []}
    flags = verify_card(card, {}, kb.roster, [], internal_terms=kb.internal_terms)["flags"]
    assert any(f["kind"] == "internal_item" and f["severity"] == BLOCK for f in flags)


def approve_version(repo):
    """Compile, approve and benchmark a version, so it is the active one (L.B4)."""
    settings = repo.settings.model_copy(update={"brief_approvers": (APPROVER,), "identity_approvers": (APPROVER,)})
    with repo.connection() as conn:
        version = compiler.compile_version(conn, on=TODAY, actor=APPROVER, root=ROOT)["version"]
        state = compiler.approve(conn, settings, version, APPROVER, note="test")["state"]
        if state == "approved_pending_benchmark":
            compiler.record_benchmark(conn, settings, version, APPROVER, passed=True, result_ref="smoke", note="")
    return version


def test_the_brief_writer_gets_exemplars_by_channel_within_k(repo, monkeypatch):
    """Exemplars reach the brief writer from the active, approved version only (R44, L.B4): one confirmed since then
    waits for the next version."""
    monkeypatch.setenv("ATELIER_CONTEXT_EXEMPLARS_K", "2")
    with repo.connection() as conn:
        for i, channel in enumerate(["email", "email", "email", "reel"]):
            confirm(conn, "exemplar", f"exemplar:e{i}", {"channel": channel, "text": f"Approved {channel} {i}", "label": "approved_final"},
                    f"x{i}", statement_date=date(2026, 6, 1) + timedelta(days=i))
    approve_version(repo)
    with repo.connection() as conn:
        confirm(conn, "exemplar", "exemplar:late", {"channel": "email", "text": "Approved email after the version", "label": "approved_final"},
                "x-late", statement_date=date(2026, 7, 1))
    worker = SimpleNamespace(repo=repo, models=SimpleNamespace(knowledge_base_root=ROOT),
                             storage=SimpleNamespace(synthetic=True, brief_channels=("email",)))
    from backend_pipeline.briefs.runtime import knowledge
    kb = knowledge(worker)
    chosen = kb.refs()["context"]["exemplars"]
    assert len(chosen) == 2 and {c["channel"] for c in chosen} == {"email"}
    assert "Approved email 2" in kb.document("exemplars").text and "Approved reel" not in kb.document("exemplars").text
    assert "after the version" not in kb.document("exemplars").text, "not in the active version"


def test_a_compiled_document_whose_items_all_expired_carries_none_of_them(repo):
    """L.B5: once every result of the approved version has passed its end date, none reaches a run. Read at the verifier,
    which always carries the results register: under version 9's priority list (v3) the strategist's prefix leaves it out
    to stay within its budget."""
    with repo.connection() as conn:
        result = confirm(conn, "result", "result:only", {"claim": "A planner's inquiries doubled in a quarter"}, "r-only",
                         permission="published")
    approve_version(repo)
    with repo.connection() as conn:
        conn.execute("UPDATE brand_kit_items SET valid_to=%s WHERE item_id=%s", (TODAY - timedelta(days=1), result))
    kb = assembly.assemble("verifier", root=ROOT, connection=repo.connection)
    assert "inquiries doubled" not in kb.document("results_register").text
    assert result in kb.refs()["context"]["expired_excluded"]


def test_a_cycle_records_its_context_and_the_strategist_sees_the_situational_block(repo):
    with repo.connection() as conn:
        hire = confirm(conn, "roster_member", "roster:new-hire", {"name": "Robin Vale", "role": "Ads coordinator", "state": "current"}, "r1")
        conn.execute("""INSERT INTO published_content(content_id,published_on,channel,title,status,source_kind,source_ref,created_by,performance)
            VALUES ('pc1',%s,'email','The reality check email','confirmed','approver_entry','pc1','w',
            '[{"id":"a","metric":"outcome","value":"Replies within a week","direction":"positive"}]'::jsonb)""", (TODAY - timedelta(days=10),))
    from backend_pipeline.config import Settings
    v5 = Settings(llm_payload_format="compact_weekly", extraction_profile="2026-10-13.weekly.v3", angle_prompt_profile=STRATEGIST_V5_PROFILE, knowledge_base_root=ROOT,
                  data_root=repo.settings.artifact_root / "legacy")
    provider = CapturingProvider()
    worker = SQLWorker(repo.settings, v5, provider=provider)
    run = repo.submit(W1, "synthetic", models=v5)
    drain(worker)
    assert "Robin Vale" in provider.card_systems[-1]
    assert "Published in the last 90 days" in provider.card_users[-1] and "The reality check email" in provider.card_users[-1]
    assert "Strongest recent pieces" in provider.card_users[-1]
    with repo.connection() as conn:
        refs = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (run["run_id"],)).fetchone()["input_refs"]
    context = refs["angle_contract"]["knowledge_base"]["context"]
    assert {i["id"] for i in context["items"]["team_roster"]} == {hire} and {"published": "pc1"} in context["situational"]
    assert context["documents"] and all(d["sha256"] for d in context["documents"])
