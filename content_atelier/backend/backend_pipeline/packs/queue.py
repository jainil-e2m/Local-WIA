"""Starting a content pack, and retrying one (NP.B2; the content-packs plan, sections 4.1, 5.3, 5.6 and 5.8).

- **On approval.** Gate 2's approval of a v4 brief starts its pack inside the approval's own transaction
  (`start_in_transaction`, called by `gate_two.decide`), through a savepoint, as Gate 1 starts a brief: a pack that cannot
  be queued is recorded as a failed `pack_generation` run with the reason, under an id of its own, and the approval still
  commits. The approval itself authorises the start, so an approver outside the pack-editor list still gets a pack.
- **The run.** `pack_run_<intent24>` and its pack `pack_<intent24>`, keyed on the contract, the brief, its approved hash, the
  mode when it is live, the pack it supersedes and that pack's manifest (section 5.3): approving or creating twice makes one
  pack. One `pipeline_runs` row, one `content_packs` row still finishing (no body until the finalize stage writes it), and
  six jobs, one per stage, each after the one before, on the interactive queue. The run binds to the approved hash; the
  first stage adds the frozen execution contract to its inputs.
- **Create or retry** (`POST /briefs/{id}/pack`, `create`): a v1 brief keeps the v1 path (packs/workflow.py); a v2 or v3
  brief is told to re-develop as v4; a v4 brief must be consumable. When the brief's pack failed or waits, its failed and
  waiting jobs are queued again (as `POST /jobs/{id}/retry` does) and that run is the answer; a pack finishing or finished
  is answered unchanged; a change of mode (a replay run once live is switched on) starts a new run that supersedes it.
- **Lineage.** A pack made for a newer version of a brief supersedes the pack of the version before, so a week shows one
  pack per idea.
"""
from __future__ import annotations

from datetime import UTC, datetime

from ..briefs import gate_two
from ..production_common import ProductionError, receipt, save_receipt
from ..repository import identifier, insert
from ..store import canonical_hash
from . import contracts_v2 as c2
from . import model
from .runtime_v2 import mode_for

MODES = ("live", "replay", "synthetic")
PACKS_OFF = "Content packs are off"
NOT_V4 = "Re-develop this brief as a v4 brief to get a content pack"
NOT_APPROVED = "Approve this brief at Gate 2 first; approving it creates its content pack"
LIVE_OFF = "Live pack generation is switched off (ATELIER_ALLOW_GENERATION and ATELIER_ALLOW_PACK_GENERATION)"


def intent(brief_id: str, approved_hash: str, mode: str, supersedes: str | None = None,
           previous_manifest: str | None = None, pass_: dict | None = None) -> str:
    """A pass (NP-7) adds its own request to the key, so the same take or grant twice makes one run; a run without one keys
    exactly as before."""
    parts = [c2.VERSION, brief_id, approved_hash, {"mode": mode} if mode == "live" else None, supersedes, previous_manifest]
    return canonical_hash(parts + [pass_] if pass_ else parts)


def run_and_pack(digest: str) -> tuple[str, str]:
    return "pack_run_" + digest[:24], "pack_" + digest[:24]


def job_id(run_id: str, stage: str) -> str:
    return "pack_job_" + canonical_hash([run_id, stage])[:24]


def brief_refs(brief: dict) -> dict:
    return {"brief_id": brief["brief_id"], "approved_hash": brief.get("approved_hash"), "week_id": brief["week_id"],
            "angle_id": brief.get("angle_id"), "schema_version": gate_two.version_of(brief)}


def title_of(brief: dict) -> str:
    """The pack's title: the brief's approved angle title."""
    body = ((brief.get("content_body") or {}).get("document") or {}).get("body") or {}
    return (body.get("approved_angle") or {}).get("title") or brief["brief_id"]


def check_mode(settings, mode: str) -> None:
    if mode not in MODES:
        raise ValueError("Unknown pack mode; one of " + ", ".join(MODES))
    if mode == "synthetic" and not settings.synthetic:
        raise ValueError("A synthetic pack needs an isolated test database")
    if mode == "live" and not (settings.generation_enabled and settings.pack_live_enabled):
        raise PermissionError(LIVE_OFF)


