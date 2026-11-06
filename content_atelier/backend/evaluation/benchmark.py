"""Benchmark version 1 (E.B2): the labels that exist today, stored as calibration rows with their source and proxy flag.

- Week 1: the six originals with Whitney's overall verdict ("1's across the board"; no per-angle ratings were
  recorded), each reframed by her own alternative from the same excerpts. Her verdict, not a proxy.
- Week 2: her ChatGPT's verdict on the batch, marked as a proxy (only the batch verdict survives).
- Weeks 3 and 4: the 16 October report's user-endorsed reference angles, marked as proxies.
- The 38 export preference pairs (source chatgpt_export, proxy), so E.B3's calibration set survives the export's
  retirement (L.X2).
- Week 5: added from E.X3 as the first clean held-out labels. Week 6 is held out and untouched: nothing here reads it.

Week N is backfill folder weekN, admitted as the week starting 2026-06-01 plus 7(N-1) days (backfill.py): Week 5 starts
on 29 June and Week 6 on 6 July. Golden scenes are marked by a person (E.B12, E.B18); none are marked yet.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from backend_pipeline.store import canonical_hash

PROJECT = Path(__file__).resolve().parents[2]
RESEARCH = PROJECT / "research"
VERSION = "benchmark-v1.2026-10-18"
HELD_OUT = {"week5": "held-out labels from E.X3 (Whitney's live review)", "week6": "held out; untouched"}
SOURCES = {
    "week1_originals": PROJECT / "testing" / "document_qa" / "source_audit.json",
    "week1_verdict": RESEARCH / "quality-experiments-2026-10-18" / "prompts" / "founder_feedback.md",
    "week1_alternatives": RESEARCH / "quality-experiments-2026-10-18" / "prompts" / "whitney_alternatives_w1.md",
    "week1_excerpts": RESEARCH / "quality-experiments-2026-10-18" / "sources" / "week1.json",
    "week2_angles": RESEARCH / "week2-luna-pro-strategic-test-review-2026-10-13.md",
    "week2_excerpts": RESEARCH / "quality-experiments-2026-10-18" / "sources" / "week2.json",
    "weeks3_4_traces": RESEARCH / "root-cause-2026-10-16" / "source-to-angle-traces.json",
    "export_pairs": RESEARCH / "chatgpt-export-2026-10-18" / "data" / "t1_pairs.jsonl",
}
# The Week 2 verdict survives only as quotes in the analysis (Content-Quality-Analysis.md, lines 52 and 463).
WEEK2_VERDICT = {"verdict": "meaningfully better, but still cautious and somewhat generic",
                 "source_document": "backend/docs/Content-Atelier-Content-Quality-Analysis.md"}
WEEK3_CASES = {"commercial-value", "creative-decision", "quiet-inbox"}


def week_start(n: int) -> date:
    return date(2026, 6, 1) + timedelta(days=7 * (n - 1))


def guard(path: Path) -> Path:
    """Nothing in the benchmark may read the held-out Week 6 (E.B17)."""
    if re.search(r"(^|[\\/_-])week6([\\/_.-]|$)", str(path), re.I):
        raise ValueError("Week 6 is held out; the benchmark never reads it")
    return path


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", text.replace("’", "'").lower()).strip()


def whitney_alternatives(text: str) -> list[dict]:
    blocks = re.split(r"\n(?=Angle \d+ \|)", text)
    out = []
    for block in blocks:
        head = re.match(r"Angle (\d+) \| (.+)", block)
        if not head:
            continue
        fields = dict(re.findall(r"^([^:\n]+): (.+)$", block, re.M))
        out.append({"number": int(head.group(1)), "title": head.group(2).strip(), "original": fields.get("Original proposed angle", "").strip(),
                    "pillar_type": fields.get("Content pillar / type"), "audience": fields.get("Audience"),
                    "why_it_matters": fields.get("Why this matters"), "wia_expertise": fields.get("WIA’s expertise or process")
                    or fields.get("WIA's expertise or process"), "evidence": fields.get("Evidence in the referenced call")})
    return out


def label(item_kind, item_id, disposition, source, *, week, proxy, rater, author, reframe=None, central_point_kept=None,
          rubric_ratings=None, details=None):
    body = {"item_kind": item_kind, "item_id": item_id, "disposition": disposition, "source": source, "week_id": week,
            "proxy": proxy, "rater": rater, "author": author, "reframe": reframe, "central_point_kept": central_point_kept,
            "rubric_ratings": rubric_ratings, "reason_code": None, "details": {**(details or {}), "benchmark": VERSION}}
    return {"label_id": "label_bench_" + canonical_hash([VERSION, item_kind, item_id, source])[:24], **body}


def build_labels() -> list[dict]:
    labels = []
    originals = json.loads(guard(SOURCES["week1_originals"]).read_text(encoding="utf-8"))["angles"]
    verdict = guard(SOURCES["week1_verdict"]).read_text(encoding="utf-8").strip().splitlines()[0]
    alternatives = {_norm(a["original"]): a for a in whitney_alternatives(guard(SOURCES["week1_alternatives"]).read_text(encoding="utf-8"))}
    week1 = f"week_{week_start(1).isoformat()}"
    for angle in originals:
        alt = alternatives.get(_norm(angle["title"]))
        if not alt:
            raise ValueError(f"No alternative recorded for the Week 1 original {angle['title']!r}")
        labels.append(label("benchmark_angle", angle["angle_id"], "reframe", "whitney_week1_review_2026-10-13", week=week1, proxy=False,
                            rater="Whitney Hodges", author="Whitney Hodges", central_point_kept=False,
                            reframe={"title": alt["title"], "why_it_matters": alt["why_it_matters"], "wia_expertise": alt["wia_expertise"],
                                     "pillar_type": alt["pillar_type"], "audience": alt["audience"]},
                            rubric_ratings={"overall": 1, "scope": "batch verdict applied to each angle; no per-angle ratings"},
                            details={"title": angle["title"], "moment_ids": angle["moment_ids"], "verdict": verdict,
                                     "run": "week1-gpt6-luna-partial-angle-diagnostic-20261008-a4"}))
    week2_titles = re.findall(r"^### \d+\. (.+)$", guard(SOURCES["week2_angles"]).read_text(encoding="utf-8"), re.M)
    labels.append(label("benchmark_batch", "week2-luna-pro-2026-10-13", "batch_verdict", "chatgpt_review_week2", week=f"week_{week_start(2).isoformat()}",
                        proxy=True, rater="Whitney's ChatGPT", author="Whitney Hodges", details={**WEEK2_VERDICT, "angle_titles": week2_titles}))
    for case in json.loads(guard(SOURCES["weeks3_4_traces"]).read_text(encoding="utf-8")):
        week = 3 if case["case"] in WEEK3_CASES else 4
        labels.append(label("benchmark_reference", case["case"], "develop", "root_cause_2026-10-16", week=f"week_{week_start(week).isoformat()}",
                            proxy=True, rater="project owner", author="project owner",
                            details={"reference_title": case["reference_title"], "status": case["reference_status"],
                                     "original_moment": case["original_moment"]}))
    for line in guard(SOURCES["export_pairs"]).read_text(encoding="utf-8").splitlines():
        if line.strip():
            pair = json.loads(line)
            labels.append(label("export_pair", pair["id"], "prefer_her_version", "chatgpt_export", week=None, proxy=True,
                                rater="Whitney Hodges", author="Whitney Hodges",
                                details={k: pair[k] for k in ("chunk", "file", "date", "channel", "ai_text", "her_text", "why")}))
    return labels


def seed(conn, labels=None) -> dict:
    """Write the labels; re-running changes nothing (label IDs are stable)."""
    from psycopg.types.json import Jsonb
    labels = labels if labels is not None else build_labels()
    written = 0
    for row in labels:
        result = conn.execute("""INSERT INTO calibration_labels(label_id,item_kind,item_id,week_id,disposition,reason_code,reframe,
            central_point_kept,rubric_ratings,rater,author,source,proxy,details) VALUES (%(label_id)s,%(item_kind)s,%(item_id)s,%(week_id)s,
            %(disposition)s,%(reason_code)s,%(reframe)s,%(central_point_kept)s,%(rubric_ratings)s,%(rater)s,%(author)s,%(source)s,%(proxy)s,%(details)s)
            ON CONFLICT (label_id) DO NOTHING""", {**row, **{k: Jsonb(row[k]) if row[k] is not None else None
                                                              for k in ("reframe", "rubric_ratings")}, "details": Jsonb(row["details"])})
        written += result.rowcount
    counts = {}
    for row in labels:
        counts[row["source"]] = counts.get(row["source"], 0) + 1
    return {"benchmark": VERSION, "labels": len(labels), "written": written, "by_source": counts, "held_out": HELD_OUT}


def ground_truth(conn, *, include_proxy: bool = False) -> list[dict]:
    """The labels that measure against WIA's judgement (section 2.3): only WIA's own, unless proxies are asked for.

    Proxies stay readable: ChatGPT's verdicts, the export pairs, the team's reference angles, and a gate decision
    recorded by someone outside WIA's reviewers (source gate_delegated, D12). The judge's calibration (E.B3), E.B5 and
    E.B6 read labels through here, so a delegated decision never counts as Whitney's."""
    return conn.execute("""SELECT * FROM calibration_labels WHERE %s OR NOT proxy ORDER BY created_at,label_id""",
                        (include_proxy,)).fetchall()


def manifest() -> dict:
    """What benchmark version 1 is made of, with hashes, recorded before any run."""
    import hashlib
    return {"version": VERSION, "weeks": {f"week{n}": week_start(n).isoformat() for n in range(1, 7)}, "held_out": HELD_OUT,
            "development_weeks": ["week1", "week2"], "golden_scenes": "pending: a person marks them (E.B12, E.B18)",
            "sources": {k: {"path": p.relative_to(PROJECT).as_posix(),
                            "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None} for k, p in SOURCES.items()}}
