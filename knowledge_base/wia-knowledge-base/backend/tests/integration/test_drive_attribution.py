"""Legacy backfill files a walked record under the scope its membership names, not the run's scope.

Regression: the Drive reader walks every approved folder on the account, and the legacy pipeline stored
everything under the running scope, so one client's questionnaires landed on another client's record.
"""
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.db import transaction
from backend.models.db import Business, ConnectorAccount, RecordAssociation, SourceRecord, SourceScope
from backend.models.domain.intake import ChangeBatch, NormalisedRecord, UnitIn
from backend.services.intake import pipeline
from backend.workers import runner


class WalkingAdapter:
    """Like Drive: one page that holds files from several approved folders, with their memberships."""
    provider = "drive"
    parser_version = "fake-v1"
    batch: ChangeBatch | None = None

    def backfill_page(self, ctx, cursor):
        return WalkingAdapter.batch


def _file(ext):
    return NormalisedRecord("drive_file", ext, None, None, None, {"name": ext}, [UnitIn("doc_paragraph", ext, {})])


@pytest.fixture
def folders(monkeypatch):
    monkeypatch.setattr(pipeline, "get_adapter", lambda provider: WalkingAdapter())
    ids = {}
    with transaction() as s:
        acct = ConnectorAccount(id=uuid4(), provider="drive", provider_account_id="hello@", expected_identity="hello@",
                                credential_ref="GOOGLE_REFRESH_TOKEN")
        s.add(acct)
        for slug, status in (("band", "active"), ("venue", "active"), ("paused", "inactive")):
            b = Business(id=uuid4(), name=slug.title(), slug=slug, status=status)
            s.add(b)
            s.flush()
            sc = SourceScope(id=uuid4(), connector_account_id=acct.id, kind="folder", external_id=f"fold-{slug}",
                             name=slug, state="approved", default_domain="profile", association_mode="dedicated",
                             business_id=b.id)
            s.add(sc)
            ids[slug] = (b.id, sc.id)
    return ids


def _owner(ext):
    with transaction() as s:
        rec = s.execute(select(SourceRecord).where(SourceRecord.external_id == ext)).scalar_one_or_none()
        if rec is None:
            return None, set()
        biz = set(s.execute(select(RecordAssociation.business_id).where(RecordAssociation.record_id == rec.id)).scalars())
        return rec.scope_id, biz


def test_walked_files_go_to_their_own_folders_client(folders):
    band_b, band_s = folders["band"]
    venue_b, venue_s = folders["venue"]
    _, paused_s = folders["paused"]
    WalkingAdapter.batch = ChangeBatch(
        records=[_file("band-doc"), _file("venue-questionnaire"), _file("shared"), _file("paused-only")],
        next_cursor=None, terminal=True, discovered=4,
        memberships=[
            {"kind": "drive_file", "external_id": "band-doc", "scope_ids": [str(band_s)]},
            {"kind": "drive_file", "external_id": "venue-questionnaire", "scope_ids": [str(venue_s)]},
            {"kind": "drive_file", "external_id": "shared", "scope_ids": [str(venue_s), str(band_s)]},
            {"kind": "drive_file", "external_id": "paused-only", "scope_ids": [str(paused_s)]},
        ])
    with transaction() as s:
        pipeline.start_backfill(s, [band_s], None)  # the band folder's run walks the venue's files too
    while runner.run_one(["bulk"]):
        pass

    assert _owner("band-doc") == (band_s, {band_b})
    assert _owner("venue-questionnaire") == (venue_s, {venue_b})  # was filed under the band before the fix
    assert _owner("shared") == (band_s, {band_b})  # in the running scope too: the run keeps it
    assert _owner("paused-only") == (None, set())  # only an archived client's folder: not stored
