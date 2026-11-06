"""Returned usage is authoritative; failures and replays must not hide/double costs."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from .store import JsonStore

STAGES = ("moment_extraction", "angle_generation")

# USD per million (input, output) tokens by OpenRouter model id, for estimates made before a paid call (`moments extract
# --estimate`). Sources: Content-Atelier-Content-Quality-Analysis.md section 4.1 (Luna 0.10 / 0.50, Sol 2.00 / 10.00) and the
# Feasibility Study's Sonnet-class rate (2 / 10), checked 18 October 2026. Hosted usage is authoritative; an estimate is
# never a charge. A model absent here has no estimate unless the settings give `moments.estimate.*_usd_per_million`.
MODEL_PRICES_USD_PER_MILLION = {
    "openai/gpt-6-luna": (0.10, 0.50),
    "openai/gpt-6.1-sol": (2.00, 10.00),
    "anthropic/claude-sonnet-5.5": (2.00, 10.00),
    # The pack finisher (NP.B5), at OpenRouter's listed price: its worst case is refused before sending and estimates work.
    "anthropic/claude-opus-5.5": (4.00, 20.00),
}


def price_of(model: str, *, input_override: float | None = None, output_override: float | None = None) -> tuple[float, float] | None:
    """(input, output) USD per million tokens: the settings' override where given, else the table, else None."""
    known = MODEL_PRICES_USD_PER_MILLION.get(model)
    price_in = input_override if input_override is not None else (known[0] if known else None)
    price_out = output_override if output_override is not None else (known[1] if known else None)
    return (price_in, price_out) if price_in is not None and price_out is not None else None


def estimate_usd(model: str, input_tokens: int, output_tokens: int, **overrides) -> float | None:
    price = price_of(model, **overrides)
    if price is None:
        return None
    return round(input_tokens / 1_000_000 * price[0] + output_tokens / 1_000_000 * price[1], 4)


def response_usage(raw) -> dict | None:
    usage = raw.get("usage") if isinstance(raw, dict) else None
    return usage if isinstance(usage, dict) else None


def reported_cost(raw: dict | None) -> float | None:
    value = (response_usage(raw) or {}).get("cost")
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return float(number) if number.is_finite() and number >= 0 else None


def call_record(*, raw: dict | None = None, dispatched: bool = False, reused: bool = False, **identity) -> dict:
    cost = reported_cost(raw)
    envelope = raw if isinstance(raw, dict) else {}
    return {
        **identity,
        "currency": "USD",
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "dispatched": dispatched,
        "reused": reused,
        "generation_id": envelope.get("id"),
        "returned_model_id": envelope.get("model"),
        "provider": envelope.get("provider"),
        "usage": response_usage(raw),
        "original_reported_cost_usd": cost,
        "new_cost_usd": 0.0 if reused or not dispatched else cost,
        "cost_status": "reused_no_new_charge"
        if reused
        else "not_sent"
        if not dispatched
        else "reported"
        if cost is not None
        else "unknown",
        "cost_source": "provider_usage.cost" if cost is not None else None,
        "credit_purchase_fees_included": False,
    }


def write_run_summary(store: JsonStore, run_dir: str, *, stages_to_report=None) -> dict:
    records = [store.read_json(key) for key in store.json_names(f"{run_dir}/costs")]
    stages = []
    for stage in stages_to_report or STAGES:
        calls = [record for record in records if record["stage"] == stage]
        known = all(record["new_cost_usd"] is not None for record in calls)
        total = sum((Decimal(str(record["new_cost_usd"])) for record in calls if record["new_cost_usd"] is not None), Decimal(0))
        stages.append(
            {
                "stage": stage,
                "status": "recorded" if calls else "not_attempted",
                "attempt_count": sum(not record["reused"] for record in calls),
                "dispatched_count": sum(record["dispatched"] and not record["reused"] for record in calls),
                "reused_count": sum(record["reused"] for record in calls),
                "known_reported_new_cost_usd": float(total),
                "new_cost_usd": float(total) if known else None,
                "all_new_costs_known": known,
                "calls": calls,
            }
        )
    known = all(stage["all_new_costs_known"] for stage in stages)
    subtotal = sum((Decimal(str(stage["known_reported_new_cost_usd"])) for stage in stages), Decimal(0))
    summary = {
        "report_run_id": run_dir.rsplit("/", 1)[-1],
        "currency": "USD",
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "stages": stages,
        "known_reported_new_cost_usd": float(subtotal),
        "total_new_cost_usd": float(subtotal) if known else None,
        "all_new_costs_known": known,
        "reasoning_is_included_in_completion_tokens": True,
        "original_reused_usage_is_not_new_billing": True,
        "credit_purchase_fees_included": False,
    }
    store.write_json(f"{run_dir}/cost_summary.json", summary, overwrite=True)
    lines = [
        "# LLM cost summary",
        "",
        f"Report: {summary['report_run_id']}",
        "",
        "| Stage | Dispatched | Reused | New reported USD cost |",
        "|---|---:|---:|---:|",
    ]
    for stage in stages:
        cost = "unknown" if stage["new_cost_usd"] is None else f"{stage['new_cost_usd']:.8f}"
        lines.append(f"| {stage['stage']} | {stage['dispatched_count']} | {stage['reused_count']} | {cost} |")
    total = "unknown (see known subtotal in JSON)" if not known else f"${summary['total_new_cost_usd']:.8f}"
    lines.extend(
        [
            "",
            f"Total new reported inference cost: {total}.",
            "",
            "Native usage and provider breakdown are retained in the JSON call records. Missing billing is unknown, not zero. Reasoning is already part of completion usage. Replayed original costs are not billed again. Credit-purchase fees are excluded.",
            "",
        ]
    )
    # Mutable report projection, atomically replaced. Requests/raw receipts stay
    # immutable; cost_summary.json is the machine-readable authority.
    store.write_text(f"{run_dir}/cost_summary.md", "\n".join(lines), overwrite=True)
    return summary
