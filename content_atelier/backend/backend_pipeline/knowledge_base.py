"""WIA knowledge base: WIA's documents loaded whole as a trusted system-prompt prefix (E.B11, R41).

Documents live in a folder (CONTENT_ATELIER_KNOWLEDGE_BASE_DIR, default backend/knowledge_base/) with a
manifest.json naming each file, its heading, version, owner and status. The current version is committed to
this private repository; earlier versions are kept under knowledge_base/archive/ so their runs replay.
backend/knowledge_base.example/ shows the layout with placeholders.

Manifest format 1 (version wia-kb-2026-10-18.v1) is loaded exactly as before, so its prefix and hashes are
unchanged. Format 2 (E.B11 c) adds, per document: an effective date, a review interval, the stages that load it
(strategist, brief, verifier, extraction) and its provenance. Its prefix shows each document's status and
effective date, and says which documents are drafts, instead of calling the whole knowledge base authoritative.
Phase L's compiler (L.B4) later writes the same format from confirmed brand-kit items.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .store import canonical_hash

MANIFEST = "manifest.json"
REQUIRED_DOCUMENTS = ("content_strategy", "founder_voice_guide", "accelerator_strategy", "team_roster", "offer_sheet")
PLACEHOLDER_MARKER = "KNOWLEDGE-BASE-PLACEHOLDER"
STAGES = ("strategist", "brief", "verifier", "extraction")
HEADER = (
    "# WIA KNOWLEDGE BASE (supplied by Wedding Industry Ads; authoritative for strategy, positioning and voice; "
    "NOT evidence of anything said on this week's calls)"
)
HEADER_V2 = (
    "# WIA KNOWLEDGE BASE (version {version}; WIA's own documents and WIA-confirmed facts, plus drafts made from "
    "WIA's own dated material; NOT evidence of anything said on this week's calls)\n"
    "Each document below states its status and effective date.\n"
    "- supplied: written by WIA (or for WIA) and given to us; authoritative for strategy and voice, except where "
    "a later rule or confirmed fact corrects it.\n"
    "- confirmed: settled by WIA's rulings; authoritative.\n"
    "- draft: drafted from WIA's own material and not yet confirmed by WIA. Use it for context and judgement; "
    "never state a fact taken only from a draft in public copy without listing it under verify before publishing.\n"
    "Where documents disagree, the rejection rules win, then confirmed documents, then supplied documents, then drafts."
)

Name = Annotated[str, Field(min_length=1, pattern=r"\S")]
Stage = Literal["strategist", "brief", "verifier", "extraction"]
# Documents a stage loads whatever a version's stage list says. The verifier must recognise a card's quote of Whitney's
# belief statements as WIA's stated view, not an invented quote (E.B10); versions written before the compiler listed
# the verifier for belief_statements give it the strategist and brief only.
STAGE_EXTRAS = {"verifier": ("belief_statements",)}


def loads_for(entry, stage: str | None) -> bool:
    """Whether a format-2 document is part of a stage's knowledge base (every document when no stage is named)."""
    return stage is None or stage in (entry.stages or []) or entry.key in STAGE_EXTRAS.get(stage, ())


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Name
    # Whose words or rules these are: WIA (published or supplied), Whitney, a named team member, or "model".
    author: Name
    # True when a model wrote the text (the voice guide was written by ChatGPT from Whitney's corpus).
    model_written: bool = False
    # Benchmark weeks any text derives from; a week is held out only if no document derives from it (E.B17).
    derived_from_weeks: list[int] = Field(default_factory=list)


class DocumentEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: Name
    file: Name
    heading: Name
    version: Name
    owner: Name
    # approved: WIA approved it for this use; supplied: WIA supplied it; confirmed: settled by WIA's rulings
    # (format 2); unconfirmed: drafted by the team and awaiting WIA (format 1); draft: drafted from WIA's own
    # material, not yet confirmed (format 2).
    status: Literal["approved", "supplied", "confirmed", "unconfirmed", "draft"]
    effective_date: date | None = None
    review_interval_days: int | None = Field(default=None, gt=0)
    stages: list[Stage] | None = None
    provenance: Provenance | None = None
    approver: str | None = None


class RulePatternsRef(BaseModel):
    """The version's lint patterns (E.B11 (2)): compiled from its rules, written beside its documents, bound by hash."""
    model_config = ConfigDict(extra="forbid")
    file: Name
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    rules: int = Field(ge=0)


