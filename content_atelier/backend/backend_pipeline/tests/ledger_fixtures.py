"""Synthetic documents, moments and an offline embedding provider for the Phase 2 search tests.

Nothing here is real client material. The embedder places a text in a space of a few concept axes (follow-up speed, pricing,
the booking calendar, praise, onboarding) plus a small hash-derived offset, so a paraphrase is nearer to its moment than a
distractor is, deterministically and with no model. It also answers the topic picker the way a sensible model would: it follows the
candidates it is offered, and proposes a topic only when none of them names the scene's subject.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from psycopg.types.json import Jsonb

from backend_pipeline.tests.platform_db import empty, platform_setup, platform_url  # noqa: F401 (fixtures)

MODEL = "openai/text-embedding-3-small"
# axis -> (words, topic name, topic description)
CONCEPTS = {
    "followup": ({"follow", "followup", "reply", "replies", "respond", "response", "inquiry", "inquiries", "lead", "leads", "minutes"},
                 "Inquiry follow-up speed", "How quickly the team replies to new inquiries"),
    "pricing": ({"price", "prices", "pricing", "cost", "expensive", "afford", "investment"},
                "Pricing objections", "Couples and clients pushing back on what the package costs"),
    "calendar": ({"calendar", "booking", "bookings", "schedule", "tour", "tours", "appointment"},
                 "Booking calendar", "Setting up tours and consultations on a booking calendar"),
    "praise": ({"love", "amazing", "grateful", "thrilled", "fantastic"}, "Client praise", "Clients saying what working with WIA was like"),
    "onboarding": ({"onboarding", "kickoff", "welcome", "setup", "intake"}, "Client onboarding", "The first weeks after a client signs"),
}
AXES = list(CONCEPTS)


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def concept_of(text: str) -> str | None:
    found = {axis: len(words(text) & vocab) for axis, (vocab, _, _) in CONCEPTS.items()}
    best = max(found, key=lambda a: (found[a], -AXES.index(a)))
    return best if found[best] else None


def vector_for(text: str, dimensions: int = 1536) -> list[float]:
    vector = [0.0] * dimensions
    for axis, (vocab, _, _) in CONCEPTS.items():
        vector[AXES.index(axis)] = float(len(words(text) & vocab))
    digest = hashlib.sha256(text.encode()).digest()
    for i in range(16):  # a small offset only the exact text shares: no two texts are identical vectors
        vector[100 + i] = (digest[i] / 255.0 - 0.5) * 0.06
    vector[500] = 0.05  # never the zero vector
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector]


class Embedder:
    """An offline provider: embeddings by concept axes, and a topic picker that follows its candidates."""
    records_runs = False

    def __init__(self, model: str = MODEL, *, fail_embeddings: bool = False):
        self.model = model
        self.fail_embeddings = fail_embeddings
        self.embedded: list[str] = []        # every text embedded, in order
        self.batches: list[int] = []         # the size of every embed_many request
        self.json_calls: list[dict] = []     # every topic-picker call: the candidates it was offered
        self.propose_blocked: str | None = None  # a topic name to propose even when it is blocked (a misbehaving model)
        self.input_set_hash = None
        self.answers: list[dict] = []        # scripted answers for the topic picker, used first

    def embed(self, *, text, fingerprint):
        if self.fail_embeddings:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings")
        self.embedded.append(text)
        return vector_for(text), {"fingerprint": fingerprint, "fake": True}

    def embed_many(self, *, texts, fingerprint):
        if self.fail_embeddings:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings")
        self.embedded.extend(texts)
        self.batches.append(len(texts))
        return {"model": self.model, "data": [{"index": i, "embedding": vector_for(t)} for i, t in enumerate(texts)],
                "usage": {"prompt_tokens": sum(len(t) // 4 for t in texts), "total_tokens": sum(len(t) // 4 for t in texts)}}

    def json_call(self, *, stage, system, user, schema, fingerprint):
        assert stage == "topic_assignment"
        # A repair call sends the same material, then a correction note: the scene and candidates are the part before it.
        offered = json.loads(user.split("\n\n## Correction needed", 1)[0])
        self.json_calls.append(offered)
        if self.answers:
            return self.answers.pop(0), {"fingerprint": fingerprint, "fake": True}
        scene = " ".join(str(v or "") for v in offered["scene"].values())
        concept = concept_of(scene)
        for candidate in offered["candidates"]:
            if concept and concept_of(candidate["name"] + " " + (candidate["description"] or "")) == concept:
                return {"topic_ids": [candidate["topic_id"]], "new_topic": None}, {"fingerprint": fingerprint, "fake": True}
        if self.propose_blocked:
            return {"topic_ids": [], "new_topic": {"name": self.propose_blocked, "description": "A subject a person ruled out"}}, \
                {"fingerprint": fingerprint, "fake": True}
        _, name, description = CONCEPTS[concept or "followup"]
        return {"topic_ids": [], "new_topic": {"name": name, "description": description}}, {"fingerprint": fingerprint, "fake": True}


# ---- documents and moments ------------------------------------------------------------------------------------------------------


def make_client(conn, client_id: str, name: str, consent: str = "anonymise_only") -> None:
    conn.execute("INSERT INTO clients (client_id, name, consent) VALUES (%s,%s,%s)", (client_id, name, consent))


def make_person(conn, person_id: str, name: str, role: str, client_id: str | None = None) -> None:
    conn.execute("INSERT INTO people (person_id, name, role, client_id, source) VALUES (%s,%s,%s,%s,'manual')",
                 (person_id, name, role, client_id))


def make_document(conn, transcript_id: str, title: str, turns: list[tuple[str, str]], *, source_type: str = "fathom",
                  call_type: str = "client_1to1", client_id: str | None = None, occurred_at: datetime | None = None,
                  roles: dict[str, tuple[str, str | None]] | None = None, timed: bool = True, source_url: str | None = None,
                  source_metadata: dict | None = None, included: bool = True, canonical: str | None = None) -> dict:
    """A document of `turns` [(speaker, text)]; `roles` maps a speaker to (role, person_id). Returns the passage map."""
    parts, passages, cursor = [], [], 0
    for i, (speaker, text) in enumerate(turns):
        body = f"{speaker}: {text}"
        passages.append({"passage_id": f"{transcript_id}:span:{i}", "ordinal": i, "start": cursor, "end": cursor + len(body),
                         "kind": "timestamped" if timed else "message", "start_ms": i * 20_000 if timed else None,
                         "end_ms": i * 20_000 + 15_000 if timed else None, "speaker": speaker})
        parts.append(body)
        cursor += len(body) + 1
    original = "\n".join(parts)
    speaker_map = {s: {"person_id": (roles or {}).get(s, ("unknown", None))[1], "role": (roles or {}).get(s, ("unknown", None))[0],
                       "basis": "name", "inferred": False} for s, _ in turns}
    conn.execute("""INSERT INTO transcripts (transcript_id, week_id, source_type, upstream_id, title, source_url, occurred_at, original_text,
        passage_map, content_hash, source_metadata, use_restrictions, processing_status, occurred_at_source, call_type, included,
        exclusion_reason, client_id, participants, speaker_map, canonical_document_id, extraction_status, normalised_at)
        VALUES (%s,NULL,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending','provider',%s,%s,%s,%s,'[]'::jsonb,%s,%s,'completed',now())""",
                 (transcript_id, source_type, f"{source_type}:{transcript_id}", title, source_url, occurred_at, original,
                  Jsonb(passages), hashlib.sha256(original.encode()).hexdigest(),
                  Jsonb({"normalized_sha256": hashlib.sha256(original.encode()).hexdigest(), **(source_metadata or {})}),
                  Jsonb({"research_allowed": True, "public_use": False}), call_type, included,
                  None if included else "Test exclusion", client_id, Jsonb(speaker_map), canonical))
    return {"transcript_id": transcript_id, "passages": passages, "text": original}


