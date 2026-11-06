"""The one writer of the moments ledger (plan 2.B2, 2.B4, 2.B10; section 4.8).

Every path that stores moments goes through `save`: the weekly extraction (the whole-week prompt and the weekly scene
profile), the per-document extraction job, and the import of saved responses. A moment saved by any of them carries the
document it came from, who said the anchor line and in what role, the client, what may be said about it (consent), whether
its quote binds the source, and the deterministic checks (`moments/checks.py`), so the columns do not depend on the path.

Identity does not change: a verified moment's ID is the extractor's content hash (`Pipeline._moment`), so storing the same
scene again is a no-op, and an ID that meets different content raises (the evidence is preserved, never rewritten).
A moment that does not bind is stored as an unverified record (`quote_verified = false`, no evidence references, never proof).

A document extracted under a newer extractor version has its older moments set `is_current = false`: they stay readable
for the cards and briefs that cite them. Extractor versions are profile ids that start with their date, so they order
by string; an imported moment's version is `imported:<original profile>` and orders by the profile.
"""
from __future__ import annotations

import hashlib

from ..store import canonical_hash
from . import checks, types

IMPORTED_PREFIX = "imported:"
TEXT_DEFAULT_REASON = "The quote does not bind to its source"


def version_key(extractor_version: str | None) -> str:
    """The sortable part of an extractor version: the profile, without the `imported:` marker."""
    return (extractor_version or "").removeprefix(IMPORTED_PREFIX)


def unverified_id(scope: str, local_key: str, draft: dict) -> str:
    """The ID of an unverified record: its scope (a run, or a document and extractor), the extractor's local key and the
    draft, so storing it again is a no-op. Migration 008 loads the weekly path's earlier ones as md5(run_id:local_key)."""
    return "unverified_" + hashlib.md5(f"{scope}:{local_key}:{canonical_hash(draft)[:12]}".encode()).hexdigest()[:24]


def passage_text(record: dict, passage: dict) -> str:
    return record["original_text"][passage["start"]:passage["end"]]


def evidence_refs(moment, records: list[dict]) -> list[dict]:
    """The exact references of a moment's context passages into the admitted originals; raises if the quote does not resolve."""
    locations = {p["passage_id"]: (r, p) for r in records for p in r["passage_map"]}
    refs = []
    for ref in moment.context_span_ids:
        record, p = locations[ref]
        refs.append({"transcript_id": record["transcript_id"], "passage_id": ref, "start": p["start"], "end": p["end"],
                     "roles": ["anchor", "context"] if ref in moment.anchor_span_ids else ["context"]})
    if not any(moment.quote in passage_text(*locations[x]) for x in moment.anchor_span_ids):
        raise ValueError("Quote does not resolve into admitted originals")
    return refs


def derive_columns(*, body: dict, document: dict, anchors: list[dict], context: list[dict], client_consent: str | None,
                   roster: list[dict] | None = None) -> dict:
    """The ledger columns that depend on the document, the roles and the client: speaker, role, type, evidence kind, consent
    and the checks. Used for a new moment and again, with the same inputs, by `moments recheck`."""
    quote = body.get("quote") or ""
    anchor_texts = [passage_text(document, p) for p in anchors]
    chosen = next((p for p, t in zip(anchors, anchor_texts, strict=True) if quote in t), anchors[0] if anchors else None)
    speaker = checks.speaker_of(document, chosen, roster)
    anchor_ids = {p["passage_id"] for p in anchors}
    assessed = checks.assess(
        original_type=body.get("moment_type"), speaker_role=speaker["role"], sensitivity=body.get("sensitivity"),
        client_consent=client_consent,
        fields={"quote": quote, "context_summary": body.get("context_summary") or "", "proposition": body.get("proposition") or ""},
        anchor_texts=anchor_texts, context_texts=[passage_text(document, p) for p in context if p["passage_id"] not in anchor_ids])
    destination = (body.get("discovery") or {}).get("destination")
    return {"document_id": document["transcript_id"], "speaker_label": speaker["label"], "speaker_id": speaker["person_id"],
            "speaker_role": speaker["role"], "client_id": document.get("client_id"), "occurred_at": document.get("occurred_at"),
            "moment_type": assessed["moment_type"], "evidence_kind": assessed["evidence_kind"],
            "consent_status": assessed["consent_status"],
            # An internal meeting's scene shows how WIA works and is never a client's evidence (D24, 1.B13's extension).
            "evidence_class": evidence_class(document),
            # The columns have CHECKs; a value outside the vocabulary (an older body) is left null rather than refused.
            "sensitivity": body.get("sensitivity") if body.get("sensitivity") in types.SENSITIVITIES else None,
            "destination": destination if destination in types.DESTINATIONS else None, "checks": assessed["checks"]}


