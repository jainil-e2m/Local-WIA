"""Plan 2.B4: the deterministic checks (role plausibility, numbers, consent), and that Python and migration 008's SQL agree."""
from __future__ import annotations

import itertools
import re
from pathlib import Path

import pytest

from backend_pipeline.cycle import verification
from backend_pipeline.moments import checks, types
from backend_pipeline.tests.platform_db import platform_url  # noqa: F401 (fixture)

MIGRATION = Path(__file__).resolve().parents[2] / "migrations" / "008_moments_ledger.sql"


# ---- role plausibility ---------------------------------------------------------------------------------------------------

def test_a_staff_praise_line_is_never_a_testimonial():
    verdict = checks.role_plausibility("testimonial", "staff")
    assert verdict["passed"] is False and verdict["moment_type"] == "observation" and verdict["evidence_kind"] == "team_report"
    assert verdict["original_type"] == "testimonial" and "client's to claim" in verdict["reason"]
    again = checks.assess(original_type="testimonial", speaker_role="staff", sensitivity="public_candidate", client_consent="may_name",
                          fields={"quote": "She loves the new form."}, anchor_texts=["Carmen: She loves the new form."])
    assert again["moment_type"] == "observation" and again["evidence_kind"] == "team_report"
    assert again["consent_status"] == "anonymise", "a relayed line is never cleared for naming, even for a client who allows it"


def test_a_client_or_prospect_may_claim_a_result_or_testimonial_and_an_unknown_speaker_is_a_relay():
    for role in ("client", "prospect"):
        for kind in types.CLIENT_CLAIM_TYPES:
            assert checks.role_plausibility(kind, role) == {"speaker_role": role, "original_type": kind, "passed": True,
                                                            "moment_type": kind, "evidence_kind": "direct_quote"}
    unknown = checks.role_plausibility("result", "unknown")
    assert unknown["evidence_kind"] == "team_report" and unknown["moment_type"] == "result" and "relay" in unknown["reason"]
    assert checks.role_plausibility("testimonial", None)["moment_type"] == "observation"
    # A type that is not the client's to claim keeps its evidence kind whoever says it.
    assert checks.role_plausibility("teaching", "staff")["evidence_kind"] == "direct_quote"
    assert checks.role_plausibility("data_point", "unknown")["passed"] is True


def test_the_roster_places_a_speaker_whose_document_has_no_speaker_map_yet():
    roster = [{"name": "Carmen Cruickshank", "status": "current", "aliases": ["Carmen Cruickshank", "Carmen"]},
              {"name": "Fallon", "status": "former", "aliases": ["Fallon"]}, {"name": "Ghost", "status": "invented", "aliases": ["Ghost"]}]
    assert checks.fallback_role("Carmen Cruickshank", roster) == "staff" and checks.fallback_role("Fallon", roster) == "staff"
    assert checks.fallback_role("Dana Lee", roster) == "unknown", "never client without the document's call type"
    assert checks.fallback_role("Ghost", roster) == "unknown" and checks.fallback_role(None, roster) == "unknown"
    document = {"speaker_map": {"Dana Lee": {"person_id": "p1", "role": "client"}}}
    assert checks.speaker_of(document, {"speaker": "Dana Lee"}) == {"label": "Dana Lee", "person_id": "p1", "role": "client"}
    assert checks.speaker_of({}, {"speaker": "Carmen"}, roster)["role"] == "staff"
    assert checks.speaker_of({}, {"speaker": None})["role"] == "unknown"


# ---- numbers --------------------------------------------------------------------------------------------------------------

def test_a_figure_absent_from_the_source_fails_the_number_check():
    anchor = ["Dana Lee: We had 45 bookings in March and spent $1,200 on ads."]
    ok = checks.number_check({"quote": "We had 45 bookings in March", "proposition": "Client: Reported 45 bookings; spent $1,200"}, anchor)
    assert ok["passed"] is True and ok["absent"] == [] and {f["digits"] for f in ok["figures"]} == {"45", "1200"}
    bad = checks.number_check({"proposition": "Client: Reported 60 bookings in March"}, anchor)
    assert bad["passed"] is False and bad["absent"] == ["60 bookings"]
    assert bad["figures"][0] == {"field": "proposition", "figure": "60 bookings", "digits": "60", "found_in": "absent"}


def test_a_figure_only_in_the_surrounding_context_is_listed_apart_and_also_fails():
    result = checks.number_check({"context_summary": "She had spent 800 dollars"}, ["Dana: It went well."], ["Carmen: you spent 800 on ads"])
    assert result["passed"] is False and result["absent"] == [] and result["context_only"] == ["800"]


