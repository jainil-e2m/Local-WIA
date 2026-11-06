"""Response models for the /storage routes the Atelier app calls (plan 1.F1).

They exist so that `backend/openapi.json`, and the TypeScript types generated from it, describe what the app reads.
They are documentation of the answer, not a filter on it: a route names its model in `responses=returns(Model)`,
which publishes the schema without validating or re-serialising the body. So a route answers exactly as before, and
no stored row can start failing because a field is missing or typed differently from the model.

The models are permissive on purpose. Extra fields are allowed (a route may add a field without breaking a caller), and
a field is required only where the app reads it unconditionally. Where the backend already owns a contract
(`AngleCard`, `BriefDocument`, `BriefDocumentV2`, `BriefDocumentV3`, `BriefDocumentV4`, `EvidenceItem`) the model reuses it, so the two cannot drift apart.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .briefs.contracts import BriefDocument, EvidenceItem
from .briefs.contracts_v2 import BriefDocumentV2
from .briefs.contracts_v3 import BriefDocumentV3
from .briefs.contracts_v4 import BriefDocumentV4
from .card_contracts import AngleCard, OfferFit, PublicStance, ReaderFit, Surprise
from .knowledge import items as knowledge_items


def returns(model: Any, status: int = 200) -> dict:
    """`responses=` for a route decorator: publish the schema of the answer, change nothing about it."""
    return {status: {'model': model}}


class Loose(BaseModel):
    model_config = ConfigDict(extra='allow')


Role = Literal['viewer', 'editor', 'approver', 'admin']
ItemKind = Literal[knowledge_items.KINDS]
ItemStatus = Literal[knowledge_items.STATUSES]
SourceType = Literal['zoom', 'fathom', 'slack', 'manual', 'file']


# ---------------------------------------------------------------- shell: flags, identity

class Flags(Loose):
    briefs: bool
    packs: bool
    calendar: bool
    context: bool


class Capabilities(Loose):
    edit_cards: bool
    edit_briefs: bool
    decide: bool
    approve_briefs: bool
    review_knowledge: bool
    identity_review: bool
    manage_users: bool
    manage_intake: bool
    generate_packs: bool
    approve_packs: bool
    schedule_calendar: bool


class Me(Loose):
    """The answer of GET /storage/me (gates/roles.py Access.describe)."""
    email: str | None
    name: str | None
    slack_user_id: str | None = None
    role: Role | None
    roles: list[Role]
    source: Literal['users', 'lists', 'none']
    identity_approver: bool
    can: Capabilities


# ---------------------------------------------------------------- weeks and cards (Gate 1)

class StoredWeek(Loose):
    week_id: str
    week_start: str
    week_end: str
    status: str
    active_run_id: str | None


class RubricRatings(Loose):
    """A label's ratings on rubric 2.3a (E.X7): the version and text the reviewer saw, each criterion 1 to 5, the mean."""
    version: str | None = None
    text_sha256: str | None = None
    criteria: dict[str, int] | None = None
    overall: float | None = None


class RubricCriterion(Loose):
    key: str
    name: str
    text: str


class Rubric(Loose):
    """Review rubric 2.3a as the Gate 1 form shows it (gates/rubric.py)."""
    version: str
    scale: list[int]
    anchors: dict[str, str]
    instruction: str
    criteria: list[RubricCriterion]
    text: str
    text_sha256: str


class Disposition(Loose):
    disposition: str
    reason_code: str | None
    note: str | None
    author: str
    actor: str
    hold_until: str | None
    resulting_item_id: str | None
    central_point_kept: bool | None
    created_at: str
    rubric_ratings: RubricRatings | None = None


class Hold(Loose):
    until: str
    reason_code: str
    note: str | None
    author: str
    # A hold the strategy brief set (E.B28): the offers in force the card undercuts.
    offers: list[str] | None = None


class LedgerFlag(Loose):
    id: str
    kind: str
    severity: Literal['block', 'check', 'style']
    field: str
    text: str
    message: str
    source: str


class LedgerSpan(Loose):
    speaker: str | None
    role: str


class LedgerBinding(Loose):
    point_index: int
    point: str
    status: str
    spans: list[LedgerSpan] | None = None


class LedgerCritic(Loose):
    wia_is_the_subject: Literal['pass', 'fail']
    worth_attention: Literal['pass', 'fail']
    reason: str


class PublicUse(Loose):
    """Why a strategist v7 card is rejected for public use (E.B30); it may still be marked internal."""
    allowed: bool
    reasons: list[str]
    kinds: list[str]


class Ledger(Loose):
    """The evidence ledger on a card (E.B10): bindings, flags, qualifiers, readiness and the critic's view."""
    version: str
    readiness: Literal['ready', 'needs_check', 'research_required']
    ledger_hash: str
    model_pass: str
    flags: list[LedgerFlag]
    qualifiers: list[str]
    bindings: list[LedgerBinding]
    critic: LedgerCritic | None
    public_use: PublicUse | None = None


class StrategistCard(AngleCard):
    """A strategist card; profile version 5 adds the priority series. Version 7 (E.B30, E.B32) replaces core_perspective with
    `point` (a v7 card has no core_perspective) and adds the point's tests and the guardrail the brief writer reads."""
    series: str | None = None
    point: str | None = None
    point_is_about: Literal['wia_belief', 'wia_standard', 'client_experience', 'platform_or_tactic'] | None = None
    surprise_for_experienced_advertiser: Surprise | None = None
    reader_takeaway: str | None = None
    reader_fit: ReaderFit | None = None
    belief_ref: str | None = None
    offer_fit: OfferFit | None = None
    public_stance: PublicStance | None = None
    guardrail: str | None = None
    recurrence: str | None = None


class StanceConfirmation(Loose):
    """An approver's confirmation of a v7 card's public stance (D31), covering the stance and point as confirmed."""
    stance: str | None
    point: str | None
    by: str
    at: str
    note: str | None = None


class StanceConfirmed(Loose):
    angle_id: str
    content_hash: str
    stance_confirmation: StanceConfirmation


class BriefQuote(Loose):
    document: str
    text: str


class PublishedPoint(Loose):
    published_on: str
    channel: str | None = None
    title: str | None = None
    key_message: str


class BeliefToProve(Loose):
    ref: str
    id: str
    belief: str
    stage: Literal['ATTRACT', 'WARM', 'CONVERT']
    offer: str | None
    offers: list[str]
    priority_series: str | None = None
    quotes: list[BriefQuote]
    last_proved: str | None
    do_not_repeat: list[PublishedPoint]


class BriefOffer(Loose):
    offer: str
    status: Literal['open', 'waitlist', 'delivering', 'closed']
    sellable: bool
    starts: str | None = None
    ends: str | None = None
    do_not_undercut: list[str]
    terms: list[str] = []
    note: str | None = None
    source: str | None = None


class BriefSeason(Loose):
    name: str
    label: str
    weeks_to_engagement_season: int | None = None


class BriefSeries(Loose):
    name: str
    last_published: str | None


