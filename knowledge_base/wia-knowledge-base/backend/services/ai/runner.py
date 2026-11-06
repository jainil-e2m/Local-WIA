"""Run one skill on one subject: build the prompt, refuse unless allowed, call, check, store.

Order (6 Nov plan, D7): blocks -> input hash -> already done? -> AI_MODE live? -> monthly budget -> OpenRouter
-> contract -> deterministic checks -> store the run (log + output) and its action candidates, rebuild the
portfolio. `prepare` alone is `kb ai preview`: the exact prompts from real data, nothing sent.

shortcut: the budget check reads month-to-date spend then sends; two AI workers could both pass it at the edge.
Run one AI worker (it is one lane), or lock the month row if that ever changes.
"""
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select, update

from backend.config import get_settings
from backend.db import transaction
from backend.models.db import (ActionCandidate, AiRun, Business, RecordAssociation, SourceRecord, SourceVersion)
from backend.services.ai import call_types, context, openrouter, skills, validate
from backend.services.read_models import portfolio
from backend.services.shared.errors import ThrottledError
from backend.services.shared.hashing import canonical_hash
from backend.workers import queue

JOB = "ai.run"


class AiRefused(ThrottledError):
    """The AI is off or over budget: the job waits (retries later), nothing is sent."""
    error_class = "ai_refused"


@dataclass
class Prepared:
    skill: skills.Skill
    subject_id: str
    business_id: UUID | None
    system: str
    user: str
    refs: context.Refs
    checker: validate.Checker
    checks: dict = field(default_factory=dict)

    @property
    def input_hash(self) -> str:
        return canonical_hash([self.skill.name, self.skill.version, skills.prompt_sha(self.skill),
                               skills.model_for(self.skill), self.system, self.user])


def _business_of(s, record_id) -> Business | None:
    return s.execute(select(Business).join(RecordAssociation, RecordAssociation.business_id == Business.id)
                     .where(RecordAssociation.record_id == record_id, RecordAssociation.status == "associated",
                            Business.status == "active").order_by(Business.name).limit(1)).scalar_one_or_none()


def _names(s, business, refs, extra=()) -> set[str]:
    from backend.models.db import AccountTeamMember, Contact, Person
    names = {t["who"] for t in refs.items.values() if t.get("who")} | set(extra)
    if business is not None:
        names |= set(s.execute(select(Person.name).join(AccountTeamMember, AccountTeamMember.person_id == Person.id)
                               .where(AccountTeamMember.business_id == business.id)).scalars())
        names |= {c for c in s.execute(select(Contact.display_name).where(Contact.business_id == business.id,
                                                                           Contact.status == "approved")).scalars() if c}
    return names


