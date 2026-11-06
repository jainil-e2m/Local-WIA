"""Run plans for tests that simulate live calls (E.B1). Real calls never happen in tests."""
from __future__ import annotations

from backend_pipeline.llm.run_plans import Ticket, write_file_plan

ALL_STAGES = ['moment_extraction', 'angle_generation', 'angle_refinement', 'brief_plan', 'brief_grade', 'brief_write',
              'brief_review', 'brief_repair', 'brief_web', 'pack_write', 'pack_review', 'embedding']


class OpenTestPlan:
    """Allows every call and records it."""

    def __init__(self):
        self.reserved, self.settled = [], []

    def reserve(self, *, stage, model, fingerprint, input_set_hash=None, worst_case_usd=None):
        ticket = Ticket('plan_test', f'llm_{len(self.reserved)}', stage, model)
        self.reserved.append(ticket)
        self.input_set_hashes = [*getattr(self, 'input_set_hashes', []), input_set_hash]
        return ticket

    def settle(self, ticket, raw, *, status, error=None):
        self.settled.append((ticket, status))


def file_plan(tmp_path, monkeypatch, *, models, stages=ALL_STAGES, max_calls=50, max_cost_usd=1.0, input_set_hash='*'):
    """A file plan named through ATELIER_RUN_PLAN_FILE, as a harness or script run would use."""
    path = tmp_path / 'run_plan.json'
    plan = write_file_plan(path, purpose='test', stages=stages, models=models, input_set_hash=input_set_hash,
                           max_calls=max_calls, max_cost_usd=max_cost_usd, approver='tester@example.invalid')
    monkeypatch.setenv('ATELIER_RUN_PLAN_FILE', str(path))
    return path, plan
