"""Identities (plan 1.B12's extension, Phase N8): people and client accounts, with the facts a privacy rule reads.

The glossary made names findable; it did not say who a name is. Here a name becomes a person or an account:

* **aliases**: every way the records write the name (a meeting handle such as "aliepler", a nickname, the spelling the
  person uses, a mis-heard transcription such as "iver"), so a transcript label resolves to one person and one account.
  Two people who share a first name stay two identities: a first name alone resolves only when one person owns it
  (normalise/speakers.py).
* **pronouns**, recorded only from evidence (the 13 October packs misgendered a prospect);
* **staff dates**: a former team member's leaving date, so copy never presents them as current;
* **naming**: an account's consent (anonymise by default, O3), and two flags no consent overrides: `do_not_name` (never in
  public copy) and `do_not_link` (published work the person or account must never be tied to, with the markers that
  identify it: a client whose anonymised case study WIA published must never be named or linked to it).

The list is reviewed by a person (D21; under the delegation the engineer, recorded as delegated) and kept under
`research/`; `import_file` loads it and `apply` re-normalises the documents whose speakers or client it changes, which
re-derives their scenes' client, role and consent (moments/recheck.py). `notes` is what the strategist, the brief writer and
the checks receive; `copy_findings` is the check: a never-name identity in public copy, or a do-not-link marker in copy that
refers to that identity or is built on its calls, is a blocking finding.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from .reference import CONSENTS, _id, consent_applies

PRONOUNS = ("she/her", "he/him", "they/them")
CLIENT_STATUSES = ("active", "former", "prospect")
PERSON_ROLES = ("client", "prospect", "outside", "vendor")
# What each naming state lets copy do, as the strategist and the writer read it.
NAMING_TEXT = {"may_name": "may be named in public copy",
               "anonymise": "anonymise: never name them or their business in public copy (describe the role instead)",
               "never_name": "never name them or their business in public copy, whatever anyone asks",
               "no_use": "do not use this account's material in public copy at all"}


def person_id_for(name: str, client: str | None) -> str:
    return _id("person_", f"identity:{name.strip().lower()}|{(client or '').strip().lower()}")


def client_id_for(name: str) -> str:
    # The same identifier the reviewed client list gives a client (reference.import_clients), so both loaders meet.
    return _id("client_", name.strip().lower())


def _aliases(raw, name: str) -> list[str]:
    if isinstance(raw, str):
        raw = [a for a in raw.replace("|", ";").split(";")]
    return list(dict.fromkeys(a.strip() for a in raw or [] if a and a.strip() and a.strip().lower() != name.lower()))


def _links(raw) -> list[dict]:
    links = []
    for item in raw or []:
        what = (item.get("what") or "").strip()
        markers = [m.strip() for m in item.get("markers") or [] if m and m.strip()]
        if not what or not markers:
            raise ValueError("A do-not-link entry needs what it is and at least one marker that identifies it")
        links.append({"what": what, "markers": markers, "reason": (item.get("reason") or "").strip() or None})
    return links


def _reviewed(entry: dict, default: dict) -> dict:
    evidence = entry.get("evidence") or entry.get("basis") or []
    return {**default, "basis": [str(e) for e in (evidence if isinstance(evidence, list) else [evidence])]}


def import_file(conn, path, *, actor: str, update_consent: bool = False) -> dict:
    """Load a reviewed identities file: {reviewed: {by, at, note}, clients: [...], people: [...], staff: [...]}.

    clients: {name, aliases, business, status (active|former|prospect), consent, do_not_name, do_not_link, notes, evidence}.
    people: {name, role (client|prospect|outside|vendor), client, aliases, pronouns, do_not_name, do_not_link, evidence}.
    staff: {name, pronouns, joined_on, left_on}: dates and pronouns for roster members (the roster owns the rest).

    Idempotent by name. Consent is never widened on an existing client unless `update_consent` (as reference.import_clients);
    the two flags only ever go on through a file, so turning one off is a deliberate edit of the reviewed list."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    review = {"by": actor, "at": date.today().isoformat(), **{k: v for k, v in (data.get("reviewed") or {}).items() if k in ("by", "at", "note")}}
    counts = {"clients_created": 0, "clients_updated": 0, "people_created": 0, "people_updated": 0, "staff_updated": 0}
    consent_changed: list[str] = []
    names: dict[str, str] = {}
    for raw in data.get("clients") or []:
        name = (raw.get("name") or "").strip()
        if not name:
            raise ValueError("Every client needs a name")
        status = (raw.get("status") or "active").strip()
        consent = (raw.get("consent") or "anonymise_only").strip()
        if status not in CLIENT_STATUSES:
            raise ValueError(f"Status for {name} must be one of: " + ", ".join(CLIENT_STATUSES))
        if consent not in CONSENTS:
            raise ValueError(f"Consent for {name} must be one of: " + ", ".join(CONSENTS))
        client_id = client_id_for(name)
        names[name.lower()] = client_id
        fields = {"name": name, "aliases": json.dumps(_aliases(raw.get("aliases"), name)), "business": raw.get("business") or None,
                  "status": status, "do_not_name": bool(raw.get("do_not_name")), "do_not_link": json.dumps(_links(raw.get("do_not_link"))),
                  "notes": raw.get("notes") or None, "reviewed": json.dumps(_reviewed(raw, review))}
        existing = conn.execute("SELECT * FROM clients WHERE client_id=%s OR lower(name)=lower(%s)", (client_id, name)).fetchone()
        if not existing:
            conn.execute("""INSERT INTO clients(client_id,name,aliases,business,status,consent,do_not_name,do_not_link,notes,reviewed,source)
                VALUES (%(client_id)s,%(name)s,%(aliases)s,%(business)s,%(status)s,%(consent)s,%(do_not_name)s,%(do_not_link)s,%(notes)s,
                %(reviewed)s,'reviewed_identities')""", {**fields, "client_id": client_id, "consent": consent})
            counts["clients_created"] += 1
            continue
        names[name.lower()] = existing["client_id"]
        if consent_applies(existing, consent, update_consent, stated=bool(raw.get("consent"))):
            fields["consent"] = consent
            consent_changed.append(existing["client_id"])
        if existing.get("source") == "call":
            fields["source"] = "reviewed_identities"  # the reviewed file now speaks for the account the system added
        conn.execute(f"UPDATE clients SET {','.join(f'{k}=%({k})s' for k in fields)},updated_at=now() WHERE client_id=%(id)s",
                     {**fields, "id": existing["client_id"]})
        counts["clients_updated"] += 1
    for raw in data.get("people") or []:
        name = (raw.get("name") or "").strip()
        role = (raw.get("role") or "").strip()
        if not name or role not in PERSON_ROLES:
            raise ValueError(f"Every person needs a name and a role ({', '.join(PERSON_ROLES)}): {raw!r}")
        pronouns = raw.get("pronouns") or None
        if pronouns not in (None, *PRONOUNS):
            raise ValueError(f"Pronouns for {name} must be one of: " + ", ".join(PRONOUNS))
        client = (raw.get("client") or "").strip() or None
        client_id = None
        if client:
            client_id = names.get(client.lower()) or (conn.execute("SELECT client_id FROM clients WHERE lower(name)=lower(%s)",
                                                                   (client,)).fetchone() or {}).get("client_id")
            if not client_id:
                raise ValueError(f"{name}'s account {client!r} is not in the clients list")
        if client_id and role not in ("client", "prospect"):
            raise ValueError(f"{name} is tied to an account, so their role is client or prospect")
        person_id = person_id_for(name, client)
        rostered = conn.execute("SELECT person_id,aliases,title,notes FROM people WHERE roster_key IS NOT NULL AND lower(name)=lower(%s)",
                                (name,)).fetchone()
        if rostered:
            # An outside person the roster already holds (a referrer, a partner): the roster owns the row, so the list adds the
            # spellings the transcripts use (a device label), the pronouns and the flags to it. A later `people sync` resets the
            # roster's own aliases, so the list is loaded again after it (DEPLOYMENT.md).
            conn.execute("""UPDATE people SET aliases=%s,pronouns=%s,do_not_name=%s,do_not_link=%s,reviewed=%s,updated_at=now()
                WHERE person_id=%s""", (json.dumps(list(dict.fromkeys([*(rostered["aliases"] or []), *_aliases(raw.get("aliases"), name)]))),
                                        pronouns, bool(raw.get("do_not_name")), json.dumps(_links(raw.get("do_not_link"))),
                                        json.dumps(_reviewed(raw, review)), rostered["person_id"]))
            counts["people_updated"] += 1
            continue
        fields = {"name": name, "role": role, "client_id": client_id, "aliases": json.dumps(_aliases(raw.get("aliases"), name)),
                  "pronouns": pronouns, "do_not_name": bool(raw.get("do_not_name")), "do_not_link": json.dumps(_links(raw.get("do_not_link"))),
                  "title": raw.get("title") or None, "notes": raw.get("notes") or None, "reviewed": json.dumps(_reviewed(raw, review))}
        if conn.execute("SELECT 1 FROM people WHERE person_id=%s", (person_id,)).fetchone():
            conn.execute(f"UPDATE people SET {','.join(f'{k}=%({k})s' for k in fields)},updated_at=now() WHERE person_id=%(id)s",
                         {**fields, "id": person_id})
            counts["people_updated"] += 1
        else:
            conn.execute(f"""INSERT INTO people(person_id,{','.join(fields)},source)
                VALUES (%(id)s,{','.join(f'%({k})s' for k in fields)},'manual')""", {**fields, "id": person_id})
            counts["people_created"] += 1
    for raw in data.get("staff") or []:
        name = (raw.get("name") or "").strip()
        row = conn.execute("SELECT person_id FROM people WHERE role='staff' AND lower(name)=lower(%s)", (name,)).fetchone()
        if not row:
            raise ValueError(f"{name} is not a staff member on the roster (people sync first)")
        pronouns = raw.get("pronouns") or None
        if pronouns not in (None, *PRONOUNS):
            raise ValueError(f"Pronouns for {name} must be one of: " + ", ".join(PRONOUNS))
        conn.execute("""UPDATE people SET pronouns=COALESCE(%s,pronouns),joined_on=COALESCE(%s,joined_on),left_on=COALESCE(%s,left_on),
            reviewed=%s,updated_at=now() WHERE person_id=%s""",
                     (pronouns, raw.get("joined_on"), raw.get("left_on"), json.dumps(_reviewed(raw, review)), row["person_id"]))
        counts["staff_updated"] += 1
    _check_aliases(conn)
    if consent_changed:
        from .moments import recheck, store
        if store.has_ledger(conn):
            counts["moments_rederived"] = sum(recheck.recheck_in(conn, client_id=c)["changed"] for c in consent_changed)
        counts["consent_changed"] = consent_changed
    return counts


