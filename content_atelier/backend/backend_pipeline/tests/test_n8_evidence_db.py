"""Phase N8 on PostgreSQL: identities (1.B12's extension), internal meetings as team-practice evidence (1.B13's extension,
D24), account memory (3.B17, D25) and founder notes (L.B13, D29), through the product path where one exists. Synthetic
documents, people and accounts only; fake providers; no network."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime

import pytest
from psycopg.types.json import Jsonb

from backend_pipeline import accounts, identities, reference, settings_store
from backend_pipeline.angle_profiles import PEOPLE_LABEL, STRATEGIST_V8_PROFILE, TEAM_PRACTICE_HANDLING
from backend_pipeline.briefs import review_document
from backend_pipeline.briefs.workflow import identity_refs
from backend_pipeline.cycle import seeds as founder_seeds
from backend_pipeline.documents import intake, team_practice
from backend_pipeline.moments.recheck import recheck_in
from backend_pipeline.normalise.classify import REASONS
from backend_pipeline.repository import account_memory
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.tests.ledger_fixtures import make_document, make_moment
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_cards_sql import W1, CardSQLProvider
from backend_pipeline.tests.test_documents_db import FILLER, KB, run_jobs, vtt
from backend_pipeline.tests.test_sql_storage import drain
from backend_pipeline.tests.test_strategist_v7 import v7_card, v7_output
from backend_pipeline.tests.test_strategy_brief import constructed

LINK = {"what": "the anonymised $18K-to-$52K case study", "markers": ["$18K", "$52K", "18K", "52K"], "reason": "her name is banned"}
IDENTITIES = {
    "reviewed": {"note": "Synthetic identities for the N8 tests."},
    "clients": [
        {"name": "Fernbrook Estate", "aliases": ["Fernbrook"], "business": "wedding venue, synthetic county", "status": "active"},
        {"name": "Larkspur Hall", "aliases": ["Larkspur"], "business": "wedding venue", "status": "active", "do_not_name": True,
         "do_not_link": [LINK]},
        {"name": "Quillon Studio", "business": "photographer", "status": "prospect"},
    ],
    "people": [
        {"name": "Dana Reyes", "role": "client", "client": "Fernbrook Estate", "aliases": ["fernbrookdana", "Dani"], "pronouns": "she/her",
         "evidence": ["synthetic: the handle, the nickname and the spelling she uses are one person"]},
        {"name": "Mara Quill", "role": "client", "client": "Larkspur Hall", "aliases": ["Mara"], "pronouns": "she/her", "do_not_name": True,
         "do_not_link": [LINK]},
        {"name": "Noa Vale", "role": "prospect", "client": "Quillon Studio", "aliases": ["noavale"], "pronouns": "she/her"},
    ],
    "staff": [{"name": "Fallon Looney", "left_on": "2026-08-14", "pronouns": "she/her"}],
}


@pytest.fixture
def n8(platform_setup, tmp_path):  # noqa: F811
    repo, models, tmp = platform_setup
    with repo.connection() as conn:
        reference.sync_roster(conn, KB, date(2026, 10, 18))
    path = tmp / "identities.json"
    path.write_text(json.dumps(IDENTITIES), encoding="utf-8")
    return repo, models, tmp, path


def load(repo, path):
    with repo.connection() as conn:
        return identities.import_file(conn, path, actor=APPROVER)


# 1.B12's extension: identities -------------------------------------------------------------------------------------------

def test_a_handle_a_nickname_and_her_own_spelling_resolve_to_one_person_and_one_account(n8):
    repo, models, tmp, path = n8
    drop = tmp / "drop"
    drop.mkdir()
    (drop / "Carmen Cruickshank's Personal Meeting Room's transcript (4).vtt").write_text(vtt(
        ("Carmen Cruickshank", f"Morning Dani, good to see you. {FILLER}"), ("fernbrookdana", f"Thanks Carmen. {FILLER}"),
        ("Carmen Cruickshank", f"Let us look at the tour bookings. {FILLER}")), encoding="utf-8")
    (drop / "Whitney Hodges's Personal Meeting Room's transcript (9).vtt").write_text(vtt(
        ("Whitney Hodges", f"Hi Dana, welcome back. {FILLER}"), ("Dana Reyes", f"Happy to be here. {FILLER}"),
        ("Whitney Hodges", f"Fallon used to run this account. {FILLER}")), encoding="utf-8")
    intake.import_directory(repo, drop)
    run_jobs(repo, models)
    with repo.connection() as conn:
        before = {r["title"]: r for r in conn.execute("SELECT * FROM transcripts WHERE week_id IS NULL")}
    assert all(r["client_id"] is None for r in before.values()), "no account is known before the identities"
    counts = load(repo, path)
    assert counts["clients_created"] == 3 and counts["people_created"] == 3 and counts["staff_updated"] == 1
    assert identities.apply(repo, dry_run=True)["documents"] == 2
    applied = identities.apply(repo)
    assert applied["applied"] and applied["documents"] == 2 and identities.apply(repo, dry_run=True)["documents"] == 0, "idempotent"
    with repo.connection() as conn:
        docs = list(conn.execute("SELECT * FROM transcripts WHERE week_id IS NULL ORDER BY title"))
        dana = conn.execute("SELECT * FROM people WHERE name='Dana Reyes'").fetchone()
        fern = conn.execute("SELECT * FROM clients WHERE name='Fernbrook Estate'").fetchone()
        found = identities.notes(conn, document_ids=[d["transcript_id"] for d in docs])
        fallon = conn.execute("SELECT left_on,pronouns FROM people WHERE name='Fallon Looney'").fetchone()
    by_label = {label: a for d in docs for label, a in d["speaker_map"].items()}
    assert by_label["fernbrookdana"]["person_id"] == by_label["Dana Reyes"]["person_id"] == dana["person_id"]
    assert by_label["fernbrookdana"]["role"] == "client" and all(d["client_id"] == fern["client_id"] for d in docs)
    assert dana["reviewed"]["by"] == APPROVER and dana["reviewed"]["basis"]
    assert fallon["left_on"] == date(2026, 8, 14) and fallon["pronouns"] == "she/her"
    note = next(i for i in found if i["name"] == "Dana Reyes")
    assert note["pronouns"] == "she/her" and {"fernbrookdana", "Dana Reyes", "Dani"} <= set(note["heard_as"])
    assert next(i for i in found if i["name"] == "Fernbrook Estate")["naming"] == "anonymise"
    assert next(i for i in found if i["name"] == "Fallon Looney")["role"] == "former staff"
    assert "Noa Vale" not in [i["name"] for i in found], "an identity the calls never involve is not sent"
    assert "Mara Quill" in [i["name"] for i in found], "one never to be named always is, so the checks catch her anywhere"


def test_a_spelling_shared_by_two_people_is_refused(n8):
    repo, _, tmp, _ = n8
    bad = {**IDENTITIES, "people": [*IDENTITIES["people"], {"name": "Dani Moss", "role": "prospect", "aliases": ["Dani"]}]}
    path = tmp / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="dani"):
        load(repo, path)


def test_the_pronoun_reaches_the_brief_writer(n8):
    repo, _, _, path = n8
    load(repo, path)
    with repo.connection() as conn:
        doc = make_document(conn, "doc_noa", "Quillon Studio discovery", [("Whitney Hodges", "Tell me about your studio."),
                            ("noavale", "I'm a mom of two and I shoot weddings on weekends.")], call_type="prospect")
        conn.execute("UPDATE transcripts SET speaker_map=%s WHERE transcript_id='doc_noa'", (Jsonb({
            "noavale": {"person_id": identities.person_id_for("Noa Vale", "Quillon Studio"), "role": "prospect", "basis": "name",
                        "inferred": True}}),))
        make_moment(conn, "moment_noa", doc, 1, "I'm a mom of two and I shoot weddings on weekends.")
        refs = identity_refs(conn, {"moment_hashes": {"moment_noa": "h"}, "body": {"card": {"title": "How we plan a studio's season"}}})
    view = identities.writer_view(refs["identities"])
    noa = next(i for i in view if i["name"] == "Noa Vale")
    assert noa["pronouns"] == "she/her" and noa["heard_as"] == ["noavale"] and "anonymise" in noa["naming"]


# 1.B13's extension: internal meetings as team practice -------------------------------------------------------------------

def test_internal_meetings_are_admitted_as_team_practice_and_other_exclusions_stay(n8):
    repo, _, _, _ = n8
    with repo.connection() as conn:
        team = make_document(conn, "doc_team", "WIA Weekly Meeting", [("Whitney Hodges", "Two of us read every new page on a phone."),
                             ("Carmen Cruickshank", "Agreed, before it goes live.")], call_type="internal", included=False)
        conn.execute("UPDATE transcripts SET exclusion_reason=%s WHERE transcript_id='doc_team'", (REASONS["internal"],))
        make_document(conn, "doc_esthetics", "Carmen and a facial studio", [("Carmen Cruickshank", "Your facial ads."),
                      ("Jill", "Thanks.")], call_type="other", included=False)
        make_moment(conn, "moment_team", team, 0, "Two of us read every new page on a phone.", moment_type="team_practice",
                    speaker=("Whitney Hodges", "staff", None), current=False)
    listed = team_practice.admit(repo, actor=APPROVER)
    assert [d["transcript_id"] for d in listed["admit"]] == ["doc_team"]
    assert [d["transcript_id"] for d in listed["left_excluded"]] == ["doc_esthetics"]
    with pytest.raises(ValueError, match="included_call_types"):
        team_practice.admit(repo, actor=APPROVER, apply=True)
    with repo.connection() as conn:
        settings_store.set_value(conn, "documents.included_call_types",
                                 ["client_1to1", "office_hours", "workshop", "prospect", "slack_thread", "internal"], actor=APPROVER)
    applied = team_practice.admit(repo, actor=APPROVER, apply=True)
    assert applied["applied"] and applied["chunks_added"] > 0
    with repo.connection() as conn:
        row = conn.execute("SELECT * FROM transcripts WHERE transcript_id='doc_team'").fetchone()
        moment = conn.execute("SELECT is_current,evidence_class FROM key_moments WHERE moment_id='moment_team'").fetchone()
        still = conn.execute("SELECT included FROM transcripts WHERE transcript_id='doc_esthetics'").fetchone()
    assert row["included"] and row["exclusion_reason"] is None and row["classification"]["team_practice"]["admitted_by"] == APPROVER
    assert moment == {"is_current": True, "evidence_class": "team_practice"} and still["included"] is False


# 3.B17: account memory ---------------------------------------------------------------------------------------------------

def memory_fixture(repo, path):
    load(repo, path)
    with repo.connection() as conn:
        fern = conn.execute("SELECT client_id FROM clients WHERE name='Fernbrook Estate'").fetchone()["client_id"]
        june = make_document(conn, "doc_june", "Fernbrook strategy call", [
            ("Whitney Hodges", "I'd send a short personal video before every far-off tour."),
            ("Dana Reyes", "Couples who book tours a month out go quiet.")], client_id=fern, occurred_at=datetime(2026, 6, 10, 15, tzinfo=UTC))
        sept = make_document(conn, "doc_sept", "Fernbrook monthly call", [
            ("Whitney Hodges", "The tour videos went out on every lead this month."),
            ("Dana Reyes", "Fewer couples cancelled their tours.")], client_id=fern, occurred_at=datetime(2026, 9, 15, 15, tzinfo=UTC))
        team = make_document(conn, "doc_build", "WIA Weekly Meeting", [
            ("Tina Henares", "For Fernbrook I put the owner's video in the first text after a lead comes in."),
            ("Whitney Hodges", "Good, that was the June recommendation.")], call_type="internal", occurred_at=datetime(2026, 9, 9, 16, tzinfo=UTC))
        make_moment(conn, "moment_rec", june, 0, "I'd send a short personal video before every far-off tour.", moment_type="decision",
                    record="Whitney Hodges recommended: a personal video before far-off tours", client_id=fern,
                    setup="Whitney recommended a personal video before far-off tours.", occurred_at=datetime(2026, 6, 10, tzinfo=UTC))
        make_moment(conn, "moment_result", sept, 1, "Fewer couples cancelled their tours.", moment_type="result", client_id=fern,
                    setup="The owner reported fewer cancelled tours.", occurred_at=datetime(2026, 9, 15, tzinfo=UTC))
        make_moment(conn, "moment_built", team, 0, "For Fernbrook I put the owner's video in the first text after a lead comes in.",
                    moment_type="team_practice", record="Tina Henares built: the owner's video in the first text to a new lead",
                    setup="Tina added the owner's video to the first text for Fernbrook.", speaker=("Tina Henares", "staff", None))
        recheck_in(conn, document_ids=["doc_build"])
        conn.execute("""INSERT INTO published_content(content_id,published_on,channel,title,text,status,source_kind,source_ref,created_by)
            VALUES ('pub_1','2026-10-01','Email','A venue story','How Fernbrook keeps far-off tours warm.','confirmed','approver_entry','t','tester')""")
    return fern


def test_a_story_card_shows_its_accounts_current_state_and_what_happened_next(n8):
    repo, _, _, path = n8
    fern = memory_fixture(repo, path)
    with repo.connection() as conn:
        cards = account_memory(conn, ["moment_rec"])
        timeline = accounts.timeline(conn, fern)
    assert [e["kind"] for e in timeline] == ["recommended", "internal", "measured", "published"]
    assert timeline[1]["source"]["built"] is True, "the internal meeting shows WIA's own work"
    (acc,) = cards
    assert acc["name"] == "Fernbrook Estate" and acc["naming"] == "anonymise" and acc["calls"] == 2
    assert acc["card_call_date"] == "2026-06-10" and acc["last_call"]["title"] == "Fernbrook monthly call"
    assert [e["kind"] for e in acc["what_happened_next"]] == ["measured", "published"]
    assert [e["kind"] for e in acc["internal_since"]] == ["internal"], "an internal remark is for the reviewer, apart"
    with repo.connection() as conn:
        assert account_memory(conn, []) == []
        # A call dated only to its week folder is shown as that folder's first day, said to be a week (1.B11).
        aug = make_document(conn, "doc_aug", "Fernbrook check-in", [("Whitney Hodges", "We built the tour video text last week."),
                            ("Dana Reyes", "Couples love it.")], client_id=fern, source_type="zoom")
        conn.execute("""UPDATE transcripts SET date_evidence=%s WHERE transcript_id='doc_aug'""", (Jsonb({"detail": "", "conflicts": [],
                     "window": {"start": "2026-08-31T00:00:00+05:30", "end": "2026-09-07T00:00:00+05:30", "basis": "week folder 14"}}),))
        make_moment(conn, "moment_aug", aug, 1, "Couples love it.", moment_type="testimonial", client_id=fern)
        entry = next(e for e in accounts.timeline(conn, fern) if e["source"].get("moment_id") == "moment_aug")
    assert (entry["date"], entry["precision"]) == ("2026-08-31", "week")


class CountingConnection:
    """The connection, counting the statements that read each kind of record (the week's review showed one card per account)."""
    def __init__(self, conn):
        self.conn, self.statements = conn, []

    def execute(self, query, *args, **kwargs):
        self.statements.append(" ".join(query.split()))
        return self.conn.execute(query, *args, **kwargs)


def test_several_cards_in_one_read_build_each_timeline_once_and_read_each_transcript_once(n8):
    repo, _, _, path = n8
    fern = memory_fixture(repo, path)
    with repo.connection() as conn:
        alone = accounts.timeline(conn, fern)
        counting = CountingConnection(conn)
        shared = {}
        first = account_memory(counting, ["moment_rec"], shared)
        second = account_memory(counting, ["moment_rec"], shared)
    assert first == second and accounts.timeline(None, fern, shared) == alone, "sharing the read changes nothing shown"
    assert sum("FROM key_moments m JOIN transcripts" in s and "team_practice" in s for s in counting.statements) == 1
    assert sum("t.original_text" in s for s in counting.statements) == 0, "a scene's row never carries its whole transcript"
    assert sum(s.startswith("SELECT transcript_id,original_text") for s in counting.statements) == 1
    assert sum("FROM people" in s for s in counting.statements) == 1


def test_what_happened_next_reaches_the_writer_as_evidence_with_its_sources(n8):
    repo, _, _, path = n8
    memory_fixture(repo, path)
    with repo.connection() as conn:
        refs = identity_refs(conn, {"moment_hashes": {"moment_rec": "h"}, "body": {"card": {}}})
        from backend_pipeline.briefs.workflow import later_records
        items = later_records(conn, refs["account_memory"])
    memory = {m["moment_id"]: m for m in refs["account_memory"]}
    assert set(memory) == {"moment_built", "moment_result"} and memory["moment_built"]["evidence_class"] == "team_practice"
    assert memory["moment_result"]["date"] == "2026-09-15"
    assert {i.transcript_id for i in items} == {"doc_build", "doc_sept"} and all(i.role == "context" for i in items)
    assert any("owner's video in the first text" in i.excerpt for i in items), "what we built, from the database, with its source"


# L.B13: founder notes ----------------------------------------------------------------------------------------------------

def test_a_founder_note_names_its_call_reaches_only_v8_and_shows_paired_or_unanswered(n8):
    repo, _, _, _ = n8
    with repo.connection() as conn:
        call = conn.execute("SELECT transcript_id,title FROM transcripts WHERE week_id=%s LIMIT 1", (W1,)).fetchone()
    with pytest.raises(ValueError, match="names the call"):
        founder_seeds.add(repo, EDITOR, kind="founder_note", text="What stood out was the follow-up.")
    with pytest.raises(ValueError, match="Only a founder note"):
        founder_seeds.add(repo, EDITOR, kind="thought", text="x", transcript_id=call["transcript_id"])
    note = founder_seeds.add(repo, EDITOR, kind="founder_note", text="What stood out was how calm she was about the follow-up.",
                             author="Whitney Hodges", transcript_id=call["transcript_id"])
    with repo.connection() as conn:
        assert founder_seeds.freeze(conn, W1) == [], "a strategist that does not read notes leaves them open"
        (frozen,) = founder_seeds.freeze(conn, W1, founder_notes=True)
    with repo.connection() as conn:
        row = conn.execute("SELECT title,occurred_at,source_metadata FROM transcripts WHERE transcript_id=%s", (call["transcript_id"],)).fetchone()
    label = (row["source_metadata"].get("packet_metadata") or {}).get("filename_label") or row["title"]
    assert frozen["call"].startswith(f"\"{label}") and frozen["call"] == founder_seeds.call_label(row), "named as its scenes' recording"
    assert frozen["transcript_id"] == call["transcript_id"]
    assert founder_seeds.prompt_seeds([frozen])[0]["call"] == frozen["call"]
    paired = founder_seeds.resolve_pairings({"seed_pairings": [{"seed_ref": "F1", "moment_ids": ["moment_x"], "note": "n"}]}, [frozen])
    assert paired["seed_pairings"][0]["seed_kind"] == "founder_note" and paired["seed_pairings"][0]["call"] == frozen["call"]
    week = {"week_start": date(2026, 6, 1), "week_end": date(2026, 6, 7)}
    card = {"angle_id": "angle_1", "content_body": {"card": {"title": "How we keep tours warm", "rank": 1}}}
    material = {"week": week, "cards": [card], "briefs": {}, "run_refs": {},
                "founder_notes": [{"text": note["text"], "author": "Whitney Hodges", "call": frozen["call"], "paired": True,
                                   "unanswered": False, "cards": ["How we keep tours warm"]},
                                  {"text": "The quiet client said something big.", "author": "Whitney Hodges", "call": "\"Call B\"",
                                   "paired": False, "unanswered": True, "cards": []}]}
    text = review_document.render(material)
    assert "## What stood out (founder notes)" in text and "in 'How we keep tours warm'" in text
    assert "unanswered: no scene from that call carries it" in text


class V8Provider(CardSQLProvider):
    """One v8 card that names a never-to-be-named client, and one founder note paired with no scene."""

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage != "angle_generation":
            return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        self.calls.append(stage)
        self.card_users.append(user)
        named = v7_card("S1", 1, title="What Mara taught us about follow-up")
        return v7_output([named], seed_pairings=[{"seed_ref": "F1", "moment_ids": [], "note": "No scene of that call carries it."}]), {"fake": True}


def test_a_v8_cycle_freezes_the_identities_reads_notes_and_blocks_a_never_named_client(n8):
    repo, models, tmp, path = n8
    load(repo, path)
    with repo.connection() as conn:
        call = conn.execute("SELECT transcript_id FROM transcripts WHERE week_id=%s LIMIT 1", (W1,)).fetchone()["transcript_id"]
    founder_seeds.add(repo, EDITOR, kind="founder_note", text="What stood out was the follow-up.", author="Whitney Hodges",
                      transcript_id=call)
    v8 = models.model_copy(update={"angle_prompt_profile": STRATEGIST_V8_PROFILE, "knowledge_base_root": constructed(tmp)})
    provider = V8Provider()
    run = repo.submit(W1, "synthetic", models=v8)
    drain(SQLWorker(repo.settings, v8, provider=provider))
    user = provider.card_users[-1]
    assert PEOPLE_LABEL in user and "(founder note, from Whitney Hodges, about the call" in user
    assert TEAM_PRACTICE_HANDLING not in user, "the week's call is a client call"
    review = repo.review(W1, APPROVER)
    refs = next(r for r in review["runs"] if r["run_id"] == run["run_id"])["input_refs"]
    assert "identities" in refs and any(s["kind"] == "founder_note" for s in refs["seeds"])
    card = next(a for a in review["angles"] if (a["content_body"] or {}).get("card"))
    flags = {f["kind"]: f for f in card["content_body"]["ledger"]["flags"]}
    assert flags["do_not_name"]["severity"] == "block" and "Mara" in flags["do_not_name"]["message"]
    pairing = review["selection"]["seed_pairings"][0]
    assert pairing["seed_kind"] == "founder_note" and pairing["moment_ids"] == [] and pairing["call"]
    assert card["account_memory"] == [], "a card on a call with no known account has no account panel"
