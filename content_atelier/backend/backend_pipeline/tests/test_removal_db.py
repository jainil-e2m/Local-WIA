"""6.B12: removal on request, on the migrated database. A developed card's call is made one client's: its document and a copy
of it, their chunks, their scenes with their topic links and the founder note about the call are deleted; a finished job and the
intake's revision keep their record without it; the card, its brief and its pack stay, and carry the mark wherever a person
reads them (the card screen, Gate 2, the pack, the review document), a version made later too. The account is kept with consent
no_use, or deleted with --delete-account. The dry run changes nothing; the real run needs the client id repeated and an
administrator, and waits for a running job. Synthetic data and invented names only (R48)."""
from __future__ import annotations

import json

import pytest

from backend_pipeline import gate_one, removal, storage_cli
from backend_pipeline.briefs import gate_two, review_document
from backend_pipeline.briefs.inputs import angle_packet
from backend_pipeline.packs import views
from backend_pipeline.repository import insert
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_brief_v4_db import v4  # noqa: F401 (fixture)
from backend_pipeline.tests.test_packs_v2_service_db import made, ready  # noqa: F401 (fixture)

ADMIN = "admin@example.invalid"
CLIENT = "client_removal_test"
NAME = "Invented Lakeside Venue"


def cli(monkeypatch, capsys, repo, *args) -> dict:
    monkeypatch.setenv("ATELIER_DATABASE_URL", repo.settings.database_url)
    monkeypatch.setenv("ATELIER_ARTIFACT_ROOT", str(repo.settings.artifact_root))
    capsys.readouterr()
    storage_cli.main(["clients", "remove", "--client-id", CLIENT, *args])
    return json.loads(capsys.readouterr().out)


def count(repo, query, *args) -> int:
    with repo.connection() as conn:
        return conn.execute(f"SELECT count(*) AS n FROM ({query}) q", args).fetchone()["n"]


@pytest.fixture
def chain(ready):  # noqa: F811
    """A developed card, its approved v4 brief and its finished pack; the card's first call made the client's, with a copy of
    it, a topic link, a founder note, a finished job and an intake revision; an administrator in users."""
    repo, row, client, headers = ready
    pack_id = made(repo, row)
    with repo.connection() as conn:
        refs = conn.execute("""SELECT m.moment_id,m.evidence_refs FROM key_moments m JOIN angle_moments am USING(moment_id)
            WHERE am.angle_id=%s ORDER BY m.moment_id""", (row["angle_id"],)).fetchall()
        doc = sorted({r["transcript_id"] for m in refs for r in m["evidence_refs"]})[0]
        conn.execute("INSERT INTO clients(client_id,name,aliases,consent,status) VALUES (%s,%s,'[\"Lakeside\"]','anonymise_only','active')",
                     (CLIENT, NAME))
        conn.execute("UPDATE transcripts SET client_id=%s WHERE transcript_id=%s", (CLIENT, doc))
        source = conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (doc,)).fetchone()
        insert(conn, "transcripts", {**{k: v for k, v in source.items() if k != "ingested_at"}, "transcript_id": "transcript_copy_of_call",
                                     "client_id": None, "week_id": None, "upstream_id": "copy", "canonical_document_id": doc,
                                     "included": False, "exclusion_reason": f"Duplicate of {doc}"})
        moment = refs[0]["moment_id"]
        conn.execute("INSERT INTO topics(topic_id,name) VALUES ('topic_removal_test','Follow-up')")
        conn.execute("INSERT INTO moment_topics(moment_id,topic_id,assigned_by) VALUES (%s,'topic_removal_test','person')", (moment,))
        conn.execute("""INSERT INTO seeds(seed_id,kind,text,author,created_by,transcript_id) VALUES
            ('seed_note_removal','founder_note','The reply time stood out.','Whitney','approver@example.invalid',%s)""", (doc,))
        run_id = conn.execute("SELECT run_id FROM content_angles WHERE angle_id=%s", (row["angle_id"],)).fetchone()["run_id"]
        insert(conn, "pipeline_jobs", {"job_id": "job_removal_done", "run_id": run_id, "stage": "document_normalise", "transcript_id": doc,
                                       "status": "completed", "idempotency_key": "removal-test-done"})
        conn.execute("""INSERT INTO intake_connections(connection_id,provider,activated_at,checkpoint,config)
            VALUES ('fathom_removal_test','fathom',now(),now(),'{}')""")
        conn.execute("""INSERT INTO intake_sources(source_id,connection_id,upstream_id,kind,title,source_url,metadata)
            VALUES ('source_removal_test','fathom_removal_test','rec-1','fathom',%s,'https://fathom.example.invalid/rec-1',
                    '{"participants": ["owner@lakeside.example.invalid"]}')""", (f"{NAME} strategy call",))
        conn.execute("""INSERT INTO intake_revisions(revision_id,source_id,transcript_id,content_hash,raw_artifact)
            VALUES ('revision_removal_test','source_removal_test',%s,'hash-1','intake/fathom/rec-1.json')""", (doc,))
        conn.execute("INSERT INTO users(email,role) VALUES (%s,'admin')", (ADMIN,))
    return repo, row, pack_id, doc


