"""E.B3's calibrated pairwise judge: a smoke test, never the gate (plan E.B3, K45, R44).

- **Rubric:** review rubric 2.3a, imported from backend_pipeline.gates.rubric (VERSION, CRITERIA, ANCHORS, TEXT), never a
  copy and never a candidate prompt's wording; `independence()` checks the judge's own instructions share no eight-word
  run with any prompt template. Every comparison records the rubric's version and text hash.
- **Model:** a family other than the generator's (refused otherwise). The default is Claude Sonnet 5.5, the only judge
  that passed the export-pair test on 18 October (31 of 38 pairs right in both orders, with the knowledge base and the
  export pack); the writers it judges are OpenAI models and ChatGPT.
- **Order:** which candidate is shown as A is drawn per comparison from a recorded seed. With both orders (the default for
  calibration) each pair is judged reversed as well; a pair whose choice follows the position is an order flip, and
  their share is the position-bias measure.
- **Shape:** both candidates are rendered in one plain format with the same fields, so the judge cannot tell
  configurations apart by shape. A label's notes (why Whitney preferred one) are never sent.
- **Context:** the knowledge base and, by default, the export pack (`data/pack_rules.md`, `data/pack_exemplars.jsonl`),
  with every paragraph or exemplar that shares an eight-word run with any candidate in the run removed, so no
  candidate's text reaches the judge as reference (leave-one-out, as on 18 October). One context serves the whole run, so
  its prefix is cached.
- **Calls:** through the llm module's dispatch with the privacy routing, reserved and settled against a run plan (E.B1;
  `ATELIER_RUN_PLAN_FILE`, or research/benchmark-v1/run_plan_judge.json); a call names the run's input-set hash. Each
  response is saved under research/benchmark-v1/judge/runs/ with its request fingerprint and reused only for the
  identical request; `replay` reads saved responses only, `dry` counts calls and estimates cost, and neither sends
  anything.

Calibration (`python -m evaluation judge-calibrate`) forms pairs from the labels (`pairs_from_labels`) and reports
agreement with them (share, with a 95% Wilson interval), agreement with dispositions, rank correlation where a week has a
ranking, the distance from the reviewer's own rubric ratings where she gave them (E.X3), and position bias. A judge
configuration may pre-screen only if it agrees with Whitney on at least 80% of the 38 export pairs in both orders, and
then on her live Week 5 dispositions (plan E.B3). Delegated labels never calibrate it (R55).

Comparison (`python -m evaluation judge-compare`) is the evaluation command's pairwise judge: two configurations' saved
samples, each week's sample s of one against sample s of the other as slates in one plain format, both orders, reporting
the share of judgements preferring each, the pairs won in both orders, the mean rubric scores and the order flips.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import sqrt
from pathlib import Path

from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.costs import price_of
from backend_pipeline.cycle.verification import family
from backend_pipeline.gates import rubric
from backend_pipeline.llm.request import chat_body
from backend_pipeline.llm.run_plans import from_environment
from backend_pipeline.llm.transport import dispatch
from backend_pipeline.store import canonical_hash

from .benchmark import PROJECT, RESEARCH, VERSION, build_labels, guard

OUT = RESEARCH / "benchmark-v1"
RUNS = OUT / "judge" / "runs"
PLAN_FILE = OUT / "run_plan_judge.json"
PACK = RESEARCH / "chatgpt-export-2026-10-18" / "data"
URL = "https://openrouter.ai/api/v1/chat/completions"
STAGE = "evaluation_judge"
PROMPT_VERSION = "judge-2.3a.2026-10-19.v1"
JUDGE_MODEL = "anthropic/claude-sonnet-5.5"
# The writers whose output the labelled pairs hold: ChatGPT or a team member's draft against Whitney's version, the
# Week 1 originals (GPT-6 Luna), and the strategist's cards (Sol, R44) unless a card records its model.
GENERATORS = {"export_pairs": "openai/chatgpt", "week1_reframes": "openai/gpt-6-luna", "dispositions": "openai/gpt-6.1-sol"}
GROUPS = tuple(GENERATORS)
CONTEXTS = ("none", "kb", "kb+pack")
DEFAULT_CONTEXT = "kb+pack"
DEFAULT_SEED = 20261019
MAX_TOKENS = 1500
OUTPUT_TOKENS_ESTIMATE = 600
PRESCREEN_BAR = 0.8
EXPORT_PAIRS = 38
SHINGLE = 8
# Anthropic prompt caching through OpenRouter: a cache write costs 1.25 times the input price, a read 0.1 times.
CACHE_WRITE, CACHE_READ = 1.25, 0.1
ACCEPTED_TIER, CLOSED = 4, ("skip", "internal")
SIDES = ("A", "B")

INSTRUCTIONS = """You are an independent reviewer for Wedding Industry Ads (WIA), a paid-ads agency that runs Google and \
Meta campaigns for wedding businesses; its founder is Whitney Hodges. You are shown two candidates, A and B, for the same \
piece of WIA content. Score each one on every criterion of the review rubric below, then name the one Whitney would \
rather publish.

- Score A and B separately, each on its own merits; use the whole scale.
- Look only at what each candidate says. The letters, the order in which they appear and their length tell you nothing.
- The reference material after the rubric is WIA's own. Use it to understand WIA's strategy, market and voice; it is not \
a candidate.
- Reply with JSON only: for A and for B a whole-number score for each criterion key, the preferred letter, and one \
sentence on why."""


@dataclass(frozen=True)
class Candidate:
    """One side of a comparison: its fields in display order, its tier in the label's ordering, and who wrote it."""
    id: str
    fields: tuple[tuple[str, str], ...]
    tier: int | None = None
    generator: str | None = None


