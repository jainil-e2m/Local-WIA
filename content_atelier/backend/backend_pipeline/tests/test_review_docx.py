"""5.B14 (.docx): the week's review document as a Word file, rendered from the same Markdown as `review.md` by the pack
document's converter, on the template made in the image. A synthetic week (a developed card with its contract v4 brief, a
card in the content bank) is rendered and opened again with python-docx: the 13 October header once, from the template; every
Markdown heading as a Word heading at its level and in its order; labels in bold, list items as bulleted list items, no
Markdown marker left; each pack on a new page; every asset's copy whole; the same bytes for the same export. The template's
contract is checked, and that the image makes it and the copy built in memory gives the same file. Invented text only (R48)."""
from __future__ import annotations

import io
import re
from datetime import UTC, datetime
from pathlib import Path

import docx
import pytest

from backend_pipeline.briefs import review_document as doc
from backend_pipeline.briefs import review_docx, review_template
from backend_pipeline.tests.brief_v4_fixtures import v4_body
from backend_pipeline.tests.test_review_document import PACKET, material

EXPORTED = datetime(2026, 10, 27, 9, 30, tzinfo=UTC)


def v4_week() -> tuple[str, dict]:
    body = v4_body(PACKET)
    body.update(evidence=[{"evidence_id": "e1", "speaker": "Strategist", "start_ms": 83000, "quote": "How do you answer a new inquiry?"}],
                claims=[])
    brief = {"brief_id": "b4", "approval_status": "pending", "approved_by": None, "updated_by": "system", "version_number": 1,
             "content_body": {"document": {"header": {"schema_version": "brief_document_v4"}, "body": body}}}
    return doc.render(material({"a1": brief}), exported=EXPORTED), body


def opened(data: bytes):
    return docx.Document(io.BytesIO(data))


def test_the_template_carries_the_13_october_header_and_the_styles_the_converter_writes_with():
    made = review_template.build()
    assert made == review_template.build(), "the same bytes every time"
    template = docx.Document(io.BytesIO(made))
    paragraphs = template.paragraphs
    assert [p.text for p in paragraphs] == list(doc.HEADER), "the body is the header and nothing else"
    assert paragraphs[0].style.name == "Title" and paragraphs[1].style.name == "Subtitle"
    title, subtitle, maker = (p.runs[0] for p in paragraphs)
    assert (title.bold, title.font.size.pt, title.font.name) == (True, 32, "Calibri")
    assert (subtitle.font.size.pt, maker.bold, maker.font.size.pt) == (16, True, 20)
    names = {s.name for s in template.styles}
    assert {"Title", "List Bullet", "List Paragraph", *(f"Heading {n}" for n in range(1, 7))} <= names


def test_the_image_makes_the_template_and_the_file_and_the_memory_copy_give_the_same_document(tmp_path, monkeypatch):
    dockerfile = (Path(__file__).resolve().parents[2] / "Dockerfile").read_text(encoding="utf-8")
    copied = dockerfile.index("COPY backend_pipeline ./backend_pipeline")
    made = dockerfile.index("RUN python -m backend_pipeline.briefs.review_template")
    assert copied < made < dockerfile.index("USER atelier"), "made from the package, before /app is read-only"
    text, _ = v4_week()
    monkeypatch.setattr(review_docx, "TEMPLATE", tmp_path / "templates" / "review-template.docx")
    in_memory = review_docx.render(text, title="t", created=EXPORTED)
    assert review_template.main() == 0 and review_docx.TEMPLATE.is_file()
    assert review_docx.template() == review_docx.TEMPLATE
    assert review_docx.render(text, title="t", created=EXPORTED) == in_memory


def test_the_word_file_has_the_header_once_and_every_heading_as_a_word_heading():
    text, body = v4_week()
    paragraphs = opened(review_docx.render(text, title="Content Atelier Review, week_2026-10-12", created=EXPORTED)).paragraphs
    assert [p.text for p in paragraphs[:3]] == list(doc.HEADER) and paragraphs[0].style.name == "Title"
    full = "\n".join(p.text for p in paragraphs)
    for line in doc.HEADER:
        assert full.count(line) == 1, line
    headings = [(p.style.name, p.text) for p in paragraphs if p.style.name.startswith("Heading")]
    expected = [(f"Heading {len(line) - len(line.lstrip('#'))}", line.lstrip("#").strip())
                for line in text.splitlines()[1:] if line.startswith("#")]
    assert headings == expected, "every Markdown heading after the header, at its level and in its order"
    names = [h for _, h in headings]
    order = ["Pack 1 · ATTRACT", "Content angle", "Content brief", "Email", "Reel 1", "Reel 2", "Reel 3", "Carousel",
             "Before you publish Pack 1", "Content bank"]
    found = [next(i for i, h in enumerate(names) if h.startswith(o)) for o in order]
    assert found == sorted(found), "the review layout's sections in order"
    plan = body["format_plan"]
    copy = [*plan["email"]["subject_options"], plan["email"]["preview"], plan["email"]["opening"], plan["email"]["body"],
            plan["email"]["ending"], *(s["text"] for s in plan["carousel"]["slides"]), *plan["carousel"]["caption"].values()]
    for reel in plan["reels"]:
        copy += [reel["cover_text"], reel["on_screen_hook"], *(reel["screens"] or []), reel["script"] or "", *reel["caption"].values()]
    for value in copy:
        # A slide's own **emphasis** is formatting in Word, not asterisks.
        for line in (x.replace("**", "").strip() for x in str(value).splitlines() if x.strip()):
            assert line in full, line
    assert "**" not in full and not re.search(r"^#+ ", full, re.MULTILINE), "no Markdown marker is left"


def test_labels_lists_emphasis_and_new_pages_follow_the_markdown():
    text, _ = v4_week()
    paragraphs = opened(review_docx.render(text, title="t", created=EXPORTED)).paragraphs
    label = next(p for p in paragraphs if p.text.startswith("Central point: "))
    assert label.runs[0].bold and label.runs[0].text == "Central point:", "a field's label is a bold run"
    item = next(p for p in paragraphs if p.text.startswith("Strategist at 1:23: "))
    assert item.style.name == "List Bullet", "a Markdown list item is a bulleted list item"
    maker = next(p for p in paragraphs if p.text.startswith("Written by the Content Atelier system (brief contract v4)"))
    assert all(r.italic for r in maker.runs if r.text.strip()), "the brief's maker line stays italic"
    slide = next(p for p in paragraphs if p.text.startswith("Slide 1\n"))
    assert slide.runs[0].bold and slide.runs[0].text == "Slide 1"
    pages = [p.text for p in paragraphs if p.paragraph_format.page_break_before]
    assert pages == ["Pack 1 · ATTRACT", "Content bank"], "each pack and the content bank start a new page"


def test_the_file_is_the_same_for_the_same_export_and_names_the_week():
    text, _ = v4_week()
    one = review_docx.render(text, title="Content Atelier Review, week_2026-10-12", created=EXPORTED)
    assert one == review_docx.render(text, title="Content Atelier Review, week_2026-10-12", created=EXPORTED)
    core = opened(one).core_properties
    assert core.title == "Content Atelier Review, week_2026-10-12" and core.author == "Content Atelier"
    assert core.created == core.modified == EXPORTED and core.comments == ""
    assert review_docx.MEDIA_TYPE == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_markdown_without_the_templates_header_is_refused():
    with pytest.raises(ValueError, match="header"):
        review_docx.render("# Something else\n\nText\n", title="t", created=EXPORTED)
