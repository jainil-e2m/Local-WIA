"""The week's review document as a Word file (plan 5.B14, the .docx), beside the Markdown.

The same document as `GET /weeks/{id}/review.md`, in the same order and with the same words: `review_document.render` writes
the Markdown from the stored structure (the cards' fields, the brief documents of contract v1 to v4, never parsed copy), and
the pack document's converter (`packs/document_docx.py`, NP.B12) turns it into Word paragraphs, so the two exports cannot
drift apart and there is one converter, not two. Headings become Word heading styles (Word's navigation pane and Google Docs'
outline show them), `- ` lines bulleted list items, `**bold**` and `*italic*` spans runs with their emphasis, and each pack
and the content bank start a new page; no Markdown marker is left in the text.

The document is built on the template shipped in the image, `templates/review-template.docx`, which the Dockerfile makes
when the image is built (`review_template.py`; it is never committed: no office file outside research/, R48). It carries the
13 October review document's header (`review_document.HEADER`: "Content Atelier Review", "Content Angles, Briefs and
Packs", "Wedding Industry Ads", in its type) and the styles the converter writes with, so the Markdown's own header lines are
left out rather than written twice. Where the file is absent (a checkout that has not run `review_template`), the same
template is built in memory. A template put in its place must keep the contract: its body is the header and nothing else,
and it has the Title, Heading 1 to 6, List Bullet and List Paragraph styles (`test_review_docx.py` checks the made one).

The file is deterministic for a given week and export time (`document_docx.stamp` and `save`). No model call; read only.
"""
from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from ..packs import document_docx
from . import review_document

MEDIA_TYPE = document_docx.MEDIA_TYPE
TEMPLATE = Path(__file__).resolve().parent / "templates" / "review-template.docx"


def template() -> Path | BinaryIO:
    """The template in the image, or the same template built in memory where the file is absent."""
    if TEMPLATE.is_file():
        return TEMPLATE
    from .review_template import build
    return io.BytesIO(build())


def render(markdown: str, *, title: str, created: datetime, template_file: Path | BinaryIO | None = None) -> bytes:
    """The .docx bytes of a review document's Markdown, on the template that carries its header."""
    head = "\n".join(review_document.header_lines())
    if not markdown.startswith(head):
        raise ValueError("The review document does not start with the header its Word template carries")
    return document_docx.render(markdown[len(head):], title=title, created=created, template=template_file or template())


def docx(repo, week_id: str, *, exported: datetime | None = None) -> bytes:
    """GET /weeks/{id}/review.docx: the week's review document, as `review.md` renders it, as a Word file."""
    exported = exported or datetime.now(UTC)
    text = review_document.render_week(repo, week_id, exported=exported)
    return render(text, title=f"Content Atelier Review, {week_id}", created=exported)
