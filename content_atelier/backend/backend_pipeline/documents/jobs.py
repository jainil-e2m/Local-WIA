"""The `document_normalise` stage (plan 1.B4, 1.B5, 1.B6, 1.B10, 1.B11, 1.B12 on one document).

In order: resolve speakers to people, classify the call and decide its inclusion, find the client, date it from evidence,
store all of that beside the immutable text and passage map, segment it (version 2, with a header and roles) with a glossary
search copy, and link it to its canonical copy if it is a duplicate. Idempotent: running it again on an unchanged document
and unchanged reference data changes nothing. A person's decision about a call's type is never overwritten.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime

from psycopg.types.json import Jsonb

from ..normalise import NORMALISER_VERSION, classify, dates, segment, speakers
from ..normalise.glossary import Glossary
from ..settings_store import value as setting
from . import duplicates

DOCUMENT_STAGES = frozenset({"document_normalise"})


def _words(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split())


def detect_client(document: dict, mapping: dict, clients: list[dict], people: dict[str, dict]) -> str | None:
    """The one client this call is with: a person tied to a client who spoke, else a client named by a speaker label or the
    title. None when no client matches or several do (never guessed)."""
    found: set[str] = set()
    for label, assigned in mapping.items():
        person = people.get(assigned.get("person_id") or "")
        if person and person.get("client_id"):
            found.add(person["client_id"])
    names = {c["client_id"]: {_words(c["name"]), *(_words(a) for a in c.get("aliases") or [])} - {""} for c in clients}
    title = f" {_words(document.get('title') or '')} "
    labels = {_words(label) for label in mapping if label}
    for client_id, spellings in names.items():
        if any(f" {s} " in title for s in spellings) or labels & spellings:
            found.add(client_id)
    return found.pop() if len(found) == 1 else None


def load(conn, transcript_id: str) -> dict:
    row = conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (transcript_id,)).fetchone()
    if row is None:
        raise LookupError("Document not found")
    return row


def resegment(conn, transcript_id: str, *, glossary: Glossary | None = None, max_characters: int | None = None,
              gap_seconds: int | None = None) -> dict:
    """Make an included document's current chunks (segmentation v2) agree with what is stored about it: its call type,
    client, speaker map and date. The normalise stage ends with it, and `documents dates --apply` runs it so a newly dated
    document's headers name the date before anything is embedded. No classification and no model call; idempotent."""
    document = load(conn, transcript_id)
    if not document["included"]:
        return {"added": 0, "retired": 0, "current": 0}
    glossary = glossary or Glossary.from_database(conn)
    max_characters = max_characters or setting("documents.segmentation.max_characters", conn)
    gap_seconds = gap_seconds or setting("documents.segmentation.gap_seconds", conn)
    client = conn.execute("SELECT name FROM clients WHERE client_id=%s", (document["client_id"],)).fetchone() if document["client_id"] else None
    chunks = segment.chunk_document(document, {"call_type": document["call_type"], "client_name": client["name"] if client else None},
                                    document["speaker_map"] or {}, max_characters=max_characters, gap_ms=gap_seconds * 1000)
    return segment.retire_and_store(conn, document, chunks, search_text=glossary.normalise)


# What one classification call costs in tokens beyond its request text: the answer (type, one sentence, confidence) and the
# schema's overhead. Characters per token as in the re-embedding estimate.
CLASSIFICATION_OUTPUT_TOKENS = 120
CHARACTERS_PER_TOKEN = 4


