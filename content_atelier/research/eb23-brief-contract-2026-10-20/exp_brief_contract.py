"""E.B23 measurement (prepared 20 October 2026, not yet run): does brief contract v3 give briefs that need no repair call
and show no new accuracy problem, against E.B22's v3-writer briefs?

The done-when (plan row E.B23): "On the live week's cards, at least two of three v3-contract briefs need no repair call and
show no new accuracy problem on the calibrated judge; v1 and v2 rows still render, export and pass their gates."

One arm is new: contract v3 on the product's own path (`briefs/workflow.py` writer_packet_v3, `briefs/runtime.py` system,
`briefs/contracts_v3.py` writer_schema_v3, writer v4), then the ledger built after writing (`briefs/validation_v3.py`
ledger_body: the rules, then the verifier from another family on what they could not settle), then the checks
(checks_v3) and, only when a blocking finding is left, the one repair (repair v4) with its guard against added hedging.
A schema failure gets the llm module's one schema repair (repair_user), as in the product. Every repair call is counted.

The other arm is E.B22's v3-writer brief for the same card, already saved in `research/final-reconciliation-2026-10-19/runs/`
(W-v3-*.json); it is not regenerated. The writer, the reasoning effort and the inputs are E.B22's: GPT-6.1 Sol at high
effort, the live development week's three developed cards and the evidence their briefs used
(`research/final-reconciliation-2026-10-19/inputs/`), and by default knowledge base version 4
(`backend/knowledge_base/archive/wia-kb-2026-10-18.c-0cb353e4`), byte for byte the one E.B22 wrote with, so the contract is
the variable. `--kb current` uses the committed knowledge base instead.

Judging: E.B22's calibrated configuration J2 and its brief-level question (`JUDGE_BASE`, imported unchanged), Claude Sonnet 5.5
with the knowledge base and the export's editing pack, in both presentation orders, on reader-facing text rendered in one
layout for both arms. The verifier is Claude Sonnet 5.5 too (the family R42 asks for against the OpenAI writer; the live
week's card verifier).

Every call goes through the product's `dispatch` (privacy routing, the file run plan `run_plan.json`, its ledger beside it);
saved responses under `runs/` are reused, never paid for twice. `--dry` builds every request it can and prints the call
count, characters and a cost estimate, and sends nothing.

Usage (from this folder, with the backend's Python):
    python exp_brief_contract.py --dry            # no call, no key read
    python exp_brief_contract.py plan             # writes run_plan.json (approver, caps); no call
    python exp_brief_contract.py write            # writer, verifier, repair where needed
    python exp_brief_contract.py judge            # six judge calls
    python exp_brief_contract.py report           # results/eb23-brief-contract.json
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
EB22 = REPO / "research" / "final-reconciliation-2026-10-19"
EXPORT = REPO / "research" / "chatgpt-export-2026-10-18"
for path in (REPO / "backend", EB22, EXPORT):
    sys.path.insert(0, str(path))

from backend_pipeline.briefs.contracts import Dossier  # noqa: E402
from backend_pipeline.briefs.contracts_v2 import BriefBodyV2  # noqa: E402
from backend_pipeline.briefs.contracts_v3 import SCHEMA_V3, BriefWriteV3, writer_part, writer_schema_v3  # noqa: E402
from backend_pipeline.briefs import ledger_v3  # noqa: E402
from backend_pipeline.briefs.runtime import system  # noqa: E402
from backend_pipeline.briefs.validation_v2 import copy_lint, repairable  # noqa: E402
from backend_pipeline.briefs.validation_v3 import (checks_v3, copy_lint_v3, hedging_added, header_for_v3, ledger_body,  # noqa: E402
                                                   repair_packet)
from backend_pipeline.briefs.workflow import writer_packet_v3  # noqa: E402
from backend_pipeline.costs import estimate_usd  # noqa: E402
from backend_pipeline.cycle.verification import BELIEF_DOCUMENT, belief_index, load_rules, rules_for  # noqa: E402
from backend_pipeline.knowledge.assembly import assemble  # noqa: E402
from backend_pipeline.llm.request import chat_body, repair_user  # noqa: E402

WRITER, VERIFIER, JUDGE = "openai/gpt-6.1-sol", "anthropic/claude-sonnet-5.5", "anthropic/claude-sonnet-5.5"
URL = "https://openrouter.ai/api/v1/chat/completions"
PLAN = HERE / "run_plan.json"
RUNS = HERE / "runs"
EB22_RUNS = EB22 / "runs"
KB_V4 = REPO / "backend" / "knowledge_base" / "archive" / "wia-kb-2026-10-18.c-0cb353e4"
KB_CURRENT = REPO / "backend" / "knowledge_base"
TEMPLATES = REPO / "backend" / "backend_pipeline" / "prompt_templates"
# Output tokens assumed by --dry where no response exists yet: the writer's from E.B22's v3 arm (8,016 to 9,974 with
# reasoning) plus the Reel scripts; a verdict per statement; the judge's from E.B22 (1,374 to 2,166).
OUT_WRITER, OUT_PER_STATEMENT, OUT_JUDGE = 11000, 60, 2200


def kb_root(choice: str) -> pathlib.Path:
    return KB_V4 if choice == "v4" else KB_CURRENT


def inputs() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((EB22 / "inputs").glob("angle_*.json"))]


def tag(record: dict) -> str:
    return record["angle_id"][-8:]


def input_set_hash(choice: str) -> str:
    """What the plan is approved for: the inputs, E.B22's saved v3 briefs, the v3 templates and the knowledge base."""
    digest = hashlib.sha256()
    paths = (sorted((EB22 / "inputs").glob("angle_*.json")) + sorted(EB22_RUNS.glob("W-v3-*.json"))
             + [TEMPLATES / n for n in ("brief_write.v4.md", "brief_repair.v4.md", "brief_verify.v1.md")]
             + [kb_root(choice) / "manifest.json"])
    for path in paths:
        digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


