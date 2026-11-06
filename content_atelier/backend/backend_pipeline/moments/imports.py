"""Importing saved extraction responses as ledger rows (plan 2.B10): Weeks 1 and 2 without regenerating anything.

The file-backed runs saved every validated model response as a `StageArtifact` JSON (the weekly packet in its request, the
compact moments in its output). `import_saved` reads those files, makes **no provider call and writes no `llm_runs` row**, and
stores each moment through the one ledger writer, so it carries the same columns as a moment extracted today.

* **Which documents.** An artifact's request holds the weekly packet: each meeting's turns, in order. A meeting is matched to the
  stored document whose passages say exactly those turns (the document's content, which is stronger than its name or path:
  the same call imported from anywhere is one document). The match, the document's content hash and its upstream id go
  into the provenance. A meeting that matches no document, or a document that is excluded, is reported and skipped: an
  excluded document has no moment in the ledger.
* **Which moments.** Each meeting's moments are resolved against that document alone and checked one by one with E.B12a's rule
  (a quote that binds is kept, a near-miss repaired and recorded, the rest kept as unverified records). Moment identity is the
  extractor's content hash over the sources it was extracted from, which for a weekly response is every meeting of its packet:
  hashed over all the matched documents, a scene the SQL weekly path already stored from the same response has the same ID,
  so it is left as it is and gains an `also_extracted_by` note (on the real Weeks 1 and 2, every bound scene).
* **Failed attempts (E.B12a).** With `include_failed`, a failed attempt's received response (`output.received.json`) is
  re-checked the same way, and its provenance names the attempt and the error that rejected the whole response then.
* **Provenance.** `extractor_version = imported:<original prompt profile>` and `checks.imported_from` (the artifact, its request
  fingerprint, the original run, the model, the meeting, the scene's local key, the match, who imported it and when).
* **Idempotent.** Importing the same artifacts again stores nothing new.

The real Week 1 and 2 artifacts arrived with the developer's handover (S.B10, 19 October 2026); the tests generate synthetic
ones in the same format.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from ..models import StageArtifact
from ..moment_validation import resolve_moment_references_partial
from ..pipeline import Pipeline
from ..storage_sources import reconstruct
from ..store import canonical_hash
from . import extract, store

TURN = re.compile(r"^(m\d+\.t\d+)\|([^|]*)\|(.*)$")
WEEKLY_PROFILE = "2026-10-13.weekly.v3"


class _Checker(Pipeline):
    """E.B12a's per-moment check, without the file runner's settings, store or provider. A meeting is checked against its
    own document; `identity_sources`, when given, are the sources a moment's ID hashes (the whole packet's documents)."""

    def __init__(self, identity_sources=None):
        self.identity_sources = identity_sources

    def _moment(self, draft, raw, spans, transcripts):
        return Pipeline._moment(draft, raw, spans, self.identity_sources or transcripts)


# ---- reading the files -----------------------------------------------------------------------------------------------------

def discover(path, *, include_failed: bool = False) -> list[tuple[Path, StageArtifact]]:
    """The validated moment-extraction artifacts under a file or folder, one per request fingerprint, in a stable order.
    Cache pointers, other stages and files that are not artifacts are ignored.

    With `include_failed`, a failed attempt that saved the response it received (`output.received.json` beside its
    `artifact.json`, the layout `revalidate_saved` reads) is re-checked too (E.B12a): a whole response that an earlier,
    stricter check rejected for one quote can still yield every moment that binds. A validated artifact for the same
    request wins."""
    root = Path(path)
    files = [root] if root.is_file() else sorted(p for p in root.rglob("*.json") if p.is_file())
    found: dict[str, tuple[Path, StageArtifact]] = {}
    failed: dict[str, tuple[Path, StageArtifact]] = {}
    for file in files:
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            if not (isinstance(data, dict) and data.get("stage") == "moment_extraction"):
                continue
            if data.get("status") == "validated" and isinstance(data.get("output"), dict):
                artifact = StageArtifact.model_validate(data)
                if artifact.output_hash and artifact.output_hash != canonical_hash(artifact.output):
                    continue  # an artifact whose output no longer matches its own hash is not trusted
                found.setdefault(artifact.request_fingerprint, (file, artifact))
            elif include_failed and data.get("status") == "failed" and (file.parent / "output.received.json").is_file():
                received = json.loads((file.parent / "output.received.json").read_text(encoding="utf-8"))
                if not isinstance(received, dict):
                    continue
                metadata = {**(data.get("metadata") or {}), "revalidated_from_attempt": str(file.parent),
                            "original_error": data.get("error")}
                artifact = StageArtifact.model_validate({**data, "output": received, "output_hash": canonical_hash(received),
                                                         "metadata": metadata})
                failed.setdefault(artifact.request_fingerprint, (file, artifact))
        except (OSError, ValueError):
            continue
    for fingerprint, item in failed.items():
        found.setdefault(fingerprint, item)
    return sorted(found.values(), key=lambda item: (item[1].created_at, item[1].request_fingerprint))


def user_message(artifact: StageArtifact) -> str:
    messages = (artifact.request or {}).get("messages") or []
    users = [m.get("content") for m in messages if m.get("role") == "user" and isinstance(m.get("content"), str)]
    if not users:
        raise ValueError("The artifact's request holds no user message, so its meetings cannot be identified")
    return users[-1]


def parse_packet(text: str) -> list[dict]:
    """The meetings of a weekly packet: `{ref, metadata, turns: [{ref, text}]}`, turns in order, texts exactly as delivered."""
    start = text.find("MEETING ")
    if start < 0:
        raise ValueError("The artifact's request holds no weekly packet")
    meetings, meeting, turn = [], None, None
    for line in text[start:].split("\n"):
        if line.startswith("MEETING {"):
            metadata = json.loads(line[len("MEETING "):])
            meeting, turn = {"ref": metadata["source_id"], "metadata": metadata, "turns": []}, None
            meetings.append(meeting)
        elif line.startswith("END_MEETING "):
            meeting = turn = None
        elif meeting is None:
            continue
        elif line.startswith("CUE_SETTINGS "):
            turn = None
        elif line.startswith(("UNTIMED {", "TIMESTAMPED {")):
            item = json.loads(line.split(" ", 1)[1])
            turn = {"ref": item["ref"], "text": item["text"]}
            meeting["turns"].append(turn)
        elif m := TURN.match(line):
            turn = {"ref": m.group(1), "text": m.group(3)}
            meeting["turns"].append(turn)
        elif turn is not None:
            turn["text"] += "\n" + line
    return meetings


def texts_of(document: dict) -> list[str]:
    return [document["original_text"][p["start"]:p["end"]] for p in document["passage_map"]]


def match_documents(meetings: list[dict], documents: list[dict]) -> dict[str, dict]:
    """meeting ref -> {document, matched_by}: the stored document whose passages are exactly the meeting's turns."""
    by_content: dict[str, list[dict]] = {}
    for document in documents:
        by_content.setdefault(canonical_hash(texts_of(document)), []).append(document)
    out = {}
    for meeting in meetings:
        candidates = by_content.get(canonical_hash([t["text"] for t in meeting["turns"]]), [])
        # Copies of one call share their content: the canonical one wins, then the oldest.
        candidates.sort(key=lambda d: (d.get("canonical_document_id") is not None, str(d.get("ingested_at")), d["transcript_id"]))
        if candidates:
            out[meeting["ref"]] = {"document": candidates[0], "matched_by": "turn_text"}
    return out


