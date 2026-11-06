"""Benchmark version 2's packets (E.B27): whole weeks from the moments ledger, built with no model call.

Benchmark v1's packets (`research/quality-experiments-2026-10-18/sources/week*.json`) are five hand-picked excerpts a week,
so its results measure the strategist's writing on a person's pre-selection, not its judgement over a week. A v2 packet is
what the live path's strategist reads (`sql_pipeline`, the window's verified ledger scenes of whole calls): every verified,
current scene of every included call of the window, in the strategist's packet shape, human lines and counter-expected
decisions first (scene profile v3, E.B31), and a scene whose client asked not to be used (consent `do_not_use`) left out
and counted. Each packet reports its scene coverage: every call of the window (included or not, with the reason), its
scenes (current, verified, unverified, held for consent, in the packet) and the packet's size against a budget. A packet
over its budget is reported, never truncated. A call that is not yet scene-extracted makes the packet `pending`: the
October window waits for the paid extraction of the calls imported by 6.B18.

- `week1`: benchmark Week 1 (the admitted week of 1 June 2026), with Whitney's Week 1 rewrites as its reference
  (`reference`, read by the reports, never by a prompt).
- `week2`: the whole of benchmark Week 2 (the admitted week of 8 June 2026, eleven recordings), with the gate's target
  ideas and the ideas WIA rejected as its reference (hand-built, labelled as such, R58).
- `october`: the held-out October window (by date, `--from`/`--to`), no reference; no prompt has seen it.

Packets carry call text, so they are written under `research/benchmark-v2/packets/` (R48). Benchmark v1 stays for replay;
`python -m evaluation run --weeks week2_v2` reads a v2 packet (evaluation/run.py).
"""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from backend_pipeline.angle_profiles import STRATEGIST_V7_PROFILE, order_packet, strategist_user
from backend_pipeline.store import canonical_hash

from .benchmark import RESEARCH, SOURCES, guard, week_start, whitney_alternatives

VERSION = "benchmark-v2.2026-10-23"
OUT = RESEARCH / "benchmark-v2" / "packets"
# The strategist's input room this report checks a packet against: the scenes as strategist v7's user message renders them
# (about four characters a token) plus the knowledge-base prefix's budget (`context.budget.prefix_tokens`). A packet over
# it is reported, never cut (`--budget-tokens`); the provider route's own preflight (token_budget) still runs before a call.
BUDGET_TOKENS = 150_000
PREFIX_TOKENS = 30_000
WEEKS = {"week1": 1, "week2": 2}
# The gate's Week 2 ideas (plan section 5, M3) and the ideas WIA rejected: the reference a report scores against. Never a
# prompt input (D28): the run harness reads `scenes` only.
WEEK2_REFERENCE = {
    "made_by": "hand-built (the v2 packs of 20 October and WIA's review); a reference, never system output (R58)",
    "target_ideas": ["How we approach a new client's ad budget, and why 'spend more' isn't our first move",
                     "What our strategy calls actually cover, and why the most useful part often isn't about the ads",
                     "How we help wedding pros understand their own ad accounts, now that AI can change them in minutes"],
    "rejected_ideas": ["A platform lesson such as 'Meta takes your instructions literally'", "The office-hours walkthrough"],
}


def _documents(conn, *, week_id: str | None, start: date | None, end: date | None) -> list[dict]:
    if week_id:
        where, args = "week_id=%s", (week_id,)
    else:
        lo = datetime.combine(start, time.min, timezone.utc)
        hi = datetime.combine(end + timedelta(days=1), time.min, timezone.utc)
        where, args = "occurred_at >= %s AND occurred_at < %s", (lo, hi)
    return conn.execute(f"""SELECT transcript_id,title,call_type,included,exclusion_reason,extraction_status,occurred_at,
            original_text,passage_map,week_id FROM transcripts WHERE {where} AND canonical_document_id IS NULL
        ORDER BY occurred_at NULLS LAST, transcript_id""", args).fetchall()


def _evidence(doc: dict, refs: list[dict]) -> list[dict]:
    passages = {p["passage_id"]: p for p in doc["passage_map"] or []}
    out = []
    for ref in refs:
        if "context" not in (ref.get("roles") or []) or ref.get("transcript_id") != doc["transcript_id"]:
            continue
        p = passages.get(ref["passage_id"])
        text = doc["original_text"][ref["start"]:ref["end"]] if p is None else doc["original_text"][p["start"]:p["end"]]
        out.append({"span_id": ref["passage_id"], "text": text, "speaker": (p or {}).get("speaker"),
                    "start_seconds": round((p or {}).get("start_ms", 0) / 1000) if p else None})
    return out