class StrategyBrief(Loose):
    """The window's strategy brief (E.B28): beliefs to prove, offers in force, recent central points, the season. Assembled
    with no model call, frozen with the cycle with its hash, shown at Gate 1 and read by strategist v7."""
    version: str
    made_by: str
    on: str
    publishing_window: dict[str, str]
    season: BriefSeason
    mix: dict[str, int]
    beliefs_to_prove: list[BeliefToProve]
    live_offers: list[BriefOffer]
    recent_central_points: list[PublishedPoint]
    priority_series: list[BriefSeries]
    content_plan: list[str]
    warnings: list[str]
    inputs: dict[str, Any]
    brief_hash: str


class CardRefreshRecord(Loose):
    """Who made a refreshed card version (3.B7, R58): the model, from a reviewer's feedback; the fields it kept as a
    person wrote them and the ones it changed."""
    maker: Literal['model']
    feedback: str
    author: str
    requested_by: str
    prompt_version: str
    model: str
    reason: str
    kept: list[str]
    changed: list[str]
    run_id: str
    at: str


class AngleBody(Loose):
    """content_body of an angle: a strategist card (`card`), a strategic opportunity (`strategy`) or a legacy angle."""
    card: StrategistCard | None = None
    strategy: dict[str, Any] | None = None
    title: str
    argument: str
    audience: str
    tension: str
    take: str
    mechanism: str
    reader_decision: str
    qualifiers: list[str]
    risks: list[str]
    source_assertions: list[str]
    inference: str | None
    ledger: Ledger | None = None
    # The card fields a person has written (3.B7): a refresh with feedback keeps them word for word.
    person_edits: list[str] | None = None
    # Set on a version a refresh with feedback wrote.
    refresh: CardRefreshRecord | None = None


class MatchingSelection(Loose):
    selection_status: str
    reason: str | None = None
    duplicate_of: str | None = None


class BatchFlag(Loose):
    angle_id: str
    cosine: float


class HistoryMatch(Loose):
    angle_id: str
    title: str | None = None
    argument: str | None = None
    week_start: str | None = None
    approval_status: str | None = None
    cosine: float
    age_days: float
    risk: float


class MatchingResult(Loose):
    selection: MatchingSelection | None = None
    status: str
    workflow: str | None = None
    max_historical_cosine: float | None = None
    history_count: int | None = None
    historical_risk: float | None = None
    current_batch_flags: list[BatchFlag] | None = None
    partial_history_ids: list[str] | None = None
    history: list[HistoryMatch] | None = None


class SelectedCta(Loose):
    text: str | None = None


class CardCheck(Loose):
    """Where a card version's comparison check stands (E.B16, E.B20): a reframe, revive or edit queues one."""
    status: Literal['checked', 'queued', 'running', 'waiting', 'failed', 'not_queued']
    run_id: str | None = None
    message: str | None = None


class GateContextItem(Loose):
    """Context or an attested fact given at a gate (5.B7, R57; interface 2)."""
    id: str
    kind: Literal['context', 'attested_fact', 'paraphrase']
    text: str
    author: str
    created_at: str
    gate: Literal['gate_one', 'gate_two'] | None = None
    # On a brief: whether this version holds it (else the card's, carried by the next refresh).
    in_brief: bool | None = None


class BlockerItem(Loose):
    """One thing that stops approval, in a reviewer's words (5.F2, R50)."""
    kind: Literal['removed_material', 'open_question', 'cta_unconfirmed', 'blocking_finding', 'stale', 'claims_check', 'role']
    title: str
    action: str
    detail: str | None = None


class RemovedMaterial(Loose):
    """The item is built on material removed at a client's request (6.B12, removal.py): marked, never deleted. It cannot be
    developed, approved, consumed or marked ready; `note` says so in a reviewer's words, with the day of the removal."""
    decision_id: str
    removed_at: str
    note: str


class CardRefresh(Loose):
    """A refresh with feedback asked for on this card version (3.B7): queued, being written, waiting for this week's refreshes
    budget, or failed; `message` says why it waits or failed, in plain words. A finished refresh is a new version carrying
    its own `content_body.refresh`."""
    status: Literal['queued', 'running', 'waiting', 'failed']
    run_id: str
    feedback: str
    author: str | None = None
    kept: list[str]
    message: str | None = None


class CardRefreshQueued(Loose):
    run_id: str
    angle_id: str
    status: Literal['queued']
    mode: Literal['live', 'replay', 'synthetic']
    kept: list[str]


class AccountEntry(Loose):
    date: str | None
    # day, week (dated only to its source folder's week, 1.B11) or undated.
    precision: str
    kind: Literal['recommended', 'built', 'decided', 'measured', 'said', 'open', 'published', 'sent', 'internal']
    text: str
    source: dict[str, Any]


class AccountLastCall(Loose):
    date: str | None
    precision: str
    title: str


class AccountMemory(Loose):
    """An account beside a client story card (3.B17, D25): its naming, current state and what happened after the card's call,
    from WIA's records only. `internal_since` are internal meetings' remarks, for the reviewer only."""
    client_id: str
    name: str
    business: str | None = None
    status: str
    naming: Literal['may_name', 'anonymise', 'never_name', 'no_use']
    calls: int
    last_call: AccountLastCall | None
    latest: list[AccountEntry]
    cautions: list[AccountEntry]
    card_call_date: str | None
    what_happened_next: list[AccountEntry]
    internal_since: list[AccountEntry]


class StoredAngle(Loose):
    can_approve: bool | None = None
    can_edit: bool | None = None
    can_reject: bool | None = None
    angle_id: str
    run_id: str
    content_hash: str
    moment_ids: list[str]
    supersedes_id: str | None = None
    workflow: str | None = None
    has_replacement: bool | None = None
    content_body: AngleBody
    base_score: float | None
    adjusted_score: float | None
    selection_status: str
    approval_status: str
    first_generated_at: str
    selected_cta: SelectedCta | None
    disposition: Disposition | None = None
    hold: Hold | None = None
    check: CardCheck | None = None
    refresh: CardRefresh | None = None
    matching_result: MatchingResult | None
    # Context and attested facts given on the card at Gate 1 (5.B7); they reach its brief's writer.
    context_items: list[GateContextItem] | None = None
    # Strategist v7 (E.B30): why the card is rejected for public use, and its stance confirmation (D31), if any.
    public_use: PublicUse | None = None
    stance_confirmation: StanceConfirmation | None = None
    # The accounts the card's scenes come from, with their current state (3.B17); empty for a card with no client account.
    account_memory: list[AccountMemory] | None = None
    # Built on material removed at a client's request (6.B12); `public_use` then says so and the card cannot be developed.
    removed_material: RemovedMaterial | None = None


class CandidateFamily(Loose):
    original_id: str
    replacement_id: str | None
    targeted: bool
    disposition: str
    explanation: str


class ComparisonFamily(CandidateFamily):
    selected_id: str | None
    original_reasons: list[str]
    replacement_reasons: list[str] | None


