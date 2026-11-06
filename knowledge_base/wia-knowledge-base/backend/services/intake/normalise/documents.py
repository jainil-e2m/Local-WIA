"""Deterministic document parsers → ordered units with structural locators."""
import io
from typing import Any

from backend.models.domain.intake import UnitIn

MAX_SHEET_ROWS = 5000  # per tab; beyond this the version is marked partial, never silently truncated


def google_doc_units(doc: dict, file_id: str) -> list[UnitIn]:
    units: list[UnitIn] = []
    tabs = doc.get("tabs") or [{"documentTab": {"body": doc.get("body", {})}, "tabProperties": {}}]

    def walk_tabs(tab_list, path=()):
        for tab in tab_list:
            props = tab.get("tabProperties", {})
            title = props.get("title")
            body = (tab.get("documentTab") or {}).get("body", {})
            _content(body.get("content", []), tab_id=props.get("tabId"), tab_title=title)
            walk_tabs(tab.get("childTabs", []), path + (title,))

    headings: list[str] = []

    def _content(elements, tab_id, tab_title):
        for el in elements:
            if "paragraph" in el:
                p = el["paragraph"]
                text = "".join((r.get("textRun") or {}).get("content", "") for r in p.get("elements", [])).strip()
                if not text:
                    continue
                style = (p.get("paragraphStyle") or {}).get("namedStyleType", "")
                if style.startswith("HEADING") or style == "TITLE":
                    level = 0 if style == "TITLE" else int(style.rsplit("_", 1)[-1])
                    del headings[level:]
                    headings.append(text)
                units.append(UnitIn("doc_heading" if style.startswith("HEADING") or style == "TITLE" else "doc_paragraph",
                                    text, {"kind": "doc", "file_id": file_id, "tab_id": tab_id, "tab": tab_title,
                                           "heading_path": list(headings), "start_index": el.get("startIndex")}))
            elif "table" in el:
                for r_i, row in enumerate(el["table"].get("tableRows", [])):
                    cells = []
                    for cell in row.get("tableCells", []):
                        cell_text = " ".join(
                            "".join((r.get("textRun") or {}).get("content", "") for r in c["paragraph"].get("elements", []))
                            for c in cell.get("content", []) if "paragraph" in c).strip()
                        cells.append(cell_text)
                    if any(cells):
                        units.append(UnitIn("doc_table_row", " | ".join(cells),
                                            {"kind": "doc", "file_id": file_id, "tab_id": tab_id, "tab": tab_title,
                                             "heading_path": list(headings), "table_start_index": el.get("startIndex"),
                                             "row": r_i}))

    walk_tabs(tabs)
    return units


def sheet_units(file_id: str, tabs: list[tuple[str, list[list[Any]]]]) -> tuple[list[UnitIn], list[str]]:
    """Rows as units, header-labelled. Cells stay strings exactly as Sheets formats them ('FALSE' is not truthy)."""
    units, notes = [], []
    for title, rows in tabs:
        if not rows:
            continue
        header = [str(h).strip() for h in rows[0]]
        if len(rows) > MAX_SHEET_ROWS:
            notes.append(f"tab '{title}': {len(rows)} rows, first {MAX_SHEET_ROWS} stored")
            rows = rows[:MAX_SHEET_ROWS]
        for i, row in enumerate(rows[1:], start=2):
            if not any(str(c).strip() for c in row):
                continue
            pairs = [f"{header[j] if j < len(header) and header[j] else f'col{j + 1}'}: {c}"
                     for j, c in enumerate(row) if str(c).strip()]
            units.append(UnitIn("sheet_row", "; ".join(pairs),
                                {"kind": "sheet", "file_id": file_id, "tab": title, "row": i}))
    return units, notes


def pdf_units(data: bytes, file_id: str) -> tuple[list[UnitIn], list[str]]:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    units, empty = [], []
    for n, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            units.append(UnitIn("pdf_page", text, {"kind": "pdf", "file_id": file_id, "page": n}))
        else:
            empty.append(n)
    notes = [f"pages without extractable text (scanned/image?): {empty}"] if empty else []
    return units, notes


def docx_units(data: bytes, file_id: str) -> list[UnitIn]:
    import docx
    document = docx.Document(io.BytesIO(data))
    units = []
    for i, para in enumerate(document.paragraphs):
        if para.text.strip():
            units.append(UnitIn("docx_paragraph", para.text, {"kind": "docx", "file_id": file_id, "paragraph": i}))
    for t_i, table in enumerate(document.tables):
        for r_i, row in enumerate(table.rows):
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                units.append(UnitIn("docx_table_row", " | ".join(cells),
                                    {"kind": "docx", "file_id": file_id, "table": t_i, "row": r_i}))
    return units


def transcript_text_units(text: str, file_id: str) -> list[UnitIn]:
    """Plain text / VTT transcripts (historical Zoom archives): one unit per cue or paragraph."""
    units, block = [], []
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.strip() in ("", "WEBVTT"):
            if block:
                units.append(UnitIn("transcript_cue", " ".join(block),
                                    {"kind": "text_file", "file_id": file_id, "cue": len(units)}))
                block = []
            continue
        if "-->" in line or line.strip().isdigit():
            continue
        block.append(line.strip())
    if block:
        units.append(UnitIn("transcript_cue", " ".join(block), {"kind": "text_file", "file_id": file_id, "cue": len(units)}))
    return units
