"""NP.B11, NP.B12 and NP.B13 on the migrated database: the week's pack plan (one Tuesday email, three Instagram pieces with one
offer ask, distinct first-touch lines, the bank; a published piece leaves the plan), the week's pack document with every
piece unabbreviated, and a person's pack edits in the learning loop (delegated and system-made versions left out; a
correction given twice becomes one rule candidate). Three packs of one week are written synthetically from the approved
brief's copy, for the brief and two stand-in sibling briefs; no model call (R48)."""
from __future__ import annotations

import copy
from datetime import date, timedelta

import pytest

from backend_pipeline.knowledge import mining
from backend_pipeline.packs import checks, document, model, versions, views, week
from backend_pipeline.packs.contracts_v2 import PackDecisionV2, PackEdit, PackFinishAgain, PackMarkPublished
from backend_pipeline.repository import identifier, insert
from backend_pipeline.tests import pack_v2_service_fixtures as fx
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_brief_v4_db import v4  # noqa: F401 (fixture)
from backend_pipeline.tests.test_packs_v2_service_db import made, ready  # noqa: F401 (fixture)

# The two stand-in packs' own first-touch lines, distinct from the brief's and from each other (no figures, no names).
OTHER = [
    {"cover": "Your landing page has to earn every click", "hook": "A landing page earns the click",
     "subjects": ["When your landing page loses couples", "What a page owes your ads", "Before you send ads to a page"],
     "point": "A landing page has to earn the traffic before it gets all of it."},
    {"cover": "A rising budget is not a growing business", "hook": "More budget, same inquiries",
     "subjects": ["When more budget buys nothing new", "Your budget should follow proof", "What a bigger budget amplifies"],
     "point": "A budget should follow proof, not hope."},
]


def sibling(repo, brief_id: str) -> dict:
    """A stand-in for another approved brief of the week: the approved brief's row under a new id."""
    with repo.connection() as conn:
        row = conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s", (brief_id,)).fetchone()
        new = {k: v for k, v in row.items() if k not in ("created_at", "updated_at")}
        new.update(brief_id=identifier("brief"), supersedes_id=None)
        insert(conn, "content_briefs", new)
        return conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s", (new["brief_id"],)).fetchone()


def own_lines(bodies: dict, other: dict) -> dict:
    out = copy.deepcopy(bodies)
    for n, key in enumerate(("reel_1", "reel_2", "reel_3")):
        out[key]["content"]["cover_text"] = other["cover"] + ("" if n == 0 else f", seen {('again', 'twice')[n - 1]}")
        out[key]["content"]["on_screen_hook"] = other["hook"] + ("" if n == 0 else f", {('once more', 'again')[n - 1]}")
    out["email"]["content"]["subject_options"] = list(other["subjects"])
    return out


def write_pack(repo, brief: dict, run_id: str, *, rank: int, pillar: str, title: str, point: str, bodies: dict) -> str:
    with repo.connection() as conn:
        body = fx.pack_body(brief, run_id=run_id, rank=rank, pillar=pillar, title=title, message_spine=point)
        body["provenance"]["approval_delegated"] = True
        found = checks.findings(conn, {"content_body": body}, bodies, brief)
        return model.write_version(repo, conn, parent=None, pack_id=None, run_id=run_id, brief=brief, body=body, piece_bodies=bodies,
                                   actor="content-pack step", validation=checks.result(found))["pack_id"]


@pytest.fixture
def three(ready):  # noqa: F811
    """The week's three packs: the brief's own (WARM, rank 1) and two stand-ins (ATTRACT rank 2, CONVERT rank 3, whose stance
    Reel carries the offer ask)."""
    repo, row, client, headers = ready
    first = made(repo, row, rank=1, pillar="WARM")
    with repo.connection() as conn:
        pack = model.get(conn, first)
        base = fx.from_brief(row["content_body"]["document"]["body"])
    packs = [first]
    for n, (pillar, other) in enumerate(zip(("ATTRACT", "CONVERT"), OTHER), 2):
        brief = sibling(repo, row["brief_id"])
        bodies = own_lines(base, other)
        if pillar == "CONVERT":
            bodies["reel_2"]["content"].update(cta="offer", no_offer_ending="That's where we start. -Whitney")
        packs.append(write_pack(repo, brief, pack["production_run_id"], rank=n, pillar=pillar, title=f"Idea {n}: {other['cover']}",
                                point=other["point"], bodies=bodies))
    return repo, row, client, headers, packs


