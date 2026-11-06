"""Published finals captured against their approved brief (L.B9, section 1.9.5).

Final copy is written outside the system, so after Gate 2 a team member (an editor or an approver) pastes what WIA
actually published from an approved brief: the channel, the title, the final text, the publish date, and optionally the
link and the first figures. One request does four things, each through the path that already reads it:

- **Content memory.** A confirmed `published_content` row linked to the brief (`brief_id`), its card (`angle_id`), its
  pillar, content type and central point (`key_message`). The strategist's situational block reads it in the next
  cycle ("do not repeat a central point already published", `assembly._situational`; 3.B5, E.B25 f), and so does the
  compiled recent-published document (`compiler.published_rows`).
- **The learning loop.** The difference between the brief's copy for that channel and the published final is kept on
  the row as an authored edit (`details.edit`, the requesting person as its author). `mining.edit_diffs` reads it with
  the Gate 2 edits, so the next weekly pass categorises it and counts it towards a rule candidate (L.B6); the final
  itself is already an exemplar candidate there.
- **Performance.** Figures, when given, are performance entries in L.B7's shape (`performance.entry`), so the
  situational block's strongest and weakest pieces read them.
- **The vector.** The final is embedded through the search module's query path (`search.query.embed_query`) only when
  encoding is switched on (ATELIER_ALLOW_ENCODING, with a key and an active run plan). Otherwise the vector stays empty,
  as on every other published row, and `details.embedding` says why. No browser request starts a paid call otherwise.

Idempotent on the table's unique key. The kind is `approved_brief`, the kind migration 006 reserved for a piece published
from an approved brief (so no migration), and the reference is `capture:<brief_id>:<channel>:<piece>`: one final per
piece of an approved brief version. L.B7's own pieces use their content ID as the reference, so the two never collide. A
content pack's piece marked published (`record_pack`, NP.B3) uses `pack:<brief_id>:<piece key>`, its edit measured against
the pack's copy of that piece.
Sending the same final again answers the same row and adds only figures not yet recorded; a different final for the same
piece is refused, never silently replaced.
"""
from __future__ import annotations

import difflib
import hashlib
import re
from datetime import date, timedelta
from urllib.parse import urlsplit

from ..briefs.gate_two import authorize, is_v2
from ..briefs.validation import hash_brief
from ..repository import identifier, insert
from . import performance
from .review import _public

CHANNELS = ("reel", "carousel", "email", "caption", "stories")
SOURCE_KIND = "approved_brief"
MAX_TEXT = 20000
MAX_EDIT = 8000
MAX_METRICS = 20
# Well under the encoder's byte bound, as for moments.
EMBED_CHARACTERS = 6000
_UNIT = re.compile(r"(?<=[.!?])\s+|\n+")


def source_ref(brief_id: str, channel: str, piece: int) -> str:
    return f"capture:{brief_id}:{channel}:{piece}"


def _lines(*parts) -> str:
    return "\n".join(p.strip() for p in parts if isinstance(p, str) and p.strip())


def brief_copy(row: dict, channel: str, piece: int = 1) -> str | None:
    """The brief's own copy for one channel and piece, as the writer planned it; None when the brief plans none."""
    document = row["content_body"]["document"]
    if is_v2(row):
        plan = document["body"]["format_plan"]
        if channel == "reel":
            reels = plan.get("reels") or []
            if piece > len(reels):
                return None
            r = reels[piece - 1]
            # A v3 Reel's script is its spoken copy (E.B23); without one, its beats.
            if r.get("script"):
                return _lines(r.get("cover_text"), r["script"]) or None
            return _lines(r.get("cover_text"), r.get("spoken_opening"), *(r.get("beats") or [])) or None
        value = plan.get(channel) if piece == 1 else None
        if not value:
            return None
        if channel == "carousel":
            text = _lines(*(s.get("text") for s in value.get("slides") or []))
        elif channel == "email":
            # v2: argument and transformation; v3 (E.B23): the body.
            text = _lines(*(value.get("subject_options") or [])[:1], value.get("preview"), value.get("opening"),
                          value.get("argument"), value.get("transformation"), value.get("body"), value.get("ending"))
        elif channel == "caption":
            text = _lines(value.get("hook"), value.get("adds") or value.get("body"), value.get("ending"))
        else:
            text = _lines(*(value.get("frames") or []))
        return text or None
    if channel == "reel":
        reels = document.get("reels") or []
        if piece > len(reels):
            return None
        r = reels[piece - 1]
        return _lines(r.get("direction"), *(r.get("outline") or [])) or None
    if piece != 1:
        return None
    if channel == "email":
        email = document.get("email") or {}
        return _lines(email.get("direction"), *(email.get("outline") or [])) or None
    if channel == "carousel":
        return _lines(*(s.get("direction") for s in document.get("carousel") or [])) or None
    return None