def test_the_dry_run_shows_everything_and_changes_nothing_and_the_real_run_needs_its_confirmations(chain, monkeypatch, capsys):
    repo, row, pack_id, doc = chain
    before = count(repo, "SELECT 1 FROM transcripts")
    shown = cli(monkeypatch, capsys, repo, "--actor", ADMIN, "--dry-run")
    would = shown["would_remove"]
    assert shown["dry_run"] and would["client"]["name"] == NAME, "the operator sees which client it is"
    assert [d["transcript_id"] for d in would["documents"]] == [doc]
    assert [d["transcript_id"] for d in would["copies"]] == ["transcript_copy_of_call"], "a copy of the call is the same call"
    counts = shown["counts"]
    assert counts["documents"] == counts["copies"] == counts["topic_links"] == counts["founder_notes"] == 1
    assert counts["chunks"] > 0 and counts["moments"] > 0 and counts["intake_revisions"] == 1
    assert row["angle_id"] in would["marked"]["angles"] and row["brief_id"] in would["marked"]["briefs"]
    assert pack_id in would["marked"]["packs"]
    assert would["account"] == "kept with consent no_use"
    assert "intake/fathom/rec-1.json" in would["originals_kept_in_store"]
    assert count(repo, "SELECT 1 FROM transcripts") == before
    unconfirmed = cli(monkeypatch, capsys, repo, "--actor", ADMIN)
    assert unconfirmed["dry_run"] and unconfirmed["next"].endswith(f"--confirm {CLIENT}"), "without --confirm it is a dry run"
    with pytest.raises(SystemExit, match="repeat --client-id"):
        cli(monkeypatch, capsys, repo, "--actor", ADMIN, "--confirm", CLIENT + "x")
    with pytest.raises(SystemExit, match="administrator"):
        cli(monkeypatch, capsys, repo, "--actor", APPROVER, "--confirm", CLIENT)
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_jobs SET status='running' WHERE job_id='job_removal_done'")
    with pytest.raises(SystemExit, match="job_removal_done"):
        cli(monkeypatch, capsys, repo, "--actor", ADMIN, "--confirm", CLIENT)
    assert count(repo, "SELECT 1 FROM transcripts") == before and count(repo, "SELECT 1 FROM decisions WHERE action=%s", removal.ACTION) == 0
    with pytest.raises(SystemExit, match="not found"):
        storage_cli.main(["clients", "remove", "--client-id", "client_missing", "--actor", ADMIN, "--dry-run"])