def by_slot(plan):
    return {s["slot"]: s for s in plan["slots"]}


def test_three_packs_give_one_tuesday_email_three_instagram_pieces_with_one_offer_ask_and_a_bank(three):
    repo, row, client, headers, packs = three
    plan = week.plan(repo, row["week_id"], APPROVER)
    slots = by_slot(plan)
    assert [s["slot"] for s in plan["slots"]] == ["instagram_1", "tuesday_email", "instagram_2", "instagram_3"], "in the week's order"
    assert (slots["tuesday_email"]["pack_id"], slots["tuesday_email"]["piece"], slots["tuesday_email"]["weekday"]) == (packs[0], "email", "Tuesday")
    assert (slots["instagram_1"]["pack_id"], slots["instagram_1"]["piece"], slots["instagram_1"]["cta"]) == (packs[0], "reel_1", "no_offer")
    assert slots["instagram_1"]["weekday"] == "Monday" and "no offer ask" in slots["instagram_1"]["note"]
    assert (slots["instagram_2"]["pack_id"], slots["instagram_2"]["piece"], slots["instagram_2"]["cta"]) == (packs[1], "carousel", "no_offer")
    assert (slots["instagram_3"]["pack_id"], slots["instagram_3"]["piece"], slots["instagram_3"]["cta"]) == (packs[2], "reel_2", "offer")
    assert slots["instagram_3"]["weekday"] == "Friday"
    assert [s["cta"] for s in plan["slots"] if s["slot"] != "tuesday_email"].count("offer") == 1, "exactly one offer ask"
    assert plan["publishing_week_start"] < plan["publishing_week_end"] and slots["instagram_1"]["date"] == plan["publishing_week_start"]
    assert len(plan["bank"]) == 15 - 4 and not {(b["pack_id"], b["piece"]) for b in plan["bank"]} & {(s["pack_id"], s["piece"]) for s in plan["slots"]}
    emails = [b for b in plan["bank"] if b["piece"] == "email"]
    assert [(b["pack_id"], b["suggested_week"]) for b in emails] == [(packs[1], 1), (packs[2], 2)], "the other emails wait for later Tuesdays"
    assert max(b["suggested_week"] for b in plan["bank"] if b["piece"] != "email") == 3, "three Instagram pieces a week"
    assert [p["pack_id"] for p in plan["packs"]] == packs and [p["rank"] for p in plan["packs"]] == [1, 2, 3]
    assert not [f for f in plan["findings"] if "distinct across the week" in f["message"]], "hooks, covers and subjects are distinct"
    assert not [f for f in plan["findings"] if "One offer CTA a week" in f["message"]]
    api = client.get(f"/storage/weeks/{row['week_id']}/pack-plan", headers=headers)
    assert api.status_code == 200 and by_slot(api.json())["instagram_3"]["piece"] == "reel_2"
    assert not any('mark it ready' in (slot['note'] or '') for slot in plan['slots'])
    text = document.markdown(repo, row['week_id'], APPROVER)
    assert 'generated' in text and 'mark it ready' not in text and 'marked ready by' not in text


def test_a_repeated_cover_is_a_week_finding(three):
    repo, row, _, _, packs = three
    with repo.connection() as conn:
        pack = model.get(conn, packs[1])
    edited = versions.edit(repo, packs[1], "reel_1", PackEdit(request_id="request_same_cover", expected_manifest_hash=pack["manifest_hash"],
                                                             changes={"cover_text": "The question we ask before touching your ads"}), EDITOR)
    plan = week.plan(repo, row["week_id"], APPROVER)
    found = [f for f in plan["findings"] if f["message"].startswith("Reel 1's cover repeats")]
    assert found and all(f["severity"] == "warning" and f["pieces"] for f in found), "both packs are told"
    assert {p for f in found for p in f["pieces"]} >= {"Reel 1 of Idea 2: " + OTHER[0]["cover"]}
    assert edited["pack_id"] in [p["pack_id"] for p in plan["packs"]]


