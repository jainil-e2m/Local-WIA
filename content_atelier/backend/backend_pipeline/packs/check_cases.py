"""Labelled cases for the pack's fidelity check (NP.X5; the content-packs plan, sections 5.5 and NP-7).

A case is one sentence of a real pack with the verdict the check should have given: a clause the check missed in a reading
(the paid proof's pairs 2 and 6), or a factual correction WIA made in a pack. The cases hold client words, so they live in
`research/` (R48); this module holds no case, only their shape, how a check's answer is scored against them, and how a
week's person-made pack edits are listed as candidate cases for a person to label.

- `load` reads and checks a case file (a JSON list).
- `score` says which cases a check's statements caught: a case is caught when a statement judged unsupported or guardrail
  (or a quote placed out of its moment) overlaps its sentence.
- `candidates` lists the lines people changed in a week's packs, with the fidelity check's verdict on the line before, so
  each factual correction becomes a case (`research/packs-2026-10/check-cases.json`).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import contracts_v2 as c2
from . import text as T

VERDICTS = ("unsupported", "guardrail")
FIELDS = ("case_id", "source", "piece", "sentence", "expected", "why")


def load(path: str | Path) -> list[dict]:
    """The cases in a file, each checked for its fields, its piece key and its verdict."""
    cases = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("A case file is a JSON list of cases")
    seen = set()
    for case in cases:
        missing = [f for f in FIELDS if not case.get(f)]
        if missing:
            raise ValueError(f"Case {case.get('case_id') or '?'} has no {', '.join(missing)}")
        if case["piece"] not in c2.PIECE_KEYS or case["expected"] not in VERDICTS:
            raise ValueError(f"Case {case['case_id']}: piece is one of {', '.join(c2.PIECE_KEYS)}; expected is unsupported or guardrail")
        if case["case_id"] in seen:
            raise ValueError(f"Case {case['case_id']} appears twice")
        seen.add(case["case_id"])
    return cases


def _flags(statements: list[dict]) -> list[dict]:
    return [s for s in statements if s.get("verdict") in VERDICTS or (s.get("verdict") == "supported" and s.get("in_moment") is False)]


def score(cases: list[dict], statements: list[dict]) -> dict:
    """{"caught": [...], "missed": [...]}: each case with the statement that caught it, or none."""
    flags = _flags(statements)
    caught, missed = [], []
    for case in cases:
        target = T.norm(case["sentence"])
        hit = next((s for s in flags if s.get("piece") in (None, case["piece"]) and target
                    and (T.norm(s["text"]) in target or target in T.norm(s["text"]))), None)
        (caught if hit else missed).append({**case, "statement": hit})
    return {"caught": caught, "missed": missed}


def candidates(conn, week_id: str) -> list[dict]:
    """The lines people changed in the week's packs (edits and reverts, delegated ones marked), each with the line before and
    after and whether the fidelity check had flagged the line before: the raw material for new cases."""
    out = []
    rows = conn.execute("""SELECT p.pack_id,p.supersedes_id,p.created_at,p.content_body->'change' AS change FROM content_packs p
        WHERE p.week_id=%s AND p.contract_version=%s AND p.supersedes_id IS NOT NULL
        AND p.content_body->'change'->>'kind' IN ('edit','revert') ORDER BY p.created_at,p.pack_id""", (week_id, c2.VERSION)).fetchall()
    for row in rows:
        change = row["change"] or {}
        pieces = {r["slot_key"]: r["content_body"] for r in conn.execute(
            "SELECT slot_key,content_body FROM content_assets WHERE pack_id=%s", (row["pack_id"],)).fetchall()}
        for key in change.get("pieces") or []:
            piece = pieces.get(key) or {}
            done = set()
            # A piece's change list carries its earlier versions' changes too: this version's are the last for each path.
            for c in reversed(piece.get("changes") or []):
                if c.get("kind") not in ("edited", "reverted") or c.get("path") not in (change.get("paths") or []) or c["path"] in done:
                    continue
                done.add(c["path"])
                flagged = [f for f in piece.get("findings") or [] if f.get("path") == c["path"]]
                out.append({"pack_id": row["pack_id"], "piece": key, "path": c["path"], "before": c.get("before"),
                            "after": c.get("after"), "by": change.get("by"), "delegated": bool(change.get("delegated")),
                            "at": change.get("at"), "flagged_before": bool(flagged)})
    return out