def units(text: str | None) -> list[str]:
    """Sentences and lines, with their spacing normalised: the unit an edit is read in."""
    return [" ".join(u.split()) for u in _UNIT.split(text or "") if u and u.strip()]


def difference(before: str | None, after: str | None) -> dict | None:
    """What the final changed from the brief's copy: the brief's sentences it dropped or rewrote (`before`) and the
    final's sentences that replace or add to them (`after`). None when the final keeps the brief's copy exactly."""
    a, b = units(before), units(after)
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    removed, added = [], []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op != "equal":
            removed += a[i1:i2]
            added += b[j1:j2]
    if not removed and not added:
        return None
    return {"before": "\n".join(removed)[:MAX_EDIT], "after": "\n".join(added)[:MAX_EDIT], "similarity": round(matcher.ratio(), 3),
            "units": {"brief": len(a), "final": len(b), "removed": len(removed), "added": len(added)}}


def _facts(row: dict) -> dict:
    """The brief's pillar, content type and central point, where it carries them."""
    document = row["content_body"]["document"]
    if is_v2(row):
        body, header = document["body"], document.get("header") or {}
        purpose = body.get("strategic_purpose") or {}
        return {"pillar": header.get("purpose") or purpose.get("pillar"), "content_type": purpose.get("content_type"),
                "key_message": (body.get("approved_angle") or {}).get("core_perspective")}
    return {"pillar": None, "content_type": None, "key_message": document.get("angle_statement")}


def approved_brief(conn, brief_id: str, *, lock: bool = False) -> dict:
    """The brief, if it is approved and still the content that was approved; otherwise the refusal."""
    row = conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s" + (" FOR SHARE" if lock else ""), (brief_id,)).fetchone()
    if not row:
        raise LookupError("Brief not found")
    if row["approval_status"] != "approved":
        raise ValueError(f"A published final is recorded against an approved brief; this brief is {row['approval_status']}")
    if not row["approved_hash"] or row["approved_hash"] != row["content_hash"] or hash_brief(row) != row["content_hash"]:
        raise ValueError("This brief changed after it was approved; record the final against the approved version")
    return row


def _clean(channel, title, text, url, piece, published_on, metrics):
    channel = (channel or "").strip().lower()
    if channel not in CHANNELS:
        raise ValueError("The channel is one of: " + ", ".join(CHANNELS))
    title, text = (title or "").strip(), (text or "").strip()
    if not title or not text:
        raise ValueError("A published final needs its title and its text")
    if len(text) > MAX_TEXT:
        raise ValueError(f"A published final is at most {MAX_TEXT} characters")
    if piece < 1 or (piece > 1 and channel != "reel"):
        raise ValueError("Only reels are numbered; send piece 1 for this channel")
    url = (url or "").strip() or None
    if url and (urlsplit(url).scheme not in ("http", "https") or not urlsplit(url).netloc):
        raise ValueError("The link must be an http or https address")
    if published_on > date.today() + timedelta(days=1):
        raise ValueError("A published final has a publish date on or before today")
    if len(metrics) > MAX_METRICS:
        raise ValueError(f"At most {MAX_METRICS} figures per request")
    return channel, title, text, url


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _existing(conn, ref):
    return conn.execute("SELECT * FROM published_content WHERE source_kind=%s AND source_ref=%s", (SOURCE_KIND, ref)).fetchone()


def _same(row, title, text, url, published_on) -> bool:
    capture = (row["details"] or {}).get("capture") or {}
    return (capture.get("text_sha256") == _digest(text) and row["title"] == title and row["published_on"] == published_on
            and capture.get("url") == url)


def _metrics(conn, content_id, metrics, published_on, actor) -> int:
    added = 0
    for m in metrics:
        entry = performance.entry(content_id, on=m.get("on") or published_on, metric=m.get("metric"), value=m.get("value"),
                                  direction=m.get("direction"), source="published final capture", actor=actor)
        added += performance._append(conn, content_id, entry)
    return added


