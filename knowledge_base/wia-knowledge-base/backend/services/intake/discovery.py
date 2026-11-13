"""S1: discovery proposes scopes and contacts; an admin approves. Nothing is opted in automatically."""
from collections import defaultdict
from pathlib import Path
from uuid import UUID, uuid4

import yaml
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.db import transaction
from backend.models.db import (
    AuditEvent,
    Business,
    BusinessAlias,
    ConnectorAccount,
    Contact,
    SourceScope,
    SyncRun,
)
from backend.models.db.base import utcnow
from backend.models.domain.intake import BusinessHint, DiscoveryResult
from backend.services.intake.adapters import get_adapter
from backend.services.intake.pipeline import window_bounds
from backend.services.shared.emails import (INTERNAL_DOMAINS, PUBLIC_DOMAINS, domain_of, is_automated_sender,
                                            is_platform_domain, within)


def hints(session: Session, business_ids=None) -> list[BusinessHint]:
    out = []
    q = select(Business).where(Business.status == "active")
    if business_ids is not None:
        q = q.where(Business.id.in_(business_ids))
    for b in session.execute(q).scalars():
        aliases = session.execute(select(BusinessAlias.alias).where(BusinessAlias.business_id == b.id)).scalars().all()
        out.append(BusinessHint(b.id, b.name, tuple({b.name, *aliases})))
    return out


PARTNER_CLIENT_THRESHOLD = 3  # a sender proposed for this many clients serves several: a partner, not a contact


def _key(c) -> str:
    """Group a candidate by organisation: its domain, or the address itself for public mailboxes."""
    domain = c.domain or domain_of(c.email)
    return c.email if domain in PUBLIC_DOMAINS else "@" + domain


def _never_client(c, rules, internal_emails=()) -> bool:
    domain = c.domain or domain_of(c.email)
    if c.email and c.email.lower() in internal_emails:
        return True
    if within(domain, INTERNAL_DOMAINS) or is_platform_domain(domain):
        return True
    if c.email and is_automated_sender(c.email):
        return True
    return rules.kind_of(c.email, c.domain) is not None


def filter_contacts(results: dict[str, DiscoveryResult], rules, *, detect_partners: bool = True,
                    internal_emails=()) -> dict[str, set]:
    """Drop candidates that are never client contacts, across all providers at once.

    Internal, team, platform, automated and admin-ruled senders are removed. A domain (or public
    address) proposed for PARTNER_CLIENT_THRESHOLD or more clients is an agency, consultant or vendor:
    it is removed everywhere and returned as a possible partner for the admin to rule on. One proposed
    for exactly two clients stays, marked so it is never pre-ticked."""
    for r in results.values():
        r.contacts = [c for c in r.contacts if not _never_client(c, rules, internal_emails)]
    if not detect_partners:
        return {}
    clients_by_key = defaultdict(set)
    for r in results.values():
        for c in r.contacts:
            clients_by_key[_key(c)].add(c.business_id)
    partners = {k: b for k, b in clients_by_key.items() if len(b) >= PARTNER_CLIENT_THRESHOLD}
    for r in results.values():
        kept = []
        for c in r.contacts:
            k = _key(c)
            if k in partners:
                continue
            if len(clients_by_key[k]) == 2:
                c.evidence += "; also proposed for another client"
            kept.append(c)
        r.contacts = kept
        r.possible_partners = dict(partners)
    return partners


def run_discovery(providers, days: int | None, business_ids=None, *, reset: bool = False) -> dict:
    """Discover across providers, filter contacts across all of them together, then store.

    `reset` (a full run over every provider) first deletes unreviewed discovery suggestions, so ones the
    current filters reject do not linger. Approved and rejected contacts are never touched. Returns
    {provider: DiscoveryResult or the exception that provider raised}."""
    from backend.services.clients import mapping
    from backend.services.people.roster import internal_addresses
    window_start, window_end = window_bounds(days)
    with transaction() as session:
        business_hints = hints(session, business_ids)
        accounts = {a.provider: a.id for a in session.execute(select(ConnectorAccount)).scalars()}
        rules = mapping.sender_rules(session)
        roster_emails = internal_addresses(session)
    results, failures = {}, {}
    for provider in providers:
        try:
            results[provider] = get_adapter(provider).discover(business_hints, window_start, window_end)
        except Exception as exc:  # one provider failing must not hide the others' suggestions
            failures[provider] = exc
    filter_contacts(results, rules, detect_partners=business_ids is None, internal_emails=roster_emails)
    with transaction() as session:
        if reset and not failures:
            session.execute(delete(Contact).where(Contact.status == "candidate", Contact.origin == "discovery"))
        for provider, result in results.items():
            _store(session, accounts[provider], result, window_start, window_end, business_ids)
    return {**results, **failures}