@dataclass(frozen=True)
class Pair:
    """Two candidates for the same piece and evidence; `preferred` is the candidate the label prefers (None when no label
    decides, as between two configurations' slates)."""
    pair_id: str
    group: str
    kind: str
    x: Candidate
    y: Candidate
    preferred: str | None
    week: str | None = None
    label_ids: tuple[str, ...] = ()
    evidence: str | None = None
    details: dict = field(default_factory=dict, compare=False, hash=False)


# Rendering: one plain format for every candidate.
CARD_FIELDS = (("title", "Title"), ("pillar", "Pillar"), ("content_type", "Content type"), ("audience", "Audience"),
               ("core_perspective", "Core perspective"), ("why_it_matters", "Why it matters"),
               ("wia_in_action", "WIA in action"), ("offer_connection", "Offer connection"), ("evidence_points", "Evidence"))


def _text(value) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {_text(v)}" for v in value if v)
    if isinstance(value, dict):
        return "; ".join(f"{k}: {v}" for k, v in value.items() if v)
    return str(value or "").strip()


def card_fields(card: dict) -> tuple[tuple[str, str], ...]:
    return tuple((label, _text(card.get(key))) for key, label in CARD_FIELDS if _text(card.get(key)))


def card_candidate(candidate_id: str, card: dict, *, tier=None, generator=None) -> Candidate:
    return Candidate(candidate_id, card_fields(card), tier, generator)


# A moment reference before an evidence line ("[w1_m1] Carmen asked..."): one profile writes them and another does not.
REFERENCE = re.compile(r"^\s*\[[^\]\n]{1,40}\]\s*")


def slate_candidate(candidate_id: str, cards: list[dict], *, generator=None) -> Candidate:
    """A week's slate as one candidate: each card in the same plain format, numbered in its rank order, its evidence
    without moment references, so the judge cannot tell the profile that wrote it by shape."""
    blocks = []
    for i, card in enumerate(cards, 1):
        card = {**card, "evidence_points": [REFERENCE.sub("", _text(e)) for e in card.get("evidence_points") or []]}
        blocks.append(f"Card {i}\n" + "\n".join(f"{label}: {text}" for label, text in card_fields(card)))
    return Candidate(candidate_id, (("Cards", "\n\n".join(blocks)),), None, generator)


def shared_labels(a: Candidate, b: Candidate) -> list[str]:
    """The fields both candidates have, in A's order: neither side shows a field the other lacks."""
    other = {label for label, _ in b.fields}
    return [label for label, _ in a.fields if label in other]


def render(candidate: Candidate, labels: list[str]) -> str:
    values = dict(candidate.fields)
    return "\n\n".join(f"{label}:\n{values[label]}" for label in labels)


def candidate_text(candidate: Candidate) -> str:
    return "\n".join(text for _, text in candidate.fields)


# Context: the knowledge base and the export pack, without any candidate's text.
def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower().replace("’", "'"))


def shingles(text: str, n: int = SHINGLE) -> set[str]:
    words = _words(text)
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def _blocks(text: str) -> list[str]:
    return [b for b in re.split(r"\n\s*\n", text) if b.strip()]


LONG_PARAGRAPH = 1500


def _without(blocks: list[str], taken: set[str]) -> tuple[list[str], int]:
    """The paragraphs that share no run with `taken`, and how many units were removed. A long paragraph (a document
    written without blank lines, such as the voice guide or the belief bank) is redacted line by line, so one quoted
    line does not take the whole document with it."""
    kept, removed = [], 0
    for block in blocks:
        if not shingles(block) & taken:
            kept.append(block)
        elif len(block) > LONG_PARAGRAPH:
            lines = block.splitlines()
            left = [line for line in lines if not shingles(line) & taken]
            removed += len(lines) - len(left)
            kept.append("\n".join(left))
        else:
            removed += 1
    return kept, removed


