"""Fathom calls from before the collector's activation, as documents (plan 6.B18, "the October calls").

The live collector (intake/fathom.py) never fetches a call created before its activation, so earlier calls come in through
this one-off command. It lists the meetings recorded in a date window through the collector's own client, writes each in the
native Fathom folder shape outside the repository (R48): `transcript.raw.json`, the API's transcript bytes exactly as received,
beside its `metadata.json` envelope. Then the folders go through `documents import`, each new document is normalised by the
rules (no model call: a call the rules cannot place waits for a person), and the embedding is estimated; embedding is a paid
step, queued only when asked (`--embed live`) and dispatched under a run plan.

No call is added twice:
- Identity is the one the live collector gives the same recording: `fathom:<recording_id>` and the SHA-256 of the transcript
  bytes (normalise/sources.fathom_document). A recording already stored (from a week packet, an earlier run or the collector) is
  neither fetched nor written again, and a later live collection of a backfilled call finds its document.
- The same call can already be a document from another source (the Zoom file of a call Fathom also recorded), or be recorded
  twice in Fathom (two team members' note-takers in one meeting). Their texts differ, so the copy check (1.B10, exact text)
  cannot see them. A recording that starts within minutes of a stored document, or of another recording in the window, and
  shares most of its wording with it (word trigrams, `same_call`) is that call: it is listed with what it matches and not
  imported. Of two recordings of one meeting, the fuller transcript is kept.
- A folder written by an earlier run is reused, so a rerun fetches and adds nothing.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, date, datetime, time as clock, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from ..normalise.sources import IST, fathom_document, fathom_title
from .intake import FATHOM_NATIVE

# A recording is created in Fathom when it ends; a call that starts on the window's last evening is created after the window.
CREATION_SLACK = timedelta(days=2)
# Two recordings of one meeting start within this of each other (one note-taker joins late), as do a Zoom file dated from the
# calendar and Fathom's recording of the same call.
SAME_CALL_START = timedelta(minutes=10)
# Share of the shorter text's word trigrams found in the other. Two transcriptions of one conversation share most of them, even
# from different engines; two different calls share only stock phrases.
SAME_CALL_SHARE = 0.3
METADATA = "metadata.json"
COLLECTOR = "documents fathom-backfill"


def window(start: date, end: date, timezone: str) -> tuple[datetime, datetime]:
    """The calendar days start..end inclusive in a time zone, as an aware [start, end) interval."""
    if end < start:
        raise ValueError("The window ends before it starts")
    zone = ZoneInfo(timezone)
    return datetime.combine(start, clock(0), zone), datetime.combine(end + timedelta(days=1), clock(0), zone)


def occurred(meeting: dict) -> datetime | None:
    """When the call happened: the recording's start, else the scheduled start, else when Fathom created it."""
    for key in ("recording_start_time", "scheduled_start_time", "created_at"):
        if meeting.get(key):
            value = datetime.fromisoformat(meeting[key])
            if value.tzinfo is None:
                raise ValueError(f"Fathom {key} requires a timezone")
            return value
    return None


def recording_id(meeting: dict) -> int:
    rid = meeting.get("recording_id")
    if type(rid) is not int:
        raise ValueError("Fathom recording ID must be an integer")
    return rid


def list_meetings(client, start: datetime, end: datetime) -> list[dict]:
    """The meetings recorded in [start, end), once each, in the order they happened."""
    found: dict[int, dict] = {}
    for page in client.meetings(start, end + CREATION_SLACK):
        for meeting in page:
            when = occurred(meeting)
            if when is not None and start <= when < end:
                found.setdefault(recording_id(meeting), meeting)
    return sorted(found.values(), key=lambda m: (occurred(m), recording_id(m)))


