"""The week's pack document as a Word file (NP.B12, the .docx; the content-packs plan, section 5.6).

The same document as `GET /weeks/{id}/packs.md`, in the same order and with the same words: the week's plan on top, then per
pack the angle card, the brief's strategy, every piece in its final form and unabbreviated, "Before you publish" with the
open notes and the client quotes to clear. It is rendered from the Markdown `document.markdown` writes, so the two exports can
never drift apart, through `python-docx` with its built-in styles and no client template:

- `#` to `######` headings become Word headings (the document's first heading is its title, and each "# Pack" or the bank
  after a `---` starts a new page);
- `- ` lines become bulleted list items and `1. ` lines numbered ones (the number written out, so each list starts at one in
  Word and in Google Docs alike);
- `**bold**` and `*italic*` spans keep their emphasis, and any other asterisk stays as written;
- every other line is text, and lines without a blank line between them stay one paragraph with their line breaks (a script,
  a slide, the email's send header).

The file is deterministic for a given Markdown and export time: the core properties carry the export time and the archive's
entries a fixed date. No model call; read only.

The week's review document (5.B14, `briefs/review_docx.py`) uses the same converter on its own Markdown, appended to the
template it ships with instead of a blank document: the template carries the title, so the first heading is a heading.
"""
from __future__ import annotations

import io
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from docx import Document
from docx.shared import Pt

MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAKER = "Content Atelier"

HEADING = re.compile(r"^(#{1,6}) +(\S.*)$")
BULLET = re.compile(r"^\s*- (.*)$")
NUMBERED = re.compile(r"^\s*(\d{1,3})\. (.*)$")
RULE = re.compile(r"^-{3,}$")
# A span is emphasis only when it closes on the same line and does not start or end on a space; "5 * 3" stays as written.
INLINE = re.compile(r"(\*\*(?=\S)(?:(?!\*\*).)+?(?<=\S)\*\*|(?<![\w*])\*(?=[^\s*])[^*\n]+?(?<=[^\s*])\*(?![\w*]))")
# Characters XML 1.0 cannot carry; python-docx refuses them, so a stray one in copy would otherwise fail the whole export.
NOT_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")
ZIP_DATE = (1980, 1, 1, 0, 0, 0)


def runs(paragraph, text: str):
    """The text as runs, `**bold**` and `*italic*` spans with their emphasis."""
    for part in INLINE.split(NOT_XML.sub("", text)):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            paragraph.add_run(part[1:-1]).italic = True
        else:
            paragraph.add_run(part)


def _numbered(document, number: str, text: str):
    paragraph = document.add_paragraph(style="List Paragraph")
    paragraph.paragraph_format.left_indent = Pt(36)
    paragraph.paragraph_format.first_line_indent = Pt(-18)
    paragraph.add_run(f"{number}.\t")
    runs(paragraph, text)
    return paragraph


def build(markdown: str, document=None):
    """The python-docx document for the Markdown subset the pack document uses. With `document` (a template that already
    carries its title) the Markdown is appended to it and every heading is a heading; without, the first is the title."""
    titled = document is not None
    document = document if document is not None else Document()
    current = None  # the paragraph a following line continues, until a blank line, a heading or a list item
    new_page = False
    for line in markdown.splitlines():
        if not line.strip():
            current = None
            continue
        if RULE.match(line):
            current, new_page = None, True
            continue
        if heading := HEADING.match(line):
            level = len(heading.group(1))
            paragraph = document.add_heading("", level=0 if not titled else min(level, 9))
            runs(paragraph, heading.group(2).strip())
            paragraph.paragraph_format.page_break_before = new_page and titled and level == 1
            titled, current, new_page = True, None, False
            continue
        new_page = False
        if item := NUMBERED.match(line):
            current = _numbered(document, item.group(1), item.group(2))
        elif item := BULLET.match(line):
            current = document.add_paragraph(style="List Bullet")
            runs(current, item.group(1))
        elif current is not None:
            current.add_run().add_break()
            runs(current, line.strip())
        else:
            current = document.add_paragraph()
            runs(current, line.strip())
    return document


def render(markdown: str, *, title: str, created: datetime, template: Path | BinaryIO | None = None) -> bytes:
    """The .docx bytes: the Markdown rendered (after `template`'s own content, when given: a path or an open file), the
    core properties set to the export, the archive's dates fixed."""
    opened = None if template is None else Document(template if hasattr(template, "read") else str(template))
    document = build(markdown, opened)
    stamp(document, title=title, created=created)
    return save(document)


def stamp(document, *, title: str, created: datetime):
    """The core properties of an export: its title and time, the maker, and nothing a template brought with it."""
    core = document.core_properties
    core.title, core.author, core.last_modified_by = title, MAKER, MAKER
    core.subject = core.keywords = core.comments = core.category = ""
    core.created = core.modified = created.astimezone(UTC).replace(tzinfo=None, microsecond=0)
    core.revision = 1


def save(document) -> bytes:
    """The document's bytes with every archive entry at a fixed date, so the same content is always the same file."""
    saved = io.BytesIO()
    document.save(saved)
    out = io.BytesIO()
    with zipfile.ZipFile(saved) as source, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        for entry in source.infolist():
            info = zipfile.ZipInfo(entry.filename, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = entry.external_attr
            target.writestr(info, source.read(entry.filename))
    return out.getvalue()


def docx(repo, week_id: str, actor=None, *, exported: datetime | None = None) -> bytes:
    """GET /weeks/{id}/packs.docx: the week's pack document, as `packs.md` renders it, as a Word file."""
    from . import document

    exported = exported or datetime.now(UTC)
    text = document.markdown(repo, week_id, actor, exported=exported)
    return render(text, title=f"Content Atelier Packs, {week_id}", created=exported)
