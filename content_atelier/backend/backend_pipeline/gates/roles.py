"""Users and roles (0.B9, R37, R50): who a verified email is allowed to be.

One identity, the verified email the Node server resolves from the Command Center session (R37). One function,
`resolve`, turns it into an `Access`: the roles held (viewer < editor < approver < admin, each implying the ones
below) and what they allow. Every role check in the editorial path, the knowledge review, the packs, the calendar
and the intake screens asks an `Access`; none keeps a private allowlist.

Precedence (documented in DEPLOYMENT.md, "Users and roles"):

1. The `users` table (migration 005). A person with a row has exactly that row's role. The environment lists
   below are not consulted for their roles, so a row can demote someone who is still on a list.
2. Otherwise the legacy environment lists, so a deployment that has not seeded `users` (or has not applied
   migration 005) behaves exactly as before: `ATELIER_BRIEF_APPROVERS` and `ATELIER_BRIEF_EDITORS` give approver
   and editor, `ATELIER_INTAKE_ADMINS` gives admin, `ATELIER_PACK_*` and `ATELIER_CALENDAR_SCHEDULERS` give the
   pack and scheduling capabilities.
3. Otherwise viewer: anyone the Command Center lets in may read.

Identity approvers (`ATELIER_IDENTITY_APPROVERS`, Whitney under rulings 2.5) are a narrower list that stays in
the environment under both rules: when it is non-empty it alone confirms identity changes. Packs and the calendar
are outside this scope (R31); they resolve here, so nothing keeps a private allowlist, but keep their behaviour:
from the lists when there is no row, from the role (editor or above to generate and to schedule, approver or above
to approve a pack) when there is one.

A bare string (as the offline tests and the command line pass) resolves from the lists only. The API never passes
one: its dependency (`gates.access`) looks the email up in `users` and hands services an `Actor`, a string that
carries the resolved `Access`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from psycopg.errors import UndefinedTable

ROLES = ("viewer", "editor", "approver", "admin")
RANK = {role: n for n, role in enumerate(ROLES)}
MAX_EMAIL = 320
# The `users` row a legacy list maps to, highest first (seed): approvers win over editors.
SEED_SOURCES = (
    ("admin", ("intake_admins",)),
    ("approver", ("brief_approvers", "pack_approvers")),
    ("editor", ("brief_editors", "pack_editors", "calendar_schedulers")),
)


def clean(value) -> str | None:
    """The lower-cased address when `value` is a plausible email, else None. The table's CHECK needs lower case
    and a local part; the header must be one token."""
    if not isinstance(value, str):
        return None
    email = value.strip().lower()
    if not email or len(email) > MAX_EMAIL or any(ch.isspace() for ch in email):
        return None
    local, at, domain = email.partition("@")
    if not at or not local or not domain or "@" in domain:
        return None
    return email


def key(value) -> str:
    """The comparison key for a bare string or a list entry: trimmed and lower case. No email test: the lists
    and the offline tests hold plain names; the API checks `clean` before it resolves."""
    return value.strip().lower() if isinstance(value, str) else ""


def chain(role: str) -> frozenset[str]:
    """admin implies approver implies editor implies viewer."""
    return frozenset(r for r in ROLES if RANK[r] <= RANK[role])


def listed(settings, name: str) -> frozenset[str]:
    return frozenset(k for k in (key(x) for x in (getattr(settings, name, None) or ())) if k)


@dataclass(frozen=True)
class Access:
    email: str | None = None
    roles: frozenset[str] = frozenset()
    source: str = "none"  # 'users' (a row), 'lists' (the environment lists, or the viewer default), 'none' (no identity)
    name: str | None = None
    slack_user_id: str | None = None
    identity_approver: bool = False
    identity_gated: bool = False  # the identity-approver list is non-empty
    pack_editor: bool = False
    pack_approver: bool = False
    scheduler: bool = False

    @property
    def role(self) -> str | None:
        held = [r for r in ROLES if r in self.roles]
        return held[-1] if held else None

    def can(self, capability: str) -> bool:
        if capability == "edit":
            return "editor" in self.roles
        if capability == "decide":
            return "approver" in self.roles
        if capability == "review":
            return "approver" in self.roles or self.identity_approver
        if capability in ("manage_users", "manage_intake"):
            return "admin" in self.roles
        if capability == "edit_packs":
            return self.pack_editor
        if capability == "approve_packs":
            return self.pack_approver
        if capability == "schedule":
            return self.scheduler
        raise ValueError(f"Unknown capability {capability!r}")

    def can_review(self, identity_kind: bool = False) -> bool:
        """Confirm a knowledge-base item: an identity kind needs an identity approver when that list is non-empty
        (rulings 2.5); everything else needs an approver."""
        if identity_kind and self.identity_gated:
            return self.identity_approver
        return "approver" in self.roles

    def capabilities(self) -> dict[str, bool]:
        """What the screens may offer. The server still checks each action."""
        return {
            "edit_cards": self.can("edit"), "edit_briefs": self.can("edit"),
            "decide": self.can("decide"), "approve_briefs": self.can("decide"),
            "review_knowledge": self.can("review"), "identity_review": self.can_review(True),
            "manage_users": self.can("manage_users"), "manage_intake": self.can("manage_intake"),
            "generate_packs": self.can("edit_packs"), "approve_packs": self.can("approve_packs"),
            "schedule_calendar": self.can("schedule"),
        }

    def describe(self) -> dict:
        """The answer of GET /storage/me."""
        return {"email": self.email, "name": self.name, "slack_user_id": self.slack_user_id, "role": self.role,
                "roles": [r for r in ROLES if r in self.roles], "source": self.source,
                "identity_approver": self.identity_approver, "can": self.capabilities()}


class Actor(str):
    """The verified email as a string (it is stored as the author and compared as before), carrying its `Access`."""

    access: Access

    def __new__(cls, access: Access, text: str | None = None):
        obj = super().__new__(cls, access.email or text or "")
        obj.access = access
        return obj

    def __reduce__(self):
        # copy.deepcopy and pickle rebuild a string subclass from its text alone; keep the access with it.
        return (Actor, (self.access, str(self)))


def resolve(settings, email: str | None, row: dict | None = None) -> Access:
    """The roles of one person. `row` is their `users` row, if the table has one (precedence above)."""
    who = key(email)
    if not who:
        return Access()
    identity_list = listed(settings, "identity_approvers")
    common = {"email": who, "identity_approver": who in identity_list, "identity_gated": bool(identity_list)}
    if row:
        roles = chain(row["role"])
        return Access(roles=roles, source="users", name=row.get("name"), slack_user_id=row.get("slack_user_id"),
                      pack_editor="editor" in roles, pack_approver="approver" in roles, scheduler="editor" in roles, **common)
    approvers, editors = listed(settings, "brief_approvers"), listed(settings, "brief_editors")
    roles = {"viewer"}
    if who in editors or who in approvers:
        roles.add("editor")
    if who in approvers:
        roles.add("approver")
    # An intake administrator is an administrator for users and intake; it does not become an approver on the
    # legacy lists, so an unseeded deployment keeps today's behaviour.
    if who in listed(settings, "intake_admins"):
        roles.add("admin")
    pack_approvers = listed(settings, "pack_approvers")
    return Access(roles=frozenset(roles), source="lists", pack_editor=who in listed(settings, "pack_editors") or who in pack_approvers,
                  pack_approver=who in pack_approvers, scheduler=who in listed(settings, "calendar_schedulers"), **common)


def access_for(settings, actor) -> Access:
    """The `Access` of whoever a service was handed: an `Actor` brings its own; a bare string resolves from the lists."""
    if isinstance(actor, Actor):
        return actor.access
    return resolve(settings, actor if isinstance(actor, str) else None)


def access_in(conn, settings, actor) -> Access:
    """`access_for` for a worker or the scheduler, which hold the address a run recorded as a bare string: it resolves through
    the `users` table like the API, on the caller's connection. A person with a row who is on no list is not a viewer."""
    if isinstance(actor, Actor):
        return actor.access
    who = actor if isinstance(actor, str) else None
    return resolve(settings, who, fetch(conn, who) if key(who) else None)


