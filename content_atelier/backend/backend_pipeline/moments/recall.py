"""Scene recall against golden scenes (plan 2.B11, E.B12's "done when", the Phase 2 exit criteria "Golden fixture" and "Scene recall").

A person marks the scenes that matter in real documents (the golden file); this measures, per golden scene, whether an
extraction found it **with a verified quote**, so two scene profiles can be compared on the same documents (`--profile`).
Nothing here calls a model.

Golden file (JSON):

    {"version": 1, "name": "funktastic-chain", "scenes": [
      {"id": "g1",
       "document": {"transcript_id": "transcript_...", "content_hash": "...", "title": "..."},   # any one of the three
       "anchor": "an exact or near-exact phrase the scene is built on",
       "kind": "quote",                      # quote (default): a phrase from the call | paraphrase: the scene in other words
       "min_overlap": 0.6,                   # paraphrase only: share of the anchor's content words found (default 0.6)
       "note": "why a person marked it"}]}

A golden scene is **found** when a verified moment of that document, from the extractor version measured, either quotes the
anchor (its quote contains the anchor or is contained in it, ignoring case, whitespace and punctuation), or has an anchor
passage that contains the anchor, or (paraphrase) covers enough of the anchor's content words across its quote, record and
anchor passages. It is **lost to a quote mismatch** when the same match is only found among the unverified records: the
extraction saw the scene and its quote could not be bound. Recall is found over total; the lost ones are listed, because the
exit criterion is that no scene is lost to a repairable quote mismatch.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..cycle.verification import STOPWORDS
from . import store

WORD = re.compile(r"\w+")


def norm(text: str) -> str:
    return " ".join(WORD.findall((text or "").lower()))


def content_words(text: str) -> set[str]:
    return {w for w in WORD.findall((text or "").lower()) if len(w) > 2 and w not in STOPWORDS}


def load_golden(path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    scenes = data.get("scenes") if isinstance(data, dict) else None
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("A golden file holds a non-empty list of scenes")
    seen = set()
    for scene in scenes:
        if not scene.get("id") or scene["id"] in seen:
            raise ValueError("Every golden scene needs a unique id")
        seen.add(scene["id"])
        if not scene.get("anchor") or not norm(scene["anchor"]):
            raise ValueError(f"Golden scene {scene['id']} needs an anchor phrase")
        if not isinstance(scene.get("document"), dict) or not any(scene["document"].get(k) for k in ("transcript_id", "content_hash", "title")):
            raise ValueError(f"Golden scene {scene['id']} names its document by transcript_id, content_hash or title")
        if scene.get("kind", "quote") not in ("quote", "paraphrase"):
            raise ValueError(f"Golden scene {scene['id']}: kind is quote or paraphrase")
    return data


def resolve_document(conn, ref: dict) -> dict | None:
    for column in ("transcript_id", "content_hash", "title"):
        if ref.get(column):
            rows = conn.execute(f"SELECT * FROM transcripts WHERE {column}=%s ORDER BY canonical_document_id NULLS FIRST, transcript_id",
                                (ref[column],)).fetchall()
            if rows:
                return rows[0]
    return None


def anchor_texts(moment: dict, document: dict) -> list[str]:
    by_id = {p["passage_id"]: p for p in document["passage_map"]}
    return [document["original_text"][by_id[r["passage_id"]]["start"]:by_id[r["passage_id"]]["end"]]
            for r in moment["evidence_refs"] if "anchor" in r["roles"] and r["passage_id"] in by_id]


def matches(scene: dict, moment: dict, document: dict) -> str | None:
    """How a moment matches a golden scene (`quote`, `anchor_passage`, `paraphrase`) or None."""
    anchor = norm(scene["anchor"])
    quote = norm(moment["moment_body"].get("quote", ""))
    if anchor and quote and (anchor in quote or quote in anchor):
        return "quote"
    passages = [norm(t) for t in anchor_texts(moment, document)] if moment["quote_verified"] else []
    if any(anchor in p for p in passages):
        return "anchor_passage"
    if scene.get("kind") == "paraphrase":
        wanted = content_words(scene["anchor"])
        body = moment["moment_body"]
        have = content_words(" ".join([body.get("quote", ""), body.get("proposition", ""), body.get("context_summary", ""), *passages]))
        if wanted and len(wanted & have) / len(wanted) >= float(scene.get("min_overlap", 0.6)):
            return "paraphrase"
    return None


def measure(conn, golden: dict, *, extractor_version: str | None = None) -> dict:
    """Recall of one extractor version (or of any, when None) against the golden scenes."""
    results = []
    for scene in golden["scenes"]:
        document = resolve_document(conn, scene["document"])
        entry = {"id": scene["id"], "found": False, "lost_to_quote_mismatch": False, "moment_id": None, "match": None}
        results.append(entry)
        if document is None:
            entry["problem"] = "the document is not in the database"
            continue
        entry["document_id"] = document["transcript_id"]
        # A scene a later extraction under the same profile replaced (`superseded_by`) is not that profile's result any more.
        rows = conn.execute(f"""SELECT * FROM key_moments m WHERE m.document_id=%(doc)s AND {store.extracted_by()}
            AND NOT (m.checks ? 'superseded_by') ORDER BY m.quote_verified DESC, m.moment_id""", {"doc": document["transcript_id"], **store.extracted_by_params(extractor_version)}).fetchall()
        for row in rows:
            how = matches(scene, row, document)
            if how and row["quote_verified"]:
                entry.update(found=True, moment_id=row["moment_id"], match=how, lost_to_quote_mismatch=False)
                break
            if how and not entry["lost_to_quote_mismatch"] and not entry["found"]:
                entry.update(lost_to_quote_mismatch=True, moment_id=row["moment_id"], match=how)
    found = sum(r["found"] for r in results)
    lost = [r["id"] for r in results if r["lost_to_quote_mismatch"] and not r["found"]]
    return {"extractor_version": extractor_version, "scenes": len(results), "found": found, "recall": round(found / len(results), 4),
            "lost_to_quote_mismatch": lost, "missed": [r["id"] for r in results if not r["found"] and not r["lost_to_quote_mismatch"]],
            "results": results}


def versions_of(conn, golden: dict) -> list[str]:
    """The extractor versions that stored a moment for any of the golden documents."""
    ids = [d["transcript_id"] for s in golden["scenes"] if (d := resolve_document(conn, s["document"]))]
    return [r["v"] for r in conn.execute("""SELECT extractor_version AS v FROM key_moments WHERE document_id=ANY(%(ids)s) AND extractor_version IS NOT NULL
        UNION SELECT a->>'extractor_version' FROM key_moments m,
          jsonb_array_elements(COALESCE(m.checks->'also_extracted_by','[]'::jsonb)) a WHERE m.document_id=ANY(%(ids)s) ORDER BY 1""", {"ids": ids})]


def compare(conn, golden: dict, versions: list[str] | None = None) -> dict:
    """Recall of each extractor version on the same golden scenes, and which scenes each one found that the other did not."""
    versions = versions or versions_of(conn, golden)
    measured = {v: measure(conn, golden, extractor_version=v) for v in versions}
    table = {s["id"]: {v: next(r for r in measured[v]["results"] if r["id"] == s["id"])["found"] for v in versions} for s in golden["scenes"]}
    return {"golden": golden.get("name"), "scenes": len(golden["scenes"]), "versions": versions,
            "recall": {v: measured[v]["recall"] for v in versions}, "by_version": measured, "found_by": table,
            "only_found_by": {v: [i for i, row in table.items() if row[v] and not any(row[o] for o in versions if o != v)] for v in versions}}