class ComparisonScenario(Loose):
    cutoff: float
    counts: dict[str, int]
    selected_ids: list[str]
    families: list[ComparisonFamily]
    current_batch_flags: dict[str, list[BatchFlag]]


class ComparisonReport(Loose):
    status: str
    families: list[CandidateFamily]
    scenarios: list[ComparisonScenario]
    threshold_selection_pending: bool


class ConsideredIdea(Loose):
    index: int
    moment_ids: list[str]
    idea: str
    reason: str
    disposition: Disposition | None = None


class RankedAngle(Loose):
    rank: int
    angle_id: str
    current_angle_id: str
    title: str | None
    selection_status: str | None
    approval_status: str | None


class InternalInsight(Loose):
    moment_ids: list[str]
    insight: str
    use: str


class PillarNote(Loose):
    pillar: str
    note: str


class SeedPairing(Loose):
    seed_ref: str
    moment_ids: list[str]
    note: str
    seed_text: str | None = None
    unanswered: bool | None = None
    seed_kind: str | None = None
    seed_author: str | None = None
    transcript_id: str | None = None
    call: str | None = None


class CardSelection(Loose):
    run_id: str
    week_summary: str
    selection_hash: str
    ranking: list[RankedAngle]
    considered_not_selected: list[ConsideredIdea]
    internal_insights: list[InternalInsight]
    unreferenced_moment_ids: list[str]
    publishing_order: list[int] | None = None
    pillar_notes: list[PillarNote] | None = None
    seed_pairings: list[SeedPairing] | None = None
    # The content plan was stale or missing when the run generated (L.B10).
    plan_warning: str | None = None


class RosterEntry(Loose):
    name: str
    role: str
    status: Literal['current', 'former', 'outside']
    aliases: list[str]


class WeekComparison(Loose):
    run_id: str
    run_status: str
    completion_state: str
    report: ComparisonReport | None


class RunSummary(Loose):
    run_id: str
    status: str
    created_at: str | None = None
    current_message: str | None
    error_summary: str | None
    has_partial_failures: bool


class JobResultRefs(Loose):
    coverage_notes: list[str] | None = None


class JobRow(Loose):
    """A pipeline job row: the progress contract (plan 1, cross-system integration). Progress is read from these fields
    and never inferred from elapsed time."""
    job_id: str
    run_id: str | None = None
    stage: str
    status: str
    current_step: str | None = None
    current_message: str | None
    completed_units: int | None
    total_units: int | None
    attempt_count: int | None = None
    error_summary: str | None
    heartbeat_at: str | None = None
    updated_at: str | None = None
    result_refs: JobResultRefs | None = None


class WeekEvent(Loose):
    event_id: str
    message: str
    created_at: str
    severity: str


class WeekTranscript(Loose):
    transcript_id: str
    title: str
    source_url: str | None
    occurred_at: str | None


class WeekReview(Loose):
    approval_cutoff: float | None = None
    selection: CardSelection | None = None
    roster: list[RosterEntry] | None = None
    week: StoredWeek
    angles: list[StoredAngle]
    comparisons: list[WeekComparison] | None = None
    runs: list[RunSummary]
    jobs: list[JobRow]
    events: list[WeekEvent]
    transcripts: list[WeekTranscript]
    context_warnings: list[str] | None = None
    # The rubric the card form rates against (E.X7), when the week has strategist cards.
    rubric: Rubric | None = None
    # The window's strategy brief the week's latest cycle was given (E.B28); None for a cycle before it.
    strategy_brief: StrategyBrief | None = None


class MomentBody(Loose):
    quote: str
    context_summary: str
    qualifications: list[str]
    sensitivity: str


class MomentRecord(Loose):
    moment_body: MomentBody


class MomentPassage(Loose):
    passage_id: str
    text: str
    title: str
    speaker: str | None
    start_ms: int | None
    end_ms: int | None
    roles: list[str]


class MomentEvidence(Loose):
    moment: MomentRecord
    passages: list[MomentPassage]


class TranscriptOriginal(Loose):
    transcript_id: str
    title: str
    source_url: str | None
    occurred_at: str | None
    original_text: str


class Seed(Loose):
    seed_id: str
    kind: Literal['thought', 'draft', 'asset', 'founder_note']
    text: str
    target_offer: str | None
    source_url: str | None
    author: str
    status: str
    always_true: bool
    created_at: str
    used_in_run_id: str | None
    transcript_id: str | None = None


class AckStatus(Loose):
    status: str


# ---------------------------------------------------------------- briefs (Gate 2)

class BriefEvidence(EvidenceItem):
    """An EvidenceItem as a stored brief or research dossier carries it: the defaulted fields are all present."""
    model_config = ConfigDict(extra='allow')
    transcript_id: str | None
    source_hash: str | None
    source_digest: str | None
    passage_id: str | None
    start: int | None
    end: int | None
    speaker: str | None
    start_ms: int | None
    source_url: str | None
    moment_ids: list[str]
    chunk_ids: list[str]
    qualifications: list[str]
    claim_status: str
    sensitivity: str
    inherited: bool
    public_use: bool
    attribution_verified: bool


class BriefFinding(Loose):
    severity: str
    message: str
    claim_id: str | None = None
    evidence_ids: list[str] | None = None


class BriefReviewBlock(Loose):
    # Paths of the lines a person edited (5.F5), or whole sections on briefs saved before 22 October.
    locked_fields: list[str]
    findings: list[BriefFinding]
    clearances: dict[str, Any] | None = None
    # On a refreshed version: each locked line the draft had changed and that was put back (5.F5).
    locks_restored: list[dict[str, Any]] | None = None



class BriefCtaV1(Loose):
    text: str | None = None


class StoredBriefDocument(BriefDocument):
    """A version 1 brief document as stored: its CTA is {text}."""
    cta: BriefCtaV1


class BriefContentV1(Loose):
    schema_version: str | None = None
    document: StoredBriefDocument
    review: BriefReviewBlock


class BriefProvenance(Loose):
    run_id: str | None = None
    roster: list[RosterEntry] | None = None


class BriefContentV2(Loose):
    schema_version: Literal['brief_document_v2']
    document: BriefDocumentV2
    review: BriefReviewBlock
    provenance: BriefProvenance | None = None


class BriefContentV3(Loose):
    """A version 3 brief (E.B23): the writer's copy with the claims ledger built after writing; `review.ledger` records
    the ledger's verifier and `review.repair` whether a repair ran and was accepted."""
    schema_version: Literal['brief_document_v3']
    document: BriefDocumentV3
    review: BriefReviewBlock
    provenance: BriefProvenance | None = None


class BriefContentV4(Loose):
    """A version 4 brief (E.B33): the brief in the 13 October order and the finished copy of every asset (each Reel with its
    kind, cover, on-screen hook and caption; the carousel's title and caption; the email's send header), with v3's ledger."""
    schema_version: Literal['brief_document_v4']
    document: BriefDocumentV4
    review: BriefReviewBlock
    provenance: BriefProvenance | None = None


class PriorBrief(Loose):
    brief_id: str
    approval_status: str


