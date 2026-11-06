"""Synthetic content packs v2 for the pack service tests (NP.B2 to NP.B6): five piece envelopes built from an approved v4
brief's own copy, as the assemble stage would make them with finishing off, and a pack body. Built here so the tests never
depend on the assemble stage, and so no file holds transcript-shaped data (R48). Invented text only."""
from __future__ import annotations

import copy

from backend_pipeline.packs import checks, model
from backend_pipeline.packs import contracts_v2 as c2

NOT_WRITTEN = "the brief has no Reel of this kind and finishing was off (assemble mode)"


def piece(key: str, content: dict | None, *, origin: str = "brief", brief_key: str | None = None, brief_copy: dict | None = None,
          locks=(), findings=(), changes=(), reason: str | None = None) -> dict:
    return {"version": c2.VERSION, "key": key, "channel": c2.CHANNEL[key], "label": c2.LABELS[key],
            "origin": "not_written" if content is None else origin, "not_written_reason": reason if content is None else None,
            "brief_key": brief_key, "content": content, "brief_copy": brief_copy, "locks": list(locks),
            "findings": list(findings), "changes": list(changes)}


def _reel_copy(reel: dict) -> dict:
    return {k: copy.deepcopy(reel.get(k)) for k in ("cover_text", "on_screen_hook", "spoken_opening", "script", "screens", "caption")}


def from_brief(body: dict, *, kinds=c2.REEL_KINDS) -> dict[str, dict]:
    """The five pieces from a v4 brief body: Reels mapped by their kind (a kind the brief lacks, or one left out of `kinds`,
    is not written), the brief's copy verbatim beside the pack's extras."""
    plan = body["format_plan"]
    by_kind = {r["kind"]: (i, r) for i, r in reversed(list(enumerate(plan.get("reels") or [])))}
    out = {}
    for key in ("reel_1", "reel_2", "reel_3"):
        kind = c2.KEY_KIND[key]
        if kind in by_kind and kind in kinds:
            i, reel = by_kind[kind]
            content = {**copy.deepcopy(reel), "title": f"The {kind.replace('_', ' ')} Reel about the first reply",
                       "cover_alternates": ["The reply comes first", "What we look at first"], "cta": "none", "no_offer_ending": None}
            out[key] = piece(key, content, brief_key=f"reel_{i + 1}", brief_copy=_reel_copy(reel))
        else:
            out[key] = piece(key, None, reason=NOT_WRITTEN)
    carousel = copy.deepcopy(plan["carousel"])
    out["carousel"] = piece("carousel", {**carousel, "cta": "none", "no_offer_ending": None}, brief_key="carousel",
                            brief_copy={"title": carousel["title"], "slides": copy.deepcopy(carousel["slides"]),
                                        "caption": copy.deepcopy(carousel.get("caption"))})
    email = copy.deepcopy(plan["email"])
    out["email"] = piece("email", {**email, "cta": "reply"}, brief_key="email",
                         brief_copy={k: copy.deepcopy(email[k]) for k in ("subject_options", "preview", "opening", "body", "ending")})
    return out


def pack_body(brief_row: dict, *, run_id: str = "pack_run_synthetic", mode: str = "synthetic", client_quotes=(), **changes) -> dict:
    document = brief_row["content_body"]["document"]
    body, header = document["body"], document["header"]
    notes = [{"id": f"P{i}", "text": x["text"], "kind": x["kind"], "required": x["required"], "answer": x.get("answer"),
              "client_permission": x["kind"] == "permission", "done": None} for i, x in enumerate(body["before_publishing"], 1)]
    value = {"version": c2.VERSION, "title": body["approved_angle"]["title"], "brief_id": brief_row["brief_id"],
             "week_id": brief_row["week_id"], "angle_id": brief_row["angle_id"], "pillar": header["purpose"], "rank": 1,
             "message_spine": body.get("central_point"), "cta": header["cta"], "before_publishing": notes,
             "client_quotes": list(client_quotes), "stronger_with_permission": [], "pack_notes": [], "change_notes": [],
             "fidelity": {"statements": 0, "flagged": 0},
             "change": {"kind": "generated", "by": "content-pack step", "at": model.now_iso(), "delegated": False, "pieces": [],
                        "paths": [], "note": None},
             "provenance": {"brief_id": brief_row["brief_id"], "approved_hash": brief_row.get("approved_hash") or brief_row["content_hash"],
                            "brief_schema": "brief_document_v4", "handoff_version": c2.HANDOFF_VERSION, "run_id": run_id, "mode": mode,
                            "finish_mode": "assemble", "profiles": {}, "models": {}, "knowledge_base_version": None,
                            "approved_by": brief_row.get("approved_by"), "approval_delegated": False}}
    value.update(changes)
    return value


def fidelity(finding_id: str, path: str, sentence: str, *, verdict: str = "unsupported", why: str = "the call does not say so") -> dict:
    return {"finding_id": finding_id, "kind": "fidelity", "verdict": verdict, "path": path, "sentence": sentence, "why": why,
            "severity": "blocking", "status": "open", "resolution": None}


def finish(repo, pack_id: str, *, bodies: dict | None = None, kinds=c2.REEL_KINDS, edit=None, **body_changes) -> dict:
    """Stand in for the main session's stages: write the queued pack's first version (`write_version`, reuse_row) from the
    brief's copy, store the checks, and close the run's jobs, as finalize does."""
    with repo.connection() as conn:
        pack = model.get(conn, pack_id, lock=True)
        brief = conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s", (pack["source_brief_id"],)).fetchone()
        bodies = bodies or from_brief(brief["content_body"]["document"]["body"], kinds=kinds)
        if edit:
            edit(bodies)
        body = pack_body(brief, run_id=pack["production_run_id"], **body_changes)
        run = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (pack["production_run_id"],)).fetchone()
        body["provenance"]["approval_delegated"] = bool(run["input_refs"].get("approval_delegated"))
        found = checks.findings(conn, {**pack, "content_body": body}, bodies, brief)
        written = model.write_version(repo, conn, parent=None, pack_id=pack_id, run_id=pack["production_run_id"], brief=brief, body=body,
                                      piece_bodies=bodies, actor="content-pack step", validation=checks.result(found), reuse_row=True)
        conn.execute("UPDATE pipeline_jobs SET status='completed',finished_at=now(),updated_at=now() WHERE run_id=%s",
                     (pack["production_run_id"],))
        conn.execute("UPDATE pipeline_runs SET status='completed',finished_at=now(),updated_at=now() WHERE run_id=%s",
                     (pack["production_run_id"],))
    return written
