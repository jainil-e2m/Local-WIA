"""The evaluation command (E.B3): a named configuration, three samples or more, over the benchmark's development weeks.

Every request is built by the product's own prompt builders, leaves through provider.send with the recorded privacy
routing (S.B1), and is reserved and settled against an active run plan (E.B1). Responses and reports are written under
research/benchmark-v1/ because they carry call excerpts (R48).

Reported per configuration and week: public cards and internal insights, pillar mix, E.B10 ledger flags (blocking and
to check), cards without a WIA contribution, near-duplicate titles inside a slate, alignment with Whitney's Week 1
reframes, E.B3's card regression cases, cost, and the variance across samples. The pairwise judge (`judge-compare`,
evaluation/judge.py) compares two configurations' saved samples; it stays a smoke test, never the gate.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import time
from contextlib import contextmanager

import httpx

from backend_pipeline.angle_profiles import (STRATEGIST_V4_PROFILE, STRATEGIST_V5_PROFILE, STRATEGIST_V6_PROFILE,
                                             STRATEGIST_V7_PROFILE, card_contract,
                                             card_schema, resolve_card_references, scene_references, strategist_angle_prompt,
                                             uses_scene_references)
from backend_pipeline.card_contracts import card_point
from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.cycle import verification
from backend_pipeline.knowledge.assembly import assemble
from backend_pipeline.llm.run_plans import from_environment
from backend_pipeline.prompts import angle_prompt
from backend_pipeline.llm.transport import dispatch_retrying_empty
from backend_pipeline.store import canonical_hash
from backend_pipeline.strategy_contracts import StrategicAngleResponse

from . import regressions
from .benchmark import RESEARCH, SOURCES, VERSION, guard, whitney_alternatives

OUT = RESEARCH / "benchmark-v1"
KB = BACKEND_ROOT / "knowledge_base"
# A compiled knowledge-base version under test (L.B4: an identity change needs this smoke result before it becomes
# the default). Unset: the file knowledge base, as every earlier result used. The scheduled benchmark (L.B11) also sets
# where samples are saved (`out`), the plan it spends under (`plan`), a label for the file knowledge base's samples and
# the model of record (`model`; unset: the configuration's own).
CONTEXT = {"version": None, "connection": None, "out": None, "plan": None, "label": None, "model": None}


@contextmanager
def under(**values):
    """Run with these CONTEXT values, restoring the previous ones afterwards (the scheduled benchmark, L.B11)."""
    previous = dict(CONTEXT)
    CONTEXT.update(values)
    try:
        yield
    finally:
        CONTEXT.clear()
        CONTEXT.update(previous)


def out_dir():
    return CONTEXT.get("out") or OUT


def knowledge(stage):
    """The stage's context from the assembly service (L.B5), for the version under test."""
    return assemble(stage, root=KB, connection=CONTEXT["connection"], version=CONTEXT["version"])
CONFIGS = {
    # The default benchmark v1 recorded: the legacy profile's version 1 on the angles model (kept byte for byte, so its
    # saved samples are reused; version 2 moves the Reel scripts out of the user message, E.B11 (3)).
    "default": {"profile": "2026-10-16.reel-editorial.v1", "model": "openai/gpt-6-luna", "effort": None},
    "strategist_v4": {"profile": STRATEGIST_V4_PROFILE, "model": "openai/gpt-6.1-sol", "effort": "high"},
    "strategist_v5": {"profile": STRATEGIST_V5_PROFILE, "model": "openai/gpt-6.1-sol", "effort": "high"},
    # E.B26: stance and experience, the pillar mix and fewer template titles; the same model and packets as v5.
    "strategist_v6": {"profile": STRATEGIST_V6_PROFILE, "model": "openai/gpt-6.1-sol", "effort": "high"},
    # E.B30, E.B32, E.B29 change: the point tests, beliefs to prove and her card format; the same model and packets as v6. The
    # strategy brief is assembled for a pinned date (the delivery week), so a saved sample's request stays the same.
    "strategist_v7": {"profile": STRATEGIST_V7_PROFILE, "model": "openai/gpt-6.1-sol", "effort": "high", "brief_on": "2026-10-27"},
    # E.B11: the same request without the exemplar bank, to measure what the bank adds.
    "strategist_v5_no_exemplars": {"profile": STRATEGIST_V5_PROFILE, "model": "openai/gpt-6.1-sol", "effort": "high",
                                   "without": ("exemplars",)},
}
WEEKS = {"week1": SOURCES["week1_excerpts"], "week2": SOURCES["week2_excerpts"]}
# A title in the template section 1.9.2 counts: "Why we...", "What we...", "How we...", "We..." (E.B26).
TEMPLATE_TITLE = re.compile(r"^\s*(?:(?:why|what|how|when|where)\s+(?:we|wia)\b|we\b)", re.I)
STOP = set("the a an and or of to in for on with your you we our is are that this it as how what why when their they".split())


