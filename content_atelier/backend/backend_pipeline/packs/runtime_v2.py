"""A content pack v2 run's model calls and frozen contract (NP.B7 to NP.B9; the content-packs plan, sections 5.3 to 5.5).

- **The frozen contract.** At the run's first stage the contract is written into the run's `input_refs`: the models, the
  reasoning efforts, the prompt profiles and their hashes, the answer schemas, the knowledge base's version and identity
  documents, and the finish mode. A later stage fails when it changed (`CONTEXT_CHANGED_MESSAGE`). The output cap
  (`models.completion_tokens`) is an operating limit and stays outside (K74), so raising it never voids a run (NP.B9).
- **The call** goes through `llm.workflow.chat` with the pack's own flow: the response cache (`pack-cache`, keyed by the
  request), recovery of an earlier attempt's answer, S.B1's privacy routing, the `packs` standing budget, an `llm_runs`
  row, and one repair for an answer that breaks its schema. A replayed call costs USD 0, so a saved pack replays byte for
  byte in a fresh database (0.B4).
- **The budget of a run** is 12 chat calls, repairs included (the finisher, the check, the repair and the re-check, each
  with its one repair, fit with room). The system prefix (prompt and knowledge base) does not count against
  `briefs.max_characters`, as for briefs.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..costs import call_record, write_run_summary
from ..artifacts import store_for
from ..llm import stage_body, workflow_fingerprint
from ..llm.workflow import Flow, chat
from ..store import canonical_hash
from . import contracts_v2 as c2

WORKFLOW = c2.VERSION
CONTEXT_CHANGED = "Frozen pack execution contract changed"
CONTEXT_CHANGED_MESSAGE = CONTEXT_CHANGED + "; restore it, or finish the pack again (a new run)"
FLOW_BUDGET = 12
TEMPLATES = Path(__file__).resolve().parent.parent / "prompt_templates"


def mode_for(settings) -> str:
    """The mode a pack run is queued in: synthetic on an isolated test database; live where both generation switches are
    on (ATELIER_ALLOW_GENERATION and ATELIER_ALLOW_PACK_GENERATION, each exactly `true`); otherwise replay (saved responses
    only)."""
    if settings.synthetic:
        return "synthetic"
    return "live" if settings.generation_enabled and settings.pack_live_enabled else "replay"


def finish_mode(settings) -> str:
    mode = getattr(settings, "pack_finish_mode", None) or "finish"
    if mode not in c2.FINISH_MODES:
        raise ValueError(f"Unknown packs.finish_mode {mode}; one of {', '.join(c2.FINISH_MODES)}")
    return mode


def profiles(settings) -> dict[str, str]:
    """The prompt profile of each pack stage (prompts.profile.pack_*); the re-check uses the check's."""
    found = {"pack_finish": settings.pack_finish_profile, "pack_check": settings.pack_check_profile,
             "pack_repair": settings.pack_repair_profile,
             # NP-7's passes: a settings object from before them has no key, and takes the released default.
             "pack_caption": getattr(settings, "pack_caption_profile", None) or c2.PROFILES["pack_caption"],
             "pack_refinish": getattr(settings, "pack_refinish_profile", None) or c2.PROFILES["pack_refinish"]}
    for stage, profile in found.items():
        if profile not in c2.TEMPLATES:
            raise ValueError(f"Unknown prompt profile {profile} for {stage}")
    # Round 2: a premise finisher plans before it writes (contracts_v2.PLAN_PROFILE), in the same step.
    planner = c2.PLAN_FOR.get(found["pack_finish"]) or c2.PLAN_FOR.get(found["pack_refinish"])
    plan = {"pack_plan": planner} if planner else {}
    return {**found, "pack_recheck": found["pack_check"], **plan}


def template(profile: str) -> str:
    from .. import prompt_files
    return prompt_files.read(TEMPLATES / c2.TEMPLATES[profile])


def writer_model(worker) -> str:
    return worker.storage.pack_writer_model or worker.models.openrouter_angles_model


def review_model(worker) -> str:
    return worker.storage.pack_review_model or worker.models.openrouter_angles_model


