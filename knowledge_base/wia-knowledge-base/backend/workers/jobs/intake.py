"""Intake job functions. Plain functions: transport (PostgreSQL runner today, RQ later) calls them."""
from uuid import UUID

from backend.services.intake import discovery, pipeline, requalify
from backend.services.read_models import portfolio

JOBS = {
    pipeline.PAGE_JOB: pipeline.run_backfill_page,
    "client.discover": discovery.run_discover_job,
    requalify.JOB: requalify.run_job,
    portfolio.JOB: portfolio.run_job,
}


def on_permanent_failure(session, kind: str, payload: dict, error_class: str) -> None:
    if kind == pipeline.PAGE_JOB and payload.get("run_id"):
        try:
            run_id = UUID(payload["run_id"])
        except (ValueError, TypeError, AttributeError):
            return  # Fail the malformed work item, never guess which run it belongs to.
        pipeline.fail_run(run_id, error_class, session=session)