# The product's inputs, rebuilt from the stored card, brief and dossier ---------------------------------------------

def run_and_dossier(record: dict) -> tuple[dict, dict]:
    """The brief run and dossier the product would hold for this card (E.B22's packet: no person CTA, no exemplars)."""
    card = record["card"]
    header = record["first_brief"]["document"]["header"]
    angle = {"angle_id": record["angle_id"], "week_id": "week_live_2026-10-18", "approved_hash": header["angle_hash"],
             "steer": None, "cta": None,
             "body": {"card": card, "title": card["title"], "argument": card["core_perspective"], "audience": card["audience"]}}
    run = {"run_id": "eb23-" + tag(record), "input_refs": {"angle": angle, "channels": header["channels"], "instructions": None,
                                                           "schema_version": SCHEMA_V3, "writer": "v4", "mode": "live"}}
    dossier = {"angle": angle, "evidence": record["selected_evidence"], "prior": record["prior_content_context"], "queries": [],
               "coverage": {}, "gaps": [], "audit": [], "brand": {"source": "knowledge_base", "hash": "kb", "documents": {}}}
    return run, dossier


def contexts(record: dict, choice: str):
    channels = record["first_brief"]["document"]["header"]["channels"]
    root = kb_root(choice)
    return root, assemble("brief", root=root, channels=tuple(channels)), assemble("verifier", root=root)


def provenance(record: dict, kb, verifier_kb) -> dict:
    document = getattr(verifier_kb, "document", None)
    saved = record["first_brief"].get("provenance") or {}
    return {"pinned_inputs": {}, "knowledge_base_keys": [d.entry.key for d in kb.documents],
            "roster": verifier_kb.roster, "internal_terms": [{"term": t["term"], "item_id": t["item_id"]} for t in verifier_kb.internal_terms],
            "clients": saved.get("clients") or [],
            "beliefs": belief_index(document(BELIEF_DOCUMENT)) if document else None}


def writer_request(record: dict, choice: str) -> tuple[dict, str]:
    run, dossier = run_and_dossier(record)
    _, kb, _ = contexts(record, choice)
    user = json.dumps(writer_packet_v3(run, dossier), ensure_ascii=False, sort_keys=True, default=str)
    body = chat_body(model=WRITER, system=system("brief_write", SCHEMA_V3, kb.text, "v4"), user=user,
                     schema=writer_schema_v3(run["input_refs"]["channels"]), reasoning_effort="high")
    body["usage"] = {"include": True}
    return body, user


