"""Changing a content pack: versions, edits, locks, readiness and published marks (NP.B3; the content-packs plan, sections
4.1, 4.5, 5.3 and 5.6).

Every mutation checks the person's role first (edit, revert and published: `edit_packs`; a clearance, an attestation, the
decision and Finish again: `approve_packs`), then locks the governing brief, the pack and its pieces in that order
(`model.get`, `model.pieces`), and refuses a v1 pack, a superseded pack, a pack whose run is active (409 `pack_running`), a
pack still finishing, and a stale manifest hash (409 `stale_pack`, "The pack changed; reload it"). Each is idempotent on its
request id (`production_common.receipt`).

- **A new version** (`model.write_version`) for each edit, revert and attestation: the five pieces copied with the changed
  one replaced, the change record in the pack body, the deterministic checks re-run and stored, and the approval reset, so
  an edit after Ready starts in review. Each is a decision on the pack (`item_kind = pack`, R45).
- **An edit** writes leaves by dotted path relative to the piece's copy (`briefs/paths.py`), each one a line a person may
  edit (`contracts_v2.is_editable`); every changed line is locked as that person's (R56: no model step changes it again),
  and a fidelity finding on the line it changed is cleared. **A revert** puts the brief's line back, locked as the person's
  choice.
- **A clearance** marks a before-publishing note done (P1..., N1...) or a client quote cleared (Q1...), with the person, the
  date and exactly the reference given (never invented). It updates the current version in place: the marks are outside the
  manifest (`model.manifest_body`), so readiness never changes.
- **An attestation** (R57) clears an open fidelity finding as attested, with the person's statement.
- **Ready to publish** needs no ready blocker (`views.ready_blockers`); before-publishing notes and client quotes never block
  it. It binds the approval to the manifest. Back to review returns it to pending.
- **Finish again** queues a new run from the brief (no new instruction; every person's line kept by the finisher), which
  supersedes this version.
- **NP-7's passes** queue such a run with a person's own input (packs/passes.py): a recorded take on a face-to-camera Reel
  (`edit_packs`) or granted items and stated facts (`approve_packs`).
- **Published** records the piece through capture (`knowledge/capture.record_pack`), outside the pack's copy: the pack stays
  as it was, ready or in review.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import date

from psycopg.types.json import Jsonb
from pydantic import ValidationError

from ..briefs import paths
from ..gates.roles import access_for
from ..production_common import ProductionError, receipt, save_receipt
from . import checks, model, queue, views
from . import contracts_v2 as c2
from .runtime_v2 import mode_for


def authorize(repo, actor, capability: str) -> None:
    if not actor or not access_for(repo.settings, actor).can(capability):
        raise PermissionError("Only a pack approver can do this" if capability == "approve_packs"
                              else "Only a pack editor or approver can do this")


def _stamp(repo, actor) -> dict:
    return {"by": str(actor), "at": model.now_iso(), "delegated": model.delegated(repo.settings, actor)}


def _locked(conn, pack_id: str, expected: str | None = None) -> tuple[dict, dict]:
    try:
        pack = model.get(conn, pack_id, lock=True)
    except LookupError:
        raise ProductionError("Pack not found", "not_found", 404) from None
    rows = model.pieces(conn, pack_id, lock=True)
    if not model.is_v2(pack):
        raise ProductionError("This is a version 1 pack; it cannot be changed here", "pack_v1", 409)
    if model.superseded(conn, pack_id):
        raise ProductionError("A newer version of this pack exists; reload it", "stale_pack", 409)
    if model.run_active(conn, pack.get("production_run_id")):
        raise ProductionError("The pack is being finished; wait until it is done", "pack_running", 409)
    if pack.get("content_body") is None:
        raise ProductionError("The pack has not finished; retry it from its brief", "pack_unfinished", 409)
    if expected is not None and pack.get("manifest_hash") != expected:
        raise ProductionError("The pack changed; reload it", "stale_pack", 409)
    return pack, rows


def _mutate(repo, pack_id: str, payload, actor, operation: str, capability: str, apply) -> dict:
    authorize(repo, actor, capability)
    data = payload.model_dump(mode="json")
    op = f"pack-{operation}:{pack_id}"
    with repo.connection() as conn:
        saved = receipt(conn, payload.request_id, actor, op, data)
        if saved is not None:
            return saved
        pack, rows = _locked(conn, pack_id, payload.expected_manifest_hash)
        return save_receipt(conn, payload.request_id, actor, op, data, apply(conn, pack, rows))


def _saved(conn, pack_id: str) -> dict:
    pack = conn.execute("SELECT * FROM content_packs WHERE pack_id=%s", (pack_id,)).fetchone()
    state, _ = model.state_of(conn, pack)
    return {"pack_id": pack["pack_id"], "manifest_hash": pack.get("manifest_hash"), "state": state, "run_id": pack.get("production_run_id")}


def _piece(rows: dict, key: str, *, written: bool = True) -> dict:
    row = rows.get(key)
    if not row or not row.get("content_body"):
        raise ProductionError(f"The pack has no {c2.LABELS[key]}", "not_found", 404)
    piece = copy.deepcopy(row["content_body"])
    if written and not piece.get("content"):
        raise ProductionError(f"{c2.LABELS[key]} was not written; it has no copy to change", "not_written", 409)
    return piece


def _path(raw: str) -> str:
    try:
        return paths.canonical(raw)
    except ValueError as exc:
        raise ProductionError(str(exc), "invalid_path", 422) from exc


def _editable(channel: str, path: str, label: str) -> None:
    if not c2.is_editable(channel, path):
        raise ProductionError(f"{path} is not a line a person edits in {label}; editable: " + ", ".join(c2.EDITABLE[channel]),
                              "not_editable", 422)


def _validate(channel: str, content: dict, label: str) -> None:
    try:
        c2.COPY_MODELS[channel].model_validate(content)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in exc.errors()[:3])
        raise ProductionError(f"The change does not fit {label}: {problems}", "invalid_edit", 422) from exc


def _text(value) -> str | None:
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _value(content: dict, path: str):
    return paths.get(content, path) if paths.exists(content, path) else None


def _locks(existing: list[dict], changed: list[str], stamp: dict) -> list[dict]:
    """A person's lock on each changed line, replacing an earlier lock on the same line (R56)."""
    kept = [lock for lock in existing or [] if lock.get("path") not in set(changed)]
    return kept + [c2.Lock(path=p, author=stamp["by"], delegated=stamp["delegated"], at=stamp["at"], origin="pack").model_dump(mode="json")
                   for p in changed]


