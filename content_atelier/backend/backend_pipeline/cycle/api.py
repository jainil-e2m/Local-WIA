"""Routes for a cycle over a date window (3.B2/3.B3), the standing budgets (6.B3), the cost summary (6.B7) and the week's
review document (5.B14, as Markdown and as a Word file).

Starting a cycle and previewing it are an approver's (the preview computes the estimate a start is made on); the cycle list,
one cycle, the budgets, the costs and the review document are reads for anyone the API admits.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from ..api_models import Loose, StrategyBrief, returns


class CycleDocument(Loose):
    transcript_id: str
    title: str | None = None
    occurred_at: datetime | None = None
    call_type: str | None = None
    extraction_status: str | None = None
    # window, late_arrival (O25: it arrived after its own window's cycle), undated or added_by_person
    selected_because: str
    missed_window: dict | None = None


class EstimateComponent(Loose):
    stage: str
    model: str | None = None
    calls: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    usd: float | None = None


class CycleEstimate(Loose):
    total_usd: float
    components: list[EstimateComponent]
    documents_to_extract: int
    scenes_in_ledger: int
    notes: list[str] = []
    assumptions: str
    note: str


class StandingBudget(Loose):
    purpose: str
    label: str
    enabled: bool
    cap_usd: float | None = None
    cap_calls: int | None = None
    cap_source: str
    # budgets.uncapped: no weekly cap binds; cap_usd is null and only what is spent is shown.
    uncapped: bool = False
    set_by: str | None = None
    status: str
    spent_usd: float
    calls_used: int
    left_usd: float
    waiting_jobs: int


class StandingBudgets(Loose):
    week_start: str
    week_end: str
    enabled: bool
    uncapped: bool = False
    total_cap_usd: float
    total_spent_usd: float
    budgets: list[StandingBudget]


class CycleWindow(Loose):
    start: str
    end: str


class CostGroup(Loose):
    """One group of recorded cost (6.B7): a stage, a model and provider, or a budget purpose (with its label)."""
    usd: float
    calls: int
    # Calls sent to a provider whose cost was never recorded: unknown, not zero.
    unknown_cost_calls: int
    input_tokens: int
    output_tokens: int
    stage: str | None = None
    model: str | None = None
    provider: str | None = None
    purpose: str | None = None
    label: str | None = None


class CostTotals(Loose):
    usd: float
    calls: int
    unknown_cost_calls: int
    input_tokens: int
    output_tokens: int
    by_stage: list[CostGroup]
    by_model: list[CostGroup]
    by_purpose: list[CostGroup]


class CostWeek(CostTotals):
    week_start: str
    week_end: str
    external_usd: float


class ExternalCost(Loose):
    service: str
    operation: str
    calls: int
    usd: float
    unknown_cost_calls: int


class ExternalCosts(Loose):
    calls: int
    usd: float
    by_service: list[ExternalCost]


class CostSince(Loose):
    """What was spent from `costs.count_from` (00:00 UTC of that day) to now."""
    start: str
    usd: float
    calls: int
    unknown_cost_calls: int


class PackCost(Loose):
    """One content pack run's cost from its own call records: what the provider reported for each call it sent."""
    run_id: str
    pack_id: str | None = None
    title: str | None = None
    week_id: str | None = None
    made_at: str
    made_again: bool
    status: str
    recorded: bool
    usd: float
    calls: int
    unknown_cost_calls: int
    verified_calls: int
    reused_calls: int
    reused_original_usd: float


class CostSummary(Loose):
    """GET /costs (6.B7): the recorded cost of model and embedding calls (`models`) and other paid services (`external`) over
    a window of budget weeks, in all and per week."""
    window: CycleWindow
    currency: str
    total_usd: float
    models: CostTotals
    by_status: dict[str, int]
    external: ExternalCosts
    weeks: list[CostWeek]
    note: str
    since: CostSince | None = None
    packs: list[PackCost] = []


class CyclePreview(Loose):
    window: CycleWindow
    document_count: int
    documents: list[CycleDocument]
    late_arrivals: list[CycleDocument]
    undated: list[CycleDocument]
    earlier_cycles: list[dict]
    estimate: CycleEstimate | None = None
    budgets: list[StandingBudget]
    within_budget: bool
    selection_hash: str
    # The strategy brief a cycle started now would be given (E.B28); the run freezes its own at submit.
    strategy_brief: StrategyBrief | dict | None = None


