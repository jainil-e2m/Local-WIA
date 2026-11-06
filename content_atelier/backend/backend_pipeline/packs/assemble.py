"""The pack's first stage: assembly from hand-off view v2, with no model call (NP.B1; the content-packs plan, sections 4.2
and 5.1).

- **Five pieces in the v4 leaf shape.** The email, the carousel and three Reels, each piece's `content` the brief's leaves
  with the pack's extra fields beside them (a working title, cover alternates, a CTA kind, a no-offer ending), and
  `brief_copy` the same leaves as approved, for comparing and reverting.
- **Reels by kind, never by position.** The brief's story Reel is `reel_1`, its stance Reel `reel_2`, its b-roll text Reel
  `reel_3`. A kind the brief lacks is left for the finisher (`not_written`, with the reason, until it writes it); a second
  Reel of one kind is source material for the missing kind; a Reel made from an existing clip keeps the brief's copy and
  carries a before-publishing note.
- **Round 2 (`premises`, finisher v3).** Reel 1 is the central story and Reels 2 and 3 each a premise of its own. A brief of
  writer v5.3 maps by its kinds (central, second, third). An earlier brief's story Reel becomes the central story; its stance
  and b-roll Reels retell that story, so they are source material only and the finisher writes Reels 2 and 3 with premises
  of their own (WIA, 26 October: "not a paraphrase of Reel 1").
- **Gate 2's locks** translate by a fixed table where only the Reel index changes (contracts_v2.translate_lock), each
  with its author and whether it was delegated; a person's anchor follows the remap.
- **Finish again** starts from the current pack: its copy, every person's line (Gate 2's and the pack's), its notes and
  their marks, and the brief's copy for comparing.

Everything here is a pure function of the hand-off view (and the previous pack), so a retry assembles the same draft.
"""
from __future__ import annotations

import copy

from ..briefs import paths
from . import contracts_v2 as c2

EMAIL_CTA = {"email_reply": "reply", "reply": "reply", "sales_page": "link", "link": "link", "book_call": "link"}


def _title(text: str | None, fallback: str) -> str:
    """A working title from a Reel's cover (never its creative direction): the cover, without a closing period."""
    title = (text or "").strip().rstrip(".") or fallback
    return title if len(title) <= 120 else title[:117].rstrip() + "..."


def email_cta(cta: dict | None) -> str:
    cta = cta or {}
    if cta.get("choice") == "no_explicit_ask":
        return "none"
    return EMAIL_CTA.get(str(cta.get("track") or "").lower(), "reply" if cta.get("action") else "none")


PREMISE_FIELDS = ("production", "premise", "takeaway", "distinct_because", "timestamps")


def reel_content(piece: dict, *, kind: str | None = None) -> dict:
    """A hand-off v4 Reel piece as pack content. `kind` re-places it (an earlier brief's story Reel as the central story)."""
    copy_, direction = piece.get("copy") or {}, piece.get("direction") or {}
    kind = kind or direction.get("kind") or "story"
    text = direction.get("production") == "on_screen_text" or kind == "broll_text"
    extra = {k: direction[k] for k in PREMISE_FIELDS if direction.get(k) is not None}
    if kind in c2.PREMISE_KINDS and "production" not in extra:
        extra["production"] = "on_screen_text" if text else "face_to_camera"
    return {"kind": kind, "job": direction.get("job") or "", "register": direction.get("register") or (
                "on_screen" if text else "spoken"), **extra,
            "title": _title(copy_.get("cover_text"), c2.LABELS[c2.KIND_KEY.get(kind, "reel_1")]),
            "cover_text": copy_.get("cover_text") or "", "cover_alternates": [],
            "on_screen_hook": copy_.get("on_screen_hook") or copy_.get("cover_text") or "",
            "spoken_opening": copy_.get("spoken_opening"), "script": copy_.get("script"), "screens": copy_.get("screens"),
            "beats": list(direction.get("beats") or []), "personal_lines": list(direction.get("personal_lines") or []),
            "read_time_seconds": int(direction.get("read_time_seconds") or (20 if text else 60)),
            "source": direction.get("source") or "new_script", "caption": copy_.get("caption"),
            "offer_descriptor": direction.get("offer_descriptor"),
            "cta": "offer" if direction.get("offer_descriptor") else "none", "no_offer_ending": None}