def _check_aliases(conn) -> None:
    """Two identities may share a first name, but never a full spelling: a label must resolve to one person or none."""
    owners: dict[str, set[str]] = {}
    for row in conn.execute("SELECT person_id,name,aliases FROM people WHERE role IN ('client','prospect','outside','vendor')"):
        for spelling in {row["name"], *(row["aliases"] or [])}:
            owners.setdefault(_norm(spelling), set()).add(row["person_id"])
    shared = sorted(k for k, v in owners.items() if len(v) > 1 and k)
    if shared:
        raise ValueError("These spellings belong to more than one person; keep each on one identity: " + ", ".join(shared))


def _norm(text: str) -> str:
    from .normalise.speakers import normal
    return normal(text or "")


# ---- applying the list to the documents ----------------------------------------------------------------------------------

def affected(conn) -> list[dict]:
    """Normalised documents whose speakers or client the identity list now resolves differently from what is stored."""
    from .documents.jobs import detect_client
    from .normalise import speakers
    from .settings_store import value as setting
    resolver = speakers.Resolver.from_database(conn, setting("documents.staff_email_domains", conn))
    people = {p["person_id"]: p for p in conn.execute("SELECT person_id,client_id FROM people").fetchall()}
    clients = conn.execute("SELECT client_id,name,aliases FROM clients").fetchall()
    out = []
    for doc in conn.execute("SELECT * FROM transcripts WHERE normalised_at IS NOT NULL ORDER BY transcript_id").fetchall():
        mapping = speakers.speaker_map(doc, resolver, doc["call_type"])
        client = detect_client(doc, mapping, clients, people) if doc["call_type"] in speakers.CLIENT_CALLS | {"prospect"} else None
        if mapping != (doc["speaker_map"] or {}) or client != doc["client_id"]:
            out.append({"transcript_id": doc["transcript_id"], "title": doc["title"], "client_before": doc["client_id"],
                        "client_after": client, "speakers_changed": mapping != (doc["speaker_map"] or {})})
    return out


