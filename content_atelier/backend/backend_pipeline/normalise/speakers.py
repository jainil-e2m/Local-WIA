"""Speaker resolution (plan 1.B5): passage speaker labels mapped to people with a role.

The map is stored beside the immutable passage map (`transcripts.speaker_map`), never inside it. A label resolves, in
order, by:

1. **email** (Fathom's matched calendar invitee): a WIA domain is staff, an address in `people` is that person, any other
   address is an outside voice, unless the full display name is a staff member's on the roster (a contractor who books with
   their own domain, as Jacqueline Hood does): that is the staff member, marked inferred. A first name alone never does it.
2. **name**: the full name, or an alias, of a `people` row. A first name alone resolves only when exactly one person owns
   it. Zoom carries a display name and nothing else, so a name-only match is marked `inferred`.
3. **context**: an unmatched voice in a client call is a client, in a prospect call a prospect (the corpus index's rule:
   the team is known, so anyone else is outside). Marked inferred; elsewhere the role is `unknown`.

A client or prospect identity (1.B12's extension) resolves to its person, but its role in a call is the call's, exactly as
an unmatched voice's would be: a prospect who later signed is a prospect on the sales call and a client afterwards, and a
first pass with no call type yet sends the classifier the same roles it always did, so a model's earlier placement of the
call still matches its request.

Every passage has a role: a passage with no label is `unknown` with basis `no_label`.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

ROLES = ("staff", "client", "prospect", "vendor", "outside", "ai_agent", "unknown")
# What people.role means as a speaker role.
ROLE_OF_PERSON = {"staff": "staff", "client": "client", "prospect": "prospect", "vendor": "vendor", "outside": "outside",
                  "ai_agent": "ai_agent"}
CLIENT_CALLS = {"client_1to1", "office_hours", "workshop"}
# A trailing role or device note some recorders add to a display name: "Dana Lee (Guest)", "Dana Lee's iPhone".
NOISE = re.compile(r"\s*(\((guest|host|co-?host|she/her|he/him|they/them)\)|'s (iphone|ipad|android|macbook)|\bis typing\b)\s*$", re.I)


def normal(label: str) -> str:
    text = unicodedata.normalize("NFKD", label or "").encode("ascii", "ignore").decode().lower()
    while True:
        stripped = NOISE.sub("", text)
        if stripped == text:
            break
        text = stripped
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", text).split())


class Resolver:
    """Resolves labels against `people` rows and the staff email domains."""

    def __init__(self, people: list[dict], staff_domains=()):
        self.staff_domains = {d.lower() for d in staff_domains}
        self.by_email = {p["email"].lower(): p for p in people if p.get("email")}
        self.by_name: dict[str, list[dict]] = {}
        self.by_first: dict[str, list[dict]] = {}
        for person in people:
            names = {normal(person["name"]), *(normal(a) for a in person.get("aliases") or [])}
            for name in filter(None, names):
                self.by_name.setdefault(name, []).append(person)
            first = normal(person["name"]).split(" ")[0] if normal(person["name"]) else ""
            if first and len(normal(person["name"]).split()) > 1:
                self.by_first.setdefault(first, []).append(person)

    @classmethod
    def from_database(cls, conn, staff_domains=()):
        rows = conn.execute("SELECT person_id,name,role,status,aliases,email,client_id FROM people").fetchall()
        return cls(rows, staff_domains)

    def _hit(self, people: list[dict]):
        unique = {p["person_id"]: p for p in people}
        return next(iter(unique.values())) if len(unique) == 1 else None

    def resolve(self, label: str | None, email: str | None, call_type: str | None) -> dict:
        if not label and not email:
            return {"person_id": None, "name": None, "role": "unknown", "basis": "no_label", "inferred": False}
        if email:
            address = email.lower()
            person = self.by_email.get(address)
            if person:
                return self._assigned(person, "email", False, call_type)
            if address.rsplit("@", 1)[-1] in self.staff_domains:
                match = self._hit(self.by_name.get(normal(label or ""), []))
                if match and match["role"] == "staff":
                    return self._assigned(match, "email", False)
                return {"person_id": None, "name": label, "role": "staff", "basis": "email_domain", "inferred": False}
            full = normal(label or "")
            staff = self._hit([p for p in self.by_name.get(full, []) if p["role"] == "staff" and normal(p["name"]) == full])
            if staff:
                return self._assigned(staff, "name_with_outside_email", True)
            return self._external(label, call_type, basis="email", inferred=False)
        name = normal(label or "")
        person = self._hit(self.by_name.get(name, []))
        if person:
            return self._assigned(person, "name", True, call_type)
        # A first name alone is enough only when exactly one person is known by it.
        first = self._hit(self.by_first.get(name, [])) if name and " " not in name else None
        if first:
            return self._assigned(first, "alias", True, call_type)
        return self._external(label, call_type, basis="inferred_external", inferred=True)

    def _assigned(self, person: dict, basis: str, inferred: bool, call_type: str | None = None) -> dict:
        role = ROLE_OF_PERSON.get(person["role"], "unknown")
        if role in ("client", "prospect"):
            role = "client" if call_type in CLIENT_CALLS else "prospect" if call_type == "prospect" else "unknown"
        return {"person_id": person["person_id"], "name": person["name"], "role": role,
                "basis": basis, "inferred": inferred, "status": person.get("status")}

    def _external(self, label, call_type, *, basis, inferred) -> dict:
        role = "client" if call_type in CLIENT_CALLS else "prospect" if call_type == "prospect" else "unknown"
        return {"person_id": None, "name": label, "role": role, "basis": basis if role != "unknown" else "unmatched",
                "inferred": inferred}


def passage_labels(document: dict):
    """(label, email) for each passage in order."""
    for passage in document["passage_map"]:
        yield passage.get("speaker"), passage.get("speaker_email")


def speaker_map(document: dict, resolver: Resolver, call_type: str | None = None) -> dict:
    """Label -> assignment for every distinct speaker of a document (the key `""` stands for passages with no label)."""
    assigned: dict[str, dict] = {}
    for label, email in passage_labels(document):
        key = label or ""
        if key not in assigned:
            assigned[key] = resolver.resolve(label, email, call_type)
    return assigned


def participants(document: dict, mapping: dict) -> list[dict]:
    """The distinct people in the call, in order of first speaking, with a role and how many passages each spoke."""
    counts = Counter(p.get("speaker") or "" for p in document["passage_map"])
    return [{"name": label or None, "role": a["role"], "person_id": a["person_id"], "basis": a["basis"], "inferred": a["inferred"],
             "passages": counts[label]} for label, a in mapping.items() if label]


def passage_roles(document: dict, mapping: dict) -> list[str]:
    """The role of every passage, in order."""
    return [mapping[p.get("speaker") or ""]["role"] for p in document["passage_map"]]


def externals(mapping: dict) -> list[str]:
    """Labels that are not WIA staff or an AI agent: the outside voices a call carries."""
    return [label for label, a in mapping.items() if label and a["role"] not in {"staff", "ai_agent"}]
