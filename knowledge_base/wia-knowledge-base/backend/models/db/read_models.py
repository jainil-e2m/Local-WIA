"""Built read models the frontend loads whole (the portfolio), rebuilt by a maintenance job."""
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base


class ReadModelSnapshot(Base):
    __tablename__ = "read_model_snapshots"
    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSONB)
