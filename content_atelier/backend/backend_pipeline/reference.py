"""Reference data: one source for people, the clients list and the glossary (plan 1.B2, 1.B12).

* **people** mirror the confirmed roster. The brand-kit roster items (Phase L) hold the staff facts prompts use (role,
  current or former, name variants) and are the editing surface; saving or retiring one updates the matching `people`
  row in the same transaction (`mirror_roster_key`, called from `knowledge.items.supersede`). `sync_roster` reads the
  confirmed roster items, or the roster document before any are confirmed.
* **clients** come from a reviewed list kept outside the repository (`import_clients`); consent defaults to
  `anonymise_only` and the importer never widens it on an existing client.
* **glossary** terms and their common mis-transcriptions (`normalise/glossary.py` applies them to a search copy).
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

CONSENTS = ("anonymise_only", "may_name", "no_use")


def consent_applies(existing: dict, consent: str, update_consent: bool, *, stated: bool = True) -> bool:
    """Whether a reviewed list's consent replaces an account's: when asked to (`update_consent`), or when the row states a
    consent and the account is the system's own guess from a call (`source` call, N10), which the first reviewed value
    replaces. Otherwise re-running an old list never rewrites a recorded consent."""
    if consent == existing["consent"]:
        return False
    return update_consent or stated and existing.get("source") == "call"
GLOSSARY_KINDS = ("product", "staff", "client", "other")


def _id(prefix: str, key: str) -> str:
    return prefix + hashlib.sha256(key.encode()).hexdigest()[:24]


def person_id_for(roster_key: str) -> str:
    return _id("person_", roster_key)


def _roster_person(entry: dict) -> dict | None:
    """The people row a roster entry stands for, or None for a name that is not a person (an invented name)."""
    state = entry["status"]
    if state == "invented":
        return None
    if state == "not_a_person":
        return {"role": "ai_agent", "status": "current"}
    if state == "outside":
        return {"role": "outside", "status": "current"}
    return {"role": "staff", "status": "current" if state == "current" else "former"}


def _upsert_person(conn, *, roster_key: str, entry: dict) -> str:
    shape = _roster_person(entry)
    existing = conn.execute("SELECT * FROM people WHERE roster_key=%s", (roster_key,)).fetchone()
    if shape is None:
        if existing:
            conn.execute("DELETE FROM people WHERE roster_key=%s", (roster_key,))
            return "removed"
        return "skipped"
    aliases = list(dict.fromkeys(a for a in entry.get("aliases") or [] if a and a != entry["name"]))
    values = (entry["name"], shape["role"], shape["status"], entry.get("role"), json.dumps(aliases))
    if existing:
        if (existing["name"], existing["role"], existing["status"], existing["title"], existing["aliases"]) == (
                entry["name"], shape["role"], shape["status"], entry.get("role"), aliases):
            return "unchanged"
        conn.execute("UPDATE people SET name=%s,role=%s,status=%s,title=%s,aliases=%s,updated_at=now() WHERE roster_key=%s",
                     (*values, roster_key))
        return "updated"
    conn.execute("""INSERT INTO people(person_id,name,role,status,title,aliases,roster_key,source)
        VALUES (%s,%s,%s,%s,%s,%s,%s,'roster')""", (person_id_for(roster_key), values[0], values[1], values[2], values[3],
                                                     values[4], roster_key))
    return "created"


def _entry_from_item(item: dict) -> dict:
    body = item["body"]
    status = {"current": "current", "former": "former", "invented": "invented", "not_a_person": "not_a_person"}.get(body["state"], "outside")
    return {"name": body["name"], "role": body["role"], "status": status,
            "aliases": list(dict.fromkeys([body["name"].split()[0], *body.get("aliases", [])]))}


def mirror_roster_key(conn, key: str, on: date | None = None) -> str | None:
    """Make the people row for one roster key agree with its confirmed item valid on a date. No valid item: no change."""
    from .knowledge import items
    valid = [r for r in items.items_valid_at(conn, "roster_member", on or date.today()) if r["key"] == key]
    if not valid:
        return None
    return _upsert_person(conn, roster_key=key, entry=_entry_from_item(valid[-1]))


def roster_entries(conn, root, on: date | None = None) -> list[tuple[str, dict]]:
    """(roster key, entry) for the roster in force: confirmed items valid on the date, else the roster document."""
    from .knowledge import items
    from .knowledge_base import team_roster
    on = on or date.today()
    if items.table_ready(conn):
        rows = items.items_valid_at(conn, "roster_member", on)
        if rows:
            return [(r["key"], _entry_from_item(r)) for r in rows]
    return [(items.key_for("roster_member", e["name"]), e) for e in team_roster(Path(root))]


def sync_roster(conn, root, on: date | None = None) -> dict:
    """Bring `people` into agreement with the roster in force: create, update, or remove the rows it owns."""
    entries = roster_entries(conn, root, on)
    counts = {"created": 0, "updated": 0, "unchanged": 0, "removed": 0, "skipped": 0}
    for key, entry in entries:
        counts[_upsert_person(conn, roster_key=key, entry=entry)] += 1
    # A roster row no longer in force stays (passage maps may name it) but is marked former rather than current.
    keys = [k for k, _ in entries]
    conn.execute("UPDATE people SET status='former',updated_at=now() WHERE source='roster' AND role='staff' AND status='current' "
                 "AND roster_key<>ALL(%s)", (keys,))
    return counts


def roster_agreement(conn, root, on: date | None = None) -> dict:
    """The roster's staff and `people`'s staff, side by side: every roster staff member has a row and the reverse."""
    roster_staff = {k: e["name"] for k, e in roster_entries(conn, root, on) if _roster_person(e) and _roster_person(e)["role"] == "staff"}
    people = {r["roster_key"] or "person:" + r["person_id"]: r["name"]
              for r in conn.execute("SELECT person_id,name,roster_key FROM people WHERE role='staff'").fetchall()}
    return {"missing_from_people": sorted(v for k, v in roster_staff.items() if k not in people),
            "missing_from_roster": sorted(v for k, v in people.items() if k not in roster_staff),
            "staff": len(roster_staff), "agree": set(roster_staff) == set(people)}


def _rows(path: Path) -> list[dict]:
    path = Path(path)
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["clients"] if isinstance(data, dict) else data
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def import_clients(conn, path, *, update_consent: bool = False) -> dict:
    """Load the reviewed client list (CSV or JSON: name, aliases, consent, status, notes). Idempotent by name.

    A new client's consent is the list's value, else `anonymise_only`. An existing client's consent changes only with
    `update_consent`, so re-running an old list cannot quietly widen what may be said in public. When a consent changes, the
    client's stored moments are re-derived in the same transaction (`moments.recheck`), and the result names the clients."""
    created = updated = unchanged = 0
    consent_changed: list[str] = []
    for raw in _rows(path):
        name = (raw.get("name") or "").strip()
        if not name:
            raise ValueError("Every client needs a name")
        aliases = raw.get("aliases") or []
        if isinstance(aliases, str):
            aliases = [a.strip() for a in aliases.replace("|", ";").split(";") if a.strip()]
        consent = (raw.get("consent") or "anonymise_only").strip()
        status = (raw.get("status") or "active").strip()
        if consent not in CONSENTS:
            raise ValueError(f"Consent for {name} must be one of: " + ", ".join(CONSENTS))
        if status not in ("active", "former"):
            raise ValueError(f"Status for {name} must be active or former")
        existing = conn.execute("SELECT * FROM clients WHERE lower(name)=lower(%s)", (name,)).fetchone()
        if not existing:
            conn.execute("INSERT INTO clients(client_id,name,aliases,consent,status,notes) VALUES (%s,%s,%s,%s,%s,%s)",
                         (_id("client_", name.lower()), name, json.dumps(aliases), consent, status, raw.get("notes") or None))
            created += 1
            continue
        fields = {"aliases": json.dumps(aliases), "status": status, "notes": raw.get("notes") or existing["notes"]}
        if consent_applies(existing, consent, update_consent, stated=bool(raw.get("consent"))):
            fields["consent"] = consent
        if existing.get("source") == "call":
            fields["source"] = "reviewed_list"  # the reviewed list now speaks for the account the system added
        if all(existing[k] == (json.loads(v) if k == "aliases" else v) for k, v in fields.items()):
            unchanged += 1
            continue
        sets = ",".join(f"{k}=%s" for k in fields)
        conn.execute(f"UPDATE clients SET {sets},updated_at=now() WHERE client_id=%s", (*fields.values(), existing["client_id"]))
        updated += 1
        if fields.get("consent", existing["consent"]) != existing["consent"]:
            consent_changed.append(existing["client_id"])
    # What may be said about a client's stored moments follows the consent at once (2.B4), not at the next manual recheck.
    result = {"created": created, "updated": updated, "unchanged": unchanged}
    if consent_changed:
        from .moments import recheck, store
        rederived = sum(recheck.recheck_in(conn, client_id=c)["changed"] for c in consent_changed) if store.has_ledger(conn) else 0
        result.update({"consent_changed": consent_changed, "moments_rederived": rederived})
    return result


