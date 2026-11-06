"""The content pack v2 run, stage by stage (Phase NP; the content-packs plan, section 5.1).

    pack_assemble  hand-off v2 -> five pieces in the v4 leaf shape, Reels by kind, locks translated   (no model)
    pack_finish    Opus 5.5 edits to the house style and writes a missing Reel kind; locks put back
    pack_check     Sonnet 5.5 lists statements: supported, unsupported or guardrail (locked and personal lines skipped)
    pack_repair    Opus 5.5 patches the flagged sentences only (only when something is flagged); locks put back
    pack_recheck   Sonnet 5.5 on the changed statements only (only when something was repaired)
    pack_finalize  surviving flags settled (put back, or an open finding on a written Reel); checks; the version (no model)

A person-started pass (NP-7, packs/passes.py) is a run whose second step is its own writer step: `pack_caption` (the
post-recording pass) or `pack_refinish` (finishing again with a permission), in `pack_finish`'s place.

Each stage saves its output as an artifact (`pack-runs/<run>/<stage>/<hash>.json`) and the next reads it, checked by hash,
so a stage retried after a crash resumes from the last saved output. The first stage freezes the run's execution contract
(runtime_v2.execution_contract) into its inputs; a later stage fails when it changed.
"""
from __future__ import annotations

from psycopg.types.json import Jsonb

from ..artifacts import store_for
from ..store import canonical_hash
from . import assemble, contracts_v2 as c2, fidelity, finalize, finish, model, passes, runtime_v2

PRIOR = dict(zip(c2.STAGES[1:], c2.STAGES[:-1]))
WRITERS = ("pack_finish", *c2.LATER_STAGES)


def prior_of(run, stage: str) -> str:
    """The step before this one in this run (a pass's writer step stands in the finisher's place)."""
    order = c2.stages_for(((run["input_refs"].get("pass")) or {}).get("kind"))
    return order[order.index(stage) - 1]


def run_of(worker, job) -> dict:
    with worker.repo.connection() as conn:
        return conn.execute("SELECT * FROM pipeline_runs WHERE run_id=%s", (job["run_id"],)).fetchone()


def save(worker, job, run, value: dict, message: str) -> None:
    store = store_for(worker.storage)
    digest = canonical_hash(value)
    path = f"pack-runs/{run['run_id']}/{job['stage']}/{digest}.json"
    store.write_json(path, value)
    with worker.repo.connection() as conn:
        worker.repo.finish(conn, job, {"artifact": path, "hash": digest}, message=message)


def output(worker, run, stage: str) -> dict:
    with worker.repo.connection() as conn:
        row = conn.execute("SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage=%s AND status='completed'",
                           (run["run_id"], stage)).fetchone()
    if not row:
        raise ValueError(f"The pack's earlier step {stage} has not finished")
    value = store_for(worker.storage).read_json(row["result_refs"]["artifact"])
    if canonical_hash(value) != row["result_refs"]["hash"]:
        raise ValueError(f"The saved output of {stage} changed after it was saved")
    return value


def progress(worker, job, message: str) -> None:
    with worker.repo.connection() as conn:
        worker.repo.guard(conn, job)
        conn.execute("UPDATE pipeline_jobs SET current_message=%s,updated_at=now() WHERE job_id=%s", (message, job["job_id"]))


def freeze(worker, job, run) -> dict:
    """The first stage writes the execution contract into the run's inputs; later stages are checked against it."""
    refs = run["input_refs"]
    if refs.get("execution_contract") is None:
        contract = runtime_v2.execution_contract(worker, run)
        with worker.repo.connection() as conn:
            worker.repo.guard(conn, job)
            refs["execution_contract"] = contract
            if isinstance(refs.get("settings_snapshot"), dict) and (contract.get("knowledge_base") or {}).get("version"):
                refs["settings_snapshot"]["knowledge_base_version"] = contract["knowledge_base"]["version"]
            conn.execute("UPDATE pipeline_runs SET input_refs=%s,updated_at=now() WHERE run_id=%s", (Jsonb(refs), run["run_id"]))
    return run


def previous_pack(worker, pack_id: str | None, brief_id: str | None = None) -> dict | None:
    if not pack_id:
        return None
    with worker.repo.connection() as conn:
        row = model.get(conn, pack_id)
        rows = model.pieces(conn, pack_id)
    if row.get("content_body") is None:
        return None  # it never finished (a replay run, or one stuck on a changed contract): start from the brief
    if brief_id and row.get("source_brief_id") != brief_id:
        # The pack of an earlier version of the brief (lineage): the newer brief is what was approved, so its pack starts
        # from the newer brief's copy, which carries Gate 2's locked lines (found by Round 2's re-test: a refreshed brief's
        # new Reels were replaced by the old pack's).
        return None
    return {"body": row["content_body"], "pieces": {k: r["content_body"] for k, r in rows.items()}}


