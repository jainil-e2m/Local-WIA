"""The week's review document's Word template (plan 5.B14, the .docx), made when the image is built.

    python -m backend_pipeline.briefs.review_template      # writes briefs/templates/review-template.docx

The Dockerfile runs it after copying the package, so the template ships in the image at `review_docx.TEMPLATE`; it is never
committed, because no office file is kept outside research/ (R48, `test_client_material_guard.py`). A checkout that has not
run it gets the same template built in memory (`review_docx.template`).

It carries the 13 October review document's header as WIA saw it, its three lines in Calibri (`review_document.HEADER`: the
title in bold at 32 points, "Content Angles, Briefs and Packs" at 16, "Wedding Industry Ads" in bold at 20), and the styles
the converter writes with (Title, Subtitle, Heading 1 to 6, List Bullet, List Paragraph), in Calibri like the rest of the
text. Its body is the header and nothing else; the renderer appends the week after it. The bytes are the same every time
(fixed core properties and archive dates).
"""
from __future__ import annotations

import sys
from datetime import UTC, datetime

from docx import Document
from docx.shared import Pt

from ..packs.document_docx import save, stamp
from .review_document import HEADER

FONT = "Calibri"
STYLES = ("Normal", "Title", "Subtitle", *(f"Heading {n}" for n in range(1, 7)), "List Bullet", "List Paragraph")
# The 13 October header's lines: (style, size in points, bold).
LINES = (("Title", 32, True), ("Subtitle", 16, False), ("Normal", 20, True))
MADE = datetime(2026, 10, 13, tzinfo=UTC)


def build() -> bytes:
    """The template's bytes."""
    document = Document()
    for name in STYLES:
        document.styles[name].font.name = FONT
    document.styles["Normal"].font.size = Pt(11)
    for text, (style, size, bold) in zip(HEADER, LINES):
        paragraph = document.add_paragraph(style=style)
        run = paragraph.add_run(text)
        run.font.name, run.font.size, run.bold = FONT, Pt(size), bold
        paragraph.paragraph_format.space_after = Pt(12)
    stamp(document, title=HEADER[0], created=MADE)
    return save(document)


def main() -> int:
    from .review_docx import TEMPLATE
    TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE.write_bytes(build())
    print(f"Wrote {TEMPLATE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