def make_moment(conn, moment_id: str, document: dict, anchor: int, quote: str, *, record: str = "WIA asked how quickly leads get a reply",
                setup: str = "The client described how inquiries are handled", moment_type: str = "observation",
                speaker: tuple[str, str, str | None] | None = None, client_id: str | None = None, consent: str = "anonymise",
                verified: bool = True, current: bool = True, occurred_at: datetime | None = None, extractor: str = "2026-10-19.scenes.v2",
                context: int = 1, checks: dict | None = None, sensitivity: str = "public_candidate",
                evidence_kind: str = "direct_quote", unverified_reason: str = "The quote does not bind to its source") -> None:
    """A moment anchored on passage `anchor`, with `context` passages either side as context references."""
    passages = document["passages"]
    refs = []
    for p in passages[max(0, anchor - context):anchor + context + 1]:
        refs.append({"transcript_id": document["transcript_id"], "passage_id": p["passage_id"], "start": p["start"], "end": p["end"],
                     "roles": ["anchor", "context"] if p["ordinal"] == anchor else ["context"]})
    body = {"quote": quote, "context_summary": setup, "moment_type": moment_type, "proposition": record, "audience_relevance": "n/a",
            "qualifications": ["Said in a call"], "claim_status": "stated", "sensitivity": sensitivity, "strength": 0.0, "reasons": []}
    label, role, person_id = speaker or (passages[anchor]["speaker"], "client", None)
    conn.execute("""INSERT INTO key_moments (moment_id, week_id, run_id, moment_body, evidence_refs, document_id, moment_type, speaker_label,
        speaker_id, speaker_role, evidence_kind, client_id, consent_status, quote_verified, sensitivity, occurred_at, extractor_version,
        checks, is_current, unverified_reason)
        VALUES (%s,NULL,NULL,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                 (moment_id, Jsonb(body), Jsonb(refs if verified else []), document["transcript_id"], moment_type, label, person_id,
                  role, evidence_kind, client_id, consent, verified, sensitivity, occurred_at, extractor, Jsonb(checks or {}), current,
                  None if verified else unverified_reason))


def load_document(conn, transcript_id: str) -> dict:
    row = conn.execute("SELECT original_text, passage_map FROM transcripts WHERE transcript_id=%s", (transcript_id,)).fetchone()
    return {"transcript_id": transcript_id, "passages": row["passage_map"], "text": row["original_text"]}


def make_chunk(conn, document: dict, chunk_id: str, first: int, last: int, *, overlap_first: bool = False, embed: bool = True,
               model: str = MODEL) -> str:
    """A current v2 chunk over passages first..last of a document, with a header and (optionally) a vector."""
    members = document["passages"][first:last + 1]
    refs = [{"passage_id": p["passage_id"], "start": p["start"], "end": p["end"]} for p in members]
    if overlap_first:
        refs[0]["overlap"] = True
    row = conn.execute("SELECT title, occurred_at, speaker_map FROM transcripts WHERE transcript_id=%s", (document["transcript_id"],)).fetchone()
    body = "\n".join(document["text"][p["start"]:p["end"]] for p in members)
    header = f"Call: {row['title']}\nDate: unknown\nType: Call"
    text = header + "\n\n" + body
    speakers = [{"name": s, "role": row["speaker_map"][s]["role"], "inferred": False} for s in dict.fromkeys(p["speaker"] for p in members)]
    conn.execute("""INSERT INTO transcript_chunks (chunk_id, transcript_id, chunk_text, passage_refs, content_hash, embedding, header,
        occurred_at, speaker_roles, embedding_model, segmentation_version, is_current) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'v2',true)""",
                 (chunk_id, document["transcript_id"], text, Jsonb(refs), hashlib.sha256(text.encode()).hexdigest(),
                  np.asarray(vector_for(text), dtype=np.float32) if embed else None, header, row["occurred_at"], Jsonb(speakers),
                  model if embed else None))
    return chunk_id


NOW = datetime.now(UTC).replace(microsecond=0)


KINDS = ("'angle', 'considered_idea', 'brief', 'brand_kit_item', 'brand_kit_version', 'brand_kit_source', 'published_content', 'run_plan', 'seed'")


def set_decision_kinds(url, kinds):
    from backend_pipeline.database import connect
    with connect(url, vectors=False) as conn:
        if "'topic'" not in kinds:
            conn.execute("DELETE FROM decisions WHERE item_kind = 'topic'")
        conn.execute("ALTER TABLE decisions DROP CONSTRAINT decisions_item_kind_check")
        conn.execute(f"ALTER TABLE decisions ADD CONSTRAINT decisions_item_kind_check CHECK (item_kind IN ({kinds}))")


@pytest.fixture
def ledger(platform_setup, platform_url):  # noqa: F811
    """Three clients, four documents and a dozen moments (verified, unverified, superseded, do_not_use), none embedded yet."""
    repo, models, tmp_path = platform_setup
    empty(platform_url)  # the two synthetic weeks platform_setup admits are not part of this archive
    # The schema gap (Phase-2-Search-Notes.md): migration 008 leaves decisions.item_kind without 'topic', which the topic registry's
    # audit rows need. Until the integrator's migration adds it, the tests widen the constraint for their own duration and restore it.
    set_decision_kinds(platform_url, KINDS + ", 'topic'")
    with repo.connection() as conn:
        make_client(conn, "client_acme", "Acme Weddings", "may_name")
        make_client(conn, "client_beta", "Beta Bridal", "anonymise_only")
        make_client(conn, "client_gamma", "Gamma Events", "no_use")
        make_person(conn, "person_whit", "Whitney Hodges", "staff")
        make_person(conn, "person_dana", "Dana Lee", "client", "client_acme")
        roles = {"Whitney Hodges": ("staff", "person_whit"), "Dana Lee": ("client", "person_dana"),
                 "Bea Park": ("client", None), "Gus Ray": ("client", None)}
        d1 = make_document(conn, "doc_acme_1", "Acme check-in", [
            ("Whitney Hodges", "How quickly do you reply when a new lead comes in?"),
            ("Dana Lee", "We reply to every inquiry within five minutes and our bookings doubled."),
            ("Whitney Hodges", "That speed is the whole game."),
            ("Dana Lee", "Honestly the price felt expensive until we saw the booking numbers."),
            ("Whitney Hodges", "Let us look at the calendar next.")],
            client_id="client_acme", occurred_at=NOW - timedelta(days=10), roles=roles,
            source_url="https://fathom.video/share/acme-1")
        d2 = make_document(conn, "doc_beta_1", "Beta office hours", [
            ("Whitney Hodges", "Where do prospects drop off?"),
            ("Bea Park", "Our pricing page scares people because the cost is hidden."),
            ("Whitney Hodges", "Show the investment earlier."),
            ("Bea Park", "I love how amazing the new tour calendar feels.")],
            call_type="office_hours", client_id="client_beta", occurred_at=NOW - timedelta(days=40), roles=roles, source_type="zoom")
        d3 = make_document(conn, "doc_gamma_1", "Gamma call", [
            ("Whitney Hodges", "How is onboarding going?"),
            ("Gus Ray", "The onboarding kickoff went fine and we are grateful.")],
            client_id="client_gamma", occurred_at=NOW - timedelta(days=5), roles=roles)
        d4 = make_document(conn, "doc_slack_1", "Slack thread", [
            ("Dana Lee", "Anyone else answering leads in minutes?"), ("Whitney Hodges", "Yes, reply fast.")],
            source_type="slack", call_type="slack_thread", client_id="client_acme", occurred_at=NOW - timedelta(days=2), roles=roles,
            timed=False, source_metadata={"slack": {"workspace": "T03P5A3L1DK", "channel": "C082DURRJ2U", "thread_ts": "1760000000.000100"}})
        make_moment(conn, "m_reply", d1, 1, "We reply to every inquiry within five minutes and our bookings doubled.",
                    record="Dana described replying to every inquiry in five minutes and bookings doubling",
                    moment_type="result", client_id="client_acme", consent="cleared", occurred_at=NOW - timedelta(days=10),
                    speaker=("Dana Lee", "client", "person_dana"))
        make_moment(conn, "m_price", d1, 3, "Honestly the price felt expensive until we saw the booking numbers.",
                    record="Dana said the cost felt high until results arrived", moment_type="objection", client_id="client_acme",
                    consent="anonymise", occurred_at=NOW - timedelta(days=10), speaker=("Dana Lee", "client", "person_dana"))
        make_moment(conn, "m_pricing_beta", d2, 1, "Our pricing page scares people because the cost is hidden.",
                    record="Bea named the hidden cost as the reason prospects leave", moment_type="tension", client_id="client_beta",
                    consent="anonymise", occurred_at=NOW - timedelta(days=40), speaker=("Bea Park", "client", None))
        make_moment(conn, "m_praise_beta", d2, 3, "I love how amazing the new tour calendar feels.", record="Bea praised the tour calendar",
                    moment_type="testimonial", client_id="client_beta", consent="anonymise", occurred_at=NOW - timedelta(days=40),
                    speaker=("Bea Park", "client", None))
        make_moment(conn, "m_gamma", d3, 1, "The onboarding kickoff went fine and we are grateful.", record="Gus thanked the team for onboarding",
                    moment_type="testimonial", client_id="client_gamma", consent="do_not_use", occurred_at=NOW - timedelta(days=5),
                    speaker=("Gus Ray", "client", None))
        make_moment(conn, "m_staff", d1, 2, "That speed is the whole game.", record="WIA stressed that speed matters",
                    moment_type="teaching", client_id="client_acme", consent="internal_only", occurred_at=NOW - timedelta(days=10),
                    speaker=("Whitney Hodges", "staff", "person_whit"), evidence_kind="team_report")
        make_moment(conn, "m_unverified", d1, 1, "We answer every lead in minutes and bookings tripled.", verified=False,
                    record="Unbindable draft about replies", moment_type="result", client_id="client_acme", consent="anonymise",
                    occurred_at=NOW - timedelta(days=10), speaker=("Dana Lee", "client", "person_dana"))
        make_moment(conn, "m_old", d1, 1, "We reply to every inquiry within five minutes and our bookings doubled.",
                    record="An older extraction of the reply scene", moment_type="result", client_id="client_acme", consent="cleared",
                    current=False, extractor="2026-10-13.weekly.v3", occurred_at=NOW - timedelta(days=10),
                    speaker=("Dana Lee", "client", "person_dana"))
        make_moment(conn, "m_slack", d4, 1, "Yes, reply fast.", record="Whitney said to reply fast to leads", moment_type="soundbite",
                    client_id="client_acme", consent="anonymise", occurred_at=NOW - timedelta(days=2),
                    speaker=("Whitney Hodges", "staff", "person_whit"))
    yield repo, models, tmp_path, Embedder()
    set_decision_kinds(platform_url, KINDS)


def embed_everything(repo, models, embedder) -> dict:
    """Queue and run the embedding job for every pending moment on the synthetic database, with the offline embedder."""
    from backend_pipeline.moments import embedding
    from backend_pipeline.sql_pipeline import SQLWorker
    queued = embedding.queue(repo, models, mode="cached")
    if queued["queued"]:
        worker = SQLWorker(repo.settings, models, provider=embedder)
        assert worker.once(), "the embedding job was picked up"
    return queued