def test_a_published_piece_leaves_the_plan(three):
    repo, row, _, _, packs = three
    for key, n in (("email", 1), ("reel_1", 2)):
        versions.published(repo, packs[0], key, PackMarkPublished(request_id=f"request_published_{n}", published_on="2026-10-20",
                                                                 channel="email" if key == "email" else "instagram",
                                                                 final_text=f"The final {key} as posted."), EDITOR)
    plan = week.plan(repo, row["week_id"], APPROVER)
    slots = by_slot(plan)
    planned = {(s["pack_id"], s["piece"]) for s in plan["slots"]} | {(b["pack_id"], b["piece"]) for b in plan["bank"]}
    assert (packs[0], "email") not in planned and (packs[0], "reel_1") not in planned
    assert slots["tuesday_email"]["pack_id"] == packs[1], "the next pack's email goes out instead"
    assert slots["instagram_1"]["pack_id"] == packs[1] and slots["instagram_1"]["piece"] == "reel_1"
    assert len(plan["bank"]) == 13 - 4


def test_the_week_s_pack_document_renders_every_piece_in_full_with_the_plan_on_top(three, tmp_path, monkeypatch):
    repo, row, client, headers, packs = three
    text = document.markdown(repo, row["week_id"], APPROVER)
    assert text.startswith("# Content Atelier Packs") and text.index("## The week's plan") < text.index("# Pack 1")
    assert document.MADE_BY in text and document.DELEGATED in text, "labelled by its maker (R58, R55)"
    assert text.count("\n# Pack ") == 3
    first = text[text.index("# Pack 1"):text.index("# Pack 2")]
    assert first.index("## Content angle") < first.index("## Content brief") < first.index("## Email") < first.index("## Reel 1") \
        < first.index("## Reel 2") < first.index("## Reel 3") < first.index("## Carousel") < first.index("## Before you publish Pack 1")
    for pack_id in packs:
        with repo.connection() as conn:
            pack = model.get(conn, pack_id)
            bodies = checks.bodies_of(model.pieces(conn, pack_id))
        start = text.index(f": {pack['title']}\n")
        end = text.find("\n---\n", start)
        section = text[start:end if end > 0 else len(text)]
        email = bodies["email"]["content"]
        for value in (*email["send_header"].values(), *email["subject_options"], email["preview"], email["opening"].strip(),
                      email["body"].strip(), email["ending"].strip()):
            assert value in section, value
        for key in ("reel_1", "reel_2", "reel_3"):
            reel = bodies[key]["content"]
            for value in (reel["title"], reel["cover_text"], *reel["cover_alternates"], reel["on_screen_hook"], *(reel.get("screens") or []),
                          *([reel["script"].strip()] if reel.get("script") else []), *reel["caption"].values()):
                assert value.strip() in section, value
        carousel = bodies["carousel"]["content"]
        for value in (carousel["title"], *[line for s in carousel["slides"] for line in s["text"].splitlines()], *carousel["caption"].values()):
            assert value.strip() in section, value
        for note in pack["content_body"]["before_publishing"]:
            assert note["text"] in section
    assert "For whoever posts: the client's okay." in text and "### Client quotes to clear before posting" in text
    assert "That's where we start. -Whitney" in text, "the offer piece's no-offer ending"
    exported = client.get(f"/storage/weeks/{row['week_id']}/packs.md", headers=headers)
    assert exported.status_code == 200 and exported.headers["content-type"].startswith("text/markdown")
    assert exported.text.split("**Exported:**")[0] == text.split("**Exported:**")[0]
    from backend_pipeline import storage_cli
    monkeypatch.setenv("ATELIER_DATABASE_URL", repo.settings.database_url)
    monkeypatch.setenv("ATELIER_ARTIFACT_ROOT", str(repo.settings.artifact_root))
    out = tmp_path / "packs.md"
    storage_cli.main(["pack-document", "--week", row["week_id"], "--out", str(out)])
    assert out.read_text(encoding="utf-8").split("**Exported:**")[0] == text.split("**Exported:**")[0]


