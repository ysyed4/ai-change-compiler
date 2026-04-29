import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    change_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("change_requests.id", ondelete="CASCADE"))
    org_id: Mapped[str] = mapped_column(String(128), default="default-org")
    event_type: Mapped[str] = mapped_column(String(128))
    stage: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    telemetry_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    rule_hits: Mapped[list[dict]] = mapped_column(JSON, default=list)
    policy_hits: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    change_request = relationship("ChangeRequest", back_populates="audit_logs")
