"""Version 3 brief checks, ledger assembly, limited repair and finalisation (E.B23).

The checks are v2's, shared (validation_v2): the locked angle, the CTA, quoted turns, claims and numbers bound to their
evidence, formats in the confirmed channel set, who speaks and who is named, internal items, clients, the rejection rules,
E.B10's narrative checks and E.B24's copy lint. What differs is where the claims come from: the ledger built after
writing (ledger_v3). A statement the ledger found unsupported is a blocking finding the repair can fix; one nobody could
check is a person's warning.

Repair (E.B23) runs only on blocking findings that are not a person's to settle at Gate 2 (schema failures are repaired by
the llm module's one schema repair). It may remove or reword what a finding points at, never add a qualifier: a repair
whose copy carries checking language (E.B24's lint) the copy did not carry before is rejected, and the brief keeps the
writer's copy with its findings for Gate 2.
"""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from ..repository import insert
from ..store import canonical_hash
from . import ledger_v3
from .contracts import Dossier
from .contracts_v3 import SCHEMA_V3, BriefDocumentV3, BriefWriteV3, writer_part, writer_schema_v3
from .handoff import parent_anchor
from .inputs import assert_packet, verify_evidence
from .validation import hash_brief
from .validation_v2 import (CHECKING_LANGUAGE, _collector, angle_and_cta_checks, before_publishing_checks,
                            email_dm_check, format_checks, ledger_checks, lint_fields, person_cta, public_copy_checks, refresh_change,
                            repairable, semantic_hash_v2)

SETTLED = ("bound", "supported")


def contract_for(version: str | None = None, writer: str | None = None) -> SimpleNamespace:
    """What differs between the contracts that share this ledger, repair and finalisation: v3 (E.B23) and v4 (E.B33). A v4
    run of writer v5.1 (NP.B10) repairs against v5.1's answer model and schema, so a repair keeps the three Reels; a
    person's edit at Gate 2 (`rebuild`) is not held to it, and the checks say so instead."""
    from .contracts_v4 import SCHEMA_V4
    if version == SCHEMA_V4:
        from . import validation_v4
        from .contracts_v4 import (BriefWriteV4, BriefWriteV51, BriefWriteV53, writer_part_v4, writer_schema_v4,
                                   writer_schema_v51, writer_schema_v53)
        from ..settings_store import PREMISE_WRITERS, THREE_REEL_WRITERS
        # Writer v5.3 (Round 2) repairs against its own answer model, so a repair keeps the central story and two premises.
        if writer in PREMISE_WRITERS:
            write, wire = BriefWriteV53, writer_schema_v53
        elif writer in THREE_REEL_WRITERS:
            write, wire = BriefWriteV51, writer_schema_v51
        else:
            write, wire = BriefWriteV4, writer_schema_v4
        return SimpleNamespace(schema=SCHEMA_V4, write=write, part=writer_part_v4, wire=wire, checks=validation_v4.checks_v4,
                               review_kind="ledger_v4", week=True)
    return SimpleNamespace(schema=SCHEMA_V3, write=BriefWriteV3, part=writer_part, wire=writer_schema_v3, checks=checks_v3,
                           review_kind="ledger_v3", week=False)


def copy_lint_v3(body) -> list[dict]:
    """E.B24's lint on a v3 brief's copy (the caption's and the email's body and a Reel's script are copy)."""
    return lint_fields(ledger_v3.copy_fields_v3(body))


def email_text(plan) -> str:
    e = plan.email
    return " ".join([*e.subject_options, e.preview, e.opening, e.body, e.ending]) if e else ""


def _snippet(text: str, n: int = 100) -> str:
    return text if len(text) <= n else text[:n - 3].rstrip() + "..."


