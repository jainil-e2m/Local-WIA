"""Run plans for paid calls (plan E.B1, ruling R39).

A run plan records the stages and models it allows, the input-set hash, the maximum calls and
cost, who approved it, and when it expires. Every live model or embedding request reserves one
call against an active plan before it leaves (`LiveProvider`), and settles its cost after the
response. A real-data call outside an active plan is refused with RunPlanError.

Plans live in one of two stores:
- the `run_plans` table (migration 005), with each call as an `llm_runs` row, for the product's
  workers: the standing weekly plan of the call's purpose (6.B3, `standing.py`), found without a variable, or the plan
  `ATELIER_RUN_PLAN_ID` names for a one-off run (`ATELIER_DATABASE_URL` is the database);
- a JSON file stored beside a harness's results, with a JSON-lines call ledger next to it
  (`ATELIER_RUN_PLAN_FILE`), for the evaluation harness and one-off scripts.

The cost cap is checked before each call against the cost already spent; one call's cost can
take the plan past its cap, after which the plan is exhausted and refuses further calls.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from .routing import policy_for


class RunPlanError(PermissionError):
    """A paid call was refused: no active plan, or outside what the plan allows."""


class BudgetExhausted(RunPlanError):
    """A paid call was refused because its plan has no room left: exhausted, expired, out of calls, or the call could pass
    the cost cap (E.B1's check before sending). A standing weekly budget (6.B3) names its purpose, so a job can wait for the
    budget to renew or be raised instead of failing."""

    def __init__(self, message: str, *, purpose: str | None = None, plan_id: str | None = None,
                 left_usd: float | None = None):
        super().__init__(message)
        self.purpose, self.plan_id, self.left_usd = purpose, plan_id, left_usd


@dataclass(frozen=True)
class Ticket:
    plan_id: str
    call_id: str
    stage: str
    model: str


def response_cost(raw) -> float:
    usage = (raw or {}).get('usage') or {} if isinstance(raw, dict) else {}
    try:
        return float(usage.get('cost') or 0)
    except (TypeError, ValueError):
        return 0.0


def _tokens(raw):
    usage = (raw or {}).get('usage') or {} if isinstance(raw, dict) else {}
    return usage.get('prompt_tokens'), usage.get('completion_tokens')


class PlanStore(Protocol):
    def reserve(self, *, stage: str, model: str, fingerprint: str, input_set_hash: str | None = None,
                worst_case_usd: float | None = None) -> Ticket: ...
    def settle(self, ticket: Ticket, raw, *, status: str, error: str | None = None) -> None: ...


ANY_INPUT = "*"
# A standing plan (6.B3) covers whatever models the settings name this week; its cap is the guard.
ANY_MODEL = "*"
# Characters per token for a request's worst case: below every model's measured ratio (GPT-6.1 Sol 3.98, Claude Sonnet
# 5.5 2.79, E.B23's dry run), so the estimate errs high.
WORST_CASE_CHARS_PER_TOKEN = 2.5


def worst_case_usd(model: str, body: dict) -> float | None:
    """What one request could cost at most: its whole body as input tokens and its output cap (`max_tokens`) as output,
    at the model's listed price; None when the price is unknown (the cap then applies after the call, as before)."""
    from ..costs import price_of
    price = price_of(model)
    if price is None:
        return None
    output = body.get("max_tokens") or body.get("max_completion_tokens") or 0
    input_tokens = len(json.dumps(body, ensure_ascii=False)) / WORST_CASE_CHARS_PER_TOKEN
    return round(input_tokens / 1_000_000 * price[0] + output / 1_000_000 * price[1], 6)


def check_allowed(plan: dict, *, stage: str, model: str, now: datetime, input_set_hash: str | None = None,
                  worst_case_usd: float | None = None) -> None:
    """The rules every store applies before a call (E.B1). A plan approved for one input set refuses a run over
    another; a plan created with input set "*" covers any (S.B2 review)."""
    if plan['status'] != 'active':
        error = BudgetExhausted if plan['status'] in ('exhausted', 'expired') else RunPlanError
        raise error(f"Run plan {plan['plan_id']} is {plan['status']}; no further paid calls")
    expires = plan['expires_at']
    if isinstance(expires, str):
        expires = datetime.fromisoformat(expires)
    if now >= expires:
        raise BudgetExhausted(f"Run plan {plan['plan_id']} expired at {expires.isoformat()}")
    if stage not in plan['stages']:
        raise RunPlanError(f"Run plan {plan['plan_id']} does not cover stage {stage}")
    if model not in plan['models'] and ANY_MODEL not in plan['models']:
        raise RunPlanError(f"Run plan {plan['plan_id']} does not cover model {model}")
    bound = plan.get('input_set_hash') not in (None, ANY_INPUT)
    if input_set_hash and bound and plan['input_set_hash'] != input_set_hash:
        raise RunPlanError(f"Run plan {plan['plan_id']} was approved for another input set; create a plan for this run")
    if bound and not input_set_hash:
        # A plan approved for one input set is spent only by calls that name it; a caller that cannot (a brief, a
        # harness, the learning loop) runs under a plan created for any input set ("*"), recorded as such.
        raise RunPlanError(f"Run plan {plan['plan_id']} is bound to input set {plan['input_set_hash']}, and this call "
                           "names no input set; create a plan with --input-set-hash '*' for it")
    if plan['calls_used'] >= plan['max_calls']:
        raise BudgetExhausted(f"Run plan {plan['plan_id']} has used all {plan['max_calls']} calls")
    if Decimal(str(plan['cost_used_usd'])) >= Decimal(str(plan['max_cost_usd'])):
        raise BudgetExhausted(f"Run plan {plan['plan_id']} reached its cost cap of USD {plan['max_cost_usd']}")
    # The cap holds for the call itself: one whose worst case (its input plus its full output cap) would pass the cap is
    # refused before it is sent, not after it has spent (S.B8, 20 October: a USD 0.33 plan ended at USD 0.41).
    if worst_case_usd and Decimal(str(plan['cost_used_usd'])) + Decimal(str(worst_case_usd)) > Decimal(str(plan['max_cost_usd'])):
        raise BudgetExhausted(f"Run plan {plan['plan_id']}: this call could cost up to USD {worst_case_usd:.4f}, more than the "
                           f"USD {Decimal(str(plan['max_cost_usd'])) - Decimal(str(plan['cost_used_usd']))} left under its cap")


class NoPlan:
    """The default: every real-data call is refused until a plan is named."""

    def reserve(self, *, stage, model, fingerprint, input_set_hash=None, worst_case_usd=None):
        raise RunPlanError('A real-data model call needs an active run plan (plan E.B1). Create one with '
                           '`storage_cli plan create` and set ATELIER_RUN_PLAN_ID, or set ATELIER_RUN_PLAN_FILE '
                           'for a harness run.')

    def settle(self, ticket, raw, *, status, error=None):  # pragma: no cover - never reserved
        raise RunPlanError('No run plan')


class SqlPlanStore:
    def __init__(self, database_url: str, plan_id: str):
        self.database_url, self.plan_id = database_url, plan_id

    def _connect(self):
        from ..database import connect
        return connect(self.database_url, vectors=False)

    def reserve(self, *, stage, model, fingerprint, input_set_hash=None, worst_case_usd=None):
        with self._connect() as conn:
            plan = conn.execute('SELECT * FROM run_plans WHERE plan_id=%s FOR UPDATE', (self.plan_id,)).fetchone()
            if not plan:
                raise RunPlanError(f'Run plan {self.plan_id} does not exist')
            check_allowed(plan, stage=stage, model=model, now=datetime.now(UTC), input_set_hash=input_set_hash,
                          worst_case_usd=worst_case_usd)
            call_id = 'llm_' + uuid.uuid4().hex[:24]
            used = conn.execute('UPDATE run_plans SET calls_used=calls_used+1 WHERE plan_id=%s RETURNING calls_used,max_calls',
                                (self.plan_id,)).fetchone()
            conn.execute("""INSERT INTO llm_runs(llm_run_id,plan_id,stage,model,routing_policy,request_fingerprint,status)
                VALUES (%s,%s,%s,%s,%s,%s,'sent')""", (call_id, self.plan_id, stage, model, policy_for(model), fingerprint))
            if used['calls_used'] >= used['max_calls']:
                conn.execute("UPDATE run_plans SET status='exhausted',closed_reason='call limit reached' WHERE plan_id=%s",
                             (self.plan_id,))
                # The reserved call still goes ahead; the plan refuses the next one.
            return Ticket(self.plan_id, call_id, stage, model)

    def settle(self, ticket, raw, *, status, error=None):
        cost = response_cost(raw)
        prompt, completion = _tokens(raw)
        provider = raw.get('provider') if isinstance(raw, dict) else None
        with self._connect() as conn:
            conn.execute("""UPDATE llm_runs SET status=%s,cost_usd=%s,input_tokens=%s,output_tokens=%s,provider=%s,error=%s
                WHERE llm_run_id=%s""", (status, cost, prompt, completion, provider, error, ticket.call_id))
            plan = conn.execute("""UPDATE run_plans SET cost_used_usd=cost_used_usd+%s WHERE plan_id=%s
                RETURNING cost_used_usd,max_cost_usd,status""", (cost, ticket.plan_id)).fetchone()
            if plan and plan['status'] == 'active' and plan['cost_used_usd'] >= plan['max_cost_usd']:
                conn.execute("UPDATE run_plans SET status='exhausted',closed_reason='cost cap reached' WHERE plan_id=%s",
                             (ticket.plan_id,))


class FilePlanStore:
    """A plan stored beside a harness's results: plan JSON plus a JSON-lines ledger of its calls."""

    _lock = threading.Lock()

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.ledger = self.path.with_suffix('.calls.jsonl')

    def _read(self):
        if not self.path.is_file():
            raise RunPlanError(f'Run plan file {self.path} does not exist')
        return json.loads(self.path.read_text(encoding='utf-8'))

    def _write(self, plan):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(plan, indent=2, default=str) + '\n', encoding='utf-8')
        os.replace(tmp, self.path)

    def _log(self, record):
        with self.ledger.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(record, default=str) + '\n')

    def reserve(self, *, stage, model, fingerprint, input_set_hash=None, worst_case_usd=None):
        with self._lock:
            plan = self._read()
            check_allowed(plan, stage=stage, model=model, now=datetime.now(UTC), input_set_hash=input_set_hash,
                          worst_case_usd=worst_case_usd)
            plan['calls_used'] += 1
            if plan['calls_used'] >= plan['max_calls']:
                plan['status'], plan['closed_reason'] = 'exhausted', 'call limit reached'
            self._write(plan)
            ticket = Ticket(plan['plan_id'], 'llm_' + uuid.uuid4().hex[:24], stage, model)
            self._log({'call_id': ticket.call_id, 'event': 'sent', 'stage': stage, 'model': model,
                       'fingerprint': fingerprint, 'routing_policy': policy_for(model), 'at': datetime.now(UTC).isoformat()})
            return ticket

    def settle(self, ticket, raw, *, status, error=None):
        cost = response_cost(raw)
        with self._lock:
            plan = self._read()
            plan['cost_used_usd'] = float(Decimal(str(plan['cost_used_usd'])) + Decimal(str(cost)))
            if plan['status'] == 'active' and plan['cost_used_usd'] >= plan['max_cost_usd']:
                plan['status'], plan['closed_reason'] = 'exhausted', 'cost cap reached'
            self._write(plan)
            self._log({'call_id': ticket.call_id, 'event': status, 'cost_usd': cost, 'error': error,
                       'at': datetime.now(UTC).isoformat()})

    def annotate(self, call_id, *, prompt_version=None, knowledge_base_version=None, details=None):
        """What only the caller knows about a call (the prompt and knowledge-base versions), in the ledger."""
        with self._lock:
            self._log({'call_id': call_id, 'event': 'annotate', 'prompt_version': prompt_version,
                       'knowledge_base_version': knowledge_base_version, 'details': details or {},
                       'at': datetime.now(UTC).isoformat()})

    def show(self):
        calls = [json.loads(line) for line in self.ledger.read_text(encoding='utf-8').splitlines() if line.strip()]             if self.ledger.is_file() else []
        return {'plan': self._read(), 'calls': calls}

    def close(self, reason):
        """Ends an active plan: no further paid calls under it."""
        with self._lock:
            plan = self._read()
            if plan['status'] != 'active':
                return {'error': f"plan {plan['plan_id']} is already {plan['status']}"}
            plan.update(status='closed', closed_reason=reason, closed_at=datetime.now(UTC).isoformat())
            self._write(plan)
            return {'plan_id': plan['plan_id'], 'status': 'closed'}


