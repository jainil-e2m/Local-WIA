"""L.B1: one schema per item kind; a malformed body is rejected before it reaches the store."""
from __future__ import annotations

from datetime import date

import pytest

from backend_pipeline.knowledge import items

VALID = {
    "rule": {"statement": "No em dashes in new copy", "level": "ban", "scope": "all", "code": "RR-01"},
    "exemplar": {"channel": "caption", "text": "You can't optimize what you can't measure."},
    "offer": {"name": "ELEVATE", "description": "Ongoing Google and Meta ads management"},
    "price": {"offer": "ELEVATE", "amount": "$1,497/month"},
    "roster_member": {"name": "Carmen Cruickshank", "role": "Google Ads lead", "state": "current"},
    "result": {"claim": "59 leads in roughly 90 days"},
    "cta": {"wording": "Comment ADS", "cta_type": "dm_keyword", "channel": "instagram"},
    "process_step": {"process": "ELEVATE journey", "what": "Discovery call"},
    "belief": {"statement": "Ads don't create demand. They capture it."},
    "audience_phrase": {"phrase": "burned by agencies", "theme": "Burned by reps"},
    "format_rule": {"format": "Reel", "rule": "The hook lands in the first line"},
    "campaign": {"name": "Audit giveaway", "starts": "2026-10-05", "ends": "2026-10-16"},
    "content_plan_entry": {"topic": "Why tracking comes first", "purpose": "warm"},
    "performance_note": {"note": "Carousel saves doubled"},
}
MALFORMED = {
    "rule": {"statement": "x", "level": "maybe", "scope": "all"},
    "exemplar": {"channel": "caption"},
    "offer": {"name": "ELEVATE", "description": "", "state": "current"},
    "price": {"offer": "ELEVATE", "amount": "ask us"},
    "roster_member": {"name": "Viktor", "role": "bot", "state": "robot"},
    "result": {"claim": "   "},
    "cta": {"wording": "Reply", "cta_type": "carrier pigeon"},
    "process_step": {"process": "x"},
    "belief": {"statement": 7},
    "audience_phrase": {"phrase": "x"},
    "format_rule": {"format": "Reel", "rule": "x", "extra": True},
    "campaign": {"name": "x", "starts": "next week"},
    "content_plan_entry": {"topic": "x", "purpose": "sell hard"},
    "performance_note": {},
}


def test_every_kind_has_a_schema():
    assert set(items.SCHEMAS) == set(items.KINDS) == set(VALID) == set(MALFORMED)
    assert items.OPERATING_KINDS | items.IDENTITY_KINDS == set(items.KINDS)
    assert not items.OPERATING_KINDS & items.IDENTITY_KINDS


@pytest.mark.parametrize("kind", items.KINDS)
def test_each_kind_accepts_a_valid_body_and_renders_it(kind):
    body = items.validate_body(kind, VALID[kind])
    assert items.render(kind, body).strip()


@pytest.mark.parametrize("kind", items.KINDS)
def test_each_kind_rejects_a_malformed_body(kind):
    with pytest.raises(ValueError, match=f"Malformed {kind} body"):
        items.validate_body(kind, MALFORMED[kind])


def test_an_unknown_kind_or_a_non_object_body_is_rejected():
    with pytest.raises(ValueError, match="Unknown item kind"):
        items.validate_body("gossip", {})
    with pytest.raises(ValueError, match="must be an object"):
        items.validate_body("rule", ["a"])


def test_a_price_blocks_its_figure_in_public_copy():
    body = items.validate_body("price", {"offer": "ELEVATE", "amount": "$1,497/month after a $1,997 onboarding"})
    assert body["block_terms"] == ["$1,497", "$1,997"], "every figure in the amount is blocked"
    assert "block_terms" not in items.validate_body("belief", VALID["belief"])


def test_field_checks_refuse_personal_material_and_bad_exposure():
    ok = dict(kind="offer", key="offer:elevate", visibility="public", sensitivity="none", permission=None,
              valid_from=None, valid_to=None)
    items.check_fields(**ok)
    for change, message in [({"key": "Offer Elevate"}, "kind prefix"), ({"visibility": "secret"}, "Visibility"),
                            ({"sensitivity": "personal"}, "never stored"), ({"sensitivity": "confidential"}, "never stored"),
                            ({"sensitivity": "client_private"}, "internal"), ({"permission": "published"}, "Only results"),
                            ({"valid_from": date(2026, 2, 1), "valid_to": date(2026, 1, 1)}, "end before")]:
        with pytest.raises(ValueError, match=message):
            items.check_fields(**{**ok, **change})
    with pytest.raises(ValueError, match="needs its permission"):
        items.check_fields(**{**ok, "kind": "result"})


def test_keys_and_hashes_are_stable():
    assert items.key_for("offer", "Google Search Accelerator (GSA)") == "offer:google-search-accelerator-gsa"
    assert items.key_for("roster_member", "Gisselle Jiménez") == "roster:gisselle-jimenez"
    row = {"kind": "rule", "key": "rule:rr-01", "body": VALID["rule"], "text": "x", "valid_from": date(2026, 1, 1),
           "valid_to": None, "status": "candidate", "visibility": "public", "sensitivity": "none", "permission": None}
    assert items.item_hash(row) == items.item_hash(dict(row))
    assert items.item_hash(row) != items.item_hash({**row, "status": "confirmed"}), "a decision changes the hash"


def test_blocked_figures_match_whole_figures_only():
    assert items.contains_term("the retainer is $1,497/month", "$1,497")
    assert not items.contains_term("they spent $5,000 a month", "$500")
    assert not items.contains_term("a $500,000 year", "$500")
    assert items.figures("$1,997 onboarding, then $1,497/month; about $70K") == ["$1,997", "$1,497", "$70K"]


def test_an_internal_offer_fact_blocks_the_figures_it_states():
    body = items.internal_figures("offer", {"name": "GSA", "description": "Ongoing access at $197/month"}, "Ongoing access at $197/month", "internal")
    assert body["block_terms"] == ["$197"]
    public = items.internal_figures("offer", {"name": "Audit", "description": "normally $297"}, "normally $297", "public")
    assert "block_terms" not in public


def test_a_rule_carries_a_known_category_and_lint_patterns_that_compile():
    rule = {"statement": "No em dashes", "level": "ban", "scope": "all"}
    assert items.validate_body("rule", {**rule, "category": "voice"})["category"] == "voice"
    with pytest.raises(ValueError, match="category"):
        items.validate_body("rule", {**rule, "category": "style"})
    with pytest.raises(ValueError, match="does not compile"):
        items.validate_body("rule", {**rule, "patterns": [{"pattern": "(unclosed", "kind": "ban", "scope": "all", "message": "x"}]})
    body = items.validate_body("rule", {**rule, "patterns": [{"pattern": "—", "kind": "ban", "scope": "all", "message": "Em dash"}]})
    assert body["patterns"][0]["pattern"] == "—" and "patterns" not in items.validate_body("rule", rule)
    with pytest.raises(ValueError, match="category"):
        items.require_category("rule", rule)