def classification_estimate(repo, transcript_ids: list[str], models=None) -> dict:
    """Before normalising: how many of these documents the rules cannot place and the model would be asked about, and the
    tokens that takes. Offline (no call); a person's decision and a kept model placement cost nothing (plan E.B1: the
    estimate comes first, the run plan names the stage and model, and without one these calls wait for a person)."""
    model = getattr(models, "openrouter_document_classification_model", None) if models is not None else None
    calls, characters = [], 0
    with repo.connection() as conn:
        resolver = speakers.Resolver.from_database(conn, setting("documents.staff_email_domains", conn))
        fragment_words = setting("documents.fragment_words", conn)
        for transcript_id in transcript_ids:
            document = load(conn, transcript_id)
            prior = document["classification"] or {}
            if prior.get("method") == "person":
                continue
            mapping = speakers.speaker_map(document, resolver, None)
            if not classify.by_rules(document, speakers.externals(mapping), fragment_words=fragment_words).needs_review:
                continue
            if classify.reusable(prior, document, mapping, model) is not None:
                continue
            calls.append(transcript_id)
            characters += len(classify.MODEL_SYSTEM) + len(classify.model_request(document, mapping))
    return {"documents": len(transcript_ids), "model": model, "stage": "document_classification", "model_calls": len(calls),
            "estimated_input_tokens": characters // CHARACTERS_PER_TOKEN,
            "estimated_output_tokens": len(calls) * CLASSIFICATION_OUTPUT_TOKENS, "documents_to_ask_about": calls,
            "note": "No model is configured (models.document_classification): these documents are marked for a person." if not model
            else "Each call needs an active run plan covering this stage and model; without one the document is marked for a person."}