def test_the_week_s_pack_document_downloads_as_a_word_file_with_every_piece(three, tmp_path, monkeypatch):
    import io
    from datetime import UTC, datetime

    import docx

    from backend_pipeline.packs import document_docx
    repo, row, client, headers, packs = three
    exported = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
    data = document_docx.docx(repo, row["week_id"], APPROVER, exported=exported)
    assert data == document_docx.docx(repo, row["week_id"], APPROVER, exported=exported), "the same export, the same bytes"
    paragraphs = docx.Document(io.BytesIO(data)).paragraphs
    headings = [p.text for p in paragraphs if p.style.name.startswith("Heading")]
    text = document.markdown(repo, row["week_id"], APPROVER, exported=exported)
    assert headings == [line.lstrip("#").strip() for line in text.splitlines()[1:] if line.startswith("#")]
    assert paragraphs[0].style.name == "Title" and sum(h.startswith("Pack ") for h in headings) == 3
    full = "\n".join(p.text for p in paragraphs)
    for pack_id in packs:
        with repo.connection() as conn:
            bodies = checks.bodies_of(model.pieces(conn, pack_id))
        email = bodies["email"]["content"]
        values = [*email["subject_options"], email["preview"], email["opening"], email["body"], email["ending"]]
        for key in ("reel_1", "reel_2", "reel_3"):
            reel = bodies[key]["content"]
            values += [reel["cover_text"], reel["on_screen_hook"], *(reel.get("screens") or []), reel.get("script") or "", *reel["caption"].values()]
        values += [s["text"] for s in bodies["carousel"]["content"]["slides"]]
        for line in (x.replace("**", "").strip() for v in values if v for x in v.splitlines() if x.strip()):
            assert line in full, line
    exported_route = client.get(f"/storage/weeks/{row['week_id']}/packs.docx", headers=headers)
    assert exported_route.status_code == 200 and exported_route.headers["content-type"] == document_docx.MEDIA_TYPE
    assert exported_route.headers["content-disposition"] == f'attachment; filename="content-atelier-packs-{row["week_id"]}.docx"'
    assert [p.text for p in docx.Document(io.BytesIO(exported_route.content)).paragraphs if p.style.name.startswith("Heading")] == headings
    assert client.get("/storage/weeks/week_missing/packs.docx", headers=headers).status_code == 404
    from backend_pipeline import storage_cli
    monkeypatch.setenv("ATELIER_DATABASE_URL", repo.settings.database_url)
    monkeypatch.setenv("ATELIER_ARTIFACT_ROOT", str(repo.settings.artifact_root))
    out = tmp_path / "packs.docx"
    storage_cli.main(["pack-document", "--week", row["week_id"], "--format", "docx", "--out", str(out)])
    assert [p.text for p in docx.Document(str(out)).paragraphs if p.style.name.startswith("Heading")] == headings
    with pytest.raises(SystemExit):
        storage_cli.main(["pack-document", "--week", row["week_id"], "--format", "docx"])


def test_a_person_s_pack_edits_reach_the_learning_loop_and_delegated_and_system_versions_do_not(three):
    repo, row, _, _, packs = three
    repo.settings.wia_reviewers = (EDITOR,)  # the editor relays WIA's own edits; the approver acts under delegation
    line = "Your inquiries deserve a faster first reply"
    with repo.connection() as conn:
        first = model.get(conn, packs[0])
        before = checks.bodies_of(model.pieces(conn, packs[0]))["email"]["content"]["subject_options"][0]
    own = versions.edit(repo, packs[0], "email", PackEdit(request_id="request_learn_own", expected_manifest_hash=first["manifest_hash"],
                                                         changes={"subject_options[0]": line}), EDITOR)
    delegated = versions.edit(repo, own["pack_id"], "reel_1", PackEdit(request_id="request_learn_delegated",
                                                                      expected_manifest_hash=own["manifest_hash"],
                                                                      changes={"cover_text": "The team's own cover line"}), APPROVER)
    versions.finish_again(repo, delegated["pack_id"], PackFinishAgain(request_id="request_learn_finish",
                                                                      expected_manifest_hash=delegated["manifest_hash"]), APPROVER)
    with repo.connection() as conn:
        diffs = [d for d in mining.edit_diffs(conn, date.today() - timedelta(days=7), date.today()) if d.get("pack")]
    (edit,) = diffs
    assert edit["field"] == "pack_email" and edit["editor"] == EDITOR and edit["after"] == line and edit["kind"] == "edit"
    assert edit["before"] == before != line
    assert edit["version_id"] == f"{own['pack_id']}:email" and edit["brief_id"] == row["brief_id"] and edit["paths"] == ["subject_options[0]"]