def _clear(piece: dict, content: dict, changed: list[str], stamp: dict, note: str) -> list[dict]:
    """A fidelity finding on a line a person changed, or whose sentence is no longer in the piece, is cleared (R57)."""
    text = checks.piece_text(piece["key"], content)
    out = []
    for f in piece.get("findings") or []:
        f = dict(f)
        if f.get("status") == "open":
            touched = bool(f.get("path")) and any(paths.overlaps(f["path"], p) for p in changed if _parses(f["path"]))
            if touched or (f.get("sentence") and f["sentence"] not in text):
                f["status"] = "cleared"
                f["resolution"] = c2.Resolution(by=stamp["by"], at=stamp["at"], delegated=stamp["delegated"], note=note).model_dump(mode="json")
        out.append(f)
    return out


def _parses(path: str) -> bool:
    try:
        paths.parse(path)
        return True
    except ValueError:
        return False


def _new_version(repo, conn, pack: dict, rows: dict, actor, *, kind: str, changed: dict[str, dict], lines: list[str], action: str,
                 note: str | None = None) -> dict:
    """Write the version these changed pieces make (section 5.3) and record the decision; answer PackSavedV2."""
    brief = views.brief_of(conn, pack)
    bodies = {k: r["content_body"] for k, r in rows.items()}
    bodies.update(changed)
    body = copy.deepcopy(pack["content_body"])
    body["client_quotes"] = [*(body.get("client_quotes") or []), *checks.missing_client_quotes(body, bodies, brief)]
    stamp = _stamp(repo, actor)
    body["change"] = c2.ChangeRecord(kind=kind, by=stamp["by"], at=stamp["at"], delegated=stamp["delegated"], pieces=sorted(changed),
                                     paths=list(lines), note=note).model_dump(mode="json")
    found = checks.findings(conn, {**pack, "content_body": body}, bodies, brief)
    written = model.write_version(repo, conn, parent=pack, pack_id=None, run_id=pack["production_run_id"], brief=brief, body=body,
                                  piece_bodies=bodies, actor=str(actor), validation=checks.result(found))
    new = conn.execute("SELECT * FROM content_packs WHERE pack_id=%s", (written["pack_id"],)).fetchone()
    model.record_decision(conn, new, action=action, actor=str(actor), settings=repo.settings, note=note,
                          details={"kind": kind, "pieces": sorted(changed), "paths": list(lines), "supersedes": pack["pack_id"]})
    repo.event(conn, pack["production_run_id"], "pack_version_created", f"Pack version saved ({kind})",
               details={"pack_id": new["pack_id"], "supersedes": pack["pack_id"], "actor": str(actor), "pieces": sorted(changed)})
    return _saved(conn, new["pack_id"])


