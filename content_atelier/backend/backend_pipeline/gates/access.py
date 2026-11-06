"""The FastAPI side of users and roles (0.B9, R37): the shared secret, then the verified email, then its roles.

Every route under `/storage` depends on these, built once per router by `dependencies`:

- `trusted`: the shared-secret check (401 without it) and an actor header (401 without one). It does no lookup.
  The router applies it to every route, so a read needs no role dependency of its own.
- `current_user`: `trusted`, then the verified email (`x-atelier-email`, else `x-atelier-actor`: the Node server
  sends the same address in both, R37), then its roles from the `users` table or the lists. A header that is not an
  email address is 401, so nothing but a verified email ever holds a role. Every mutating route uses this one.
- `optional_user`: the same, except that a header that is not an email gives an `Actor` with no roles instead
  of a 401. For the reads that only mark what the caller may do.

`Actor` is a string (the lower-cased email) that carries the resolved `Access`; services check it through
`roles.access_for` and store it as the author as before.
"""
from __future__ import annotations

import secrets
from collections import namedtuple

from fastapi import Depends, Header, HTTPException
from psycopg import OperationalError

from . import roles

Dependencies = namedtuple("Dependencies", "trusted current_user optional_user")


def dependencies(secret_of, repo) -> Dependencies:
    """`secret_of()` returns the backend secret to compare; `repo` looks users up and holds the legacy lists."""

    def trusted(authorization: str = Header(default=""), x_atelier_actor: str = Header(default="")):
        secret = secret_of()
        if not secret or not secrets.compare_digest(authorization.encode(), ("Bearer " + secret).encode()):
            raise HTTPException(401, "Verified backend authorization required")
        if not x_atelier_actor.strip() or len(x_atelier_actor) > roles.MAX_EMAIL:
            raise HTTPException(401, "Trusted actor required")
        return x_atelier_actor
    trusted.checks_shared_secret = True

    def resolved(claimed: str, header: str, *, required: bool):
        email = roles.clean(claimed)
        if not email:
            if required:
                raise HTTPException(401, "Verified actor email required")
            return roles.Actor(roles.Access(), header)
        try:
            return roles.Actor(roles.load(repo, email), email)
        except OperationalError as exc:
            raise HTTPException(503, "The user store is unavailable; retry shortly") from exc

    def current_user(subject: str = Depends(trusted), x_atelier_email: str = Header(default="")):
        # The email header wins when both are sent: a decision binds to the verified address, never to a user id.
        return resolved(x_atelier_email.strip() or subject.strip(), subject, required=True)
    current_user.resolves_roles = True

    def optional_user(subject: str = Depends(trusted), x_atelier_email: str = Header(default="")):
        return resolved(x_atelier_email.strip() or subject.strip(), subject, required=False)
    optional_user.resolves_roles = True

    return Dependencies(trusted, current_user, optional_user)