class SupersessionsRef(BaseModel):
    """The superseded lines of the supplied documents a version applied (E.B25 (c), knowledge/supersessions.py): the
    committed list's file and hash when it was applied, and the entries applied, this version's and its bases'."""
    model_config = ConfigDict(extra="forbid")
    file: Name
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    applied: list[Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]{1,40}$")]]


class AdditionsRef(SupersessionsRef):
    """The supplied documents a version added (E.B25 (e), knowledge/additions.py): the committed list's file and hash
    when it was applied, and the entries applied, this version's and its bases'."""


class KnowledgeBaseManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    knowledge_base_version: Name
    format: Literal[1, 2] = 1
    documents: list[DocumentEntry]
    rule_patterns: RulePatternsRef | None = None
    supersessions: SupersessionsRef | None = None
    additions: AdditionsRef | None = None


class LoadedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entry: DocumentEntry
    text: str
    sha256: str


class KnowledgeBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    format: int = 1
    stage: str | None = None
    manifest_sha256: str
    documents: list[LoadedDocument]
    text: str
    # The lint patterns a compiled version derives from its rules (E.B11 (2)); None for a version that names none.
    rule_patterns: list[dict] | None = None
    rule_patterns_sha256: str | None = None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def document(self, key: str) -> LoadedDocument | None:
        return next((d for d in self.documents if d.entry.key == key), None)

    def refs(self) -> dict:
        """Frozen identity for run input refs: hashes and versions only, never document text."""
        refs = {
            "version": self.version,
            "sha256": self.sha256,
            "manifest_sha256": self.manifest_sha256,
            "documents": [
                {"key": d.entry.key, "file": d.entry.file, "version": d.entry.version, "owner": d.entry.owner,
                 "status": d.entry.status, "sha256": d.sha256, "characters": len(d.text)}
                for d in self.documents
            ],
        }
        if self.format == 2:
            # Live runs record when they used drafts (E.B11 c).
            refs["stage"] = self.stage
            refs["drafts_used"] = [d.entry.key for d in self.documents if d.entry.status in {"draft", "unconfirmed"}]
        if self.rule_patterns_sha256:
            refs["rule_patterns_sha256"] = self.rule_patterns_sha256
        return refs

    def refs_hash(self) -> str:
        return canonical_hash(self.refs())

    def overdue(self, today: date) -> list[str]:
        """Documents past their review date (6.B14, L.B8 warn; they still load)."""
        return [d.entry.key for d in self.documents if d.entry.effective_date and d.entry.review_interval_days
                and today > d.entry.effective_date + timedelta(days=d.entry.review_interval_days)]


def _read_text(path: Path, fmt: int = 1) -> tuple[str, str]:
    """Text and its hash. Format 1 hashes the raw bytes (its recorded runs did); format 2 hashes the normalised
    text, so a Windows checkout with CRLF line endings and a Linux one record the same hash (E.B11 e)."""
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig").replace("\r\n", "\n").strip()
    return text, hashlib.sha256(raw if fmt == 1 else text.encode("utf-8")).hexdigest()


def _manifest_sha256(manifest_bytes: bytes, fmt: int) -> str:
    if fmt == 1:
        return hashlib.sha256(manifest_bytes).hexdigest()
    normalised = manifest_bytes.decode("utf-8-sig").replace("\r\n", "\n").strip()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def _section(entry: DocumentEntry, text: str, fmt: int) -> str:
    if fmt == 1:
        return f"## {entry.heading}\n{text}"
    meta = f"Status: {entry.status}"
    if entry.effective_date:
        meta += f"; effective {entry.effective_date.isoformat()}"
    meta += f"; owner: {entry.owner}"
    if entry.provenance and entry.provenance.model_written:
        meta += "; written by a model from WIA's material, so WIA's corrections and approved finals win over it"
    return f"## {entry.heading}\n({meta}.)\n{text}"


