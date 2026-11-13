"""SourceAdapter contract.

identify()      -> who the credential really is (compared with the registered identity)
discover()      -> candidate scopes and contacts; never opts anything in
backfill_page() -> one page of normalised, qualified records for one approved scope

Backfill and incremental share backfill_page(); production incremental passes a
provider cursor instead of a window (Ingestion design §8.1).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from backend.models.domain.intake import BusinessHint, ChangeBatch, DiscoveryResult, IntakeContext


@dataclass
class ConnectorIdentity:
    provider_account_id: str
    display_identity: str
    expected_identity_value: str  # the value compared with ConnectorAccount.expected_identity
    granted_scopes: list[str]
    credential_ref: str


class SourceAdapter(Protocol):
    provider: str
    parser_version: str

    def identify(self) -> ConnectorIdentity: ...

    def discover(self, hints: list[BusinessHint], window_start: datetime | None,
                 window_end: datetime) -> DiscoveryResult: ...

    def backfill_page(self, ctx: IntakeContext, cursor: str | None) -> ChangeBatch: ...
