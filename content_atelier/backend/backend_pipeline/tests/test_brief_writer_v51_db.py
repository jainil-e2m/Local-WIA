"""NP.B10 on the migrated database: a card developed with writer v5.1 gets a contract v4 brief written and repaired under
v5.1's prompt and schema (three Reels), records its writer, and its hand-off maps the three Reels straight to the pack's
reel_1, reel_2 and reel_3. Synthetic fixtures and fake providers only."""
from __future__ import annotations

import pytest

from backend_pipeline.briefs import gate_two
from backend_pipeline.briefs.contracts_v4 import BriefWriteV51
from backend_pipeline.packs import assemble
from backend_pipeline.store import canonical_hash
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_brief_v4_db import develop


@pytest.fixture
def v51(platform_setup, monkeypatch):  # noqa: F811
    return develop(platform_setup, monkeypatch, "v5.1")


def test_a_v51_brief_is_written_with_three_reels_and_maps_straight_to_the_pack(v51):
    repo, provider, row, refs, _, _ = v51
    assert refs["schema_version"] == "brief_document_v4" and refs["writer"] == "v5.1"
    contract = refs["execution_contract"]
    assert contract["writer"] == "v5.1"
    assert contract["schema_hashes"]["brief_write"] == canonical_hash(BriefWriteV51.model_json_schema())
    system, _, schema = provider.packets["brief_write"][0]
    assert "write exactly three Reels, one of each kind" in system and "Write two Reels" not in system
    reels = schema["$defs"]["FormatPlanV4"]["properties"]["reels"]
    assert schema["title"] == "BriefWriteV51" and reels["minItems"] == reels["maxItems"] == 3
    body = row["content_body"]
    assert body["provenance"]["writer"] == "v5.1"
    assert [r["kind"] for r in body["document"]["body"]["format_plan"]["reels"]] == ["story", "stance", "broll_text"]
    assert not any("Writer v5.1 writes three Reels" in f["message"] for f in body["review"]["findings"])
    plan = assemble.draft(gate_two.handoff_v2(repo, row["brief_id"], APPROVER), finish_mode="finish")
    assert {k: plan["brief_map"].get(k) for k in ("reel_1", "reel_2", "reel_3")} == {"reel_1": "reel_1", "reel_2": "reel_2", "reel_3": "reel_3"}
    assert plan["missing"] == [] and all(plan["pieces"][k]["origin"] == "brief" for k in ("reel_1", "reel_2", "reel_3"))