def knowledge():
    """The strategist's knowledge base from the assembly service, for the version the evaluation command is set to."""
    from . import run
    return run.knowledge("strategist")


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in guard(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def judge_context(name: str, texts: list[str], *, kb=None) -> tuple[str, dict]:
    """The reference text after the rubric, and what it is made of. Paragraphs and exemplars sharing an eight-word run
    with any of `texts` are removed, and the record says how many and checks none remains."""
    if name not in CONTEXTS:
        raise ValueError(f"Unknown judge context {name!r}; use one of: {', '.join(CONTEXTS)}")
    if name == "none":
        return "", {"name": name, "sha256": hashlib.sha256(b"").hexdigest(), "characters": 0}
    taken = set().union(*(shingles(t) for t in texts)) if texts else set()
    kb = kb if kb is not None else knowledge()
    kb_kept, kb_removed = _without(_blocks(kb.text), taken)
    parts = ["# WIA reference: the knowledge base\n\n" + "\n\n".join(kb_kept)]
    record = {"name": name, "knowledge_base": {"version": kb.version, "sha256": getattr(kb, "sha256", None)},
              "knowledge_base_units_removed": kb_removed}
    if name == "kb+pack":
        rules_kept, rules_removed = _without(_blocks(guard(PACK / "pack_rules.md").read_text(encoding="utf-8")), taken)
        exemplars = _load_jsonl(PACK / "pack_exemplars.jsonl")
        kept = [e for e in exemplars if not shingles(e["text"]) & taken]
        parts.append("# WIA reference: how Whitney edits (from her ChatGPT history)\n\n" + "\n\n".join(rules_kept))
        parts.append("# WIA reference: copy Whitney wrote or approved\n\n"
                     + "\n\n".join(f"[{e['channel']}, {e['date']}]\n{e['text']}" for e in kept))
        record.update(pack_rules_units_removed=rules_removed, pack_exemplars_used=len(kept),
                      pack_exemplars_removed=len(exemplars) - len(kept))
    text = "\n\n".join(parts)
    record.update(sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(), characters=len(text),
                  candidate_runs_left=len(shingles(text) & taken))
    return text, record


def independence() -> dict:
    """K45: the judge's instructions share no eight-word run with any candidate prompt (the prompt templates and the
    prompt builders)."""
    sources = [p for p in (BACKEND_ROOT / "backend_pipeline" / "prompt_templates").rglob("*") if p.is_file()]
    sources += [BACKEND_ROOT / "backend_pipeline" / name for name in ("prompts.py", "angle_profiles.py")]
    mine = shingles(INSTRUCTIONS)
    shared = sorted({s for p in sources for s in shingles(p.read_text(encoding="utf-8", errors="replace")) & mine})
    return {"checked_files": len(sources), "shared_runs": shared}


# The request.
def system_prompt(context_text: str) -> str:
    keys = "; ".join(f"{i} = {c.key}" for i, c in enumerate(rubric.CRITERIA, 1))
    parts = [INSTRUCTIONS, rubric.TEXT, f"Criterion keys for your scores: {keys}."]
    return "\n\n".join(parts + ([context_text] if context_text else []))


def user_message(kind: str, evidence: str | None, a: str, b: str) -> str:
    parts = [f"Content: {kind}"]
    if evidence:
        parts.append(f"Evidence both candidates draw on:\n{evidence}")
    return "\n\n".join(parts + [f"Candidate A\n\n{a}", f"Candidate B\n\n{b}"])


def response_schema() -> dict:
    side = {"type": "object", "additionalProperties": False, "required": list(rubric.KEYS),
            "properties": {key: {"type": "integer", "enum": list(rubric.SCALE)} for key in rubric.KEYS}}
    return {"type": "object", "additionalProperties": False, "required": ["A", "B", "preferred", "reason"],
            "properties": {"A": side, "B": side, "preferred": {"type": "string", "enum": list(SIDES)},
                           "reason": {"type": "string"}}}


def shown(pair: Pair, order: int) -> tuple[Candidate, Candidate]:
    """Order 0 shows x as A; order 1 shows y as A."""
    return (pair.x, pair.y) if order == 0 else (pair.y, pair.x)


def request(pair: Pair, order: int, context_text: str, model: str = JUDGE_MODEL) -> dict:
    a, b = shown(pair, order)
    labels = shared_labels(a, b)
    if not labels:
        raise ValueError(f"Pair {pair.pair_id}: the candidates share no field to compare")
    return chat_body(model=model, system=system_prompt(context_text), user=user_message(pair.kind, pair.evidence,
                     render(a, labels), render(b, labels)), schema=response_schema(), max_tokens=MAX_TOKENS)


def fingerprint(body: dict) -> str:
    return canonical_hash({"judge": PROMPT_VERSION, "body": body})


def first_order(seed: int, pair_id: str) -> int:
    """The order a pair is shown in first, drawn from the recorded seed: the same seed gives the same orders."""
    return 1 if random.Random(f"{seed}:{pair_id}").random() < 0.5 else 0


def check_family(model: str, pairs: list[Pair]) -> None:
    for pair in pairs:
        for candidate in (pair.x, pair.y):
            if candidate.generator and "/" in candidate.generator and family(candidate.generator) == family(model):
                raise ValueError(f"The judge {model} is from the same family as {candidate.generator}, which wrote "
                                 f"{candidate.id}; use a judge from another family (E.B3, K45)")


def parse(raw: dict) -> dict | None:
    """The judge's scores, or None when the answer is not a complete, valid verdict."""
    try:
        output = json.loads(raw["choices"][0]["message"].get("content") or "")
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    if not isinstance(output, dict) or output.get("preferred") not in SIDES:
        return None
    try:
        ratings = {side: rubric.ratings(output.get(side), rubric.VERSION) for side in SIDES}
    except (ValueError, TypeError):
        return None
    if not all(ratings.values()):
        return None
    return {"ratings": {s: r["criteria"] for s, r in ratings.items()}, "overall": {s: r["overall"] for s, r in ratings.items()},
            "preferred_side": output["preferred"], "reason": str(output.get("reason") or "")}


def _saved(path: Path, fp: str) -> dict | None:
    if not path.is_file():
        return None
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved.get("request_fingerprint") != fp:
        raise SystemExit(f"{path.name} was saved for another request; move it aside before re-running")
    return saved


def compare(pair: Pair, order: int, *, context_text: str, context_sha256: str, model: str = JUDGE_MODEL, seed: int,
            mode: str = "paid", plan=None, input_set_hash: str | None = None) -> dict:
    """One comparison in one order. mode: paid (a planned call unless saved), replay (saved only) or dry (no call)."""
    body = request(pair, order, context_text, model)
    fp = fingerprint(body)
    a, b = shown(pair, order)
    record = {"pair_id": pair.pair_id, "group": pair.group, "order": order, "first": order == first_order(seed, pair.pair_id),
              "A": a.id, "B": b.id, "label_preferred": pair.preferred, "seed": seed, "judge_model": model,
              "rubric_version": rubric.VERSION, "rubric_text_sha256": rubric.TEXT_SHA256, "prompt_version": PROMPT_VERSION,
              "context_sha256": context_sha256, "request_fingerprint": fp}
    path = RUNS / f"{pair.pair_id}-o{order}-{fp[:16]}.json"
    saved = _saved(path, fp)
    if saved is None and mode in ("dry", "replay"):
        system, user = body["messages"][0]["content"], body["messages"][1]["content"]
        return {**record, "status": "to_call" if mode == "dry" else "missing",
                "system_characters": len(system), "user_characters": len(user), "system_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest()}
    if saved is None:
        from .run import _key
        raw = dispatch(plan=plan, runs=None, stage=STAGE, model=model, fingerprint=fp, url=URL, body=body, timeout=300,
                       input_set_hash=input_set_hash,
                       headers=lambda: {"Authorization": "Bearer " + _key(), "Content-Type": "application/json",
                                        "X-Title": "Content Atelier judge calibration"},
                       context={"prompt_version": PROMPT_VERSION, "rubric_version": rubric.VERSION})
        saved = {"request_fingerprint": fp, "pair_id": pair.pair_id, "order": order, "model": model,
                 "saved_at": datetime.now(UTC).isoformat(), "response": raw}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
        reused = False
    else:
        reused = True
    raw = saved["response"]
    verdict = parse(raw)
    cost = float(((raw.get("usage") or {}).get("cost") or 0)) if isinstance(raw, dict) else 0.0
    if verdict is None:
        return {**record, "status": "unparsed", "reused": reused, "cost": 0.0 if reused else cost}
    preferred = a.id if verdict["preferred_side"] == "A" else b.id
    agrees = None if pair.preferred is None else preferred == pair.preferred
    return {**record, **verdict, "status": "judged", "preferred": preferred, "agrees": agrees,
            "reused": reused, "cost": 0.0 if reused else cost}


# Labelled pairs.
def _usable(label: dict) -> bool:
    """WIA's own labels, and the export pairs the plan names as the first calibration set; never a delegated decision
    (R55) or another proxy."""
    if label["source"] == "gate_delegated" or (label.get("details") or {}).get("delegated"):
        return False
    return not label["proxy"] or label["source"] == "chatgpt_export"


def _tier(label: dict) -> int:
    if label["disposition"] == "develop" or label["disposition"] == "reframe" and label.get("central_point_kept"):
        return ACCEPTED_TIER
    return {"reframe": 3, "hold": 2}.get(label["disposition"], 1)


def _her_ratings(label: dict) -> dict | None:
    """The reviewer's per-criterion ratings on the label (E.X3), when given on the rubric version in force."""
    rated = label.get("rubric_ratings") or {}
    return rated.get("criteria") if rated.get("version") == rubric.VERSION and rated.get("criteria") else None


def pairs_from_labels(labels: list[dict], cards: dict[str, dict] | None = None) -> tuple[list[Pair], dict]:
    """The calibration pairs the labels allow, and what was left out and why.

    - export_pairs: each of the 38 export pairs, the draft against the version Whitney wrote or approved; hers is preferred.
    - week1_reframes: each Week 1 original against Whitney's own alternative; hers is preferred. The originals survive
      as titles only, so these pairs compare titles.
    - dispositions: within a week, every accepted card (developed, or reframed with the central point kept) against
      every card skipped or marked internal, on the latest label per card (`cards` maps angle IDs to {"week_id",
      "content_body"}; Gate 1 labels only); the reviewer's rubric ratings, where given, travel in the pair's details
      and are never sent."""
    pairs, excluded = [], {}
    latest = {}
    for label in labels:
        if not _usable(label):
            excluded[label["source"]] = excluded.get(label["source"], 0) + 1
            continue
        if label["item_kind"] == "export_pair":
            d = label["details"]
            draft = Candidate(f"{label['item_id']}.draft", (("Text", d["ai_text"]),), 1, GENERATORS["export_pairs"])
            hers = Candidate(f"{label['item_id']}.whitney", (("Text", d["her_text"]),), 2, "person")
            pairs.append(Pair(label["item_id"], "export_pairs", d["channel"], draft, hers, hers.id, None, (label["label_id"],),
                              details={"date": d.get("date")}))
        elif label["item_kind"] == "benchmark_angle" and label.get("reframe"):
            r, d = label["reframe"], label["details"]
            original = Candidate(f"{label['item_id']}.original", (("Title", d["title"]),), 1, GENERATORS["week1_reframes"])
            hers = Candidate(f"{label['item_id']}.whitney", tuple((name, _text(r.get(key))) for key, name in (
                ("title", "Title"), ("pillar_type", "Pillar and type"), ("audience", "Audience"),
                ("why_it_matters", "Why it matters"), ("wia_expertise", "WIA's expertise")) if _text(r.get(key))), 2, "person")
            pairs.append(Pair(f"w1-{label['item_id']}", "week1_reframes", "content card", original, hers, hers.id,
                              label["week_id"], (label["label_id"],)))
        elif label["item_kind"] == "angle":
            latest[label["item_id"]] = label
        else:
            excluded[f"{label['source']} ({label['item_kind']})"] = excluded.get(f"{label['source']} ({label['item_kind']})", 0) + 1
    by_week = {}
    for angle_id, label in latest.items():
        row = (cards or {}).get(angle_id)
        card = ((row or {}).get("content_body") or {}).get("card")
        if not card:
            excluded["gate label without its card"] = excluded.get("gate label without its card", 0) + 1
            continue
        model = ((row["content_body"].get("provenance") or {}).get("model")) or GENERATORS["dispositions"]
        week = label["week_id"] or row.get("week_id")
        by_week.setdefault(week, []).append((label, card_candidate(angle_id, card, tier=_tier(label), generator=model)))
    for week, rows in sorted(by_week.items(), key=lambda kv: str(kv[0])):
        # Accepted as section 2.3 counts it: developed, or reframed with the central point kept. A reframe that drops
        # the central point, and a hold, rank between the two (their tiers) but form no pair.
        accepted = [(lab, c) for lab, c in rows if c.tier == ACCEPTED_TIER]
        closed = [(lab, c) for lab, c in rows if lab["disposition"] in CLOSED]
        for la, ca in accepted:
            for lc, cc in closed:
                pairs.append(Pair(f"d-{ca.id}-{cc.id}", "dispositions", "content card", cc, ca, ca.id, week,
                                  (la["label_id"], lc["label_id"]), details={
                                      "accepted": la["disposition"], "closed": lc["disposition"],
                                      "ratings": {c.id: r for c, r in ((ca, _her_ratings(la)), (cc, _her_ratings(lc))) if r}}))
    order = {g: i for i, g in enumerate(GROUPS)}
    return sorted(pairs, key=lambda p: (order[p.group], p.pair_id)), excluded


def load_labels(source: str = "auto") -> tuple[list[dict], dict[str, dict], str]:
    """The labels and the Gate 1 cards they name. files: benchmark version 1's labels as `seed` writes them (no Gate 1
    dispositions); db: the calibration rows through benchmark.ground_truth; auto: db when ATELIER_DATABASE_URL is set."""
    import os
    if source == "auto":
        source = "db" if os.getenv("ATELIER_DATABASE_URL") else "files"
    if source == "files":
        return build_labels(), {}, "files"
    from backend_pipeline.database import connect
    from backend_pipeline.storage_config import StorageSettings

    from .benchmark import ground_truth
    with connect(StorageSettings.from_env().database_url, vectors=False) as conn:
        labels = [dict(r) for r in ground_truth(conn, include_proxy=True)]
        ids = [r["item_id"] for r in labels if r["item_kind"] == "angle"]
        cards = {r["angle_id"]: dict(r) for r in conn.execute(
            "SELECT angle_id,week_id,content_body FROM content_angles WHERE angle_id = ANY(%s)", (ids,))} if ids else {}
    return labels, cards, "db"


# Measures.
def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    """The 95% Wilson score interval for k of n."""
    if not n:
        return None
    p = k / n
    centre, half, scale = p + z * z / (2 * n), z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)), 1 + z * z / n
    return [round(max(0.0, (centre - half) / scale), 4), round(min(1.0, (centre + half) / scale), 4)]