# ---- importing --------------------------------------------------------------------------------------------------------------

def meeting_output(output: dict, meeting_ref: str) -> dict:
    """The part of a weekly response that concerns one meeting: its moments (by their first anchor) and its coverage entry."""
    key = "moments" if "moments" in output else "scenes"
    mine = [m for m in output[key] if m["anchor_span_ids"][0].split(".", 1)[0] == meeting_ref]
    entry = [e for e in output["processed_meetings"] if e["meeting_ref"] == meeting_ref]
    return {**{k: v for k, v in output.items() if k not in (key, "processed_meetings")}, key: mine, "processed_meetings": entry}


def meeting_refs(meeting: dict, document: dict) -> dict[str, str]:
    """The compact reference of each turn -> the document's passage ID, in the artifact's own numbering."""
    if len(meeting["turns"]) != len(document["passage_map"]):
        raise ValueError("The meeting and the document differ in length")
    return {turn["ref"]: p["passage_id"] for turn, p in zip(meeting["turns"], document["passage_map"], strict=True)}


def check_meeting(output: dict, meeting: dict, document: dict, profile: str, sources: list[dict] | None = None):
    """One meeting's moments against its document, scene by scene. Returns the partition (moments, repairs, unverified).

    `sources` are every document the artifact's packet matched: a moment's identity hashes the sources it was extracted
    from, so the weekly path's row for the same scene has the same ID only when all of them are given."""
    refs = meeting_refs(meeting, document)
    transcripts, _, _ = reconstruct([document])
    part = meeting_output(output, meeting["ref"])
    if "scenes" in part:
        return extract.partition_scenes(part, refs, transcripts, profile, call_type=document.get("call_type"))
    resolved, unresolved = resolve_moment_references_partial(part, refs)
    identity = reconstruct(sources)[0] if sources else None
    result = _Checker(identity)._partition_moments(resolved, f"imported-{meeting['ref']}", transcripts, unresolved=unresolved)
    # The partition keeps its input order: the moments that bound are the response's moments that are not unverified.
    lost = {u["local_key"] for u in result.unverified}
    kept = [m["local_key"] for m in part["moments"] if m["local_key"] not in lost]
    return extract.ScenePartition(moments=result.moments, repairs=result.repairs, unverified=result.unverified,
                                  local_keys=dict(zip([m.moment_id for m in result.moments], kept, strict=True)))