def stored(conn, recording_ids) -> dict[int, str]:
    """Recordings that are already documents (from a week packet, an earlier backfill or the live collector)."""
    rows = conn.execute("""SELECT upstream_id,transcript_id FROM transcripts WHERE source_type='fathom' AND upstream_id=ANY(%s)
        ORDER BY ingested_at""", ([f"fathom:{r}" for r in recording_ids],)).fetchall()
    found: dict[int, str] = {}
    for row in rows:
        found.setdefault(int(row["upstream_id"].split(":", 1)[1]), row["transcript_id"])
    return found


def near(conn, when: datetime) -> list[dict]:
    """Stored documents (not copies) that started within SAME_CALL_START of this time."""
    return conn.execute("""SELECT transcript_id,source_type,upstream_id,title,occurred_at,original_text FROM transcripts
        WHERE canonical_document_id IS NULL AND occurred_at BETWEEN %s AND %s ORDER BY occurred_at,transcript_id""",
                        (when - SAME_CALL_START, when + SAME_CALL_START)).fetchall()


CUE_LINE = re.compile(r"^\s*(?:WEBVTT.*|\d+|[\d:.,]+\s*-->.*)\s*$")
SPEAKER_LABEL = re.compile(r"^\s*[^:\n]{1,60}:\s+")


def trigrams(text: str) -> set[tuple[str, ...]]:
    """The spoken words' trigrams: caption numbers and timings and the speaker labels are not what was said (two calls with
    the same people share their names, and every caption file shares its timings)."""
    spoken = " ".join(SPEAKER_LABEL.sub("", line) for line in text.splitlines() if not CUE_LINE.match(line))
    words = re.findall(r"[a-z0-9']+", spoken.lower())
    return {tuple(words[i:i + 3]) for i in range(len(words) - 2)}


def same_call(a: str, b: str) -> float:
    """How much of the shorter text's wording (word trigrams) the other has, 0 to 1."""
    left, right = trigrams(a), trigrams(b)
    if not left or not right:
        return 0.0
    return round(len(left & right) / min(len(left), len(right)), 3)


def folder_for(root: Path, meeting: dict, timezone: str) -> Path:
    return Path(root) / occurred(meeting).astimezone(ZoneInfo(timezone)).date().isoformat() / str(recording_id(meeting))


def written(folder: Path) -> bool:
    """A folder an earlier run completed: both files, and the transcript's bytes are the ones its envelope names."""
    raw, meta = folder / FATHOM_NATIVE, folder / METADATA
    if not (raw.is_file() and meta.is_file()):
        return False
    try:
        return json.loads(meta.read_text(encoding="utf-8")).get("transcript_sha256") == hashlib.sha256(raw.read_bytes()).hexdigest()
    except ValueError:
        return False


def envelope(meeting: dict, raw: bytes, *, collected_at: datetime) -> dict:
    """The `metadata.json` that `documents import` (fathom_sources.capture_fathom) verifies: a selected additional source,
    the transcript's hash, and the provider's meeting metadata as the source metadata."""
    start = meeting.get("recording_start_time")
    if not start:
        raise ValueError("Fathom meeting has no recording start time")
    return {"source_type": "fathom", "classification": "additional", "selected_as_additional_source": True,
            "recording_id": recording_id(meeting), "week": None,
            "occurrence_ist": datetime.fromisoformat(start).astimezone(IST).isoformat(),
            "transcript_sha256": hashlib.sha256(raw).hexdigest(), "source_metadata": meeting,
            "collected_by": COLLECTOR, "collected_at": collected_at.isoformat()}


def write_folder(folder: Path, meeting: dict, raw: bytes, *, collected_at: datetime) -> None:
    meta = envelope(meeting, raw, collected_at=collected_at)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / FATHOM_NATIVE).write_bytes(raw)
    (folder / METADATA).write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch(client, rid: int, *, attempts: int = 5, sleep=time.sleep) -> bytes:
    """The transcript's bytes as Fathom sends them. A rate limit (429) waits and tries again; anything else is raised."""
    for attempt in range(attempts):
        try:
            raw, _ = client.transcript(rid)
            return raw
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 429 or attempt == attempts - 1:
                raise
            sleep(float(exc.response.headers.get("retry-after") or 10 * (attempt + 1)))
    raise AssertionError("unreachable")