def apply(repo, *, dry_run: bool = False) -> dict:
    """Re-normalise every document the list changes (no model call: a call type a model placed is kept, since the request it
    was placed on is unchanged), so its speaker map, client, chunk headers and scenes' client, role and consent follow."""
    from .documents.jobs import normalise
    with repo.connection() as conn:
        changes = affected(conn)
    if dry_run:
        return {"applied": False, "documents": len(changes), "changes": changes}
    done = [normalise(repo, c["transcript_id"]) for c in changes]
    return {"applied": True, "documents": len(done), "changes": changes,
            "chunks_added": sum((d.get("chunks") or {}).get("added", 0) for d in done)}


# ---- what the strategist, the writer and the checks read -----------------------------------------------------------------

def naming_of(consent: str | None, do_not_name: bool) -> str:
    if do_not_name:
        return "never_name"
    return {"may_name": "may_name", "no_use": "no_use"}.get(consent or "", "anonymise")


def _spellings(name: str, aliases) -> list[str]:
    return list(dict.fromkeys([name, *(aliases or [])]))


def _mentioned(spelling: str, text: str) -> bool:
    """A spelling written in a text. A one-word spelling counts only as written with a capital (so the prospect "rose" is not
    every "rose" in a call) and a lower-case handle ("aliepler") only exactly; a longer name in any case."""
    spelling = spelling.strip()
    if len(spelling) < 3:
        return False
    if " " in spelling:
        return re.search(r"(?<![A-Za-z0-9])" + re.escape(spelling) + r"(?![A-Za-z0-9])", text, re.I) is not None
    if spelling[0].isupper():
        return re.search(r"(?<![A-Za-z0-9])" + re.escape(spelling) + r"(?![A-Za-z0-9])", text) is not None
    if re.fullmatch(r"[a-z]+", spelling) and spelling in COMMON_WORDS:
        return False
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(spelling) + r"(?![A-Za-z0-9])", text) is not None