def edit(repo, pack_id: str, key: str, payload, actor) -> dict:
    """PATCH /packs/{id}/pieces/{key} -> PackSavedV2: a person's edit, each changed line locked as theirs."""
    def apply(conn, pack, rows):
        piece = _piece(rows, key)
        channel, label, content = piece["channel"], piece["label"], piece["content"]
        changes = {}
        for raw, value in payload.changes.items():
            path = _path(raw)
            _editable(channel, path, label)
            if not paths.exists(content, path):
                raise ProductionError(f"{label} has no line {path}", "no_such_line", 422)
            changes[path] = value
        new, lines = paths.apply(content, changes, set(c2.EDITABLE[channel]))
        if not lines:
            raise ProductionError("Nothing changed: every line already has that text", "no_change", 409)
        _validate(channel, new, label)
        stamp = _stamp(repo, actor)
        # Why, in the person's words (Round 2, WIA's section 9): kept on each changed line and the decision, for the weekly
        # learning loop (knowledge/mining.py).
        reason = (payload.reason or "").strip() or None
        piece.update(content=new, locks=_locks(piece.get("locks"), lines, stamp), findings=_clear(piece, new, lines, stamp, "Edited by a person"),
                     changes=[*(piece.get("changes") or []),
                              *(c2.Change(path=p, kind="edited", before=_text(_value(content, p)), after=_text(_value(new, p)),
                                          note=reason).model_dump(mode="json")
                                for p in lines)])
        return _new_version(repo, conn, pack, rows, actor, kind="edit", changed={key: piece}, lines=lines, action="pack_edit",
                            note=reason)
    return _mutate(repo, pack_id, payload, actor, "edit", "edit_packs", apply)


def revert(repo, pack_id: str, key: str, payload, actor) -> dict:
    """POST /packs/{id}/pieces/{key}/revert -> PackSavedV2: the brief's line put back, locked as the person's choice."""
    def apply(conn, pack, rows):
        piece = _piece(rows, key)
        channel, label, content = piece["channel"], piece["label"], piece["content"]
        brief_copy = piece.get("brief_copy")
        if not brief_copy:
            raise ProductionError(f"{label} was written by the finisher; it has no brief line to go back to", "no_brief_copy", 409)
        new, lines = content, []
        for raw in payload.paths:
            path = _path(raw)
            _editable(channel, path, label)
            if not paths.exists(brief_copy, path):
                raise ProductionError(f"The brief has no line {path} in {label}", "no_brief_line", 409)
            if not paths.exists(new, path):
                raise ProductionError(f"{label} has no line {path} to put the brief's line back in", "no_such_line", 409)
            value = paths.get(brief_copy, path)
            if paths.get(new, path) != value:
                new = paths.put(new, path, value)
                lines.append(path)
        if not lines:
            raise ProductionError("Nothing changed: those lines already read as the brief's", "no_change", 409)
        _validate(channel, new, label)
        stamp = _stamp(repo, actor)
        piece.update(content=new, locks=_locks(piece.get("locks"), lines, stamp),
                     findings=_clear(piece, new, lines, stamp, "The brief's line was put back by a person"),
                     changes=[*(piece.get("changes") or []),
                              *(c2.Change(path=p, kind="reverted", before=_text(_value(content, p)), after=_text(_value(new, p))).model_dump(mode="json")
                                for p in lines)])
        return _new_version(repo, conn, pack, rows, actor, kind="revert", changed={key: piece}, lines=lines, action="pack_revert")
    return _mutate(repo, pack_id, payload, actor, "revert", "edit_packs", apply)


