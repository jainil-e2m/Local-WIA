"""S0: connector identity. Every run compares what the credential *is* with what was registered."""
from uuid import uuid4

from sqlalchemy import select

from backend.db import transaction
from backend.models.db import AuditEvent, ConnectorAccount
from backend.models.db.base import utcnow
from backend.services.intake.adapters import get_adapter
from backend.services.shared.errors import AuthInvalidError


def verify(provider: str, register: bool = False, actor: str = "cli") -> ConnectorAccount:
    identity = get_adapter(provider).identify()  # network call outside any transaction
    with transaction() as session:
        account = session.execute(
            select(ConnectorAccount).where(ConnectorAccount.provider == provider)
        ).scalars().first()
        if account is None:
            if not register:
                raise AuthInvalidError(f"{provider}: no registered connector account (run with --register)")
            account = ConnectorAccount(
                id=uuid4(), provider=provider, provider_account_id=identity.provider_account_id,
                display_identity=identity.display_identity, expected_identity=identity.expected_identity_value,
                credential_ref=identity.credential_ref, granted_scopes=identity.granted_scopes,
                last_verified_at=utcnow())
            session.add(account)
            session.add(AuditEvent(actor=actor, action="connector.register", target_type="connector_account",
                                   target_id=str(account.id),
                                   details={"provider": provider, "identity": identity.display_identity}))
            return account
        if identity.expected_identity_value != account.expected_identity:
            account.state = "blocked"
            account.blocked_reason = "identity mismatch: credential is not the registered account"
            session.add(AuditEvent(actor=actor, action="connector.blocked", target_type="connector_account",
                                   target_id=str(account.id), details={"reason": "identity_mismatch"}))
            raise AuthInvalidError(f"{provider}: identity mismatch — account blocked")
        account.display_identity = identity.display_identity
        account.granted_scopes = identity.granted_scopes
        account.last_verified_at = utcnow()
        if account.state == "blocked" and account.blocked_reason and "mismatch" not in account.blocked_reason:
            account.state, account.blocked_reason = "active", None  # credential fixed and re-verified
        return account
