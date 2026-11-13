"""Call prep inside the AI runner: prepare the brief (and the regenerate focus pass), check the answer with one
content repair, and store the version. The runner keeps the budget, the run log and the never-twice rule.

Options carried on the work item: {"trigger": first|final|skill_changed|regenerate, "built_by": ..., "instructions":
..., "focus_run": <ai_runs id of the call_focus pass>}.
"""
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from backend.models.db import AiRun
from backend.services.ai import context, openrouter, validate
from backend.services.callprep import briefs, checks, pack as packs, registry


def _call(s, subject_id: str):
    call = registry.get(s, UUID(subject_id))
    if call is None:
        raise ValueError("this calendar event is not linked to an active client")
    return call


def prepare_brief(s, skill, subject_id: str, *, fetch=None, now=None, options: dict | None = None):
    from backend.services.ai.runner import Prepared
    options = options or {}
    now = now or datetime.now(UTC)
    call = _call(s, subject_id)
    instructions = options.get("instructions")
    if instructions is None and options.get("trigger") != "regenerate":
        instructions = briefs.latest_instructions(s, call.record_id)
    extra, declined = [], None
    if options.get("focus_run"):
        focus = s.get(AiRun, UUID(options["focus_run"]))
        if focus is not None and focus.output:
            extra = packs.fetch_extra(s, call, focus.output.get("fetch", []), fetch=fetch)
            declined = focus.output.get("declined")
    p = packs.build(s, call, instructions=instructions or None, fetch=fetch, extra=extra, now=now)
    system, user = packs.render(p)
    # The call type's skill may set the reasoning level or a model; AI_MODELS still overrides the model.
    skill = replace(skill, reasoning=call.skill.reasoning or skill.reasoning, model=call.skill.model_id or skill.model)
    checker = validate.Checker(p.refs, names=set(), meeting_date=None)
    return Prepared(skill, subject_id, call.business.id, system, user, p.refs, checker,
                    {"call_type": call.skill.key, "skill_ref": call.skill.ref, "starts_at": call.starts_at.isoformat(),
                     "version": str(call.version_id), "fingerprint": p.fingerprint, "trigger": options.get("trigger", "first")},
                    extra={"pack": p, "options": options, "declined": declined})


def prepare_focus(s, skill, subject_id: str, *, options: dict | None = None):
    from backend.services.ai import skills as ai_skills
    from backend.services.ai.runner import Prepared
    call = _call(s, subject_id)
    offered = packs.extra_candidates(s, call)
    instructions = (options or {}).get("instructions") or ""
    user = ai_skills.render(skill.user_file, {
        "instructions": instructions,
        "call": f"{call.title} with {call.business.name} on {call.starts_at.astimezone(context.WIA_TZ):%Y-%m-%d}",
        "offered": "\n".join(f"{o['id']} · {o['label']} · {o['date']}" for o in offered) or "(nothing beyond the brief)"})
    return Prepared(skill, subject_id, call.business.id, ai_skills.render(skill.system_file, {}), user, context.Refs(),
                    validate.Checker(context.Refs(), names=set(), meeting_date=None),
                    {"instructions": instructions, "offered": len(offered)}, extra={"offered": {o["id"] for o in offered}})


def check_focus(p, output: dict) -> dict:
    output["fetch"] = [i for i in output.get("fetch", []) if i in p.extra["offered"]][:4]
    return output


def check_brief(p, output: dict, answer, *, model: str, client=None):
    """(checked output or None when rejected, the answer with any repair's cost added, the checks record)."""
    pk = p.extra["pack"]
    texts = packs.all_text(pk, p.system, p.user)
    run = checks.BriefChecks(pk.skill, pk.refs.items, texts)
    checked, core = run.run(output)
    repaired = False
    if core:
        failures = "; ".join(f"{d['where']}: {d['why']}" for d in run.dropped if d["where"] in core) or ", ".join(core)
        try:
            again = openrouter.call(type(answer.output), model=model, system=p.system,
                                    user=p.user + "\n\n## Your previous answer failed these checks\n" + failures +
                                    "\nAnswer again. Use only figures that appear in the input, and cite refs.",
                                    schema=_schema(p), max_tokens=p.skill.max_tokens, reasoning=p.skill.reasoning,
                                    client=client)
        except (openrouter.RoutingError, openrouter.ProviderError) as error:
            again = None
            # The failed repair may still have been billed: keep its cost on the run (estimated when unknown).
            spent = getattr(error, "spent", None)
            if spent is not None:
                extra = max(spent.cost_usd, p.skill.max_cost_usd) if spent.unknown else spent.cost_usd
                answer = replace(answer, prompt_tokens=answer.prompt_tokens + spent.prompt_tokens,
                                 completion_tokens=answer.completion_tokens + spent.completion_tokens,
                                 cost_usd=answer.cost_usd + extra)
        if again is not None:
            answer = replace(again, prompt_tokens=answer.prompt_tokens + again.prompt_tokens,
                             completion_tokens=answer.completion_tokens + again.completion_tokens,
                             cost_usd=answer.cost_usd + again.cost_usd, repaired=True)
            run = checks.BriefChecks(pk.skill, pk.refs.items, texts)
            checked, core = run.run(again.output.model_dump())
            repaired = True
    declined = p.extra.get("declined")
    if declined and not checked.get("declined"):
        checked["declined"] = declined
    record = {"dropped_lines": run.dropped, "core_failed": core, "content_repaired": repaired}
    return (None if core else checked), answer, record


def _schema(p):
    from backend.services.ai.contracts import strict_schema
    return strict_schema(p.skill.contract)


def store(s, p, run_id, checked: dict | None, record: dict) -> None:
    o = p.extra["options"]
    briefs.save(s, p.extra["pack"], output=checked, checks=record, ai_run_id=run_id,
                trigger=o.get("trigger", "first"), built_by=o.get("built_by", "auto"))


def latest_focus(s, subject_id: str) -> AiRun | None:
    return s.execute(select(AiRun).where(AiRun.skill == "call_focus", AiRun.subject_id == subject_id, AiRun.is_current)).scalar_one_or_none()