def checks_v3(document: dict, dossier, provenance: dict, clearances=None, rules=None) -> list[dict]:
    findings = []
    add, block = _collector(findings)
    doc = BriefDocumentV3.model_validate(document)
    d = Dossier.model_validate(dossier) if isinstance(dossier, dict) else dossier
    body, header = doc.body, doc.header
    angle_and_cta_checks(add, block, body, header, d.angle)

    # The ledger: settled claims face v2's claim checks; the rest are findings of their own.
    copy = ledger_v3.copy_fields_v3(body, wide=True)
    narrative = "\n".join(text for _, _, text in copy)
    labels = {field: label for field, label, _ in copy}
    for claim in body.claims:
        label = labels.get(claim.field, claim.field)
        section = claim.field.split(".")[0]
        if claim.status not in SETTLED:
            # Its figures were checked by the rules (a figure the call lacks makes the line unsupported); the line is
            # reported once, below, not again as an unbound number.
            narrative = narrative.replace(claim.text, " ")
        if claim.status == "unsupported":
            block(f'{label[0].upper() + label[1:]} says "{_snippet(claim.text)}": {claim.note or "the call does not support it"}. '
                  "Remove it, or say only what the call supports", claim.claim_id, section=section)
        elif claim.status == "unchecked":
            add("warning", f'Check against the call: {label} says "{_snippet(claim.text)}" ({claim.note or "not checked"})',
                claim.claim_id, section=section)
        elif claim.status == "kept_by_person":
            add("warning", f'{label[0].upper() + label[1:]} keeps "{_snippet(claim.text)}", which the verifier found no '
                           "support for; a person kept it", claim.claim_id, section=section)
        if claim.flag and claim.status in SETTLED:
            if claim.flag.kind == "consent" and claim.flag.severity == "block":
                cited = [e for e in d.evidence if e.evidence_id in claim.evidence_ids]
                if not any(e.public_use and e.attribution_verified or (clearances or {}).get(e.evidence_id) for e in cited):
                    block(f'{claim.flag.message} ("{_snippet(claim.text, 80)}"); record the client\'s permission as a '
                          "clearance on its evidence", claim.claim_id, section="claims")
            else:
                add("warning", f'{claim.flag.message} ("{_snippet(claim.text, 80)}")', claim.claim_id, section=section)
    paraphrase_checks(block, copy, body.claims, d.evidence)
    settled = SimpleNamespace(evidence=body.evidence, claims=[c for c in body.claims if c.status in SETTLED])
    ledger_checks(add, block, settled, d, provenance, clearances, narrative)

    plan = body.format_plan
    format_checks(add, block, plan, set(header.channels))
    for i, reel in enumerate(plan.reels, 1):
        # The format guide: a scripted Reel is recorded from its script (section 1.9.8: the judge wanted the script). Missing
        # copy is the reviewer's to see, not an accuracy problem, so it warns and never sends the brief to repair.
        if reel.source == "new_script" and not (reel.script or "").strip():
            add("warning", f"Reel {i} is a new script without its script", section="format_plan")
    email = email_text(plan)
    email_dm_check(block, email)
    # The narrative checks read the copy, not the directions to the maker: a Reel's job ("about 125 to 140 words") is no
    # claim (E.B23: assets must not read as claims; 1.9.2).
    public_copy_checks(findings, body, header, d, provenance, clearances, rules, public="\n".join(text for _, _, text in copy),
                       copy=copy, lint=copy_lint_v3(body), email_text=email)
    before_publishing_checks(block, body)
    return findings


def paraphrase_checks(block, copy, claims, evidence) -> None:
    """R57: a paraphrase of a client's words, given at a gate, is never presented as their words. Words in quotation
    marks that come from a paraphrase and from no turn of the call block, for the repair or a person to fix."""
    from ..cycle.verification import _tokens, normalise, quotes_in
    paraphrases = [c for c in claims if c.attested and c.attested.kind == "paraphrase" and c.field == "context_items"]
    if not paraphrases:
        return
    turns = [normalise(e.excerpt) for e in evidence]
    for field, label, text in copy:
        for q in quotes_in(text):
            said, words = normalise(q), _tokens(q)
            if any(said in t for t in turns):
                continue
            source = next((p for p in paraphrases if said in normalise(p.text) or len(words) >= 2 and words <= _tokens(p.text)), None)
            if source:
                block(f'{label[0].upper() + label[1:]} puts "{_snippet(q, 80)}" in quotation marks, but it is a paraphrase of '
                      f"the client's words ({source.attested.by}, {source.attested.on}), not what the client said: drop the "
                      "quotation marks, or quote the call", source.claim_id, section=field.split(".")[0])