def seconds(stamp):
    h, m, s = (int(x) for x in stamp.split(":"))
    return h * 3600 + m * 60 + s


def packet(week):
    if week.endswith("_v2"):
        # Benchmark v2 (E.B27): the whole week's verified ledger scenes, already in the strategist's packet shape.
        from .packets import load
        built = load(week[:-3])
        if built["state"] != "complete":
            raise ValueError(f"Benchmark v2 packet {week} is {built['state']}: {built['coverage']['summary']}")
        return built["scenes"]
    rows = json.loads(guard(WEEKS[week]).read_text(encoding="utf-8"))
    return [{"moment_id": m["moment_id"], "source_ids": [m.get("meeting") or m["moment_id"]], "source_metadata": {}, "sensitivity": "unknown",
             "qualifications": [], "speaker_identity_status": "unverified_labels",
             "source_evidence": [{"span_id": f"{m['moment_id']}.t{i:03d}", "text": t["text"], "speaker": t["speaker"],
                                  "start_seconds": seconds(t["t"])} for i, t in enumerate(m["turns"])]} for m in rows]


SEPARATOR = "\n\n"  # between knowledge-base sections (knowledge_base.load_knowledge_base)


def without_document(kb, key):
    """The knowledge base with one document's section removed, everything else byte for byte the same."""
    from backend_pipeline.knowledge_base import _section
    document = kb.document(key)
    if document is None:
        return kb
    section = _section(document.entry, document.text, kb.format)
    if SEPARATOR + section not in kb.text:
        raise ValueError(f"The {key} section is not in the knowledge-base text as rendered")
    return kb.model_copy(update={"documents": [d for d in kb.documents if d.entry.key != key],
                                 "text": kb.text.replace(SEPARATOR + section, "", 1)})


def model_of(config_name):
    """The model a configuration runs on: the scheduled benchmark's (L.B11) is the configuration of record's."""
    return CONTEXT.get("model") or CONFIGS[config_name]["model"]


def request(config_name, week):
    config = CONFIGS[config_name]
    moments = packet(week)
    if uses_scene_references(config["profile"]):
        kb = knowledge("strategist")
        for key in config.get("without", ()):
            kb = without_document(kb, key)
        brief = None
        if config.get("brief_on"):
            from datetime import date

            from backend_pipeline.cycle import strategy_brief
            brief = strategy_brief.assemble(kb, root=KB, on=date.fromisoformat(config["brief_on"]))
        system, user = strategist_angle_prompt(moments, kb, config["profile"], strategy_brief=brief)
        schema = card_schema(config["profile"])
    else:
        system, user = angle_prompt(moments, [], config["profile"])
        schema = StrategicAngleResponse.model_json_schema()
    body = {"model": model_of(config_name), "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": 40000, "usage": {"include": True},
            "response_format": {"type": "json_schema", "json_schema": {"name": "atelier_output", "strict": True, "schema": schema}}}
    if config["effort"]:
        body["reasoning"] = {"effort": config["effort"]}
    return body, moments


def _key():
    key = os.getenv("OPENROUTER_API_KEY")
    env = BACKEND_ROOT / ".env"
    if not key and env.is_file():
        key = next((line.split("=", 1)[1].strip().strip("'\"") for line in env.read_text(encoding="utf-8").splitlines()
                    if line.startswith("OPENROUTER_API_KEY=")), None)
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set")
    return key


def run_label():
    """Runs on a compiled knowledge-base version are saved apart from the file knowledge base's runs."""
    label = CONTEXT.get("label") or CONTEXT["version"]
    return f".{label}" if label else ""


def sample_path(config_name, week, sample):
    return out_dir() / "runs" / f"{config_name}-{week}-s{sample}{run_label()}.json"