def lineage_pack(conn, brief: dict) -> dict | None:
    """The current v2 pack of an earlier version of this brief (the newest earlier version that has one), which a pack of
    this version supersedes."""
    seen, parent = {brief["brief_id"]}, brief.get("supersedes_id")
    while parent and parent not in seen:
        seen.add(parent)
        found = model.current_for_brief(conn, parent)
        if found:
            return found
        row = conn.execute("SELECT supersedes_id FROM content_briefs WHERE brief_id=%s", (parent,)).fetchone()
        parent = row["supersedes_id"] if row else None
    return None


def queue_in_transaction(repo, conn, brief: dict, actor, mode: str, *, trigger: str = "manual", supersedes: str | None = None,
                         previous_manifest: str | None = None, pass_: dict | None = None) -> dict:
    """Queue a pack run in the caller's transaction and answer {pack_id, run_id, status, mode}. The same brief, approval,
    mode and predecessor answer the run already queued. Raises when the brief cannot make a pack.

    `pass_` (NP-7) is a person-started pass on the pack it supersedes: {"kind": "caption" or "refinish", ...}; its writer
    step takes the finisher's place (contracts_v2.stages_for)."""
    if pass_ and not supersedes:
        raise ValueError("A pass works on an existing pack")
    settings = repo.settings
    if not settings.packs_enabled:
        raise ValueError(PACKS_OFF)
    check_mode(settings, mode)
    brief = conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s", (brief["brief_id"],)).fetchone()
    if not brief:
        raise LookupError("Brief not found")
    if not gate_two.is_v4(brief):
        raise ValueError(NOT_V4)
    if brief["approval_status"] != "approved" or not brief["approved_hash"] or brief["approved_hash"] != brief["content_hash"]:
        raise ValueError(NOT_APPROVED)
    if conn.execute("SELECT 1 FROM content_briefs WHERE supersedes_id=%s", (brief["brief_id"],)).fetchone():
        raise ValueError("A newer version of this brief exists; approve it to get its content pack")
    run_id, pack_id = run_and_pack(intent(brief["brief_id"], brief["approved_hash"], mode, supersedes, previous_manifest, pass_))
    existing = conn.execute("SELECT status FROM pipeline_runs WHERE run_id=%s", (run_id,)).fetchone()
    if existing:
        return {"pack_id": pack_id, "run_id": run_id, "status": existing["status"], "mode": mode}
    if supersedes:
        old = conn.execute("SELECT pack_id,source_brief_id,contract_version FROM content_packs WHERE pack_id=%s FOR UPDATE",
                           (supersedes,)).fetchone()
        if not old or old["contract_version"] != c2.VERSION:
            raise ValueError("The pack to replace is not a content pack")
        old_brief = conn.execute("SELECT angle_id FROM content_briefs WHERE brief_id=%s", (old["source_brief_id"],)).fetchone()
        if not old_brief or old_brief["angle_id"] != brief["angle_id"]:
            raise ValueError("A pack replaces only a pack of the same idea")
        if model.superseded(conn, supersedes):
            raise ValueError("That pack already has a newer version")
    from ..settings_store import snapshot_refs
    from .checks import pack_identities
    # The identity records the pack's checks hold its copy to (N8), frozen with the run as a cycle's and a brief's are.
    refs = {"workflow": c2.VERSION, "brief": brief_refs(brief), "mode": mode, "synthetic": bool(settings.synthetic),
            "queued_by": str(actor), "trigger": trigger, "supersedes": supersedes, "previous_manifest": previous_manifest,
            "approval_delegated": model.delegated(settings, brief["approved_by"]), "pack_id": pack_id,
            **({"pass": pass_} if pass_ else {}), **snapshot_refs("pack", storage=settings, conn=conn),
            **pack_identities(conn, brief)}
    insert(conn, "pipeline_runs", {"run_id": run_id, "week_id": brief["week_id"], "run_scope": c2.RUN_SCOPE,
                                   "trigger_type": "manual", "triggered_by": str(actor), "input_refs": refs})
    insert(conn, "content_packs", {"pack_id": pack_id, "week_id": brief["week_id"], "title": title_of(brief),
                                   "source_brief_id": brief["brief_id"], "source_brief_hash": brief["approved_hash"],
                                   "production_run_id": run_id, "contract_version": c2.VERSION, "supersedes_id": supersedes,
                                   "updated_by": str(actor)})
    previous = None
    for stage in c2.stages_for((pass_ or {}).get("kind")):
        jid = job_id(run_id, stage)
        insert(conn, "pipeline_jobs", {"job_id": jid, "run_id": run_id, "week_id": brief["week_id"], "pack_id": pack_id,
                                       "stage": stage, "idempotency_key": f"{run_id}:{stage}", "input_hash": canonical_hash(refs),
                                       "progress_details": {"dependencies": [previous] if previous else []}})
        previous = jid
    repo.event(conn, run_id, "pack_queued", "Approved brief queued for its content pack",
               details={"pack_id": pack_id, "brief_id": brief["brief_id"], "actor": str(actor), "trigger": trigger, "mode": mode,
                        "supersedes": supersedes})
    return {"pack_id": pack_id, "run_id": run_id, "status": "queued", "mode": mode}