def add_glossary_term(conn, term: str, kind: str, variants=(), notes: str | None = None) -> str:
    if kind not in GLOSSARY_KINDS:
        raise ValueError("A glossary kind is one of: " + ", ".join(GLOSSARY_KINDS))
    term = term.strip()
    if not term:
        raise ValueError("A glossary term needs its spelling")
    variants = list(dict.fromkeys(v.strip() for v in variants if v and v.strip() and v.strip().lower() != term.lower()))
    term_id = _id("term_", term.lower())
    conn.execute("""INSERT INTO glossary_terms(term_id,term,kind,variants,notes) VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (term_id) DO UPDATE SET kind=EXCLUDED.kind,variants=EXCLUDED.variants,
        notes=COALESCE(EXCLUDED.notes,glossary_terms.notes),status='active',updated_at=now()""",
                 (term_id, term, kind, json.dumps(variants), notes))
    return term_id


def import_glossary(conn, path) -> dict:
    """Load a glossary file (JSON list of {term, kind, variants, notes}, or CSV with variants separated by ;)."""
    count = 0
    for raw in _rows(Path(path)):
        variants = raw.get("variants") or []
        if isinstance(variants, str):
            variants = [v for v in variants.split(";")]
        add_glossary_term(conn, raw["term"], raw.get("kind") or "other", variants, raw.get("notes"))
        count += 1
    return {"terms": count}
