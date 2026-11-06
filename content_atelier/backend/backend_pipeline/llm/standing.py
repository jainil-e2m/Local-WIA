"""Standing weekly budgets (plan 6.B3, D36): one database run plan per purpose and week, found without a variable.

A live week needs no run-plan variable and no redeploy. Each paid call belongs to a purpose (the weekly cycle, briefs,
refreshes, embedding, extraction, the learning loop's context mining): the job that makes it names the purpose
(`purpose`), or the call's stage does (`STAGE_PURPOSE`). The call reserves against that purpose's plan for the current
week (Monday 00:00 UTC to the next Monday, when the internal OpenRouter key's weekly allowance also resets), which is
created from the settings the first time it is needed and renewed by the scheduler each week (`renew`, 0.B6). Its cap is
the setting `budgets.weekly_usd.<purpose>` (blank: no standing budget for that purpose) and `budgets.weekly_calls.<purpose>`;
`storage_cli budgets set` changes both and the current week's plan with them, and `budgets show` lists the week.

A call that would pass the cap is refused before it is sent (E.B1's check, with the call's worst case), as `BudgetExhausted`
with the purpose and a reason in words. The job that made it waits instead of failing (`wait_for_budget`): its reason is on
the job and its run, where the app shows it (the cycle, the card's brief, a refresh), and the scheduler queues it again
once that purpose has room (the next week's plan, or a raised cap: `release_waits`). A plan named by ATELIER_RUN_PLAN_ID
or ATELIER_RUN_PLAN_FILE overrides all of this for a one-off run (`run_plans.from_environment`).
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from .run_plans import ANY_INPUT, ANY_MODEL, BudgetExhausted, RunPlanError, SqlPlanStore

PURPOSES = ("cycle", "briefs", "refreshes", "embedding", "extraction", "context_mining", "packs")
LABELS = {"cycle": "weekly cycle", "briefs": "briefs", "refreshes": "refreshes", "embedding": "embedding",
          "extraction": "scene extraction", "context_mining": "context mining", "packs": "content packs"}
# The purpose of a call made outside a job that names one: by its stage.
BRIEF_STAGES = ("brief_plan", "brief_grade", "brief_write", "brief_review", "brief_repair", "brief_verify", "brief_web")
# Content packs (Phase NP, D43f): every pack stage, NP-7's post-recording pass and permission re-finish included, so a
# week's plan, whose stage list is frozen when the week's row is created, never refuses a later pack stage (NP.B5).
PACK_STAGES = ("pack_finish", "pack_check", "pack_repair", "pack_recheck", "pack_caption", "pack_refinish")
STAGE_PURPOSE = {"moment_extraction": "extraction", "document_classification": "extraction", "topic_assignment": "extraction",
                 "embedding": "embedding", "angle_generation": "cycle", "angle_refinement": "cycle",
                 "card_verification": "cycle", "context_mining": "context_mining", **{s: "briefs" for s in BRIEF_STAGES},
                 **{s: "packs" for s in PACK_STAGES}}
# A standing plan covers every stage its purpose's jobs may call (a brief's query embeddings, a cycle's card checks);
# the purpose decides which plan pays, the cap is the guard.
ALL_STAGES = tuple(sorted(STAGE_PURPOSE))
# Who approved a plan whose cap is the code default (plan D36's figures): no person set it, and the plan says so.
DEFAULT_APPROVER = "standing-defaults@content-atelier.invalid"
KIND = "weekly"
# `budgets.uncapped` (the owner, 27 October 2026): no weekly cap binds. A purpose's plan keeps recording what is spent, with a
# ceiling no week reaches, so no call is refused and no job waits for budget; the provider's own key limit still applies.
# The ceiling fits run_plans.max_cost_usd (numeric(10,4)).
UNCAPPED_USD, UNCAPPED_CALLS = 100_000, 10_000_000

_purpose: ContextVar[str | None] = ContextVar("atelier_budget_purpose", default=None)


@contextmanager
def purpose(name: str | None):
    """The purpose every paid call inside the block spends (a job's run scope decides it: a brief revision is a refresh)."""
    if name is not None and name not in PURPOSES:
        raise ValueError(f"Unknown budget purpose {name}; one of {', '.join(PURPOSES)}")
    token = _purpose.set(name)
    try:
        yield name
    finally:
        _purpose.reset(token)


def purpose_of(stage: str) -> str | None:
    return _purpose.get() or STAGE_PURPOSE.get(stage)


# Run scopes and the purpose their jobs spend. A cycle's extraction stage reads the scene ledger, document by document: it is
# extraction, like a document's own job.
SCOPE_PURPOSE = {"weekly_angles": "cycle", "angle_reassessment": "cycle", "comparison_reassessment": "cycle",
                 "brief_generation": "briefs", "brief_revision": "refreshes", "card_refresh": "refreshes",
                 "pack_generation": "packs"}


def purpose_for_job(scope: str | None, stage: str | None) -> str | None:
    if stage == "moment_extraction":
        return "extraction"
    return SCOPE_PURPOSE.get(scope or "")


# ---- the week and its plans ------------------------------------------------------------------------------------------------

def week_of(now: datetime) -> tuple[datetime, datetime]:
    """The budget week holding `now`: Monday 00:00 UTC to the next Monday."""
    now = now.astimezone(UTC)
    start = datetime(now.year, now.month, now.day, tzinfo=UTC) - timedelta(days=now.weekday())
    return start, start + timedelta(days=7)


def plan_id(name: str, start: datetime) -> str:
    return f"plan_standing_{name}_{start:%Y%m%d}"


def caps(conn) -> dict[str, dict]:
    """Each purpose's cap from the settings, where it came from and who set it."""
    from ..settings_store import load
    eff = load(conn, read_files=False, environ={})
    out = {}
    uncapped = bool(eff.values.get("budgets.uncapped"))
    for name in PURPOSES:
        usd_key, calls_key = f"budgets.weekly_usd.{name}", f"budgets.weekly_calls.{name}"
        row = eff.rows.get(usd_key) or eff.rows.get(calls_key) or {}
        out[name] = {"usd": eff.values[usd_key], "calls": eff.values[calls_key], "source": eff.sources[usd_key],
                     "set_by": row.get("updated_by"), "enabled": eff.values["budgets.standing"], "uncapped": uncapped}
        if uncapped:
            urow = eff.rows.get("budgets.uncapped") or {}
            out[name].update(usd=UNCAPPED_USD, calls=UNCAPPED_CALLS, source="uncapped", set_by=urow.get("updated_by"))
    return out


def ensure(conn, name: str, now: datetime | None = None, *, cap: dict | None = None) -> dict | None:
    """This week's plan for a purpose, created from the settings when it does not exist yet; None when the purpose has no
    standing budget. The row is locked for the caller's transaction."""
    now = now or datetime.now(UTC)
    cap = cap or caps(conn)[name]
    start, end = week_of(now)
    pid = plan_id(name, start)
    if cap["usd"] is not None:
        approver = cap["set_by"] if cap["set_by"] and "@" in cap["set_by"] else DEFAULT_APPROVER
        details = {"standing": KIND, "budget_purpose": name, "week_start": start.isoformat(), "week_end": end.isoformat(),
                   "cap_source": "plan D36 default" if cap["source"] == "default" else f"settings ({cap['source']})",
                   "cap_set_by": cap["set_by"]}
        # approved_at is the week's start, so the plan reads as the week's own; expires_at the next Monday.
        conn.execute("""INSERT INTO run_plans(plan_id,purpose,stages,models,input_set_hash,max_calls,max_cost_usd,approver,
            approved_at,expires_at,details) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (plan_id) DO NOTHING""",
                     (pid, f"standing weekly budget: {LABELS[name]}", list(ALL_STAGES), [ANY_MODEL], ANY_INPUT, int(cap["calls"]),
                      cap["usd"], approver, start, end, json.dumps(details)))
        if cap.get("uncapped"):
            # A week's plan made under a cap is lifted to the uncapped ceiling, and one the cap closed opens again.
            conn.execute("""UPDATE run_plans SET max_cost_usd=GREATEST(max_cost_usd,%s),max_calls=GREATEST(max_calls,%s),
                status=CASE WHEN status='exhausted' THEN 'active' ELSE status END,
                closed_reason=CASE WHEN status='exhausted' THEN NULL ELSE closed_reason END WHERE plan_id=%s""",
                         (cap["usd"], cap["calls"], pid))
    return conn.execute("SELECT * FROM run_plans WHERE plan_id=%s FOR UPDATE", (pid,)).fetchone()


def left_usd(row: dict) -> float:
    return float(max(Decimal(0), Decimal(str(row["max_cost_usd"])) - Decimal(str(row["cost_used_usd"]))))


def calls_left(row: dict) -> int:
    return max(0, int(row["max_calls"]) - int(row["calls_used"]))


def has_room(row: dict | None, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    return bool(row) and row["status"] == "active" and row["expires_at"] > now and row["calls_used"] < row["max_calls"] \
        and Decimal(str(row["cost_used_usd"])) < Decimal(str(row["max_cost_usd"]))


def _money(value) -> str:
    return f"USD {float(value):.2f}"


def describe(name: str, row: dict, error: Exception) -> str:
    """The refusal in words a reviewer reads (R50): which budget, how much is spent, what happens next."""
    _, end = week_of(row["approved_at"]) if isinstance(row["approved_at"], datetime) else week_of(datetime.now(UTC))
    renews = f"It renews on Monday {end:%d %B} at 00:00 UTC, or an administrator can raise it."
    text = str(error)
    if "could cost up to" in text:
        worst = text.split("could cost up to USD ")[1].split(",")[0]
        return (f"This week's {LABELS[name]} budget has {_money(left_usd(row))} left of {_money(row['max_cost_usd'])}, and the "
                f"next call could cost up to USD {float(worst):.2f}, so it was not sent. {renews}")
    # A plan that reached its call limit is closed as exhausted; its counts say so even when the refusal's words do not (N1
    # shakedown: a call cap read "budget is spent (USD 0.00 of USD 0.50)").
    if ("calls" in text and "used all" in text) or int(row.get("calls_used") or 0) >= int(row.get("max_calls") or 0) > 0:
        return (f"This week's {LABELS[name]} budget has used all {row['max_calls']} calls it allows, so the next call was not "
                f"sent. {renews}")
    return (f"This week's {LABELS[name]} budget is spent ({_money(row['cost_used_usd'])} of {_money(row['max_cost_usd'])}), so "
            f"the next call was not sent. {renews}")


class StandingPlanStore:
    """The plan store of a worker or the API with no named plan: each call reserves against its purpose's weekly plan."""

    def __init__(self, database_url: str, *, clock=None):
        self.database_url = database_url
        self.clock = clock or (lambda: datetime.now(UTC))

    def _connect(self):
        from ..database import connect
        return connect(self.database_url, vectors=False)

    def plan_for(self, stage: str) -> tuple[str, dict]:
        """The purpose and this week's plan row for a call of this stage, or a refusal saying why there is none."""
        name = purpose_of(stage)
        with self._connect() as conn:
            cap = caps(conn)
            if name is None:
                raise RunPlanError(f"No standing budget covers the {stage} stage; name a run plan for it (ATELIER_RUN_PLAN_ID)")
            if not cap[name]["enabled"]:
                raise RunPlanError("Standing budgets are switched off (budgets.standing); a paid call needs a named run plan "
                                   "(storage_cli plan create, then ATELIER_RUN_PLAN_ID)")
            row = ensure(conn, name, self.clock(), cap=cap[name]) if cap[name]["usd"] is not None else None
            conn.commit()
        if row is None:
            raise RunPlanError(f"No standing budget is set for {LABELS[name]} (budgets.weekly_usd.{name} is blank); set one "
                               f"with `storage_cli budgets set --purpose {name} --weekly-usd <usd>` or name a run plan")
        return name, row

    def reserve(self, *, stage, model, fingerprint, input_set_hash=None, worst_case_usd=None):
        name, row = self.plan_for(stage)
        try:
            return SqlPlanStore(self.database_url, row["plan_id"]).reserve(
                stage=stage, model=model, fingerprint=fingerprint, input_set_hash=input_set_hash, worst_case_usd=worst_case_usd)
        except BudgetExhausted as error:
            with self._connect() as conn:
                current = conn.execute("SELECT * FROM run_plans WHERE plan_id=%s", (row["plan_id"],)).fetchone() or row
            raise BudgetExhausted(describe(name, current, error), purpose=name, plan_id=row["plan_id"],
                                  left_usd=left_usd(current)) from error

    def settle(self, ticket, raw, *, status, error=None):
        SqlPlanStore(self.database_url, ticket.plan_id).settle(ticket, raw, status=status, error=error)


def refusal(error: BaseException | None) -> BudgetExhausted | None:
    """The standing-budget refusal behind an error, if any (a caller may have wrapped it)."""
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, BudgetExhausted) and error.purpose:
            return error
        error = error.__cause__ or error.__context__
    return None


# ---- waiting, release and renewal ------------------------------------------------------------------------------------------

def wait_for_budget(repo, job: dict, error: BudgetExhausted) -> None:
    """The job waits for its purpose's budget instead of failing; the reason is on the job and its run, for the app."""
    from psycopg.types.json import Jsonb
    reason = str(error)
    with repo.connection() as conn:
        current = repo.guard(conn, job)
        plan = conn.execute("SELECT max_calls,calls_used FROM run_plans WHERE plan_id=%s", (error.plan_id,)).fetchone()
        details = {**(current["progress_details"] or {}), "waiting_for": "budget", "budget_purpose": error.purpose,
                   "budget_plan_id": error.plan_id, "budget_left_usd": error.left_usd, "budget_reason": reason,
                   "budget_calls_left": calls_left(plan) if plan else 0,
                   "budget_waiting_since": datetime.now(UTC).isoformat()}
        conn.execute("""UPDATE pipeline_jobs SET status='waiting',progress_details=%s,current_message=%s,error_summary=NULL,
            finished_at=now(),updated_at=now(),lease_token=NULL,lease_expires_at=NULL WHERE job_id=%s""",
                     (Jsonb(details), reason, job["job_id"]))
        scope = conn.execute("SELECT run_scope FROM pipeline_runs WHERE run_id=%s", (job["run_id"],)).fetchone()["run_scope"]
        from ..jobs.policy import PER_DOCUMENT_SCOPES
        if scope in PER_DOCUMENT_SCOPES:
            from ..moments.queue import settle_run
            settle_run(conn, job["run_id"], done_word=PER_DOCUMENT_SCOPES[scope])
        else:
            conn.execute("UPDATE pipeline_runs SET status='partially_completed',current_message=%s,updated_at=now() WHERE run_id=%s",
                         (reason, job["run_id"]))
        if job["stage"] == "moment_extraction":
            from ..documents.select import mark_extraction
            mark_extraction(conn, job["run_id"], "queued", job)
        repo.event(conn, job["run_id"], "budget_wait", reason, job=job, severity="warning",
                   details={"purpose": error.purpose, "plan_id": error.plan_id, "left_usd": error.left_usd})


def release_waits(conn, now: datetime | None = None, *, purposes=None) -> list[str]:
    """Queue again the jobs waiting for a budget that now has room: a new week's plan, or a raised cap. A job refused for one
    call's worst case is released only when its plan changed or has more left than when it was refused."""
    from psycopg.types.json import Jsonb
    from ..repository import identifier, insert
    now = now or datetime.now(UTC)
    rows = conn.execute("""SELECT job_id,run_id,attempt_count,progress_details FROM pipeline_jobs WHERE status='waiting'
        AND progress_details->>'waiting_for'='budget' ORDER BY created_at,job_id FOR UPDATE SKIP LOCKED""").fetchall()
    cache, released = caps(conn), []
    plans: dict[str, dict | None] = {}
    for job in rows:
        details = dict(job["progress_details"] or {})
        name = details.get("budget_purpose")
        if name not in PURPOSES or (purposes and name not in purposes):
            continue
        if name not in plans:
            plans[name] = ensure(conn, name, now, cap=cache[name]) if cache[name]["enabled"] else None
        plan = plans[name]
        if not has_room(plan, now):
            continue
        same = plan["plan_id"] == details.get("budget_plan_id")
        # Room again means more money or more calls than at the refusal: a raised call limit releases a job its call limit
        # stopped (N1 shakedown: it waited on, since its money left had not changed).
        more_calls = calls_left(plan) > int(details.get("budget_calls_left") or 0)
        if same and left_usd(plan) <= float(details.get("budget_left_usd") or 0) + 1e-9 and not more_calls:
            continue
        reason = details.get("budget_reason")
        for key in ("waiting_for", "budget_purpose", "budget_plan_id", "budget_left_usd", "budget_calls_left", "budget_reason",
                    "budget_waiting_since"):
            details.pop(key, None)
        details["budget_released"] = {"at": now.isoformat(), "plan_id": plan["plan_id"], "after": reason}
        conn.execute("""UPDATE pipeline_jobs SET status='queued',progress_details=%s,current_message=%s,finished_at=NULL,
            updated_at=now() WHERE job_id=%s""", (Jsonb(details), "Budget available; waiting to start", job["job_id"]))
        conn.execute("""UPDATE pipeline_runs SET status=CASE WHEN status IN ('partially_completed','failed') THEN 'queued' ELSE status END,
            current_message=%s,updated_at=now() WHERE run_id=%s""", (f"This week's {LABELS[name]} budget has room again", job["run_id"]))
        insert(conn, "pipeline_events", {"event_id": identifier("event"), "run_id": job["run_id"], "job_id": job["job_id"],
                                         "event_type": "budget_released", "message": f"Queued again under {plan['plan_id']}",
                                         "severity": "info", "attempt_number": job["attempt_count"] or None,
                                         "details": {"purpose": name, "plan_id": plan["plan_id"]}})
        released.append(job["job_id"])
    return released


def renew(conn, now: datetime | None = None) -> dict:
    """The scheduler's weekly pass (0.B6): this week's plan for every purpose with a cap, last week's closed as expired, and
    the jobs that waited for a budget queued again."""
    now = now or datetime.now(UTC)
    expired = conn.execute("""UPDATE run_plans SET status='expired',closed_at=now(),closed_reason='the budget week ended'
        WHERE details->>'standing'=%s AND status IN ('active','exhausted') AND expires_at<=%s RETURNING plan_id""",
                           (KIND, now)).fetchall()
    cache = caps(conn)
    plans = {name: (row["plan_id"] if (row := ensure(conn, name, now, cap=cache[name])) else None)
             for name in PURPOSES if cache[name]["enabled"]}
    released = release_waits(conn, now)
    start, end = week_of(now)
    return {"week_start": start.isoformat(), "week_end": end.isoformat(), "plans": plans,
            "expired": [r["plan_id"] for r in expired], "released_jobs": released}


def status(conn, now: datetime | None = None) -> dict:
    """This week's standing budgets, for the app and `budgets show`: the cap, what is spent, what is left, what waits."""
    now = now or datetime.now(UTC)
    start, end = week_of(now)
    cache = caps(conn)
    waiting = {r["purpose"]: r["n"] for r in conn.execute("""SELECT progress_details->>'budget_purpose' AS purpose,count(*) AS n
        FROM pipeline_jobs WHERE status='waiting' AND progress_details->>'waiting_for'='budget' GROUP BY 1""")}
    rows = {r["details"].get("budget_purpose"): r for r in conn.execute(
        "SELECT * FROM run_plans WHERE details->>'standing'=%s AND approved_at=%s", (KIND, start))}
    items = []
    uncapped = bool(cache["cycle"].get("uncapped"))
    for name in PURPOSES:
        cap, row = cache[name], rows.get(name)
        if uncapped:
            # No cap to show: what is spent, and nothing "left" (budgets.uncapped).
            items.append({"purpose": name, "label": LABELS[name], "enabled": cap["enabled"], "uncapped": True, "cap_usd": None,
                          "cap_calls": None, "cap_source": "uncapped", "set_by": cap["set_by"],
                          "plan_id": row["plan_id"] if row else None, "status": row["status"] if row else "not_started",
                          "spent_usd": float(row["cost_used_usd"]) if row else 0.0, "calls_used": row["calls_used"] if row else 0,
                          "left_usd": 0.0, "max_cost_usd": None, "max_calls": None, "waiting_jobs": waiting.get(name, 0)})
            continue
        items.append({"purpose": name, "label": LABELS[name], "enabled": cap["enabled"], "cap_usd": cap["usd"],
                      "cap_calls": cap["calls"], "cap_source": cap["source"], "set_by": cap["set_by"],
                      "plan_id": row["plan_id"] if row else None, "status": row["status"] if row else ("not_started" if cap["usd"] is not None else "no_budget"),
                      "spent_usd": float(row["cost_used_usd"]) if row else 0.0, "calls_used": row["calls_used"] if row else 0,
                      "left_usd": left_usd(row) if row else (cap["usd"] or 0.0),
                      "max_cost_usd": float(row["max_cost_usd"]) if row else cap["usd"], "max_calls": row["max_calls"] if row else cap["calls"],
                      "waiting_jobs": waiting.get(name, 0)})
    return {"week_start": start.isoformat(), "week_end": end.isoformat(), "enabled": cache["cycle"]["enabled"],
            "uncapped": uncapped, "total_cap_usd": round(sum(i["cap_usd"] or 0 for i in items), 2),
            "total_spent_usd": round(sum(i["spent_usd"] for i in items), 4), "budgets": items}


def set_cap(conn, name: str, actor: str, *, usd=None, calls=None, clear: bool = False, now: datetime | None = None) -> dict:
    """Change a purpose's weekly cap (the settings row records who and when) and this week's plan with it, then queue again the
    jobs that waited for it. `clear` removes the standing budget: the purpose's calls then need a named plan."""
    from ..settings_store import set_value
    if name not in PURPOSES:
        raise ValueError(f"Unknown budget purpose {name}; one of {', '.join(PURPOSES)}")
    if not clear and usd is None and calls is None:
        raise ValueError("Give --weekly-usd, --weekly-calls or --clear")
    now = now or datetime.now(UTC)
    changed = []
    if clear or usd is not None:
        changed.append(set_value(conn, f"budgets.weekly_usd.{name}", None if clear else usd, actor))
    if calls is not None:
        changed.append(set_value(conn, f"budgets.weekly_calls.{name}", calls, actor))
    cap = caps(conn)[name]
    start, _ = week_of(now)
    row = conn.execute("SELECT * FROM run_plans WHERE plan_id=%s FOR UPDATE", (plan_id(name, start),)).fetchone()
    if row and cap["usd"] is None:
        conn.execute("""UPDATE run_plans SET status='closed',closed_at=now(),closed_reason=%s WHERE plan_id=%s AND status IN
            ('active','exhausted')""", (f"standing budget removed by {actor}", row["plan_id"]))
    elif row:
        calls_cap = max(int(cap["calls"]), int(row["calls_used"]))
        room = Decimal(str(row["cost_used_usd"])) < Decimal(str(cap["usd"])) and row["calls_used"] < calls_cap
        details = {**row["details"], "cap_set_by": actor, "cap_source": "settings (table)"}
        conn.execute("""UPDATE run_plans SET max_cost_usd=%s,max_calls=%s,approver=%s,details=%s,
            status=CASE WHEN status IN ('active','exhausted') THEN (CASE WHEN %s THEN 'active' ELSE 'exhausted' END) ELSE status END,
            closed_reason=CASE WHEN %s AND status IN ('active','exhausted') THEN NULL ELSE closed_reason END WHERE plan_id=%s""",
                     (cap["usd"], calls_cap, actor if "@" in actor else row["approver"], json.dumps(details), room, room, row["plan_id"]))
    else:
        ensure(conn, name, now, cap=cap)
    released = release_waits(conn, now, purposes=[name])
    return {"changed": changed, "released_jobs": released, **next(i for i in status(conn, now)["budgets"] if i["purpose"] == name)}