def fetch(conn, email: str) -> dict | None:
    """The `users` row, or None when the person has none or the database has not applied migration 005."""
    try:
        return conn.execute("SELECT email,name,role,slack_user_id FROM users WHERE email=%s", (key(email),)).fetchone()
    except UndefinedTable:
        conn.rollback()
        return None


def load(repo, email: str) -> Access:
    """Resolve through the database. Raises psycopg errors other than a missing table; the API maps them to 503."""
    with repo.connection() as conn:
        row = fetch(conn, email)
    return resolve(repo.settings, email, row)


def actor_for(repo, email: str) -> Actor:
    """For the command line and workers: the same resolution the API does for a request."""
    return Actor(load(repo, email), key(email))


# --- managing the table (storage_cli users ...) ---------------------------------------------------------------

def users(conn) -> list[dict]:
    return conn.execute("SELECT email,name,role,slack_user_id,created_at,updated_at FROM users ORDER BY email").fetchall()


def _record(conn, setting: str, actor: str, value: dict):
    conn.execute("""INSERT INTO settings(key,value,updated_by) VALUES (%s,%s::jsonb,%s)
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value,updated_by=EXCLUDED.updated_by,updated_at=now()""",
                 (setting, json.dumps(value), actor))


def set_user(conn, settings, *, actor: str, email: str, role: str, name: str | None = None,
             slack_user_id: str | None = None) -> dict:
    """Create or change one person. Only an administrator may (checked against the actor's own resolution)."""
    by = key(actor)
    if not resolve(settings, by, fetch(conn, by)).can("manage_users"):
        raise PermissionError("Managing users needs an administrator")
    address = clean(email)
    if not address:
        raise ValueError("Give the person's email address")
    if role not in ROLES:
        raise ValueError("Role must be one of " + ", ".join(ROLES))
    before = fetch(conn, address)
    row = conn.execute("""INSERT INTO users(email,name,role,slack_user_id) VALUES (%s,%s,%s,%s)
        ON CONFLICT (email) DO UPDATE SET role=EXCLUDED.role,name=COALESCE(EXCLUDED.name,users.name),
        slack_user_id=COALESCE(EXCLUDED.slack_user_id,users.slack_user_id),updated_at=now()
        RETURNING email,name,role,slack_user_id""", (address, name, role, slack_user_id)).fetchone()
    _record(conn, "users.last_change", by, {"email": address, "from": before["role"] if before else None, "to": role,
                                            "at": datetime.now(UTC).isoformat()})
    return row