def clearance(repo, pack_id: str, payload, actor) -> dict:
    """POST /packs/{id}/clearances -> PackSavedV2: a before-publishing note done or a client quote cleared, on this version in
    place (outside the manifest)."""
    def apply(conn, pack, rows):
        body = copy.deepcopy(pack["content_body"])
        item = payload.item_id.strip()
        stamp = _stamp(repo, actor)
        done = c2.Done(by=stamp["by"], at=stamp["at"], delegated=stamp["delegated"], reference=payload.reference,
                       note=payload.note).model_dump(mode="json")
        if re.fullmatch(r"Q\d+", item):
            target, mark, what = next((q for q in body.get("client_quotes") or [] if q.get("quote_id") == item), None), "cleared", "client quote"
        else:
            target, mark, what = next((n for n in body.get("before_publishing") or [] if n.get("id") == item), None), "done", "note"
        if target is None:
            raise ProductionError(f"The pack has no {what} {item}", "not_found", 404)
        if target.get(mark):
            raise ProductionError(f"{item} is already marked {'cleared' if mark == 'cleared' else 'done'}", "already_done", 409)
        target[mark] = done
        c2.PackBody.model_validate(body)
        if model.manifest({**pack, "content_body": body}, rows.values()) != pack["manifest_hash"]:
            raise ValueError("A clearance would change the pack's manifest; it was not saved")
        conn.execute("UPDATE content_packs SET content_body=%s,content_hash=%s,updated_by=%s,updated_at=now() WHERE pack_id=%s",
                     (Jsonb(body), model.body_hash(body), str(actor), pack["pack_id"]))
        model.record_decision(conn, pack, action="pack_clearance", actor=str(actor), settings=repo.settings, note=payload.note,
                              details={"item_id": item, "reference": payload.reference})
        repo.event(conn, pack["production_run_id"], "pack_clearance", f"{item} marked {mark}",
                   details={"pack_id": pack["pack_id"], "actor": str(actor), "item_id": item})
        return _saved(conn, pack["pack_id"])
    return _mutate(repo, pack_id, payload, actor, "clearance", "approve_packs", apply)


def attest(repo, pack_id: str, finding_id: str, payload, actor) -> dict:
    """POST /packs/{id}/findings/{finding_id}/attest -> PackSavedV2: an open fidelity finding attested true (R57), or an
    editorial finding kept with the person's reason (Round 2)."""
    def apply(conn, pack, rows):
        if finding_id.startswith("check_"):
            raise ProductionError("A check's finding clears when its line is edited; it cannot be attested", "not_attestable", 409)
        key = next((k for k, r in rows.items() if any(f.get("finding_id") == finding_id
                                                      for f in (r.get("content_body") or {}).get("findings") or [])), None)
        if key is None:
            raise ProductionError("The pack has no such finding", "not_found", 404)
        piece = _piece(rows, key, written=False)
        target = next(f for f in piece["findings"] if f["finding_id"] == finding_id)
        if target.get("status") != "open":
            raise ProductionError("That finding is already resolved", "already_resolved", 409)
        stamp = _stamp(repo, actor)
        # An editorial finding (Round 2) is kept with the person's reason; it never becomes a fact for later checks.
        target["status"] = "kept" if target.get("kind") == "editorial" else "attested"
        target["resolution"] = c2.Resolution(by=stamp["by"], at=stamp["at"], delegated=stamp["delegated"],
                                             note=payload.statement).model_dump(mode="json")
        return _new_version(repo, conn, pack, rows, actor, kind="attest", changed={key: piece},
                            lines=[target["path"]] if target.get("path") else [], action="pack_attest", note=payload.statement)
    return _mutate(repo, pack_id, payload, actor, "attest", "approve_packs", apply)