def record_failure(repo, conn, brief: dict, actor, mode: str | None, exc: Exception) -> dict:
    """A pack that could not start on approval: a failed run under a distinct id (the deterministic id stays free for the
    pack once the cause is fixed), with the reason; the approval stands."""
    reason = f"{type(exc).__name__}: {exc}"[:2000]
    run_id = identifier("pack_run_unqueued")
    insert(conn, "pipeline_runs", {
        "run_id": run_id, "week_id": brief["week_id"], "run_scope": c2.RUN_SCOPE, "status": "failed", "error_summary": reason,
        "current_message": "The content pack could not be started; the Gate 2 approval was saved", "trigger_type": "manual",
        "triggered_by": str(actor), "finished_at": datetime.now(UTC),
        "input_refs": {"workflow": c2.VERSION, "brief": brief_refs(brief), "mode": mode, "synthetic": bool(repo.settings.synthetic),
                       "queued_by": str(actor), "trigger": "gate_two", "queue_failure": reason}})
    repo.event(conn, run_id, "pack_queue_failed", "The content pack could not be started: " + reason,
               details={"brief_id": brief["brief_id"]}, severity="error")
    return {"pack_id": None, "run_id": run_id, "status": "failed", "mode": mode, "error": reason}


def start_in_transaction(repo, conn, brief: dict, actor) -> dict:
    """Gate 2 approved a v4 brief with packs on: start its pack (section 5.1). A savepoint keeps the approval whatever
    happens here."""
    mode = None
    try:
        mode = mode_for(repo.settings)
        with conn.transaction():  # Savepoint: a failure leaves the approval intact.
            earlier = lineage_pack(conn, brief)
            return queue_in_transaction(repo, conn, brief, actor, mode, trigger="gate_two",
                                        supersedes=earlier["pack_id"] if earlier else None,
                                        previous_manifest=earlier["manifest_hash"] if earlier else None)
    except Exception as exc:
        return record_failure(repo, conn, brief, actor, mode, exc)


def retry_run(repo, conn, run_id: str, actor) -> list[str]:
    """Queue a pack run's failed and waiting jobs again, as `POST /jobs/{id}/retry` does for one job."""
    from ..jobs.recover import RETRY_REQUESTED
    jobs = [j["job_id"] for j in conn.execute("""SELECT job_id FROM pipeline_jobs WHERE run_id=%s AND status IN ('failed','waiting')
        ORDER BY created_at,job_id FOR UPDATE""", (run_id,)).fetchall()]
    for jid in jobs:
        conn.execute("""UPDATE pipeline_jobs SET status='queued',error_summary=NULL,current_message=%s,finished_at=NULL,
            updated_at=now() WHERE job_id=%s""", (RETRY_REQUESTED, jid))
    conn.execute("UPDATE pipeline_runs SET status='queued',error_summary=NULL,updated_at=now() WHERE run_id=%s", (run_id,))
    repo.event(conn, run_id, "retry_requested", "Retry requested for the content pack", details={"job_ids": jobs, "actor": str(actor)})
    return jobs


def _blocked(row: dict) -> ProductionError:
    """Why an approved v4 brief cannot make a pack, in words (R50)."""
    if row["approval_status"] != "approved":
        return ProductionError(NOT_APPROVED, "brief_not_approved", 409)
    items = [i["title"] + (f" {i['detail']}" if i.get("detail") else "") for i in row.get("blocker_items") or [] if i["kind"] != "role"]
    return ProductionError("This brief cannot make a content pack yet: " + ("; ".join(items) or "it has unresolved review items"),
                           "brief_blocked", 409)