# Lower-case transcript labels that are also ordinary words: they resolve a speaker label, never a mention in text.
COMMON_WORDS = frozenset({"rose", "judy", "jenny", "jana", "bri", "maddie", "scott", "julie", "lauren", "skyler", "teresa"})


def notes(conn, *, document_ids=(), texts=(), client_ids=()) -> list[dict]:
    """The identities a packet needs, in a stable order: every client or outside person who speaks in the documents (their
    speaker maps), the documents' accounts, `client_ids`, every former team member the text mentions, every person or account
    whose name or alias the documents' text or `texts` mention, and always every identity never to be named or linked (the
    check must catch them wherever copy brings them in). Staff in force are left out: the knowledge base's roster carries them."""
    document_ids = sorted(set(document_ids))
    docs = conn.execute("SELECT transcript_id,client_id,speaker_map,original_text FROM transcripts WHERE transcript_id=ANY(%s)",
                        (document_ids,)).fetchall() if document_ids else []
    corpus = "\n".join([*(d["original_text"] or "" for d in docs), *(t for t in texts if t)])
    people = conn.execute("""SELECT p.*,c.name AS client_name,c.consent AS client_consent,c.do_not_name AS client_do_not_name
        FROM people p LEFT JOIN clients c USING (client_id) ORDER BY p.person_id""").fetchall()
    clients = conn.execute("SELECT * FROM clients ORDER BY client_id").fetchall()
    speaking = {a.get("person_id") for d in docs for a in (d["speaker_map"] or {}).values() if a.get("person_id")}
    labels: dict[str, set[str]] = {}
    for d in docs:
        for label, a in (d["speaker_map"] or {}).items():
            if a.get("person_id") and label:
                labels.setdefault(a["person_id"], set()).add(label)
    accounts = {d["client_id"] for d in docs if d["client_id"]} | set(client_ids)
    out = []
    for p in people:
        if p["role"] in ("staff", "ai_agent") and p["status"] == "current":
            continue
        heard = sorted(labels.get(p["person_id"], set()) | {s for s in _spellings(p["name"], p["aliases"]) if _mentioned(s, corpus)})
        former_staff = p["role"] == "staff" and p["status"] == "former"
        guarded = bool(p["do_not_name"] or p.get("do_not_link"))
        if not (p["person_id"] in speaking or heard or guarded or (former_staff and _mentioned(p["name"].split()[0], corpus))):
            continue
        if p["client_id"]:
            accounts.add(p["client_id"])
        naming = naming_of(p["client_consent"], bool(p["do_not_name"] or p["client_do_not_name"])) if p["role"] in ("client", "prospect") \
            else ("never_name" if p["do_not_name"] else "anonymise" if p["role"] in ("outside", "vendor") else "may_name")
        out.append({"kind": "person", "id": p["person_id"], "name": p["name"], "role": "former staff" if former_staff else p["role"],
                    "account": p["client_name"], "heard_as": heard, "spellings": _spellings(p["name"], p["aliases"]),
                    "pronouns": p.get("pronouns"), "left_on": p["left_on"].isoformat() if p.get("left_on") else None,
                    "naming": naming, "never_link": _links(p.get("do_not_link"))})
    for c in clients:
        heard = sorted(s for s in _spellings(c["name"], c["aliases"]) if _mentioned(s, corpus))
        if c["client_id"] not in accounts and not heard and not (c["do_not_name"] or c.get("do_not_link")):
            continue
        out.append({"kind": "account", "id": c["client_id"], "name": c["name"], "role": c["status"], "business": c.get("business"),
                    "heard_as": heard, "spellings": _spellings(c["name"], c["aliases"]), "naming": naming_of(c["consent"], bool(c["do_not_name"])),
                    "never_link": _links(c.get("do_not_link"))})
    return out