def share(k: int, n: int) -> dict:
    return {"agree": k, "of": n, "share": round(k / n, 4) if n else None, "ci95": wilson(k, n)}


def kendall_tau_b(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    concordant = discordant = tied_x = tied_y = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = xs[i] - xs[j], ys[i] - ys[j]
            if dx == 0:
                tied_x += 1
            if dy == 0:
                tied_y += 1
            if dx and dy:
                concordant += (dx > 0) == (dy > 0)
                discordant += (dx > 0) != (dy > 0)
    total = n * (n - 1) // 2
    denominator = sqrt((total - tied_x) * (total - tied_y))
    return round((concordant - discordant) / denominator, 4) if denominator else None


def rank_agreement(pairs: list[Pair], judged: list[dict]) -> dict | None:
    """Per week, the correlation between each candidate's mean judge score and its tier in the labels (Kendall's tau-b),
    where a week has at least three candidates on at least two tiers."""
    tiers, scores = {}, {}
    for pair in pairs:
        for c in (pair.x, pair.y):
            tiers[(pair.week, c.id)] = c.tier
    for c in judged:
        week = next(p.week for p in pairs if p.pair_id == c["pair_id"])
        for side in SIDES:
            scores.setdefault((week, c[side]), []).append(c["overall"][side])
    weeks = {}
    for (week, cid), values in scores.items():
        if week is not None and tiers.get((week, cid)) is not None:
            weeks.setdefault(week, []).append((statistics.mean(values), tiers[(week, cid)]))
    out = {}
    for week, rows in sorted(weeks.items()):
        if len(rows) >= 3 and len({t for _, t in rows}) >= 2:
            out[week] = {"candidates": len(rows), "kendall_tau_b": kendall_tau_b([s for s, _ in rows], [t for _, t in rows])}
    if not out:
        return None
    taus = [w["kendall_tau_b"] for w in out.values() if w["kendall_tau_b"] is not None]
    return {"weeks": out, "mean_kendall_tau_b": round(statistics.mean(taus), 4) if taus else None}


def criterion_means(rows: list[dict]) -> dict | None:
    """The judge's mean score per criterion for the candidate the label prefers and for the other one."""
    if not rows:
        return None
    preferred = [c["ratings"]["A" if c["A"] == c["label_preferred"] else "B"] for c in rows]
    other = [c["ratings"]["B" if c["A"] == c["label_preferred"] else "A"] for c in rows]
    return {name: {k: round(statistics.mean(r[k] for r in side), 3) for k in rubric.KEYS}
            for name, side in (("label_preferred", preferred), ("other", other))}


def rubric_agreement(pairs: list[Pair], rows: list[dict]) -> dict | None:
    """Where the reviewer rated a card on rubric 2.3a (E.X3), the judge's scores against hers: per criterion and overall,
    the mean absolute difference over every judgement of a rated card, and how many cards it rests on."""
    theirs = {cid: r for p in pairs for cid, r in (p.details.get("ratings") or {}).items()}
    diffs, cards = {k: [] for k in rubric.KEYS}, set()
    for c in rows:
        for side in SIDES:
            hers = theirs.get(c[side])
            if hers:
                cards.add(c[side])
                for k in rubric.KEYS:
                    diffs[k].append(abs(c["ratings"][side][k] - hers[k]))
    if not cards:
        return None
    every = [d for k in rubric.KEYS for d in diffs[k]]
    return {"rated_cards": len(cards), "mean_absolute_difference": {k: round(statistics.mean(v), 3) for k, v in diffs.items()},
            "overall_mean_absolute_difference": round(statistics.mean(every), 3)}


def summarise(pairs: list[Pair], comparisons: list[dict]) -> dict:
    judged = [c for c in comparisons if c.get("status") == "judged"]
    by_pair = {}
    for c in judged:
        by_pair.setdefault(c["pair_id"], []).append(c)
    groups = {}
    for group in GROUPS:
        members = [p for p in pairs if p.group == group]
        if not members:
            continue
        rows = [c for p in members for c in by_pair.get(p.pair_id, [])]
        both = [by_pair[p.pair_id] for p in members if len(by_pair.get(p.pair_id, [])) == 2]
        flips = sum(x["preferred"] != y["preferred"] for x, y in both)
        out = {"pairs": len(members), "judgements": share(sum(c["agrees"] for c in rows), len(rows)),
               "pairs_right_in_both_orders": share(sum(x["agrees"] and y["agrees"] for x, y in both), len(both)),
               "position_bias": {"pairs_in_both_orders": len(both), "order_flips": flips,
                                 "flip_rate": round(flips / len(both), 4) if both else None,
                                 "chose_A": share(sum(c["preferred_side"] == "A" for c in rows), len(rows))},
               "criterion_means": criterion_means(rows),
               "rank": rank_agreement(members, rows)}
        if group == "dispositions":
            kinds = {}
            for c in rows:
                p = next(p for p in members if p.pair_id == c["pair_id"])
                kinds.setdefault(f"{p.details['accepted']}_over_{p.details['closed']}", []).append(c["agrees"])
            out["by_disposition"] = {k: share(sum(v), len(v)) for k, v in sorted(kinds.items())}
            out["rubric_ratings"] = rubric_agreement(members, rows)
        groups[group] = out
    export = groups.get("export_pairs")
    complete = bool(export) and export["pairs"] == EXPORT_PAIRS and export["pairs_right_in_both_orders"]["of"] == EXPORT_PAIRS
    prescreen = {"bar": PRESCREEN_BAR, "rule": "at least 80% of the 38 export pairs right in both orders, then Whitney's live "
                 "Week 5 dispositions (plan E.B3)",
                 "export_pairs_right_in_both_orders": export["pairs_right_in_both_orders"] if export else None,
                 "passes_first_test": (export["pairs_right_in_both_orders"]["share"] >= PRESCREEN_BAR) if complete else None,
                 **({} if complete else {"not_judged": "the first test needs all 38 export pairs judged in both orders"})}
    return {"groups": groups, "prescreen": prescreen}


def input_set(pairs: list[Pair], model: str, context_record: dict, seed: int, both_orders: bool) -> str:
    """The run's input-set hash, which its run plan is approved for (E.B1)."""
    return "sha256:" + canonical_hash({"judge": PROMPT_VERSION, "model": model, "rubric": rubric.TEXT_SHA256, "seed": seed,
                                       "both_orders": both_orders, "context": context_record["sha256"],
                                       "pairs": [[p.pair_id, p.preferred, candidate_text(p.x), candidate_text(p.y)] for p in pairs]})


def estimate(model: str, planned: list[dict]) -> dict:
    """Cost of the calls still to make: without a prompt cache, and with the shared system prefix cached (Anthropic)."""
    price = price_of(model)
    if price is None or not planned:
        return {"without_prompt_cache": None if price is None else 0.0, "with_prompt_cache": None if price is None else 0.0}
    pin, pout = price[0] / 1e6, price[1] / 1e6
    system = [(c["system_characters"] + 3) // 4 for c in planned]
    user = [(c["user_characters"] + 3) // 4 for c in planned]
    output = OUTPUT_TOKENS_ESTIMATE * len(planned) * pout
    plain = (sum(system) + sum(user)) * pin + output
    if not model.startswith("anthropic/"):
        return {"without_prompt_cache": round(plain, 4), "with_prompt_cache": None}
    prefixes = {}
    for c, tokens in zip(planned, system):
        prefixes.setdefault(c["system_sha256"], []).append(tokens)
    cached = sum(t[0] * CACHE_WRITE + sum(t[1:]) * CACHE_READ for t in prefixes.values()) * pin + sum(user) * pin + output
    return {"without_prompt_cache": round(plain, 4), "with_prompt_cache": round(cached, 4)}


def _judge_all(pairs: list[Pair], *, model: str, context: str, seed: int, both_orders: bool, mode: str, kb) -> tuple:
    """Every comparison of a run, each pair in its drawn order first and, with both orders, reversed; one context and
    one run plan (paid mode only) serve the whole run."""
    if mode not in ("paid", "replay", "dry"):
        raise ValueError("mode is paid, replay or dry")
    check_family(model, pairs)
    context_text, context_record = judge_context(context, [candidate_text(c) for p in pairs for c in (p.x, p.y)], kb=kb)
    input_hash = input_set(pairs, model, context_record, seed, both_orders)
    plan = from_environment(default_file=PLAN_FILE) if mode == "paid" else None
    comparisons = []
    for pair in pairs:
        first = first_order(seed, pair.pair_id)
        for order in (first, 1 - first) if both_orders else (first,):
            comparisons.append(compare(pair, order, context_text=context_text, context_sha256=context_record["sha256"],
                                       model=model, seed=seed, mode=mode, plan=plan, input_set_hash=input_hash))
    head = {"benchmark": VERSION, "judge": {"model": model, "stage": STAGE, "prompt_version": PROMPT_VERSION, "seed": seed,
                                            "both_orders": both_orders, "context": context_record},
            "rubric": {"version": rubric.VERSION, "text_sha256": rubric.TEXT_SHA256}, "input_set_hash": input_hash}
    return head, comparisons


def _dry(head: dict, comparisons: list[dict], purpose: str) -> dict:
    """The calls still to make, their estimated cost, and the command that creates a run plan bound to this run."""
    model = head["judge"]["model"]
    planned = [c for c in comparisons if c["status"] == "to_call"]
    cost = estimate(model, planned)
    # The cap assumes the prompt cache holds (with a margin); if it does not, the plan is exhausted early, the run
    # stops, and every saved response is reused when it is resumed under a new plan.
    cap = round((cost["with_prompt_cache"] or cost["without_prompt_cache"] or 0) * 1.5 + 0.05, 2)
    plan_file = PLAN_FILE.relative_to(PROJECT).as_posix()
    return {**head, "dry": True, "calls": len(comparisons), "already_saved": len(comparisons) - len(planned),
            "to_call": len(planned), "estimated_cost_usd": cost,
            "plan_command": (f"python -m backend_pipeline.storage_cli plan create --file ../{plan_file} --purpose "
                             f"\"{purpose} ({model}, {head['judge']['context']['name']})\" --stage {STAGE} --model {model} "
                             f"--input-set-hash {head['input_set_hash']} --max-calls {max(len(planned), 1)} "
                             f"--max-cost-usd {cap} --approver <email>")}


def _rows(comparisons: list[dict]) -> list[dict]:
    return [{k: v for k, v in c.items() if k not in ("system_characters", "user_characters", "system_sha256")} for c in comparisons]


def calibrate(pairs: list[Pair], *, model: str = JUDGE_MODEL, context: str = DEFAULT_CONTEXT, seed: int = DEFAULT_SEED,
              both_orders: bool = True, mode: str = "paid", limit: int | None = None, kb=None,
              label_source: str | None = None, excluded: dict | None = None) -> dict:
    """Run (or count) the judge on labelled pairs and report its agreement with them."""
    pairs = pairs[:limit] if limit else list(pairs)
    head, comparisons = _judge_all(pairs, model=model, context=context, seed=seed, both_orders=both_orders, mode=mode, kb=kb)
    counts = {g: sum(p.group == g for p in pairs) for g in GROUPS}
    head["labels"] = {"source": label_source, "pairs": counts, "excluded": excluded or {}, "limit": limit}
    if mode == "dry":
        return _dry(head, comparisons, "E.B3 judge calibration")
    return {**head, **summarise(pairs, comparisons),
            "unparsed": sum(c["status"] == "unparsed" for c in comparisons),
            "missing": sum(c["status"] == "missing" for c in comparisons),
            "independence": independence(),
            "total_cost_usd": round(sum(c.get("cost") or 0 for c in comparisons), 6),
            "comparisons": _rows(comparisons),
            "notes": ["A smoke test, never the gate (E.B3): the judge may pre-screen only after the first test (export pairs, "
                      "both orders) and then Whitney's live Week 5 dispositions.",
                      "export_pairs are proxies the plan names as the first calibration set; week1_reframes are Whitney's "
                      "own and compare titles only (the originals survive as titles); dispositions are WIA's Gate 1 "
                      "labels, never delegated ones (R55).",
                      "An order flip is a pair whose choice changed when the order did: the judge followed the position."]}


# Configurations: two configurations' saved samples, slate against slate (the evaluation command's pairwise judge).
CONFIG_GROUP = "configurations"
SLATE_KIND = "a week's slate of content cards (rate each slate as a whole: each criterion over its cards)"


def saved_sample(name: str, week: str, sample: int) -> dict | None:
    """A configuration's saved sample as `evaluation run` wrote it, or None; never generated here. `name` is a
    configuration, or configuration@knowledge-base-version for a run on a compiled version (L.B4)."""
    from . import run
    config, _, version = name.partition("@")
    if config not in run.CONFIGS:
        raise ValueError(f"Unknown configuration {config!r}; use one of: {', '.join(run.CONFIGS)}")
    path = run.OUT / "runs" / f"{config}-{week}-s{sample}{'.' + version if version else ''}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def config_pairs(names: list[str], weeks: list[str], samples: int) -> tuple[list[Pair], list[str]]:
    """Per week and sample index, one configuration's slate against the other's, as their saved samples hold them; and
    the samples not saved (a pair needs both)."""
    from . import run
    if len(names) != 2 or names[0] == names[1]:
        raise ValueError("Compare exactly two different configurations")
    pairs, missing = [], []
    for week in weeks:
        for s in range(1, samples + 1):
            slates = []
            for name in names:
                record = saved_sample(name, week, s)
                if not record or record.get("output") is None:
                    missing.append(f"{name} {week} s{s}")
                    continue
                cards, _ = run.cards_of(name.partition("@")[0], week, record["output"])
                slates.append(slate_candidate(f"{name}:{week}:s{s}", cards, generator=record.get("model")))
            if len(slates) == 2:
                pairs.append(Pair(f"c-{names[0]}-vs-{names[1]}-{week}-s{s}", CONFIG_GROUP, SLATE_KIND, *slates, None, week,
                                  details={"sample": s}))
    return pairs, missing


def compare_summary(names: list[str], pairs: list[Pair], comparisons: list[dict]) -> dict:
    """Per configuration: the judgements preferring it, the pairs it won in both orders, and its mean rubric scores;
    with the order flips, which say how much of the result is position."""
    owner = {c.id: c.id.split(":", 1)[0] for p in pairs for c in (p.x, p.y)}
    judged = [c for c in comparisons if c.get("status") == "judged"]
    by_pair = {}
    for c in judged:
        by_pair.setdefault(c["pair_id"], []).append(c)
    both = [rows for rows in by_pair.values() if len(rows) == 2]
    scores = {name: [] for name in names}
    for c in judged:
        for side in SIDES:
            scores[owner[c[side]]].append(c["ratings"][side])
    configs = {}
    for name in names:
        mine = scores[name]
        configs[name] = {
            "preferred": share(sum(owner[c["preferred"]] == name for c in judged), len(judged)),
            "pairs_won_in_both_orders": sum(all(owner[c["preferred"]] == name for c in rows) for rows in both),
            "mean_overall": round(statistics.mean(statistics.mean(r.values()) for r in mine), 3) if mine else None,
            "criterion_means": {k: round(statistics.mean(r[k] for r in mine), 3) for k in rubric.KEYS} if mine else None}
    weeks = {}
    for p in pairs:
        rows = by_pair.get(p.pair_id, [])
        week = weeks.setdefault(p.week, {**dict.fromkeys(names, 0), "judgements": 0})
        week["judgements"] += len(rows)
        for c in rows:
            week[owner[c["preferred"]]] += 1
    flips = sum(rows[0]["preferred"] != rows[1]["preferred"] for rows in both)
    return {"configs": configs, "by_week": weeks,
            "position_bias": {"pairs_in_both_orders": len(both), "order_flips": flips,
                              "flip_rate": round(flips / len(both), 4) if both else None,
                              "chose_A": share(sum(c["preferred_side"] == "A" for c in judged), len(judged))}}


def compare_configs(names: list[str], weeks: list[str], samples: int = 3, *, model: str = JUDGE_MODEL,
                    context: str = DEFAULT_CONTEXT, seed: int = DEFAULT_SEED, both_orders: bool = True, mode: str = "paid",
                    kb=None) -> dict:
    """Run (or count) the judge on two configurations' saved samples: each week's sample s of one against sample s of
    the other, each rendered as a slate in one plain format. A smoke test, never the gate."""
    pairs, missing = config_pairs(names, weeks, samples)
    planned = {"names": list(names), "weeks": list(weeks), "samples": samples, "pairs": len(pairs), "missing_samples": missing,
               "calls_once_saved": len(weeks) * samples * (2 if both_orders else 1)}
    if missing and mode == "dry":
        # The judge's run plan is bound to the slates it will judge, so it can be made only once every sample is saved:
        # say what to generate first, and how many calls the comparison will then be.
        return {"dry": True, "configurations": planned, "calls": None, "plan_command": None,
                "note": "Generate the missing samples first (python -m evaluation run, under its own run plan); the judge's "
                        "plan binds the saved slates, so its command is printed once every sample is saved."}
    if not pairs:
        raise ValueError("No sample index has both configurations saved; run `python -m evaluation run` first: "
                         + ", ".join(missing))
    head, comparisons = _judge_all(pairs, model=model, context=context, seed=seed, both_orders=both_orders, mode=mode, kb=kb)
    head["configurations"] = planned
    if mode == "dry":
        return _dry(head, comparisons, f"E.B3 judge comparison {names[0]} vs {names[1]}")
    return {**head, **compare_summary(names, pairs, comparisons),
            "unparsed": sum(c["status"] == "unparsed" for c in comparisons),
            "missing": sum(c["status"] == "missing" for c in comparisons),
            "total_cost_usd": round(sum(c.get("cost") or 0 for c in comparisons), 6),
            "comparisons": _rows(comparisons),
            "notes": ["A smoke test, never the gate (E.B3, section 2.3): WIA's dispositions and ratings decide.",
                      "Each pair is one week's sample s of each configuration, rendered in one plain format (the same "
                      "card fields, moment references removed); which one is A is drawn from the seed, and with both "
                      "orders an order flip is a pair whose choice followed the position.",
                      "Trust the result only as far as the judge's calibration (judge-calibrate) allows."]}


def results_path(model: str, context: str, compared: list[str] | None = None) -> Path:
    from datetime import date
    what = f"compare-{'-vs-'.join(n.replace('@', '.') for n in compared)}-" if compared else ""
    return OUT / "results" / f"{date.today().isoformat()}-judge-{what}{model.split('/')[-1]}-{context.replace('+', '-')}.json"