def test_the_removal_deletes_the_clients_material_and_marks_everything_built_on_it(chain, monkeypatch, capsys):
    repo, row, pack_id, doc = chain
    with repo.connection() as conn:
        moments = [r["moment_id"] for r in conn.execute(
            "SELECT moment_id FROM key_moments WHERE evidence_refs @> %s::jsonb", (json.dumps([{"transcript_id": doc}]),))]
        others = conn.execute("SELECT count(*) AS n FROM transcripts WHERE transcript_id <> ALL(%s)", ([doc, "transcript_copy_of_call"],)).fetchone()["n"]
    assert moments and others > 0
    done = cli(monkeypatch, capsys, repo, "--actor", ADMIN, "--confirm", CLIENT)["removed"]
    assert done["counts"]["documents"] == 1 and done["account"] == "kept with consent no_use"
    docs = [doc, "transcript_copy_of_call"]
    assert count(repo, "SELECT 1 FROM transcripts WHERE transcript_id = ANY(%s)", docs) == 0
    assert count(repo, "SELECT 1 FROM transcripts") == others, "every other document stays"
    assert count(repo, "SELECT 1 FROM transcript_chunks WHERE transcript_id = ANY(%s)", docs) == 0
    assert count(repo, "SELECT 1 FROM key_moments WHERE moment_id = ANY(%s)", moments) == 0
    assert count(repo, "SELECT 1 FROM moment_topics WHERE topic_id='topic_removal_test'") == 0
    assert count(repo, "SELECT 1 FROM angle_moments WHERE moment_id = ANY(%s)", moments) == 0
    assert count(repo, "SELECT 1 FROM seeds WHERE seed_id='seed_note_removal'") == 0
    with repo.connection() as conn:
        job = conn.execute("SELECT transcript_id,status FROM pipeline_jobs WHERE job_id='job_removal_done'").fetchone()
        revision = conn.execute("SELECT transcript_id,deleted FROM intake_revisions WHERE revision_id='revision_removal_test'").fetchone()
        source = conn.execute("SELECT title,source_url,metadata,status FROM intake_sources WHERE source_id='source_removal_test'").fetchone()
        client = conn.execute("SELECT consent FROM clients WHERE client_id=%s", (CLIENT,)).fetchone()
        kept = {t: conn.execute(f"SELECT count(*) AS n FROM {t} WHERE {k}=%s", (i,)).fetchone()["n"]
                for t, k, i in (("content_angles", "angle_id", row["angle_id"]), ("content_briefs", "brief_id", row["brief_id"]),
                                ("content_packs", "pack_id", pack_id))}
        decision = conn.execute("SELECT * FROM decisions WHERE action=%s", (removal.ACTION,)).fetchone()
    assert job == {"transcript_id": None, "status": "completed"}, "the job keeps its record without the document"
    assert revision == {"transcript_id": None, "deleted": True}, "the collector skips a revision it has seen"
    assert source == {"title": removal.REMOVED_TITLE, "source_url": None, "metadata": {}, "status": "deleted"}
    assert client == {"consent": "no_use"}
    assert kept == {"content_angles": 1, "content_briefs": 1, "content_packs": 1}, "marked, never deleted"
    assert (decision["item_kind"], decision["item_id"], decision["actor"]) == ("client", CLIENT, ADMIN)
    details = decision["details"]
    assert details["documents"] == [doc] and details["copies"] == ["transcript_copy_of_call"] and sorted(details["moments"]) == sorted(
        set(details["moments"])) and set(moments) <= set(details["moments"])
    assert details["counts"] == done["counts"] and row["angle_id"] in details["cited"]
    record = json.dumps(details, default=str) + decision["note"]
    assert NAME not in record and "Lakeside" not in record and "reply time" not in record, "ids and counts only, never a name or text"

    # Where a person sees the mark.
    review = repo.review(row["week_id"], APPROVER)
    card = next(a for a in review["angles"] if a["angle_id"] == row["angle_id"])
    assert card["removed_material"]["decision_id"] == decision["decision_id"]
    assert card["public_use"]["allowed"] is False and card["public_use"]["reasons"][0].startswith(removal.NOTE)
    assert card["public_use"]["kinds"][0] == "removed_material" and card["can_approve"] is False
    pending = [a for a in review["angles"] if a["removed_material"] and a["approval_status"] == "pending"]
    assert pending, "the synthetic week's other cards cite the same call"
    with pytest.raises(ValueError, match="removed at a client's request"):
        gate_one.decide(repo, pending[0]["angle_id"], pending[0]["content_hash"], "approved", None, False, None, APPROVER)
    brief = gate_two.get(repo, row["brief_id"], APPROVER)
    assert brief["blockers"][0].startswith(removal.NOTE) and brief["can_consume"] is False and brief["can_approve"] is False
    assert brief["blocker_items"][0]["kind"] == "removed_material" and brief["removed_material"]
    pack = views.detail(repo, pack_id, APPROVER)
    assert any(b.startswith(removal.NOTE) for b in pack["ready_blockers"]) and pack["removed_material"]
    # The marks and the blocker as the API's response models declare them (a mark that failed them would fail the read).
    from backend_pipeline.api_models import BlockerItem, RemovedMaterial
    for mark in (card["removed_material"], brief["removed_material"], pack["removed_material"]):
        assert RemovedMaterial.model_validate(mark).decision_id == decision["decision_id"]
    assert BlockerItem.model_validate(brief["blocker_items"][0]).title
    text = review_document.render_week(repo, row["week_id"])
    developed = text.split("# Pack 1 ")[1].split("# Content bank")[0]
    assert developed.count("**Built on removed material:** " + removal.NOTE) == 2, "on the card and on its brief"
    with repo.connection() as conn:
        material = review_document.week_material(conn, row["week_id"])
    in_bank = [a for a in material["cards"] if a["angle_id"] not in material["briefs"] and a["removed_material"]]
    assert text.split("# Content bank")[1].count("**Built on removed material:**") == len(in_bank), "the other cards that cited it"
    with repo.connection() as conn:
        with pytest.raises(ValueError, match="removed at a client's request"):
            angle_packet(conn, row["angle_id"])
        # A version made after the removal carries the mark through what it was built on.
        later = {k: v for k, v in conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s", (row["brief_id"],)).fetchone().items()
                 if k not in ("created_at", "updated_at")}
        insert(conn, "content_briefs", {**later, "brief_id": "brief_after_removal", "supersedes_id": row["brief_id"],
                                        "approval_status": "pending", "approved_hash": None, "approved_by": None, "approved_at": None})
        assert removal.marks(conn, "brief", ["brief_after_removal"])["brief_after_removal"]["decision_id"] == decision["decision_id"]
        assert removal.marks(conn, "angle", ["angle_never_marked"]) == {}