class PriorContent(Loose):
    angle_id: str
    argument: str
    approval_status: str
    cosine: float | None
    briefs: list[PriorBrief]
    publications: list[dict[str, Any]]


class ResearchGaps(Loose):
    items: list[str]
    coverage: dict[str, Any]


class AnchorOption(Loose):
    key: str
    label: str


class BriefAnchor(Loose):
    """The piece production writes first (E.B23, briefs/handoff.py): a person's choice at Gate 2, else the rule's."""
    key: str | None
    chosen_by: Literal['rule', 'person']
    actor: str | None = None
    at: str | None = None
    rule: str
    # Set when a person's choice names a piece no longer in the format plan, so the rule applies.
    note: str | None = None
    options: list[AnchorOption] | None = None


class BriefRowBase(Loose):
    brief_id: str
    week_id: str
    angle_id: str
    content_hash: str
    approval_status: str
    can_approve: bool
    can_edit: bool
    can_review: bool
    can_consume: bool
    # Whether this person may record a published final against the brief (L.B9): an editor, on approved content.
    can_record_published: bool | None = None
    has_replacement: bool
    blockers: list[str]
    # The blockers by kind in plain words, with the role when this person may not approve (5.F2).
    blocker_items: list[BlockerItem] | None = None
    context_items: list[GateContextItem] | None = None
    locked_fields: list[str] | None = None
    # The accounts the brief's card comes from, with their current state (3.B17), for the approver at Gate 2.
    account_memory: list[AccountMemory] | None = None
    selected_evidence: list[BriefEvidence]
    prior_content_context: list[PriorContent]
    research_gaps: ResearchGaps
    supersedes_id: str | None = None
    created_at: str | None = None
    anchor: BriefAnchor | None = None
    # Review rubric 2.3a for the decision form while the brief waits for its decision (E.X9).
    rubric: Rubric | None = None
    # Built on material removed at a client's request (6.B12); a removed_material blocker then stops approval.
    removed_material: RemovedMaterial | None = None


class StoredBriefV1(BriefRowBase):
    schema_version: Literal['brief_document_v1']
    content_body: BriefContentV1


class StoredBriefV2(BriefRowBase):
    schema_version: Literal['brief_document_v2']
    content_body: BriefContentV2


class StoredBriefV3(BriefRowBase):
    schema_version: Literal['brief_document_v3']
    content_body: BriefContentV3


class StoredBriefV4(BriefRowBase):
    schema_version: Literal['brief_document_v4']
    content_body: BriefContentV4


class BriefPage(Loose):
    items: list[StoredBriefV1 | StoredBriefV2 | StoredBriefV3 | StoredBriefV4]
    total: int
    limit: int
    offset: int


class HandoffPiece(Loose):
    """One format-plan piece (E.B23): a stable key from the plan (`reel_1`, `carousel`, `email`, `caption`, `stories`)."""
    key: str
    channel: Literal['reel', 'carousel', 'email', 'caption', 'stories']
    platform: str
    label: str
    anchor: bool
    # Finished words the audience reads or hears, and notes to the person who makes the asset, by field.
    copy_fields: dict[str, Any] = Field(alias='copy')
    direction: dict[str, Any]
    # The evidence a v1 or v2 piece cites; empty for v3, whose claims ledger binds the copy to the evidence.
    evidence_ids: list[str]


class MessageSpine(Loose):
    text: str
    source: Literal['sharpened_point', 'approved_angle', 'core_insight']
    supporting: list[str]


class PublishingOrder(Loose):
    rank: int | None
    position: int | None
    of: int | None
    held: bool
    known: bool


class HandoffTopic(Loose):
    topic_id: str
    name: str
    moments: int


class HandoffClaim(Loose):
    claim_id: str
    text: str
    kind: str
    status: str | None
    evidence_ids: list[str]
    quote: str | None
    public_quote: bool
    numeric_facts: list[dict[str, Any]]
    notes: list[str]


class HandoffItem(Loose):
    id: str
    text: str
    kind: str
    required: bool
    answer: str | None


class HandoffEvidence(Loose):
    evidence_id: str
    cited: bool
    role: str | None
    title: str | None
    speaker: str | None
    start_ms: int | None
    quote: str | None
    moment_ids: list[str]
    consent_status: Literal['cleared', 'anonymise', 'internal_only', 'do_not_use', 'unknown', 'not_applicable']
    client_consent: Literal['may_name', 'anonymise_only', 'no_use', 'unknown', 'not_applicable']
    consent_basis: str
    sensitivity: str | None
    public_use: bool
    attribution_verified: bool
    permission_recorded: bool
    attribution_reference: str | None


class HandoffAnchor(Loose):
    key: str | None
    chosen_by: Literal['rule', 'person']
    actor: str | None
    at: str | None
    rule: str
    note: str | None


class BriefHandoff(Loose):
    """The version-independent production hand-off of a brief (E.B23, briefs/handoff.py). Production reads this, never the
    contract-specific document, and acts only when `can_consume` is true."""
    handoff_version: Literal['brief_handoff_v1']
    brief_id: str
    schema_version: Literal['brief_document_v1', 'brief_document_v2', 'brief_document_v3', 'brief_document_v4']
    content_hash: str
    approval_status: str
    approved_hash: str | None
    approved_by: str | None
    approved_at: str | None
    can_consume: bool
    blockers: list[str]
    week_id: str
    angle_id: str
    title: str
    core_perspective: str
    audience: str
    purpose: str | None
    content_type: str | None
    point_of_view: str | None
    wia_perspective: str | None
    cta: dict[str, Any]
    message_spine: MessageSpine
    anchor: HandoffAnchor
    pieces: list[HandoffPiece]
    channels: list[str]
    channels_without_piece: list[str]
    series: str | None
    publishing_order: PublishingOrder
    topic: HandoffTopic | None
    topics: list[HandoffTopic]
    claims: list[HandoffClaim]
    before_publishing: list[HandoffItem]
    evidence: list[HandoffEvidence]


class BriefVersion(Loose):
    brief_id: str
    supersedes_id: str | None
    content_hash: str
    approval_status: str
    created_at: str
    updated_by: str | None = None
    # Who made the version and why (5.F5 d): generated, edit, refresh, context, answers, check, permission, cta, anchor.
    author: str | None = None
    kind: str | None = None
    reason: str | None = None
    fields: list[str] | None = None
    unlocked: list[str] | None = None


class AngleContextResult(GateContextItem):
    angle_id: str
    context_items: list[GateContextItem]


class BriefContextResult(Loose):
    brief_id: str
    content_hash: str
    context_id: str


class PackStarted(Loose):
    """The content pack a Gate 2 approval started (D43c, NP.B2): its run, or why it could not start (the approval still
    stands). Absent when packs are off or the brief is not a v4 brief, with `pack_note` saying which."""
    pack_id: str | None = None
    run_id: str | None = None
    status: str
    mode: str | None = None
    error: str | None = None