def carousel_content(piece: dict) -> dict:
    copy_, direction = piece.get("copy") or {}, piece.get("direction") or {}
    jobs = {s["number"]: s.get("job") or "" for s in direction.get("slides") or []}
    return {"job": direction.get("job") or "", "register": "written", "title": copy_.get("title") or "",
            "slides": [{"number": s["number"], "job": jobs.get(s["number"], ""), "text": s["text"]} for s in copy_.get("slides") or []],
            "caption": copy_.get("caption"), "offer_descriptor": direction.get("offer_descriptor"),
            "cta": "offer" if direction.get("offer_descriptor") else "none", "no_offer_ending": None}


def email_content(piece: dict, cta: dict | None) -> dict:
    copy_, direction = piece.get("copy") or {}, piece.get("direction") or {}
    return {"job": direction.get("job") or "", "register": "written",
            "send_header": direction.get("send_header") or {"date": "To confirm", "send_time": "To confirm", "recipients": "To confirm"},
            "subject_options": list(copy_.get("subject_options") or []), "preview": copy_.get("preview") or "",
            "opening": copy_.get("opening") or "", "body": copy_.get("body") or "", "ending": copy_.get("ending") or "",
            "offer_descriptor": direction.get("offer_descriptor"), "cta": email_cta(cta)}


def piece(key: str, *, origin: str, content: dict | None, brief_key: str | None, reason: str | None = None) -> dict:
    return {"version": c2.VERSION, "key": key, "channel": c2.CHANNEL[key], "label": c2.LABELS[key], "origin": origin,
            "not_written_reason": reason, "brief_key": brief_key, "content": content,
            "brief_copy": copy.deepcopy(content) if origin == "brief" else None, "locks": [], "findings": [], "changes": []}


def notes(handoff: dict) -> list[dict]:
    """Gate 2's before-publishing items with their answers. A client's permission is a note for whoever posts, never a gate:
    a permission item carries `client_permission` (the owner, 24 October)."""
    return [{"id": i["id"], "text": i["text"], "kind": i.get("kind") or "other", "required": bool(i.get("required")),
             "answer": i.get("answer"), "client_permission": (i.get("kind") == "permission"), "done": None}
            for i in handoff.get("before_publishing") or []]


