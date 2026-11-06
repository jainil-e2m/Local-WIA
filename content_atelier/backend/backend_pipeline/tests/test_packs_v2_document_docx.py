"""NP.B12 (.docx): the week's pack document as a Word file, rendered from the same Markdown as `packs.md` through python-docx
with its built-in styles. A synthetic week of two packs is written with the pack document's own section writers (the week's
plan, the angle card, the brief, every piece, "Before you publish"), rendered, and opened again with python-docx: every heading
in order, every piece's text whole (a long script too), lists, emphasis and new pages where the Markdown has them, and the same
bytes for the same export. Invented text only (R48)."""
from __future__ import annotations

import copy
import io
import zipfile
from datetime import UTC, datetime

import docx

from backend_pipeline.briefs import review_document as rd
from backend_pipeline.packs import contracts_v2 as c2
from backend_pipeline.packs import document, document_docx
from backend_pipeline.tests import pack_v2_fixtures as fx
from backend_pipeline.tests import pack_v2_service_fixtures as sfx
from backend_pipeline.tests.test_strategist_profile import card

EXPORTED = datetime(2026, 10, 27, 9, 30, tzinfo=UTC)
# A whole Reel script far longer than any real one: nothing in the export may cut it.
LONG_SCRIPT = " ".join(f"Sentence {n} of the long script says the reply is part of the ad." for n in range(1, 401))

PLAN = {"publishing_week_start": "2026-10-27", "publishing_week_end": "2026-11-02",
        "slots": [{"label": "Tuesday email", "weekday": "Tuesday", "date": "2026-10-27", "piece": "email", "piece_label": "Email",
                   "title": "How we read follow-up before the ads", "cta": "reply", "note": None},
                  {"label": "Instagram 1", "weekday": "Wednesday", "date": "2026-10-28", "piece": None, "piece_label": None,
                   "title": None, "cta": None, "note": "Nothing ready for this slot"}],
        "bank": [{"piece_label": "Reel 2", "title": "How we read follow-up before the ads", "suggested_week": 1,
                  "reason": "the week already has a stance Reel"}],
        "findings": [{"severity": "warning", "message": "Two covers open the same way", "pieces": ["Reel 1", "Reel 2"]}]}


def pack_pieces(number: int) -> tuple[dict, dict]:
    row = fx.brief_row()
    bodies = sfx.from_brief(row["content_body"]["document"]["body"])
    if number == 2:
        bodies["reel_1"]["content"]["script"] = LONG_SCRIPT
        bodies["email"]["content"]["subject_options"] = ["A second pack's first subject", "A second pack's other subject"]
    return row, bodies


def week_markdown() -> tuple[str, list[dict]]:
    """The pack document's layout for two packs, written by `document`'s own section writers in `document.markdown`'s order."""
    w = rd.Writer()
    w.add("# Content Atelier Packs", "", "The week's content packs", "", "Wedding Industry Ads", "")
    w.add("**Week:** 12 October 2026 to 18 October 2026", f"**Made by:** {document.MADE_BY}.", f"**Exported:** {EXPORTED:%d %B %Y, %H:%M} UTC")
    w.gap()
    document.week_plan(w, PLAN)
    packs = []
    for number in (1, 2):
        row, bodies = pack_pieces(number)
        body = sfx.pack_body(row, client_quotes=[{"quote_id": "Q1", "piece": "reel_1", "quote": "it usually takes us two days to reply",
                                                  "speaker": "The owner", "cleared": None}])
        w.add("---", "", f"# Pack {number} · WARM: {body['title']}, part {number}", "")
        w.add(f"*{document.MADE_BY}; {document.DELEGATED}.*")
        w.gap()
        w.add("## Content angle")
        w.gap()
        the_card = card("moment_a", number)
        w.add(f"### {the_card['title']}")
        w.gap()
        rd.card_section(w, the_card, {"approval_status": "approved", "approved_by": "approver@example.invalid", "content_body": {}})
        w.add("## Content brief")
        w.gap()
        rd.brief_section(w, row["content_body"]["document"]["body"], rd.BRIEF_SECTIONS)
        for key in c2.EXPORT_ORDER:
            if key.startswith("reel_"):
                document.reel(w, key, bodies[key])
            elif key == "email":
                document.email(w, bodies[key]["content"])
            else:
                document.carousel(w, bodies[key]["content"])
        document.before_publishing(w, body, number, ["Reel 1 has an open note"])
        packs.append({"bodies": bodies, "body": body})
    return w.text(), packs


def piece_text(bodies: dict) -> list[str]:
    """Every line of every piece's final copy, as a reader of the document must find it."""
    email = bodies["email"]["content"]
    values = [*email["send_header"].values(), *email["subject_options"], email["preview"], email["opening"], email["body"], email["ending"]]
    for key in ("reel_1", "reel_2", "reel_3"):
        reel = bodies[key]["content"]
        values += [reel["title"], reel["cover_text"], *reel["cover_alternates"], reel["on_screen_hook"], *(reel.get("screens") or []),
                   reel.get("script") or "", *reel["caption"].values()]
    carousel = bodies["carousel"]["content"]
    values += [carousel["title"], *[s["text"] for s in carousel["slides"]], *carousel["caption"].values()]
    return [line.replace("**", "").strip() for value in values if value for line in str(value).splitlines() if line.strip()]


