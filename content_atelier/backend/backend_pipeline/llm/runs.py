"""The `llm_runs` record: one row per model or embedding call (plan 0.B4, migration 005).

Planned (paid) calls get their row from the run-plan store, in the same transaction that counts the call, so a counted
call always has a row. Everything else is written here: a call answered from saved artifacts ("replayed"), a call the
offline fake provider answered, and a call refused before it left (no plan, plan exhausted, routing). The planned
rows are then completed with the prompt and knowledge-base versions and the call's details (`annotate`).

Writing the record never breaks a call that already happened: if the database cannot be written, the row goes to a
JSON-lines file beside the artifacts and the error is logged.
"""
from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from .routing import ROUTING_POLICY

log = logging.getLogger(__name__)

STATUSES = ("sent", "succeeded", "failed", "refused", "replayed")
FAKE_POLICY = "offline-fake"


def new_id() -> str:
    return "llm_" + uuid.uuid4().hex[:24]


def usage_of(raw) -> dict:
    """Tokens and cost a response reports, in the columns' terms."""
    usage = (raw or {}).get("usage") if isinstance(raw, dict) else None
    usage = usage if isinstance(usage, dict) else {}
    details = usage.get("prompt_tokens_details") if isinstance(usage.get("prompt_tokens_details"), dict) else {}
    cost = usage.get("cost")
    return {"input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens"),
            "cost_usd": cost if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None,
            "cached_tokens": details.get("cached_tokens"), "cache_write_tokens": details.get("cache_write_tokens"),
            "generation_id": raw.get("id") if isinstance(raw, dict) else None}


def insert_row(conn, *, call_id, plan_id=None, stage, model, fingerprint, status, routing_policy=ROUTING_POLICY, provider=None,
               prompt_version=None, knowledge_base_version=None, input_tokens=None, output_tokens=None, cost_usd=None,
               error=None, details=None):
    conn.execute("""INSERT INTO llm_runs(llm_run_id,plan_id,stage,model,provider,routing_policy,request_fingerprint,prompt_version,
        knowledge_base_version,input_tokens,output_tokens,cost_usd,status,error,details) VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                 (call_id, plan_id, stage, model, provider, routing_policy, fingerprint, prompt_version, knowledge_base_version,
                  input_tokens, output_tokens, cost_usd, status, error, json.dumps(details or {}, default=str)))


class LlmRuns:
    """Writes llm_runs rows: to the database through `connect` (a context manager yielding a connection), else to a file."""

    def __init__(self, *, connect: Callable | None = None, file: str | Path | None = None):
        self.connect = connect
        self.file = Path(file) if file else None

    @classmethod
    def for_database(cls, database_url: str | None, *, file: str | Path | None = None):
        if not database_url:
            return cls(file=file)
        from ..database import connect
        return cls(connect=lambda: connect(database_url, vectors=False), file=file)

    @classmethod
    def for_storage(cls, storage):
        """The recorder a worker or the API uses: its database, with a file beside its artifacts as the fallback."""
        return cls.for_database(storage.database_url, file=Path(storage.artifact_root) / "llm_runs.fallback.jsonl")

    def _append(self, row: dict) -> None:
        if self.file is None:
            return
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            with self.file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({**row, "at": datetime.now(UTC).isoformat()}, default=str) + "\n")
        except OSError:  # The record must never break a call that already happened (module docstring).
            log.exception("llm_runs row could not be written to %s; it is in this log only: %s", self.file,
                          json.dumps({k: row.get(k) for k in ("call_id", "stage", "model", "status", "fingerprint")}, default=str))

    def record(self, *, stage, model, fingerprint, status, call_id=None, plan_id=None, provider=None, routing_policy=ROUTING_POLICY,
               prompt_version=None, knowledge_base_version=None, raw=None, error=None, details=None, cost_usd=None) -> str:
        """One finished call (or refused attempt) in one write."""
        call_id = call_id or new_id()
        usage = usage_of(raw)
        row = dict(call_id=call_id, plan_id=plan_id, stage=stage, model=model, fingerprint=fingerprint, status=status,
                   routing_policy=routing_policy, provider=provider or (raw.get("provider") if isinstance(raw, dict) else None),
                   prompt_version=prompt_version, knowledge_base_version=knowledge_base_version,
                   input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"],
                   cost_usd=cost_usd if cost_usd is not None else usage["cost_usd"], error=error,
                   details={**(details or {}), **{k: usage[k] for k in ("cached_tokens", "cache_write_tokens") if usage[k] is not None},
                            **({"generation_id": usage["generation_id"]} if usage["generation_id"] else {})})
        if self.connect is not None:
            try:
                with self.connect() as conn:
                    insert_row(conn, **row)
                    conn.commit()
                return call_id
            except Exception:  # The call already happened; its record must not be lost or break the run.
                log.exception("llm_runs could not be written to the database; keeping the row in the fallback file")
        self._append({**row, "event": "record"})
        return call_id

    def annotate(self, call_id: str, *, prompt_version=None, knowledge_base_version=None, details=None) -> None:
        """Complete a planned call's row (written by the plan store) with what only the caller knows."""
        if self.connect is not None:
            try:
                with self.connect() as conn:
                    conn.execute("""UPDATE llm_runs SET prompt_version=COALESCE(%s,prompt_version),
                        knowledge_base_version=COALESCE(%s,knowledge_base_version),details=details||%s::jsonb WHERE llm_run_id=%s""",
                                 (prompt_version, knowledge_base_version, json.dumps(details or {}, default=str), call_id))
                    conn.commit()
                return
            except Exception:
                log.exception("llm_runs could not be annotated; keeping the annotation in the fallback file")
        self._append({"event": "annotate", "call_id": call_id, "prompt_version": prompt_version,
                      "knowledge_base_version": knowledge_base_version, "details": details or {}})


class NoRuns(LlmRuns):
    """Records nothing: for offline tests that do not look at the record."""

    def record(self, **kwargs) -> str:
        return new_id()

    def annotate(self, *args, **kwargs) -> None:
        return None