def execute(worker, job) -> None:
    run = run_of(worker, job)
    if run["input_refs"].get("workflow") != c2.VERSION:
        raise ValueError("Not a content pack v2 run")
    stage = job["stage"]
    if stage == "pack_assemble":
        freeze(worker, job, run)
    runtime_v2.check_dependencies(worker, run)
    if stage == "pack_assemble":
        from ..briefs import gate_two
        refs = run["input_refs"]
        handoff = gate_two.handoff_v2(worker.repo, refs["brief"]["brief_id"])
        if handoff.get("approved_hash") != refs["brief"]["approved_hash"]:
            raise ValueError("The approved brief changed since the pack was started")
        mode = runtime_v2.finish_mode(worker.storage)
        # Round 2: under finisher v3 the Reels are the central story and two premises of their own.
        premises = runtime_v2.profiles(worker.storage)["pack_finish"] in c2.PREMISE_FINISHERS
        draft = assemble.draft(handoff, finish_mode=mode,
                               previous=previous_pack(worker, refs.get("supersedes"), refs["brief"]["brief_id"]),
                               premises=premises)
        found = runtime_v2.profiles(worker.storage)
        if found["pack_finish"] in c2.CALL_FINISHERS or refs.get("pass") and found["pack_refinish"] in c2.CALL_FINISHERS:
            # Finisher v4: the card's whole call, for the plan to find premises in (packs/call.py).
            from . import call as card_call
            with worker.repo.connection() as conn:
                draft["call"] = card_call.turns(conn, refs["brief"]["brief_id"])
        if refs.get("pass"):
            if not refs.get("supersedes") or "attested" not in draft:
                raise ValueError("A pass works on a finished pack")
            draft = passes.prepare(draft, refs["pass"])
        save(worker, job, run, {"handoff": handoff, "draft": {**draft, "finish_mode": mode, "premises": premises}},
             f"Assembled {sum(p['content'] is not None for p in draft['pieces'].values())} of 5 pieces from the approved brief")
        return
    prior = output(worker, run, prior_of(run, stage))
    handoff = prior["handoff"]
    pass_ = run["input_refs"].get("pass") or {}
    if stage in WRITERS:
        draft = prior["draft"]
        if stage == "pack_caption":
            progress(worker, job, "Writing the caption and covers from what was said")
            done = passes.run_caption(worker, job, run, draft, handoff, pass_["piece"])
            checked, only = [pass_["piece"]], passes.check_only(pass_["piece"])
        else:
            progress(worker, job, "Finishing the copy again with the granted items" if stage == "pack_refinish"
                     else "Finishing the copy in WIA's house style")
            done = finish.run(worker, job, run, draft, handoff, stage=stage)
            checked, only = [k for k in c2.PIECE_KEYS if done["pieces"][k]["origin"] in ("finished", "written")], None
        # Every recorded take on the pack (this pass's included) is a source for the check of its Reel's caption.
        said = dict(draft["body"].get("recorded_takes") or {})
        if done.get("extra_evidence"):
            # Finisher v4: the turns behind the premise Reels are evidence for the check and the repair.
            handoff = {**handoff, "evidence": [*(handoff.get("evidence") or []), *done["extra_evidence"]]}
        state = {"pieces": done["pieces"], "body": done["body"], "finish_mode": draft["finish_mode"], "attested": draft.get("attested") or [],
                 "finished_keys": checked, "fidelity": {"finisher_called": done["called"]},
                 **({"check_only": only} if only else {}), **({"said": said} if said else {})}
        save(worker, job, run, {"handoff": handoff, "state": state},
             "Finished the copy" if done["called"] else "No finishing call in this mode")
        return
    state = prior["state"]
    said = state.get("said")
    fid = state["fidelity"]
    # Only what the finisher changed or wrote is checked: a piece left as the brief wrote it was checked before Gate 2.
    checkable = state["finished_keys"]
    if stage == "pack_check":
        if state["finish_mode"] == "assemble" or not fid["finisher_called"]:
            result = {"statements": [], "flags": [], "skipped": 0, "called": False}
        else:
            progress(worker, job, "Checking every statement against the call")
            only = {k: set(v) for k, v in state["check_only"].items()} if state.get("check_only") else None
            result = fidelity.check(worker, job, run, state["pieces"], handoff, keys=checkable, only=only,
                                    attested=state.get("attested"), said=said)
        fid.update(checked=len(result["statements"]), flags=result["flags"], check_called=result["called"])
        if result.get("readings"):
            fid["readings"] = result["readings"]  # check v4: how strong each piece is (Round 2)
        save(worker, job, run, {"handoff": handoff, "state": state},
             f"{len(result['flags'])} flags from {len(result['statements'])} statements" if result["called"] else "Nothing to check")
        return
    if stage == "pack_repair":
        flags = fid.get("flags") or []
        if flags:
            progress(worker, job, f"Repairing {len(flags)} flagged statements")
            result = fidelity.repair(worker, job, run, state["pieces"], handoff, flags, attested=state.get("attested"), said=said)
        else:
            result = {"pieces": state["pieces"], "applied": [], "missed": [], "called": False}
        state["pieces"] = result["pieces"]
        fid.update(repairs=result["applied"], missed_patches=result["missed"], repair_called=result["called"])
        save(worker, job, run, {"handoff": handoff, "state": state},
             f"{len(result['applied'])} repairs applied, {len(result['missed'])} not found" if result["called"] else "Nothing to repair")
        return
    if stage == "pack_recheck":
        repairs = fid.get("repairs") or []
        if repairs:
            progress(worker, job, "Checking the repaired statements again")
            result = fidelity.check(worker, job, run, state["pieces"], handoff, stage="pack_recheck",
                                    only=fidelity.changed_leaves(repairs, state["pieces"]), attested=state.get("attested"),
                                    said=said)
            repaired_leaves = {(r["piece"], r["path"]) for r in repairs}
            # A flag on a whole piece (an editorial note on a Reel's premise) counts as repaired when that piece was patched;
            # the re-check reads the patched lines again.
            repaired_pieces = {r["piece"] for r in repairs}
            unrepaired = [f for f in fid.get("flags") or [] if (f["piece"], f["path"]) not in repaired_leaves
                          and not (f.get("path") is None and f["piece"] in repaired_pieces)]
            survivors = result["flags"] + unrepaired
        else:
            result = {"statements": [], "flags": [], "called": False}
            survivors = list(fid.get("flags") or [])
        fid.update(rechecked=len(result["statements"]), recheck_flags=result["flags"], survivors=survivors,
                   recheck_called=result["called"])
        save(worker, job, run, {"handoff": handoff, "state": state},
             f"{len(survivors)} flags remain for finalize" if survivors else "No flag remains")
        return
    if stage == "pack_finalize":
        _finalize(worker, job, run, state, handoff)
        return
    raise ValueError(f"Unknown pack stage {stage}")


