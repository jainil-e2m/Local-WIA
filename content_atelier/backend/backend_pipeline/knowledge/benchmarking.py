"""The scheduled knowledge-base benchmark (L.B11): an approved identity change reaches a benchmarked version without a
developer.

An identity change (rules, exemplars, beliefs, audience language, format) is approved, then waits for an E.B3 smoke
result before it becomes the default (L.B4, R44). The scheduler (`knowledge/scheduler.tick`, every pass) finds the newest
version in that state that was compiled from the version in force and has no result yet, and queues one `evaluation_run`
job on the `bulk` queue (a `kb_benchmark` run, week-less, like a document run). The worker runs benchmark version 1
(`python -m evaluation`'s own request builders and metrics: the strategist profile and model the settings name, that is the
configuration of record, on development Weeks 1 and 2, three samples each) on the version and on the version it was
compiled from, and records the comparison on the version for an approver:
which accuracy measures got worse, a suggested verdict and the report's path. It never records the benchmark itself
and never activates a version; an identity approver does that with the result (`record_benchmark`, the Versions screen).

Spending is safe by default. The job spends only under a **standing run plan**: one a person created for this purpose
(`storage_cli plan create --standing kb_benchmark ...`, its stage `evaluation`, the strategist's model, a call limit and
a cost cap; a long `--hours`). Without one, or with one that has expired, does not cover the stage or model, or has fewer
calls left than the samples the benchmark still needs, nothing is queued and the cycle's knowledge notice says why.
Every call reserves and settles against the plan (E.B1) through the harness's single dispatch (S.B1's routing).

The benchmark's inputs (the development weeks' excerpts and Whitney's Week 1 alternatives) carry call excerpts and live
under `research/` (R48), which the production image does not carry; where they or the `evaluation` package are missing,
or the settings name a strategist profile the harness has no configuration for, nothing is queued: the version records
a `skipped` result with the reason (shown on the Versions screen and in the cycle's notice), and a job that reaches such
a worker finishes as skipped rather than failing. Tone-change benchmarks therefore run from a checkout, with the inputs
and a key, by a developer or the weekly tone loop (plan X.2); the image only carries the record of why it did not run.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from functools import partial

from ..repository import insert
from ..store import canonical_hash
from . import compiler

STANDING = "kb_benchmark"
STAGE = "evaluation_run"
RUN_SCOPE = "kb_benchmark"
PLAN_STAGE = "evaluation"
WEEKS = ("week1", "week2")
SAMPLES = 3
# The accuracy measures a regression is read from (E.B10's ledger flags; a card without WIA's contribution). The judge
# stays a smoke test, never the gate; the approver decides.
ACCURACY = (("blocking_flags", "blocking ledger flags"), ("without_wia_contribution", "cards without a WIA contribution"))


def harness():
    """The evaluation harness's run module, or why this environment cannot run the benchmark."""
    try:
        from evaluation import run as ev
        from evaluation.benchmark import SOURCES
    except ImportError:
        return None, "the evaluation harness (backend/evaluation) is not installed where the scheduler runs"
    missing = [p for p in (*ev.WEEKS.values(), SOURCES["week1_alternatives"]) if not p.is_file()]
    if missing:
        return None, ("benchmark v1's inputs are not on this machine (research/ carries call excerpts and is not in the "
                      "image, R48): " + ", ".join(p.name for p in missing))
    return ev, None


def configuration(ev, conn) -> tuple[str | None, str | None, str | None]:
    """The harness configuration of record: (name, model, None), or (None, None, why not). The strategist profile and
    the angle model come from the settings (`prompts.profile.strategist`, `models.angle_generation`), not from a version
    this module was written for; a profile the harness has no strategist configuration for cannot be benchmarked."""
    from ..settings_store import values
    current = values(("prompts.profile.strategist", "models.angle_generation"), conn)
    profile, model = current["prompts.profile.strategist"], current["models.angle_generation"]
    for name, config in ev.CONFIGS.items():
        if config["profile"] == profile and name.startswith("strategist_") and not config.get("without"):
            return name, model or config["model"], None
    return None, None, (f"the configuration of record's strategist profile ({profile}) has no benchmark configuration in the "
                        "evaluation harness; apply the production settings or benchmark from a checkout")


def standing_plan(conn, now: datetime | None = None) -> dict | None:
    """The newest active, unexpired run plan a person created for the scheduled benchmark."""
    now = now or datetime.now(UTC)
    if not conn.execute("SELECT to_regclass('public.run_plans') AS t").fetchone()["t"]:
        return None
    return conn.execute("""SELECT * FROM run_plans WHERE status='active' AND details->>'standing'=%s AND expires_at>%s
        ORDER BY approved_at DESC,plan_id LIMIT 1""", (STANDING, now)).fetchone()


