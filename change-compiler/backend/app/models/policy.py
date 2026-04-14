import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import EnforcementType


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str] = mapped_column(Text)
    condition_expr: Mapped[str] = mapped_column(Text)
    enforcement: Mapped[EnforcementType] = mapped_column(Enum(EnforcementType), default=EnforcementType.hard_stop)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    scope_platform: Mapped[str] = mapped_column(String(64), default="kafka")
    scope_change_type: Mapped[str] = mapped_column(String(128), default="restart_component")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