def discover(provider: str, days: int | None, business_ids=None) -> DiscoveryResult:
    """Propose scopes and contacts for one provider. `business_ids` limits matching to those clients (a
    newly added client) and never clears another client's existing suggestion."""
    result = run_discovery([provider], days, business_ids)[provider]
    if isinstance(result, Exception):
        raise result
    return result


def _store(session, account_id, result, window_start, window_end, business_ids) -> None:
    session.add(SyncRun(id=uuid4(), connector_account_id=account_id, mode="discovery", window_start=window_start,
                        window_end=window_end, state="succeeded", finished_at=utcnow()))
    for c in result.scopes:
        scope = session.execute(select(SourceScope).where(
            SourceScope.connector_account_id == account_id, SourceScope.kind == c.kind,
            SourceScope.external_id == c.external_id)).scalar_one_or_none()
        if scope is None:
            scope = SourceScope(id=uuid4(), connector_account_id=account_id, kind=c.kind,
                                external_id=c.external_id, state="candidate")
            session.add(scope)
        # Refresh descriptive fields; never touch an admin's state/business decision.
        scope.name, scope.parent_name = c.name[:500], (c.parent_name or None)
        if c.suggested_business_id or business_ids is None:
            scope.discovery_stats, scope.suggestion_reason = c.stats, c.reason
            scope.suggested_business_id = c.suggested_business_id
        if scope.state == "candidate":
            scope.default_domain, scope.association_mode = c.default_domain, c.association_mode
    for c in result.contacts:
        _upsert_contact_candidate(session, c.business_id, c.email, c.domain, c.display_name)


def discover_client(business_id: UUID) -> dict[str, str]:
    """Discovery for one newly added client across every connected source, over the discovery window."""
    from backend.config import get_settings
    with transaction() as session:
        providers = list(session.execute(select(ConnectorAccount.provider).where(
            ConnectorAccount.state == "active")).scalars())
    out = {}
    for provider, r in run_discovery(providers, get_settings().discovery_window_days, [business_id]).items():
        out[provider] = (f"failed: {type(r).__name__}" if isinstance(r, Exception)
                         else f"{len(r.scopes)} scope(s), {len(r.contacts)} contact(s)")
    with transaction() as session:
        session.add(AuditEvent(actor="system", action="business.discovered", target_type="business",
                               target_id=str(business_id), details=out))
    return out


def run_discover_job(work_id: UUID, lease_token: UUID, payload: dict) -> None:
    from backend.workers import queue
    discover_client(UUID(payload["business_id"]))
    with transaction() as session:
        queue.complete(session, work_id, lease_token)


def _upsert_contact_candidate(session, business_id, email, domain, name):
    q = select(Contact).where(Contact.business_id == business_id)
    q = q.where(Contact.email == email) if email else q.where(Contact.domain == domain)
    if session.execute(q).scalar_one_or_none() is None:
        session.add(Contact(id=uuid4(), business_id=business_id, email=email, domain=domain, display_name=name,
                            status="candidate", origin="discovery"))
        session.flush()


