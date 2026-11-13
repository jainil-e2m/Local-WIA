"""Which approved scopes and contacts are live. Archiving a client pauses its dedicated scopes and its
contacts (S2, decided 29 Oct); cursors and history are kept so reactivation resumes where it stopped."""
from sqlalchemy import exists, select

from backend.models.db import Business, Contact, SenderRule, SourceScope
from backend.services.shared.emails import within


def live_scope():
    """SQL condition: approved, and not dedicated to an archived client."""
    archived_owner = exists().where(Business.id == SourceScope.business_id, Business.status != "active")
    return (SourceScope.state == "approved") & ~archived_owner


def is_live(s, scope) -> bool:
    if scope.state != "approved":
        return False
    return scope.business_id is None or s.get(Business, scope.business_id).status == "active"


def live_contacts(s) -> list[Contact]:
    """Approved contacts of active clients that may decide which client a record belongs to.

    A contact covered by a sender rule never does. A partner linked to a client (e.g. a consultant who
    works with one client but introduces many venues) stays on that client's record, but its mail is
    associated only through the client's own contacts, or goes to association review."""
    from backend.services.people.roster import internal_addresses
    rules = s.execute(select(SenderRule.email, SenderRule.domain)).all()
    emails = {e for e, _ in rules if e}
    emails.update(internal_addresses(s))
    domains = [d for _, d in rules if d]
    out = []
    for c in s.execute(select(Contact).join(Business, Business.id == Contact.business_id).where(
            Contact.status == "approved", Business.status == "active")).scalars():
        domain = c.domain or (c.email.split("@", 1)[1] if c.email else None)
        if c.email in emails or within(domain, domains):
            continue
        out.append(c)
    return out