def prompt_lines(identities: list[dict]) -> list[str]:
    """One line per identity for a prompt: who a name is, their pronouns and status, and what copy may do with them."""
    lines = []
    for i in identities:
        heard = [h for h in i.get("heard_as") or [] if h != i["name"]]
        who = f"{', '.join(heard)} = {i['name']}" if heard else i["name"]
        if i["kind"] == "account":
            what = f"{who}: a WIA account ({i['role']}{', ' + i['business'] if i.get('business') else ''})"
        elif i["role"] == "former staff":
            what = f"{who}: a former WIA team member{' (left ' + _day(i['left_on']) + ')' if i.get('left_on') else ''}; never present them as current, credit \"our team\""
        else:
            what = f"{who}: {i['role']}{' at ' + i['account'] if i.get('account') else ''}"
        if i.get("pronouns"):
            what += f"; pronouns {i['pronouns']}"
        if i["role"] != "former staff":
            what += f"; {NAMING_TEXT[i['naming']]}"
        for link in i.get("never_link") or []:
            what += f"; never link them to {link['what']}"
        lines.append(f"- {what}.")
    return lines


def _day(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def writer_view(identities: list[dict]) -> list[dict]:
    """The writer's field: who each name is, pronouns, status and naming, without the markers the check uses."""
    return [{k: v for k, v in {"name": i["name"], "heard_as": [h for h in i.get("heard_as") or [] if h != i["name"]] or None,
                                "who": i["role"] + (f" at {i['account']}" if i.get("account") else ""), "pronouns": i.get("pronouns"),
                                "left_wia": _day(i["left_on"]) if i.get("left_on") else None, "naming": NAMING_TEXT.get(i["naming"])
                                if i["role"] != "former staff" else "never present as current; credit \"our team\"",
                                "never_link_to": [link["what"] for link in i.get("never_link") or []] or None}.items() if v}
            for i in identities]


# ---- the check -----------------------------------------------------------------------------------------------------------

def copy_findings(fields: dict[str, str], identities: list[dict], *, evidence_ids=(), where: str = "copy") -> list[dict]:
    """Blocking findings for public copy (`fields`: name -> text). `evidence_ids` are the person and account ids the copy is
    built on (the speakers and accounts of its evidence), so a marker of a do-not-link identity is caught even when the copy
    leaves the name out: anonymising a case-study client does not unlink her if the copy carries the case study's figures."""
    findings, built_on = [], set(evidence_ids)
    for i in identities or []:
        spellings = i.get("spellings") or [i["name"]]
        named = {f: s for f, text in fields.items() if text for s in spellings if _mentioned(s, text)}
        if i.get("naming") == "never_name" and named:
            for field, spelling in named.items():
                findings.append({"kind": "do_not_name", "severity": "blocking", "field": field,
                                 "message": f"{where.capitalize()} names {spelling!r} ({i['name']}), who must never be named in public copy"})
        refers = bool(named) or i.get("id") in built_on
        for link in i.get("never_link") or []:
            for field, text in fields.items():
                hit = next((m for m in link["markers"] if text and _marker(m, text)), None)
                if hit and refers:
                    findings.append({"kind": "do_not_link", "severity": "blocking", "field": field,
                                     "message": f"{where.capitalize()} built on {i['name']} carries {hit!r}, which links them to "
                                                f"{link['what']}; they must never be linked to it"})
    return findings


def _marker(marker: str, text: str) -> bool:
    """A marker in a text: case-insensitive, and a figure such as "$70K" also as "70K", "70k" or "$70,000"."""
    if re.search(r"(?<![A-Za-z0-9])" + re.escape(marker) + r"(?![A-Za-z0-9])", text, re.I):
        return True
    figure = re.fullmatch(r"\$?(\d+)[kK]", marker.strip())
    if figure:
        n = figure.group(1)
        return re.search(rf"(?<![\d,.])\$?{n}(?:[kK]|,000)(?![\d])", text) is not None
    return False


def ids_for(identities: list[dict], *, document_ids=(), conn=None) -> set[str]:
    """The identity ids a set of documents is about: its accounts and the people who speak in it."""
    if conn is None or not document_ids:
        return set()
    rows = conn.execute("SELECT client_id,speaker_map FROM transcripts WHERE transcript_id=ANY(%s)", (sorted(set(document_ids)),)).fetchall()
    found = {r["client_id"] for r in rows if r["client_id"]}
    found |= {a.get("person_id") for r in rows for a in (r["speaker_map"] or {}).values() if a.get("person_id")}
    known = {i["id"] for i in identities}
    return found & known


# ---- pronouns ------------------------------------------------------------------------------------------------------------

PRONOUN_WORDS = {"she/her": {"she", "her", "hers", "herself"}, "he/him": {"he", "him", "his", "himself"},
                 "they/them": {"they", "them", "their", "theirs", "themselves"}}
THIRD_PERSON = {"she", "her", "hers", "herself", "he", "him", "his", "himself"}


def pronoun_findings(fields: dict[str, str], identities: list[dict] | None, *, where: str = "copy") -> list[dict]:
    """A sentence that names a person whose pronouns are recorded and uses a third-person pronoun of another set: a likely
    misgendering (the 13 October packs called a prospect "he"; N8's free-model shakedown wrote "him" for her in a card's
    guardrail). A sentence can name two people, so this is a warning for a person to read, not a block. "They" is never
    flagged: it is always a safe way to refer to anyone."""
    findings = []
    people = [i for i in identities or [] if i.get("kind") == "person" and i.get("pronouns") in ("she/her", "he/him")]
    for field, text in fields.items():
        for sentence in re.split(r"(?<=[.!?])\s+", text or ""):
            words = set(re.findall(r"[a-z]+", sentence.lower()))
            for person in people:
                if not any(_mentioned(s, sentence) for s in person.get("spellings") or [person["name"]]):
                    continue
                wrong = sorted((words & THIRD_PERSON) - PRONOUN_WORDS[person["pronouns"]])
                if wrong:
                    findings.append({"kind": "pronoun", "severity": "warning", "field": field,
                                     "message": f"{where.capitalize()} refers to {person['name']} with {', '.join(repr(w) for w in wrong)}; "
                                                f"their recorded pronouns are {person['pronouns']}"})
    return findings


# ---- team practice (1.B13's extension, D24) ------------------------------------------------------------------------------

FIGURE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?\s?[kKmM]?|\d[\d,]*(?:\.\d+)?\s?(?:%|percent|[kK]\b)|\b\d[\d,]{1,}\b")


def _figures(text: str) -> set[str]:
    return {re.sub(r"[^\d.]", "", m.group(0)).rstrip(".") for m in FIGURE.finditer(text or "")} - {""}


def leak_findings(fields: dict[str, str], team_texts, other_texts, identities: list[dict] | None, *,
                  where: str = "copy") -> list[dict]:
    """Blocking findings for a client name or figure in public copy that only an internal meeting's evidence carries (D24:
    internal calls evidence how WIA works, never names or figures). A name is a person's or an account's spelling from the
    identity records; a figure counts when a team-practice text states it and no client-call evidence does."""
    team = "\n".join(t for t in team_texts if t)
    other = "\n".join(t for t in other_texts if t)
    if not team:
        return []
    findings = []
    leaked_figures = _figures(team) - _figures(other)
    names = [(s, i) for i in identities or [] if i.get("role") in ("client", "prospect", "active", "former", "prospect")
             for s in i.get("spellings") or [i["name"]] if _mentioned(s, team) and not _mentioned(s, other)]
    for field, text in fields.items():
        if not text:
            continue
        for spelling, identity in names:
            if _mentioned(spelling, text):
                findings.append({"kind": "team_practice_name", "severity": "blocking", "field": field,
                                 "message": f"{where.capitalize()} names {spelling!r} ({identity['name']}), which only an internal "
                                            "meeting mentions; internal meetings show how WIA works, never a client's name"})
        for figure in sorted(_figures(text) & leaked_figures):
            findings.append({"kind": "team_practice_figure", "severity": "blocking", "field": field,
                             "message": f"{where.capitalize()} states the figure {figure}, which only an internal meeting gives; "
                                        "internal meetings show how WIA works, never a client's figure"})
    return findings


# ---- accounts the system adds from a call (Phase N10's autonomy pass) -----------------------------------------------------
#
# A new client or prospect is not in the reviewed list until someone edits it, so their calls had no account: no account
# memory, no "what happened next", and the identity checks could not follow them. Now a client or prospect call whose
# speakers and title match no account names one from its own title ("Matlai Photography Ads Kickoff Call", "Ads Consultation
# with Peter Larsen", "Ridgefield x WIA | Monthly Strategy Call"), anonymised by default (O3), never-name and never-link off,
# with the call's outside speakers as its people (no pronouns: those come only from evidence). The row says it was added by
# the system (`source` 'call', `reviewed` empty), so a person can correct it in the app; a title that names no business or
# person ("Impromptu Zoom Meeting") adds nothing, because an account is never guessed. A title that is another spelling of an
# existing account ("Brightside" for "The Brightside") is that account: the spelling is added to its aliases instead.

_TITLE_NOISE = re.compile(
    r"\b(?:wia|wedding industry ads|ads?|google ads?|meta ads?|facebook ads?|kick-?off|strategy|consultation|consult|onboarding|"
    r"check-?in|monthly|weekly|quarterly|bi-?weekly|sync|call|calls|meeting|session|review|audit|discovery|intro|introduction|"
    r"messaging|positioning|follow-?up|launch|planning|transcript|zoom|fathom|recording|personal meeting room|impromptu|"
    r"office hours|workshop|training|q\s?&\s?a|catch-?up|touch base|update|recap|demo|leadlock|accelerator|elevate)\b", re.I)
_TITLE_SPLIT = re.compile(r"\s+(?:x|×|\+|&|and|with|\||-|–|—|:|/|_)\s+|[|:–—_]", re.I)
_GENERIC = {"", "the", "our", "my", "new", "client", "prospect", "team", "internal", "call", "untitled", "meeting", "s", "co",
            "venue", "wedding", "planner", "photographer", "florist", "dj", "business", "vendor"}  # a trade alone names no one
_COMPANY_TAIL = re.compile(r"\b(?:llc|inc|co|ltd|company)\.?$", re.I)
_TITLE_DATE = re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|"
                         r"nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b", re.I)