def wanted(settings) -> tuple[dict[str, str], list[str]]:
    """The role each listed address would get: the highest list it is on (admin, then approver, then editor).
    Identity approvers get a row as viewers: that list stays narrower and separate. Entries that are not email
    addresses cannot be rows (the table requires one) and are returned apart."""
    result: dict[str, str] = {}
    skipped: list[str] = []
    for role, names in SEED_SOURCES:
        for name in names:
            for entry in sorted(listed(settings, name)):
                if not clean(entry):
                    skipped.append(entry)
                elif RANK[role] > RANK.get(result.get(entry), -1):
                    result[entry] = role
    for entry in sorted(listed(settings, "identity_approvers")):
        if clean(entry):
            result.setdefault(entry, "viewer")
        else:
            skipped.append(entry)
    return result, sorted(set(skipped))


def seed(conn, settings, *, actor: str, overwrite: bool = False) -> dict:
    """Create a row for every address on the legacy lists. Idempotent: it adds the missing rows and never changes
    an existing one unless `overwrite`, so a role an administrator set with `users set` survives a second run.
    Rows that differ from their lists are reported. Records who ran it."""
    desired, skipped = wanted(settings)
    existing = {r["email"]: r for r in conn.execute("SELECT email,role FROM users").fetchall()}
    created, updated, differs = [], [], []
    for email, role in desired.items():
        if email not in existing:
            conn.execute("INSERT INTO users(email,role) VALUES (%s,%s)", (email, role))
            created.append({"email": email, "role": role})
        elif existing[email]["role"] != role:
            if overwrite:
                conn.execute("UPDATE users SET role=%s,updated_at=now() WHERE email=%s", (role, email))
                updated.append({"email": email, "from": existing[email]["role"], "to": role})
            else:
                differs.append({"email": email, "row": existing[email]["role"], "lists": role})
    # One role cannot say "intake administrator but not approver", or "scheduler but not card editor". Name every
    # person whose row would allow more than their lists did, so the operator can lower it with `users set`.
    gains = []
    for email, role in desired.items():
        before, after = resolve(settings, email).capabilities(), resolve(settings, email, {"role": role}).capabilities()
        more = sorted(k for k, allowed in after.items() if allowed and not before[k])
        if more:
            gains.append({"email": email, "role": role, "gains": more})
    result = {"created": created, "updated": updated, "differs": differs, "skipped_not_email": skipped,
              "gains_beyond_the_lists": gains, "total_rows": len(existing) + len(created)}
    _record(conn, "users.seed.last", key(actor), {**result, "overwrite": overwrite, "at": datetime.now(UTC).isoformat()})
    return result


def run_users(storage, args) -> dict:
    """`storage_cli users seed|list|set`."""
    from ..database import connect
    with connect(storage.database_url, vectors=False) as conn:
        try:
            if args.users_command == "seed":
                result = seed(conn, storage, actor=args.actor, overwrite=args.overwrite)
            elif args.users_command == "set":
                result = set_user(conn, storage, actor=args.actor, email=args.email, role=args.role, name=args.name,
                                  slack_user_id=args.slack_user_id)
            else:
                result = {"users": users(conn)}
        except UndefinedTable:
            raise SystemExit("The users table does not exist; apply migration 005 first (storage_cli migrate)")
        conn.commit()
    return result
