"""A recording link a person added to a past meeting that has none (most older calls were on Zoom)."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, utcnow


class MeetingLink(Base):
    __tablename__ = "meeting_links"
    record_id: Mapped[UUID] = mapped_column(ForeignKey("source_records.id"), primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    added_by: Mapped[str] = mapped_column(String(200))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
