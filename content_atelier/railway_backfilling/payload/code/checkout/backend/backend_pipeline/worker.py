from __future__ import annotations

from .config import Settings
from .pipeline import Pipeline


def run_week(week_index: int, mode: str = "plan") -> dict:
    """RQ-compatible job entry point; JSON remains authoritative for this slice."""
    return Pipeline(Settings.from_env()).run(week_index, mode=mode)