def model_for(worker, stage: str) -> str:
    return review_model(worker) if stage in c2.REVIEW_STAGES else writer_model(worker)


def knowledge(worker, run=None):
    """The finisher's knowledge base (the assembly service's `pack` stage), assembled for the run's date, so every stage of
    one run and a retry after midnight see the same documents."""
    from ..knowledge.assembly import assemble
    repo = getattr(worker, "repo", None)
    on = run["created_at"].date() if run and hasattr(run.get("created_at"), "date") else None
    kb = assemble("pack", root=worker.models.knowledge_base_root, connection=repo.connection if repo else None, on=on,
                  allow_placeholders=worker.storage.synthetic)
    if not worker.storage.synthetic:
        from ..knowledge import held_out
        held_out.check_live(kb.text)
    return kb


# The writer steps that take the knowledge base as their trusted prefix (the house style and Whitney's finished pieces).
KB_STAGES = ("pack_finish", "pack_caption", "pack_refinish")


def system(worker, run, stage: str, profile: str | None = None) -> tuple[str, str | None]:
    """A stage's system prompt and the knowledge-base version it carries: the finisher and NP-7's two passes take the
    knowledge base as their trusted prefix; the check and the repair take their sources in the user message. `profile`
    names another prompt for the stage's step (finisher v3's plan)."""
    profile = profile or profiles(worker.storage)[stage]
    text = template(profile)
    if stage in KB_STAGES:
        kb = knowledge(worker, run)
        return kb.text.strip() + "\n\n" + text, kb.refs().get("version")
    return text, None


def execution_contract(worker, run=None) -> dict:
    kb = knowledge(worker, run)
    found = profiles(worker.storage)
    return {"version": c2.VERSION, "writer": writer_model(worker), "reviewer": review_model(worker),
            "endpoint": worker.models.openrouter_base_url, "max_tokens": worker.models.llm_completion_tokens,
            "reasoning_effort": {s: worker.models.reasoning_effort_for(s) for s in ("pack_finish", "pack_check", *c2.LATER_STAGES)},
            "response_format": worker.models.llm_response_format, "synthetic": worker.storage.synthetic,
            "finish_mode": finish_mode(worker.storage), "profiles": found,
            "prompt_hashes": {s: canonical_hash(template(p)) for s, p in sorted(found.items())},
            "schema_hashes": {s: canonical_hash(c2.wire_schema(s, found.get(s)))
                              for s in sorted(set(c2.OUTPUTS) | ({"pack_plan"} & set(found)))},
            "knowledge_base": kb.refs()}


def stable_contract(contract):
    """What must not change while a run is in flight: everything but the output cap (K74, NP.B9), with the knowledge base
    reduced to its version and identity documents (operating facts confirmed mid-run are used as they stand), compared as
    JSON: the frozen copy comes back from the database, where a tuple is a list (found by NP.X1's shakedown: every pack's
    second stage failed as "changed" against a database-backed knowledge base)."""
    if not contract:
        return contract
    from ..knowledge.assembly import stable_refs
    out = {k: v for k, v in contract.items() if k != "max_tokens"}
    if isinstance(out.get("knowledge_base"), dict):
        out["knowledge_base"] = stable_refs(out["knowledge_base"])
    return json.loads(json.dumps(out, sort_keys=True, default=str))


def require_live_models(worker, run, stage):
    """A live pack names its models explicitly: no silent fallback to the default model."""
    if run["input_refs"].get("mode") != "live":
        return
    if stage in c2.REVIEW_STAGES and not worker.storage.pack_review_model:
        raise ValueError("A live pack needs models.pack_review (ATELIER_PACK_REVIEW_MODEL) set explicitly for " + stage)
    if stage not in c2.REVIEW_STAGES and not worker.storage.pack_writer_model:
        raise ValueError("A live pack needs models.pack_writer (ATELIER_PACK_WRITER_MODEL) set explicitly for " + stage)