def embedding_text(title: str, text: str) -> str:
    return f"{title}\n\n{text}"[:EMBED_CHARACTERS]


def _embedding(repo, title, text):
    """The final's vector, through the query embedding path, only when encoding is switched on."""
    if not repo.settings.encoding_enabled:
        return None, {"status": "pending", "detail": "Encoding is switched off (ATELIER_ALLOW_ENCODING); the vector is left empty"}
    from ..config import Settings
    from ..search import query
    models = Settings.from_env(database_url=repo.settings.database_url)
    source = embedding_text(title, text)
    found = query.embed_query(source, models=models, storage=repo.settings, purpose="published_final")
    if found.vector is None:
        return None, {"status": "pending", "detail": found.detail}
    return found.vector, {"status": "stored", "model": models.embedding_model, "input_sha256": _digest(source)}


def _answer(row, *, created: bool, metrics_added: int) -> dict:
    return {**_public(row), "created": created, "metrics_added": metrics_added}


def record(repo, brief_id: str, actor, *, channel: str, title: str, text: str, published_on: date, url: str | None = None,
           piece: int = 1, metrics: list[dict] | None = None) -> dict:
    """Record one published final against its approved brief (module docstring). Editors and approvers only."""
    # The role first: whether this brief exists is not for a viewer to learn from the error.
    authorize(repo, actor)
    metrics = list(metrics or [])
    channel, title, text, url = _clean(channel, title, text, url, piece, published_on, metrics)
    ref = source_ref(brief_id, channel, piece)

    def replay(conn, row):
        if not _same(row, title, text, url, published_on):
            raise ValueError(f"A different published final is already recorded for this piece ({row['content_id']}); "
                             "it is kept as recorded")
        added = _metrics(conn, row["content_id"], metrics, published_on, actor)
        return _answer(_existing(conn, ref), created=False, metrics_added=added)

    with repo.connection() as conn:
        approved_brief(conn, brief_id)
        if row := _existing(conn, ref):
            return replay(conn, row)
    # Outside any transaction: a provider call never holds a lock on the brief.
    vector, embedding = _embedding(repo, title, text)
    with repo.connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (ref,))
        brief = approved_brief(conn, brief_id, lock=True)
        if row := _existing(conn, ref):
            return replay(conn, row)
        copy = brief_copy(brief, channel, piece)
        edit = difference(copy, text) if copy else None
        if edit:
            edit = {"field": f"published_{channel}", "channel": channel, "piece": piece, "author": str(actor), **edit}
        content_id = "published_" + hashlib.sha256(ref.encode()).hexdigest()[:24]
        details = {"capture": {"channel": channel, "piece": piece, "url": url, "text_sha256": _digest(text),
                               "brief_hash": brief["approved_hash"], "recorded_by": str(actor)},
                   "edit": edit, "brief_copy": (copy or "")[:MAX_TEXT] or None, "embedding": embedding,
                   **({} if copy else {"note": f"The brief plans no {channel} copy for piece {piece}: no edit is recorded"})}
        record_row = {"content_id": content_id, "published_on": published_on, "channel": channel, "title": title, "text": text,
                      "status": "confirmed", "source_kind": SOURCE_KIND, "source_ref": ref, "brief_id": brief_id,
                      "angle_id": brief["angle_id"], "sibling_group": brief_id, "created_by": str(actor), "details": details,
                      **_facts(brief)}
        if vector is not None:
            import numpy as np
            record_row["embedding"] = np.asarray(vector, dtype=np.float32)
        insert(conn, "published_content", record_row)
        insert(conn, "decisions", {"decision_id": identifier("decision"), "item_kind": "published_content", "item_id": content_id,
                                   "week_id": brief["week_id"], "action": "published_capture", "actor": str(actor),
                                   "author": str(actor), "note": f"Published {channel} recorded against the approved brief",
                                   "expected_hash": brief["approved_hash"],
                                   "details": {"brief_id": brief_id, "source_ref": ref, "edit": bool(edit)}})
        added = _metrics(conn, content_id, metrics, published_on, actor)
        return _answer(_existing(conn, ref), created=True, metrics_added=added)


def pack_source_ref(brief_id: str, piece: str) -> str:
    """The reference of a content pack's published piece (NP.B3): one final per piece of the brief's pack, whichever version
    it was published from."""
    return f"pack:{brief_id}:{piece}"