def opened(data: bytes):
    return docx.Document(io.BytesIO(data))


def test_the_word_file_has_every_heading_and_every_piece_whole():
    text, packs = week_markdown()
    data = document_docx.render(text, title="Content Atelier Packs, week_2026-10-12", created=EXPORTED)
    word = opened(data)
    paragraphs = word.paragraphs
    assert paragraphs[0].style.name == "Title" and paragraphs[0].text == "Content Atelier Packs"
    headings = [(p.style.name, p.text) for p in paragraphs[1:] if p.style.name.startswith("Heading")]
    expected = [(f"Heading {len(line) - len(line.lstrip('#'))}", line.lstrip("#").strip())
                for line in text.splitlines()[1:] if line.startswith("#")]
    assert headings == expected, "every Markdown heading, at its level and in its order"
    names = [h for _, h in headings]
    for n in (1, 2):
        pack = names[names.index(next(h for h in names if h.startswith(f"Pack {n} "))):]
        order = ["Content angle", "Content brief", "Email", "Reel 1", "Reel 2", "Reel 3", "Carousel", f"Before you publish Pack {n}"]
        found = [next(i for i, h in enumerate(pack) if h.startswith(o)) for o in order]
        assert found == sorted(found), "the pack's sections in the Markdown's order"
    assert names.index("The week's plan") < names.index(next(h for h in names if h.startswith("Pack 1 ")))
    full = "\n".join(p.text for p in paragraphs)
    for pack in packs:
        for line in piece_text(pack["bodies"]):
            assert line in full, line
        for note in pack["body"]["before_publishing"]:
            assert note["text"] in full
    assert LONG_SCRIPT in full, "a long script is whole"
    assert "it usually takes us two days to reply" in full and "Client quotes to clear before posting" in names
    assert "**" not in full, "emphasis marks become formatting"


def test_lists_emphasis_and_new_pages_follow_the_markdown():
    text, _ = week_markdown()
    paragraphs = opened(document_docx.render(text, title="t", created=EXPORTED)).paragraphs
    by_text = {p.text: p for p in paragraphs}
    alternates = by_text["The reply comes first"]
    assert alternates.style.name == "List Bullet", "a Markdown list item is a bulleted list item"
    first, second = by_text["1.\tWhen more inquiries aren't enough"], by_text["1.\tA second pack's first subject"]
    assert first.style.name == second.style.name == "List Paragraph", "numbered lists start at one in every pack"
    label = next(p for p in paragraphs if p.text.startswith("DATE: "))
    assert [r.text for r in label.runs if r.bold][:1] == ["DATE:"] and "\nSEND TIME: " in label.text, "a bold label; lines kept together"
    made = next(p for p in paragraphs if p.text.startswith(document.MADE_BY + "; "))
    assert all(r.italic for r in made.runs if r.text.strip()), "an italic line stays italic"
    slide = next(p for p in paragraphs if p.text.startswith("Slide 1\n"))
    assert slide.runs[0].bold and slide.runs[0].text == "Slide 1"
    pages = [p.text for p in paragraphs if p.paragraph_format.page_break_before]
    assert [t.split(" · ")[0] for t in pages] == ["Pack 1", "Pack 2"], "each pack starts on a new page"


def test_the_file_is_the_same_for_the_same_export_and_carries_no_template_metadata():
    text, _ = week_markdown()
    one = document_docx.render(text, title="Content Atelier Packs, week_2026-10-12", created=EXPORTED)
    two = document_docx.render(copy.copy(text), title="Content Atelier Packs, week_2026-10-12", created=EXPORTED)
    assert one == two, "deterministic: fixed core-property dates and archive dates"
    with zipfile.ZipFile(io.BytesIO(one)) as archive:
        assert archive.namelist()[0] == "[Content_Types].xml"
        assert {i.date_time for i in archive.infolist()} == {document_docx.ZIP_DATE}
    core = opened(one).core_properties
    assert core.title == "Content Atelier Packs, week_2026-10-12" and core.author == core.last_modified_by == document_docx.MAKER
    assert core.created == core.modified == EXPORTED and core.comments == ""


def test_stray_asterisks_and_characters_xml_cannot_carry_do_not_break_the_export():
    text = "# Title\n\nA note: 5 * 3 is *not* a list, and a lone ** stays.\n\nA bell \x07 here.\n\n- **Label** (Tuesday): an *idea*\n"
    paragraphs = opened(document_docx.render(text, title="t", created=EXPORTED)).paragraphs
    assert paragraphs[1].text == "A note: 5 * 3 is not a list, and a lone ** stays."
    assert [r.text for r in paragraphs[1].runs if r.italic] == ["not"]
    assert paragraphs[2].text == "A bell  here."
    assert paragraphs[3].style.name == "List Bullet" and paragraphs[3].text == "Label (Tuesday): an idea"
    assert document_docx.MEDIA_TYPE == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