def test_the_record_s_process_step_label_is_not_a_stated_figure():
    record = "Carmen explained: Audit | Process step: Step 12 review"
    assert checks.number_check({"proposition": record}, ["Carmen: let us audit"])["passed"] is True


def test_the_card_verification_and_the_ledger_share_one_reading_of_a_figure():
    assert verification.digits_in(["spent $1,200.50", "about 45"]) == {"1200.50", "45"}
    assert verification.figures_in("45 bookings and 3 tours, $5k, 12%") == [("45 bookings", "45"), ("3 tours", "3"), ("$5k", "5"), ("12%", "12")]
    assert checks.number_check({"quote": "12%"}, ["it went up 12%"])["passed"] is True


# ---- consent --------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("consent,sensitivity,evidence,expected", [
    ("no_use", "public_candidate", "direct_quote", "do_not_use"),
    ("no_use", "internal_only", "direct_quote", "do_not_use"),
    ("may_name", "internal_only", "direct_quote", "internal_only"),
    ("may_name", "public_candidate", "direct_quote", "cleared"),
    ("may_name", "public_candidate", "team_report", "anonymise"),
    ("may_name", "unknown", "direct_quote", "anonymise"),
    ("anonymise_only", "public_candidate", "direct_quote", "anonymise"),
    (None, "public_candidate", "direct_quote", "anonymise"),
    (None, "internal_only", "direct_quote", "internal_only"),
])
def test_consent_status_follows_the_clients_level_the_sensitivity_and_the_evidence(consent, sensitivity, evidence, expected):
    assert checks.consent_status(consent, sensitivity, evidence) == expected


def test_a_moment_from_a_client_with_no_use_consent_carries_do_not_use():
    out = checks.assess(original_type="result", speaker_role="client", sensitivity="public_candidate", client_consent="no_use",
                        fields={"quote": "We got three bookings."}, anchor_texts=["Dana: We got three bookings."])
    assert out["consent_status"] == "do_not_use" and out["checks"]["consent"]["client_consent"] == "no_use"
    assert checks.assess_unverified(original_type="result", sensitivity="unknown", client_consent="no_use")["consent_status"] == "do_not_use"


# ---- Python and SQL agree --------------------------------------------------------------------------------------------------

def migration_statements() -> list[str]:
    text = MIGRATION.read_text(encoding="utf-8")
    wanted = ("UPDATE key_moments SET evidence_kind = 'team_report'", "UPDATE key_moments m SET consent_status = CASE",
              "UPDATE key_moments SET consent_status = 'internal_only' WHERE client_id IS NULL")
    out = []
    for start in wanted:
        at = text.index(start)
        out.append(text[at:text.index(";", at)])
    return out


def test_the_python_rules_and_migration_008s_sql_agree(platform_url):
    """Insert every combination, run the migration's own statements on them, and compare with `checks`."""
    from backend_pipeline.database import connect
    from backend_pipeline.tests.platform_db import empty
    empty(platform_url)
    consents = [None, "anonymise_only", "may_name", "no_use"]
    cases = list(itertools.product(("result", "testimonial", "observation", "teaching"), ("staff", "client", "prospect", "unknown", "vendor"),
                                   ("public_candidate", "internal_only", "unknown"), consents))
    with connect(platform_url) as conn:
        for consent in consents[1:]:
            conn.execute("INSERT INTO clients(client_id,name,consent) VALUES (%s,%s,%s)", (f"c_{consent}", f"Client {consent}", consent))
        for i, (kind, role, sensitivity, consent) in enumerate(cases):
            conn.execute("""INSERT INTO key_moments(moment_id,moment_body,evidence_refs,moment_type,speaker_role,sensitivity,client_id)
                VALUES (%s,'{}','[]',%s,%s,%s,%s)""", (f"m{i}", kind, role, sensitivity, f"c_{consent}" if consent else None))
        for statement in migration_statements():
            conn.execute(statement)
        stored = {r["moment_id"]: r for r in conn.execute("SELECT moment_id,evidence_kind,consent_status FROM key_moments")}
    for i, (kind, role, sensitivity, consent) in enumerate(cases):
        evidence = checks.role_plausibility(kind, role)["evidence_kind"]
        assert stored[f"m{i}"]["evidence_kind"] == evidence, (kind, role)
        assert stored[f"m{i}"]["consent_status"] == checks.consent_status(consent, sensitivity, evidence), (kind, role, sensitivity, consent)
    assert re.search(r"consent_status", MIGRATION.read_text(encoding="utf-8")) and len(cases) == 240


