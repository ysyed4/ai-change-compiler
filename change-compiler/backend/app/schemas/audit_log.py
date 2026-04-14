from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMBase


class AuditLogCreate(BaseModel):
    change_request_id: UUID
    event_type: str
    stage: str
    payload: dict = {}
    telemetry_snapshot: dict = {}
    rule_hits: list[dict] = []
    policy_hits: list[dict] = []


class AuditLogRead(ORMBase):
    id: UUID
    change_request_id: UUID
    event_type: str
    stage: str
    payload: dict
    telemetry_snapshot: dict
    rule_hits: list[dict]
    policy_hits: list[dict]
    created_at: datetime