def _stored(conn, version, *, lock=False):
    row = conn.execute("SELECT value FROM settings WHERE key=%s" + (" FOR UPDATE" if lock else ""),
                       (compiler.MANIFEST_PREFIX + version,)).fetchone()
    return row["value"] if row else None


def waiting(conn) -> dict | None:
    """The newest approved version that waits for its benchmark and can still be recorded (compiled from the version in
    force), as {version, compiled}."""
    active = compiler.active_version(conn)
    for row in conn.execute("""SELECT key,value FROM settings WHERE starts_with(key,%s)
            AND value->'compiled'->>'state'='approved_pending_benchmark' ORDER BY updated_at DESC,key""",
                            (compiler.MANIFEST_PREFIX,)).fetchall():
        compiled = row["value"]["compiled"]
        if active is None or compiled.get("base_version") == active:
            return {"version": row["key"][len(compiler.MANIFEST_PREFIX):], "compiled": compiled}
    return None


def _is_compiled(conn, version) -> bool:
    return bool(conn.execute("SELECT 1 FROM brand_kit_docs WHERE version=%s LIMIT 1", (version,)).fetchone())


def _contexts(ev, conn, version, base, database_url):
    """The harness's context for the version under test and for its base: a compiled base is read from the database; a
    file base is the committed knowledge base, which must be that version."""
    from ..database import connect
    connection = partial(connect, database_url)
    candidate = {"version": version, "connection": connection, "label": None}
    if _is_compiled(conn, base):
        return candidate, {"version": base, "connection": connection, "label": None}
    from ..knowledge_base import load_knowledge_base
    files = load_knowledge_base(ev.KB).version
    if files != base:
        raise ValueError(f"The version was compiled from {base}, but the committed knowledge base is {files}; compile again")
    return candidate, {"version": None, "connection": None, "label": base}


def calls_needed(ev, contexts, config) -> int:
    """Samples not yet saved under the scheduled benchmark's folder: each is one paid call."""
    n = 0
    for context in contexts:
        with ev.under(out=ev.OUT / "scheduled", **context):
            n += sum(not ev.sample_path(config, w, s).is_file() for w in WEEKS for s in range(1, SAMPLES + 1))
    return n


def refusal(plan, ev, contexts, config, model) -> str | None:
    """Why the standing plan cannot pay for this benchmark, or None."""
    if plan is None:
        return ("no standing run plan exists for it; a person creates one with `storage_cli plan create --standing "
                f"{STANDING} --stage {PLAN_STAGE} --model {model} --input-set-hash '*' ...`")
    if PLAN_STAGE not in plan["stages"] or model not in plan["models"]:
        return f"the standing run plan {plan['plan_id']} does not cover stage {PLAN_STAGE} and model {model}"
    if plan.get("input_set_hash") not in (None, "*"):
        return f"the standing run plan {plan['plan_id']} is bound to one input set; the harness needs one created with '*'"
    needed = calls_needed(ev, contexts, config)
    left = plan["max_calls"] - plan["calls_used"]
    if left < needed:
        return f"the standing run plan {plan['plan_id']} has {left} calls left and the benchmark needs {needed}"
    if Decimal(str(plan["cost_used_usd"])) >= Decimal(str(plan["max_cost_usd"])):
        return f"the standing run plan {plan['plan_id']} has reached its cost cap of USD {plan['max_cost_usd']}"
    return None


def _latest_job(conn, version):
    return conn.execute("""SELECT j.job_id,j.status,j.error_summary,j.created_at FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id)
        WHERE r.run_scope=%s AND r.input_refs->'knowledge_base'->>'version'=%s ORDER BY j.created_at DESC LIMIT 1""",
                        (RUN_SCOPE, version)).fetchone()