def _finalize(worker, job, run, state: dict, handoff: dict) -> None:
    fid = state["fidelity"]
    pass_ = run["input_refs"].get("pass") or {}
    pieces, record = finalize.settle(state["pieces"], fid.get("survivors") or [],
                                     open_keys=[pass_["piece"]] if pass_.get("kind") == "caption" else ())
    fid.update(settled=record, put_back=sum(r["outcome"] == "put_back" for r in record),
               open=sum(r["outcome"] == "open_finding" for r in record))
    state = {**state, "pieces": pieces}
    body = finalize.body_for(state, run, handoff, worker)
    refs = run["input_refs"]
    with worker.repo.connection() as conn:
        worker.repo.guard(conn, job)
        brief = conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s", (refs["brief"]["brief_id"],)).fetchone()
        pack = model.get(conn, refs["pack_id"], lock=True)
        # Every client quote in copy is listed for the client's okay before posting, declared by the finisher or not (a
        # note, never a gate; section 4.3).
        from . import checks
        body["client_quotes"] = list(body.get("client_quotes") or []) + checks.missing_client_quotes(body, pieces, brief)
        validation = finalize.deterministic(conn, {**pack, "content_body": body}, pieces, brief)
        result = model.write_version(worker.repo, conn, parent=None, pack_id=refs["pack_id"], run_id=run["run_id"], brief=brief,
                                     body=body, piece_bodies=pieces, actor=finalize.SYSTEM_ACTOR, validation=validation,
                                     reuse_row=True)
        worker.repo.event(conn, run["run_id"], "pack_ready_for_review", "Content pack finished and checked; ready for review",
                          details={"pack_id": refs["pack_id"], "manifest_hash": result["manifest_hash"],
                                   "open_findings": fid["open"], "put_back": fid["put_back"]})
        # Finishing the last job leaves the run waiting for review (repository.finish).
        worker.repo.finish(conn, job, {"pack_id": refs["pack_id"], "manifest_hash": result["manifest_hash"]},
                           message="Content pack ready for review")