def account_name_from_title(title: str | None) -> str | None:
    """The business or person a client call's title names, or None when it names neither."""
    text = re.sub(r"\.(?:txt|vtt|srt|docx?|md|pdf|json)$", "", (title or "").strip(), flags=re.I)  # an upload's file name
    text = re.sub(r"(?:['’]s)?\s*transcript(?:\s*\(\d+\))?$", "", text, flags=re.I)
    best = None
    for part in _TITLE_SPLIT.split(text):
        cleaned = " ".join(_TITLE_NOISE.sub(" ", part).split()).strip(" .,'’\"()[]")
        cleaned = re.sub(r"^(?:with|for|and|x)\s+", "", cleaned, flags=re.I)
        cleaned = re.sub(r"['’]s$", "", cleaned).strip()
        # A date or a counter in the title is not part of the name ("Review with Dana Lee 2026-03-10 A", "Venue Call #2").
        cleaned = " ".join(_TITLE_DATE.sub(" ", cleaned).split())
        cleaned = re.sub(r"(?:\s+(?:#?\d+|\(\d+\)))+$", "", cleaned)
        if len(cleaned.split()) >= 3 and re.search(r"\s[A-Za-z]$", cleaned):
            cleaned = cleaned[:-2]  # a lone letter after a name of two or more words is a copy's mark, never the name
        if cleaned.lower() in _GENERIC or len(re.sub(r"[^a-z]", "", cleaned.lower())) < 3:
            continue
        if not any(ch.isupper() for ch in cleaned):  # a name is written with a capital; "and then" is not a business
            continue
        best = best or cleaned
    return best


