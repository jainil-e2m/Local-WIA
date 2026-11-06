"""1.B2, 1.B12 (data side): people mirror the roster, clients come from a reviewed list, the glossary holds names.

Real PostgreSQL on the migrated platform database. No model call."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from backend_pipeline import reference
from backend_pipeline.database import connect
from backend_pipeline.knowledge import items
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401 (fixture)

KB = Path(__file__).resolve().parents[2] / "knowledge_base"


@pytest.fixture
def conn(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url, vectors=False) as connection:
        yield connection
        connection.rollback()


def roster_item(conn, name, role, state, *, aliases=(), ref=None):
    return items.add_item(conn, kind="roster_member", key=items.key_for("roster_member", name),
                          body={"name": name, "role": role, "state": state, "aliases": list(aliases)}, status="confirmed",
                          source_kind="approver_entry", source_ref=ref or f"test:{name}", author="Whitney", created_by="tester",
                          reviewed_by="whitney@example.invalid")[0]


def test_the_roster_document_seeds_people_and_the_two_agree(conn):
    counts = reference.sync_roster(conn, KB, date(2026, 10, 18))
    assert counts["created"] >= 11 and counts["removed"] == 0
    staff = {r["name"]: r for r in conn.execute("SELECT * FROM people WHERE role='staff'").fetchall()}
    assert {"Carmen Cruickshank", "Whitney Hodges", "Gisselle Jiménez", "Christina Hill", "Fallon Looney"} <= set(staff)
    assert staff["Christina Hill"]["status"] == "former" and staff["Whitney Hodges"]["status"] == "current"
    assert "Giselle" in staff["Gisselle Jiménez"]["aliases"], "name variants are the roster's"
    assert conn.execute("SELECT role FROM people WHERE name='Emily Foster'").fetchone()["role"] == "outside"
    assert conn.execute("SELECT count(*) n FROM people WHERE name ILIKE 'Viktor%%' OR name ILIKE 'Matt%%'").fetchone()["n"] == 0
    agreement = reference.roster_agreement(conn, KB, date(2026, 10, 18))
    assert agreement["agree"] and agreement["missing_from_people"] == [] and agreement["missing_from_roster"] == []
    assert reference.sync_roster(conn, KB, date(2026, 10, 18))["created"] == 0, "idempotent"


def test_agreement_names_a_missing_row_and_a_stranger(conn):
    reference.sync_roster(conn, KB, date(2026, 10, 18))
    conn.execute("DELETE FROM people WHERE name='Ivy Ayala'")
    conn.execute("INSERT INTO people(person_id,name,role,source) VALUES ('p_x','Pat Stranger','staff','manual')")
    agreement = reference.roster_agreement(conn, KB, date(2026, 10, 18))
    assert not agreement["agree"]
    assert agreement["missing_from_people"] == ["Ivy Ayala"] and agreement["missing_from_roster"] == ["Pat Stranger"]
    reference.sync_roster(conn, KB, date(2026, 10, 18))
    assert reference.roster_agreement(conn, KB, date(2026, 10, 18))["missing_from_people"] == []


def test_confirmed_roster_items_are_the_source_once_they_exist(conn):
    roster_item(conn, "Whitney Hodges", "Co-founder", "current", aliases=["Whit"])
    keys = reference.roster_entries(conn, KB, date(2026, 10, 18))
    assert [e["name"] for _, e in keys] == ["Whitney Hodges"], "the document is only the fallback before any item is confirmed"
    reference.sync_roster(conn, KB, date(2026, 10, 18))
    assert [r["name"] for r in conn.execute("SELECT name FROM people WHERE role='staff'")] == ["Whitney Hodges"]


def test_saving_a_roster_item_updates_the_people_row_in_the_same_transaction(conn):
    roster_item(conn, "Fallon Looney", "Funnel strategist", "current", ref="v1")
    row = conn.execute("SELECT * FROM people WHERE name='Fallon Looney'").fetchone()
    assert row["status"] == "current" and row["title"] == "Funnel strategist" and row["roster_key"] == "roster:fallon-looney"
    person_id = row["person_id"]
    # She leaves: the same key gets a new confirmed item; the row follows, keeping its identity.
    items.add_item(conn, kind="roster_member", key="roster:fallon-looney",
                   body={"name": "Fallon Looney", "role": "Funnel strategist", "state": "former", "left_on": "2026-08-14"},
                   status="confirmed", source_kind="approver_entry", source_ref="v2", author="Whitney", created_by="tester",
                   reviewed_by="whitney@example.invalid", valid_from=date(2026, 8, 14))
    row = conn.execute("SELECT * FROM people WHERE roster_key='roster:fallon-looney'").fetchone()
    assert row["person_id"] == person_id and row["status"] == "former" and row["role"] == "staff"


def test_a_failed_save_leaves_people_untouched(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url, vectors=False) as first:
        roster_item(first, "Ivy Ayala", "Ad creative", "current")
        first.commit()
    with pytest.raises(RuntimeError):
        with connect(platform_url, vectors=False) as second:
            items.add_item(second, kind="roster_member", key="roster:ivy-ayala",
                           body={"name": "Ivy Ayala", "role": "Ad lead", "state": "current"}, status="confirmed",
                           source_kind="approver_entry", source_ref="v2", author="Whitney", created_by="tester",
                           reviewed_by="whitney@example.invalid", valid_from=date(2026, 9, 1))
            assert second.execute("SELECT title FROM people WHERE name='Ivy Ayala'").fetchone()["title"] == "Ad lead"
            raise RuntimeError("the transaction fails after the roster item was saved")
    with connect(platform_url, vectors=False) as check:
        assert check.execute("SELECT title FROM people WHERE name='Ivy Ayala'").fetchone()["title"] == "Ad creative"


def test_an_invented_name_never_becomes_a_person(conn):
    roster_item(conn, "Matt", "Invented by ChatGPT", "invented")
    roster_item(conn, "Viktor", "AI agent", "not_a_person")
    assert conn.execute("SELECT count(*) n FROM people WHERE name='Matt'").fetchone()["n"] == 0
    assert conn.execute("SELECT role FROM people WHERE name='Viktor'").fetchone()["role"] == "ai_agent"


def test_clients_import_is_idempotent_and_consent_only_narrows_by_default(conn, tmp_path):
    listing = tmp_path / "clients.csv"
    listing.write_text("name,aliases,consent,status,notes\nFunktastic,Funk;Funktastic Weddings,,active,\n"
                       "Dogwood Reserve,,may_name,active,named in the 2026 case study\n", encoding="utf-8")
    assert reference.import_clients(conn, listing) == {"created": 2, "updated": 0, "unchanged": 0}
    rows = {r["name"]: r for r in conn.execute("SELECT * FROM clients")}
    assert rows["Funktastic"]["consent"] == "anonymise_only", "consent defaults to anonymise_only"
    assert rows["Funktastic"]["aliases"] == ["Funk", "Funktastic Weddings"] and rows["Dogwood Reserve"]["consent"] == "may_name"
    assert reference.import_clients(conn, listing) == {"created": 0, "updated": 0, "unchanged": 2}
    listing.write_text("name,aliases,consent,status\nDogwood Reserve,,anonymise_only,former\n", encoding="utf-8")
    assert reference.import_clients(conn, listing)["updated"] == 1
    after = conn.execute("SELECT consent,status FROM clients WHERE name='Dogwood Reserve'").fetchone()
    assert (after["consent"], after["status"]) == ("may_name", "former"), "an old list does not rewrite recorded consent"
    reference.import_clients(conn, listing, update_consent=True)
    assert conn.execute("SELECT consent FROM clients WHERE name='Dogwood Reserve'").fetchone()["consent"] == "anonymise_only"


def test_clients_import_refuses_bad_rows(conn, tmp_path):
    bad = tmp_path / "clients.json"
    bad.write_text(json.dumps([{"name": "X", "consent": "everyone"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="Consent"):
        reference.import_clients(conn, bad)
    bad.write_text(json.dumps({"clients": [{"name": " "}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="needs a name"):
        reference.import_clients(conn, bad)


def test_the_glossary_keeps_terms_with_their_mis_transcriptions(conn, tmp_path):
    first = reference.add_glossary_term(conn, "LeadLock", "product", ["Lead Lock", "lead luck", "LeadLock"])
    assert reference.add_glossary_term(conn, "leadlock", "product", ["Lead Lok"]) == first, "one row per term, whatever the case"
    row = conn.execute("SELECT * FROM glossary_terms WHERE term_id=%s", (first,)).fetchone()
    assert row["variants"] == ["Lead Lok"]
    with pytest.raises(ValueError):
        reference.add_glossary_term(conn, "x", "gadget")
    listing = tmp_path / "glossary.json"
    listing.write_text(json.dumps([{"term": "ELEVATE", "kind": "product", "variants": ["elevate", "Elevate program"]},
                                   {"term": "Carmen", "kind": "staff", "variants": "Carmen's;Carmin"}]), encoding="utf-8")
    assert reference.import_glossary(conn, listing) == {"terms": 2}
    assert conn.execute("SELECT variants FROM glossary_terms WHERE term='Carmen'").fetchone()["variants"] == ["Carmen's", "Carmin"]