def text_of(meeting: dict, raw: bytes) -> str:
    """The document text this recording would get, built by the one Fathom normaliser (offline)."""
    return fathom_document(meeting, json.loads(raw), hashlib.sha256(raw).hexdigest())["original_text"]


def outside_repository(root: Path) -> None:
    """Call text belongs outside git, or under research/ (R48)."""
    from ..config import BACKEND_ROOT
    project = BACKEND_ROOT.parent.resolve()
    if project.parent == project:  # The image installs the backend at /app, whose parent is the filesystem root.
        project = BACKEND_ROOT.resolve()
    target = Path(root).resolve()
    if target.is_relative_to(project) and not target.is_relative_to(project / "research"):
        raise ValueError(f"Write the Fathom folders outside the repository (R48), not under {project}")


def run(repo, models, client, *, start: datetime, end: datetime, out: Path, timezone: str, dry_run: bool = False,
        estimate: bool = False, embed: str | None = None, actor: str = "local-cli", sleep=time.sleep) -> dict:
    """List, fetch, write, import, normalise by the rules, and estimate (or with `embed`, queue) the embedding.

    `dry_run` and `estimate` read the meeting list and the database only: no transcript is fetched and nothing is written;
    a recording that starts near a stored document or another recording is flagged `possible_same_call` (the wording decides
    on a real run). `estimate` adds what the paid steps would cost for the window's recordings that are documents already."""
    outside_repository(out)
    meetings = list_meetings(client, start, end)
    with repo.connection() as conn:
        known = stored(conn, [recording_id(m) for m in meetings])
        nearby = {recording_id(m): near(conn, occurred(m)) for m in meetings if recording_id(m) not in known}
    listing = []
    for meeting in meetings:
        rid = recording_id(meeting)
        folder = folder_for(out, meeting, timezone)
        state = "already_a_document" if rid in known else "fetched_earlier" if written(folder) else "to_fetch"
        listing.append({"recording_id": rid, "title": fathom_title(meeting, rid),
                        "occurred_at": occurred(meeting).isoformat(), "state": state, "transcript_id": known.get(rid),
                        "folder": str(folder), "meeting": meeting})
    window_text = {"from": start.isoformat(), "to": end.isoformat(), "timezone": timezone}
    if dry_run or estimate:
        for item in listing:
            if item["state"] == "already_a_document":
                continue
            when = datetime.fromisoformat(item["occurred_at"])
            item["possible_same_call"] = [d["transcript_id"] for d in nearby[item["recording_id"]]] + [
                other["recording_id"] for other in listing if other is not item
                and abs(datetime.fromisoformat(other["occurred_at"]) - when) <= SAME_CALL_START]
        result = {"window": window_text, "meetings_listed": len(meetings), "by_state": _count(listing, "state"),
                  "fetched": 0, "written": 0, "meetings": _public(listing)}
        if estimate:
            result["estimate"] = _estimate(repo, models, list(known.values()))
        return result
    fetched, failed = _texts(client, listing, sleep)
    _same_calls(listing, nearby)
    collected_at = datetime.now(UTC)
    for item in listing:
        if item["state"] == "fetched":
            write_folder(Path(item["folder"]), item["meeting"], item.pop("raw"), collected_at=collected_at)
    folders = [Path(i["folder"]) for i in listing if i["state"] in {"fetched", "fetched_earlier"}]
    imported = _import(repo, out, folders, actor)
    return _finish(repo, models, listing, imported, embed=embed, actor=actor,
                   head={"window": window_text, "meetings_listed": len(meetings), "fetched": fetched, "failed": failed})


