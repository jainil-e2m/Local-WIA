"""Edits people make in the app that everyone must see: Action Hub changes and client details (services/edits.py)."""
from sqlalchemy import CheckConstraint, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, IdMixin, TimestampMixin


class SharedEdit(IdMixin, TimestampMixin, Base):
    """One action's or one client's edited fields, layered over what the KB built. `revision` rejects a save
    based on an older copy (two people editing the same thing)."""
    __tablename__ = "shared_edits"
    kind: Mapped[str] = mapped_column(String(20))
    key: Mapped[str] = mapped_column(String(200))
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_by: Mapped[str] = mapped_column(String(200))
    __table_args__ = (
        UniqueConstraint("kind", "key"),
        CheckConstraint("kind IN ('action','client')", name="kind"),
    )
