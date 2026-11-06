"""E.X9 on the migrated database: WIA rates briefs as well as cards. The Gate 2 decision takes the reviewer's ratings on review
rubric 2.3a (every criterion or none, with the version the form showed) and stores them on the decision's label, which is
WIA's (source `gate`) only when its actor or the author it names is a WIA reviewer (ATELIER_WIA_REVIEWERS); any other is
kept with the delegated label (R55). The brief carries the rubric for its decision form while it waits. Synthetic data only."""
from __future__ import annotations

from backend_pipeline.gates import rubric
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_brief_v4_db import v4  # noqa: F401 (fixture)
from backend_pipeline.tests.test_packs_v2_service_db import ready, settle  # noqa: F401 (fixture, helper)

RATINGS = {key: 4 for key in rubric.KEYS}


def labels(repo, brief_id):
    with repo.connection() as conn:
        return conn.execute("""SELECT l.source,l.proxy,l.rubric_ratings,d.details FROM calibration_labels l
            JOIN decisions d ON d.decision_id=l.decision_id WHERE l.item_kind='brief' AND l.item_id=%s""", (brief_id,)).fetchall()


def test_a_brief_s_rating_is_stored_on_its_gate_two_label_and_is_wia_s_only_for_a_wia_reviewer(ready):
    repo, row, client, headers = ready
    shown = client.get(f"/storage/briefs/{row['brief_id']}", headers=headers).json()
    assert shown["rubric"]["version"] == rubric.VERSION and [c["key"] for c in shown["rubric"]["criteria"]] == list(rubric.KEYS)
    partial = client.post(f"/storage/briefs/{row['brief_id']}/decision", headers=headers, json={
        "expected_hash": row["content_hash"], "decision": "approved", "note": "Ready.",
        "rubric_ratings": {rubric.KEYS[0]: 4}, "rubric_version": rubric.VERSION})
    assert partial.status_code == 422 and "every rubric criterion" in partial.text.lower(), partial.text
    stale = client.post(f"/storage/briefs/{row['brief_id']}/decision", headers=headers, json={
        "expected_hash": row["content_hash"], "decision": "approved", "note": "Ready.", "rubric_ratings": RATINGS,
        "rubric_version": "rubric-2.3a.v0"})
    assert stale.status_code == 422
    assert labels(repo, row["brief_id"]) == [], "a refused rating records nothing"
    repo.settings.wia_reviewers = (APPROVER,)
    decided = client.post(f"/storage/briefs/{row['brief_id']}/decision", headers=headers, json={
        "expected_hash": row["content_hash"], "decision": "approved", "note": "Ready.", "rubric_ratings": RATINGS,
        "rubric_version": rubric.VERSION})
    assert decided.status_code == 200, decided.text
    (label,) = labels(repo, row["brief_id"])
    assert label["source"] == "gate" and label["proxy"] is False, "the reviewer is on WIA's list"
    assert label["rubric_ratings"]["criteria"] == RATINGS and label["rubric_ratings"]["overall"] == 4
    assert label["details"]["rubric_version"] == rubric.VERSION and label["details"]["wia_review"] is True
    assert client.get(f"/storage/briefs/{row['brief_id']}", headers=headers).json()["rubric"] is None, "a decided brief shows no form"


def test_a_rating_on_the_shared_account_is_kept_with_the_delegated_label(ready):
    repo, row, client, headers = ready
    repo.settings.wia_reviewers = ("someone-else@example.invalid",)  # the shared account is not on the list
    decided = client.post(f"/storage/briefs/{row['brief_id']}/decision", headers=headers, json={
        "expected_hash": row["content_hash"], "decision": "approved", "note": "Ready.", "rubric_ratings": RATINGS,
        "rubric_version": rubric.VERSION})
    assert decided.status_code == 200, decided.text
    (label,) = labels(repo, row["brief_id"])
    assert label["source"] == "gate_delegated" and label["proxy"] is True and label["rubric_ratings"]["overall"] == 4