def evidence_class(document: dict) -> str:
    """team_practice for a scene from an internal meeting (only WIA's team speaks), else call (migration 010)."""
    return "team_practice" if document.get("call_type") == "internal" else "call"


def client_consents(conn, records: list[dict]) -> dict[str, str]:
    ids = sorted({r.get("client_id") for r in records if r.get("client_id")})
    if not ids:
        return {}
    return {r["client_id"]: r["consent"] for r in conn.execute("SELECT client_id,consent FROM clients WHERE client_id=ANY(%s)", (ids,))}


def known_people(conn, person_ids) -> set[str]:
    ids = sorted({p for p in person_ids if p})
    return {r["person_id"] for r in conn.execute("SELECT person_id FROM people WHERE person_id=ANY(%s)", (ids,))} if ids else set()


def has_ledger(conn) -> bool:
    """Whether `key_moments` has the ledger columns (migration 008). Every migrated database does; the shared test database
    that stays at the baseline schema for the older suites does not."""
    return bool(conn.execute("""SELECT EXISTS (SELECT 1 FROM information_schema.columns
        WHERE table_schema=current_schema() AND table_name='key_moments' AND column_name='document_id') AS ok""").fetchone()["ok"])


def same_evidence(old: dict, body: dict, refs: list) -> bool:
    """Whether a stored row holds the evidence a moment with its ID would store. A key whose value is null says the same as
    no key: a row written before a field existed (`discovery` before 13 October) is the same moment."""
    def present(value: dict) -> dict:
        return {k: v for k, v in (value or {}).items() if v is not None}
    return present(old["moment_body"]) == present(body) and old["evidence_refs"] == refs


def save_legacy(conn, moments, records: list[dict], *, run_id, week_id) -> dict:
    """The writer before migration 008: body and evidence only."""
    from ..repository import insert
    saved = []
    for m in moments:
        body = m.model_dump(mode="json", exclude={"moment_id", "source_ids", "anchor_span_ids", "context_span_ids"})
        refs = evidence_refs(m, records)
        old = conn.execute("SELECT moment_body,evidence_refs FROM key_moments WHERE moment_id=%s", (m.moment_id,)).fetchone()
        if old and not same_evidence(old, body, refs):
            raise ValueError("Moment identity conflicts with preserved evidence")
        insert(conn, "key_moments", {"moment_id": m.moment_id, "week_id": week_id, "run_id": run_id, "moment_body": body,
                                     "evidence_refs": refs}, conflict=True)
        saved.append(m.moment_id)
    return {"moment_ids": saved, "unverified_ids": [], "documents": []}