def load_knowledge_base(root: Path, *, allow_placeholders: bool = False, stage: str | None = None) -> KnowledgeBase:
    """Load and assemble the knowledge base. With a stage (format 2), only that stage's documents are loaded."""
    root = Path(root)
    manifest_path = root / MANIFEST
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"WIA knowledge base manifest not found at {manifest_path}. "
            "See backend/knowledge_base.example/README.md for the expected files."
        )
    if stage is not None and stage not in STAGES:
        raise ValueError(f"Unknown knowledge-base stage: {stage}")
    manifest_bytes = manifest_path.read_bytes()
    manifest = KnowledgeBaseManifest.model_validate(json.loads(manifest_bytes.decode("utf-8-sig")))
    keys = [d.key for d in manifest.documents]
    if len(keys) != len(set(keys)):
        raise ValueError("Knowledge base document keys must be unique")
    missing = [key for key in REQUIRED_DOCUMENTS if key not in keys]
    if missing:
        raise ValueError("Knowledge base is missing required documents: " + ", ".join(missing))
    if manifest.format == 2:
        incomplete = [d.key for d in manifest.documents
                      if not (d.effective_date and d.review_interval_days and d.stages and d.provenance)]
        if incomplete:
            raise ValueError("Format 2 documents need an effective date, a review interval, stages and provenance: "
                             + ", ".join(incomplete))
    selected = [d for d in manifest.documents if manifest.format == 1 or loads_for(d, stage)]
    documents = []
    for entry in selected:
        path = (root / entry.file).resolve()
        if root.resolve() not in path.parents:
            raise ValueError(f"Knowledge base file must sit inside the knowledge base folder: {entry.file}")
        if not path.is_file():
            raise FileNotFoundError(f"Knowledge base document not found: {path}")
        text, digest = _read_text(path, manifest.format)
        if not text:
            raise ValueError(f"Knowledge base document is empty: {entry.file}")
        if PLACEHOLDER_MARKER in text and not allow_placeholders:
            raise ValueError(f"Knowledge base document is still a placeholder: {entry.file}")
        documents.append(LoadedDocument(entry=entry, text=text, sha256=digest))
    header = HEADER if manifest.format == 1 else HEADER_V2.format(version=manifest.knowledge_base_version)
    text = "\n\n".join([header] + [_section(d.entry, d.text, manifest.format) for d in documents])
    patterns, patterns_sha = _rule_patterns(root, manifest)
    return KnowledgeBase(
        version=manifest.knowledge_base_version,
        format=manifest.format,
        stage=stage if manifest.format == 2 else None,
        manifest_sha256=_manifest_sha256(manifest_bytes, manifest.format),
        documents=documents,
        text=text,
        rule_patterns=patterns,
        rule_patterns_sha256=patterns_sha,
    )


def _rule_patterns(root: Path, manifest: KnowledgeBaseManifest) -> tuple[list[dict] | None, str | None]:
    """The lint patterns a manifest names, checked against the hash it records: a version's patterns are compiled
    from its rules and can never be edited by hand beside it (E.B11 (2))."""
    ref = manifest.rule_patterns
    if ref is None:
        return None, None
    path = (root / ref.file).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise FileNotFoundError(f"The knowledge base names lint patterns it does not hold: {ref.file}")
    text, digest = _read_text(path, 2)
    if digest != ref.sha256:
        raise ValueError(f"{ref.file} does not match the hash its version records; it is compiled from the rules, never edited")
    return json.loads(text)["rules"], digest


def publish(conn, root: Path, *, approver: str) -> dict:
    """Write a format-2 knowledge-base version from files into brand_kit_docs (E.B11 e, migration 005).

    Idempotent per (key, version): a document already published with the same hash is left alone, and a different
    body under an existing version is refused, so a version never changes after publication.
    """
    root = Path(root)
    manifest_bytes = (root / MANIFEST).read_bytes()
    manifest = KnowledgeBaseManifest.model_validate(json.loads(manifest_bytes.decode("utf-8-sig")))
    if manifest.format != 2:
        raise ValueError("Only format 2 knowledge bases are published to brand_kit_docs")
    files = load_knowledge_base(root)  # Every validation the loader applies, before anything is written.
    written, unchanged = [], []
    for entry in manifest.documents:
        text, digest = _read_text(root / entry.file, 2)
        existing = conn.execute("SELECT sha256 FROM brand_kit_docs WHERE key=%s AND version=%s",
                                (entry.key, manifest.knowledge_base_version)).fetchone()
        if existing:
            if existing["sha256"] != digest:
                raise ValueError(f"{entry.key} is already published under {manifest.knowledge_base_version} with other content")
            unchanged.append(entry.key)
            continue
        conn.execute("""INSERT INTO brand_kit_docs(key,version,heading,owner,status,effective_date,review_interval_days,
            approver,approved_at,sha256,body,object_key) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now(),%s,%s,%s)""",
            (entry.key, manifest.knowledge_base_version, entry.heading, entry.owner, entry.status, entry.effective_date,
             entry.review_interval_days, approver, digest, text, entry.file))
        written.append(entry.key)
    conn.execute("""INSERT INTO settings(key,value,updated_by) VALUES ('knowledge_base.manifest.' || %s, %s, %s)
        ON CONFLICT (key) DO NOTHING""", (manifest.knowledge_base_version,
        json.dumps({"manifest": json.loads(manifest_bytes.decode("utf-8-sig")),
                    "sha256": _manifest_sha256(manifest_bytes, 2),
                    **({"patterns": files.rule_patterns} if files.rule_patterns is not None else {})}), approver))
    return {"version": manifest.knowledge_base_version, "written": written, "unchanged": unchanged}