def decide(repo, pack_id: str, payload, actor) -> dict:
    """POST /packs/{id}/decision -> PackSavedV2: ready to publish (bound to the manifest), or back to review."""
    def apply(conn, pack, rows):
        if payload.decision == "ready_to_publish":
            if pack["approval_status"] == "approved":
                raise ProductionError("The pack is already ready to publish", "already_ready", 409)
            if model.manifest(pack, rows.values()) != pack["manifest_hash"]:
                raise ProductionError("The pack changed; reload it", "stale_pack", 409)
            brief = views.brief_of(conn, pack)
            bodies = checks.bodies_of(rows)
            blockers = views.ready_blockers(bodies, checks.findings(conn, pack, bodies, brief))
            if blockers:
                raise ProductionError("Not ready to publish yet: " + "; ".join(blockers), "pack_blocked", 409)
            conn.execute("""UPDATE content_packs SET approval_status='approved',approved_hash=manifest_hash,approved_by=%s,approved_at=now(),
                review_note=%s,updated_by=%s,updated_at=now() WHERE pack_id=%s""", (str(actor), payload.note, str(actor), pack["pack_id"]))
            model.record_decision(conn, pack, action="pack_ready_to_publish", actor=str(actor), settings=repo.settings, note=payload.note,
                                  disposition="approve")
            repo.event(conn, pack["production_run_id"], "pack_ready_to_publish", "Pack marked ready to publish",
                       details={"pack_id": pack["pack_id"], "actor": str(actor), "manifest_hash": pack["manifest_hash"]})
        else:
            if pack["approval_status"] != "approved":
                raise ProductionError("The pack is already in review", "already_in_review", 409)
            conn.execute("""UPDATE content_packs SET approval_status='pending',approved_hash=NULL,approved_by=NULL,approved_at=NULL,
                review_note=%s,updated_by=%s,updated_at=now() WHERE pack_id=%s""", (payload.note, str(actor), pack["pack_id"]))
            model.record_decision(conn, pack, action="pack_in_review", actor=str(actor), settings=repo.settings, note=payload.note)
            repo.event(conn, pack["production_run_id"], "pack_in_review", "Pack returned to review",
                       details={"pack_id": pack["pack_id"], "actor": str(actor)})
        return _saved(conn, pack["pack_id"])
    return _mutate(repo, pack_id, payload, actor, "decision", "approve_packs", apply)


def finish_again(repo, pack_id: str, payload, actor) -> dict:
    """POST /packs/{id}/finish -> PackSavedV2: a new run from the brief that supersedes this version (state finishing)."""
    def apply(conn, pack, rows):
        brief = views.brief_of(conn, pack)
        try:
            started = queue.queue_in_transaction(repo, conn, brief, actor, mode_for(repo.settings), trigger="finish_again",
                                                 supersedes=pack["pack_id"], previous_manifest=pack["manifest_hash"])
        except (ValueError, PermissionError) as exc:
            raise ProductionError(str(exc), "pack_not_started", 409) from exc
        model.record_decision(conn, pack, action="pack_finish_again", actor=str(actor), settings=repo.settings,
                              details={"pack_id": started["pack_id"], "run_id": started["run_id"]})
        return {"pack_id": started["pack_id"], "manifest_hash": None, "state": "finishing", "run_id": started["run_id"]}
    return _mutate(repo, pack_id, payload, actor, "finish", "approve_packs", apply)


def _pass(repo, conn, pack: dict, actor, pass_: dict, action: str) -> dict:
    """Queue a person-started pass (NP-7) as a new run that supersedes this version (state finishing)."""
    if repo.settings.pack_finish_mode == "assemble":
        raise ProductionError("Packs are assembled without a model call (packs.finish_mode assemble); this needs the finisher",
                              "pack_not_started", 409)
    brief = views.brief_of(conn, pack)
    try:
        started = queue.queue_in_transaction(repo, conn, brief, actor, mode_for(repo.settings), trigger=action,
                                             supersedes=pack["pack_id"], previous_manifest=pack["manifest_hash"], pass_=pass_)
    except (ValueError, PermissionError) as exc:
        raise ProductionError(str(exc), "pack_not_started", 409) from exc
    model.record_decision(conn, pack, action=action, actor=str(actor), settings=repo.settings,
                          details={"pack_id": started["pack_id"], "run_id": started["run_id"],
                                   **({"piece": pass_["piece"]} if pass_.get("piece") else {}),
                                   **({"grants": pass_["grants"]} if pass_.get("grants") else {})})
    return {"pack_id": started["pack_id"], "manifest_hash": None, "state": "finishing", "run_id": started["run_id"]}