def _texts(client, listing: list[dict], sleep) -> tuple[int, list[dict]]:
    """Fetch each new recording's transcript (or read the folder an earlier run wrote) and build its text, offline."""
    from ..intake.fathom import PendingTranscript
    fetched, failed = 0, []
    for item in listing:
        if item["state"] not in {"to_fetch", "fetched_earlier"}:
            continue
        try:
            if item["state"] == "fetched_earlier":
                raw = (Path(item["folder"]) / FATHOM_NATIVE).read_bytes()
            else:
                raw = fetch(client, item["recording_id"], sleep=sleep)
                fetched += 1
                envelope(item["meeting"], raw, collected_at=datetime.now(UTC))  # refuses a meeting with no recording time
                item["raw"], item["state"] = raw, "fetched"
            item["text"] = text_of(item["meeting"], raw)
        except PendingTranscript:
            item["state"] = "transcript_not_ready"
        except ValueError as exc:  # JSONDecodeError is a ValueError
            item["state"] = "failed"
            item.pop("raw", None)
            failed.append({"recording_id": item["recording_id"], "reason": f"{type(exc).__name__}: {exc}"[:300]})
    return fetched, failed


def _same_calls(listing: list[dict], nearby: dict[int, list[dict]]) -> None:
    """Mark a recording that is a stored document's call, or another recording's in this window, so it is not imported."""
    pending = [i for i in listing if "text" in i]
    for item in pending:
        scores = [(same_call(item["text"], d["original_text"]), d["transcript_id"]) for d in nearby[item["recording_id"]]]
        best = max(scores, default=(0.0, None))
        if best[0] >= SAME_CALL_SHARE:
            item.update(state="same_call_as_document", same_as=best[1], similarity=best[0])
            item.pop("raw", None)
    # Two recordings of one meeting: keep the fuller transcript (then the lower id); the others name it.
    pending = sorted((i for i in pending if i["state"] in {"fetched", "fetched_earlier"}),
                     key=lambda i: (-len(i["text"]), i["recording_id"]))
    kept: list[dict] = []
    for item in pending:
        when = datetime.fromisoformat(item["occurred_at"])
        twin = next(((score, k) for k in kept if abs(datetime.fromisoformat(k["occurred_at"]) - when) <= SAME_CALL_START
                     and (score := same_call(item["text"], k["text"])) >= SAME_CALL_SHARE), None)
        if twin is None:
            kept.append(item)
            continue
        item.update(state="same_call_as_recording", same_as=twin[1]["recording_id"], similarity=twin[0])
        item.pop("raw", None)


def _import(repo, out: Path, folders: list[Path], actor: str) -> dict:
    from .intake import import_directory
    if not folders:
        return {"files": 0, "new": 0, "unchanged": 0, "skipped": [], "failed": [], "transcript_ids": [], "run_id": None, "jobs": 0}
    return import_directory(repo, out, paths=[f / FATHOM_NATIVE for f in folders], actor=actor)


