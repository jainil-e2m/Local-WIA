"""SQLAlchemy mappings. Importing this package registers every table on Base.metadata."""
from backend.models.db.base import Base
from backend.models.db.people import AccountTeamMember, MailboxHolder, Person, PersonAddress
from backend.models.db.ops import AuditEvent, CoverageWindow, SyncCursor, SyncRun, WorkItem
from backend.models.db.registry import (Business, BusinessAlias, ClientSourceDecision, Contact, SenderRule,
                                        ServiceEngagement)
from backend.models.db.sync import (AssociationReview, DriveNode, RecordChange, ScopeMembership,
                                    SyncStream, WebhookReceipt)
from backend.models.db.sources import (
    ConnectorAccount,
    ContentUnit,
    ProviderIdentity,
    RecordAssociation,
    SourceRecord,
    SourceScope,
    SourceVersion,
)
from backend.models.db.outbound import ClickUpConnection, OutboundRequest
from backend.models.db.leadlock import LeadLockAppEvent, LeadLockInstallation, LeadLockLocation
from backend.models.db.read_models import ReadModelSnapshot
from backend.models.db.edits import SharedEdit
from backend.models.db.ai import ActionCandidate, AiRun
from backend.models.db.meetings import MeetingLink
from backend.models.db.callprep import AdAccount, AdDaily, CallBrief, CallOverride, CallSkill

__all__ = [
    "AdAccount",
    "AdDaily",
    "CallBrief",
    "CallOverride",
    "CallSkill",
    "ActionCandidate",
    "AiRun",
    "ClickUpConnection",
    "LeadLockAppEvent",
    "LeadLockInstallation",
    "LeadLockLocation",
    "MeetingLink",
    "OutboundRequest",
    "ReadModelSnapshot",
    "SharedEdit",
    "AccountTeamMember",
    "MailboxHolder",
    "Person",
    "PersonAddress",
    "AuditEvent",
    "Base",
    "Business",
    "BusinessAlias",
    "ClientSourceDecision",
    "ConnectorAccount",
    "Contact",
    "ContentUnit",
    "CoverageWindow",
    "ProviderIdentity",
    "RecordAssociation",
    "SenderRule",
    "ServiceEngagement",
    "SourceRecord",
    "SourceScope",
    "SourceVersion",
    "SyncCursor",
    "SyncRun",
    "WorkItem",
]