# The ledger -------------------------------------------------------------------------------------------------------

def beliefs_of(provenance: dict) -> dict | None:
    return provenance.get("beliefs") or None


def ledger_body(writer_body: dict, evidence: list[dict], provenance: dict, *, verify=None, previous: list[dict] | None = None,
                views=(), person_fields=frozenset(), attested=(), contract=None) -> tuple[dict, dict]:
    """The v3 body (the writer's sections plus the ledger) and the ledger's record. `verify(open_statements)` returns
    (output, refs, model) or raises; without it nothing new is sent to a model (a person's edit at Gate 2). `attested` are
    the brief's context items (5.B7): its attested facts and paraphrases settle the statements that say what they say and
    enter the ledger themselves, with the person and the date (R57). `contract` is contract_for's (v3 when absent)."""
    value = (contract or contract_for()).write.model_validate(writer_body).model_dump(mode="json")
    settled, open_ = ledger_v3.deterministic(value, evidence, beliefs_of(provenance), provenance.get("roster") or [], attested)
    carried, open_, kept_views = ledger_v3.carry(open_, previous or [], list(views), person_fields=set(person_fields), body=value)
    output, refs, model, status, error = None, {}, None, "nothing_to_check" if not open_ else "not_run", None
    if open_ and verify is not None:
        try:
            output, refs, model = verify(open_)
            status = "run"
        except ledger_v3.VerifierSkipped as skipped:
            status, error = "skipped", str(skipped)
    verified, new_views = ledger_v3.merge(open_, output, refs, set(provenance.get("knowledge_base_keys") or []), model)
    claims = settled + carried + verified
    order = {s["id"]: i for i, s in enumerate(ledger_v3.statements(value))}
    claims.sort(key=lambda c: order.get(c["claim_id"], len(order)))
    claims += ledger_v3.attested_entries(attested)
    body = {**value, "evidence": ledger_v3.evidence_refs(claims, evidence), "claims": claims}
    counted = ("bound", "supported", "unsupported", "unchecked", "kept_by_person") + (("attested",) if attested else ())
    record = {"version": ledger_v3.LEDGER_VERSION, "verifier": {"profile": ledger_v3.VERIFIER_PROFILE, "model": model,
                                                                 "status": status, **({"reason": error} if error else {})},
              "views": sorted(set(kept_views) | set(new_views)),
              "counts": {s: sum(c["status"] == s for c in claims) for s in counted}
              | {"sent_to_verifier": len(open_) if status == "run" else 0}}
    return body, record


def hedging_added(before: dict, after: dict) -> list[str]:
    """Checking language (E.B24's lint) in the repaired copy that the copy before the repair did not carry, as
    "label: phrase". A repair may remove or reword; it may never add a qualifier to the copy (E.B23)."""
    def phrases(body):
        return {(label, m.group(0).lower()) for _, label, text in ledger_v3.copy_fields_v3(body, wide=True)
                for m in CHECKING_LANGUAGE.finditer(text or "")}
    return [f"{label}: {phrase}" for label, phrase in sorted(phrases(after) - phrases(before))]


def header_for_v3(run, body: dict, provenance: dict, schema: str = SCHEMA_V3) -> dict:
    angle = run["input_refs"]["angle"]
    card = (angle.get("body") or {}).get("card") or {}
    cta = person_cta(angle) or {**body["cta"], "chosen_by": "writer"}
    return {"schema_version": schema, "angle_id": angle["angle_id"], "angle_hash": angle["approved_hash"],
            "purpose": card.get("pillar") or body["strategic_purpose"]["pillar"],
            "content_type": card.get("content_type") or body["strategic_purpose"]["content_type"],
            "audience": card.get("audience") or angle["body"]["audience"],
            "intended_shift": body["intended_shift"], "point_of_view": body["point_of_view"],
            "cta": cta, "channels": list(run["input_refs"].get("channels") or []), "pinned_inputs": provenance["pinned_inputs"]}