def recorded_take(repo, pack_id: str, key: str, payload, actor) -> dict:
    """POST /packs/{id}/pieces/{key}/recorded -> PackSavedV2: the post-recording pass (NP.B14). What Whitney said becomes
    the Reel's script, locked as the person's; the caption and covers are written from it in a new run."""
    def apply(conn, pack, rows):
        from .passes import SPOKEN
        if key not in SPOKEN:
            raise ProductionError("A recorded take goes on a face-to-camera Reel (Reel 1 or Reel 2); Reel 3 is b-roll text",
                                  "not_spoken", 422)
        _piece(rows, key)
        stamp = _stamp(repo, actor)
        pass_ = {"kind": "caption", "piece": key, "said": payload.said.strip(), **stamp}
        return _pass(repo, conn, pack, actor, pass_, "pack_recorded_take")
    return _mutate(repo, pack_id, payload, actor, "recorded", "edit_packs", apply)


def refinish(repo, pack_id: str, payload, actor) -> dict:
    """POST /packs/{id}/refinish -> PackSavedV2: finish again with a permission (NP.B15). Each granted item or stated fact
    is evidence for the finisher and the check, attested with the person and date (R57)."""
    def apply(conn, pack, rows):
        items = pack["content_body"].get("stronger_with_permission") or []
        stamp = _stamp(repo, actor)
        grants = []
        for g in payload.grants:
            item = None
            if g.item_id:
                n = int(g.item_id[1:]) - 1
                if not 0 <= n < len(items):
                    raise ProductionError(f"The pack has no item {g.item_id} under Stronger with permission", "not_found", 404)
                item = items[n]
            grants.append(c2.Grant(item_id=g.item_id, item=item, statement=g.statement.strip(), **stamp).model_dump(mode="json"))
        return _pass(repo, conn, pack, actor, {"kind": "refinish", "grants": grants, **stamp}, "pack_refinish")
    return _mutate(repo, pack_id, payload, actor, "refinish", "approve_packs", apply)


def _title(piece: dict, pack: dict) -> str:
    content = piece.get("content") or {}
    if piece.get("channel") == "email":
        return ((content.get("subject_options") or [None])[0] or pack["title"]).strip()
    return (content.get("title") or pack["title"]).strip()


def published(repo, pack_id: str, key: str, payload, actor) -> dict:
    """POST /packs/{id}/pieces/{key}/published -> PackPublishedV2: the piece recorded through capture, outside the manifest."""
    from ..knowledge.capture import record_pack
    authorize(repo, actor, "edit_packs")
    data = payload.model_dump(mode="json")
    op = f"pack-published:{pack_id}:{key}"
    with repo.connection() as conn:
        saved = receipt(conn, payload.request_id, actor, op, data)
        if saved is not None:
            return saved
        pack, rows = _locked(conn, pack_id)
        piece = _piece(rows, key)
    try:
        captured = record_pack(repo, pack["source_brief_id"], actor, piece=key, channel=piece["channel"], platform=payload.channel,
                               title=_title(piece, pack), pack_copy=checks.piece_text(key, piece["content"]), text=payload.final_text,
                               published_on=date.fromisoformat(payload.published_on), url=payload.url, pack_id=pack["pack_id"],
                               manifest_hash=pack["manifest_hash"])
    except LookupError as exc:
        raise ProductionError(str(exc), "not_found", 404) from exc
    except ValueError as exc:
        raise ProductionError(str(exc), "not_recorded", 409) from exc
    with repo.connection() as conn:
        saved = receipt(conn, payload.request_id, actor, op, data)
        if saved is not None:
            return saved
        state, _ = model.state_of(conn, conn.execute("SELECT * FROM content_packs WHERE pack_id=%s", (pack_id,)).fetchone())
        return save_receipt(conn, payload.request_id, actor, op, data,
                            {"pack_id": pack_id, "piece": key, "content_id": captured["content_id"], "state": state})