def normalise(repo, transcript_id: str, *, models=None, provider=None, runs=None, job=None, events=(), today=None) -> dict:
    """Run the whole stage on one document and return what was decided."""
    with repo.connection() as conn:
        document = load(conn, transcript_id)
        domains = setting("documents.staff_email_domains", conn)
        included_types = setting("documents.included_call_types", conn)
        fragment_words = setting("documents.fragment_words", conn)
        max_characters = setting("documents.segmentation.max_characters", conn)
        gap_seconds = setting("documents.segmentation.gap_seconds", conn)
        resolver = speakers.Resolver.from_database(conn, domains)
        people = {p["person_id"]: p for p in conn.execute("SELECT person_id,client_id FROM people").fetchall()}
        clients = conn.execute("SELECT client_id,name,aliases FROM clients").fetchall()
        glossary = Glossary.from_database(conn)
        triage = {"min_words": setting("documents.slack_triage.min_words", conn), "bot_names": setting("documents.slack_triage.bot_names", conn),
                  "excluded_channels": setting("documents.slack_export.excluded_channels", conn),
                  "closed_channel_ids": [r["channel_id"] for r in conn.execute("SELECT channel_id FROM slack_channels WHERE NOT included")]}
    prior = (document["classification"] or {}) if document["classification"] else {}
    by_person = prior.get("method") == "person"
    first_pass = speakers.speaker_map(document, resolver, None)
    if by_person:
        decision = classify.Decision(document["call_type"], "person", prior.get("reason") or "Decided by a person.",
                                     rule_version=prior.get("rule_version", classify.RULES_VERSION))
    else:
        model = getattr(models, "openrouter_document_classification_model", None) if models is not None else None
        decision = classify.classify(document, first_pass, provider=provider, model=model, runs=runs, fragment_words=fragment_words,
                                     prior=prior)
    mapping = speakers.speaker_map(document, resolver, decision.call_type)
    if by_person:
        included, reason = document["included"], document["exclusion_reason"]
    else:
        included, reason = classify.inclusion(decision.call_type, tuple(included_types))
    triaged = None
    if included and not by_person and decision.call_type == "slack_thread":
        # Slack triage (2.B9): an acknowledgement, a join message or a bot's post is not worth a model call. A person's decision
        # (above) is never triaged, so a person can include a thread the rules would drop.
        triaged = classify.triage_slack(document, **triage)
        if triaged:
            included, reason = False, triaged.reason
    client_id = detect_client(document, mapping, clients, people) if decision.call_type in speakers.CLIENT_CALLS | {"prospect"} else None
    when = dates.resolve(document, list(events), today=today, names=(document["source_metadata"].get("filename") or "",))
    if document["occurred_at_source"] in {"manual"}:
        when = dates.Result(document["occurred_at"], "manual", "recorded by a person")
    participants = speakers.participants(document, mapping)
    with repo.connection() as conn:
        if job is not None:
            repo.guard(conn, job)
        current = load(conn, transcript_id)
        if current["original_text"] != document["original_text"] or current["passage_map"] != document["passage_map"]:
            raise ValueError("The document changed while it was being normalised")
        kept = decision.method == "model" and prior.get("request_hash") == decision.request_hash and prior.get("decided_at")
        record = {**decision.record(), "decided_at": prior["decided_at"] if kept else datetime.now(UTC).isoformat()} \
            if not by_person else prior
        if decision.needs_review and not by_person:
            record["needs_review"] = True
        if triaged:
            record["triage"] = triaged.record()
        if prior.get("unlinked_by"):
            record["unlinked_by"] = prior["unlinked_by"]  # a person said this is not a copy; that stands
        if client_id is None and included and decision.call_type in speakers.CLIENT_CALLS | {"prospect"}:
            # A new client or prospect: the account the title names, added by the system for a person to check (identities.py).
            from ..identities import provisional_account
            client_id = provisional_account(conn, document, mapping, decision.call_type)
        conn.execute("""UPDATE transcripts SET call_type=%s,included=%s,exclusion_reason=%s,classification=%s,client_id=%s,
            participants=%s,speaker_map=%s,normaliser_version=%s,normalised_at=now(),
            extraction_status=CASE WHEN %s THEN CASE WHEN extraction_status='not_applicable' THEN 'pending' ELSE extraction_status END
                              ELSE 'not_applicable' END WHERE transcript_id=%s""",
                     (decision.call_type, included, reason, Jsonb(record), client_id, Jsonb(participants), Jsonb(mapping),
                      NORMALISER_VERSION, included, transcript_id))
        dates.apply(conn, transcript_id, when)
        from ..moments import store as ledger
        if ledger.has_ledger(conn):
            # An excluded document feeds nothing: its moments stay readable for what cites them, but are not current (2.B9, 2.B11).
            ledger.align_currency(conn, transcript_id, included)
            # The client, the speakers' roles and so the consent may have changed: re-derive the stored moments now (2.B4).
            from ..moments.recheck import recheck_in
            recheck_in(conn, document_ids=[transcript_id])
        stored = resegment(conn, transcript_id, glossary=glossary, max_characters=max_characters, gap_seconds=gap_seconds)
        linked = duplicates.link(conn, transcript_id)
    return {"transcript_id": transcript_id, "call_type": decision.call_type, "method": decision.method if not by_person else "person",
            "included": included, "exclusion_reason": reason, "needs_review": bool(record.get("needs_review")),
            "client_id": client_id, "participants": len(participants), "dated": when.source,
            "chunks": stored, "duplicate_of": linked}


def classification_provider(models, storage, provider=None):
    """The provider that places a call the rules cannot: the one given, else a live one when a classification model is
    configured and the store is not synthetic, else none (rules only; the call waits for a person). The queued job and
    `documents normalise --now` use the same one."""
    if provider is None and getattr(models, "openrouter_document_classification_model", None) and not storage.synthetic:
        from ..llm import live_provider
        provider = live_provider(models, storage=storage)
    return provider


def execute(worker, job) -> None:
    """The queue worker's handler: normalise the job's document and finish the job."""
    transcript_id = job["transcript_id"]
    if not transcript_id:
        raise ValueError("A document_normalise job names its document")
    result = normalise(worker.repo, transcript_id, models=worker.models,
                       provider=classification_provider(worker.models, worker.storage, worker.provider), job=job)
    with worker.repo.connection() as conn:
        worker.repo.finish(conn, job, result, message=f"{result['call_type']}: " + (
            "included" if result["included"] else "excluded") + (", needs a person" if result["needs_review"] else ""))