class BriefWriteResult(Loose):
    """What a brief write answers: a new version (edit, answers, review, clearance, CTA, refinement) or the decision. An
    approval of a v4 brief with packs on also starts its content pack (`pack_run`)."""
    brief_id: str | None = None
    content_hash: str | None = None
    approval_status: str | None = None
    decision_id: str | None = None
    pack_run: PackStarted | None = None
    pack_note: str | None = None


class ResearchJob(Loose):
    job_id: str
    stage: str
    status: str
    current_step: str | None = None
    current_message: str | None
    completed_units: int | None
    total_units: int | None
    error_summary: str | None


class Dossier(Loose):
    evidence: list[BriefEvidence]
    gaps: list[str]
    coverage: dict[str, Any]


class AngleResearch(Loose):
    status: str
    run_id: str | None = None
    # live, replay or synthetic: a developed card's brief starts live (4.B1).
    mode: str | None = None
    # Why the brief waits: this week's standing budget for its purpose is spent (6.B3), in words.
    waiting_reason: str | None = None
    error_summary: str | None = None
    brief_id: str | None = None
    jobs: list[ResearchJob]
    dossier: Dossier | None = None


# ---------------------------------------------------------------- packs and calendar (production)

class SchedulePreview(Loose):
    calendar_entry_id: str
    asset_id: str
    asset_content_hash: str
    pack_manifest_hash: str
    scheduled_for: str
    status: str
    revision: int
    display_timezone: str


class PackClaim(Loose):
    text: str
    brief_claim_ids: list[str]
    qualifications: list[str]


class PackSlide(Loose):
    number: int
    headline: str
    body: str
    direction: str | None = None


class PackCta(Loose):
    text: str | None = None


class PackDocument(Loose):
    """A pack asset's copy: an email (subject, preview_text, body), a carousel (slides, caption) or a reel
    (spoken_script, caption, visual_directions). Every field is optional here because the list route sends the title only."""
    title: str | None = None
    subject: str | None = None
    preview_text: str | None = None
    body: str | None = None
    spoken_script: str | None = None
    slides: list[PackSlide] | None = None
    caption: str | None = None
    visual_directions: list[str] | None = None
    cta: PackCta | None = None
    claims: list[PackClaim] | None = None
    evidence_ids: list[str] | None = None


class PackAssetBody(Loose):
    document: PackDocument


class StoredAsset(Loose):
    asset_id: str
    slot_key: str
    ordinal: int
    asset_type: Literal['email', 'carousel', 'reel']
    content_hash: str | None
    content_body: PackAssetBody | None
    schedule: list[SchedulePreview]


class PackReview(Loose):
    findings: list[str]


class PackValidation(Loose):
    passed: bool
    review: PackReview


class StoredPack(Loose):
    pack_id: str
    title: str
    week_id: str
    source_brief_id: str
    manifest_hash: str | None
    approval_status: str
    created_at: str
    assets: list[StoredAsset]
    blockers: list[str]
    schedule_blockers: list[str]
    can_approve: bool
    can_schedule: bool
    can_generate: bool
    validation_result: PackValidation | None = None


class PackPage(Loose):
    items: list[StoredPack]
    total: int


class PackJob(Loose):
    job_id: str
    stage: str
    status: str
    current_step: str | None = None
    current_message: str | None
    error_summary: str | None
    attempt_count: int | None = None
    heartbeat_at: str | None = None
    completed_units: int | None
    total_units: int | None


class PackProduction(Loose):
    jobs: list[PackJob]
    costs: dict[str, Any] | None


class PackQueued(Loose):
    pack_id: str


# ---------------------------------------------------------------- content packs, contract v2 (Phase NP, NP.B6)
# The content-packs plan, sections 4.1, 4.2 and 5.6. A pack is 1 email, 1 carousel and 3 Reels in brief contract v4's leaf
# shape (packs/contracts_v2.py); `content` and `brief_copy` hold a piece's leaves, edited by dotted path relative to
# `content`.

PackStateV2 = Literal['finishing', 'waiting', 'in_review', 'ready_to_publish', 'superseded']
PackPieceKey = Literal['email', 'carousel', 'reel_1', 'reel_2', 'reel_3']


class PackLockV2(Loose):
    """A line a person wrote, kept word for word by every model step: where (Gate 2 or the pack), who, and whether the
    person acted under D12's delegation (R55)."""
    path: str
    author: str
    delegated: bool
    at: str | None = None
    origin: Literal['gate_two', 'pack']


class PackResolutionV2(Loose):
    by: str
    at: str
    delegated: bool
    note: str | None = None


class PackFindingV2(Loose):
    """A finding on a piece or the pack. `source` fidelity: the fidelity loop's, stored, cleared by an edit of its sentence
    or an attestation (R57); `source` check: a deterministic check, recomputed on every read and edit."""
    finding_id: str
    source: Literal['fidelity', 'check', 'editorial']
    piece: str | None = None
    path: str | None = None
    sentence: str | None = None
    severity: Literal['blocking', 'warning']
    message: str
    status: Literal['open', 'cleared', 'attested', 'kept']
    resolution: PackResolutionV2 | None = None
    can_attest: bool = False
    # Round 2: an editorial finding's issue (contracts_v2.EDITORIAL_ISSUES); "attest" on it keeps the line with a reason.
    issue: str | None = None


class PackChangeV2(Loose):
    path: str
    kind: str
    before: str | None = None
    after: str | None = None
    note: str | None = None


class PackPublicationV2(Loose):
    """A piece marked published (date, channel, final text), recorded through capture outside the pack's copy."""
    content_id: str
    piece: str
    channel: str
    published_on: str
    url: str | None = None
    by: str
    at: str


class PackPieceV2(Loose):
    key: PackPieceKey
    channel: Literal['email', 'carousel', 'reel']
    label: str
    kind: Literal['story', 'stance', 'broll_text', 'central', 'second', 'third'] | None = None
    ordinal: int
    origin: Literal['brief', 'finished', 'written', 'not_written']
    not_written_reason: str | None = None
    brief_key: str | None = None
    content: dict[str, Any] | None
    brief_copy: dict[str, Any] | None = None
    locks: list[PackLockV2]
    findings: list[PackFindingV2]
    changes: list[PackChangeV2]
    published: list[PackPublicationV2]
    content_hash: str | None = None
    asset_id: str | None = None
    schedule: PieceSchedule | None = None
    editable: list[str]


class PieceSchedule(Loose):
    calendar_entry_id: str
    scheduled_for: str
    revision: int
    display_timezone: str
    status: str


class PackDoneV2(Loose):
    by: str
    at: str
    delegated: bool
    reference: str | None = None
    note: str | None = None


class PackNoteV2(Loose):
    """A before-publishing note: carried from Gate 2 with its answer, or added by the pack. A client's permission is a note
    for whoever posts the piece, never a gate (`client_permission`)."""
    id: str
    text: str
    kind: str
    required: bool
    answer: str | None = None
    client_permission: bool
    done: PackDoneV2 | None = None


class PackQuoteV2(Loose):
    quote_id: str
    piece: str
    quote: str
    speaker: str | None = None
    evidence_id: str | None = None
    cleared: PackDoneV2 | None = None