def generate(config_name, week, sample, *, dry=False):
    """One sample; a saved response for the same request is reused, never paid for twice."""
    path = sample_path(config_name, week, sample)
    body, _ = request(config_name, week)
    fingerprint = canonical_hash({"benchmark": VERSION, "config": config_name, "week": week, "sample": sample, "body": body})
    if path.is_file():
        saved = json.loads(path.read_text(encoding="utf-8"))
        # Reused only for the same request: a sample saved under another knowledge base, prompt or model is never
        # reported as this configuration's (E.B3).
        if saved.get("request_fingerprint") != fingerprint:
            raise SystemExit(f"{path.name} was saved for another request; move it aside before re-running")
        return saved
    size = len(json.dumps(body, ensure_ascii=False))
    if dry:
        return {"dry": True, "characters": size}
    plan = CONTEXT.get("plan") or from_environment(default_file=OUT / "run_plan.json")
    started = time.time()
    try:
        # The llm module's single dispatch: the plan is checked first, so a missing key is a failed call that is settled,
        # with nothing sent; every reserved call is settled (E.B1), whatever happened to the request.
        # An answer with no content at its length limit is asked again once with a raised limit (E.B1), both calls planned.
        raw, _ = dispatch_retrying_empty(plan=plan, runs=None, stage="evaluation", model=body["model"], fingerprint=fingerprint,
                       url="https://openrouter.ai/api/v1/chat/completions", body=body, timeout=900,
                       headers=lambda: {"Authorization": "Bearer " + _key(), "Content-Type": "application/json",
                                        "X-Title": "Content Atelier evaluation"},
                       context={"prompt_version": VERSION, "knowledge_base_version": CONTEXT["version"] or None})
    except httpx.HTTPStatusError as error:
        raise SystemExit(f"HTTP {error.response.status_code}: {error.response.text[:500]}") from error
    content = raw["choices"][0]["message"].get("content") or ""
    try:
        output = json.loads(content)
    except ValueError:
        output = None
    record = {"config": config_name, "week": week, "sample": sample, "model": body["model"], "benchmark": VERSION,
              "cost": (raw.get("usage") or {}).get("cost") or 0, "usage": raw.get("usage"), "seconds": round(time.time() - started, 1),
              "finish": raw["choices"][0].get("finish_reason"), "request_fingerprint": fingerprint, "output": output,
              **({"raw_content": content} if output is None else {})}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    if output is None:
        # The paid answer is kept for inspection; move the file aside to ask again.
        raise SystemExit(f"{path.name}: the response did not parse as JSON; it is saved for inspection")
    return record


def cards_of(config_name, week, output):
    """Card-shaped views: strategist output is resolved and contract-checked; the default's strategic angles map across."""
    profile = CONFIGS[config_name]["profile"]
    if uses_scene_references(profile):
        card_contract(profile).model_validate(output)
        out = resolve_card_references(output, scene_references(packet(week)))
        return out["angles"], out.get("internal_insights", [])
    StrategicAngleResponse.model_validate(output)
    cards = [{"rank": i, "title": a["title"], "pillar": a["strategic_purpose"], "content_type": a["content_type"], "audience": a["audience"],
              "core_perspective": a["core_perspective"], "why_it_matters": a["tension"], "wia_in_action": a.get("wia_expertise_in_action"),
              "offer_connection": a.get("service_relevance"), "moment_ids": a["moment_ids"], "evidence_points": a.get("source_assertions", [])}
             for i, a in enumerate(output["angles"], 1)]
    return cards, output.get("internal_insights", [])


def _words(text):
    return {w for w in re.findall(r"[a-z']+", (text or "").lower()) if len(w) > 3 and w not in STOP}


def _jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