def import_saved(repo, path, *, actor: str = "local-cli", apply: bool = True, roster=None, include_failed: bool = False) -> dict:
    """Import every validated moment-extraction artifact under `path` (and, with `include_failed`, every failed attempt's
    received response, re-checked moment by moment). With `apply=False`, report what would be stored."""
    artifacts = discover(path, include_failed=include_failed)
    now = datetime.now(UTC).isoformat()
    report = {"artifacts": [], "moments": 0, "already_present": 0, "unverified": 0, "repaired": 0, "unmatched_meetings": 0,
              "provider_calls": 0, "applied": apply}
    with repo.connection() as conn:
        documents = conn.execute("SELECT * FROM transcripts").fetchall()
        roster = roster if roster is not None else _roster(conn)
        for file, artifact in artifacts:
            revalidated = {k: artifact.metadata[k] for k in ("revalidated_from_attempt", "original_error")
                           if artifact.status == "failed" and artifact.metadata.get(k)}
            entry = {"artifact_id": artifact.artifact_id, "request_fingerprint": artifact.request_fingerprint, "file": file.name,
                     "prompt_version": artifact.prompt_version, "meetings": [], "problems": [], **revalidated}
            report["artifacts"].append(entry)
            profile = artifact.prompt_version or WEEKLY_PROFILE
            try:
                meetings = parse_packet(user_message(artifact))
            except ValueError as error:
                entry["problems"].append(str(error))
                continue
            matches = match_documents(meetings, documents)
            sources = [matches[m["ref"]]["document"] for m in meetings if m["ref"] in matches]
            for meeting in meetings:
                found = matches.get(meeting["ref"])
                item = {"meeting": meeting["ref"], "turns": len(meeting["turns"])}
                entry["meetings"].append(item)
                if found is None:
                    item["skipped"] = "no stored document says exactly these turns"
                    report["unmatched_meetings"] += 1
                    continue
                document = found["document"]
                item["document_id"] = document["transcript_id"]
                if not document["included"] or document.get("canonical_document_id"):
                    item["skipped"] = ("the document is excluded, so it has no moment" if not document["included"]
                                       else f"the document is a copy of {document['canonical_document_id']}")
                    continue
                try:
                    part = check_meeting(artifact.output, meeting, document, profile, sources)
                except ValueError as error:
                    item["skipped"] = f"the saved response does not check against the document: {error}"
                    entry["problems"].append(item["skipped"])
                    continue
                local = getattr(part, "local_keys", {})
                provenance = {m.moment_id: {"imported_from": {
                    "artifact_id": artifact.artifact_id, "request_fingerprint": artifact.request_fingerprint,
                    "original_run_id": artifact.run_id, "prompt_version": artifact.prompt_version, "model_id": artifact.model_id,
                    "artifact_created_at": artifact.created_at.isoformat(), "meeting": meeting["ref"], "matched_by": found["matched_by"],
                    "source_content_hash": document["content_hash"], "upstream_id": document["upstream_id"], "imported_by": actor,
                    "imported_at": now, "local_key": local.get(m.moment_id), **revalidated}} for m in part.moments}
                unverified = [{**u, "provenance": {"imported_from": {
                    "artifact_id": artifact.artifact_id, "request_fingerprint": artifact.request_fingerprint,
                    "original_run_id": artifact.run_id, "prompt_version": artifact.prompt_version, "meeting": meeting["ref"],
                    "matched_by": found["matched_by"], "imported_by": actor, "imported_at": now, **revalidated}}}
                              for u in part.unverified]
                ids = [m.moment_id for m in part.moments]
                present = {r["moment_id"] for r in conn.execute("SELECT moment_id FROM key_moments WHERE moment_id=ANY(%s::text[])", (ids,))}
                item.update({"moments": len(ids), "already_present": len(present), "repaired": len(part.repairs),
                             "unverified": len(unverified)})
                report["moments"] += len(ids) - len(present)
                report["already_present"] += len(present)
                report["unverified"] += len(unverified)
                report["repaired"] += len(part.repairs)
                if apply:
                    store.save(conn, part.moments, [document], run_id=None, week_id=document.get("week_id"),
                               extractor_version=f"{store.IMPORTED_PREFIX}{profile}", unverified=unverified, repairs=part.repairs,
                               provenance=provenance, unverified_scope=f"imported:{artifact.request_fingerprint}:{meeting['ref']}",
                               roster=roster)
    return report


def _roster(conn):
    """The roster, which places a speaker whose document has no speaker map yet (a Week 1 or 2 document before Phase 1's backfill)."""
    from ..repository import review_roster
    return review_roster(conn)