def write_proposal(results: dict[str, DiscoveryResult], out_dir: Path) -> tuple[Path, Path]:
    """Human-readable proposal + an editable approval file (both gitignored: they hold client data)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence = defaultdict(list)
    for provider, r in results.items():
        for c in r.contacts:
            evidence[(c.business_id, c.email, c.domain)].append(c.evidence)

    with transaction() as session:
        businesses = {b.id: b for b in session.execute(select(Business)).scalars()}
        hint_by_id = {h.business_id: h for h in hints(session)}
        accounts = {a.id: a for a in session.execute(select(ConnectorAccount)).scalars()}
        scopes = session.execute(select(SourceScope).order_by(SourceScope.connector_account_id, SourceScope.name)).scalars().all()
        contacts = session.execute(select(Contact).order_by(Contact.business_id, Contact.domain, Contact.email)).scalars().all()

        scope_rows, contact_rows = [], []
        for s in scopes:
            provider = accounts[s.connector_account_id].provider
            suggested = businesses.get(s.suggested_business_id or s.business_id)
            if s.state != "candidate":
                default = s.state == "approved"
            elif s.association_mode == "per_record":
                # Shared sources that qualify per record by contact. Unmapped Slack channels (programme,
                # testing) are never proposed: their mixed-client content needs a deliberate decision.
                default = provider in ("gmail", "fathom") or (
                    provider == "calendar" and bool((s.discovery_stats or {}).get("client_titled_events")))
            else:
                default = suggested is not None
            scope_rows.append({
                "id": str(s.id), "provider": provider, "kind": s.kind, "name": s.name, "parent": s.parent_name,
                "mode": s.association_mode, "business": suggested.slug if suggested and s.association_mode == "dedicated" else None,
                "approve": default, "why": s.suggestion_reason,
            })
        for c in contacts:
            ev = evidence.get((c.business_id, c.email, c.domain), [])
            if c.status != "candidate":
                default = c.status == "approved"
            elif any("also proposed for another client" in e for e in ev):
                default = False  # seen for two clients: an admin decides
            elif c.domain:
                default = c.domain not in PUBLIC_DOMAINS and any("matches client name" in e for e in ev)
            else:
                # Seen on a client meeting (calendar/fathom), or the address itself carries the client's name.
                default = any(not e.startswith("gmail:") for e in ev) or hint_by_id[c.business_id].matches_text(c.email)
            contact_rows.append({
                "id": str(c.id), "business": businesses[c.business_id].slug, "email": c.email, "domain": c.domain,
                "name": c.display_name, "approve": default, "evidence": sorted(set(ev))[:4],
            })

    approval = out_dir / "approval.yaml"
    header = ("# Review, edit `approve` (true/false) and `business` (slug) where needed, then run:\n"
              "#   python -m backend.scripts.kb approve backend/.local/approval.yaml\n"
              "# Dedicated scopes need a business. Per-record scopes qualify records by approved contacts.\n")
    approval.write_text(header + yaml.safe_dump({"scopes": scope_rows, "contacts": contact_rows},
                                                sort_keys=False, allow_unicode=True, width=140), encoding="utf-8")

    lines = ["# Discovery proposal", ""]
    for provider in sorted({r["provider"] for r in scope_rows}):
        lines += [f"## {provider}", "", "| Approve | Scope | Mode | Client | Why |", "|---|---|---|---|---|"]
        for r in [r for r in scope_rows if r["provider"] == provider]:
            where = f"{r['parent']} / {r['name']}" if r["parent"] else r["name"]
            lines.append(f"| {'✅' if r['approve'] else '—'} | {r['kind']}: {where} | {r['mode']} | "
                         f"{r['business'] or ''} | {r['why'] or ''} |")
        lines.append("")
    lines += ["## Client contacts", "", "| Approve | Client | Email / domain | Evidence |", "|---|---|---|---|"]
    for r in contact_rows:
        lines.append(f"| {'✅' if r['approve'] else '—'} | {r['business']} | {r['email'] or '@' + r['domain']} | "
                     f"{'; '.join(r['evidence'])} |")
    partners = {}
    for r in results.values():
        partners.update(getattr(r, "possible_partners", None) or {})
    if partners:
        lines += ["", "## Possible partners (proposed for 3+ clients, so never proposed as a client's contact)", "",
                  "Rule on each: python -m backend.scripts.kb sender-rule add partner|team|blocked <domain or email> --reason ...",
                  "", "| Sender | Clients |", "|---|---|"]
        for k, ids in sorted(partners.items()):
            lines.append(f"| {k} | {', '.join(sorted(businesses[i].slug for i in ids if i in businesses))} |")
    proposal = out_dir / "proposal.md"
    proposal.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return proposal, approval


def apply_approval(path: Path, actor: str = "cli") -> dict:
    from backend.services.clients import mapping
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    summary = {"scopes_approved": 0, "scopes_excluded": 0, "contacts_approved": 0, "contacts_rejected": 0}
    with transaction() as session:
        by_slug = {b.slug: b.id for b in session.execute(select(Business)).scalars()}
        for row in data.get("scopes", []):
            scope = session.get(SourceScope, UUID(row["id"]))
            if row.get("approve"):
                business_id = None
                if scope.association_mode == "dedicated" or row.get("mode") == "dedicated":
                    if row.get("business") not in by_slug:
                        raise ValueError(f"scope {scope.name}: dedicated scope needs a valid business slug")
                    business_id = by_slug[row["business"]]
                mapping.assign_scope(session, scope.id, business_id=business_id, expected_revision=None, actor=actor)
                summary["scopes_approved"] += 1
            else:
                mapping.exclude_scope(session, scope.id, expected_revision=None, actor=actor)
                summary["scopes_excluded"] += 1
        for row in data.get("contacts", []):
            mapping.review_contact(session, UUID(row["id"]), approve=bool(row.get("approve")), expected_revision=None,
                                   actor=actor, business_id=by_slug.get(row.get("business")))
            summary["contacts_approved" if row.get("approve") else "contacts_rejected"] += 1
    return summary
