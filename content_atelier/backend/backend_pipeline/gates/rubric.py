"""Review rubric 2.3a (plan section 2.3a, E.X7), as confirmed under D12: `rubric-2.3a.v1`.

WIA's reviewer rates each card against it at Gate 1 (E.X3), on the form the card screen shows from `form()`, and the
label records the version and the hash of the text she saw. E.B3's judge imports the same text as a smoke test only:
`TEXT` (the whole rubric as one block), `CRITERIA` (each a `Criterion` with `key`, `name` and `text`, in order), `SCALE`,
`ANCHORS` and `VERSION`, and records `VERSION` with its scores; `ratings()` checks a set of scores against the criteria and
scale and gives the label's shape.

The text is frozen: it is never copied from a candidate prompt, and any change to it is a new version, recorded like a
knowledge-base change (section 2.3a); the pinned hash in test_rubric.py fails on an unversioned edit.
"""
from __future__ import annotations

import hashlib
from statistics import mean
from typing import NamedTuple


class Criterion(NamedTuple):
    """One rubric criterion: its stable key (the label's and the critic's), its name, and what it asks, word for word."""
    key: str
    name: str
    text: str


VERSION = "rubric-2.3a.v1"
SCALE = (1, 2, 3, 4, 5)
ANCHORS = {1: "would not publish", 3: "publishable after a light reframe", 5: "publish as is"}
# In the rubric's order. The editorial critic (E.B10) judges criteria 1 and 4 under the same keys.
CRITERIA = (
    Criterion("wia_is_the_subject", "WIA is the subject",
              "The card shows what WIA knows, how it thinks or works with clients, or why its approach matters (R40; "
              "steps 4 and 6 of Whitney's seven-step framework in the review document). An education or opinion card "
              "passes when the view is WIA's own."),
    Criterion("strategic_purpose", "Strategic purpose",
              "The pillar, content type and offer connection fit Savannah's strategy and the current content plan "
              "(framework step 2)."),
    Criterion("audience", "Audience",
              "It speaks to WIA's market: established, growth-minded wedding businesses. It does not speak to the "
              "person on the call, or to an owner in a place of desperation (framework step 3)."),
    Criterion("worth_attention", "Worth attention",
              "It carries a real tension, and it is distinct from the week's other cards and from recent content "
              "(framework step 5; \"distinctiveness\" is her ranking criterion)."),
    Criterion("sounds_like_whitney", "Sounds like Whitney",
              "Plain, confident and specific to weddings; none of her rejected constructions."),
)
KEYS = tuple(c.key for c in CRITERIA)
INSTRUCTION = ("Rate each card 1 to 5 on each criterion: " + "; ".join(f"{n} = {a}" for n, a in ANCHORS.items()) + ".")
TEXT = "\n".join([f"Review rubric 2.3a ({VERSION})", "", INSTRUCTION, ""]
                 + [f"{i}. {c.name}. {c.text}" for i, c in enumerate(CRITERIA, 1)])
TEXT_SHA256 = hashlib.sha256(TEXT.encode("utf-8")).hexdigest()


def form() -> dict:
    """The rubric as the review form shows it: its version, scale, anchors and criteria, and the text they render."""
    return {"version": VERSION, "scale": list(SCALE), "anchors": {str(k): v for k, v in ANCHORS.items()},
            "instruction": INSTRUCTION, "criteria": [c._asdict() for c in CRITERIA],
            "text": TEXT, "text_sha256": TEXT_SHA256}


def ratings(values: dict | None, version: str | None = None) -> dict | None:
    """A reviewer's ratings of one card as a label stores them, or None when none were given. Every criterion is rated,
    1 to 5, against the version the form showed; `overall` is their mean (the bar in section 2.3 is on it and on each)."""
    if not values:
        return None
    if version is not None and version != VERSION:
        raise ValueError(f"The form showed rubric {version}, but {VERSION} is in force; reload the card and rate it again")
    if set(values) != set(KEYS):
        missing, unknown = [k for k in KEYS if k not in values], sorted(set(values) - set(KEYS))
        raise ValueError("Rate every rubric criterion, or none"
                         + (f"; missing: {', '.join(missing)}" if missing else "") + (f"; unknown: {', '.join(unknown)}" if unknown else ""))
    if any(isinstance(v, bool) or not isinstance(v, int) or v not in SCALE for v in values.values()):
        raise ValueError("Each rubric rating is a whole number from 1 to 5")
    criteria = {k: values[k] for k in KEYS}
    return {"version": VERSION, "text_sha256": TEXT_SHA256, "criteria": criteria, "overall": round(mean(criteria.values()), 2)}


__all__ = ["ANCHORS", "CRITERIA", "Criterion", "INSTRUCTION", "KEYS", "SCALE", "TEXT", "TEXT_SHA256", "VERSION", "form", "ratings"]