def _bare(name: str) -> str:
    words = re.sub(r"[^a-z0-9 ]+", " ", name.lower()).split()
    words = [w for w in words if w not in ("the", "a")]
    return _COMPANY_TAIL.sub("", " ".join(words)).strip()


def provisional_account(conn, document: dict, mapping: dict, call_type: str) -> str | None:
    """Add the account (and its outside speakers) a client or prospect call names, or link the title's spelling to an existing
    account. Returns the client id, or None when the title names no business or person."""
    name = account_name_from_title(document.get("title"))
    if not name:
        return None
    staff = conn.execute("SELECT name,aliases FROM people WHERE role='staff'").fetchall()
    words = set(_bare(name).split())
    if any(_bare(s["name"]) == _bare(name) or _bare(s["name"]).split()[:1] == _bare(name).split()[:1] and len(words) <= 2
           or any(_bare(a) == _bare(name) for a in s["aliases"] or []) for s in staff):
        return None  # a staff member's meeting room or check-in names WIA's own team, never a client
    outside = [(label, a) for label, a in mapping.items() if label and a.get("role") in ("client", "prospect")]
    if not outside:
        return None
    for row in conn.execute("SELECT client_id,name,aliases FROM clients").fetchall():
        spellings = [row["name"], *(row["aliases"] or [])]
        if any(_bare(s) == _bare(name) for s in spellings):
            if name not in spellings:
                conn.execute("UPDATE clients SET aliases=%s,updated_at=now() WHERE client_id=%s",
                             (json.dumps([*(row["aliases"] or []), name]), row["client_id"]))
            return row["client_id"]
    client_id = client_id_for(name)
    status = "prospect" if call_type == "prospect" else "active"
    conn.execute("""INSERT INTO clients(client_id,name,aliases,status,consent,notes,source) VALUES (%s,%s,'[]',%s,'anonymise_only',%s,'call')
        ON CONFLICT (client_id) DO NOTHING""",
                 (client_id, name, status, f"Added by the system from the call \"{document.get('title')}\" "
                  f"({document['transcript_id']}): check the name, the people and the naming."))
    role = "prospect" if call_type == "prospect" else "client"
    emails = {}
    for passage in document.get("passage_map") or []:
        if passage.get("speaker") and passage.get("speaker_email"):
            emails.setdefault(passage["speaker"], passage["speaker_email"].strip().lower())
    for label, assigned in outside:
        if assigned.get("person_id"):
            continue  # a known person keeps their row (and their own account, if any)
        person = " ".join(label.split())
        if len(person.split()) < 2:
            continue  # a first name or a device label alone is not enough to name a person
        email = emails.get(label)
        if email and conn.execute("SELECT 1 FROM people WHERE lower(email)=%s", (email,)).fetchone():
            email = None  # an address already on someone's row stays theirs
        conn.execute("""INSERT INTO people(person_id,name,role,client_id,aliases,email,source,notes)
            VALUES (%s,%s,%s,%s,'[]',%s,'call',%s) ON CONFLICT (person_id) DO NOTHING""",
                     (person_id_for(person, name), person, role, client_id, email,
                      f"Added by the system from the call \"{document.get('title')}\"; no pronouns until a record states them."))
    return client_id