def evidence_view(d: Dossier) -> list[dict]:
    """The call's turns as the writer and the repair see them: who said it, when, and the words; no identifiers."""
    return [{"speaker": e.speaker, "start_ms": e.start_ms, "role": e.role, "excerpt": e.excerpt,
             "qualifications": e.qualifications} for e in d.evidence]


def repair_packet(document: dict, d: Dossier, findings: list[dict], channels, part=writer_part) -> dict:
    return {"brief": part(document["body"]), "evidence": evidence_view(d),
            "findings": [{"section": f.get("section"), "problem": f["message"]} for f in findings], "channels": channels}


def finalize_v3(worker, job, run, dossier, body, provenance, contract=None):
    """Build the v3 ledger, check the brief, repair once only for blocking findings, and save it for Gate 2. Contract v4
    (E.B33) is finalised here too, with its own body, schema and checks (`contract`, from contract_for)."""
    c = contract or contract_for()
    from ..cycle.verification import knowledge_root, load_rules, rules_for
    from .runtime import call, knowledge, verifier_for
    from . import paths
    d = Dossier.model_validate(dossier)
    rules = rules_for(knowledge(worker, run), worker.models.knowledge_base_root, "brief") or load_rules(knowledge_root(), stage="brief")
    # A revision keeps every line a person edited (5.F5): the locks are paths, so the rest of a section is rewritten.
    parent, keep, restored = None, [], []
    if run["input_refs"].get("revision_of"):
        from .gate_two import get
        parent = get(worker.repo, run["input_refs"]["revision_of"])
        keep = paths.revision_locks(run, parent)
    # The context and attested facts given at the gates, frozen with the run (5.B7).
    context = run["input_refs"].get("context_items") or []
    evidence = [e.model_dump(mode="json") for e in d.evidence]
    channels = run["input_refs"].get("channels") or []
    verify = verifier_for(worker, job, run, evidence, provenance)
    # Contract v4's week checks read the cycle's other current briefs (E.B24: one offer CTA a week, covers distinct).
    week = {}
    if c.week:
        from .asset_checks import week_siblings
        with worker.repo.connection() as conn:
            week = {"siblings": week_siblings(conn, {"week_id": d.angle["week_id"], "angle_id": d.angle["angle_id"]})}

    def assemble(value, previous=None, views=(), stage="writer"):
        value = c.write.model_validate(value).model_dump(mode="json")
        if keep:
            # A draft that changed a locked line gets the person's line back, recorded; one with no place for it is refused.
            value, back = paths.restore(c.part(parent["content_body"]["document"]["body"]), value, keep)
            restored.extend({**r, "stage": stage} for r in back)
            value = c.write.model_validate(value).model_dump(mode="json")
        if (cta := person_cta(d.angle)) is not None:
            value = {**value, "cta": {**value["cta"], **cta}}
        full, record = ledger_body(value, evidence, provenance, verify=verify, previous=previous, views=views, attested=context,
                                   contract=c)
        document = {"header": header_for_v3(run, value, provenance, c.schema), "body": full}
        return document, c.checks(document, d, provenance, None, rules, **week), record

    document, findings, record = assemble(body)
    repair = {"used": False}
    if blocking := repairable(findings):
        fixed = call(worker, job, run, "brief_repair", c.write, repair_packet(document, d, blocking, channels, c.part),
                     c.wire(channels)).model_dump(mode="json")
        added = hedging_added(c.part(document["body"]), fixed)
        repair = {"used": True, "findings": [f["message"] for f in blocking], "accepted": not added}
        if added:
            # The repair added a qualifier to the copy: the writer's copy stands, with its findings, for Gate 2.
            repair["rejected_because"] = "The repair added checking language to the copy: " + "; ".join(added)
        else:
            # Unchanged statements keep their verdicts; only new ones go to the verifier again.
            document, findings, again = assemble(fixed, document["body"]["claims"], record["views"], stage="repair")
            record = {**again, "verifier": {**record["verifier"], "after_repair": again["verifier"]}}
    envelope = {"schema_version": c.schema, "document": document,
                "review": {"locked_fields": keep,
                           **({"locks_restored": restored} if parent else {}),
                           "findings": findings, "support_reviewed_document_hash": semantic_hash_v2(document),
                           "history_acknowledged": False, "clearances": {}, "repair_used": repair["used"], "repair": repair,
                           "ledger": record, "review_kind": c.review_kind,
                           # A person's anchor choice carries into a revision; the hand-off view ignores it if its piece left the plan.
                           **parent_anchor(parent)},
                "provenance": {"brand_hash": ((provenance.get("pinned_inputs") or {}).get("knowledge_base") or {}).get("sha256"),
                               "dossier_hash": canonical_hash(d.model_dump(mode="json")),
                               "run_id": run["run_id"], "angle": d.angle, **provenance},
                **({"context_items": context} if context else {}),
                **({"change": refresh_change(run)} if parent else {})}
    row = {"brief_id": "brief_" + canonical_hash([run["run_id"], document])[:24], "week_id": d.angle["week_id"],
           "angle_id": d.angle["angle_id"], "angle_input_hash": d.angle["approved_hash"], "content_body": envelope,
           "selected_evidence": evidence,
           "prior_content_context": [p.model_dump(mode="json") for p in d.prior],
           "research_gaps": {"items": d.gaps, "coverage": d.coverage}, "supersedes_id": run["input_refs"].get("revision_of")}
    row["content_hash"] = hash_brief(row)
    with worker.repo.connection() as conn:
        assert_packet(conn, d.angle)
        verify_evidence(conn, d.evidence)
        from ..retrieval import check_prior
        check_prior(conn, d.prior)
        if parent:
            from .gate_two import locked
            locked(conn, parent["brief_id"], parent["content_hash"])
        old = conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s", (row["brief_id"],)).fetchone()
        if old and old["content_hash"] != row["content_hash"]:
            raise ValueError("Saved brief identity differs from recovered output")
        insert(conn, "content_briefs", row, conflict=True)
        worker.repo.finish(conn, job, {"brief_id": row["brief_id"], "content_hash": row["content_hash"], "schema_version": c.schema,
                                       "blocking": sum(f["severity"] == "blocking" for f in findings), "repair_used": repair["used"],
                                       "repair_accepted": repair.get("accepted"), "finished_at": datetime.now(UTC).isoformat()},
                           message="Brief ready for Gate 2")