def save(conn, moments, records: list[dict], *, run_id: str | None, week_id: str | None, extractor_version: str,
         unverified=(), repairs=(), provenance: dict[str, dict] | None = None, unverified_scope: str | None = None,
         roster: list[dict] | None = None, supersede: dict | None = None) -> dict:
    """Store verified moments and unverified records. Returns the IDs stored (new or already there) and the documents touched.

    `repairs` are the quote repairs (each names its `moment_id`); `provenance` maps a moment ID to extra keys for its checks
    (`extraction`, `imported_from`); `unverified` are `{local_key, reason, draft}` records, stored under `unverified_scope`
    (the run for the weekly paths, the document and extractor for a document's extraction). `supersede` marks this call as a
    complete, later extraction of its documents under `extractor_version` (see `settle_currency`)."""
    from ..repository import insert
    if not has_ledger(conn):
        return save_legacy(conn, moments, records, run_id=run_id, week_id=week_id)
    repaired = {r["moment_id"]: r for r in repairs}
    consents = client_consents(conn, records)
    people = known_people(conn, [(r.get("speaker_map") or {}).get(label, {}).get("person_id")
                                 for r in records for label in (r.get("speaker_map") or {})])
    locations = {p["passage_id"]: (r, p) for r in records for p in r["passage_map"]}
    saved, owned, shared, touched = [], [], [], {}
    for m in moments:
        body = m.model_dump(mode="json", exclude={"moment_id", "source_ids", "anchor_span_ids", "context_span_ids"})
        refs = evidence_refs(m, records)
        old = conn.execute("SELECT moment_body,evidence_refs,extractor_version,checks FROM key_moments WHERE moment_id=%s",
                           (m.moment_id,)).fetchone()
        if old and not same_evidence(old, body, refs):
            raise ValueError("Moment identity conflicts with preserved evidence")
        saved.append(m.moment_id)
        document = locations[m.anchor_span_ids[0]][0]
        touched[document["transcript_id"]] = document
        if old:
            # The same scene from another extractor is the same moment: the row stays as it was, currency included (that
            # extractor's own saves decide it), and says who else produced it.
            if old["extractor_version"] == extractor_version:
                owned.append(m.moment_id)
            else:
                shared.append(m.moment_id)
                note_other_extractor(conn, m.moment_id, old, extractor_version, (provenance or {}).get(m.moment_id, {}))
            continue
        owned.append(m.moment_id)
        columns = derive_columns(body=body, document=document, anchors=[locations[x][1] for x in m.anchor_span_ids],
                                 context=[locations[x][1] for x in m.context_span_ids],
                                 client_consent=consents.get(document.get("client_id")), roster=roster)
        if columns["speaker_id"] not in people:
            columns["speaker_id"] = None
        columns["checks"] = {**columns["checks"], **(provenance or {}).get(m.moment_id, {})}
        insert(conn, "key_moments", {"moment_id": m.moment_id, "week_id": week_id, "run_id": run_id, "moment_body": body,
                                     "evidence_refs": refs, "extractor_version": extractor_version, "quote_verified": True,
                                     "quote_repair": repaired.get(m.moment_id), **columns}, conflict=True)
    kept = []
    for record in unverified:
        draft = record["draft"]
        document = next((locations[x][0] for x in (draft.get("anchor_span_ids") or []) if x in locations), None)
        if document is None and len(records) == 1:
            document = records[0]
        moment_id = unverified_id(unverified_scope or run_id or "", record["local_key"], draft)
        kept.append(moment_id)
        if document is not None:
            touched.setdefault(document["transcript_id"], document)
        assessed = checks.assess_unverified(original_type=draft.get("moment_type"), sensitivity=draft.get("sensitivity"),
                                            client_consent=consents.get((document or {}).get("client_id")))
        insert(conn, "key_moments", {
            "moment_id": moment_id, "week_id": week_id, "run_id": run_id, "moment_body": draft, "evidence_refs": [],
            "document_id": document["transcript_id"] if document else None, "moment_type": assessed["moment_type"],
            "sensitivity": draft.get("sensitivity") if draft.get("sensitivity") in ("public_candidate", "internal_only", "unknown") else None,
            "occurred_at": (document or {}).get("occurred_at"), "client_id": (document or {}).get("client_id"),
            "extractor_version": extractor_version, "quote_verified": False,
            "unverified_reason": record.get("reason") or TEXT_DEFAULT_REASON, "consent_status": assessed["consent_status"],
            "evidence_class": evidence_class(document or {}),
            "checks": {**assessed["checks"], "local_key": record["local_key"], **record.get("provenance", {})}},
            conflict=True)
    verified = {locations[m.anchor_span_ids[0]][0]["transcript_id"] for m in moments}
    for document_id in touched:
        settle_currency(conn, document_id, extractor_version, owned + kept, retire_older=document_id in verified,
                        supersede=supersede, shared=shared)
    return {"moment_ids": saved, "unverified_ids": kept, "documents": sorted(touched)}


def note_other_extractor(conn, moment_id: str, old: dict, extractor_version: str, provenance: dict) -> bool:
    """Record on an existing moment that another extractor version produced the identical scene (`checks.also_extracted_by`),
    with that extraction's provenance. A report or a recall for that version then counts it. Idempotent."""
    if old["extractor_version"] == extractor_version:
        return False
    checks_ = old["checks"] or {}
    also = list(checks_.get("also_extracted_by") or [])
    if any(a.get("extractor_version") == extractor_version for a in also):
        return False
    from psycopg.types.json import Jsonb
    conn.execute("UPDATE key_moments SET checks=%s WHERE moment_id=%s",
                 (Jsonb({**checks_, "also_extracted_by": [*also, {"extractor_version": extractor_version, **provenance}]}), moment_id))
    return True


