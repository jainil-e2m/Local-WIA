"""File intake as documents (plan 1.B3).

A directory of transcripts becomes documents that belong to no week: text and WebVTT files, and native Fathom folders
(`transcript.raw.json` with its `metadata.json`) through the same path. Identity comes from the content (a file imported
from anywhere is one document), the original bytes go to the artifact store, and each new document gets a normalise job.
Importing the same directory twice adds nothing: no rows, no jobs.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from psycopg.types.json import Jsonb

from ..normalise.sources import LIVE_RESTRICTIONS
from ..repository import insert
from ..store import canonical_hash
from . import NORMALISE_STAGE, RUN_SCOPE

TEXT_SUFFIXES = {".txt", ".vtt", ".webvtt"}
FATHOM_NATIVE = "transcript.raw.json"


def discover(directory) -> list[Path]:
    """Importable files under a directory, in a stable order. Hidden files (a macOS `._name` copy, an editor's lock file)
    are not transcripts."""
    root = Path(directory)
    if not root.is_dir():
        raise ValueError(f"{root} is not a directory")
    return sorted(p for p in root.rglob("*") if p.is_file() and not p.name.startswith(".")
                  and (p.suffix.lower() in TEXT_SUFFIXES or p.name == FATHOM_NATIVE))


def text_document(path: Path, raw: bytes, source_type: str = "zoom") -> dict:
    """A text or WebVTT file as a week-less document whose identity is its content, not its path."""
    from ..storage_sources import capture
    digest = hashlib.sha256(raw).hexdigest()
    record = capture(path, 0, 0, source_id=f"file:{digest[:16]}")
    record.update({"source_type": source_type, "week_id": None, "use_restrictions": LIVE_RESTRICTIONS, "occurred_at": None,
                   "occurred_at_source": None, "processing_status": "pending"})
    # The path is an accident of where the file sat; what it was called is worth keeping, for dates and for people.
    record["source_metadata"] = {**record["source_metadata"], "filename": path.name, "week_index": 0}
    record["source_metadata"].pop("file_order", None)
    record["source_metadata"].pop("source_path", None)
    return record


def fathom_document(path: Path) -> dict:
    from ..fathom_sources import capture_fathom
    record = capture_fathom(path, None, 0)
    record.update({"week_id": None, "use_restrictions": LIVE_RESTRICTIONS, "processing_status": "pending"})
    return record


def _raw_key(raw: bytes) -> str:
    return f"source-originals/{hashlib.sha256(raw).hexdigest()}.original"


# What a reader of a document sees: its text and where each passage is and who said it. Keys a later normaliser added beside
# them (1.B14's `locator` and `extraction_method` on Fathom passages) describe the same passages and are not a change.
READER_KEYS = ("passage_id", "ordinal", "start", "end", "speaker", "start_ms", "end_ms")


def reader_view(original_text: str, passage_map: list[dict]):
    return original_text, [tuple(p.get(k) for k in READER_KEYS) for p in passage_map]


def register(conn, store, record: dict, raw: bytes) -> bool:
    """Store one document if it is new. Returns True when a row was created; raises if the id exists with other text."""
    existing = conn.execute("SELECT original_text,passage_map FROM transcripts WHERE transcript_id=%s", (record["transcript_id"],)).fetchone()
    if existing:
        if reader_view(existing["original_text"], existing["passage_map"]) != reader_view(record["original_text"], record["passage_map"]):
            raise ValueError("Reader view differs from an immutable stored document; an explicit migration is required")
        return False
    key = _raw_key(raw)
    store.write_bytes(key, raw)
    insert(conn, "transcripts", {**record, "raw_object_key": key})
    return True


def queue_normalisation(conn, transcript_ids: list[str], *, actor: str, version: str) -> dict:
    """One run for a batch, one `document_normalise` job per document (idempotent per document and normaliser version)."""
    from ..repository import identifier  # noqa: F401  (kept for symmetry with other queues)
    if not transcript_ids:
        return {"run_id": None, "jobs": []}
    run_id = "docrun_" + canonical_hash([sorted(transcript_ids), version])[:24]
    insert(conn, "pipeline_runs", {"run_id": run_id, "week_id": None, "run_scope": RUN_SCOPE, "trigger_type": "manual",
                                   "triggered_by": actor, "input_refs": {"transcript_ids": sorted(transcript_ids), "normaliser": version}},
           conflict=True)
    jobs = []
    for transcript_id in sorted(transcript_ids):
        key = canonical_hash([NORMALISE_STAGE, transcript_id, version])
        job_id = "docjob_" + key[:24]
        insert(conn, "pipeline_jobs", {"job_id": job_id, "run_id": run_id, "week_id": None, "transcript_id": transcript_id,
                                       "stage": NORMALISE_STAGE, "idempotency_key": "document:" + key, "input_hash": key,
                                       "progress_details": Jsonb({"dependencies": []}),
                                       "current_message": "Waiting to classify, resolve speakers, date and segment"}, conflict=True)
        jobs.append(job_id)
    return {"run_id": run_id, "jobs": jobs}


def import_directory(repo, directory, *, source_type: str = "zoom", actor: str = "local-cli", paths=None) -> dict:
    """Import every transcript under a directory as week-less documents, once each (or only `paths`, files under it).

    One file never stops the others (plan 4.11, "Normalise: unreadable file"): a file that does not parse is listed under
    `failed` with its reason (fix it and import again; what was imported is not imported twice), and a Fathom capture the
    reconciliation did not select for admission is listed under `skipped`."""
    from ..artifacts import store_for
    from ..fathom_sources import NotSelected
    from ..normalise import NORMALISER_VERSION
    root = Path(directory)
    if paths is None:
        paths = discover(root)
    else:
        paths = sorted(Path(p) for p in paths)
        if any(not p.resolve().is_relative_to(root.resolve()) for p in paths):
            raise ValueError("Every file to import must be under the directory")
    if not paths:
        raise ValueError("No transcript files (.txt, .vtt, .webvtt or a native Fathom folder) under that directory")
    prepared, skipped, failed = [], [], []
    for path in paths:
        name = path.relative_to(root).as_posix()
        try:
            raw = path.read_bytes()
            record = fathom_document(path) if path.name == FATHOM_NATIVE else text_document(path, raw, source_type)
        except NotSelected as exc:
            skipped.append({"file": name, "reason": str(exc)})
            continue
        except (ValueError, KeyError, TypeError, OSError) as exc:  # UnicodeDecodeError and JSONDecodeError are ValueErrors
            failed.append({"file": name, "reason": f"{type(exc).__name__}: {exc}"[:300]})
            continue
        prepared.append((name, record, raw))
    store = store_for(repo.settings)
    created, unchanged = [], 0
    with repo.connection() as conn:
        for name, record, raw in prepared:
            try:
                if register(conn, store, record, raw):
                    created.append(record["transcript_id"])
                else:
                    unchanged += 1
            except ValueError as exc:  # the id exists with another text: that file's failure, raised before anything is written
                failed.append({"file": name, "reason": f"{type(exc).__name__}: {exc}"[:300]})
        queued = queue_normalisation(conn, created, actor=actor, version=NORMALISER_VERSION)
    return {"files": len(paths), "new": len(created), "unchanged": unchanged, "skipped": skipped,
            "failed": failed, "transcript_ids": created, "run_id": queued["run_id"], "jobs": len(queued["jobs"])}