class PackVersionV2(Loose):
    pack_id: str
    supersedes_id: str | None = None
    manifest_hash: str | None = None
    approval_status: str
    created_at: str
    run_id: str | None = None
    kind: str
    by: str | None = None
    delegated: bool
    pieces: list[str]
    paths: list[str]
    note: str | None = None


class PackProvenanceV2(Loose):
    brief_id: str
    approved_hash: str
    brief_schema: str
    handoff_version: str
    run_id: str
    mode: str
    finish_mode: Literal['finish', 'missing_only', 'assemble']
    profiles: dict[str, Any]
    models: dict[str, Any]
    knowledge_base_version: str | None = None
    approved_by: str | None = None
    approval_delegated: bool


class PackGrantV2(Loose):
    item_id: str | None = None
    item: str | None = None
    statement: str
    by: str
    at: str
    delegated: bool


class PackCreativeChoiceV2(Loose):
    """Round 2 (finisher v3): the openings or premises weighed for one piece, the one chosen and why."""
    piece: str
    considered: list[str]
    chosen: str
    why: str


class StoredPackV2(Loose):
    """GET /packs/{id}: one pack version with its pieces in tab order (Email, Carousel, Reel 1 to 3)."""
    pack_id: str
    contract_version: Literal['content_pack_v2']
    title: str
    week_id: str
    source_brief_id: str
    source_brief_hash: str
    angle_id: str | None = None
    pillar: str | None = None
    rank: int | None = None
    state: PackStateV2
    state_reason: str | None = None
    approval_status: str
    manifest_hash: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    created_at: str
    supersedes_id: str | None = None
    run_id: str | None = None
    run_active: bool
    pieces: list[PackPieceV2]
    findings: list[PackFindingV2]
    ready_blockers: list[str]
    before_publishing: list[PackNoteV2]
    client_quotes: list[PackQuoteV2]
    stronger_with_permission: list[str]
    # NP.B15: the items granted and facts stated, each attested with the person and date (R57).
    granted: list[PackGrantV2] = []
    pack_notes: list[str]
    change_notes: list[str]
    creative_choices: list[PackCreativeChoiceV2] = []
    fidelity: dict[str, Any] | None = None
    provenance: PackProvenanceV2 | None = None
    change: dict[str, Any] | None = None
    versions: list[PackVersionV2]
    approval_delegated: bool
    can_edit: bool
    can_decide: bool
    can_finish_again: bool
    can_mark_published: bool
    # Built on material removed at a client's request (6.B12); a blocking finding then stops "ready to publish".
    removed_material: RemovedMaterial | None = None


class PackPieceSummaryV2(Loose):
    key: PackPieceKey
    label: str
    kind: Literal['story', 'stance', 'broll_text', 'central', 'second', 'third'] | None = None
    origin: Literal['brief', 'finished', 'written', 'not_written']
    published: bool


class PackSummaryV2(Loose):
    pack_id: str
    title: str
    week_id: str
    source_brief_id: str
    state: PackStateV2
    state_reason: str | None = None
    approval_status: str
    manifest_hash: str | None = None
    created_at: str
    pillar: str | None = None
    rank: int | None = None
    pieces: list[PackPieceSummaryV2]
    open_findings: int
    open_notes: int


class PackPageV2(Loose):
    items: list[PackSummaryV2]
    total: int


class PackProductionV2(Loose):
    """GET /packs/{id}/production: the pack run's jobs, costs and why it waits, in words."""
    run_id: str | None = None
    state: PackStateV2
    state_reason: str | None = None
    jobs: list[PackJob]
    costs: dict[str, Any] | None = None


class PackQueuedV2(Loose):
    """POST /briefs/{id}/pack: the pack run created or retried."""
    pack_id: str | None = None
    run_id: str | None = None
    status: str
    mode: str | None = None
    error: str | None = None


class PackSavedV2(Loose):
    """The answer to an edit, revert, clearance, attestation, decision or Finish again: the pack version to show now."""
    pack_id: str
    manifest_hash: str | None = None
    state: PackStateV2
    run_id: str | None = None


class PackPublishedV2(Loose):
    pack_id: str
    piece: str
    content_id: str
    state: PackStateV2


class WeekPlanSlotV2(Loose):
    """One proposed slot of the publishing week (section 4.4): a suggestion computed on read, never stored on the pack."""
    slot: Literal['tuesday_email', 'instagram_1', 'instagram_2', 'instagram_3']
    label: str
    date: str
    weekday: str
    pack_id: str | None = None
    piece: str | None = None
    piece_label: str | None = None
    title: str | None = None
    cta: Literal['offer', 'no_offer', 'reply', 'link', 'none'] | None = None
    note: str | None = None


class WeekPlanBankItemV2(Loose):
    pack_id: str
    piece: str
    piece_label: str
    title: str
    suggested_week: int | None = None
    reason: str | None = None


class WeekPlanFindingV2(Loose):
    severity: Literal['blocking', 'warning']
    message: str
    pieces: list[str] = []


class WeekPlanPackV2(Loose):
    pack_id: str
    title: str
    state: PackStateV2
    pillar: str | None = None
    rank: int | None = None


class WeekPackPlanV2(Loose):
    """GET /weeks/{id}/pack-plan: the week's proposed allocation (one Tuesday email, three Instagram pieces with one offer
    post), the bank, and the week's findings. Computed on read; the system neither schedules nor publishes (D43e)."""
    week_id: str
    publishing_week_start: str
    publishing_week_end: str
    slots: list[WeekPlanSlotV2]
    bank: list[WeekPlanBankItemV2]
    findings: list[WeekPlanFindingV2]
    packs: list[WeekPlanPackV2]


class SavedSchedule(Loose):
    calendar_entry_id: str
    asset_id: str
    asset_content_hash: str
    pack_id: str
    pack_manifest_hash: str
    scheduled_for: str
    status: str
    effective_status: str
    publication: PackPublicationV2 | None = None
    revision: int
    display_timezone: str
    format: Literal['email', 'carousel', 'reel']
    slot_key: str
    title: str
    pack_title: str
    week_id: str
    warnings: list[str]
    overdue: bool


class CalendarConfig(Loose):
    worker_ready: bool | None = None
    enabled: bool
    display_timezone: str
    server_time: str
    can_schedule: bool
    packs_enabled: bool
    can_generate: bool
    live_generation_enabled: bool


class CalendarPage(Loose):
    items: list[SavedSchedule]
    next_cursor: int | None
    display_timezone: str
    server_time: str


# ---------------------------------------------------------------- context system (Phase L)

class WouldChange(Loose):
    document: str
    layer: str
    replaces: dict[str, str] | None
    summary: str


class ItemSuggestion(Loose):
    action: Literal['accept', 'reject', 'review']
    reason: str
    changes: dict[str, str | None] | None = None
    duplicate_of: str | None = None


class EditDiffExample(Loose):
    brief_id: str | None = None
    field: str
    before: str
    after: str


class SourceCorrection(Loose):
    from_: str = Field(alias='from')
    to: str