def build(conn, name: str, *, start: date | None = None, end: date | None = None, budget_tokens: int = BUDGET_TOKENS) -> dict:
    """One packet and its coverage, from the ledger as it stands. Reads only."""
    if name in WEEKS:
        week_id = f"week_{week_start(WEEKS[name]).isoformat()}"
        window = {"week_id": week_id, "from": week_start(WEEKS[name]).isoformat(),
                  "to": (week_start(WEEKS[name]) + timedelta(days=6)).isoformat()}
        docs = _documents(conn, week_id=week_id, start=None, end=None)
    else:
        if not (start and end):
            raise ValueError("A dated window needs --from and --to")
        window = {"from": start.isoformat(), "to": end.isoformat()}
        docs = _documents(conn, week_id=None, start=start, end=end)
    scenes, coverage = [], []
    for doc in docs:
        rows = conn.execute("""SELECT moment_id,moment_type,moment_body,evidence_refs,quote_verified,consent_status,
                extractor_version FROM key_moments WHERE document_id=%s AND is_current ORDER BY moment_id""",
                            (doc["transcript_id"],)).fetchall() if doc["included"] else []
        verified = [r for r in rows if r["quote_verified"]]
        held = [r for r in verified if r["consent_status"] == "do_not_use"]
        mine = []
        for r in verified:
            if r["consent_status"] == "do_not_use":
                continue
            body = dict(r["moment_body"])
            if r["consent_status"] == "internal_only":
                body["sensitivity"] = "internal_only"
            mine.append({**body, "moment_id": r["moment_id"], "moment_type": r["moment_type"] or body.get("moment_type"),
                         "source_ids": [doc["transcript_id"]], "source_metadata": {}, "consent": r["consent_status"],
                         "extractor_version": r["extractor_version"], "speaker_identity_status": "unverified_labels",
                         "source_evidence": _evidence(doc, r["evidence_refs"])})
        mine.sort(key=lambda m: min((e["start_seconds"] or 0 for e in m["source_evidence"]), default=0))
        scenes += mine
        state = ("excluded" if not doc["included"] else "extracted" if doc["extraction_status"] == "completed"
                 else "pending_extraction")
        coverage.append({"transcript_id": doc["transcript_id"], "title": doc["title"], "call_type": doc["call_type"],
                         "occurred_at": doc["occurred_at"].isoformat() if doc["occurred_at"] else None, "included": doc["included"],
                         "exclusion_reason": doc["exclusion_reason"], "state": state, "scenes": len(rows),
                         "verified": len(verified), "unverified": len(rows) - len(verified), "held_for_consent": len(held),
                         "in_packet": len(mine),
                         "extractor_versions": sorted({r["extractor_version"] for r in rows if r["extractor_version"]})})
    scenes = order_packet(scenes)
    tokens = (len(strategist_user(scenes, STRATEGIST_V7_PROFILE, [], None)) + 3) // 4 + PREFIX_TOKENS
    pending = [c["transcript_id"] for c in coverage if c["state"] == "pending_extraction"]
    included = [c for c in coverage if c["included"]]
    summary = {"calls": len(coverage), "included_calls": len(included), "excluded_calls": len(coverage) - len(included),
               "verified_scenes": sum(c["verified"] for c in included), "in_packet": len(scenes),
               "held_for_consent": sum(c["held_for_consent"] for c in included),
               "first_scene_types": sum(m.get("moment_type") in ("human_line", "counter_expected_decision") for m in scenes),
               "tokens": tokens, "budget_tokens": budget_tokens, "within_budget": tokens <= budget_tokens,
               "pending_extraction": pending,
               "every_verified_scene_in_packet": sum(c["verified"] - c["held_for_consent"] for c in included) == len(scenes)}
    state = "pending" if pending or not included else "complete" if summary["within_budget"] else "over_budget"
    packet = {"benchmark": VERSION, "name": name, "window": window, "made_by": "system: ledger packet, no model call",
              "state": state, "coverage": {"summary": summary, "documents": coverage}, "scenes": scenes}
    if name == "week1":
        packet["reference"] = {"made_by": "Whitney's own rewrites of the Week 1 batch (13 October review)",
                               "rewrites": whitney_alternatives(guard(SOURCES["week1_alternatives"]).read_text(encoding="utf-8"))}
    elif name == "week2":
        packet["reference"] = WEEK2_REFERENCE
    packet["packet_hash"] = canonical_hash(packet["scenes"])
    return packet


def write(packet: dict, out: Path = OUT) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{packet['name']}.json"
    path.write_text(json.dumps(packet, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    return path


def load(name: str, out: Path = OUT) -> dict:
    """A written packet; `run.packet` reads its scenes."""
    path = out / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Benchmark v2 packet {name} is not built: python -m evaluation packets --name {name}")
    return json.loads(path.read_text(encoding="utf-8"))