def sample_metrics(config_name, week, record):
    cards, internal = cards_of(config_name, week, record["output"])
    scenes = {m["moment_id"]: m["source_evidence"] for m in packet(week)}
    roster, rules = knowledge("verifier").roster, verification.load_rules(KB)
    ledgers = [verification.verify_card(c, scenes, roster, rules) for c in cards]
    titles = [_words(c["title"]) for c in cards]
    near = sum(1 for i in range(len(titles)) for j in range(i + 1, len(titles)) if _jaccard(titles[i], titles[j]) >= 0.5)
    metrics = {"public_cards": len(cards), "internal_insights": len(internal),
               "pillars": {p: sum(c["pillar"] == p for c in cards) for p in ("ATTRACT", "WARM", "CONVERT")},
               "blocking_flags": sum(len(verification.blocking(x)) for x in ledgers),
               "check_flags": sum(sum(f["severity"] == "check" for f in x["flags"]) for x in ledgers),
               "style_warnings": sum(sum(f["severity"] == "style" for f in x["flags"]) for x in ledgers),
               "without_wia_contribution": sum(any(f["kind"] == "no_wia_contribution" for f in x["flags"]) for x in ledgers),
               # Strategist v7 (E.B30): public cards the deterministic point tests reject for public use, and why.
               "rejected_for_public_use": sum(bool(x.get("public_use")) for x in ledgers),
               "public_use_reasons": [{"title": c["title"], "kinds": x["public_use"]["kinds"]} for c, x in zip(cards, ledgers)
                                      if x.get("public_use")],
               "near_duplicate_title_pairs": near, "template_titles": sum(bool(TEMPLATE_TITLE.match(c["title"])) for c in cards),
               "cost": record["cost"], "titles": [c["title"] for c in cards],
               # E.B3's regression cases: public cards failing each one.
               "regressions": regressions.card_counts(cards, ledgers, scenes, roster)}
    if week == "week1":
        alternatives = whitney_alternatives(guard(SOURCES["week1_alternatives"]).read_text(encoding="utf-8"))
        targets = [_words(" ".join(filter(None, [a["title"], a["why_it_matters"], a["wia_expertise"]]))) for a in alternatives]
        scores = [max(_jaccard(_words(c["title"] + " " + (card_point(c) or "")), t) for t in targets) for c in cards]
        metrics["reframe_alignment"] = round(statistics.mean(scores), 3) if scores else 0.0
    return metrics


def summarise(samples):
    keys = ("public_cards", "internal_insights", "blocking_flags", "check_flags", "style_warnings", "without_wia_contribution",
            "near_duplicate_title_pairs", "template_titles", "cost", "reframe_alignment")
    out = {}
    for key in keys:
        values = [s[key] for s in samples if key in s]
        if values:
            out[key] = {"mean": round(statistics.mean(values), 4), "stdev": round(statistics.pstdev(values), 4), "values": values}
    cases = [s["regressions"] for s in samples if "regressions" in s]
    if cases:
        out["regressions"] = {case: {"mean": round(statistics.mean(c[case] for c in cases), 4), "values": [c[case] for c in cases]}
                              for case in regressions.CARD_CASES}
    sets = [set(map(str.lower, s["titles"])) for s in samples]
    words = [set().union(*(_words(t) for t in s["titles"])) for s in samples]
    pairs = [(i, j) for i in range(len(samples)) for j in range(i + 1, len(samples))]
    out["title_stability"] = round(statistics.mean(_jaccard(words[i], words[j]) for i, j in pairs), 3) if pairs else None
    out["identical_titles_across_samples"] = len(set.intersection(*sets)) if sets else 0
    return out


def report(config_names, weeks, samples):
    result = {"benchmark": VERSION, "knowledge_base": knowledge("strategist").refs(), "configs": {}, "notes": [
        "Development weeks only (Weeks 1 and 2, excerpt-only moment packets, the same for every configuration); "
        "the held-out result is E.B13's.",
        "Ledger flags are E.B10's deterministic pass; a blocking flag is an unsupported fact, misattribution or consent problem.",
        "reframe_alignment is word overlap with Whitney's Week 1 alternatives: a proxy for her accepted share, not her verdict.",
        "regressions counts the public cards failing each of E.B3's card regression cases (evaluation/regressions.py); the "
        "brief cases (a local edit keeps untouched text, an approved line survives a revision) apply to brief revisions, "
        "which this command does not generate (they run on the product's Gate 2 path, test_regressions_db.py).",
        "Compare two configurations with the pairwise judge: python -m evaluation judge-compare --configs a,b (a smoke "
        "test, never the gate)."]}
    total = 0.0
    for name in config_names:
        result["configs"][name] = {"model": model_of(name), "profile": CONFIGS[name]["profile"], "weeks": {}}
        for week in weeks:
            rows = [sample_metrics(name, week, generate(name, week, s)) for s in range(1, samples + 1)]
            total += sum(r["cost"] for r in rows)
            result["configs"][name]["weeks"][week] = {"samples": rows, "summary": summarise(rows)}
    result["total_cost_usd"] = round(total, 4)
    return result