def status(conn, now: datetime | None = None) -> dict | None:
    """Where the waiting version's scheduled benchmark stands, for the cycle's notice and the scheduler: None when no
    version waits; else its state (recorded, queued, failed, refused or ready) and the reason or result. A refusal that
    comes from absent inputs (the harness, its data, a profile it has no configuration for) says `skip: True`: the
    benchmark cannot run where the scheduler runs, whatever the plan."""
    now = now or datetime.now(UTC)
    found = waiting(conn)
    if not found:
        return None
    version, compiled = found["version"], found["compiled"]
    out = {"version": version, "on": compiled.get("on"), "base_version": compiled.get("base_version")}
    recorded = compiled.get("scheduled_benchmark") or {}
    if recorded.get("state") == "recorded":
        return {**out, "state": "recorded", "result": recorded}
    job = _latest_job(conn, version)
    if job and job["status"] in ("queued", "running"):
        return {**out, "state": "queued", "job_id": job["job_id"]}
    if job and job["status"] == "failed" and job["created_at"].date() == now.date():
        # A failed benchmark is queued again on the next day's first pass, not in a loop.
        return {**out, "state": "failed", "job_id": job["job_id"], "reason": job["error_summary"]}
    ev, why = harness()
    if why:
        return {**out, "state": "refused", "reason": why, "skip": True}
    config, model, why = configuration(ev, conn)
    if why:
        return {**out, "state": "refused", "reason": why, "skip": True}
    try:
        contexts = _contexts(ev, conn, version, compiled.get("base_version"), None)
    except ValueError as error:
        return {**out, "state": "refused", "reason": str(error)}
    plan = standing_plan(conn, now)
    if why := refusal(plan, ev, contexts, config, model):
        return {**out, "state": "refused", "reason": why}
    return {**out, "state": "ready", "plan_id": plan["plan_id"], "config": config, "model": model}


def schedule(repo, now: datetime | None = None) -> dict | None:
    """The scheduler's part (every pass): queue the waiting version's benchmark when a standing plan can pay for it.
    Returns None when no version waits, else what it found or did."""
    now = now or datetime.now(UTC)
    with repo.connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(7313)")
        found = status(conn, now)
        if found and found.get("skip"):
            record_skip(conn, found["version"], found["reason"], now)
        if not found or found["state"] != "ready":
            return found
        version = found["version"]
        run_id = "kbbench_" + canonical_hash([version, now.date().isoformat()])[:24]
        refs = {"knowledge_base": {"version": version}, "base_version": found["base_version"], "plan_id": found["plan_id"],
                "config": found["config"], "model": found["model"], "weeks": list(WEEKS), "samples": SAMPLES}
        insert(conn, "pipeline_runs", {"run_id": run_id, "week_id": None, "run_scope": RUN_SCOPE, "trigger_type": "scheduled",
                                       "triggered_by": "scheduler", "input_refs": refs,
                                       "current_message": "Benchmarking an approved identity change"}, conflict=True)
        key = canonical_hash([STAGE, version, now.date().isoformat()])
        job_id = "kbjob_" + key[:24]
        insert(conn, "pipeline_jobs", {"job_id": job_id, "run_id": run_id, "week_id": None, "stage": STAGE,
                                       "idempotency_key": "kb_benchmark:" + key, "input_hash": key,
                                       "progress_details": {"dependencies": []},
                                       "current_message": f"Waiting to benchmark {version}"}, conflict=True)
    from ..jobs.dispatch import kick
    kick(repo, run_id=run_id)
    return {**found, "state": "queued", "run_id": run_id, "job_id": job_id}


def record_skip(conn, version: str, reason: str, now: datetime | None = None) -> bool:
    """Record on the waiting version why its scheduled benchmark cannot run here, once per reason: the Versions screen
    shows it beside what an approver decides. A recorded result is never replaced; returns whether anything was written."""
    value = _stored(conn, version, lock=True)
    if not value or value["compiled"].get("state") != "approved_pending_benchmark":
        return False
    held = value["compiled"].get("scheduled_benchmark") or {}
    if held.get("state") == "recorded" or (held.get("state") == "skipped" and held.get("reason") == reason):
        return False
    value["compiled"]["scheduled_benchmark"] = {"state": "skipped", "reason": reason,
                                                 "at": (now or datetime.now(UTC)).isoformat()}
    conn.execute("UPDATE settings SET value=%s,updated_at=now() WHERE key=%s", (json.dumps(value), compiler.MANIFEST_PREFIX + version))
    return True


def compare(base: dict, candidate: dict, config: str) -> list[str]:
    """The accuracy measures on which the version did worse than its base, week by week (mean over the samples)."""
    out = []
    for week in WEEKS:
        before = base["configs"][config]["weeks"][week]["summary"]
        after = candidate["configs"][config]["weeks"][week]["summary"]
        for key, label in ACCURACY:
            if after.get(key, {}).get("mean", 0) > before.get(key, {}).get("mean", 0):
                out.append(f"{week}: more {label} ({after[key]['mean']} against {before.get(key, {}).get('mean', 0)})")
    return out


def _summary(report: dict, config: str) -> dict:
    keys = ("public_cards", "blocking_flags", "check_flags", "without_wia_contribution", "reframe_alignment")
    return {w: {k: s[k]["mean"] for k in keys if k in (s := report["configs"][config]["weeks"][w]["summary"])}
            for w in WEEKS}