def _finish(repo, models, listing: list[dict], imported: dict, *, embed, actor, head) -> dict:
    """Normalise the window's documents that are not yet (rules only, no provider: no model call), then report and estimate."""
    from . import reembed
    from .jobs import normalise
    with repo.connection() as conn:
        now_known = stored(conn, [i["recording_id"] for i in listing])
    for item in listing:
        item["transcript_id"] = now_known.get(item["recording_id"], item["transcript_id"])
    ids = sorted({i["transcript_id"] for i in listing if i["transcript_id"] and i["state"] != "same_call_as_document"})
    with repo.connection() as conn:
        waiting = [r["transcript_id"] for r in conn.execute(
            "SELECT transcript_id FROM transcripts WHERE transcript_id=ANY(%s) AND normalised_at IS NULL ORDER BY 1", (ids,)).fetchall()]
    normalised = [normalise(repo, transcript_id, models=models, provider=None) for transcript_id in waiting]
    with repo.connection() as conn:
        rows = conn.execute("""SELECT transcript_id,call_type,included,occurred_at_source,canonical_document_id,
            normalised_at IS NOT NULL AS normalised,COALESCE(classification->>'needs_review','false')='true' AS needs_review
            FROM transcripts WHERE transcript_id=ANY(%s) ORDER BY transcript_id""", (ids,)).fetchall()
        embedding = reembed.estimate(conn, ids)
    queued = reembed.queue(repo, models, transcript_ids=ids, mode=embed, actor=actor) if embed and ids else None
    created = set(imported["transcript_ids"])
    return {**head,
            "already_documents": sum(1 for i in listing if i["state"] == "already_a_document"),
            "same_call_as_a_document": sum(1 for i in listing if i["state"] == "same_call_as_document"),
            "same_call_as_another_recording": sum(1 for i in listing if i["state"] == "same_call_as_recording"),
            "import": {k: imported[k] for k in ("files", "new", "unchanged", "skipped", "failed", "run_id", "jobs")},
            "imported": len(created), "normalised_now": len(normalised),
            "documents": len(ids), "normalised": sum(1 for r in rows if r["normalised"]),
            "waiting_for_classification": sum(1 for r in rows if r["needs_review"]),
            "included": sum(1 for r in rows if r["included"]),
            "duplicates_linked": sum(1 for r in rows if r["canonical_document_id"]),
            "dated_by_provider": sum(1 for r in rows if r["occurred_at_source"] == "provider"),
            "by_call_type": _count(rows, "call_type"),
            "embedding_estimate": embedding, "embedding_queued": queued, "next": _next(ids, embed, embedding, models),
            "by_state": _count(listing, "state"), "meetings": _public(listing),
            "classification": [{k: n[k] for k in ("transcript_id", "call_type", "included", "needs_review", "dated", "duplicate_of")}
                               for n in normalised]}


def _public(listing: list[dict]) -> list[dict]:
    """The listing as reported: no transcript text or bytes, and the meeting's title only (its metadata is in the folder)."""
    return [{k: v for k, v in i.items() if k not in {"meeting", "raw", "text"}} for i in listing]


def _estimate(repo, models, ids: list[str]) -> dict:
    from . import reembed
    from .jobs import classification_estimate
    with repo.connection() as conn:
        unnormalised = [r["transcript_id"] for r in conn.execute(
            "SELECT transcript_id FROM transcripts WHERE transcript_id=ANY(%s) AND normalised_at IS NULL", (ids,)).fetchall()]
        embedding = reembed.estimate(conn, ids)
    return {"documents": len(ids), "embedding": embedding,
            "classification": classification_estimate(repo, unnormalised, models) if unnormalised else None,
            "note": "Recordings not yet documents are counted once imported (fetching and importing are free); the embedding "
                    "estimate covers normalised documents only."}


def _next(ids: list[str], embed: str | None, embedding: dict, models) -> list[str]:
    """The paid step's commands, in order, for an operator with a funded key: estimate, plan, queue, run."""
    from ..chunk_encoding import BATCH_SIZE
    if not ids or embed or not embedding["chunks"]:
        return []
    joined = " ".join(ids)
    calls = -(-embedding["chunks"] // BATCH_SIZE)
    cap = max(0.01, round(embedding["estimated_cost_usd"] * 2, 2))
    cli = "python -m backend_pipeline.storage_cli"
    return [f"{cli} documents reembed --estimate --ids {joined}",
            f"{cli} plan create --purpose \"Embed the backfilled Fathom calls (6.B18)\" --stage embedding --model {models.embedding_model} "
            f"--input-set-hash '*' --max-calls {calls} --max-cost-usd {cap} --hours 6 --approver <approver email>",
            f"ATELIER_ALLOW_ENCODING=true {cli} documents reembed --mode live --ids {joined}",
            f"ATELIER_ALLOW_ENCODING=true ATELIER_RUN_PLAN_ID=<plan id> EMBEDDING_API_KEY=<key> {cli} worker"]


def _count(rows, key) -> dict:
    counts: dict = {}
    for row in rows:
        counts[str(row[key])] = counts.get(str(row[key]), 0) + 1
    return counts
