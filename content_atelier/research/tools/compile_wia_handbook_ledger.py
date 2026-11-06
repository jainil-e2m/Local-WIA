"""Build and validate the structured research ledger from its human-readable source.

This is an offline documentation utility. It does not modify runtime prompts,
call providers, or confer approval on the supplied handbook or interpretations.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
LEDGER = RESEARCH / "2026-10-13-wia-handbook-understanding-ledger.md"
SOURCE = RESEARCH / "sources" / "wia-handbook-2026-10-13" / "source-extract.json"
FIELD_NAMES = {
    "Basis": "basis",
    "Evidence": "evidence",
    "Understanding": "understanding",
    "Reasoning": "reasoning",
    "Build implication": "build_implication",
    "Check": "acceptance_check",
}
ALLOWED_BASES = {
    "Handbook guidance", "Handbook offer description",
    "Proposed calibration policy", "Proposed example",
}


def expand_reference(token: str) -> list[str]:
    ends = token.split("–")
    if len(ends) == 1:
        return ends
    first, last = ends
    if ".R" in first:
        prefix, start = first.split(".R")
        other_prefix, end = last.split(".R")
        if prefix != other_prefix:
            raise ValueError(f"Cross-table range is ambiguous: {token}")
        return [f"{prefix}.R{i:02d}" for i in range(int(start), int(end) + 1)]
    return [f"B{i:03d}" for i in range(int(first[1:]), int(last[1:]) + 1)]


def compile_ledger() -> dict:
    text = LEDGER.read_text(encoding="utf-8")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    archive = Path(source["archived_path"])
    expected_hash = source["sha256"]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_hash:
        raise ValueError("Archived handbook does not match the extraction source hash")
    original = Path(source["source_path"])
    if original.exists() and hashlib.sha256(original.read_bytes()).hexdigest() != expected_hash:
        raise ValueError("Original handbook has changed; create a new source version")
    known = {block["id"] for block in source["blocks"]}
    known.update(row["id"] for block in source["blocks"] for row in block.get("rows", []))
    records = []
    for match in re.finditer(r"^### (H\d{3}) ([^\n]+)\n(.*?)(?=^### |^## |\Z)", text, re.M | re.S):
        record_id, title, body = match.groups()
        category = list(re.finditer(r"^## (.+)$", text[:match.start()], re.M))[-1].group(1)
        fields = re.findall(r"^\*\*([^\n]+?):\*\* (.*?)(?=\n\n\*\*|\Z)", body.strip(), re.M | re.S)
        if {name for name, _ in fields} != set(FIELD_NAMES) or len(fields) != len(FIELD_NAMES):
            raise ValueError(f"Missing or duplicate field in {record_id}")
        record = {"id": record_id, "title": title, "category": category}
        record.update({FIELD_NAMES[name]: value.strip() for name, value in fields})
        record["basis"] = record["basis"].rstrip(".")
        if record["basis"] not in ALLOWED_BASES:
            raise ValueError(f"Unknown authority label in {record_id}")
        tokens = re.findall(r"B\d{3}(?:\.R\d{2})?(?:–B\d{3}(?:\.R\d{2})?)?", record["evidence"])
        refs = list(dict.fromkeys(ref for token in tokens for ref in expand_reference(token)))
        if not refs or not set(refs) <= known:
            raise ValueError(f"Invalid evidence reference in {record_id}")
        record["source_refs"] = refs
        record["source_id"] = "wia-handbook-2026-10-13-v1"
        record["interpretation_status"] = "research_recommendation"
        record["human_approval"] = "not_established"
        records.append(record)
    if [r["id"] for r in records] != [f"H{i:03d}" for i in range(1, 61)]:
        raise ValueError("Ledger must contain H001 through H060 in order")
    synthesis = text.split("## What this taste profile means in practice", 1)[1]
    sections = [{"title": m.group(1), "markdown": m.group(2).strip()}
                for m in re.finditer(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)",
                    "## What this taste profile means in practice" + synthesis, re.M | re.S)]
    payload = {
        "ledger_version": "2026-10-13.wia-handbook-understanding.v1",
        "recorded_date": "2026-10-13",
        "timezone": "Asia/Calcutta",
        "purpose": "Research knowledge for rebuilding Content Atelier content-angle discovery and selection",
        "runtime_status": "not_integrated",
        "authority_note": "Supplied handbook is design reference; new examples, thresholds and implementation choices are proposals. Derived reasoning is not founder approval.",
        "source": {"id": "wia-handbook-2026-10-13-v1", "title": "WIA Content System Handoff",
            "version": "1.0", "date": "2026-10-13", "sha256": expected_hash,
            "archived_docx": "sources/wia-handbook-2026-10-13/WIA_Content_System_Handbook.docx",
            "extraction": "sources/wia-handbook-2026-10-13/source-extract.json",
            "locator_kind": "OOXML body block and table row; not page numbers",
            "structural_audit": source["audit"]},
        "human_readable_ledger": LEDGER.name,
        "records": records,
        "derived_sections": sections,
    }
    output = LEDGER.with_suffix(".json")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"records": len(records), "source_references": sum(len(r["source_refs"]) for r in records),
            "derived_sections": len(sections), "source_hash_verified": True,
            "output": str(output), "runtime_modified": False}


if __name__ == "__main__":
    print(json.dumps(compile_ledger(), indent=2))