def extracted_by(alias: str = "m") -> str:
    """SQL for 'this extractor version produced the moment', for `%(v)s` and `%(contains)s` (see `extracted_by_params`)."""
    return (f"(%(v)s::text IS NULL OR {alias}.extractor_version=%(v)s OR {alias}.checks->'also_extracted_by' @> %(contains)s::jsonb)")


def extracted_by_params(extractor_version: str | None) -> dict:
    from psycopg.types.json import Jsonb
    return {"v": extractor_version, "contains": Jsonb([{"extractor_version": extractor_version}] if extractor_version else [])}


def align_currency(conn, document_id: str, included: bool) -> int:
    """Bring a document's moments in line with whether it is included. An excluded document has no current moment (they stay
    readable for the cards and briefs that cite them); an included one has its newest verified extractor's moments current,
    except the ones a later extraction under the same extractor replaced (`checks.superseded_by`). Returns how many rows
    changed. Idempotent."""
    if not included:
        return conn.execute("UPDATE key_moments SET is_current=false WHERE document_id=%s AND is_current", (document_id,)).rowcount
    wanted = """(NOT (checks ? 'superseded_by') AND regexp_replace(extractor_version,'^imported:','') COLLATE "C" >=
        COALESCE((SELECT max(regexp_replace(extractor_version,'^imported:','') COLLATE "C") FROM key_moments
                  WHERE document_id=%(d)s AND quote_verified AND extractor_version IS NOT NULL
                    AND NOT (checks ? 'superseded_by')), '' COLLATE "C"))"""
    return conn.execute(f"""UPDATE key_moments SET is_current={wanted}
        WHERE document_id=%(d)s AND extractor_version IS NOT NULL AND is_current IS DISTINCT FROM {wanted}""",
                        {"d": document_id}).rowcount


def settle_currency(conn, document_id: str, extractor_version: str, new_ids: list[str], *, retire_older: bool = True,
                    supersede: dict | None = None, shared: list[str] = ()) -> dict:
    """Keep exactly the newest extractor's moments of a document current. Older ones stay readable, not current; if a newer
    extractor's moments already exist, the ones just stored are the ones that are not current. Only verified moments decide
    which extractor is newer, and only a document that gained a verified moment retires its older ones: a newer extraction that
    found nothing it can prove does not hide what an older one proved.

    `supersede` (the per-document extraction passes its extraction key and job) says the moments just stored are a complete,
    later extraction of the document under the same extractor version: that version's other moments of the document (an
    earlier extraction with an older knowledge base, say) are then replaced, marked `checks.superseded_by`, and stay readable
    but not current, so one document never has two current sets of scenes. A scene the later extraction reproduced is the same
    moment (one identity) and stays current.

    `shared` are rows another extractor stored that this one produced again (the same identity): they are left exactly as
    they are, neither deciding which extractor is newer nor retired, so an import never changes another extractor's rows."""
    from psycopg.types.json import Jsonb
    mine = version_key(extractor_version)
    rows = conn.execute("""SELECT DISTINCT extractor_version FROM key_moments WHERE document_id=%s AND quote_verified
        AND extractor_version IS NOT NULL AND moment_id <> ALL(%s::text[])""", (document_id, [*new_ids, *shared])).fetchall()
    others = [version_key(r["extractor_version"]) for r in rows]
    newer = any(v > mine for v in others)
    older = [r["extractor_version"] for r in rows if version_key(r["extractor_version"]) < mine]
    if new_ids:
        # A moment just produced again is not superseded, whatever an earlier extraction decided.
        conn.execute("UPDATE key_moments SET is_current=%s,checks=checks - 'superseded_by' WHERE moment_id=ANY(%s::text[]) AND document_id=%s",
                     (not newer, new_ids, document_id))
    retired = replaced = 0
    if older and retire_older:
        retired = conn.execute("""UPDATE key_moments SET is_current=false WHERE document_id=%s AND is_current
            AND extractor_version=ANY(%s::text[]) AND moment_id <> ALL(%s::text[])""", (document_id, older, [*new_ids, *shared])).rowcount
    if supersede and retire_older:
        replaced = conn.execute("""UPDATE key_moments SET is_current=false,checks=checks || jsonb_build_object('superseded_by', %s::jsonb)
            WHERE document_id=%s AND extractor_version=%s AND moment_id <> ALL(%s::text[]) AND NOT (checks ? 'superseded_by')""",
                                (Jsonb(supersede), document_id, extractor_version, [*new_ids, *shared])).rowcount
    return {"document_id": document_id, "retired": retired, "replaced": replaced, "stored_as_current": not newer}