def load_published(conn, version: str, *, stage: str | None = None) -> KnowledgeBase:
    """The same knowledge base, read from brand_kit_docs: identical text and hashes to the files it came from."""
    row = conn.execute("SELECT value FROM settings WHERE key=%s", ("knowledge_base.manifest." + version,)).fetchone()
    if not row:
        raise ValueError(f"Knowledge base {version} is not published")
    stored = row["value"] if isinstance(row["value"], dict) else json.loads(row["value"])
    manifest = KnowledgeBaseManifest.model_validate(stored["manifest"])
    if stage is not None and stage not in STAGES:
        raise ValueError(f"Unknown knowledge-base stage: {stage}")
    bodies = {r["key"]: r for r in conn.execute("SELECT key,body,sha256 FROM brand_kit_docs WHERE version=%s", (version,))}
    documents = []
    for entry in manifest.documents:
        if not loads_for(entry, stage):
            continue
        if entry.key not in bodies:
            raise ValueError(f"Published knowledge base {version} is missing {entry.key}")
        documents.append(LoadedDocument(entry=entry, text=bodies[entry.key]["body"], sha256=bodies[entry.key]["sha256"]))
    text = "\n\n".join([HEADER_V2.format(version=version)] + [_section(d.entry, d.text, 2) for d in documents])
    patterns = stored.get("patterns") if manifest.rule_patterns else None
    return KnowledgeBase(version=version, format=2, stage=stage, manifest_sha256=stored["sha256"], documents=documents, text=text,
                         rule_patterns=patterns, rule_patterns_sha256=manifest.rule_patterns.sha256 if patterns is not None else None)


ROSTER_SECTIONS = {"## Current team": "current", "## Former staff": "former", "## Outside people": "outside"}


# A compiled roster line (L.B4, `knowledge/items.render`): "- Name: role (current; left ...; shown as A, B) (source: ...)".
ROSTER_LINE = re.compile(r"^- (?P<name>[^:]+): (?P<role>.+) \((?:current|former|outside|not a person|invented)(?:; left [^;)]*)?"
                         r"(?:; shown as (?P<shown>[^)]*))?\)(?: \(source: .*\))?$")


def team_roster(root: Path) -> list[dict]:
    """The roster document's tables (a file version) or lines (a compiled version) as rows: name, role, the names a
    transcript may show, and status.

    Status is current, former (never present as current) or outside (named often, not staff). Used for speaker
    labels on the card screen (E.F2) and the verification step's roster checks (E.B10).
    """
    path = Path(root) / "04-team-roster.md"
    if not path.is_file():
        return []
    rows, status = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            status = next((value for prefix, value in ROSTER_SECTIONS.items() if line.startswith(prefix)), None)
            continue
        compiled = ROSTER_LINE.match(line.strip()) if status is not None else None
        if compiled:
            name, role, shown = compiled["name"].strip(), compiled["role"].strip(), (compiled["shown"] or "").split(",")
            shown = [alias.strip() for alias in shown] if status == "current" else []
        else:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if status is None or not line.startswith("|") or len(cells) < 3 or cells[0] in {"Name", ""} or set(cells[0]) <= {"-"}:
                continue
            name, role = cells[0], cells[1]
            shown = [alias.strip() for alias in cells[2].split(",")] if status == "current" else []
        aliases = list(dict.fromkeys([name, name.split()[0], *[a for a in shown if a]]))
        rows.append({"name": name, "role": role, "status": status, "aliases": aliases})
    return rows