class SourceDetail(Loose):
    """Where an item came from. Which fields appear depends on the item's source_kind; every one is optional."""
    draft: str | None = None
    section: str | None = None
    subsection: str | None = None
    export: str | None = None
    document: str | None = None
    version: str | None = None
    conversations: list[str] | None = None
    attachments: list[str] | None = None
    chunks: list[str] | None = None
    date_text: str | None = None
    citations_from: Literal['section', 'draft'] | None = None
    date_from: Literal['section', 'export'] | None = None
    decisions: list[str] | None = None
    diffs: list[EditDiffExample] | None = None
    briefs: list[str] | None = None
    category: str | None = None
    authors: list[str] | None = None
    angle_id: str | None = None
    brief_id: str | None = None
    content_id: str | None = None
    seed_id: str | None = None
    disposition: str | None = None
    corrects: str | None = None
    correction: SourceCorrection | None = None
    note: str | None = None


class ContextItem(Loose):
    item_id: str
    kind: ItemKind
    key: str
    body: dict[str, Any]
    text: str
    valid_from: str | None
    valid_to: str | None
    status: ItemStatus
    visibility: Literal['public', 'internal']
    sensitivity: str
    permission: Literal['published', 'client_permission', 'none'] | None
    source_kind: str
    source_ref: str
    source_detail: SourceDetail
    statement_date: str | None
    author: str | None
    model_written: bool
    confidence: str | None
    hash: str
    supersedes_id: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    review_note: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    would_change: WouldChange | None = None
    suggestion: ItemSuggestion | None = None
    can_decide: bool | None = None


class ContextSummary(Loose):
    kinds: dict[str, dict[str, int]]
    candidates: int
    published: dict[str, int]


class ContextKinds(Loose):
    kinds: list[ItemKind]
    operating: list[ItemKind]
    identity: list[ItemKind]
    batch: list[ItemKind]
    documents: dict[str, str]
    schemas: dict[str, Any]


class ContextQueue(Loose):
    items: list[ContextItem]
    groups: dict[str, list[str]]
    total: int
    limit: int
    offset: int
    batch_kinds: list[ItemKind]


class DecisionResult(Loose):
    item_id: str
    status: ItemStatus
    hash: str
    decision_id: str
    superseded: list[str]
    diff: dict[str, Any]


class KnownItems(Loose):
    on: str
    items: list[ContextItem]
    scheduled: list[ContextItem]


class EntryResult(Loose):
    item_id: str
    key: str
    status: Literal['confirmed']
    valid_from: str | None
    supersedes_id: str | None


class HistoryDecision(Loose):
    action: str
    note: str | None
    actor: str | None
    author: str | None
    created_at: str
    details: dict[str, Any] | None = None


class ItemHistory(Loose):
    key: str
    versions: list[ContextItem]
    decisions: list[HistoryDecision]


class PerformanceFigure(Loose):
    date: str
    metric: str
    value: str
    direction: Literal['positive', 'negative'] | None = None
    source: str | None = None


class PublishedPiece(Loose):
    content_id: str
    published_on: str | None
    channel: str | None
    title: str | None
    status: str
    source_kind: str | None
    details: dict[str, Any] | None
    angle_id: str | None
    brief_id: str | None
    performance: list[PerformanceFigure] | None


class PublishedPage(Loose):
    items: list[PublishedPiece]


class BriefPublished(PublishedPiece):
    """A published piece linked to a brief (L.B9): the captured final, its central point and the recorded edit."""
    text: str | None = None
    key_message: str | None = None
    pillar: str | None = None
    content_type: str | None = None
    source_ref: str | None = None
    created_by: str | None = None
    created_at: str | None = None


class BriefPublishedPage(Loose):
    items: list[BriefPublished]


class PublishedCaptureResult(BriefPublished):
    """What recording a published final answers: the stored row, whether this request created it, and how many of
    the figures sent were new."""
    created: bool
    metrics_added: int


class VersionRun(Loose):
    run_id: str
    run_scope: str | None
    status: str
    created_at: str


class VersionBenchmark(Loose):
    result: str
    passed: bool
    recorded_by: str | None = None
    note: str | None = None


class ScheduledBenchmark(Loose):
    """What the scheduled benchmark found for an approved identity change (L.B11); an identity approver records the
    verdict with `POST /context/versions/{version}/benchmark`."""
    state: Literal['recorded', 'skipped']
    result_ref: str | None = None
    suggested: Literal['pass', 'review'] | None = None
    regressions: list[str] = []
    reason: str | None = None  # why a skipped benchmark could not run where the scheduler runs
    at: str | None = None
    config: str | None = None
    model: str | None = None
    base_version: str | None = None
    summary: dict[str, dict[str, dict[str, float]]] | None = None
    spent_usd: float | None = None
    plan_id: str | None = None
    ran_at: str | None = None


class KbVersion(Loose):
    version: str
    active: bool
    state: str
    base_version: str | None = None
    on: str | None = None
    changes: dict[str, Literal['unchanged', 'operating', 'identity']] | None = None
    pending_candidates: dict[str, int] | None = None
    approved_by: str | None = None
    approved_on: str | None = None
    created_by: str | None = None
    benchmark: VersionBenchmark | None = None
    scheduled_benchmark: ScheduledBenchmark | None = None
    runs: list[VersionRun]


class KbVersions(Loose):
    active: str | None
    versions: list[KbVersion]


class CompileResult(Loose):
    status: Literal['compiled', 'exists', 'unchanged']
    version: str
    documents: dict[str, str]
    changes: dict[str, Literal['unchanged', 'operating', 'identity']] | None = None
    pending_candidates: dict[str, int]
    state: str | None = None


class DiscardResult(Loose):
    version: str
    state: Literal['discarded']
    decision_id: str


class VersionDocumentDiff(Loose):
    key: str
    change: Literal['unchanged', 'operating', 'identity'] | None
    diff: str


class VersionDiff(Loose):
    version: str
    against: str | None
    state: str
    documents: list[VersionDocumentDiff]


class StaleWarning(Loose):
    scope: str
    kind: str | None = None
    key: str | None = None
    # None for the L.B11 notices (identity items waiting to be compiled, a version waiting for its benchmark).
    since: str | None = None
    message: str
    overdue: int | None = None
    documents: list[str] | None = None
    items: int | None = None


class StaleWarnings(Loose):
    warnings: list[StaleWarning]


# ---------------------------------------------------------------- intake sources (Sources view)

class IntakeSource(Loose):
    source_id: str
    title: str
    kind: str
    status: str
    source_url: str | None = None
    occurred_at: str | None = None
    received_at: str
    collection_status: str | None = None
    extraction_status: str | None = None
    indexing_status: str | None = None
    error_summary: str | None = None


class IntakeConnection(Loose):
    connection_id: str
    activated_at: str
    checkpoint: str
    health: str
    error_summary: str | None = None


class IntakeBucket(Loose):
    bucket_id: str
    starts_at: str
    cutoff: str | None = None
    status: str


class IntakeRequest(Loose):
    request_id: str
    connection_id: str
    window_start: str
    window_end: str
    status: str
    coverage: dict[str, Any]