def test_a_correction_given_twice_in_two_packs_becomes_one_rule_candidate(three):
    repo, row, _, _, packs = three
    repo.settings.wia_reviewers = (EDITOR,)
    line = "Your inquiries deserve a faster first reply"
    for n, pack_id in enumerate(packs[:2]):
        with repo.connection() as conn:
            pack = model.get(conn, pack_id)
        versions.edit(repo, pack_id, "email", PackEdit(request_id=f"request_repeat_{n}", expected_manifest_hash=pack["manifest_hash"],
                                                      changes={"subject_options[0]": line}), EDITOR)
    with repo.connection() as conn:
        result = mining.run(conn, actor="context_mining")
        rules = conn.execute("SELECT key,source_detail FROM brand_kit_items WHERE kind='rule' AND source_kind='brief_edit'").fetchall()
        assert result["candidates"]["rule"] >= 1
        (rule,) = rules
        assert len(rule["source_detail"]["edits"]) == 2 and len(rule["source_detail"]["briefs"]) == 2
        again = mining.run(conn, actor="context_mining")
        assert len(conn.execute("SELECT 1 FROM brand_kit_items WHERE kind='rule' AND source_kind='brief_edit'").fetchall()) == 1, \
            "proposed once"
        assert again["candidates"]["rule"] == 0


def test_an_explained_edit_becomes_a_rule_candidate_with_its_reason_once(three):
    """Round 2 (WIA's section 9): an edit's reason is stated guidance, so one explained edit proposes a rule for WIA to approve."""
    repo, row, _, _, packs = three
    repo.settings.wia_reviewers = (EDITOR,)
    reason = "A subject line names the reader's own question, never a slogan"
    with repo.connection() as conn:
        pack = model.get(conn, packs[0])
    versions.edit(repo, packs[0], "email", PackEdit(request_id="request_explained", expected_manifest_hash=pack["manifest_hash"],
                                                   changes={"subject_options[0]": "How fast is your first reply to a new inquiry?"},
                                                   reason=reason), EDITOR)
    with repo.connection() as conn:
        (edit,) = [d for d in mining.edit_diffs(conn, date.today() - timedelta(days=7), date.today()) if d.get("pack")]
        assert edit["reason"] == reason
        result = mining.run(conn, actor="context_mining")
        rules = conn.execute("""SELECT key,body,source_detail,author FROM brand_kit_items WHERE kind='rule'
            AND key LIKE 'rule:explained-edit.%'""").fetchall()
        assert result["candidates"]["rule"] >= 1
        (rule,) = rules
        assert rule["body"]["statement"].startswith(reason) and rule["source_detail"]["reason"] == reason
        assert rule["author"] == EDITOR and len(rule["source_detail"]["edits"]) == 1
        mining.run(conn, actor="context_mining")
        assert len(conn.execute("SELECT 1 FROM brand_kit_items WHERE key LIKE 'rule:explained-edit.%'").fetchall()) == 1, "proposed once"


def test_a_review_note_given_on_two_packs_becomes_one_repeat_rule(three):
    repo, row, _, _, packs = three
    note = "The subject line narrates what the client did; lead with the reader's problem"
    for n, pack_id in enumerate(packs[:2]):
        with repo.connection() as conn:
            pack = model.get(conn, pack_id)
        versions.decide(repo, pack_id, PackDecisionV2(request_id=f"request_ready_note_{n}", expected_manifest_hash=pack["manifest_hash"],
                                                      decision="ready_to_publish"), APPROVER)
        versions.decide(repo, pack_id, PackDecisionV2(request_id=f"request_back_note_{n}", expected_manifest_hash=pack["manifest_hash"],
                                                      decision="in_review", note=note), APPROVER)
    with repo.connection() as conn:
        result = mining.run(conn, actor="context_mining")
    (proposed,) = [p for p in result["repeat_corrections"]["proposed"] if p["kind"] == "subject_line"]
    assert len(proposed["feedback"]) == 2
    assert views.detail(repo, packs[0], APPROVER)["state"] == "in_review"
