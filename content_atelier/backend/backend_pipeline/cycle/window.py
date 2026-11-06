"""A cycle over a date window, from the app (plan 3.B2/3.B3, go-live subset; O25).

The approver names a window; `preview` lists what the cycle would read before anything is queued or paid for: the window's
included, normalised documents (`documents.select`), the calls that arrived after their own window's cycle ran (O25: listed
for the next window, and read by it), the undated documents a person must date or add by hand, the cycles already run over
the window, and the cost estimate with this week's standing budgets (6.B3). `start` queues exactly that selection on the
existing weekly runner (`two_call_v1`: the scene ledger's verified scenes of the whole calls, `sql_pipeline.document_scenes`),
refusing when the selection changed since the preview the approver saw. The run records every document it selected and why
(the window, a late arrival, an undated document a person added), the estimate it was started on, and, once the strategist
has run, the scenes it saw (`scene_coverage`): every verified scene of every selected call reaches the strategist unless its
client asked not to be used, and a week over the context budget is refused before sending, never truncated (stage.py).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ..angle_workflow import LEGACY
from ..store import canonical_hash

NOT_READ = ("failed", "cancelled")  # statuses of a cycle run that did not read its documents
# Assumptions of the estimate, said with it. The strategist's output is reasoning plus cards; verification is one call a card.
STRATEGIST_OUTPUT_TOKENS = 16000
CARDS_ASSUMED = 8
VERIFICATION_INPUT_TOKENS, VERIFICATION_OUTPUT_TOKENS = 12000, 1500
CHARACTERS_PER_TOKEN = 4
# A scene as the strategist reads it, record and spanned turns, when the ledger holds none yet: 4,330 on the October window.
CHARACTERS_PER_SCENE = 4300
SCENES_PER_NEW_DOCUMENT = 14  # 1,669 scenes from 91 documents on 20 October (2.B11): about 18; a shorter week's calls fewer


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("A window needs explicit time zones")
    return value.astimezone(UTC)


def cycle_runs(conn) -> list[dict]:
    """Weekly runs started from a selection of documents (a window or a set), newest first."""
    return conn.execute("""SELECT r.run_id,r.week_id,r.status,r.current_message,r.error_summary,r.created_at,r.triggered_by,
        r.input_refs,w.week_start,w.week_end FROM pipeline_runs r JOIN weeks w USING (week_id)
        WHERE r.run_scope='weekly_angles' AND r.input_refs ? 'selected_by' ORDER BY r.created_at DESC""").fetchall()


def run_window(run: dict) -> tuple[datetime, datetime] | None:
    """The window a cycle run read: recorded on the run (from 3.B2), or, for an earlier window run, its container week."""
    window = (run["input_refs"] or {}).get("window")
    if window:
        return datetime.fromisoformat(window["start"]), datetime.fromisoformat(window["end"])
    if (run["input_refs"] or {}).get("selected_by") == "window" and run.get("week_start"):
        start = datetime(run["week_start"].year, run["week_start"].month, run["week_start"].day, tzinfo=UTC)
        return start, start + timedelta(days=7)
    return None


def _read_by_cycles(runs) -> set[str]:
    return {t["id"] for r in runs if r["status"] not in NOT_READ for t in (r["input_refs"] or {}).get("transcripts", [])}


def late_arrivals(conn, window_start: datetime, runs=None) -> list[dict]:
    """O25: included documents dated before this window that no cycle read, because they arrived (were ingested) after the
    cycle of the window they belong to had started. The next window lists and reads them."""
    from ..documents.select import SELECTABLE
    runs = cycle_runs(conn) if runs is None else runs
    read = _read_by_cycles(runs)
    windows = [(w, r["created_at"]) for r in runs if r["status"] not in NOT_READ and (w := run_window(r))]
    out = []
    for doc in conn.execute(f"""SELECT * FROM transcripts WHERE {SELECTABLE} AND occurred_at IS NOT NULL AND occurred_at < %s
            ORDER BY occurred_at,transcript_id""", (window_start,)):
        if doc["transcript_id"] in read:
            continue
        arrived = doc["ingested_at"]
        missed = [(w, at) for w, at in windows if w[0] <= doc["occurred_at"] < w[1] and arrived and at < arrived]
        if missed:
            doc["missed_window"] = {"start": missed[0][0][0].isoformat(), "end": missed[0][0][1].isoformat()}
            out.append(doc)
    return out


def undated(conn, runs=None) -> list[dict]:
    """Included documents with no date, which no window can reach: listed for a person, who dates them or adds them by hand."""
    from ..documents.select import SELECTABLE
    read = _read_by_cycles(cycle_runs(conn) if runs is None else runs)
    return [d for d in conn.execute(f"SELECT * FROM transcripts WHERE {SELECTABLE} AND occurred_at IS NULL ORDER BY ingested_at,transcript_id")
            if d["transcript_id"] not in read]


def _document(d: dict, reason: str) -> dict:
    return {"transcript_id": d["transcript_id"], "title": d["title"], "occurred_at": d["occurred_at"], "call_type": d.get("call_type"),
            "source_type": d.get("source_type"), "extraction_status": d.get("extraction_status"), "ingested_at": d.get("ingested_at"),
            "selected_because": reason, **({"missed_window": d["missed_window"]} if d.get("missed_window") else {})}


def selection_hash(window_start, window_end, documents) -> str:
    return canonical_hash({"window": [window_start.isoformat(), window_end.isoformat()],
                           "documents": sorted([d["transcript_id"], d["content_hash"]] for d in documents)})


# ---- the estimate --------------------------------------------------------------------------------------------------------

def estimate(repo, models, documents: list[dict]) -> dict:
    """What the cycle would cost before anything is sent; no model is called. Scene extraction for the documents the ledger
    does not hold yet (the extraction estimate of `moments extract --estimate`), the strategist's one call over every verified
    scene (the ledger's for the documents it holds, an assumed count for the rest) and card verification when a model is set.
    Prices are the table's in costs.py; hosted usage is authoritative."""
    from .. import costs
    from ..knowledge.assembly import stable_refs
    from ..moments import queue as extraction
    from ..moments.jobs import already_extracted
    from ..moments.scenes import SCENE_V2_PROFILE
    from ..settings_store import DOCUMENT_EXTRACTION_PROFILES, value
    # The scene profile the cycle will extract under (E.B31: v3 when it is selected), else the ledger's v2.
    scene_profile = (models.extraction_profile if getattr(models, "extraction_profile", None) in DOCUMENT_EXTRACTION_PROFILES
                        else SCENE_V2_PROFILE)
    ids = [d["transcript_id"] for d in documents]
    components, notes = [], []
    try:
        kb, kb_refs = extraction.knowledge_base(repo, models, "cached")
        kb_refs = stable_refs(kb.refs())
    except Exception as error:  # a missing knowledge base is said, not hidden: the run itself refuses it before paying
        kb_refs = None
        notes.append(f"The extraction knowledge base could not be assembled ({type(error).__name__}: {error}); every document "
                     "is counted as new")
    with repo.connection() as conn:
        todo = [d for d in documents if kb_refs is None or already_extracted(
            conn, d["transcript_id"], extraction.extraction_key(d, scene_profile, kb_refs), "") is None]
        # The strategist reads each scene with the call turns it spans (`source_evidence`), not its record alone: N2's
        # October cycle sent 188,604 input tokens against 78,000 estimated from the records (USD 0.61 against 0.32).
        held = conn.execute("""SELECT count(*) AS n,COALESCE(sum(length(moment_body::text)+(SELECT COALESCE(sum((r->>'end')::int
                -(r->>'start')::int),0) FROM jsonb_array_elements(COALESCE(evidence_refs,'[]'::jsonb)) r)),0) AS chars
            FROM key_moments WHERE document_id=ANY(%s) AND is_current AND quote_verified AND extractor_version=%s""",
                            (ids, scene_profile)).fetchone()
        prefix = value("context.budget.prefix_tokens", conn)
    if todo:
        try:
            ext = extraction.estimate(repo, models, todo, profile=scene_profile, mode="cached")
            components.append({"stage": "scene extraction", "model": ext["model"], "calls": len(todo),
                               "input_tokens": ext["input_tokens_estimate"], "output_tokens": ext["output_tokens_assumed"],
                               "usd": ext["estimated_cost_usd"]})
        except Exception as error:
            notes.append(f"Scene extraction for {len(todo)} new documents could not be estimated ({type(error).__name__}: {error})")
    per_scene = (held["chars"] / held["n"]) if held["n"] else CHARACTERS_PER_SCENE
    scenes = held["n"] + len(todo) * SCENES_PER_NEW_DOCUMENT
    strategist_model = models.model_for("angle_generation")
    strategist_in = int(prefix + scenes * per_scene / CHARACTERS_PER_TOKEN)
    components.append({"stage": "strategist", "model": strategist_model, "calls": 1, "input_tokens": strategist_in,
                       "output_tokens": STRATEGIST_OUTPUT_TOKENS,
                       "usd": costs.estimate_usd(strategist_model, strategist_in, STRATEGIST_OUTPUT_TOKENS)})
    verifier = getattr(models, "openrouter_verification_model", None)
    if verifier:
        components.append({"stage": "card verification", "model": verifier, "calls": CARDS_ASSUMED,
                           "input_tokens": CARDS_ASSUMED * VERIFICATION_INPUT_TOKENS, "output_tokens": CARDS_ASSUMED * VERIFICATION_OUTPUT_TOKENS,
                           "usd": costs.estimate_usd(verifier, CARDS_ASSUMED * VERIFICATION_INPUT_TOKENS, CARDS_ASSUMED * VERIFICATION_OUTPUT_TOKENS)})
    unknown = [c["stage"] for c in components if c["usd"] is None]
    if unknown:
        notes.append("No price is known for " + ", ".join(unknown) + " (costs.py); the total leaves them out")
    return {"total_usd": round(sum(c["usd"] or 0 for c in components), 4), "components": components,
            "documents_to_extract": len(todo), "scenes_in_ledger": held["n"], "scenes_assumed_for_new_documents": len(todo) * SCENES_PER_NEW_DOCUMENT,
            "provider_calls_made": 0, "notes": notes,
            "assumptions": f"{STRATEGIST_OUTPUT_TOKENS} strategist output tokens; {CARDS_ASSUMED} cards verified; "
                           f"{SCENES_PER_NEW_DOCUMENT} scenes for each document not yet extracted; about {CHARACTERS_PER_TOKEN} characters a token",
            "note": "An estimate, not a charge: hosted usage is authoritative, and reasoning tokens are part of the output."}


# ---- preview and start ---------------------------------------------------------------------------------------------------

def preview(repo, models, window_start: datetime, window_end: datetime | None = None) -> dict:
    """What a cycle over this window would read and cost; nothing is queued."""
    from ..documents.select import by_window
    from ..llm import standing
    window_start = _aware(window_start)
    window_end = _aware(window_end) if window_end else window_start + timedelta(days=7)
    if window_end <= window_start:
        raise ValueError("A window ends after it starts")
    with repo.connection() as conn:
        runs = cycle_runs(conn)
        documents = by_window(conn, window_start, window_end)
        late = late_arrivals(conn, window_start, runs)
        waiting = undated(conn, runs)
        earlier = [{"run_id": r["run_id"], "status": r["status"], "created_at": r["created_at"], "week_id": r["week_id"],
                    "window": {"start": w[0].isoformat(), "end": w[1].isoformat()}}
                   for r in runs if (w := run_window(r)) and w[0] < window_end and window_start < w[1]]
        budgets = {b["purpose"]: b for b in standing.status(conn)["budgets"] if b["purpose"] in ("cycle", "extraction")}
    selected = documents + late
    cost = estimate(repo, models, selected) if selected else None
    left = sum(b["left_usd"] for b in budgets.values() if b["cap_usd"] is not None)
    # With no weekly caps (budgets.uncapped) nothing is "left" to compare against: every estimate fits.
    uncapped = any(b.get("uncapped") for b in budgets.values())
    brief = brief_preview(repo, models)
    return {"window": {"start": window_start.isoformat(), "end": window_end.isoformat()},
            "document_count": len(selected), "documents": [_document(d, "window") for d in documents],
            "late_arrivals": [_document(d, "late_arrival") for d in late], "undated": [_document(d, "undated") for d in waiting],
            "earlier_cycles": earlier, "estimate": cost, "budgets": list(budgets.values()),
            "within_budget": uncapped or cost is None or cost["total_usd"] <= left,
            "selection_hash": selection_hash(window_start, window_end, selected), "strategy_brief": brief}


def brief_preview(repo, models) -> dict | None:
    """The strategy brief a cycle started now would be given (E.B28), for the preview; None for a profile without cards. The
    brief the run is given is assembled again, and frozen, when it is submitted."""
    from datetime import date

    from ..angle_profiles import uses_cards
    from .strategy_brief import assemble_for
    if not uses_cards(getattr(models, "angle_prompt_profile", "")):
        return None
    try:
        return assemble_for(models, repo.connection, date.today(), "cached")
    except Exception as error:  # the preview never fails on the brief; the submit assembles it again and refuses there
        return {"error": f"{type(error).__name__}: {error}"}


def start(repo, models, actor, window_start: datetime, window_end: datetime | None, *, mode: str = "live",
          expected_selection: str, include_undated: list[str] | tuple = ()) -> dict:
    """Queue the cycle the approver previewed. A selection that changed since the preview (a call imported, re-dated or
    excluded) is refused with the counts, so the approver previews again; nothing is ever silently added or dropped."""
    from ..documents.select import by_set, container_week
    from ..gate_one import require
    from ..repository import insert
    require(repo, actor, "decide")
    if mode not in ("live", "replay", "synthetic"):
        raise ValueError("mode must be live, replay or synthetic")
    shown = preview(repo, models, window_start, window_end)
    if shown["selection_hash"] != expected_selection:
        raise ValueError(f"The selection changed since the preview: it now has {shown['document_count']} documents. Preview the "
                         "window again before starting the cycle")
    if not shown["document_count"] and not include_undated:
        raise ValueError("No included, normalised documents fall in that window")
    undated_ids = {d["transcript_id"] for d in shown["undated"]}
    if stray := [i for i in include_undated if i not in undated_ids]:
        raise ValueError(f"Only the listed undated documents can be added by hand: {', '.join(stray)}")
    start_at = datetime.fromisoformat(shown["window"]["start"])
    with repo.connection() as conn:
        ids = [d["transcript_id"] for d in shown["documents"] + shown["late_arrivals"]]
        documents = by_set(conn, ids) if ids else []
        added = by_set(conn, list(include_undated)) if include_undated else []
        week_id, first = container_week(documents + added, start_at)
        insert(conn, "weeks", {"week_id": week_id, "week_start": first, "week_end": first + timedelta(days=6)}, conflict=True)
    reasons = {d["transcript_id"]: d["selected_because"] for d in shown["documents"] + shown["late_arrivals"]}
    reasons.update({i: "added_by_person" for i in include_undated})
    extra = {"window": shown["window"], "selected_because": reasons, "cycle_estimate": shown["estimate"],
             "started_from": "app", "selection_hash": shown["selection_hash"]}
    result = repo.submit(week_id, mode, actor=actor, models=models, documents=documents + added, selected_by="window",
                         workflow=LEGACY, extra_refs=extra)
    return {**result, "week_id": week_id, "documents": [d["transcript_id"] for d in documents + added],
            "late_arrivals": [d["transcript_id"] for d in shown["late_arrivals"]], "estimate": shown["estimate"]}


# ---- what a cycle read -----------------------------------------------------------------------------------------------------

def scene_coverage(conn, run: dict, *, sent=None, dropped=None) -> dict:
    """The scenes the strategist saw, document by document: every verified scene of each selected call, the ones sent, the
    ones held back for consent (do_not_use), and any other verified scene not sent, which should never happen."""
    refs = run["input_refs"] or {}
    doc_ids = [t["id"] for t in refs.get("transcripts", [])]
    jobs = {j["stage"]: j for j in conn.execute("SELECT stage,status,result_refs FROM pipeline_jobs WHERE run_id=%s", (run["run_id"],))}
    extraction = jobs.get("moment_extraction")
    if not extraction or extraction["status"] != "completed":
        return {"state": "not_extracted", "documents": [{"transcript_id": i, "verified": 0, "sent": 0, "held_for_consent": 0,
                                                          "not_sent": []} for i in doc_ids]}
    verified = list(extraction["result_refs"].get("moment_ids") or [])
    unverified = list(extraction["result_refs"].get("unverified_ids") or [])
    if sent is None:
        generation = jobs.get("angle_generation")
        if generation and generation["status"] == "completed":
            sent = generation["result_refs"].get("moment_ids") or []
            dropped = generation["result_refs"].get("consent_dropped") or []
    owner = {r["moment_id"]: r["document_id"] for r in conn.execute(
        "SELECT moment_id,document_id FROM key_moments WHERE moment_id=ANY(%s)", (verified + unverified,))}
    held = {d["moment_id"] if isinstance(d, dict) else d for d in (dropped or [])}
    documents = []
    for doc in doc_ids:
        mine = [m for m in verified if owner.get(m) == doc]
        row = {"transcript_id": doc, "verified": len(mine), "unverified": sum(owner.get(m) == doc for m in unverified)}
        if sent is not None:
            row.update(sent=sum(m in set(sent) for m in mine), held_for_consent=sum(m in held for m in mine),
                       not_sent=[m for m in mine if m not in set(sent) and m not in held])
        documents.append(row)
    if sent is None:
        return {"state": "extracted", "verified": len(verified), "documents": documents}
    missing = [m for d in documents for m in d["not_sent"]]
    return {"state": "complete" if not missing else "incomplete", "verified": len(verified), "sent": len(sent),
            "held_for_consent": len(held), "not_sent": missing, "documents": documents}


def _summary(conn, run) -> dict:
    window = run_window(run)
    refs = run["input_refs"] or {}
    coverage = scene_coverage(conn, run)
    return {"run_id": run["run_id"], "week_id": run["week_id"], "status": run["status"], "message": run["current_message"],
            "error_summary": run["error_summary"], "created_at": run["created_at"], "started_by": run["triggered_by"],
            "mode": refs.get("mode"), "selected_by": refs.get("selected_by"),
            "window": {"start": window[0].isoformat(), "end": window[1].isoformat()} if window else None,
            "document_count": len(refs.get("transcripts", [])), "estimate_usd": (refs.get("cycle_estimate") or {}).get("total_usd"),
            "coverage_state": coverage["state"], "scenes_sent": coverage.get("sent"), "scenes_verified": coverage.get("verified"),
            # The window's strategy brief frozen with the cycle (E.B28); the detail carries the brief itself.
            "strategy_brief_hash": refs.get("strategy_brief_hash")}


def listing(repo, limit: int = 20) -> list[dict]:
    with repo.connection() as conn:
        return [_summary(conn, r) for r in cycle_runs(conn)[:limit]]


def detail(repo, run_id: str) -> dict:
    """One cycle: its documents and why each was selected, the estimate it started on, its stages (a stage waiting for a
    spent budget says so), and the scenes the strategist saw."""
    with repo.connection() as conn:
        run = next((r for r in cycle_runs(conn) if r["run_id"] == run_id), None)
        if run is None:
            raise LookupError("No cycle run with that id")
        refs = run["input_refs"] or {}
        ids = [t["id"] for t in refs.get("transcripts", [])]
        rows = {d["transcript_id"]: d for d in conn.execute("SELECT * FROM transcripts WHERE transcript_id=ANY(%s)", (ids,))}
        because = refs.get("selected_because") or {}
        coverage = scene_coverage(conn, run)
        jobs = conn.execute("""SELECT job_id,stage,status,current_message,error_summary,progress_details FROM pipeline_jobs
            WHERE run_id=%s ORDER BY created_at,job_id""", (run_id,)).fetchall()
        summary = _summary(conn, run)
    waiting = next(((j["progress_details"] or {}).get("budget_reason") for j in jobs if j["status"] == "waiting"
                    and (j["progress_details"] or {}).get("waiting_for") == "budget"), None)
    return {**summary, "estimate": refs.get("cycle_estimate"), "waiting_reason": waiting, "strategy_brief": refs.get("strategy_brief"),
            "documents": [_document(rows[i], because.get(i, refs.get("selected_by") or "window")) for i in ids if i in rows],
            "scene_coverage": coverage,
            "stages": [{k: j[k] for k in ("job_id", "stage", "status", "current_message", "error_summary")} for j in jobs]}