def verifier_request(open_statements: list[dict], record: dict, choice: str, prov: dict) -> tuple[dict, dict]:
    run, _ = run_and_dossier(record)
    _, _, verifier_kb = contexts(record, choice)
    angle = run["input_refs"]["angle"]
    packet, refs = ledger_v3.verifier_packet(open_statements, record["selected_evidence"], prov["roster"],
                                             {"title": angle["body"]["title"], "core_perspective": angle["body"]["argument"]})
    body = chat_body(model=VERIFIER, system=system("brief_verify", SCHEMA_V3, verifier_kb.text),
                     user=json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str),
                     schema=ledger_v3.wire_schema())
    body["usage"] = {"include": True}
    return body, refs


def repair_request(document: dict, findings: list[dict], record: dict, choice: str) -> dict:
    run, dossier = run_and_dossier(record)
    _, kb, _ = contexts(record, choice)
    channels = run["input_refs"]["channels"]
    packet = repair_packet(document, Dossier.model_validate(dossier), findings, channels)
    body = chat_body(model=WRITER, system=system("brief_repair", SCHEMA_V3, kb.text, "v4"),
                     user=json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str), schema=writer_schema_v3(channels),
                     reasoning_effort="high")
    body["usage"] = {"include": True}
    return body


# Calls -------------------------------------------------------------------------------------------------------------