def _spent(conn, plan_id) -> float:
    row = conn.execute("SELECT cost_used_usd FROM run_plans WHERE plan_id=%s", (plan_id,)).fetchone()
    return float(row["cost_used_usd"]) if row else 0.0


def execute(worker, job) -> None:
    """The `evaluation_run` stage: benchmark the version and its base under the standing plan, record the comparison."""
    from ..llm.run_plans import SqlPlanStore
    repo, url = worker.repo, worker.storage.database_url
    with repo.connection() as conn:
        refs = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (job["run_id"],)).fetchone()["input_refs"]
        version, base = refs["knowledge_base"]["version"], refs["base_version"]
        config, model = refs["config"], refs.get("model")
        still = waiting(conn)
        if not still or still["version"] != version:
            repo.finish(conn, job, {"skipped": "the version no longer waits for its benchmark"}, message="Nothing to benchmark")
            return
        ev, why = harness()
        if why:
            # Not a failure: the inputs are not where this worker runs (R48). Say so on the version and finish.
            record_skip(conn, version, why)
            repo.finish(conn, job, {"skipped": why}, message=f"The benchmark cannot run here: {why}"[:240])
            return
        candidate, previous = _contexts(ev, conn, version, base, url)
        spent_before = _spent(conn, refs["plan_id"])
    plan = SqlPlanStore(url, refs["plan_id"])
    reports = {}
    for name, context in (("base", previous), ("version", candidate)):
        # The harness's own requests and metrics (E.B3); every call reserves and settles against the standing plan.
        with ev.under(out=ev.OUT / "scheduled", plan=plan, model=model, **context):
            try:
                reports[name] = ev.report([config], list(WEEKS), SAMPLES)
            except SystemExit as error:
                # The command-line harness exits on a refused or unreadable sample; here that fails the job, not the worker.
                raise RuntimeError(f"Benchmarking the {name} ({context['version'] or context['label']}): {error}") from None
    regressions = compare(reports["base"], reports["version"], config)
    ran = datetime.now(UTC)
    path = ev.OUT / "scheduled" / "results" / f"{ran.date().isoformat()}-{config}.{version}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": version, "base_version": base, "regressions": regressions, **reports},
                               ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    from evaluation.benchmark import PROJECT
    result_ref = path.relative_to(PROJECT).as_posix() if path.is_relative_to(PROJECT) else str(path)
    with repo.connection() as conn:
        spent = round(_spent(conn, refs["plan_id"]) - spent_before, 6)
        value = _stored(conn, version, lock=True)
        compiled = value["compiled"]
        record = {"state": "recorded", "result_ref": result_ref, "suggested": "pass" if not regressions else "review",
                  "regressions": regressions, "base_version": base, "benchmark": reports["version"]["benchmark"],
                  "config": config, "model": model, "weeks": list(WEEKS), "samples": SAMPLES, "summary": {
                      "version": _summary(reports["version"], config), "base": _summary(reports["base"], config)},
                  "spent_usd": spent, "plan_id": refs["plan_id"], "job_id": job["job_id"], "ran_at": ran.isoformat()}
        if compiled.get("state") == "approved_pending_benchmark":
            # Recorded for the approver; the version's state and its documents' benchmark_state stay as they are.
            compiled["scheduled_benchmark"] = record
            conn.execute("UPDATE settings SET value=%s,updated_at=now() WHERE key=%s",
                         (json.dumps(value), compiler.MANIFEST_PREFIX + version))
        repo.finish(conn, job, record, message="No regression on the accuracy measures; an approver records it" if not regressions
                    else f"{len(regressions)} accuracy measures got worse; an approver decides")


def notice(state: dict | None) -> str | None:
    """The cycle's knowledge notice about a version waiting for its benchmark (L.B11)."""
    if not state:
        return None
    when = f"compiled on {state['on']}" if state.get("on") else state["version"]
    head = f"The knowledge base {when} is approved and waits for its benchmark"
    if state["state"] == "recorded":
        r = state["result"]
        found = ("found no regression on the accuracy measures" if not r["regressions"] else
                 "found a regression: " + "; ".join(r["regressions"]))
        return (f"{head}: the scheduled benchmark {found} (USD {r['spent_usd']}). An identity approver records the result "
                f"under What the system knows, Versions ({r['result_ref']}).")
    if state["state"] == "queued":
        return f"{head}: the scheduled benchmark is running."
    if state["state"] == "failed":
        return f"{head}: today's scheduled benchmark failed ({(state.get('reason') or '')[:200]}); it is tried again tomorrow."
    if state["state"] == "refused":
        return f"{head}, and the scheduled benchmark cannot run: {state['reason']}."
    return f"{head}: the scheduled benchmark is queued on the next pass."