def prepare(s, skill_name: str, subject_id: str, *, fetch=None, now: datetime | None = None) -> Prepared:
    skill = skills.SKILLS[skill_name]
    now = now or datetime.now(UTC)
    refs, b, blocks = context.Refs(), skill.budgets, {}
    if skill.subject_kind == "meeting":
        record = s.get(SourceRecord, UUID(subject_id))
        version = s.get(SourceVersion, record.current_version_id)
        business = None if skill_name == "team_meeting_digest" else _business_of(s, record.id)
        if skill_name == "meeting_digest" and business is None:
            raise ValueError("this meeting is not linked to an active client")
        people = context.People(s, business.id if business else None)
        blocks["meeting"] = context.meeting(s, record, version, people)
        blocks["transcript"] = context.transcript(s, version, people, refs, b["transcript"])
        if business is None:
            blocks["client_list"] = context.client_list(s)
        else:
            since = context.last_meeting_before(s, business, record.occurred_at)
            blocks["client_card"] = context.client_card(s, business)
            blocks["open_actions"] = context.open_actions(s, business, people, refs, b["open_actions"], subject=subject_id)
            blocks["previous_digest"] = context.previous_digest(s, business, record.occurred_at)
            blocks["client_emails"] = context.client_emails(s, business, since, record.occurred_at + timedelta(days=1),
                                                            people, refs, b["client_emails"], fetch=fetch)
            for viktor, key in ((False, "internal_comms"), (True, "viktor_posts")):
                blocks[key] = context.slack_posts(s, business, since, record.occurred_at + timedelta(days=1), people, refs,
                                                  b[key], viktor=viktor)
        invitees = [i.get("name") for i in version.attributes.get("invitees", [])]
        meeting_date = record.occurred_at.astimezone(context.WIA_TZ).date() if record.occurred_at else None
        checks = {"meeting_date": record.occurred_at.isoformat() if record.occurred_at else "", "version": str(version.id)}
        clients = set(s.execute(select(Business.slug).where(Business.status == "active")).scalars())
    elif skill.subject_kind == "call":
        record = s.get(SourceRecord, UUID(subject_id))
        version = s.get(SourceVersion, record.current_version_id)
        business = _business_of(s, record.id)
        if business is None:
            raise ValueError("this calendar event is not linked to an active client")
        people = context.People(s, business.id)
        ct = call_types.detect(version.attributes.get("summary"))
        since = context.last_meeting_before(s, business, record.occurred_at)
        blocks["calendar_event"] = context.calendar_event(record, version, people, refs)
        blocks["call_type"] = context.call_type(ct)
        blocks["client_card"] = context.client_card(s, business)
        blocks["previous_digest"] = context.previous_digest(s, business, record.occurred_at, limit=2)
        blocks["open_actions"] = context.open_actions(s, business, people, refs, b["open_actions"], subject=subject_id)
        blocks["client_emails"] = context.client_emails(s, business, since, now, people, refs, b["client_emails"], fetch=fetch)
        for viktor, key in ((False, "internal_comms"), (True, "viktor_posts")):
            blocks[key] = context.slack_posts(s, business, since, now, people, refs, b[key], viktor=viktor)
        blocks["leads_summary"] = context.leads_summary(s, business)
        invitees, meeting_date, clients = [], now.astimezone(context.WIA_TZ).date(), set()
        checks = {"call_type": ct.key, "starts_at": record.occurred_at.isoformat() if record.occurred_at else "",
                  "version": str(version.id), "since": since.isoformat()}
    elif skill.subject_kind == "client":  # history_moments: the client slug
        business = s.execute(select(Business).where(Business.slug == subject_id)).scalar_one()
        people = context.People(s, business.id)
        blocks["client_card"] = context.client_card(s, business)
        blocks["activity"] = context.activity(s, business, refs, b["activity"])
        blocks["digests"] = context.meeting_decisions(s, business, refs, b["digests"])
        invitees, meeting_date, clients = [], now.astimezone(context.WIA_TZ).date(), set()
        checks = {"week": now.strftime("%G-W%V")}
    else:  # email_batch: "<client slug>:<window end ISO>"
        slug, _, end = subject_id.partition(":")
        business = s.execute(select(Business).where(Business.slug == slug)).scalar_one()
        until = datetime.fromisoformat(end)
        since = until - timedelta(hours=get_settings().ai_email_batch_hours)
        people = context.People(s, business.id)
        blocks["client_card"] = context.client_card(s, business)
        blocks["open_actions"] = context.open_actions(s, business, people, refs, b["open_actions"], subject=subject_id)
        blocks["client_emails"] = context.client_emails(s, business, since, until, people, refs, b["client_emails"],
                                                        fetch=fetch, limit=40)
        invitees, meeting_date, clients = [], until.astimezone(context.WIA_TZ).date(), set()
        checks = {"since": since.isoformat(), "until": until.isoformat()}
    checks["clipped"] = {k: v.clipped for k, v in blocks.items() if v.clipped}
    values = {k: v.text for k, v in blocks.items()}
    checker = validate.Checker(refs, names=_names(s, business, refs, invitees), meeting_date=meeting_date,
                               clients=clients)
    return Prepared(skill, subject_id, business.id if business else None, skills.render(skill.system_file, {}),
                    skills.render(skill.user_file, values), refs, checker, checks)


def month_spend(s, now: datetime) -> Decimal:
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return s.scalar(select(func.coalesce(func.sum(AiRun.cost_usd), 0)).where(AiRun.created_at >= start))


def _store(s, p: Prepared, *, state, model, output=None, answer=None, error=None, latency=None) -> AiRun:
    run = AiRun(id=uuid4(), skill=p.skill.name, skill_version=p.skill.version, model=model,
                subject_kind=p.skill.subject_kind, subject_id=p.subject_id, business_id=p.business_id,
                input_hash=p.input_hash, state=state, prompt_tokens=answer.prompt_tokens if answer else 0,
                completion_tokens=answer.completion_tokens if answer else 0,
                cost_usd=Decimal(str(answer.cost_usd)) if answer else Decimal(0), latency_ms=latency,
                error_class=error, refs=p.refs.items, output=output,
                checks={**p.checks, "dropped": p.checker.dropped, "unverified": p.checker.unverified,
                        "repaired": bool(answer and answer.repaired)},
                is_current=state == "succeeded")
    if state == "succeeded":
        s.execute(update(AiRun).where(AiRun.skill == p.skill.name, AiRun.subject_id == p.subject_id, AiRun.is_current)
                  .values(is_current=False))
    s.add(run)
    s.flush()
    return run