def record_pack(repo, brief_id: str, actor, *, piece: str, channel: str, platform: str, title: str, pack_copy: str, text: str,
                published_on: date, url: str | None = None, pack_id: str | None = None, manifest_hash: str | None = None) -> dict:
    """A piece of a content pack marked published (NP.B3; the content-packs plan, section 4.1), recorded like a published
    final (`record`), outside the pack's copy: a confirmed `published_content` row with reference `pack:<brief_id>:<piece>`,
    the brief's facts, and `details.edit`, the difference between the pack's copy of the piece and what was published, an
    authored edit by the person who recorded it (the learning loop reads it, `mining.edit_diffs`). The pack's readiness and
    manifest never change. The caller checks the pack and the person's role. Idempotent as `record`: the same final answers
    the same row; a different final for the same piece is refused."""
    title, text = (title or "").strip(), (text or "").strip()
    if not title or not text:
        raise ValueError("A published piece needs its title and its text")
    if len(text) > MAX_TEXT:
        raise ValueError(f"A published final is at most {MAX_TEXT} characters")
    url = (url or "").strip() or None
    if url and (urlsplit(url).scheme not in ("http", "https") or not urlsplit(url).netloc):
        raise ValueError("The link must be an http or https address")
    if published_on > date.today() + timedelta(days=1):
        raise ValueError("A published piece has a publish date on or before today")
    ref = pack_source_ref(brief_id, piece)

    def replay(row):
        if not _same(row, title, text, url, published_on):
            raise ValueError(f"A different published final is already recorded for this piece ({row['content_id']}); "
                             "it is kept as recorded")
        return _answer(row, created=False, metrics_added=0)

    with repo.connection() as conn:
        approved_brief(conn, brief_id)
        if row := _existing(conn, ref):
            return replay(row)
    # Outside any transaction: a provider call never holds a lock on the brief.
    vector, embedding = _embedding(repo, title, text)
    with repo.connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (ref,))
        brief = approved_brief(conn, brief_id, lock=True)
        if row := _existing(conn, ref):
            return replay(row)
        edit = difference(pack_copy, text) if pack_copy else None
        if edit:
            edit = {"field": f"published_{channel}", "channel": channel, "piece": piece, "author": str(actor), "source": "pack", **edit}
        content_id = "published_" + hashlib.sha256(ref.encode()).hexdigest()[:24]
        details = {"capture": {"channel": channel, "platform": platform, "piece": piece, "url": url, "text_sha256": _digest(text),
                               "brief_hash": brief["approved_hash"], "pack_id": pack_id, "manifest_hash": manifest_hash,
                               "recorded_by": str(actor)},
                   "edit": edit, "pack_copy": (pack_copy or "")[:MAX_TEXT] or None, "embedding": embedding}
        record_row = {"content_id": content_id, "published_on": published_on, "channel": channel, "title": title, "text": text,
                      "status": "confirmed", "source_kind": SOURCE_KIND, "source_ref": ref, "brief_id": brief_id,
                      "angle_id": brief["angle_id"], "sibling_group": brief_id, "created_by": str(actor), "details": details,
                      **_facts(brief)}
        if vector is not None:
            import numpy as np
            record_row["embedding"] = np.asarray(vector, dtype=np.float32)
        insert(conn, "published_content", record_row)
        insert(conn, "decisions", {"decision_id": identifier("decision"), "item_kind": "published_content", "item_id": content_id,
                                   "week_id": brief["week_id"], "action": "published_capture", "actor": str(actor),
                                   "author": str(actor), "note": f"Published {channel} recorded from the content pack",
                                   "expected_hash": brief["approved_hash"],
                                   "details": {"brief_id": brief_id, "source_ref": ref, "edit": bool(edit), "pack_id": pack_id}})
        return _answer(_existing(conn, ref), created=True, metrics_added=0)


def listing(repo, brief_id: str) -> dict:
    """The published pieces linked to one brief, newest first (captured finals and L.B7's linked pieces alike)."""
    with repo.connection() as conn:
        if not conn.execute("SELECT 1 FROM content_briefs WHERE brief_id=%s", (brief_id,)).fetchone():
            raise LookupError("Brief not found")
        rows = conn.execute("""SELECT * FROM published_content WHERE brief_id=%s
            ORDER BY published_on DESC NULLS LAST, created_at DESC, content_id""", (brief_id,)).fetchall()
    return {"items": [_public(r) for r in rows]}