def test_delete_account_unlinks_the_people_and_deletes_the_client(platform_setup, monkeypatch, capsys):  # noqa: F811
    repo, _, _ = platform_setup
    with repo.connection() as conn:
        doc = conn.execute("SELECT transcript_id FROM transcripts ORDER BY transcript_id LIMIT 1").fetchone()["transcript_id"]
        conn.execute("INSERT INTO clients(client_id,name) VALUES (%s,%s)", (CLIENT, NAME))
        conn.execute("UPDATE transcripts SET client_id=%s WHERE transcript_id=%s", (CLIENT, doc))
        conn.execute("""INSERT INTO people(person_id,name,role,source,client_id) VALUES ('person_owner_test','Invented Owner','client',
            'manual',%s)""", (CLIENT,))
        conn.execute("INSERT INTO users(email,role) VALUES (%s,'admin')", (ADMIN,))
    done = cli(monkeypatch, capsys, repo, "--actor", ADMIN, "--confirm", CLIENT, "--delete-account")["removed"]
    assert done["account"] == "deleted; its people unlinked" and done["counts"]["people"] == 1
    assert count(repo, "SELECT 1 FROM clients WHERE client_id=%s", CLIENT) == 0
    assert count(repo, "SELECT 1 FROM transcripts WHERE transcript_id=%s", doc) == 0
    with repo.connection() as conn:
        person = conn.execute("SELECT client_id FROM people WHERE person_id='person_owner_test'").fetchone()
        decision = conn.execute("SELECT details FROM decisions WHERE action=%s", (removal.ACTION,)).fetchone()["details"]
    assert person == {"client_id": None}
    assert decision["account"] == "deleted" and decision["people_unlinked"] == ["person_owner_test"] and decision["consent_after"] is None
