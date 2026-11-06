"""The per-document scene check (plan 2.B2): one response, validated scene by scene.

`partition_scenes` is E.B12a's rule applied to a scene profile's response for one document, without the weekly path's
seven-type contract (profile v2 emits twelve types, and a changed contract would change the request fingerprints of the
saved weekly responses, so the weekly validators stay as they are and this one reuses their parts):

* the response as a whole must match its schema, acknowledge the delivered document exactly, carry unique local keys and, if
  it holds no scene, say why. A failure here is a schema failure (`SchemaViolation`, repairable): the llm module makes
  exactly one repair call, and if that fails too the document's job fails and no other document is touched;
* each scene is then checked alone with `Pipeline._check_moment_structure` and the quote rule of
  `moment_validation.repair_quote`: a quote that binds is kept, a near-miss is repaired to the source's own words with the
  repair recorded, a quote found in the source's own words in exactly one turn of the document is re-anchored on that turn
  (`rebind`, recorded as a repair with the model's original references), and the rest is an unverified record (`reason`,
  never proof). One unbindable quote never costs another scene.

Moment identity is `Pipeline._moment`'s content hash, so extracting the same scene again stores nothing new.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..llm.stage import SchemaViolation
from ..moment_validation import REPAIR_RULE, WORD, MomentPartition, repair_quote
from ..pipeline import Pipeline
from ..weekly import meeting_inventory, resolve_moment_references
from . import scenes


# E.B12: a quote that binds, in the source's own words, to exactly one turn of the document is re-anchored there (`rebind`).
REBIND_RULE = "unique-verbatim-turn.v1"
REBIND_MIN_WORDS = 6


@dataclass
class ScenePartition(MomentPartition):
    """The moments that bind, the repairs and the unverified records, plus which scene (local key) each moment came from."""
    local_keys: dict[str, str] = field(default_factory=dict)
    scenes: dict[str, dict] = field(default_factory=dict)
    # Profile v3 (E.B31): counter-expected decisions kept as decisions because they broke the type's rule.
    retyped: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        return {**super().summary(), "scene_count": len(self.moments) + len(self.unverified),
                **({"retyped_scenes": self.retyped} if self.retyped else {})}


def check_response(output: dict, refs: dict[str, str], profile: str):
    """The response-level checks. Returns the validated response; raises `ValidationError` or `SchemaViolation` (repairable)."""
    response = scenes.PROFILES[profile]["response"].model_validate(output)
    keys = [s.local_key for s in response.scenes]
    if len(keys) != len(set(keys)):
        raise SchemaViolation("Scene local keys must be unique")
    expected = meeting_inventory(refs)
    received = sorted(output["processed_meetings"], key=lambda item: item["meeting_ref"])
    if received != sorted(expected, key=lambda item: item["meeting_ref"]):
        raise SchemaViolation("processed_meetings must list the delivered meeting exactly as the delivery inventory does: "
                              + str(expected))
    if not response.scenes and not response.coverage_notes:
        raise SchemaViolation("An empty scene result requires an explanation in coverage_notes")
    return response


def partition_scenes(output: dict, refs: dict[str, str], transcripts, profile: str, *, call_type: str | None = None) -> ScenePartition:
    """Validate one document's scene response scene by scene (see the module docstring). `call_type` is the document's (v4:
    team practice only in an internal meeting)."""
    check_response(output, refs, profile)
    contract = scenes.PROFILES[profile]["response"]
    retyped = []
    if profile in scenes.TYPE_RULE_PROFILES:
        # E.B31: the type rules, on a working copy; the quote of every scene, the new types' too, is checked below.
        output, retyped = scenes.check_scene_types(output, call_type=call_type)
    compact = scenes.to_compact(output, contract)
    spans = {s.span_id: s for t in transcripts for s in t.spans}
    by_key = {s["local_key"]: s for s in output["scenes"]}
    result = ScenePartition(retyped=retyped)
    order = sorted(refs, key=lambda ref: spans[refs[ref]].ordinal) if all(refs[r] in spans for r in refs) else []
    for moment in compact["moments"]:
        key = moment["local_key"]
        try:
            draft, raw, repair = _bind(moment, refs, spans, key)
        except ValueError as error:
            rebound = rebind(moment, refs, spans, order)
            if rebound is None:
                result.unverified.append({"local_key": key, "reason": str(error), "usable_as_proof": False,
                                          "draft": getattr(error, "draft", moment)})
                continue
            try:
                draft, raw, repair = _bind(rebound, refs, spans, key)
            except ValueError:
                result.unverified.append({"local_key": key, "reason": str(error), "usable_as_proof": False,
                                          "draft": getattr(error, "draft", moment)})
                continue
            repair = {**(repair or {}), "local_key": key, "rule": REBIND_RULE, "original_error": str(error),
                      "original_anchor_refs": moment["anchor_span_ids"], "anchor_span_id": draft.anchor_span_ids[0],
                      "original_quote": moment["quote"], "repaired_quote": raw["quote"]}
        stored = Pipeline._moment(draft, raw, spans, transcripts)
        result.moments.append(stored)
        result.local_keys[stored.moment_id] = key
        result.scenes[stored.moment_id] = by_key[key]
        if repair:
            result.repairs.append({**repair, "moment_id": stored.moment_id})
    return result


def _bind(moment: dict, refs: dict[str, str], spans: dict, key: str):
    """One compact scene resolved, structure-checked and quote-bound (with the near-miss repair); raises ValueError."""
    resolved = resolve_moment_references({"moments": [moment], "processed_span_ids": [], "coverage_notes": []}, refs)["moments"][0]
    draft = scenes.SceneMomentDraft.model_validate(resolved)
    raw, repair = draft.model_dump(mode="json"), None
    try:
        Pipeline._check_moment_structure(draft, spans)
        if not any(draft.quote in spans[x].text for x in draft.anchor_span_ids):
            repaired = repair_quote(draft.quote, [spans[x].text for x in draft.anchor_span_ids])
            if repaired is None:
                raise ValueError("Moment quote must match an existing anchor span")
            raw["quote"], at = repaired
            repair = {"local_key": key, "rule": REPAIR_RULE, "original_quote": draft.quote, "repaired_quote": raw["quote"],
                      "anchor_span_id": draft.anchor_span_ids[at]}
    except ValueError as error:
        error.draft = raw  # the unverified record keeps the resolved draft, as before
        raise
    return draft, raw, repair


def rebind(moment: dict, refs: dict[str, str], spans: dict, order: list[str]) -> dict | None:
    """The scene re-anchored on the one turn of its document that holds its quote in the source's own words, or None.

    On long calls the model sometimes cites a turn's timestamp in seconds as its reference (m1.t1696 for the turn at 28:16)
    or an anchor a few turns away from the words it quotes. When the quote, at least REBIND_MIN_WORDS words, binds to
    exactly one turn of the document, that turn becomes the only anchor; the context stays the model's if it resolves and
    holds that turn, else it is the turn with two on each side. A quote found in no turn, or in several, stays unverified.
    """
    if not order or len(WORD.findall(moment.get("quote") or "")) < REBIND_MIN_WORDS:
        return None
    hits = [i for i, ref in enumerate(order) if repair_quote(moment["quote"], [spans[refs[ref]].text]) is not None]
    if len(hits) != 1:
        return None
    at = hits[0]
    first, last = moment.get("context_first_span_id"), moment.get("context_last_span_id")
    if not (first in refs and last in refs and order.index(first) <= at <= order.index(last)):
        first, last = order[max(at - 2, 0)], order[min(at + 2, len(order) - 1)]
    return {**moment, "anchor_span_ids": [order[at]], "context_first_span_id": first, "context_last_span_id": last}