class IntakeJob(Loose):
    job_id: str
    run_id: str | None = None
    stage: str
    status: str
    error_summary: str | None = None
    current_message: str | None = None
    attempt_count: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class IntakeOverview(Loose):
    can_admin: bool
    schedule: str
    sources: list[IntakeSource]
    connections: list[IntakeConnection]
    buckets: list[IntakeBucket]
    requests: list[IntakeRequest]
    jobs: list[IntakeJob]


class IntakeRevision(Loose):
    revision_id: str
    received_at: str
    original_text: str | None = None
    indexing_status: str
    deleted: bool
    passage_map: list[dict[str, Any]] | None = None


class IntakeAssetMetadata(Loose):
    permalink: str | None = None
    error: str | None = None


class IntakeAsset(Loose):
    asset_id: str
    filename: str
    status: str
    source_id: str | None = None
    raw_artifact: str | None = None
    metadata: IntakeAssetMetadata


class IntakeSourceDetail(Loose):
    source: IntakeSource
    revisions: list[IntakeRevision]
    assets: list[IntakeAsset]


class IntakeBucketDetail(Loose):
    bucket: IntakeBucket
    sources: list[IntakeSource]


class IntakeSearchHit(Loose):
    transcript_id: str | None = None
    chunk_id: str
    source_id: str | None = None
    title: str
    chunk_text: str


class RevisionOriginal(Loose):
    revision_id: str
    original: Any


# ---------------------------------------------------------------- the cycle summary, the schedule, alerts, monitoring

class WaitingCount(Loose):
    """How many items wait, and for whom in the app's terms ("an approver", "an editor or an approver")."""
    count: int
    who: str


class WeekCount(Loose):
    week_id: str
    n: int


class CardsAtGateOne(WaitingCount):
    by_week: list[WeekCount]


class HeldCardDue(Loose):
    """A card held until a date that has come (3.B11's reminder): due back at Gate 1."""
    angle_id: str
    week_id: str
    title: str | None = None
    hold_until: str


class HeldCardsDue(WaitingCount):
    cards: list[HeldCardDue]


class PackWaitingReason(Loose):
    pack_id: str
    title: str | None = None
    reason: str


class PacksWithTheSystem(Loose):
    finishing: int
    waiting: int
    reasons: list[PackWaitingReason]


class SummaryWaiting(Loose):
    cards_at_gate_1: CardsAtGateOne
    held_cards_due_back: HeldCardsDue
    briefs_at_gate_2: WaitingCount
    packs_in_review: WaitingCount
    packs_ready: int
    packs_with_the_system: PacksWithTheSystem


class ScheduleWindow(Loose):
    start: str
    end: str


class LatestCycle(Loose):
    run_id: str
    week_id: str
    status: str
    created_at: str
    trigger_type: str | None = None
    window: ScheduleWindow | None = None
    # "schedule" when the weekly schedule started it (3.B11); otherwise absent or another word.
    started_from: str | None = None


class NextCycle(Loose):
    """When the weekly schedule starts the cycle next (3.B11): `at` and `window` are null while the schedule is off."""
    enabled: bool
    at: str | None = None
    timezone: str
    window: ScheduleWindow | None = None


class CycleSchedule(NextCycle):
    """GET /schedule: the next run with the schedule in words ("Sunday 04:00 America/Chicago")."""
    text: str


class SourceConnection(Loose):
    connection_id: str
    provider: str
    activated_at: str | None = None
    checkpoint: str | None = None
    health: str | None = None
    error_summary: str | None = None


class SourceHealth(Loose):
    connections: list[SourceConnection]
    # Included documents by extraction status (2.B12's counts).
    extraction: dict[str, int]
    collector: str


class SummaryAlerts(Loose):
    open: int
    errors: int


class SummarySpend(Loose):
    this_week_usd: float
    caps_usd: float
    left_usd: float
    # The labels of the weekly limits reached, and of those with at most a fifth left (summary.CLOSE_SHARE).
    limits_reached: list[str] = []
    limits_close: list[str] = []


class CycleOverview(Loose):
    """GET /summary (6.F2): what Home shows in one read."""
    waiting: SummaryWaiting
    latest_cycle: LatestCycle | None = None
    next_cycle: NextCycle
    sources: SourceHealth
    alerts: SummaryAlerts
    spend: SummarySpend
    at: str


class Alert(Loose):
    """One failure alert (6.B4). `alert_id` is null for the scheduler's silence, which is read live and cannot be dismissed."""
    alert_id: str | None = None
    kind: str
    subject: str
    severity: Literal['error', 'warning']
    message: str
    details: dict[str, Any] = {}
    occurrences: int
    first_seen_at: str | None = None
    last_seen_at: str
    resolved_at: str | None = None
    resolved_by: str | None = None
    # cleared (the condition went away) or dismissed (a person acknowledged it)
    resolution: str | None = None


class AlertList(Loose):
    """GET /alerts: the open alerts first; with ?resolved=true also those resolved in the last 14 days. Alert emails are
    off (the owner, 25 October 2026): the app is the channel."""
    open: int
    alerts: list[Alert]
    email: Literal['off']


class AlertDismissed(Loose):
    alert_id: str
    kind: str
    subject: str


class SideCounts(Loose):
    """A count split into WIA's own rows and delegated ones; `all` is both."""
    wia: int
    delegated: int
    all: int


class CardMeasures(Loose):
    slate: int
    top_five: int
    developed_or_reframed_keeping_the_point: SideCounts
    top_five_developed_or_reframed_keeping_the_point: SideCounts


class SkipReason(Loose):
    reason_code: str | None = None
    note: str | None = None
    title: str | None = None


class MonitoredCycle(Loose):
    run_id: str | None = None
    knowledge_base_version: str | None = None
    strategist_profile: str | None = None
    # "schedule" when the weekly schedule started the cycle, else "app".
    started_from: str
    cost_usd: float
    model_calls: int


class EditorialMonitoring(Loose):
    """The week's editorial monitoring (6.B13): the accepted share against the bar, which counts once Gate 1 is done (at least
    `decided_at_least` cards decided, the rule the low-share alert uses), the skip reasons, the cards whose evidence check
    raised a flag, and the cycle the week ran on."""
    accepted_share: float | None = None
    bar: float
    cards_decided: int
    decided_at_least: int
    gate_1_done: bool
    skip_reasons: list[SkipReason]
    cards_with_evidence_flags: int
    cycle: MonitoredCycle


class WeekMeasures(Loose):
    """GET /weeks/{week_id}/measures: the week's success measures (7.X2) with its editorial monitoring (6.B13)."""
    week_id: str
    week_start: str
    week_end: str
    cards: CardMeasures
    rubric: dict[str, Any]
    briefs: dict[str, Any]
    gate_two_edits: dict[str, Any]
    packs: dict[str, Any]
    thresholds: list[dict[str, Any]]
    wia_reviewers_configured: bool
    previous_week_id: str | None = None
    monitoring: EditorialMonitoring