def draft(handoff: dict, *, finish_mode: str, previous: dict | None = None, premises: bool = False) -> dict:
    """The pack before finishing: {"pieces", "brief_map", "sources", "missing", "keep_verbatim", "anchor", "body"}.

    `previous` (Finish again) is {"body": the current pack body, "pieces": {key: piece}}. `premises` (Round 2) is whether the
    finisher writes the central story and two premises of their own (finisher v3)."""
    if handoff.get("handoff_version") != c2.HANDOFF_VERSION:
        raise ValueError("A content pack reads only hand-off view version 2")
    if handoff.get("schema_version") != "brief_document_v4":
        raise ValueError("Re-develop this brief as a v4 brief to get a content pack")
    by_key = {p["key"]: p for p in handoff.get("pieces") or []}
    reels = [p for p in handoff.get("pieces") or [] if p["channel"] == "reel"]
    pieces, brief_map, sources, missing, keep = {}, {}, {}, [], []
    extra_notes = []
    written_with_premises = any((r.get("direction") or {}).get("kind") in c2.PREMISE_KINDS for r in reels)
    if written_with_premises and not premises:
        raise ValueError("This brief has the central story and two premises (writer v5.3); its pack needs finisher v3 "
                         "(prompts.profile.pack_finish)")
    # Under finisher v3 an earlier brief's story Reel is the central story, and its stance and b-roll Reels are only source
    # material: they retell that story, and Reels 2 and 3 need premises of their own.
    retold = premises and not written_with_premises
    for kind in (c2.PREMISE_KINDS if premises else c2.REEL_KINDS):
        key = c2.KIND_KEY[kind]
        if retold and kind != "central":
            missing.append(key)
            pieces[key] = piece(key, origin="not_written", content=None, brief_key=None,
                                reason=f"The brief's {c2.LABELS[key]} retells the central story; the finisher writes a premise "
                                       "of its own")
            continue
        source_kind = "story" if retold else kind
        of_kind = [r for r in reels if (r.get("direction") or {}).get("kind") == source_kind]
        if of_kind:
            first = of_kind[0]
            pieces[key] = piece(key, origin="brief", content=reel_content(first, kind=kind if premises else None),
                                brief_key=first["key"])
            brief_map[first["key"]] = key
            if (first.get("direction") or {}).get("source") == "existing_clip":
                keep.append(key)
                extra_notes.append(f"{c2.LABELS[key]} uses an existing clip: post the clip as approved, with this caption")
        else:
            missing.append(key)
            reason = (f"The brief has no {c2.KIND_LABELS[kind]} Reel and packs.finish_mode is assemble (no model call)"
                      if finish_mode == "assemble" else f"The brief has no {c2.KIND_LABELS[kind]} Reel; the finisher writes it")
            pieces[key] = piece(key, origin="not_written", content=None, brief_key=None, reason=reason)
    # A second Reel of a kind already mapped is source material for a missing kind (section 4.2); under finisher v3 an earlier
    # brief's stance and b-roll Reels are source material for the Reels that take their places.
    for r in reels:
        if r["key"] not in brief_map:
            target = r["key"] if premises and r["key"] in missing else (missing[0] if missing else "reel_1")
            sources.setdefault(target, []).append(r["key"])
    for key, maker in (("carousel", carousel_content), ("email", None)):
        found = by_key.get(key)
        if not found:
            missing.append(key)
            pieces[key] = piece(key, origin="not_written", content=None, brief_key=None,
                                reason=f"The brief has no {key}; re-develop it with the {key} channel")
            continue
        content = email_content(found, handoff.get("cta")) if key == "email" else maker(found)
        pieces[key] = piece(key, origin="brief", content=content, brief_key=key)
        brief_map[key] = key
    _translate_locks(pieces, brief_map, handoff.get("locks") or [], extra_notes)
    anchor = (handoff.get("anchor") or {}).get("key")
    body_notes = notes(handoff) + [{"id": f"N{i}", "text": t, "kind": "pack", "required": False, "answer": None,
                                    "client_permission": False, "done": None} for i, t in enumerate(extra_notes, 1)]
    body = {"version": c2.VERSION, "title": handoff.get("title") or "Content pack", "brief_id": handoff["brief_id"],
            "week_id": handoff["week_id"], "angle_id": handoff["angle_id"], "pillar": handoff.get("purpose"),
            "rank": ((handoff.get("publishing_order") or {}).get("rank")),
            "message_spine": (handoff.get("message_spine") or {}).get("text"), "cta": handoff.get("cta") or {},
            "anchor": brief_map.get(anchor, "reel_1"), "before_publishing": body_notes, "client_quotes": [],
            "stronger_with_permission": [], "pack_notes": [], "change_notes": []}
    if previous:
        return _from_previous(previous, body, sources, keep, premises=premises)
    return {"pieces": pieces, "brief_map": brief_map, "sources": sources, "missing": missing, "keep_verbatim": keep,
            "anchor": body["anchor"], "body": body}