def _v1(repo, brief_id, payload, actor) -> dict:
    """A v1 brief keeps the v1 pack path (packs/workflow.py), which needs the brief's hash."""
    from pydantic import ValidationError
    from .contracts import Generate
    from .workflow import queue as queue_v1
    mode = payload.mode or "replay"
    try:
        generate = Generate(request_id=payload.request_id, expected_brief_hash=payload.expected_brief_hash or "", mode=mode)
    except ValidationError as exc:
        raise ProductionError("Send the brief's hash (expected_brief_hash) to make a pack from a version 1 brief",
                              "stale_brief", 409) from exc
    return {**queue_v1(repo, brief_id, generate, actor), "status": "queued", "mode": mode}


def create(repo, brief_id: str, payload, actor) -> dict:
    """POST /briefs/{id}/pack -> PackQueuedV2: create the pack of an approved v4 brief, or retry its failed or waiting run.
    An editor or approver (`edit_packs`); idempotent on the request id."""
    from .service import authorize
    authorize(repo, actor)
    if not repo.settings.packs_enabled:
        raise ProductionError("Pack production is not enabled", "packs_disabled", 503)
    with repo.connection() as conn:
        head = conn.execute("SELECT content_body FROM content_briefs WHERE brief_id=%s", (brief_id,)).fetchone()
    if not head:
        raise ProductionError("Brief not found", "not_found", 404)
    if not gate_two.is_v2(head):
        return _v1(repo, brief_id, payload, actor)
    if not gate_two.is_v4(head):
        raise ProductionError(NOT_V4, "brief_not_v4", 409)
    data = payload.model_dump(mode="json")
    operation = "pack-create:" + brief_id
    with repo.connection() as conn:
        saved = receipt(conn, payload.request_id, actor, operation, data)
        if saved is not None:
            return saved
        conn.execute("SELECT brief_id FROM content_briefs WHERE brief_id=%s FOR UPDATE", (brief_id,))
        row = gate_two._get(repo, conn, brief_id, actor)
        if payload.expected_brief_hash and payload.expected_brief_hash != row["content_hash"]:
            raise ProductionError("The brief changed; reload it", "stale_brief", 409)
        if not row["can_consume"]:
            raise _blocked(row)
        mode = payload.mode or mode_for(repo.settings)
        try:
            check_mode(repo.settings, mode)
        except PermissionError as exc:
            raise ProductionError(str(exc), "live_disabled", 403) from exc
        current = model.current_for_brief(conn, brief_id)
        supersedes = previous = None
        if current:
            state, _ = model.state_of(conn, current)
            run = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (current["production_run_id"],)).fetchone()
            ran_in = ((run or {}).get("input_refs") or {}).get("mode")
            # A run whose frozen contract changed under it (a new prompt profile, a model switch) fails the same way on every
            # retry, so it is replaced by a new run (found by NP.X1's shakedown), as a run in another mode is.
            from .runtime_v2 import CONTEXT_CHANGED
            stuck = bool(conn.execute("SELECT 1 FROM pipeline_jobs WHERE run_id=%s AND status='failed' AND error_summary LIKE %s",
                                      (current["production_run_id"], f"%{CONTEXT_CHANGED}%")).fetchone())
            if state != "waiting" or (ran_in == mode and not stuck):
                if state == "waiting":
                    retry_run(repo, conn, current["production_run_id"], actor)
                    state = "queued"
                answer = {"pack_id": current["pack_id"], "run_id": current["production_run_id"], "status": state, "mode": ran_in}
                return save_receipt(conn, payload.request_id, actor, operation, data, answer)
            # A run in another mode (a replay run once live is switched on), or one stuck on a changed contract, is replaced by
            # a new run (section 5.3).
            supersedes, previous = current["pack_id"], current["manifest_hash"]
        else:
            earlier = lineage_pack(conn, row)
            if earlier:
                supersedes, previous = earlier["pack_id"], earlier["manifest_hash"]
        try:
            answer = queue_in_transaction(repo, conn, row, actor, mode, trigger="manual", supersedes=supersedes,
                                          previous_manifest=previous)
        except (ValueError, PermissionError) as exc:
            raise ProductionError(str(exc), "pack_not_started", 409) from exc
        return save_receipt(conn, payload.request_id, actor, operation, data, answer)
