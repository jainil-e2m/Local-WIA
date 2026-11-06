"""Synthetic documents, a scripted offline provider and helpers for the moments ledger suites (Phase 2).

No real client text and no network: the documents are invented, the provider answers from a script, and the conftest forbids
outbound HTTP.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from backend_pipeline import reference
from backend_pipeline.documents import intake
from backend_pipeline.tests.test_documents_db import FILLER, run_jobs, vtt

KB = Path(__file__).resolve().parents[2] / "knowledge_base"
MARK = {"A": "alpha-booking-review", "B": "beta-inquiry-form", "C": "gamma-schema-failure"}


def doc_a() -> str:
    return vtt(("Carmen Cruickshank", f"Welcome Dana, {MARK['A']}. {FILLER}"),
               ("Dana Lee", f"We had 45 bookings in March. {FILLER}"),
               ("Carmen Cruickshank", f"Good, let us look at the follow up. {FILLER}"),
               ("Dana Lee", "Lead Lock has helped a lot with the follow-up."))


def doc_b() -> str:
    return vtt(("Carmen Cruickshank", f"Welcome Dana, {MARK['B']}. {FILLER}"),
               ("Carmen Cruickshank", f"Dana loves the new inquiry form so much. {FILLER}"),
               ("Dana Lee", f"I stopped dreading Mondays after the form changed. {FILLER}"),
               ("Dana Lee", f"Honestly the form is the best change we made. {FILLER}"))


def doc_c() -> str:
    return vtt(("Carmen Cruickshank", f"Welcome Dana, {MARK['C']}. {FILLER}"),
               ("Dana Lee", f"Our calendar is the main thing for us. {FILLER}"))


FILES = {"Review with Dana Lee 2026-03-10 A.vtt": doc_a, "Review with Dana Lee 2026-03-11 B.vtt": doc_b,
         "Review with Dana Lee 2026-03-12 C.vtt": doc_c}


def scene(**changes) -> dict:
    value = {"local_key": "s1", "anchor_span_ids": ["m1.t0002"], "context_first_span_id": "m1.t0001", "context_last_span_id": "m1.t0003",
             "quote": "We had 45 bookings in March.", "setup": "The client reports March bookings.",
             "wia_moves": [{"speaker": "Carmen Cruickshank", "move": "asked", "what": "How March went"}],
             "client_contribution": "Reported 45 bookings in March", "left_open": [], "process_step": None,
             "moment_type": "result", "qualifications": ["Reported, not measured by WIA"], "claim_status": "reported",
             "sensitivity": "public_candidate"}
    value.update(changes)
    return value


def response(inventory, *scenes, notes=()) -> dict:
    return {"scenes": list(scenes), "processed_meetings": inventory, "coverage_notes": list(notes)}


class ScriptedProvider:
    """Answers a v2 scene call from a script keyed by the document's marker; counts every call. `scripts[marker]` is a
    function of the delivery inventory returning the response (or a list of responses for the first call and the repair)."""

    records_runs = False

    def __init__(self, scripts):
        self.scripts, self.calls, self.users, self.systems = scripts, [], [], []

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage != "moment_extraction":
            raise AssertionError(f"unexpected stage {stage}")
        marker = next(m for m in self.scripts if m in user)
        self.calls.append(marker)
        self.users.append(user)
        self.systems.append(system)
        inventory = json.loads(re.search(r"Trusted delivery inventory for this document \(not conversation evidence\):\n(\[.*?\])", system).group(1))
        script = self.scripts[marker]
        attempt = self.calls.count(marker)
        out = script(inventory, attempt, system) if callable(script) else script
        return out, {"fake": True}

    def embed(self, *, text, fingerprint):  # pragma: no cover - extraction never embeds
        raise AssertionError("extraction never embeds")


def standard_scripts():
    return {
        MARK["A"]: lambda inv, n, system: response(inv, scene(),
            scene(local_key="s2", anchor_span_ids=["m1.t0004"], context_first_span_id="m1.t0003", context_last_span_id="m1.t0004",
                  quote="Lead Lock has helped a lot with the follow up", setup="A near-miss quote (a hyphen differs).",
                  client_contribution="Said the follow-up tool helped", moment_type="observation", sensitivity="unknown"),
            scene(local_key="s3", anchor_span_ids=["m1.t0003"], context_first_span_id="m1.t0003", context_last_span_id="m1.t0003",
                  quote="Nobody said this at all, ever.", setup="No binding quote.", moment_type="observation")),
        MARK["B"]: lambda inv, n, system: response(inv,
            scene(local_key="p1", anchor_span_ids=["m1.t0002"], context_first_span_id="m1.t0001", context_last_span_id="m1.t0003",
                  quote="Dana loves the new inquiry form so much.", setup="A team member says the client likes the form.",
                  wia_moves=[{"speaker": "Carmen Cruickshank", "move": "noticed", "what": "Dana likes the new form"}],
                  client_contribution=None, moment_type="testimonial", sensitivity="public_candidate"),
            scene(local_key="p2", anchor_span_ids=["m1.t0003"], context_first_span_id="m1.t0002", context_last_span_id="m1.t0004",
                  quote="I stopped dreading Mondays after the form changed.", setup="The client describes the effect of the form.",
                  client_contribution="Said she stopped dreading Mondays and that bookings rose by 60", moment_type="testimonial",
                  sensitivity="public_candidate")),
        MARK["C"]: lambda inv, n, system: {"scenes": "not a list", "coverage_notes": []},
    }


def import_documents(repo, models, tmp_path, files=None, *, name="drop") -> dict[str, dict]:
    """Import the files as week-less documents and normalise them; returns the rows by the letter in their file name."""
    root = tmp_path / name
    root.mkdir()
    files = files or FILES
    for filename, make in files.items():
        (root / filename).write_text(make(), encoding="utf-8")
    intake.import_directory(repo, root)
    run_jobs(repo, models)
    with repo.connection() as conn:
        rows = conn.execute("SELECT * FROM transcripts WHERE week_id IS NULL AND title=ANY(%s) ORDER BY title", (list(files),)).fetchall()
    return {row["title"].split()[-1].split(".")[0]: row for row in rows}


def prepare_reference(repo) -> None:
    with repo.connection() as conn:
        reference.sync_roster(conn, KB, date(2026, 10, 18))
        reference.add_glossary_term(conn, "LeadLock", "product", ["Lead Lock", "lead luck"])