def _translate_locks(pieces: dict, brief_map: dict, locks: list[dict], extra_notes: list[str]) -> None:
    for lock in locks:
        targets = list(c2.PIECE_KEYS) if lock["piece"] == "*" else [brief_map.get(lock["piece"])]
        for key in targets:
            if not key or not pieces.get(key) or pieces[key]["content"] is None:
                if lock["piece"] != "*":
                    extra_notes.append(f"A line written at Gate 2 ({lock['path']}) belongs to a Reel the pack used only as "
                                       "source material; check it is carried")
                continue
            path = lock["leaf"] or "*"
            pieces[key]["locks"].append({"path": path, "author": lock["author"], "delegated": bool(lock.get("delegated")),
                                         "at": lock.get("at"), "origin": "gate_two"})


def _from_previous(previous: dict, body: dict, sources: dict, keep: list, *, premises: bool = False) -> dict:
    """Finish again: the current pack's pieces and every person's line, its notes with their marks. Under finisher v3
    (`premises`) a pack made before it is re-placed: its story Reel is the central story, and its stance and b-roll Reels
    become source material (their copy, in `sources`) for Reels 2 and 3, which the finisher writes with premises of their
    own; a line a person wrote in one of those becomes a before-publishing note, so it is not lost."""
    pieces, carried = {}, []
    sources = {k: list(v) for k, v in sources.items()}
    for key in c2.PIECE_KEYS:
        old = copy.deepcopy(previous["pieces"][key])
        kind = (old.get("content") or {}).get("kind")
        if premises and key == "reel_1" and kind == "story":
            old["content"] = {**old["content"], "kind": "central", "production": "face_to_camera"}
            if old.get("brief_copy"):
                old["brief_copy"] = {**old["brief_copy"], "kind": "central", "production": "face_to_camera"}
        elif premises and kind in ("stance", "broll_text"):
            # The pack's own copy of the Reel (with any person's edits) stands in for the brief's.
            sources[key] = [{"retold": old["content"]}]
            for lock in old.get("locks") or []:
                value = old["content"] if lock["path"] == "*" else paths.get(old["content"], lock["path"]) \
                    if paths.exists(old["content"], lock["path"]) else None
                if value:
                    carried.append(f"A line a person wrote for the earlier {c2.LABELS[key]} was not carried into its new "
                                   f"premise: {value if isinstance(value, str) else lock['path']}")
            old = {**old, "origin": "not_written", "content": None, "brief_copy": None, "locks": [], "brief_key": None,
                   "not_written_reason": f"The earlier {c2.LABELS[key]} retold the central story; the finisher writes a "
                                         "premise of its own"}
        pieces[key] = {**old, "findings": [], "changes": []}
    old_body = previous["body"]
    kept_notes = old_body.get("before_publishing") or body["before_publishing"]
    kept_notes = kept_notes + [{"id": f"N{len(kept_notes) + i}", "text": t, "kind": "pack", "required": False, "answer": None,
                                "client_permission": False, "done": None} for i, t in enumerate(carried, 1)]
    body = {**body, "before_publishing": kept_notes,
            "client_quotes": old_body.get("client_quotes") or [],
            "stronger_with_permission": old_body.get("stronger_with_permission") or [],
            "anchor": old_body.get("anchor") or body["anchor"]}
    if old_body.get("granted"):
        body["granted"] = list(old_body["granted"])
    if old_body.get("recorded_takes"):
        body["recorded_takes"] = dict(old_body["recorded_takes"])
    missing = [k for k, p in pieces.items() if p["content"] is None]
    brief_map = {p["brief_key"]: k for k, p in pieces.items() if p.get("brief_key")}
    attested = [f["resolution"]["note"] for p in previous["pieces"].values() for f in p.get("findings") or []
                if f.get("status") == "attested" and (f.get("resolution") or {}).get("note")]
    # A permission granted earlier (NP.B15) stays evidence when the pack is finished again.
    attested += [g["statement"] for g in old_body.get("granted") or []]
    return {"pieces": pieces, "brief_map": brief_map, "sources": sources, "missing": missing, "keep_verbatim": keep,
            "anchor": body["anchor"], "body": body, "attested": attested}


def locked_paths(p: dict) -> list[str]:
    return [lock["path"] for lock in p.get("locks") or []]
