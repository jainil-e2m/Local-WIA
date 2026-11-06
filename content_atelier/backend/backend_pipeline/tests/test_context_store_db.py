"""L.B1 on a migrated database: the store's validity queries, supersession and delete-by-source."""
from __future__ import annotations

from datetime import date, timedelta

import psycopg
import pytest

from backend_pipeline.database import connect
from backend_pipeline.knowledge import items
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401

TODAY = date.today()


@pytest.fixture
def conn(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url) as c:
        yield c


def price(conn, ref, amount, *, start=None, end=None, status="confirmed", key="price:elevate-retainer"):
    return items.add_item(conn, kind="price", key=key, body={"offer": "ELEVATE", "amount": amount}, status=status,
                          source_kind="approver_entry", source_ref=ref, author="Whitney", created_by="whitney@example.invalid",
                          visibility="internal", valid_from=start, valid_to=end,
                          reviewed_by="whitney@example.invalid" if status == "confirmed" else None)[0]


def test_items_valid_at_returns_only_items_valid_on_the_date(conn):
    past = price(conn, "p1", "$1,197/month", start=date(2026, 1, 1), end=date(2026, 3, 31), key="price:old")
    current = price(conn, "p2", "$1,497/month", start=date(2026, 4, 1), key="price:new")
    future = price(conn, "p3", "$1,697/month", start=TODAY + timedelta(days=30), key="price:future")
    price(conn, "p4", "$9/month", status="candidate", key="price:candidate")

    def ids(on):
        return {r["item_id"] for r in items.items_valid_at(conn, "price", on)}
    assert ids(date(2026, 2, 1)) == {past}
    assert ids(TODAY) == {current}
    assert ids(TODAY + timedelta(days=31)) == {current, future}
    assert ids(date(2025, 12, 31)) == set(), "nothing before any item starts"
    assert items.items_valid_at(conn, "offer", TODAY) == []


def test_a_new_version_supersedes_the_old_from_its_start_date(conn):
    old = price(conn, "a", "$1,497/month")
    new = price(conn, "b", "$1,697/month", start=TODAY + timedelta(days=14))
    old_row, new_row = items.get_item(conn, old), items.get_item(conn, new)
    assert old_row["status"] == "confirmed" and old_row["valid_to"] == TODAY + timedelta(days=13)
    assert new_row["supersedes_id"] == old
    assert [r["item_id"] for r in items.items_valid_at(conn, "price", TODAY)] == [old]
    assert [r["item_id"] for r in items.items_valid_at(conn, "price", TODAY + timedelta(days=14))] == [new]
    # A same-day change replaces the current version at once.
    newest = price(conn, "c", "$1,797/month")
    assert items.get_item(conn, new)["status"] == "retired", "the scheduled version never starts"
    assert items.get_item(conn, old)["status"] == "retired" and items.get_item(conn, old)["valid_to"] == TODAY - timedelta(days=1)
    assert [r["item_id"] for r in items.items_valid_at(conn, "price", TODAY)] == [newest]


def test_adding_is_idempotent_by_source_and_a_reviewer_is_required(conn):
    first = price(conn, "same", "$1,497/month", status="candidate")
    assert price(conn, "same", "$9/month", status="candidate") == first
    assert conn.execute("SELECT count(*) n FROM brand_kit_items").fetchone()["n"] == 1
    with pytest.raises(ValueError, match="recorded reviewer"):
        items.add_item(conn, kind="belief", key="belief:x", body={"statement": "x"}, status="confirmed",
                       source_kind="approver_entry", source_ref="r", author="Whitney", created_by="w")
    with pytest.raises(ValueError, match="Model-written text enters as a candidate"):
        items.add_item(conn, kind="belief", key="belief:x", body={"statement": "x"}, status="confirmed",
                       source_kind="export_seed", source_ref="r", author="model", created_by="w", model_written=True,
                       reviewed_by="w")
    conn.commit()
    # The database refuses a confirmed row without a reviewer too, whatever writes it.
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("UPDATE brand_kit_items SET status='confirmed' WHERE item_id=%s", (first,))
    conn.rollback()


def test_deleting_a_source_removes_its_candidates_and_records_the_deletion(conn):
    keep = items.add_item(conn, kind="rule", key="rule:rr-01", body={"statement": "No em dashes", "level": "ban", "scope": "all", "category": "voice"},
                          status="confirmed", source_kind="export_seed", source_ref="kb-candidates/rejection-rules.md#p01",
                          author="Whitney", created_by="seed", reviewed_by="owner")[0]
    gone = [items.add_item(conn, kind="belief", key=f"belief:b{i}", body={"statement": f"belief {i}"}, status="candidate",
                           source_kind="export_seed", source_ref=f"kb-candidates/belief-statements.md#row{i}",
                           author="Whitney", created_by="seed")[0] for i in range(3)]
    other = items.add_item(conn, kind="belief", key="belief:other", body={"statement": "kept"}, status="candidate",
                           source_kind="approver_entry", source_ref="kb-candidates/x", author="Whitney", created_by="w")[0]
    conn.execute("""INSERT INTO published_content(content_id,channel,title,status,source_kind,source_ref,created_by)
        VALUES ('pc1','email','A','unconfirmed','export_seed','kb-candidates/published-content-log.md#r1','seed')""")
    result = items.delete_source(conn, source_kind="export_seed", source_ref_prefix="kb-candidates/", actor="owner",
                                 reason="WIA asked for the export's drafts to be removed")
    assert result["deleted_items"] == 3 and result["deleted_published"] == 1 and result["kept_confirmed"] == 1
    left = {r["item_id"] for r in conn.execute("SELECT item_id FROM brand_kit_items")}
    assert left == {keep, other} and not left & set(gone)
    record = conn.execute("SELECT * FROM decisions WHERE decision_id=%s", (result["decision_id"],)).fetchone()
    assert record["item_kind"] == "brand_kit_source" and record["action"] == "delete_source"
    assert {d["item_id"] for d in record["details"]["deleted_items"]} == set(gone)
    assert all(set(d) == {"item_id", "kind", "key", "hash"} for d in record["details"]["deleted_items"]), "IDs and hashes, never text"
    assert record["details"]["deleted_published"] == ["pc1"]
    with pytest.raises(ValueError, match="reason"):
        items.delete_source(conn, source_kind="export_seed", source_ref="x", actor="owner", reason=" ")