def check_dependencies(worker, run):
    """The run binds to the approved brief's hash and to "no replacement brief"; it does not re-run Gate 2's live blockers,
    so a prior-use change elsewhere cannot fail it part way (section 5.3)."""
    refs = run["input_refs"]
    if not worker.storage.packs_enabled:
        raise ValueError("Content packs are switched off (features.packs)")
    frozen = refs.get("execution_contract")
    if frozen is not None and stable_contract(frozen) != stable_contract(execution_contract(worker, run)):
        raise ValueError(CONTEXT_CHANGED_MESSAGE)
    with worker.repo.connection() as conn:
        brief = conn.execute("SELECT brief_id,approval_status,approved_hash FROM content_briefs WHERE brief_id=%s",
                             (refs["brief"]["brief_id"],)).fetchone()
        if not brief or brief["approval_status"] != "approved" or brief["approved_hash"] != refs["brief"]["approved_hash"]:
            raise ValueError("The approved brief changed since the pack was started; start the pack again from the brief")
        if conn.execute("SELECT 1 FROM content_briefs WHERE supersedes_id=%s", (brief["brief_id"],)).fetchone():
            raise ValueError("A newer version of the brief exists; approve it to get its pack")


def record(worker, job, run, stage, fingerprint, raw=None, *, dispatched=False, reused=False):
    store = store_for(worker.storage)
    directory = f"pack-runs/{run['run_id']}"
    value = call_record(raw=raw, dispatched=dispatched and not worker.storage.synthetic, reused=reused, stage=stage,
                        job_id=job["job_id"], attempt=job["attempt_count"], fingerprint=fingerprint,
                        synthetic=worker.storage.synthetic, real_external_dispatch=dispatched and not worker.storage.synthetic)
    store.write_json(f"{directory}/costs/{job['job_id']}-{job['attempt_count']}-{stage}-{fingerprint}.json", value, overwrite=True)
    return write_run_summary(store, directory, stages_to_report=c2.MODEL_STAGES)


def flow() -> Flow:
    return Flow(name="pack", workflow=WORKFLOW, cache="pack-cache", attempts="pack-attempts", artifact_prefix="pack_artifact_",
                budget=FLOW_BUDGET, live_enabled=lambda worker: worker.storage.pack_live_enabled, record=record)


def request_for(worker, run, stage: str, packet: dict, profile: str | None = None) -> tuple[dict, str, str, str | None]:
    """The request a stage sends (deterministic for the same inputs, so a saved response replays): (request, prompt,
    payload, knowledge-base version)."""
    profile = profile or profiles(worker.storage)[stage]
    prompt, kb_version = system(worker, run, stage, profile)
    payload = json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str)
    request = stage_body(worker.models, stage, prompt, payload, c2.wire_schema(stage, profile), model=model_for(worker, stage))
    return request, prompt, payload, kb_version


def call(worker, job, run, stage: str, packet: dict, profile: str | None = None):
    """One pack stage call; returns the validated answer (contracts_v2.output_model for the stage's profile). `profile`
    names another prompt for the stage's step: finisher v3's plan runs under pack_finish, with its own prompt and answer."""
    check_dependencies(worker, run)
    profile = profile or profiles(worker.storage)[stage]
    require_live_models(worker, run, stage)
    request, prompt, payload, kb_version = request_for(worker, run, stage, packet, profile)
    # The system prefix (prompt and knowledge base) does not count against the request limit (as briefs, E.B15 e).
    if len(json.dumps(request, ensure_ascii=False)) - len(json.dumps(prompt, ensure_ascii=False)) > worker.storage.brief_max_characters:
        raise ValueError(f"The {stage} request is larger than briefs.max_characters; nothing was left out to fit it")
    fp = workflow_fingerprint(workflow=WORKFLOW, stage=stage, request=request, endpoint=worker.models.openrouter_base_url,
                              synthetic=worker.storage.synthetic)
    return chat(flow(), worker, job, run, stage=stage, model=model_for(worker, stage), prompt=prompt, payload=payload,
                request=request, fp=fp, schema=c2.output_model(stage, profile), wire_schema=c2.wire_schema(stage, profile), packet=packet,
                knowledge_base_version=kb_version)
