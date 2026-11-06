"""Per-moment validation for the weekly extraction (E.B12a).

One inexact quote must not discard a week. The response as a whole must still match its schema and its
coverage; after that each moment is checked on its own:
- a moment that binds to its anchor spans is kept;
- a near-miss quote (whitespace or punctuation only) is repaired to the exact source text, and the repair is recorded;
- anything else is kept as an unverified record, which is never saved as a key moment or used as proof.

The same rule runs on the SQL weekly path, the scene profile, the file-backed runner (`Pipeline._execute`) and the
partial-pool diagnostic (`calibration.py`). A coverage failure (a meeting or span set the response does not acknowledge
exactly) is a response-level failure and still fails the week on every path; that is the accepted rule (COVERAGE_RULE),
recorded in every validation summary.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

REPAIR_RULE = "normalised-whitespace-punctuation.v1"
# A repaired quote must still be a phrase; one or two common words would bind almost anywhere.
MIN_REPAIR_WORDS = 3
# Accepted (E.B12a "done when"): coverage is checked on the whole response, so a coverage failure fails the week.
COVERAGE_RULE = "coverage-failure-fails-week.accepted.v1"
WORD = re.compile(r"\w+")


@dataclass
class MomentPartition:
    moments: list = field(default_factory=list)
    repairs: list[dict] = field(default_factory=list)
    unverified: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        return {"validation": "per_moment.v1", "repair_rule": REPAIR_RULE, "coverage_rule": COVERAGE_RULE,
                "quote_repairs": self.repairs,
                "unverified_moments": self.unverified, "unverified_count": len(self.unverified),
                "unverified_usable_as_proof": False}


def repair_quote(quote: str, texts: list[str]) -> tuple[str, int] | None:
    """The exact source text whose words equal the quote's words, ignoring whitespace and punctuation.

    Returns the repaired quote and the index of the text it came from, or None. Word order and case must match, except the
    first word's case: a quote that starts mid-sentence is often capitalised ("And truthfully" for "um, and truthfully").
    """
    words = WORD.findall(quote)
    if len(words) < MIN_REPAIR_WORDS:
        return None
    for index, text in enumerate(texts):
        tokens = list(WORD.finditer(text))
        found = [t.group(0) for t in tokens]
        for start in range(len(found) - len(words) + 1):
            window = found[start:start + len(words)]
            if window[1:] == words[1:] and window[0].lower() == words[0].lower():
                return text[tokens[start].start():tokens[start + len(words) - 1].end()], index
    return None


def resolve_moment_references_partial(output: dict, reference_map: dict[str, str]) -> tuple[dict, dict[int, str]]:
    """Resolve compact short references moment by moment.

    The whole response's schema and meeting coverage are checked first, so a failure there still fails the week.
    A moment with an unknown or out-of-order reference is left unresolved and reported by its index instead.
    """
    from .contracts import CompactMomentResponse
    from .strategy_contracts import StrategicCompactMomentResponse, is_strategic_moment_response
    from .weekly import resolve_moment_references

    if "processed_meetings" in output:
        (StrategicCompactMomentResponse if is_strategic_moment_response(output) else CompactMomentResponse).model_validate(output)
    envelope = {key: value for key, value in output.items() if key != "moments"}
    resolved = resolve_moment_references({**envelope, "moments": []}, reference_map)
    problems = {}
    for index, moment in enumerate(output["moments"]):
        try:
            one = resolve_moment_references({**envelope, "moments": [moment]}, reference_map)["moments"][0]
        except ValueError as error:
            one = copy.deepcopy(moment)
            bounds = [one.pop(key) for key in ("context_first_span_id", "context_last_span_id") if key in one]
            one.setdefault("context_span_ids", bounds)
            problems[index] = str(error)
        resolved["moments"].append(one)
    return resolved, problems
