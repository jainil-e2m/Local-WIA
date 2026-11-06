"""The cost summary (plan 6.B7): what the model and embedding calls cost, per budget week, by stage, by model and provider and
by budget purpose, behind `GET /storage/costs` and `storage_cli costs`.

It reads the recorded cost and nothing else: `llm_runs.cost_usd`, the cost the provider reported for the call (written by the
run-plan store or `llm/runs.py`; a replayed call records 0, a refused one none), and `external_calls.cost_usd` for the paid
services that are not model calls (the table may be empty). No second price list and no estimate: a call sent to a provider
whose cost was never recorded (a `sent` row whose answer was lost, a provider that reported none) is counted as an unknown
cost, never as zero. Calls the offline fake provider answered are not sent anywhere and carry no cost.

- **The window** is [from, to), default the last eight budget weeks: from Monday 00:00 UTC seven weeks before this week's
  Monday to the next Monday (`llm/standing.week_of`, the week the standing budgets and the internal key's allowance use).
- **A budget purpose** is the one whose plan paid for the call (a standing plan's `budget_purpose`, so a brief's query
  embedding counts as briefs, as the budget did), else the purpose of its stage (`standing.STAGE_PURPOSE`), else `other`
  (a named run plan or an unplanned call of a stage no purpose owns).
- **Embedding runs** are model calls of stage `embedding` and are in every view.

Read only (one read-only transaction); no model call. `report`, behind the costs page, counts nothing before
`costs.count_from` (the moment production was handed over; earlier calls were the team's own tests): its window starts
there at the earliest, and it adds the running total since then and each content pack run's cost from its own call
records (`pack_costs`).
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from . import standing

WEEKS = 8
# A call that went to a provider; refused and replayed calls did not.
SENT = ("sent", "succeeded", "failed")


def window(start: datetime | None = None, end: datetime | None = None, now: datetime | None = None) -> tuple[datetime, datetime]:
    """[start, end) in UTC: the given bounds (a bound without a zone is UTC), else the last eight budget weeks."""
    current, following = standing.week_of(now or datetime.now(UTC))
    start = _utc(start) if start else current - timedelta(weeks=WEEKS - 1)
    end = _utc(end) if end else following
    if end <= start:
        from ..errors import NeedsInput
        raise NeedsInput("The window's end must come after its start")
    return start, end


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _purpose(plan_purpose: str | None, stage: str) -> str:
    return plan_purpose or standing.STAGE_PURPOSE.get(stage) or "other"


class _Tally:
    """Calls, recorded USD (exact decimals), unknown costs and tokens for one group."""

    def __init__(self):
        self.calls = self.unknown = self.input_tokens = self.output_tokens = 0
        self.usd = Decimal(0)

    def add(self, row: dict):
        self.calls += row["calls"]
        self.unknown += row["unknown"]
        self.usd += Decimal(str(row["usd"]))
        self.input_tokens += row["input_tokens"]
        self.output_tokens += row["output_tokens"]

    def view(self, **keys) -> dict:
        return {**keys, "usd": float(round(self.usd, 6)), "calls": self.calls, "unknown_cost_calls": self.unknown,
                "input_tokens": self.input_tokens, "output_tokens": self.output_tokens}


def _views(rows: list[dict]) -> dict:
    """The groups of a set of aggregated rows: by stage, by model and provider, by budget purpose; biggest spend first."""
    stages, models, purposes, total = defaultdict(_Tally), defaultdict(_Tally), defaultdict(_Tally), _Tally()
    for r in rows:
        stages[r["stage"]].add(r)
        models[(r["model"], r["provider"])].add(r)
        purposes[_purpose(r["plan_purpose"], r["stage"])].add(r)
        total.add(r)

    def ordered(groups, build):
        return [build(k, t) for k, t in sorted(groups.items(), key=lambda kt: (-kt[1].usd, -kt[1].calls, str(kt[0])))]
    return {**total.view(),
            "by_stage": ordered(stages, lambda k, t: t.view(stage=k)),
            "by_model": ordered(models, lambda k, t: t.view(model=k[0], provider=k[1])),
            "by_purpose": ordered(purposes, lambda k, t: t.view(purpose=k, label=standing.LABELS.get(k, k)))}


def summary(conn, start: datetime | None = None, end: datetime | None = None, *, now: datetime | None = None) -> dict:
    """The cost summary over the window: totals and groups for the whole window and for each budget week in it."""
    start, end = window(start, end, now)
    rows = conn.execute("""SELECT date_trunc('week', r.created_at AT TIME ZONE 'UTC') AS week, r.stage, r.model,
            r.provider, p.details->>'budget_purpose' AS plan_purpose, count(*) AS calls,
            coalesce(sum(r.cost_usd), 0) AS usd,
            count(*) FILTER (WHERE r.cost_usd IS NULL AND r.status = ANY(%(sent)s) AND r.routing_policy <> 'offline-fake') AS unknown,
            coalesce(sum(r.input_tokens), 0) AS input_tokens, coalesce(sum(r.output_tokens), 0) AS output_tokens
        FROM llm_runs r LEFT JOIN run_plans p ON p.plan_id = r.plan_id
        WHERE r.created_at >= %(start)s AND r.created_at < %(end)s
        GROUP BY 1, 2, 3, 4, 5""", {"start": start, "end": end, "sent": list(SENT)}).fetchall()
    statuses = {r["status"]: r["n"] for r in conn.execute("""SELECT status, count(*) AS n FROM llm_runs
        WHERE created_at >= %s AND created_at < %s GROUP BY status ORDER BY status""", (start, end))}
    external = conn.execute("""SELECT date_trunc('week', created_at AT TIME ZONE 'UTC') AS week, service, operation,
            count(*) AS calls, coalesce(sum(cost_usd), 0) AS usd, count(*) FILTER (WHERE cost_usd IS NULL) AS unknown
        FROM external_calls WHERE created_at >= %s AND created_at < %s GROUP BY 1, 2, 3 ORDER BY 2, 3""", (start, end)).fetchall()
    by_week = defaultdict(list)
    for r in rows:
        by_week[r["week"]].append(r)
    weeks = []
    first, _ = standing.week_of(start)
    monday = first
    while monday < end:
        key = monday.replace(tzinfo=None)
        spent = sum((Decimal(str(e["usd"])) for e in external if e["week"] == key), Decimal(0))
        weeks.append({"week_start": monday.isoformat(), "week_end": (monday + timedelta(days=7)).isoformat(),
                      **_views(by_week.get(key, [])), "external_usd": float(round(spent, 6))})
        monday += timedelta(days=7)
    services = defaultdict(lambda: {"calls": 0, "usd": Decimal(0), "unknown": 0})
    for e in external:
        s = services[(e["service"], e["operation"])]
        s["calls"] += e["calls"]
        s["usd"] += Decimal(str(e["usd"]))
        s["unknown"] += e["unknown"]
    external_total = sum((s["usd"] for s in services.values()), Decimal(0))
    models = _views(rows)
    return {
        "window": {"start": start.isoformat(), "end": end.isoformat()}, "currency": "USD",
        "total_usd": float(round(Decimal(str(models["usd"])) + external_total, 6)),
        "models": models, "by_status": statuses,
        "external": {"calls": sum(s["calls"] for s in services.values()), "usd": float(round(external_total, 6)),
                     "by_service": [{"service": k[0], "operation": k[1], "calls": s["calls"], "usd": float(round(s["usd"], 6)),
                                     "unknown_cost_calls": s["unknown"]} for k, s in sorted(services.items())]},
        "weeks": weeks,
        "note": ("Recorded cost only (llm_runs.cost_usd, external_calls.cost_usd): a call sent to a provider without a recorded "
                 "cost is an unknown cost, not zero; replayed calls cost nothing; refused calls were not sent."),
    }


def count_from(conn) -> datetime | None:
    """`costs.count_from` in UTC: a moment (`2026-10-27T17:45:00Z`; one without a zone is UTC) or a day (from 00:00 UTC);
    None when it is blank or neither."""
    from ..settings_store import value
    raw = value("costs.count_from", conn)
    try:
        return _utc(datetime.fromisoformat(raw.replace("Z", "+00:00"))) if raw else None
    except ValueError:
        return None


def since(conn) -> dict | None:
    """Everything recorded since `costs.count_from`: model and embedding calls sent to a provider and other paid services."""
    start = count_from(conn)
    if start is None:
        return None
    row = conn.execute("""SELECT count(*) AS calls, coalesce(sum(cost_usd), 0) AS usd,
            count(*) FILTER (WHERE cost_usd IS NULL) AS unknown
        FROM llm_runs WHERE created_at >= %(start)s AND status = ANY(%(sent)s) AND routing_policy <> 'offline-fake'""",
                       {"start": start, "sent": list(SENT)}).fetchone()
    external = conn.execute("SELECT coalesce(sum(cost_usd), 0) AS usd FROM external_calls WHERE created_at >= %s",
                            (start,)).fetchone()
    return {"start": start.isoformat(), "usd": float(round(Decimal(str(row["usd"])) + Decimal(str(external["usd"])), 6)),
            "calls": row["calls"], "unknown_cost_calls": row["unknown"]}


def pack_runs(conn, start: datetime | None = None) -> list[dict]:
    """Every content pack run started at or after `start` (all of them without one), newest first, with the pack it made."""
    return conn.execute("""SELECT r.run_id, r.status, r.created_at, p.pack_id, p.title, p.week_id, p.supersedes_id
        FROM pipeline_runs r LEFT JOIN content_packs p ON p.pack_id = r.input_refs->>'pack_id'
        WHERE r.run_scope = 'pack_generation' AND (%(start)s::timestamptz IS NULL OR r.created_at >= %(start)s)
        ORDER BY r.created_at DESC, r.run_id""", {"start": start}).fetchall()


def _sum(values) -> float:
    return float(round(sum((Decimal(str(v)) for v in values if v is not None), Decimal(0)), 6))


def pack_costs(store, runs: list[dict]) -> list[dict]:
    """Each content pack run's cost from its own call records (`pack-runs/<run>/cost_summary.json`, `costs.call_record`):
    the cost the model provider reported for every call the run sent, with the provider's generation id; never an estimate.
    A call answered from a saved earlier answer is no new charge here: its originally reported cost is kept apart. An attempt
    with neither a generation id nor a cost was never answered by the provider (the record is written before the call is
    sent, so a call refused before sending, by a budget or a size check, leaves one): it is not a call and costs nothing."""
    out = []
    for run in runs:
        path = f"pack-runs/{run['run_id']}/cost_summary.json"
        try:
            summary = store.read_json(path) if store.exists(path) else None
        except Exception:  # noqa: BLE001 - one unreadable record never hides the other packs
            summary = None
        calls = [c for stage in (summary or {}).get("stages", []) for c in stage.get("calls", [])]
        sent = [c for c in calls if c.get("dispatched") and not c.get("reused")
                and (c.get("generation_id") or c.get("new_cost_usd") is not None)]
        reused = [c for c in calls if c.get("reused")]
        out.append({"run_id": run["run_id"], "pack_id": run["pack_id"], "title": run["title"], "week_id": run["week_id"],
                    "made_at": run["created_at"].isoformat(), "made_again": run["supersedes_id"] is not None,
                    "status": run["status"], "recorded": summary is not None,
                    "usd": _sum(c.get("new_cost_usd") for c in sent), "calls": len(sent),
                    "unknown_cost_calls": sum(c.get("new_cost_usd") is None for c in sent),
                    "verified_calls": sum(c.get("cost_status") == "reported" and bool(c.get("generation_id")) for c in sent),
                    "reused_calls": len(reused), "reused_original_usd": _sum(c.get("original_reported_cost_usd") for c in reused)})
    return out


def report(repo, start: datetime | None = None, end: datetime | None = None) -> dict:
    from ..artifacts import store_for
    with repo.connection() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        first = count_from(conn)
        if first is not None:
            # Nothing before the hand-over counts: a window reaching back further starts there.
            lo, hi = window(start, end)
            if first < hi:
                start = max(lo, first)
        result = summary(conn, start, end)
        result["since"] = since(conn)
        runs = pack_runs(conn, first)
    result["packs"] = pack_costs(store_for(repo.settings), runs)
    return result


# ---- the report in words (storage_cli costs) -------------------------------------------------------------------------------

def _usd(value: float) -> str:
    return f"USD {value:.4f}"


def _group(lines: list[str], title: str, items: list[dict], name) -> None:
    lines.append(title)
    if not items:
        lines.append("- none")
    for i in items:
        unknown = f", {i['unknown_cost_calls']} with no recorded cost" if i["unknown_cost_calls"] else ""
        lines.append(f"- {name(i)}: {_usd(i['usd'])} over {i['calls']} calls{unknown}")


def text(s: dict) -> str:
    m = s["models"]
    lines = [f"Costs from {s['window']['start'][:10]} to {s['window']['end'][:10]} (budget weeks start Monday 00:00 UTC): "
             f"{_usd(s['total_usd'])} in all", s["note"], "",
             f"Model and embedding calls: {_usd(m['usd'])} over {m['calls']} calls"
             + (f" ({m['unknown_cost_calls']} with no recorded cost)" if m["unknown_cost_calls"] else ""),
             "By status: " + (", ".join(f"{k} {v}" for k, v in s["by_status"].items()) or "no calls"), ""]
    _group(lines, "By budget purpose", m["by_purpose"], lambda i: i["label"])
    _group(lines, "By stage", m["by_stage"], lambda i: i["stage"])
    _group(lines, "By model and provider", m["by_model"], lambda i: i["model"] + (f" ({i['provider']})" if i["provider"] else ""))
    lines += ["", "Other paid services (external_calls): " + (f"{_usd(s['external']['usd'])} over {s['external']['calls']} calls"
                                                               if s["external"]["calls"] else "none recorded")]
    lines += [f"- {e['service']} {e['operation']}: {_usd(e['usd'])} over {e['calls']} calls" for e in s["external"]["by_service"]]
    lines += ["", "By week"]
    for w in s["weeks"]:
        top = ", ".join(f"{p['label']} {_usd(p['usd'])}" for p in w["by_purpose"] if p["usd"]) or "nothing spent"
        lines.append(f"- {w['week_start'][:10]}: {_usd(w['usd'] + w['external_usd'])} over {w['calls']} calls ({top})")
    return "\n".join(lines) + "\n"


def run_cli(repo, start: datetime | None, end: datetime | None, as_json: bool) -> str:
    result = report(repo, start, end)
    return json.dumps(result, indent=2, default=str) + "\n" if as_json else text(result)
