"""The one-time seed from the ChatGPT-export analysis and today's knowledge base (L.B2, R52, section 4.12).

`storage_cli context-seed` runs this once per environment. It reads only committed material:

- `backend/knowledge_base/` 04 (roster), 05 (offer sheet) and 06 (rejection rules). WIA confirmed these in E.X2
  (`WIA-Rulings-2026-10-18.md` sections 2.1 to 2.3), so their entries load as confirmed items, with the E.X2
  approver as reviewer and the ruling as the review note.
- every entry of `research/chatgpt-export-2026-10-18/kb-candidates/`: one candidate per table row, rule section,
  bullet or paragraph, with its kind, the conversation files, attachments and chunk reports it cites, its date,
  its author (Whitney, the team, or the model), a model-written flag and its visibility (internal for every
  internal or gated price and every client-private result);
- the exemplar bank, as exemplar candidates;
- the published-content log, into `published_content` as unconfirmed rows.

Supplied documents (01, 02, 03) stay documents. Personal and confidential material is never loaded: an entry
with a contact detail, HR detail or WIA's own financials is skipped and counted, never stored. The custom GPT
instructions and ChatGPT memory were declined as a source (E.X1), so there is nothing else to add.

Each entry's source reference is its draft file and position, so a second run finds every entry already present
and changes nothing. After the seed has run, nothing from ChatGPT is accepted (R52): a run whose inputs differ
from the recorded seed is refused, and new facts enter through the operating-facts editor (L.F2).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from ..config import BACKEND_ROOT
from ..repository import insert
from . import items

REPOSITORY_ROOT = BACKEND_ROOT.parent
ANALYSIS = Path("research/chatgpt-export-2026-10-18")
DRAFTS = ANALYSIS / "kb-candidates"
KNOWLEDGE_BASE = Path("backend/knowledge_base")
# The seed reads the documents as WIA confirmed them in E.X2 (version 2), kept in the archive once later versions
# replace them, so its inputs, input hash and source references never change (R52). References keep the original path.
SEED_SOURCE = KNOWLEDGE_BASE / "archive" / "wia-kb-2026-10-18.v2"
PATTERNS = "rejection-rules.patterns.json"
SEED_MARKER = "context.seed"
EXPORT_DATE = date(2026, 10, 14)
MODEL = "model (the 18 October export analysis, from WIA's material)"
TEAM = "team (Gisselle Jiménez or another WIA team member)"
SKIP_SECTIONS = re.compile(r"^(how to use|how to read( this file)?|why this file exists)\b", re.I)

# What a citation looks like in the analysis: a conversation file (dated, or its 8-character ID), an export
# attachment or library file, or a chunk report naming a group of conversations.
CONVERSATION = re.compile(r"\b(20\d\d-\d\d-\d\d_[0-9a-f]{8})\b|(?<![0-9a-z_-])([0-9a-f]{8})(?![0-9a-z_-])")
ATTACHMENT = re.compile(r"\battachments(?:\s*\(([^)]*)\)|\s+((?:[A-Z]\d{1,2}|V\d\d|B\d|D\d)(?:\s*,\s*(?:[A-Z]\d{1,2}))*))?")
CHUNK = re.compile(r"\b([A-F]-(?:social|strategy|email|delivery|sales|megaemail)-\d)\b")
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
ISO = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")
DAY_MONTH = re.compile(r"\b(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (20\d\d)\b")
MONTH_YEAR = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (20\d\d)\b")
YEAR_MONTH = re.compile(r"\b(20\d\d)-(\d\d)\b(?!-\d)")

# Never stored (R52, L.B2): contact details, HR details and WIA's own financials.
PERSONAL = [
    ("contact detail", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\+?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")),
    ("HR detail", re.compile(r"\b(salary|salaries|payroll|pay rate|hourly rate|wages?|fired|termination|disciplinary|"
                             r"performance review|maternity|sick leave|employment terms?)\b", re.I)),
    ("WIA financials", re.compile(r"\b(profit|p&l|bank (account|balance)|tax(es)? (return|filing)|financial statements?|"
                                  r"(our|wia'?s|their own) (monthly |annual )?revenue (is|was|of)|cash ?flow)\b", re.I)),
]


@dataclass
class Entry:
    file: str
    section: str
    subsection: str | None
    shape: str  # row, rule, bullet, numbered or paragraph
    index: int
    text: str
    cells: dict = field(default_factory=dict)
    # The group label a table row sits under ("Voice", "CTA and format"), or a rule section's own lines, in order.
    group: str | None = None
    lines: list[str] = field(default_factory=list)

    @property
    def anchor(self) -> str:
        parts = [items.slug(self.section, 40)] + ([items.slug(self.subsection, 40)] if self.subsection else [])
        return f"{self.file}#{'/'.join(parts)}/{self.shape}{self.index:02d}"


def row_text(entry: "Entry", kind: str, body: dict) -> str:
    """A table row as one readable line, with the source the row cites; other entries keep their own words."""
    if entry.shape != "row":
        return entry.text[:8000]
    source = next((entry.cells[k] for k in ("Source", "Sources", "origin") if entry.cells.get(k)), None)
    line = items.render(kind, items.validate_body(kind, body))
    return (line + (f" (source: {clean(source)})" if source else ""))[:8000]


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("**", "").replace("`", "")).strip()


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def entries(path: Path, *, rule_sections: bool = False, preamble: str | None = None) -> list[Entry]:
    """Every entry of one draft document, in order: table rows, rule sections, list items and paragraphs.

    Text before the first section heading, the draft banner and the "how to use" sections are the document's
    own instructions, not entries; a knowledge-base document without headings names its preamble instead.
    """
    name = path.name
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[Entry] = []
    section, subsection, header, group = preamble, None, None, None
    counter: dict[tuple, int] = {}
    block: list[str] = []
    block_shape = None

    def emit(shape, text, cells=None, lines=None):
        if section is None or SKIP_SECTIONS.match(section) or (subsection and SKIP_SECTIONS.match(subsection)):
            return
        text = clean(text)
        if not text or set(text) <= set("-—"):
            return
        k = (section, subsection, shape)
        counter[k] = counter.get(k, 0) + 1
        out.append(Entry(name, section, subsection, shape, counter[k], text, cells or {},
                         group if shape == "row" else None, [clean(x) for x in lines or []]))

    def flush():
        nonlocal block, block_shape
        if block:
            emit(block_shape, " ".join(block), lines=block[1:] if block_shape == "rule" else None)
        block, block_shape = [], None

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("#"):
            flush()
            header, group = None, None
            level = len(stripped) - len(stripped.lstrip("#"))
            title = clean(stripped.lstrip("#"))
            if level == 1:
                continue
            if level == 2:
                section, subsection = title, None
            elif rule_sections and level == 3:
                subsection = title
                block, block_shape = [title], "rule"
            else:
                subsection = title
            continue
        if stripped.startswith(">") or stripped == "---":
            continue
        if stripped.startswith("|"):
            if block_shape != "rule":
                flush()
            cells = _cells(stripped)
            if header is None:
                header = cells
                continue
            if all(set(c) <= set("-: ") for c in cells):
                continue
            if sum(1 for c in cells if c) <= 1:
                # A group label inside a table, such as "Absolute bans": the rows below it belong to it.
                group = clean(next((c for c in cells if c), "")) or None
                continue
            row = {header[i] if i < len(header) else f"col{i}": cells[i] for i in range(len(cells))}
            emit("row", " | ".join(f"{k}: {v}" for k, v in row.items() if v), row)
            continue
        header = None if not stripped else header
        group = None if not stripped else group
        if block_shape == "rule":
            if stripped:
                block.append(re.sub(r"^[-*]\s+", "", stripped))
            continue
        if not stripped:
            if block_shape == "paragraph":
                flush()
            continue
        top_bullet = re.match(r"^[-*]\s+(.*)", line)
        top_number = re.match(r"^\d+\.\s+(.*)", line)
        if top_bullet or top_number:
            flush()
            block, block_shape = [(top_bullet or top_number).group(1)], "bullet" if top_bullet else "numbered"
        elif block_shape in ("bullet", "numbered") and (line.startswith(" ") or line.startswith("\t")):
            block.append(re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line))
        elif block_shape == "paragraph":
            block.append(stripped)
        else:
            flush()
            block, block_shape = [stripped], "paragraph"
    flush()
    return out


def citations(text: str) -> dict:
    conversations = []
    for dated, bare in CONVERSATION.findall(text):
        value = dated or bare
        if bare and not (re.search(r"\d", bare) and re.search(r"[a-f]", bare)):
            continue
        if value not in conversations and not any(c.endswith(value) for c in conversations):
            conversations.append(value)
    attachments = []
    for match in ATTACHMENT.finditer(text):
        ref = ("attachments " + (match.group(1) or match.group(2) or "")).strip()
        if ref not in attachments:
            attachments.append(ref)
    chunks = list(dict.fromkeys(CHUNK.findall(text)))
    return {k: v for k, v in (("conversations", conversations), ("attachments", attachments), ("chunks", chunks)) if v}


def dates(text: str) -> list[tuple[date, str]]:
    """Dates in an entry with their precision: day, month or the month part of a dated conversation file."""
    found = []
    for y, m, d in ISO.findall(text):
        try:
            found.append((date(int(y), int(m), int(d)), "day"))
        except ValueError:
            pass
    for d, mon, y in DAY_MONTH.findall(text):
        try:
            found.append((date(int(y), MONTHS[mon.lower()[:3]], int(d)), "day"))
        except ValueError:
            pass
    for mon, y in MONTH_YEAR.findall(text):
        found.append((date(int(y), MONTHS[mon.lower()[:3]], 1), "month"))
    for y, m in YEAR_MONTH.findall(text):
        if 1 <= int(m) <= 12:
            found.append((date(int(y), int(m), 1), "month"))
    return found


def statement_date(entry: Entry) -> tuple[date | None, str | None]:
    """The date the entry was stated: its Date column first, else the latest date it cites."""
    column = next((v for k, v in entry.cells.items() if k.lower() in {"date", "dates seen", "first published", "last stated"} and v), None)
    for candidate in ([column] if column else []) + [entry.text]:
        found = dates(candidate)
        if found:
            best = max(found, key=lambda x: (x[0], x[1] == "day"))
            return best[0], (column or None)
    return None, column


def screen(text: str) -> str | None:
    """The reason an entry must never be stored, or None."""
    for reason, pattern in PERSONAL:
        if pattern.search(text):
            return reason
    return None


def _visibility(value: str | None, default="public") -> str:
    v = (value or "").lower()
    return "internal" if ("internal" in v or "gated" in v) else default


def _author(text: str, default=MODEL) -> str:
    m = re.search(r"author\s+(Whitney|team|both)", text, re.I)
    if not m:
        return default
    return {"whitney": "Whitney", "team": TEAM, "both": "Whitney and the team"}[m.group(1).lower()]


def _rule_level(text: str) -> str:
    return "ban" if re.search(r"\bBan\b", text) and not re.match(r"^.{0,40}\bFlag\b", text) else "flag"


def _scope(text: str, default="all") -> str:
    m = re.search(r"scope\s+`?(angle|brief|all)`?", text)
    return m.group(1) if m else default


# Each rule's category (E.B11, items.RULE_CATEGORIES). KB 06 files its confirmed rules under group labels and the drafts
# under numbered sections; the groups that hold more than one category ("Absolute bans", "Positioning") name each rule's.
GROUP_CATEGORY = {"audience": "audience", "accuracy": "factual", "accuracy and claims": "factual", "offer": "offer",
                  "voice": "voice", "voice and style": "voice", "cta and format": "cta", "format": "cta",
                  "edit scope": "edit_scope", "process (edit behaviour)": "edit_scope", "positioning": "audience"}
CODE_CATEGORY = {
    "RR-01": "voice", "RR-02": "voice", "RR-03": "factual", "RR-04": "offer", "RR-05": "mechanism", "RR-06": "offer",
    "RR-07": "audience", "RR-08": "mechanism", "RR-09": "cta", "RR-10": "factual", "RR-11": "mechanism",
    "RR-12": "mechanism", "RR-13": "mechanism", "RR-14": "audience", "RR-15": "audience", "RR-16": "offer", "RR-17": "voice",
    "P01": "mechanism", "P04": "mechanism", "P05": "mechanism", "P06": "offer", "P07": "mechanism", "P08": "offer",
    "P13": "voice", "P14": "mechanism", "P15": "voice", "P16": "cta",
    "A03": "offer", "A04": "offer", "A05": "offer", "A11": "offer", "A12": "offer"}
FILE_CATEGORY = {"roster-corrections.md": "factual", "cta-catalogue.md": "cta", "case-study-method.md": "factual",
                 "04-team-roster.md": "factual", "05-offer-sheet.md": "offer"}


def rule_category(entry: Entry, code: str | None = None) -> str:
    if code in CODE_CATEGORY:
        return CODE_CATEGORY[code]
    for label in (entry.group, re.sub(r"^\d+\.\s*", "", entry.section)):
        label = (label or "").strip().lower()
        if label in GROUP_CATEGORY:
            return GROUP_CATEGORY[label]
        if label.startswith("team house rules"):
            return "edit_scope"
    return FILE_CATEGORY.get(entry.file, "audience")


RULE_META = re.compile(r"^(?:Ban|Flag)\b")


def rule_parts(title: str, entry: Entry) -> tuple[str, str | None, str | None]:
    """A draft rule section as (statement, origin, since): the heading with any text before "Origin:" (the heading
    alone is the rule when the section only quotes its origin), the quoted origin, and the first date of its range."""
    lines = list(entry.lines)
    meta = lines.pop(0) if lines and RULE_META.match(lines[0]) else ""
    body = " ".join(lines)
    if "Origin:" in meta:
        meta, origin = meta.split("Origin:", 1)
        extra, origin = "", f"{origin} {body}"
    else:
        extra, _, origin = body.partition("Origin:")
    extra = extra.strip(" ·")
    found = sorted(d for d, _ in dates(meta))
    statement = title.strip() + (f": {extra}" if extra else "")
    return statement[:8000], (origin.strip() or None) and origin.strip()[:2000], found[0].isoformat() if found else None


FIGURE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:/|per )\s?(?:month|mo|day|year))?")


def _offer_name(section: str) -> str:
    return re.sub(r"^\d+\.\s*", "", section).split("(")[0].strip() or section


def candidates(root: Path = REPOSITORY_ROOT) -> tuple[list[dict], list[dict], dict]:
    """Every draft entry as an item to add, every published-log row, and what was skipped (with reasons only)."""
    drafts = root / DRAFTS
    out, published, skipped = [], [], {}

    def add(entry: Entry, kind: str, body: dict, *, key=None, visibility="public", sensitivity="none",
            permission=None, author=MODEL, model_written=True, confidence="medium", part=None):
        reason = screen(entry.text)
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            return
        when, when_text = statement_date(entry)
        # The position names the subsection too: entries are counted per subsection, so without it two different
        # entries (rule P16 and rule P17, both "rule01" of their section) would share a key, and accepting both would
        # retire one of them (L.B3 supersedes by key).
        where = items.slug(entry.section, 30) + (f".{items.slug(entry.subsection, 30)}" if entry.subsection else "")
        out.append({
            "kind": kind, "key": key or f"{items.KEY_PREFIX[kind]}:{items.slug(entry.file.split('.')[0], 30)}."
                                            f"{where}.{entry.shape}{entry.index:02d}",
            "body": body, "status": "candidate", "visibility": visibility, "sensitivity": sensitivity,
            "permission": permission, "source_kind": "export_seed",
            "source_ref": f"{DRAFTS.as_posix()}/{entry.anchor}" + (f"/{items.slug(part, 40)}" if part else ""),
            "source_detail": {"draft": f"{DRAFTS.as_posix()}/{entry.file}", "section": entry.section,
                              "subsection": entry.subsection, "export": "ChatGPT export of 14 October 2026",
                              **citations(entry.text), **({"date_text": when_text} if when_text else {}),
                              "entry_sha256": hashlib.sha256(entry.text.encode()).hexdigest()},
            "statement_date": when, "author": author, "model_written": model_written, "confidence": confidence,
            "text": row_text(entry, kind, body)})

    for e in entries(drafts / "rejection-rules.md", rule_sections=True):
        title = e.subsection or e.section
        code = re.match(r"^([A-Z]\d\d)\s+(.*)", title)
        if e.shape == "rule" and code:
            statement, origin, since = rule_parts(code.group(2), e)
            add(e, "rule", {"code": code.group(1), "statement": statement, "level": _rule_level(e.text),
                            "scope": _scope(e.text), "origin": origin, "since": since,
                            "category": rule_category(e, code.group(1))}, author=_author(e.text))
        else:
            add(e, "rule", {"statement": e.text[:8000], "level": "flag", "scope": _scope(e.text), "category": rule_category(e)},
                author=_author(e.text), confidence="low")

    for e in entries(drafts / "roster-corrections.md"):
        name = clean(e.cells.get("Person") or e.cells.get("Name") or "")
        if e.shape == "row" and name:
            sect = e.section.lower()
            state = "former" if "no longer" in sect else "outside" if "outside" in sect or "partners" in sect else "current"
            if name.startswith("An unnamed"):
                state = "former"
            role = e.cells.get("Role in the export") or e.cells.get("What the export shows") or e.cells.get("Relationship") or "-"
            if "Viktor" in name:
                state = "not_a_person"
            add(e, "roster_member", {"name": name, "role": clean(role)[:400] or "-", "state": state,
                                     "notes": clean(e.cells.get("Change from KB 04", ""))[:2000] or None},
                key=items.key_for("roster_member", name))
        elif "invented" in e.section.lower():
            for invented in re.findall(r'"([^"]+)"', e.text) or [e.text[:80]]:
                add(e, "roster_member", {"name": invented, "role": "invented by ChatGPT; never use", "state": "invented"},
                    key=items.key_for("roster_member", invented), part=invented)
        else:
            add(e, "rule", {"statement": e.text, "level": "flag", "scope": "all", "category": rule_category(e)})

    for e in entries(drafts / "offer-facts.md"):
        offer = _offer_name(e.section)
        if e.shape == "row" and "Offer" in e.cells:
            name = clean(e.cells["Offer"]).split(":")[0].strip()
            add(e, "offer", {"name": name, "description": clean(e.cells["Offer"])},
                key=items.key_for("offer", name), visibility=_visibility(e.cells.get("Visibility")))
        elif e.shape == "row" and "Fact" in e.cells:
            fact = clean(e.cells["Fact"])
            figure = FIGURE.search(fact)
            visibility = _visibility(e.cells.get("Visibility"))
            if figure:
                add(e, "price", {"offer": offer, "amount": figure.group(0), "terms": fact[:2000]},
                    visibility="internal" if visibility == "internal" or "public" not in (e.cells.get("Visibility") or "").lower() else "public")
            else:
                add(e, "offer", {"name": offer, "description": fact}, visibility=visibility)
        elif "retired" in e.section.lower():
            add(e, "offer", {"name": e.text.split(":")[0][:400], "description": e.text, "state": "retired"})
        else:
            add(e, "offer", {"name": offer[:400], "description": e.text}, confidence="low")

    for e in entries(drafts / "belief-statements.md"):
        if e.shape == "row" and e.cells.get("Statement"):
            add(e, "belief", {"statement": clean(e.cells["Statement"]), "said_or_published": e.cells.get("Kind")},
                author="Whitney", model_written=False)
        else:
            add(e, "belief", {"statement": e.text}, confidence="low")

    for e in entries(drafts / "cta-catalogue.md"):
        if e.shape == "row":
            wording = e.cells.get("Keyword") or e.cells.get("Wording") or e.cells.get("Wording or link") or e.cells.get("CTAs seen") or e.text
            kind_cell = (e.cells.get("Type") or "").lower()
            cta_type = ("dm_keyword" if "Keyword" in e.cells else "reply" if "Wording" in e.cells and "Used for" in e.cells
                        else next((t for t in ("waitlist", "apply", "register", "podcast", "link", "none") if t in kind_cell), "other"))
            add(e, "cta", {"wording": clean(wording)[:8000], "cta_type": cta_type,
                           "used_for": clean(e.cells.get("Used for") or e.cells.get("Offer") or "")[:400] or None,
                           "channel": "instagram" if cta_type == "dm_keyword" else "email" if cta_type == "reply" else None})
        else:
            add(e, "rule", {"statement": e.text, "level": "flag", "scope": "brief", "category": rule_category(e)})

    for e in entries(drafts / "case-study-method.md"):
        sect = (e.subsection or e.section).lower()
        if e.shape == "row" and "public" in sect:
            add(e, "result", {"claim": clean(e.cells.get("Result as published") or e.text),
                              "client_type": clean(e.cells.get("Client type", "")) or None,
                              "first_published": clean(e.cells.get("First published", "")) or None,
                              "framing": clean(e.cells.get("Notes", "")) or None},
                key=f"result:{items.slug(e.cells.get('#', str(e.index)))}", permission="published")
        elif e.shape == "row":
            add(e, "result", {"claim": clean(e.cells.get("Metric type") or e.text),
                              "client_type": clean(e.cells.get("Client type", "")) or None,
                              "framing": clean(e.cells.get("Status", "")) or None},
                key=f"result:{items.slug(e.cells.get('#', str(e.index)))}", permission="none",
                visibility="internal", sensitivity="client_private")
        elif "never use" in sect:
            add(e, "result", {"claim": e.text, "framing": "never use"}, permission="none",
                visibility="internal", sensitivity="client_private")
        else:
            add(e, "rule", {"statement": e.text, "level": "flag", "scope": "brief", "category": rule_category(e)})

    for name, process in (("process-catalogue.md", None), ("content-workflow.md", "Content workflow")):
        for e in entries(drafts / name):
            title = re.sub(r"^[A-Z0-9]+\.\s*", "", e.section)
            what = clean(e.cells.get("What happens") or e.cells.get("Content") or e.cells.get("Order") or
                         e.cells.get("Steps") or e.cells.get("WIA range") or e.text)
            step = clean(e.cells.get("Step") or e.cells.get("Framework") or e.cells.get("Metric") or
                         e.cells.get("Campaign") or e.cells.get("Sequence") or "") or None
            add(e, "process_step", {"process": (f"{process}: {title}" if process else title)[:400], "what": what[:8000],
                                    "step": step[:200] if step else None, "owner": clean(e.cells.get("Owner", "")) or None})

    for e in entries(drafts / "format-guide.md"):
        add(e, "format_rule", {"format": e.section[:400], "rule": e.text})

    for e in entries(drafts / "audience-language.md"):
        theme = (e.subsection or e.section)[:400]
        if e.shape == "row" and e.cells.get("Objection"):
            add(e, "audience_phrase", {"phrase": f"{clean(e.cells['Objection'])}: {clean(e.cells.get('Her answer', ''))}",
                                       "theme": "Objection and Whitney's answer", "speaker": "prospect"})
        elif e.shape == "row":
            add(e, "audience_phrase", {"phrase": e.text, "theme": theme})
        else:
            add(e, "audience_phrase", {"phrase": e.text, "theme": theme,
                                       "speaker": "prospect or client" if "words" in e.section.lower() else None},
                confidence="low" if "survey" in e.section.lower() else "medium")

    for e in entries(drafts / "published-content-log.md"):
        if e.shape != "row":
            add(e, "process_step", {"process": "Published content: what the log shows", "what": e.text})
            continue
        reason = screen(e.text)
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        # A dated row, or a run of days, starts on its first date; a month or "onward" alone stays undated.
        start = re.match(r"(20\d\d)-(\d\d)-(\d\d)", e.cells.get("Date", "").strip())
        published.append({
            "published_on": date(*map(int, start.groups())) if start else None, "channel": clean(e.cells.get("Channel") or "unknown"),
            "title": clean(e.cells.get("Item and hook") or e.text)[:2000], "status": "unconfirmed",
            "source_kind": "export_seed", "source_ref": f"{DRAFTS.as_posix()}/{e.anchor}",
            "details": {"date_text": e.cells.get("Date"), "export_status": e.cells.get("Status"),
                        "siblings_and_notes": clean(e.cells.get("Siblings and notes", "")) or None,
                        "draft": f"{DRAFTS.as_posix()}/{e.file}", **citations(e.text)}})

    inherit(out)
    resolve_citations(out, root)
    out.extend(content_plan_candidates(root))

    for line_no, line in enumerate((drafts / "exemplar-bank.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        record = json.loads(line)
        if record.get("type") == "meta":
            continue
        text = record.get("her_text") or record.get("text") or ""
        cite = " ".join(str(record.get(k) or "") for k in ("file", "source", "date"))
        reason = screen(text + " " + str(record.get("why") or ""))
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        when = dates(str(record.get("date") or ""))
        whose = record.get("author") or "Whitney"
        out.append({
            "kind": "exemplar", "key": f"exemplar:{items.slug(record['id'])}",
            "body": {k: v for k, v in {"channel": record.get("channel") or "other", "text": text[:8000],
                                       "label": record.get("type"), "why": (record.get("why") or "")[:4000] or None,
                                       "published": str(record.get("published", "")).lower().startswith("true") or None,
                                       "ai_text": (record.get("ai_text") or "")[:8000] or None}.items() if v is not None},
            "status": "candidate", "visibility": "public", "sensitivity": "none", "permission": None,
            "source_kind": "export_seed", "source_ref": f"{DRAFTS.as_posix()}/exemplar-bank.jsonl#{record['id']}",
            "source_detail": {"draft": f"{DRAFTS.as_posix()}/exemplar-bank.jsonl", "export": "ChatGPT export of 14 October 2026",
                              **citations(cite), **({"conversations": [record["file"].removesuffix(".md")]} if record.get("file") else {}),
                              "date_text": record.get("date"), "entry_sha256": hashlib.sha256(text.encode()).hexdigest()},
            "statement_date": max(d for d, _ in when) if when else None,
            "author": whose if whose != "model" else MODEL,
            # Whitney's or the team's own words are not model-written; the analyst's "why" note is provenance only.
            # A ChatGPT draft Whitney approved or edited is still model-written: authorship separates her from the
            # model (R52); her approval is recorded by the review, not by the flag.
            "model_written": whose.lower() in {"model", "chatgpt"} or "chatgpt" in whose.lower(), "confidence": "high" if record.get("type") == "approved_final" else "medium",
            "text": text[:8000]})
    return out, published, skipped


def inherit(out: list[dict]) -> None:
    """An entry the draft does not cite or date itself takes its section's citations or latest date, marked so.

    The drafts often cite once for a group of lines (a table's notes, a list under a cited heading). The reviewer
    sees that the citation or date came from the section, never a value presented as the entry's own; an entry
    in an undated section is dated "as of the export".
    """
    groups: dict[tuple, list[dict]] = {}
    for item in out:
        d = item["source_detail"]
        groups.setdefault((d["draft"], d["section"]), []).append(item)
    for members in groups.values():
        cited = {k: list(dict.fromkeys(v for m in members for v in m["source_detail"].get(k, [])))
                 for k in ("conversations", "attachments", "chunks")}
        dated = [m["statement_date"] for m in members if m["statement_date"]]
        for m in members:
            d = m["source_detail"]
            if not any(d.get(k) for k in ("conversations", "attachments", "chunks")) and any(cited.values()):
                d.update({k: v for k, v in cited.items() if v})
                d["citations_from"] = "section"
            elif not any(d.get(k) for k in ("conversations", "attachments", "chunks")):
                # The analysis's own summary line: it cites only its draft, so it is a low-confidence candidate.
                d["citations_from"] = "draft"
                m["confidence"] = "low"
            if not m["statement_date"]:
                m["statement_date"] = max(dated) if dated else EXPORT_DATE
                d["date_from"] = "section" if dated else "export"


RESOLVED = ANALYSIS / "citations-resolved.json"
PLAN_MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}


def content_plan_candidates(root: Path) -> list[dict]:
    """KB 14, the six-week content plan drafted from WIA's dated offers and workflow (E.B11 i), as content-plan
    candidates: it is model-written, so a person confirms each line before it compiles (section 4.12)."""
    kb = root / SEED_SOURCE
    path = kb / "14-content-plan.md"
    if not path.is_file():
        return []
    version = json.loads((kb / "manifest.json").read_text(encoding="utf-8"))["knowledge_base_version"]
    out = []
    for e in entries(path, preamble="Content plan"):
        week_of, purpose = None, None
        weeks = e.cells.get("Weeks", "")
        day, month = re.match(r"(\d{1,2})", weeks), re.search(r"\b([A-Za-z]{3})[a-z]*\b", weeks)
        if day and month and month.group(1).lower() in PLAN_MONTHS:
            week_of = date(2026, PLAN_MONTHS[month.group(1).lower()], int(day.group(1)))
        found = re.search(r"\b(ATTRACT|WARM|CONVERT)\b", e.text)
        if found and e.shape == "row":
            purpose = found.group(1).lower()
        body = {"topic": (clean(e.cells["Promotes"]) if e.cells.get("Promotes") else e.text)[:8000],
                **({"week_of": week_of.isoformat()} if week_of else {}), **({"purpose": purpose} if purpose else {}),
                **({"notes": clean(e.cells["Notes"])[:2000]} if e.cells.get("Notes") else {})}
        out.append({"kind": "content_plan_entry", "key": f"plan:{items.slug(e.section, 30)}.{e.shape}{e.index:02d}", "body": body,
                    "status": "candidate", "visibility": "public", "sensitivity": "none", "permission": None,
                    "source_kind": "knowledge_base", "source_ref": f"{KNOWLEDGE_BASE.as_posix()}/{version}/{e.anchor}",
                    "source_detail": {"document": f"{KNOWLEDGE_BASE.as_posix()}/14-content-plan.md", "version": version,
                                      "section": e.section, **citations(e.text)},
                    "statement_date": date(2026, 10, 18), "author": MODEL, "model_written": True, "confidence": "medium",
                    "valid_from": week_of, "text": e.text[:8000]})
    return out


def resolve_citations(out: list[dict], root: Path) -> None:
    """Conversation files for entries the drafts cite only by chunk report, section or draft: found once in the
    raw export by the entry's quoted words (L.B2, under D11) and committed as IDs and dates only, so the seed is the
    same in every environment and the raw export can be retired (L.X2)."""
    path = root / RESOLVED
    if not path.is_file():
        return
    resolved = json.loads(path.read_text(encoding="utf-8"))["resolved"]
    for item in out:
        files = resolved.get(item["source_ref"])
        if files:
            item["source_detail"]["conversations"] = files
            item["source_detail"]["conversations_from"] = "the export: the entry's quoted words found in these conversations"


def confirmed_from_knowledge_base(root: Path, approver: str) -> list[dict]:
    """KB 04, 05 and 06 entries, which WIA confirmed in E.X2, as confirmed items with the ruling as review note."""
    kb = root / SEED_SOURCE
    manifest = json.loads((kb / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["knowledge_base_version"]
    # KB 06's lint patterns, confirmed with it: each joins its rule, so the version's patterns derive from the store.
    lint: dict[str, list[dict]] = {}
    for p in json.loads((kb / PATTERNS).read_text(encoding="utf-8"))["rules"]:
        lint.setdefault(p["id"], []).append({k: p[k] for k in ("pattern", "kind", "scope", "message", "applies_to") if p.get(k)})
    rulings = {"04-team-roster.md": "E.X2: WIA rulings 2026-10-18 section 2.1 (team roster)",
               "05-offer-sheet.md": "E.X2: WIA rulings 2026-10-18 section 2.2 (offer sheet)",
               "06-rejection-rules.md": "E.X2: WIA rulings 2026-10-18 section 2.3 (contradictions) and the confirmed rejection rules"}
    out = []

    def add(entry: Entry, kind, body, key, *, visibility="public", author="WIA", part=None):
        when, _ = statement_date(entry)
        out.append({"kind": kind, "key": key, "body": body, "status": "confirmed", "visibility": visibility,
                    "sensitivity": "none", "permission": None, "source_kind": "knowledge_base",
                    "source_ref": f"{KNOWLEDGE_BASE.as_posix()}/{version}/{entry.anchor}" + (f"/{items.slug(part, 40)}" if part else ""),
                    "source_detail": {"document": f"{KNOWLEDGE_BASE.as_posix()}/{entry.file}", "version": version,
                                      "section": entry.section, **citations(entry.text)},
                    "statement_date": when or date(2026, 10, 14), "author": author, "model_written": False,
                    "confidence": "high", "reviewed_by": approver, "review_note": rulings[entry.file],
                    "valid_from": date(2026, 10, 14), "text": row_text(entry, kind, body)})

    for e in entries(kb / "04-team-roster.md"):
        name = e.cells.get("Name")
        sect = e.section.lower()
        if e.shape == "row" and name:
            state = "former" if "former" in sect else "outside" if "outside" in sect else "current"
            aliases = [a.strip() for a in (e.cells.get("Transcript may show") or "").split(",") if a.strip()]
            role = e.cells.get("Role") or e.cells.get("Former role") or e.cells.get("Who they are") or "-"
            add(e, "roster_member", {"name": name, "role": role, "state": state, "aliases": aliases,
                                     **({"left_on": e.cells["Left"]} if e.cells.get("Left") else {})},
                items.key_for("roster_member", name))
        elif "reject" in sect:
            for invented in re.findall(r'"([^"]+)"', e.text):
                add(e, "roster_member", {"name": invented, "role": "invented by ChatGPT; never use", "state": "invented"},
                    items.key_for("roster_member", invented), part=invented)
        elif e.text.startswith("Viktor"):
            add(e, "roster_member", {"name": "Viktor", "role": "an AI agent the team uses; never credit it as a person",
                                     "state": "not_a_person"}, items.key_for("roster_member", "Viktor"))
        else:
            add(e, "rule", {"statement": e.text, "level": "ban" if "never" in e.text.lower() else "flag", "scope": "all",
                            "category": rule_category(e)},
                f"rule:kb-roster.{items.slug(e.section, 30)}.{e.shape}{e.index:02d}")
    for e in entries(kb / "05-offer-sheet.md"):
        if e.shape == "row" and e.cells.get("Offer"):
            name = e.cells["Offer"]
            add(e, "offer", {"name": name, "description": e.cells.get("What it is") or name,
                             "ownership": e.cells.get("Who does what"), "access": e.cells.get("How a buyer gets to it")},
                items.key_for("offer", name.split("(")[0]), visibility="public")
        elif "retired" in e.section.lower() and e.shape == "bullet":
            name = e.text.split(":")[0]
            add(e, "offer", {"name": name, "description": e.text, "state": "retired"}, items.key_for("offer", "retired " + name))
        elif not e.text.startswith("Source:"):
            # A "Source: ..." line cites its section's facts; it is not a rule of its own.
            add(e, "rule", {"statement": e.text, "level": "ban" if re.search(r"\b(no|never|not)\b", e.text, re.I) else "flag",
                            "scope": "all", "category": rule_category(e)},
                f"rule:kb-offers.{items.slug(e.section, 30)}.{e.shape}{e.index:02d}")
    for e in entries(kb / "06-rejection-rules.md", preamble="Rejection rules"):
        if e.shape == "row" and e.cells.get("id"):
            author = {"whitney": "Whitney", "team": TEAM, "both": "Whitney and the team"}.get((e.cells.get("author") or "").lower(), "WIA")
            code = clean(e.cells["id"])
            add(e, "rule", {"code": code, "statement": e.cells["rule"],
                            "level": "ban" if e.cells.get("ban/flag") == "ban" else "flag",
                            "scope": e.cells.get("scope") if e.cells.get("scope") in ("angle", "brief", "all") else "all",
                            "since": e.cells.get("since"), "origin": e.cells.get("origin"), "category": rule_category(e, code),
                            "patterns": lint.get(code, [])},
                f"rule:{items.slug(code)}", author=author)
        elif e.shape != "row" and e.section != "Rejection rules":
            # The text before the table is its legend (what ban, flag, scope and origin mean), not a rule.
            add(e, "rule", {"statement": e.text, "level": "flag", "scope": "all", "category": rule_category(e)},
                f"rule:kb-rules.{items.slug(e.section, 30)}.{e.shape}{e.index:02d}")
    return out


def input_hash(root: Path = REPOSITORY_ROOT) -> str:
    files = sorted((root / DRAFTS).glob("*")) + [root / RESOLVED] * (root / RESOLVED).is_file() + [root / SEED_SOURCE / n for n in
                                                  ("manifest.json", "04-team-roster.md", "05-offer-sheet.md", "06-rejection-rules.md",
                                                   "14-content-plan.md", PATTERNS)]
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode())
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def run(conn, *, actor: str, approver: str, root: Path = REPOSITORY_ROOT) -> dict:
    """Load the seed; idempotent. Refused after the seed has run with other inputs (R52)."""
    if not items.table_ready(conn):
        raise RuntimeError("Apply migration 006 (storage_cli migrate) before seeding the context store")
    if not (approver or "").strip():
        raise ValueError("Name the E.X2 approver whose confirmations the knowledge-base entries carry")
    if not (root / DRAFTS).is_dir():
        raise RuntimeError(f"The seed reads {DRAFTS.as_posix()} from a repository checkout; the backend image does not carry "
                           "research/. Run it from a checkout with ATELIER_DATABASE_URL pointing at the environment.")
    digest = input_hash(root)
    marker = conn.execute("SELECT value FROM settings WHERE key=%s", (SEED_MARKER,)).fetchone()
    if marker and marker["value"].get("input_sha256") != digest:
        raise ValueError("The one-time ChatGPT seed has already run with other inputs; nothing from ChatGPT is accepted "
                         "after it (R52). New facts enter through the operating-facts editor.")
    drafts, published, skipped = candidates(root)
    confirmed = confirmed_from_knowledge_base(root, approver)
    created = {"confirmed": 0, "candidates": 0, "published": 0}
    # A source deleted by source (L.B1) stays deleted: a second run never brings its entries back.
    deleted = [r["details"] for r in conn.execute("SELECT details FROM decisions WHERE action='delete_source'")]

    def was_deleted(row):
        return any(d.get("source_kind") == row["source_kind"] and (
            row["source_ref"] == d.get("source_ref") or d.get("source_ref_prefix") and row["source_ref"].startswith(d["source_ref_prefix"]))
            for d in deleted)
    skipped_deleted = sum(1 for row in confirmed + drafts + published if was_deleted(row))
    drafts = [d for d in drafts if not was_deleted(d)]
    published = [p for p in published if not was_deleted(p)]
    keys = set()
    for item in confirmed + drafts:
        key = item["key"]
        if item["status"] == "confirmed" and key in keys:
            # Two confirmed entries that name the same thing both stand, each under its own key. A candidate keeps the
            # key of the confirmed entry it would replace, so accepting it supersedes that entry (L.B3).
            key = f"{key}.{hashlib.sha256(item['source_ref'].encode()).hexdigest()[:8]}"
        if item["status"] == "confirmed":
            keys.add(key)
        fields = {k: v for k, v in item.items() if k not in {"key"}}
        _, new = items.add_item(conn, key=key, created_by=actor, **fields)
        if new:
            created["confirmed" if item["status"] == "confirmed" else "candidates"] += 1
    for row in published:
        exists = conn.execute("SELECT 1 FROM published_content WHERE source_kind=%s AND source_ref=%s",
                              (row["source_kind"], row["source_ref"])).fetchone()
        if not exists:
            insert(conn, "published_content", {"content_id": "published_" + hashlib.sha256(row["source_ref"].encode()).hexdigest()[:24],
                                               **row, "created_by": actor})
            created["published"] += 1
    from .performance import seed_export_outcomes
    created["performance_entries"] = seed_export_outcomes(conn, actor)
    totals = {"confirmed_items": len(confirmed), "candidates": len(drafts), "published_content": len(published),
              "skipped_personal_or_confidential": skipped, "skipped_deleted": skipped_deleted,
              "supplied_documents": ["content_strategy (01)", "founder_voice_guide (02)", "accelerator_strategy (03)"],
              "custom_gpt_and_memory": "declined as a source (E.X1); nothing to add"}
    if not marker:
        conn.execute("INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,%s)",
                     (SEED_MARKER, json.dumps({"input_sha256": digest, "seeded_on": date.today().isoformat(), **totals}), actor))
    return {"status": "seeded" if any(created.values()) else "already_seeded", "created": created, **totals}