def rebuild(row: dict, changes: dict, person_fields=None) -> dict:
    """A person's edit at Gate 2: the writer's sections with the changed sections, and the ledger rebuilt without a model.
    Unchanged statements keep their verdicts; new ones the rules cannot bind stay for a person to check. `person_fields`
    are the paths the person changed (the changed sections when not given); the brief's attested facts settle again."""
    body = row["content_body"]["document"]["body"]
    review = row["content_body"]["review"]
    c = contract_for(row["content_body"].get("schema_version"))
    if c.schema == "brief_document_v4":
        # A person's edit keeps the brief's own plan shape (writer v5.3's premises included); Round 2.
        from .contracts_v4 import BriefEditV4
        c = SimpleNamespace(**{**vars(c), "write": BriefEditV4})
    writer = c.write.model_validate({**c.part(body), **changes}).model_dump(mode="json")
    full, record = ledger_body(writer, row["selected_evidence"], row["content_body"]["provenance"], previous=body["claims"],
                               views=(review.get("ledger") or {}).get("views") or [],
                               person_fields=set(changes if person_fields is None else person_fields),
                               attested=row["content_body"].get("context_items") or [], contract=c)
    review["ledger"] = {**record, "verifier": {**((review.get("ledger") or {}).get("verifier") or {}), "rebuilt_after_edit": True}}
    return full
