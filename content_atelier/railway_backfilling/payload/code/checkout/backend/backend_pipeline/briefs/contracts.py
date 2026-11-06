from typing import Literal
from pydantic import Field
from ..contracts import Contract, Text

WORKFLOW = 'approved_angle_brief_v1'
STAGES = ('brief_prepare','brief_research','brief_context','brief_writing','brief_validation')

class EvidenceItem(Contract):
    evidence_id: Text
    transcript_id: str | None = None
    source_hash: str | None = None
    source_digest: str | None = None
    passage_id: str | None = None
    start: int | None = None
    end: int | None = None
    excerpt: Text
    title: Text
    speaker: str | None = None
    start_ms: int | None = None
    source_url: str | None = None
    moment_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    role: Literal['anchor','support','qualification','counterevidence','context','external_framing']
    qualifications: list[Text] = Field(default_factory=list)
    claim_status: str = 'unknown'
    sensitivity: str = 'unknown'
    inherited: bool = False
    public_use: bool = False
    attribution_verified: bool = False

class Query(Contract):
    text: Text
    purpose: Literal['support','pain','objection','explanation','numbers','counterevidence','prior_coverage']

class QueryPlan(Contract):
    queries: list[Query] = Field(min_length=1,max_length=10)

class Grade(Contract):
    evidence_id: Text
    relevant: bool
    role: Literal['support','qualification','counterevidence','context']
    reason: Text

class GradeResponse(Contract):
    grades: list[Grade]
    gaps: list[Text]

class NumericFact(Contract):
    value: Text
    unit: Text
    timeframe: Text
    subject: Text
    evidence_id: Text
    source_quote: Text

class Claim(Contract):
    claim_id: Text
    text: Text
    kind: Literal['source_assertion','inference','hypothesis','instruction','external_context']
    evidence_ids: list[Text]
    source_status: str
    qualifications: list[Text]
    quote: str | None
    public_quote: bool
    numeric_facts: list[NumericFact]

class Question(Contract):
    question_id: Text
    text: Text
    required: bool
    answer: str | None

class FormatDirection(Contract):
    reader_job: Text
    direction: Text
    outline: list[Text] = Field(min_length=1)
    evidence_ids: list[Text]

class Slide(Contract):
    number: int = Field(ge=1,le=8)
    direction: Text
    evidence_ids: list[Text]

class BriefDocument(Contract):
    title: Text
    angle_statement: Text
    audience: Text
    reader_decision: Text | None
    reader_promise: Text
    positioning: str | None
    why_now: Text
    core_insight: Text
    message_spine: list[Text] = Field(min_length=3,max_length=4)
    audience_pain: Text
    narrative: list[Text] = Field(min_length=1)
    evidence_boundaries: list[Text] = Field(min_length=1)
    claims: list[Claim]
    differentiation: Text
    prior_differences: dict[str,Text]
    voice: list[Text] = Field(min_length=1)
    email: FormatDirection
    carousel_reader_job: Text
    carousel: list[Slide] = Field(min_length=8,max_length=8)
    reels: list[FormatDirection] = Field(min_length=3,max_length=3)
    cta: dict
    creative_direction: list[Text] = Field(min_length=1)
    accessibility: list[Text] = Field(min_length=1)
    distribution: list[Text] = Field(min_length=1)
    evaluation_signals: list[Text] = Field(min_length=1)
    similarity_review: Text
    claims_requiring_consent: list[Text]
    open_questions: list[Question]
    sources: list[Text]
    handoff_checklist: list[Text] = Field(min_length=1)

class ReviewFinding(Contract):
    claim_id: str | None
    severity: Literal['blocking','warning']
    message: Text
    evidence_ids: list[Text]

class SupportReview(Contract):
    reviewed_claim_ids: list[Text]
    preserves_approved_direction: bool
    distinct_treatment: bool
    findings: list[ReviewFinding]

class PriorItem(Contract):
    angle_id: Text
    argument: Text
    audience: Text
    mechanism: Text
    approval_status: Text
    cosine: float | None
    discovery: list[Text]
    briefs: list[dict]
    publications: list[dict]
    content_hash: Text

class Dossier(Contract):
    angle: dict
    evidence: list[EvidenceItem]
    prior: list[PriorItem]
    queries: list[Query]
    coverage: dict
    gaps: list[Text]
    audit: list[dict]
    brand: dict