def key() -> str:
    """Read only when a call is actually sent (never by --dry): OPENROUTER_API_KEY from the environment, else backend/.env."""
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    for line in (REPO / "backend" / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("OPENROUTER_API_KEY missing")


def headers() -> dict:
    return {"Authorization": "Bearer " + key(), "Content-Type": "application/json", "X-Title": "Content Atelier E.B23 brief contract"}


def run_file(name: str) -> pathlib.Path:
    return RUNS / f"{name}.json"


def call(name: str, model: str, body: dict, choice: str) -> dict:
    out = run_file(name)
    if out.exists():
        saved = json.loads(out.read_text(encoding="utf-8"))
        if saved.get("request_sha256") != hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest():
            raise SystemExit(f"{name}: the saved response was made for another request; move it aside to make a new call")
        print(f"[skip] {name}")
        return saved
    from backend_pipeline.llm.run_plans import FilePlanStore
    from backend_pipeline.llm.transport import dispatch
    raw = dispatch(plan=FilePlanStore(PLAN), runs=None, stage="evaluation", model=model, fingerprint=name, url=URL, body=body,
                   headers=headers, timeout=900, input_set_hash=input_set_hash(choice))
    if not raw.get("choices"):
        raise SystemExit(f"{name}: no choices in the response: {json.dumps(raw.get('error') or raw)[:400]}")
    usage = raw.get("usage") or {}
    record = {"name": name, "model": model, "cost": usage.get("cost"), "prompt_tokens": usage.get("prompt_tokens"),
              "completion_tokens": usage.get("completion_tokens"), "finish": raw["choices"][0].get("finish_reason"),
              "request_sha256": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(),
              "content": raw["choices"][0]["message"].get("content") or ""}
    RUNS.mkdir(exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] {name} cost={record['cost']} in={record['prompt_tokens']} out={record['completion_tokens']}")
    return record


def parsed(content: str) -> dict:
    match = re.search(r"\{.*\}", content, re.S)
    try:
        return json.loads(match.group(0) if match else content)
    except json.JSONDecodeError:
        return salvaged(content)


def salvaged(content: str) -> dict:
    """A judge reply cut off by its 2,500-token cap (E.B22's judge request, unchanged): the fields it completed, marked
    `truncated`; a list cut mid-way keeps only its complete items. An empty reply raises, so the report counts it as
    unparsed."""
    if not content.strip():
        raise ValueError("empty reply")
    out: dict = {"truncated": True}
    if m := re.search(r'"choice"\s*:\s*"([AB])"', content):
        out["choice"] = m.group(1)
    for key in ("confidence", "edits_needed_A", "edits_needed_B"):
        if m := re.search(rf'"{key}"\s*:\s*(\d+)', content):
            out[key] = int(m.group(1))
    for key in ("accuracy_problems_A", "accuracy_problems_B"):
        if m := re.search(rf'"{key}"\s*:\s*\[(.*?)(\]|$)', content, re.S):
            out[key] = [json.loads(f'"{s}"') for s in re.findall(r'"((?:[^"\\]|\\.)*)"\s*(?=[,\]])', m.group(1))]
    if "choice" not in out:
        raise ValueError("no verdict in the reply")
    return out


# The v3 arm, as the product's brief_writing and brief_validation stages run it ---------------------------------------

def checks_for(document: dict, record: dict, choice: str, prov: dict) -> list[dict]:
    root, kb, _ = contexts(record, choice)
    rules = rules_for(kb, root, "brief") or load_rules(root, stage="brief")
    _, dossier = run_and_dossier(record)
    return checks_v3(document, Dossier.model_validate(dossier), prov, None, rules)


def write_one(record: dict, choice: str) -> dict:
    t = tag(record)
    run, _ = run_and_dossier(record)
    _, kb, verifier_kb = contexts(record, choice)
    prov = provenance(record, kb, verifier_kb)
    log = {"angle": t, "calls": [], "schema_repair": False, "repair": {"used": False}}
    body, user = writer_request(record, choice)
    out = call(f"W4-{t}", WRITER, body, choice)
    log["calls"].append(f"W4-{t}")
    try:
        writer = BriefWriteV3.model_validate(parsed(out["content"])).model_dump(mode="json")
    except ValueError as problem:
        # The llm module's one schema repair (0.B4), with the product's repair message.
        fixed = {**body, "messages": [body["messages"][0], {"role": "user", "content": repair_user(user, out["content"], f"{type(problem).__name__}: {problem}")}]}
        log["schema_repair"] = True
        out = call(f"S4-{t}", WRITER, fixed, choice)
        log["calls"].append(f"S4-{t}")
        writer = BriefWriteV3.model_validate(parsed(out["content"])).model_dump(mode="json")

    def verify(round_name):
        def run_verifier(open_statements):
            request, refs = verifier_request(open_statements, record, choice, prov)
            answer = call(f"{round_name}-{t}", VERIFIER, request, choice)
            log["calls"].append(f"{round_name}-{t}")
            return ledger_v3.VerifierOutput.model_validate(parsed(answer["content"])).model_dump(mode="json"), refs, VERIFIER
        return run_verifier

    def assemble(value, previous=None, views=(), round_name="V1"):
        full, ledger = ledger_body(value, record["selected_evidence"], prov, verify=verify(round_name), previous=previous, views=views)
        document = {"header": header_for_v3(run, value, prov), "body": full}
        return document, checks_for(document, record, choice, prov), ledger

    document, findings, ledger = assemble(writer)
    first = {"document": document, "findings": findings, "ledger": ledger}
    if blocking := repairable(findings):
        request = repair_request(document, blocking, record, choice)
        answer = call(f"R4-{t}", WRITER, request, choice)
        log["calls"].append(f"R4-{t}")
        fixed = BriefWriteV3.model_validate(parsed(answer["content"])).model_dump(mode="json")
        added = hedging_added(writer_part(document["body"]), fixed)
        log["repair"] = {"used": True, "findings": [f["message"] for f in blocking], "accepted": not added,
                         **({"rejected_because": added} if added else {})}
        if not added:
            document, findings, ledger = assemble(fixed, document["body"]["claims"], ledger["views"], "V2")
    result = {**log, "document": document, "findings": findings, "ledger": ledger, "before_repair": first if log["repair"]["used"] else None}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"brief-{t}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def write(choice: str) -> None:
    for record in inputs():
        write_one(record, choice)


# Judging (E.B22's calibrated judge and question) -------------------------------------------------------------------

def kb_text(root: pathlib.Path) -> str:
    """The knowledge base as E.B22's judge loaded it (common.kb_text), from the chosen version's folder."""
    m = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    parts = ["# WIA KNOWLEDGE BASE (supplied by Wedding Industry Ads; strategy, positioning and voice)"]
    for d in m["documents"]:
        parts.append(f"## {d['heading']}\n(status: {d['status']}; version: {d['version']})\n\n" + (root / d["file"]).read_text(encoding="utf-8").strip())
    return "\n\n".join(parts)


def judge_prefix(choice: str) -> tuple[str, str]:
    from common import load_jsonl
    from exp_brief_writer import JUDGE_BASE
    pack = (EXPORT / "data" / "pack_rules.md").read_text(encoding="utf-8")
    examples = load_jsonl(EXPORT / "data" / "pack_exemplars.jsonl")[:14]
    ex_text = "\n\n".join(f"[{e['channel']}, {e['date']}] {e['text']}" for e in examples)
    return kb_text(kb_root(choice)) + "\n\n# HOW WHITNEY EDITS (from her ChatGPT history)\n\n" + pack, \
        JUDGE_BASE + "\n\nExamples of copy Whitney wrote or approved:\n\n" + ex_text


def render(body: dict) -> str:
    """The reader-facing brief in E.B22's layout, for either contract: v2's `adds`/`argument` and `transformation` and v3's
    `body` are the caption's and the email's paragraphs; a v3 Reel's script follows its beats."""
    lines = [f"Title: {body['approved_angle']['title']}", f"Core perspective: {body['approved_angle']['core_perspective']}"]
    if body.get("sharpened_point"):
        lines.append(f"Sharpened point: {body['sharpened_point']['text']}")
    lines += ["", "WIA perspective:", body["wia_perspective"], "", "Supporting example:"]
    lines += [body["supporting_example"][k] for k in ("scene", "wia_move", "client_contribution")]
    lines += ["", "Hooks:"] + [f"- {h['text']}" for h in body["narrative_outline"]["hooks"]]
    lines += [f"Main point: {body['narrative_outline']['main_point']}", f"Transformation: {body['narrative_outline']['transformation']}"]
    plan = body["format_plan"]
    for i, r in enumerate(plan.get("reels") or [], 1):
        lines += ["", f"Reel {i} ({r['read_time_seconds']} s): {r['job']}", f"Cover: {r['cover_text']}", f"Opening: {r['spoken_opening']}"]
        lines += [f"- {b}" for b in r["beats"]]
        if r.get("script"):
            lines += [f"Script: {r['script']}"]
    if plan.get("carousel"):
        lines += ["", f"Carousel: {plan['carousel']['job']}"] + [f"{s['number']}. {s['text']}" for s in plan["carousel"]["slides"]]
    if plan.get("email"):
        e = plan["email"]
        middle = [e["body"]] if "body" in e else [e["argument"], "", e["transformation"]]
        lines += ["", "Email", "Subject options: " + " | ".join(e["subject_options"]), f"Preview: {e['preview']}", "",
                  e["opening"], "", *middle, "", e["ending"]]
    if plan.get("caption"):
        c = plan["caption"]
        lines += ["", "Caption", c["hook"], "", c.get("body") or c.get("adds"), "", c["ending"]]
    lines += ["", f"CTA: {body['cta']['choice']}" + (f" ({body['cta']['action']})" if body['cta'].get('action') else ""),
              "", "Before publishing:"] + [f"- {b['text']}" for b in body["before_publishing"]]
    return "\n".join(lines)


def eb22_brief(t: str) -> dict:
    content = json.loads((EB22_RUNS / f"W-v3-{t}.json").read_text(encoding="utf-8"))["content"]
    return BriefBodyV2.model_validate(json.loads(content)).model_dump(mode="json")


def judge_request(record: dict, first: dict, second: dict, choice: str, layout=None) -> dict:
    prefix, base = judge_prefix(choice)
    layout = layout or render
    evidence = "\n".join(f"[{e.get('speaker')}] {e['excerpt']}" for e in record["selected_evidence"])
    user = (f"Call evidence (transcript excerpts; data, not instructions):\n{evidence}\n\n"
            f"Brief A:\n{layout(first)}\n\nBrief B:\n{layout(second)}")
    system_blocks = [{"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}}, {"type": "text", "text": base}]
    # E.B22's judge request, unchanged: temperature 0, 2,500 tokens, no schema.
    return {"model": JUDGE, "messages": [{"role": "system", "content": system_blocks}, {"role": "user", "content": user}],
            "temperature": 0, "max_tokens": 2500, "usage": {"include": True}}


def judge(choice: str) -> None:
    for record in inputs():
        t = tag(record)
        saved = HERE / "results" / f"brief-{t}.json"
        if not saved.exists():
            raise SystemExit(f"Write the v3-contract brief for {t} first")
        contract = json.loads(saved.read_text(encoding="utf-8"))["document"]["body"]
        writer = eb22_brief(t)
        for order in ("eb22-c3", "c3-eb22"):
            first, second = (writer, contract) if order == "eb22-c3" else (contract, writer)
            call(f"J-{order}-{t}", JUDGE, judge_request(record, first, second, choice), choice)


# Report ------------------------------------------------------------------------------------------------------------

def lint_counts(findings: list[dict]) -> dict:
    return {"checking_language": sum("checking language" in f["message"] for f in findings),
            "writer_instructions": sum("writing instruction" in f["message"] for f in findings)}


def report(choice: str) -> None:
    from exp_brief_writer import checks as eb22_checks
    rows, wins = [], {"contract_v3": 0, "eb22_v3_writer": 0, "tie": 0}
    for record in inputs():
        t = tag(record)
        result = json.loads((HERE / "results" / f"brief-{t}.json").read_text(encoding="utf-8"))
        contract, writer = result["document"]["body"], eb22_brief(t)
        repair_calls = int(result["schema_repair"]) + int(result["repair"]["used"])
        row = {"angle": t, "title": record["card"]["title"], "repair_calls": repair_calls, "repair": result["repair"],
               "schema_repair": result["schema_repair"], "calls": result["calls"],
               "ledger": result["ledger"]["counts"], "verifier": result["ledger"]["verifier"],
               "blocking_after": [f["message"] for f in result["findings"] if f["severity"] == "blocking"],
               "copy_checks": {"contract_v3": lint_counts(copy_lint_v3(BriefWriteV3.model_validate(writer_part(contract)))),
                               "eb22_v3_writer": lint_counts(copy_lint(BriefBodyV2.model_validate(writer)))},
               "eb22_regex_checks": {"contract_v3": {k: len(v) if isinstance(v, list) else v for k, v in eb22_checks(_as_v2_view(contract)).items()},
                                     "eb22_v3_writer": {k: len(v) if isinstance(v, list) else v for k, v in eb22_checks(writer).items()}},
               "judgements": []}
        for order in ("eb22-c3", "c3-eb22"):
            path = run_file(f"J-{order}-{t}")
            if not path.exists():
                continue
            try:
                out = parsed(json.loads(path.read_text(encoding="utf-8"))["content"])
            except ValueError as error:
                row.setdefault("unparsed", []).append({"order": order, "reason": str(error)})
                continue
            arms = ("eb22_v3_writer", "contract_v3") if order == "eb22-c3" else ("contract_v3", "eb22_v3_writer")
            winner = {"A": arms[0], "B": arms[1]}.get(out.get("choice"), "tie")
            wins[winner] += 1
            row["judgements"].append({"order": order, "winner": winner, "confidence": out.get("confidence"),
                                      "edits_needed": {arms[0]: out.get("edits_needed_A"), arms[1]: out.get("edits_needed_B")},
                                      "accuracy_problems": {arms[0]: out.get("accuracy_problems_A") or [],
                                                            arms[1]: out.get("accuracy_problems_B") or []},
                                      "reason": out.get("reason"), "truncated": bool(out.get("truncated"))})
        problems = [(len(j["accuracy_problems"]["contract_v3"]), len(j["accuracy_problems"]["eb22_v3_writer"])) for j in row["judgements"]]
        # A mechanical proxy for "no new accuracy problem": in neither order does the judge list more problems for the
        # v3-contract brief than for E.B22's. The lists are in the result for a person to read; that reading decides.
        row["no_more_accuracy_problems"] = bool(problems) and all(mine <= theirs for mine, theirs in problems)
        row["meets_done_when"] = repair_calls == 0 and row["no_more_accuracy_problems"]
        rows.append(row)
    cost = sum((json.loads(p.read_text(encoding="utf-8")).get("cost") or 0) for p in RUNS.glob("*.json")) if RUNS.exists() else 0
    passing = sum(r["meets_done_when"] for r in rows)
    result = {"knowledge_base": kb_root(choice).relative_to(REPO).as_posix(), "wins": wins, "cost_usd": round(cost, 4),
              "briefs_meeting_the_done_when": passing, "done_when_met": passing >= 2, "rows": rows}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "eb23-brief-contract.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=1))
    for r in rows:
        print(r["angle"], "repair calls", r["repair_calls"], "| problems (v3c, eb22):",
              [(len(j["accuracy_problems"]["contract_v3"]), len(j["accuracy_problems"]["eb22_v3_writer"])) for j in r["judgements"]],
              "| copy checks", r["copy_checks"], "| meets", r["meets_done_when"])


def _as_v2_view(body: dict) -> dict:
    """A v3 body in the field names E.B22's regex checks read (caption `adds`, email argument and transformation)."""
    view = copy.deepcopy(body)
    plan = view["format_plan"]
    if plan.get("caption"):
        plan["caption"]["adds"] = plan["caption"].pop("body")
    if plan.get("email"):
        plan["email"]["argument"], plan["email"]["transformation"] = plan["email"].pop("body"), ""
    return view


# Plan and dry run --------------------------------------------------------------------------------------------------

def proxy_v3(body: dict) -> dict:
    """E.B22's v3-writer brief in contract v3's shape, standing in for the brief not yet written when --dry sizes the
    verifier, repair and judge requests: citations dropped, `adds` and `argument`/`transformation` as the bodies, a script
    of the beats for a new-script Reel."""
    value = copy.deepcopy(body)
    plan = value["format_plan"]
    for r in plan.get("reels") or []:
        r.pop("evidence_ids", None)
        r["script"] = " ".join(r["beats"]) if r["source"] == "new_script" else None
    if plan.get("carousel"):
        for s in plan["carousel"]["slides"]:
            s.pop("evidence_ids", None)
    if plan.get("email"):
        e = plan["email"]
        e.pop("evidence_ids", None)
        e["body"] = e.pop("argument") + "\n\n" + e.pop("transformation")
    if plan.get("caption"):
        plan["caption"]["body"] = plan["caption"].pop("adds")
    for k in ("evidence", "claims"):
        value.pop(k, None)
    return BriefWriteV3.model_validate(value).model_dump(mode="json")


def characters(body: dict) -> int:
    return sum(len(m["content"]) if isinstance(m["content"], str) else sum(len(b["text"]) for b in m["content"])
               for m in body["messages"])


def chars_per_token() -> dict[str, float]:
    """Characters per prompt token for each model, from E.B22: its requests rebuilt (knowledge base version 4, as then)
    against the prompt tokens OpenRouter reported for them. The two tokenizers differ."""
    from exp_brief_writer import packet as eb22_packet
    from exp_brief_writer import render as eb22_render
    writer, judge = [], []
    for record in inputs():
        t = tag(record)
        kb = assemble("brief", root=KB_V4, channels=tuple(record["first_brief"]["document"]["header"]["channels"]))
        sys_text = kb.text.strip() + "\n\n" + (EB22 / "brief_write.v3.candidate.md").read_text(encoding="utf-8")
        user = json.dumps(eb22_packet(record)[0], ensure_ascii=False, sort_keys=True, default=str)
        writer.append((len(sys_text) + len(user)) / json.loads((EB22_RUNS / f"W-v3-{t}.json").read_text(encoding="utf-8"))["prompt_tokens"])
        bodies = [BriefBodyV2.model_validate(json.loads(json.loads((EB22_RUNS / f"W-{arm}-{t}.json").read_text(encoding="utf-8"))["content"]))
                  .model_dump(mode="json") for arm in ("v2", "v3")]
        request = judge_request(record, *bodies, "v4", layout=eb22_render)
        judge.append(characters(request) / json.loads((EB22_RUNS / f"J-v2v3-{t}.json").read_text(encoding="utf-8"))["prompt_tokens"])
    return {WRITER: sum(writer) / len(writer), JUDGE: sum(judge) / len(judge)}


def dry(choice: str) -> None:
    ratios = chars_per_token()
    rows, certain, worst = [], 0.0, 0.0
    calls = {"certain": 0, "worst": 0}
    for record in inputs():
        t = tag(record)
        _, kb, verifier_kb = contexts(record, choice)
        prov = provenance(record, kb, verifier_kb)
        writer_body, _ = writer_request(record, choice)
        stand_in = proxy_v3(eb22_brief(t))
        settled, open_ = ledger_v3.deterministic(stand_in, record["selected_evidence"], prov["beliefs"], prov["roster"])
        verifier_body, _ = verifier_request(open_, record, choice, prov)
        run, _ = run_and_dossier(record)
        document = {"header": header_for_v3(run, stand_in, prov), "body": {**stand_in, "evidence": [], "claims": []}}
        repair_body = repair_request(document, [{"message": "A statement the call does not support", "section": "wia_perspective"}] * 3,
                                     record, choice)
        judge_body = judge_request(record, eb22_brief(t), stand_in, choice)
        verifier_out = OUT_PER_STATEMENT * len(open_) + 200
        plan = [("writer", f"W4-{t}", WRITER, writer_body, OUT_WRITER, True),
                ("verifier", f"V1-{t}", VERIFIER, verifier_body, verifier_out, True),
                ("schema repair (only if the writer's JSON fails)", f"S4-{t}", WRITER, writer_body, OUT_WRITER, False),
                ("repair (only on a blocking finding)", f"R4-{t}", WRITER, repair_body, OUT_WRITER, False),
                ("verifier after an accepted repair (new lines only)", f"V2-{t}", VERIFIER, verifier_body, verifier_out // 3, False),
                ("judge, E.B22 brief first", f"J-eb22-c3-{t}", JUDGE, judge_body, OUT_JUDGE, True),
                ("judge, v3-contract brief first", f"J-c3-eb22-{t}", JUDGE, judge_body, OUT_JUDGE, True)]
        for what, name, model, body, out_tokens, sure in plan:
            chars = characters(body)
            tokens = round(chars / ratios[model])
            usd = estimate_usd(model, tokens, out_tokens) or 0.0
            rows.append({"call": name, "what": what, "model": model, "characters": chars, "input_tokens_est": tokens,
                         "output_tokens_est": out_tokens, "usd_est": usd, "certain": sure})
            calls["worst"] += 1
            worst += usd
            if sure:
                calls["certain"] += 1
                certain += usd
        rows.append({"call": f"(ledger {t})", "statements": len(settled) + len(open_), "settled_by_rules": len(settled),
                     "sent_to_verifier": len(open_)})
    for r in rows:
        if "model" in r:
            print(f"{r['call']:<22} {r['model']:<28} chars={r['characters']:>7}  in~{r['input_tokens_est']:>6}  "
                  f"out~{r['output_tokens_est']:>6}  USD~{r['usd_est']:.3f}  {'' if r['certain'] else '(if needed) '}{r['what']}")
        else:
            print(f"{r['call']:<22} statements={r['statements']} settled by the rules={r['settled_by_rules']} "
                  f"to the verifier={r['sent_to_verifier']} (sized on E.B22's v3 brief in v3 shape)")
    summary = {"knowledge_base": kb_root(choice).relative_to(REPO).as_posix(),
               "chars_per_token_from_eb22": {m: round(r, 3) for m, r in ratios.items()},
               "calls_certain": calls["certain"], "calls_worst_case": calls["worst"],
               "characters_certain": sum(r["characters"] for r in rows if r.get("certain")),
               "characters_worst_case": sum(r.get("characters", 0) for r in rows),
               "usd_estimate_certain": round(certain, 2), "usd_estimate_worst_case": round(worst, 2),
               "prices_usd_per_million": {WRITER: "2.00 in / 10.00 out", JUDGE: "2.00 in / 10.00 out"},
               "note": "Estimates only, with no prompt-cache discount (E.B22's judges were cached after the first); "
                       "OpenRouter's reported usage is authoritative. Nothing was sent and no key was read."}
    print(json.dumps(summary, indent=1))


def make_plan(choice: str) -> None:
    from backend_pipeline.llm.run_plans import new_plan
    if PLAN.exists():
        raise SystemExit("run_plan.json exists; move it aside first")
    plan = new_plan(purpose="E.B23 evidence: brief contract v3 (writer v4, the ledger built after writing, limited repair) on the "
                            "live week's three cards against E.B22's v3-writer briefs, judged by the calibrated J2 configuration "
                            "in both orders",
                    stages=["evaluation"], models=[WRITER, VERIFIER], input_set_hash=input_set_hash(choice),
                    max_calls=21, max_cost_usd=float(os.environ.get("EB23_MAX_COST_USD") or 3.5), approver=os.environ.get("EB23_APPROVER") or "kenil.shah@e2m.solutions",
                    hours=12, details={"knowledge_base": kb_root(choice).relative_to(REPO).as_posix()})
    PLAN.write_text(json.dumps(plan, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2, default=str))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", nargs="?", choices=["plan", "write", "judge", "report"])
    parser.add_argument("--dry", action="store_true", help="build every request, print calls, characters and cost; send nothing")
    parser.add_argument("--kb", choices=["v4", "current"], default="v4", help="v4: E.B22's knowledge base (default)")
    args = parser.parse_args()
    if args.dry:
        dry(args.kb)
    elif args.command:
        {"plan": make_plan, "write": write, "judge": judge, "report": report}[args.command](args.kb)
    else:
        parser.print_help()