class CycleSummary(Loose):
    run_id: str
    week_id: str
    status: str
    message: str | None = None
    error_summary: str | None = None
    created_at: datetime
    started_by: str | None = None
    mode: str | None = None
    window: CycleWindow | None = None
    document_count: int
    estimate_usd: float | None = None
    # not_extracted, extracted, complete (every verified scene sent or held for consent) or incomplete
    coverage_state: str
    scenes_sent: int | None = None
    scenes_verified: int | None = None
    # The hash of the strategy brief frozen with the cycle (E.B28).
    strategy_brief_hash: str | None = None


class CoverageDocument(Loose):
    transcript_id: str
    verified: int
    unverified: int | None = None
    sent: int | None = None
    held_for_consent: int | None = None
    not_sent: list[str] = []


class SceneCoverage(Loose):
    state: str
    verified: int | None = None
    sent: int | None = None
    held_for_consent: int | None = None
    not_sent: list[str] = []
    documents: list[CoverageDocument]


class CycleStage(Loose):
    job_id: str
    stage: str
    status: str
    current_message: str | None = None
    error_summary: str | None = None


class CycleDetail(CycleSummary):
    estimate: CycleEstimate | None = None
    waiting_reason: str | None = None
    documents: list[CycleDocument]
    scene_coverage: SceneCoverage
    stages: list[CycleStage]
    # The window's strategy brief frozen with the cycle (E.B28): beliefs to prove, offers in force, the season.
    strategy_brief: StrategyBrief | None = None


class CycleStart(BaseModel):
    model_config = ConfigDict(extra='forbid')
    window_start: datetime
    window_end: datetime | None = None
    # The selection the approver previewed: a start over a changed selection is refused.
    selection_hash: str = Field(min_length=8, max_length=128)
    mode: str = Field(default='live', pattern='^(live|replay)$')
    include_undated: list[str] = Field(default_factory=list, max_length=50)


def install(routes, repo, decider, reader, action, settings):
    from ..config import Settings
    from ..gate_one import require
    from . import window

    def models():
        return Settings.from_env(database_url=settings.database_url)

    @routes.get('/cycles', responses=returns(list[CycleSummary]))
    def cycle_list(limit: int = Query(default=20, ge=1, le=100)):
        return action(window.listing, repo, limit)

    @routes.get('/cycles/preview', responses=returns(CyclePreview))
    def cycle_preview(start: datetime = Query(alias='from'), end: datetime | None = Query(default=None, alias='to'),
                      subject: str = Depends(decider)):
        action(require, repo, subject, 'decide')
        return action(window.preview, repo, models(), start, end)

    @routes.post('/cycles', status_code=202)
    def cycle_start(payload: CycleStart, subject: str = Depends(decider)):
        return action(window.start, repo, models(), subject, payload.window_start, payload.window_end, mode=payload.mode,
                      expected_selection=payload.selection_hash, include_undated=payload.include_undated)

    @routes.get('/cycles/{run_id}', responses=returns(CycleDetail))
    def cycle_detail(run_id: str):
        return action(window.detail, repo, run_id)

    @routes.get('/budgets', responses=returns(StandingBudgets))
    def budgets(subject: str = Depends(reader)):
        from ..database import connect
        from ..llm import standing

        def read():
            with connect(settings.database_url, vectors=False) as conn:
                return standing.status(conn)
        return action(read)

    @routes.get('/costs', responses=returns(CostSummary))
    def costs(start: datetime | None = Query(default=None, alias='from'), end: datetime | None = Query(default=None, alias='to'),
              subject: str = Depends(reader)):
        from ..llm import cost_summary
        return action(cost_summary.report, repo, start, end)

    @routes.get('/weeks/{week_id}/review.md')
    def review_document(week_id: str, subject: str = Depends(reader)):
        from ..briefs.review_document import render_week
        text = action(render_week, repo, week_id)
        return Response(text, media_type='text/markdown',
                        headers={'Content-Disposition': f'attachment; filename="content-atelier-review-{week_id}.md"'})

    @routes.get('/weeks/{week_id}/review.docx')
    def review_document_docx(week_id: str, subject: str = Depends(reader)):
        from ..briefs.review_docx import MEDIA_TYPE, docx
        data = action(docx, repo, week_id)
        return Response(data, media_type=MEDIA_TYPE,
                        headers={'Content-Disposition': f'attachment; filename="content-atelier-review-{week_id}.docx"'})