def _uuid(value) -> UUID | None:
    return UUID(value) if value else None


def _candidates(s, p: Prepared, run: AiRun, output: dict) -> None:
    s.execute(update(ActionCandidate).where(ActionCandidate.status == "proposed", ActionCandidate.run_id.in_(
        select(AiRun.id).where(AiRun.skill == p.skill.name, AiRun.subject_id == p.subject_id, AiRun.id != run.id)))
        .values(status="superseded"))
    slugs = dict(s.execute(select(Business.slug, Business.id)).all())
    for c in output.get("commitments", []):
        if c.get("matches_action"):
            continue  # already on WIA's list: nothing new to propose
        target = p.refs.items.get(c["ref"], {})
        business_id = slugs.get(c.get("client")) if "client" in c else p.business_id
        s.add(ActionCandidate(id=uuid4(), run_id=run.id, business_id=business_id, kind="new", title=c["text"],
                              owner_side=c["owner_side"], owner_name=c.get("owner_name"),
                              due_date=c.get("due_date") and datetime.fromisoformat(c["due_date"]).date(),
                              due_phrase=c.get("due_phrase"), quote=c["quote"],
                              source_record_id=_uuid(target.get("record_id")), unit_id=_uuid(target.get("unit_id")),
                              verified=c["verified"]))
    for u in output.get("action_updates", []):
        target = p.refs.items.get(u["ref"], {})
        s.add(ActionCandidate(id=uuid4(), run_id=run.id, business_id=p.business_id, kind="update",
                              title=p.refs.texts.get(u["action_ref"], ""), signal=u["signal"],
                              target_action_ref=p.refs.items[u["action_ref"]].get("action_ref"), quote=u["quote"],
                              source_record_id=_uuid(target.get("record_id")), unit_id=_uuid(target.get("unit_id")),
                              verified=True))


def run(skill_name: str, subject_id: str, *, client=None, fetch=None) -> AiRun | None:
    settings = get_settings()
    with transaction() as s:
        p = prepare(s, skill_name, subject_id, fetch=fetch)
        done = s.execute(select(AiRun).where(AiRun.skill == skill_name, AiRun.input_hash == p.input_hash,
                                             AiRun.state == "succeeded")).scalar_one_or_none()
        if done is not None:
            return done  # same inputs, same prompts, same model: never paid for twice
        if settings.ai_mode != "live":
            raise AiRefused("AI_MODE is off", retry_after=3600)
        if month_spend(s, datetime.now(UTC)) + Decimal(str(p.skill.max_cost_usd)) > Decimal(str(settings.ai_monthly_budget_usd)):
            raise AiRefused("monthly AI budget reached", retry_after=6 * 3600)
    model, started = skills.model_for(p.skill), time.monotonic()
    try:
        answer = openrouter.call(p.skill.contract, model=model, system=p.system, user=p.user,
                                 schema=contracts_schema(p.skill), max_tokens=p.skill.max_tokens,
                                 reasoning=p.skill.reasoning, client=client)
    except (openrouter.RoutingError, openrouter.ProviderError) as error:
        with transaction() as s:
            _store(s, p, state="failed", model=model, error=type(error).__name__,
                   latency=int((time.monotonic() - started) * 1000))
        raise
    output = validate.check(skill_name, answer.output.model_dump(), p.checker)
    with transaction() as s:
        stored = _store(s, p, state="succeeded", model=answer.model, output=output, answer=answer,
                        latency=int((time.monotonic() - started) * 1000))
        _candidates(s, p, stored, output)
        portfolio.request_refresh(s)
    return stored


def contracts_schema(skill: skills.Skill) -> dict:
    from backend.services.ai.contracts import strict_schema
    return strict_schema(skill.contract)


def run_job(work_id, lease_token, payload: dict) -> None:
    run(payload["skill"], payload["subject_id"])
    with transaction() as s:
        queue.complete(s, work_id, lease_token)