def new_plan(*, purpose, stages, models, input_set_hash, max_calls, max_cost_usd, approver, hours=24, details=None):
    if not approver or '@' not in approver:
        raise ValueError('A run plan needs the approver\'s email')
    if max_calls < 1 or max_cost_usd <= 0:
        raise ValueError('A run plan needs a positive call limit and cost cap')
    now = datetime.now(UTC)
    return {'plan_id': 'plan_' + uuid.uuid4().hex[:20], 'purpose': purpose, 'stages': list(stages), 'models': list(models),
            'input_set_hash': input_set_hash, 'max_calls': int(max_calls), 'max_cost_usd': float(max_cost_usd),
            'approver': approver, 'approved_at': now.isoformat(), 'expires_at': (now + timedelta(hours=hours)).isoformat(),
            'status': 'active', 'calls_used': 0, 'cost_used_usd': 0.0, 'details': details or {}}


def write_file_plan(path, **fields):
    plan = new_plan(**fields)
    path = Path(path)
    if path.exists():
        raise ValueError(f'{path} exists; a plan is never overwritten')
    path.parent.mkdir(parents=True, exist_ok=True)
    FilePlanStore(path)._write(plan)
    return plan


def create_sql_plan(conn, **fields):
    plan = new_plan(**fields)
    conn.execute("""INSERT INTO run_plans(plan_id,purpose,stages,models,input_set_hash,max_calls,max_cost_usd,approver,
        approved_at,expires_at,details) VALUES (%(plan_id)s,%(purpose)s,%(stages)s,%(models)s,%(input_set_hash)s,
        %(max_calls)s,%(max_cost_usd)s,%(approver)s,%(approved_at)s,%(expires_at)s,%(details)s)""",
                 {**plan, 'details': json.dumps(plan['details'])})
    return plan


def from_environment(default_file: str | Path | None = None) -> PlanStore:
    """The store a live provider uses: ATELIER_RUN_PLAN_ID (database), ATELIER_RUN_PLAN_FILE, a harness's
    default plan file when it exists, then the standing weekly budgets of the database (6.B3: the plan is found per call,
    by the call's purpose, with no variable), or NoPlan, which refuses. A named plan is the explicit override for a one-off
    run (a backlog import, a benchmark)."""
    if os.getenv('ATELIER_RUN_PLAN_ID'):
        url = os.getenv('ATELIER_DATABASE_URL')
        if not url:
            raise RunPlanError('ATELIER_RUN_PLAN_ID needs ATELIER_DATABASE_URL')
        return SqlPlanStore(url, os.environ['ATELIER_RUN_PLAN_ID'])
    if os.getenv('ATELIER_RUN_PLAN_FILE'):
        return FilePlanStore(os.environ['ATELIER_RUN_PLAN_FILE'])
    if default_file and Path(default_file).is_file():
        return FilePlanStore(default_file)
    if os.getenv('ATELIER_DATABASE_URL'):
        from .standing import StandingPlanStore
        return StandingPlanStore(os.environ['ATELIER_DATABASE_URL'])
    return NoPlan()
